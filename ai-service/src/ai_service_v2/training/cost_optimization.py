"""Non-authorizing experiment registry for the separately approved cost route.

Historical registry and selection authority are inputs, never execution permission.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, loads_strict_json
from ai_service_v2.training.selection import (
    ConfigurationQualification,
    ConfigurationSelection,
    SeedValidationOutcome,
    StrongestBaselineSelection,
    qualify_configuration,
)

ROUTE_ID = "MP2-LOCAL-V5-COST-OPT-01"
DATASET_ID = "V5_INTERNAL_CURRENT"
BASE_SEEDS = (42, 2027, 31415)
EXTENDED_SEEDS = (2718, 1618)
METHODS = ("MostPop", "ItemKNN", "BPR-MF", "LightGCN", "Deep-only", "Rule-only", "Hybrid")
BASELINES = ("MostPop", "ItemKNN", "BPR-MF", "LightGCN")
SOURCE_REGISTRY_SHA256 = "6055ca870b3e7feed69a816f374c22b35622a6e154cd885af748ff5efb50250c"
REGISTRY_SCHEMA = "mp2-cost-optimized-compute-registry/1.0"
TEST_LOCKED = "LOCKED_NOT_ACCESSED"


def require_integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise IntegrityError(f"{field} must be a JSON integer >= {minimum}")
    return value


def preparation_state() -> dict[str, Any]:
    return {
        "authorization_state": "NON_AUTHORIZING",
        "c4_state": "BLOCKED",
        "validation_started": False,
        "validation_execution_authorized": False,
        "test_release_authorized": False,
        "test_access_state": TEST_LOCKED,
        "accepted_result_rows": 0,
        "scientific_evidence_created": False,
        "automatic_retry": False,
    }


def build_registry(source: dict[str, Any], *, source_sha256: str) -> dict[str, Any]:
    """Project the seven retained conditions without changing any source document."""
    from ai_service_v2.hashing import sha256_bytes

    if (
        source_sha256 != SOURCE_REGISTRY_SHA256
        or sha256_bytes(canonical_json_bytes(source) + b"\n") != SOURCE_REGISTRY_SHA256
        or source.get("fixed_logical_result_unit_count") != 140
        or source.get("fixed_execution_packet_count") != 142
    ):
        raise IntegrityError("historical registry binding mismatch")
    original_rows = source.get("units")
    if not isinstance(original_rows, list):
        raise IntegrityError("historical registry units missing")

    def configuration(method: str, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
        matches = [
            row
            for row in original_rows
            if row["method_id"] == method
            and row["configuration_index"] == index
            and row["seed"] == 42
        ]
        if len(matches) != 1:
            raise IntegrityError(f"source configuration is ambiguous: {method}/{index}")
        payload = loads_strict_json(matches[0]["configuration"].encode("utf-8"))
        config = copy.deepcopy(payload["configuration"])
        overrides: dict[str, Any] = {}
        if method in {"BPR-MF", "LightGCN"}:
            if type(config.get("max_epochs")) is not int or config["max_epochs"] != 300:
                raise IntegrityError("source epoch ceiling mismatch")
            config["max_epochs"] = 100
            overrides["max_epochs"] = {"original": 300, "resolved": 100}
        return config, overrides

    packets: list[dict[str, Any]] = []

    def add(
        method: str,
        index: int | None,
        seed: int,
        stage: str,
        *,
        dependencies: tuple[str, ...] = (),
        selection: str | None = None,
        logical: bool = True,
    ) -> None:
        config, overrides = configuration(method, index) if index is not None else (None, {})
        packet_id = f"cost-opt-{method.lower()}-c{index or 'selected'}-s{seed}"
        packets.append(
            {
                "packet_id": packet_id,
                "method_id": method,
                "configuration_index": index,
                "configuration": config,
                "configuration_sha256": canonical_json_sha256(config)
                if config is not None
                else None,
                "overrides": overrides,
                "seed": seed,
                "stage": stage,
                "dependencies": list(dependencies),
                "selection_lock": selection,
                "logical_result_unit": logical,
                "training_required": method in {"BPR-MF", "LightGCN", "Deep-only"},
                "input_roles": ["TRAIN_DATA", "VALIDATION_PROTOCOL", "FROZEN_CANDIDATE_CATALOG"],
                "automatic_retry": False,
            }
        )

    add("MostPop", 1, 42, "DETERMINISTIC")
    for index in (1, 3, 5):
        add("ItemKNN", index, 42, "DETERMINISTIC")
    for method in ("BPR-MF", "LightGCN"):
        for index in (1, 3, 5):
            add(method, index, 42, "SCREENING")
        for seed in BASE_SEEDS[1:]:
            add(
                method,
                None,
                seed,
                "CONFIRMATION",
                selection=f"{method}:SCREENING_WINNER",
                dependencies=tuple(f"cost-opt-{method.lower()}-c{i}-s42" for i in (1, 3, 5)),
            )
    for seed in BASE_SEEDS:
        add("Deep-only", 8, seed, "COMPONENT")
    for index in (1, 2, 3):
        add("Rule-only", index, 42, "COMPONENT")
    for index in (1, 2, 3, 4):
        for seed in BASE_SEEDS:
            add(
                "Hybrid",
                index,
                seed,
                "HYBRID",
                selection="RULE_WINNER",
                dependencies=(f"cost-opt-deep-only-c8-s{seed}", "RULE_SELECTION"),
            )
    for seed in EXTENDED_SEEDS:
        add("Deep-only", 8, seed, "DEPENDENCY", logical=False, dependencies=("HYBRID_SELECTION",))
        add(
            "Hybrid",
            None,
            seed,
            "EXTENSION",
            selection="HYBRID_WINNER",
            dependencies=(f"cost-opt-deep-only-c8-s{seed}", "HYBRID_SELECTION"),
        )

    result = {
        "schema_version": REGISTRY_SCHEMA,
        "route_id": ROUTE_ID,
        "dataset_id": DATASET_ID,
        "predecessor_registry_sha256": source_sha256,
        "predecessor_disposition": "IMMUTABLE_NOT_EXECUTION_AUTHORITY_FOR_THIS_ROUTE",
        "base_seeds": list(BASE_SEEDS),
        "primary_seeds": list(BASE_SEEDS + EXTENDED_SEEDS),
        "method_counts": {
            method: sum(p["method_id"] == method and p["logical_result_unit"] for p in packets)
            for method in METHODS
        },
        "fixed_logical_result_unit_count": 34,
        "fixed_execution_packet_count": 36,
        "extended_deep_dependency_packet_count": 2,
        "conditional_strongest_baseline_extension_range": [0, 2],
        "maximum_logical_result_unit_count": 36,
        "maximum_execution_packet_count": 38,
        "stochastic_training_run_range": [15, 17],
        "strongest_baseline_candidates": list(BASELINES),
        "deterministic_reuse": "BYTE_IDENTICAL_SURFACES_UNDER_DISCLOSED_SEED_LABELS",
        "screening_reuse": "WINNING_SEED_42_SCREEN_IS_BASE_CONFIRMATION_NO_RETRAIN",
        "external_slots": "NOT_TESTED",
        "movielens_evidence_scope": "PUBLIC_PROTOCOL_EVIDENCE_NOT_HYBRID_VALIDATION",
        "packets": packets,
        **preparation_state(),
    }
    return result


def validate_registry(registry: dict[str, Any], source: dict[str, Any]) -> None:
    """Check counts and exact projected parameters, not just declared totals."""
    expected = build_registry(source, source_sha256=SOURCE_REGISTRY_SHA256)
    if canonical_json_bytes(registry) != canonical_json_bytes(expected):
        raise IntegrityError("registry is not the exact approved projection")


def _sha256(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise IntegrityError("invalid SHA-256")
    return value


def _metric(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise IntegrityError("validation NDCG must be finite within [0,1]")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise IntegrityError("validation NDCG must be finite within [0,1]")
    return float(value)


@dataclass(frozen=True)
class ScreeningObservation:
    method_id: str
    configuration_index: int
    seed: int
    validation_ndcg_at_10: float
    configuration_sha256: str
    score_artifact_sha256: str

    def __post_init__(self) -> None:
        require_integer(self.configuration_index, "configuration_index", minimum=1)
        require_integer(self.seed, "seed")
        _metric(self.validation_ndcg_at_10)
        _sha256(self.configuration_sha256)
        _sha256(self.score_artifact_sha256)


def lock_screening_winner(rows: Sequence[ScreeningObservation]) -> dict[str, Any]:
    """Lock one seed-42 winner before any confirmation seed is observed."""
    if len(rows) != 3 or {row.configuration_index for row in rows} != {1, 3, 5}:
        raise IntegrityError("screening requires configurations 1/3/5 exactly once")
    if any(row.seed != 42 for row in rows):
        raise IntegrityError("screening accepts seed 42 only")
    methods = {row.method_id for row in rows}
    if len(methods) != 1 or not methods <= {"BPR-MF", "LightGCN"}:
        raise IntegrityError("screening must contain one retained stochastic baseline")
    if len({row.configuration_sha256 for row in rows}) != 3:
        raise IntegrityError("screening configurations require distinct hashes")
    winner = min(rows, key=lambda row: (-row.validation_ndcg_at_10, row.configuration_sha256))
    return {
        "schema_version": "mp2-cost-optimized-screening-selection/1.0",
        "route_id": ROUTE_ID,
        "method_id": winner.method_id,
        "phase": "SCREENING_ONLY_NOT_CONFIRMATION",
        "seed": 42,
        "configuration_index": winner.configuration_index,
        "configuration_sha256": winner.configuration_sha256,
        "score_artifact_sha256": winner.score_artifact_sha256,
        "validation_ndcg_at_10": winner.validation_ndcg_at_10,
        "tie_break": "CONFIGURATION_SHA256_ASCENDING",
        "selection_reopened": False,
    }


def qualify_locked_baseline(
    lock: dict[str, Any],
    outcomes: Sequence[SeedValidationOutcome],
    *,
    configuration_sha256: str,
) -> ConfigurationQualification:
    if set(lock) != {
        "schema_version",
        "route_id",
        "method_id",
        "phase",
        "seed",
        "configuration_index",
        "configuration_sha256",
        "score_artifact_sha256",
        "validation_ndcg_at_10",
        "tie_break",
        "selection_reopened",
    }:
        raise IntegrityError("screening winner lock schema mismatch")
    if (
        require_integer(lock["seed"], "seed") != 42
        or require_integer(lock["configuration_index"], "configuration_index") not in {1, 3, 5}
        or lock["selection_reopened"] is not False
    ):
        raise IntegrityError("screening winner identity mismatch")
    if (
        lock.get("schema_version") != "mp2-cost-optimized-screening-selection/1.0"
        or lock.get("route_id") != ROUTE_ID
        or lock.get("phase") != "SCREENING_ONLY_NOT_CONFIRMATION"
        or lock.get("method_id") not in {"BPR-MF", "LightGCN"}
        or lock.get("configuration_sha256") != configuration_sha256
    ):
        raise IntegrityError("confirmation must retain the locked screening winner")
    if len(outcomes) != 3 or {row.seed for row in outcomes} != set(BASE_SEEDS):
        raise IntegrityError("confirmation requires all three base seeds, no extended seeds")
    initial = next(row for row in outcomes if row.seed == 42)
    if initial.validation_ndcg_at_10 != lock.get(
        "validation_ndcg_at_10"
    ) or initial.validation_score_artifact_sha256 != lock.get("score_artifact_sha256"):
        raise IntegrityError("confirmation must reuse the byte-bound seed-42 screening result")
    return qualify_configuration(
        dataset_id=DATASET_ID,
        method_id=lock["method_id"],
        canonical_config_sha256=configuration_sha256,
        outcomes=outcomes,
    )


def select_cost_strongest_baseline(
    selections: Sequence[ConfigurationSelection],
) -> StrongestBaselineSelection:
    if len(selections) != 4 or {row.method_id for row in selections} != set(BASELINES):
        raise IntegrityError("strongest comparator requires all four retained baselines")
    if any(row.dataset_id != DATASET_ID or row.status != "SELECTED" for row in selections):
        raise IntegrityError("strongest comparator has an incomplete method selection")
    for row in selections:
        _metric(row.validation_statistic)
        _sha256(row.selected_config_sha256)
    winner = min(selections, key=lambda row: (-_metric(row.validation_statistic), row.method_id))
    return StrongestBaselineSelection(
        dataset_id=DATASET_ID,
        status="SELECTED",
        method_id=winner.method_id,
        canonical_config_sha256=winner.selected_config_sha256,
        validation_statistic=winner.validation_statistic,
    )


def budget_contract() -> dict[str, Any]:
    return {
        "schema_version": "mp2-cost-optimized-budget/1.0",
        "route_id": ROUTE_ID,
        "profile_cumulative_cap_ns": 7_200_000_000_000,
        "test_analysis_reserve_ns": 10_800_000_000_000,
        "validation_target_ns": 54_000_000_000_000,
        "validation_ceiling_ns": 72_000_000_000_000,
        "envelope_target_ns": 86_400_000_000_000,
        "envelope_ceiling_ns": 108_000_000_000_000,
        "contingency_numerator": 1,
        "contingency_denominator": 5,
        "early_stopping_credit_ns": 0,
        "parallelism_credit_ns": 0,
        "forecast_status": "UNMEASURED_NOT_EXECUTION_AUTHORITY",
        **preparation_state(),
    }


def budget_envelope(*, validation_upper_bound_ns: object) -> dict[str, Any]:
    """Integer-only arithmetic; ceil the 20% reserve rather than round down."""
    validation = require_integer(validation_upper_bound_ns, "validation_upper_bound_ns")
    budget = budget_contract()
    base = validation + budget["profile_cumulative_cap_ns"] + budget["test_analysis_reserve_ns"]
    envelope = base + (base + 4) // 5
    status = "TARGET_WITHIN_24H"
    if envelope > budget["envelope_target_ns"]:
        status = "ALLOWED_EXCEPTION_24_TO_30H"
    if envelope > budget["envelope_ceiling_ns"] or validation > budget["validation_ceiling_ns"]:
        status = "BUDGET_INFEASIBLE"
    return {
        "route_id": ROUTE_ID,
        "validation_upper_bound_ns": validation,
        "envelope_ns": envelope,
        "status": status,
        "early_stopping_credit_ns": 0,
        "parallelism_credit_ns": 0,
        "authorization_state": "NON_AUTHORIZING",
    }


def empirical_stability(
    mean_epoch_losses: Sequence[float],
    *,
    patience_count: object,
    epoch_cap: object,
) -> str:
    """Describe per-seed empirical stability, never optimizer/global convergence."""
    patience = require_integer(patience_count, "patience_count")
    cap = require_integer(epoch_cap, "epoch_cap", minimum=1)
    if len(mean_epoch_losses) > cap or not mean_epoch_losses:
        raise IntegrityError("loss history exceeds or omits the authorized epochs")
    if patience >= len(mean_epoch_losses):
        raise IntegrityError("patience cannot exceed epochs since the first checkpoint")
    for loss in mean_epoch_losses:
        if (
            isinstance(loss, bool)
            or not isinstance(loss, (float, int))
            or not math.isfinite(loss)
            or loss < 0
        ):
            raise IntegrityError("loss history must be finite and non-negative")
    if patience >= 20 and len(mean_epoch_losses) >= 10:
        earlier = math.fsum(mean_epoch_losses[-10:-5]) / 5
        later = math.fsum(mean_epoch_losses[-5:]) / 5
        relative_change = (
            abs(later - earlier) / abs(earlier)
            if earlier != 0
            else (0.0 if later == 0 else math.inf)
        )
        if relative_change <= 0.01:
            return "PER_SEED_EMPIRICAL_STABILITY_NOT_OPTIMALITY"
    return "BUDGET_LIMITED" if len(mean_epoch_losses) == cap else "STABILITY_NOT_ESTABLISHED"
