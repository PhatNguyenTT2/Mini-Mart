#!/usr/bin/env python3
"""Static fail-closed validator for the PC2W-P1 query-only dispatch."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
REPO = CONTROL.parents[4]
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_dispatch.json"
AUTH = CONTROL / "e4_r6_pc2w_p1_user_authorization_and_model_override.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_query_only.py"


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


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


try:
    dispatch = load(DISPATCH)
    auth = load(AUTH)
    runner_source = RUNNER.read_text(encoding="utf-8")
    ast.parse(runner_source)
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

check("dispatch_schema", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-dispatch-1.0", dispatch.get("schema_version"))
check("dispatch_stage", dispatch.get("stage_id") == "E4-R6-PC2W-P1", dispatch.get("stage_id"))
check("runner_checkpoint", dispatch.get("runner_checkpoint") == "3ebe4caeff8d83d739f96eb7634fed96a5759ec4", dispatch.get("runner_checkpoint"))

frozen = dispatch.get("frozen_artifacts", [])
observed = {row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256")) for row in frozen}
check("frozen_artifact_count", len(observed) == 5, sorted(observed))
for relative, expected in observed.items():
    path = REPO / relative
    check(f"frozen_exists:{relative}", path.is_file(), str(path))
    if path.is_file():
        check(f"frozen_fact:{relative}", file_fact(path) == expected, [file_fact(path), expected])

interpreter = dispatch.get("interpreter", {})
interpreter_path = Path(interpreter.get("path", ""))
check("interpreter_path", interpreter_path == Path(r"C:\Program Files\Python311\python.exe"), str(interpreter_path))
check("interpreter_exists", interpreter_path.is_file(), str(interpreter_path))
if interpreter_path.is_file():
    check("interpreter_hash", file_fact(interpreter_path)[1] == interpreter.get("sha256"), file_fact(interpreter_path)[1])

binding = dispatch.get("execution_binding", {})
output_root = Path(binding.get("output_root", ""))
check("output_root_absent", not output_root.exists(), str(output_root))
check("output_root_inside_repo", REPO in output_root.parents, str(output_root))
check("output_file_set", binding.get("expected_output_files") == ["command_receipts.json", "runtime_inventory.json", "p1_execution_receipt.json", "p1_handoff.json"], binding.get("expected_output_files"))
check("head_binding_rule", "full commit containing this dispatch" in binding.get("expected_head_rule", "").casefold(), binding.get("expected_head_rule"))
argv = binding.get("argv_template", [])
check("argv_interpreter", argv[:1] == [str(interpreter_path)], argv[:1])
check("argv_runner", len(argv) == 8 and argv[1].endswith("execute_e4_r6_pc2w_p1_query_only.py"), argv)
check("argv_output_root", len(argv) == 8 and argv[5] == str(output_root), argv)

controls = dispatch.get("execution_controls", {})
check("one_start", controls.get("docker_desktop_start_attempts") == 1, controls.get("docker_desktop_start_attempts"))
check("one_stop", controls.get("docker_desktop_stop_attempts_after_start_attempt") == 1, controls.get("docker_desktop_stop_attempts_after_start_attempt"))
check("zero_retry", controls.get("automatic_retry_count") == 0, controls.get("automatic_retry_count"))
check("start_stop_timeout", controls.get("hard_start_timeout_seconds") == 180 and controls.get("hard_stop_timeout_seconds") == 180, controls)
for key in ("raw_stdout_or_stderr_persisted", "proxy_secret_values_persisted", "image_pull_or_build_allowed", "container_create_or_run_allowed", "docker_or_wsl_settings_change_allowed", "materialization_allowed", "training_evaluation_or_test_allowed"):
    check(f"control_false:{key}", controls.get(key) is False, controls.get(key))

decision = auth.get("user_decision", {})
check("user_authorized_p1", decision.get("decision") == "AUTHORIZE_PC2W_P1_EXECUTION", decision.get("decision"))
for key in ("automatic_retry_authorized", "image_pull_or_build_authorized", "container_create_or_run_authorized", "docker_or_wsl_settings_change_authorized", "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized", "materialization_authorized", "training_authorized", "evaluation_authorized", "test_access_authorized"):
    check(f"auth_false:{key}", decision.get(key) is False, decision.get(key))

model = auth.get("model_policy_override", {}).get("all_new_phase_worktree_tasks", {})
check("worktree_model", model.get("model") == "gpt-5.6-sol", model)
check("worktree_reasoning", model.get("reasoning_effort") == "xhigh", model)
check("worktree_fast", model.get("service_tier") == "priority", model)

check("runner_start_id_once", runner_source.count('"P03_DOCKER_DESKTOP_START_ONCE"') == 1, runner_source.count('"P03_DOCKER_DESKTOP_START_ONCE"'))
check("runner_stop_id_once", runner_source.count('"P14_DOCKER_DESKTOP_STOP_ONCE"') == 1, runner_source.count('"P14_DOCKER_DESKTOP_STOP_ONCE"'))
check("runner_start_literal", '[str(DOCKER), "desktop", "start"]' in runner_source, None)
check("runner_stop_literal", '[str(DOCKER), "desktop", "stop"]' in runner_source, None)
check("runner_no_sleep", "time.sleep(" not in runner_source, None)
check("runner_shell_false", "shell=False" in runner_source and "shell=True" not in runner_source, None)
check("runner_root_absence", "if output_root.exists()" in runner_source and "exist_ok=False" in runner_source, None)
check("runner_hash_lock", "EXPECTED_DOCKER_DESKTOP_SHA256" in runner_source and "Docker Desktop executable hash changed" in runner_source, None)
check("runner_prohibited_guard", "PROHIBITED_DOCKER_SUBCOMMANDS" in runner_source and "docker_subcommand_is_allowed" in runner_source, None)
check("runner_no_raw_persistence", '"raw_stdout_or_stderr_persisted": False' in runner_source, None)
check("runner_no_scientific_execution", '"scientific_execution_performed": False' in runner_source, None)
check("runner_truth_lock", all(token in runner_source for token in ('"result_status": "NOT_RUN"', '"test_set_opened": "NO"', '"accepted_result_rows": 0')), None)
check("runner_exact_output_names", all(name in runner_source for name in binding.get("expected_output_files", [])), binding.get("expected_output_files"))

truth = dispatch.get("truth_state")
check("dispatch_truth", truth == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, truth)

failures = [row for row in checks if not row["pass"]]
print(json.dumps({"verdict": "PASS_PC2W_P1_DISPATCH_STATIC_READY" if not failures else "FAIL", "checks": f"{len(checks)-len(failures)}/{len(checks)}", "failure_count": len(failures), "failures": failures}, indent=2))
sys.exit(1 if failures else 0)
