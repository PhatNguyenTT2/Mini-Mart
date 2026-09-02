"""Canonical hashing and strict JSON helpers used by every receipt."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise IntegrityError(f"duplicate JSON key: {key}")
        normalized = key.casefold()
        if normalized in folded:
            raise IntegrityError(f"case-colliding JSON keys: {folded[normalized]} / {key}")
        folded[normalized] = key
        result[key] = value
    return result


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IntegrityError("non-finite number is not valid canonical JSON")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    raise IntegrityError(f"unsupported JSON value type: {type(value).__name__}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return deterministic UTF-8 JSON bytes without a trailing newline."""

    try:
        canonical = _canonical_value(value)
        encoded = json.dumps(
            canonical,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise IntegrityError("value cannot be canonicalized as JSON") from error
    return encoded.encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise IntegrityError(f"cannot hash file: {path}") from error
    return digest.hexdigest()


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def load_strict_json(path: Path) -> dict[str, Any]:
    """Load JSON while rejecting BOMs, duplicate keys, and non-object roots."""

    try:
        payload = path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"cannot read JSON file: {path}") from error
    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {path}")
    return loads_strict_json(payload, source=str(path))


def loads_strict_json(payload: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    """Parse one JSON object with the same strict rules as ``load_strict_json``."""

    if payload.startswith(b"\xef\xbb\xbf"):
        raise IntegrityError(f"UTF-8 BOM is forbidden: {source}")
    try:
        parsed = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                IntegrityError(f"non-finite JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IntegrityError(f"invalid JSON: {source}") from error
    if not isinstance(parsed, dict):
        raise IntegrityError(f"JSON root must be an object: {source}")
    return parsed


def assert_canonical_json_file(path: Path, expected_sha256: str) -> dict[str, Any]:
    parsed = load_strict_json(path)
    actual = sha256_bytes(canonical_json_bytes(parsed))
    if actual != expected_sha256:
        raise IntegrityError(f"canonical JSON hash mismatch for {path}")
    return parsed


__all__ = [
    "assert_canonical_json_file",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "load_strict_json",
    "loads_strict_json",
    "sha256_bytes",
    "sha256_file",
]
