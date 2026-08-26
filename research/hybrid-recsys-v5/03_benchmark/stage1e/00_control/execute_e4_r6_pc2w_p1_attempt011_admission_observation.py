#!/usr/bin/env python3
"""Dormant one-shot adapter with strict stage-bound gate receipts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
import e4_r6_pc2w_p1_gate_receipt_binding as receipt_binding
import execute_e4_r6_pc2w_p1_attempt010_admission_observation as previous


legacy = previous.previous.legacy
CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt011_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt011_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt011_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt011_static_packet.py"
PACKET_PARENT = "da18aa102567dcfef7296fafa223bcaef065e934"
PACKET_RELATIVES = {
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
}
PACKET_ROSTER = tuple(
    path.as_posix()
    for path in (
        CONTRACT_RELATIVE,
        AUTHORIZATION_RELATIVE,
        RUNNER_RELATIVE,
        VALIDATOR_RELATIVE,
    )
)
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_at/"
    "E4_R6PC2W_P1_attempt011_admission_observation"
)
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT011_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt011-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT011_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt011-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT011_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT011_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT011_CURRENT_HOST_NOT_ADMISSIBLE"
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03", "P04", "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]
RETAINED_P04_CALL = 'invoke("P04", "POWERSHELL_MODULE_PREFLIGHT", 60)'

GATE_RECEIPT_SPEC = receipt_binding.GateReceiptSpec(
    stage_id="E4-R6-PC2W-P1-ATTEMPT011",
    packet_files=PACKET_ROSTER,
    central_schema=CENTRAL_RECEIPT_SCHEMA,
    central_verdict=CENTRAL_RECEIPT_VERDICT,
    central_validator_verdict="READY_FOR_CENTRAL_STATIC_VALIDATION",
    fresh_audit_schema=AUDIT_RECEIPT_SCHEMA,
    fresh_audit_verdict=AUDIT_RECEIPT_VERDICT,
)
FROZEN_SUPPORT_SHA256 = {
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_gate_receipt_binding.py":
        "8a1ea9f854fbe81c4873b326db4a1a82b31c6557c4efb92c0e3332ecdddaa526",
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_gate_receipt_binding_contract.json":
        "784cd9639ae43f11bc4977155c6528c8f0f304ba9d4bcc4a394b1c93916f0e0b",
    CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py":
        "41e1c30a784368b713532899a86feec3fe538a1b85388621f7431a8c9eaa8c51",
}

_ORIGINAL_ATTEMPT010_VALIDATE_FROZEN = previous._validate_frozen_upstream


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _adapted_document(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(value)
    schemas = {
        "command_receipts.json": "stage1e-e4-r6-pc2w-p1-attempt011-command-receipts-1.0",
        "admission_observation.json": "stage1e-e4-r6-pc2w-p1-attempt011-admission-observation-1.0",
        "execution_receipt.json": "stage1e-e4-r6-pc2w-p1-attempt011-execution-receipt-1.0",
        "handoff.json": "stage1e-e4-r6-pc2w-p1-attempt011-handoff-1.0",
    }
    if path.name in schemas:
        document["schema_version"] = schemas[path.name]
        document["stage_id"] = GATE_RECEIPT_SPEC.stage_id
    return document


def _runtime_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get(
        "experiment_intake_declaration"
    )
    if not isinstance(intake, dict):
        raise RuntimeError("authorization intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": (
            "stage1e_e4_r6_pc2w_p1_attempt011_admission_observation_execution_v1"
        ),
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt011_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt011_execution_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_gate_receipt_binding_contract_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": copy.deepcopy(intake),
    }


def _validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    result = _ORIGINAL_ATTEMPT010_VALIDATE_FROZEN(repo_root, head)
    support_facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_SUPPORT_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        blob_bytes, blob_sha256 = legacy.git_blob_fact(repo_root, head, relative)
        if blob_sha256 != expected_sha256:
            raise RuntimeError("frozen gate-receipt support Git blob hash mismatch")
        if legacy.canonical_lf_fact(repo_root / relative) != (
            blob_bytes,
            blob_sha256,
        ):
            raise RuntimeError("frozen gate-receipt support checkout drift")
        support_facts.append(
            {
                "path": relative.as_posix(),
                "git_blob_bytes": blob_bytes,
                "git_blob_sha256": blob_sha256,
            }
        )
    result["attempt011_gate_receipt_support_artifact_count"] = len(support_facts)
    result["attempt011_gate_receipt_support_artifacts"] = support_facts
    binding_record = result.get("attempt010_process_command_binding")
    if isinstance(binding_record, dict):
        binding_record["schema_version"] = (
            "stage1e-attempt011-python-command-binding-1.0"
        )
    return result


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
        raise RuntimeError("read-only Git blob lookup failed")
    return completed.stdout


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


def configure_attempt011_runner() -> None:
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
    previous.configure_attempt010_runner()
    legacy.EXPECTED_COMMAND_IDS = EXPECTED_COMMAND_IDS
    legacy.validate_gate_receipts = _validate_bound_gate_receipts


def main() -> int:
    configure_attempt011_runner()
    expected_normalized = [
        str(legacy.PYTHON.resolve()),
        str((Path.cwd().resolve() / RUNNER_RELATIVE).resolve()),
        *sys.argv[1:],
    ]
    original = list(getattr(sys, "orig_argv", []))
    command_binding = previous.command_interface.bind_exact_python_script_argv(
        original, expected_normalized
    )
    previous._COMMAND_BINDING = command_binding
    sys.orig_argv = list(command_binding.normalized_argv)
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
        print(
            json.dumps(
                {
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
                },
                indent=2,
                allow_nan=False,
            )
        )
        raise SystemExit(2)
