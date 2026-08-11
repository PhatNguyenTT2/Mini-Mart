"""Streaming full-catalog evaluation and model-hard negative preparation.

The evaluator deliberately keeps only per-user metrics and the bounded hard
negative cache.  A full ``user -> catalog scores`` mapping is never materialised
by the production seams in this module.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, cast

import numpy as np
import pandas as pd
import torch

from ai_service.config import Settings
from ai_service.contracts import EvaluationReport, ModelVariant, SplitName
from ai_service.data.history import build_user_profile_vectors
from ai_service.data.quality import filter_event_origin
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import DataIntegrityError
from ai_service.evaluation.metrics import ranking_metrics, user_auc
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


class ExternalBatchScorer(Protocol):
    def __call__(self, users: np.ndarray, candidates: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class PreparedEvaluationSplit:
    split: SplitName
    history_events: pd.DataFrame
    scoring_users: np.ndarray
    eligible_users: np.ndarray
    organic_novel_truth: dict[int, set[int]]
    seen_items: dict[int, set[int]]
    latest_prior_purchase_contexts: dict[int, int]
    personas: dict[int, int]
    raw_product_ids: np.ndarray
    candidate_item_ids: np.ndarray
    warm_candidate_item_ids: np.ndarray


@dataclass(frozen=True)
class EvaluationResult:
    report: EvaluationReport
    user_ids: np.ndarray
    per_user_hr: np.ndarray
    per_user_ndcg: np.ndarray
    per_user_gauc: np.ndarray
    top_k_by_user: dict[int, tuple[int, ...]]


@dataclass(frozen=True)
class TrainingValidationPass:
    variants: dict[ModelVariant, EvaluationResult]
    model_hard_cache: np.ndarray
    deep_logit_rms: float
    wide_logit_rms: float
    hybrid_logit_rms: float


def _history_and_target(snapshot: Snapshot, split: SplitName) -> tuple[pd.DataFrame, pd.DataFrame]:
    if split is SplitName.VAL:
        history = snapshot.train_df
        target = snapshot.val_df
    elif split is SplitName.TEST:
        history = pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True)
        target = snapshot.test_df
    else:
        raise ValueError("full-catalog evaluation supports validation or test only")
    return filter_event_origin(history), filter_event_origin(target)


def prepare_split(snapshot: Snapshot, split: SplitName) -> PreparedEvaluationSplit:
    """Freeze temporal history, truth, contexts, and candidate cohorts once."""
    history, target = _history_and_target(snapshot, split)
    history_sets = {
        int(cast(int, user)): {int(item) for item in items}
        for user, items in history.groupby("internal_user_id")
        .internal_product_id.apply(set)
        .items()
    }
    purchase_target = target[target.event_type == "purchase"]
    target_sets = purchase_target.groupby("internal_user_id").internal_product_id.apply(set)
    truth = {
        int(cast(int, user)): {int(item) for item in items}
        - history_sets.get(int(cast(int, user)), set())
        for user, items in target_sets.items()
    }
    truth = {user: items for user, items in truth.items() if user > 0 and items}

    purchases = history[history.event_type == "purchase"].sort_values(
        ["event_ts", "event_id"], kind="stable"
    )
    contexts = {
        int(cast(int, user)): int(item)
        for user, item in purchases.groupby("internal_user_id").internal_product_id.last().items()
    }
    scoring_users = np.arange(1, snapshot.manifest.num_users + 1, dtype=np.int64)
    eligible = np.asarray(sorted(truth), dtype=np.int64)
    # Personas are intentionally prepared for every scoring user.  This lets
    # training hard-cache rows include users without novel validation truth.
    personas = {
        int(user): int(
            snapshot.persona_map.get(
                snapshot.raw_user_map[int(user)],
                self_persona_default(snapshot),
            )
        )
        for user in scoring_users
    }
    raw_product_ids = np.asarray(
        [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
        dtype=np.int64,
    )
    candidate_item_ids = np.arange(snapshot.manifest.num_items, dtype=np.int64)
    cold = np.asarray(snapshot.cold_item_ids, dtype=np.int64)
    warm_candidate_item_ids = candidate_item_ids[~np.isin(candidate_item_ids, cold)]
    # The frame and arrays are immutable inputs to all downstream evaluation.
    history = history.copy(deep=True)
    history.attrs["prepared_read_only"] = True
    for array in (
        scoring_users,
        eligible,
        raw_product_ids,
        candidate_item_ids,
        warm_candidate_item_ids,
    ):
        array.setflags(write=False)
    return PreparedEvaluationSplit(
        split=split,
        history_events=history,
        scoring_users=scoring_users,
        eligible_users=eligible,
        organic_novel_truth=truth,
        seen_items=history_sets,
        latest_prior_purchase_contexts=contexts,
        personas=personas,
        raw_product_ids=raw_product_ids,
        candidate_item_ids=candidate_item_ids,
        warm_candidate_item_ids=warm_candidate_item_ids,
    )


def self_persona_default(snapshot: Snapshot) -> int:
    """Return the configured unknown persona without coupling to Settings."""
    if snapshot.persona_map:
        return max(snapshot.persona_map.values(), default=0)
    return 0


def _build_report(
    snapshot: Snapshot,
    prepared: PreparedEvaluationSplit,
    variant: ModelVariant,
    k: int,
    rows: list[tuple[int, float, float, float, tuple[int, ...]]],
) -> EvaluationResult:
    rows.sort(key=lambda row: row[0])
    user_ids = np.asarray([row[0] for row in rows], dtype=np.int64)
    hrs = np.asarray([row[1] for row in rows], dtype=np.float64)
    ndcgs = np.asarray([row[2] for row in rows], dtype=np.float64)
    aucs = np.asarray([row[3] for row in rows], dtype=np.float64)
    return EvaluationResult(
        report=EvaluationReport(
            run_id=snapshot.manifest.artifact_id,
            split=prepared.split,
            variant=variant,
            num_total_users=int(snapshot.manifest.num_users),
            num_eligible_users=len(rows),
            num_users_without_novel_purchase=int(snapshot.manifest.num_users) - len(rows),
            num_catalog_items=int(snapshot.manifest.num_items),
            hr_at_k=float(hrs.mean()) if len(hrs) else 0.0,
            ndcg_at_k=float(ndcgs.mean()) if len(ndcgs) else 0.0,
            gauc=float(aucs.mean()) if len(aucs) else 0.5,
            k=k,
        ),
        user_ids=user_ids,
        per_user_hr=hrs,
        per_user_ndcg=ndcgs,
        per_user_gauc=aucs,
        top_k_by_user={row[0]: row[4] for row in rows},
    )


def _metric_row(
    user: int,
    scores: np.ndarray,
    prepared: PreparedEvaluationSplit,
    k: int,
) -> tuple[int, float, float, float, tuple[int, ...]]:
    positives = prepared.organic_novel_truth[user]
    masked = np.asarray(scores, dtype=np.float64).copy()
    if masked.shape != prepared.candidate_item_ids.shape or not np.isfinite(masked).all():
        raise DataIntegrityError("full-catalog score vector has invalid shape or values")
    seen = prepared.seen_items.get(user, set())
    if seen:
        masked[np.fromiter(seen, dtype=np.int64)] = -np.inf
    ranking = ranking_metrics(
        scores=masked,
        positive_indices=positives,
        raw_product_ids=prepared.raw_product_ids,
        k=k,
    )
    negative_ids = np.asarray(
        [
            item
            for item in prepared.candidate_item_ids
            if int(item) not in positives and int(item) not in seen
        ],
        dtype=np.int64,
    )
    positive_ids = np.fromiter(positives, dtype=np.int64)
    auc = user_auc(masked[positive_ids], masked[negative_ids])
    return (
        user,
        ranking.hit,
        ranking.ndcg,
        float(auc if auc is not None else 0.5),
        tuple(int(item) for item in ranking.ranked_indices),
    )


class FullCatalogEvaluator:
    def __init__(self, settings: Settings, embeddings: np.ndarray, rule_store: RuleStore) -> None:
        self.settings = settings
        self.embeddings = np.array(embeddings, dtype=np.float32, copy=True)
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.semantic_vectors = self.embeddings / np.maximum(norms, np.finfo(np.float32).eps)
        self.rule_store = rule_store

    def _prepare_model_catalog(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        device: torch.device,
    ) -> torch.Tensor:
        if self.embeddings.shape != (snapshot.manifest.num_items, self.settings.model.sbert_dim):
            raise DataIntegrityError("embedding artifact does not match snapshot")
        catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
        item_ids = torch.arange(snapshot.manifest.num_items, dtype=torch.int64, device=device)
        cold_mask = torch.zeros(snapshot.manifest.num_items, dtype=torch.bool, device=device)
        if snapshot.cold_item_ids:
            cold_mask[torch.tensor(snapshot.cold_item_ids, dtype=torch.int64, device=device)] = True
        return model.encode_items(
            torch.from_numpy(self.embeddings).to(device),
            torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)).to(device),
            torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(device),
            item_idx=item_ids,
            is_cold=cold_mask,
        )

    def _score_neural_batch(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        prepared: PreparedEvaluationSplit,
        item_vectors: torch.Tensor,
        users: np.ndarray,
        device: torch.device,
        *,
        user_profiles: torch.Tensor,
        noisy: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        user_ids = torch.from_numpy(np.array(users, dtype=np.int64, copy=True)).to(device)
        personas = np.asarray([prepared.personas[int(user)] for user in users], dtype=np.int64)
        if noisy:
            personas = np.asarray(
                [
                    0
                    if int(persona) >= self.settings.data.num_personas
                    else (int(persona) + 1) % self.settings.data.num_personas
                    for persona in personas
                ],
                dtype=np.int64,
            )
        profile = user_profiles[user_ids]
        if not self.settings.train.use_history_profiles:
            profile = torch.zeros_like(profile)
        present = torch.linalg.vector_norm(profile, dim=-1) > 0
        user_vectors = model.encode_user(
            user_ids,
            torch.from_numpy(personas).to(device),
            history_vector=profile,
            history_present=present,
        )
        deep = (torch.matmul(user_vectors, item_vectors.T) / model._temperature).cpu().numpy()
        contexts = np.asarray(
            [prepared.latest_prior_purchase_contexts.get(int(user), -1) for user in users],
            dtype=np.int64,
        )
        candidates = prepared.candidate_item_ids
        candidate_matrix = np.broadcast_to(candidates, (len(users), len(candidates)))
        wide_values, rule_present = self.rule_store.batch_lookup(contexts, candidate_matrix)
        wide = (
            model.wide_layer(
                torch.from_numpy(wide_values).to(device),
                torch.from_numpy(rule_present).to(device),
            )
            .cpu()
            .numpy()
        )
        hybrid = deep + wide
        return np.asarray(deep), np.asarray(wide), np.asarray(hybrid)

    def evaluate(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        prepared_split: PreparedEvaluationSplit,
        k: int,
        variant: ModelVariant,
        device: torch.device | str,
    ) -> EvaluationResult:
        return self.evaluate_variants(
            model,
            snapshot,
            prepared_split=prepared_split,
            k=k,
            variants=(variant,),
            device=device,
        )[variant]

    @torch.no_grad()
    def evaluate_variants(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        prepared_split: PreparedEvaluationSplit,
        k: int,
        variants: tuple[ModelVariant, ...],
        device: torch.device | str,
    ) -> dict[ModelVariant, EvaluationResult]:
        supported = {
            ModelVariant.HYBRID,
            ModelVariant.DEEP_ONLY,
            ModelVariant.WIDE_ONLY,
            ModelVariant.NOISY_HYBRID,
        }
        if not variants or any(variant not in supported for variant in variants):
            raise ValueError("neural evaluator received a non-neural variant")
        if prepared_split.split not in (SplitName.VAL, SplitName.TEST):
            raise ValueError("prepared split must be validation or test")
        device = torch.device(device)
        model = model.to(device).eval()
        item_vectors = self._prepare_model_catalog(model, snapshot, device)
        user_profiles = build_user_profile_vectors(
            model,
            snapshot,
            item_vectors,
            prepared_split.history_events,
            max_history_items=self.settings.train.max_history_items,
            device=device,
        )
        if not self.settings.train.use_history_profiles:
            user_profiles.zero_()
        eligible = prepared_split.eligible_users
        swap_count = round(0.10 * len(eligible))
        ordered = sorted(
            (
                hashlib.sha256(f"{self.settings.train.seed}:{int(user)}".encode()).hexdigest(),
                int(user),
            )
            for user in eligible
        )
        swap_users = {user for _, user in ordered[:swap_count]}
        rows: dict[ModelVariant, list[tuple[int, float, float, float, tuple[int, ...]]]] = {
            variant: [] for variant in variants
        }
        batch_size = self.settings.train.validation_user_batch_size
        for offset in range(0, len(eligible), batch_size):
            users = eligible[offset : offset + batch_size]
            deep, wide, hybrid = self._score_neural_batch(
                model,
                snapshot,
                prepared_split,
                item_vectors,
                users,
                device,
                user_profiles=user_profiles,
            )
            noisy = None
            if ModelVariant.NOISY_HYBRID in variants:
                noisy_deep, _, _ = self._score_neural_batch(
                    model,
                    snapshot,
                    prepared_split,
                    item_vectors,
                    users,
                    device,
                    noisy=True,
                    user_profiles=user_profiles,
                )
                noisy = noisy_deep + wide
            for row_index, user_value in enumerate(users):
                user = int(user_value)
                values = {
                    ModelVariant.DEEP_ONLY: deep[row_index],
                    ModelVariant.WIDE_ONLY: wide[row_index],
                    ModelVariant.HYBRID: hybrid[row_index],
                    ModelVariant.NOISY_HYBRID: (
                        noisy[row_index]
                        if noisy is not None and user in swap_users
                        else hybrid[row_index]
                    ),
                }
                for variant in variants:
                    rows[variant].append(_metric_row(user, values[variant], prepared_split, k))
        return {
            variant: _build_report(snapshot, prepared_split, variant, k, variant_rows)
            for variant, variant_rows in rows.items()
        }

    @torch.no_grad()
    def evaluate_training_epoch(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        prepared_split: PreparedEvaluationSplit,
        k: int,
        device: torch.device | str,
    ) -> TrainingValidationPass:
        if prepared_split.split is not SplitName.VAL:
            raise ValueError("training validation requires a validation prepared split")
        device = torch.device(device)
        model = model.to(device).eval()
        item_vectors = self._prepare_model_catalog(model, snapshot, device)
        user_profiles = build_user_profile_vectors(
            model,
            snapshot,
            item_vectors,
            prepared_split.history_events,
            max_history_items=self.settings.train.max_history_items,
            device=device,
        )
        if not self.settings.train.use_history_profiles:
            user_profiles.zero_()
        variants = (ModelVariant.HYBRID, ModelVariant.DEEP_ONLY, ModelVariant.WIDE_ONLY)
        rows: dict[ModelVariant, list[tuple[int, float, float, float, tuple[int, ...]]]] = {
            variant: [] for variant in variants
        }
        cache_width = min(64, len(prepared_split.warm_candidate_item_ids))
        if cache_width <= 0:
            raise DataIntegrityError("warm catalog is empty")
        cache = np.full((snapshot.manifest.num_users + 1, cache_width), -1, dtype=np.int32)
        sums = {ModelVariant.DEEP_ONLY: 0.0, ModelVariant.WIDE_ONLY: 0.0, ModelVariant.HYBRID: 0.0}
        counts = {variant: 0 for variant in sums}
        batch_size = self.settings.train.validation_user_batch_size
        eligible = set(int(user) for user in prepared_split.eligible_users)
        for offset in range(0, len(prepared_split.scoring_users), batch_size):
            users = prepared_split.scoring_users[offset : offset + batch_size]
            deep, wide, hybrid = self._score_neural_batch(
                model,
                snapshot,
                prepared_split,
                item_vectors,
                users,
                device,
                user_profiles=user_profiles,
            )
            values = {
                ModelVariant.DEEP_ONLY: deep,
                ModelVariant.WIDE_ONLY: wide,
                ModelVariant.HYBRID: hybrid,
            }
            for variant, logits in values.items():
                if not np.isfinite(logits).all():
                    raise DataIntegrityError(f"non-finite {variant.value} logits")
                sums[variant] += float(np.square(logits, dtype=np.float64).sum())
                counts[variant] += int(logits.size)
            for row_index, user_value in enumerate(users):
                user = int(user_value)
                deep_scores = np.asarray(deep[row_index], dtype=np.float64).copy()
                seen = prepared_split.seen_items.get(user, set())
                if seen:
                    deep_scores[np.fromiter(seen, dtype=np.int64)] = -np.inf
                candidate = prepared_split.warm_candidate_item_ids
                candidate = candidate[~np.isin(candidate, np.fromiter(seen, dtype=np.int64))]
                if len(candidate) < cache_width:
                    raise DataIntegrityError(
                        "insufficient warm unseen items for hard-negative cache"
                    )
                order = np.lexsort(
                    (prepared_split.raw_product_ids[candidate], -deep_scores[candidate])
                )[:cache_width]
                selected = candidate[order]
                if len(np.unique(selected)) != cache_width or np.any(selected < 0):
                    raise DataIntegrityError("invalid model-hard cache row")
                cache[user] = selected.astype(np.int32)
                if user in eligible:
                    for variant, logits in values.items():
                        rows[variant].append(
                            _metric_row(user, logits[row_index], prepared_split, k)
                        )
        if np.any(cache[1:] < 0):
            raise DataIntegrityError("model-hard cache has an unpopulated scoring-user row")
        reports = {
            variant: _build_report(snapshot, prepared_split, variant, k, variant_rows)
            for variant, variant_rows in rows.items()
        }
        return TrainingValidationPass(
            variants=reports,
            model_hard_cache=cache,
            deep_logit_rms=float(
                np.sqrt(sums[ModelVariant.DEEP_ONLY] / counts[ModelVariant.DEEP_ONLY])
            ),
            wide_logit_rms=float(
                np.sqrt(sums[ModelVariant.WIDE_ONLY] / counts[ModelVariant.WIDE_ONLY])
            ),
            hybrid_logit_rms=float(
                np.sqrt(sums[ModelVariant.HYBRID] / counts[ModelVariant.HYBRID])
            ),
        )

    def evaluate_external_scores(
        self,
        snapshot: Snapshot,
        *,
        prepared_split: PreparedEvaluationSplit,
        variant: ModelVariant,
        scorer: ExternalBatchScorer,
        k: int,
    ) -> EvaluationResult:
        if not callable(scorer):
            raise TypeError("external scorer must be callable")
        rows: list[tuple[int, float, float, float, tuple[int, ...]]] = []
        candidates = prepared_split.candidate_item_ids
        batch_size = self.settings.train.validation_user_batch_size
        for offset in range(0, len(prepared_split.eligible_users), batch_size):
            users = prepared_split.eligible_users[offset : offset + batch_size]
            batch_scores = np.asarray(scorer(users, candidates))
            if batch_scores.shape != (len(users), len(candidates)):
                raise DataIntegrityError("external scorer returned invalid score shape")
            if not np.isfinite(batch_scores).all():
                raise DataIntegrityError("external scorer returned non-finite values")
            for row_index, user_value in enumerate(users):
                rows.append(
                    _metric_row(int(user_value), batch_scores[row_index], prepared_split, k)
                )
        return _build_report(snapshot, prepared_split, variant, k, rows)


__all__ = [
    "EvaluationReport",
    "EvaluationResult",
    "ExternalBatchScorer",
    "FullCatalogEvaluator",
    "PreparedEvaluationSplit",
    "TrainingValidationPass",
    "prepare_split",
]
