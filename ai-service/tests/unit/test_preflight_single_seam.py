from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import torch

from ai_service.config import Settings
from ai_service.errors import ArtifactIntegrityError
from ai_service.training import pipeline, preflight


def _v5_settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.rule_feature_schema_version = "3.0.0"
    return settings


def test_r3_preflight_uses_supplied_prepared_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    snapshot = SimpleNamespace(manifest=SimpleNamespace(artifact_id="snapshot-v5"))
    prepared = SimpleNamespace(
        snapshot=snapshot,
        embedding=SimpleNamespace(vectors=object()),
        rules=object(),
        lineage=object(),
        rule_readiness=object(),
    )
    audit = SimpleNamespace(training_suitability_passed=True)
    probes = SimpleNamespace(passed=True)
    audited: list[object] = []
    probed: list[tuple[object, object, object, object]] = []

    monkeypatch.setattr(
        preflight,
        "prepare_training_inputs",
        lambda _settings: (_ for _ in ()).throw(AssertionError("prepared twice")),
    )
    monkeypatch.setattr(
        preflight.DataQualityAuditor,
        "audit",
        lambda _self, value: audited.append(value) or audit,
    )
    monkeypatch.setattr(
        preflight,
        "run_data_probes",
        lambda *values: probed.append(values) or probes,
    )
    monkeypatch.setattr(preflight, "R3PreflightReceipt", SimpleNamespace)

    receipt = preflight.run_r3_preflight(
        settings,
        device=torch.device("cpu"),
        prepared_inputs=cast(preflight.PreparedTrainingInputs, cast(object, prepared)),
    )

    assert audited == [snapshot]
    assert probed == [(settings, snapshot, prepared.embedding.vectors, prepared.rules)]
    assert receipt.lineage is prepared.lineage
    assert receipt.rule_readiness is prepared.rule_readiness


def test_v5_train_preflight_fails_before_run_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _v5_settings(tmp_path)
    prepared = SimpleNamespace(
        snapshot=object(),
        embedding=object(),
        rules=object(),
        train_loader=object(),
    )
    received: list[object] = []
    created = False

    def reject_preflight(
        _settings: Settings,
        *,
        device: torch.device,
        prepared_inputs: object | None = None,
    ) -> dict[str, object]:
        assert device.type == "cpu"
        received.append(prepared_inputs)
        raise ArtifactIntegrityError("readiness failed")

    def create_run(*_args: object, **_kwargs: object) -> object:
        nonlocal created
        created = True
        raise AssertionError("run must not be created")

    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "prepare_training_inputs", lambda _settings: prepared)
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    monkeypatch.setattr(pipeline, "_preflight_r3", reject_preflight)
    monkeypatch.setattr(
        pipeline,
        "_train",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("training started")),
    )
    monkeypatch.setattr(pipeline.RunLifecycle, "create", create_run)

    with pytest.raises(ArtifactIntegrityError, match="readiness failed"):
        pipeline.execute_command(
            Namespace(command="train", run_id="v5-preflight-failure", device="cpu")
        )

    assert received == [prepared]
    assert created is False


def test_v5_train_command_prepares_inputs_once_without_snapshot_reload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _v5_settings(tmp_path)
    prepared = SimpleNamespace(
        snapshot=object(),
        embedding=object(),
        rules=object(),
        train_loader=object(),
    )
    prepared_calls = 0
    preflight_calls: list[object] = []
    trained: list[tuple[tuple[object, ...], dict[str, object]]] = []
    emitted: list[object] = []

    def prepare(_settings: Settings) -> object:
        nonlocal prepared_calls
        prepared_calls += 1
        return prepared

    def record_preflight(
        _settings: Settings,
        *,
        device: torch.device,
        prepared_inputs: object | None = None,
    ) -> dict[str, object]:
        assert device.type == "cpu"
        preflight_calls.append(prepared_inputs)
        return {"passed": True}

    def train(*args: object, **kwargs: object) -> tuple[object, object]:
        trained.append((args, kwargs))
        return object(), SimpleNamespace(model_dump=lambda mode: {"run_id": "v5-train"})

    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    monkeypatch.setattr(pipeline, "prepare_training_inputs", prepare)
    monkeypatch.setattr(
        pipeline,
        "load_snapshot",
        lambda *_args: (_ for _ in ()).throw(AssertionError("snapshot reloaded")),
    )
    monkeypatch.setattr(pipeline, "_device", lambda _value: torch.device("cpu"))
    monkeypatch.setattr(pipeline, "_preflight_r3", record_preflight)
    monkeypatch.setattr(pipeline, "_train", train)
    monkeypatch.setattr(pipeline, "_emit", emitted.append)

    pipeline.execute_command(Namespace(command="train", run_id="v5-train", device="cpu"))

    assert prepared_calls == 1
    assert preflight_calls == [prepared]
    assert trained[0][0][1:4] == (prepared.snapshot, prepared.embedding, prepared.rules)
    assert trained[0][1]["prepared_inputs"] is prepared
    assert emitted == [{"run_id": "v5-train"}]
