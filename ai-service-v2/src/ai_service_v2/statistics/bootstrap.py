"""Deterministic paired bootstrap routines for model comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from ai_service_v2.errors import ContractError


@dataclass(frozen=True)
class BootstrapInterval:
    mean_delta: float
    lower: float
    upper: float
    samples: int
    seed: int


def _validate_pair(candidate: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
    candidate: np.ndarray,
    baseline: np.ndarray,
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
    candidate: np.ndarray,
    baseline: np.ndarray,
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


__all__ = [
    "BootstrapInterval",
    "hierarchical_paired_bootstrap",
    "holm_adjust",
    "paired_bootstrap_delta",
]
