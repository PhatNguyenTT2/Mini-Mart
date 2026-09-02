from __future__ import annotations

import numpy as np
import pytest

from ai_service_v2.errors import ContractError
from ai_service_v2.statistics import (
    hierarchical_paired_bootstrap,
    holm_adjust,
    paired_bootstrap_delta,
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


def test_holm_adjustment_and_validation() -> None:
    adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": 0.2})
    assert adjusted["a"] <= adjusted["b"] <= adjusted["c"]
    with pytest.raises(ContractError, match="p-value"):
        holm_adjust({"bad": 1.1})
