#!/usr/bin/env python3
"""Offline, read-only static audit for the Attempt-006 baseline packet."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt006_baseline_remediation.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt006_baseline_remediation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt006_user_authorization.json"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt006_static_packet.py"
STATE = CONTROL / "pipeline_state_stage1e.json"
PACKET_PARENT = "c4d471a5ac5c9e763e66a1d7288367c5c905e1e9"
PACKET_FILES = {RUNNER, CONTRACT, AUTHORIZATION, VALIDATOR}
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/"
    "E4_R6PC2W_P1_attempt006_baseline_remediation"
)
OUTPUT_FILES = [
    "command_receipts.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
    "runtime_inventory.json",
]
FROZEN_ATTEMPT005_SHA256 = {
    CONTROL / "e4_r6_pc2w_p1_attempt005_instrumented_contract.json":
        "cf022505edcaba11e49a00e8b43e180796870679fa20647923ddba9158e5096b",
    CONTROL / "execute_e4_r6_pc2w_p1_attempt005_instrumented.py":
        "8e595d892a2548458b83c1cbbe1b332243c101554e21fa06ae725a198856e1e9",
    CONTROL / "validate_e4_r6_pc2w_p1_attempt005_static_packet.py":
        "8d2973fa7d119ecb0adb3b81f0c3f201dab181d87b092a40e622391359567d2c",
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt005_failure_receipt.json":
        "9e8432933c83e8ca4e8a40e189c85b9b076cd2f44a32fe844991c6b06646a0cf",
    STATE: "0e7865bc56efa78ec65e49c2b360aa41e1d2a3f499424944087900d6b1a0533a",
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
ERROR_CODES = {"NONE", "PROBE_EXCEPTION", "COMMAND_FAILED", "OUTPUT_MALFORMED"}
EXPECTED_COMMAND_TEMPLATES = {
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
EXPECTED_WITH_REMEDIATION = [
    "B00", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09",
    "B10", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19",
]
EXPECTED_ALREADY_CLOSED = [
    "B00", "B01", "B02", "B03", "B04", "B07", "B08", "B09", "B10",
    "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19",
]
EXPECTED_DIRECT_INVOKES = [
    ("B00", "DOCKER_DESKTOP_STATUS"),
    ("B01", "WSL_VERBOSE"),
    ("B02", "WSL_RUNNING"),
    ("B03", "PROCESS_POPULATION"),
    ("B04", "TCP_POPULATION"),
    ("B05", "DOCKER_DESKTOP_STOP"),
    ("B06", "WSL_SHUTDOWN"),
    ("B07", "DOCKER_DESKTOP_STATUS"),
]
EXPECTED_SNAPSHOT_CALLS = [
    ("A", "B08", "B09", "B10", "B11"),
    ("B", "B12", "B13", "B14", "B15"),
    ("C", "B16", "B17", "B18", "B19"),
]
EXPECTED_MODEL_POLICY = {
    "requested_model": "gpt-5.6-sol",
    "requested_reasoning_effort": "xhigh",
    "requested_service_tier": "default",
    "display_name": "Sol XHigh Standard",
    "fast_or_priority_allowed": False,
    "actual_model": "UNOBSERVABLE",
    "actual_reasoning_effort": "UNOBSERVABLE",
    "actual_service_tier": "UNOBSERVABLE",
    "fast_or_priority_observability": "UNOBSERVABLE",
}
EXPECTED_VERDICTS = [
    "PASS_PC2W_P1_ATTEMPT006_BASELINE_REMEDIATED_READY_FOR_ADMISSION_PACKET",
    "FAIL_CLOSED_PC2W_P1_ATTEMPT006_BASELINE_NOT_CLOSED",
    "HANDOFF_INCOMPLETE",
]


class DuplicateKeyError(ValueError):
    pass


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


def strict_json_bytes(value: bytes) -> Any:
    return json.loads(
        value.decode("utf-8", errors="strict"),
        object_pairs_hook=strict_pairs,
        parse_constant=reject_nonfinite,
    )


def canonical_lf(value: bytes) -> bytes:
    normalized = value.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("bare carriage return")
    return normalized


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    ).stdout


def git_text(root: Path, *args: str) -> str:
    return run_git(root, *args).decode("utf-8", errors="strict").strip()


def git_blob(root: Path, revision: str, path: Path) -> bytes:
    return run_git(root, "cat-file", "blob", f"{revision}:{path.as_posix()}")


def assigned_literal(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def assigned_stripped_string(tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "strip"
            and not value.args
            and not value.keywords
        ):
            literal = ast.literal_eval(value.func.value)
            if isinstance(literal, str):
                return literal.strip()
    raise KeyError(name)


def assigned_path_string(tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "Path"
            and len(value.args) == 1
            and not value.keywords
        ):
            literal = ast.literal_eval(value.args[0])
            if isinstance(literal, str):
                return literal
    raise KeyError(name)


def find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        ),
        None,
    )


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def literal_call_tuple(node: ast.Call, function_name: str, width: int) -> tuple[str, ...] | None:
    if call_name(node) != function_name or len(node.args) < width:
        return None
    values: list[str] = []
    for argument in node.args[:width]:
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            return None
        values.append(argument.value)
    return tuple(values)


def literal_calls(tree: ast.AST, function_name: str, width: int) -> list[tuple[str, ...]]:
    rows = [
        (node.lineno, value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (value := literal_call_tuple(node, function_name, width)) is not None
    ]
    return [value for _, value in sorted(rows)]


def validate_population_envelope(value: Any, kind: str) -> tuple[bool, bool]:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        return False, False
    available = value.get("Available")
    count = value.get("Count")
    rows = value.get("Rows")
    error_code = value.get("ErrorCode")
    error_hash = value.get("ErrorTypeHash")
    if not isinstance(available, bool):
        return False, False
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return False, False
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return False, False
    if count != len(rows) or error_code not in ERROR_CODES:
        return False, False
    if available:
        if error_code != "NONE" or error_hash is not None:
            return False, False
    else:
        if (
            error_code == "NONE"
            or not isinstance(error_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", error_hash) is None
            or count != 0
            or bool(rows)
        ):
            return False, False
    expected_fields = {"Name", "ProcessId"} if kind == "process" else {"Name", "ProcessId", "ConnectionCount"}
    seen_names: set[str] = set()
    for row in rows:
        if set(row) != expected_fields:
            return False, False
        name = row.get("Name")
        process_id = row.get("ProcessId")
        if (
            not isinstance(name, str)
            or name != name.casefold()
            or name not in TARGET_PROCESS_NAMES
            or name.casefold() in seen_names
        ):
            return False, False
        seen_names.add(name.casefold())
        if not isinstance(process_id, int) or isinstance(process_id, bool) or process_id <= 0:
            return False, False
        if kind == "tcp":
            connection_count = row.get("ConnectionCount")
            if (
                not isinstance(connection_count, int)
                or isinstance(connection_count, bool)
                or connection_count <= 0
            ):
                return False, False
    if rows != sorted(rows, key=lambda row: (str(row["Name"]).casefold(), int(row["ProcessId"]))):
        return False, False
    return True, available and count == 0 and rows == []


def passport_ok(value: Any, mode: str, version_label: str) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("origin_skill") == "experiment-agent"
        and value.get("origin_mode") == mode
        and isinstance(value.get("origin_date"), str)
        and value.get("verification_status") == "UNVERIFIED"
        and value.get("version_label") == version_label
        and isinstance(value.get("upstream_dependencies"), list)
        and value.get("repro_lock") is None
        and isinstance(value.get("experiment_intake_declaration"), dict)
        and value["experiment_intake_declaration"].get("status") == "no_experiments_declared"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    head = git_text(root, "rev-parse", "HEAD").casefold()
    check("expected_head_format", re.fullmatch(r"[0-9a-f]{40}", args.expected_head.casefold()) is not None)
    check("expected_head_exact", head == args.expected_head.casefold())
    check("worktree_clean", git_text(root, "status", "--porcelain=v1", "--untracked-files=all") == "")
    parent_row = git_text(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    check("single_parent", len(parent_row) == 2)
    check("exact_packet_parent", len(parent_row) == 2 and parent_row[1].casefold() == PACKET_PARENT)
    name_status_lines = git_text(
        root, "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"
    ).splitlines()
    name_status: dict[str, str] = {}
    name_status_well_formed = True
    for line in name_status_lines:
        parts = line.split("\t")
        if len(parts) != 2 or parts[1] in name_status:
            name_status_well_formed = False
            continue
        name_status[parts[1]] = parts[0]
    expected_paths = {path.as_posix() for path in PACKET_FILES}
    check("delta_name_status_well_formed", name_status_well_formed)
    check("delta_exact_four_paths", set(name_status) == expected_paths and len(name_status) == 4)
    check("delta_all_new_files", set(name_status.values()) == {"A"})
    check("output_root_not_present", not (root / OUTPUT_ROOT).exists())
    check(
        "output_root_not_tracked",
        git_text(root, "ls-tree", "-r", "--name-only", "HEAD", "--", OUTPUT_ROOT.as_posix()) == "",
    )

    blobs: dict[Path, bytes] = {}
    for path in sorted(PACKET_FILES, key=lambda value: value.as_posix()):
        try:
            blob = git_blob(root, head, path)
            blobs[path] = blob
            check(f"packet_blob_exists:{path.name}", True)
            try:
                normalized = canonical_lf(blob)
                check(f"packet_bare_cr_absent:{path.name}", True)
                check(f"packet_canonical_lf:{path.name}", normalized == blob)
            except ValueError:
                check(f"packet_bare_cr_absent:{path.name}", False)
                check(f"packet_canonical_lf:{path.name}", False)
        except subprocess.CalledProcessError:
            blobs[path] = b""
            check(f"packet_blob_exists:{path.name}", False)
            check(f"packet_bare_cr_absent:{path.name}", False)
            check(f"packet_canonical_lf:{path.name}", False)

    for path, expected_sha256 in sorted(
        FROZEN_ATTEMPT005_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        try:
            blob = git_blob(root, head, path)
            check(f"attempt005_blob_exists:{path.name}", True)
            check(f"attempt005_blob_sha256:{path.name}", sha256_bytes(blob) == expected_sha256)
            try:
                canonical_lf(blob)
                check(f"attempt005_bare_cr_absent:{path.name}", True)
            except ValueError:
                check(f"attempt005_bare_cr_absent:{path.name}", False)
        except subprocess.CalledProcessError:
            check(f"attempt005_blob_exists:{path.name}", False)
            check(f"attempt005_blob_sha256:{path.name}", False)
            check(f"attempt005_bare_cr_absent:{path.name}", False)

    try:
        contract = strict_json_bytes(blobs.get(CONTRACT, b""))
        check("contract_strict_json", isinstance(contract, dict))
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
        contract = {}
        check("contract_strict_json", False)
    try:
        authorization = strict_json_bytes(blobs.get(AUTHORIZATION, b""))
        check("authorization_strict_json", isinstance(authorization, dict))
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
        authorization = {}
        check("authorization_strict_json", False)
    try:
        state = strict_json_bytes(git_blob(root, head, STATE))
        check("pipeline_state_strict_json", isinstance(state, dict))
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError):
        state = {}
        check("pipeline_state_strict_json", False)

    strict_json_negative = {
        "duplicate": b'{"x":1,"x":2}',
        "casefold_duplicate": b'{"x":1,"X":2}',
        "nan": b'{"x":NaN}',
        "positive_infinity": b'{"x":Infinity}',
        "negative_infinity": b'{"x":-Infinity}',
    }
    for name, fixture in strict_json_negative.items():
        try:
            strict_json_bytes(fixture)
            rejected = False
        except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
            rejected = True
        check(f"strict_json_fixture_rejected:{name}", rejected)

    check(
        "contract_schema",
        contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt006-baseline-remediation-contract-1.0",
    )
    check("contract_stage", contract.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT006")
    check(
        "contract_material_passport_schema9",
        passport_ok(
            contract.get("material_passport"),
            "plan",
            "stage1e_e4_r6_pc2w_p1_attempt006_baseline_remediation_contract_v1",
        ),
    )
    auth_boundary = contract.get("authorization_boundary", {})
    check("contract_current_text_exact", auth_boundary.get("current_user_text") == "Xác nhận")
    check("contract_preparation_authorized", auth_boundary.get("packet_preparation_authorized") is True)
    check("contract_execution_false", auth_boundary.get("execution_authorized") is False)
    check("contract_exact_command_unconfirmed", auth_boundary.get("exact_process_command_confirmed") is False)
    check(
        "contract_separate_confirmation_required",
        auth_boundary.get("exact_process_command_confirmation_required_after_static_audit") is True,
    )
    immutable = contract.get("attempt_immutability", {})
    check("contract_attempt005_immutable", immutable.get("attempt005_preserved_immutable") is True)
    check(
        "contract_attempt005_verdict_preserved",
        immutable.get("attempt005_verdict_preserved") == "FAIL_CLOSED_PC2W_P1_ATTEMPT005_CURRENT_HOST_NOT_ADMISSIBLE",
    )
    expected_frozen = {path.as_posix(): value for path, value in FROZEN_ATTEMPT005_SHA256.items()}
    check("contract_exact_frozen_attempt005_map", immutable.get("frozen_attempt005_artifacts") == expected_frozen)
    algorithm = contract.get("baseline_algorithm", {})
    check("contract_pre_gate_once", algorithm.get("pre_baseline_native_closure_is_replayed_once") is True)
    check(
        "contract_prepass_zero_mutation",
        algorithm.get("if_pre_baseline_all_lanes_pass", {}).get("mutation_commands") == 0,
    )
    failed_path = algorithm.get("if_pre_baseline_any_lane_fails", {})
    check("contract_failed_path_one_stop", failed_path.get("docker_desktop_stop_attempts_exactly") == 1)
    check("contract_failed_path_one_shutdown", failed_path.get("wsl_shutdown_attempts_exactly_after_stop") == 1)
    check("contract_shutdown_nested_finally", failed_path.get("wsl_shutdown_is_in_nested_finally") is True)
    for field in (
        "automatic_retry_count", "fallback_count", "docker_desktop_start_attempts",
        "docker_daemon_queries", "force_kill_count", "service_restart_count",
        "settings_change_count", "install_or_download_count", "network_operation_count",
        "image_pull_build_create_run_count",
    ):
        check(f"contract_zero:{field}", algorithm.get(field) == 0)
    probes = contract.get("lightweight_population_probes", {})
    check("contract_lightweight_separate", probes.get("separate_from_rich_identity") is True)
    check("contract_no_path_requirement", probes.get("pre_and_post_do_not_require_executable_path") is True)
    check("contract_no_signature_requirement", probes.get("pre_and_post_do_not_require_signature") is True)
    check(
        "contract_exact_envelope_fields",
        probes.get("exact_envelope_fields") == ["Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"],
    )
    check("contract_closed_error_codes", set(probes.get("closed_error_codes", [])) == ERROR_CODES)
    check(
        "contract_available_false_valid_but_ineligible",
        probes.get("unavailable_envelope_can_be_structurally_valid_but_is_gate_ineligible") is True,
    )
    closure = contract.get("closure", {})
    check("contract_settle_20", closure.get("settling_seconds") == 20)
    check("contract_snapshots_abc", closure.get("snapshot_labels") == ["A", "B", "C"])
    check("contract_barrier_15", closure.get("snapshot_barrier_seconds") == 15)
    check("contract_status_advisory", closure.get("docker_desktop_cli_status_is_advisory_only") is True)
    durable = contract.get("durable_failure_packet", {})
    check("contract_failure_before_first_command", durable.get("exact_four_files_created_before_first_command") is True)
    check("contract_failure_after_every_receipt", durable.get("exact_four_files_refreshed_after_every_command_receipt") is True)
    check("contract_failure_handoff_incomplete", durable.get("in_progress_or_exception_verdict") == "HANDOFF_INCOMPLETE")
    output = contract.get("output_contract", {})
    check("contract_exact_output_root", output.get("output_root") == OUTPUT_ROOT.as_posix())
    check("contract_output_immutable", output.get("immutable_and_must_not_preexist") is True)
    check("contract_exact_four_outputs", output.get("exact_files") == OUTPUT_FILES)
    check("contract_no_extra_outputs", output.get("extra_files_allowed") is False)
    check("contract_model_policy", contract.get("model_policy") == EXPECTED_MODEL_POLICY)
    check("contract_exact_verdict_lanes", contract.get("verdict_lanes") == EXPECTED_VERDICTS)
    truth = contract.get("truth_state", {})
    check("contract_result_not_run", truth.get("RESULT_STATUS") == "NOT_RUN")
    check("contract_test_closed", truth.get("TEST_SET_OPENED") == "NO")
    check("contract_zero_rows", truth.get("ACCEPTED_RESULT_ROWS") == 0)
    check("contract_no_admission", truth.get("benchmark_admission_opened") is False)

    check(
        "authorization_schema",
        authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt006-user-authorization-1.0",
    )
    check("authorization_stage", authorization.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT006")
    check(
        "authorization_material_passport_schema9",
        passport_ok(
            authorization.get("material_passport"),
            "plan",
            "stage1e_e4_r6_pc2w_p1_attempt006_user_authorization_v1",
        ),
    )
    check("authorization_parent", authorization.get("packet_parent_checkpoint") == PACKET_PARENT)
    basis = authorization.get("authorization_basis", {})
    check("authorization_source_thread", basis.get("source_thread_id") == "019ff4f0-802a-7892-a989-24f32ac26ac8")
    check("authorization_current_text", basis.get("current_user_text") == "Xác nhận")
    current = authorization.get("current_authorization", {})
    expected_true = (
        "packet_preparation_authorized",
        "baseline_remediation_direction_authorized",
        "exact_process_command_confirmation_required_after_static_audit",
    )
    for field in expected_true:
        check(f"authorization_true:{field}", current.get(field) is True)
    expected_false = (
        "execution_authorized", "exact_process_command_confirmed", "runner_invocation_authorized",
        "docker_desktop_stop_authorized_now", "wsl_shutdown_authorized_now",
        "runtime_probe_authorized_now", "benchmark_admission_authorized",
        "materialization_authorized", "training_authorized", "evaluation_authorized",
        "test_access_authorized",
    )
    for field in expected_false:
        check(f"authorization_false:{field}", current.get(field) is False)
    prospective = authorization.get("prospective_limits_after_separate_exact_command_confirmation", {})
    check("authorization_future_one_attempt", prospective.get("execution_attempts_maximum") == 1)
    check("authorization_future_prepass_zero", prospective.get("if_pre_baseline_passes_mutation_commands") == 0)
    check("authorization_future_fail_one_stop", prospective.get("if_pre_baseline_fails_docker_desktop_stop_attempts_exactly") == 1)
    check("authorization_future_fail_one_shutdown", prospective.get("if_pre_baseline_fails_wsl_shutdown_attempts_exactly") == 1)
    for field in (
        "docker_desktop_start_attempts", "docker_daemon_queries", "automatic_retry_count",
        "fallback_count", "force_kill_count", "service_restart_count", "settings_change_count",
        "install_or_download_count", "network_operation_count", "image_pull_build_create_run_count",
    ):
        check(f"authorization_future_zero:{field}", prospective.get(field) == 0)
    expected_command_template = [
        r"C:\Program Files\Python311\python.exe",
        RUNNER.as_posix(),
        "--repo-root",
        r"E:\UIT\cv\backend",
        "--expected-head",
        "<EXACT_FULL_PACKET_HEAD_AFTER_STATIC_AUDIT>",
        "--execution-confirmation",
        "USER_CONFIRMED_EXACT_PROCESS_COMMAND_AFTER_STATIC_AUDIT",
    ]
    check("authorization_exact_future_command_template", authorization.get("future_exact_process_command_template") == expected_command_template)
    check("authorization_exact_output_root", authorization.get("authorized_output_root_after_future_confirmation") == OUTPUT_ROOT.as_posix())
    check("authorization_model_policy", authorization.get("model_policy") == EXPECTED_MODEL_POLICY)
    auth_truth = authorization.get("truth_state", {})
    check("authorization_result_not_run", auth_truth.get("RESULT_STATUS") == "NOT_RUN")
    check("authorization_test_closed", auth_truth.get("TEST_SET_OPENED") == "NO")
    check("authorization_zero_rows", auth_truth.get("ACCEPTED_RESULT_ROWS") == 0)

    state_r6 = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {})
    pc2w = state_r6.get("pc2w", {})
    attempt005 = pc2w.get("p1_attempt005_instrumented", {})
    execution_result = attempt005.get("execution_result", {})
    check(
        "state_attempt005_fail_closed",
        execution_result.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT005_CURRENT_HOST_NOT_ADMISSIBLE",
    )
    check("state_attempt005_no_retry", execution_result.get("automatic_retry_count") == 0)
    check("state_attempt005_packet_audited", execution_result.get("failure_packet_audited") is True)
    check("state_result_not_run", state.get("result_status") == "NOT_RUN")
    check("state_test_closed", state.get("test_set_opened") == "NO")
    check("state_no_attempt006_mutation", "p1_attempt006_baseline_remediation" not in pc2w)

    runner_source = blobs.get(RUNNER, b"").decode("utf-8", errors="strict") if blobs.get(RUNNER) else ""
    validator_source = blobs.get(VALIDATOR, b"").decode("utf-8", errors="strict") if blobs.get(VALIDATOR) else ""
    try:
        runner_tree = ast.parse(runner_source, filename=RUNNER.as_posix())
        check("runner_ast_parse", True)
    except SyntaxError:
        runner_tree = ast.Module(body=[], type_ignores=[])
        check("runner_ast_parse", False)
    try:
        validator_tree = ast.parse(validator_source, filename=VALIDATOR.as_posix())
        check("validator_ast_parse", True)
    except SyntaxError:
        validator_tree = ast.Module(body=[], type_ignores=[])
        check("validator_ast_parse", False)

    try:
        check("runner_exact_command_templates", assigned_literal(runner_tree, "COMMAND_ARGV_TEMPLATES") == EXPECTED_COMMAND_TEMPLATES)
        check("runner_exact_with_remediation_ids", assigned_literal(runner_tree, "EXPECTED_COMMAND_IDS_WITH_REMEDIATION") == EXPECTED_WITH_REMEDIATION)
        check("runner_exact_already_closed_ids", assigned_literal(runner_tree, "EXPECTED_COMMAND_IDS_ALREADY_CLOSED") == EXPECTED_ALREADY_CLOSED)
        check("runner_snapshot_labels", assigned_literal(runner_tree, "SNAPSHOT_LABELS") == ["A", "B", "C"])
        check("runner_settle_20", assigned_literal(runner_tree, "SETTLING_SECONDS") == 20)
        check("runner_barrier_15", assigned_literal(runner_tree, "SNAPSHOT_BARRIER_SECONDS") == 15)
        check("runner_closed_error_codes", assigned_literal(runner_tree, "ERROR_CODES") == ERROR_CODES)
    except (KeyError, ValueError, TypeError):
        for name in (
            "runner_exact_command_templates", "runner_exact_with_remediation_ids",
            "runner_exact_already_closed_ids", "runner_snapshot_labels", "runner_settle_20",
            "runner_barrier_15", "runner_closed_error_codes",
        ):
            if not any(existing == name for existing, _ in checks):
                check(name, False)

    direct_invokes = literal_calls(runner_tree, "invoke", 2)
    snapshot_calls = literal_calls(runner_tree, "collect_snapshot", 5)
    check("runner_exact_direct_invoke_pairs", direct_invokes == EXPECTED_DIRECT_INVOKES)
    check("runner_exact_snapshot_specs", snapshot_calls == EXPECTED_SNAPSHOT_CALLS)
    all_invoke_calls = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call) and call_name(node) == "invoke"
    ]
    check("runner_exact_invoke_callsite_count", len(all_invoke_calls) == 12)
    collect_function = find_function(runner_tree, "collect_snapshot")
    dynamic_kinds: list[str] = []
    if collect_function is not None:
        for node in sorted(
            (node for node in ast.walk(collect_function) if isinstance(node, ast.Call) and call_name(node) == "invoke"),
            key=lambda value: value.lineno,
        ):
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                dynamic_kinds.append(node.args[1].value)
    check(
        "runner_snapshot_command_kinds_exact_order",
        dynamic_kinds == ["WSL_VERBOSE", "WSL_RUNNING", "PROCESS_POPULATION", "TCP_POPULATION"],
    )

    remediation_if: ast.If | None = None
    for node in ast.walk(runner_tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "remediation_required":
            remediation_if = node
            break
    transition_try = (
        next((node for node in remediation_if.body if isinstance(node, ast.Try)), None)
        if remediation_if is not None else None
    )
    body_pairs = literal_calls(ast.Module(body=transition_try.body, type_ignores=[]), "invoke", 2) if transition_try else []
    final_pairs = literal_calls(ast.Module(body=transition_try.finalbody, type_ignores=[]), "invoke", 2) if transition_try else []
    check("runner_remediation_if_found", remediation_if is not None)
    check("runner_stop_in_try_exactly_once", body_pairs == [("B05", "DOCKER_DESKTOP_STOP")])
    check("runner_shutdown_in_finally_exactly_once", final_pairs == [("B06", "WSL_SHUTDOWN")])
    transition_loop_calls: list[tuple[str, ...]] = []
    for node in ast.walk(runner_tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            transition_loop_calls.extend(literal_calls(node, "invoke", 2))
    check(
        "runner_transitions_not_in_loops",
        not any(pair[0] in {"B05", "B06"} for pair in transition_loop_calls),
    )
    check("runner_no_while_retry_loop", not any(isinstance(node, ast.While) for node in ast.walk(runner_tree)))

    sleep_rows: list[tuple[int, str]] = []
    for node in ast.walk(runner_tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "time"
            and node.func.attr == "sleep"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
        ):
            sleep_rows.append((node.lineno, node.args[0].id))
    sleep_arguments = [name for _, name in sorted(sleep_rows)]
    check(
        "runner_exact_sleep_order",
        sleep_arguments == ["SETTLING_SECONDS", "SNAPSHOT_BARRIER_SECONDS", "SNAPSHOT_BARRIER_SECONDS"],
    )
    run_command_calls = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "base"
        and node.func.attr == "run_command"
    ]
    check("runner_single_runtime_command_gateway", len(run_command_calls) == 1)
    shell_true = any(
        isinstance(node, ast.Call)
        and any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        for node in ast.walk(runner_tree)
    )
    check("runner_no_shell_true", not shell_true)
    runner_call_names = {
        name for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call) and (name := call_name(node)) is not None
    }
    check("runner_no_popen", "Popen" not in runner_call_names)
    check("runner_no_os_system", "system" not in runner_call_names)
    check("runner_no_delete", not {"remove", "unlink", "rmtree"}.intersection(runner_call_names))
    try:
        check("runner_exact_output_root", assigned_path_string(runner_tree, "OUTPUT_RELATIVE") == OUTPUT_ROOT.as_posix())
    except (KeyError, ValueError, TypeError):
        check("runner_exact_output_root", False)
    check("runner_confirmation_token", "USER_CONFIRMED_EXACT_PROCESS_COMMAND_AFTER_STATIC_AUDIT" in runner_source)
    check("runner_no_raw_argv_field", '"argv":' not in runner_source)
    initialization_lines = [
        node.lineno for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and call_name(node) == "persist_failure_packet"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "IN_PROGRESS"
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "Attempt-006 initialized before first command"
    ]
    b00_lines = [
        node.lineno for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and literal_call_tuple(node, "invoke", 2) == ("B00", "DOCKER_DESKTOP_STATUS")
    ]
    check(
        "runner_failure_initialized_before_b00",
        len(initialization_lines) == 1
        and len(b00_lines) == 1
        and initialization_lines[0] < b00_lines[0],
    )
    invoke_function = find_function(runner_tree, "invoke")
    check(
        "runner_failure_refreshed_after_every_receipt",
        invoke_function is not None
        and any(
            isinstance(node, ast.Call) and call_name(node) == "persist_failure_packet"
            for node in ast.walk(invoke_function)
        ),
    )
    check("runner_exception_rewrites_failure_packet", "failure_packet_persisted = persist_failure_packet" in runner_source)
    check("runner_exact_verdicts_present", all(value in runner_source for value in EXPECTED_VERDICTS))
    check("runner_truth_not_run", '"result_status": "NOT_RUN"' in runner_source)
    check("runner_test_closed", '"test_set_opened": "NO"' in runner_source)
    check("runner_no_benchmark_admission", '"benchmark_admission_opened": False' in runner_source)
    check("runner_zero_retry", '"automatic_retry_count": 0' in runner_source)

    try:
        process_query = assigned_stripped_string(runner_tree, "PROCESS_POPULATION_QUERY")
        tcp_query = assigned_stripped_string(runner_tree, "TCP_POPULATION_QUERY")
        check("runner_process_query_extracted", True)
        check("runner_tcp_query_extracted", True)
    except (KeyError, ValueError, TypeError):
        process_query = ""
        tcp_query = ""
        check("runner_process_query_extracted", False)
        check("runner_tcp_query_extracted", False)
    rich_identity_tokens = (
        "ExecutablePath", "CommandLine", "Get-AuthenticodeSignature", "Get-FileHash",
        "SignerCertificate", "CreationDate", "FileVersion",
    )
    check("runner_process_query_lightweight", all(token not in process_query for token in rich_identity_tokens))
    check("runner_tcp_query_lightweight", all(token not in tcp_query for token in rich_identity_tokens))
    check("runner_process_query_exact_cim_properties", "-Property Name,ProcessId" in process_query)
    check("runner_tcp_query_exact_cim_properties", "-Property Name,ProcessId" in tcp_query)
    check("runner_tcp_query_uses_tcp_population", "Get-NetTCPConnection -ErrorAction Stop" in tcp_query)
    check("runner_tcp_query_does_not_emit_addresses", all(token not in tcp_query for token in ("LocalAddress", "RemoteAddress", "LocalPort", "RemotePort")))
    for query_name, query in (("process", process_query), ("tcp", tcp_query)):
        for token in (
            "Start-Process", "Stop-Process", "Stop-Service", "Restart-Service", "Set-Service",
            "Invoke-WebRequest", "Invoke-RestMethod", "curl.exe", "Remove-Item", "Set-ItemProperty",
        ):
            check(f"runner_{query_name}_query_forbids:{token}", token not in query)
        check(f"runner_{query_name}_query_closed_error", "ErrorCode='PROBE_EXCEPTION'" in query and "ErrorCode='NONE'" in query)
        check(f"runner_{query_name}_query_exact_envelope", all(field in query for field in ("Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash")))

    for path, expected_sha256 in FROZEN_ATTEMPT005_SHA256.items():
        check(f"runner_embeds_prior_name:{path.name}", path.name in runner_source)
        check(f"runner_embeds_prior_hash:{path.name}", expected_sha256 in runner_source)
    check("runner_material_passport_origin", '"origin_skill": "experiment-agent"' in runner_source)
    check("runner_material_passport_mode", '"origin_mode": "run"' in runner_source)
    check("runner_material_passport_unverified", '"verification_status": "UNVERIFIED"' in runner_source)

    valid_hash = "a" * 64
    process_empty = {"Available": True, "Count": 0, "Rows": [], "ErrorCode": "NONE", "ErrorTypeHash": None}
    process_singleton = {
        "Available": True,
        "Count": 1,
        "Rows": [{"Name": "wslrelay", "ProcessId": 7}],
        "ErrorCode": "NONE",
        "ErrorTypeHash": None,
    }
    tcp_empty = {"Available": True, "Count": 0, "Rows": [], "ErrorCode": "NONE", "ErrorTypeHash": None}
    tcp_singleton = {
        "Available": True,
        "Count": 1,
        "Rows": [{"Name": "wslrelay", "ProcessId": 7, "ConnectionCount": 1}],
        "ErrorCode": "NONE",
        "ErrorTypeHash": None,
    }
    unavailable = {
        "Available": False,
        "Count": 0,
        "Rows": [],
        "ErrorCode": "PROBE_EXCEPTION",
        "ErrorTypeHash": valid_hash,
    }
    for kind, fixture, expected_eligible in (
        ("process", process_empty, True),
        ("process", process_singleton, False),
        ("process", unavailable, False),
        ("tcp", tcp_empty, True),
        ("tcp", tcp_singleton, False),
        ("tcp", unavailable, False),
    ):
        valid, eligible = validate_population_envelope(fixture, kind)
        label = f"{kind}:{'empty' if fixture['Available'] and fixture['Count'] == 0 else 'singleton' if fixture['Available'] else 'unavailable'}"
        check(f"fixture_valid:{label}", valid)
        check(f"fixture_gate_eligibility:{label}", eligible is expected_eligible)

    for kind, singleton in (("process", process_singleton), ("tcp", tcp_singleton)):
        negatives: dict[str, dict[str, Any]] = {}
        negatives["rows_null"] = {**process_empty, "Rows": None}
        negatives["rows_singleton_object"] = {**singleton, "Rows": singleton["Rows"][0]}
        negatives["available_nonboolean"] = {**process_empty, "Available": 1}
        negatives["count_boolean"] = {**process_empty, "Count": True}
        negatives["count_negative"] = {**process_empty, "Count": -1}
        negatives["count_mismatch"] = {**singleton, "Count": 0}
        negatives["unknown_error_code"] = {**unavailable, "ErrorCode": "UNKNOWN"}
        negatives["malformed_hash_short"] = {**unavailable, "ErrorTypeHash": "a" * 63}
        negatives["malformed_hash_upper"] = {**unavailable, "ErrorTypeHash": "A" * 64}
        negatives["available_with_hash"] = {**process_empty, "ErrorTypeHash": valid_hash}
        negatives["unavailable_without_hash"] = {**unavailable, "ErrorTypeHash": None}
        negatives["unavailable_nonempty"] = {
            **singleton,
            "Available": False,
            "ErrorCode": "PROBE_EXCEPTION",
            "ErrorTypeHash": valid_hash,
        }
        duplicate_row = dict(singleton["Rows"][0])
        duplicate_row["ProcessId"] = int(duplicate_row["ProcessId"]) + 1
        negatives["duplicate_name"] = {**singleton, "Count": 2, "Rows": [singleton["Rows"][0], duplicate_row]}
        unexpected_row = dict(singleton["Rows"][0])
        unexpected_row["Name"] = "unexpected"
        negatives["unexpected_name"] = {**singleton, "Rows": [unexpected_row]}
        negatives["missing_available"] = {key: value for key, value in process_empty.items() if key != "Available"}
        negatives["missing_count"] = {key: value for key, value in process_empty.items() if key != "Count"}
        negatives["missing_rows"] = {key: value for key, value in process_empty.items() if key != "Rows"}
        negatives["missing_error_code"] = {key: value for key, value in process_empty.items() if key != "ErrorCode"}
        negatives["missing_error_hash"] = {key: value for key, value in process_empty.items() if key != "ErrorTypeHash"}
        negatives["unexpected_envelope_field"] = {**process_empty, "Extra": False}
        row_missing = dict(singleton["Rows"][0])
        row_missing.pop("ProcessId")
        negatives["missing_row_field"] = {**singleton, "Rows": [row_missing]}
        negatives["boolean_process_id"] = {**singleton, "Rows": [{**singleton["Rows"][0], "ProcessId": True}]}
        negatives["zero_process_id"] = {**singleton, "Rows": [{**singleton["Rows"][0], "ProcessId": 0}]}
        if kind == "tcp":
            negatives["boolean_connection_count"] = {**singleton, "Rows": [{**singleton["Rows"][0], "ConnectionCount": True}]}
            negatives["zero_connection_count"] = {**singleton, "Rows": [{**singleton["Rows"][0], "ConnectionCount": 0}]}
        for name, fixture in negatives.items():
            valid, eligible = validate_population_envelope(fixture, kind)
            check(f"fixture_rejected:{kind}:{name}", not valid and not eligible)

    validator_imports = {
        alias.name.split(".")[0]
        for node in ast.walk(validator_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    check("validator_no_network_imports", not {"socket", "requests", "urllib", "http", "ftplib"}.intersection(validator_imports))
    check("validator_does_not_import_runner", "execute_e4_r6_pc2w_p1_attempt006_baseline_remediation" not in validator_imports)
    validator_subprocess_calls = [
        node for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    check("validator_single_subprocess_gateway", len(validator_subprocess_calls) == 1)
    run_git_function = find_function(validator_tree, "run_git")
    check(
        "validator_subprocess_is_git_only",
        run_git_function is not None
        and '["git", *args]' in ast.get_source_segment(validator_source, run_git_function),
    )
    validator_call_names = {
        name for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call) and (name := call_name(node)) is not None
    }
    check("validator_no_write_calls", not {"write", "write_text", "write_bytes", "mkdir", "touch", "unlink", "remove", "rmtree"}.intersection(validator_call_names))
    check("validator_no_runtime_sleep", "sleep" not in validator_call_names)
    check("validator_no_shell_true", not any(
        isinstance(node, ast.Call)
        and any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        for node in ast.walk(validator_tree)
    ))
    check("validator_dont_write_bytecode", "sys.dont_write_bytecode = True" in validator_source)

    failures = [name for name, passed in checks if not passed]
    result = {
        "verdict": (
            "PASS_PC2W_P1_ATTEMPT006_STATIC_PACKET_READY_FOR_EXACT_COMMAND_CONFIRMATION"
            if not failures else "FAIL_CLOSED_PC2W_P1_ATTEMPT006_STATIC_PACKET"
        ),
        "head": head,
        "parent": parent_row[1].casefold() if len(parent_row) == 2 else None,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
        "runtime_commands_executed": False,
        "write_set": [],
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "verdict": "FAIL_CLOSED_PC2W_P1_ATTEMPT006_STATIC_PACKET",
            "error_type": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8")),
            "runtime_commands_executed": False,
            "write_set": [],
        }, indent=2, allow_nan=False))
        raise SystemExit(2)
