from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from pydantic import SecretStr

from ai_service.config import Settings
from ai_service.data import sources
from ai_service.data.snapshot import SnapshotBuilder
from ai_service.data.sources import PostgresDatasetSource, SyntheticDatasetSource
from ai_service.errors import SourceReadError


def _small_settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 4
    settings.data.num_items = 10
    settings.data.num_cold_items = 2
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.data.expected_event_count = 40
    settings.data.expected_train_count = 30
    settings.data.expected_val_count = 5
    settings.data.expected_test_count = 5
    settings.data.expected_order_count = 5
    return settings


def test_synthetic_source_is_explicit_deterministic_and_snapshot_valid(tmp_path: Path) -> None:
    settings = _small_settings(tmp_path)
    source = SyntheticDatasetSource(settings)
    first = source.load(store_id=1, benchmark_run_id="synthetic-contract")
    second = source.load(store_id=1, benchmark_run_id="synthetic-contract")

    pd.testing.assert_frame_equal(first.events_df, second.events_df)
    assert len(first.cold_product_ids) == 2
    assert len(first.orders_df.order_id.unique()) == 5
    snapshot = SnapshotBuilder(settings).build(first, snapshot_id="synthetic-contract")
    assert snapshot.manifest.split_counts == {"train": 30, "val": 5, "test": 5}


def test_synthetic_source_has_preference_signal_and_novel_targets(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 32
    settings.data.num_items = 128
    settings.data.num_cold_items = 8
    settings.data.num_leaf_categories = 16
    settings.data.expected_event_count = 1536
    settings.data.expected_train_count = 1024
    settings.data.expected_val_count = 256
    settings.data.expected_test_count = 256
    settings.data.expected_order_count = 128
    raw = SyntheticDatasetSource(settings).load(store_id=1, benchmark_run_id="synthetic-signal")
    events = raw.events_df
    train = events.iloc[: settings.data.expected_train_count]
    val = events.iloc[
        settings.data.expected_train_count : settings.data.expected_train_count
        + settings.data.expected_val_count
    ]
    test = events.iloc[settings.data.expected_train_count + settings.data.expected_val_count :]
    categories = dict(
        zip(
            raw.products_df.product_id.astype(int),
            raw.products_df.leaf_category_id.astype(int),
            strict=True,
        )
    )
    preferred_matches = [
        categories[int(row.product_id)]
        == ((int(row.user_id) - 1) % settings.data.num_leaf_categories) + 1
        for row in train.itertuples()
        if row.event_type == "purchase"
    ]
    assert sum(preferred_matches) / len(preferred_matches) >= 0.75
    train_seen = train.groupby("user_id").product_id.apply(set).to_dict()
    for row in val.itertuples():
        assert int(row.product_id) not in train_seen[int(row.user_id)]
    history_seen = train.groupby("user_id").product_id.apply(set).to_dict()
    for row in val.itertuples():
        history_seen.setdefault(int(row.user_id), set()).add(int(row.product_id))
    for row in test.itertuples():
        if row.event_origin == "organic":
            assert int(row.product_id) not in history_seen[int(row.user_id)]
    assert sum(test.event_origin == "cold_start") == settings.data.num_cold_items


def test_remote_postgres_source_requires_verified_ca_before_connecting(tmp_path: Path) -> None:
    settings = _small_settings(tmp_path)
    settings.data.chatbot_database_url = SecretStr("postgresql://user:pass@example.com/db")
    settings.data.catalog_database_url = SecretStr("postgresql://user:pass@example.com/db")
    settings.data.order_database_url = SecretStr("postgresql://user:pass@example.com/db")

    with pytest.raises(SourceReadError, match="SUPABASE_DB_CA_PATH"):
        PostgresDatasetSource(settings).load(store_id=1)


def test_postgres_source_reads_one_published_lineage_with_read_only_adapters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _small_settings(tmp_path)
    settings.data.chatbot_database_url = SecretStr("postgresql://localhost/chat")
    settings.data.catalog_database_url = SecretStr("postgresql://localhost/catalog")
    settings.data.order_database_url = SecretStr("postgresql://localhost/order")

    class FakeCursor:
        def __init__(self, database: str):
            self.database = database
            self.query = ""

        def __enter__(self) -> object:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, query: str, _params: tuple[object, ...]) -> None:
            self.query = query

        @property
        def description(self) -> list[SimpleNamespace]:
            if "ml_interaction_event_v1" in self.query:
                names = [
                    "event_id",
                    "store_id",
                    "user_id",
                    "product_id",
                    "persona_cluster",
                    "event_type",
                    "event_ts",
                    "interaction_weight",
                    "session_id",
                    "event_origin",
                    "cohort_id",
                    "benchmark_run_id",
                ]
            elif "FROM product" in self.query:
                names = [
                    "product_id",
                    "name",
                    "unit_price",
                    "leaf_category_id",
                    "leaf_category_name",
                    "root_category_name",
                    "vendor",
                    "description",
                ]
            elif "sale_order" in self.query:
                names = ["order_id", "user_id", "product_id", "quantity", "order_ts"]
            else:
                names = []
            return [SimpleNamespace(name=name) for name in names]

        def fetchone(self) -> tuple[str] | None:
            if "benchmark_spec_sha256" in self.query:
                return ("a" * 64, {})
            if "ml_benchmark_run_v1" in self.query:
                return ("benchmark-ready",)
            return None

        def fetchall(self) -> list[tuple[Any, ...]]:
            if "ml_interaction_event_v1" in self.query:
                return [
                    (
                        "event-1",
                        1,
                        100,
                        1001,
                        0,
                        "purchase",
                        pd.Timestamp("2026-01-01", tz="UTC"),
                        1.0,
                        "session-1",
                        "organic",
                        None,
                        "benchmark-ready",
                    )
                ]
            if "ml_benchmark_item_partition_v1" in self.query:
                return [(1010,)]
            if "FROM product" in self.query:
                return [(1001, "Item", 10.0, 1, "Leaf", "Root", "Vendor", "Text")]
            if "sale_order" in self.query:
                return [(1, 100, 1001, 1, pd.Timestamp("2026-01-01", tz="UTC"))]
            return []

    class FakeConnection:
        def __init__(self, database: str):
            self.database = database

        def __enter__(self) -> object:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> FakeCursor:
            return FakeCursor(self.database)

    monkeypatch.setattr(
        sources,
        "_connect_read_only",
        lambda url, _settings: FakeConnection(url.rsplit("/", 1)[-1]),
    )

    raw = PostgresDatasetSource(settings).load(store_id=1)

    assert raw.benchmark_run_id == "benchmark-ready"
    assert raw.events_df.event_id.tolist() == ["event-1"]
    assert raw.products_df.product_id.tolist() == [1001]
    assert raw.orders_df.order_id.tolist() == [1]
    assert raw.cold_product_ids == (1010,)
    assert raw.benchmark_metadata.spec_sha256 == "a" * 64
