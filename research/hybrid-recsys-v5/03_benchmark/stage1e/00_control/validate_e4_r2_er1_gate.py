from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r2_er1_frozen_input_manifest.json"
EXPECTED_ROW_ID = "E3-LIGHTGCN-GOWALLA-PYTORCH-001"
EXPECTED_MODEL = {
    "display_name": "Sol Max Fast",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "priority",
    "speed_label": "Fast",
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lowered: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in lowered and lowered[folded] != key:
            raise ContractError(f"case-colliding JSON keys: {lowered[folded]} / {key}")
        lowered[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:  # fail closed with a bounded diagnostic
        print(json.dumps({"passed": False, "failures": [f"manifest_parse:{exc}"]}, indent=2))
        return 1

    inputs = manifest.get("inputs")
    check(checks, failures, "manifest_inputs_is_list", isinstance(inputs, list))
    if not isinstance(inputs, list):
        inputs = []

    check(checks, failures, "manifest_input_count_31", manifest.get("input_count") == 31 == len(inputs))
    paths = [item.get("path") for item in inputs if isinstance(item, dict)]
    check(checks, failures, "manifest_rows_are_objects", len(paths) == len(inputs))
    check(checks, failures, "manifest_paths_unique", len(paths) == len(set(paths)))

    matched = 0
    json_inputs_verified = 0
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            failures.append(f"input_{index}_not_object")
            continue
        relative = item.get("path")
        if not isinstance(relative, str):
            failures.append(f"input_{index}_path_invalid")
            continue
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            payload = canonical_lf(path)
        except Exception as exc:
            failures.append(f"utf8_or_read_failure:{relative}:{exc}")
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != item.get("canonical_lf_bytes"):
            failures.append(f"byte_mismatch:{relative}")
            continue
        if digest != item.get("canonical_lf_sha256"):
            failures.append(f"hash_mismatch:{relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
                json_inputs_verified += 1
            except Exception as exc:
                failures.append(f"strict_json_failure:{relative}:{exc}")
                continue
        matched += 1

    check(checks, failures, "frozen_inputs_31_of_31", matched == 31)
    check(checks, failures, "strict_json_inputs_verified", json_inputs_verified == 24)

    required_paths = {
        "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r2_er1_change_control_contract.md",
        "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r2_er1_stage_map.json",
        "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r2_g1_validation_receipt.json",
        "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_h/E4_R2G1_candidate_selection/r2_g1_handoff.json",
    }
    check(checks, failures, "required_control_inputs_present", required_paths.issubset(set(paths)))

    check(checks, failures, "manifest_candidate_scope", manifest.get("candidate_scope") == {
        "row_id": EXPECTED_ROW_ID,
        "selection_cardinality_max": 1,
        "scope_expansion_allowed": False,
    })
    check(checks, failures, "manifest_model_policy_sol_max_fast", manifest.get("model_policy") == EXPECTED_MODEL)
    check(checks, failures, "manifest_truth_state_frozen", manifest.get("truth_state") == {
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "execution_authorized": False,
        "project_benchmark_numbers": "INVALID_FOR_PAPER",
    })

    stage_map = load_json(CONTROL / "e4_r2_er1_stage_map.json")
    check(checks, failures, "stage_map_user_checkpoint", stage_map.get("entry_checkpoint", {}).get("user_confirmed") is True)
    check(checks, failures, "stage_map_candidate_scope", stage_map.get("candidate_scope", {}).get("row_id") == EXPECTED_ROW_ID)
    check(checks, failures, "stage_map_model_policy", all(
        stage_map.get("model_policy", {}).get(key) == value for key, value in EXPECTED_MODEL.items()
    ))
    phases = stage_map.get("phases", [])
    substantive = [phase for phase in phases if isinstance(phase, dict) and phase.get("model") is not None]
    check(checks, failures, "all_six_substantive_stages_present", len(substantive) == 6)
    check(checks, failures, "all_stages_sol_max_fast", bool(substantive) and all(
        phase.get("model") == "gpt-5.6-sol"
        and phase.get("reasoning") == "max"
        and phase.get("service_tier") == "priority"
        for phase in substantive
    ))
    boundary = stage_map.get("execution_boundary", {})
    check(checks, failures, "execution_boundary_fail_closed", boundary.get("public_primary_source_web_replay") is True and all(
        value is False for key, value in boundary.items() if key != "public_primary_source_web_replay"
    ))

    contract = (CONTROL / "e4_r2_er1_change_control_contract.md").read_text(encoding="utf-8")
    contract_markers = [
        "display name: `Sol Max Fast`",
        "model ID: `gpt-5.6-sol`",
        "reasoning effort: `max`",
        "service tier: `priority` (`Fast`)",
        "Execution authority: `DENIED`",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
    ]
    check(checks, failures, "contract_runtime_and_truth_markers", all(marker in contract for marker in contract_markers))

    prior_receipt = load_json(CONTROL / "rebaseline_v2_e4_r2_g1_validation_receipt.json")
    check(checks, failures, "prior_g1_validation_pass", prior_receipt.get("passed") is True and prior_receipt.get("verdict") == "PASS_R2_G1_NO_SELECTION_FAIL_CLOSED_DOWNSTREAM_BLOCKED")
    check(checks, failures, "prior_g1_selected_zero", prior_receipt.get("selection", {}).get("selected") == 0)
    check(checks, failures, "prior_contract_findings_preserved", prior_receipt.get("contract_findings_preserved") == [
        "R2-CF-A1-001", "R2-CF-A2-001", "R2-CF-A3-001"
    ])

    g1_root = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_h/E4_R2G1_candidate_selection"
    handoff = load_json(g1_root / "r2_g1_handoff.json")
    check(checks, failures, "prior_handoff_no_selection", handoff.get("verdict") == "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT")
    check(checks, failures, "prior_handoff_truth_state", handoff.get("truth_state") == {
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "execution_authorized": False,
        "project_benchmark_numbers": "INVALID_FOR_PAPER",
    })
    intersection = load_json(g1_root / "central_evidence_intersection.json")
    rows = intersection.get("candidate_rows", [])
    lightgcn = [row for row in rows if isinstance(row, dict) and row.get("row_id") == EXPECTED_ROW_ID]
    check(checks, failures, "lightgcn_priority_row_unique", len(lightgcn) == 1)
    check(checks, failures, "lightgcn_prior_lanes_all_incomplete", len(lightgcn) == 1 and set(lightgcn[0].get("lane_statuses", {}).values()) == {"EVIDENCE_INCOMPLETE"})

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r2-er1-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R2_ER1_GATE_31_OF_31_READY_FOR_PARALLEL_DISPATCH" if passed else "FAIL_R2_ER1_GATE_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"expected": 31, "matched": matched, "strict_json_inputs_verified": json_inputs_verified},
        "model_policy": EXPECTED_MODEL,
        "candidate_row_id": EXPECTED_ROW_ID,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
