#!/usr/bin/env python3
"""Run exactly one instrumented PC2W-P1 Attempt-005.

The runner performs a native pre-gate, at most one Docker Desktop start, one
synchronous Docker Desktop stop, exactly one authorized ``wsl --shutdown``
after the stop attempt, and three fixed fail-closed closure snapshots. It never
pulls/builds/runs a container, retries, materializes data, trains, evaluates, or
opens TEST.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
import execute_e4_r6_pc2w_p1_attempt004_query_only as base


DOCKER = base.DOCKER
DOCKER_DESKTOP = base.DOCKER_DESKTOP
WSL = base.WSL
POWERSHELL = base.POWERSHELL
PYTHON = base.PYTHON
EXPECTED_EXECUTION_ROOT = base.EXPECTED_EXECUTION_ROOT
EXPECTED_EXECUTABLES = base.EXPECTED_EXECUTABLES

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt005_instrumented.py"
BASE_RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt004_query_only.py"
NATIVE_HELPER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt005_user_authorization.json"
REQUIREMENTS_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt005_instrumented_contract.json"
POLICY_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_am/"
    "E4_R6PC2W_P1_residual_process_policy_review/"
    "prospective_residual_process_admission_policy.md"
)
POLICY_HANDOFF_RELATIVE = POLICY_RELATIVE.with_name("policy_review_handoff.json")
POLICY_VALIDATION_RELATIVE = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt.json"
)
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt005_dispatch.json"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_an/"
    "E4_R6PC2W_P1_attempt005_instrumented"
)
EXPECTED_HEAD_CHANGE_SET = {AUTH_RELATIVE.as_posix(), DISPATCH_RELATIVE.as_posix()}
EXPECTED_OUTPUT_FILES = {
    "command_receipts.json",
    "runtime_inventory.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
}
TARGET_PROCESS_NAMES = {
    "docker desktop.exe",
    "com.docker.backend.exe",
    "com.docker.build.exe",
    "com.docker.proxy.exe",
    "dockerd.exe",
    "vpnkit.exe",
    "wslrelay.exe",
}
POST_SHUTDOWN_SETTLING_SECONDS = 20
POST_SHUTDOWN_SNAPSHOT_BARRIER_SECONDS = 15
POST_SHUTDOWN_SNAPSHOTS = 3
EXPECTED_COORDINATOR_MODEL = "gpt-5.6-sol"
EXPECTED_COORDINATOR_REASONING = "max"
EXPECTED_STATIC_AUDIT_MODEL = "gpt-5.6-sol"
EXPECTED_STATIC_AUDIT_REASONING = "xhigh"
EXPECTED_SERVICE_TIER = "default"
_FAILURE_CONTEXT: dict[str, Any] | None = None
EXPECTED_COMMAND_IDS = [
    "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE",
    "A01_WSL_LIST_VERBOSE_PRE_GATE",
    "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE",
    "A03_TARGET_PROCESS_IDENTITY_PRE_GATE",
    "A04_TARGET_TCP_OWNERSHIP_PRE_GATE",
    "A05_WSL_VERSION_IDENTITY",
    "A06_WINDOWS_IDENTITY",
    "A07_DOCKER_DESKTOP_FILE_IDENTITY",
    "A08_DOCKER_DESKTOP_START_ONCE",
    "A09_DOCKER_DESKTOP_STATUS_ADVISORY_DURING",
    "A10_CONTAINER_LIST_INITIAL",
    "A11_IMAGE_LIST_INITIAL",
    "A12_DOCKER_VERSION",
    "A13_DOCKER_INFO",
    "A14_CONTEXT_INSPECT",
    "A15_SYSTEM_DF",
    "A16_WSL_LIST_VERBOSE_DURING",
    "A17_TARGET_PROCESS_IDENTITY_DURING",
    "A18_TARGET_TCP_OWNERSHIP_DURING",
    "A19_CONTAINER_LIST_FINAL",
    "A20_IMAGE_LIST_FINAL",
    "A21_DOCKER_EVENTS_BEFORE_STOP",
    "A22_DOCKER_DESKTOP_STOP_ONCE",
    "A23_WSL_SHUTDOWN_ONCE",
    "A24_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER",
    "A25_WSL_LIST_VERBOSE_POST_A",
    "A26_WSL_LIST_RUNNING_QUIET_POST_A",
    "A27_TARGET_PROCESS_IDENTITY_POST_A",
    "A28_TARGET_TCP_OWNERSHIP_POST_A",
    "A29_WSL_LIST_VERBOSE_POST_B",
    "A30_WSL_LIST_RUNNING_QUIET_POST_B",
    "A31_TARGET_PROCESS_IDENTITY_POST_B",
    "A32_TARGET_TCP_OWNERSHIP_POST_B",
    "A33_WSL_LIST_VERBOSE_POST_C",
    "A34_WSL_LIST_RUNNING_QUIET_POST_C",
    "A35_TARGET_PROCESS_IDENTITY_POST_C",
    "A36_TARGET_TCP_OWNERSHIP_POST_C",
]


PROCESS_IDENTITY_QUERY = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Require-NonEmpty($value,[string]$label){
  if([string]::IsNullOrWhiteSpace([string]$value)){throw "missing required identity field: $label"}
}
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
try {
  $all=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId,ParentProcessId,ExecutablePath,CreationDate,CommandLine -ErrorAction Stop)
  $byPid=@{}
  foreach($x in $all){$byPid[[uint32]$x.ProcessId]=$x}
  $rows=@()
  foreach($p in @($all | Where-Object {$target -contains $_.Name} | Sort-Object ProcessId)){
    $path=[string]$p.ExecutablePath
    $parent=$byPid[[uint32]$p.ParentProcessId]
    if($null -eq $parent){throw 'parent process identity unavailable'}
    $parentName=[string]$parent.Name
    $parentPath=[string]$parent.ExecutablePath
    Require-NonEmpty $path 'ExecutablePath'
    Require-NonEmpty $parentName 'ParentName'
    Require-NonEmpty $parentPath 'ParentExecutablePath'
    Require-NonEmpty ([string]$p.CommandLine) 'CommandLine'
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw 'target executable path is not a file'}
    $fileHash=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    $sig=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
    $sigStatus=[string]$sig.Status
    $signerSubject=[string]$sig.SignerCertificate.Subject
    $fileVersion=[string](Get-Item -LiteralPath $path -ErrorAction Stop).VersionInfo.FileVersion
    $created=([datetime]$p.CreationDate).ToUniversalTime().ToString('o')
    Require-NonEmpty $fileHash 'ExecutableFileSha256'
    Require-NonEmpty $sigStatus 'AuthenticodeStatus'
    Require-NonEmpty $signerSubject 'SignerSubject'
    Require-NonEmpty $fileVersion 'FileVersion'
    Require-NonEmpty $created 'CreationTimeUtc'
    $rows += [pscustomobject]@{
      Name=[IO.Path]::GetFileNameWithoutExtension([string]$p.Name)
      ProcessId=[uint32]$p.ProcessId
      ParentProcessId=[uint32]$p.ParentProcessId
      ParentNameHash=$(Get-RedactedSha256 $parentName)
      ParentExecutablePathHash=$(Get-RedactedSha256 $parentPath)
      ExecutablePathHash=$(Get-RedactedSha256 $path)
      ExecutableFileSha256=$fileHash
      FileVersion=$fileVersion
      AuthenticodeStatus=$sigStatus
      SignerSubjectHash=$(Get-RedactedSha256 $signerSubject)
      CreationTimeUtc=$created
      CommandLineHash=$(Get-RedactedSha256 ([string]$p.CommandLine))
    }
  }
  [pscustomobject]@{Available=$true;ProcessCount=$rows.Count;Rows=$rows} | ConvertTo-Json -Depth 7 -Compress
} catch {
  [pscustomobject]@{Available=$false;ProcessCount=$null;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName));Rows=@()} | ConvertTo-Json -Depth 7 -Compress
}
""".strip()


TCP_OWNERSHIP_QUERY = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Require-NonEmpty($value,[string]$label){
  if([string]::IsNullOrWhiteSpace([string]$value)){throw "missing required TCP field: $label"}
}
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
try {
  $procs=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId -ErrorAction Stop | Where-Object {$target -contains $_.Name})
  $ids=@($procs | ForEach-Object {[uint32]$_.ProcessId})
  $rows=@()
  if($ids.Count -gt 0){
    foreach($c in @(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids -contains [uint32]$_.OwningProcess} | Sort-Object OwningProcess,LocalPort,RemotePort)){
      Require-NonEmpty ([string]$c.State) 'State'
      Require-NonEmpty ([string]$c.LocalAddress) 'LocalAddress'
      Require-NonEmpty ([string]$c.RemoteAddress) 'RemoteAddress'
      $rows += [pscustomobject]@{
        State=[string]$c.State
        LocalAddressHash=$(Get-RedactedSha256 ([string]$c.LocalAddress))
        LocalPort=[uint16]$c.LocalPort
        RemoteAddressHash=$(Get-RedactedSha256 ([string]$c.RemoteAddress))
        RemotePort=[uint16]$c.RemotePort
        OwningProcess=[uint32]$c.OwningProcess
      }
    }
  }
  [pscustomobject]@{Available=$true;ConnectionCount=$rows.Count;Rows=$rows} | ConvertTo-Json -Depth 6 -Compress
} catch {
  [pscustomobject]@{Available=$false;ConnectionCount=$null;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName));Rows=@()} | ConvertTo-Json -Depth 6 -Compress
}
""".strip()


def load_json(path: Path) -> dict[str, Any]:
    return base.load_json(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo_root: Path, *args: str) -> str:
    return base.git(repo_root, *args)


def git_blob_fact(repo_root: Path, revision: str, relative: Path) -> tuple[int, str]:
    return base.git_blob_fact(repo_root, revision, relative)


def file_fact(path: Path) -> tuple[int, str]:
    return base.file_fact(path)


def command_ok(receipt: dict[str, Any]) -> bool:
    return base.command_ok(receipt)


def parse_probe(value: bytes, *, count_key: str) -> dict[str, Any]:
    parsed = base.parse_json_output(value)
    if not isinstance(parsed, dict) or parsed.get("Available") is not True:
        raise ValueError("instrumented probe unavailable")
    rows = parsed.get("Rows")
    if rows is None:
        rows = []
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("instrumented probe rows malformed")
    if parsed.get(count_key) != len(rows):
        raise ValueError("instrumented probe count mismatch")
    return {"available": True, "count": len(rows), "rows": rows}


def parse_process_probe(value: bytes) -> dict[str, Any]:
    result = parse_probe(value, count_key="ProcessCount")
    required = {
        "Name", "ProcessId", "ParentProcessId", "ParentNameHash",
        "ParentExecutablePathHash", "ExecutablePathHash", "ExecutableFileSha256",
        "FileVersion", "AuthenticodeStatus", "SignerSubjectHash",
        "CreationTimeUtc", "CommandLineHash",
    }
    for row in result["rows"]:
        if set(row) != required:
            raise ValueError("process identity field set mismatch")
        if str(row.get("Name", "")).casefold() + ".exe" not in TARGET_PROCESS_NAMES:
            raise ValueError("unexpected target process name")
        if any(
            not isinstance(row.get(key), str) or not row.get(key).strip()
            for key in ("Name", "FileVersion", "AuthenticodeStatus", "CreationTimeUtc")
        ):
            raise ValueError("missing process identity string")
        if any(
            not isinstance(row.get(key), int)
            or isinstance(row.get(key), bool)
            or row.get(key) <= 0
            for key in ("ProcessId", "ParentProcessId")
        ):
            raise ValueError("invalid process identity integer")
        for key in (
            "ParentNameHash", "ParentExecutablePathHash", "ExecutablePathHash",
            "ExecutableFileSha256", "SignerSubjectHash", "CommandLineHash",
        ):
            if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError(f"invalid process identity hash: {key}")
        try:
            datetime.fromisoformat(row["CreationTimeUtc"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid process creation time") from exc
    return result


def parse_tcp_probe(value: bytes) -> dict[str, Any]:
    result = parse_probe(value, count_key="ConnectionCount")
    required = {
        "State", "LocalAddressHash", "LocalPort", "RemoteAddressHash",
        "RemotePort", "OwningProcess",
    }
    if any(set(row) != required for row in result["rows"]):
        raise ValueError("TCP ownership field set mismatch")
    for row in result["rows"]:
        if not isinstance(row.get("State"), str) or not row["State"].strip():
            raise ValueError("missing TCP state")
        for key in ("LocalAddressHash", "RemoteAddressHash"):
            if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError(f"invalid TCP address hash: {key}")
        for key in ("LocalPort", "RemotePort"):
            value = row.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 65535:
                raise ValueError(f"invalid TCP port: {key}")
        owner = row.get("OwningProcess")
        if not isinstance(owner, int) or isinstance(owner, bool) or owner <= 0:
            raise ValueError("invalid TCP owning process")
    return result


def parse_if_success(
    command_id: str,
    by_id: dict[str, dict[str, Any]],
    raw: dict[str, tuple[bytes, bytes]],
    parser: Callable[[bytes], Any],
    failures: list[str],
) -> Any:
    return base.parse_if_success(command_id, by_id, raw, parser, failures)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _failure_documents(
    context: dict[str, Any], *, error_type: str, error_sha256: str
) -> dict[str, dict[str, Any]]:
    receipts = list(context["receipts"])
    command_ids = [str(row.get("command_id")) for row in receipts]
    material_passport = context["material_passport"]
    entry_checkpoint = context["entry_checkpoint"]
    runner_checkpoint = context["runner_checkpoint"]
    attempts = {
        "startup_attempts": command_ids.count("A08_DOCKER_DESKTOP_START_ONCE"),
        "docker_stop_attempts": command_ids.count("A22_DOCKER_DESKTOP_STOP_ONCE"),
        "wsl_shutdown_attempts": command_ids.count("A23_WSL_SHUTDOWN_ONCE"),
    }
    common_failure = {
        "verdict": "HANDOFF_INCOMPLETE",
        "error_type": error_type,
        "error_sha256": error_sha256,
        "exception_message_persisted": False,
        "failure_receipt_is_progress_durable": True,
    }
    return {
        "command_receipts.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-command-receipts-1.0",
            "material_passport": material_passport,
            "entry_checkpoint": entry_checkpoint,
            "runner_checkpoint": runner_checkpoint,
            "commands": receipts,
            "command_ids": command_ids,
            "exact_command_sequence": False,
            "automatic_retry_count": 0,
            "raw_stdout_or_stderr_persisted": False,
            "raw_process_paths_or_command_lines_persisted": False,
            "raw_network_addresses_persisted": False,
            "failure": common_failure,
        },
        "runtime_inventory.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-runtime-inventory-1.0",
            "material_passport": material_passport,
            "entry_checkpoint": entry_checkpoint,
            "evidence_state": "INCOMPLETE_FAIL_CLOSED",
            "commands_observed": command_ids,
            "docker_client_version_whitelist": None,
            "docker_server_version_whitelist": None,
            "docker_info_whitelist": None,
            "raw_or_secret_bearing_runtime_output_persisted": False,
            "failure": common_failure,
        },
        "p1_execution_receipt.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-execution-receipt-1.0",
            "material_passport": material_passport,
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT005",
            "created_at": context["created_at"],
            "entry_checkpoint": entry_checkpoint,
            "runner_checkpoint": runner_checkpoint,
            **attempts,
            "automatic_retry_count": 0,
            "force_kill_performed": False,
            "service_restart_performed": False,
            "settings_changed": False,
            "image_pull_or_build_performed": False,
            "container_create_or_run_performed": False,
            "install_or_download_performed": False,
            "materialization_performed": False,
            "scientific_execution_performed": False,
            "result_status": "NOT_RUN",
            "test_set_opened": "NO",
            "accepted_result_rows": 0,
            **common_failure,
        },
        "p1_handoff.json": {
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-handoff-1.0",
            "material_passport": material_passport,
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT005",
            "verdict": "HANDOFF_INCOMPLETE",
            "output_files": sorted(EXPECTED_OUTPUT_FILES),
            "next_gate": "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY",
            "truth_state": {
                "RESULT_STATUS": "NOT_RUN",
                "TEST_SET_OPENED": "NO",
                "ACCEPTED_RESULT_ROWS": 0,
            },
            "failure": common_failure,
        },
    }


def persist_failure_packet(error_type: str, error_text: str) -> bool:
    context = _FAILURE_CONTEXT
    if context is None:
        return False
    output_root = Path(context["output_root"])
    error_sha256 = hashlib.sha256(error_text.encode("utf-8")).hexdigest()
    documents = _failure_documents(
        context, error_type=error_type, error_sha256=error_sha256
    )
    for name in sorted(EXPECTED_OUTPUT_FILES):
        write_json(output_root / name, documents[name])
    entries = list(output_root.iterdir())
    if {path.name for path in entries} != EXPECTED_OUTPUT_FILES:
        raise RuntimeError("durable failure packet exact file set violated")
    return True


def passport(created_at: str, auth: dict[str, Any]) -> dict[str, Any]:
    intake = auth.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt005_instrumented_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt005_user_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt005_instrumented_contract_v1",
            "stage1e_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def main() -> int:
    global _FAILURE_CONTEXT
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if repo_root != EXPECTED_EXECUTION_ROOT.resolve():
        raise RuntimeError("execution is bound to the central repository root")
    if Path.cwd().resolve() != repo_root:
        raise RuntimeError("working directory mismatch")
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repository root mismatch")
    if Path(sys.executable).resolve() != PYTHON.resolve() or sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("interpreter identity mismatch")
    for executable, expected in EXPECTED_EXECUTABLES.items():
        if not executable.is_file() or file_fact(executable) != expected:
            raise RuntimeError(f"executable identity mismatch: {executable}")

    output_root = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_root.exists():
        raise RuntimeError(f"immutable output root already exists: {output_root}")
    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        raise RuntimeError("exact execution HEAD mismatch")
    expected_process_argv = [
        str(PYTHON.resolve()), str((repo_root / RUNNER_RELATIVE).resolve()),
        "--repo-root", str(repo_root), "--expected-head", head,
    ]
    original = list(getattr(sys, "orig_argv", []))
    actual_process_argv = (
        [str(Path(original[0]).resolve()), str(Path(original[1]).resolve()), *original[2:]]
        if len(original) >= 2 else original
    )
    if actual_process_argv != expected_process_argv:
        raise RuntimeError("exact original process argv mismatch")
    parent_line = git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parent_line) != 2:
        raise RuntimeError("execution checkpoint must have exactly one parent")
    parent = parent_line[1].casefold()
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean")
    changed = set(filter(None, git(
        repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"
    ).splitlines()))
    if changed != EXPECTED_HEAD_CHANGE_SET:
        raise RuntimeError(f"execution checkpoint change set mismatch: {sorted(changed)}")

    auth = load_json(repo_root / AUTH_RELATIVE)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    dispatch = load_json(repo_root / DISPATCH_RELATIVE)
    policy_handoff = load_json(repo_root / POLICY_HANDOFF_RELATIVE)
    policy_validation = load_json(repo_root / POLICY_VALIDATION_RELATIVE)
    if auth.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt005-user-authorization-1.0":
        raise RuntimeError("Attempt-005 authorization schema mismatch")
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt005-instrumented-contract-1.0":
        raise RuntimeError("Attempt-005 contract schema mismatch")
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt005-dispatch-1.0":
        raise RuntimeError("Attempt-005 dispatch schema mismatch")
    if policy_handoff.get("verdict") != "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED":
        raise RuntimeError("residual-process policy verdict missing")
    if policy_validation.get("verdict") != "PASS_PC2W_P1_RESIDUAL_PROCESS_POLICY_REVIEW_VALIDATED":
        raise RuntimeError("residual-process policy validation missing")
    if dispatch.get("runner_checkpoint", "").casefold() != parent:
        raise RuntimeError("dispatch runner checkpoint mismatch")
    if auth.get("entry_checkpoint", "").casefold() != parent:
        raise RuntimeError("authorization runner checkpoint mismatch")
    if auth.get("authorized_output_root") != str(output_root):
        raise RuntimeError("authorization output root mismatch")
    binding = dispatch.get("execution_binding", {})
    if binding.get("output_root") != str(output_root):
        raise RuntimeError("dispatch output root mismatch")
    if binding.get("working_directory") != str(repo_root):
        raise RuntimeError("dispatch working directory mismatch")
    if binding.get("expected_output_files") != sorted(EXPECTED_OUTPUT_FILES):
        raise RuntimeError("dispatch output file set mismatch")
    expected_dispatch_argv = [
        str(PYTHON), RUNNER_RELATIVE.as_posix(), "--repo-root", str(repo_root),
        "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    if binding.get("argv") != expected_dispatch_argv:
        raise RuntimeError("dispatch argv mismatch")
    model = dispatch.get("model_policy", {})
    expected_model_binding = {
        "coordinator_model": EXPECTED_COORDINATOR_MODEL,
        "coordinator_reasoning_effort": EXPECTED_COORDINATOR_REASONING,
        "static_audit_model": EXPECTED_STATIC_AUDIT_MODEL,
        "static_audit_reasoning_effort": EXPECTED_STATIC_AUDIT_REASONING,
        "service_tier": EXPECTED_SERVICE_TIER,
        "fast_or_priority_allowed": False,
    }
    if model != expected_model_binding:
        raise RuntimeError("dispatch model policy is not Standard-only")

    decision = auth.get("user_decision", {})
    required_true = (
        "one_docker_desktop_start_authorized",
        "one_docker_desktop_stop_authorized",
        "one_wsl_shutdown_after_stop_authorized",
        "three_instrumented_closure_snapshots_authorized",
        "query_only_runtime_inventory_authorized",
    )
    if decision.get("decision") != "AUTHORIZE_ATTEMPT005_INSTRUMENTED_CURRENT_HOST":
        raise RuntimeError("Attempt-005 decision missing")
    if any(decision.get(key) is not True for key in required_true):
        raise RuntimeError("Attempt-005 required authority missing")
    required_false = (
        "automatic_retry_authorized", "force_kill_authorized",
        "service_restart_authorized", "settings_change_authorized",
        "image_pull_or_build_authorized", "container_create_or_run_authorized",
        "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
        "materialization_authorized", "training_authorized",
        "evaluation_authorized", "benchmark_admission_authorized",
        "test_access_authorized",
    )
    if any(decision.get(key) is not False for key in required_false):
        raise RuntimeError("Attempt-005 fail-closed authority widened")

    frozen_rows = dispatch.get("frozen_artifacts")
    expected_paths = {
        RUNNER_RELATIVE, BASE_RUNNER_RELATIVE, NATIVE_HELPER_RELATIVE,
        AUTH_RELATIVE, REQUIREMENTS_RELATIVE, CONTRACT_RELATIVE,
        POLICY_RELATIVE, POLICY_HANDOFF_RELATIVE, POLICY_VALIDATION_RELATIVE,
    }
    frozen_map = {
        Path(str(row.get("path"))): row
        for row in frozen_rows or [] if isinstance(row, dict)
    }
    if set(frozen_map) != expected_paths:
        raise RuntimeError("dispatch frozen artifact path set mismatch")
    for relative, row in frozen_map.items():
        if git_blob_fact(repo_root, head, relative) != (
            row.get("git_blob_bytes"), row.get("git_blob_sha256")
        ):
            raise RuntimeError(f"frozen artifact mismatch: {relative.as_posix()}")
    for relative in (RUNNER_RELATIVE, CONTRACT_RELATIVE):
        if git_blob_fact(repo_root, parent, relative) != file_fact(repo_root / relative):
            raise RuntimeError(f"runner checkpoint drift: {relative.as_posix()}")

    created_at = utc_now()
    material_passport = passport(created_at, auth)
    receipts: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}
    output_root.mkdir(parents=True, exist_ok=False)
    _FAILURE_CONTEXT = {
        "output_root": str(output_root),
        "created_at": created_at,
        "material_passport": material_passport,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "receipts": receipts,
    }
    persist_failure_packet("IN_PROGRESS", "Attempt-005 initialized before first command")

    def invoke(command_id: str, argv: list[str], timeout_seconds: int = 30) -> dict[str, Any]:
        if not base.docker_subcommand_is_allowed(argv):
            raise RuntimeError(f"prohibited Docker command: {argv}")
        receipt, stdout, stderr = base.run_command(
            command_id, argv, timeout_seconds=timeout_seconds
        )
        receipts.append(receipt)
        raw[command_id] = (stdout, stderr)
        persist_failure_packet("IN_PROGRESS", f"Attempt-005 progress after {command_id}")
        return receipt

    process_argv = [
        str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
        "-Command", PROCESS_IDENTITY_QUERY,
    ]
    tcp_argv = [
        str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
        "-Command", TCP_OWNERSHIP_QUERY,
    ]
    before_disk = base.disk_snapshot()
    invoke("A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE", [str(DOCKER), "desktop", "status"])
    invoke("A01_WSL_LIST_VERBOSE_PRE_GATE", [str(WSL), "--list", "--verbose"])
    invoke("A02_WSL_LIST_RUNNING_QUIET_PRE_GATE", [str(WSL), "--list", "--running", "--quiet"])
    pre_pipe = base.native_gate.probe_desktop_linux_pipe()
    invoke("A03_TARGET_PROCESS_IDENTITY_PRE_GATE", process_argv)
    invoke("A04_TARGET_TCP_OWNERSHIP_PRE_GATE", tcp_argv)
    invoke("A05_WSL_VERSION_IDENTITY", [str(WSL), "--version"])
    invoke("A06_WINDOWS_IDENTITY", [
        str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture | ConvertTo-Json -Depth 3 -Compress",
    ])
    invoke("A07_DOCKER_DESKTOP_FILE_IDENTITY", [
        str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "$f=Get-Item -LiteralPath 'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe'; [pscustomobject]@{FullName=$f.FullName;Length=$f.Length;FileVersion=$f.VersionInfo.FileVersion;ProductVersion=$f.VersionInfo.ProductVersion} | ConvertTo-Json -Depth 3 -Compress",
    ])

    by_id = {row["command_id"]: row for row in receipts}
    failures: list[str] = []
    before_wsl = parse_if_success(
        "A01_WSL_LIST_VERBOSE_PRE_GATE", by_id, raw, base.parse_wsl_list, failures
    ) or []
    before_running = parse_if_success(
        "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE", by_id, raw, base.parse_wsl_running, failures
    )
    before_processes = parse_if_success(
        "A03_TARGET_PROCESS_IDENTITY_PRE_GATE", by_id, raw, parse_process_probe, failures
    )
    before_tcp = parse_if_success(
        "A04_TARGET_TCP_OWNERSHIP_PRE_GATE", by_id, raw, parse_tcp_probe, failures
    )
    wsl_version = parse_if_success(
        "A05_WSL_VERSION_IDENTITY", by_id, raw, base.parse_wsl_version, failures
    ) or {}
    windows_identity = parse_if_success(
        "A06_WINDOWS_IDENTITY", by_id, raw, base.parse_json_output, failures
    ) or {}
    docker_identity = parse_if_success(
        "A07_DOCKER_DESKTOP_FILE_IDENTITY", by_id, raw, base.parse_json_output, failures
    ) or {}
    pre_gate = {
        "wsl_verbose_all_stopped": bool(before_wsl) and all(row.get("state") == "Stopped" for row in before_wsl),
        "docker_desktop_distro_exactly_stopped": base.native_gate.distro_state(before_wsl, "docker-desktop") == "Stopped",
        "wsl_running_inventory_empty": before_running == [],
        "desktop_linux_named_pipe_absent_win32_error_2": base.native_gate.pipe_is_specifically_absent(pre_pipe),
        "target_process_population_empty": isinstance(before_processes, dict) and before_processes.get("count") == 0,
        "target_tcp_population_empty": isinstance(before_tcp, dict) and before_tcp.get("count") == 0,
        "identity_payloads_complete": (
            bool(wsl_version.get("wsl_version"))
            and bool(wsl_version.get("kernel_version"))
            and all(windows_identity.get(k) for k in ("Caption", "Version", "BuildNumber", "OSArchitecture"))
            and docker_identity.get("FullName") == str(DOCKER_DESKTOP)
            and docker_identity.get("Length") == DOCKER_DESKTOP.stat().st_size
        ),
        "parse_failures_absent": not failures,
        "disk_thresholds_before_pass": (
            before_disk["c"]["free_bytes"] >= 20 * 1024**3
            and before_disk["e"]["free_bytes"] >= 50 * 1024**3
        ),
    }

    started = False
    start_receipt: dict[str, Any] | None = None
    stop_receipt: dict[str, Any] | None = None
    shutdown_receipt: dict[str, Any] | None = None
    event_since = utc_now()
    try:
        if all(pre_gate.values()):
            started = True
            start_receipt = invoke(
                "A08_DOCKER_DESKTOP_START_ONCE", [str(DOCKER), "desktop", "start"], 180
            )
            if command_ok(start_receipt):
                queries = [
                    ("A09_DOCKER_DESKTOP_STATUS_ADVISORY_DURING", [str(DOCKER), "desktop", "status"]),
                    ("A10_CONTAINER_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("A11_IMAGE_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                    ("A12_DOCKER_VERSION", [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .}}"]),
                    ("A13_DOCKER_INFO", [str(DOCKER), "--context", "desktop-linux", "info", "--format", "{{json .}}"]),
                    ("A14_CONTEXT_INSPECT", [str(DOCKER), "context", "inspect", "desktop-linux"]),
                    ("A15_SYSTEM_DF", [str(DOCKER), "--context", "desktop-linux", "system", "df", "--format", "{{json .}}"]),
                    ("A16_WSL_LIST_VERBOSE_DURING", [str(WSL), "--list", "--verbose"]),
                    ("A17_TARGET_PROCESS_IDENTITY_DURING", process_argv),
                    ("A18_TARGET_TCP_OWNERSHIP_DURING", tcp_argv),
                    ("A19_CONTAINER_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("A20_IMAGE_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                ]
                for command_id, argv in queries:
                    invoke(command_id, argv)
                invoke("A21_DOCKER_EVENTS_BEFORE_STOP", [
                    str(DOCKER), "--context", "desktop-linux", "events",
                    "--since", event_since, "--until", utc_now(), "--format", "{{json .}}",
                ])
    finally:
        if started:
            try:
                stop_receipt = invoke(
                    "A22_DOCKER_DESKTOP_STOP_ONCE", [str(DOCKER), "desktop", "stop"], 180
                )
            finally:
                shutdown_receipt = invoke(
                    "A23_WSL_SHUTDOWN_ONCE", [str(WSL), "--shutdown"], 120
                )

    invoke("A24_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER", [str(DOCKER), "desktop", "status"])
    time.sleep(POST_SHUTDOWN_SETTLING_SECONDS)
    snapshot_specs = [
        ("A", "A25_WSL_LIST_VERBOSE_POST_A", "A26_WSL_LIST_RUNNING_QUIET_POST_A", "A27_TARGET_PROCESS_IDENTITY_POST_A", "A28_TARGET_TCP_OWNERSHIP_POST_A"),
        ("B", "A29_WSL_LIST_VERBOSE_POST_B", "A30_WSL_LIST_RUNNING_QUIET_POST_B", "A31_TARGET_PROCESS_IDENTITY_POST_B", "A32_TARGET_TCP_OWNERSHIP_POST_B"),
        ("C", "A33_WSL_LIST_VERBOSE_POST_C", "A34_WSL_LIST_RUNNING_QUIET_POST_C", "A35_TARGET_PROCESS_IDENTITY_POST_C", "A36_TARGET_TCP_OWNERSHIP_POST_C"),
    ]
    pipe_probes: dict[str, dict[str, Any]] = {}
    for index, (label, verbose_id, running_id, process_id, tcp_id) in enumerate(snapshot_specs):
        if index:
            time.sleep(POST_SHUTDOWN_SNAPSHOT_BARRIER_SECONDS)
        invoke(verbose_id, [str(WSL), "--list", "--verbose"])
        invoke(running_id, [str(WSL), "--list", "--running", "--quiet"])
        pipe_probes[label] = base.native_gate.probe_desktop_linux_pipe()
        invoke(process_id, process_argv)
        invoke(tcp_id, tcp_argv)

    after_disk = base.disk_snapshot()
    by_id = {row["command_id"]: row for row in receipts}
    version_data = parse_if_success("A12_DOCKER_VERSION", by_id, raw, base.parse_json_output, failures) or {}
    info_data = parse_if_success("A13_DOCKER_INFO", by_id, raw, base.parse_json_output, failures) or {}
    context_data = parse_if_success("A14_CONTEXT_INSPECT", by_id, raw, base.parse_json_output, failures)
    system_df_raw = parse_if_success("A15_SYSTEM_DF", by_id, raw, base.parse_json_lines, failures) or []
    during_wsl = parse_if_success("A16_WSL_LIST_VERBOSE_DURING", by_id, raw, base.parse_wsl_list, failures) or []
    during_processes = parse_if_success("A17_TARGET_PROCESS_IDENTITY_DURING", by_id, raw, parse_process_probe, failures)
    during_tcp = parse_if_success("A18_TARGET_TCP_OWNERSHIP_DURING", by_id, raw, parse_tcp_probe, failures)
    containers_initial_raw = parse_if_success("A10_CONTAINER_LIST_INITIAL", by_id, raw, base.parse_json_lines, failures) or []
    images_initial_raw = parse_if_success("A11_IMAGE_LIST_INITIAL", by_id, raw, base.parse_json_lines, failures) or []
    containers_final_raw = parse_if_success("A19_CONTAINER_LIST_FINAL", by_id, raw, base.parse_json_lines, failures) or []
    images_final_raw = parse_if_success("A20_IMAGE_LIST_FINAL", by_id, raw, base.parse_json_lines, failures) or []
    events_raw = parse_if_success("A21_DOCKER_EVENTS_BEFORE_STOP", by_id, raw, base.parse_json_lines, failures) or []

    snapshots: list[dict[str, Any]] = []
    for label, verbose_id, running_id, process_id, tcp_id in snapshot_specs:
        wsl_rows = parse_if_success(verbose_id, by_id, raw, base.parse_wsl_list, failures) or []
        running = parse_if_success(running_id, by_id, raw, base.parse_wsl_running, failures)
        processes = parse_if_success(process_id, by_id, raw, parse_process_probe, failures)
        tcp = parse_if_success(tcp_id, by_id, raw, parse_tcp_probe, failures)
        lanes = {
            "wsl_inventory_all_stopped": bool(wsl_rows) and all(row.get("state") == "Stopped" for row in wsl_rows),
            "docker_desktop_distro_exactly_stopped": base.native_gate.distro_state(wsl_rows, "docker-desktop") == "Stopped",
            "wsl_running_inventory_empty": running == [],
            "desktop_linux_named_pipe_absent_win32_error_2": base.native_gate.pipe_is_specifically_absent(pipe_probes[label]),
            "target_process_population_empty": isinstance(processes, dict) and processes.get("count") == 0,
            "target_tcp_population_empty": isinstance(tcp, dict) and tcp.get("count") == 0,
        }
        snapshots.append({
            "label": label,
            "wsl_inventory": wsl_rows,
            "running_inventory": running,
            "named_pipe_probe": pipe_probes[label],
            "target_process_identity": processes,
            "target_tcp_ownership_redacted": tcp,
            "lanes": lanes,
            "all_lanes_pass": all(lanes.values()),
        })

    containers_initial = base.sanitize_rows(containers_initial_raw, ("ID", "State", "Status"))
    containers_final = base.sanitize_rows(containers_final_raw, ("ID", "State", "Status"))
    images_initial = base.sanitize_rows(images_initial_raw, ("ID", "Digest", "Size"))
    images_final = base.sanitize_rows(images_final_raw, ("ID", "Digest", "Size"))
    system_df = base.sanitize_rows(system_df_raw, ("Type", "TotalCount", "Active", "Size", "Reclaimable"))
    mutation_events = [
        {"Type": row.get("Type"), "Action": row.get("Action")}
        for row in events_raw if isinstance(row, dict)
        and str(row.get("Type", "")).casefold() in {"container", "image"}
    ]
    client = version_data.get("Client") or {}
    server = version_data.get("Server") or {}
    client_whitelist = {
        key: client.get(key)
        for key in (
            "Version", "ApiVersion", "DefaultAPIVersion", "GitCommit",
            "GoVersion", "Os", "Arch", "BuildTime", "Context",
        )
    }
    server_whitelist = {
        key: server.get(key)
        for key in (
            "Version", "ApiVersion", "MinAPIVersion", "GitCommit", "GoVersion",
            "Os", "Arch", "KernelVersion", "BuildTime", "Experimental",
        )
    }
    containerd_commit = info_data.get("ContainerdCommit")
    info_whitelist = {
        key: info_data.get(key)
        for key in (
            "ID", "ServerVersion", "OperatingSystem", "OSType", "Architecture",
            "KernelVersion", "Driver", "CgroupDriver", "CgroupVersion",
            "DockerRootDir", "SecurityOptions", "DefaultRuntime", "NCPU",
            "MemTotal", "Containers", "ContainersRunning", "ContainersPaused",
            "ContainersStopped", "Images", "LiveRestoreEnabled", "Isolation",
            "ExperimentalBuild",
        )
    }
    info_whitelist.update({
        "ContainerdCommitID": (
            containerd_commit.get("ID") if isinstance(containerd_commit, dict) else None
        ),
        "Runtimes": sorted((info_data.get("Runtimes") or {}).keys()),
        "HttpProxyConfigured": bool(info_data.get("HttpProxy")),
        "HttpsProxyConfigured": bool(info_data.get("HttpsProxy")),
        "NoProxyConfigured": bool(info_data.get("NoProxy")),
    })
    context = base.sanitize_context(context_data)
    backend_linux = (
        str(info_data.get("OSType", "")).casefold() == "linux"
        and str(info_data.get("Architecture", "")).casefold() in {"x86_64", "amd64"}
        and str(context.get("Name", "")).casefold() == "desktop-linux"
        and context.get("DockerEndpointHostClass") == "DESKTOP_LINUX_NPIPE_EXACT"
    )
    query_ids = [f"A{number:02d}" for number in range(10, 22)]
    all_queries_ok = all(
        any(command_id.startswith(prefix + "_") and command_ok(by_id[command_id]) for command_id in by_id)
        for prefix in query_ids
    )
    no_running_containers = (
        info_data.get("ContainersRunning") == 0
        and all(str(row.get("State", "")).casefold() != "running" for row in containers_initial + containers_final)
    )
    exact_ids = [row["command_id"] for row in receipts] == EXPECTED_COMMAND_IDS
    closure_stable = (
        len(snapshots) == POST_SHUTDOWN_SNAPSHOTS
        and all(snapshot["all_lanes_pass"] for snapshot in snapshots)
        and snapshots[0]["wsl_inventory"] == snapshots[1]["wsl_inventory"] == snapshots[2]["wsl_inventory"]
        and snapshots[0]["running_inventory"] == snapshots[1]["running_inventory"] == snapshots[2]["running_inventory"]
        and snapshots[0]["target_process_identity"] == snapshots[1]["target_process_identity"] == snapshots[2]["target_process_identity"]
        and snapshots[0]["target_tcp_ownership_redacted"] == snapshots[1]["target_tcp_ownership_redacted"] == snapshots[2]["target_tcp_ownership_redacted"]
        and before_wsl == snapshots[0]["wsl_inventory"]
    )
    pass_conditions = {
        "pre_start_gate_all_pass": all(pre_gate.values()),
        "startup_attempted_exactly_once": started and start_receipt is not None,
        "startup_command_success": start_receipt is not None and command_ok(start_receipt),
        "during_docker_desktop_running": base.native_gate.distro_state(during_wsl, "docker-desktop") == "Running",
        "during_process_probe_complete_and_nonempty": (
            isinstance(during_processes, dict) and during_processes.get("count", 0) > 0
        ),
        "during_tcp_probe_available": isinstance(during_tcp, dict),
        "all_query_commands_success": all_queries_ok,
        "backend_linux_amd64_desktop_linux": backend_linux,
        "docker_identity_complete": (
            all(client_whitelist.get(key) for key in ("Version", "ApiVersion", "Os", "Arch"))
            and all(
                server_whitelist.get(key)
                for key in ("Version", "ApiVersion", "Os", "Arch", "KernelVersion")
            )
            and all(
                info_whitelist.get(key)
                for key in (
                    "ServerVersion", "OSType", "Architecture", "KernelVersion",
                    "Driver", "CgroupVersion", "DockerRootDir", "ContainerdCommitID",
                )
            )
        ),
        "parse_failures_absent": not failures,
        "containers_running_zero": no_running_containers,
        "container_inventory_unchanged": containers_initial == containers_final,
        "image_inventory_unchanged": images_initial == images_final,
        "container_or_image_events_absent": not mutation_events,
        "docker_stop_attempted_exactly_once": stop_receipt is not None,
        "docker_stop_success": stop_receipt is not None and command_ok(stop_receipt),
        "wsl_shutdown_attempted_exactly_once": shutdown_receipt is not None,
        "wsl_shutdown_success": shutdown_receipt is not None and command_ok(shutdown_receipt),
        "three_snapshot_final_closure_all_pass_and_stable": closure_stable,
        "exact_command_sequence_no_retry": exact_ids,
        "disk_thresholds_after_pass": (
            after_disk["c"]["free_bytes"] >= 20 * 1024**3
            and after_disk["e"]["free_bytes"] >= 50 * 1024**3
        ),
        "automatic_retry_count_zero": True,
    }
    verdict = (
        "PASS_PC2W_P1_ATTEMPT005_INSTRUMENTED_CURRENT_HOST_ADMITTED_FOR_CENTRAL_G1"
        if all(pass_conditions.values())
        else "FAIL_CLOSED_PC2W_P1_ATTEMPT005_CURRENT_HOST_NOT_ADMISSIBLE"
    )

    frozen_facts = [
        {
            "path": relative.as_posix(),
            "git_blob_bytes": git_blob_fact(repo_root, head, relative)[0],
            "git_blob_sha256": git_blob_fact(repo_root, head, relative)[1],
        }
        for relative in sorted(frozen_map, key=lambda value: value.as_posix())
    ]
    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-command-receipts-1.0",
        "material_passport": material_passport,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "commands": receipts,
        "command_ids": [row["command_id"] for row in receipts],
        "exact_command_sequence": exact_ids,
        "named_pipe_probes_are_non_command_read_only_probes": True,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
        "raw_process_paths_or_command_lines_persisted": False,
        "raw_network_addresses_persisted": False,
    }
    inventory_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-runtime-inventory-1.0",
        "material_passport": material_passport,
        "host_identity": {"windows": windows_identity, "wsl": wsl_version},
        "docker_desktop_identity": {
            "path": str(DOCKER_DESKTOP),
            "raw_bytes": DOCKER_DESKTOP.stat().st_size,
            "raw_sha256": sha256_file(DOCKER_DESKTOP),
            "file_version": docker_identity.get("FileVersion"),
            "product_version": docker_identity.get("ProductVersion"),
        },
        "pre_start": {
            "wsl_inventory": before_wsl,
            "running_inventory": before_running,
            "named_pipe_probe": pre_pipe,
            "target_process_identity": before_processes,
            "target_tcp_ownership_redacted": before_tcp,
            "lanes": pre_gate,
        },
        "during": {
            "wsl_inventory": during_wsl,
            "target_process_identity": during_processes,
            "target_tcp_ownership_redacted": during_tcp,
        },
        "docker_client_version_whitelist": client_whitelist,
        "docker_server_version_whitelist": server_whitelist,
        "docker_info_whitelist": info_whitelist,
        "post_shutdown_snapshots": snapshots,
        "closure_stable": closure_stable,
        "containers_initial": containers_initial,
        "containers_final": containers_final,
        "images_initial": images_initial,
        "images_final": images_final,
        "container_or_image_events": mutation_events,
        "system_df": system_df,
        "context_whitelist": context,
        "before_disk": before_disk,
        "after_disk": after_disk,
        "parse_failures": failures,
        "proxy_values_persisted": False,
        "raw_context_persisted": False,
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-execution-receipt-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT005",
        "created_at": created_at,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "frozen_artifacts": frozen_facts,
        "authorization_sha256": sha256_file(repo_root / AUTH_RELATIVE),
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "dispatch_sha256": sha256_file(repo_root / DISPATCH_RELATIVE),
        "runner_sha256": sha256_file(repo_root / RUNNER_RELATIVE),
        "output_root": str(output_root),
        "startup_attempts": 1 if start_receipt is not None else 0,
        "docker_stop_attempts": 1 if stop_receipt is not None else 0,
        "wsl_shutdown_attempts": 1 if shutdown_receipt is not None else 0,
        "closure_snapshots": len(snapshots),
        "post_shutdown_settling_seconds": POST_SHUTDOWN_SETTLING_SECONDS,
        "snapshot_barrier_seconds": POST_SHUTDOWN_SNAPSHOT_BARRIER_SECONDS,
        "automatic_retry_count": 0,
        "pass_conditions": pass_conditions,
        "verdict": verdict,
        "force_kill_performed": False,
        "service_restart_performed": False,
        "settings_changed": False,
        "image_pull_or_build_performed": False,
        "container_create_or_run_performed": False,
        "install_or_download_performed": False,
        "materialization_performed": False,
        "scientific_execution_performed": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt005-handoff-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT005",
        "verdict": verdict,
        "output_files": sorted(EXPECTED_OUTPUT_FILES),
        "next_gate": (
            "CENTRAL_PC2W_G1_AND_FRESH_INDEPENDENT_SOL_XHIGH_STANDARD_AUDIT"
            if verdict.startswith("PASS_")
            else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
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
        "output_root": str(output_root),
        "commands_recorded": len(receipts),
        "automatic_retry_count": 0,
    }, indent=2))
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
            "error_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
            "failure_packet_persisted": failure_packet_persisted,
        }, indent=2), file=sys.stderr)
        raise SystemExit(2)
