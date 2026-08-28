#!/usr/bin/env python3
"""Pure Attempt-013 identity compatibility seam; no host I/O at import time."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from typing import Any

import e4_r6_pc2w_p1_attempt008_probe_contract as parser008
import e4_r6_pc2w_p1_attempt008_safe_probe_envelopes as probes008
import e4_r6_pc2w_p1_attempt009_runtime_compatibility as compat009


IdentityContractError = parser008.IdentityContractError
PROBE_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-runtime-identity-compatibility-1.0"
)
PARENT_RESOLUTIONS = {
    "RESOLVED",
    "UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT",
}
PROCESS_FAILURE_STEPS = (
    probes008.PROCESS_FAILURE_STEPS - {"RESOLVE_PARENT"}
) | {"REQUIRE_PARENT_PROCESS_ID"}
TCP_FAILURE_STEPS = probes008.TCP_FAILURE_STEPS
PROCESS_ROW_FIELDS = {
    "Name",
    "ProcessId",
    "ParentProcessId",
    "ParentResolution",
    "ParentNameHash",
    "ParentExecutablePathHash",
    "ExecutablePathHash",
    "ExecutableFileSha256",
    "FileVersion",
    "AuthenticodeStatus",
    "SignerSubjectHash",
    "CreationTimeUtc",
    "CommandLineHash",
}
SELF_HASH_FIELDS = (
    "ExecutablePathHash",
    "ExecutableFileSha256",
    "SignerSubjectHash",
    "CommandLineHash",
)
_DOCKER_HUMAN_TIME = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r" ?(\d{1,2}) (\d{2}):(\d{2}):(\d{2}) (\d{4})$"
)
_RFC3339_UTC_TIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"
    r"(?:\.(\d{1,9}))?(Z|[+-]00:00)$"
)
_MONTHS = {
    name: index
    for index, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}


PROCESS_IDENTITY_QUERY_V3 = rf"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){{
  if($null -eq $s){{$s=''}}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try {{ ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }}
  finally {{ $sha.Dispose() }}
}}
function Require-NonEmpty($value){{
  if([string]::IsNullOrWhiteSpace([string]$value)){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
}}
$schema='{PROBE_SCHEMA}'
$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe')
$targetNames=@('docker desktop','com.docker.backend','com.docker.build','com.docker.proxy','dockerd','vpnkit','wslrelay')
$allowedSteps=@('ENUMERATE_PROCESSES','REQUIRE_PARENT_PROCESS_ID','REQUIRE_EXECUTABLE_PATH','REQUIRE_PARENT_NAME','REQUIRE_PARENT_PATH','REQUIRE_COMMAND_LINE','VERIFY_EXECUTABLE_FILE','HASH_EXECUTABLE','READ_AUTHENTICODE','REQUIRE_SIGNER_SUBJECT','READ_FILE_VERSION','READ_CREATION_TIME')
$step='ENUMERATE_PROCESSES'
$currentTarget=$null
try {{
  $all=@(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId,ParentProcessId,ExecutablePath,CreationDate,CommandLine -ErrorAction Stop)
  $byPid=@{{}}
  foreach($x in $all){{$byPid[[uint32]$x.ProcessId]=$x}}
  $rows=@()
  foreach($p in @($all | Where-Object {{$target -contains $_.Name}} | Sort-Object Name,ProcessId)){{
    $currentTarget=([IO.Path]::GetFileNameWithoutExtension([string]$p.Name)).ToLowerInvariant()
    $step='REQUIRE_PARENT_PROCESS_ID'
    if($null -eq $p.ParentProcessId -or [uint32]$p.ParentProcessId -eq 0){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
    $parent=$byPid[[uint32]$p.ParentProcessId]
    $parentResolution='UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT'
    $parentNameHash=$null
    $parentPathHash=$null
    if($null -ne $parent){{
      $parentName=[string]$parent.Name
      $parentPath=[string]$parent.ExecutablePath
      $step='REQUIRE_PARENT_NAME'; Require-NonEmpty $parentName
      $step='REQUIRE_PARENT_PATH'; Require-NonEmpty $parentPath
      $parentResolution='RESOLVED'
      $parentNameHash=Get-RedactedSha256 $parentName
      $parentPathHash=Get-RedactedSha256 $parentPath
    }}
    $path=[string]$p.ExecutablePath
    $step='REQUIRE_EXECUTABLE_PATH'; Require-NonEmpty $path
    $step='REQUIRE_COMMAND_LINE'; Require-NonEmpty ([string]$p.CommandLine)
    $step='VERIFY_EXECUTABLE_FILE'
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
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
    if($null -eq $p.CreationDate){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
    $created=([datetime]$p.CreationDate).ToUniversalTime().ToString('o')
    $rows += [pscustomobject]@{{
      Name=$currentTarget
      ProcessId=[uint32]$p.ProcessId
      ParentProcessId=[uint32]$p.ParentProcessId
      ParentResolution=$parentResolution
      ParentNameHash=$parentNameHash
      ParentExecutablePathHash=$parentPathHash
      ExecutablePathHash=$(Get-RedactedSha256 $path)
      ExecutableFileSha256=$fileHash
      FileVersion=$fileVersion
      AuthenticodeStatus=$sigStatus
      SignerSubjectHash=$(Get-RedactedSha256 $signerSubject)
      CreationTimeUtc=$created
      CommandLineHash=$(Get-RedactedSha256 ([string]$p.CommandLine))
    }}
  }}
  [pscustomobject]@{{SchemaVersion=$schema;Available=$true;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';FailureStep='NONE';FailureTarget=$null;ErrorTypeHash=$null}} | ConvertTo-Json -Depth 7 -Compress
}} catch {{
  $safeStep=if($allowedSteps -contains $step){{$step}}else{{'INTERNAL_UNCLASSIFIED'}}
  $safeTarget=if($targetNames -contains $currentTarget){{$currentTarget}}else{{$null}}
  [pscustomobject]@{{SchemaVersion=$schema;Available=$false;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';FailureStep=$safeStep;FailureTarget=$safeTarget;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))}} | ConvertTo-Json -Depth 7 -Compress
}}
""".strip()

TCP_IDENTITY_QUERY_V3 = probes008.TCP_IDENTITY_QUERY_V2.replace(
    probes008.PROBE_SCHEMA, PROBE_SCHEMA
)
wrap_process_identity_probe = compat009.wrap_process_identity_probe
wrap_tcp_identity_probe = compat009.wrap_tcp_identity_probe
validate_desktop_file_probe_envelope = probes008.validate_desktop_file_probe_envelope


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _safe_hash(value: Any) -> str | None:
    return value if parser008.legacy.valid_hash(value) else None


def _validate_common(
    value: Any,
    failure_steps: set[str],
    stage: str,
    prefix: str,
) -> dict[str, Any]:
    fields = {
        "SchemaVersion",
        "Available",
        "Count",
        "Rows",
        "ErrorCode",
        "FailureStep",
        "FailureTarget",
        "ErrorTypeHash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise IdentityContractError(f"{prefix}_ENVELOPE_FIELDS_INVALID", stage)
    if value["SchemaVersion"] != PROBE_SCHEMA:
        raise IdentityContractError(f"{prefix}_ENVELOPE_SCHEMA_INVALID", stage)
    if value["Available"] is True:
        if (
            value["ErrorCode"] != "NONE"
            or value["FailureStep"] != "NONE"
            or value["ErrorTypeHash"] is not None
        ):
            raise IdentityContractError(f"{prefix}_SUCCESS_STATE_INCOHERENT", stage)
    elif value["Available"] is False:
        if value["ErrorCode"] != "PROBE_EXCEPTION":
            raise IdentityContractError(f"{prefix}_FAILURE_CODE_INVALID", stage)
        if value["FailureStep"] not in failure_steps:
            raise IdentityContractError(f"{prefix}_FAILURE_STEP_INVALID", stage)
        if not parser008.legacy.valid_hash(value["ErrorTypeHash"]):
            raise IdentityContractError(f"{prefix}_FAILURE_HASH_INVALID", stage)
    else:
        raise IdentityContractError(f"{prefix}_AVAILABLE_INVALID", stage)
    target = value["FailureTarget"]
    if target is not None and target not in parser008.legacy.TARGET_PROCESS_NAMES:
        raise IdentityContractError(f"{prefix}_FAILURE_TARGET_INVALID", stage)
    return value


def validate_process_probe_envelope(value: Any) -> dict[str, Any]:
    envelope = _validate_common(
        value, PROCESS_FAILURE_STEPS, "D01", "PROCESS_PROBE"
    )
    if envelope["Available"] is False:
        raise IdentityContractError(
            f"PROCESS_PROBE_{envelope['FailureStep']}",
            "D01",
            safe_details={
                "failure_step": envelope["FailureStep"],
                "failure_target": envelope["FailureTarget"],
                "error_type_hash": _safe_hash(envelope["ErrorTypeHash"]),
            },
        )
    if envelope["FailureTarget"] is not None:
        raise IdentityContractError("PROCESS_PROBE_SUCCESS_TARGET_NOT_NULL", "D01")
    count = envelope["Count"]
    rows = envelope["Rows"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise IdentityContractError("PROCESS_COUNT_INVALID", "D01")
    if not isinstance(rows, list) or count != len(rows):
        raise IdentityContractError("PROCESS_ROWS_INVALID", "D01")
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != PROCESS_ROW_FIELDS:
            raise IdentityContractError("PROCESS_ROW_FIELDS_INVALID", "D01")
        name = row["Name"]
        if (
            not isinstance(name, str)
            or name != name.casefold()
            or name not in parser008.legacy.TARGET_PROCESS_NAMES
        ):
            raise IdentityContractError("PROCESS_NAME_INVALID", "D01")
        for field in ("ProcessId", "ParentProcessId"):
            number = row[field]
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                raise IdentityContractError("PROCESS_INTEGER_INVALID", "D01")
        if row["ProcessId"] in seen:
            raise IdentityContractError("PROCESS_ID_DUPLICATE", "D01")
        seen.add(row["ProcessId"])
        if any(not parser008.legacy.valid_hash(row[field]) for field in SELF_HASH_FIELDS):
            raise IdentityContractError("PROCESS_SELF_HASH_INVALID", "D01")
        if not isinstance(row["FileVersion"], str) or not row["FileVersion"].strip():
            raise IdentityContractError("PROCESS_FILE_VERSION_MISSING", "D01")
        if row["AuthenticodeStatus"] != "Valid":
            raise IdentityContractError("PROCESS_SIGNATURE_INVALID", "D01")
        try:
            parser008.legacy.parse_dotnet_utc(row["CreationTimeUtc"])
        except (TypeError, ValueError) as exc:
            raise IdentityContractError("PROCESS_CREATION_TIME_INVALID", "D01") from exc
        resolution = row["ParentResolution"]
        if resolution not in PARENT_RESOLUTIONS:
            raise IdentityContractError("PROCESS_PARENT_RESOLUTION_INVALID", "D01")
        parent_values = (
            row["ParentNameHash"], row["ParentExecutablePathHash"]
        )
        if resolution == "RESOLVED":
            if any(not parser008.legacy.valid_hash(item) for item in parent_values):
                raise IdentityContractError("PROCESS_PARENT_HASH_INVALID", "D01")
        elif any(item is not None for item in parent_values):
            raise IdentityContractError("PROCESS_PARENT_NULLABILITY_INVALID", "D01")
    if rows != sorted(rows, key=lambda row: (row["Name"], row["ProcessId"])):
        raise IdentityContractError("PROCESS_ROWS_NOT_CANONICAL", "D01")
    names = {row["Name"] for row in rows}
    if not parser008.legacy.REQUIRED_DURING_PROCESS_NAMES.issubset(names):
        raise IdentityContractError("PROCESS_REQUIRED_IDENTITIES_MISSING", "D01")
    return {
        key: envelope[key]
        for key in ("Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash")
    }


def validate_tcp_probe_envelope(
    value: Any, processes: dict[str, Any] | None
) -> dict[str, Any]:
    if processes is None:
        raise IdentityContractError(
            "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE", "D02"
        )
    envelope = _validate_common(value, TCP_FAILURE_STEPS, "D02", "TCP_PROBE")
    if envelope["Available"] is False:
        raise IdentityContractError(
            f"TCP_PROBE_{envelope['FailureStep']}",
            "D02",
            safe_details={
                "failure_step": envelope["FailureStep"],
                "failure_target": envelope["FailureTarget"],
                "error_type_hash": _safe_hash(envelope["ErrorTypeHash"]),
            },
        )
    if envelope["FailureTarget"] is not None:
        raise IdentityContractError("TCP_PROBE_SUCCESS_TARGET_NOT_NULL", "D02")
    payload = {
        key: envelope[key]
        for key in ("Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash")
    }
    return parser008.validate_tcp_identity(payload, processes)


def _build_time_parts(value: str) -> tuple[str, tuple[int, ...], bool]:
    family = parser008.classify_docker_build_time(value)
    if family == "DOCKER_CLI_HUMAN":
        matched = _DOCKER_HUMAN_TIME.fullmatch(value)
        assert matched is not None
        _, month, day, hour, minute, second, year = matched.groups()
        parts = (
            int(year), _MONTHS[month], int(day), int(hour), int(minute), int(second)
        )
        return family, parts, True
    matched = _RFC3339_UTC_TIME.fullmatch(value)
    assert matched is not None
    year, month, day, hour, minute, second, fraction, _ = matched.groups()
    parts = tuple(int(item) for item in (year, month, day, hour, minute, second))
    return family, parts, fraction is None or set(fraction) <= {"0"}


def _compare_build_times(root_raw: str, engine_raw: str) -> dict[str, Any]:
    root_format, root_parts, root_fraction_zero = _build_time_parts(root_raw)
    engine_format, engine_parts, engine_fraction_zero = _build_time_parts(engine_raw)
    civil_equal = root_parts == engine_parts
    fraction_zero = root_fraction_zero and engine_fraction_zero
    if root_raw == engine_raw:
        profile = "EXACT_RAW"
    elif (
        {root_format, engine_format} == {"DOCKER_CLI_HUMAN", "RFC3339_UTC"}
        and civil_equal
        and fraction_zero
    ):
        profile = "FORMAT_EQUIVALENT_CIVIL_SECOND"
    else:
        raise IdentityContractError(
            "DOCKER_SERVER_FIELD_CONFLICT", "DOCKER_SERVER", field="BuildTime"
        )
    return {
        "field": "BuildTime",
        "root_source": "SERVER_ROOT",
        "engine_source": "ENGINE_COMPONENT_DETAILS",
        "root_format": root_format,
        "engine_format": engine_format,
        "comparison_profile": profile,
        "civil_second_equal": civil_equal,
        "fraction_zero_or_absent": fraction_zero,
        "root_value_sha256": hashlib.sha256(root_raw.encode("utf-8")).hexdigest(),
        "engine_value_sha256": hashlib.sha256(engine_raw.encode("utf-8")).hexdigest(),
        "raw_values_persisted": False,
        "instant_equivalence_claimed": False,
    }


def canonicalize_docker_server(
    version_data: Any,
) -> tuple[dict[str, Any], dict[str, str], str, dict[str, Any] | None]:
    if not isinstance(version_data, dict) or set(version_data) != {"Client", "Server"}:
        raise IdentityContractError("DOCKER_VERSION_ROOT_INVALID", "DOCKER_IDENTITY")
    client = version_data["Client"]
    server = version_data["Server"]
    if not isinstance(client, dict) or not isinstance(server, dict):
        raise IdentityContractError("DOCKER_IDENTITY_SECTION_MISSING", "DOCKER_IDENTITY")
    engine = compat009._engine_component(server)
    canonical: dict[str, Any] = {}
    sources: dict[str, str] = {}
    comparison: dict[str, Any] | None = None
    supplemented = False
    for field in (*compat009._SERVER_STRING_FIELDS, "Experimental"):
        root_raw = compat009._field_value(server, field)
        engine_raw = compat009._engine_field_value(engine, field)
        root_value = (
            compat009._normalize_server_value(field, root_raw)
            if root_raw is not None
            else None
        )
        engine_value = (
            compat009._normalize_server_value(
                field, engine_raw, allow_lowercase_boolean_string=True
            )
            if engine_raw is not None
            else None
        )
        if root_value is None and engine_value is None:
            raise IdentityContractError(
                "DOCKER_SERVER_FIELD_MISSING", "DOCKER_SERVER", field=field
            )
        if field == "BuildTime":
            if root_value is not None:
                parser008.classify_docker_build_time(root_value)
            if engine_value is not None:
                parser008.classify_docker_build_time(engine_value)
            if root_value is not None and engine_value is not None:
                comparison = _compare_build_times(root_value, engine_value)
        elif (
            root_value is not None
            and engine_value is not None
            and root_value != engine_value
        ):
            raise IdentityContractError(
                "DOCKER_SERVER_FIELD_CONFLICT", "DOCKER_SERVER", field=field
            )
        if root_value is not None:
            canonical[field] = root_value
            sources[field] = (
                "ROOT_CROSSCHECKED_ENGINE_COMPONENT"
                if engine_value is not None
                else "ROOT"
            )
        else:
            canonical[field] = engine_value
            sources[field] = (
                "ENGINE_COMPONENT" if field == "Version" else "ENGINE_COMPONENT_DETAILS"
            )
            supplemented = True
    profile = "ROOT_WITH_ENGINE_COMPONENT_SUPPLEMENT" if supplemented else "ROOT_ONLY"
    return canonical, sources, profile, comparison


def _single_build_time_record(
    raw: str, source: str
) -> dict[str, Any]:
    family, _, fraction_zero = _build_time_parts(raw)
    return {
        "field": "BuildTime",
        "source": source,
        "format": family,
        "comparison_profile": "SINGLE_VALIDATED_SOURCE_NO_CROSS_SURFACE",
        "fraction_zero_or_absent": fraction_zero,
        "value_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "raw_values_persisted": False,
        "instant_equivalence_claimed": False,
    }


def sanitize_docker_identity(
    version_data: Any,
    info_data: Any,
    context_data: Any,
) -> tuple[dict[str, Any], dict[str, bool]]:
    canonical_server, sources, profile, comparison = canonicalize_docker_server(
        version_data
    )
    normalized = {
        "Client": copy.deepcopy(version_data["Client"]),
        "Server": canonical_server,
    }
    sanitized, cross = parser008.sanitize_docker_identity(
        normalized, info_data, context_data
    )
    raw_build_time = sanitized["server"].pop("BuildTime")
    sanitized["server"].pop("BuildTimeFormat", None)
    sanitized["server"]["IdentitySourceProfile"] = profile
    sanitized["server"]["IdentityFieldSources"] = sources
    sanitized["server"]["BuildTimeComparison"] = (
        comparison
        if comparison is not None
        else _single_build_time_record(raw_build_time, sources["BuildTime"])
    )
    return sanitized, cross
