from __future__ import annotations

import pytest
import torch

from ai_service.config import Settings
from ai_service.contracts import ModelVariant
from ai_service.models.history_encoder import HistoryEncoder
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.models.user_tower import UserTower
from ai_service.models.wide_layer import WideLayer


def _settings() -> Settings:
    settings = Settings()
    settings.data.num_users = 3
    settings.data.num_items = 5
    settings.data.num_personas = 2
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 4
    return settings


def test_history_encoder_defaults_and_validates_inputs() -> None:
    encoder = HistoryEncoder()
    vectors = torch.eye(3).unsqueeze(0)
    mask = torch.tensor([[True, False, True]])
    profile, present = encoder(vectors, mask)
    assert profile.shape == (1, 3)
    assert present.tolist() == [True]
    empty_profile, empty_present = encoder(vectors, torch.zeros_like(mask))
    assert empty_present.tolist() == [False]
    assert torch.equal(empty_profile, torch.zeros_like(empty_profile))
    with pytest.raises(ValueError, match="half life"):
        HistoryEncoder(half_life_days=0)
    with pytest.raises(ValueError, match="boolean"):
        encoder(vectors, mask.to(torch.int64))
    with pytest.raises(ValueError, match="finite"):
        encoder(vectors, mask, torch.full_like(mask, float("nan"), dtype=torch.float32))


def test_wide_layer_zero_init_and_input_guards() -> None:
    layer = WideLayer()
    values = torch.ones(2, 3)
    present = torch.tensor([True, False])
    output = layer(values, present)
    assert torch.equal(output, torch.zeros(2))
    with pytest.raises(ValueError, match="shape"):
        layer(torch.ones(2, 2), present)
    with pytest.raises(ValueError, match="bool"):
        layer(values, present.to(torch.int64))
    with pytest.raises(ValueError, match="finite"):
        layer(torch.full((2, 3), float("nan")), present)
    with pytest.raises(ValueError, match="non-negative"):
        layer(torch.full((2, 3), -1.0), present)
    with pytest.raises(ValueError, match="confidence"):
        layer(torch.tensor([[0.0, 2.0, 0.0], [0.0, 0.0, 0.0]]), present)


def test_user_tower_and_hybrid_variants_cover_shape_and_ablation_paths() -> None:
    settings = _settings()
    tower = UserTower(settings)
    users = torch.tensor([1, 2], dtype=torch.int64)
    personas = torch.tensor([0, 1], dtype=torch.int64)
    history = torch.zeros(2, settings.model.item_emb_dim)
    encoded = tower(
        users, personas, history_vector=history, history_present=torch.tensor([True, False])
    )
    assert encoded.shape == (2, settings.model.item_emb_dim)
    with pytest.raises(ValueError, match="int64"):
        tower(users.float(), personas)
    with pytest.raises(ValueError, match="outside"):
        tower(torch.tensor([0, 4]), personas)
    with pytest.raises(ValueError, match="shape"):
        tower(users, personas, history_vector=torch.zeros(1, settings.model.item_emb_dim))

    model = HybridTwoTowerModel(settings)
    candidates = torch.randn(2, 4, settings.model.item_emb_dim)
    wide_values = torch.zeros(2, 4, 3)
    present = torch.zeros(2, 4, dtype=torch.bool)
    deep = model.score_cached(
        users, personas, candidates, wide_values, present, ModelVariant.DEEP_ONLY
    )
    wide = model.score_cached(
        users, personas, candidates, wide_values, present, ModelVariant.WIDE_ONLY
    )
    hybrid = model.score_cached(
        users, personas, candidates, wide_values, present, ModelVariant.HYBRID
    )
    assert deep.shape == wide.shape == hybrid.shape == (2, 4)
    with pytest.raises(ValueError, match="candidate_vectors"):
        model.score_cached(users, personas, torch.zeros(2, 4, 5, 2), wide_values, present)
    with pytest.raises(ValueError, match="variant"):
        model.score_cached(users, personas, candidates, wide_values, present, ModelVariant.RANDOM)
