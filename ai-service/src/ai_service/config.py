"""Typed immutable configuration settings for ai_service module."""

from pathlib import Path
from typing import Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for ai_service package
PACKAGE_DIR: Path = Path(__file__).resolve().parent
SERVICE_DIR: Path = PACKAGE_DIR.parent.parent
ARTIFACTS_DIR: Path = SERVICE_DIR / "artifacts"
DATA_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "data"
RUN_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "runs"
MODEL_ARTIFACTS_DIR: Path = ARTIFACTS_DIR / "model"


class DataConfig(BaseSettings):
    """Data Ingestion & Artifacts Configuration."""

    store_id: int = Field(default=1, description="Default target store ID")
    snapshot_id: str = Field(default="scaled-v1", description="Dataset snapshot identifier")
    num_users: int = Field(default=5000, description="Mapped known users count")
    num_items: int = Field(default=5200, description="Mapped product catalog count")
    num_cold_items: int = Field(default=250, description="Cold-start reserved products count")
    num_personas: int = Field(default=8, description="Persona clusters count (0..7)")
    num_leaf_categories: int = Field(default=40, description="Catalog leaf categories count")
    num_price_buckets: int = Field(default=8, description="Quantile price buckets count")
    
    database_url: Optional[SecretStr] = Field(
        default=None, alias="CHATBOT_DATABASE_URL", description="PostgreSQL DSN for ML events"
    )
    catalog_database_url: Optional[SecretStr] = Field(
        default=None, alias="CATALOG_DATABASE_URL", description="PostgreSQL DSN for Catalog DB"
    )
    order_database_url: Optional[SecretStr] = Field(
        default=None, alias="ORDER_DATABASE_URL", description="PostgreSQL DSN for Order DB"
    )
    
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
    """Training Engine Hyperparameters."""

    batch_size: int = Field(default=2048, description="Batch size for training")
    negative_ratio: int = Field(default=4, description="Negative sampling ratio (1 positive : N negatives)")
    lr: float = Field(default=1e-3, description="Adam optimizer learning rate")
    weight_decay: float = Field(default=1e-5, description="Adam optimizer weight decay")
    max_epochs: int = Field(default=30, description="Maximum training epochs")
    early_stopping_patience: int = Field(default=4, description="Patience epochs for early stopping")
    min_delta: float = Field(default=1e-4, description="Minimum GAUC delta for early stopping")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    max_grad_norm: float = Field(default=5.0, description="Maximum gradient clipping norm")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class EvalConfig(BaseSettings):
    """Full-catalog & Benchmark Evaluation settings."""

    k: int = Field(default=10, description="Top-K cutoff for HR@K and NDCG@K")
    split: str = Field(default="test", description="Default evaluation split (val or test)")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ServingConfig(BaseSettings):
    """FastAPI & ONNX Runtime Serving Microservice Configuration."""

    host: str = Field(default="0.0.0.0", description="Serving host interface")
    port: int = Field(default=8000, description="Serving HTTP port")
    workers: int = Field(default=1, description="Uvicorn worker count")
    model_version: str = Field(default="v2.0.0", description="Serving model version identifier")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())


class Settings:
    """Master aggregated settings for ai_service."""

    def __init__(self):
        self.data = DataConfig()
        self.model = ModelConfig()
        self.train = TrainConfig()
        self.eval = EvalConfig()
        self.serving = ServingConfig()


def get_settings() -> Settings:
    """Return Settings singleton."""
    return Settings()
