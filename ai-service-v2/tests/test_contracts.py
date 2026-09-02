from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.hashing import canonical_json_sha256, load_strict_json


def test_manifest_round_trip(snapshot: Snapshot) -> None:
    restored = DatasetManifest.from_mapping(snapshot.manifest.to_mapping())
    assert restored == snapshot.manifest
    assert len(canonical_json_sha256(restored.to_mapping())) == 64


def test_manifest_rejects_unknown_field(snapshot: Snapshot) -> None:
    value = snapshot.manifest.to_mapping()
    value["legacy_model_result"] = 0.99
    with pytest.raises(ContractError, match="unknown contract fields"):
        DatasetManifest.from_mapping(value)


def test_manifest_rejects_cold_count_mismatch(snapshot: Snapshot) -> None:
    value = snapshot.manifest.to_mapping()
    value["num_cold_items"] = 2
    with pytest.raises(ContractError, match="num_cold_items"):
        DatasetManifest.from_mapping(value)


def test_strict_json_rejects_duplicate_case_and_bom(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(IntegrityError, match="duplicate"):
        load_strict_json(duplicate)

    collision = tmp_path / "collision.json"
    collision.write_text('{"A": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(IntegrityError, match="case-colliding"):
        load_strict_json(collision)

    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(IntegrityError, match="BOM"):
        load_strict_json(bom)


def test_strict_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "valid.json"
    path.write_text(json.dumps({"value": 1}), encoding="utf-8")
    assert load_strict_json(path) == {"value": 1}
