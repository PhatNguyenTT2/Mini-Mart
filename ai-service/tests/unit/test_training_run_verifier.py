from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    PipelineState,
    RunStatus,
    TerminalAction,
    TrainingVariant,
    artifact_lineage_model,
)
from ai_service.errors import ArtifactIntegrityError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle
from ai_service.training.run_verifier import verify_training_run
from ai_service.training.trainer import EpochMetrics

_LINEAGE = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
_SNAPSHOT_ID = "training-verifier-snapshot"


def _settings(root: Path, variant: TrainingVariant) -> Settings:
    return Settings(
        {
            "data": {
                "artifact_root": str(root),
                "snapshot_id": _SNAPSHOT_ID,
                "num_users": 4,
                "num_items": 8,
                "num_cold_items": 1,
                "num_personas": 4,
                "num_leaf_categories": 4,
                "num_price_buckets": 2,
            },
            "model": {"sbert_dim": 8},
            "train": {
                "training_variant": variant.value,
                "campaign_stage": "diagnostic",
                "max_epochs": 2,
                "diagnostic_warmup_epochs": 2,
                "batch_size": 2,
                "validation_user_batch_size": 2,
            },
            "eval": {"k": 10, "random_seeds": 10},
        }
    )


def _epoch_metrics(
    epoch: int,
    *,
    is_best: bool,
    variant: TrainingVariant,
) -> EpochMetrics:
    final = epoch == 2
    return EpochMetrics(
        epoch=epoch,
        global_step=epoch * 10,
        train_loss=0.5 + 0.1 * epoch,
        purchase_loss=0.4,
        view_loss=0.1,
        wide_loss=0.0,
        val_gauc=0.70 + 0.05 * epoch,
        val_hr_at_k=0.30,
        val_ndcg_at_k=0.20,
        val_deep_gauc=0.70,
        val_deep_ndcg_at_k=0.15,
        val_wide_gauc=0.60,
        val_wide_ndcg_at_k=0.10,
        checkpoint_guardrails_passed=True,
        learning_rate=0.001,
        sampled_pair_accuracy=0.75,
        all_negative_win_rate=0.75,
        margin_p10=0.1,
        margin_p50=0.2,
        margin_p90=0.3,
        gradient_norm=1.0,
        user_tower_gradient_norm=0.5,
        item_tower_gradient_norm=0.5,
        wide_gradient_norm=0.0 if variant is TrainingVariant.DEEP_ONLY else 0.25,
        positive_logit_p10=0.1,
        positive_logit_p50=0.2,
        positive_logit_p90=0.3,
        negative_logit_p10=-0.3,
        negative_logit_p50=-0.2,
        negative_logit_p90=-0.1,
        in_batch_rule_present_rate=0.5,
        explicit_rule_present_rate=0.5,
        rows_with_any_rule_rate=0.5,
        wide_to_deep_logit_rms_ratio=0.1,
        hybrid_deep_top_k_change_rate=0.1,
        elapsed_seconds=float(epoch),
        peak_ram_bytes=1,
        peak_vram_bytes=0,
        gpu_utilization_median=0.0,
        data_wait_ratio=0.0,
        is_best=is_best,
        early_peak_warning=False,
        deep_logit_rms=1.0,
        wide_logit_rms=0.1,
        hybrid_logit_rms=1.1,
        strict_target_rule_rate=0.5,
        other_positive_rule_rate=0.1,
        valid_negative_rule_rate=0.5,
        explicit_negative_rule_rate=0.5,
        negative_only_row_rate=0.1,
        rule_loss=0.0,
        model_hard_cache_updated=True,
        terminal_action=TerminalAction.COMPLETED if final else TerminalAction.CONTINUE,
        stopping_reason="maximum epochs completed" if final else "diagnostic warmup",
    )


def _checkpoint_args(
    model: HybridTwoTowerModel,
    settings: Settings,
    variant: TrainingVariant,
    *,
    epoch: int,
    checkpoint_kind: str,
    stopping_state: Mapping[str, object],
    run_id: str,
) -> dict[str, Any]:
    parameters = (
        [
            parameter
            for name, parameter in model.named_parameters()
            if not name.startswith("wide_layer.")
        ]
        if variant is TrainingVariant.DEEP_ONLY
        else list(model.parameters())
    )
    optimizer = AdamW(parameters, lr=settings.train.learning_rate)
    scheduler = LambdaLR(optimizer, lambda _step: 1.0)
    metrics = _epoch_metrics(epoch, is_best=checkpoint_kind == "best", variant=variant)
    return {
        "model": model,
        "optimizer": optimizer,
        "scheduler": scheduler,
        "scaler": SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _value: None),
        "epoch": epoch,
        "metrics": {
            "val_gauc": metrics.val_gauc,
            "val_ndcg_at_k": metrics.val_ndcg_at_k,
            "val_hr_at_k": metrics.val_hr_at_k,
            "train_loss": metrics.train_loss,
        },
        "stopping_state": stopping_state,
        "checkpoint_kind": checkpoint_kind,
        "lineage": _LINEAGE,
        "training_signature_sha256": settings.training_signature_sha256(),
        "comparison_signature_sha256": settings.comparison_signature_sha256(),
        "training_variant": variant,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "run_id": run_id,
    }


def _create_run(
    root: Path,
    variant: TrainingVariant = TrainingVariant.HYBRID,
    *,
    selected_epoch: int = 2,
) -> Path:
    settings = _settings(root, variant)
    run_id = f"verifier-{variant.value}"
    run_dir = root / "runs" / run_id
    lifecycle = RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage=_LINEAGE,
        git_commit="0" * 40,
    )
    lifecycle.transition(RunStatus.TRAINING)

    history = [
        _epoch_metrics(epoch, is_best=epoch == selected_epoch, variant=variant) for epoch in (1, 2)
    ]
    history_path = run_dir / "training" / "history.jsonl"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        "".join(json.dumps(asdict(row), sort_keys=True) + "\n" for row in history),
        encoding="utf-8",
    )

    selected = history[selected_epoch - 1]
    best_state = {
        "highest_gauc": selected.val_gauc,
        "selected_epoch": selected_epoch,
        "selected_gauc": selected.val_gauc,
        "selected_ndcg": selected.val_ndcg_at_k,
        "selected_hr": selected.val_hr_at_k,
        "patience_used": 0,
    }
    last_state = (
        best_state
        if selected_epoch == 2
        else {
            **best_state,
            "highest_gauc": history[-1].val_gauc,
            "patience_used": 1,
        }
    )
    model = HybridTwoTowerModel(settings)
    checkpoints = run_dir / "checkpoints"
    best_path = checkpoints / "best.pt"
    last_path = checkpoints / "last.pt"
    CheckpointManager.save(
        best_path,
        **_checkpoint_args(
            model,
            settings,
            variant,
            epoch=selected_epoch,
            checkpoint_kind="best",
            stopping_state=best_state,
            run_id=run_id,
        ),
    )
    CheckpointManager.save(
        last_path,
        **_checkpoint_args(
            model,
            settings,
            variant,
            epoch=2,
            checkpoint_kind="last",
            stopping_state=last_state,
            run_id=run_id,
        ),
    )
    summary = {
        "best_epoch": selected_epoch,
        "best_val_gauc": selected.val_gauc,
        "best_val_ndcg_at_k": selected.val_ndcg_at_k,
        "best_val_hr_at_k": selected.val_hr_at_k,
        "epochs_completed": 2,
        "stop_reason": "maximum epochs completed",
        "terminal_reason": "maximum epochs completed",
        "terminal_action": TerminalAction.COMPLETED.value,
    }
    (run_dir / "training" / "summary.json").write_text(
        json.dumps(summary, sort_keys=True), encoding="utf-8"
    )
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id=run_id,
        training_variant=variant,
        snapshot_id=_SNAPSHOT_ID,
        embedding_path=str(root / "embeddings"),
        rule_path=str(root / "rules"),
        checkpoint_path=str(best_path),
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
        lineage=artifact_lineage_model(_LINEAGE),
    )
    (run_dir / "pipeline-state.json").write_text(state.model_dump_json(), encoding="utf-8")
    return run_dir


def _refresh_manifest_checksum(path: Path) -> None:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")


def _rewrite_payload(path: Path, mutate: Any) -> None:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    mutate(payload)
    torch.save(payload, path)
    _refresh_manifest_checksum(path)


@pytest.mark.parametrize("variant", [TrainingVariant.HYBRID, TrainingVariant.DEEP_ONLY])
def test_verifier_accepts_complete_pre_evaluation_run(
    tmp_path: Path, variant: TrainingVariant
) -> None:
    run_dir = _create_run(tmp_path, variant)

    result = verify_training_run(
        tmp_path,
        run_dir.name,
        expected_variant=variant,
        expected_stage="diagnostic",
        expected_snapshot_id=_SNAPSHOT_ID,
    )

    assert result["passed"] is True
    assert result["epochs"] == 2


def test_verifier_rejects_corrupt_checkpoint_payload(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)
    _rewrite_payload(run_dir / "checkpoints" / "last.pt", lambda payload: payload.update(model={}))

    with pytest.raises(ArtifactIntegrityError, match="strict-loaded"):
        verify_training_run(
            tmp_path,
            run_dir.name,
            expected_variant=TrainingVariant.HYBRID,
            expected_stage="diagnostic",
            expected_snapshot_id=_SNAPSHOT_ID,
        )


def test_verifier_rejects_inconsistent_stopping_state(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        payload["stopping_state"] = {
            "highest_gauc": 0.80,
            "selected_epoch": 1,
            "selected_gauc": 0.75,
            "selected_ndcg": 0.20,
            "selected_hr": 0.30,
            "patience_used": 1,
        }

    _rewrite_payload(run_dir / "checkpoints" / "last.pt", mutate)

    with pytest.raises(ArtifactIntegrityError, match="last checkpoint stopping state differs"):
        verify_training_run(
            tmp_path,
            run_dir.name,
            expected_variant=TrainingVariant.HYBRID,
            expected_stage="diagnostic",
            expected_snapshot_id=_SNAPSHOT_ID,
        )


def test_verifier_rejects_checkpoint_metric_mismatch(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)
    _rewrite_payload(
        run_dir / "checkpoints" / "last.pt",
        lambda payload: payload["metrics"].update(train_loss=0.99),
    )

    with pytest.raises(ArtifactIntegrityError, match="last checkpoint metric differs"):
        verify_training_run(
            tmp_path,
            run_dir.name,
            expected_variant=TrainingVariant.HYBRID,
            expected_stage="diagnostic",
            expected_snapshot_id=_SNAPSHOT_ID,
        )


def test_verifier_rejects_pre_warmup_selected_checkpoint(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path, selected_epoch=1)

    with pytest.raises(ArtifactIntegrityError, match="precedes diagnostic warmup"):
        verify_training_run(
            tmp_path,
            run_dir.name,
            expected_variant=TrainingVariant.HYBRID,
            expected_stage="diagnostic",
            expected_snapshot_id=_SNAPSHOT_ID,
        )


def test_verifier_rejects_evaluation_side_effect(tmp_path: Path) -> None:
    run_dir = _create_run(tmp_path)
    (run_dir / "evaluation").mkdir()

    with pytest.raises(ArtifactIntegrityError, match="evaluation or release side effect"):
        verify_training_run(
            tmp_path,
            run_dir.name,
            expected_variant=TrainingVariant.HYBRID,
            expected_stage="diagnostic",
            expected_snapshot_id=_SNAPSHOT_ID,
        )
