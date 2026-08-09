"""Unit tests for user_tower.py module."""

import torch
import pytest
from models.user_tower import UserTower
from config import get_settings


def test_user_tower_forward():
    settings = get_settings()
    user_tower = UserTower(settings)

    user_idx = torch.tensor([0, 1, 42, 5000, 9999], dtype=torch.long)
    persona_idx = torch.tensor([0, 2, 7, 3, -1], dtype=torch.long)

    output = user_tower(user_idx, persona_idx)

    assert output.shape == (5, 64)
    # Check L2 normalization: norms must be ~1.0
    norms = torch.norm(output, p=2, dim=-1)
    torch.testing.assert_close(norms, torch.ones(5), rtol=1e-5, atol=1e-5)


def test_refresh_unknown_embedding():
    user_tower = UserTower()

    # Mutate known user embeddings
    with torch.no_grad():
        user_tower.user_embedding.weight[1:].fill_(2.0)

    user_tower.refresh_unknown_embedding()

    # Check that row 0 is now equal to mean (2.0)
    torch.testing.assert_close(
        user_tower.user_embedding.weight[0], torch.full((64,), 2.0)
    )
