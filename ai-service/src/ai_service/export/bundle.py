"""Atomic serving bundle publication and verification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import ModelBundleManifest, TrainingVariant
from ai_service.errors import ArtifactIntegrityError, ConfigurationError

if TYPE_CHECKING:
    from ai_service.config import Settings
    from ai_service.data.rules import RuleStore
    from ai_service.data.snapshot import Snapshot
    from ai_service.export.parity import ParityReport


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _aggregate(files: dict[str, str]) -> str:
    return hashlib.sha256(
        "\n".join(f"{name}\t{checksum}" for name, checksum in sorted(files.items())).encode()
    ).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _load_bundle_manifest(path: Path) -> ModelBundleManifest:
    try:
        return ModelBundleManifest.model_validate_json(
            (path / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("bundle manifest cannot be read") from error


@dataclass(frozen=True)
class BundleArtifact:
    path: Path
    manifest: ModelBundleManifest


class BundlePublisher:
    def __init__(self, settings: Settings):
        self.settings = settings

    def publish(
        self,
        *,
        bundle_id: str,
        run_id: str,
        snapshot: Snapshot,
        rule_store: RuleStore,
        ranker_path: Path,
        item_vectors: np.ndarray,
        user_profile_vectors: np.ndarray,
        embedding_sha256: str,
        rule_sha256: str,
        checkpoint_sha256: str,
        comparison_signature_sha256: str,
        parity: ParityReport,
        victory_matrix_sha256: str,
    ) -> BundleArtifact:
        if len(victory_matrix_sha256) != 64 or set(victory_matrix_sha256) == {"0"}:
            raise ArtifactIntegrityError(
                "bundle publication requires a non-placeholder victory matrix hash"
            )
        vectors = np.asarray(item_vectors, dtype=np.float32)
        expected = (snapshot.manifest.num_items, self.settings.model.item_emb_dim)
        if vectors.shape != expected or not np.isfinite(vectors).all():
            raise ArtifactIntegrityError("item vector cache has invalid shape or values")
        profiles = np.asarray(user_profile_vectors, dtype=np.float32)
        profile_expected = (
            snapshot.manifest.num_users + 1,
            self.settings.model.item_emb_dim,
        )
        if profiles.shape != profile_expected or not np.isfinite(profiles).all():
            raise ArtifactIntegrityError("user profile cache has invalid shape or values")
        if np.any(profiles[0] != 0):
            raise ArtifactIntegrityError("unknown-user profile must be zero")
        root = self.settings.data.artifact_root.resolve() / "bundles"
        root.mkdir(parents=True, exist_ok=True)
        destination = root / bundle_id
        if destination.exists():
            raise ArtifactIntegrityError(f"immutable bundle already exists: {destination}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{bundle_id}-", dir=root))
        try:
            shutil.copy2(ranker_path, temporary / "ranker.onnx")
            np.save(temporary / "item_vectors.npy", vectors)
            np.save(temporary / "user_profile_vectors.npy", profiles)
            np.savez_compressed(
                temporary / "rules.npz",
                crow_indices=rule_store.crow_indices.numpy(),
                col_indices=rule_store.col_indices.numpy(),
                values=rule_store.values.numpy(),
                features=rule_store.features.numpy(),
                raw_lifts=rule_store.raw_lifts.numpy(),
                supports=rule_store.supports.numpy(),
                confidences=rule_store.confidences.numpy(),
                counts=rule_store.counts.numpy(),
                q99_log_lift=np.asarray([rule_store.q99_log_lift], dtype=np.float32),
            )
            (temporary / "mappings.json").write_text(
                json.dumps(
                    {
                        "product_map": snapshot.product_map,
                        "user_map": snapshot.user_map,
                        "persona_map": snapshot.persona_map,
                        "cold_item_ids": snapshot.cold_item_ids,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            (temporary / "normalization.json").write_text(
                json.dumps(
                    {
                        "tau": self.settings.model.tau,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            (temporary / "resolved-config.json").write_text(
                json.dumps(self.settings.resolved_document(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            (temporary / "training-signature.sha256").write_text(
                self.settings.training_signature_sha256() + "\n",
                encoding="ascii",
            )
            for path in temporary.iterdir():
                if path.is_file():
                    _fsync_file(path)
            files = {path.name: file_sha256(path) for path in temporary.iterdir() if path.is_file()}
            manifest = ModelBundleManifest(
                schema_version="5.0.0",
                artifact_id=bundle_id,
                bundle_id=bundle_id,
                run_id=run_id,
                store_id=snapshot.manifest.store_id,
                content_sha256=_aggregate(files),
                parent_sha256={
                    "snapshot": snapshot.manifest.content_sha256,
                    "embedding": embedding_sha256,
                    "rules": rule_sha256,
                    "checkpoint": checkpoint_sha256,
                    "victory_matrix": victory_matrix_sha256,
                },
                files=files,
                item_count=snapshot.manifest.num_items,
                embedding_dim=self.settings.model.item_emb_dim,
                model_version="5.0.0",
                parity_max_abs=parity.max_abs_error,
                ranking_parity_users=parity.ranking_parity_users,
                kernel_latency_ms=parity.kernel_latency_ms,
                benchmark_hardware=parity.hardware,
                training_variant=TrainingVariant.HYBRID,
                comparison_signature_sha256=comparison_signature_sha256,
                victory_matrix_sha256=victory_matrix_sha256,
            )
            (temporary / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            _fsync_file(temporary / "manifest.json")
            # Verify before the directory becomes immutable.  A malformed
            # generated bundle must never be published as a permanent failure.
            verify_bundle(temporary)
            if destination.exists():
                raise ArtifactIntegrityError(f"immutable bundle already exists: {destination}")
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return verify_bundle(destination)


def verify_bundle(path: Path) -> BundleArtifact:
    path = path.resolve()
    if not path.is_dir():
        raise ArtifactIntegrityError(f"bundle directory does not exist: {path}")
    manifest = _load_bundle_manifest(path)
    required_files = {
        "ranker.onnx",
        "item_vectors.npy",
        "user_profile_vectors.npy",
        "rules.npz",
        "mappings.json",
        "normalization.json",
        "resolved-config.json",
        "training-signature.sha256",
    }
    directory_entries = {entry.name for entry in path.iterdir()}
    if directory_entries != required_files | {"manifest.json"}:
        raise ArtifactIntegrityError("bundle directory contains unexpected files")
    if set(manifest.files) != required_files:
        raise ArtifactIntegrityError("bundle manifest does not contain the exact file allowlist")
    actual: dict[str, str] = {}
    for name, expected in manifest.files.items():
        candidate_name = Path(name)
        if (
            candidate_name.is_absolute()
            or candidate_name.name != name
            or ".." in candidate_name.parts
        ):
            raise ArtifactIntegrityError(f"bundle file name is unsafe: {name}")
        candidate = path / name
        if not candidate.is_file():
            raise ArtifactIntegrityError(f"bundle file missing: {name}")
        actual[name] = file_sha256(candidate)
        if actual[name] != expected:
            raise ArtifactIntegrityError(f"bundle checksum mismatch: {name}")
    if _aggregate(actual) != manifest.content_sha256:
        raise ArtifactIntegrityError("bundle aggregate checksum mismatch")
    if set(manifest.victory_matrix_sha256) == {"0"}:
        raise ArtifactIntegrityError("bundle has a placeholder victory matrix hash")
    if manifest.parent_sha256.get("victory_matrix") != manifest.victory_matrix_sha256:
        raise ArtifactIntegrityError("bundle victory matrix lineage mismatch")
    if set(manifest.parent_sha256) != {
        "snapshot",
        "embedding",
        "rules",
        "checkpoint",
        "victory_matrix",
    }:
        raise ArtifactIntegrityError("bundle parent lineage is incomplete")
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in manifest.parent_sha256.values()
    ):
        raise ArtifactIntegrityError("bundle parent lineage contains an invalid SHA")
    try:
        training_signature = (
            (path / "training-signature.sha256").read_text(encoding="ascii").strip()
        )
    except (OSError, UnicodeError) as error:
        raise ArtifactIntegrityError("bundle training signature cannot be read") from error
    if len(training_signature) != 64 or any(
        character not in "0123456789abcdef" for character in training_signature
    ):
        raise ArtifactIntegrityError("bundle training signature is invalid")
    try:
        resolved_document = json.loads((path / "resolved-config.json").read_text(encoding="utf-8"))
        resolved_payload = dict(resolved_document)
        resolved_payload.pop("schema_version", None)
        resolved_settings = Settings.from_resolved_document(resolved_payload)
    except (OSError, TypeError, ValueError, ConfigurationError) as error:
        raise ArtifactIntegrityError("bundle resolved configuration is invalid") from error
    if resolved_document.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ArtifactIntegrityError("bundle resolved configuration schema mismatch")
    if resolved_settings.train.training_variant is not TrainingVariant.HYBRID:
        raise ArtifactIntegrityError("bundle resolved configuration is not Hybrid")
    if resolved_settings.training_signature_sha256() != training_signature:
        raise ArtifactIntegrityError("bundle training signature does not match resolved config")
    if resolved_settings.comparison_signature_sha256() != manifest.comparison_signature_sha256:
        raise ArtifactIntegrityError("bundle comparison signature does not match resolved config")
    if not np.isfinite(manifest.parity_max_abs) or manifest.parity_max_abs > 1e-5:
        raise ArtifactIntegrityError("bundle ONNX parity exceeds the release tolerance")
    try:
        item_vectors = np.load(path / "item_vectors.npy", allow_pickle=False)
        profiles = np.load(path / "user_profile_vectors.npy", allow_pickle=False)
        mappings = json.loads((path / "mappings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("bundle numerical artifacts cannot be loaded") from error
    if (
        item_vectors.shape != (manifest.item_count, manifest.embedding_dim)
        or item_vectors.dtype != np.float32
        or not np.isfinite(item_vectors).all()
    ):
        raise ArtifactIntegrityError("bundle item vector cache has invalid shape or values")
    if not isinstance(mappings, dict):
        raise ArtifactIntegrityError("bundle mappings must be an object")
    product_map = mappings.get("product_map", {})
    user_map = mappings.get("user_map", {})
    try:
        product_indices = sorted(int(value) for value in product_map.values())
    except (AttributeError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("bundle product mapping does not match item count") from error
    if (
        not isinstance(product_map, dict)
        or len(product_map) != manifest.item_count
        or product_indices != list(range(manifest.item_count))
    ):
        raise ArtifactIntegrityError("bundle product mapping does not match item count")
    try:
        user_indices = sorted(int(value) for value in user_map.values())
    except (AttributeError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError(
            "bundle user profile cache has invalid shape or values"
        ) from error
    if (
        not isinstance(user_map, dict)
        or user_indices != list(range(1, len(user_map) + 1))
        or profiles.ndim != 2
        or profiles.shape[0] != len(user_map) + 1
        or profiles.shape[1] != manifest.embedding_dim
        or profiles.dtype != np.float32
        or not np.isfinite(profiles).all()
        or not np.allclose(profiles[0], 0.0)
    ):
        raise ArtifactIntegrityError("bundle user profile cache has invalid shape or values")
    try:
        rules = np.load(path / "rules.npz", allow_pickle=False)
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("bundle rule cache cannot be loaded") from error
    with rules:
        required_rule_arrays = {
            "crow_indices",
            "col_indices",
            "values",
            "features",
            "raw_lifts",
            "supports",
            "confidences",
            "counts",
            "q99_log_lift",
        }
        if set(rules.files) != required_rule_arrays:
            raise ArtifactIntegrityError("bundle rule cache is incomplete")
        crow = rules["crow_indices"]
        cols = rules["col_indices"]
        nnz = len(cols)
        if len(crow) != manifest.item_count + 1:
            raise ArtifactIntegrityError("bundle rule CSR row pointer length is invalid")
        if (
            crow.dtype != np.int64
            or cols.dtype != np.int64
            or rules["values"].dtype != np.float32
            or rules["features"].dtype != np.float32
            or rules["raw_lifts"].dtype != np.float32
            or rules["supports"].dtype != np.float32
            or rules["confidences"].dtype != np.float32
            or rules["counts"].dtype != np.int64
            or rules["q99_log_lift"].dtype != np.float32
            or any(
                len(rules[name]) != nnz
                for name in (
                    "values",
                    "features",
                    "raw_lifts",
                    "supports",
                    "confidences",
                    "counts",
                )
            )
            or rules["features"].shape != (nnz, 3)
            or rules["q99_log_lift"].shape != (1,)
            or not np.isfinite(rules["q99_log_lift"]).all()
            or float(rules["q99_log_lift"][0]) <= 0
            or not np.isfinite(rules["values"]).all()
            or not np.isfinite(rules["features"]).all()
            or not np.isfinite(rules["raw_lifts"]).all()
            or not np.isfinite(rules["supports"]).all()
            or not np.isfinite(rules["confidences"]).all()
            or np.any(rules["raw_lifts"] < 0)
            or np.any(rules["supports"] < 0)
            or np.any(rules["supports"] > 1)
            or np.any(rules["confidences"] < 0)
            or np.any(rules["confidences"] > 1)
            or np.any(rules["counts"] < 1)
        ):
            raise ArtifactIntegrityError("bundle rule arrays have invalid shape or dtype")
        if (
            crow[0] != 0
            or np.any(np.diff(crow) < 0)
            or crow[-1] != nnz
            or np.any(cols < 0)
            or np.any(cols >= manifest.item_count)
        ):
            raise ArtifactIntegrityError("bundle rule CSR bounds are invalid")
    return BundleArtifact(path=path, manifest=manifest)
