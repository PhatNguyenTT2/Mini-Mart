#!/usr/bin/env python3
"""Fail-closed validator for the Attempt-005 authorization/dispatch checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt005_instrumented.py"
BASE_RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt004_query_only.py"
NATIVE_HELPER = CONTROL / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
AUTH = CONTROL / "e4_r6_pc2w_p1_attempt005_user_authorization.json"
REQUIREMENTS = CONTROL / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt005_instrumented_contract.json"
POLICY = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_am/"
    "E4_R6PC2W_P1_residual_process_policy_review/"
    "prospective_residual_process_admission_policy.md"
)
POLICY_HANDOFF = POLICY.with_name("policy_review_handoff.json")
POLICY_VALIDATION = CONTROL / (
    "rebaseline_v2_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt.json"
)
AUDIT_RECEIPT = CONTROL / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt005_fourth_static_audit_receipt.json"
)
STATE = CONTROL / "pipeline_state_stage1e.json"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt005_dispatch.json"
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_an/"
    "E4_R6PC2W_P1_attempt005_instrumented"
)
EXECUTION_ROOT = Path(r"E:\UIT\cv\backend")
PYTHON = Path(r"C:\Program Files\Python311\python.exe")
AUDITED_CHECKPOINT = "e8369bec6cd580346d748781e89748648ba6d5d0"
AUDIT_TASK_ID = "01a0350d-8dbe-7971-a8cc-9df33cf2b882"
EXPECTED_EXECUTION_DELTA = {AUTH.as_posix(), DISPATCH.as_posix()}
EXPECTED_OUTPUT_FILES = [
    "command_receipts.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
    "runtime_inventory.json",
]
EXPECTED_FROZEN = {
    RUNNER,
    BASE_RUNNER,
    NATIVE_HELPER,
    AUTH,
    REQUIREMENTS,
    CONTRACT,
    POLICY,
    POLICY_HANDOFF,
    POLICY_VALIDATION,
}
EXPECTED_MODEL_POLICY = {
    "coordinator_model": "gpt-5.6-sol",
    "coordinator_reasoning_effort": "max",
    "static_audit_model": "gpt-5.6-sol",
    "static_audit_reasoning_effort": "xhigh",
    "service_tier": "default",
    "fast_or_priority_allowed": False,
}


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
        raise ValueError(f"non-object JSON root: {path}")
    return value


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(repo: Path, revision: str, relative: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative.as_posix()}"],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    )
    value = completed.stdout
    return len(value), hashlib.sha256(value).hexdigest()


def changed_set(repo: Path, revision: str) -> set[str]:
    return set(filter(None, git(
        repo, "diff-tree", "--no-commit-id", "--name-only", "-r", revision
    ).splitlines()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
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
    check("exact_execution_root", repo == EXECUTION_ROOT.resolve(), str(repo))
    check("exact_git_root", Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo)
    check("worktree_clean", not git(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    parent_line = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    check("one_parent", len(parent_line) == 2, parent_line)
    parent = parent_line[1].casefold() if len(parent_line) == 2 else ""
    check("exact_execution_delta", changed_set(repo, head) == EXPECTED_EXECUTION_DELTA, sorted(changed_set(repo, head)))
    check("output_root_absent", not (repo / OUTPUT).exists())

    documents: dict[Path, dict[str, Any]] = {}
    for relative in (AUTH, CONTRACT, AUDIT_RECEIPT, STATE, DISPATCH, REQUIREMENTS, POLICY_HANDOFF, POLICY_VALIDATION):
        try:
            documents[relative] = load_json(repo / relative)
            check(f"strict_json:{relative.name}", True)
        except Exception as exc:
            check(f"strict_json:{relative.name}", False, type(exc).__name__)
    auth = documents.get(AUTH, {})
    contract = documents.get(CONTRACT, {})
    audit = documents.get(AUDIT_RECEIPT, {})
    state = documents.get(STATE, {})
    dispatch = documents.get(DISPATCH, {})
    policy_handoff = documents.get(POLICY_HANDOFF, {})
    policy_validation = documents.get(POLICY_VALIDATION, {})

    check("contract_schema", contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt005-instrumented-contract-1.0")
    check("auth_schema", auth.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt005-user-authorization-1.0")
    check("audit_schema", audit.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt005-fourth-static-audit-receipt-1.0")
    check("dispatch_schema", dispatch.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt005-dispatch-1.0")
    check("stage_ids", all(document.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT005" for document in (auth, audit, dispatch)))
    check("policy_verdict", policy_handoff.get("verdict") == "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED")
    check("policy_validation", policy_validation.get("verdict") == "PASS_PC2W_P1_RESIDUAL_PROCESS_POLICY_REVIEW_VALIDATED")

    check("audit_checkpoint", audit.get("audit_task", {}).get("audited_checkpoint") == AUDITED_CHECKPOINT)
    check("audit_task_id", audit.get("audit_task", {}).get("thread_id") == AUDIT_TASK_ID)
    check("audit_verdict", audit.get("verdict") == "PASS_PC2W_P1_ATTEMPT005_PACKET_READY_FOR_AUTHORIZATION_AND_EXACT_COMMAND_CONFIRMATION")
    validation = audit.get("validation", {})
    check("audit_162", validation.get("checks_passed") == 162 and validation.get("checks_total") == 162 and validation.get("failures") == [])
    check("audit_negative_fixtures", validation.get("prior_malformed_fixtures_rejected") == 109 and validation.get("time_extension_fixtures_rejected") == 10)
    check("audit_valid_utc", validation.get("valid_dotnet_roundtrip_utc_fixture_accepted") is True)
    findings = audit.get("findings", {})
    check("audit_no_material_findings", all(findings.get(key) == 0 for key in ("critical", "major", "minor")))
    safety = audit.get("safety", {})
    check("audit_no_runtime", safety.get("runtime_commands_executed") is False and safety.get("attempt005_runner_executed") is False)
    check("audit_no_writes", safety.get("write_set") == [])
    check("audit_standard_requested", audit.get("model_policy", {}).get("requested_service_tier") == "default" and audit.get("model_policy", {}).get("fast_or_priority_allowed") is False)
    check("audit_actual_unobservable", all(audit.get("model_policy", {}).get(key) == "UNOBSERVABLE" for key in ("actual_model_observability", "actual_reasoning_effort_observability", "actual_service_tier_observability")))
    check("runner_same_as_audited", blob_fact(repo, parent, RUNNER) == blob_fact(repo, AUDITED_CHECKPOINT, RUNNER))
    check("contract_same_as_audited", blob_fact(repo, parent, CONTRACT) == blob_fact(repo, AUDITED_CHECKPOINT, CONTRACT))

    check("state_audit_pass", state.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt005_fourth_static_audit_pass_dispatch_packet_preparation_no_execution")
    check("state_truth_not_run", state.get("result_status") == "NOT_RUN" and state.get("test_set_opened") == "NO")
    attempt = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {}).get("p1_attempt005_instrumented", {})
    check("state_fourth_audit_task", attempt.get("fourth_fresh_static_audit", {}).get("task_id") == AUDIT_TASK_ID)
    check("state_execution_not_opened", attempt.get("execution_previously_opened") is False)
    check("state_confirmation_required", attempt.get("exact_command_confirmation_required") is True)

    check("auth_parent", str(auth.get("entry_checkpoint", "")).casefold() == parent)
    check("auth_output_root", auth.get("authorized_output_root") == str((repo / OUTPUT).resolve()))
    basis = auth.get("authorization_basis", {})
    check("auth_user_text", basis.get("latest_user_decision_text") == "Ủy quyền và tiếp tục")
    check("auth_source_thread", basis.get("source_thread_id") == "019ff4f0-802a-7892-a989-24f32ac26ac8")
    check("auth_audit_pass", auth.get("entry_evidence", {}).get("fourth_static_audit_verdict") == audit.get("verdict"))
    decision = auth.get("user_decision", {})
    check("auth_decision", decision.get("decision") == "AUTHORIZE_ATTEMPT005_INSTRUMENTED_CURRENT_HOST")
    true_flags = (
        "one_docker_desktop_start_authorized",
        "one_docker_desktop_stop_authorized",
        "one_wsl_shutdown_after_stop_authorized",
        "three_instrumented_closure_snapshots_authorized",
        "query_only_runtime_inventory_authorized",
    )
    false_flags = (
        "automatic_retry_authorized", "force_kill_authorized",
        "service_restart_authorized", "settings_change_authorized",
        "image_pull_or_build_authorized", "container_create_or_run_authorized",
        "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
        "materialization_authorized", "training_authorized", "evaluation_authorized",
        "benchmark_admission_authorized", "test_access_authorized",
    )
    check("auth_required_true", all(decision.get(key) is True for key in true_flags))
    check("auth_required_false", all(decision.get(key) is False for key in false_flags))
    check("auth_model_policy", auth.get("model_policy") == EXPECTED_MODEL_POLICY)

    check("dispatch_parent", str(dispatch.get("runner_checkpoint", "")).casefold() == parent)
    check("dispatch_model_policy", dispatch.get("model_policy") == EXPECTED_MODEL_POLICY)
    check("dispatch_execution_authorized", dispatch.get("execution_authorized") is True)
    confirmation = dispatch.get("exact_command_confirmation", {})
    check("dispatch_confirmation_pending", confirmation.get("required_before_process_launch") is True and confirmation.get("state_at_packet_creation") == "PENDING_USER_CONFIRMATION")
    binding = dispatch.get("execution_binding", {})
    check("dispatch_working_directory", binding.get("working_directory") == str(repo))
    check("dispatch_output_root", binding.get("output_root") == str((repo / OUTPUT).resolve()))
    check("dispatch_output_files", binding.get("expected_output_files") == EXPECTED_OUTPUT_FILES)
    expected_dispatch_argv = [
        str(PYTHON), RUNNER.as_posix(), "--repo-root", str(repo),
        "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    check("dispatch_argv", binding.get("argv") == expected_dispatch_argv, binding.get("argv"))
    check("dispatch_one_execution", binding.get("execution_attempts_maximum") == 1 and binding.get("automatic_retry_count") == 0)
    check("dispatch_transitions", binding.get("docker_desktop_start_attempts_maximum") == 1 and binding.get("docker_desktop_stop_attempts_exactly_after_any_start") == 1 and binding.get("wsl_shutdown_attempts_exactly_after_stop") == 1)
    check("dispatch_snapshots", binding.get("closure_snapshots_required") == 3 and binding.get("post_shutdown_settling_seconds") == 20 and binding.get("snapshot_barrier_seconds") == 15)
    interpreter = dispatch.get("interpreter", {})
    check("dispatch_interpreter", interpreter.get("path") == str(PYTHON) and interpreter.get("version") == "3.11.9")
    audit_binding = dispatch.get("audit_binding", {})
    check("dispatch_audit_binding_path", audit_binding.get("path") == AUDIT_RECEIPT.as_posix())
    check("dispatch_audit_binding_verdict", audit_binding.get("verdict") == audit.get("verdict"))
    check("dispatch_audit_binding_blob", blob_fact(repo, head, AUDIT_RECEIPT) == (audit_binding.get("git_blob_bytes"), audit_binding.get("git_blob_sha256")))

    frozen_rows = dispatch.get("frozen_artifacts")
    frozen_map = {
        Path(str(row.get("path"))): row
        for row in frozen_rows or [] if isinstance(row, dict)
    }
    check("frozen_exact_set", set(frozen_map) == EXPECTED_FROZEN, sorted(path.as_posix() for path in frozen_map))
    for relative, row in frozen_map.items():
        check(
            f"frozen_blob:{relative.name}",
            blob_fact(repo, head, relative)
            == (row.get("git_blob_bytes"), row.get("git_blob_sha256")),
        )

    expected_command = [
        str(PYTHON.resolve()), str((repo / RUNNER).resolve()),
        "--repo-root", str(repo), "--expected-head", head,
    ]
    failures = [row for row in checks if not row["pass"]]
    verdict = (
        "PASS_PC2W_P1_ATTEMPT005_DISPATCH_READY_FOR_EXACT_COMMAND_CONFIRMATION"
        if not failures else "FAIL_CLOSED_PC2W_P1_ATTEMPT005_DISPATCH_INVALID"
    )
    print(json.dumps({
        "verdict": verdict,
        "head": head,
        "parent": parent,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
        "output_root_absent": not (repo / OUTPUT).exists(),
        "exact_command": expected_command,
        "execution_performed": False,
    }, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
