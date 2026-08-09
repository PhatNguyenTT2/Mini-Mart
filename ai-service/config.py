"""Configuration management for ai-service.

Provides typed immutable configuration settings for Data Ingestion, Model Architecture,
Training, Evaluation, and Serving microservice.
"""

from pathlib import Path
import random
import os
from typing import Optional
import numpy as np
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for ai-service module
BASE_DIR: Path = Path(__file__).resolve().parent
ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"
DATA_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "data"
RUN_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "runs"
MODEL_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "model"


class DataConfig(BaseSettings):
    """Data Pipeline and Ingestion settings."""

    store_id: int = Field(default=1, description="Default target store ID")
    num_users: int = Field(default=5000, description="Mapped known users count")
    num_items: int = Field(default=5200, description="Mapped product catalog count")
    num_personas: int = Field(default=8, description="Persona clusters count (0..7)")
    num_leaf_categories: int = Field(
        default=40, description="Catalog leaf categories count (excluding UNK row 0)"
    )
    num_price_buckets: int = Field(
        default=8, description="Quantile price buckets count (excluding UNK row 0)"
    )
    database_url: Optional[str] = Field(
        default=None, alias="CHATBOT_DATABASE_URL", description="PostgreSQL database URL for Chatbot/ML events"
    )
    catalog_database_url: Optional[str] = Field(
        default=None, alias="CATALOG_DATABASE_URL", description="PostgreSQL database URL for Catalog DB"
    )
    order_database_url: Optional[str] = Field(
        default=None, alias="ORDER_DATABASE_URL", description="PostgreSQL database URL for Order DB"
    )
    snapshot_id: str = Field(default="scaled-v1", description="Dataset snapshot identifier")
    min_rule_count: int = Field(default=3, description="Minimum co-purchase count for Apriori rules")
    min_rule_lift: float = Field(default=1.0, description="Minimum lift threshold for active rules")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ModelConfig(BaseSettings):
    """Model Architecture Hyperparameters."""

    user_emb_dim: int = Field(default=64, description="User ID embedding dimension")
    persona_emb_dim: int = Field(default=8, description="Persona Cluster embedding dimension")
    category_emb_dim: int = Field(default=16, description="Leaf Category embedding dimension")
    price_emb_dim: int = Field(default=8, description="Price Bucket embedding dimension")
    sbert_dim: int = Field(default=768, description="Frozen SBERT raw embedding dimension")
    item_emb_dim: int = Field(default=64, description="Final Item embedding dimension")
    tau: float = Field(default=0.1, description="Temperature scaling hyperparameter")

    @field_validator("tau")
    @classmethod
    def validate_tau(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Temperature tau must be strictly positive (> 0)")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class TrainConfig(BaseSettings):
    """Training Engine & Optimizer Hyperparameters."""

    batch_size: int = Field(default=2048, description="Batch size for training")
    negative_ratio: int = Field(default=4, description="Negative sampling ratio (1 positive : N negatives)")
    lr: float = Field(default=1e-3, description="Adam optimizer learning rate")
    weight_decay: float = Field(default=1e-5, description="Adam optimizer weight decay")
    max_epochs: int = Field(default=30, description="Maximum training epochs")
    early_stopping_patience: int = Field(
        default=4, description="Patience epochs for early stopping on Validation GAUC"
    )
    min_delta: float = Field(default=1e-4, description="Minimum GAUC delta for early stopping")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    max_grad_norm: float = Field(default=5.0, description="Maximum gradient clipping norm")

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("batch_size must be positive")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class EvalConfig(BaseSettings):
    """Full-catalog & Benchmark Evaluation settings."""

    k: int = Field(default=10, description="Top-K metric rank cut-off")
    eval_user_batch_size: int = Field(default=512, description="User chunk size for full-catalog GPU matmul")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ServingConfig(BaseSettings):
    """Production FastAPI Serving settings."""

    service_name: str = "ai-service"
    model_version: str = "two_tower_v1"
    host: str = "0.0.0.0"
    port: int = 8000
    max_candidates: int = Field(default=256, description="Maximum allowed candidate products per request")

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=("settings_",)
    )


class Settings(BaseSettings):
    """Master aggregated settings container."""

    data: DataConfig = Field(default_factory=DataConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    train: TrainConfig = Field(default_factory=TrainConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    serving: ServingConfig = Field(default_factory=ServingConfig)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_cached_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Retrieve or initialize singleton application settings."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
        # Ensure default directories exist
        DATA_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        RUN_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        MODEL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return _cached_settings


def set_seed(seed: int = 42) -> None:
    """Set deterministic random seed across Python, NumPy, PyTorch, and CUDA."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
