"""Immutable hand-off receipt from the R4 diagnostic campaign to production."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ai_service.artifact_io import immutable_write_json
from ai_service.config import MODEL_SCHEMA_VERSION, Settings, load_resolved_settings, load_settings
from ai_service.contracts import (
    ArtifactLineageV5,
    CheckpointManifest,
    PipelineState,
    RunStatus,
    SplitName,
    TrainingVariant,
    artifact_lineage_model,
)
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.evaluation.ablation import R3FeatureSelection, load_deep_ablation_artifact
from ai_service.evaluation.report import load_evaluation_artifacts
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.provenance import is_git_commit_sha
from ai_service.training.run import RunLifecycle

_DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_OBJECTIVE_FIELDS = (
    "objective",
    "negative_ratio",
    "explicit_negative_ratio",
    "learning_rate",
    "minimum_learning_rate",
    "weight_decay",
    "max_epochs",
    "early_stopping_patience",
    "min_delta",
    "warmup_fraction",
    "view_auxiliary_weight",
    "rule_auxiliary_weight",
    "rule_hard_negative_count",
    "use_history_profiles",
    "max_grad_norm",
    "max_history_items",
    "validation_user_batch_size",
)


@dataclass(frozen=True)
class _RunEvidence:
    """Verified diagnostic run data needed by the promotion receipt."""

    run_id: str
    run_dir: Path
    settings: Settings
    state: PipelineState
    checkpoint_manifest: CheckpointManifest
    lineage: ArtifactLineageV5
    git_commit: str


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


def _artifact_root_from_selection_report(selection_report: Path) -> Path:
    path = selection_report.resolve()
    if (
        path.name != "report.json"
        or path.parent.parent.name != "r3"
        or path.parent.parent.parent.name != "diagnostics"
    ):
        raise ArtifactIntegrityError(
            "R3 selection report must be diagnostics/r3/<artifact>/report.json"
        )
    return path.parent.parent.parent.parent


def _require_path_within(root: Path, path: Path, *, description: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ArtifactIntegrityError(f"{description} escapes its expected root") from error
    return resolved


def _require_run_id(run_id: str) -> None:
    if not run_id.strip() or Path(run_id).name != run_id:
        raise ArtifactIntegrityError("promotion run ID is invalid")


def _load_run_evidence(
    artifact_root: Path,
    run_id: str,
    *,
    expected_variant: TrainingVariant,
) -> _RunEvidence:
    """Strict-load a completed R3 diagnostic run and its best checkpoint."""
    _require_run_id(run_id)
    root = artifact_root.resolve()
    runs_root = root / "runs"
    run_dir = _require_path_within(runs_root, runs_root / run_id, description="promotion run")
    if not run_dir.is_dir() or run_dir.parent != runs_root:
        raise ArtifactIntegrityError("promotion run directory does not match its run ID")

    lifecycle = RunLifecycle.load(run_dir)
    if lifecycle.status not in {RunStatus.TRAINING, RunStatus.EVALUATED}:
        raise ArtifactIntegrityError("promotion requires a completed diagnostic run")
    try:
        settings = load_resolved_settings(run_dir / "resolved-config.json")
        settings.validate_campaign_stage()
        state = PipelineState.model_validate_json(
            (run_dir / "pipeline-state.json").read_text(encoding="utf-8")
        )
    except (ConfigurationError, OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("promotion run evidence cannot be read") from error
    if (
        state.run_id != run_id
        or state.model_schema_version != MODEL_SCHEMA_VERSION
        or state.training_variant is not expected_variant
        or settings.train.training_variant is not expected_variant
        or lifecycle.document.get("training_variant") != expected_variant.value
    ):
        raise ArtifactIntegrityError("promotion run variant or identity mismatch")
    if settings.train.campaign_stage != "diagnostic":
        raise ArtifactIntegrityError("promotion evidence must come from a diagnostic run")
    if state.checkpoint_path is None:
        raise ArtifactIntegrityError("promotion run has no best checkpoint")

    checkpoint_path = Path(state.checkpoint_path).resolve()
    if (
        run_dir not in checkpoint_path.parents
        or checkpoint_path.parent.name != "checkpoints"
        or checkpoint_path.name != "best.pt"
    ):
        raise ArtifactIntegrityError("promotion checkpoint escapes its immutable run directory")
    try:
        checkpoint_manifest = CheckpointManifest.model_validate_json(
            checkpoint_path.with_suffix(".pt.manifest.json").read_text(encoding="utf-8")
        )
        lineage = artifact_lineage_model(lifecycle.document["lineage"])
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("promotion checkpoint evidence cannot be read") from error
    if not isinstance(lineage, ArtifactLineageV5):
        raise ArtifactIntegrityError("promotion evidence requires six-field lineage")
    if not isinstance(state.lineage, ArtifactLineageV5) or state.lineage != lineage:
        raise ArtifactIntegrityError("promotion pipeline state lineage mismatch")
    if (
        checkpoint_manifest.run_id != run_id
        or checkpoint_manifest.checkpoint_kind != "best"
        or checkpoint_manifest.training_variant is not expected_variant
        or checkpoint_manifest.model_schema_version != MODEL_SCHEMA_VERSION
        or checkpoint_manifest.parent_sha256 != lineage.as_mapping()
        or checkpoint_manifest.training_signature_sha256 != settings.training_signature_sha256()
        or checkpoint_manifest.comparison_signature_sha256 != settings.comparison_signature_sha256()
        or lifecycle.document.get("training_signature_sha256")
        != settings.training_signature_sha256()
        or lifecycle.document.get("comparison_signature_sha256")
        != settings.comparison_signature_sha256()
    ):
        raise ArtifactIntegrityError("promotion checkpoint/configuration evidence mismatch")
    git_commit = lifecycle.document.get("git_commit")
    if not is_git_commit_sha(git_commit):
        raise ArtifactIntegrityError("promotion run Git commit is invalid")

    CheckpointManager.load(
        checkpoint_path,
        model=HybridTwoTowerModel(settings),
        expected_lineage=lineage,
        expected_training_signature=settings.training_signature_sha256(),
        expected_comparison_signature=settings.comparison_signature_sha256(),
        expected_training_variant=expected_variant,
        expected_checkpoint_kind="best",
        expected_run_id=run_id,
        expected_model_schema_version=MODEL_SCHEMA_VERSION,
    )
    return _RunEvidence(
        run_id=run_id,
        run_dir=run_dir,
        settings=settings,
        state=state,
        checkpoint_manifest=checkpoint_manifest,
        lineage=lineage,
        git_commit=git_commit,
    )


def _load_production_config(
    path: Path, *, expected_variant: TrainingVariant
) -> tuple[Path, Settings]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ArtifactIntegrityError(f"R4 promotion input is missing: {path}")
    try:
        settings = load_settings(resolved)
        settings.validate_campaign_stage()
    except (ConfigurationError, ValueError) as error:
        raise ArtifactIntegrityError(f"production configuration is invalid: {path}") from error
    if (
        settings.train.campaign_stage != "production"
        or settings.data.rule_feature_schema_version != "3.0.0"
        or settings.train.training_variant is not expected_variant
    ):
        raise ArtifactIntegrityError("promotion configuration has an invalid production variant")
    return resolved, settings


def _selection_features(selection: R3FeatureSelection) -> dict[str, bool]:
    return selection.model_dump(mode="json")


def _objective_settings(settings: Settings) -> dict[str, float | int | str | bool]:
    train = settings.train.model_dump(mode="json")
    return {field: train[field] for field in _OBJECTIVE_FIELDS}


def _promotion_semantics(settings: Settings, *, ignore_variant: bool) -> dict[str, Any]:
    """Return settings that must survive the diagnostic-to-production transition."""
    document = settings.resolved_document()
    document.pop("schema_version", None)
    train = document["train"]
    assert isinstance(train, dict)
    train.pop("campaign_stage", None)
    train.pop("r3_selection_report_path", None)
    train.pop("r4_promotion_report_path", None)
    if ignore_variant:
        train.pop("training_variant", None)
    return document


def _validate_production_configs(
    *,
    deep: Settings,
    hybrid: Settings,
    selection_sha256: str,
    selected_deep_run_id: str,
    features: R3FeatureSelection,
    comparison_signature_sha256: str,
    h3b: _RunEvidence,
) -> dict[str, float | int | str | bool]:
    for settings in (deep, hybrid):
        if (
            settings.train.r3_feature_selection_mode != "selection_artifact"
            or settings.train.r3_selection_artifact_sha256 != selection_sha256
            or settings.train.r3_selected_deep_run_id != selected_deep_run_id
        ):
            raise ArtifactIntegrityError("production config does not bind the R3 selection receipt")
        if (
            settings.model.use_user_id_embedding != features.use_user_id_embedding
            or settings.model.use_price_features != features.use_price_features
        ):
            raise ArtifactIntegrityError(
                "production config feature flags differ from the R3 selection"
            )
        if settings.comparison_signature_sha256() != comparison_signature_sha256:
            raise ArtifactIntegrityError(
                "production config comparison signature differs from diagnostics"
            )

    if _promotion_semantics(deep, ignore_variant=True) != _promotion_semantics(
        hybrid, ignore_variant=True
    ):
        raise ArtifactIntegrityError(
            "production Deep and Hybrid configs differ beyond training variant"
        )
    if _promotion_semantics(hybrid, ignore_variant=False) != _promotion_semantics(
        h3b.settings, ignore_variant=False
    ):
        raise ArtifactIntegrityError(
            "production Hybrid config differs from H3b diagnostic settings"
        )

    objective_settings = _objective_settings(h3b.settings)
    if (
        _objective_settings(deep) != objective_settings
        or _objective_settings(hybrid) != objective_settings
    ):
        raise ArtifactIntegrityError("production objective settings differ from H3b diagnostics")
    return objective_settings


def _git_output(repository_root: Path, arguments: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        command = "git " + " ".join(arguments)
        raise ArtifactIntegrityError(f"promotion Git command failed: {command}") from error
    return result.stdout.strip()


def _relative_production_config_path(repository_root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(repository_root)
    except ValueError as error:
        raise ArtifactIntegrityError("production config is outside the repository") from error
    parts = relative.parts
    if not any(
        parts[index : index + 2] == ("configs", "production") for index in range(len(parts))
    ):
        raise ArtifactIntegrityError("promotion config is not under configs/production")
    return relative.as_posix()


def _require_frozen_production_commit(repository_root: Path) -> str:
    if not repository_root.is_dir():
        raise ArtifactIntegrityError("promotion repository root does not exist")
    if _git_output(repository_root, ("status", "--porcelain", "--untracked-files=normal")):
        raise ArtifactIntegrityError("promotion requires a clean Git worktree")
    try:
        upstream_ref = _git_output(
            repository_root,
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
        )
        upstream_commit = _git_output(repository_root, ("rev-parse", "@{u}"))
    except ArtifactIntegrityError as error:
        raise ArtifactIntegrityError(
            "promotion requires a pushed branch with a configured upstream"
        ) from error
    production_commit = _git_output(repository_root, ("rev-parse", "HEAD"))
    if not is_git_commit_sha(production_commit) or upstream_commit != production_commit:
        raise ArtifactIntegrityError(
            f"promotion branch {upstream_ref!r} is not synchronized with HEAD"
        )
    return production_commit


def _validate_production_git(
    *,
    repository_root: Path,
    diagnostic_commit: str,
    config_paths: tuple[Path, Path],
) -> str:
    production_commit = _require_frozen_production_commit(repository_root)
    try:
        _git_output(
            repository_root,
            ("merge-base", "--is-ancestor", diagnostic_commit, production_commit),
        )
    except ArtifactIntegrityError as error:
        raise ArtifactIntegrityError(
            "diagnostic commit is not an ancestor of production HEAD"
        ) from error
    allowed_paths = {
        _relative_production_config_path(repository_root, path) for path in config_paths
    }
    if len(allowed_paths) != 2:
        raise ArtifactIntegrityError("Deep and Hybrid production configs must be distinct")
    changed_paths = {
        path
        for path in _git_output(
            repository_root,
            (
                "diff",
                "--name-only",
                "--no-renames",
                f"{diagnostic_commit}..{production_commit}",
            ),
        ).splitlines()
        if path
    }
    if changed_paths != allowed_paths:
        raise ArtifactIntegrityError(
            "promotion Git diff must contain exactly the two production config paths"
        )
    return production_commit


def publish_r4_promotion(
    destination: Path,
    *,
    selection_report: Path,
    hybrid_run_id: str,
    deep_config: Path,
    hybrid_config: Path,
    artifact_root: Path | None = None,
    repository_root: Path | None = None,
) -> R4PromotionReport:
    """Derive and publish the one immutable R4 promotion receipt.

    The operator supplies only the selected R3 report, H3b run ID, and reviewed
    production configurations.  All promotion-critical SHA, lineage, commit,
    feature, objective, and victory evidence is strict-loaded from those roots.
    """
    selection_path = selection_report.resolve()
    derived_artifact_root = _artifact_root_from_selection_report(selection_path)
    root = artifact_root.resolve() if artifact_root is not None else derived_artifact_root
    if root != derived_artifact_root:
        _require_path_within(root, selection_path, description="R3 selection report")
        if _artifact_root_from_selection_report(selection_path) != root:
            raise ArtifactIntegrityError("R3 selection report does not belong to artifact_root")
    try:
        selection_artifact = load_deep_ablation_artifact(selection_path.parent)
    except ArtifactIntegrityError:
        raise
    if selection_artifact.report_path.resolve() != selection_path:
        raise ArtifactIntegrityError("R3 selection report path is not the verified artifact report")
    selection = selection_artifact.report
    if (
        selection.diagnostic_pause
        or selection.selected_run_id is None
        or selection.selected_feature_selection is None
        or selection.comparison_signature_sha256 is None
    ):
        raise ArtifactIntegrityError("R3 selection report has no promotable Deep configuration")
    if not isinstance(selection.lineage, ArtifactLineageV5):
        raise ArtifactIntegrityError("R3 selection report requires six-field lineage")

    selected_deep = _load_run_evidence(
        root,
        selection.selected_run_id,
        expected_variant=TrainingVariant.DEEP_ONLY,
    )
    h3b = _load_run_evidence(root, hybrid_run_id, expected_variant=TrainingVariant.HYBRID)
    if (
        selected_deep.lineage != selection.lineage
        or h3b.lineage != selection.lineage
        or selected_deep.git_commit != selection.diagnostic_git_commit
        or h3b.git_commit != selection.diagnostic_git_commit
        or selected_deep.settings.comparison_signature_sha256()
        != selection.comparison_signature_sha256
        or h3b.settings.comparison_signature_sha256() != selection.comparison_signature_sha256
    ):
        raise ArtifactIntegrityError("diagnostic run evidence differs from the R3 selection report")
    if (
        h3b.settings.train.r3_selection_artifact_sha256 != selection.artifact_sha256
        or h3b.settings.train.r3_selected_deep_run_id != selected_deep.run_id
        or h3b.settings.train.r3_feature_selection_mode != "selection_artifact"
        or h3b.settings.model.use_user_id_embedding
        != selection.selected_feature_selection.use_user_id_embedding
        or h3b.settings.model.use_price_features
        != selection.selected_feature_selection.use_price_features
    ):
        raise ArtifactIntegrityError("H3b run does not bind the selected R3 Deep configuration")

    evaluation = load_evaluation_artifacts(
        h3b.run_dir,
        expected_split=SplitName.VAL,
        expected_hybrid_run_id=h3b.run_id,
        expected_deep_run_id=selected_deep.run_id,
        expected_comparison_signature=h3b.settings.comparison_signature_sha256(),
        expected_lineage=selection.lineage,
    )
    if (
        not evaluation.manifest.passed
        or not evaluation.victory_matrix.all_passed
        or evaluation.manifest.hybrid_checkpoint_sha256 != h3b.checkpoint_manifest.content_sha256
        or evaluation.manifest.deep_checkpoint_sha256
        != selected_deep.checkpoint_manifest.content_sha256
        or not h3b.state.validation_gate_passed
        or h3b.state.paired_run_id != selected_deep.run_id
        or h3b.state.validation_victory_matrix_path is None
        or Path(h3b.state.validation_victory_matrix_path).resolve()
        != evaluation.victory_matrix_path.resolve()
    ):
        raise ArtifactIntegrityError("H3b has no validated, passing, hybrid-owned VAL victory")

    deep_config_path, deep_settings = _load_production_config(
        deep_config, expected_variant=TrainingVariant.DEEP_ONLY
    )
    hybrid_config_path, hybrid_settings = _load_production_config(
        hybrid_config, expected_variant=TrainingVariant.HYBRID
    )
    objective_settings = _validate_production_configs(
        deep=deep_settings,
        hybrid=hybrid_settings,
        selection_sha256=selection.artifact_sha256,
        selected_deep_run_id=selected_deep.run_id,
        features=selection.selected_feature_selection,
        comparison_signature_sha256=selection.comparison_signature_sha256,
        h3b=h3b,
    )

    repository = (repository_root or _DEFAULT_REPOSITORY_ROOT).resolve()
    production_commit = _validate_production_git(
        repository_root=repository,
        diagnostic_commit=selection.diagnostic_git_commit,
        config_paths=(deep_config_path, hybrid_config_path),
    )
    document: dict[str, Any] = {
        "schema_version": "5.2.0",
        "deep_selection_report_sha256": _sha256_file(selection_path),
        "selected_deep_run_id": selected_deep.run_id,
        "selected_deep_checkpoint_sha256": selected_deep.checkpoint_manifest.content_sha256,
        "h3b_hybrid_run_id": h3b.run_id,
        "h3b_hybrid_checkpoint_sha256": h3b.checkpoint_manifest.content_sha256,
        "h3b_victory_matrix_sha256": evaluation.victory_matrix_sha256,
        "lineage": selection.lineage.model_dump(mode="json"),
        "diagnostic_git_commit": selection.diagnostic_git_commit,
        "production_git_commit": production_commit,
        "deep_config_sha256": _sha256_file(deep_config_path),
        "hybrid_config_sha256": _sha256_file(hybrid_config_path),
        "feature_selection": _selection_features(selection.selected_feature_selection),
        "objective_settings": objective_settings,
    }
    document["artifact_sha256"] = canonical_r4_promotion_sha(document)
    report = R4PromotionReport.model_validate(document)
    if destination.exists():
        existing = load_r4_promotion(destination)
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
