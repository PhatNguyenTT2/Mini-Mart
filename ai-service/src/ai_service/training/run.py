"""Durable lifecycle and provenance for one immutable training lineage."""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import RunStatus
from ai_service.errors import ArtifactIntegrityError

_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.STAGING: frozenset({RunStatus.TRAINING, RunStatus.INTERRUPTED}),
    RunStatus.TRAINING: frozenset({RunStatus.INTERRUPTED, RunStatus.EVALUATED}),
    RunStatus.INTERRUPTED: frozenset({RunStatus.TRAINING}),
    RunStatus.EVALUATED: frozenset({RunStatus.SEALED, RunStatus.INTERRUPTED}),
    RunStatus.SEALED: frozenset(),
}


def _atomic_json(path: Path, document: dict[str, Any]) -> None:
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


@dataclass
class RunLifecycle:
    """Small interface hiding lifecycle validation and atomic persistence."""

    run_dir: Path
    document: dict[str, Any]

    @classmethod
    def create(
        cls,
        run_dir: Path,
        *,
        settings: Settings,
        lineage: dict[str, str],
        git_commit: str,
    ) -> RunLifecycle:
        if run_dir.exists():
            raise ArtifactIntegrityError(f"immutable run already exists: {run_dir}")
        if set(lineage) != {"snapshot", "embedding", "rules"}:
            raise ArtifactIntegrityError("run lineage must contain snapshot, embedding, and rules")
        run_dir.mkdir(parents=True)
        now = datetime.now(UTC).isoformat()
        document: dict[str, Any] = {
            "schema_version": "1.0.0",
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "run_id": run_dir.name,
            "status": RunStatus.STAGING.value,
            "status_reason": None,
            "created_at": now,
            "updated_at": now,
            "training_signature_sha256": settings.training_signature_sha256(),
            "experiment_signature_sha256": settings.experiment_signature_sha256(),
            "lineage": dict(sorted(lineage.items())),
            "git_commit": git_commit,
            "hardware": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "torch": torch.__version__,
                "cuda_runtime": torch.version.cuda or "none",
                "cuda_device": (
                    torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
                ),
            },
        }
        _atomic_json(run_dir / "resolved-config.json", settings.resolved_document())
        _atomic_json(run_dir / "run-manifest.json", document)
        return cls(run_dir=run_dir, document=document)

    @classmethod
    def load(cls, run_dir: Path) -> RunLifecycle:
        path = run_dir / "run-manifest.json"
        if not path.is_file():
            raise ArtifactIntegrityError(f"run manifest does not exist: {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        RunStatus(document["status"])
        return cls(run_dir=run_dir, document=document)

    @property
    def status(self) -> RunStatus:
        return RunStatus(self.document["status"])

    def transition(self, status: RunStatus, *, reason: str | None = None) -> None:
        current = RunStatus(self.document["status"])
        if status not in _TRANSITIONS[current]:
            raise ArtifactIntegrityError(
                f"illegal run transition: {current.value} -> {status.value}"
            )
        self.document["status"] = status.value
        self.document["status_reason"] = reason
        self.document["updated_at"] = datetime.now(UTC).isoformat()
        _atomic_json(self.run_dir / "run-manifest.json", self.document)
