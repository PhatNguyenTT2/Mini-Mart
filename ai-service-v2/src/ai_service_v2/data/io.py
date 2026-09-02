"""Minimal canonical JSONL snapshot adapter for fixtures and local smoke runs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.snapshot import Interaction, ItemRecord, Snapshot, TrainingBasket
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_sha256, load_strict_json, loads_strict_json


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read JSONL file: {path}") from error
    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        if not line.strip():
            raise IntegrityError(f"blank JSONL line at {path}:{line_number}")
        rows.append(loads_strict_json(line, source=f"{path}:{line_number}"))
    return rows


def _require_exact_fields(row: dict[str, Any], expected: set[str], path: Path) -> None:
    if set(row) != expected:
        missing = sorted(expected - set(row))
        unknown = sorted(set(row) - expected)
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unknown:
            details.append(f"unknown={','.join(unknown)}")
        raise IntegrityError(f"{path}: row fields do not match schema ({'; '.join(details)})")


def _required_int(row: dict[str, Any], key: str, path: Path) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise IntegrityError(f"{path}: {key} must be an integer")
    return value


def _required_string(row: dict[str, Any], key: str, path: Path) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise IntegrityError(f"{path}: {key} must be a non-empty string")
    return value


def _canonical_payload(
    manifest: DatasetManifest,
    user_rows: list[dict[str, Any]],
    item_rows: list[dict[str, Any]],
    basket_rows: list[dict[str, Any]],
    split_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    splits = {split: split_rows[split] for split in ("train", "val", "test")}
    if manifest.schema_version == "dataset-manifest/1.0":
        return {"items": item_rows, "splits": splits}
    return {
        "users": user_rows,
        "items": item_rows,
        "training_baskets": basket_rows,
        "splits": splits,
    }


def load_canonical_snapshot(root: Path) -> Snapshot:
    """Load a JSONL snapshot and verify all hashes before constructing objects.

    JSONL is intentionally a small fixture/local adapter.  The production
    materializer may provide Arrow/Parquet rows through the same ``Snapshot``
    seam without changing the evaluator.
    """

    manifest = DatasetManifest.from_mapping(load_strict_json(root / "manifest.json"))
    expected_files = {
        "manifest.json",
        "items.jsonl",
        "train.jsonl",
        "val.jsonl",
        "test.jsonl",
    }
    if manifest.schema_version == "dataset-manifest/1.1":
        expected_files |= {"users.jsonl", "baskets.jsonl"}
    try:
        actual_files = {path.name for path in root.iterdir()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect snapshot root: {root}") from error
    if actual_files != expected_files:
        raise IntegrityError("snapshot file set does not match manifest schema")

    user_rows = (
        _read_jsonl(root / "users.jsonl")
        if manifest.schema_version == "dataset-manifest/1.1"
        else [{"user_id": user_id, "raw_user_id": user_id} for user_id in range(manifest.num_users)]
    )
    item_rows = _read_jsonl(root / "items.jsonl")
    basket_rows = (
        _read_jsonl(root / "baskets.jsonl")
        if manifest.schema_version == "dataset-manifest/1.1"
        else []
    )
    split_rows = {split: _read_jsonl(root / f"{split}.jsonl") for split in ("train", "val", "test")}
    payload = _canonical_payload(manifest, user_rows, item_rows, basket_rows, split_rows)
    if canonical_json_sha256(payload) != manifest.dataset_sha256:
        raise IntegrityError("snapshot payload hash does not match manifest")
    for split, rows in split_rows.items():
        if canonical_json_sha256({"split": split, "rows": rows}) != manifest.split_hashes[split]:
            raise IntegrityError(f"{split} split hash does not match manifest")

    raw_users: dict[int, int] = {}
    for row in user_rows:
        _require_exact_fields(row, {"user_id", "raw_user_id"}, root / "users.jsonl")
        user_id = _required_int(row, "user_id", root / "users.jsonl")
        raw_user_id = _required_int(row, "raw_user_id", root / "users.jsonl")
        if user_id in raw_users:
            raise IntegrityError(f"duplicate user_id: {user_id}")
        raw_users[user_id] = raw_user_id
    if tuple(sorted(raw_users)) != tuple(range(manifest.num_users)):
        raise IntegrityError("user rows must contain dense ascending internal IDs")
    raw_user_ids = tuple(raw_users[user_id] for user_id in range(manifest.num_users))

    item_records: dict[int, ItemRecord] = {}
    for row in item_rows:
        _require_exact_fields(
            row,
            {"item_id", "raw_item_id", "text", "category", "price"},
            root / "items.jsonl",
        )
        item_id = _required_int(row, "item_id", root / "items.jsonl")
        if item_id in item_records:
            raise IntegrityError(f"duplicate item_id: {item_id}")
        raw_item_id = _required_int(row, "raw_item_id", root / "items.jsonl")
        price = row.get("price")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))):
            raise IntegrityError("item price must be numeric or null")
        item_records[item_id] = ItemRecord(
            item_id=item_id,
            raw_item_id=raw_item_id,
            text=_required_string(row, "text", root / "items.jsonl"),
            category=_required_string(row, "category", root / "items.jsonl"),
            price=None if price is None else float(price),
        )

    training_baskets: list[TrainingBasket] = []
    for row in basket_rows:
        _require_exact_fields(
            row,
            {"basket_id", "user_id", "timestamp", "item_ids", "origin"},
            root / "baskets.jsonl",
        )
        item_ids = row["item_ids"]
        if not isinstance(item_ids, list) or any(
            isinstance(item_id, bool) or not isinstance(item_id, int) for item_id in item_ids
        ):
            raise IntegrityError("basket item_ids must be a list of integers")
        training_baskets.append(
            TrainingBasket(
                basket_id=_required_string(row, "basket_id", root / "baskets.jsonl"),
                user_id=_required_int(row, "user_id", root / "baskets.jsonl"),
                timestamp=_required_int(row, "timestamp", root / "baskets.jsonl"),
                item_ids=tuple(item_ids),
                origin=_required_string(row, "origin", root / "baskets.jsonl"),
            )
        )
    if manifest.schema_version == "dataset-manifest/1.1":
        if canonical_json_sha256({"training_baskets": basket_rows}) != manifest.basket_sha256:
            raise IntegrityError("training basket hash does not match manifest")
        if len(training_baskets) != manifest.num_baskets:
            raise IntegrityError("training basket count does not match manifest")

    events: dict[str, tuple[Interaction, ...]] = {}
    global_event_ids: set[int] = set()
    expected_event_fields = {
        "event_id",
        "user_id",
        "item_id",
        "timestamp",
        "event_type",
        "basket_id",
    }
    if manifest.schema_version == "dataset-manifest/1.1":
        expected_event_fields |= {
            "raw_event_id",
            "event_origin",
            "session_id",
            "cohort_id",
        }
    if set(manifest.event_schema) != expected_event_fields:
        raise IntegrityError("event_schema does not match snapshot schema")
    for split, rows in split_rows.items():
        parsed: list[Interaction] = []
        for row in rows:
            _require_exact_fields(
                row,
                expected_event_fields,
                root / f"{split}.jsonl",
            )
            event = Interaction(
                event_id=_required_int(row, "event_id", root / f"{split}.jsonl"),
                user_id=_required_int(row, "user_id", root / f"{split}.jsonl"),
                item_id=_required_int(row, "item_id", root / f"{split}.jsonl"),
                timestamp=_required_int(row, "timestamp", root / f"{split}.jsonl"),
                event_type=_required_string(row, "event_type", root / f"{split}.jsonl"),
                basket_id=(
                    None
                    if row["basket_id"] is None
                    else _required_string(row, "basket_id", root / f"{split}.jsonl")
                ),
                raw_event_id=(
                    None
                    if row.get("raw_event_id") is None
                    else _required_string(row, "raw_event_id", root / f"{split}.jsonl")
                ),
                event_origin=(
                    _required_string(row, "event_origin", root / f"{split}.jsonl")
                    if "event_origin" in row
                    else "organic"
                ),
                session_id=(
                    None
                    if row.get("session_id") is None
                    else _required_string(row, "session_id", root / f"{split}.jsonl")
                ),
                cohort_id=(
                    None
                    if row.get("cohort_id") is None
                    else _required_string(row, "cohort_id", root / f"{split}.jsonl")
                ),
            )
            if event.event_id in global_event_ids:
                raise IntegrityError(f"duplicate event_id across splits: {event.event_id}")
            global_event_ids.add(event.event_id)
            parsed.append(event)
        events[split] = tuple(parsed)

    raw_item_ids = tuple(item_records[item].raw_item_id for item in sorted(item_records))
    if canonical_json_sha256({"raw_user_ids": list(raw_user_ids)}) != manifest.raw_user_map_sha256:
        raise IntegrityError("raw user mapping hash does not match manifest")
    if canonical_json_sha256({"raw_item_ids": list(raw_item_ids)}) != manifest.raw_item_map_sha256:
        raise IntegrityError("raw item mapping hash does not match manifest")
    feature_payload = {
        "text": [
            {"item_id": item, "text": item_records[item].text} for item in sorted(item_records)
        ],
        "category": [
            {"item_id": item, "category": item_records[item].category}
            for item in sorted(item_records)
        ],
        "price": [
            {"item_id": item, "price": item_records[item].price} for item in sorted(item_records)
        ],
    }
    for feature_name, feature_rows in feature_payload.items():
        if (
            canonical_json_sha256({feature_name: feature_rows})
            != manifest.item_feature_hashes[feature_name]
        ):
            raise IntegrityError(f"{feature_name} feature hash does not match manifest")

    snapshot = Snapshot.from_fixture(
        manifest,
        events,
        item_records,
        raw_user_ids=raw_user_ids,
        raw_item_ids=raw_item_ids,
        training_baskets=(
            training_baskets if manifest.schema_version == "dataset-manifest/1.1" else None
        ),
    )
    if len(item_records) != manifest.num_items:
        raise IntegrityError("item row count does not match manifest")
    if len({event.user_id for rows in events.values() for event in rows}) > manifest.num_users:
        raise IntegrityError("event user coverage exceeds manifest")
    return snapshot


def materialize_snapshot(source_root: Path, output_root: Path) -> Snapshot:
    """Validate and copy a canonical snapshot into a new immutable namespace.

    This is intentionally a file-based adapter for local fixtures and staged
    inputs.  It never overwrites an existing output and copies only the exact
    versioned canonical file set covered by the manifest hashes.
    """

    source = source_root.resolve()
    target = output_root.resolve()
    if source == target:
        raise IntegrityError("source and output snapshot roots must differ")
    snapshot = load_canonical_snapshot(source)
    if target.exists():
        raise IntegrityError(f"snapshot output already exists: {target}")
    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        raise IntegrityError(f"snapshot staging root already exists: {staging}")
    try:
        staging.mkdir(parents=True)
        names = ["manifest.json", "items.jsonl", "train.jsonl", "val.jsonl", "test.jsonl"]
        if snapshot.manifest.schema_version == "dataset-manifest/1.1":
            names.extend(["users.jsonl", "baskets.jsonl"])
        for name in names:
            shutil.copyfile(source / name, staging / name)
        # Re-parse the copied bytes before publication, then publish atomically.
        load_canonical_snapshot(staging)
        staging.replace(target)
    except (OSError, IntegrityError):
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return snapshot


__all__ = ["load_canonical_snapshot", "materialize_snapshot"]
