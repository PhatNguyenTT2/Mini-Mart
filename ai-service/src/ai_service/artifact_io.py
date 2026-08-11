"""Small fail-closed helpers for immutable JSON artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ai_service.errors import ArtifactIntegrityError


def atomic_write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as destination:
            json.dump(document, destination, indent=2, sort_keys=True)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def immutable_write_json(path: Path, document: Mapping[str, object]) -> None:
    """Publish JSON once; a previously published path is never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as destination:
            json.dump(document, destination, indent=2, sort_keys=True)
            destination.flush()
            os.fsync(destination.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise ArtifactIntegrityError(f"immutable artifact already exists: {path}") from error
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def canonical_json_sha256(document: Mapping[str, object]) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require_child_path(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ArtifactIntegrityError("artifact path escapes its root") from error
    return resolved_candidate


def publish_directory_atomic(source: Path, destination: Path) -> None:
    """Atomically publish a fully fsynced temporary directory once."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ArtifactIntegrityError(f"immutable directory already exists: {destination}")
    try:
        os.replace(source, destination)
    except OSError as error:
        raise ArtifactIntegrityError("atomic directory publication failed") from error
