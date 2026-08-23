#!/usr/bin/env python3
"""Portable fail-closed static validator for the PC2W-P1 v2 dispatch."""

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


CONTROL = Path(__file__).resolve().parent
AUDIT_REPO = CONTROL.parents[4]
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_dispatch.json"
AUTH = CONTROL / "e4_r6_pc2w_p1_user_authorization_and_model_override.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_query_only.py"
EXPECTED_CHANGED = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc2w_p1_user_authorization_and_model_override.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc2w_p1_dispatch.json",
}
EXPECTED_OUTPUTS = [
    "command_receipts.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
    "runtime_inventory.json",
]


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key: {key}")
        case = key.casefold()
        if case in folded:
            raise DuplicateKeyError(f"case collision: {folded[case]} vs {key}")
        result[key] = value
        folded[case] = key
    return result


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object root: {path}")
    return value


def file_fact(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(repo: Path, revision: str, relative: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=repo,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, shell=False,
    )
    return len(completed.stdout), hashlib.sha256(completed.stdout).hexdigest()


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


parser = argparse.ArgumentParser()
parser.add_argument("--expected-head", required=True)
args = parser.parse_args()
expected_head = str(args.expected_head).casefold()

try:
    dispatch = load(DISPATCH)
    auth = load(AUTH)
    source = RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    binding = dispatch.get("execution_binding", {})
    execution_repo = Path(binding.get("working_directory", "")).resolve()
    output_root = Path(binding.get("output_root", "")).resolve()
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), expected_head)
check("execution_repo_exact", execution_repo == Path(r"E:\UIT\cv\backend"), str(execution_repo))
check("execution_repo_exists", execution_repo.is_dir(), str(execution_repo))

audit_head = git(AUDIT_REPO, "rev-parse", "HEAD").casefold()
execution_head = git(execution_repo, "rev-parse", "HEAD").casefold()
audit_parent_fields = git(AUDIT_REPO, "rev-list", "--parents", "-n", "1", "HEAD").split()
execution_parent_fields = git(execution_repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
audit_parent = audit_parent_fields[1].casefold() if len(audit_parent_fields) == 2 else None
execution_parent = execution_parent_fields[1].casefold() if len(execution_parent_fields) == 2 else None
audit_changed = set(filter(None, git(AUDIT_REPO, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
execution_changed = set(filter(None, git(execution_repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
audit_status = git(AUDIT_REPO, "status", "--porcelain=v1", "--untracked-files=all")
execution_status = git(execution_repo, "status", "--porcelain=v1", "--untracked-files=all")

check("dispatch_schema", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-dispatch-2.0", dispatch.get("schema_version"))
check("auth_schema", auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-user-authorization-model-override-2.0", auth.get("schema_version"))
check("stage", dispatch.get("stage_id") == "E4-R6-PC2W-P1", dispatch.get("stage_id"))
check("audit_head_exact", audit_head == expected_head, audit_head)
check("execution_head_exact", execution_head == expected_head, execution_head)
check("audit_worktree_clean", audit_status == "", audit_status)
check("execution_worktree_clean", execution_status == "", execution_status)
check("audit_single_parent", len(audit_parent_fields) == 2, audit_parent_fields)
check("execution_single_parent", len(execution_parent_fields) == 2, execution_parent_fields)
check("parents_equal", audit_parent == execution_parent, [audit_parent, execution_parent])
check("runner_checkpoint_parent", execution_parent == dispatch.get("runner_checkpoint", "").casefold(), [execution_parent, dispatch.get("runner_checkpoint")])
check("authorization_parent", execution_parent == auth.get("entry_checkpoint", "").casefold(), [execution_parent, auth.get("entry_checkpoint")])
check("audit_exact_changes", audit_changed == EXPECTED_CHANGED, sorted(audit_changed))
check("execution_exact_changes", execution_changed == EXPECTED_CHANGED, sorted(execution_changed))
check("output_absent", not output_root.exists(), str(output_root))

check("exact_output_binding", output_root == execution_repo / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-001", str(output_root))
check("auth_output_binding", Path(auth.get("authorized_output_root", "")).resolve() == output_root, auth.get("authorized_output_root"))
check("exact_output_set", binding.get("expected_output_files") == EXPECTED_OUTPUTS, binding.get("expected_output_files"))
argv = binding.get("argv", [])
check("argv_shape", len(argv) == 6 and argv[:4] == [r"C:\Program Files\Python311\python.exe", "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_query_only.py", "--repo-root", str(execution_repo)] and argv[4:] == ["--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>"], argv)

frozen = dispatch.get("frozen_artifacts", [])
frozen_map = {
    row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256"))
    for row in frozen
    if isinstance(row, dict)
}
check("frozen_artifact_count", len(frozen_map) == 5, sorted(frozen_map))
for relative, expected in frozen_map.items():
    path = execution_repo / str(relative)
    check(f"frozen_exists:{relative}", path.is_file(), str(path))
    if path.is_file():
        check(f"frozen_execution_fact:{relative}", file_fact(path) == expected, [file_fact(path), expected])
        check(f"frozen_commit_blob:{relative}", blob_fact(AUDIT_REPO, expected_head, str(relative)) == expected, [blob_fact(AUDIT_REPO, expected_head, str(relative)), expected])

runner_relative = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_query_only.py"
check("parent_freezes_runner", blob_fact(AUDIT_REPO, str(audit_parent), runner_relative) == blob_fact(AUDIT_REPO, expected_head, runner_relative), [blob_fact(AUDIT_REPO, str(audit_parent), runner_relative), blob_fact(AUDIT_REPO, expected_head, runner_relative)])

interpreter = dispatch.get("interpreter", {})
interpreter_path = Path(interpreter.get("path", ""))
check("interpreter_exact", interpreter_path == Path(r"C:\Program Files\Python311\python.exe"), str(interpreter_path))
check("interpreter_exists", interpreter_path.is_file(), str(interpreter_path))
if interpreter_path.is_file():
    check("interpreter_fact", file_fact(interpreter_path) == (interpreter.get("raw_bytes"), interpreter.get("sha256")), file_fact(interpreter_path))

decision = auth.get("user_decision", {})
check("user_authorized", decision.get("decision") == "AUTHORIZE_PC2W_P1_EXECUTION", decision.get("decision"))
for key in (
    "automatic_retry_authorized", "image_pull_or_build_authorized",
    "container_create_or_run_authorized", "docker_or_wsl_settings_change_authorized",
    "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
    "materialization_authorized", "training_authorized", "evaluation_authorized",
    "test_access_authorized",
):
    check(f"auth_false:{key}", decision.get(key) is False, decision.get(key))

model = auth.get("model_policy_override", {}).get("all_new_phase_worktree_tasks", {})
check("worktree_model", model.get("model") == "gpt-5.6-sol", model)
check("worktree_reasoning", model.get("reasoning_effort") == "xhigh", model)
check("worktree_fast_requested", model.get("service_tier") == "priority", model)
audit = dispatch.get("fresh_independent_runner_audit", {})
check("fresh_audit_required", audit.get("required_before_execution") is True and audit.get("must_use_new_worktree_context") is True, audit)
check("fresh_audit_xhigh_fast", audit.get("model") == "gpt-5.6-sol" and audit.get("reasoning_effort") == "xhigh" and audit.get("requested_service_tier") == "priority", audit)

controls = dispatch.get("execution_controls", {})
for key in (
    "raw_stdout_or_stderr_persisted", "raw_context_persisted",
    "proxy_secret_values_persisted", "image_pull_or_build_allowed",
    "container_create_or_run_allowed", "docker_or_wsl_settings_change_allowed",
    "materialization_allowed", "training_evaluation_or_test_allowed",
):
    check(f"control_false:{key}", controls.get(key) is False, controls.get(key))
check("one_start_max", controls.get("docker_desktop_start_attempts_maximum") == 1, controls)
check("one_stop_max", controls.get("docker_desktop_stop_attempts_after_start_attempt_maximum") == 1, controls)
check("zero_retry", controls.get("automatic_retry_count") == 0, controls)
check("finally_stop_required", controls.get("stop_finally_required") is True, controls)
check("pre_gate_required", controls.get("pre_start_gate_required") is True, controls)

check("runner_ast", isinstance(tree, ast.Module), None)
check("runner_expected_head_arg", 'parser.add_argument("--expected-head", required=True)' in source and "exact execution HEAD mismatch" in source, None)
check("runner_one_start_id", source.count('"P06_DOCKER_DESKTOP_START_ONCE"') == 1, source.count('"P06_DOCKER_DESKTOP_START_ONCE"'))
check("runner_one_stop_id", source.count('"P20_DOCKER_DESKTOP_STOP_ONCE"') == 1, source.count('"P20_DOCKER_DESKTOP_STOP_ONCE"'))
check("runner_start_stop_literals", '[str(DOCKER), "desktop", "start"]' in source and '[str(DOCKER), "desktop", "stop"]' in source, None)
check("runner_finally", "finally:" in source and "if startup_attempted:" in source, None)
check("runner_no_sleep", "time.sleep(" not in source, None)
check("runner_shell_lock", "shell=True" not in source and source.count("shell=False") >= 3, source.count("shell=False"))
check("runner_exact_entries", "output_entries = list(output_root.iterdir())" in source and "not all(path.is_file() for path in output_entries)" in source, None)
check("runner_clean_parent_change_gates", all(token in source for token in ('"status", "--porcelain=v1", "--untracked-files=all"', '"rev-list", "--parents", "-n", "1", "HEAD"', "EXPECTED_HEAD_CHANGE_SET")), None)
check("runner_frozen_gates", "frozen artifact mismatch" in source and "git_blob_fact" in source and "authorized_output_root" in source, None)
check("runner_pre_identity_gate", "identity_payloads_parsed_and_complete" in source and "if all(value is True for value in pre_gate.values())" in source, None)
check("runner_daemon_specific", all(token in source for token in ("DAEMON_PIPE_MARKERS", "DAEMON_PIPE_MISSING_MARKERS", "PERMISSION_ERROR_MARKERS")) and '"error during connect"' not in source, None)
check("runner_mutation_gate", all(token in source for token in ("containers_running_zero", "container_inventory_unchanged", "image_inventory_unchanged", "container_or_image_events_absent")), None)
check("runner_wsl_restoration", all(token in source for token in ("during_docker_desktop_distro_exactly_running", "wsl_inventory_restored_exactly")), None)
check("runner_backend_identity", all(token in source for token in ("client_version_whitelist", "ContainerdCommit", "containerd_commit_id")), None)
check("runner_passport_carry_forward", 'intake = auth.get("material_passport", {}).get("experiment_intake_declaration")' in source and '"declared_at": created_at' not in source, None)
check("runner_secret_safety", all(token in source for token in ('"raw_stdout_or_stderr_persisted": False', '"raw_context_persisted": False', '"proxy_values_persisted": False', "RemoteAddressSha256")), None)
check("runner_no_raw_error", '"error_sha256"' in source and '"error": str(exc)' not in source, None)
check("runner_no_science", all(token in source for token in ('"scientific_execution_performed": False', '"result_status": "NOT_RUN"', '"test_set_opened": "NO"', '"accepted_result_rows": 0')), None)

truth = dispatch.get("truth_state")
check("dispatch_truth", truth == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, truth)
failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_DISPATCH_V2_STATIC_READY" if not failures else "FAIL",
    "expected_execution_checkpoint": expected_head,
    "audit_checkpoint": audit_head,
    "execution_checkpoint": execution_head,
    "runner_checkpoint": execution_parent,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)
