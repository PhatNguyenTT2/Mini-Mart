from __future__ import annotations

from pathlib import Path

import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.hashing import load_strict_json
from ai_service_v2.models.registry import (
    ModelRunSpec,
    default_spec,
    descriptor_for_spec,
    train_local_model,
)
from ai_service_v2.protocol import build_protocol

CONFIG_ROOT = Path(__file__).parents[1] / "configs"


def test_local_registry_wires_controls_and_ablations(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    for kind in ("random", "mostpop", "rule_only", "deep_two_tower", "hybrid"):
        spec = default_spec(kind, feature_dimensions=8)
        bundle = train_local_model(snapshot, protocol, spec, seed=42)
        result = FullCatalogEvaluator(protocol).evaluate(
            bundle.scorer, run_id=f"{kind}-run", model_id=spec.model_id
        )
        assert result.receipt.verdict == "PASS"
        assert bundle.descriptor.model_id == spec.model_id


def test_example_registry_configs_are_strict_and_cover_local_models() -> None:
    files = sorted(CONFIG_ROOT.glob("*.json"))
    specs = [ModelRunSpec.from_mapping(load_strict_json(path)) for path in files]

    assert {spec.model_kind for spec in specs} == {
        "random",
        "mostpop",
        "rule_only",
        "deep_two_tower",
        "hybrid",
    }
    assert len({spec.model_id for spec in specs}) == len(specs)


def test_hybrid_descriptor_hash_binds_fusion_and_feature_controls() -> None:
    base = default_spec("hybrid", feature_dimensions=16, wide_weight=0.5)
    changed_weight = default_spec("hybrid", feature_dimensions=16, wide_weight=0.75)
    changed_normalization = default_spec(
        "hybrid",
        feature_dimensions=16,
        wide_weight=0.5,
        fusion_normalization="none",
    )
    changed_features = default_spec("hybrid", feature_dimensions=32, wide_weight=0.5)
    hashes = {
        descriptor_for_spec(spec).config_sha256
        for spec in (base, changed_weight, changed_normalization, changed_features)
    }
    assert len(hashes) == 4


def test_legacy_model_spec_round_trips_without_rewriting_its_hash_surface() -> None:
    current = default_spec("hybrid", feature_dimensions=8).to_mapping()
    legacy = {key: value for key, value in current.items() if key != "fusion_normalization"}
    legacy["schema_version"] = "model-run-spec/1.0"
    parsed = ModelRunSpec.from_mapping(legacy)
    assert parsed.fusion_normalization == "none"
    assert parsed.to_mapping() == legacy


def test_legacy_model_spec_is_inspection_only_at_training_seam(snapshot: Snapshot) -> None:
    legacy = default_spec("deep_two_tower", feature_dimensions=8).to_mapping()
    legacy.pop("fusion_normalization")
    legacy["schema_version"] = "model-run-spec/1.0"
    spec = ModelRunSpec.from_mapping(legacy)
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    with pytest.raises(ContractError, match="inspection-only"):
        train_local_model(snapshot, protocol, spec, seed=42)


@pytest.mark.parametrize(
    "two_tower",
    [
        {},
        {
            "embedding_dim": True,
            "hidden_dim": 32,
            "epochs": 5,
            "learning_rate": 0.03,
            "l2": 1e-5,
            "negatives_per_positive": 1,
        },
        {
            "embedding_dim": 16,
            "hidden_dim": 32,
            "epochs": 5.5,
            "learning_rate": 0.03,
            "l2": 1e-5,
            "negatives_per_positive": 1,
        },
        {
            "embedding_dim": 16,
            "hidden_dim": 32,
            "epochs": 5,
            "learning_rate": float("inf"),
            "l2": 1e-5,
            "negatives_per_positive": 1,
        },
    ],
)
def test_current_deep_spec_rejects_incomplete_or_ill_typed_effective_config(
    two_tower: dict[str, object],
) -> None:
    mapping = default_spec("deep_two_tower", feature_dimensions=8).to_mapping()
    mapping["two_tower"] = two_tower

    with pytest.raises(ContractError):
        ModelRunSpec.from_mapping(mapping)


def test_deep_spec_rejects_an_unsupported_feature_generator_before_training() -> None:
    mapping = default_spec("deep_two_tower", feature_dimensions=8).to_mapping()
    mapping["feature_source"] = "declared_but_not_implemented"

    with pytest.raises(ContractError, match="feature source"):
        ModelRunSpec.from_mapping(mapping)


def test_admitted_feature_source_matches_the_generator_output(
    snapshot: Snapshot,
) -> None:
    spec = default_spec("deep_two_tower", feature_dimensions=8)
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    bundle = train_local_model(snapshot, protocol, spec, seed=42)

    assert bundle.features is not None
    assert bundle.features.source == spec.feature_source
