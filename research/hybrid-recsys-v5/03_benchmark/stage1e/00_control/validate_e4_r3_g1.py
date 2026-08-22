from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_t/E4_R3G1_bundle_selection"
VERDICT = "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT"
CANDIDATE_IDS = [
    "R3-BUNDLE-CORNAC-ML100K-001",
    "R3-BUNDLE-ELLIOT-ML1M-001",
    "R3-BUNDLE-DAISYREC-ML1M-001",
]
MODEL = {
    "display_name": "Sol Max Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "standard",
}
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
SEED_BINDING = {
    "path": "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery/candidate_bundle_seeds.json",
    "canonical_lf_bytes": 23034,
    "canonical_lf_sha256": "dce058850afb537f062531d1b128a1c36685bc878a3761e35a22db3d72db8781",
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


def is_https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    contract = load_json(CONTROL / "e4_r3_g1_output_contract.json")
    expected_files = set(contract["exact_files"])
    actual_files = {path.name for path in OUTPUT.iterdir() if path.is_file()} if OUTPUT.is_dir() else set()
    directories = [path.name for path in OUTPUT.iterdir() if path.is_dir()] if OUTPUT.is_dir() else []
    check(
        checks,
        failures,
        "exact_six_file_output_set",
        actual_files == expected_files and not directories,
    )

    documents: dict[str, dict[str, Any]] = {}
    strict_json = 0
    for name in expected_files:
        path = OUTPUT / name
        if not path.is_file():
            continue
        try:
            canonical_lf(path)
            if path.suffix.lower() == ".json":
                documents[name] = load_json(path)
                strict_json += 1
        except Exception as exc:
            failures.append(f"output_parse:{name}:{exc}")
    check(checks, failures, "strict_json_outputs_5_of_5", strict_json == 5)

    common_fields = set(contract["common_json_fields"])
    common_ok = True
    for name, data in documents.items():
        if not common_fields.issubset(data):
            failures.append(f"common_fields:{name}")
            common_ok = False
        if data.get("stage_id") != "R3-G1":
            failures.append(f"stage_id:{name}")
            common_ok = False
        if data.get("model_profile") != MODEL:
            failures.append(f"model:{name}")
            common_ok = False
        if data.get("seed_manifest_binding") != SEED_BINDING:
            failures.append(f"seed_binding:{name}")
            common_ok = False
        if data.get("candidate_ids") != CANDIDATE_IDS:
            failures.append(f"candidate_ids:{name}")
            common_ok = False
        if data.get("truth_state") != TRUTH:
            failures.append(f"truth:{name}")
            common_ok = False
    check(checks, failures, "common_json_contract", common_ok and len(documents) == 5)

    frozen_gate = load_json(
        CONTROL / "rebaseline_v2_e4_r3_g1_frozen_input_gate_receipt.json"
    )
    check(
        checks,
        failures,
        "frozen_input_gate_pass",
        frozen_gate.get("passed") is True
        and frozen_gate.get("verdict")
        == "PASS_R3_G1_FROZEN_20_OF_20_READY_FOR_CENTRAL_SYNTHESIS"
        and frozen_gate.get("frozen_inputs", {}).get("matched") == 20,
    )

    lane_statuses: dict[str, dict[str, str]] = {}
    source_urls: list[str] = []
    for lane_id, path in LANES.items():
        data = load_json(path)
        rows = data.get("rows", [])
        statuses: dict[str, str] = {}
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            candidate_id = str(row.get("candidate_id"))
            statuses[candidate_id] = str(row.get("status"))
            sources = row.get("decision_bearing_sources")
            if isinstance(sources, list):
                for source in sources:
                    if isinstance(source, dict) and is_https(source.get("url")):
                        source_urls.append(str(source["url"]))
        lane_statuses[lane_id] = statuses
    expected_statuses = {
        "R3-FD2": {candidate_id: "EVIDENCE_INCOMPLETE" for candidate_id in CANDIDATE_IDS},
        "R3-FD3": {candidate_id: "EVIDENCE_INCOMPLETE" for candidate_id in CANDIDATE_IDS},
        "R3-FD4": {candidate_id: "COMPATIBILITY_INCOMPLETE" for candidate_id in CANDIDATE_IDS},
    }
    check(checks, failures, "lane_statuses_exact", lane_statuses == expected_statuses)
    check(checks, failures, "source_mentions_77", len(source_urls) == 77)
    check(checks, failures, "unique_exact_urls_61", len(set(source_urls)) == 61)

    intersection = documents.get("bundle_evidence_intersection.json", {})
    rows = intersection.get("rows")
    check(checks, failures, "intersection_rows_is_list", isinstance(rows, list))
    if not isinstance(rows, list):
        rows = []
    check(
        checks,
        failures,
        "intersection_candidate_order",
        [row.get("candidate_id") for row in rows if isinstance(row, dict)]
        == CANDIDATE_IDS,
    )
    required_intersection = set(contract["intersection_row_fields"])
    intersection_ok = True
    for row in rows:
        if not isinstance(row, dict) or not required_intersection.issubset(row):
            intersection_ok = False
            continue
        candidate_id = str(row.get("candidate_id"))
        expected = {
            "fd1_status": "PLAUSIBLE_COMPLETE_SEED",
            "fd2_status": lane_statuses["R3-FD2"].get(candidate_id),
            "fd3_status": lane_statuses["R3-FD3"].get(candidate_id),
            "fd4_status": lane_statuses["R3-FD4"].get(candidate_id),
        }
        if any(row.get(key) != value for key, value in expected.items()):
            intersection_ok = False
        if row.get("central_replay_required") is not False:
            intersection_ok = False
        if row.get("central_replay_pass") is not False:
            intersection_ok = False
        if row.get("positive_gate_pass") is not False:
            intersection_ok = False
        if not isinstance(row.get("dispositive_mismatches"), list):
            intersection_ok = False
        if not isinstance(row.get("unresolved_fields"), list) or not row.get("unresolved_fields"):
            intersection_ok = False
    check(checks, failures, "intersection_row_contract", intersection_ok and len(rows) == 3)
    check(
        checks,
        failures,
        "intersection_dedup_counts",
        intersection.get("source_deduplication", {}).get("decision_bearing_source_mentions") == 77
        and intersection.get("source_deduplication", {}).get("unique_exact_urls") == 61
        and intersection.get("source_deduplication", {}).get("duplicate_mentions_removed_from_independence_count") == 16,
    )
    summary = intersection.get("intersection_summary", {})
    check(
        checks,
        failures,
        "intersection_zero_eligible_selected",
        summary.get("fully_sufficient_candidates") == 0
        and summary.get("central_replay_required_candidates") == 0
        and summary.get("selected_candidate_count") == 0
        and summary.get("selected_candidate_id") is None
        and intersection.get("verdict") == VERDICT,
    )

    replay = documents.get("central_locator_replay_log.json", {})
    entries = replay.get("entries")
    replay_summary = replay.get("summary", {})
    check(checks, failures, "replay_entries_empty", entries == [])
    check(
        checks,
        failures,
        "replay_zero_required_attempted",
        replay_summary.get("candidate_rows_could_otherwise_pass") == 0
        and replay_summary.get("decision_bearing_urls_required") == 0
        and replay_summary.get("attempted") == 0
        and replay_summary.get("passed") == 0
        and replay_summary.get("failed") == 0
        and replay_summary.get("unresolved") == 0
        and replay_summary.get("failed_replays_used_as_positive_evidence") == 0
        and replay_summary.get("positive_selection_supported") is False,
    )
    precheck = replay.get("candidate_precheck")
    check(
        checks,
        failures,
        "replay_precheck_all_ineligible",
        isinstance(precheck, list)
        and [row.get("candidate_id") for row in precheck if isinstance(row, dict)] == CANDIDATE_IDS
        and all(
            row.get("could_otherwise_pass") is False
            and row.get("replay_required") is False
            for row in precheck
            if isinstance(row, dict)
        ),
    )

    matrix = documents.get("bundle_decision_matrix.json", {})
    matrix_rows = matrix.get("rows")
    check(checks, failures, "matrix_rows_is_list", isinstance(matrix_rows, list))
    if not isinstance(matrix_rows, list):
        matrix_rows = []
    required_matrix = set(contract["decision_matrix_row_fields"])
    check(
        checks,
        failures,
        "matrix_row_contract",
        len(matrix_rows) == 3
        and [row.get("candidate_id") for row in matrix_rows if isinstance(row, dict)] == CANDIDATE_IDS
        and all(isinstance(row, dict) and required_matrix.issubset(row) for row in matrix_rows)
        and all(row.get("eligible_before_ranking") is False for row in matrix_rows)
        and all(row.get("rank_disposition") == "INELIGIBLE_NOT_RANKED" for row in matrix_rows),
    )
    check(
        checks,
        failures,
        "matrix_no_dedup_or_ranking",
        matrix.get("deduplication", {}).get("unique_identity_tuples") == 3
        and matrix.get("deduplication", {}).get("rows_collapsed") == 0
        and matrix.get("ranking_order") == contract.get("ranking_order")
        and matrix.get("ranking_applied") is False
        and matrix.get("eligible_candidate_ids") == []
        and matrix.get("selected_candidate_id") is None,
    )

    decision = documents.get("selection_decision.json", {})
    decision_body = decision.get("decision", {})
    check(
        checks,
        failures,
        "decision_no_selection",
        decision_body.get("verdict") == VERDICT
        and decision_body.get("selected_candidate_count") == 0
        and decision_body.get("selected_candidate_id") is None
        and decision_body.get("materialization_allowed") is False
        and decision_body.get("execution_allowed") is False,
    )
    check(
        checks,
        failures,
        "decision_no_fallback_downstream_blocked",
        decision.get("automatic_fallback_allowed") is False
        and decision.get("downstream", {}).get("R3-M0") == "NOT_OPENED_NO_SELECTION"
        and all(
            value == "BLOCKED"
            for key, value in decision.get("downstream", {}).items()
            if key != "R3-M0"
        ),
    )

    report_path = OUTPUT / "r3_g1_report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    report_markers = [
        VERDICT,
        "Sol Max Standard",
        "20/20",
        "14/14",
        "53/53",
        "Replay attempts are therefore `0`",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
        "INVALID_FOR_PAPER",
    ]
    check(
        checks,
        failures,
        "report_required_markers",
        all(marker in report for marker in report_markers),
    )

    handoff = documents.get("r3_g1_handoff.json", {})
    records = {
        row.get("path"): row
        for row in handoff.get("outputs", [])
        if isinstance(row, dict)
    }
    output_hashes_ok = True
    for name in expected_files - {"r3_g1_handoff.json"}:
        path = OUTPUT / name
        relative = path.relative_to(ROOT).as_posix()
        record = records.get(relative)
        if record is None:
            output_hashes_ok = False
            continue
        payload = canonical_lf(path)
        if (
            record.get("canonical_lf_bytes") != len(payload)
            or record.get("canonical_lf_sha256")
            != hashlib.sha256(payload).hexdigest()
        ):
            output_hashes_ok = False
    check(
        checks,
        failures,
        "handoff_five_output_hashes",
        output_hashes_ok and len(records) == 5,
    )
    forbidden = handoff.get("forbidden_operations")
    check(
        checks,
        failures,
        "handoff_forbidden_operations",
        isinstance(forbidden, dict)
        and bool(forbidden)
        and all(value is False for value in forbidden.values()),
    )
    check(
        checks,
        failures,
        "handoff_no_selection",
        handoff.get("verdict") == VERDICT
        and handoff.get("selection", {}).get("eligible_candidate_count") == 0
        and handoff.get("selection", {}).get("selected_candidate_count") == 0
        and handoff.get("selection", {}).get("selected_candidate_id") is None
        and handoff.get("selection", {}).get("selection_performed") is False,
    )
    check(
        checks,
        failures,
        "handoff_downstream_blocked",
        handoff.get("downstream", {}).get("R3-M0") == "NOT_OPENED_NO_SELECTION"
        and handoff.get("downstream", {}).get("materialization") == "BLOCKED"
        and handoff.get("downstream", {}).get("execution") == "BLOCKED",
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-g1-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R3_G1_NO_SELECTION_FAIL_CLOSED_R3_M0_NOT_OPENED"
            if passed
            else "FAIL_R3_G1_VALIDATION_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "selection": {
            "candidate_count": 3,
            "eligible": 0,
            "selected": 0,
            "verdict": VERDICT,
        },
        "source_deduplication": {
            "mentions": len(source_urls),
            "unique_exact_urls": len(set(source_urls)),
        },
        "central_replay": {"required": 0, "attempted": 0},
        "model_profile": MODEL,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
