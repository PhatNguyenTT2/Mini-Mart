"""Unit tests for wide_layer.py module."""

import torch
import pytest
from models.wide_layer import WideLayer


def test_wide_layer_zero_masking():
    wide_layer = WideLayer()

    # Manually set FC2 bias to non-zero to test presence mask
    with torch.no_grad():
        wide_layer.fc2.bias.fill_(5.0)
        wide_layer.fc2.weight.fill_(1.0)
        wide_layer.fc1.weight.fill_(1.0)

    log_lift = torch.tensor([[[0.0]], [[1.5]], [[0.0]], [[6.71]]], dtype=torch.float32)
    scores = wide_layer(log_lift)

    assert scores.shape == (4, 1)

    # Missing rule (0.0) MUST produce exact 0.0 despite FC2 bias of 5.0
    assert scores[0, 0].item() == 0.0
    assert scores[2, 0].item() == 0.0

    # Active rules (> 0.0) produce positive scores
    assert scores[1, 0].item() > 0.0
    assert scores[3, 0].item() > 0.0


def test_wide_layer_zero_initialization():
    wide_layer = WideLayer()  # default zero-init for fc2

    log_lift = torch.tensor([[[2.5]], [[4.0]]], dtype=torch.float32)
    scores = wide_layer(log_lift)

    # Initial zero-init produces 0.0 scores
    torch.testing.assert_close(scores, torch.zeros(2, 1))
