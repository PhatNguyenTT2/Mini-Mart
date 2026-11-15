from __future__ import annotations

import numpy as np
import pytest

from ai_service_v2.errors import ContractError
from ai_service_v2.statistics import (
    crossed_paired_bootstrap,
    hierarchical_paired_bootstrap,
    holm_adjust,
    paired_bootstrap_delta,
    resolve_secondary_holm_family,
)


def test_paired_bootstrap_is_deterministic() -> None:
    candidate = np.array([0.4, 0.6, 0.8, 0.5])
    baseline = np.array([0.3, 0.5, 0.7, 0.5])
    first = paired_bootstrap_delta(candidate, baseline, samples=100, seed=7)
    second = paired_bootstrap_delta(candidate, baseline, samples=100, seed=7)
    assert first == second
    assert first.mean_delta == pytest.approx(0.075)


def test_hierarchical_bootstrap_preserves_shape_and_pairing() -> None:
    candidate = np.array([[0.5, 0.6], [0.7, 0.8], [0.4, 0.5]])
    baseline = candidate - 0.1
    interval = hierarchical_paired_bootstrap(candidate, baseline, samples=100, seed=42)
    assert interval.mean_delta == pytest.approx(0.1)
    assert interval.lower <= interval.mean_delta <= interval.upper


def test_crossed_bootstrap_replays_seedsequence_cartesian_schedule() -> None:
    candidate = np.array(
        [
            [0.9, 0.1, 0.4, 0.8],
            [0.2, 0.7, 0.3, 0.5],
            [0.6, 0.4, 0.9, 0.0],
        ],
        dtype=np.float64,
    )
    baseline = np.array(
        [
            [0.4, 0.2, 0.5, 0.1],
            [0.3, 0.1, 0.4, 0.2],
            [0.2, 0.5, 0.3, 0.1],
        ],
        dtype=np.float64,
    )
    result = crossed_paired_bootstrap(
        candidate,
        baseline,
        resampling_schedule_id="V5_MAIN_NDCG_S5",
        schedule_index=0,
        samples=11,
    )

    delta = candidate - baseline
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(42, spawn_key=(0,))))
    expected = []
    for _ in range(11):
        users = rng.integers(0, delta.shape[1], size=delta.shape[1])
        seeds = rng.integers(0, delta.shape[0], size=delta.shape[0])
        expected.append(float(delta[np.ix_(seeds, users)].mean()))
    observed = float(delta.mean())
    lower, upper = np.quantile(expected, [0.025, 0.975], method="linear")
    centered = np.asarray(expected) - observed
    expected_p = min(
        1.0,
        (1 + int(np.count_nonzero(np.abs(centered) >= abs(observed)))) / 12,
    )

    assert result.mean_delta == observed
    assert result.lower == lower
    assert result.upper == upper
    assert result.raw_two_sided_p_value == expected_p
    assert result.seed_effects == tuple(float(value) for value in delta.mean(axis=1))
    assert result.schema_version == "crossed-paired-bootstrap/1.0"


def test_crossed_bootstrap_schedule_and_missing_cells_fail_closed() -> None:
    candidate = np.arange(15, dtype=np.float64).reshape(3, 5) / 10
    baseline = np.zeros((3, 5), dtype=np.float64)
    first = crossed_paired_bootstrap(
        candidate,
        baseline,
        resampling_schedule_id="V5_MAIN_NDCG_S5",
        schedule_index=0,
        samples=50,
    )
    second = crossed_paired_bootstrap(
        candidate,
        baseline,
        resampling_schedule_id="V5_MAIN_HR_S5",
        schedule_index=1,
        samples=50,
    )
    assert (first.lower, first.upper, first.raw_two_sided_p_value) != (
        second.lower,
        second.upper,
        second.raw_two_sided_p_value,
    )

    incomplete = candidate.copy()
    incomplete[1, 2] = np.nan
    with pytest.raises(ContractError, match="finite"):
        crossed_paired_bootstrap(
            incomplete,
            baseline,
            resampling_schedule_id="V5_MAIN_NDCG_S5",
            schedule_index=0,
        )


def test_holm_adjustment_and_validation() -> None:
    adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": 0.2})
    assert adjusted["a"] <= adjusted["b"] <= adjusted["c"]
    with pytest.raises(ContractError, match="p-value"):
        holm_adjust({"bad": 1.1})


def test_secondary_holm_family_retains_nine_deferred_instacart_slots() -> None:
    comparisons = [
        {"test_id": f"V5_{index}", "dataset": "V5_INTERNAL_CURRENT"} for index in range(8)
    ] + [{"test_id": f"INSTACART_{index}", "dataset": "INSTACART_EXTERNAL"} for index in range(9)]
    estimated = {f"V5_{index}": 0.01 * (index + 1) for index in range(8)}

    resolution = resolve_secondary_holm_family(comparisons, estimated)
    slots = {slot["test_id"]: slot for slot in resolution["slots"]}

    assert resolution["family_size"] == 17
    assert resolution["estimated_slot_count"] == 8
    assert resolution["not_tested_slot_count"] == 9
    for index in range(9):
        slot = slots[f"INSTACART_{index}"]
        assert slot["status"] == "NOT_TESTED_NO_EFFECT_OR_INTERVAL_REPORTED"
        assert slot["raw_p_value"] is None
        assert slot["adjustment_only_raw_p_value"] == 1.0
        assert slot["adjustment_value_is_estimated_p_value"] is False


def test_secondary_holm_family_rejects_instacart_estimates_and_wrong_size() -> None:
    comparisons = [
        {"test_id": f"V5_{index}", "dataset": "V5_INTERNAL_CURRENT"} for index in range(8)
    ] + [{"test_id": f"INSTACART_{index}", "dataset": "INSTACART_EXTERNAL"} for index in range(9)]
    with pytest.raises(ContractError, match="cannot carry estimated"):
        resolve_secondary_holm_family(comparisons, {"INSTACART_0": 0.5})
    with pytest.raises(ContractError, match="exactly 17"):
        resolve_secondary_holm_family(comparisons[:-1], {})
