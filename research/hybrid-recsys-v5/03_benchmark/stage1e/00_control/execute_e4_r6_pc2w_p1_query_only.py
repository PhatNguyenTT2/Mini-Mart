#!/usr/bin/env python3
"""Run one authorized Docker Desktop query-only start/query/stop probe.

This runner is fail-closed: it performs no retry, never pulls/builds/runs a
container, and always reaches the single stop attempt after a start attempt.
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


DOCKER = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
WSL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wsl.exe"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
EXPECTED_DOCKER_DESKTOP_SHA256 = "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce"

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_query_only.py"
AUTH_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_user_authorization_and_model_override.json"
REQUIREMENTS_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_current_host_wsl2_linux_admission_contract.md"
PREFLIGHT_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_read_only_preflight_receipt.json"
DISPATCH_RELATIVE = CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_p1_dispatch.json"
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_al/"
    "E4_R6PC2W_P1_docker_query_preflight/attempt-001"
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
DAEMON_UNAVAILABLE_MARKERS = (
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "dockerdesktoplinuxengine: the system cannot find the file specified",
    "dockerdesktoplinuxengine. the system cannot find the file specified",
    "open //./pipe/dockerdesktoplinuxengine",
    "error during connect",
)


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
    text = decode_output(value).strip()
    return json.loads(text) if text else None


def parse_json_lines(value: bytes) -> list[Any]:
    rows: list[Any] = []
    for line in decode_output(value).splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_status(value: bytes) -> str | None:
    matches = set(re.findall(r"\b(running|stopped)\b", decode_output(value).casefold()))
    return next(iter(matches)) if len(matches) == 1 else None


def parse_wsl_list(value: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in decode_output(value).replace("\x00", "").splitlines():
        line = raw_line.strip()
        if not line or ("name" in line.casefold() and "state" in line.casefold()):
            continue
        match = re.match(
            r"^\*?\s*(.+?)\s+(Running|Stopped)\s+([12])\s*$",
            line,
            re.IGNORECASE,
        )
        if match:
            rows.append(
                {
                    "name": match.group(1).strip(),
                    "state": match.group(2).title(),
                    "version": int(match.group(3)),
                }
            )
    return rows


def parse_wsl_version(value: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in decode_output(value).replace("\x00", "").splitlines():
        if ":" in line:
            key, item = line.split(":", 1)
            normalized = key.strip().casefold().replace(" ", "_")
            if normalized in {
                "wsl_version", "kernel_version", "wslg_version", "windows_version"
            }:
                result[normalized] = item.strip()
    return result


def distro_state(rows: list[dict[str, Any]], name: str) -> str | None:
    matches = [
        str(row.get("state"))
        for row in rows
        if str(row.get("name", "")).casefold() == name.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def daemon_is_specifically_unavailable(
    receipt: dict[str, Any], stdout: bytes, stderr: bytes
) -> bool:
    if receipt.get("timed_out") or receipt.get("spawn_exception_type") is not None:
        return False
    exit_code = receipt.get("exit_code")
    if not isinstance(exit_code, int) or exit_code == 0:
        return False
    text = (decode_output(stdout) + "\n" + decode_output(stderr)).casefold()
    return any(marker in text for marker in DAEMON_UNAVAILABLE_MARKERS)


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


def material_passport(created_at: str) -> dict[str, Any]:
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_execution_v2",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_user_authorization_v2",
            "stage1e_e4_r6_pc2w_p1_requirements_v1",
        ],
        "repro_lock": None,
        "experiment_intake_declaration": {
            "status": "no_experiments_declared",
            "declared_at": created_at,
            "declared_by": "scholar",
        },
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
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repo root is not the exact Git worktree root")
    output_root = (repo_root / OUTPUT_RELATIVE).resolve()
    if output_root.exists():
        raise RuntimeError(f"immutable output root already exists: {output_root}")
    for required in (DOCKER, DOCKER_DESKTOP, WSL, POWERSHELL):
        if not required.is_file():
            raise RuntimeError(f"required executable missing: {required}")
    if sha256_file(DOCKER_DESKTOP) != EXPECTED_DOCKER_DESKTOP_SHA256:
        raise RuntimeError("Docker Desktop executable hash changed")

    head = git(repo_root, "rev-parse", "HEAD").casefold()
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
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc2w-p1-dispatch-2.0":
        raise RuntimeError("dispatch v2 missing")
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
    decision = auth.get("user_decision", {})
    if decision.get("decision") != "AUTHORIZE_PC2W_P1_EXECUTION":
        raise RuntimeError("P1 user authorization missing")
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
    if not isinstance(frozen, list) or len(frozen) != 5:
        raise RuntimeError("dispatch frozen artifact set invalid")
    expected_paths = {
        RUNNER_RELATIVE,
        AUTH_RELATIVE,
        REQUIREMENTS_RELATIVE,
        CONTRACT_RELATIVE,
        PREFLIGHT_RELATIVE,
    }
    frozen_map = {
        Path(str(row.get("path"))): row for row in frozen if isinstance(row, dict)
    }
    if set(frozen_map) != expected_paths:
        raise RuntimeError("dispatch frozen artifact path set invalid")
    for relative, row in frozen_map.items():
        if file_fact(repo_root / relative) != (
            row.get("raw_bytes"),
            row.get("raw_sha256"),
        ):
            raise RuntimeError(f"frozen artifact mismatch: {relative.as_posix()}")
    if git_blob_fact(repo_root, parent, RUNNER_RELATIVE) != file_fact(
        repo_root / RUNNER_RELATIVE
    ):
        raise RuntimeError("runner differs from frozen parent checkpoint")
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
    passport = material_passport(created_at)
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
    invoke("P00_WSL_LIST_BEFORE", [str(WSL), "--list", "--verbose"])
    invoke("P01_DOCKER_DESKTOP_STATUS_BEFORE", [str(DOCKER), "desktop", "status"])
    invoke(
        "P02_DAEMON_VERSION_BEFORE",
        [
            str(DOCKER), "--context", "desktop-linux", "version",
            "--format", "{{json .Server}}",
        ],
    )
    invoke("P03_WSL_VERSION_BEFORE", [str(WSL), "--version"])
    invoke(
        "P04_WINDOWS_IDENTITY_BEFORE",
        [
            str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
            "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture | ConvertTo-Json -Depth 3 -Compress",
        ],
    )
    invoke(
        "P05_DOCKER_DESKTOP_FILE_IDENTITY_BEFORE",
        [
            str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
            "$f=Get-Item -LiteralPath 'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe'; [pscustomobject]@{FullName=$f.FullName;Length=$f.Length;FileVersion=$f.VersionInfo.FileVersion;ProductVersion=$f.VersionInfo.ProductVersion} | ConvertTo-Json -Depth 3 -Compress",
        ],
    )

    by_id = {row["command_id"]: row for row in receipts}
    before_wsl_rows = (
        parse_wsl_list(raw["P00_WSL_LIST_BEFORE"][0])
        if command_ok(by_id["P00_WSL_LIST_BEFORE"])
        else []
    )
    before_status = (
        parse_status(raw["P01_DOCKER_DESKTOP_STATUS_BEFORE"][0])
        if command_ok(by_id["P01_DOCKER_DESKTOP_STATUS_BEFORE"])
        else None
    )
    pre_gate = {
        "wsl_list_query_success": command_ok(by_id["P00_WSL_LIST_BEFORE"]),
        "docker_desktop_status_query_success": command_ok(
            by_id["P01_DOCKER_DESKTOP_STATUS_BEFORE"]
        ),
        "docker_desktop_exactly_stopped": before_status == "stopped",
        "daemon_specifically_unavailable": daemon_is_specifically_unavailable(
            by_id["P02_DAEMON_VERSION_BEFORE"], *raw["P02_DAEMON_VERSION_BEFORE"]
        ),
        "docker_desktop_distro_exactly_stopped": (
            distro_state(before_wsl_rows, "docker-desktop") == "Stopped"
        ),
        "wsl_identity_query_success": command_ok(by_id["P03_WSL_VERSION_BEFORE"]),
        "windows_identity_query_success": command_ok(
            by_id["P04_WINDOWS_IDENTITY_BEFORE"]
        ),
        "docker_file_identity_query_success": command_ok(
            by_id["P05_DOCKER_DESKTOP_FILE_IDENTITY_BEFORE"]
        ),
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
                "P06_DOCKER_DESKTOP_START_ONCE",
                [str(DOCKER), "desktop", "start"],
                timeout_seconds=180,
            )
            if command_ok(start_receipt):
                query_specs = [
                    ("P07_DOCKER_DESKTOP_STATUS_DURING", [str(DOCKER), "desktop", "status"]),
                    ("P08_CONTAINER_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("P09_IMAGE_LIST_INITIAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                    ("P10_DOCKER_VERSION", [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .}}"]),
                    ("P11_DOCKER_INFO", [str(DOCKER), "--context", "desktop-linux", "info", "--format", "{{json .}}"]),
                    ("P12_CONTEXT_INSPECT", [str(DOCKER), "context", "inspect", "desktop-linux"]),
                    ("P13_SYSTEM_DF", [str(DOCKER), "--context", "desktop-linux", "system", "df", "--format", "{{json .}}"]),
                    ("P14_WSL_LIST_DURING", [str(WSL), "--list", "--verbose"]),
                    (
                        "P15_PROCESS_INVENTORY",
                        [
                            str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
                            "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); try {$r=@(Get-Process -ErrorAction Stop | Where-Object {$n -contains $_.ProcessName} | Select-Object ProcessName,Id); [pscustomobject]@{Available=$true;Rows=$r} | ConvertTo-Json -Depth 4 -Compress} catch {[pscustomobject]@{Available=$false;ErrorType=$_.Exception.GetType().Name;Rows=@()} | ConvertTo-Json -Depth 4 -Compress}",
                        ],
                    ),
                    (
                        "P16_NETWORK_CONNECTION_INVENTORY",
                        [
                            str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
                            "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); try {$p=@(Get-Process -ErrorAction Stop | Where-Object {$n -contains $_.ProcessName}); $ids=@($p.Id); $r=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids -contains $_.OwningProcess} | Select-Object State,LocalPort,RemoteAddress,RemotePort,OwningProcess); [pscustomobject]@{Available=$true;Rows=$r} | ConvertTo-Json -Depth 5 -Compress} catch {[pscustomobject]@{Available=$false;ErrorType=$_.Exception.GetType().Name;Rows=@()} | ConvertTo-Json -Depth 5 -Compress}",
                        ],
                    ),
                    ("P17_CONTAINER_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
                    ("P18_IMAGE_LIST_FINAL", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
                ]
                for query_id, argv in query_specs:
                    invoke(query_id, argv)
                invoke(
                    "P19_DOCKER_EVENTS_BEFORE_STOP",
                    [
                        str(DOCKER), "--context", "desktop-linux", "events",
                        "--since", event_since, "--until", utc_now(),
                        "--format", "{{json .}}",
                    ],
                )
    finally:
        if startup_attempted:
            stop_receipt = invoke(
                "P20_DOCKER_DESKTOP_STOP_ONCE",
                [str(DOCKER), "desktop", "stop"],
                timeout_seconds=180,
            )

    invoke("P21_DOCKER_DESKTOP_STATUS_AFTER", [str(DOCKER), "desktop", "status"])
    invoke(
        "P22_DAEMON_VERSION_AFTER",
        [
            str(DOCKER), "--context", "desktop-linux", "version",
            "--format", "{{json .Server}}",
        ],
    )
    invoke("P23_WSL_LIST_AFTER", [str(WSL), "--list", "--verbose"])
    after_disk = disk_snapshot()
    by_id = {row["command_id"]: row for row in receipts}
    parse_failures: list[str] = []

    wsl_version = parse_if_success(
        "P03_WSL_VERSION_BEFORE", by_id, raw, parse_wsl_version, parse_failures
    ) or {}
    windows_identity = parse_if_success(
        "P04_WINDOWS_IDENTITY_BEFORE", by_id, raw, parse_json_output, parse_failures
    ) or {}
    docker_file_identity = parse_if_success(
        "P05_DOCKER_DESKTOP_FILE_IDENTITY_BEFORE",
        by_id,
        raw,
        parse_json_output,
        parse_failures,
    ) or {}
    version_data = parse_if_success(
        "P10_DOCKER_VERSION", by_id, raw, parse_json_output, parse_failures
    ) or {}
    info_data = parse_if_success(
        "P11_DOCKER_INFO", by_id, raw, parse_json_output, parse_failures
    ) or {}
    context_data = parse_if_success(
        "P12_CONTEXT_INSPECT", by_id, raw, parse_json_output, parse_failures
    )
    system_df_rows = parse_if_success(
        "P13_SYSTEM_DF", by_id, raw, parse_json_lines, parse_failures
    ) or []
    during_wsl_rows = parse_if_success(
        "P14_WSL_LIST_DURING", by_id, raw, parse_wsl_list, parse_failures
    ) or []
    process_data = parse_if_success(
        "P15_PROCESS_INVENTORY", by_id, raw, parse_json_output, parse_failures
    ) or {}
    network_data = parse_if_success(
        "P16_NETWORK_CONNECTION_INVENTORY", by_id, raw, parse_json_output, parse_failures
    ) or {}
    containers_initial_raw = parse_if_success(
        "P08_CONTAINER_LIST_INITIAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    images_initial_raw = parse_if_success(
        "P09_IMAGE_LIST_INITIAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    containers_final_raw = parse_if_success(
        "P17_CONTAINER_LIST_FINAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    images_final_raw = parse_if_success(
        "P18_IMAGE_LIST_FINAL", by_id, raw, parse_json_lines, parse_failures
    ) or []
    events_raw = parse_if_success(
        "P19_DOCKER_EVENTS_BEFORE_STOP", by_id, raw, parse_json_lines, parse_failures
    ) or []
    after_wsl_rows = parse_if_success(
        "P23_WSL_LIST_AFTER", by_id, raw, parse_wsl_list, parse_failures
    ) or []

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

    server = version_data.get("Server") or {}
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
    context_whitelist = sanitize_context(context_data)
    after_status = (
        parse_status(raw["P21_DOCKER_DESKTOP_STATUS_AFTER"][0])
        if command_ok(by_id["P21_DOCKER_DESKTOP_STATUS_AFTER"])
        else None
    )
    during_status = (
        parse_status(raw["P07_DOCKER_DESKTOP_STATUS_DURING"][0])
        if "P07_DOCKER_DESKTOP_STATUS_DURING" in by_id
        and command_ok(by_id["P07_DOCKER_DESKTOP_STATUS_DURING"])
        else None
    )
    query_ids = [
        "P07_DOCKER_DESKTOP_STATUS_DURING",
        "P08_CONTAINER_LIST_INITIAL",
        "P09_IMAGE_LIST_INITIAL",
        "P10_DOCKER_VERSION",
        "P11_DOCKER_INFO",
        "P12_CONTEXT_INSPECT",
        "P13_SYSTEM_DF",
        "P14_WSL_LIST_DURING",
        "P15_PROCESS_INVENTORY",
        "P16_NETWORK_CONNECTION_INVENTORY",
        "P17_CONTAINER_LIST_FINAL",
        "P18_IMAGE_LIST_FINAL",
        "P19_DOCKER_EVENTS_BEFORE_STOP",
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
        and all(server_whitelist.get(key) for key in ("Version", "Os", "Arch", "KernelVersion"))
        and all(
            info_whitelist.get(key)
            for key in ("Driver", "CgroupVersion", "DockerRootDir")
        )
    )
    backend_linux = (
        str(info_whitelist.get("OSType", "")).casefold() == "linux"
        and str(info_whitelist.get("Architecture", "")).casefold()
        in {"x86_64", "amd64"}
        and str(context_whitelist.get("Name", "")).casefold() == "desktop-linux"
        and str(context_whitelist.get("DockerEndpointHost", "")).casefold()
        == "npipe:////./pipe/dockerdesktoplinuxengine"
    )
    pass_conditions = {
        "pre_start_gate_all_pass": all(value is True for value in pre_gate.values()),
        "startup_attempted_exactly_once": startup_attempted and start_receipt is not None,
        "startup_command_success": start_receipt is not None and command_ok(start_receipt),
        "during_status_exactly_running": during_status == "running",
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
        "after_status_exactly_stopped": after_status == "stopped",
        "after_daemon_specifically_unavailable": daemon_is_specifically_unavailable(
            by_id["P22_DAEMON_VERSION_AFTER"], *raw["P22_DAEMON_VERSION_AFTER"]
        ),
        "after_docker_desktop_distro_exactly_stopped": (
            distro_state(after_wsl_rows, "docker-desktop") == "Stopped"
        ),
        "disk_thresholds_after_pass": (
            after_disk["c"]["free_bytes"] >= 20 * 1024**3
            and after_disk["e"]["free_bytes"] >= 50 * 1024**3
        ),
        "prohibited_commands_issued": False,
        "automatic_retry_count_zero": True,
    }
    verdict = (
        "PASS_PC2W_P1_QUERY_EVIDENCE_READY_FOR_CENTRAL_G1"
        if all(value is True for value in pass_conditions.values())
        else "FAIL_CLOSED_PC2W_BACKEND_OR_POLICY_NOT_ADMISSIBLE"
    )

    frozen_facts = [
        {
            "path": relative.as_posix(),
            "raw_bytes": file_fact(repo_root / relative)[0],
            "raw_sha256": file_fact(repo_root / relative)[1],
        }
        for relative in sorted(frozen_map, key=lambda item: item.as_posix())
    ]
    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-command-receipts-2.0",
        "material_passport": passport,
        "entry_checkpoint": head,
        "runner_checkpoint": parent,
        "runner_sha256": sha256_file(repo_root / RUNNER_RELATIVE),
        "commands": receipts,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    inventory_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-runtime-inventory-2.0",
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
            "before": before_wsl_rows,
            "during": during_wsl_rows,
            "after": after_wsl_rows,
        },
        "docker_desktop_status": {
            "before": before_status,
            "during": during_status,
            "after": after_status,
        },
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
        "parse_failures": parse_failures,
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-execution-receipt-2.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1",
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-handoff-2.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1",
        "verdict": verdict,
        "output_files": sorted(EXPECTED_OUTPUT_FILES),
        "next_gate": (
            "CENTRAL_PC2W_G1_AND_FRESH_INDEPENDENT_XHIGH_FAST_AUDIT"
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
    if {path.name for path in output_root.iterdir() if path.is_file()} != EXPECTED_OUTPUT_FILES:
        raise RuntimeError("exact output file set violated")
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
