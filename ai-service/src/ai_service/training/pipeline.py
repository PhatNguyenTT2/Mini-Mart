"""Fail-closed orchestration for one immutable training and serving lineage."""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
from argparse import Namespace
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from ai_service.artifact_io import atomic_write_json
from ai_service.config import (
    MODEL_SCHEMA_VERSION,
    Settings,
    load_resolved_settings,
    load_settings,
)
from ai_service.contracts import (
    RULE_COVERAGE_SEMANTICS_VERSION,
    AggregateReleaseReport,
    ArtifactLineageV5,
    CheckpointManifest,
    DataSourceKind,
    EmbeddingSource,
    PipelineState,
    RuleManifest,
    RunStatus,
    SnapshotManifest,
    SplitName,
    TerminalAction,
    TrainingVariant,
    VictoryMatrix,
)
from ai_service.data.dataset import (
    HybridImplicitDataset,
    PurchaseBatchIterator,
    TrainingBatch,
    build_purchase_training_index,
    collate_candidate_groups,
)
from ai_service.data.features import (
    EmbeddingArtifact,
    SBERTArtifactBuilder,
    load_embedding_artifact,
)
from ai_service.data.history import build_user_profile_vectors
from ai_service.data.quality import DataQualityAuditor
from ai_service.data.rule_readiness import assess_training_rule_readiness
from ai_service.data.rules import AprioriRuleMiner, RuleArtifact, load_rule_artifact
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot, SnapshotBuilder, load_snapshot
from ai_service.data.sources import DatasetSource, PostgresDatasetSource, SyntheticDatasetSource
from ai_service.errors import (
    ArtifactIntegrityError,
    CatastrophicTrainingError,
    ConfigurationError,
    DataIntegrityError,
    DiagnosticQualityError,
    TrainingInterruptedError,
    VictoryGateError,
)
from ai_service.evaluation.ablation import (
    DeepAblationRun,
    load_deep_ablation_artifact,
    require_hybrid_diagnostic_signal,
    require_selected_r3_pair,
    run_deep_ablation_comparison,
)
from ai_service.evaluation.baselines import run_full_catalog_comparison
from ai_service.evaluation.cold_start import evaluate_cold_parity
from ai_service.evaluation.full_catalog import FullCatalogEvaluator, prepare_split
from ai_service.evaluation.gates import SingleSeedGateInputs, evaluate_single_seed
from ai_service.evaluation.probes import run_data_probes
from ai_service.evaluation.r3_diagnostics import publish_r3_diagnostic
from ai_service.evaluation.release import evaluate_three_seed
from ai_service.evaluation.report import load_evaluation_artifacts, publish_evaluation_artifacts
from ai_service.evaluation.semantic_traps import evaluate_semantic_traps
from ai_service.export.bundle import BundlePublisher, file_sha256, verify_bundle
from ai_service.export.onnx import export_onnx_models
from ai_service.export.parity import verify_onnx_parity
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.provenance import (
    require_frozen_source_revision,
    resolve_source_revision,
)
from ai_service.training.run import RunLifecycle
from ai_service.training.trainer import Trainer


@dataclass(frozen=True)
class PairEvaluationResult:
    split: SplitName
    hybrid_state: PipelineState
    deep_state: PipelineState
    artifact_dir: Path
    victory_matrix: VictoryMatrix


@dataclass(frozen=True)
class LoadedRun:
    run_dir: Path
    checkpoint_manifest: CheckpointManifest
    settings: Settings
    state: PipelineState
    lifecycle: RunLifecycle
    snapshot: Snapshot
    embedding: EmbeddingArtifact
    rules: RuleArtifact
    model: HybridTwoTowerModel


def _validate_artifact_id(value: str, *, kind: str) -> str:
    if value == "main" or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ConfigurationError(f"invalid immutable {kind}: {value!r}")
    return value


def _emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _state_path(settings: Settings, run_id: str) -> Path:
    return settings.data.artifact_root.resolve() / "runs" / run_id / "pipeline-state.json"


def _write_state(settings: Settings, state: PipelineState) -> None:
    path = _state_path(settings, state.run_id)
    atomic_write_json(path, state.model_dump(mode="json"))


def _update_pipeline_state(state: PipelineState, **updates: object) -> PipelineState:
    """Apply state transitions through the strict v5 contract.

    Pydantic's ``model_copy(update=...)`` deliberately skips validation.  A
    pipeline state is an immutable lineage boundary, so every mutation must
    be revalidated before it is persisted.
    """
    document = state.model_dump(mode="json")
    document.update(updates)
    return PipelineState.model_validate(document)


def _load_state(settings: Settings, run_id: str | None) -> PipelineState:
    if not run_id:
        raise ConfigurationError("--run-id is required for this command")
    path = _state_path(settings, run_id)
    if not path.is_file():
        raise ArtifactIntegrityError(f"pipeline state does not exist: {path}")
    state_document = json.loads(path.read_text(encoding="utf-8"))
    if "model_schema_version" not in state_document:
        raise ArtifactIntegrityError("pipeline state has no model schema version")
    state = PipelineState.model_validate(state_document)
    return state


def _configure(args: Namespace) -> Settings:
    settings = load_settings(getattr(args, "config", None))
    store_id = int(getattr(args, "store_id", settings.data.store_id))
    if store_id <= 0:
        raise ConfigurationError("--store-id must be positive")
    settings.data.store_id = store_id
    snapshot_id = getattr(args, "snapshot_id", None)
    if snapshot_id:
        settings.data.snapshot_id = _validate_artifact_id(str(snapshot_id), kind="snapshot ID")
    benchmark_run_id = getattr(args, "benchmark_run_id", None)
    if benchmark_run_id:
        settings.data.benchmark_run_id = str(benchmark_run_id)
    settings.train.seed = int(getattr(args, "seed", settings.train.seed))
    selection_report = getattr(args, "r3_selection_report", None)
    if selection_report is not None:
        selection_path = Path(selection_report).resolve()
        if not selection_path.is_file():
            raise ConfigurationError(f"R3 selection report does not exist: {selection_path}")
        if settings.train.r3_feature_selection_mode != "selection_artifact":
            raise ConfigurationError(
                "--r3-selection-report requires selection_artifact config mode"
            )
        if selection_path.name != "report.json":
            raise ConfigurationError("R3 selection report must be the verified report.json")
        artifact = load_deep_ablation_artifact(selection_path.parent)
        if artifact.report.diagnostic_pause or artifact.report.selected_run_id is None:
            raise ConfigurationError("R3 selection report is a diagnostic pause")
        selection = artifact.report.selected_feature_selection
        if selection is None:
            raise ConfigurationError("R3 selection report has no feature selection")
        settings.model.use_user_id_embedding = selection.use_user_id_embedding
        settings.model.use_price_features = selection.use_price_features
        settings.train.r3_selection_artifact_sha256 = artifact.report.artifact_sha256
    elif settings.train.r3_feature_selection_mode == "selection_artifact":
        raise ConfigurationError("selection_artifact config requires --r3-selection-report")
    if settings.serving.environment.lower() == "production" and (
        getattr(args, "source", DataSourceKind.POSTGRES.value) != DataSourceKind.POSTGRES.value
        or getattr(args, "embedding_source", EmbeddingSource.REAL.value)
        != EmbeddingSource.REAL.value
    ):
        raise ConfigurationError("production requires postgres and real embedding adapters")
    explicit_bundle_selector = bool(
        getattr(args, "bundle_id", None) or getattr(args, "run_id", None)
    )
    settings.validate_production(
        serving=args.command == "verify-bundle" and not explicit_bundle_selector
    )
    return settings


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if torch.backends.cudnn.is_available():  # type: ignore[no-untyped-call]
        torch.backends.cudnn.benchmark = False


def _ensure_training_terminal_summary(
    run_dir: Path,
    *,
    action: TerminalAction,
    reason: str,
) -> None:
    summary_path = run_dir / "training" / "summary.json"
    summary: dict[str, object] = {}
    try:
        loaded = json.loads(summary_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            summary.update(loaded)
    except (OSError, ValueError):
        pass
    completed_epochs = summary.get("epochs_completed", 0)
    if not isinstance(completed_epochs, int) or completed_epochs < 0:
        completed_epochs = 0
    atomic_write_json(
        summary_path,
        {
            **summary,
            "terminal_action": action.value,
            "terminal_reason": reason,
            "stop_reason": reason,
            "epochs_completed": completed_epochs,
        },
    )


def _terminalize_training_session(
    lifecycle: RunLifecycle,
    run_dir: Path,
    *,
    requested_action: TerminalAction,
    reason: str,
) -> None:
    """Persist a terminal summary and lifecycle status after session failure."""

    action = requested_action
    status = RunStatus.FAILED if action is TerminalAction.FAILED else RunStatus.INTERRUPTED
    if lifecycle.status is RunStatus.STAGING:
        # STAGING cannot transition to INTERRUPTED by contract. A failure while
        # entering TRAINING is therefore a failed setup, not an interrupted run.
        action = TerminalAction.FAILED
        status = RunStatus.FAILED
    try:
        _ensure_training_terminal_summary(run_dir, action=action, reason=reason)
        lifecycle.transition_training_terminal(status, reason=reason)
    except BaseException as error:
        raise ArtifactIntegrityError("training failure could not be terminalized") from error


def _require_resume_history(run_dir: Path, *, checkpoint_epoch: int) -> None:
    """Reject a resume before transition unless its durable epoch history is intact."""

    history_path = run_dir / "training" / "history.jsonl"
    if not history_path.is_file():
        raise ArtifactIntegrityError("resume checkpoint has no durable training history")
    epochs: list[int] = []
    try:
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            document = json.loads(line)
            epoch = document.get("epoch") if isinstance(document, dict) else None
            if not isinstance(epoch, int):
                raise ValueError("history epoch is invalid")
            epochs.append(epoch)
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("resume history contains an invalid epoch record") from error
    if epochs != list(range(1, checkpoint_epoch + 1)):
        raise ArtifactIntegrityError("resume history and checkpoint epochs differ")


def _device(requested: str) -> torch.device:
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ConfigurationError("CUDA was requested but the installed Torch runtime has no CUDA")
    return device


def _snapshot(settings: Settings, source_kind: DataSourceKind) -> Snapshot:
    source: DatasetSource
    if source_kind is DataSourceKind.POSTGRES:
        source = PostgresDatasetSource(settings)
    else:
        source = SyntheticDatasetSource(settings)
    raw = source.load(settings.data.store_id, settings.data.benchmark_run_id)
    return SnapshotBuilder(settings).build(raw, snapshot_id=settings.data.snapshot_id)


def _features(
    settings: Settings, snapshot: Snapshot, source_kind: EmbeddingSource
) -> EmbeddingArtifact:
    return SBERTArtifactBuilder(settings).build(
        snapshot,
        encoder=None,
        source_kind=source_kind,
    )


def _rules(settings: Settings, snapshot: Snapshot) -> RuleArtifact:
    return AprioriRuleMiner(settings).mine(snapshot)


def _find_single_parent_artifact(
    root: Path,
    *,
    snapshot_sha256: str,
    manifest_name: str = "manifest.json",
) -> Path:
    matches: list[Path] = []
    if root.exists():
        for manifest_path in root.glob(f"*/{manifest_name}"):
            try:
                document = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ArtifactIntegrityError(
                    f"artifact manifest cannot be parsed: {manifest_path}"
                ) from error
            if document.get("snapshot_sha256") == snapshot_sha256:
                matches.append(manifest_path.parent)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            f"expected exactly one artifact below {root} for snapshot; found {len(matches)}"
        )
    return matches[0]


def _find_training_rule_artifact(settings: Settings, snapshot_sha256: str) -> Path:
    """Select exactly one full-stat rule artifact for the resolved training config."""
    root = settings.data.artifact_root.resolve() / "rules"
    matches: list[Path] = []
    scanned: dict[str, list[str]] = {}
    if root.exists():
        for manifest_path in root.glob("*/manifest.json"):
            artifact_id = manifest_path.parent.name
            try:
                manifest = RuleManifest.model_validate_json(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError) as error:
                scanned[artifact_id] = [f"manifest_parse:{type(error).__name__}"]
                continue
            reasons: list[str] = []
            if manifest.snapshot_sha256 != snapshot_sha256:
                reasons.append("snapshot_sha256")
            if not manifest.has_full_statistics:
                reasons.append("has_full_statistics")
            if manifest.feature_schema_version != settings.data.rule_feature_schema_version:
                reasons.append("feature_schema_version")
            if manifest.min_count != settings.data.min_rule_count:
                reasons.append("min_count")
            if abs(manifest.min_lift - settings.data.min_rule_lift) > 1e-12:
                reasons.append("min_lift")
            if settings.data.rule_feature_schema_version == "3.0.0":
                if manifest.coverage_semantics_version != RULE_COVERAGE_SEMANTICS_VERSION:
                    reasons.append("coverage_semantics_version")
                coverage = manifest.coverage
                if coverage is None:
                    reasons.append("coverage")
                else:
                    if (
                        coverage.non_trap_directed_rules
                        < settings.data.minimum_non_trap_directed_rules
                    ):
                        reasons.append("minimum_non_trap_directed_rules")
                    if (
                        coverage.distinct_organic_rule_items
                        < settings.data.minimum_distinct_organic_rule_items
                    ):
                        reasons.append("minimum_distinct_organic_rule_items")
                    if (
                        coverage.val_context_rule_coverage
                        < settings.data.minimum_val_context_rule_coverage
                    ):
                        reasons.append("minimum_val_context_rule_coverage")
                    if (
                        coverage.trap_anchored_rule_fraction
                        > settings.data.maximum_trap_anchored_rule_fraction
                    ):
                        reasons.append("maximum_trap_anchored_rule_fraction")
            scanned[artifact_id] = reasons
            if not reasons:
                matches.append(manifest_path.parent)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            "expected exactly one full-stat rule artifact matching the training config; "
            f"found {len(matches)}; scanned={json.dumps(scanned, sort_keys=True)}"
        )
    return matches[0]


def _require_rule_training_capability(rules: Any, settings: Settings) -> Any:
    """Invoke one settings-aware capability contract for artifacts and test adapters."""
    return rules.require_training_capability(settings)


def _train(
    settings: Settings,
    snapshot: Snapshot,
    embedding: EmbeddingArtifact,
    rules: RuleArtifact,
    *,
    run_id: str,
    device: torch.device,
    resume: bool = False,
    require_frozen_source: bool,
) -> tuple[HybridTwoTowerModel, PipelineState]:
    settings.validate_campaign_stage()
    run_id = _validate_artifact_id(run_id, kind="run ID")
    run_dir = settings.data.artifact_root.resolve() / "runs" / run_id
    revision = (
        require_frozen_source_revision() if require_frozen_source else resolve_source_revision()
    )
    lineage = {
        "snapshot": snapshot.manifest.content_sha256,
        "embedding": embedding.manifest.content_sha256,
        "rules": rules.manifest.content_sha256,
    }
    if settings.data.rule_feature_schema_version == "3.0.0":
        metadata = {
            "benchmark_spec": getattr(snapshot.manifest, "benchmark_spec_sha256", None),
            "semantic_cohort": getattr(snapshot.manifest, "semantic_cohort_sha256", None),
            "order_metadata": getattr(snapshot.manifest, "order_metadata_sha256", None),
        }
        if all(isinstance(value, str) for value in metadata.values()):
            lineage = ArtifactLineageV5(
                snapshot=lineage["snapshot"],
                embedding=lineage["embedding"],
                rules=lineage["rules"],
                benchmark_spec=cast(str, metadata["benchmark_spec"]),
                semantic_cohort=cast(str, metadata["semantic_cohort"]),
                order_metadata=cast(str, metadata["order_metadata"]),
            ).as_mapping()
        elif type(snapshot.manifest).__name__ == SnapshotManifest.__name__:
            raise ArtifactIntegrityError("v5 R3 snapshot is missing expanded lineage hashes")
        elif not all(value is None for value in metadata.values()):
            raise ArtifactIntegrityError("v5 R3 snapshot is missing expanded lineage hashes")
    rule_store = _require_rule_training_capability(rules, settings)
    if (
        rules.manifest.feature_schema_version != settings.data.rule_feature_schema_version
        or rules.manifest.snapshot_sha256 != snapshot.manifest.content_sha256
        or rules.manifest.min_count != settings.data.min_rule_count
        or abs(rules.manifest.min_lift - settings.data.min_rule_lift) > 1e-12
    ):
        raise ArtifactIntegrityError("training rule artifact does not match resolved config")
    if settings.train.campaign_stage == "production":
        require_selected_r3_pair(
            artifact_root=settings.data.artifact_root,
            hybrid_flags=(
                settings.model.use_user_id_embedding,
                settings.model.use_price_features,
            ),
            deep_flags=(
                settings.model.use_user_id_embedding,
                settings.model.use_price_features,
            ),
            campaign_stage="production",
            selection_artifact_sha256=settings.train.r3_selection_artifact_sha256,
            lineage=lineage,
        )

    # Build every potentially failing training input before publishing an immutable
    # run directory.  Trainer construction is deliberately deferred until after
    # lifecycle transition because it moves the model to the requested device and
    # may allocate CUDA/optimizer state.
    if settings.train.objective == "sampled_softmax":
        purchase_index = build_purchase_training_index(
            snapshot,
            max_history_items=settings.train.max_history_items,
        )
        sampler = MixedNegativeSampler(
            purchase_index,
            snapshot,
            embedding.vectors,
            ratio=settings.train.explicit_negative_ratio,
            seed=settings.train.seed,
            rule_store=rule_store,
            rule_hard_negative_count=(
                settings.train.rule_hard_negative_count
                if settings.train.training_variant is TrainingVariant.HYBRID
                else 0
            ),
        )
        loader: Any = PurchaseBatchIterator(
            purchase_index,
            sampler,
            rule_store,
            batch_size=settings.train.batch_size,
            seed=settings.train.seed,
        )
    else:
        dataset = HybridImplicitDataset(
            snapshot,
            rule_store,
            split=SplitName.TRAIN,
            negative_ratio=settings.train.negative_ratio,
            seed=settings.train.seed,
            positive_event_types=(
                frozenset({"purchase"})
                if settings.train.objective == "purchase_bce"
                else frozenset({"view", "purchase"})
            ),
        )
        loader = cast(
            DataLoader[TrainingBatch],
            DataLoader(
                dataset,
                batch_size=settings.train.batch_size,
                shuffle=True,
                num_workers=min(4, os.cpu_count() or 1),
                persistent_workers=(os.cpu_count() or 1) > 0,
                pin_memory=device.type == "cuda",
                collate_fn=collate_candidate_groups,
                generator=torch.Generator().manual_seed(settings.train.seed),
            ),
        )
    rule_readiness = None
    if (
        settings.train.objective == "sampled_softmax"
        and settings.data.rule_feature_schema_version == "3.0.0"
    ):
        rule_readiness = assess_training_rule_readiness(
            loader,
            minimum_rows_with_any_rule=settings.data.minimum_training_rows_with_any_rule,
            minimum_training_target_rule_rate=settings.data.minimum_training_target_rule_rate,
        )
        if not rule_readiness.passed:
            raise ArtifactIntegrityError(
                "training rule readiness failed: " + "; ".join(rule_readiness.failure_reasons)
            )
    model = HybridTwoTowerModel(settings)
    evaluator = FullCatalogEvaluator(settings, embedding.vectors, rule_store)

    if resume:
        lifecycle = RunLifecycle.load(run_dir)
        if lifecycle.status is not RunStatus.INTERRUPTED:
            raise ArtifactIntegrityError("only an interrupted run may be resumed")
        if lifecycle.document.get("lineage") != dict(sorted(lineage.items())):
            raise ArtifactIntegrityError("resume run lineage differs from requested artifacts")
        if (
            lifecycle.document.get("training_signature_sha256")
            != settings.training_signature_sha256()
        ):
            raise ArtifactIntegrityError("resume run training signature differs")
        if lifecycle.document.get("training_variant") != settings.train.training_variant.value:
            raise ArtifactIntegrityError("resume run training variant differs")
        if lifecycle.document.get("git_commit") != revision.commit_sha:
            raise ArtifactIntegrityError(
                "resume run Git commit differs from the frozen source revision"
            )
        resume_checkpoint = run_dir / "checkpoints" / "last.pt"
        resume_state = CheckpointManager.load(
            resume_checkpoint,
            model=model,
            expected_lineage=lineage,
            expected_training_signature=settings.training_signature_sha256(),
            expected_comparison_signature=settings.comparison_signature_sha256(),
            expected_training_variant=settings.train.training_variant,
            expected_checkpoint_kind="last",
            expected_run_id=run_id,
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
            require_resume_state=True,
        )
        _require_resume_history(run_dir, checkpoint_epoch=int(resume_state["epoch"]))
    else:
        resume_checkpoint = None
        lifecycle = RunLifecycle.create(
            run_dir,
            settings=settings,
            lineage=lineage,
            git_commit=revision.commit_sha,
        )

    try:
        lifecycle.transition(RunStatus.TRAINING)
        if rule_readiness is not None:
            atomic_write_json(
                run_dir / "training" / "preflight-rule-readiness.json",
                rule_readiness.model_dump(mode="json"),
            )
        trainer = Trainer(
            model,
            settings=settings,
            run_dir=run_dir,
            training_variant=settings.train.training_variant,
            device=device,
        )
        result = trainer.fit(
            loader,
            snapshot,
            embedding.vectors,
            evaluator,
            lineage,
            resume_from=resume_checkpoint,
        )
        release_checkpoint = result.checkpoint_path
        state = PipelineState(
            model_schema_version=MODEL_SCHEMA_VERSION,
            run_id=run_id,
            training_variant=settings.train.training_variant,
            snapshot_id=snapshot.manifest.artifact_id,
            embedding_path=str(embedding.artifact_dir),
            rule_path=str(rules.artifact_dir),
            checkpoint_path=str(release_checkpoint),
            paired_run_id=None,
            validation_gate_passed=False,
            test_gate_passed=False,
            validation_victory_matrix_path=None,
            test_victory_matrix_path=None,
            bundle_path=None,
        )
        _write_state(settings, state)
    except (CatastrophicTrainingError, DiagnosticQualityError) as error:
        reason = str(error) or type(error).__name__
        _terminalize_training_session(
            lifecycle,
            run_dir,
            requested_action=TerminalAction.FAILED,
            reason=reason,
        )
        raise
    except (TrainingInterruptedError, KeyboardInterrupt) as error:
        reason = str(error) or type(error).__name__
        _terminalize_training_session(
            lifecycle,
            run_dir,
            requested_action=TerminalAction.INTERRUPTED,
            reason=reason,
        )
        raise
    except BaseException as error:
        reason = type(error).__name__
        _terminalize_training_session(
            lifecycle,
            run_dir,
            requested_action=TerminalAction.INTERRUPTED,
            reason=reason,
        )
        raise
    return model, state


def _export(
    settings: Settings,
    snapshot: Snapshot,
    embedding: EmbeddingArtifact,
    rules: RuleArtifact,
    model: HybridTwoTowerModel,
    state: PipelineState,
) -> PipelineState:
    if not state.test_gate_passed or state.checkpoint_path is None:
        raise DataIntegrityError("only a test-evaluated best checkpoint may be exported")
    lifecycle = RunLifecycle.load(Path(state.checkpoint_path).parents[1])
    if lifecycle.status is not RunStatus.SEALED:
        raise DataIntegrityError("only a sealed training run may be exported")
    comparison_signature = lifecycle.document.get("comparison_signature_sha256", "")
    if not comparison_signature:
        raise DataIntegrityError("sealed run has no comparison signature")
    release_path = (
        settings.data.artifact_root.resolve()
        / "releases"
        / comparison_signature
        / "release-gate.json"
    )
    if not release_path.is_file():
        raise DataIntegrityError("three-seed aggregate release gate has not been published")
    release = AggregateReleaseReport.model_validate_json(release_path.read_text(encoding="utf-8"))
    release_document = release.model_dump(mode="json")
    claimed_release_sha = release_document.pop("artifact_sha256")
    if (
        hashlib.sha256(
            json.dumps(release_document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        != claimed_release_sha
    ):
        raise DataIntegrityError("aggregate release report hash mismatch")
    if not release.passed or release.selected_run_id != state.run_id:
        raise DataIntegrityError("this run was not selected by the aggregate release gate")
    test_matrix_path = state.test_victory_matrix_path
    if not test_matrix_path or not Path(test_matrix_path).is_file():
        raise DataIntegrityError("selected run has no immutable test victory matrix")
    if state.paired_run_id is None:
        raise DataIntegrityError("selected run has no paired Deep run")
    evaluation = load_evaluation_artifacts(
        Path(state.checkpoint_path).parents[1],
        expected_split=SplitName.TEST,
        expected_hybrid_run_id=state.run_id,
        expected_deep_run_id=state.paired_run_id,
        expected_comparison_signature=comparison_signature,
        expected_lineage={
            "snapshot": snapshot.manifest.content_sha256,
            "embedding": embedding.manifest.content_sha256,
            "rules": rules.manifest.content_sha256,
        },
    )
    test_matrix = evaluation.victory_matrix
    if not test_matrix.all_passed:
        raise DataIntegrityError("selected test Victory Matrix did not pass all gates")
    if test_matrix.sha256 != release.selected_victory_matrix_sha256:
        raise DataIntegrityError("selected Victory Matrix does not match release gate")
    output_dir = Path(state.checkpoint_path).parents[1] / "export"
    paths = export_onnx_models(model, settings, output_dir)
    parity = verify_onnx_parity(model, settings, snapshot, embedding.vectors, rules.store, paths)
    if parity.kernel_latency_ms["p95"] >= 1.0:
        raise DataIntegrityError("full-catalog ONNX kernel p95 is not below 1 ms")
    catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
    export_model = model.cpu().eval()
    item_ids = torch.arange(snapshot.manifest.num_items, dtype=torch.int64)
    cold_mask = torch.zeros(snapshot.manifest.num_items, dtype=torch.bool)
    if snapshot.cold_item_ids:
        cold_mask[torch.tensor(snapshot.cold_item_ids, dtype=torch.int64)] = True
    with torch.no_grad():
        item_tensor = export_model.encode_items(
            torch.from_numpy(np.array(embedding.vectors, dtype=np.float32, copy=True)),
            torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)),
            torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)),
            item_idx=item_ids,
            is_cold=cold_mask,
        )
        profile_tensor = build_user_profile_vectors(
            export_model,
            snapshot,
            item_tensor,
            pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True),
            max_history_items=settings.train.max_history_items,
            device=torch.device("cpu"),
        )
        if not settings.train.use_history_profiles:
            profile_tensor.zero_()
        item_vectors = item_tensor.numpy()
        user_profiles = profile_tensor.numpy()
    checkpoint_sha = file_sha256(Path(state.checkpoint_path))
    bundle_id = f"{state.run_id}-{checkpoint_sha[:12]}"
    if test_matrix is None:
        raise ArtifactIntegrityError("export requires a verified test Victory Matrix artifact")
    bundle = BundlePublisher(settings).publish(
        bundle_id=bundle_id,
        run_id=state.run_id,
        snapshot=snapshot,
        rule_store=rules.store,
        ranker_path=paths.ranker,
        item_vectors=item_vectors,
        user_profile_vectors=user_profiles,
        embedding_sha256=embedding.manifest.content_sha256,
        rule_sha256=rules.manifest.content_sha256,
        checkpoint_sha256=checkpoint_sha,
        comparison_signature_sha256=comparison_signature,
        parity=parity,
        victory_matrix_sha256=test_matrix.sha256,
    )
    next_state = _update_pipeline_state(state, bundle_path=str(bundle.path))
    _write_state(settings, next_state)
    return next_state


def _load_lineage(
    settings: Settings,
    state: PipelineState,
    *,
    expected_variant: TrainingVariant | None = None,
) -> tuple[Snapshot, EmbeddingArtifact, RuleArtifact, HybridTwoTowerModel]:
    snapshot = load_snapshot(state.snapshot_id, settings)
    embedding = load_embedding_artifact(Path(state.embedding_path))
    rules = load_rule_artifact(Path(state.rule_path), snapshot.manifest.num_items)
    model = HybridTwoTowerModel(settings)
    if state.checkpoint_path is not None:
        CheckpointManager.load(
            Path(state.checkpoint_path),
            model=model,
            expected_lineage={
                "snapshot": snapshot.manifest.content_sha256,
                "embedding": embedding.manifest.content_sha256,
                "rules": rules.manifest.content_sha256,
            },
            expected_training_signature=settings.training_signature_sha256(),
            expected_comparison_signature=settings.comparison_signature_sha256(),
            expected_training_variant=expected_variant,
            expected_checkpoint_kind="best",
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
        )
    return snapshot, embedding, rules, model


def _load_run_context(
    base_settings: Settings,
    run_id: str,
    *,
    expected_variant: TrainingVariant,
) -> LoadedRun:
    run_id = _validate_artifact_id(run_id, kind="run ID")
    run_dir = base_settings.data.artifact_root.resolve() / "runs" / run_id
    if not run_dir.is_dir() or run_dir.name != run_id:
        raise ArtifactIntegrityError("run directory does not match requested run ID")
    settings = load_resolved_settings(run_dir / "resolved-config.json")
    state_document = json.loads((run_dir / "pipeline-state.json").read_text(encoding="utf-8"))
    if "model_schema_version" not in state_document:
        raise ArtifactIntegrityError("pipeline state has no model schema version")
    state = PipelineState.model_validate(state_document)
    if state.run_id != run_id:
        raise ArtifactIntegrityError("pipeline state run ID does not match run directory")
    if state.model_schema_version != MODEL_SCHEMA_VERSION:
        raise ArtifactIntegrityError("pipeline state model schema mismatch")
    if TrainingVariant(state.training_variant) is not expected_variant:
        raise ArtifactIntegrityError(f"run {run_id} has unexpected training variant")
    if settings.train.training_variant is not expected_variant:
        raise ArtifactIntegrityError("resolved configuration variant differs from run state")
    lifecycle = RunLifecycle.load(run_dir)
    if lifecycle.document.get("training_variant") != expected_variant.value:
        raise ArtifactIntegrityError("run manifest variant differs from run state")
    if state.checkpoint_path is None:
        raise ArtifactIntegrityError("run context has no checkpoint")
    checkpoint_path = Path(state.checkpoint_path).resolve()
    if (
        run_dir.resolve() not in checkpoint_path.parents
        or checkpoint_path.parent.name != "checkpoints"
        or checkpoint_path.name != "best.pt"
    ):
        raise ArtifactIntegrityError("checkpoint is outside its immutable run directory")
    manifest_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".manifest.json")
    try:
        checkpoint_manifest = CheckpointManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("checkpoint manifest cannot be read") from error
    if checkpoint_manifest.run_id != run_id:
        raise ArtifactIntegrityError("checkpoint run ID does not match requested run")
    if checkpoint_manifest.training_variant is not expected_variant:
        raise ArtifactIntegrityError("checkpoint variant does not match requested run")
    if checkpoint_manifest.training_signature_sha256 != settings.training_signature_sha256():
        raise ArtifactIntegrityError("checkpoint training signature differs from run config")
    if checkpoint_manifest.comparison_signature_sha256 != settings.comparison_signature_sha256():
        raise ArtifactIntegrityError("checkpoint comparison signature differs from run config")
    if checkpoint_manifest.model_schema_version != MODEL_SCHEMA_VERSION:
        raise ArtifactIntegrityError("checkpoint model schema differs from run state")
    snapshot, embedding, rules, model = _load_lineage(
        settings, state, expected_variant=expected_variant
    )
    _require_rule_training_capability(rules, settings)
    if settings.data.rule_feature_schema_version == "3.0.0":
        coverage = getattr(rules.manifest, "coverage", None)
        if rules.manifest.feature_schema_version != "3.0.0" or coverage is None:
            raise ArtifactIntegrityError("run context rule artifact lacks v3 coverage evidence")
    if (
        rules.manifest.feature_schema_version != settings.data.rule_feature_schema_version
        or rules.manifest.min_count != settings.data.min_rule_count
        or abs(rules.manifest.min_lift - settings.data.min_rule_lift) > 1e-12
    ):
        raise ArtifactIntegrityError("loaded rule artifact does not match resolved training config")
    loaded_lineage = {
        "snapshot": snapshot.manifest.content_sha256,
        "embedding": embedding.manifest.content_sha256,
        "rules": rules.manifest.content_sha256,
    }
    if lifecycle.document.get("lineage") != loaded_lineage:
        raise ArtifactIntegrityError("run lifecycle lineage differs from loaded artifacts")
    if checkpoint_manifest.parent_sha256 != loaded_lineage:
        raise ArtifactIntegrityError("checkpoint lineage differs from loaded artifacts")
    return LoadedRun(
        run_dir=run_dir,
        checkpoint_manifest=checkpoint_manifest,
        settings=settings,
        state=state,
        lifecycle=lifecycle,
        snapshot=snapshot,
        embedding=embedding,
        rules=rules,
        model=model,
    )


def _evaluate_pair(
    base_settings: Settings,
    *,
    hybrid_run_id: str,
    deep_run_id: str,
    split: SplitName,
    device: torch.device,
) -> PairEvaluationResult:
    hybrid = _load_run_context(
        base_settings, hybrid_run_id, expected_variant=TrainingVariant.HYBRID
    )
    deep = _load_run_context(base_settings, deep_run_id, expected_variant=TrainingVariant.DEEP_ONLY)
    hybrid.settings.validate_campaign_stage()
    deep.settings.validate_campaign_stage()
    if hybrid.settings.train.campaign_stage != deep.settings.train.campaign_stage:
        raise ArtifactIntegrityError("paired evaluation requires matching campaign stages")
    if hybrid.settings.train.seed != deep.settings.train.seed:
        raise ArtifactIntegrityError("paired evaluation requires matching seeds")
    if hybrid.settings.comparison_signature_sha256() != deep.settings.comparison_signature_sha256():
        raise ArtifactIntegrityError("paired evaluation requires matching comparison signatures")
    if hybrid.lifecycle.document.get("git_commit") != deep.lifecycle.document.get("git_commit"):
        raise ArtifactIntegrityError("paired evaluation requires matching source revisions")
    lineage: dict[str, str] = {
        "snapshot": hybrid.snapshot.manifest.content_sha256,
        "embedding": hybrid.embedding.manifest.content_sha256,
        "rules": hybrid.rules.manifest.content_sha256,
    }
    if hybrid.settings.data.rule_feature_schema_version == "3.0.0":
        metadata = {
            "benchmark_spec": getattr(hybrid.snapshot.manifest, "benchmark_spec_sha256", None),
            "semantic_cohort": getattr(hybrid.snapshot.manifest, "semantic_cohort_sha256", None),
            "order_metadata": getattr(hybrid.snapshot.manifest, "order_metadata_sha256", None),
        }
        if not all(isinstance(value, str) for value in metadata.values()) and (
            type(hybrid.snapshot.manifest).__name__ == SnapshotManifest.__name__
            or any(value is not None for value in metadata.values())
        ):
            raise ArtifactIntegrityError("paired evaluation requires expanded v5 lineage")
        if all(isinstance(value, str) for value in metadata.values()):
            lineage = ArtifactLineageV5(
                snapshot=lineage["snapshot"],
                embedding=lineage["embedding"],
                rules=lineage["rules"],
                benchmark_spec=cast(str, metadata["benchmark_spec"]),
                semantic_cohort=cast(str, metadata["semantic_cohort"]),
                order_metadata=cast(str, metadata["order_metadata"]),
            ).as_mapping()
    deep_base_lineage = {
        "snapshot": deep.snapshot.manifest.content_sha256,
        "embedding": deep.embedding.manifest.content_sha256,
        "rules": deep.rules.manifest.content_sha256,
    }
    if any(lineage[name] != value for name, value in deep_base_lineage.items()):
        raise ArtifactIntegrityError("paired evaluation requires matching artifact lineage")
    if hybrid.settings.data.rule_feature_schema_version == "3.0.0":
        deep_metadata = {
            "benchmark_spec": getattr(deep.snapshot.manifest, "benchmark_spec_sha256", None),
            "semantic_cohort": getattr(deep.snapshot.manifest, "semantic_cohort_sha256", None),
            "order_metadata": getattr(deep.snapshot.manifest, "order_metadata_sha256", None),
        }
        if not all(isinstance(value, str) for value in deep_metadata.values()) and (
            type(deep.snapshot.manifest).__name__ == SnapshotManifest.__name__
            or any(value is not None for value in deep_metadata.values())
        ):
            raise ArtifactIntegrityError("paired evaluation requires expanded v5 lineage")
        if all(isinstance(value, str) for value in deep_metadata.values()):
            deep_lineage = ArtifactLineageV5(
                snapshot=deep.snapshot.manifest.content_sha256,
                embedding=deep.embedding.manifest.content_sha256,
                rules=deep.rules.manifest.content_sha256,
                benchmark_spec=cast(str, deep_metadata["benchmark_spec"]),
                semantic_cohort=cast(str, deep_metadata["semantic_cohort"]),
                order_metadata=cast(str, deep_metadata["order_metadata"]),
            ).as_mapping()
            if lineage != deep_lineage:
                raise ArtifactIntegrityError("paired evaluation requires matching artifact lineage")
    if hybrid.settings.data.rule_feature_schema_version == "3.0.0":
        campaign_stage = hybrid.settings.train.campaign_stage
        if campaign_stage not in {"diagnostic", "production"}:
            raise ArtifactIntegrityError("R3 evaluation requires a diagnostic or production stage")
        if hybrid.settings.train.campaign_stage == "production":
            if (
                hybrid.settings.train.r3_selection_artifact_sha256
                != deep.settings.train.r3_selection_artifact_sha256
            ):
                raise ArtifactIntegrityError(
                    "production pair requires the same R3 selection receipt"
                )
        require_selected_r3_pair(
            artifact_root=hybrid.settings.data.artifact_root,
            selected_deep_run_id=(
                deep.state.run_id if hybrid.settings.train.campaign_stage == "diagnostic" else None
            ),
            hybrid_flags=(
                hybrid.settings.model.use_user_id_embedding,
                hybrid.settings.model.use_price_features,
            ),
            deep_flags=(
                deep.settings.model.use_user_id_embedding,
                deep.settings.model.use_price_features,
            ),
            campaign_stage=cast(Literal["diagnostic", "production"], campaign_stage),
            selection_artifact_sha256=hybrid.settings.train.r3_selection_artifact_sha256,
            lineage=lineage,
        )
        require_hybrid_diagnostic_signal(
            hybrid.run_dir / "training" / "history.jsonl",
            best_epoch=hybrid.checkpoint_manifest.best_epoch,
            minimum_rule_row_rate=hybrid.settings.data.minimum_training_rows_with_any_rule,
            minimum_wide_deep_ratio=hybrid.settings.eval.minimum_wide_to_deep_rms_ratio,
            minimum_top_k_change_rate=(hybrid.settings.eval.minimum_hybrid_deep_top_k_change_rate),
        )
    if split is SplitName.TEST:
        release_path = (
            base_settings.data.artifact_root.resolve()
            / "releases"
            / hybrid.settings.comparison_signature_sha256()
            / "validation-gate.json"
        )
        if not release_path.is_file():
            raise ArtifactIntegrityError("test evaluation requires an aggregate validation gate")
        validation_gate = AggregateReleaseReport.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        gate_document = validation_gate.model_dump(mode="json")
        claimed_sha = gate_document.pop("artifact_sha256")
        if (
            hashlib.sha256(
                json.dumps(gate_document, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            != claimed_sha
        ):
            raise ArtifactIntegrityError("validation aggregate gate hash mismatch")
        if not validation_gate.passed or validation_gate.split is not SplitName.VAL:
            raise ArtifactIntegrityError("aggregate validation gate did not pass")
        if (
            validation_gate.comparison_signature_sha256
            != hybrid.settings.comparison_signature_sha256()
        ):
            raise ArtifactIntegrityError("validation gate comparison signature differs")
        if (
            hybrid_run_id not in validation_gate.hybrid_run_ids
            or deep_run_id not in validation_gate.deep_run_ids
            or validation_gate.selected_run_id not in validation_gate.hybrid_run_ids
        ):
            raise ArtifactIntegrityError("test pair is not part of the validated finalist set")

    prepared_split = prepare_split(hybrid.snapshot, split)
    comparison = run_full_catalog_comparison(
        hybrid_model=hybrid.model,
        deep_model=deep.model,
        snapshot=hybrid.snapshot,
        embeddings=hybrid.embedding.vectors,
        rule_store=hybrid.rules.store,
        settings=hybrid.settings,
        device=device,
        prepared_split=prepared_split,
    )
    cold_prepared = (
        prepared_split
        if split is SplitName.TEST
        else prepare_split(hybrid.snapshot, SplitName.TEST)
    )
    cold_parity = evaluate_cold_parity(
        hybrid.model,
        hybrid.snapshot,
        hybrid.embedding.vectors,
        hybrid.rules.store,
        prepared_split=cold_prepared,
        settings=hybrid.settings,
        device=device,
    )
    fixture = Path(__file__).parents[1] / "evaluation" / "fixtures" / "semantic_traps.json"
    traps = evaluate_semantic_traps(
        hybrid.model,
        deep.model,
        hybrid.snapshot,
        hybrid.embedding.vectors,
        hybrid.rules.store,
        fixture,
        k=hybrid.settings.eval.k,
        device=device,
        prepared_split=prepared_split,
        settings=hybrid.settings,
    )
    matrix = evaluate_single_seed(
        SingleSeedGateInputs(
            comparison=comparison,
            cold_parity=cold_parity,
            semantic_traps=traps,
            seed=hybrid.settings.train.seed,
            split=split,
            comparison_signature=hybrid.settings.comparison_signature_sha256(),
        ),
        settings=hybrid.settings,
    )
    if hybrid.state.checkpoint_path is None:
        raise ArtifactIntegrityError("paired evaluation requires a Hybrid checkpoint")
    checkpoint_sha = hybrid.checkpoint_manifest.content_sha256
    if deep.state.checkpoint_path is None:
        raise ArtifactIntegrityError("paired evaluation requires a Deep checkpoint")
    deep_checkpoint_sha = deep.checkpoint_manifest.content_sha256
    run_dir = Path(hybrid.state.checkpoint_path).parents[1]
    random_results = comparison.random_seed_results
    metrics = {
        "user_ids": comparison.hybrid.user_ids,
        "hybrid_hr": comparison.hybrid.per_user_hr,
        "hybrid_ndcg": comparison.hybrid.per_user_ndcg,
        "hybrid_gauc": comparison.hybrid.per_user_gauc,
        "deep_hr": comparison.deep_only.per_user_hr,
        "deep_ndcg": comparison.deep_only.per_user_ndcg,
        "deep_gauc": comparison.deep_only.per_user_gauc,
        "persona_hr": comparison.persona_only.per_user_hr,
        "persona_ndcg": comparison.persona_only.per_user_ndcg,
        "persona_gauc": comparison.persona_only.per_user_gauc,
        "apriori_hr": comparison.apriori_only.per_user_hr,
        "apriori_ndcg": comparison.apriori_only.per_user_ndcg,
        "apriori_gauc": comparison.apriori_only.per_user_gauc,
        "sbert_hr": comparison.sbert_centroid.per_user_hr,
        "sbert_ndcg": comparison.sbert_centroid.per_user_ndcg,
        "sbert_gauc": comparison.sbert_centroid.per_user_gauc,
        "item_cf_hr": comparison.item_cf.per_user_hr,
        "item_cf_ndcg": comparison.item_cf.per_user_ndcg,
        "item_cf_gauc": comparison.item_cf.per_user_gauc,
        "noisy_hybrid_hr": comparison.noisy_hybrid.per_user_hr,
        "noisy_hybrid_ndcg": comparison.noisy_hybrid.per_user_ndcg,
        "noisy_hybrid_gauc": comparison.noisy_hybrid.per_user_gauc,
        "random_hr": np.stack([result.per_user_hr for result in random_results]),
        "random_ndcg": np.stack([result.per_user_ndcg for result in random_results]),
        "random_gauc": np.stack([result.per_user_gauc for result in random_results]),
    }
    artifact_set = publish_evaluation_artifacts(
        run_dir=run_dir,
        split=split,
        hybrid_run_id=hybrid_run_id,
        deep_run_id=deep_run_id,
        hybrid_checkpoint_sha256=checkpoint_sha,
        deep_checkpoint_sha256=deep_checkpoint_sha,
        lineage=lineage,
        comparison_signature_sha256=hybrid.settings.comparison_signature_sha256(),
        metrics=metrics,
        results={
            "run_id": hybrid_run_id,
            "paired_run_id": deep_run_id,
            "baselines": {
                name: report.model_dump(mode="json")
                for name, report in comparison.baselines.items()
            },
            "cold_parity": cold_parity.model_dump(mode="json"),
            "semantic_traps": asdict(traps),
            "victory_matrix": matrix.model_dump(mode="json"),
            "passed": matrix.all_passed,
        },
        victory_matrix=matrix,
    )
    output_dir = artifact_set.directory
    matrix_path = artifact_set.victory_matrix_path

    state_updates = {
        "paired_run_id": deep_run_id,
        "validation_victory_matrix_path": (
            str(matrix_path)
            if split is SplitName.VAL
            else hybrid.state.validation_victory_matrix_path
        ),
        "test_victory_matrix_path": (
            str(matrix_path) if split is SplitName.TEST else hybrid.state.test_victory_matrix_path
        ),
        "validation_gate_passed": (
            matrix.all_passed if split is SplitName.VAL else hybrid.state.validation_gate_passed
        ),
        "test_gate_passed": (
            matrix.all_passed if split is SplitName.TEST else hybrid.state.test_gate_passed
        ),
    }
    next_hybrid = _update_pipeline_state(hybrid.state, **state_updates)
    next_deep = _update_pipeline_state(
        deep.state,
        **{
            "paired_run_id": hybrid_run_id,
            "validation_victory_matrix_path": (
                str(matrix_path)
                if split is SplitName.VAL
                else deep.state.validation_victory_matrix_path
            ),
            "test_victory_matrix_path": (
                str(matrix_path) if split is SplitName.TEST else deep.state.test_victory_matrix_path
            ),
            "validation_gate_passed": (
                matrix.all_passed if split is SplitName.VAL else deep.state.validation_gate_passed
            ),
            "test_gate_passed": (
                matrix.all_passed if split is SplitName.TEST else deep.state.test_gate_passed
            ),
        },
    )
    _write_state(hybrid.settings, next_hybrid)
    _write_state(deep.settings, next_deep)
    if not matrix.all_passed:
        hybrid.lifecycle.transition(
            RunStatus.FAILED, reason=f"{split.value} single-seed gate failed"
        )
        if split is SplitName.TEST and deep.lifecycle.status is RunStatus.TRAINING:
            deep.lifecycle.transition(RunStatus.EVALUATED)
        raise VictoryGateError(f"{split.value} single-seed victory matrix failed")
    if split is SplitName.TEST:
        if hybrid.lifecycle.status is RunStatus.TRAINING:
            hybrid.lifecycle.transition(RunStatus.EVALUATED)
        if deep.lifecycle.status is RunStatus.TRAINING:
            deep.lifecycle.transition(RunStatus.EVALUATED)
    return PairEvaluationResult(
        split=split,
        hybrid_state=next_hybrid,
        deep_state=next_deep,
        artifact_dir=output_dir,
        victory_matrix=matrix,
    )


def _compare_deep_ablations(
    base_settings: Settings,
    *,
    control_run_id: str,
    candidate_run_ids: tuple[str, str, str],
    device: torch.device,
) -> dict[str, object]:
    """Compare four immutable Deep runs without changing their lifecycle."""
    all_run_ids = (control_run_id, *candidate_run_ids)
    if len(set(all_run_ids)) != 4:
        raise ConfigurationError("R3 requires four distinct Deep run IDs")
    loaded = tuple(
        _load_run_context(base_settings, run_id, expected_variant=TrainingVariant.DEEP_ONLY)
        for run_id in all_run_ids
    )
    runs = tuple(
        DeepAblationRun(
            run_id=run.state.run_id,
            settings=run.settings,
            lifecycle_status=run.lifecycle.status,
            git_commit=cast(str, run.lifecycle.document.get("git_commit")),
            lineage={
                "snapshot": run.snapshot.manifest.content_sha256,
                "embedding": run.embedding.manifest.content_sha256,
                "rules": run.rules.manifest.content_sha256,
            },
            snapshot=run.snapshot,
            embeddings=run.embedding.vectors,
            rule_store=run.rules.store,
            model=run.model,
        )
        for run in loaded
    )
    artifact = run_deep_ablation_comparison(
        cast(
            tuple[DeepAblationRun, DeepAblationRun, DeepAblationRun, DeepAblationRun],
            runs,
        ),
        artifact_root=base_settings.data.artifact_root,
        device=device,
    )
    return {
        "artifact_dir": str(artifact.directory),
        "diagnostic_signature": artifact.directory.name,
        "report": artifact.report.model_dump(mode="json"),
    }


def _diagnose_r3(
    base_settings: Settings,
    *,
    hybrid_run_id: str,
    deep_run_id: str,
    device: torch.device,
) -> object:
    """Run the immutable R3 replay; no lifecycle or pipeline state is mutated."""
    hybrid = _load_run_context(
        base_settings, hybrid_run_id, expected_variant=TrainingVariant.HYBRID
    )
    deep = _load_run_context(base_settings, deep_run_id, expected_variant=TrainingVariant.DEEP_ONLY)
    if hybrid.settings.train.seed != deep.settings.train.seed:
        raise ArtifactIntegrityError("R3 diagnostic requires matching seeds")
    artifact = publish_r3_diagnostic(
        hybrid_run=hybrid,
        deep_run=deep,
        split=SplitName.VAL,
        settings=hybrid.settings,
        artifact_root=hybrid.settings.data.artifact_root,
        device=device,
    )
    return {
        "artifact_dir": str(artifact.directory),
        "report": artifact.report.model_dump(mode="json"),
    }


def execute_command(args: Namespace) -> None:
    """Execute one explicit stage without hidden source or embedding fallbacks."""
    settings = _configure(args)
    _seed_everything(settings.train.seed)
    source_kind = DataSourceKind(getattr(args, "source", DataSourceKind.POSTGRES.value))
    embedding_kind = EmbeddingSource(getattr(args, "embedding_source", EmbeddingSource.REAL.value))

    if args.command == "verify-bundle":
        if args.bundle_id and getattr(args, "run_id", None):
            raise ConfigurationError("--bundle-id and --run-id are mutually exclusive")
        configured_bundle: str | Path | None = cast(
            str | Path | None, args.bundle_id or settings.data.model_bundle_path
        )
        if getattr(args, "run_id", None):
            run_id = _validate_artifact_id(str(args.run_id), kind="run ID")
            run_dir = settings.data.artifact_root.resolve() / "runs" / run_id
            try:
                run_state = PipelineState.model_validate_json(
                    (run_dir / "pipeline-state.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError) as error:
                raise ConfigurationError(
                    "--run-id does not reference a valid PipelineState"
                ) from error
            if run_state.run_id != run_id:
                raise ConfigurationError("--run-id does not match PipelineState.run_id")
            if run_state.bundle_path is None:
                raise ConfigurationError("selected run has no bundle_path")
            configured_bundle = run_state.bundle_path
        if configured_bundle is None:
            raise ConfigurationError("--bundle-id, --run-id, or AI_MODEL_BUNDLE_PATH is required")
        path = Path(configured_bundle)
        if args.bundle_id:
            bundle_id = _validate_artifact_id(str(args.bundle_id), kind="bundle ID")
            path = settings.data.artifact_root.resolve() / "bundles" / bundle_id
        elif not path.is_absolute():
            raise ConfigurationError("AI_MODEL_BUNDLE_PATH must be absolute")
        _emit(verify_bundle(path.resolve()).manifest.model_dump(mode="json"))
        return

    if args.command == "release-gate":
        split = SplitName(args.split)
        hybrid_run_ids = getattr(args, "hybrid_run_ids", None)
        deep_run_ids = getattr(args, "deep_run_ids", None)
        if (
            not hybrid_run_ids
            or len(hybrid_run_ids) != 3
            or not deep_run_ids
            or len(deep_run_ids) != 3
        ):
            raise ConfigurationError(
                "--hybrid-run-ids and --deep-run-ids require exactly 3 run IDs each"
            )
        hybrid_dirs = tuple(
            settings.data.artifact_root.resolve()
            / "runs"
            / _validate_artifact_id(str(rid), kind="run ID")
            for rid in hybrid_run_ids
        )
        deep_dirs = tuple(
            settings.data.artifact_root.resolve()
            / "runs"
            / _validate_artifact_id(str(rid), kind="run ID")
            for rid in deep_run_ids
        )
        # Release thresholds and artifact namespace are immutable properties of
        # the finalist runs, not of the caller's ambient/default config.
        try:
            release_settings = load_resolved_settings(
                cast(tuple[Path, Path, Path], hybrid_dirs)[0] / "resolved-config.json"
            )
        except (OSError, ConfigurationError, ValueError) as error:
            raise ArtifactIntegrityError(
                "release finalists must contain a readable resolved configuration"
            ) from error
        release_report = evaluate_three_seed(
            split=split,
            hybrid_run_dirs=cast(tuple[Path, Path, Path], hybrid_dirs),
            deep_run_dirs=cast(tuple[Path, Path, Path], deep_dirs),
            settings=release_settings,
        )
        _emit(release_report.model_dump(mode="json"))
        return

    if args.command == "compare-deep-ablations":
        candidate_ids = tuple(
            _validate_artifact_id(str(run_id), kind="run ID") for run_id in args.candidate_run_ids
        )
        if len(candidate_ids) != 3:
            raise ConfigurationError("--candidate-run-ids requires exactly three run IDs")
        _emit(
            _compare_deep_ablations(
                settings,
                control_run_id=_validate_artifact_id(str(args.control_run_id), kind="run ID"),
                candidate_run_ids=candidate_ids,
                device=_device(args.device),
            )
        )
        return

    if args.command == "diagnose-r3":
        hybrid_run_id = _validate_artifact_id(str(args.hybrid_run_id), kind="run ID")
        deep_run_id = _validate_artifact_id(str(args.deep_run_id), kind="run ID")
        if SplitName(args.split) is not SplitName.VAL:
            raise ConfigurationError("diagnose-r3 is validation-only")
        _emit(
            _diagnose_r3(
                settings,
                hybrid_run_id=hybrid_run_id,
                deep_run_id=deep_run_id,
                device=_device(args.device),
            )
        )
        return

    if args.command == "snapshot":
        _emit(_snapshot(settings, source_kind).manifest.model_dump(mode="json"))
        return

    if args.command == "audit-data":
        snapshot = load_snapshot(settings.data.snapshot_id, settings)
        _emit(DataQualityAuditor().audit(snapshot).model_dump(mode="json"))
        return

    if args.command == "probe-data":
        snapshot = load_snapshot(settings.data.snapshot_id, settings)
        embedding_path = _find_single_parent_artifact(
            settings.data.artifact_root.resolve() / "features",
            snapshot_sha256=snapshot.manifest.content_sha256,
        )
        embedding = load_embedding_artifact(embedding_path)
        rules = None
        if settings.data.rule_feature_schema_version == "3.0.0":
            rule_path = _find_training_rule_artifact(
                settings,
                snapshot.manifest.content_sha256,
            )
            rules = load_rule_artifact(rule_path, snapshot.manifest.num_items)
            _require_rule_training_capability(rules, settings)
        _emit(run_data_probes(settings, snapshot, embedding.vectors, rules))
        return

    if args.command in {"evaluate", "export"}:
        if args.command == "evaluate":
            if not getattr(args, "hybrid_run_id", None) or not getattr(args, "deep_run_id", None):
                raise ConfigurationError("evaluate requires --hybrid-run-id and --deep-run-id")
            result = _evaluate_pair(
                settings,
                hybrid_run_id=args.hybrid_run_id,
                deep_run_id=args.deep_run_id,
                split=SplitName(args.split),
                device=_device(args.device),
            )
            _emit(
                {
                    "split": result.split.value,
                    "hybrid_state": result.hybrid_state.model_dump(mode="json"),
                    "deep_state": result.deep_state.model_dump(mode="json"),
                    "artifact_dir": str(result.artifact_dir),
                    "victory_matrix": result.victory_matrix.model_dump(mode="json"),
                }
            )
            return
        run = _load_run_context(settings, args.run_id, expected_variant=TrainingVariant.HYBRID)
        _emit(
            _export(
                run.settings,
                run.snapshot,
                run.embedding,
                run.rules,
                run.model,
                run.state,
            ).model_dump(mode="json")
        )
        return

    if args.command == "run-all":
        if (
            source_kind is not DataSourceKind.SYNTHETIC
            or embedding_kind is not EmbeddingSource.MOCK
        ):
            raise ConfigurationError(
                "run-all is disabled for production; smoke-only mode requires "
                "synthetic source plus mock embeddings"
            )
        smoke_run_id = getattr(args, "run_id", None)
        if not smoke_run_id:
            raise ConfigurationError("run-all smoke requires --run-id")
        if getattr(args, "config", None) is None:
            raise ConfigurationError("run-all smoke requires --config")
        if settings.train.training_variant is not TrainingVariant.DEEP_ONLY:
            raise ConfigurationError("run-all smoke config must be deep_only")
        if settings.train.max_epochs != 1:
            raise ConfigurationError("run-all smoke config must set max_epochs=1")
        snapshot_path = (
            settings.data.artifact_root.resolve() / "snapshots" / settings.data.snapshot_id
        )
        smoke_snapshot = (
            load_snapshot(settings.data.snapshot_id, settings)
            if snapshot_path.is_dir()
            else _snapshot(settings, source_kind)
        )
        try:
            smoke_embedding_path = _find_single_parent_artifact(
                settings.data.artifact_root.resolve() / "features",
                snapshot_sha256=smoke_snapshot.manifest.content_sha256,
            )
            smoke_embedding = load_embedding_artifact(smoke_embedding_path)
        except ArtifactIntegrityError:
            smoke_embedding = _features(settings, smoke_snapshot, embedding_kind)
        try:
            smoke_rule_path = _find_training_rule_artifact(
                settings, smoke_snapshot.manifest.content_sha256
            )
            smoke_rules = load_rule_artifact(smoke_rule_path, smoke_snapshot.manifest.num_items)
        except ArtifactIntegrityError:
            smoke_rules = _rules(settings, smoke_snapshot)
        smoke_embedding_loaded = load_embedding_artifact(smoke_embedding.artifact_dir)
        smoke_rules_loaded = load_rule_artifact(
            smoke_rules.artifact_dir, smoke_snapshot.manifest.num_items
        )
        _, smoke_state = _train(
            settings,
            smoke_snapshot,
            smoke_embedding_loaded,
            smoke_rules_loaded,
            run_id=str(smoke_run_id),
            device=_device(args.device),
            require_frozen_source=False,
        )
        smoke_run_dir = settings.data.artifact_root.resolve() / "runs" / str(smoke_run_id)
        if not (smoke_run_dir / "checkpoints" / "best.pt").is_file():
            raise ArtifactIntegrityError("run-all smoke did not publish checkpoints/best.pt")
        if not (smoke_run_dir / "checkpoints" / "last.pt").is_file():
            raise ArtifactIntegrityError("run-all smoke did not publish checkpoints/last.pt")
        if (smoke_run_dir / "evaluation").exists():
            raise ArtifactIntegrityError("run-all smoke must not publish evaluation artifacts")
        release_root = (
            settings.data.artifact_root.resolve()
            / "releases"
            / settings.comparison_signature_sha256()
        )
        if (release_root / "validation-gate.json").exists() or (
            release_root / "release-gate.json"
        ).exists():
            raise ArtifactIntegrityError("run-all smoke must not publish release gates")
        if (
            smoke_state.validation_gate_passed
            or smoke_state.test_gate_passed
            or smoke_state.bundle_path
        ):
            raise ArtifactIntegrityError(
                "run-all smoke must not publish validation, test, or bundle state"
            )
        if RunLifecycle.load(smoke_run_dir).status is not RunStatus.TRAINING:
            raise ArtifactIntegrityError("run-all smoke must leave the run in TRAINING")
        _emit(smoke_state.model_dump(mode="json"))
        return

    snapshot = load_snapshot(settings.data.snapshot_id, settings)
    if args.command == "features":
        _emit(_features(settings, snapshot, embedding_kind).manifest.model_dump(mode="json"))
        return
    if args.command == "rules":
        _emit(_rules(settings, snapshot).manifest.model_dump(mode="json"))
        return

    device = _device(args.device)

    if args.command == "train":
        run_id = args.run_id
        if not run_id:
            raise ConfigurationError("--run-id is required for training")
        raw_variant = getattr(args, "variant", None) or settings.train.training_variant.value
        variant_arg = TrainingVariant(raw_variant)
        if variant_arg != settings.train.training_variant:
            raise ConfigurationError(
                "--variant must match config training_variant "
                f"({settings.train.training_variant.value})"
            )
        snapshot = load_snapshot(settings.data.snapshot_id, settings)
        device = _device(args.device)
        artifact_root = settings.data.artifact_root.resolve()
        embedding_path = _find_single_parent_artifact(
            artifact_root / "features", snapshot_sha256=snapshot.manifest.content_sha256
        )
        rule_path = _find_training_rule_artifact(settings, snapshot.manifest.content_sha256)
        embedding = load_embedding_artifact(embedding_path)
        rules = load_rule_artifact(rule_path, snapshot.manifest.num_items)
        _, state = _train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id=run_id,
            device=device,
            resume=bool(getattr(args, "resume", False)),
            require_frozen_source=True,
        )
        _emit(state.model_dump(mode="json"))
        return

    raise ConfigurationError(f"unsupported pipeline command: {args.command}")
