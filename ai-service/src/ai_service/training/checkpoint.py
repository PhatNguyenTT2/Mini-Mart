"""Atomic, resumable training checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.optim import Optimizer

from ai_service.contracts import CheckpointManifest
from ai_service.errors import ArtifactIntegrityError


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CheckpointManager:
    @staticmethod
    def save(
        path: Path,
        *,
        model: nn.Module,
        optimizer: Optimizer,
        scheduler: Any,
        epoch: int,
        metrics: dict[str, float],
        lineage: dict[str, str],
        training_signature_sha256: str,
        model_schema_version: str,
        run_id: str,
        scaler: Any = None,
    ) -> CheckpointManifest:
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": "3.0.0",
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict() if scheduler is not None else None,
            "scaler": scaler.state_dict() if scaler is not None else None,
            "epoch": epoch,
            "metrics": metrics,
            "lineage": lineage,
            "training_signature_sha256": training_signature_sha256,
            "model_schema_version": model_schema_version,
            "rng": {
                "python": random.getstate(),
                "numpy": np.random.get_state(),
                "torch": torch.get_rng_state(),
                "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            },
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            torch.save(state, temporary)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        checksum = _sha256(path)
        manifest = CheckpointManifest(
            artifact_id=path.stem,
            content_sha256=checksum,
            parent_sha256=lineage,
            run_id=run_id,
            snapshot_sha256=lineage["snapshot"],
            embedding_sha256=lineage["embedding"],
            rule_sha256=lineage["rules"],
            training_signature_sha256=training_signature_sha256,
            model_schema_version=model_schema_version,
            best_epoch=epoch,
            best_val_gauc=metrics["val_gauc"],
            best_val_ndcg_at_k=metrics.get("val_ndcg_at_k", 0.0),
        )
        manifest_path = path.with_suffix(path.suffix + ".manifest.json")
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
        return manifest

    @staticmethod
    def load(
        path: Path,
        *,
        model: nn.Module,
        optimizer: Optimizer | None = None,
        scheduler: Any = None,
        scaler: Any = None,
        expected_lineage: dict[str, str] | None = None,
        expected_training_signature: str | None = None,
        expected_model_schema_version: str | None = None,
        restore_rng: bool = False,
    ) -> dict[str, Any]:
        manifest = CheckpointManifest.model_validate_json(
            path.with_suffix(path.suffix + ".manifest.json").read_text(encoding="utf-8")
        )
        if _sha256(path) != manifest.content_sha256:
            raise ArtifactIntegrityError("checkpoint checksum mismatch")
        if expected_lineage and manifest.parent_sha256 != expected_lineage:
            raise ArtifactIntegrityError("checkpoint lineage mismatch")
        if (
            expected_training_signature is not None
            and manifest.training_signature_sha256 != expected_training_signature
        ):
            raise ArtifactIntegrityError("checkpoint training signature mismatch")
        if (
            expected_model_schema_version is not None
            and manifest.model_schema_version != expected_model_schema_version
        ):
            raise ArtifactIntegrityError("checkpoint model schema mismatch")
        state: dict[str, Any] = torch.load(path, map_location="cpu", weights_only=False)
        if state.get("training_signature_sha256") != manifest.training_signature_sha256:
            raise ArtifactIntegrityError("checkpoint training signature state mismatch")
        if state.get("model_schema_version") != manifest.model_schema_version:
            raise ArtifactIntegrityError("checkpoint model schema state mismatch")
        model.load_state_dict(state["model"], strict=True)
        if optimizer is not None:
            optimizer.load_state_dict(state["optimizer"])
        if scheduler is not None and state["scheduler"] is not None:
            scheduler.load_state_dict(state["scheduler"])
        if scaler is not None and state.get("scaler") is not None:
            scaler.load_state_dict(state["scaler"])
        if restore_rng:
            rng = state["rng"]
            random.setstate(rng["python"])
            np.random.set_state(rng["numpy"])
            torch.set_rng_state(rng["torch"])
            if torch.cuda.is_available() and rng["cuda"]:
                torch.cuda.set_rng_state_all(rng["cuda"])
        return state
