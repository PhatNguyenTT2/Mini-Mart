"""Strict recency-weighted aggregation of prior purchase item vectors."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class HistoryEncoder(nn.Module):
    def __init__(self, *, half_life_days: float = 30.0) -> None:
        super().__init__()
        if half_life_days <= 0:
            raise ValueError("history half life must be positive")
        self.half_life_days = half_life_days

    def forward(
        self,
        item_vectors: torch.Tensor,
        mask: torch.Tensor,
        age_days: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if item_vectors.ndim != 3 or mask.shape != item_vectors.shape[:2]:
            raise ValueError("history inputs must have shape [B,L,D] and [B,L]")
        if mask.dtype != torch.bool:
            raise ValueError("history mask must be boolean")
        if age_days is None:
            age_days = torch.zeros_like(mask, dtype=item_vectors.dtype)
        if age_days.shape != mask.shape or not bool(torch.isfinite(age_days).all()):
            raise ValueError("history ages must be finite [B,L]")
        weights = torch.exp(-age_days / self.half_life_days) * mask.to(item_vectors.dtype)
        total = weights.sum(dim=1, keepdim=True)
        profile = (item_vectors * weights.unsqueeze(-1)).sum(dim=1)
        profile = profile / total.clamp_min(torch.finfo(item_vectors.dtype).eps)
        present = mask.any(dim=1)
        profile = torch.where(present.unsqueeze(-1), profile, torch.zeros_like(profile))
        return F.normalize(profile, p=2, dim=-1, eps=1e-8), present
