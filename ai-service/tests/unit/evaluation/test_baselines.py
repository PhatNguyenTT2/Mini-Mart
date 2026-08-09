"""Unit tests for baselines.py module."""

import pytest
from evaluation.baselines import (
    run_random_baseline,
    run_noisy_persona_hybrid,
    run_seven_way_comparison,
    BaselineComparisonReport,
)
from data.ingestion import load_snapshot
from models.two_tower_wide_deep import HybridTwoTowerModel


def test_random_baseline_sanity_check():
    snapshot = load_snapshot("test-sbert-snapshot")
    # Slice test_df for fast unit test execution
    snapshot.test_df = snapshot.test_df.iloc[:50]

    report = run_random_baseline(snapshot, k=10)

    assert report.split == "test"
    assert 0.0 <= report.gauc <= 1.0


def test_seven_way_comparison_execution():
    snapshot = load_snapshot("test-sbert-snapshot")
    snapshot.test_df = snapshot.test_df.iloc[:50]
    model = HybridTwoTowerModel()

    report = run_seven_way_comparison(model, snapshot, k=10)

    assert isinstance(report, BaselineComparisonReport)
    assert "Proposed Hybrid (Ours)" in report.baselines
    assert "Deep-Only Two-Tower" in report.baselines
    assert "Noisy 10% Hybrid" in report.baselines
    assert "Random Base (Sanity Check)" in report.baselines
