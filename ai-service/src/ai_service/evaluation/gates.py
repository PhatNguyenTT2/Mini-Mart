"""Strict single-seed victory gates over one aligned full-catalog comparison."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import (
    EVALUATION_SCHEMA_VERSION,
    ColdParityReport,
    MetricBaselineSelection,
    MetricGateResult,
    SplitName,
    VictoryMatrix,
)
from ai_service.evaluation.baselines import BaselineComparisonReport, _mean_report
from ai_service.evaluation.full_catalog import EvaluationResult
from ai_service.evaluation.metrics import paired_bootstrap_delta
from ai_service.evaluation.semantic_traps import SemanticTrapReport


@dataclass(frozen=True)
class SingleSeedGateInputs:
    comparison: BaselineComparisonReport
    cold_parity: ColdParityReport
    semantic_traps: SemanticTrapReport
    seed: int = 42
    split: SplitName = SplitName.VAL
    comparison_signature: str = ""


def _mean_random_result(comparison: BaselineComparisonReport) -> EvaluationResult:
    first = comparison.random_seed_results[0]
    return EvaluationResult(
        report=_mean_report([row.report for row in comparison.random_seed_results]),
        user_ids=first.user_ids,
        per_user_hr=np.mean([row.per_user_hr for row in comparison.random_seed_results], axis=0),
        per_user_ndcg=np.mean(
            [row.per_user_ndcg for row in comparison.random_seed_results], axis=0
        ),
        per_user_gauc=np.mean(
            [row.per_user_gauc for row in comparison.random_seed_results], axis=0
        ),
        top_k_by_user=first.top_k_by_user,
    )


def _competitors(comparison: BaselineComparisonReport) -> dict[str, EvaluationResult]:
    return {
        "persona_only": comparison.persona_only,
        "item_cf": comparison.item_cf,
        "sbert_centroid": comparison.sbert_centroid,
        "apriori_only": comparison.apriori_only,
        "deep_only": comparison.deep_only,
        "noisy_hybrid": comparison.noisy_hybrid,
        "random": _mean_random_result(comparison),
    }


def _select_strongest_competitor(
    comparison: BaselineComparisonReport,
    *,
    metric: Literal["gauc", "hr_at_k", "ndcg_at_k"],
) -> tuple[str, EvaluationResult]:
    competitors = _competitors(comparison)
    name = max(
        competitors, key=lambda candidate: float(getattr(competitors[candidate].report, metric))
    )
    return name, competitors[name]


def _domination_gate(
    comparison: BaselineComparisonReport,
    *,
    metric: Literal["gauc", "hr_at_k", "ndcg_at_k"],
    gate_name: str,
    samples: int,
    seed: int,
) -> tuple[MetricGateResult, str]:
    baseline_name, baseline = _select_strongest_competitor(comparison, metric=metric)
    per_user_name = f"per_user_{metric.replace('_at_k', '')}"
    candidate_values = np.asarray(getattr(comparison.hybrid, per_user_name), dtype=np.float64)
    baseline_values = np.asarray(getattr(baseline, per_user_name), dtype=np.float64)
    interval = paired_bootstrap_delta(candidate_values, baseline_values, samples=samples, seed=seed)
    candidate_mean = float(getattr(comparison.hybrid.report, metric))
    baseline_mean = float(getattr(baseline.report, metric))
    passed = candidate_mean > baseline_mean and interval.lower > 0.0
    gate = MetricGateResult(
        name=gate_name,
        passed=passed,
        observed=candidate_mean,
        target=baseline_mean,
        description=(
            f"Hybrid {metric} must beat strongest competitor {baseline_name} "
            "with paired CI lower > 0"
        ),
        candidate_name="hybrid",
        baseline_name=baseline_name,
        candidate_mean=candidate_mean,
        baseline_mean=baseline_mean,
        delta_mean=float(interval.mean_delta),
        ci_lower=float(interval.lower),
        ci_upper=float(interval.upper),
        threshold=0.0,
        failure_reason=None if passed else f"Hybrid {metric} does not dominate {baseline_name}",
    )
    return gate, baseline_name


def evaluate_single_seed(
    inputs: SingleSeedGateInputs,
    settings: Settings | int | None = None,
    *,
    bootstrap_samples: int | None = None,
) -> VictoryMatrix:
    if isinstance(settings, int):
        bootstrap_samples = settings
        settings = None
    samples = bootstrap_samples or (settings.eval.bootstrap_samples if settings else 2_000)
    random_tolerance = settings.eval.random_gauc_tolerance if settings else 0.02
    minimum_gauc = settings.eval.minimum_gauc if settings else 0.75
    wide_tolerance = settings.eval.wide_zero_atol if settings else 1e-7
    comparison = inputs.comparison
    if len(comparison.random_seed_results) != 10:
        raise ValueError("single-seed gates require exactly 10 random baseline seeds")

    random = _mean_random_result(comparison)
    random_interval = paired_bootstrap_delta(
        random.per_user_gauc,
        np.full_like(random.per_user_gauc, 0.5),
        samples=samples,
        seed=inputs.seed,
    )
    random_gauc = float(random.report.gauc)
    random_passed = (
        0.5 - random_tolerance <= random_gauc <= 0.5 + random_tolerance
        and random_interval.lower <= 0.0 <= random_interval.upper
    )
    gates = [
        MetricGateResult(
            name="random_gauc",
            passed=random_passed,
            observed=random_gauc,
            target=0.5,
            description="Random GAUC must remain chance-like and its CI must contain 0.5",
            candidate_name="random",
            baseline_name="chance",
            candidate_mean=random_gauc,
            baseline_mean=0.5,
            delta_mean=float(random_interval.mean_delta),
            ci_lower=float(random_interval.lower),
            ci_upper=float(random_interval.upper),
            threshold=random_tolerance,
            failure_reason=None if random_passed else "random GAUC sanity failed",
        )
    ]
    hybrid_gauc = float(comparison.hybrid.report.gauc)
    minimum_passed = hybrid_gauc >= minimum_gauc
    gates.append(
        MetricGateResult(
            name="hybrid_minimum_gauc",
            passed=minimum_passed,
            observed=hybrid_gauc,
            target=minimum_gauc,
            description="Hybrid GAUC must satisfy the absolute release floor",
            candidate_name="hybrid",
            baseline_name="minimum",
            candidate_mean=hybrid_gauc,
            baseline_mean=minimum_gauc,
            delta_mean=hybrid_gauc - minimum_gauc,
            ci_lower=hybrid_gauc - minimum_gauc,
            ci_upper=hybrid_gauc - minimum_gauc,
            threshold=minimum_gauc,
            failure_reason=None if minimum_passed else "Hybrid GAUC below minimum",
        )
    )
    gauc_gate, gauc_baseline = _domination_gate(
        comparison,
        metric="gauc",
        gate_name="gauc_domination",
        samples=samples,
        seed=inputs.seed + 11,
    )
    hr_gate, hr_baseline = _domination_gate(
        comparison,
        metric="hr_at_k",
        gate_name="hr_domination",
        samples=samples,
        seed=inputs.seed + 13,
    )
    ndcg_gate, ndcg_baseline = _domination_gate(
        comparison,
        metric="ndcg_at_k",
        gate_name="ndcg_domination",
        samples=samples,
        seed=inputs.seed + 17,
    )
    gates.extend((gauc_gate, hr_gate, ndcg_gate))

    traps_passed = bool(
        inputs.semantic_traps.total == 10
        and inputs.semantic_traps.passed == 10
        and inputs.semantic_traps.all_passed
    )
    gates.append(
        MetricGateResult(
            name="semantic_traps",
            passed=traps_passed,
            observed=float(inputs.semantic_traps.passed),
            target=10.0,
            description="All ten semantic traps must pass",
            candidate_name="hybrid",
            baseline_name="semantic_traps",
            candidate_mean=float(inputs.semantic_traps.passed),
            baseline_mean=10.0,
            delta_mean=float(inputs.semantic_traps.passed - 10),
            ci_lower=float(inputs.semantic_traps.passed - 10),
            ci_upper=float(inputs.semantic_traps.passed - 10),
            threshold=10.0,
            failure_reason=None if traps_passed else "semantic traps failed",
        )
    )
    cold_passed = bool(inputs.cold_parity.passed)
    gates.append(
        MetricGateResult(
            name="cold_parity",
            passed=cold_passed,
            observed=float(inputs.cold_parity.max_abs_wide_logit),
            target=wide_tolerance,
            description="Cold items must preserve zero-Wide Hybrid/Deep parity",
            candidate_name="hybrid",
            baseline_name="deep_only",
            candidate_mean=float(inputs.cold_parity.max_abs_wide_logit),
            baseline_mean=0.0,
            delta_mean=float(inputs.cold_parity.max_abs_wide_logit),
            ci_lower=float(inputs.cold_parity.max_abs_wide_logit),
            ci_upper=float(inputs.cold_parity.max_abs_wide_logit),
            threshold=wide_tolerance,
            failure_reason=None if cold_passed else "cold parity failed",
        )
    )
    all_passed = all(gate.passed for gate in gates)
    selection = MetricBaselineSelection(
        gauc=gauc_baseline,
        hr_at_k=hr_baseline,
        ndcg_at_k=ndcg_baseline,
    )
    document = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "seed": inputs.seed,
        "split": inputs.split.value,
        "comparison_signature": inputs.comparison_signature,
        "random_gauc_passed": random_passed,
        "hybrid_minimum_gauc_passed": minimum_passed,
        "gauc_domination_passed": gauc_gate.passed,
        "hr_domination_passed": hr_gate.passed,
        "ndcg_domination_passed": ndcg_gate.passed,
        "semantic_traps_passed": traps_passed,
        "cold_parity_passed": cold_passed,
        "all_passed": all_passed,
        "strongest_baselines": selection.model_dump(mode="json"),
        "gates": [gate.model_dump(mode="json") for gate in gates],
    }
    sha256 = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return VictoryMatrix(**document, sha256=sha256)


__all__ = [
    "SingleSeedGateInputs",
    "_select_strongest_competitor",
    "evaluate_single_seed",
]
