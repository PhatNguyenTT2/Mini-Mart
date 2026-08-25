#!/usr/bin/env python3
"""Dormant one-shot Attempt-009 Docker admission observation adapter.

Packet design, static validation and fresh audit must not invoke this runner.
It may run once only after an exact later user confirmation binds the packet,
execution HEAD and both immutable gate receipts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.dont_write_bytecode = True
import e4_r6_pc2w_p1_attempt009_runtime_compatibility as compatibility
import execute_e4_r6_pc2w_p1_attempt008_admission_observation as legacy


CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt009_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt009_static_packet.py"
PACKET_PARENT = "91466f7dd5a004cbcabfac61815f49c6fcef4606"
PACKET_RELATIVES = {
    RUNNER_RELATIVE,
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    VALIDATOR_RELATIVE,
}
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ar/"
    "E4_R6PC2W_P1_attempt009_admission_observation"
)
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT009_REVISION2_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt009-revision2-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT009_REVISION2_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt009-revision2-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT009_REVISION2_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT009_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT009_CURRENT_HOST_NOT_ADMISSIBLE"
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03", "P04",
    "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]

FROZEN_COMPATIBILITY_SHA256 = {
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
}

_ORIGINAL_LOAD_JSON = legacy.load_json
_ORIGINAL_WRITE_JSON = legacy.write_json
_ORIGINAL_VALIDATE_FROZEN = legacy.validate_frozen_upstream
_ORIGINAL_PRE_START = legacy.pre_start_snapshot


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _adapted_load_json(path: Path) -> dict[str, Any]:
    value = _ORIGINAL_LOAD_JSON(path)
    if path.name == CONTRACT_RELATIVE.name:
        value = copy.deepcopy(value)
        value["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-contract-2.0"
        )
    elif path.name == AUTHORIZATION_RELATIVE.name:
        value = copy.deepcopy(value)
        value["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-execution-authorization-2.0"
        )
        value["user_decision"]["confirmed_scope"] = (
            "REPAIR_PROBE_PARSER_AND_PREPARE_ATTEMPT008_DORMANT_PACKET"
        )
    return value


def _adapted_document(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(value)
    schema_by_name = {
        "command_receipts.json": "stage1e-e4-r6-pc2w-p1-attempt009-command-receipts-1.0",
        "admission_observation.json": "stage1e-e4-r6-pc2w-p1-attempt009-admission-observation-1.0",
        "execution_receipt.json": "stage1e-e4-r6-pc2w-p1-attempt009-execution-receipt-1.0",
        "handoff.json": "stage1e-e4-r6-pc2w-p1-attempt009-handoff-1.0",
    }
    if path.name in schema_by_name:
        document["schema_version"] = schema_by_name[path.name]
        document["stage_id"] = "E4-R6-PC2W-P1-ATTEMPT009"
    return document


def _adapted_write_json(path: Path, value: dict[str, Any]) -> None:
    _ORIGINAL_WRITE_JSON(path, _adapted_document(path, value))


def _runtime_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt009_admission_observation_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt009_admission_observation_contract_v2",
            "stage1e_e4_r6_pc2w_p1_attempt009_execution_authorization_v2",
            "stage1e_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_validation_receipt_v1",
            "stage1e_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_fresh_independent_audit_receipt_v1"
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def _run_command(
    command_id: str, argv: list[str], *, timeout_seconds: int
) -> tuple[dict[str, Any], bytes, bytes]:
    started_at = legacy.utc_now()
    started = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    stdout = b""
    stderr = b""
    exception_type: str | None = None
    exception_sha256: str | None = None
    child_environment = None
    if Path(argv[0]).resolve() == legacy.POWERSHELL.resolve():
        child_environment = compatibility.windows_powershell_child_environment(os.environ)
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
            timeout=timeout_seconds,
            env=child_environment,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        timed_out = True
    except Exception as exc:
        exception_type = type(exc).__name__
        exception_sha256 = _sha256(str(exc).encode("utf-8"))
    return {
        "command_id": command_id,
        "argv": argv,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "started_at": started_at,
        "ended_at": legacy.utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "spawn_exception_type": exception_type,
        "spawn_exception_message_sha256": exception_sha256,
        "stdout_bytes": len(stdout),
        "stdout_sha256": _sha256(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": _sha256(stderr),
    }, stdout, stderr


def _pre_start_snapshot(invoke: Any) -> tuple[dict[str, Any], dict[str, bool]]:
    evidence, lanes = _ORIGINAL_PRE_START(invoke)
    receipt, stdout, _ = invoke("P04", "POWERSHELL_MODULE_PREFLIGHT", 60)
    preflight: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    if legacy.command_ok(receipt):
        try:
            preflight = compatibility.validate_powershell_module_preflight(
                legacy.parse_json_bytes(stdout)
            )
        except Exception as exc:
            if isinstance(exc, compatibility.IdentityContractError):
                failure = exc.as_record()
            else:
                failure = {
                    "stage": "P04",
                    "code": f"P04_UNEXPECTED_{type(exc).__name__.upper()}",
                    "field": None,
                    "safe_details": {},
                }
    else:
        failure = {
            "stage": "P04",
            "code": "POWERSHELL_PREFLIGHT_COMMAND_FAILED",
            "field": None,
            "safe_details": {},
        }
    complete = preflight is not None and failure is None
    evidence["powershell_module_preflight"] = preflight
    evidence["powershell_module_preflight_failure"] = failure
    evidence["powershell_module_preflight_complete"] = complete
    lanes = dict(lanes)
    lanes["powershell_module_preflight"] = complete
    evidence["lanes"] = lanes
    evidence["all_lanes_pass"] = all(lanes.values())
    return evidence, lanes


def _validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    result = _ORIGINAL_VALIDATE_FROZEN(repo_root, head)
    compatibility_facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_COMPATIBILITY_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        blob_bytes, blob_sha256 = legacy.git_blob_fact(repo_root, head, relative)
        if blob_sha256 != expected_sha256:
            raise RuntimeError("frozen Attempt-009 compatibility Git blob hash mismatch")
        if legacy.canonical_lf_fact(repo_root / relative) != (blob_bytes, blob_sha256):
            raise RuntimeError("frozen Attempt-009 compatibility checkout drift")
        compatibility_facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": blob_bytes,
            "git_blob_sha256": blob_sha256,
        })
    result["attempt009_compatibility_artifact_count"] = len(compatibility_facts)
    result["attempt009_compatibility_artifacts"] = compatibility_facts
    return result


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate_gate_receipts(
    repo_root: Path,
    head: str,
    packet_commit: str,
    central_path: Path,
    central_sha256: str,
    audit_path: Path,
    audit_sha256: str,
) -> dict[str, Any]:
    if central_path == audit_path or not _valid_hash(central_sha256) or not _valid_hash(audit_sha256):
        raise RuntimeError("Attempt-009 gate receipt locator invalid")
    if legacy.git_blob_fact(repo_root, head, central_path)[1] != central_sha256:
        raise RuntimeError("central validation receipt hash mismatch")
    if legacy.git_blob_fact(repo_root, head, audit_path)[1] != audit_sha256:
        raise RuntimeError("fresh audit receipt hash mismatch")
    central = _ORIGINAL_LOAD_JSON(repo_root / central_path)
    audit = _ORIGINAL_LOAD_JSON(repo_root / audit_path)
    expected_facts = legacy.packet_facts(repo_root, packet_commit)
    if (
        central.get("schema_version") != CENTRAL_RECEIPT_SCHEMA
        or central.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT009"
        or central.get("verdict") != CENTRAL_RECEIPT_VERDICT
        or central.get("packet_commit", "").casefold() != packet_commit
        or central.get("packet_artifacts") != expected_facts
        or central.get("validator_verdict") != "READY_FOR_CENTRAL_STATIC_VALIDATION"
        or central.get("runtime_commands_executed") is not False
        or central.get("write_set") != [central_path.as_posix()]
    ):
        raise RuntimeError("central validation receipt binding mismatch")
    if (
        audit.get("schema_version") != AUDIT_RECEIPT_SCHEMA
        or audit.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT009"
        or audit.get("verdict") != AUDIT_RECEIPT_VERDICT
        or audit.get("packet_commit", "").casefold() != packet_commit
        or audit.get("packet_artifacts") != expected_facts
        or audit.get("central_validation_receipt_git_blob_sha256") != central_sha256
        or audit.get("runtime_commands_executed") is not False
        or audit.get("write_set") != [audit_path.as_posix()]
    ):
        raise RuntimeError("fresh audit receipt binding mismatch")
    return {
        "central_validation_receipt": {
            "path": central_path.as_posix(),
            "git_blob_sha256": central_sha256,
            "verdict": central["verdict"],
        },
        "fresh_independent_audit_receipt": {
            "path": audit_path.as_posix(),
            "git_blob_sha256": audit_sha256,
            "verdict": audit["verdict"],
        },
    }


def configure_legacy_runner() -> None:
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
    legacy.EXPECTED_COMMAND_IDS = EXPECTED_COMMAND_IDS
    legacy.COMMAND_ARGV_TEMPLATES = dict(legacy.COMMAND_ARGV_TEMPLATES)
    legacy.COMMAND_ARGV_TEMPLATES["POWERSHELL_MODULE_PREFLIGHT"] = [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "POWERSHELL_MODULE_PREFLIGHT_QUERY",
    ]
    legacy.POWERSHELL_MODULE_PREFLIGHT_QUERY = compatibility.POWERSHELL_MODULE_PREFLIGHT_QUERY
    legacy.PROCESS_IDENTITY_QUERY = compatibility.wrap_process_identity_probe(
        legacy.PROCESS_IDENTITY_QUERY
    )
    legacy.TCP_IDENTITY_QUERY = compatibility.wrap_tcp_identity_probe(
        legacy.TCP_IDENTITY_QUERY
    )
    legacy.DOCKER_DESKTOP_FILE_IDENTITY_QUERY = compatibility.wrap_desktop_file_identity_probe(
        legacy.DOCKER_DESKTOP_FILE_IDENTITY_QUERY
    )
    original_build_argv = legacy.build_argv

    def build_argv(kind: str) -> list[str]:
        if kind == "POWERSHELL_MODULE_PREFLIGHT":
            return [
                str(legacy.POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
                "-Command", compatibility.POWERSHELL_MODULE_PREFLIGHT_QUERY,
            ]
        return original_build_argv(kind)

    legacy.build_argv = build_argv
    legacy.load_json = _adapted_load_json
    legacy.write_json = _adapted_write_json
    legacy.passport = _runtime_passport
    legacy.base.run_command = _run_command
    legacy.pre_start_snapshot = _pre_start_snapshot
    legacy.validate_frozen_upstream = _validate_frozen_upstream
    legacy.validate_gate_receipts = _validate_gate_receipts
    legacy.parser_v2 = SimpleNamespace(
        IdentityContractError=compatibility.IdentityContractError,
        sanitize_docker_identity=compatibility.sanitize_docker_identity,
    )


def main() -> int:
    configure_legacy_runner()
    return legacy.main()


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
