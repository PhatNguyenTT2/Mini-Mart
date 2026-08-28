#!/usr/bin/env python3
"""Dormant Attempt-013 adapter installing two adjudicated identity seams."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.dont_write_bytecode = True
import e4_r6_pc2w_p1_attempt010_command_interface as command_interface
import e4_r6_pc2w_p1_attempt013_pre_runtime_authority as authority
import e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility as compatibility
import e4_r6_pc2w_p1_gate_receipt_binding as receipt_binding
import execute_e4_r6_pc2w_p1_attempt012_admission_observation as previous


legacy = previous.legacy
CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNTIME_HELPER_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
RUNTIME_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json"
RUNTIME_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
AUTHORITY_HELPER_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py"
AUTHORITY_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json"
AUTHORITY_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_execution_authorization.json"
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt013_admission_observation.py"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt013_static_packet.py"
PACKET_PARENT = "ce6377c351625ed7e029f2883520583ca97fc2b8"
PACKET_PATHS = (
    RUNTIME_HELPER_RELATIVE,
    RUNTIME_CONTRACT_RELATIVE,
    RUNTIME_TEST_RELATIVE,
    AUTHORITY_HELPER_RELATIVE,
    AUTHORITY_CONTRACT_RELATIVE,
    AUTHORITY_TEST_RELATIVE,
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
)
PACKET_RELATIVES = set(PACKET_PATHS)
PACKET_ROSTER = tuple(path.as_posix() for path in PACKET_PATHS)
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/"
    "E4_R6PC2W_P1_attempt013_admission_observation"
)
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT013_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_PATH = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_central_static_validation_receipt.json"
)
AUDIT_RECEIPT_PATH = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_fresh_independent_audit_receipt.json"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT013_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT013_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT013_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT013_CURRENT_HOST_NOT_ADMISSIBLE"
AUTHORITY_CONTRACT_BYTES = 4526
AUTHORITY_CONTRACT_SHA256 = (
    "1cb5d8130420ae543d9f63b4d4cd0b9d16c7571577a5ad506f0217b2ebd530f0"
)
RUNTIME_CONTRACT_BYTES = 4121
RUNTIME_CONTRACT_SHA256 = (
    "ed7d4323e7287643e0372e11cc1a2e6f5b5af73f4ec20fc0d0758dd12e648784"
)
FROZEN_R0_SHA256 = {
    RUNTIME_CONTRACT_RELATIVE: RUNTIME_CONTRACT_SHA256,
    RUNTIME_TEST_RELATIVE:
        "36b0e95a7b87a98325da6debfb345cb5a1df96ec672e6f1f3bb35db6b79fc21b",
    AUTHORITY_CONTRACT_RELATIVE: AUTHORITY_CONTRACT_SHA256,
    AUTHORITY_TEST_RELATIVE:
        "9c372dcd8a4cb4f87dab444a55739966936a930f098999487fd86d6f65a8c437",
}

GATE_RECEIPT_SPEC = receipt_binding.GateReceiptSpec(
    stage_id="E4-R6-PC2W-P1-ATTEMPT013",
    packet_files=PACKET_ROSTER,
    central_schema=CENTRAL_RECEIPT_SCHEMA,
    central_verdict=CENTRAL_RECEIPT_VERDICT,
    central_validator_verdict="IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
    fresh_audit_schema=AUDIT_RECEIPT_SCHEMA,
    fresh_audit_verdict=AUDIT_RECEIPT_VERDICT,
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_git_blob(repo_root: Path, revision: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative}"],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("ATTEMPT013_GIT_BLOB_UNRESOLVED")
    return completed.stdout


def _bound_document(repo_root: Path, head: str, relative: Path) -> dict[str, Any]:
    return authority.strict_json_object(
        _read_git_blob(repo_root, head, relative.as_posix())
    )


def _validate_contract_owners(
    repo_root: Path, head: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    authority_raw = _read_git_blob(
        repo_root, head, AUTHORITY_CONTRACT_RELATIVE.as_posix()
    )
    runtime_raw = _read_git_blob(
        repo_root, head, RUNTIME_CONTRACT_RELATIVE.as_posix()
    )
    if (
        len(authority_raw) != AUTHORITY_CONTRACT_BYTES
        or _sha256(authority_raw) != AUTHORITY_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_AUTHORITY_OWNER_RAW_BINDING_MISMATCH")
    if (
        len(runtime_raw) != RUNTIME_CONTRACT_BYTES
        or _sha256(runtime_raw) != RUNTIME_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_RUNTIME_OWNER_RAW_BINDING_MISMATCH")
    owner = authority.strict_json_object(authority_raw)
    runtime_owner = authority.strict_json_object(runtime_raw)
    contract = _bound_document(repo_root, head, CONTRACT_RELATIVE)
    authorization = _bound_document(repo_root, head, AUTHORIZATION_RELATIVE)
    expected_authority = {
        "path": AUTHORITY_CONTRACT_RELATIVE.as_posix(),
        "raw_git_blob_bytes": AUTHORITY_CONTRACT_BYTES,
        "raw_git_blob_sha256": AUTHORITY_CONTRACT_SHA256,
    }
    expected_runtime = {
        "path": RUNTIME_CONTRACT_RELATIVE.as_posix(),
        "raw_git_blob_bytes": RUNTIME_CONTRACT_BYTES,
        "raw_git_blob_sha256": RUNTIME_CONTRACT_SHA256,
    }
    for document in (contract, authorization):
        authority_binding = document.get("pre_runtime_authority_binding")
        runtime_binding = document.get("runtime_identity_compatibility_binding")
        if not isinstance(authority_binding, dict) or any(
            authority_binding.get(key) != value
            for key, value in expected_authority.items()
        ):
            raise RuntimeError("ATTEMPT013_AUTHORITY_CONSUMER_BINDING_MISMATCH")
        if not isinstance(runtime_binding, dict) or any(
            runtime_binding.get(key) != value
            for key, value in expected_runtime.items()
        ):
            raise RuntimeError("ATTEMPT013_RUNTIME_CONSUMER_BINDING_MISMATCH")
        if (
            authority_binding.get("restated_authority_values") is not False
            or runtime_binding.get("restated_seam_values") is not False
        ):
            raise RuntimeError("ATTEMPT013_CONSUMER_RESTATED_VALUES")
    return owner, runtime_owner, contract, authorization


def _legacy_model_compatibility_view() -> dict[str, Any]:
    """Non-authoritative shape needed only by the retained legacy predicate."""

    return {
        "requested_model": "gpt-5.6-sol",
        "requested_reasoning_effort": "max",
        "requested_service_tier": "default",
        "requested_display_name": "Sol Max Standard",
        "fresh_audit_requested_model": "gpt-5.6-sol",
        "fresh_audit_requested_reasoning_effort": "xhigh",
        "fast_or_priority_allowed": False,
        "actual_model_reasoning_and_service_tier": "UNOBSERVABLE",
    }


def _adapted_load_json(path: Path) -> dict[str, Any]:
    document = previous.previous.previous._ORIGINAL_LOAD_JSON(path)
    if path.name == CONTRACT_RELATIVE.name:
        document = copy.deepcopy(document)
        document["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-contract-2.0"
        )
        document["model_policy"] = _legacy_model_compatibility_view()
    elif path.name == AUTHORIZATION_RELATIVE.name:
        document = copy.deepcopy(document)
        document["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-execution-authorization-2.0"
        )
        document["user_decision"] = {
            "status": "CONFIRMED",
            "confirmed_scope": "REPAIR_PROBE_PARSER_AND_PREPARE_ATTEMPT008_DORMANT_PACKET",
            "runtime_execution_authorized_now": False,
            "exact_process_command_confirmed_now": False,
        }
        document["model_policy"] = _legacy_model_compatibility_view()
    return document


def _adapted_document(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(value)
    schemas = {
        "command_receipts.json": "stage1e-e4-r6-pc2w-p1-attempt013-command-receipts-1.0",
        "admission_observation.json": "stage1e-e4-r6-pc2w-p1-attempt013-admission-observation-1.0",
        "execution_receipt.json": "stage1e-e4-r6-pc2w-p1-attempt013-execution-receipt-1.0",
        "handoff.json": "stage1e-e4-r6-pc2w-p1-attempt013-handoff-1.0",
    }
    if path.name in schemas:
        document["schema_version"] = schemas[path.name]
        document["stage_id"] = GATE_RECEIPT_SPEC.stage_id
    return document


def _adapted_write_json(path: Path, value: dict[str, Any]) -> None:
    previous.previous.previous._ORIGINAL_WRITE_JSON(
        path, _adapted_document(path, value)
    )


def _runtime_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get(
        "experiment_intake_declaration"
    )
    if not isinstance(intake, dict):
        raise RuntimeError("ATTEMPT013_AUTHORIZATION_INTAKE_MISSING")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": (
            "stage1e_e4_r6_pc2w_p1_attempt013_admission_observation_execution_v1"
        ),
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt013_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_execution_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": copy.deepcopy(intake),
        "experiment_provenance": [],
    }


def _validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    result = previous._validate_frozen_upstream(repo_root, head)
    facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_R0_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        raw = _read_git_blob(repo_root, head, relative.as_posix())
        if _sha256(raw) != expected_sha256:
            raise RuntimeError("ATTEMPT013_FROZEN_R0_HASH_MISMATCH")
        facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": len(raw),
            "git_blob_sha256": expected_sha256,
        })
    result["attempt013_frozen_r0_artifact_count"] = len(facts)
    result["attempt013_frozen_r0_artifacts"] = facts
    result["attempt013_parent_resolution_schema"] = compatibility.PROBE_SCHEMA
    result["attempt013_authority_schema"] = authority.AUTHORITY_SCHEMA
    result["attempt013_model_policy_schema"] = authority.MODEL_POLICY_SCHEMA
    return result


def _validate_bound_gate_receipts(
    repo_root: Path,
    head: str,
    packet_commit: str,
    central_path: Path,
    central_sha256: str,
    audit_path: Path,
    audit_sha256: str,
) -> dict[str, Any]:
    return receipt_binding.validate_bound_gate_receipts(
        repository_root=repo_root,
        execution_head=head,
        packet_commit=packet_commit,
        spec=GATE_RECEIPT_SPEC,
        central_locator=receipt_binding.ReceiptLocator(
            central_path.as_posix(), central_sha256
        ),
        fresh_audit_locator=receipt_binding.ReceiptLocator(
            audit_path.as_posix(), audit_sha256
        ),
        read_git_blob=_read_git_blob,
    )


def _parse_parameters() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--packet-commit", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--central-validation-receipt", required=True)
    parser.add_argument("--central-validation-receipt-sha256", required=True)
    parser.add_argument("--fresh-audit-receipt", required=True)
    parser.add_argument("--fresh-audit-receipt-sha256", required=True)
    parser.add_argument("--execution-confirmation", required=True)
    return parser.parse_args()


def configure_attempt013_runner() -> None:
    previous.configure_attempt012_runner()
    legacy.RUNNER_RELATIVE = RUNNER_RELATIVE
    legacy.CONTRACT_RELATIVE = CONTRACT_RELATIVE
    legacy.AUTHORIZATION_RELATIVE = AUTHORIZATION_RELATIVE
    legacy.VALIDATOR_RELATIVE = VALIDATOR_RELATIVE
    legacy.PACKET_PARENT = PACKET_PARENT
    legacy.PACKET_RELATIVES = PACKET_RELATIVES
    legacy.OUTPUT_RELATIVE = OUTPUT_RELATIVE
    legacy.CONFIRMATION_TOKEN = CONFIRMATION_TOKEN
    legacy.CENTRAL_RECEIPT_SCHEMA = CENTRAL_RECEIPT_SCHEMA
    legacy.CENTRAL_RECEIPT_VERDICT = CENTRAL_RECEIPT_VERDICT
    legacy.AUDIT_RECEIPT_SCHEMA = AUDIT_RECEIPT_SCHEMA
    legacy.AUDIT_RECEIPT_VERDICT = AUDIT_RECEIPT_VERDICT
    legacy.PASS_VERDICT = PASS_VERDICT
    legacy.FAIL_VERDICT = FAIL_VERDICT
    legacy.PROCESS_IDENTITY_QUERY = compatibility.wrap_process_identity_probe(
        compatibility.PROCESS_IDENTITY_QUERY_V3
    )
    legacy.TCP_IDENTITY_QUERY = compatibility.wrap_tcp_identity_probe(
        compatibility.TCP_IDENTITY_QUERY_V3
    )
    legacy.probes_v2 = compatibility
    legacy.parser_v2 = SimpleNamespace(
        IdentityContractError=compatibility.IdentityContractError,
        sanitize_docker_identity=compatibility.sanitize_docker_identity,
    )
    legacy.load_json = _adapted_load_json
    legacy.write_json = _adapted_write_json
    legacy.passport = _runtime_passport
    legacy.validate_frozen_upstream = _validate_frozen_upstream
    legacy.validate_gate_receipts = _validate_bound_gate_receipts


def main() -> int:
    args = _parse_parameters()
    repo_root = Path(args.repo_root).resolve()
    head = legacy.git(repo_root, "rev-parse", "HEAD").casefold()
    git_toplevel = str(
        Path(legacy.git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    )
    owner, _runtime_owner, _contract_document, authorization_document = (
        _validate_contract_owners(repo_root, head)
    )
    receipt_contract = owner.get("receipt_contract")
    if not isinstance(receipt_contract, dict) or (
        receipt_contract.get("central_path") != CENTRAL_RECEIPT_PATH.as_posix()
        or receipt_contract.get("central_schema") != CENTRAL_RECEIPT_SCHEMA
        or receipt_contract.get("central_verdict") != CENTRAL_RECEIPT_VERDICT
        or receipt_contract.get("fresh_audit_path") != AUDIT_RECEIPT_PATH.as_posix()
        or receipt_contract.get("fresh_audit_schema") != AUDIT_RECEIPT_SCHEMA
        or receipt_contract.get("fresh_audit_verdict") != AUDIT_RECEIPT_VERDICT
        or receipt_contract.get("fresh_audit_must_link_central_raw_sha256") is not True
        or receipt_contract.get("attempt012_receipts_accepted") is not False
    ):
        raise RuntimeError("ATTEMPT013_RECEIPT_CONTRACT_MISMATCH")
    owner_contract = owner.get("authority_contract")
    budget = owner_contract.get("attempt_budget") if isinstance(owner_contract, dict) else None
    if not isinstance(budget, dict):
        raise RuntimeError("ATTEMPT013_BUDGET_OWNER_MISSING")
    handoff_contract = authority.AuthorityContract(
        schema_version=authority.AUTHORITY_SCHEMA,
        stage_id=GATE_RECEIPT_SPEC.stage_id,
        execution_root=str(repo_root),
        runner_relative=RUNNER_RELATIVE.as_posix(),
        output_relative=OUTPUT_RELATIVE.as_posix(),
        packet_commit=str(args.packet_commit).casefold(),
        expected_head=str(args.expected_head).casefold(),
        python_executable=str(legacy.PYTHON.resolve()),
        confirmation_token=CONFIRMATION_TOKEN,
        central_receipt=authority.ReceiptLocator(
            str(args.central_validation_receipt),
            str(args.central_validation_receipt_sha256),
        ),
        fresh_audit_receipt=authority.ReceiptLocator(
            str(args.fresh_audit_receipt),
            str(args.fresh_audit_receipt_sha256),
        ),
        model_role="locked_execution",
        attempts_authorized=budget.get("authorized"),
        attempts_consumed=budget.get("consumed"),
        attempts_remaining=budget.get("remaining"),
    )
    observation = authority.RuntimeObservation(
        working_directory=str(Path.cwd().resolve()),
        git_toplevel=git_toplevel,
        head=head,
        model_attestation=authorization_document.get(
            "implementation_model_observation", {}
        ),
    )
    binding = authority.prepare_legacy_handoff(
        handoff_contract, observation, owner.get("model_policy", {})
    )
    if binding.runner_path != Path(__file__).resolve():
        raise RuntimeError("ATTEMPT013_RUNNER_PATH_BINDING_MISMATCH")
    command_binding = command_interface.bind_exact_python_script_argv(
        list(getattr(sys, "orig_argv", [])), binding.expected_process_argv
    )
    configure_attempt013_runner()
    previous.previous.previous._COMMAND_BINDING = command_binding
    original = list(getattr(sys, "orig_argv", []))
    sys.orig_argv = list(command_binding.normalized_argv)
    legacy.EXPECTED_EXECUTION_ROOT = binding.execution_root
    try:
        return legacy.main()
    finally:
        sys.orig_argv = original


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            failure_packet_persisted = legacy.persist_failure_packet(
                type(exc).__name__, str(exc)
            )
        except Exception:
            failure_packet_persisted = False
        print(json.dumps({
            "verdict": "HANDOFF_INCOMPLETE",
            "error_type": type(exc).__name__,
            "error_sha256": _sha256(str(exc).encode("utf-8")),
            "exception_message_persisted": False,
            "failure_packet_persisted": failure_packet_persisted,
            "automatic_retry_count": 0,
            "fallback_count": 0,
            "benchmark_admission_opened": False,
            "result_status": "NOT_RUN",
            "test_set_opened": "NO",
            "accepted_result_rows": 0,
        }, indent=2, allow_nan=False))
        raise SystemExit(2)
