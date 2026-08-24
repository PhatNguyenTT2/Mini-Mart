#!/usr/bin/env python3
"""Observe the PC2W-P1 attempt-003 native offline baseline exactly once."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOCKER = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
WSL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wsl.exe"
POWERSHELL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
PYTHON = Path(r"C:\Program Files\Python311\python.exe")

EXPECTED_EXECUTABLES = {
    DOCKER: (42748848, "0cdb9dea2e39a0a29e5dc3f9732f572dc140547b28deab0495589b4f79b31ca1"),
    DOCKER_DESKTOP: (13209520, "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce"),
    WSL: (278528, "7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757"),
    POWERSHELL: (454656, "7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5"),
    PYTHON: (103192, "5f7b89a612c9b8af1d6456cdfcd1dbe5ca630849e79aebced9bee9a6694952ec"),
}

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_offline_equivalent_observation_contract.json"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_offline_equivalent_authorization.json"
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_dispatch.json"
PRIOR_OBSERVATION_VALIDATION_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_receipt.json"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003-native-offline-observation-v5"
)
EXPECTED_HEAD_CHANGE_SET = {AUTH_RELATIVE.as_posix(), DISPATCH_RELATIVE.as_posix()}
EXPECTED_OUTPUT_FILES = {
    "observation_command_receipts.json",
    "offline_equivalent_observation_receipt.json",
    "observation_handoff.json",
}
EXPECTED_COMMAND_IDS = [
    "O00_DOCKER_DESKTOP_STATUS_ADVISORY",
    "O01A_WSL_LIST_VERBOSE",
    "O02A_WSL_LIST_RUNNING_QUIET",
    "O03A_DOCKER_RUNTIME_PROCESS_NAMES_ONLY",
    "O01B_WSL_LIST_VERBOSE_STABILITY_BARRIER",
    "O02B_WSL_LIST_RUNNING_QUIET_STABILITY_BARRIER",
    "O03B_DOCKER_RUNTIME_PROCESS_NAMES_ONLY_STABILITY_BARRIER",
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
    "$target=@('Docker Desktop.exe','com.docker.backend.exe','com.docker.build.exe','com.docker.proxy.exe','dockerd.exe','vpnkit.exe','wslrelay.exe');"
    "$all=@(Get-CimInstance -ClassName Win32_Process -Property Name -ErrorAction Stop);"
    "$found=@($all | Where-Object { $target -contains $_.Name } | "
    "ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_.Name) } | Sort-Object -Unique);"
    "[pscustomobject]@{runtime_processes=$found} | ConvertTo-Json -Compress"
)
DESKTOP_LINUX_PIPE = r"\\.\pipe\dockerDesktopLinuxEngine"
ERROR_FILE_NOT_FOUND = 2


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


def decode_output_strict(value: bytes) -> tuple[str, bool]:
    if not value:
        return "", True
    try:
        if value.count(b"\x00") > max(1, len(value) // 8):
            text = value.decode("utf-16-le", errors="strict")
        else:
            text = value.decode("utf-8", errors="strict")
        if "\ufffd" in text or any(
            char not in "\r\n\t" and unicodedata.category(char).startswith("C")
            for char in text
        ):
            return "", False
        return text, True
    except UnicodeDecodeError:
        return "", False


def git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo_root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_blob_fact(repo_root: Path, revision: str, relative: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative.as_posix()}"], cwd=repo_root,
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


def parse_status_text(stdout: bytes, stderr: bytes) -> tuple[str | None, bool]:
    stdout_text, stdout_complete = decode_output_strict(stdout)
    stderr_text, stderr_complete = decode_output_strict(stderr)
    if not stdout_complete or not stderr_complete:
        return None, False
    text = (stdout_text + "\n" + stderr_text).casefold()
    matches = set(re.findall(r"\b(running|stopped)\b", text))
    if "running" in matches:
        return "running", True
    if matches == {"stopped"}:
        return "stopped", True
    return None, True


def classify_status(receipt: dict[str, Any], stdout: bytes, stderr: bytes) -> str:
    if receipt.get("timed_out") or receipt.get("spawn_exception_type") is not None:
        return "UNCLASSIFIED_SPAWN_OR_TIMEOUT"
    parsed, decoded = parse_status_text(stdout, stderr)
    if not decoded:
        return "UNCLASSIFIED_INVALID_ENCODING"
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
    text, decoded = decode_output_strict(value)
    if not decoded:
        return [], False
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    header_seen = False
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue
        if re.fullmatch(r"NAME\s+STATE\s+VERSION", line, re.IGNORECASE):
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
    text, decoded = decode_output_strict(value)
    text = text.lstrip("\ufeff")
    if not decoded:
        return [], False
    names = [line.strip() for line in text.splitlines() if line.strip()]
    folded = [name.casefold() for name in names]
    if len(folded) != len(set(folded)):
        return [], False
    return names, True


def parse_process_inventory(value: bytes) -> tuple[list[str], bool]:
    text, decoded = decode_output_strict(value)
    if not decoded:
        return [], False
    try:
        parsed = json.loads(text, object_pairs_hook=strict_pairs)
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


def probe_desktop_linux_pipe() -> dict[str, Any]:
    """Observe named-pipe presence without connecting to a pipe instance."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        wait_named_pipe = kernel32.WaitNamedPipeW
        wait_named_pipe.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        wait_named_pipe.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        available = bool(wait_named_pipe(DESKTOP_LINUX_PIPE, 1))
        error_code = None if available else ctypes.get_last_error()
        return {
            "method": "WaitNamedPipeW_one_millisecond_timeout",
            "timeout_milliseconds": 1,
            "pipe_path_sha256": sha256_bytes(DESKTOP_LINUX_PIPE.encode("utf-8")),
            "available": available,
            "win32_error": error_code,
            "probe_exception_type": None,
        }
    except Exception as exc:
        return {
            "method": "WaitNamedPipeW_one_millisecond_timeout",
            "timeout_milliseconds": 1,
            "pipe_path_sha256": sha256_bytes(DESKTOP_LINUX_PIPE.encode("utf-8")),
            "available": None,
            "win32_error": None,
            "probe_exception_type": type(exc).__name__,
        }


def pipe_is_specifically_absent(probe: dict[str, Any]) -> bool:
    return (
        probe.get("available") is False
        and probe.get("win32_error") == ERROR_FILE_NOT_FOUND
        and probe.get("probe_exception_type") is None
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
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_observation_v5",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_authorization_v5",
            "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_contract_v5",
            "stage1e_e4_r6_pc2w_p1_attempt003_offline_equivalent_validation_v2",
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
    if Path.cwd().resolve() != repo_root:
        raise RuntimeError("working directory is not exact execution repo root")
    if Path(sys.executable).resolve() != PYTHON.resolve() or sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("interpreter identity mismatch")
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
    expected_process_argv = [
        str(PYTHON.resolve()), str((repo_root / RUNNER_RELATIVE).resolve()), "--repo-root", str(repo_root),
        "--expected-head", head,
    ]
    original = list(getattr(sys, "orig_argv", []))
    actual_process_argv = (
        [str(Path(original[0]).resolve()), str(Path(original[1]).resolve()), *original[2:]]
        if len(original) >= 2 else original
    )
    if actual_process_argv != expected_process_argv:
        raise RuntimeError("exact original process argv mismatch; interpreter flags are forbidden")
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
    prior_validation = load_json(repo_root / PRIOR_OBSERVATION_VALIDATION_RELATIVE)
    if auth.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-authorization-5.0":
        raise RuntimeError("authorization schema mismatch")
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-dispatch-5.0":
        raise RuntimeError("dispatch schema mismatch")
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-observation-contract-5.0":
        raise RuntimeError("contract schema mismatch")
    if prior_validation.get("attempt_result", {}).get("attempt003_execution_opened") is not False:
        raise RuntimeError("prior validation no longer proves attempt-003 unopened")
    if prior_validation.get("attempt_result", {}).get("automatic_retry_count") != 0:
        raise RuntimeError("prior validation retry count mismatch")
    if auth.get("entry_checkpoint", "").casefold() != parent or dispatch.get("runner_checkpoint", "").casefold() != parent:
        raise RuntimeError("runner checkpoint binding mismatch")
    if Path(auth.get("authorized_output_root", "")).resolve() != output_root:
        raise RuntimeError("authorization output root mismatch")
    binding = dispatch.get("execution_binding", {})
    if Path(binding.get("output_root", "")).resolve() != output_root:
        raise RuntimeError("dispatch output root mismatch")
    if binding.get("expected_output_files") != sorted(EXPECTED_OUTPUT_FILES):
        raise RuntimeError("dispatch expected output set mismatch")
    if Path(binding.get("working_directory", "")).resolve() != repo_root:
        raise RuntimeError("dispatch working directory mismatch")
    expected_dispatch_argv = [
        str(PYTHON), RUNNER_RELATIVE.as_posix(), "--repo-root", str(repo_root),
        "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    if binding.get("argv") != expected_dispatch_argv:
        raise RuntimeError("dispatch argv binding mismatch")
    interpreter = dispatch.get("interpreter", {})
    if (
        Path(interpreter.get("path", "")).resolve() != PYTHON.resolve()
        or interpreter.get("version") != "3.11.9"
        or (interpreter.get("raw_bytes"), interpreter.get("sha256")) != EXPECTED_EXECUTABLES[PYTHON]
    ):
        raise RuntimeError("dispatch interpreter binding mismatch")
    decision = auth.get("user_decision", {})
    if decision.get("decision") != "AUTHORIZE_ATTEMPT003_NATIVE_OFFLINE_OBSERVATION_V5_AND_CONDITIONAL_EXECUTION":
        raise RuntimeError("user decision mismatch")
    if decision.get("native_offline_observation_v5_authorized") is not True or decision.get("attempt003_execution_authorized_on_pass") is not True:
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
    expected_frozen = {RUNNER_RELATIVE, CONTRACT_RELATIVE, AUTH_RELATIVE, PRIOR_OBSERVATION_VALIDATION_RELATIVE}
    if not isinstance(frozen, list) or {Path(str(row.get("path"))) for row in frozen if isinstance(row, dict)} != expected_frozen:
        raise RuntimeError("frozen artifact set mismatch")
    for row in frozen:
        relative = Path(str(row.get("path")))
        expected = (row.get("git_blob_bytes"), row.get("git_blob_sha256"))
        if git_blob_fact(repo_root, head, relative) != expected:
            raise RuntimeError(f"frozen artifact mismatch: {relative}")
    for relative in (RUNNER_RELATIVE, CONTRACT_RELATIVE):
        if git_blob_fact(repo_root, parent, relative) != git_blob_fact(repo_root, head, relative):
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
    wsl_verbose_receipt_a = record(EXPECTED_COMMAND_IDS[1], [str(WSL), "--list", "--verbose"])
    wsl_running_receipt_a = record(EXPECTED_COMMAND_IDS[2], [str(WSL), "--list", "--running", "--quiet"])
    pipe_probe_a = probe_desktop_linux_pipe()
    process_receipt_a = record(
        EXPECTED_COMMAND_IDS[3],
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PROCESS_QUERY],
    )
    wsl_verbose_receipt_b = record(EXPECTED_COMMAND_IDS[4], [str(WSL), "--list", "--verbose"])
    wsl_running_receipt_b = record(EXPECTED_COMMAND_IDS[5], [str(WSL), "--list", "--running", "--quiet"])
    pipe_probe_b = probe_desktop_linux_pipe()
    process_receipt_b = record(
        EXPECTED_COMMAND_IDS[6],
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PROCESS_QUERY],
    )

    status_classification = classify_status(status_receipt, *raw[EXPECTED_COMMAND_IDS[0]])

    def parse_snapshot(
        verbose_id: str, running_id: str, process_id: str,
        verbose_receipt: dict[str, Any], running_receipt: dict[str, Any],
        process_receipt: dict[str, Any], pipe_probe: dict[str, Any],
    ) -> dict[str, Any]:
        wsl_rows, wsl_complete = (
            parse_wsl_verbose(raw[verbose_id][0]) if command_ok(verbose_receipt) else ([], False)
        )
        running_names, running_complete = (
            parse_wsl_running_quiet(raw[running_id][0]) if command_ok(running_receipt) else ([], False)
        )
        runtime_processes, process_complete = (
            parse_process_inventory(raw[process_id][0]) if command_ok(process_receipt) else ([], False)
        )
        lanes = {
            "wsl_inventory_all_stopped": (
                wsl_complete
                and distro_state(wsl_rows, "docker-desktop") == "Stopped"
                and all(row["state"] == "Stopped" for row in wsl_rows)
            ),
            "wsl_running_inventory_empty": running_complete and not running_names,
            "desktop_linux_named_pipe_specifically_absent_win32_error_2": pipe_is_specifically_absent(pipe_probe),
            "target_runtime_process_inventory_empty": process_complete and not runtime_processes,
        }
        return {
            "wsl_inventory": {
                "parse_complete": wsl_complete,
                "rows": wsl_rows,
                "docker_desktop_state": distro_state(wsl_rows, "docker-desktop"),
            },
            "wsl_running_inventory": {"parse_complete": running_complete, "running_names": running_names},
            "desktop_linux_named_pipe_probe": pipe_probe,
            "runtime_process_inventory": {
                "parse_complete": process_complete,
                "runtime_processes": runtime_processes,
            },
            "lanes_pass": lanes,
        }

    snapshot_a = parse_snapshot(
        EXPECTED_COMMAND_IDS[1], EXPECTED_COMMAND_IDS[2], EXPECTED_COMMAND_IDS[3],
        wsl_verbose_receipt_a, wsl_running_receipt_a, process_receipt_a, pipe_probe_a,
    )
    snapshot_b = parse_snapshot(
        EXPECTED_COMMAND_IDS[4], EXPECTED_COMMAND_IDS[5], EXPECTED_COMMAND_IDS[6],
        wsl_verbose_receipt_b, wsl_running_receipt_b, process_receipt_b, pipe_probe_b,
    )
    independent_lanes_pass = {
        "snapshot_a_all_native_lanes": all(snapshot_a["lanes_pass"].values()),
        "snapshot_b_all_native_lanes": all(snapshot_b["lanes_pass"].values()),
        "wsl_inventory_stable_across_barrier": snapshot_a["wsl_inventory"] == snapshot_b["wsl_inventory"],
        "running_inventory_stable_across_barrier": snapshot_a["wsl_running_inventory"] == snapshot_b["wsl_running_inventory"],
        "runtime_process_inventory_stable_across_barrier": snapshot_a["runtime_process_inventory"] == snapshot_b["runtime_process_inventory"],
        "named_pipe_absence_stable_across_barrier": (
            pipe_is_specifically_absent(pipe_probe_a) and pipe_is_specifically_absent(pipe_probe_b)
        ),
    }
    command_ids = [row["command_id"] for row in commands]
    exact_command_sequence = command_ids == EXPECTED_COMMAND_IDS and len(set(command_ids)) == len(command_ids)
    pass_gate = all(independent_lanes_pass.values()) and exact_command_sequence
    verdict = (
        "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_BASELINE_V5"
        if pass_gate else "FAIL_CLOSED_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_BASELINE_V5"
    )

    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-command-receipts-5.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-NATIVE-OFFLINE-OBSERVATION-V5",
        "created_at": created_at,
        "commands": commands,
        "command_ids": command_ids,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    receipt_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-observation-receipt-5.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-NATIVE-OFFLINE-OBSERVATION-V5",
        "created_at": created_at,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "output_root": str(output_root),
        "docker_desktop_status_lane": {
            "classification": status_classification,
            "advisory_only": True,
            "admission_authority": False,
            "cannot_veto_or_admit_native_gate": True,
        },
        "snapshot_a": snapshot_a,
        "snapshot_b_stability_barrier": snapshot_b,
        "independent_lanes_pass": independent_lanes_pass,
        "observation_is_not_sufficient_without_attempt003_immediate_pre_gate_replay": True,
        "status_lane_used_for_admission": False,
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-native-offline-handoff-5.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003-NATIVE-OFFLINE-OBSERVATION-V5",
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
