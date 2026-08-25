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


base = baseline.base
DOCKER = baseline.DOCKER
DOCKER_DESKTOP = base.DOCKER_DESKTOP
WSL = baseline.WSL
POWERSHELL = baseline.POWERSHELL
PYTHON = baseline.PYTHON
EXPECTED_EXECUTION_ROOT = baseline.EXPECTED_EXECUTION_ROOT
EXPECTED_EXECUTABLES = baseline.EXPECTED_EXECUTABLES

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt007_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt007_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt007_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt007_static_packet.py"
PACKET_PARENT = "594076231cbd12d5a3ffd61b358a38033bbaca85"
PACKET_RELATIVES = {
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
}
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ap/"
    "E4_R6PC2W_P1_attempt007_admission_observation"
)
EXPECTED_OUTPUT_FILES = {
    "admission_observation.json",
    "command_receipts.json",
    "execution_receipt.json",
    "handoff.json",
}
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT007_PROCESS_COMMAND_AFTER_"
    "CENTRAL_VALIDATION_AND_FRESH_AUDIT"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt007-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT007_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt007-fresh-independent-audit-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT007_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_EXACT_COMMAND_CONFIRMATION"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT007_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT007_CURRENT_HOST_NOT_ADMISSIBLE"
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
FROZEN_ATTEMPT006_SHA256_LITERAL = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json":
        "3253d9773b0525b4156cfefc15f4f4ef5866cb8b32d9d5f3c423fa0fa4c64be4",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt006_baseline_remediation_contract.json":
        "fa7a08d98de43562a7f02b30be1dc83e8da451ab54ba850cedbd96f1d6364372",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt006_user_authorization.json":
        "0c18926c5d23ea3f1e666adb42dd0ec8debdce566c2dceddf00f42206d90ff57",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt006_baseline_remediation.py":
        "ba377b0be805160c979f169c093ab862403b74328d54917baa60199078727c99",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt006_static_packet.py":
        "238cbbe25c60eac880b81a96c399514589e11e201c48e01c3fe3e127899b5b0a",
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
}
FROZEN_ATTEMPT006_SHA256 = {
    Path(path): value for path, value in FROZEN_ATTEMPT006_SHA256_LITERAL.items()
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
  foreach($p in @($all | Where-Object {$target -contains $_.Name} | Sort-Object Name,ProcessId)){
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
    if($null -eq $p.CreationDate){throw 'missing required identity field: CreationDate'}
    $created=([datetime]$p.CreationDate).ToUniversalTime().ToString('o')
    Require-NonEmpty $fileHash 'ExecutableFileSha256'
    Require-NonEmpty $sigStatus 'AuthenticodeStatus'
    Require-NonEmpty $signerSubject 'SignerSubject'
    Require-NonEmpty $fileVersion 'FileVersion'
    Require-NonEmpty $created 'CreationTimeUtc'
    $rows += [pscustomobject]@{
      Name=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant()
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
  [pscustomobject]@{Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';ErrorTypeHash=$null} | ConvertTo-Json -Depth 7 -Compress
} catch {
  [pscustomobject]@{Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 7 -Compress
}
""".strip()

TCP_IDENTITY_QUERY = r"""
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
  $byPid=@{}
  foreach($p in $procs){$byPid[[uint32]$p.ProcessId]=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant()}
  $rows=@()
  foreach($c in @(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$byPid.ContainsKey([uint32]$_.OwningProcess)} | Sort-Object OwningProcess,State,LocalPort,RemotePort)){
    Require-NonEmpty ([string]$c.State) 'State'
    Require-NonEmpty ([string]$c.LocalAddress) 'LocalAddress'
    Require-NonEmpty ([string]$c.RemoteAddress) 'RemoteAddress'
    if($null -eq $c.LocalPort){throw 'missing required TCP field: LocalPort'}
    if($null -eq $c.RemotePort){throw 'missing required TCP field: RemotePort'}
    if($null -eq $c.OwningProcess -or [uint32]$c.OwningProcess -eq 0){throw 'missing required TCP field: OwningProcess'}
    $rows += [pscustomobject]@{
      ProcessName=[string]$byPid[[uint32]$c.OwningProcess]
      ProcessId=[uint32]$c.OwningProcess
      State=[string]$c.State
      LocalAddressHash=$(Get-RedactedSha256 ([string]$c.LocalAddress))
      LocalPort=[uint16]$c.LocalPort
      RemoteAddressHash=$(Get-RedactedSha256 ([string]$c.RemoteAddress))
      RemotePort=[uint16]$c.RemotePort
    }
  }
  [pscustomobject]@{Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';ErrorTypeHash=$null} | ConvertTo-Json -Depth 7 -Compress
} catch {
  [pscustomobject]@{Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 7 -Compress
}
""".strip()

DOCKER_DESKTOP_FILE_IDENTITY_QUERY = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
$path='C:\Program Files\Docker\Docker\Docker Desktop.exe'
$f=Get-Item -LiteralPath $path -ErrorAction Stop
$sig=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
if([string]::IsNullOrWhiteSpace([string]$f.VersionInfo.FileVersion)){throw 'missing Docker Desktop file version'}
if([string]::IsNullOrWhiteSpace([string]$f.VersionInfo.ProductVersion)){throw 'missing Docker Desktop product version'}
if([string]::IsNullOrWhiteSpace([string]$sig.Status)){throw 'missing Docker Desktop signature status'}
if([string]::IsNullOrWhiteSpace([string]$sig.SignerCertificate.Subject)){throw 'missing Docker Desktop signer subject'}
[pscustomobject]@{
  PathHash=$(Get-RedactedSha256 $path)
  RawBytes=[uint64]$f.Length
  FileSha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
  FileVersion=[string]$f.VersionInfo.FileVersion
  ProductVersion=[string]$f.VersionInfo.ProductVersion
  AuthenticodeStatus=[string]$sig.Status
  SignerSubjectHash=$(Get-RedactedSha256 ([string]$sig.SignerCertificate.Subject))
} | ConvertTo-Json -Depth 4 -Compress
""".strip()


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


def parse_dotnet_utc(value: Any) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z", value
    ) is None:
        raise ValueError("timestamp must be .NET round-trip UTC with seven digits and Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp is not UTC")
    return parsed


def parse_rfc3339_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("RFC3339 timestamp must have Z suffix")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("RFC3339 timestamp is not UTC")
    return parsed


def validate_rich_process_envelope(value: Any) -> dict[str, Any]:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("rich process envelope field set mismatch")
    if value["Available"] is not True or value["ErrorCode"] != "NONE" or value["ErrorTypeHash"] is not None:
        raise ValueError("rich process envelope unavailable")
    count = value["Count"]
    rows = value["Rows"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("rich process count invalid")
    if not isinstance(rows, list) or count != len(rows):
        raise ValueError("rich process Rows invalid")
    fields = {
        "Name", "ProcessId", "ParentProcessId", "ParentNameHash",
        "ParentExecutablePathHash", "ExecutablePathHash", "ExecutableFileSha256",
        "FileVersion", "AuthenticodeStatus", "SignerSubjectHash",
        "CreationTimeUtc", "CommandLineHash",
    }
    seen_pids: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("rich process row field set mismatch")
        name = row["Name"]
        if not isinstance(name, str) or name != name.casefold() or name not in TARGET_PROCESS_NAMES:
            raise ValueError("rich process name invalid")
        for field in ("ProcessId", "ParentProcessId"):
            number = row[field]
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                raise ValueError("rich process integer invalid")
        if row["ProcessId"] in seen_pids:
            raise ValueError("duplicate rich process id")
        seen_pids.add(row["ProcessId"])
        for field in (
            "ParentNameHash", "ParentExecutablePathHash", "ExecutablePathHash",
            "ExecutableFileSha256", "SignerSubjectHash", "CommandLineHash",
        ):
            if not valid_hash(row[field]):
                raise ValueError("rich process hash invalid")
        if not isinstance(row["FileVersion"], str) or not row["FileVersion"].strip():
            raise ValueError("rich process FileVersion missing")
        if row["AuthenticodeStatus"] != "Valid":
            raise ValueError("rich process signature is not Valid")
        parse_dotnet_utc(row["CreationTimeUtc"])
    if rows != sorted(rows, key=lambda row: (row["Name"], row["ProcessId"])):
        raise ValueError("rich process rows not canonical")
    names = {row["Name"] for row in rows}
    if not REQUIRED_DURING_PROCESS_NAMES.issubset(names):
        raise ValueError("required Docker Desktop process identities missing")
    return value


def validate_rich_tcp_envelope(
    value: Any, processes: dict[str, Any]
) -> dict[str, Any]:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("rich TCP envelope field set mismatch")
    if value["Available"] is not True or value["ErrorCode"] != "NONE" or value["ErrorTypeHash"] is not None:
        raise ValueError("rich TCP envelope unavailable")
    count = value["Count"]
    rows = value["Rows"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("rich TCP count invalid")
    if not isinstance(rows, list) or count != len(rows):
        raise ValueError("rich TCP Rows invalid")
    process_keys = {(row["Name"], row["ProcessId"]) for row in processes["Rows"]}
    fields = {
        "ProcessName", "ProcessId", "State", "LocalAddressHash", "LocalPort",
        "RemoteAddressHash", "RemotePort",
    }
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("rich TCP row field set mismatch")
        key = (row["ProcessName"], row["ProcessId"])
        if key not in process_keys:
            raise ValueError("rich TCP owner is ambiguous")
        if not isinstance(row["State"], str) or not row["State"].strip():
            raise ValueError("rich TCP State missing")
        for field in ("LocalAddressHash", "RemoteAddressHash"):
            if not valid_hash(row[field]):
                raise ValueError("rich TCP address hash invalid")
        for field in ("LocalPort", "RemotePort"):
            port = row[field]
            if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
                raise ValueError("rich TCP port invalid")
        identity = (
            row["ProcessName"], row["ProcessId"], row["State"],
            row["LocalAddressHash"], row["LocalPort"],
            row["RemoteAddressHash"], row["RemotePort"],
        )
        if identity in seen:
            raise ValueError("duplicate rich TCP row")
        seen.add(identity)
    if rows != sorted(
        rows,
        key=lambda row: (
            row["ProcessName"], row["ProcessId"], row["State"],
            row["LocalPort"], row["RemotePort"],
        ),
    ):
        raise ValueError("rich TCP rows not canonical")
    return value


def validate_desktop_file_identity(value: Any) -> dict[str, Any]:
    fields = {
        "PathHash", "RawBytes", "FileSha256", "FileVersion", "ProductVersion",
        "AuthenticodeStatus", "SignerSubjectHash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Docker Desktop file identity field set mismatch")
    if not all(valid_hash(value[field]) for field in ("PathHash", "FileSha256", "SignerSubjectHash")):
        raise ValueError("Docker Desktop file identity hash invalid")
    if not isinstance(value["RawBytes"], int) or isinstance(value["RawBytes"], bool) or value["RawBytes"] <= 0:
        raise ValueError("Docker Desktop file byte count invalid")
    if any(not isinstance(value[field], str) or not value[field].strip() for field in ("FileVersion", "ProductVersion")):
        raise ValueError("Docker Desktop version identity missing")
    if value["AuthenticodeStatus"] != "Valid":
        raise ValueError("Docker Desktop executable signature is not Valid")
    return value


def sanitize_docker_identity(
    version_data: Any, info_data: Any, context_data: Any
) -> tuple[dict[str, Any], dict[str, bool]]:
    if not isinstance(version_data, dict) or set(version_data) != {"Client", "Server"}:
        raise ValueError("Docker version identity root invalid")
    client = version_data["Client"]
    server = version_data["Server"]
    if not isinstance(client, dict) or not isinstance(server, dict) or not isinstance(info_data, dict):
        raise ValueError("Docker client, server or info identity missing")
    client_fields = (
        "Version", "ApiVersion", "DefaultAPIVersion", "GitCommit", "GoVersion",
        "Os", "Arch", "BuildTime", "Context",
    )
    server_fields = (
        "Version", "ApiVersion", "MinAPIVersion", "GitCommit", "GoVersion",
        "Os", "Arch", "KernelVersion", "BuildTime", "Experimental",
    )
    for field in client_fields:
        if field not in client or client[field] is None:
            raise ValueError("Docker client identity field missing")
    for field in server_fields:
        if field not in server or server[field] is None:
            raise ValueError("Docker server identity field missing")
    for field in client_fields[:-2]:
        if not isinstance(client[field], str) or not client[field].strip():
            raise ValueError("Docker client identity string missing")
    if not isinstance(client["Context"], str) or not client["Context"].strip():
        raise ValueError("Docker client context missing")
    for field in server_fields[:-1]:
        if not isinstance(server[field], str) or not server[field].strip():
            raise ValueError("Docker server identity string missing")
    if not isinstance(server["Experimental"], bool):
        raise ValueError("Docker server Experimental must be boolean")
    parse_rfc3339_utc(client["BuildTime"])
    parse_rfc3339_utc(server["BuildTime"])
    required_info_strings = (
        "ServerVersion", "OperatingSystem", "OSType", "Architecture",
        "KernelVersion", "Driver", "CgroupDriver", "CgroupVersion",
        "DockerRootDir", "DefaultRuntime", "ID",
    )
    for field in required_info_strings:
        if not isinstance(info_data.get(field), str) or not info_data[field].strip():
            raise ValueError("Docker info identity field missing")
    for field in ("NCPU", "MemTotal"):
        number = info_data.get(field)
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise ValueError("Docker info positive integer identity missing")
    for field in ("Containers", "ContainersRunning", "ContainersPaused", "ContainersStopped", "Images"):
        number = info_data.get(field)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise ValueError("Docker info nonnegative counter invalid")
    for field in ("LiveRestoreEnabled", "ExperimentalBuild"):
        if not isinstance(info_data.get(field), bool):
            raise ValueError("Docker info boolean identity invalid")
    containerd = info_data.get("ContainerdCommit")
    if not isinstance(containerd, dict) or not isinstance(containerd.get("ID"), str) or not containerd["ID"].strip():
        raise ValueError("Docker info containerd identity missing")
    runtimes = info_data.get("Runtimes")
    if not isinstance(runtimes, dict) or not runtimes or any(not isinstance(key, str) or not key for key in runtimes):
        raise ValueError("Docker info runtimes identity missing")
    security = info_data.get("SecurityOptions")
    if not isinstance(security, list) or any(not isinstance(item, str) or not item for item in security):
        raise ValueError("Docker info security options malformed")
    context = base.sanitize_context(context_data)
    if not isinstance(context, dict):
        raise ValueError("Docker context identity malformed")
    cross = {
        "client_context_desktop_linux": client["Context"] == "desktop-linux",
        "server_linux": server["Os"].casefold() == "linux",
        "server_amd64": server["Arch"].casefold() in {"amd64", "x86_64"},
        "info_server_version_matches": info_data["ServerVersion"] == server["Version"],
        "info_os_matches": info_data["OSType"].casefold() == server["Os"].casefold(),
        "info_arch_matches": info_data["Architecture"].casefold() == server["Arch"].casefold(),
        "info_kernel_matches": info_data["KernelVersion"] == server["KernelVersion"],
        "context_name_desktop_linux": str(context.get("Name", "")).casefold() == "desktop-linux",
        "context_endpoint_exact": context.get("DockerEndpointHostClass") == "DESKTOP_LINUX_NPIPE_EXACT",
    }
    sanitized = {
        "client": {field: client[field] for field in client_fields},
        "server": {field: server[field] for field in server_fields},
        "info": {
            "ServerVersion": info_data["ServerVersion"],
            "OperatingSystem": info_data["OperatingSystem"],
            "OSType": info_data["OSType"],
            "Architecture": info_data["Architecture"],
            "KernelVersion": info_data["KernelVersion"],
            "Driver": info_data["Driver"],
            "CgroupDriver": info_data["CgroupDriver"],
            "CgroupVersion": info_data["CgroupVersion"],
            "DockerRootDirHash": stable_error_hash(info_data["DockerRootDir"]),
            "DefaultRuntime": info_data["DefaultRuntime"],
            "DaemonIDHash": stable_error_hash(info_data["ID"]),
            "ContainerdCommitID": containerd["ID"],
            "Runtimes": sorted(runtimes),
            "SecurityOptionHashes": sorted(stable_error_hash(item) for item in security),
            "NCPU": info_data["NCPU"],
            "MemTotal": info_data["MemTotal"],
            "Containers": info_data["Containers"],
            "ContainersRunning": info_data["ContainersRunning"],
            "ContainersPaused": info_data["ContainersPaused"],
            "ContainersStopped": info_data["ContainersStopped"],
            "Images": info_data["Images"],
            "LiveRestoreEnabled": info_data["LiveRestoreEnabled"],
            "ExperimentalBuild": info_data["ExperimentalBuild"],
            "HttpProxyConfigured": bool(info_data.get("HttpProxy")),
            "HttpsProxyConfigured": bool(info_data.get("HttpsProxy")),
            "NoProxyConfigured": bool(info_data.get("NoProxy")),
        },
        "context": context,
        "cross_consistency": cross,
        "raw_proxy_values_persisted": False,
        "raw_docker_root_dir_persisted": False,
        "raw_daemon_id_persisted": False,
    }
    return sanitized, cross


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
    if central.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT007":
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
    if audit.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT007":
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


def validate_frozen_attempt006(repo_root: Path, head: str) -> dict[str, Any]:
    facts = []
    for relative, expected_sha256 in sorted(
        FROZEN_ATTEMPT006_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        blob_bytes, blob_sha256 = git_blob_fact(repo_root, head, relative)
        if blob_sha256 != expected_sha256:
            raise RuntimeError("frozen Attempt-006 Git blob hash mismatch")
        if canonical_lf_fact(repo_root / relative) != (blob_bytes, blob_sha256):
            raise RuntimeError("frozen Attempt-006 checkout CRLF or bare-CR drift")
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
        "stage1e_rebaseline_v2_r6_pc2w_p1_attempt006_baseline_packet_"
        "audited_ready_for_admission_packet_design"
    ):
        raise RuntimeError("Attempt-006 pipeline state is not the frozen admission input")
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
        raise RuntimeError("Attempt-006 truth state widened")
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
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt007_admission_observation_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt007_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt007_execution_authorization_v1",
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
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-command-receipts-1.0",
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
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-admission-observation-1.0",
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
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-execution-receipt-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT007",
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
            "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-handoff-1.0",
            "material_passport": context["material_passport"],
            "stage_id": "E4-R6-PC2W-P1-ATTEMPT007",
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
    frozen_attempt006 = validate_frozen_attempt006(repo_root, head)
    gate_receipts = validate_gate_receipts(
        repo_root, head, packet_commit, central_path,
        args.central_validation_receipt_sha256,
        audit_path, args.fresh_audit_receipt_sha256,
    )
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    authorization = load_json(repo_root / AUTHORIZATION_RELATIVE)
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt007-admission-observation-contract-1.0":
        raise RuntimeError("Attempt-007 contract schema mismatch")
    if authorization.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt007-execution-authorization-1.0":
        raise RuntimeError("Attempt-007 authorization schema mismatch")
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
        "frozen_attempt006": frozen_attempt006,
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
    persist_failure_packet("IN_PROGRESS", "Attempt-007 initialized before first runtime command")

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
        persist_failure_packet("IN_PROGRESS", f"Attempt-007 progress after {command_id}")
        return receipt, stdout, stderr

    pre_start, pre_lanes = pre_start_snapshot(invoke)
    observations["pre_start"] = pre_start
    persist_failure_packet("IN_PROGRESS", "Attempt-007 immediate pre-start gate complete")

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
    during_wsl = parse_if_success("D00", by_id, raw, base.parse_wsl_list, parse_failures)
    rich_process_raw = parse_if_success("D01", by_id, raw, parse_json_bytes, parse_failures)
    try:
        rich_process = validate_rich_process_envelope(rich_process_raw)
    except Exception as exc:
        rich_process = None
        parse_failures.append(f"D01:IDENTITY:{type(exc).__name__}")
    rich_tcp_raw = parse_if_success("D02", by_id, raw, parse_json_bytes, parse_failures)
    try:
        rich_tcp = validate_rich_tcp_envelope(rich_tcp_raw, rich_process) if rich_process else None
        if rich_process is None:
            raise ValueError("process identity unavailable for TCP ownership")
    except Exception as exc:
        rich_tcp = None
        parse_failures.append(f"D02:IDENTITY:{type(exc).__name__}")
    version_data = parse_if_success("D03", by_id, raw, parse_json_bytes, parse_failures)
    info_data = parse_if_success("D04", by_id, raw, parse_json_bytes, parse_failures)
    context_data = parse_if_success("D05", by_id, raw, parse_json_bytes, parse_failures)
    desktop_file_raw = parse_if_success("D06", by_id, raw, parse_json_bytes, parse_failures)
    try:
        docker_identity, cross_consistency = sanitize_docker_identity(
            version_data, info_data, context_data
        )
    except Exception as exc:
        docker_identity = None
        cross_consistency = {}
        parse_failures.append(f"DOCKER_IDENTITY:{type(exc).__name__}")
    try:
        desktop_file_identity = validate_desktop_file_identity(desktop_file_raw)
        if desktop_file_identity["RawBytes"] != DOCKER_DESKTOP.stat().st_size:
            raise ValueError("Docker Desktop executable size drift")
    except Exception as exc:
        desktop_file_identity = None
        parse_failures.append(f"D06:IDENTITY:{type(exc).__name__}")

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
        "frozen_attempt006_replayed": frozen_attempt006.get("artifact_count") == 10,
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-command-receipts-1.0",
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-admission-observation-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT007",
        "entry_checkpoint": head,
        "packet_commit": packet_commit,
        "frozen_attempt006": frozen_attempt006,
        "gate_receipts": gate_receipts,
        "pre_start": pre_start,
        "during": observations["during"],
        "post_shutdown_snapshots": snapshots,
        "closure_stable": closure_stable,
        "final_closure_matches_pre_start": final_matches_pre,
        "parse_failures": parse_failures,
        "sanitization": {
            "raw_process_paths_or_command_lines_persisted": False,
            "raw_network_addresses_persisted": False,
            "raw_proxy_values_persisted": False,
            "raw_docker_root_dir_persisted": False,
            "raw_stdout_stderr_or_argv_persisted": False,
        },
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-execution-receipt-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT007",
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt007-handoff-1.0",
        "material_passport": material_passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT007",
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
