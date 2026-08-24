#!/usr/bin/env python3
"""Static fail-closed validation for the Attempt-005 runner freeze."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt005_instrumented.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt005_instrumented_contract.json"
STATE = CONTROL / "pipeline_state_stage1e.json"
UPSTREAM_HASHES = {
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_am/E4_R6PC2W_P1_residual_process_policy_review/prospective_residual_process_admission_policy.md"):
        "e5a0fecdd7dc0c83869b432583900ca1bf5981fb8380ecba8a089df26135b005",
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_am/E4_R6PC2W_P1_residual_process_policy_review/policy_review_handoff.json"):
        "293388b658075e5d307c53ed63e796d94cc021e9e6c0b2fa37562cd08002bfb9",
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt.json":
        "ef5da387f492593da25b4316a1e698dab0afe4f0313c471a5dbc9987eda08a6d",
    CONTROL / "execute_e4_r6_pc2w_p1_attempt004_query_only.py":
        "66c964e40cc23cee0bda59b8afc949c6fd3189c3c821e2eb98ffd4323c3c0e13",
    CONTROL / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py":
        "59896953c4e3aac49c6c51f3afd82d785b65928ea5eaa3b42f245181549cc8de",
    CONTROL / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json":
        "fc6d5479ad56692b6c04449ac0150b256d2dd4409471c8723f1ad2d84f193b83",
}
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
WINDOWS_POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    folded: set[str] = set()
    for key, item in pairs:
        if key in value or key.casefold() in folded:
            raise DuplicateKeyError(key)
        value[key] = item
        folded.add(key.casefold())
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object JSON: {path}")
    return value


def git_blob_bytes(root: Path, revision: str, path: Path) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{path.as_posix()}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def invoke_literal_id(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Name) or node.func.id != "invoke" or not node.args:
        return None
    first = node.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def literal_invoke_ids(node: ast.AST) -> list[str]:
    calls = [
        (child.lineno, command_id)
        for child in ast.walk(node)
        if (command_id := invoke_literal_id(child)) is not None
    ]
    return [command_id for _, command_id in sorted(calls)]


def find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        ),
        None,
    )


def assigned_literal(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise KeyError(name)


def assigned_stripped_string(tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
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


def powershell_source_parses(source: str) -> bool:
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    script = (
        "$source=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
        + encoded
        + "'));$tokens=$null;$errors=$null;"
        "[System.Management.Automation.Language.Parser]::ParseInput("
        "$source,[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -ne 0){exit 1}"
    )
    result = subprocess.run(
        [
            str(WINDOWS_POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
            "-Command", script,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and not result.stdout.strip() and not result.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    check("expected_head", head == args.expected_head)
    check("runner_exists", (root / RUNNER).is_file())
    check("contract_exists", (root / CONTRACT).is_file())
    check("state_exists", (root / STATE).is_file())

    for path, expected in UPSTREAM_HASHES.items():
        try:
            blob = git_blob_bytes(root, head, path)
            blob_exists = True
        except subprocess.CalledProcessError:
            blob = b""
            blob_exists = False
        check(f"upstream_exists_in_head:{path.name}", blob_exists)
        check(
            f"upstream_git_blob_hash:{path.name}",
            blob_exists and hashlib.sha256(blob).hexdigest() == expected,
        )

    try:
        contract = load_json(root / CONTRACT)
        check("contract_strict_json", True)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError, ValueError):
        contract = {}
        check("contract_strict_json", False)
    try:
        state = load_json(root / STATE)
        check("state_strict_json", True)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError, ValueError):
        state = {}
        check("state_strict_json", False)

    check("contract_schema", contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt005-instrumented-contract-1.0")
    check("contract_stage", contract.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT005")
    check("contract_user_option", contract.get("authorization_basis", {}).get("selected_policy_option") == "AUTHORIZE_ATTEMPT005_INSTRUMENTED_CURRENT_HOST")
    transitions = contract.get("authorized_runtime_transitions", {})
    check("contract_one_start", transitions.get("docker_desktop_start_attempts_maximum") == 1)
    check("contract_one_stop", transitions.get("docker_desktop_stop_attempts_exactly_after_any_start") == 1)
    check("contract_one_shutdown", transitions.get("wsl_shutdown_attempts_exactly_after_stop") == 1)
    check("contract_zero_retry", transitions.get("automatic_retry_count") == 0)
    check("contract_zero_force_kill", transitions.get("force_kill_count") == 0)
    closure = contract.get("post_shutdown_closure", {})
    check("contract_three_snapshots", closure.get("snapshots_required") == 3)
    check("contract_settling_20", closure.get("settling_seconds") == 20)
    check("contract_barrier_15", closure.get("snapshot_barrier_seconds") == 15)
    check("contract_allowlist_forbidden", closure.get("name_only_allowlist_forbidden") is True)
    privacy = contract.get("privacy_controls", {})
    check("contract_no_raw_stdout", privacy.get("raw_stdout_or_stderr_persisted") is False)
    check("contract_no_raw_paths", privacy.get("raw_process_paths_persisted") is False)
    check("contract_no_raw_commandline", privacy.get("raw_command_lines_persisted") is False)
    check("contract_no_raw_addresses", privacy.get("raw_network_addresses_persisted") is False)
    model = contract.get("model_policy", {})
    check("contract_standard_tier", model.get("fresh_static_audit_service_tier") == "default")
    check("contract_audit_model", model.get("fresh_static_audit_model") == "gpt-5.6-sol")
    check("contract_audit_reasoning", model.get("fresh_static_audit_reasoning_effort") == "xhigh")
    check("contract_coordinator_model", model.get("central_model") == "gpt-5.6-sol")
    check("contract_coordinator_reasoning", model.get("central_reasoning_effort") == "max")
    check("contract_dispatch_binding", model.get("dispatch_binding_required") == {
        "coordinator_model": "gpt-5.6-sol",
        "coordinator_reasoning_effort": "max",
        "static_audit_model": "gpt-5.6-sol",
        "static_audit_reasoning_effort": "xhigh",
        "service_tier": "default",
        "fast_or_priority_allowed": False,
    })
    check("contract_fast_forbidden", model.get("fast_or_priority_allowed") is False)
    completeness = contract.get("fail_closed_completeness", {})
    check("contract_process_null_fails", completeness.get("process_identity_null_or_empty_field_is_error") is True)
    check("contract_rows_array_strict", completeness.get("rows_must_be_json_array_without_singleton_or_null_coercion") is True)
    check("contract_count_integer_strict", completeness.get("count_must_be_nonnegative_integer_and_not_boolean") is True)
    check("contract_tcp_null_fails", completeness.get("tcp_identity_null_or_empty_field_is_error") is True)
    check("contract_tcp_precast_null_check", completeness.get("tcp_ports_and_owner_are_checked_before_numeric_cast") is True)
    check("contract_during_process_nonempty", completeness.get("during_process_population_must_be_nonempty") is True)
    durable = contract.get("durable_failure_receipts", {})
    check("contract_initial_failure_packet", durable.get("exact_four_file_packet_initialized_before_first_runtime_command") is True)
    check("contract_progress_failure_packet", durable.get("packet_refreshed_after_every_command_receipt") is True)
    check("contract_exception_failure_packet", durable.get("ordinary_exception_rewrites_fail_closed_packet") is True)
    check("contract_failure_message_private", durable.get("exception_message_persisted") is False)
    required_runtime = contract.get("required_sanitized_runtime_evidence", [])
    check("contract_runtime_evidence_three", isinstance(required_runtime, list) and len(required_runtime) == 3)
    checkout = contract.get("checkout_independence", {})
    check("contract_git_blob_hashes", checkout.get("upstream_hashes_use_git_blob_bytes") is True)
    check("contract_crlf_normalization", checkout.get("runner_and_contract_drift_gate_normalizes_crlf_to_lf") is True)
    check("contract_bare_cr_rejected", checkout.get("bare_carriage_return_is_rejected") is True)
    truth = contract.get("truth_state", {})
    check("contract_result_not_run", truth.get("RESULT_STATUS") == "NOT_RUN")
    check("contract_test_closed", truth.get("TEST_SET_OPENED") == "NO")
    check("contract_zero_rows", truth.get("ACCEPTED_RESULT_ROWS") == 0)

    source = (root / RUNNER).read_text(encoding="utf-8") if (root / RUNNER).is_file() else ""
    try:
        tree = ast.parse(source)
        check("runner_ast_parse", True)
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
        check("runner_ast_parse", False)
    try:
        command_ids = assigned_literal(tree, "EXPECTED_COMMAND_IDS")
        check("runner_exact_command_ids", command_ids == EXPECTED_COMMAND_IDS)
        check("runner_command_ids_unique", len(command_ids) == len(set(command_ids)) == 37)
    except (KeyError, ValueError):
        check("runner_exact_command_ids", False)
        check("runner_command_ids_unique", False)
    try:
        check("runner_three_snapshots", assigned_literal(tree, "POST_SHUTDOWN_SNAPSHOTS") == 3)
        check("runner_settling_20", assigned_literal(tree, "POST_SHUTDOWN_SETTLING_SECONDS") == 20)
        check("runner_barrier_15", assigned_literal(tree, "POST_SHUTDOWN_SNAPSHOT_BARRIER_SECONDS") == 15)
    except (KeyError, ValueError):
        check("runner_three_snapshots", False)
        check("runner_settling_20", False)
        check("runner_barrier_15", False)
    try:
        process_query = assigned_stripped_string(tree, "PROCESS_IDENTITY_QUERY")
        tcp_query = assigned_stripped_string(tree, "TCP_OWNERSHIP_QUERY")
        check("runner_process_powershell_parse_only", powershell_source_parses(process_query))
        check("runner_tcp_powershell_parse_only", powershell_source_parses(tcp_query))
    except (KeyError, ValueError, OSError):
        check("runner_process_powershell_parse_only", False)
        check("runner_tcp_powershell_parse_only", False)

    main_function = find_function(tree, "main")
    main_literal_ids = literal_invoke_ids(main_function) if main_function else []
    check("runner_start_literal_once", main_literal_ids.count("A08_DOCKER_DESKTOP_START_ONCE") == 1)
    check("runner_stop_literal_once", main_literal_ids.count("A22_DOCKER_DESKTOP_STOP_ONCE") == 1)
    check("runner_shutdown_literal_once", main_literal_ids.count("A23_WSL_SHUTDOWN_ONCE") == 1)
    transition_try = None
    if main_function is not None:
        for node in ast.walk(main_function):
            if not isinstance(node, ast.Try):
                continue
            body_ids = literal_invoke_ids(ast.Module(body=node.body, type_ignores=[]))
            final_ids = literal_invoke_ids(ast.Module(body=node.finalbody, type_ignores=[]))
            if "A08_DOCKER_DESKTOP_START_ONCE" in body_ids:
                transition_try = node
                break
    if transition_try is None:
        check("runner_transition_try_found", False)
        check("runner_stop_shutdown_in_same_finally", False)
        check("runner_stop_immediately_before_shutdown", False)
        check("runner_shutdown_survives_stop_exception", False)
    else:
        check("runner_transition_try_found", True)
        final_ids = literal_invoke_ids(ast.Module(body=transition_try.finalbody, type_ignores=[]))
        check(
            "runner_stop_shutdown_in_same_finally",
            final_ids.count("A22_DOCKER_DESKTOP_STOP_ONCE") == 1
            and final_ids.count("A23_WSL_SHUTDOWN_ONCE") == 1,
        )
        check(
            "runner_stop_immediately_before_shutdown",
            final_ids.index("A22_DOCKER_DESKTOP_STOP_ONCE") + 1
            == final_ids.index("A23_WSL_SHUTDOWN_ONCE")
            if "A22_DOCKER_DESKTOP_STOP_ONCE" in final_ids
            and "A23_WSL_SHUTDOWN_ONCE" in final_ids
            else False,
        )
        nested_stop_finally = any(
            isinstance(node, ast.Try)
            and "A22_DOCKER_DESKTOP_STOP_ONCE"
            in literal_invoke_ids(ast.Module(body=node.body, type_ignores=[]))
            and "A23_WSL_SHUTDOWN_ONCE"
            in literal_invoke_ids(ast.Module(body=node.finalbody, type_ignores=[]))
            for statement in transition_try.finalbody
            for node in ast.walk(statement)
        )
        check("runner_shutdown_survives_stop_exception", nested_stop_finally)
    loop_transition_ids: list[str] = []
    if main_function is not None:
        for node in ast.walk(main_function):
            if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                loop_transition_ids.extend(literal_invoke_ids(node))
    check(
        "runner_transitions_not_in_loop",
        not {"A08_DOCKER_DESKTOP_START_ONCE", "A22_DOCKER_DESKTOP_STOP_ONCE", "A23_WSL_SHUTDOWN_ONCE"}
        .intersection(loop_transition_ids),
    )

    call_names: list[str] = []
    shell_true = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_names.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                call_names.append(node.func.attr)
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    shell_true = True
    check("runner_no_shell_true", not shell_true)
    check("runner_no_os_system", "system" not in call_names)
    check("runner_no_popen", "Popen" not in call_names)
    check("runner_no_remove", "remove" not in call_names and "unlink" not in call_names and "rmtree" not in call_names)
    check("runner_no_environment_install", all(token not in source for token in ("pip install", "conda install", "wsl --install")))
    check("runner_exact_output_root", "E4_R6PC2W_P1_attempt005_instrumented" in source)
    check("runner_stop_marker", '"A22_DOCKER_DESKTOP_STOP_ONCE", [str(DOCKER), "desktop", "stop"]' in source)
    check("runner_shutdown_marker", '"A23_WSL_SHUTDOWN_ONCE", [str(WSL), "--shutdown"]' in source)
    check("runner_stop_before_shutdown", source.find("A22_DOCKER_DESKTOP_STOP_ONCE") < source.find("A23_WSL_SHUTDOWN_ONCE"))
    check("runner_finally_present", "finally:\n        if started:" in source)
    check("runner_no_detach", '"--detach"' not in source)
    check("runner_zero_retry_marker", '"automatic_retry_count": 0' in source)
    check("runner_test_closed_marker", '"test_set_opened": "NO"' in source)
    check("runner_result_not_run_marker", '"result_status": "NOT_RUN"' in source)
    check("runner_no_scientific_execution", '"scientific_execution_performed": False' in source)
    check("runner_no_materialization", '"materialization_performed": False' in source)
    check("runner_no_swallowed_process_field_errors", "catch{}" not in source)
    check("runner_process_hash_validation", "invalid process identity hash" in source)
    check("runner_tcp_hash_validation", "invalid TCP address hash" in source)
    check("runner_rows_no_coercion", 'if not isinstance(rows, list)' in source and 'rows = [rows]' not in source)
    check("runner_count_bool_rejected", 'isinstance(count, bool)' in source and 'count < 0' in source)
    check("runner_tcp_precast_local_port", "if($null -eq $c.LocalPort)" in source)
    check("runner_tcp_precast_remote_port", "if($null -eq $c.RemotePort)" in source)
    check("runner_tcp_precast_owner", "$null -eq $c.OwningProcess" in source)
    check("runner_canonical_lf_fact", find_function(tree, "canonical_lf_text_fact") is not None)
    check("runner_canonical_drift_gate", "canonical_lf_text_fact(repo_root / relative)" in source)
    check("runner_material_passport_contract_v2", "stage1e_e4_r6_pc2w_p1_attempt005_instrumented_contract_v2" in source)
    check("runner_during_process_nonempty", '"during_process_probe_complete_and_nonempty"' in source and 'during_processes.get("count", 0) > 0' in source)
    check("runner_failure_packet_function", find_function(tree, "persist_failure_packet") is not None)
    check("runner_failure_packet_initialized", 'persist_failure_packet("IN_PROGRESS", "Attempt-005 initialized before first command")' in source)
    invoke_function = find_function(tree, "invoke")
    check(
        "runner_failure_packet_refreshed_after_invoke",
        invoke_function is not None
        and any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "persist_failure_packet"
            for node in ast.walk(invoke_function)
        ),
    )
    check("runner_exception_persists_failure", "failure_packet_persisted = persist_failure_packet" in source)
    check("runner_client_version_persisted", '"docker_client_version_whitelist": client_whitelist' in source)
    check("runner_server_version_persisted", '"docker_server_version_whitelist": server_whitelist' in source)
    check("runner_info_whitelist_persisted", '"docker_info_whitelist": info_whitelist' in source)
    check("runner_dispatch_coordinator_model_bound", '"coordinator_model": EXPECTED_COORDINATOR_MODEL' in source)
    check("runner_dispatch_audit_reasoning_bound", '"static_audit_reasoning_effort": EXPECTED_STATIC_AUDIT_REASONING' in source)
    for field in contract.get("instrumented_process_fields", []):
        check(f"runner_process_field:{field}", field in source)
    for field in contract.get("instrumented_tcp_fields", []):
        check(f"runner_tcp_field:{field}", field in source)

    check("state_root_attempt005_packet", state.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt005_static_audit_failed_closed_packet_rework_in_progress_no_execution")
    r6 = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {})
    pc2w = r6.get("pc2w", {})
    attempt005 = pc2w.get("p1_attempt005_instrumented", {})
    check("state_attempt005_authorized", attempt005.get("attempt005_authorized") is True)
    check("state_execution_not_opened", attempt005.get("execution_previously_opened") is False)
    check("state_static_audit_required", attempt005.get("fresh_static_audit_required") is True)
    first_audit = attempt005.get("first_fresh_static_audit", {})
    check("state_first_audit_fail_closed", first_audit.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT005_STATIC_AUDIT")
    check("state_first_audit_no_runtime", first_audit.get("runtime_commands_executed") is False)
    check("state_first_audit_empty_write_set", first_audit.get("write_set") == [])
    second_audit = attempt005.get("second_fresh_static_audit", {})
    check("state_second_audit_fail_closed", second_audit.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT005_REWORK_STATIC_AUDIT")
    check("state_second_audit_135", second_audit.get("mandatory_validator_checks_passed") == 135 and second_audit.get("mandatory_validator_checks_total") == 135)
    check("state_second_audit_no_runtime", second_audit.get("runtime_commands_executed") is False)
    check("state_second_audit_empty_write_set", second_audit.get("write_set") == [])
    incident = attempt005.get("rework_validation_incident", {})
    check("state_rework_incident_disclosed", incident.get("occurred") is True)
    check("state_rework_incident_exact_two_probes", incident.get("native_process_probe_calls") == 1 and incident.get("native_tcp_probe_calls") == 1)
    check("state_rework_incident_no_docker_wsl", incident.get("docker_cli_commands_executed") is False and incident.get("wsl_commands_executed") is False)
    check("state_rework_incident_no_runner", incident.get("attempt005_runner_executed") is False)
    check("state_rework_incident_no_writes", incident.get("artifact_write_set") == [])
    check("state_rework_incident_no_science", incident.get("scientific_execution_performed") is False and incident.get("test_access_performed") is False)
    check("state_rework_incident_no_repeat", incident.get("repeat_forbidden") is True)
    check("state_no_auto_retry", attempt005.get("automatic_retry_count") == 0)
    check("state_no_runtime", attempt005.get("runtime_commands_executed") is False)
    check("state_exact_command_confirmation", attempt005.get("exact_command_confirmation_required") is True)
    check("state_next_gate", pc2w.get("next_gate") == "REWORK_FREEZE_AND_NEW_FRESH_STANDARD_STATIC_AUDIT_BEFORE_EXACT_COMMAND_CONFIRMATION")
    check("state_result_not_run", state.get("result_status") == "NOT_RUN")
    check("state_test_closed", state.get("test_set_opened") == "NO")

    failures = [name for name, passed in checks if not passed]
    result = {
        "verdict": (
            "PASS_PC2W_P1_ATTEMPT005_STATIC_PACKET_READY_FOR_FRESH_STANDARD_AUDIT"
            if not failures else "FAIL_PC2W_P1_ATTEMPT005_STATIC_PACKET"
        ),
        "head": head,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
