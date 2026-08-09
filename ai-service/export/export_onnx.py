"""Lightweight ONNX Exporter module for ai-service.

Exports User Tower, Item Tower, Wide Layer, and full HybridTwoTowerModel to optimized ONNX format for sub-millisecond production candidate reranking (< 1.0 ms warm serving budget).
"""

from pathlib import Path
import time
from typing import Dict, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn

try:
    import onnx
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

from config import get_settings, RUN_ARTIFACTS_DIR
from models.two_tower_wide_deep import HybridTwoTowerModel


class UserTowerONNXWrapper(nn.Module):
    """Wrapper for exporting User Tower to ONNX."""

    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.user_tower = model.user_tower

    def forward(self, user_idx: torch.Tensor, persona_idx: torch.Tensor) -> torch.Tensor:
        return self.user_tower(user_idx, persona_idx)


class ItemTowerONNXWrapper(nn.Module):
    """Wrapper for exporting Item Tower to ONNX."""

    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.item_tower = model.item_tower

    def forward(
        self, sbert: torch.Tensor, category_idx: torch.Tensor, price_idx: torch.Tensor
    ) -> torch.Tensor:
        return self.item_tower(sbert, category_idx, price_idx)


class WideLayerONNXWrapper(nn.Module):
    """Wrapper for exporting Wide Layer to ONNX."""

    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.wide_layer = model.wide_layer

    def forward(self, log_lift: torch.Tensor) -> torch.Tensor:
        return self.wide_layer(log_lift)


class HybridModelONNXWrapper(nn.Module):
    """Wrapper for exporting end-to-end Candidate Reranking Score to ONNX."""

    def __init__(self, model: HybridTwoTowerModel):
        super().__init__()
        self.model = model

    def forward(
        self,
        user_vectors: torch.Tensor,
        item_vectors: torch.Tensor,
        log_lift: torch.Tensor,
    ) -> torch.Tensor:
        scores = self.model.score_candidates(user_vectors, item_vectors, log_lift, use_wide=True)
        return scores.logits


def export_user_tower_onnx(model: HybridTwoTowerModel, save_path: Path) -> Path:
    """Export User Tower to ONNX with dynamic batch size."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = UserTowerONNXWrapper(model).eval()

    dummy_user_idx = torch.tensor([1, 42], dtype=torch.long)
    dummy_persona_idx = torch.tensor([0, 2], dtype=torch.long)

    torch.onnx.export(
        wrapper,
        (dummy_user_idx, dummy_persona_idx),
        str(save_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["user_idx", "persona_idx"],
        output_names=["user_vector"],
        dynamic_axes={
            "user_idx": {0: "batch_size"},
            "persona_idx": {0: "batch_size"},
            "user_vector": {0: "batch_size"},
        },
    )

    if HAS_ONNX:
        onnx_model = onnx.load(str(save_path))
        onnx.checker.check_model(onnx_model)

    return save_path


def export_item_tower_onnx(model: HybridTwoTowerModel, save_path: Path) -> Path:
    """Export Item Tower to ONNX supporting arbitrary candidate dimensions."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = ItemTowerONNXWrapper(model).eval()

    dummy_sbert = torch.randn(2, 5, 768)
    dummy_cat = torch.randint(0, 41, (2, 5))
    dummy_price = torch.randint(0, 9, (2, 5))

    torch.onnx.export(
        wrapper,
        (dummy_sbert, dummy_cat, dummy_price),
        str(save_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["sbert_embedding", "category_idx", "price_idx"],
        output_names=["item_vector"],
        dynamic_axes={
            "sbert_embedding": {0: "batch_size", 1: "num_candidates"},
            "category_idx": {0: "batch_size", 1: "num_candidates"},
            "price_idx": {0: "batch_size", 1: "num_candidates"},
            "item_vector": {0: "batch_size", 1: "num_candidates"},
        },
    )

    if HAS_ONNX:
        onnx_model = onnx.load(str(save_path))
        onnx.checker.check_model(onnx_model)

    return save_path


def export_wide_layer_onnx(model: HybridTwoTowerModel, save_path: Path) -> Path:
    """Export Wide Layer to ONNX with dynamic candidate shape."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = WideLayerONNXWrapper(model).eval()

    dummy_log_lift = torch.randn(2, 5, 1)

    torch.onnx.export(
        wrapper,
        (dummy_log_lift,),
        str(save_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["log_lift"],
        output_names=["wide_score"],
        dynamic_axes={
            "log_lift": {0: "batch_size", 1: "num_candidates"},
            "wide_score": {0: "batch_size", 1: "num_candidates"},
        },
    )

    if HAS_ONNX:
        onnx_model = onnx.load(str(save_path))
        onnx.checker.check_model(onnx_model)

    return save_path


def export_full_hybrid_onnx(model: HybridTwoTowerModel, save_path: Path) -> Path:
    """Export Full Candidate Scoring Wrapper to ONNX for production candidate reranking."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    wrapper = HybridModelONNXWrapper(model).eval()

    dummy_user_vec = torch.randn(2, 64)
    dummy_item_vec = torch.randn(2, 5, 64)
    dummy_log_lift = torch.randn(2, 5, 1)

    torch.onnx.export(
        wrapper,
        (dummy_user_vec, dummy_item_vec, dummy_log_lift),
        str(save_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["user_vector", "item_vector", "log_lift"],
        output_names=["logits"],
        dynamic_axes={
            "user_vector": {0: "batch_size"},
            "item_vector": {0: "batch_size", 1: "num_candidates"},
            "log_lift": {0: "batch_size", 1: "num_candidates"},
            "logits": {0: "batch_size", 1: "num_candidates"},
        },
    )

    if HAS_ONNX:
        onnx_model = onnx.load(str(save_path))
        onnx.checker.check_model(onnx_model)

    return save_path


def export_all_onnx_models(
    model: HybridTwoTowerModel, export_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """Export all 4 ONNX model files to export_dir."""
    if export_dir is None:
        export_dir = RUN_ARTIFACTS_DIR / "main" / "onnx"
    export_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "user_tower": export_user_tower_onnx(model, export_dir / "user_tower.onnx"),
        "item_tower": export_item_tower_onnx(model, export_dir / "item_tower.onnx"),
        "wide_layer": export_wide_layer_onnx(model, export_dir / "wide_layer.onnx"),
        "hybrid_recommender": export_full_hybrid_onnx(
            model, export_dir / "hybrid_recommender.onnx"
        ),
    }
    return paths
