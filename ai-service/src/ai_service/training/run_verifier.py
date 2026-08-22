"""Read-only verifier for completed, pre-evaluation training runs."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

from ai_service.config import Settings, load_resolved_settings
from ai_service.contracts import (
    CheckpointManifest,
    PipelineState,
    RunStatus,
    TerminalAction,
    TrainingVariant,
)
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle
from ai_service.training.stopping import EarlyStoppingController
from ai_service.training.trainer import EpochMetrics

_HISTORY_FIELDS = {field.name for field in fields(EpochMetrics)}
_INTEGER_HISTORY_FIELDS = frozenset({"epoch", "global_step", "peak_ram_bytes", "peak_vram_bytes"})
_BOOLEAN_HISTORY_FIELDS = frozenset(
    {
        "checkpoint_guardrails_passed",
        "is_best",
        "early_peak_warning",
        "model_hard_cache_updated",
    }
)
_STRING_HISTORY_FIELDS = frozenset({"terminal_action", "stopping_reason"})
_NUMERIC_HISTORY_FIELDS = (
    _HISTORY_FIELDS - _INTEGER_HISTORY_FIELDS - _BOOLEAN_HISTORY_FIELDS - _STRING_HISTORY_FIELDS
)
_CHECKPOINT_METRICS = frozenset({"val_gauc", "val_ndcg_at_k", "val_hr_at_k", "train_loss"})


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError(f"cannot read JSON artifact: {path}") from error
    if not isinstance(value, dict):
        raise ArtifactIntegrityError(f"JSON artifact is not an object: {path}")
    return cast(dict[str, object], value)


def _finite_number(value: object, *, description: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArtifactIntegrityError(f"{description} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ArtifactIntegrityError(f"{description} must be finite")
    return numeric


def _load_history(path: Path) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ArtifactIntegrityError(f"cannot read training history: {path}") from error

    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ArtifactIntegrityError(
                f"training history contains invalid JSON at line {line_number}"
            ) from error
        if not isinstance(row, dict):
            raise ArtifactIntegrityError(
                f"training history row is not an object at line {line_number}"
            )
        rows.append(cast(dict[str, object], row))

    if not rows:
        raise ArtifactIntegrityError("training history is empty")
    return rows


def _validate_history(rows: list[dict[str, object]]) -> None:
    epochs: list[int] = []
    for index, row in enumerate(rows, start=1):
        if set(row) != _HISTORY_FIELDS:
            missing = sorted(_HISTORY_FIELDS - set(row))
            unexpected = sorted(set(row) - _HISTORY_FIELDS)
            raise ArtifactIntegrityError(
                "training history fields differ from EpochMetrics: "
                f"missing={missing}, unexpected={unexpected}"
            )
        for name in _INTEGER_HISTORY_FIELDS:
            value = row[name]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ArtifactIntegrityError(f"history field must be an integer: {name}")
        for name in _BOOLEAN_HISTORY_FIELDS:
            if not isinstance(row[name], bool):
                raise ArtifactIntegrityError(f"history field must be a boolean: {name}")
        for name in _STRING_HISTORY_FIELDS:
            if not isinstance(row[name], str):
                raise ArtifactIntegrityError(f"history field must be a string: {name}")
        for name in _NUMERIC_HISTORY_FIELDS:
            _finite_number(row[name], description=f"history diagnostic {name}")
        try:
            TerminalAction(cast(str, row["terminal_action"]))
        except ValueError as error:
            raise ArtifactIntegrityError("history terminal action is invalid") from error
        if not cast(str, row["stopping_reason"]).strip():
            raise ArtifactIntegrityError("history stopping reason is empty")
        if not bool(row["model_hard_cache_updated"]):
            raise ArtifactIntegrityError(
                f"model hard cache was not updated for completed epoch {index}"
            )
        epochs.append(cast(int, row["epoch"]))

    if epochs != list(range(1, len(rows) + 1)):
        raise ArtifactIntegrityError("training history epochs are not continuous")


def _checkpoint_eligible(
    settings: Settings,
    row: Mapping[str, object],
    *,
    training_variant: TrainingVariant,
) -> bool:
    del settings, training_variant
    # The history persists whether a checkpoint was selected, but not every
    # evaluator value that determines selection eligibility.  A selected row
    # is necessarily eligible; for an unselected row, treating it as
    # ineligible reproduces the same stopping-state transition.
    return bool(row["is_best"])


def _replay_stopping(
    settings: Settings,
    rows: list[dict[str, object]],
    *,
    training_variant: TrainingVariant,
) -> dict[int, dict[str, object]]:
    controller = EarlyStoppingController(
        patience=settings.train.early_stopping_patience,
        min_delta=settings.train.min_delta,
        minimum_gauc=0.50,
        max_wall_minutes=settings.train.max_wall_minutes,
    )
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    states: dict[int, dict[str, object]] = {}
    for row in rows:
        epoch = cast(int, row["epoch"])
        decision = controller.evaluate(
            epoch,
            _finite_number(row["val_gauc"], description="history diagnostic val_gauc"),
            _finite_number(row["val_ndcg_at_k"], description="history diagnostic val_ndcg_at_k"),
            _finite_number(row["val_hr_at_k"], description="history diagnostic val_hr_at_k"),
            start_time=timestamp,
            current_time=timestamp,
            checkpoint_eligible=_checkpoint_eligible(
                settings, row, training_variant=training_variant
            ),
            eligibility_reason=(
                "diagnostic warmup"
                if settings.train.campaign_stage == "diagnostic"
                and epoch < settings.train.diagnostic_warmup_epochs
                else ""
            ),
        )
        expected_action = decision.terminal_action
        if expected_action is TerminalAction.CONTINUE and epoch == settings.train.max_epochs:
            expected_action = TerminalAction.COMPLETED
        if bool(row["is_best"]) is not (decision.checkpoint_action.value != "none"):
            raise ArtifactIntegrityError(f"history checkpoint selection mismatch at epoch {epoch}")
        if TerminalAction(cast(str, row["terminal_action"])) is not expected_action:
            raise ArtifactIntegrityError(f"history terminal action mismatch at epoch {epoch}")
        states[epoch] = controller.state_dict()
    return states


def _load_manifest(path: Path) -> CheckpointManifest:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    try:
        return CheckpointManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError(
            f"cannot strict-load checkpoint manifest: {manifest_path}"
        ) from error


def _optimizer_and_scheduler(
    model: HybridTwoTowerModel,
    settings: Settings,
    training_variant: TrainingVariant,
) -> tuple[AdamW, LambdaLR]:
    parameters = (
        [
            parameter
            for name, parameter in model.named_parameters()
            if not name.startswith("wide_layer.")
        ]
        if training_variant is TrainingVariant.DEEP_ONLY
        else list(model.parameters())
    )
    optimizer = AdamW(
        parameters,
        lr=settings.train.learning_rate,
        weight_decay=settings.train.weight_decay,
    )
    return optimizer, LambdaLR(optimizer, lambda _step: 1.0)


def _strict_load_checkpoint(
    path: Path,
    *,
    settings: Settings,
    lineage: Mapping[str, str],
    training_variant: TrainingVariant,
    run_id: str,
    checkpoint_kind: str,
) -> tuple[CheckpointManifest, dict[str, Any], HybridTwoTowerModel]:
    manifest = _load_manifest(path)
    model = HybridTwoTowerModel(settings)
    optimizer, scheduler = _optimizer_and_scheduler(model, settings, training_variant)
    state = CheckpointManager.load(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        expected_lineage=lineage,
        expected_training_signature=settings.training_signature_sha256(),
        expected_comparison_signature=settings.comparison_signature_sha256(),
        expected_training_variant=training_variant,
        expected_checkpoint_kind=checkpoint_kind,
        expected_run_id=run_id,
        require_resume_state=True,
    )
    for name, parameter in model.named_parameters():
        if not bool(torch.isfinite(parameter).all()):
            raise ArtifactIntegrityError(f"checkpoint model parameter is non-finite: {name}")
    return manifest, state, model


def _stopping_state(state: Mapping[str, Any], *, checkpoint_name: str) -> dict[str, object]:
    value = state.get("stopping_state")
    if not isinstance(value, Mapping):
        raise ArtifactIntegrityError(f"{checkpoint_name} checkpoint stopping state is missing")
    stopping_state = dict(value)
    controller = EarlyStoppingController()
    try:
        controller.load_state_dict(stopping_state)
    except ValueError as error:
        raise ArtifactIntegrityError(
            f"{checkpoint_name} checkpoint stopping state is invalid"
        ) from error
    return stopping_state


def _assert_checkpoint_metrics(
    manifest: CheckpointManifest,
    state: Mapping[str, Any],
    row: Mapping[str, object],
    *,
    checkpoint_name: str,
) -> None:
    metrics = state.get("metrics")
    if not isinstance(metrics, Mapping) or set(metrics) != _CHECKPOINT_METRICS:
        raise ArtifactIntegrityError(f"{checkpoint_name} checkpoint metrics are incomplete")
    for name in _CHECKPOINT_METRICS:
        if _finite_number(
            metrics[name], description=f"{checkpoint_name} checkpoint metric {name}"
        ) != _finite_number(row[name], description=f"history metric {name}"):
            raise ArtifactIntegrityError(
                f"{checkpoint_name} checkpoint metric differs from training history: {name}"
            )
    manifest_metrics = {
        "val_gauc": manifest.best_val_gauc,
        "val_ndcg_at_k": manifest.best_val_ndcg_at_k,
        "val_hr_at_k": manifest.best_val_hr_at_k,
    }
    for name, value in manifest_metrics.items():
        if value != _finite_number(row[name], description=f"history metric {name}"):
            raise ArtifactIntegrityError(
                f"{checkpoint_name} manifest metric differs from training history: {name}"
            )


def _validate_summary(
    summary: Mapping[str, object],
    rows: list[dict[str, object]],
    best_manifest: CheckpointManifest,
    *,
    run_id: str,
) -> None:
    if summary.get("run_id") not in (None, run_id):
        raise ArtifactIntegrityError("training summary run ID mismatch")
    epochs_completed = summary.get("epochs_completed")
    if (
        isinstance(epochs_completed, bool)
        or not isinstance(epochs_completed, int)
        or epochs_completed != len(rows)
    ):
        raise ArtifactIntegrityError("training summary completed epoch count differs from history")
    try:
        action = TerminalAction(cast(str, summary["terminal_action"]))
    except (KeyError, ValueError) as error:
        raise ArtifactIntegrityError("training summary terminal action is invalid") from error
    if action not in {TerminalAction.COMPLETED, TerminalAction.STOP_PLATEAU}:
        raise ArtifactIntegrityError("training summary is not a successful terminal training state")
    final_row = rows[-1]
    if action is not TerminalAction(cast(str, final_row["terminal_action"])):
        raise ArtifactIntegrityError("training summary terminal action differs from history")
    for name in ("terminal_reason", "stop_reason"):
        value = summary.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ArtifactIntegrityError(f"training summary {name} is invalid")
        if value != final_row["stopping_reason"]:
            raise ArtifactIntegrityError(f"training summary {name} differs from history")
    best_epoch = summary.get("best_epoch")
    if (
        isinstance(best_epoch, bool)
        or not isinstance(best_epoch, int)
        or best_epoch != best_manifest.best_epoch
    ):
        raise ArtifactIntegrityError("training summary best epoch differs from best checkpoint")
    summary_metrics = {
        "best_val_gauc": best_manifest.best_val_gauc,
        "best_val_ndcg_at_k": best_manifest.best_val_ndcg_at_k,
        "best_val_hr_at_k": best_manifest.best_val_hr_at_k,
    }
    for name, expected in summary_metrics.items():
        if _finite_number(summary.get(name), description=f"training summary {name}") != expected:
            raise ArtifactIntegrityError(
                f"training summary metric differs from best checkpoint: {name}"
            )


def _reject_evaluation_or_release_side_effects(run_dir: Path, state: PipelineState) -> None:
    if (
        state.paired_run_id is not None
        or state.validation_gate_passed
        or state.test_gate_passed
        or state.validation_victory_matrix_path is not None
        or state.test_victory_matrix_path is not None
        or state.bundle_path is not None
    ):
        raise ArtifactIntegrityError("pipeline state contains evaluation or release side effects")
    checkpoints = run_dir / "checkpoints"
    for path in (
        checkpoints / "pareto",
        checkpoints / "release-candidate.pt",
        checkpoints / "release-candidate.pt.manifest.json",
        run_dir / "release-candidate.pt",
        run_dir / "release-candidate.pt.manifest.json",
        run_dir / "evaluation",
        run_dir / "evaluation-release",
        run_dir / "release",
        run_dir / "releases",
    ):
        if path.exists():
            raise ArtifactIntegrityError(f"unexpected evaluation or release side effect: {path}")


def _assert_deep_or_hybrid_invariants(
    rows: list[dict[str, object]],
    *,
    training_variant: TrainingVariant,
    best_model: HybridTwoTowerModel,
    last_model: HybridTwoTowerModel,
) -> None:
    if training_variant is TrainingVariant.HYBRID:
        first_gradient = _finite_number(
            rows[0]["wide_gradient_norm"], description="Hybrid epoch-one Wide gradient norm"
        )
        if first_gradient <= 0.0:
            raise ArtifactIntegrityError("Hybrid epoch-one Wide gradient must be greater than zero")
        return

    for row in rows:
        if (
            _finite_number(row["wide_gradient_norm"], description="Deep-only Wide gradient norm")
            != 0.0
        ):
            raise ArtifactIntegrityError("Deep-only Wide gradient invariant failed")
    best_parameters = dict(best_model.wide_layer.named_parameters())
    last_parameters = dict(last_model.wide_layer.named_parameters())
    if set(best_parameters) != set(last_parameters):
        raise ArtifactIntegrityError("Deep-only Wide parameter sets differ between checkpoints")
    for name, best_parameter in best_parameters.items():
        if not torch.equal(best_parameter, last_parameters[name]):
            raise ArtifactIntegrityError("Deep-only Wide parameters changed after best checkpoint")


def verify_training_run(
    artifact_root: Path,
    run_id: str,
    *,
    expected_variant: TrainingVariant,
    expected_stage: str,
    expected_snapshot_id: str,
) -> dict[str, object]:
    """Verify a successful run before it is handed to evaluation or release workflows."""
    run_dir = artifact_root.resolve() / "runs" / run_id
    if not run_dir.is_dir():
        raise ArtifactIntegrityError(f"training run does not exist: {run_dir}")
    lifecycle = RunLifecycle.load(run_dir)
    if lifecycle.status is not RunStatus.TRAINING:
        raise ArtifactIntegrityError(
            "training verifier requires a pre-evaluation training lifecycle"
        )
    try:
        settings = load_resolved_settings(run_dir / "resolved-config.json")
    except ConfigurationError as error:
        raise ArtifactIntegrityError(
            "resolved training configuration cannot be strict-loaded"
        ) from error
    if settings.train.training_variant is not expected_variant:
        raise ArtifactIntegrityError("resolved training variant does not match requested variant")
    if settings.train.campaign_stage != expected_stage:
        raise ArtifactIntegrityError("training campaign stage differs from expected stage")
    if settings.data.snapshot_id != expected_snapshot_id:
        raise ArtifactIntegrityError("training snapshot ID differs from expected snapshot")
    if lifecycle.document.get("training_variant") != expected_variant.value:
        raise ArtifactIntegrityError(
            "run manifest training variant does not match requested variant"
        )
    if lifecycle.document.get("training_signature_sha256") != settings.training_signature_sha256():
        raise ArtifactIntegrityError("run manifest training signature differs from resolved config")
    if (
        lifecycle.document.get("comparison_signature_sha256")
        != settings.comparison_signature_sha256()
    ):
        raise ArtifactIntegrityError(
            "run manifest comparison signature differs from resolved config"
        )
    if (
        lifecycle.document.get("experiment_signature_sha256")
        != settings.experiment_signature_sha256()
    ):
        raise ArtifactIntegrityError(
            "run manifest experiment signature differs from resolved config"
        )

    try:
        state = PipelineState.model_validate_json((run_dir / "pipeline-state.json").read_text())
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("pipeline state cannot be strict-loaded") from error
    if state.run_id != run_id or state.training_variant is not expected_variant:
        raise ArtifactIntegrityError("pipeline state identity mismatch")
    if state.snapshot_id != expected_snapshot_id:
        raise ArtifactIntegrityError("pipeline state snapshot ID differs from expected snapshot")
    if state.lineage is None:
        raise ArtifactIntegrityError("pipeline state is missing artifact lineage")
    lineage = state.lineage.as_mapping()
    if lifecycle.document.get("lineage") != lineage:
        raise ArtifactIntegrityError("run manifest and pipeline state lineage differ")

    checkpoints = run_dir / "checkpoints"
    best_path = checkpoints / "best.pt"
    last_path = checkpoints / "last.pt"
    if not best_path.is_file() or not last_path.is_file():
        raise ArtifactIntegrityError("best.pt and last.pt are required")
    if state.checkpoint_path != str(best_path):
        raise ArtifactIntegrityError("pipeline state must point to checkpoints/best.pt")
    _reject_evaluation_or_release_side_effects(run_dir, state)

    best_manifest, best_state, best_model = _strict_load_checkpoint(
        best_path,
        settings=settings,
        lineage=lineage,
        training_variant=expected_variant,
        run_id=run_id,
        checkpoint_kind="best",
    )
    last_manifest, last_state, last_model = _strict_load_checkpoint(
        last_path,
        settings=settings,
        lineage=lineage,
        training_variant=expected_variant,
        run_id=run_id,
        checkpoint_kind="last",
    )
    rows = _load_history(run_dir / "training" / "history.jsonl")
    _validate_history(rows)
    if last_manifest.best_epoch != len(rows):
        raise ArtifactIntegrityError(
            "last checkpoint epoch differs from completed training history"
        )
    if (
        expected_stage == "diagnostic"
        and best_manifest.best_epoch < settings.train.diagnostic_warmup_epochs
    ):
        raise ArtifactIntegrityError("selected checkpoint precedes diagnostic warmup")

    stopping_states = _replay_stopping(settings, rows, training_variant=expected_variant)
    best_stopping_state = _stopping_state(best_state, checkpoint_name="best")
    last_stopping_state = _stopping_state(last_state, checkpoint_name="last")
    if best_stopping_state != stopping_states[best_manifest.best_epoch]:
        raise ArtifactIntegrityError("best checkpoint stopping state differs from training history")
    if last_stopping_state != stopping_states[last_manifest.best_epoch]:
        raise ArtifactIntegrityError("last checkpoint stopping state differs from training history")
    if cast(int, last_stopping_state["selected_epoch"]) != best_manifest.best_epoch:
        raise ArtifactIntegrityError("last checkpoint selected epoch differs from best checkpoint")

    best_row = rows[best_manifest.best_epoch - 1]
    last_row = rows[-1]
    if not bool(best_row["is_best"]):
        raise ArtifactIntegrityError("best checkpoint epoch is not selected in training history")
    if (
        max(cast(int, row["epoch"]) for row in rows if bool(row["is_best"]))
        != best_manifest.best_epoch
    ):
        raise ArtifactIntegrityError("best checkpoint does not match the final history selection")
    _assert_checkpoint_metrics(best_manifest, best_state, best_row, checkpoint_name="best")
    _assert_checkpoint_metrics(last_manifest, last_state, last_row, checkpoint_name="last")
    _validate_summary(
        _read_json(run_dir / "training" / "summary.json"),
        rows,
        best_manifest,
        run_id=run_id,
    )
    _assert_deep_or_hybrid_invariants(
        rows,
        training_variant=expected_variant,
        best_model=best_model,
        last_model=last_model,
    )

    return {
        "passed": True,
        "run_id": run_id,
        "status": lifecycle.status.value,
        "epochs": len(rows),
        "best_checkpoint_sha256": best_manifest.content_sha256,
        "last_checkpoint_sha256": last_manifest.content_sha256,
    }


__all__ = ["verify_training_run"]
