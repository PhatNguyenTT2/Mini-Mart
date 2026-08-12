from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_service.config import Settings
from ai_service.contracts import DataSourceKind
from ai_service.data.snapshot import SnapshotBuilder, _semantic_cohort_document, load_snapshot
from ai_service.data.sources import RawDataset
from ai_service.errors import DataIntegrityError


def _raw(*, cold_test_type: str = "purchase") -> RawDataset:
    timestamps = list(pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC"))
    products = pd.DataFrame(
        {
            "product_id": np.arange(1, 11),
            "name": [f"item-{value}" for value in range(1, 11)],
            "unit_price": np.arange(1, 11, dtype=float),
            "leaf_category_id": (np.arange(10) % 4) + 1,
            "leaf_category_name": ["leaf"] * 10,
            "root_category_name": ["root"] * 10,
            "vendor": ["vendor"] * 10,
            "description": [""] * 10,
        }
    )
    events = pd.DataFrame(
        {
            "event_id": [f"evt-{idx:03d}" for idx in range(20)],
            "store_id": [1] * 20,
            "user_id": [(idx % 4) + 1 for idx in range(20)],
            "product_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 10],
            "persona_cluster": [idx % 4 for idx in range(20)],
            "event_type": ["purchase"] * 19 + [cold_test_type],
            "event_ts": timestamps,
            "interaction_weight": [1.0] * 19 + ([0.5] if cold_test_type == "view" else [1.0]),
            "session_id": [f"session-{idx:03d}" for idx in range(20)],
            "event_origin": ["organic"] * 19 + ["cold_start"],
            "cohort_id": [None] * 19 + ["cold-10"],
            "benchmark_run_id": ["run-test"] * 20,
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": [1, 1],
            "user_id": [1, 1],
            "product_id": [1, 2],
            "quantity": [1, 1],
            "order_ts": [timestamps[0], timestamps[0]],
        }
    )
    return RawDataset(
        events_df=events,
        products_df=products,
        orders_df=orders,
        cold_product_ids=(10,),
        source_kind=DataSourceKind.SYNTHETIC,
        benchmark_run_id="run-test",
        store_id=1,
    )


def _settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 4
    settings.data.num_items = 10
    settings.data.expected_event_count = 20
    settings.data.expected_train_count = 16
    settings.data.expected_val_count = 2
    settings.data.expected_test_count = 2
    settings.data.expected_order_count = 1
    settings.data.num_cold_items = 1
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    return settings


def test_semantic_cohort_document_persists_prior_anchor_for_targets() -> None:
    events = pd.DataFrame(
        {
            "event_id": ["run:val:semantic:anchor:0", "run:val:semantic:target:0"],
            "user_id": [7, 7],
            "product_id": [101, 102],
            "event_ts": pd.date_range("2026-01-01", periods=2, tz="UTC"),
            "cohort_id": ["semantic-1", "semantic-1"],
            "event_origin": ["semantic_trap", "semantic_trap"],
        }
    )
    document = _semantic_cohort_document(events)
    assert document[0]["target_product_ids"] == []
    assert document[1]["anchor_product_id"] == 101
    assert document[1]["target_product_ids"] == [102]


def test_snapshot_keeps_timestamp_groups_and_explicit_cold_partition(tmp_path: Path) -> None:
    snapshot = SnapshotBuilder(_settings(tmp_path)).build(_raw(), snapshot_id="fixture")

    assert snapshot.train_df["event_ts"].max() < snapshot.val_df["event_ts"].min()
    assert snapshot.val_df["event_ts"].max() < snapshot.test_df["event_ts"].min()
    assert set(snapshot.cold_item_ids) == {9}
    assert 9 not in set(snapshot.train_df["internal_product_id"])
    assert 9 not in set(snapshot.val_df["internal_product_id"])
    assert set(
        snapshot.test_df.loc[snapshot.test_df.event_type == "purchase", "internal_product_id"]
    ) >= {9}
    assert snapshot.order_baskets_df["order_ts"].max() <= snapshot.train_df["event_ts"].max()
    assert len(snapshot.manifest.content_sha256) == 64
    loaded = load_snapshot("fixture", _settings(tmp_path))
    assert loaded.manifest.content_sha256 == snapshot.manifest.content_sha256
    assert loaded.product_map == snapshot.product_map


def test_snapshot_rejects_cold_item_without_test_purchase(tmp_path: Path) -> None:
    with pytest.raises(DataIntegrityError, match=r"cold.*purchase"):
        SnapshotBuilder(_settings(tmp_path)).build(
            _raw(cold_test_type="view"), snapshot_id="invalid"
        )


def test_snapshot_rejects_duplicate_catalog_rows(tmp_path: Path) -> None:
    raw = _raw()
    raw.products_df.loc[9, "product_id"] = 9

    with pytest.raises(DataIntegrityError, match="product_id must be unique"):
        SnapshotBuilder(_settings(tmp_path)).build(raw, snapshot_id="duplicate-catalog")


def test_snapshot_rejects_session_crossing_temporal_boundary(tmp_path: Path) -> None:
    raw = _raw()
    raw.events_df.loc[15:16, "session_id"] = "cross-boundary"

    with pytest.raises(DataIntegrityError, match=r"session.*split"):
        SnapshotBuilder(_settings(tmp_path)).build(raw, snapshot_id="crossed-session")
