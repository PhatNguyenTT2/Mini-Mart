#!/usr/bin/env python3
"""Static fail-closed validation for the Attempt-005 runner freeze."""

from __future__ import annotations

import argparse
import ast
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assigned_literal(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise KeyError(name)


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
        check(f"upstream_exists:{path.name}", (root / path).is_file())
        check(f"upstream_hash:{path.name}", (root / path).is_file() and sha256(root / path) == expected)

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
    check("contract_fast_forbidden", model.get("fast_or_priority_allowed") is False)
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
    for field in contract.get("instrumented_process_fields", []):
        check(f"runner_process_field:{field}", field in source)
    for field in contract.get("instrumented_tcp_fields", []):
        check(f"runner_tcp_field:{field}", field in source)

    check("state_root_attempt005_packet", state.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt005_packet_preparation_authorized_runner_freeze_in_progress_no_execution")
    r6 = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {})
    pc2w = r6.get("pc2w", {})
    attempt005 = pc2w.get("p1_attempt005_instrumented", {})
    check("state_attempt005_authorized", attempt005.get("attempt005_authorized") is True)
    check("state_execution_not_opened", attempt005.get("execution_previously_opened") is False)
    check("state_static_audit_required", attempt005.get("fresh_static_audit_required") is True)
    check("state_no_auto_retry", attempt005.get("automatic_retry_count") == 0)
    check("state_no_runtime", attempt005.get("runtime_commands_executed") is False)
    check("state_exact_command_confirmation", attempt005.get("exact_command_confirmation_required") is True)
    check("state_next_gate", pc2w.get("next_gate") == "FREEZE_AND_FRESH_STANDARD_STATIC_AUDIT_BEFORE_EXACT_COMMAND_CONFIRMATION")
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
