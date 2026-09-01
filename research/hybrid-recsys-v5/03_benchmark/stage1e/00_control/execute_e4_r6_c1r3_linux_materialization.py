#!/usr/bin/env python3
"""Fail-closed Linux/amd64 M0/M1 materialization runner for R6-C1R3.

This runner executes the immutable packet's image probe, dataset lane, and
environment lane only.  It cannot dispatch bridge, training, evaluation,
metric, benchmark-admission, or TEST commands.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Iterable


sys.dont_write_bytecode = True

REPO_FROM_FILE = Path(__file__).resolve().parents[5]
CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
PACKET_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_bd/"
    "E4_R6C1R3_linux_command_packet"
)
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_c1r3_linux_materialization.py"
CONTRACT_RELATIVE = (
    CONTROL_RELATIVE / "e4_r6_c1r3_linux_materialization_runner_contract.json"
)
MINIMAL_CENTRAL_RECEIPT_RELATIVE = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_c1r3_linux_attempt005_minimal_runner_central_static_validation_receipt.json"
)
PACKET_VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_c1r3_linux_packet.py"
PACKET_AUDIT_RELATIVE = CONTROL_RELATIVE / (
    "rebaseline_v2_e4_r6_c1r3_linux_revision1_fresh_independent_audit_receipt.json"
)

ACCEPTED_PACKET_AUDIT_COMMIT = "1e3617cd0befe790a28129d3714dc4a17e6ce964"
ACCEPTED_PACKET_COMMIT = "210c1edfd432e19b0007b3ba39528bcdb73c2288"
ACCEPTED_PACKET_PARENT = "a939692d72d5d33cf67a8762d5260f2378df64f6"
ACCEPTED_PACKET_AUDIT_VERDICT = (
    "PASS_R6_C1R3_LINUX_REVISION1_FRESH_INDEPENDENT_AUDIT_"
    "READY_FOR_CENTRAL_RUNNER_CONSTRUCTION"
)
ACCEPTED_PACKET_AUDIT_SCHEMA = (
    "stage1e-r6-c1r3-linux-revision1-fresh-independent-audit-receipt-1.0"
)
MINIMAL_CENTRAL_RECEIPT_SCHEMA = (
    "stage1e-r6-c1r3-linux-attempt005-minimal-runner-central-static-validation-receipt-1.0"
)
MINIMAL_CENTRAL_RECEIPT_VERDICT = (
    "PASS_R6_C1R3_LINUX_ATTEMPT005_MINIMAL_RUNNER_CENTRAL_STATIC_VALIDATION_READY_FOR_M0_M1_RUNTIME"
)

DOCKER_EXE = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_BYTES = 42_748_848
DOCKER_SHA256 = "0cdb9dea2e39a0a29e5dc3f9732f572dc140547b28deab0495589b4f79b31ca1"
WSL_EXE = Path(r"C:\Windows\System32\wsl.exe")
TASKLIST_EXE = Path(r"C:\Windows\System32\tasklist.exe")
DOCKER_SERVER_PIPE = "npipe:////./pipe/dockerdesktoplinuxengine"
DOCKER_SERVER_NOT_FOUND = "the system cannot find the file specified."
DOCKER_PROCESS_NAMES = frozenset(
    {
        "docker desktop.exe",
        "com.docker.backend.exe",
        "com.docker.build.exe",
        "com.docker.proxy.exe",
        "dockerd.exe",
        "vpnkit.exe",
        "wslrelay.exe",
    }
)
IMAGE_REF = (
    "docker.io/library/python@sha256:"
    "2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
)
ML100K_SHA256 = "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229"

SOURCE_ATTEMPT_NAME = "attempt-004-linux"
ATTEMPT_NAME = "attempt-005-linux"

RUN_ROOT = Path(
    r"E:\UIT\cv\materialized-runs\hybrid-recsys-v5\stage1e\r6\c1r3"
    rf"\{ATTEMPT_NAME}"
)
DATA_ROOT = Path(
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    rf"\official_source\grouplens_ml100k\{ATTEMPT_NAME}"
)
ENV_ROOT = Path(
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    rf"\recbole_bpr_ml100k_py3119_cpu\{ATTEMPT_NAME}"
)
EXTERNAL_FLOOR = Path(r"E:\UIT\cv")

CONFIRMATION_TOKEN = (
    "USER_CONFIRMED_STAGE1E_MINIMAL_X2_ATTEMPT005_M0_M1_2026_09_01"
)
DOCKER_START_ARGV = [str(DOCKER_EXE), "desktop", "start", "--detach"]
DOCKER_READY_ARGV = [str(DOCKER_EXE), "version", "--format", "{{json .Server}}"]
TRUTH_STATE = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "benchmark_admission_opened": False,
    "phase_1e_complete": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}

EXPECTED_COMMAND_IDS = (
    "I00_PULL_EXACT_OFFICIAL_PLATFORM_MANIFEST",
    "I01_INSPECT_LOCAL_IMAGE_IDENTITY",
    "I02_PROBE_EXACT_CPYTHON_IDENTITY",
    "M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES",
    "M01_SAFE_EXTRACT_CONVERT_AND_RECONCILE",
    "M02_SEAL_DATASET_MATERIALIZATION_RECEIPT",
    "E00_DOWNLOAD_LINUX_WHEEL_CLOSURE",
    "E01_HASH_AND_FREEZE_WHEEL_CLOSURE",
    "E02_CREATE_EXACT_CONTAINER_VENV",
    "E03_INSTALL_HASHED_THIRD_PARTY_CLOSURE",
    "E04_STAGE_VERIFIED_RECBOLE_SOURCE",
    "E05_PREPARE_EPHEMERAL_BUILD_SOURCE",
    "E06_BUILD_LOCAL_RECBOLE_WHEEL",
    "E07_HASH_LOCAL_RECBOLE_WHEEL",
    "E08_INSTALL_HASHED_LOCAL_RECBOLE_WHEEL",
    "E09_SEAL_ENVIRONMENT_AND_IMPORT_CHECK",
    "E10_ASSERT_ATTEMPT_WRITE_BOUNDARY",
)

LOCKED_BLOB_OIDS = {
    CONTROL_RELATIVE / "build_e4_r6_c1r3_linux_packet.py": (
        "ad4d9ad18f81f7e515b45eaecdd93aaea39411ac"
    ),
    PACKET_VALIDATOR_RELATIVE: "f83ac9414f279eb1cb658f6d240b2025fdcf4594",
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_pc2w_g1_backend_admission_receipt.json": (
        "f9dbb49dd63972ab75779a0f8e90c1564039f50f"
    ),
    CONTROL_RELATIVE / "rebaseline_v2_e4_r6_c1r3_linux_central_static_validation_receipt.json": (
        "700cdfa7572caad1337e0611dfbe35c2be0da11a"
    ),
    PACKET_RELATIVE / "audit_handoff.json": "61c271c28a8bb9e8f5df9c0176bb0b0b937aaa48",
    PACKET_RELATIVE / "dataset_materialization_packet.json": (
        "15c5e215f128331f263cb3504ecc0bc90b90575a"
    ),
    PACKET_RELATIVE / "environment_materialization_packet.json": (
        "76e176f57e3b318694c47b1f39e166b8d4098254"
    ),
    PACKET_RELATIVE / "execution_boundary_and_negative_assertions.json": (
        "f0dbb49d8c413908a3f5464b2103ebf967d6bd2c"
    ),
    PACKET_RELATIVE / "recbole_dataset_bridge_packet.json": (
        "bef13cab870b83e8a9ccb614e0947ef1e4b380aa"
    ),
    PACKET_AUDIT_RELATIVE: "73c8f3a9a5d3a84bf000c0ca2b3e2af794282f78",
}

DROP_ENV_NAMES = {
    "all_proxy",
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


def reject_nonfinite(value: str) -> None:
    raise StrictJsonError(f"non-finite number: {value}")


def strict_json_bytes(payload: bytes) -> Any:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJsonError("JSON_NOT_UTF8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=reject_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"JSON_PARSE_FAILED:{exc}") from exc


def strict_load(path: Path) -> dict[str, Any]:
    value = strict_json_bytes(path.read_bytes())
    if not isinstance(value, dict):
        raise StrictJsonError(f"TOP_LEVEL_OBJECT_REQUIRED:{path}")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def raw_fact(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            count += len(block)
            digest.update(block)
    return {"bytes": count, "sha256": digest.hexdigest()}


def argv_hash(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256_bytes(payload)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def write_json_atomic_new(path: Path, value: dict[str, Any]) -> None:
    """Publish one authoritative JSON file without exposing a partial final path."""
    payload = (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    if path.exists() or partial.exists():
        raise FileExistsError(f"RESULT_PUBLICATION_PATH_EXISTS:{path}")
    linked = False
    try:
        with partial.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(partial, path)
        linked = True
    finally:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            if not linked:
                raise


def persist_final_result(
    path: Path,
    document: dict[str, Any],
    writer: Callable[[Path, dict[str, Any]], None] = write_json_atomic_new,
) -> bool:
    """Publish the final result or mutate the emitted document to fail closed."""
    try:
        writer(path, document)
        return True
    except Exception as write_error:
        detail = f"{type(write_error).__name__}:{write_error}"
        document["prior_error_type"] = document.get("error_type")
        document["prior_error"] = document.get("error")
        document["passed"] = False
        document["error_type"] = "RunnerResultWriteError"
        document["error"] = detail
        document["runner_result_write_error"] = detail
        document["verdict"] = "HANDOFF_INCOMPLETE_R6_C1R3_LINUX_ATTEMPT005_CLOSED"
        return False


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def validate_packet_command(row: dict[str, Any]) -> None:
    identifier = row.get("id")
    argv = row.get("argv")
    if not isinstance(identifier, str) or not identifier:
        raise RuntimeError("COMMAND_ID_INVALID")
    if not isinstance(argv, list) or not argv or not all(
        isinstance(token, str) for token in argv
    ):
        raise RuntimeError(f"COMMAND_ARGV_INVALID:{identifier}")
    if argv[0] != str(DOCKER_EXE):
        raise RuntimeError(f"COMMAND_EXECUTABLE_MISMATCH:{identifier}")
    if row.get("argv_sha256") != argv_hash(argv):
        raise RuntimeError(f"ARGV_HASH_MISMATCH:{identifier}")
    if not isinstance(row.get("network"), bool):
        raise RuntimeError(f"COMMAND_NETWORK_FLAG_INVALID:{identifier}")
    timeout = row.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise RuntimeError(f"COMMAND_TIMEOUT_INVALID:{identifier}")


def rebase_attempt_command(row: dict[str, Any]) -> dict[str, Any]:
    """Rebase only the immutable packet's attempt identifier in argv tokens."""
    validate_packet_command(row)
    source_argv = list(row["argv"])
    rebased_argv = [
        token.replace(SOURCE_ATTEMPT_NAME, ATTEMPT_NAME) for token in source_argv
    ]
    if any(SOURCE_ATTEMPT_NAME in token for token in rebased_argv):
        raise RuntimeError(f"ATTEMPT_REBASE_INCOMPLETE:{row['id']}")
    if rebased_argv == source_argv:
        return dict(row)
    rebased = dict(row)
    rebased["source_argv_sha256"] = row["argv_sha256"]
    rebased["argv"] = rebased_argv
    rebased["argv_sha256"] = argv_hash(rebased_argv)
    validate_packet_command(rebased)
    return rebased


def load_execution_plan(repo_root: Path) -> list[dict[str, Any]]:
    packet_root = repo_root / PACKET_RELATIVE
    boundary = strict_load(packet_root / "execution_boundary_and_negative_assertions.json")
    dataset = strict_load(packet_root / "dataset_materialization_packet.json")
    environment = strict_load(packet_root / "environment_materialization_packet.json")
    bridge = strict_load(packet_root / "recbole_dataset_bridge_packet.json")
    for document in (boundary, dataset, environment, bridge):
        if document.get("stage_id") != "R6-C1R3-LINUX":
            raise RuntimeError("PACKET_STAGE_MISMATCH")
        if document.get("execution_authorized") is not False:
            raise RuntimeError("PACKET_EXECUTION_STATE_MUTATED")
        if document.get("truth_state") != TRUTH_STATE:
            raise RuntimeError("PACKET_TRUTH_STATE_MUTATED")

    image = boundary.get("image_acquisition_and_probe_commands")
    dataset_rows = dataset.get("commands")
    environment_rows = environment.get("commands")
    bridge_rows = bridge.get("commands")
    if not all(
        isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
        for rows in (image, dataset_rows, environment_rows, bridge_rows)
    ):
        raise RuntimeError("PACKET_COMMAND_ARRAY_INVALID")
    if any(str(row.get("id", "")).startswith("B") is False for row in bridge_rows):
        raise RuntimeError("BRIDGE_COMMAND_ID_INVALID")

    source_plan = [*image, *dataset_rows, *environment_rows]
    identifiers = tuple(str(row.get("id", "")) for row in source_plan)
    if identifiers != EXPECTED_COMMAND_IDS:
        raise RuntimeError("EXECUTION_PLAN_ORDER_MISMATCH")
    for row in source_plan:
        validate_packet_command(row)
    plan = [rebase_attempt_command(row) for row in source_plan]
    changed = [row for row in plan if row.get("source_argv_sha256")]
    if len(changed) != 14:
        raise RuntimeError("ATTEMPT_REBASE_COMMAND_COUNT_MISMATCH")
    if any(identifier.startswith("B") for identifier in identifiers):
        raise RuntimeError("BRIDGE_COMMAND_IN_RUNTIME_PLAN")
    return plan


def orchestrate_commands(
    commands: Iterable[dict[str, Any]],
    execute: Callable[[dict[str, Any]], None],
    create_roots: Callable[[], None],
) -> None:
    rows = list(commands)
    if tuple(str(row.get("id", "")) for row in rows) != EXPECTED_COMMAND_IDS:
        raise RuntimeError("ORCHESTRATOR_PLAN_MISMATCH")
    for index, row in enumerate(rows):
        execute(row)
        if index == 2:
            create_roots()


def require_confirmation(value: str) -> None:
    if value != CONFIRMATION_TOKEN:
        raise RuntimeError("EXECUTION_CONFIRMATION_MISMATCH")


def validate_dataset_final_receipt(receipt: dict[str, Any]) -> None:
    valid = (
        receipt.get("schema_version")
        == "stage1e-r6-c1r3-dataset-materialization-1.0"
        and receipt.get("attempt") == ATTEMPT_NAME
        and receipt.get("archive_sha256") == ML100K_SHA256
        and receipt.get("rows") == 100000
        and receipt.get("users") == 943
        and receipt.get("items") == 1682
        and receipt.get("scientific_execution_performed") is False
        and receipt.get("test_opened") is False
        and receipt.get("verdict") == "PASS_R6_M0_MATERIALIZED_NOT_BENCHMARKED"
    )
    if not valid:
        raise RuntimeError("DATASET_FINAL_RECEIPT_INVALID")


def validate_environment_final_receipt(receipt: dict[str, Any]) -> None:
    valid = (
        receipt.get("schema_version")
        == "stage1e-r6-c1r3-environment-materialization-1.0"
        and receipt.get("attempt") == ATTEMPT_NAME
        and receipt.get("python") == "3.11.9"
        and receipt.get("recbole") == "1.2.1"
        and receipt.get("torch") == "2.2.2+cpu"
        and receipt.get("torch_cuda") is None
        and receipt.get("cuda_available") is False
        and receipt.get("source_python_files") == 150
        and receipt.get("source_python_bytes") == 1_378_341
        and receipt.get("dataset_constructed") is False
        and receipt.get("training") is False
        and receipt.get("evaluation") is False
        and receipt.get("test_opened") is False
        and receipt.get("verdict")
        == "PASS_R6_M1_ENVIRONMENT_MATERIALIZED_NOT_BENCHMARKED"
    )
    if not valid:
        raise RuntimeError("ENVIRONMENT_FINAL_RECEIPT_INVALID")


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
    if not windows_under(path, EXTERNAL_FLOOR):
        raise RuntimeError(f"ATTEMPT_ROOT_OUTSIDE_FLOOR:{path}")
    existing = nearest_existing_parent(path)
    probe = existing
    checked: list[str] = []
    while True:
        if not probe.is_dir() or probe.is_symlink() or is_reparse(probe):
            raise RuntimeError(f"ANCESTOR_NOT_REAL_DIRECTORY:{probe}")
        checked.append(str(probe))
        if probe == EXTERNAL_FLOOR:
            break
        parent = probe.parent
        if parent == probe or not windows_under(probe, EXTERNAL_FLOOR):
            raise RuntimeError(f"ANCESTOR_ESCAPES_FLOOR:{probe}")
        probe = parent
    return {
        "path": str(path),
        "nearest_existing_parent": str(existing),
        "ancestors_checked": checked,
    }


def create_new_tree(root: Path, relatives: Iterable[str]) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for relative in relatives:
        target = root / relative
        target.mkdir(parents=True, exist_ok=False)


def tree_observation(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "files": 0, "directories": 0, "bytes": 0}
    if not root.is_dir() or root.is_symlink() or is_reparse(root):
        raise RuntimeError(f"ROOT_NOT_REAL_DIRECTORY:{root}")
    total_bytes = 0
    file_count = 0
    directory_count = 1
    stack = [root]
    while stack:
        current = stack.pop()
        for entry in os.scandir(current):
            info = entry.stat(follow_symlinks=False)
            attributes = getattr(info, "st_file_attributes", 0)
            if entry.is_symlink() or attributes & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            ):
                raise RuntimeError(f"TREE_LINK_OR_REPARSE:{entry.path}")
            if stat.S_ISDIR(info.st_mode):
                directory_count += 1
                stack.append(Path(entry.path))
            elif stat.S_ISREG(info.st_mode):
                file_count += 1
                total_bytes += info.st_size
            else:
                raise RuntimeError(f"TREE_NON_REGULAR:{entry.path}")
    return {
        "exists": True,
        "files": file_count,
        "directories": directory_count,
        "bytes": total_bytes,
    }


def run_git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"GIT_COMMAND_FAILED:{args[0]}:{result.stderr.decode('utf-8', 'replace')[-500:]}"
        )
    return result


def git_text(repo_root: Path, *args: str) -> str:
    return run_git(repo_root, *args).stdout.decode("utf-8", "strict").strip()


def git_commit_for_path(repo_root: Path, revision: str, relative: Path) -> str:
    return git_text(
        repo_root,
        "log",
        "-1",
        "--format=%H",
        revision,
        "--",
        relative.as_posix(),
    ).casefold()


def validate_minimal_pre_runtime_gate_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    policy = contract.get("execution_policy")
    handoff = contract.get("validation_and_handoff")
    if not isinstance(policy, dict) or not isinstance(handoff, dict):
        raise RuntimeError("MINIMAL_PRE_RUNTIME_GATE_MISSING")
    expected = {
        "central_static_receipt_required_before_runtime": True,
        "fresh_independent_audit_required_before_runtime": False,
        "fresh_independent_audit_timing": "POST_RUNTIME",
        "runtime_authority": (
            "EXACT_HEAD_CLEAN_TRACKED_TREE_CONFIRMATION_AND_CENTRAL_STATIC_RECEIPT"
        ),
    }
    observed = {
        "central_static_receipt_required_before_runtime": policy.get(
            "central_static_receipt_required_before_runtime"
        ),
        "fresh_independent_audit_required_before_runtime": policy.get(
            "fresh_independent_audit_required_before_runtime"
        ),
        "fresh_independent_audit_timing": handoff.get(
            "fresh_independent_audit_timing"
        ),
        "runtime_authority": handoff.get("runtime_authority"),
    }
    if observed != expected:
        raise RuntimeError("MINIMAL_PRE_RUNTIME_GATE_POLICY_MISMATCH")
    if handoff.get("central_static_receipt") != MINIMAL_CENTRAL_RECEIPT_RELATIVE.as_posix():
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_PATH_MISMATCH")
    if handoff.get("central_receipt_schema") != MINIMAL_CENTRAL_RECEIPT_SCHEMA:
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_SCHEMA_MISMATCH")
    if handoff.get("central_receipt_verdict") != MINIMAL_CENTRAL_RECEIPT_VERDICT:
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_VERDICT_MISMATCH")
    return observed


def validate_minimal_central_receipt(
    repo_root: Path, actual_head: str, contract: dict[str, Any]
) -> dict[str, Any]:
    gate = validate_minimal_pre_runtime_gate_contract(contract)
    try:
        blob = git_blob(repo_root, actual_head, MINIMAL_CENTRAL_RECEIPT_RELATIVE)
    except RuntimeError as exc:
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_MISSING") from exc
    worktree_path = repo_root / MINIMAL_CENTRAL_RECEIPT_RELATIVE
    require_regular(worktree_path)
    if blob != worktree_path.read_bytes():
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_BYTES_MISMATCH")

    receipt_commit = git_commit_for_path(
        repo_root, actual_head, MINIMAL_CENTRAL_RECEIPT_RELATIVE
    )
    if receipt_commit != actual_head:
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_NOT_AT_EXPECTED_HEAD")
    implementation = git_text(repo_root, "rev-parse", f"{actual_head}^").casefold()
    if not re.fullmatch(r"[0-9a-f]{40}", implementation):
        raise RuntimeError("MINIMAL_IMPLEMENTATION_COMMIT_INVALID")

    receipt = strict_load(worktree_path)
    subject = receipt.get("subject", {})
    tests = receipt.get("static_tests", {})
    packet = receipt.get("packet_validator", {})
    x0 = receipt.get("x0_docker_smoke", {})
    if (
        receipt.get("schema_version") != MINIMAL_CENTRAL_RECEIPT_SCHEMA
        or receipt.get("stage_id") != "R6-C1R3-LINUX"
        or receipt.get("verdict") != MINIMAL_CENTRAL_RECEIPT_VERDICT
        or subject.get("implementation_commit", "").casefold() != implementation
        or subject.get("runner_contract_schema")
        != "stage1e-r6-c1r3-linux-materialization-runner-contract-1.3"
        or tests.get("tests_passed") != 25
        or tests.get("tests_total") != 25
        or packet.get("checks_passed") != 72
        or packet.get("checks_total") != 72
        or x0.get("verdict") != "PASS_X0_DOCKER_DAEMON_SMOKE"
        or receipt.get("scope_boundary", {}).get("materialization_executed") is not False
        or receipt.get("scope_boundary", {}).get("training") is not False
        or receipt.get("scope_boundary", {}).get("evaluation") is not False
        or receipt.get("scope_boundary", {}).get("test_opened") is not False
        or receipt.get("truth_state") != TRUTH_STATE
    ):
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_SEMANTICS_INVALID")

    expected_hashes = {
        "runner": sha256_bytes(git_blob(repo_root, implementation, RUNNER_RELATIVE)),
        "contract": sha256_bytes(
            git_blob(repo_root, implementation, CONTRACT_RELATIVE)
        ),
        "tests": sha256_bytes(
            git_blob(
                repo_root,
                implementation,
                CONTROL_RELATIVE / "test_execute_e4_r6_c1r3_linux_materialization.py",
            )
        ),
    }
    if subject.get("artifact_sha256") != expected_hashes:
        raise RuntimeError("MINIMAL_CENTRAL_RECEIPT_ARTIFACT_HASH_MISMATCH")
    return {
        **gate,
        "central_receipt_commit": receipt_commit,
        "implementation_commit": implementation,
        "central_receipt_sha256": sha256_bytes(blob),
    }


def git_blob(repo_root: Path, revision: str, relative: Path) -> bytes:
    return run_git(
        repo_root, "cat-file", "blob", f"{revision}:{relative.as_posix()}"
    ).stdout


def assert_repo_authority(repo_root: Path, expected_head: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise RuntimeError("EXPECTED_HEAD_INVALID")
    top = Path(git_text(repo_root, "rev-parse", "--show-toplevel")).resolve()
    if top != repo_root.resolve() or repo_root.resolve() != REPO_FROM_FILE:
        raise RuntimeError("EXECUTION_ROOT_MISMATCH")
    actual_head = git_text(repo_root, "rev-parse", "HEAD").casefold()
    if actual_head != expected_head:
        raise RuntimeError("HEAD_MISMATCH")
    ancestor = run_git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        ACCEPTED_PACKET_AUDIT_COMMIT,
        actual_head,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("ACCEPTED_PACKET_AUDIT_NOT_ANCESTOR")
    status = run_git(
        repo_root, "status", "--porcelain=v1", "--untracked-files=no"
    ).stdout
    if status:
        raise RuntimeError("RUNTIME_WORKTREE_NOT_CLEAN")

    bindings: list[dict[str, Any]] = []
    for relative, expected_oid in LOCKED_BLOB_OIDS.items():
        oid = git_text(repo_root, "rev-parse", f"{actual_head}:{relative.as_posix()}")
        if oid != expected_oid:
            raise RuntimeError(f"LOCKED_BLOB_OID_MISMATCH:{relative.as_posix()}")
        blob = git_blob(repo_root, actual_head, relative)
        worktree = (repo_root / relative).read_bytes()
        if blob != worktree:
            raise RuntimeError(f"WORKTREE_BLOB_BYTES_MISMATCH:{relative.as_posix()}")
        bindings.append(
            {
                "path": relative.as_posix(),
                "git_blob_oid": oid,
                "bytes": len(blob),
                "sha256": sha256_bytes(blob),
            }
        )

    for relative in (RUNNER_RELATIVE, CONTRACT_RELATIVE):
        blob = git_blob(repo_root, actual_head, relative)
        if blob != (repo_root / relative).read_bytes():
            raise RuntimeError(f"RUNTIME_CONTROL_BYTES_MISMATCH:{relative.as_posix()}")

    audit = strict_json_bytes(git_blob(repo_root, actual_head, PACKET_AUDIT_RELATIVE))
    if not isinstance(audit, dict):
        raise RuntimeError("PACKET_AUDIT_NOT_OBJECT")
    valid_audit = (
        audit.get("schema_version") == ACCEPTED_PACKET_AUDIT_SCHEMA
        and audit.get("verdict") == ACCEPTED_PACKET_AUDIT_VERDICT
        and audit.get("subject", {}).get("packet_commit") == ACCEPTED_PACKET_COMMIT
        and audit.get("subject", {}).get("packet_parent") == ACCEPTED_PACKET_PARENT
        and audit.get("validator", {}).get("checks_passed") == 72
        and audit.get("validator", {}).get("checks_total") == 72
        and audit.get("checkout_provenance_validation", {}).get(
            "raw_worktree_bytes_equal_git_blobs"
        )
        == 9
        and audit.get("checkout_provenance_validation", {}).get(
            "raw_worktree_bytes_total"
        )
        == 9
        and audit.get("truth_state") == TRUTH_STATE
        and audit.get("execution_authorized") is False
        and audit.get("RESULT_STATUS") == "NOT_RUN"
        and audit.get("TEST_SET_OPENED") == "NO"
        and audit.get("ACCEPTED_RESULT_ROWS") == 0
    )
    if not valid_audit:
        raise RuntimeError("PACKET_AUDIT_REPLAY_FAILED")

    contract = strict_json_bytes(git_blob(repo_root, actual_head, CONTRACT_RELATIVE))
    if not isinstance(contract, dict):
        raise RuntimeError("RUNNER_CONTRACT_NOT_OBJECT")
    if (
        contract.get("schema_version")
        != "stage1e-r6-c1r3-linux-materialization-runner-contract-1.3"
        or contract.get("accepted_packet_audit", {}).get("commit")
        != ACCEPTED_PACKET_AUDIT_COMMIT
        or tuple(contract.get("runtime_scope", {}).get("included_command_ids", []))
        != EXPECTED_COMMAND_IDS
        or contract.get("truth_state") != TRUTH_STATE
    ):
        raise RuntimeError("RUNNER_CONTRACT_REPLAY_FAILED")
    central_gate = validate_minimal_central_receipt(repo_root, actual_head, contract)
    return {
        "head": actual_head,
        "locked_bindings": bindings,
        "minimal_pre_runtime_gate": central_gate,
    }


def run_packet_validator(repo_root: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(repo_root / PACKET_VALIDATOR_RELATIVE),
            "--packet-root",
            str(repo_root / PACKET_RELATIVE),
        ],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "LIVE_PACKET_VALIDATOR_FAILED:"
            + result.stderr.decode("utf-8", "replace")[-500:]
        )
    value = strict_json_bytes(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("LIVE_PACKET_VALIDATOR_NOT_OBJECT")
    diagnostics = value.get("diagnostics", {})
    source_replay = diagnostics.get("source_replay", {})
    if (
        value.get("verdict") != "PASS_R6_C1R3_LINUX_PACKET_READY_FOR_FRESH_XHIGH_AUDIT"
        or diagnostics.get("passed_count") != 72
        or diagnostics.get("check_count") != 72
        or value.get("failures") != []
        or source_replay.get("files") != 265
        or source_replay.get("bytes") != 1_541_044
        or source_replay.get("failure_count") != 0
    ):
        raise RuntimeError("LIVE_PACKET_VALIDATOR_SEMANTICS_FAILED")
    return value


def sanitized_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() not in DROP_ENV_NAMES
        and not key.casefold().startswith("pip_")
    }
    environment.update(
        {
            "NO_COLOR": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    return environment


def kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            check=False,
        )
    else:
        process.kill()


def tail_utf8(path: Path, maximum: int = 4000) -> str:
    with path.open("rb") as stream:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - maximum))
        return stream.read().decode("utf-8", "replace")


class EvidenceExecutor:
    def __init__(self, repo_root: Path, run_root: Path) -> None:
        self.repo_root = repo_root
        self.run_root = run_root
        self.journal = run_root / "command_journal.jsonl"
        self.sequence = 0
        self.results: list[dict[str, Any]] = []

    def run(
        self,
        identifier: str,
        argv: list[str],
        timeout_seconds: int,
        *,
        category: str,
        network: bool | None,
    ) -> tuple[dict[str, Any], Path, Path]:
        self.sequence += 1
        sequence = self.sequence
        stem = f"{sequence:03d}_{identifier}"
        stdout_path = self.run_root / "logs" / f"{stem}.stdout.bin"
        stderr_path = self.run_root / "logs" / f"{stem}.stderr.bin"
        started_at = utc_now()
        started = time.perf_counter()
        timed_out = False
        launch_error: str | None = None
        process: subprocess.Popen[bytes] | None = None
        print(
            json.dumps(
                {
                    "event": "command_started",
                    "sequence": sequence,
                    "command_id": identifier,
                    "category": category,
                    "timeout_seconds": timeout_seconds,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        with stdout_path.open("xb") as stdout_stream, stderr_path.open(
            "xb"
        ) as stderr_stream:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=self.repo_root,
                    env=sanitized_environment(),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_stream,
                    stderr=stderr_stream,
                    shell=False,
                )
                next_heartbeat = 30.0
                while process.poll() is None:
                    elapsed = time.perf_counter() - started
                    if elapsed >= timeout_seconds:
                        timed_out = True
                        kill_process_tree(process)
                        break
                    if elapsed >= next_heartbeat:
                        stdout_stream.flush()
                        stderr_stream.flush()
                        print(
                            json.dumps(
                                {
                                    "event": "command_heartbeat",
                                    "sequence": sequence,
                                    "command_id": identifier,
                                    "elapsed_seconds": round(elapsed, 3),
                                    "stdout_bytes": stdout_path.stat().st_size,
                                    "stderr_bytes": stderr_path.stat().st_size,
                                },
                                sort_keys=True,
                            ),
                            flush=True,
                        )
                        next_heartbeat += 30.0
                    time.sleep(1.0)
                if process.poll() is None:
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        kill_process_tree(process)
                        process.wait(timeout=15)
            except OSError as exc:
                launch_error = f"{type(exc).__name__}:{exc}"
            finally:
                stdout_stream.flush()
                stderr_stream.flush()
                os.fsync(stdout_stream.fileno())
                os.fsync(stderr_stream.fileno())

        exit_code = process.returncode if process is not None else None
        success = exit_code == 0 and not timed_out and launch_error is None
        result: dict[str, Any] = {
            "sequence": sequence,
            "command_id": identifier,
            "category": category,
            "argv_sha256": argv_hash(argv),
            "network_declared": network,
            "started_at": started_at,
            "ended_at": utc_now(),
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "timeout_seconds": timeout_seconds,
            "timed_out": timed_out,
            "exit_code": exit_code,
            "launch_error": launch_error,
            "stdout": {
                "path": stdout_path.relative_to(self.run_root).as_posix(),
                **raw_fact(stdout_path),
            },
            "stderr": {
                "path": stderr_path.relative_to(self.run_root).as_posix(),
                **raw_fact(stderr_path),
            },
            "retry_count": 0,
            "fallback_count": 0,
            "process_success": success,
            "success": success,
        }
        if not success:
            result["stdout_tail_utf8"] = tail_utf8(stdout_path)
            result["stderr_tail_utf8"] = tail_utf8(stderr_path)
        return result, stdout_path, stderr_path

    def commit(self, result: dict[str, Any]) -> None:
        append_jsonl(self.journal, result)
        self.results.append(result)
        print(
            json.dumps(
                {
                    "event": "command_complete",
                    "sequence": result["sequence"],
                    "command_id": result["command_id"],
                    "success": result["success"],
                    "exit_code": result["exit_code"],
                    "elapsed_seconds": result["elapsed_seconds"],
                },
                sort_keys=True,
            ),
            flush=True,
        )


def require_regular(path: Path) -> None:
    if not path.is_file() or path.is_symlink() or is_reparse(path):
        raise RuntimeError(f"REQUIRED_REGULAR_FILE_MISSING:{path}")


def receipt(path: Path) -> dict[str, Any]:
    require_regular(path)
    return strict_load(path)


def write_image_adapter(
    identifier: str, stdout_path: Path, run_root: Path, result: dict[str, Any]
) -> None:
    target = run_root / "receipts"
    if identifier == "I00_PULL_EXACT_OFFICIAL_PLATFORM_MANIFEST":
        write_json_new(
            target / "image_pull.json",
            {
                "schema_version": "stage1e-r6-c1r3-image-pull-1.0",
                "image_ref": IMAGE_REF,
                "argv_sha256": result["argv_sha256"],
                "network": True,
                "retry_count": 0,
                "fallback_count": 0,
                "verdict": "PASS",
            },
        )
        return
    value = strict_json_bytes(stdout_path.read_bytes())
    if identifier == "I01_INSPECT_LOCAL_IMAGE_IDENTITY":
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise RuntimeError("IMAGE_INSPECT_OUTPUT_INVALID")
        row = value[0]
        repo_digests = row.get("RepoDigests")
        if (
            not isinstance(row.get("Id"), str)
            or not str(row["Id"]).startswith("sha256:")
            or not isinstance(repo_digests, list)
            or IMAGE_REF not in repo_digests
            or row.get("Os") != "linux"
            or row.get("Architecture") != "amd64"
        ):
            raise RuntimeError("IMAGE_IDENTITY_POSTCONDITION_FAILED")
        write_json_new(
            target / "image_identity.json",
            {
                "schema_version": "stage1e-r6-c1r3-image-identity-1.0",
                "image_ref": IMAGE_REF,
                "local_image_id": row["Id"],
                "repo_digests": repo_digests,
                "os": row["Os"],
                "architecture": row["Architecture"],
                "verdict": "PASS",
            },
        )
        return
    if identifier == "I02_PROBE_EXACT_CPYTHON_IDENTITY":
        if not isinstance(value, dict):
            raise RuntimeError("PYTHON_IDENTITY_OUTPUT_INVALID")
        machine = str(value.get("machine", "")).casefold()
        if (
            value.get("python") != "3.11.9"
            or value.get("implementation") != "CPython"
            or value.get("platform") != "linux"
            or machine not in {"x86_64", "amd64"}
            or value.get("executable") != "/usr/local/bin/python"
        ):
            raise RuntimeError("PYTHON_IDENTITY_POSTCONDITION_FAILED")
        write_json_new(
            target / "python_runtime_identity.json",
            {
                "schema_version": "stage1e-r6-c1r3-python-runtime-identity-1.0",
                **value,
                "architecture": "amd64",
                "verdict": "PASS",
            },
        )


def validate_packet_postcondition(
    identifier: str,
    stdout_path: Path,
    run_root: Path,
    data_root: Path,
    env_root: Path,
    result: dict[str, Any],
) -> None:
    if identifier.startswith("I"):
        write_image_adapter(identifier, stdout_path, run_root, result)
        return
    if identifier == "M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES":
        value = receipt(data_root / "receipts/dataset_acquisition.json")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-ml100k-acquisition-1.0"
            or value.get("attempt") != ATTEMPT_NAME
            or value.get("archive_provider_md5_verified") is not True
            or value.get("archive_frozen_sha256_verified") is not True
            or value.get("verdict") != "PASS"
        ):
            raise RuntimeError("DATASET_ACQUISITION_RECEIPT_INVALID")
    elif identifier == "M01_SAFE_EXTRACT_CONVERT_AND_RECONCILE":
        extraction = receipt(data_root / "receipts/extraction_inventory.json")
        maps = receipt(data_root / "receipts/first_occurrence_id_maps.json")
        reconciliation = receipt(data_root / "receipts/raw_to_atomic_reconciliation.json")
        if (
            extraction.get("schema_version")
            != "stage1e-r6-c1r3-ml100k-extraction-1.0"
            or extraction.get("safe_extraction_checks") != "PASS"
            or maps.get("schema_version")
            != "stage1e-r6-c1r3-first-occurrence-maps-1.0"
            or reconciliation.get("schema_version")
            != "stage1e-r6-c1r3-raw-atomic-reconciliation-1.0"
            or reconciliation.get("rows_checked") != 100000
            or reconciliation.get("projection_equal") is not True
            or reconciliation.get("filtering") is not False
            or reconciliation.get("deduplication") is not False
            or reconciliation.get("sorting") is not False
            or reconciliation.get("id_rewrite") is not False
            or reconciliation.get("timestamp_rewrite") is not False
            or reconciliation.get("verdict") != "PASS"
        ):
            raise RuntimeError("DATASET_TRANSFORMATION_RECEIPTS_INVALID")
    elif identifier == "M02_SEAL_DATASET_MATERIALIZATION_RECEIPT":
        validate_dataset_final_receipt(
            receipt(data_root / "receipts/dataset_materialization.json")
        )
    elif identifier == "E00_DOWNLOAD_LINUX_WHEEL_CLOSURE":
        files = list((env_root / "wheelhouse").iterdir())
        if not files or any(
            not path.is_file()
            or path.is_symlink()
            or is_reparse(path)
            or path.suffix.casefold() != ".whl"
            for path in files
        ):
            raise RuntimeError("WHEELHOUSE_DOWNLOAD_POSTCONDITION_FAILED")
    elif identifier == "E01_HASH_AND_FREEZE_WHEEL_CLOSURE":
        value = receipt(env_root / "receipts/wheelhouse_manifest.json")
        require_regular(env_root / "receipts/hashed_third_party_requirements.txt")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-linux-wheelhouse-1.0"
            or value.get("platform") != "linux/amd64"
            or value.get("python") != "3.11.9"
            or value.get("wheel_only") is not True
            or value.get("cpu_only") is not True
            or value.get("recbole_absent") is not True
        ):
            raise RuntimeError("WHEELHOUSE_MANIFEST_INVALID")
    elif identifier in {
        "E02_CREATE_EXACT_CONTAINER_VENV",
        "E03_INSTALL_HASHED_THIRD_PARTY_CLOSURE",
    }:
        require_regular(env_root / "venv/bin/python")
    elif identifier == "E04_STAGE_VERIFIED_RECBOLE_SOURCE":
        value = receipt(env_root / "receipts/recbole_source_staging.json")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-recbole-source-staging-1.0"
            or value.get("file_count") != 265
            or value.get("total_bytes") != 1_541_044
            or value.get("source_destination_equal") is not True
        ):
            raise RuntimeError("RECBOLE_SOURCE_STAGING_RECEIPT_INVALID")
    elif identifier == "E05_PREPARE_EPHEMERAL_BUILD_SOURCE":
        value = receipt(env_root / "receipts/recbole_build_source.json")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-recbole-build-source-1.0"
            or value.get("file_count") != 265
            or value.get("total_bytes") != 1_541_044
            or value.get("source_destination_equal") is not True
            or value.get("immutable_staging_unchanged") is not True
        ):
            raise RuntimeError("RECBOLE_BUILD_SOURCE_RECEIPT_INVALID")
    elif identifier == "E06_BUILD_LOCAL_RECBOLE_WHEEL":
        wheels = list((env_root / "local-wheel").glob("*.whl"))
        if len(wheels) != 1 or any(path.is_symlink() or is_reparse(path) for path in wheels):
            raise RuntimeError("LOCAL_RECBOLE_WHEEL_COUNT_INVALID")
    elif identifier == "E07_HASH_LOCAL_RECBOLE_WHEEL":
        value = receipt(env_root / "receipts/local_recbole_wheel.json")
        require_regular(env_root / "receipts/hashed_local_recbole_requirement.txt")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-local-recbole-wheel-1.0"
            or value.get("name") != "recbole"
            or value.get("version") != "1.2.1"
            or value.get("local_source_build") is not True
        ):
            raise RuntimeError("LOCAL_RECBOLE_WHEEL_RECEIPT_INVALID")
    elif identifier == "E08_INSTALL_HASHED_LOCAL_RECBOLE_WHEEL":
        require_regular(env_root / "venv/bin/python")
    elif identifier == "E09_SEAL_ENVIRONMENT_AND_IMPORT_CHECK":
        validate_environment_final_receipt(
            receipt(env_root / "receipts/environment_materialization.json")
        )
    elif identifier == "E10_ASSERT_ATTEMPT_WRITE_BOUNDARY":
        value = receipt(env_root / "receipts/environment_attempt_inventory.json")
        if (
            value.get("schema_version")
            != "stage1e-r6-c1r3-environment-inventory-1.0"
            or not isinstance(value.get("files"), list)
            or value.get("file_count") != len(value["files"])
        ):
            raise RuntimeError("ENVIRONMENT_INVENTORY_RECEIPT_INVALID")
    else:
        raise RuntimeError(f"UNHANDLED_PACKET_POSTCONDITION:{identifier}")


def decode_windows_output(payload: bytes) -> str:
    if b"\x00" in payload:
        try:
            return payload.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    return payload.decode("utf-8", "replace")


def validate_docker_server_absence(
    result: dict[str, Any], stdout: bytes, stderr: bytes
) -> dict[str, Any]:
    stdout_text = decode_windows_output(stdout).replace("\x00", "").replace("\ufeff", "").strip()
    stderr_text = decode_windows_output(stderr).replace("\x00", "").replace("\ufeff", "").strip()
    combined = (stdout_text + "\n" + stderr_text).casefold()
    if "access is denied" in combined or "e_accessdenied" in combined:
        raise RuntimeError("DOCKER_SERVER_PROBE_ACCESS_DENIED")
    process_shape = (
        result.get("exit_code") == 1
        and result.get("process_success") is False
        and result.get("launch_error") is None
        and result.get("timed_out") is False
    )
    signature = (
        stdout_text.casefold() == "null"
        and DOCKER_SERVER_PIPE in combined
        and DOCKER_SERVER_NOT_FOUND in combined
    )
    if not process_shape or not signature:
        raise RuntimeError("DOCKER_SERVER_ABSENCE_SIGNATURE_MISMATCH")
    return {
        "exit_code": 1,
        "stdout_token": "null",
        "endpoint": DOCKER_SERVER_PIPE,
        "os_error": DOCKER_SERVER_NOT_FOUND,
        "docker_server_endpoint_absent": True,
    }


def wsl_running_distros(
    result: dict[str, Any], stdout: bytes, stderr: bytes
) -> list[str]:
    stdout_text = decode_windows_output(stdout).replace("\x00", "").replace("\ufeff", "")
    stderr_text = decode_windows_output(stderr).replace("\x00", "").replace("\ufeff", "")
    combined = (stdout_text + "\n" + stderr_text).casefold()
    if "access is denied" in combined or "e_accessdenied" in combined:
        raise RuntimeError("WSL_ENUMERATION_ACCESS_DENIED")
    if not (
        result.get("exit_code") == 0
        and result.get("process_success") is True
        and result.get("launch_error") is None
        and result.get("timed_out") is False
    ):
        raise RuntimeError("WSL_ENUMERATION_FAILED")
    return [line.strip() for line in stdout_text.splitlines() if line.strip()]


def docker_processes(
    result: dict[str, Any], stdout: bytes, stderr: bytes
) -> tuple[list[str], int]:
    stdout_text = decode_windows_output(stdout).replace("\x00", "").replace("\ufeff", "")
    stderr_text = decode_windows_output(stderr).replace("\x00", "").replace("\ufeff", "")
    combined = (stdout_text + "\n" + stderr_text).casefold()
    if "access is denied" in combined or "e_accessdenied" in combined:
        raise RuntimeError("TASKLIST_ACCESS_DENIED")
    if not (
        result.get("exit_code") == 0
        and result.get("process_success") is True
        and result.get("launch_error") is None
        and result.get("timed_out") is False
    ):
        raise RuntimeError("TASKLIST_ENUMERATION_FAILED")
    try:
        rows = list(csv.reader(io.StringIO(stdout_text)))
    except csv.Error as exc:
        raise RuntimeError("TASKLIST_CSV_INVALID") from exc
    if not rows or any(
        len(row) != 5 or not row[0].strip() or not row[1].strip().isdigit()
        for row in rows
    ):
        raise RuntimeError("TASKLIST_CSV_INVALID")
    images = [row[0].strip() for row in rows]
    matches = sorted(
        {image for image in images if image.casefold() in DOCKER_PROCESS_NAMES},
        key=str.casefold,
    )
    return matches, len(images)


def validate_stopped_snapshot(
    docker_result: dict[str, Any],
    docker_stdout: bytes,
    docker_stderr: bytes,
    wsl_result: dict[str, Any],
    wsl_stdout: bytes,
    wsl_stderr: bytes,
    tasklist_result: dict[str, Any],
    tasklist_stdout: bytes,
    tasklist_stderr: bytes,
) -> dict[str, Any]:
    daemon = validate_docker_server_absence(
        docker_result, docker_stdout, docker_stderr
    )
    distros = wsl_running_distros(wsl_result, wsl_stdout, wsl_stderr)
    if distros:
        raise RuntimeError("WSL_DISTRO_STILL_RUNNING")
    processes, image_count = docker_processes(
        tasklist_result, tasklist_stdout, tasklist_stderr
    )
    if processes:
        raise RuntimeError("DOCKER_PROCESS_STILL_RUNNING")
    return {
        "schema_version": "r6-c1r3-docker-wsl-stopped-composite-1.0",
        "passed": True,
        "docker_server_endpoint_absent": daemon[
            "docker_server_endpoint_absent"
        ],
        "docker_server_absence_signature": daemon,
        "wsl_running_distros": [],
        "docker_processes": [],
        "tasklist_image_count": image_count,
    }


def collect_stopped_snapshot(
    executor: EvidenceExecutor, prefix: str, *, category: str
) -> dict[str, Any]:
    docker_result, docker_stdout, docker_stderr = executor.run(
        f"{prefix}_DOCKER_SERVER_ENDPOINT_ABSENT",
        [str(DOCKER_EXE), "version", "--format", "{{json .Server}}"],
        120,
        category=category,
        network=None,
    )
    wsl_result, wsl_stdout, wsl_stderr = executor.run(
        f"{prefix}_WSL_RUNNING_DISTROS",
        [str(WSL_EXE), "--list", "--running", "--quiet"],
        120,
        category=category,
        network=None,
    )
    tasklist_result, tasklist_stdout, tasklist_stderr = executor.run(
        f"{prefix}_DOCKER_PROCESS_INVENTORY",
        [str(TASKLIST_EXE), "/FO", "CSV", "/NH"],
        120,
        category=category,
        network=None,
    )
    try:
        evidence = validate_stopped_snapshot(
            docker_result,
            docker_stdout.read_bytes(),
            docker_stderr.read_bytes(),
            wsl_result,
            wsl_stdout.read_bytes(),
            wsl_stderr.read_bytes(),
            tasklist_result,
            tasklist_stdout.read_bytes(),
            tasklist_stderr.read_bytes(),
        )
    except Exception as exc:
        evidence = {
            "schema_version": "r6-c1r3-docker-wsl-stopped-composite-1.0",
            "passed": False,
            "state_error": f"{type(exc).__name__}:{exc}",
        }
    for role, result in (
        ("docker_server_absence", docker_result),
        ("wsl_running_distros", wsl_result),
        ("docker_process_inventory", tasklist_result),
    ):
        result["state_evidence_role"] = role
        result["state_evidence_success"] = evidence["passed"]
        if not evidence["passed"]:
            result["state_error"] = evidence["state_error"]
        executor.commit(result)
    return evidence


def wait_for_docker_server(
    executor: EvidenceExecutor, *, timeout_seconds: int = 180, interval_seconds: int = 5
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    probe = 0
    while True:
        probe += 1
        result, stdout_path, _ = executor.run(
            f"L00_DOCKER_SERVER_READY_{probe:02d}",
            DOCKER_READY_ARGV,
            20,
            category="lifecycle",
            network=None,
        )
        server: Any = None
        if result["process_success"]:
            try:
                server = strict_json_bytes(stdout_path.read_bytes())
            except (StrictJsonError, UnicodeDecodeError) as exc:
                result["success"] = False
                result["readiness_error"] = f"{type(exc).__name__}:{exc}"
        ready = isinstance(server, dict) and bool(server)
        result["state_evidence_role"] = "docker_server_ready"
        result["state_evidence_success"] = ready
        if result["process_success"] and not ready:
            result["success"] = False
            result["readiness_error"] = "DOCKER_SERVER_RESPONSE_NOT_OBJECT"
        executor.commit(result)
        if ready:
            return {
                "schema_version": "r6-c1r3-docker-server-ready-1.0",
                "probe_count": probe,
                "server": server,
                "passed": True,
            }
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("DOCKER_SERVER_READINESS_TIMEOUT")
        time.sleep(min(interval_seconds, remaining))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--execution-confirmation", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root_created = False
    executor: EvidenceExecutor | None = None
    primary_error: Exception | None = None
    materialization_passed = False
    docker_start_attempted = False
    docker_server_ready: dict[str, Any] | None = None
    cleanup: dict[str, Any] = {
        "docker_stop_attempts": 0,
        "wsl_shutdown_attempts": 0,
        "closure_snapshots": [],
        "passed": False,
    }

    try:
        if not sys.dont_write_bytecode or "-B" not in list(getattr(sys, "orig_argv", [])):
            raise RuntimeError("INTERPRETER_DASH_B_REQUIRED")
        repo_root = Path(args.repo_root).resolve()
        require_confirmation(args.execution_confirmation)
        authority = assert_repo_authority(repo_root, args.expected_head.casefold())
        plan = load_execution_plan(repo_root)
        validator = run_packet_validator(repo_root)
        docker_fact = raw_fact(DOCKER_EXE)
        if (
            not DOCKER_EXE.is_file()
            or DOCKER_EXE.is_symlink()
            or is_reparse(DOCKER_EXE)
            or docker_fact != {"bytes": DOCKER_BYTES, "sha256": DOCKER_SHA256}
        ):
            raise RuntimeError("DOCKER_EXECUTABLE_IDENTITY_MISMATCH")
        require_regular(WSL_EXE)
        require_regular(TASKLIST_EXE)
        roots = {
            "runner": verify_absent_external_root(RUN_ROOT),
            "dataset": verify_absent_external_root(DATA_ROOT),
            "environment": verify_absent_external_root(ENV_ROOT),
        }
        capacities = {
            "C_free_bytes": shutil.disk_usage(Path("C:\\")).free,
            "E_free_bytes": shutil.disk_usage(Path("E:\\")).free,
        }
        if capacities["C_free_bytes"] < 20 * 1024**3:
            raise RuntimeError("C_FREE_SPACE_BELOW_20_GIB")
        if capacities["E_free_bytes"] < 50 * 1024**3:
            raise RuntimeError("E_FREE_SPACE_BELOW_50_GIB")

        create_new_tree(RUN_ROOT, ("logs", "receipts"))
        run_root_created = True
        executor = EvidenceExecutor(repo_root, RUN_ROOT)

        baseline = collect_stopped_snapshot(executor, "P00", category="preflight")
        if not baseline["passed"]:
            raise RuntimeError(
                "DOCKER_WSL_BASELINE_NOT_AUTHORITATIVELY_STOPPED:"
                + str(baseline.get("state_error", "UNKNOWN"))
            )

        write_json_new(
            RUN_ROOT / "preflight.json",
            {
                "schema_version": "stage1e-r6-c1r3-linux-runtime-preflight-1.0",
                "created_at": utc_now(),
                "authority": authority,
                "live_packet_validator": validator,
                "docker_executable": docker_fact,
                "roots": roots,
                "capacities": capacities,
                "docker_wsl_baseline": baseline,
                "attempt_rebase": {
                    "source_attempt": SOURCE_ATTEMPT_NAME,
                    "target_attempt": ATTEMPT_NAME,
                    "transform": "exact argv token substring replacement only",
                    "changed_commands": [
                        {
                            "command_id": row["id"],
                            "source_argv_sha256": row["source_argv_sha256"],
                            "executed_argv_sha256": row["argv_sha256"],
                        }
                        for row in plan
                        if row.get("source_argv_sha256")
                    ],
                },
                "fresh_explicit_authorization": True,
                "root_creation_state": {
                    "runner_root_created": True,
                    "dataset_root_created": False,
                    "environment_root_created": False,
                },
                "truth_state": TRUTH_STATE,
                "verdict": "PASS_READY_FOR_ONE_DOCKER_START_AND_M0_M1_ONLY",
            },
        )

        docker_start_attempted = True
        start_result, _, _ = executor.run(
            "L00_DOCKER_DESKTOP_START",
            DOCKER_START_ARGV,
            60,
            category="lifecycle",
            network=None,
        )
        executor.commit(start_result)
        if not start_result["success"]:
            raise RuntimeError("DOCKER_DESKTOP_START_FAILED")
        docker_server_ready = wait_for_docker_server(executor)
        write_json_new(RUN_ROOT / "receipts/docker_server_ready.json", docker_server_ready)

        def create_lane_roots() -> None:
            verify_absent_external_root(DATA_ROOT)
            verify_absent_external_root(ENV_ROOT)
            if shutil.disk_usage(Path("E:\\")).free < 50 * 1024**3:
                raise RuntimeError("E_FREE_SPACE_BELOW_50_GIB_AT_ROOT_CREATION")
            create_new_tree(
                DATA_ROOT,
                (
                    "download",
                    "provider_metadata",
                    "extract-staging",
                    "raw",
                    "recbole_atomic",
                    "receipts",
                ),
            )
            create_new_tree(
                ENV_ROOT,
                (
                    "wheelhouse",
                    "source-staging",
                    "build-source",
                    "local-wheel",
                    "receipts",
                ),
            )
            append_jsonl(
                executor.journal,
                {
                    "event": "lane_roots_created_after_I02",
                    "created_at": utc_now(),
                    "dataset_root": str(DATA_ROOT),
                    "environment_root": str(ENV_ROOT),
                },
            )

        def execute_packet(row: dict[str, Any]) -> None:
            validate_packet_command(row)
            result, stdout_path, _ = executor.run(
                row["id"],
                list(row["argv"]),
                int(row["timeout_seconds"]),
                category="packet",
                network=bool(row["network"]),
            )
            if result["argv_sha256"] != row["argv_sha256"]:
                result["success"] = False
                result["postcondition_error"] = "EXECUTED_ARGV_HASH_MISMATCH"
            elif result["process_success"]:
                try:
                    validate_packet_postcondition(
                        row["id"], stdout_path, RUN_ROOT, DATA_ROOT, ENV_ROOT, result
                    )
                    result["postconditions_passed"] = True
                except Exception as exc:
                    result["postconditions_passed"] = False
                    result["postcondition_error"] = f"{type(exc).__name__}:{exc}"
                    result["success"] = False
            executor.commit(result)
            if not result["success"]:
                raise RuntimeError(f"PACKET_COMMAND_FAILED:{row['id']}")

        orchestrate_commands(plan, execute_packet, create_lane_roots)
        validate_dataset_final_receipt(
            receipt(DATA_ROOT / "receipts/dataset_materialization.json")
        )
        validate_environment_final_receipt(
            receipt(ENV_ROOT / "receipts/environment_materialization.json")
        )
        materialization_passed = True
    except Exception as exc:
        primary_error = exc
    finally:
        if docker_start_attempted and executor is not None:
            cleanup["docker_stop_attempts"] = 1
            stop_result, _, _ = executor.run(
                "L01_DOCKER_DESKTOP_STOP",
                [str(DOCKER_EXE), "desktop", "stop"],
                300,
                category="cleanup",
                network=None,
            )
            executor.commit(stop_result)
            cleanup["docker_stop_process_success"] = stop_result["process_success"]

            cleanup["wsl_shutdown_attempts"] = 1
            shutdown_result, _, _ = executor.run(
                "L02_WSL_SHUTDOWN",
                [str(WSL_EXE), "--shutdown"],
                180,
                category="cleanup",
                network=None,
            )
            executor.commit(shutdown_result)
            cleanup["wsl_shutdown_process_success"] = shutdown_result[
                "process_success"
            ]

            snapshots: list[dict[str, Any]] = []
            for index in range(1, 4):
                if index > 1:
                    time.sleep(2.0)
                snapshot = collect_stopped_snapshot(
                    executor, f"C{index:02d}", category="closure"
                )
                snapshot["index"] = index
                snapshots.append(snapshot)
            cleanup["closure_snapshots"] = snapshots
            states = [
                {
                    "docker_server_endpoint_absent": row.get(
                        "docker_server_endpoint_absent"
                    ),
                    "wsl_running_distros": row.get("wsl_running_distros"),
                    "docker_processes": row.get("docker_processes"),
                }
                for row in snapshots
            ]
            independently_proven_stopped = (
                len(states) == 3
                and all(row.get("passed") is True for row in snapshots)
                and states[0] == states[1] == states[2]
            )
            cleanup["independently_proven_stopped"] = independently_proven_stopped
            cleanup["docker_stop_or_independently_proven_stopped"] = (
                stop_result["process_success"] or independently_proven_stopped
            )
            cleanup["passed"] = (
                shutdown_result["process_success"]
                and independently_proven_stopped
                and cleanup["docker_stop_or_independently_proven_stopped"]
            )

    overall_passed = materialization_passed and primary_error is None and cleanup["passed"]
    if primary_error is None and not cleanup["passed"]:
        primary_error = RuntimeError("FINAL_DOCKER_WSL_CLOSURE_FAILED")

    result_document = {
        "schema_version": "stage1e-r6-c1r3-linux-m0-m1-runtime-result-1.0",
        "created_at": utc_now(),
        "stage_id": "R6-C1R3-LINUX",
        "attempt": ATTEMPT_NAME,
        "passed": overall_passed,
        "materialization_passed": materialization_passed,
        "error_type": type(primary_error).__name__ if primary_error else None,
        "error": str(primary_error) if primary_error else None,
        "packet_commands_expected": len(EXPECTED_COMMAND_IDS),
        "packet_commands_succeeded": (
            sum(
                1
                for row in (executor.results if executor else [])
                if row.get("category") == "packet" and row.get("success") is True
            )
        ),
        "docker_start_attempts": 1 if docker_start_attempted else 0,
        "docker_server_ready": docker_server_ready,
        "retry_count": 0,
        "fallback_count": 0,
        "cleanup": cleanup,
        "runner_root": tree_observation(RUN_ROOT) if run_root_created else {"exists": False},
        "dataset_root": tree_observation(DATA_ROOT),
        "environment_root": tree_observation(ENV_ROOT),
        "bridge_executed": False,
        "dataset_constructed_or_loaded": False,
        "training": False,
        "evaluation": False,
        "metrics": False,
        "test_opened": False,
        "benchmark_admitted": False,
        "truth_state": TRUTH_STATE,
        "verdict": (
            "PASS_R6_C1R3_LINUX_M0_M1_MATERIALIZED_NOT_BENCHMARKED"
            if overall_passed
            else "HANDOFF_INCOMPLETE_R6_C1R3_LINUX_ATTEMPT005_CLOSED"
        ),
    }
    if run_root_created:
        publication_passed = persist_final_result(
            RUN_ROOT / "runner_result.json", result_document
        )
        overall_passed = overall_passed and publication_passed
    print(json.dumps(result_document, indent=2, sort_keys=True), flush=True)
    return 0 if overall_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
