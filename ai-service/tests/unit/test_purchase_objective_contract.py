from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service.data.dataset import build_purchase_training_index
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot
from ai_service.training.objectives import multi_positive_sampled_softmax


def _snapshot(tmp_path: Path) -> Snapshot:
    train = pd.DataFrame(
        {
            "event_id": ["a", "b", "c", "d", "e", "f"],
            "internal_user_id": [1, 1, 1, 2, 2, 2],
            "internal_product_id": [0, 0, 1, 2, 2, 3],
            "event_type": ["view", "purchase", "purchase", "view", "purchase", "purchase"],
            "event_ts": pd.date_range("2026-01-01", periods=6, freq="h", tz="UTC"),
            "event_origin": ["organic"] * 6,
        }
    )
    return Snapshot(
        manifest=SimpleNamespace(num_users=2, num_items=8),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame({"internal_product_id": range(8)}),
        train_df=train,
        val_df=train.iloc[0:0].copy(),
        test_df=train.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={100 + item: item for item in range(8)},
        raw_product_map={item: 100 + item for item in range(8)},
        user_map={101: 1, 102: 2},
        raw_user_map={1: 101, 2: 102},
        persona_map={101: 0, 102: 1},
        cold_item_ids=(7,),
        price_boundaries=np.asarray([10.0]),
    )


def test_purchase_index_aggregates_confidence_and_strict_histories(tmp_path: Path) -> None:
    index = build_purchase_training_index(_snapshot(tmp_path), max_history_items=2)

    assert index.users.tolist() == [1, 1, 2, 2]
    assert index.positive_items.tolist() == [0, 1, 2, 3]
    assert index.history_items.tolist() == [[-1, -1], [-1, 0], [-1, -1], [-1, 2]]
    assert index.known_history[1, 0]
    assert index.known_history[1, 1]
    assert index.confidence[0] == pytest.approx(1.0 + np.log(2.0) + 0.1 * np.log(2.0))


def test_mixed_negative_sampler_is_deterministic_and_excludes_history_and_cold(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path)
    index = build_purchase_training_index(snapshot, max_history_items=2)
    embeddings = np.eye(8, dtype=np.float32)
    sampler = MixedNegativeSampler(index, snapshot, embeddings, ratio=4, seed=42)

    first = sampler.sample(index.users, index.positive_items, epoch=1, batch_index=0)
    repeated = sampler.sample(index.users, index.positive_items, epoch=1, batch_index=0)
    next_epoch = sampler.sample(index.users, index.positive_items, epoch=2, batch_index=0)

    np.testing.assert_array_equal(first, repeated)
    assert first.shape == (4, 4)
    assert any(
        not np.array_equal(left, right) for left, right in zip(first, next_epoch, strict=True)
    )
    for user, row in zip(index.users, first, strict=True):
        assert len(set(row.tolist())) == 4
        assert 7 not in row
        assert not index.known_history[int(user), row].any()


def test_multi_positive_sampled_softmax_matches_worked_example() -> None:
    users = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    positives = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    explicit = torch.zeros(2, 1, 2)
    positive_mask = torch.eye(2, dtype=torch.bool)
    denominator_mask = torch.eye(2, dtype=torch.bool)

    result = multi_positive_sampled_softmax(
        users,
        positives,
        explicit,
        positive_mask=positive_mask,
        denominator_mask=denominator_mask,
        confidence=torch.ones(2),
        temperature=torch.tensor(1.0),
    )

    assert float(result.loss) == pytest.approx(0.3132617, abs=1e-6)
    assert result.sampled_pair_accuracy == pytest.approx(1.0)
    assert result.all_negative_win_rate == pytest.approx(1.0)


def test_sampled_softmax_rejects_every_malformed_tensor_contract() -> None:
    users = torch.eye(2)
    positives = torch.eye(2)
    negatives = torch.zeros(2, 1, 2)
    mask = torch.eye(2, dtype=torch.bool)
    confidence = torch.ones(2)
    temperature = torch.tensor(1.0)

    def call(
        user: torch.Tensor = users,
        positive: torch.Tensor = positives,
        negative: torch.Tensor = negatives,
        positive_mask: torch.Tensor = mask,
        denominator_mask: torch.Tensor = mask,
        weights: torch.Tensor = confidence,
        tau: torch.Tensor = temperature,
    ) -> None:
        multi_positive_sampled_softmax(
            user,
            positive,
            negative,
            positive_mask=positive_mask,
            denominator_mask=denominator_mask,
            confidence=weights,
            temperature=tau,
        )

    with pytest.raises(ValueError, match="share shape"):
        call(user=users[0])
    with pytest.raises(ValueError, match=r"\[B,R,D\]"):
        call(negative=torch.zeros(2, 2))
    with pytest.raises(ValueError, match="dimension"):
        call(negative=torch.zeros(2, 1, 3))
    with pytest.raises(ValueError, match="masks"):
        call(positive_mask=torch.ones(1, 1, dtype=torch.bool))
    with pytest.raises(ValueError, match="confidence"):
        call(weights=torch.zeros(2))
    with pytest.raises(ValueError, match="temperature"):
        call(tau=torch.tensor(float("nan")))
    with pytest.raises(ValueError, match="at least one positive"):
        call(positive_mask=torch.zeros_like(mask))
    with pytest.raises(ValueError, match="not finite"):
        call(tau=torch.tensor(0.0))


def test_sampled_softmax_handles_a_batch_with_no_negative_candidate() -> None:
    result = multi_positive_sampled_softmax(
        torch.tensor([[1.0, 0.0]]),
        torch.tensor([[1.0, 0.0]]),
        torch.empty(1, 0, 2),
        positive_mask=torch.ones(1, 1, dtype=torch.bool),
        denominator_mask=torch.zeros(1, 1, dtype=torch.bool),
        confidence=torch.ones(1),
        temperature=torch.tensor(1.0),
    )

    assert result.sampled_pair_accuracy == 1.0
    assert result.all_negative_win_rate == 1.0
