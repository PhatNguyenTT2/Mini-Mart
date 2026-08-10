from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service.config import Settings
from ai_service.contracts import ContextRef, EmbeddingSource, SplitName
from ai_service.data.dataset import HybridImplicitDataset
from ai_service.data.features import (
    DeterministicMockEncoder,
    SBERTArtifactBuilder,
    load_embedding_artifact,
)
from ai_service.data.rules import AprioriRuleMiner, RuleStore, load_rule_artifact
from ai_service.data.snapshot import Snapshot


def _snapshot(tmp_path: Path) -> Snapshot:
    catalog = pd.DataFrame(
        {
            "product_id": np.arange(101, 109),
            "internal_product_id": np.arange(8),
            "name": [f"item-{idx}" for idx in range(8)],
            "leaf_category_name": ["leaf"] * 8,
            "root_category_name": ["root"] * 8,
            "vendor": ["vendor"] * 8,
            "description": [""] * 8,
            "internal_leaf_category_id": [1] * 8,
            "price_bucket_id": [1] * 8,
        }
    )
    timestamps = pd.to_datetime(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T02:00:00Z",
        ],
        utc=True,
    )
    train = pd.DataFrame(
        {
            "event_id": ["a", "b", "c", "d"],
            "internal_user_id": [1, 1, 1, 1],
            "internal_product_id": [0, 1, 2, 3],
            "event_type": ["purchase", "view", "purchase", "purchase"],
            "event_ts": timestamps,
            "interaction_weight": [1.0, 0.5, 1.0, 1.0],
        }
    )
    return Snapshot(
        manifest=SimpleNamespace(num_items=8, artifact_id="fixture", content_sha256="a" * 64),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=train,
        val_df=train.iloc[0:0].copy(),
        test_df=train.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={idx + 101: idx for idx in range(8)},
        raw_product_map={idx: idx + 101 for idx in range(8)},
        user_map={11: 1},
        raw_user_map={1: 11},
        persona_map={11: 2},
        cold_item_ids=(7,),
        price_boundaries=np.array([10.0]),
    )


def test_mock_embedding_artifact_is_explicit_normalized_and_hashed(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.model.sbert_dim = 8
    artifact = SBERTArtifactBuilder(settings).build(
        _snapshot(tmp_path),
        encoder=DeterministicMockEncoder(embedding_dim=8),
        source_kind=EmbeddingSource.MOCK,
    )

    assert artifact.vectors.shape == (8, 8)
    assert artifact.vectors.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(artifact.vectors, axis=1), 1.0, atol=1e-5)
    assert artifact.manifest.source_kind is EmbeddingSource.MOCK
    assert len(artifact.manifest.content_sha256) == 64
    loaded = load_embedding_artifact(artifact.artifact_dir)
    np.testing.assert_array_equal(loaded.vectors, artifact.vectors)


def test_real_embedding_provider_error_is_not_replaced_by_mock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path

    class BrokenEncoder:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise OSError("model unavailable")

    monkeypatch.setattr("ai_service.data.features.RealSBERTEncoder", BrokenEncoder)
    with pytest.raises(OSError, match="model unavailable"):
        SBERTArtifactBuilder(settings).build(
            _snapshot(tmp_path), encoder=None, source_kind=EmbeddingSource.REAL
        )


def test_rule_store_is_sparse_csr_and_zero_masks_missing_rules() -> None:
    store = RuleStore(
        num_items=8,
        rule_pairs=[
            (0, 4, 12.0, 0.1, 0.6, 120),
            (0, 5, 4.0, 0.05, 0.3, 60),
            (2, 4, 2.0, 0.01, 0.2, 20),
        ],
    )

    assert store.csr.layout == torch.sparse_csr
    values, present = store.batch_lookup(
        np.array([0, -1]), np.array([[4, 6], [4, 5]], dtype=np.int64)
    )
    assert values.shape == (2, 2, 3)
    assert present.tolist() == [[True, False], [False, False]]
    assert values[0, 0, 0] > 0
    assert values[0, 0, 1] == pytest.approx(0.6)
    assert np.count_nonzero(values[1]) == 0
    lifts, present_mask = store.batch_raw_lift(
        np.array([0]),
        np.array([[4, 5]], dtype=np.int64),
    )
    assert lifts.tolist() == [[12.0, 4.0]]
    assert present_mask.tolist() == [[True, True]]


def test_rule_miner_round_trips_train_only_sparse_artifact(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.min_rule_count = 1
    settings.data.min_rule_lift = 0.0
    orders = pd.DataFrame(
        {
            "order_id": [1, 1, 2, 2, 3, 3],
            "internal_product_id": [0, 1, 0, 1, 0, 2],
        }
    )
    snapshot = replace(_snapshot(tmp_path), order_baskets_df=orders)

    artifact = AprioriRuleMiner(settings).mine(snapshot)
    loaded = load_rule_artifact(artifact.artifact_dir, num_items=8)

    assert artifact.manifest.train_basket_count == 3
    assert artifact.manifest.num_directed_rules == 4
    assert loaded.store.lookup(0, 1) > 0


def test_dataset_uses_strict_purchase_context_and_dynamic_negative_ratio(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    dataset = HybridImplicitDataset(
        snapshot,
        RuleStore(8, [(0, 4, 2.0)]),
        split=SplitName.TRAIN,
        negative_ratio=3,
        seed=42,
    )

    assert dataset.context_refs == (
        ContextRef(item_idx=-1, present=False),
        ContextRef(item_idx=0, present=True),
        ContextRef(item_idx=0, present=True),
        ContextRef(item_idx=2, present=True),
    )
    sample = dataset[0]
    candidates = sample["candidate_item_idx"]
    assert candidates.shape == (4,)
    assert candidates[0] == 0
    assert len(set(candidates.tolist())) == 4
    assert not set(candidates[1:]) & {0, 1, 2, 3, 7}
    dataset.set_epoch(0)
    np.testing.assert_array_equal(dataset[0]["candidate_item_idx"], candidates)
