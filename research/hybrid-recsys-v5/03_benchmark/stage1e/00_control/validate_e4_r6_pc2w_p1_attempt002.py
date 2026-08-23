#!/usr/bin/env python3
"""Portable validator for the sealed PC2W-P1 attempt-002 failure packet."""

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
EXECUTION_REPO = Path(r"E:\UIT\cv\backend")
ROOT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-002"
)
ROOT = EXECUTION_REPO / ROOT_RELATIVE
EXECUTION_CHECKPOINT = "ba3b707b3fd839b4f53e9e5cc64938adf95aa724"
SEALED_PACKET_COMMIT = "9ec4868fec6216f1840a3bbc04fb7203e0ae70d1"
SEALED_PACKET_PARENT = EXECUTION_CHECKPOINT
EXPECTED_REWORK_PARENT = SEALED_PACKET_COMMIT
EXPECTED_REWORK_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt002_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt002.py",
}
EXPECTED_PACKET_CHANGES = {
    f"{ROOT_RELATIVE.as_posix()}/command_receipts.json",
    f"{ROOT_RELATIVE.as_posix()}/runtime_inventory.json",
    f"{ROOT_RELATIVE.as_posix()}/p1_execution_receipt.json",
    f"{ROOT_RELATIVE.as_posix()}/p1_handoff.json",
}
EXPECTED_FILES = {
    "command_receipts.json",
    "runtime_inventory.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
}
EXPECTED_COMMANDS = [
    "P00_WSL_LIST_BEFORE",
    "P01_DOCKER_DESKTOP_STATUS_BEFORE",
    "P02_DAEMON_VERSION_BEFORE",
    "P03_WSL_VERSION_BEFORE",
    "P04_WINDOWS_IDENTITY_BEFORE",
    "P05_DOCKER_DESKTOP_FILE_IDENTITY_BEFORE",
    "P21_DOCKER_DESKTOP_STATUS_AFTER",
    "P22_DAEMON_VERSION_AFTER",
    "P23_WSL_LIST_AFTER",
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


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def blob_fact(repo: Path, revision: str, relative: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=repo,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, shell=False,
    )
    return len(completed.stdout), sha256_bytes(completed.stdout)


def changed_paths(repo: Path, revision: str) -> set[str]:
    return set(
        filter(
            None,
            git(
                repo, "diff-tree", "--no-commit-id", "--name-only", "-r", revision
            ).splitlines(),
        )
    )


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


parser = argparse.ArgumentParser()
parser.add_argument("--expected-head", required=True)
args = parser.parse_args()
expected_head = str(args.expected_head).casefold()

try:
    entries = list(ROOT.iterdir())
    command = load(ROOT / "command_receipts.json")
    inventory = load(ROOT / "runtime_inventory.json")
    execution = load(ROOT / "p1_execution_receipt.json")
    handoff = load(ROOT / "p1_handoff.json")
    validation = load(
        EXECUTION_REPO
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
        "rebaseline_v2_e4_r6_pc2w_p1_attempt002_validation_receipt.json"
    )
    pipeline = load(
        EXECUTION_REPO
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
        "pipeline_state_stage1e.json"
    )
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

audit_head = git(AUDIT_REPO, "rev-parse", "HEAD").casefold()
execution_head = git(EXECUTION_REPO, "rev-parse", "HEAD").casefold()
audit_parent = git(AUDIT_REPO, "rev-parse", "HEAD^").casefold()
execution_parent = git(EXECUTION_REPO, "rev-parse", "HEAD^").casefold()
check("expected_head_format", bool(re.fullmatch(r"[0-9a-f]{40}", expected_head)), expected_head)
check("audit_head_exact", audit_head == expected_head, audit_head)
check("execution_head_exact", execution_head == expected_head, execution_head)
check("audit_parent_exact", audit_parent == EXPECTED_REWORK_PARENT, audit_parent)
check("execution_parent_exact", execution_parent == EXPECTED_REWORK_PARENT, execution_parent)
check("audit_clean", git(AUDIT_REPO, "status", "--porcelain=v1", "--untracked-files=all") == "", git(AUDIT_REPO, "status", "--porcelain=v1", "--untracked-files=all"))
check("execution_clean", git(EXECUTION_REPO, "status", "--porcelain=v1", "--untracked-files=all") == "", git(EXECUTION_REPO, "status", "--porcelain=v1", "--untracked-files=all"))
check("rework_exact_three_files", changed_paths(AUDIT_REPO, expected_head) == EXPECTED_REWORK_CHANGES, sorted(changed_paths(AUDIT_REPO, expected_head)))
check("sealed_packet_parent", git(AUDIT_REPO, "rev-parse", f"{SEALED_PACKET_COMMIT}^").casefold() == SEALED_PACKET_PARENT, git(AUDIT_REPO, "rev-parse", f"{SEALED_PACKET_COMMIT}^"))
check("sealed_packet_exact_four_files", changed_paths(AUDIT_REPO, SEALED_PACKET_COMMIT) == EXPECTED_PACKET_CHANGES, sorted(changed_paths(AUDIT_REPO, SEALED_PACKET_COMMIT)))

check("root_exact", ROOT.resolve() == Path(execution.get("output_root", "")).resolve(), execution.get("output_root"))
check("exact_four_entries", {entry.name for entry in entries} == EXPECTED_FILES and all(entry.is_file() for entry in entries), sorted(entry.name for entry in entries))
check("schemas", command.get("schema_version", "").endswith("command-receipts-2.0") and inventory.get("schema_version", "").endswith("runtime-inventory-2.0") and execution.get("schema_version", "").endswith("execution-receipt-2.0") and handoff.get("schema_version", "").endswith("handoff-2.0"), None)

passports = [document.get("material_passport") for document in (command, inventory, execution, handoff)]
check("execution_passports_shared", all(item == passports[0] for item in passports), passports)
passport = passports[0] if isinstance(passports[0], dict) else {}
check("execution_passport", passport.get("origin_skill") == "experiment-agent" and passport.get("origin_mode") == "run" and passport.get("verification_status") == "UNVERIFIED" and passport.get("version_label") == "stage1e_e4_r6_pc2w_p1_attempt002_execution_v1" and passport.get("repro_lock") is None, passport)
check("execution_passport_dependency", passport.get("upstream_dependencies") == ["stage1e_e4_r6_pc2w_p1_attempt002_user_authorization_v1", "stage1e_e4_r6_pc2w_p1_requirements_v1"], passport.get("upstream_dependencies"))
validation_passport = validation.get("material_passport", {})
check("validation_passport", validation_passport.get("origin_skill") == "experiment-agent" and validation_passport.get("origin_mode") == "validate" and validation_passport.get("verification_status") == "ANALYZED" and validation_passport.get("repro_lock") is None, validation_passport)

rows = command.get("commands", [])
ids = [row.get("command_id") for row in rows if isinstance(row, dict)]
check("exact_nine_commands", ids == EXPECTED_COMMANDS, ids)
check("no_start_stop_or_retry", "P06_DOCKER_DESKTOP_START_ONCE" not in ids and "P20_DOCKER_DESKTOP_STOP_ONCE" not in ids and command.get("automatic_retry_count") == 0 and execution.get("startup_attempts") == 0 and execution.get("stop_attempts") == 0 and execution.get("query_retry_count") == 0, ids)
check("all_nine_completed", all(row.get("exit_code") == 0 and row.get("timed_out") is False and row.get("spawn_exception_type") is None for row in rows), rows)
check("hash_only_output", all("stdout" not in row and "stderr" not in row and isinstance(row.get("stdout_sha256"), str) and isinstance(row.get("stderr_sha256"), str) for row in rows) and command.get("raw_stdout_or_stderr_persisted") is False, None)

pre = execution.get("pre_start_gate", {})
check("pre_identity_and_disk_pass", all(pre.get(key) is True for key in ("wsl_list_query_success", "docker_desktop_status_query_success", "wsl_identity_query_success", "windows_identity_query_success", "docker_file_identity_query_success", "identity_payloads_parsed_and_complete", "disk_thresholds_before_pass")), pre)
check("preexisting_running_blocks_start", all(pre.get(key) is False for key in ("docker_desktop_exactly_stopped", "daemon_specifically_unavailable", "docker_desktop_distro_exactly_stopped")), pre)
check("failure_class", execution.get("verdict") == "FAIL_CLOSED_PC2W_BACKEND_OR_POLICY_NOT_ADMISSIBLE" and validation.get("attempt_result", {}).get("failure_class") == "PRE_START_BASELINE_NOT_STOPPED", [execution.get("verdict"), validation.get("attempt_result")])
status = inventory.get("docker_desktop_status", {})
wsl = inventory.get("wsl_state", {})
check("backend_running_before_after", status == {"before": "running", "during": None, "after": "running"}, status)
check("wsl_running_before_after", wsl.get("before") == [{"name": "docker-desktop", "state": "Running", "version": 2}] and wsl.get("during") == [] and wsl.get("after") == wsl.get("before"), wsl)
check("daemon_reachable_before_after", next(row for row in rows if row.get("command_id") == "P02_DAEMON_VERSION_BEFORE").get("exit_code") == 0 and next(row for row in rows if row.get("command_id") == "P22_DAEMON_VERSION_AFTER").get("exit_code") == 0, None)
check("attribution_unknown", validation.get("attempt_result", {}).get("attribution_of_preexisting_backend_start") == "UNKNOWN_NOT_INFERRED", validation.get("attempt_result"))

for key in (
    "image_pull_or_build_performed", "container_create_or_run_performed",
    "docker_or_wsl_settings_changed", "source_data_or_checkpoint_download_performed",
    "materialization_performed", "scientific_execution_performed",
):
    check(f"mutation_false:{key}", execution.get(key) is False, execution.get(key))
check("secret_safety", inventory.get("proxy_values_persisted") is False and inventory.get("raw_context_persisted") is False and command.get("raw_stdout_or_stderr_persisted") is False, None)
check("truth", execution.get("result_status") == "NOT_RUN" and execution.get("test_set_opened") == "NO" and execution.get("accepted_result_rows") == 0 and handoff.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, None)

expected_output_facts = {
    row.get("path"): (row.get("raw_bytes"), row.get("raw_sha256"))
    for row in validation.get("output_facts", [])
    if isinstance(row, dict)
}
check("validation_output_fact_count", len(expected_output_facts) == 4, expected_output_facts)
for name in sorted(EXPECTED_FILES):
    relative = f"{ROOT_RELATIVE.as_posix()}/{name}"
    expected = expected_output_facts.get(relative)
    check(f"output_blob_fact:{name}", blob_fact(AUDIT_REPO, SEALED_PACKET_COMMIT, relative) == expected, [blob_fact(AUDIT_REPO, SEALED_PACKET_COMMIT, relative), expected])

frozen = execution.get("frozen_artifacts", [])
check("frozen_count", len(frozen) == 5, len(frozen))
for row in frozen:
    if isinstance(row, dict):
        relative = str(row.get("path"))
        expected = (row.get("raw_bytes"), row.get("raw_sha256"))
        check(f"frozen_execution_blob:{relative}", blob_fact(AUDIT_REPO, EXECUTION_CHECKPOINT, relative) == expected, [blob_fact(AUDIT_REPO, EXECUTION_CHECKPOINT, relative), expected])

validator_relative = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt002.py"
validator_record = validation.get("central_validation", {})
check("validator_blob_fact", blob_fact(AUDIT_REPO, expected_head, validator_relative) == (validator_record.get("validator_raw_bytes"), validator_record.get("validator_raw_sha256")), [blob_fact(AUDIT_REPO, expected_head, validator_relative), validator_record])
check("validation_claim", validator_record.get("validator_verdict") == "PASS_PC2W_P1_ATTEMPT002_FAILURE_RECEIPT_VALIDATED" and validator_record.get("checks") == "54/54", validator_record)

pc2w = pipeline.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
check("pipeline_root_state", pipeline.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt002_fail_closed_preexisting_backend_running_awaiting_user_decision", pipeline.get("state"))
check("pipeline_rebaseline_status", pipeline.get("rebaseline_v2", {}).get("status") == "e4_r6_pc2w_p1_attempt002_fail_closed_preexisting_backend_running", pipeline.get("rebaseline_v2", {}).get("status"))
check("pipeline_nested_state", pc2w.get("status") == "P1_ATTEMPT002_FAIL_CLOSED_PRE_START_BASELINE_NOT_STOPPED_NO_AUTOMATIC_RETRY" and pc2w.get("p1_attempt002", {}).get("attempt_authorization_consumed") is True and pc2w.get("p1_attempt002", {}).get("new_attempt_authorized") is False, pc2w.get("p1_attempt002"))
check("pipeline_gate", pc2w.get("next_gate") == "EXPLICIT_USER_DECISION_REQUIRED_FOR_ANY_SEPARATE_BASELINE_RESTORATION_AND_NEW_PC2W_P1_ATTEMPT_NO_AUTOMATIC_RETRY", pc2w.get("next_gate"))
check("phase_not_complete", pipeline.get("stage") == "1E" and pipeline.get("result_status") == "NOT_RUN" and pipeline.get("test_set_opened") == "NO", [pipeline.get("stage"), pipeline.get("result_status"), pipeline.get("test_set_opened")])

failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT002_FAILURE_RECEIPT_VALIDATED" if not failures else "FAIL",
    "expected_head": expected_head,
    "sealed_packet_commit": SEALED_PACKET_COMMIT,
    "execution_checkpoint": EXECUTION_CHECKPOINT,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
}, indent=2))
sys.exit(1 if failures else 0)

