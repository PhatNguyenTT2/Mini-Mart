"""Item Tower module for ai-service.

Encodes Text SBERT projection (768d -> 64d), Leaf Category Embedding (41 x 16d), and Price Bucket Embedding (9 x 8d) into a 64-dimensional L2-normalized item embedding vector.
Supports arbitrary leading dimensions for single candidates, candidate groups [B, C], or full catalog tensors.
"""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

from config import get_settings, Settings


class ItemTower(nn.Module):
    """Item Tower neural network encoding SBERT text, Leaf Category, and Price Bucket into 64d L2-normalized vector."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        if settings is None:
            settings = get_settings()

        self.sbert_dim = settings.model.sbert_dim  # 768
        self.num_categories = settings.data.num_leaf_categories + 1  # 41 (row 0 = UNK)
        self.num_price_buckets = settings.data.num_price_buckets + 1  # 9 (row 0 = UNK)

        self.category_emb_dim = settings.model.category_emb_dim  # 16
        self.price_emb_dim = settings.model.price_emb_dim  # 8
        self.item_emb_dim = settings.model.item_emb_dim  # 64

        # Projection for frozen SBERT text embedding (768 -> 64)
        self.sbert_proj = nn.Linear(self.sbert_dim, self.item_emb_dim)

        # Categorical Embeddings
        self.category_embedding = nn.Embedding(
            self.num_categories, self.category_emb_dim, padding_idx=0
        )
        self.price_embedding = nn.Embedding(
            self.num_price_buckets, self.price_emb_dim, padding_idx=0
        )

        # Item MLP: 88 (64 + 16 + 8) -> 64 -> ReLU -> 64
        in_features = self.item_emb_dim + self.category_emb_dim + self.price_emb_dim  # 88
        self.fc1 = nn.Linear(in_features, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, self.item_emb_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights with Xavier uniform for linear layers and normal for embeddings."""
        nn.init.xavier_uniform_(self.sbert_proj.weight)
        nn.init.zeros_(self.sbert_proj.bias)

        nn.init.normal_(self.category_embedding.weight, std=0.01)
        nn.init.normal_(self.price_embedding.weight, std=0.01)

        # Row 0 UNK embeddings zeroed initially
        with torch.no_grad():
            self.category_embedding.weight[0].fill_(0.0)
            self.price_embedding.weight[0].fill_(0.0)

        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass generating L2-normalized item vectors for arbitrary leading tensor shapes.

        Args:
            sbert: Tensor of pre-computed SBERT embeddings [..., 768]
            category_idx: Tensor of category indices [...] in 0..40 (0=UNK)
            price_idx: Tensor of price bucket indices [...] in 0..8 (0=UNK)

        Returns:
            Tensor of L2-normalized item embeddings [..., 64]
        """
        orig_shape = sbert.shape[:-1]

        # Flatten leading dimensions for uniform MLP processing
        sbert_flat = sbert.reshape(-1, self.sbert_dim)
        cat_flat = category_idx.reshape(-1)
        price_flat = price_idx.reshape(-1)

        # Clamp indices to valid range
        cat_clamped = torch.where(
            (cat_flat >= 0) & (cat_flat < self.num_categories),
            cat_flat,
            torch.zeros_like(cat_flat),
        )
        price_clamped = torch.where(
            (price_flat >= 0) & (price_flat < self.num_price_buckets),
            price_flat,
            torch.zeros_like(price_flat),
        )

        s_proj = self.sbert_proj(sbert_flat)  # [N, 64]
        c_emb = self.category_embedding(cat_clamped)  # [N, 16]
        p_emb = self.price_embedding(price_clamped)  # [N, 8]

        concat = torch.cat([s_proj, c_emb, p_emb], dim=-1)  # [N, 88]

        h1 = self.fc1(concat)  # [N, 64]
        h1_act = self.relu(h1)  # [N, 64]
        h2 = self.fc2(h1_act)  # [N, 64]

        # L2 Normalization with epsilon protection
        out_flat = F.normalize(h2, p=2, dim=-1, eps=1e-12)  # [N, 64]

        # Restore original leading tensor dimensions
        final_shape = orig_shape + (self.item_emb_dim,)
        return out_flat.reshape(final_shape)
