"""Durable lifecycle and provenance for one immutable training lineage."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from ai_service.artifact_io import atomic_write_json
from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    ArtifactLineageInput,
    RunStatus,
    TrainingVariant,
    normalize_artifact_lineage,
)
from ai_service.errors import ArtifactIntegrityError
from ai_service.training.provenance import is_git_commit_sha

_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.STAGING: frozenset({RunStatus.TRAINING, RunStatus.FAILED}),
    RunStatus.TRAINING: frozenset({RunStatus.INTERRUPTED, RunStatus.FAILED, RunStatus.EVALUATED}),
    RunStatus.INTERRUPTED: frozenset({RunStatus.TRAINING, RunStatus.FAILED}),
    RunStatus.EVALUATED: frozenset({RunStatus.FAILED, RunStatus.SEALED}),
    RunStatus.FAILED: frozenset(),
    RunStatus.SEALED: frozenset(),
}


def _validate_document(document: object, run_id: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ArtifactIntegrityError("run manifest must be a JSON object")
    try:
        status = RunStatus(document["status"])
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("run manifest status is invalid") from error
    if document.get("schema_version") != "1.0.0":
        raise ArtifactIntegrityError("run manifest schema version is unsupported")
    if document.get("model_schema_version") != MODEL_SCHEMA_VERSION:
        raise ArtifactIntegrityError(
            "run manifest model schema does not match " + MODEL_SCHEMA_VERSION
        )
    git_commit = document.get("git_commit")
    if not is_git_commit_sha(git_commit):
        raise ArtifactIntegrityError("run manifest contains an invalid Git commit SHA")
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
    if document.get("run_id") != run_id:
        raise ArtifactIntegrityError("run manifest ID does not match its directory")
    lineage = document.get("lineage")
    if not isinstance(lineage, dict) or set(lineage) not in (
        {"snapshot", "embedding", "rules"},
        {"snapshot", "embedding", "rules", "benchmark_spec", "semantic_cohort", "order_metadata"},
    ):
        raise ArtifactIntegrityError("run manifest lineage is incomplete")
    for name, value in lineage.items():
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ArtifactIntegrityError(f"run manifest lineage value is invalid: {name}")
    terminal_reason = document.get("status_reason")
    if status in {RunStatus.FAILED, RunStatus.INTERRUPTED} and (
        not isinstance(terminal_reason, str) or not terminal_reason.strip()
    ):
        raise ArtifactIntegrityError("terminal run status requires a reason")
    return document


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
        lineage: ArtifactLineageInput,
        git_commit: str,
    ) -> RunLifecycle:
        try:
            lineage_mapping = normalize_artifact_lineage(lineage)
        except ValueError as error:
            raise ArtifactIntegrityError(f"run lineage is invalid: {error}") from error
        if run_dir.exists():
            raise ArtifactIntegrityError(f"immutable run already exists: {run_dir}")
        expected_keys = (
            {
                "snapshot",
                "embedding",
                "rules",
                "benchmark_spec",
                "semantic_cohort",
                "order_metadata",
            }
            if settings.data.rule_feature_schema_version == "3.0.0"
            else {"snapshot", "embedding", "rules"}
        )
        if set(lineage_mapping) != expected_keys:
            raise ArtifactIntegrityError("run lineage does not match the resolved artifact schema")
        if any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in lineage_mapping.values()
        ):
            raise ArtifactIntegrityError("run lineage contains an invalid SHA")
        if not is_git_commit_sha(git_commit):
            raise ArtifactIntegrityError("run manifest contains an invalid Git commit SHA")
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
            "lineage": dict(sorted(lineage_mapping.items())),
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
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        temporary_dir = Path(tempfile.mkdtemp(prefix=f".{run_dir.name}-", dir=run_dir.parent))
        try:
            resolved_document = settings.resolved_document()
            atomic_write_json(temporary_dir / "resolved-config.json", resolved_document)
            atomic_write_json(temporary_dir / "run-manifest.json", document)
            try:
                published_config = json.loads(
                    (temporary_dir / "resolved-config.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as error:
                raise ArtifactIntegrityError("resolved run config cannot be verified") from error
            if published_config != resolved_document:
                raise ArtifactIntegrityError("resolved run config changed during publication")
            _validate_document(
                json.loads((temporary_dir / "run-manifest.json").read_text(encoding="utf-8")),
                run_dir.name,
            )
            if run_dir.exists():
                raise ArtifactIntegrityError(f"immutable run already exists: {run_dir}")
            os.replace(temporary_dir, run_dir)
        except BaseException:
            shutil.rmtree(temporary_dir, ignore_errors=True)
            raise
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
        validated = _validate_document(document, run_dir.name)
        resolved_path = run_dir / "resolved-config.json"
        if resolved_path.is_file():
            try:
                resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ArtifactIntegrityError("resolved run config cannot be parsed") from error
            if (
                isinstance(resolved, dict)
                and resolved.get("data", {}).get("rule_feature_schema_version") == "3.0.0"
                and set(validated.get("lineage", {}))
                != {
                    "snapshot",
                    "embedding",
                    "rules",
                    "benchmark_spec",
                    "semantic_cohort",
                    "order_metadata",
                }
            ):
                raise ArtifactIntegrityError("v5 run manifest requires six-field lineage")
        return cls(run_dir=run_dir, document=validated)

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
        candidate = {
            **self.document,
            "status": status.value,
            "status_reason": reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        _validate_document(candidate, self.run_dir.name)
        atomic_write_json(self.run_dir / "run-manifest.json", candidate)
        self.document = candidate

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
