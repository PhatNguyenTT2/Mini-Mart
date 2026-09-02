from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from ai_service_v2.adapters.v5_family_view import materialize_v5_family_view
from ai_service_v2.adapters.v5_source import materialize_v5_source_bundle
from ai_service_v2.cli import main
from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, sha256_bytes
from tests.source_bundle_fixture import build_v5_source_bundle


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> bytes:
    payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    path.write_bytes(payload)
    return payload


def _build_family_inputs(root: Path) -> tuple[Path, Path, Path, Path]:
    source = build_v5_source_bundle(root / "source")
    parent_root = root / "parent"
    parent = materialize_v5_source_bundle(source, parent_root)

    policy = {
        "text_source": "FAMILY_ANCHOR_NAME_PLUS_CATEGORY",
        "category_source": "PARENT_V5_CATEGORY",
        "price_source": "FAMILY_ANCHOR_PRICE_AND_GLOBAL_FAMILY_QUARTILE",
        "raw_name_usage": "LINEAGE_ONLY_EXCLUDED_FROM_MODEL",
        "raw_price_usage": "LINEAGE_ONLY_EXCLUDED_FROM_MODEL",
        "vendor_usage": "FAMILY_MAPPING_ONLY_NOT_A_SEPARATE_MODEL_FEATURE",
        "family_id_usage": "AUDIT_ONLY_NOT_A_MODEL_FEATURE",
        "sku_identity": "PARENT_V5_RAW_ITEM_ID_PRESERVED",
    }
    scope = {
        "behavior_nature": "CONTROLLED_GENERATED_BEHAVIOR",
        "observed_behavior": False,
        "primary_scope": "INTERNAL_WARM_ITEM_CONTROLLED_COMPARISON",
        "cold_item_scope": "DIAGNOSTIC_NOT_PRIMARY",
        "production_realism_claim_authorized": False,
        "external_validity_claim_authorized": False,
        "test_set_opened": False,
    }
    amendment = {
        "schema_version": "benchmark-dataset-amendment/1.0",
        "dataset_version": "v5.1",
        "generator_version": "5.1.0",
        "parent_generator_version": "5.0.0",
        "seed": 42,
        "num_users": parent.manifest.num_users,
        "num_products": parent.manifest.num_items,
        "num_product_families": 5,
        "num_cold_products": parent.manifest.num_cold_items,
        "num_events": parent.manifest.num_interactions,
        "num_orders": parent.manifest.num_baskets,
        "split_counts": {
            split: len(parent.events_by_split[split]) for split in ("train", "val", "test")
        },
        "catalog_seed_path": "fixture/catalog.sql",
        "catalog_seed_sha256": "1" * 64,
        "parent_source_items_sha256": parent.manifest.source_artifact_hashes["items.jsonl"],
        "parent_dataset_sha256": parent.manifest.dataset_sha256,
        "parent_dataset_manifest_sha256": canonical_json_sha256(parent.manifest.to_mapping()),
        "behavior_artifact_policy": "REUSE_PARENT_V5_EXACT_BYTES_BY_HASH",
        "family_anchor_ranges": [
            {"start": 10, "end": 10},
            {"start": 25, "end": 25},
            {"start": 50, "end": 50},
            {"start": 75, "end": 75},
            {"start": 100, "end": 100},
        ],
        "ambiguous_family_groups": [],
        "model_feature_policy": policy,
        "scientific_scope": scope,
    }
    amendment_path = root / "benchmark-spec-v5.1.json"
    _write_json(amendment_path, amendment)

    family_root = root / "family-view"
    family_root.mkdir()
    family_rows: list[dict[str, Any]] = []
    anchors = {item.raw_item_id: item for item in parent.item_records.values()}
    for item_id in parent.items:
        item = parent.item_records[item_id]
        family_id = item.raw_item_id
        anchor = anchors[family_id]
        family_rows.append(
            {
                "raw_item_id": item.raw_item_id,
                "family_id": family_id,
                "model_text": f"{anchor.text}. Danh mục: {anchor.category}.",
                "category": item.category,
                "model_price": float(anchor.price or 0.0),
                "price_bucket": {10: 0, 25: 0, 50: 1, 75: 2, 100: 3}[family_id],
                "partition": "cold" if item_id in parent.cold_item_ids else "warm",
                "raw_item_sha256": sha256_bytes(f"raw-{item.raw_item_id}".encode()),
            }
        )
    family_bytes = _write_jsonl(family_root / "catalog_family_view.jsonl", family_rows)
    family_manifest = {
        "schema_version": "catalog-family-view/1.0",
        "dataset_version": "v5.1",
        "parent_dataset_sha256": amendment["parent_dataset_sha256"],
        "parent_dataset_manifest_sha256": amendment["parent_dataset_manifest_sha256"],
        "parent_source_items_sha256": amendment["parent_source_items_sha256"],
        "policy_sha256": sha256_bytes(canonical_json_bytes(amendment) + b"\n"),
        "catalog_family_view_sha256": sha256_bytes(family_bytes),
        "num_products": 5,
        "num_product_families": 5,
        "num_cold_products": 1,
        "minimum_family_size": 1,
        "maximum_family_size": 1,
        "model_feature_policy": policy,
        "scientific_scope": scope,
        "behavior_artifact_policy": "REUSE_PARENT_V5_EXACT_BYTES_BY_HASH",
        "test_set_opened": False,
        "accepted_result_rows": 0,
    }
    _write_json(family_root / "catalog_family_view_manifest.json", family_manifest)
    return parent_root, family_root, amendment_path, root / "output"


def test_v5_family_view_materializes_and_preserves_behavior_bytes(tmp_path: Path) -> None:
    parent_root, family_root, amendment_path, output_root = _build_family_inputs(tmp_path)

    parent_bytes = {
        name: (parent_root / name).read_bytes()
        for name in ("users.jsonl", "baskets.jsonl", "train.jsonl", "val.jsonl", "test.jsonl")
    }
    snapshot = materialize_v5_family_view(
        parent_root, family_root, output_root, amendment_path=amendment_path
    )

    assert snapshot.manifest.dataset_id.endswith("-v5.1-family-view")
    assert snapshot.manifest.dataset_sha256 != snapshot.manifest.source_bundle_sha256
    assert snapshot.item_records[0].text.endswith(". Danh mục: cold.")
    parent_snapshot = load_canonical_snapshot(parent_root)
    assert snapshot.item_records[0].text != parent_snapshot.item_records[0].text
    for name, expected in parent_bytes.items():
        assert (output_root / name).read_bytes() == expected
    assert {path.name for path in output_root.iterdir()} == {
        "manifest.json",
        "items.jsonl",
        "users.jsonl",
        "baskets.jsonl",
        "train.jsonl",
        "val.jsonl",
        "test.jsonl",
    }


def test_v5_family_view_rejects_catalog_hash_mutation(tmp_path: Path) -> None:
    parent_root, family_root, amendment_path, output_root = _build_family_inputs(tmp_path)
    view_path = family_root / "catalog_family_view.jsonl"
    view_path.write_bytes(view_path.read_bytes().replace(b"cold item", b"changed item", 1))

    with pytest.raises(IntegrityError, match="file hash"):
        materialize_v5_family_view(
            parent_root, family_root, output_root, amendment_path=amendment_path
        )


def test_v5_family_view_rejects_partition_drift_even_when_file_hash_is_updated(
    tmp_path: Path,
) -> None:
    parent_root, family_root, amendment_path, output_root = _build_family_inputs(tmp_path)
    view_path = family_root / "catalog_family_view.jsonl"
    rows = [json.loads(line) for line in view_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["partition"] = "warm" if rows[0]["partition"] == "cold" else "cold"
    family_bytes = _write_jsonl(view_path, rows)
    manifest_path = family_root / "catalog_family_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["catalog_family_view_sha256"] = sha256_bytes(family_bytes)
    _write_json(manifest_path, manifest)

    with pytest.raises(IntegrityError, match="cold partition"):
        materialize_v5_family_view(
            parent_root, family_root, output_root, amendment_path=amendment_path
        )


def test_v5_family_view_rejects_mutated_parent_behavior(tmp_path: Path) -> None:
    parent_root, family_root, amendment_path, output_root = _build_family_inputs(tmp_path)
    mutated_parent = tmp_path / "mutated-parent"
    shutil.copytree(parent_root, mutated_parent)
    behavior = mutated_parent / "train.jsonl"
    behavior.write_bytes(behavior.read_bytes().replace(b'"event_id":0', b'"event_id":1', 1))

    with pytest.raises(IntegrityError, match=r"payload hash|duplicate event"):
        materialize_v5_family_view(
            mutated_parent, family_root, output_root, amendment_path=amendment_path
        )


def test_cli_materializes_v5_family_view(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parent_root, family_root, amendment_path, output_root = _build_family_inputs(tmp_path)

    assert (
        main(
            [
                "materialize-v5-family-view",
                str(parent_root),
                str(family_root),
                str(output_root),
                "--amendment",
                str(amendment_path),
            ]
        )
        == 0
    )
    assert '"status": "PASS"' in capsys.readouterr().out
