"""Fail-closed structural and cross-artifact validator for Stage 1E E4."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
E4 = CONTROL.parent / "rebaseline_v2" / "wave_b" / "E4_reproduction_adaptation"

EXPECTED = {
    "selected_reference_bundle.json",
    "reproduction_execution_plan.md",
    "v5_adapter_and_evaluator_contract.md",
    "cross_dataset_reporting_contract.md",
    "exact_command_confirmation_packet.json",
    "e4_handoff.json",
}
MANIFEST_SHA = "e320eff700eae6e12d8e4059e25656b88dfd1ac1904e42290fce32944ddf41d2"
CONTRACT_SHA = "368df1ab39df6f4cf03565cd871ba2fc5276a886f314557c6c0ff1244e9e63e5"
WAVE_A_RECEIPT_SHA = "1024cd38692a6632e4972484f37fd58e24ea05744e00bd33b61eca4af470b44a"
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


def canonical_lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def record(checks: dict[str, bool], failures: list[str], name: str, passed: bool) -> None:
    checks[name] = bool(passed)
    if not passed:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    missing = sorted(name for name in EXPECTED if not (E4 / name).is_file())
    record(checks, failures, "all_six_outputs_present", not missing)
    if missing:
        print(json.dumps({"passed": False, "missing": missing}, indent=2))
        return 1

    try:
        handoff = load_json(E4 / "e4_handoff.json")
        bundle = load_json(E4 / "selected_reference_bundle.json")
        commands = load_json(E4 / "exact_command_confirmation_packet.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    passport = handoff.get("material_passport")
    repro_lock = passport.get("repro_lock") if isinstance(passport, dict) else None
    required_passport = {
        "origin_skill",
        "origin_mode",
        "origin_date",
        "verification_status",
        "version_label",
        "repro_lock",
    }
    record(checks, failures, "passport_object", isinstance(passport, dict))
    record(
        checks,
        failures,
        "passport_required_fields",
        isinstance(passport, dict) and required_passport.issubset(passport),
    )
    record(
        checks,
        failures,
        "passport_unverified",
        isinstance(passport, dict) and passport.get("verification_status") == "UNVERIFIED",
    )
    record(checks, failures, "repro_lock_object", isinstance(repro_lock, dict))
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

    record(checks, failures, "lane_id", handoff.get("lane_id") == "E4_reproduction_adaptation")
    record(checks, failures, "model", handoff.get("model") == "gpt-5.6-sol")
    record(checks, failures, "reasoning", handoff.get("reasoning") == "xhigh")
    record(checks, failures, "status", handoff.get("status") == "COMPLETE_FAIL_CLOSED")
    record(checks, failures, "verdict", handoff.get("verdict") == "FAIL_NOT_READY_FOR_E5")
    record(
        checks,
        failures,
        "verdict_detail",
        handoff.get("verdict_detail") == "BLOCKED_NO_READY_REFERENCE_BUNDLE",
    )
    record(
        checks,
        failures,
        "manifest_hash",
        handoff.get("frozen_manifest_canonical_lf_sha256") == MANIFEST_SHA,
    )
    record(
        checks,
        failures,
        "contract_hash",
        handoff.get("frozen_contract_canonical_lf_sha256") == CONTRACT_SHA,
    )
    record(
        checks,
        failures,
        "wave_a_receipt_hash",
        handoff.get("wave_a_validation_receipt_canonical_lf_sha256")
        == WAVE_A_RECEIPT_SHA,
    )

    input_verification = handoff.get("input_verification")
    record(
        checks,
        failures,
        "input_verification",
        isinstance(input_verification, dict)
        and input_verification.get("verdict") == "PASS"
        and input_verification.get("listed_inputs") == 28
        and input_verification.get("listed_inputs_matched") == 28
        and input_verification.get("listed_inputs_missing") == 0
        and input_verification.get("listed_inputs_mismatched") == 0,
    )

    truth = handoff.get("truth_state")
    record(
        checks,
        failures,
        "truth_state",
        isinstance(truth, dict)
        and truth.get("result_status") == "NOT_RUN"
        and truth.get("test_set_opened") == "NO"
        and truth.get("ACCEPTED_RESULT_ROWS") == 0
        and truth.get("execution_authorized") is False
        and truth.get("empirical_claims_made") is False,
    )

    expected_counts = {
        "READY_FOR_E5_AUDIT": 0,
        "ACQUISITION_GATE": 0,
        "EXTERNAL_COMPUTE_GATE": 0,
        "PENDING_EVIDENCE": 7,
        "REJECTED": 6,
        "total_candidate_rows": 13,
    }
    record(
        checks,
        failures,
        "handoff_candidate_counts",
        handoff.get("candidate_status_counts") == expected_counts,
    )
    bundle_counts = bundle.get("status_counts")
    record(
        checks,
        failures,
        "bundle_candidate_counts",
        isinstance(bundle_counts, dict)
        and bundle_counts.get("READY_FOR_E5_AUDIT") == 0
        and bundle_counts.get("ACQUISITION_GATE") == 0
        and bundle_counts.get("EXTERNAL_COMPUTE_GATE") == 0
        and bundle_counts.get("PENDING_EVIDENCE") == 7
        and bundle_counts.get("REJECTED") == 6
        and bundle_counts.get("total") == 13
        and isinstance(bundle.get("candidate_rows"), list)
        and len(bundle["candidate_rows"]) == 13,
    )

    blocker_accounting = handoff.get("blocker_accounting")
    dispositions = bundle.get("blocker_dispositions")
    record(
        checks,
        failures,
        "blocker_accounting",
        isinstance(blocker_accounting, dict)
        and blocker_accounting.get("wave_a_blockers_total") == 26
        and blocker_accounting.get("RESOLVED") == 1
        and blocker_accounting.get("CARRIED") == 18
        and blocker_accounting.get("REJECTED_WITH_ROW") == 7
        and blocker_accounting.get("all_blockers_mapped") is True
        and isinstance(dispositions, list)
        and len(dispositions) == 26,
    )

    output_rows = handoff.get("outputs")
    output_checks: dict[str, object] = {}
    expected_hashed_outputs = EXPECTED - {"e4_handoff.json"}
    indexed = {
        Path(str(row.get("path", ""))).name: row
        for row in output_rows
        if isinstance(output_rows, list) and isinstance(row, dict)
    } if isinstance(output_rows, list) else {}
    for name in sorted(expected_hashed_outputs):
        row = indexed.get(name)
        actual = canonical_lf_sha256(E4 / name)
        passed = bool(row) and row.get("canonical_lf_sha256") == actual
        output_checks[name] = {
            "passed": passed,
            "recorded": row.get("canonical_lf_sha256") if row else None,
            "actual": actual,
        }
        record(checks, failures, f"output_hash:{name}", passed)

    record(
        checks,
        failures,
        "bundle_fail_closed",
        bundle.get("fail_closed_verdict") == "BLOCKED_NO_READY_REFERENCE_BUNDLE"
        and bundle.get("external_validation_verdict")
        == "NO_DATASET_PASSES_CURRENT_EXTERNAL_CONTRACT",
    )
    record(
        checks,
        failures,
        "command_packet_root",
        commands.get("packet_state") == "DRAFT_BLOCKED_NOT_EXECUTABLE"
        and commands.get("candidate_status") == "PENDING_EVIDENCE"
        and commands.get("user_confirmation_required") is True
        and commands.get("confirmed") is False
        and commands.get("execution_authorized") is False
        and commands.get("no_command_was_executed") is True
        and commands.get("new_packet_required_for_any_execution") is True
        and commands.get("fail_closed_verdict") == "DO_NOT_EXECUTE",
    )
    command_rows = commands.get("commands")
    command_rows_valid = isinstance(command_rows, list) and len(command_rows) == 10
    if command_rows_valid:
        command_rows_valid = all(
            isinstance(row, dict)
            and row.get("user_confirmation_required") is True
            and row.get("confirmed") is False
            and row.get("execution_authorized") is False
            and row.get("retry_policy") == "NO_AUTO_RETRY"
            and row.get("status")
            in {"BLOCKED_NOT_EXECUTABLE", "UNAVAILABLE_SOURCE_COMMAND_ROW_REMAINS_PENDING"}
            for row in command_rows
        )
    record(checks, failures, "command_rows_fail_closed", command_rows_valid)

    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-validation-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_FROZEN_PACKET_READY_FOR_E5_FAIL_CLOSED_AUDIT"
            if not failures
            else "FAIL_E4_PACKET_NOT_READY_FOR_E5"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "output_checks": output_checks,
        "handoff_canonical_lf_sha256": canonical_lf_sha256(E4 / "e4_handoff.json"),
        "content_verdict": handoff.get("verdict"),
        "content_verdict_detail": handoff.get("verdict_detail"),
        "candidate_status_counts": handoff.get("candidate_status_counts"),
        "blocker_accounting": handoff.get("blocker_accounting"),
        "execution_authorized": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
