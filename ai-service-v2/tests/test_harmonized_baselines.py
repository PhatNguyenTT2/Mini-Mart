from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.adapters.harmonized_baselines import (
    HarmonizedBaselineSpec,
    fit_harmonized_baseline,
    load_harmonized_baseline_checkpoint,
    save_harmonized_baseline_checkpoint,
)
from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.protocol import build_protocol

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fixture-retail-v1"


def _spec(model_kind: str) -> HarmonizedBaselineSpec:
    if model_kind == "itemknn":
        parameters: dict[str, int | float | str] = {
            "top_k": 2,
            "similarity": "binary_cosine",
            "interaction_signal": "purchase",
        }
        model_id = "fixture-itemknn"
    else:
        parameters = {
            "embedding_dim": 4,
            "epochs": 2,
            "learning_rate": 0.01,
            "l2": 0.00001,
            "negatives_per_positive": 1,
            "interaction_signal": "purchase",
        }
        model_id = "fixture-bpr-mf"
    return HarmonizedBaselineSpec(model_kind=model_kind, model_id=model_id, parameters=parameters)


@pytest.mark.parametrize("model_kind", ("itemknn", "bpr_mf"))
def test_harmonized_baseline_checkpoint_round_trip(model_kind: str, tmp_path: Path) -> None:
    snapshot = load_canonical_snapshot(FIXTURE_ROOT)
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    model, report = fit_harmonized_baseline(snapshot, protocol, _spec(model_kind), seed=42)
    before = model(protocol.eligible_user_ids[0], protocol.candidate_item_ids)
    manifest = save_harmonized_baseline_checkpoint(
        model,
        root=tmp_path / "checkpoint",
        run_id=f"run-{model_kind}",
        seed=42,
        checkpoint_rule="fixture-fixed",
    )
    loaded, replayed_manifest = load_harmonized_baseline_checkpoint(
        tmp_path / "checkpoint", snapshot=snapshot, protocol=protocol
    )
    after = loaded(protocol.eligible_user_ids[0], protocol.candidate_item_ids)

    assert np.array_equal(before, after)
    assert np.isfinite(after).all()
    assert replayed_manifest == manifest
    assert report["fit_scope"] == "TRAIN_PURCHASES_ONLY"


def test_bpr_training_is_seed_deterministic() -> None:
    snapshot = load_canonical_snapshot(FIXTURE_ROOT)
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    first, first_report = fit_harmonized_baseline(snapshot, protocol, _spec("bpr_mf"), seed=7)
    second, second_report = fit_harmonized_baseline(snapshot, protocol, _spec("bpr_mf"), seed=7)

    assert np.array_equal(first.user_factors, second.user_factors)
    assert np.array_equal(first.item_factors, second.item_factors)
    assert first_report == second_report


def test_baseline_spec_and_checkpoint_fail_closed(tmp_path: Path) -> None:
    mapping = _spec("itemknn").to_mapping()
    mapping["source_commit"] = "0" * 40
    with pytest.raises(ContractError, match="source commit"):
        HarmonizedBaselineSpec.from_mapping(mapping)

    snapshot = load_canonical_snapshot(FIXTURE_ROOT)
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    model, _report = fit_harmonized_baseline(snapshot, protocol, _spec("itemknn"), seed=42)
    checkpoint_root = tmp_path / "checkpoint"
    save_harmonized_baseline_checkpoint(
        model,
        root=checkpoint_root,
        run_id="itemknn",
        seed=42,
        checkpoint_rule="fixture-fixed",
    )
    payload = (checkpoint_root / "checkpoint.npz").read_bytes()
    (checkpoint_root / "checkpoint.npz").write_bytes(payload + b"tamper")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        load_harmonized_baseline_checkpoint(checkpoint_root, snapshot=snapshot, protocol=protocol)
