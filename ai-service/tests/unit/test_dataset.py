"""Unit tests for dataset.py module."""

import numpy as np
import pytest
import torch

from data.ingestion import load_snapshot, build_snapshot
from data.apriori_rules import build_rule_store
from data.dataset import HybridImplicitDataset, collate_candidate_groups


def test_dataset_sample_generation():
    snapshot = load_snapshot("test-sbert-snapshot")
    rule_store = build_rule_store(snapshot, min_count=1, min_lift=0.0)

    dataset = HybridImplicitDataset(snapshot, rule_store, split="train", seed=42)
    assert len(dataset) > 0

    sample = dataset[0]
    assert "user_idx" in sample
    assert "persona_idx" in sample
    assert "candidate_item_idx" in sample
    assert "context_item_idx" in sample
    assert "log_lift" in sample
    assert "labels" in sample

    assert len(sample["candidate_item_idx"]) == 5
    assert np.array_equal(sample["labels"], [1.0, 0.0, 0.0, 0.0, 0.0])
    assert sample["log_lift"].shape == (5, 1)


def test_collate_candidate_groups():
    snapshot = load_snapshot("test-sbert-snapshot")
    rule_store = build_rule_store(snapshot, min_count=1, min_lift=0.0)

    dataset = HybridImplicitDataset(snapshot, rule_store, split="train", seed=42)
    samples = [dataset[0], dataset[1], dataset[2]]

    batch = collate_candidate_groups(samples)

    assert isinstance(batch.user_idx, torch.Tensor)
    assert batch.user_idx.shape == (3,)
    assert batch.candidate_item_idx.shape == (3, 5)
    assert batch.log_lift.shape == (3, 5, 1)
    assert batch.labels.shape == (3, 5)
    assert torch.all(batch.labels[:, 0] == 1.0)
    assert torch.all(batch.labels[:, 1:] == 0.0)


def test_epoch_reproducibility():
    snapshot = load_snapshot("test-sbert-snapshot")
    rule_store = build_rule_store(snapshot, min_count=1, min_lift=0.0)

    dataset1 = HybridImplicitDataset(snapshot, rule_store, split="train", seed=42)
    dataset1.set_epoch(1)
    sample_ep1_a = dataset1[0]

    dataset2 = HybridImplicitDataset(snapshot, rule_store, split="train", seed=42)
    dataset2.set_epoch(1)
    sample_ep1_b = dataset2[0]

    np.testing.assert_array_equal(
        sample_ep1_a["candidate_item_idx"], sample_ep1_b["candidate_item_idx"]
    )

    dataset1.set_epoch(2)
    sample_ep2 = dataset1[0]
    # Check that epoch 2 produces different dynamic negative samples
    assert not np.array_equal(
        sample_ep1_a["candidate_item_idx"], sample_ep2["candidate_item_idx"]
    )
