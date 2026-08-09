"""Hybrid Two-Tower Wide & Deep Model Architecture."""

from typing import Optional, Tuple
import torch
import torch.nn as nn

from ai_service.config import Settings
from ai_service.models.user_tower import UserTower
from ai_service.models.item_tower import ItemTower
from ai_service.models.wide_layer import WideLayer


class HybridTwoTowerModel(nn.Module):
    """Hybrid Two-Tower Wide & Deep Recommender System Architecture."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = Settings()

        self.settings = settings
        self.tau = settings.model.tau

        self.user_tower = UserTower(settings=settings)
        self.item_tower = ItemTower(settings=settings)
        self.wide_layer = WideLayer(settings=settings)

    def encode_user(self, user_idx: torch.Tensor, persona_idx: torch.Tensor) -> torch.Tensor:
        return self.user_tower(user_idx, persona_idx)

    def encode_items(
        self,
        sbert_emb: torch.Tensor,
        cat_idx: torch.Tensor,
        price_idx: torch.Tensor,
    ) -> torch.Tensor:
        return self.item_tower(sbert_emb, cat_idx, price_idx)

    def forward(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        candidate_sbert: torch.Tensor,
        candidate_cat: torch.Tensor,
        candidate_price: torch.Tensor,
        log_lift: Optional[torch.Tensor] = None,
        context_present: Optional[torch.Tensor] = None,
        include_wide: bool = True,
    ) -> torch.Tensor:
        """Forward pass computing joint Deep + Wide logit scores [B, C]."""
        u_vec = self.encode_user(user_idx, persona_idx) # [B, 64]
        v_vec = self.encode_items(candidate_sbert, candidate_cat, candidate_price) # [B, C, 64]

        # Deep dot-product logit scaled by temperature tau
        deep_scores = torch.matmul(v_vec, u_vec.unsqueeze(-1)).squeeze(-1) / self.tau # [B, C]

        if include_wide and log_lift is not None:
            wide_scores = self.wide_layer(log_lift, context_present=context_present) # [B, C]
            return deep_scores + wide_scores

        return deep_scores
