"""Exact full-catalog ranking metrics with deterministic tie handling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ai_service_v2.errors import ScoreError


@dataclass(frozen=True)
class UserMetrics:
    hit_rate: float
    ndcg: float
    gauc: float | None
    ranked_indices: tuple[int, ...]


def _validate_score_inputs(
    scores: np.ndarray, raw_item_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(scores, dtype=np.float64)
    raw = np.asarray(raw_item_ids)
    if values.ndim != 1 or raw.ndim != 1 or values.shape != raw.shape or not len(values):
        raise ScoreError("scores and raw_item_ids must be non-empty equal-length vectors")
    if np.isnan(values).any() or np.isposinf(values).any():
        raise ScoreError("scores cannot contain NaN or positive infinity")
    if len(np.unique(raw)) != len(raw):
        raise ScoreError("raw item IDs must be unique")
    return values, raw


def rank_indices(scores: np.ndarray, raw_item_ids: np.ndarray, k: int) -> np.ndarray:
    values, raw = _validate_score_inputs(scores, raw_item_ids)
    if k < 1 or k > len(values):
        raise ValueError("k must be inside the candidate catalog")
    # np.lexsort uses the last key as primary: score descending, then raw ID.
    order = np.lexsort((raw, -values))
    return order[:k]


def user_auc(positive_scores: np.ndarray, negative_scores: np.ndarray) -> float | None:
    """Compute exact AUC with average ranks for ties."""

    positive = np.asarray(positive_scores, dtype=np.float64)
    negative = np.asarray(negative_scores, dtype=np.float64)
    if positive.ndim != 1 or negative.ndim != 1:
        raise ScoreError("AUC inputs must be one-dimensional")
    if not len(positive) or not len(negative):
        return None
    combined = np.concatenate((positive, negative))
    if np.isnan(combined).any() or np.isinf(combined).any():
        raise ScoreError("AUC inputs must be finite")
    order = np.argsort(combined, kind="mergesort")
    sorted_scores = combined[order]
    ranks = np.empty(len(combined), dtype=np.float64)
    start = 0
    while start < len(sorted_scores):
        end = start + 1
        while end < len(sorted_scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        # Ranks are one-based and averaged over a tie block.
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    positive_rank_sum = float(ranks[: len(positive)].sum())
    pair_count = len(positive) * len(negative)
    return (positive_rank_sum - len(positive) * (len(positive) + 1) / 2.0) / pair_count


def ranking_metrics(
    *,
    scores: np.ndarray,
    positive_indices: set[int],
    raw_item_ids: np.ndarray,
    k: int,
    negative_indices: set[int] | None = None,
) -> UserMetrics:
    values, raw = _validate_score_inputs(scores, raw_item_ids)
    if not positive_indices:
        raise ValueError("at least one positive item is required")
    if any(index < 0 or index >= len(values) for index in positive_indices):
        raise ScoreError("positive index is outside the candidate catalog")
    top = rank_indices(values, raw, k)
    relevant_ranks = [rank + 1 for rank, index in enumerate(top) if int(index) in positive_indices]
    hit = float(bool(relevant_ranks))
    dcg = sum(1.0 / np.log2(rank + 1) for rank in relevant_ranks)
    ideal_count = min(len(positive_indices), k)
    idcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_count + 1))
    if negative_indices is None:
        negative_indices = set(range(len(values))) - positive_indices
    if any(index < 0 or index >= len(values) for index in negative_indices):
        raise ScoreError("negative index is outside the candidate catalog")
    if positive_indices & negative_indices:
        raise ScoreError("positive and negative indices must be disjoint")
    auc = user_auc(values[list(positive_indices)], values[list(negative_indices)])
    return UserMetrics(
        hit_rate=hit,
        ndcg=float(dcg / idcg if idcg else 0.0),
        gauc=auc,
        ranked_indices=tuple(int(index) for index in top),
    )


def aggregate_user_metrics(rows: list[UserMetrics]) -> dict[str, float | None]:
    return aggregate_user_metrics_at_k(rows, cutoff=10)


def aggregate_user_metrics_at_k(rows: list[UserMetrics], *, cutoff: int) -> dict[str, float | None]:
    if not rows:
        raise ValueError("cannot aggregate an empty user metric list")
    if cutoff < 1:
        raise ValueError("cutoff must be positive")
    gauc_values = [row.gauc for row in rows if row.gauc is not None]
    return {
        f"HR@{cutoff}": float(np.mean([row.hit_rate for row in rows])),
        f"NDCG@{cutoff}": float(np.mean([row.ndcg for row in rows])),
        "GAUC": float(np.mean(gauc_values)) if gauc_values else None,
    }


__all__ = [
    "UserMetrics",
    "aggregate_user_metrics",
    "aggregate_user_metrics_at_k",
    "rank_indices",
    "ranking_metrics",
    "user_auc",
]
