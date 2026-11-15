from __future__ import annotations

import math

import numpy as np
import pytest

from ai_service_v2.errors import ScoreError
from ai_service_v2.evaluation.metrics import rank_indices, ranking_metrics, user_auc


def test_ties_use_raw_item_id_as_secondary_order() -> None:
    scores = np.array([1.0, 1.0, 0.0])
    raw_ids = np.array([20, 10, 30])
    assert rank_indices(scores, raw_ids, 3).tolist() == [1, 0, 2]


def test_ndcg_and_hit_are_computed_from_rank() -> None:
    row = ranking_metrics(
        scores=np.array([0.9, 0.8, 0.1]),
        positive_indices={1},
        negative_indices={0, 2},
        raw_item_ids=np.array([10, 20, 30]),
        k=2,
    )
    assert row.hit_rate == 1.0
    assert math.isclose(row.ndcg, 1.0 / math.log2(3), rel_tol=1e-12)
    assert row.gauc == 0.5


def test_auc_uses_average_rank_for_ties() -> None:
    assert user_auc(np.array([1.0]), np.array([1.0])) == 0.5
    assert user_auc(np.array([2.0]), np.array([1.0])) == 1.0
    assert user_auc(np.array([1.0]), np.array([2.0])) == 0.0


def test_metrics_reject_nan_and_invalid_positive() -> None:
    with pytest.raises(ScoreError, match="NaN"):
        rank_indices(np.array([1.0, np.nan]), np.array([1, 2]), 1)
    with pytest.raises(ScoreError, match="outside"):
        ranking_metrics(
            scores=np.array([1.0, 0.0]),
            positive_indices={2},
            raw_item_ids=np.array([1, 2]),
            k=1,
        )


def test_undefined_gauc_is_not_imputed() -> None:
    from ai_service_v2.evaluation.metrics import UserMetrics, aggregate_user_metrics_at_k

    result = aggregate_user_metrics_at_k([UserMetrics(1.0, 1.0, None, (0,))], cutoff=1)
    assert result["GAUC"] is None
