from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError, IntegrityError, ProtocolError, ScoreError
from ai_service_v2.evaluation.evaluator import (
    FullCatalogEvaluator,
    evaluator_implementation_sha256,
    evaluator_source_hashes,
)
from ai_service_v2.evaluation.metrics import ranking_metrics
from ai_service_v2.evaluation.persistence import load_evaluation, save_evaluation
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, load_strict_json
from ai_service_v2.protocol import PreparedProtocol, build_protocol
from ai_service_v2.statistics import hierarchical_paired_bootstrap, holm_adjust


def test_full_catalog_oracle_covers_mask_ties_and_primary_metrics(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=3)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        del candidates
        if user_id == 0:
            return np.asarray([100.0, 99.0, 80.0, 70.0, 60.0])
        return np.asarray([0.0, 99.0, 98.0, 50.0, 50.0])

    result = FullCatalogEvaluator(protocol).evaluate(
        scorer,
        run_id="r3-oracle-run",
        model_id="r3-oracle-model",
    )

    # User 0's seen items are deliberately highest-scoring, so masking must
    # leave item 2 at rank 1. User 1 has a tie between items 3 and 4; raw IDs
    # 10 < 25 make item 4 rank first deterministically.
    expected_ndcg_user_1 = 1.0 / math.log2(3.0)
    assert result.top_k_by_user[0] == (2, 3, 4)
    assert result.top_k_by_user[1] == (4, 3, 0)
    assert result.per_user_metrics["HR@3"] == (1.0, 1.0)
    assert result.per_user_metrics["NDCG@3"] == (1.0, expected_ndcg_user_1)
    assert result.per_user_metrics["GAUC"] == (1.0, 0.75)
    assert result.receipt.aggregate_metrics["GAUC"] == 0.875
    assert result.receipt.denominator_by_metric == {
        "HR@3": 2,
        "NDCG@3": 2,
        "GAUC": 2,
    }


def test_metric_formula_oracle_uses_binary_ndcg_and_exact_tie_aware_auc() -> None:
    row = ranking_metrics(
        scores=np.asarray([0.9, 0.8, 0.7, 0.6]),
        positive_indices={0, 2},
        negative_indices={1, 3},
        raw_item_ids=np.asarray([40, 30, 20, 10]),
        k=3,
    )
    expected_dcg = 1.0 + 1.0 / math.log2(4.0)
    expected_idcg = 1.0 + 1.0 / math.log2(3.0)
    assert row.hit_rate == 1.0
    assert row.ndcg == pytest.approx(expected_dcg / expected_idcg)
    assert row.gauc == pytest.approx(0.75)


def test_excluded_candidates_must_be_the_evaluator_mask() -> None:
    with pytest.raises(ScoreError, match="masked"):
        ranking_metrics(
            scores=np.asarray([1.0, 0.0, -1.0]),
            positive_indices={0},
            negative_indices={1},
            excluded_indices={2},
            raw_item_ids=np.asarray([1, 2, 3]),
            k=2,
        )


def test_prepared_protocol_rejects_catalog_or_test_state_drift(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    with pytest.raises(IntegrityError, match="candidate order hash"):
        PreparedProtocol(
            protocol.manifest,
            tuple(reversed(protocol.raw_item_ids)),
            protocol.cases,
            protocol.num_total_users,
        )

    bad_manifest = replace(protocol.manifest, test_set_opened=True)
    with pytest.raises(ProtocolError, match="TEST-open"):
        PreparedProtocol(
            bad_manifest,
            protocol.raw_item_ids,
            protocol.cases,
            protocol.num_total_users,
        )


def test_build_protocol_rejects_a_supplied_dataset_hash_drift(snapshot: Snapshot) -> None:
    with pytest.raises(IntegrityError, match="dataset manifest hash"):
        build_protocol(snapshot, split="val", cutoff=5, dataset_manifest_sha256="0" * 64)


def test_receipt_binds_the_exact_evaluator_source_bundle(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    result = FullCatalogEvaluator(protocol).evaluate(
        lambda user_id, candidates: np.zeros(len(candidates)),
        run_id="r3-hash-run",
        model_id="r3-hash-model",
    )
    source_hashes = evaluator_source_hashes()
    assert set(source_hashes) == {
        "evaluation/evaluator.py",
        "evaluation/metrics.py",
        "protocol.py",
    }
    assert all(len(value) == 64 for value in source_hashes.values())
    assert result.receipt.evaluator_implementation_sha256 == evaluator_implementation_sha256()
    assert result.receipt.protocol_manifest_sha256 == canonical_json_sha256(
        protocol.manifest.to_mapping()
    )
    assert result.receipt.candidate_order_sha256 == protocol.manifest.candidate_order_sha256


def test_persisted_receipt_rejects_evaluator_hash_substitution(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    result = FullCatalogEvaluator(protocol).evaluate(
        lambda user_id, candidates: np.zeros(len(candidates)),
        run_id="r3-persisted-hash-run",
        model_id="r3-persisted-hash-model",
    )
    root = save_evaluation(result, tmp_path / "evaluation").root
    receipt_path = root / "evaluation_receipt.json"
    receipt = load_strict_json(receipt_path)
    receipt["receipt"]["evaluator_implementation_sha256"] = "0" * 64
    receipt_path.write_bytes(canonical_json_bytes(receipt) + b"\n")
    with pytest.raises(IntegrityError, match="implementation"):
        load_evaluation(root)


def test_hierarchical_bootstrap_matches_the_registered_seed_user_schedule() -> None:
    candidate = np.asarray([[0.2, 0.4], [0.6, 0.8]])
    baseline = np.zeros_like(candidate)
    interval = hierarchical_paired_bootstrap(candidate, baseline, samples=7, seed=19)

    rng = np.random.Generator(np.random.PCG64(19))
    expected_samples: list[float] = []
    for _ in range(7):
        selected_seeds = [int(rng.integers(0, 2)) for _ in range(2)]
        cells: list[float] = []
        for selected_seed in selected_seeds:
            selected_users = rng.integers(0, 2, size=2)
            cells.extend((candidate[selected_seed, selected_users]).tolist())
        expected_samples.append(float(np.mean(cells)))
    expected_lower, expected_upper = np.quantile(
        np.asarray(expected_samples), [0.025, 0.975], method="linear"
    )
    assert interval.mean_delta == pytest.approx(float(np.mean(candidate)))
    assert interval.lower == pytest.approx(float(expected_lower))
    assert interval.upper == pytest.approx(float(expected_upper))


def test_holm_is_deterministic_and_rejects_nonfinite_or_non_numeric_values() -> None:
    assert holm_adjust({"a": 0.01, "b": 0.04, "c": 0.2}) == {
        "a": 0.03,
        "b": 0.08,
        "c": 0.2,
    }
    with pytest.raises(ContractError, match="p-value"):
        holm_adjust({"nan": float("nan")})
    with pytest.raises(ContractError, match="p-value"):
        bad_values = {"text": "0.1"}
        holm_adjust(cast(Mapping[str, float], bad_values))
