"""Typed immutable three-seed validation/test release gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ai_service.artifact_io import canonical_json_sha256, immutable_write_json
from ai_service.config import MODEL_SCHEMA_VERSION, Settings, load_resolved_settings
from ai_service.contracts import (
    EVALUATION_SCHEMA_VERSION,
    AggregateReleaseReport,
    ArtifactLineage,
    ArtifactLineageInput,
    ArtifactLineageV5,
    CheckpointManifest,
    MetricGateResult,
    PipelineState,
    RunStatus,
    SplitName,
    TrainingVariant,
    artifact_lineage_model,
)
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.metrics import paired_bootstrap_delta
from ai_service.evaluation.report import EvaluationArtifactSet, load_evaluation_artifacts
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle


@dataclass(frozen=True)
class FinalistRunRecord:
    run_dir: Path
    lifecycle: RunLifecycle
    settings: Settings
    state: PipelineState
    checkpoint_manifest: CheckpointManifest
    seed: int
    variant: TrainingVariant
    lineage: ArtifactLineage | ArtifactLineageV5
    git_commit: str


@dataclass(frozen=True)
class FinalistPairRecord:
    hybrid: FinalistRunRecord
    deep: FinalistRunRecord
    evaluation: EvaluationArtifactSet


def _load_finalist_run(run_dir: Path, expected_variant: TrainingVariant) -> FinalistRunRecord:
    lifecycle = RunLifecycle.load(run_dir)
    if lifecycle.status not in {RunStatus.TRAINING, RunStatus.EVALUATED, RunStatus.SEALED}:
        raise DataIntegrityError(f"finalist run is not evaluable: {run_dir.name}")
    settings = load_resolved_settings(run_dir / "resolved-config.json")
    settings.validate_campaign_stage()
    if (
        settings.data.rule_feature_schema_version == "3.0.0"
        and settings.train.campaign_stage != "production"
    ):
        raise DataIntegrityError("release finalists must use production campaign configs")
    if settings.train.training_variant is not expected_variant:
        raise DataIntegrityError(f"run variant mismatch: {run_dir.name}")
    try:
        state = PipelineState.model_validate_json(
            (run_dir / "pipeline-state.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("finalist pipeline state cannot be read") from error
    if state.run_id != run_dir.name or state.training_variant.value != expected_variant.value:
        raise ArtifactIntegrityError("pipeline state finalist identity mismatch")
    if state.checkpoint_path is None:
        raise ArtifactIntegrityError("finalist has no best checkpoint")
    checkpoint_path = Path(state.checkpoint_path)
    if checkpoint_path.name != "best.pt" or checkpoint_path.parent.name != "checkpoints":
        raise ArtifactIntegrityError("finalist checkpoint must be checkpoints/best.pt")
    checkpoint_path = checkpoint_path.resolve()
    if run_dir.resolve() not in checkpoint_path.parents:
        raise ArtifactIntegrityError("finalist checkpoint escapes its run directory")
    try:
        checkpoint_manifest = CheckpointManifest.model_validate_json(
            checkpoint_path.with_suffix(".pt.manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("finalist checkpoint manifest cannot be read") from error
    if checkpoint_manifest.checkpoint_kind != "best" or checkpoint_manifest.run_id != run_dir.name:
        raise ArtifactIntegrityError("finalist checkpoint manifest identity mismatch")
    lineage = artifact_lineage_model(lifecycle.document["lineage"])
    if checkpoint_manifest.parent_sha256 != lineage.as_mapping():
        raise ArtifactIntegrityError("finalist checkpoint lineage mismatch")
    if checkpoint_manifest.model_schema_version != MODEL_SCHEMA_VERSION:
        raise ArtifactIntegrityError("finalist checkpoint schema mismatch")
    if checkpoint_manifest.training_signature_sha256 != settings.training_signature_sha256():
        raise ArtifactIntegrityError("finalist checkpoint training signature mismatch")
    if checkpoint_manifest.comparison_signature_sha256 != settings.comparison_signature_sha256():
        raise ArtifactIntegrityError("finalist checkpoint comparison signature mismatch")
    CheckpointManager.load(
        checkpoint_path,
        model=HybridTwoTowerModel(settings),
        expected_lineage=lineage,
        expected_training_signature=settings.training_signature_sha256(),
        expected_comparison_signature=settings.comparison_signature_sha256(),
        expected_training_variant=expected_variant,
        expected_checkpoint_kind="best",
        expected_model_schema_version=MODEL_SCHEMA_VERSION,
    )
    return FinalistRunRecord(
        run_dir=run_dir,
        lifecycle=lifecycle,
        settings=settings,
        state=state,
        checkpoint_manifest=checkpoint_manifest,
        seed=settings.train.seed,
        variant=expected_variant,
        lineage=lineage,
        git_commit=lifecycle.document["git_commit"],
    )


def _pair_finalists_by_seed(
    hybrid: tuple[FinalistRunRecord, ...],
    deep: tuple[FinalistRunRecord, ...],
    *,
    split: SplitName,
) -> tuple[FinalistPairRecord, ...]:
    if {record.seed for record in hybrid} != {42, 2027, 31415} or {
        record.seed for record in deep
    } != {42, 2027, 31415}:
        raise DataIntegrityError("finalist seeds must be exactly 42, 2027, and 31415")
    hybrid_by_seed = {record.seed: record for record in hybrid}
    deep_by_seed = {record.seed: record for record in deep}
    if set(hybrid_by_seed) != set(deep_by_seed):
        raise DataIntegrityError("Hybrid and Deep finalist seeds do not match")
    pairs: list[FinalistPairRecord] = []
    for seed in (42, 2027, 31415):
        h = hybrid_by_seed[seed]
        d = deep_by_seed[seed]
        if h.state.paired_run_id != d.run_dir.name or d.state.paired_run_id != h.run_dir.name:
            raise DataIntegrityError(f"seed {seed} finalist pair IDs do not match")
        if h.lineage != d.lineage:
            raise ArtifactIntegrityError(f"seed {seed} finalist lineage differs")
        if h.settings.comparison_signature_sha256() != d.settings.comparison_signature_sha256():
            raise ArtifactIntegrityError(f"seed {seed} comparison signature differs")
        if (
            h.settings.train.r3_selection_artifact_sha256
            != d.settings.train.r3_selection_artifact_sha256
        ):
            raise ArtifactIntegrityError(f"seed {seed} R3 selection receipt differs")
        evaluation = load_evaluation_artifacts(
            h.run_dir,
            expected_split=split,
            expected_hybrid_run_id=h.run_dir.name,
            expected_deep_run_id=d.run_dir.name,
            expected_comparison_signature=h.settings.comparison_signature_sha256(),
            expected_lineage=h.lineage,
        )
        if evaluation.victory_matrix.split is not split:
            raise ArtifactIntegrityError(f"seed {seed} evaluation split mismatch")
        if not evaluation.victory_matrix.all_passed:
            raise DataIntegrityError(f"single-seed gate failed for seed {seed}")
        if pairs and not np.array_equal(
            pairs[0].evaluation.metrics["user_ids"], evaluation.metrics["user_ids"]
        ):
            raise DataIntegrityError("finalist evaluation user IDs differ")
        pairs.append(FinalistPairRecord(hybrid=h, deep=d, evaluation=evaluation))
    return tuple(pairs)


def _validate_finalist_set(
    pairs: tuple[FinalistPairRecord, ...],
    *,
    split: SplitName,
    comparison_signature: str,
) -> None:
    """Validate split-dependent lifecycle and shared finalist identity."""
    if len(pairs) != 3 or tuple(pair.hybrid.seed for pair in pairs) != (42, 2027, 31415):
        raise DataIntegrityError("release gate requires exactly three seed-sorted pairs")
    for pair in pairs:
        if pair.evaluation.victory_matrix.split is not split:
            raise ArtifactIntegrityError("finalist evaluation split differs from release split")
        if pair.evaluation.manifest.comparison_signature_sha256 != comparison_signature:
            raise ArtifactIntegrityError("finalist evaluation signature differs from release")
        if split is SplitName.TEST and (
            pair.hybrid.lifecycle.status not in {RunStatus.EVALUATED, RunStatus.SEALED}
            or pair.deep.lifecycle.status not in {RunStatus.EVALUATED, RunStatus.SEALED}
        ):
            raise DataIntegrityError(
                "TEST aggregate requires finalist runs to be EVALUATED or an exact retry"
            )


def _build_aggregate_gates(
    pairs: tuple[FinalistPairRecord, ...],
    *,
    settings: Settings,
) -> tuple[MetricGateResult, ...]:
    """Build strict aggregate dominance and Hybrid-vs-Deep gates."""
    gates: list[MetricGateResult] = []
    metric_settings = (
        ("gauc", settings.eval.aggregate_gauc_min_delta),
        ("hr", settings.eval.aggregate_hr_min_delta),
        ("ndcg", settings.eval.aggregate_ndcg_min_delta),
    )
    competitor_keys = {
        "persona_only": "persona",
        "item_cf": "item_cf",
        "sbert_centroid": "sbert",
        "apriori_only": "apriori",
        "deep_only": "deep",
        "noisy_hybrid": "noisy_hybrid",
        "random": "random",
    }
    for metric, threshold in metric_settings:
        candidate = _aggregate_metric(pairs, f"hybrid_{metric}")
        competitors = {
            name: _aggregate_metric(pairs, f"{prefix}_{metric}")
            for name, prefix in competitor_keys.items()
        }
        strongest_name = max(competitors, key=lambda name: float(competitors[name].mean()))
        gates.append(
            _aggregate_gate(
                f"aggregate_{metric}_domination",
                candidate,
                competitors[strongest_name],
                threshold,
                settings.eval.bootstrap_samples,
                baseline_name=strongest_name,
            )
        )
        gates.append(
            _aggregate_gate(
                f"aggregate_{metric}_vs_deep",
                candidate,
                competitors["deep_only"],
                threshold,
                settings.eval.bootstrap_samples,
                baseline_name="deep_only",
            )
        )
    order = {
        "aggregate_gauc_domination": 0,
        "aggregate_hr_domination": 1,
        "aggregate_ndcg_domination": 2,
        "aggregate_gauc_vs_deep": 3,
        "aggregate_hr_vs_deep": 4,
        "aggregate_ndcg_vs_deep": 5,
    }
    return tuple(sorted(gates, key=lambda gate: order[gate.name]))


def _aggregate_metric(
    pairs: tuple[FinalistPairRecord, ...],
    key: str,
) -> np.ndarray:
    values = [pair.evaluation.metrics[key] for pair in pairs]
    if key.startswith("random_"):
        values = [np.mean(value, axis=0) for value in values]
    return np.asarray(np.mean(values, axis=0), dtype=np.float64)


def _select_validation_winner(
    pairs: tuple[FinalistPairRecord, ...],
) -> FinalistPairRecord:
    """Select by validation GAUC, NDCG, HR, then smaller seed."""
    return max(
        pairs,
        key=lambda pair: (
            pair.hybrid.checkpoint_manifest.best_val_gauc,
            pair.hybrid.checkpoint_manifest.best_val_ndcg_at_k,
            pair.hybrid.checkpoint_manifest.best_val_hr_at_k,
            -pair.hybrid.seed,
        ),
    )


def _aggregate_gate(
    name: str,
    candidate: np.ndarray,
    baseline: np.ndarray,
    threshold: float,
    samples: int,
    *,
    baseline_name: str,
) -> MetricGateResult:
    interval = paired_bootstrap_delta(candidate, baseline, samples=samples, seed=42)
    passed = interval.lower > threshold
    return MetricGateResult(
        name=name,
        passed=passed,
        observed=float(candidate.mean()),
        target=threshold,
        description=f"aggregate {name} CI lower must be >= {threshold:.6f}",
        candidate_name="hybrid",
        baseline_name=baseline_name,
        candidate_mean=float(candidate.mean()),
        baseline_mean=float(baseline.mean()),
        delta_mean=interval.mean_delta,
        ci_lower=interval.lower,
        ci_upper=interval.upper,
        threshold=threshold,
        failure_reason=None if passed else f"aggregate {name} CI lower is not above threshold",
    )


def _report_sha(report: AggregateReleaseReport) -> str:
    document = report.model_dump(mode="json")
    document.pop("artifact_sha256", None)
    return canonical_json_sha256(document)


def _build_release_report(
    *,
    split: SplitName,
    pairs: tuple[FinalistPairRecord, ...],
    selected: FinalistPairRecord,
    gates: tuple[MetricGateResult, ...],
    comparison_signature: str,
    lineage: ArtifactLineage | ArtifactLineageV5,
) -> AggregateReleaseReport:
    """Build a fully validated report with canonical artifact SHA."""
    provisional = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "split": split,
        "passed": all(gate.passed for gate in gates),
        "comparison_signature_sha256": comparison_signature,
        "hybrid_run_ids": tuple(pair.hybrid.run_dir.name for pair in pairs),
        "deep_run_ids": tuple(pair.deep.run_dir.name for pair in pairs),
        "selected_run_id": selected.hybrid.run_dir.name,
        "selected_seed": selected.hybrid.seed,
        "selected_victory_matrix_sha256": selected.evaluation.victory_matrix.sha256,
        "gates": gates,
        "artifact_sha256": "0" * 64,
    }
    lineage_model = artifact_lineage_model(lineage)
    if isinstance(lineage_model, ArtifactLineageV5):
        provisional["lineage"] = lineage_model.model_dump(mode="json")
    provisional_report = AggregateReleaseReport.model_validate(provisional)
    provisional_document = provisional_report.model_dump(mode="json")
    provisional_document.pop("artifact_sha256", None)
    provisional_document["artifact_sha256"] = canonical_json_sha256(provisional_document)
    return AggregateReleaseReport.model_validate(provisional_document)


def _load_validation_release(
    path: Path,
    *,
    expected_signature: str,
    expected_hybrid_run_ids: tuple[str, str, str],
    expected_deep_run_ids: tuple[str, str, str],
    expected_lineage: ArtifactLineageInput | None = None,
) -> AggregateReleaseReport:
    """Strict-load and independently hash-check the aggregate VAL report."""
    if not path.is_file():
        raise ArtifactIntegrityError("test release gate requires validation gate")
    report = AggregateReleaseReport.model_validate_json(path.read_text(encoding="utf-8"))
    if _report_sha(report) != report.artifact_sha256:
        raise ArtifactIntegrityError("validation aggregate report hash mismatch")
    if report.split is not SplitName.VAL or not report.passed:
        raise ArtifactIntegrityError("validation aggregate report is not a passing VAL report")
    if report.comparison_signature_sha256 != expected_signature:
        raise ArtifactIntegrityError("validation aggregate signature differs from TEST")
    if (
        report.hybrid_run_ids != expected_hybrid_run_ids
        or report.deep_run_ids != expected_deep_run_ids
    ):
        raise ArtifactIntegrityError("validation aggregate finalist set differs from TEST")
    if isinstance(expected_lineage, ArtifactLineageV5):
        if report.lineage is None or artifact_lineage_model(
            report.lineage
        ) != artifact_lineage_model(expected_lineage):
            raise ArtifactIntegrityError("validation aggregate lineage differs from TEST")
    return report


def _publish_release_report(path: Path, report: AggregateReleaseReport) -> None:
    """Publish one immutable aggregate report and allow an exact retry only."""
    document = report.model_dump(mode="json")
    if path.exists():
        try:
            existing = AggregateReleaseReport.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError) as error:
            raise ArtifactIntegrityError("existing release report cannot be read") from error
        if (
            existing.model_dump(mode="json") != document
            or _report_sha(existing) != existing.artifact_sha256
        ):
            raise ArtifactIntegrityError("immutable release report differs from retry")
        return
    immutable_write_json(path, document)


def evaluate_three_seed(
    *,
    split: SplitName,
    hybrid_run_dirs: tuple[Path, Path, Path],
    deep_run_dirs: tuple[Path, Path, Path],
    settings: Settings,
) -> AggregateReleaseReport:
    hybrid = tuple(_load_finalist_run(path, TrainingVariant.HYBRID) for path in hybrid_run_dirs)
    deep = tuple(_load_finalist_run(path, TrainingVariant.DEEP_ONLY) for path in deep_run_dirs)
    if (
        len({record.run_dir.resolve() for record in hybrid}) != 3
        or len({record.run_dir.resolve() for record in deep}) != 3
    ):
        raise DataIntegrityError("release gate requires three distinct runs per variant")
    if any(record.lineage != hybrid[0].lineage for record in (*hybrid[1:], *deep)):
        raise ArtifactIntegrityError("all six finalists must share full lineage")
    if any(record.git_commit != hybrid[0].git_commit for record in (*hybrid[1:], *deep)):
        raise ArtifactIntegrityError("all six finalists must share one frozen source revision")
    signatures = {record.settings.comparison_signature_sha256() for record in (*hybrid, *deep)}
    if len(signatures) != 1:
        raise ArtifactIntegrityError("all six finalists must share comparison signature")
    comparison_signature = next(iter(signatures))
    finalist_settings = hybrid[0].settings
    if settings.comparison_signature_sha256() != comparison_signature:
        raise ArtifactIntegrityError("ambient settings comparison signature differs from finalists")
    pairs = _pair_finalists_by_seed(hybrid, deep, split=split)
    _validate_finalist_set(pairs, split=split, comparison_signature=comparison_signature)
    gates = _build_aggregate_gates(pairs, settings=finalist_settings)
    passed = all(gate.passed for gate in gates)
    if not passed:
        raise DataIntegrityError(f"aggregate three-seed release gate failed on split {split.value}")
    selected = _select_validation_winner(pairs)
    report = _build_release_report(
        split=split,
        pairs=pairs,
        selected=selected,
        gates=gates,
        comparison_signature=comparison_signature,
        lineage=hybrid[0].lineage,
    )
    release_root = (
        finalist_settings.data.artifact_root.resolve() / "releases" / comparison_signature
    )
    output_path = release_root / (
        "validation-gate.json" if split is SplitName.VAL else "release-gate.json"
    )
    if (
        split is SplitName.TEST
        and any(record.lifecycle.status is RunStatus.SEALED for record in (*hybrid, *deep))
        and not output_path.is_file()
    ):
        raise DataIntegrityError(
            "TEST aggregate cannot start with a sealed finalist and no existing gate"
        )
    if split is SplitName.TEST:
        validation = _load_validation_release(
            release_root / "validation-gate.json",
            expected_signature=comparison_signature,
            expected_hybrid_run_ids=report.hybrid_run_ids,
            expected_deep_run_ids=report.deep_run_ids,
            expected_lineage=hybrid[0].lineage,
        )
        if (
            validation.selected_run_id != selected.hybrid.run_dir.name
            or validation.selected_seed != selected.hybrid.seed
        ):
            raise ArtifactIntegrityError("test gate selected run differs from validation winner")
        if (
            validation.hybrid_run_ids != report.hybrid_run_ids
            or validation.deep_run_ids != report.deep_run_ids
        ):
            raise ArtifactIntegrityError("test gate finalist set differs from validation gate")
        if validation.comparison_signature_sha256 != report.comparison_signature_sha256:
            raise ArtifactIntegrityError("test gate comparison signature differs from validation")
    _publish_release_report(output_path, report)
    if split is SplitName.TEST:
        sealed = [record for record in hybrid if record.lifecycle.status is RunStatus.SEALED]
        if sealed and (len(sealed) != 1 or sealed[0].run_dir.name != report.selected_run_id):
            raise ArtifactIntegrityError("existing sealed finalist differs from selected winner")
        for record in hybrid:
            if record.run_dir.name == report.selected_run_id:
                if record.lifecycle.status is not RunStatus.SEALED:
                    record.lifecycle.transition(
                        RunStatus.SEALED, reason="winner selected by validation and test gates"
                    )
    return report


__all__ = ["FinalistPairRecord", "FinalistRunRecord", "evaluate_three_seed"]
