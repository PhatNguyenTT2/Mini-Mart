"""Unit tests for cold_start_eval.py module."""

import pytest
from evaluation.cold_start_eval import evaluate_cold_start, ColdStartReport
from data.ingestion import load_snapshot
from models.two_tower_wide_deep import HybridTwoTowerModel


def test_evaluate_cold_start_execution():
    snapshot = load_snapshot("test-sbert-snapshot")
    snapshot.test_df = snapshot.test_df.iloc[:50]
    model = HybridTwoTowerModel()

    report = evaluate_cold_start(model, snapshot, k=10)

    assert isinstance(report, ColdStartReport)
    assert report.num_cold_items == 250
    assert report.train_leakage_detected is False  # Must detect 0% data leakage
    assert report.all_scores_finite is True
    assert 0.0 <= report.zero_shot_hr10 <= 1.0
    assert 0.0 <= report.zero_shot_ndcg10 <= 1.0
