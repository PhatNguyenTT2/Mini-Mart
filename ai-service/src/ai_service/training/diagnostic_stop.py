"""Immutable publication of fail-closed diagnostic quality stops."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from ai_service.artifact_io import canonical_json_sha256, immutable_write_json
from ai_service.contracts import ArtifactLineage, ArtifactLineageV5
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
    lineage: ArtifactLineage | ArtifactLineageV5 | None = None
    comparison_signature_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_lineage(self) -> DiagnosticStopReport:
        if self.lineage is not None:
            keys = set(self.lineage.as_mapping())
            if keys not in (
                {"snapshot", "embedding", "rules"},
                {
                    "snapshot",
                    "embedding",
                    "rules",
                    "benchmark_spec",
                    "semantic_cohort",
                    "order_metadata",
                },
            ):
                raise ValueError("diagnostic stop lineage is incomplete")
        return self

    def with_canonical_hash(self) -> DiagnosticStopReport:
        document = self.model_dump(mode="json")
        document["artifact_sha256"] = None
        document["artifact_sha256"] = canonical_json_sha256(document)
        return DiagnosticStopReport.model_validate(document)


def publish_diagnostic_stop(run_dir: Path, report: DiagnosticStopReport) -> Path:
    destination = run_dir / "training" / "diagnostic-stop.json"
    report = report.with_canonical_hash()
    if destination.exists():
        existing = DiagnosticStopReport.model_validate_json(destination.read_text(encoding="utf-8"))
        if existing.model_dump(mode="json") != report.model_dump(mode="json"):
            raise ArtifactIntegrityError(
                "diagnostic stop artifact already exists with different content"
            )
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        immutable_write_json(destination, report.model_dump(mode="json"))
    except FileExistsError as error:
        raise ArtifactIntegrityError("diagnostic stop artifact already exists") from error
    return destination


def load_diagnostic_stop(path: Path, *, expected_run_id: str | None = None) -> DiagnosticStopReport:
    try:
        report = DiagnosticStopReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("diagnostic stop artifact cannot be read") from error
    if expected_run_id is not None and report.run_id != expected_run_id:
        raise ArtifactIntegrityError("diagnostic stop run ID differs")
    if report.artifact_sha256 is not None:
        document = report.model_dump(mode="json")
        actual = document.pop("artifact_sha256")
        document["artifact_sha256"] = None
        if actual != canonical_json_sha256(document):
            raise ArtifactIntegrityError("diagnostic stop artifact hash mismatch")
    return report


__all__ = ["DiagnosticStopReport", "load_diagnostic_stop", "publish_diagnostic_stop"]
