"""Unit tests for precompute_sbert.py module."""

import numpy as np
import pytest
from data.ingestion import load_snapshot, build_snapshot
from data.precompute_sbert import (
    precompute_embeddings,
    format_product_text,
    compute_text_template_hash,
)


def test_text_template_formatting(tmp_path):
    build_snapshot(snapshot_id="test-sbert-snapshot")
    snapshot = load_snapshot("test-sbert-snapshot")
    sample_row = snapshot.catalog_df.iloc[0]

    formatted_text = format_product_text(sample_row)
    assert "Thương hiệu:" in formatted_text
    assert "Danh mục:" in formatted_text
    assert len(compute_text_template_hash()) == 64


def test_precompute_embeddings_mock():
    snapshot = load_snapshot("test-sbert-snapshot")
    embeddings, manifest = precompute_embeddings(snapshot, use_mock=True)

    assert embeddings.shape == (5200, 768)
    assert embeddings.dtype == np.float32

    # Check L2 normalization: vector norms must be ~1.0
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-5)

    assert manifest.num_products == 5200
    assert manifest.embedding_dim == 768
    assert manifest.is_normalized is True
