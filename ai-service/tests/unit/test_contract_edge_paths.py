from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import MODEL_SCHEMA_VERSION
from ai_service.contracts import RunStatus, TrainingVariant
from ai_service.data.rules import AprioriRuleMiner, RuleStore, load_rule_artifact
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.cold_start import evaluate_cold_start
from ai_service.evaluation.full_catalog import EvaluationResult, prepare_split
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle
from tests.support.v5_factories import make_settings, make_snapshot


def test_rule_miner_publishes_full_statistics_and_loader_rejects_corruption(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    settings.data.min_rule_count = 1
    settings.data.min_rule_lift = 1.0
    snapshot = make_snapshot(tmp_path)
    snapshot = replace(
        snapshot,
        order_baskets_df=pd.DataFrame(
            {
                "order_id": [1, 1, 2, 2],
                "internal_product_id": [0, 1, 0, 1],
            }
        ),
    )
    artifact = AprioriRuleMiner(settings).mine(snapshot)
    loaded = load_rule_artifact(artifact.artifact_dir, snapshot.manifest.num_items)
    assert loaded.manifest.has_full_statistics is True
    assert loaded.require_training_capability().features.shape[1] == 3
    with np.load(artifact.artifact_dir / "rules.npz", allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    arrays["values"] = arrays["values"].copy()
    if len(arrays["values"]):
        arrays["values"][0] = np.nan
    np.savez_compressed(artifact.artifact_dir / "rules.npz", **arrays)
    with pytest.raises(ArtifactIntegrityError, match="rule CSR values"):
        load_rule_artifact(artifact.artifact_dir, snapshot.manifest.num_items)


@pytest.mark.parametrize(
    "rules",
    [
        [(0, 5, 1.0)],
        [(0, 1, 1.0, float("nan"), 0.8, 1)],
        [(0, 1, 1.0), (0, 1, 2.0)],
    ],
)
def test_rule_store_rejects_invalid_coordinates_values_and_duplicates(rules: list[tuple]) -> None:
    with pytest.raises(DataIntegrityError):
        RuleStore(2, rules, min_lift=0.0)


def test_rule_store_lookup_and_batch_shape_guards() -> None:
    store = RuleStore(3, [(0, 1, 3.0, 0.2, 0.8, 3)])
    assert store.lookup(-1, 1) == 0.0
    assert store.lookup(0, 1) > 0
    assert store.lookup(0, 2) == 0.0
    with pytest.raises(DataIntegrityError):
        store.batch_lookup(np.asarray([0]), np.zeros((2, 3), dtype=np.int64))
    with pytest.raises(DataIntegrityError):
        store.batch_raw_lift(np.asarray([0, 1]), np.zeros((1, 3), dtype=np.int64))


def test_run_lifecycle_terminal_summary_and_invalid_manifest(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    run_dir = tmp_path / "runs" / "lifecycle"
    lifecycle = RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="0" * 40,
    )
    with pytest.raises(ArtifactIntegrityError, match="illegal run transition"):
        lifecycle.transition(RunStatus.INTERRUPTED, reason="stop")
    lifecycle.transition(RunStatus.TRAINING)
    with pytest.raises(ArtifactIntegrityError, match="requires a reason"):
        lifecycle.transition(RunStatus.FAILED)
    summary_path = run_dir / "training" / "summary.json"
    summary_path.parent.mkdir()
    summary_path.write_text(
        json.dumps({"terminal_reason": "boom", "terminal_action": "failed"}),
        encoding="utf-8",
    )
    lifecycle.transition_training_terminal(RunStatus.FAILED, reason="boom")
    assert RunLifecycle.load(run_dir).status is RunStatus.FAILED
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    manifest["lineage"]["snapshot"] = "not-a-sha"
    (run_dir / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="lineage value"):
        RunLifecycle.load(run_dir)


def test_checkpoint_preflight_rejects_incomplete_metrics_and_stopping_state(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    scaler = SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _state: None)
    kwargs = {
        "model": model,
        "optimizer": optimizer,
        "scheduler": scheduler,
        "scaler": scaler,
        "epoch": 1,
        "lineage": {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        "training_signature_sha256": settings.training_signature_sha256(),
        "comparison_signature_sha256": settings.comparison_signature_sha256(),
        "training_variant": TrainingVariant.HYBRID,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "run_id": "checkpoint-edge",
        "checkpoint_kind": "best",
    }
    with pytest.raises(ArtifactIntegrityError, match="complete finite"):
        CheckpointManager.save(
            tmp_path / "checkpoints" / "best.pt",
            metrics={"val_gauc": 0.8},
            stopping_state={},
            **kwargs,
        )
    with pytest.raises(ArtifactIntegrityError, match="stopping state fields"):
        CheckpointManager.save(
            tmp_path / "checkpoints" / "best.pt",
            metrics={
                "val_gauc": 0.8,
                "val_ndcg_at_k": 0.4,
                "val_hr_at_k": 0.5,
                "train_loss": 0.2,
            },
            stopping_state={"highest_gauc": 0.8},
            **kwargs,
        )


def test_checkpoint_loader_rejects_missing_files_and_metadata_mismatches(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    scaler = SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _state: None)
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    path = tmp_path / "checkpoints" / "last.pt"
    CheckpointManager.save(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        scaler=scaler,
        epoch=1,
        metrics={
            "val_gauc": 0.8,
            "val_ndcg_at_k": 0.4,
            "val_hr_at_k": 0.5,
            "train_loss": 0.2,
        },
        stopping_state={
            "highest_gauc": 0.8,
            "selected_epoch": 0,
            "selected_gauc": -float("inf"),
            "selected_ndcg": -float("inf"),
            "selected_hr": -float("inf"),
            "patience_used": 1,
        },
        checkpoint_kind="last",
        lineage=lineage,
        training_signature_sha256=settings.training_signature_sha256(),
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        training_variant=TrainingVariant.HYBRID,
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id="last-edge",
    )
    common = {
        "model": model,
        "expected_lineage": lineage,
        "expected_training_signature": settings.training_signature_sha256(),
        "expected_comparison_signature": settings.comparison_signature_sha256(),
        "expected_training_variant": TrainingVariant.HYBRID,
    }
    CheckpointManager.load(path, expected_checkpoint_kind="last", **common)
    with pytest.raises(ArtifactIntegrityError, match="kind mismatch"):
        CheckpointManager.load(path, expected_checkpoint_kind="best", **common)
    with pytest.raises(ArtifactIntegrityError, match="schema mismatch"):
        CheckpointManager.load(path, expected_model_schema_version="6.0.0", **common)
    with pytest.raises(ArtifactIntegrityError, match="lineage mismatch"):
        CheckpointManager.load(path, model=model, expected_lineage={**lineage, "rules": "d" * 64})
    path.with_suffix(path.suffix + ".manifest.json").unlink()
    with pytest.raises(ArtifactIntegrityError, match="manifest missing"):
        CheckpointManager.load(path, model=model)


def test_cold_start_report_checks_coverage_and_metrics(tmp_path: Path) -> None:
    snapshot = make_snapshot(tmp_path, num_users=4, num_items=12, num_cold_items=4)
    # The fixture test split contains every cold item exactly once.
    user_ids = np.arange(1, 5, dtype=np.int64)
    result = EvaluationResult(
        report=SimpleNamespace(k=10),
        user_ids=user_ids,
        per_user_hr=np.ones(4),
        per_user_ndcg=np.ones(4),
        per_user_gauc=np.ones(4),
        top_k_by_user={user: (snapshot.cold_item_ids[user - 1],) for user in user_ids},
    )
    report = evaluate_cold_start(result, snapshot, RuleStore(12, []))
    assert report.ground_truth_coverage == 1.0
    assert report.recommendation_coverage == 1.0


def test_prepared_split_excludes_user_zero_and_freezes_arrays(tmp_path: Path) -> None:
    snapshot = make_snapshot(tmp_path)
    prepared = prepare_split(
        snapshot, __import__("ai_service.contracts", fromlist=["SplitName"]).SplitName.VAL
    )
    assert 0 not in prepared.scoring_users
    assert 0 not in prepared.eligible_users
    assert prepared.scoring_users.flags.writeable is False
    with pytest.raises(ValueError):
        prepared.scoring_users[0] = 99
