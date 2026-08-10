"""Zero-sampling full-catalog evaluator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import cast

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


@dataclass(frozen=True)
class EvaluationResult:
    report: EvaluationReport
    user_ids: np.ndarray
    per_user_hr: np.ndarray
    per_user_ndcg: np.ndarray
    per_user_gauc: np.ndarray
    top_k_by_user: dict[int, tuple[int, ...]]


def _history_and_truth(
    snapshot: Snapshot, split: SplitName
) -> tuple[pd.DataFrame, dict[int, set[int]]]:
    if split is SplitName.VAL:
        history = snapshot.train_df
        target = snapshot.val_df
    elif split is SplitName.TEST:
        history = pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True)
        target = snapshot.test_df
    else:
        raise ValueError("full-catalog evaluation supports validation or test only")
    history = filter_event_origin(history)
    target = filter_event_origin(target)
    history_items = history.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
    purchase_target = target[target.event_type == "purchase"]
    target_items = purchase_target.groupby("internal_user_id").internal_product_id.apply(set)
    truth = {
        cast(int, user): {int(item) for item in items}
        - {int(item) for item in history_items.get(user, set())}
        for user, items in target_items.items()
    }
    return history, {user: items for user, items in truth.items() if items}


class FullCatalogEvaluator:
    def __init__(
        self,
        settings: Settings,
        embeddings: np.ndarray,
        rule_store: RuleStore,
    ) -> None:
        self.settings = settings
        # Snapshot artifacts are loaded as read-only memmaps.  Torch requires
        # writable NumPy storage even when the tensor is only read from.
        self.embeddings = np.array(embeddings, dtype=np.float32, copy=True)
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.semantic_vectors = self.embeddings / np.maximum(norms, np.finfo(np.float32).eps)
        self.rule_store = rule_store

    def evaluate_scores(
        self,
        snapshot: Snapshot,
        *,
        split: SplitName,
        variant: ModelVariant,
        scores_by_user: dict[int, np.ndarray],
        k: int,
    ) -> EvaluationResult:
        history, truth = _history_and_truth(snapshot, split)
        total_users = int(snapshot.manifest.num_users)
        raw_product_ids = np.asarray(
            [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
            dtype=np.int64,
        )
        history_sets = history.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
        user_ids = np.asarray(sorted(truth), dtype=np.int64)
        hrs: list[float] = []
        ndcgs: list[float] = []
        aucs: list[float] = []
        top_k_by_user: dict[int, tuple[int, ...]] = {}
        for user in user_ids:
            if int(user) not in scores_by_user:
                raise DataIntegrityError(f"scores missing for eligible user {user}")
            scores = np.asarray(scores_by_user[int(user)], dtype=np.float64).copy()
            if scores.shape != (snapshot.manifest.num_items,) or not np.isfinite(scores).all():
                raise DataIntegrityError("full-catalog score vector has invalid shape or values")
            positives = truth[int(user)]
            seen = {int(item) for item in history_sets.get(int(user), set())}
            if seen:
                scores[np.fromiter(seen, dtype=np.int64)] = -np.inf
            ranking = ranking_metrics(
                scores=scores,
                positive_indices=positives,
                raw_product_ids=raw_product_ids,
                k=k,
            )
            negatives = np.asarray(
                [item for item in range(len(scores)) if item not in positives and item not in seen],
                dtype=np.int64,
            )
            positive = np.fromiter(positives, dtype=np.int64)
            auc = user_auc(scores[positive], scores[negatives])
            hrs.append(ranking.hit)
            ndcgs.append(ranking.ndcg)
            aucs.append(float(auc if auc is not None else 0.5))
            top_k_by_user[int(user)] = tuple(int(item) for item in ranking.ranked_indices)
        report = EvaluationReport(
            run_id=snapshot.manifest.artifact_id,
            split=split,
            variant=variant,
            num_total_users=total_users,
            num_eligible_users=len(user_ids),
            num_users_without_novel_purchase=total_users - len(user_ids),
            num_catalog_items=snapshot.manifest.num_items,
            hr_at_k=float(np.mean(hrs)) if hrs else 0.0,
            ndcg_at_k=float(np.mean(ndcgs)) if ndcgs else 0.0,
            gauc=float(np.mean(aucs)) if aucs else 0.5,
            k=k,
        )
        return EvaluationResult(
            report=report,
            user_ids=user_ids,
            per_user_hr=np.asarray(hrs, dtype=np.float64),
            per_user_ndcg=np.asarray(ndcgs, dtype=np.float64),
            per_user_gauc=np.asarray(aucs, dtype=np.float64),
            top_k_by_user=top_k_by_user,
        )

    @torch.no_grad()
    def evaluate(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        split: SplitName,
        k: int,
        variant: ModelVariant,
        device: torch.device | str,
    ) -> EvaluationResult:
        return self.evaluate_variants(
            model,
            snapshot,
            split=split,
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
        split: SplitName,
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
        if self.embeddings.shape != (
            snapshot.manifest.num_items,
            self.settings.model.sbert_dim,
        ):
            raise DataIntegrityError("embedding artifact does not match snapshot")
        device = torch.device(device)
        model = model.to(device).eval()
        catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
        item_ids = torch.arange(snapshot.manifest.num_items, dtype=torch.int64, device=device)
        cold_mask = torch.zeros(snapshot.manifest.num_items, dtype=torch.bool, device=device)
        if snapshot.cold_item_ids:
            cold_mask[torch.tensor(snapshot.cold_item_ids, dtype=torch.int64, device=device)] = True
        item_vectors = model.encode_items(
            torch.from_numpy(self.embeddings).to(device),
            torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)).to(device),
            torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(device),
            item_idx=item_ids,
            is_cold=cold_mask,
        )
        history, truth = _history_and_truth(snapshot, split)
        user_profiles = build_user_profile_vectors(
            model,
            snapshot,
            item_vectors,
            history,
            max_history_items=self.settings.train.max_history_items,
            device=device,
        )
        if not self.settings.train.use_history_profiles:
            user_profiles.zero_()
        eligible = sorted(truth)
        if history.empty:
            contexts: dict[int, int] = {}
        else:
            purchases = history[history.event_type == "purchase"].sort_values(
                ["event_ts", "event_id"], kind="stable"
            )
            contexts = {
                cast(int, user): int(item)
                for user, item in purchases.groupby("internal_user_id")
                .internal_product_id.last()
                .items()
            }
        candidates = np.arange(snapshot.manifest.num_items, dtype=np.int64)
        cold_candidates = np.asarray(snapshot.cold_item_ids, dtype=np.int64)
        scores_by_variant: dict[ModelVariant, dict[int, np.ndarray]] = {
            variant: {} for variant in variants
        }
        batch_size = self.settings.train.validation_user_batch_size
        for offset in range(0, len(eligible), batch_size):
            batch_users = eligible[offset : offset + batch_size]
            raw_users = [snapshot.raw_user_map[user] for user in batch_users]
            personas = [
                snapshot.persona_map.get(user, self.settings.data.num_personas)
                for user in raw_users
            ]
            context_ids = np.asarray(
                [contexts.get(user, -1) for user in batch_users], dtype=np.int64
            )
            candidate_matrix = np.broadcast_to(candidates, (len(batch_users), len(candidates)))
            wide_values, rule_present = self.rule_store.batch_lookup(context_ids, candidate_matrix)
            user_tensor = torch.tensor(batch_users, dtype=torch.int64, device=device)
            profile_batch = user_profiles[user_tensor]
            persona_tensor = torch.tensor(personas, dtype=torch.int64, device=device)
            history_present = torch.linalg.vector_norm(profile_batch, dim=-1) > 0

            user_vectors = model.encode_user(
                user_tensor,
                persona_tensor,
                history_vector=profile_batch,
                history_present=history_present,
            )
            deep = (torch.matmul(user_vectors, item_vectors.T) / model._temperature).cpu().numpy()
            wide = (
                model.wide_layer(
                    torch.from_numpy(wide_values).to(device),
                    torch.from_numpy(rule_present).to(device),
                )
                .cpu()
                .numpy()
            )

            # Check persona swap for NOISY_HYBRID variant
            noisy_user_vectors = None
            if ModelVariant.NOISY_HYBRID in variants:
                swapped_personas = list(personas)
                for i, u in enumerate(batch_users):
                    h = int(hashlib.md5(f"{self.settings.train.seed}_{u}".encode()).hexdigest(), 16)
                    if h % 10 == 0:
                        swapped_personas[i] = (personas[i] + 1) % self.settings.data.num_personas
                noisy_user_vectors = model.encode_user(
                    user_tensor,
                    torch.tensor(swapped_personas, dtype=torch.int64, device=device),
                    history_vector=profile_batch,
                    history_present=history_present,
                )
            noisy_deep = (
                (torch.matmul(noisy_user_vectors, item_vectors.T) / model._temperature).cpu().numpy()
                if noisy_user_vectors is not None
                else None
            )

            for variant in variants:
                if variant is ModelVariant.DEEP_ONLY:
                    logits = deep.copy()
                elif variant is ModelVariant.WIDE_ONLY:
                    logits = wide.copy()
                elif variant is ModelVariant.NOISY_HYBRID and noisy_deep is not None:
                    logits = noisy_deep + wide
                else:
                    logits = deep + wide
                for row_index, user in enumerate(batch_users):
                    scores_by_variant[variant][user] = logits[row_index]
        return {
            variant: self.evaluate_scores(
                snapshot,
                split=split,
                variant=variant,
                scores_by_user=scores_by_variant[variant],
                k=k,
            )
            for variant in variants
        }


__all__ = ["EvaluationReport", "EvaluationResult", "FullCatalogEvaluator"]
