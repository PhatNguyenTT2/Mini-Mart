"""Fail-closed central intake validator for Stage 1E E5-R1 Wave F."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
WAVE_F = (
    CONTROL.parent
    / "rebaseline_v2"
    / "wave_f"
    / "E5_R1_independent_remediation_audit"
)

MANIFEST_SHA = "25a44c845b3a034fea82c4d335923dfff931eb7252f118c3ae7e614ba696895e"
CONTRACT_SHA = "7147cdbf3732f8c8c46c275c8b9c21bad392a0abea76b50217d0616e7868320e"
R1C_RECEIPT_SHA = "bd7e0ed6b3e204ee14f707cab0af33e346f40067bd132e7e9311920ecbd31d2c"
EXPECTED_VERDICT = "PASS_REMEDIATION_INTEGRITY_EXECUTION_DENIED"
EXPECTED_FILES = {
    "independent_remediation_audit.md",
    "audit_findings.json",
    "replay_receipt.json",
    "stage1e_execution_authorization.json",
    "e5_r1_handoff.json",
}


def reject_case_colliding_keys(
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
        object_pairs_hook=reject_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"root JSON value is not an object: {path}")
    return value


def canonical_lf_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n")


def canonical_lf_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_lf_bytes(path)).hexdigest()


def record(
    checks: dict[str, bool], failures: list[str], name: str, passed: bool
) -> None:
    checks[name] = bool(passed)
    if not passed:
        failures.append(name)


def truth_state_is_closed(row: object) -> bool:
    return (
        isinstance(row, dict)
        and row.get("RESULT_STATUS", row.get("result_status")) == "NOT_RUN"
        and row.get("TEST_SET_OPENED", row.get("test_set_opened")) == "NO"
        and row.get("ACCEPTED_RESULT_ROWS", row.get("accepted_result_rows")) == 0
        and row.get("execution_authorized") is False
        and row.get("confirmed") is False
    )


def scope_guards_are_closed(row: object) -> bool:
    return isinstance(row, dict) and bool(row) and all(value is False for value in row.values())


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    present = {path.name for path in WAVE_F.iterdir() if path.is_file()} if WAVE_F.is_dir() else set()
    record(checks, failures, "exact_five_file_write_set", present == EXPECTED_FILES)
    if present != EXPECTED_FILES:
        print(json.dumps({"passed": False, "failures": failures, "present": sorted(present)}, indent=2))
        return 1

    try:
        manifest = load_json(CONTROL / "e5_r1_frozen_input_manifest.json")
        r1c_receipt = load_json(CONTROL / "rebaseline_v2_e4_r1c_validation_receipt.json")
        findings = load_json(WAVE_F / "audit_findings.json")
        replay = load_json(WAVE_F / "replay_receipt.json")
        authorization = load_json(WAVE_F / "stage1e_execution_authorization.json")
        handoff = load_json(WAVE_F / "e5_r1_handoff.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    record(
        checks,
        failures,
        "manifest_self_hash",
        canonical_lf_sha256(CONTROL / "e5_r1_frozen_input_manifest.json")
        == MANIFEST_SHA,
    )
    record(
        checks,
        failures,
        "contract_hash",
        canonical_lf_sha256(CONTROL / "e5_r1_independent_remediation_audit_contract.md")
        == CONTRACT_SHA,
    )
    record(
        checks,
        failures,
        "r1c_validation_receipt_hash",
        canonical_lf_sha256(CONTROL / "rebaseline_v2_e4_r1c_validation_receipt.json")
        == R1C_RECEIPT_SHA,
    )
    record(
        checks,
        failures,
        "r1c_entry_gate",
        r1c_receipt.get("passed") is True
        and r1c_receipt.get("verdict")
        == "PASS_E4_R1C_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT",
    )

    input_rows = manifest.get("inputs")
    input_matches = 0
    if isinstance(input_rows, list):
        for row in input_rows:
            if not isinstance(row, dict):
                continue
            path = ROOT / str(row.get("path", ""))
            try:
                observed = canonical_lf_bytes(path)
                if (
                    len(observed) == row.get("canonical_lf_bytes")
                    and hashlib.sha256(observed).hexdigest()
                    == row.get("canonical_lf_sha256")
                ):
                    input_matches += 1
            except (OSError, UnicodeError):
                pass
    record(
        checks,
        failures,
        "frozen_inputs_19_of_19",
        isinstance(input_rows, list)
        and len(input_rows) == 19
        and input_matches == 19,
    )

    output_rows = handoff.get("outputs")
    output_index = {
        Path(str(row.get("path", ""))).name: row
        for row in output_rows
        if isinstance(output_rows, list) and isinstance(row, dict)
    } if isinstance(output_rows, list) else {}
    expected_outputs = EXPECTED_FILES - {"e5_r1_handoff.json"}
    output_details: dict[str, object] = {}
    output_hashes_ok = set(output_index) == expected_outputs
    for name in sorted(expected_outputs):
        observed = canonical_lf_bytes(WAVE_F / name)
        observed_hash = hashlib.sha256(observed).hexdigest()
        row = output_index.get(name)
        passed = (
            isinstance(row, dict)
            and row.get("canonical_lf_bytes") == len(observed)
            and row.get("canonical_lf_sha256") == observed_hash
        )
        output_hashes_ok = output_hashes_ok and passed
        output_details[name] = {
            "passed": passed,
            "canonical_lf_bytes": len(observed),
            "canonical_lf_sha256": observed_hash,
        }
    record(checks, failures, "four_output_hashes", output_hashes_ok)

    finding_counts = findings.get("finding_counts")
    closures = findings.get("original_finding_closures")
    closure_counts = findings.get("closure_counts")
    record(
        checks,
        failures,
        "audit_verdict_and_zero_new_findings",
        findings.get("verdict") == EXPECTED_VERDICT
        and finding_counts
        == {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "total_new_findings": 0}
        and findings.get("new_findings") == [],
    )
    record(
        checks,
        failures,
        "four_original_finding_closures",
        isinstance(closures, list)
        and len(closures) == 4
        and {row.get("finding_id") for row in closures if isinstance(row, dict)}
        == {"E5-F001", "E5-F002", "E5-F003", "E5-F004"}
        and isinstance(closure_counts, dict)
        and closure_counts.get("closed_for_remediation_integrity") == 4
        and closure_counts.get("closed_for_execution_readiness") == 0,
    )

    replay_totals = replay.get("input_replay_totals")
    record(
        checks,
        failures,
        "replay_entry_and_input_totals",
        isinstance(replay.get("entry_gate"), dict)
        and replay["entry_gate"].get("passed") is True
        and replay["entry_gate"].get("observed_receipt")
        == "PASS_E4_R1C_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT"
        and isinstance(replay_totals, dict)
        and replay_totals.get("listed_inputs_expected") == 19
        and replay_totals.get("canonical_lf_hash_matches") == 19
        and replay_totals.get("manifest_plus_inputs_passed") == 20
        and replay_totals.get("failed") == 0,
    )

    candidates = replay.get("candidate_and_comparison_replay")
    record(
        checks,
        failures,
        "candidate_and_comparison_replay",
        isinstance(candidates, dict)
        and candidates.get("candidate_rows") == 13
        and candidates.get("ready") == 0
        and candidates.get("pending") == 7
        and candidates.get("rejected") == 6
        and candidates.get("prohibited_joins") == 5
        and candidates.get("prohibited_joins_rejected") == 5
        and candidates.get("selected_row") is None
        and candidates.get("priority_is_selection") is False
        and candidates.get("raw_cross_dataset_metric_league_allowed") is False
        and candidates.get("source_center_as_v5_superiority_allowed") is False,
    )

    commands = replay.get("command_control_replay")
    record(
        checks,
        failures,
        "command_control_replay",
        isinstance(commands, dict)
        and commands.get("central_replacement_packet") is True
        and commands.get("closed_receipt_schemas") == 7
        and commands.get("command_receipt_mappings") == 10
        and commands.get("command_records") == 10
        and commands.get("ordered_ordinals") == list(range(0, 100, 10))
        and commands.get("null_shell_fields") == 10
        and commands.get("null_working_directory_fields") == 10
        and commands.get("null_command_fields") == 10
        and commands.get("no_auto_retry_records") == 10
        and commands.get("confirmed_false_records") == 10
        and commands.get("execution_authorized_false_records") == 10
        and commands.get("test_denied_records") == 10
        and commands.get("prerequisites") == 15
        and commands.get("resolved_prerequisites") == 1
        and commands.get("only_resolved_prerequisite")
        == "P13_NEW_FROZEN_CENTRAL_PACKET"
        and commands.get("unresolved_prerequisites") == 14
        and commands.get("materialized_enforcement_verified") is False,
    )
    record(
        checks,
        failures,
        "mechanical_assertions_28_of_28",
        replay.get("mechanical_assertions")
        == {"total": 28, "passed": 28, "failed": 0},
    )
    record(
        checks,
        failures,
        "reproducibility_cannot_verify",
        isinstance(replay.get("reproducibility"), dict)
        and replay["reproducibility"].get("method") == "not run"
        and replay["reproducibility"].get("verdict") == "CANNOT_VERIFY",
    )
    record(checks, failures, "replay_truth_state", truth_state_is_closed(replay.get("truth_state")))
    record(checks, failures, "replay_scope_guards", scope_guards_are_closed(replay.get("scope_guards")))

    record(
        checks,
        failures,
        "authorization_denial",
        authorization.get("authorized") is False
        and authorization.get("execution_authorized") is False
        and authorization.get("confirmed") is False
        and authorization.get("RESULT_STATUS") == "NOT_RUN"
        and authorization.get("TEST_SET_OPENED") == "NO"
        and authorization.get("ACCEPTED_RESULT_ROWS") == 0
        and authorization.get("retry_policy") == "NO_AUTO_RETRY"
        and authorization.get("pass_execution_authorized_emitted") is False
        and authorization.get("forbidden_verdict_emitted") is False
        and authorization.get("audit_verdict") == EXPECTED_VERDICT,
    )

    passport = handoff.get("material_passport")
    repro_lock = passport.get("repro_lock") if isinstance(passport, dict) else None
    model = repro_lock.get("model") if isinstance(repro_lock, dict) else None
    record(
        checks,
        failures,
        "handoff_passport_and_model",
        isinstance(passport, dict)
        and passport.get("verification_status") == "ANALYZED"
        and isinstance(model, dict)
        and model.get("id") == "gpt-5.6-sol"
        and model.get("reasoning") == "xhigh"
        and model.get("weight_stable") is False,
    )
    record(
        checks,
        failures,
        "handoff_verdict",
        handoff.get("verdict") == EXPECTED_VERDICT
        and handoff.get("fail_closed") is True,
    )
    record(checks, failures, "handoff_truth_state", truth_state_is_closed(handoff.get("truth_state")))
    record(checks, failures, "handoff_scope_guards", scope_guards_are_closed(handoff.get("scope_guards")))
    handoff_authorization = handoff.get("authorization")
    record(
        checks,
        failures,
        "handoff_authorization_denial",
        isinstance(handoff_authorization, dict)
        and handoff_authorization.get("authorized") is False
        and handoff_authorization.get("current_packet_executable") is False
        and handoff_authorization.get("current_packet_may_be_confirmed") is False
        and handoff_authorization.get("pass_execution_authorized_emitted") is False,
    )

    handoff_hash = canonical_lf_sha256(WAVE_F / "e5_r1_handoff.json")
    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e5-r1-central-validation-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_E5_R1_REMEDIATION_INTEGRITY_EXECUTION_DENIED"
            if not failures
            else "FAIL_E5_R1_CENTRAL_INTAKE"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "central_import": {
            "source_commit": "c2211cb9a4536f747fad5b44dfd725319838b6d6",
            "parent_commit": "de91bdd06df280aa60082e775fc6e06a1c1cc810",
            "import_method": "git-fast-forward",
            "central_tip": "c2211cb9a4536f747fad5b44dfd725319838b6d6",
            "preserved_dirty_user_state": True,
        },
        "frozen_inputs": {
            "expected": 19,
            "matched": input_matches,
            "manifest_canonical_lf_sha256": canonical_lf_sha256(
                CONTROL / "e5_r1_frozen_input_manifest.json"
            ),
            "contract_canonical_lf_sha256": canonical_lf_sha256(
                CONTROL / "e5_r1_independent_remediation_audit_contract.md"
            ),
        },
        "outputs": {
            "expected_files": 5,
            "present_files": len(present),
            "non_handoff_output_checks": output_details,
            "handoff_canonical_lf_bytes": len(
                canonical_lf_bytes(WAVE_F / "e5_r1_handoff.json")
            ),
            "handoff_canonical_lf_sha256": handoff_hash,
        },
        "audit_result": {
            "verdict": EXPECTED_VERDICT,
            "new_critical": 0,
            "new_major": 0,
            "new_minor": 0,
            "original_findings_closed_for_remediation_integrity": 4,
            "original_findings_closed_for_execution_readiness": 0,
            "mechanical_assertions_passed": 28,
            "mechanical_assertions_expected": 28,
        },
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
            "confirmed": False,
        },
        "next_gate": "E4_R2_EVIDENCE_AND_MATERIALIZATION_PLANNING_NOT_EXECUTION",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
