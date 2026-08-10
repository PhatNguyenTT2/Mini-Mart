"""Masked non-negative MLP over lift, confidence, and co-purchase count."""

from __future__ import annotations

import torch
from torch import nn


class WideLayer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(3, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )
        output_layer = self.network[-1]
        if not isinstance(output_layer, nn.Linear):
            raise TypeError("wide output layer must be linear")
        nn.init.zeros_(output_layer.weight)
        nn.init.zeros_(output_layer.bias)

    def score_unchecked(
        self, wide_values: torch.Tensor, rule_present: torch.Tensor
    ) -> torch.Tensor:
        scores = self.network(wide_values).squeeze(-1)
        return torch.where(rule_present, scores, torch.zeros_like(scores))

    def forward(self, wide_values: torch.Tensor, rule_present: torch.Tensor) -> torch.Tensor:
        if not torch.jit.is_tracing():  # type: ignore[attr-defined,no-untyped-call]
            if wide_values.ndim < 2 or wide_values.shape[-1] != 3:
                raise ValueError("wide_values must have shape [...,3]")
            if rule_present.dtype != torch.bool or rule_present.shape != wide_values.shape[:-1]:
                raise ValueError("rule_present must be bool with shape wide_values[:-1]")
            if not bool(torch.isfinite(wide_values).all()):
                raise ValueError("wide values must be finite")
            if bool((wide_values < 0).any()):
                raise ValueError("wide values must be non-negative")
            confidence = wide_values[..., 1]
            if bool((confidence > 1).any()):
                raise ValueError("wide confidence must be in [0,1]")
        return self.score_unchecked(wide_values, rule_present)
