from __future__ import annotations

import numpy as np
import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ScoreError
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.protocol import build_protocol


def test_evaluator_owns_masking_and_aggregation(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    evaluator = FullCatalogEvaluator(protocol)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        values = np.zeros(len(candidates), dtype=float)
        if user_id == 0:
            values[2] = 10.0
        else:
            values[3] = 10.0
        return values

    result = evaluator.evaluate(scorer, run_id="fixture-run", model_id="fixture-model")
    assert result.receipt.verdict == "PASS"
    assert result.receipt.num_total_users == 4
    assert result.receipt.num_eligible_users == 2
    assert result.receipt.aggregate_metrics["HR@5"] == 1.0
    assert result.receipt.aggregate_metrics["NDCG@5"] == 1.0
    assert result.receipt.denominator_by_metric["GAUC"] == 2
    assert result.top_k_by_user[0][0] == 2
    assert set(result.per_user_metrics) == {"HR@5", "NDCG@5", "GAUC"}


def test_evaluator_rejects_bad_provider_output(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    evaluator = FullCatalogEvaluator(protocol)

    def bad_scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        del user_id, candidates
        return np.ones(2)

    with pytest.raises(ScoreError, match="shape"):
        evaluator.evaluate(bad_scorer, run_id="bad-run", model_id="bad-model")


def test_evaluator_does_not_allow_provider_nan(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    evaluator = FullCatalogEvaluator(protocol)

    def bad_scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        del user_id
        return np.full(len(candidates), np.nan)

    with pytest.raises(ScoreError, match="non-finite"):
        evaluator.evaluate(bad_scorer, run_id="nan-run", model_id="nan-model")
