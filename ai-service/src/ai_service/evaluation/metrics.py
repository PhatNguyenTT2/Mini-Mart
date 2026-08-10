"""Ranking metrics with bounded-memory GAUC and deterministic ties."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def user_auc(positive_scores: np.ndarray, negative_scores: np.ndarray) -> float | None:
    positive = np.asarray(positive_scores, dtype=np.float64)
    negative = np.asarray(negative_scores, dtype=np.float64)
    if not len(positive) or not len(negative):
        return None
    scores = np.concatenate((positive, negative))
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positive_rank_sum = float(ranks[: len(positive)].sum())
    pairs = len(positive) * len(negative)
    return (positive_rank_sum - len(positive) * (len(positive) + 1) / 2.0) / pairs


@dataclass(frozen=True)
class UserRankingMetrics:
    hit: float
    ndcg: float
    ranked_indices: np.ndarray


def ranking_metrics(
    *,
    scores: np.ndarray,
    positive_indices: set[int],
    raw_product_ids: np.ndarray,
    k: int,
) -> UserRankingMetrics:
    if not 1 <= k <= len(scores):
        raise ValueError("k must be inside the catalog")
    order = np.lexsort((raw_product_ids, -np.asarray(scores)))
    top = order[:k]
    relevant_ranks = [rank + 1 for rank, item in enumerate(top) if int(item) in positive_indices]
    hit = float(bool(relevant_ranks))
    dcg = sum(1.0 / np.log2(rank + 1) for rank in relevant_ranks)
    ideal_count = min(len(positive_indices), k)
    idcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return UserRankingMetrics(hit=hit, ndcg=float(dcg / idcg if idcg else 0.0), ranked_indices=top)


@dataclass(frozen=True)
class BootstrapInterval:
    mean_delta: float
    lower: float
    upper: float


def paired_bootstrap_delta(
    candidate: np.ndarray,
    baseline: np.ndarray,
    *,
    samples: int = 2_000,
    seed: int = 42,
) -> BootstrapInterval:
    candidate = np.asarray(candidate, dtype=np.float64)
    baseline = np.asarray(baseline, dtype=np.float64)
    if candidate.shape != baseline.shape or candidate.ndim != 1 or not len(candidate):
        raise ValueError("paired metrics must be non-empty vectors of equal shape")
    delta = candidate - baseline
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=np.float64)
    for index in range(samples):
        selection = rng.integers(0, len(delta), len(delta))
        means[index] = delta[selection].mean()
    lower, upper = np.quantile(means, [0.025, 0.975])
    return BootstrapInterval(float(delta.mean()), float(lower), float(upper))
