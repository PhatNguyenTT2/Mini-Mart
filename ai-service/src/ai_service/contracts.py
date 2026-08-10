"""Versioned domain and artifact contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class SplitName(StrEnum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


class RunStatus(StrEnum):
    STAGING = "staging"
    TRAINING = "training"
    INTERRUPTED = "interrupted"
    EVALUATED = "evaluated"
    SEALED = "sealed"
    FAILED = "failed"


class ModelVariant(StrEnum):
    WIDE_ONLY = "wide_only"
    SBERT_CENTROID = "sbert_centroid"
    ITEM_CF = "item_cf"
    DEEP_ONLY = "deep_only"
    HYBRID = "hybrid"
    NOISY_HYBRID = "noisy_hybrid"
    RANDOM = "random"


class TrainingVariant(StrEnum):
    DEEP_ONLY = "deep_only"
    HYBRID = "hybrid"


class DataSourceKind(StrEnum):
    POSTGRES = "postgres"
    SYNTHETIC = "synthetic"


class EmbeddingSource(StrEnum):
    REAL = "real"
    MOCK = "mock"


class ArtifactManifest(BaseModel):
    schema_version: str = "3.0.0"
    artifact_id: str
    created_at: datetime = Field(default_factory=utc_now)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_sha256: dict[str, str] = Field(default_factory=dict)


class ColdPartitionManifest(ArtifactManifest):
    benchmark_run_id: str
    store_id: int = Field(gt=0)
    seed: int
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cold_product_ids: list[int]


class SnapshotManifest(ArtifactManifest):
    benchmark_run_id: str
    store_id: int = Field(gt=0)
    source_kind: DataSourceKind
    num_events: int
    num_users: int
    num_items: int
    num_cold_items: int
    split_counts: dict[SplitName, int]
    split_boundaries: dict[str, datetime]


class EmbeddingManifest(ArtifactManifest):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_kind: EmbeddingSource
    model_name: str
    model_revision: str
    input_text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    product_map_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shape: tuple[int, int]
    dtype: str = "float32"
    l2_normalized: bool = True


class RuleManifest(ArtifactManifest):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    num_directed_rules: int
    train_basket_count: int
    min_count: int
    min_lift: float
    q99_log_lift: float
    feature_schema_version: str = "2.0.0"
    has_full_statistics: bool = True


class CheckpointManifest(ArtifactManifest):
    run_id: str
    snapshot_sha256: str
    embedding_sha256: str
    rule_sha256: str
    training_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_schema_version: str
    best_epoch: int
    best_val_gauc: float
    best_val_ndcg_at_k: float = 0.0
    best_val_hr_at_k: float = 0.0
    training_variant: TrainingVariant = TrainingVariant.HYBRID
    comparison_signature_sha256: str = Field(default="", pattern=r"^(|[0-9a-f]{64})$")


class ModelBundleManifest(ArtifactManifest):
    bundle_id: str
    run_id: str
    store_id: int
    files: dict[str, str]
    item_count: int
    embedding_dim: int
    model_version: str
    parity_max_abs: float
    ranking_parity_users: int = Field(ge=1)
    kernel_latency_ms: dict[str, float]
    benchmark_hardware: dict[str, str]
    training_variant: TrainingVariant = TrainingVariant.HYBRID
    victory_matrix_sha256: str = Field(default="", pattern=r"^(|[0-9a-f]{64})$")


class MetricGateResult(BaseModel):
    name: str
    passed: bool
    observed: float
    target: float
    description: str


class ColdParityReport(BaseModel):
    max_abs_wide_logit: float
    max_abs_hybrid_minus_deep: float
    cold_only_order_equality: bool
    deep_cold_hr_at_k: float
    deep_cold_ndcg_at_k: float
    hybrid_cold_hr_at_k: float
    hybrid_cold_ndcg_at_k: float
    passed: bool


class VictoryMatrix(BaseModel):
    random_gauc_passed: bool
    hybrid_gauc_passed: bool
    hr_domination_passed: bool
    relative_ndcg_passed: bool
    semantic_traps_passed: bool
    cold_parity_passed: bool
    all_passed: bool
    gates: list[MetricGateResult]
    sha256: str = ""


class EvaluationReport(BaseModel):
    run_id: str
    split: SplitName
    variant: ModelVariant
    num_total_users: int
    num_eligible_users: int
    num_users_without_novel_purchase: int
    num_catalog_items: int
    hr_at_k: float
    ndcg_at_k: float
    gauc: float
    k: int


class DataQualityReport(BaseModel):
    total_events: int
    split_counts: dict[str, int]
    unique_user_item_pairs: int
    repeat_event_rate: float
    view_pairs: int
    purchase_pairs: int
    view_only_pairs: int
    converted_pairs: int
    purchase_with_prior_view_fraction: float | None
    view_to_purchase_lift: float | None = None
    per_user_unique_item_quantiles: dict[str, float]
    popularity_gini: float
    popularity_top_shares: dict[str, float]
    product_distribution_js: dict[str, float]
    organic_novel_purchase_users: dict[str, int]
    strict_context_coverage: float
    fixture_event_counts: dict[str, int]
    legacy_origin_defaulted: bool
    training_suitability_passed: bool
    gate_failures: tuple[str, ...]


class ContextRef(BaseModel):
    item_idx: int = -1
    present: bool = False
