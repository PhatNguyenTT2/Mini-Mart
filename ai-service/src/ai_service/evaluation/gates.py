"""Single-seed victory gate verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from ai_service.contracts import ColdParityReport, MetricGateResult, VictoryMatrix


@dataclass(frozen=True)
class SingleSeedGateInputs:
    comparison: Any  # BaselineComparisonReport
    cold_parity: ColdParityReport
    semantic_traps: Any  # SemanticTrapReport


def evaluate_single_seed(inputs: SingleSeedGateInputs) -> VictoryMatrix:
    comparison = inputs.comparison
    cold_parity = inputs.cold_parity
    semantic_traps = inputs.semantic_traps

    gates: list[MetricGateResult] = []

    # 1. Random GAUC Gate
    random_gauc = float(comparison.baselines["random"].gauc)
    random_passed = 0.48 <= random_gauc <= 0.52
    gates.append(
        MetricGateResult(
            name="random_gauc",
            passed=random_passed,
            observed=random_gauc,
            target=0.50,
            description="Random baseline GAUC must be in [0.48, 0.52]",
        )
    )

    # 2. Hybrid GAUC Gate
    hybrid_gauc = float(comparison.hybrid.gauc)
    hybrid_gauc_passed = hybrid_gauc >= 0.75
    gates.append(
        MetricGateResult(
            name="hybrid_gauc",
            passed=hybrid_gauc_passed,
            observed=hybrid_gauc,
            target=0.75,
            description="Hybrid model GAUC must be >= 0.75",
        )
    )

    # 3. HR Domination Gate
    other_baselines = {
        name: r.hr_at_k for name, r in comparison.baselines.items()
    }
    strongest_baseline_name = max(other_baselines, key=other_baselines.get)
    strongest_hr = float(other_baselines[strongest_baseline_name])
    hybrid_hr = float(comparison.hybrid.hr_at_k)
    hr_passed = hybrid_hr > strongest_hr
    gates.append(
        MetricGateResult(
            name="hr_domination",
            passed=hr_passed,
            observed=hybrid_hr,
            target=strongest_hr,
            description=f"Hybrid HR@10 ({hybrid_hr:.4f}) must exceed strongest baseline {strongest_baseline_name} ({strongest_hr:.4f})",
        )
    )

    # 4. Relative NDCG Gate
    apriori_ndcg = float(comparison.baselines["apriori_only"].ndcg_at_k) if "apriori_only" in comparison.baselines else 0.0
    hybrid_ndcg = float(comparison.hybrid.ndcg_at_k)
    ndcg_passed = hybrid_ndcg > apriori_ndcg
    gates.append(
        MetricGateResult(
            name="relative_ndcg",
            passed=ndcg_passed,
            observed=hybrid_ndcg,
            target=apriori_ndcg,
            description=f"Hybrid NDCG@10 ({hybrid_ndcg:.4f}) must exceed Apriori-only ({apriori_ndcg:.4f})",
        )
    )

    # 5. Semantic Traps Gate
    traps_passed = bool(getattr(semantic_traps, "all_passed", False))
    observed_traps = float(getattr(semantic_traps, "passed_count", 0))
    gates.append(
        MetricGateResult(
            name="semantic_traps",
            passed=traps_passed,
            observed=observed_traps,
            target=10.0,
            description="All 10 semantic traps must pass",
        )
    )

    # 6. Cold Parity Gate
    cold_passed = bool(cold_parity.passed)
    gates.append(
        MetricGateResult(
            name="cold_parity",
            passed=cold_passed,
            observed=cold_parity.max_abs_wide_logit,
            target=1e-7,
            description="Cold parity must have max Wide logit <= 1e-7 and zero-shot order equality",
        )
    )

    all_passed = random_passed and hybrid_gauc_passed and hr_passed and ndcg_passed and traps_passed and cold_passed

    payload = json.dumps(
        {
            "random_gauc": random_gauc,
            "hybrid_gauc": hybrid_gauc,
            "hybrid_hr": hybrid_hr,
            "hybrid_ndcg": hybrid_ndcg,
            "all_passed": all_passed,
        },
        sort_keys=True,
    ).encode("utf-8")
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
        sha256=sha256,
    )
