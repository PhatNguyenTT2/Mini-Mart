"""Fail-closed run directory lifecycle for local research executions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_service_v2.contracts import RunManifest
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json


@dataclass(frozen=True)
class RunDirectory:
    root: Path
    manifest: RunManifest


def _write_manifest(root: Path, manifest: RunManifest) -> None:
    path = root / "run_manifest.json"
    try:
        path.write_bytes(canonical_json_bytes(manifest.to_mapping()) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write run manifest: {path}") from error


def create_run(
    *,
    root: Path,
    run_id: str,
    model_id: str,
    dataset_manifest_sha256: str,
    protocol_manifest_sha256: str,
    seed: int,
    environment_lock_sha256: str,
    checkpoint_rule: str,
    command_sha256: str,
) -> RunDirectory:
    """Create a unique RUNNING namespace without touching existing runs."""

    if root.exists():
        raise IntegrityError(f"run root already exists: {root}")
    root.mkdir(parents=True)
    manifest = RunManifest(
        run_id=run_id,
        model_id=model_id,
        dataset_manifest_sha256=dataset_manifest_sha256,
        protocol_manifest_sha256=protocol_manifest_sha256,
        seed=seed,
        environment_lock_sha256=environment_lock_sha256,
        checkpoint_rule=checkpoint_rule,
        checkpoint_sha256=None,
        command_sha256=command_sha256,
        status="RUNNING",
    )
    _write_manifest(root, manifest)
    return RunDirectory(root, manifest)


def update_run_status(
    run: RunDirectory,
    *,
    status: str,
    checkpoint_sha256: str | None = None,
) -> RunDirectory:
    """Write a lifecycle transition while preserving immutable run identity."""

    current = run.manifest
    updated = RunManifest(
        run_id=current.run_id,
        model_id=current.model_id,
        dataset_manifest_sha256=current.dataset_manifest_sha256,
        protocol_manifest_sha256=current.protocol_manifest_sha256,
        seed=current.seed,
        environment_lock_sha256=current.environment_lock_sha256,
        checkpoint_rule=current.checkpoint_rule,
        checkpoint_sha256=checkpoint_sha256 or current.checkpoint_sha256,
        command_sha256=current.command_sha256,
        status=status,
    )
    _write_manifest(run.root, updated)
    return RunDirectory(run.root, updated)


def load_run(root: Path) -> RunDirectory:
    """Load a run manifest without repairing or coercing serialized values."""

    path = root / "run_manifest.json"
    manifest = RunManifest.from_mapping(load_strict_json(path))
    return RunDirectory(root, manifest)


def write_run_artifact(root: Path, name: str, document: dict[str, object]) -> Path:
    """Write one exclusive canonical JSON artifact inside a run namespace."""

    if not name or Path(name).name != name or Path(name).suffix != ".json":
        raise IntegrityError("run artifact name must be a simple .json filename")
    path = root / name
    if path.exists():
        raise IntegrityError(f"run artifact already exists: {path}")
    try:
        path.write_bytes(canonical_json_bytes(document) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write run artifact: {path}") from error
    return path


__all__ = ["RunDirectory", "create_run", "load_run", "update_run_status", "write_run_artifact"]
