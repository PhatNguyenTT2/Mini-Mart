from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r3_g1_frozen_input_manifest.json"
CANDIDATE_IDS = [
    "R3-BUNDLE-CORNAC-ML100K-001",
    "R3-BUNDLE-ELLIOT-ML1M-001",
    "R3-BUNDLE-DAISYREC-ML1M-001",
]
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
WORKER_MODEL = {
    "display_name": "Sol XHigh Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "xhigh",
    "service_tier": "standard",
}
CENTRAL_MODEL = {
    "display_name": "Sol Max Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "standard",
}
LANES = {
    "R3-FD2": ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_q/E4_R3FD2_rights_lineage_verification/rights_lineage_verification.json",
    "R3-FD3": ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_r/E4_R3FD3_benchmark_evaluator_verification/benchmark_evaluator_verification.json",
    "R3-FD4": ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_s/E4_R3FD4_v5_compatibility_stress_test/v5_compatibility_assessment.json",
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded_seen: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in folded_seen and folded_seen[folded] != key:
            raise ContractError(
                f"case-colliding JSON keys: {folded_seen[folded]} / {key}"
            )
        folded_seen[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    value = json.loads(raw, object_pairs_hook=reject_duplicate_or_case_colliding_keys)
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(
    checks: dict[str, bool], failures: list[str], name: str, condition: bool
) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    manifest = load_json(MANIFEST)
    inputs = manifest.get("inputs")
    check(checks, failures, "inputs_is_list", isinstance(inputs, list))
    if not isinstance(inputs, list):
        inputs = []
    check(
        checks,
        failures,
        "input_count_20",
        manifest.get("input_count") == 20 and len(inputs) == 20,
    )
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(
        checks,
        failures,
        "input_paths_unique",
        len(paths) == len(set(paths)) == 20,
    )

    matched = 0
    strict_json = 0
    for row in inputs:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append("invalid_manifest_row")
            continue
        relative = row["path"]
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            payload = canonical_lf(path)
        except Exception as exc:
            failures.append(f"utf8:{relative}:{exc}")
            continue
        if len(payload) != row.get("canonical_lf_bytes"):
            failures.append(f"bytes:{relative}")
            continue
        if hashlib.sha256(payload).hexdigest() != row.get("canonical_lf_sha256"):
            failures.append(f"sha256:{relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
                strict_json += 1
            except Exception as exc:
                failures.append(f"strict_json:{relative}:{exc}")
                continue
        matched += 1
    check(checks, failures, "frozen_inputs_20_of_20", matched == 20)
    check(
        checks,
        failures,
        "strict_json_14_of_14",
        manifest.get("json_input_count") == 14 and strict_json == 14,
    )
    check(
        checks,
        failures,
        "candidate_ids_frozen",
        manifest.get("candidate_count") == 3
        and manifest.get("candidate_ids") == CANDIDATE_IDS,
    )
    check(
        checks,
        failures,
        "model_policy_frozen",
        manifest.get("model_policy", {}).get("workers") == WORKER_MODEL
        and manifest.get("model_policy", {}).get("central") == CENTRAL_MODEL,
    )
    check(checks, failures, "truth_state_frozen", manifest.get("truth_state") == TRUTH)
    check(
        checks,
        failures,
        "no_selection_in_manifest",
        manifest.get("selection_performed") is False,
    )

    receipt = load_json(
        CONTROL / "rebaseline_v2_e4_r3_verification_lanes_validation_receipt.json"
    )
    check(
        checks,
        failures,
        "lane_validation_receipt_pass",
        receipt.get("passed") is True
        and receipt.get("verdict")
        == "PASS_R3_FD2_FD4_READY_FOR_CENTRAL_G1_FREEZE"
        and receipt.get("failure_count") == 0,
    )
    check(
        checks,
        failures,
        "lane_validation_53_of_53",
        receipt.get("mechanical_checks") == {"passed": 53, "expected": 53},
    )

    observed: dict[str, dict[str, str]] = {}
    no_positive_lane_rows = True
    for lane_id, path in LANES.items():
        data = load_json(path)
        rows = data.get("rows")
        check(checks, failures, f"{lane_id}_rows_is_list", isinstance(rows, list))
        if not isinstance(rows, list):
            rows = []
        row_ids = [row.get("candidate_id") for row in rows if isinstance(row, dict)]
        check(
            checks,
            failures,
            f"{lane_id}_candidate_order",
            row_ids == CANDIDATE_IDS,
        )
        statuses = {
            str(row.get("candidate_id")): str(row.get("status"))
            for row in rows
            if isinstance(row, dict)
        }
        observed[lane_id] = statuses
        positive = (
            "COMPATIBLE_WITH_BOUNDED_ADAPTER"
            if lane_id == "R3-FD4"
            else "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW"
        )
        if any(status == positive for status in statuses.values()):
            no_positive_lane_rows = False
        check(checks, failures, f"{lane_id}_worker_model", data.get("model_profile") == WORKER_MODEL)
        check(checks, failures, f"{lane_id}_truth", data.get("truth_state") == TRUTH)
    check(
        checks,
        failures,
        "observed_statuses_match_manifest",
        observed == manifest.get("observed_lane_statuses"),
    )
    check(
        checks,
        failures,
        "no_positive_lane_rows",
        no_positive_lane_rows,
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-g1-frozen-input-gate-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R3_G1_FROZEN_20_OF_20_READY_FOR_CENTRAL_SYNTHESIS"
            if passed
            else "FAIL_R3_G1_FROZEN_INPUT_REPLAY_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 20,
            "matched": matched,
            "strict_json_verified": strict_json,
        },
        "candidate_ids": CANDIDATE_IDS,
        "lane_statuses": observed,
        "positive_lane_rows": 0 if no_positive_lane_rows else "ONE_OR_MORE",
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
