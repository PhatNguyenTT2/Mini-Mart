from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
import torch
from pydantic import ValidationError

from ai_service.artifact_io import require_child_path
from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import TrainingVariant
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.training import pipeline
from ai_service.training.pipeline import PipelineState


@pytest.mark.parametrize("value", ["", "main", "bad id", "x" * 129])
def test_pipeline_artifact_id_and_device_guards(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    with pytest.raises(ConfigurationError, match="invalid immutable"):
        pipeline._validate_artifact_id(value, kind="run ID")
    assert pipeline._validate_artifact_id("valid-run.v5", kind="run ID") == "valid-run.v5"
    assert pipeline._device("cpu") == torch.device("cpu")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(ConfigurationError, match="CUDA"):
        pipeline._device("cuda")


def test_pipeline_git_commit_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pipeline.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("git unavailable")),
    )
    with pytest.raises(ConfigurationError, match="provenance command failed"):
        pipeline._git_commit()
    monkeypatch.setattr(
        pipeline.subprocess,
        "run",
        lambda *_args, **_kwargs: Namespace(stdout="0" * 40 + "\n"),
    )
    assert pipeline._git_commit() == "0" * 40
    monkeypatch.setattr(
        pipeline.subprocess,
        "run",
        lambda *_args, **_kwargs: Namespace(stdout=""),
    )
    with pytest.raises(ConfigurationError, match="valid Git commit SHA"):
        pipeline._git_commit()


def test_pipeline_requires_clean_pushed_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        ("status", "--porcelain", "--untracked-files=normal"): "",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main",
        ("rev-parse", "@{u}"): "0" * 40,
        ("rev-parse", "HEAD"): "0" * 40,
    }
    monkeypatch.setattr(
        pipeline,
        "_git_output",
        lambda arguments: responses[tuple(arguments)],
    )
    assert pipeline._require_frozen_repository() == "0" * 40

    monkeypatch.setattr(
        pipeline,
        "_git_output",
        lambda arguments: (
            "dirty.py"
            if tuple(arguments) == ("status", "--porcelain", "--untracked-files=normal")
            else responses[tuple(arguments)]
        ),
    )
    with pytest.raises(ConfigurationError, match="clean Git worktree"):
        pipeline._require_frozen_repository()

    monkeypatch.setattr(
        pipeline,
        "_git_output",
        lambda arguments: (
            (_ for _ in ()).throw(ConfigurationError("no upstream"))
            if tuple(arguments) == ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            else responses[tuple(arguments)]
        ),
    )
    with pytest.raises(ConfigurationError, match="configured upstream"):
        pipeline._require_frozen_repository()

    mismatch = dict(responses)
    mismatch[("rev-parse", "@{u}")] = "1" * 40
    monkeypatch.setattr(pipeline, "_git_output", lambda arguments: mismatch[tuple(arguments)])
    with pytest.raises(ConfigurationError, match="not synchronized"):
        pipeline._require_frozen_repository()


def test_pipeline_parent_and_state_load_errors(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    with pytest.raises(ArtifactIntegrityError, match="exactly one artifact"):
        pipeline._find_single_parent_artifact(missing_root, snapshot_sha256="a" * 64)
    root = tmp_path / "features" / "broken"
    root.mkdir(parents=True)
    (root / "manifest.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="cannot be parsed"):
        pipeline._find_single_parent_artifact(tmp_path / "features", snapshot_sha256="a" * 64)

    settings = Settings()
    settings.data.artifact_root = tmp_path
    state_path = tmp_path / "runs" / "state" / "pipeline-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="no model schema"):
        pipeline._load_state(settings, "state")
    state_path.write_text(json.dumps({"model_schema_version": "4.0.0"}), encoding="utf-8")
    with pytest.raises(ValidationError):
        pipeline._load_state(settings, "state")


def test_pipeline_state_updates_are_revalidated() -> None:
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="state-edge",
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot",
        embedding_path="embedding",
        rule_path="rules",
        checkpoint_path=None,
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
    )
    updated = pipeline._update_pipeline_state(state, paired_run_id="deep-edge")
    assert updated.paired_run_id == "deep-edge"
    with pytest.raises(ValidationError, match="validation gate"):
        pipeline._update_pipeline_state(state, validation_gate_passed=True)


@pytest.mark.parametrize(
    "updates",
    [
        {"run_id": ""},
        {"paired_run_id": ""},
        {"paired_run_id": "state-edge"},
        {"test_gate_passed": True},
        {"bundle_path": "bundle"},
    ],
)
def test_pipeline_state_dependency_guards(updates: dict[str, object]) -> None:
    base = {
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "run_id": "state-edge",
        "training_variant": TrainingVariant.HYBRID,
        "snapshot_id": "snapshot",
        "embedding_path": "embedding",
        "rule_path": "rules",
        "checkpoint_path": None,
        "paired_run_id": None,
        "validation_gate_passed": False,
        "test_gate_passed": False,
        "validation_victory_matrix_path": None,
        "test_victory_matrix_path": None,
        "bundle_path": None,
    }
    base.update(updates)
    with pytest.raises(ValidationError):
        PipelineState.model_validate(base)


def test_pipeline_config_rejects_nonpositive_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: Settings())
    args = Namespace(
        command="snapshot",
        store_id=0,
        snapshot_id=None,
        benchmark_run_id=None,
        seed=42,
        source="postgres",
        embedding_source="real",
        bundle_id=None,
        run_id=None,
    )
    with pytest.raises(ConfigurationError, match="store-id"):
        pipeline._configure(args)


def test_artifact_child_path_rejects_escape(tmp_path: Path) -> None:
    inside = require_child_path(tmp_path, tmp_path / "child.json")
    assert inside == (tmp_path / "child.json").resolve()
    with pytest.raises(ArtifactIntegrityError, match="escapes"):
        require_child_path(tmp_path, tmp_path.parent / "outside.json")
