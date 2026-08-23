#!/usr/bin/env python3
"""Execute one authorized Docker Desktop P1 query-only start/query/stop probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOCKER = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
WSL = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wsl.exe"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

EXPECTED_DOCKER_DESKTOP_SHA256 = "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce"
EXPECTED_AUTH_PATH = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc2w_p1_user_authorization_and_model_override.json"
)
EXPECTED_REQUIREMENTS_PATH = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
)

PROHIBITED_DOCKER_SUBCOMMANDS = {
    "pull",
    "build",
    "create",
    "run",
    "exec",
    "commit",
    "import",
    "load",
    "tag",
    "push",
    "login",
    "logout",
    "rm",
    "rmi",
    "prune",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def decode_output(value: bytes) -> str:
    if not value:
        return ""
    if value.count(b"\x00") > max(1, len(value) // 8):
        return value.decode("utf-16-le", errors="replace")
    return value.decode("utf-8", errors="replace")


def run_command(
    command_id: str,
    argv: list[str],
    *,
    timeout_seconds: int,
) -> tuple[dict[str, Any], bytes, bytes]:
    started_at = utc_now()
    start_monotonic = time.monotonic()
    timed_out = False
    exit_code: int | None
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        exit_code = None
        timed_out = True
    ended_at = utc_now()
    receipt = {
        "command_id": command_id,
        "argv": argv,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "started_at": started_at,
        "ended_at": ended_at,
        "elapsed_seconds": round(time.monotonic() - start_monotonic, 6),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_bytes": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
    }
    return receipt, stdout, stderr


def parse_json_output(value: bytes) -> Any:
    text = decode_output(value).strip()
    return json.loads(text) if text else None


def parse_json_lines(value: bytes) -> list[Any]:
    rows: list[Any] = []
    for line in decode_output(value).splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


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


def material_passport(created_at: str) -> dict[str, Any]:
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "run",
        "origin_date": created_at,
        "verification_status": "UNVERIFIED",
        "version_label": "stage1e_e4_r6_pc2w_p1_execution_v1",
        "upstream_dependencies": [
            "stage1e_e4_r6_pc2w_p1_user_authorization_v1",
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


def docker_subcommand_is_allowed(argv: list[str]) -> bool:
    if not argv or Path(argv[0]).resolve() != DOCKER.resolve():
        return True
    tokens = [token.casefold() for token in argv[1:]]
    if any(token in PROHIBITED_DOCKER_SUBCOMMANDS for token in tokens):
        return False
    if "system" in tokens and "prune" in tokens:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    expected_head = args.expected_head.lower()

    if output_root.exists():
        raise RuntimeError(f"immutable output root already exists: {output_root}")
    if repo_root not in output_root.parents:
        raise RuntimeError("output root must be inside the repository")
    for required in (DOCKER, DOCKER_DESKTOP, WSL, POWERSHELL):
        if not required.is_file():
            raise RuntimeError(f"required executable missing: {required}")
    if sha256_file(DOCKER_DESKTOP) != EXPECTED_DOCKER_DESKTOP_SHA256:
        raise RuntimeError("Docker Desktop executable hash changed")

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        shell=False,
    ).stdout.decode("ascii").strip().lower()
    if head != expected_head:
        raise RuntimeError(f"HEAD mismatch: expected {expected_head}, observed {head}")

    auth = json.loads((repo_root / EXPECTED_AUTH_PATH).read_text(encoding="utf-8"))
    requirements = json.loads(
        (repo_root / EXPECTED_REQUIREMENTS_PATH).read_text(encoding="utf-8")
    )
    if auth["user_decision"]["decision"] != "AUTHORIZE_PC2W_P1_EXECUTION":
        raise RuntimeError("P1 user authorization missing")
    if auth["user_decision"]["automatic_retry_authorized"] is not False:
        raise RuntimeError("automatic retry must remain false")

    created_at = utc_now()
    output_root.mkdir(parents=True, exist_ok=False)
    passport = material_passport(created_at)
    command_receipts: list[dict[str, Any]] = []
    raw: dict[str, tuple[bytes, bytes]] = {}

    def invoke(command_id: str, argv: list[str], timeout_seconds: int = 30) -> int | None:
        if not docker_subcommand_is_allowed(argv):
            raise RuntimeError(f"prohibited Docker command in frozen runner: {argv}")
        receipt, stdout, stderr = run_command(
            command_id, argv, timeout_seconds=timeout_seconds
        )
        command_receipts.append(receipt)
        raw[command_id] = (stdout, stderr)
        return receipt["exit_code"]

    before_disk = disk_snapshot()
    invoke("P00_WSL_LIST_BEFORE", [str(WSL), "--list", "--verbose"])
    invoke("P01_DOCKER_DESKTOP_STATUS_BEFORE", [str(DOCKER), "desktop", "status"])
    invoke(
        "P02_DAEMON_VERSION_BEFORE",
        [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .Server}}"],
    )

    start_exit = invoke(
        "P03_DOCKER_DESKTOP_START_ONCE",
        [str(DOCKER), "desktop", "start"],
        timeout_seconds=180,
    )
    startup_attempted = True
    query_ids: list[str] = []

    if start_exit == 0:
        query_specs = [
            ("P04_DOCKER_DESKTOP_STATUS_DURING", [str(DOCKER), "desktop", "status"]),
            ("P05_DOCKER_VERSION", [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .}}"]),
            ("P06_DOCKER_INFO", [str(DOCKER), "--context", "desktop-linux", "info", "--format", "{{json .}}"]),
            ("P07_CONTEXT_INSPECT", [str(DOCKER), "context", "inspect", "desktop-linux"]),
            ("P08_IMAGE_LIST", [str(DOCKER), "--context", "desktop-linux", "image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}"]),
            ("P09_CONTAINER_LIST", [str(DOCKER), "--context", "desktop-linux", "container", "ls", "-a", "--no-trunc", "--format", "{{json .}}"]),
            ("P10_SYSTEM_DF", [str(DOCKER), "--context", "desktop-linux", "system", "df", "--format", "{{json .}}"]),
            ("P11_WSL_LIST_DURING", [str(WSL), "--list", "--verbose"]),
            (
                "P12_PROCESS_INVENTORY",
                [
                    str(POWERSHELL),
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); Get-Process -ErrorAction SilentlyContinue | Where-Object {$n -contains $_.ProcessName} | Select-Object ProcessName,Id,Path,StartTime | ConvertTo-Json -Depth 3 -Compress",
                ],
            ),
            (
                "P13_NETWORK_CONNECTION_INVENTORY",
                [
                    str(POWERSHELL),
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$n=@('Docker Desktop','com.docker.backend','com.docker.build','wsl','wslhost','vmmemWSL'); $p=@(Get-Process -ErrorAction SilentlyContinue | Where-Object {$n -contains $_.ProcessName}); $ids=@($p.Id); Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids -contains $_.OwningProcess} | Select-Object State,LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess | ConvertTo-Json -Depth 3 -Compress",
                ],
            ),
        ]
        for query_id, argv in query_specs:
            invoke(query_id, argv)
            query_ids.append(query_id)

    stop_exit = None
    if startup_attempted:
        stop_exit = invoke(
            "P14_DOCKER_DESKTOP_STOP_ONCE",
            [str(DOCKER), "desktop", "stop"],
            timeout_seconds=180,
        )

    invoke("P15_DOCKER_DESKTOP_STATUS_AFTER", [str(DOCKER), "desktop", "status"])
    invoke(
        "P16_DAEMON_VERSION_AFTER",
        [str(DOCKER), "--context", "desktop-linux", "version", "--format", "{{json .Server}}"],
    )
    invoke("P17_WSL_LIST_AFTER", [str(WSL), "--list", "--verbose"])
    after_disk = disk_snapshot()

    version_data: dict[str, Any] = {}
    info_data: dict[str, Any] = {}
    context_data: Any = None
    images: list[Any] = []
    containers: list[Any] = []
    system_df: list[Any] = []
    processes: Any = []
    connections: Any = []
    parse_failures: list[str] = []

    def parse_if_success(command_id: str, parser_fn: Any) -> Any:
        receipt = next(row for row in command_receipts if row["command_id"] == command_id)
        if receipt["exit_code"] != 0:
            return None
        try:
            return parser_fn(raw[command_id][0])
        except Exception as exc:
            parse_failures.append(f"{command_id}:{type(exc).__name__}:{exc}")
            return None

    if start_exit == 0:
        version_data = parse_if_success("P05_DOCKER_VERSION", parse_json_output) or {}
        info_data = parse_if_success("P06_DOCKER_INFO", parse_json_output) or {}
        context_data = parse_if_success("P07_CONTEXT_INSPECT", parse_json_output)
        images = parse_if_success("P08_IMAGE_LIST", parse_json_lines) or []
        containers = parse_if_success("P09_CONTAINER_LIST", parse_json_lines) or []
        system_df_value = parse_if_success("P10_SYSTEM_DF", parse_json_lines)
        system_df = system_df_value or []
        processes = parse_if_success("P12_PROCESS_INVENTORY", parse_json_output) or []
        connections = parse_if_success("P13_NETWORK_CONNECTION_INVENTORY", parse_json_output) or []

    server = version_data.get("Server") or {}
    info_whitelist = {
        "ID": info_data.get("ID"),
        "ServerVersion": info_data.get("ServerVersion"),
        "OperatingSystem": info_data.get("OperatingSystem"),
        "OSType": info_data.get("OSType"),
        "Architecture": info_data.get("Architecture"),
        "KernelVersion": info_data.get("KernelVersion"),
        "Driver": info_data.get("Driver"),
        "CgroupDriver": info_data.get("CgroupDriver"),
        "CgroupVersion": info_data.get("CgroupVersion"),
        "DockerRootDir": info_data.get("DockerRootDir"),
        "SecurityOptions": info_data.get("SecurityOptions"),
        "Runtimes": sorted((info_data.get("Runtimes") or {}).keys()),
        "DefaultRuntime": info_data.get("DefaultRuntime"),
        "NCPU": info_data.get("NCPU"),
        "MemTotal": info_data.get("MemTotal"),
        "Containers": info_data.get("Containers"),
        "ContainersRunning": info_data.get("ContainersRunning"),
        "ContainersPaused": info_data.get("ContainersPaused"),
        "ContainersStopped": info_data.get("ContainersStopped"),
        "Images": info_data.get("Images"),
        "LiveRestoreEnabled": info_data.get("LiveRestoreEnabled"),
        "Isolation": info_data.get("Isolation"),
        "ExperimentalBuild": info_data.get("ExperimentalBuild"),
        "DefaultAddressPools": info_data.get("DefaultAddressPools"),
        "HttpProxyConfigured": bool(info_data.get("HttpProxy")),
        "HttpsProxyConfigured": bool(info_data.get("HttpsProxy")),
        "NoProxyConfigured": bool(info_data.get("NoProxy")),
    }

    sanitized_images = [
        {
            "ID": row.get("ID"),
            "Digest": row.get("Digest"),
            "Size": row.get("Size"),
            "row_sha256": sha256_bytes(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ),
        }
        for row in images
    ]
    sanitized_containers = [
        {
            "ID": row.get("ID"),
            "State": row.get("State"),
            "Status": row.get("Status"),
            "row_sha256": sha256_bytes(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ),
        }
        for row in containers
    ]

    if isinstance(connections, dict):
        connections = [connections]
    sanitized_connections: list[dict[str, Any]] = []
    for row in connections if isinstance(connections, list) else []:
        remote = str(row.get("RemoteAddress", ""))
        sanitized_connections.append(
            {
                "State": row.get("State"),
                "LocalPort": row.get("LocalPort"),
                "RemoteAddressSha256": sha256_bytes(remote.encode("utf-8")),
                "RemotePort": row.get("RemotePort"),
                "OwningProcess": row.get("OwningProcess"),
            }
        )

    by_id = {row["command_id"]: row for row in command_receipts}
    query_success = start_exit == 0 and all(by_id[q]["exit_code"] == 0 for q in query_ids)
    backend_linux = (
        str(info_whitelist.get("OSType", "")).casefold() == "linux"
        and str(info_whitelist.get("Architecture", "")).casefold() in {"x86_64", "amd64"}
    )
    during_status = decode_output(raw.get("P04_DOCKER_DESKTOP_STATUS_DURING", (b"", b""))[0]).casefold()
    after_status = decode_output(raw["P15_DOCKER_DESKTOP_STATUS_AFTER"][0]).casefold()
    after_daemon_unavailable = by_id["P16_DAEMON_VERSION_AFTER"]["exit_code"] != 0
    after_wsl = decode_output(raw["P17_WSL_LIST_AFTER"][0]).casefold()
    after_distro_stopped = "docker-desktop" in after_wsl and "stopped" in after_wsl
    disk_pass = (
        after_disk["c"]["free_bytes"] >= 20 * 1024**3
        and after_disk["e"]["free_bytes"] >= 50 * 1024**3
    )

    pass_conditions = {
        "startup_exit_zero": start_exit == 0,
        "during_status_running": "running" in during_status,
        "all_query_commands_exit_zero": query_success,
        "backend_linux_amd64": backend_linux,
        "parse_failures_absent": not parse_failures,
        "stop_exit_zero": stop_exit == 0,
        "after_status_stopped": "stopped" in after_status,
        "after_daemon_unavailable": after_daemon_unavailable,
        "after_docker_desktop_distro_stopped": after_distro_stopped,
        "disk_thresholds_pass": disk_pass,
        "prohibited_commands_issued": False,
        "automatic_retry_count_zero": True,
    }
    verdict = (
        "PASS_PC2W_P1_QUERY_EVIDENCE_READY_FOR_CENTRAL_G1"
        if all(value is True for value in pass_conditions.values())
        else "FAIL_CLOSED_PC2W_BACKEND_OR_POLICY_NOT_ADMISSIBLE"
    )

    command_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-command-receipts-1.0",
        "material_passport": passport,
        "entry_checkpoint": head,
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "commands": command_receipts,
        "automatic_retry_count": 0,
        "raw_stdout_or_stderr_persisted": False,
    }
    inventory_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-runtime-inventory-1.0",
        "material_passport": passport,
        "server_version": server,
        "docker_info_whitelist": info_whitelist,
        "context": context_data,
        "images": sanitized_images,
        "containers": sanitized_containers,
        "system_df": system_df,
        "processes": processes,
        "connections_redacted": sanitized_connections,
        "before_disk": before_disk,
        "after_disk": after_disk,
        "disk_delta_free_bytes": {
            key: after_disk[key]["free_bytes"] - before_disk[key]["free_bytes"]
            for key in ("c", "e")
        },
        "proxy_values_persisted": False,
        "parse_failures": parse_failures,
    }
    execution_document = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-execution-receipt-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1",
        "created_at": created_at,
        "entry_checkpoint": head,
        "requirements_sha256": sha256_file(repo_root / EXPECTED_REQUIREMENTS_PATH),
        "authorization_sha256": sha256_file(repo_root / EXPECTED_AUTH_PATH),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "output_root": str(output_root),
        "startup_attempts": 1,
        "query_retry_count": 0,
        "stop_attempts": 1 if startup_attempted else 0,
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
        "schema_version": "stage1e-e4-r6-pc2w-p1-handoff-1.0",
        "material_passport": passport,
        "stage_id": "E4-R6-PC2W-P1",
        "verdict": verdict,
        "output_files": [
            "command_receipts.json",
            "runtime_inventory.json",
            "p1_execution_receipt.json",
            "p1_handoff.json",
        ],
        "next_gate": (
            "CENTRAL_PC2W_G1_AND_INDEPENDENT_XHIGH_FAST_AUDIT"
            if verdict == "PASS_PC2W_P1_QUERY_EVIDENCE_READY_FOR_CENTRAL_G1"
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

    print(
        json.dumps(
            {
                "verdict": verdict,
                "output_root": str(output_root),
                "commands_recorded": len(command_receipts),
                "automatic_retry_count": 0,
            },
            indent=2,
        )
    )
    return 0 if verdict == "PASS_PC2W_P1_QUERY_EVIDENCE_READY_FOR_CENTRAL_G1" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "verdict": "HANDOFF_INCOMPLETE",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
