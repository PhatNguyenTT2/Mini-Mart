"""Hybrid Wide and Deep ranking model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import torch
from torch import nn

from ai_service.config import Settings
from ai_service.contracts import ModelVariant
from ai_service.models.history_encoder import HistoryEncoder
from ai_service.models.item_tower import ItemTower
from ai_service.models.user_tower import UserTower
from ai_service.models.wide_layer import WideLayer


@dataclass(frozen=True)
class ScoreBreakdown:
    deep_logits: torch.Tensor
    wide_logits: torch.Tensor
    hybrid_logits: torch.Tensor


class HybridTwoTowerModel(nn.Module):
    _temperature: torch.Tensor

    def __init__(self, settings: Settings):
        super().__init__()
        self.register_buffer("_temperature", torch.tensor(settings.model.tau, dtype=torch.float32))
        self.user_tower = UserTower(settings)
        self.item_tower = ItemTower(settings)
        self.history_encoder = HistoryEncoder()
        self.wide_layer = WideLayer()

    @property
    def tau(self) -> float:
        return float(self._temperature.detach())

    def encode_user(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        *,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return cast(
            torch.Tensor,
            self.user_tower(
                user_idx,
                persona_idx,
                history_vector=history_vector,
                history_present=history_present,
            ),
        )

    def encode_items(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
        *,
        item_idx: torch.Tensor | None = None,
        is_cold: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return cast(
            torch.Tensor,
            self.item_tower(
                sbert,
                category_idx,
                price_idx,
                item_idx=item_idx,
                is_cold=is_cold,
            ),
        )

    def encode_history(
        self,
        item_vectors: torch.Tensor,
        mask: torch.Tensor,
        age_days: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return cast(
            tuple[torch.Tensor, torch.Tensor], self.history_encoder(item_vectors, mask, age_days)
        )

    def fuse_scores(self, deep: torch.Tensor, wide: torch.Tensor) -> torch.Tensor:
        """Combine temperature-scaled deep logits with Wide logits additively."""
        return deep + wide

    def score_breakdown(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        candidate_vectors: torch.Tensor,
        wide_values: torch.Tensor,
        rule_present: torch.Tensor,
        *,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> ScoreBreakdown:
        user_vectors = self.encode_user(
            user_idx,
            persona_idx,
            history_vector=history_vector,
            history_present=history_present,
        )
        if candidate_vectors.ndim == 2:
            deep = torch.matmul(user_vectors, candidate_vectors.T) / self._temperature
        elif candidate_vectors.ndim == 3:
            deep = (
                torch.matmul(candidate_vectors, user_vectors.unsqueeze(-1)).squeeze(-1)
                / self._temperature
            )
        else:
            raise ValueError("candidate_vectors must be [C,D] or [B,C,D]")
        wide = self.wide_layer(wide_values, rule_present)
        hybrid = self.fuse_scores(deep, wide)
        return ScoreBreakdown(deep_logits=deep, wide_logits=wide, hybrid_logits=hybrid)

    def score_cached(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        candidate_vectors: torch.Tensor,
        wide_values: torch.Tensor,
        rule_present: torch.Tensor,
        variant: ModelVariant = ModelVariant.HYBRID,
        *,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if variant is ModelVariant.DEEP_ONLY:
            # Keep the Deep ablation genuinely independent: evaluating a Deep
            # score must not execute the Wide branch (or create Wide grads).
            user_vectors = self.encode_user(
                user_idx,
                persona_idx,
                history_vector=history_vector,
                history_present=history_present,
            )
            if candidate_vectors.ndim == 2:
                return torch.matmul(user_vectors, candidate_vectors.T) / self._temperature
            if candidate_vectors.ndim == 3:
                return (
                    torch.matmul(candidate_vectors, user_vectors.unsqueeze(-1)).squeeze(-1)
                    / self._temperature
                )
            raise ValueError("candidate_vectors must be [C,D] or [B,C,D]")
        breakdown = self.score_breakdown(
            user_idx,
            persona_idx,
            candidate_vectors,
            wide_values,
            rule_present,
            history_vector=history_vector,
            history_present=history_present,
        )
        if variant is ModelVariant.WIDE_ONLY:
            return breakdown.wide_logits
        if variant in {ModelVariant.HYBRID, ModelVariant.NOISY_HYBRID}:
            return breakdown.hybrid_logits
        raise ValueError(f"variant {variant.value} is not a neural model variant")

    def forward(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        candidate_sbert: torch.Tensor,
        candidate_category: torch.Tensor,
        candidate_price: torch.Tensor,
        wide_values: torch.Tensor,
        rule_present: torch.Tensor,
        variant: ModelVariant = ModelVariant.HYBRID,
        *,
        item_idx: torch.Tensor | None = None,
        is_cold: torch.Tensor | None = None,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return self.score_cached(
            user_idx,
            persona_idx,
            self.encode_items(
                candidate_sbert,
                candidate_category,
                candidate_price,
                item_idx=item_idx,
                is_cold=is_cold,
            ),
            wide_values,
            rule_present,
            variant,
            history_vector=history_vector,
            history_present=history_present,
        )
