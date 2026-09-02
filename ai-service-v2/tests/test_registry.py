from __future__ import annotations

from pathlib import Path

from ai_service_v2.data.snapshot import Snapshot
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
