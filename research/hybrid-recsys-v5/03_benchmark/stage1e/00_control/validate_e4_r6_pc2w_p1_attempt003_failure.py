#!/usr/bin/env python3
"""Validate the sealed attempt-003 query-only fail-closed packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
STATE = CONTROL / "pipeline_state_stage1e.json"
RECEIPT = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_failure_receipt.json"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt003_failure.py"
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003"
)
OUTPUTS = {
    "command_receipts.json": (27853, "2fca9d80e993aabe97667b56cf0b11af337ee8e7c9c8c37da14a0ae8dc92fd7a"),
    "p1_execution_receipt.json": (5281, "d07348c82af6ed71ebf6943cad23c04696eb73c536b6df876581e69252b7378d"),
    "p1_handoff.json": (1207, "46ab58f5f0002c4ccb7f5192bdce5526d08c5d88a724a9d3e4d51fb1fdaad247"),
    "runtime_inventory.json": (19667, "b112e9a809117b4f22994f86edcade82868b36223c9207edad0eb4112b95fa2a"),
}
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
PACKET_COMMIT = "65b0e50716d4c53d220f917baa316f743e012167"
EXECUTION_COMMIT = "a61f1b9ff9f27dca439a74885b2ea5c7da352f16"


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


def strict_json_bytes(data: bytes) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError("JSON root is not object")
    return value


def load_json(path: Path) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob(repo: Path, commit: str, relative: Path) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative.as_posix()}"], cwd=repo,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, check=True,
    ).stdout


def delta(repo: Path, commit: str) -> set[str]:
    return set(filter(None, git(
        repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit
    ).splitlines()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    checks: list[dict[str, Any]] = []

    def check(name: str, value: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(value), "detail": detail})

    head = git(repo, "rev-parse", "HEAD").casefold()
    expected = args.expected_head.casefold()
    check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected)))
    check("exact_head", head == expected, head)
    check("repo_root", Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo)
    check("worktree_clean", not git(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    check("final_validation_delta", delta(repo, head) == {STATE.as_posix(), RECEIPT.as_posix(), VALIDATOR.as_posix()}, sorted(delta(repo, head)))
    parent = git(repo, "rev-parse", "HEAD^").casefold()
    check("packet_parent", parent == PACKET_COMMIT, parent)
    check("packet_execution_parent", git(repo, "rev-parse", f"{PACKET_COMMIT}^").casefold() == EXECUTION_COMMIT)
    expected_packet_delta = {(OUTPUT_ROOT / name).as_posix() for name in OUTPUTS}
    check("packet_exact_four_files", delta(repo, PACKET_COMMIT) == expected_packet_delta, sorted(delta(repo, PACKET_COMMIT)))

    packet: dict[str, dict[str, Any]] = {}
    for name, expected_fact in OUTPUTS.items():
        relative = OUTPUT_ROOT / name
        data = blob(repo, PACKET_COMMIT, relative)
        check(f"blob_fact:{name}", (len(data), sha256(data)) == expected_fact, (len(data), sha256(data)))
        try:
            packet[name] = strict_json_bytes(data)
            check(f"strict_json:{name}", True)
        except Exception as exc:
            check(f"strict_json:{name}", False, type(exc).__name__)

    command_doc = packet.get("command_receipts.json", {})
    execution = packet.get("p1_execution_receipt.json", {})
    handoff = packet.get("p1_handoff.json", {})
    inventory = packet.get("runtime_inventory.json", {})
    commands = command_doc.get("commands", [])
    command_ids = [row.get("command_id") for row in commands if isinstance(row, dict)]
    check("command_count_29", len(commands) == 29)
    check("exact_command_sequence", command_ids == EXPECTED_COMMAND_IDS)
    check("command_ids_unique", len(set(command_ids)) == len(command_ids))
    check("zero_retry_commands", command_doc.get("automatic_retry_count") == 0)
    check("raw_output_not_persisted", command_doc.get("raw_stdout_or_stderr_persisted") is False)
    check("no_timeout", all(row.get("timed_out") is False for row in commands))
    check("no_spawn_exception", all(row.get("spawn_exception_type") is None for row in commands))
    nonzero = {row.get("command_id"): row.get("exit_code") for row in commands if row.get("exit_code") != 0}
    check("only_advisory_status_nonzero", nonzero == {
        "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE": 1,
        "A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER": 1,
    }, nonzero)
    check("start_once_success", command_ids.count("A07_DOCKER_DESKTOP_START_ONCE") == 1 and next(row for row in commands if row.get("command_id") == "A07_DOCKER_DESKTOP_START_ONCE").get("exit_code") == 0)
    check("stop_once_success", command_ids.count("A21_DOCKER_DESKTOP_STOP_ONCE") == 1 and next(row for row in commands if row.get("command_id") == "A21_DOCKER_DESKTOP_STOP_ONCE").get("exit_code") == 0)

    check("execution_verdict", execution.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT003_BACKEND_OR_POLICY_NOT_ADMISSIBLE")
    check("handoff_verdict", handoff.get("verdict") == execution.get("verdict"))
    check("handoff_no_retry_gate", handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY")
    check("one_start_one_stop", execution.get("startup_attempts") == 1 and execution.get("stop_attempts") == 1)
    check("execution_zero_retry", execution.get("query_retry_count") == 0)
    check("pre_gate_all_pass", all(execution.get("pre_start_gate", {}).values()))
    conditions = execution.get("pass_conditions", {})
    failed_conditions = {key for key, value in conditions.items() if value is not True}
    check("exact_failed_conditions", failed_conditions == {"post_stop_native_closure_all_pass", "prohibited_commands_issued"}, sorted(failed_conditions))
    check("query_evidence_pass", all(conditions.get(key) is True for key in (
        "startup_command_success", "during_docker_desktop_distro_exactly_running",
        "all_query_commands_success", "backend_linux_amd64_desktop_linux",
        "runtime_identities_complete", "parse_failures_absent", "containers_running_zero",
        "container_inventory_unchanged", "image_inventory_unchanged",
        "container_or_image_events_absent", "stop_command_success",
    )))
    closure = execution.get("post_stop_native_closure", {})
    check("closure_snapshots_fail", closure.get("snapshot_a_all_native_lanes") is False and closure.get("snapshot_b_all_native_lanes") is False)
    check("closure_stable_and_wsl_restored", all(closure.get(key) is True for key in (
        "wsl_inventory_stable", "wsl_running_inventory_stable",
        "runtime_process_inventory_stable", "named_pipe_absence_stable",
        "wsl_inventory_restored_to_pre_start",
    )))
    gate = inventory.get("native_gate", {})
    lanes_a = gate.get("post_stop_snapshot_a_lanes", {})
    lanes_b = gate.get("post_stop_snapshot_b_lanes", {})
    expected_lane_failure = {"target_runtime_process_inventory_empty"}
    check("snapshot_a_exact_lane_failure", {key for key, value in lanes_a.items() if value is not True} == expected_lane_failure)
    check("snapshot_b_exact_lane_failure", {key for key, value in lanes_b.items() if value is not True} == expected_lane_failure)
    check("residual_wslrelay_both_snapshots", gate.get("post_stop_runtime_processes_a") == ["wslrelay"] and gate.get("post_stop_runtime_processes_b") == ["wslrelay"])
    status = inventory.get("docker_desktop_status_advisory_only", {})
    check("status_advisory_no_authority", status.get("admission_authority") is False and status.get("cannot_veto_or_admit_native_gate") is True)
    check("parse_failures_absent", inventory.get("parse_failures") == [])
    check("raw_context_not_persisted", inventory.get("raw_context_persisted") is False)
    check("proxy_values_not_persisted", inventory.get("proxy_values_persisted") is False)

    for key in (
        "image_pull_or_build_performed", "container_create_or_run_performed",
        "docker_or_wsl_settings_changed", "source_data_or_checkpoint_download_performed",
        "materialization_performed", "scientific_execution_performed",
    ):
        check(f"execution_false:{key}", execution.get(key) is False)
    check("truth_not_run", execution.get("result_status") == "NOT_RUN")
    check("truth_test_no", execution.get("test_set_opened") == "NO")
    check("truth_rows_zero", execution.get("accepted_result_rows") == 0)

    receipt = load_json(repo / RECEIPT)
    state = load_json(repo / STATE)
    check("failure_receipt_schema", receipt.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt003-failure-receipt-1.0")
    check("failure_receipt_packet", receipt.get("packet_commit") == PACKET_COMMIT)
    check("failure_receipt_output_facts", {
        Path(row.get("path", "")).name: (row.get("git_blob_bytes"), row.get("git_blob_sha256"))
        for row in receipt.get("output_facts", [])
    } == OUTPUTS)
    check("failure_receipt_primary_class", receipt.get("failure_analysis", {}).get("primary_failure_class") == "POST_STOP_RUNTIME_PROCESS_RESIDUAL_WSLRELAY")
    check("failure_receipt_runner_bug", receipt.get("failure_analysis", {}).get("secondary_runner_defect") == "PROHIBITED_COMMAND_CONDITION_POLARITY_BUG_NON_CAUSAL_TO_FINAL_FAILURE")
    check("failure_receipt_no_retry", receipt.get("next_gate") == "FRESH_INDEPENDENT_SOL_XHIGH_STANDARD_FAILURE_PACKET_AUDIT_NO_RETRY")
    check("state_root_status", state.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt003_fail_closed_packet_validation_pending")
    check("state_truth", state.get("result_status") == "NOT_RUN" and state.get("test_set_opened") == "NO")
    check("state_next_gate", state.get("next_gate", "").startswith("Attempt-003 executed exactly once and failed closed"))

    failures = [row for row in checks if not row["pass"]]
    verdict = "PASS_PC2W_P1_ATTEMPT003_FAIL_CLOSED_PACKET_VALIDATED" if not failures else "REWORK_REQUIRED"
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
