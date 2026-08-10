"""Fail-closed orchestration for one immutable training and serving lineage."""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
from argparse import Namespace
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from ai_service.config import MODEL_SCHEMA_VERSION, Settings, load_settings
from ai_service.contracts import DataSourceKind, EmbeddingSource, RunStatus, SplitName
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
from ai_service.data.rules import AprioriRuleMiner, RuleArtifact, load_rule_artifact
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot, SnapshotBuilder, load_snapshot
from ai_service.data.sources import DatasetSource, PostgresDatasetSource, SyntheticDatasetSource
from ai_service.errors import ArtifactIntegrityError, ConfigurationError, DataIntegrityError
from ai_service.evaluation.baselines import BaselineComparisonReport, run_seven_way_baselines
from ai_service.evaluation.cold_start import evaluate_cold_start
from ai_service.evaluation.full_catalog import FullCatalogEvaluator
from ai_service.evaluation.metrics import BootstrapInterval, paired_bootstrap_delta
from ai_service.evaluation.probes import run_data_probes
from ai_service.evaluation.release import aggregate_three_seed_release
from ai_service.evaluation.report import write_evaluation_report
from ai_service.evaluation.semantic_traps import evaluate_semantic_traps
from ai_service.export.bundle import BundlePublisher, file_sha256, verify_bundle
from ai_service.export.onnx import export_onnx_models
from ai_service.export.parity import verify_onnx_parity
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle
from ai_service.training.trainer import Trainer


@dataclass(frozen=True)
class PipelineState:
    run_id: str
    training_variant: str = "hybrid"
    snapshot_id: str = ""
    embedding_path: str = ""
    rule_path: str = ""
    checkpoint_path: str | None = None
    paired_run_id: str | None = None
    validation_gate_passed: bool = False
    test_gate_passed: bool = False
    evaluation_passed: bool = False
    victory_matrix_path: str | None = None
    bundle_path: str | None = None


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
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _load_state(settings: Settings, run_id: str | None) -> PipelineState:
    if not run_id:
        raise ConfigurationError("--run-id is required for this command")
    path = _state_path(settings, run_id)
    if not path.is_file():
        raise ArtifactIntegrityError(f"pipeline state does not exist: {path}")
    return PipelineState(**json.loads(path.read_text(encoding="utf-8")))


def _configure(args: Namespace) -> Settings:
    settings = load_settings(getattr(args, "config", None))
    store_id = int(args.store_id)
    if store_id <= 0:
        raise ConfigurationError("--store-id must be positive")
    settings.data.store_id = store_id
    if args.snapshot_id:
        settings.data.snapshot_id = _validate_artifact_id(str(args.snapshot_id), kind="snapshot ID")
    if args.benchmark_run_id:
        settings.data.benchmark_run_id = str(args.benchmark_run_id)
    settings.train.seed = int(args.seed)
    if settings.serving.environment.lower() == "production" and (
        args.source != DataSourceKind.POSTGRES.value
        or args.embedding_source != EmbeddingSource.REAL.value
    ):
        raise ConfigurationError("production requires postgres and real embedding adapters")
    settings.validate_production(serving=args.command == "verify-bundle")
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


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parents[4],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


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
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            if document.get("snapshot_sha256") == snapshot_sha256:
                matches.append(manifest_path.parent)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            f"expected exactly one artifact below {root} for snapshot; found {len(matches)}"
        )
    return matches[0]


def _train(
    settings: Settings,
    snapshot: Snapshot,
    embedding: EmbeddingArtifact,
    rules: RuleArtifact,
    *,
    run_id: str,
    device: torch.device,
    resume: bool = False,
) -> tuple[HybridTwoTowerModel, PipelineState]:
    run_id = _validate_artifact_id(run_id, kind="run ID")
    run_dir = settings.data.artifact_root.resolve() / "runs" / run_id
    lineage = {
        "snapshot": snapshot.manifest.content_sha256,
        "embedding": embedding.manifest.content_sha256,
        "rules": rules.manifest.content_sha256,
    }
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
    else:
        lifecycle = RunLifecycle.create(
            run_dir,
            settings=settings,
            lineage=lineage,
            git_commit=_git_commit(),
        )
    lifecycle.transition(RunStatus.TRAINING)
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
        )
        loader: Any = PurchaseBatchIterator(
            purchase_index,
            sampler,
            batch_size=settings.train.batch_size,
            seed=settings.train.seed,
        )
    else:
        dataset = HybridImplicitDataset(
            snapshot,
            rules.store,
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
    model = HybridTwoTowerModel(settings)
    evaluator = FullCatalogEvaluator(settings, embedding.vectors, rules.store)
    trainer = Trainer(model, settings=settings, run_dir=run_dir, device=device)
    try:
        result = trainer.fit(
            loader,
            snapshot,
            embedding.vectors,
            evaluator,
            lineage,
            resume_from=(
                run_dir / "checkpoints" / "last.pt"
                if resume and (run_dir / "checkpoints" / "last.pt").is_file()
                else None
            ),
        )
    except BaseException as error:
        lifecycle.transition(RunStatus.INTERRUPTED, reason=type(error).__name__)
        raise
    try:
        if settings.train.enable_wide_calibration:
            _, release_optimizer = WideCalibrator(settings).fit(
                model,
                snapshot,
                rules.store,
                device=device,
                output_path=run_dir / "training" / "wide-calibration.json",
            )
        else:
            release_optimizer = trainer.optimizer
        release_checkpoint = run_dir / "checkpoints" / "release-candidate.pt"
        CheckpointManager.save(
            release_checkpoint,
            model=model,
            optimizer=release_optimizer,
            scheduler=None,
            epoch=result.best_epoch,
            metrics={
                "val_gauc": result.best_gauc,
                "val_ndcg_at_k": result.best_ndcg_at_k,
                "train_loss": result.history[-1].train_loss,
            },
            lineage=lineage,
            training_signature_sha256=settings.training_signature_sha256(),
            model_schema_version=MODEL_SCHEMA_VERSION,
            run_id=run_id,
        )
    except BaseException as error:
        lifecycle.transition(RunStatus.INTERRUPTED, reason=type(error).__name__)
        raise
    state = PipelineState(
        run_id=run_id,
        snapshot_id=snapshot.manifest.artifact_id,
        embedding_path=str(embedding.artifact_dir),
        rule_path=str(rules.artifact_dir),
        checkpoint_path=str(release_checkpoint),
    )
    _write_state(settings, state)
    return model, state


def _interval(candidate: np.ndarray, baseline: np.ndarray, settings: Settings) -> BootstrapInterval:
    return paired_bootstrap_delta(
        candidate,
        baseline,
        samples=settings.eval.bootstrap_samples,
        seed=settings.train.seed,
    )


def _comparison_gates(
    comparison: BaselineComparisonReport,
    settings: Settings,
) -> dict[str, Any]:
    hybrid = comparison.results["Proposed Hybrid (Ours)"]
    gate_document: dict[str, Any] = {}
    passed = True
    comparison_names = (
        "Deep-Only Two-Tower",
        "Rule-based Apriori",
        "Item-Item CF",
    )
    for name in comparison_names:
        baseline = comparison.results[name]
        intervals = {
            "gauc": _interval(hybrid.per_user_gauc, baseline.per_user_gauc, settings),
            "hr_at_k": _interval(hybrid.per_user_hr, baseline.per_user_hr, settings),
            "ndcg_at_k": _interval(hybrid.per_user_ndcg, baseline.per_user_ndcg, settings),
        }
        gauc_margin = -0.010 if name == "Item-Item CF" else -0.002
        gate_passed = (
            intervals["gauc"].lower >= gauc_margin and intervals["hr_at_k"].lower >= -0.001
        )
        if name != "Item-Item CF":
            gate_passed &= intervals["ndcg_at_k"].lower >= -0.001
        gate_document[name] = {
            "passed": gate_passed,
            "intervals": {metric: asdict(value) for metric, value in intervals.items()},
        }
        passed &= gate_passed
    strongest_name = max(
        comparison_names,
        key=lambda name: comparison.results[name].report.ndcg_at_k,
    )
    strongest = comparison.results[strongest_name]
    strongest_ndcg_interval = _interval(
        hybrid.per_user_ndcg,
        strongest.per_user_ndcg,
        settings,
    )
    relative_ndcg_passed = (
        hybrid.report.ndcg_at_k >= strongest.report.ndcg_at_k * 1.05
        and strongest_ndcg_interval.lower > 0.0
    )
    gate_document["strongest_ndcg_baseline"] = {
        "name": strongest_name,
        "passed": relative_ndcg_passed,
        "hybrid_ndcg_at_k": hybrid.report.ndcg_at_k,
        "baseline_ndcg_at_k": strongest.report.ndcg_at_k,
        "delta_ci": asdict(strongest_ndcg_interval),
    }
    # This is diagnostic for a single seed.  The release contract applies the
    # 5% uplift and paired CI to the aggregate of all three locked seeds.
    # Seeds are repeated measurements of the same users, not independent
    # bootstrap units.  Average across seeds first, then resample users.
    random_gauc = np.stack(
        [result.per_user_gauc for result in comparison.random_seed_results]
    ).mean(axis=0)
    random_interval = _interval(random_gauc, np.full_like(random_gauc, 0.5), settings)
    random_mean = float(random_gauc.mean())
    random_passed = (
        0.48 <= random_mean <= 0.52 and random_interval.lower <= 0.0 <= random_interval.upper
    )
    gate_document["random"] = {
        "passed": random_passed,
        "mean_gauc": random_mean,
        "delta_from_half_ci": asdict(random_interval),
    }
    gate_document["passed"] = passed and random_passed
    return gate_document


def _evaluate(
    settings: Settings,
    snapshot: Snapshot,
    embedding: EmbeddingArtifact,
    rules: RuleArtifact,
    model: HybridTwoTowerModel,
    state: PipelineState,
    *,
    device: torch.device,
) -> PipelineState:
    comparison = run_seven_way_baselines(
        model,
        snapshot,
        embeddings=embedding.vectors,
        rule_store=rules.store,
        split=SplitName.TEST,
        settings=settings,
        device=device,
    )
    gates = _comparison_gates(comparison, settings)
    hybrid = comparison.results["Proposed Hybrid (Ours)"]
    centroid = comparison.results["SBERT User Centroid"]
    hybrid_cold = evaluate_cold_start(hybrid, snapshot, rules.store)
    centroid_cold = evaluate_cold_start(centroid, snapshot, rules.store)
    cold_passed = (
        hybrid_cold.num_cold_items_with_test_purchase == settings.data.num_cold_items
        and hybrid_cold.ndcg_at_k >= centroid_cold.ndcg_at_k - 0.001
    )
    fixture = Path(__file__).parents[1] / "evaluation" / "fixtures" / "semantic_traps.json"
    traps = evaluate_semantic_traps(
        model,
        snapshot,
        embedding.vectors,
        rules.store,
        fixture,
        k=settings.eval.k,
        device=device,
    )
    traps_passed = traps.total == 10 and traps.passed == 10
    evaluation_passed = bool(gates["passed"] and cold_passed and traps_passed)
    if state.checkpoint_path is None:
        raise ArtifactIntegrityError("evaluation requires a checkpoint")
    checkpoint_manifest = Path(state.checkpoint_path).with_suffix(".pt.manifest.json")
    checkpoint_sha = json.loads(checkpoint_manifest.read_text(encoding="utf-8"))["content_sha256"]
    payload = {
        "baselines": {
            name: report.model_dump(mode="json") for name, report in comparison.baselines.items()
        },
        "bootstrap_gates": gates,
        "cold_start": {
            "hybrid": asdict(hybrid_cold),
            "sbert_centroid": asdict(centroid_cold),
            "passed": cold_passed,
        },
        "semantic_traps": {**asdict(traps), "passed_gate": traps_passed},
        "passed": evaluation_passed,
    }
    run_dir = Path(state.checkpoint_path).parents[1]
    metrics_temporary = run_dir / "per-user-metrics.tmp.npz"
    np.savez_compressed(
        metrics_temporary,
        user_ids=hybrid.user_ids,
        hybrid_hr=hybrid.per_user_hr,
        hybrid_ndcg=hybrid.per_user_ndcg,
        hybrid_gauc=hybrid.per_user_gauc,
        deep_hr=comparison.results["Deep-Only Two-Tower"].per_user_hr,
        deep_ndcg=comparison.results["Deep-Only Two-Tower"].per_user_ndcg,
        deep_gauc=comparison.results["Deep-Only Two-Tower"].per_user_gauc,
        wide_hr=comparison.results["Rule-based Apriori"].per_user_hr,
        wide_ndcg=comparison.results["Rule-based Apriori"].per_user_ndcg,
        wide_gauc=comparison.results["Rule-based Apriori"].per_user_gauc,
        item_cf_hr=comparison.results["Item-Item CF"].per_user_hr,
        item_cf_ndcg=comparison.results["Item-Item CF"].per_user_ndcg,
        item_cf_gauc=comparison.results["Item-Item CF"].per_user_gauc,
    )
    payload["per_user_metrics_sha256"] = file_sha256(metrics_temporary)
    evaluation_dir = run_dir / "evaluation"
    write_evaluation_report(
        evaluation_dir,
        payload=payload,
        lineage={
            "snapshot": snapshot.manifest.content_sha256,
            "embedding": embedding.manifest.content_sha256,
            "rules": rules.manifest.content_sha256,
            "checkpoint": checkpoint_sha,
        },
    )
    os.replace(metrics_temporary, evaluation_dir / "per-user-metrics.npz")
    next_state = PipelineState(**{**asdict(state), "evaluation_passed": evaluation_passed})
    _write_state(settings, next_state)
    lifecycle = RunLifecycle.load(Path(state.checkpoint_path).parents[1])
    lifecycle.transition(RunStatus.EVALUATED, reason=None if evaluation_passed else "gates failed")
    if not evaluation_passed:
        raise DataIntegrityError("model release gates failed; ONNX export is blocked")
    return next_state


def _export(
    settings: Settings,
    snapshot: Snapshot,
    embedding: EmbeddingArtifact,
    rules: RuleArtifact,
    model: HybridTwoTowerModel,
    state: PipelineState,
) -> PipelineState:
    if not state.evaluation_passed or state.checkpoint_path is None:
        raise DataIntegrityError("only an evaluated best checkpoint may be exported")
    lifecycle = RunLifecycle.load(Path(state.checkpoint_path).parents[1])
    if lifecycle.status is not RunStatus.SEALED:
        raise DataIntegrityError("only a sealed training run may be exported")
    experiment_signature = lifecycle.document["experiment_signature_sha256"]
    release_path = (
        settings.data.artifact_root.resolve()
        / "releases"
        / experiment_signature
        / "release-gate.json"
    )
    if not release_path.is_file():
        raise DataIntegrityError("three-seed aggregate release gate has not been published")
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if not release.get("passed") or release.get("selected_run_id") != state.run_id:
        raise DataIntegrityError("this run was not selected by the aggregate release gate")
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
    bundle = BundlePublisher(settings).publish(
        bundle_id=bundle_id,
        run_id=state.run_id,
        snapshot=snapshot,
        rule_store=rules.store,
        ranker_path=paths.ranker,
        item_vectors=item_vectors,
        user_profile_vectors=user_profiles,
        semantic_vectors=np.asarray(embedding.vectors, dtype=np.float32),
        checkpoint_sha256=checkpoint_sha,
        parity=parity,
    )
    next_state = PipelineState(**{**asdict(state), "bundle_path": str(bundle.path)})
    _write_state(settings, next_state)
    return next_state


def _load_lineage(
    settings: Settings, state: PipelineState
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
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
        )
    return snapshot, embedding, rules, model


def execute_command(args: Namespace) -> None:
    """Execute one explicit stage without hidden source or embedding fallbacks."""
    settings = _configure(args)
    _seed_everything(settings.train.seed)
    source_kind = DataSourceKind(args.source)
    embedding_kind = EmbeddingSource(args.embedding_source)

    if args.command == "verify-bundle":
        configured_bundle = args.bundle_id or settings.data.model_bundle_path
        if configured_bundle is None:
            raise ConfigurationError("--bundle-id or AI_MODEL_BUNDLE_PATH is required")
        path = Path(configured_bundle)
        if args.bundle_id:
            bundle_id = _validate_artifact_id(str(args.bundle_id), kind="bundle ID")
            path = settings.data.artifact_root.resolve() / "bundles" / bundle_id
        elif not path.is_absolute():
            raise ConfigurationError("AI_MODEL_BUNDLE_PATH must be absolute")
        _emit(verify_bundle(path.resolve()).manifest.model_dump(mode="json"))
        return

    if args.command == "release-gate":
        run_ids = getattr(args, "run_ids", None)
        if not run_ids or len(run_ids) != 3:
            raise ConfigurationError("--run-ids requires exactly three finalist runs")
        run_dirs = tuple(
            settings.data.artifact_root.resolve()
            / "runs"
            / _validate_artifact_id(str(run_id), kind="run ID")
            for run_id in run_ids
        )
        _emit(aggregate_three_seed_release(settings, cast(tuple[Path, Path, Path], run_dirs)))
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
        _emit(run_data_probes(settings, snapshot, embedding.vectors))
        return

    if args.command in {"evaluate", "export"}:
        state = _load_state(settings, args.run_id)
        snapshot, embedding, rules, model = _load_lineage(settings, state)
        if args.command == "evaluate":
            _emit(
                asdict(
                    _evaluate(
                        settings,
                        snapshot,
                        embedding,
                        rules,
                        model,
                        state,
                        device=_device(args.device),
                    )
                )
            )
            return
        _emit(asdict(_export(settings, snapshot, embedding, rules, model, state)))
        return

    snapshot = (
        _snapshot(settings, source_kind)
        if args.command == "run-all"
        else load_snapshot(settings.data.snapshot_id, settings)
    )
    if args.command == "features":
        _emit(_features(settings, snapshot, embedding_kind).manifest.model_dump(mode="json"))
        return
    if args.command == "rules":
        _emit(_rules(settings, snapshot).manifest.model_dump(mode="json"))
        return

    device = _device(args.device)

    if args.command == "run-all":
        embedding = _features(settings, snapshot, embedding_kind)
        rules = _rules(settings, snapshot)
        run_id = args.run_id or (
            f"run-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{snapshot.manifest.content_sha256[:8]}"
        )
        model, state = _train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id=run_id,
            device=device,
            resume=False,
        )
        state = _evaluate(settings, snapshot, embedding, rules, model, state, device=device)
        _emit(asdict(state))
        return

    if args.command == "train":
        run_id = args.run_id
        if not run_id:
            raise ConfigurationError("--run-id is required for training")
        artifact_root = settings.data.artifact_root.resolve()
        embedding_path = _find_single_parent_artifact(
            artifact_root / "features", snapshot_sha256=snapshot.manifest.content_sha256
        )
        rule_path = _find_single_parent_artifact(
            artifact_root / "rules", snapshot_sha256=snapshot.manifest.content_sha256
        )
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
        )
        _emit(asdict(state))
        return

    raise ConfigurationError(f"unsupported pipeline command: {args.command}")
