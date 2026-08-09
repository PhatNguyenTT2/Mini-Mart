"""Unit tests for apriori_rules.py module."""

import numpy as np
import pytest
from data.ingestion import load_snapshot, build_snapshot
from data.apriori_rules import build_rule_store, load_rule_store, RuleStore


def test_rule_store_lookup():
    indptr = np.array([0, 2, 3, 3], dtype=np.int64)
    indices = np.array([1, 2, 0], dtype=np.int32)
    log_lift = np.array([2.5, 1.2, 3.0], dtype=np.float32)
    count = np.array([5, 4, 10], dtype=np.int32)

    store = RuleStore(indptr=indptr, indices=indices, log_lift=log_lift, count=count, num_items=3)

    # Valid lookups
    assert store.lookup(0, 1) == pytest.approx(2.5)
    assert store.lookup(0, 2) == pytest.approx(1.2)
    assert store.lookup(1, 0) == pytest.approx(3.0)

    # Non-existent lookups return 0.0
    assert store.lookup(0, 0) == 0.0
    assert store.lookup(1, 1) == 0.0
    assert store.lookup(2, 0) == 0.0

    # Out of bounds lookups return 0.0
    assert store.lookup(-1, 0) == 0.0
    assert store.lookup(0, 999) == 0.0

    # Batch lookup
    batch_scores = store.lookup_batch(0, np.array([0, 1, 2, 3]))
    np.testing.assert_allclose(batch_scores, [0.0, 2.5, 1.2, 0.0])


def test_build_and_load_rule_store():
    snapshot = load_snapshot("test-sbert-snapshot")
    rule_store = build_rule_store(snapshot, min_count=1, min_lift=0.0)

    loaded_store = load_rule_store(snapshot.snapshot_dir)
    assert len(loaded_store.indptr) == len(rule_store.indptr)
    assert len(loaded_store.indices) == len(rule_store.indices)
