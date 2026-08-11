"""Dynamic implicit-feedback training dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from ai_service.contracts import ContextRef, SplitName
from ai_service.data.quality import filter_event_origin
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import NegativeSamplingError


@dataclass(frozen=True)
class TrainingBatch:
    user_idx: torch.Tensor
    persona_idx: torch.Tensor
    candidate_item_idx: torch.Tensor
    context_item_idx: torch.Tensor
    context_present: torch.Tensor
    wide_values: torch.Tensor
    rule_present: torch.Tensor
    labels: torch.Tensor
    sample_weight: torch.Tensor
    is_purchase: torch.Tensor


@dataclass(frozen=True)
class PurchaseTrainingIndex:
    users: np.ndarray
    personas: np.ndarray
    context_items: np.ndarray
    positive_items: np.ndarray
    confidence: np.ndarray
    history_items: np.ndarray
    history_mask: np.ndarray
    history_age_days: np.ndarray
    known_history: np.ndarray
    known_purchases: np.ndarray
    view_only_pairs: np.ndarray


@dataclass(frozen=True)
class RulePairIndex:
    """Deterministic organic context→target lookup used by R3 diagnostics."""

    neighbors: dict[int, tuple[int, ...]]

    def candidates(self, context_item: int, positive_item: int) -> np.ndarray:
        values = [
            item
            for item in self.neighbors.get(int(context_item), ())
            if int(item) != int(positive_item)
        ]
        return np.asarray(values, dtype=np.int64)


def build_rule_pair_index(snapshot: Snapshot) -> RulePairIndex:
    """Build organic same-basket directed pairs in stable order.

    Semantic-trap rows are intentionally excluded.  The event timestamp is the
    stable basket boundary for snapshots that do not carry order IDs.
    """
    frame = snapshot.train_df
    if "event_origin" in frame.columns:
        frame = frame[frame.event_origin.astype(str) == "organic"]
    if frame.empty:
        return RulePairIndex({})
    frame = frame.sort_values(["internal_user_id", "event_ts", "event_id"], kind="stable")
    neighbors: dict[int, set[int]] = {}
    for _, basket in frame.groupby(["internal_user_id", "event_ts"], sort=False):
        items = sorted({int(item) for item in basket.internal_product_id})
        for context in items:
            neighbors.setdefault(context, set()).update(item for item in items if item != context)
    return RulePairIndex(
        {context: tuple(sorted(targets)) for context, targets in sorted(neighbors.items())}
    )


def build_purchase_training_index(
    snapshot: Snapshot,
    *,
    max_history_items: int = 32,
) -> PurchaseTrainingIndex:
    """Materialize unique organic purchase targets and strict prior-purchase histories."""
    if max_history_items < 1:
        raise ValueError("max_history_items must be positive")
    frame = filter_event_origin(snapshot.train_df).sort_values(
        ["internal_user_id", "event_ts", "event_id"], kind="stable"
    )
    num_users = int(snapshot.manifest.num_users)
    num_items = int(snapshot.manifest.num_items)
    known = np.zeros((num_users + 1, num_items), dtype=np.bool_)
    known_purchases = np.zeros((num_users + 1, num_items), dtype=np.bool_)
    if len(frame):
        known[
            frame.internal_user_id.to_numpy(np.int64),
            frame.internal_product_id.to_numpy(np.int64),
        ] = True
    purchase_counts: dict[tuple[int, int], int] = {}
    view_counts: dict[tuple[int, int], int] = {}
    for raw_user, raw_item, raw_type in frame[
        ["internal_user_id", "internal_product_id", "event_type"]
    ].itertuples(index=False, name=None):
        pair = (int(raw_user), int(raw_item))
        counts = purchase_counts if raw_type == "purchase" else view_counts
        counts[pair] = counts.get(pair, 0) + 1
    views = set(view_counts)
    purchases = set(purchase_counts)
    for user, item in purchases:
        known_purchases[int(user), int(item)] = True

    users: list[int] = []
    personas: list[int] = []
    contexts: list[int] = []
    positives: list[int] = []
    confidences: list[float] = []
    histories: list[list[int]] = []
    history_ages: list[list[float]] = []
    emitted: set[tuple[int, int]] = set()
    history_by_user: dict[int, list[tuple[int, pd.Timestamp]]] = {}
    pending_by_user: dict[int, list[tuple[int, pd.Timestamp]]] = {}
    last_purchase_by_user: dict[int, int] = {}
    pending_purchase_by_user: dict[int, int] = {}
    timestamp_by_user: dict[int, object] = {}
    for user, item, event_type, timestamp in frame[
        ["internal_user_id", "internal_product_id", "event_type", "event_ts"]
    ].itertuples(index=False, name=None):
        user_id = int(user)
        item_id = int(item)
        previous_timestamp = timestamp_by_user.get(user_id)
        if previous_timestamp is not None and timestamp != previous_timestamp:
            history_by_user.setdefault(user_id, []).extend(pending_by_user.pop(user_id, []))
            if user_id in pending_purchase_by_user:
                last_purchase_by_user[user_id] = pending_purchase_by_user.pop(user_id)
        timestamp_by_user[user_id] = timestamp
        pair = (user_id, item_id)
        if event_type == "purchase" and pair not in emitted:
            emitted.add(pair)
            raw_user = snapshot.raw_user_map.get(user_id)
            users.append(user_id)
            personas.append(
                int(snapshot.persona_map.get(raw_user, 8)) if raw_user is not None else 8
            )
            contexts.append(last_purchase_by_user.get(user_id, -1))
            positives.append(item_id)
            confidences.append(
                float(
                    np.clip(
                        1.0
                        + np.log1p(purchase_counts[pair])
                        + 0.1 * np.log1p(view_counts.get(pair, 0)),
                        1.0,
                        3.0,
                    )
                )
            )
            prior = history_by_user.get(user_id, [])[-max_history_items:]
            padding = max_history_items - len(prior)
            histories.append([-1] * padding + [value for value, _ in prior])
            target_ts = pd.Timestamp(timestamp)
            history_ages.append(
                [0.0] * padding
                + [
                    max(0.0, (target_ts - prior_ts).total_seconds() / 86_400)
                    for _, prior_ts in prior
                ]
            )
        if event_type == "purchase":
            pending_by_user.setdefault(user_id, []).append((item_id, pd.Timestamp(timestamp)))
            pending_purchase_by_user[user_id] = item_id

    history_array = np.asarray(histories, dtype=np.int64).reshape(-1, max_history_items)
    view_only = np.asarray(sorted(views - purchases), dtype=np.int64).reshape(-1, 2)
    return PurchaseTrainingIndex(
        users=np.asarray(users, dtype=np.int64),
        personas=np.asarray(personas, dtype=np.int64),
        context_items=np.asarray(contexts, dtype=np.int64),
        positive_items=np.asarray(positives, dtype=np.int64),
        confidence=np.asarray(confidences, dtype=np.float32),
        history_items=history_array,
        history_mask=history_array >= 0,
        history_age_days=np.asarray(history_ages, dtype=np.float32).reshape(-1, max_history_items),
        known_history=known,
        known_purchases=known_purchases,
        view_only_pairs=view_only,
    )


@dataclass(frozen=True)
class PurchaseBatch:
    user_idx: torch.Tensor
    persona_idx: torch.Tensor
    context_item_idx: torch.Tensor
    positive_item_idx: torch.Tensor
    explicit_negative_idx: torch.Tensor
    positive_mask: torch.Tensor
    denominator_mask: torch.Tensor
    confidence: torch.Tensor
    history_item_idx: torch.Tensor
    history_mask: torch.Tensor
    history_age_days: torch.Tensor
    in_batch_wide_values: torch.Tensor
    in_batch_rule_present: torch.Tensor
    explicit_wide_values: torch.Tensor
    explicit_rule_present: torch.Tensor


class PurchaseBatchIterator:
    """Vectorized deterministic batches without Pandas work in the hot path."""

    def __init__(
        self,
        index: PurchaseTrainingIndex,
        sampler: Any,
        rule_store: RuleStore,
        *,
        batch_size: int,
        seed: int,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.index = index
        self.sampler = sampler
        self.rule_store = rule_store
        self.batch_size = batch_size
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return int(np.ceil(len(self.index.users) / self.batch_size))

    def __iter__(self):  # type: ignore[no-untyped-def]
        order = np.random.default_rng(np.random.SeedSequence([self.seed, self.epoch])).permutation(
            len(self.index.users)
        )
        for batch_index, offset in enumerate(range(0, len(order), self.batch_size)):
            selected = order[offset : offset + self.batch_size]
            users = self.index.users[selected]
            contexts = self.index.context_items[selected]
            positives = self.index.positive_items[selected]
            positive_mask = self.index.known_purchases[users[:, None], positives[None, :]]
            denominator_mask = ~self.index.known_history[users[:, None], positives[None, :]]
            denominator_mask |= positive_mask
            negatives = self.sampler.sample(
                users,
                positives,
                epoch=self.epoch,
                batch_index=batch_index,
            )
            b = len(selected)
            in_batch_candidates = np.broadcast_to(positives[None, :], (b, b))
            in_batch_wide, in_batch_present = self.rule_store.batch_lookup(
                contexts, in_batch_candidates
            )
            explicit_wide, explicit_present = self.rule_store.batch_lookup(contexts, negatives)
            yield PurchaseBatch(
                user_idx=torch.from_numpy(users),
                persona_idx=torch.from_numpy(self.index.personas[selected]),
                context_item_idx=torch.from_numpy(contexts),
                positive_item_idx=torch.from_numpy(positives),
                explicit_negative_idx=torch.from_numpy(negatives),
                positive_mask=torch.from_numpy(positive_mask),
                denominator_mask=torch.from_numpy(denominator_mask),
                confidence=torch.from_numpy(self.index.confidence[selected]),
                history_item_idx=torch.from_numpy(self.index.history_items[selected]),
                history_mask=torch.from_numpy(self.index.history_mask[selected]),
                history_age_days=torch.from_numpy(self.index.history_age_days[selected]),
                in_batch_wide_values=torch.from_numpy(in_batch_wide),
                in_batch_rule_present=torch.from_numpy(in_batch_present),
                explicit_wide_values=torch.from_numpy(explicit_wide),
                explicit_rule_present=torch.from_numpy(explicit_present),
            )


def collate_candidate_groups(rows: list[dict[str, Any]]) -> TrainingBatch:
    return TrainingBatch(
        user_idx=torch.tensor([row["user_idx"] for row in rows], dtype=torch.int64),
        persona_idx=torch.tensor([row["persona_idx"] for row in rows], dtype=torch.int64),
        candidate_item_idx=torch.from_numpy(np.stack([row["candidate_item_idx"] for row in rows])),
        context_item_idx=torch.tensor([row["context_item_idx"] for row in rows], dtype=torch.int64),
        context_present=torch.tensor([row["context_present"] for row in rows], dtype=torch.bool),
        wide_values=torch.from_numpy(np.stack([row["wide_values"] for row in rows])),
        rule_present=torch.from_numpy(np.stack([row["rule_present"] for row in rows])),
        labels=torch.from_numpy(np.stack([row["labels"] for row in rows])),
        sample_weight=torch.tensor([row["sample_weight"] for row in rows], dtype=torch.float32),
        is_purchase=torch.tensor([row["is_purchase"] for row in rows], dtype=torch.bool),
    )


class HybridImplicitDataset(Dataset[dict[str, Any]]):
    def __init__(
        self,
        snapshot: Snapshot,
        rule_store: RuleStore,
        *,
        split: SplitName,
        negative_ratio: int,
        seed: int = 42,
        positive_event_types: frozenset[str] = frozenset({"view", "purchase"}),
    ) -> None:
        if negative_ratio < 1:
            raise ValueError("negative_ratio must be >= 1")
        self.snapshot = snapshot
        self.rule_store = rule_store
        self.negative_ratio = negative_ratio
        self.seed = seed
        if not positive_event_types or not positive_event_types <= {"view", "purchase"}:
            raise ValueError("positive_event_types must select view and/or purchase")
        self.positive_event_types = positive_event_types
        self.epoch = 0
        frames = {
            SplitName.TRAIN: snapshot.train_df,
            SplitName.VAL: snapshot.val_df,
            SplitName.TEST: snapshot.test_df,
        }
        self.frame = (
            frames[split][frames[split].event_type.isin(positive_event_types)]
            .sort_values(["internal_user_id", "event_ts", "event_id"], kind="stable")
            .reset_index(drop=True)
        )
        self.context_refs = self._build_context_refs()
        cold = set(snapshot.cold_item_ids)
        self.warm_items = np.asarray(
            [item for item in range(snapshot.manifest.num_items) if item not in cold],
            dtype=np.int64,
        )
        grouped = snapshot.train_df.groupby("internal_user_id").internal_product_id.apply(set)
        self.user_positives = {
            cast(int, user): {int(item) for item in items} for user, items in grouped.items()
        }
        popularity = snapshot.train_df.internal_product_id.value_counts()
        popular_count = max(1, int(len(self.warm_items) * 0.2))
        self.popular_items = np.asarray(
            [int(item) for item in popularity.index if int(item) not in cold][:popular_count],
            dtype=np.int64,
        )
        popular_set = set(self.popular_items.tolist())
        self.user_hard_available = {
            user: len(self.popular_items) - len(items & popular_set)
            for user, items in self.user_positives.items()
        }

    def _build_context_refs(self) -> tuple[ContextRef, ...]:
        users = self.frame.internal_user_id.to_numpy(np.int64, copy=False)
        timestamps = self.frame.event_ts.to_numpy(copy=False)
        products = self.frame.internal_product_id.to_numpy(np.int64, copy=False)
        purchases = self.frame.event_type.to_numpy(copy=False) == "purchase"
        refs: list[ContextRef] = []
        current_user = -1
        current_timestamp: object | None = None
        last_purchase = -1
        pending_purchase = -1
        for user, timestamp, product, is_purchase in zip(
            users, timestamps, products, purchases, strict=True
        ):
            user_id = int(user)
            if user_id != current_user:
                current_user = user_id
                current_timestamp = timestamp
                last_purchase = -1
                pending_purchase = -1
            elif timestamp != current_timestamp:
                if pending_purchase >= 0:
                    last_purchase = pending_purchase
                current_timestamp = timestamp
                pending_purchase = -1
            refs.append(ContextRef(item_idx=last_purchase, present=last_purchase >= 0))
            if bool(is_purchase):
                pending_purchase = int(product)
        return tuple(refs)

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.frame)

    def _sample_negatives(self, index: int, user_idx: int) -> np.ndarray:
        excluded = self.user_positives.get(user_idx, set())
        eligible_count = len(self.warm_items) - len(excluded)
        if eligible_count < self.negative_ratio:
            raise NegativeSamplingError(
                f"only {eligible_count} valid negatives for ratio {self.negative_ratio}"
            )
        rng = np.random.default_rng(np.random.SeedSequence([self.seed, self.epoch, index]))
        hard_target = self.negative_ratio // 2
        hard_available = self.user_hard_available.get(user_idx, len(self.popular_items))
        hard_count = min(hard_target, hard_available)
        selected: set[int] = set()

        def draw(pool: np.ndarray, count: int) -> list[int]:
            values: list[int] = []
            maximum_attempts = max(64, count * 32)
            attempts = 0
            while len(values) < count and attempts < maximum_attempts:
                candidate = int(pool[int(rng.integers(0, len(pool)))])
                attempts += 1
                if candidate in excluded or candidate in selected:
                    continue
                selected.add(candidate)
                values.append(candidate)
            if len(values) < count:
                remainder = np.fromiter(
                    (
                        int(item)
                        for item in pool
                        if int(item) not in excluded and int(item) not in selected
                    ),
                    dtype=np.int64,
                )
                missing = count - len(values)
                if len(remainder) < missing:
                    raise NegativeSamplingError("negative candidate pool exhausted")
                extra = rng.choice(remainder, size=missing, replace=False).astype(np.int64).tolist()
                selected.update(extra)
                values.extend(extra)
            return values

        hard = draw(self.popular_items, hard_count) if hard_count else []
        uniform = draw(self.warm_items, self.negative_ratio - hard_count)
        return np.asarray(hard + uniform, dtype=np.int64)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.frame.iloc[index]
        user_idx = int(row.internal_user_id)
        positive = int(row.internal_product_id)
        negatives = self._sample_negatives(index, user_idx)
        candidates = np.concatenate((np.asarray([positive], dtype=np.int64), negatives))
        context = self.context_refs[index]
        wide_values, rule_present = self.rule_store.batch_lookup(
            np.asarray([context.item_idx], dtype=np.int64), candidates.reshape(1, -1)
        )
        raw_user_id = self.snapshot.raw_user_map.get(user_idx)
        persona = self.snapshot.persona_map.get(raw_user_id, 8) if raw_user_id is not None else 8
        labels = np.zeros(1 + self.negative_ratio, dtype=np.float32)
        labels[0] = 1.0
        return {
            "user_idx": user_idx,
            "persona_idx": int(persona),
            "candidate_item_idx": candidates,
            "context_item_idx": context.item_idx,
            "context_present": context.present,
            "wide_values": wide_values[0],
            "rule_present": rule_present[0],
            "labels": labels,
            "sample_weight": float(row.interaction_weight),
            "is_purchase": bool(row.event_type == "purchase"),
        }
