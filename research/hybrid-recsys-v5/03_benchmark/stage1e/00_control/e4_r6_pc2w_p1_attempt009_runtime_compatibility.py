#!/usr/bin/env python3
"""Attempt-009 compatibility seam for Windows PowerShell and Docker 29.x.

The module performs no host I/O at import time.  It provides a deterministic
child environment, exact-module PowerShell probe wrappers, a safe preflight
envelope, and an explicit Docker server identity schema union.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any, Mapping

import e4_r6_pc2w_p1_attempt008_probe_contract as attempt008


IdentityContractError = attempt008.IdentityContractError
PREFLIGHT_SCHEMA = "stage1e-e4-r6-pc2w-p1-attempt009-powershell-preflight-1.0"
WINDOWS_ROOT = Path(os.environ.get("WINDIR", r"C:\Windows"))
WINPS_SYSTEM_MODULE_ROOT = (
    WINDOWS_ROOT / "System32" / "WindowsPowerShell" / "v1.0" / "Modules"
)
WINPS_ALL_USERS_MODULE_ROOT = Path(r"C:\Program Files\WindowsPowerShell\Modules")
WINPS_CHILD_MODULE_PATHS = (
    WINPS_SYSTEM_MODULE_ROOT,
    WINPS_ALL_USERS_MODULE_ROOT,
)
WINPS_MANIFESTS = {
    "CimCmdlets": WINPS_SYSTEM_MODULE_ROOT / "CimCmdlets" / "CimCmdlets.psd1",
    "NetTCPIP": WINPS_SYSTEM_MODULE_ROOT / "NetTCPIP" / "NetTCPIP.psd1",
    "Microsoft.PowerShell.Utility": (
        WINPS_SYSTEM_MODULE_ROOT
        / "Microsoft.PowerShell.Utility"
        / "Microsoft.PowerShell.Utility.psd1"
    ),
    "Microsoft.PowerShell.Security": (
        WINPS_SYSTEM_MODULE_ROOT
        / "Microsoft.PowerShell.Security"
        / "Microsoft.PowerShell.Security.psd1"
    ),
}
PREFLIGHT_COMMANDS = (
    ("Get-CimInstance", "CimCmdlets", "CimCmdlets", "Cmdlet"),
    ("Get-NetTCPConnection", "NetTCPIP", "MSFT_NetTCPConnection", "Function"),
    ("Get-FileHash", "Microsoft.PowerShell.Utility", "Microsoft.PowerShell.Utility", "Function"),
    ("Get-AuthenticodeSignature", "Microsoft.PowerShell.Security", "Microsoft.PowerShell.Security", "Cmdlet"),
    ("ConvertTo-Json", "Microsoft.PowerShell.Utility", "Microsoft.PowerShell.Utility", "Cmdlet"),
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def windows_powershell_child_environment(
    parent: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a child-only environment without PowerShell 7 module shadowing."""
    child = dict(os.environ if parent is None else parent)
    child["PSModulePath"] = os.pathsep.join(
        str(path) for path in WINPS_CHILD_MODULE_PATHS
    )
    return child


def _ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _module_import_preamble(module_names: tuple[str, ...]) -> str:
    lines = ["$ErrorActionPreference='Stop'"]
    for module_name in module_names:
        manifest = WINPS_MANIFESTS[module_name]
        lines.append(
            f"Import-Module -Name {_ps_literal(str(manifest))} "
            "-Force -ErrorAction Stop"
        )
    return "\n".join(lines)


def _wrap_probe(query: str, module_names: tuple[str, ...]) -> str:
    return _module_import_preamble(module_names) + "\n" + query


def wrap_process_identity_probe(query: str) -> str:
    return _wrap_probe(
        query,
        (
            "CimCmdlets",
            "Microsoft.PowerShell.Utility",
            "Microsoft.PowerShell.Security",
        ),
    )


def wrap_tcp_identity_probe(query: str) -> str:
    return _wrap_probe(
        query,
        ("CimCmdlets", "NetTCPIP", "Microsoft.PowerShell.Utility"),
    )


def wrap_desktop_file_identity_probe(query: str) -> str:
    return _wrap_probe(
        query,
        ("Microsoft.PowerShell.Utility", "Microsoft.PowerShell.Security"),
    )


def _build_powershell_module_preflight_query() -> str:
    specs = ",\n  ".join(
        "[pscustomobject]@{Command="
        + _ps_literal(command)
        + ";ImportModule="
        + _ps_literal(import_module)
        + ";ResolvedModule="
        + _ps_literal(resolved_module)
        + ";CommandType="
        + _ps_literal(command_type)
        + ";Manifest="
        + _ps_literal(str(WINPS_MANIFESTS[import_module]))
        + "}"
        for command, import_module, resolved_module, command_type in PREFLIGHT_COMMANDS
    )
    return rf"""
$ErrorActionPreference='Stop'
function Get-RedactedSha256([string]$s){{
  if($null -eq $s){{$s=''}}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try {{ ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s)))).Replace('-','').ToLowerInvariant() }}
  finally {{ $sha.Dispose() }}
}}
function Get-FileSha256DotNet([string]$path){{
  $stream=[IO.File]::OpenRead($path)
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try {{ ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }}
  finally {{ $sha.Dispose(); $stream.Dispose() }}
}}
$schema='{PREFLIGHT_SCHEMA}'
$allowedSteps=@('VERIFY_MANIFEST','IMPORT_MODULE','RESOLVE_COMMAND','VERIFY_COMMAND_BINDING','HASH_MANIFEST','READ_LANGUAGE_MODE')
$step='VERIFY_MANIFEST'
try {{
  $specs=@(
  {specs}
  )
  $imported=@{{}}
  foreach($spec in $specs){{
    $step='VERIFY_MANIFEST'
    if(-not (Test-Path -LiteralPath $spec.Manifest -PathType Leaf)){{throw [IO.FileNotFoundException]::new('PROBE_STEP_FAILED')}}
    if(-not $imported.ContainsKey([string]$spec.ImportModule)){{
      $step='IMPORT_MODULE'
      Import-Module -Name $spec.Manifest -Force -ErrorAction Stop
      $imported[[string]$spec.ImportModule]=$true
    }}
  }}
  $rows=@()
  foreach($spec in $specs){{
    $step='RESOLVE_COMMAND'
    $qualified=([string]$spec.ImportModule)+'\'+([string]$spec.Command)
    $matches=@(Get-Command -Name $qualified -ErrorAction Stop)
    if($matches.Count -ne 1){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
    $cmd=$matches[0]
    $step='VERIFY_COMMAND_BINDING'
    if([string]$cmd.ModuleName -ne [string]$spec.ResolvedModule -or [string]$cmd.CommandType -ne [string]$spec.CommandType){{throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}}
    $step='HASH_MANIFEST'
    $rows += [pscustomobject]@{{
      Command=[string]$spec.Command
      Module=[string]$cmd.ModuleName
      CommandType=[string]$cmd.CommandType
      ModuleVersion=[string]$cmd.Module.Version
      ModulePathHash=$(Get-RedactedSha256 ([string]$cmd.Module.Path))
      ManifestSha256=$(Get-FileSha256DotNet ([string]$spec.Manifest))
    }}
  }}
  $step='READ_LANGUAGE_MODE'
  $mode=[string]$ExecutionContext.SessionState.LanguageMode
  [pscustomobject]@{{SchemaVersion=$schema;Available=$true;PowerShellMajor=[int]$PSVersionTable.PSVersion.Major;LanguageMode=$mode;Count=@($rows).Count;Rows=@($rows);ErrorCode='NONE';FailureStep='NONE';ErrorTypeHash=$null}} | ConvertTo-Json -Depth 6 -Compress
}} catch {{
  $safeStep=if($allowedSteps -contains $step){{$step}}else{{'INTERNAL_UNCLASSIFIED'}}
  [pscustomobject]@{{SchemaVersion=$schema;Available=$false;PowerShellMajor=$null;LanguageMode=$null;Count=0;Rows=@();ErrorCode='PROBE_EXCEPTION';FailureStep=$safeStep;ErrorTypeHash=$(Get-RedactedSha256 ($_.Exception.GetType().FullName))}} | ConvertTo-Json -Depth 6 -Compress
}}
""".strip()


POWERSHELL_MODULE_PREFLIGHT_QUERY = _build_powershell_module_preflight_query()


def validate_powershell_module_preflight(value: Any) -> dict[str, Any]:
    fields = {
        "SchemaVersion", "Available", "PowerShellMajor", "LanguageMode",
        "Count", "Rows", "ErrorCode", "FailureStep", "ErrorTypeHash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise IdentityContractError("POWERSHELL_PREFLIGHT_FIELDS_INVALID", "P04")
    if value["SchemaVersion"] != PREFLIGHT_SCHEMA:
        raise IdentityContractError("POWERSHELL_PREFLIGHT_SCHEMA_INVALID", "P04")
    if value["Available"] is not True:
        raise IdentityContractError(
            "POWERSHELL_PREFLIGHT_UNAVAILABLE",
            "P04",
            safe_details={
                "failure_step": value.get("FailureStep"),
                "error_type_hash": (
                    value.get("ErrorTypeHash")
                    if isinstance(value.get("ErrorTypeHash"), str)
                    and _LOWER_SHA256.fullmatch(value["ErrorTypeHash"])
                    else None
                ),
            },
        )
    if (
        value["PowerShellMajor"] != 5
        or value["LanguageMode"] != "FullLanguage"
        or value["ErrorCode"] != "NONE"
        or value["FailureStep"] != "NONE"
        or value["ErrorTypeHash"] is not None
    ):
        raise IdentityContractError("POWERSHELL_PREFLIGHT_STATE_INVALID", "P04")
    rows = value["Rows"]
    if not isinstance(rows, list) or value["Count"] != len(PREFLIGHT_COMMANDS) or len(rows) != len(PREFLIGHT_COMMANDS):
        raise IdentityContractError("POWERSHELL_PREFLIGHT_COUNT_INVALID", "P04")
    row_fields = {
        "Command", "Module", "CommandType", "ModuleVersion",
        "ModulePathHash", "ManifestSha256",
    }
    expected = [(entry[0], entry[2], entry[3]) for entry in PREFLIGHT_COMMANDS]
    observed: list[tuple[str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != row_fields:
            raise IdentityContractError("POWERSHELL_PREFLIGHT_ROW_FIELDS_INVALID", "P04")
        observed.append((row["Command"], row["Module"], row["CommandType"]))
        if not isinstance(row["ModuleVersion"], str) or not row["ModuleVersion"].strip():
            raise IdentityContractError("POWERSHELL_PREFLIGHT_MODULE_VERSION_INVALID", "P04")
        if any(
            not isinstance(row[field], str) or not _LOWER_SHA256.fullmatch(row[field])
            for field in ("ModulePathHash", "ManifestSha256")
        ):
            raise IdentityContractError("POWERSHELL_PREFLIGHT_HASH_INVALID", "P04")
    if observed != expected:
        raise IdentityContractError("POWERSHELL_PREFLIGHT_BINDINGS_INVALID", "P04")
    return value


_SERVER_STRING_FIELDS = (
    "Version", "ApiVersion", "MinAPIVersion", "GitCommit", "GoVersion",
    "Os", "Arch", "KernelVersion", "BuildTime",
)


def _api_alias(section: dict[str, Any], stage: str) -> Any:
    canonical = section.get("ApiVersion")
    alias = section.get("APIVersion")
    if canonical is not None and alias is not None and canonical != alias:
        raise IdentityContractError(
            "DOCKER_API_VERSION_ALIAS_CONFLICT", stage, field="ApiVersion"
        )
    return canonical if canonical is not None else alias


def _normalize_server_value(field: str, value: Any) -> Any:
    if field == "Experimental":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.casefold() in {"true", "false"}:
            return value.casefold() == "true"
        raise IdentityContractError(
            "DOCKER_SERVER_EXPERIMENTAL_INVALID",
            "DOCKER_SERVER",
            field=field,
        )
    if not isinstance(value, str) or not value.strip():
        raise IdentityContractError(
            "DOCKER_SERVER_STRING_INVALID", "DOCKER_SERVER", field=field
        )
    return value


def _engine_component(server: dict[str, Any]) -> dict[str, Any] | None:
    components = server.get("Components")
    if components is None:
        return None
    if not isinstance(components, list):
        raise IdentityContractError(
            "DOCKER_SERVER_COMPONENTS_INVALID", "DOCKER_SERVER", field="Components"
        )
    engines = [
        row for row in components
        if isinstance(row, dict) and row.get("Name") == "Engine"
    ]
    if len(engines) > 1:
        raise IdentityContractError(
            "DOCKER_ENGINE_COMPONENT_AMBIGUOUS", "DOCKER_SERVER", field="Components"
        )
    if not engines:
        return None
    engine = engines[0]
    if not isinstance(engine.get("Details"), dict):
        raise IdentityContractError(
            "DOCKER_ENGINE_DETAILS_INVALID", "DOCKER_SERVER", field="Components"
        )
    return engine


def _field_value(section: dict[str, Any], field: str) -> Any:
    return _api_alias(section, "DOCKER_SERVER") if field == "ApiVersion" else section.get(field)


def _engine_field_value(engine: dict[str, Any] | None, field: str) -> Any:
    if engine is None:
        return None
    if field == "Version":
        return engine.get("Version")
    details = engine["Details"]
    return _api_alias(details, "DOCKER_ENGINE_DETAILS") if field == "ApiVersion" else details.get(field)


def canonicalize_docker_server(version_data: Any) -> tuple[dict[str, Any], dict[str, str], str]:
    if not isinstance(version_data, dict) or set(version_data) != {"Client", "Server"}:
        raise IdentityContractError("DOCKER_VERSION_ROOT_INVALID", "DOCKER_IDENTITY")
    client = version_data["Client"]
    server = version_data["Server"]
    if not isinstance(client, dict) or not isinstance(server, dict):
        raise IdentityContractError("DOCKER_IDENTITY_SECTION_MISSING", "DOCKER_IDENTITY")
    engine = _engine_component(server)
    canonical: dict[str, Any] = {}
    sources: dict[str, str] = {}
    supplemented = False
    for field in (*_SERVER_STRING_FIELDS, "Experimental"):
        root_raw = _field_value(server, field)
        engine_raw = _engine_field_value(engine, field)
        root_value = _normalize_server_value(field, root_raw) if root_raw is not None else None
        engine_value = _normalize_server_value(field, engine_raw) if engine_raw is not None else None
        if root_value is None and engine_value is None:
            raise IdentityContractError(
                "DOCKER_SERVER_FIELD_MISSING", "DOCKER_SERVER", field=field
            )
        if root_value is not None and engine_value is not None and root_value != engine_value:
            raise IdentityContractError(
                "DOCKER_SERVER_FIELD_CONFLICT", "DOCKER_SERVER", field=field
            )
        if root_value is not None:
            canonical[field] = root_value
            sources[field] = (
                "ROOT_CROSSCHECKED_ENGINE_COMPONENT"
                if engine_value is not None else "ROOT"
            )
        else:
            canonical[field] = engine_value
            sources[field] = "ENGINE_COMPONENT_DETAILS"
            supplemented = True
    profile = "ROOT_WITH_ENGINE_COMPONENT_SUPPLEMENT" if supplemented else "ROOT_ONLY"
    return canonical, sources, profile


def sanitize_docker_identity(
    version_data: Any,
    info_data: Any,
    context_data: Any,
) -> tuple[dict[str, Any], dict[str, bool]]:
    canonical_server, sources, profile = canonicalize_docker_server(version_data)
    normalized = {
        "Client": copy.deepcopy(version_data["Client"]),
        "Server": canonical_server,
    }
    sanitized, cross = attempt008.sanitize_docker_identity(
        normalized, info_data, context_data
    )
    sanitized["server"]["IdentitySourceProfile"] = profile
    sanitized["server"]["IdentityFieldSources"] = sources
    return sanitized, cross
