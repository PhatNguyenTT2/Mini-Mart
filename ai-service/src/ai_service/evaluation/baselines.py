"""Seven independent full-catalog benchmark methods."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from scipy import sparse

from ai_service.config import Settings
from ai_service.contracts import EvaluationReport, ModelVariant, SplitName
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import EvaluationResult, FullCatalogEvaluator
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class BaselineComparisonReport:
    results: dict[str, EvaluationResult]
    random_seed_results: tuple[EvaluationResult, ...]

    @property
    def baselines(self) -> dict[str, EvaluationReport]:
        reports = {name: result.report for name, result in self.results.items()}
        reports["Random Base (Sanity Check)"] = _mean_report(
            [result.report for result in self.random_seed_results]
        )
        return reports


def _history(snapshot: Snapshot, split: SplitName) -> pd.DataFrame:
    if split is SplitName.TEST:
        return pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True)
    return snapshot.train_df


def _stateless_random_scores(seed: int, user_id: int, raw_item_ids: np.ndarray) -> np.ndarray:
    values = raw_item_ids.astype(np.uint64)
    values = values ^ np.uint64(seed * 0x9E3779B1) ^ np.uint64(user_id * 0x85EBCA77)
    values ^= values >> np.uint64(30)
    values *= np.uint64(0xBF58476D1CE4E5B9)
    values ^= values >> np.uint64(27)
    values *= np.uint64(0x94D049BB133111EB)
    values ^= values >> np.uint64(31)
    return ((values >> np.uint64(11)).astype(np.float64) / float(1 << 53)).astype(np.float32)


def _mean_report(reports: list[EvaluationReport]) -> EvaluationReport:
    first = reports[0]
    return first.model_copy(
        update={
            "hr_at_k": float(np.mean([report.hr_at_k for report in reports])),
            "ndcg_at_k": float(np.mean([report.ndcg_at_k for report in reports])),
            "gauc": float(np.mean([report.gauc for report in reports])),
        }
    )


def run_seven_way_baselines(
    model: HybridTwoTowerModel,
    snapshot: Snapshot,
    *,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    split: SplitName,
    settings: Settings,
    device: str | torch.device,
) -> BaselineComparisonReport:
    evaluator = FullCatalogEvaluator(settings, embeddings, rule_store)
    results: dict[str, EvaluationResult] = {}
    neural = evaluator.evaluate_variants(
        model,
        snapshot,
        split=split,
        k=settings.eval.k,
        variants=(
            ModelVariant.WIDE_ONLY,
            ModelVariant.DEEP_ONLY,
            ModelVariant.HYBRID,
            ModelVariant.NOISY_HYBRID,
        ),
        device=device,
    )
    results["Rule-based Apriori"] = neural[ModelVariant.WIDE_ONLY]
    results["Deep-Only Two-Tower"] = neural[ModelVariant.DEEP_ONLY]
    results["Proposed Hybrid (Ours)"] = neural[ModelVariant.HYBRID]
    results["Noisy 10% Hybrid"] = neural[ModelVariant.NOISY_HYBRID]

    history = _history(snapshot, split)
    eligible_users = sorted(
        set(
            snapshot.val_df.internal_user_id
            if split is SplitName.VAL
            else snapshot.test_df.internal_user_id
        )
    )
    normalized_embeddings = embeddings / np.maximum(
        np.linalg.norm(embeddings, axis=1, keepdims=True), np.finfo(np.float32).eps
    )
    centroid_scores: dict[int, np.ndarray] = {}
    for user in eligible_users:
        items = history.loc[history.internal_user_id == user, "internal_product_id"].to_numpy(
            np.int64
        )
        if len(items):
            centroid = normalized_embeddings[np.unique(items)].mean(axis=0)
            centroid /= max(float(np.linalg.norm(centroid)), np.finfo(np.float32).eps)
            centroid_scores[int(user)] = normalized_embeddings @ centroid
        else:
            centroid_scores[int(user)] = np.zeros(snapshot.manifest.num_items, dtype=np.float32)
    results["SBERT User Centroid"] = evaluator.evaluate_scores(
        snapshot,
        split=split,
        variant=ModelVariant.SBERT_CENTROID,
        scores_by_user=centroid_scores,
        k=settings.eval.k,
    )

    train_pairs = snapshot.train_df[["internal_user_id", "internal_product_id"]].drop_duplicates()
    matrix = sparse.csr_matrix(
        (
            np.ones(len(train_pairs), dtype=np.float32),
            (
                train_pairs.internal_user_id.to_numpy(np.int64) - 1,
                train_pairs.internal_product_id.to_numpy(np.int64),
            ),
        ),
        shape=(snapshot.manifest.num_users, snapshot.manifest.num_items),
    )
    similarity = (matrix.T @ matrix).tocsr()
    similarity.setdiag(0)
    similarity.eliminate_zeros()
    cf_scores: dict[int, np.ndarray] = {}
    for user in eligible_users:
        items = history.loc[history.internal_user_id == user, "internal_product_id"].to_numpy(
            np.int64
        )
        cf_scores[int(user)] = (
            np.asarray(similarity[np.unique(items)].sum(axis=0)).ravel().astype(np.float32)
            if len(items)
            else np.zeros(snapshot.manifest.num_items, dtype=np.float32)
        )
    results["Item-Item CF"] = evaluator.evaluate_scores(
        snapshot,
        split=split,
        variant=ModelVariant.ITEM_CF,
        scores_by_user=cf_scores,
        k=settings.eval.k,
    )

    raw_ids = np.asarray(
        [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
        dtype=np.uint64,
    )
    random_results: list[EvaluationResult] = []
    for seed in range(settings.eval.random_seeds):
        scores = {
            int(user): _stateless_random_scores(seed, int(user), raw_ids) for user in eligible_users
        }
        random_results.append(
            evaluator.evaluate_scores(
                snapshot,
                split=split,
                variant=ModelVariant.RANDOM,
                scores_by_user=scores,
                k=settings.eval.k,
            )
        )
    return BaselineComparisonReport(results, tuple(random_results))
