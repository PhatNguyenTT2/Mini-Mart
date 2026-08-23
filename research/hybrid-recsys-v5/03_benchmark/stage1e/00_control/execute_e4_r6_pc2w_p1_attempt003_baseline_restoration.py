#!/usr/bin/env python3
"""Restore a stopped Docker Desktop/WSL baseline once for PC2W-P1 attempt-003."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOCKER = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
WSL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wsl.exe"
EXPECTED_DOCKER_DESKTOP_SHA256 = "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce"

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_baseline_restoration.py"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_user_authorization_and_model_override.json"
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_dispatch.json"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_baseline_restoration_contract.json"
ATTEMPT002_VALIDATION_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt002_validation_receipt.json"
PC2W_CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_current_host_wsl2_linux_admission_contract.md"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-baseline-restoration"
)
EXPECTED_HEAD_CHANGE_SET = {AUTH_RELATIVE.as_posix(), DISPATCH_RELATIVE.as_posix()}
EXPECTED_OUTPUT_FILES = {
    "baseline_command_receipts.json",
    "baseline_restoration_receipt.json",
    "baseline_handoff.json",
}
DAEMON_PIPE_MARKERS = ("dockerdesktoplinuxengine", "//./pipe/dockerdesktoplinuxengine")
DAEMON_PIPE_MISSING_MARKERS = (
    "the system cannot find the file specified",
    "no such file or directory",
)
PERMISSION_ERROR_MARKERS = ("access is denied", "permission denied", "unauthorized")


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate key: {key}")
        case = key.casefold()
        if case in folded:
            raise DuplicateKeyError(f"case collision: {folded[case]} vs {key}")
        value[key] = item
        folded[case] = key
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object JSON root: {path}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_fact(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256_bytes(data)


def decode_output(value: bytes) -> str:
    if not value:
        return ""
    if value.count(b"\x00") > max(1, len(value) // 8):
        return value.decode("utf-16-le", errors="replace")
    return value.decode("utf-8", errors="replace")


def git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo_root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_blob_fact(repo_root: Path, revision: str, relative: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative.as_posix()}"], cwd=repo_root,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=False, check=True,
    )
    return len(completed.stdout), sha256_bytes(completed.stdout)


def run_command(command_id: str, argv: list[str], timeout_seconds: int) -> tuple[dict[str, Any], bytes, bytes]:
    started_at = utc_now()
    started = time.monotonic()
    stdout = b""
    stderr = b""
    exit_code: int | None = None
    timed_out = False
    exception_type: str | None = None
    exception_sha256: str | None = None
    try:
        completed = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, check=False,
            timeout=timeout_seconds,
        )
        stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, timed_out = exc.stdout or b"", exc.stderr or b"", True
    except Exception as exc:
        exception_type = type(exc).__name__
        exception_sha256 = sha256_bytes(str(exc).encode("utf-8"))
    receipt = {
        "command_id": command_id,
        "argv": argv,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "started_at": started_at,
        "ended_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "spawn_exception_type": exception_type,
        "spawn_exception_message_sha256": exception_sha256,
        "stdout_bytes": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
    }
    return receipt, stdout, stderr


def command_ok(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("exit_code") == 0
        and receipt.get("timed_out") is False
        and receipt.get("spawn_exception_type") is None
    )


def parse_status(value: bytes) -> str | None:
    matches = set(re.findall(r"\b(running|stopped)\b", decode_output(value).casefold()))
    return next(iter(matches)) if len(matches) == 1 else None


def parse_wsl_list(value: bytes) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    header_seen = False
    for raw_line in decode_output(value).replace("\x00", "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        folded_line = line.casefold()
        if "name" in folded_line and "state" in folded_line and "version" in folded_line:
            if header_seen or rows:
                return [], False
            header_seen = True
            continue
        match = re.match(r"^\*?\s*(.+?)\s+(Running|Stopped)\s+([12])\s*$", line, re.IGNORECASE)
        if not match:
            return [], False
        name = match.group(1).strip()
        folded_name = name.casefold()
        if not name or folded_name in seen_names:
            return [], False
        seen_names.add(folded_name)
        rows.append({
            "name": name,
            "state": match.group(2).title(),
            "version": int(match.group(3)),
        })
    complete = header_seen and len(rows) > 0
    if not complete:
        return [], False
    return sorted(rows, key=lambda row: str(row.get("name", "")).casefold()), True


def distro_state(rows: list[dict[str, Any]], name: str) -> str | None:
    values = [str(row.get("state")) for row in rows if str(row.get("name", "")).casefold() == name.casefold()]
    return values[0] if len(values) == 1 else None


def daemon_is_specifically_unavailable(receipt: dict[str, Any], stdout: bytes, stderr: bytes) -> bool:
    if receipt.get("timed_out") or receipt.get("spawn_exception_type") is not None:
        return False
    code = receipt.get("exit_code")
    if not isinstance(code, int) or code == 0:
        return False
    text = (decode_output(stdout) + "\n" + decode_output(stderr)).casefold()
    return (
        any(marker in text for marker in DAEMON_PIPE_MARKERS)
        and any(marker in text for marker in DAEMON_PIPE_MISSING_MARKERS)
        and not any(marker in text for marker in PERMISSION_ERROR_MARKERS)
    )


def material_passport(created_at: str, auth: dict[str, Any]) -> dict[str, Any]:
    intake = auth.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization Material Passport intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt003_baseline_execution_v3",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt003_user_authorization_v3",
            "stage1e_e4_r6_pc2w_p1_attempt003_baseline_contract_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repo root is not exact Git worktree root")
    output_root = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_root.exists():
        raise RuntimeError(f"immutable output root already exists: {output_root}")
    for required in (DOCKER, DOCKER_DESKTOP, WSL):
        if not required.is_file():
            raise RuntimeError(f"required executable missing: {required}")
    if sha256_file(DOCKER_DESKTOP) != EXPECTED_DOCKER_DESKTOP_SHA256:
        raise RuntimeError("Docker Desktop executable hash changed")

    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        raise RuntimeError("exact execution HEAD mismatch")
    parent_fields = git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parent_fields) != 2:
        raise RuntimeError("execution checkpoint must have exactly one parent")
    parent = parent_fields[1].casefold()
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean")
    changed = set(filter(None, git(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
    if changed != EXPECTED_HEAD_CHANGE_SET:
        raise RuntimeError(f"execution checkpoint change set mismatch: {sorted(changed)}")

    auth = load_json(repo_root / AUTH_RELATIVE)
    dispatch = load_json(repo_root / DISPATCH_RELATIVE)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if auth.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-user-authorization-model-override-1.0":
        raise RuntimeError("attempt-003 authorization schema mismatch")
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-baseline-dispatch-1.0":
        raise RuntimeError("attempt-003 baseline dispatch schema mismatch")
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-baseline-restoration-contract-1.0":
        raise RuntimeError("attempt-003 baseline contract schema mismatch")
    if auth.get("entry_checkpoint", "").casefold() != parent or dispatch.get("runner_checkpoint", "").casefold() != parent:
        raise RuntimeError("runner checkpoint binding mismatch")
    if Path(auth.get("authorized_baseline_output_root", "")).resolve() != output_root:
        raise RuntimeError("authorization output root mismatch")
    binding = dispatch.get("execution_binding", {})
    if Path(binding.get("output_root", "")).resolve() != output_root:
        raise RuntimeError("dispatch output root mismatch")
    if binding.get("expected_output_files") != sorted(EXPECTED_OUTPUT_FILES):
        raise RuntimeError("dispatch expected output set mismatch")
    decision = auth.get("user_decision", {})
    if decision.get("decision") != "AUTHORIZE_PC2W_P1_ATTEMPT003_BASELINE_RESTORATION_AND_EXECUTION":
        raise RuntimeError("attempt-003 user authorization missing")
    if decision.get("baseline_restoration_authorized") is not True or decision.get("attempt003_execution_authorized") is not True:
        raise RuntimeError("attempt-003 authorization scope incomplete")
    for key in (
        "automatic_retry_authorized", "image_pull_or_build_authorized",
        "container_create_or_run_authorized", "docker_or_wsl_settings_change_authorized",
        "package_or_distro_install_authorized", "source_data_or_checkpoint_download_authorized",
        "materialization_authorized", "training_authorized", "evaluation_authorized",
        "test_access_authorized",
    ):
        if decision.get(key) is not False:
            raise RuntimeError(f"forbidden authorization flag changed: {key}")

    frozen = dispatch.get("frozen_artifacts")
    expected_frozen = {
        RUNNER_RELATIVE, AUTH_RELATIVE, CONTRACT_RELATIVE,
        ATTEMPT002_VALIDATION_RELATIVE, PC2W_CONTRACT_RELATIVE,
    }
    if not isinstance(frozen, list) or {Path(str(row.get("path"))) for row in frozen if isinstance(row, dict)} != expected_frozen:
        raise RuntimeError("frozen artifact set mismatch")
    for row in frozen:
        relative = Path(str(row.get("path")))
        expected = (row.get("raw_bytes"), row.get("raw_sha256"))
        if file_fact(repo_root / relative) != expected or git_blob_fact(repo_root, head, relative) != expected:
            raise RuntimeError(f"frozen artifact mismatch: {relative}")
    if git_blob_fact(repo_root, parent, RUNNER_RELATIVE) != file_fact(repo_root / RUNNER_RELATIVE):
        raise RuntimeError("runner not frozen in parent")
    if git_blob_fact(repo_root, parent, CONTRACT_RELATIVE) != file_fact(repo_root / CONTRACT_RELATIVE):
        raise RuntimeError("contract not frozen in parent")

    output_root.mkdir(parents=True, exist_ok=False)
    created_at = utc_now()
    passport = material_passport(created_at, auth)
    commands: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}

    def record(command_id: str, argv: list[str], timeout_seconds: int) -> dict[str, Any]:
        receipt, stdout, stderr = run_command(command_id, argv, timeout_seconds)
        commands.append(receipt)
        raw[command_id] = (stdout, stderr)
        return receipt

    before_status_receipt = record("B00_DOCKER_DESKTOP_STATUS_BEFORE", [str(DOCKER), "desktop", "status"], 30)
    before_wsl_receipt = record("B01_WSL_LIST_BEFORE", [str(WSL), "--list", "--verbose"], 30)
    before_daemon_receipt = record(
        "B02_DAEMON_VERSION_BEFORE",
        [str(DOCKER), "version", "--format", "{{json .Server}}"],
        30,
    )

    before_status = parse_status(raw["B00_DOCKER_DESKTOP_STATUS_BEFORE"][0]) if command_ok(before_status_receipt) else None
    before_wsl, before_wsl_parse_complete = (
        parse_wsl_list(raw["B01_WSL_LIST_BEFORE"][0])
        if command_ok(before_wsl_receipt)
        else ([], False)
    )
    before_daemon_unavailable = daemon_is_specifically_unavailable(
        before_daemon_receipt, *raw["B02_DAEMON_VERSION_BEFORE"]
    )
    before_daemon_known = command_ok(before_daemon_receipt) or before_daemon_unavailable
    pre_queries_complete = (
        before_status in {"running", "stopped"}
        and command_ok(before_wsl_receipt)
        and before_wsl_parse_complete
        and len(before_wsl) > 0
        and distro_state(before_wsl, "docker-desktop") in {"Running", "Stopped"}
        and before_daemon_known
    )
    baseline_already_stopped = (
        pre_queries_complete
        and before_status == "stopped"
        and before_daemon_unavailable
        and distro_state(before_wsl, "docker-desktop") == "Stopped"
        and all(row.get("state") == "Stopped" for row in before_wsl)
    )

    restoration_attempted = False
    docker_stop_attempts = 0
    wsl_shutdown_attempts = 0
    if pre_queries_complete and not baseline_already_stopped:
        restoration_attempted = True
        try:
            docker_stop_attempts = 1
            record("B03_DOCKER_DESKTOP_STOP_ONCE", [str(DOCKER), "desktop", "stop"], 180)
        finally:
            wsl_shutdown_attempts = 1
            record("B04_WSL_SHUTDOWN_ONCE", [str(WSL), "--shutdown"], 180)

    after_status_receipt = record("B05_DOCKER_DESKTOP_STATUS_AFTER", [str(DOCKER), "desktop", "status"], 30)
    after_daemon_receipt = record(
        "B06_DAEMON_VERSION_AFTER",
        [str(DOCKER), "version", "--format", "{{json .Server}}"],
        30,
    )
    after_wsl_receipt = record("B07_WSL_LIST_AFTER", [str(WSL), "--list", "--verbose"], 30)

    after_status = parse_status(raw["B05_DOCKER_DESKTOP_STATUS_AFTER"][0]) if command_ok(after_status_receipt) else None
    after_wsl, after_wsl_parse_complete = (
        parse_wsl_list(raw["B07_WSL_LIST_AFTER"][0])
        if command_ok(after_wsl_receipt)
        else ([], False)
    )
    after_daemon_unavailable = daemon_is_specifically_unavailable(
        after_daemon_receipt, *raw["B06_DAEMON_VERSION_AFTER"]
    )
    post_baseline_stopped = (
        after_status == "stopped"
        and after_daemon_unavailable
        and command_ok(after_wsl_receipt)
        and after_wsl_parse_complete
        and len(after_wsl) > 0
        and distro_state(after_wsl, "docker-desktop") == "Stopped"
        and all(row.get("state") == "Stopped" for row in after_wsl)
    )
    command_ids = [row["command_id"] for row in commands]
    prohibited_command_issued = any(
        token in {"start", "pull", "build", "create", "run", "exec"}
        for row in commands for token in [item.casefold() for item in row.get("argv", [])[1:]]
    )
    verdict = (
        "PASS_PC2W_P1_ATTEMPT003_BASELINE_RESTORED"
        if pre_queries_complete
        and post_baseline_stopped
        and docker_stop_attempts <= 1
        and wsl_shutdown_attempts <= 1
        and not prohibited_command_issued
        else "FAIL_CLOSED_PC2W_P1_ATTEMPT003_BASELINE_NOT_RESTORED"
    )

    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-baseline-command-receipts-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-BASELINE",
        "created_at": created_at,
        "commands": commands,
        "command_ids": command_ids,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    receipt_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-baseline-restoration-receipt-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-BASELINE",
        "created_at": created_at,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "output_root": str(output_root),
        "before": {
            "docker_desktop_status": before_status,
            "docker_desktop_wsl_distro": distro_state(before_wsl, "docker-desktop"),
            "all_wsl_rows": before_wsl,
            "wsl_list_parse_complete": before_wsl_parse_complete,
            "daemon_specifically_unavailable": before_daemon_unavailable,
        },
        "after": {
            "docker_desktop_status": after_status,
            "docker_desktop_wsl_distro": distro_state(after_wsl, "docker-desktop"),
            "all_wsl_rows": after_wsl,
            "wsl_list_parse_complete": after_wsl_parse_complete,
            "daemon_specifically_unavailable": after_daemon_unavailable,
        },
        "pre_queries_complete": pre_queries_complete,
        "baseline_already_stopped": baseline_already_stopped,
        "restoration_attempted": restoration_attempted,
        "docker_stop_attempts": docker_stop_attempts,
        "wsl_shutdown_attempts": wsl_shutdown_attempts,
        "automatic_retry_count": 0,
        "post_baseline_stopped": post_baseline_stopped,
        "prohibited_command_issued": prohibited_command_issued,
        "verdict": verdict,
        "image_pull_or_build_performed": False,
        "container_create_or_run_performed": False,
        "settings_changed": False,
        "download_performed": False,
        "materialization_performed": False,
        "scientific_execution_performed": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-baseline-handoff-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-BASELINE",
        "verdict": verdict,
        "next_gate": (
            "ATTEMPT003_QUERY_PROBE_STATIC_AUDIT"
            if verdict == "PASS_PC2W_P1_ATTEMPT003_BASELINE_RESTORED"
            else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
        "truth_state": {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0},
    }
    write_json(output_root / "baseline_command_receipts.json", command_document)
    write_json(output_root / "baseline_restoration_receipt.json", receipt_document)
    write_json(output_root / "baseline_handoff.json", handoff)
    entries = list(output_root.iterdir())
    if {path.name for path in entries} != EXPECTED_OUTPUT_FILES or not all(path.is_file() for path in entries):
        raise RuntimeError("exact baseline output set violation")

    print(json.dumps({
        "verdict": verdict,
        "output_root": str(output_root),
        "commands_recorded": len(commands),
        "docker_stop_attempts": docker_stop_attempts,
        "wsl_shutdown_attempts": wsl_shutdown_attempts,
        "automatic_retry_count": 0,
    }, indent=2))
    return 0 if verdict == "PASS_PC2W_P1_ATTEMPT003_BASELINE_RESTORED" else 1


if __name__ == "__main__":
    sys.exit(main())
