#!/usr/bin/env python3
"""Fail-closed static validator for the PC2W-P1 v2 execution dispatch."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
REPO = CONTROL.parents[4]
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_dispatch.json"
AUTH = CONTROL / "e4_r6_pc2w_p1_user_authorization_and_model_override.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_query_only.py"
OUTPUT = REPO / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-001"
)
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
    value: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate key: {key}")
        case = key.casefold()
        if case in folded:
            raise DuplicateKeyError(f"case collision: {folded[case]} vs {key}")
        value[key] = item
        folded[case] = key
    return value


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object root: {path}")
    return value


def file_fact(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPO, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


try:
    dispatch = load(DISPATCH)
    auth = load(AUTH)
    source = RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

head = git("rev-parse", "HEAD").casefold()
parent_fields = git("rev-list", "--parents", "-n", "1", "HEAD").split()
parent = parent_fields[1].casefold() if len(parent_fields) == 2 else None
changed = set(
    filter(
        None,
        git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines(),
    )
)
status = git("status", "--porcelain=v1", "--untracked-files=all")

check("dispatch_schema", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-dispatch-2.0", dispatch.get("schema_version"))
check("auth_schema", auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-user-authorization-model-override-2.0", auth.get("schema_version"))
check("stage", dispatch.get("stage_id") == "E4-R6-PC2W-P1", dispatch.get("stage_id"))
check("worktree_clean", status == "", status)
check("single_parent", len(parent_fields) == 2, parent_fields)
check("runner_checkpoint_parent", parent == dispatch.get("runner_checkpoint", "").casefold(), [parent, dispatch.get("runner_checkpoint")])
check("authorization_parent", parent == auth.get("entry_checkpoint", "").casefold(), [parent, auth.get("entry_checkpoint")])
check("exact_execution_commit_changes", changed == EXPECTED_CHANGED, sorted(changed))
check("output_absent", not OUTPUT.exists(), str(OUTPUT))

binding = dispatch.get("execution_binding", {})
check("exact_output_binding", binding.get("output_root") == str(OUTPUT), binding.get("output_root"))
check("auth_output_binding", auth.get("authorized_output_root") == str(OUTPUT), auth.get("authorized_output_root"))
check("exact_output_set", binding.get("expected_output_files") == EXPECTED_OUTPUTS, binding.get("expected_output_files"))
check("argv_exact", binding.get("argv") == [r"C:\Program Files\Python311\python.exe", "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_query_only.py", "--repo-root", str(REPO)], binding.get("argv"))

frozen = dispatch.get("frozen_artifacts", [])
frozen_map = {
    row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256"))
    for row in frozen
    if isinstance(row, dict)
}
check("frozen_artifact_count", len(frozen_map) == 5, sorted(frozen_map))
for relative, expected in frozen_map.items():
    path = REPO / str(relative)
    check(f"frozen_exists:{relative}", path.is_file(), str(path))
    if path.is_file():
        check(f"frozen_fact:{relative}", file_fact(path) == expected, [file_fact(path), expected])

runner_relative = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/execute_e4_r6_pc2w_p1_query_only.py"
try:
    blob = subprocess.run(
        ["git", "show", f"{parent}:{runner_relative}"], cwd=REPO,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, shell=False,
    ).stdout
    parent_runner_fact = (len(blob), hashlib.sha256(blob).hexdigest())
except Exception:
    parent_runner_fact = None
check("parent_freezes_runner", parent_runner_fact == file_fact(RUNNER), [parent_runner_fact, file_fact(RUNNER)])

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
check("runner_one_start_id", source.count('"P06_DOCKER_DESKTOP_START_ONCE"') == 1, source.count('"P06_DOCKER_DESKTOP_START_ONCE"'))
check("runner_one_stop_id", source.count('"P20_DOCKER_DESKTOP_STOP_ONCE"') == 1, source.count('"P20_DOCKER_DESKTOP_STOP_ONCE"'))
check("runner_start_literal", '[str(DOCKER), "desktop", "start"]' in source, None)
check("runner_stop_literal", '[str(DOCKER), "desktop", "stop"]' in source, None)
check("runner_finally", "finally:" in source and "if startup_attempted:" in source, None)
check("runner_no_sleep", "time.sleep(" not in source, None)
check("runner_shell_lock", "shell=True" not in source and source.count("shell=False") >= 3, source.count("shell=False"))
check("runner_exact_output_constant", all(f'"{name}"' in source for name in EXPECTED_OUTPUTS), EXPECTED_OUTPUTS)
check("runner_clean_gate", '"status", "--porcelain=v1", "--untracked-files=all"' in source, None)
check("runner_parent_gate", '"rev-list", "--parents", "-n", "1", "HEAD"' in source, None)
check("runner_change_set_gate", "EXPECTED_HEAD_CHANGE_SET" in source, None)
check("runner_frozen_hash_gate", "frozen artifact mismatch" in source and "git_blob_fact" in source, None)
check("runner_exact_root", "authorized_output_root" in source and "OUTPUT_RELATIVE" in source, None)
check("runner_pre_gate", "pre_gate" in source and "if all(value is True for value in pre_gate.values())" in source, None)
check("runner_daemon_marker_gate", "daemon_is_specifically_unavailable" in source and "DAEMON_UNAVAILABLE_MARKERS" in source, None)
check("runner_mutation_gate", all(token in source for token in ("containers_running_zero", "container_inventory_unchanged", "image_inventory_unchanged", "container_or_image_events_absent")), None)
check("runner_identity_evidence", all(token in source for token in ("P03_WSL_VERSION_BEFORE", "P04_WINDOWS_IDENTITY_BEFORE", "P05_DOCKER_DESKTOP_FILE_IDENTITY_BEFORE", '"wsl_state"')), None)
check("runner_secret_safety", all(token in source for token in ('"raw_stdout_or_stderr_persisted": False', '"raw_context_persisted": False', '"proxy_values_persisted": False', "RemoteAddressSha256")), None)
check("runner_no_raw_error", '"error_sha256"' in source and '"error": str(exc)' not in source, None)
check("runner_no_science", all(token in source for token in ('"scientific_execution_performed": False', '"result_status": "NOT_RUN"', '"test_set_opened": "NO"', '"accepted_result_rows": 0')), None)

truth = dispatch.get("truth_state")
check("dispatch_truth", truth == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, truth)
failures = [row for row in checks if not row["pass"]]
print(
    json.dumps(
        {
            "verdict": "PASS_PC2W_P1_DISPATCH_V2_STATIC_READY" if not failures else "FAIL",
            "execution_checkpoint": head,
            "runner_checkpoint": parent,
            "checks": f"{len(checks) - len(failures)}/{len(checks)}",
            "failure_count": len(failures),
            "failures": failures,
        },
        indent=2,
    )
)
sys.exit(1 if failures else 0)
