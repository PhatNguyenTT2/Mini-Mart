#!/usr/bin/env python3
"""Strict, attempt-agnostic binding of immutable gate-receipt Git blobs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable


_CONTROL_PREFIX = PurePosixPath(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOWER_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class GateReceiptBindingError(RuntimeError):
    """Fail-closed receipt mismatch carrying only a stable error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GateReceiptSpec:
    """One immutable set of stage, packet, schema, and verdict predicates."""

    stage_id: str
    packet_files: tuple[str, ...]
    central_schema: str
    central_verdict: str
    central_validator_verdict: str
    fresh_audit_schema: str
    fresh_audit_verdict: str


@dataclass(frozen=True)
class ReceiptLocator:
    """Canonical repository-relative path and exact raw-blob digest."""

    path: str
    sha256: str


GitBlobReader = Callable[[Path, str, str], bytes]


def _fail(code: str) -> None:
    raise GateReceiptBindingError(code)


def _canonical_json_path(value: Any, *, packet_files: tuple[str, ...]) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "//" in value:
        _fail("LOCATOR_PATH_INVALID")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or candidate.as_posix() != value
        or candidate.suffix != ".json"
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.parent != _CONTROL_PREFIX
        or value in packet_files
    ):
        _fail("LOCATOR_PATH_INVALID")
    return value


def _require_lower_sha256(value: Any) -> str:
    if not isinstance(value, str) or _LOWER_SHA256.fullmatch(value) is None:
        _fail("LOCATOR_HASH_INVALID")
    return value


def _strict_json_object(raw: bytes, *, role: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        _fail(f"{role}_JSON_INVALID")

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        folded: set[str] = set()
        for key, value in pairs:
            normalized = key.casefold()
            if key in result or normalized in folded:
                raise ValueError("duplicate key")
            result[key] = value
            folded.add(normalized)
        return result

    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_constant=lambda _token: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        _fail(f"{role}_JSON_INVALID")
    if not isinstance(value, dict):
        _fail(f"{role}_JSON_INVALID")
    return value


def _read_blob(
    reader: GitBlobReader,
    repository_root: Path,
    revision: str,
    path: str,
    *,
    role: str,
) -> bytes:
    try:
        raw = reader(repository_root, revision, path)
    except Exception:
        _fail(f"{role}_BLOB_UNRESOLVED")
    if not isinstance(raw, bytes):
        _fail(f"{role}_BLOB_UNRESOLVED")
    return raw


def _packet_facts(
    *,
    repository_root: Path,
    packet_commit: str,
    packet_files: tuple[str, ...],
    read_git_blob: GitBlobReader,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for path in packet_files:
        raw = _read_blob(
            read_git_blob,
            repository_root,
            packet_commit,
            path,
            role="PACKET_ARTIFACT",
        )
        facts.append(
            {
                "path": path,
                "git_blob_bytes": len(raw),
                "git_blob_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return facts


def _validate_spec(spec: GateReceiptSpec) -> None:
    if not isinstance(spec, GateReceiptSpec):
        _fail("SPEC_INVALID")
    strings = (
        spec.stage_id,
        spec.central_schema,
        spec.central_verdict,
        spec.central_validator_verdict,
        spec.fresh_audit_schema,
        spec.fresh_audit_verdict,
    )
    if any(not isinstance(value, str) or not value for value in strings):
        _fail("SPEC_INVALID")
    if (
        not isinstance(spec.packet_files, tuple)
        or len(spec.packet_files) == 0
        or len(set(spec.packet_files)) != len(spec.packet_files)
    ):
        _fail("SPEC_INVALID")
    for path in spec.packet_files:
        if not isinstance(path, str) or PurePosixPath(path).as_posix() != path:
            _fail("SPEC_INVALID")
        candidate = PurePosixPath(path)
        if candidate.parent != _CONTROL_PREFIX or any(
            part in {"", ".", ".."} for part in candidate.parts
        ):
            _fail("SPEC_INVALID")


def _validate_central(
    document: dict[str, Any],
    *,
    spec: GateReceiptSpec,
    packet_commit: str,
    packet_facts: list[dict[str, Any]],
    locator_path: str,
) -> None:
    checks = (
        (document.get("schema_version") == spec.central_schema, "CENTRAL_SCHEMA_MISMATCH"),
        (document.get("stage_id") == spec.stage_id, "CENTRAL_STAGE_MISMATCH"),
        (document.get("verdict") == spec.central_verdict, "CENTRAL_VERDICT_MISMATCH"),
        (document.get("packet_commit") == packet_commit, "CENTRAL_PACKET_COMMIT_MISMATCH"),
        (document.get("packet_artifacts") == packet_facts, "CENTRAL_PACKET_ARTIFACT_MISMATCH"),
        (
            document.get("validator_verdict") == spec.central_validator_verdict,
            "CENTRAL_VALIDATOR_VERDICT_MISMATCH",
        ),
        (
            document.get("runtime_commands_executed") is False,
            "CENTRAL_RUNTIME_BOUNDARY_MISMATCH",
        ),
        (document.get("write_set") == [locator_path], "CENTRAL_WRITE_SET_MISMATCH"),
    )
    for valid, code in checks:
        if not valid:
            _fail(code)


def _validate_audit(
    document: dict[str, Any],
    *,
    spec: GateReceiptSpec,
    packet_commit: str,
    packet_facts: list[dict[str, Any]],
    central_sha256: str,
    locator_path: str,
) -> None:
    checks = (
        (document.get("schema_version") == spec.fresh_audit_schema, "FRESH_AUDIT_SCHEMA_MISMATCH"),
        (document.get("stage_id") == spec.stage_id, "FRESH_AUDIT_STAGE_MISMATCH"),
        (document.get("verdict") == spec.fresh_audit_verdict, "FRESH_AUDIT_VERDICT_MISMATCH"),
        (document.get("packet_commit") == packet_commit, "FRESH_AUDIT_PACKET_COMMIT_MISMATCH"),
        (document.get("packet_artifacts") == packet_facts, "FRESH_AUDIT_PACKET_ARTIFACT_MISMATCH"),
        (
            document.get("central_validation_receipt_git_blob_sha256")
            == central_sha256,
            "FRESH_AUDIT_CENTRAL_LINK_MISMATCH",
        ),
        (
            document.get("runtime_commands_executed") is False,
            "FRESH_AUDIT_RUNTIME_BOUNDARY_MISMATCH",
        ),
        (document.get("write_set") == [locator_path], "FRESH_AUDIT_WRITE_SET_MISMATCH"),
    )
    for valid, code in checks:
        if not valid:
            _fail(code)


def validate_bound_gate_receipts(
    *,
    repository_root: Path,
    execution_head: str,
    packet_commit: str,
    spec: GateReceiptSpec,
    central_locator: ReceiptLocator,
    fresh_audit_locator: ReceiptLocator,
    read_git_blob: GitBlobReader,
) -> dict[str, dict[str, str]]:
    """Bind two strict receipt documents to exact Git blobs and packet facts."""

    _validate_spec(spec)
    if not isinstance(repository_root, Path) or not callable(read_git_blob):
        _fail("BINDING_INPUT_INVALID")
    if not isinstance(execution_head, str) or _LOWER_COMMIT.fullmatch(execution_head) is None:
        _fail("EXECUTION_HEAD_INVALID")
    if not isinstance(packet_commit, str) or _LOWER_COMMIT.fullmatch(packet_commit) is None:
        _fail("PACKET_COMMIT_INVALID")
    if not isinstance(central_locator, ReceiptLocator) or not isinstance(
        fresh_audit_locator, ReceiptLocator
    ):
        _fail("LOCATOR_INVALID")
    central_path = _canonical_json_path(
        central_locator.path, packet_files=spec.packet_files
    )
    audit_path = _canonical_json_path(
        fresh_audit_locator.path, packet_files=spec.packet_files
    )
    if central_path == audit_path:
        _fail("LOCATOR_PATH_COLLISION")
    central_sha256 = _require_lower_sha256(central_locator.sha256)
    audit_sha256 = _require_lower_sha256(fresh_audit_locator.sha256)

    central_raw = _read_blob(
        read_git_blob,
        repository_root,
        execution_head,
        central_path,
        role="CENTRAL",
    )
    if hashlib.sha256(central_raw).hexdigest() != central_sha256:
        _fail("CENTRAL_RAW_HASH_MISMATCH")
    audit_raw = _read_blob(
        read_git_blob,
        repository_root,
        execution_head,
        audit_path,
        role="FRESH_AUDIT",
    )
    if hashlib.sha256(audit_raw).hexdigest() != audit_sha256:
        _fail("FRESH_AUDIT_RAW_HASH_MISMATCH")

    central = _strict_json_object(central_raw, role="CENTRAL")
    audit = _strict_json_object(audit_raw, role="FRESH_AUDIT")
    facts = _packet_facts(
        repository_root=repository_root,
        packet_commit=packet_commit,
        packet_files=spec.packet_files,
        read_git_blob=read_git_blob,
    )
    _validate_central(
        central,
        spec=spec,
        packet_commit=packet_commit,
        packet_facts=facts,
        locator_path=central_path,
    )
    _validate_audit(
        audit,
        spec=spec,
        packet_commit=packet_commit,
        packet_facts=facts,
        central_sha256=central_sha256,
        locator_path=audit_path,
    )
    return {
        "central_validation_receipt": {
            "path": central_path,
            "git_blob_sha256": central_sha256,
            "verdict": spec.central_verdict,
        },
        "fresh_independent_audit_receipt": {
            "path": audit_path,
            "git_blob_sha256": audit_sha256,
            "verdict": spec.fresh_audit_verdict,
        },
    }
