from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_service.config import Settings
from ai_service.data.snapshot import SnapshotBuilder
from ai_service.data.sources import PostgresDatasetSource, SyntheticDatasetSource
from ai_service.errors import SourceReadError
from tests.support.v5_factories import make_settings


def _raw(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings.data.expected_event_count = 20
    settings.data.expected_train_count = 10
    settings.data.expected_val_count = 5
    settings.data.expected_test_count = 5
    settings.data.expected_order_count = 1
    settings.data.num_users = 4
    settings.data.num_items = 12
    settings.data.num_cold_items = 4
    dataset = SyntheticDatasetSource(settings, num_events=20).load(1, "snapshot-edge")
    return settings, dataset


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("missing_event", "missing event columns"),
        ("catalog_count", "catalog count"),
        ("duplicate_product", "product_id must be unique"),
        ("event_count", "event count"),
        ("duplicate_event", "event_id must be unique"),
        ("event_type", "event_type must be"),
        ("session", "session_id must be"),
        ("origin", "event_origin"),
        ("weight", "interaction weights"),
        ("store", "event store"),
        ("benchmark", "another benchmark"),
    ],
)
def test_snapshot_builder_rejects_invalid_raw_contracts(
    tmp_path: Path, mutation: str, message: str
) -> None:
    settings, raw = _raw(tmp_path)
    events = raw.events_df.copy()
    products = raw.products_df.copy()
    if mutation == "missing_event":
        events = events.drop(columns=["session_id"])
    elif mutation == "catalog_count":
        products = products.iloc[:-1]
    elif mutation == "duplicate_product":
        products.loc[1, "product_id"] = products.loc[0, "product_id"]
    elif mutation == "event_count":
        events = events.iloc[:-1]
    elif mutation == "duplicate_event":
        events.loc[1, "event_id"] = events.loc[0, "event_id"]
    elif mutation == "event_type":
        events.loc[0, "event_type"] = "click"
    elif mutation == "session":
        events.loc[0, "session_id"] = ""
    elif mutation == "origin":
        events.loc[0, "event_origin"] = "unknown"
    elif mutation == "weight":
        events.loc[0, "interaction_weight"] = 9.0
    elif mutation == "store":
        events.loc[0, "store_id"] = 99
    elif mutation == "benchmark":
        events.loc[0, "benchmark_run_id"] = "other"
    broken = replace(raw, events_df=events, products_df=products)
    with pytest.raises(Exception, match=message):
        SnapshotBuilder(settings).build(broken, snapshot_id=f"broken-{mutation}")


def test_source_configuration_guards(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    with pytest.raises(SourceReadError, match="all three"):
        PostgresDatasetSource(settings).load(1)
    settings.data.num_items = 2
    settings.data.num_cold_items = 2
    settings.data.expected_event_count = 1
    settings.data.expected_train_count = 1
    settings.data.expected_val_count = 0
    settings.data.expected_test_count = 0
    with pytest.raises(SourceReadError, match="test split"):
        SyntheticDatasetSource(settings, num_events=1).load(1)
