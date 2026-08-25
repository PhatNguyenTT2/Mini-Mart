#!/usr/bin/env python3
"""Attempt-008 R2 safe probe envelopes and pure validators; no host I/O."""

from __future__ import annotations

from typing import Any

import e4_r6_pc2w_p1_attempt008_probe_contract as parser


PROBE_SCHEMA = "stage1e-e4-r6-pc2w-p1-attempt008-safe-probe-envelope-1.0"

PROCESS_FAILURE_STEPS = {
    "ENUMERATE_PROCESSES",
    "RESOLVE_PARENT",
    "REQUIRE_EXECUTABLE_PATH",
    "REQUIRE_PARENT_NAME",
    "REQUIRE_PARENT_PATH",
    "REQUIRE_COMMAND_LINE",
    "VERIFY_EXECUTABLE_FILE",
    "HASH_EXECUTABLE",
    "READ_AUTHENTICODE",
    "REQUIRE_SIGNER_SUBJECT",
    "READ_FILE_VERSION",
    "READ_CREATION_TIME",
}
TCP_FAILURE_STEPS = {
    "ENUMERATE_TARGET_PROCESSES",
    "ENUMERATE_TCP_CONNECTIONS",
    "REQUIRE_STATE",
    "REQUIRE_LOCAL_ADDRESS",
    "REQUIRE_REMOTE_ADDRESS",
    "REQUIRE_LOCAL_PORT",
    "REQUIRE_REMOTE_PORT",
    "REQUIRE_OWNER",
}
FILE_FAILURE_STEPS = {
    "READ_FILE",
    "READ_AUTHENTICODE",
    "REQUIRE_FILE_VERSION",
    "REQUIRE_PRODUCT_VERSION",
    "REQUIRE_SIGNATURE_STATUS",
    "REQUIRE_SIGNER_SUBJECT",
    "HASH_FILE",
}


PROCESS_IDENTITY_QUERY_V2 = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Require-NonEmpty($value){
  if([string]::IsNullOrWhiteSpace([string]$value)){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
}
$schema='stage1e-e4-r6-pc2w-p1-attempt008-safe-probe-envelope-1.0'
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
$targetNames=@('docker desktop','com.docker.backend','com.docker.build','com.docker.proxy','dockerd','vpnkit','wslrelay')
$allowedSteps=@('ENUMERATE_PROCESSES','RESOLVE_PARENT','REQUIRE_EXECUTABLE_PATH','REQUIRE_PARENT_NAME','REQUIRE_PARENT_PATH','REQUIRE_COMMAND_LINE','VERIFY_EXECUTABLE_FILE','HASH_EXECUTABLE','READ_AUTHENTICODE','REQUIRE_SIGNER_SUBJECT','READ_FILE_VERSION','READ_CREATION_TIME')
$step='ENUMERATE_PROCESSES'
$currentTarget=$null
try {
  $all=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId,ParentProcessId,ExecutablePath,CreationDate,CommandLine -ErrorAction Stop)
  $byPid=@{}
  foreach($x in $all){$byPid[[uint32]$x.ProcessId]=$x}
  $rows=@()
  foreach($p in @($all | Where-Object {$target -contains $_.Name} | Sort-Object Name,ProcessId)){
    $currentTarget=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant()
    $step='RESOLVE_PARENT'
    $parent=$byPid[[uint32]$p.ParentProcessId]
    if($null -eq $parent){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $path=[string]$p.ExecutablePath
    $parentName=[string]$parent.Name
    $parentPath=[string]$parent.ExecutablePath
    $step='REQUIRE_EXECUTABLE_PATH'; Require-NonEmpty $path
    $step='REQUIRE_PARENT_NAME'; Require-NonEmpty $parentName
    $step='REQUIRE_PARENT_PATH'; Require-NonEmpty $parentPath
    $step='REQUIRE_COMMAND_LINE'; Require-NonEmpty ([string]$p.CommandLine)
    $step='VERIFY_EXECUTABLE_FILE'
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $step='HASH_EXECUTABLE'
    $fileHash=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    $step='READ_AUTHENTICODE'
    $sig=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
    $sigStatus=[string]$sig.Status
    $signerSubject=[string]$sig.SignerCertificate.Subject
    $step='REQUIRE_SIGNER_SUBJECT'; Require-NonEmpty $signerSubject
    $step='READ_FILE_VERSION'
    $fileVersion=[string](Get-Item -LiteralPath $path -ErrorAction Stop).VersionInfo.FileVersion
    Require-NonEmpty $fileVersion
    $step='READ_CREATION_TIME'
    if($null -eq $p.CreationDate){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $created=([datetime]$p.CreationDate).ToUniversalTime().ToString('o')
    $rows += [pscustomobject]@{
      Name=$currentTarget
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
  [pscustomobject]@{SchemaVersion=$schema;Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';FailureStep='NONE';FailureTarget=$null;ErrorTypeHash=$null} | ConvertTo-Json -Depth 7 -Compress
} catch {
  $safeStep=if($allowedSteps -contains $step){$step}else{'INTERNAL_UNCLASSIFIED'}
  $safeTarget=if($targetNames -contains $currentTarget){$currentTarget}else{$null}
  [pscustomobject]@{SchemaVersion=$schema;Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';FailureStep=$safeStep;FailureTarget=$safeTarget;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 7 -Compress
}
""".strip()


TCP_IDENTITY_QUERY_V2 = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Require-NonEmpty($value){
  if([string]::IsNullOrWhiteSpace([string]$value)){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
}
$schema='stage1e-e4-r6-pc2w-p1-attempt008-safe-probe-envelope-1.0'
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
$targetNames=@('docker desktop','com.docker.backend','com.docker.build','com.docker.proxy','dockerd','vpnkit','wslrelay')
$allowedSteps=@('ENUMERATE_TARGET_PROCESSES','ENUMERATE_TCP_CONNECTIONS','REQUIRE_STATE','REQUIRE_LOCAL_ADDRESS','REQUIRE_REMOTE_ADDRESS','REQUIRE_LOCAL_PORT','REQUIRE_REMOTE_PORT','REQUIRE_OWNER')
$step='ENUMERATE_TARGET_PROCESSES'
$currentTarget=$null
try {
  $procs=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId -ErrorAction Stop | Where-Object {$target -contains $_.Name})
  $byPid=@{}
  foreach($p in $procs){$byPid[[uint32]$p.ProcessId]=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant()}
  $step='ENUMERATE_TCP_CONNECTIONS'
  $connections=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$byPid.ContainsKey([uint32]$_.OwningProcess)} | Sort-Object OwningProcess,State,LocalPort,RemotePort)
  $rows=@()
  foreach($c in $connections){
    $currentTarget=[string]$byPid[[uint32]$c.OwningProcess]
    $step='REQUIRE_STATE'; Require-NonEmpty ([string]$c.State)
    $step='REQUIRE_LOCAL_ADDRESS'; Require-NonEmpty ([string]$c.LocalAddress)
    $step='REQUIRE_REMOTE_ADDRESS'; Require-NonEmpty ([string]$c.RemoteAddress)
    $step='REQUIRE_LOCAL_PORT'; if($null -eq $c.LocalPort){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $step='REQUIRE_REMOTE_PORT'; if($null -eq $c.RemotePort){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $step='REQUIRE_OWNER'; if($null -eq $c.OwningProcess -or [uint32]$c.OwningProcess -eq 0){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
    $rows += [pscustomobject]@{
      ProcessName=$currentTarget
      ProcessId=[uint32]$c.OwningProcess
      State=[string]$c.State
      LocalAddressHash=$(Get-RedactedSha256 ([string]$c.LocalAddress))
      LocalPort=[uint16]$c.LocalPort
      RemoteAddressHash=$(Get-RedactedSha256 ([string]$c.RemoteAddress))
      RemotePort=[uint16]$c.RemotePort
    }
  }
  [pscustomobject]@{SchemaVersion=$schema;Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';FailureStep='NONE';FailureTarget=$null;ErrorTypeHash=$null} | ConvertTo-Json -Depth 7 -Compress
} catch {
  $safeStep=if($allowedSteps -contains $step){$step}else{'INTERNAL_UNCLASSIFIED'}
  $safeTarget=if($targetNames -contains $currentTarget){$currentTarget}else{$null}
  [pscustomobject]@{SchemaVersion=$schema;Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';FailureStep=$safeStep;FailureTarget=$safeTarget;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 7 -Compress
}
""".strip()


DOCKER_DESKTOP_FILE_IDENTITY_QUERY_V2 = r"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){
  if($null -eq $s){$s=''}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }
  finally { $sha.Dispose() }
}
function Require-NonEmpty($value){
  if([string]::IsNullOrWhiteSpace([string]$value)){throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}
}
$schema='stage1e-e4-r6-pc2w-p1-attempt008-safe-probe-envelope-1.0'
$allowedSteps=@('READ_FILE','READ_AUTHENTICODE','REQUIRE_FILE_VERSION','REQUIRE_PRODUCT_VERSION','REQUIRE_SIGNATURE_STATUS','REQUIRE_SIGNER_SUBJECT','HASH_FILE')
$path='C:\Program Files\Docker\Docker\Docker Desktop.exe'
$step='READ_FILE'
try {
  $f=Get-Item -LiteralPath $path -ErrorAction Stop
  $step='READ_AUTHENTICODE'
  $sig=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
  $step='REQUIRE_FILE_VERSION'; Require-NonEmpty ([string]$f.VersionInfo.FileVersion)
  $step='REQUIRE_PRODUCT_VERSION'; Require-NonEmpty ([string]$f.VersionInfo.ProductVersion)
  $step='REQUIRE_SIGNATURE_STATUS'; Require-NonEmpty ([string]$sig.Status)
  $step='REQUIRE_SIGNER_SUBJECT'; Require-NonEmpty ([string]$sig.SignerCertificate.Subject)
  $step='HASH_FILE'
  $identity=[pscustomobject]@{
    PathHash=$(Get-RedactedSha256 $path)
    RawBytes=[uint64]$f.Length
    FileSha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    FileVersion=[string]$f.VersionInfo.FileVersion
    ProductVersion=[string]$f.VersionInfo.ProductVersion
    AuthenticodeStatus=[string]$sig.Status
    SignerSubjectHash=$(Get-RedactedSha256 ([string]$sig.SignerCertificate.Subject))
  }
  [pscustomobject]@{SchemaVersion=$schema;Available=$true;Identity=$identity;ErrorCode='NONE';FailureStep='NONE';ErrorTypeHash=$null} | ConvertTo-Json -Depth 6 -Compress
} catch {
  $safeStep=if($allowedSteps -contains $step){$step}else{'INTERNAL_UNCLASSIFIED'}
  [pscustomobject]@{SchemaVersion=$schema;Available=$false;Identity=$null;ErrorCode='PROBE_EXCEPTION';FailureStep=$safeStep;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))} | ConvertTo-Json -Depth 6 -Compress
}
""".strip()


def _safe_hash(value: Any) -> str | None:
    return value if parser.legacy.valid_hash(value) else None


def _validate_common(
    value: Any,
    fields: set[str],
    failure_steps: set[str],
    stage: str,
    prefix: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise parser.IdentityContractError(f"{prefix}_ENVELOPE_FIELDS_INVALID", stage)
    if value["SchemaVersion"] != PROBE_SCHEMA:
        raise parser.IdentityContractError(f"{prefix}_ENVELOPE_SCHEMA_INVALID", stage)
    if value["Available"] is True:
        if value["ErrorCode"] != "NONE" or value["FailureStep"] != "NONE" or value["ErrorTypeHash"] is not None:
            raise parser.IdentityContractError(f"{prefix}_SUCCESS_STATE_INCOHERENT", stage)
    elif value["Available"] is False:
        if value["ErrorCode"] != "PROBE_EXCEPTION":
            raise parser.IdentityContractError(f"{prefix}_FAILURE_CODE_INVALID", stage)
        if value["FailureStep"] not in failure_steps:
            raise parser.IdentityContractError(f"{prefix}_FAILURE_STEP_INVALID", stage)
        if not parser.legacy.valid_hash(value["ErrorTypeHash"]):
            raise parser.IdentityContractError(f"{prefix}_FAILURE_HASH_INVALID", stage)
    else:
        raise parser.IdentityContractError(f"{prefix}_AVAILABLE_INVALID", stage)
    return value


def validate_process_probe_envelope(value: Any) -> dict[str, Any]:
    fields = {
        "SchemaVersion", "Available", "Count", "Rows", "ErrorCode",
        "FailureStep", "FailureTarget", "ErrorTypeHash",
    }
    envelope = _validate_common(value, fields, PROCESS_FAILURE_STEPS, "D01", "PROCESS_PROBE")
    target = envelope["FailureTarget"]
    if target is not None and target not in parser.legacy.TARGET_PROCESS_NAMES:
        raise parser.IdentityContractError("PROCESS_PROBE_FAILURE_TARGET_INVALID", "D01")
    if envelope["Available"] is False:
        raise parser.IdentityContractError(
            f"PROCESS_PROBE_{envelope['FailureStep']}",
            "D01",
            safe_details={
                "failure_step": envelope["FailureStep"],
                "failure_target": target,
                "error_type_hash": _safe_hash(envelope["ErrorTypeHash"]),
            },
        )
    if target is not None:
        raise parser.IdentityContractError("PROCESS_PROBE_SUCCESS_TARGET_NOT_NULL", "D01")
    payload = {
        key: envelope[key]
        for key in ("Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash")
    }
    return parser.validate_process_identity(payload)


def validate_tcp_probe_envelope(
    value: Any,
    processes: dict[str, Any] | None,
) -> dict[str, Any]:
    if processes is None:
        raise parser.IdentityContractError(
            "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE", "D02"
        )
    fields = {
        "SchemaVersion", "Available", "Count", "Rows", "ErrorCode",
        "FailureStep", "FailureTarget", "ErrorTypeHash",
    }
    envelope = _validate_common(value, fields, TCP_FAILURE_STEPS, "D02", "TCP_PROBE")
    target = envelope["FailureTarget"]
    if target is not None and target not in parser.legacy.TARGET_PROCESS_NAMES:
        raise parser.IdentityContractError("TCP_PROBE_FAILURE_TARGET_INVALID", "D02")
    if envelope["Available"] is False:
        raise parser.IdentityContractError(
            f"TCP_PROBE_{envelope['FailureStep']}",
            "D02",
            safe_details={
                "failure_step": envelope["FailureStep"],
                "failure_target": target,
                "error_type_hash": _safe_hash(envelope["ErrorTypeHash"]),
            },
        )
    if target is not None:
        raise parser.IdentityContractError("TCP_PROBE_SUCCESS_TARGET_NOT_NULL", "D02")
    payload = {
        key: envelope[key]
        for key in ("Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash")
    }
    return parser.validate_tcp_identity(payload, processes)


def validate_desktop_file_probe_envelope(value: Any) -> dict[str, Any]:
    fields = {
        "SchemaVersion", "Available", "Identity", "ErrorCode",
        "FailureStep", "ErrorTypeHash",
    }
    envelope = _validate_common(value, fields, FILE_FAILURE_STEPS, "D06", "DESKTOP_FILE_PROBE")
    if envelope["Available"] is False:
        if envelope["Identity"] is not None:
            raise parser.IdentityContractError("DESKTOP_FILE_PROBE_FAILURE_IDENTITY_NOT_NULL", "D06")
        raise parser.IdentityContractError(
            f"DESKTOP_FILE_PROBE_{envelope['FailureStep']}",
            "D06",
            safe_details={
                "failure_step": envelope["FailureStep"],
                "error_type_hash": _safe_hash(envelope["ErrorTypeHash"]),
            },
        )
    if not isinstance(envelope["Identity"], dict):
        raise parser.IdentityContractError("DESKTOP_FILE_PROBE_SUCCESS_IDENTITY_INVALID", "D06")
    return parser.validate_desktop_file_identity(envelope["Identity"])
