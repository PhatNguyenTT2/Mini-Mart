"""SBERT artifact construction with explicit real and mock adapters."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import EmbeddingManifest, EmbeddingSource
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError


class TextEncoder(Protocol):
    model_name: str
    revision: str

    def encode(self, texts: list[str]) -> np.ndarray: ...


class RealSBERTEncoder:
    model_name = "keepitreal/vietnamese-sbert"
    pinned_revision = "a9467ef2ef47caa6448edeabfd8e5e5ce0fa2a23"

    def __init__(self, model_name: str | None = None, revision: str = pinned_revision) -> None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self.model_name = model_name or self.model_name
        self.revision = revision
        self.model = SentenceTransformer(self.model_name, revision=revision)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )


class DeterministicMockEncoder:
    model_name = "deterministic-mock-sbert"
    revision = "1"

    def __init__(self, embedding_dim: int = 768) -> None:
        self.embedding_dim = embedding_dim

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.empty((len(texts), self.embedding_dim), dtype=np.float32)
        for index, text in enumerate(texts):
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
            vectors[index] = np.random.default_rng(seed).standard_normal(self.embedding_dim)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return np.asarray(vectors / np.maximum(norms, np.finfo(np.float32).eps), dtype=np.float32)


@dataclass(frozen=True)
class EmbeddingArtifact:
    manifest: EmbeddingManifest
    artifact_dir: Path
    vectors: np.ndarray


def _product_text(row: object) -> str:
    values = row._asdict()  # type: ignore[attr-defined]
    return " | ".join(
        str(values.get(name) or "").strip()
        for name in (
            "name",
            "root_category_name",
            "leaf_category_name",
            "vendor",
            "description",
        )
    )


class SBERTArtifactBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build(
        self,
        snapshot: Snapshot,
        *,
        encoder: TextEncoder | None,
        source_kind: EmbeddingSource,
    ) -> EmbeddingArtifact:
        if encoder is None:
            if source_kind is EmbeddingSource.MOCK:
                encoder = DeterministicMockEncoder(self.settings.model.sbert_dim)
            else:
                encoder = RealSBERTEncoder(
                    self.settings.model.sbert_model_name,
                    self.settings.model.sbert_model_revision,
                )
        elif source_kind is EmbeddingSource.REAL and isinstance(encoder, DeterministicMockEncoder):
            raise DataIntegrityError("mock encoder cannot declare a real embedding source")

        catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
        texts = [_product_text(row) for row in catalog.itertuples(index=False)]
        vectors = np.asarray(encoder.encode(texts), dtype=np.float32)
        expected = (len(catalog), self.settings.model.sbert_dim)
        if vectors.shape != expected:
            raise DataIntegrityError(f"embedding shape {vectors.shape} != {expected}")
        if not np.isfinite(vectors).all():
            raise DataIntegrityError("embeddings contain NaN or Inf")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms <= np.finfo(np.float32).eps):
            raise DataIntegrityError("embeddings contain a zero vector")
        vectors = np.ascontiguousarray(vectors / norms, dtype=np.float32)

        input_sha = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()
        product_map_sha = hashlib.sha256(
            np.asarray(sorted(snapshot.product_map.items()), dtype=np.int64).tobytes()
        ).hexdigest()
        content_sha = hashlib.sha256(vectors.tobytes()).hexdigest()
        artifact_id = f"{snapshot.manifest.artifact_id}-{source_kind.value}-{content_sha[:12]}"
        manifest = EmbeddingManifest(
            artifact_id=artifact_id,
            content_sha256=content_sha,
            parent_sha256={"snapshot": snapshot.manifest.content_sha256},
            snapshot_sha256=snapshot.manifest.content_sha256,
            source_kind=source_kind,
            model_name=encoder.model_name,
            model_revision=encoder.revision,
            input_text_sha256=input_sha,
            product_map_sha256=product_map_sha,
            shape=vectors.shape,
        )

        root = self.settings.data.artifact_root.resolve() / "features"
        root.mkdir(parents=True, exist_ok=True)
        destination = root / artifact_id
        if destination.exists():
            raise ArtifactIntegrityError(f"immutable embedding artifact exists: {destination}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}-", dir=root))
        try:
            np.save(temporary / "sbert.npy", vectors)
            (temporary / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return EmbeddingArtifact(manifest=manifest, artifact_dir=destination, vectors=vectors)


def load_embedding_artifact(path: Path) -> EmbeddingArtifact:
    manifest = EmbeddingManifest.model_validate_json(
        (path / "manifest.json").read_text(encoding="utf-8")
    )
    vectors = np.load(path / "sbert.npy", mmap_mode="r")
    if hashlib.sha256(np.asarray(vectors).tobytes()).hexdigest() != manifest.content_sha256:
        raise ArtifactIntegrityError("embedding checksum mismatch")
    return EmbeddingArtifact(manifest=manifest, artifact_dir=path, vectors=vectors)
