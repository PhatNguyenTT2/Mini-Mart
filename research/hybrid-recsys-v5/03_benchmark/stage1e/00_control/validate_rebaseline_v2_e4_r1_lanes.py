"""Fail-closed central intake validator for Stage 1E E4-R1A/R1B lanes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
WAVE_D = CONTROL.parent / "rebaseline_v2" / "wave_d"
R1A = WAVE_D / "E4_R1A_provenance_config"
R1B = WAVE_D / "E4_R1B_command_controls"

MANIFEST_SHA = "d0a5db377c36f7109b4b56089ac024bb8ddcd4b5badc5aeb464969aa2e13d817"
CONTRACT_SHA = "b51c41a931ef88a1fcc356394600b3c2fcdafad68b5599477c9a894040d82538"
R1A_HANDOFF_SHA = "6d779deeebd1422860665d42713da567c59fc3075045f406d308933aa9f13f26"
R1B_HANDOFF_SHA = "61dd6a87dacb09916ef0e10f0798ffffc3f4c641f3a3b3dbe6add8f39652a84b"
V5_SPEC_PATH = "backend/docs/chatbot/seed-product/benchmark-spec-v5.json"
V5_SPEC_SHA = "acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d"
STOCHASTICITY_DECLARATION = (
    "LLM outputs are not byte-reproducible. This lockfile documents "
    "configuration, not a deterministic replay guarantee."
)

EXPECTED_A = {
    "source_and_binding_corrections.json",
    "candidate_readiness_delta.json",
    "r1a_evidence_report.md",
    "r1a_handoff.json",
}
EXPECTED_B = {
    "mechanical_control_spec.md",
    "replacement_command_packet_draft.json",
    "receipt_schema_bundle.json",
    "r1b_handoff.json",
}
EXPECTED_COMMAND_IDS = [
    "E4-LGCN-000-PREFLIGHT",
    "E4-LGCN-010-CLONE",
    "E4-LGCN-020-CHECKOUT",
    "E4-LGCN-030-VERIFY-SOURCE",
    "E4-LGCN-040-CREATE-ENV",
    "E4-LGCN-050-INSTALL",
    "E4-LGCN-060-PREPROCESS-GATE",
    "E4-LGCN-070-TRAIN-AND-INTEGRATED-EVALUATE",
    "E4-LGCN-080-STANDALONE-EVALUATE",
    "E4-LGCN-090-FINALIZE-RECEIPTS",
]
EXPECTED_REPLACEMENT_COMMAND_IDS = [
    "E4-R1B-000-PREFLIGHT",
    "E4-R1B-010-SOURCE-ACQUIRE",
    "E4-R1B-020-SOURCE-CHECKOUT",
    "E4-R1B-030-SOURCE-VERIFY",
    "E4-R1B-040-ENVIRONMENT-CREATE",
    "E4-R1B-050-DEPENDENCY-INSTALL",
    "E4-R1B-060-PREPROCESS",
    "E4-R1B-070-RUN",
    "E4-R1B-080-EVALUATE",
    "E4-R1B-090-FINALIZE",
]


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


def record(checks: dict[str, bool], failures: list[str], name: str, passed: bool) -> None:
    checks[name] = bool(passed)
    if not passed:
        failures.append(name)


def truth_value(row: dict[str, object], upper: str, lower: str) -> object:
    return row.get(upper, row.get(lower))


def truth_state_is_closed(row: object) -> bool:
    return (
        isinstance(row, dict)
        and truth_value(row, "RESULT_STATUS", "result_status") == "NOT_RUN"
        and truth_value(row, "TEST_SET_OPENED", "test_set_opened") == "NO"
        and truth_value(row, "ACCEPTED_RESULT_ROWS", "accepted_result_rows") == 0
        and row.get("execution_authorized") is False
        and row.get("confirmed") is False
    )


def scope_guards_are_closed(row: object) -> bool:
    return isinstance(row, dict) and bool(row) and all(value is False for value in row.values())


def passport_is_honest(handoff: dict[str, object]) -> bool:
    passport = handoff.get("material_passport")
    repro = passport.get("repro_lock") if isinstance(passport, dict) else None
    model = repro.get("model") if isinstance(repro, dict) else None
    return (
        isinstance(passport, dict)
        and passport.get("verification_status") == "UNVERIFIED"
        and isinstance(passport.get("version_label"), str)
        and bool(passport.get("version_label"))
        and isinstance(repro, dict)
        and repro.get("schema_version") == "1.0"
        and repro.get("stochasticity_declaration") == STOCHASTICITY_DECLARATION
        and isinstance(model, dict)
        and model.get("id") == "gpt-5.6-sol"
        and model.get("weight_stable") is False
    )


def verify_handoff_outputs(
    handoff: dict[str, object],
    lane_root: Path,
    expected_names: set[str],
) -> tuple[bool, dict[str, object]]:
    rows = handoff.get("outputs")
    details: dict[str, object] = {}
    indexed = {
        Path(str(row.get("path", ""))).name: row
        for row in rows
        if isinstance(rows, list) and isinstance(row, dict)
    } if isinstance(rows, list) else {}
    valid = set(indexed) == expected_names
    for name in sorted(expected_names):
        row = indexed.get(name)
        observed_bytes = canonical_lf_bytes(lane_root / name)
        observed_hash = hashlib.sha256(observed_bytes).hexdigest()
        passed = (
            isinstance(row, dict)
            and row.get("canonical_lf_bytes") == len(observed_bytes)
            and row.get("canonical_lf_sha256") == observed_hash
        )
        valid = valid and passed
        details[name] = {
            "passed": passed,
            "canonical_lf_bytes": len(observed_bytes),
            "canonical_lf_sha256": observed_hash,
        }
    return valid, details


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    present_a = {path.name for path in R1A.iterdir() if path.is_file()} if R1A.is_dir() else set()
    present_b = {path.name for path in R1B.iterdir() if path.is_file()} if R1B.is_dir() else set()
    record(checks, failures, "r1a_exact_write_set", present_a == EXPECTED_A)
    record(checks, failures, "r1b_exact_write_set", present_b == EXPECTED_B)
    if present_a != EXPECTED_A or present_b != EXPECTED_B:
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        return 1

    try:
        manifest = load_json(CONTROL / "e4_r1_frozen_input_manifest.json")
        a_handoff = load_json(R1A / "r1a_handoff.json")
        a_sources = load_json(R1A / "source_and_binding_corrections.json")
        a_delta = load_json(R1A / "candidate_readiness_delta.json")
        b_handoff = load_json(R1B / "r1b_handoff.json")
        b_packet = load_json(R1B / "replacement_command_packet_draft.json")
        b_receipts = load_json(R1B / "receipt_schema_bundle.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    record(
        checks,
        failures,
        "manifest_self_hash",
        canonical_lf_sha256(CONTROL / "e4_r1_frozen_input_manifest.json") == MANIFEST_SHA,
    )
    record(
        checks,
        failures,
        "contract_hash",
        canonical_lf_sha256(CONTROL / "e4_r1_parallel_remediation_contract.md") == CONTRACT_SHA,
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
        "frozen_inputs_17_of_17",
        isinstance(input_rows, list) and len(input_rows) == 17 and input_matches == 17,
    )

    record(checks, failures, "r1a_handoff_hash", canonical_lf_sha256(R1A / "r1a_handoff.json") == R1A_HANDOFF_SHA)
    record(checks, failures, "r1b_handoff_hash", canonical_lf_sha256(R1B / "r1b_handoff.json") == R1B_HANDOFF_SHA)
    record(checks, failures, "r1a_passport", passport_is_honest(a_handoff))
    record(checks, failures, "r1b_passport", passport_is_honest(b_handoff))

    a_outputs_ok, a_output_checks = verify_handoff_outputs(
        a_handoff,
        R1A,
        EXPECTED_A - {"r1a_handoff.json"},
    )
    b_outputs_ok, b_output_checks = verify_handoff_outputs(
        b_handoff,
        R1B,
        EXPECTED_B - {"r1b_handoff.json"},
    )
    record(checks, failures, "r1a_output_hashes", a_outputs_ok)
    record(checks, failures, "r1b_output_hashes", b_outputs_ok)

    for prefix, handoff in (("r1a", a_handoff), ("r1b", b_handoff)):
        input_verification = handoff.get("input_verification")
        record(
            checks,
            failures,
            f"{prefix}_input_verification",
            isinstance(input_verification, dict)
            and input_verification.get("verdict") == "PASS"
            and 17
            in {
                input_verification.get("manifest_entries_matched"),
                input_verification.get("listed_inputs_hash_matched"),
            },
        )
        record(checks, failures, f"{prefix}_model", handoff.get("model") == "gpt-5.6-sol" and handoff.get("reasoning") == "xhigh")
        record(checks, failures, f"{prefix}_status", handoff.get("status") == "COMPLETE_FAIL_CLOSED")
        record(checks, failures, f"{prefix}_truth_state", truth_state_is_closed(handoff.get("truth_state")))
        record(checks, failures, f"{prefix}_scope_guards", scope_guards_are_closed(handoff.get("scope_guards")))

    expected_counts = {
        "READY_FOR_E4_R1C_CONSIDERATION": 0,
        "PENDING_EVIDENCE": 7,
        "REJECTED": 6,
        "total": 13,
    }
    record(
        checks,
        failures,
        "r1a_verdict",
        a_handoff.get("verdict") == "R1A_COMPLETE_WITH_UNRESOLVED_EVIDENCE"
        and a_handoff.get("fail_closed") is True
        and a_delta.get("fail_closed_verdict") == "R1A_COMPLETE_WITH_UNRESOLVED_EVIDENCE",
    )
    record(
        checks,
        failures,
        "r1a_candidate_counts",
        a_handoff.get("candidate_status_counts") == expected_counts
        and a_delta.get("proposed_status_counts") == expected_counts
        and isinstance(a_delta.get("candidate_rows"), list)
        and len(a_delta["candidate_rows"]) == 13
        and isinstance(a_delta.get("prohibited_join_replay"), list)
        and len(a_delta["prohibited_join_replay"]) == 5,
    )
    minimum = a_delta.get("minimum_defensible_official_reproduction")
    record(
        checks,
        failures,
        "r1a_no_ready_selection",
        isinstance(minimum, dict)
        and minimum.get("selection_status") == "NO_READY_ROW"
        and minimum.get("priority_is_selection") is False
        and minimum.get("priority_is_execution_authority") is False,
    )
    record(checks, failures, "r1a_delta_truth_state", truth_state_is_closed(a_delta.get("truth_state")))

    corrections = a_sources.get("corrections")
    correction_index = {
        row.get("binding_id"): row
        for row in corrections
        if isinstance(corrections, list) and isinstance(row, dict)
    } if isinstance(corrections, list) else {}
    simgcl = correction_index.get("R1A-BIND-SIMGCL-PAPER-001")
    spec = correction_index.get("R1A-BIND-V5-SPEC-001")
    record(
        checks,
        failures,
        "r1a_simgcl_correction",
        isinstance(simgcl, dict)
        and isinstance(simgcl.get("old_value"), dict)
        and simgcl["old_value"].get("url") == "https://arxiv.org/abs/2207.09037"
        and isinstance(simgcl.get("proposed_value"), dict)
        and simgcl["proposed_value"].get("url") == "https://arxiv.org/abs/2112.08679"
        and simgcl.get("readiness_promoted") is False
        and simgcl.get("execution_authorized") is False,
    )
    record(
        checks,
        failures,
        "r1a_v5_spec_correction",
        isinstance(spec, dict)
        and isinstance(spec.get("proposed_value"), dict)
        and spec["proposed_value"].get("path") == V5_SPEC_PATH
        and spec["proposed_value"].get("canonical_lf_sha256") == V5_SPEC_SHA
        and spec.get("readiness_promoted") is False
        and spec.get("execution_authorized") is False,
    )
    a_findings = a_handoff.get("finding_dispositions")
    record(
        checks,
        failures,
        "r1a_owned_findings",
        isinstance(a_findings, list)
        and {row.get("finding_id") for row in a_findings if isinstance(row, dict)}
        == {"E5-F001", "E5-F002"},
    )

    commands = b_packet.get("commands")
    record(
        checks,
        failures,
        "r1b_packet_root",
        b_packet.get("packet_state") == "DRAFT_BLOCKED_NON_EXECUTABLE_PROPOSAL"
        and b_packet.get("executable") is False
        and b_packet.get("central_replacement_packet") is False
        and b_packet.get("candidate_selected") is False
        and b_packet.get("user_confirmation_required") is True
        and b_packet.get("confirmed") is False
        and b_packet.get("execution_authorized") is False
        and b_packet.get("retry_policy") == "NO_AUTO_RETRY"
        and b_packet.get("automatic_retry") is False
        and b_packet.get("command_count") == 10,
    )
    record(
        checks,
        failures,
        "r1b_ten_null_commands",
        isinstance(commands, list)
        and [row.get("replaces_command_id") for row in commands if isinstance(row, dict)]
        == EXPECTED_COMMAND_IDS
        and [row.get("command_id") for row in commands if isinstance(row, dict)]
        == EXPECTED_REPLACEMENT_COMMAND_IDS
        and [row.get("order") for row in commands if isinstance(row, dict)]
        == list(range(0, 100, 10))
        and all(
            isinstance(row, dict)
            and row.get("command") is None
            and row.get("command_state") == "NULL_BLOCKING_NOT_MATERIALIZED"
            and row.get("user_confirmation_required") is True
            and row.get("confirmed") is False
            and row.get("execution_authorized") is False
            and row.get("retry_policy") == "NO_AUTO_RETRY"
            for row in commands
        ),
    )
    record(checks, failures, "r1b_packet_truth_state", truth_state_is_closed(b_packet))
    prerequisites = b_packet.get("blocking_prerequisites")
    record(
        checks,
        failures,
        "r1b_blocking_prerequisites",
        isinstance(prerequisites, list)
        and len(prerequisites) == 15
        and b_handoff.get("blocking_prerequisites")
        == {
            "required": 15,
            "resolved": 0,
            "unresolved": 15,
            "unknown_values_remain_null": True,
            "ids": [row.get("prerequisite_id") for row in prerequisites if isinstance(row, dict)],
        },
    )
    schemas = b_receipts.get("schemas")
    mappings = b_receipts.get("receipt_file_mapping")
    record(
        checks,
        failures,
        "r1b_receipt_bundle",
        isinstance(schemas, dict)
        and len(schemas) == 7
        and b_receipts.get("receipt_schema_count") == 7
        and isinstance(mappings, list)
        and len(mappings) == 10
        and b_receipts.get("command_receipt_mapping_count") == 10
        and b_receipts.get("execution_authorized") is False
        and b_receipts.get("confirmed") is False
        and b_receipts.get("lane_verdict") == "R1B_COMPLETE_WITH_BLOCKING_PREREQUISITES",
    )
    record(
        checks,
        failures,
        "r1b_verdict",
        b_handoff.get("verdict") == "R1B_COMPLETE_WITH_BLOCKING_PREREQUISITES"
        and b_handoff.get("fail_closed") is True
        and b_packet.get("lane_verdict") == "R1B_COMPLETE_WITH_BLOCKING_PREREQUISITES",
    )
    b_findings = b_handoff.get("finding_dispositions")
    record(
        checks,
        failures,
        "r1b_owned_findings",
        isinstance(b_findings, list)
        and {row.get("finding_id") for row in b_findings if isinstance(row, dict)}
        == {"E5-F003", "E5-F004"},
    )

    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-r1-lanes-validation-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_BOTH_LANES_READY_FOR_E4_R1C_SYNTHESIS"
            if not failures
            else "FAIL_E4_R1_LANE_INTAKE"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {"expected": 17, "matched": input_matches},
        "r1a": {
            "source_commit": "48d0bbd031f4850750c9659de8244408ac6eb4e0",
            "central_tip_after_import": "48d0bbd031f4850750c9659de8244408ac6eb4e0",
            "handoff_canonical_lf_sha256": canonical_lf_sha256(R1A / "r1a_handoff.json"),
            "verdict": a_handoff.get("verdict"),
            "candidate_status_counts": a_handoff.get("candidate_status_counts"),
            "output_checks": a_output_checks,
        },
        "r1b": {
            "source_commit": "196e6c0ad295c282127dfb7fbd0d0a22ede33c39",
            "central_tip_after_import": "de91bdd",
            "handoff_canonical_lf_sha256": canonical_lf_sha256(R1B / "r1b_handoff.json"),
            "verdict": b_handoff.get("verdict"),
            "blocking_prerequisites": b_handoff.get("blocking_prerequisites"),
            "output_checks": b_output_checks,
        },
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
            "confirmed": False,
        },
        "next_gate": "E4_R1C_CENTRAL_SYNTHESIS_AND_FREEZE",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
