from __future__ import annotations

from pathlib import Path

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.hashing import load_strict_json
from ai_service_v2.models.registry import ModelRunSpec, default_spec, train_local_model
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
