"""Eight independent full-catalog benchmark methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import torch
from scipy import sparse

from ai_service.config import Settings
from ai_service.contracts import EvaluationReport, ModelVariant
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import (
    EvaluationResult,
    ExternalBatchScorer,
    FullCatalogEvaluator,
    PreparedEvaluationSplit,
)
from ai_service.evaluation.persona import prepare_persona_baseline, score_persona_batch
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class BaselineComparisonReport:
    persona_only: EvaluationResult
    apriori_only: EvaluationResult
    sbert_centroid: EvaluationResult
    item_cf: EvaluationResult
    deep_only: EvaluationResult
    hybrid: EvaluationResult
    noisy_hybrid: EvaluationResult
    random_seed_results: tuple[EvaluationResult, ...]

    @property
    def baselines(self) -> dict[str, EvaluationReport]:
        return {
            "persona_only": self.persona_only.report,
            "apriori_only": self.apriori_only.report,
            "sbert_centroid": self.sbert_centroid.report,
            "item_cf": self.item_cf.report,
            "deep_only": self.deep_only.report,
            "hybrid": self.hybrid.report,
            "noisy_hybrid": self.noisy_hybrid.report,
            "random": _mean_report([result.report for result in self.random_seed_results]),
        }


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


def evaluate_random_baselines(
    *,
    evaluator: FullCatalogEvaluator,
    snapshot: Snapshot,
    prepared_split: PreparedEvaluationSplit,
    settings: Settings,
) -> tuple[EvaluationResult, ...]:
    """Evaluate the exact stateless Random seeds used by every release comparison."""
    raw_ids = np.asarray(
        [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
        dtype=np.uint64,
    )
    results: list[EvaluationResult] = []
    for seed in range(settings.eval.random_seeds):

        def random_scorer(
            users: np.ndarray, _candidates: np.ndarray, *, _seed: int = seed
        ) -> np.ndarray:
            return np.stack([_stateless_random_scores(_seed, int(user), raw_ids) for user in users])

        results.append(
            evaluator.evaluate_external_scores(
                snapshot,
                prepared_split=prepared_split,
                variant=ModelVariant.RANDOM,
                scorer=cast(ExternalBatchScorer, random_scorer),
                k=settings.eval.k,
            )
        )
    return tuple(results)


def run_full_catalog_comparison(
    *,
    hybrid_model: HybridTwoTowerModel,
    deep_model: HybridTwoTowerModel,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    settings: Settings,
    device: str | torch.device,
    prepared_split: PreparedEvaluationSplit,
) -> BaselineComparisonReport:
    evaluator = FullCatalogEvaluator(settings, embeddings, rule_store)
    # 1. Neural models (Hybrid, Deep control, Noisy Hybrid)
    hybrid_eval = evaluator.evaluate_variants(
        hybrid_model,
        snapshot,
        k=settings.eval.k,
        variants=(ModelVariant.HYBRID, ModelVariant.NOISY_HYBRID),
        device=device,
        prepared_split=prepared_split,
    )
    deep_eval = evaluator.evaluate_variants(
        deep_model,
        snapshot,
        k=settings.eval.k,
        variants=(ModelVariant.DEEP_ONLY,),
        device=device,
        prepared_split=prepared_split,
    )

    hybrid_result = hybrid_eval[ModelVariant.HYBRID]
    noisy_hybrid_result = hybrid_eval[ModelVariant.NOISY_HYBRID]
    deep_result = deep_eval[ModelVariant.DEEP_ONLY]

    history = prepared_split.history_events

    persona = prepare_persona_baseline(snapshot, prepared_split)

    def persona_scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        return score_persona_batch(persona, users, candidates)

    persona_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared_split,
        variant=ModelVariant.PERSONA_ONLY,
        scorer=persona_scorer,
        k=settings.eval.k,
    )

    # 2. Raw Apriori Lift Baseline
    def apriori_scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        contexts = np.asarray(
            [prepared_split.latest_prior_purchase_contexts.get(int(user), -1) for user in users],
            dtype=np.int64,
        )
        raw_lift, rule_pres = rule_store.batch_raw_lift(
            contexts, np.broadcast_to(candidates, (len(users), len(candidates)))
        )
        return np.where(rule_pres, raw_lift, 0.0).astype(np.float32)

    apriori_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared_split,
        variant=ModelVariant.WIDE_ONLY,
        scorer=apriori_scorer,
        k=settings.eval.k,
    )

    # 3. SBERT User Centroid (ORGANIC PURCHASES ONLY)
    organic_purchases = history[history.event_type == "purchase"]
    normalized_embeddings = embeddings / np.maximum(
        np.linalg.norm(embeddings, axis=1, keepdims=True), np.finfo(np.float32).eps
    )

    centroids = np.zeros(
        (snapshot.manifest.num_users + 1, normalized_embeddings.shape[1]), dtype=np.float32
    )
    for user, group in organic_purchases.groupby("internal_user_id"):
        items = np.unique(group.internal_product_id.to_numpy(np.int64))
        if len(items):
            centroid = normalized_embeddings[items].mean(axis=0)
            centroids[int(cast(int, user))] = centroid / max(
                float(np.linalg.norm(centroid)), np.finfo(np.float32).eps
            )

    def centroid_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        return np.asarray(centroids[users] @ normalized_embeddings.T, dtype=np.float32)

    sbert_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared_split,
        variant=ModelVariant.SBERT_CENTROID,
        scorer=cast(ExternalBatchScorer, centroid_scorer),
        k=settings.eval.k,
    )

    # 4. Item-Item CF (ORGANIC PURCHASES ONLY)
    train_purchases = organic_purchases
    train_pairs = train_purchases[["internal_user_id", "internal_product_id"]].drop_duplicates()
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

    def cf_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        return np.asarray(
            (matrix[np.asarray(users, dtype=np.int64) - 1] @ similarity).toarray(),
            dtype=np.float32,
        )

    cf_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared_split,
        variant=ModelVariant.ITEM_CF,
        scorer=cast(ExternalBatchScorer, cf_scorer),
        k=settings.eval.k,
    )

    # 5. Stateless Random Baseline
    random_results = evaluate_random_baselines(
        evaluator=evaluator,
        snapshot=snapshot,
        prepared_split=prepared_split,
        settings=settings,
    )

    return BaselineComparisonReport(
        persona_only=persona_result,
        apriori_only=apriori_result,
        sbert_centroid=sbert_result,
        item_cf=cf_result,
        deep_only=deep_result,
        hybrid=hybrid_result,
        noisy_hybrid=noisy_hybrid_result,
        random_seed_results=random_results,
    )
