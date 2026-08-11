"""Versioned domain and artifact contracts."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class CheckpointAction(StrEnum):
    NONE = "none"
    SAVE_BEST = "save_best"
    SAVE_BEST_TIE = "save_best_tie"


class TerminalAction(StrEnum):
    CONTINUE = "continue"
    COMPLETED = "completed"
    STOP_PLATEAU = "stop_plateau"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ArtifactLineage(BaseModel):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RuleManifest(ArtifactManifest):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    num_directed_rules: int
    train_basket_count: int
    min_count: int
    min_lift: float
    q99_log_lift: float
    feature_schema_version: str = "2.0.0"
    has_full_statistics: bool = False


class CheckpointManifest(ArtifactManifest):
    schema_version: Literal["5.0.0"]
    run_id: str
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    training_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_schema_version: Literal["5.0.0"]
    best_epoch: int
    best_val_gauc: float
    best_val_ndcg_at_k: float
    best_val_hr_at_k: float
    checkpoint_kind: Literal["best", "last"]
    training_variant: TrainingVariant
    comparison_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("best_val_gauc", "best_val_ndcg_at_k", "best_val_hr_at_k")
    @classmethod
    def finite_metrics(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("checkpoint metrics must be finite")
        return value


class PipelineState(BaseModel):
    """Durable state for one schema-v5 training run."""

    model_schema_version: Literal["5.0.0"]
    run_id: str
    training_variant: TrainingVariant
    snapshot_id: str
    embedding_path: str
    rule_path: str
    checkpoint_path: str | None
    paired_run_id: str | None
    validation_gate_passed: bool
    test_gate_passed: bool
    validation_victory_matrix_path: str | None
    test_victory_matrix_path: str | None
    bundle_path: str | None

    @field_validator("run_id", "snapshot_id", "embedding_path", "rule_path")
    @classmethod
    def require_non_empty_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pipeline state identity fields cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_state_dependencies(self) -> PipelineState:
        if self.paired_run_id is not None and not self.paired_run_id.strip():
            raise ValueError("paired_run_id cannot be empty")
        if self.paired_run_id == self.run_id:
            raise ValueError("pipeline state cannot pair a run with itself")
        if self.validation_gate_passed and self.validation_victory_matrix_path is None:
            raise ValueError("validation gate requires a validation Victory Matrix path")
        if self.test_gate_passed:
            if not self.validation_gate_passed:
                raise ValueError("test gate requires a passed validation gate")
            if self.validation_victory_matrix_path is None:
                raise ValueError("test gate requires a validation Victory Matrix path")
            if self.test_victory_matrix_path is None:
                raise ValueError("test gate requires a test Victory Matrix path")
        if self.bundle_path is not None and not self.test_gate_passed:
            raise ValueError("bundle path requires a passed test gate")
        return self


class ModelBundleManifest(ArtifactManifest):
    schema_version: Literal["5.0.0"]
    bundle_id: str
    run_id: str
    store_id: int
    files: dict[str, str]
    item_count: int
    embedding_dim: int
    model_version: Literal["5.0.0"]
    parity_max_abs: float
    ranking_parity_users: int = Field(ge=1)
    kernel_latency_ms: dict[str, float]
    benchmark_hardware: dict[str, str]
    training_variant: Literal[TrainingVariant.HYBRID]
    comparison_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    victory_matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MetricGateResult(BaseModel):
    name: str
    passed: bool
    observed: float
    target: float
    description: str
    candidate_name: str
    baseline_name: str
    candidate_mean: float
    baseline_mean: float
    delta_mean: float
    ci_lower: float
    ci_upper: float
    threshold: float
    failure_reason: str | None = None

    @field_validator(
        "observed",
        "target",
        "candidate_mean",
        "baseline_mean",
        "delta_mean",
        "ci_lower",
        "ci_upper",
        "threshold",
    )
    @classmethod
    def finite_gate_values(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("gate evidence must be finite")
        return value

    @model_validator(mode="after")
    def failure_reason_matches_status(self) -> MetricGateResult:
        if not self.passed and (
            not isinstance(self.failure_reason, str) or not self.failure_reason.strip()
        ):
            raise ValueError("failed metric gates require a failure_reason")
        if self.passed and self.failure_reason is not None:
            raise ValueError("passed metric gates cannot carry a failure_reason")
        return self


class AggregateReleaseReport(BaseModel):
    schema_version: Literal["5.0.0"]
    split: SplitName
    passed: bool
    comparison_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hybrid_run_ids: tuple[str, str, str]
    deep_run_ids: tuple[str, str, str]
    selected_run_id: str
    selected_seed: Literal[42, 2027, 31415]
    selected_victory_matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gates: tuple[MetricGateResult, ...]
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def rollup_is_consistent(self) -> AggregateReleaseReport:
        if any(not run_id.strip() for run_id in (*self.hybrid_run_ids, *self.deep_run_ids)):
            raise ValueError("aggregate release run IDs cannot be empty")
        if len(set(self.hybrid_run_ids)) != 3:
            raise ValueError("aggregate release requires three distinct Hybrid runs")
        if len(set(self.deep_run_ids)) != 3:
            raise ValueError("aggregate release requires three distinct Deep runs")
        if set(self.hybrid_run_ids) & set(self.deep_run_ids):
            raise ValueError("Hybrid and Deep finalist IDs must be disjoint")
        if len(self.gates) != 3:
            raise ValueError("aggregate release requires GAUC, NDCG, and HR gates")
        if {gate.name for gate in self.gates} != {
            "aggregate_gauc",
            "aggregate_ndcg",
            "aggregate_hr",
        }:
            raise ValueError("aggregate release gate names are incomplete")
        if self.passed != all(gate.passed for gate in self.gates):
            raise ValueError("aggregate release rollup disagrees with gate evidence")
        if self.selected_run_id not in self.hybrid_run_ids:
            raise ValueError("selected release run must be a Hybrid finalist")
        return self


class ColdParityReport(BaseModel):
    max_abs_wide_logit: float
    max_abs_hybrid_minus_deep: float
    cold_only_order_equality: bool
    deep_cold_hr_at_k: float
    deep_cold_ndcg_at_k: float
    hybrid_cold_hr_at_k: float
    hybrid_cold_ndcg_at_k: float
    passed: bool
    num_cold_items: int = 250
    num_cohort_users: int = 250
    wide_zero_atol: float = 1e-7
    cold_score_atol: float = 1e-6

    @model_validator(mode="after")
    def require_fixed_cohort(self) -> ColdParityReport:
        if self.num_cold_items != 250 or self.num_cohort_users != 250:
            raise ValueError("cold parity requires exactly 250 items and 250 users")
        return self


class VictoryMatrix(BaseModel):
    random_gauc_passed: bool
    hybrid_gauc_passed: bool
    hr_domination_passed: bool
    relative_ndcg_passed: bool
    semantic_traps_passed: bool
    cold_parity_passed: bool
    all_passed: bool
    gates: list[MetricGateResult]
    seed: int
    split: SplitName
    comparison_signature: str = Field(pattern=r"^[0-9a-f]{64}$")
    strongest_hr_baseline: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def gate_rollup_is_consistent(self) -> VictoryMatrix:
        if self.all_passed != all(gate.passed for gate in self.gates):
            raise ValueError("victory matrix all_passed disagrees with gate evidence")
        expected = {
            "random_gauc": self.random_gauc_passed,
            "hybrid_gauc": self.hybrid_gauc_passed,
            "hr_domination": self.hr_domination_passed,
            "relative_ndcg": self.relative_ndcg_passed,
            "semantic_traps": self.semantic_traps_passed,
            "cold_parity": self.cold_parity_passed,
        }
        if {gate.name for gate in self.gates} != set(expected):
            raise ValueError("victory matrix requires the six single-seed gates")
        for gate in self.gates:
            if gate.name in expected and gate.passed != expected[gate.name]:
                raise ValueError(f"victory matrix boolean disagrees with {gate.name} gate")
        return self


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
