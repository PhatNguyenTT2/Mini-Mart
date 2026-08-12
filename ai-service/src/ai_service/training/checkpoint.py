"""Atomic, resumable training checkpoints."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import random
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
from torch import nn
from torch.optim import Optimizer

from ai_service.config import MODEL_SCHEMA_VERSION
from ai_service.contracts import (
    ArtifactLineageInput,
    CheckpointManifest,
    TrainingVariant,
    normalize_artifact_lineage,
)
from ai_service.errors import ArtifactIntegrityError


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_stopping_state(
    stopping_state: Mapping[str, object],
    *,
    epoch: int,
    checkpoint_kind: Literal["best", "last"],
) -> dict[str, object]:
    required = {
        "highest_gauc",
        "selected_epoch",
        "selected_gauc",
        "selected_ndcg",
        "selected_hr",
        "patience_used",
    }
    if set(stopping_state) != required:
        raise ArtifactIntegrityError("checkpoint stopping state fields are incomplete")
    for name in ("highest_gauc", "selected_gauc", "selected_ndcg", "selected_hr"):
        value = stopping_state[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ArtifactIntegrityError("checkpoint stopping state contains invalid metrics")
        if float(value) != -float("inf") and not math.isfinite(float(value)):
            raise ArtifactIntegrityError("checkpoint stopping state contains invalid metrics")
    selected_epoch_value = stopping_state["selected_epoch"]
    if (
        isinstance(selected_epoch_value, bool)
        or not isinstance(selected_epoch_value, int)
        or selected_epoch_value < 0
    ):
        raise ArtifactIntegrityError("checkpoint selected epoch must be a non-negative integer")
    patience_value = stopping_state["patience_used"]
    if (
        isinstance(patience_value, bool)
        or not isinstance(patience_value, int)
        or patience_value < 0
    ):
        raise ArtifactIntegrityError("checkpoint patience counter must be a non-negative integer")
    selected_epoch = selected_epoch_value
    if selected_epoch > epoch:
        raise ArtifactIntegrityError("checkpoint selected epoch is outside checkpoint epoch")
    if checkpoint_kind == "best" and selected_epoch != epoch:
        raise ArtifactIntegrityError("best checkpoint must point to the selected epoch")
    return dict(stopping_state)


def _load_checkpoint_manifest(path: Path) -> CheckpointManifest:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    try:
        return CheckpointManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("checkpoint manifest cannot be read") from error


class CheckpointManager:
    @staticmethod
    def save(
        path: Path,
        *,
        model: nn.Module,
        optimizer: Optimizer,
        scheduler: Any,
        epoch: int,
        metrics: Mapping[str, float],
        stopping_state: Mapping[str, object],
        checkpoint_kind: Literal["best", "last"],
        lineage: ArtifactLineageInput,
        training_signature_sha256: str,
        comparison_signature_sha256: str,
        training_variant: TrainingVariant,
        model_schema_version: str,
        run_id: str,
        scaler: Any,
    ) -> CheckpointManifest:
        if checkpoint_kind not in {"best", "last"}:
            raise ArtifactIntegrityError("checkpoint kind must be best or last")
        if model_schema_version != MODEL_SCHEMA_VERSION:
            raise ArtifactIntegrityError("checkpoint schema must be v5.0.0")
        required_metrics = {"val_gauc", "val_ndcg_at_k", "val_hr_at_k", "train_loss"}
        if set(metrics) != required_metrics or any(
            not isinstance(metrics[name], (int, float)) or not math.isfinite(float(metrics[name]))
            for name in required_metrics
        ):
            raise ArtifactIntegrityError("checkpoint requires complete finite validation metrics")
        stopping_state = _validate_stopping_state(
            stopping_state, epoch=epoch, checkpoint_kind=checkpoint_kind
        )
        try:
            lineage_mapping = normalize_artifact_lineage(lineage)
        except ValueError as error:
            raise ArtifactIntegrityError("checkpoint lineage is invalid") from error
        if set(lineage_mapping) not in (
            {"snapshot", "embedding", "rules"},
            {
                "snapshot",
                "embedding",
                "rules",
                "benchmark_spec",
                "semantic_cohort",
                "order_metadata",
            },
        ):
            raise ArtifactIntegrityError("checkpoint lineage is incomplete")
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": MODEL_SCHEMA_VERSION,
            "run_id": run_id,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict() if scheduler is not None else None,
            "scaler": scaler.state_dict() if scaler is not None else None,
            "epoch": epoch,
            "metrics": dict(metrics),
            "lineage": lineage_mapping,
            "training_signature_sha256": training_signature_sha256,
            "comparison_signature_sha256": comparison_signature_sha256,
            "training_variant": training_variant.value,
            "model_schema_version": model_schema_version,
            "checkpoint_kind": checkpoint_kind,
            "rng": {
                "python": random.getstate(),
                "numpy": np.random.get_state(),
                "torch": torch.get_rng_state(),
                "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            },
            "stopping_state": dict(stopping_state),
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        manifest_temp: Path | None = None
        try:
            torch.save(state, temporary)
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            checksum = _sha256(temporary)
            manifest = CheckpointManifest(
                schema_version=model_schema_version,
                artifact_id=path.stem,
                content_sha256=checksum,
                parent_sha256=lineage_mapping,
                run_id=run_id,
                snapshot_sha256=lineage_mapping["snapshot"],
                embedding_sha256=lineage_mapping["embedding"],
                rule_sha256=lineage_mapping["rules"],
                training_signature_sha256=training_signature_sha256,
                comparison_signature_sha256=comparison_signature_sha256,
                training_variant=training_variant,
                model_schema_version=model_schema_version,
                best_epoch=epoch,
                best_val_gauc=float(metrics["val_gauc"]),
                best_val_ndcg_at_k=float(metrics["val_ndcg_at_k"]),
                best_val_hr_at_k=float(metrics["val_hr_at_k"]),
                checkpoint_kind=checkpoint_kind,
                benchmark_spec_sha256=lineage_mapping.get("benchmark_spec"),
                semantic_cohort_sha256=lineage_mapping.get("semantic_cohort"),
                order_metadata_sha256=lineage_mapping.get("order_metadata"),
            )
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            manifest_temp = manifest_path.with_name(f".{manifest_path.name}.tmp")
            with manifest_temp.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest.model_dump(mode="json"), handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.replace(manifest_temp, manifest_path)
        finally:
            temporary.unlink(missing_ok=True)
            if manifest_temp is not None:
                manifest_temp.unlink(missing_ok=True)
        return manifest

    @staticmethod
    def load(
        path: Path,
        *,
        model: nn.Module,
        optimizer: Optimizer | None = None,
        scheduler: Any = None,
        scaler: Any = None,
        expected_lineage: ArtifactLineageInput | None = None,
        expected_training_signature: str | None = None,
        expected_comparison_signature: str | None = None,
        expected_training_variant: TrainingVariant | None = None,
        expected_checkpoint_kind: str | None = None,
        expected_run_id: str | None = None,
        expected_model_schema_version: str = MODEL_SCHEMA_VERSION,
        require_resume_state: bool = False,
        restore_rng: bool = False,
    ) -> dict[str, Any]:
        manifest_path = path.with_suffix(path.suffix + ".manifest.json")
        if not manifest_path.is_file():
            raise ArtifactIntegrityError(f"checkpoint manifest missing: {manifest_path}")
        if not path.is_file():
            raise ArtifactIntegrityError(f"checkpoint payload missing: {path}")
        manifest = _load_checkpoint_manifest(path)
        if manifest.model_schema_version != expected_model_schema_version:
            raise ArtifactIntegrityError(
                "checkpoint schema mismatch: "
                f"expected {expected_model_schema_version}, got {manifest.model_schema_version}"
            )
        if _sha256(path) != manifest.content_sha256:
            raise ArtifactIntegrityError("checkpoint checksum mismatch")
        if expected_lineage is not None:
            try:
                expected_lineage_mapping = normalize_artifact_lineage(expected_lineage)
            except ValueError as error:
                raise ArtifactIntegrityError("expected checkpoint lineage is invalid") from error
        else:
            expected_lineage_mapping = None
        if (
            expected_lineage_mapping is not None
            and manifest.parent_sha256 != expected_lineage_mapping
        ):
            raise ArtifactIntegrityError("checkpoint lineage mismatch")
        if (
            expected_training_signature is not None
            and manifest.training_signature_sha256 != expected_training_signature
        ):
            raise ArtifactIntegrityError("checkpoint training signature mismatch")
        if (
            expected_comparison_signature is not None
            and manifest.comparison_signature_sha256 != expected_comparison_signature
        ):
            raise ArtifactIntegrityError("checkpoint comparison signature mismatch")
        if (
            expected_training_variant is not None
            and manifest.training_variant is not expected_training_variant
        ):
            raise ArtifactIntegrityError("checkpoint training variant mismatch")
        try:
            loaded_state = torch.load(path, map_location="cpu", weights_only=False)
        except (
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            EOFError,
            pickle.UnpicklingError,
        ) as error:
            raise ArtifactIntegrityError("checkpoint payload cannot be deserialized") from error
        if not isinstance(loaded_state, dict):
            raise ArtifactIntegrityError("checkpoint payload must be a mapping")
        state: dict[str, Any] = loaded_state
        if state.get("schema_version") != manifest.schema_version:
            raise ArtifactIntegrityError("checkpoint artifact schema state mismatch")
        if state.get("training_signature_sha256") != manifest.training_signature_sha256:
            raise ArtifactIntegrityError("checkpoint training signature state mismatch")
        if state.get("comparison_signature_sha256") != manifest.comparison_signature_sha256:
            raise ArtifactIntegrityError("checkpoint comparison signature state mismatch")
        if state.get("training_variant") != manifest.training_variant.value:
            raise ArtifactIntegrityError("checkpoint training variant state mismatch")
        if state.get("model_schema_version") != manifest.model_schema_version:
            raise ArtifactIntegrityError("checkpoint model schema state mismatch")
        if state.get("run_id") != manifest.run_id:
            raise ArtifactIntegrityError("checkpoint run ID state mismatch")
        if state.get("checkpoint_kind") != manifest.checkpoint_kind:
            raise ArtifactIntegrityError("checkpoint kind state mismatch")
        if state.get("epoch") != manifest.best_epoch:
            raise ArtifactIntegrityError("checkpoint epoch state mismatch")
        if (
            expected_checkpoint_kind is not None
            and manifest.checkpoint_kind != expected_checkpoint_kind
        ):
            raise ArtifactIntegrityError("checkpoint kind mismatch")
        if expected_run_id is not None and manifest.run_id != expected_run_id:
            raise ArtifactIntegrityError("checkpoint run ID mismatch")
        if state.get("lineage") != manifest.parent_sha256:
            raise ArtifactIntegrityError("checkpoint lineage state mismatch")
        payload_metrics = state.get("metrics")
        required_metric_keys = {"val_gauc", "val_ndcg_at_k", "val_hr_at_k", "train_loss"}
        expected_metrics = {
            "val_gauc": manifest.best_val_gauc,
            "val_ndcg_at_k": manifest.best_val_ndcg_at_k,
            "val_hr_at_k": manifest.best_val_hr_at_k,
        }
        if (
            not isinstance(payload_metrics, dict)
            or set(payload_metrics) != required_metric_keys
            or any(
                not isinstance(payload_metrics[name], (int, float))
                or not math.isfinite(float(payload_metrics[name]))
                for name in required_metric_keys
            )
            or any(payload_metrics.get(name) != value for name, value in expected_metrics.items())
        ):
            raise ArtifactIntegrityError("checkpoint metrics state mismatch")
        stopping_state = state.get("stopping_state")
        if not isinstance(stopping_state, Mapping):
            raise ArtifactIntegrityError("checkpoint stopping state is missing")
        _validate_stopping_state(
            stopping_state,
            epoch=manifest.best_epoch,
            checkpoint_kind=manifest.checkpoint_kind,
        )
        rng = state.get("rng")
        resume_sections_missing = (
            state.get("optimizer") is None
            or state.get("scheduler") is None
            or state.get("scaler") is None
        )
        rng_state_missing = not isinstance(rng, dict) or not {
            "python",
            "numpy",
            "torch",
            "cuda",
        } <= set(rng)
        if (require_resume_state or restore_rng) and resume_sections_missing:
            raise ArtifactIntegrityError(
                "resume requires optimizer, scheduler, scaler, RNG, and stopping state"
            )
        if (require_resume_state or restore_rng) and rng_state_missing:
            raise ArtifactIntegrityError("resume RNG state is missing or incomplete")
        if restore_rng and (optimizer is None or scheduler is None or scaler is None):
            raise ArtifactIntegrityError(
                "resume restore requires optimizer, scheduler, and scaler instances"
            )
        try:
            model.load_state_dict(state["model"], strict=True)
        except (KeyError, RuntimeError, TypeError) as error:
            raise ArtifactIntegrityError(
                "checkpoint model payload cannot be strict-loaded"
            ) from error
        if optimizer is not None:
            if state.get("optimizer") is None:
                raise ArtifactIntegrityError("checkpoint optimizer payload is missing")
            try:
                optimizer.load_state_dict(state["optimizer"])
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as error:
                raise ArtifactIntegrityError("checkpoint optimizer payload is invalid") from error
        if scheduler is not None:
            if state.get("scheduler") is None:
                raise ArtifactIntegrityError("checkpoint scheduler payload is missing")
            try:
                scheduler.load_state_dict(state["scheduler"])
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as error:
                raise ArtifactIntegrityError("checkpoint scheduler payload is invalid") from error
        if scaler is not None:
            if state.get("scaler") is None:
                raise ArtifactIntegrityError("checkpoint scaler payload is missing")
            try:
                scaler.load_state_dict(state["scaler"])
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as error:
                raise ArtifactIntegrityError("checkpoint scaler payload is invalid") from error
        if restore_rng:
            rng = state.get("rng")
            if not isinstance(rng, dict) or not {"python", "numpy", "torch", "cuda"} <= set(rng):
                raise ArtifactIntegrityError("checkpoint RNG state is missing")
            try:
                random.setstate(rng["python"])
                np.random.set_state(rng["numpy"])
                torch.set_rng_state(rng["torch"])
                if torch.cuda.is_available() and rng["cuda"]:
                    torch.cuda.set_rng_state_all(rng["cuda"])
            except (TypeError, ValueError, RuntimeError) as error:
                raise ArtifactIntegrityError("checkpoint RNG state is invalid") from error
        return state
