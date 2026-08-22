"""Fail-closed central intake validator for Stage 1E E5."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
E5 = CONTROL.parent / "rebaseline_v2" / "wave_c" / "E5_independent_lock_audit"
E4 = CONTROL.parent / "rebaseline_v2" / "wave_b" / "E4_reproduction_adaptation"

EXPECTED = {
    "independent_lock_audit.md",
    "audit_findings.json",
    "replay_receipt.json",
    "stage1e_execution_authorization.json",
    "e5_handoff.json",
}
MANIFEST_SHA = "f06e3b4e60afd53923fb343b74cedd4e1a49c75d2b4e0151197adc9c7945446f"
CONTRACT_SHA = "59394ab80d3d78c491d20346bf44cfab5ab7d75e8acbab45ae3ecaf50c62dff5"
E4_RECEIPT_SHA = "b7a7ed680f2aafe1e42fb246225c3a507a03c514f122ebeadd809ce88f5a41f7"
E4_MANIFEST_SHA = "e320eff700eae6e12d8e4059e25656b88dfd1ac1904e42290fce32944ddf41d2"
STOCHASTICITY_DECLARATION = (
    "LLM outputs are not byte-reproducible. This lockfile documents "
    "configuration, not a deterministic replay guarantee."
)


def reject_case_colliding_keys(pairs: Iterable[tuple[str, object]]) -> dict[str, object]:
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


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(checks: dict[str, bool], failures: list[str], name: str, passed: bool) -> None:
    checks[name] = bool(passed)
    if not passed:
        failures.append(name)


def validate_manifest_rows(
    rows: object,
    *,
    expected: int,
    prefix: str,
    checks: dict[str, bool],
    failures: list[str],
) -> dict[str, object]:
    details: dict[str, object] = {}
    rows_valid = isinstance(rows, list) and len(rows) == expected
    record(checks, failures, f"{prefix}_row_count", rows_valid)
    if not isinstance(rows, list):
        return details

    for index, row in enumerate(rows):
        name = f"{prefix}:{index:02d}"
        if not isinstance(row, dict):
            record(checks, failures, name, False)
            details[name] = {"passed": False, "reason": "row_not_object"}
            continue
        relpath = row.get("path")
        expected_hash = row.get("canonical_lf_sha256")
        expected_bytes = row.get("canonical_lf_bytes")
        path = ROOT / str(relpath)
        try:
            observed_bytes = canonical_lf_bytes(path)
            observed_hash = hashlib.sha256(observed_bytes).hexdigest()
            passed = (
                path.is_file()
                and observed_hash == expected_hash
                and len(observed_bytes) == expected_bytes
            )
            details[str(relpath)] = {
                "passed": passed,
                "expected_canonical_lf_sha256": expected_hash,
                "observed_canonical_lf_sha256": observed_hash,
                "expected_canonical_lf_bytes": expected_bytes,
                "observed_canonical_lf_bytes": len(observed_bytes),
            }
        except (OSError, UnicodeError) as exc:
            passed = False
            details[str(relpath)] = {"passed": False, "error": str(exc)}
        record(checks, failures, name, passed)
    return details


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    present = {path.name for path in E5.iterdir() if path.is_file()} if E5.is_dir() else set()
    record(checks, failures, "exact_five_output_files", present == EXPECTED)
    if not EXPECTED.issubset(present):
        print(
            json.dumps(
                {
                    "passed": False,
                    "missing": sorted(EXPECTED - present),
                    "unexpected": sorted(present - EXPECTED),
                },
                indent=2,
            )
        )
        return 1

    json_names = EXPECTED - {"independent_lock_audit.md"}
    try:
        parsed = {name: load_json(E5 / name) for name in json_names}
        manifest = load_json(CONTROL / "e5_frozen_input_manifest.json")
        parent_manifest = load_json(CONTROL / "e4_frozen_input_manifest.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    handoff = parsed["e5_handoff.json"]
    findings = parsed["audit_findings.json"]
    replay = parsed["replay_receipt.json"]
    authorization = parsed["stage1e_execution_authorization.json"]

    record(
        checks,
        failures,
        "manifest_hash",
        canonical_lf_sha256(CONTROL / "e5_frozen_input_manifest.json") == MANIFEST_SHA,
    )
    record(
        checks,
        failures,
        "contract_hash",
        canonical_lf_sha256(CONTROL / "e5_independent_lock_audit_contract.md")
        == CONTRACT_SHA,
    )
    record(
        checks,
        failures,
        "e4_receipt_hash",
        canonical_lf_sha256(CONTROL / "rebaseline_v2_e4_validation_receipt.json")
        == E4_RECEIPT_SHA,
    )
    record(
        checks,
        failures,
        "e4_manifest_hash",
        canonical_lf_sha256(CONTROL / "e4_frozen_input_manifest.json")
        == E4_MANIFEST_SHA,
    )

    direct_checks = validate_manifest_rows(
        manifest.get("direct_inputs"),
        expected=10,
        prefix="direct_input",
        checks=checks,
        failures=failures,
    )
    transitive_checks = validate_manifest_rows(
        parent_manifest.get("inputs"),
        expected=28,
        prefix="transitive_input",
        checks=checks,
        failures=failures,
    )

    passport = handoff.get("material_passport")
    repro_lock = passport.get("repro_lock") if isinstance(passport, dict) else None
    record(checks, failures, "passport_object", isinstance(passport, dict))
    record(
        checks,
        failures,
        "passport_verified_audit_artifact",
        isinstance(passport, dict) and passport.get("verification_status") == "VERIFIED",
    )
    record(
        checks,
        failures,
        "repro_lock_honest",
        isinstance(repro_lock, dict)
        and repro_lock.get("schema_version") == "1.0"
        and repro_lock.get("stochasticity_declaration") == STOCHASTICITY_DECLARATION
        and isinstance(repro_lock.get("model"), dict)
        and repro_lock["model"].get("id") == "gpt-5.6-sol"
        and repro_lock["model"].get("weight_stable") is False,
    )
    record(checks, failures, "lane_id", handoff.get("lane_id") == "E5_independent_lock_audit")
    record(checks, failures, "model", handoff.get("model") == "gpt-5.6-sol")
    record(checks, failures, "reasoning", handoff.get("reasoning") == "xhigh")
    record(checks, failures, "status", handoff.get("status") == "COMPLETE_FAIL_CLOSED")
    record(
        checks,
        failures,
        "verdict",
        handoff.get("verdict") == "REVISE_E4_ADDITIONAL_FINDINGS",
    )
    record(
        checks,
        failures,
        "frozen_bindings",
        handoff.get("frozen_manifest_canonical_lf_sha256") == MANIFEST_SHA
        and handoff.get("frozen_contract_canonical_lf_sha256") == CONTRACT_SHA
        and handoff.get("e4_central_validation_receipt_canonical_lf_sha256")
        == E4_RECEIPT_SHA
        and handoff.get("e4_parent_manifest_canonical_lf_sha256") == E4_MANIFEST_SHA,
    )

    input_verification = handoff.get("input_verification")
    record(
        checks,
        failures,
        "input_verification",
        isinstance(input_verification, dict)
        and input_verification.get("verdict") == "PASS"
        and input_verification.get("direct_inputs_matched") == 10
        and input_verification.get("transitive_inputs_matched") == 28
        and input_verification.get("required_artifact_checks_matched") == 38
        and input_verification.get("missing") == 0
        and input_verification.get("mismatched") == 0,
    )

    output_rows = handoff.get("outputs")
    indexed = {
        Path(str(row.get("path", ""))).name: row
        for row in output_rows
        if isinstance(output_rows, list) and isinstance(row, dict)
    } if isinstance(output_rows, list) else {}
    output_checks: dict[str, object] = {}
    for name in sorted(EXPECTED - {"e5_handoff.json"}):
        row = indexed.get(name)
        observed = canonical_lf_sha256(E5 / name)
        passed = bool(row) and row.get("canonical_lf_sha256") == observed
        output_checks[name] = {
            "passed": passed,
            "recorded": row.get("canonical_lf_sha256") if row else None,
            "observed": observed,
        }
        record(checks, failures, f"output_hash:{name}", passed)

    expected_coverage = {
        "manifest_artifact_checks": (38, 38),
        "candidate_rows": (13, 13),
        "prohibited_joins": (5, 5),
        "blocker_dispositions": (26, 26),
        "resolved_blocker_dispositions": (1, 1),
        "command_records": (10, 10),
        "decision_points": (8, 8),
        "sequence_stages": (4, 4),
        "raw_cross_dataset_league_guards": (1, 1),
    }
    coverage = handoff.get("audit_coverage")
    coverage_valid = isinstance(coverage, dict)
    if coverage_valid:
        for key, (required, audited) in expected_coverage.items():
            row = coverage.get(key)
            coverage_valid = coverage_valid and isinstance(row, dict)
            coverage_valid = coverage_valid and row.get("required") == required
            coverage_valid = coverage_valid and row.get("audited") == audited
        tolerances = coverage.get("reported_tolerances")
        coverage_valid = coverage_valid and isinstance(tolerances, dict)
        coverage_valid = coverage_valid and tolerances == {
            "required": 26,
            "audited": 26,
            "mismatched": 0,
        }
    record(checks, failures, "audit_coverage", coverage_valid)

    source_counts = {
        "CONFIRMED": 30,
        "CONTRADICTED": 1,
        "PARTIAL": 4,
        "UNAVAILABLE": 3,
        "NOT_APPLICABLE": 0,
        "total": 38,
    }
    record(
        checks,
        failures,
        "source_replay_counts",
        handoff.get("source_replay_counts") == source_counts
        and replay.get("external_source_replay_counts") == source_counts,
    )

    finding_rows = findings.get("findings")
    expected_finding_counts = {"CRITICAL": 0, "MAJOR": 4, "MINOR": 0, "total": 4}
    record(
        checks,
        failures,
        "findings",
        handoff.get("finding_counts") == expected_finding_counts
        and findings.get("finding_counts") == expected_finding_counts
        and isinstance(finding_rows, list)
        and len(finding_rows) == 4
        and {row.get("finding_id") for row in finding_rows if isinstance(row, dict)}
        == {"E5-F001", "E5-F002", "E5-F003", "E5-F004"}
        and all(
            isinstance(row, dict)
            and row.get("severity") == "MAJOR"
            and bool(row.get("owner"))
            and bool(row.get("disposition"))
            for row in finding_rows
        ),
    )

    record(
        checks,
        failures,
        "candidate_status_counts",
        handoff.get("candidate_status_counts")
        == {"READY_FOR_E5_AUDIT": 0, "PENDING_EVIDENCE": 7, "REJECTED": 6, "total": 13},
    )
    record(
        checks,
        failures,
        "blocker_disposition_counts",
        handoff.get("blocker_disposition_counts")
        == {"RESOLVED": 1, "CARRIED": 18, "REJECTED_WITH_ROW": 7, "total": 26},
    )

    command_state = handoff.get("command_packet_state")
    record(
        checks,
        failures,
        "command_packet_fail_closed",
        isinstance(command_state, dict)
        and command_state.get("commands") == 10
        and command_state.get("packet_state") == "DRAFT_BLOCKED_NOT_EXECUTABLE"
        and command_state.get("user_confirmation_required") is True
        and command_state.get("confirmed") is False
        and command_state.get("execution_authorized") is False
        and command_state.get("retry_policy") == "NO_AUTO_RETRY",
    )

    truth = handoff.get("truth_state")
    record(
        checks,
        failures,
        "truth_state",
        isinstance(truth, dict)
        and truth.get("RESULT_STATUS") == "NOT_RUN"
        and truth.get("TEST_SET_OPENED") == "NO"
        and truth.get("ACCEPTED_RESULT_ROWS") == 0
        and truth.get("project_benchmark_numbers") == "INVALID_FOR_PAPER"
        and truth.get("empirical_claims_made") is False
        and truth.get("execution_authorized") is False
        and truth.get("confirmed") is False,
    )

    record(
        checks,
        failures,
        "authorization_denied",
        authorization.get("authorized") is False
        and authorization.get("execution_authorized") is False
        and authorization.get("confirmed") is False
        and authorization.get("decision") == "DENIED_E4_FAIL_NOT_READY_ADDITIONAL_FINDINGS"
        and authorization.get("replacement_e4_packet_required") is True
        and authorization.get("new_e5_audit_required") is True
        and authorization.get("current_packet_may_be_confirmed") is False
        and authorization.get("pass_execution_authorized_emitted") is False
        and authorization.get("RESULT_STATUS") == "NOT_RUN"
        and authorization.get("TEST_SET_OPENED") == "NO"
        and authorization.get("ACCEPTED_RESULT_ROWS") == 0,
    )

    scope_guards = handoff.get("scope_guards")
    record(
        checks,
        failures,
        "scope_guards",
        isinstance(scope_guards, dict)
        and scope_guards
        and all(value is False for value in scope_guards.values()),
    )

    e4_preservation = handoff.get("e4_byte_preservation")
    preservation_valid = isinstance(e4_preservation, dict) and e4_preservation.get("verified") is True
    expected_raw = e4_preservation.get("raw_sha256") if isinstance(e4_preservation, dict) else None
    if preservation_valid and isinstance(expected_raw, dict):
        for filename, expected_hash in expected_raw.items():
            preservation_valid = preservation_valid and raw_sha256(E4 / filename) == expected_hash
    else:
        preservation_valid = False
    record(checks, failures, "e4_byte_preservation", preservation_valid)

    record(
        checks,
        failures,
        "report_verdict_present",
        "REVISE_E4_ADDITIONAL_FINDINGS"
        in (E5 / "independent_lock_audit.md").read_text(encoding="utf-8"),
    )

    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e5-validation-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_E5_COMPLETE_FAIL_CLOSED_REMEDIATION_REQUIRED"
            if not failures
            else "FAIL_E5_CENTRAL_INTAKE"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "input_check_summary": {
            "direct_expected": 10,
            "direct_matched": sum(
                1 for row in direct_checks.values() if row.get("passed") is True
            ),
            "transitive_expected": 28,
            "transitive_matched": sum(
                1 for row in transitive_checks.values() if row.get("passed") is True
            ),
        },
        "output_checks": output_checks,
        "handoff_canonical_lf_sha256": canonical_lf_sha256(E5 / "e5_handoff.json"),
        "content_verdict": handoff.get("verdict"),
        "authorization_decision": authorization.get("decision"),
        "finding_counts": handoff.get("finding_counts"),
        "candidate_status_counts": handoff.get("candidate_status_counts"),
        "execution_authorized": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "next_gate": "NEW_E4_REMEDIATION_PACKET",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
