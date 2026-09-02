"""Strict adapter from an admitted v5 export bundle to a canonical snapshot."""

from __future__ import annotations

import calendar
import math
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    load_strict_json,
    loads_strict_json,
    sha256_file,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SOURCE_DATA_FILES = (
    "benchmark_spec.json",
    "users.jsonl",
    "items.jsonl",
    "events.jsonl",
    "baskets.jsonl",
)
_SOURCE_FILES = {"source_manifest.json", *_SOURCE_DATA_FILES}
_COUNT_FIELDS = {
    "users",
    "items",
    "events",
    "baskets",
    "cold_items",
    "train_events",
    "val_events",
    "test_events",
}


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise IntegrityError(f"{label} fields do not match the source contract")


def _string(value: dict[str, Any], key: str, label: str) -> str:
    parsed = value.get(key)
    if not isinstance(parsed, str) or not parsed:
        raise IntegrityError(f"{label}.{key} must be a non-empty string")
    return parsed


def _nullable_string(value: dict[str, Any], key: str, label: str) -> str | None:
    parsed = value.get(key)
    if parsed is None:
        return None
    if not isinstance(parsed, str) or not parsed:
        raise IntegrityError(f"{label}.{key} must be null or a non-empty string")
    return parsed


def _integer(value: dict[str, Any], key: str, label: str, *, minimum: int = 0) -> int:
    parsed = value.get(key)
    if isinstance(parsed, bool) or not isinstance(parsed, int) or parsed < minimum:
        raise IntegrityError(f"{label}.{key} must be an integer >= {minimum}")
    return parsed


def _number(value: dict[str, Any], key: str, label: str, *, minimum: float = 0.0) -> float:
    parsed = value.get(key)
    if (
        isinstance(parsed, bool)
        or not isinstance(parsed, (int, float))
        or not math.isfinite(float(parsed))
        or float(parsed) < minimum
    ):
        raise IntegrityError(f"{label}.{key} must be a finite number >= {minimum}")
    return float(parsed)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read source JSONL: {path}") from error
    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        if not line.strip():
            raise IntegrityError(f"blank source JSONL line at {path}:{line_number}")
        rows.append(loads_strict_json(line, source=f"{path}:{line_number}"))
    return rows


def _timestamp(value: str, label: str) -> int:
    if not value.endswith("Z"):
        raise IntegrityError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise IntegrityError(f"{label} is not a valid timestamp") from error
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise IntegrityError(f"{label} must use UTC")
    return calendar.timegm(parsed.utctimetuple()) * 1_000_000 + parsed.microsecond


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))


def _load_source_manifest(root: Path) -> tuple[dict[str, Any], dict[str, int]]:
    try:
        actual_files = {path.name for path in root.iterdir()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect source bundle: {root}") from error
    if actual_files != _SOURCE_FILES:
        raise IntegrityError("source bundle file set does not match contract")

    manifest = load_strict_json(root / "source_manifest.json")
    version = _string(manifest, "schema_version", "source_manifest")
    fields = {
        "schema_version",
        "source_bundle_id",
        "source_kind",
        "source_commit",
        "benchmark_run_id",
        "generator_source_tree_sha256",
        "generator_spec_source_sha256",
        "export_query_contract_sha256",
        "file_sha256",
        "expected_counts",
        "catalog_provenance_status",
        "catalog_license_status",
        "catalog_language_status",
        "behavior_nature",
        "observed_behavior",
    }
    if version == "v5-source-bundle/1.1":
        fields |= {"catalog_audit_sha256", "catalog_audit_evidence_sha256"}
    _exact_fields(manifest, fields, "source_manifest")
    if version not in {"v5-source-bundle/1.0", "v5-source-bundle/1.1"}:
        raise IntegrityError("unsupported v5 source bundle schema")
    for key in (
        "source_bundle_id",
        "source_kind",
        "benchmark_run_id",
        "catalog_provenance_status",
        "catalog_license_status",
        "catalog_language_status",
        "behavior_nature",
    ):
        _string(manifest, key, "source_manifest")
    if not _COMMIT.fullmatch(_string(manifest, "source_commit", "source_manifest")):
        raise IntegrityError("source_manifest.source_commit must be a full commit SHA")
    for key in (
        "generator_source_tree_sha256",
        "generator_spec_source_sha256",
        "export_query_contract_sha256",
    ):
        if not _SHA256.fullmatch(_string(manifest, key, "source_manifest")):
            raise IntegrityError(f"source_manifest.{key} must be a SHA-256")
    if version == "v5-source-bundle/1.0":
        fixture_only = manifest["source_commit"] == "0" * 40 and all(
            str(manifest[key]).upper() in {"VERIFIED_TEST_FIXTURE", "TEST_ONLY"}
            for key in (
                "catalog_provenance_status",
                "catalog_license_status",
                "catalog_language_status",
            )
        )
        if not fixture_only:
            raise IntegrityError("v5-source-bundle/1.0 is fixture-only and not runtime-admissible")
    else:
        if not _SHA256.fullmatch(_string(manifest, "catalog_audit_sha256", "source_manifest")):
            raise IntegrityError("source_manifest.catalog_audit_sha256 must be a SHA-256")
        evidence_hashes = manifest.get("catalog_audit_evidence_sha256")
        if (
            not isinstance(evidence_hashes, list)
            or not evidence_hashes
            or any(
                not isinstance(value, str) or not _SHA256.fullmatch(value)
                for value in evidence_hashes
            )
        ):
            raise IntegrityError("catalog audit evidence hashes are invalid")
    observed = manifest.get("observed_behavior")
    if not isinstance(observed, bool):
        raise IntegrityError("source_manifest.observed_behavior must be boolean")

    file_hashes = manifest.get("file_sha256")
    if not isinstance(file_hashes, dict) or set(file_hashes) != set(_SOURCE_DATA_FILES):
        raise IntegrityError("source_manifest.file_sha256 does not cover exact source files")
    for name, expected_hash in file_hashes.items():
        if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
            raise IntegrityError(f"invalid source file hash declaration: {name}")
        if sha256_file(root / name) != expected_hash:
            raise IntegrityError(f"source file hash mismatch: {name}")

    raw_counts = manifest.get("expected_counts")
    if not isinstance(raw_counts, dict) or set(raw_counts) != _COUNT_FIELDS:
        raise IntegrityError("source_manifest.expected_counts fields do not match contract")
    counts = {
        key: _integer(raw_counts, key, "source_manifest.expected_counts")
        for key in sorted(_COUNT_FIELDS)
    }
    return manifest, counts


def _load_spec(root: Path, counts: dict[str, int]) -> tuple[dict[str, int], dict[str, int]]:
    spec = load_strict_json(root / "benchmark_spec.json")
    _exact_fields(
        spec,
        {
            "schema_version",
            "generator_version",
            "seed",
            "store_id",
            "num_users",
            "num_products",
            "num_cold_products",
            "num_events",
            "num_orders",
            "split_counts",
            "cutoffs",
        },
        "benchmark_spec",
    )
    _string(spec, "schema_version", "benchmark_spec")
    _string(spec, "generator_version", "benchmark_spec")
    _integer(spec, "seed", "benchmark_spec")
    _integer(spec, "store_id", "benchmark_spec", minimum=1)
    scalar_bindings = {
        "num_users": "users",
        "num_products": "items",
        "num_cold_products": "cold_items",
        "num_events": "events",
        "num_orders": "baskets",
    }
    for spec_key, count_key in scalar_bindings.items():
        if _integer(spec, spec_key, "benchmark_spec") != counts[count_key]:
            raise IntegrityError(f"benchmark_spec.{spec_key} disagrees with source manifest")

    raw_split_counts = spec.get("split_counts")
    if not isinstance(raw_split_counts, dict) or set(raw_split_counts) != {"train", "val", "test"}:
        raise IntegrityError("benchmark_spec.split_counts fields do not match contract")
    split_counts = {
        split: _integer(raw_split_counts, split, "benchmark_spec.split_counts")
        for split in ("train", "val", "test")
    }
    for split in ("train", "val", "test"):
        if split_counts[split] != counts[f"{split}_events"]:
            raise IntegrityError(f"benchmark_spec {split} count disagrees with source manifest")

    raw_cutoffs = spec.get("cutoffs")
    cutoff_keys = {
        "train_start",
        "train_end",
        "val_start",
        "val_end",
        "test_start",
        "test_end",
    }
    if not isinstance(raw_cutoffs, dict) or set(raw_cutoffs) != cutoff_keys:
        raise IntegrityError("benchmark_spec.cutoffs fields do not match contract")
    cutoffs = {
        key: _timestamp(_string(raw_cutoffs, key, "benchmark_spec.cutoffs"), f"cutoffs.{key}")
        for key in sorted(cutoff_keys)
    }
    if not (
        cutoffs["train_start"]
        <= cutoffs["train_end"]
        < cutoffs["val_start"]
        <= cutoffs["val_end"]
        < cutoffs["test_start"]
        <= cutoffs["test_end"]
    ):
        raise IntegrityError("benchmark split cutoffs overlap or are out of order")
    return split_counts, cutoffs


def _split_for(timestamp: int, cutoffs: dict[str, int]) -> str:
    for split in ("train", "val", "test"):
        if cutoffs[f"{split}_start"] <= timestamp <= cutoffs[f"{split}_end"]:
            return split
    raise IntegrityError("source event timestamp is outside all frozen split intervals")


def materialize_v5_source_bundle(source_root: Path, output_root: Path) -> Snapshot:
    """Verify one immutable export and publish a canonical seven-file snapshot.

    The adapter is deliberately file-only. It never connects to PostgreSQL,
    generates behavior, or opens a benchmark TEST result.
    """

    source = source_root.resolve()
    target = output_root.resolve()
    if source == target:
        raise IntegrityError("source bundle and canonical output roots must differ")
    if target.exists():
        raise IntegrityError(f"canonical output already exists: {target}")
    manifest, counts = _load_source_manifest(source)
    split_counts, cutoffs = _load_spec(source, counts)

    user_rows = _read_jsonl(source / "users.jsonl")
    if len(user_rows) != counts["users"]:
        raise IntegrityError("source user count does not match manifest")
    raw_users: list[int] = []
    for index, row in enumerate(user_rows):
        _exact_fields(row, {"raw_user_id"}, f"users[{index}]")
        raw_users.append(_integer(row, "raw_user_id", f"users[{index}]", minimum=1))
    if len(set(raw_users)) != len(raw_users):
        raise IntegrityError("source users contain duplicate raw IDs")
    raw_users.sort()
    user_map = {raw_id: internal_id for internal_id, raw_id in enumerate(raw_users)}
    canonical_users = [{"user_id": user_map[raw_id], "raw_user_id": raw_id} for raw_id in raw_users]

    item_rows = _read_jsonl(source / "items.jsonl")
    if len(item_rows) != counts["items"]:
        raise IntegrityError("source item count does not match manifest")
    source_items: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(item_rows):
        label = f"items[{index}]"
        _exact_fields(
            row,
            {"raw_item_id", "name", "category", "vendor", "price", "partition"},
            label,
        )
        raw_id = _integer(row, "raw_item_id", label, minimum=1)
        if raw_id in source_items:
            raise IntegrityError("source items contain duplicate raw IDs")
        for key in ("name", "category", "vendor"):
            _string(row, key, label)
        partition = _string(row, "partition", label)
        if partition not in {"warm", "cold"}:
            raise IntegrityError(f"{label}.partition is unsupported")
        _number(row, "price", label)
        source_items[raw_id] = row
    raw_items = sorted(source_items)
    item_map = {raw_id: internal_id for internal_id, raw_id in enumerate(raw_items)}
    canonical_items = [
        {
            "item_id": item_map[raw_id],
            "raw_item_id": raw_id,
            "text": _string(source_items[raw_id], "name", f"item[{raw_id}]"),
            "category": _string(source_items[raw_id], "category", f"item[{raw_id}]"),
            "price": _number(source_items[raw_id], "price", f"item[{raw_id}]"),
        }
        for raw_id in raw_items
    ]
    cold_item_ids = tuple(
        item_map[raw_id] for raw_id in raw_items if source_items[raw_id]["partition"] == "cold"
    )
    if len(cold_item_ids) != counts["cold_items"]:
        raise IntegrityError("source cold-item count does not match manifest")

    event_rows = _read_jsonl(source / "events.jsonl")
    if len(event_rows) != counts["events"]:
        raise IntegrityError("source event count does not match manifest")
    canonical_splits: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    event_ids: set[str] = set()
    previous_event_key: tuple[int, str] | None = None
    for event_id, row in enumerate(event_rows):
        label = f"events[{event_id}]"
        _exact_fields(
            row,
            {
                "raw_event_id",
                "raw_user_id",
                "raw_item_id",
                "event_type",
                "event_ts",
                "event_origin",
                "session_id",
                "cohort_id",
                "persona_cluster",
                "interaction_weight",
            },
            label,
        )
        raw_event_id = _string(row, "raw_event_id", label)
        if raw_event_id in event_ids:
            raise IntegrityError("source events contain duplicate raw event IDs")
        event_ids.add(raw_event_id)
        raw_user_id = _integer(row, "raw_user_id", label, minimum=1)
        raw_item_id = _integer(row, "raw_item_id", label, minimum=1)
        if raw_user_id not in user_map or raw_item_id not in item_map:
            raise IntegrityError(f"{label} references an unknown raw ID")
        event_type = _string(row, "event_type", label)
        if event_type not in {"view", "purchase"}:
            raise IntegrityError(f"{label}.event_type is unsupported")
        origin = _string(row, "event_origin", label)
        if origin not in {"organic", "semantic_trap", "cold_start"}:
            raise IntegrityError(f"{label}.event_origin is unsupported")
        timestamp = _timestamp(_string(row, "event_ts", label), f"{label}.event_ts")
        event_key = (timestamp, raw_event_id)
        if previous_event_key is not None and event_key < previous_event_key:
            raise IntegrityError("source events must be ordered by timestamp and raw_event_id")
        previous_event_key = event_key
        _integer(row, "persona_cluster", label)
        _number(row, "interaction_weight", label)
        split = _split_for(timestamp, cutoffs)
        canonical_splits[split].append(
            {
                "event_id": event_id,
                "raw_event_id": raw_event_id,
                "user_id": user_map[raw_user_id],
                "item_id": item_map[raw_item_id],
                "timestamp": timestamp,
                "event_type": event_type,
                "basket_id": None,
                "event_origin": origin,
                "session_id": _string(row, "session_id", label),
                "cohort_id": _nullable_string(row, "cohort_id", label),
            }
        )
    if {split: len(rows) for split, rows in canonical_splits.items()} != split_counts:
        raise IntegrityError("source event split counts do not match benchmark spec")

    basket_rows = _read_jsonl(source / "baskets.jsonl")
    if len(basket_rows) != counts["baskets"]:
        raise IntegrityError("source basket count does not match manifest")
    canonical_baskets: list[dict[str, Any]] = []
    basket_ids: set[str] = set()
    previous_basket_key: tuple[int, str] | None = None
    for index, row in enumerate(basket_rows):
        label = f"baskets[{index}]"
        _exact_fields(
            row,
            {"raw_basket_id", "raw_user_id", "basket_ts", "basket_origin", "raw_item_ids"},
            label,
        )
        basket_id = _string(row, "raw_basket_id", label)
        if basket_id in basket_ids:
            raise IntegrityError("source baskets contain duplicate IDs")
        basket_ids.add(basket_id)
        raw_user_id = _integer(row, "raw_user_id", label, minimum=1)
        if raw_user_id not in user_map:
            raise IntegrityError(f"{label} references an unknown user")
        raw_basket_items = row.get("raw_item_ids")
        if (
            not isinstance(raw_basket_items, list)
            or len(raw_basket_items) < 2
            or any(isinstance(item, bool) or not isinstance(item, int) for item in raw_basket_items)
            or len(set(raw_basket_items)) != len(raw_basket_items)
            or any(item not in item_map for item in raw_basket_items)
        ):
            raise IntegrityError(f"{label}.raw_item_ids must contain known unique items")
        origin = _string(row, "basket_origin", label)
        if origin not in {"organic", "semantic_trap"}:
            raise IntegrityError(f"{label}.basket_origin is unsupported")
        timestamp = _timestamp(_string(row, "basket_ts", label), f"{label}.basket_ts")
        if not cutoffs["train_start"] <= timestamp <= cutoffs["train_end"]:
            raise IntegrityError("all source baskets must be inside the frozen TRAIN interval")
        basket_key = (timestamp, basket_id)
        if previous_basket_key is not None and basket_key < previous_basket_key:
            raise IntegrityError("source baskets must be ordered by timestamp and ID")
        previous_basket_key = basket_key
        canonical_baskets.append(
            {
                "basket_id": basket_id,
                "user_id": user_map[raw_user_id],
                "timestamp": timestamp,
                "item_ids": sorted(item_map[item] for item in raw_basket_items),
                "origin": origin,
            }
        )

    feature_rows = {
        "text": [{"item_id": row["item_id"], "text": row["text"]} for row in canonical_items],
        "category": [
            {"item_id": row["item_id"], "category": row["category"]} for row in canonical_items
        ],
        "price": [{"item_id": row["item_id"], "price": row["price"]} for row in canonical_items],
    }
    payload = {
        "users": canonical_users,
        "items": canonical_items,
        "training_baskets": canonical_baskets,
        "splits": {split: canonical_splits[split] for split in ("train", "val", "test")},
    }
    source_hashes = {
        "source_manifest.json": sha256_file(source / "source_manifest.json"),
        "generator_spec_source": manifest["generator_spec_source_sha256"],
        **{name: str(manifest["file_sha256"][name]) for name in _SOURCE_DATA_FILES},
    }
    if manifest["schema_version"] == "v5-source-bundle/1.1":
        source_hashes["catalog_audit"] = manifest["catalog_audit_sha256"]
        for index, value in enumerate(manifest["catalog_audit_evidence_sha256"]):
            source_hashes[f"catalog_audit_evidence_{index:03d}"] = value
    manifest_mapping: dict[str, Any] = {
        "schema_version": "dataset-manifest/1.1",
        "dataset_id": f"{manifest['benchmark_run_id']}-canonical",
        "source_kind": manifest["source_kind"],
        "source_locator": manifest["source_bundle_id"],
        "dataset_sha256": canonical_json_sha256(payload),
        "num_users": len(canonical_users),
        "num_items": len(canonical_items),
        "num_interactions": len(event_rows),
        "num_cold_items": len(cold_item_ids),
        "raw_user_map_sha256": canonical_json_sha256({"raw_user_ids": raw_users}),
        "raw_item_map_sha256": canonical_json_sha256({"raw_item_ids": raw_items}),
        "split_hashes": {
            split: canonical_json_sha256({"split": split, "rows": canonical_splits[split]})
            for split in ("train", "val", "test")
        },
        "item_feature_hashes": {
            feature: canonical_json_sha256({feature: rows})
            for feature, rows in feature_rows.items()
        },
        "cold_item_ids": list(cold_item_ids),
        "event_schema": [
            "event_id",
            "raw_event_id",
            "user_id",
            "item_id",
            "timestamp",
            "event_type",
            "basket_id",
            "event_origin",
            "session_id",
            "cohort_id",
        ],
        "id_convention": "dense_zero_based_internal_raw_ids_preserved",
        "basket_field": "baskets.jsonl",
        "provenance_status": manifest["catalog_provenance_status"],
        "license_status": manifest["catalog_license_status"],
        "source_bundle_sha256": canonical_json_sha256(manifest),
        "source_artifact_hashes": source_hashes,
        "num_baskets": len(canonical_baskets),
        "basket_sha256": canonical_json_sha256({"training_baskets": canonical_baskets}),
        "behavior_nature": manifest["behavior_nature"],
        "observed_behavior": manifest["observed_behavior"],
        "language_status": manifest["catalog_language_status"],
    }
    canonical_manifest = DatasetManifest.from_mapping(manifest_mapping)

    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        raise IntegrityError(f"canonical staging root already exists: {staging}")
    try:
        staging.mkdir(parents=True)
        _write_json(staging / "manifest.json", canonical_manifest.to_mapping())
        _write_jsonl(staging / "users.jsonl", canonical_users)
        _write_jsonl(staging / "items.jsonl", canonical_items)
        _write_jsonl(staging / "baskets.jsonl", canonical_baskets)
        for split in ("train", "val", "test"):
            _write_jsonl(staging / f"{split}.jsonl", canonical_splits[split])
        load_canonical_snapshot(staging)
        staging.replace(target)
    except (OSError, IntegrityError):
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return load_canonical_snapshot(target)


__all__ = ["materialize_v5_source_bundle"]
