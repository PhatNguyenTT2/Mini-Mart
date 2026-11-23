"""Deterministic paired bootstrap routines for model comparisons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from hybrid_recsys.array_types import Array
from hybrid_recsys.errors import ContractError


@dataclass(frozen=True)
class BootstrapInterval:
    mean_delta: float
    lower: float
    upper: float
    samples: int
    seed: int


@dataclass(frozen=True)
class CrossedBootstrapResult:
    mean_delta: float
    lower: float
    upper: float
    raw_two_sided_p_value: float
    seed_effects: tuple[float, ...]
    samples: int
    root_seed: int
    schedule_index: int
    resampling_schedule_id: str
    schema_version: str = "crossed-paired-bootstrap/1.0"


def _validate_pair(candidate: Array, baseline: Array) -> tuple[Array, Array]:
    try:
        left = np.asarray(candidate, dtype=np.float64)
        right = np.asarray(baseline, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ContractError("bootstrap arrays must be numeric and rectangular") from error
    if left.shape != right.shape or left.ndim == 0 or not left.size:
        raise ContractError("paired arrays must be non-empty and have identical shape")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ContractError("bootstrap arrays must contain only finite values")
    return left, right


def _validate_controls(samples: object, seed: object) -> tuple[int, int]:
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        raise ContractError("samples must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ContractError("seed must be a non-negative integer")
    return int(samples), int(seed)


def paired_bootstrap_delta(
    candidate: Array,
    baseline: Array,
    *,
    samples: int = 2_000,
    seed: int = 42,
) -> BootstrapInterval:
    """Paired user bootstrap for a single seed or already flattened vector."""

    left, right = _validate_pair(candidate, baseline)
    if left.ndim != 1:
        raise ContractError("paired_bootstrap_delta expects one-dimensional arrays")
    samples, seed = _validate_controls(samples, seed)
    delta = left - right
    rng = np.random.Generator(np.random.PCG64(seed))
    means = np.empty(samples, dtype=np.float64)
    for index in range(samples):
        selected = rng.integers(0, len(delta), size=len(delta))
        means[index] = float(delta[selected].mean())
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    return BootstrapInterval(float(delta.mean()), float(lower), float(upper), samples, seed)


def hierarchical_paired_bootstrap(
    candidate: Array,
    baseline: Array,
    *,
    samples: int = 2_000,
    seed: int = 42,
) -> BootstrapInterval:
    """Resample training seeds and users while preserving model pairing.

    Inputs are ``[seed, user]`` metric matrices.  A replicate first resamples
    seed occurrences and then independently resamples users within every
    occurrence.  The same selected user indices are used for candidate and
    baseline, preserving the paired estimand.
    """

    left, right = _validate_pair(candidate, baseline)
    if left.ndim != 2 or left.shape[0] < 1 or left.shape[1] < 1:
        raise ContractError("hierarchical bootstrap expects a non-empty [seed, user] matrix")
    samples, seed = _validate_controls(samples, seed)
    seed_count, user_count = left.shape
    rng = np.random.Generator(np.random.PCG64(seed))
    means = np.empty(samples, dtype=np.float64)
    for sample_index in range(samples):
        selected_seeds: list[int] = [int(rng.integers(0, seed_count)) for _ in range(seed_count)]
        deltas: list[float] = []
        for selected_seed_value in selected_seeds:
            selected_seed = int(selected_seed_value)
            selected_users = rng.integers(0, user_count, size=user_count)
            seed_deltas = left[selected_seed, selected_users] - right[selected_seed, selected_users]
            deltas.extend(seed_deltas.tolist())
        means[sample_index] = float(np.mean(deltas))
    observed = float(np.mean(left - right))
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    return BootstrapInterval(observed, float(lower), float(upper), samples, seed)


def crossed_paired_bootstrap(
    candidate: Array,
    baseline: Array,
    *,
    resampling_schedule_id: str,
    schedule_index: int,
    samples: int = 2_000,
    root_seed: int = 42,
) -> CrossedBootstrapResult:
    """Run the frozen crossed user-by-seed paired bootstrap.

    Inputs are complete seed-by-user matrices. Each replicate draws one user
    vector first, then one seed vector, and evaluates their Cartesian product
    with identical indices for candidate and comparator.
    """

    left, right = _validate_pair(candidate, baseline)
    if left.ndim != 2 or left.shape[0] < 1 or left.shape[1] < 1:
        raise ContractError("crossed bootstrap expects a non-empty [seed, user] matrix")
    samples, root_seed = _validate_controls(samples, root_seed)
    if (
        isinstance(schedule_index, bool)
        or not isinstance(schedule_index, int)
        or schedule_index < 0
    ):
        raise ContractError("schedule_index must be a non-negative integer")
    if not isinstance(resampling_schedule_id, str) or not resampling_schedule_id:
        raise ContractError("resampling_schedule_id must be a non-empty string")

    delta = left - right
    seed_count, user_count = delta.shape
    seed_sequence = np.random.SeedSequence(root_seed, spawn_key=(schedule_index,))
    rng = np.random.Generator(np.random.PCG64(seed_sequence))
    effects = np.empty(samples, dtype=np.float64)
    for replicate_index in range(samples):
        selected_users = rng.integers(0, user_count, size=user_count)
        selected_seeds = rng.integers(0, seed_count, size=seed_count)
        effects[replicate_index] = float(delta[np.ix_(selected_seeds, selected_users)].mean())

    observed = float(delta.mean())
    lower, upper = np.quantile(effects, [0.025, 0.975], method="linear")
    centered = effects - observed
    extreme_count = int(np.count_nonzero(np.abs(centered) >= abs(observed)))
    raw_p_value = min(1.0, (1.0 + extreme_count) / (samples + 1.0))
    return CrossedBootstrapResult(
        mean_delta=observed,
        lower=float(lower),
        upper=float(upper),
        raw_two_sided_p_value=float(raw_p_value),
        seed_effects=tuple(float(value) for value in delta.mean(axis=1)),
        samples=samples,
        root_seed=root_seed,
        schedule_index=schedule_index,
        resampling_schedule_id=resampling_schedule_id,
    )


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Return Holm step-down adjusted p-values without external dependencies."""

    if not p_values:
        raise ContractError("at least one p-value is required")
    normalized: dict[str, float] = {}
    for name, value in p_values.items():
        if not isinstance(name, str) or not name:
            raise ContractError("p-value names must be non-empty strings")
        candidate_value: object = value
        if (
            isinstance(candidate_value, bool)
            or not isinstance(candidate_value, (int, float))
            or not np.isfinite(candidate_value)
        ):
            raise ContractError(f"invalid p-value for {name}")
        if not 0.0 <= candidate_value <= 1.0:
            raise ContractError(f"invalid p-value for {name}")
        normalized[name] = float(candidate_value)
    ordered = sorted(normalized.items(), key=lambda pair: (pair[1], pair[0]))
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (name, p_value) in enumerate(ordered):
        corrected = min(1.0, (count - index) * p_value)
        running = max(running, corrected)
        adjusted[name] = running
    return {name: adjusted[name] for name in normalized}


def resolve_secondary_holm_family(
    comparisons: Sequence[Mapping[str, object]],
    estimated_p_values: Mapping[str, float],
    *,
    family_alpha: float = 0.05,
) -> dict[str, object]:
    """Resolve the frozen 17-slot family without estimating deferred slots."""

    if len(comparisons) != 17:
        raise ContractError("secondary Holm family must contain exactly 17 slots")
    if (
        isinstance(family_alpha, bool)
        or not isinstance(family_alpha, (int, float))
        or not np.isfinite(family_alpha)
        or not 0.0 < float(family_alpha) < 1.0
    ):
        raise ContractError("family_alpha must be finite and between zero and one")
    slots: list[tuple[str, str]] = []
    for comparison in comparisons:
        test_id = comparison.get("test_id")
        dataset = comparison.get("dataset")
        if not isinstance(test_id, str) or not test_id:
            raise ContractError("secondary Holm slot has an invalid test_id")
        if dataset not in {"V5_INTERNAL_CURRENT", "INSTACART_EXTERNAL"}:
            raise ContractError("secondary Holm slot has an invalid dataset")
        slots.append((test_id, str(dataset)))
    test_ids = [test_id for test_id, _ in slots]
    if len(set(test_ids)) != 17:
        raise ContractError("secondary Holm family has duplicate test IDs")
    instacart_ids = {test_id for test_id, dataset in slots if dataset == "INSTACART_EXTERNAL"}
    if len(instacart_ids) != 9:
        raise ContractError("secondary Holm family must retain nine deferred Instacart slots")
    unknown = set(estimated_p_values) - set(test_ids)
    if unknown:
        raise ContractError("estimated p-values contain an unknown Holm slot")
    if set(estimated_p_values) & instacart_ids:
        raise ContractError("deferred Instacart slots cannot carry estimated p-values")

    adjustment_values: dict[str, float] = {}
    for test_id, _ in slots:
        value = estimated_p_values.get(test_id, 1.0)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(value)
            or not 0.0 <= float(value) <= 1.0
        ):
            raise ContractError(f"invalid raw p-value for {test_id}")
        adjustment_values[test_id] = float(value)
    adjusted = holm_adjust(adjustment_values)

    resolved_slots: list[dict[str, object]] = []
    for test_id, dataset in slots:
        estimated = test_id in estimated_p_values
        resolved_slots.append(
            {
                "test_id": test_id,
                "dataset": dataset,
                "status": (
                    "ESTIMATED" if estimated else "NOT_TESTED_NO_EFFECT_OR_INTERVAL_REPORTED"
                ),
                "raw_p_value": (float(estimated_p_values[test_id]) if estimated else None),
                "adjustment_only_raw_p_value": adjustment_values[test_id],
                "holm_adjusted_p_value": adjusted[test_id],
                "reject": estimated and adjusted[test_id] <= float(family_alpha),
                "adjustment_value_is_estimated_p_value": estimated,
            }
        )
    return {
        "schema_version": "secondary-holm-family-resolution/1.0",
        "family_size": 17,
        "family_alpha": float(family_alpha),
        "estimated_slot_count": len(estimated_p_values),
        "not_tested_slot_count": 17 - len(estimated_p_values),
        "instacart_deferred_slot_count": 9,
        "slots": resolved_slots,
    }


__all__ = [
    "BootstrapInterval",
    "CrossedBootstrapResult",
    "crossed_paired_bootstrap",
    "hierarchical_paired_bootstrap",
    "holm_adjust",
    "paired_bootstrap_delta",
    "resolve_secondary_holm_family",
]
