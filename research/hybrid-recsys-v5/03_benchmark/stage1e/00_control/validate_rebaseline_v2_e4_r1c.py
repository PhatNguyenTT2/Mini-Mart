"""Fail-closed central validator for Stage 1E E4-R1C Wave E synthesis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
WAVE_E = CONTROL.parent / "rebaseline_v2" / "wave_e" / "E4_R1C_reproduction_adaptation"

CONTRACT_SHA = "192a49d4afec4e52d52515879ec28e4e58f8acf4f9038afe9ff0a3d06d7765c9"
MANIFEST_SHA = "3f1a1c6eb350120674a57dc6df846c58f456d61df30e0da27ebb7aea17923d87"
LANE_RECEIPT_SHA = "d790eaf2503f9dba8dcff231b894ad8a50cefb98ae96d7f7ef9b363e0231edf2"
R1A_SOURCE_SHA = "ce1ae9194e24dc1c35ce736aec039a3564674912ef0a0452ac2a045d3e64214b"
R1A_CANDIDATE_SHA = "3d53f30e284edaefc02737fa7a7cad7326fb53cf2f3db0b218a93f3c1137fb32"
R1B_CONTROL_SHA = "6d9d00114fe1da84d8f6df312906ad82da408800523a66cc60423f38585dcdf7"
R1B_COMMAND_SHA = "40b8a7e753c896cd19ec38c10764e8b073f158050e7452af3549292b85c5c41b"
R1B_SCHEMA_SHA = "0d462872340130eeeadbf54eb41301c6e6675c2e7006384a85c36960ccf8fb32"
V5_SPEC_PATH = "backend/docs/chatbot/seed-product/benchmark-spec-v5.json"
V5_SPEC_SHA = "acef1c62cc2a9a3ae04fdf2f4b2fb24b3eb8d2634f15e085fbe1878be8dc166d"
VERDICT = "COMPLETE_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT"
STOCHASTICITY_DECLARATION = (
    "LLM outputs are not byte-reproducible. This lockfile documents "
    "configuration, not a deterministic replay guarantee."
)

EXPECTED_FILES = {
    "selected_reference_bundle.json",
    "reproduction_execution_plan.md",
    "v5_adapter_and_evaluator_contract.md",
    "cross_dataset_reporting_contract.md",
    "exact_command_confirmation_packet.json",
    "e4_r1c_handoff.json",
}
EXPECTED_NON_HANDOFF = EXPECTED_FILES - {"e4_r1c_handoff.json"}
EXPECTED_COMMAND_IDS = [
    "E4-R1C-000-PREFLIGHT",
    "E4-R1C-010-SOURCE-ACQUIRE",
    "E4-R1C-020-SOURCE-CHECKOUT",
    "E4-R1C-030-SOURCE-VERIFY",
    "E4-R1C-040-ENVIRONMENT-CREATE",
    "E4-R1C-050-DEPENDENCY-INSTALL",
    "E4-R1C-060-PREPROCESS",
    "E4-R1C-070-RUN",
    "E4-R1C-080-EVALUATE",
    "E4-R1C-090-FINALIZE",
]
EXPECTED_PREREQUISITES = [
    "P01_CANDIDATE_SELECTION",
    "P02_CONTROLLER_IDENTITY",
    "P03_RESOURCE_WRAPPER_IDENTITY",
    "P04_SOURCE_IDENTITY",
    "P05_SOURCE_RIGHTS_SUBMODULE_TREE_LOCK",
    "P06_INTERPRETER_ENVIRONMENT_LOCK",
    "P07_DEPENDENCY_WHEEL_LOCK",
    "P08_DATASET_PROVIDER_RELEASE_RIGHTS_RAW_HASHES",
    "P09_PREPROCESSING_LINEAGE_ARGV_SCHEMA_COUNTS",
    "P10_MODEL_CONFIG_SEED_CHECKPOINT_SAMPLER_CANDIDATE_TIE",
    "P11_EVALUATOR_ADAPTER_METRIC_IDENTITY",
    "P12_EXACT_LOG_OUTPUT_INVENTORIES",
    "P13_NEW_FROZEN_CENTRAL_PACKET",
    "P14_FUTURE_INDEPENDENT_E5_R1_PASS",
    "P15_EXPLICIT_USER_CONFIRMATION_AND_AUTHORITY_RECEIPT",
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

    present = {path.name for path in WAVE_E.iterdir() if path.is_file()} if WAVE_E.is_dir() else set()
    record(checks, failures, "exact_six_file_write_set", present == EXPECTED_FILES)
    if present != EXPECTED_FILES:
        print(json.dumps({"passed": False, "failures": failures, "present": sorted(present)}, indent=2))
        return 1

    try:
        manifest = load_json(CONTROL / "e4_r1c_frozen_input_manifest.json")
        lane_receipt = load_json(CONTROL / "rebaseline_v2_e4_r1_lanes_validation_receipt.json")
        selected = load_json(WAVE_E / "selected_reference_bundle.json")
        packet = load_json(WAVE_E / "exact_command_confirmation_packet.json")
        handoff = load_json(WAVE_E / "e4_r1c_handoff.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "invalid_json": str(exc)}, indent=2))
        return 1

    record(checks, failures, "contract_hash", canonical_lf_sha256(CONTROL / "e4_r1c_central_synthesis_contract.md") == CONTRACT_SHA)
    record(checks, failures, "manifest_self_hash", canonical_lf_sha256(CONTROL / "e4_r1c_frozen_input_manifest.json") == MANIFEST_SHA)
    record(checks, failures, "lane_receipt_hash", canonical_lf_sha256(CONTROL / "rebaseline_v2_e4_r1_lanes_validation_receipt.json") == LANE_RECEIPT_SHA)
    record(checks, failures, "lane_receipt_gate", lane_receipt.get("verdict") == "PASS_BOTH_LANES_READY_FOR_E4_R1C_SYNTHESIS" and lane_receipt.get("passed") is True)

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
                    and hashlib.sha256(observed).hexdigest() == row.get("canonical_lf_sha256")
                ):
                    input_matches += 1
            except (OSError, UnicodeError):
                pass
    record(checks, failures, "frozen_inputs_20_of_20", isinstance(input_rows, list) and len(input_rows) == 20 and input_matches == 20)

    output_rows = handoff.get("outputs")
    output_index = {
        Path(str(row.get("path", ""))).name: row
        for row in output_rows
        if isinstance(output_rows, list) and isinstance(row, dict)
    } if isinstance(output_rows, list) else {}
    output_details: dict[str, object] = {}
    output_hashes_ok = set(output_index) == EXPECTED_NON_HANDOFF
    for name in sorted(EXPECTED_NON_HANDOFF):
        observed = canonical_lf_bytes(WAVE_E / name)
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
    record(checks, failures, "five_output_hashes", output_hashes_ok)

    passport = handoff.get("material_passport")
    repro = passport.get("repro_lock") if isinstance(passport, dict) else None
    model = repro.get("model") if isinstance(repro, dict) else None
    record(
        checks,
        failures,
        "material_passport_and_repro_lock",
        isinstance(passport, dict)
        and passport.get("verification_status") == "UNVERIFIED"
        and isinstance(repro, dict)
        and repro.get("stochasticity_declaration") == STOCHASTICITY_DECLARATION
        and isinstance(model, dict)
        and model.get("id") == "gpt-5.6-sol"
        and model.get("reasoning") == "high"
        and model.get("weight_stable") is False
        and isinstance(repro.get("materials"), dict)
        and repro["materials"].get("count") == 20,
    )
    record(checks, failures, "handoff_model", handoff.get("model") == "gpt-5.6-sol" and handoff.get("reasoning") == "high")
    record(checks, failures, "handoff_status", handoff.get("status") == "COMPLETE_FAIL_CLOSED" and handoff.get("verdict") == VERDICT and handoff.get("fail_closed") is True)
    record(checks, failures, "handoff_truth_state", truth_state_is_closed(handoff.get("truth_state")))
    record(checks, failures, "handoff_scope_guards", scope_guards_are_closed(handoff.get("scope_guards")))

    corrected = selected.get("corrected_sources")
    simgcl = corrected.get("S_SIM_GCL_PAPER") if isinstance(corrected, dict) else None
    rejected = corrected.get("REJECTED_SIMGCL_SOURCE") if isinstance(corrected, dict) else None
    spec = corrected.get("V5_BENCHMARK_SPEC") if isinstance(corrected, dict) else None
    record(
        checks,
        failures,
        "simgcl_source_correction",
        isinstance(simgcl, dict)
        and simgcl.get("url") == "https://arxiv.org/abs/2112.08679"
        and simgcl.get("immutable_revision") == "arXiv:2112.08679v4"
        and isinstance(rejected, dict)
        and rejected.get("url") == "https://arxiv.org/abs/2207.09037"
        and rejected.get("may_support_simgcl_claim") is False,
    )
    record(
        checks,
        failures,
        "v5_spec_correction",
        isinstance(spec, dict)
        and spec.get("path") == V5_SPEC_PATH
        and spec.get("canonical_lf_sha256") == V5_SPEC_SHA
        and spec.get("path_exists") is True
        and isinstance(packet.get("evaluation_binding"), dict)
        and packet["evaluation_binding"].get("frozen_v5_spec_path") == V5_SPEC_PATH
        and packet["evaluation_binding"].get("frozen_v5_spec_canonical_lf_sha256") == V5_SPEC_SHA,
    )

    bindings = selected.get("authoritative_bindings")
    source_binding = bindings.get("source_corrections") if isinstance(bindings, dict) else None
    candidate_binding = bindings.get("candidate_registry") if isinstance(bindings, dict) else None
    record(checks, failures, "r1a_bindings", isinstance(source_binding, dict) and source_binding.get("canonical_lf_sha256") == R1A_SOURCE_SHA and isinstance(candidate_binding, dict) and candidate_binding.get("canonical_lf_sha256") == R1A_CANDIDATE_SHA)

    candidate_rows = selected.get("candidate_rows")
    statuses = [row.get("status") for row in candidate_rows if isinstance(row, dict)] if isinstance(candidate_rows, list) else []
    prohibited = [row for row in candidate_rows if isinstance(row, dict) and row.get("prohibited_join") is True] if isinstance(candidate_rows, list) else []
    counts = selected.get("status_counts")
    minimum = selected.get("minimum_defensible_official_reproduction")
    record(
        checks,
        failures,
        "candidate_registry_13_rows",
        isinstance(candidate_rows, list)
        and len(candidate_rows) == 13
        and statuses.count("PENDING_EVIDENCE") == 7
        and statuses.count("REJECTED") == 6
        and isinstance(counts, dict)
        and counts.get("READY_FOR_E5_R1_AUDIT") == 0
        and counts.get("PENDING_EVIDENCE") == 7
        and counts.get("REJECTED") == 6
        and counts.get("total") == 13
        and all(row.get("selected_for_execution") is False for row in candidate_rows if isinstance(row, dict)),
    )
    record(checks, failures, "five_prohibited_joins", len(prohibited) == 5 and all(row.get("status") == "REJECTED" for row in prohibited))
    record(checks, failures, "no_candidate_selected", isinstance(minimum, dict) and minimum.get("selection_status") == "NO_READY_ROW" and minimum.get("selected_row_id") is None and minimum.get("priority_is_selection") is False and minimum.get("priority_is_execution_authority") is False)

    central = packet.get("central_bindings")
    control = central.get("mechanical_control_spec") if isinstance(central, dict) else None
    command_design = central.get("command_design_source") if isinstance(central, dict) else None
    schemas = central.get("receipt_schema_bundle") if isinstance(central, dict) else None
    record(
        checks,
        failures,
        "r1b_control_schema_bindings",
        isinstance(control, dict)
        and control.get("canonical_lf_sha256") == R1B_CONTROL_SHA
        and isinstance(command_design, dict)
        and command_design.get("canonical_lf_sha256") == R1B_COMMAND_SHA
        and isinstance(schemas, dict)
        and schemas.get("canonical_lf_sha256") == R1B_SCHEMA_SHA
        and schemas.get("closed_schema_count") == 7
        and schemas.get("command_receipt_mapping_count") == 10,
    )

    commands = packet.get("commands")
    record(
        checks,
        failures,
        "packet_root_fail_closed",
        packet.get("packet_state") == "CENTRAL_REPLACEMENT_FROZEN_FAIL_CLOSED_NON_EXECUTABLE"
        and packet.get("central_replacement_packet") is True
        and packet.get("executable") is False
        and packet.get("candidate_selected") is False
        and packet.get("candidate_row_id") is None
        and packet.get("user_confirmation_required") is True
        and packet.get("confirmed") is False
        and packet.get("execution_authorized") is False
        and packet.get("retry_policy") == "NO_AUTO_RETRY"
        and packet.get("automatic_retry") is False
        and packet.get("resume_allowed") is False
        and packet.get("packet_verdict") == VERDICT,
    )
    record(
        checks,
        failures,
        "ten_null_command_records",
        isinstance(commands, list)
        and len(commands) == 10
        and [row.get("order") for row in commands if isinstance(row, dict)] == list(range(0, 100, 10))
        and [row.get("command_id") for row in commands if isinstance(row, dict)] == EXPECTED_COMMAND_IDS
        and all(
            isinstance(row, dict)
            and row.get("shell") is None
            and row.get("working_directory") is None
            and row.get("command") is None
            and row.get("command_state") == "NULL_BLOCKING_NOT_MATERIALIZED"
            and row.get("test_access_allowed") is False
            and row.get("retry_policy") == "NO_AUTO_RETRY"
            and row.get("user_confirmation_required") is True
            and row.get("confirmed") is False
            and row.get("execution_authorized") is False
            for row in commands
        ),
    )

    prerequisites = packet.get("blocking_prerequisites")
    prereq_counts = packet.get("prerequisite_counts")
    resolved = [row for row in prerequisites if isinstance(row, dict) and row.get("resolved") is True] if isinstance(prerequisites, list) else []
    unresolved = [row for row in prerequisites if isinstance(row, dict) and row.get("resolved") is False] if isinstance(prerequisites, list) else []
    record(
        checks,
        failures,
        "prerequisite_ledger_15_one_resolved",
        isinstance(prerequisites, list)
        and [row.get("prerequisite_id") for row in prerequisites if isinstance(row, dict)] == EXPECTED_PREREQUISITES
        and len(resolved) == 1
        and resolved[0].get("prerequisite_id") == "P13_NEW_FROZEN_CENTRAL_PACKET"
        and len(unresolved) == 14
        and all(row.get("value") is None for row in unresolved)
        and isinstance(prereq_counts, dict)
        and prereq_counts == {
            "required": 15,
            "resolved": 1,
            "unresolved": 14,
            "only_resolved_id": "P13_NEW_FROZEN_CENTRAL_PACKET",
        },
    )
    record(checks, failures, "packet_truth_state", truth_state_is_closed(packet.get("truth_state")))
    record(checks, failures, "packet_scope_guards", scope_guards_are_closed(packet.get("scope_guards")))

    ownership = packet.get("phase_ownership")
    record(
        checks,
        failures,
        "phase_ownership_corrected",
        isinstance(ownership, dict)
        and "audit only" in str(ownership.get("FUTURE_E5_R1", "")).lower()
        and "Resolve candidate/material identities" in str(ownership.get("FUTURE_E4_REMEDIATION_OWNER", ""))
        and packet.get("materialization_policy", {}).get("future_e5_r1_may_materialize") is False,
    )

    finding_rows = handoff.get("finding_dispositions")
    record(
        checks,
        failures,
        "all_four_findings_disposed",
        isinstance(finding_rows, list)
        and {row.get("finding_id") for row in finding_rows if isinstance(row, dict)} == {"E5-F001", "E5-F002", "E5-F003", "E5-F004"},
    )

    adapter_text = (WAVE_E / "v5_adapter_and_evaluator_contract.md").read_text(encoding="utf-8")
    reporting_text = (WAVE_E / "cross_dataset_reporting_contract.md").read_text(encoding="utf-8")
    plan_text = (WAVE_E / "reproduction_execution_plan.md").read_text(encoding="utf-8")
    record(checks, failures, "adapter_contract_correct_path_hash", V5_SPEC_PATH in adapter_text and V5_SPEC_SHA in adapter_text and "future E5-R1 task is independent audit-only" in adapter_text)
    record(checks, failures, "cross_dataset_guard", "may be compared as a direct performance contrast only when this complete key is equal" in reporting_text and "INVALID_FOR_PAPER" in reporting_text)
    record(checks, failures, "execution_plan_denial", "10/10 command strings are null" in plan_text and "14 unresolved" in plan_text and "does not authorize" in plan_text)

    handoff_hash = canonical_lf_sha256(WAVE_E / "e4_r1c_handoff.json")
    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-r1c-validation-1.0",
        "passed": not failures,
        "verdict": "PASS_E4_R1C_CORRECTED_FAIL_CLOSED_READY_FOR_E5_R1_AUDIT" if not failures else "FAIL_E4_R1C_CENTRAL_VALIDATION",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 20,
            "matched": input_matches,
            "manifest_canonical_lf_sha256": canonical_lf_sha256(CONTROL / "e4_r1c_frozen_input_manifest.json"),
            "contract_canonical_lf_sha256": canonical_lf_sha256(CONTROL / "e4_r1c_central_synthesis_contract.md"),
        },
        "outputs": {
            "expected_files": 6,
            "present_files": len(present),
            "non_handoff_output_checks": output_details,
            "handoff_canonical_lf_sha256": handoff_hash,
        },
        "candidate_status_counts": handoff.get("candidate_status_counts"),
        "command_packet": handoff.get("command_packet"),
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
            "confirmed": False,
        },
        "next_gate": "FREEZE_E5_R1_INPUTS_AND_DISPATCH_FRESH_INDEPENDENT_SOL_XHIGH_AUDIT",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
