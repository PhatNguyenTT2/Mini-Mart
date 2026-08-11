"""Single-seed victory gate verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import ColdParityReport, MetricGateResult, SplitName, VictoryMatrix
from ai_service.evaluation.baselines import BaselineComparisonReport, _mean_report
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


def evaluate_single_seed(
    inputs: SingleSeedGateInputs,
    settings: Settings | int | None = None,
    *,
    bootstrap_samples: int | None = None,
) -> VictoryMatrix:
    if isinstance(settings, int):
        bootstrap_samples = settings
        settings = None
    samples = bootstrap_samples or (settings.eval.bootstrap_samples if settings else 2000)
    random_tolerance = settings.eval.random_gauc_tolerance if settings else 0.02
    minimum_gauc = settings.eval.minimum_gauc if settings else 0.75
    wide_tolerance = settings.eval.wide_zero_atol if settings else 1e-7
    comp = inputs.comparison
    cold_parity = inputs.cold_parity
    semantic_traps = inputs.semantic_traps

    if len(comp.random_seed_results) != 10:
        raise ValueError("single-seed gates require exactly 10 random baseline seeds")
    if semantic_traps.total != 10 or semantic_traps.passed != 10:
        traps_passed = False
    else:
        traps_passed = bool(semantic_traps.all_passed)

    gates: list[MetricGateResult] = []

    # 1. Random GAUC Mean Gate
    random_mean_report = _mean_report([r.report for r in comp.random_seed_results])
    random_gauc = float(random_mean_report.gauc)
    random_per_user_gauc = np.mean([r.per_user_gauc for r in comp.random_seed_results], axis=0)
    random_ci = paired_bootstrap_delta(
        random_per_user_gauc,
        np.full_like(random_per_user_gauc, 0.5),
        samples=samples,
        seed=inputs.seed,
    )
    random_passed = (
        0.5 - random_tolerance <= random_gauc <= 0.5 + random_tolerance
        and random_ci.lower <= 0.0 <= random_ci.upper
    )
    gates.append(
        MetricGateResult(
            name="random_gauc",
            passed=random_passed,
            observed=random_gauc,
            target=0.50,
            description=(
                f"Random baseline GAUC mean must be in "
                f"[{0.5 - random_tolerance:.4f}, {0.5 + random_tolerance:.4f}]"
            ),
            candidate_name="random",
            baseline_name="sanity_check",
            candidate_mean=random_gauc,
            baseline_mean=0.50,
            delta_mean=float(random_ci.mean_delta),
            ci_lower=float(random_ci.lower),
            ci_upper=float(random_ci.upper),
            threshold=random_tolerance,
            failure_reason=None if random_passed else "random GAUC or CI guardrail failed",
        )
    )

    # 2. Hybrid GAUC Gate
    hybrid_gauc = float(comp.hybrid.report.gauc)
    hybrid_gauc_passed = hybrid_gauc >= minimum_gauc
    gates.append(
        MetricGateResult(
            name="hybrid_gauc",
            passed=hybrid_gauc_passed,
            observed=hybrid_gauc,
            target=minimum_gauc,
            description=f"Hybrid model GAUC must be >= {minimum_gauc:.4f}",
            candidate_name="hybrid",
            baseline_name="threshold",
            candidate_mean=hybrid_gauc,
            baseline_mean=minimum_gauc,
            delta_mean=hybrid_gauc - minimum_gauc,
            ci_lower=hybrid_gauc - minimum_gauc,
            ci_upper=hybrid_gauc - minimum_gauc,
            threshold=minimum_gauc,
            failure_reason=None if hybrid_gauc_passed else "Hybrid GAUC below minimum threshold",
        )
    )

    # 3. HR Domination Gate (vs strongest of 6 competitors)
    competitors = {
        "apriori_only": comp.apriori_only,
        "sbert_centroid": comp.sbert_centroid,
        "item_cf": comp.item_cf,
        "deep_only": comp.deep_only,
        "noisy_hybrid": comp.noisy_hybrid,
        "random": comp.random_seed_results[0].__class__(
            report=random_mean_report,
            user_ids=comp.random_seed_results[0].user_ids,
            per_user_hr=np.mean([r.per_user_hr for r in comp.random_seed_results], axis=0),
            per_user_ndcg=np.mean([r.per_user_ndcg for r in comp.random_seed_results], axis=0),
            per_user_gauc=random_per_user_gauc,
            top_k_by_user=comp.random_seed_results[0].top_k_by_user,
        ),
    }
    strongest_name = max(competitors, key=lambda k: float(competitors[k].report.hr_at_k))
    strongest_hr = float(competitors[strongest_name].report.hr_at_k)
    hybrid_hr = float(comp.hybrid.report.hr_at_k)

    # Compute paired bootstrap CI for HR
    hr_delta_ci = paired_bootstrap_delta(
        comp.hybrid.per_user_hr,
        competitors[strongest_name].per_user_hr,
        samples=samples,
        seed=inputs.seed,
    )
    hr_passed = hybrid_hr > strongest_hr and hr_delta_ci.lower > 0.0
    gates.append(
        MetricGateResult(
            name="hr_domination",
            passed=hr_passed,
            observed=hybrid_hr,
            target=strongest_hr,
            description=(
                f"Hybrid HR@10 ({hybrid_hr:.4f}) must exceed strongest baseline "
                f"{strongest_name} ({strongest_hr:.4f}) with positive CI"
            ),
            candidate_name="hybrid",
            baseline_name=strongest_name,
            candidate_mean=hybrid_hr,
            baseline_mean=strongest_hr,
            delta_mean=float(hr_delta_ci.mean_delta),
            ci_lower=float(hr_delta_ci.lower),
            ci_upper=float(hr_delta_ci.upper),
            threshold=0.0,
            failure_reason=None
            if hr_passed
            else "Hybrid HR paired CI does not beat strongest competitor",
        )
    )

    # 4. Relative NDCG Gate vs Apriori
    apriori_ndcg = float(comp.apriori_only.report.ndcg_at_k)
    hybrid_ndcg = float(comp.hybrid.report.ndcg_at_k)
    ndcg_delta_ci = paired_bootstrap_delta(
        comp.hybrid.per_user_ndcg,
        comp.apriori_only.per_user_ndcg,
        samples=samples,
        seed=inputs.seed,
    )
    ndcg_passed = hybrid_ndcg > apriori_ndcg and ndcg_delta_ci.lower > 0.0
    gates.append(
        MetricGateResult(
            name="relative_ndcg",
            passed=ndcg_passed,
            observed=hybrid_ndcg,
            target=apriori_ndcg,
            description=(
                f"Hybrid NDCG@10 ({hybrid_ndcg:.4f}) must exceed Apriori-only "
                f"({apriori_ndcg:.4f}) with positive CI"
            ),
            candidate_name="hybrid",
            baseline_name="apriori_only",
            candidate_mean=hybrid_ndcg,
            baseline_mean=apriori_ndcg,
            delta_mean=float(ndcg_delta_ci.mean_delta),
            ci_lower=float(ndcg_delta_ci.lower),
            ci_upper=float(ndcg_delta_ci.upper),
            threshold=0.0,
            failure_reason=None if ndcg_passed else "Hybrid NDCG paired CI does not beat Apriori",
        )
    )

    # 5. Semantic Traps Gate
    observed_traps = float(semantic_traps.passed)
    gates.append(
        MetricGateResult(
            name="semantic_traps",
            passed=traps_passed,
            observed=observed_traps,
            target=10.0,
            description="All 10 semantic traps must pass",
            candidate_name="hybrid",
            baseline_name="traps",
            candidate_mean=observed_traps,
            baseline_mean=10.0,
            delta_mean=observed_traps - 10.0,
            ci_lower=observed_traps - 10.0,
            ci_upper=observed_traps - 10.0,
            threshold=10.0,
            failure_reason=None if traps_passed else "one or more semantic traps failed",
        )
    )

    # 6. Cold Parity Gate
    cold_passed = bool(cold_parity.passed)
    gates.append(
        MetricGateResult(
            name="cold_parity",
            passed=cold_passed,
            observed=cold_parity.max_abs_wide_logit,
            target=wide_tolerance,
            description=(
                "Cold parity must have max Wide logit <= configured tolerance "
                "and zero-shot order equality"
            ),
            candidate_name="hybrid",
            baseline_name="deep_ablation",
            candidate_mean=cold_parity.max_abs_wide_logit,
            baseline_mean=0.0,
            delta_mean=cold_parity.max_abs_wide_logit,
            ci_lower=cold_parity.max_abs_wide_logit,
            ci_upper=cold_parity.max_abs_wide_logit,
            threshold=wide_tolerance,
            failure_reason=None if cold_passed else "cold-start Wide/Deep parity failed",
        )
    )

    all_passed = (
        random_passed
        and hybrid_gauc_passed
        and hr_passed
        and ndcg_passed
        and traps_passed
        and cold_passed
    )

    matrix_doc = {
        "seed": inputs.seed,
        "split": inputs.split.value,
        "comparison_signature": inputs.comparison_signature,
        "random_gauc_passed": random_passed,
        "hybrid_gauc_passed": hybrid_gauc_passed,
        "hr_domination_passed": hr_passed,
        "relative_ndcg_passed": ndcg_passed,
        "semantic_traps_passed": traps_passed,
        "cold_parity_passed": cold_passed,
        "all_passed": all_passed,
        "strongest_hr_baseline": strongest_name,
        "gates": [g.model_dump(mode="json") for g in gates],
    }
    payload = json.dumps(matrix_doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha256 = hashlib.sha256(payload).hexdigest()

    return VictoryMatrix(
        random_gauc_passed=random_passed,
        hybrid_gauc_passed=hybrid_gauc_passed,
        hr_domination_passed=hr_passed,
        relative_ndcg_passed=ndcg_passed,
        semantic_traps_passed=traps_passed,
        cold_parity_passed=cold_passed,
        all_passed=all_passed,
        gates=gates,
        seed=inputs.seed,
        split=inputs.split,
        comparison_signature=inputs.comparison_signature,
        strongest_hr_baseline=strongest_name,
        sha256=sha256,
    )
