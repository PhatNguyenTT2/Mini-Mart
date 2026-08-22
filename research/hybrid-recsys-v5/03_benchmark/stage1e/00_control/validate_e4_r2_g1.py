"""Deterministic central validator for the fail-closed R2-G1 packet."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
OUTPUT = CONTROL.parent / "rebaseline_v2" / "wave_h" / "E4_R2G1_candidate_selection"
MANIFEST = CONTROL / "e4_r2_g1_frozen_input_manifest.json"
CONTRACT = CONTROL / "e4_r2_g1_central_synthesis_contract.md"
LANE_RECEIPT = CONTROL / "rebaseline_v2_e4_r2_evidence_lanes_validation_receipt.json"

EXPECTED_FILES = {
    "central_evidence_intersection.json",
    "candidate_decision_matrix.json",
    "primary_locator_replay_log.json",
    "r2_g1_no_selection_report.md",
    "r2_g1_handoff.json",
}
EXPECTED_CANDIDATES = [
    "E3-LIGHTGCN-GOWALLA-PYTORCH-001",
    "E3-SIMGCL-YELP2018-QREC-001",
    "E3-XSIMGCL-YELP2018-SELFREC-001",
    "E3-LIGHTGCL-YELP-UPDATED-001",
    "E3-UNISREC-SCIENTIFIC-TRANS-001",
    "E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001",
    "E3-ALPHAREC-MOVIES-TV-001",
]
VERDICT = "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT"


def reject_duplicate_or_case_colliding_keys(
    pairs: Iterable[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    seen: dict[str, str] = {}
    for key, value in pairs:
        folded = key.casefold()
        if folded in seen:
            raise ValueError(
                f"duplicate/case-colliding JSON keys: {seen[folded]!r} and {key!r}"
            )
        seen[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"root JSON value is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest(path: Path) -> dict[str, object]:
    data = canonical_lf(path)
    return {
        "canonical_lf_bytes": len(data),
        "canonical_lf_sha256": hashlib.sha256(data).hexdigest(),
    }


def check(
    checks: dict[str, bool], failures: list[str], name: str, passed: bool
) -> None:
    checks[name] = bool(passed)
    if not passed:
        failures.append(name)


def closed_truth(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("RESULT_STATUS") == "NOT_RUN"
        and value.get("TEST_SET_OPENED") == "NO"
        and value.get("ACCEPTED_RESULT_ROWS") == 0
        and value.get("execution_authorized") is False
        and value.get("project_benchmark_numbers") == "INVALID_FOR_PAPER"
    )


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    present = {path.name for path in OUTPUT.iterdir() if path.is_file()} if OUTPUT.is_dir() else set()
    check(checks, failures, "exact_five_file_output_set", present == EXPECTED_FILES)
    if present != EXPECTED_FILES:
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        return 1

    try:
        manifest = load_json(MANIFEST)
        lane_receipt = load_json(LANE_RECEIPT)
        intersection = load_json(OUTPUT / "central_evidence_intersection.json")
        matrix = load_json(OUTPUT / "candidate_decision_matrix.json")
        replay = load_json(OUTPUT / "primary_locator_replay_log.json")
        handoff = load_json(OUTPUT / "r2_g1_handoff.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    manifest_rows = manifest.get("inputs")
    input_matches = 0
    if isinstance(manifest_rows, list):
        for row in manifest_rows:
            if not isinstance(row, dict):
                continue
            path = ROOT / str(row.get("path", ""))
            try:
                observed = digest(path)
                if (
                    observed["canonical_lf_bytes"] == row.get("canonical_lf_bytes")
                    and observed["canonical_lf_sha256"] == row.get("canonical_lf_sha256")
                ):
                    input_matches += 1
            except (OSError, UnicodeError):
                pass
    check(
        checks,
        failures,
        "frozen_inputs_21_of_21",
        isinstance(manifest_rows, list)
        and len(manifest_rows) == 21
        and input_matches == 21
        and manifest.get("json_input_count") == 16,
    )
    check(
        checks,
        failures,
        "manifest_candidate_order",
        manifest.get("candidate_order") == EXPECTED_CANDIDATES,
    )
    check(
        checks,
        failures,
        "manifest_no_selection_only",
        manifest.get("allowed_decision") == VERDICT,
    )
    check(
        checks,
        failures,
        "lane_receipt_gate",
        lane_receipt.get("mechanical_import_passed") is True
        and lane_receipt.get("contract_conformity_passed") is False
        and lane_receipt.get("positive_selection_gate_passed") is False
        and lane_receipt.get("no_selection_synthesis_allowed") is True
        and lane_receipt.get("verdict")
        == "R2_LANES_IMPORTED_HASH_VALIDATED_CONTRACT_NONCONFORMANT_NO_SELECTION_ONLY",
    )

    output_rows = handoff.get("outputs")
    output_index = {
        Path(str(row.get("path", ""))).name: row
        for row in output_rows
        if isinstance(output_rows, list) and isinstance(row, dict)
    } if isinstance(output_rows, list) else {}
    expected_non_handoff = EXPECTED_FILES - {"r2_g1_handoff.json"}
    output_checks: dict[str, object] = {}
    output_hashes_pass = set(output_index) == expected_non_handoff
    for name in sorted(expected_non_handoff):
        observed = digest(OUTPUT / name)
        declared = output_index.get(name)
        passed = (
            isinstance(declared, dict)
            and declared.get("canonical_lf_bytes") == observed["canonical_lf_bytes"]
            and declared.get("canonical_lf_sha256") == observed["canonical_lf_sha256"]
        )
        output_hashes_pass = output_hashes_pass and passed
        output_checks[name] = {"passed": passed, **observed}
    check(checks, failures, "four_non_handoff_output_hashes", output_hashes_pass)

    passport = handoff.get("material_passport")
    repro = passport.get("repro_lock") if isinstance(passport, dict) else None
    model = repro.get("model") if isinstance(repro, dict) else None
    declaration = passport.get("experiment_intake_declaration") if isinstance(passport, dict) else None
    check(
        checks,
        failures,
        "material_passport_and_repro_lock",
        isinstance(passport, dict)
        and passport.get("verification_status") == "UNVERIFIED"
        and isinstance(repro, dict)
        and isinstance(model, dict)
        and model.get("id") == "gpt-5.6-sol"
        and model.get("reasoning") == "high"
        and model.get("weight_stable") is False
        and isinstance(declaration, dict)
        and declaration.get("status") == "no_experiments_declared",
    )
    check(
        checks,
        failures,
        "handoff_model",
        handoff.get("actual_model") == "gpt-5.6-sol"
        and handoff.get("actual_reasoning") == "high",
    )
    check(checks, failures, "handoff_truth_state", closed_truth(handoff.get("truth_state")))
    flags = handoff.get("forbidden_operation_flags")
    check(
        checks,
        failures,
        "all_forbidden_operations_false",
        isinstance(flags, dict) and bool(flags) and all(value is False for value in flags.values()),
    )

    candidate_rows = intersection.get("candidate_rows")
    check(
        checks,
        failures,
        "intersection_7_rows_in_order",
        isinstance(candidate_rows, list)
        and [row.get("row_id") for row in candidate_rows if isinstance(row, dict)]
        == EXPECTED_CANDIDATES,
    )
    check(
        checks,
        failures,
        "intersection_zero_positive",
        isinstance(candidate_rows, list)
        and all(
            isinstance(row, dict)
            and row.get("positive_selection_eligible") is False
            for row in candidate_rows
        )
        and intersection.get("intersection_summary", {}).get("selected_candidate_count") == 0
        and intersection.get("verdict") == VERDICT,
    )
    xsim = candidate_rows[2] if isinstance(candidate_rows, list) and len(candidate_rows) == 7 else None
    check(
        checks,
        failures,
        "xsim_current_row_rejected",
        isinstance(xsim, dict)
        and xsim.get("central_disposition") == "REJECT_CURRENT_ROW"
        and xsim.get("lane_statuses", {}).get("R2-A1") == "DISPOSITIVE_REJECT",
    )
    check(
        checks,
        failures,
        "source_deduplication",
        intersection.get("source_deduplication")
        == {
            "authoritative_source_mentions": 77,
            "unique_urls": 62,
            "duplicate_mentions_removed_from_independence_count": 15,
            "dedup_key": "exact URL string",
            "repeated_url_is_independent_evidence": False,
        },
    )

    matrix_rows = matrix.get("rows")
    downstream = matrix.get("downstream_routing")
    check(
        checks,
        failures,
        "decision_matrix_zero_selected",
        isinstance(matrix_rows, list)
        and len(matrix_rows) == 7
        and all(isinstance(row, dict) and row.get("selected") is False for row in matrix_rows)
        and matrix.get("decision_counts", {}).get("selected") == 0
        and matrix.get("verdict") == VERDICT,
    )
    check(
        checks,
        failures,
        "all_downstream_gates_blocked",
        isinstance(downstream, dict)
        and downstream.get("R2-M0") == "BLOCKED_NO_SELECTED_CANDIDATE"
        and all(value == "BLOCKED" for key, value in downstream.items() if key != "R2-M0"),
    )

    replay_summary = replay.get("summary")
    replay_flags = replay.get("forbidden_operations")
    check(
        checks,
        failures,
        "primary_locator_replay_6_of_6",
        isinstance(replay.get("replays"), list)
        and len(replay["replays"]) == 6
        and isinstance(replay_summary, dict)
        and replay_summary.get("attempted") == 6
        and replay_summary.get("successful") == 6
        and replay_summary.get("positive_selection_closures") == 0,
    )
    check(
        checks,
        failures,
        "replay_scope_closed",
        isinstance(replay_flags, dict)
        and bool(replay_flags)
        and all(value is False for value in replay_flags.values()),
    )
    report_text = (OUTPUT / "r2_g1_no_selection_report.md").read_text(encoding="utf-8")
    check(
        checks,
        failures,
        "report_fail_closed_language",
        VERDICT in report_text
        and "All benchmark values remain `INVALID_FOR_PAPER`" in report_text
        and "Do not start R2-M0" in report_text,
    )
    check(
        checks,
        failures,
        "handoff_verdict_and_routing",
        handoff.get("verdict") == VERDICT
        and handoff.get("fail_closed") is True
        and handoff.get("selection", {}).get("selected_candidate_count") == 0
        and handoff.get("downstream", {}).get("R2-M0") == "BLOCKED_NO_SELECTION",
    )

    handoff_digest = digest(OUTPUT / "r2_g1_handoff.json")
    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-r2-g1-validation-1.0",
        "created_at": "2026-08-22",
        "passed": not failures,
        "verdict": (
            "PASS_R2_G1_NO_SELECTION_FAIL_CLOSED_DOWNSTREAM_BLOCKED"
            if not failures
            else "FAIL_R2_G1_CENTRAL_VALIDATION"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 21,
            "matched": input_matches,
            "manifest": digest(MANIFEST),
            "contract": digest(CONTRACT),
            "lane_validation_receipt": digest(LANE_RECEIPT),
        },
        "outputs": {
            "expected_files": 5,
            "present_files": len(present),
            "non_handoff_output_checks": output_checks,
            "handoff": handoff_digest,
        },
        "selection": {
            "candidate_count": 7,
            "fully_sufficient": 0,
            "selected": 0,
            "verdict": VERDICT,
        },
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
            "project_benchmark_numbers": "INVALID_FOR_PAPER",
        },
        "next_gate": "USER_CHECKPOINT_BEFORE_CHANGE_CONTROLLED_EVIDENCE_REMEDIATION",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
