"""Durable lifecycle and provenance for one immutable training lineage."""

from __future__ import annotations

import json
import platform
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from ai_service.artifact_io import atomic_write_json
from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import RunStatus, TrainingVariant
from ai_service.errors import ArtifactIntegrityError

_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.STAGING: frozenset({RunStatus.TRAINING, RunStatus.FAILED}),
    RunStatus.TRAINING: frozenset({RunStatus.INTERRUPTED, RunStatus.FAILED, RunStatus.EVALUATED}),
    RunStatus.INTERRUPTED: frozenset({RunStatus.TRAINING, RunStatus.FAILED}),
    RunStatus.EVALUATED: frozenset({RunStatus.FAILED, RunStatus.SEALED}),
    RunStatus.FAILED: frozenset(),
    RunStatus.SEALED: frozenset(),
}


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
        if any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in lineage.values()
        ):
            raise ArtifactIntegrityError("run lineage contains an invalid SHA")
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
            "comparison_signature_sha256": settings.comparison_signature_sha256(),
            "training_variant": settings.train.training_variant.value,
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
        atomic_write_json(run_dir / "resolved-config.json", settings.resolved_document())
        atomic_write_json(run_dir / "run-manifest.json", document)
        return cls(run_dir=run_dir, document=document)

    @classmethod
    def load(cls, run_dir: Path) -> RunLifecycle:
        path = run_dir / "run-manifest.json"
        if not path.is_file():
            raise ArtifactIntegrityError(f"run manifest does not exist: {path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArtifactIntegrityError("run manifest cannot be parsed") from error
        if not isinstance(document, dict):
            raise ArtifactIntegrityError("run manifest must be a JSON object")
        try:
            RunStatus(document["status"])
        except (KeyError, TypeError, ValueError) as error:
            raise ArtifactIntegrityError("run manifest status is invalid") from error
        if document.get("schema_version") != "1.0.0":
            raise ArtifactIntegrityError("run manifest schema version is unsupported")
        if document.get("model_schema_version") != MODEL_SCHEMA_VERSION:
            raise ArtifactIntegrityError(
                "run manifest model schema does not match " + MODEL_SCHEMA_VERSION
            )
        sha_fields = {
            "training_signature_sha256",
            "comparison_signature_sha256",
            "experiment_signature_sha256",
        }
        if any(
            not isinstance(document.get(name), str)
            or re.fullmatch(r"[0-9a-f]{64}", document[name]) is None
            for name in sha_fields
        ):
            raise ArtifactIntegrityError("run manifest is missing comparison or variant metadata")
        try:
            TrainingVariant(document["training_variant"])
        except (KeyError, ValueError, TypeError) as error:
            raise ArtifactIntegrityError("run manifest training variant is invalid") from error
        if document.get("run_id") != run_dir.name:
            raise ArtifactIntegrityError("run manifest ID does not match its directory")
        lineage = document.get("lineage")
        if not isinstance(lineage, dict) or set(lineage) != {"snapshot", "embedding", "rules"}:
            raise ArtifactIntegrityError("run manifest lineage is incomplete")
        for name, value in lineage.items():
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ArtifactIntegrityError(f"run manifest lineage value is invalid: {name}")
        status = RunStatus(document["status"])
        terminal_reason = document.get("status_reason")
        if status in {RunStatus.FAILED, RunStatus.INTERRUPTED} and (
            not isinstance(terminal_reason, str) or not terminal_reason.strip()
        ):
            raise ArtifactIntegrityError("terminal run status requires a reason")
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
        if status in {RunStatus.FAILED, RunStatus.INTERRUPTED} and (
            reason is None or not reason.strip()
        ):
            raise ArtifactIntegrityError("FAILED/INTERRUPTED transition requires a reason")
        self.document["status"] = status.value
        self.document["status_reason"] = reason
        self.document["updated_at"] = datetime.now(UTC).isoformat()
        atomic_write_json(self.run_dir / "run-manifest.json", self.document)

    def transition_training_terminal(self, status: RunStatus, *, reason: str) -> None:
        if status not in {RunStatus.FAILED, RunStatus.INTERRUPTED}:
            raise ArtifactIntegrityError(
                "training terminal transition requires FAILED or INTERRUPTED"
            )
        summary_path = self.run_dir / "training" / "summary.json"
        if not summary_path.is_file():
            raise ArtifactIntegrityError("training terminal transition requires a training summary")
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ArtifactIntegrityError("training summary cannot be read") from error
        if summary.get("terminal_reason") != reason or not reason.strip():
            raise ArtifactIntegrityError("training summary reason does not match lifecycle reason")
        expected_action = "failed" if status is RunStatus.FAILED else "interrupted"
        if summary.get("terminal_action") != expected_action:
            raise ArtifactIntegrityError(
                "training summary terminal action does not match lifecycle"
            )
        self.transition(status, reason=reason)
