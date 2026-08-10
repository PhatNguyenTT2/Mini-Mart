from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service import cli
from ai_service.cli import build_parser
from ai_service.config import Settings
from ai_service.contracts import RunStatus
from ai_service.errors import ConfigurationError
from ai_service.evaluation.cold_start import ColdStartReport
from ai_service.evaluation.semantic_traps import SemanticTrapReport
from ai_service.training import pipeline
from ai_service.training.pipeline import PipelineState


def _arguments(command: str, **overrides: object) -> Namespace:
    values: dict[str, object] = {
        "command": command,
        "store_id": 1,
        "snapshot_id": None,
        "run_id": "run-contract",
        "bundle_id": None,
        "source": "postgres",
        "embedding_source": "real",
        "seed": 42,
        "benchmark_run_id": None,
        "device": "cpu",
    }
    values.update(overrides)
    return Namespace(**values)


def test_cli_does_not_override_environment_snapshot_by_default() -> None:
    arguments = build_parser().parse_args(["export", "--run-id", "run-contract"])

    assert arguments.snapshot_id is None


def test_cli_main_dispatches_to_the_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatched: list[str] = []
    monkeypatch.setattr(cli, "execute_command", lambda args: dispatched.append(args.command))

    assert cli.main(["snapshot", "--device", "cpu"]) == 0
    assert dispatched == ["snapshot"]


def test_audit_data_command_reports_snapshot_training_suitability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = object()
    report = SimpleNamespace(model_dump=lambda **_kwargs: {"training_suitability_passed": False})
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        pipeline,
        "DataQualityAuditor",
        lambda: SimpleNamespace(audit=lambda _s: report),
    )
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("audit-data"))

    assert emitted == [{"training_suitability_passed": False}]


def test_probe_data_command_resolves_embedding_for_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = SimpleNamespace(manifest=SimpleNamespace(content_sha256="a" * 64))
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        pipeline,
        "_find_single_parent_artifact",
        lambda *_args, **_kwargs: tmp_path / "feature",
    )
    monkeypatch.setattr(
        pipeline,
        "load_embedding_artifact",
        lambda _path: SimpleNamespace(vectors=np.eye(4, dtype=np.float32)),
    )
    monkeypatch.setattr(
        pipeline,
        "run_data_probes",
        lambda *_args: {"label_permutation_sanity": {"passed": True}},
    )
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("probe-data"))

    assert emitted == [{"label_permutation_sanity": {"passed": True}}]


def test_export_loads_snapshot_only_from_run_lineage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = PipelineState(
        run_id="run-contract",
        snapshot_id="snapshot-from-state",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path="checkpoint",
        evaluation_passed=True,
    )
    loaded: list[str] = []
    monkeypatch.setenv("AI_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setattr(pipeline, "_load_state", lambda _settings, _run_id: state)
    monkeypatch.setattr(
        pipeline,
        "_load_lineage",
        lambda _settings, loaded_state: (
            loaded.append(loaded_state.snapshot_id) or (object(), object(), object(), object())
        ),
    )
    monkeypatch.setattr(pipeline, "_export", lambda *_args, **_kwargs: state)
    monkeypatch.setattr(pipeline, "_emit", lambda _value: None)
    monkeypatch.setattr(
        pipeline,
        "load_snapshot",
        lambda *_args, **_kwargs: pytest.fail("export must not load a CLI/default snapshot"),
    )

    pipeline.execute_command(_arguments("export"))

    assert loaded == ["snapshot-from-state"]


@pytest.mark.parametrize(
    ("source", "embedding_source"),
    [("synthetic", "real"), ("postgres", "mock")],
)
def test_production_rejects_non_production_data_adapters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source: str,
    embedding_source: str,
) -> None:
    monkeypatch.setenv("AI_ENV", "production")
    monkeypatch.setenv("AI_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("AI_STORE_ID", "1")
    monkeypatch.setenv("CHATBOT_DATABASE_URL", "postgresql://localhost/chat")
    monkeypatch.setenv("CATALOG_DATABASE_URL", "postgresql://localhost/catalog")
    monkeypatch.setenv("ORDER_DATABASE_URL", "postgresql://localhost/order")
    monkeypatch.setenv("SUPABASE_DB_CA_PATH", str(tmp_path / "ca.crt"))

    with pytest.raises(ConfigurationError, match="production requires postgres and real"):
        pipeline.execute_command(
            _arguments("run-all", source=source, embedding_source=embedding_source)
        )


def test_pipeline_state_is_atomic_and_requires_a_run_id(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    state = PipelineState("run-1", "snapshot-1", "feature", "rule")

    pipeline._write_state(settings, state)

    assert pipeline._load_state(settings, "run-1") == state
    assert not pipeline._state_path(settings, "run-1").with_suffix(".json.tmp").exists()
    with pytest.raises(ConfigurationError, match="--run-id"):
        pipeline._load_state(settings, None)
    with pytest.raises(ConfigurationError, match="invalid immutable"):
        pipeline._validate_artifact_id("main", kind="run ID")


def test_parent_artifact_resolution_is_unambiguous(tmp_path: Path) -> None:
    root = tmp_path / "features"
    artifact = root / "feature-1"
    artifact.mkdir(parents=True)
    (artifact / "manifest.json").write_text('{"snapshot_sha256":"snapshot-sha"}', encoding="utf-8")

    assert pipeline._find_single_parent_artifact(root, snapshot_sha256="snapshot-sha") == artifact
    with pytest.raises(Exception, match="expected exactly one artifact"):
        pipeline._find_single_parent_artifact(root, snapshot_sha256="missing")


def test_comparison_gates_bootstrap_users_after_averaging_random_seeds() -> None:
    settings = Settings()
    settings.eval.bootstrap_samples = 100
    strong = SimpleNamespace(
        per_user_gauc=np.asarray([0.7, 0.7, 0.7]),
        per_user_hr=np.asarray([1.0, 1.0, 1.0]),
        per_user_ndcg=np.asarray([0.5, 0.5, 0.5]),
        report=SimpleNamespace(ndcg_at_k=0.5),
    )
    weak = SimpleNamespace(
        per_user_gauc=np.asarray([0.5, 0.5, 0.5]),
        per_user_hr=np.asarray([0.0, 0.0, 0.0]),
        per_user_ndcg=np.asarray([0.1, 0.1, 0.1]),
        report=SimpleNamespace(ndcg_at_k=0.1),
    )
    random_runs = tuple(
        SimpleNamespace(per_user_gauc=np.asarray([0.49, 0.50, 0.51])) for _ in range(10)
    )
    comparison = SimpleNamespace(
        results={
            "Proposed Hybrid (Ours)": strong,
            "Deep-Only Two-Tower": weak,
            "Rule-based Apriori": weak,
            "Item-Item CF": weak,
        },
        random_seed_results=random_runs,
    )

    gates = pipeline._comparison_gates(comparison, settings)

    assert gates["passed"] is True
    assert gates["random"]["mean_gauc"] == pytest.approx(0.5)


def _stub_settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.snapshot_id = "snapshot-state"
    return settings


def _manifest(**values: object) -> SimpleNamespace:
    defaults = {"artifact_id": "artifact", "content_sha256": "a" * 64, "num_items": 4}
    defaults.update(values)
    return SimpleNamespace(model_dump=lambda **_kwargs: defaults, **defaults)


@pytest.mark.parametrize("command", ["snapshot", "features", "rules"])
def test_execute_simple_artifact_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = SimpleNamespace(manifest=_manifest(artifact_id="snapshot-state"))
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "_features", lambda *_args: SimpleNamespace(manifest=_manifest()))
    monkeypatch.setattr(pipeline, "_rules", lambda *_args: SimpleNamespace(manifest=_manifest()))
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments(command))

    assert emitted


def test_execute_run_all_uses_one_lineage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = SimpleNamespace(manifest=_manifest(artifact_id="snapshot-state"))
    embedding = object()
    rules = object()
    model = object()
    initial = PipelineState("run-contract", "snapshot-state", "feature", "rule")
    evaluated = PipelineState(
        "run-contract", "snapshot-state", "feature", "rule", evaluation_passed=True
    )
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "_features", lambda *_args: embedding)
    monkeypatch.setattr(pipeline, "_rules", lambda *_args: rules)
    monkeypatch.setattr(pipeline, "_train", lambda *_args, **_kwargs: (model, initial))
    monkeypatch.setattr(pipeline, "_evaluate", lambda *_args, **_kwargs: evaluated)
    monkeypatch.setattr(
        pipeline,
        "_export",
        lambda *_args, **_kwargs: pytest.fail("run-all must wait for three-seed release gate"),
    )
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("run-all"))

    assert emitted[0]["evaluation_passed"] is True
    assert emitted[0]["bundle_path"] is None


def _ranked_result(value: float = 0.5) -> SimpleNamespace:
    report = SimpleNamespace(
        ndcg_at_k=value,
        model_dump=lambda **_kwargs: {"ndcg_at_k": value},
    )
    metrics = np.full(3, value, dtype=np.float64)
    return SimpleNamespace(
        report=report,
        user_ids=np.asarray([1, 2, 3], dtype=np.int64),
        per_user_hr=metrics,
        per_user_ndcg=metrics,
        per_user_gauc=metrics,
    )


def test_evaluate_publishes_measured_per_user_artifact_and_evaluated_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    settings.data.num_cold_items = 1
    run_dir = tmp_path / "run-evaluate"
    checkpoint = run_dir / "checkpoints" / "release-candidate.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    checkpoint.with_suffix(".pt.manifest.json").write_text(
        '{"content_sha256":"' + "d" * 64 + '"}', encoding="utf-8"
    )
    state = PipelineState(
        "run-evaluate",
        "snapshot",
        "feature",
        "rule",
        checkpoint_path=str(checkpoint),
    )
    snapshot = SimpleNamespace(manifest=SimpleNamespace(content_sha256="a" * 64))
    embedding = SimpleNamespace(
        vectors=np.eye(4, dtype=np.float32),
        manifest=SimpleNamespace(content_sha256="b" * 64),
    )
    rules = SimpleNamespace(store=object(), manifest=SimpleNamespace(content_sha256="c" * 64))
    result = _ranked_result()
    comparison = SimpleNamespace(
        results={
            "Proposed Hybrid (Ours)": result,
            "SBERT User Centroid": result,
            "Deep-Only Two-Tower": result,
            "Rule-based Apriori": result,
            "Item-Item CF": result,
        },
        baselines={"hybrid": result.report},
    )
    cold = ColdStartReport(1, 1, 1.0, 1.0, 1.0, 1.0, 3)
    transitions: list[tuple[RunStatus, str | None]] = []
    monkeypatch.setattr(pipeline, "run_seven_way_baselines", lambda *_a, **_kw: comparison)
    monkeypatch.setattr(pipeline, "_comparison_gates", lambda *_a: {"passed": True})
    monkeypatch.setattr(pipeline, "evaluate_cold_start", lambda *_a: cold)
    monkeypatch.setattr(
        pipeline,
        "evaluate_semantic_traps",
        lambda *_a, **_kw: SemanticTrapReport(all_passed=True, passed=10, total=10, results=()),
    )
    monkeypatch.setattr(pipeline, "_write_state", lambda *_a: None)
    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda *_a: SimpleNamespace(
            transition=lambda status, reason=None: transitions.append((status, reason))
        ),
    )

    evaluated = pipeline._evaluate(
        settings,
        snapshot,
        embedding,
        rules,
        object(),
        state,
        device=torch.device("cpu"),
    )

    report = run_dir / "evaluation" / "report.json"
    assert evaluated.evaluation_passed is True
    assert report.is_file()
    assert (run_dir / "evaluation" / "per-user-metrics.npz").is_file()
    assert transitions == [(RunStatus.EVALUATED, None)]


def test_export_requires_aggregate_winner_and_publishes_profile_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    run_dir = tmp_path / "runs" / "winner"
    checkpoint = run_dir / "checkpoints" / "release-candidate.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"best-checkpoint")
    experiment = "e" * 64
    release = tmp_path / "releases" / experiment / "release-gate.json"
    release.parent.mkdir(parents=True)
    release.write_text('{"passed":true,"selected_run_id":"winner"}', encoding="utf-8")
    state = PipelineState(
        "winner",
        "snapshot",
        "feature",
        "rule",
        checkpoint_path=str(checkpoint),
        evaluation_passed=True,
    )
    catalog = pd.DataFrame(
        {
            "internal_product_id": range(4),
            "internal_leaf_category_id": [1, 1, 2, 2],
            "price_bucket_id": [1, 2, 1, 2],
        }
    )
    empty = pd.DataFrame(columns=["event_type", "internal_user_id", "internal_product_id"])
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(num_items=4, num_users=2),
        catalog_df=catalog,
        cold_item_ids=(3,),
        train_df=empty,
        val_df=empty,
    )
    embedding = SimpleNamespace(vectors=np.eye(4, 768, dtype=np.float32))
    rules = SimpleNamespace(store=object())

    class StubModel:
        def cpu(self) -> object:
            return self

        def eval(self) -> object:
            return self

        def encode_items(self, *_args: object, **_kwargs: object) -> torch.Tensor:
            return torch.eye(4, settings.model.item_emb_dim)

    published: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda *_a: SimpleNamespace(
            status=RunStatus.SEALED,
            document={"experiment_signature_sha256": experiment},
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "export_onnx_models",
        lambda *_a: SimpleNamespace(ranker=run_dir / "export" / "ranker.onnx"),
    )
    monkeypatch.setattr(
        pipeline,
        "verify_onnx_parity",
        lambda *_a: SimpleNamespace(kernel_latency_ms={"p95": 0.2}),
    )
    monkeypatch.setattr(
        pipeline,
        "build_user_profile_vectors",
        lambda *_a, **_kw: torch.zeros(3, settings.model.item_emb_dim),
    )
    monkeypatch.setattr(
        pipeline,
        "BundlePublisher",
        lambda *_a: SimpleNamespace(
            publish=lambda **kwargs: (
                published.update(kwargs) or SimpleNamespace(path=tmp_path / "bundles" / "winner")
            )
        ),
    )
    monkeypatch.setattr(pipeline, "_write_state", lambda *_a: None)

    exported = pipeline._export(
        settings,
        snapshot,
        embedding,
        rules,
        StubModel(),
        state,
    )

    assert exported.bundle_path == str(tmp_path / "bundles" / "winner")
    assert np.asarray(published["item_vectors"]).shape == (4, 64)
    assert np.asarray(published["user_profile_vectors"]).shape == (3, 64)


def test_execute_verify_bundle_and_evaluate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    manifest = _manifest(bundle_id="bundle-1")
    state = PipelineState("run-contract", "snapshot-state", "feature", "rule")
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "verify_bundle", lambda _path: SimpleNamespace(manifest=manifest))
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    pipeline.execute_command(_arguments("verify-bundle", bundle_id="bundle-1"))
    assert emitted[-1]["bundle_id"] == "bundle-1"

    monkeypatch.setattr(pipeline, "_load_state", lambda *_args: state)
    monkeypatch.setattr(
        pipeline, "_load_lineage", lambda *_args: (object(), object(), object(), object())
    )
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    evaluated = PipelineState(
        "run-contract", "snapshot-state", "feature", "rule", evaluation_passed=True
    )
    monkeypatch.setattr(pipeline, "_evaluate", lambda *_args, **_kwargs: evaluated)
    pipeline.execute_command(_arguments("evaluate"))
    assert emitted[-1]["evaluation_passed"] is True


def test_snapshot_adapter_selection_and_cuda_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    loaded: list[str] = []

    class _Source:
        def __init__(self, _settings: Settings, name: str) -> None:
            self.name = name

        def load(self, _store_id: int, _run_id: str | None) -> str:
            loaded.append(self.name)
            return self.name

    monkeypatch.setattr(pipeline, "PostgresDatasetSource", lambda value: _Source(value, "postgres"))
    monkeypatch.setattr(
        pipeline, "SyntheticDatasetSource", lambda value: _Source(value, "synthetic")
    )
    monkeypatch.setattr(
        pipeline,
        "SnapshotBuilder",
        lambda _settings: SimpleNamespace(build=lambda raw, snapshot_id: (raw, snapshot_id)),
    )

    assert pipeline._snapshot(settings, pipeline.DataSourceKind.POSTGRES)[0] == "postgres"
    assert pipeline._snapshot(settings, pipeline.DataSourceKind.SYNTHETIC)[0] == "synthetic"
    assert loaded == ["postgres", "synthetic"]
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(ConfigurationError, match="CUDA was requested"):
        pipeline._device("cuda")


def test_feature_and_rule_builders_receive_the_same_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = object()
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        pipeline,
        "SBERTArtifactBuilder",
        lambda _settings: SimpleNamespace(
            build=lambda value, **_kwargs: calls.append(("features", value)) or "embedding"
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "AprioriRuleMiner",
        lambda _settings: SimpleNamespace(
            mine=lambda value: calls.append(("rules", value)) or "rule-artifact"
        ),
    )

    assert pipeline._features(settings, snapshot, pipeline.EmbeddingSource.MOCK) == "embedding"
    assert pipeline._rules(settings, snapshot) == "rule-artifact"
    assert calls == [("features", snapshot), ("rules", snapshot)]


def test_load_lineage_strictly_reloads_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(
            num_items=4,
            content_sha256="a" * 64,
        )
    )
    embedding = SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64))
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256="c" * 64))
    model = object()
    calls: list[dict[str, str]] = []
    state = PipelineState(
        "run-contract", "snapshot-state", "feature", "rule", checkpoint_path="best.pt"
    )
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda *_args: embedding)
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: rules)
    monkeypatch.setattr(pipeline, "HybridTwoTowerModel", lambda _settings: model)
    monkeypatch.setattr(
        pipeline.CheckpointManager,
        "load",
        lambda _path, **kwargs: calls.append(kwargs["expected_lineage"]),
    )

    loaded = pipeline._load_lineage(settings, state)

    assert loaded == (snapshot, embedding, rules, model)
    assert calls == [{"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}]


def test_execute_train_resolves_parent_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    snapshot = SimpleNamespace(manifest=_manifest(artifact_id="snapshot-state", num_items=4))
    state = PipelineState("run-contract", "snapshot-state", "feature", "rule")
    resolved: list[Path] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    monkeypatch.setattr(
        pipeline,
        "_find_single_parent_artifact",
        lambda root, **_kwargs: resolved.append(root) or root / "artifact",
    )
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda _path: object())
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: object())
    monkeypatch.setattr(pipeline, "_train", lambda *_args, **_kwargs: (object(), state))
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("train"))

    assert [path.name for path in resolved] == ["features", "rules"]
    assert emitted[0]["run_id"] == "run-contract"
