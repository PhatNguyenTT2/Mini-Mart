from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_service.contracts import TrainingVariant
from ai_service.errors import ConfigurationError
from ai_service.training import pipeline
from tests.support.v5_factories import make_settings


def _args(command: str, **updates: object) -> Namespace:
    values: dict[str, object] = {
        "command": command,
        "source": "synthetic",
        "embedding_source": "mock",
        "device": "cpu",
        "bundle_id": None,
        "run_id": None,
        "config": None,
        "snapshot_id": None,
        "benchmark_run_id": None,
        "seed": 42,
        "store_id": 1,
        "split": "val",
        "hybrid_run_id": None,
        "deep_run_id": None,
        "hybrid_run_ids": None,
        "deep_run_ids": None,
    }
    values.update(updates)
    return Namespace(**values)


def test_pipeline_emit_and_verify_bundle_command_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match="mutually exclusive"):
        pipeline.execute_command(_args("verify-bundle", bundle_id="bundle", run_id="run"))

    with pytest.raises(ConfigurationError, match="bundle-id"):
        pipeline.execute_command(_args("verify-bundle", bundle_id=None, run_id=None))

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    monkeypatch.setattr(
        pipeline,
        "verify_bundle",
        lambda path: SimpleNamespace(
            manifest=SimpleNamespace(model_dump=lambda **_kwargs: {"path": str(path)})
        ),
    )
    with pytest.raises(ConfigurationError, match="bundle-id"):
        pipeline.execute_command(_args("verify-bundle", bundle_id=None, run_id=None, config=None))
    # No configured bundle path is a fail-closed configuration error.
    assert emitted == []


def test_pipeline_verify_bundle_run_id_and_bundle_id_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    run_dir = tmp_path / "runs" / "selected"
    run_dir.mkdir(parents=True)
    state = {
        "model_schema_version": "5.0.0",
        "run_id": "selected",
        "training_variant": "hybrid",
        "snapshot_id": "snapshot",
        "embedding_path": "embedding",
        "rule_path": "rules",
        "checkpoint_path": None,
        "paired_run_id": None,
        "validation_gate_passed": True,
        "test_gate_passed": True,
        "validation_victory_matrix_path": "val",
        "test_victory_matrix_path": "test",
        "bundle_path": str(tmp_path / "bundle") + "\\bundle",
    }
    (run_dir / "pipeline-state.json").write_text(json.dumps(state), encoding="utf-8")
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    monkeypatch.setattr(
        pipeline,
        "verify_bundle",
        lambda path: SimpleNamespace(
            manifest=SimpleNamespace(model_dump=lambda **_kwargs: {"path": str(path)})
        ),
    )
    pipeline.execute_command(_args("verify-bundle", run_id="selected"))
    assert emitted and str(tmp_path / "bundle") in emitted[-1]["path"]  # type: ignore[index]

    pipeline.execute_command(_args("verify-bundle", bundle_id="bundle"))
    assert len(emitted) == 2


def test_pipeline_release_gate_command_dispatch_and_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match="exactly 3"):
        pipeline.execute_command(_args("release-gate", hybrid_run_ids=["h"], deep_run_ids=["d"]))

    ids_h = ["h42", "h2027", "h31415"]
    ids_d = ["d42", "d2027", "d31415"]
    config_path = tmp_path / "resolved-config.json"
    config_path.write_text(json.dumps(settings.resolved_document()), encoding="utf-8")
    report = SimpleNamespace(model_dump=lambda **_kwargs: {"passed": True})
    monkeypatch.setattr(pipeline, "evaluate_three_seed", lambda **_kwargs: report)
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    monkeypatch.setattr(pipeline, "load_resolved_settings", lambda _path: settings)
    monkeypatch.setattr(
        pipeline,
        "_validate_artifact_id",
        lambda value, *, kind: value,
    )
    pipeline.execute_command(
        _args(
            "release-gate",
            hybrid_run_ids=ids_h,
            deep_run_ids=ids_d,
        )
    )
    assert emitted == [{"passed": True}]


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"source": "postgres", "embedding_source": "real"}, "smoke-only"),
        ({"run_id": None}, "requires --run-id"),
        ({"run_id": "smoke", "config": None}, "requires --config"),
    ],
)
def test_pipeline_run_all_smoke_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    updates: dict[str, object],
    message: str,
) -> None:
    settings = make_settings(tmp_path, variant=TrainingVariant.DEEP_ONLY)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match=message):
        pipeline.execute_command(_args("run-all", **updates))


def test_pipeline_run_all_smoke_config_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path, variant=TrainingVariant.HYBRID)
    settings.train.max_epochs = 1
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match="deep_only"):
        pipeline.execute_command(_args("run-all", run_id="smoke", config="smoke.toml"))

    settings = make_settings(tmp_path / "epochs", variant=TrainingVariant.DEEP_ONLY)
    settings.train.max_epochs = 2
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    with pytest.raises(ConfigurationError, match="max_epochs"):
        pipeline.execute_command(_args("run-all", run_id="smoke", config="smoke.toml"))


def test_pipeline_simple_command_dispatch_and_unsupported_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(
        pipeline,
        "_snapshot",
        lambda *_args: SimpleNamespace(
            manifest=SimpleNamespace(model_dump=lambda **_kwargs: {"kind": "snapshot"})
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_features",
        lambda *_args: SimpleNamespace(
            manifest=SimpleNamespace(model_dump=lambda **_kwargs: {"kind": "features"})
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_rules",
        lambda *_args: SimpleNamespace(
            manifest=SimpleNamespace(model_dump=lambda **_kwargs: {"kind": "rules"})
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "load_snapshot",
        lambda *_args: SimpleNamespace(manifest=SimpleNamespace(content_sha256="a" * 64)),
    )
    monkeypatch.setattr(
        pipeline,
        "DataQualityAuditor",
        lambda: SimpleNamespace(
            audit=lambda _snapshot: SimpleNamespace(model_dump=lambda **_kwargs: {"passed": True})
        ),
    )
    monkeypatch.setattr(pipeline, "run_data_probes", lambda *_args: {"probe": True})
    emitted: list[object] = []
    monkeypatch.setattr(pipeline, "_emit", emitted.append)
    for command in ("snapshot", "features", "rules", "audit-data", "probe-data"):
        if command == "probe-data":
            monkeypatch.setattr(
                pipeline, "_find_single_parent_artifact", lambda *_a, **_k: tmp_path
            )
            monkeypatch.setattr(
                pipeline, "load_embedding_artifact", lambda *_a: SimpleNamespace(vectors=[])
            )
        pipeline.execute_command(_args(command))
    assert len(emitted) == 5
    with pytest.raises(ConfigurationError, match="unsupported pipeline command"):
        pipeline.execute_command(_args("unknown"))
