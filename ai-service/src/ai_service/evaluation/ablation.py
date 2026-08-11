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
from typing import Any

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
    eligible: bool


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
    git_commit: object
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


def compare_deep_ablations(
    *,
    control_run_id: str,
    control: EvaluationResult,
    candidates: Mapping[str, tuple[str, EvaluationResult]],
    random_per_user_gauc: np.ndarray,
    bootstrap_samples: int,
    minimum_control_gauc: float,
) -> tuple[DeepAblationDecision, dict[str, np.ndarray]]:
    """Select one materially better Deep ablation or issue a diagnostic pause."""
    if len(candidates) != 3 or control_run_id in candidates:
        raise DataIntegrityError("R3 comparison requires one control and exactly three candidates")
    user_ids = np.asarray(control.user_ids, dtype=np.int64)
    control_gauc = _metric_vector(control.per_user_gauc, user_ids, "control GAUC")
    random_gauc = _metric_vector(random_per_user_gauc, user_ids, "random GAUC")
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
        "random_gauc": random_gauc,
    }
    for run_id, (config_name, result) in sorted(candidates.items()):
        candidate_gauc = _metric_vector(result.per_user_gauc, user_ids, f"{run_id} GAUC")
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
        catastrophic = float(result.report.gauc) < 0.50
        eligible = not catastrophic and vs_control.lower > 0.0 and vs_random.lower > 0.0
        if catastrophic:
            pause_reasons.append(f"{run_id} GAUC is below catastrophic threshold 0.50")
        arrays[f"{run_id}_gauc"] = candidate_gauc
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
                eligible=eligible,
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
                record.gauc,
                record.ndcg_at_k,
                record.hr_at_k,
                record.config_name,
            ),
        ).run_id
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
) -> DeepAblationArtifact:
    if not _is_sha256(diagnostic_signature):
        raise ArtifactIntegrityError("diagnostic signature must be a lowercase SHA-256")
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
            "per_user_metrics_sha256": _file_sha256(metrics_path),
        }
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
    )


def require_selected_r3_pair(
    *,
    artifact_root: Path,
    selected_deep_run_id: str,
    hybrid_flags: tuple[bool, bool],
    deep_flags: tuple[bool, bool],
) -> None:
    if hybrid_flags != deep_flags:
        raise ArtifactIntegrityError("R3 Hybrid flags must match the selected Deep ablation")
    matches: list[DeepAblationReport] = []
    for path in sorted((artifact_root.resolve() / "diagnostics" / "r3").glob("*/report.json")):
        report = load_deep_ablation_artifact(path.parent).report
        if report.selected_run_id == selected_deep_run_id and not report.diagnostic_pause:
            matches.append(report)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            "paired R3 evaluation requires exactly one immutable report selecting the Deep run"
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
        "random_gauc",
        *(f"{candidate.run_id}_gauc" for candidate in report.candidates),
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
    "canonical_ablation_report_sha",
    "compare_deep_ablations",
    "load_deep_ablation_artifact",
    "publish_deep_ablation_artifact",
    "require_hybrid_diagnostic_signal",
    "require_selected_r3_pair",
    "run_deep_ablation_comparison",
]
