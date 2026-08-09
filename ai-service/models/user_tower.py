"""User Tower module for ai-service.

Encodes User ID (5001 x 64d) and Persona Cluster (8 x 8d) into a 64-dimensional L2-normalized user embedding vector.
Supports UNK user fallback (row 0 refreshed with mean known user embedding) and cluster 0 default for missing personas.
"""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

from config import get_settings, Settings


class UserTower(nn.Module):
    """User Tower neural network encoding User ID and Persona Cluster into 64d L2-normalized representation."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = get_settings()

        self.num_users = settings.data.num_users + 1  # 5001 (row 0 = UNK)
        self.num_personas = settings.data.num_personas  # 8 (0..7)

        self.user_emb_dim = settings.model.user_emb_dim  # 64
        self.persona_emb_dim = settings.model.persona_emb_dim  # 8
        self.item_emb_dim = settings.model.item_emb_dim  # 64

        # Embeddings
        self.user_embedding = nn.Embedding(self.num_users, self.user_emb_dim, padding_idx=0)
        self.persona_embedding = nn.Embedding(self.num_personas, self.persona_emb_dim)

        # MLP Block: 72 -> 128 -> ReLU -> LayerNorm -> 64
        in_features = self.user_emb_dim + self.persona_emb_dim  # 72
        self.fc1 = nn.Linear(in_features, 128)
        self.relu = nn.ReLU()
        self.layer_norm = nn.LayerNorm(128)
        self.fc2 = nn.Linear(128, self.item_emb_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights with Xavier uniform for linear layers and normal for embeddings."""
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.persona_embedding.weight, std=0.01)

        # Ensure row 0 is zeroed out initially
        with torch.no_grad():
            self.user_embedding.weight[0].fill_(0.0)

        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def refresh_unknown_embedding(self) -> None:
        """Replace UNK user embedding (row 0) with mean of all trained known user embeddings (rows 1:)."""
        with torch.no_grad():
            mean_embedding = self.user_embedding.weight[1:].mean(dim=0)
            self.user_embedding.weight[0].copy_(mean_embedding)

    def forward(self, user_idx: torch.Tensor, persona_idx: torch.Tensor) -> torch.Tensor:
        """Forward pass generating L2-normalized user vectors.

        Args:
            user_idx: Tensor of user indices [B] in 0..5000 (0=UNK)
            persona_idx: Tensor of persona indices [B] in 0..7

        Returns:
            Tensor of L2-normalized user embeddings [B, 64]
        """
        # Clamp persona to valid 0..7 range (default 0 for invalid)
        persona_clamped = torch.clamp(persona_idx, 0, self.num_personas - 1)

        # Clamp unknown user IDs > 5000 to UNK row 0
        user_clamped = torch.where(
            (user_idx >= 0) & (user_idx < self.num_users), user_idx, torch.zeros_like(user_idx)
        )

        u_emb = self.user_embedding(user_clamped)  # [B, 64]
        p_emb = self.persona_embedding(persona_clamped)  # [B, 8]

        concat = torch.cat([u_emb, p_emb], dim=-1)  # [B, 72]

        h1 = self.fc1(concat)  # [B, 128]
        h1_act = self.relu(h1)  # [B, 128]
        h1_norm = self.layer_norm(h1_act)  # [B, 128]

        h2 = self.fc2(h1_norm)  # [B, 64]

        # L2 Normalization with epsilon protection
        output = F.normalize(h2, p=2, dim=-1, eps=1e-12)  # [B, 64]
        return output
