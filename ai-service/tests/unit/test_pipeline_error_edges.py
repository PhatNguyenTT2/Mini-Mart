from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ai_service.config import MODEL_SCHEMA_VERSION
from ai_service.contracts import RuleManifest, RunStatus, TerminalAction, TrainingVariant
from ai_service.data.features import EmbeddingArtifact
from ai_service.data.rules import RuleArtifact
from ai_service.errors import (
    ArtifactIntegrityError,
    CatastrophicTrainingError,
    TrainingInterruptedError,
)
from ai_service.training import pipeline
from ai_service.training.trainer import TrainResult
from tests.support.v5_factories import make_settings, make_snapshot


def _rules(tmp_path: Path, snapshot_sha: str) -> RuleArtifact:
    manifest = RuleManifest(
        artifact_id="rule",
        content_sha256="c" * 64,
        parent_sha256={"snapshot": snapshot_sha},
        snapshot_sha256=snapshot_sha,
        num_directed_rules=0,
        train_basket_count=1,
        min_count=3,
        min_lift=1.0,
        q99_log_lift=1.0,
        feature_schema_version="2.0.0",
        has_full_statistics=True,
    )
    return RuleArtifact(
        store=SimpleNamespace(),
        manifest=manifest,
        artifact_dir=tmp_path / "rules" / "rule",
    )


@pytest.mark.parametrize(
    "failure",
    [
        CatastrophicTrainingError("catastrophe"),
        TrainingInterruptedError("interrupted"),
        RuntimeError("unexpected"),
    ],
)
def test_pipeline_maps_training_failures_to_terminal_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: BaseException,
) -> None:
    settings = make_settings(tmp_path)
    settings.train.objective = "sampled_softmax"
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = _rules(tmp_path, snapshot.manifest.content_sha256)

    class Lifecycle:
        status = RunStatus.STAGING

        def __init__(self) -> None:
            self.document = {
                "lineage": {
                    "snapshot": snapshot.manifest.content_sha256,
                    "embedding": "b" * 64,
                    "rules": "c" * 64,
                }
            }
            self.terminal: tuple[RunStatus, str] | None = None

        @classmethod
        def create(cls, run_dir: Path, **_kwargs: object) -> Lifecycle:
            run_dir.mkdir(parents=True, exist_ok=True)
            return cls()

        def transition(self, status: RunStatus, **_kwargs: object) -> None:
            self.status = status

        def transition_training_terminal(self, status: RunStatus, *, reason: str) -> None:
            self.terminal = (status, reason)
            self.status = status

    lifecycle = Lifecycle()
    monkeypatch.setattr(
        pipeline, "RunLifecycle", SimpleNamespace(create=lambda *_a, **_k: lifecycle)
    )
    monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda _settings: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_a: object())

    class TrainerStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fit(self, *_args: object, **_kwargs: object) -> TrainResult:
            raise failure

    monkeypatch.setattr(pipeline, "Trainer", TrainerStub)
    with pytest.raises(type(failure)):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="failure-edge",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    summary = json.loads(
        (tmp_path / "runs" / "failure-edge" / "training" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["terminal_action"] in {"failed", "interrupted"}


def test_pipeline_transition_failure_is_terminalized_as_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path)
    settings.train.objective = "sampled_softmax"
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = _rules(tmp_path, snapshot.manifest.content_sha256)

    class Lifecycle:
        status = RunStatus.STAGING

        def __init__(self) -> None:
            self.document = {"git_commit": "0" * 40}

        @classmethod
        def create(cls, run_dir: Path, **_kwargs: object) -> Lifecycle:
            run_dir.mkdir(parents=True, exist_ok=True)
            return cls()

        def transition(self, _status: RunStatus, **_kwargs: object) -> None:
            raise RuntimeError("transition persistence")

        def transition_training_terminal(self, status: RunStatus, *, reason: str) -> None:
            assert status is RunStatus.FAILED
            self.status = status
            self.document["status_reason"] = reason

    lifecycle = Lifecycle()
    monkeypatch.setattr(
        pipeline, "RunLifecycle", SimpleNamespace(create=lambda *_a, **_k: lifecycle)
    )
    monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda _settings: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_a: object())

    with pytest.raises(RuntimeError, match="transition persistence"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="transition-failure",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    summary = json.loads(
        (tmp_path / "runs" / "transition-failure" / "training" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["terminal_action"] == "failed"
    assert summary["terminal_reason"] == "RuntimeError"


def test_terminal_summary_write_failure_is_reported_as_artifact_integrity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = SimpleNamespace(status=RunStatus.TRAINING)
    monkeypatch.setattr(
        pipeline,
        "_ensure_training_terminal_summary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk failure")),
    )

    with pytest.raises(ArtifactIntegrityError, match="could not be terminalized") as raised:
        pipeline._terminalize_training_session(
            lifecycle,
            tmp_path,
            requested_action=TerminalAction.INTERRUPTED,
            reason="RuntimeError",
        )

    assert isinstance(raised.value.__cause__, OSError)


@pytest.mark.parametrize("failure_target", ["index", "sampler", "iterator", "model", "evaluator"])
def test_training_preflight_failure_does_not_publish_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_target: str
) -> None:
    settings = make_settings(tmp_path)
    settings.train.objective = "sampled_softmax"
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = _rules(tmp_path, snapshot.manifest.content_sha256)
    failure = RuntimeError(failure_target)

    if failure_target == "index":
        monkeypatch.setattr(
            pipeline,
            "build_purchase_training_index",
            lambda *_a, **_k: (_ for _ in ()).throw(failure),
        )
    else:
        monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_a, **_k: object())
    if failure_target == "sampler":
        monkeypatch.setattr(
            pipeline, "MixedNegativeSampler", lambda *_a, **_k: (_ for _ in ()).throw(failure)
        )
    else:
        monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_a, **_k: object())
    if failure_target == "iterator":
        monkeypatch.setattr(
            pipeline, "PurchaseBatchIterator", lambda *_a, **_k: (_ for _ in ()).throw(failure)
        )
    else:
        monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_a, **_k: object())
    if failure_target == "model":
        monkeypatch.setattr(
            pipeline, "HybridTwoTowerModel", lambda *_a, **_k: (_ for _ in ()).throw(failure)
        )
    else:
        monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda *_a, **_k: object())
    if failure_target == "evaluator":
        monkeypatch.setattr(
            pipeline, "FullCatalogEvaluator", lambda *_a, **_k: (_ for _ in ()).throw(failure)
        )
    else:
        monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_a, **_k: object())

    with pytest.raises(RuntimeError, match=failure_target):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id=f"preflight-{failure_target}",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    assert not (tmp_path / "runs" / f"preflight-{failure_target}").exists()


def test_production_r3_selection_is_verified_before_training_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise the production receipt gate before any run directory is created."""
    settings = make_settings(tmp_path)
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.train.campaign_stage = "production"
    settings.train.r3_selection_artifact_sha256 = "d" * 64
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = SimpleNamespace(
        manifest=SimpleNamespace(
            feature_schema_version="3.0.0",
            snapshot_sha256=snapshot.manifest.content_sha256,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
            content_sha256="c" * 64,
        ),
        require_training_capability=lambda _settings: object(),
    )
    selected_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        pipeline,
        "require_selected_r3_pair",
        lambda **kwargs: selected_calls.append(kwargs),
    )
    failure = RuntimeError("production preflight")
    monkeypatch.setattr(
        pipeline,
        "build_purchase_training_index",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(RuntimeError, match="production preflight"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,  # type: ignore[arg-type]
            run_id="production-preflight",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )

    assert selected_calls and selected_calls[0]["campaign_stage"] == "production"
    assert not (tmp_path / "runs" / "production-preflight").exists()


def test_trainer_setup_failure_is_terminal_and_resumable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path)
    settings.train.objective = "sampled_softmax"
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = _rules(tmp_path, snapshot.manifest.content_sha256)
    monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_a, **_k: object())

    class TrainerStub:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("trainer setup")

    monkeypatch.setattr(pipeline, "Trainer", TrainerStub)
    with pytest.raises(RuntimeError, match="trainer setup"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="trainer-setup-failure",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    run_dir = tmp_path / "runs" / "trainer-setup-failure"
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "training" / "summary.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert manifest["status_reason"] == "RuntimeError"
    assert summary["terminal_action"] == "interrupted"
    assert summary["terminal_reason"] == "RuntimeError"


def test_pipeline_state_publication_failure_is_terminal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path)
    settings.train.objective = "sampled_softmax"
    snapshot = make_snapshot(tmp_path)
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = _rules(tmp_path, snapshot.manifest.content_sha256)
    monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda *_a, **_k: object())
    monkeypatch.setattr(pipeline, "FullCatalogEvaluator", lambda *_a, **_k: object())
    monkeypatch.setattr(
        pipeline,
        "Trainer",
        type(
            "TrainerStub",
            (),
            {
                "__init__": lambda self, *_a, **_k: None,
                "fit": lambda self, *_a, **_k: TrainResult(
                    run_id="state-write-failure",
                    best_epoch=1,
                    best_gauc=0.8,
                    best_ndcg_at_k=0.1,
                    best_hr_at_k=0.2,
                    history=(),
                    checkpoint_path=tmp_path / "best.pt",
                    stop_reason="done",
                ),
            },
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_write_state",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("state write")),
    )

    with pytest.raises(RuntimeError, match="state write"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="state-write-failure",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    run_dir = tmp_path / "runs" / "state-write-failure"
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "training" / "summary.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert summary["terminal_reason"] == "RuntimeError"


def _write_rule_manifest(
    path: Path,
    *,
    snapshot_sha: str,
    full: bool,
    schema: str = "2.0.0",
    coverage_semantics_version: str | None = None,
    coverage: dict[str, object] | None = None,
) -> None:
    path.mkdir(parents=True)
    document = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "artifact_id": path.name,
        "content_sha256": "c" * 64,
        "parent_sha256": {"snapshot": snapshot_sha},
        "snapshot_sha256": snapshot_sha,
        "num_directed_rules": 0,
        "train_basket_count": 1,
        "min_count": 3,
        "min_lift": 1.0,
        "q99_log_lift": 1.0,
        "feature_schema_version": schema,
        "has_full_statistics": full,
    }
    if coverage_semantics_version is not None:
        document["coverage_semantics_version"] = coverage_semantics_version
    if coverage is not None:
        document["coverage"] = coverage
    (path / "manifest.json").write_text(json.dumps(document), encoding="utf-8")


def test_training_rule_selector_rejects_legacy_and_ambiguous_artifacts(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    root = tmp_path / "rules"
    snapshot_sha = "a" * 64
    with pytest.raises(ArtifactIntegrityError, match="found 0"):
        pipeline._find_training_rule_artifact(settings, snapshot_sha)
    _write_rule_manifest(root / "legacy", snapshot_sha=snapshot_sha, full=False)
    with pytest.raises(ArtifactIntegrityError, match="found 0"):
        pipeline._find_training_rule_artifact(settings, snapshot_sha)
    _write_rule_manifest(root / "full-a", snapshot_sha=snapshot_sha, full=True)
    _write_rule_manifest(root / "full-b", snapshot_sha=snapshot_sha, full=True)
    with pytest.raises(ArtifactIntegrityError, match="found 2"):
        pipeline._find_training_rule_artifact(settings, snapshot_sha)
    (root / "full-b" / "manifest.json").unlink()
    assert pipeline._find_training_rule_artifact(settings, snapshot_sha).name == "full-a"


def test_training_rule_selector_ignores_legacy_v3_coverage_semantics(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.data.rule_feature_schema_version = "3.0.0"
    root = tmp_path / "rules"
    snapshot_sha = "a" * 64
    _write_rule_manifest(root / "legacy-v3", snapshot_sha=snapshot_sha, full=True, schema="3.0.0")
    _write_rule_manifest(
        root / "semantic-trap-purchase-v3",
        snapshot_sha=snapshot_sha,
        full=True,
        schema="3.0.0",
        coverage_semantics_version="organic-target-alignment-v3",
        coverage={
            "total_directed_rules": 100,
            "non_trap_directed_rules": 90,
            "trap_anchored_directed_rules": 10,
            "trap_anchored_rule_fraction": 0.1,
            "distinct_organic_rule_items": 50,
            "eligible_val_context_users": 10,
            "val_context_users_with_rule": 8,
            "val_context_rule_coverage": 0.8,
            "full_catalog_organic_pair_coverage": 0.01,
        },
    )

    selected = pipeline._find_training_rule_artifact(settings, snapshot_sha)

    assert selected.name == "semantic-trap-purchase-v3"


def test_training_rule_selector_filters_every_resolved_coverage_threshold(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.data.minimum_non_trap_directed_rules = 80
    settings.data.minimum_distinct_organic_rule_items = 40
    settings.data.minimum_val_context_rule_coverage = 0.7
    settings.data.maximum_trap_anchored_rule_fraction = 0.2
    root = tmp_path / "rules"
    snapshot_sha = "a" * 64
    base_coverage: dict[str, object] = {
        "total_directed_rules": 100,
        "non_trap_directed_rules": 90,
        "trap_anchored_directed_rules": 10,
        "trap_anchored_rule_fraction": 0.1,
        "distinct_organic_rule_items": 50,
        "eligible_val_context_users": 10,
        "val_context_users_with_rule": 8,
        "val_context_rule_coverage": 0.8,
        "full_catalog_organic_pair_coverage": 0.01,
    }
    _write_rule_manifest(
        root / "passing",
        snapshot_sha=snapshot_sha,
        full=True,
        schema="3.0.0",
        coverage_semantics_version="organic-target-alignment-v3",
        coverage=base_coverage,
    )
    for name, mutation in (
        ("low-rules", {"non_trap_directed_rules": 79}),
        ("low-items", {"distinct_organic_rule_items": 39}),
        ("low-context", {"val_context_rule_coverage": 0.69}),
        ("high-traps", {"trap_anchored_rule_fraction": 0.21}),
    ):
        _write_rule_manifest(
            root / name,
            snapshot_sha=snapshot_sha,
            full=True,
            schema="3.0.0",
            coverage_semantics_version="organic-target-alignment-v3",
            coverage={**base_coverage, **mutation},
        )

    assert pipeline._find_training_rule_artifact(settings, snapshot_sha).name == "passing"

    (root / "passing" / "manifest.json").unlink()
    with pytest.raises(ArtifactIntegrityError) as captured:
        pipeline._find_training_rule_artifact(settings, snapshot_sha)
    message = str(captured.value)
    assert "minimum_non_trap_directed_rules" in message
    assert "minimum_distinct_organic_rule_items" in message
    assert "minimum_val_context_rule_coverage" in message
    assert "maximum_trap_anchored_rule_fraction" in message


def test_run_all_smoke_executes_only_synthetic_mock_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path, variant=TrainingVariant.DEEP_ONLY)
    snapshot = make_snapshot(tmp_path)
    embedding = SimpleNamespace(
        artifact_dir=tmp_path / "features" / "embedding",
        manifest=SimpleNamespace(content_sha256="b" * 64),
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = SimpleNamespace(
        artifact_dir=tmp_path / "rules" / "rule",
        manifest=SimpleNamespace(content_sha256="c" * 64),
    )
    state = SimpleNamespace(
        validation_gate_passed=False,
        test_gate_passed=False,
        bundle_path=None,
        model_dump=lambda **_kwargs: {"run_id": "smoke-edge"},
    )
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        pipeline,
        "_find_single_parent_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ArtifactIntegrityError("missing")),
    )
    monkeypatch.setattr(pipeline, "_features", lambda *_args: embedding)
    monkeypatch.setattr(pipeline, "_find_training_rule_artifact", lambda *_args: tmp_path / "rules")
    monkeypatch.setattr(pipeline, "_rules", lambda *_args: rules)
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda *_args: embedding)
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: rules)
    train_kwargs: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline,
        "_train",
        lambda *_args, **kwargs: train_kwargs.update(kwargs) or (object(), state),
    )
    smoke_checkpoints = tmp_path / "runs" / "smoke-edge" / "checkpoints"
    smoke_checkpoints.mkdir(parents=True)
    (smoke_checkpoints / "best.pt").write_bytes(b"best")
    (smoke_checkpoints / "last.pt").write_bytes(b"last")
    monkeypatch.setattr(
        pipeline,
        "RunLifecycle",
        SimpleNamespace(load=lambda *_args, **_kwargs: SimpleNamespace(status=RunStatus.TRAINING)),
    )
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    pipeline.execute_command(
        SimpleNamespace(
            command="run-all",
            source="synthetic",
            embedding_source="mock",
            run_id="smoke-edge",
            device="cpu",
            config="configs/smoke/v5.toml",
        )
    )
    assert emitted == [{"run_id": "smoke-edge"}]
    assert train_kwargs["require_frozen_source"] is False
