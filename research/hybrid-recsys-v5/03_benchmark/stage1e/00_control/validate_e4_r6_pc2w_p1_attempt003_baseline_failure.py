#!/usr/bin/env python3
"""Validate sealed PC2W-P1 attempt-003 baseline-restoration failure packet."""

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
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-baseline-restoration"
)
ROOT = AUDIT_REPO / ROOT_RELATIVE
EXECUTION_CHECKPOINT = "3b565467bdec068e1a5f14273520fa6759233a17"
RUNNER_CHECKPOINT = "596bacc6a85572949e47e0953d09f0a60611e926"
SEALED_PACKET_COMMIT = "7e0790ac981e091abb362885fb95a23959a8a0ff"
EXPECTED_VALIDATION_PARENT = SEALED_PACKET_COMMIT
EXPECTED_VALIDATION_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_baseline_failure.py",
}
EXPECTED_PACKET_CHANGES = {
    f"{ROOT_RELATIVE.as_posix()}/baseline_command_receipts.json",
    f"{ROOT_RELATIVE.as_posix()}/baseline_handoff.json",
    f"{ROOT_RELATIVE.as_posix()}/baseline_restoration_receipt.json",
}
EXPECTED_FILES = {
    "baseline_command_receipts.json",
    "baseline_handoff.json",
    "baseline_restoration_receipt.json",
}
EXPECTED_COMMANDS = [
    "B00_DOCKER_DESKTOP_STATUS_BEFORE",
    "B01_WSL_LIST_BEFORE",
    "B02_DAEMON_VERSION_BEFORE",
    "B03_DOCKER_DESKTOP_STOP_ONCE",
    "B04_WSL_SHUTDOWN_ONCE",
    "B05_DOCKER_DESKTOP_STATUS_AFTER",
    "B06_DAEMON_VERSION_AFTER",
    "B07_WSL_LIST_AFTER",
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


def file_fact(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256_bytes(data)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=AUDIT_REPO, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(revision: str, relative: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=AUDIT_REPO,
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
    commands = load(ROOT / "baseline_command_receipts.json")
    restoration = load(ROOT / "baseline_restoration_receipt.json")
    handoff = load(ROOT / "baseline_handoff.json")
    validation = load(CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_validation_receipt.json")
    pipeline = load(CONTROL / "pipeline_state_stage1e.json")
    dispatch = load(CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_dispatch.json")
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
check("packet_parent", git("rev-parse", f"{SEALED_PACKET_COMMIT}^").casefold() == EXECUTION_CHECKPOINT, git("rev-parse", f"{SEALED_PACKET_COMMIT}^"))
check("packet_exact_changes", changed_paths(SEALED_PACKET_COMMIT) == EXPECTED_PACKET_CHANGES, sorted(changed_paths(SEALED_PACKET_COMMIT)))
check("execution_parent", git("rev-parse", f"{EXECUTION_CHECKPOINT}^").casefold() == RUNNER_CHECKPOINT, git("rev-parse", f"{EXECUTION_CHECKPOINT}^"))

check("exact_files", {path.name for path in entries} == EXPECTED_FILES and all(path.is_file() for path in entries), sorted(path.name for path in entries))
check("schemas", commands.get("schema_version", "").endswith("baseline-command-receipts-1.0") and restoration.get("schema_version", "").endswith("baseline-restoration-receipt-1.0") and handoff.get("schema_version", "").endswith("baseline-handoff-1.0"), None)
passports = [doc.get("material_passport") for doc in (commands, restoration, handoff)]
check("shared_passport", all(item == passports[0] for item in passports), passports)
passport = passports[0] if isinstance(passports[0], dict) else {}
check("execution_passport", passport.get("origin_skill") == "experiment-agent" and passport.get("origin_mode") == "run" and passport.get("verification_status") == "UNVERIFIED" and passport.get("version_label") == "stage1e_e4_r6_pc2w_p1_attempt003_baseline_execution_v3" and passport.get("repro_lock") is None, passport)
check("execution_dependencies", passport.get("upstream_dependencies") == ["stage1e_e4_r6_pc2w_p1_attempt003_user_authorization_v3", "stage1e_e4_r6_pc2w_p1_attempt003_baseline_contract_v1"], passport.get("upstream_dependencies"))
validation_passport = validation.get("material_passport", {})
check("validation_passport", validation_passport.get("origin_skill") == "experiment-agent" and validation_passport.get("origin_mode") == "validate" and validation_passport.get("verification_status") == "ANALYZED" and validation_passport.get("repro_lock") is None, validation_passport)

rows = commands.get("commands", [])
ids = [row.get("command_id") for row in rows if isinstance(row, dict)]
check("exact_commands", ids == EXPECTED_COMMANDS, ids)
check("zero_retry", commands.get("automatic_retry_count") == 0 and restoration.get("automatic_retry_count") == 0, None)
check("one_stop_shutdown", restoration.get("docker_stop_attempts") == 1 and restoration.get("wsl_shutdown_attempts") == 1, restoration)
check("no_start_command", all("start" not in [str(token).casefold() for token in row.get("argv", [])[1:]] for row in rows), ids)
check("all_completed_no_timeout", all(row.get("timed_out") is False and row.get("spawn_exception_type") is None for row in rows), rows)
exit_by_id = {row.get("command_id"): row.get("exit_code") for row in rows}
check("expected_exit_codes", exit_by_id == {
    "B00_DOCKER_DESKTOP_STATUS_BEFORE": 0,
    "B01_WSL_LIST_BEFORE": 0,
    "B02_DAEMON_VERSION_BEFORE": 0,
    "B03_DOCKER_DESKTOP_STOP_ONCE": 0,
    "B04_WSL_SHUTDOWN_ONCE": 0,
    "B05_DOCKER_DESKTOP_STATUS_AFTER": 1,
    "B06_DAEMON_VERSION_AFTER": 1,
    "B07_WSL_LIST_AFTER": 0,
}, exit_by_id)
check("hash_only_outputs", all("stdout" not in row and "stderr" not in row and isinstance(row.get("stdout_sha256"), str) and isinstance(row.get("stderr_sha256"), str) for row in rows) and commands.get("raw_stdout_or_stderr_persisted") is False, None)

before = restoration.get("before", {})
after = restoration.get("after", {})
check("before_running", before.get("docker_desktop_status") == "running" and before.get("docker_desktop_wsl_distro") == "Running" and before.get("daemon_specifically_unavailable") is False and before.get("wsl_list_parse_complete") is True, before)
check("after_partial_stopped_evidence", after.get("docker_desktop_status") is None and after.get("docker_desktop_wsl_distro") == "Stopped" and after.get("daemon_specifically_unavailable") is True and after.get("wsl_list_parse_complete") is True, after)
check("after_all_wsl_stopped", after.get("all_wsl_rows") == [{"name": "docker-desktop", "state": "Stopped", "version": 2}], after.get("all_wsl_rows"))
check("conjunctive_gate_failed", restoration.get("post_baseline_stopped") is False and restoration.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT003_BASELINE_NOT_RESTORED", restoration.get("verdict"))
attempt_result = validation.get("attempt_result", {})
check("failure_class", attempt_result.get("failure_class") == "POST_DOCKER_DESKTOP_STATUS_UNCLASSIFIED_NONZERO" and attempt_result.get("docker_desktop_status_after") == "UNCLASSIFIED_EXIT_1_HASH_ONLY", attempt_result)
check("no_inference", attempt_result.get("baseline_actual_state_inference") == "NOT_INFERRED_FROM_PARTIAL_EVIDENCE", attempt_result)
check("attempt003_not_opened", attempt_result.get("attempt003_start_query_stop_executed") is False and attempt_result.get("new_retry_performed") is False, attempt_result)

for key in (
    "image_pull_or_build_performed", "container_create_or_run_performed",
    "settings_changed", "download_performed", "materialization_performed",
    "scientific_execution_performed",
):
    check(f"mutation_false:{key}", restoration.get(key) is False, restoration.get(key))
check("truth", restoration.get("result_status") == "NOT_RUN" and restoration.get("test_set_opened") == "NO" and restoration.get("accepted_result_rows") == 0 and handoff.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, None)

output_facts = {row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256")) for row in validation.get("output_facts", []) if isinstance(row, dict)}
check("output_fact_count", len(output_facts) == 3, output_facts)
for name in sorted(EXPECTED_FILES):
    relative = f"{ROOT_RELATIVE.as_posix()}/{name}"
    check(f"output_blob:{name}", blob_fact(SEALED_PACKET_COMMIT, relative) == output_facts.get(relative), [blob_fact(SEALED_PACKET_COMMIT, relative), output_facts.get(relative)])

frozen = dispatch.get("frozen_artifacts", [])
check("frozen_count", len(frozen) == 5, len(frozen))
for row in frozen:
    if isinstance(row, dict):
        relative = str(row.get("path"))
        expected = (row.get("raw_bytes"), row.get("raw_sha256"))
        check(f"frozen_blob:{relative}", blob_fact(EXECUTION_CHECKPOINT, relative) == expected, [blob_fact(EXECUTION_CHECKPOINT, relative), expected])

validator_record = validation.get("central_validation", {})
validator_relative = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt003_baseline_failure.py"
check("validator_blob", blob_fact(expected_head, validator_relative) == (validator_record.get("validator_raw_bytes"), validator_record.get("validator_raw_sha256")), validator_record)
check("validation_claim", validator_record.get("validator_verdict") == "PASS_PC2W_P1_ATTEMPT003_BASELINE_FAILURE_VALIDATED", validator_record)

pc2w = pipeline.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
check("pipeline_root", pipeline.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt003_baseline_fail_closed_status_unclassified_awaiting_user_decision", pipeline.get("state"))
check("pipeline_status", pipeline.get("rebaseline_v2", {}).get("status") == "e4_r6_pc2w_p1_attempt003_baseline_fail_closed_status_unclassified", pipeline.get("rebaseline_v2", {}).get("status"))
check("pipeline_nested", pc2w.get("status") == "P1_ATTEMPT003_BASELINE_FAIL_CLOSED_POST_STATUS_UNCLASSIFIED_NO_AUTOMATIC_RETRY" and pc2w.get("p1_attempt003_baseline", {}).get("authorization_consumed") is True and pc2w.get("p1_attempt003_baseline", {}).get("attempt003_execution_opened") is False, pc2w.get("p1_attempt003_baseline"))
check("pipeline_gate", pc2w.get("next_gate") == "EXPLICIT_USER_DECISION_REQUIRED_FOR_ANY_NEW_BASELINE_ADMISSION_REVISION_OR_ATTEMPT_NO_AUTOMATIC_RETRY", pc2w.get("next_gate"))
check("phase_not_complete", pipeline.get("stage") == "1E" and pipeline.get("result_status") == "NOT_RUN" and pipeline.get("test_set_opened") == "NO", None)

failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT003_BASELINE_FAILURE_VALIDATED" if not failures else "FAIL",
    "expected_head": expected_head,
    "sealed_packet_commit": SEALED_PACKET_COMMIT,
    "execution_checkpoint": EXECUTION_CHECKPOINT,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)

