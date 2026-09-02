"""Hash-bound NumPy checkpoints for the lightweight research trainer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, cast

import numpy as np

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json, sha256_bytes
from ai_service_v2.models.proposed import ItemFeatureMatrix, TrainedTwoTower


@dataclass(frozen=True)
class CheckpointManifest:
    schema_version: str
    run_id: str
    model_id: str
    seed: int
    checkpoint_rule: str
    checkpoint_sha256: str
    arrays: dict[str, dict[str, Any]]
    feature_content_sha256: str
    descriptor: dict[str, Any]

    _FIELDS: ClassVar[set[str]] = {
        "schema_version",
        "run_id",
        "model_id",
        "seed",
        "checkpoint_rule",
        "checkpoint_sha256",
        "arrays",
        "feature_content_sha256",
        "descriptor",
    }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> CheckpointManifest:
        if set(value) != cls._FIELDS:
            raise IntegrityError("checkpoint manifest fields do not match schema")
        required_strings = (
            "schema_version",
            "run_id",
            "model_id",
            "checkpoint_rule",
            "checkpoint_sha256",
            "feature_content_sha256",
        )
        for name in required_strings:
            if not isinstance(value[name], str) or not value[name]:
                raise IntegrityError(f"checkpoint manifest field is invalid: {name}")
        seed = value["seed"]
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise IntegrityError("checkpoint seed is invalid")
        if not _is_sha256(value["checkpoint_sha256"]) or not _is_sha256(
            value["feature_content_sha256"]
        ):
            raise IntegrityError("checkpoint manifest contains an invalid hash")
        arrays = value["arrays"]
        descriptor = value["descriptor"]
        if not isinstance(arrays, dict) or not isinstance(descriptor, dict):
            raise IntegrityError("checkpoint arrays and descriptor must be objects")
        return cls(
            schema_version=value["schema_version"],
            run_id=value["run_id"],
            model_id=value["model_id"],
            seed=seed,
            checkpoint_rule=value["checkpoint_rule"],
            checkpoint_sha256=value["checkpoint_sha256"],
            arrays=arrays,
            feature_content_sha256=value["feature_content_sha256"],
            descriptor=descriptor,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "model_id": self.model_id,
            "seed": self.seed,
            "checkpoint_rule": self.checkpoint_rule,
            "checkpoint_sha256": self.checkpoint_sha256,
            "arrays": self.arrays,
            "feature_content_sha256": self.feature_content_sha256,
            "descriptor": self.descriptor,
        }


def save_checkpoint(
    model: TrainedTwoTower,
    *,
    root: Path,
    run_id: str,
    seed: int,
    checkpoint_rule: str = "final_training_state_after_fixed_epochs",
) -> CheckpointManifest:
    """Write one immutable checkpoint directory; refuse existing roots."""

    if root.exists():
        raise IntegrityError(f"checkpoint root already exists: {root}")
    root.mkdir(parents=True)
    arrays = model.parameter_arrays()
    checkpoint_path = root / "checkpoint.npz"
    try:
        with checkpoint_path.open("wb") as stream:
            np.savez(stream, **cast(Any, arrays))
        payload = checkpoint_path.read_bytes()
    except OSError as error:
        raise IntegrityError(f"could not write checkpoint: {checkpoint_path}") from error
    array_manifest = {
        name: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for name, value in arrays.items()
    }
    manifest = CheckpointManifest(
        schema_version="checkpoint/1.0",
        run_id=run_id,
        model_id=model.describe().model_id,
        seed=seed,
        checkpoint_rule=checkpoint_rule,
        checkpoint_sha256=sha256_bytes(payload),
        arrays=array_manifest,
        feature_content_sha256=model.features.content_sha256,
        descriptor=model.describe().to_mapping(),
    )
    try:
        (root / "manifest.json").write_bytes(canonical_json_bytes(manifest.to_mapping()) + b"\n")
    except OSError as error:
        manifest_path = root / "manifest.json"
        raise IntegrityError(f"could not write checkpoint manifest: {manifest_path}") from error
    return manifest


def load_checkpoint(
    root: Path,
    *,
    snapshot: Snapshot,
    features: ItemFeatureMatrix,
) -> tuple[TrainedTwoTower, CheckpointManifest]:
    """Verify and restore a checkpoint without accepting partial arrays."""

    manifest_path = root / "manifest.json"
    checkpoint_path = root / "checkpoint.npz"
    manifest_data = load_strict_json(manifest_path)
    manifest = CheckpointManifest.from_mapping(manifest_data)
    try:
        actual_files = {path.name for path in root.iterdir() if path.is_file()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect checkpoint root: {root}") from error
    if actual_files != {"manifest.json", "checkpoint.npz"}:
        raise IntegrityError("checkpoint contains an unexpected or missing file")
    try:
        payload = checkpoint_path.read_bytes()
        with np.load(checkpoint_path, allow_pickle=False) as loaded:
            arrays = {name: np.asarray(loaded[name]) for name in loaded.files}
    except (OSError, ValueError) as error:
        raise IntegrityError("could not read checkpoint payload") from error
    if sha256_bytes(payload) != manifest.checkpoint_sha256:
        raise IntegrityError("checkpoint payload hash mismatch")
    if manifest.feature_content_sha256 != features.content_sha256:
        raise IntegrityError("checkpoint feature hash does not match supplied features")
    descriptor = ModelDescriptor.from_mapping(manifest.descriptor)
    if manifest.model_id != descriptor.model_id:
        raise IntegrityError("checkpoint model ID does not match descriptor")
    if manifest.schema_version != "checkpoint/1.0":
        raise IntegrityError("unsupported checkpoint schema")
    actual_arrays = set(arrays)
    if actual_arrays != set(manifest.arrays):
        raise IntegrityError("checkpoint array names do not match manifest")
    for name, array in arrays.items():
        declaration = manifest.arrays[name]
        if not isinstance(declaration, dict) or set(declaration) != {"shape", "dtype"}:
            raise IntegrityError(f"checkpoint array declaration is invalid: {name}")
        shape = declaration["shape"]
        dtype = declaration["dtype"]
        if (
            not isinstance(shape, list)
            or any(isinstance(dim, bool) or not isinstance(dim, int) or dim < 0 for dim in shape)
            or not isinstance(dtype, str)
            or str(array.dtype) != dtype
            or list(array.shape) != shape
            or not np.isfinite(array).all()
        ):
            raise IntegrityError(f"checkpoint array declaration does not match payload: {name}")
    model = TrainedTwoTower.from_parameter_arrays(snapshot, features, arrays, descriptor)
    return model, manifest


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = ["CheckpointManifest", "load_checkpoint", "save_checkpoint"]
