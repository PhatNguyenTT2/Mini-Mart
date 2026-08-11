"""Deterministic mutations used by immutable-artifact contract tests."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch


def replace_json_field(path: Path, dotted_path: str, value: object) -> None:
    """Replace a JSON field in place, preserving a valid JSON container."""

    document = json.loads(path.read_text(encoding="utf-8"))
    parts = dotted_path.split(".")
    cursor: Any = document
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise KeyError(dotted_path)
        cursor = cursor[part]
    if not isinstance(cursor, dict):
        raise KeyError(dotted_path)
    cursor[parts[-1]] = value
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")


def rewrite_torch_payload(
    path: Path,
    mutation: Callable[[dict[str, Any]], Mapping[str, Any] | None],
) -> None:
    """Load, mutate and save a checkpoint payload without changing its manifest."""

    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise TypeError("checkpoint payload is not a mapping")
    changed = mutation(payload)
    if changed is not None:
        payload = dict(changed)
    torch.save(payload, path)


def rewrite_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    """Rewrite an NPZ archive with an explicitly supplied array mapping."""

    temporary = path.with_name(f".{path.stem}.corrupt.tmp.npz")
    np.savez_compressed(temporary, **arrays)
    os.replace(temporary, path)


def rehash_file_in_manifest(
    manifest_path: Path,
    *,
    field: str,
    checksum: str,
) -> None:
    """Update one outer checksum when a test needs to reach an inner guard."""

    replace_json_field(manifest_path, field, checksum)


def fail_nth_replace(monkeypatch: Any, n: int) -> None:
    """Inject one deterministic ``os.replace`` failure, then restore behavior."""

    original = os.replace
    calls = 0

    def replacing(
        source: str | bytes | os.PathLike[str],
        destination: str | bytes | os.PathLike[str],
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == n:
            raise OSError(f"injected os.replace failure #{n}")
        original(source, destination)

    monkeypatch.setattr(os, "replace", replacing)


__all__ = [
    "fail_nth_replace",
    "rehash_file_in_manifest",
    "replace_json_field",
    "rewrite_npz",
    "rewrite_torch_payload",
]
