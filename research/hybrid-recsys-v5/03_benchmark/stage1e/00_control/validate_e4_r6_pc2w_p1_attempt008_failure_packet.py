#!/usr/bin/env python3
"""Validate the immutable Attempt-008 fail-closed observation packet.

This validator is read-only.  It replays packet structure, command identity,
failure locators, cleanup closure, and the still-closed scientific boundary.
It never starts or queries Docker/WSL and never writes an artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
import execute_e4_r6_pc2w_p1_attempt008_admission_observation as runner


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt008_failure_packet.py"
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_aq/"
    "E4_R6PC2W_P1_attempt008_admission_observation"
)
OUTPUT_PACKET_COMMIT = "2dc7bce6ff2d3bcaf0fee33ebf6f50376f1f9261"
OUTPUT_PACKET_PARENT = "1d0806f2849e47357a632cdf468c00f0cc57deac"
OUTPUTS = {
    "admission_observation.json": (
        15698,
        "0fa7f633dd0aa17a1c322c8fc0bb43634ebfc6cc3ff7c89b252b1a267d39ff0f",
    ),
    "command_receipts.json": (
        21503,
        "241e8e1e80dbc5861608beddbff7ae49cd8080e5fe64da62433bd22f986dcd69",
    ),
    "execution_receipt.json": (
        5173,
        "a5baa0494f9cdecc7da2c77321cc8e5ec005b67a56a931c3ae0111b1724ca8c3",
    ),
    "handoff.json": (
        1454,
        "97c1ef778ae4bdf6a32d4dbce993a84da35190def4801d3fb449e54e2399b80a",
    ),
}
EXPECTED_VERDICT = "FAIL_CLOSED_PC2W_P1_ATTEMPT008_CURRENT_HOST_NOT_ADMISSIBLE"
EXPECTED_ERROR_TYPE_HASH = (
    "26d8eb80215ec872c6fb95cbc9432488cb86615cf31728df5394f20abbb723e2"
)
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03", "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]
EXPECTED_IDENTITY_FAILURES = [
    {
        "stage": "D01",
        "code": "PROCESS_PROBE_HASH_EXECUTABLE",
        "field": None,
        "safe_details": {
            "failure_step": "HASH_EXECUTABLE",
            "failure_target": "com.docker.backend",
            "error_type_hash": EXPECTED_ERROR_TYPE_HASH,
        },
    },
    {
        "stage": "D02",
        "code": "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE",
        "field": None,
        "safe_details": {},
    },
    {
        "stage": "DOCKER_IDENTITY",
        "code": "DOCKER_SERVER_FIELD_MISSING",
        "field": None,
        "safe_details": {},
    },
    {
        "stage": "D06",
        "code": "DESKTOP_FILE_PROBE_READ_AUTHENTICODE",
        "field": None,
        "safe_details": {
            "failure_step": "READ_AUTHENTICODE",
            "error_type_hash": EXPECTED_ERROR_TYPE_HASH,
        },
    },
]


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
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    if b"\r" in data:
        raise ValueError("bare or CRLF carriage return in canonical JSON blob")
    value = json.loads(
        data.decode("utf-8", errors="strict"),
        object_pairs_hook=strict_pairs,
        parse_constant=reject_constant,
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


def expected_argv_hash(kind: str) -> str:
    value = runner.build_argv(kind)
    encoded = json.dumps(
        value, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    checks: list[dict[str, Any]] = []

    def check(name: str, value: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(value), "detail": detail})

    expected_head = args.expected_head.casefold()
    head = git(repo, "rev-parse", "HEAD").casefold()
    packet_commit = git(repo, "rev-parse", OUTPUT_PACKET_COMMIT).casefold()
    check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)))
    check("exact_head", head == expected_head, head)
    check(
        "repo_root",
        Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo,
    )
    check(
        "worktree_clean",
        not git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
    )
    check("validator_only_delta", delta(repo, head) == {VALIDATOR.as_posix()})
    check("validator_parent_is_output_packet", git(repo, "rev-parse", "HEAD^").casefold() == packet_commit)
    check("output_packet_parent", git(repo, "rev-parse", f"{packet_commit}^").casefold() == OUTPUT_PACKET_PARENT)
    expected_output_delta = {(OUTPUT_ROOT / name).as_posix() for name in OUTPUTS}
    check("packet_exact_four_files", delta(repo, packet_commit) == expected_output_delta)

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
    observation = packet.get("admission_observation.json", {})
    execution = packet.get("execution_receipt.json", {})
    handoff = packet.get("handoff.json", {})
    commands = command_doc.get("commands", [])
    command_ids = [row.get("command_id") for row in commands if isinstance(row, dict)]

    check("command_count_26", len(commands) == 26)
    check("exact_command_order", command_ids == EXPECTED_COMMAND_IDS, command_ids)
    check("command_ids_field_matches", command_doc.get("command_ids") == command_ids)
    check("exact_command_sequence", command_doc.get("exact_command_sequence") is True)
    check("all_commands_exit_zero", all(row.get("exit_code") == 0 for row in commands))
    check("no_timeout", all(row.get("timed_out") is False for row in commands))
    check("no_spawn_exception", all(row.get("spawn_exception_type_hash") is None for row in commands))
    check(
        "argv_hashes_replay",
        all(
            row.get("argv_sha256") == expected_argv_hash(str(row.get("command_kind")))
            for row in commands
        ),
    )
    check(
        "raw_not_persisted",
        command_doc.get("raw_argv_stdout_stderr_persisted") is False
        and all(row.get("raw_argv_stdout_stderr_persisted") is False for row in commands),
    )
    check("one_start", command_doc.get("docker_desktop_start_attempts") == 1)
    check("one_stop", command_doc.get("docker_desktop_stop_attempts") == 1)
    check("one_shutdown", command_doc.get("wsl_shutdown_attempts") == 1)
    check("zero_retry", command_doc.get("automatic_retry_count") == 0)
    check("zero_fallback", command_doc.get("fallback_count") == 0)

    check("parse_failures_empty", observation.get("parse_failures") == [])
    check("identity_failures_exact", observation.get("identity_failures") == EXPECTED_IDENTITY_FAILURES)
    check("pre_start_all_pass", observation.get("pre_start", {}).get("all_lanes_pass") is True)
    snapshots = observation.get("post_shutdown_snapshots", [])
    check("three_closure_snapshots", len(snapshots) == 3)
    check("all_closure_lanes_pass", all(row.get("all_lanes_pass") is True for row in snapshots))
    check("closure_stable", observation.get("closure_stable") is True)
    check("closure_matches_pre_start", observation.get("final_closure_matches_pre_start") is True)

    pass_conditions = execution.get("pass_conditions", {})
    expected_false = {
        "during_process_identity_complete",
        "during_tcp_identity_complete",
        "docker_client_server_info_identity_complete",
        "docker_client_server_info_cross_consistent",
        "docker_desktop_executable_identity_complete",
        "identity_failures_absent",
    }
    check(
        "exact_failed_pass_conditions",
        {name for name, value in pass_conditions.items() if value is False} == expected_false,
        sorted(name for name, value in pass_conditions.items() if value is False),
    )
    check("producer_verdict", execution.get("verdict") == EXPECTED_VERDICT)
    check("handoff_verdict", handoff.get("verdict") == EXPECTED_VERDICT)
    check(
        "no_unsafe_runtime_remediation",
        all(
            execution.get(field) is False
            for field in (
                "force_kill_performed", "service_restart_performed", "settings_changed",
                "install_or_download_performed", "network_or_web_operation_performed",
                "image_or_container_mutation_performed",
            )
        ),
    )
    check(
        "scientific_boundary_closed",
        execution.get("materialization_performed") is False
        and execution.get("preprocessing_performed") is False
        and execution.get("training_performed") is False
        and execution.get("evaluation_performed") is False
        and execution.get("benchmark_admission_opened") is False
        and execution.get("result_status") == "NOT_RUN"
        and execution.get("test_set_opened") == "NO"
        and execution.get("accepted_result_rows") == 0,
    )
    check(
        "handoff_next_gate",
        handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY",
    )

    failures = [row for row in checks if not row["pass"]]
    print(
        json.dumps(
            {
                "verdict": (
                    "PASS_PC2W_P1_ATTEMPT008_FAIL_CLOSED_PACKET_READY_FOR_FRESH_AUDIT"
                    if not failures
                    else "FAIL_PC2W_P1_ATTEMPT008_FAILURE_PACKET_VALIDATION"
                ),
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
