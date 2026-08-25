#!/usr/bin/env python3
"""Pure Attempt-008 probe/parser seam; this module performs no host I/O."""

from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Any

import execute_e4_r6_pc2w_p1_attempt007_admission_observation as legacy


class IdentityContractError(ValueError):
    """Fail-closed parser error with a stable, non-sensitive locator."""

    def __init__(
        self,
        code: str,
        stage: str,
        *,
        field: str | None = None,
        safe_details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.stage = stage
        self.field = field
        self.safe_details = safe_details or {}
        super().__init__(code)

    def as_record(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "code": self.code,
            "field": self.field,
            "safe_details": self.safe_details,
        }


_DAYS = {name: index for index, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))}
_MONTHS = {
    name: index
    for index, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}
_DOCKER_HUMAN_TIME = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r" ?(\d{1,2}) (\d{2}):(\d{2}):(\d{2}) (\d{4})$"
)
_RFC3339_UTC_TIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"
    r"(?:\.(\d{1,9}))?(Z|[+-]00:00)$"
)


def classify_docker_build_time(value: Any) -> str:
    """Classify a Docker CLI BuildTime without changing the source value."""
    if not isinstance(value, str) or value != value.strip() or not value:
        raise IdentityContractError(
            "DOCKER_BUILD_TIME_MISSING", "DOCKER_IDENTITY", field="BuildTime"
        )
    human = _DOCKER_HUMAN_TIME.fullmatch(value)
    if human is not None:
        day_name, month_name, day, hour, minute, second, year = human.groups()
        try:
            parsed = datetime(
                int(year), _MONTHS[month_name], int(day), int(hour), int(minute), int(second)
            )
        except ValueError as exc:
            raise IdentityContractError(
                "DOCKER_BUILD_TIME_INVALID", "DOCKER_IDENTITY", field="BuildTime"
            ) from exc
        if parsed.weekday() != _DAYS[day_name]:
            raise IdentityContractError(
                "DOCKER_BUILD_TIME_WEEKDAY_MISMATCH",
                "DOCKER_IDENTITY",
                field="BuildTime",
            )
        return "DOCKER_CLI_HUMAN"
    rfc3339 = _RFC3339_UTC_TIME.fullmatch(value)
    if rfc3339 is not None:
        year, month, day, hour, minute, second, _, _ = rfc3339.groups()
        try:
            datetime(
                int(year), int(month), int(day), int(hour), int(minute), int(second)
            )
        except ValueError as exc:
            raise IdentityContractError(
                "DOCKER_BUILD_TIME_INVALID", "DOCKER_IDENTITY", field="BuildTime"
            ) from exc
        return "RFC3339_UTC"
    raise IdentityContractError(
        "DOCKER_BUILD_TIME_FORMAT_UNSUPPORTED", "DOCKER_IDENTITY", field="BuildTime"
    )


_PROCESS_ERROR_CODES = {
    "rich process envelope field set mismatch": "PROCESS_ENVELOPE_FIELDS_INVALID",
    "rich process envelope unavailable": "PROCESS_ENVELOPE_UNAVAILABLE",
    "rich process count invalid": "PROCESS_COUNT_INVALID",
    "rich process Rows invalid": "PROCESS_ROWS_INVALID",
    "rich process row field set mismatch": "PROCESS_ROW_FIELDS_INVALID",
    "rich process name invalid": "PROCESS_NAME_INVALID",
    "rich process integer invalid": "PROCESS_INTEGER_INVALID",
    "duplicate rich process id": "PROCESS_ID_DUPLICATE",
    "rich process hash invalid": "PROCESS_HASH_INVALID",
    "rich process FileVersion missing": "PROCESS_FILE_VERSION_MISSING",
    "rich process signature is not Valid": "PROCESS_SIGNATURE_INVALID",
    "timestamp must be .NET round-trip UTC with seven digits and Z": "PROCESS_CREATION_TIME_INVALID",
    "timestamp is not UTC": "PROCESS_CREATION_TIME_NOT_UTC",
    "rich process rows not canonical": "PROCESS_ROWS_NOT_CANONICAL",
    "required Docker Desktop process identities missing": "PROCESS_REQUIRED_IDENTITIES_MISSING",
}


def _mapped_error(
    exc: ValueError,
    mapping: dict[str, str],
    fallback: str,
    stage: str,
) -> IdentityContractError:
    return IdentityContractError(mapping.get(str(exc), fallback), stage)


def validate_process_identity(value: Any) -> dict[str, Any]:
    """Validate the process envelope at the future Attempt-008 seam."""
    if isinstance(value, dict) and value.get("Available") is False:
        error_hash = value.get("ErrorTypeHash")
        details = {
            "probe_error_code": value.get("ErrorCode"),
            "probe_error_type_hash": error_hash if legacy.valid_hash(error_hash) else None,
        }
        raise IdentityContractError(
            "PROCESS_ENVELOPE_UNAVAILABLE",
            "D01",
            safe_details=details,
        )
    try:
        return legacy.validate_rich_process_envelope(value)
    except ValueError as exc:
        raise _mapped_error(
            exc,
            _PROCESS_ERROR_CODES,
            "PROCESS_CONTRACT_INVALID",
            "D01",
        ) from exc


_TCP_ERROR_CODES = {
    "rich TCP envelope field set mismatch": "TCP_ENVELOPE_FIELDS_INVALID",
    "rich TCP envelope unavailable": "TCP_ENVELOPE_UNAVAILABLE",
    "rich TCP count invalid": "TCP_COUNT_INVALID",
    "rich TCP Rows invalid": "TCP_ROWS_INVALID",
    "rich TCP row field set mismatch": "TCP_ROW_FIELDS_INVALID",
    "rich TCP owner is ambiguous": "TCP_OWNER_AMBIGUOUS",
    "rich TCP State missing": "TCP_STATE_MISSING",
    "rich TCP address hash invalid": "TCP_ADDRESS_HASH_INVALID",
    "rich TCP port invalid": "TCP_PORT_INVALID",
    "duplicate rich TCP row": "TCP_ROW_DUPLICATE",
    "rich TCP rows not canonical": "TCP_ROWS_NOT_CANONICAL",
}


def validate_tcp_identity(value: Any, processes: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("Available") is False:
        error_hash = value.get("ErrorTypeHash")
        raise IdentityContractError(
            "TCP_ENVELOPE_UNAVAILABLE",
            "D02",
            safe_details={
                "probe_error_code": value.get("ErrorCode"),
                "probe_error_type_hash": error_hash if legacy.valid_hash(error_hash) else None,
            },
        )
    try:
        return legacy.validate_rich_tcp_envelope(value, processes)
    except ValueError as exc:
        raise _mapped_error(exc, _TCP_ERROR_CODES, "TCP_CONTRACT_INVALID", "D02") from exc


_FILE_ERROR_CODES = {
    "Docker Desktop file identity field set mismatch": "DESKTOP_FILE_FIELDS_INVALID",
    "Docker Desktop file identity hash invalid": "DESKTOP_FILE_HASH_INVALID",
    "Docker Desktop file byte count invalid": "DESKTOP_FILE_SIZE_INVALID",
    "Docker Desktop version identity missing": "DESKTOP_FILE_VERSION_MISSING",
    "Docker Desktop executable signature is not Valid": "DESKTOP_FILE_SIGNATURE_INVALID",
}


def validate_desktop_file_identity(value: Any) -> dict[str, Any]:
    try:
        return legacy.validate_desktop_file_identity(value)
    except ValueError as exc:
        raise _mapped_error(
            exc,
            _FILE_ERROR_CODES,
            "DESKTOP_FILE_CONTRACT_INVALID",
            "D06",
        ) from exc


_DOCKER_ERROR_CODES = {
    "Docker version identity root invalid": "DOCKER_VERSION_ROOT_INVALID",
    "Docker client, server or info identity missing": "DOCKER_IDENTITY_SECTION_MISSING",
    "Docker client identity field missing": "DOCKER_CLIENT_FIELD_MISSING",
    "Docker server identity field missing": "DOCKER_SERVER_FIELD_MISSING",
    "Docker client identity string missing": "DOCKER_CLIENT_STRING_MISSING",
    "Docker client context missing": "DOCKER_CLIENT_CONTEXT_MISSING",
    "Docker server identity string missing": "DOCKER_SERVER_STRING_MISSING",
    "Docker server Experimental must be boolean": "DOCKER_SERVER_EXPERIMENTAL_INVALID",
    "Docker info identity field missing": "DOCKER_INFO_FIELD_MISSING",
    "Docker info positive integer identity missing": "DOCKER_INFO_POSITIVE_INTEGER_INVALID",
    "Docker info nonnegative counter invalid": "DOCKER_INFO_COUNTER_INVALID",
    "Docker info boolean identity invalid": "DOCKER_INFO_BOOLEAN_INVALID",
    "Docker info containerd identity missing": "DOCKER_INFO_CONTAINERD_MISSING",
    "Docker info runtimes identity missing": "DOCKER_INFO_RUNTIMES_MISSING",
    "Docker info security options malformed": "DOCKER_INFO_SECURITY_OPTIONS_INVALID",
    "Docker context identity malformed": "DOCKER_CONTEXT_INVALID",
}


def _normalize_api_version_alias(section: dict[str, Any], stage: str) -> None:
    canonical = section.get("ApiVersion")
    alias = section.get("APIVersion")
    if canonical is not None and alias is not None and canonical != alias:
        raise IdentityContractError(
            "DOCKER_API_VERSION_ALIAS_CONFLICT", stage, field="ApiVersion"
        )
    if canonical is None and alias is not None:
        section["ApiVersion"] = alias
    section.pop("APIVersion", None)


def sanitize_docker_identity(
    version_data: Any,
    info_data: Any,
    context_data: Any,
) -> tuple[dict[str, Any], dict[str, bool]]:
    """Accept documented Docker CLI time/key variants, preserving raw safe values."""
    normalized = copy.deepcopy(version_data)
    if not isinstance(normalized, dict):
        raise IdentityContractError("DOCKER_VERSION_ROOT_INVALID", "DOCKER_IDENTITY")
    client = normalized.get("Client")
    server = normalized.get("Server")
    if not isinstance(client, dict) or not isinstance(server, dict):
        raise IdentityContractError("DOCKER_IDENTITY_SECTION_MISSING", "DOCKER_IDENTITY")
    _normalize_api_version_alias(client, "DOCKER_CLIENT")
    _normalize_api_version_alias(server, "DOCKER_SERVER")
    raw_client_build_time = client.get("BuildTime")
    raw_server_build_time = server.get("BuildTime")
    client_format = classify_docker_build_time(raw_client_build_time)
    server_format = classify_docker_build_time(raw_server_build_time)
    client["BuildTime"] = "2000-01-01T00:00:00Z"
    server["BuildTime"] = "2000-01-01T00:00:00Z"
    try:
        sanitized, cross = legacy.sanitize_docker_identity(
            normalized, info_data, context_data
        )
    except ValueError as exc:
        raise _mapped_error(
            exc,
            _DOCKER_ERROR_CODES,
            "DOCKER_IDENTITY_CONTRACT_INVALID",
            "DOCKER_IDENTITY",
        ) from exc
    sanitized["client"]["BuildTime"] = raw_client_build_time
    sanitized["client"]["BuildTimeFormat"] = client_format
    sanitized["server"]["BuildTime"] = raw_server_build_time
    sanitized["server"]["BuildTimeFormat"] = server_format
    return sanitized, cross
