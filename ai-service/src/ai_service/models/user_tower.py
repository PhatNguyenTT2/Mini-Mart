"""User Tower Module for Dense User Embedding Representation."""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

from ai_service.config import Settings


class UserTower(nn.Module):
    """Encodes User ID and Persona Cluster into an L2-normalized 64d embedding."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = Settings()

        self.num_users = settings.data.num_users
        self.num_personas = settings.data.num_personas
        self.user_emb_dim = settings.model.user_emb_dim
        self.persona_emb_dim = settings.model.persona_emb_dim
        self.out_dim = settings.model.item_emb_dim

        # Embeddings (+1 for UNK index 0)
        self.user_embedding = nn.Embedding(
            num_embeddings=self.num_users + 1,
            embedding_dim=self.user_emb_dim,
            padding_idx=0,
        )
        self.persona_embedding = nn.Embedding(
            num_embeddings=self.num_personas,
            embedding_dim=self.persona_emb_dim,
        )

        in_features = self.user_emb_dim + self.persona_emb_dim  # 64 + 8 = 72
        self.fc1 = nn.Linear(in_features, 128)
        self.relu = nn.ReLU()
        self.norm = nn.LayerNorm(128)
        self.fc2 = nn.Linear(128, self.out_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.persona_embedding.weight, std=0.01)
        nn.init.zeros_(self.user_embedding.weight[0])  # UNK padding index 0

        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity="relu")
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_normal_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, user_idx: torch.Tensor, persona_idx: torch.Tensor) -> torch.Tensor:
        """Forward pass generating L2-normalized user vectors [B, 64]."""
        u_emb = self.user_embedding(user_idx)       # [B, 64]
        p_emb = self.persona_embedding(persona_idx) # [B, 8]

        x = torch.cat([u_emb, p_emb], dim=-1)       # [B, 72]
        x = self.fc1(x)                             # [B, 128]
        x = self.relu(x)
        x = self.norm(x)
        x = self.fc2(x)                             # [B, 64]

        return F.normalize(x, p=2, dim=-1, eps=1e-8)
