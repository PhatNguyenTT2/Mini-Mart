"""Cheap streaming probes separating data signal from model optimization."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from scipy import sparse

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.rules import RuleArtifact, RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import (
    ExternalBatchScorer,
    FullCatalogEvaluator,
    prepare_split,
)
from ai_service.evaluation.metrics import paired_bootstrap_delta
from ai_service.evaluation.persona import prepare_persona_baseline, score_persona_batch


def _metrics(result: Any) -> dict[str, float | int]:
    report = result.report
    return {
        "eligible_users": int(report.num_eligible_users),
        "hr_at_k": float(report.hr_at_k),
        "ndcg_at_k": float(report.ndcg_at_k),
        "gauc": float(report.gauc),
    }


def _paired_evidence(candidate: Any, baseline: Any, settings: Settings) -> dict[str, Any]:
    if not np.array_equal(candidate.user_ids, baseline.user_ids):
        raise ValueError("paired probe results must use the same eligible user IDs")
    gauc = paired_bootstrap_delta(
        candidate.per_user_gauc,
        baseline.per_user_gauc,
        samples=settings.eval.bootstrap_samples,
        seed=settings.train.seed,
    )
    ndcg = paired_bootstrap_delta(
        candidate.per_user_ndcg,
        baseline.per_user_ndcg,
        samples=settings.eval.bootstrap_samples,
        seed=settings.train.seed + 1,
    )
    return {
        "gauc": {
            "mean_delta": gauc.mean_delta,
            "ci_lower": gauc.lower,
            "ci_upper": gauc.upper,
            "passed": gauc.lower > 0.0,
        },
        "ndcg_at_k": {
            "mean_delta": ndcg.mean_delta,
            "ci_lower": ndcg.lower,
            "ci_upper": ndcg.upper,
            "passed": ndcg.lower > 0.0,
        },
    }


def run_data_probes(
    settings: Settings,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_artifact: RuleArtifact | None = None,
) -> dict[str, Any]:
    """Evaluate non-neural signal probes on one frozen organic validation split."""
    vectors = np.array(embeddings, dtype=np.float32, copy=True)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), np.finfo(np.float32).eps)
    prepared = prepare_split(snapshot, SplitName.VAL)
    rule_store = (
        rule_artifact.store
        if rule_artifact is not None
        else RuleStore(snapshot.manifest.num_items, [])
    )
    evaluator = FullCatalogEvaluator(settings, vectors, rule_store)
    history = prepared.history_events
    purchases = history[history.event_type == "purchase"]
    items = prepared.candidate_item_ids
    popularity = np.log1p(
        np.bincount(
            history.internal_product_id.to_numpy(np.int64),
            minlength=snapshot.manifest.num_items,
        ).astype(np.float32)
    )

    def popularity_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        return np.broadcast_to(popularity, (len(users), len(items))).copy()

    popularity_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.ITEM_CF,
        scorer=cast(ExternalBatchScorer, popularity_scorer),
        k=settings.eval.k,
    )

    def apriori_scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        contexts = np.asarray(
            [prepared.latest_prior_purchase_contexts.get(int(user), -1) for user in users],
            dtype=np.int64,
        )
        lifts, _ = rule_store.batch_raw_lift(
            contexts, np.broadcast_to(candidates, (len(users), len(candidates)))
        )
        return lifts

    apriori_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.WIDE_ONLY,
        scorer=apriori_scorer,
        k=settings.eval.k,
    )

    persona = prepare_persona_baseline(snapshot, prepared)

    def persona_scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        return score_persona_batch(persona, users, candidates)

    persona_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.PERSONA_ONLY,
        scorer=persona_scorer,
        k=settings.eval.k,
    )

    purchase_sets = purchases.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
    centroids = np.zeros((snapshot.manifest.num_users + 1, vectors.shape[1]), dtype=np.float32)
    for user, values in purchase_sets.items():
        ids = np.asarray(sorted(values), dtype=np.int64)
        if len(ids):
            centroid = vectors[ids].mean(axis=0)
            centroids[int(cast(int, user))] = centroid / max(
                float(np.linalg.norm(centroid)), np.finfo(np.float32).eps
            )

    def centroid_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        return np.asarray(centroids[users] @ vectors.T, dtype=np.float32)

    centroid_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.SBERT_CENTROID,
        scorer=cast(ExternalBatchScorer, centroid_scorer),
        k=settings.eval.k,
    )

    pairs = purchases[["internal_user_id", "internal_product_id"]].drop_duplicates()
    matrix = sparse.csr_matrix(
        (
            np.ones(len(pairs), dtype=np.float32),
            (
                pairs.internal_user_id.to_numpy(np.int64) - 1,
                pairs.internal_product_id.to_numpy(np.int64),
            ),
        ),
        shape=(snapshot.manifest.num_users, snapshot.manifest.num_items),
    )
    similarity = (matrix.T @ matrix).tocsr()
    similarity.setdiag(0)
    similarity.eliminate_zeros()

    def item_cf_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        return np.asarray(
            (matrix[np.asarray(users, dtype=np.int64) - 1] @ similarity).toarray(),
            dtype=np.float32,
        )

    item_cf_result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.ITEM_CF,
        scorer=cast(ExternalBatchScorer, item_cf_scorer),
        k=settings.eval.k,
    )

    rng = np.random.default_rng(settings.train.seed)
    next_user = 1

    def permutation_scorer(users: np.ndarray, _candidates: np.ndarray) -> np.ndarray:
        nonlocal next_user
        rows: list[np.ndarray] = []
        for user in users:
            while next_user <= int(user):
                generated = rng.random(snapshot.manifest.num_items, dtype=np.float32)
                if next_user == int(user):
                    rows.append(generated)
                next_user += 1
        return np.stack(rows)

    permuted = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.RANDOM,
        scorer=cast(ExternalBatchScorer, permutation_scorer),
        k=settings.eval.k,
    )
    return {
        "snapshot_sha256": snapshot.manifest.content_sha256,
        "embedding_shape": list(vectors.shape),
        "popularity_only": _metrics(popularity_result),
        "apriori_only": _metrics(apriori_result),
        "persona_only": _metrics(persona_result),
        "sbert_centroid": _metrics(centroid_result),
        "item_item_cf": _metrics(item_cf_result),
        "label_permutation_sanity": {
            **_metrics(permuted),
            "passed": abs(float(permuted.report.gauc) - 0.5) <= settings.eval.random_gauc_tolerance,
        },
        "apriori_vs_random": _paired_evidence(apriori_result, permuted, settings),
        "rule_coverage": (
            rule_artifact.manifest.coverage.model_dump(mode="json")
            if rule_artifact is not None and rule_artifact.manifest.coverage is not None
            else None
        ),
    }
