from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ai_service.data.dataset import build_purchase_training_index
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot
from ai_service.errors import NegativeSamplingError


def _snapshot(tmp_path: Path) -> Snapshot:
    events = pd.DataFrame(
        {
            "event_id": ["a", "b"],
            "internal_user_id": [1, 1],
            "internal_product_id": [0, 1],
            "event_type": ["purchase", "purchase"],
            "event_ts": pd.date_range("2026-01-01", periods=2, tz="UTC"),
            "event_origin": ["organic", "organic"],
        }
    )
    return Snapshot(
        manifest=SimpleNamespace(num_users=1, num_items=6),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame({"internal_product_id": range(6)}),
        train_df=events,
        val_df=events.iloc[0:0].copy(),
        test_df=events.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={100 + i: i for i in range(6)},
        raw_product_map={i: 100 + i for i in range(6)},
        user_map={10: 1},
        raw_user_map={1: 10},
        persona_map={10: 0},
        cold_item_ids=(5,),
        price_boundaries=np.asarray([5.0]),
    )


def test_sampler_constructor_and_input_guards(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    index = build_purchase_training_index(snapshot, max_history_items=2)
    embeddings = np.eye(6, dtype=np.float32)
    with pytest.raises(ValueError, match="at least four"):
        MixedNegativeSampler(index, snapshot, embeddings, ratio=3)
    with pytest.raises(ValueError, match="do not match"):
        MixedNegativeSampler(index, snapshot, np.eye(5, dtype=np.float32), ratio=4)
    sampler = MixedNegativeSampler(index, snapshot, embeddings, ratio=4)
    with pytest.raises(ValueError, match="equal"):
        sampler.sample(np.asarray([1]), np.asarray([1, 2]), epoch=1, batch_index=0)
    with pytest.raises(NegativeSamplingError, match="range"):
        sampler.sample(np.asarray([0]), np.asarray([1]), epoch=1, batch_index=0)
    with pytest.raises(ValueError, match="width"):
        sampler.update_model_hard_cache(np.full((2, 0), -1, dtype=np.int32))
