from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import MODEL_SCHEMA_VERSION
from ai_service.contracts import TrainingVariant
from ai_service.errors import ArtifactIntegrityError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from tests.support.corruption import fail_nth_replace, rewrite_torch_payload
from tests.support.v5_factories import make_settings


def _refresh_payload_manifest(path: Path) -> None:
    manifest_path = path.with_suffix(".pt.manifest.json")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(document), encoding="utf-8")


def _checkpoint_args(tmp_path: Path, *, kind: str = "last") -> dict[str, object]:
    settings = make_settings(tmp_path)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters(), lr=1e-3)
    return {
        "model": model,
        "optimizer": optimizer,
        "scheduler": ReduceLROnPlateau(optimizer),
        "scaler": SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _: None),
        "epoch": 1,
        "metrics": {
            "val_gauc": 0.8,
            "val_ndcg_at_k": 0.2,
            "val_hr_at_k": 0.3,
            "train_loss": 0.5,
        },
        "stopping_state": {
            "highest_gauc": 0.8,
            "selected_epoch": 1,
            "selected_gauc": 0.8,
            "selected_ndcg": 0.2,
            "selected_hr": 0.3,
            "patience_used": 0,
        },
        "checkpoint_kind": kind,
        "lineage": {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        "training_signature_sha256": "d" * 64,
        "comparison_signature_sha256": "e" * 64,
        "training_variant": TrainingVariant.HYBRID,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "run_id": "checkpoint-corruption",
    }


def test_checkpoint_manifest_parse_error_is_integrity_error(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints" / "last.pt"
    args = _checkpoint_args(tmp_path)
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    path.with_suffix(".pt.manifest.json").write_text("{", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="manifest cannot be read"):
        CheckpointManager.load(path, model=args["model"])  # type: ignore[arg-type]


def test_checkpoint_save_rejects_nonfinite_stopping_state(tmp_path: Path) -> None:
    args = _checkpoint_args(tmp_path)
    args["stopping_state"] = dict(args["stopping_state"], selected_gauc=float("nan"))

    with pytest.raises(ArtifactIntegrityError, match="stopping state"):
        CheckpointManager.save(tmp_path / "checkpoints" / "last.pt", **args)  # type: ignore[arg-type]


def test_checkpoint_replace_failure_never_loads_mismatched_pair_and_retry_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "checkpoints" / "last.pt"
    args = _checkpoint_args(tmp_path)
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    old_manifest = path.with_suffix(".pt.manifest.json").read_text(encoding="utf-8")
    next_args = dict(args)
    next_args["metrics"] = dict(args["metrics"], train_loss=0.51)  # type: ignore[arg-type]

    fail_nth_replace(monkeypatch, 2)
    with pytest.raises(OSError, match="replace failure #2"):
        CheckpointManager.save(path, **next_args)  # type: ignore[arg-type]
    monkeypatch.undo()

    with pytest.raises(ArtifactIntegrityError, match="checksum mismatch"):
        CheckpointManager.load(path, model=args["model"])  # type: ignore[arg-type]
    assert path.with_suffix(".pt.manifest.json").read_text(encoding="utf-8") == old_manifest

    CheckpointManager.save(path, **next_args)  # type: ignore[arg-type]
    assert CheckpointManager.load(path, model=args["model"])["run_id"] == "checkpoint-corruption"
    assert not list(path.parent.glob(".*tmp*"))


def test_checkpoint_payload_corruption_is_rejected_before_deserialize(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints" / "last.pt"
    args = _checkpoint_args(tmp_path)
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    rewrite_torch_payload(path, lambda payload: dict(payload, model={}))

    with pytest.raises(ArtifactIntegrityError, match="checksum mismatch"):
        CheckpointManager.load(path, model=args["model"])  # type: ignore[arg-type]


def test_checkpoint_resume_preflight_requires_exact_run_and_full_state(tmp_path: Path) -> None:
    path = tmp_path / "checkpoints" / "last.pt"
    args = _checkpoint_args(tmp_path)
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]

    with pytest.raises(ArtifactIntegrityError, match="run ID mismatch"):
        CheckpointManager.load(
            path,
            model=args["model"],  # type: ignore[arg-type]
            expected_run_id="another-run",
            require_resume_state=True,
        )

    rewrite_torch_payload(path, lambda payload: dict(payload, optimizer=None))
    _refresh_payload_manifest(path)
    with pytest.raises(ArtifactIntegrityError, match="resume requires optimizer"):
        CheckpointManager.load(
            path,
            model=args["model"],  # type: ignore[arg-type]
            expected_run_id="checkpoint-corruption",
            require_resume_state=True,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("highest_gauc", True, "invalid metrics"),
        ("patience_used", -1, "patience counter"),
    ],
)
def test_checkpoint_save_rejects_invalid_stopping_counters(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    args = _checkpoint_args(tmp_path)
    args["stopping_state"] = dict(args["stopping_state"], **{field: value})  # type: ignore[arg-type]

    with pytest.raises(ArtifactIntegrityError, match=message):
        CheckpointManager.save(tmp_path / "checkpoints" / "last.pt", **args)  # type: ignore[arg-type]


def test_checkpoint_best_requires_selected_epoch_and_epoch_order(tmp_path: Path) -> None:
    args = _checkpoint_args(tmp_path, kind="best")
    args["stopping_state"] = dict(args["stopping_state"], selected_epoch=0)  # type: ignore[arg-type]
    with pytest.raises(ArtifactIntegrityError, match="selected epoch"):
        CheckpointManager.save(tmp_path / "checkpoints" / "best.pt", **args)  # type: ignore[arg-type]

    args = _checkpoint_args(tmp_path, kind="last")
    args["stopping_state"] = dict(args["stopping_state"], selected_epoch=2)  # type: ignore[arg-type]
    with pytest.raises(ArtifactIntegrityError, match="outside checkpoint"):
        CheckpointManager.save(tmp_path / "checkpoints" / "last.pt", **args)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "4.0.0", "artifact schema state"),
        ("training_signature_sha256", "f" * 64, "training signature state"),
        ("comparison_signature_sha256", "f" * 64, "comparison signature state"),
        ("training_variant", "deep_only", "training variant state"),
        ("model_schema_version", "4.0.0", "model schema state"),
        ("run_id", "other", "run ID state"),
        ("checkpoint_kind", "best", "checkpoint kind state"),
        ("epoch", 99, "epoch state"),
        ("lineage", {"snapshot": "f" * 64}, "lineage state"),
    ],
)
def test_checkpoint_loader_rejects_payload_manifest_mismatches(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    args = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last.pt"
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    rewrite_torch_payload(path, lambda payload: dict(payload, **{field: value}))
    _refresh_payload_manifest(path)

    with pytest.raises(ArtifactIntegrityError, match=message):
        CheckpointManager.load(path, model=args["model"])  # type: ignore[arg-type]


def test_checkpoint_loader_wraps_section_restore_errors(tmp_path: Path) -> None:
    args = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last.pt"
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    for section, message in (
        ("optimizer", "optimizer payload"),
        ("scheduler", "scheduler payload"),
        ("scaler", "scaler payload"),
    ):
        rewrite_torch_payload(
            path, lambda payload, _section=section: dict(payload, **{_section: "bad"})
        )
        _refresh_payload_manifest(path)
        settings = make_settings(tmp_path)
        model = HybridTwoTowerModel(settings)
        optimizer = AdamW(model.parameters())
        scheduler = ReduceLROnPlateau(optimizer)
        scaler = SimpleNamespace(
            load_state_dict=lambda _state: (_ for _ in ()).throw(TypeError("bad scaler"))
        )
        kwargs: dict[str, object] = {"model": model}
        if section == "optimizer":
            kwargs["optimizer"] = optimizer
        elif section == "scheduler":
            kwargs["scheduler"] = scheduler
        else:
            kwargs["scaler"] = scaler
        with pytest.raises(ArtifactIntegrityError, match=message):
            CheckpointManager.load(path, **kwargs)  # type: ignore[arg-type]
        # Restore a valid artifact for the next section mutation.
        CheckpointManager.save(path, **args)  # type: ignore[arg-type]


def test_checkpoint_loader_wraps_deserialize_and_rng_errors(tmp_path: Path) -> None:
    args = _checkpoint_args(tmp_path)
    path = tmp_path / "checkpoints" / "last.pt"
    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    path.write_bytes(b"not-a-torch-payload")
    _refresh_payload_manifest(path)
    with pytest.raises(ArtifactIntegrityError, match="cannot be deserialized"):
        CheckpointManager.load(path, model=args["model"])  # type: ignore[arg-type]

    CheckpointManager.save(path, **args)  # type: ignore[arg-type]
    rewrite_torch_payload(
        path,
        lambda payload: dict(
            payload, rng={"python": "bad", "numpy": None, "torch": None, "cuda": []}
        ),
    )
    _refresh_payload_manifest(path)
    with pytest.raises(ArtifactIntegrityError, match="RNG state is invalid"):
        CheckpointManager.load(
            path,
            model=args["model"],
            optimizer=args["optimizer"],  # type: ignore[arg-type]
            scheduler=args["scheduler"],  # type: ignore[arg-type]
            scaler=args["scaler"],  # type: ignore[arg-type]
            restore_rng=True,
        )
