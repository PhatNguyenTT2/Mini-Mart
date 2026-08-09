"""SBERT Feature Embedding Cache Manager."""

import hashlib
from pathlib import Path
from typing import Protocol, Optional
import numpy as np
import pandas as pd

from ai_service.config import Settings
from ai_service.contracts import EmbeddingManifestV2, EmbeddingSource


class EmbeddingProvider(Protocol):
    """Protocol interface for generating raw text embeddings."""

    def encode(self, texts: list[str]) -> np.ndarray:
        ...


class SentenceTransformerProvider:
    """Production SentenceTransformer text embedder."""

    def __init__(self, model_name: str = "keepitreal/vietnamese-sbert"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)


class DeterministicFakeEmbedder:
    """Deterministic mock embedder for tests."""

    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim

    def encode(self, texts: list[str]) -> np.ndarray:
        embeddings = []
        for text in texts:
            seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed=seed)
            vec = rng.normal(loc=0.0, scale=1.0, size=self.embedding_dim).astype(np.float32)
            # L2 normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec)
        return np.array(embeddings, dtype=np.float32)


def precompute_embeddings(
    catalog_df: pd.DataFrame,
    output_dir: Path,
    provider: Optional[EmbeddingProvider] = None,
    source_kind: EmbeddingSource = EmbeddingSource.REAL,
) -> np.ndarray:
    """Precompute and save normalized 768d text embeddings for product catalog."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sort by internal_product_id (0..5199)
    sorted_catalog = catalog_df.sort_values(by="internal_product_id").reset_index(drop=True)
    texts = sorted_catalog["name"].fillna("sản phẩm").tolist()

    if provider is None:
        try:
            provider = SentenceTransformerProvider()
            source_kind = EmbeddingSource.REAL
        except Exception:
            provider = DeterministicFakeEmbedder(768)
            source_kind = EmbeddingSource.MOCK

    embeddings = provider.encode(texts)

    # Save NumPy array
    np.save(output_dir / "sbert_embeddings.npy", embeddings)

    # Compute Checksum
    checksum = hashlib.sha256(embeddings.tobytes()).hexdigest()[:16]

    manifest = EmbeddingManifestV2(
        source_kind=source_kind,
        model_name="keepitreal/vietnamese-sbert" if source_kind == EmbeddingSource.REAL else "DeterministicFakeEmbedder",
        embedding_dim=embeddings.shape[1],
        num_items=len(embeddings),
        checksum=checksum,
    )

    (output_dir / "sbert_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return embeddings
