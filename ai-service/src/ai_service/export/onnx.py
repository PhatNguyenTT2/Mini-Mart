"""Export the offline item encoder and online hybrid ranker graphs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from ai_service.config import Settings
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


class ItemEncoderGraph(nn.Module):
    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.item_tower = model.item_tower

    def forward(
        self,
        sbert: torch.Tensor,
        category_idx: torch.Tensor,
        price_idx: torch.Tensor,
        item_idx: torch.Tensor,
        is_cold: torch.Tensor,
    ) -> torch.Tensor:
        return self.item_tower.encode_unchecked(
            sbert,
            category_idx,
            price_idx,
            item_idx,
            is_cold,
        )


class RankerGraph(nn.Module):
    temperature: torch.Tensor

    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.user_tower = model.user_tower
        self.wide_layer = model.wide_layer
        self.register_buffer("temperature", model._temperature.detach().clone())

    def forward(
        self,
        user_idx: torch.Tensor,
        persona_idx: torch.Tensor,
        history_vector: torch.Tensor,
        history_present: torch.Tensor,
        candidate_vectors: torch.Tensor,
        wide_values: torch.Tensor,
        rule_present: torch.Tensor,
    ) -> torch.Tensor:
        user_vectors = self.user_tower.encode_unchecked(
            user_idx,
            persona_idx,
            history_vector,
            history_present,
        )
        deep = (
            torch.matmul(candidate_vectors, user_vectors.unsqueeze(-1)).squeeze(-1)
            / self.temperature
        )
        wide = self.wide_layer.score_unchecked(wide_values, rule_present)
        return deep + wide


@dataclass(frozen=True)
class OnnxPaths:
    item_encoder: Path
    ranker: Path


def export_onnx_models(
    model: HybridTwoTowerModel,
    settings: Settings,
    output_dir: Path,
) -> OnnxPaths:
    output_dir.mkdir(parents=True, exist_ok=False)
    model = model.cpu().eval()
    item_path = output_dir / "item_encoder.onnx"
    ranker_path = output_dir / "ranker.onnx"
    items = torch.export.Dim("items", min=1)
    batch = torch.export.Dim("batch", min=1)
    candidates = torch.export.Dim("candidates", min=1)
    item_graph = ItemEncoderGraph(model).eval()
    ranker_graph = RankerGraph(model).eval()
    with torch.no_grad():
        torch.onnx.export(
            item_graph,
            (
                torch.zeros(4, settings.model.sbert_dim, dtype=torch.float32),
                torch.ones(4, dtype=torch.int64),
                torch.ones(4, dtype=torch.int64),
                torch.arange(4, dtype=torch.int64),
                torch.zeros(4, dtype=torch.bool),
            ),
            item_path,
            input_names=["sbert", "category_idx", "price_idx", "item_idx", "is_cold"],
            output_names=["item_vectors"],
            dynamic_shapes=({0: items}, {0: items}, {0: items}, {0: items}, {0: items}),
            opset_version=18,
            dynamo=True,
            external_data=False,
        )
        torch.onnx.export(
            ranker_graph,
            (
                torch.ones(2, dtype=torch.int64),
                torch.ones(2, dtype=torch.int64),
                torch.zeros(2, settings.model.item_emb_dim, dtype=torch.float32),
                torch.zeros(2, dtype=torch.bool),
                torch.zeros(2, 3, settings.model.item_emb_dim, dtype=torch.float32),
                torch.zeros(2, 3, 3, dtype=torch.float32),
                torch.zeros(2, 3, dtype=torch.bool),
            ),
            ranker_path,
            input_names=[
                "user_idx",
                "persona_idx",
                "history_vector",
                "history_present",
                "candidate_vectors",
                "wide_values",
                "rule_present",
            ],
            output_names=["logits"],
            dynamic_shapes=(
                {0: batch},
                {0: batch},
                {0: batch},
                {0: batch},
                {0: batch, 1: candidates},
                {0: batch, 1: candidates},
                {0: batch, 1: candidates},
            ),
            opset_version=18,
            dynamo=True,
            external_data=False,
        )
    return OnnxPaths(item_encoder=item_path, ranker=ranker_path)
