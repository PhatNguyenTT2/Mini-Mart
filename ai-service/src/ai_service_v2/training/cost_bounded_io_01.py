"""Owned, bounded Python streams. Unadapted native writers are not covered."""

from __future__ import annotations

import copy
import ctypes
import io
import os
import re
import shutil
import stat
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, cast

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
    sha256_bytes,
)
from ai_service_v2.hashing import (
    sha256_file as _sha256_file,
)
from ai_service_v2.training.cost_control_storage_01 import (
    _allocated_size,
    capacity_census,
    current_storage_policy_controls,
    safe_name,
    size,
    storage_admission_for_authority,
)
from ai_service_v2.training.cost_profile_process_03 import (
    process_identity,
    resolve_owned_process,
    validate_identity,
)
from ai_service_v2.training.cost_runtime_custody import (
    exclusive_lane,
    write_exclusive_json,
)
from ai_service_v2.training.cost_runtime_custody import (
    read_canonical_json as _read_canonical_json,
)
from ai_service_v2.training.cost_runtime_custody import (
    reject_reparse_path as _reject_reparse_path,
)

MIB = 1_048_576
_METADATA_PASS: ContextVar[dict[Path, tuple[dict[str, Any], str]] | None] = ContextVar(
    "bounded_storage_metadata_pass", default=None
)
_CHECKED_PATHS: ContextVar[set[Path] | None] = ContextVar("bounded_storage_paths", default=None)
_PREDICATE_PASS: ContextVar[dict[tuple[str, Path], Any] | None] = ContextVar(
    "bounded_storage_predicates", default=None
)
_STORAGE_LEASE: ContextVar[tuple[Path, int, int] | None] = ContextVar(
    "bounded_storage_lease", default=None
)
_ALLOCATION_PASS: ContextVar[dict[Path, tuple[int, int]] | None] = ContextVar(
    "bounded_storage_allocations", default=None
)
_CONTROL_SNAPSHOT_PASS: ContextVar[dict[tuple[Path, str, str, str], dict[str, int]] | None] = (
    ContextVar("bounded_control_snapshots", default=None)
)


def invalidate_materialization(path: Path, *, operation_directory: Path | None = None) -> None:
    """Only the owned current output changes; other admitted records are immutable."""
    metadata = _METADATA_PASS.get()
    if metadata is not None:
        metadata.pop(path, None)
    allocations = _ALLOCATION_PASS.get()
    if allocations is not None:
        allocations.pop(path, None)
    predicates = _PREDICATE_PASS.get()
    if predicates is not None:
        if operation_directory is None:
            # Retention/disposal changes have dependencies beyond one operation.
            predicates.clear()
        else:
            for key in list(predicates):
                if key[1] == operation_directory:
                    del predicates[key]


def reject_reparse_path(path: Path) -> None:
    checked = _CHECKED_PATHS.get()
    if checked is None:
        _reject_reparse_path(path)
        return
    if path in checked:
        return
    admitted = []
    for ancestor in (path, *path.parents):
        if ancestor in checked:
            continue
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise IntegrityError("reparse/symlink paths are forbidden for execution custody")
        admitted.append(ancestor)
    checked.update(admitted)


def read_canonical_json(path: Path) -> dict[str, Any]:
    cache = _METADATA_PASS.get()
    if cache is None:
        return _read_canonical_json(path)
    if path not in cache:
        reject_reparse_path(path)
        payload = path.read_bytes()
        value = loads_strict_json(payload, source=str(path))
        if payload != canonical_json_bytes(value) + b"\n":
            raise IntegrityError("noncanonical execution custody")
        cache[path] = (value, sha256_bytes(payload))
    return copy.deepcopy(cache[path][0])


def sha256_file(path: Path) -> str:
    cache = _METADATA_PASS.get()
    if cache is not None and path in cache:
        return cache[path][1]
    return _sha256_file(path)


def _native_invocation_deadline(document: dict[str, Any], guard: Path) -> None:
    """Current generated-lane mutation ceiling; never a watchdog or timing qualification."""
    from ai_service_v2.training.cost_closure_control_calibration_01 import (
        CURRENT_AUTHORITY_SCHEMA,
        current_calibration_capacity,
        remaining_current_calibration,
    )

    if document.get("schema_version") == CURRENT_AUTHORITY_SCHEMA:
        reject_reparse_path(guard)
        if guard.exists():
            remaining_current_calibration(read_canonical_json(guard), document)
        else:
            current_calibration_capacity(document)
        return
    if "native_invocation_deadline" not in document:
        return
    policy = document["native_invocation_deadline"]
    if (
        type(policy) is not dict
        or set(policy) != {"route", "limit_seconds", "clock"}
        or policy["route"] != "GENERATED_REHEARSAL"
        or type(policy["limit_seconds"]) is not int
        or policy["limit_seconds"] != 7200
        or policy["clock"] != "MONOTONIC_NS_FROM_DURABLE_CLAIM"
        or document.get("scientific_execution_authorized") is not False
    ):
        raise IntegrityError("BOUNDED_NATIVE_INVOCATION_DEADLINE_POLICY")
    reject_reparse_path(guard)
    if not guard.exists():
        return  # The bounded control reservation precedes the durable compute claim.
    claim = read_canonical_json(guard)
    started, now = claim.get("claim_monotonic_ns"), time.monotonic_ns()
    if (
        type(started) is not int
        or started <= 0
        or now < started
        or now - started >= 7200 * 1_000_000_000
    ):
        raise IntegrityError("BOUNDED_NATIVE_INVOCATION_DEADLINE")


@contextmanager
def serialized_storage_lane(root: Path) -> Iterator[None]:
    """Wait only for the storage lease, never retry a write or invocation."""
    held = _STORAGE_LEASE.get()
    identity = (root, os.getpid(), threading.get_ident())
    if held is not None:
        if held != identity:
            raise IntegrityError("BOUNDED_NESTED_FOREIGN_STORAGE_LEASE")
        yield
        return
    deadline = time.monotonic() + 30
    lease = exclusive_lane(root)
    while True:
        try:
            lease.__enter__()
            break
        except IntegrityError as error:
            if str(error) != "execution lane already occupied":
                raise
            if time.monotonic() >= deadline:
                raise IntegrityError("BOUNDED_STORAGE_LEASE_TIMEOUT") from error
            time.sleep(0.01)
            lease = exclusive_lane(root)
    # Append-only metadata is one snapshot while all admitted writers hold this
    # lease. Discard it before the next lease; sealed replay never uses it.
    token = _METADATA_PASS.set({})
    path_token = _CHECKED_PATHS.set(set())
    predicate_token = _PREDICATE_PASS.set({})
    lease_token = _STORAGE_LEASE.set(identity)
    allocation_token = _ALLOCATION_PASS.set({})
    control_token = _CONTROL_SNAPSHOT_PASS.set({})
    try:
        yield
    finally:
        _CONTROL_SNAPSHOT_PASS.reset(control_token)
        _ALLOCATION_PASS.reset(allocation_token)
        _STORAGE_LEASE.reset(lease_token)
        _PREDICATE_PASS.reset(predicate_token)
        _METADATA_PASS.reset(token)
        _CHECKED_PATHS.reset(path_token)
        lease.__exit__(None, None, None)


def allocation_unit(cache: Path) -> int:
    """Charge each file's allocation rounding before allowing growth."""
    if os.name != "nt":
        raise IntegrityError("BOUNDED_WINDOWS_ALLOCATION_REQUIRED")
    values = [ctypes.c_ulong() for _ in range(4)]
    query = ctypes.WinDLL("kernel32", use_last_error=True).GetDiskFreeSpaceW
    query.argtypes = [ctypes.c_wchar_p, *([ctypes.POINTER(ctypes.c_ulong)] * 4)]
    query.restype = ctypes.c_int
    if not query(str(cache.resolve().anchor), *(ctypes.byref(value) for value in values)):
        raise IntegrityError("BOUNDED_ALLOCATION_UNIT_UNAVAILABLE")
    unit = values[0].value * values[1].value
    if unit <= 0 or unit > MIB or unit & (unit - 1):
        raise IntegrityError("BOUNDED_ALLOCATION_GEOMETRY")
    return unit


def policy_caps() -> dict[str, int]:
    """Enforced policy limits, not observations of serialized artifact sizes."""
    return {
        "scores": 128 * MIB,
        "checkpoint": 128 * MIB,
        "sidecars": 8 * MIB,
        "input": 128 * MIB,
        "auxiliary": 64 * MIB,
        "execution_controls": 1024 * MIB,
    }


def score_reservation_policy(
    chunk_rows: list[int],
    columns: int,
    *,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Bound prospective primitive NPY files, not observed or admitted scores."""
    if (
        type(chunk_rows) is not list
        or not 1 <= len(chunk_rows) <= 39
        or any(type(rows) is not int or not 1 <= rows <= 128 for rows in chunk_rows)
        or any(rows != 128 for rows in chunk_rows[:-1])
        or type(columns) is not int
        or columns <= 0
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
    ):
        raise IntegrityError("BOUNDED_SCORE_STORAGE_GEOMETRY")
    unit = allocation_unit_bytes
    bound = sum(((rows * columns * 4 + 256 + unit - 1) // unit) * unit for rows in chunk_rows)
    if bound > policy_caps()["scores"]:
        raise IntegrityError("BOUNDED_SCORE_STORAGE_GEOMETRY_EXCEEDS_POLICY")
    return {
        "schema_version": "mp2-cost-score-reservation-geometry/1.0",
        "chunk_rows": list(chunk_rows),
        "columns": columns,
        "score_dtype": "float32",
        "header_bound_bytes_per_file": 256,
        "allocation_unit_bytes": unit,
        "allocated_bound_bytes": bound,
        "source_manifest_sha256": source_manifest_sha256,
        "scope": "PROSPECTIVE_SERIALIZER_BOUND_NOT_PAYLOAD_QUALIFICATION",
    }


def operation_name(value: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", value):
        raise IntegrityError("BOUNDED_OPERATION_ID")
    safe_name(value)
    return value


def input_reservation_policy(
    packets: dict[str, list[dict[str, Any]]],
    *,
    allocation_unit_bytes: int,
    source_inventory_sha256: str,
) -> dict[str, Any]:
    """Prospective copies of exact immutable inputs, not observed file-size credit."""
    if (
        type(packets) is not dict
        or not 1 <= len(packets) <= 38
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_inventory_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_inventory_sha256)
    ):
        raise IntegrityError("BOUNDED_INPUT_STORAGE_GEOMETRY")
    bounds: dict[str, int] = {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    operations: set[str] = set()
    outputs: set[str] = set()
    identity_bound: bool | None = None
    for packet_id, rows in sorted(packets.items()):
        operation_name(packet_id)
        if type(rows) is not list or not 1 <= len(rows) <= 128:
            raise IntegrityError("BOUNDED_INPUT_STORAGE_ROSTER")
        bound = 0
        for row in rows:
            fields = {
                "operation_id",
                "source_path",
                "output_path",
                "bytes",
                "sha256",
            }
            if type(row) is not dict or set(row) not in (fields, fields | {"source_identity"}):
                raise IntegrityError("BOUNDED_INPUT_STORAGE_ROSTER")
            has_identity = "source_identity" in row
            if identity_bound is None:
                identity_bound = has_identity
            if identity_bound != has_identity:
                raise IntegrityError("BOUNDED_INPUT_SOURCE_IDENTITY_ROSTER")
            if has_identity:
                identity = row["source_identity"]
                if (
                    type(identity) is not dict
                    or set(identity) != {"volume_id", "file_id", "modified_ns", "links"}
                    or any(type(value) is not int for value in identity.values())
                    or identity["volume_id"] < 0
                    or identity["file_id"] <= 0
                    or identity["modified_ns"] < 0
                    or identity["links"] != 1
                ):
                    raise IntegrityError("BOUNDED_INPUT_SOURCE_IDENTITY")
            name = operation_name(row["operation_id"])
            output = safe_name(row["output_path"])
            source = row["source_path"]
            length = size(row["bytes"])
            if (
                name in operations
                or output.casefold() in outputs
                or not output.startswith(f"packets/{packet_id}/input/")
                or type(source) is not str
                or not Path(source).is_absolute()
                or str(Path(source)) != source
                or ".." in Path(source).parts
                or type(row["sha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                or not 0 < length <= policy_caps()["input"]
            ):
                raise IntegrityError("BOUNDED_INPUT_STORAGE_ROSTER")
            operations.add(name)
            outputs.add(output.casefold())
            bound += (
                (length + allocation_unit_bytes - 1)
                // allocation_unit_bytes
                * allocation_unit_bytes
            )
        if bound > policy_caps()["input"]:
            raise IntegrityError("BOUNDED_INPUT_STORAGE_GEOMETRY_EXCEEDS_POLICY")
        bounds[packet_id] = bound
        normalized[packet_id] = sorted(copy.deepcopy(rows), key=lambda row: row["operation_id"])
    return {
        "schema_version": "mp2-cost-input-reservation-geometry/1.1"
        if identity_bound
        else "mp2-cost-input-reservation-geometry/1.0",
        "packets": normalized,
        "packet_allocated_bounds": bounds,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_inventory_sha256": source_inventory_sha256,
        "scope": "IMMUTABLE_AUTHORITY_INPUT_COPIES_ONLY",
    }


def native_top_k_storage_policy(
    operations: dict[str, str],
    *,
    user_ids: list[int],
    candidate_item_ids: list[int],
    cutoff: int,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """A fixed native top-k file proof, never a complete epoch reservation proof."""
    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 1301
        or type(user_ids) is not list
        or not 1 <= len(user_ids) <= 39 * 128
        or type(candidate_item_ids) is not list
        or not 1 <= len(candidate_item_ids) <= 4960
        or any(type(value) is not int or not 0 <= value < 2**63 for value in user_ids)
        or any(type(value) is not int or not 0 <= value < 2**63 for value in candidate_item_ids)
        or user_ids != sorted(set(user_ids))
        or len(set(candidate_item_ids)) != len(candidate_item_ids)
        or type(cutoff) is not int
        or not 1 <= cutoff <= 10
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
    ):
        raise IntegrityError("BOUNDED_TOP_K_STORAGE_GEOMETRY")
    count = min(cutoff, len(candidate_item_ids))
    # Unique item IDs use at most the count longest decimal representations.
    items = sum(sorted((len(str(item)) for item in candidate_item_ids), reverse=True)[:count])
    items += count - 1
    bound = len(canonical_json_bytes({"schema_version": "mp2-cost-native-top-k/1.0", "users": []}))
    bound += sum(
        len(canonical_json_bytes({"user_id": user, "items": []})) + items for user in user_ids
    )
    bound += len(user_ids) - 1 + 1  # Between-row commas and the durable newline.
    allocated = (bound + allocation_unit_bytes - 1) // allocation_unit_bytes * allocation_unit_bytes
    if allocated > policy_caps()["sidecars"]:
        raise IntegrityError("BOUNDED_TOP_K_STORAGE_GEOMETRY_EXCEEDS_POLICY")
    roster: dict[str, dict[str, Any]] = {}
    paths: set[str] = set()
    for operation, path in sorted(operations.items()):
        operation_name(operation)
        path = safe_name(path)
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/.+/top_k\.json", path)
            or path.casefold() in paths
        ):
            raise IntegrityError("BOUNDED_TOP_K_OUTPUT_ROSTER")
        paths.add(path.casefold())
        roster[operation] = {
            "path": path,
            "logical_bound_bytes": bound,
            "allocated_bound_bytes": allocated,
        }
    return {
        "schema_version": "mp2-cost-native-top-k-storage/1.0",
        "operations": roster,
        "user_ids": list(user_ids),
        "candidate_item_ids": list(candidate_item_ids),
        "cutoff": cutoff,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "scope": "PROSPECTIVE_NATIVE_TOP_K_FILE_ONLY",
        "complete_transaction_proof": False,
        "reservation_credit_bytes": 0,
    }


def _evaluation_bound_documents(
    identity: dict[str, Any], user_ids: list[int], total: int, candidates: int, cutoff: int
) -> dict[str, dict[str, Any]]:
    # CPython binary64 JSON uses at most 24 ASCII bytes (sign, 17 significant
    # digits, decimal point and exponent). A 24-digit integer is a proof token,
    # not a metric; real documents still require finite values inside [0, 1].
    number = 10**23
    metrics = {f"HR@{cutoff}": number, f"NDCG@{cutoff}": number, "GAUC": number}
    denominators = {key: len(user_ids) for key in metrics}
    common = {key: value for key, value in identity.items() if not key.startswith("evaluator_")}
    return {
        "per_user_metrics.json": {
            "schema_version": "per-user-metrics/1.0",
            **common,
            "cutoff": cutoff,
            "user_ids": user_ids,
            "metrics": [{"user_id": user, **metrics} for user in user_ids],
        },
        "aggregate_metrics.json": {
            "schema_version": "aggregate-metrics/1.0",
            **common,
            "aggregate_metrics": metrics,
            "denominator_by_metric": denominators,
        },
        "evaluation_receipt.json": {
            "schema_version": "evaluation-receipt/1.1",
            "receipt": {
                **identity,
                "per_user_metrics_sha256": "f" * 64,
                "num_total_users": total,
                "num_eligible_users": len(user_ids),
                "candidate_count": candidates,
                "cutoff": cutoff,
                "aggregate_metrics": metrics,
                "denominator_by_metric": denominators,
                "verdict": "INCOMPLETE",
            },
            "per_user_metrics_file": "per_user_metrics.json",
            "aggregate_metrics_file": "aggregate_metrics.json",
        },
    }


def native_evaluation_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    user_ids: list[int],
    num_total_users: int,
    candidate_count: int,
    cutoff: int,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Complete three-file native bundles; no credit for other epoch sidecars."""
    import inspect
    import json.encoder
    import sys

    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] not in {(3, 11), (3, 12)}
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise IntegrityError("BOUNDED_EVALUATION_SERIALIZER_RUNTIME")
    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 2602
        or type(user_ids) is not list
        or not 1 <= len(user_ids) <= 39 * 128
        or any(type(user) is not int or not 0 <= user < 2**63 for user in user_ids)
        or user_ids != sorted(set(user_ids))
        or type(num_total_users) is not int
        or not len(user_ids) <= num_total_users < 2**63
        or type(candidate_count) is not int
        or not 1 <= candidate_count <= 4960
        or type(cutoff) is not int
        or not 1 <= cutoff <= min(10, candidate_count)
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
    ):
        raise IntegrityError("BOUNDED_EVALUATION_STORAGE_GEOMETRY")
    identities = {
        "run_id",
        "model_id",
        "protocol_id",
        "protocol_manifest_sha256",
        "candidate_order_sha256",
        "evaluator_version",
        "evaluator_implementation_sha256",
    }
    roster: dict[str, Any] = {}
    roots: set[str] = set()
    for operation, spec in sorted(operations.items()):
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"root", "identity"}:
            raise IntegrityError("BOUNDED_EVALUATION_OUTPUT_ROSTER")
        root = safe_name(spec["root"])
        identity = spec["identity"]
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/.+/(cost|legacy)", root)
            or root.casefold() in roots
            or type(identity) is not dict
            or set(identity) != identities
            or any(
                type(value) is not str or not 1 <= len(value.encode("utf-8")) <= 1024
                for value in identity.values()
            )
            or any(
                not re.fullmatch(r"[0-9a-f]{64}", identity[key])
                for key in identities
                if key.endswith("sha256")
            )
        ):
            raise IntegrityError("BOUNDED_EVALUATION_IDENTITY_OR_ROSTER")
        roots.add(root.casefold())
        files: dict[str, Any] = {}
        for name, document in _evaluation_bound_documents(
            identity, user_ids, num_total_users, candidate_count, cutoff
        ).items():
            length = len(canonical_json_bytes(document)) + 1
            allocated = (length + allocation_unit_bytes - 1) // allocation_unit_bytes
            files[f"{root}/{name}"] = {
                "logical_bound_bytes": length,
                "allocated_bound_bytes": allocated * allocation_unit_bytes,
            }
        amount = sum(row["allocated_bound_bytes"] for row in files.values())
        if amount > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_EVALUATION_STORAGE_GEOMETRY_EXCEEDS_POLICY")
        roster[operation] = {
            "root": root,
            "identity": copy.deepcopy(identity),
            "files": files,
            "allocated_bound_bytes": amount,
        }
    return {
        "schema_version": "mp2-cost-native-evaluation-storage/1.0",
        "operations": roster,
        "user_ids": list(user_ids),
        "num_total_users": num_total_users,
        "candidate_count": candidate_count,
        "cutoff": cutoff,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "numeric_token_bound_bytes": 24,
        "serializer_binding": {
            "python_implementation": sys.implementation.name,
            "python_version": sys.version,
            "float_mantissa_bits": sys.float_info.mant_dig,
            "canonical_source_sha256": sha256_file(Path(inspect.getfile(canonical_json_bytes))),
            "json_encoder_source_sha256": sha256_file(Path(inspect.getfile(json.encoder))),
            "numeric_rule": "CPYTHON_BINARY64_SHORTEST_REPR_MAX_24_ASCII_BYTES",
        },
        "scope": "PROSPECTIVE_NATIVE_EVALUATION_BUNDLES_ONLY",
        "complete_transaction_proof": True,
    }


def native_score_manifest_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    chunk_rows: list[int],
    columns: int,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Fixed float32 scientific score manifests, not generated calibration documents."""
    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 1301
        or type(chunk_rows) is not list
        or not 1 <= len(chunk_rows) <= 39
        or any(type(row) is not int or not 1 <= row <= 128 for row in chunk_rows)
        or any(row != 128 for row in chunk_rows[:-1])
        or type(columns) is not int
        or not 1 <= columns <= 4960
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
    ):
        raise IntegrityError("BOUNDED_SCORE_MANIFEST_STORAGE_GEOMETRY")
    identity_fields = {
        "run_id",
        "model_id",
        "user_order_sha256",
        "candidate_order_sha256",
        "protocol_manifest_sha256",
    }
    chunks = [
        {"name": f"scores-{index:05d}.npy", "first_user_index": 128 * index, "user_count": rows}
        for index, rows in enumerate(chunk_rows)
    ]
    roster: dict[str, Any] = {}
    paths: set[str] = set()
    for operation, spec in sorted(operations.items()):
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"path", "identity"}:
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_OUTPUT_ROSTER")
        path = safe_name(spec["path"])
        identity = spec["identity"]
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/.+/scores/manifest\.json", path)
            or path.casefold() in paths
            or type(identity) is not dict
            or set(identity) != identity_fields
            or any(
                type(value) is not str or not 1 <= len(value.encode("utf-8")) <= 1024
                for value in identity.values()
            )
            or any(
                not re.fullmatch(r"[0-9a-f]{64}", identity[key])
                for key in identity_fields
                if key.endswith("sha256")
            )
        ):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_IDENTITY_OR_ROSTER")
        paths.add(path.casefold())
        manifest = {
            **identity,
            "num_users": sum(chunk_rows),
            "num_candidates": columns,
            "score_dtype": "float32",
            "score_shape": [sum(chunk_rows), columns],
            "finite": True,
            "chunks": [chunk["name"] for chunk in chunks],
        }
        document = {
            "schema_version": "score-artifact/1.0",
            "manifest": manifest,
            "chunks": [{**chunk, "sha256": "f" * 64} for chunk in chunks],
        }
        logical = len(canonical_json_bytes(document)) + 1
        allocated = (
            (logical + allocation_unit_bytes - 1) // allocation_unit_bytes * allocation_unit_bytes
        )
        if allocated > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_GEOMETRY_EXCEEDS_POLICY")
        roster[operation] = {
            "path": path,
            "identity": copy.deepcopy(identity),
            "fixed_manifest": manifest,
            "chunk_roster": copy.deepcopy(chunks),
            "logical_bound_bytes": logical,
            "allocated_bound_bytes": allocated,
        }
    source = Path(__file__).parent.parent
    return {
        "schema_version": "mp2-cost-native-score-manifest-storage/1.0",
        "operations": roster,
        "chunk_rows": list(chunk_rows),
        "columns": columns,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "serializer_sources": {
            "canonical_source_sha256": sha256_file(source / "hashing.py"),
            "manifest_contract_source_sha256": sha256_file(source / "contracts.py"),
            "score_artifact_source_sha256": sha256_file(source / "evaluation/artifacts.py"),
        },
        "scope": "PROSPECTIVE_NATIVE_FLOAT32_SCORE_MANIFEST_ONLY",
        "complete_transaction_proof": True,
    }


def native_reference_manifest_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Bound the fixed Reference manifest, never its tensor checkpoint payload."""
    import json.encoder
    import sys

    from ai_service_v2.training.reference_state_policy import (
        REFERENCE_STATE_POLICY_SCHEMA,
        REFERENCE_STATE_POLICY_SHA256,
        reference_state_policy_keys,
    )

    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 1301
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
        or sys.implementation.name != "cpython"
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_STORAGE_GEOMETRY")
    fields = {
        "schema_version",
        "logical_unit_id",
        "method_id",
        "seed",
        "epoch",
        "configuration_plan_sha256",
        "reference_spec_sha256",
        "state_policy_schema",
        "state_policy_sha256",
        "model_device_identity",
        "test_access_state",
        "durable_auxiliary_keys",
        "transient_auxiliary_keys",
        "optimizer_present",
    }
    digests = {
        "canonical_state_sha256",
        "checkpoint_sha256",
        "model_state_sha256",
        "reference_model_state_sha256",
        "configuration_sha256",
    }
    roster: dict[str, Any] = {}
    paths: set[str] = set()
    for operation, spec in sorted(operations.items()):
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"path", "identity"}:
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OUTPUT_ROSTER")
        path, identity = safe_name(spec["path"]), spec["identity"]
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/.+/checkpoint/manifest\.json", path)
            or path.casefold() in paths
            or type(identity) is not dict
            or set(identity) != fields
            or identity["schema_version"] != "local-v5-reference-checkpoint/1.1"
            or identity["state_policy_schema"] != REFERENCE_STATE_POLICY_SCHEMA
            or identity["state_policy_sha256"] != REFERENCE_STATE_POLICY_SHA256
            or identity["test_access_state"] != "LOCKED_NOT_ACCESSED"
            or type(identity["optimizer_present"]) is not bool
            or type(identity["seed"]) is not int
            or not 0 <= identity["seed"] < 2**63
            or (
                identity["epoch"] is not None
                and (type(identity["epoch"]) is not int or not 1 <= identity["epoch"] <= 1280)
            )
            or any(
                type(identity[key]) is not str
                or not 1 <= len(identity[key].encode("utf-8")) <= 1024
                for key in ("logical_unit_id", "method_id")
            )
            or any(
                type(identity[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", identity[key])
                for key in ("configuration_plan_sha256", "reference_spec_sha256")
            )
        ):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_IDENTITY_OR_ROSTER")
        durable, transient = reference_state_policy_keys(identity["method_id"])
        if identity["durable_auxiliary_keys"] != sorted(durable) or identity[
            "transient_auxiliary_keys"
        ] != sorted(transient):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_AUXILIARY_ROSTER")
        device = identity["model_device_identity"]
        if (
            type(device) is not dict
            or set(device) != {"schema_version", "raw", "canonical", "type", "index"}
            or device["schema_version"] != "local-v5-device-identity/1.0"
            or type(device["index"]) is not int
            or not 0 <= device["index"] <= 255
            or not (
                (
                    device["type"] == "cpu"
                    and device["index"] == 0
                    and device["raw"] in {"cpu", "cpu:0"}
                    and device["canonical"] == "cpu"
                )
                or (
                    device["type"] == "cuda"
                    and device["raw"] == device["canonical"] == f"cuda:{device['index']}"
                )
            )
        ):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_DEVICE_IDENTITY")
        fixed = {
            key: copy.deepcopy(value)
            for key, value in identity.items()
            if key != "optimizer_present"
        }
        fixed.update({key: "f" * 64 for key in digests})
        fixed["optimizer_state_sha256"] = "f" * 64 if identity["optimizer_present"] else None
        fixed["validation_ndcg_at_10"] = 10**23
        logical = len(canonical_json_bytes(fixed)) + 1
        allocated = (
            (logical + allocation_unit_bytes - 1) // allocation_unit_bytes * allocation_unit_bytes
        )
        if allocated > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_GEOMETRY_EXCEEDS_POLICY")
        paths.add(path.casefold())
        roster[operation] = {
            "path": path,
            "identity": copy.deepcopy(identity),
            "fixed_manifest": fixed,
            "logical_bound_bytes": logical,
            "allocated_bound_bytes": allocated,
        }
    source = Path(__file__).parent.parent
    return {
        "schema_version": "mp2-cost-native-reference-manifest-storage/1.0",
        "operations": roster,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "numeric_token_bound_bytes": 24,
        "serializer_binding": {
            "python_implementation": sys.implementation.name,
            "python_version": sys.version,
            "float_mantissa_bits": sys.float_info.mant_dig,
            "float_radix": sys.float_info.radix,
            "float_max_exp": sys.float_info.max_exp,
            "canonical_source_sha256": sha256_file(source / "hashing.py"),
            "json_encoder_source_sha256": sha256_file(Path(json.encoder.__file__)),
            "reference_source_sha256": sha256_file(source / "training/local_v5_reference.py"),
            "state_policy_source_sha256": sha256_file(
                source / "training/reference_state_policy.py"
            ),
            "device_identity_source_sha256": sha256_file(source / "device_identity.py"),
        },
        "scope": "PROSPECTIVE_NATIVE_REFERENCE_MANIFEST_ONLY",
        "complete_transaction_proof": True,
    }


def native_deep_manifest_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Bound Deep's native JSON manifest, independently of tensor payload size."""
    import json.encoder
    import sys

    from ai_service_v2.training.local_v5_checkpoint import CHECKPOINT_SCHEMA

    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 1301
        or type(allocation_unit_bytes) is not int
        or not 0 < allocation_unit_bytes <= MIB
        or allocation_unit_bytes & (allocation_unit_bytes - 1)
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
        or sys.implementation.name != "cpython"
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise IntegrityError("BOUNDED_DEEP_MANIFEST_STORAGE_GEOMETRY")
    integer_fields = {
        "segment_index",
        "completed_epoch",
        "next_epoch",
        "maximum_epochs",
        "early_stopping_patience",
    }
    fields = integer_fields | {"logical_unit_id", "authorities", "predecessor_present"}
    roster: dict[str, Any] = {}
    paths: set[str] = set()
    for operation, spec in sorted(operations.items()):
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"path", "identity"}:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_ROSTER")
        path, identity = safe_name(spec["path"]), spec["identity"]
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/.+/checkpoint/manifest\.json", path)
            or path.casefold() in paths
            or type(identity) is not dict
            or set(identity) != fields
            or any(type(identity[key]) is not int for key in integer_fields)
            or not 0 <= identity["segment_index"] <= 1280
            or not 1 <= identity["completed_epoch"] <= identity["maximum_epochs"] <= 1280
            or identity["next_epoch"] != identity["completed_epoch"] + 1
            or not 1 <= identity["early_stopping_patience"] <= 1280
            or type(identity["logical_unit_id"]) is not str
            or not 1 <= len(identity["logical_unit_id"].encode("utf-8")) <= 1024
            or type(identity["predecessor_present"]) is not bool
            or type(identity["authorities"]) is not dict
            or not 1 <= len(identity["authorities"]) <= 38
        ):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_IDENTITY_OR_ROSTER")
        authorities = identity["authorities"]
        if any(
            type(key) is not str
            or not 1 <= len(key.encode("utf-8")) <= 1024
            or type(value) is not str
            or not 1 <= len(value.encode("utf-8")) <= 1024
            for key, value in authorities.items()
        ) or len({key.casefold() for key in authorities}) != len(authorities):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_AUTHORITIES")
        fixed = {
            key: copy.deepcopy(value)
            for key, value in identity.items()
            if key != "predecessor_present"
        }
        fixed.update(
            {
                "schema_version": CHECKPOINT_SCHEMA,
                "best_epoch": max(1000, identity["completed_epoch"]),
                "best_metric": 10**23,
                "patience_count": identity["completed_epoch"],
                "history_sha256": "f" * 64,
                "payload_sha256": "f" * 64,
                "canonical_state_sha256": "f" * 64,
                "predecessor_manifest_sha256": "f" * 64
                if identity["predecessor_present"]
                else None,
                "accepted_result_rows": 0,
                "scientific_evidence_created": False,
                "test_access_state": "LOCKED_NOT_ACCESSED",
            }
        )
        # Four bytes also cover a null best epoch; metric's 24 bytes cover binary64.
        logical = len(canonical_json_bytes(fixed)) + 1
        allocated = (
            (logical + allocation_unit_bytes - 1) // allocation_unit_bytes * allocation_unit_bytes
        )
        if allocated > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_GEOMETRY_EXCEEDS_POLICY")
        paths.add(path.casefold())
        roster[operation] = {
            "path": path,
            "identity": copy.deepcopy(identity),
            "fixed_manifest": fixed,
            "logical_bound_bytes": logical,
            "allocated_bound_bytes": allocated,
        }
    source = Path(__file__).parent.parent
    return {
        "schema_version": "mp2-cost-native-deep-manifest-storage/1.0",
        "operations": roster,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "numeric_token_bound_bytes": 24,
        "serializer_binding": {
            "python_implementation": sys.implementation.name,
            "python_version": sys.version,
            "float_mantissa_bits": sys.float_info.mant_dig,
            "float_radix": sys.float_info.radix,
            "float_max_exp": sys.float_info.max_exp,
            "canonical_source_sha256": sha256_file(source / "hashing.py"),
            "json_encoder_source_sha256": sha256_file(Path(json.encoder.__file__)),
            "checkpoint_source_sha256": sha256_file(source / "training/local_v5_checkpoint.py"),
        },
        "scope": "PROSPECTIVE_NATIVE_DEEP_MANIFEST_ONLY",
        "complete_transaction_proof": True,
    }


def native_deep_receipt_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    user_ids: list[int],
    candidate_item_ids: list[int],
    cutoff: int,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Prove both native Deep epoch and top-k files, not an entire epoch bundle."""
    import json.encoder
    import sys

    if (
        type(operations) is not dict
        or not 1 <= len(operations) <= 1280
        or type(source_manifest_sha256) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256)
        or sys.implementation.name != "cpython"
        or sys.float_info.radix != 2
        or sys.float_info.mant_dig != 53
        or sys.float_info.max_exp != 1024
    ):
        raise IntegrityError("BOUNDED_DEEP_RECEIPT_STORAGE_GEOMETRY")
    roots: set[str] = set()
    specs: dict[str, dict[str, Any]] = {}
    for operation, spec in sorted(operations.items()):
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"root", "epoch", "example_count"}:
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_OUTPUT_ROSTER")
        root = safe_name(spec["root"])
        if (
            type(spec["epoch"]) is not int
            or not 1 <= spec["epoch"] <= 16
            or type(spec["example_count"]) is not int
            or not 1 <= spec["example_count"] < 2**61
            or not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/epochs/[1-9][0-9]*", root)
            or root.rsplit("/", 1)[1] != str(spec["epoch"])
            or root.casefold() in roots
        ):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_IDENTITY_OR_ROSTER")
        roots.add(root.casefold())
        specs[operation] = {**spec, "root": root}
    top_k = native_top_k_storage_policy(
        {operation: f"{row['root']}/top_k.json" for operation, row in specs.items()},
        user_ids=user_ids,
        candidate_item_ids=candidate_item_ids,
        cutoff=cutoff,
        allocation_unit_bytes=allocation_unit_bytes,
        source_manifest_sha256=source_manifest_sha256,
    )
    roster: dict[str, Any] = {}
    for operation, spec in specs.items():
        epoch, examples = spec["epoch"], spec["example_count"]
        fixed = {
            "epoch": epoch,
            "training": {
                "epoch": epoch,
                "effective_batch_size": 1024,
                "microbatch_size": 256,
                "optimizer_steps": (examples + 1023) // 1024,
                "pair_count": examples * 4,
                "mean_pairwise_loss": 10**23,
                "negatives_per_positive": 4,
                "runtime_identity": "LEGACY_TRAINING_COST_EVALUATOR",
                "wall_ns": 2**63 - 1,
                "phase_wall_ns": None,
                "instrumentation_and_loop_ns": None,
                "timing_scope": "SYNCHRONIZED_GROUPED_TRAINING_WALL_NOT_KERNEL_BUSY",
            },
            "semantic": {
                "epoch": epoch,
                "mean_pairwise_loss": 10**23,
                "NDCG@10": 10**23,
                "model_state_sha256": "f" * 64,
                "score_chunks_sha256": "f" * 64,
            },
            "checkpoint_manifest_sha256": "f" * 64,
            "score_manifest_sha256": "f" * 64,
        }
        logical = len(canonical_json_bytes(fixed)) + 1
        files = {
            f"{spec['root']}/epoch.json": {
                "logical_bound_bytes": logical,
                "allocated_bound_bytes": (logical + allocation_unit_bytes - 1)
                // allocation_unit_bytes
                * allocation_unit_bytes,
            },
            f"{spec['root']}/top_k.json": {
                key: top_k["operations"][operation][key]
                for key in ("logical_bound_bytes", "allocated_bound_bytes")
            },
        }
        allocated = sum(row["allocated_bound_bytes"] for row in files.values())
        if allocated > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_GEOMETRY_EXCEEDS_POLICY")
        roster[operation] = {
            **spec,
            "fixed_receipt": fixed,
            "files": files,
            "allocated_bound_bytes": allocated,
        }
    source = Path(__file__).parent.parent
    return {
        "schema_version": "mp2-cost-native-deep-receipt-storage/1.0",
        "operations": roster,
        "top_k_storage_policy": top_k,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "numeric_token_bound_bytes": 24,
        "serializer_binding": {
            "python_implementation": sys.implementation.name,
            "python_version": sys.version,
            "float_mantissa_bits": sys.float_info.mant_dig,
            "float_radix": sys.float_info.radix,
            "float_max_exp": sys.float_info.max_exp,
            "canonical_source_sha256": sha256_file(source / "hashing.py"),
            "json_encoder_source_sha256": sha256_file(Path(json.encoder.__file__)),
            "training_source_sha256": sha256_file(source / "training/local_v5_qualification.py"),
            "runtime_source_sha256": sha256_file(source / "training/cost_optimized_runtime_02.py"),
            "driver_source_sha256": sha256_file(source / "training/cost_native_io_01.py"),
        },
        "scope": "PROSPECTIVE_NATIVE_DEEP_RECEIPT_AND_TOP_K_TRANSACTION_ONLY",
        "complete_transaction_proof": True,
    }


def native_reference_receipt_storage_policy(
    operations: dict[str, dict[str, Any]],
    *,
    namespace: Path,
    user_ids: list[int],
    candidate_item_ids: list[int],
    cutoff: int,
    allocation_unit_bytes: int,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Bound Reference epoch/top-k together, retaining the exact checkpoint return schema."""
    reject_reparse_path(namespace)
    if not namespace.is_absolute() or namespace != namespace.resolve():
        raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_NAMESPACE")
    if type(operations) is not dict or not 1 <= len(operations) <= 1280:
        raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_STORAGE_GEOMETRY")
    specs: dict[str, dict[str, Any]] = {}
    for operation, spec in operations.items():
        operation_name(operation)
        if type(spec) is not dict or set(spec) != {"root", "identity", "loss_components"}:
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
        root, identity, components = (
            safe_name(spec["root"]),
            spec["identity"],
            spec["loss_components"],
        )
        if (
            not re.fullmatch(r"packets/[a-z0-9][a-z0-9-]{0,99}/epochs/[1-9][0-9]*", root)
            or type(identity) is not dict
            or type(identity.get("epoch")) is not int
            or not 1 <= identity["epoch"] <= 100
            or root.rsplit("/", 1)[1] != str(identity["epoch"])
            or type(components) is not int
            or not 0 <= components <= 16
        ):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_IDENTITY_OR_ROSTER")
        specs[operation] = {"root": root, "identity": identity, "loss_components": components}
    manifests = native_reference_manifest_storage_policy(
        {
            operation: {
                "path": f"{spec['root']}/checkpoint/manifest.json",
                "identity": spec["identity"],
            }
            for operation, spec in specs.items()
        },
        allocation_unit_bytes=allocation_unit_bytes,
        source_manifest_sha256=source_manifest_sha256,
    )
    top_k = native_top_k_storage_policy(
        {operation: f"{spec['root']}/top_k.json" for operation, spec in specs.items()},
        user_ids=user_ids,
        candidate_item_ids=candidate_item_ids,
        cutoff=cutoff,
        allocation_unit_bytes=allocation_unit_bytes,
        source_manifest_sha256=source_manifest_sha256,
    )
    roster: dict[str, Any] = {}
    for operation, spec in specs.items():
        root, components = spec["root"], spec["loss_components"]
        fixed = {
            "epoch": spec["identity"]["epoch"],
            "semantic": {
                "training_loss": [10**23] * components if components else 10**23,
                "model_state_sha256": "f" * 64,
                "optimizer_state_sha256": "f" * 64,
                "rng_sha256": "f" * 64,
                "NDCG@10": 10**23,
            },
            "checkpoint": {
                **manifests["operations"][operation]["fixed_manifest"],
                "manifest_sha256": "f" * 64,
                "checkpoint_path": str(namespace / root / "checkpoint/checkpoint.pt"),
            },
            "score_manifest_sha256": "f" * 64,
            "legacy_parity": "EXACT",
        }
        logical = len(canonical_json_bytes(fixed)) + 1
        files = {
            f"{root}/epoch.json": {
                "logical_bound_bytes": logical,
                "allocated_bound_bytes": (logical + allocation_unit_bytes - 1)
                // allocation_unit_bytes
                * allocation_unit_bytes,
            },
            f"{root}/top_k.json": {
                key: top_k["operations"][operation][key]
                for key in ("logical_bound_bytes", "allocated_bound_bytes")
            },
        }
        allocated = sum(row["allocated_bound_bytes"] for row in files.values())
        if allocated > policy_caps()["sidecars"]:
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_GEOMETRY_EXCEEDS_POLICY")
        roster[operation] = {
            **copy.deepcopy(spec),
            "fixed_receipt": fixed,
            "files": files,
            "allocated_bound_bytes": allocated,
        }
    return {
        "schema_version": "mp2-cost-native-reference-receipt-storage/1.0",
        "namespace": str(namespace),
        "operations": roster,
        "top_k_storage_policy": top_k,
        "allocation_unit_bytes": allocation_unit_bytes,
        "source_manifest_sha256": source_manifest_sha256,
        "numeric_token_bound_bytes": 24,
        "serializer_binding": {
            **manifests["serializer_binding"],
            "driver_source_sha256": sha256_file(Path(__file__).with_name("cost_native_io_01.py")),
        },
        "scope": "PROSPECTIVE_NATIVE_REFERENCE_RECEIPT_AND_TOP_K_TRANSACTION_ONLY",
        "complete_transaction_proof": True,
    }


def generated_calibration_policy() -> dict[str, Any]:
    """A fixed exception for generated control calibration, not scientific retention."""
    return {
        "schema_version": "mp2-cost-generated-calibration-retirement/1.0",
        "families": ["reference", "deep"],
        "bundles": ["old", "latest"],
        "raw_kinds": ["scores", "checkpoint"],
        "max_native_control_bytes": 16384,
        "scope": "GENERATED_RAW_ONLY_AFTER_CUSTODY_READBACK",
        "scientific_retention_unchanged": True,
    }


def _generated_policy_matches(value: Any) -> bool:
    return type(value) is dict and canonical_json_bytes(value) == canonical_json_bytes(
        generated_calibration_policy()
    )


def writer_coverage() -> dict[str, Any]:
    """A Python stream is not proof that an unadapted library uses that stream."""
    return {
        "schema_version": "mp2-cost-writer-coverage/1.0",
        "policy_caps": policy_caps(),
        "bounded_entrypoint": "BoundedArtifactWriter.transaction/BoundedTransaction.open",
        "native_descriptor_access": "REJECTED",
        "foreign_thread_access": "REJECTED",
        "serializer_fixture_roundtrips": ["torch.save(stream)", "numpy.save(stream)"],
        "candidate_adapter": "cost_native_io_01.NativeBoundedIO/BoundedRecBoleTrainer",
        "candidate_dispatch_scope": "ADAPTER_FIXTURES_NOT_COMPLETE_PACKET_EXECUTOR",
        "candidate_background_outputs": "NO_TENSORBOARD_OR_WANDB_IN_ADAPTER_CONSTRUCTOR",
        "candidate_checkpoint_container": "TORCH_STREAM_ZIP_ARCHIVE_PREFIX_SEPARATELY_BOUND",
        "uncovered_production_writers": [
            "recbole.Trainer.__init__/get_tensorboard/SummaryWriter/background-event-writer",
            "evaluation.persistence-and-cost-persistence/unbounded-sidecars",
            "native-cache-temp-and-input-materialization/unbounded-output-paths",
            "checkpoint-and-score-path-writers/missing-shared-ledger-and-aggregate-admission",
        ],
        "integrated_bounded_writers": [],
        "fixed_file_cap_integrations": [
            "local_v5_reference._save_reference_checkpoint/cost_bounded_serialization_52",
            "local_v5_checkpoint.save_training_checkpoint/cost_bounded_serialization_52",
            "evaluation.artifacts.materialize_scores/cost_bounded_serialization_52",
        ],
        "fixed_file_caps_are_complete_accounting_coverage": False,
        "storage_enforcement_complete": False,
        "measured_serializer_timing_transfer_qualified": False,
        "scientific_execution_authorized": False,
    }


def native_retention_contract() -> dict[str, Any]:
    """Declare existing native retention constraints, never additional disposal rights."""
    return {
        "scope": "CURRENT_AUTHORITY_NAMESPACE_ONLY",
        "roles": ["accepted", "best", "dependency", "latest"],
        "nonempty_roles": ["best", "latest"],
        "monotone_roles": ["accepted", "dependency"],
        "raw_disposal_categories": {"checkpoint": ".pt", "scores": ".npy"},
        "historical_disposal_authorized": False,
        "scientific_retention_unchanged": True,
    }


def _validate_native_retention_contract(document: dict[str, Any]) -> None:
    policy = document.get("native_packet_dispatch")
    if (
        type(policy) is dict
        and policy.get("schema_version") == "mp2-benchmark-lane-dispatch/1.1"
        and (
            type(policy.get("retention_contract")) is not dict
            or canonical_json_bytes(policy["retention_contract"])
            != canonical_json_bytes(native_retention_contract())
        )
    ):
        raise IntegrityError("BOUNDED_NATIVE_RETENTION_CONTRACT")


def admitted_lane_writer_coverage() -> dict[str, Any]:
    """Describe the bounded native lane without certifying unrelated writers."""
    source_scopes = (
        ("cost_native_io_01.py", "NATIVE_PACKET_DRIVER_AND_BOUNDED_RECOBOLE_TRAINER"),
        ("cost_closure_control_calibration_01.py", "GENERATED_LIFECYCLE_FIXED_SIDECAR_ROSTER"),
        ("cost_bounded_io_01.py", "BOUNDED_STORAGE_ADMISSION_AND_WRITER_PRIMITIVES"),
        ("cost_optimization_closure_03.py", "WORKER_OWNED_COORDINATOR_AND_BOUNDED_PACKET_DISPATCH"),
        ("cost_closure_components.py", "COMPONENT_NATIVE_REPLACEMENT_ROUTES"),
        ("cost_closure_itemknn.py", "ITEMKNN_NATIVE_REPLACEMENT_ROUTE"),
        ("cost_runtime_custody.py", "PROCESS_OWNERSHIP_AND_LANE_CUSTODY"),
        (
            "cost_profile_process_03.py",
            "GENERATED_PROCESS_JOB_TREE_WATCHDOG_AND_BOUNDED_EOF_OBSERVATION",
        ),
        ("cost_engineering_write_guard_33.py", "CURRENT_AND_HISTORICAL_PATH_PROHIBITIONS"),
        ("cost_control_storage_01.py", "BOUNDED_CONTROL_PUBLICATION_AND_COMPANIONS"),
        ("cost_continuous_session_01.py", "CONTINUOUS_RECIPE_AND_POPULATION_BOUNDS"),
        (
            "local_v5_validation_worker.py",
            "SCIENTIFIC_ENTRYPOINT_PROHIBITIONS_NOT_WRITER_QUALIFICATION",
        ),
    )
    recbole_background_writer = "/".join(
        (
            "recbole.Trainer.__init__",
            "get_tensorboard",
            "SummaryWriter",
            "background-event-writer",
        )
    )
    checkpoint_writer = "/".join(
        (
            "checkpoint-and-score-path-writers",
            "missing-shared-ledger-and-aggregate-admission",
        )
    )
    deferred_writer_groups = [
        {
            "writer_group": recbole_background_writer,
            "route_state": "DEFERRED_NOT_ADMITTED",
            "guard": "BoundedRecBoleTrainer.fit/evaluate/_save_checkpoint/resume_checkpoint",
            "enforcement": "NATIVE_IO_DEFERRED_ENTRYPOINT_*",
        },
        {
            "writer_group": "evaluation.persistence-and-cost-persistence/unbounded-sidecars",
            "route_state": "DEFERRED_NOT_ADMITTED",
            "guard": (
                "NativeContinuousPacketDriver._export_surface/run_reference/run_deep"
                " -> NativeBoundedIO.save_documents/save_cost_evaluation/save_legacy_evaluation"
            ),
            "enforcement": "NATIVE_IO_DOCUMENT_CATEGORY_AND_FIXED_ROSTER",
        },
        {
            "writer_group": "native-cache-temp-and-input-materialization/unbounded-output-paths",
            "route_state": "DEFERRED_NOT_ADMITTED",
            "guard": "_admit_native_data_setup/copy_admitted_inputs",
            "enforcement": "NATIVE_PACKET_DATA_SETUP_*_AND_INPUT_ROSTER",
        },
        {
            "writer_group": checkpoint_writer,
            "route_state": "DEFERRED_NOT_ADMITTED",
            "guard": (
                "NativeBoundedIO.materialize_scores/save_checkpoint_payload/"
                "save_training_checkpoint"
            ),
            "enforcement": "BOUNDED_TRANSACTION_SHARED_LEDGER_AND_POLICY_ROSTERS",
        },
    ]
    scientific_prohibition_sites = [
        "ValidationUnitWorker.execute",
        "ProductionValidationUnitExecutor.execute_segment",
        "ProductionValidationUnitExecutor.execute_result",
        "ProductionValidationUnitExecutor.cleanup_result",
        "local_v5_validation_worker._write_new_json",
        "local_v5_validation_worker._append_jsonl",
    ]
    # A call-site inventory is not an implementation acceptance receipt.
    # Leave every row unqualified until its source-bound enforcement is verified.
    coverage_rows = [
        {
            "blocker": "storage_and_historical_reservation_bindings",
            "state": "NOT_RUN",
            "qualification": "FRESH_CENSUS_AND_ADMISSION_PENDING",
            "call_sites": ["NativeContinuousPacketDriver._control", "BoundedArtifactWriter"],
        },
        {
            "blocker": "maximum_packet_seal_census_population",
            "state": "NOT_RUN",
            "qualification": "MAXIMUM_POPULATION_ROSTER_AND_ENFORCEMENT_PENDING",
            "call_sites": [
                "NativeContinuousPacketDriver._export_surface",
                "run_generated_family_lifecycle",
                "seal_packet",
            ],
        },
        {
            "blocker": "continuous_native_io_driver",
            "state": "NOT_RUN",
            "qualification": "CONTINUOUS_DRIVER_ENFORCEMENT_PENDING",
            "call_sites": [
                "dispatch_bounded_native_packet",
                "run_generated_family_lifecycle",
                "run_generated_owned_worker",
                "run_generated_owned_coordinator",
                "NativeBoundedIO",
            ],
        },
        {
            "blocker": "bootstrap_guard_ownership_journal_writers",
            "state": "NOT_RUN",
            "qualification": "CONTROL_WRITER_BOUNDS_AND_OWNERSHIP_PENDING",
            "prohibition_only_call_sites": scientific_prohibition_sites,
            "call_sites": [
                "NativeContinuousPacketDriver._control",
                "BoundedArtifactWriter",
                "run_generated_owned_worker",
                "run_generated_owned_coordinator",
                *scientific_prohibition_sites,
            ],
        },
        {
            "blocker": "epoch_sidecars_aggregate_retention",
            "state": "NOT_RUN",
            "qualification": "SIDECAR_AGGREGATE_AND_RETENTION_ENFORCEMENT_PENDING",
            "call_sites": [
                "NativeBoundedIO.save_documents",
                "NativeBoundedIO.save_numpy_chunks",
                "BoundedArtifactWriter.retain",
                "BoundedArtifactWriter.dispose",
                "_validate_native_retention_contract",
            ],
        },
        {
            "blocker": "serializer_geometry_allocation_rounding",
            "state": "NOT_RUN",
            "qualification": "FOCUSED_STATIC_PASS_ONLY",
            "call_sites": ["NativeBoundedIO.save_training_checkpoint", "BoundedTransaction.open"],
        },
        {
            "blocker": "maximum_population_multi_lease_timing",
            "state": "NOT_RUN",
            "qualification": "MAXIMUM_POPULATION_AND_MULTI_LEASE_ENFORCEMENT_PENDING",
            "call_sites": [
                "dispatch_bounded_native_packet",
                "run_generated_family_lifecycle",
                "NativeContinuousPacketDriver",
            ],
        },
        {
            "blocker": "component_replacement_mapping",
            "state": "NOT_RUN",
            "qualification": "FOCUSED_DELTA_PASS_ONLY",
            "call_sites": [
                "measure_mostpop",
                "measure_itemknn",
                "measure_rule",
                "measure_hybrid",
                "NativeContinuousPacketDriver.run_reference",
                "NativeContinuousPacketDriver.run_itemknn",
                "NativeContinuousPacketDriver.run_rule",
                "NativeContinuousPacketDriver.run_hybrid",
            ],
        },
        {
            "blocker": "coordinator_terminal_tail_watchdog_teardown",
            "state": "NOT_RUN",
            "qualification": "TERMINAL_TAIL_WATCHDOG_AND_TEARDOWN_ENFORCEMENT_PENDING",
            "call_sites": [
                "dispatch_bounded_native_packet",
                "NativeContinuousPacketDriver._control",
                "GeneratedProcessDeadline",
                "run_bounded_generated_child",
                "run_generated_owned_worker",
                "run_generated_owned_coordinator",
                "reconcile_generated_worker_terminal",
                "_native_invocation_deadline",
            ],
        },
    ]
    return {
        "schema_version": "mp2-cost-admitted-lane-writer-coverage/1.0",
        "state": "ADMITTED_LANE_CALL_SITE_INVENTORY_NOT_QUALIFIED",
        "source_bindings": [
            {
                "path": str(Path(__file__).with_name(name)),
                "sha256": _sha256_file(Path(__file__).with_name(name)),
                "scope": scope,
            }
            for name, scope in source_scopes
        ],
        "bounded_call_sites": [
            "worker_workload",
            "run_generated_owned_worker",
            "run_generated_owned_coordinator",
            "reconcile_generated_worker_terminal",
            "run_generated_family_lifecycle",
            "dispatch_bounded_native_packet",
            "dispatch_bounded_native_sequence",
            "BoundedArtifactWriter.open_successor_packet",
            "_native_invocation_deadline",
            "GeneratedProcessDeadline",
            "run_bounded_generated_child",
            "measure_mostpop",
            "measure_itemknn",
            "measure_rule",
            "measure_hybrid",
            "NativeContinuousPacketDriver._control",
            "NativeContinuousPacketDriver._export_surface",
            "NativeContinuousPacketDriver.run_itemknn",
            "NativeContinuousPacketDriver.run_rule",
            "NativeContinuousPacketDriver.run_hybrid",
            "NativeContinuousPacketDriver.run_reference",
            "NativeContinuousPacketDriver.run_deep",
            "NativeBoundedIO.save_numpy_chunks",
            "NativeBoundedIO.save_documents",
            "NativeBoundedIO.save_training_checkpoint",
            "BoundedRecBoleTrainer.__init__",
        ],
        "deferred_branches": [
            {
                "branch": "recbole.Trainer.fit/evaluate/_save_checkpoint/resume_checkpoint",
                "guard": "NATIVE_IO_DEFERRED_ENTRYPOINT_*",
            },
            {
                "branch": "RecBole dataset/dataloader/logging/cache side effects",
                "guard": "NATIVE_PACKET_DATA_SETUP_*",
            },
            {
                "branch": "unadapted native path-based checkpoint output",
                "guard": "saved_model_file=None_and_bounded_checkpoint_methods",
            },
        ],
        "deferred_writer_groups": deferred_writer_groups,
        "coverage_rows": coverage_rows,
        "coverage_row_count": len(coverage_rows),
        "timing_qualified": False,
        "rehearsal_qualification": "PENDING",
        "production_measurement": "PENDING",
        "deferred_lane_guard_pass": all(
            row["route_state"] == "DEFERRED_NOT_ADMITTED" for row in deferred_writer_groups
        ),
        "unqualified_production_writers_remain": list(
            writer_coverage()["uncovered_production_writers"]
        ),
        "production_coverage_pass": False,
        "scientific_writer_bounds_qualified": False,
        "scientific_execution_authorized": False,
    }


def policy_peak(
    census: dict[str, Any],
    recipe: dict[str, Any],
    *,
    score_storage_policy: dict[str, Any] | None = None,
    input_storage_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Whole-cache simultaneous occupancy under the enforceable policy caps."""
    if (
        census.get("schema_version")
        not in {"mp2-cost-storage-census/1.0", "mp2-cost-storage-census/1.1"}
        or census.get("scope") != "FILESYSTEM_METADATA_ONLY_NOT_PAYLOAD_REPLAY"
        or census.get("payload_bytes_certified") is not False
        or recipe.get("schema_version") != "mp2-cost-continuous-recipe/1.1"
        or recipe.get("counts_scope") != "DRIVER_SOURCE_DERIVED_BOUNDS_NOT_PHYSICAL_OBSERVATIONS"
    ):
        raise IntegrityError("BOUNDED_PEAK_INPUT_SCOPE")
    maximum = recipe["branches"]["maximum"]
    for name, expected in {
        "training_runs": 17,
        "packets": 38,
        "epoch_transaction": 1280,
        "surface_transaction": 21,
        "epoch_surface_transactions": 1301,
    }.items():
        if size(maximum[name]) != expected:
            raise IntegrityError("BOUNDED_PEAK_RECIPE_DRIFT")
    caps = policy_caps()
    input_bound = maximum["packets"] * caps["input"]
    if input_storage_policy is not None:
        if type(input_storage_policy) is not dict or not {
            "packets",
            "allocation_unit_bytes",
            "source_inventory_sha256",
        }.issubset(input_storage_policy):
            raise IntegrityError("BOUNDED_PEAK_INPUT_POLICY")
        expected_input_policy = input_reservation_policy(
            input_storage_policy["packets"],
            allocation_unit_bytes=input_storage_policy["allocation_unit_bytes"],
            source_inventory_sha256=input_storage_policy["source_inventory_sha256"],
        )
        if (
            canonical_json_bytes(input_storage_policy)
            != canonical_json_bytes(expected_input_policy)
            or len(expected_input_policy["packets"]) != maximum["packets"]
        ):
            raise IntegrityError("BOUNDED_PEAK_INPUT_POLICY")
        packet_ids = maximum.get("packet_ids")
        if (
            type(packet_ids) is not list
            or len(packet_ids) != maximum["packets"]
            or any(
                type(name) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", name)
                for name in packet_ids
            )
            or len(set(packet_ids)) != len(packet_ids)
            or set(packet_ids) != set(expected_input_policy["packets"])
        ):
            raise IntegrityError("BOUNDED_PEAK_INPUT_PACKET_ROSTER")
        input_bound = sum(expected_input_policy["packet_allocated_bounds"].values())
    score_bound = caps["scores"]
    if score_storage_policy is not None:
        if type(score_storage_policy) is not dict or not {
            "chunk_rows",
            "columns",
            "allocation_unit_bytes",
            "source_manifest_sha256",
        }.issubset(score_storage_policy):
            raise IntegrityError("BOUNDED_PEAK_SCORE_POLICY")
        expected_score_policy = score_reservation_policy(
            score_storage_policy["chunk_rows"],
            score_storage_policy["columns"],
            allocation_unit_bytes=score_storage_policy["allocation_unit_bytes"],
            source_manifest_sha256=score_storage_policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(score_storage_policy) != canonical_json_bytes(
            expected_score_policy
        ):
            raise IntegrityError("BOUNDED_PEAK_SCORE_POLICY")
        score_bound = expected_score_policy["allocated_bound_bytes"]
    counts = {
        "best_latest_bundles": 2 * maximum["training_runs"],
        "current_bundle": 1,
        "staging_bundles": 2,
        "component_surfaces": maximum["surface_transaction"],
        "component_checkpoints": 3,
        "epoch_surface_sidecars": maximum["epoch_surface_transactions"],
        "packet_input_and_auxiliary": maximum["packets"],
        "future_test_surfaces_metadata_only": 36,
    }
    allocations = {
        "historical_charged_bytes": size(census["charged_unique_bytes"]),
        "training_and_staging_payloads": sum(
            counts[name]
            for name in (
                "best_latest_bundles",
                "current_bundle",
                "staging_bundles",
            )
        )
        * (score_bound + caps["checkpoint"]),
        "component_payloads": counts["component_surfaces"] * score_bound,
        "component_checkpoint_payloads": counts["component_checkpoints"] * caps["checkpoint"],
        "epoch_surface_sidecars": counts["epoch_surface_sidecars"] * caps["sidecars"],
        "input_and_auxiliary": input_bound
        + counts["packet_input_and_auxiliary"] * caps["auxiliary"],
        "future_test_payloads_and_sidecars": 36 * (caps["scores"] + caps["sidecars"]),
        "controls_analysis": caps["execution_controls"],
    }
    result = {
        "schema_version": "mp2-cost-bounded-policy-peak/1.0",
        "projected_peak_bytes": sum(allocations.values()),
        "allocations_bytes": allocations,
        "counts": counts,
        "size_basis": "POLICY_CAPS_NOT_OBSERVED_SERIALIZED_SIZES",
        "writer_coverage_complete": False,
        "test_payload_accessed": False,
        "scientific_execution_authorized": False,
    }
    if score_storage_policy is not None:
        result["schema_version"] = "mp2-cost-bounded-policy-peak/1.1"
        result["size_basis"] = "POLICY_CAPS_AND_PROSPECTIVE_VALIDATION_SCORE_GEOMETRY"
        result["validation_score_storage_policy"] = score_storage_policy
        result["test_score_geometry_credited"] = False
    if input_storage_policy is not None:
        result["schema_version"] = "mp2-cost-bounded-policy-peak/1.2"
        result["size_basis"] = "POLICY_CAPS_AND_PROSPECTIVE_SERIALIZER_INPUT_BOUNDS"
        result["input_storage_policy"] = expected_input_policy
    return result


def _control_policy_limits(document: dict[str, Any]) -> tuple[str, int, int]:
    from ai_service_v2.training.cost_closure_control_calibration_01 import (
        CURRENT_AUTHORITY_SCHEMA,
        CURRENT_CONTROL_POLICY_SCHEMA,
        current_calibration_control_policy,
    )

    policy = document.get("control_plane")
    if document.get("schema_version") == CURRENT_AUTHORITY_SCHEMA or (
        type(policy) is dict and policy.get("schema_version") == CURRENT_CONTROL_POLICY_SCHEMA
    ):
        try:
            expected = current_calibration_control_policy(document)
            if canonical_json_bytes({"policy": policy}) != canonical_json_bytes(
                {"policy": expected}
            ):
                raise IntegrityError("CURRENT_CALIBRATION_CONTROL_POLICY_DRIFT")
        except IntegrityError as error:
            raise IntegrityError("CURRENT_CALIBRATION_CONTROL_POLICY") from error
        return CURRENT_CONTROL_POLICY_SCHEMA, 1024, 1024 * MIB
    return "mp2-cost-bounded-control-policy/1.0", 512, 16 * MIB


class BoundedControlPublisher:
    """Fixed, caller-authenticated controls, including preclaim bootstrap.

    A separate small reservation covers these records and their own ledger.
    Payload accounting must be supplied once a native artifact ledger exists;
    this control boundary never certifies payload or sandboxes native code.
    """

    def __init__(
        self,
        cache: Path,
        namespace: Path,
        *,
        authority: Path,
        storage_lane: Path,
        expected_roster: tuple[str, ...],
        approved_aliases: Mapping[str, str] | None = None,
        admitted_owner: Path | None = None,
        native_accounting: Callable[[], dict[str, int]] | None = None,
    ) -> None:
        import psutil  # type: ignore[import-untyped]

        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(namespace)
        for path in (cache, namespace, authority, storage_lane):
            reject_reparse_path(path)
        self.cache, self.namespace = cache.resolve(), namespace.resolve()
        self.authority, self.lane = authority, storage_lane
        self.aliases, self.native_accounting = approved_aliases, native_accounting
        self.owner = admitted_owner
        self.pid, self.thread = os.getpid(), threading.get_ident()
        self.actor = process_identity(psutil.Process())
        self.authority_sha256 = sha256_file(authority)
        document = read_canonical_json(authority)
        self.storage_authority = copy.deepcopy(document)
        policy = document.get("control_plane")
        policy_schema, maximum_paths, maximum_reservation = _control_policy_limits(document)
        _native_invocation_deadline(document, self.namespace / "invocation_guard.json")
        if (
            self.namespace == self.cache
            or not self.namespace.is_relative_to(self.cache)
            or not storage_lane.is_dir()
            or storage_lane.resolve().is_relative_to(self.namespace)
            or document.get("namespace") != str(namespace)
            or document.get("writer_policy") != policy_caps()
            or document.get("scientific_execution_authorized") is not False
            or type(policy) is not dict
            or set(policy)
            != {"schema_version", "paths", "reserved_bytes", "max_document_bytes", "scope"}
            or policy["schema_version"] != policy_schema
            or policy["scope"] != "FIXED_CONTROL_ROSTER_NOT_ARBITRARY_JSON"
            or type(policy["paths"]) is not list
            or policy["paths"] != list(expected_roster)
            or not 1 <= len(expected_roster) <= maximum_paths
            or any(type(name) is not str for name in expected_roster)
            or len({name.casefold() for name in expected_roster}) != len(expected_roster)
            or any(
                type(name) is not str
                or safe_name(name) != name
                or not name.endswith(".json")
                or name.startswith("bounded-controls/")
                for name in expected_roster
            )
            or type(policy["reserved_bytes"]) is not int
            or not MIB <= policy["reserved_bytes"] <= maximum_reservation
            or type(policy["max_document_bytes"]) is not int
            or not 1 <= policy["max_document_bytes"] <= MIB
        ):
            raise IntegrityError("BOUNDED_CONTROL_POLICY_OR_ROSTER")
        self.policy = policy
        self.roster = expected_roster
        self.unit = allocation_unit(self.cache)
        if policy_schema.endswith("/1.1") and document.get("allocation_unit_bytes") != self.unit:
            raise IntegrityError("CURRENT_CALIBRATION_CONTROL_POLICY_ALLOCATION")
        self.directory = self.namespace / "bounded-controls"
        self.reserve_path = self.directory / "reserve.json"
        with serialized_storage_lane(self.lane):
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            created = not self.reserve_path.exists()
            if created:
                if self.directory.exists() or (self.namespace / "invocation_guard.json").exists():
                    raise IntegrityError("BOUNDED_CONTROL_BOOTSTRAP_IN_DOUBT")
                admission = self._storage_admission(
                    census["charged_unique_bytes"] + policy["reserved_bytes"],
                    current_bytes=census["charged_unique_bytes"],
                    free_bytes=shutil.disk_usage(self.cache).free,
                )
                reserve = {
                    "schema_version": "mp2-cost-bounded-control-reservation/1.0",
                    "authority_sha256": self.authority_sha256,
                    "policy_sha256": canonical_json_sha256(policy),
                    "namespace": str(self.namespace),
                    "creator": self.actor,
                    "admission": admission,
                    "scope": "PRECLAIM_STORAGE_RESERVATION_NOT_COMPUTE_CLAIM",
                }
                data = canonical_json_bytes(reserve) + b"\n"
                if self._round(len(data)) > policy["reserved_bytes"]:
                    raise IntegrityError("BOUNDED_CONTROL_RESERVATION_CAP")
                self.directory.mkdir()
                self._raw_write(self.reserve_path, data)
            self.reserve_sha256 = sha256_file(self.reserve_path)
            snapshot = self.snapshot()
            self._baseline_charged = census["charged_unique_bytes"] - (
                0 if created else snapshot["actual_bytes"]
            )
            self._baseline_files = census["unique_files"] - (0 if created else snapshot["files"])
            self._authenticate()

    def _storage_admission(
        self, peak: object, *, current_bytes: object, free_bytes: object
    ) -> dict[str, Any]:
        return storage_admission_for_authority(
            peak,
            authority=read_canonical_json(self.authority),
            current_bytes=current_bytes,
            free_bytes=free_bytes,
        )

    def _round(self, value: int) -> int:
        return (value + self.unit - 1) // self.unit * self.unit

    def _raw_write(self, path: Path, data: bytes) -> None:
        _native_invocation_deadline(
            read_canonical_json(self.authority), self.namespace / "invocation_guard.json"
        )
        reject_reparse_path(path)
        if (
            self.policy["schema_version"] == "mp2-cost-bounded-control-policy/1.1"
            and path.parent == self.directory
            and len(data) > 65536
        ):
            raise IntegrityError("CURRENT_CALIBRATION_CONTROL_COMPANION_CAP")
        if len(data) > self.policy["max_document_bytes"]:
            raise IntegrityError("BOUNDED_CONTROL_DOCUMENT_CAP")
        snapshots = _CONTROL_SNAPSHOT_PASS.get()
        if snapshots is not None:
            snapshots.clear()
        invalidate_materialization(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            if stream.write(data) != len(data):
                raise IntegrityError("BOUNDED_CONTROL_PARTIAL_WRITE_IN_DOUBT")
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != data:
            raise IntegrityError("BOUNDED_CONTROL_READBACK")

    def _authenticate(self) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(self.namespace)
        if os.getpid() != self.pid or threading.get_ident() != self.thread:
            raise IntegrityError("BOUNDED_CONTROL_FOREIGN_PROCESS_OR_THREAD")
        _reject_reparse_path(self.authority)
        if _sha256_file(self.authority) != self.authority_sha256:
            raise IntegrityError("BOUNDED_CONTROL_AUTHORITY_DRIFT")
        _native_invocation_deadline(
            read_canonical_json(self.authority), self.namespace / "invocation_guard.json"
        )
        reserve = read_canonical_json(self.reserve_path)
        if self.owner is None:
            if reserve["creator"] != self.actor:
                raise IntegrityError("BOUNDED_CONTROL_FOREIGN_OWNER")
        else:
            if self.owner.relative_to(self.namespace).as_posix() not in self.roster:
                raise IntegrityError("BOUNDED_CONTROL_FOREIGN_OWNER")
            descriptor = read_canonical_json(self.owner)
            if (
                resolve_owned_process(descriptor, descriptor["command"], check_parent=False)
                != self.actor
            ):
                raise IntegrityError("BOUNDED_CONTROL_FOREIGN_OWNER")
        guard = self.namespace / "invocation_guard.json"
        if guard.exists():
            claim = read_canonical_json(guard)
            if (
                claim.get("namespace") != str(self.namespace)
                or claim.get("authority_sha256") != self.authority_sha256
                or claim.get("automatic_retry") is not False
            ):
                raise IntegrityError("BOUNDED_CONTROL_CLAIM_DRIFT")

    def snapshot(self) -> dict[str, int]:
        """Declared control bytes only, without process or payload admission."""
        snapshots = _CONTROL_SNAPSHOT_PASS.get()
        key = (
            self.directory,
            self.authority_sha256,
            self.reserve_sha256,
            canonical_json_sha256(self.policy),
        )
        if snapshots is not None and key in snapshots:
            return dict(snapshots[key])
        result = self._snapshot()
        if snapshots is not None:
            snapshots[key] = dict(result)
        return result

    def _snapshot(self) -> dict[str, int]:
        current_policy = self.policy["schema_version"] == "mp2-cost-bounded-control-policy/1.1"
        if current_policy and self.reserve_path.stat().st_size > 65536:
            raise IntegrityError("CURRENT_CALIBRATION_CONTROL_COMPANION_CAP")
        reserve = read_canonical_json(self.reserve_path)
        if (
            set(reserve)
            != {
                "schema_version",
                "authority_sha256",
                "policy_sha256",
                "namespace",
                "creator",
                "admission",
                "scope",
            }
            or reserve["schema_version"] != "mp2-cost-bounded-control-reservation/1.0"
            or reserve["authority_sha256"] != self.authority_sha256
            or reserve["policy_sha256"] != canonical_json_sha256(self.policy)
            or reserve["namespace"] != str(self.namespace)
            or reserve["scope"] != "PRECLAIM_STORAGE_RESERVATION_NOT_COMPUTE_CLAIM"
            or sha256_file(self.reserve_path) != self.reserve_sha256
        ):
            raise IntegrityError("BOUNDED_CONTROL_RESERVATION_DRIFT")
        validate_identity(reserve["creator"])
        admission = reserve["admission"]
        if admission != self._storage_admission(
            admission["projected_peak_bytes"],
            current_bytes=admission["current_bytes"],
            free_bytes=admission["free_bytes"],
        ):
            raise IntegrityError("BOUNDED_CONTROL_ADMISSION_DRIFT")
        files = {self.reserve_path}
        declared = {"reserve.json"}
        for index, name in enumerate(self.roster):
            intent = self.directory / f"intent-{index:04d}.json"
            settled = self.directory / f"settled-{index:04d}.json"
            target = self.namespace / name
            for path in (intent, settled, target):
                reject_reparse_path(path)
            if not intent.exists():
                if target.exists() or settled.exists():
                    raise IntegrityError("BOUNDED_CONTROL_UNDECLARED_WRITE")
                continue
            if not settled.is_file() or not target.is_file():
                raise IntegrityError("BOUNDED_CONTROL_PARTIAL_WRITE_IN_DOUBT")
            if current_policy and any(path.stat().st_size > 65536 for path in (intent, settled)):
                raise IntegrityError("CURRENT_CALIBRATION_CONTROL_COMPANION_CAP")
            row, receipt = read_canonical_json(intent), read_canonical_json(settled)
            if (
                set(row)
                != {"authority_sha256", "reserve_sha256", "path", "bytes", "sha256", "actor"}
                or row["authority_sha256"] != self.authority_sha256
                or row["reserve_sha256"] != self.reserve_sha256
                or row["path"] != name
                or not 0 < size(row["bytes"]) <= self.policy["max_document_bytes"]
                or target.stat().st_size != row["bytes"]
                or sha256_file(target) != row["sha256"]
                or receipt
                != {"intent_sha256": sha256_file(intent), "state": "CONTROL_BYTES_READBACK"}
            ):
                raise IntegrityError("BOUNDED_CONTROL_BINDING_DRIFT")
            validate_identity(row["actor"])
            files.update((intent, settled, target))
            declared.update((intent.name, settled.name))
        if {path.name for path in self.directory.iterdir()} != declared:
            raise IntegrityError("BOUNDED_CONTROL_LEDGER_ROSTER")
        actual = charged = 0
        for path in files:
            info = path.stat()
            if not path.is_file() or info.st_nlink != 1:
                raise IntegrityError("BOUNDED_CONTROL_PATH_ALIAS")
            allocation = _allocated_size(path, info)
            actual += allocation
            charged += max(allocation, self._round(info.st_size))
        if charged > self.policy["reserved_bytes"]:
            raise IntegrityError("BOUNDED_CONTROL_RESERVATION_CAP")
        return {
            "actual_bytes": actual,
            "charged_bytes": charged,
            "files": len(files),
            "reserved_bytes": self.policy["reserved_bytes"],
            "pending_bytes": self.policy["reserved_bytes"] - charged,
        }

    def write_json(self, name: str, document: dict[str, Any]) -> None:
        self._authenticate()
        if type(name) is not str or name not in self.roster:
            raise IntegrityError("BOUNDED_CONTROL_PATH_NOT_ADMITTED")
        data = canonical_json_bytes(document) + b"\n"
        if len(data) > self.policy["max_document_bytes"]:
            raise IntegrityError("BOUNDED_CONTROL_DOCUMENT_CAP")
        if name == "invocation_guard.json" and (
            document.get("namespace") != str(self.namespace)
            or document.get("authority_sha256") != self.authority_sha256
            or document.get("automatic_retry") is not False
        ):
            raise IntegrityError("BOUNDED_CONTROL_CLAIM_DRIFT")
        with serialized_storage_lane(self.lane):
            self._authenticate()
            snapshot = self.snapshot()
            if (self.namespace / name).exists():
                raise IntegrityError("BOUNDED_CONTROL_ALREADY_PUBLISHED")
            if (self.namespace / "bounded-ledger").exists() and self.native_accounting is None:
                raise IntegrityError("BOUNDED_CONTROL_NATIVE_ACCOUNTING_REQUIRED")
            native = self._native_snapshot()
            current = (
                self._baseline_charged + snapshot["charged_bytes"] + size(native["charged_bytes"])
            )
            self._storage_admission(
                current + snapshot["pending_bytes"] + size(native["pending_bytes"]),
                current_bytes=current,
                free_bytes=shutil.disk_usage(self.cache).free,
            )
            index = self.roster.index(name)
            intent = self.directory / f"intent-{index:04d}.json"
            row = {
                "authority_sha256": self.authority_sha256,
                "reserve_sha256": self.reserve_sha256,
                "path": name,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "actor": self.actor,
            }
            intent_data = canonical_json_bytes(row) + b"\n"
            settled = {
                "intent_sha256": sha256_bytes(intent_data),
                "state": "CONTROL_BYTES_READBACK",
            }
            settled_data = canonical_json_bytes(settled) + b"\n"
            growth = sum(self._round(len(value)) for value in (intent_data, data, settled_data))
            if snapshot["charged_bytes"] + growth > snapshot["reserved_bytes"]:
                raise IntegrityError("BOUNDED_CONTROL_RESERVATION_CAP")
            self._raw_write(intent, intent_data)
            self._raw_write(self.namespace / name, data)
            staged = self.directory / f"settled-{index:04d}.staged.json"
            self._raw_write(staged, settled_data)
            # Windows rename publishes complete bytes and refuses an existing target.
            _native_invocation_deadline(
                read_canonical_json(self.authority), self.namespace / "invocation_guard.json"
            )
            staged.rename(self.directory / f"settled-{index:04d}.json")
            self.snapshot()

    def reconcile(self) -> dict[str, Any]:
        self._authenticate()
        with serialized_storage_lane(self.lane):
            snapshot = self.snapshot()
            if (self.namespace / "bounded-ledger").exists() and self.native_accounting is None:
                raise IntegrityError("BOUNDED_CONTROL_NATIVE_RECONCILIATION_REQUIRED")
            native = self._native_snapshot()
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            if (
                census["charged_unique_bytes"]
                != self._baseline_charged + snapshot["actual_bytes"] + native["actual_bytes"]
                or census["unique_files"]
                != self._baseline_files + snapshot["files"] + native["files"]
            ):
                raise IntegrityError("BOUNDED_CONTROL_OCCUPANCY_DRIFT")
            return {
                "state": "BOUNDED_CONTROL_COVERAGE_PASS_NON_AUTHORIZING",
                **snapshot,
                "payload_bytes_certified": False,
            }

    def _native_snapshot(self) -> dict[str, int]:
        value = (
            self.native_accounting()
            if self.native_accounting is not None
            else {"actual_bytes": 0, "charged_bytes": 0, "pending_bytes": 0, "files": 0}
        )
        if set(value) != {"actual_bytes", "charged_bytes", "pending_bytes", "files"}:
            raise IntegrityError("BOUNDED_CONTROL_NATIVE_ACCOUNTING_SHAPE")
        return {key: size(amount) for key, amount in value.items()}

    def bind_native_accounting(self, provider: Callable[[], dict[str, int]]) -> None:
        """Bind the admitted native ledger at a serialized packet boundary."""
        self._authenticate()
        with serialized_storage_lane(self.lane):
            if self.native_accounting is not None:
                raise IntegrityError("BOUNDED_CONTROL_ACCOUNTING_ALREADY_BOUND")
            self.native_accounting = provider
            native, controls = self._native_snapshot(), self.snapshot()
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            self._baseline_charged = (
                census["charged_unique_bytes"] - controls["actual_bytes"] - native["actual_bytes"]
            )
            self._baseline_files = census["unique_files"] - controls["files"] - native["files"]
            if self._baseline_charged < 0 or self._baseline_files < 0:
                raise IntegrityError("BOUNDED_CONTROL_ACCOUNTING_DRIFT")


class BoundedControlReplay(BoundedControlPublisher):
    """Fixed control read ledger; no bootstrap, process admission or writes."""

    def __init__(
        self,
        namespace: Path,
        *,
        authority: Path,
        expected_roster: tuple[str, ...],
        expected_authority_sha256: str,
        expected_reserve_sha256: str,
    ) -> None:
        from ai_service_v2.training.cost_reference_metadata_01 import MetadataBoundary

        for path in (namespace, authority):
            reject_reparse_path(path)
        self.namespace, self.authority = namespace.resolve(), authority
        self.directory = self.namespace / "bounded-controls"
        self.reserve_path = self.directory / "reserve.json"
        self.authority_sha256, self.reserve_sha256 = (
            expected_authority_sha256,
            expected_reserve_sha256,
        )
        if (
            any(
                type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)
                for digest in (expected_authority_sha256, expected_reserve_sha256)
            )
            or not 1 <= len(expected_roster) <= 1024
            or any(type(name) is not str or safe_name(name) != name for name in expected_roster)
            or len({name.casefold() for name in expected_roster}) != len(expected_roster)
        ):
            raise IntegrityError("BOUNDED_CONTROL_REPLAY_BINDING")
        allowed = {
            authority,
            self.reserve_path,
            *(self.namespace / name for name in expected_roster),
        }
        allowed.update(
            self.directory / f"{kind}-{index:04d}.json"
            for index in range(len(expected_roster))
            for kind in ("intent", "settled")
        )
        self._boundary = MetadataBoundary(
            {path: "FIXED_BOUND_CONTROL_BYTES_ONLY" for path in allowed},
            (self.namespace, authority.parent),
        )
        with self._boundary.enforce():
            if sha256_file(authority) != expected_authority_sha256:
                raise IntegrityError("BOUNDED_CONTROL_REPLAY_AUTHORITY_DRIFT")
            document = read_canonical_json(authority)
        self.storage_authority = copy.deepcopy(document)
        policy_controls = current_storage_policy_controls(document)
        from ai_service_v2.training.cost_closure_control_calibration_01 import (
            CURRENT_AUTHORITY_SCHEMA,
            current_calibration_control_bindings,
        )

        calibration_controls = (
            current_calibration_control_bindings(document)
            if document.get("schema_version") == CURRENT_AUTHORITY_SCHEMA
            else {}
        )
        self._boundary = MetadataBoundary(
            {
                **{path: "FIXED_BOUND_CONTROL_BYTES_ONLY" for path in allowed},
                **policy_controls,
                **calibration_controls,
            },
            (
                self.namespace,
                authority.parent,
                *(path.parent for path in policy_controls),
                *(path.parent for path in calibration_controls),
            ),
        )
        with self._boundary.enforce():
            if sha256_file(authority) != expected_authority_sha256:
                raise IntegrityError("BOUNDED_CONTROL_REPLAY_AUTHORITY_DRIFT")
            document = read_canonical_json(authority)
            self.policy = document["control_plane"]
            policy_schema, maximum_paths, maximum_reservation = _control_policy_limits(document)
            if (
                len(expected_roster) > maximum_paths
                or document.get("namespace") != str(namespace)
                or document.get("writer_policy") != policy_caps()
                or document.get("scientific_execution_authorized") is not False
                or type(self.policy) is not dict
                or set(self.policy)
                != {"schema_version", "paths", "reserved_bytes", "max_document_bytes", "scope"}
                or self.policy["schema_version"] != policy_schema
                or self.policy["paths"] != list(expected_roster)
                or self.policy["scope"] != "FIXED_CONTROL_ROSTER_NOT_ARBITRARY_JSON"
                or type(self.policy["reserved_bytes"]) is not int
                or not MIB <= self.policy["reserved_bytes"] <= maximum_reservation
                or type(self.policy["max_document_bytes"]) is not int
                or not 1 <= self.policy["max_document_bytes"] <= MIB
            ):
                raise IntegrityError("BOUNDED_CONTROL_REPLAY_POLICY")
            self.unit = size(document.get("allocation_unit_bytes"))
            if not 0 < self.unit <= MIB or self.unit & (self.unit - 1):
                raise IntegrityError("BOUNDED_CONTROL_REPLAY_ALLOCATION")
            self.roster = expected_roster
            self.snapshot()

    def _authenticate(self) -> None:
        raise IntegrityError("BOUNDED_CONTROL_REPLAY_READ_ONLY")

    def snapshot(self) -> dict[str, int]:
        with self._boundary.enforce():
            if sha256_file(self.authority) != self.authority_sha256:
                raise IntegrityError("BOUNDED_CONTROL_REPLAY_AUTHORITY_DRIFT")
            return super().snapshot()

    def report(self) -> dict[str, Any]:
        return {**self._boundary.report(), "scope": "BOUND_CONTROL_BYTES_ONLY_NOT_PAYLOAD_CUSTODY"}


class BoundedArtifactWriter:
    """Reservations serialize on an external byte lock, not an in-process lock.

    The caller must already hold the shared execution lane. This adapter checks
    the durable claim and admitted parent/worker descriptor on each mutation.
    It does not sandbox arbitrary libraries or certify their output paths.
    """

    def __init__(
        self,
        cache: Path,
        namespace: Path,
        *,
        authority: Path,
        guard: Path,
        owner: Path,
        storage_lane: Path,
        approved_aliases: Mapping[str, str] | None = None,
        admitted_owners: Mapping[Path, str] | None = None,
        admitted_runtime_identities: Mapping[Path, dict[str, Any]] | None = None,
        expected_owner_roster_sha256: str | None = None,
        control_publisher: BoundedControlPublisher | None = None,
        packet_id: str | None = None,
        admitted_packet_seals: Mapping[str, str] | None = None,
    ) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(namespace)
        for path in (cache, namespace, authority, guard, owner, storage_lane):
            reject_reparse_path(path)
        self.cache, self.namespace = cache.resolve(), namespace.resolve()
        self.authority, self.guard, self.owner = authority, guard, owner
        self.lane = storage_lane
        self.aliases = approved_aliases
        self.control_publisher = control_publisher
        if control_publisher is not None and (
            control_publisher.namespace != self.namespace
            or control_publisher.authority.resolve() != authority.resolve()
            or control_publisher.lane.resolve() != storage_lane.resolve()
        ):
            raise IntegrityError("BOUNDED_CONTROL_PUBLISHER_BINDING")
        if control_publisher is None and (self.namespace / "bounded-controls").exists():
            raise IntegrityError("BOUNDED_CONTROL_PUBLISHER_REQUIRED")
        self.allocation_unit = allocation_unit(self.cache)
        if (
            self.namespace == self.cache
            or not self.namespace.is_relative_to(self.cache)
            or not guard.resolve().is_relative_to(self.namespace)
            or not owner.resolve().is_relative_to(self.namespace)
            or storage_lane.resolve().is_relative_to(self.namespace)
            or not storage_lane.is_dir()
        ):
            raise IntegrityError("BOUNDED_NAMESPACE_OR_EXTERNAL_LANE")
        document, claim = read_canonical_json(authority), read_canonical_json(guard)
        self.storage_authority = copy.deepcopy(document)
        admitted_policy = document.get("writer_policy")
        _native_invocation_deadline(document, self.guard)
        self.binding = {
            "authority_sha256": sha256_file(authority),
            "guard_sha256": sha256_file(guard),
            "owner_sha256": sha256_file(owner),
        }
        self._configure_owners(
            admitted_owners, expected_owner_roster_sha256, admitted_runtime_identities
        )
        if (
            document.get("namespace") != str(namespace)
            or document.get("storage_mutex") != str(storage_lane / "lane.lock")
            or not isinstance(admitted_policy, dict)
            or canonical_json_bytes(admitted_policy) != canonical_json_bytes(policy_caps())
            or type(document.get("allocation_unit_bytes")) is not int
            or document.get("allocation_unit_bytes") != self.allocation_unit
            or document.get("scientific_execution_authorized") is not False
            or claim.get("namespace") != str(namespace)
            or claim.get("authority_sha256") != self.binding["authority_sha256"]
            or claim.get("automatic_retry") is not False
        ):
            raise IntegrityError("BOUNDED_AUTHORITY_OR_CLAIM")
        self.pid, self.thread = os.getpid(), threading.get_ident()
        self._actor_identity: dict[str, Any] | None = None
        self._owner_handles: list[Any] = []
        self._configure_score_storage(document)
        self._configure_input_storage(document)
        self._configure_top_k_storage(document)
        self._configure_evaluation_storage(document)
        self._configure_score_manifest_storage(document)
        self._configure_reference_manifest_storage(document)
        self._configure_deep_manifest_storage(document)
        self._configure_deep_receipt_storage(document)
        self._configure_reference_receipt_storage(document)
        self._configure_packet(document, packet_id, admitted_packet_seals)
        with serialized_storage_lane(self.lane):
            if self.packet_id is not None and self.packet_root.exists():
                raise IntegrityError("BOUNDED_PACKET_ALREADY_OPENED")
            self._ownership_boundary()
            self._packet_totals()
            self.directory.mkdir(parents=True, exist_ok=True)
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            actual, charged, files = self._occupancy()
            namespace_census = capacity_census(self.namespace)
            control_names = (
                set(control_publisher.roster) if control_publisher is not None else set()
            )
            bootstrap = {
                path
                for path in (self.guard, *self._owners)
                if path.relative_to(self.namespace).as_posix() not in control_names
            }
            bootstrap_bytes = sum(self._charge(path)[0] for path in bootstrap)
            if namespace_census[
                "charged_unique_bytes"
            ] != actual + bootstrap_bytes or namespace_census["unique_files"] != files + len(
                bootstrap
            ):
                raise IntegrityError("BOUNDED_NAMESPACE_ROSTER_UNCOVERED_WRITER")
            self._baseline_actual = census["charged_unique_bytes"] - actual
            self._baseline_files = census["unique_files"] - files
            self._baseline_charged = self._baseline_actual
            if self.packet_seals:
                first = next(iter(self.packet_seals))
                baseline = read_canonical_json(self.packet_root.parent / first / "seal.json")[
                    "baseline"
                ]
                if baseline != self._packet_baseline():
                    raise IntegrityError("BOUNDED_OCCUPANCY_DRIFT_BETWEEN_PACKETS")
            self._storage_admission(
                self._baseline_charged + charged + self._pending(),
                current_bytes=self._baseline_charged + charged,
                free_bytes=shutil.disk_usage(self.cache).free,
            )
            if self.packet_id is not None:
                self._write_ledger(self.packet_root / "open.json", self._packet_open())

    def _storage_admission(
        self, peak: object, *, current_bytes: object, free_bytes: object
    ) -> dict[str, Any]:
        return storage_admission_for_authority(
            peak,
            authority=read_canonical_json(self.authority),
            current_bytes=current_bytes,
            free_bytes=free_bytes,
        )

    def _configure_score_storage(self, document: dict[str, Any]) -> None:
        self.score_storage_policy: dict[str, Any] | None = None
        if "score_storage_policy" not in document:
            return
        policy = document["score_storage_policy"]
        if type(policy) is not dict or not {
            "chunk_rows",
            "columns",
            "source_manifest_sha256",
        }.issubset(policy):
            raise IntegrityError("BOUNDED_SCORE_STORAGE_POLICY")
        expected = score_reservation_policy(
            policy["chunk_rows"],
            policy["columns"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_SCORE_STORAGE_POLICY")
        self.score_storage_policy = expected

    def _configure_input_storage(self, document: dict[str, Any]) -> None:
        self.input_storage_policy: dict[str, Any] | None = None
        if "input_storage_policy" not in document:
            return
        policy = document["input_storage_policy"]
        if type(policy) is not dict or not {"packets", "source_inventory_sha256"}.issubset(policy):
            raise IntegrityError("BOUNDED_INPUT_STORAGE_POLICY")
        expected = input_reservation_policy(
            policy["packets"],
            allocation_unit_bytes=self.allocation_unit,
            source_inventory_sha256=policy["source_inventory_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_INPUT_STORAGE_POLICY")
        ledger = document.get("packet_ledger")
        if ledger is not None and (
            type(ledger) is not dict
            or type(ledger.get("packet_ids")) is not list
            or set(expected["packets"]) != set(ledger["packet_ids"])
        ):
            raise IntegrityError("BOUNDED_INPUT_PACKET_ROSTER")
        self.input_storage_policy = expected

    def _configure_top_k_storage(self, document: dict[str, Any]) -> None:
        self.top_k_storage_policy: dict[str, Any] | None = None
        if "top_k_storage_policy" not in document:
            return
        policy = document["top_k_storage_policy"]
        fields = {
            "schema_version",
            "operations",
            "user_ids",
            "candidate_item_ids",
            "cutoff",
            "allocation_unit_bytes",
            "source_manifest_sha256",
            "scope",
            "complete_transaction_proof",
            "reservation_credit_bytes",
        }
        if (
            type(policy) is not dict
            or set(policy) != fields
            or type(policy["operations"]) is not dict
        ):
            raise IntegrityError("BOUNDED_TOP_K_STORAGE_POLICY")
        paths: dict[str, str] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "path",
                "logical_bound_bytes",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_TOP_K_STORAGE_POLICY")
            paths[operation] = row["path"]
        expected = native_top_k_storage_policy(
            paths,
            user_ids=policy["user_ids"],
            candidate_item_ids=policy["candidate_item_ids"],
            cutoff=policy["cutoff"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_TOP_K_STORAGE_POLICY")
        self.top_k_storage_policy = expected

    def _top_k_file(self, operation_id: str, category: str, name: str) -> dict[str, Any] | None:
        policy = self.top_k_storage_policy
        if policy is None or Path(name).name.casefold() != "top_k.json":
            return None
        row = policy["operations"].get(operation_id)
        if row is None or category != "sidecars" or name != row["path"]:
            raise IntegrityError("BOUNDED_TOP_K_OUTPUT_ROSTER")
        return cast(dict[str, Any], row)

    def _configure_evaluation_storage(self, document: dict[str, Any]) -> None:
        self.evaluation_storage_policy: dict[str, Any] | None = None
        if "evaluation_storage_policy" not in document:
            return
        policy = document["evaluation_storage_policy"]
        fields = {
            "schema_version",
            "operations",
            "user_ids",
            "num_total_users",
            "candidate_count",
            "cutoff",
            "allocation_unit_bytes",
            "source_manifest_sha256",
            "numeric_token_bound_bytes",
            "serializer_binding",
            "scope",
            "complete_transaction_proof",
        }
        if (
            type(policy) is not dict
            or set(policy) != fields
            or type(policy["operations"]) is not dict
        ):
            raise IntegrityError("BOUNDED_EVALUATION_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "root",
                "identity",
                "files",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_EVALUATION_STORAGE_POLICY")
            specs[operation] = {"root": row["root"], "identity": row["identity"]}
        expected = native_evaluation_storage_policy(
            specs,
            user_ids=policy["user_ids"],
            num_total_users=policy["num_total_users"],
            candidate_count=policy["candidate_count"],
            cutoff=policy["cutoff"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_EVALUATION_STORAGE_POLICY")
        if self.top_k_storage_policy is not None and set(expected["operations"]) & set(
            self.top_k_storage_policy["operations"]
        ):
            raise IntegrityError("BOUNDED_EVALUATION_OPERATION_OVERLAP")
        self.evaluation_storage_policy = expected

    def _evaluation_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.evaluation_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _evaluation_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        if self.evaluation_storage_policy is None:
            return None
        row = self._evaluation_operation(operation_id)
        protected = Path(name).name.casefold() in {
            "per_user_metrics.json",
            "aggregate_metrics.json",
            "evaluation_receipt.json",
        }
        if row is None and not protected:
            return None
        if row is None or category != "sidecars" or name not in row["files"]:
            raise IntegrityError("BOUNDED_EVALUATION_OUTPUT_ROSTER")
        return cast(dict[str, Any], row["files"][name])

    def _configure_score_manifest_storage(self, document: dict[str, Any]) -> None:
        self.score_manifest_storage_policy: dict[str, Any] | None = None
        if "score_manifest_storage_policy" not in document:
            return
        policy = document["score_manifest_storage_policy"]
        fields = {
            "schema_version",
            "operations",
            "chunk_rows",
            "columns",
            "allocation_unit_bytes",
            "source_manifest_sha256",
            "serializer_sources",
            "scope",
            "complete_transaction_proof",
        }
        if (
            type(policy) is not dict
            or set(policy) != fields
            or type(policy["operations"]) is not dict
        ):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "path",
                "identity",
                "fixed_manifest",
                "chunk_roster",
                "logical_bound_bytes",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_SCORE_MANIFEST_STORAGE_POLICY")
            specs[operation] = {"path": row["path"], "identity": row["identity"]}
        expected = native_score_manifest_storage_policy(
            specs,
            chunk_rows=policy["chunk_rows"],
            columns=policy["columns"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_STORAGE_POLICY")
        if self.score_storage_policy is not None and (
            expected["chunk_rows"] != self.score_storage_policy["chunk_rows"]
            or expected["columns"] != self.score_storage_policy["columns"]
        ):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_GEOMETRY_BINDING")
        for other in (self.top_k_storage_policy, self.evaluation_storage_policy):
            if other is not None and set(other["operations"]) & set(expected["operations"]):
                raise IntegrityError("BOUNDED_SCORE_MANIFEST_OPERATION_OVERLAP")
        self.score_manifest_storage_policy = expected

    def _score_manifest_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.score_manifest_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _score_manifest_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        if self.score_manifest_storage_policy is None:
            return None
        row = self._score_manifest_operation(operation_id)
        if row is None and not name.casefold().endswith("/scores/manifest.json"):
            return None
        if row is None or category != "sidecars" or name != row["path"]:
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_OUTPUT_ROSTER")
        return row

    def _configure_reference_manifest_storage(self, document: dict[str, Any]) -> None:
        self.reference_manifest_storage_policy: dict[str, Any] | None = None
        if "reference_manifest_storage_policy" not in document:
            return
        policy = document["reference_manifest_storage_policy"]
        fields = {
            "schema_version",
            "operations",
            "allocation_unit_bytes",
            "source_manifest_sha256",
            "numeric_token_bound_bytes",
            "serializer_binding",
            "scope",
            "complete_transaction_proof",
        }
        if (
            type(policy) is not dict
            or set(policy) != fields
            or type(policy["operations"]) is not dict
        ):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "path",
                "identity",
                "fixed_manifest",
                "logical_bound_bytes",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_STORAGE_POLICY")
            specs[operation] = {"path": row["path"], "identity": row["identity"]}
        expected = native_reference_manifest_storage_policy(
            specs,
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_STORAGE_POLICY")
        for other in (
            self.top_k_storage_policy,
            self.evaluation_storage_policy,
            self.score_manifest_storage_policy,
        ):
            if other is not None and set(other["operations"]) & set(expected["operations"]):
                raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OPERATION_OVERLAP")
        self.reference_manifest_storage_policy = expected

    def _reference_manifest_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.reference_manifest_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _reference_manifest_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        if self.reference_manifest_storage_policy is None:
            return None
        row = self._reference_manifest_operation(operation_id)
        if row is None and self._deep_manifest_operation(operation_id) is not None:
            return None
        if row is None and not name.casefold().endswith("/checkpoint/manifest.json"):
            return None
        if row is None or category != "sidecars" or name != row["path"]:
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OUTPUT_ROSTER")
        return row

    def _configure_deep_manifest_storage(self, document: dict[str, Any]) -> None:
        self.deep_manifest_storage_policy: dict[str, Any] | None = None
        if "deep_manifest_storage_policy" not in document:
            return
        policy = document["deep_manifest_storage_policy"]
        if (
            type(policy) is not dict
            or set(policy)
            != {
                "schema_version",
                "operations",
                "allocation_unit_bytes",
                "source_manifest_sha256",
                "numeric_token_bound_bytes",
                "serializer_binding",
                "scope",
                "complete_transaction_proof",
            }
            or type(policy["operations"]) is not dict
        ):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "path",
                "identity",
                "fixed_manifest",
                "logical_bound_bytes",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_DEEP_MANIFEST_STORAGE_POLICY")
            specs[operation] = {"path": row["path"], "identity": row["identity"]}
        expected = native_deep_manifest_storage_policy(
            specs,
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(policy) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_STORAGE_POLICY")
        for other in (
            self.top_k_storage_policy,
            self.evaluation_storage_policy,
            self.score_manifest_storage_policy,
            self.reference_manifest_storage_policy,
        ):
            if other is not None and set(other["operations"]) & set(expected["operations"]):
                raise IntegrityError("BOUNDED_DEEP_MANIFEST_OPERATION_OVERLAP")
        if self.reference_manifest_storage_policy is not None and {
            row["path"].casefold()
            for row in self.reference_manifest_storage_policy["operations"].values()
        } & {row["path"].casefold() for row in expected["operations"].values()}:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_OVERLAP")
        self.deep_manifest_storage_policy = expected

    def _deep_manifest_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.deep_manifest_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _deep_manifest_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        if self.deep_manifest_storage_policy is None:
            return None
        row = self._deep_manifest_operation(operation_id)
        if row is None and self._reference_manifest_operation(operation_id) is not None:
            return None
        if row is None and not name.casefold().endswith("/checkpoint/manifest.json"):
            return None
        if row is None or category != "sidecars" or name != row["path"]:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_ROSTER")
        return row

    def _input_operation(self, operation_id: str, scope_id: str) -> dict[str, Any] | None:
        if self.input_storage_policy is None:
            return None
        rows = self.input_storage_policy["packets"].get(scope_id, [])
        for row in rows:
            if row["operation_id"] == operation_id:
                return cast(dict[str, Any], row)
        raise IntegrityError("BOUNDED_INPUT_OPERATION_UNADMITTED")

    def _configure_deep_receipt_storage(self, document: dict[str, Any]) -> None:
        self.deep_receipt_storage_policy: dict[str, Any] | None = None
        if "deep_receipt_storage_policy" not in document:
            return
        policy = document["deep_receipt_storage_policy"]
        if (
            type(policy) is not dict
            or set(policy)
            != {
                "schema_version",
                "operations",
                "top_k_storage_policy",
                "allocation_unit_bytes",
                "source_manifest_sha256",
                "numeric_token_bound_bytes",
                "serializer_binding",
                "scope",
                "complete_transaction_proof",
            }
            or type(policy["operations"]) is not dict
            or type(policy["top_k_storage_policy"]) is not dict
        ):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "root",
                "epoch",
                "example_count",
                "fixed_receipt",
                "files",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_DEEP_RECEIPT_STORAGE_POLICY")
            specs[operation] = {key: row[key] for key in ("root", "epoch", "example_count")}
        top_k = policy["top_k_storage_policy"]
        if not {"user_ids", "candidate_item_ids", "cutoff"}.issubset(top_k):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_STORAGE_POLICY")
        expected = native_deep_receipt_storage_policy(
            specs,
            user_ids=top_k["user_ids"],
            candidate_item_ids=top_k["candidate_item_ids"],
            cutoff=top_k["cutoff"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(expected) != canonical_json_bytes(policy):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_STORAGE_POLICY")
        for other in (
            self.evaluation_storage_policy,
            self.score_manifest_storage_policy,
            self.reference_manifest_storage_policy,
            self.deep_manifest_storage_policy,
        ):
            if other is not None and set(other["operations"]) & set(expected["operations"]):
                raise IntegrityError("BOUNDED_DEEP_RECEIPT_OPERATION_OVERLAP")
        admitted_top_k = expected["top_k_storage_policy"]
        if self.top_k_storage_policy is not None:
            existing = self.top_k_storage_policy
            if canonical_json_bytes(
                {key: value for key, value in existing.items() if key != "operations"}
            ) != canonical_json_bytes(
                {key: value for key, value in admitted_top_k.items() if key != "operations"}
            ):
                raise IntegrityError("BOUNDED_DEEP_RECEIPT_TOP_K_BINDING")
            for operation, row in admitted_top_k["operations"].items():
                if operation in existing["operations"] and existing["operations"][operation] != row:
                    raise IntegrityError("BOUNDED_DEEP_RECEIPT_TOP_K_BINDING")
                if any(
                    other != operation and old["path"].casefold() == row["path"].casefold()
                    for other, old in existing["operations"].items()
                ):
                    raise IntegrityError("BOUNDED_DEEP_RECEIPT_TOP_K_BINDING")
            admitted_top_k = {
                **existing,
                "operations": {**existing["operations"], **admitted_top_k["operations"]},
            }
        self.top_k_storage_policy = copy.deepcopy(admitted_top_k)
        self.deep_receipt_storage_policy = expected

    def _deep_receipt_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.deep_receipt_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _deep_receipt_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        row = self._deep_receipt_operation(operation_id)
        if row is None:
            return None
        if category != "sidecars" or name not in row["files"]:
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_OUTPUT_ROSTER")
        return cast(dict[str, Any], row["files"][name])

    def _configure_reference_receipt_storage(self, document: dict[str, Any]) -> None:
        self.reference_receipt_storage_policy: dict[str, Any] | None = None
        if "reference_receipt_storage_policy" not in document:
            return
        policy = document["reference_receipt_storage_policy"]
        if (
            type(policy) is not dict
            or set(policy)
            != {
                "schema_version",
                "namespace",
                "operations",
                "top_k_storage_policy",
                "allocation_unit_bytes",
                "source_manifest_sha256",
                "numeric_token_bound_bytes",
                "serializer_binding",
                "scope",
                "complete_transaction_proof",
            }
            or policy["namespace"] != str(self.namespace)
            or type(policy["operations"]) is not dict
            or type(policy["top_k_storage_policy"]) is not dict
        ):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_STORAGE_POLICY")
        specs: dict[str, dict[str, Any]] = {}
        for operation, row in policy["operations"].items():
            if type(row) is not dict or set(row) != {
                "root",
                "identity",
                "loss_components",
                "fixed_receipt",
                "files",
                "allocated_bound_bytes",
            }:
                raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_STORAGE_POLICY")
            specs[operation] = {key: row[key] for key in ("root", "identity", "loss_components")}
        top_k = policy["top_k_storage_policy"]
        if not {"user_ids", "candidate_item_ids", "cutoff"}.issubset(top_k):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_STORAGE_POLICY")
        expected = native_reference_receipt_storage_policy(
            specs,
            namespace=self.namespace,
            user_ids=top_k["user_ids"],
            candidate_item_ids=top_k["candidate_item_ids"],
            cutoff=top_k["cutoff"],
            allocation_unit_bytes=self.allocation_unit,
            source_manifest_sha256=policy["source_manifest_sha256"],
        )
        if canonical_json_bytes(expected) != canonical_json_bytes(policy):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_STORAGE_POLICY")
        for other in (
            self.evaluation_storage_policy,
            self.score_manifest_storage_policy,
            self.reference_manifest_storage_policy,
            self.deep_manifest_storage_policy,
            self.deep_receipt_storage_policy,
        ):
            if other is not None and set(other["operations"]) & set(expected["operations"]):
                raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OPERATION_OVERLAP")
        admitted_top_k = expected["top_k_storage_policy"]
        if self.top_k_storage_policy is not None:
            existing = self.top_k_storage_policy
            if canonical_json_bytes({k: v for k, v in existing.items() if k != "operations"}) != (
                canonical_json_bytes({k: v for k, v in admitted_top_k.items() if k != "operations"})
            ):
                raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_TOP_K_BINDING")
            for operation, row in admitted_top_k["operations"].items():
                if operation in existing["operations"] and existing["operations"][operation] != row:
                    raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_TOP_K_BINDING")
                if any(
                    other != operation and old["path"].casefold() == row["path"].casefold()
                    for other, old in existing["operations"].items()
                ):
                    raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_TOP_K_BINDING")
            admitted_top_k = {
                **existing,
                "operations": {**existing["operations"], **admitted_top_k["operations"]},
            }
        self.top_k_storage_policy = copy.deepcopy(admitted_top_k)
        self.reference_receipt_storage_policy = expected

    def _reference_receipt_operation(self, operation_id: str) -> dict[str, Any] | None:
        policy = self.reference_receipt_storage_policy
        return (
            None
            if policy is None
            else cast(dict[str, Any] | None, policy["operations"].get(operation_id))
        )

    def _reference_receipt_file(
        self, operation_id: str, category: str, name: str
    ) -> dict[str, Any] | None:
        row = self._reference_receipt_operation(operation_id)
        if row is None:
            policy = self.reference_receipt_storage_policy
            if policy is not None and any(
                name.casefold() == path.casefold()
                for operation in policy["operations"].values()
                for path in operation["files"]
            ):
                raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
            return None
        if category != "sidecars" or name not in row["files"]:
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
        return cast(dict[str, Any], row["files"][name])

    def _configure_packet(
        self,
        document: dict[str, Any],
        packet_id: str | None,
        admitted_seals: Mapping[str, str] | None,
    ) -> None:
        _validate_native_retention_contract(document)
        self.packet_id = packet_id
        policy = document.get("packet_ledger")
        self.packet_policy: dict[str, Any] = {}
        self.packet_seals = dict(admitted_seals or {})
        self._sealed_sha256: str | None = None
        self.packet_root = self.namespace / "bounded-ledger"
        self.directory = self.packet_root
        if policy is None:
            if packet_id is not None or admitted_seals is not None:
                raise IntegrityError("BOUNDED_PACKET_POLICY_REQUIRED")
            return
        if (
            type(policy) is not dict
            or set(policy) != {"schema_version", "packet_ids", "source_sha256"}
            or policy["schema_version"] != "mp2-cost-packet-ledger-policy/1.0"
            or type(policy["packet_ids"]) is not list
            or not 1 <= len(policy["packet_ids"]) <= 38
            or any(type(name) is not str for name in policy["packet_ids"])
            or len(set(policy["packet_ids"])) != len(policy["packet_ids"])
            or any(operation_name(name) != name for name in policy["packet_ids"])
            or type(policy["source_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", policy["source_sha256"])
            or packet_id is None
            or packet_id not in policy["packet_ids"]
        ):
            raise IntegrityError("BOUNDED_PACKET_POLICY_OR_ID")
        self.packet_policy = policy
        prefix = policy["packet_ids"][: policy["packet_ids"].index(packet_id)]
        if set(self.packet_seals) != set(prefix) or any(
            type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in self.packet_seals.values()
        ):
            raise IntegrityError("BOUNDED_PACKET_PREDECESSOR_ROSTER")
        self.packet_root = self.packet_root / "packets" / packet_id
        self.directory = self.packet_root / "operations"

    def _packet_open(self) -> dict[str, Any]:
        return {
            "schema_version": "mp2-cost-packet-open/1.0",
            "binding": self.binding,
            "packet_id": self.packet_id,
            "policy_sha256": canonical_json_sha256(self.packet_policy),
            "source_sha256": self.packet_policy["source_sha256"],
            "predecessor_seals": self.packet_seals,
            "baseline": self._packet_baseline(),
        }

    def _packet_baseline(self) -> dict[str, int]:
        return {"actual_bytes": self._baseline_actual, "files": self._baseline_files}

    def _packet_output(self, name: str) -> None:
        if getattr(self, "packet_id", None) is None:
            return
        if name.startswith(
            (f"packets/{self.packet_id}/", f"controls/retention/{self.packet_id}/")
        ) or name in {
            f"controls/packets/{self.packet_id}/bootstrap.json",
            f"controls/packets/{self.packet_id}/terminal.json",
        }:
            return
        parts = name.split("/")
        if (
            len(parts) == 4
            and parts[:2] == ["controls", "disposal"]
            and parts[3] in {"intent.json", "disposed.json"}
            and (self.directory / operation_name(parts[2]) / "reserve.json").is_file()
        ):
            return
        raise IntegrityError("BOUNDED_PACKET_PATH")

    def _packet_totals(self) -> dict[str, int]:
        """Only active operations and admitted seals participate in hot accounting."""
        cache = _PREDICATE_PASS.get()
        admission_sha256 = canonical_json_sha256(
            {
                "policy": self.packet_policy,
                "predecessor_seals": self.packet_seals,
                "current_seal_sha256": self._sealed_sha256,
                "terminal_successor_seals": getattr(self, "_replay_successor_seals", {}),
            }
        )
        key = (
            "packet-totals-" + self.owner_roster_sha256 + "-" + admission_sha256,
            self.packet_root,
        )
        if cache is not None and key in cache:
            return dict(cast(dict[str, int], cache[key]))
        result = self._read_packet_totals()
        if cache is not None:
            cache[key] = dict(result)
        return result

    def _read_packet_totals(self) -> dict[str, int]:
        totals = dict(actual_bytes=0, charged_bytes=0, files=0, control_charged_bytes=0)
        if self.packet_id is None:
            return totals
        root = self.namespace / "bounded-ledger"
        reject_reparse_path(root)
        if root.exists() and {path.name for path in root.iterdir()} != {"packets"}:
            raise IntegrityError("BOUNDED_PACKET_LAYOUT")
        packets = root / "packets"
        reject_reparse_path(packets)
        admitted = dict(self.packet_seals)
        if self._sealed_sha256 is not None:
            admitted[self.packet_id] = self._sealed_sha256
        admitted.update(getattr(self, "_replay_successor_seals", {}))
        present = {path.name for path in packets.iterdir()} if packets.exists() else set()
        if not set(admitted) <= present or not present <= set(admitted) | {self.packet_id}:
            raise IntegrityError("BOUNDED_PACKET_PREDECESSOR_OR_CONCURRENT")
        policy_ids = self.packet_policy["packet_ids"]
        dispatch = read_canonical_json(self.authority).get("native_packet_dispatch")
        current_terminals = (
            type(dispatch) is dict
            and dispatch.get("schema_version") == "mp2-benchmark-lane-dispatch/1.1"
        )
        baseline: dict[str, int] | None = None
        for packet, digest in admitted.items():
            path = packets / packet / "seal.json"
            reject_reparse_path(path)
            if not path.is_file() or sha256_file(path) != digest:
                raise IntegrityError("BOUNDED_PACKET_SEAL_DRIFT")
            seal = read_canonical_json(path)
            fields = {
                "schema_version",
                "binding",
                "packet_id",
                "policy_sha256",
                "source_sha256",
                "predecessor_seals",
                "open_sha256",
                "operation_roster_sha256",
                "operation_count",
                "retention_sha256",
                "artifact_manifests",
                "accounting",
                "payload_bytes_certified",
                "baseline",
            }
            expected_prefix = policy_ids[: policy_ids.index(packet)]
            accounting = seal.get("accounting")
            if (
                set(seal) != fields
                or seal["schema_version"] != "mp2-cost-packet-seal/1.0"
                or not self._binding_matches(seal["binding"])
                or seal["packet_id"] != packet
                or seal["policy_sha256"] != canonical_json_sha256(self.packet_policy)
                or seal["source_sha256"] != self.packet_policy["source_sha256"]
                or seal["predecessor_seals"] != {name: admitted[name] for name in expected_prefix}
                or seal["payload_bytes_certified"] is not False
                or type(seal["operation_count"]) is not int
                or seal["operation_count"] < 1
                or any(
                    type(seal[name]) is not str or not re.fullmatch(r"[0-9a-f]{64}", seal[name])
                    for name in ("open_sha256", "operation_roster_sha256", "retention_sha256")
                )
                or type(seal["artifact_manifests"]) is not dict
                or any(
                    type(name) is not str
                    or not (
                        name.startswith(f"packets/{packet}/")
                        or (
                            current_terminals and name == f"controls/packets/{packet}/terminal.json"
                        )
                    )
                    or safe_name(name) != name
                    or type(value) is not str
                    or not re.fullmatch(r"[0-9a-f]{64}", value)
                    for name, value in seal["artifact_manifests"].items()
                )
                or type(accounting) is not dict
                or set(accounting) != set(totals)
                or any(type(value) is not int or value < 0 for value in accounting.values())
                or accounting["charged_bytes"] < accounting["actual_bytes"]
                or accounting["control_charged_bytes"] > accounting["charged_bytes"]
                or accounting["files"] < 1 + 3 * seal["operation_count"]
                or type(seal["baseline"]) is not dict
                or set(seal["baseline"]) != {"actual_bytes", "files"}
                or any(type(value) is not int or value < 0 for value in seal["baseline"].values())
                or (baseline is not None and seal["baseline"] != baseline)
            ):
                raise IntegrityError("BOUNDED_PACKET_SEAL_BINDING")
            baseline = seal["baseline"]
            for name in totals:
                totals[name] += accounting[name]
            actual, charged = self._charge(path)
            totals["actual_bytes"] += actual
            totals["charged_bytes"] += charged
            totals["files"] += 1
            totals["control_charged_bytes"] += charged
        if self.packet_id not in admitted:
            path = self.packet_root / "open.json"
            reject_reparse_path(path)
            if (self.packet_root / "seal.json").exists():
                raise IntegrityError("BOUNDED_PACKET_SEALED")
            if path.exists():
                if read_canonical_json(path) != self._packet_open():
                    raise IntegrityError("BOUNDED_PACKET_OPEN_DRIFT")
                actual, charged = self._charge(path)
                totals["actual_bytes"] += actual
                totals["charged_bytes"] += charged
                totals["files"] += 1
                totals["control_charged_bytes"] += charged
        return totals

    def seal_packet(
        self, *, expected_operations: Mapping[str, str], artifact_manifests: Mapping[str, str]
    ) -> dict[str, Any]:
        """Reconcile custody before publishing the immutable packet boundary."""
        if self.packet_id is None:
            raise IntegrityError("BOUNDED_PACKET_POLICY_REQUIRED")
        with serialized_storage_lane(self.lane):
            self._ownership_boundary()
            operations = {
                directory.name: self._reservation(directory)["category"]
                for directory in self._operation_directories()
            }
            if not operations or operations != dict(expected_operations):
                raise IntegrityError("BOUNDED_PACKET_OPERATION_ROSTER")
            for operation in operations:
                self.replay(operation, certify_bytes=False)
            manifests = dict(artifact_manifests)
            declared = {
                path.relative_to(self.namespace).as_posix()
                for directory in self._operation_directories()
                for path in self._file_roster(directory)
            }
            for name, digest in manifests.items():
                if name not in declared or sha256_file(self.namespace / safe_name(name)) != digest:
                    raise IntegrityError("BOUNDED_PACKET_MANIFEST_BINDING")
            retentions = self._retentions(self.packet_id)
            self.reconcile()
            paths: set[Path] = {self.packet_root / "open.json"}
            controls = {self.packet_root / "open.json"}
            for directory in self._operation_directories():
                paths.update(self._directory_occupancy(directory)[2])
                controls.update(self._ledger_files(directory))
                if self._reservation(directory)["category"] == "execution_controls":
                    controls.update(self._file_roster(directory))
            seal = {
                **self._packet_open(),
                "schema_version": "mp2-cost-packet-seal/1.0",
                "open_sha256": sha256_file(self.packet_root / "open.json"),
                "operation_roster_sha256": canonical_json_sha256({"operations": operations}),
                "operation_count": len(operations),
                "retention_sha256": canonical_json_sha256(
                    {
                        "receipts": {
                            path.relative_to(self.namespace).as_posix(): sha256_file(path)
                            for path, _ in retentions
                        }
                    }
                ),
                "artifact_manifests": manifests,
                "accounting": {
                    "actual_bytes": sum(self._charge(path)[0] for path in paths),
                    "charged_bytes": sum(self._charge(path)[1] for path in paths),
                    "files": len(paths),
                    "control_charged_bytes": sum(self._charge(path)[1] for path in controls),
                },
                "payload_bytes_certified": False,
            }
            path = self.packet_root / "seal.json"
            self._write_ledger(path, seal)
            self._sealed_sha256 = sha256_file(path)
            return {"seal": seal, "seal_sha256": self._sealed_sha256}

    def open_successor_packet(self) -> BoundedArtifactWriter:
        """Transfer owned custody to the next durable packet after its predecessor seals."""
        if type(self) is not BoundedArtifactWriter:
            raise IntegrityError("BOUNDED_REPLAY_READ_ONLY")
        if os.getpid() != self.pid or threading.get_ident() != self.thread:
            raise IntegrityError("BOUNDED_FOREIGN_PROCESS_OR_THREAD")
        if self.packet_id is None or self._sealed_sha256 is None:
            raise IntegrityError("BOUNDED_PACKET_SUCCESSOR_REQUIRES_SEAL")
        with serialized_storage_lane(self.lane):
            for path, field in (
                (self.authority, "authority_sha256"),
                (self.guard, "guard_sha256"),
                (self.owner, "owner_sha256"),
            ):
                reject_reparse_path(path)
                if sha256_file(path) != self.binding[field]:
                    raise IntegrityError("BOUNDED_OWNERSHIP_BINDING_DRIFT")
            packet_ids = read_canonical_json(self.authority)["packet_ledger"]["packet_ids"]
            index = packet_ids.index(self.packet_id) + 1
            if index == len(packet_ids):
                raise IntegrityError("BOUNDED_PACKET_SUCCESSOR_EXHAUSTED")
            return BoundedArtifactWriter(
                self.cache,
                self.namespace,
                authority=self.authority,
                guard=self.guard,
                owner=self.owner,
                storage_lane=self.lane,
                approved_aliases=self.aliases,
                admitted_owners=self._owners,
                admitted_runtime_identities=self._runtime_identities or None,
                expected_owner_roster_sha256=self.owner_roster_sha256,
                control_publisher=self.control_publisher,
                packet_id=packet_ids[index],
                admitted_packet_seals={**self.packet_seals, self.packet_id: self._sealed_sha256},
            )

    def read_sealed_packet_terminal(self, packet_id: str) -> dict[str, Any]:
        """Read only the current terminal control authenticated by a predecessor seal."""
        if self.packet_id is None or packet_id not in self.packet_seals:
            raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_BINDING")
        with serialized_storage_lane(self.lane):
            self._ownership_boundary()
            dispatch = read_canonical_json(self.authority).get("native_packet_dispatch")
            if (
                type(dispatch) is not dict
                or dispatch.get("schema_version") != "mp2-benchmark-lane-dispatch/1.1"
            ):
                raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_TERMINAL_SCOPE")
            seal_path = self.packet_root.parent / packet_id / "seal.json"
            seal = read_canonical_json(seal_path)
            name = f"controls/packets/{packet_id}/terminal.json"
            expected = seal["artifact_manifests"].get(name)
            path = self.namespace / name
            reject_reparse_path(path)
            if (
                type(expected) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or not path.is_file()
                or path.stat().st_nlink != 1
                or path.stat().st_size > 8388608
                or sha256_file(path) != expected
            ):
                raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_TERMINAL_DRIFT")
            document = read_canonical_json(path)
            if (
                sha256_file(path) != expected
                or document.get("packet_id") != packet_id
                or not self._binding_matches(document.get("binding"))
                or document.get("scientific_execution_authorized") is not False
            ):
                raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_TERMINAL_BINDING")
            return document

    def verify_dependency_manifest(self, name: str, *, expected_sha256: str) -> None:
        """Admit bound predecessor metadata, never its unread payload bytes."""
        if self.packet_id is None:
            raise IntegrityError("BOUNDED_PACKET_POLICY_REQUIRED")
        name = safe_name(name)
        parts = name.split("/")
        if (
            len(parts) < 4
            or parts[0] != "packets"
            or parts[1] not in self.packet_seals
            or parts[-1] != "manifest.json"
            or type(expected_sha256) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        ):
            raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_BINDING")
        with serialized_storage_lane(self.lane):
            self._ownership_boundary()
            seal_path = self.packet_root.parent / parts[1] / "seal.json"
            seal = read_canonical_json(seal_path)
            if seal["artifact_manifests"].get(name) != expected_sha256:
                raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_MANIFEST_UNADMITTED")
            path = self.namespace / name
            reject_reparse_path(path)
            if (
                not path.is_file()
                or path.stat().st_nlink != 1
                or sha256_file(path) != expected_sha256
            ):
                raise IntegrityError("BOUNDED_PACKET_DEPENDENCY_MANIFEST_DRIFT")

    def _configure_owners(
        self,
        admitted: Mapping[Path, str] | None,
        expected_sha256: str | None,
        runtime_identities: Mapping[Path, dict[str, Any]] | None = None,
    ) -> None:
        """The route authenticates this fixed roster via parent admission/seal.

        This boundary checks its bytes and topology, not an unpublished caller's
        authority to dispatch. Previous workers need not remain alive to replay.
        """
        self._owners = (
            dict(admitted) if admitted is not None else {self.owner: self.binding["owner_sha256"]}
        )
        names: dict[str, str] = {}
        for path, digest in self._owners.items():
            reject_reparse_path(path)
            if (
                not path.resolve().is_relative_to(self.namespace)
                or not path.is_file()
                or path.stat().st_nlink != 1
                or type(digest) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                raise IntegrityError("BOUNDED_OWNER_ROSTER")
            name = safe_name(path.relative_to(self.namespace).as_posix())
            if name.casefold() in {key.casefold() for key in names}:
                raise IntegrityError("BOUNDED_OWNER_ROSTER")
            names[name] = digest
        self._runtime_identities = {
            path: dict(identity) for path, identity in (runtime_identities or {}).items()
        }
        roster: dict[str, Any] = {"owners": names}
        if runtime_identities is not None:
            if admitted is None or set(runtime_identities) != set(self._owners):
                raise IntegrityError("BOUNDED_OWNER_ROSTER_RUNTIME")
            for identity in runtime_identities.values():
                validate_identity(identity)
            roster["runtime_identities"] = {
                path.relative_to(self.namespace).as_posix(): identity
                for path, identity in runtime_identities.items()
            }
        self.owner_roster_sha256 = canonical_json_sha256(roster)
        if (
            not 1 <= len(names) <= 39
            or self._owners.get(self.owner) != self.binding["owner_sha256"]
            or (admitted is not None and expected_sha256 != self.owner_roster_sha256)
            or (admitted is None and expected_sha256 is not None)
        ):
            raise IntegrityError("BOUNDED_OWNER_ROSTER")
        self._verify_owners()
        anchor = read_canonical_json(self.owner)
        fields = {
            "schema_version",
            "spawned",
            "parent",
            "command",
            "launcher_executable",
            "base_executable",
            "telemetry_authority",
        }
        if set(anchor) != fields:
            raise IntegrityError("BOUNDED_OWNER_ROSTER_TOPOLOGY")
        descriptors = {}
        for path in self._owners:
            descriptor = read_canonical_json(path)
            if (
                set(descriptor) != fields
                or descriptor.get("schema_version") != "mp2-cost-role-process/1.0"
                or descriptor.get("launcher_executable") != anchor.get("launcher_executable")
                or descriptor.get("base_executable") != anchor.get("base_executable")
                or descriptor.get("telemetry_authority") != "UNAUTHENTICATED_RAW_BYTES_ONLY"
                or type(descriptor.get("command")) is not list
                or not descriptor["command"]
                or any(type(value) is not str for value in descriptor["command"])
                or str(Path(descriptor["command"][0]).resolve())
                not in {
                    descriptor["launcher_executable"],
                    descriptor["base_executable"],
                }
                or (
                    runtime_identities is None
                    and not (
                        descriptor["parent"] == anchor["parent"]
                        or descriptor["parent"] == anchor["spawned"]
                        or descriptor["spawned"] == anchor["parent"]
                    )
                )
            ):
                raise IntegrityError("BOUNDED_OWNER_ROSTER_TOPOLOGY")
            validate_identity(descriptor["spawned"])
            validate_identity(descriptor["parent"])
            descriptors[path] = descriptor
        if runtime_identities is not None:
            for path, descriptor in descriptors.items():
                runtime = runtime_identities[path]
                if runtime != descriptor["spawned"] and (
                    runtime["executable"] != descriptor["base_executable"]
                    or descriptor["spawned"]["executable"] != descriptor["launcher_executable"]
                    or runtime["pid"] == descriptor["spawned"]["pid"]
                ):
                    raise IntegrityError("BOUNDED_OWNER_ROSTER_RUNTIME")
            remaining_paths = set(descriptors) - {self.owner}
            connected = [anchor["parent"], anchor["spawned"], runtime_identities[self.owner]]
            while remaining_paths:
                found = {
                    path
                    for path in remaining_paths
                    if descriptors[path]["parent"] in connected
                    or descriptors[path]["spawned"] in connected
                    or runtime_identities[path] in connected
                }
                if not found:
                    raise IntegrityError("BOUNDED_OWNER_ROSTER_TOPOLOGY")
                for path in found:
                    connected.extend(
                        [
                            descriptors[path]["parent"],
                            descriptors[path]["spawned"],
                            runtime_identities[path],
                        ]
                    )
                remaining_paths -= found

    def _verify_owners(self) -> None:
        for path, digest in self._owners.items():
            _reject_reparse_path(path)
            if not path.is_file() or path.stat().st_nlink != 1 or _sha256_file(path) != digest:
                raise IntegrityError("BOUNDED_OWNER_ROSTER_DRIFT")

    def _binding_matches(self, value: Any) -> bool:
        return (
            type(value) is dict
            and set(value) == set(self.binding)
            and value["authority_sha256"] == self.binding["authority_sha256"]
            and value["guard_sha256"] == self.binding["guard_sha256"]
            and value["owner_sha256"] in self._owners.values()
        )

    def _file_roster(self, directory: Path) -> list[Path]:
        cache = _PREDICATE_PASS.get()
        key = ("file-roster-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return list(cast(list[Path], cache[key]))
        result = self._read_file_roster(directory)
        if cache is not None:
            cache[key] = list(result)
        return result

    def _read_file_roster(self, directory: Path) -> list[Path]:
        result = []
        names: set[str] = set()
        binding = self._reservation(directory)["binding"]
        for index, path in enumerate(sorted(directory.glob("file-*.json"))):
            reject_reparse_path(path)
            value = read_canonical_json(path)
            if (
                path.name != f"file-{index:06d}.json"
                or set(value) != {"schema_version", "binding", "operation_id", "path"}
                or value["schema_version"] != "mp2-cost-bounded-file-intent/1.0"
                or value["binding"] != binding
                or value["operation_id"] != directory.name
            ):
                raise IntegrityError("BOUNDED_FILE_INTENT_DRIFT")
            name = safe_name(value["path"])
            self._packet_output(name)
            payload = self.namespace / name
            reject_reparse_path(payload)
            if name.casefold() in names or not payload.resolve().is_relative_to(self.namespace):
                raise IntegrityError("BOUNDED_FILE_INTENT_DRIFT")
            names.add(name.casefold())
            result.append(payload)
        return result

    def _charge(self, path: Path) -> tuple[int, int]:
        cached = _ALLOCATION_PASS.get()
        if cached is not None and path in cached:
            return cached[path]
        reject_reparse_path(path)
        info = path.stat()
        if not path.is_file() or info.st_nlink != 1:
            raise IntegrityError("BOUNDED_FILE_ALLOCATION_DRIFT")
        actual = _allocated_size(path, info)
        unit = self.allocation_unit
        result = actual, max(actual, (info.st_size + unit - 1) // unit * unit)
        if cached is not None:
            cached[path] = result
        return result

    def _ledger_files(self, directory: Path) -> list[Path]:
        cache = _PREDICATE_PASS.get()
        key = ("ledger-roster-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return list(cast(list[Path], cache[key]))
        paths = list(directory.iterdir())
        if any(
            path.name not in {"reserve.json", "materialized.json", "settled.json"}
            and not re.fullmatch(r"file-[0-9]{6}\.json", path.name)
            for path in paths
        ):
            raise IntegrityError("BOUNDED_LEDGER_ROSTER")
        if cache is not None:
            cache[key] = list(paths)
        return paths

    def _directory_occupancy(self, directory: Path) -> tuple[int, int, frozenset[Path]]:
        cache = _PREDICATE_PASS.get()
        key = ("occupancy-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return cast(tuple[int, int, frozenset[Path]], cache[key])
        self._reservation(directory)
        known_lengths: dict[str, int] | None = None
        if (directory / "settled.json").exists():
            self.replay(directory.name, certify_bytes=False)
            known_lengths = {
                row["path"]: row["bytes"]
                for row in read_canonical_json(directory / "materialized.json")["artifacts"]
            }
        disposed = self._disposition(directory.name) is not None
        paths = set(self._ledger_files(directory))
        for payload in self._file_roster(directory):
            if disposed:
                continue
            if payload in paths:
                raise IntegrityError("BOUNDED_DUPLICATE_ALLOCATION")
            if known_lengths is not None and (
                not payload.is_file()
                or payload.stat().st_size
                != known_lengths[payload.relative_to(self.namespace).as_posix()]
            ):
                raise IntegrityError("BOUNDED_FILE_ALLOCATION_DRIFT")
            if payload.exists():
                paths.add(payload)
        values = [self._charge(path) for path in paths]
        result = sum(row[0] for row in values), sum(row[1] for row in values), frozenset(paths)
        if cache is not None:
            cache[key] = result
        return result

    def _operation_directories(self) -> tuple[Path, ...]:
        if getattr(self, "_sealed_sha256", None) is not None:
            return ()
        cache = _PREDICATE_PASS.get()
        key = ("operation-directories-" + self.owner_roster_sha256, self.directory)
        if cache is not None and key in cache:
            return cast(tuple[Path, ...], cache[key])
        result = tuple(self.directory.iterdir())
        if cache is not None:
            cache[key] = result
        return result

    def _occupancy(self) -> tuple[int, int, int]:
        """Reuse immutable operation allocations only inside the serialized lease."""
        paths: set[Path] = set()
        packet = (
            self._packet_totals()
            if hasattr(self, "packet_id")
            else {
                "actual_bytes": 0,
                "charged_bytes": 0,
                "files": 0,
            }
        )
        actual, charged = packet["actual_bytes"], packet["charged_bytes"]
        for directory in self._operation_directories():
            operation_actual, operation_charged, operation_paths = self._directory_occupancy(
                directory
            )
            if not paths.isdisjoint(operation_paths):
                raise IntegrityError("BOUNDED_DUPLICATE_ALLOCATION")
            paths.update(operation_paths)
            actual += operation_actual
            charged += operation_charged
        controls = (
            self.control_publisher.snapshot()
            if self.control_publisher is not None
            else {"actual_bytes": 0, "charged_bytes": 0, "files": 0}
        )
        return (
            actual + controls["actual_bytes"],
            charged + controls["charged_bytes"],
            len(paths) + controls["files"] + packet["files"],
        )

    def accounting(self) -> dict[str, int]:
        """Read declared native allocations; caller serializes the shared lane.

        Control-plane bytes are excluded so its reservation is charged once.
        This checks ledger predicates without restoring or certifying payload.
        """
        actual, charged, files = self._occupancy()
        pending = self._pending()
        if self.control_publisher is not None:
            controls = self.control_publisher.snapshot()
            actual -= controls["actual_bytes"]
            charged -= controls["charged_bytes"]
            files -= controls["files"]
            pending -= controls["pending_bytes"]
        return {
            "actual_bytes": actual,
            "charged_bytes": charged,
            "pending_bytes": pending,
            "files": files,
        }

    def observe_accounting_population(self) -> dict[str, Any]:
        """Observe a real fresh-lease scan; a small roster grants no scaling credit."""
        if _STORAGE_LEASE.get() is not None:
            raise IntegrityError("BOUNDED_POPULATION_OBSERVATION_REQUIRES_FRESH_LEASE")
        started = time.perf_counter_ns()
        with serialized_storage_lane(self.lane):
            self._ownership_boundary()
            accounting = self.accounting()
            operations = {
                directory.name: self._reservation(directory)["category"]
                for directory in self._operation_directories()
            }
            category_counts = {
                category: sum(value == category for value in operations.values())
                for category in policy_caps()
            }
        ended = time.perf_counter_ns()
        return {
            "schema_version": "mp2-cost-accounting-population-observation/1.0",
            "binding": dict(self.binding),
            "owner_roster_sha256": self.owner_roster_sha256,
            "operation_count": len(operations),
            "category_counts": category_counts,
            "operation_roster_sha256": canonical_json_sha256({"operations": operations}),
            "accounting": accounting,
            "boundaries_ns": [started, ended],
            "timer_clock": "PERF_COUNTER_NS_MONOTONIC_NOT_DURABLE_DEADLINE_CLOCK",
            "interval_scope": "FRESH_LEASE_WAIT_OWNERSHIP_ACCOUNTING_AND_ROSTER_SCAN",
            "lease_scope": "FRESH_SERIALIZED_STORAGE_LEASE",
            "payload_bytes_certified": False,
            "physical_timing_qualification": False,
            "scientific_execution_authorized": False,
        }

    def reconcile(self) -> dict[str, Any]:
        """Packet/terminal boundary check, not per-epoch re-inventory."""
        self._ownership_boundary()
        with serialized_storage_lane(self.lane):
            actual, charged, files = self._occupancy()
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            if (
                census["charged_unique_bytes"] != self._baseline_actual + actual
                or census["unique_files"] != self._baseline_files + files
            ):
                raise IntegrityError("BOUNDED_OCCUPANCY_DRIFT_UNCOVERED_WRITER")
            return self._storage_admission(
                self._baseline_charged + charged + self._pending(),
                current_bytes=self._baseline_charged + charged,
                free_bytes=shutil.disk_usage(self.cache).free,
            )

    def _write_ledger(self, path: Path, document: dict[str, Any]) -> None:
        """The ledger's own writes are capped before opening the output file."""
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(self.namespace)
        data = canonical_json_bytes(document) + b"\n"
        unit = self.allocation_unit
        growth = (len(data) + unit - 1) // unit * unit
        if len(data) > MIB:
            raise IntegrityError("BOUNDED_LEDGER_DOCUMENT_CAP")
        policy = read_canonical_json(self.authority).get("generated_payload_policy")
        if policy is not None and (
            not _generated_policy_matches(policy) or len(data) > policy["max_native_control_bytes"]
        ):
            raise IntegrityError("BOUNDED_GENERATED_LEDGER_CAP")
        if (
            self._scope_charge("execution_controls", "execution") + growth
            > policy_caps()["execution_controls"]
        ):
            raise IntegrityError("BOUNDED_EXECUTION_CONTROLS_CAP")
        _, current, _ = self._occupancy()
        self._storage_admission(
            self._baseline_charged + current + self._pending() + growth,
            current_bytes=self._baseline_charged + current,
            free_bytes=shutil.disk_usage(self.cache).free,
        )
        invalidate_materialization(path, operation_directory=path.parent)
        _native_invocation_deadline(read_canonical_json(self.authority), self.guard)
        write_exclusive_json(path, document)
        if read_canonical_json(path) != document:
            raise IntegrityError("BOUNDED_LEDGER_READBACK")

    def _invalidate_output(self, path: Path, *, operation_directory: Path) -> None:
        """Invalidate owned dependencies, not unrelated immutable lease records."""
        invalidate_materialization(path, operation_directory=operation_directory)
        cache = _PREDICATE_PASS.get()
        if cache is None:
            return
        name = path.relative_to(self.namespace).parts
        if len(name) >= 4 and name[:2] == ("controls", "retention"):
            root = self.namespace / "controls/retention" / name[2]
            for key in list(cache):
                if key[1] == root:
                    del cache[key]
        elif len(name) >= 4 and name[:2] == ("controls", "disposal"):
            target = self.directory / operation_name(name[2])
            for key in list(cache):
                if key[1] == target:
                    del cache[key]

    def _active(self) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(self.namespace)
        if (
            getattr(self, "packet_id", None) is not None
            and (self.packet_root / "seal.json").exists()
        ):
            raise IntegrityError("BOUNDED_PACKET_SEALED")
        if os.getpid() != self.pid or threading.get_ident() != self.thread:
            raise IntegrityError("BOUNDED_FOREIGN_PROCESS_OR_THREAD")
        for path, field in (
            (self.authority, "authority_sha256"),
            (self.guard, "guard_sha256"),
            (self.owner, "owner_sha256"),
        ):
            _reject_reparse_path(path)
            if _sha256_file(path) != self.binding[field]:
                raise IntegrityError("BOUNDED_OWNERSHIP_BINDING_DRIFT")
        _native_invocation_deadline(read_canonical_json(self.authority), self.guard)
        _validate_native_retention_contract(read_canonical_json(self.authority))
        self._verify_owners()
        if any(not process.is_running() for process in self._owner_handles):
            raise IntegrityError("BOUNDED_PROCESS_CUSTODY_DRIFT")
        if any(
            (self.namespace / name).exists()
            for name in ("completion.json", "failure.json", "terminal_failure.json")
        ):
            raise IntegrityError("BOUNDED_CLAIM_TERMINAL")
        if getattr(self, "packet_id", None) is not None:
            self._packet_totals()

    def _ownership_boundary(self) -> None:
        """Full native admission at boundaries; live PID leases for ZIP headers.

        Windows cannot exec into a new image in-place. Immutable descriptor
        bytes, PID/thread and creation-time-aware liveness remain checked on
        every growth, without repeated image/command lookups for each header.
        """
        import psutil

        self._active()
        cache = _PREDICATE_PASS.get()
        key = (f"native-owner-admission-{id(self)}", self.owner)
        if cache is not None and cache.get(key) is True and self._actor_identity is not None:
            return
        descriptor = read_canonical_json(self.owner)
        actual = resolve_owned_process(descriptor, descriptor["command"])
        if self._runtime_identities and actual != self._runtime_identities[self.owner]:
            raise IntegrityError("BOUNDED_OWNER_ROSTER_RUNTIME_DRIFT")
        if self._actor_identity is not None and actual != self._actor_identity:
            raise IntegrityError("BOUNDED_PROCESS_CUSTODY_DRIFT")
        identities = {
            identity["pid"]: identity
            for identity in (actual, descriptor["spawned"], descriptor["parent"])
        }
        handles = [psutil.Process(pid) for pid in identities]
        if any(process_identity(process) != identities[process.pid] for process in handles):
            raise IntegrityError("BOUNDED_PROCESS_CUSTODY_DRIFT")
        self._actor_identity, self._owner_handles = actual, handles
        if cache is not None:
            cache[key] = True

    def _reservation(self, directory: Path) -> dict[str, Any]:
        # Internal callers only read this validated lease-local document.
        cache = _PREDICATE_PASS.get()
        key = ("reservation-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return cast(dict[str, Any], cache[key])
        result = self._read_reservation(directory)
        if cache is not None:
            cache[key] = result
        return result

    def _read_reservation(self, directory: Path) -> dict[str, Any]:
        reject_reparse_path(directory)
        row = read_canonical_json(directory / "reserve.json")
        expected_fields = {
            "schema_version",
            "binding",
            "operation_id",
            "category",
            "reserved_bytes",
            "admission",
            "allocation_unit_bytes",
            "scope_id",
        }
        if (
            set(row) != expected_fields
            or row["schema_version"] != "mp2-cost-bounded-reservation/1.1"
            or not self._binding_matches(row["binding"])
            or row["operation_id"] != operation_name(directory.name)
            or row["category"] not in policy_caps()
            or not 0 < size(row["reserved_bytes"]) <= policy_caps()[row["category"]]
            or row["scope_id"] != operation_name(row["scope_id"])
            or (row["category"] == "execution_controls" and row["scope_id"] != "execution")
            or size(row["allocation_unit_bytes"]) != self.allocation_unit
        ):
            raise IntegrityError("BOUNDED_RESERVATION_DRIFT")
        if row["category"] == "scores" and self.score_storage_policy is not None:
            if row["reserved_bytes"] > self.score_storage_policy["allocated_bound_bytes"]:
                raise IntegrityError("BOUNDED_SCORE_RESERVATION_DRIFT")
        if row["category"] == "input":
            source = self._input_operation(row["operation_id"], row["scope_id"])
            if source is not None and row["reserved_bytes"] != (
                (source["bytes"] + self.allocation_unit - 1)
                // self.allocation_unit
                * self.allocation_unit
            ):
                raise IntegrityError("BOUNDED_INPUT_RESERVATION_DRIFT")
        if (
            self.top_k_storage_policy is not None
            and row["operation_id"] in self.top_k_storage_policy["operations"]
            and row["category"] != "sidecars"
        ):
            raise IntegrityError("BOUNDED_TOP_K_OUTPUT_ROSTER")
        evaluation = self._evaluation_operation(row["operation_id"])
        if evaluation is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != evaluation["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_EVALUATION_RESERVATION_DRIFT")
        score_manifest = self._score_manifest_operation(row["operation_id"])
        if score_manifest is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != score_manifest["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_RESERVATION_DRIFT")
        reference_manifest = self._reference_manifest_operation(row["operation_id"])
        if reference_manifest is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != reference_manifest["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_RESERVATION_DRIFT")
        deep_manifest = self._deep_manifest_operation(row["operation_id"])
        if deep_manifest is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != deep_manifest["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_RESERVATION_DRIFT")
        deep_receipt = self._deep_receipt_operation(row["operation_id"])
        if deep_receipt is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != deep_receipt["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_RESERVATION_DRIFT")
        reference_receipt = self._reference_receipt_operation(row["operation_id"])
        if reference_receipt is not None and (
            row["category"] != "sidecars"
            or row["reserved_bytes"] != reference_receipt["allocated_bound_bytes"]
        ):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_RESERVATION_DRIFT")
        admission = row["admission"]
        if canonical_json_bytes(admission) != canonical_json_bytes(
            self._storage_admission(
                admission["projected_peak_bytes"],
                current_bytes=admission["current_bytes"],
                free_bytes=admission["free_bytes"],
            )
        ):
            raise IntegrityError("BOUNDED_ADMISSION_DRIFT")
        return row

    def _pending(self) -> int:
        pending = (
            self.control_publisher.snapshot()["pending_bytes"]
            if self.control_publisher is not None
            else 0
        )
        for directory in self._operation_directories():
            pending += self._directory_pending(directory)
        return pending

    def _directory_pending(self, directory: Path) -> int:
        cache = _PREDICATE_PASS.get()
        key = ("pending-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return cast(int, cache[key])
        row = self._reservation(directory)
        if (directory / "settled.json").exists():
            self.replay(directory.name, certify_bytes=False)
            result = 0
        else:
            if any(
                p.name not in {"reserve.json", "materialized.json"}
                and not re.fullmatch(r"file-[0-9]{6}\.json", p.name)
                for p in self._ledger_files(directory)
            ):
                raise IntegrityError("BOUNDED_LEDGER_ROSTER")
            materialized = sum(
                self._charge(path)[1] for path in self._file_roster(directory) if path.exists()
            )
            if materialized > row["reserved_bytes"]:
                raise IntegrityError("BOUNDED_CAP_EXCEEDED")
            result = row["reserved_bytes"] - materialized
        if cache is not None:
            cache[key] = result
        return result

    def _directory_scope_charge(self, directory: Path) -> int:
        cache = _PREDICATE_PASS.get()
        key = ("scope-charge-" + self.owner_roster_sha256, directory)
        if cache is not None and key in cache:
            return cast(int, cache[key])
        if (directory / "settled.json").exists():
            self.replay(directory.name, certify_bytes=False)
            result = (
                sum(self._charge(path)[1] for path in self._file_roster(directory))
                if self._disposition(directory.name) is None
                else 0
            )
        else:
            result = self._reservation(directory)["reserved_bytes"]
        if cache is not None:
            cache[key] = result
        return result

    def _scope_charge(self, category: str, scope_id: str) -> int:
        charged = (
            sum(
                self._charge(p)[1]
                for d in self._operation_directories()
                for p in self._ledger_files(d)
            )
            if category == "execution_controls"
            else 0
        )
        if category == "execution_controls" and self.control_publisher is not None:
            charged += self.control_publisher.snapshot()["reserved_bytes"]
        if category == "execution_controls" and hasattr(self, "packet_id"):
            charged += self._packet_totals()["control_charged_bytes"]
        for directory in self._operation_directories():
            row = self._reservation(directory)
            if row["category"] != category or row["scope_id"] != scope_id:
                continue
            charged += self._directory_scope_charge(directory)
        if charged > policy_caps()[category]:
            raise IntegrityError("BOUNDED_SCOPE_CAP_EXCEEDED")
        return charged

    def _retentions(self, packet_id: str) -> list[tuple[Path, dict[str, Any]]]:
        packet_id = operation_name(packet_id)
        cache = _PREDICATE_PASS.get()
        key = (
            "retention-" + self.owner_roster_sha256,
            self.namespace / "controls/retention" / packet_id,
        )
        if cache is not None and key in cache:
            return cast(list[tuple[Path, dict[str, Any]]], cache[key])
        result = self._read_retentions(packet_id)
        if cache is not None:
            cache[key] = result
        return result

    def _read_retentions(self, packet_id: str) -> list[tuple[Path, dict[str, Any]]]:
        packet_id = operation_name(packet_id)
        root = self.namespace / "controls" / "retention" / packet_id
        reject_reparse_path(root)
        results: list[tuple[Path, dict[str, Any]]] = []
        for index, path in enumerate(sorted(root.glob("*.json")), 1):
            reject_reparse_path(path)
            value = read_canonical_json(path)
            if (
                path.name != f"{index:06d}.json"
                or set(value)
                != {"schema_version", "binding", "packet_id", "index", "roles", "selection_sha256"}
                or value["schema_version"] != "mp2-cost-bounded-retention/1.0"
                or not self._binding_matches(value["binding"])
                or value["packet_id"] != packet_id
                or type(value["index"]) is not int
                or value["index"] != index
                or type(value["selection_sha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", value["selection_sha256"])
                or type(value["roles"]) is not dict
                or set(value["roles"]) != {"best", "latest", "dependency", "accepted"}
            ):
                raise IntegrityError("BOUNDED_RETENTION_DRIFT")
            for role, operations in value["roles"].items():
                if (
                    type(operations) is not list
                    or any(type(operation) is not str for operation in operations)
                    or operations != sorted(set(operations))
                    or (
                        role in {"best", "latest"}
                        and not operations
                        and not self._generated_terminal_retention(value, packet_id)
                    )
                ):
                    raise IntegrityError("BOUNDED_RETENTION_DRIFT")
                for operation in operations:
                    operation_name(operation)
            if results and (
                results[-1][1]["binding"] != value["binding"]
                or any(
                    not set(results[-1][1]["roles"][role]) <= set(value["roles"][role])
                    for role in ("dependency", "accepted")
                )
            ):
                raise IntegrityError("BOUNDED_RETENTION_PROTECTED_ROLE_DROPPED")
            results.append((path, value))
        return results

    def _generated_terminal_retention(self, value: dict[str, Any], family: str) -> bool:
        authority = read_canonical_json(self.authority)
        geometry = authority.get("native_serialization_geometry")
        return (
            _generated_policy_matches(authority.get("generated_payload_policy"))
            and authority.get("scope") == "PROSPECTIVE_CPU_CONTROL_FILESYSTEM_ONLY"
            and type(geometry) is dict
            and geometry.get("scope") == "GENERATED_DISPOSABLE_NATIVE_SERIALIZATION_ONLY"
            and family in generated_calibration_policy()["families"]
            and value["index"] == 2
            and value["roles"] == {"best": [], "latest": [], "dependency": [], "accepted": []}
            and value["selection_sha256"]
            == canonical_json_sha256(
                {
                    "family": family,
                    "policy": generated_calibration_policy(),
                    "geometry": authority["native_serialization_geometry"],
                    "state": "GENERATED_SERIALIZATION_COMPLETE_NO_SCIENTIFIC_DEPENDENCY",
                }
            )
        )

    def retire_generated_calibration(self, family: str) -> dict[str, Any]:
        """Retire only the source-fixed latest generated bundle after old custody."""
        self._active()
        authority = read_canonical_json(self.authority)
        document = {
            "schema_version": "mp2-cost-bounded-retention/1.0",
            "binding": self.binding,
            "packet_id": family,
            "index": 2,
            "roles": {"best": [], "latest": [], "dependency": [], "accepted": []},
            "selection_sha256": canonical_json_sha256(
                {
                    "family": family,
                    "policy": generated_calibration_policy(),
                    "geometry": authority.get("native_serialization_geometry"),
                    "state": "GENERATED_SERIALIZATION_COMPLETE_NO_SCIENTIFIC_DEPENDENCY",
                }
            ),
        }
        if not self._generated_terminal_retention(document, family):
            raise IntegrityError("BOUNDED_GENERATED_RETIREMENT_AUTHORITY")
        prior = self._retentions(family)
        latest = sorted([f"{family}-latest-scores", f"{family}-latest-checkpoint"])
        if (
            len(prior) != 1
            or prior[0][1]["binding"] != self.binding
            or prior[0][1]["roles"]
            != {"best": latest, "latest": latest, "dependency": [], "accepted": []}
        ):
            raise IntegrityError("BOUNDED_GENERATED_RETIREMENT_CUSTODY")
        for kind in ("scores", "checkpoint"):
            old = self.replay(f"{family}-old-{kind}")
            if old["state"] != "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED":
                raise IntegrityError("BOUNDED_GENERATED_RETIREMENT_CUSTODY")
            rows = self._raw_packet_rows(family, f"{family}-latest-{kind}")
            geometry = authority["native_serialization_geometry"]
            expected_paths = (
                [
                    f"packets/{family}/latest/scores/scores-{index:05d}.npy"
                    for index in range(len(geometry["chunk_rows"]))
                ]
                if kind == "scores"
                else [f"packets/{family}/latest/checkpoint/checkpoint.pt"]
            )
            if [row["path"] for row in rows] != expected_paths:
                raise IntegrityError("BOUNDED_GENERATED_RETIREMENT_PATH")
        operation = f"retain-{sha256_file(self.guard)[:16]}-{family}-2"
        with self.transaction(operation, "execution_controls") as transaction:
            with transaction.open(f"controls/retention/{family}/000002.json") as stream:
                stream.write(canonical_json_bytes(document) + b"\n")
        if self._retentions(family)[-1][1] != document:
            raise IntegrityError("BOUNDED_GENERATED_RETIREMENT_READBACK")
        self.dispose(family, latest)
        return document

    def _raw_packet_rows(self, packet_id: str, operation_id: str) -> list[dict[str, Any]]:
        self.replay(operation_id)
        directory = self.directory / operation_name(operation_id)
        row = self._reservation(directory)
        artifacts = read_canonical_json(directory / "materialized.json")["artifacts"]
        if (
            row["category"] not in {"scores", "checkpoint"}
            or row["binding"] != self.binding
            or self._disposition(operation_id) is not None
            or not artifacts
            or any(
                not value["path"].startswith(f"packets/{packet_id}/")
                or Path(value["path"]).suffix != (".npy" if row["category"] == "scores" else ".pt")
                for value in artifacts
            )
        ):
            raise IntegrityError("BOUNDED_DISPOSAL_UNOWNED_OR_NONRAW")
        return artifacts  # type: ignore[no-any-return]

    def retain(
        self, packet_id: str, *, roles: dict[str, list[str]], selection_sha256: str
    ) -> dict[str, Any]:
        with serialized_storage_lane(self.lane):
            return self._retain_in_lane(packet_id, roles=roles, selection_sha256=selection_sha256)

    def _retain_in_lane(
        self, packet_id: str, *, roles: dict[str, list[str]], selection_sha256: str
    ) -> dict[str, Any]:
        self._active()
        packet_id = operation_name(packet_id)
        if (
            set(roles) != {"best", "latest", "dependency", "accepted"}
            or type(selection_sha256) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", selection_sha256)
            or any(
                type(operations) is not list
                or any(type(operation) is not str for operation in operations)
                or len(operations) != len(set(operations))
                or (role in {"best", "latest"} and not operations)
                for role, operations in roles.items()
            )
        ):
            raise IntegrityError("BOUNDED_RETENTION_SCHEMA")
        previous = self._retentions(packet_id)
        if previous and any(
            not set(previous[-1][1]["roles"][role]) <= set(roles[role])
            for role in ("dependency", "accepted")
        ):
            raise IntegrityError("BOUNDED_RETENTION_PROTECTED_ROLE_DROPPED")
        for operations in roles.values():
            for operation in operations:
                self._raw_packet_rows(packet_id, operation)
        index = len(previous) + 1
        document = {
            "schema_version": "mp2-cost-bounded-retention/1.0",
            "binding": self.binding,
            "packet_id": packet_id,
            "index": index,
            "roles": {role: sorted(operations) for role, operations in roles.items()},
            "selection_sha256": selection_sha256,
        }
        operation = f"retain-{sha256_file(self.guard)[:16]}-{packet_id}-{index}"
        with self.transaction(operation, "execution_controls") as transaction:
            with transaction.open(f"controls/retention/{packet_id}/{index:06d}.json") as stream:
                stream.write(canonical_json_bytes(document) + b"\n")
        if self._retentions(packet_id)[-1][1] != document:
            raise IntegrityError("BOUNDED_RETENTION_READBACK")
        return document

    def _disposition(self, operation_id: str) -> dict[str, Any] | None:
        operation_id = operation_name(operation_id)
        cache = _PREDICATE_PASS.get()
        key = ("disposition-" + self.owner_roster_sha256, self.directory / operation_id)
        if cache is not None and key in cache:
            return cast(dict[str, Any] | None, copy.deepcopy(cache[key]))
        result = self._read_disposition(operation_id)
        if cache is not None:
            cache[key] = result
        return result

    def _read_disposition(self, operation_id: str) -> dict[str, Any] | None:
        operation_id = operation_name(operation_id)
        root = self.namespace / "controls" / "disposal" / operation_id
        intent_path, disposed_path = root / "intent.json", root / "disposed.json"
        for path in (root, intent_path, disposed_path):
            reject_reparse_path(path)
        if not any(path.exists() and path.stat().st_size for path in (intent_path, disposed_path)):
            return None
        if not all(path.is_file() and path.stat().st_size for path in (intent_path, disposed_path)):
            raise IntegrityError("BOUNDED_PARTIAL_DISPOSAL_IN_DOUBT")
        intent, disposed = read_canonical_json(intent_path), read_canonical_json(disposed_path)
        directory = self.directory / operation_id
        materialized = read_canonical_json(directory / "materialized.json")
        if (
            set(intent)
            != {
                "schema_version",
                "binding",
                "operation_id",
                "packet_id",
                "retention_sha256",
                "settlement_sha256",
                "materialization_sha256",
                "artifacts",
            }
            or intent["schema_version"] != "mp2-cost-bounded-disposal-intent/1.0"
            or intent["binding"] != self._reservation(directory)["binding"]
            or intent["operation_id"] != operation_id
            or intent["settlement_sha256"] != sha256_file(directory / "settled.json")
            or intent["materialization_sha256"] != sha256_file(directory / "materialized.json")
            or intent["artifacts"] != materialized["artifacts"]
        ):
            raise IntegrityError("BOUNDED_DISPOSAL_DRIFT")
        retentions = self._retentions(intent["packet_id"])
        matches = [
            value for path, value in retentions if sha256_file(path) == intent["retention_sha256"]
        ]
        if (
            len(matches) != 1
            or matches[0]["binding"] != intent["binding"]
            or any(operation_id in operations for operations in matches[0]["roles"].values())
            or self._reservation(directory)["category"] not in {"scores", "checkpoint"}
            or any(
                not row["path"].startswith(f"packets/{intent['packet_id']}/")
                or (self.namespace / safe_name(row["path"])).exists()
                for row in intent["artifacts"]
            )
        ):
            raise IntegrityError("BOUNDED_DISPOSAL_RETENTION_DRIFT")
        expected = {
            "schema_version": "mp2-cost-bounded-disposal/1.0",
            "binding": intent["binding"],
            "state": "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED",
            "intent_sha256": sha256_file(intent_path),
            "raw_bytes_currently_certified": False,
        }
        if canonical_json_bytes(disposed) != canonical_json_bytes(expected):
            raise IntegrityError("BOUNDED_DISPOSAL_DRIFT")
        return disposed

    def dispose(self, packet_id: str, operation_ids: list[str]) -> None:
        with serialized_storage_lane(self.lane):
            self._dispose_in_lane(packet_id, operation_ids)

    def _dispose_in_lane(self, packet_id: str, operation_ids: list[str]) -> None:
        self._active()
        packet_id = operation_name(packet_id)
        if (
            not operation_ids
            or len(operation_ids) > 4
            or len(set(operation_ids)) != len(operation_ids)
        ):
            raise IntegrityError("BOUNDED_DISPOSAL_ROSTER")
        retentions = self._retentions(packet_id)
        if not retentions:
            raise IntegrityError("BOUNDED_DISPOSAL_RETENTION_REQUIRED")
        retention_path, retention = retentions[-1]
        if any(
            operation in operations
            for operation in operation_ids
            for operations in retention["roles"].values()
        ):
            raise IntegrityError("BOUNDED_RETAINED_PAYLOAD")
        rows = {
            operation: self._raw_packet_rows(packet_id, operation) for operation in operation_ids
        }
        for category in ("scores", "checkpoint"):
            if (
                sum(
                    self._reservation(self.directory / operation)["category"] == category
                    for operation in operation_ids
                )
                > 2
            ):
                raise IntegrityError("BOUNDED_DISPOSAL_MORE_THAN_TWO_BUNDLES")
        for operation, artifacts in rows.items():
            directory = self.directory / operation
            root = f"controls/disposal/{operation}"
            intent = {
                "schema_version": "mp2-cost-bounded-disposal-intent/1.0",
                "binding": self.binding,
                "operation_id": operation,
                "packet_id": packet_id,
                "retention_sha256": sha256_file(retention_path),
                "settlement_sha256": sha256_file(directory / "settled.json"),
                "materialization_sha256": sha256_file(directory / "materialized.json"),
                "artifacts": artifacts,
            }
            with self.transaction(f"dispose-{operation}", "execution_controls") as transaction:
                # Both intents are declared before disposal becomes in-doubt.
                with (
                    transaction.open(f"{root}/intent.json") as intent_stream,
                    transaction.open(f"{root}/disposed.json") as disposed_stream,
                ):
                    intent_stream.write(canonical_json_bytes(intent) + b"\n")
                    intent_stream.close()
                    if read_canonical_json(self.namespace / root / "intent.json") != intent:
                        raise IntegrityError("BOUNDED_DISPOSAL_INTENT_READBACK")
                    for row in artifacts:
                        self._active()
                        path = self.namespace / safe_name(row["path"])
                        reject_reparse_path(path)
                        if path.stat().st_nlink != 1 or sha256_file(path) != row["sha256"]:
                            raise IntegrityError("BOUNDED_DISPOSAL_TARGET_DRIFT")
                        path.unlink()
                        self._invalidate_output(path, operation_directory=directory)
                        if path.exists():
                            raise IntegrityError("BOUNDED_DISPOSAL_READBACK")
                    disposed_stream.write(
                        canonical_json_bytes(
                            {
                                "schema_version": "mp2-cost-bounded-disposal/1.0",
                                "binding": self.binding,
                                "state": "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED",
                                "intent_sha256": sha256_file(self.namespace / root / "intent.json"),
                                "raw_bytes_currently_certified": False,
                            }
                        )
                        + b"\n"
                    )
            self.replay(operation, certify_bytes=False)

    @contextmanager
    def transaction(
        self, operation_id: str, category: str, *, scope_id: str | None = None
    ) -> Iterator[BoundedTransaction]:
        self._active()
        # Synchronous log streams live for the packet. Their individual growth
        # is serialized; native bundles hold the lease through custody settlement.
        if category == "auxiliary":
            with self._transaction_in_lane(
                operation_id, category, scope_id=scope_id
            ) as transaction:
                yield transaction
        else:
            with (
                serialized_storage_lane(self.lane),
                self._transaction_in_lane(operation_id, category, scope_id=scope_id) as transaction,
            ):
                yield transaction

    @contextmanager
    def _transaction_in_lane(
        self, operation_id: str, category: str, *, scope_id: str | None
    ) -> Iterator[BoundedTransaction]:
        self._active()
        operation_name(operation_id)
        if category not in policy_caps():
            raise IntegrityError("BOUNDED_WRITER_CATEGORY_UNCOVERED")
        if self.packet_id is not None and category in {"input", "auxiliary"}:
            if scope_id not in {None, self.packet_id}:
                raise IntegrityError("BOUNDED_PACKET_SCOPE")
            scope_id = self.packet_id
        if category == "execution_controls":
            if scope_id not in {None, "execution"}:
                raise IntegrityError("BOUNDED_EXECUTION_CONTROLS_SCOPE")
            scope_id = "execution"
        else:
            scope_id = operation_name(scope_id if scope_id is not None else operation_id)
        directory = self.directory / operation_id
        reject_reparse_path(directory)
        with serialized_storage_lane(self.lane):
            self._ownership_boundary()
            if directory.exists():
                raise IntegrityError("BOUNDED_OPERATION_ALREADY_RESERVED")
            pending = self._pending()
            _, allocated, _ = self._occupancy()
            current = self._baseline_charged + allocated
            amount = policy_caps()[category] - self._scope_charge(category, scope_id)
            evaluation = self._evaluation_operation(operation_id)
            if evaluation is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_EVALUATION_OUTPUT_ROSTER")
                if amount < evaluation["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_EVALUATION_SHARED_SCOPE_EXHAUSTED")
                amount = evaluation["allocated_bound_bytes"]
            score_manifest = self._score_manifest_operation(operation_id)
            if score_manifest is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_SCORE_MANIFEST_OUTPUT_ROSTER")
                if amount < score_manifest["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_SCORE_MANIFEST_SHARED_SCOPE_EXHAUSTED")
                amount = score_manifest["allocated_bound_bytes"]
            reference_manifest = self._reference_manifest_operation(operation_id)
            if reference_manifest is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OUTPUT_ROSTER")
                if amount < reference_manifest["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_SHARED_SCOPE_EXHAUSTED")
                amount = reference_manifest["allocated_bound_bytes"]
            deep_manifest = self._deep_manifest_operation(operation_id)
            if deep_manifest is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_ROSTER")
                if amount < deep_manifest["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_DEEP_MANIFEST_SHARED_SCOPE_EXHAUSTED")
                amount = deep_manifest["allocated_bound_bytes"]
            deep_receipt = self._deep_receipt_operation(operation_id)
            if deep_receipt is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_DEEP_RECEIPT_OUTPUT_ROSTER")
                if amount < deep_receipt["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_DEEP_RECEIPT_SHARED_SCOPE_EXHAUSTED")
                amount = deep_receipt["allocated_bound_bytes"]
            reference_receipt = self._reference_receipt_operation(operation_id)
            if reference_receipt is not None:
                if category != "sidecars":
                    raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
                if amount < reference_receipt["allocated_bound_bytes"]:
                    raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_SHARED_SCOPE_EXHAUSTED")
                amount = reference_receipt["allocated_bound_bytes"]
            if category == "scores" and self.score_storage_policy is not None:
                amount = min(
                    amount,
                    self.score_storage_policy["allocated_bound_bytes"]
                    - self._scope_charge(category, scope_id),
                )
            if category == "input":
                source = self._input_operation(operation_id, scope_id)
                if source is not None:
                    amount = (
                        (source["bytes"] + self.allocation_unit - 1)
                        // self.allocation_unit
                        * self.allocation_unit
                    )
                    policy = self.input_storage_policy
                    if policy is None:
                        raise IntegrityError("BOUNDED_INPUT_STORAGE_POLICY")
                    if (
                        self._scope_charge(category, scope_id) + amount
                        > policy["packet_allocated_bounds"][scope_id]
                    ):
                        raise IntegrityError("BOUNDED_INPUT_SCOPE_EXHAUSTED")
            if category == "execution_controls":
                amount = min(amount, MIB)
            if amount <= 0:
                raise IntegrityError("BOUNDED_SCOPE_CAP_EXHAUSTED")
            admission = self._storage_admission(
                current + pending + amount,
                current_bytes=current,
                free_bytes=shutil.disk_usage(self.cache).free,
            )
            # First reservation has no directory record yet. Check the bytes
            # against the admission before publishing it, without recursive accounting.
            reserve = {
                "schema_version": "mp2-cost-bounded-reservation/1.1",
                "binding": self.binding,
                "operation_id": operation_id,
                "category": category,
                "scope_id": scope_id,
                "reserved_bytes": amount,
                "admission": admission,
                "allocation_unit_bytes": self.allocation_unit,
            }
            data = canonical_json_bytes(reserve) + b"\n"
            generated_policy = read_canonical_json(self.authority).get("generated_payload_policy")
            if generated_policy is not None and (
                not _generated_policy_matches(generated_policy)
                or len(data) > generated_policy["max_native_control_bytes"]
            ):
                raise IntegrityError("BOUNDED_GENERATED_LEDGER_CAP")
            growth = (
                (len(data) + self.allocation_unit - 1)
                // self.allocation_unit
                * self.allocation_unit
            )
            control_charge = self._scope_charge("execution_controls", "execution")
            if (
                control_charge + growth + (amount if category == "execution_controls" else 0)
                > policy_caps()["execution_controls"]
            ):
                raise IntegrityError("BOUNDED_EXECUTION_CONTROLS_CAP")
            self._storage_admission(
                current + pending + amount + growth,
                current_bytes=current,
                free_bytes=shutil.disk_usage(self.cache).free,
            )
            invalidate_materialization(directory, operation_directory=self.directory)
            directory.mkdir()
            write_exclusive_json(
                directory / "reserve.json",
                reserve,
            )
            if read_canonical_json(directory / "reserve.json") != reserve:
                raise IntegrityError("BOUNDED_RESERVATION_READBACK")
        transaction = BoundedTransaction(self, directory, amount)
        try:
            yield transaction
            transaction.settle()
        finally:
            transaction.close()
            # Partial bytes plus the unmaterialized balance retain the reservation.

    def replay(self, operation_id: str, *, certify_bytes: bool = True) -> dict[str, Any]:
        operation_id = operation_name(operation_id)
        cache = _PREDICATE_PASS.get() if not certify_bytes else None
        key = ("settlement-" + self.owner_roster_sha256, self.directory / operation_id)
        if cache is not None and key in cache:
            return cast(dict[str, Any], copy.deepcopy(cache[key]))
        result = self._replay_operation(operation_id, certify_bytes=certify_bytes)
        if cache is not None:
            cache[key] = result
        return result

    def _replay_operation(self, operation_id: str, *, certify_bytes: bool) -> dict[str, Any]:
        self._verify_owners()
        directory = self.directory / operation_name(operation_id)
        row = self._reservation(directory)
        if not (directory / "settled.json").exists():
            raise IntegrityError("BOUNDED_PARTIAL_RESERVATION_IN_DOUBT")
        disposed = self._disposition(operation_id)
        if {
            p.name
            for p in self._ledger_files(directory)
            if not re.fullmatch(r"file-[0-9]{6}\.json", p.name)
        } != {
            "reserve.json",
            "materialized.json",
            "settled.json",
        }:
            raise IntegrityError("BOUNDED_LEDGER_ROSTER")
        materialized = read_canonical_json(directory / "materialized.json")
        settled = read_canonical_json(directory / "settled.json")
        if (
            set(materialized) != {"schema_version", "reservation_sha256", "artifacts"}
            or materialized["schema_version"] != "mp2-cost-bounded-materialization/1.0"
            or materialized["reservation_sha256"] != sha256_file(directory / "reserve.json")
            or not isinstance(materialized["artifacts"], list)
            or not materialized["artifacts"]
        ):
            raise IntegrityError("BOUNDED_MATERIALIZATION_DRIFT")
        names: set[str] = set()
        logical = 0
        score_manifest = self._score_manifest_operation(operation_id)
        if score_manifest is not None and (
            len(materialized["artifacts"]) != 1
            or type(materialized["artifacts"][0]) is not dict
            or materialized["artifacts"][0].get("path") != score_manifest["path"]
        ):
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_OUTPUT_ROSTER")
        evaluation = self._evaluation_operation(operation_id)
        if evaluation is not None and {
            artifact.get("path") for artifact in materialized["artifacts"] if type(artifact) is dict
        } != set(evaluation["files"]):
            raise IntegrityError("BOUNDED_EVALUATION_OUTPUT_ROSTER")
        deep_receipt = self._deep_receipt_operation(operation_id)
        if deep_receipt is not None and {
            artifact.get("path") for artifact in materialized["artifacts"] if type(artifact) is dict
        } != set(deep_receipt["files"]):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_OUTPUT_ROSTER")
        reference_receipt = self._reference_receipt_operation(operation_id)
        if reference_receipt is not None and {
            artifact.get("path") for artifact in materialized["artifacts"] if type(artifact) is dict
        } != set(reference_receipt["files"]):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
        reference_manifest = self._reference_manifest_operation(operation_id)
        if reference_manifest is not None and (
            len(materialized["artifacts"]) != 1
            or type(materialized["artifacts"][0]) is not dict
            or materialized["artifacts"][0].get("path") != reference_manifest["path"]
        ):
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OUTPUT_ROSTER")
        deep_manifest = self._deep_manifest_operation(operation_id)
        if deep_manifest is not None and (
            len(materialized["artifacts"]) != 1
            or type(materialized["artifacts"][0]) is not dict
            or materialized["artifacts"][0].get("path") != deep_manifest["path"]
        ):
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_ROSTER")
        top_k = (
            self.top_k_storage_policy["operations"].get(operation_id)
            if self.top_k_storage_policy is not None
            else None
        )
        if top_k is not None and not any(
            type(artifact) is dict and artifact.get("path") == top_k["path"]
            for artifact in materialized["artifacts"]
        ):
            raise IntegrityError("BOUNDED_TOP_K_OUTPUT_ROSTER")
        if row["category"] == "input":
            source = self._input_operation(operation_id, row["scope_id"])
            if source is not None and materialized["artifacts"] != [
                {
                    "path": source["output_path"],
                    "bytes": source["bytes"],
                    "sha256": source["sha256"],
                }
            ]:
                raise IntegrityError("BOUNDED_INPUT_MATERIALIZATION_DRIFT")
        for artifact in materialized["artifacts"]:
            if set(artifact) != {"path", "bytes", "sha256"}:
                raise IntegrityError("BOUNDED_ARTIFACT_SCHEMA")
            name = safe_name(artifact["path"])
            path = self.namespace / name
            reject_reparse_path(path)
            if (
                name.casefold() in names
                or not path.resolve().is_relative_to(self.namespace)
                or type(artifact["bytes"]) is not int
                or artifact["bytes"] < 0
                or not isinstance(artifact["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_OR_PATH_DRIFT")
            names.add(name.casefold())
            logical += artifact["bytes"]
            top_k_file = self._top_k_file(operation_id, row["category"], name)
            if top_k_file is not None and artifact["bytes"] > top_k_file["logical_bound_bytes"]:
                raise IntegrityError("BOUNDED_TOP_K_LOGICAL_CAP_EXCEEDED")
            evaluation_file = self._evaluation_file(operation_id, row["category"], name)
            if (
                evaluation_file is not None
                and artifact["bytes"] > evaluation_file["logical_bound_bytes"]
            ):
                raise IntegrityError("BOUNDED_EVALUATION_LOGICAL_CAP_EXCEEDED")
            score_file = self._score_manifest_file(operation_id, row["category"], name)
            if score_file is not None and artifact["bytes"] > score_file["logical_bound_bytes"]:
                raise IntegrityError("BOUNDED_SCORE_MANIFEST_LOGICAL_CAP_EXCEEDED")
            reference_file = self._reference_manifest_file(operation_id, row["category"], name)
            if (
                reference_file is not None
                and artifact["bytes"] > reference_file["logical_bound_bytes"]
            ):
                raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_LOGICAL_CAP_EXCEEDED")
            deep_file = self._deep_manifest_file(operation_id, row["category"], name)
            if deep_file is not None and artifact["bytes"] > deep_file["logical_bound_bytes"]:
                raise IntegrityError("BOUNDED_DEEP_MANIFEST_LOGICAL_CAP_EXCEEDED")
            deep_receipt_file = self._deep_receipt_file(operation_id, row["category"], name)
            if (
                deep_receipt_file is not None
                and artifact["bytes"] > deep_receipt_file["logical_bound_bytes"]
            ):
                raise IntegrityError("BOUNDED_DEEP_RECEIPT_LOGICAL_CAP_EXCEEDED")
            reference_receipt_file = self._reference_receipt_file(
                operation_id, row["category"], name
            )
            if (
                reference_receipt_file is not None
                and artifact["bytes"] > reference_receipt_file["logical_bound_bytes"]
            ):
                raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_LOGICAL_CAP_EXCEEDED")
            if (
                certify_bytes
                and disposed is None
                and (
                    not path.is_file()
                    or path.stat().st_nlink != 1
                    or path.stat().st_size != artifact["bytes"]
                    or sha256_file(path) != artifact["sha256"]
                )
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_OR_PATH_DRIFT")
        if names != {
            p.relative_to(self.namespace).as_posix().casefold()
            for p in self._file_roster(directory)
        }:
            raise IntegrityError("BOUNDED_FILE_INTENT_DRIFT")
        expected = {
            "schema_version": "mp2-cost-bounded-settlement/1.0",
            "state": "SETTLED_BYTES_VERIFIED",
            "reservation_sha256": sha256_file(directory / "reserve.json"),
            "materialization_sha256": sha256_file(directory / "materialized.json"),
            "logical_bytes": logical,
            "binding": row["binding"],
        }
        if (
            canonical_json_bytes(settled) != canonical_json_bytes(expected)
            or logical > row["reserved_bytes"]
        ):
            raise IntegrityError("BOUNDED_SETTLEMENT_DRIFT")
        if disposed is not None:
            return disposed
        return (
            settled
            if certify_bytes
            else {
                **settled,
                "state": "SETTLED_CUSTODY_METADATA_ONLY",
                "raw_bytes_currently_certified": False,
            }
        )


class BoundedLedgerAccounting(BoundedArtifactWriter):
    """Read-only live reservation accounting, never sealed replay evidence.

    The route supplies its authenticated process roster. Only declared file
    metadata and control predicates are inspected; raw payload is not hashed.
    """

    def __init__(
        self,
        namespace: Path,
        *,
        authority: Path,
        guard: Path,
        owner: Path,
        admitted_owners: Mapping[Path, str],
        admitted_runtime_identities: Mapping[Path, dict[str, Any]],
        expected_owner_roster_sha256: str,
        control_publisher: BoundedControlPublisher,
        packet_id: str | None = None,
        admitted_packet_seals: Mapping[str, str] | None = None,
        expected_packet_open_sha256: str | None = None,
        expected_packet_seal_sha256: str | None = None,
    ) -> None:
        for path in (namespace, authority, guard, owner):
            reject_reparse_path(path)
        self.namespace, self.directory = namespace.resolve(), namespace / "bounded-ledger"
        self.authority, self.guard, self.owner = authority, guard, owner
        self.control_publisher = control_publisher
        self.binding = {
            "authority_sha256": sha256_file(authority),
            "guard_sha256": sha256_file(guard),
            "owner_sha256": sha256_file(owner),
        }
        document, claim = read_canonical_json(authority), read_canonical_json(guard)
        self.storage_authority = copy.deepcopy(document)
        self.allocation_unit = size(document.get("allocation_unit_bytes"))
        if (
            document.get("namespace") != str(namespace)
            or document.get("writer_policy") != policy_caps()
            or document.get("scientific_execution_authorized") is not False
            or claim.get("namespace") != str(namespace)
            or claim.get("authority_sha256") != self.binding["authority_sha256"]
            or claim.get("automatic_retry") is not False
            or not 0 < self.allocation_unit <= MIB
            or self.allocation_unit & (self.allocation_unit - 1)
            or control_publisher.namespace != self.namespace
            or control_publisher.authority.resolve() != authority.resolve()
            or not self.directory.is_dir()
        ):
            raise IntegrityError("BOUNDED_ACCOUNTING_BINDING_DRIFT")
        self._configure_owners(
            admitted_owners, expected_owner_roster_sha256, admitted_runtime_identities
        )
        self._configure_score_storage(document)
        self._configure_input_storage(document)
        self._configure_packet(document, packet_id, admitted_packet_seals)
        self._configure_top_k_storage(document)
        self._configure_evaluation_storage(document)
        self._configure_score_manifest_storage(document)
        self._expected_open_sha256 = expected_packet_open_sha256
        self._configure_reference_manifest_storage(document)
        self._configure_deep_manifest_storage(document)
        self._configure_deep_receipt_storage(document)
        self._configure_reference_receipt_storage(document)
        self._packet_owner_binding: dict[str, str] | None = None
        if self.packet_id is None:
            if expected_packet_open_sha256 is not None or expected_packet_seal_sha256 is not None:
                raise IntegrityError("BOUNDED_PACKET_POLICY_REQUIRED")
        else:
            for digest in (expected_packet_open_sha256, expected_packet_seal_sha256):
                if digest is not None and (
                    type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)
                ):
                    raise IntegrityError("BOUNDED_PACKET_ACCOUNTING_BINDING")
            if expected_packet_open_sha256 is None:
                raise IntegrityError("BOUNDED_PACKET_ACCOUNTING_OPEN_REQUIRED")
            self._sealed_sha256 = expected_packet_seal_sha256
        with serialized_storage_lane(control_publisher.lane):
            self._verify_accounting_bindings()
            self._packet_totals()

    def _packet_open(self) -> dict[str, Any]:
        document = super()._packet_open()
        if self._packet_owner_binding is not None:
            document["binding"] = self._packet_owner_binding
        return document

    def _verify_accounting_bindings(self) -> None:
        for path, field in (
            (self.authority, "authority_sha256"),
            (self.guard, "guard_sha256"),
            (self.owner, "owner_sha256"),
        ):
            reject_reparse_path(path)
            if sha256_file(path) != self.binding[field]:
                raise IntegrityError("BOUNDED_ACCOUNTING_BINDING_DRIFT")
        self._verify_owners()
        if self.packet_id is None:
            return
        path = self.packet_root / "open.json"
        reject_reparse_path(path)
        if not path.is_file() or sha256_file(path) != self._expected_open_sha256:
            raise IntegrityError("BOUNDED_PACKET_OPEN_DRIFT")
        opened = read_canonical_json(path)
        baseline = opened.get("baseline")
        if (
            not self._binding_matches(opened.get("binding"))
            or type(baseline) is not dict
            or set(baseline) != {"actual_bytes", "files"}
            or any(type(value) is not int or value < 0 for value in baseline.values())
        ):
            raise IntegrityError("BOUNDED_PACKET_ACCOUNTING_BINDING")
        self._baseline_actual, self._baseline_files = baseline["actual_bytes"], baseline["files"]
        self._packet_owner_binding = opened["binding"]
        if opened != self._packet_open() or not self.directory.is_dir():
            raise IntegrityError("BOUNDED_PACKET_OPEN_DRIFT")

    def accounting(self) -> dict[str, int]:
        if self.control_publisher is None:
            raise IntegrityError("BOUNDED_CONTROL_PUBLISHER_REQUIRED")
        with serialized_storage_lane(self.control_publisher.lane):
            self._verify_accounting_bindings()
            return super().accounting()

    def _active(self) -> None:
        raise IntegrityError("BOUNDED_ACCOUNTING_READ_ONLY")

    def replay(self, operation_id: str, *, certify_bytes: bool = True) -> dict[str, Any]:
        if certify_bytes:
            raise IntegrityError("BOUNDED_ACCOUNTING_CANNOT_CERTIFY_PAYLOAD")
        return super().replay(operation_id, certify_bytes=False)


class BoundedArtifactReplay(BoundedArtifactWriter):
    """Read-only ledger predicates from caller-authenticated sealed bindings.

    The route must authenticate the committed inventory and terminal custody
    before constructing this reader. It is not authority publication or a
    liveness gate. No writer constructor, census or process admission runs.
    """

    def __init__(
        self,
        namespace: Path,
        *,
        authority: Path,
        guard: Path,
        owner: Path,
        expected_binding: dict[str, str],
        control_inventory: list[dict[str, Any]],
        expected_inventory_sha256: str,
        admitted_owners: Mapping[Path, str] | None = None,
        admitted_runtime_identities: Mapping[Path, dict[str, Any]] | None = None,
        expected_owner_roster_sha256: str | None = None,
        packet_id: str | None = None,
        admitted_packet_seals: Mapping[str, str] | None = None,
        expected_packet_seal_sha256: str | None = None,
    ) -> None:
        from ai_service_v2.training.cost_reference_metadata_01 import (
            MetadataBoundary,
            validate_inventory,
        )

        for path in (namespace, authority, guard, owner):
            reject_reparse_path(path)
        self.namespace = namespace.resolve()
        self.authority, self.guard, self.owner = authority, guard, owner
        self.directory = self.namespace / "bounded-ledger"
        self.binding = dict(expected_binding)
        if (
            set(self.binding) != {"authority_sha256", "guard_sha256", "owner_sha256"}
            or any(
                type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)
                for digest in self.binding.values()
            )
            or not guard.resolve().is_relative_to(self.namespace)
            or not owner.resolve().is_relative_to(self.namespace)
            or canonical_json_sha256({"artifacts": control_inventory}) != expected_inventory_sha256
        ):
            raise IntegrityError("BOUNDED_REPLAY_BINDING_DRIFT")
        rows = validate_inventory(control_inventory)
        pattern = (
            r"(?:bounded-ledger/[a-z0-9][a-z0-9-]{0,99}/"
            r"(?:reserve|materialized|settled|file-[0-9]{6})\.json"
            r"|bounded-ledger/packets/[a-z0-9][a-z0-9-]{0,99}/(?:open|seal)\.json"
            r"|bounded-ledger/packets/[a-z0-9][a-z0-9-]{0,99}/operations/"
            r"[a-z0-9][a-z0-9-]{0,99}/(?:reserve|materialized|settled|file-[0-9]{6})\.json"
            r"|controls/retention/[a-z0-9][a-z0-9-]{0,99}/[0-9]{6}\.json"
            r"|controls/disposal/[a-z0-9][a-z0-9-]{0,99}/(?:intent|disposed)\.json)"
        )
        if not rows or any(not re.fullmatch(pattern, name) for name in rows):
            raise IntegrityError("BOUNDED_REPLAY_CONTROL_ROSTER")
        self._controls = {self.namespace / safe_name(name): value for name, value in rows.items()}
        owner_paths = list(admitted_owners) if admitted_owners is not None else [owner]
        self._boundary = MetadataBoundary(
            {
                path: "CONTROL_BYTES_ONLY"
                for path in (*self._controls, authority, guard, *owner_paths)
            },
            (self.namespace,),
        )
        with self._boundary.enforce():
            if sha256_file(authority) != self.binding["authority_sha256"]:
                raise IntegrityError("BOUNDED_REPLAY_BINDING_DRIFT")
            document = read_canonical_json(authority)
        self.storage_authority = copy.deepcopy(document)
        policy_controls = current_storage_policy_controls(document)
        self._boundary = MetadataBoundary(
            {
                **{
                    path: "CONTROL_BYTES_ONLY"
                    for path in (*self._controls, authority, guard, *owner_paths)
                },
                **policy_controls,
            },
            (self.namespace, *(path.parent for path in policy_controls)),
        )
        self._payload_reports: list[dict[str, Any]] = []
        self._certified_operations: set[str] = set()
        self._batch_active = False
        with self._boundary.enforce():
            self._configure_owners(
                admitted_owners, expected_owner_roster_sha256, admitted_runtime_identities
            )
            self._verify_control_bindings()
            document, claim = read_canonical_json(authority), read_canonical_json(guard)
            self.allocation_unit = size(document.get("allocation_unit_bytes"))
            if not 0 < self.allocation_unit <= MIB or self.allocation_unit & (
                self.allocation_unit - 1
            ):
                raise IntegrityError("BOUNDED_REPLAY_AUTHORITY_OR_CLAIM")
            self._configure_score_storage(document)
            self._configure_input_storage(document)
            self._configure_top_k_storage(document)
            self._configure_evaluation_storage(document)
            self._configure_score_manifest_storage(document)
            self._configure_reference_manifest_storage(document)
            self._configure_deep_manifest_storage(document)
            self._configure_deep_receipt_storage(document)
            self._configure_reference_receipt_storage(document)
            self._configure_packet(document, packet_id, admitted_packet_seals)
            if self.packet_id is not None:
                seal_path = self.packet_root / "seal.json"
                if (
                    expected_packet_seal_sha256 is None
                    or seal_path not in self._controls
                    or self._controls[seal_path]["sha256"] != expected_packet_seal_sha256
                ):
                    raise IntegrityError("BOUNDED_PACKET_REPLAY_SEAL_REQUIRED")
                self._sealed_sha256 = expected_packet_seal_sha256
                self._replay_successor_seals: dict[str, str] = {}
                # Only terminal replay can admit later sealed packets from its
                # caller-authenticated inventory; live writers keep their guard.
                policy_ids = self.packet_policy["packet_ids"]
                for successor in policy_ids[policy_ids.index(self.packet_id) + 1 :]:
                    successor_root = self.namespace / "bounded-ledger/packets" / successor
                    successor_seal = successor_root / "seal.json"
                    if successor_seal in self._controls:
                        if successor_root / "open.json" not in self._controls:
                            raise IntegrityError("BOUNDED_PACKET_REPLAY_SUCCESSOR_OPEN_REQUIRED")
                        self._replay_successor_seals[successor] = self._controls[successor_seal][
                            "sha256"
                        ]
                self._packet_totals()
                seal = read_canonical_json(seal_path)
                self._baseline_actual = seal["baseline"]["actual_bytes"]
                self._baseline_files = seal["baseline"]["files"]
                if read_canonical_json(
                    self.packet_root / "open.json"
                ) != self._packet_open() or seal["open_sha256"] != sha256_file(
                    self.packet_root / "open.json"
                ):
                    raise IntegrityError("BOUNDED_PACKET_OPEN_DRIFT")
            elif expected_packet_seal_sha256 is not None:
                raise IntegrityError("BOUNDED_PACKET_POLICY_REQUIRED")
            descriptor = read_canonical_json(owner)
            admitted_policy = document.get("writer_policy")
            self.allocation_unit = size(document.get("allocation_unit_bytes"))
            if (
                document.get("namespace") != str(namespace)
                or not isinstance(admitted_policy, dict)
                or canonical_json_bytes(admitted_policy) != canonical_json_bytes(policy_caps())
                or document.get("scientific_execution_authorized") is not False
                or not 0 < self.allocation_unit <= MIB
                or self.allocation_unit & (self.allocation_unit - 1)
                or claim.get("namespace") != str(namespace)
                or claim.get("authority_sha256") != self.binding["authority_sha256"]
                or claim.get("automatic_retry") is not False
                or descriptor.get("schema_version") != "mp2-cost-role-process/1.0"
            ):
                raise IntegrityError("BOUNDED_REPLAY_AUTHORITY_OR_CLAIM")

    def _verify_control_bindings(self) -> None:
        if self._batch_active:
            return
        for path, field in (
            (self.authority, "authority_sha256"),
            (self.guard, "guard_sha256"),
            (self.owner, "owner_sha256"),
        ):
            reject_reparse_path(path)
            if sha256_file(path) != self.binding[field]:
                raise IntegrityError("BOUNDED_REPLAY_BINDING_DRIFT")
        self._verify_owners()
        for path, row in self._controls.items():
            reject_reparse_path(path)
            if (
                not path.is_file()
                or path.stat().st_nlink != 1
                or path.stat().st_size != row["bytes"]
                or sha256_file(path) != row["sha256"]
            ):
                raise IntegrityError("BOUNDED_REPLAY_CONTROL_DRIFT")

    @contextmanager
    def verified_batch(self) -> Iterator[None]:
        """Check every frozen control before and after one read-only replay batch."""
        if self._batch_active or _METADATA_PASS.get() is not None:
            raise IntegrityError("BOUNDED_REPLAY_NESTED_BATCH")
        with self._boundary.enforce():
            self._verify_control_bindings()
        token = _METADATA_PASS.set({})
        path_token = _CHECKED_PATHS.set(set())
        self._batch_active = True
        try:
            yield
        finally:
            self._batch_active = False
            _METADATA_PASS.reset(token)
            _CHECKED_PATHS.reset(path_token)
            with self._boundary.enforce():
                self._verify_control_bindings()

    def _active(self) -> None:
        raise IntegrityError("BOUNDED_REPLAY_READ_ONLY")

    def accounting(self) -> dict[str, int]:
        raise IntegrityError("BOUNDED_REPLAY_CANNOT_ACCOUNT_LIVE_OCCUPANCY")

    def replay(self, operation_id: str, *, certify_bytes: bool = True) -> dict[str, Any]:
        from ai_service_v2.training.cost_reference_metadata_01 import MetadataBoundary

        self._certified_operations.discard(operation_id)
        with self._boundary.enforce():
            self._verify_control_bindings()
            result = super().replay(operation_id, certify_bytes=False)
            if not certify_bytes or result["state"] == "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED":
                return result
            rows = read_canonical_json(
                self.directory / operation_name(operation_id) / "materialized.json"
            )["artifacts"]
        payload_boundary = MetadataBoundary(
            {
                **{path: "CONTROL_BYTES_ONLY" for path, _ in self._boundary.allowed.values()},
                **{
                    self.namespace / safe_name(row["path"]): "ADMITTED_OPERATION_PAYLOAD_BYTES_ONLY"
                    for row in rows
                },
            },
            (self.namespace,),
        )
        try:
            with payload_boundary.enforce():
                self._verify_control_bindings()
                result = super().replay(operation_id, certify_bytes=True)
                self._certified_operations.add(operation_id)
                return result
        finally:
            self._payload_reports.append(payload_boundary.report())

    def report(self) -> dict[str, Any]:
        return {
            **self._boundary.report(),
            "read_scope": "BOUND_LEDGER_CONTROL_BYTES_ONLY"
            if not self._payload_reports
            else "BOUND_CONTROLS_THEN_ADMITTED_OPERATION_PAYLOAD_BYTES",
            "payload_read_reports": list(self._payload_reports),
            "payload_bytes_certified": bool(self._certified_operations),
            "certified_operations": sorted(self._certified_operations),
            "terminal_custody_authority": "REQUIRES_CALLER_COMMITTED_TERMINAL_GATE",
            "owner_roster_sha256": self.owner_roster_sha256,
            "scientific_execution_authorized": False,
        }


class BoundedTransaction:
    def __init__(self, writer: BoundedArtifactWriter, directory: Path, cap: int) -> None:
        self.writer, self.directory, self.cap = writer, directory, cap
        self.lengths: dict[str, int] = {}
        self.streams: list[BoundedStream] = []
        self.finished = False
        reservation = writer._reservation(directory)
        self.category = reservation["category"]
        self.input_policy = (
            writer._input_operation(directory.name, reservation["scope_id"])
            if reservation["category"] == "input"
            else None
        )

    def open(self, name: str) -> BoundedStream:
        self.writer._active()
        if self.finished:
            raise IntegrityError("BOUNDED_TRANSACTION_CLOSED")
        name = safe_name(name)
        self.writer._top_k_file(self.directory.name, self.category, name)
        self.writer._evaluation_file(self.directory.name, self.category, name)
        self.writer._score_manifest_file(self.directory.name, self.category, name)
        self.writer._reference_manifest_file(self.directory.name, self.category, name)
        self.writer._deep_manifest_file(self.directory.name, self.category, name)
        self.writer._deep_receipt_file(self.directory.name, self.category, name)
        self.writer._reference_receipt_file(self.directory.name, self.category, name)
        if self.input_policy is not None and name != self.input_policy["output_path"]:
            raise IntegrityError("BOUNDED_INPUT_OUTPUT_ROSTER_DRIFT")
        self.writer._packet_output(name)
        path = self.writer.namespace / name
        reject_reparse_path(path)
        if (
            name.split("/")[0] in {"bounded-ledger", "children", "journal", "lifecycle"}
            or name.casefold() in {key.casefold() for key in self.lengths}
            or path.exists()
            or path == self.writer.guard
            or path in self.writer._owners
            or not path.resolve().is_relative_to(self.writer.namespace)
        ):
            raise IntegrityError("BOUNDED_UNOWNED_OR_DUPLICATE_PATH")
        path.parent.mkdir(parents=True, exist_ok=True)
        with serialized_storage_lane(self.writer.lane):
            self.writer._ownership_boundary()
            self.writer._write_ledger(
                self.directory / f"file-{len(self.lengths):06d}.json",
                {
                    "schema_version": "mp2-cost-bounded-file-intent/1.0",
                    "binding": self.writer.binding,
                    "operation_id": self.directory.name,
                    "path": name,
                },
            )
        stream = BoundedStream(self, name, path)
        self.lengths[name] = 0
        self.streams.append(stream)
        return stream

    def check(self, name: str, extent: int) -> None:
        self.writer._active()
        if self.finished:
            raise IntegrityError("BOUNDED_TRANSACTION_CLOSED")
        if self.input_policy is not None and extent > self.input_policy["bytes"]:
            raise IntegrityError("BOUNDED_INPUT_LOGICAL_CAP_EXCEEDED")
        top_k = self.writer._top_k_file(self.directory.name, self.category, name)
        if top_k is not None and extent > top_k["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_TOP_K_LOGICAL_CAP_EXCEEDED")
        evaluation = self.writer._evaluation_file(self.directory.name, self.category, name)
        if evaluation is not None and extent > evaluation["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_EVALUATION_LOGICAL_CAP_EXCEEDED")
        score_manifest = self.writer._score_manifest_file(self.directory.name, self.category, name)
        if score_manifest is not None and extent > score_manifest["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_LOGICAL_CAP_EXCEEDED")
        reference_manifest = self.writer._reference_manifest_file(
            self.directory.name, self.category, name
        )
        if reference_manifest is not None and extent > reference_manifest["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_LOGICAL_CAP_EXCEEDED")
        deep_manifest = self.writer._deep_manifest_file(self.directory.name, self.category, name)
        if deep_manifest is not None and extent > deep_manifest["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_LOGICAL_CAP_EXCEEDED")
        deep_receipt = self.writer._deep_receipt_file(self.directory.name, self.category, name)
        if deep_receipt is not None and extent > deep_receipt["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_LOGICAL_CAP_EXCEEDED")
        reference_receipt = self.writer._reference_receipt_file(
            self.directory.name, self.category, name
        )
        if reference_receipt is not None and extent > reference_receipt["logical_bound_bytes"]:
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_LOGICAL_CAP_EXCEEDED")
        unit = self.writer.allocation_unit
        lengths = {**self.lengths, name: extent}
        charged = sum((length + unit - 1) // unit * unit for length in lengths.values())
        if charged > self.cap:
            raise IntegrityError("BOUNDED_CAP_EXCEEDED")

    def settle(self) -> None:
        self.writer._active()
        if not self.lengths or any(not stream.closed for stream in self.streams):
            raise IntegrityError("BOUNDED_EMPTY_OR_OPEN_STREAM")
        evaluation = self.writer._evaluation_operation(self.directory.name)
        if evaluation is not None and set(self.lengths) != set(evaluation["files"]):
            raise IntegrityError("BOUNDED_EVALUATION_OUTPUT_ROSTER")
        score_manifest = self.writer._score_manifest_operation(self.directory.name)
        if score_manifest is not None and set(self.lengths) != {score_manifest["path"]}:
            raise IntegrityError("BOUNDED_SCORE_MANIFEST_OUTPUT_ROSTER")
        reference_manifest = self.writer._reference_manifest_operation(self.directory.name)
        if reference_manifest is not None and set(self.lengths) != {reference_manifest["path"]}:
            raise IntegrityError("BOUNDED_REFERENCE_MANIFEST_OUTPUT_ROSTER")
        deep_manifest = self.writer._deep_manifest_operation(self.directory.name)
        if deep_manifest is not None and set(self.lengths) != {deep_manifest["path"]}:
            raise IntegrityError("BOUNDED_DEEP_MANIFEST_OUTPUT_ROSTER")
        deep_receipt = self.writer._deep_receipt_operation(self.directory.name)
        if deep_receipt is not None and set(self.lengths) != set(deep_receipt["files"]):
            raise IntegrityError("BOUNDED_DEEP_RECEIPT_OUTPUT_ROSTER")
        reference_receipt = self.writer._reference_receipt_operation(self.directory.name)
        if reference_receipt is not None and set(self.lengths) != set(reference_receipt["files"]):
            raise IntegrityError("BOUNDED_REFERENCE_RECEIPT_OUTPUT_ROSTER")
        policy = self.writer.top_k_storage_policy
        if policy is not None:
            row = policy["operations"].get(self.directory.name)
            if row is not None and row["path"] not in self.lengths:
                raise IntegrityError("BOUNDED_TOP_K_OUTPUT_ROSTER")
        with serialized_storage_lane(self.writer.lane):
            self.writer._ownership_boundary()
            rows = []
            for name, length in sorted(self.lengths.items()):
                path = self.writer.namespace / name
                reject_reparse_path(path)
                if path.stat().st_size != length or path.stat().st_nlink != 1:
                    raise IntegrityError("BOUNDED_MATERIALIZATION_DRIFT")
                rows.append({"path": name, "bytes": length, "sha256": sha256_file(path)})
            materialized = {
                "schema_version": "mp2-cost-bounded-materialization/1.0",
                "reservation_sha256": sha256_file(self.directory / "reserve.json"),
                "artifacts": rows,
            }
            self.writer._write_ledger(self.directory / "materialized.json", materialized)
            if read_canonical_json(self.directory / "materialized.json") != materialized:
                raise IntegrityError("BOUNDED_MATERIALIZATION_READBACK")
            self.writer._write_ledger(
                self.directory / "settled.json",
                {
                    "schema_version": "mp2-cost-bounded-settlement/1.0",
                    "state": "SETTLED_BYTES_VERIFIED",
                    "reservation_sha256": sha256_file(self.directory / "reserve.json"),
                    "materialization_sha256": sha256_file(self.directory / "materialized.json"),
                    "logical_bytes": sum(self.lengths.values()),
                    "binding": self.writer.binding,
                },
            )
            self.writer.replay(self.directory.name)
            self.finished = True

    def close(self) -> None:
        for stream in self.streams:
            stream.close()
        self.finished = True


class BoundedStream(io.RawIOBase):
    """No public descriptor: serializers must use checked Python write calls."""

    def __init__(self, transaction: BoundedTransaction, name: str, path: Path) -> None:
        super().__init__()
        self.transaction, self.name = transaction, name
        self._stream = path.open("xb", buffering=0)

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def fileno(self) -> int:
        raise IntegrityError("BOUNDED_NATIVE_DESCRIPTOR_BYPASS_FORBIDDEN")

    def tell(self) -> int:
        return self._stream.tell()

    def write(self, data: Any) -> int:
        if (
            os.getpid() != self.transaction.writer.pid
            or threading.get_ident() != self.transaction.writer.thread
        ):
            raise IntegrityError("BOUNDED_FOREIGN_PROCESS_OR_THREAD")
        with serialized_storage_lane(self.transaction.writer.lane):
            length = memoryview(data).nbytes
            extent = max(self.transaction.lengths[self.name], self.tell() + length)
            self.transaction.check(self.name, extent)
            self.transaction.writer._invalidate_output(
                self.transaction.writer.namespace / self.name,
                operation_directory=self.transaction.directory,
            )
            written = self._stream.write(data)
            if written is None or written != length:
                raise IntegrityError("BOUNDED_PARTIAL_WRITE_IN_DOUBT")
            self.transaction.lengths[self.name] = extent
            return written

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if type(offset) is not int or whence not in {os.SEEK_SET, os.SEEK_CUR, os.SEEK_END}:
            raise IntegrityError("BOUNDED_SEEK_SCHEMA")
        target = offset + (
            self.tell()
            if whence == os.SEEK_CUR
            else self.transaction.lengths[self.name]
            if whence == os.SEEK_END
            else 0
        )
        if target < 0:
            raise IntegrityError("BOUNDED_NEGATIVE_SEEK")
        self.transaction.check(self.name, max(target, self.transaction.lengths[self.name]))
        return self._stream.seek(target)

    def truncate(self, size: int | None = None) -> int:
        if (
            os.getpid() != self.transaction.writer.pid
            or threading.get_ident() != self.transaction.writer.thread
        ):
            raise IntegrityError("BOUNDED_FOREIGN_PROCESS_OR_THREAD")
        with serialized_storage_lane(self.transaction.writer.lane):
            extent = self.tell() if size is None else size
            if type(extent) is not int or extent < 0:
                raise IntegrityError("BOUNDED_TRUNCATE_SCHEMA")
            self.transaction.check(self.name, extent)
            self.transaction.writer._invalidate_output(
                self.transaction.writer.namespace / self.name,
                operation_directory=self.transaction.directory,
            )
            value = self._stream.truncate(extent)
            self.transaction.lengths[self.name] = extent
            return value

    def flush(self) -> None:
        if not self.closed:
            self._stream.flush()

    def close(self) -> None:
        if not self.closed:
            self._stream.flush()
            os.fsync(self._stream.fileno())
            super().close()
            self._stream.close()
