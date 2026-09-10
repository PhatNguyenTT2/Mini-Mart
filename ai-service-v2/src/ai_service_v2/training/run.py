"""Fail-closed run directory lifecycle for local research executions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_service_v2.contracts import RunManifest
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, load_strict_json


@dataclass(frozen=True)
class ProcessCommand:
    """Canonical process identity captured by the CLI rather than supplied as prose."""

    executable: str
    argv: tuple[str, ...]
    argv_source: str
    schema_version: str = "process-command/1.0"

    def __post_init__(self) -> None:
        if self.schema_version != "process-command/1.0":
            raise ContractError("unsupported process command schema")
        if not isinstance(self.executable, str) or not self.executable.strip():
            raise ContractError("process command executable is required")
        if not isinstance(self.argv, tuple) or not self.argv:
            raise ContractError("process command argv must be a non-empty tuple")
        if any(not isinstance(value, str) or not value or "\x00" in value for value in self.argv):
            raise ContractError("process command argv entries must be non-empty strings")
        if self.argv_source not in {"process_sys_argv", "provided_main_argv"}:
            raise ContractError("unsupported process command argv source")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "executable": self.executable,
            "argv": list(self.argv),
            "argv_source": self.argv_source,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ProcessCommand:
        required = {"schema_version", "executable", "argv", "argv_source"}
        if set(value) != required or not isinstance(value.get("argv"), list):
            raise ContractError("process command fields do not match schema")
        return cls(
            schema_version=value["schema_version"],
            executable=value["executable"],
            argv=tuple(value["argv"]),
            argv_source=value["argv_source"],
        )


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
    process_command: ProcessCommand,
) -> RunDirectory:
    """Create a unique RUNNING namespace without touching existing runs."""

    if root.exists():
        raise IntegrityError(f"run root already exists: {root}")
    if not isinstance(process_command, ProcessCommand):
        raise ContractError("process_command must be a validated ProcessCommand")
    root.mkdir(parents=True)
    command_sha256 = canonical_json_sha256(process_command.to_mapping())
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
    write_run_artifact(root, "command.json", process_command.to_mapping())
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


def load_run_command(run: RunDirectory | Path) -> ProcessCommand:
    """Strict-load the persisted command and replay its run-manifest hash binding."""

    loaded_run = load_run(run) if isinstance(run, Path) else run
    document = load_strict_json(loaded_run.root / "command.json")
    command = ProcessCommand.from_mapping(document)
    if canonical_json_sha256(command.to_mapping()) != loaded_run.manifest.command_sha256:
        raise IntegrityError("run command hash does not match the run manifest")
    return command


def validate_external_application_artifact(
    *,
    source_run_root: Path,
    artifact_path: Path,
    output_roots: tuple[Path, ...],
) -> Path:
    """Validate that TEST-application outputs cannot mutate a frozen source run."""

    if not artifact_path.name or artifact_path.suffix.lower() != ".json":
        raise IntegrityError("application artifact must be a JSON file path")
    if artifact_path.exists():
        raise IntegrityError(f"application artifact already exists: {artifact_path}")
    if not artifact_path.parent.is_dir():
        raise IntegrityError(
            f"application artifact parent directory does not exist: {artifact_path.parent}"
        )

    frozen_root = source_run_root.resolve()
    for candidate in (artifact_path, *output_roots):
        resolved = candidate.resolve()
        if resolved == frozen_root or frozen_root in resolved.parents:
            raise IntegrityError(
                "TEST application artifacts must be outside the frozen validation run"
            )
    return artifact_path.resolve()


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


__all__ = [
    "ProcessCommand",
    "RunDirectory",
    "create_run",
    "load_run",
    "load_run_command",
    "update_run_status",
    "validate_external_application_artifact",
    "write_run_artifact",
]
