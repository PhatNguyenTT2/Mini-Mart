from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import MODEL_SCHEMA_VERSION
from ai_service.contracts import RunStatus, TrainingVariant
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.release import _load_finalist_run, evaluate_three_seed
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from tests.support.v5_factories import make_settings
from tests.unit.test_release_gate_contract import _make_fixture

LINEAGE = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}


def _checkpoint_args(tmp_path: Path, *, kind: str = "last") -> dict[str, object]:
    settings = make_settings(tmp_path)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    scaler = type(
        "Scaler", (), {"state_dict": lambda self: {}, "load_state_dict": lambda self, _: None}
    )()
    return {
        "model": model,
        "optimizer": optimizer,
        "scheduler": scheduler,
        "scaler": scaler,
        "epoch": 1,
        "metrics": {
            "val_gauc": 0.8,
            "val_ndcg_at_k": 0.4,
            "val_hr_at_k": 0.5,
            "train_loss": 0.2,
        },
        "stopping_state": {
            "highest_gauc": 0.8,
            "selected_epoch": 0,
            "selected_gauc": -float("inf"),
            "selected_ndcg": -float("inf"),
            "selected_hr": -float("inf"),
            "patience_used": 1,
        },
        "checkpoint_kind": kind,
        "lineage": LINEAGE,
        "training_signature_sha256": settings.training_signature_sha256(),
        "comparison_signature_sha256": settings.comparison_signature_sha256(),
        "training_variant": TrainingVariant.HYBRID,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "run_id": "edge-checkpoint",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("checkpoint_kind", "other", "checkpoint kind"),
        ("model_schema_version", "4.0.0", "schema"),
        ("lineage", {"snapshot": "a" * 64}, "lineage"),
        ("stopping_state", {"highest_gauc": 0.8}, "stopping state"),
        (
            "stopping_state",
            {
                "highest_gauc": 0.8,
                "selected_epoch": 3,
                "selected_gauc": 0.8,
                "selected_ndcg": 0.4,
                "selected_hr": 0.5,
                "patience_used": 0,
            },
            "selected epoch",
        ),
    ],
)
def test_checkpoint_save_rejects_strict_contract_edges(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    kwargs = _checkpoint_args(tmp_path)
    kwargs[field] = value
    with pytest.raises(ArtifactIntegrityError, match=message):
        CheckpointManager.save(tmp_path / "checkpoints" / "last.pt", **kwargs)  # type: ignore[arg-type]


def _rewrite_payload(path: Path, mutate: object) -> None:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    mutate(payload)
    torch.save(payload, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_checkpoint_loader_rejects_payload_metadata_and_resume_edges(tmp_path: Path) -> None:
    kwargs = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last.pt"
    CheckpointManager.save(path, **kwargs)  # type: ignore[arg-type]
    settings = make_settings(tmp_path)
    model = HybridTwoTowerModel(settings)
    with pytest.raises(ArtifactIntegrityError, match="run ID state"):
        _rewrite_payload(path, lambda payload: payload.update(run_id="wrong"))
        CheckpointManager.load(path, model=model)

    kwargs = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last-2.pt"
    CheckpointManager.save(path, **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ArtifactIntegrityError, match="stopping state"):
        _rewrite_payload(path, lambda payload: payload.pop("stopping_state"))
        CheckpointManager.load(path, model=HybridTwoTowerModel(settings))

    kwargs = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last-3.pt"
    CheckpointManager.save(path, **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ArtifactIntegrityError, match="resume requires"):
        _rewrite_payload(path, lambda payload: payload.update(scaler=None))
        CheckpointManager.load(
            path,
            model=HybridTwoTowerModel(settings),
            optimizer=AdamW(HybridTwoTowerModel(settings).parameters()),
            scheduler=ReduceLROnPlateau(AdamW(HybridTwoTowerModel(settings).parameters())),
            scaler=type("Scaler", (), {"load_state_dict": lambda self, _: None})(),
            restore_rng=True,
        )


def test_checkpoint_publication_cleans_temporary_files_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "checkpoints" / "last.pt"
    original_replace = os.replace

    def fail_first_replace(
        source: str | bytes | os.PathLike[str], destination: str | bytes | os.PathLike[str]
    ) -> None:
        monkeypatch.setattr(os, "replace", original_replace)
        raise OSError("injected checkpoint replace failure")

    monkeypatch.setattr(os, "replace", fail_first_replace)
    with pytest.raises(OSError, match="injected checkpoint replace failure"):
        CheckpointManager.save(path, **_checkpoint_args(tmp_path))  # type: ignore[arg-type]
    assert not path.exists()
    assert not path.with_suffix(path.suffix + ".manifest.json").exists()
    assert list(path.parent.glob(".*.tmp")) == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("metrics", "metrics state"),
        ("selected_epoch", "selected epoch"),
        ("model", "strict-loaded"),
        ("optimizer", "optimizer payload"),
        ("scheduler", "scheduler payload"),
        ("scaler", "scaler payload"),
        ("rng", "RNG state"),
    ],
)
def test_checkpoint_loader_rejects_payload_sections(
    tmp_path: Path, mutation: str, message: str
) -> None:
    settings = make_settings(tmp_path)
    path = tmp_path / "checkpoints" / f"{mutation}.pt"
    CheckpointManager.save(path, **_checkpoint_args(tmp_path))  # type: ignore[arg-type]
    if mutation == "metrics":

        def mutate(payload: dict[str, object]) -> None:
            payload["metrics"].pop("train_loss")  # type: ignore[union-attr]
    elif mutation == "selected_epoch":

        def mutate(payload: dict[str, object]) -> None:
            payload["stopping_state"].update(selected_epoch="bad")  # type: ignore[union-attr]
    elif mutation == "model":

        def mutate(payload: dict[str, object]) -> None:
            payload.update(model={})
    elif mutation == "optimizer":

        def mutate(payload: dict[str, object]) -> None:
            payload.update(optimizer=None)
    elif mutation == "scheduler":

        def mutate(payload: dict[str, object]) -> None:
            payload.update(scheduler=None)
    elif mutation == "scaler":

        def mutate(payload: dict[str, object]) -> None:
            payload.update(scaler=None)
    else:

        def mutate(payload: dict[str, object]) -> None:
            payload.update(rng={})

    _rewrite_payload(path, mutate)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    scaler = type("Scaler", (), {"load_state_dict": lambda self, _: None})()
    with pytest.raises(ArtifactIntegrityError, match=message):
        CheckpointManager.load(
            path,
            model=model,
            optimizer=optimizer if mutation in {"optimizer", "rng"} else None,
            scheduler=scheduler if mutation in {"scheduler", "rng"} else None,
            scaler=scaler if mutation in {"scaler", "rng"} else None,
            restore_rng=mutation == "rng",
        )


def test_checkpoint_loader_rejects_missing_payload_and_bad_rng(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    path = tmp_path / "checkpoints" / "missing.pt"
    CheckpointManager.save(path, **_checkpoint_args(tmp_path))  # type: ignore[arg-type]
    path.unlink()
    with pytest.raises(ArtifactIntegrityError, match="payload missing"):
        CheckpointManager.load(path, model=HybridTwoTowerModel(settings))


@pytest.mark.parametrize("mutation", ["status", "variant", "state", "checkpoint", "lineage"])
def test_release_finalist_loader_rejects_invalid_run_contracts(
    tmp_path: Path, mutation: str
) -> None:
    hybrids, _deeps = _make_fixture(tmp_path)
    run_dir = hybrids[0]
    if mutation == "status":
        lifecycle = __import__(
            "ai_service.training.run", fromlist=["RunLifecycle"]
        ).RunLifecycle.load(run_dir)
        lifecycle.transition(RunStatus.FAILED, reason="fixture failed")
    elif mutation == "variant":
        document = json.loads((run_dir / "resolved-config.json").read_text(encoding="utf-8"))
        document["train"]["training_variant"] = TrainingVariant.DEEP_ONLY.value
        (run_dir / "resolved-config.json").write_text(json.dumps(document), encoding="utf-8")
    elif mutation == "state":
        document = json.loads((run_dir / "pipeline-state.json").read_text(encoding="utf-8"))
        document["run_id"] = "different"
        (run_dir / "pipeline-state.json").write_text(json.dumps(document), encoding="utf-8")
    elif mutation == "checkpoint":
        document = json.loads((run_dir / "pipeline-state.json").read_text(encoding="utf-8"))
        document["checkpoint_path"] = str(run_dir / "checkpoints" / "last.pt")
        (run_dir / "pipeline-state.json").write_text(json.dumps(document), encoding="utf-8")
    else:
        manifest_path = run_dir / "run-manifest.json"
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        document["lineage"]["rules"] = "d" * 64
        manifest_path.write_text(json.dumps(document), encoding="utf-8")
    expected = "not evaluable|variant|identity|checkpoint|lineage"
    with pytest.raises((ArtifactIntegrityError, DataIntegrityError), match=expected):
        _load_finalist_run(run_dir, TrainingVariant.HYBRID)


def test_release_gate_rejects_test_without_validation_and_immutable_overwrite(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    # The fixture has both artifacts, but removing validation forces the test precondition.
    validation_path = (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    )
    validation_path.unlink(missing_ok=True)
    with pytest.raises(ArtifactIntegrityError, match="requires validation"):
        evaluate_three_seed(
            split=__import__("ai_service.contracts", fromlist=["SplitName"]).SplitName.TEST,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )
