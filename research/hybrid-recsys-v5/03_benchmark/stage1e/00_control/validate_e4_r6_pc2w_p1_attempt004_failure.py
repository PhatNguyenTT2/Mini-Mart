#!/usr/bin/env python3
"""Validate the final audited Attempt-004 fail-closed receipt and Stage 1E state."""

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
RECEIPT = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt004_failure_receipt.json"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt004_failure.py"
PACKET_VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt004_failure_packet.py"
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
PACKET_COMMIT = "6f09ccfea5701f9d99caf040abd54644882d1eff"
EXECUTION_COMMIT = "c6bf15298b00b65ba797706a0911e21d72f39d39"
RUNNER_COMMIT = "f30caeace4cb8f7baca8abfe4a9bef3357fa7194"
AUDIT_VALIDATION_COMMIT = "3832b2f786cc21a288926b538a4ae2e992c9d64a"


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


def load_json(path: Path) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes())


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
    parent = git(repo, "rev-parse", "HEAD^").casefold()
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
    expected_final_delta = {STATE.as_posix(), RECEIPT.as_posix(), VALIDATOR.as_posix()}
    check(
        "final_exact_three_file_delta",
        delta(repo, head) == expected_final_delta,
        sorted(delta(repo, head)),
    )
    check("audit_validation_parent", parent == AUDIT_VALIDATION_COMMIT, parent)
    check(
        "packet_parent_of_audit_validation",
        git(repo, "rev-parse", f"{AUDIT_VALIDATION_COMMIT}^").casefold()
        == PACKET_COMMIT,
    )
    check(
        "packet_execution_parent",
        git(repo, "rev-parse", f"{PACKET_COMMIT}^").casefold()
        == EXECUTION_COMMIT,
    )
    check(
        "execution_runner_parent",
        git(repo, "rev-parse", f"{EXECUTION_COMMIT}^").casefold()
        == RUNNER_COMMIT,
    )
    check(
        "audit_validation_exact_validator_delta",
        delta(repo, AUDIT_VALIDATION_COMMIT) == {PACKET_VALIDATOR.as_posix()},
        sorted(delta(repo, AUDIT_VALIDATION_COMMIT)),
    )
    expected_packet_delta = {(OUTPUT_ROOT / name).as_posix() for name in OUTPUTS}
    check(
        "packet_exact_four_files",
        delta(repo, PACKET_COMMIT) == expected_packet_delta,
        sorted(delta(repo, PACKET_COMMIT)),
    )

    packet: dict[str, dict[str, Any]] = {}
    for name, expected_fact in OUTPUTS.items():
        data = blob(repo, PACKET_COMMIT, OUTPUT_ROOT / name)
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
    check("command_ids_unique", len(set(command_ids)) == 29)
    check("one_start", command_ids.count("A07_DOCKER_DESKTOP_START_ONCE") == 1)
    check("one_stop", command_ids.count("A21_DOCKER_DESKTOP_STOP_ONCE") == 1)
    check("zero_retry", command_doc.get("automatic_retry_count") == 0)
    check(
        "sealed_failure_verdict",
        execution.get("verdict")
        == "FAIL_CLOSED_PC2W_P1_ATTEMPT004_BACKEND_OR_POLICY_NOT_ADMISSIBLE",
    )
    check("handoff_matches_execution", handoff.get("verdict") == execution.get("verdict"))
    conditions = execution.get("pass_conditions", {})
    check(
        "exact_failed_condition",
        {key for key, value in conditions.items() if value is not True}
        == {"post_stop_native_closure_all_pass"},
    )
    check("prohibited_commands_absent", conditions.get("prohibited_commands_absent") is True)
    stabilization = execution.get("post_stop_stabilization", {})
    check(
        "fixed_observation_window",
        stabilization.get("settling_seconds") == 20
        and stabilization.get("snapshot_barrier_seconds") == 5
        and stabilization.get("observation_only") is True
        and stabilization.get("mutation_retry_count") == 0,
    )
    gate = inventory.get("native_gate", {})
    check(
        "residual_wslrelay_both_snapshots",
        gate.get("post_stop_runtime_processes_a") == ["wslrelay"]
        and gate.get("post_stop_runtime_processes_b") == ["wslrelay"],
    )
    for suffix in ("a", "b"):
        lanes = gate.get(f"post_stop_snapshot_{suffix}_lanes", {})
        check(
            f"snapshot_{suffix}_exact_lane_failure",
            {key for key, value in lanes.items() if value is not True}
            == {"target_runtime_process_inventory_empty"},
        )
    for key in (
        "image_pull_or_build_performed",
        "container_create_or_run_performed",
        "docker_or_wsl_settings_changed",
        "source_data_or_checkpoint_download_performed",
        "materialization_performed",
        "scientific_execution_performed",
    ):
        check(f"execution_false:{key}", execution.get(key) is False)
    check(
        "sealed_truth",
        execution.get("result_status") == "NOT_RUN"
        and execution.get("test_set_opened") == "NO"
        and execution.get("accepted_result_rows") == 0,
    )

    receipt = load_json(repo / RECEIPT)
    state = load_json(repo / STATE)
    check(
        "failure_receipt_schema",
        receipt.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt004-failure-receipt-1.0",
    )
    validator_bytes = (repo / VALIDATOR).read_bytes()
    check(
        "validator_self_fact",
        (len(validator_bytes), sha256(validator_bytes))
        == (
            receipt.get("central_validation", {}).get("validator_raw_bytes"),
            receipt.get("central_validation", {}).get("validator_raw_sha256"),
        ),
    )
    packet_validator_bytes = blob(repo, AUDIT_VALIDATION_COMMIT, PACKET_VALIDATOR)
    check(
        "packet_validator_fact",
        (len(packet_validator_bytes), sha256(packet_validator_bytes))
        == (
            receipt.get("central_packet_validation", {}).get("validator_raw_bytes"),
            receipt.get("central_packet_validation", {}).get("validator_raw_sha256"),
        ),
    )
    check("receipt_runner", receipt.get("runner_checkpoint") == RUNNER_COMMIT)
    check("receipt_execution", receipt.get("execution_checkpoint") == EXECUTION_COMMIT)
    check("receipt_packet", receipt.get("packet_commit") == PACKET_COMMIT)
    check(
        "receipt_output_facts",
        {
            Path(row.get("path", "")).name: (
                row.get("git_blob_bytes"),
                row.get("git_blob_sha256"),
            )
            for row in receipt.get("output_facts", [])
        }
        == OUTPUTS,
    )
    analysis = receipt.get("failure_analysis", {})
    check(
        "receipt_primary_class",
        analysis.get("primary_failure_class")
        == "POST_STOP_RUNTIME_PROCESS_RESIDUAL_WSLRELAY",
    )
    check(
        "receipt_polarity_repaired",
        analysis.get("secondary_runner_defect")
        == "NONE_POLARITY_REPAIRED_BEFORE_ATTEMPT004",
    )
    audit = receipt.get("fresh_independent_failure_packet_audit", {})
    check(
        "independent_audit_verdict",
        audit.get("verdict")
        == "PASS_PC2W_P1_ATTEMPT004_FAILURE_PACKET_AUDITED_NO_RETRY",
    )
    check("independent_audit_write_set", audit.get("write_set") == [])
    check(
        "independent_audit_standard",
        audit.get("requested_service_tier") == "default"
        and audit.get("fast_or_priority_observed") is False,
    )
    check(
        "receipt_truth",
        receipt.get("truth_state", {}).get("RESULT_STATUS") == "NOT_RUN"
        and receipt.get("truth_state", {}).get("TEST_SET_OPENED") == "NO"
        and receipt.get("truth_state", {}).get("ACCEPTED_RESULT_ROWS") == 0,
    )
    check(
        "receipt_no_retry",
        receipt.get("next_gate")
        == "USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY_AFTER_AUDITED_FAILURE",
    )
    check(
        "state_root_status",
        state.get("state")
        == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt004_fail_closed_packet_audited_no_retry_user_decision_required",
    )
    check(
        "state_truth",
        state.get("result_status") == "NOT_RUN"
        and state.get("test_set_opened") == "NO",
    )
    check(
        "state_next_gate",
        state.get("next_gate", "").startswith(
            "Attempt-004 failure packet passed independent Sol XHigh Standard audit"
        ),
    )

    failures = [row for row in checks if not row["pass"]]
    verdict = (
        "PASS_PC2W_P1_ATTEMPT004_FAIL_CLOSED_PACKET_VALIDATED"
        if not failures
        else "REWORK_REQUIRED"
    )
    print(
        json.dumps(
            {
                "verdict": verdict,
                "head": head,
                "parent": parent,
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
