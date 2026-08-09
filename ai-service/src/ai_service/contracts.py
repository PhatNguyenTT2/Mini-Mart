"""Central data and domain contracts for ai_service module."""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field


class SplitName(str, Enum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


class ModelVariant(str, Enum):
    HYBRID = "hybrid"
    DEEP_ONLY = "deep_only"
    WIDE_ONLY = "wide_only"
    SBERT_CENTROID = "sbert_centroid"
    ITEM_CF = "item_cf"
    NOISY_HYBRID = "noisy_hybrid"
    RANDOM = "random"


class EmbeddingSource(str, Enum):
    REAL = "real"
    MOCK = "mock"


class ContextRef(BaseModel):
    item_idx: int = Field(default=-1, description="Internal product index or -1 if missing")
    present: bool = Field(default=False, description="True if a valid context item exists")


from datetime import datetime, timezone

class SnapshotManifestV2(BaseModel):
    version: str = "2.0.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    store_id: int
    source_kind: str
    num_events: int
    num_users: int
    num_items: int
    num_cold_items: int
    train_count: int
    val_count: int
    test_count: int
    train_max_ts: str
    val_min_ts: str
    val_max_ts: str
    test_min_ts: str
    checksum: str


class EmbeddingManifestV2(BaseModel):
    version: str = "2.0.0"
    source_kind: EmbeddingSource
    model_name: str
    embedding_dim: int
    num_items: int
    checksum: str


class RuleManifestV2(BaseModel):
    version: str = "2.0.0"
    num_rules: int
    min_support: float
    min_confidence: float
    min_lift: float
    train_basket_count: int
    checksum: str


class RunManifestV2(BaseModel):
    version: str = "2.0.0"
    run_id: str
    trained_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    epochs_trained: int
    best_epoch: int
    best_val_gauc: float
    model_variant: ModelVariant
    checkpoint_checksum: str


class ModelBundleManifestV2(BaseModel):
    version: str = "2.0.0"
    bundle_id: str
    onnx_recommender_checksum: str
    onnx_user_tower_checksum: str
    onnx_item_tower_checksum: str
    onnx_wide_layer_checksum: str
    latency_p95_ms: float
