#!/usr/bin/env python3
"""Attempt-013 Revision 5 adapter for observed Docker 4.78 identity variants."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.dont_write_bytecode = True
import e4_r6_pc2w_p1_attempt010_command_interface as command_interface
import e4_r6_pc2w_p1_attempt013_packet_lineage as packet_lineage
import e4_r6_pc2w_p1_attempt013_pre_runtime_authority as authority
import e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility as compatibility
import e4_r6_pc2w_p1_gate_receipt_binding as receipt_binding
import execute_e4_r6_pc2w_p1_attempt012_admission_observation as previous


legacy = previous.legacy
CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNTIME_HELPER_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
RUNTIME_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json"
RUNTIME_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
AUTHORITY_HELPER_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py"
AUTHORITY_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json"
AUTHORITY_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py"
LINEAGE_HELPER_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_packet_lineage.py"
LINEAGE_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_packet_lineage_contract.json"
LINEAGE_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt013_packet_lineage.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt013_execution_authorization.json"
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt013_admission_observation.py"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt013_static_packet.py"
R0_COMMIT = "ce6377c351625ed7e029f2883520583ca97fc2b8"
R1_COMMIT = "294422ca8557e4b55ae3863d853289e2232011b2"
R2A_SUPPORT_COMMIT = "1a9ca21c5c8b1b08fdec788fbbf23e88473c117f"
PACKET_PARENT = "d9b7c24065dc5def894d94dcb8eddafd4f89ac1f"
FROZEN_R0_PATHS = (
    RUNTIME_CONTRACT_RELATIVE,
    RUNTIME_TEST_RELATIVE,
    AUTHORITY_CONTRACT_RELATIVE,
    AUTHORITY_TEST_RELATIVE,
)
SUPPORT_PATHS = (
    RUNTIME_HELPER_RELATIVE,
    AUTHORITY_HELPER_RELATIVE,
    LINEAGE_HELPER_RELATIVE,
    LINEAGE_CONTRACT_RELATIVE,
    LINEAGE_TEST_RELATIVE,
)
SEALING_PATHS = (
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
)
PACKET_PATHS = (
    RUNTIME_CONTRACT_RELATIVE,
    RUNTIME_TEST_RELATIVE,
    AUTHORITY_CONTRACT_RELATIVE,
    AUTHORITY_TEST_RELATIVE,
    RUNTIME_HELPER_RELATIVE,
    AUTHORITY_HELPER_RELATIVE,
    LINEAGE_HELPER_RELATIVE,
    LINEAGE_CONTRACT_RELATIVE,
    LINEAGE_TEST_RELATIVE,
    *SEALING_PATHS,
)
PACKET_RELATIVES = set(SEALING_PATHS)
PACKET_ROSTER = tuple(path.as_posix() for path in PACKET_PATHS)
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ay/"
    "E4_R6PC2W_P1_attempt013_revision5_admission_observation"
)
CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_EXACT_ATTEMPT013_REVISION5_PROCESS_COMMAND_WITH_"
    "DASH_B_AND_AUDIT_WAIVER"
)
CENTRAL_RECEIPT_PATH = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision5_central_static_validation_receipt.json"
)
AUDIT_RECEIPT_PATH = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision5_user_audit_waiver_receipt.json"
)
CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-central-static-validation-receipt-1.0"
)
CENTRAL_RECEIPT_VERDICT = "PASS_PC2W_P1_ATTEMPT013_REVISION5_CENTRAL_STATIC_VALIDATION"
AUDIT_RECEIPT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-user-audit-waiver-receipt-1.0"
)
AUDIT_RECEIPT_VERDICT = (
    "USER_OVERRIDE_PC2W_P1_ATTEMPT013_REVISION5_AUDIT_WAIVED_"
    "READY_FOR_EXACT_COMMAND"
)
PASS_VERDICT = (
    "PASS_PC2W_P1_ATTEMPT013_REVISION5_ADMISSION_OBSERVATION_COMPLETE_"
    "FOR_CENTRAL_EVALUATION"
)
FAIL_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT013_REVISION5_CURRENT_HOST_NOT_ADMISSIBLE"
AUTHORITY_CONTRACT_BYTES = 4526
AUTHORITY_CONTRACT_SHA256 = (
    "1cb5d8130420ae543d9f63b4d4cd0b9d16c7571577a5ad506f0217b2ebd530f0"
)
RUNTIME_CONTRACT_BYTES = 4121
RUNTIME_CONTRACT_SHA256 = (
    "ed7d4323e7287643e0372e11cc1a2e6f5b5af73f4ec20fc0d0758dd12e648784"
)
LINEAGE_CONTRACT_BYTES = 2543
LINEAGE_CONTRACT_SHA256 = (
    "520308aa361f100ecd9783ffb022e75f2895195d37f149e5bc34931ca7d6f8a0"
)
ORIGIN_FACTS = {
    RUNTIME_CONTRACT_RELATIVE: (R0_COMMIT, 4121, RUNTIME_CONTRACT_SHA256),
    RUNTIME_TEST_RELATIVE: (
        R0_COMMIT, 11844,
        "36b0e95a7b87a98325da6debfb345cb5a1df96ec672e6f1f3bb35db6b79fc21b",
    ),
    AUTHORITY_CONTRACT_RELATIVE: (R0_COMMIT, 4526, AUTHORITY_CONTRACT_SHA256),
    AUTHORITY_TEST_RELATIVE: (
        R0_COMMIT, 7613,
        "9c372dcd8a4cb4f87dab444a55739966936a930f098999487fd86d6f65a8c437",
    ),
    RUNTIME_HELPER_RELATIVE: (
        R1_COMMIT, 19773,
        "53474c597643fda346d72b251b5dd504a264621ad7daef48fc55663ee86b4614",
    ),
    AUTHORITY_HELPER_RELATIVE: (
        R1_COMMIT, 9084,
        "abdaab61ffcf05e5d5fec8f7731f07804588d6dd06e69754e55b9f522e8eae9d",
    ),
    LINEAGE_HELPER_RELATIVE: (
        R2A_SUPPORT_COMMIT, 8142,
        "d7101a54bb7143df591fb6f32128bbf230c76a859cb21982ab179c0eb32afed5",
    ),
    LINEAGE_CONTRACT_RELATIVE: (
        R2A_SUPPORT_COMMIT, LINEAGE_CONTRACT_BYTES, LINEAGE_CONTRACT_SHA256,
    ),
    LINEAGE_TEST_RELATIVE: (
        R2A_SUPPORT_COMMIT, 10118,
        "0d9fafa87cc586e92ba49b327b63dbe37208041d15e44fdf1552776cd781d58f",
    ),
}

GATE_RECEIPT_SPEC = receipt_binding.GateReceiptSpec(
    stage_id="E4-R6-PC2W-P1-ATTEMPT013",
    packet_files=PACKET_ROSTER,
    central_schema=CENTRAL_RECEIPT_SCHEMA,
    central_verdict=CENTRAL_RECEIPT_VERDICT,
    central_validator_verdict="IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
    fresh_audit_schema=AUDIT_RECEIPT_SCHEMA,
    fresh_audit_verdict=AUDIT_RECEIPT_VERDICT,
)

_FILE_VERSION_SENTINEL = "ABSENT_FROM_PE_METADATA_HASH_AND_SIGNATURE_BOUND"
_FILE_VERSION_READ = (
    "$fileVersion=[string](Get-Item -LiteralPath $path -ErrorAction Stop)."
    "VersionInfo.FileVersion\n"
    "    Require-NonEmpty $fileVersion"
)
_FILE_VERSION_COMPATIBLE_READ = (
    "$fileVersion=[string](Get-Item -LiteralPath $path -ErrorAction Stop)."
    "VersionInfo.FileVersion\n"
    "    if([string]::IsNullOrWhiteSpace($fileVersion)){\n"
    "      if($currentTarget -ne 'com.docker.build'){"
    "throw [InvalidOperationException]::new('PROBE_STEP_FAILED')}\n"
    f"      $fileVersion='{_FILE_VERSION_SENTINEL}'\n"
    "    }"
)
if compatibility.PROCESS_IDENTITY_QUERY_V3.count(_FILE_VERSION_READ) != 1:
    raise RuntimeError("ATTEMPT013_REVISION5_FILE_VERSION_SEAM_DRIFT")
PROCESS_IDENTITY_QUERY_REVISION5 = compatibility.PROCESS_IDENTITY_QUERY_V3.replace(
    _FILE_VERSION_READ, _FILE_VERSION_COMPATIBLE_READ
)

_ARCHITECTURE_ALIASES = {
    "amd64": "amd64",
    "x86_64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def _canonical_architecture(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise compatibility.IdentityContractError(
            "DOCKER_ARCHITECTURE_MISSING", "DOCKER_IDENTITY", field="Architecture"
        )
    normalized = value.strip().casefold()
    if normalized not in _ARCHITECTURE_ALIASES:
        raise compatibility.IdentityContractError(
            "DOCKER_ARCHITECTURE_UNSUPPORTED", "DOCKER_IDENTITY", field="Architecture"
        )
    return _ARCHITECTURE_ALIASES[normalized]


def _sanitize_docker_identity_revision5(
    version_data: Any,
    info_data: Any,
    context_data: Any,
) -> tuple[dict[str, Any], dict[str, bool]]:
    sanitized, cross = compatibility.sanitize_docker_identity(
        version_data, info_data, context_data
    )
    server_arch = sanitized["server"]["Arch"]
    info_arch = sanitized["info"]["Architecture"]
    aliases_match = (
        _canonical_architecture(server_arch) == _canonical_architecture(info_arch)
    )
    cross["info_arch_matches"] = aliases_match
    sanitized["cross_consistency"]["info_arch_matches"] = aliases_match
    return sanitized, cross


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_git_blob(repo_root: Path, revision: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative}"],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("ATTEMPT013_GIT_BLOB_UNRESOLVED")
    return completed.stdout


def _bound_document(repo_root: Path, head: str, relative: Path) -> dict[str, Any]:
    return authority.strict_json_object(
        _read_git_blob(repo_root, head, relative.as_posix())
    )


def _blob_fact(repo_root: Path, revision: str, relative: Path) -> packet_lineage.PacketBlobFact:
    raw = _read_git_blob(repo_root, revision, relative.as_posix())
    return packet_lineage.PacketBlobFact(
        path=relative.as_posix(), raw_bytes=len(raw), raw_sha256=_sha256(raw)
    )


def _origin_binding(
    repo_root: Path,
    packet_commit: str,
    relative: Path,
) -> packet_lineage.OriginBinding:
    origin_commit, expected_bytes, expected_sha256 = ORIGIN_FACTS[relative]
    origin_raw = _read_git_blob(repo_root, origin_commit, relative.as_posix())
    if len(origin_raw) != expected_bytes or _sha256(origin_raw) != expected_sha256:
        raise RuntimeError("ATTEMPT013_REVISION2_ORIGIN_RAW_BINDING_MISMATCH")
    final = _blob_fact(repo_root, packet_commit, relative)
    return packet_lineage.OriginBinding(
        path=relative.as_posix(),
        origin_commit=origin_commit,
        origin_raw_bytes=expected_bytes,
        origin_raw_sha256=expected_sha256,
        final_raw_bytes=final.raw_bytes,
        final_raw_sha256=final.raw_sha256,
    )


def _git_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError("ATTEMPT013_REVISION2_ANCESTRY_QUERY_FAILED")


def _parse_delta(raw: str) -> tuple[packet_lineage.DeltaEntry, ...]:
    entries = []
    for row in raw.splitlines():
        if not row:
            continue
        parts = row.split("\t")
        if len(parts) != 2:
            raise RuntimeError("ATTEMPT013_REVISION2_DELTA_ROW_INVALID")
        entries.append(packet_lineage.DeltaEntry(parts[0], parts[1]))
    return tuple(entries)


def _validate_packet_lineage(
    repo_root: Path,
    packet_commit: str,
    execution_head: str,
) -> packet_lineage.PacketLineageEvidence:
    normalized_commit = packet_commit.casefold()
    lineage_raw = _read_git_blob(
        repo_root, normalized_commit, LINEAGE_CONTRACT_RELATIVE.as_posix()
    )
    if (
        len(lineage_raw) != LINEAGE_CONTRACT_BYTES
        or _sha256(lineage_raw) != LINEAGE_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_REVISION2_LINEAGE_CONTRACT_RAW_MISMATCH")
    lineage_document = authority.strict_json_object(lineage_raw)
    public_seam = lineage_document.get("public_seam")
    if (
        lineage_document.get("schema_version")
        != "stage1e-e4-r6-pc2w-p1-attempt013-revision2-packet-lineage-contract-1.0"
        or not isinstance(public_seam, dict)
        or public_seam.get("module") != packet_lineage.__name__
        or public_seam.get("callable") != "validate_packet_lineage"
        or public_seam.get("pure") is not True
    ):
        raise RuntimeError("ATTEMPT013_REVISION2_LINEAGE_CONTRACT_INVALID")

    parent_row = legacy.git(
        repo_root, "rev-list", "--parents", "-n", "1", normalized_commit
    ).split()
    if not parent_row or parent_row[0].casefold() != normalized_commit:
        raise RuntimeError("ATTEMPT013_REVISION2_PARENT_QUERY_INVALID")
    delta = _parse_delta(legacy.git(
        repo_root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        normalized_commit,
    ))
    spec = packet_lineage.PacketLineageSpec(
        aggregate_roster=PACKET_ROSTER,
        frozen_r0_bindings=tuple(
            _origin_binding(repo_root, normalized_commit, relative)
            for relative in FROZEN_R0_PATHS
        ),
        support_bindings=tuple(
            _origin_binding(repo_root, normalized_commit, relative)
            for relative in SUPPORT_PATHS
        ),
        sealing_parent=PACKET_PARENT,
        expected_sealing_delta=tuple(
            packet_lineage.DeltaEntry("M", relative.as_posix())
            for relative in SEALING_PATHS
        ),
    )
    observation = packet_lineage.PacketLineageObservation(
        packet_commit=normalized_commit,
        packet_parents=tuple(parent.casefold() for parent in parent_row[1:]),
        observed_sealing_delta=delta,
        final_packet_blobs=tuple(
            _blob_fact(repo_root, normalized_commit, relative)
            for relative in PACKET_PATHS
        ),
        packet_is_ancestor_of_execution_head=_git_is_ancestor(
            repo_root, normalized_commit, execution_head
        ),
    )
    return packet_lineage.validate_packet_lineage(spec, observation)


def _validate_contract_owners(
    repo_root: Path, head: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    authority_raw = _read_git_blob(
        repo_root, head, AUTHORITY_CONTRACT_RELATIVE.as_posix()
    )
    runtime_raw = _read_git_blob(
        repo_root, head, RUNTIME_CONTRACT_RELATIVE.as_posix()
    )
    lineage_raw = _read_git_blob(
        repo_root, head, LINEAGE_CONTRACT_RELATIVE.as_posix()
    )
    if (
        len(authority_raw) != AUTHORITY_CONTRACT_BYTES
        or _sha256(authority_raw) != AUTHORITY_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_AUTHORITY_OWNER_RAW_BINDING_MISMATCH")
    if (
        len(runtime_raw) != RUNTIME_CONTRACT_BYTES
        or _sha256(runtime_raw) != RUNTIME_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_RUNTIME_OWNER_RAW_BINDING_MISMATCH")
    if (
        len(lineage_raw) != LINEAGE_CONTRACT_BYTES
        or _sha256(lineage_raw) != LINEAGE_CONTRACT_SHA256
    ):
        raise RuntimeError("ATTEMPT013_REVISION2_LINEAGE_OWNER_RAW_BINDING_MISMATCH")
    owner = authority.strict_json_object(authority_raw)
    runtime_owner = authority.strict_json_object(runtime_raw)
    contract = _bound_document(repo_root, head, CONTRACT_RELATIVE)
    authorization = _bound_document(repo_root, head, AUTHORIZATION_RELATIVE)
    expected_authority = {
        "path": AUTHORITY_CONTRACT_RELATIVE.as_posix(),
        "raw_git_blob_bytes": AUTHORITY_CONTRACT_BYTES,
        "raw_git_blob_sha256": AUTHORITY_CONTRACT_SHA256,
    }
    expected_runtime = {
        "path": RUNTIME_CONTRACT_RELATIVE.as_posix(),
        "raw_git_blob_bytes": RUNTIME_CONTRACT_BYTES,
        "raw_git_blob_sha256": RUNTIME_CONTRACT_SHA256,
    }
    expected_lineage = {
        "path": LINEAGE_CONTRACT_RELATIVE.as_posix(),
        "raw_git_blob_bytes": LINEAGE_CONTRACT_BYTES,
        "raw_git_blob_sha256": LINEAGE_CONTRACT_SHA256,
        "schema_version": (
            "stage1e-e4-r6-pc2w-p1-attempt013-revision2-"
            "packet-lineage-contract-1.0"
        ),
        "public_seam": (
            "e4_r6_pc2w_p1_attempt013_packet_lineage.validate_packet_lineage"
        ),
    }
    for document in (contract, authorization):
        authority_binding = document.get("pre_runtime_authority_binding")
        runtime_binding = document.get("runtime_identity_compatibility_binding")
        lineage_binding = document.get("packet_lineage_binding")
        if not isinstance(authority_binding, dict) or any(
            authority_binding.get(key) != value
            for key, value in expected_authority.items()
        ):
            raise RuntimeError("ATTEMPT013_AUTHORITY_CONSUMER_BINDING_MISMATCH")
        if not isinstance(runtime_binding, dict) or any(
            runtime_binding.get(key) != value
            for key, value in expected_runtime.items()
        ):
            raise RuntimeError("ATTEMPT013_RUNTIME_CONSUMER_BINDING_MISMATCH")
        if not isinstance(lineage_binding, dict) or any(
            lineage_binding.get(key) != value
            for key, value in expected_lineage.items()
        ):
            raise RuntimeError("ATTEMPT013_REVISION2_LINEAGE_CONSUMER_BINDING_MISMATCH")
        if (
            authority_binding.get("restated_authority_values") is not False
            or runtime_binding.get("restated_seam_values") is not False
            or lineage_binding.get("restated_lineage_values") is not False
        ):
            raise RuntimeError("ATTEMPT013_CONSUMER_RESTATED_VALUES")
    return owner, runtime_owner, contract, authorization


def _legacy_model_compatibility_view() -> dict[str, Any]:
    """Non-authoritative shape needed only by the retained legacy predicate."""

    return {
        "requested_model": "gpt-5.6-sol",
        "requested_reasoning_effort": "max",
        "requested_service_tier": "default",
        "requested_display_name": "Sol Max Standard",
        "fresh_audit_requested_model": "gpt-5.6-sol",
        "fresh_audit_requested_reasoning_effort": "xhigh",
        "fast_or_priority_allowed": False,
        "actual_model_reasoning_and_service_tier": "UNOBSERVABLE",
    }


def _adapted_load_json(path: Path) -> dict[str, Any]:
    document = previous.previous.previous.previous._ORIGINAL_LOAD_JSON(path)
    if path.name == CONTRACT_RELATIVE.name:
        document = copy.deepcopy(document)
        document["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-contract-2.0"
        )
        document["model_policy"] = _legacy_model_compatibility_view()
    elif path.name == AUTHORIZATION_RELATIVE.name:
        document = copy.deepcopy(document)
        document["schema_version"] = (
            "stage1e-e4-r6-pc2w-p1-attempt008-execution-authorization-2.0"
        )
        document["user_decision"] = {
            "status": "CONFIRMED",
            "confirmed_scope": "REPAIR_PROBE_PARSER_AND_PREPARE_ATTEMPT008_DORMANT_PACKET",
            "runtime_execution_authorized_now": False,
            "exact_process_command_confirmed_now": False,
        }
        document["model_policy"] = _legacy_model_compatibility_view()
    return document


def _adapted_document(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(value)
    schemas = {
        "command_receipts.json": "stage1e-e4-r6-pc2w-p1-attempt013-revision5-command-receipts-1.0",
        "admission_observation.json": "stage1e-e4-r6-pc2w-p1-attempt013-revision5-admission-observation-1.0",
        "execution_receipt.json": "stage1e-e4-r6-pc2w-p1-attempt013-revision5-execution-receipt-1.0",
        "handoff.json": "stage1e-e4-r6-pc2w-p1-attempt013-revision5-handoff-1.0",
    }
    if path.name in schemas:
        document["schema_version"] = schemas[path.name]
        document["stage_id"] = GATE_RECEIPT_SPEC.stage_id
    gate_receipts = document.get("gate_receipts")
    if isinstance(gate_receipts, dict) and (
        "central_validation_receipt" in gate_receipts
        and "user_audit_waiver_receipt" in gate_receipts
        and "fresh_independent_audit_receipt" not in gate_receipts
    ):
        gate_receipts["fresh_independent_audit_performed"] = False
    pass_conditions = document.get("pass_conditions")
    if isinstance(pass_conditions, dict) and (
        "central_validation_and_fresh_audit_bound" in pass_conditions
    ):
        pass_conditions[
            "central_validation_and_user_audit_waiver_bound"
        ] = pass_conditions.pop("central_validation_and_fresh_audit_bound")
    return document


def _adapted_write_json(path: Path, value: dict[str, Any]) -> None:
    previous.previous.previous.previous._ORIGINAL_WRITE_JSON(
        path, _adapted_document(path, value)
    )


def _runtime_passport(created_at: str, authorization: dict[str, Any]) -> dict[str, Any]:
    intake = authorization.get("material_passport", {}).get(
        "experiment_intake_declaration"
    )
    if not isinstance(intake, dict):
        raise RuntimeError("ATTEMPT013_AUTHORIZATION_INTAKE_MISSING")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": (
            "stage1e_e4_r6_pc2w_p1_attempt013_revision5_"
            "admission_observation_execution_v1"
        ),
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt013_revision5_admission_observation_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_revision5_execution_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_revision2_packet_lineage_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": copy.deepcopy(intake),
        "experiment_provenance": [],
    }


def _validate_frozen_upstream(repo_root: Path, head: str) -> dict[str, Any]:
    result = previous._validate_frozen_upstream(repo_root, head)
    facts = []
    for relative in sorted(
        FROZEN_R0_PATHS, key=lambda item: item.as_posix()
    ):
        _origin_commit, expected_bytes, expected_sha256 = ORIGIN_FACTS[relative]
        raw = _read_git_blob(repo_root, head, relative.as_posix())
        if len(raw) != expected_bytes or _sha256(raw) != expected_sha256:
            raise RuntimeError("ATTEMPT013_FROZEN_R0_HASH_MISMATCH")
        facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": len(raw),
            "git_blob_sha256": expected_sha256,
        })
    result["attempt013_frozen_r0_artifact_count"] = len(facts)
    result["attempt013_frozen_r0_artifacts"] = facts
    result["attempt013_parent_resolution_schema"] = compatibility.PROBE_SCHEMA
    result["attempt013_authority_schema"] = authority.AUTHORITY_SCHEMA
    result["attempt013_model_policy_schema"] = authority.MODEL_POLICY_SCHEMA
    return result


def _validate_bound_gate_receipts(
    repo_root: Path,
    head: str,
    packet_commit: str,
    central_path: Path,
    central_sha256: str,
    audit_path: Path,
    audit_sha256: str,
) -> dict[str, Any]:
    result = receipt_binding.validate_bound_gate_receipts(
        repository_root=repo_root,
        execution_head=head,
        packet_commit=packet_commit,
        spec=GATE_RECEIPT_SPEC,
        central_locator=receipt_binding.ReceiptLocator(
            central_path.as_posix(), central_sha256
        ),
        fresh_audit_locator=receipt_binding.ReceiptLocator(
            audit_path.as_posix(), audit_sha256
        ),
        read_git_blob=_read_git_blob,
    )
    result["user_audit_waiver_receipt"] = result.pop(
        "fresh_independent_audit_receipt"
    )
    return result


def _parse_parameters() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--packet-commit", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--central-validation-receipt", required=True)
    parser.add_argument("--central-validation-receipt-sha256", required=True)
    parser.add_argument("--fresh-audit-receipt", required=True)
    parser.add_argument("--fresh-audit-receipt-sha256", required=True)
    parser.add_argument("--execution-confirmation", required=True)
    return parser.parse_args()


def configure_attempt013_runner() -> None:
    previous.configure_attempt012_runner()
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
    legacy.PROCESS_IDENTITY_QUERY = compatibility.wrap_process_identity_probe(
        PROCESS_IDENTITY_QUERY_REVISION5
    )
    legacy.TCP_IDENTITY_QUERY = compatibility.wrap_tcp_identity_probe(
        compatibility.TCP_IDENTITY_QUERY_V3
    )
    legacy.probes_v2 = compatibility
    legacy.parser_v2 = SimpleNamespace(
        IdentityContractError=compatibility.IdentityContractError,
        sanitize_docker_identity=_sanitize_docker_identity_revision5,
    )
    legacy.load_json = _adapted_load_json
    legacy.write_json = _adapted_write_json
    legacy.passport = _runtime_passport
    legacy.validate_frozen_upstream = _validate_frozen_upstream
    legacy.validate_gate_receipts = _validate_bound_gate_receipts


def main() -> int:
    args = _parse_parameters()
    repo_root = Path(args.repo_root).resolve()
    head = legacy.git(repo_root, "rev-parse", "HEAD").casefold()
    git_toplevel = str(
        Path(legacy.git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    )
    owner, _runtime_owner, contract_document, authorization_document = (
        _validate_contract_owners(repo_root, head)
    )
    receipt_contract = contract_document.get("receipt_contract")
    if not isinstance(receipt_contract, dict) or (
        authorization_document.get("receipt_contract") != receipt_contract
        or
        receipt_contract.get("central_path") != CENTRAL_RECEIPT_PATH.as_posix()
        or receipt_contract.get("central_schema") != CENTRAL_RECEIPT_SCHEMA
        or receipt_contract.get("central_verdict") != CENTRAL_RECEIPT_VERDICT
        or receipt_contract.get("fresh_audit_path") != AUDIT_RECEIPT_PATH.as_posix()
        or receipt_contract.get("fresh_audit_schema") != AUDIT_RECEIPT_SCHEMA
        or receipt_contract.get("fresh_audit_verdict") != AUDIT_RECEIPT_VERDICT
        or receipt_contract.get("fresh_audit_must_link_central_raw_sha256") is not True
        or receipt_contract.get("fresh_audit_requirement") != "WAIVED_BY_CURRENT_USER"
        or receipt_contract.get("fresh_audit_receipt_semantics")
        != "USER_OVERRIDE_NOT_AN_INDEPENDENT_AUDIT"
        or receipt_contract.get("user_override_confirmation")
        != "CURRENT_USER_IF_FAILURE_AUDIT_AND_FIX_STANDING_AUTHORITY_2026_08_30"
        or receipt_contract.get("attempt012_receipts_accepted") is not False
        or receipt_contract.get("attempt013_revision1_receipts_accepted") is not False
        or receipt_contract.get("attempt013_revision2_receipts_accepted") is not False
        or receipt_contract.get("attempt013_revision3_receipts_accepted") is not False
        or receipt_contract.get("attempt013_revision4_receipts_accepted") is not False
    ):
        raise RuntimeError("ATTEMPT013_RECEIPT_CONTRACT_MISMATCH")
    exact_command_contract = contract_document.get("exact_process_command_contract")
    expected_exact_command_contract = {
        "required_original_argv_prefix": [
            "PYTHON_EXECUTABLE", "-B", "RUNNER_PATH"
        ],
        "required_interpreter_flags": ["-B"],
        "required_interpreter_flag_count": 1,
        "machine_checked_by": (
            "e4_r6_pc2w_p1_attempt010_command_interface."
            "bind_exact_python_script_argv"
        ),
        "revision2_failure_error_sha256": (
            "4190f8dce17455e17eb3615e06ccbfd23249346e5bdcfec01a5aa085b47212b4"
        ),
        "revision2_failure_stable_code": "INTERPRETER_FLAGS_EXACT_MISMATCH",
        "revision2_may_be_reinvoked": False,
    }
    if (
        exact_command_contract != expected_exact_command_contract
        or authorization_document.get("exact_process_command_contract")
        != expected_exact_command_contract
        or command_interface.REQUIRED_INTERPRETER_FLAGS != ("-B",)
    ):
        raise RuntimeError("ATTEMPT013_REVISION5_EXACT_COMMAND_CONTRACT_MISMATCH")
    expected_adapter_contract = {
        "module_chain": [
            "ATTEMPT013", "ATTEMPT012", "ATTEMPT011", "ATTEMPT010",
            "ATTEMPT009",
        ],
        "original_json_io_owner": "ATTEMPT009",
        "load_reference": (
            "previous.previous.previous.previous._ORIGINAL_LOAD_JSON"
        ),
        "write_reference": (
            "previous.previous.previous.previous._ORIGINAL_WRITE_JSON"
        ),
        "forbidden_three_hop_reference": True,
        "revision3_failure_error_sha256": (
            "a76a4582be67134579d5f7224a7d76dbb4411750b3b517d0de5b4a88c3395c80"
        ),
        "revision3_may_be_reinvoked": False,
    }
    if (
        contract_document.get("adapter_ancestry_contract")
        != expected_adapter_contract
        or authorization_document.get("adapter_ancestry_contract")
        != expected_adapter_contract
        or not hasattr(
            previous.previous.previous.previous, "_ORIGINAL_LOAD_JSON"
        )
        or not hasattr(
            previous.previous.previous.previous, "_ORIGINAL_WRITE_JSON"
        )
    ):
        raise RuntimeError("ATTEMPT013_REVISION5_ADAPTER_ANCESTRY_MISMATCH")
    owner_contract = owner.get("authority_contract")
    budget = owner_contract.get("attempt_budget") if isinstance(owner_contract, dict) else None
    if not isinstance(budget, dict):
        raise RuntimeError("ATTEMPT013_BUDGET_OWNER_MISSING")
    handoff_contract = authority.AuthorityContract(
        schema_version=authority.AUTHORITY_SCHEMA,
        stage_id=GATE_RECEIPT_SPEC.stage_id,
        execution_root=str(repo_root),
        runner_relative=RUNNER_RELATIVE.as_posix(),
        output_relative=OUTPUT_RELATIVE.as_posix(),
        packet_commit=str(args.packet_commit).casefold(),
        expected_head=str(args.expected_head).casefold(),
        python_executable=str(legacy.PYTHON.resolve()),
        confirmation_token=CONFIRMATION_TOKEN,
        central_receipt=authority.ReceiptLocator(
            str(args.central_validation_receipt),
            str(args.central_validation_receipt_sha256),
        ),
        fresh_audit_receipt=authority.ReceiptLocator(
            str(args.fresh_audit_receipt),
            str(args.fresh_audit_receipt_sha256),
        ),
        model_role="locked_execution",
        attempts_authorized=budget.get("authorized"),
        attempts_consumed=budget.get("consumed"),
        attempts_remaining=budget.get("remaining"),
    )
    observation = authority.RuntimeObservation(
        working_directory=str(Path.cwd().resolve()),
        git_toplevel=git_toplevel,
        head=head,
        model_attestation=authorization_document.get(
            "implementation_model_observation", {}
        ),
    )
    binding = authority.prepare_legacy_handoff(
        handoff_contract, observation, owner.get("model_policy", {})
    )
    if binding.runner_path != Path(__file__).resolve():
        raise RuntimeError("ATTEMPT013_RUNNER_PATH_BINDING_MISMATCH")
    command_binding = command_interface.bind_exact_python_script_argv(
        list(getattr(sys, "orig_argv", [])), binding.expected_process_argv
    )
    lineage_evidence = _validate_packet_lineage(
        repo_root, str(args.packet_commit), head
    )
    if lineage_evidence.predicate_passed is not True:
        raise RuntimeError("ATTEMPT013_REVISION5_LINEAGE_PREDICATE_DID_NOT_PASS")
    configure_attempt013_runner()
    previous.previous.previous._COMMAND_BINDING = command_binding
    original = list(getattr(sys, "orig_argv", []))
    sys.orig_argv = list(command_binding.normalized_argv)
    legacy.EXPECTED_EXECUTION_ROOT = binding.execution_root
    try:
        return legacy.main()
    finally:
        sys.orig_argv = original


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
