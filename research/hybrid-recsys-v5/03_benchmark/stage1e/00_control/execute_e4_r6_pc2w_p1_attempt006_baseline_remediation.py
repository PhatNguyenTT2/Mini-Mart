#!/usr/bin/env python3
"""Restore and verify the Attempt-006 native closed baseline exactly once.

This runner never starts Docker Desktop, queries the Docker daemon, retries,
materializes data, trains, evaluates, admits a benchmark, or opens TEST.  It
may issue one Docker Desktop stop and one WSL shutdown only when the immediate
native pre-baseline gate is not already closed.
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
from typing import Any

sys.dont_write_bytecode = True
import execute_e4_r6_pc2w_p1_attempt004_query_only as base


DOCKER = base.DOCKER
WSL = base.WSL
POWERSHELL = base.POWERSHELL
PYTHON = base.PYTHON
EXPECTED_EXECUTION_ROOT = base.EXPECTED_EXECUTION_ROOT
EXPECTED_EXECUTABLES = base.EXPECTED_EXECUTABLES

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt006_baseline_remediation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt006_baseline_remediation_contract.json"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt006_user_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt006_static_packet.py"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/"
    "E4_R6PC2W_P1_attempt006_baseline_remediation"
)
PACKET_PARENT = "c4d471a5ac5c9e763e66a1d7288367c5c905e1e9"
PACKET_RELATIVES = {
    AUTH_RELATIVE,
    CONTRACT_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
}
EXPECTED_HEAD_CHANGE_SET = {relative.as_posix() for relative in PACKET_RELATIVES}
EXPECTED_OUTPUT_FILES = {
    "command_receipts.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
    "runtime_inventory.json",
}
FROZEN_ATTEMPT005_SHA256 = {
    CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt005_instrumented_contract.json":
        "cf022505edcaba11e49a00e8b43e180796870679fa20647923ddba9158e5096b",
    CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt005_instrumented.py":
        "8e595d892a2548458b83c1cbbe1b332243c101554e21fa06ae725a198856e1e9",
    CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt005_static_packet.py":
        "8d2973fa7d119ecb0adb3b81f0c3f201dab181d87b092a40e622391359567d2c",
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt005_failure_receipt.json":
        "9e8432933c83e8ca4e8a40e189c85b9b076cd2f44a32fe844991c6b06646a0cf",
    CONTROL_RELATIVE / "pipeline_state_stage1e.json":
        "0e7865bc56efa78ec65e49c2b360aa41e1d2a3f499424944087900d6b1a0533a",
}
TARGET_PROCESS_NAMES = {
    "docker desktop",
    "com.docker.backend",
    "com.docker.build",
    "com.docker.proxy",
    "dockerd",
    "vpnkit",
    "wslrelay",
}
CONFIRMATION_TOKEN = "USER_CONFIRMED_EXACT_PROCESS_COMMAND_AFTER_STATIC_AUDIT"
SETTLING_SECONDS = 20
SNAPSHOT_BARRIER_SECONDS = 15
SNAPSHOT_LABELS = ["A", "B", "C"]
ERROR_CODES = {"NONE", "PROBE_EXCEPTION", "COMMAND_FAILED", "OUTPUT_MALFORMED"}
EXPECTED_COMMAND_IDS_WITH_REMEDIATION = [
    "B00", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09",
    "B10", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19",
]
EXPECTED_COMMAND_IDS_ALREADY_CLOSED = [
    "B00", "B01", "B02", "B03", "B04", "B07", "B08", "B09", "B10",
    "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19",
]
COMMAND_ARGV_TEMPLATES = {
    "DOCKER_DESKTOP_STATUS": ["DOCKER", "desktop", "status"],
    "DOCKER_DESKTOP_STOP": ["DOCKER", "desktop", "stop"],
    "WSL_VERBOSE": ["WSL", "--list", "--verbose"],
    "WSL_RUNNING": ["WSL", "--list", "--running", "--quiet"],
    "WSL_SHUTDOWN": ["WSL", "--shutdown"],
    "PROCESS_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "PROCESS_POPULATION_QUERY",
    ],
    "TCP_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "TCP_POPULATION_QUERY",
    ],
}


PROCESS_POPULATION_QUERY = r"""
$ErrorActionPreference='Stop'
function Get-ErrorTypeHash([string]$s){
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
try {
  $rows=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId -ErrorAction Stop |
    Where-Object {$target -contains $_.Name} |
    ForEach-Object {[pscustomobject]@{Name=([IO.Path]::GetFileNameWithoutExtension([string]$_.Name)).ToLowerInvariant();ProcessId=[uint32]$_.ProcessId}} |
    Sort-Object Name,ProcessId)
  [pscustomobject]@{Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';ErrorTypeHash=$null} | ConvertTo-Json -Depth 5 -Compress
} catch {
  [pscustomobject]@{Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';ErrorTypeHash=$(Get-ErrorTypeHash ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 5 -Compress
}
""".strip()


TCP_POPULATION_QUERY = r"""
$ErrorActionPreference='Stop'
function Get-ErrorTypeHash([string]$s){
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
try {
  $procs=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId -ErrorAction Stop | Where-Object {$target -contains $_.Name})
  $connections=@(Get-NetTCPConnection -ErrorAction Stop)
  $rows=@()
  foreach($p in @($procs | Sort-Object Name,ProcessId)){
    $owned=@($connections | Where-Object {[uint32]$_.OwningProcess -eq [uint32]$p.ProcessId})
    if($owned.Count -gt 0){
      $rows += [pscustomobject]@{Name=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant();ProcessId=[uint32]$p.ProcessId;ConnectionCount=[uint32]$owned.Count}
    }
  }
  [pscustomobject]@{Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';ErrorTypeHash=$null} | ConvertTo-Json -Depth 5 -Compress
} catch {
  [pscustomobject]@{Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';ErrorTypeHash=$(Get-ErrorTypeHash ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 5 -Compress
}
""".strip()


class DuplicateKeyError(ValueError):
    pass


_FAILURE_CONTEXT: dict[str, Any] | None = None


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result or key.casefold() in folded:
            raise DuplicateKeyError(key)
        result[key] = value
        folded[key.casefold()] = key
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def strict_json_text(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=strict_pairs,
        parse_constant=reject_nonfinite,
    )


def load_json(path: Path) -> dict[str, Any]:
    value = strict_json_text(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"non-object JSON root: {path.name}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_error_hash(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def git(repo_root: Path, *args: str) -> str:
    return base.git(repo_root, *args)


def git_blob_fact(repo_root: Path, revision: str, relative: Path) -> tuple[int, str]:
    return base.git_blob_fact(repo_root, revision, relative)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def material_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization Material Passport intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt006_baseline_remediation_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt006_baseline_remediation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt006_user_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt005_failure_receipt_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


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
    }
    return [replacements.get(token, token) for token in template]


def sanitized_receipt(receipt: dict[str, Any], kind: str) -> dict[str, Any]:
    argv = receipt.get("argv")
    argv_bytes = json.dumps(argv, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "command_id": receipt.get("command_id"),
        "command_kind": kind,
        "argv_sha256": sha256_bytes(argv_bytes),
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


def command_ok(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("exit_code") == 0
        and receipt.get("timed_out") is False
        and receipt.get("spawn_exception_type") is None
    )


def unavailable_population(error_code: str, label: str) -> dict[str, Any]:
    if error_code not in ERROR_CODES or error_code == "NONE":
        raise ValueError("invalid normalized population error code")
    return {
        "Available": False,
        "Count": 0,
        "Rows": [],
        "ErrorCode": error_code,
        "ErrorTypeHash": stable_error_hash(label),
    }


def validate_population_envelope(value: Any, kind: str) -> dict[str, Any]:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("population envelope field set mismatch")
    available = value["Available"]
    count = value["Count"]
    rows = value["Rows"]
    error_code = value["ErrorCode"]
    error_hash = value["ErrorTypeHash"]
    if not isinstance(available, bool):
        raise ValueError("population Available must be boolean")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("population Count must be a nonnegative integer")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("population Rows must be an array of objects")
    if count != len(rows):
        raise ValueError("population Count and Rows length mismatch")
    if error_code not in ERROR_CODES:
        raise ValueError("unknown population ErrorCode")
    if available:
        if error_code != "NONE" or error_hash is not None:
            raise ValueError("available population envelope error fields invalid")
    else:
        if error_code == "NONE" or not isinstance(error_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", error_hash):
            raise ValueError("unavailable population envelope error fields invalid")
        if count != 0 or rows:
            raise ValueError("unavailable population envelope must have empty population")
    row_fields = {"Name", "ProcessId"} if kind == "process" else {"Name", "ProcessId", "ConnectionCount"}
    seen_names: set[str] = set()
    for row in rows:
        if set(row) != row_fields:
            raise ValueError("population row field set mismatch")
        name = row.get("Name")
        process_id = row.get("ProcessId")
        if not isinstance(name, str) or name != name.casefold() or name not in TARGET_PROCESS_NAMES:
            raise ValueError("unexpected target population name")
        if name.casefold() in seen_names:
            raise ValueError("duplicate target population name")
        seen_names.add(name.casefold())
        if not isinstance(process_id, int) or isinstance(process_id, bool) or process_id <= 0:
            raise ValueError("invalid target population process id")
        if kind == "tcp":
            connection_count = row.get("ConnectionCount")
            if not isinstance(connection_count, int) or isinstance(connection_count, bool) or connection_count <= 0:
                raise ValueError("invalid TCP ownership connection count")
    expected_rows = sorted(rows, key=lambda row: (str(row["Name"]).casefold(), int(row["ProcessId"])))
    if rows != expected_rows:
        raise ValueError("population rows not in canonical order")
    return value


def parse_population_bytes(value: bytes, kind: str) -> dict[str, Any]:
    text, complete = base.native_gate.decode_output_strict(value)
    if not complete or not text.strip():
        raise ValueError("population output encoding or emptiness failure")
    parsed = strict_json_text(text)
    return validate_population_envelope(parsed, kind)


def population_evidence(
    receipt: dict[str, Any], stdout: bytes, kind: str
) -> tuple[dict[str, Any], bool]:
    if not command_ok(receipt):
        return unavailable_population("COMMAND_FAILED", f"{kind}:command_failed"), False
    try:
        return parse_population_bytes(stdout, kind), True
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
        return unavailable_population("OUTPUT_MALFORMED", f"{kind}:output_malformed"), False


def generic_unavailable(label: str, error_code: str) -> dict[str, Any]:
    return {
        "Available": False,
        "Rows": [],
        "ErrorCode": error_code,
        "ErrorTypeHash": stable_error_hash(label),
    }


def wsl_evidence(
    receipt: dict[str, Any], stdout: bytes, running_only: bool
) -> tuple[dict[str, Any], bool]:
    label = "wsl_running" if running_only else "wsl_verbose"
    if not command_ok(receipt):
        return generic_unavailable(f"{label}:command_failed", "COMMAND_FAILED"), False
    try:
        rows: list[Any] = (
            base.parse_wsl_running(stdout) if running_only else base.parse_wsl_list(stdout)
        )
        return {
            "Available": True,
            "Rows": rows,
            "ErrorCode": "NONE",
            "ErrorTypeHash": None,
        }, True
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return generic_unavailable(f"{label}:output_malformed", "OUTPUT_MALFORMED"), False


def pipe_evidence() -> tuple[dict[str, Any], bool]:
    probe = base.native_gate.probe_desktop_linux_pipe()
    error_type = probe.get("probe_exception_type")
    available = probe.get("available")
    win32_error = probe.get("win32_error")
    structurally_valid = (
        isinstance(available, bool)
        and (win32_error is None or isinstance(win32_error, int))
        and (error_type is None or isinstance(error_type, str))
    )
    return {
        "Available": available if isinstance(available, bool) else None,
        "Win32Error": win32_error if isinstance(win32_error, int) else None,
        "ErrorTypeHash": stable_error_hash(error_type) if isinstance(error_type, str) else None,
        "PipePathSha256": probe.get("pipe_path_sha256"),
        "RawPipePathPersisted": False,
    }, structurally_valid


def disk_evidence() -> tuple[dict[str, Any], bool]:
    try:
        snapshot = base.disk_snapshot()
        valid = (
            set(snapshot) == {"c", "e"}
            and all(
                isinstance(snapshot[drive].get("free_bytes"), int)
                and not isinstance(snapshot[drive].get("free_bytes"), bool)
                and snapshot[drive]["free_bytes"] >= 0
                for drive in ("c", "e")
            )
        )
        if not valid:
            raise ValueError("disk snapshot malformed")
        return {
            "Available": True,
            "Volumes": snapshot,
            "ErrorCode": "NONE",
            "ErrorTypeHash": None,
        }, True
    except Exception as exc:
        return {
            "Available": False,
            "Volumes": {"c": None, "e": None},
            "ErrorCode": "PROBE_EXCEPTION",
            "ErrorTypeHash": stable_error_hash(type(exc).__name__),
        }, False


def disk_gate(value: dict[str, Any], complete: bool) -> bool:
    volumes = value.get("Volumes")
    return bool(
        complete
        and value.get("Available") is True
        and isinstance(volumes, dict)
        and isinstance(volumes.get("c"), dict)
        and isinstance(volumes.get("e"), dict)
        and volumes["c"].get("free_bytes", -1) >= 20 * 1024**3
        and volumes["e"].get("free_bytes", -1) >= 50 * 1024**3
    )


def distro_state(rows: list[dict[str, Any]], name: str) -> str | None:
    return base.distro_state(rows, name)


def lane_result(
    wsl: dict[str, Any],
    wsl_complete: bool,
    running: dict[str, Any],
    running_complete: bool,
    pipe: dict[str, Any],
    pipe_complete: bool,
    processes: dict[str, Any],
    process_complete: bool,
    tcp: dict[str, Any],
    tcp_complete: bool,
    disk: dict[str, Any],
    disk_complete: bool,
) -> dict[str, bool]:
    wsl_rows = wsl.get("Rows") if wsl.get("Available") is True else None
    running_rows = running.get("Rows") if running.get("Available") is True else None
    parse_complete = all((
        wsl_complete,
        running_complete,
        pipe_complete,
        process_complete,
        tcp_complete,
        disk_complete,
        processes.get("Available") is True,
        tcp.get("Available") is True,
    ))
    return {
        "wsl_inventory_all_stopped": (
            isinstance(wsl_rows, list)
            and bool(wsl_rows)
            and all(row.get("state") == "Stopped" for row in wsl_rows)
        ),
        "docker_desktop_exactly_once_stopped": (
            isinstance(wsl_rows, list)
            and distro_state(wsl_rows, "docker-desktop") == "Stopped"
        ),
        "wsl_running_inventory_empty": running_rows == [],
        "desktop_linux_named_pipe_absent_win32_error_2": (
            pipe_complete
            and pipe.get("Available") is False
            and pipe.get("Win32Error") == 2
            and pipe.get("ErrorTypeHash") is None
        ),
        "target_process_population_empty": (
            process_complete
            and processes.get("Available") is True
            and processes.get("Count") == 0
            and processes.get("Rows") == []
        ),
        "target_tcp_ownership_population_empty": (
            tcp_complete
            and tcp.get("Available") is True
            and tcp.get("Count") == 0
            and tcp.get("Rows") == []
        ),
        "parse_and_completeness": parse_complete,
        "disk_thresholds_pass": disk_gate(disk, disk_complete),
    }


def packet_facts(repo_root: Path, head: str) -> list[dict[str, Any]]:
    return [
        {
            "path": relative.as_posix(),
            "git_blob_bytes": git_blob_fact(repo_root, head, relative)[0],
            "git_blob_sha256": git_blob_fact(repo_root, head, relative)[1],
        }
        for relative in sorted(PACKET_RELATIVES, key=lambda item: item.as_posix())
    ]


def failure_documents(
    context: dict[str, Any], error_type: str, error_hash: str
) -> dict[str, dict[str, Any]]:
    receipts = list(context["receipts"])
    command_ids = [str(receipt.get("command_id")) for receipt in receipts]
    stop_count = command_ids.count("B05")
    shutdown_count = command_ids.count("B06")
    common = {
        "verdict": "HANDOFF_INCOMPLETE",
        "error_type": error_type,
        "error_sha256": error_hash,
        "exception_message_persisted": False,
        "failure_receipt_is_progress_durable": True,
    }
    return {
        "command_receipts.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-command-receipts-1.0",
            "material_passport": context["material_passport"],
            "entry_checkpoint": context["entry_checkpoint"],
            "commands": receipts,
            "command_ids": command_ids,
            "automatic_retry_count": 0,
            "raw_argv_stdout_stderr_persisted": False,
            "failure": common,
        },
        "runtime_inventory.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-runtime-inventory-1.0",
            "material_passport": context["material_passport"],
            "entry_checkpoint": context["entry_checkpoint"],
            "evidence_state": "INCOMPLETE_FAIL_CLOSED",
            "observations": context.get("observations", {}),
            "raw_paths_command_lines_addresses_proxies_stdout_stderr_persisted": False,
            "failure": common,
        },
        "p1_execution_receipt.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-execution-receipt-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT006",
            "created_at": context["created_at"],
            "entry_checkpoint": context["entry_checkpoint"],
            "docker_desktop_start_attempts": 0,
            "docker_desktop_stop_attempts": stop_count,
            "wsl_shutdown_attempts": shutdown_count,
            "automatic_retry_count": 0,
            "materialization_performed": False,
            "training_performed": False,
            "evaluation_performed": False,
            "benchmark_admission_opened": False,
            "result_status": "NOT_RUN",
            "test_set_opened": "NO",
            "accepted_result_rows": 0,
            **common,
        },
        "p1_handoff.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-handoff-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT006",
            "verdict": "HANDOFF_INCOMPLETE",
            "output_files": sorted(EXPECTED_OUTPUT_FILES),
            "next_gate": "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY",
            "truth_state": {
                "RESULT_STATUS": "NOT_RUN",
                "TEST_SET_OPENED": "NO",
                "ACCEPTED_RESULT_ROWS": 0,
            },
            "failure": common,
        },
    }


def persist_failure_packet(error_type: str, error_text: str) -> bool:
    context = _FAILURE_CONTEXT
    if context is None:
        return False
    output_root = Path(context["output_root"])
    documents = failure_documents(context, error_type, stable_error_hash(error_text))
    for name in sorted(EXPECTED_OUTPUT_FILES):
        write_json(output_root / name, documents[name])
    entries = list(output_root.iterdir())
    if {path.name for path in entries} != EXPECTED_OUTPUT_FILES or not all(path.is_file() for path in entries):
        raise RuntimeError("durable failure packet exact file set violated")
    return True


def main() -> int:
    global _FAILURE_CONTEXT
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--execution-confirmation", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if repo_root != EXPECTED_EXECUTION_ROOT.resolve() or Path.cwd().resolve() != repo_root:
        raise RuntimeError("execution root or working directory mismatch")
    if args.execution_confirmation != CONFIRMATION_TOKEN:
        raise RuntimeError("separate post-audit exact-command confirmation missing")
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repository root mismatch")
    if Path(sys.executable).resolve() != PYTHON.resolve() or sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("interpreter identity mismatch")
    for executable, expected in EXPECTED_EXECUTABLES.items():
        if not executable.is_file() or base.file_fact(executable) != expected:
            raise RuntimeError("executable identity mismatch")

    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        raise RuntimeError("exact execution HEAD mismatch")
    parent_line = git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parent_line) != 2 or parent_line[1].casefold() != PACKET_PARENT:
        raise RuntimeError("packet parent mismatch")
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean")
    changed = set(filter(None, git(
        repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"
    ).splitlines()))
    if changed != EXPECTED_HEAD_CHANGE_SET:
        raise RuntimeError("packet commit exact four-file delta mismatch")
    expected_process_argv = [
        str(PYTHON.resolve()),
        str((repo_root / RUNNER_RELATIVE).resolve()),
        "--repo-root",
        str(repo_root),
        "--expected-head",
        head,
        "--execution-confirmation",
        CONFIRMATION_TOKEN,
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
        raise RuntimeError("immutable output root already exists")
    for relative, expected_sha256 in FROZEN_ATTEMPT005_SHA256.items():
        if git_blob_fact(repo_root, head, relative)[1] != expected_sha256:
            raise RuntimeError("Attempt-005 immutable artifact mismatch")

    contract = load_json(repo_root / CONTRACT_RELATIVE)
    authorization = load_json(repo_root / AUTH_RELATIVE)
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt006-baseline-remediation-contract-1.0":
        raise RuntimeError("Attempt-006 contract schema mismatch")
    if authorization.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt006-user-authorization-1.0":
        raise RuntimeError("Attempt-006 authorization schema mismatch")
    current_auth = authorization.get("current_authorization", {})
    if current_auth.get("packet_preparation_authorized") is not True:
        raise RuntimeError("packet preparation authority missing")
    if current_auth.get("execution_authorized") is not False:
        raise RuntimeError("pre-audit authorization truth widened")
    if current_auth.get("exact_process_command_confirmed") is not False:
        raise RuntimeError("authorization artifact must preserve pre-confirmation truth")
    if authorization.get("authorized_output_root_after_future_confirmation") != OUTPUT_RELATIVE.as_posix():
        raise RuntimeError("authorization output root mismatch")
    if contract.get("output_contract", {}).get("output_root") != OUTPUT_RELATIVE.as_posix():
        raise RuntimeError("contract output root mismatch")
    model_policy = authorization.get("model_policy", {})
    if model_policy != contract.get("model_policy"):
        raise RuntimeError("model policy mismatch")
    if (
        model_policy.get("requested_model") != "gpt-5.6-sol"
        or model_policy.get("requested_reasoning_effort") != "xhigh"
        or model_policy.get("requested_service_tier") != "default"
        or model_policy.get("fast_or_priority_allowed") is not False
    ):
        raise RuntimeError("Standard-only model policy mismatch")

    created_at = utc_now()
    passport = material_passport(created_at, authorization)
    receipts: list[dict[str, Any]] = []
    raw: dict[str, tuple[dict[str, Any], bytes, bytes]] = {}
    observations: dict[str, Any] = {}
    output_root.mkdir(parents=True, exist_ok=False)
    _FAILURE_CONTEXT = {
        "output_root": str(output_root),
        "created_at": created_at,
        "material_passport": passport,
        "entry_checkpoint": head,
        "receipts": receipts,
        "observations": observations,
    }
    persist_failure_packet("IN_PROGRESS", "Attempt-006 initialized before first command")

    def invoke(command_id: str, kind: str, timeout_seconds: int = 30) -> tuple[dict[str, Any], bytes, bytes]:
        argv = build_argv(kind)
        receipt, stdout, stderr = base.run_command(
            command_id, argv, timeout_seconds=timeout_seconds
        )
        receipts.append(sanitized_receipt(receipt, kind))
        raw[command_id] = (receipt, stdout, stderr)
        persist_failure_packet("IN_PROGRESS", f"Attempt-006 progress after {command_id}")
        return receipt, stdout, stderr

    pre_status_receipt, pre_status_stdout, pre_status_stderr = invoke(
        "B00", "DOCKER_DESKTOP_STATUS"
    )
    pre_wsl_receipt, pre_wsl_stdout, _ = invoke("B01", "WSL_VERBOSE")
    pre_running_receipt, pre_running_stdout, _ = invoke("B02", "WSL_RUNNING")
    pre_pipe, pre_pipe_complete = pipe_evidence()
    pre_process_receipt, pre_process_stdout, _ = invoke("B03", "PROCESS_POPULATION")
    pre_tcp_receipt, pre_tcp_stdout, _ = invoke("B04", "TCP_POPULATION")
    pre_disk, pre_disk_complete = disk_evidence()
    pre_wsl, pre_wsl_complete = wsl_evidence(pre_wsl_receipt, pre_wsl_stdout, False)
    pre_running, pre_running_complete = wsl_evidence(pre_running_receipt, pre_running_stdout, True)
    pre_process, pre_process_complete = population_evidence(
        pre_process_receipt, pre_process_stdout, "process"
    )
    pre_tcp, pre_tcp_complete = population_evidence(
        pre_tcp_receipt, pre_tcp_stdout, "tcp"
    )
    pre_lanes = lane_result(
        pre_wsl, pre_wsl_complete, pre_running, pre_running_complete,
        pre_pipe, pre_pipe_complete, pre_process, pre_process_complete,
        pre_tcp, pre_tcp_complete, pre_disk, pre_disk_complete,
    )
    observations["pre_baseline"] = {
        "docker_desktop_status_advisory": {
            "classification": base.native_gate.classify_status(
                pre_status_receipt, pre_status_stdout, pre_status_stderr
            ),
            "cannot_veto_or_admit": True,
        },
        "wsl_inventory": pre_wsl,
        "wsl_running_inventory": pre_running,
        "named_pipe": pre_pipe,
        "target_process_population": pre_process,
        "target_process_population_envelope_valid": pre_process_complete,
        "target_tcp_ownership_population": pre_tcp,
        "target_tcp_ownership_population_envelope_valid": pre_tcp_complete,
        "disk": pre_disk,
        "lanes": pre_lanes,
        "all_lanes_pass": all(pre_lanes.values()),
    }
    persist_failure_packet("IN_PROGRESS", "Attempt-006 pre-baseline observation complete")

    remediation_required = not all(pre_lanes.values())
    stop_receipt: dict[str, Any] | None = None
    shutdown_receipt: dict[str, Any] | None = None
    if remediation_required:
        try:
            stop_receipt, _, _ = invoke("B05", "DOCKER_DESKTOP_STOP", 180)
        finally:
            shutdown_receipt, _, _ = invoke("B06", "WSL_SHUTDOWN", 120)

    post_status_receipt, post_status_stdout, post_status_stderr = invoke(
        "B07", "DOCKER_DESKTOP_STATUS"
    )
    observations["remediation"] = {
        "required": remediation_required,
        "mode": "ONE_STOP_THEN_ONE_WSL_SHUTDOWN" if remediation_required else "ALREADY_CLOSED_ZERO_MUTATION",
        "docker_desktop_stop_attempts": 1 if stop_receipt is not None else 0,
        "docker_desktop_stop_success": stop_receipt is not None and command_ok(stop_receipt),
        "wsl_shutdown_attempts": 1 if shutdown_receipt is not None else 0,
        "wsl_shutdown_success": shutdown_receipt is not None and command_ok(shutdown_receipt),
        "docker_desktop_status_advisory_after": {
            "classification": base.native_gate.classify_status(
                post_status_receipt, post_status_stdout, post_status_stderr
            ),
            "cannot_veto_or_admit": True,
        },
    }
    persist_failure_packet("IN_PROGRESS", "Attempt-006 transition phase complete")

    time.sleep(SETTLING_SECONDS)

    def collect_snapshot(
        label: str,
        verbose_id: str,
        running_id: str,
        process_id: str,
        tcp_id: str,
    ) -> dict[str, Any]:
        wsl_receipt, wsl_stdout, _ = invoke(verbose_id, "WSL_VERBOSE")
        running_receipt, running_stdout, _ = invoke(running_id, "WSL_RUNNING")
        pipe, pipe_complete = pipe_evidence()
        process_receipt, process_stdout, _ = invoke(process_id, "PROCESS_POPULATION")
        tcp_receipt, tcp_stdout, _ = invoke(tcp_id, "TCP_POPULATION")
        disk, disk_complete = disk_evidence()
        wsl, wsl_complete = wsl_evidence(wsl_receipt, wsl_stdout, False)
        running, running_complete = wsl_evidence(running_receipt, running_stdout, True)
        processes, process_complete = population_evidence(
            process_receipt, process_stdout, "process"
        )
        tcp, tcp_complete = population_evidence(tcp_receipt, tcp_stdout, "tcp")
        lanes = lane_result(
            wsl, wsl_complete, running, running_complete, pipe, pipe_complete,
            processes, process_complete, tcp, tcp_complete, disk, disk_complete,
        )
        snapshot = {
            "label": label,
            "wsl_inventory": wsl,
            "wsl_running_inventory": running,
            "named_pipe": pipe,
            "target_process_population": processes,
            "target_process_population_envelope_valid": process_complete,
            "target_tcp_ownership_population": tcp,
            "target_tcp_ownership_population_envelope_valid": tcp_complete,
            "disk": disk,
            "lanes": lanes,
            "all_lanes_pass": all(lanes.values()),
        }
        persist_failure_packet("IN_PROGRESS", f"Attempt-006 snapshot {label} complete")
        return snapshot

    snapshot_a = collect_snapshot("A", "B08", "B09", "B10", "B11")
    time.sleep(SNAPSHOT_BARRIER_SECONDS)
    snapshot_b = collect_snapshot("B", "B12", "B13", "B14", "B15")
    time.sleep(SNAPSHOT_BARRIER_SECONDS)
    snapshot_c = collect_snapshot("C", "B16", "B17", "B18", "B19")
    snapshots = [snapshot_a, snapshot_b, snapshot_c]
    observations["post_baseline_snapshots"] = snapshots

    stable_keys = (
        "wsl_inventory",
        "wsl_running_inventory",
        "named_pipe",
        "target_process_population",
        "target_tcp_ownership_population",
    )
    snapshots_stable = all(
        snapshot_a[key] == snapshot_b[key] == snapshot_c[key]
        for key in stable_keys
    )
    pre_rows = pre_wsl.get("Rows") if pre_wsl.get("Available") is True else None
    closed_projection = (
        [
            {"name": row["name"], "state": "Stopped", "version": row["version"]}
            for row in pre_rows
        ]
        if isinstance(pre_rows, list) else None
    )
    final_rows = (
        snapshot_c["wsl_inventory"].get("Rows")
        if snapshot_c["wsl_inventory"].get("Available") is True else None
    )
    final_wsl_inventory_compatible = (
        isinstance(closed_projection, list)
        and bool(closed_projection)
        and final_rows == closed_projection
    )
    command_ids = [str(receipt.get("command_id")) for receipt in receipts]
    expected_ids = (
        EXPECTED_COMMAND_IDS_WITH_REMEDIATION
        if remediation_required else EXPECTED_COMMAND_IDS_ALREADY_CLOSED
    )
    transition_policy_pass = (
        (
            remediation_required
            and stop_receipt is not None
            and command_ok(stop_receipt)
            and shutdown_receipt is not None
            and command_ok(shutdown_receipt)
        )
        or (
            not remediation_required
            and stop_receipt is None
            and shutdown_receipt is None
        )
    )
    pass_conditions = {
        "pre_baseline_pass_or_single_remediation_path": transition_policy_pass,
        "exact_command_sequence_no_retry": command_ids == expected_ids,
        "three_snapshots_present": [snapshot["label"] for snapshot in snapshots] == SNAPSHOT_LABELS,
        "all_native_lanes_pass_in_all_snapshots": all(
            snapshot["all_lanes_pass"] for snapshot in snapshots
        ),
        "snapshots_stable": snapshots_stable,
        "final_wsl_inventory_closed_and_topology_compatible": final_wsl_inventory_compatible,
        "docker_desktop_start_attempts_zero": True,
        "docker_daemon_queries_zero": True,
        "automatic_retry_count_zero": True,
        "benchmark_admission_not_opened": True,
    }
    verdict = (
        "PASS_PC2W_P1_ATTEMPT006_BASELINE_REMEDIATED_READY_FOR_ADMISSION_PACKET"
        if all(pass_conditions.values())
        else "FAIL_CLOSED_PC2W_P1_ATTEMPT006_BASELINE_NOT_CLOSED"
    )
    packet_artifacts = packet_facts(repo_root, head)
    prior_artifacts = [
        {
            "path": relative.as_posix(),
            "git_blob_sha256": expected_sha256,
        }
        for relative, expected_sha256 in sorted(
            FROZEN_ATTEMPT005_SHA256.items(), key=lambda item: item[0].as_posix()
        )
    ]
    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-command-receipts-1.0",
        "material_passport": passport,
        "entry_checkpoint": head,
        "commands": receipts,
        "command_ids": command_ids,
        "exact_command_sequence": command_ids == expected_ids,
        "docker_desktop_start_attempts": 0,
        "docker_daemon_queries": 0,
        "automatic_retry_count": 0,
        "raw_argv_stdout_stderr_persisted": False,
    }
    inventory_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-runtime-inventory-1.0",
        "material_passport": passport,
        "entry_checkpoint": head,
        "pre_baseline": observations["pre_baseline"],
        "remediation": observations["remediation"],
        "post_baseline_snapshots": snapshots,
        "snapshots_stable": snapshots_stable,
        "final_wsl_inventory_closed_projection": closed_projection,
        "final_wsl_inventory_compatible": final_wsl_inventory_compatible,
        "docker_desktop_status_is_advisory_only": True,
        "rich_process_identity_required": False,
        "raw_paths_command_lines_addresses_proxies_stdout_stderr_persisted": False,
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-execution-receipt-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT006",
        "created_at": created_at,
        "entry_checkpoint": head,
        "packet_parent": PACKET_PARENT,
        "packet_artifacts": packet_artifacts,
        "attempt005_frozen_artifacts": prior_artifacts,
        "output_root": OUTPUT_RELATIVE.as_posix(),
        "baseline_mode": observations["remediation"]["mode"],
        "docker_desktop_start_attempts": 0,
        "docker_desktop_stop_attempts": command_ids.count("B05"),
        "wsl_shutdown_attempts": command_ids.count("B06"),
        "closure_snapshots": len(snapshots),
        "settling_seconds": SETTLING_SECONDS,
        "snapshot_barrier_seconds": SNAPSHOT_BARRIER_SECONDS,
        "automatic_retry_count": 0,
        "pass_conditions": pass_conditions,
        "verdict": verdict,
        "force_kill_performed": False,
        "service_restart_performed": False,
        "settings_changed": False,
        "install_or_download_performed": False,
        "network_operation_performed": False,
        "image_pull_build_create_run_performed": False,
        "materialization_performed": False,
        "training_performed": False,
        "evaluation_performed": False,
        "benchmark_admission_opened": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt006-handoff-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT006",
        "verdict": verdict,
        "attempt005_verdict_preserved": "FAIL_CLOSED_PC2W_P1_ATTEMPT005_CURRENT_HOST_NOT_ADMISSIBLE",
        "output_files": sorted(EXPECTED_OUTPUT_FILES),
        "next_gate": (
            "FRESH_INDEPENDENT_BASELINE_PACKET_AUDIT_BEFORE_ANY_ADMISSION_PACKET"
            if verdict.startswith("PASS_")
            else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
        "benchmark_admission_opened": False,
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
        },
    }
    write_json(output_root / "command_receipts.json", command_document)
    write_json(output_root / "runtime_inventory.json", inventory_document)
    write_json(output_root / "p1_execution_receipt.json", execution_document)
    write_json(output_root / "p1_handoff.json", handoff_document)
    entries = list(output_root.iterdir())
    if {path.name for path in entries} != EXPECTED_OUTPUT_FILES or not all(path.is_file() for path in entries):
        raise RuntimeError("exact output file set violated")
    _FAILURE_CONTEXT = None
    print(json.dumps({
        "verdict": verdict,
        "output_root": OUTPUT_RELATIVE.as_posix(),
        "commands_recorded": len(receipts),
        "automatic_retry_count": 0,
        "benchmark_admission_opened": False,
    }, indent=2, allow_nan=False))
    return 0 if verdict.startswith("PASS_") else 1


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
        }, indent=2, allow_nan=False), file=sys.stderr)
        raise SystemExit(2)
