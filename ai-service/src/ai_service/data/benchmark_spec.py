"""Verified cross-runtime benchmark-spec loading and canonicalization."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ai_service.errors import ArtifactIntegrityError

BENCHMARK_SCHEMA_VERSION = "3.0.0"
BENCHMARK_GENERATOR_VERSION = "5.0.0"


class SemanticTrapSpec(BaseModel):
    """One directed semantic benchmark contract from the seeded document."""

    trap_id: int = Field(ge=1, le=10)
    anchor: int = Field(gt=0)
    targets: tuple[int, ...] = Field(min_length=1)


class VerifiedBenchmarkSpec(BaseModel):
    """A schema-v5 spec whose canonical bytes match the database receipt."""

    document: dict[str, object]
    canonical_bytes: bytes
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_traps: tuple[SemanticTrapSpec, ...]
    validation_users_per_trap: int = Field(gt=0)
    test_users_per_trap: int = Field(gt=0)


def _canonical_value(value: object) -> object:
    """Produce the JSON value shared with Node's ``JSON.stringify`` contract."""

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactIntegrityError("benchmark spec contains a non-finite number")
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise ArtifactIntegrityError("benchmark spec object keys must be strings")
            normalized[key] = _canonical_value(value[key])
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_canonical_value(item) for item in value]
    raise ArtifactIntegrityError(
        f"benchmark spec contains unsupported scalar type: {type(value).__name__}"
    )


def canonical_benchmark_spec_bytes(document: Mapping[str, object]) -> bytes:
    """Canonical UTF-8 JSON used by both the seed receipt and Python loader."""

    try:
        canonical = _canonical_value(document)
        return json.dumps(
            canonical,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ArtifactIntegrityError("benchmark spec cannot be canonicalized") from error


def _required_positive_int(document: Mapping[str, object], name: str) -> int:
    value = document.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ArtifactIntegrityError(f"benchmark spec {name} must be a positive integer")
    return value


def _semantic_traps(document: Mapping[str, object]) -> tuple[SemanticTrapSpec, ...]:
    rows = document.get("semantic_traps")
    if not isinstance(rows, list) or len(rows) != 10:
        raise ArtifactIntegrityError("benchmark spec must contain exactly ten semantic traps")
    try:
        traps = tuple(SemanticTrapSpec.model_validate(row) for row in rows)
    except (TypeError, ValueError) as error:
        raise ArtifactIntegrityError("benchmark spec semantic trap is invalid") from error
    if tuple(sorted(trap.trap_id for trap in traps)) != tuple(range(1, 11)):
        raise ArtifactIntegrityError("benchmark spec semantic trap IDs must be exactly 1..10")
    if any(len(set(trap.targets)) != len(trap.targets) for trap in traps):
        raise ArtifactIntegrityError("benchmark spec semantic trap targets must be unique")
    return traps


def load_benchmark_spec(path: Path, *, expected_sha256: str) -> VerifiedBenchmarkSpec:
    """Load a v5 document only when it exactly matches its control-plane receipt."""

    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        raise ArtifactIntegrityError("benchmark spec expected checksum is invalid")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("benchmark spec cannot be read") from error
    if not isinstance(parsed, dict):
        raise ArtifactIntegrityError("benchmark spec root must be an object")
    document = {str(key): value for key, value in parsed.items()}
    if document.get("schema_version") != BENCHMARK_SCHEMA_VERSION or document.get(
        "generator_version"
    ) != BENCHMARK_GENERATOR_VERSION:
        raise ArtifactIntegrityError("benchmark spec must use schema 3.0.0 / generator 5.0.0")
    traps = _semantic_traps(document)
    validation_users = _required_positive_int(document, "semantic_validation_users_per_trap")
    test_users = _required_positive_int(document, "semantic_test_users_per_trap")
    canonical_bytes = canonical_benchmark_spec_bytes(document)
    actual_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ArtifactIntegrityError("benchmark spec checksum does not match database receipt")
    return VerifiedBenchmarkSpec(
        document=document,
        canonical_bytes=canonical_bytes,
        sha256=actual_sha256,
        semantic_traps=traps,
        validation_users_per_trap=validation_users,
        test_users_per_trap=test_users,
    )


__all__ = [
    "BENCHMARK_GENERATOR_VERSION",
    "BENCHMARK_SCHEMA_VERSION",
    "SemanticTrapSpec",
    "VerifiedBenchmarkSpec",
    "canonical_benchmark_spec_bytes",
    "load_benchmark_spec",
]
