import hashlib
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service import cli
from ai_service.cli import build_parser
from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    AggregateReleaseReport,
    ArtifactLineage,
    RunStatus,
    SplitName,
    TrainingVariant,
)
from ai_service.data.rule_readiness import TrainingRuleReadiness
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.training import pipeline
from ai_service.training.pipeline import PipelineState
from tests.support.v5_factories import make_metric_gate


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
        "variant": "hybrid",
        "hybrid_run_id": "hybrid-contract",
        "deep_run_id": "deep-contract",
        "split": "val",
    }
    values.update(overrides)
    return Namespace(**values)


def test_r3_preflight_reuses_read_only_training_seams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(artifact_id="snapshot-v5", content_sha256="a" * 64, num_items=4)
    )
    embedding = SimpleNamespace(
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((4, settings.model.sbert_dim), dtype=np.float32),
        manifest=SimpleNamespace(content_sha256="b" * 64),
    )
    rules = SimpleNamespace(
        artifact_dir=tmp_path / "rules" / "rules-v5",
        store=object(),
        manifest=SimpleNamespace(content_sha256="c" * 64),
        require_training_capability=lambda _settings: None,
    )
    readiness = TrainingRuleReadiness(
        in_batch_rule_present_rate=0.5,
        explicit_rule_present_rate=0.5,
        rows_with_any_rule_rate=0.5,
        examined_rows=4,
        passed=True,
        failure_reasons=(),
        strict_target_rule_rate=0.5,
    )
    lineage = ArtifactLineage(
        snapshot_sha256="a" * 64,
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
    )
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(pipeline, "_find_single_parent_artifact", lambda *_args, **_kw: tmp_path)
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda *_args: embedding)
    monkeypatch.setattr(pipeline, "_find_training_rule_artifact", lambda *_args: tmp_path)
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: rules)
    monkeypatch.setattr(pipeline, "resolve_artifact_lineage", lambda *_args, **_kw: lineage)
    monkeypatch.setattr(pipeline, "build_purchase_training_index", lambda *_args, **_kw: object())
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_args, **_kw: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_args, **_kw: object())
    monkeypatch.setattr(pipeline, "assess_training_rule_readiness", lambda *_args, **_kw: readiness)
    monkeypatch.setattr(
        pipeline.DataQualityAuditor,
        "audit",
        lambda *_args, **_kw: SimpleNamespace(model_dump=lambda **_dump_kw: {"passed": True}),
    )
    monkeypatch.setattr(pipeline, "run_data_probes", lambda *_args, **_kw: {"parity": True})

    result = pipeline._preflight_r3(settings, device=torch.device("cpu"))

    assert result["snapshot_id"] == "snapshot-v5"
    assert result["lineage"] == lineage.model_dump(mode="json")
    assert result["rule_readiness"]["passed"] is True  # type: ignore[index]
    assert result["probes"] == {"parity": True}
    failed_readiness = readiness.model_copy(
        update={"passed": False, "failure_reasons": ("strict target floor",)}
    )
    monkeypatch.setattr(
        pipeline, "assess_training_rule_readiness", lambda *_args, **_kw: failed_readiness
    )
    with pytest.raises(ArtifactIntegrityError, match="strict target floor"):
        pipeline._preflight_r3(settings, device=torch.device("cpu"))


def test_preflight_r3_cli_dispatches_read_only_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = Settings()
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(
        pipeline,
        "_preflight_r3",
        lambda _settings, *, device: {"device": str(device), "passed": True},
    )
    pipeline.execute_command(Namespace(command="preflight-r3", device="cpu"))
    assert '"passed": true' in capsys.readouterr().out


def test_cli_does_not_override_environment_snapshot_by_default() -> None:
    arguments = build_parser().parse_args(["export", "--run-id", "run-contract"])

    assert not hasattr(arguments, "snapshot_id")


def test_cli_main_dispatches_to_the_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatched: list[str] = []
    monkeypatch.setattr(cli, "execute_command", lambda args: dispatched.append(args.command))

    assert cli.main(["snapshot", "--device", "cpu"]) == 0
    assert dispatched == ["snapshot"]


def test_diagnose_r3_wrapper_publishes_a_paired_read_only_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    hybrid_settings = SimpleNamespace(
        train=SimpleNamespace(seed=42),
        data=SimpleNamespace(artifact_root=tmp_path),
    )
    deep_settings = SimpleNamespace(train=SimpleNamespace(seed=42))
    hybrid = SimpleNamespace(settings=hybrid_settings)
    deep = SimpleNamespace(settings=deep_settings)
    loaded: list[tuple[str, TrainingVariant]] = []

    def load_context(
        _settings: Settings, run_id: str, *, expected_variant: TrainingVariant
    ) -> object:
        loaded.append((run_id, expected_variant))
        return hybrid if expected_variant is TrainingVariant.HYBRID else deep

    class _Report:
        def model_dump(self, **_: object) -> dict[str, object]:
            return {"passed": False}

    artifact = SimpleNamespace(directory=tmp_path / "r3", report=_Report())
    monkeypatch.setattr(pipeline, "_load_run_context", load_context)
    monkeypatch.setattr(pipeline, "publish_r3_diagnostic", lambda **_: artifact)

    result = pipeline._diagnose_r3(
        settings,
        hybrid_run_id="hybrid",
        deep_run_id="deep",
        device=torch.device("cpu"),
    )

    assert loaded == [
        ("hybrid", TrainingVariant.HYBRID),
        ("deep", TrainingVariant.DEEP_ONLY),
    ]
    assert result == {"artifact_dir": str(tmp_path / "r3"), "report": {"passed": False}}


def test_diagnose_r3_rejects_mismatched_seed_before_publish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    hybrid = SimpleNamespace(settings=SimpleNamespace(train=SimpleNamespace(seed=42)))
    deep = SimpleNamespace(settings=SimpleNamespace(train=SimpleNamespace(seed=2027)))
    monkeypatch.setattr(
        pipeline,
        "_load_run_context",
        lambda _settings, run_id, *, expected_variant: hybrid if run_id == "hybrid" else deep,
    )
    published = False

    def publish(**_: object) -> None:
        nonlocal published
        published = True

    monkeypatch.setattr(pipeline, "publish_r3_diagnostic", publish)
    with pytest.raises(ArtifactIntegrityError, match="matching seeds"):
        pipeline._diagnose_r3(
            settings,
            hybrid_run_id="hybrid",
            deep_run_id="deep",
            device=torch.device("cpu"),
        )
    assert published is False


def test_execute_command_diagnose_r3_dispatches_validation_pair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        pipeline,
        "_diagnose_r3",
        lambda *_args, **kwargs: calls.append(kwargs) or {"ok": True},
    )
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(
        _arguments(
            "diagnose-r3",
            hybrid_run_id="hybrid-r3",
            deep_run_id="deep-r3",
            split="val",
        )
    )

    assert calls == [
        {
            "hybrid_run_id": "hybrid-r3",
            "deep_run_id": "deep-r3",
            "device": torch.device("cpu"),
        }
    ]
    assert emitted == [{"ok": True}]


def test_run_all_parser_requires_explicit_synthetic_smoke_config() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["run-all", "--run-id", "smoke-contract"])
    arguments = build_parser().parse_args(
        [
            "run-all",
            "--run-id",
            "smoke-contract",
            "--config",
            "configs/smoke/v5.toml",
            "--source",
            "synthetic",
            "--embedding-source",
            "mock",
        ]
    )
    assert arguments.source == "synthetic"
    assert arguments.embedding_source == "mock"
    assert arguments.config.name == "v5.toml"


def test_compare_deep_ablations_parser_requires_exact_candidate_set() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "compare-deep-ablations",
                "--control-run-id",
                "control",
                "--candidate-run-ids",
                "one",
                "two",
            ]
        )
    arguments = build_parser().parse_args(
        [
            "compare-deep-ablations",
            "--control-run-id",
            "control",
            "--candidate-run-ids",
            "one",
            "two",
            "three",
            "--device",
            "cpu",
        ]
    )
    assert arguments.candidate_run_ids == ["one", "two", "three"]


def test_compare_deep_ablations_wrapper_builds_typed_runs_and_dispatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path

    def loaded(run_id: str) -> pipeline.LoadedRun:
        return pipeline.LoadedRun(
            run_dir=tmp_path / "runs" / run_id,
            checkpoint_manifest=SimpleNamespace(),
            state=SimpleNamespace(run_id=run_id),
            settings=settings,
            lifecycle=SimpleNamespace(status=RunStatus.TRAINING, document={"git_commit": "a" * 40}),
            snapshot=SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64)),
            embedding=SimpleNamespace(
                manifest=SimpleNamespace(content_sha256="c" * 64),
                vectors=np.zeros((2, 2), dtype=np.float32),
            ),
            rules=SimpleNamespace(
                manifest=SimpleNamespace(content_sha256="d" * 64),
                store=object(),
            ),
            model=object(),
        )

    monkeypatch.setattr(
        pipeline,
        "_load_deep_ablation_candidate",
        lambda _settings, run_id: loaded(run_id),
    )
    captured: list[object] = []

    def compare(runs: object, **_kwargs: object) -> SimpleNamespace:
        captured.append(runs)
        return SimpleNamespace(
            directory=tmp_path / "diagnostics" / "r3" / ("e" * 64),
            report=SimpleNamespace(model_dump=lambda **_kwargs: {"selected_run_id": "candidate-1"}),
        )

    monkeypatch.setattr(pipeline, "run_deep_ablation_comparison", compare)
    result = pipeline._compare_deep_ablations(
        settings,
        control_run_id="control",
        candidate_run_ids=("candidate-1", "candidate-2", "candidate-3"),
        device=torch.device("cpu"),
    )
    assert len(captured[0]) == 4  # type: ignore[arg-type]
    assert result["diagnostic_signature"] == "e" * 64
    with pytest.raises(ConfigurationError, match="four distinct"):
        pipeline._compare_deep_ablations(
            settings,
            control_run_id="control",
            candidate_run_ids=("control", "candidate-2", "candidate-3"),
            device=torch.device("cpu"),
        )

    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(
        pipeline,
        "_compare_deep_ablations",
        lambda *_args, **_kwargs: {"diagnostic": "pass"},
    )
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    pipeline.execute_command(
        Namespace(
            command="compare-deep-ablations",
            control_run_id="control",
            candidate_run_ids=["candidate-1", "candidate-2", "candidate-3"],
            device="cpu",
        )
    )
    assert emitted == [{"diagnostic": "pass"}]
    with pytest.raises(ConfigurationError, match="exactly three"):
        pipeline.execute_command(
            Namespace(
                command="compare-deep-ablations",
                control_run_id="control",
                candidate_run_ids=["candidate-1", "candidate-2"],
                device="cpu",
            )
        )

    with pytest.raises(ArtifactIntegrityError, match="resolved configuration"):
        pipeline.execute_command(
            Namespace(
                command="release-gate",
                split="val",
                hybrid_run_ids=["h1", "h2", "h3"],
                deep_run_ids=["d1", "d2", "d3"],
            )
        )


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
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="run-contract",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot-from-state",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path="checkpoint",
        paired_run_id="deep-contract",
        validation_gate_passed=True,
        test_gate_passed=True,
        validation_victory_matrix_path="validation-matrix",
        test_victory_matrix_path="test-matrix",
        bundle_path=None,
    )
    loaded: list[object] = []
    monkeypatch.setenv("AI_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setattr(
        pipeline,
        "_load_run_context",
        lambda _settings, _run_id, **_kwargs: SimpleNamespace(
            settings=Settings(),
            snapshot=object(),
            embedding=object(),
            rules=object(),
            model=object(),
            state=state,
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_export",
        lambda *_args, **_kwargs: loaded.append(_args[-1]) or state,
    )
    monkeypatch.setattr(pipeline, "_emit", lambda _value: None)
    monkeypatch.setattr(
        pipeline,
        "load_snapshot",
        lambda *_args, **_kwargs: pytest.fail("export must not load a CLI/default snapshot"),
    )

    pipeline.execute_command(_arguments("export"))

    assert loaded == [state]


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
    with pytest.raises(TypeError):
        PipelineState("run-1", "snapshot-1", "feature", "rule")
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="run-1",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot-1",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path=None,
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
    )

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


def test_execute_run_all_is_disabled_without_a_paired_control(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match="run-all is disabled"):
        pipeline.execute_command(_arguments("run-all"))


def test_evaluate_command_requires_explicit_paired_run_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="hybrid-contract",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path=None,
        paired_run_id="deep-contract",
        validation_gate_passed=True,
        test_gate_passed=False,
        validation_victory_matrix_path="validation-matrix",
        test_victory_matrix_path=None,
        bundle_path=None,
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    pair_result = SimpleNamespace(
        split=pipeline.SplitName.VAL,
        hybrid_state=state,
        deep_state=state,
        artifact_dir=tmp_path / "evaluation",
        victory_matrix=SimpleNamespace(model_dump=lambda **_: {}),
    )
    monkeypatch.setattr(
        pipeline,
        "_evaluate_pair",
        lambda *_args, **kwargs: calls.append(kwargs) or pair_result,
    )
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("evaluate", split="val"))

    assert calls == [
        {
            "hybrid_run_id": "hybrid-contract",
            "deep_run_id": "deep-contract",
            "split": pipeline.SplitName.VAL,
            "device": torch.device("cpu"),
        }
    ]
    assert emitted[-1]["hybrid_state"]["run_id"] == "hybrid-contract"


def test_export_requires_aggregate_winner_and_publishes_profile_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _stub_settings(tmp_path)
    run_dir = tmp_path / "runs" / "winner"
    checkpoint = run_dir / "checkpoints" / "release-candidate.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"best-checkpoint")
    comparison = settings.comparison_signature_sha256()
    release = tmp_path / "releases" / comparison / "release-gate.json"
    release.parent.mkdir(parents=True)
    release_report = AggregateReleaseReport(
        schema_version="5.2.0",
        split=SplitName.TEST,
        passed=True,
        comparison_signature_sha256=comparison,
        hybrid_run_ids=("winner", "h2", "h3"),
        deep_run_ids=("deep-winner", "d2", "d3"),
        selected_run_id="winner",
        selected_seed=42,
        selected_victory_matrix_sha256="c" * 64,
        gates=tuple(
            make_metric_gate(name)
            for name in (
                "aggregate_gauc_domination",
                "aggregate_hr_domination",
                "aggregate_ndcg_domination",
                "aggregate_gauc_vs_deep",
                "aggregate_hr_vs_deep",
                "aggregate_ndcg_vs_deep",
            )
        ),
        artifact_sha256="0" * 64,
    )
    release_document = release_report.model_dump(mode="json")
    release_document["artifact_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in release_document.items() if key != "artifact_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    release.write_text(json.dumps(release_document), encoding="utf-8")
    matrix = run_dir / "evaluation" / "test" / "victory-matrix.json"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text("{}", encoding="utf-8")
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="winner",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path=str(checkpoint),
        paired_run_id="deep-winner",
        validation_gate_passed=True,
        test_gate_passed=True,
        validation_victory_matrix_path=str(matrix),
        test_victory_matrix_path=str(matrix),
        bundle_path=None,
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
        manifest=SimpleNamespace(
            num_items=4,
            num_users=2,
            content_sha256="a" * 64,
            store_id=1,
        ),
        catalog_df=catalog,
        cold_item_ids=(3,),
        train_df=empty,
        val_df=empty,
    )
    embedding = SimpleNamespace(
        vectors=np.eye(4, 768, dtype=np.float32),
        manifest=SimpleNamespace(content_sha256="b" * 64),
    )
    rules = SimpleNamespace(store=object(), manifest=SimpleNamespace(content_sha256="c" * 64))

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
            document={"comparison_signature_sha256": comparison},
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
        "load_evaluation_artifacts",
        lambda *_args, **_kwargs: SimpleNamespace(
            victory_matrix=SimpleNamespace(all_passed=True, sha256="c" * 64)
        ),
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
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "verify_bundle", lambda _path: SimpleNamespace(manifest=manifest))
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    pipeline.execute_command(_arguments("verify-bundle", bundle_id="bundle-1", run_id=None))
    assert emitted[-1]["bundle_id"] == "bundle-1"

    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    evaluated = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="run-contract",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot-state",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path=None,
        paired_run_id="deep-contract",
        validation_gate_passed=True,
        test_gate_passed=True,
        validation_victory_matrix_path="validation-matrix",
        test_victory_matrix_path="test-matrix",
        bundle_path=None,
    )
    pair_result = SimpleNamespace(
        split=SplitName.VAL,
        hybrid_state=evaluated,
        deep_state=evaluated,
        artifact_dir=tmp_path / "evaluation",
        victory_matrix=SimpleNamespace(model_dump=lambda **_: {}),
    )
    monkeypatch.setattr(pipeline, "_evaluate_pair", lambda *_args, **_kwargs: pair_result)
    pipeline.execute_command(_arguments("evaluate", split="val"))
    assert emitted[-1]["hybrid_state"]["validation_gate_passed"] is True


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
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="run-contract",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot-state",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path="best.pt",
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
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
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="run-contract",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot-state",
        embedding_path="feature",
        rule_path="rule",
        checkpoint_path=None,
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
    )
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
    monkeypatch.setattr(
        pipeline,
        "_find_training_rule_artifact",
        lambda settings, snapshot_sha256: (
            resolved.append(Path("rules")) or settings.data.artifact_root / "rules" / "artifact"
        ),
    )
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda _path: object())
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: object())
    train_kwargs: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline,
        "_train",
        lambda *_args, **kwargs: train_kwargs.update(kwargs) or (object(), state),
    )
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(_arguments("train"))

    assert [path.name for path in resolved] == ["features", "rules"]
    assert emitted[0]["run_id"] == "run-contract"
    assert train_kwargs["require_frozen_source"] is True
