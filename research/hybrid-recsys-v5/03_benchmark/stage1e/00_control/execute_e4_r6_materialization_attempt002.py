from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
DISPATCH_PATH = CONTROL / "rebaseline_v2_e4_r6_m0_m1_attempt002_dispatch.json"
C1_VALIDATOR = CONTROL / "validate_e4_r6_c1r1_packet.py"

DATA_ROOT = Path(
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    r"\official_source\grouplens_ml100k\attempt-002"
)
ENV_ROOT = Path(
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-002"
)

PWSH = Path(
    r"C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\powershell\pwsh.exe"
)
PWSH_BYTES = 301_368
PWSH_SHA256 = "db6dd81183fe57d22e03b911ec9a30a2fd7c40542e97743615355a6fb44f458f"
ENTRY_GATE = "PASS_R6_C1R1_ATTEMPT_002_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1"
DISPATCH_STATUS = "FROZEN_READY_FOR_CENTRAL_R6_M0_R6_M1_ATTEMPT002_EXECUTION"

LANE_CONFIG = {
    "dataset": {
        "packet_key": "dataset_packet",
        "root": DATA_ROOT,
        "hard_timeout_seconds": 1800,
        "maximum_root_bytes": 2_147_483_648,
        "maximum_parent_working_set_bytes": 536_870_912,
        "expected_command_count": 8,
    },
    "environment": {
        "packet_key": "environment_packet",
        "root": ENV_ROOT,
        "hard_timeout_seconds": 7200,
        "maximum_root_bytes": 4_294_967_296,
        "maximum_parent_working_set_bytes": 2_147_483_648,
        "expected_command_count": 25,
    },
}

DROP_ENV_NAMES = {
    "all_proxy",
    "conda_default_env",
    "conda_prefix",
    "cuda_home",
    "cuda_path",
    "cuda_visible_devices",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "pip_config_file",
    "pip_extra_index_url",
    "pip_find_links",
    "pip_index_url",
    "pip_no_index",
    "pip_proxy",
    "pip_trusted_host",
    "pythonhome",
    "pythonpath",
    "virtual_env",
}

DETERMINISTIC_ENV = {
    "CUDA_VISIBLE_DEVICES": "",
    "NO_COLOR": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PIP_NO_INPUT": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "SOURCE_DATE_EPOCH": "1740319008",
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate key: {key}")
        normalized = key.casefold()
        if normalized in folded and folded[normalized] != key:
            raise StrictJsonError(f"case-colliding keys: {folded[normalized]} / {key}")
        folded[normalized] = key
        result[key] = value
    return result


def strict_load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=strict_object
    )
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level object required: {path}")
    return value


def raw_fingerprint(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def canonical_lf_fingerprint(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    payload = text.encode("utf-8")
    return {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def verify_frozen_artifacts(dispatch: dict[str, Any]) -> None:
    rows = dispatch.get("frozen_artifacts", [])
    if not isinstance(rows, list) or len(rows) != dispatch.get("frozen_artifact_count"):
        raise RuntimeError("FROZEN_ARTIFACT_COUNT_MISMATCH")
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("FROZEN_ARTIFACT_ROW_NOT_OBJECT")
        path = ROOT / str(row.get("path", ""))
        if not path.is_file() or path.is_symlink() or is_reparse(path):
            raise RuntimeError(f"FROZEN_ARTIFACT_MISSING_OR_LINK:{path}")
        raw = raw_fingerprint(path)
        canonical = canonical_lf_fingerprint(path)
        if (
            row.get("raw_bytes") != raw["bytes"]
            or row.get("raw_sha256") != raw["sha256"]
            or row.get("canonical_lf_bytes") != canonical["bytes"]
            or row.get("canonical_lf_sha256") != canonical["sha256"]
        ):
            raise RuntimeError(f"FROZEN_ARTIFACT_HASH_MISMATCH:{path}")


def is_reparse(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def windows_under(path: Path, root: Path) -> bool:
    value = str(PureWindowsPath(path)).casefold().rstrip("\\")
    boundary = str(PureWindowsPath(root)).casefold().rstrip("\\")
    return value == boundary or value.startswith(boundary + "\\")


def nearest_existing_parent(path: Path) -> Path:
    probe = path
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            raise RuntimeError(f"NO_EXISTING_PARENT:{path}")
        probe = parent
    return probe


def verify_absent_external_root(path: Path) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"ATTEMPT_ROOT_ALREADY_EXISTS:{path}")
    if windows_under(path, ROOT):
        raise RuntimeError(f"ATTEMPT_ROOT_INSIDE_REPOSITORY:{path}")
    existing = nearest_existing_parent(path)
    probe = existing
    checked: list[str] = []
    floor = Path(r"E:\UIT\cv")
    while True:
        if not probe.is_dir() or probe.is_symlink() or is_reparse(probe):
            raise RuntimeError(f"ANCESTOR_NOT_REAL_DIRECTORY:{probe}")
        checked.append(str(probe))
        if probe == floor:
            break
        parent = probe.parent
        if parent == probe or not windows_under(probe, floor):
            raise RuntimeError(f"ANCESTOR_ESCAPES_FLOOR:{probe}")
        probe = parent
    free = shutil.disk_usage(existing).free
    return {
        "attempt_root": str(path),
        "nearest_existing_parent": str(existing),
        "ancestors_checked": checked,
        "free_bytes": free,
    }


def git_status() -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "GIT_STATUS_FAILED:" + completed.stderr.decode("utf-8", "replace")
        )
    return completed.stdout.decode("utf-8", "strict").splitlines()


def packet_commands(packet: dict[str, Any], lane: str) -> list[dict[str, Any]]:
    if lane == "dataset":
        rows = packet.get("commands", [])
    else:
        rows = [
            row
            for group in packet.get("command_groups", [])
            if isinstance(group, dict)
            for row in group.get("commands", [])
            if isinstance(row, dict)
        ]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(f"COMMAND_ARRAY_INVALID:{lane}")
    return rows


def command_id(row: dict[str, Any]) -> str:
    value = row.get("command_id", row.get("id"))
    if not isinstance(value, str) or not value:
        raise RuntimeError("COMMAND_ID_INVALID")
    return value


def verify_command(row: dict[str, Any]) -> None:
    executable = row.get("executable")
    arguments = row.get("arguments")
    argv = row.get("argv")
    if (
        not isinstance(executable, str)
        or not isinstance(arguments, list)
        or not isinstance(argv, list)
        or not all(isinstance(token, str) for token in arguments)
        or not all(isinstance(token, str) for token in argv)
        or argv != [executable, *arguments]
        or not isinstance(row.get("timeout_seconds"), int)
        or row["timeout_seconds"] <= 0
        or not isinstance(row.get("network"), bool)
    ):
        raise RuntimeError(f"COMMAND_CONTRACT_INVALID:{command_id(row)}")


def sanitized_environment(row: dict[str, Any]) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() not in DROP_ENV_NAMES
        and not key.casefold().startswith("pip_")
    }
    environment.update(DETERMINISTIC_ENV)
    overrides = row.get("environment_overrides", {})
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in overrides.items()
    ):
        raise RuntimeError(f"ENVIRONMENT_OVERRIDES_INVALID:{command_id(row)}")
    environment.update(overrides)
    return environment


def verify_control_plane() -> dict[str, Any]:
    if not PWSH.is_file() or PWSH.is_symlink() or is_reparse(PWSH):
        raise RuntimeError("PWSH_MISSING_LINK_REPARSE_OR_NON_FILE")
    observed = raw_fingerprint(PWSH)
    if observed != {"bytes": PWSH_BYTES, "sha256": PWSH_SHA256}:
        raise RuntimeError("PWSH_BYTE_IDENTITY_MISMATCH")
    script = (
        "$ErrorActionPreference='Stop';$a=Get-Command Get-FileHash;"
        "$b=Get-Command Get-AuthenticodeSignature;"
        "[ordered]@{PSVersion=$PSVersionTable.PSVersion.ToString();"
        "GetFileHashSource=$a.Source;GetAuthenticodeSignatureSource=$b.Source}"
        "|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [str(PWSH), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=ROOT,
        env=sanitized_environment({"command_id": "PWSH_CAPABILITY_PREFLIGHT"}),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        shell=False,
    )
    try:
        capability = json.loads(completed.stdout.decode("utf-8", "strict"))
    except Exception as exc:
        raise RuntimeError("PWSH_CAPABILITY_OUTPUT_INVALID") from exc
    expected = {
        "PSVersion": "7.6.4",
        "GetFileHashSource": "Microsoft.PowerShell.Utility",
        "GetAuthenticodeSignatureSource": "Microsoft.PowerShell.Security",
    }
    if completed.returncode != 0 or capability != expected or completed.stderr:
        raise RuntimeError("PWSH_REQUIRED_CAPABILITY_MISMATCH")
    return {
        "path": str(PWSH),
        "bytes": observed["bytes"],
        "sha256": observed["sha256"],
        "capability": capability,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
    }


def verify_packet_control_plane(commands: list[dict[str, Any]], lane: str) -> None:
    expected = {"dataset": 5, "environment": 3}[lane]
    powershell_rows = [
        row
        for row in commands
        if str(row.get("executable", "")).casefold().endswith(("pwsh.exe", "powershell.exe"))
    ]
    if len(powershell_rows) != expected:
        raise RuntimeError(f"PWSH_COMMAND_COUNT_MISMATCH:{lane}")
    if any(
        row.get("executable") != str(PWSH)
        or row.get("argv", [None])[0] != str(PWSH)
        for row in powershell_rows
    ):
        raise RuntimeError(f"PWSH_COMMAND_NOT_EXACTLY_LOCKED:{lane}")


def tree_observation(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "files": 0, "directories": 0, "bytes": 0}
    if not root.is_dir() or root.is_symlink() or is_reparse(root):
        raise RuntimeError(f"ROOT_LINK_REPARSE_OR_NON_DIRECTORY:{root}")
    total = 0
    files = 0
    directories = 1
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            raise RuntimeError(f"TREE_SCAN_FAILED:{current}:{exc}") from exc
        folded: dict[str, str] = {}
        for entry in entries:
            normalized = entry.name.casefold()
            if normalized in folded and folded[normalized] != entry.name:
                raise RuntimeError(
                    f"TREE_CASE_COLLISION:{current}:{folded[normalized]}:{entry.name}"
                )
            folded[normalized] = entry.name
            path = Path(entry.path)
            info = entry.stat(follow_symlinks=False)
            attributes = getattr(info, "st_file_attributes", 0)
            if entry.is_symlink() or attributes & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            ):
                raise RuntimeError(f"TREE_LINK_OR_REPARSE:{path}")
            if stat.S_ISDIR(info.st_mode):
                directories += 1
                stack.append(path)
            elif stat.S_ISREG(info.st_mode):
                files += 1
                total += info.st_size
            else:
                raise RuntimeError(f"TREE_NON_REGULAR:{path}")
    return {"exists": True, "files": files, "directories": directories, "bytes": total}


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def process_memory(proc: subprocess.Popen[bytes]) -> tuple[int | None, int | None]:
    if os.name != "nt":
        return None, None
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    try:
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            int(proc._handle), ctypes.byref(counters), counters.cb  # type: ignore[attr-defined]
        )
    except (AttributeError, OSError):
        return None, None
    if not ok:
        return None, None
    return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)


def kill_process_tree(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
        )
    else:
        proc.kill()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execute_command(
    row: dict[str, Any],
    lane_config: dict[str, Any],
    packet_started: float,
    baseline_git_status: list[str],
) -> tuple[dict[str, Any], bool]:
    verify_command(row)
    identifier = command_id(row)
    argv = row["argv"]
    working_directory = row.get("working_directory") or str(ROOT)
    cwd = Path(str(working_directory))
    if not cwd.is_dir() or cwd.is_symlink() or is_reparse(cwd):
        raise RuntimeError(f"WORKING_DIRECTORY_INVALID:{identifier}:{cwd}")

    packet_elapsed = time.perf_counter() - packet_started
    if packet_elapsed >= lane_config["hard_timeout_seconds"]:
        raise RuntimeError(f"PACKET_HARD_TIMEOUT_BEFORE_COMMAND:{identifier}")
    command_timeout = min(
        int(row["timeout_seconds"]),
        max(1, int(lane_config["hard_timeout_seconds"] - packet_elapsed)),
    )

    started_at = utc_now()
    started = time.perf_counter()
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=sanitized_environment(row),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    peak_parent = 0
    timed_out = False
    memory_limit_breached = False
    while True:
        remaining = command_timeout - (time.perf_counter() - started)
        if remaining <= 0:
            timed_out = True
            kill_process_tree(proc)
            stdout, stderr = proc.communicate()
            break
        try:
            stdout, stderr = proc.communicate(timeout=min(1.0, remaining))
            break
        except subprocess.TimeoutExpired:
            current, peak = process_memory(proc)
            if peak is not None:
                peak_parent = max(peak_parent, peak)
            if (
                current is not None
                and current > lane_config["maximum_parent_working_set_bytes"]
            ):
                memory_limit_breached = True
                kill_process_tree(proc)
                stdout, stderr = proc.communicate()
                break

    elapsed = time.perf_counter() - started
    root_observation = tree_observation(lane_config["root"])
    disk_breached = root_observation["bytes"] > lane_config["maximum_root_bytes"]
    repository_changed = git_status() != baseline_git_status
    success = (
        proc.returncode == 0
        and not timed_out
        and not memory_limit_breached
        and not disk_breached
        and not repository_changed
    )
    result: dict[str, Any] = {
        "command_id": identifier,
        "argv_canonical_sha256": sha256_bytes(
            json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ),
        "network_declared": row["network"],
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 6),
        "timeout_seconds": command_timeout,
        "timed_out": timed_out,
        "exit_code": proc.returncode,
        "stdout_bytes": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
        "observed_parent_peak_working_set_bytes": peak_parent or None,
        "parent_memory_limit_bytes": lane_config["maximum_parent_working_set_bytes"],
        "parent_memory_limit_breached": memory_limit_breached,
        "attempt_root_observation": root_observation,
        "attempt_root_disk_limit_bytes": lane_config["maximum_root_bytes"],
        "attempt_root_disk_limit_breached": disk_breached,
        "repository_status_changed": repository_changed,
        "retry_count": 0,
        "success": success,
    }
    if not success:
        result["stdout_tail_utf8"] = stdout[-4000:].decode("utf-8", "replace")
        result["stderr_tail_utf8"] = stderr[-4000:].decode("utf-8", "replace")
    return result, success


def common_preflight(require_both_absent: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    dispatch = strict_load(DISPATCH_PATH)
    if (
        dispatch.get("status") != DISPATCH_STATUS
        or dispatch.get("entry_gate") != ENTRY_GATE
    ):
        raise RuntimeError("DISPATCH_NOT_EXECUTION_READY")
    verify_frozen_artifacts(dispatch)
    approval = strict_load(CONTROL / "e4_r5_m2_user_approval_receipt.json")
    if (
        approval.get("authorization_state", {}).get("materialization_authorized") is not True
        or approval.get("authorization_state", {}).get("experiment_execution_authorized") is not False
        or approval.get("authorization_state", {}).get("test_access_authorized") is not False
    ):
        raise RuntimeError("USER_AUTHORITY_REPLAY_FAILED")
    receipt = strict_load(CONTROL / "rebaseline_v2_e4_r6_c1r1_validation_receipt.json")
    if (
        receipt.get("validation_run", {}).get("verdict")
        != ENTRY_GATE
        or receipt.get("validation_run", {}).get("failure_count") != 0
    ):
        raise RuntimeError("C1_RECEIPT_REPLAY_FAILED")
    if git_status():
        raise RuntimeError("REPOSITORY_NOT_CLEAN")
    control_plane = verify_control_plane()
    roots = {
        "dataset": verify_absent_external_root(DATA_ROOT),
        "environment": verify_absent_external_root(ENV_ROOT),
    }
    if require_both_absent and (
        DATA_ROOT.exists() or DATA_ROOT.is_symlink() or ENV_ROOT.exists() or ENV_ROOT.is_symlink()
    ):
        raise RuntimeError("MATERIALIZATION_ROOT_ALREADY_EXISTS")
    return dispatch, {"attempt_roots": roots, "control_plane": control_plane}


def run_preflight() -> int:
    dispatch, preflight = common_preflight(require_both_absent=True)
    validation = subprocess.run(
        [sys.executable, "-B", str(C1_VALIDATOR)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=90,
    )
    stdout = validation.stdout.decode("utf-8", "strict")
    if (
        validation.returncode != 0
        or ENTRY_GATE not in stdout
    ):
        raise RuntimeError(
            "C1_LIVE_REVALIDATION_FAILED:"
            + validation.stderr.decode("utf-8", "replace")[-2000:]
        )
    result = {
        "schema_version": "stage1e-r6-m0-m1-attempt002-central-preflight-result-1.0",
        "event": "preflight_complete",
        "passed": True,
        "dispatch_sha256": raw_fingerprint(DISPATCH_PATH)["sha256"],
        "frozen_artifacts_verified": dispatch.get("frozen_artifact_count"),
        "c1_live_revalidation_exit_code": validation.returncode,
        "c1_live_revalidation_stdout_sha256": sha256_bytes(validation.stdout),
        "roots": preflight["attempt_roots"],
        "control_plane": preflight["control_plane"],
        "repository_clean": True,
        "source_date_epoch": DETERMINISTIC_ENV["SOURCE_DATE_EPOCH"],
        "training_evaluation_test_authorized": False,
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True), flush=True)
    return 0


def run_lane(lane: str) -> int:
    lane_config = LANE_CONFIG[lane]
    dispatch = strict_load(DISPATCH_PATH)
    if (
        dispatch.get("status") != DISPATCH_STATUS
        or dispatch.get("entry_gate") != ENTRY_GATE
    ):
        raise RuntimeError("DISPATCH_NOT_EXECUTION_READY")
    verify_frozen_artifacts(dispatch)
    verify_control_plane()
    if git_status():
        raise RuntimeError("REPOSITORY_NOT_CLEAN")
    root_preflight = verify_absent_external_root(lane_config["root"])
    if root_preflight["free_bytes"] < lane_config["maximum_root_bytes"] + 1_073_741_824:
        raise RuntimeError(f"INSUFFICIENT_FREE_SPACE:{lane}")

    lane_record = dispatch.get("lanes", {}).get(lane)
    if not isinstance(lane_record, dict):
        raise RuntimeError(f"DISPATCH_LANE_MISSING:{lane}")
    packet_path = ROOT / str(lane_record.get("packet_path", ""))
    packet = strict_load(packet_path)
    commands = packet_commands(packet, lane)
    if len(commands) != lane_config["expected_command_count"]:
        raise RuntimeError(f"COMMAND_COUNT_MISMATCH:{lane}")
    expected_order = packet.get("command_order", [])
    if [command_id(row) for row in commands] != expected_order:
        raise RuntimeError(f"COMMAND_ORDER_MISMATCH:{lane}")
    verify_packet_control_plane(commands, lane)

    baseline_status = git_status()
    packet_started = time.perf_counter()
    packet_started_at = utc_now()
    results: list[dict[str, Any]] = []
    print(
        json.dumps(
            {
                "event": "packet_started",
                "lane": lane,
                "started_at_utc": packet_started_at,
                "command_count": len(commands),
                "attempt_root": str(lane_config["root"]),
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        flush=True,
    )
    passed = True
    for row in commands:
        result, command_passed = execute_command(
            row, lane_config, packet_started, baseline_status
        )
        results.append(result)
        print(
            json.dumps(
                {"event": "command_complete", "lane": lane, **result},
                ensure_ascii=True,
                sort_keys=True,
            ),
            flush=True,
        )
        if not command_passed:
            passed = False
            break

    summary = {
        "schema_version": "stage1e-r6-attempt002-central-materialization-run-result-1.0",
        "event": "packet_complete",
        "lane": lane,
        "passed": passed and len(results) == len(commands),
        "packet_path": packet_path.relative_to(ROOT).as_posix(),
        "packet_raw_sha256": raw_fingerprint(packet_path)["sha256"],
        "started_at_utc": packet_started_at,
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(time.perf_counter() - packet_started, 6),
        "commands_expected": len(commands),
        "commands_executed": len(results),
        "commands_succeeded": sum(1 for row in results if row["success"]),
        "commands": results,
        "final_attempt_root_observation": tree_observation(lane_config["root"]),
        "repository_clean_after_run": git_status() == baseline_status == [],
        "retry_count": 0,
        "scientific_execution_performed": False,
        "test_accessed": False,
        "benchmark_admitted": False,
    }
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True), flush=True)
    return 0 if summary["passed"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "dataset", "environment"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "preflight":
            return run_preflight()
        return run_lane(args.mode)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": "runner_fail_closed",
                    "mode": args.mode,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "training_evaluation_test_authorized": False,
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
