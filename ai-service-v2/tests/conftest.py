from __future__ import annotations

import hashlib

import pytest

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.snapshot import Interaction, ItemRecord, Snapshot


def fake_sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture
def snapshot() -> Snapshot:
    manifest = DatasetManifest(
        schema_version="dataset-manifest/1.0",
        dataset_id="fixture-retail-v1",
        source_kind="fixture",
        source_locator="tests/fixtures/fixture-retail-v1",
        dataset_sha256=fake_sha("dataset"),
        num_users=4,
        num_items=5,
        num_interactions=10,
        num_cold_items=1,
        raw_user_map_sha256=fake_sha("users"),
        raw_item_map_sha256=fake_sha("items"),
        split_hashes={
            "train": fake_sha("train"),
            "val": fake_sha("val"),
            "test": fake_sha("test"),
        },
        item_feature_hashes={
            "text": fake_sha("text"),
            "category": fake_sha("category"),
            "price": fake_sha("price"),
        },
        cold_item_ids=(4,),
        event_schema=("event_id", "user_id", "item_id", "timestamp", "event_type", "basket_id"),
        id_convention="dense_zero_based_internal_raw_ids_preserved",
        basket_field="basket_id",
        provenance_status="FIXTURE_ONLY",
        license_status="TEST_ONLY",
    )
    train = (
        Interaction(0, 0, 0, 1, "purchase", "basket-a"),
        Interaction(1, 0, 1, 2, "purchase", "basket-a"),
        Interaction(2, 1, 1, 3, "purchase", "basket-b"),
        Interaction(3, 1, 2, 4, "purchase", "basket-b"),
        Interaction(4, 2, 2, 5, "purchase", "basket-c"),
        Interaction(5, 2, 3, 6, "purchase", "basket-c"),
    )
    val = (
        Interaction(6, 0, 2, 7, "purchase", "basket-d"),
        Interaction(7, 1, 3, 8, "purchase", "basket-e"),
    )
    test = (
        Interaction(8, 0, 3, 9, "purchase", "basket-f"),
        Interaction(9, 1, 4, 10, "purchase", "basket-g"),
    )
    item_records = {
        item_id: ItemRecord(item_id, raw_id, f"item {item_id}", "category", float(item_id + 1))
        for item_id, raw_id in enumerate((100, 50, 75, 25, 10))
    }
    return Snapshot.from_fixture(
        manifest,
        {"train": train, "val": val, "test": test},
        item_records,
        raw_item_ids=(100, 50, 75, 25, 10),
    )
