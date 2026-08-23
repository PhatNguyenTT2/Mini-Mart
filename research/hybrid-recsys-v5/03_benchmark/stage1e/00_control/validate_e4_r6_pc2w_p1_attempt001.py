#!/usr/bin/env python3
"""Validate the immutable PC2W-P1 attempt-001 pre-start failure receipt."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
REPO = CONTROL.parents[4]
ROOT = REPO / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-001"
)
EXPECTED_HEAD = "6237e196d5bc689cb004c2149ff8a81e82410ddf"
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
ALLOWED_TRACKED_VALIDATION_CHANGES = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/pipeline_state_stage1e.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/rebaseline_v2_e4_r6_pc2w_p1_attempt001_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/validate_e4_r6_pc2w_p1_attempt001.py",
}


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


def file_fact(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO)).replace("\\", "/"),
        "raw_bytes": len(data),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
    }


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPO, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


try:
    entries = list(ROOT.iterdir())
    command = load(ROOT / "command_receipts.json")
    inventory = load(ROOT / "runtime_inventory.json")
    execution = load(ROOT / "p1_execution_receipt.json")
    handoff = load(ROOT / "p1_handoff.json")
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    raise SystemExit(1)

current_head = git("rev-parse", "HEAD").casefold()
try:
    git("merge-base", "--is-ancestor", EXPECTED_HEAD, "HEAD")
    execution_checkpoint_is_ancestor = True
except subprocess.CalledProcessError:
    execution_checkpoint_is_ancestor = False
check("execution_checkpoint_is_ancestor", execution_checkpoint_is_ancestor, [EXPECTED_HEAD, current_head])
tracked_changes = set(filter(None, git("diff", "--name-only").splitlines()))
check("tracked_changes_bounded", tracked_changes <= ALLOWED_TRACKED_VALIDATION_CHANGES, sorted(tracked_changes))
check("root_exact", ROOT.resolve() == Path(execution.get("output_root", "")).resolve(), execution.get("output_root"))
check("exact_four_entries", {entry.name for entry in entries} == EXPECTED_FILES and all(entry.is_file() for entry in entries), sorted(entry.name for entry in entries))

check("command_schema", command.get("schema_version") == "stage1e-e4-r6-pc2w-p1-command-receipts-2.0", command.get("schema_version"))
check("inventory_schema", inventory.get("schema_version") == "stage1e-e4-r6-pc2w-p1-runtime-inventory-2.0", inventory.get("schema_version"))
check("execution_schema", execution.get("schema_version") == "stage1e-e4-r6-pc2w-p1-execution-receipt-2.0", execution.get("schema_version"))
check("handoff_schema", handoff.get("schema_version") == "stage1e-e4-r6-pc2w-p1-handoff-2.0", handoff.get("schema_version"))

passports = [document.get("material_passport") for document in (command, inventory, execution, handoff)]
check("passport_exactly_shared", all(item == passports[0] for item in passports), passports)
passport = passports[0] if isinstance(passports[0], dict) else {}
check("passport_origin", passport.get("origin_skill") == "experiment-agent" and passport.get("origin_mode") == "run", passport)
check("passport_status", passport.get("verification_status") == "UNVERIFIED", passport.get("verification_status"))
check("passport_version", passport.get("version_label") == "stage1e_e4_r6_pc2w_p1_execution_v3", passport.get("version_label"))
check("passport_dependency", passport.get("upstream_dependencies") == ["stage1e_e4_r6_pc2w_p1_user_authorization_v3", "stage1e_e4_r6_pc2w_p1_requirements_v1"], passport.get("upstream_dependencies"))
check("passport_intake", passport.get("experiment_intake_declaration") == {"status": "no_experiments_declared", "declared_at": "2026-08-24T01:12:40.9534228+07:00", "declared_by": "scholar"}, passport.get("experiment_intake_declaration"))

rows = command.get("commands", [])
ids = [row.get("command_id") for row in rows if isinstance(row, dict)]
check("exact_nine_commands", ids == EXPECTED_COMMANDS, ids)
check("no_start_command", "P06_DOCKER_DESKTOP_START_ONCE" not in ids, ids)
check("no_stop_command", "P20_DOCKER_DESKTOP_STOP_ONCE" not in ids, ids)
check("all_commands_completed", all(row.get("exit_code") == 0 and row.get("timed_out") is False and row.get("spawn_exception_type") is None for row in rows), rows)
check("hash_only_output", all("stdout" not in row and "stderr" not in row and isinstance(row.get("stdout_sha256"), str) and isinstance(row.get("stderr_sha256"), str) for row in rows), None)
check("zero_retry", command.get("automatic_retry_count") == 0 and command.get("raw_stdout_or_stderr_persisted") is False, command.get("automatic_retry_count"))

pre = execution.get("pre_start_gate", {})
check("pre_queries_succeeded", all(pre.get(key) is True for key in ("wsl_list_query_success", "docker_desktop_status_query_success", "wsl_identity_query_success", "windows_identity_query_success", "docker_file_identity_query_success", "identity_payloads_parsed_and_complete", "disk_thresholds_before_pass")), pre)
check("pre_existing_backend_running_blocks_start", all(pre.get(key) is False for key in ("docker_desktop_exactly_stopped", "daemon_specifically_unavailable", "docker_desktop_distro_exactly_stopped")), pre)
check("zero_start_stop_attempts", execution.get("startup_attempts") == 0 and execution.get("stop_attempts") == 0 and execution.get("query_retry_count") == 0, [execution.get("startup_attempts"), execution.get("stop_attempts"), execution.get("query_retry_count")])
check("fail_closed_verdict", execution.get("verdict") == "FAIL_CLOSED_PC2W_BACKEND_OR_POLICY_NOT_ADMISSIBLE" and handoff.get("verdict") == execution.get("verdict"), execution.get("verdict"))

status = inventory.get("docker_desktop_status", {})
wsl = inventory.get("wsl_state", {})
check("backend_running_before_after", status == {"before": "running", "during": None, "after": "running"}, status)
check("wsl_running_before_after", wsl.get("before") == [{"name": "docker-desktop", "state": "Running", "version": 2}] and wsl.get("during") == [] and wsl.get("after") == wsl.get("before"), wsl)
check("daemon_reachable_before_after", next(row for row in rows if row.get("command_id") == "P02_DAEMON_VERSION_BEFORE").get("exit_code") == 0 and next(row for row in rows if row.get("command_id") == "P22_DAEMON_VERSION_AFTER").get("exit_code") == 0, None)
check("no_runtime_query_inventory", inventory.get("images_initial") == [] and inventory.get("images_final") == [] and inventory.get("containers_initial") == [] and inventory.get("containers_final") == [] and inventory.get("container_or_image_events") == [], None)
check("secret_safety", inventory.get("proxy_values_persisted") is False and inventory.get("raw_context_persisted") is False and command.get("raw_stdout_or_stderr_persisted") is False, None)
check("parse_failures_absent", inventory.get("parse_failures") == [], inventory.get("parse_failures"))

for key in (
    "image_pull_or_build_performed", "container_create_or_run_performed",
    "docker_or_wsl_settings_changed", "source_data_or_checkpoint_download_performed",
    "materialization_performed", "scientific_execution_performed",
):
    check(f"mutation_false:{key}", execution.get(key) is False, execution.get(key))
check("truth_execution", execution.get("result_status") == "NOT_RUN" and execution.get("test_set_opened") == "NO" and execution.get("accepted_result_rows") == 0, [execution.get("result_status"), execution.get("test_set_opened"), execution.get("accepted_result_rows")])
check("truth_handoff", handoff.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, handoff.get("truth_state"))
check("next_gate_no_retry", handoff.get("next_gate") == "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY", handoff.get("next_gate"))

frozen = execution.get("frozen_artifacts", [])
check("frozen_count", len(frozen) == 5, len(frozen))
for row in frozen:
    if isinstance(row, dict):
        path = REPO / str(row.get("path"))
        check(f"frozen_fact:{row.get('path')}", path.is_file() and file_fact(path)["raw_bytes"] == row.get("raw_bytes") and file_fact(path)["raw_sha256"] == row.get("raw_sha256"), file_fact(path) if path.is_file() else None)

output_facts = [file_fact(ROOT / name) for name in sorted(EXPECTED_FILES)]
failures = [row for row in checks if not row["pass"]]
print(json.dumps({
    "verdict": "PASS_PC2W_P1_ATTEMPT001_FAILURE_RECEIPT_VALIDATED" if not failures else "FAIL",
    "execution_checkpoint": EXPECTED_HEAD,
    "checks": f"{len(checks) - len(failures)}/{len(checks)}",
    "failure_count": len(failures),
    "failures": failures,
    "output_facts": output_facts,
}, indent=2))
sys.exit(1 if failures else 0)
