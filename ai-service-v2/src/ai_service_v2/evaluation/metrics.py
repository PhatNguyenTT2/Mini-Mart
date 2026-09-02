"""Exact full-catalog ranking metrics with deterministic tie handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

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
    if raw.dtype.kind not in "iu":
        raise ScoreError("raw item IDs must be integer values")
    if len(np.unique(raw)) != len(raw):
        raise ScoreError("raw item IDs must be unique")
    return values, raw


def _validate_indices(indices: set[int], name: str, length: int) -> set[int]:
    try:
        parsed = set(indices)
    except (TypeError, ValueError) as error:
        raise ScoreError(f"{name} must be a set of integer indices") from error
    if any(isinstance(index, bool) or not isinstance(index, (int, np.integer)) for index in parsed):
        raise ScoreError(f"{name} must contain only integer indices")
    if any(index < 0 or index >= length for index in parsed):
        raise ScoreError(f"{name} index is outside the candidate catalog")
    return {int(index) for index in parsed}


def rank_indices(
    scores: np.ndarray,
    raw_item_ids: np.ndarray,
    k: int,
    *,
    excluded_indices: set[int] | None = None,
) -> np.ndarray:
    values, raw = _validate_score_inputs(scores, raw_item_ids)
    if isinstance(k, bool) or not isinstance(k, (int, np.integer)):
        raise ValueError("k must be an integer")
    if k < 1 or k > len(values):
        raise ValueError("k must be inside the candidate catalog")
    # np.lexsort uses the last key as primary: score descending, then raw ID.
    order = np.lexsort((raw, -values))
    if excluded_indices is None:
        return order[:k]
    excluded = _validate_indices(excluded_indices, "excluded_indices", len(values))
    if excluded and not np.isneginf(values[list(excluded)]).all():
        raise ScoreError("excluded candidate scores must be masked to negative infinity")
    available = np.asarray([int(index) not in excluded for index in order], dtype=bool)
    return cast(np.ndarray, order[available][:k])


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
    excluded_indices: set[int] | None = None,
) -> UserMetrics:
    values, raw = _validate_score_inputs(scores, raw_item_ids)
    positives = _validate_indices(positive_indices, "positive_indices", len(values))
    if not positives:
        raise ValueError("at least one positive item is required")
    if negative_indices is None:
        negatives = set(range(len(values))) - positives
    else:
        negatives = _validate_indices(negative_indices, "negative_indices", len(values))
    if excluded_indices is None:
        excluded = set(range(len(values))) - positives - negatives
    else:
        excluded = _validate_indices(excluded_indices, "excluded_indices", len(values))
    if positives & negatives:
        raise ScoreError("positive and negative indices must be disjoint")
    if positives & excluded or negatives & excluded:
        raise ScoreError("positive, negative, and excluded indices must be disjoint")
    if positives | negatives | excluded != set(range(len(values))):
        raise ScoreError("metric index sets must cover the full candidate catalog")
    if excluded and not np.isneginf(values[list(excluded)]).all():
        raise ScoreError("excluded candidate scores must be masked to negative infinity")
    top = rank_indices(values, raw, k, excluded_indices=excluded)
    relevant_ranks = [rank + 1 for rank, index in enumerate(top) if int(index) in positives]
    hit = float(bool(relevant_ranks))
    dcg = sum(1.0 / np.log2(rank + 1) for rank in relevant_ranks)
    ideal_count = min(len(positives), k)
    idcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_count + 1))
    auc = user_auc(values[list(positives)], values[list(negatives)])
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
    for row in rows:
        for name, value in (("HR", row.hit_rate), ("NDCG", row.ndcg), ("GAUC", row.gauc)):
            if value is not None and (not np.isfinite(value) or not 0.0 <= value <= 1.0):
                raise ScoreError(f"{name} metric value must be finite and inside [0, 1]")
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
