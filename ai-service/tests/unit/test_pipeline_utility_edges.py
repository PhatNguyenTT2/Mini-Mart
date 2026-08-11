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


def test_pipeline_config_requires_verified_r3_selection_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.train.r3_feature_selection_mode = "selection_artifact"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    base = Namespace(
        command="train",
        store_id=1,
        snapshot_id=None,
        benchmark_run_id=None,
        seed=42,
        source="postgres",
        embedding_source="real",
        config=None,
        r3_selection_report=None,
    )
    with pytest.raises(ConfigurationError, match="requires --r3-selection-report"):
        pipeline._configure(base)

    wrong_name = tmp_path / "selection.json"
    wrong_name.write_text("{}", encoding="utf-8")
    base.r3_selection_report = str(wrong_name)
    with pytest.raises(ConfigurationError, match=r"verified report\.json"):
        pipeline._configure(base)

    missing = tmp_path / "report.json"
    base.r3_selection_report = str(missing)
    with pytest.raises(ConfigurationError, match="does not exist"):
        pipeline._configure(base)


def test_pipeline_config_materializes_verified_r3_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.train.r3_feature_selection_mode = "selection_artifact"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    selection = Namespace(use_user_id_embedding=True, use_price_features=False)
    report = Namespace(
        diagnostic_pause=False,
        selected_run_id="deep-candidate",
        selected_feature_selection=selection,
        artifact_sha256="a" * 64,
    )
    monkeypatch.setattr(
        pipeline,
        "load_deep_ablation_artifact",
        lambda _directory: Namespace(report=report),
    )
    args = Namespace(
        command="train",
        store_id=1,
        snapshot_id=None,
        benchmark_run_id=None,
        seed=42,
        source="postgres",
        embedding_source="real",
        config=None,
        r3_selection_report=str(report_path),
    )
    resolved = pipeline._configure(args)
    assert resolved.model.use_user_id_embedding is True
    assert resolved.model.use_price_features is False
    assert resolved.train.r3_selection_artifact_sha256 == "a" * 64


def test_pipeline_config_rejects_production_mock_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    settings.serving.environment = "production"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    args = Namespace(
        command="train",
        store_id=1,
        snapshot_id=None,
        benchmark_run_id=None,
        seed=42,
        source="synthetic",
        embedding_source="mock",
        config=None,
        r3_selection_report=None,
    )
    with pytest.raises(ConfigurationError, match="postgres and real"):
        pipeline._configure(args)


def test_artifact_child_path_rejects_escape(tmp_path: Path) -> None:
    inside = require_child_path(tmp_path, tmp_path / "child.json")
    assert inside == (tmp_path / "child.json").resolve()
    with pytest.raises(ArtifactIntegrityError, match="escapes"):
        require_child_path(tmp_path, tmp_path.parent / "outside.json")
