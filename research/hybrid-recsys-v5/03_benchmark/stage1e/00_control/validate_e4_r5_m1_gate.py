from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r5_m1_frozen_input_manifest.json"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
DIMENSIONS = {f"S{index:02d}" for index in range(1, 10)}


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
    check(checks, failures, "manifest_count_15", manifest.get("input_count") == 15 == len(inputs))
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
            digest = hashlib.sha256(payload).hexdigest()
            if len(payload) != row.get("canonical_lf_bytes") or digest != row.get("canonical_lf_sha256"):
                failures.append(f"hash:{row['path']}")
                continue
            if path.suffix.casefold() == ".json":
                load_json(path)
                json_verified += 1
            matched += 1
        except Exception as exc:
            failures.append(f"parse:{row['path']}:{exc}")
    check(checks, failures, "frozen_inputs_15_of_15", matched == 15)
    check(checks, failures, "strict_json_11_of_11", json_verified == 11)
    check(
        checks,
        failures,
        "manifest_entry_gate",
        manifest.get("entry_gate") == "PASS_R5_M0_TWO_HASH_LOCKED_SOURCE_TREES_READY_FOR_R5_M1"
        and manifest.get("candidate_count") == 2
        and manifest.get("parallel_stage_count") == 2,
    )
    model = manifest.get("model_policy", {})
    check(
        checks,
        failures,
        "sol_xhigh_standard",
        model
        == {
            "display_name": "Sol XHigh Standard",
            "runtime_model_id": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "service_tier": "standard",
        },
    )
    check(checks, failures, "manifest_truth", manifest.get("truth_state") == TRUTH)

    contract = load_json(CONTROL / "e4_r5_m1_source_audit_contract.json")
    dimensions = contract.get("mandatory_audit_dimensions", [])
    ids = {str(row.get("id", ""))[:3] for row in dimensions if isinstance(row, dict)}
    lanes = {row.get("stage_id"): row for row in contract.get("lanes", []) if isinstance(row, dict)}
    check(checks, failures, "exact_nine_dimensions", len(dimensions) == 9 and ids == DIMENSIONS)
    check(
        checks,
        failures,
        "exact_two_disjoint_lanes",
        set(lanes) == {"R5-M1A", "R5-M1B"}
        and lanes["R5-M1A"].get("candidate_id") != lanes["R5-M1B"].get("candidate_id")
        and lanes["R5-M1A"].get("write_root") != lanes["R5-M1B"].get("write_root"),
    )
    expected_outputs = [
        "source_fact_matrix.json",
        "gap_closure_assessment.json",
        "v5_adapter_feasibility.json",
        "audit_report.md",
        "audit_handoff.json",
    ]
    check(
        checks,
        failures,
        "exact_output_contract",
        contract.get("output_contract", {}).get("exact_filenames") == expected_outputs
        and contract.get("output_contract", {}).get("extra_files_allowed") is False,
    )
    invariants = contract.get("audit_invariants", {})
    check(
        checks,
        failures,
        "audit_is_read_only_no_execution",
        invariants.get("source_files_are_read_only") is True
        and invariants.get("network_access_allowed") is False
        and invariants.get("cross_candidate_evidence_join_allowed") is False
        and invariants.get("dataset_or_checkpoint_acquisition_allowed") is False
        and invariants.get("package_install_or_environment_creation_allowed") is False
        and invariants.get("vendor_source_execution_allowed") is False
        and invariants.get("preprocessing_training_evaluation_allowed") is False
        and invariants.get("project_v5_test_access_allowed") is False
        and invariants.get("verified_reproducibility_claim_allowed_without_rerun") is False
        and invariants.get("numeric_target_valid_for_paper") is False,
    )
    check(checks, failures, "contract_truth", contract.get("truth_state") == TRUTH)
    m0 = load_json(CONTROL / "rebaseline_v2_e4_r5_m0_validation_receipt.json")
    check(
        checks,
        failures,
        "m0_central_validation_passed",
        m0.get("passed") is True
        and m0.get("failure_count") == 0
        and m0.get("materialization", {}).get("materialized_files_hash_verified") == 330
        and m0.get("execution_boundary", {}).get("benchmark_admission") == "NONE",
    )
    check(checks, failures, "m0_truth", m0.get("truth_state") == TRUTH)

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m1-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R5_M1_FROZEN_15_OF_15_READY_FOR_PARALLEL_AUDITS" if passed else "FAIL_R5_M1_GATE_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"matched": matched, "expected": 15, "strict_json": json_verified},
        "parallel_stages": ["R5-M1A", "R5-M1B"],
        "model_profile": contract.get("model_profile"),
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
