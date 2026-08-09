"""Unit tests for ingestion.py module."""

import numpy as np
import pytest
from config import get_settings
from data.ingestion import (
    build_snapshot,
    load_snapshot,
    fit_price_boundaries,
    map_price_to_bucket,
)


def test_fit_price_boundaries_and_bucket_mapping():
    prices = np.array([10000, 20000, 30000, 50000, 80000, 120000, 180000, 250000])
    boundaries = fit_price_boundaries(prices)
    assert len(boundaries) == 7

    # Check bucket mappings
    assert map_price_to_bucket(0, boundaries) == 0
    assert map_price_to_bucket(None, boundaries) == 0
    assert map_price_to_bucket(5000, boundaries) == 1
    assert map_price_to_bucket(300000, boundaries) == 8


def test_build_and_load_snapshot(tmp_path):
    settings = get_settings()

    manifest = build_snapshot(settings=settings, snapshot_id="test-snapshot")
    assert manifest.snapshot_id == "test-snapshot"
    assert manifest.num_users == 5000
    assert manifest.num_items == 5200
    assert manifest.num_leaf_categories == 40
    assert manifest.num_cold_items == 250

    artifacts = load_snapshot("test-snapshot")
    assert artifacts.manifest.snapshot_id == "test-snapshot"
    assert len(artifacts.user_map) == 5000
    assert len(artifacts.product_map) == 5200
    assert len(artifacts.leaf_category_map) == 40
    assert len(artifacts.cold_item_ids) == 250

    # Verify Cold Item Isolation: cold items must not be in train or val
    cold_set = set(artifacts.cold_item_ids)
    train_products = set(artifacts.train_df["internal_product_id"])
    val_products = set(artifacts.val_df["internal_product_id"])

    assert len(cold_set.intersection(train_products)) == 0
    assert len(cold_set.intersection(val_products)) == 0

    # Verify Temporal Isolation
    train_max_ts = artifacts.train_df["event_ts"].max()
    val_min_ts = artifacts.val_df["event_ts"].min()
    val_max_ts = artifacts.val_df["event_ts"].max()
    test_min_ts = artifacts.test_df["event_ts"].min()

    assert train_max_ts <= val_min_ts
    assert val_max_ts <= test_min_ts
