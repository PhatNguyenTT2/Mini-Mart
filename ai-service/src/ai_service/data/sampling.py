"""Deterministic mixed negative sampling over materialized purchase indexes."""

from __future__ import annotations

import numpy as np

from ai_service.data.dataset import PurchaseTrainingIndex, RulePairIndex, build_rule_pair_index
from ai_service.data.quality import filter_event_origin
from ai_service.data.snapshot import Snapshot
from ai_service.errors import NegativeSamplingError


class MixedNegativeSampler:
    def __init__(
        self,
        index: PurchaseTrainingIndex,
        snapshot: Snapshot,
        semantic_embeddings: np.ndarray,
        *,
        ratio: int = 16,
        seed: int = 42,
        rule_pair_index: RulePairIndex | None = None,
        rule_hard_negative_count: int = 0,
    ) -> None:
        if ratio < 4:
            raise ValueError("mixed negative ratio must be at least four")
        embeddings = np.asarray(semantic_embeddings, dtype=np.float32)
        if embeddings.shape[0] != snapshot.manifest.num_items or not np.isfinite(embeddings).all():
            raise ValueError("semantic embeddings do not match the catalog")
        self.index = index
        self.ratio = ratio
        self.seed = seed
        if rule_hard_negative_count < 0 or rule_hard_negative_count > ratio // 4:
            raise ValueError("rule_hard_negative_count must fit the warm quota")
        self.rule_pair_index = rule_pair_index or build_rule_pair_index(snapshot)
        self.rule_hard_negative_count = int(rule_hard_negative_count)
        self._context_by_target = {
            (int(user), int(item)): int(context)
            for user, item, context in zip(
                index.users, index.positive_items, index.context_items, strict=True
            )
        }
        cold = set(int(item) for item in snapshot.cold_item_ids)
        self.warm_items = np.asarray(
            [item for item in range(snapshot.manifest.num_items) if item not in cold],
            dtype=np.int64,
        )
        popularity = filter_event_origin(snapshot.train_df).internal_product_id.value_counts()
        self.popular_items = np.asarray(
            [int(item) for item in popularity.index if int(item) not in cold], dtype=np.int64
        )
        normalized = embeddings / np.maximum(
            np.linalg.norm(embeddings, axis=1, keepdims=True), np.finfo(np.float32).eps
        )
        neighbor_count = min(64, len(self.warm_items))
        self.semantic_neighbors = np.empty(
            (snapshot.manifest.num_items, neighbor_count), dtype=np.int64
        )
        for offset in range(0, len(normalized), 256):
            scores = normalized[offset : offset + 256] @ normalized.T
            order = np.argsort(-scores, axis=1, kind="stable")
            for row, values in enumerate(order):
                filtered = [int(item) for item in values if int(item) not in cold]
                self.semantic_neighbors[offset + row] = filtered[:neighbor_count]
        self.model_hard_cache: np.ndarray | None = None

    def update_model_hard_cache(self, values: np.ndarray) -> None:
        raw_cache = np.asarray(values)
        if raw_cache.dtype != np.int32:
            raise ValueError("model hard cache must use int32 IDs")
        cache = raw_cache.astype(np.int32, copy=False)
        if cache.ndim != 2 or cache.shape[0] != self.index.known_history.shape[0]:
            raise ValueError("model hard cache must have shape [num_users+1,K]")
        if cache.shape[1] < 1:
            raise ValueError("model hard cache width must be positive")
        if not np.all(cache[0] == -1):
            raise ValueError("model hard cache row zero must be the -1 sentinel")
        if np.any(cache[1:] < 0) or np.any(~np.isin(cache[1:], self.warm_items)):
            raise ValueError("model hard cache contains cold or invalid items")
        for user in range(1, cache.shape[0]):
            if np.any(self.index.known_history[user, cache[user].astype(np.int64)]):
                raise ValueError("model hard cache contains known history items")
            if len(np.unique(cache[user])) != cache.shape[1]:
                raise ValueError("model hard cache rows must not contain duplicate items")
        self.model_hard_cache = cache.copy()

    def _draw(
        self,
        pool: np.ndarray,
        count: int,
        *,
        rng: np.random.Generator,
        selected: set[int],
        user: int,
        positive: int,
        allow_fallback: bool = True,
    ) -> list[int]:
        if count == 0:
            return []
        values: list[int] = []
        candidates = np.asarray(pool, dtype=np.int64)
        if not len(candidates):
            candidates = self.warm_items
        for candidate in rng.permutation(candidates):
            item = int(candidate)
            if item == positive or item in selected or self.index.known_history[user, item]:
                continue
            selected.add(item)
            values.append(item)
            if len(values) == count:
                break
        if len(values) < count and allow_fallback:
            for candidate in rng.permutation(self.warm_items):
                item = int(candidate)
                if item in selected or self.index.known_history[user, item]:
                    continue
                selected.add(item)
                values.append(item)
                if len(values) == count:
                    break
        if len(values) != count:
            raise NegativeSamplingError("mixed negative candidate pool exhausted")
        return values

    def sample(
        self,
        users: np.ndarray,
        positive_items: np.ndarray,
        *,
        epoch: int,
        batch_index: int,
    ) -> np.ndarray:
        users = np.asarray(users, dtype=np.int64)
        positives = np.asarray(positive_items, dtype=np.int64)
        if users.shape != positives.shape or users.ndim != 1:
            raise ValueError("users and positive_items must be equal [B] vectors")
        if np.any(users < 1) or np.any(users >= self.index.known_history.shape[0]):
            raise NegativeSamplingError("sampler users must be in the range [1,num_users]")
        result = np.empty((len(users), self.ratio), dtype=np.int64)
        result_with_sources = self._sample_internal(
            users, positives, epoch=epoch, batch_index=batch_index
        )
        result[...] = result_with_sources[0]
        return result

    def sample_with_sources(
        self,
        users: np.ndarray,
        positive_items: np.ndarray,
        *,
        epoch: int,
        batch_index: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return candidates and a stable source tag matrix for diagnostics."""
        return self._sample_internal(users, positive_items, epoch=epoch, batch_index=batch_index)

    def _sample_internal(
        self,
        users: np.ndarray,
        positive_items: np.ndarray,
        *,
        epoch: int,
        batch_index: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        users = np.asarray(users, dtype=np.int64)
        positives = np.asarray(positive_items, dtype=np.int64)
        if users.shape != positives.shape or users.ndim != 1:
            raise ValueError("users and positive_items must be equal [B] vectors")
        if np.any(users < 1) or np.any(users >= self.index.known_history.shape[0]):
            raise NegativeSamplingError("sampler users must be in the range [1,num_users]")
        result = np.empty((len(users), self.ratio), dtype=np.int64)
        sources = np.empty((len(users), self.ratio), dtype="U16")
        base = self.ratio // 4
        quotas = [base, base, base, base + self.ratio - base * 4]
        for row_index, (user, positive) in enumerate(zip(users, positives, strict=True)):
            rng = np.random.default_rng(
                np.random.SeedSequence([self.seed, epoch, batch_index, row_index])
            )
            selected: set[int] = set()

            semantic = self.semantic_neighbors[int(positive)]
            model_cache = self.model_hard_cache
            if epoch >= 2:
                if model_cache is None:
                    raise NegativeSamplingError("model hard cache is required from epoch 2")
                model_pool = model_cache[int(user)]
            else:
                model_pool = semantic
            values: list[int] = []
            source_values: list[str] = []
            if self.rule_hard_negative_count:
                context = self._context_by_target.get((int(user), int(positive)), -1)
                rule_pool = self.rule_pair_index.candidates(context, int(positive))
                rule_values = self._draw(
                    rule_pool,
                    self.rule_hard_negative_count,
                    rng=rng,
                    selected=selected,
                    user=int(user),
                    positive=int(positive),
                    allow_fallback=False,
                )
                values.extend(rule_values)
                source_values.extend(["rule_hard"] * len(rule_values))
            remaining_warm = max(0, quotas[0] - self.rule_hard_negative_count)
            values.extend(
                self._draw(
                    self.warm_items,
                    remaining_warm,
                    rng=rng,
                    selected=selected,
                    user=int(user),
                    positive=int(positive),
                )
            )
            source_values.extend(["warm"] * remaining_warm)
            values.extend(
                [
                    *self._draw(
                        self.popular_items,
                        quotas[1],
                        rng=rng,
                        selected=selected,
                        user=int(user),
                        positive=int(positive),
                    ),
                    *self._draw(
                        semantic,
                        quotas[2],
                        rng=rng,
                        selected=selected,
                        user=int(user),
                        positive=int(positive),
                    ),
                    *self._draw(
                        model_pool,
                        quotas[3],
                        rng=rng,
                        selected=selected,
                        user=int(user),
                        positive=int(positive),
                        allow_fallback=epoch < 2,
                    ),
                ]
            )
            source_values.extend(["popular"] * quotas[1])
            source_values.extend(["semantic"] * quotas[2])
            source_values.extend(["model_hard"] * quotas[3])
            result[row_index] = values
            sources[row_index] = source_values
        return result, sources
