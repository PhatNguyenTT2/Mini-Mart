#!/usr/bin/env python3
"""Offline, read-only static validator for the Attempt-007 admission packet.

The validator parses the runner as inert source.  It never imports or invokes
the runner and never calls Docker, WSL, PowerShell, process/TCP, named-pipe, or
network probes.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt007_admission_observation.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt007_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt007_execution_authorization.json"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt007_static_packet.py"
STATE = CONTROL / "pipeline_state_stage1e.json"
ATTEMPT006_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt006_baseline_remediation_contract.json"
ATTEMPT006_AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt006_user_authorization.json"
ATTEMPT006_RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt006_baseline_remediation.py"
ATTEMPT006_VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt006_static_packet.py"
ATTEMPT006_AUDIT = CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt006_baseline_packet_audit_receipt.json"
ATTEMPT006_OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ao/"
    "E4_R6PC2W_P1_attempt006_baseline_remediation"
)
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ap/"
    "E4_R6PC2W_P1_attempt007_admission_observation"
)
PACKET_PARENT = "594076231cbd12d5a3ffd61b358a38033bbaca85"
PACKET_FILES = {CONTRACT, AUTHORIZATION, RUNNER, VALIDATOR}
OUTPUT_FILES = {
    "admission_observation.json",
    "command_receipts.json",
    "execution_receipt.json",
    "handoff.json",
}
FROZEN_ATTEMPT006_SHA256 = {
    STATE: "3253d9773b0525b4156cfefc15f4f4ef5866cb8b32d9d5f3c423fa0fa4c64be4",
    ATTEMPT006_CONTRACT: "fa7a08d98de43562a7f02b30be1dc83e8da451ab54ba850cedbd96f1d6364372",
    ATTEMPT006_AUTHORIZATION: "0c18926c5d23ea3f1e666adb42dd0ec8debdce566c2dceddf00f42206d90ff57",
    ATTEMPT006_RUNNER: "ba377b0be805160c979f169c093ab862403b74328d54917baa60199078727c99",
    ATTEMPT006_VALIDATOR: "238cbbe25c60eac880b81a96c399514589e11e201c48e01c3fe3e127899b5b0a",
    ATTEMPT006_AUDIT: "cdab7460e62d86a95d17cd67874c4dfacc17c8152bcc6a1e07dcfaacbdaf6c66",
    ATTEMPT006_OUTPUT / "command_receipts.json":
        "0c708d53732aeaaa7c525111bd7086fce943cce5ffab2d580f293942f53ffe2c",
    ATTEMPT006_OUTPUT / "p1_execution_receipt.json":
        "430becb7502b90058614671832daf6604aaa0d00166bd200719383570cae2900",
    ATTEMPT006_OUTPUT / "p1_handoff.json":
        "5a0847ed7229e0de5b7ebc9e40ec4111304ac6a1803cf2de5b7796edc4d0c955",
    ATTEMPT006_OUTPUT / "runtime_inventory.json":
        "2c07fd7b7bc73d51d58071999eb062831e75261a2674d57df796cdf6bc3a5298",
}
EXPECTED_OUTPUT_LIST = sorted(OUTPUT_FILES)
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03",
    "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]
EXPECTED_LITERAL_INVOKES = [
    ("P00", "WSL_VERBOSE"),
    ("P01", "WSL_RUNNING"),
    ("P02", "PROCESS_POPULATION"),
    ("P03", "TCP_POPULATION"),
    ("S00", "DOCKER_DESKTOP_START"),
    ("D00", "WSL_VERBOSE"),
    ("D01", "PROCESS_IDENTITY"),
    ("D02", "TCP_IDENTITY"),
    ("D03", "DOCKER_VERSION"),
    ("D04", "DOCKER_INFO"),
    ("D05", "DOCKER_CONTEXT_INSPECT"),
    ("D06", "DOCKER_DESKTOP_FILE_IDENTITY"),
    ("F00", "DOCKER_DESKTOP_STOP"),
    ("F01", "WSL_SHUTDOWN"),
]
EXPECTED_WINDOW_INVOKES = [
    ("S00", "DOCKER_DESKTOP_START"),
    ("D00", "WSL_VERBOSE"),
    ("D01", "PROCESS_IDENTITY"),
    ("D02", "TCP_IDENTITY"),
    ("D03", "DOCKER_VERSION"),
    ("D04", "DOCKER_INFO"),
    ("D05", "DOCKER_CONTEXT_INSPECT"),
    ("D06", "DOCKER_DESKTOP_FILE_IDENTITY"),
]
EXPECTED_SNAPSHOT_CALLS = [
    ("A", "A00", "A01", "A02", "A03"),
    ("B", "B00", "B01", "B02", "B03"),
    ("C", "C00", "C01", "C02", "C03"),
]
EXPECTED_COMMAND_TEMPLATES = {
    "WSL_VERBOSE": ["WSL", "--list", "--verbose"],
    "WSL_RUNNING": ["WSL", "--list", "--running", "--quiet"],
    "PROCESS_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "PROCESS_POPULATION_QUERY",
    ],
    "TCP_POPULATION": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "TCP_POPULATION_QUERY",
    ],
    "DOCKER_DESKTOP_START": ["DOCKER", "desktop", "start"],
    "DOCKER_DESKTOP_STOP": ["DOCKER", "desktop", "stop"],
    "WSL_SHUTDOWN": ["WSL", "--shutdown"],
    "PROCESS_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "PROCESS_IDENTITY_QUERY",
    ],
    "TCP_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "TCP_IDENTITY_QUERY",
    ],
    "DOCKER_VERSION": [
        "DOCKER", "--context", "desktop-linux", "version", "--format", "{{json .}}",
    ],
    "DOCKER_INFO": [
        "DOCKER", "--context", "desktop-linux", "info", "--format", "{{json .}}",
    ],
    "DOCKER_CONTEXT_INSPECT": ["DOCKER", "context", "inspect", "desktop-linux"],
    "DOCKER_DESKTOP_FILE_IDENTITY": [
        "POWERSHELL", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
        "DOCKER_DESKTOP_FILE_IDENTITY_QUERY",
    ],
}
EXPECTED_MODEL_POLICY = {
    "requested_model": "gpt-5.6-sol",
    "requested_reasoning_effort": "xhigh",
    "requested_service_tier": "default",
    "requested_display_name": "Sol XHigh Standard",
    "fast_or_priority_allowed": False,
    "actual_model": "UNOBSERVABLE",
    "actual_reasoning_effort": "UNOBSERVABLE",
    "actual_service_tier": "UNOBSERVABLE",
    "fast_or_priority_observability": "UNOBSERVABLE",
}
ERROR_CODES = {"NONE", "PROBE_EXCEPTION", "COMMAND_FAILED", "OUTPUT_MALFORMED"}
TARGET_PROCESS_NAMES = {
    "docker desktop", "com.docker.backend", "com.docker.build",
    "com.docker.proxy", "dockerd", "vpnkit", "wslrelay",
}
REQUIRED_DURING_PROCESS_NAMES = {"docker desktop", "com.docker.backend"}


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        folded_key = key.casefold()
        if key in result or folded_key in folded:
            raise DuplicateKeyError(key)
        result[key] = value
        folded.add(folded_key)
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def strict_json_bytes(value: bytes) -> Any:
    return json.loads(
        value.decode("utf-8", errors="strict"),
        object_pairs_hook=strict_pairs,
        parse_constant=reject_nonfinite,
    )


def strict_json_object(value: bytes) -> dict[str, Any]:
    result = strict_json_bytes(value)
    if not isinstance(result, dict):
        raise ValueError("JSON root must be an object")
    return result


def canonical_lf(value: bytes) -> bytes:
    normalized = value.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("bare carriage return")
    return normalized


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    ).stdout


def git_text(root: Path, *args: str) -> str:
    return run_git(root, *args).decode("utf-8", errors="strict").strip()


def git_blob(root: Path, revision: str, path: Path) -> bytes:
    return run_git(root, "cat-file", "blob", f"{revision}:{path.as_posix()}")


def assigned_literal(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def assigned_path_string(tree: ast.AST, name: str) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "Path"
            and len(value.args) == 1
            and not value.keywords
        ):
            literal = ast.literal_eval(value.args[0])
            if isinstance(literal, str):
                return literal
    raise KeyError(name)


def find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    return next(
        (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name),
        None,
    )


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def literal_call_tuple(node: ast.Call, function_name: str, width: int) -> tuple[str, ...] | None:
    if call_name(node) != function_name or len(node.args) < width:
        return None
    values: list[str] = []
    for argument in node.args[:width]:
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            return None
        values.append(argument.value)
    return tuple(values)


def literal_calls(tree: ast.AST, function_name: str, width: int) -> list[tuple[str, ...]]:
    rows = [
        (node.lineno, value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (value := literal_call_tuple(node, function_name, width)) is not None
    ]
    return [value for _, value in sorted(rows)]


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def parse_dotnet_utc(value: Any) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z", value
    ) is None:
        raise ValueError("invalid .NET UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp is not UTC")
    return parsed


def parse_rfc3339_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("invalid RFC3339 UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp is not UTC")
    return parsed


def validate_population_envelope(value: Any, kind: str) -> tuple[bool, bool]:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        return False, False
    available, count, rows = value["Available"], value["Count"], value["Rows"]
    error_code, error_hash = value["ErrorCode"], value["ErrorTypeHash"]
    if not isinstance(available, bool):
        return False, False
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return False, False
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return False, False
    if count != len(rows) or error_code not in ERROR_CODES:
        return False, False
    if available:
        if error_code != "NONE" or error_hash is not None:
            return False, False
    elif (
        error_code == "NONE" or not valid_hash(error_hash) or count != 0 or rows
    ):
        return False, False
    fields = {"Name", "ProcessId"} if kind == "process" else {"Name", "ProcessId", "ConnectionCount"}
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if set(row) != fields:
            return False, False
        name, process_id = row["Name"], row["ProcessId"]
        if not isinstance(name, str) or name != name.casefold() or name not in TARGET_PROCESS_NAMES:
            return False, False
        if not isinstance(process_id, int) or isinstance(process_id, bool) or process_id <= 0:
            return False, False
        key = (name, process_id)
        if key in seen:
            return False, False
        seen.add(key)
        if kind == "tcp":
            connections = row["ConnectionCount"]
            if not isinstance(connections, int) or isinstance(connections, bool) or connections <= 0:
                return False, False
    if rows != sorted(rows, key=lambda row: (row["Name"], row["ProcessId"])):
        return False, False
    return True, available and count == 0 and rows == []


def validate_rich_process(value: Any) -> bool:
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        return False
    if value["Available"] is not True or value["ErrorCode"] != "NONE" or value["ErrorTypeHash"] is not None:
        return False
    count, rows = value["Count"], value["Rows"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return False
    if not isinstance(rows, list) or count != len(rows):
        return False
    fields = {
        "Name", "ProcessId", "ParentProcessId", "ParentNameHash",
        "ParentExecutablePathHash", "ExecutablePathHash", "ExecutableFileSha256",
        "FileVersion", "AuthenticodeStatus", "SignerSubjectHash",
        "CreationTimeUtc", "CommandLineHash",
    }
    seen: set[int] = set()
    try:
        for row in rows:
            if not isinstance(row, dict) or set(row) != fields:
                return False
            if row["Name"] not in TARGET_PROCESS_NAMES or row["Name"] != row["Name"].casefold():
                return False
            for field in ("ProcessId", "ParentProcessId"):
                if not isinstance(row[field], int) or isinstance(row[field], bool) or row[field] <= 0:
                    return False
            if row["ProcessId"] in seen:
                return False
            seen.add(row["ProcessId"])
            if any(not valid_hash(row[field]) for field in (
                "ParentNameHash", "ParentExecutablePathHash", "ExecutablePathHash",
                "ExecutableFileSha256", "SignerSubjectHash", "CommandLineHash",
            )):
                return False
            if not isinstance(row["FileVersion"], str) or not row["FileVersion"].strip():
                return False
            if row["AuthenticodeStatus"] != "Valid":
                return False
            parse_dotnet_utc(row["CreationTimeUtc"])
    except (KeyError, TypeError, ValueError):
        return False
    if rows != sorted(rows, key=lambda row: (row["Name"], row["ProcessId"])):
        return False
    return REQUIRED_DURING_PROCESS_NAMES.issubset({row["Name"] for row in rows})


def validate_rich_tcp(value: Any, process_value: Any) -> bool:
    if not validate_rich_process(process_value):
        return False
    required = {"Available", "Count", "Rows", "ErrorCode", "ErrorTypeHash"}
    if not isinstance(value, dict) or set(value) != required:
        return False
    if value["Available"] is not True or value["ErrorCode"] != "NONE" or value["ErrorTypeHash"] is not None:
        return False
    count, rows = value["Count"], value["Rows"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return False
    if not isinstance(rows, list) or count != len(rows):
        return False
    process_keys = {(row["Name"], row["ProcessId"]) for row in process_value["Rows"]}
    fields = {
        "ProcessName", "ProcessId", "State", "LocalAddressHash", "LocalPort",
        "RemoteAddressHash", "RemotePort",
    }
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            return False
        if (row["ProcessName"], row["ProcessId"]) not in process_keys:
            return False
        if not isinstance(row["State"], str) or not row["State"].strip():
            return False
        if not valid_hash(row["LocalAddressHash"]) or not valid_hash(row["RemoteAddressHash"]):
            return False
        for field in ("LocalPort", "RemotePort"):
            if not isinstance(row[field], int) or isinstance(row[field], bool) or not 0 <= row[field] <= 65535:
                return False
        identity = tuple(row[field] for field in (
            "ProcessName", "ProcessId", "State", "LocalAddressHash", "LocalPort",
            "RemoteAddressHash", "RemotePort",
        ))
        if identity in seen:
            return False
        seen.add(identity)
    return rows == sorted(
        rows,
        key=lambda row: (
            row["ProcessName"], row["ProcessId"], row["State"],
            row["LocalPort"], row["RemotePort"],
        ),
    )


def validate_docker_identity_fixture(version: Any, info: Any, context: Any) -> bool:
    try:
        if not isinstance(version, dict) or set(version) != {"Client", "Server"}:
            return False
        client, server = version["Client"], version["Server"]
        if not isinstance(client, dict) or not isinstance(server, dict) or not isinstance(info, dict):
            return False
        for field in ("Version", "ApiVersion", "DefaultAPIVersion", "GitCommit", "GoVersion", "Os", "Arch", "BuildTime", "Context"):
            if not isinstance(client.get(field), str) or not client[field].strip():
                return False
        for field in ("Version", "ApiVersion", "MinAPIVersion", "GitCommit", "GoVersion", "Os", "Arch", "KernelVersion", "BuildTime"):
            if not isinstance(server.get(field), str) or not server[field].strip():
                return False
        if not isinstance(server.get("Experimental"), bool):
            return False
        parse_rfc3339_utc(client["BuildTime"])
        parse_rfc3339_utc(server["BuildTime"])
        for field in (
            "ServerVersion", "OperatingSystem", "OSType", "Architecture",
            "KernelVersion", "Driver", "CgroupDriver", "CgroupVersion",
            "DockerRootDir", "DefaultRuntime", "ID",
        ):
            if not isinstance(info.get(field), str) or not info[field].strip():
                return False
        for field in ("NCPU", "MemTotal"):
            if not isinstance(info.get(field), int) or isinstance(info[field], bool) or info[field] <= 0:
                return False
        for field in ("Containers", "ContainersRunning", "ContainersPaused", "ContainersStopped", "Images"):
            if not isinstance(info.get(field), int) or isinstance(info[field], bool) or info[field] < 0:
                return False
        for field in ("LiveRestoreEnabled", "ExperimentalBuild"):
            if not isinstance(info.get(field), bool):
                return False
        containerd = info.get("ContainerdCommit")
        runtimes = info.get("Runtimes")
        security = info.get("SecurityOptions")
        if not isinstance(containerd, dict) or not isinstance(containerd.get("ID"), str) or not containerd["ID"]:
            return False
        if not isinstance(runtimes, dict) or not runtimes:
            return False
        if not isinstance(security, list) or any(not isinstance(row, str) or not row for row in security):
            return False
        if context != {"Name": "desktop-linux", "DockerEndpointHostClass": "DESKTOP_LINUX_NPIPE_EXACT"}:
            return False
        return all((
            client["Context"] == "desktop-linux",
            server["Os"].casefold() == "linux",
            server["Arch"].casefold() in {"amd64", "x86_64"},
            info["ServerVersion"] == server["Version"],
            info["OSType"].casefold() == server["Os"].casefold(),
            info["Architecture"].casefold() == server["Arch"].casefold(),
            info["KernelVersion"] == server["KernelVersion"],
        ))
    except (KeyError, TypeError, ValueError):
        return False


def packet_hashes_match(actual: dict[str, str], expected: dict[str, str]) -> bool:
    return actual == expected and all(valid_hash(value) for value in actual.values())


def exact_output_set(names: Any) -> bool:
    return isinstance(names, list) and names == EXPECTED_OUTPUT_LIST


def command_policy_ok(templates: Any) -> bool:
    if templates != EXPECTED_COMMAND_TEMPLATES:
        return False
    flattened = [token.casefold() for row in templates.values() for token in row]
    prohibited_tokens = {
        "clone", "fetch", "pull", "build", "import", "load", "tag", "push",
        "remove", "prune", "create", "run", "exec", "restart",
        "preprocess", "train", "evaluate", "benchmark", "pytest", "test",
    }
    return not prohibited_tokens.intersection(flattened)


def transition_semantics_ok(tree: ast.AST) -> bool:
    main = find_function(tree, "main")
    if main is None:
        return False
    candidates = []
    for node in ast.walk(main):
        if not isinstance(node, ast.Try):
            continue
        body = literal_calls(ast.Module(body=node.body, type_ignores=[]), "invoke", 2)
        if body and body[0] == ("S00", "DOCKER_DESKTOP_START"):
            candidates.append((node, body))
    if len(candidates) != 1:
        return False
    outer, body = candidates[0]
    if body != EXPECTED_WINDOW_INVOKES:
        return False
    final_if = next((node for node in outer.finalbody if isinstance(node, ast.If)), None)
    if final_if is None or not isinstance(final_if.test, ast.Name) or final_if.test.id != "start_attempted":
        return False
    inner = next((node for node in final_if.body if isinstance(node, ast.Try)), None)
    if inner is None:
        return False
    inner_body = literal_calls(ast.Module(body=inner.body, type_ignores=[]), "invoke", 2)
    inner_final = literal_calls(ast.Module(body=inner.finalbody, type_ignores=[]), "invoke", 2)
    if inner_body != [("F00", "DOCKER_DESKTOP_STOP")]:
        return False
    if inner_final != [("F01", "WSL_SHUTDOWN")]:
        return False
    for loop in (node for node in ast.walk(main) if isinstance(node, (ast.For, ast.AsyncFor, ast.While))):
        if any(pair[0] in {"S00", "F00", "F01"} for pair in literal_calls(loop, "invoke", 2)):
            return False
    return not any(isinstance(node, ast.While) for node in ast.walk(main))


def passport_ok(value: Any, version_label: str) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("origin_skill") == "experiment-agent"
        and value.get("origin_mode") == "plan"
        and isinstance(value.get("origin_date"), str)
        and value.get("verification_status") == "UNVERIFIED"
        and value.get("version_label") == version_label
        and isinstance(value.get("upstream_dependencies"), list)
        and value.get("repro_lock") is None
        and isinstance(value.get("experiment_intake_declaration"), dict)
        and value["experiment_intake_declaration"].get("status") == "no_experiments_declared"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    head = git_text(root, "rev-parse", "HEAD").casefold()
    check("expected_head_format", re.fullmatch(r"[0-9a-f]{40}", args.expected_head.casefold()) is not None)
    check("expected_head_exact", head == args.expected_head.casefold())
    status_lines = git_text(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    expected_paths = {path.as_posix() for path in PACKET_FILES}
    expected_untracked = {f"?? {path}" for path in expected_paths}
    parent_row = git_text(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    committed_delta = git_text(
        root, "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"
    ).splitlines()
    expected_added = {f"A\t{path}" for path in expected_paths}
    draft_mode = head == PACKET_PARENT and set(status_lines) == expected_untracked
    committed_mode = (
        status_lines == []
        and len(parent_row) == 2
        and parent_row[1].casefold() == PACKET_PARENT
        and set(committed_delta) == expected_added
    )
    packet_state = "WORKTREE_DRAFT" if draft_mode else "COMMITTED_PACKET" if committed_mode else "INVALID"
    check("packet_state_supported", draft_mode or committed_mode)
    check("packet_exact_four_file_scope", (
        set(status_lines) == expected_untracked if draft_mode else set(committed_delta) == expected_added
    ))
    check("packet_all_new_files", draft_mode or all(line.startswith("A\t") for line in committed_delta))
    check("packet_parent_exact", head == PACKET_PARENT if draft_mode else len(parent_row) == 2 and parent_row[1].casefold() == PACKET_PARENT)
    check("output_root_not_present", not (root / OUTPUT_ROOT).exists())
    check(
        "output_root_not_tracked",
        git_text(root, "ls-tree", "-r", "--name-only", "HEAD", "--", OUTPUT_ROOT.as_posix()) == "",
    )

    blobs: dict[Path, bytes] = {}
    for path in sorted(PACKET_FILES, key=lambda item: item.as_posix()):
        try:
            value = (root / path).read_bytes() if draft_mode else git_blob(root, head, path)
            blobs[path] = value
            check(f"packet_file_exists:{path.name}", True)
            normalized = canonical_lf(value)
            check(f"packet_no_bare_cr:{path.name}", True)
            check(f"packet_canonical_lf:{path.name}", normalized == value)
        except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError):
            blobs[path] = b""
            check(f"packet_file_exists:{path.name}", False)
            check(f"packet_no_bare_cr:{path.name}", False)
            check(f"packet_canonical_lf:{path.name}", False)

    for path, expected_sha256 in sorted(
        FROZEN_ATTEMPT006_SHA256.items(), key=lambda item: item[0].as_posix()
    ):
        try:
            value = git_blob(root, head, path)
            check(f"attempt006_blob_exists:{path.name}", True)
            check(f"attempt006_blob_sha256:{path.name}", sha256_bytes(value) == expected_sha256)
            check(f"attempt006_blob_canonical_lf:{path.name}", canonical_lf(value) == value)
        except (ValueError, subprocess.CalledProcessError):
            check(f"attempt006_blob_exists:{path.name}", False)
            check(f"attempt006_blob_sha256:{path.name}", False)
            check(f"attempt006_blob_canonical_lf:{path.name}", False)

    try:
        contract = strict_json_object(blobs.get(CONTRACT, b""))
        check("contract_strict_json", True)
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
        contract = {}
        check("contract_strict_json", False)
    try:
        authorization = strict_json_object(blobs.get(AUTHORIZATION, b""))
        check("authorization_strict_json", True)
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
        authorization = {}
        check("authorization_strict_json", False)
    try:
        state = strict_json_object(git_blob(root, head, STATE))
        attempt006_audit = strict_json_object(git_blob(root, head, ATTEMPT006_AUDIT))
        attempt006_execution = strict_json_object(
            git_blob(root, head, ATTEMPT006_OUTPUT / "p1_execution_receipt.json")
        )
        check("attempt006_semantic_json_strict", True)
    except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError):
        state, attempt006_audit, attempt006_execution = {}, {}, {}
        check("attempt006_semantic_json_strict", False)

    check(
        "contract_schema",
        contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt007-admission-observation-contract-1.0",
    )
    check("contract_stage", contract.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT007")
    check(
        "contract_passport",
        passport_ok(
            contract.get("material_passport"),
            "stage1e_e4_r6_pc2w_p1_attempt007_admission_observation_contract_v1",
        ),
    )
    scope = contract.get("scope_boundary", {})
    for field in (
        "packet_design_and_static_validation_only_now",
        "pass_means_observation_packet_complete_for_central_evaluation_only",
        "pass_does_not_open_materialization",
        "pass_does_not_open_preprocessing",
        "pass_does_not_open_training",
        "pass_does_not_open_evaluation",
        "pass_does_not_open_benchmark",
        "pass_does_not_open_test",
    ):
        check(f"contract_scope_true:{field}", scope.get(field) is True)
    check("contract_runtime_false", scope.get("runtime_execution_authorized_now") is False)
    check("contract_confirmation_false", scope.get("exact_command_confirmation_received_now") is False)
    check("contract_no_scientific_claim", scope.get("scientific_reproduction_claimed") is False)
    entry = contract.get("packet_entry_gate", {})
    check("contract_parent", entry.get("packet_parent_checkpoint") == PACKET_PARENT)
    check("contract_one_execution", entry.get("execution_attempts_maximum") == 1)
    check("contract_zero_retry", entry.get("automatic_retry_count") == 0)
    check("contract_zero_fallback", entry.get("fallback_count") == 0)
    frozen = contract.get("frozen_attempt006_inputs", {})
    expected_frozen = {path.as_posix(): value for path, value in FROZEN_ATTEMPT006_SHA256.items()}
    check("contract_frozen_count", frozen.get("input_count") == 10)
    check("contract_exact_frozen_hashes", frozen.get("artifacts") == expected_frozen)
    check("contract_attempt006_460", frozen.get("required_attempt006_audit_checks") == "460/460")
    pre = contract.get("immediate_pre_start_gate", {})
    for field in (
        "frozen_attempt006_hashes_and_semantics_replayed_before_output_root_creation",
        "immediate_host_probes_are_fail_closed",
        "wsl_inventory_all_rows_stopped",
        "docker_desktop_distro_exactly_once_and_stopped",
        "wsl_running_inventory_empty",
        "desktop_linux_named_pipe_specifically_absent_with_win32_error_2",
        "target_process_population_available_complete_and_empty",
        "target_tcp_population_available_complete_and_empty",
        "any_missing_ambiguous_timeout_or_parse_failure_blocks_start",
    ):
        check(f"contract_pre_gate_true:{field}", pre.get(field) is True)
    window = contract.get("controlled_observation_window", {})
    check("contract_one_start", window.get("docker_desktop_start_attempts_exactly_on_admitted_path") == 1)
    check("contract_identity_cross_consistency", window.get("docker_client_server_info_cross_consistency_required") is True)
    cleanup = contract.get("mandatory_cleanup_and_closure", {})
    check("contract_stop_finally", cleanup.get("docker_desktop_stop_is_in_outer_finally_after_any_start_attempt") is True)
    check("contract_shutdown_nested_finally", cleanup.get("wsl_shutdown_is_in_nested_finally_after_stop") is True)
    check("contract_one_stop", cleanup.get("docker_desktop_stop_attempts_maximum") == 1)
    check("contract_one_shutdown", cleanup.get("wsl_shutdown_attempts_maximum") == 1)
    check("contract_settle_20", cleanup.get("settling_seconds") == 20)
    check("contract_snapshots_abc", cleanup.get("snapshot_labels") == ["A", "B", "C"])
    check("contract_barrier_15", cleanup.get("snapshot_barrier_seconds") == 15)
    output = contract.get("output_contract", {})
    check("contract_output_root", output.get("output_root") == OUTPUT_ROOT.as_posix())
    check("contract_exact_outputs", output.get("exact_files") == EXPECTED_OUTPUT_LIST)
    check("contract_no_extra_outputs", output.get("extra_files_allowed") is False)
    check("contract_model_policy", contract.get("model_policy") == EXPECTED_MODEL_POLICY)
    check("contract_static_verdict", contract.get("static_packet_verdict") == "READY_FOR_CENTRAL_STATIC_VALIDATION")
    truth = contract.get("truth_state", {})
    check("contract_result_not_run", truth.get("RESULT_STATUS") == "NOT_RUN")
    check("contract_test_closed", truth.get("TEST_SET_OPENED") == "NO")
    check("contract_zero_rows", truth.get("ACCEPTED_RESULT_ROWS") == 0)
    check("contract_no_benchmark_admission", truth.get("benchmark_admission_opened") is False)

    check(
        "authorization_schema",
        authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt007-execution-authorization-1.0",
    )
    check("authorization_stage", authorization.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT007")
    check(
        "authorization_passport",
        passport_ok(
            authorization.get("material_passport"),
            "stage1e_e4_r6_pc2w_p1_attempt007_execution_authorization_v1",
        ),
    )
    check("authorization_parent", authorization.get("packet_parent_checkpoint") == PACKET_PARENT)
    check(
        "authorization_source_thread",
        authorization.get("authorization_basis", {}).get("source_thread_id")
        == "019ff4f0-802a-7892-a989-24f32ac26ac8",
    )
    current = authorization.get("current_authorization", {})
    check("authorization_design_true", current.get("packet_design_authorized") is True)
    check("authorization_static_true", current.get("static_validation_authorized") is True)
    for field in (
        "runtime_execution_authorized", "runner_invocation_authorized",
        "exact_command_confirmation_received", "docker_desktop_start_authorized_now",
        "docker_desktop_stop_authorized_now", "wsl_shutdown_authorized_now",
        "runtime_probe_authorized_now", "local_docker_daemon_query_authorized_now",
        "materialization_authorized", "preprocessing_authorized", "training_authorized",
        "evaluation_authorized", "benchmark_admission_authorized", "test_access_authorized",
    ):
        check(f"authorization_false:{field}", current.get(field) is False)
    prospective = authorization.get("prospective_limits_after_all_three_future_gates", {})
    check("authorization_future_one_execution", prospective.get("execution_attempts_maximum") == 1)
    check("authorization_future_one_start", prospective.get("docker_desktop_start_attempts_maximum") == 1)
    check("authorization_future_one_stop", prospective.get("docker_desktop_stop_attempts_maximum") == 1)
    check("authorization_future_one_shutdown", prospective.get("wsl_shutdown_attempts_maximum") == 1)
    check("authorization_future_zero_retry", prospective.get("automatic_retry_count") == 0)
    check("authorization_future_zero_fallback", prospective.get("fallback_count") == 0)
    future_command = authorization.get("future_exact_process_command_template")
    check("authorization_future_command_array", isinstance(future_command, list) and len(future_command) == 18)
    check("authorization_future_confirmation_last", isinstance(future_command, list) and future_command[-1] == (
        "USER_CONFIRMED_EXACT_ATTEMPT007_PROCESS_COMMAND_AFTER_CENTRAL_VALIDATION_AND_FRESH_AUDIT"
    ))
    check("authorization_output_root", authorization.get("authorized_output_root_only_after_future_confirmation") == OUTPUT_ROOT.as_posix())
    check("authorization_model_policy", authorization.get("model_policy") == EXPECTED_MODEL_POLICY)
    auth_truth = authorization.get("truth_state", {})
    check("authorization_result_not_run", auth_truth.get("RESULT_STATUS") == "NOT_RUN")
    check("authorization_test_closed", auth_truth.get("TEST_SET_OPENED") == "NO")
    check("authorization_zero_rows", auth_truth.get("ACCEPTED_RESULT_ROWS") == 0)
    check("authorization_no_benchmark_admission", auth_truth.get("benchmark_admission_opened") is False)

    pc2w = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {}).get("pc2w", {})
    attempt006 = pc2w.get("p1_attempt006_baseline_remediation", {})
    check("state_current_attempt006", state.get("state") == (
        "stage1e_rebaseline_v2_r6_pc2w_p1_attempt006_baseline_packet_"
        "audited_ready_for_admission_packet_design"
    ))
    check("state_attempt006_status", attempt006.get("status") == "COMPLETE_BASELINE_PACKET_AUDITED_READY_FOR_ADMISSION_PACKET_DESIGN")
    check("state_result_not_run", state.get("result_status") == "NOT_RUN")
    check("state_test_closed", state.get("test_set_opened") == "NO")
    check("attempt006_audit_verdict", attempt006_audit.get("verdict") == (
        "PASS_PC2W_P1_ATTEMPT006_BASELINE_PACKET_AUDITED_READY_FOR_ADMISSION_PACKET_DESIGN"
    ))
    check("attempt006_audit_460", attempt006_audit.get("audit_summary", {}).get("authoritative_checks_passed") == 460 == attempt006_audit.get("audit_summary", {}).get("authoritative_checks_total"))
    check("attempt006_execution_verdict", attempt006_execution.get("verdict") == "PASS_PC2W_P1_ATTEMPT006_BASELINE_REMEDIATED_READY_FOR_ADMISSION_PACKET")
    check("attempt006_no_admission", attempt006_execution.get("benchmark_admission_opened") is False)

    runner_source = blobs.get(RUNNER, b"").decode("utf-8", errors="strict") if blobs.get(RUNNER) else ""
    validator_source = blobs.get(VALIDATOR, b"").decode("utf-8", errors="strict") if blobs.get(VALIDATOR) else ""
    try:
        runner_tree = ast.parse(runner_source, filename=RUNNER.as_posix())
        check("runner_ast_parse", True)
    except SyntaxError:
        runner_tree = ast.Module(body=[], type_ignores=[])
        check("runner_ast_parse", False)
    try:
        validator_tree = ast.parse(validator_source, filename=VALIDATOR.as_posix())
        check("validator_ast_parse", True)
    except SyntaxError:
        validator_tree = ast.Module(body=[], type_ignores=[])
        check("validator_ast_parse", False)

    try:
        check("runner_exact_command_ids", assigned_literal(runner_tree, "EXPECTED_COMMAND_IDS") == EXPECTED_COMMAND_IDS)
        check("runner_exact_command_templates", assigned_literal(runner_tree, "COMMAND_ARGV_TEMPLATES") == EXPECTED_COMMAND_TEMPLATES)
        check(
            "runner_exact_frozen_hashes",
            assigned_literal(runner_tree, "FROZEN_ATTEMPT006_SHA256_LITERAL")
            == {path.as_posix(): value for path, value in FROZEN_ATTEMPT006_SHA256.items()},
        )
        check("runner_snapshot_labels", assigned_literal(runner_tree, "SNAPSHOT_LABELS") == ["A", "B", "C"])
        check("runner_settle_20", assigned_literal(runner_tree, "SETTLING_SECONDS") == 20)
        check("runner_barrier_15", assigned_literal(runner_tree, "SNAPSHOT_BARRIER_SECONDS") == 15)
        check("runner_output_root", assigned_path_string(runner_tree, "OUTPUT_RELATIVE") == OUTPUT_ROOT.as_posix())
    except (KeyError, TypeError, ValueError):
        for name in (
            "runner_exact_command_ids", "runner_exact_command_templates",
            "runner_exact_frozen_hashes", "runner_snapshot_labels",
            "runner_settle_20", "runner_barrier_15", "runner_output_root",
        ):
            if not any(existing == name for existing, _ in checks):
                check(name, False)
    check("runner_command_policy", command_policy_ok(EXPECTED_COMMAND_TEMPLATES))
    check("runner_exact_literal_invokes", literal_calls(runner_tree, "invoke", 2) == EXPECTED_LITERAL_INVOKES)
    check("runner_exact_snapshot_calls", literal_calls(runner_tree, "collect_snapshot", 5) == EXPECTED_SNAPSHOT_CALLS)
    snapshot_function = find_function(runner_tree, "collect_snapshot")
    snapshot_kinds = []
    if snapshot_function is not None:
        for node in sorted(
            (node for node in ast.walk(snapshot_function) if isinstance(node, ast.Call) and call_name(node) == "invoke"),
            key=lambda item: item.lineno,
        ):
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                snapshot_kinds.append(node.args[1].value)
    check("runner_snapshot_kinds", snapshot_kinds == ["WSL_VERBOSE", "WSL_RUNNING", "PROCESS_POPULATION", "TCP_POPULATION"])
    check("runner_nested_finally_semantics", transition_semantics_ok(runner_tree))
    sleep_names = []
    for node in ast.walk(runner_tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "time"
            and node.func.attr == "sleep"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
        ):
            sleep_names.append((node.lineno, node.args[0].id))
    check("runner_exact_sleep_order", [name for _, name in sorted(sleep_names)] == [
        "SETTLING_SECONDS", "SNAPSHOT_BARRIER_SECONDS", "SNAPSHOT_BARRIER_SECONDS"
    ])
    run_command_calls = [
        node for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "base"
        and node.func.attr == "run_command"
    ]
    check("runner_single_runtime_gateway", len(run_command_calls) == 1)
    runner_call_names = {
        name for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call) and (name := call_name(node)) is not None
    }
    check("runner_no_popen_or_system", not {"Popen", "system"}.intersection(runner_call_names))
    check("runner_no_delete", not {"remove", "unlink", "rmtree"}.intersection(runner_call_names))
    check("runner_no_while", not any(isinstance(node, ast.While) for node in ast.walk(runner_tree)))
    check("runner_confirmation_token", (
        "USER_CONFIRMED_EXACT_ATTEMPT007_PROCESS_COMMAND_AFTER_" in runner_source
        and "CENTRAL_VALIDATION_AND_FRESH_AUDIT" in runner_source
    ))
    check("runner_durable_failure_before_runtime", (
        'persist_failure_packet("IN_PROGRESS", "Attempt-007 initialized before first runtime command")'
        in runner_source
        and runner_source.index('persist_failure_packet("IN_PROGRESS", "Attempt-007 initialized before first runtime command")')
        < runner_source.index("pre_start_snapshot(invoke)")
    ))
    invoke_function = find_function(runner_tree, "invoke")
    check("runner_failure_refreshed_after_every_receipt", invoke_function is not None and any(
        isinstance(node, ast.Call) and call_name(node) == "persist_failure_packet"
        for node in ast.walk(invoke_function)
    ))
    check("runner_exception_rewrites_failure", "failure_packet_persisted = persist_failure_packet" in runner_source)
    check("runner_exact_outputs_present", all(f'\"{name}\"' in runner_source for name in OUTPUT_FILES))
    check("runner_pass_semantics_bounded", "FOR_CENTRAL_EVALUATION" in runner_source)
    check("runner_truth_not_run", '"result_status": "NOT_RUN"' in runner_source)
    check("runner_test_closed", '"test_set_opened": "NO"' in runner_source)
    check("runner_zero_rows", '"accepted_result_rows": 0' in runner_source)
    check("runner_no_benchmark_admission", '"benchmark_admission_opened": False' in runner_source)
    check("runner_zero_retry_and_fallback", (
        '"automatic_retry_count": 0' in runner_source and '"fallback_count": 0' in runner_source
    ))
    check("runner_process_query_null_guards", all(token in runner_source for token in (
        "CreationDate", "CreationTimeUtc", "ExecutablePath", "CommandLine",
        "SignerSubjectHash", "ParentExecutablePathHash",
    )))
    check("runner_tcp_query_owner_binding", all(token in runner_source for token in (
        "ProcessName", "ProcessId", "OwningProcess", "LocalAddressHash", "RemoteAddressHash",
    )))
    check("runner_identity_sanitization", all(token in runner_source for token in (
        "raw_process_paths_or_command_lines_persisted", "raw_network_addresses_persisted",
        "raw_proxy_values_persisted", "raw_docker_root_dir_persisted",
        "raw_stdout_stderr_or_argv_persisted",
    )))

    strict_negative = {
        "malformed": b'{"x":',
        "duplicate": b'{"x":1,"x":2}',
        "casefold_duplicate": b'{"x":1,"X":2}',
        "nan": b'{"x":NaN}',
        "positive_infinity": b'{"x":Infinity}',
        "negative_infinity": b'{"x":-Infinity}',
        "invalid_utf8": b'{"x":"\xff"}',
        "null_root_coercion": b'null',
        "array_root_coercion": b'[]',
        "string_root_coercion": b'"object"',
    }
    for name, fixture in strict_negative.items():
        try:
            strict_json_object(fixture)
            rejected = False
        except (DuplicateKeyError, UnicodeError, ValueError, json.JSONDecodeError):
            rejected = True
        check(f"fixture_strict_json_rejected:{name}", rejected)
    check("fixture_crlf_detected_as_drift", canonical_lf(b"a\r\nb\r\n") != b"a\r\nb\r\n")
    try:
        canonical_lf(b"a\rb\n")
        bare_cr_rejected = False
    except ValueError:
        bare_cr_rejected = True
    check("fixture_bare_cr_rejected", bare_cr_rejected)

    empty = {"Available": True, "Count": 0, "Rows": [], "ErrorCode": "NONE", "ErrorTypeHash": None}
    process_row = {"Name": "wslrelay", "ProcessId": 7}
    tcp_row = {"Name": "wslrelay", "ProcessId": 7, "ConnectionCount": 1}
    unavailable = {"Available": False, "Count": 0, "Rows": [], "ErrorCode": "PROBE_EXCEPTION", "ErrorTypeHash": "a" * 64}
    for kind, row in (("process", process_row), ("tcp", tcp_row)):
        positive = {**empty, "Count": 1, "Rows": [row]}
        valid, eligible = validate_population_envelope(empty, kind)
        check(f"fixture_population_empty_valid:{kind}", valid and eligible)
        valid, eligible = validate_population_envelope(positive, kind)
        check(f"fixture_population_nonempty_ineligible:{kind}", valid and not eligible)
        valid, eligible = validate_population_envelope(unavailable, kind)
        check(f"fixture_population_unavailable_ineligible:{kind}", valid and not eligible)
        negatives = {
            "rows_null": {**empty, "Rows": None},
            "rows_singleton_object": {**positive, "Rows": row},
            "available_coercion": {**empty, "Available": 1},
            "count_boolean": {**empty, "Count": True},
            "count_negative": {**empty, "Count": -1},
            "count_mismatch": {**positive, "Count": 0},
            "unknown_error": {**unavailable, "ErrorCode": "UNKNOWN"},
            "null_error_hash": {**unavailable, "ErrorTypeHash": None},
            "upper_hash": {**unavailable, "ErrorTypeHash": "A" * 64},
            "extra_field": {**empty, "Extra": False},
            "null_process_id": {**positive, "Rows": [{**row, "ProcessId": None}]},
            "boolean_process_id": {**positive, "Rows": [{**row, "ProcessId": True}]},
            "duplicate_row": {**positive, "Count": 2, "Rows": [row, row]},
        }
        if kind == "tcp":
            negatives["null_connection_count"] = {**positive, "Rows": [{**row, "ConnectionCount": None}]}
            negatives["boolean_connection_count"] = {**positive, "Rows": [{**row, "ConnectionCount": True}]}
        for name, fixture in negatives.items():
            valid, eligible = validate_population_envelope(fixture, kind)
            check(f"fixture_population_rejected:{kind}:{name}", not valid and not eligible)

    hash64 = "a" * 64
    rich_rows = [
        {
            "Name": "com.docker.backend", "ProcessId": 10, "ParentProcessId": 1,
            "ParentNameHash": hash64, "ParentExecutablePathHash": hash64,
            "ExecutablePathHash": hash64, "ExecutableFileSha256": hash64,
            "FileVersion": "1.0", "AuthenticodeStatus": "Valid",
            "SignerSubjectHash": hash64, "CreationTimeUtc": "2026-08-25T00:00:00.0000000Z",
            "CommandLineHash": hash64,
        },
        {
            "Name": "docker desktop", "ProcessId": 11, "ParentProcessId": 1,
            "ParentNameHash": hash64, "ParentExecutablePathHash": hash64,
            "ExecutablePathHash": hash64, "ExecutableFileSha256": hash64,
            "FileVersion": "1.0", "AuthenticodeStatus": "Valid",
            "SignerSubjectHash": hash64, "CreationTimeUtc": "2026-08-25T00:00:01.0000000Z",
            "CommandLineHash": hash64,
        },
    ]
    rich_process = {"Available": True, "Count": 2, "Rows": rich_rows, "ErrorCode": "NONE", "ErrorTypeHash": None}
    check("fixture_rich_process_positive", validate_rich_process(rich_process))
    process_mutations = {
        "rows_null": {**rich_process, "Rows": None},
        "count_boolean": {**rich_process, "Count": True},
        "null_name": copy.deepcopy(rich_process),
        "null_path_hash": copy.deepcopy(rich_process),
        "null_creation_time": copy.deepcopy(rich_process),
        "utc_offset_not_z": copy.deepcopy(rich_process),
        "utc_six_fraction_digits": copy.deepcopy(rich_process),
        "bad_utc_date": copy.deepcopy(rich_process),
        "boolean_pid": copy.deepcopy(rich_process),
        "duplicate_pid": copy.deepcopy(rich_process),
        "missing_required_process": {**rich_process, "Count": 1, "Rows": [rich_rows[0]]},
        "signature_not_valid": copy.deepcopy(rich_process),
    }
    process_mutations["null_name"]["Rows"][0]["Name"] = None
    process_mutations["null_path_hash"]["Rows"][0]["ExecutablePathHash"] = None
    process_mutations["null_creation_time"]["Rows"][0]["CreationTimeUtc"] = None
    process_mutations["utc_offset_not_z"]["Rows"][0]["CreationTimeUtc"] = "2026-08-25T07:00:00.0000000+07:00"
    process_mutations["utc_six_fraction_digits"]["Rows"][0]["CreationTimeUtc"] = "2026-08-25T00:00:00.000000Z"
    process_mutations["bad_utc_date"]["Rows"][0]["CreationTimeUtc"] = "2026-02-30T00:00:00.0000000Z"
    process_mutations["boolean_pid"]["Rows"][0]["ProcessId"] = True
    process_mutations["duplicate_pid"]["Rows"][1]["ProcessId"] = 10
    process_mutations["signature_not_valid"]["Rows"][0]["AuthenticodeStatus"] = "UnknownError"
    for name, fixture in process_mutations.items():
        check(f"fixture_rich_process_rejected:{name}", not validate_rich_process(fixture))
    check("fixture_dotnet_utc_positive", parse_dotnet_utc("2026-08-25T00:00:00.0000000Z").tzinfo is not None)

    rich_tcp = {
        "Available": True,
        "Count": 1,
        "Rows": [{
            "ProcessName": "com.docker.backend", "ProcessId": 10, "State": "Listen",
            "LocalAddressHash": hash64, "LocalPort": 2375,
            "RemoteAddressHash": hash64, "RemotePort": 0,
        }],
        "ErrorCode": "NONE",
        "ErrorTypeHash": None,
    }
    check("fixture_rich_tcp_positive", validate_rich_tcp(rich_tcp, rich_process))
    tcp_mutations = {
        "rows_null": {**rich_tcp, "Rows": None},
        "owner_unknown": copy.deepcopy(rich_tcp),
        "owner_null": copy.deepcopy(rich_tcp),
        "state_null": copy.deepcopy(rich_tcp),
        "address_null": copy.deepcopy(rich_tcp),
        "port_boolean": copy.deepcopy(rich_tcp),
        "port_overflow": copy.deepcopy(rich_tcp),
        "duplicate_row": {**rich_tcp, "Count": 2, "Rows": rich_tcp["Rows"] * 2},
    }
    tcp_mutations["owner_unknown"]["Rows"][0]["ProcessId"] = 999
    tcp_mutations["owner_null"]["Rows"][0]["ProcessId"] = None
    tcp_mutations["state_null"]["Rows"][0]["State"] = None
    tcp_mutations["address_null"]["Rows"][0]["LocalAddressHash"] = None
    tcp_mutations["port_boolean"]["Rows"][0]["LocalPort"] = True
    tcp_mutations["port_overflow"]["Rows"][0]["RemotePort"] = 65536
    for name, fixture in tcp_mutations.items():
        check(f"fixture_rich_tcp_rejected:{name}", not validate_rich_tcp(fixture, rich_process))

    client = {
        "Version": "28.0", "ApiVersion": "1.48", "DefaultAPIVersion": "1.48",
        "GitCommit": "abc", "GoVersion": "go1.24", "Os": "windows", "Arch": "amd64",
        "BuildTime": "2026-08-25T00:00:00Z", "Context": "desktop-linux",
    }
    server = {
        "Version": "28.0", "ApiVersion": "1.48", "MinAPIVersion": "1.24",
        "GitCommit": "def", "GoVersion": "go1.24", "Os": "linux", "Arch": "amd64",
        "KernelVersion": "6.6", "BuildTime": "2026-08-25T00:00:00Z", "Experimental": False,
    }
    info = {
        "ServerVersion": "28.0", "OperatingSystem": "Docker Desktop", "OSType": "linux",
        "Architecture": "amd64", "KernelVersion": "6.6", "Driver": "overlayfs",
        "CgroupDriver": "cgroupfs", "CgroupVersion": "2", "DockerRootDir": "/var/lib/docker",
        "DefaultRuntime": "runc", "ID": "daemon", "NCPU": 8, "MemTotal": 1024,
        "Containers": 0, "ContainersRunning": 0, "ContainersPaused": 0,
        "ContainersStopped": 0, "Images": 0, "LiveRestoreEnabled": False,
        "ExperimentalBuild": False, "ContainerdCommit": {"ID": "containerd"},
        "Runtimes": {"runc": {}}, "SecurityOptions": ["seccomp"],
    }
    context = {"Name": "desktop-linux", "DockerEndpointHostClass": "DESKTOP_LINUX_NPIPE_EXACT"}
    version = {"Client": client, "Server": server}
    check("fixture_docker_identity_positive", validate_docker_identity_fixture(version, info, context))
    docker_mutations = {
        "client_null": {"Client": None, "Server": server},
        "server_null": {"Client": client, "Server": None},
        "client_version_null": {"Client": {**client, "Version": None}, "Server": server},
        "server_kernel_null": {"Client": client, "Server": {**server, "KernelVersion": None}},
        "client_time_offset": {"Client": {**client, "BuildTime": "2026-08-25T07:00:00+07:00"}, "Server": server},
        "info_null": None,
        "info_root_null": {**info, "DockerRootDir": None},
        "info_bool_cpu": {**info, "NCPU": True},
        "info_bool_count": {**info, "Containers": False},
        "info_server_drift": {**info, "ServerVersion": "27.0"},
        "context_ambiguous": {"Name": "default", "DockerEndpointHostClass": "OTHER"},
    }
    for name, mutation in docker_mutations.items():
        mutated_version = mutation if name.startswith("client_") or name.startswith("server_") else version
        mutated_info = mutation if name.startswith("info_") else info
        mutated_context = mutation if name == "context_ambiguous" else context
        check(
            f"fixture_docker_identity_rejected:{name}",
            not validate_docker_identity_fixture(mutated_version, mutated_info, mutated_context),
        )
    check("fixture_rfc3339_utc_positive", parse_rfc3339_utc("2026-08-25T00:00:00Z").tzinfo is not None)

    actual_hashes = {path.as_posix(): value for path, value in FROZEN_ATTEMPT006_SHA256.items()}
    check("fixture_hash_map_positive", packet_hashes_match(actual_hashes, expected_frozen))
    drifted_hashes = dict(actual_hashes)
    first_hash_key = next(iter(drifted_hashes))
    drifted_hashes[first_hash_key] = "0" * 64
    check("fixture_hash_drift_rejected", not packet_hashes_match(drifted_hashes, expected_frozen))
    extra_hashes = {**actual_hashes, "extra.json": "a" * 64}
    check("fixture_hash_extra_rejected", not packet_hashes_match(extra_hashes, expected_frozen))
    check("fixture_output_set_positive", exact_output_set(EXPECTED_OUTPUT_LIST))
    check("fixture_extra_output_rejected", not exact_output_set(EXPECTED_OUTPUT_LIST + ["extra.json"]))
    check("fixture_missing_output_rejected", not exact_output_set(EXPECTED_OUTPUT_LIST[:-1]))
    check("fixture_retry_policy_positive", command_policy_ok(EXPECTED_COMMAND_TEMPLATES))
    retry_templates = copy.deepcopy(EXPECTED_COMMAND_TEMPLATES)
    retry_templates["RETRY"] = ["DOCKER", "desktop", "start"]
    fallback_templates = copy.deepcopy(EXPECTED_COMMAND_TEMPLATES)
    fallback_templates["FALLBACK"] = ["DOCKER", "context", "use", "default"]
    scientific_templates = copy.deepcopy(EXPECTED_COMMAND_TEMPLATES)
    scientific_templates["SCIENCE"] = ["PYTHON", "train.py", "--test"]
    container_templates = copy.deepcopy(EXPECTED_COMMAND_TEMPLATES)
    container_templates["MUTATION"] = ["DOCKER", "container", "run", "image"]
    check("fixture_retry_template_rejected", not command_policy_ok(retry_templates))
    check("fixture_fallback_template_rejected", not command_policy_ok(fallback_templates))
    check("fixture_scientific_test_verbs_rejected", not command_policy_ok(scientific_templates))
    check("fixture_container_mutation_rejected", not command_policy_ok(container_templates))

    transition_fixtures = {
        "positive": """
def main():
    try:
        invoke('S00','DOCKER_DESKTOP_START')
        invoke('D00','WSL_VERBOSE')
        invoke('D01','PROCESS_IDENTITY')
        invoke('D02','TCP_IDENTITY')
        invoke('D03','DOCKER_VERSION')
        invoke('D04','DOCKER_INFO')
        invoke('D05','DOCKER_CONTEXT_INSPECT')
        invoke('D06','DOCKER_DESKTOP_FILE_IDENTITY')
    finally:
        if start_attempted:
            try:
                invoke('F00','DOCKER_DESKTOP_STOP')
            finally:
                invoke('F01','WSL_SHUTDOWN')
""",
        "stop_before_start": """
def main():
    invoke('F00','DOCKER_DESKTOP_STOP')
    try:
        invoke('S00','DOCKER_DESKTOP_START')
    finally:
        if start_attempted:
            try: pass
            finally: invoke('F01','WSL_SHUTDOWN')
""",
        "stop_outside_finally": """
def main():
    try:
        invoke('S00','DOCKER_DESKTOP_START')
    finally:
        pass
    invoke('F00','DOCKER_DESKTOP_STOP')
    invoke('F01','WSL_SHUTDOWN')
""",
        "shutdown_not_nested": """
def main():
    try:
        invoke('S00','DOCKER_DESKTOP_START')
    finally:
        if start_attempted:
            invoke('F00','DOCKER_DESKTOP_STOP')
            invoke('F01','WSL_SHUTDOWN')
""",
        "retry_loop": """
def main():
    while True:
        invoke('S00','DOCKER_DESKTOP_START')
""",
    }
    for name, source in transition_fixtures.items():
        accepted = transition_semantics_ok(ast.parse(source))
        check(f"fixture_ast_transition:{name}", accepted if name == "positive" else not accepted)

    validator_imports = {
        alias.name.split(".")[0]
        for node in ast.walk(validator_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    check("validator_no_network_imports", not {"socket", "requests", "urllib", "http", "ftplib"}.intersection(validator_imports))
    check("validator_does_not_import_runner", "execute_e4_r6_pc2w_p1_attempt007_admission_observation" not in validator_imports)
    validator_subprocess_calls = [
        node for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    check("validator_single_subprocess_gateway", len(validator_subprocess_calls) == 1)
    run_git_function = find_function(validator_tree, "run_git")
    check("validator_subprocess_git_only", run_git_function is not None and '["git", *args]' in ast.get_source_segment(validator_source, run_git_function))
    validator_call_names = {
        name for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call) and (name := call_name(node)) is not None
    }
    check("validator_no_write_calls", not {
        "write", "write_text", "write_bytes", "mkdir", "touch", "unlink", "remove", "rmtree"
    }.intersection(validator_call_names))
    check("validator_no_runtime_sleep", "sleep" not in validator_call_names)
    check("validator_no_shell_true", not any(
        isinstance(node, ast.Call)
        and any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        for node in ast.walk(validator_tree)
    ))
    check("validator_dont_write_bytecode", "sys.dont_write_bytecode = True" in validator_source)

    failures = [name for name, passed in checks if not passed]
    result = {
        "verdict": (
            "READY_FOR_CENTRAL_STATIC_VALIDATION"
            if not failures else "FAIL_CLOSED_PC2W_P1_ATTEMPT007_STATIC_PACKET"
        ),
        "packet_state": packet_state,
        "head": head,
        "parent": PACKET_PARENT,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "benchmark_admission_opened": False,
        "runtime_commands_executed": False,
        "docker_wsl_process_tcp_named_pipe_network_actions": 0,
        "scientific_or_test_actions": 0,
        "write_set": [],
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "verdict": "FAIL_CLOSED_PC2W_P1_ATTEMPT007_STATIC_PACKET",
            "error_type": type(exc).__name__,
            "error_sha256": sha256_bytes(str(exc).encode("utf-8")),
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "benchmark_admission_opened": False,
            "runtime_commands_executed": False,
            "docker_wsl_process_tcp_named_pipe_network_actions": 0,
            "scientific_or_test_actions": 0,
            "write_set": [],
        }, indent=2, allow_nan=False))
        raise SystemExit(2)
