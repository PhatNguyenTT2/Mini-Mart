#!/usr/bin/env python3
"""Statically validate the attempt-003 offline-equivalent observation dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import types
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_contract.json"
AUTH = CONTROL / "e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization.json"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json"
BASELINE_VALIDATION = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_validation_receipt.json"
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-offline-equivalent-observation"
)
EXPECTED_CHANGED = {AUTH.as_posix(), DISPATCH.as_posix()}
EXPECTED_OUTPUTS = [
    "observation_command_receipts.json",
    "observation_handoff.json",
    "offline_equivalent_observation_receipt.json",
]
CENTRAL_REPO_ROOT = Path(r"E:\UIT\cv\backend")
PYTHON = Path(r"C:\Program Files\Python311\python.exe")
PYTHON_FACT = (103192, "5f7b89a612c9b8af1d6456cdfcd1dbe5ca630849e79aebced9bee9a6694952ec")


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        if key in result or key.casefold() in folded:
            raise DuplicateKeyError(key)
        result[key] = value
        folded.add(key.casefold())
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_fact(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), sha256(value)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_fact(repo: Path, revision: str, relative: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative.as_posix()}"], cwd=repo,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, check=True,
    )
    return len(completed.stdout), sha256(completed.stdout)


def import_runner(path: Path) -> Any:
    module = types.ModuleType("offline_equivalent_runner")
    module.__file__ = str(path)
    module.__dict__["__name__"] = "offline_equivalent_runner"
    source = path.read_bytes()
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    checks: list[str] = []

    def check(condition: bool, label: str) -> None:
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    check(Path(sys.executable).resolve() == PYTHON.resolve(), "actual_validator_python_path")
    check(sys.version_info[:3] == (3, 11, 9), "actual_validator_python_version")
    check(file_fact(Path(sys.executable)) == PYTHON_FACT, "actual_validator_python_fact")

    check(Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo, "exact_repo_root")
    head = git(repo, "rev-parse", "HEAD").casefold()
    check(re.fullmatch(r"[0-9a-f]{40}", args.expected_head.casefold()) is not None, "expected_head_shape")
    check(head == args.expected_head.casefold(), "expected_head_match")
    parents = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    check(len(parents) == 2, "single_parent")
    parent = parents[1].casefold()
    check(not git(repo, "status", "--porcelain=v1", "--untracked-files=all"), "clean_worktree")
    changed = set(filter(None, git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
    check(changed == EXPECTED_CHANGED, "exact_execution_commit_write_set")
    expected_execution_output = (CENTRAL_REPO_ROOT / OUTPUT).resolve()
    check(not expected_execution_output.exists(), "central_execution_output_root_absent")

    runner = import_runner(repo / RUNNER)
    auth = load_json(repo / AUTH)
    dispatch = load_json(repo / DISPATCH)
    contract = load_json(repo / CONTRACT)
    prior = load_json(repo / BASELINE_VALIDATION)
    check(auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-authorization-3.0", "auth_schema")
    check(dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-dispatch-3.0", "dispatch_schema")
    check(contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-observation-contract-3.0", "contract_schema")
    check(prior.get("attempt_result", {}).get("attempt003_execution_opened") is False, "attempt003_still_unopened")
    check(prior.get("attempt_result", {}).get("automatic_retry_count") == 0, "prior_retry_zero")
    check(prior.get("truth_state", {}).get("RESULT_STATUS") == "NOT_RUN", "prior_truth_not_run")

    decision = auth.get("user_decision", {})
    check(auth.get("entry_checkpoint", "").casefold() == parent, "auth_parent_binding")
    check(Path(auth.get("authorized_output_root", "")).resolve() == expected_execution_output, "auth_central_output_root")
    check(decision.get("decision") == "AUTHORIZE_ATTEMPT003_OFFLINE_EQUIVALENT_OBSERVATION_AND_CONDITIONAL_EXECUTION", "decision_exact")
    check(decision.get("offline_equivalent_observation_authorized") is True, "observation_authorized")
    check(decision.get("attempt003_execution_authorized_on_pass") is True, "conditional_execution_authorized")
    for field in (
        "automatic_retry_authorized", "docker_desktop_start_or_stop_authorized_in_observation",
        "wsl_shutdown_or_terminate_authorized_in_observation", "image_or_container_mutation_authorized",
        "settings_change_authorized", "install_or_download_authorized", "materialization_authorized",
        "training_authorized", "evaluation_authorized", "test_access_authorized",
    ):
        check(decision.get(field) is False, f"forbidden_flag_false:{field}")
    model = auth.get("model_policy", {}).get("worktree_audit", {})
    check(model.get("model") == "gpt-5.6-sol", "audit_model_sol")
    check(model.get("reasoning_effort") == "xhigh", "audit_reasoning_xhigh")
    check(model.get("requested_service_tier") == "priority", "audit_tier_fast_requested")

    binding = dispatch.get("execution_binding", {})
    check(dispatch.get("runner_checkpoint", "").casefold() == parent, "dispatch_parent_binding")
    check(Path(binding.get("working_directory", "")).resolve() == CENTRAL_REPO_ROOT.resolve(), "dispatch_central_working_directory")
    check(Path(binding.get("output_root", "")).resolve() == expected_execution_output, "dispatch_central_output_root")
    check(binding.get("expected_output_files") == EXPECTED_OUTPUTS, "dispatch_exact_outputs")
    check(binding.get("output_root_must_be_absent") is True, "dispatch_output_absence_gate")
    expected_dispatch_argv = [
        r"C:\Program Files\Python311\python.exe", RUNNER.as_posix(), "--repo-root",
        str(CENTRAL_REPO_ROOT), "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    check(binding.get("argv") == expected_dispatch_argv, "dispatch_full_argv_binding")
    interpreter = dispatch.get("interpreter", {})
    check(Path(interpreter.get("path", "")).resolve() == PYTHON.resolve(), "interpreter_path")
    check(interpreter.get("version") == "3.11.9", "interpreter_version")
    check((interpreter.get("raw_bytes"), interpreter.get("sha256")) == PYTHON_FACT, "interpreter_fact")
    controls = dispatch.get("execution_controls", {})
    check(controls.get("read_only_observation") is True, "read_only_control")
    check(controls.get("commands_exactly_once") == 9, "nine_command_control")
    check(controls.get("automatic_retry_count") == 0, "retry_zero_control")
    check(controls.get("two_snapshot_stability_barrier_required") is True, "stability_barrier_control")
    check(controls.get("win32_named_pipe_absence_required_twice") is True, "named_pipe_control")
    check(controls.get("win32_named_pipe_wait_bound_milliseconds") == 1, "named_pipe_one_millisecond_control")
    check(controls.get("strict_status_and_daemon_decoding_required") is True, "strict_status_daemon_control")
    check(controls.get("contradictory_daemon_stdout_rejected") is True, "daemon_contradiction_control")
    check(controls.get("exact_wsl_header_required") is True, "exact_wsl_header_control")
    check(controls.get("attempt003_immediate_pre_gate_replay_required") is True, "attempt003_replay_control")
    for field in (
        "docker_desktop_start_or_stop_allowed", "wsl_shutdown_or_terminate_allowed",
        "image_or_container_mutation_allowed", "settings_change_allowed", "install_or_download_allowed",
        "materialization_allowed", "training_evaluation_or_test_allowed",
    ):
        check(controls.get(field) is False, f"dispatch_forbidden_false:{field}")
    audit = dispatch.get("fresh_independent_audit", {})
    check(audit.get("required_before_execution") is True, "fresh_audit_required")
    check(audit.get("must_use_new_worktree_context") is True, "fresh_worktree_required")
    check(audit.get("model") == "gpt-5.6-sol", "dispatch_audit_model")
    check(audit.get("reasoning_effort") == "xhigh", "dispatch_audit_reasoning")
    check(audit.get("requested_service_tier") == "priority", "dispatch_audit_tier")

    frozen = dispatch.get("frozen_artifacts")
    expected_frozen = {RUNNER, CONTRACT, AUTH, BASELINE_VALIDATION}
    check(isinstance(frozen, list), "frozen_list")
    check({Path(str(row.get("path"))) for row in frozen} == expected_frozen, "frozen_exact_set")
    for row in frozen:
        relative = Path(str(row["path"]))
        expected = (row.get("git_blob_bytes"), row.get("git_blob_sha256"))
        check(git_fact(repo, head, relative) == expected, f"frozen_head_fact:{relative.name}")
    check(git_fact(repo, parent, RUNNER) == git_fact(repo, head, RUNNER), "runner_frozen_in_parent")
    check(git_fact(repo, parent, CONTRACT) == git_fact(repo, head, CONTRACT), "contract_frozen_in_parent")

    valid_wsl = b"  NAME              STATE           VERSION\r\n* Ubuntu            Stopped         2\r\n  docker-desktop    Stopped         2\r\n"
    rows, complete = runner.parse_wsl_verbose(valid_wsl)
    check(complete and len(rows) == 2, "wsl_valid_fixture")
    rows, complete = runner.parse_wsl_verbose(b"NAME STATE VERSION\nUbuntu Stopped 2\nUNPARSED")
    check(not complete and rows == [], "wsl_partial_rejected")
    rows, complete = runner.parse_wsl_verbose(b"NAME STATE VERSION\nUbuntu Stopped 2\nubuntu Stopped 2")
    check(not complete and rows == [], "wsl_duplicate_rejected")
    rows, complete = runner.parse_wsl_verbose(b"Ubuntu Stopped 2")
    check(not complete and rows == [], "wsl_missing_header_rejected")
    rows, complete = runner.parse_wsl_verbose(b"username interstate versioned\nUbuntu Stopped 2")
    check(not complete and rows == [], "wsl_false_header_rejected")
    rows, complete = runner.parse_wsl_verbose(b"NAME STATE VERSION\nUbuntu\x01 Stopped 2")
    check(not complete and rows == [], "wsl_control_character_rejected")
    rows, complete = runner.parse_wsl_verbose(b"NAME STATE VERSION\nUbuntu Stopped 2\xff")
    check(not complete and rows == [], "wsl_invalid_utf8_rejected")
    names, complete = runner.parse_wsl_running_quiet(b"")
    check(complete and names == [], "running_quiet_empty_valid")
    names, complete = runner.parse_wsl_running_quiet(b"Ubuntu\r\n")
    check(complete and names == ["Ubuntu"], "running_quiet_one_detected")
    names, complete = runner.parse_wsl_running_quiet(b"Ubuntu\nubuntu\n")
    check(not complete and names == [], "running_quiet_duplicate_rejected")
    names, complete = runner.parse_wsl_running_quiet(b"Ubuntu\x01")
    check(not complete and names == [], "running_quiet_control_rejected")

    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":[]}')
    check(complete and processes == [], "process_empty_valid")
    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":["com.docker.backend"]}')
    check(complete and processes == ["com.docker.backend"], "process_target_detected")
    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":["unknown"]}')
    check(not complete and processes == [], "process_unknown_rejected")
    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":[],"extra":1}')
    check(not complete and processes == [], "process_extra_key_rejected")
    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":[],"runtime_processes":[]}')
    check(not complete and processes == [], "process_duplicate_key_rejected")
    processes, complete = runner.parse_process_inventory(b'{"runtime_processes":[]}\xff')
    check(not complete and processes == [], "process_invalid_encoding_rejected")

    receipt_ok = {"exit_code": 0, "timed_out": False, "spawn_exception_type": None}
    receipt_fail = {"exit_code": 1, "timed_out": False, "spawn_exception_type": None}
    check(runner.classify_status(receipt_ok, b"Docker Desktop is stopped", b"") == "STOPPED_EXACT", "status_stopped_exact")
    check(runner.classify_status(receipt_ok, b"Docker Desktop is running", b"") == "RUNNING_EXACT", "status_running_exact")
    check(runner.classify_status(receipt_fail, b"", b"opaque failure") == "UNCLASSIFIED_NONZERO_HASH_ONLY", "status_nonzero_unclassified")
    check(runner.classify_status(receipt_fail, b"", b"still running") == "RUNNING_EXACT", "status_running_blocks_even_nonzero")
    check(runner.classify_status(receipt_fail, b"", b"opaque\xff") == "UNCLASSIFIED_INVALID_ENCODING", "status_invalid_encoding_rejected")
    daemon_missing = b"open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
    check(runner.daemon_is_specifically_unavailable(receipt_fail, b"", daemon_missing), "daemon_named_pipe_missing_valid")
    check(not runner.daemon_is_specifically_unavailable(receipt_fail, b"", daemon_missing + b" Access is denied"), "daemon_permission_rejected")
    check(not runner.daemon_is_specifically_unavailable(receipt_ok, b"{}", b""), "daemon_reachable_rejected")
    check(not runner.daemon_is_specifically_unavailable(receipt_fail, b'{"Version":"reachable"}', daemon_missing), "daemon_contradictory_stdout_rejected")
    check(not runner.daemon_is_specifically_unavailable(receipt_fail, b"", daemon_missing + b"\xff"), "daemon_invalid_encoding_rejected")
    check(runner.pipe_is_specifically_absent({"available": False, "win32_error": 2, "probe_exception_type": None}), "win32_pipe_absence_valid")
    check(not runner.pipe_is_specifically_absent({"available": False, "win32_error": 5, "probe_exception_type": None}), "win32_pipe_access_denied_rejected")
    check(not runner.pipe_is_specifically_absent({"available": True, "win32_error": None, "probe_exception_type": None}), "win32_pipe_available_rejected")

    source = (repo / RUNNER).read_text(encoding="utf-8")
    check("wait_named_pipe(DESKTOP_LINUX_PIPE, 1)" in source, "wait_named_pipe_one_millisecond_bound")
    check("wait_named_pipe(DESKTOP_LINUX_PIPE, 0)" not in source, "wait_named_pipe_default_wait_absent")
    check(source.count("record(EXPECTED_COMMAND_IDS[") == 7, "seven_direct_record_calls")
    check(source.count("= record(\n        EXPECTED_COMMAND_IDS[") == 2, "two_process_record_calls")
    check(source.count("probe_desktop_linux_pipe()") == 3, "two_pipe_probe_calls_plus_definition")
    for forbidden_literal in (
        '[str(DOCKER), "desktop", "start"]', '[str(DOCKER), "desktop", "stop"]',
        '[str(WSL), "--shutdown"]', '[str(WSL), "--terminate"]',
        '[str(DOCKER), "pull"]', '[str(DOCKER), "run"]', '[str(DOCKER), "build"]',
    ):
        check(forbidden_literal not in source, f"runner_forbidden_absent:{forbidden_literal}")
    check(runner.EXPECTED_COMMAND_IDS == [
        "O00_DOCKER_DESKTOP_STATUS_ADVISORY",
        "O01A_WSL_LIST_VERBOSE", "O02A_WSL_LIST_RUNNING_QUIET",
        "O03A_DAEMON_VERSION_SERVER_ONLY", "O04A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY",
        "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER", "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER",
        "O03B_DAEMON_VERSION_SERVER_ONLY_STABILITY_BARRIER",
        "O04B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER",
    ], "exact_command_id_sequence")
    check(contract.get("pass_verdict") == "PASS_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_BASELINE", "contract_pass_verdict")
    check(contract.get("next_gate_on_pass") == "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT", "contract_next_gate")
    check(contract.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, "contract_truth_state")

    print(json.dumps({
        "verdict": "PASS_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_RUNNER_READY_FOR_FRESH_AUDIT",
        "checkpoint": head,
        "runner_checkpoint": parent,
        "checks_passed": len(checks),
        "checks_total": len(checks),
        "execution_performed": False,
        "output_root_opened": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({
            "verdict": "FAIL_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_STATIC_VALIDATION",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "execution_performed": False,
        }, indent=2))
        sys.exit(1)
