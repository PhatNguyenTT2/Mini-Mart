"""Materialize the v5.1 catalog feature view over an admitted v5 snapshot.

The v5.1 correction is deliberately a feature-view amendment.  It changes
only model-facing item content; users, interactions, baskets, IDs, and split
files are copied from the admitted parent snapshot byte-for-byte.  This
adapter is file-only and does not connect to a database, container runtime, or
network service.
"""

from __future__ import annotations

import hashlib
import math
import re
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
    sha256_bytes,
    sha256_file,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_FAMILY_VIEW_FILES = {"catalog_family_view.jsonl", "catalog_family_view_manifest.json"}
_CANONICAL_FILES = {
    "manifest.json",
    "items.jsonl",
    "users.jsonl",
    "baskets.jsonl",
    "train.jsonl",
    "val.jsonl",
    "test.jsonl",
}
_BEHAVIOR_FILES = ("users.jsonl", "baskets.jsonl", "train.jsonl", "val.jsonl", "test.jsonl")
_FAMILY_ROW_FIELDS = {
    "raw_item_id",
    "family_id",
    "model_text",
    "category",
    "model_price",
    "price_bucket",
    "partition",
    "raw_item_sha256",
}
_FAMILY_MANIFEST_FIELDS = {
    "schema_version",
    "dataset_version",
    "parent_dataset_sha256",
    "parent_dataset_manifest_sha256",
    "parent_source_items_sha256",
    "policy_sha256",
    "catalog_family_view_sha256",
    "num_products",
    "num_product_families",
    "num_cold_products",
    "minimum_family_size",
    "maximum_family_size",
    "model_feature_policy",
    "scientific_scope",
    "behavior_artifact_policy",
    "test_set_opened",
    "accepted_result_rows",
}
_AMENDMENT_FIELDS = {
    "schema_version",
    "dataset_version",
    "generator_version",
    "parent_generator_version",
    "seed",
    "num_users",
    "num_products",
    "num_product_families",
    "num_cold_products",
    "num_events",
    "num_orders",
    "split_counts",
    "catalog_seed_path",
    "catalog_seed_sha256",
    "parent_source_items_sha256",
    "parent_dataset_sha256",
    "parent_dataset_manifest_sha256",
    "behavior_artifact_policy",
    "family_anchor_ranges",
    "ambiguous_family_groups",
    "model_feature_policy",
    "scientific_scope",
}


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unknown:
            details.append("unknown=" + ",".join(unknown))
        raise IntegrityError(f"{label} fields do not match contract ({'; '.join(details)})")


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IntegrityError(f"{label} must be a non-empty string")
    return value


def _sha(value: Any, label: str) -> str:
    parsed = _nonempty_string(value, label)
    if not _SHA256.fullmatch(parsed):
        raise IntegrityError(f"{label} must be a lowercase SHA-256")
    return parsed


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IntegrityError(f"{label} must be an integer >= {minimum}")
    return int(value)


def _finite_number(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntegrityError(f"{label} must be a finite number >= {minimum}")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < minimum:
        raise IntegrityError(f"{label} must be a finite number >= {minimum}")
    return parsed


def _read_canonical_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read JSONL file: {path}") from error
    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    if not payload or not payload.endswith(b"\n"):
        raise IntegrityError(f"JSONL file must be non-empty and end with LF: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(keepends=True), start=1):
        if not line.endswith(b"\n") or line.endswith(b"\r\n"):
            raise IntegrityError(f"JSONL line must use LF only: {path}:{line_number}")
        body = line[:-1]
        if not body:
            raise IntegrityError(f"blank JSONL line: {path}:{line_number}")
        row = loads_strict_json(body, source=f"{path}:{line_number}")
        if body != canonical_json_bytes(row):
            raise IntegrityError(f"JSONL row is not canonical: {path}:{line_number}")
        rows.append(row)
    return rows


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("wb") as stream:
        for row in rows:
            stream.write(canonical_json_bytes(row) + b"\n")


def _expand_anchor_ranges(raw_ranges: Any, *, expected_count: int) -> frozenset[int]:
    if not isinstance(raw_ranges, list):
        raise IntegrityError("family_anchor_ranges must be a list")
    anchors: list[int] = []
    for index, raw_range in enumerate(raw_ranges):
        if not isinstance(raw_range, dict):
            raise IntegrityError(f"family_anchor_ranges[{index}] must be an object")
        _exact_fields(raw_range, {"start", "end"}, f"family_anchor_ranges[{index}]")
        start = _integer(raw_range["start"], f"family_anchor_ranges[{index}].start", minimum=1)
        end = _integer(raw_range["end"], f"family_anchor_ranges[{index}].end", minimum=1)
        if end < start:
            raise IntegrityError(f"family_anchor_ranges[{index}] is reversed")
        anchors.extend(range(start, end + 1))
    if len(anchors) != expected_count or len(set(anchors)) != len(anchors):
        raise IntegrityError("family anchor count or uniqueness does not match amendment")
    return frozenset(anchors)


def _load_amendment(path: Path) -> tuple[dict[str, Any], str, str, frozenset[int]]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read v5.1 amendment: {path}") from error
    if raw.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    amendment = loads_strict_json(raw, source=str(path))
    _exact_fields(amendment, _AMENDMENT_FIELDS, "v5.1 amendment")
    if amendment["schema_version"] != "benchmark-dataset-amendment/1.0":
        raise IntegrityError("unsupported v5.1 amendment schema")
    if amendment["dataset_version"] != "v5.1":
        raise IntegrityError("amendment dataset_version must be v5.1")
    if amendment["behavior_artifact_policy"] != "REUSE_PARENT_V5_EXACT_BYTES_BY_HASH":
        raise IntegrityError("v5.1 amendment may not regenerate parent behavior")
    for field in (
        "catalog_seed_sha256",
        "parent_source_items_sha256",
        "parent_dataset_sha256",
        "parent_dataset_manifest_sha256",
    ):
        _sha(amendment[field], f"v5.1 amendment.{field}")
    for field in (
        "seed",
        "num_users",
        "num_products",
        "num_product_families",
        "num_cold_products",
        "num_events",
        "num_orders",
    ):
        _integer(amendment[field], f"v5.1 amendment.{field}", minimum=1)
    split_counts = amendment.get("split_counts")
    if not isinstance(split_counts, dict) or set(split_counts) != {"train", "val", "test"}:
        raise IntegrityError("v5.1 amendment.split_counts is invalid")
    for split, value in split_counts.items():
        _integer(value, f"v5.1 amendment.split_counts.{split}", minimum=1)
    if sum(split_counts.values()) != amendment["num_events"]:
        raise IntegrityError("v5.1 split counts do not sum to num_events")
    if not isinstance(amendment["model_feature_policy"], dict):
        raise IntegrityError("v5.1 amendment.model_feature_policy must be an object")
    if not isinstance(amendment["scientific_scope"], dict):
        raise IntegrityError("v5.1 amendment.scientific_scope must be an object")
    anchors = _expand_anchor_ranges(
        amendment["family_anchor_ranges"], expected_count=amendment["num_product_families"]
    )
    policy_hash = sha256_bytes(canonical_json_bytes(amendment) + b"\n")
    return amendment, sha256_file(path), policy_hash, anchors


def _validate_family_manifest(
    manifest: dict[str, Any],
    *,
    amendment: dict[str, Any] | None,
    policy_hash: str | None,
) -> None:
    _exact_fields(manifest, _FAMILY_MANIFEST_FIELDS, "family-view manifest")
    if manifest["schema_version"] != "catalog-family-view/1.0":
        raise IntegrityError("unsupported catalog-family-view schema")
    if manifest["dataset_version"] != "v5.1":
        raise IntegrityError("family-view dataset_version must be v5.1")
    for field in (
        "parent_dataset_sha256",
        "parent_dataset_manifest_sha256",
        "parent_source_items_sha256",
        "policy_sha256",
        "catalog_family_view_sha256",
    ):
        _sha(manifest[field], f"family-view manifest.{field}")
    for field in (
        "num_products",
        "num_product_families",
        "num_cold_products",
        "minimum_family_size",
        "maximum_family_size",
        "accepted_result_rows",
    ):
        _integer(manifest[field], f"family-view manifest.{field}")
    if not isinstance(manifest["model_feature_policy"], dict):
        raise IntegrityError("family-view model_feature_policy must be an object")
    if not isinstance(manifest["scientific_scope"], dict):
        raise IntegrityError("family-view scientific_scope must be an object")
    if manifest["behavior_artifact_policy"] != "REUSE_PARENT_V5_EXACT_BYTES_BY_HASH":
        raise IntegrityError("family-view behavior policy is not parent-byte preserving")
    if manifest["test_set_opened"] is not False or manifest["accepted_result_rows"] != 0:
        raise IntegrityError("v5.1 family view cannot open TEST or accept result rows")
    if amendment is not None:
        if manifest["parent_dataset_sha256"] != amendment["parent_dataset_sha256"]:
            raise IntegrityError("family-view parent dataset hash disagrees with amendment")
        if manifest["parent_dataset_manifest_sha256"] != amendment[
            "parent_dataset_manifest_sha256"
        ]:
            raise IntegrityError("family-view parent manifest hash disagrees with amendment")
        if manifest["parent_source_items_sha256"] != amendment["parent_source_items_sha256"]:
            raise IntegrityError("family-view source-item hash disagrees with amendment")
        if manifest["num_products"] != amendment["num_products"]:
            raise IntegrityError("family-view product count disagrees with amendment")
        if manifest["num_product_families"] != amendment["num_product_families"]:
            raise IntegrityError("family-view family count disagrees with amendment")
        if manifest["num_cold_products"] != amendment["num_cold_products"]:
            raise IntegrityError("family-view cold count disagrees with amendment")
        if manifest["model_feature_policy"] != amendment["model_feature_policy"]:
            raise IntegrityError("family-view feature policy disagrees with amendment")
        if manifest["scientific_scope"] != amendment["scientific_scope"]:
            raise IntegrityError("family-view scientific scope disagrees with amendment")
        if policy_hash != manifest["policy_sha256"]:
            raise IntegrityError("family-view policy hash does not match amendment")


def _load_family_view(
    root: Path,
    *,
    amendment: dict[str, Any] | None,
    policy_hash: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str]:
    try:
        actual = {entry.name for entry in root.iterdir()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect family-view root: {root}") from error
    if actual != _FAMILY_VIEW_FILES:
        raise IntegrityError("family-view root does not contain the exact two-file set")
    view_path = root / "catalog_family_view.jsonl"
    manifest_path = root / "catalog_family_view_manifest.json"
    if not view_path.is_file() or not manifest_path.is_file():
        raise IntegrityError("family-view files must be regular files")
    manifest_raw = manifest_path.read_bytes()
    if not manifest_raw.endswith(b"\n") or manifest_raw.endswith(b"\r\n"):
        raise IntegrityError("family-view manifest must use one canonical LF line")
    manifest = loads_strict_json(manifest_raw[:-1], source=str(manifest_path))
    if manifest_raw[:-1] != canonical_json_bytes(manifest):
        raise IntegrityError("family-view manifest is not canonical JSON")
    _validate_family_manifest(manifest, amendment=amendment, policy_hash=policy_hash)
    view_bytes_hash = sha256_file(view_path)
    if view_bytes_hash != manifest["catalog_family_view_sha256"]:
        raise IntegrityError("catalog family-view file hash does not match manifest")
    rows = _read_canonical_jsonl(view_path)
    if len(rows) != manifest["num_products"]:
        raise IntegrityError("family-view row count does not match manifest")
    return manifest, rows, view_bytes_hash, sha256_file(manifest_path)


def _validate_family_rows(
    rows: list[dict[str, Any]],
    *,
    parent: Snapshot,
    family_manifest: dict[str, Any],
    anchor_ids: frozenset[int] | None,
) -> dict[int, dict[str, Any]]:
    by_raw_id: dict[int, dict[str, Any]] = {}
    families: set[int] = set()
    family_sizes: dict[int, int] = {}
    cold_count = 0
    parent_cold = parent.cold_item_ids
    parent_raw_ids = tuple(parent.raw_item_ids)
    parent_internal_by_raw = {raw_id: item_id for item_id, raw_id in enumerate(parent_raw_ids)}
    for index, row in enumerate(rows):
        label = f"family_view[{index}]"
        _exact_fields(row, _FAMILY_ROW_FIELDS, label)
        raw_id = _integer(row["raw_item_id"], f"{label}.raw_item_id", minimum=1)
        if raw_id in by_raw_id:
            raise IntegrityError(f"duplicate family-view raw item ID: {raw_id}")
        family_id = _integer(row["family_id"], f"{label}.family_id", minimum=1)
        model_text = _nonempty_string(row["model_text"], f"{label}.model_text")
        category = _nonempty_string(row["category"], f"{label}.category")
        _finite_number(row["model_price"], f"{label}.model_price")
        price_bucket = _integer(row["price_bucket"], f"{label}.price_bucket")
        if price_bucket > 3:
            raise IntegrityError(f"{label}.price_bucket must be between 0 and 3")
        partition = _nonempty_string(row["partition"], f"{label}.partition")
        if partition not in {"warm", "cold"}:
            raise IntegrityError(f"{label}.partition is unsupported")
        _sha(row["raw_item_sha256"], f"{label}.raw_item_sha256")
        if ". Danh mục: " not in model_text or not model_text.endswith("."):
            raise IntegrityError(f"{label}.model_text lacks the frozen category anchor form")
        if raw_id not in parent.raw_item_ids:
            raise IntegrityError(f"family-view raw item ID is absent from parent: {raw_id}")
        internal_id = parent_internal_by_raw[raw_id]
        parent_item = parent.item_records[internal_id]
        if category != parent_item.category:
            raise IntegrityError(f"{label}.category changes the parent category")
        expected_partition = "cold" if internal_id in parent_cold else "warm"
        if partition != expected_partition:
            raise IntegrityError(f"{label}.partition changes the parent cold partition")
        if (partition == "cold"):
            cold_count += 1
        if anchor_ids is not None and family_id not in anchor_ids:
            raise IntegrityError(f"{label}.family_id is not a frozen family anchor")
        by_raw_id[raw_id] = row
        families.add(family_id)
        family_sizes[family_id] = family_sizes.get(family_id, 0) + 1
    if tuple(sorted(by_raw_id)) != tuple(sorted(parent_raw_ids)):
        raise IntegrityError("family-view raw IDs do not exactly cover the parent catalog")
    if len(families) != family_manifest["num_product_families"]:
        raise IntegrityError("family-view family count does not match manifest")
    if anchor_ids is not None and families != anchor_ids:
        raise IntegrityError("family-view families do not cover exactly the frozen anchors")
    if cold_count != family_manifest["num_cold_products"]:
        raise IntegrityError("family-view cold count does not match manifest")
    sizes = list(family_sizes.values())
    if min(sizes) != family_manifest["minimum_family_size"] or max(sizes) != family_manifest[
        "maximum_family_size"
    ]:
        raise IntegrityError("family-view family-size bounds do not match manifest")

    # The family artifact is source-bound, but its internal mapping is also
    # checked independently of its file hash.  This prevents a rewritten
    # artifact plus rewritten manifest from smuggling a different anchor or
    # price policy into the canonical snapshot.
    anchors: dict[int, dict[str, Any]] = {}
    for family_id in sorted(families):
        anchor = by_raw_id.get(family_id)
        if anchor is None:
            raise IntegrityError(f"family-view is missing anchor row {family_id}")
        anchor_item = parent.item_records[parent_internal_by_raw[family_id]]
        expected_text = f"{anchor_item.text}. Danh mục: {anchor_item.category}."
        if anchor["model_text"] != expected_text:
            raise IntegrityError(f"family anchor {family_id} text is not bound to parent")
        if float(anchor["model_price"]) != float(anchor_item.price or 0.0):
            raise IntegrityError(f"family anchor {family_id} price is not bound to parent")
        if anchor["category"] != anchor_item.category:
            raise IntegrityError(f"family anchor {family_id} category is not bound to parent")
        anchors[family_id] = anchor

    anchor_prices = sorted(float(row["model_price"]) for row in anchors.values())
    boundaries = [
        anchor_prices[min(len(anchor_prices) - 1, int(len(anchor_prices) * quantile))]
        for quantile in (0.25, 0.5, 0.75)
    ]
    for raw_id, row in by_raw_id.items():
        anchor = anchors[row["family_id"]]
        if row["model_text"] != anchor["model_text"]:
            raise IntegrityError(f"item {raw_id} does not use its frozen family text")
        if float(row["model_price"]) != float(anchor["model_price"]):
            raise IntegrityError(f"item {raw_id} does not use its frozen family price")
        if row["category"] != anchor["category"]:
            raise IntegrityError(f"item {raw_id} does not use its frozen family category")
        expected_bucket = sum(float(anchor["model_price"]) > boundary for boundary in boundaries)
        if row["price_bucket"] != expected_bucket:
            raise IntegrityError(f"item {raw_id} has an invalid frozen price bucket")
    return by_raw_id


def _hash_jsonl_array(path: Path) -> bytes:
    """Return canonical bytes for a JSONL array without retaining all rows."""

    try:
        payload = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read behavior file: {path}") from error
    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    lines = payload.splitlines()
    if not lines:
        raise IntegrityError(f"behavior JSONL file is empty: {path}")
    result = bytearray(b"[")
    for index, line in enumerate(lines):
        if not line:
            raise IntegrityError(f"blank behavior JSONL row: {path}:{index + 1}")
        row = loads_strict_json(line, source=f"{path}:{index + 1}")
        if index:
            result.extend(b",")
        result.extend(canonical_json_bytes(row))
    result.extend(b"]")
    return bytes(result)


def _stream_dataset_hash(
    *,
    item_rows: list[dict[str, Any]],
    users_path: Path,
    baskets_path: Path,
    split_paths: dict[str, Path],
) -> str:
    """Hash the same sorted-key JSON object used by ``load_canonical_snapshot``."""

    digest = hashlib.sha256()

    def add(value: bytes) -> None:
        digest.update(value)

    add(b'{"items":[')
    for index, row in enumerate(item_rows):
        if index:
            add(b",")
        add(canonical_json_bytes(row))
    add(b'],"splits":{"test":')
    add(_hash_jsonl_array(split_paths["test"])[0:])
    add(b',"train":')
    add(_hash_jsonl_array(split_paths["train"]))
    add(b',"val":')
    add(_hash_jsonl_array(split_paths["val"]))
    add(b'},"training_baskets":')
    add(_hash_jsonl_array(baskets_path))
    add(b',"users":')
    add(_hash_jsonl_array(users_path))
    add(b"}")
    return digest.hexdigest()


def _feature_hashes(item_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "text": canonical_json_sha256(
            {"text": [{"item_id": row["item_id"], "text": row["text"]} for row in item_rows]}
        ),
        "category": canonical_json_sha256(
            {
                "category": [
                    {"item_id": row["item_id"], "category": row["category"]}
                    for row in item_rows
                ]
            }
        ),
        "price": canonical_json_sha256(
            {"price": [{"item_id": row["item_id"], "price": row["price"]} for row in item_rows]}
        ),
    }


def _verify_parent_binding(
    parent: Snapshot,
    *,
    amendment: dict[str, Any],
) -> None:
    manifest = parent.manifest
    if manifest.schema_version != "dataset-manifest/1.1":
        raise IntegrityError("v5.1 family view requires a dataset-manifest/1.1 parent")
    if manifest.dataset_sha256 != amendment["parent_dataset_sha256"]:
        raise IntegrityError("parent dataset hash does not match v5.1 amendment")
    if canonical_json_sha256(manifest.to_mapping()) != amendment["parent_dataset_manifest_sha256"]:
        raise IntegrityError("parent manifest hash does not match v5.1 amendment")
    if manifest.source_artifact_hashes.get("items.jsonl") != amendment[
        "parent_source_items_sha256"
    ]:
        raise IntegrityError("parent source-item hash is absent or mismatched")
    expected_counts = {
        "num_users": amendment["num_users"],
        "num_items": amendment["num_products"],
        "num_interactions": amendment["num_events"],
        "num_baskets": amendment["num_orders"],
        "num_cold_items": amendment["num_cold_products"],
    }
    for field, expected in expected_counts.items():
        if getattr(manifest, field) != expected:
            raise IntegrityError(f"parent {field} does not match v5.1 amendment")
    split_counts = {split: len(parent.events_by_split[split]) for split in ("train", "val", "test")}
    if split_counts != amendment["split_counts"]:
        raise IntegrityError("parent split counts do not match v5.1 amendment")
    if manifest.behavior_nature != amendment["scientific_scope"]["behavior_nature"]:
        raise IntegrityError("parent behavior nature does not match amendment scope")
    if manifest.observed_behavior is not amendment["scientific_scope"]["observed_behavior"]:
        raise IntegrityError("parent observed_behavior does not match amendment scope")


def materialize_v5_family_view(
    parent_root: Path,
    family_view_root: Path,
    output_root: Path,
    *,
    amendment_path: Path,
) -> Snapshot:
    """Publish one immutable v5.1 canonical snapshot from a frozen feature view."""

    parent_path = parent_root.resolve()
    family_path = family_view_root.resolve()
    target = output_root.resolve()
    amendment_file = amendment_path.resolve()
    if len({parent_path, family_path, target}) != 3:
        raise IntegrityError("parent, family-view, and output roots must differ")
    if target.is_relative_to(parent_path) or target.is_relative_to(family_path):
        raise IntegrityError("output root may not be inside an input root")
    if target.exists():
        raise IntegrityError(f"v5.1 canonical output already exists: {target}")
    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        raise IntegrityError(f"v5.1 canonical staging root already exists: {staging}")

    amendment, amendment_file_hash, policy_hash, anchor_ids = _load_amendment(amendment_file)
    parent = load_canonical_snapshot(parent_path)
    _verify_parent_binding(parent, amendment=amendment)
    family_manifest, family_rows, family_file_hash, family_manifest_file_hash = _load_family_view(
        family_path, amendment=amendment, policy_hash=policy_hash
    )
    by_raw_id = _validate_family_rows(
        family_rows,
        parent=parent,
        family_manifest=family_manifest,
        anchor_ids=anchor_ids,
    )

    item_rows = [
        {
            "item_id": item_id,
            "raw_item_id": parent.item_records[item_id].raw_item_id,
            "text": by_raw_id[parent.item_records[item_id].raw_item_id]["model_text"],
            "category": by_raw_id[parent.item_records[item_id].raw_item_id]["category"],
            "price": float(by_raw_id[parent.item_records[item_id].raw_item_id]["model_price"]),
        }
        for item_id in parent.items
    ]
    feature_hashes = _feature_hashes(item_rows)
    behavior_hashes = {name: sha256_file(parent_path / name) for name in _BEHAVIOR_FILES}
    parent_manifest = parent.manifest
    manifest_mapping = parent_manifest.to_mapping()
    manifest_mapping.update(
        {
            "dataset_id": f"{parent_manifest.dataset_id}-v5.1-family-view",
            "source_kind": "versioned-parent-feature-view",
            "source_locator": (
                f"parent:{parent_manifest.dataset_id};family-view:{family_file_hash}"
            ),
            "dataset_sha256": "0" * 64,
            "item_feature_hashes": feature_hashes,
            "source_artifact_hashes": {
                **parent_manifest.source_artifact_hashes,
                "parent_manifest_canonical.json": canonical_json_sha256(
                    parent_manifest.to_mapping()
                ),
                "v5.1_amendment.json": amendment_file_hash,
                "catalog_family_view.jsonl": family_file_hash,
                "catalog_family_view_manifest.json": family_manifest_file_hash,
                "v5.1_policy": policy_hash,
            },
        }
    )
    # The stream hash uses the exact item rows that will be written and the
    # parent behavior rows parsed into canonical JSON values.
    manifest_mapping["dataset_sha256"] = _stream_dataset_hash(
        item_rows=item_rows,
        users_path=parent_path / "users.jsonl",
        baskets_path=parent_path / "baskets.jsonl",
        split_paths={split: parent_path / f"{split}.jsonl" for split in ("train", "val", "test")},
    )
    canonical_manifest = DatasetManifest.from_mapping(manifest_mapping)

    try:
        staging.mkdir(parents=True)
        _write_json(staging / "manifest.json", canonical_manifest.to_mapping())
        _write_jsonl(staging / "items.jsonl", item_rows)
        for name in _BEHAVIOR_FILES:
            shutil.copyfile(parent_path / name, staging / name)
            if sha256_file(staging / name) != behavior_hashes[name]:
                raise IntegrityError(f"behavior file changed during copy: {name}")
        # This replay validates the new payload, all split/basket hashes, and
        # the exact seven-file canonical snapshot contract before publication.
        del parent
        validated = load_canonical_snapshot(staging)
        if {entry.name for entry in staging.iterdir()} != _CANONICAL_FILES:
            raise IntegrityError("v5.1 canonical staging root has an unexpected file set")
        staging.replace(target)
    except (OSError, IntegrityError):
        if staging.exists():
            shutil.rmtree(staging)
        raise
    if {entry.name for entry in target.iterdir()} != _CANONICAL_FILES:
        raise IntegrityError("v5.1 canonical output has an unexpected file set")
    return validated


__all__ = ["materialize_v5_family_view"]
