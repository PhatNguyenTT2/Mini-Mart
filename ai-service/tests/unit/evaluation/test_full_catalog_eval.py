"""Unit tests for full_catalog_eval.py module."""

import numpy as np
import pytest
from evaluation.full_catalog_eval import (
    compute_user_auc,
    compute_user_dcg,
    compute_user_idcg,
    evaluate_full_catalog,
)
from data.ingestion import load_snapshot, build_snapshot
from models.two_tower_wide_deep import HybridTwoTowerModel


def test_metric_helpers():
    # Test AUC helper
    pos_scores = np.array([2.5, 3.0])
    neg_scores = np.array([0.1, 0.5, 1.0])
    auc = compute_user_auc(pos_scores, neg_scores)
    assert auc == 1.0  # Perfect separation

    # Test DCG and IDCG helpers
    ranks = np.array([1, 3])
    dcg = compute_user_dcg(ranks)
    idcg = compute_user_idcg(num_positives=2, k=10)

    assert dcg > 0.0
    assert idcg >= dcg


def test_evaluate_full_catalog_execution():
    snapshot = load_snapshot("test-sbert-snapshot")
    snapshot.test_df = snapshot.test_df.iloc[:50]
    model = HybridTwoTowerModel()

    report = evaluate_full_catalog(model, snapshot, split="test", k=10)

    assert report.split == "test"
    assert report.num_catalog_items == 5200
    assert 0.0 <= report.hr10 <= 1.0
    assert 0.0 <= report.ndcg10 <= 1.0
    assert 0.0 <= report.gauc <= 1.0
