#!/usr/bin/env python3
"""Validate the sealed attempt-003 offline-equivalent observation failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
AUDIT_REPO = CONTROL.parents[4]
ROOT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-offline-equivalent-observation"
)
ROOT = AUDIT_REPO / ROOT_RELATIVE
RUNNER_CHECKPOINT = "36353894d67f9b6c94f1377362fc66fa9c4c3a9b"
EXECUTION_CHECKPOINT = "e83dfbdd6e9aea8ba2baf9e9a87f6166e4e6f9b2"
SEALED_PACKET_COMMIT = "da2d495fe9bdedf84176ede7f63e031141f5cc6c"
VALIDATION_V1_COMMIT = "59e6f0bcf7efef241819756b55d145edeacd6b21"
EXPECTED_VALIDATION_PARENT = VALIDATION_V1_COMMIT
EXPECTED_VALIDATION_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_offline_equivalent_failure.py",
}
EXPECTED_VALIDATION_V1_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_offline_equivalent_failure.py",
}
EXPECTED_PACKET_CHANGES = {
    f"{ROOT_RELATIVE.as_posix()}/observation_command_receipts.json",
    f"{ROOT_RELATIVE.as_posix()}/observation_handoff.json",
    f"{ROOT_RELATIVE.as_posix()}/offline_equivalent_observation_receipt.json",
}
EXPECTED_FILES = {
    "observation_command_receipts.json",
    "observation_handoff.json",
    "offline_equivalent_observation_receipt.json",
}
EXPECTED_COMMANDS = [
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY",
    "O01A_WSL_LIST_VERBOSE",
    "O02A_WSL_LIST_RUNNING_QUIET",
    "O03A_DAEMON_VERSION_SERVER_ONLY",
    "O04A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY",
    "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER",
    "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER",
    "O03B_DAEMON_VERSION_SERVER_ONLY_STABILITY_BARRIER",
    "O04B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER",
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=AUDIT_REPO, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(revision: str, relative: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative}"], cwd=AUDIT_REPO,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, shell=False,
    )
    return len(completed.stdout), sha256_bytes(completed.stdout)


def changed_paths(revision: str) -> set[str]:
    return set(filter(None, git("diff-tree", "--no-commit-id", "--name-only", "-r", revision).splitlines()))


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


parser = argparse.ArgumentParser()
parser.add_argument("--expected-head", required=True)
args = parser.parse_args()
expected_head = str(args.expected_head).casefold()

try:
    entries = list(ROOT.iterdir())
    commands = load(ROOT / "observation_command_receipts.json")
    observation = load(ROOT / "offline_equivalent_observation_receipt.json")
    handoff = load(ROOT / "observation_handoff.json")
    validation = load(CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_receipt.json")
    pipeline = load(CONTROL / "pipeline_state_stage1e.json")
    dispatch = load(CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json")
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

head = git("rev-parse", "HEAD").casefold()
parent = git("rev-parse", "HEAD^").casefold()
check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), expected_head)
check("head_exact", head == expected_head, head)
check("parent_exact", parent == EXPECTED_VALIDATION_PARENT, parent)
check("worktree_clean", git("status", "--porcelain=v1", "--untracked-files=all") == "", git("status", "--porcelain=v1", "--untracked-files=all"))
check("validation_exact_changes", changed_paths(expected_head) == EXPECTED_VALIDATION_CHANGES, sorted(changed_paths(expected_head)))
check("validation_v1_parent", git("rev-parse", f"{VALIDATION_V1_COMMIT}^").casefold() == SEALED_PACKET_COMMIT, git("rev-parse", f"{VALIDATION_V1_COMMIT}^"))
check("validation_v1_exact_changes", changed_paths(VALIDATION_V1_COMMIT) == EXPECTED_VALIDATION_V1_CHANGES, sorted(changed_paths(VALIDATION_V1_COMMIT)))
check("packet_parent", git("rev-parse", f"{SEALED_PACKET_COMMIT}^").casefold() == EXECUTION_CHECKPOINT, git("rev-parse", f"{SEALED_PACKET_COMMIT}^"))
check("packet_exact_changes", changed_paths(SEALED_PACKET_COMMIT) == EXPECTED_PACKET_CHANGES, sorted(changed_paths(SEALED_PACKET_COMMIT)))
check("execution_parent", git("rev-parse", f"{EXECUTION_CHECKPOINT}^").casefold() == RUNNER_CHECKPOINT, git("rev-parse", f"{EXECUTION_CHECKPOINT}^"))

check("exact_files", {path.name for path in entries} == EXPECTED_FILES and all(path.is_file() for path in entries), sorted(path.name for path in entries))
check("schemas", commands.get("schema_version", "").endswith("offline-equivalent-command-receipts-4.0") and observation.get("schema_version", "").endswith("offline-equivalent-observation-receipt-4.0") and handoff.get("schema_version", "").endswith("offline-equivalent-handoff-4.0"), None)
passports = [doc.get("material_passport") for doc in (commands, observation, handoff)]
check("shared_passport", all(item == passports[0] for item in passports), passports)
passport = passports[0] if isinstance(passports[0], dict) else {}
check("execution_passport", passport.get("origin_skill") == "experiment-agent" and passport.get("origin_mode") == "run" and passport.get("verification_status") == "UNVERIFIED" and passport.get("version_label") == "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_v4" and passport.get("repro_lock") is None, passport)
check("execution_dependencies", passport.get("upstream_dependencies") == ["stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization_v4", "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_contract_v4", "stage1e_e4_r6_pc2w_p1_attempt003_baseline_validation_v1"], passport.get("upstream_dependencies"))

rows = commands.get("commands", [])
ids = [row.get("command_id") for row in rows if isinstance(row, dict)]
check("exact_commands", ids == EXPECTED_COMMANDS, ids)
check("zero_retry", commands.get("automatic_retry_count") == 0 and observation.get("automatic_retry_count") == 0, None)
check("all_completed_no_timeout", all(row.get("timed_out") is False and row.get("spawn_exception_type") is None for row in rows), rows)
exit_by_id = {row.get("command_id"): row.get("exit_code") for row in rows}
check("expected_exit_codes", exit_by_id == {
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY": 1,
    "O01A_WSL_LIST_VERBOSE": 0,
    "O02A_WSL_LIST_RUNNING_QUIET": 0,
    "O03A_DAEMON_VERSION_SERVER_ONLY": 1,
    "O04A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY": 0,
    "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER": 0,
    "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER": 0,
    "O03B_DAEMON_VERSION_SERVER_ONLY_STABILITY_BARRIER": 1,
    "O04B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER": 0,
}, exit_by_id)
check("hash_only_outputs", all("stdout" not in row and "stderr" not in row and isinstance(row.get("stdout_sha256"), str) and isinstance(row.get("stderr_sha256"), str) for row in rows) and commands.get("raw_stdout_or_stderr_persisted") is False, None)
check("no_state_mutation_argv", all(not any(str(token).casefold() in {"start", "stop", "shutdown", "terminate", "run", "create", "pull", "build"} for token in row.get("argv", [])[1:]) for row in rows), ids)

check("entry_binding", observation.get("entry_checkpoint") == EXECUTION_CHECKPOINT and observation.get("runner_checkpoint") == RUNNER_CHECKPOINT, [observation.get("entry_checkpoint"), observation.get("runner_checkpoint")])
check("status_advisory_fail_closed", observation.get("docker_desktop_status_lane") == {"classification": "RUNNING_EXACT", "advisory_only": True, "unclassified_nonzero_is_not_relabelled_stopped": True, "admissible_without_independent_lanes": False}, observation.get("docker_desktop_status_lane"))
for key in ("snapshot_a", "snapshot_b_stability_barrier"):
    snapshot = observation.get(key, {})
    lanes = snapshot.get("lanes_pass", {})
    check(f"{key}:wsl_stopped", snapshot.get("wsl_inventory", {}).get("parse_complete") is True and snapshot.get("wsl_inventory", {}).get("rows") == [{"name": "docker-desktop", "state": "Stopped", "version": 2}] and snapshot.get("wsl_inventory", {}).get("docker_desktop_state") == "Stopped", snapshot.get("wsl_inventory"))
    check(f"{key}:running_empty", snapshot.get("wsl_running_inventory") == {"parse_complete": True, "running_names": []}, snapshot.get("wsl_running_inventory"))
    check(f"{key}:process_empty", snapshot.get("runtime_process_inventory") == {"parse_complete": True, "runtime_processes": []}, snapshot.get("runtime_process_inventory"))
    check(f"{key}:pipe_absent", snapshot.get("desktop_linux_named_pipe_probe", {}).get("available") is False and snapshot.get("desktop_linux_named_pipe_probe", {}).get("win32_error") == 2 and snapshot.get("desktop_linux_named_pipe_probe", {}).get("timeout_milliseconds") == 1, snapshot.get("desktop_linux_named_pipe_probe"))
    check(f"{key}:daemon_not_specifically_unavailable", snapshot.get("daemon_cli_specifically_unavailable") is False and lanes.get("daemon_cli_specifically_unavailable") is False, [snapshot.get("daemon_cli_specifically_unavailable"), lanes])
    check(f"{key}:other_lanes_pass", lanes.get("wsl_inventory_all_stopped") is True and lanes.get("wsl_running_inventory_empty") is True and lanes.get("desktop_linux_named_pipe_specifically_absent_win32_error_2") is True and lanes.get("target_runtime_process_inventory_empty") is True, lanes)

independent = observation.get("independent_lanes_pass", {})
check("snapshots_fail_only_conjunctive_gate", independent.get("snapshot_a_all_lanes") is False and independent.get("snapshot_b_all_lanes") is False, independent)
check("snapshots_stable", all(independent.get(key) is True for key in ("wsl_inventory_stable_across_barrier", "running_inventory_stable_across_barrier", "runtime_process_inventory_stable_across_barrier", "named_pipe_absence_stable_across_barrier")), independent)
check("failure_verdict", observation.get("status_lane_admissible") is False and observation.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_BASELINE", observation.get("verdict"))
check("attempt_gate_preserved", observation.get("observation_is_not_sufficient_without_attempt003_immediate_pre_gate_replay") is True and handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY", handoff)

for key in ("state_mutation_command_issued", "image_or_container_mutation_performed", "settings_changed", "install_or_download_performed", "materialization_performed", "scientific_execution_performed"):
    check(f"mutation_false:{key}", observation.get(key) is False, observation.get(key))
check("truth", observation.get("result_status") == "NOT_RUN" and observation.get("test_set_opened") == "NO" and observation.get("accepted_result_rows") == 0 and handoff.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, None)

output_facts = {row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256")) for row in validation.get("output_facts", []) if isinstance(row, dict)}
check("output_fact_count", len(output_facts) == 3, output_facts)
for name in sorted(EXPECTED_FILES):
    relative = f"{ROOT_RELATIVE.as_posix()}/{name}"
    check(f"output_blob:{name}", blob_fact(SEALED_PACKET_COMMIT, relative) == output_facts.get(relative), [blob_fact(SEALED_PACKET_COMMIT, relative), output_facts.get(relative)])

frozen = dispatch.get("frozen_artifacts", [])
check("frozen_count", len(frozen) == 4, len(frozen))
for row in frozen:
    if isinstance(row, dict):
        relative = str(row.get("path"))
        expected = (row.get("git_blob_bytes"), row.get("git_blob_sha256"))
        check(f"frozen_blob:{relative}", blob_fact(EXECUTION_CHECKPOINT, relative) == expected, [blob_fact(EXECUTION_CHECKPOINT, relative), expected])

validation_passport = validation.get("material_passport", {})
check("validation_passport", validation_passport.get("origin_skill") == "experiment-agent" and validation_passport.get("origin_mode") == "validate" and validation_passport.get("verification_status") == "ANALYZED" and validation_passport.get("repro_lock") is None, validation_passport)
validator_record = validation.get("central_validation", {})
validator_relative = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_offline_equivalent_failure.py"
check("validator_blob", blob_fact(expected_head, validator_relative) == (validator_record.get("validator_raw_bytes"), validator_record.get("validator_raw_sha256")), validator_record)
check("validation_claim", validator_record.get("validator_verdict") == "PASS_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_FAILURE_VALIDATED", validator_record)
check("standard_model_policy", validator_record.get("model") == "gpt-5.6-sol" and validator_record.get("reasoning_effort") == "max" and validator_record.get("service_tier") == "default" and validator_record.get("display_name") == "Sol Max Standard", validator_record)
attempt_result = validation.get("attempt_result", {})
check("failure_class", attempt_result.get("failure_class") == "DAEMON_CLI_UNAVAILABLE_NOT_SPECIFICALLY_PROVEN" and attempt_result.get("observation_attempts") == 1 and attempt_result.get("automatic_retry_count") == 0, attempt_result)
check("attempt003_not_opened", attempt_result.get("attempt003_execution_opened") is False and attempt_result.get("attempt003_start_query_stop_executed") is False and attempt_result.get("new_retry_performed") is False, attempt_result)

pc2w = pipeline.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
expected_state = "stage1e_rebaseline_v2_r6_pc2w_p1_attempt003_offline_equivalent_observation_fail_closed_awaiting_user_decision"
check("pipeline_root", pipeline.get("state") == expected_state, pipeline.get("state"))
check("pipeline_status", pipeline.get("rebaseline_v2", {}).get("status") == "e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_fail_closed", pipeline.get("rebaseline_v2", {}).get("status"))
record = pc2w.get("p1_attempt003_offline_equivalent_observation", {})
check("pipeline_nested", pc2w.get("status") == "P1_ATTEMPT003_OFFLINE_EQUIVALENT_OBSERVATION_FAIL_CLOSED_NO_AUTOMATIC_RETRY" and record.get("authorization_consumed") is True and record.get("attempt003_execution_opened") is False, record)
check("pipeline_gate", pc2w.get("next_gate") == "EXPLICIT_USER_DECISION_REQUIRED_FOR_ANY_NEW_ADMISSION_REVISION_OBSERVATION_OR_ATTEMPT_NO_AUTOMATIC_RETRY", pc2w.get("next_gate"))
check("phase_not_complete", pipeline.get("stage") == "1E" and pipeline.get("result_status") == "NOT_RUN" and pipeline.get("test_set_opened") == "NO", None)

failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_FAILURE_VALIDATED" if not failures else "FAIL",
    "expected_head": expected_head,
    "sealed_packet_commit": SEALED_PACKET_COMMIT,
    "execution_checkpoint": EXECUTION_CHECKPOINT,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)
