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

from ai_service.contracts import ModelBundleManifest
from ai_service.errors import ArtifactIntegrityError

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
        checkpoint_sha256: str,
        parity: ParityReport,
        victory_matrix_sha256: str = "",
    ) -> BundleArtifact:
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
            files = {path.name: file_sha256(path) for path in temporary.iterdir() if path.is_file()}
            manifest = ModelBundleManifest(
                artifact_id=bundle_id,
                bundle_id=bundle_id,
                run_id=run_id,
                store_id=snapshot.manifest.store_id,
                content_sha256=_aggregate(files),
                parent_sha256={
                    "snapshot": snapshot.manifest.content_sha256,
                    "checkpoint": checkpoint_sha256,
                },
                files=files,
                item_count=snapshot.manifest.num_items,
                embedding_dim=self.settings.model.item_emb_dim,
                model_version="5.0.0",
                parity_max_abs=parity.max_abs_error,
                ranking_parity_users=parity.ranking_parity_users,
                kernel_latency_ms=parity.kernel_latency_ms,
                benchmark_hardware=parity.hardware,
                victory_matrix_sha256=victory_matrix_sha256,
            )
            (temporary / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return verify_bundle(destination)


def verify_bundle(path: Path) -> BundleArtifact:
    manifest = ModelBundleManifest.model_validate_json(
        (path / "manifest.json").read_text(encoding="utf-8")
    )
    actual: dict[str, str] = {}
    for name, expected in manifest.files.items():
        candidate = path / name
        if not candidate.is_file():
            raise ArtifactIntegrityError(f"bundle file missing: {name}")
        actual[name] = file_sha256(candidate)
        if actual[name] != expected:
            raise ArtifactIntegrityError(f"bundle checksum mismatch: {name}")
    if _aggregate(actual) != manifest.content_sha256:
        raise ArtifactIntegrityError("bundle aggregate checksum mismatch")
    return BundleArtifact(path=path, manifest=manifest)
