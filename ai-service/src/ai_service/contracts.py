"""Versioned domain and artifact contracts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EVALUATION_SCHEMA_VERSION = "5.2.0"
RULE_COVERAGE_SEMANTICS_VERSION = "organic-target-alignment-v3"


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
    PERSONA_ONLY = "persona_only"


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
    benchmark_spec_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    semantic_cohort_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    order_metadata_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def postgres_v5_lineage_is_complete(self) -> SnapshotManifest:
        if self.schema_version == "3.0.0" and self.source_kind is DataSourceKind.POSTGRES:
            if not all(
                isinstance(value, str)
                for value in (
                    self.benchmark_spec_sha256,
                    self.semantic_cohort_sha256,
                    self.order_metadata_sha256,
                )
            ):
                raise ValueError("postgres v5 snapshot requires expanded lineage hashes")
        return self


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
    benchmark_spec_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    semantic_cohort_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    order_metadata_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def metadata_lineage_is_complete(self) -> ArtifactLineage:
        values = (
            self.benchmark_spec_sha256,
            self.semantic_cohort_sha256,
            self.order_metadata_sha256,
        )
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("expanded benchmark lineage must contain all metadata hashes")
        return self

    def as_mapping(self) -> dict[str, str]:
        mapping = {
            "snapshot": self.snapshot_sha256,
            "embedding": self.embedding_sha256,
            "rules": self.rule_sha256,
        }
        if self.benchmark_spec_sha256 is not None:
            mapping.update(
                {
                    "benchmark_spec": self.benchmark_spec_sha256,
                    "semantic_cohort": str(self.semantic_cohort_sha256),
                    "order_metadata": str(self.order_metadata_sha256),
                }
            )
        return mapping


class ArtifactLineageV5(BaseModel):
    """Strict six-artifact lineage for the R3/R4 benchmark campaign."""

    # The short names are the canonical serialized lineage keys.  Read-only
    # SHA-suffixed properties below keep callers explicit without creating a
    # second wire representation.
    snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding: str = Field(pattern=r"^[0-9a-f]{64}$")
    rules: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_spec: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_cohort: str = Field(pattern=r"^[0-9a-f]{64}$")
    order_metadata: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def snapshot_sha256(self) -> str:
        return self.snapshot

    @property
    def embedding_sha256(self) -> str:
        return self.embedding

    @property
    def rule_sha256(self) -> str:
        return self.rules

    @property
    def benchmark_spec_sha256(self) -> str:
        return self.benchmark_spec

    @property
    def semantic_cohort_sha256(self) -> str:
        return self.semantic_cohort

    @property
    def order_metadata_sha256(self) -> str:
        return self.order_metadata

    def as_mapping(self) -> dict[str, str]:
        return {
            "snapshot": self.snapshot,
            "embedding": self.embedding,
            "rules": self.rules,
            "benchmark_spec": self.benchmark_spec,
            "semantic_cohort": self.semantic_cohort,
            "order_metadata": self.order_metadata,
        }


ArtifactLineageInput = ArtifactLineage | ArtifactLineageV5 | Mapping[str, str]


def normalize_artifact_lineage(value: ArtifactLineageInput) -> dict[str, str]:
    """Normalize a typed lineage at an artifact boundary.

    The wire representation remains a canonical mapping because manifests and
    checkpoint payloads are JSON documents. Callers may pass either strict
    domain models or a mapping while legacy schema-2 audit fixtures are read;
    all values and keys are validated before serialization.
    """
    if isinstance(value, (ArtifactLineage, ArtifactLineageV5)):
        return value.as_mapping()
    if not isinstance(value, Mapping):
        raise ValueError("artifact lineage must be a typed lineage or mapping")
    normalized = dict(value)
    expected = {
        "snapshot",
        "embedding",
        "rules",
    }
    expanded = expected | {"benchmark_spec", "semantic_cohort", "order_metadata"}
    if set(normalized) not in (expected, expanded):
        raise ValueError("artifact lineage keys are incomplete")
    if any(
        not isinstance(key, str) or not isinstance(item, str) or len(item) != 64
        for key, item in normalized.items()
    ):
        raise ValueError("artifact lineage contains an invalid SHA")
    if any(
        any(character not in "0123456789abcdef" for character in item)
        for item in normalized.values()
    ):
        raise ValueError("artifact lineage contains an invalid SHA")
    return normalized


def artifact_lineage_model(value: ArtifactLineageInput) -> ArtifactLineage | ArtifactLineageV5:
    """Return the strict domain object for a verified lineage boundary."""

    normalized = normalize_artifact_lineage(value)
    if set(normalized) == {
        "snapshot",
        "embedding",
        "rules",
        "benchmark_spec",
        "semantic_cohort",
        "order_metadata",
    }:
        return ArtifactLineageV5(**normalized)
    return ArtifactLineage(
        snapshot_sha256=normalized["snapshot"],
        embedding_sha256=normalized["embedding"],
        rule_sha256=normalized["rules"],
    )


class RuleCoverageEvidence(BaseModel):
    total_directed_rules: int = Field(ge=0)
    non_trap_directed_rules: int = Field(ge=0)
    trap_anchored_directed_rules: int = Field(ge=0)
    trap_anchored_rule_fraction: float = Field(ge=0.0, le=1.0)
    distinct_organic_rule_items: int = Field(ge=0)
    eligible_val_context_users: int = Field(ge=0)
    val_context_users_with_rule: int = Field(ge=0)
    val_context_rule_coverage: float = Field(ge=0.0, le=1.0)
    full_catalog_organic_pair_coverage: float = Field(ge=0.0, le=1.0)


class RuleManifest(ArtifactManifest):
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    num_directed_rules: int
    train_basket_count: int
    min_count: int
    min_lift: float
    q99_log_lift: float
    feature_schema_version: str = "3.0.0"
    has_full_statistics: bool = False
    coverage_semantics_version: str | None = None
    coverage: RuleCoverageEvidence | None = None


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
    benchmark_spec_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    semantic_cohort_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    order_metadata_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def expanded_lineage_is_complete(self) -> CheckpointManifest:
        values = (
            self.benchmark_spec_sha256,
            self.semantic_cohort_sha256,
            self.order_metadata_sha256,
        )
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("checkpoint expanded lineage must contain all metadata hashes")
        parent_keys = set(self.parent_sha256)
        if (
            "benchmark_spec" in parent_keys
            or "semantic_cohort" in parent_keys
            or "order_metadata" in parent_keys
        ):
            if parent_keys != {
                "snapshot",
                "embedding",
                "rules",
                "benchmark_spec",
                "semantic_cohort",
                "order_metadata",
            }:
                raise ValueError("checkpoint v5 lineage must contain all six artifact hashes")
            if {
                "snapshot": self.snapshot_sha256,
                "embedding": self.embedding_sha256,
                "rules": self.rule_sha256,
                "benchmark_spec": self.benchmark_spec_sha256,
                "semantic_cohort": self.semantic_cohort_sha256,
                "order_metadata": self.order_metadata_sha256,
            } != self.parent_sha256:
                raise ValueError("checkpoint manifest lineage fields do not match parent_sha256")
        return self

    def as_mapping(self) -> dict[str, str]:
        mapping = {
            "snapshot": self.snapshot_sha256,
            "embedding": self.embedding_sha256,
            "rules": self.rule_sha256,
        }
        if self.benchmark_spec_sha256 is not None:
            mapping.update(
                {
                    "benchmark_spec": self.benchmark_spec_sha256,
                    "semantic_cohort": str(self.semantic_cohort_sha256),
                    "order_metadata": str(self.order_metadata_sha256),
                }
            )
        return mapping

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
    # Active v5 runs always populate this typed lineage.  ``None`` remains
    # accepted for legacy unit/synthetic state fixtures that never cross a
    # production artifact boundary.
    lineage: ArtifactLineage | ArtifactLineageV5 | None = None

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
    lineage: ArtifactLineageV5 | None = None


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


class MetricBaselineSelection(BaseModel):
    gauc: Literal[
        "persona_only",
        "item_cf",
        "sbert_centroid",
        "apriori_only",
        "deep_only",
        "noisy_hybrid",
        "random",
    ]
    hr_at_k: Literal[
        "persona_only",
        "item_cf",
        "sbert_centroid",
        "apriori_only",
        "deep_only",
        "noisy_hybrid",
        "random",
    ]
    ndcg_at_k: Literal[
        "persona_only",
        "item_cf",
        "sbert_centroid",
        "apriori_only",
        "deep_only",
        "noisy_hybrid",
        "random",
    ]


class AggregateReleaseReport(BaseModel):
    schema_version: Literal["5.2.0"]
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
    lineage: ArtifactLineageV5 | None = None

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
        if len(self.gates) != 6:
            raise ValueError("aggregate release requires six dominance gates")
        if {gate.name for gate in self.gates} != {
            "aggregate_gauc_domination",
            "aggregate_hr_domination",
            "aggregate_ndcg_domination",
            "aggregate_gauc_vs_deep",
            "aggregate_hr_vs_deep",
            "aggregate_ndcg_vs_deep",
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
    schema_version: Literal["5.2.0"]
    random_gauc_passed: bool
    hybrid_minimum_gauc_passed: bool
    hybrid_minimum_hr_passed: bool = False
    hybrid_minimum_ndcg_passed: bool = False
    gauc_domination_passed: bool
    hr_domination_passed: bool
    ndcg_domination_passed: bool
    semantic_traps_passed: bool
    cold_parity_passed: bool
    all_passed: bool
    gates: list[MetricGateResult]
    seed: int
    split: SplitName
    comparison_signature: str = Field(pattern=r"^[0-9a-f]{64}$")
    strongest_baselines: MetricBaselineSelection
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def gate_rollup_is_consistent(self) -> VictoryMatrix:
        if self.all_passed != all(gate.passed for gate in self.gates):
            raise ValueError("victory matrix all_passed disagrees with gate evidence")
        expected = {
            "random_gauc": self.random_gauc_passed,
            "hybrid_minimum_gauc": self.hybrid_minimum_gauc_passed,
            "gauc_domination": self.gauc_domination_passed,
            "hr_domination": self.hr_domination_passed,
            "ndcg_domination": self.ndcg_domination_passed,
            "semantic_traps": self.semantic_traps_passed,
            "cold_parity": self.cold_parity_passed,
        }
        gate_names = {gate.name for gate in self.gates}
        if "hybrid_minimum_hr" in gate_names or "hybrid_minimum_ndcg" in gate_names:
            expected.update(
                {
                    "hybrid_minimum_hr": self.hybrid_minimum_hr_passed,
                    "hybrid_minimum_ndcg": self.hybrid_minimum_ndcg_passed,
                }
            )
        if gate_names != set(expected):
            raise ValueError("victory matrix single-seed gates are incomplete")
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


class RuleAlignmentEvidence(BaseModel):
    training_targets: int = Field(ge=0)
    strict_training_rule_targets: int = Field(ge=0)
    strict_training_rule_rate: float = Field(ge=0.0, le=1.0)
    positive_other_rule_hits: int = Field(ge=0)
    in_batch_negative_rule_hits: int = Field(ge=0)
    explicit_negative_rule_hits: int = Field(ge=0)
    negative_only_rows: int = Field(ge=0)
    val_eligible_users: int = Field(ge=0)
    val_rule_aligned_users: int = Field(ge=0)
    val_rule_aligned_rate: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def counts_are_consistent(self) -> RuleAlignmentEvidence:
        if self.strict_training_rule_targets > self.training_targets:
            raise ValueError("strict training rule targets exceed training targets")
        if self.val_rule_aligned_users > self.val_eligible_users:
            raise ValueError("aligned VAL users exceed eligible VAL users")
        return self


class DatasetAlignmentEvidence(BaseModel):
    """Immutable receipt for the target/useful-rule alignment preflight."""

    training_target_count: int = Field(ge=0)
    strict_target_rule_count: int = Field(ge=0)
    strict_target_rule_rate: float = Field(ge=0.0, le=1.0)
    val_eligible_user_count: int = Field(ge=0)
    val_aligned_user_count: int = Field(ge=0)
    val_aligned_user_rate: float = Field(ge=0.0, le=1.0)
    negative_only_row_count: int = Field(ge=0)


class RulePairIndexManifest(BaseModel):
    """Receipt describing the organic/protected edge index used by sampling."""

    schema_version: Literal["3.0.0"]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    organic_directed_edge_count: int = Field(ge=0)
    protected_trap_edge_count: int = Field(ge=0)


class CheckpointEligibility(BaseModel):
    """Resolved post-warmup eligibility decision persisted in epoch evidence."""

    epoch: int = Field(ge=1)
    eligible: bool
    reason: str
    gauc: float = Field(ge=0.0, le=1.0)
    hr_at_k: float = Field(ge=0.0, le=1.0)
    ndcg_at_k: float = Field(ge=0.0, le=1.0)


class CohortMetricDelta(BaseModel):
    cohort_name: Literal["aligned", "unaligned"]
    user_count: int = Field(ge=0)
    hybrid_minus_deep_gauc: float
    hybrid_minus_deep_hr_at_k: float
    hybrid_minus_deep_ndcg_at_k: float

    @field_validator(
        "hybrid_minus_deep_gauc",
        "hybrid_minus_deep_hr_at_k",
        "hybrid_minus_deep_ndcg_at_k",
    )
    @classmethod
    def finite_delta(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("cohort deltas must be finite")
        return value


class TrapDiagnosticEvidence(BaseModel):
    trap_id: int = Field(ge=1, le=10)
    anchor_raw_id: int = Field(gt=0)
    target_raw_ids: tuple[int, ...]
    anchor_internal_id: int = Field(ge=0)
    target_internal_ids: tuple[int, ...]
    rule_present: tuple[bool, ...]
    raw_lifts: tuple[float, ...]
    item_query_deep_rank: int = Field(ge=1)
    item_query_hybrid_rank: int = Field(ge=1)
    serving_deep_rank: int = Field(ge=1)
    serving_hybrid_rank: int = Field(ge=1)
    deep_top_k_cutoff: float
    learned_wide_bonus: float
    required_wide_bonus: float

    @model_validator(mode="after")
    def target_vectors_match(self) -> TrapDiagnosticEvidence:
        if len(self.target_raw_ids) != len(self.target_internal_ids):
            raise ValueError("trap raw/internal target IDs must have equal length")
        if len(self.target_raw_ids) != len(self.rule_present):
            raise ValueError("trap rule evidence must cover every target")
        if len(self.target_raw_ids) != len(self.raw_lifts):
            raise ValueError("trap lift evidence must cover every target")
        values = (
            self.deep_top_k_cutoff,
            self.learned_wide_bonus,
            self.required_wide_bonus,
            *self.raw_lifts,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("trap score evidence must be finite")
        return self


class AlphaSweepEvidence(BaseModel):
    alpha: float
    gauc: float = Field(ge=0.0, le=1.0)
    hr_at_k: float = Field(ge=0.0, le=1.0)
    ndcg_at_k: float = Field(ge=0.0, le=1.0)
    meets_absolute_floors: bool

    @field_validator("alpha")
    @classmethod
    def finite_alpha(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("alpha must be finite")
        return value


class R3DiagnosticReport(BaseModel):
    schema_version: Literal["1.0.0"]
    evaluation_schema_version: Literal["5.2.0"]
    split: Literal[SplitName.VAL]
    hybrid_run_id: str = Field(min_length=1)
    deep_run_id: str = Field(min_length=1)
    hybrid_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deep_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
    lineage: ArtifactLineage | ArtifactLineageV5
    comparison_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_cohort_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    order_metadata_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    rule_alignment: RuleAlignmentEvidence
    cohort_deltas: tuple[CohortMetricDelta, CohortMetricDelta]
    trap_evidence: tuple[TrapDiagnosticEvidence, ...]
    alpha_sweep: tuple[AlphaSweepEvidence, ...]
    per_user_metrics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_diagnostic_shape(self) -> R3DiagnosticReport:
        if self.hybrid_run_id == self.deep_run_id:
            raise ValueError("R3 diagnostic requires distinct Hybrid and Deep runs")
        if tuple(sorted(item.cohort_name for item in self.cohort_deltas)) != (
            "aligned",
            "unaligned",
        ):
            raise ValueError("R3 diagnostic requires aligned and unaligned cohort deltas")
        if len(self.trap_evidence) != 10 or {item.trap_id for item in self.trap_evidence} != set(
            range(1, 11)
        ):
            raise ValueError("R3 diagnostic requires exactly trap IDs 1..10")
        expected_alphas = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
        if tuple(item.alpha for item in self.alpha_sweep) != expected_alphas:
            raise ValueError("R3 diagnostic alpha sweep is not canonical")
        lineage_spec = getattr(self.lineage, "benchmark_spec_sha256", None)
        lineage_cohort = getattr(self.lineage, "semantic_cohort_sha256", None)
        lineage_order = getattr(self.lineage, "order_metadata_sha256", None)
        if isinstance(self.lineage, ArtifactLineageV5) and self.order_metadata_sha256 is None:
            raise ValueError("v5 diagnostic reports require order metadata lineage")
        if lineage_spec is not None and self.benchmark_spec_sha256 != lineage_spec:
            raise ValueError("R3 diagnostic benchmark spec hash is not bound to lineage")
        if lineage_cohort is not None and self.semantic_cohort_sha256 != lineage_cohort:
            raise ValueError("R3 diagnostic cohort hash is not bound to lineage")
        if lineage_order is not None and self.order_metadata_sha256 != lineage_order:
            raise ValueError("R3 diagnostic order metadata hash is not bound to lineage")
        return self


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
