from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r5_g1_frozen_input_manifest.json"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
MODEL = {
    "display_name": "Sol Max Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "standard",
}


class ContractError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate key: {key}")
        casefolded = key.casefold()
        if casefolded in folded and folded[casefolded] != key:
            raise ContractError(f"case-colliding keys: {folded[casefolded]} / {key}")
        folded[casefolded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(checks: dict[str, bool], failures: list[str], name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"manifest:{exc}"]}, indent=2))
        return 1
    inputs = manifest.get("inputs", [])
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(checks, failures, "manifest_count_23", manifest.get("input_count") == 23 == len(inputs))
    check(checks, failures, "manifest_paths_unique", len(paths) == len(inputs) == len(set(paths)))
    matched = 0
    json_verified = 0
    for row in inputs:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append("invalid_manifest_row")
            continue
        path = ROOT / row["path"]
        if not path.is_file():
            failures.append(f"missing:{row['path']}")
            continue
        try:
            payload = canonical_lf(path)
            if (
                len(payload) != row.get("canonical_lf_bytes")
                or hashlib.sha256(payload).hexdigest() != row.get("canonical_lf_sha256")
            ):
                failures.append(f"hash:{row['path']}")
                continue
            if path.suffix.casefold() == ".json":
                load_json(path)
                json_verified += 1
            matched += 1
        except Exception as exc:
            failures.append(f"parse:{row['path']}:{exc}")
    check(checks, failures, "frozen_inputs_23_of_23", matched == 23)
    check(checks, failures, "strict_json_18_of_18", json_verified == 18)
    check(
        checks,
        failures,
        "manifest_entry_and_model",
        manifest.get("entry_gate")
        == "PASS_R5_M1_TWO_SOURCE_AUDITS_READY_FOR_CENTRAL_R5_G1_FREEZE"
        and manifest.get("candidate_count") == 2
        and manifest.get("selection_cardinality_max") == 1
        and manifest.get("selection_is_benchmark_admission") is False
        and manifest.get("model_policy") == MODEL,
    )
    boundary = manifest.get("scientific_boundary", {})
    check(
        checks,
        failures,
        "manifest_scientific_boundary",
        boundary.get("numeric_target_magnitude_used_for_selection") is False
        and boundary.get("cross_candidate_fact_borrowing") is False
        and boundary.get("source_audit_can_claim_verified_reproducibility") is False
        and boundary.get("dataset_environment_or_execution_authorized") is False
        and boundary.get("test_access_authorized") is False
        and boundary.get("next_positive_checkpoint") == "R5-M2"
        and manifest.get("truth_state") == TRUTH,
    )

    lane_receipt = load_json(CONTROL / "rebaseline_v2_e4_r5_m1_lanes_validation_receipt.json")
    check(
        checks,
        failures,
        "m1_lanes_centrally_validated",
        lane_receipt.get("passed") is True
        and lane_receipt.get("failure_count") == 0
        and lane_receipt.get("outputs", {}).get("files_present") == 10
        and lane_receipt.get("source_facts", {}).get("total") == 75
        and lane_receipt.get("source_facts", {}).get("positive_hash_bound") == 56,
    )
    check(checks, failures, "m1_lane_receipt_truth", lane_receipt.get("truth_state") == TRUTH)

    a_root = ROOT / (
        "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
        "wave_ad/E4_R5M1A_recbole_source_audit"
    )
    b_root = ROOT / (
        "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
        "wave_ae/E4_R5M1B_recbole_gnn_source_audit"
    )
    a_handoff = load_json(a_root / "audit_handoff.json")
    b_handoff = load_json(b_root / "audit_handoff.json")
    check(
        checks,
        failures,
        "candidate_handoffs_incomplete_not_run",
        all(
            handoff.get("candidate_status") == "SOURCE_INCOMPLETE_CANDIDATE_FOR_R5_G1"
            and handoff.get("reproducibility_status") == "SOURCE_INCOMPLETE_NOT_RUN"
            and handoff.get("dispositive_conflicts") == []
            and handoff.get("truth_state") == TRUTH
            for handoff in (a_handoff, b_handoff)
        ),
    )
    check(
        checks,
        failures,
        "a_bounded_comparison_only",
        a_handoff.get("adapter_status", {}).get("decision")
        == "CONDITIONALLY_BOUNDED_REPRESENTATION_ONLY_SCORE_ADAPTER_NOT_READY"
        and a_handoff.get("adapter_status", {}).get("bpr_objective_preserved") is True
        and "CENTRAL_COMPARISON_ONLY" in a_handoff.get("r5_g1_recommendation", ""),
    )
    b_recommendation = b_handoff.get("r5_g1_recommendation", {})
    check(
        checks,
        failures,
        "b_hold_not_ready",
        isinstance(b_recommendation, dict)
        and b_recommendation.get("recommendation") == "HOLD_NOT_READY_FOR_SELECTION_OR_EXECUTION"
        and b_recommendation.get("admit_candidate_now") is False
        and b_handoff.get("adapter_feasibility", {}).get("method_preserving_adapter_plausible") is True
        and b_handoff.get("adapter_feasibility", {}).get("evaluator_ready") is False,
    )

    contract = load_json(CONTROL / "e4_r5_g1_central_synthesis_contract.json")
    invariants = contract.get("selection_invariants", {})
    check(
        checks,
        failures,
        "g1_contract_zero_or_one_no_execution",
        contract.get("selection_cardinality_min") == 0
        and contract.get("selection_cardinality_max") == 1
        and contract.get("selection_is_benchmark_admission") is False
        and contract.get("selection_authorizes_dataset_environment_or_run") is False
        and invariants.get("numeric_target_magnitude_used_for_selection") is False
        and invariants.get("cross_candidate_fact_borrowing_allowed") is False
        and invariants.get("zero_selection_is_valid") is True
        and invariants.get("dataset_or_checkpoint_acquisition_allowed") is False
        and invariants.get("package_install_or_environment_creation_allowed") is False
        and invariants.get("preprocessing_training_evaluation_allowed") is False
        and invariants.get("project_v5_test_access_allowed") is False,
    )
    check(checks, failures, "g1_contract_truth", contract.get("truth_state") == TRUTH)

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-g1-frozen-input-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R5_G1_FROZEN_23_OF_23_READY_FOR_CENTRAL_SYNTHESIS" if passed else "FAIL_R5_G1_FROZEN_INPUT_GATE_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"matched": matched, "expected": 23, "strict_json": json_verified},
        "candidate_count": 2,
        "selection_cardinality_max": 1,
        "model_profile": MODEL,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
