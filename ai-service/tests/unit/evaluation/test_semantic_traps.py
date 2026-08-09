"""Unit tests for semantic_traps.py module."""

import pytest
from evaluation.semantic_traps import (
    load_trap_fixtures,
    evaluate_semantic_traps,
    SemanticTrapsReport,
)
from data.ingestion import load_snapshot
from models.two_tower_wide_deep import HybridTwoTowerModel


def test_load_trap_fixtures():
    traps = load_trap_fixtures()
    assert len(traps) == 10
    assert traps[0]["trap_id"] == 1
    assert "anchor_product_id" in traps[0]
    assert "target_product_ids" in traps[0]


def test_evaluate_semantic_traps_execution():
    snapshot = load_snapshot("test-sbert-snapshot")
    model = HybridTwoTowerModel()

    report = evaluate_semantic_traps(model, snapshot)

    assert isinstance(report, SemanticTrapsReport)
    assert report.num_traps == 10
    assert 0.0 <= report.mean_hybrid_hr10 <= 1.0
    assert 0.0 <= report.mean_hybrid_ndcg10 <= 1.0
    assert len(report.trap_results) == 10
