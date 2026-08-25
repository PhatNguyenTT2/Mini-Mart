#!/usr/bin/env python3
"""Run one fail-closed Docker Desktop admission observation after all later gates.

This file is a dormant packet runner.  Packet design and static validation do
not invoke it.  A later exact command may invoke it once only after a tracked
central-validation receipt, a tracked fresh-audit receipt, and a separate user
confirmation are all present and hash-bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
import execute_e4_r6_pc2w_p1_attempt006_baseline_remediation as baseline
import e4_r6_pc2w_p1_attempt008_probe_contract as parser_v2
import e4_r6_pc2w_p1_attempt008_safe_probe_envelopes as probes_v2


base = baseline.base
DOCKER = baseline.DOCKER
DOCKER_DESKTOP = base.DOCKER_DESKTOP
WSL = baseline.WSL
POWERSHELL = baseline.POWERSHELL
PYTHON = baseline.PYTHON
EXPECTED_EXECUTION_ROOT = baseline.EXPECTED_EXECUTION_ROOT
EXPECTED_EXECUTABLES = baseline.EXPECTED_EXECUTABLES

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt008_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt008_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt008_static_packet.py"
PACKET_PARENT = "b973ed673a314d6223265712b95d2a7ce51b02f3"
PACKET_RELATIVES = {
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
}
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_aq/"
    "E4_R6PC2W_P1_attempt008_admission_observation"
)
EXPECTED_OUTPUT_FILES = {
    "admission_observation.json",
    "command_receipts.json",
    "execution_receipt.json",
    "handoff.json",
}
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT008_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt008-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT008_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt008-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT008_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT008_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT008_CURRENT_HOST_NOT_ADMISSIBLE"
SETTLING_SECONDS = 20
SNAPSHOT_BARRIER_SECONDS = 15
SNAPSHOT_LABELS = ["A", "B", "C"]
ERROR_CODES = {"NONE", "PROBE_EXCEPTION", "COMMAND_FAILED", "OUTPUT_MALFORMED"}
TARGET_PROCESS_NAMES = {
    "docker desktop",
    "com.docker.backend",
    "com.docker.build",
    "com.docker.proxy",
    "dockerd",
    "vpnkit",
    "wslrelay",
}
REQUIRED_DURING_PROCESS_NAMES = {"docker desktop", "com.docker.backend"}
FROZEN_UPSTREAM_SHA256_LITERAL = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json":
        "7008657dfcbe138321c68dc3b2632265f16bfb05084c9686ae7eb95706c3a970",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt006_baseline_packet_audit_receipt.json":
        "cdab7460e62d86a95d17cd67874c4dfacc17c8152bcc6a1e07dcfaacbdaf6c66",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/E4_R6PC2W_P1_attempt006_baseline_remediation/command_receipts.json":
        "0c708d53732aeaaa7c525111bd7086fce943cce5ffab2d580f293942f53ffe2c",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/E4_R6PC2W_P1_attempt006_baseline_remediation/p1_execution_receipt.json":
        "430becb7502b90058614671832daf6604aaa0d00166bd200719383570cae2900",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/E4_R6PC2W_P1_attempt006_baseline_remediation/p1_handoff.json":
        "5a0847ed7229e0de5b7ebc9e40ec4111304ac6a1803cf2de5b7796edc4d0c955",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/E4_R6PC2W_P1_attempt006_baseline_remediation/runtime_inventory.json":
        "2c07fd7b7bc73d51d58071999eb062831e75261a2674d57df796cdf6bc3a5298",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt007_failure_packet_audit_receipt.json":
        "1ba1cf68b230fe06e5c2283394914d0db17435ba9f97f758644bd20425ebc156",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt008_probe_parser_remediation_contract.json":
        "3976a4c511684fa7b8df753265b9f96b49d022098894f9769ca0c531d85245e0",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt008_probe_contract.py":
        "2076af6aac7f0d28b53378b9362b2e8aa73ce8ac5e97664f29294ae6417f9d03",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt008_probe_contract.py":
        "94470c80740817f5ab5f206dde1c88b4fd2d90fff18576a5be142449a9e31b6f",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt008_probe_parser_remediation_validation_receipt.json":
        "f7e53f14de491ea588c7a9688a1e52a07c6448389f3d13d526fd3da2d4c0d519",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt008_safe_probe_envelope_contract.json":
        "9bf7745b49d18ad44cdeba242d0524d24ca13c47c8c0574f559b4c570c35caaa",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py":
        "04d2014b07388215ff034e817471228dbb767a3d85efb21cb80c74691358e047",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py":
        "1d1d8ac297eebfedb23091ed8735dd2622ef10018dfc85396eac48c7016dcf6c",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt008_safe_probe_envelope_validation_receipt.json":
        "90e3eaf42512e11ca441e3c00132d44e7ec24c0b9a916a6637aacba59886c169",
}
FROZEN_UPSTREAM_SHA256 = {
    Path(path): value for path, value in FROZEN_UPSTREAM_SHA256_LITERAL.items()
}

EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03",
    "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]
COMMAND_ARGV_TEMPLATES = {
    "WSL_VERBOSE": ["WSL", "--list", "--verbose"],
    "WSL_RUNNING": ["WSL", "--list", "--running", "--quiet"],
    "PROCESS_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "PROCESS_POPULATION_QUERY",
    ],
    "TCP_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "TCP_POPULATION_QUERY",
    ],
    "DOCKER_DESKTOP_START": ["DOCKER", "desktop", "start"],
    "DOCKER_DESKTOP_STOP": ["DOCKER", "desktop", "stop"],
    "WSL_SHUTDOWN": ["WSL", "--shutdown"],
    "PROCESS_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "PROCESS_IDENTITY_QUERY",
    ],
    "TCP_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "TCP_IDENTITY_QUERY",
    ],
    "DOCKER_VERSION": [
        "DOCKER", "--context", "desktop-linux", "version", "--format", "{{json .}}",
    ],
    "DOCKER_INFO": [
        "DOCKER", "--context", "desktop-linux", "info", "--format", "{{json .}}",
    ],
    "DOCKER_CONTEXT_INSPECT": ["DOCKER", "context", "inspect", "desktop-linux"],
    "DOCKER_DESKTOP_FILE_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "DOCKER_DESKTOP_FILE_IDENTITY_QUERY",
    ],
}

PROCESS_POPULATION_QUERY = baseline.PROCESS_POPULATION_QUERY
TCP_POPULATION_QUERY = baseline.TCP_POPULATION_QUERY

PROCESS_IDENTITY_QUERY = probes_v2.PROCESS_IDENTITY_QUERY_V2
TCP_IDENTITY_QUERY = probes_v2.TCP_IDENTITY_QUERY_V2
DOCKER_DESKTOP_FILE_IDENTITY_QUERY = probes_v2.DOCKER_DESKTOP_FILE_IDENTITY_QUERY_V2


_FAILURE_CONTEXT: dict[str, Any] | None = None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_error_hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git(repo_root: Path, *args: str) -> str:
    return baseline.git(repo_root, *args)


def git_blob_fact(repo_root: Path, revision: str, relative: Path) -> tuple[int, str]:
    return baseline.git_blob_fact(repo_root, revision, relative)


def canonical_lf_fact(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("bare carriage return")
    return len(normalized), sha256_bytes(normalized)


def strict_json_text(value: str) -> Any:
    return baseline.strict_json_text(value)


def load_json(path: Path) -> dict[str, Any]:
    return baseline.load_json(path)


def command_ok(receipt: dict[str, Any]) -> bool:
    return baseline.command_ok(receipt)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_argv(kind: str) -> list[str]:
    template = COMMAND_ARGV_TEMPLATES.get(kind)
    if template is None:
        raise RuntimeError("unknown command kind")
    replacements = {
        "DOCKER": str(DOCKER),
        "WSL": str(WSL),
        "POWERSHELL": str(POWERSHELL),
        "PROCESS_POPULATION_QUERY": PROCESS_POPULATION_QUERY,
        "TCP_POPULATION_QUERY": TCP_POPULATION_QUERY,
        "PROCESS_IDENTITY_QUERY": PROCESS_IDENTITY_QUERY,
        "TCP_IDENTITY_QUERY": TCP_IDENTITY_QUERY,
        "DOCKER_DESKTOP_FILE_IDENTITY_QUERY": DOCKER_DESKTOP_FILE_IDENTITY_QUERY,
    }
    return [replacements.get(token, token) for token in template]


def sanitized_receipt(receipt: dict[str, Any], kind: str) -> dict[str, Any]:
    argv = receipt.get("argv")
    argv_hash = sha256_bytes(
        json.dumps(argv, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return {
        "command_id": receipt.get("command_id"),
        "command_kind": kind,
        "argv_sha256": argv_hash,
        "shell": receipt.get("shell"),
        "timeout_seconds": receipt.get("timeout_seconds"),
        "started_at": receipt.get("started_at"),
        "ended_at": receipt.get("ended_at"),
        "elapsed_seconds": receipt.get("elapsed_seconds"),
        "exit_code": receipt.get("exit_code"),
        "timed_out": receipt.get("timed_out"),
        "spawn_exception_type_hash": (
            stable_error_hash(str(receipt.get("spawn_exception_type")))
            if receipt.get("spawn_exception_type") else None
        ),
        "spawn_exception_message_sha256": receipt.get("spawn_exception_message_sha256"),
        "stdout_bytes": receipt.get("stdout_bytes"),
        "stdout_sha256": receipt.get("stdout_sha256"),
        "stderr_bytes": receipt.get("stderr_bytes"),
        "stderr_sha256": receipt.get("stderr_sha256"),
        "raw_argv_stdout_stderr_persisted": False,
    }


def parse_json_bytes(value: bytes) -> Any:
    text, complete = base.native_gate.decode_output_strict(value)
    if not complete or not text.strip():
        raise ValueError("JSON command output encoding or emptiness failure")
    return strict_json_text(text)


def parse_if_success(
    command_id: str,
    by_id: dict[str, dict[str, Any]],
    raw: dict[str, tuple[bytes, bytes]],
    parser: Callable[[bytes], Any],
    failures: list[str],
) -> Any:
    receipt = by_id.get(command_id)
    if receipt is None or not command_ok(receipt):
        failures.append(f"{command_id}:COMMAND_FAILED")
        return None
    try:
        return parser(raw[command_id][0])
    except Exception as exc:
        failures.append(f"{command_id}:PARSE:{type(exc).__name__}")
        return None


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None




def gate_receipt_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or relative.suffix.casefold() != ".json":
        raise RuntimeError("gate receipt path must be a relative JSON path")
    if relative == CONTROL_RELATIVE or CONTROL_RELATIVE not in relative.parents:
        raise RuntimeError("gate receipt path must be below 00_control")
    if relative in PACKET_RELATIVES:
        raise RuntimeError("gate receipt cannot alias a packet artifact")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise RuntimeError("gate receipt path is not canonical")
    return relative


def packet_facts(repo_root: Path, packet_commit: str) -> list[dict[str, Any]]:
    return [
        {
            "path": relative.as_posix(),
            "git_blob_bytes": git_blob_fact(repo_root, packet_commit, relative)[0],
            "git_blob_sha256": git_blob_fact(repo_root, packet_commit, relative)[1],
        }
        for relative in sorted(PACKET_RELATIVES, key=lambda path: path.as_posix())
    ]


def validate_gate_receipts(
    repo_root: Path,
    head: str,
    packet_commit: str,
    central_path: Path,
    central_sha256: str,
    audit_path: Path,
    audit_sha256: str,
) -> dict[str, Any]:
    if central_path == audit_path:
        raise RuntimeError("central and audit receipt paths must be distinct")
    if not valid_hash(central_sha256) or not valid_hash(audit_sha256):
        raise RuntimeError("gate receipt SHA-256 must be lowercase hex")
    if git_blob_fact(repo_root, head, central_path)[1] != central_sha256:
        raise RuntimeError("central validation receipt hash mismatch")
    if git_blob_fact(repo_root, head, audit_path)[1] != audit_sha256:
        raise RuntimeError("fresh audit receipt hash mismatch")
    central = load_json(repo_root / central_path)
    audit = load_json(repo_root / audit_path)
    expected_facts = packet_facts(repo_root, packet_commit)
    if central.get("schema_version") != CENTRAL_RECEIPT_SCHEMA:
        raise RuntimeError("central validation receipt schema mismatch")
    if central.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT008":
        raise RuntimeError("central validation receipt stage mismatch")
    if central.get("verdict") != CENTRAL_RECEIPT_VERDICT:
        raise RuntimeError("central validation receipt verdict mismatch")
    if central.get("packet_commit", "").casefold() != packet_commit:
        raise RuntimeError("central validation receipt packet binding mismatch")
    if central.get("packet_artifacts") != expected_facts:
        raise RuntimeError("central validation receipt artifact binding mismatch")
    if central.get("validator_verdict") != "READY_FOR_CENTRAL_STATIC_VALIDATION":
        raise RuntimeError("central validation receipt validator binding mismatch")
    if central.get("runtime_commands_executed") is not False:
        raise RuntimeError("central validation receipt runtime boundary widened")
    if central.get("write_set") != [central_path.as_posix()]:
        raise RuntimeError("central validation receipt write set mismatch")
    if audit.get("schema_version") != AUDIT_RECEIPT_SCHEMA:
        raise RuntimeError("fresh audit receipt schema mismatch")
    if audit.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT008":
        raise RuntimeError("fresh audit receipt stage mismatch")
    if audit.get("verdict") != AUDIT_RECEIPT_VERDICT:
        raise RuntimeError("fresh audit receipt verdict mismatch")
    if audit.get("packet_commit", "").casefold() != packet_commit:
        raise RuntimeError("fresh audit receipt packet binding mismatch")
    if audit.get("packet_artifacts") != expected_facts:
        raise RuntimeError("fresh audit receipt artifact binding mismatch")
    if audit.get("central_validation_receipt_git_blob_sha256") != central_sha256:
        raise RuntimeError("fresh audit receipt central binding mismatch")
    if audit.get("runtime_commands_executed") is not False:
        raise RuntimeError("fresh audit receipt runtime boundary widened")
    if audit.get("write_set") != [audit_path.as_posix()]:
        raise RuntimeError("fresh audit receipt write set mismatch")
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


def validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_UPSTREAM_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        blob_bytes, blob_sha256 = git_blob_fact(repo_root, head, relative)
        if blob_sha256 != expected_sha256:
            raise RuntimeError("frozen Attempt-008 upstream Git blob hash mismatch")
        if canonical_lf_fact(repo_root / relative) != (blob_bytes, blob_sha256):
            raise RuntimeError("frozen Attempt-008 upstream checkout CRLF or bare-CR drift")
        facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": blob_bytes,
            "git_blob_sha256": blob_sha256,
        })
    state = load_json(repo_root / (CONTROL_RELATIVE / "pipeline_state_stage1e.json"))
    audit = load_json(
        repo_root / (
            CONTROL_RELATIVE /
            "rebaseline_v2_e4_r6_pc2w_p1_attempt006_baseline_packet_audit_receipt.json"
        )
    )
    pc2w = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
    attempt006 = pc2w.get("p1_attempt006_baseline_remediation", {})
    if state.get("state") != (
        "stage1e_rebaseline_v2_r6_pc2w_p1_attempt008_r2_safe_probe_envelopes_"
        "complete_r3_dormant_runtime_packet_design"
    ):
        raise RuntimeError("Attempt-008 R2 pipeline state is not the frozen admission input")
    if audit.get("verdict") != (
        "PASS_PC2W_P1_ATTEMPT006_BASELINE_PACKET_AUDITED_"
        "READY_FOR_ADMISSION_PACKET_DESIGN"
    ):
        raise RuntimeError("Attempt-006 audit verdict mismatch")
    summary = audit.get("audit_summary", {})
    if summary.get("authoritative_checks_passed") != 460 or summary.get("authoritative_checks_total") != 460:
        raise RuntimeError("Attempt-006 audit check count mismatch")
    result = attempt006.get("execution_result", {})
    if result.get("verdict") != "PASS_PC2W_P1_ATTEMPT006_BASELINE_REMEDIATED_READY_FOR_ADMISSION_PACKET":
        raise RuntimeError("Attempt-006 execution verdict mismatch")
    if (
        result.get("baseline_mode") != "ALREADY_CLOSED_ZERO_MUTATION"
        or result.get("closure_snapshots") != 3
        or result.get("snapshots_stable") is not True
        or result.get("benchmark_admission_opened") is not False
    ):
        raise RuntimeError("Attempt-006 frozen baseline semantics mismatch")
    if state.get("result_status") != "NOT_RUN" or state.get("test_set_opened") != "NO":
        raise RuntimeError("Attempt-008 upstream truth state widened")
    attempt007 = pc2w.get("p1_attempt007_admission_observation", {})
    if (
        attempt007.get("execution_result", {}).get("verdict")
        != "FAIL_CLOSED_PC2W_P1_ATTEMPT007_CURRENT_HOST_NOT_ADMISSIBLE"
        or attempt007.get("automatic_retry_authorized") is not False
    ):
        raise RuntimeError("Attempt-007 failure truth or no-retry lock mismatch")
    r1 = pc2w.get("p1_attempt008_probe_parser_remediation", {})
    if (
        r1.get("validation_verdict")
        != "PASS_PC2W_P1_ATTEMPT008_R1_SYNTHETIC_PROBE_PARSER_REMEDIATION"
        or r1.get("runtime_execution_authorized") is not False
    ):
        raise RuntimeError("Attempt-008 R1 remediation state mismatch")
    r2 = pc2w.get("p1_attempt008_safe_probe_envelopes", {})
    if (
        r2.get("validation_verdict")
        != "PASS_PC2W_P1_ATTEMPT008_R2_SAFE_PROBE_ENVELOPES_STATIC_SYNTHETIC"
        or r2.get("runtime_execution_authorized") is not False
    ):
        raise RuntimeError("Attempt-008 R2 safe envelope state mismatch")
    return {"artifact_count": len(facts), "artifacts": facts}


def passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt008_admission_observation_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt008_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt008_execution_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt006_baseline_packet_audit_receipt_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def failure_documents(
    context: dict[str, Any], error_type: str, error_hash: str
) -> dict[str, dict[str, Any]]:
    receipts = list(context["receipts"])
    ids = [str(row.get("command_id")) for row in receipts]
    common = {
        "verdict": "HANDOFF_INCOMPLETE",
        "error_type": error_type,
        "error_sha256": error_hash,
        "exception_message_persisted": False,
        "failure_receipt_is_progress_durable": True,
    }
    truth = {
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "benchmark_admission_opened": False,
    }
    return {
        "command_receipts.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-command-receipts-1.0",
            "material_passport": context["material_passport"],
            "entry_checkpoint": context["entry_checkpoint"],
            "packet_commit": context["packet_commit"],
            "commands": receipts,
            "command_ids": ids,
            "automatic_retry_count": 0,
            "fallback_count": 0,
            "raw_argv_stdout_stderr_persisted": False,
            "failure": common,
        },
        "admission_observation.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-1.0",
            "material_passport": context["material_passport"],
            "entry_checkpoint": context["entry_checkpoint"],
            "evidence_state": "INCOMPLETE_FAIL_CLOSED",
            "observations": context.get("observations", {}),
            "sanitization": {
                "raw_process_paths_or_command_lines_persisted": False,
                "raw_network_addresses_persisted": False,
                "raw_proxy_values_persisted": False,
                "raw_stdout_stderr_or_argv_persisted": False,
            },
            "failure": common,
        },
        "execution_receipt.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-execution-receipt-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
            "created_at": context["created_at"],
            "entry_checkpoint": context["entry_checkpoint"],
            "packet_commit": context["packet_commit"],
            "docker_desktop_start_attempts": ids.count("S00"),
            "docker_desktop_stop_attempts": ids.count("F00"),
            "wsl_shutdown_attempts": ids.count("F01"),
            "automatic_retry_count": 0,
            "fallback_count": 0,
            "materialization_performed": False,
            "preprocessing_performed": False,
            "training_performed": False,
            "evaluation_performed": False,
            "benchmark_admission_opened": False,
            "result_status": "NOT_RUN",
            "test_set_opened": "NO",
            "accepted_result_rows": 0,
            "failure": common,
        },
        "handoff.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-handoff-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
            "verdict": "HANDOFF_INCOMPLETE",
            "output_files": sorted(EXPECTED_OUTPUT_FILES),
            "next_gate": "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY",
            "truth_state": truth,
            "failure": common,
        },
    }


def persist_failure_packet(error_type: str, error_text: str) -> bool:
    context = _FAILURE_CONTEXT
    if context is None:
        return False
    root = Path(context["output_root"])
    docs = failure_documents(context, error_type, stable_error_hash(error_text))
    for name in sorted(EXPECTED_OUTPUT_FILES):
        write_json(root / name, docs[name])
    entries = list(root.iterdir())
    if {entry.name for entry in entries} != EXPECTED_OUTPUT_FILES or not all(entry.is_file() for entry in entries):
        raise RuntimeError("durable failure packet exact file set violated")
    return True


def pre_start_snapshot(
    invoke: Callable[[str, str, int], tuple[dict[str, Any], bytes, bytes]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    wsl_receipt, wsl_stdout, _ = invoke("P00", "WSL_VERBOSE", 30)
    running_receipt, running_stdout, _ = invoke("P01", "WSL_RUNNING", 30)
    pipe, pipe_complete = baseline.pipe_evidence()
    process_receipt, process_stdout, _ = invoke("P02", "PROCESS_POPULATION", 30)
    tcp_receipt, tcp_stdout, _ = invoke("P03", "TCP_POPULATION", 30)
    disk, disk_complete = baseline.disk_evidence()
    wsl, wsl_complete = baseline.wsl_evidence(wsl_receipt, wsl_stdout, False)
    running, running_complete = baseline.wsl_evidence(running_receipt, running_stdout, True)
    processes, process_complete = baseline.population_evidence(process_receipt, process_stdout, "process")
    tcp, tcp_complete = baseline.population_evidence(tcp_receipt, tcp_stdout, "tcp")
    lanes = baseline.lane_result(
        wsl, wsl_complete, running, running_complete, pipe, pipe_complete,
        processes, process_complete, tcp, tcp_complete, disk, disk_complete,
    )
    evidence = {
        "wsl_inventory": wsl,
        "wsl_running_inventory": running,
        "named_pipe": pipe,
        "target_process_population": processes,
        "target_process_population_envelope_valid": process_complete,
        "target_tcp_population": tcp,
        "target_tcp_population_envelope_valid": tcp_complete,
        "disk": disk,
        "lanes": lanes,
        "all_lanes_pass": all(lanes.values()),
    }
    return evidence, lanes


def collect_snapshot(
    label: str,
    verbose_id: str,
    running_id: str,
    process_id: str,
    tcp_id: str,
    invoke: Callable[[str, str, int], tuple[dict[str, Any], bytes, bytes]],
) -> dict[str, Any]:
    wsl_receipt, wsl_stdout, _ = invoke(verbose_id, "WSL_VERBOSE", 30)
    running_receipt, running_stdout, _ = invoke(running_id, "WSL_RUNNING", 30)
    pipe, pipe_complete = baseline.pipe_evidence()
    process_receipt, process_stdout, _ = invoke(process_id, "PROCESS_POPULATION", 30)
    tcp_receipt, tcp_stdout, _ = invoke(tcp_id, "TCP_POPULATION", 30)
    disk, disk_complete = baseline.disk_evidence()
    wsl, wsl_complete = baseline.wsl_evidence(wsl_receipt, wsl_stdout, False)
    running, running_complete = baseline.wsl_evidence(running_receipt, running_stdout, True)
    processes, process_complete = baseline.population_evidence(process_receipt, process_stdout, "process")
    tcp, tcp_complete = baseline.population_evidence(tcp_receipt, tcp_stdout, "tcp")
    lanes = baseline.lane_result(
        wsl, wsl_complete, running, running_complete, pipe, pipe_complete,
        processes, process_complete, tcp, tcp_complete, disk, disk_complete,
    )
    return {
        "label": label,
        "wsl_inventory": wsl,
        "wsl_running_inventory": running,
        "named_pipe": pipe,
        "target_process_population": processes,
        "target_process_population_envelope_valid": process_complete,
        "target_tcp_population": tcp,
        "target_tcp_population_envelope_valid": tcp_complete,
        "disk": disk,
        "lanes": lanes,
        "all_lanes_pass": all(lanes.values()),
    }


def main() -> int:
    global _FAILURE_CONTEXT
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--packet-commit", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--central-validation-receipt", required=True)
    parser.add_argument("--central-validation-receipt-sha256", required=True)
    parser.add_argument("--fresh-audit-receipt", required=True)
    parser.add_argument("--fresh-audit-receipt-sha256", required=True)
    parser.add_argument("--execution-confirmation", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if repo_root != EXPECTED_EXECUTION_ROOT.resolve() or Path.cwd().resolve() != repo_root:
        raise RuntimeError("execution root or working directory mismatch")
    if args.execution_confirmation != CONFIRMATION_TOKEN:
        raise RuntimeError("separate post-validation exact-command confirmation missing")
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repository root mismatch")
    if Path(sys.executable).resolve() != PYTHON.resolve() or sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("interpreter identity mismatch")
    for executable, expected in EXPECTED_EXECUTABLES.items():
        if not executable.is_file() or base.file_fact(executable) != expected:
            raise RuntimeError("executable identity mismatch")

    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    packet_commit = str(args.packet_commit).casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        raise RuntimeError("exact execution HEAD mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", packet_commit):
        raise RuntimeError("packet commit format invalid")
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean")
    packet_parent = git(repo_root, "rev-list", "--parents", "-n", "1", packet_commit).split()
    if len(packet_parent) != 2 or packet_parent[1].casefold() != PACKET_PARENT:
        raise RuntimeError("packet parent mismatch")
    packet_delta = git(
        repo_root, "diff-tree", "--no-commit-id", "--name-status", "-r", packet_commit
    ).splitlines()
    expected_delta = sorted(f"A\t{path.as_posix()}" for path in PACKET_RELATIVES)
    if sorted(packet_delta) != expected_delta:
        raise RuntimeError("packet commit exact four-file add delta mismatch")
    try:
        git(repo_root, "merge-base", "--is-ancestor", packet_commit, head)
    except Exception as exc:
        raise RuntimeError("packet commit is not an ancestor of execution HEAD") from exc
    for relative in PACKET_RELATIVES:
        if git_blob_fact(repo_root, packet_commit, relative) != git_blob_fact(repo_root, head, relative):
            raise RuntimeError("packet artifact drift after static validation")

    central_path = gate_receipt_path(args.central_validation_receipt)
    audit_path = gate_receipt_path(args.fresh_audit_receipt)
    expected_process_argv = [
        str(PYTHON.resolve()),
        str((repo_root / RUNNER_RELATIVE).resolve()),
        "--repo-root", str(repo_root),
        "--packet-commit", packet_commit,
        "--expected-head", head,
        "--central-validation-receipt", central_path.as_posix(),
        "--central-validation-receipt-sha256", args.central_validation_receipt_sha256,
        "--fresh-audit-receipt", audit_path.as_posix(),
        "--fresh-audit-receipt-sha256", args.fresh_audit_receipt_sha256,
        "--execution-confirmation", CONFIRMATION_TOKEN,
    ]
    original = list(getattr(sys, "orig_argv", []))
    actual_process_argv = (
        [str(Path(original[0]).resolve()), str(Path(original[1]).resolve()), *original[2:]]
        if len(original) >= 2 else original
    )
    if actual_process_argv != expected_process_argv:
        raise RuntimeError("exact original process argv mismatch")

    output_root = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_root.exists():
        raise RuntimeError("immutable one-shot output root already exists")
    frozen_upstream = validate_frozen_upstream(repo_root, head)
    gate_receipts = validate_gate_receipts(
        repo_root, head, packet_commit, central_path,
        args.central_validation_receipt_sha256,
        audit_path, args.fresh_audit_receipt_sha256,
    )
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    authorization = load_json(repo_root / AUTHORIZATION_RELATIVE)
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-contract-1.0":
        raise RuntimeError("Attempt-008 contract schema mismatch")
    if authorization.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt008-execution-authorization-1.0":
        raise RuntimeError("Attempt-008 authorization schema mismatch")
    current_auth = authorization.get("current_authorization", {})
    if (
        current_auth.get("packet_design_authorized") is not True
        or current_auth.get("runtime_execution_authorized") is not False
        or current_auth.get("exact_command_confirmation_received") is not False
    ):
        raise RuntimeError("authorization artifact truth widened or malformed")
    if contract.get("model_policy") != authorization.get("model_policy"):
        raise RuntimeError("model policy mismatch")
    model = authorization.get("model_policy", {})
    if (
        model.get("requested_model") != "gpt-5.6-sol"
        or model.get("requested_reasoning_effort") != "xhigh"
        or model.get("requested_service_tier") != "default"
        or model.get("fast_or_priority_allowed") is not False
        or model.get("actual_service_tier") != "UNOBSERVABLE"
    ):
        raise RuntimeError("requested Standard-only model policy mismatch")

    created_at = utc_now()
    material_passport = passport(created_at, authorization)
    receipts: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}
    observations: dict[str, Any] = {
        "frozen_upstream": frozen_upstream,
        "gate_receipts": gate_receipts,
    }
    output_root.mkdir(parents=True, exist_ok=False)
    _FAILURE_CONTEXT = {
        "output_root": str(output_root),
        "created_at": created_at,
        "material_passport": material_passport,
        "entry_checkpoint": head,
        "packet_commit": packet_commit,
        "receipts": receipts,
        "observations": observations,
    }
    persist_failure_packet("IN_PROGRESS", "Attempt-008 initialized before first runtime command")

    def invoke(
        command_id: str, kind: str, timeout_seconds: int = 30
    ) -> tuple[dict[str, Any], bytes, bytes]:
        argv = build_argv(kind)
        if kind.startswith("DOCKER_") and not base.docker_subcommand_is_allowed(argv):
            raise RuntimeError("Docker command is outside the exact allowlist")
        receipt, stdout, stderr = base.run_command(
            command_id, argv, timeout_seconds=timeout_seconds
        )
        receipts.append(sanitized_receipt(receipt, kind))
        raw[command_id] = (stdout, stderr)
        persist_failure_packet("IN_PROGRESS", f"Attempt-008 progress after {command_id}")
        return receipt, stdout, stderr

    pre_start, pre_lanes = pre_start_snapshot(invoke)
    observations["pre_start"] = pre_start
    persist_failure_packet("IN_PROGRESS", "Attempt-008 immediate pre-start gate complete")

    start_attempted = False
    start_receipt: dict[str, Any] | None = None
    stop_receipt: dict[str, Any] | None = None
    shutdown_receipt: dict[str, Any] | None = None
    if all(pre_lanes.values()):
        try:
            start_attempted = True
            start_receipt, _, _ = invoke("S00", "DOCKER_DESKTOP_START", 180)
            if command_ok(start_receipt):
                invoke("D00", "WSL_VERBOSE", 30)
                invoke("D01", "PROCESS_IDENTITY", 60)
                invoke("D02", "TCP_IDENTITY", 60)
                invoke("D03", "DOCKER_VERSION", 60)
                invoke("D04", "DOCKER_INFO", 60)
                invoke("D05", "DOCKER_CONTEXT_INSPECT", 60)
                invoke("D06", "DOCKER_DESKTOP_FILE_IDENTITY", 60)
        finally:
            if start_attempted:
                try:
                    stop_receipt, _, _ = invoke("F00", "DOCKER_DESKTOP_STOP", 180)
                finally:
                    shutdown_receipt, _, _ = invoke("F01", "WSL_SHUTDOWN", 120)

    snapshots: list[dict[str, Any]] = []
    if start_attempted:
        time.sleep(SETTLING_SECONDS)
        snapshot_a = collect_snapshot("A", "A00", "A01", "A02", "A03", invoke)
        time.sleep(SNAPSHOT_BARRIER_SECONDS)
        snapshot_b = collect_snapshot("B", "B00", "B01", "B02", "B03", invoke)
        time.sleep(SNAPSHOT_BARRIER_SECONDS)
        snapshot_c = collect_snapshot("C", "C00", "C01", "C02", "C03", invoke)
        snapshots = [snapshot_a, snapshot_b, snapshot_c]
    observations["post_shutdown_snapshots"] = snapshots

    by_id = {str(row.get("command_id")): row for row in receipts}
    parse_failures: list[str] = []
    identity_failures: list[dict[str, Any]] = []

    def record_identity_failure(stage: str, exc: Exception) -> None:
        if isinstance(exc, parser_v2.IdentityContractError):
            identity_failures.append(exc.as_record())
        else:
            identity_failures.append({
                "stage": stage,
                "code": f"{stage}_UNEXPECTED_{type(exc).__name__.upper()}",
                "field": None,
                "safe_details": {},
            })

    during_wsl = parse_if_success("D00", by_id, raw, base.parse_wsl_list, parse_failures)
    rich_process_raw = parse_if_success("D01", by_id, raw, parse_json_bytes, parse_failures)
    rich_process = None
    if rich_process_raw is not None:
        try:
            rich_process = probes_v2.validate_process_probe_envelope(rich_process_raw)
        except Exception as exc:
            record_identity_failure("D01", exc)
    rich_tcp_raw = parse_if_success("D02", by_id, raw, parse_json_bytes, parse_failures)
    rich_tcp = None
    if rich_tcp_raw is not None:
        try:
            rich_tcp = probes_v2.validate_tcp_probe_envelope(rich_tcp_raw, rich_process)
        except Exception as exc:
            record_identity_failure("D02", exc)
    version_data = parse_if_success("D03", by_id, raw, parse_json_bytes, parse_failures)
    info_data = parse_if_success("D04", by_id, raw, parse_json_bytes, parse_failures)
    context_data = parse_if_success("D05", by_id, raw, parse_json_bytes, parse_failures)
    desktop_file_raw = parse_if_success("D06", by_id, raw, parse_json_bytes, parse_failures)
    docker_identity = None
    cross_consistency: dict[str, bool] = {}
    docker_inputs = {
        "D03": version_data,
        "D04": info_data,
        "D05": context_data,
    }
    if all(value is not None for value in docker_inputs.values()):
        try:
            docker_identity, cross_consistency = parser_v2.sanitize_docker_identity(
                version_data, info_data, context_data
            )
        except Exception as exc:
            record_identity_failure("DOCKER_IDENTITY", exc)
    else:
        identity_failures.append({
            "stage": "DOCKER_IDENTITY",
            "code": "DOCKER_IDENTITY_DEPENDENCY_UNAVAILABLE",
            "field": None,
            "safe_details": {
                "missing_command_ids": sorted(
                    command_id for command_id, value in docker_inputs.items() if value is None
                )
            },
        })
    desktop_file_identity = None
    if desktop_file_raw is not None:
        try:
            desktop_file_identity = probes_v2.validate_desktop_file_probe_envelope(
                desktop_file_raw
            )
            if desktop_file_identity["RawBytes"] != DOCKER_DESKTOP.stat().st_size:
                raise parser_v2.IdentityContractError(
                    "DESKTOP_FILE_SIZE_DRIFT", "D06", field="RawBytes"
                )
        except Exception as exc:
            desktop_file_identity = None
            record_identity_failure("D06", exc)

    stable_keys = (
        "wsl_inventory", "wsl_running_inventory", "named_pipe",
        "target_process_population", "target_tcp_population",
    )
    closure_stable = bool(snapshots) and all(
        snapshots[0][key] == snapshots[1][key] == snapshots[2][key]
        for key in stable_keys
    )
    final_matches_pre = bool(snapshots) and all(
        snapshots[-1][key] == pre_start[key]
        for key in stable_keys
    )
    command_ids = [str(row.get("command_id")) for row in receipts]
    pass_conditions = {
        "frozen_upstream_replayed": frozen_upstream.get("artifact_count") == 15,
        "central_validation_and_fresh_audit_bound": len(gate_receipts) == 2,
        "immediate_pre_start_gate_all_pass": all(pre_lanes.values()),
        "docker_desktop_start_attempted_exactly_once": command_ids.count("S00") == 1,
        "docker_desktop_start_succeeded": start_receipt is not None and command_ok(start_receipt),
        "during_docker_desktop_wsl_running": (
            isinstance(during_wsl, list)
            and baseline.distro_state(during_wsl, "docker-desktop") == "Running"
        ),
        "during_process_identity_complete": rich_process is not None,
        "during_tcp_identity_complete": rich_tcp is not None,
        "docker_client_server_info_identity_complete": docker_identity is not None,
        "docker_client_server_info_cross_consistent": bool(cross_consistency) and all(cross_consistency.values()),
        "docker_desktop_executable_identity_complete": desktop_file_identity is not None,
        "parse_failures_absent": not parse_failures,
        "identity_failures_absent": not identity_failures,
        "docker_desktop_stop_attempted_exactly_once": command_ids.count("F00") == 1,
        "docker_desktop_stop_succeeded": stop_receipt is not None and command_ok(stop_receipt),
        "wsl_shutdown_attempted_exactly_once": command_ids.count("F01") == 1,
        "wsl_shutdown_succeeded": shutdown_receipt is not None and command_ok(shutdown_receipt),
        "three_closure_snapshots_present": [row["label"] for row in snapshots] == SNAPSHOT_LABELS,
        "all_closure_lanes_pass": bool(snapshots) and all(row["all_lanes_pass"] for row in snapshots),
        "closure_snapshots_stable": closure_stable,
        "final_closure_matches_pre_start": final_matches_pre,
        "exact_command_sequence_no_retry": command_ids == EXPECTED_COMMAND_IDS,
        "automatic_retry_count_zero": True,
        "fallback_count_zero": True,
        "benchmark_admission_not_opened": True,
    }
    verdict = PASS_VERDICT if all(pass_conditions.values()) else FAIL_VERDICT
    observations.update({
        "during": {
            "wsl_inventory": during_wsl,
            "target_process_identity": rich_process,
            "target_tcp_identity": rich_tcp,
            "docker_identity": docker_identity,
            "docker_desktop_file_identity": desktop_file_identity,
        },
        "parse_failures": parse_failures,
        "identity_failures": identity_failures,
        "closure_stable": closure_stable,
        "final_closure_matches_pre_start": final_matches_pre,
        "pass_conditions": pass_conditions,
    })
    truth = {
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "benchmark_admission_opened": False,
    }
    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-command-receipts-1.0",
        "material_passport": material_passport,
        "entry_checkpoint": head,
        "packet_commit": packet_commit,
        "commands": receipts,
        "command_ids": command_ids,
        "exact_command_sequence": command_ids == EXPECTED_COMMAND_IDS,
        "docker_desktop_start_attempts": command_ids.count("S00"),
        "docker_desktop_stop_attempts": command_ids.count("F00"),
        "wsl_shutdown_attempts": command_ids.count("F01"),
        "automatic_retry_count": 0,
        "fallback_count": 0,
        "raw_argv_stdout_stderr_persisted": False,
    }
    observation_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
        "entry_checkpoint": head,
        "packet_commit": packet_commit,
        "frozen_upstream": frozen_upstream,
        "gate_receipts": gate_receipts,
        "pre_start": pre_start,
        "during": observations["during"],
        "post_shutdown_snapshots": snapshots,
        "closure_stable": closure_stable,
        "final_closure_matches_pre_start": final_matches_pre,
        "parse_failures": parse_failures,
        "identity_failures": identity_failures,
        "sanitization": {
            "raw_process_paths_or_command_lines_persisted": False,
            "raw_network_addresses_persisted": False,
            "raw_proxy_values_persisted": False,
            "raw_docker_root_dir_persisted": False,
            "raw_stdout_stderr_or_argv_persisted": False,
        },
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-execution-receipt-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
        "created_at": created_at,
        "entry_checkpoint": head,
        "packet_commit": packet_commit,
        "packet_artifacts": packet_facts(repo_root, packet_commit),
        "output_root": OUTPUT_RELATIVE.as_posix(),
        "docker_desktop_start_attempts": command_ids.count("S00"),
        "docker_desktop_stop_attempts": command_ids.count("F00"),
        "wsl_shutdown_attempts": command_ids.count("F01"),
        "closure_snapshots": len(snapshots),
        "settling_seconds": SETTLING_SECONDS,
        "snapshot_barrier_seconds": SNAPSHOT_BARRIER_SECONDS,
        "automatic_retry_count": 0,
        "fallback_count": 0,
        "parse_failures": parse_failures,
        "identity_failures": identity_failures,
        "pass_conditions": pass_conditions,
        "verdict": verdict,
        "force_kill_performed": False,
        "service_restart_performed": False,
        "settings_changed": False,
        "install_or_download_performed": False,
        "network_or_web_operation_performed": False,
        "image_or_container_mutation_performed": False,
        "materialization_performed": False,
        "preprocessing_performed": False,
        "training_performed": False,
        "evaluation_performed": False,
        "benchmark_admission_opened": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-handoff-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
        "verdict": verdict,
        "output_files": sorted(EXPECTED_OUTPUT_FILES),
        "next_gate": (
            "CENTRAL_ADMISSION_OBSERVATION_EVALUATION_NO_SCIENTIFIC_OR_TEST_GATE_OPEN"
            if verdict == PASS_VERDICT
            else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
        "pass_semantics": (
            "Admission observation packet complete for central evaluation only; "
            "no benchmark, materialization, scientific reproduction, or TEST access is opened."
        ),
        "truth_state": truth,
    }
    write_json(output_root / "command_receipts.json", command_document)
    write_json(output_root / "admission_observation.json", observation_document)
    write_json(output_root / "execution_receipt.json", execution_document)
    write_json(output_root / "handoff.json", handoff_document)
    entries = list(output_root.iterdir())
    if {entry.name for entry in entries} != EXPECTED_OUTPUT_FILES or not all(entry.is_file() for entry in entries):
        raise RuntimeError("exact output file set violated")
    _FAILURE_CONTEXT = None
    print(json.dumps({
        "verdict": verdict,
        "output_root": OUTPUT_RELATIVE.as_posix(),
        "commands_recorded": len(receipts),
        "automatic_retry_count": 0,
        "fallback_count": 0,
        "benchmark_admission_opened": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }, indent=2, allow_nan=False))
    return 0 if verdict == PASS_VERDICT else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            failure_packet_persisted = persist_failure_packet(type(exc).__name__, str(exc))
        except Exception:
            failure_packet_persisted = False
        print(json.dumps({
            "verdict": "HANDOFF_INCOMPLETE",
            "error_type": type(exc).__name__,
            "error_sha256": stable_error_hash(str(exc)),
            "failure_packet_persisted": failure_packet_persisted,
            "benchmark_admission_opened": False,
            "result_status": "NOT_RUN",
            "test_set_opened": "NO",
            "accepted_result_rows": 0,
        }, indent=2, allow_nan=False), file=sys.stderr)
        raise SystemExit(2)
