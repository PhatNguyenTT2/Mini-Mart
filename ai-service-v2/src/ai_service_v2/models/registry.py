"""Small local model registry used by the fixture runner and CLI.

The registry is deliberately narrow: it wires only controls and the three
proposed ablations to the shared score-provider seam.  Reference repositories
will enter through separate adapters and are not silently represented here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.rules import AprioriRuleTable
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError
from ai_service_v2.hashing import canonical_json_sha256
from ai_service_v2.models.baselines import MostPopScorer, RandomScorer
from ai_service_v2.models.proposed import (
    HybridScorer,
    ItemFeatureMatrix,
    RuleOnlyScorer,
    TrainedTwoTower,
    TrainingReport,
    TwoTowerConfig,
    item_text_hash_features,
    train_two_tower,
)
from ai_service_v2.protocol import PreparedProtocol

MODEL_KINDS = frozenset({"random", "mostpop", "rule_only", "deep_two_tower", "hybrid"})
FUSION_NORMALIZATIONS = frozenset({"none", "per_user_zscore"})
FEATURE_SOURCES = frozenset({"deterministic_hash_features"})


@dataclass(frozen=True)
class ModelRunSpec:
    model_kind: str
    model_id: str
    feature_source: str
    feature_dimensions: int
    two_tower: dict[str, Any] | None
    wide_weight: float
    rule_min_support: int
    fusion_normalization: str
    schema_version: str = "model-run-spec/1.1"

    def __post_init__(self) -> None:
        if not isinstance(self.model_kind, str) or not isinstance(self.model_id, str):
            raise ContractError("model spec identity fields must be strings")
        if self.model_kind not in MODEL_KINDS:
            raise ContractError(f"unsupported model kind: {self.model_kind}")
        if self.schema_version not in {"model-run-spec/1.0", "model-run-spec/1.1"}:
            raise ContractError("unsupported model run spec schema")
        if not self.model_id or not isinstance(self.feature_source, str) or not self.feature_source:
            raise ContractError("model spec identity fields are required")
        if self.feature_source not in FEATURE_SOURCES:
            raise ContractError(f"unsupported feature source: {self.feature_source}")
        if self.feature_dimensions < 4:
            raise ContractError("feature_dimensions must be at least four")
        if not math.isfinite(self.wide_weight) or self.wide_weight < 0:
            raise ContractError("wide_weight must be finite and non-negative")
        if self.rule_min_support < 1:
            raise ContractError("rule_min_support must be positive")
        if self.model_kind == "hybrid":
            if self.fusion_normalization not in FUSION_NORMALIZATIONS:
                raise ContractError("unsupported hybrid fusion normalization")
        elif self.fusion_normalization != "not_applicable":
            raise ContractError("fusion normalization is only valid for hybrid models")
        needs_deep = self.model_kind in {"deep_two_tower", "hybrid"}
        if needs_deep and self.two_tower is None:
            raise ContractError("deep and hybrid specs require two_tower config")
        if not needs_deep and self.two_tower is not None:
            raise ContractError("non-deep specs must not carry two_tower config")
        if self.model_kind != "hybrid" and self.wide_weight != 0.0:
            raise ContractError("wide_weight is only valid for hybrid models")

    def to_mapping(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "model_kind": self.model_kind,
            "model_id": self.model_id,
            "feature_source": self.feature_source,
            "feature_dimensions": self.feature_dimensions,
            "two_tower": self.two_tower,
            "wide_weight": self.wide_weight,
            "rule_min_support": self.rule_min_support,
        }
        if self.schema_version == "model-run-spec/1.1":
            result["fusion_normalization"] = self.fusion_normalization
        return result

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ModelRunSpec:
        legacy_required = {
            "schema_version",
            "model_kind",
            "model_id",
            "feature_source",
            "feature_dimensions",
            "two_tower",
            "wide_weight",
            "rule_min_support",
        }
        current_required = legacy_required | {"fusion_normalization"}
        schema_version = value.get("schema_version")
        if schema_version == "model-run-spec/1.0" and set(value) == legacy_required:
            fusion_normalization = (
                "none" if value.get("model_kind") == "hybrid" else "not_applicable"
            )
        elif schema_version == "model-run-spec/1.1" and set(value) == current_required:
            fusion_normalization = value["fusion_normalization"]
        else:
            raise ContractError("model run spec fields do not match schema")
        dimensions = value["feature_dimensions"]
        if isinstance(dimensions, bool) or not isinstance(dimensions, int):
            raise ContractError("feature_dimensions must be an integer")
        wide_weight = value["wide_weight"]
        if isinstance(wide_weight, bool) or not isinstance(wide_weight, (int, float)):
            raise ContractError("wide_weight must be numeric")
        min_support = value["rule_min_support"]
        if isinstance(min_support, bool) or not isinstance(min_support, int):
            raise ContractError("rule_min_support must be an integer")
        two_tower = value["two_tower"]
        if two_tower is not None and not isinstance(two_tower, dict):
            raise ContractError("two_tower must be an object or null")
        if two_tower is not None:
            two_tower = TwoTowerConfig.from_mapping(two_tower).to_mapping()
        if not isinstance(fusion_normalization, str):
            raise ContractError("fusion_normalization must be a string")
        return cls(
            model_kind=value["model_kind"],
            model_id=value["model_id"],
            feature_source=value["feature_source"],
            feature_dimensions=dimensions,
            two_tower=two_tower,
            wide_weight=float(wide_weight),
            rule_min_support=min_support,
            fusion_normalization=fusion_normalization,
            schema_version=schema_version,
        )


@dataclass(frozen=True)
class LocalModelBundle:
    spec: ModelRunSpec
    descriptor: ModelDescriptor
    scorer: Any
    features: ItemFeatureMatrix | None
    deep_model: TrainedTwoTower | None
    rules: AprioriRuleTable | None
    training_report: TrainingReport | None


def default_spec(
    model_kind: str,
    *,
    feature_dimensions: int = 32,
    two_tower_config: TwoTowerConfig | None = None,
    wide_weight: float = 1.0,
    rule_min_support: int = 1,
    fusion_normalization: str = "per_user_zscore",
    model_id: str | None = None,
) -> ModelRunSpec:
    defaults = {
        "random": "random-v1",
        "mostpop": "mostpop-v1",
        "rule_only": "wide-rule-only-v1",
        "deep_two_tower": "independent-deep-two-tower-v1",
        "hybrid": "proposed-hybrid-v1",
    }
    needs_deep = model_kind in {"deep_two_tower", "hybrid"}
    config = two_tower_config or (TwoTowerConfig() if needs_deep else None)
    return ModelRunSpec(
        model_kind=model_kind,
        model_id=model_id or defaults[model_kind],
        feature_source="deterministic_hash_features",
        feature_dimensions=feature_dimensions,
        two_tower=None if config is None else config.to_mapping(),
        wide_weight=wide_weight if model_kind == "hybrid" else 0.0,
        rule_min_support=rule_min_support,
        fusion_normalization=(fusion_normalization if model_kind == "hybrid" else "not_applicable"),
    )


def descriptor_for_spec(spec: ModelRunSpec) -> ModelDescriptor:
    if spec.model_kind in {"deep_two_tower", "hybrid"}:
        assert spec.two_tower is not None
        resolved_two_tower = TwoTowerConfig.from_mapping(spec.two_tower).to_mapping()
        if spec.schema_version == "model-run-spec/1.0":
            config_hash = canonical_json_sha256(resolved_two_tower)
        else:
            config_hash = canonical_json_sha256(
                {
                    "feature_source": spec.feature_source,
                    "feature_dimensions": spec.feature_dimensions,
                    "two_tower": resolved_two_tower,
                    "wide_weight": spec.wide_weight,
                    "rule_min_support": spec.rule_min_support,
                    "fusion_normalization": spec.fusion_normalization,
                }
            )
        family = "deep_two_tower" if spec.model_kind == "deep_two_tower" else "hybrid"
        features: tuple[str, ...] = (
            "user_id",
            "train_history",
            "item_text_features",
            "category",
            "price",
        )
        if spec.model_kind == "hybrid":
            features += ("train_apriori_rule_features",)
        return ModelDescriptor(
            model_id=spec.model_id,
            family=family,
            implementation_provenance="local-research-runner-v1",
            repository_url=None,
            repository_commit=None,
            objective="pairwise_bpr",
            negative_sampler="train_seen_exclusion_pcg64",
            input_features=features,
            config_sha256=config_hash,
            adapter_revision="ai-service-v2:proposed:v1",
        )
    family = {"random": "sanity_random", "mostpop": "sanity_mostpop", "rule_only": "wide_rule"}[
        spec.model_kind
    ]
    control_config: dict[str, Any] = {
        "model_kind": spec.model_kind,
        "rule_min_support": spec.rule_min_support,
    }
    if spec.schema_version == "model-run-spec/1.1":
        control_config.update(
            {
                "feature_source": spec.feature_source,
                "feature_dimensions": spec.feature_dimensions,
            }
        )
    config_hash = canonical_json_sha256(control_config)
    return ModelDescriptor(
        model_id=spec.model_id,
        family=family,
        implementation_provenance="local-research-runner-v1",
        repository_url=None,
        repository_commit=None,
        objective="non_learning_control" if spec.model_kind != "rule_only" else "train_only_rules",
        negative_sampler="not_applicable",
        input_features=("train_interactions",),
        config_sha256=config_hash,
        adapter_revision="ai-service-v2:local:v1",
    )


def train_local_model(
    snapshot: Snapshot,
    protocol: PreparedProtocol,
    spec: ModelRunSpec,
    *,
    seed: int,
) -> LocalModelBundle:
    """Fit one local candidate using only TRAIN-derived state."""

    descriptor = descriptor_for_spec(spec)
    if spec.model_kind == "random":
        return LocalModelBundle(spec, descriptor, RandomScorer(seed), None, None, None, None)
    if spec.model_kind == "mostpop":
        return LocalModelBundle(
            spec,
            descriptor,
            MostPopScorer(snapshot.events_by_split["train"]),
            None,
            None,
            None,
            None,
        )
    rules = None
    if spec.model_kind in {"rule_only", "hybrid"}:
        rules = AprioriRuleTable.fit(snapshot, min_support=spec.rule_min_support)
    if spec.model_kind == "rule_only":
        assert rules is not None
        return LocalModelBundle(
            spec, descriptor, RuleOnlyScorer(protocol, rules), None, None, rules, None
        )
    assert spec.two_tower is not None
    config = TwoTowerConfig.from_mapping(spec.two_tower)
    features = item_text_hash_features(snapshot, dimensions=spec.feature_dimensions)
    if features.source != spec.feature_source:
        raise ContractError("generated feature source does not match the admitted model spec")
    deep_model, report = train_two_tower(
        snapshot,
        features,
        config=config,
        seed=seed,
        model_id=spec.model_id,
        descriptor=descriptor,
    )
    if deep_model.describe() != descriptor:
        raise ContractError("trained model descriptor does not match registry spec")
    if spec.model_kind == "deep_two_tower":
        return LocalModelBundle(spec, descriptor, deep_model, features, deep_model, None, report)
    assert rules is not None
    wide = RuleOnlyScorer(protocol, rules)
    scorer = HybridScorer(
        deep_model,
        wide,
        wide_weight=spec.wide_weight,
        fusion_normalization=spec.fusion_normalization,
    )
    return LocalModelBundle(spec, descriptor, scorer, features, deep_model, rules, report)


__all__ = [
    "FEATURE_SOURCES",
    "FUSION_NORMALIZATIONS",
    "MODEL_KINDS",
    "LocalModelBundle",
    "ModelRunSpec",
    "default_spec",
    "descriptor_for_spec",
    "train_local_model",
]
