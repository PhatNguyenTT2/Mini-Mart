from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_x/E4_R4G0_strict_admission_freeze"
)
EXPECTED_FILES = {
    "r4_g0_admission_decision.json",
    "frozen_complete_bundles.json",
    "central_source_replay_log.json",
    "deduplication_log.json",
    "r4_g0_report.md",
    "r4_g0_handoff.json",
}
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
VERDICT = "NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED"


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lowered: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in lowered and lowered[folded] != key:
            raise ContractError(
                f"case-colliding JSON keys: {lowered[folded]} / {key}"
            )
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


def check(
    checks: dict[str, bool],
    failures: list[str],
    name: str,
    condition: bool,
) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    actual_files = {
        path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()
    } if OUTPUT_ROOT.is_dir() else set()
    actual_dirs = [
        path.name for path in OUTPUT_ROOT.iterdir() if path.is_dir()
    ] if OUTPUT_ROOT.is_dir() else []
    check(checks, failures, "output_root_exists", OUTPUT_ROOT.is_dir())
    check(
        checks,
        failures,
        "exact_six_output_files",
        actual_files == EXPECTED_FILES and not actual_dirs,
    )
    if actual_files != EXPECTED_FILES:
        print(
            json.dumps(
                {
                    "passed": False,
                    "failures": failures,
                    "actual_files": sorted(actual_files),
                },
                indent=2,
            )
        )
        return 1

    try:
        decision = load_json(OUTPUT_ROOT / "r4_g0_admission_decision.json")
        frozen = load_json(OUTPUT_ROOT / "frozen_complete_bundles.json")
        replay = load_json(OUTPUT_ROOT / "central_source_replay_log.json")
        dedup = load_json(OUTPUT_ROOT / "deduplication_log.json")
        handoff = load_json(OUTPUT_ROOT / "r4_g0_handoff.json")
        report = (OUTPUT_ROOT / "r4_g0_report.md").read_text(
            encoding="utf-8"
        )
    except Exception as exc:
        failures.append(f"parse:{exc}")
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        return 1

    payloads = [decision, frozen, replay, dedup, handoff]
    check(
        checks,
        failures,
        "all_stage_ids_r4_g0",
        all(payload.get("stage_id") == "R4-G0" for payload in payloads),
    )
    check(
        checks,
        failures,
        "truth_state_5_of_5",
        all(payload.get("truth_state") == TRUTH for payload in payloads),
    )
    check(
        checks,
        failures,
        "central_model_profile",
        decision.get("model_profile") == MODEL
        and handoff.get("model_profile") == MODEL,
    )

    aggregate = decision.get("aggregate", {})
    gate = decision.get("central_admission_gate", {})
    decision_row = decision.get("decision", {})
    check(
        checks,
        failures,
        "decision_worker_counts",
        aggregate.get("proposals_examined") == 18
        and aggregate.get("worker_admitted") == 0
        and aggregate.get("worker_excluded") == 18
        and aggregate.get("excluded_incomplete_bundle") == 12
        and aggregate.get("dispositive_reject") == 6
        and aggregate.get("source_record_mentions") == 90
        and aggregate.get("unique_exact_source_urls") == 88,
    )
    check(
        checks,
        failures,
        "decision_zero_replay_zero_freeze",
        gate.get("worker_admitted_proposals_received") == 0
        and gate.get("central_replay_required_proposals") == 0
        and gate.get("central_replay_required_urls") == 0
        and gate.get("central_replays_attempted") == 0
        and gate.get("centrally_admissible_bundle_count") == 0
        and gate.get("frozen_complete_bundle_count") == 0,
    )
    check(
        checks,
        failures,
        "decision_fail_closed",
        decision_row.get("verdict") == VERDICT
        and decision_row.get("frozen_bundle_count") == 0
        and decision_row.get("audit_lanes_authorized") is False
        and decision_row.get("materialization_allowed") is False
        and decision_row.get("execution_allowed") is False
        and decision_row.get("automatic_new_wave_allowed") is False,
    )
    downstream = decision.get("downstream", {})
    check(
        checks,
        failures,
        "downstream_not_opened",
        downstream.get("R4-A1") == "NOT_LAUNCHED_ZERO_FROZEN_BUNDLES"
        and downstream.get("R4-A2")
        == "NOT_LAUNCHED_ZERO_FROZEN_BUNDLES"
        and downstream.get("R4-A3")
        == "NOT_LAUNCHED_ZERO_FROZEN_BUNDLES"
        and downstream.get("R4-G1") == "NOT_OPENED_ZERO_FROZEN_BUNDLES"
        and downstream.get("R4-M0") == "NOT_OPENED_NO_SELECTION"
        and downstream.get("test_access") == "BLOCKED",
    )

    check(
        checks,
        failures,
        "empty_frozen_bundle_set",
        frozen.get("worker_admitted_proposal_count") == 0
        and frozen.get("central_replay_passed_proposal_count") == 0
        and frozen.get("frozen_complete_bundle_count") == 0
        and frozen.get("frozen_complete_bundles") == []
        and frozen.get("freeze_status") == "EMPTY_FAIL_CLOSED"
        and frozen.get("audit_dispatch_allowed") is False
        and frozen.get("materialization_allowed") is False,
    )
    check(
        checks,
        failures,
        "replay_correctly_not_triggered",
        replay.get("worker_admitted_proposal_count") == 0
        and replay.get("required_proposal_count") == 0
        and replay.get("required_url_count") == 0
        and replay.get("attempted_url_count") == 0
        and replay.get("replay_records") == []
        and replay.get("status")
        == "NOT_TRIGGERED_ZERO_WORKER_ADMISSIONS",
    )

    proposal_dedup = dedup.get("proposal_deduplication", {})
    tuple_dedup = dedup.get("provenance_tuple_deduplication", {})
    source_dedup = dedup.get("source_url_deduplication", {})
    check(
        checks,
        failures,
        "proposal_and_tuple_dedup",
        proposal_dedup.get("proposal_id_mentions") == 18
        and proposal_dedup.get("unique_proposal_ids") == 18
        and proposal_dedup.get("duplicate_proposal_ids") == 0
        and tuple_dedup.get("tuple_mentions") == 18
        and tuple_dedup.get("unique_exact_tuples") == 18
        and tuple_dedup.get("duplicate_exact_tuples") == 0
        and tuple_dedup.get("collapsed_proposals") == [],
    )
    check(
        checks,
        failures,
        "source_dedup",
        source_dedup.get("source_record_mentions") == 90
        and source_dedup.get("unique_exact_urls") == 88
        and source_dedup.get("duplicate_mentions") == 2
        and len(source_dedup.get("duplicate_urls", [])) == 2,
    )
    check(
        checks,
        failures,
        "no_cross_join_or_repair",
        dedup.get("cross_join_performed") is False
        and dedup.get("central_repair_performed") is False,
    )

    check(
        checks,
        failures,
        "handoff_exact_filenames",
        set(handoff.get("exact_filenames", [])) == EXPECTED_FILES
        and len(handoff.get("exact_filenames", [])) == 6,
    )
    hash_rows = handoff.get("output_hashes")
    hash_valid = isinstance(hash_rows, list) and len(hash_rows) == 5
    if not isinstance(hash_rows, list):
        hash_rows = []
    for row in hash_rows:
        if not isinstance(row, dict):
            hash_valid = False
            continue
        filename = row.get("filename")
        path = OUTPUT_ROOT / str(filename)
        if filename == "r4_g0_handoff.json" or not path.is_file():
            hash_valid = False
            continue
        payload = canonical_lf(path)
        if (
            len(payload) != row.get("canonical_lf_bytes")
            or hashlib.sha256(payload).hexdigest()
            != row.get("canonical_lf_sha256")
        ):
            hash_valid = False
    check(
        checks,
        failures,
        "handoff_hashes_5_of_5",
        hash_valid,
    )
    counts = handoff.get("counts", {})
    check(
        checks,
        failures,
        "handoff_counts",
        counts.get("worker_lanes") == 3
        and counts.get("worker_output_files") == 15
        and counts.get("proposals_examined") == 18
        and counts.get("worker_admitted") == 0
        and counts.get("worker_excluded") == 18
        and counts.get("central_replay_required_proposals") == 0
        and counts.get("central_replays_attempted") == 0
        and counts.get("frozen_complete_bundles") == 0
        and counts.get("source_record_mentions") == 90
        and counts.get("unique_exact_source_urls") == 88
        and counts.get("g0_output_files") == 6
        and counts.get("accepted_result_rows") == 0,
    )
    check(
        checks,
        failures,
        "handoff_decision_and_next_gate",
        handoff.get("decision", {}).get("verdict") == VERDICT
        and handoff.get("decision", {}).get("audit_dispatch_allowed")
        is False
        and handoff.get("decision", {}).get("materialization_allowed")
        is False
        and handoff.get("decision", {}).get("execution_allowed") is False
        and handoff.get("next_gate")
        == (
            "MANDATORY_USER_DECISION_TARGETED_EVIDENCE_"
            "MATERIALIZATION_REDESIGN_OR_PAUSE"
        ),
    )

    report_markers = [
        "NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED",
        "18 distinct proposals",
        "D03",
        "D08",
        "D09",
        "D11",
        "R4-A1, R4-A2 and R4-A3 are not launched",
        "RESULT_STATUS remains NOT_RUN",
        "TEST_SET_OPENED remains NO",
    ]
    check(
        checks,
        failures,
        "report_policy_markers",
        all(marker in report for marker in report_markers),
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r4-g0-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R4_G0_NO_ADMISSIBLE_BUNDLE_FAIL_CLOSED_AUDITS_NOT_LAUNCHED"
            if passed
            else "FAIL_R4_G0_OUTPUT_GATE_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "output_files": {
            "present": len(actual_files),
            "expected": 6,
            "strict_json_present": 5,
            "strict_json_expected": 5,
        },
        "decision": {
            "examined": 18,
            "worker_admitted": 0,
            "centrally_admissible": 0,
            "frozen_complete_bundles": 0,
            "verdict": VERDICT,
        },
        "source_deduplication": {
            "mentions": 90,
            "unique_exact_urls": 88,
            "duplicate_mentions": 2,
        },
        "central_replay": {
            "required_proposals": 0,
            "required_urls": 0,
            "attempted": 0,
        },
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
