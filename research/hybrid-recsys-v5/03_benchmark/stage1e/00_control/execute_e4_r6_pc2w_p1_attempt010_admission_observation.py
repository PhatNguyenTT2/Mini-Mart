#!/usr/bin/env python3
"""Dormant one-shot Attempt-010 command-interface remediation adapter."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
import e4_r6_pc2w_p1_attempt010_command_interface as command_interface
import execute_e4_r6_pc2w_p1_attempt009_admission_observation as previous


CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt010_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt010_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt010_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt010_static_packet.py"
PACKET_PARENT = "fe9f334e555639ed61781388421e8f8f7c228b46"
PACKET_RELATIVES = {
    RUNNER_RELATIVE,
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    VALIDATOR_RELATIVE,
}
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_as/"
    "E4_R6PC2W_P1_attempt010_admission_observation"
)
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT010_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt010-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT010_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt010-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT010_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT010_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT010_CURRENT_HOST_NOT_ADMISSIBLE"

FROZEN_REMEDIATION_SHA256 = {
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_runtime_compatibility.py":
        "8148e6437af20d4c2b66f774adae102afe83583c7ed2b463340162beb6f342d7",
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_runtime_compatibility_contract.json":
        "6a627d077af4389676ea458265bd8b93a132a606571fd515493dae2e4258b008",
    CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py":
        "d486fbec952a8365828dc132d90fb8fc02cc4cd5811560c7541700054e02b1ea",
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_validation_receipt.json":
        "c1ae7c3daf70041630b9a4c56c0241c5ce5104694a6fa53ee371a3d495ade102",
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_fresh_independent_audit_receipt.json":
        "211de28607daf5e5e5e38a0d016ef6fa3a46d3cea88f566519bbfbc61629b451",
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt010_command_interface.py":
        "970f5b5269c36dc3f2e0e1639db591adbd4623aeb6f97b86e049957dde1a9559",
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt010_command_interface_contract.json":
        "6f31ec175bbd142fb588379ba312e0fa16d66b905340879a4648a65b821ee429",
    CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt010_command_interface.py":
        "faa6b3b5884482996b34303f6efc72a412b4fa3c8ad76c3bb3511b803890911a",
    CONTROL_RELATIVE / "stage1e_legacy_source_cleanup_manifest.json":
        "7c618ef482e260a5b81207a8e6b70793a4afbf288dffa4af57e67fc77df1d45e",
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_pre_runtime_failure_receipt.json":
        "0e74e4f3d594a521fc4cee9b3ee2e2e5131b47246473d452ae55bfe5fddbda12",
}

_COMMAND_BINDING: command_interface.CommandBinding | None = None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _adapted_document(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    document = previous.copy.deepcopy(value)
    schema_by_name = {
        "command_receipts.json": "stage1e-e4-r6-pc2w-p1-attempt010-command-receipts-1.0",
        "admission_observation.json": "stage1e-e4-r6-pc2w-p1-attempt010-admission-observation-1.0",
        "execution_receipt.json": "stage1e-e4-r6-pc2w-p1-attempt010-execution-receipt-1.0",
        "handoff.json": "stage1e-e4-r6-pc2w-p1-attempt010-handoff-1.0",
    }
    if path.name in schema_by_name:
        document["schema_version"] = schema_by_name[path.name]
        document["stage_id"] = "E4-R6-PC2W-P1-ATTEMPT010"
    return document


def _runtime_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt010_admission_observation_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt010_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt010_execution_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt010_command_interface_contract_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def _validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    result = previous._ORIGINAL_VALIDATE_FROZEN(repo_root, head)
    facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_REMEDIATION_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        blob_bytes, blob_sha256 = previous.legacy.git_blob_fact(repo_root, head, relative)
        if blob_sha256 != expected_sha256:
            raise RuntimeError("frozen Attempt-010 remediation Git blob hash mismatch")
        if previous.legacy.canonical_lf_fact(repo_root / relative) != (blob_bytes, blob_sha256):
            raise RuntimeError("frozen Attempt-010 remediation checkout drift")
        facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": blob_bytes,
            "git_blob_sha256": blob_sha256,
        })
    if _COMMAND_BINDING is None:
        raise RuntimeError("Attempt-010 process command binding missing")
    result["attempt010_remediation_artifact_count"] = len(facts)
    result["attempt010_remediation_artifacts"] = facts
    result["attempt010_process_command_binding"] = _COMMAND_BINDING.as_record()
    return result


def configure_attempt010_runner() -> None:
    previous.RUNNER_RELATIVE = RUNNER_RELATIVE
    previous.CONTRACT_RELATIVE = CONTRACT_RELATIVE
    previous.AUTHORIZATION_RELATIVE = AUTHORIZATION_RELATIVE
    previous.VALIDATOR_RELATIVE = VALIDATOR_RELATIVE
    previous.PACKET_PARENT = PACKET_PARENT
    previous.PACKET_RELATIVES = PACKET_RELATIVES
    previous.OUTPUT_RELATIVE = OUTPUT_RELATIVE
    previous.CONFIRMATION_TOKEN = CONFIRMATION_TOKEN
    previous.CENTRAL_RECEIPT_SCHEMA = CENTRAL_RECEIPT_SCHEMA
    previous.CENTRAL_RECEIPT_VERDICT = CENTRAL_RECEIPT_VERDICT
    previous.AUDIT_RECEIPT_SCHEMA = AUDIT_RECEIPT_SCHEMA
    previous.AUDIT_RECEIPT_VERDICT = AUDIT_RECEIPT_VERDICT
    previous.PASS_VERDICT = PASS_VERDICT
    previous.FAIL_VERDICT = FAIL_VERDICT
    previous._adapted_document = _adapted_document
    previous._runtime_passport = _runtime_passport
    previous._validate_frozen_upstream = _validate_frozen_upstream
    previous.configure_legacy_runner()


def main() -> int:
    global _COMMAND_BINDING
    configure_attempt010_runner()
    expected_normalized = [
        str(previous.legacy.PYTHON.resolve()),
        str((Path.cwd().resolve() / RUNNER_RELATIVE).resolve()),
        *sys.argv[1:],
    ]
    original = list(getattr(sys, "orig_argv", []))
    _COMMAND_BINDING = command_interface.bind_exact_python_script_argv(
        original, expected_normalized
    )
    sys.orig_argv = list(_COMMAND_BINDING.normalized_argv)
    try:
        return previous.legacy.main()
    finally:
        sys.orig_argv = original


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            failure_packet_persisted = previous.legacy.persist_failure_packet(
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
