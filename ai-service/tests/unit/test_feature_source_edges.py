from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ai_service.config import Settings
from ai_service.contracts import EmbeddingSource
from ai_service.data.features import (
    DeterministicMockEncoder,
    SBERTArtifactBuilder,
    load_embedding_artifact,
)
from ai_service.data.snapshot import SnapshotBuilder, load_snapshot
from ai_service.data.sources import SyntheticDatasetSource
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError, SourceReadError
from tests.support.v5_factories import make_settings, make_snapshot


def test_mock_embedding_builder_and_loader_are_hash_checked(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    artifact = SBERTArtifactBuilder(settings).build(
        snapshot,
        encoder=None,
        source_kind=EmbeddingSource.MOCK,
    )
    loaded = load_embedding_artifact(artifact.artifact_dir)
    assert loaded.vectors.shape == (snapshot.manifest.num_items, settings.model.sbert_dim)
    assert np.allclose(np.linalg.norm(loaded.vectors, axis=1), 1.0)
    tampered = np.zeros(loaded.vectors.shape, dtype=np.float32)
    del loaded
    np.save(artifact.artifact_dir / "sbert.npy", tampered)
    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        load_embedding_artifact(artifact.artifact_dir)


class _Encoder:
    model_name = "fixture"
    revision = "1"

    def __init__(self, values: np.ndarray) -> None:
        self.values = values

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.broadcast_to(self.values, (len(texts), self.values.shape[-1]))


def test_embedding_builder_rejects_wrong_source_shape_and_nonfinite_values(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    builder = SBERTArtifactBuilder(settings)
    with pytest.raises(DataIntegrityError, match="mock encoder"):
        builder.build(
            snapshot,
            encoder=DeterministicMockEncoder(settings.model.sbert_dim),
            source_kind=EmbeddingSource.REAL,
        )
    with pytest.raises(DataIntegrityError, match="embedding shape"):
        builder.build(
            snapshot,
            encoder=_Encoder(np.ones(2, dtype=np.float32)),
            source_kind=EmbeddingSource.MOCK,
        )
    with pytest.raises(DataIntegrityError, match="NaN"):
        builder.build(
            snapshot,
            encoder=_Encoder(np.full(settings.model.sbert_dim, np.nan, dtype=np.float32)),
            source_kind=EmbeddingSource.MOCK,
        )


def test_deterministic_encoder_and_synthetic_source_guards(tmp_path: Path) -> None:
    encoder = DeterministicMockEncoder(4)
    first = encoder.encode(["a", "b"])
    second = encoder.encode(["a", "b"])
    np.testing.assert_array_equal(first, second)
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 4
    settings.data.num_items = 10
    settings.data.num_cold_items = 2
    settings.data.expected_event_count = 20
    settings.data.expected_train_count = 10
    settings.data.expected_val_count = 5
    settings.data.expected_test_count = 5
    settings.data.expected_order_count = 1
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    source = SyntheticDatasetSource(settings, num_events=20)
    dataset = source.load(1, "synthetic-edge")
    assert len(dataset.events_df) == 20
    snapshot = SnapshotBuilder(settings).build(dataset, snapshot_id="snapshot-edge")
    loaded = load_snapshot("snapshot-edge", settings)
    assert loaded.manifest.content_sha256 == snapshot.manifest.content_sha256
    settings.data.expected_test_count = 1
    with pytest.raises(SourceReadError, match="split counts"):
        SyntheticDatasetSource(settings, num_events=20).load(1)
