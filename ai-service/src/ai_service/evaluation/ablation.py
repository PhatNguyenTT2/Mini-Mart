"""Immutable Deep-only ablation comparison for the R3 diagnostic pause."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
from pydantic import BaseModel, Field, model_validator

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, RunStatus, SplitName
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import (
    ArtifactIntegrityError,
    ConfigurationError,
    DataIntegrityError,
    VictoryGateError,
)
from ai_service.evaluation.baselines import evaluate_random_baselines
from ai_service.evaluation.full_catalog import (
    EvaluationResult,
    FullCatalogEvaluator,
    prepare_split,
)
from ai_service.evaluation.metrics import paired_bootstrap_delta
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


class R3FeatureSelection(BaseModel):
    use_user_id_embedding: bool
    use_price_features: bool


class R3ArtifactLineage(BaseModel):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SelectedR3Configuration(BaseModel):
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_diagnostic_run_id: str = Field(min_length=1)
    selected_config_name: str = Field(min_length=1)
    feature_selection: R3FeatureSelection
    lineage: R3ArtifactLineage
    diagnostic_git_commit: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


class DeepAblationCandidate(BaseModel):
    run_id: str = Field(min_length=1)
    config_name: str = Field(min_length=1)
    gauc: float = Field(ge=0.0, le=1.0)
    hr_at_k: float = Field(ge=0.0, le=1.0)
    ndcg_at_k: float = Field(ge=0.0, le=1.0)
    gauc_delta_vs_control: float
    gauc_ci_lower_vs_control: float
    gauc_ci_upper_vs_control: float
    gauc_ci_lower_vs_random: float
    hr_delta_vs_control: float
    hr_ci_lower_vs_control: float
    hr_ci_upper_vs_control: float
    ndcg_delta_vs_control: float
    ndcg_ci_lower_vs_control: float
    ndcg_ci_upper_vs_control: float
    eligible: bool
    feature_selection: R3FeatureSelection


class DeepAblationDecision(BaseModel):
    control_run_id: str = Field(min_length=1)
    minimum_control_gauc: float = Field(ge=0.5, le=1.0)
    candidates: tuple[DeepAblationCandidate, ...]
    selected_run_id: str | None
    diagnostic_pause: bool
    pause_reasons: tuple[str, ...]

    @model_validator(mode="after")
    def selection_is_consistent(self) -> DeepAblationDecision:
        if len(self.candidates) != 3:
            raise ValueError("R3 requires exactly three Deep ablation candidates")
        if len({candidate.run_id for candidate in self.candidates}) != 3:
            raise ValueError("R3 candidate run IDs must be distinct")
        if self.control_run_id in {candidate.run_id for candidate in self.candidates}:
            raise ValueError("R3 control run ID must differ from every candidate")
        eligible = {candidate.run_id for candidate in self.candidates if candidate.eligible}
        if self.diagnostic_pause:
            if self.selected_run_id is not None or not self.pause_reasons:
                raise ValueError("diagnostic pause requires reasons and no selection")
        elif self.selected_run_id not in eligible or self.pause_reasons:
            raise ValueError("successful diagnostic report must select one eligible candidate")
        return self


class DeepAblationReport(DeepAblationDecision):
    per_user_metrics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostic_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostic_git_commit: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
    lineage: R3ArtifactLineage
    selected_config_name: str | None
    selected_feature_selection: R3FeatureSelection | None

    @model_validator(mode="after")
    def selected_configuration_is_consistent(self) -> DeepAblationReport:
        if self.diagnostic_pause:
            if self.selected_config_name is not None or self.selected_feature_selection is not None:
                raise ValueError("paused R3 report cannot contain a selected configuration")
        else:
            selected = next(
                (
                    candidate
                    for candidate in self.candidates
                    if candidate.run_id == self.selected_run_id
                ),
                None,
            )
            if selected is None or self.selected_config_name != selected.config_name:
                raise ValueError("R3 selected configuration does not match the selected candidate")
            if self.selected_feature_selection != selected.feature_selection:
                raise ValueError("R3 selected feature flags do not match the selected candidate")
        return self


@dataclass(frozen=True)
class DeepAblationArtifact:
    directory: Path
    report: DeepAblationReport
    metrics_path: Path
    report_path: Path


@dataclass(frozen=True)
class DeepAblationRun:
    run_id: str
    settings: Settings
    lifecycle_status: RunStatus
    git_commit: str
    lineage: dict[str, str]
    snapshot: Snapshot
    embeddings: np.ndarray
    rule_store: RuleStore
    model: HybridTwoTowerModel


def canonical_ablation_report_sha(document: Mapping[str, object]) -> str:
    payload = dict(document)
    payload.pop("artifact_sha256", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _feature_selection_for_config(config_name: str) -> R3FeatureSelection:
    values = {
        "deep-control": (True, True),
        "deep-no-user-id": (False, True),
        "deep-no-price": (True, False),
        "deep-no-price-no-user-id": (False, False),
    }
    try:
        use_user_id_embedding, use_price_features = values[config_name]
    except KeyError as error:
        raise DataIntegrityError(f"unknown R3 feature configuration: {config_name}") from error
    return R3FeatureSelection(
        use_user_id_embedding=use_user_id_embedding,
        use_price_features=use_price_features,
    )


def compare_deep_ablations(
    *,
    control_run_id: str,
    control: EvaluationResult,
    candidates: Mapping[str, tuple[str, EvaluationResult]],
    random_per_user_gauc: np.ndarray,
    random_per_user_hr: np.ndarray,
    random_per_user_ndcg: np.ndarray,
    bootstrap_samples: int,
    minimum_control_gauc: float,
    gauc_guardrail_delta: float = 0.0,
    hr_guardrail_delta: float = 0.0,
    ndcg_guardrail_delta: float = 0.0,
    minimum_candidate_gauc: float = 0.55,
    selection_gauc_floor: float = 0.75,
    selection_hr_floor: float = 0.15,
    selection_ndcg_floor: float = 0.08,
) -> tuple[DeepAblationDecision, dict[str, np.ndarray]]:
    """Select one materially better Deep ablation or issue a diagnostic pause."""
    if len(candidates) != 3 or control_run_id in candidates:
        raise DataIntegrityError("R3 comparison requires one control and exactly three candidates")
    user_ids = np.asarray(control.user_ids, dtype=np.int64)
    control_gauc = _metric_vector(control.per_user_gauc, user_ids, "control GAUC")
    control_hr = _metric_vector(control.per_user_hr, user_ids, "control HR")
    control_ndcg = _metric_vector(control.per_user_ndcg, user_ids, "control NDCG")
    random_gauc = _metric_vector(random_per_user_gauc, user_ids, "random GAUC")
    random_hr = _metric_vector(random_per_user_hr, user_ids, "random HR")
    random_ndcg = _metric_vector(random_per_user_ndcg, user_ids, "random NDCG")
    control_random = paired_bootstrap_delta(
        control_gauc,
        random_gauc,
        samples=bootstrap_samples,
    )
    pause_reasons: list[str] = []
    if not 0.5 <= minimum_control_gauc <= 1.0:
        raise DataIntegrityError("minimum control GAUC must be within [0.5,1.0]")
    if float(control.report.gauc) < minimum_control_gauc:
        pause_reasons.append(f"control Deep GAUC is below {minimum_control_gauc:g}")
    if control_random.lower <= 0.0:
        pause_reasons.append("control Deep is not clearly better than Random")

    records: list[DeepAblationCandidate] = []
    arrays: dict[str, np.ndarray] = {
        "user_ids": user_ids,
        "control_gauc": control_gauc,
        "control_hr": control_hr,
        "control_ndcg": control_ndcg,
        "random_gauc": random_gauc,
        "random_hr": random_hr,
        "random_ndcg": random_ndcg,
    }
    for run_id, (config_name, result) in sorted(candidates.items()):
        candidate_gauc = _metric_vector(result.per_user_gauc, user_ids, f"{run_id} GAUC")
        candidate_hr = _metric_vector(result.per_user_hr, user_ids, f"{run_id} HR")
        candidate_ndcg = _metric_vector(result.per_user_ndcg, user_ids, f"{run_id} NDCG")
        vs_control = paired_bootstrap_delta(
            candidate_gauc,
            control_gauc,
            samples=bootstrap_samples,
        )
        vs_random = paired_bootstrap_delta(
            candidate_gauc,
            random_gauc,
            samples=bootstrap_samples,
        )
        vs_control_hr = paired_bootstrap_delta(candidate_hr, control_hr, samples=bootstrap_samples)
        vs_control_ndcg = paired_bootstrap_delta(
            candidate_ndcg, control_ndcg, samples=bootstrap_samples
        )
        catastrophic = float(result.report.gauc) < 0.50
        candidate_is_clear = float(result.report.gauc) >= minimum_candidate_gauc
        noninferior = (
            vs_control.lower >= gauc_guardrail_delta
            and vs_control_hr.lower >= hr_guardrail_delta
            and vs_control_ndcg.lower >= ndcg_guardrail_delta
        )
        any_metric_better = (
            vs_control.lower > 0.0 or vs_control_hr.lower > 0.0 or vs_control_ndcg.lower > 0.0
        )
        eligible = (
            not catastrophic
            and candidate_is_clear
            and vs_random.lower > 0.0
            and noninferior
            and any_metric_better
        )
        if catastrophic:
            pause_reasons.append(f"{run_id} GAUC is below catastrophic threshold 0.50")
        arrays[f"{run_id}_gauc"] = candidate_gauc
        arrays[f"{run_id}_hr"] = candidate_hr
        arrays[f"{run_id}_ndcg"] = candidate_ndcg
        records.append(
            DeepAblationCandidate(
                run_id=run_id,
                config_name=config_name,
                gauc=float(result.report.gauc),
                hr_at_k=float(result.report.hr_at_k),
                ndcg_at_k=float(result.report.ndcg_at_k),
                gauc_delta_vs_control=vs_control.mean_delta,
                gauc_ci_lower_vs_control=vs_control.lower,
                gauc_ci_upper_vs_control=vs_control.upper,
                gauc_ci_lower_vs_random=vs_random.lower,
                hr_delta_vs_control=vs_control_hr.mean_delta,
                hr_ci_lower_vs_control=vs_control_hr.lower,
                hr_ci_upper_vs_control=vs_control_hr.upper,
                ndcg_delta_vs_control=vs_control_ndcg.mean_delta,
                ndcg_ci_lower_vs_control=vs_control_ndcg.lower,
                ndcg_ci_upper_vs_control=vs_control_ndcg.upper,
                eligible=eligible,
                feature_selection=_feature_selection_for_config(config_name),
            )
        )

    eligible_records = [record for record in records if record.eligible]
    if not eligible_records:
        pause_reasons.append("no ablation has positive paired GAUC CI versus control")
    diagnostic_pause = bool(pause_reasons)
    selected = None
    if not diagnostic_pause:
        selected = max(
            eligible_records,
            key=lambda record: (
                min(
                    record.gauc / selection_gauc_floor,
                    record.hr_at_k / selection_hr_floor,
                    record.ndcg_at_k / selection_ndcg_floor,
                ),
                record.gauc,
                record.ndcg_at_k,
                record.hr_at_k,
            ),
        ).run_id
        selected_record = next(record for record in eligible_records if record.run_id == selected)
        tied = [
            record
            for record in eligible_records
            if (
                min(
                    record.gauc / selection_gauc_floor,
                    record.hr_at_k / selection_hr_floor,
                    record.ndcg_at_k / selection_ndcg_floor,
                ),
                record.gauc,
                record.ndcg_at_k,
                record.hr_at_k,
            )
            == (
                min(
                    selected_record.gauc / selection_gauc_floor,
                    selected_record.hr_at_k / selection_hr_floor,
                    selected_record.ndcg_at_k / selection_ndcg_floor,
                ),
                selected_record.gauc,
                selected_record.ndcg_at_k,
                selected_record.hr_at_k,
            )
        ]
        selected = min(tied, key=lambda record: record.config_name).run_id
    decision = DeepAblationDecision(
        control_run_id=control_run_id,
        minimum_control_gauc=minimum_control_gauc,
        candidates=tuple(records),
        selected_run_id=selected,
        diagnostic_pause=diagnostic_pause,
        pause_reasons=tuple(sorted(set(pause_reasons))),
    )
    return decision, arrays


def publish_deep_ablation_artifact(
    root: Path,
    *,
    diagnostic_signature: str,
    report: DeepAblationDecision,
    metrics: Mapping[str, np.ndarray],
    diagnostic_git_commit: str,
    lineage: Mapping[str, str],
) -> DeepAblationArtifact:
    if not _is_sha256(diagnostic_signature):
        raise ArtifactIntegrityError("diagnostic signature must be a lowercase SHA-256")
    if not _is_git_commit(diagnostic_git_commit):
        raise ArtifactIntegrityError("diagnostic Git commit is invalid")
    try:
        provenance = R3ArtifactLineage(
            snapshot_sha256=str(lineage["snapshot"]),
            embedding_sha256=str(lineage["embedding"]),
            rule_sha256=str(lineage["rules"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("R3 diagnostic lineage is invalid") from error
    validated_metrics = _validate_ablation_metrics(report, metrics)
    destination = root.resolve() / "diagnostics" / "r3" / diagnostic_signature
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ArtifactIntegrityError(f"Deep ablation artifact already exists: {destination}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{diagnostic_signature}-", dir=destination.parent))
    try:
        metrics_path = temporary / "per-user-metrics.npz"
        np.savez_compressed(metrics_path, **validated_metrics)  # type: ignore[arg-type]
        _fsync_file(metrics_path)
        document = {
            **report.model_dump(mode="json"),
            "diagnostic_signature_sha256": diagnostic_signature,
            "diagnostic_git_commit": diagnostic_git_commit,
            "lineage": provenance.model_dump(mode="json"),
            "selected_config_name": None,
            "selected_feature_selection": None,
            "per_user_metrics_sha256": _file_sha256(metrics_path),
        }
        if report.selected_run_id is not None:
            selected_candidate = next(
                candidate
                for candidate in report.candidates
                if candidate.run_id == report.selected_run_id
            )
            document["selected_config_name"] = selected_candidate.config_name
            document["selected_feature_selection"] = (
                selected_candidate.feature_selection.model_dump(mode="json")
            )
        document["artifact_sha256"] = canonical_ablation_report_sha(document)
        published_report = DeepAblationReport.model_validate(document)
        report_path = temporary / "report.json"
        report_path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        _fsync_file(report_path)
        load_deep_ablation_artifact(temporary)
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    artifact = load_deep_ablation_artifact(destination)
    if artifact.report != published_report:
        raise ArtifactIntegrityError("published Deep ablation report changed after rename")
    return artifact


def run_deep_ablation_comparison(
    runs: tuple[DeepAblationRun, DeepAblationRun, DeepAblationRun, DeepAblationRun],
    *,
    artifact_root: Path,
    device: torch.device,
) -> DeepAblationArtifact:
    """Validate, evaluate and publish one complete R3 comparison."""
    control = runs[0]
    if len({run.run_id for run in runs}) != 4:
        raise ConfigurationError("R3 requires four distinct Deep run IDs")
    if any(run.settings.train.seed != 42 for run in runs):
        raise ArtifactIntegrityError("R3 Deep ablations require seed 42")
    if any(run.settings.train.campaign_stage != "diagnostic" for run in runs):
        raise ArtifactIntegrityError("R3 Deep ablations require diagnostic campaign configs")
    if any(run.settings.train.r3_selection_artifact_sha256 is not None for run in runs):
        raise ArtifactIntegrityError("R3 diagnostics cannot carry a production selection receipt")
    if any(run.lifecycle_status is not RunStatus.TRAINING for run in runs):
        raise ArtifactIntegrityError("R3 Deep ablations require completed TRAINING lifecycles")
    if any(run.git_commit != control.git_commit for run in runs[1:]):
        raise ArtifactIntegrityError("R3 Deep ablations require one frozen source revision")
    for run in runs[1:]:
        if run.lineage != control.lineage:
            raise ArtifactIntegrityError("R3 Deep ablations require identical v4 lineage")
        if run.settings.eval.model_dump(mode="json") != control.settings.eval.model_dump(
            mode="json"
        ):
            raise ArtifactIntegrityError("R3 Deep ablations require identical evaluation settings")
        if _fixed_settings(run.settings) != _fixed_settings(control.settings):
            raise ArtifactIntegrityError("R3 configs may differ only by neural feature flags")

    expected_flags = {
        (True, True): "deep-control",
        (False, True): "deep-no-user-id",
        (True, False): "deep-no-price",
        (False, False): "deep-no-price-no-user-id",
    }
    actual_flags = {
        (run.settings.model.use_user_id_embedding, run.settings.model.use_price_features): run
        for run in runs
    }
    if set(actual_flags) != set(expected_flags) or actual_flags[(True, True)] is not control:
        raise ArtifactIntegrityError("R3 requires the exact control and three feature ablations")

    prepared = prepare_split(control.snapshot, SplitName.VAL)
    evaluations: dict[str, EvaluationResult] = {}
    for run in runs:
        evaluator = FullCatalogEvaluator(run.settings, run.embeddings, run.rule_store)
        evaluations[run.run_id] = evaluator.evaluate(
            run.model,
            run.snapshot,
            prepared_split=prepared,
            k=run.settings.eval.k,
            variant=ModelVariant.DEEP_ONLY,
            device=device,
        )
    random_evaluator = FullCatalogEvaluator(
        control.settings,
        control.embeddings,
        control.rule_store,
    )
    random_results = evaluate_random_baselines(
        evaluator=random_evaluator,
        snapshot=control.snapshot,
        prepared_split=prepared,
        settings=control.settings,
    )
    random_gauc = np.mean(
        np.stack([result.per_user_gauc for result in random_results]),
        axis=0,
    )
    random_hr = np.mean(
        np.stack([result.per_user_hr for result in random_results]),
        axis=0,
    )
    random_ndcg = np.mean(
        np.stack([result.per_user_ndcg for result in random_results]),
        axis=0,
    )
    candidate_results = {
        run.run_id: (
            expected_flags[
                (run.settings.model.use_user_id_embedding, run.settings.model.use_price_features)
            ],
            evaluations[run.run_id],
        )
        for run in runs[1:]
    }
    report, metrics = compare_deep_ablations(
        control_run_id=control.run_id,
        control=evaluations[control.run_id],
        candidates=candidate_results,
        random_per_user_gauc=np.asarray(random_gauc, dtype=np.float64),
        random_per_user_hr=np.asarray(random_hr, dtype=np.float64),
        random_per_user_ndcg=np.asarray(random_ndcg, dtype=np.float64),
        bootstrap_samples=control.settings.eval.bootstrap_samples,
        minimum_control_gauc=control.settings.eval.deep_clear_random_gauc,
    )
    signature_document = {
        "run_ids": [run.run_id for run in runs],
        "git_commit": control.git_commit,
        "lineage": control.lineage,
        "evaluation": control.settings.eval.model_dump(mode="json"),
    }
    diagnostic_signature = hashlib.sha256(
        json.dumps(signature_document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return publish_deep_ablation_artifact(
        artifact_root,
        diagnostic_signature=diagnostic_signature,
        report=report,
        metrics=metrics,
        diagnostic_git_commit=control.git_commit,
        lineage=control.lineage,
    )


def require_selected_r3_pair(
    *,
    artifact_root: Path,
    selected_deep_run_id: str | None = None,
    hybrid_flags: tuple[bool, bool],
    deep_flags: tuple[bool, bool],
    campaign_stage: Literal["diagnostic", "production"] = "diagnostic",
    selection_artifact_sha256: str | None = None,
    lineage: Mapping[str, str] | None = None,
) -> SelectedR3Configuration:
    if hybrid_flags != deep_flags:
        raise ArtifactIntegrityError("R3 Hybrid flags must match the selected Deep ablation")
    expected_features = R3FeatureSelection(
        use_user_id_embedding=deep_flags[0],
        use_price_features=deep_flags[1],
    )
    matches: list[DeepAblationArtifact] = []
    for path in sorted((artifact_root.resolve() / "diagnostics" / "r3").glob("*/report.json")):
        artifact = load_deep_ablation_artifact(path.parent)
        report = artifact.report
        if report.diagnostic_pause or report.selected_feature_selection != expected_features:
            continue
        if campaign_stage == "production":
            if (
                selection_artifact_sha256 is not None
                and artifact.report.artifact_sha256 == selection_artifact_sha256
            ):
                matches.append(artifact)
        elif report.selected_run_id == selected_deep_run_id:
            matches.append(artifact)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            "paired R3 evaluation requires exactly one immutable report selecting "
            "the feature configuration"
        )
    report = matches[0].report
    if lineage is not None:
        expected_lineage = {
            "snapshot": report.lineage.snapshot_sha256,
            "embedding": report.lineage.embedding_sha256,
            "rules": report.lineage.rule_sha256,
        }
        if dict(lineage) != expected_lineage:
            raise ArtifactIntegrityError(
                "R3 selection lineage does not match the current artifacts"
            )
    if report.selected_run_id is None or report.selected_config_name is None:
        raise ArtifactIntegrityError("R3 selection report has no selected configuration")
    if report.selected_feature_selection is None:
        raise ArtifactIntegrityError("R3 selection report has no selected feature flags")
    return SelectedR3Configuration(
        artifact_sha256=report.artifact_sha256,
        selected_diagnostic_run_id=report.selected_run_id,
        selected_config_name=report.selected_config_name,
        feature_selection=report.selected_feature_selection,
        lineage=report.lineage,
        diagnostic_git_commit=report.diagnostic_git_commit,
    )


def require_hybrid_diagnostic_signal(
    history_path: Path,
    *,
    best_epoch: int,
    minimum_rule_row_rate: float,
    minimum_wide_deep_ratio: float,
    minimum_top_k_change_rate: float,
) -> None:
    try:
        rows: list[dict[str, Any]] = [
            json.loads(line)
            for line in history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("Hybrid diagnostic history cannot be read") from error
    if not rows:
        raise ArtifactIntegrityError("Hybrid diagnostic history is empty")
    epoch_one = next((row for row in rows if int(row.get("epoch", -1)) == 1), None)
    selected = next((row for row in rows if int(row.get("epoch", -1)) == best_epoch), None)
    if epoch_one is None or selected is None:
        raise ArtifactIntegrityError("Hybrid diagnostic history lacks epoch 1 or selected epoch")
    required = {
        "wide_gradient_norm": epoch_one.get("wide_gradient_norm"),
        "rows_with_any_rule_rate": selected.get("rows_with_any_rule_rate"),
        "wide_to_deep_logit_rms_ratio": selected.get("wide_to_deep_logit_rms_ratio"),
        "hybrid_deep_top_k_change_rate": selected.get("hybrid_deep_top_k_change_rate"),
    }
    if any(value is None for value in required.values()):
        raise ArtifactIntegrityError("Hybrid diagnostic history is missing required values")
    try:
        values = {name: float(value) for name, value in required.items() if value is not None}
    except (TypeError, ValueError) as error:
        raise ArtifactIntegrityError("Hybrid diagnostic history has invalid values") from error
    if not np.isfinite(tuple(values.values())).all():
        raise ArtifactIntegrityError("Hybrid diagnostic history contains NaN or Inf")
    if values["wide_gradient_norm"] <= 0.0:
        raise VictoryGateError("Hybrid epoch-1 Wide gradient is not positive")
    if values["rows_with_any_rule_rate"] < minimum_rule_row_rate:
        raise VictoryGateError("Hybrid training rule-row coverage is below the resolved threshold")
    if values["wide_to_deep_logit_rms_ratio"] < minimum_wide_deep_ratio:
        raise VictoryGateError("Hybrid Wide/Deep RMS ratio is below the resolved threshold")
    if values["hybrid_deep_top_k_change_rate"] < minimum_top_k_change_rate:
        raise VictoryGateError("Hybrid/Deep top-k change rate is below the resolved threshold")


def _fixed_settings(settings: Settings) -> dict[str, object]:
    document = settings.resolved_document()
    model = document["model"]
    if not isinstance(model, dict):
        raise ArtifactIntegrityError("resolved model settings are malformed")
    model.pop("use_user_id_embedding", None)
    model.pop("use_price_features", None)
    return document


def _metric_vector(values: np.ndarray, expected_users: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != expected_users.shape or not np.isfinite(array).all():
        raise DataIntegrityError(f"{name} must be a finite vector aligned to control users")
    return array


def _validate_ablation_metrics(
    report: DeepAblationDecision,
    metrics: Mapping[str, np.ndarray],
) -> dict[str, np.ndarray]:
    expected_keys = {
        "user_ids",
        "control_gauc",
        "control_hr",
        "control_ndcg",
        "random_gauc",
        "random_hr",
        "random_ndcg",
        *(f"{candidate.run_id}_gauc" for candidate in report.candidates),
        *(f"{candidate.run_id}_hr" for candidate in report.candidates),
        *(f"{candidate.run_id}_ndcg" for candidate in report.candidates),
    }
    if set(metrics) != expected_keys:
        raise ArtifactIntegrityError("Deep ablation metrics have unexpected keys")
    users = np.asarray(metrics["user_ids"])
    if (
        users.dtype != np.int64
        or users.ndim != 1
        or len(users) == 0
        or np.any(users <= 0)
        or np.any(np.diff(users) <= 0)
    ):
        raise ArtifactIntegrityError("Deep ablation user IDs must be sorted unique int64")
    validated = {"user_ids": users.copy()}
    for key in sorted(expected_keys - {"user_ids"}):
        values = np.asarray(metrics[key])
        if (
            values.dtype != np.float64
            or values.shape != users.shape
            or not np.isfinite(values).all()
            or np.any(values < 0.0)
            or np.any(values > 1.0)
        ):
            raise ArtifactIntegrityError(
                f"Deep ablation metric {key} must be finite float64 in [0,1]"
            )
        validated[key] = values.copy()
    return validated


def load_deep_ablation_artifact(directory: Path) -> DeepAblationArtifact:
    expected_files = {"report.json", "per-user-metrics.npz"}
    try:
        entries = tuple(directory.iterdir())
        if {path.name for path in entries} != expected_files or any(
            not path.is_file() for path in entries
        ):
            raise ArtifactIntegrityError("Deep ablation artifact file allowlist mismatch")
        report_path = directory / "report.json"
        metrics_path = directory / "per-user-metrics.npz"
        report = DeepAblationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        if canonical_ablation_report_sha(report.model_dump(mode="json")) != report.artifact_sha256:
            raise ArtifactIntegrityError("Deep ablation report canonical SHA mismatch")
        if _file_sha256(metrics_path) != report.per_user_metrics_sha256:
            raise ArtifactIntegrityError("Deep ablation metrics file SHA mismatch")
        with np.load(metrics_path, allow_pickle=False) as source:
            metrics = {key: source[key] for key in source.files}
        _validate_ablation_metrics(report, metrics)
    except ArtifactIntegrityError:
        raise
    except (OSError, ValueError, KeyError) as error:
        raise ArtifactIntegrityError(
            f"Deep ablation artifact cannot be verified: {directory}"
        ) from error
    return DeepAblationArtifact(
        directory=directory,
        report=report,
        metrics_path=metrics_path,
        report_path=report_path,
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_git_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.lower()
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("r+b") as source:
        os.fsync(source.fileno())


__all__ = [
    "DeepAblationArtifact",
    "DeepAblationCandidate",
    "DeepAblationDecision",
    "DeepAblationReport",
    "DeepAblationRun",
    "R3ArtifactLineage",
    "R3FeatureSelection",
    "SelectedR3Configuration",
    "canonical_ablation_report_sha",
    "compare_deep_ablations",
    "load_deep_ablation_artifact",
    "publish_deep_ablation_artifact",
    "require_hybrid_diagnostic_signal",
    "require_selected_r3_pair",
    "run_deep_ablation_comparison",
]
