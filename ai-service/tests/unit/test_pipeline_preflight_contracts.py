from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    CheckpointManifest,
    EvaluationReport,
    ModelVariant,
    PipelineState,
    RuleManifest,
    RunStatus,
    SplitName,
    TrainingVariant,
)
from ai_service.data.features import EmbeddingArtifact
from ai_service.data.rules import RuleArtifact, RuleStore
from ai_service.errors import ConfigurationError
from ai_service.evaluation.baselines import BaselineComparisonReport
from ai_service.evaluation.full_catalog import EvaluationResult
from ai_service.evaluation.semantic_traps import SemanticTrapReport
from ai_service.training import pipeline
from ai_service.training.trainer import TrainResult
from tests.support.v5_factories import make_victory_matrix


def test_pipeline_preflight_rejects_invalid_ids_and_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigurationError):
        pipeline._validate_artifact_id("bad/id", kind="run ID")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(ConfigurationError, match="CUDA"):
        pipeline._device("cuda")


def test_pipeline_training_preflight_writes_v5_state_without_release_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 1
    settings.data.num_items = 4
    settings.train.objective = "purchase_bce"
    settings.train.training_variant = TrainingVariant.HYBRID
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(
            artifact_id="snapshot",
            content_sha256="a" * 64,
            num_items=4,
            num_users=1,
        ),
    )
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "feature",
        vectors=np.zeros((4, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = RuleArtifact(
        store=RuleStore(4, [(0, 1, 2.0, 0.1, 0.5, 2)]),
        manifest=RuleManifest(
            artifact_id="rule",
            content_sha256="c" * 64,
            parent_sha256={},
            snapshot_sha256="a" * 64,
            num_directed_rules=1,
            train_basket_count=1,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
            q99_log_lift=1.0,
            feature_schema_version="2.0.0",
            has_full_statistics=True,
        ),
        artifact_dir=tmp_path / "rules" / "rule",
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.status = pipeline.RunStatus.STAGING
            self.document = {
                "lineage": {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
            }

        @classmethod
        def create(cls, run_dir: Path, **_kwargs: object) -> Lifecycle:
            run_dir.mkdir(parents=True, exist_ok=True)
            return cls()

        def transition(self, status: object, reason: str | None = None) -> None:
            self.status = status

    class TrainerStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fit(self, *_args: object, **_kwargs: object) -> TrainResult:
            checkpoint = tmp_path / "runs" / "hybrid-smoke" / "checkpoints" / "best.pt"
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_bytes(b"checkpoint")
            return TrainResult(
                run_id="hybrid-smoke",
                best_epoch=1,
                best_gauc=0.8,
                best_ndcg_at_k=0.2,
                best_hr_at_k=0.3,
                history=(),
                checkpoint_path=checkpoint,
                stop_reason="test",
            )

    monkeypatch.setattr(pipeline, "RunLifecycle", Lifecycle)

    class DatasetStub:
        def __len__(self) -> int:
            return 1

    monkeypatch.setattr(pipeline, "HybridImplicitDataset", lambda *_args, **_kwargs: DatasetStub())
    monkeypatch.setattr(pipeline, "Trainer", TrainerStub)
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda _settings: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_args: object())

    _, state = pipeline._train(
        settings,
        snapshot,
        embedding,
        rules,
        run_id="hybrid-smoke",
        device=torch.device("cpu"),
        require_frozen_source=False,
    )
    assert state.model_schema_version == MODEL_SCHEMA_VERSION
    assert state.checkpoint_path is not None
    assert not (tmp_path / "runs" / "hybrid-smoke" / "release-candidate.pt").exists()


def test_pipeline_sampled_softmax_path_uses_purchase_iterator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.train.objective = "sampled_softmax"
    settings.train.training_variant = TrainingVariant.HYBRID
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(
            artifact_id="snapshot", content_sha256="a" * 64, num_items=4, num_users=1
        )
    )
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "feature",
        vectors=np.zeros((4, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = RuleArtifact(
        store=RuleStore(4, [(0, 1, 2.0, 0.1, 0.5, 2)]),
        manifest=RuleManifest(
            artifact_id="rule",
            content_sha256="c" * 64,
            parent_sha256={},
            snapshot_sha256="a" * 64,
            num_directed_rules=1,
            train_basket_count=1,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
            q99_log_lift=1.0,
            feature_schema_version="2.0.0",
            has_full_statistics=True,
        ),
        artifact_dir=tmp_path / "rules" / "rule",
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.status = pipeline.RunStatus.STAGING
            self.document = {}

        @classmethod
        def create(cls, run_dir: Path, **_kwargs: object) -> Lifecycle:
            run_dir.mkdir(parents=True, exist_ok=True)
            return cls()

        def transition(self, status: object, reason: str | None = None) -> None:
            self.status = status

    class TrainerStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fit(self, *_args: object, **_kwargs: object) -> TrainResult:
            checkpoint = tmp_path / "runs" / "sampled-smoke" / "checkpoints" / "best.pt"
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_bytes(b"checkpoint")
            return TrainResult(
                run_id="sampled-smoke",
                best_epoch=1,
                best_gauc=0.8,
                best_ndcg_at_k=0.2,
                best_hr_at_k=0.3,
                history=(),
                checkpoint_path=checkpoint,
                stop_reason="test",
            )

    monkeypatch.setattr(pipeline, "RunLifecycle", Lifecycle)
    monkeypatch.setattr(
        pipeline, "build_purchase_training_index", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(pipeline, "Trainer", TrainerStub)
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda _settings: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_args: object())
    _, state = pipeline._train(
        settings,
        snapshot,
        embedding,
        rules,
        run_id="sampled-smoke",
        device=torch.device("cpu"),
        require_frozen_source=False,
    )
    assert state.run_id == "sampled-smoke"


def test_pipeline_pair_evaluation_publishes_hybrid_owned_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 1
    settings.data.num_items = 4
    signature = settings.comparison_signature_sha256()
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(content_sha256="a" * 64, artifact_id="snapshot", num_items=4)
    )
    embedding = SimpleNamespace(
        manifest=SimpleNamespace(content_sha256="b" * 64), vectors=np.zeros((4, 768), np.float32)
    )
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256="c" * 64), store=object())

    class Lifecycle:
        def __init__(self, status: RunStatus) -> None:
            self.status = status
            self.document = {
                "lineage": {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
            }

        def transition(self, status: RunStatus, reason: str | None = None) -> None:
            self.status = status

    def loaded(run_id: str, variant: TrainingVariant) -> SimpleNamespace:
        run_dir = tmp_path / "runs" / run_id
        checkpoint = run_dir / "checkpoints" / "best.pt"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(b"checkpoint")
        checkpoint.with_suffix(".pt.manifest.json").write_text(
            json.dumps({"content_sha256": "d" * 64}), encoding="utf-8"
        )
        state = PipelineState(
            model_schema_version=MODEL_SCHEMA_VERSION,
            run_id=run_id,
            training_variant=variant,
            snapshot_id="snapshot",
            embedding_path="embedding",
            rule_path="rules",
            checkpoint_path=str(checkpoint),
            paired_run_id=None,
            validation_gate_passed=False,
            test_gate_passed=False,
            validation_victory_matrix_path=None,
            test_victory_matrix_path=None,
            bundle_path=None,
        )
        return SimpleNamespace(
            run_dir=run_dir,
            checkpoint_manifest=SimpleNamespace(content_sha256="d" * 64),
            settings=settings,
            state=state,
            lifecycle=Lifecycle(RunStatus.TRAINING),
            snapshot=snapshot,
            embedding=embedding,
            rules=rules,
            model=object(),
        )

    def result(variant: ModelVariant, value: float) -> EvaluationResult:
        report = EvaluationReport(
            run_id="fixture",
            split=SplitName.VAL,
            variant=variant,
            num_total_users=1,
            num_eligible_users=1,
            num_users_without_novel_purchase=0,
            num_catalog_items=4,
            hr_at_k=value,
            ndcg_at_k=value,
            gauc=value,
            k=10,
        )
        return EvaluationResult(
            report=report,
            user_ids=np.array([1]),
            per_user_hr=np.array([value]),
            per_user_ndcg=np.array([value]),
            per_user_gauc=np.array([value]),
            top_k_by_user={1: (0,)},
        )

    baseline = result(ModelVariant.HYBRID, 0.9)
    comparison = BaselineComparisonReport(
        apriori_only=result(ModelVariant.ITEM_CF, 0.1),
        sbert_centroid=result(ModelVariant.SBERT_CENTROID, 0.1),
        item_cf=result(ModelVariant.ITEM_CF, 0.1),
        deep_only=result(ModelVariant.DEEP_ONLY, 0.2),
        hybrid=baseline,
        noisy_hybrid=result(ModelVariant.NOISY_HYBRID, 0.8),
        random_seed_results=tuple(result(ModelVariant.RANDOM, 0.5) for _ in range(10)),
    )
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=signature,
    )
    artifact_dir = tmp_path / "runs" / "hybrid-42" / "evaluation" / "val"
    monkeypatch.setattr(
        pipeline,
        "_load_run_context",
        lambda _s, run, *, expected_variant: loaded(run, expected_variant),
    )
    monkeypatch.setattr(pipeline, "prepare_split", lambda *_args: object())
    monkeypatch.setattr(pipeline, "run_seven_way_baselines", lambda **_kwargs: comparison)
    monkeypatch.setattr(
        pipeline,
        "evaluate_cold_parity",
        lambda *_args, **_kwargs: SimpleNamespace(model_dump=lambda **_: {}),
    )
    monkeypatch.setattr(
        pipeline,
        "evaluate_semantic_traps",
        lambda *_args, **_kwargs: SemanticTrapReport(
            passed=10, total=10, all_passed=True, results=()
        ),
    )
    monkeypatch.setattr(pipeline, "evaluate_single_seed", lambda *_args, **_kwargs: matrix)
    monkeypatch.setattr(
        pipeline,
        "publish_evaluation_artifacts",
        lambda **_kwargs: SimpleNamespace(
            directory=artifact_dir, victory_matrix_path=artifact_dir / "victory-matrix.json"
        ),
    )
    monkeypatch.setattr(pipeline, "_write_state", lambda *_args: None)

    result_pair = pipeline._evaluate_pair(
        settings,
        hybrid_run_id="hybrid-42",
        deep_run_id="deep-42",
        split=SplitName.VAL,
        device=torch.device("cpu"),
    )
    assert result_pair.victory_matrix is matrix
    assert result_pair.hybrid_state.paired_run_id == "deep-42"


def test_pipeline_load_run_context_verifies_typed_checkpoint_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.train.training_variant = TrainingVariant.HYBRID
    run_dir = tmp_path / "runs" / "hybrid-context"
    checkpoint = run_dir / "checkpoints" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    settings_path = run_dir / "resolved-config.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings.resolved_document()), encoding="utf-8")
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="hybrid-context",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot",
        embedding_path="embedding",
        rule_path="rules",
        checkpoint_path=str(checkpoint),
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
    )
    (run_dir / "pipeline-state.json").write_text(
        json.dumps(state.model_dump(mode="json")), encoding="utf-8"
    )
    manifest = CheckpointManifest(
        artifact_id="best",
        content_sha256="d" * 64,
        parent_sha256={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        run_id="hybrid-context",
        snapshot_sha256="a" * 64,
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
        training_signature_sha256=settings.training_signature_sha256(),
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        training_variant=TrainingVariant.HYBRID,
        model_schema_version=MODEL_SCHEMA_VERSION,
        best_epoch=1,
        best_val_gauc=0.8,
        best_val_ndcg_at_k=0.2,
        best_val_hr_at_k=0.3,
        checkpoint_kind="best",
        schema_version=MODEL_SCHEMA_VERSION,
    )
    checkpoint.with_suffix(".pt.manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json")), encoding="utf-8"
    )
    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda _path: SimpleNamespace(
            status=RunStatus.TRAINING,
            document={
                "training_variant": TrainingVariant.HYBRID.value,
                "lineage": {
                    "snapshot": "a" * 64,
                    "embedding": "b" * 64,
                    "rules": "c" * 64,
                },
            },
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_load_lineage",
        lambda *_args, **_kwargs: (
            SimpleNamespace(manifest=SimpleNamespace(content_sha256="a" * 64)),
            SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64)),
            SimpleNamespace(
                manifest=SimpleNamespace(
                    content_sha256="c" * 64,
                    feature_schema_version="2.0.0",
                    min_count=settings.data.min_rule_count,
                    min_lift=settings.data.min_rule_lift,
                ),
                require_training_capability=object,
            ),
            object(),
        ),
    )
    loaded = pipeline._load_run_context(
        settings, "hybrid-context", expected_variant=TrainingVariant.HYBRID
    )
    assert loaded.checkpoint_manifest.run_id == "hybrid-context"
