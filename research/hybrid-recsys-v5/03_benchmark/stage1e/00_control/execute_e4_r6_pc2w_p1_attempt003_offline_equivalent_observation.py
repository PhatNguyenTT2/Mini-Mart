#!/usr/bin/env python3
"""Observe the PC2W-P1 attempt-003 offline-equivalent baseline exactly once."""

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
POWERSHELL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

EXPECTED_EXECUTABLES = {
    DOCKER: (42748848, "0cdb9dea2e39a0a29e5dc3f9732f572dc140547b28deab0495589b4f79b31ca1"),
    DOCKER_DESKTOP: (13209520, "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce"),
    WSL: (278528, "7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757"),
    POWERSHELL: (454656, "7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5"),
}

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_contract.json"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization.json"
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json"
BASELINE_VALIDATION_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_baseline_validation_receipt.json"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-offline-equivalent-observation"
)
EXPECTED_HEAD_CHANGE_SET = {AUTH_RELATIVE.as_posix(), DISPATCH_RELATIVE.as_posix()}
EXPECTED_OUTPUT_FILES = {
    "observation_command_receipts.json",
    "offline_equivalent_observation_receipt.json",
    "observation_handoff.json",
}
EXPECTED_COMMAND_IDS = [
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY",
    "O01_WSL_LIST_VERBOSE",
    "O02_WSL_LIST_RUNNING_QUIET",
    "O03_DAEMON_VERSION_SERVER_ONLY",
    "O04_DOCKER_RUNTIME_PROCESS_NAMES_ONLY",
]
TARGET_RUNTIME_PROCESSES = {
    "docker desktop",
    "com.docker.backend",
    "com.docker.build",
    "com.docker.proxy",
    "dockerd",
    "vpnkit",
    "wslrelay",
}
PROCESS_QUERY = (
    "$ErrorActionPreference='Stop';"
    "$target=@('Docker Desktop','com.docker.backend','com.docker.build','com.docker.proxy','dockerd','vpnkit','wslrelay');"
    "$found=@(Get-Process -Name $target -ErrorAction SilentlyContinue | "
    "ForEach-Object { $_.ProcessName } | Sort-Object -Unique);"
    "[pscustomobject]@{runtime_processes=$found} | ConvertTo-Json -Compress"
)
DAEMON_PIPE_MARKERS = ("dockerdesktoplinuxengine", "//./pipe/dockerdesktoplinuxengine")
DAEMON_PIPE_MISSING_MARKERS = ("the system cannot find the file specified", "no such file or directory")
PERMISSION_ERROR_MARKERS = ("access is denied", "permission denied", "unauthorized")


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
            raise DuplicateKeyError(f"case-colliding key: {folded[case]} vs {key}")
        result[key] = value
        folded[case] = key
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError(f"non-object JSON root: {path}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, check=False, timeout=timeout_seconds,
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
    return receipt.get("exit_code") == 0 and receipt.get("timed_out") is False and receipt.get("spawn_exception_type") is None


def parse_status_text(stdout: bytes, stderr: bytes) -> str | None:
    text = (decode_output(stdout) + "\n" + decode_output(stderr)).casefold()
    matches = set(re.findall(r"\b(running|stopped)\b", text))
    return next(iter(matches)) if len(matches) == 1 else None


def classify_status(receipt: dict[str, Any], stdout: bytes, stderr: bytes) -> str:
    if receipt.get("timed_out") or receipt.get("spawn_exception_type") is not None:
        return "UNCLASSIFIED_SPAWN_OR_TIMEOUT"
    parsed = parse_status_text(stdout, stderr)
    if parsed == "running":
        return "RUNNING_EXACT"
    if parsed == "stopped" and receipt.get("exit_code") == 0:
        return "STOPPED_EXACT"
    if receipt.get("exit_code") == 0:
        return "UNCLASSIFIED_ZERO_EXIT"
    if isinstance(receipt.get("exit_code"), int):
        return "UNCLASSIFIED_NONZERO_HASH_ONLY"
    return "UNCLASSIFIED_NO_EXIT"


def parse_wsl_verbose(value: bytes) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    header_seen = False
    for raw_line in decode_output(value).replace("\x00", "").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue
        folded = line.casefold()
        if "name" in folded and "state" in folded and "version" in folded:
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
        rows.append({"name": name, "state": match.group(2).title(), "version": int(match.group(3))})
    if not header_seen or not rows:
        return [], False
    return sorted(rows, key=lambda row: str(row["name"]).casefold()), True


def parse_wsl_running_quiet(value: bytes) -> tuple[list[str], bool]:
    text = decode_output(value).replace("\x00", "").lstrip("\ufeff")
    if "\ufffd" in text or any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        return [], False
    names = [line.strip() for line in text.splitlines() if line.strip()]
    folded = [name.casefold() for name in names]
    if len(folded) != len(set(folded)):
        return [], False
    return names, True


def parse_process_inventory(value: bytes) -> tuple[list[str], bool]:
    try:
        parsed = json.loads(decode_output(value), object_pairs_hook=strict_pairs)
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return [], False
    if not isinstance(parsed, dict) or set(parsed) != {"runtime_processes"}:
        return [], False
    values = parsed.get("runtime_processes")
    if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() == item and item for item in values):
        return [], False
    folded = [item.casefold() for item in values]
    if len(folded) != len(set(folded)) or not set(folded).issubset(TARGET_RUNTIME_PROCESSES):
        return [], False
    return sorted(folded), True


def distro_state(rows: list[dict[str, Any]], name: str) -> str | None:
    matches = [str(row["state"]) for row in rows if str(row["name"]).casefold() == name.casefold()]
    return matches[0] if len(matches) == 1 else None


def daemon_is_specifically_unavailable(receipt: dict[str, Any], stdout: bytes, stderr: bytes) -> bool:
    if receipt.get("timed_out") or receipt.get("spawn_exception_type") is not None:
        return False
    if not isinstance(receipt.get("exit_code"), int) or receipt.get("exit_code") == 0:
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
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization_v1",
            "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_contract_v1",
            "stage1e_e4_r6_pc2w_p1_attempt003_baseline_validation_v1",
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
    for executable, expected in EXPECTED_EXECUTABLES.items():
        if not executable.is_file() or file_fact(executable) != expected:
            raise RuntimeError(f"executable identity mismatch: {executable}")

    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_head = str(args.expected_head).casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head) or head != expected_head:
        raise RuntimeError("exact execution HEAD mismatch")
    parents = git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parents) != 2:
        raise RuntimeError("execution checkpoint must have exactly one parent")
    parent = parents[1].casefold()
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean")
    changed = set(filter(None, git(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()))
    if changed != EXPECTED_HEAD_CHANGE_SET:
        raise RuntimeError(f"execution checkpoint change set mismatch: {sorted(changed)}")

    auth = load_json(repo_root / AUTH_RELATIVE)
    dispatch = load_json(repo_root / DISPATCH_RELATIVE)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    baseline_validation = load_json(repo_root / BASELINE_VALIDATION_RELATIVE)
    if auth.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-authorization-1.0":
        raise RuntimeError("authorization schema mismatch")
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-dispatch-1.0":
        raise RuntimeError("dispatch schema mismatch")
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-observation-contract-1.0":
        raise RuntimeError("contract schema mismatch")
    if baseline_validation.get("attempt_result", {}).get("attempt003_execution_opened") is not False:
        raise RuntimeError("prior validation no longer proves attempt-003 unopened")
    if auth.get("entry_checkpoint", "").casefold() != parent or dispatch.get("runner_checkpoint", "").casefold() != parent:
        raise RuntimeError("runner checkpoint binding mismatch")
    if Path(auth.get("authorized_output_root", "")).resolve() != output_root:
        raise RuntimeError("authorization output root mismatch")
    binding = dispatch.get("execution_binding", {})
    if Path(binding.get("output_root", "")).resolve() != output_root:
        raise RuntimeError("dispatch output root mismatch")
    if binding.get("expected_output_files") != sorted(EXPECTED_OUTPUT_FILES):
        raise RuntimeError("dispatch expected output set mismatch")
    decision = auth.get("user_decision", {})
    if decision.get("decision") != "AUTHORIZE_ATTEMPT003_OFFLINE_EQUIVALENT_OBSERVATION_AND_CONDITIONAL_EXECUTION":
        raise RuntimeError("user decision mismatch")
    if decision.get("offline_equivalent_observation_authorized") is not True or decision.get("attempt003_execution_authorized_on_pass") is not True:
        raise RuntimeError("authorization scope incomplete")
    for key in (
        "automatic_retry_authorized", "docker_desktop_start_or_stop_authorized_in_observation",
        "wsl_shutdown_or_terminate_authorized_in_observation", "image_or_container_mutation_authorized",
        "settings_change_authorized", "install_or_download_authorized", "materialization_authorized",
        "training_authorized", "evaluation_authorized", "test_access_authorized",
    ):
        if decision.get(key) is not False:
            raise RuntimeError(f"forbidden authorization flag changed: {key}")

    frozen = dispatch.get("frozen_artifacts")
    expected_frozen = {RUNNER_RELATIVE, CONTRACT_RELATIVE, AUTH_RELATIVE, BASELINE_VALIDATION_RELATIVE}
    if not isinstance(frozen, list) or {Path(str(row.get("path"))) for row in frozen if isinstance(row, dict)} != expected_frozen:
        raise RuntimeError("frozen artifact set mismatch")
    for row in frozen:
        relative = Path(str(row.get("path")))
        expected = (row.get("raw_bytes"), row.get("raw_sha256"))
        if file_fact(repo_root / relative) != expected or git_blob_fact(repo_root, head, relative) != expected:
            raise RuntimeError(f"frozen artifact mismatch: {relative}")
    for relative in (RUNNER_RELATIVE, CONTRACT_RELATIVE):
        if git_blob_fact(repo_root, parent, relative) != file_fact(repo_root / relative):
            raise RuntimeError(f"artifact not frozen in runner checkpoint: {relative}")

    output_root.mkdir(parents=True, exist_ok=False)
    created_at = utc_now()
    passport = material_passport(created_at, auth)
    commands: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}

    def record(command_id: str, argv: list[str], timeout_seconds: int = 30) -> dict[str, Any]:
        receipt, stdout, stderr = run_command(command_id, argv, timeout_seconds)
        commands.append(receipt)
        raw[command_id] = (stdout, stderr)
        return receipt

    status_receipt = record(EXPECTED_COMMAND_IDS[0], [str(DOCKER), "desktop", "status"])
    wsl_verbose_receipt = record(EXPECTED_COMMAND_IDS[1], [str(WSL), "--list", "--verbose"])
    wsl_running_receipt = record(EXPECTED_COMMAND_IDS[2], [str(WSL), "--list", "--running", "--quiet"])
    daemon_receipt = record(EXPECTED_COMMAND_IDS[3], [str(DOCKER), "version", "--format", "{{json .Server}}"])
    process_receipt = record(
        EXPECTED_COMMAND_IDS[4],
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PROCESS_QUERY],
    )

    status_classification = classify_status(status_receipt, *raw[EXPECTED_COMMAND_IDS[0]])
    wsl_rows, wsl_verbose_complete = (
        parse_wsl_verbose(raw[EXPECTED_COMMAND_IDS[1]][0]) if command_ok(wsl_verbose_receipt) else ([], False)
    )
    running_names, wsl_running_complete = (
        parse_wsl_running_quiet(raw[EXPECTED_COMMAND_IDS[2]][0]) if command_ok(wsl_running_receipt) else ([], False)
    )
    daemon_unavailable = daemon_is_specifically_unavailable(daemon_receipt, *raw[EXPECTED_COMMAND_IDS[3]])
    runtime_processes, process_inventory_complete = (
        parse_process_inventory(raw[EXPECTED_COMMAND_IDS[4]][0]) if command_ok(process_receipt) else ([], False)
    )
    independent_lanes_pass = {
        "wsl_inventory_all_stopped": (
            wsl_verbose_complete
            and distro_state(wsl_rows, "docker-desktop") == "Stopped"
            and all(row["state"] == "Stopped" for row in wsl_rows)
        ),
        "wsl_running_inventory_empty": wsl_running_complete and not running_names,
        "daemon_specifically_unavailable": daemon_unavailable,
        "target_runtime_process_inventory_empty": process_inventory_complete and not runtime_processes,
    }
    status_lane_admissible = status_classification in {"STOPPED_EXACT", "UNCLASSIFIED_NONZERO_HASH_ONLY"}
    command_ids = [row["command_id"] for row in commands]
    exact_command_sequence = command_ids == EXPECTED_COMMAND_IDS and len(set(command_ids)) == len(command_ids)
    pass_gate = status_lane_admissible and all(independent_lanes_pass.values()) and exact_command_sequence
    verdict = (
        "PASS_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_BASELINE"
        if pass_gate else "FAIL_CLOSED_PC2W_P1_ATTEMPT003_OFFLINE_EQUIVALENT_BASELINE"
    )

    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-command-receipts-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-OFFLINE-EQUIVALENT-OBSERVATION",
        "created_at": created_at,
        "commands": commands,
        "command_ids": command_ids,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    receipt_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-observation-receipt-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-OFFLINE-EQUIVALENT-OBSERVATION",
        "created_at": created_at,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "output_root": str(output_root),
        "docker_desktop_status_lane": {
            "classification": status_classification,
            "advisory_only": True,
            "unclassified_nonzero_is_not_relabelled_stopped": True,
            "admissible_without_independent_lanes": False,
        },
        "wsl_inventory": {
            "parse_complete": wsl_verbose_complete,
            "rows": wsl_rows,
            "docker_desktop_state": distro_state(wsl_rows, "docker-desktop"),
        },
        "wsl_running_inventory": {"parse_complete": wsl_running_complete, "running_names": running_names},
        "daemon_specifically_unavailable": daemon_unavailable,
        "runtime_process_inventory": {"parse_complete": process_inventory_complete, "runtime_processes": runtime_processes},
        "independent_lanes_pass": independent_lanes_pass,
        "status_lane_admissible": status_lane_admissible,
        "exact_command_sequence": exact_command_sequence,
        "automatic_retry_count": 0,
        "state_mutation_command_issued": False,
        "verdict": verdict,
        "image_or_container_mutation_performed": False,
        "settings_changed": False,
        "install_or_download_performed": False,
        "materialization_performed": False,
        "scientific_execution_performed": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-offline-equivalent-handoff-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-OFFLINE-EQUIVALENT-OBSERVATION",
        "verdict": verdict,
        "next_gate": (
            "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT"
            if pass_gate else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
        "truth_state": {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0},
    }
    write_json(output_root / "observation_command_receipts.json", command_document)
    write_json(output_root / "offline_equivalent_observation_receipt.json", receipt_document)
    write_json(output_root / "observation_handoff.json", handoff)
    entries = list(output_root.iterdir())
    if {path.name for path in entries} != EXPECTED_OUTPUT_FILES or not all(path.is_file() for path in entries):
        raise RuntimeError("exact observation output set violation")

    print(json.dumps({
        "verdict": verdict,
        "output_root": str(output_root),
        "commands_recorded": len(commands),
        "status_classification": status_classification,
        "independent_lanes_pass": independent_lanes_pass,
        "automatic_retry_count": 0,
    }, indent=2))
    return 0 if pass_gate else 1


if __name__ == "__main__":
    sys.exit(main())
