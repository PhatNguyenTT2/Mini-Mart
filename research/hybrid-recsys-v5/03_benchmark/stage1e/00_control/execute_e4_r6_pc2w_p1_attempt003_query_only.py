#!/usr/bin/env python3
"""Run PC2W-P1 attempt-003 as one fail-closed start/query-only/stop probe.

This runner is fail-closed: it performs no retry, never pulls/builds/runs a
container, replays the native offline gate immediately before startup, and
always reaches the single stop attempt after a start attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation as native_gate


DOCKER = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
WSL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wsl.exe"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
PYTHON = Path(r"C:\Program Files\Python311\python.exe")
EXPECTED_EXECUTABLES = native_gate.EXPECTED_EXECUTABLES

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_query_only.py"
NATIVE_HELPER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt003_offline_equivalent_observation.py"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_user_authorization_and_model_override.json"
REQUIREMENTS_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt003_query_only_contract.json"
NATIVE_VALIDATION_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_native_offline_validation_receipt.json"
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_attempt003_query_only_dispatch.json"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-003"
)
EXPECTED_HEAD_CHANGE_SET = {AUTH_RELATIVE.as_posix(), DISPATCH_RELATIVE.as_posix()}
EXPECTED_OUTPUT_FILES = {
    "command_receipts.json",
    "runtime_inventory.json",
    "p1_execution_receipt.json",
    "p1_handoff.json",
}
PROHIBITED_DOCKER_SUBCOMMANDS = {
    "pull", "build", "create", "run", "exec", "commit", "import", "load",
    "tag", "push", "login", "logout", "rm", "rmi", "prune", "restart",
    "start", "kill", "pause", "unpause", "rename", "update", "cp",
}
PRE_START_PROCESS_QUERY = native_gate.PROCESS_QUERY
POST_STOP_PROCESS_QUERY = native_gate.PROCESS_QUERY
EXPECTED_COMMAND_IDS = [
    "A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE",
    "A01_WSL_LIST_VERBOSE_PRE_GATE",
    "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE",
    "A03_RUNTIME_PROCESS_NAMES_PRE_GATE",
    "A04_WSL_VERSION_IDENTITY",
    "A05_WINDOWS_IDENTITY",
    "A06_DOCKER_DESKTOP_FILE_IDENTITY",
    "A07_DOCKER_DESKTOP_START_ONCE",
    "A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING",
    "A09_CONTAINER_LIST_INITIAL",
    "A10_IMAGE_LIST_INITIAL",
    "A11_DOCKER_VERSION",
    "A12_DOCKER_INFO",
    "A13_CONTEXT_INSPECT",
    "A14_SYSTEM_DF",
    "A15_WSL_LIST_VERBOSE_DURING",
    "A16_PROCESS_INVENTORY_DURING",
    "A17_NETWORK_CONNECTION_INVENTORY_DURING",
    "A18_CONTAINER_LIST_FINAL",
    "A19_IMAGE_LIST_FINAL",
    "A20_DOCKER_EVENTS_BEFORE_STOP",
    "A21_DOCKER_DESKTOP_STOP_ONCE",
    "A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER",
    "A23_WSL_LIST_VERBOSE_POST_A",
    "A24_WSL_LIST_RUNNING_QUIET_POST_A",
    "A25_RUNTIME_PROCESS_NAMES_POST_A",
    "A26_WSL_LIST_VERBOSE_POST_B",
    "A27_WSL_LIST_RUNNING_QUIET_POST_B",
    "A28_RUNTIME_PROCESS_NAMES_POST_B",
]


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


def run_command(
    command_id: str, argv: list[str], *, timeout_seconds: int
) -> tuple[dict[str, Any], bytes, bytes]:
    started_at = utc_now()
    start_monotonic = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    stdout = b""
    stderr = b""
    exception_type: str | None = None
    exception_sha256: str | None = None
    try:
        completed = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, check=False,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        timed_out = True
    except Exception as exc:  # retain control so the finally-stop path still runs
        exception_type = type(exc).__name__
        exception_sha256 = sha256_bytes(str(exc).encode("utf-8"))
    receipt = {
        "command_id": command_id,
        "argv": argv,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "started_at": started_at,
        "ended_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - start_monotonic, 6),
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


def parse_json_output(value: bytes) -> Any:
    text, complete = native_gate.decode_output_strict(value)
    if not complete:
        raise ValueError("invalid output encoding")
    text = text.strip()
    return json.loads(text, object_pairs_hook=strict_pairs) if text else None


def parse_json_lines(value: bytes) -> list[Any]:
    rows: list[Any] = []
    text, complete = native_gate.decode_output_strict(value)
    if not complete:
        raise ValueError("invalid output encoding")
    for line in text.splitlines():
        if line.strip():
            rows.append(json.loads(line, object_pairs_hook=strict_pairs))
    return rows


def parse_wsl_list(value: bytes) -> list[dict[str, Any]]:
    rows, complete = native_gate.parse_wsl_verbose(value)
    if not complete:
        raise ValueError("strict WSL verbose parse incomplete")
    return rows


def parse_wsl_running(value: bytes) -> list[str]:
    names, complete = native_gate.parse_wsl_running_quiet(value)
    if not complete:
        raise ValueError("strict WSL running parse incomplete")
    return names


def parse_runtime_processes(value: bytes) -> list[str]:
    names, complete = native_gate.parse_process_inventory(value)
    if not complete:
        raise ValueError("strict runtime-process parse incomplete")
    return names


def parse_wsl_version(value: bytes) -> dict[str, str]:
    text, complete = native_gate.decode_output_strict(value)
    if not complete:
        raise ValueError("invalid WSL version encoding")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, item = line.split(":", 1)
            normalized = key.strip().casefold().replace(" ", "_")
            if normalized in {
                "wsl_version", "kernel_version", "wslg_version", "windows_version"
            }:
                if normalized in result:
                    raise ValueError(f"duplicate WSL version key: {normalized}")
                result[normalized] = item.strip()
    return result


def distro_state(rows: list[dict[str, Any]], name: str) -> str | None:
    matches = [
        str(row.get("state"))
        for row in rows
        if str(row.get("name", "")).casefold() == name.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def disk_snapshot() -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for drive in ("C:\\", "E:\\"):
        usage = shutil.disk_usage(drive)
        result[drive[0].lower()] = {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        }
    return result


def docker_subcommand_is_allowed(argv: list[str]) -> bool:
    if not argv or Path(argv[0]).resolve() != DOCKER.resolve():
        return True
    tokens = [token.casefold() for token in argv[1:]]
    if tokens[:2] in (
        ["desktop", "start"], ["desktop", "stop"], ["desktop", "status"]
    ):
        return True
    return not any(token in PROHIBITED_DOCKER_SUBCOMMANDS for token in tokens)


def material_passport(created_at: str, auth: dict[str, Any]) -> dict[str, Any]:
    intake = auth.get("material_passport", {}).get("experiment_intake_declaration")
    if not isinstance(intake, dict):
        raise RuntimeError("authorization Material Passport intake declaration missing")
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_attempt003_query_only_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_attempt003_user_authorization_standard_v1",
            "stage1e_e4_r6_pc2w_p1_requirements_v1",
            "stage1e_e4_r6_pc2w_p1_attempt003_native_offline_v5_validated",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": intake,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sanitize_context(value: Any) -> dict[str, Any]:
    row = (
        value[0]
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict)
        else {}
    )
    endpoint = (row.get("Endpoints") or {}).get("docker") or {}
    metadata = row.get("Metadata") or {}
    return {
        "Name": row.get("Name"),
        "Description": metadata.get("Description"),
        "DockerEndpointHost": endpoint.get("Host"),
        "DockerEndpointSkipTLSVerify": endpoint.get("SkipTLSVerify"),
        "TLSMaterialConfigured": bool(row.get("TLSMaterial")),
        "StorageConfigured": bool(row.get("Storage")),
    }


def sanitize_rows(rows: list[Any], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            item = {field: row.get(field) for field in fields}
            item["row_sha256"] = sha256_bytes(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
            sanitized.append(item)
    return sorted(sanitized, key=lambda row: str(row.get("row_sha256")))


def listify(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def parse_if_success(
    command_id: str,
    by_id: dict[str, dict[str, Any]],
    raw: dict[str, tuple[bytes, bytes]],
    parser: Callable[[bytes], Any],
    failures: list[str],
) -> Any:
    receipt = by_id.get(command_id)
    if receipt is None or not command_ok(receipt):
        return None
    try:
        return parser(raw[command_id][0])
    except Exception as exc:
        failures.append(f"{command_id}:{type(exc).__name__}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repo root is not the exact Git worktree root")
    if Path.cwd().resolve() != repo_root:
        raise RuntimeError("working directory is not the exact execution repo root")
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
        str(PYTHON.resolve()), str((repo_root / RUNNER_RELATIVE).resolve()),
        "--repo-root", str(repo_root), "--expected-head", head,
    ]
    original = list(getattr(sys, "orig_argv", []))
    actual_process_argv = (
        [str(Path(original[0]).resolve()), str(Path(original[1]).resolve()), *original[2:]]
        if len(original) >= 2 else original
    )
    if actual_process_argv != expected_process_argv:
        raise RuntimeError("exact original process argv mismatch; interpreter flags are forbidden")
    parent_line = git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parent_line) != 2:
        raise RuntimeError("execution checkpoint must have exactly one parent")
    parent = parent_line[1].casefold()
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("execution worktree must be clean before output creation")
    changed = set(
        filter(
            None,
            git(
                repo_root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ).splitlines(),
        )
    )
    if changed != EXPECTED_HEAD_CHANGE_SET:
        raise RuntimeError(f"execution checkpoint change set mismatch: {sorted(changed)}")

    dispatch = load_json(repo_root / DISPATCH_RELATIVE)
    auth = load_json(repo_root / AUTH_RELATIVE)
    requirements = load_json(repo_root / REQUIREMENTS_RELATIVE)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    native_validation = load_json(repo_root / NATIVE_VALIDATION_RELATIVE)
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-query-only-dispatch-1.0":
        raise RuntimeError("attempt-003 query-only dispatch schema mismatch")
    if auth.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-user-authorization-standard-1.0":
        raise RuntimeError("attempt-003 Standard authorization schema mismatch")
    if contract.get("schema_version") != "stage1e-e4-r6-pc2w-p1-attempt003-query-only-contract-1.0":
        raise RuntimeError("attempt-003 query-only contract schema mismatch")
    if native_validation.get("verdict") != "PASS_PC2W_P1_ATTEMPT003_NATIVE_OFFLINE_V5_VALIDATED":
        raise RuntimeError("validated native-offline v5 PASS missing")
    if native_validation.get("next_gate") != "ATTEMPT003_START_QUERY_STOP_RUNNER_STATIC_AUDIT":
        raise RuntimeError("native validation next gate mismatch")
    if dispatch.get("runner_checkpoint", "").casefold() != parent:
        raise RuntimeError("dispatch runner checkpoint does not equal execution parent")
    if auth.get("entry_checkpoint", "").casefold() != parent:
        raise RuntimeError("authorization entry checkpoint does not equal execution parent")
    if auth.get("authorized_output_root") != str(output_root):
        raise RuntimeError("authorization does not bind the exact output root")
    if dispatch.get("execution_binding", {}).get("output_root") != str(output_root):
        raise RuntimeError("dispatch does not bind the exact output root")
    if dispatch.get("execution_binding", {}).get("expected_output_files") != sorted(
        EXPECTED_OUTPUT_FILES
    ):
        raise RuntimeError("dispatch exact output file set changed")
    binding = dispatch.get("execution_binding", {})
    if Path(binding.get("working_directory", "")).resolve() != repo_root:
        raise RuntimeError("dispatch working directory mismatch")
    expected_dispatch_argv = [
        str(PYTHON), RUNNER_RELATIVE.as_posix(), "--repo-root", str(repo_root),
        "--expected-head", "<EXACT_FULL_EXECUTION_HEAD_FROM_FRESH_AUDIT>",
    ]
    if binding.get("argv") != expected_dispatch_argv:
        raise RuntimeError("dispatch argv binding mismatch")
    if dispatch.get("model_policy", {}).get("service_tier") != "default":
        raise RuntimeError("dispatch is not Standard tier")
    if dispatch.get("model_policy", {}).get("fast_or_priority_allowed") is not False:
        raise RuntimeError("Fast/priority model policy is not forbidden")
    decision = auth.get("user_decision", {})
    if decision.get("decision") != "AUTHORIZE_PC2W_P1_ATTEMPT003_START_QUERY_STOP_ON_VALIDATED_NATIVE_PASS":
        raise RuntimeError("P1 attempt-003 user authorization missing")
    if decision.get("one_docker_desktop_start_authorized") is not True:
        raise RuntimeError("single Docker Desktop start not authorized")
    if decision.get("one_docker_desktop_stop_authorized") is not True:
        raise RuntimeError("single Docker Desktop stop not authorized")
    if decision.get("query_only_runtime_inventory_authorized") is not True:
        raise RuntimeError("query-only inventory not authorized")
    false_auth = (
        "automatic_retry_authorized",
        "image_pull_or_build_authorized",
        "container_create_or_run_authorized",
        "docker_or_wsl_settings_change_authorized",
        "package_or_distro_install_authorized",
        "source_data_or_checkpoint_download_authorized",
        "materialization_authorized",
        "training_authorized",
        "evaluation_authorized",
        "test_access_authorized",
    )
    if any(decision.get(key) is not False for key in false_auth):
        raise RuntimeError("authorization mutation/training lock changed")

    frozen = dispatch.get("frozen_artifacts")
    if not isinstance(frozen, list) or len(frozen) != 6:
        raise RuntimeError("dispatch frozen artifact set invalid")
    expected_paths = {
        RUNNER_RELATIVE,
        NATIVE_HELPER_RELATIVE,
        AUTH_RELATIVE,
        REQUIREMENTS_RELATIVE,
        CONTRACT_RELATIVE,
        NATIVE_VALIDATION_RELATIVE,
    }
    frozen_map = {
        Path(str(row.get("path"))): row for row in frozen if isinstance(row, dict)
    }
    if set(frozen_map) != expected_paths:
        raise RuntimeError("dispatch frozen artifact path set invalid")
    for relative, row in frozen_map.items():
        if git_blob_fact(repo_root, head, relative) != (
            row.get("git_blob_bytes"),
            row.get("git_blob_sha256"),
        ):
            raise RuntimeError(f"frozen artifact mismatch: {relative.as_posix()}")
    if git_blob_fact(repo_root, parent, RUNNER_RELATIVE) != file_fact(
        repo_root / RUNNER_RELATIVE
    ):
        raise RuntimeError("runner differs from frozen parent checkpoint")
    if git_blob_fact(repo_root, parent, CONTRACT_RELATIVE) != file_fact(
        repo_root / CONTRACT_RELATIVE
    ):
        raise RuntimeError("contract differs from frozen parent checkpoint")
    if contract.get("native_pre_gate_replay_immediately_before_start") is not True:
        raise RuntimeError("contract immediate native pre-gate replay missing")
    if contract.get("docker_desktop_status_advisory_only") is not True:
        raise RuntimeError("contract status advisory-only lock missing")
    if requirements.get("schema_version") != (
        "stage1e-e4-r6-pc2w-p1-docker-query-preflight-requirements-1.0"
    ):
        raise RuntimeError("requirements schema changed")
    if set(requirements.get("required_evidence", {})) != {"before", "during", "after"}:
        raise RuntimeError("requirements evidence contract changed")
    if requirements.get("required_user_decision", "").find("Explicitly authorize") < 0:
        raise RuntimeError("requirements user-decision contract changed")

    created_at = utc_now()
    output_root.mkdir(parents=True, exist_ok=False)
    passport = material_passport(created_at, auth)
    receipts: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}

    def invoke(
        command_id: str, argv: list[str], timeout_seconds: int = 30
    ) -> dict[str, Any]:
        if not docker_subcommand_is_allowed(argv):
            raise RuntimeError(f"prohibited Docker command in frozen runner: {argv}")
        receipt, stdout, stderr = run_command(
            command_id, argv, timeout_seconds=timeout_seconds
        )
        receipts.append(receipt)
        raw[command_id] = (stdout, stderr)
        return receipt

    before_disk = disk_snapshot()
    invoke("A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE", [str(DOCKER), "desktop", "status"])
    invoke("A01_WSL_LIST_VERBOSE_PRE_GATE", [str(WSL), "--list", "--verbose"])
    invoke("A02_WSL_LIST_RUNNING_QUIET_PRE_GATE", [str(WSL), "--list", "--running", "--quiet"])
    pre_pipe_probe = native_gate.probe_desktop_linux_pipe()
    invoke(
        "A03_RUNTIME_PROCESS_NAMES_PRE_GATE",
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PRE_START_PROCESS_QUERY],
    )
    invoke("A04_WSL_VERSION_IDENTITY", [str(WSL), "--version"])
    invoke(
        "A05_WINDOWS_IDENTITY",
        [
            str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture | ConvertTo-Json -Depth 3 -Compress",
        ],
    )
    invoke(
        "A06_DOCKER_DESKTOP_FILE_IDENTITY",
        [
            str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
            "$f=Get-Item -LiteralPath 'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe'; [pscustomobject]@{FullName=$f.FullName;Length=$f.Length;FileVersion=$f.VersionInfo.FileVersion;ProductVersion=$f.VersionInfo.ProductVersion} | ConvertTo-Json -Depth 3 -Compress",
        ],
    )

    by_id = {row["command_id"]: row for row in receipts}
    pre_parse_failures: list[str] = []
    before_wsl_rows = parse_if_success(
        "A01_WSL_LIST_VERBOSE_PRE_GATE", by_id, raw, parse_wsl_list, pre_parse_failures
    ) or []
    before_running_names = parse_if_success(
        "A02_WSL_LIST_RUNNING_QUIET_PRE_GATE", by_id, raw, parse_wsl_running, pre_parse_failures
    )
    before_runtime_processes = parse_if_success(
        "A03_RUNTIME_PROCESS_NAMES_PRE_GATE", by_id, raw, parse_runtime_processes, pre_parse_failures
    )
    wsl_version = parse_if_success(
        "A04_WSL_VERSION_IDENTITY", by_id, raw, parse_wsl_version, pre_parse_failures
    ) or {}
    windows_identity = parse_if_success(
        "A05_WINDOWS_IDENTITY", by_id, raw, parse_json_output, pre_parse_failures
    ) or {}
    docker_file_identity = parse_if_success(
        "A06_DOCKER_DESKTOP_FILE_IDENTITY", by_id, raw, parse_json_output, pre_parse_failures
    ) or {}
    pre_status_classification = native_gate.classify_status(
        by_id["A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE"],
        *raw["A00_DOCKER_DESKTOP_STATUS_ADVISORY_BEFORE"],
    )
    pre_identity_payloads_complete = (
        not pre_parse_failures
        and bool(wsl_version.get("wsl_version"))
        and bool(wsl_version.get("kernel_version"))
        and isinstance(windows_identity, dict)
        and all(windows_identity.get(key) for key in ("Caption", "Version", "BuildNumber", "OSArchitecture"))
        and isinstance(docker_file_identity, dict)
        and docker_file_identity.get("FullName") == str(DOCKER_DESKTOP)
        and docker_file_identity.get("Length") == DOCKER_DESKTOP.stat().st_size
        and bool(docker_file_identity.get("FileVersion"))
    )
    pre_gate = {
        "wsl_verbose_strict_parse_complete_and_all_stopped": (
            bool(before_wsl_rows)
            and native_gate.distro_state(before_wsl_rows, "docker-desktop") == "Stopped"
            and all(row.get("state") == "Stopped" for row in before_wsl_rows)
        ),
        "wsl_running_inventory_strict_parse_complete_and_empty": before_running_names == [],
        "desktop_linux_named_pipe_specifically_absent_win32_error_2": native_gate.pipe_is_specifically_absent(pre_pipe_probe),
        "target_runtime_process_inventory_strict_parse_complete_and_empty": before_runtime_processes == [],
        "identity_payloads_parsed_and_complete": pre_identity_payloads_complete,
        "disk_thresholds_before_pass": (
            before_disk["c"]["free_bytes"] >= 20 * 1024**3
            and before_disk["e"]["free_bytes"] >= 50 * 1024**3
        ),
    }

    startup_attempted = False
    start_receipt: dict[str, Any] | None = None
    stop_receipt: dict[str, Any] | None = None
    event_since = utc_now()
    try:
        if all(value is True for value in pre_gate.values()):
            startup_attempted = True
            start_receipt = invoke(
                "A07_DOCKER_DESKTOP_START_ONCE",
                [str(DOCKER), "desktop", "start"],
                timeout_seconds=180,
            )
            if command_ok(start_receipt):
                query_specs = [
                    ("A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING", [str(DOCKER), "desktop", "status"]),
                    ("A09_CONTAINER_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("A10_IMAGE_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                    ("A11_DOCKER_VERSION", [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .}}"]),
                    ("A12_DOCKER_INFO", [str(DOCKER), "--context", "desktop-linux", "info", "--format", "{{json .}}"]),
                    ("A13_CONTEXT_INSPECT", [str(DOCKER), "context", "inspect", "desktop-linux"]),
                    ("A14_SYSTEM_DF", [str(DOCKER), "--context", "desktop-linux", "system", "df", "--format", "{{json .}}"]),
                    ("A15_WSL_LIST_VERBOSE_DURING", [str(WSL), "--list", "--verbose"]),
                    (
                        "A16_PROCESS_INVENTORY_DURING",
                        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); try {$r=@(Get-Process -ErrorAction Stop | Where-Object {$n -contains $_.ProcessName} | Select-Object ProcessName,Id); [pscustomobject]@{Available=$true;Rows=$r} | ConvertTo-Json -Depth 4 -Compress} catch {[pscustomobject]@{Available=$false;ErrorType=$_.Exception.GetType().Name;Rows=@()} | ConvertTo-Json -Depth 4 -Compress}"],
                    ),
                    (
                        "A17_NETWORK_CONNECTION_INVENTORY_DURING",
                        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); try {$p=@(Get-Process -ErrorAction Stop | Where-Object {$n -contains $_.ProcessName}); $ids=@($p.Id); $r=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids -contains $_.OwningProcess} | Select-Object State,LocalPort,RemoteAddress,RemotePort,OwningProcess); [pscustomobject]@{Available=$true;Rows=$r} | ConvertTo-Json -Depth 5 -Compress} catch {[pscustomobject]@{Available=$false;ErrorType=$_.Exception.GetType().Name;Rows=@()} | ConvertTo-Json -Depth 5 -Compress}"],
                    ),
                    ("A18_CONTAINER_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("A19_IMAGE_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                ]
                for query_id, argv in query_specs:
                    invoke(query_id, argv)
                invoke(
                    "A20_DOCKER_EVENTS_BEFORE_STOP",
                    [str(DOCKER), "--context", "desktop-linux", "events", "--since", event_since, "--until", utc_now(), "--format", "{{json .}}"],
                )
    finally:
        if startup_attempted:
            stop_receipt = invoke(
                "A21_DOCKER_DESKTOP_STOP_ONCE",
                [str(DOCKER), "desktop", "stop"],
                timeout_seconds=180,
            )

    invoke("A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER", [str(DOCKER), "desktop", "status"])
    invoke("A23_WSL_LIST_VERBOSE_POST_A", [str(WSL), "--list", "--verbose"])
    invoke("A24_WSL_LIST_RUNNING_QUIET_POST_A", [str(WSL), "--list", "--running", "--quiet"])
    post_pipe_probe_a = native_gate.probe_desktop_linux_pipe()
    invoke(
        "A25_RUNTIME_PROCESS_NAMES_POST_A",
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", POST_STOP_PROCESS_QUERY],
    )
    invoke("A26_WSL_LIST_VERBOSE_POST_B", [str(WSL), "--list", "--verbose"])
    invoke("A27_WSL_LIST_RUNNING_QUIET_POST_B", [str(WSL), "--list", "--running", "--quiet"])
    post_pipe_probe_b = native_gate.probe_desktop_linux_pipe()
    invoke(
        "A28_RUNTIME_PROCESS_NAMES_POST_B",
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", POST_STOP_PROCESS_QUERY],
    )
    after_disk = disk_snapshot()
    by_id = {row["command_id"]: row for row in receipts}
    parse_failures: list[str] = list(pre_parse_failures)
    version_data = parse_if_success(
        "A11_DOCKER_VERSION", by_id, raw, parse_json_output, parse_failures
    ) or {}
    info_data = parse_if_success(
        "A12_DOCKER_INFO", by_id, raw, parse_json_output, parse_failures
    ) or {}
    context_data = parse_if_success(
        "A13_CONTEXT_INSPECT", by_id, raw, parse_json_output, parse_failures
    )
    system_df_rows = parse_if_success(
        "A14_SYSTEM_DF", by_id, raw, parse_json_lines, parse_failures
    ) or []
    during_wsl_rows = parse_if_success(
        "A15_WSL_LIST_VERBOSE_DURING", by_id, raw, parse_wsl_list, parse_failures
    ) or []
    process_data = parse_if_success(
        "A16_PROCESS_INVENTORY_DURING", by_id, raw, parse_json_output, parse_failures
    ) or {}
    network_data = parse_if_success(
        "A17_NETWORK_CONNECTION_INVENTORY_DURING", by_id, raw, parse_json_output, parse_failures
    ) or {}
    containers_initial_raw = parse_if_success(
        "A09_CONTAINER_LIST_INITIAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    images_initial_raw = parse_if_success(
        "A10_IMAGE_LIST_INITIAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    containers_final_raw = parse_if_success(
        "A18_CONTAINER_LIST_FINAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    images_final_raw = parse_if_success(
        "A19_IMAGE_LIST_FINAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    events_raw = parse_if_success(
        "A20_DOCKER_EVENTS_BEFORE_STOP", by_id, raw, parse_json_lines, parse_failures
    ) or []
    post_wsl_rows_a = parse_if_success(
        "A23_WSL_LIST_VERBOSE_POST_A", by_id, raw, parse_wsl_list, parse_failures
    ) or []
    post_running_names_a = parse_if_success(
        "A24_WSL_LIST_RUNNING_QUIET_POST_A", by_id, raw, parse_wsl_running, parse_failures
    )
    post_runtime_processes_a = parse_if_success(
        "A25_RUNTIME_PROCESS_NAMES_POST_A", by_id, raw, parse_runtime_processes, parse_failures
    )
    post_wsl_rows_b = parse_if_success(
        "A26_WSL_LIST_VERBOSE_POST_B", by_id, raw, parse_wsl_list, parse_failures
    ) or []
    post_running_names_b = parse_if_success(
        "A27_WSL_LIST_RUNNING_QUIET_POST_B", by_id, raw, parse_wsl_running, parse_failures
    )
    post_runtime_processes_b = parse_if_success(
        "A28_RUNTIME_PROCESS_NAMES_POST_B", by_id, raw, parse_runtime_processes, parse_failures
    )

    containers_initial = sanitize_rows(
        containers_initial_raw, ("ID", "State", "Status")
    )
    containers_final = sanitize_rows(containers_final_raw, ("ID", "State", "Status"))
    images_initial = sanitize_rows(images_initial_raw, ("ID", "Digest", "Size"))
    images_final = sanitize_rows(images_final_raw, ("ID", "Digest", "Size"))
    system_df = sanitize_rows(
        system_df_rows, ("Type", "TotalCount", "Active", "Size", "Reclaimable")
    )
    mutation_events = [
        {
            "Type": row.get("Type"),
            "Action": row.get("Action"),
            "ActorIDSha256": sha256_bytes(
                str((row.get("Actor") or {}).get("ID", "")).encode("utf-8")
            ),
        }
        for row in events_raw
        if isinstance(row, dict)
        and str(row.get("Type", "")).casefold() in {"container", "image"}
    ]

    process_rows = listify(process_data.get("Rows")) if isinstance(process_data, dict) else []
    network_rows = listify(network_data.get("Rows")) if isinstance(network_data, dict) else []
    sanitized_processes = [
        {"ProcessName": row.get("ProcessName"), "Id": row.get("Id")}
        for row in process_rows
        if isinstance(row, dict)
    ]
    sanitized_connections = [
        {
            "State": row.get("State"),
            "LocalPort": row.get("LocalPort"),
            "RemoteAddressSha256": sha256_bytes(
                str(row.get("RemoteAddress", "")).encode("utf-8")
            ),
            "RemotePort": row.get("RemotePort"),
            "OwningProcess": row.get("OwningProcess"),
        }
        for row in network_rows
        if isinstance(row, dict)
    ]

    client = version_data.get("Client") or {}
    server = version_data.get("Server") or {}
    client_whitelist = {
        key: client.get(key)
        for key in (
            "Version", "ApiVersion", "DefaultAPIVersion", "GitCommit",
            "GoVersion", "Os", "Arch", "BuildTime", "Context",
        )
    }
    server_whitelist = {
        key: server.get(key)
        for key in (
            "Version", "ApiVersion", "MinAPIVersion", "GitCommit", "GoVersion",
            "Os", "Arch", "KernelVersion", "BuildTime", "Experimental",
        )
    }
    info_whitelist = {
        key: info_data.get(key)
        for key in (
            "ID", "ServerVersion", "OperatingSystem", "OSType", "Architecture",
            "KernelVersion", "Driver", "CgroupDriver", "CgroupVersion",
            "DockerRootDir", "SecurityOptions", "DefaultRuntime", "NCPU",
            "MemTotal", "Containers", "ContainersRunning", "ContainersPaused",
            "ContainersStopped", "Images", "LiveRestoreEnabled", "Isolation",
            "ExperimentalBuild", "ContainerdCommit",
        )
    }
    info_whitelist.update(
        {
            "Runtimes": sorted((info_data.get("Runtimes") or {}).keys()),
            "HttpProxyConfigured": bool(info_data.get("HttpProxy")),
            "HttpsProxyConfigured": bool(info_data.get("HttpsProxy")),
            "NoProxyConfigured": bool(info_data.get("NoProxy")),
        }
    )
    containerd_commit = info_whitelist.get("ContainerdCommit")
    containerd_commit_id = (
        containerd_commit.get("ID")
        if isinstance(containerd_commit, dict)
        else None
    )
    context_whitelist = sanitize_context(context_data)
    during_status_classification = (
        native_gate.classify_status(
            by_id["A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING"],
            *raw["A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING"],
        )
        if "A08_DOCKER_DESKTOP_STATUS_ADVISORY_DURING" in by_id
        else "NOT_OBSERVED"
    )
    post_status_classification = native_gate.classify_status(
        by_id["A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER"],
        *raw["A22_DOCKER_DESKTOP_STATUS_ADVISORY_AFTER"],
    )
    query_ids = [
        "A09_CONTAINER_LIST_INITIAL",
        "A10_IMAGE_LIST_INITIAL",
        "A11_DOCKER_VERSION",
        "A12_DOCKER_INFO",
        "A13_CONTEXT_INSPECT",
        "A14_SYSTEM_DF",
        "A15_WSL_LIST_VERBOSE_DURING",
        "A16_PROCESS_INVENTORY_DURING",
        "A17_NETWORK_CONNECTION_INVENTORY_DURING",
        "A18_CONTAINER_LIST_FINAL",
        "A19_IMAGE_LIST_FINAL",
        "A20_DOCKER_EVENTS_BEFORE_STOP",
    ]
    all_queries_ok = all(command_ok(by_id.get(command_id, {})) for command_id in query_ids)
    no_running_containers = (
        info_whitelist.get("ContainersRunning") == 0
        and all(
            str(row.get("State", "")).casefold() != "running"
            for row in containers_initial + containers_final
        )
    )
    identities_complete = (
        bool(wsl_version.get("wsl_version"))
        and bool(wsl_version.get("kernel_version"))
        and isinstance(windows_identity, dict)
        and all(
            windows_identity.get(key)
            for key in ("Caption", "Version", "BuildNumber", "OSArchitecture")
        )
        and isinstance(docker_file_identity, dict)
        and docker_file_identity.get("FullName") == str(DOCKER_DESKTOP)
        and docker_file_identity.get("Length") == DOCKER_DESKTOP.stat().st_size
        and bool(docker_file_identity.get("FileVersion"))
        and all(client_whitelist.get(key) for key in ("Version", "ApiVersion"))
        and all(server_whitelist.get(key) for key in ("Version", "Os", "Arch", "KernelVersion"))
        and all(
            info_whitelist.get(key)
            for key in ("Driver", "CgroupVersion", "DockerRootDir")
        )
        and bool(containerd_commit_id)
    )
    backend_linux = (
        str(info_whitelist.get("OSType", "")).casefold() == "linux"
        and str(info_whitelist.get("Architecture", "")).casefold()
        in {"x86_64", "amd64"}
        and str(context_whitelist.get("Name", "")).casefold() == "desktop-linux"
        and str(context_whitelist.get("DockerEndpointHost", "")).casefold()
        == "npipe:////./pipe/dockerdesktoplinuxengine"
    )
    post_lanes_a = {
        "wsl_inventory_all_stopped": (
            bool(post_wsl_rows_a)
            and native_gate.distro_state(post_wsl_rows_a, "docker-desktop") == "Stopped"
            and all(row.get("state") == "Stopped" for row in post_wsl_rows_a)
        ),
        "wsl_running_inventory_empty": post_running_names_a == [],
        "desktop_linux_named_pipe_specifically_absent_win32_error_2": native_gate.pipe_is_specifically_absent(post_pipe_probe_a),
        "target_runtime_process_inventory_empty": post_runtime_processes_a == [],
    }
    post_lanes_b = {
        "wsl_inventory_all_stopped": (
            bool(post_wsl_rows_b)
            and native_gate.distro_state(post_wsl_rows_b, "docker-desktop") == "Stopped"
            and all(row.get("state") == "Stopped" for row in post_wsl_rows_b)
        ),
        "wsl_running_inventory_empty": post_running_names_b == [],
        "desktop_linux_named_pipe_specifically_absent_win32_error_2": native_gate.pipe_is_specifically_absent(post_pipe_probe_b),
        "target_runtime_process_inventory_empty": post_runtime_processes_b == [],
    }
    post_stop_closure = {
        "snapshot_a_all_native_lanes": all(post_lanes_a.values()),
        "snapshot_b_all_native_lanes": all(post_lanes_b.values()),
        "wsl_inventory_stable": post_wsl_rows_a == post_wsl_rows_b,
        "wsl_running_inventory_stable": post_running_names_a == post_running_names_b,
        "runtime_process_inventory_stable": post_runtime_processes_a == post_runtime_processes_b,
        "named_pipe_absence_stable": (
            native_gate.pipe_is_specifically_absent(post_pipe_probe_a)
            and native_gate.pipe_is_specifically_absent(post_pipe_probe_b)
        ),
        "wsl_inventory_restored_to_pre_start": before_wsl_rows == post_wsl_rows_a == post_wsl_rows_b,
    }
    command_ids = [row["command_id"] for row in receipts]
    exact_command_sequence = command_ids == EXPECTED_COMMAND_IDS and len(set(command_ids)) == len(command_ids)
    pass_conditions = {
        "pre_start_gate_all_pass": all(value is True for value in pre_gate.values()),
        "startup_attempted_exactly_once": startup_attempted and start_receipt is not None,
        "startup_command_success": start_receipt is not None and command_ok(start_receipt),
        "during_docker_desktop_distro_exactly_running": (
            native_gate.distro_state(during_wsl_rows, "docker-desktop") == "Running"
        ),
        "all_query_commands_success": all_queries_ok,
        "backend_linux_amd64_desktop_linux": backend_linux,
        "runtime_identities_complete": identities_complete,
        "parse_failures_absent": not parse_failures,
        "containers_running_zero": no_running_containers,
        "container_inventory_unchanged": containers_initial == containers_final,
        "image_inventory_unchanged": images_initial == images_final,
        "container_or_image_events_absent": not mutation_events,
        "stop_attempted_exactly_once": startup_attempted and stop_receipt is not None,
        "stop_command_success": stop_receipt is not None and command_ok(stop_receipt),
        "post_stop_native_closure_all_pass": all(post_stop_closure.values()),
        "exact_command_sequence_no_retry": exact_command_sequence,
        "disk_thresholds_after_pass": (
            after_disk["c"]["free_bytes"] >= 20 * 1024**3
            and after_disk["e"]["free_bytes"] >= 50 * 1024**3
        ),
        "prohibited_commands_issued": False,
        "automatic_retry_count_zero": True,
    }
    verdict = (
        "PASS_PC2W_P1_ATTEMPT003_QUERY_EVIDENCE_READY_FOR_CENTRAL_G1"
        if all(value is True for value in pass_conditions.values())
        else "FAIL_CLOSED_PC2W_P1_ATTEMPT003_BACKEND_OR_POLICY_NOT_ADMISSIBLE"
    )

    frozen_facts = [
        {
            "path": relative.as_posix(),
            "git_blob_bytes": git_blob_fact(repo_root, head, relative)[0],
            "git_blob_sha256": git_blob_fact(repo_root, head, relative)[1],
        }
        for relative in sorted(frozen_map, key=lambda item: item.as_posix())
    ]
    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-command-receipts-1.0",
        "material_passport": passport,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "runner_sha256": sha256_file(repo_root / RUNNER_RELATIVE),
        "commands": receipts,
        "command_ids": command_ids,
        "exact_command_sequence": exact_command_sequence,
        "named_pipe_probes_are_non_command_read_only_probes": True,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    inventory_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-runtime-inventory-1.0",
        "material_passport": passport,
        "host_identity": {"windows": windows_identity, "wsl": wsl_version},
        "docker_desktop_identity": {
            "path": str(DOCKER_DESKTOP),
            "raw_bytes": DOCKER_DESKTOP.stat().st_size,
            "raw_sha256": sha256_file(DOCKER_DESKTOP),
            "file_version": docker_file_identity.get("FileVersion"),
            "product_version": docker_file_identity.get("ProductVersion"),
        },
        "wsl_state": {
            "pre_start": before_wsl_rows,
            "during": during_wsl_rows,
            "post_stop_snapshot_a": post_wsl_rows_a,
            "post_stop_snapshot_b": post_wsl_rows_b,
        },
        "docker_desktop_status_advisory_only": {
            "pre_start": pre_status_classification,
            "during": during_status_classification,
            "post_stop": post_status_classification,
            "admission_authority": False,
            "cannot_veto_or_admit_native_gate": True,
        },
        "native_gate": {
            "pre_start_lanes": pre_gate,
            "pre_start_named_pipe_probe": pre_pipe_probe,
            "post_stop_snapshot_a_lanes": post_lanes_a,
            "post_stop_snapshot_a_named_pipe_probe": post_pipe_probe_a,
            "post_stop_snapshot_b_lanes": post_lanes_b,
            "post_stop_snapshot_b_named_pipe_probe": post_pipe_probe_b,
            "post_stop_closure": post_stop_closure,
            "post_stop_runtime_processes_a": post_runtime_processes_a,
            "post_stop_runtime_processes_b": post_runtime_processes_b,
        },
        "client_version_whitelist": client_whitelist,
        "server_version_whitelist": server_whitelist,
        "docker_info_whitelist": info_whitelist,
        "context_whitelist": context_whitelist,
        "images_initial": images_initial,
        "images_final": images_final,
        "containers_initial": containers_initial,
        "containers_final": containers_final,
        "container_or_image_events": mutation_events,
        "system_df": system_df,
        "process_inventory": {
            "available": process_data.get("Available") if isinstance(process_data, dict) else False,
            "rows": sanitized_processes,
        },
        "connections_redacted": {
            "available": network_data.get("Available") if isinstance(network_data, dict) else False,
            "rows": sanitized_connections,
        },
        "before_disk": before_disk,
        "after_disk": after_disk,
        "disk_delta_free_bytes": {
            key: after_disk[key]["free_bytes"] - before_disk[key]["free_bytes"]
            for key in ("c", "e")
        },
        "proxy_values_persisted": False,
        "raw_context_persisted": False,
        "vendor_startup_network_claimed_absent": False,
        "parse_failures": parse_failures,
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-execution-receipt-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003",
        "created_at": created_at,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "frozen_artifacts": frozen_facts,
        "requirements_sha256": sha256_file(repo_root / REQUIREMENTS_RELATIVE),
        "authorization_sha256": sha256_file(repo_root / AUTH_RELATIVE),
        "dispatch_sha256": sha256_file(repo_root / DISPATCH_RELATIVE),
        "runner_sha256": sha256_file(repo_root / RUNNER_RELATIVE),
        "output_root": str(output_root),
        "startup_attempts": 1 if startup_attempted else 0,
        "query_retry_count": 0,
        "stop_attempts": 1 if stop_receipt is not None else 0,
        "pre_start_gate": pre_gate,
        "docker_desktop_status_is_advisory_only": True,
        "post_stop_native_closure": post_stop_closure,
        "pass_conditions": pass_conditions,
        "verdict": verdict,
        "image_pull_or_build_performed": False,
        "container_create_or_run_performed": False,
        "docker_or_wsl_settings_changed": False,
        "source_data_or_checkpoint_download_performed": False,
        "materialization_performed": False,
        "scientific_execution_performed": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    handoff_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt003-handoff-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT003",
        "verdict": verdict,
        "output_files": sorted(EXPECTED_OUTPUT_FILES),
        "next_gate": (
            "CENTRAL_PC2W_G1_AND_FRESH_INDEPENDENT_SOL_XHIGH_STANDARD_AUDIT"
            if verdict.startswith("PASS_")
            else "FAIL_CLOSED_USER_DECISION_REQUIRED_NO_AUTOMATIC_RETRY"
        ),
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
        },
    }
    write_json(output_root / "command_receipts.json", command_document)
    write_json(output_root / "runtime_inventory.json", inventory_document)
    write_json(output_root / "p1_execution_receipt.json", execution_document)
    write_json(output_root / "p1_handoff.json", handoff_document)
    output_entries = list(output_root.iterdir())
    if (
        {path.name for path in output_entries} != EXPECTED_OUTPUT_FILES
        or not all(path.is_file() for path in output_entries)
    ):
        raise RuntimeError("exact output entry set violated")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "output_root": str(output_root),
                "commands_recorded": len(receipts),
                "automatic_retry_count": 0,
            },
            indent=2,
        )
    )
    return 0 if verdict.startswith("PASS_") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "verdict": "HANDOFF_INCOMPLETE",
                    "error_type": type(exc).__name__,
                    "error_sha256": sha256_bytes(str(exc).encode("utf-8")),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
