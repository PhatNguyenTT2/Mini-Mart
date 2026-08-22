from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_o/E4_R2ER1G1_candidate_selection"
MANIFEST = CONTROL / "e4_r2_er1_g1_frozen_input_manifest.json"
ROW_ID = "E3-LIGHTGCN-GOWALLA-PYTORCH-001"
VERDICT = "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT"
EXPECTED_FILES = {
    "lightgcn_evidence_intersection.json",
    "locator_replay_log.json",
    "selection_decision.json",
    "er1_g1_report.md",
    "er1_g1_handoff.json",
}
EXPECTED_STATUSES = {
    "R2-ER1-A1": "EVIDENCE_INCOMPLETE",
    "R2-ER1-A2": "EVIDENCE_INCOMPLETE",
    "R2-ER1-A3": "EVIDENCE_INCOMPLETE",
}
MODEL = {
    "display_name": "Sol Max Fast",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "priority",
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate key: {key}")
        canonical = key.casefold()
        if canonical in folded and folded[canonical] != key:
            raise ContractError(f"case collision: {folded[canonical]} / {key}")
        folded[canonical] = key
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not object: {path}")
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

    manifest = load_json(MANIFEST)
    inputs = manifest.get("inputs")
    check(checks, failures, "manifest_30_inputs", isinstance(inputs, list) and manifest.get("input_count") == 30 and len(inputs) == 30)
    check(checks, failures, "manifest_23_json_inputs", manifest.get("json_input_count") == 23)
    if not isinstance(inputs, list):
        inputs = []
    paths = [entry.get("path") for entry in inputs if isinstance(entry, dict)]
    check(checks, failures, "manifest_paths_unique", len(paths) == len(set(paths)) == 30)

    matched = 0
    strict_json_inputs = 0
    for entry in inputs:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            failures.append("manifest_entry_invalid")
            continue
        relative = entry["path"]
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            payload = canonical_lf(path)
        except Exception as exc:
            failures.append(f"utf8_failure:{relative}:{exc}")
            continue
        if len(payload) != entry.get("canonical_lf_bytes"):
            failures.append(f"bytes:{relative}")
            continue
        if hashlib.sha256(payload).hexdigest() != entry.get("canonical_lf_sha256"):
            failures.append(f"sha256:{relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
                strict_json_inputs += 1
            except Exception as exc:
                failures.append(f"strict_json:{relative}:{exc}")
                continue
        matched += 1
    check(checks, failures, "frozen_inputs_30_of_30", matched == 30)
    check(checks, failures, "strict_json_inputs_23_of_23", strict_json_inputs == 23)
    check(checks, failures, "manifest_statuses_no_selection_only", manifest.get("candidate_scope", {}).get("observed_lane_statuses") == EXPECTED_STATUSES and manifest.get("candidate_scope", {}).get("allowed_decision") == VERDICT)
    check(checks, failures, "manifest_model_sol_max_fast", all(manifest.get("model_policy", {}).get(key) == value for key, value in MODEL.items()))

    lane_receipt = load_json(CONTROL / "rebaseline_v2_e4_r2_er1_lanes_validation_receipt.json")
    check(checks, failures, "lane_validation_pass", lane_receipt.get("passed") is True and lane_receipt.get("verdict") == "PASS_R2_ER1_PARALLEL_LANES_READY_FOR_FRESH_G1")
    check(checks, failures, "lane_statuses_all_incomplete", lane_receipt.get("lane_statuses") == EXPECTED_STATUSES)

    actual_files = {path.name for path in OUTPUT.iterdir() if path.is_file()} if OUTPUT.is_dir() else set()
    check(checks, failures, "exact_five_file_output_set", actual_files == EXPECTED_FILES)
    documents: dict[str, dict[str, Any]] = {}
    for name in EXPECTED_FILES:
        path = OUTPUT / name
        if not path.is_file():
            continue
        canonical_lf(path)
        if path.suffix == ".json":
            try:
                documents[name] = load_json(path)
            except Exception as exc:
                failures.append(f"output_strict_json:{name}:{exc}")
    check(checks, failures, "strict_json_outputs_4_of_4", len(documents) == 4)

    intersection = documents.get("lightgcn_evidence_intersection.json", {})
    candidate = intersection.get("candidate", {})
    check(checks, failures, "intersection_exact_candidate", candidate.get("row_id") == ROW_ID)
    check(checks, failures, "intersection_three_incomplete_lanes", candidate.get("lane_statuses") == EXPECTED_STATUSES and candidate.get("positive_lane_count") == 0)
    check(checks, failures, "intersection_zero_selection", intersection.get("intersection_summary", {}).get("selected_candidate_count") == 0 and candidate.get("positive_selection_eligible") is False)
    check(checks, failures, "intersection_deduplication", intersection.get("source_deduplication") == {
        "authoritative_source_mentions": 43,
        "unique_exact_urls": 36,
        "duplicate_mentions_removed_from_independence_count": 7,
        "dedup_key": "exact URL string",
        "repeated_url_is_independent_evidence": False,
    })
    check(checks, failures, "intersection_verdict", intersection.get("verdict") == VERDICT)

    replay = documents.get("locator_replay_log.json", {})
    entries = replay.get("entries", [])
    check(checks, failures, "locator_replay_10_entries", isinstance(entries, list) and len(entries) == 10)
    check(checks, failures, "locator_replay_summary_7_of_10", replay.get("summary") == {
        "attempted": 10,
        "successful": 7,
        "failed": 3,
        "failed_replays_used_as_positive_evidence": 0,
        "positive_selection_supported": False,
    })
    check(checks, failures, "locator_replay_no_failed_positive", all(
        not (entry.get("retrieval_status", "").startswith("FAILED") and entry.get("supports"))
        for entry in entries if isinstance(entry, dict)
    ))
    check(checks, failures, "locator_replay_verdict", replay.get("verdict") == "REPLAY_SUPPORTS_NO_SELECTION_ONLY")

    decision = documents.get("selection_decision.json", {})
    check(checks, failures, "decision_gate_0_of_3", decision.get("positive_gate", {}).get("observed_positive_lane_count") == 0 and decision.get("positive_gate", {}).get("observed_lane_statuses") == EXPECTED_STATUSES)
    check(checks, failures, "decision_zero_selected", decision.get("decision", {}).get("selected_candidate_count") == 0 and decision.get("decision", {}).get("selected_candidate_row_id") is None)
    check(checks, failures, "decision_verdict", decision.get("decision", {}).get("verdict") == VERDICT)
    downstream = decision.get("downstream", {})
    check(checks, failures, "all_downstream_blocked", bool(downstream) and all(str(value).startswith("BLOCKED") for value in downstream.values()))
    check(checks, failures, "no_automatic_fallback", decision.get("automatic_fallback_allowed") is False)

    report = (OUTPUT / "er1_g1_report.md").read_text(encoding="utf-8") if (OUTPUT / "er1_g1_report.md").is_file() else ""
    report_markers = [VERDICT, "Sol Max Fast", "gpt-5.6-sol", "reasoning `max`", "service tier `priority`", "RESULT_STATUS=NOT_RUN", "TEST_SET_OPENED=NO", "ACCEPTED_RESULT_ROWS=0", "INVALID_FOR_PAPER"]
    check(checks, failures, "report_required_markers", all(marker in report for marker in report_markers))

    handoff = documents.get("er1_g1_handoff.json", {})
    check(checks, failures, "handoff_passport_unverified", handoff.get("material_passport", {}).get("verification_status") == "UNVERIFIED")
    check(checks, failures, "handoff_no_experiment", handoff.get("material_passport", {}).get("experiment_intake_declaration", {}).get("status") == "no_experiments_declared")
    check(checks, failures, "handoff_sol_max_fast", handoff.get("actual_model") == "gpt-5.6-sol" and handoff.get("actual_reasoning") == "max" and handoff.get("actual_service_tier") == "priority" and handoff.get("actual_display") == "Sol Max Fast")
    check(checks, failures, "handoff_input_replay", handoff.get("frozen_manifest", {}).get("input_replay") == "PASS_30_OF_30" and handoff.get("frozen_manifest", {}).get("strict_json_replay") == "PASS_23_OF_23")

    output_records = handoff.get("outputs", [])
    records = {record.get("path"): record for record in output_records if isinstance(record, dict)}
    output_hashes_ok = True
    for name in EXPECTED_FILES - {"er1_g1_handoff.json"}:
        path = OUTPUT / name
        relative = path.relative_to(ROOT).as_posix()
        record = records.get(relative)
        if record is None:
            output_hashes_ok = False
            continue
        payload = canonical_lf(path)
        if record.get("canonical_lf_bytes") != len(payload) or record.get("canonical_lf_sha256") != hashlib.sha256(payload).hexdigest():
            output_hashes_ok = False
    check(checks, failures, "handoff_four_output_hashes", output_hashes_ok and len(records) == 4)
    check(checks, failures, "handoff_zero_selection", handoff.get("selection", {}).get("selected_candidate_count") == 0 and handoff.get("verdict") == VERDICT)
    truth = handoff.get("truth_state", {})
    check(checks, failures, "handoff_truth_state", truth == {
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "execution_authorized": False,
        "project_benchmark_numbers": "INVALID_FOR_PAPER",
    })
    forbidden = handoff.get("forbidden_operation_flags", {})
    check(checks, failures, "handoff_all_forbidden_false", bool(forbidden) and all(value is False for value in forbidden.values()))
    check(checks, failures, "handoff_downstream_blocked", handoff.get("downstream", {}).get("R2-M0") == "BLOCKED_NO_SELECTION" and handoff.get("downstream", {}).get("materialization") == "BLOCKED" and handoff.get("downstream", {}).get("execution") == "BLOCKED")

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r2-er1-g1-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R2_ER1_G1_NO_SELECTION_FAIL_CLOSED_DOWNSTREAM_BLOCKED" if passed else "FAIL_R2_ER1_G1_VALIDATION_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"expected": 30, "matched": matched, "strict_json_inputs": strict_json_inputs},
        "selection": {"candidate_count": 1, "fully_sufficient": 0, "selected": 0, "verdict": VERDICT},
        "model_policy": MODEL,
        "truth_state": truth,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
