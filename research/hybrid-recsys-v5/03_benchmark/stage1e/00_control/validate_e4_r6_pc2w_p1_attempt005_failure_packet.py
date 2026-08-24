#!/usr/bin/env python3
"""Validate the sealed Attempt-005 instrumented fail-closed packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt005_failure_packet.py"
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_an/"
    "E4_R6PC2W_P1_attempt005_instrumented"
)
OUTPUTS = {
    "command_receipts.json": (
        40300,
        "30b12f0333405858744c4b1e4415d862722ab457983f7cb58434315d54b61412",
    ),
    "p1_execution_receipt.json": (
        5703,
        "8b385729d2cb3df65ff9d3ab575a498894eed91eb2ecbecb51d718a88432a8d4",
    ),
    "p1_handoff.json": (
        1229,
        "76862e10c5d438e06107c23faa48f99ba3407d88d7cf86bbb106e0105fc46fc4",
    ),
    "runtime_inventory.json": (
        8549,
        "0d35fd00ad6b6c5399443fa59dcc5e90700afa2861b35bd46a514a2f551108ef",
    ),
}
PRE_GATE_COMMAND_IDS = [
    "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE",
    "A01_WSL_LIST_VERBOSE_PRE_GATE",
    "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE",
    "A03_TARGET_PROCESS_IDENTITY_PRE_GATE",
    "A04_TARGET_TCP_OWNERSHIP_PRE_GATE",
    "A05_WSL_VERSION_IDENTITY",
    "A06_WINDOWS_IDENTITY",
    "A07_DOCKER_DESKTOP_FILE_IDENTITY",
]
POST_COMMAND_IDS = [
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
EXPECTED_COMMAND_IDS = PRE_GATE_COMMAND_IDS + POST_COMMAND_IDS
PACKET_COMMIT = "92e240c"
EXECUTION_COMMIT = "bb4fe8d8bded1501c567a10664265093abbeb79d"
RUNNER_COMMIT = "f511e27eaafae29a5008b9f41ed574fecbeac8a1"
EXPECTED_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT005_CURRENT_HOST_NOT_ADMISSIBLE"


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


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
    packet_commit = git(repo, "rev-parse", PACKET_COMMIT).casefold()
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
    check("validator_parent_is_packet", git(repo, "rev-parse", "HEAD^").casefold() == packet_commit)
    check("packet_execution_parent", git(repo, "rev-parse", f"{packet_commit}^").casefold() == EXECUTION_COMMIT)
    check("execution_runner_parent", git(repo, "rev-parse", f"{EXECUTION_COMMIT}^").casefold() == RUNNER_COMMIT)
    expected_packet_delta = {(OUTPUT_ROOT / name).as_posix() for name in OUTPUTS}
    check("packet_exact_four_files", delta(repo, packet_commit) == expected_packet_delta, sorted(delta(repo, packet_commit)))

    packet: dict[str, dict[str, Any]] = {}
    for name, expected_fact in OUTPUTS.items():
        relative = OUTPUT_ROOT / name
        data = blob(repo, packet_commit, relative)
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
    by_id = {row.get("command_id"): row for row in commands if isinstance(row, dict)}

    check("command_count_21", len(commands) == 21)
    check("pre_gate_then_observation_only_sequence", command_ids == EXPECTED_COMMAND_IDS, command_ids)
    check("command_ids_field_matches", command_doc.get("command_ids") == command_ids)
    check("command_ids_unique", len(set(command_ids)) == len(command_ids))
    check("full_success_sequence_not_claimed", command_doc.get("exact_command_sequence") is False)
    check("named_pipe_probes_are_read_only_non_commands", command_doc.get("named_pipe_probes_are_non_command_read_only_probes") is True)
    check("zero_automatic_retry", command_doc.get("automatic_retry_count") == 0)
    check("all_commands_zero_exit", all(row.get("exit_code") == 0 for row in commands))
    check("no_timeout", all(row.get("timed_out") is False for row in commands))
    check("no_spawn_exception", all(row.get("spawn_exception_type") is None for row in commands))
    check("raw_output_not_persisted", command_doc.get("raw_stdout_or_stderr_persisted") is False)
    check("raw_process_or_command_line_not_persisted", command_doc.get("raw_process_paths_or_command_lines_persisted") is False)
    check("raw_network_addresses_not_persisted", command_doc.get("raw_network_addresses_persisted") is False)

    runtime_mutation_ids = {
        f"A{number:02d}" for number in range(8, 24)
    }
    check(
        "no_start_query_stop_shutdown_commands",
        not any(any(command_id.startswith(prefix + "_") for prefix in runtime_mutation_ids) for command_id in command_ids),
    )
    check(
        "recorded_settling_and_barriers",
        execution.get("post_shutdown_settling_seconds") == 20
        and execution.get("snapshot_barrier_seconds") == 15,
    )
    try:
        gap_settle = (parse_time(by_id["A25_WSL_LIST_VERBOSE_POST_A"]["started_at"]) - parse_time(by_id["A24_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER"]["ended_at"])).total_seconds()
        gap_ab = (parse_time(by_id["A29_WSL_LIST_VERBOSE_POST_B"]["started_at"]) - parse_time(by_id["A28_TARGET_TCP_OWNERSHIP_POST_A"]["ended_at"])).total_seconds()
        gap_bc = (parse_time(by_id["A33_WSL_LIST_VERBOSE_POST_C"]["started_at"]) - parse_time(by_id["A32_TARGET_TCP_OWNERSHIP_POST_B"]["ended_at"])).total_seconds()
        check("timing_barriers_observed", gap_settle >= 19.0 and gap_ab >= 14.0 and gap_bc >= 14.0, [gap_settle, gap_ab, gap_bc])
    except Exception as exc:
        check("timing_barriers_observed", False, type(exc).__name__)

    check("execution_stage", execution.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT005")
    check("execution_entry", execution.get("entry_checkpoint") == EXECUTION_COMMIT)
    check("execution_runner", execution.get("runner_checkpoint") == RUNNER_COMMIT)
    check("execution_verdict", execution.get("verdict") == EXPECTED_VERDICT)
    check("handoff_verdict", handoff.get("verdict") == EXPECTED_VERDICT)
    check("handoff_no_retry_gate", handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY")
    check(
        "no_runtime_transition_attempted",
        execution.get("startup_attempts") == 0
        and execution.get("docker_stop_attempts") == 0
        and execution.get("wsl_shutdown_attempts") == 0,
    )
    check("three_closure_snapshots", execution.get("closure_snapshots") == 3)
    check("execution_zero_retry", execution.get("automatic_retry_count") == 0)

    pre_lanes = inventory.get("pre_start", {}).get("lanes", {})
    expected_failed_pre_lanes = {
        "wsl_verbose_all_stopped",
        "docker_desktop_distro_exactly_stopped",
        "wsl_running_inventory_empty",
        "desktop_linux_named_pipe_absent_win32_error_2",
        "target_process_population_empty",
        "parse_failures_absent",
    }
    check(
        "pre_gate_exact_failures",
        {key for key, value in pre_lanes.items() if value is not True} == expected_failed_pre_lanes,
        sorted(key for key, value in pre_lanes.items() if value is not True),
    )
    check("pre_gate_blocks_start", execution.get("pass_conditions", {}).get("pre_start_gate_all_pass") is False)
    check("pre_start_docker_desktop_running", inventory.get("pre_start", {}).get("running_inventory") == ["docker-desktop"])
    check("pre_start_named_pipe_available", inventory.get("pre_start", {}).get("named_pipe_probe", {}).get("available") is True)

    expected_parse_failures = [
        "A03_TARGET_PROCESS_IDENTITY_PRE_GATE:ValueError",
        "A27_TARGET_PROCESS_IDENTITY_POST_A:ValueError",
        "A31_TARGET_PROCESS_IDENTITY_POST_B:ValueError",
        "A35_TARGET_PROCESS_IDENTITY_POST_C:ValueError",
    ]
    check("exact_parse_failures", inventory.get("parse_failures") == expected_parse_failures, inventory.get("parse_failures"))
    snapshots = inventory.get("post_shutdown_snapshots", [])
    check("snapshot_labels_abc", [row.get("label") for row in snapshots] == ["A", "B", "C"])
    check("snapshots_fail_closed", all(row.get("all_lanes_pass") is False for row in snapshots))
    check("closure_not_promoted", inventory.get("closure_stable") is False)
    check("raw_context_not_persisted", inventory.get("raw_context_persisted") is False)
    check("proxy_values_not_persisted", inventory.get("proxy_values_persisted") is False)

    for key in (
        "force_kill_performed",
        "service_restart_performed",
        "settings_changed",
        "image_pull_or_build_performed",
        "container_create_or_run_performed",
        "install_or_download_performed",
        "materialization_performed",
        "scientific_execution_performed",
    ):
        check(f"execution_false:{key}", execution.get(key) is False)
    check("truth_not_run", execution.get("result_status") == "NOT_RUN")
    check("truth_test_no", execution.get("test_set_opened") == "NO")
    check("truth_rows_zero", execution.get("accepted_result_rows") == 0)
    check("passport_unverified", execution.get("material_passport", {}).get("verification_status") == "UNVERIFIED")

    failures = [row for row in checks if not row["pass"]]
    verdict = (
        "PASS_PC2W_P1_ATTEMPT005_FAIL_CLOSED_PACKET_READY_FOR_FRESH_AUDIT"
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
