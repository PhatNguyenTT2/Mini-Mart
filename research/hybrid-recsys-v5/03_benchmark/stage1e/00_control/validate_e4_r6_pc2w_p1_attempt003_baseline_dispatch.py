#!/usr/bin/env python3
"""Static fail-closed validator for PC2W-P1 attempt-003 baseline restoration."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
AUDIT_REPO = CONTROL.parents[4]
AUTH = CONTROL / "e4_r6_pc2w_p1_attempt003_user_authorization_and_model_override.json"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_dispatch.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt003_baseline_restoration.py"
EXPECTED_CHANGED = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt003_user_authorization_and_model_override.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_dispatch.json",
}
EXPECTED_OUTPUTS = [
    "baseline_command_receipts.json",
    "baseline_handoff.json",
    "baseline_restoration_receipt.json",
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
    auth = load(AUTH)
    dispatch = load(DISPATCH)
    source = RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    spec = importlib.util.spec_from_file_location("attempt003_baseline_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("runner import spec unavailable")
    runner_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner_module)
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

head = git(AUDIT_REPO, "rev-parse", "HEAD").casefold()
parent_fields = git(AUDIT_REPO, "rev-list", "--parents", "-n", "1", "HEAD").split()
parent = parent_fields[1].casefold() if len(parent_fields) == 2 else None
changed = set(filter(None, git(AUDIT_REPO, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
status = git(AUDIT_REPO, "status", "--porcelain=v1", "--untracked-files=all")
binding = dispatch.get("execution_binding", {})
execution_repo = Path(binding.get("working_directory", "")).resolve()
output_root = Path(binding.get("output_root", "")).resolve()

check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), expected_head)
check("head_exact", head == expected_head, head)
check("single_parent", len(parent_fields) == 2, parent_fields)
check("worktree_clean", status == "", status)
check("exact_changed_set", changed == EXPECTED_CHANGED, sorted(changed))
check("execution_repo_exact", execution_repo == Path(r"E:\UIT\cv\backend"), str(execution_repo))
check("output_absent", not output_root.exists(), str(output_root))
check("output_exact", output_root == execution_repo / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-003-baseline-restoration", str(output_root))
check("schema_auth", auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-user-authorization-model-override-1.0", auth.get("schema_version"))
check("schema_dispatch", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-baseline-dispatch-1.0", dispatch.get("schema_version"))
check("parent_bindings", parent == auth.get("entry_checkpoint", "").casefold() == dispatch.get("runner_checkpoint", "").casefold(), [parent, auth.get("entry_checkpoint"), dispatch.get("runner_checkpoint")])
check("output_auth_binding", Path(auth.get("authorized_baseline_output_root", "")).resolve() == output_root, auth.get("authorized_baseline_output_root"))
check("exact_output_set", binding.get("expected_output_files") == EXPECTED_OUTPUTS, binding.get("expected_output_files"))
argv = binding.get("argv", [])
check("argv_exact", argv == [
    r"C:\Program Files\Python311\python.exe",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt003_baseline_restoration.py",
    "--repo-root", r"E:\UIT\cv\backend", "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
], argv)

decision = auth.get("user_decision", {})
check("user_decision", decision.get("decision") == "AUTHORIZE_PC2W_P1_ATTEMPT003_BASELINE_RESTORATION_AND_EXECUTION", decision.get("decision"))
check("restoration_authorized", decision.get("baseline_restoration_authorized") is True, decision)
check("attempt003_authorized", decision.get("attempt003_execution_authorized") is True, decision)
for key in (
    "automatic_retry_authorized", "image_pull_or_build_authorized",
    "container_create_or_run_authorized", "docker_or_wsl_settings_change_authorized",
    "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
    "materialization_authorized", "training_authorized", "evaluation_authorized",
    "test_access_authorized",
):
    check(f"auth_false:{key}", decision.get(key) is False, decision.get(key))

model = auth.get("model_policy_override", {}).get("all_new_phase_worktree_tasks", {})
check("model_xhigh_fast_requested", model.get("model") == "gpt-5.6-sol" and model.get("reasoning_effort") == "xhigh" and model.get("service_tier") == "priority", model)

frozen = dispatch.get("frozen_artifacts", [])
frozen_map = {row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256")) for row in frozen if isinstance(row, dict)}
check("frozen_count", len(frozen_map) == 5, sorted(frozen_map))
for relative, expected in frozen_map.items():
    check(f"frozen_blob:{relative}", blob_fact(AUDIT_REPO, expected_head, str(relative)) == expected, [blob_fact(AUDIT_REPO, expected_head, str(relative)), expected])
check("parent_freezes_runner", blob_fact(AUDIT_REPO, str(parent), "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt003_baseline_restoration.py") == blob_fact(AUDIT_REPO, expected_head, "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_attempt003_baseline_restoration.py"), None)

controls = dispatch.get("execution_controls", {})
check("one_stop_max", controls.get("docker_desktop_stop_attempts_maximum") == 1, controls)
check("one_shutdown_max", controls.get("wsl_shutdown_attempts_maximum") == 1, controls)
check("zero_retry", controls.get("automatic_retry_count") == 0, controls)
check("no_start_allowed", controls.get("docker_desktop_start_allowed") is False, controls)
for key in (
    "image_pull_or_build_allowed", "container_create_or_run_allowed",
    "settings_change_allowed", "install_or_download_allowed",
    "materialization_allowed", "training_evaluation_or_test_allowed",
    "raw_stdout_or_stderr_persisted",
):
    check(f"control_false:{key}", controls.get(key) is False, controls.get(key))

check("runner_ast", isinstance(tree, ast.Module), None)
check("runner_expected_head", 'parser.add_argument("--expected-head", required=True)' in source, None)
check("runner_stop_once_id", source.count('"B03_DOCKER_DESKTOP_STOP_ONCE"') == 1, source.count('"B03_DOCKER_DESKTOP_STOP_ONCE"'))
check("runner_shutdown_once_id", source.count('"B04_WSL_SHUTDOWN_ONCE"') == 1, source.count('"B04_WSL_SHUTDOWN_ONCE"'))
check("runner_stop_literal", '[str(DOCKER), "desktop", "stop"]' in source, None)
check("runner_shutdown_literal", '[str(WSL), "--shutdown"]' in source, None)
check("runner_no_start_literal", '[str(DOCKER), "desktop", "start"]' not in source, None)
check("runner_finally_shutdown", "finally:" in source and 'record("B04_WSL_SHUTDOWN_ONCE"' in source, None)
check("runner_no_retry_sleep", "time.sleep(" not in source and '"automatic_retry_count": 0' in source, None)
check("runner_shell_false", "shell=True" not in source and source.count("shell=False") >= 3, source.count("shell=False"))
check("runner_pre_query_gate", "if pre_queries_complete and not baseline_already_stopped:" in source, None)
check("runner_post_gate", "post_baseline_stopped" in source and "PASS_PC2W_P1_ATTEMPT003_BASELINE_RESTORED" in source, None)
check("runner_strict_wsl_total_parse", all(token in source for token in ("return [], False", "seen_names", "header_seen", "wsl_list_parse_complete")), None)
valid_wsl = "  NAME              STATE           VERSION\r\n* docker-desktop    Stopped         2\r\n".encode("utf-16-le")
partial_wsl = "  NAME              STATE           VERSION\r\n* docker-desktop    Stopped         2\r\nmalformed row\r\n".encode("utf-16-le")
duplicate_wsl = "  NAME              STATE           VERSION\r\n* docker-desktop    Stopped         2\r\n  docker-desktop    Stopped         2\r\n".encode("utf-16-le")
missing_header_wsl = "* docker-desktop    Stopped         2\r\n".encode("utf-16-le")
valid_rows, valid_complete = runner_module.parse_wsl_list(valid_wsl)
partial_rows, partial_complete = runner_module.parse_wsl_list(partial_wsl)
duplicate_rows, duplicate_complete = runner_module.parse_wsl_list(duplicate_wsl)
missing_header_rows, missing_header_complete = runner_module.parse_wsl_list(missing_header_wsl)
check("wsl_fixture_valid_passes", valid_complete is True and valid_rows == [{"name": "docker-desktop", "state": "Stopped", "version": 2}], [valid_rows, valid_complete])
check("wsl_fixture_partial_rejected", partial_rows == [] and partial_complete is False, [partial_rows, partial_complete])
check("wsl_fixture_duplicate_rejected", duplicate_rows == [] and duplicate_complete is False, [duplicate_rows, duplicate_complete])
check("wsl_fixture_missing_header_rejected", missing_header_rows == [] and missing_header_complete is False, [missing_header_rows, missing_header_complete])
check("runner_daemon_specific", all(token in source for token in ("DAEMON_PIPE_MARKERS", "DAEMON_PIPE_MISSING_MARKERS", "PERMISSION_ERROR_MARKERS")), None)
check("runner_exact_outputs", "entries = list(output_root.iterdir())" in source and "not all(path.is_file() for path in entries)" in source, None)
check("runner_frozen_gates", "frozen artifact mismatch" in source and "git_blob_fact" in source, None)
check("runner_current_passport_dependency", '"stage1e_e4_r6_pc2w_p1_attempt003_user_authorization_v2"' in source and '"stage1e_e4_r6_pc2w_p1_attempt003_user_authorization_v1"' not in source, None)
check("runner_no_science", all(token in source for token in ('"scientific_execution_performed": False', '"result_status": "NOT_RUN"', '"test_set_opened": "NO"', '"accepted_result_rows": 0')), None)

truth = dispatch.get("truth_state")
check("truth", truth == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, truth)
failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT003_BASELINE_DISPATCH_STATIC_READY" if not failures else "FAIL",
    "expected_head": expected_head,
    "head": head,
    "parent": parent,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)
