"""Validated application configuration with fail-closed production semantics."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai_service.contracts import TrainingVariant
from ai_service.errors import ConfigurationError

MIN_TEMPERATURE = 1e-3
MODEL_SCHEMA_VERSION = "5.0.0"
PINNED_SBERT_NAME = "keepitreal/vietnamese-sbert"
PINNED_SBERT_REVISION = "a9467ef2ef47caa6448edeabfd8e5e5ce0fa2a23"


class DataConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    store_id: int = Field(default=1, alias="AI_STORE_ID", gt=0)
    snapshot_id: str = Field(
        default="benchmark-local",
        alias="AI_SNAPSHOT_ID",
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    )
    artifact_root: Path = Field(default=Path("artifacts"), alias="AI_ARTIFACT_ROOT")
    model_bundle_path: Path | None = Field(default=None, alias="AI_MODEL_BUNDLE_PATH")
    chatbot_database_url: SecretStr | None = Field(default=None, alias="CHATBOT_DATABASE_URL")
    catalog_database_url: SecretStr | None = Field(default=None, alias="CATALOG_DATABASE_URL")
    order_database_url: SecretStr | None = Field(default=None, alias="ORDER_DATABASE_URL")
    database_ssl_root_cert: Path | None = Field(default=None, alias="SUPABASE_DB_CA_PATH")
    benchmark_run_id: str | None = Field(default=None, alias="AI_BENCHMARK_RUN_ID")
    num_users: int = Field(default=5_000, gt=0)
    num_items: int = Field(default=5_200, gt=0)
    expected_event_count: int = Field(default=823_371, gt=0)
    expected_train_count: int = Field(default=658_697, gt=0)
    expected_val_count: int = Field(default=82_337, gt=0)
    expected_test_count: int = Field(default=82_337, gt=0)
    expected_order_count: int = Field(default=15_000, gt=0)
    num_cold_items: int = Field(default=250, ge=0)
    num_personas: int = Field(default=8, gt=0)
    num_leaf_categories: int = Field(default=40, gt=0)
    num_price_buckets: int = Field(default=8, gt=0)
    min_rule_count: int = Field(default=3, gt=0)
    min_rule_lift: float = Field(default=1.0, ge=0.0)
    rule_feature_schema_version: Literal["2.0.0", "3.0.0"] = "2.0.0"
    minimum_non_trap_directed_rules: int = Field(default=0, ge=0)
    minimum_distinct_organic_rule_items: int = Field(default=0, ge=0)
    minimum_val_context_rule_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    minimum_training_target_rule_rate: float = Field(default=0.40, ge=0.0, le=1.0)
    minimum_val_rule_target_rate: float = Field(default=0.40, ge=0.0, le=1.0)
    minimum_training_rows_with_any_rule: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_trap_anchored_rule_fraction: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_split_counts(self) -> DataConfig:
        actual = self.expected_train_count + self.expected_val_count + self.expected_test_count
        if actual != self.expected_event_count:
            raise ValueError("expected temporal split counts must sum to expected_event_count")
        return self


class ModelConfig(BaseModel):
    sbert_model_name: str = "keepitreal/vietnamese-sbert"
    sbert_model_revision: str = Field(
        default="a9467ef2ef47caa6448edeabfd8e5e5ce0fa2a23",
        pattern=r"^[0-9a-f]{40}$",
    )
    user_emb_dim: int = Field(default=64, gt=0)
    persona_emb_dim: int = Field(default=8, gt=0)
    category_emb_dim: int = Field(default=16, gt=0)
    price_emb_dim: int = Field(default=8, gt=0)
    sbert_dim: int = Field(default=768, gt=0)
    item_emb_dim: int = Field(default=64, gt=0)
    user_id_dropout: float = Field(default=0.1, ge=0.0, lt=1.0)
    use_item_id_residual: bool = True
    use_user_id_embedding: bool = True
    use_price_features: bool = True
    tau: float = Field(default=0.1)

    @field_validator("tau")
    @classmethod
    def validate_tau(cls, value: float) -> float:
        if value < MIN_TEMPERATURE:
            raise ValueError("tau must be >= 1e-3")
        return value


class TrainConfig(BaseModel):
    objective: Literal["sampled_softmax", "legacy_bce", "purchase_bce"] = "sampled_softmax"
    training_variant: TrainingVariant = TrainingVariant.HYBRID
    batch_size: int = Field(default=2_048, gt=0)
    negative_ratio: int = Field(default=4, ge=1)
    explicit_negative_ratio: int = Field(default=16, ge=4)
    learning_rate: float = Field(default=3e-4, gt=0)
    minimum_learning_rate: float = Field(default=1e-5, gt=0)
    weight_decay: float = Field(default=1e-5, ge=0)
    max_epochs: int = Field(default=30, gt=0)
    early_stopping_patience: int = Field(default=4, gt=0)
    min_delta: float = Field(default=1e-4, ge=0)
    warmup_fraction: float = Field(default=0.05, ge=0.0, lt=1.0)
    view_auxiliary_weight: float = Field(default=0.0, ge=0.0)
    use_history_profiles: bool = True
    seed: int = 42
    max_grad_norm: float = Field(default=5.0, gt=0)
    validation_user_batch_size: int = Field(default=512, gt=0)
    max_history_items: int = Field(default=32, ge=1)
    max_wall_minutes: int = Field(default=90, ge=1)
    campaign_stage: Literal["legacy", "diagnostic", "production"] = "legacy"
    r3_selection_artifact_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    rule_auxiliary_weight: float = Field(default=0.0, ge=0.0)
    rule_hard_negative_count: int = Field(default=0, ge=0)
    diagnostic_warmup_epochs: int = Field(default=3, ge=1)
    diagnostic_minimum_gauc: float = Field(default=0.65, ge=0.5, le=1.0)
    diagnostic_minimum_hr_at_k: float = Field(default=0.10, ge=0.0, le=1.0)
    diagnostic_minimum_ndcg_at_k: float = Field(default=0.04, ge=0.0, le=1.0)
    r3_feature_selection_mode: Literal["fixed", "selection_artifact"] = "fixed"

    @model_validator(mode="after")
    def validate_training_schedule(self) -> TrainConfig:
        if self.minimum_learning_rate > self.learning_rate:
            raise ValueError("minimum_learning_rate must not exceed learning_rate")
        return self


class EvalConfig(BaseModel):
    k: Literal[10] = 10
    bootstrap_samples: int = Field(default=2_000, gt=0)
    random_seeds: Literal[10] = 10
    primary_metric: Literal["gauc"] = "gauc"
    aggregate_gauc_min_delta: float = Field(default=0.0, ge=0.0)
    aggregate_hr_min_delta: float = Field(default=0.0, ge=0.0)
    aggregate_ndcg_min_delta: float = Field(default=0.0, ge=0.0)
    gauc_guardrail_delta: float = Field(default=-0.002, le=0.0)
    ndcg_guardrail_delta: float = Field(default=-0.001, le=0.0)
    hr_guardrail_delta: float = Field(default=-0.001, le=0.0)
    deep_clear_random_gauc: float = Field(default=0.55, ge=0.5, le=1.0)
    minimum_wide_to_deep_rms_ratio: float = Field(default=0.01, gt=0.0)
    minimum_hybrid_deep_top_k_change_rate: float = Field(default=0.05, gt=0.0, le=1.0)
    minimum_gauc: float = Field(default=0.75, ge=0.5, le=1.0)
    minimum_hr_at_k: float = Field(default=0.15, ge=0.0, le=1.0)
    minimum_ndcg_at_k: float = Field(default=0.08, ge=0.0, le=1.0)
    random_gauc_tolerance: float = Field(default=0.02, ge=0.0)
    cold_score_atol: float = Field(default=1e-6, ge=0.0)
    wide_zero_atol: float = Field(default=1e-7, ge=0.0)


class ServingConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    environment: str = Field(default="development", alias="AI_ENV")
    host: str = Field(default="0.0.0.0", alias="AI_HOST")
    port: int = Field(default=8_000, alias="AI_PORT", ge=1, le=65_535)
    workers: int = Field(default=1, alias="AI_WORKERS", ge=1)
    ort_intra_op_threads: int = Field(default=1, alias="AI_ORT_INTRA_OP_THREADS", ge=1)
    ort_inter_op_threads: int = Field(default=1, alias="AI_ORT_INTER_OP_THREADS", ge=1)
    max_candidates: int = Field(default=256, ge=1)


class Settings:
    """Small aggregated interface shared by pipeline, model, and serving."""

    def __init__(self, document: dict[str, Any] | None = None) -> None:
        document = document or {}
        unexpected = set(document) - {"data", "model", "train", "eval", "serving"}
        if unexpected:
            raise ConfigurationError(f"unknown configuration groups: {sorted(unexpected)}")
        self.data = DataConfig(**document.get("data", {}))
        self.model = ModelConfig(**document.get("model", {}))
        self.train = TrainConfig(**document.get("train", {}))
        self.eval = EvalConfig(**document.get("eval", {}))
        self.serving = ServingConfig(**document.get("serving", {}))

    @classmethod
    def from_resolved_document(cls, document: dict[str, Any]) -> Settings:
        """Rehydrate immutable run settings without reading environment aliases."""
        groups = {"data", "model", "train", "eval", "serving"}
        if set(document) != groups:
            raise ConfigurationError(
                f"resolved configuration groups must be exactly {sorted(groups)}"
            )
        instance = cls.__new__(cls)
        instance.data = DataConfig.model_validate(document.get("data", {}))
        instance.model = ModelConfig.model_validate(document.get("model", {}))
        instance.train = TrainConfig.model_validate(document.get("train", {}))
        instance.eval = EvalConfig.model_validate(document.get("eval", {}))
        instance.serving = ServingConfig.model_validate(document.get("serving", {}))
        return instance

    def resolved_document(self) -> dict[str, Any]:
        """Return the non-secret, fully resolved configuration for provenance."""
        return {
            "schema_version": MODEL_SCHEMA_VERSION,
            "data": self.data.model_dump(
                mode="json",
                exclude={
                    "chatbot_database_url",
                    "catalog_database_url",
                    "order_database_url",
                },
            ),
            "model": self.model.model_dump(mode="json"),
            "train": self.train.model_dump(mode="json"),
            "eval": self.eval.model_dump(mode="json"),
            "serving": self.serving.model_dump(mode="json"),
        }

    def validate_campaign_stage(self) -> None:
        """Validate the R3 diagnostic/production promotion contract.

        The model schema remains v5.0.0; this is a campaign-level invariant
        that prevents a v3 RuleArtifact from being trained with an unpromoted
        configuration.
        """
        stage = self.train.campaign_stage
        selection_sha = self.train.r3_selection_artifact_sha256
        is_r3_rules = self.data.rule_feature_schema_version == "3.0.0"
        if is_r3_rules and stage == "legacy":
            raise ConfigurationError(
                "rule feature schema 3.0.0 requires diagnostic or production campaign_stage"
            )
        if not is_r3_rules and selection_sha is not None:
            raise ConfigurationError(
                "R3 selection receipt is only valid with rule feature schema 3.0.0"
            )
        if (
            stage == "diagnostic"
            and selection_sha is not None
            and self.train.r3_feature_selection_mode != "selection_artifact"
        ):
            raise ConfigurationError(
                "diagnostic campaign cannot predeclare an R3 selection receipt"
            )
        if self.train.r3_feature_selection_mode == "selection_artifact" and selection_sha is None:
            raise ConfigurationError(
                "selection_artifact mode requires a verified R3 selection receipt"
            )
        if stage == "production" and not is_r3_rules:
            raise ConfigurationError("production campaign requires rule feature schema 3.0.0")
        if stage == "production" and selection_sha is None:
            raise ConfigurationError("production campaign requires an R3 selection receipt SHA")

    def training_signature_sha256(self) -> str:
        """Hash only semantics that can change training or model outputs."""
        document = {
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "dimensions": {
                "num_users": self.data.num_users,
                "num_items": self.data.num_items,
                "num_personas": self.data.num_personas,
                "num_leaf_categories": self.data.num_leaf_categories,
                "num_price_buckets": self.data.num_price_buckets,
            },
            "model": self.model.model_dump(mode="json"),
            "train": self.train.model_dump(mode="json"),
            "eval": self.eval.model_dump(mode="json"),
        }
        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def experiment_signature_sha256(self) -> str:
        """Hash finalist semantics while allowing repeated training seeds."""
        train = self.train.model_dump(mode="json")
        train.pop("seed")
        document = {
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "dimensions": {
                "num_users": self.data.num_users,
                "num_items": self.data.num_items,
                "num_personas": self.data.num_personas,
                "num_leaf_categories": self.data.num_leaf_categories,
                "num_price_buckets": self.data.num_price_buckets,
            },
            "model": self.model.model_dump(mode="json"),
            "train": train,
            "eval": self.eval.model_dump(mode="json"),
        }
        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def comparison_signature_sha256(self) -> str:
        """Hash comparison signature (experiment signature without training_variant)."""
        train = self.train.model_dump(mode="json")
        train.pop("seed", None)
        train.pop("training_variant", None)
        document = {
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "dimensions": {
                "num_users": self.data.num_users,
                "num_items": self.data.num_items,
                "num_personas": self.data.num_personas,
                "num_leaf_categories": self.data.num_leaf_categories,
                "num_price_buckets": self.data.num_price_buckets,
            },
            "model": self.model.model_dump(mode="json"),
            "train": train,
            "eval": self.eval.model_dump(mode="json"),
        }
        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def validate_production(self, *, serving: bool = False) -> None:
        if self.serving.environment.lower() != "production":
            return
        if (
            self.model.sbert_model_name != PINNED_SBERT_NAME
            or self.model.sbert_model_revision != PINNED_SBERT_REVISION
        ):
            raise ConfigurationError("production requires pinned SBERT model and revision")
        if (
            self.data.model_bundle_path is not None
            and not self.data.model_bundle_path.is_absolute()
        ):
            raise ConfigurationError("AI_MODEL_BUNDLE_PATH must be an absolute path in production")
        if (
            self.data.database_ssl_root_cert is not None
            and not self.data.database_ssl_root_cert.is_absolute()
        ):
            raise ConfigurationError("SUPABASE_DB_CA_PATH must be an absolute path in production")
        required = {
            "AI_ARTIFACT_ROOT": os.getenv("AI_ARTIFACT_ROOT"),
            "AI_STORE_ID": os.getenv("AI_STORE_ID"),
        }
        if serving:
            required["AI_MODEL_BUNDLE_PATH"] = os.getenv("AI_MODEL_BUNDLE_PATH")
        else:
            required.update(
                {
                    "CHATBOT_DATABASE_URL": os.getenv("CHATBOT_DATABASE_URL"),
                    "CATALOG_DATABASE_URL": os.getenv("CATALOG_DATABASE_URL"),
                    "ORDER_DATABASE_URL": os.getenv("ORDER_DATABASE_URL"),
                    "SUPABASE_DB_CA_PATH": os.getenv("SUPABASE_DB_CA_PATH"),
                }
            )
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ConfigurationError(f"missing production settings: {', '.join(missing)}")


def get_settings() -> Settings:
    return Settings()


def load_settings(path: Path | None = None) -> Settings:
    """Load one explicit TOML configuration without hidden fallback values."""
    if path is None:
        return Settings()
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"cannot load training configuration {path}: {error}") from error
    return Settings(document)


def load_resolved_settings(path: Path) -> Settings:
    """Load the immutable configuration saved with a v5 training run."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigurationError(
            f"cannot load resolved training configuration {path}: {error}"
        ) from error
    if not isinstance(document, dict) or document.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ConfigurationError(
            f"resolved training configuration schema does not match {MODEL_SCHEMA_VERSION}"
        )
    payload = dict(document)
    payload.pop("schema_version", None)
    return Settings.from_resolved_document(payload)
