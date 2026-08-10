"""User and persona encoder."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from ai_service.config import Settings


def _require_integer_vector(name: str, value: torch.Tensor) -> None:
    if value.dtype != torch.int64 or value.ndim != 1:
        raise ValueError(f"{name} must be int64 [B]")


class UserTower(nn.Module):
    def __init__(self, settings: Settings):
        super().__init__()
        self.max_user = settings.data.num_users
        self.unknown_persona = settings.data.num_personas
        self.item_emb_dim = settings.model.item_emb_dim
        self.user_id_dropout = settings.model.user_id_dropout
        self.user_embedding = nn.Embedding(
            settings.data.num_users + 1,
            settings.model.user_emb_dim,
            padding_idx=0,
        )
        self.persona_embedding = nn.Embedding(
            settings.data.num_personas + 1,
            settings.model.persona_emb_dim,
        )
        self.network = nn.Sequential(
            nn.Linear(
                settings.model.user_emb_dim
                + settings.model.persona_emb_dim
                + settings.model.item_emb_dim
                + 1,
                128,
            ),
            nn.ReLU(),
            nn.LayerNorm(128),
            nn.Linear(128, settings.model.item_emb_dim),
        )
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        with torch.no_grad():
            self.user_embedding.weight[0].zero_()

    def encode_unchecked(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> torch.Tensor:
        user_embedding = F.dropout(
            self.user_embedding(user_idx), p=self.user_id_dropout, training=self.training
        )
        if history_vector is None:
            history_vector = torch.zeros(
                (*user_idx.shape, self.item_emb_dim),
                dtype=user_embedding.dtype,
                device=user_embedding.device,
            )
        if history_present is None:
            history_present = torch.zeros_like(user_idx, dtype=torch.bool)
        encoded = self.network(
            torch.cat(
                (
                    user_embedding,
                    self.persona_embedding(persona_idx),
                    history_vector,
                    history_present.to(user_embedding.dtype).unsqueeze(-1),
                ),
                dim=-1,
            )
        )
        return F.normalize(encoded, p=2, dim=-1, eps=1e-8)

    def forward(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        *,
        history_vector: torch.Tensor | None = None,
        history_present: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if not torch.jit.is_tracing():  # type: ignore[attr-defined,no-untyped-call]
            _require_integer_vector("user_idx", user_idx)
            _require_integer_vector("persona_idx", persona_idx)
            if user_idx.shape != persona_idx.shape:
                raise ValueError("user and persona shapes differ")
            if bool((user_idx < 0).any()) or bool((user_idx > self.max_user).any()):
                raise ValueError("user_idx is outside configured range")
            if bool((persona_idx < 0).any()) or bool((persona_idx > self.unknown_persona).any()):
                raise ValueError("persona_idx is outside configured range")
            if history_vector is not None and history_vector.shape != (
                len(user_idx),
                self.item_emb_dim,
            ):
                raise ValueError("history_vector must have shape [B,item_emb_dim]")
            if history_present is not None and (
                history_present.dtype != torch.bool or history_present.shape != user_idx.shape
            ):
                raise ValueError("history_present must be bool [B]")
        result = self.encode_unchecked(user_idx, persona_idx, history_vector, history_present)
        if not torch.jit.is_tracing() and not bool(  # type: ignore[attr-defined,no-untyped-call]
            torch.isfinite(result).all()
        ):
            raise ValueError("user tower output must be finite")
        return result
