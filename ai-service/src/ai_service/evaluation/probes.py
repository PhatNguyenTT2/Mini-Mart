"""Cheap data-only probes that separate signal quality from model optimization."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.quality import filter_event_origin
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import FullCatalogEvaluator


def _metrics(result: Any) -> dict[str, float | int]:
    report = result.report
    return {
        "eligible_users": int(report.num_eligible_users),
        "hr_at_k": float(report.hr_at_k),
        "ndcg_at_k": float(report.ndcg_at_k),
        "gauc": float(report.gauc),
    }


def run_data_probes(
    settings: Settings,
    snapshot: Snapshot,
    embeddings: np.ndarray,
) -> dict[str, Any]:
    """Evaluate non-neural signal probes on organic validation purchases."""
    vectors = np.array(embeddings, dtype=np.float32, copy=True)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), np.finfo(np.float32).eps)
    evaluator = FullCatalogEvaluator(
        settings,
        vectors,
        RuleStore(snapshot.manifest.num_items, []),
    )
    history = filter_event_origin(snapshot.train_df)
    purchases = history[history.event_type == "purchase"]
    all_users = range(1, snapshot.manifest.num_users + 1)

    popularity = np.bincount(
        history.internal_product_id.to_numpy(np.int64),
        minlength=snapshot.manifest.num_items,
    ).astype(np.float32)
    popularity = np.log1p(popularity)
    popularity_scores = {user: popularity for user in all_users}
    popularity_result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.ITEM_CF,
        scores_by_user=popularity_scores,
        k=settings.eval.k,
    )

    category_by_item = snapshot.catalog_df.sort_values(
        "internal_product_id", kind="stable"
    ).internal_leaf_category_id.to_numpy(np.int64)
    persona_category: dict[int, Counter[int]] = defaultdict(Counter)
    for user, item in purchases[["internal_user_id", "internal_product_id"]].itertuples(
        index=False, name=None
    ):
        raw_user = snapshot.raw_user_map[int(user)]
        persona = int(snapshot.persona_map.get(raw_user, settings.data.num_personas))
        persona_category[persona][int(category_by_item[int(item)])] += 1
    persona_vectors: dict[int, np.ndarray] = {}
    for persona in range(settings.data.num_personas + 1):
        counts = persona_category[persona]
        persona_vectors[persona] = (
            np.asarray([counts[int(category)] for category in category_by_item], dtype=np.float32)
            + popularity * 1e-4
        )
    persona_scores = {
        user: persona_vectors[
            int(snapshot.persona_map.get(snapshot.raw_user_map[user], settings.data.num_personas))
        ]
        for user in all_users
    }
    persona_result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.SBERT_CENTROID,
        scores_by_user=persona_scores,
        k=settings.eval.k,
    )

    purchase_sets = purchases.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
    centroid_scores: dict[int, np.ndarray] = {}
    for user in all_users:
        items = np.asarray(sorted(purchase_sets.get(user, set())), dtype=np.int64)
        if len(items):
            centroid = vectors[items].mean(axis=0)
            centroid /= max(float(np.linalg.norm(centroid)), np.finfo(np.float32).eps)
            centroid_scores[user] = vectors @ centroid
        else:
            centroid_scores[user] = np.zeros(snapshot.manifest.num_items, dtype=np.float32)
    centroid_result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.SBERT_CENTROID,
        scores_by_user=centroid_scores,
        k=settings.eval.k,
    )

    adjacency: dict[int, Counter[int]] = defaultdict(Counter)
    for items in purchase_sets.values():
        for left, right in combinations(sorted(int(item) for item in items), 2):
            adjacency[left][right] += 1
            adjacency[right][left] += 1
    item_cf_scores: dict[int, np.ndarray] = {}
    for user in all_users:
        scores = np.zeros(snapshot.manifest.num_items, dtype=np.float32)
        for item in purchase_sets.get(user, set()):
            for neighbor, count in adjacency[int(item)].items():
                scores[neighbor] += count
        item_cf_scores[user] = scores
    item_cf_result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.ITEM_CF,
        scores_by_user=item_cf_scores,
        k=settings.eval.k,
    )

    rng = np.random.default_rng(settings.train.seed)
    permuted_scores = {
        user: rng.random(snapshot.manifest.num_items, dtype=np.float32) for user in all_users
    }
    permuted = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.RANDOM,
        scores_by_user=permuted_scores,
        k=settings.eval.k,
    )
    return {
        "snapshot_sha256": snapshot.manifest.content_sha256,
        "embedding_shape": list(vectors.shape),
        "popularity_only": _metrics(popularity_result),
        "persona_only": _metrics(persona_result),
        "sbert_centroid": _metrics(centroid_result),
        "item_item_cf": _metrics(item_cf_result),
        "label_permutation_sanity": {
            **_metrics(permuted),
            "passed": abs(float(permuted.report.gauc) - 0.5) <= 0.02,
        },
    }
