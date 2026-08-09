"""Hybrid Two-Tower Wide & Deep Model module for ai-service.

Unifies User Tower, Item Tower, and Masked Wide MLP into a single end-to-end recommender architecture with temperature-scaled dot-product similarity (tau = 0.1) and additive joint scoring.
"""

from dataclasses import dataclass
from typing import Optional
import torch
import torch.nn as nn

from config import get_settings, Settings
from models.user_tower import UserTower
from models.item_tower import ItemTower
from models.wide_layer import WideLayer


@dataclass
class HybridScores:
    """Container for model output logits and branch diagnostic scores."""

    logits: torch.Tensor          # [B, C] joint unnormalized logits
    deep_logits: torch.Tensor     # [B, C] temperature-scaled deep dot products
    wide_logits: torch.Tensor     # [B, C] wide MLP rule contributions


class HybridTwoTowerModel(nn.Module):
    """Hybrid Cascade Ranking Architecture (Wide Apriori MLP + Deep Two-Tower SBERT)."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = get_settings()

        self.tau = settings.model.tau  # 0.1

        self.user_tower = UserTower(settings)
        self.item_tower = ItemTower(settings)
        self.wide_layer = WideLayer(settings)

    def encode_users(self, user_idx: torch.Tensor, persona_idx: torch.Tensor) -> torch.Tensor:
        """Encode users into 64d L2-normalized vectors."""
        return self.user_tower(user_idx, persona_idx)

    def encode_items(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
    ) -> torch.Tensor:
        """Encode items into 64d L2-normalized vectors for any leading tensor shape."""
        return self.item_tower(sbert, category_idx, price_idx)

    def refresh_unknown_embedding(self) -> None:
        """Delegate UNK user embedding refresh to User Tower."""
        self.user_tower.refresh_unknown_embedding()

    def score_candidates(
        self,
        user_vectors: torch.Tensor,
        item_vectors: torch.Tensor,
        log_lift: torch.Tensor,
        use_wide: bool = True,
    ) -> HybridScores:
        """Compute joint logits given user vectors [B, 64], item vectors [B, C, 64], and log1p lift [B, C, 1].

        Args:
            user_vectors: Tensor [B, 64]
            item_vectors: Tensor [B, C, 64]
            log_lift: Tensor [B, C, 1]
            use_wide: If False, disables Wide branch score contribution for Deep-only ablation

        Returns:
            HybridScores dataclass container
        """
        # Deep Dot Product Similarity with Temperature Scaling: S_deep = (U . V) / tau
        # user_vectors: [B, 64], item_vectors: [B, C, 64] -> dot product [B, C]
        deep_dot = torch.einsum("bd,bcd->bc", user_vectors, item_vectors)
        deep_logits = deep_dot / self.tau  # [B, C]

        if use_wide:
            wide_logits = self.wide_layer(log_lift)  # [B, C]
        else:
            wide_logits = torch.zeros_like(deep_logits)

        joint_logits = deep_logits + wide_logits  # [B, C]

        return HybridScores(
            logits=joint_logits,
            deep_logits=deep_logits.detach(),
            wide_logits=wide_logits.detach(),
        )

    def forward(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
        log_lift: torch.Tensor,
        use_wide: bool = True,
    ) -> HybridScores:
        """End-to-end forward pass for grouped candidate training or inference.

        Args:
            user_idx: Tensor [B]
            persona_idx: Tensor [B]
            sbert: Tensor [B, C, 768]
            category_idx: Tensor [B, C]
            price_idx: Tensor [B, C]
            log_lift: Tensor [B, C, 1]
            use_wide: bool flag for Wide branch activation

        Returns:
            HybridScores container
        """
        user_vectors = self.encode_users(user_idx, persona_idx)  # [B, 64]
        item_vectors = self.encode_items(sbert, category_idx, price_idx)  # [B, C, 64]

        return self.score_candidates(
            user_vectors=user_vectors,
            item_vectors=item_vectors,
            log_lift=log_lift,
            use_wide=use_wide,
        )
