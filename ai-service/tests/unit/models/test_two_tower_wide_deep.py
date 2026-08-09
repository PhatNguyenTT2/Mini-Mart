"""Unit tests for two_tower_wide_deep.py module."""

import torch
import pytest
from models.two_tower_wide_deep import HybridTwoTowerModel, HybridScores
from config import get_settings


def test_hybrid_model_end_to_end_forward():
    settings = get_settings()
    model = HybridTwoTowerModel(settings)

    B, C = 4, 5
    user_idx = torch.tensor([1, 42, 0, 5000], dtype=torch.long)
    persona_idx = torch.tensor([2, 7, 0, 3], dtype=torch.long)

    sbert = torch.randn(B, C, 768)
    cat_idx = torch.randint(0, 41, (B, C))
    price_idx = torch.randint(0, 9, (B, C))
    log_lift = torch.tensor(
        [
            [[0.0], [2.5], [0.0], [0.0], [1.2]],
            [[0.0], [0.0], [0.0], [0.0], [0.0]],
            [[1.0], [1.0], [1.0], [1.0], [1.0]],
            [[0.0], [0.0], [3.5], [0.0], [0.0]],
        ],
        dtype=torch.float32,
    )

    scores = model(user_idx, persona_idx, sbert, cat_idx, price_idx, log_lift, use_wide=True)

    assert isinstance(scores, HybridScores)
    assert scores.logits.shape == (B, C)
    assert scores.deep_logits.shape == (B, C)
    assert scores.wide_logits.shape == (B, C)

    # Check Deep-only ablation
    deep_only_scores = model(
        user_idx, persona_idx, sbert, cat_idx, price_idx, log_lift, use_wide=False
    )
    torch.testing.assert_close(deep_only_scores.logits, deep_only_scores.deep_logits)
    torch.testing.assert_close(deep_only_scores.wide_logits, torch.zeros(B, C))


def test_model_backward_pass():
    model = HybridTwoTowerModel()
    B, C = 2, 5

    user_idx = torch.tensor([1, 2], dtype=torch.long)
    persona_idx = torch.tensor([0, 1], dtype=torch.long)
    sbert = torch.randn(B, C, 768)
    cat_idx = torch.randint(0, 41, (B, C))
    price_idx = torch.randint(0, 9, (B, C))
    log_lift = torch.rand(B, C, 1)

    scores = model(user_idx, persona_idx, sbert, cat_idx, price_idx, log_lift)
    loss = scores.logits.sum()
    loss.backward()

    # Verify gradients computed for model parameters
    assert model.user_tower.fc1.weight.grad is not None
    assert model.item_tower.sbert_proj.weight.grad is not None
    assert model.wide_layer.fc1.weight.grad is not None
