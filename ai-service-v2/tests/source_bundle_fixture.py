from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_service_v2.hashing import canonical_json_bytes, sha256_file


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))


def build_v5_source_bundle(root: Path) -> Path:
    root.mkdir()
    spec = {
        "schema_version": "3.0.0",
        "generator_version": "5.0.0",
        "seed": 42,
        "store_id": 1,
        "num_users": 4,
        "num_products": 5,
        "num_cold_products": 1,
        "num_events": 10,
        "num_orders": 2,
        "split_counts": {"train": 6, "val": 2, "test": 2},
        "cutoffs": {
            "train_start": "2026-01-01T00:00:00.000Z",
            "train_end": "2026-06-19T23:59:59.000Z",
            "val_start": "2026-06-20T00:00:00.000Z",
            "val_end": "2026-07-10T23:59:59.000Z",
            "test_start": "2026-07-11T00:00:00.000Z",
            "test_end": "2026-08-01T23:59:59.000Z",
        },
    }
    users = [{"raw_user_id": value} for value in (10, 20, 30, 40)]
    items = [
        {
            "raw_item_id": 10,
            "name": "cold item",
            "category": "cold",
            "vendor": "fixture",
            "price": 1.0,
            "partition": "cold",
        },
        {
            "raw_item_id": 25,
            "name": "semantic target",
            "category": "semantic",
            "vendor": "fixture",
            "price": 2.0,
            "partition": "warm",
        },
        {
            "raw_item_id": 50,
            "name": "organic context",
            "category": "organic",
            "vendor": "fixture",
            "price": 3.0,
            "partition": "warm",
        },
        {
            "raw_item_id": 75,
            "name": "organic validation target",
            "category": "organic",
            "vendor": "fixture",
            "price": 4.0,
            "partition": "warm",
        },
        {
            "raw_item_id": 100,
            "name": "organic companion",
            "category": "organic",
            "vendor": "fixture",
            "price": 5.0,
            "partition": "warm",
        },
    ]
    events = [
        {
            "raw_event_id": "event-000",
            "raw_user_id": 10,
            "raw_item_id": 50,
            "event_type": "view",
            "event_ts": "2026-01-02T00:00:00.000Z",
            "event_origin": "organic",
            "session_id": "session-a",
            "cohort_id": None,
            "persona_cluster": 0,
            "interaction_weight": 0.5,
        },
        {
            "raw_event_id": "event-001",
            "raw_user_id": 10,
            "raw_item_id": 50,
            "event_type": "purchase",
            "event_ts": "2026-01-02T00:00:01.000Z",
            "event_origin": "organic",
            "session_id": "session-a",
            "cohort_id": None,
            "persona_cluster": 0,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-002",
            "raw_user_id": 20,
            "raw_item_id": 25,
            "event_type": "view",
            "event_ts": "2026-01-03T00:00:00.000Z",
            "event_origin": "semantic_trap",
            "session_id": "session-b",
            "cohort_id": "semantic-1",
            "persona_cluster": 1,
            "interaction_weight": 0.5,
        },
        {
            "raw_event_id": "event-003",
            "raw_user_id": 30,
            "raw_item_id": 100,
            "event_type": "purchase",
            "event_ts": "2026-01-04T00:00:00.000Z",
            "event_origin": "organic",
            "session_id": "session-c",
            "cohort_id": None,
            "persona_cluster": 2,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-004",
            "raw_user_id": 40,
            "raw_item_id": 50,
            "event_type": "view",
            "event_ts": "2026-01-05T00:00:00.000Z",
            "event_origin": "organic",
            "session_id": "session-d",
            "cohort_id": None,
            "persona_cluster": 3,
            "interaction_weight": 0.5,
        },
        {
            "raw_event_id": "event-005",
            "raw_user_id": 40,
            "raw_item_id": 100,
            "event_type": "purchase",
            "event_ts": "2026-01-05T00:00:01.000Z",
            "event_origin": "organic",
            "session_id": "session-d",
            "cohort_id": None,
            "persona_cluster": 3,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-006",
            "raw_user_id": 10,
            "raw_item_id": 75,
            "event_type": "purchase",
            "event_ts": "2026-06-21T00:00:00.000Z",
            "event_origin": "organic",
            "session_id": "session-e",
            "cohort_id": None,
            "persona_cluster": 0,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-007",
            "raw_user_id": 20,
            "raw_item_id": 25,
            "event_type": "purchase",
            "event_ts": "2026-06-22T00:00:00.000Z",
            "event_origin": "semantic_trap",
            "session_id": "session-f",
            "cohort_id": "semantic-1",
            "persona_cluster": 1,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-008",
            "raw_user_id": 10,
            "raw_item_id": 10,
            "event_type": "purchase",
            "event_ts": "2026-07-12T00:00:00.000Z",
            "event_origin": "cold_start",
            "session_id": "session-g",
            "cohort_id": "cold-1",
            "persona_cluster": 0,
            "interaction_weight": 1.0,
        },
        {
            "raw_event_id": "event-009",
            "raw_user_id": 30,
            "raw_item_id": 75,
            "event_type": "purchase",
            "event_ts": "2026-07-13T00:00:00.000Z",
            "event_origin": "organic",
            "session_id": "session-h",
            "cohort_id": None,
            "persona_cluster": 2,
            "interaction_weight": 1.0,
        },
    ]
    baskets = [
        {
            "raw_basket_id": "order-organic",
            "raw_user_id": 10,
            "basket_ts": "2026-02-01T00:00:00.000Z",
            "basket_origin": "organic",
            "raw_item_ids": [50, 100],
        },
        {
            "raw_basket_id": "order-semantic",
            "raw_user_id": 20,
            "basket_ts": "2026-02-02T00:00:00.000Z",
            "basket_origin": "semantic_trap",
            "raw_item_ids": [25, 75],
        },
    ]

    _write_json(root / "benchmark_spec.json", spec)
    _write_jsonl(root / "users.jsonl", users)
    _write_jsonl(root / "items.jsonl", items)
    _write_jsonl(root / "events.jsonl", events)
    _write_jsonl(root / "baskets.jsonl", baskets)
    names = ("benchmark_spec.json", "users.jsonl", "items.jsonl", "events.jsonl", "baskets.jsonl")
    manifest = {
        "schema_version": "v5-source-bundle/1.0",
        "source_bundle_id": "fixture-v5-source-bundle",
        "source_kind": "seed-product-postgres-export",
        "source_commit": "0" * 40,
        "benchmark_run_id": "fixture-benchmark-v5",
        "generator_source_tree_sha256": "1" * 64,
        "generator_spec_source_sha256": sha256_file(root / "benchmark_spec.json"),
        "export_query_contract_sha256": "2" * 64,
        "file_sha256": {name: sha256_file(root / name) for name in names},
        "expected_counts": {
            "users": 4,
            "items": 5,
            "events": 10,
            "baskets": 2,
            "cold_items": 1,
            "train_events": 6,
            "val_events": 2,
            "test_events": 2,
        },
        "catalog_provenance_status": "VERIFIED_TEST_FIXTURE",
        "catalog_license_status": "TEST_ONLY",
        "catalog_language_status": "VERIFIED_TEST_FIXTURE",
        "behavior_nature": "CONTROLLED_GENERATED_BEHAVIOR",
        "observed_behavior": False,
    }
    _write_json(root / "source_manifest.json", manifest)
    return root
