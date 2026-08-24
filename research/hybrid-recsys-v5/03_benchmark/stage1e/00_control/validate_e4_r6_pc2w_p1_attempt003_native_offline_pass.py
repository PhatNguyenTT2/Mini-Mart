#!/usr/bin/env python3
"""Validate the sealed PC2W-P1 attempt-003 native-offline v5 PASS packet."""

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
REPO = CONTROL.parents[4]
ROOT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-native-offline-observation-v5"
)
ROOT = REPO / ROOT_RELATIVE
RUNNER_CHECKPOINT = "be88181f8b7d8986bbe850ecce3c645c781e6827"
EXECUTION_CHECKPOINT = "4d1ed5ece5725812cfcceec4f9d24b2dfe253d85"
PACKET_COMMIT = "cfff2fec05010c3b9969303e434a3c5d2eb48f44"
EXPECTED_PARENT = PACKET_COMMIT
VALIDATOR_RELATIVE = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_native_offline_pass.py"
VALIDATION_RECEIPT_RELATIVE = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_native_offline_validation_receipt.json"
PIPELINE_RELATIVE = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json"
EXPECTED_VALIDATION_CHANGES = {VALIDATOR_RELATIVE, VALIDATION_RECEIPT_RELATIVE, PIPELINE_RELATIVE}
EXPECTED_EXECUTION_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json",
}
EXPECTED_PACKET_FILES = {
    "observation_command_receipts.json",
    "observation_handoff.json",
    "offline_equivalent_observation_receipt.json",
}
EXPECTED_PACKET_CHANGES = {f"{ROOT_RELATIVE.as_posix()}/{name}" for name in EXPECTED_PACKET_FILES}
EXPECTED_COMMANDS = [
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY",
    "O01A_WSL_LIST_VERBOSE",
    "O02A_WSL_LIST_RUNNING_QUIET",
    "O03A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY",
    "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER",
    "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER",
    "O03B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER",
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


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object root: {path}")
    return value


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return result.stdout.decode("utf-8", errors="strict").strip()


def changed(revision: str) -> set[str]:
    return set(filter(None, git("diff-tree", "--no-commit-id", "--name-only", "-r", revision).splitlines()))


def blob_fact(revision: str, path: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{path}"], cwd=REPO,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, check=True,
    )
    return len(result.stdout), sha256(result.stdout)


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


parser = argparse.ArgumentParser()
parser.add_argument("--expected-head", required=True)
args = parser.parse_args()
expected_head = str(args.expected_head).casefold()

try:
    commands = load(ROOT / "observation_command_receipts.json")
    observation = load(ROOT / "offline_equivalent_observation_receipt.json")
    handoff = load(ROOT / "observation_handoff.json")
    validation = load(CONTROL / Path(VALIDATION_RECEIPT_RELATIVE).name)
    pipeline = load(CONTROL / "pipeline_state_stage1e.json")
    dispatch = load(CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json")
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

head = git("rev-parse", "HEAD").casefold()
parent = git("rev-parse", "HEAD^").casefold()
check("expected_head_shape", re.fullmatch(r"[0-9a-f]{40}", expected_head) is not None, expected_head)
check("head_exact", head == expected_head, head)
check("parent_exact", parent == EXPECTED_PARENT, parent)
check("clean", git("status", "--porcelain=v1", "--untracked-files=all") == "", git("status", "--porcelain=v1", "--untracked-files=all"))
check("validation_exact_changes", changed(head) == EXPECTED_VALIDATION_CHANGES, sorted(changed(head)))
check("packet_parent", git("rev-parse", f"{PACKET_COMMIT}^").casefold() == EXECUTION_CHECKPOINT, git("rev-parse", f"{PACKET_COMMIT}^"))
check("packet_exact_changes", changed(PACKET_COMMIT) == EXPECTED_PACKET_CHANGES, sorted(changed(PACKET_COMMIT)))
check("execution_parent", git("rev-parse", f"{EXECUTION_CHECKPOINT}^").casefold() == RUNNER_CHECKPOINT, git("rev-parse", f"{EXECUTION_CHECKPOINT}^"))
check("execution_exact_changes", changed(EXECUTION_CHECKPOINT) == EXPECTED_EXECUTION_CHANGES, sorted(changed(EXECUTION_CHECKPOINT)))
entries = list(ROOT.iterdir())
check("exact_packet_files", {p.name for p in entries} == EXPECTED_PACKET_FILES and all(p.is_file() for p in entries), sorted(p.name for p in entries))

check("schemas", commands.get("schema_version", "").endswith("native-offline-command-receipts-5.0") and observation.get("schema_version", "").endswith("native-offline-observation-receipt-5.0") and handoff.get("schema_version", "").endswith("native-offline-handoff-5.0"), None)
passports = [doc.get("material_passport") for doc in (commands, observation, handoff)]
check("shared_passport", all(p == passports[0] for p in passports), passports)
passport = passports[0] if isinstance(passports[0], dict) else {}
check("passport", passport.get("origin_skill") == "experiment-agent" and passport.get("origin_mode") == "run" and passport.get("verification_status") == "UNVERIFIED" and passport.get("version_label") == "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_observation_v5" and passport.get("repro_lock") is None, passport)
check("passport_dependencies", passport.get("upstream_dependencies") == ["stage1e_e4_r6_pc2w_p1_attempt003_native_offline_authorization_v5", "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_contract_v5", "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_v2"], passport.get("upstream_dependencies"))

rows = commands.get("commands", [])
ids = [row.get("command_id") for row in rows if isinstance(row, dict)]
check("exact_commands", ids == EXPECTED_COMMANDS, ids)
check("zero_retry", commands.get("automatic_retry_count") == 0 and observation.get("automatic_retry_count") == 0, None)
check("all_completed", all(row.get("timed_out") is False and row.get("spawn_exception_type") is None for row in rows), rows)
exit_codes = {row.get("command_id"): row.get("exit_code") for row in rows}
check("exit_codes", exit_codes == {
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY": 1,
    "O01A_WSL_LIST_VERBOSE": 0,
    "O02A_WSL_LIST_RUNNING_QUIET": 0,
    "O03A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY": 0,
    "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER": 0,
    "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER": 0,
    "O03B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER": 0,
}, exit_codes)
check("hash_only_outputs", commands.get("raw_stdout_or_stderr_persisted") is False and all("stdout" not in row and "stderr" not in row and isinstance(row.get("stdout_sha256"), str) and isinstance(row.get("stderr_sha256"), str) for row in rows), None)
check("no_daemon_cli", all(not (len(row.get("argv", [])) >= 2 and row.get("argv", [])[1] == "version") for row in rows), ids)
check("no_mutation_argv", all(not any(str(token).casefold() in {"start", "stop", "shutdown", "terminate", "run", "create", "pull", "build"} for token in row.get("argv", [])[1:]) for row in rows), ids)

check("entry_binding", observation.get("entry_checkpoint") == EXECUTION_CHECKPOINT and observation.get("runner_checkpoint") == RUNNER_CHECKPOINT, [observation.get("entry_checkpoint"), observation.get("runner_checkpoint")])
status = observation.get("docker_desktop_status_lane", {})
check("status_telemetry_only", status.get("classification") == "RUNNING_EXACT" and status.get("advisory_only") is True and status.get("admission_authority") is False and status.get("cannot_veto_or_admit_native_gate") is True and observation.get("status_lane_used_for_admission") is False, status)
for key in ("snapshot_a", "snapshot_b_stability_barrier"):
    snapshot = observation.get(key, {})
    lanes = snapshot.get("lanes_pass", {})
    check(f"{key}:exact_lane_set", set(lanes) == {"wsl_inventory_all_stopped", "wsl_running_inventory_empty", "desktop_linux_named_pipe_specifically_absent_win32_error_2", "target_runtime_process_inventory_empty"} and all(value is True for value in lanes.values()), lanes)
    check(f"{key}:wsl", snapshot.get("wsl_inventory") == {"parse_complete": True, "rows": [{"name": "docker-desktop", "state": "Stopped", "version": 2}], "docker_desktop_state": "Stopped"}, snapshot.get("wsl_inventory"))
    check(f"{key}:running", snapshot.get("wsl_running_inventory") == {"parse_complete": True, "running_names": []}, snapshot.get("wsl_running_inventory"))
    check(f"{key}:process", snapshot.get("runtime_process_inventory") == {"parse_complete": True, "runtime_processes": []}, snapshot.get("runtime_process_inventory"))
    pipe = snapshot.get("desktop_linux_named_pipe_probe", {})
    check(f"{key}:pipe", pipe.get("method") == "WaitNamedPipeW_one_millisecond_timeout" and pipe.get("timeout_milliseconds") == 1 and pipe.get("available") is False and pipe.get("win32_error") == 2 and pipe.get("probe_exception_type") is None, pipe)
independent = observation.get("independent_lanes_pass", {})
check("native_snapshot_pass", independent.get("snapshot_a_all_native_lanes") is True and independent.get("snapshot_b_all_native_lanes") is True, independent)
check("stable", all(independent.get(k) is True for k in ("wsl_inventory_stable_across_barrier", "running_inventory_stable_across_barrier", "runtime_process_inventory_stable_across_barrier", "named_pipe_absence_stable_across_barrier")), independent)
check("pass_verdict", observation.get("verdict") == "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_BASELINE_V5" and handoff.get("verdict") == observation.get("verdict") and handoff.get("next_gate") == "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT", [observation.get("verdict"), handoff.get("next_gate")])
check("immediate_replay_required", observation.get("observation_is_not_sufficient_without_attempt003_immediate_pre_gate_replay") is True, None)
for key in ("state_mutation_command_issued", "image_or_container_mutation_performed", "settings_changed", "install_or_download_performed", "materialization_performed", "scientific_execution_performed"):
    check(f"mutation_false:{key}", observation.get(key) is False, observation.get(key))
check("truth", observation.get("result_status") == "NOT_RUN" and observation.get("test_set_opened") == "NO" and observation.get("accepted_result_rows") == 0 and handoff.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, None)

output_facts = {row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256")) for row in validation.get("output_facts", []) if isinstance(row, dict)}
check("output_fact_count", len(output_facts) == 3, output_facts)
for name in sorted(EXPECTED_PACKET_FILES):
    path = f"{ROOT_RELATIVE.as_posix()}/{name}"
    check(f"output_blob:{name}", blob_fact(PACKET_COMMIT, path) == output_facts.get(path), [blob_fact(PACKET_COMMIT, path), output_facts.get(path)])
frozen = dispatch.get("frozen_artifacts", [])
check("frozen_count", len(frozen) == 4, len(frozen))
for row in frozen:
    if isinstance(row, dict):
        path = str(row.get("path"))
        check(f"frozen_blob:{Path(path).name}", blob_fact(EXECUTION_CHECKPOINT, path) == (row.get("git_blob_bytes"), row.get("git_blob_sha256")), row)

central = validation.get("central_validation", {})
check("central_model", central.get("model") == "gpt-5.6-sol" and central.get("reasoning_effort") == "max" and central.get("service_tier") == "default" and central.get("display_name") == "Sol Max Standard", central)
check("validator_blob", blob_fact(head, VALIDATOR_RELATIVE) == (central.get("validator_raw_bytes"), central.get("validator_raw_sha256")), central)
check("validator_claim", central.get("validator_verdict") == "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_V5_VALIDATED", central)
result = validation.get("attempt_result", {})
check("validation_result", result.get("verdict") == "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_BASELINE_V5" and result.get("observation_attempts") == 1 and result.get("automatic_retry_count") == 0 and result.get("attempt003_execution_opened") is False, result)

pc2w = pipeline.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
check("pipeline_root", pipeline.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt003_native_offline_v5_pass_validated_runner_audit_required", pipeline.get("state"))
check("pipeline_status", pipeline.get("rebaseline_v2", {}).get("status") == "e4_r6_pc2w_p1_attempt003_native_offline_v5_pass_validated", pipeline.get("rebaseline_v2", {}).get("status"))
record = pc2w.get("p1_attempt003_native_offline_observation_v5", {})
check("pipeline_nested", pc2w.get("status") == "P1_ATTEMPT003_NATIVE_OFFLINE_V5_PASS_VALIDATED_RUNNER_AUDIT_REQUIRED" and record.get("verdict") == "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_BASELINE_V5" and record.get("attempt003_execution_opened") is False, record)
check("pipeline_gate", pc2w.get("next_gate") == "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT", pc2w.get("next_gate"))
check("phase_not_complete", pipeline.get("stage") == "1E" and pipeline.get("result_status") == "NOT_RUN" and pipeline.get("test_set_opened") == "NO", None)

failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_V5_VALIDATED" if not failures else "FAIL",
    "expected_head": expected_head,
    "packet_commit": PACKET_COMMIT,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)
