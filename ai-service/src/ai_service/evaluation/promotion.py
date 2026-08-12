"""Immutable hand-off receipt from the R4 diagnostic campaign to production."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ai_service.artifact_io import immutable_write_json
from ai_service.contracts import ArtifactLineageV5
from ai_service.errors import ArtifactIntegrityError


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as error:
        raise ArtifactIntegrityError(f"promotion input is not readable: {path}") from error


class R4PromotionReport(BaseModel):
    """The only receipt allowed to bridge diagnostic and production commits."""

    schema_version: str = Field(default="5.2.0", pattern=r"^5\.2\.0$")
    deep_selection_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_deep_run_id: str = Field(min_length=1)
    selected_deep_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    h3b_hybrid_run_id: str = Field(min_length=1)
    h3b_hybrid_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    h3b_victory_matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lineage: ArtifactLineageV5
    diagnostic_git_commit: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
    production_git_commit: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
    deep_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hybrid_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_selection: dict[str, bool]
    objective_settings: dict[str, float | int | str | bool]
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def canonical_r4_promotion_sha(document: dict[str, Any]) -> str:
    payload = dict(document)
    payload.pop("artifact_sha256", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validated_document(document: dict[str, Any]) -> R4PromotionReport:
    claimed = document.get("artifact_sha256")
    if claimed != canonical_r4_promotion_sha(document):
        raise ArtifactIntegrityError("R4 promotion report hash mismatch")
    return R4PromotionReport.model_validate(document)


def publish_r4_promotion(
    destination: Path,
    *,
    deep_selection_report: Path,
    selected_deep_run_id: str,
    selected_deep_checkpoint_sha256: str,
    h3b_hybrid_run_id: str,
    h3b_hybrid_checkpoint_sha256: str,
    h3b_victory_matrix_sha256: str,
    lineage: ArtifactLineageV5,
    diagnostic_git_commit: str,
    production_git_commit: str,
    deep_config: Path,
    hybrid_config: Path,
    feature_selection: dict[str, bool],
    objective_settings: dict[str, float | int | str | bool],
) -> R4PromotionReport:
    """Validate inputs and publish a promotion receipt exactly once."""
    for path in (deep_selection_report, deep_config, hybrid_config):
        if not path.is_file():
            raise ArtifactIntegrityError(f"R4 promotion input is missing: {path}")
    document: dict[str, Any] = {
        "schema_version": "5.2.0",
        "deep_selection_report_sha256": _sha256_file(deep_selection_report),
        "selected_deep_run_id": selected_deep_run_id,
        "selected_deep_checkpoint_sha256": selected_deep_checkpoint_sha256,
        "h3b_hybrid_run_id": h3b_hybrid_run_id,
        "h3b_hybrid_checkpoint_sha256": h3b_hybrid_checkpoint_sha256,
        "h3b_victory_matrix_sha256": h3b_victory_matrix_sha256,
        "lineage": lineage.model_dump(mode="json"),
        "diagnostic_git_commit": diagnostic_git_commit,
        "production_git_commit": production_git_commit,
        "deep_config_sha256": _sha256_file(deep_config),
        "hybrid_config_sha256": _sha256_file(hybrid_config),
        "feature_selection": dict(feature_selection),
        "objective_settings": dict(objective_settings),
    }
    document["artifact_sha256"] = canonical_r4_promotion_sha(document)
    report = R4PromotionReport.model_validate(document)
    if destination.exists():
        try:
            existing = load_r4_promotion(destination)
        except ArtifactIntegrityError:
            raise
        if existing != report:
            raise ArtifactIntegrityError(
                "R4 promotion destination already contains another receipt"
            )
        return existing
    try:
        immutable_write_json(destination, report.model_dump(mode="json"))
    except (ArtifactIntegrityError, OSError) as error:
        raise ArtifactIntegrityError("R4 promotion receipt publication failed") from error
    return load_r4_promotion(destination)


def load_r4_promotion(path: Path) -> R4PromotionReport:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("R4 promotion report cannot be read") from error
    if not isinstance(document, dict):
        raise ArtifactIntegrityError("R4 promotion report must be an object")
    return _validated_document(document)


__all__ = [
    "R4PromotionReport",
    "canonical_r4_promotion_sha",
    "load_r4_promotion",
    "publish_r4_promotion",
]
