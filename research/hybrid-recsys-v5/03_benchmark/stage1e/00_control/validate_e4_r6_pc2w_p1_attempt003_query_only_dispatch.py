#!/usr/bin/env python3
"""Static fail-closed validator for the attempt-003 query-only dispatch."""

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


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt003_query_only.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt003_query_only_dispatch.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt003_query_only_contract.json"
AUTH = CONTROL / "e4_r6_pc2w_p1_attempt003_user_authorization_and_model_override.json"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_query_only_dispatch.json"
REQUIREMENTS = CONTROL / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
NATIVE_HELPER = CONTROL / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
NATIVE_VALIDATION = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_native_offline_validation_receipt.json"
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003"
)
EXPECTED_OUTPUT_FILES = [
    "command_receipts.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
    "runtime_inventory.json",
]
EXPECTED_EXECUTION_DELTA = {AUTH.as_posix(), DISPATCH.as_posix()}
EXPECTED_RUNNER_DELTA = {RUNNER.as_posix(), VALIDATOR.as_posix(), CONTRACT.as_posix()}
EXPECTED_FROZEN = {RUNNER, NATIVE_HELPER, AUTH, REQUIREMENTS, CONTRACT, NATIVE_VALIDATION}
EXPECTED_COMMAND_IDS = [
    "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE",
    "A01_WSL_LIST_VERBOSE_PRE_GATE",
    "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE",
    "A03_RUNTIME_PROCESS_NAMES_PRE_GATE",
    "A04_WSL_VERSION_IDENTITY",
    "A05_WINDOWS_IDENTITY",
    "A06_DOCKER_DESKTOP_FILE_IDENTITY",
    "A07_DOCKER_DESKTOP_START_ONCE",
    "A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING",
    "A09_CONTAINER_LIST_INITIAL",
    "A10_IMAGE_LIST_INITIAL",
    "A11_DOCKER_VERSION",
    "A12_DOCKER_INFO",
    "A13_CONTEXT_INSPECT",
    "A14_SYSTEM_DF",
    "A15_WSL_LIST_VERBOSE_DURING",
    "A16_PROCESS_INVENTORY_DURING",
    "A17_NETWORK_CONNECTION_INVENTORY_DURING",
    "A18_CONTAINER_LIST_FINAL",
    "A19_IMAGE_LIST_FINAL",
    "A20_DOCKER_EVENTS_BEFORE_STOP",
    "A21_DOCKER_DESKTOP_STOP_ONCE",
    "A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER",
    "A23_WSL_LIST_VERBOSE_POST_A",
    "A24_WSL_LIST_RUNNING_QUIET_POST_A",
    "A25_RUNTIME_PROCESS_NAMES_POST_A",
    "A26_WSL_LIST_VERBOSE_POST_B",
    "A27_WSL_LIST_RUNNING_QUIET_POST_B",
    "A28_RUNTIME_PROCESS_NAMES_POST_B",
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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object JSON root: {path}")
    return value


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_fact(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256(data)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(repo: Path, revision: str, relative: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative.as_posix()}"],
        cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=False, check=True,
    )
    return len(completed.stdout), sha256(completed.stdout)


def changed_set(repo: Path, revision: str) -> set[str]:
    return set(filter(None, git(
        repo, "diff-tree", "--no-commit-id", "--name-only", "-r", revision
    ).splitlines()))


def import_runner(path: Path) -> Any:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("attempt003_query_runner_static", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("runner import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": detail})

    head = git(repo, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)))
    check("exact_head", head == expected_head, head)
    check("exact_repo_root", Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo)
    check("worktree_clean", not git(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    parents = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    check("execution_has_one_parent", len(parents) == 2, parents)
    parent = parents[1].casefold() if len(parents) == 2 else ""
    parent_parents = git(repo, "rev-list", "--parents", "-n", "1", parent).split() if parent else []
    check("runner_checkpoint_has_one_parent", len(parent_parents) == 2, parent_parents)
    check("exact_execution_delta", changed_set(repo, head) == EXPECTED_EXECUTION_DELTA, sorted(changed_set(repo, head)))
    check("exact_runner_delta", changed_set(repo, parent) == EXPECTED_RUNNER_DELTA, sorted(changed_set(repo, parent)))
    check("attempt003_output_root_absent", not (repo / OUTPUT).exists())

    documents: dict[Path, dict[str, Any]] = {}
    for relative in (CONTRACT, AUTH, DISPATCH, REQUIREMENTS, NATIVE_VALIDATION):
        try:
            documents[relative] = load_json(repo / relative)
            check(f"strict_json:{relative.name}", True)
        except Exception as exc:
            check(f"strict_json:{relative.name}", False, type(exc).__name__)
    contract = documents.get(CONTRACT, {})
    auth = documents.get(AUTH, {})
    dispatch = documents.get(DISPATCH, {})
    requirements = documents.get(REQUIREMENTS, {})
    native_validation = documents.get(NATIVE_VALIDATION, {})
    check("contract_schema", contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-query-only-contract-1.0")
    check("authorization_schema", auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-user-authorization-standard-1.0")
    check("dispatch_schema", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-query-only-dispatch-1.0")
    check("requirements_schema", requirements.get("schema_version") == "stage1e-e4-r6-pc2w-p1-docker-query-preflight-requirements-1.0")
    check("native_pass_validated", native_validation.get("verdict") == "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_V5_VALIDATED")
    check("native_next_gate", native_validation.get("next_gate") == "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT")
    check("native_attempt003_unopened", native_validation.get("attempt_result", {}).get("attempt003_execution_opened") is False)
    check("native_zero_retry", native_validation.get("attempt_result", {}).get("automatic_retry_count") == 0)
    check("immediate_native_replay", contract.get("native_pre_gate_replay_immediately_before_start") is True)
    check("status_advisory_only", contract.get("docker_desktop_status_advisory_only") is True)
    check("status_no_admission_authority", contract.get("docker_desktop_status_admission_authority") is False)
    check("contract_zero_retry", contract.get("authorized_runtime_transitions", {}).get("automatic_retry_count") == 0)
    check("contract_one_start", contract.get("authorized_runtime_transitions", {}).get("docker_desktop_start_attempts_exactly") == 1)
    check("contract_one_stop", contract.get("authorized_runtime_transitions", {}).get("docker_desktop_stop_attempts_exactly") == 1)
    check("contract_stop_finally", contract.get("authorized_runtime_transitions", {}).get("stop_is_in_finally_after_any_start_attempt") is True)
    check("contract_exact_outputs", contract.get("output_contract", {}).get("exact_files") == EXPECTED_OUTPUT_FILES)
    check("contract_truth_state", contract.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0})
    check("contract_standard_only", contract.get("model_policy", {}).get("fresh_audit_service_tier") == "default" and contract.get("model_policy", {}).get("fast_or_priority_allowed") is False)

    decision = auth.get("user_decision", {})
    check("auth_entry_parent", str(auth.get("entry_checkpoint", "")).casefold() == parent)
    check("auth_decision", decision.get("decision") == "AUTHORIZE_PC2W_P1_ATTEMPT003_START_QUERY_STOP_ON_VALIDATED_NATIVE_PASS")
    check("auth_start", decision.get("one_docker_desktop_start_authorized") is True)
    check("auth_stop", decision.get("one_docker_desktop_stop_authorized") is True)
    check("auth_query_only", decision.get("query_only_runtime_inventory_authorized") is True)
    false_flags = [
        "automatic_retry_authorized", "image_pull_or_build_authorized",
        "container_create_or_run_authorized", "docker_or_wsl_settings_change_authorized",
        "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
        "materialization_authorized", "training_authorized", "evaluation_authorized",
        "test_access_authorized",
    ]
    check("auth_forbidden_flags_false", all(decision.get(key) is False for key in false_flags))
    check("auth_standard_tier", auth.get("model_policy", {}).get("service_tier") == "default")
    check("auth_fast_forbidden", auth.get("model_policy", {}).get("fast_or_priority_allowed") is False)

    binding = dispatch.get("execution_binding", {})
    check("dispatch_runner_parent", str(dispatch.get("runner_checkpoint", "")).casefold() == parent)
    check("dispatch_output_root", Path(binding.get("output_root", "")).resolve() == (repo / OUTPUT).resolve())
    check("dispatch_working_directory", Path(binding.get("working_directory", "")).resolve() == repo)
    check("dispatch_output_files", binding.get("expected_output_files") == EXPECTED_OUTPUT_FILES)
    expected_argv = [
        r"C:\Program Files\Python311\python.exe", RUNNER.as_posix(),
        "--repo-root", str(repo), "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    check("dispatch_exact_argv", binding.get("argv") == expected_argv, binding.get("argv"))
    check("dispatch_standard_tier", dispatch.get("model_policy", {}).get("service_tier") == "default")
    check("dispatch_fast_forbidden", dispatch.get("model_policy", {}).get("fast_or_priority_allowed") is False)
    check("dispatch_zero_retry", dispatch.get("execution_binding", {}).get("automatic_retry_count") == 0)

    frozen = dispatch.get("frozen_artifacts")
    frozen_map = {
        Path(str(row.get("path"))): row for row in frozen or [] if isinstance(row, dict)
    }
    check("frozen_exact_set", set(frozen_map) == EXPECTED_FROZEN, sorted(path.as_posix() for path in frozen_map))
    for relative, row in frozen_map.items():
        check(
            f"frozen_blob:{relative.name}",
            blob_fact(repo, head, relative) == (row.get("git_blob_bytes"), row.get("git_blob_sha256")),
        )
    check("runner_frozen_in_parent", blob_fact(repo, parent, RUNNER) == blob_fact(repo, head, RUNNER))
    check("contract_frozen_in_parent", blob_fact(repo, parent, CONTRACT) == blob_fact(repo, head, CONTRACT))

    source = (repo / RUNNER).read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
        check("runner_ast_parse", True)
    except SyntaxError as exc:
        tree = ast.Module(body=[], type_ignores=[])
        check("runner_ast_parse", False, str(exc))
    check("runner_no_shell_true", "shell=True" not in source and "shell = True" not in source)
    check("runner_no_wsl_shutdown", "--shutdown" not in source and "--terminate" not in source)
    check(
        "runner_no_fast_priority_assignment",
        "XHIGH_FAST" not in source
        and "Sol XHigh Fast" not in source
        and '\"service_tier\": \"priority\"' not in source,
    )
    check("runner_status_advisory", source.count("STATUS_ADVISORY") >= 3)
    check("runner_imports_native_gate", "attempt003_offline_equivalent_observation as native_gate" in source)
    check("runner_named_pipe_pre_and_post", source.count("probe_desktop_linux_pipe()") == 3)
    check("runner_finally_stop", "finally:" in source and "A21_DOCKER_DESKTOP_STOP_ONCE" in source)
    check("runner_zero_retry_literal", source.count('"automatic_retry_count": 0') >= 2)
    check("runner_truth_not_run", '"result_status": "NOT_RUN"' in source)
    check("runner_test_unopened", '"test_set_opened": "NO"' in source)
    check("runner_rows_zero", '"accepted_result_rows": 0' in source)
    check("runner_exact_command_ids", all(source.count(command_id) >= 1 for command_id in EXPECTED_COMMAND_IDS))
    forbidden_runtime = [
        '"pull"', '"build"', '"create"', '"run"', '"exec"', '"commit"',
        '"import"', '"load"', '"push"', '"login"', '"prune"',
    ]
    check("runner_forbidden_commands_guarded", all(token in source for token in forbidden_runtime))
    subprocess_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
    ]
    check("runner_subprocess_calls_bounded", len(subprocess_calls) == 3, len(subprocess_calls))
    check("runner_subprocess_shell_false", all(
        any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False for keyword in call.keywords)
        for call in subprocess_calls
    ))

    try:
        runner = import_runner(repo / RUNNER)
        valid = "  NAME            STATE           VERSION\r\n* Ubuntu          Stopped         2\r\n  docker-desktop  Stopped         2\r\n".encode("utf-16-le")
        check("fixture_wsl_valid", len(runner.parse_wsl_list(valid)) == 2)
        for label, fixture in {
            "partial": "NAME STATE VERSION\nUbuntu Stopped 2\ngarbage\n".encode(),
            "duplicate": "NAME STATE VERSION\nUbuntu Stopped 2\nUbuntu Stopped 2\n".encode(),
            "missing_header": "Ubuntu Stopped 2\n".encode(),
        }.items():
            try:
                runner.parse_wsl_list(fixture)
                check(f"fixture_wsl_reject_{label}", False)
            except ValueError:
                check(f"fixture_wsl_reject_{label}", True)
        try:
            runner.parse_wsl_running(b"Ubuntu\nubuntu\n")
            check("fixture_running_reject_duplicate", False)
        except ValueError:
            check("fixture_running_reject_duplicate", True)
        check("fixture_running_empty_valid", runner.parse_wsl_running(b"") == [])
        check("module_expected_command_ids", runner.EXPECTED_COMMAND_IDS == EXPECTED_COMMAND_IDS)
        check("module_output_root", runner.OUTPUT_RELATIVE == OUTPUT)
        check("module_exact_output_files", sorted(runner.EXPECTED_OUTPUT_FILES) == EXPECTED_OUTPUT_FILES)
    except Exception as exc:
        check("runner_fixture_suite", False, type(exc).__name__)

    failures = [row for row in checks if not row["pass"]]
    verdict = (
        "PASS_PC2W_P1_ATTEMPT003_QUERY_ONLY_RUNNER_READY_FOR_FRESH_AUDIT"
        if not failures else "REWORK_REQUIRED"
    )
    print(json.dumps({
        "verdict": verdict,
        "head": head,
        "parent": parent,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
    }, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
