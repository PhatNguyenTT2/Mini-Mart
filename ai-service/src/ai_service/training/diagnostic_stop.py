"""Immutable publication of fail-closed diagnostic quality stops."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from ai_service.artifact_io import atomic_write_json
from ai_service.errors import ArtifactIntegrityError


class DiagnosticStopReport(BaseModel):
    schema_version: str = "5.0.0"
    run_id: str = Field(min_length=1)
    epoch: int = Field(ge=1)
    reason: str = Field(min_length=1)
    best_gauc: float
    best_hr_at_k: float
    best_ndcg_at_k: float
    thresholds: dict[str, float]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def publish_diagnostic_stop(run_dir: Path, report: DiagnosticStopReport) -> Path:
    destination = run_dir / "training" / "diagnostic-stop.json"
    if destination.exists():
        existing = DiagnosticStopReport.model_validate_json(destination.read_text(encoding="utf-8"))
        if existing.model_dump(mode="json") != report.model_dump(mode="json"):
            raise ArtifactIntegrityError(
                "diagnostic stop artifact already exists with different content"
            )
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination, report.model_dump(mode="json"))
    return destination


def load_diagnostic_stop(path: Path, *, expected_run_id: str | None = None) -> DiagnosticStopReport:
    try:
        report = DiagnosticStopReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("diagnostic stop artifact cannot be read") from error
    if expected_run_id is not None and report.run_id != expected_run_id:
        raise ArtifactIntegrityError("diagnostic stop run ID differs")
    return report


__all__ = ["DiagnosticStopReport", "load_diagnostic_stop", "publish_diagnostic_stop"]
