#!/usr/bin/env python3
"""Validate the sealed Attempt-004 query-only fail-closed packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt004_failure_packet.py"
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-004"
)
OUTPUTS = {
    "command_receipts.json": (
        27853,
        "9dffc35e21970386d312a9ed19778d4dca5d30f5f5e23c69bb59fe20f7aaed6d",
    ),
    "p1_execution_receipt.json": (
        5709,
        "fda12183132f77078c25e2a46008989a6586701084e89337403efab3f8c412f2",
    ),
    "p1_handoff.json": (
        1207,
        "1bf3a13bee187cd061bf679601dcb6536720355b557405a5ae556629da0d9844",
    ),
    "runtime_inventory.json": (
        19666,
        "3095483788ef3b38562660ef5eaf8f15053e426d3097c93bf93a4ad4d6750390",
    ),
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
PACKET_COMMIT = "6f09ccfea5701f9d99caf040abd54644882d1eff"
EXECUTION_COMMIT = "c6bf15298b00b65ba797706a0911e21d72f39d39"
RUNNER_COMMIT = "f30caeace4cb8f7baca8abfe4a9bef3357fa7194"


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
    value = json.loads(
        data.decode("utf-8", errors="strict"), object_pairs_hook=strict_pairs
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root is not object")
    return value


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def blob(repo: Path, commit: str, relative: Path) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative.as_posix()}"],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    ).stdout


def delta(repo: Path, commit: str) -> set[str]:
    return set(
        filter(
            None,
            git(
                repo,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commit,
            ).splitlines(),
        )
    )


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
    check(
        "repo_root",
        Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo,
    )
    check(
        "worktree_clean",
        not git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
    )
    check(
        "validator_only_delta",
        delta(repo, head) == {VALIDATOR.as_posix()},
        sorted(delta(repo, head)),
    )
    check("packet_is_validator_parent", git(repo, "rev-parse", "HEAD^").casefold() == PACKET_COMMIT)
    check(
        "packet_execution_parent",
        git(repo, "rev-parse", f"{PACKET_COMMIT}^").casefold() == EXECUTION_COMMIT,
    )
    check(
        "execution_runner_parent",
        git(repo, "rev-parse", f"{EXECUTION_COMMIT}^").casefold() == RUNNER_COMMIT,
    )
    expected_packet_delta = {(OUTPUT_ROOT / name).as_posix() for name in OUTPUTS}
    check(
        "packet_exact_four_files",
        delta(repo, PACKET_COMMIT) == expected_packet_delta,
        sorted(delta(repo, PACKET_COMMIT)),
    )

    packet: dict[str, dict[str, Any]] = {}
    for name, expected_fact in OUTPUTS.items():
        relative = OUTPUT_ROOT / name
        data = blob(repo, PACKET_COMMIT, relative)
        fact = (len(data), sha256(data))
        check(f"blob_fact:{name}", fact == expected_fact, fact)
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
    check("zero_automatic_retry", command_doc.get("automatic_retry_count") == 0)
    check("raw_output_not_persisted", command_doc.get("raw_stdout_or_stderr_persisted") is False)
    check("no_timeout", all(row.get("timed_out") is False for row in commands))
    check("no_spawn_exception", all(row.get("spawn_exception_type") is None for row in commands))
    nonzero = {
        row.get("command_id"): row.get("exit_code")
        for row in commands
        if row.get("exit_code") != 0
    }
    check(
        "only_advisory_status_nonzero",
        nonzero
        == {
            "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE": 1,
            "A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER": 1,
        },
        nonzero,
    )
    starts = [row for row in commands if row.get("command_id") == "A07_DOCKER_DESKTOP_START_ONCE"]
    stops = [row for row in commands if row.get("command_id") == "A21_DOCKER_DESKTOP_STOP_ONCE"]
    check("start_once_success", len(starts) == 1 and starts[0].get("exit_code") == 0)
    check("stop_once_success", len(stops) == 1 and stops[0].get("exit_code") == 0)

    expected_verdict = "FAIL_CLOSED_PC2W_P1_ATTEMPT004_BACKEND_OR_POLICY_NOT_ADMISSIBLE"
    check("execution_stage", execution.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT004")
    check("execution_entry", execution.get("entry_checkpoint") == EXECUTION_COMMIT)
    check("execution_runner", execution.get("runner_checkpoint") == RUNNER_COMMIT)
    check("execution_verdict", execution.get("verdict") == expected_verdict)
    check("handoff_verdict", handoff.get("verdict") == expected_verdict)
    check(
        "handoff_no_retry_gate",
        handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY",
    )
    check(
        "one_start_one_stop",
        execution.get("startup_attempts") == 1 and execution.get("stop_attempts") == 1,
    )
    check("execution_zero_retry", execution.get("query_retry_count") == 0)
    check("pre_gate_all_pass", all(execution.get("pre_start_gate", {}).values()))

    conditions = execution.get("pass_conditions", {})
    failed_conditions = {key for key, value in conditions.items() if value is not True}
    check(
        "exact_failed_condition",
        failed_conditions == {"post_stop_native_closure_all_pass"},
        sorted(failed_conditions),
    )
    check(
        "query_evidence_pass",
        all(
            conditions.get(key) is True
            for key in (
                "startup_command_success",
                "during_docker_desktop_distro_exactly_running",
                "all_query_commands_success",
                "backend_linux_amd64_desktop_linux",
                "runtime_identities_complete",
                "parse_failures_absent",
                "containers_running_zero",
                "container_inventory_unchanged",
                "image_inventory_unchanged",
                "container_or_image_events_absent",
                "stop_command_success",
                "prohibited_commands_absent",
                "automatic_retry_count_zero",
            )
        ),
    )
    stabilization = execution.get("post_stop_stabilization", {})
    check(
        "fixed_observation_window",
        stabilization.get("settling_seconds") == 20
        and stabilization.get("snapshot_barrier_seconds") == 5
        and stabilization.get("observation_only") is True
        and stabilization.get("mutation_retry_count") == 0,
    )
    closure = execution.get("post_stop_native_closure", {})
    check(
        "closure_snapshots_fail",
        closure.get("snapshot_a_all_native_lanes") is False
        and closure.get("snapshot_b_all_native_lanes") is False,
    )
    check(
        "closure_stable_and_wsl_restored",
        all(
            closure.get(key) is True
            for key in (
                "wsl_inventory_stable",
                "wsl_running_inventory_stable",
                "runtime_process_inventory_stable",
                "named_pipe_absence_stable",
                "wsl_inventory_restored_to_pre_start",
            )
        ),
    )
    gate = inventory.get("native_gate", {})
    lanes_a = gate.get("post_stop_snapshot_a_lanes", {})
    lanes_b = gate.get("post_stop_snapshot_b_lanes", {})
    expected_lane_failure = {"target_runtime_process_inventory_empty"}
    check(
        "snapshot_a_exact_lane_failure",
        {key for key, value in lanes_a.items() if value is not True}
        == expected_lane_failure,
    )
    check(
        "snapshot_b_exact_lane_failure",
        {key for key, value in lanes_b.items() if value is not True}
        == expected_lane_failure,
    )
    check(
        "residual_wslrelay_both_snapshots",
        gate.get("post_stop_runtime_processes_a") == ["wslrelay"]
        and gate.get("post_stop_runtime_processes_b") == ["wslrelay"],
    )
    status = inventory.get("docker_desktop_status_advisory_only", {})
    check(
        "status_advisory_no_authority",
        status.get("admission_authority") is False
        and status.get("cannot_veto_or_admit_native_gate") is True,
    )
    check("parse_failures_absent", inventory.get("parse_failures") == [])
    check("raw_context_not_persisted", inventory.get("raw_context_persisted") is False)
    check("proxy_values_not_persisted", inventory.get("proxy_values_persisted") is False)

    for key in (
        "image_pull_or_build_performed",
        "container_create_or_run_performed",
        "docker_or_wsl_settings_changed",
        "source_data_or_checkpoint_download_performed",
        "materialization_performed",
        "scientific_execution_performed",
    ):
        check(f"execution_false:{key}", execution.get(key) is False)
    check("truth_not_run", execution.get("result_status") == "NOT_RUN")
    check("truth_test_no", execution.get("test_set_opened") == "NO")
    check("truth_rows_zero", execution.get("accepted_result_rows") == 0)

    failures = [row for row in checks if not row["pass"]]
    verdict = (
        "PASS_PC2W_P1_ATTEMPT004_FAIL_CLOSED_PACKET_READY_FOR_FRESH_AUDIT"
        if not failures
        else "REWORK_REQUIRED"
    )
    print(
        json.dumps(
            {
                "verdict": verdict,
                "head": head,
                "parent": git(repo, "rev-parse", "HEAD^").casefold(),
                "checks_passed": len(checks) - len(failures),
                "checks_total": len(checks),
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
