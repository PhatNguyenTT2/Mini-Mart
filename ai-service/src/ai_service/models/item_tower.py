"""Item Tower Module for Item Feature Embedding Representation."""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

from ai_service.config import Settings


class ItemTower(nn.Module):
    """Encodes SBERT Text (768d), Category ID, and Price Bucket into an L2-normalized 64d embedding."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = Settings()

        self.num_categories = settings.data.num_leaf_categories
        self.num_price_buckets = settings.data.num_price_buckets
        self.sbert_dim = settings.model.sbert_dim
        self.category_emb_dim = settings.model.category_emb_dim
        self.price_emb_dim = settings.model.price_emb_dim
        self.out_dim = settings.model.item_emb_dim

        self.category_embedding = nn.Embedding(
            num_embeddings=self.num_categories + 1,
            embedding_dim=self.category_emb_dim,
            padding_idx=0,
        )
        self.price_embedding = nn.Embedding(
            num_embeddings=self.num_price_buckets + 1,
            embedding_dim=self.price_emb_dim,
            padding_idx=0,
        )

        self.sbert_proj = nn.Linear(self.sbert_dim, 64)

        in_features = 64 + self.category_emb_dim + self.price_emb_dim  # 64 + 16 + 8 = 88
        self.fc1 = nn.Linear(in_features, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, self.out_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        nn.init.normal_(self.category_embedding.weight, std=0.01)
        nn.init.zeros_(self.category_embedding.weight[0])

        nn.init.normal_(self.price_embedding.weight, std=0.01)
        nn.init.zeros_(self.price_embedding.weight[0])

        nn.init.kaiming_normal_(self.sbert_proj.weight, nonlinearity="relu")
        nn.init.zeros_(self.sbert_proj.bias)

        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity="relu")
        nn.init.zeros_(self.fc1.bias)

        nn.init.xavier_normal_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(
        self,
        sbert_emb: torch.Tensor,
        cat_idx: torch.Tensor,
        price_idx: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass generating L2-normalized item vectors [..., 64]."""
        sbert_proj = self.sbert_proj(sbert_emb)       # [..., 64]
        cat_emb = self.category_embedding(cat_idx)    # [..., 16]
        price_emb = self.price_embedding(price_idx)  # [..., 8]

        x = torch.cat([sbert_proj, cat_emb, price_emb], dim=-1) # [..., 88]
        x = self.fc1(x)                                        # [..., 64]
        x = self.relu(x)
        x = self.fc2(x)                                        # [..., 64]

        return F.normalize(x, p=2, dim=-1, eps=1e-8)
