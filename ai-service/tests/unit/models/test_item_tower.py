"""Unit tests for item_tower.py module."""

import torch
import pytest
from models.item_tower import ItemTower
from config import get_settings


def test_item_tower_forward_1d():
    item_tower = ItemTower()

    sbert = torch.randn(10, 768)
    cat_idx = torch.tensor([0, 1, 40, 99, 15, 20, 5, 10, 30, 25], dtype=torch.long)
    price_idx = torch.tensor([0, 1, 8, 99, 2, 4, 6, 7, 3, 5], dtype=torch.long)

    output = item_tower(sbert, cat_idx, price_idx)

    assert output.shape == (10, 64)
    # Check L2 normalization: norms must be ~1.0
    norms = torch.norm(output, p=2, dim=-1)
    torch.testing.assert_close(norms, torch.ones(10), rtol=1e-5, atol=1e-5)


def test_item_tower_forward_2d_batch_candidates():
    item_tower = ItemTower()

    # Shape [B, C, 768] = [32, 5, 768]
    sbert = torch.randn(32, 5, 768)
    cat_idx = torch.randint(0, 41, (32, 5))
    price_idx = torch.randint(0, 9, (32, 5))

    output = item_tower(sbert, cat_idx, price_idx)

    assert output.shape == (32, 5, 64)
    norms = torch.norm(output, p=2, dim=-1)
    torch.testing.assert_close(norms, torch.ones(32, 5), rtol=1e-5, atol=1e-5)
