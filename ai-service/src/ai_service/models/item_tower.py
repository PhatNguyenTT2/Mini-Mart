"""Catalog feature encoder."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from ai_service.config import Settings


class ItemTower(nn.Module):
    def __init__(self, settings: Settings):
        super().__init__()
        self.sbert_dim = settings.model.sbert_dim
        self.max_category = settings.data.num_leaf_categories
        self.max_price = settings.data.num_price_buckets
        self.max_item = settings.data.num_items
        self.use_item_id_residual = settings.model.use_item_id_residual
        self.use_price_features = settings.model.use_price_features
        self.category_embedding = nn.Embedding(
            self.max_category + 1,
            settings.model.category_emb_dim,
            padding_idx=0,
        )
        self.price_embedding: nn.Embedding | None = None
        if self.use_price_features:
            self.price_embedding = nn.Embedding(
                self.max_price + 1,
                settings.model.price_emb_dim,
                padding_idx=0,
            )
        self.sbert_projection = nn.Linear(settings.model.sbert_dim, 64)
        self.network = nn.Sequential(
            nn.Linear(
                64
                + settings.model.category_emb_dim
                + (settings.model.price_emb_dim if self.use_price_features else 0),
                64,
            ),
            nn.ReLU(),
            nn.Linear(64, settings.model.item_emb_dim),
        )
        self.item_embedding = nn.Embedding(
            settings.data.num_items + 1,
            settings.model.item_emb_dim,
            padding_idx=0,
        )
        self.residual_gate = nn.Parameter(torch.tensor(0.0))
        nn.init.normal_(self.item_embedding.weight, std=0.01)
        with torch.no_grad():
            self.item_embedding.weight[0].zero_()

    def encode_unchecked(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
        item_idx: torch.Tensor | None = None,
        is_cold: torch.Tensor | None = None,
    ) -> torch.Tensor:
        feature_parts = [self.sbert_projection(sbert), self.category_embedding(category_idx)]
        if self.price_embedding is not None:
            feature_parts.append(self.price_embedding(price_idx))
        features = torch.cat(feature_parts, dim=-1)
        encoded = self.network(features)
        if self.use_item_id_residual and item_idx is not None:
            residual = self.item_embedding(item_idx + 1) * torch.sigmoid(self.residual_gate)
            if is_cold is not None:
                residual = torch.where(is_cold.unsqueeze(-1), torch.zeros_like(residual), residual)
            encoded = encoded + residual
        return F.normalize(encoded, p=2, dim=-1, eps=1e-8)

    def forward(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
        *,
        item_idx: torch.Tensor | None = None,
        is_cold: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not torch.jit.is_tracing():  # type: ignore[attr-defined,no-untyped-call]
            if sbert.ndim < 2 or sbert.shape[-1] != self.sbert_dim:
                raise ValueError(f"sbert must end in dimension {self.sbert_dim}")
            if category_idx.dtype != torch.int64 or price_idx.dtype != torch.int64:
                raise ValueError("category and price indices must be int64")
            if sbert.shape[:-1] != category_idx.shape or category_idx.shape != price_idx.shape:
                raise ValueError("item feature shapes differ")
            if not bool(torch.isfinite(sbert).all()):
                raise ValueError("sbert input must be finite")
            if bool((category_idx < 0).any()) or bool((category_idx > self.max_category).any()):
                raise ValueError("category index is outside configured range")
            if bool((price_idx < 0).any()) or bool((price_idx > self.max_price).any()):
                raise ValueError("price index is outside configured range")
            if item_idx is not None:
                if item_idx.dtype != torch.int64 or item_idx.shape != category_idx.shape:
                    raise ValueError("item_idx must be int64 with the categorical feature shape")
                if bool((item_idx < 0).any()) or bool((item_idx >= self.max_item).any()):
                    raise ValueError("item index is outside configured range")
            if is_cold is not None and (
                is_cold.dtype != torch.bool or is_cold.shape != category_idx.shape
            ):
                raise ValueError("is_cold must be bool with the categorical feature shape")
        result = self.encode_unchecked(sbert, category_idx, price_idx, item_idx, is_cold)
        if not torch.jit.is_tracing() and not bool(  # type: ignore[attr-defined,no-untyped-call]
            torch.isfinite(result).all()
        ):
            raise ValueError("item tower output must be finite")
        return result
