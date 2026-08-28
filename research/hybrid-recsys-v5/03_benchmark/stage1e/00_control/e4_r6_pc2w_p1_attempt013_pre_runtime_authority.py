#!/usr/bin/env python3
"""Pure Attempt-013 one-shot authority boundary; no host I/O at import."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL_POLICY_SCHEMA = "stage1e-e4-r6-pc2w-p1-attempt013-model-policy-1.0"
AUTHORITY_SCHEMA = "stage1e-e4-r6-pc2w-p1-attempt013-pre-runtime-authority-1.0"
LOWER_COMMIT = re.compile(r"^[0-9a-f]{40}$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuthorityError(RuntimeError):
    """Fail closed with a stable, non-sensitive code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ReceiptLocator:
    path: str
    sha256: str


@dataclass(frozen=True)
class AuthorityContract:
    schema_version: str
    stage_id: str
    execution_root: str
    runner_relative: str
    output_relative: str
    packet_commit: str
    expected_head: str
    python_executable: str
    confirmation_token: str
    central_receipt: ReceiptLocator
    fresh_audit_receipt: ReceiptLocator
    model_role: str
    attempts_authorized: int
    attempts_consumed: int
    attempts_remaining: int


@dataclass(frozen=True)
class RuntimeObservation:
    working_directory: str
    git_toplevel: str
    head: str
    model_attestation: dict[str, Any]


@dataclass(frozen=True)
class HandoffBinding:
    execution_root: Path
    runner_path: Path
    output_path: Path
    expected_process_argv: tuple[str, ...]
    model_record: dict[str, Any]
    attempt_budget: tuple[int, int, int]


def _fail(code: str) -> None:
    raise AuthorityError(code)


def strict_json_object(raw: bytes) -> dict[str, Any]:
    """Parse strict UTF-8 object JSON and reject case-fold duplicate keys."""

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        folded: set[str] = set()
        for key, value in pairs:
            normalized = key.casefold()
            if key in result or normalized in folded:
                raise ValueError("duplicate key")
            result[key] = value
            folded.add(normalized)
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_constant=lambda _token: (_ for _ in ()).throw(
                ValueError("non-finite JSON")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        _fail("JSON_INVALID")
    if not isinstance(value, dict):
        _fail("JSON_INVALID")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        _fail(code)


def validate_model_policy(
    policy: dict[str, Any], role: str, attestation: dict[str, Any]
) -> dict[str, Any]:
    _exact_keys(policy, {"schema_version", "roles"}, "MODEL_POLICY_SCHEMA_INVALID")
    if policy.get("schema_version") != MODEL_POLICY_SCHEMA:
        _fail("MODEL_POLICY_SCHEMA_INVALID")
    roles = policy.get("roles")
    if not isinstance(roles, dict) or role not in roles:
        _fail("MODEL_ROLE_INVALID")
    requirement = roles[role]
    required_keys = {
        "requested_model",
        "requested_reasoning_effort",
        "requested_service_tier",
        "requested_display_tier",
        "fast_or_priority_allowed",
    }
    if not isinstance(requirement, dict):
        _fail("MODEL_ROLE_INVALID")
    _exact_keys(requirement, required_keys, "MODEL_ROLE_SCHEMA_INVALID")
    if requirement != {
        "requested_model": "gpt-5.6-sol",
        "requested_reasoning_effort": "xhigh",
        "requested_service_tier": "default",
        "requested_display_tier": "Standard",
        "fast_or_priority_allowed": False,
    }:
        _fail("MODEL_ROLE_REQUIREMENT_MISMATCH")
    attestation_keys = {
        "actual_model",
        "actual_reasoning_effort",
        "actual_service_tier",
        "actual_speed",
        "fast_or_priority_observed",
        "basis",
    }
    _exact_keys(attestation, attestation_keys, "MODEL_ATTESTATION_SCHEMA_INVALID")
    if (
        attestation.get("actual_model") != requirement["requested_model"]
        or attestation.get("actual_reasoning_effort")
        != requirement["requested_reasoning_effort"]
    ):
        _fail("MODEL_OR_REASONING_MISMATCH")
    if attestation.get("fast_or_priority_observed") is not False:
        _fail("FAST_OR_PRIORITY_OBSERVED")
    if attestation.get("actual_service_tier") not in {"default", "UNOBSERVABLE"}:
        _fail("SERVICE_TIER_MISMATCH")
    if attestation.get("actual_speed") not in {"Standard", "UNOBSERVABLE"}:
        _fail("SPEED_MISMATCH")
    if not isinstance(attestation.get("basis"), str) or not attestation["basis"]:
        _fail("MODEL_ATTESTATION_SCHEMA_INVALID")
    return {
        "schema_version": MODEL_POLICY_SCHEMA,
        "role": role,
        "requested": dict(requirement),
        "actual": dict(attestation),
    }


def _canonical_absolute(value: str, code: str) -> Path:
    if not isinstance(value, str) or not value:
        _fail(code)
    candidate = Path(value)
    if not candidate.is_absolute():
        _fail(code)
    return candidate.resolve()


def _contained(root: Path, candidate: Path, code: str) -> None:
    try:
        candidate.relative_to(root)
    except ValueError:
        _fail(code)
    if candidate == root:
        _fail(code)


def _valid_locator(locator: ReceiptLocator) -> None:
    if not isinstance(locator, ReceiptLocator):
        _fail("RECEIPT_LOCATOR_INVALID")
    path = Path(locator.path)
    if (
        path.is_absolute()
        or path.suffix.casefold() != ".json"
        or any(part in {"", ".", ".."} for part in path.parts)
        or LOWER_SHA256.fullmatch(locator.sha256) is None
    ):
        _fail("RECEIPT_LOCATOR_INVALID")


def build_expected_process_argv(contract: AuthorityContract) -> tuple[str, ...]:
    root = _canonical_absolute(contract.execution_root, "ROOT_AUTHORITY_UNBOUND")
    runner = (root / contract.runner_relative).resolve()
    return (
        str(Path(contract.python_executable).resolve()),
        str(runner),
        "--repo-root",
        str(root),
        "--packet-commit",
        contract.packet_commit,
        "--expected-head",
        contract.expected_head,
        "--central-validation-receipt",
        contract.central_receipt.path,
        "--central-validation-receipt-sha256",
        contract.central_receipt.sha256,
        "--fresh-audit-receipt",
        contract.fresh_audit_receipt.path,
        "--fresh-audit-receipt-sha256",
        contract.fresh_audit_receipt.sha256,
        "--execution-confirmation",
        contract.confirmation_token,
    )


def prepare_legacy_handoff(
    contract: AuthorityContract,
    observation: RuntimeObservation,
    model_policy: dict[str, Any],
) -> HandoffBinding:
    if not isinstance(contract, AuthorityContract) or not isinstance(
        observation, RuntimeObservation
    ):
        _fail("AUTHORITY_INPUT_INVALID")
    if contract.schema_version != AUTHORITY_SCHEMA:
        _fail("AUTHORITY_SCHEMA_INVALID")
    root = _canonical_absolute(contract.execution_root, "ROOT_AUTHORITY_UNBOUND")
    cwd = _canonical_absolute(observation.working_directory, "CWD_INVALID")
    git_root = _canonical_absolute(observation.git_toplevel, "GIT_TOPLEVEL_INVALID")
    if cwd != root:
        _fail("CWD_AUTHORITY_MISMATCH")
    if git_root != root:
        _fail("GIT_TOPLEVEL_AUTHORITY_MISMATCH")
    if (
        LOWER_COMMIT.fullmatch(contract.packet_commit) is None
        or LOWER_COMMIT.fullmatch(contract.expected_head) is None
    ):
        _fail("COMMIT_BINDING_INVALID")
    if observation.head.casefold() != contract.expected_head:
        _fail("EXECUTION_HEAD_MISMATCH")
    runner = (root / contract.runner_relative).resolve()
    output = (root / contract.output_relative).resolve()
    _contained(root, runner, "RUNNER_OUTSIDE_AUTHORIZED_ROOT")
    _contained(root, output, "OUTPUT_OUTSIDE_AUTHORIZED_ROOT")
    if output.exists():
        _fail("OUTPUT_ROOT_ALREADY_EXISTS")
    if (
        contract.attempts_authorized,
        contract.attempts_consumed,
        contract.attempts_remaining,
    ) != (1, 0, 1):
        _fail("ATTEMPT_BUDGET_INVALID")
    _valid_locator(contract.central_receipt)
    _valid_locator(contract.fresh_audit_receipt)
    if contract.central_receipt.path == contract.fresh_audit_receipt.path:
        _fail("RECEIPT_LOCATOR_COLLISION")
    model_record = validate_model_policy(
        model_policy, contract.model_role, observation.model_attestation
    )
    expected_process_argv = build_expected_process_argv(contract)
    return HandoffBinding(
        execution_root=root,
        runner_path=runner,
        output_path=output,
        expected_process_argv=expected_process_argv,
        model_record=model_record,
        attempt_budget=(1, 0, 1),
    )
