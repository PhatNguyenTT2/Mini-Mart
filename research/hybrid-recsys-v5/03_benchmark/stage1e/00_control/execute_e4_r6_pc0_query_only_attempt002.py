from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import stat
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(r"E:\UIT\cv\backend")
CONTROL_ROOT = REPOSITORY_ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
RUNNER_PATH = CONTROL_ROOT / "execute_e4_r6_pc0_query_only_attempt002.py"
DISPATCH_PATH = CONTROL_ROOT / "rebaseline_v2_e4_r6_pc0_query_only_attempt002_dispatch.json"

RECOVERY_CHECKPOINT = "4f07d20c056b06cb255117e7b0d1284fdd40c320"
STAGE_ID = "E4-R6-PC0-QUERY-ATTEMPT-002"
STATUS = "READ_ONLY_QUERY_ATTEMPT002_AWAITING_STATIC_ADMISSION_AND_EXPLICIT_CONFIRMATION"

EXTERNAL_ROOT = Path(
    r"E:\UIT\cv\materialized-tools\hybrid-recsys-v5\stage1e\r6"
    r"\mxc_v0_7_0_rc1\attempt-001"
)
DATA_ROOT = Path(
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    r"\official_source\grouplens_ml100k\attempt-003"
)
ENV_ROOT = Path(
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-003"
)

ASSET_URL = (
    "https://github.com/microsoft/mxc/releases/download/"
    "v0.7.0-rc1/mxc-release-binaries.zip"
)
ASSET_FINAL_HOST = "release-assets.githubusercontent.com"
ASSET_BYTES = 180_948_670
ASSET_SHA256 = "450ad608bd2268a8cbe126597be209601c51fbfe36141cec08abb017e828aba5"
SOURCE_REPOSITORY = "https://github.com/microsoft/mxc"
SOURCE_TAG = "v0.7.0-rc1"
SOURCE_COMMIT = "0e02a720e32416b151dbcb0a00e3d4ac2b891559"

PROCESSMODEL_DLL = Path(r"C:\Windows\System32\processmodel.dll")
PROCESSMODEL_BYTES = 192_512
PROCESSMODEL_SHA256 = "7d18a80be826916e59ca1a49c692d8e59ab55a39c865dd664f469758b20177d5"
QUERY_EXPORT = "Experimental_QuerySandboxSupport"
CREATE_EXPORT = "Experimental_CreateProcessInSandbox"
QUERY_SIGNATURE = "unsafe extern system fn(capabilities: *mut u64) -> i32"
QUERY_SUCCESS_SEMANTICS = "NONZERO_BOOL_OUTPUT_MASK_VALID"
QUERY_FAILURE_SEMANTICS = "ZERO_BOOL_QUERY_FAILED_OUTPUT_MASK_INVALID"
CREATE_CAPABILITY_BIT = 0x1
LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800

PYTHON_EXE = Path(
    r"C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)
PYTHON_BYTES = 91_648
PYTHON_SHA256 = "d8e3f0adf246db00358c0c4ed349cf714898178f9558fb0e944f79f5c07f8eaa"
PYTHON_VERSION_INFO = (3, 12, 13, "final", 0)
PYTHON_IMPLEMENTATION = "CPython"
PYTHON_ARCHITECTURE_BITS = 64

GIT_EXE = Path(r"C:\Program Files\Git\mingw64\bin\git.exe")
GIT_BYTES = 4_238_224
GIT_SHA256 = "1f2ee2de971b6d0a7a13f053014998b66c22df47f30f1907a767346392eb8d78"
GIT_VERSION = "git version 2.50.0.windows.1"

EXPECTED_WINDOWS_MAJOR = 10
EXPECTED_WINDOWS_BUILD = 26_200
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
MAX_JSON_BYTES = 256 * 1024
MAX_PE_BYTES = 8 * 1024 * 1024

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INCOMPLETE = 2

REQUIRED_FROZEN_INPUTS = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_mxc_containment_feasibility_contract.md",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_runner_compatibility_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_future_agent_model_policy_standard.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_query_api_source_lock.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc0_initial_runner_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc0_query_preflight_attempt001_failure_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_query_only_v1_supersession_record.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/dataset_materialization_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/environment_materialization_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/recbole_dataset_bridge_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/execution_boundary_and_negative_assertions.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/audit_handoff.json",
}

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "created_at",
    "stage_id",
    "status",
    "recovery_checkpoint",
    "objective",
    "ars_workflow",
    "model_provenance",
    "runner",
    "frozen_inputs",
    "checkpoint_binding",
    "python_control",
    "git_control",
    "host_lock",
    "query_api",
    "source_candidate",
    "source_materialization",
    "roots",
    "modes",
    "execution_scope",
    "admission_logic",
    "exit_codes",
    "truth_state",
}


class GateFailure(RuntimeError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise GateFailure(f"DUPLICATE_JSON_KEY:{key}")
        casefolded = key.casefold()
        if casefolded in folded:
            raise GateFailure(f"CASE_COLLIDING_JSON_KEYS:{folded[casefolded]}:{key}")
        result[key] = value
        folded[casefolded] = key
    return result


def strict_load_json(path: Path) -> dict[str, Any]:
    require_ordinary_file(path, max_bytes=MAX_JSON_BYTES)
    payload = path.read_bytes()
    if payload.startswith(b"\xef\xbb\xbf"):
        raise GateFailure(f"UTF8_BOM_FORBIDDEN:{path}")
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                GateFailure(f"NONFINITE_JSON_NUMBER:{token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateFailure(f"INVALID_STRICT_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise GateFailure(f"JSON_ROOT_NOT_OBJECT:{path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"raw_bytes": len(payload), "raw_sha256": hashlib.sha256(payload).hexdigest()}


def is_reparse(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise GateFailure(f"LSTAT_FAILED:{path}:{exc}") from exc
    return bool(getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def require_ordinary_file(path: Path, *, max_bytes: int | None = None) -> None:
    if not path.is_file() or path.is_symlink() or is_reparse(path):
        raise GateFailure(f"ORDINARY_FILE_REQUIRED:{path}")
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise GateFailure(f"REGULAR_FILE_REQUIRED:{path}")
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise GateFailure(f"FILE_TOO_LARGE:{path}:{path.stat().st_size}")


def repository_path(relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not relative or "\\" in relative:
        raise GateFailure(f"INVALID_REPOSITORY_RELATIVE_PATH:{relative}")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise GateFailure(f"UNSAFE_REPOSITORY_RELATIVE_PATH:{relative}")
    absolute = Path(os.path.abspath(REPOSITORY_ROOT / candidate))
    if os.path.commonpath((str(REPOSITORY_ROOT), str(absolute))) != str(REPOSITORY_ROOT):
        raise GateFailure(f"REPOSITORY_PATH_ESCAPE:{relative}")
    require_ordinary_file(absolute)
    cursor = absolute.parent
    while cursor != REPOSITORY_ROOT:
        if cursor.is_symlink() or is_reparse(cursor):
            raise GateFailure(f"REPARSE_ANCESTOR_FORBIDDEN:{cursor}")
        cursor = cursor.parent
    if REPOSITORY_ROOT.is_symlink() or is_reparse(REPOSITORY_ROOT):
        raise GateFailure(f"REPOSITORY_ROOT_REPARSE_FORBIDDEN:{REPOSITORY_ROOT}")
    return absolute


def exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise GateFailure(
            f"SCHEMA_KEYS_MISMATCH:{label}:missing={sorted(expected - actual)}:"
            f"unexpected={sorted(actual - expected)}"
        )


def verify_checkpoint_argument(checkpoint: str) -> None:
    if len(checkpoint) != 40 or any(char not in "0123456789abcdef" for char in checkpoint):
        raise GateFailure(f"INVALID_EXACT_CHECKPOINT_ARGUMENT:{checkpoint}")


def verify_python_control_runtime() -> dict[str, Any]:
    expected = os.path.normcase(os.path.abspath(str(PYTHON_EXE)))
    observed = os.path.normcase(os.path.abspath(sys.executable))
    if observed != expected:
        raise GateFailure(f"PYTHON_EXECUTABLE_MISMATCH:{sys.executable}")
    require_ordinary_file(PYTHON_EXE)
    if fingerprint(PYTHON_EXE) != {
        "raw_bytes": PYTHON_BYTES,
        "raw_sha256": PYTHON_SHA256,
    }:
        raise GateFailure("PYTHON_EXECUTABLE_IDENTITY_MISMATCH")
    version_info = tuple(sys.version_info[:5])
    if version_info != PYTHON_VERSION_INFO:
        raise GateFailure(f"PYTHON_VERSION_MISMATCH:{version_info}")
    if platform.python_implementation() != PYTHON_IMPLEMENTATION:
        raise GateFailure("PYTHON_IMPLEMENTATION_MISMATCH")
    architecture_bits = struct.calcsize("P") * 8
    if architecture_bits != PYTHON_ARCHITECTURE_BITS:
        raise GateFailure(f"PYTHON_ARCHITECTURE_MISMATCH:{architecture_bits}")
    if sys.flags.isolated != 1 or sys.flags.dont_write_bytecode != 1:
        raise GateFailure(
            f"PYTHON_FLAGS_MISMATCH:isolated={sys.flags.isolated}:"
            f"dont_write_bytecode={sys.flags.dont_write_bytecode}"
        )
    return {
        "path": str(PYTHON_EXE),
        "version_info": list(version_info),
        "implementation": platform.python_implementation(),
        "architecture_bits": architecture_bits,
        "isolated": True,
        "dont_write_bytecode": True,
        **fingerprint(PYTHON_EXE),
    }


def git_run(arguments: list[str], *, allow_return_codes: set[int] | None = None) -> subprocess.CompletedProcess[bytes]:
    env = {
        "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
        "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
        "COMSPEC": os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"),
        "PATH": str(GIT_EXE.parent),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "NUL",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "core.untrackedCache",
        "GIT_CONFIG_VALUE_1": "false",
        "LC_ALL": "C",
    }
    command = [
        str(GIT_EXE),
        "--no-optional-locks",
        "--git-dir",
        str(REPOSITORY_ROOT / ".git"),
        "--work-tree",
        str(REPOSITORY_ROOT),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        *arguments,
    ]
    completed = subprocess.run(
        command,
        cwd=str(REPOSITORY_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        shell=False,
    )
    accepted = {0} if allow_return_codes is None else allow_return_codes
    if completed.returncode not in accepted:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GateFailure(
            f"FROZEN_GIT_COMMAND_FAILED:rc={completed.returncode}:args={arguments}:stderr={stderr}"
        )
    return completed


def verify_git_control(expected_head: str, tracked_paths: list[str]) -> dict[str, Any]:
    verify_checkpoint_argument(expected_head)
    require_ordinary_file(GIT_EXE)
    if fingerprint(GIT_EXE) != {"raw_bytes": GIT_BYTES, "raw_sha256": GIT_SHA256}:
        raise GateFailure("FROZEN_GIT_IDENTITY_MISMATCH")
    version = git_run(["--version"]).stdout.decode("ascii", errors="strict").strip()
    if version != GIT_VERSION:
        raise GateFailure(f"FROZEN_GIT_VERSION_MISMATCH:{version}")
    head = git_run(["rev-parse", "--verify", "HEAD^{commit}"]).stdout.decode("ascii").strip()
    if head != expected_head:
        raise GateFailure(f"EXACT_HEAD_MISMATCH:expected={expected_head}:observed={head}")
    ancestry = git_run(
        ["merge-base", "--is-ancestor", RECOVERY_CHECKPOINT, head],
        allow_return_codes={0, 1},
    )
    if ancestry.returncode != 0:
        raise GateFailure(f"RECOVERY_CHECKPOINT_NOT_ANCESTOR:{RECOVERY_CHECKPOINT}:{head}")
    status_output = git_run(
        ["status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    if status_output:
        raise GateFailure("WORKTREE_NOT_CLEAN_OR_UNTRACKED_FILES_PRESENT")
    verified: list[str] = []
    for relative in sorted(set(tracked_paths)):
        local = repository_path(relative).read_bytes()
        git_run(["ls-files", "--error-unmatch", "--", relative])
        blob = git_run(["show", f"HEAD:{relative}"]).stdout
        if blob != local:
            raise GateFailure(f"HEAD_BLOB_DIFFERS_FROM_WORKTREE:{relative}")
        verified.append(relative)
    return {
        "git_path": str(GIT_EXE),
        "git_version": version,
        "exact_head": head,
        "recovery_checkpoint_is_ancestor": True,
        "worktree_clean_including_untracked": True,
        "head_blob_paths_verified": verified,
    }


def verify_frozen_inputs(dispatch: dict[str, Any]) -> list[dict[str, Any]]:
    rows = dispatch.get("frozen_inputs")
    if not isinstance(rows, list) or len(rows) != 13:
        raise GateFailure("FROZEN_INPUT_COUNT_MUST_EQUAL_13")
    observed_paths: set[str] = set()
    verified: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise GateFailure(f"FROZEN_INPUT_ROW_NOT_OBJECT:{index}")
        exact_keys(row, {"path", "raw_bytes", "raw_sha256", "role"}, f"frozen_inputs[{index}]")
        relative = row["path"]
        if not isinstance(relative, str) or relative in observed_paths:
            raise GateFailure(f"INVALID_OR_DUPLICATE_FROZEN_INPUT_PATH:{relative}")
        path = repository_path(relative)
        observed = fingerprint(path)
        expected = {"raw_bytes": row["raw_bytes"], "raw_sha256": row["raw_sha256"]}
        if observed != expected:
            raise GateFailure(f"FROZEN_INPUT_FINGERPRINT_MISMATCH:{relative}")
        observed_paths.add(relative)
        verified.append({"path": relative, **observed})
    if observed_paths != REQUIRED_FROZEN_INPUTS:
        raise GateFailure(
            f"FROZEN_INPUT_SET_MISMATCH:missing={sorted(REQUIRED_FROZEN_INPUTS - observed_paths)}:"
            f"unexpected={sorted(observed_paths - REQUIRED_FROZEN_INPUTS)}"
        )
    return verified


def verify_dispatch() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dispatch = strict_load_json(DISPATCH_PATH)
    exact_keys(dispatch, EXPECTED_TOP_LEVEL_KEYS, "dispatch")
    if dispatch.get("schema_version") != "stage1e-e4-r6-pc0-query-attempt002-dispatch-1.0":
        raise GateFailure("DISPATCH_SCHEMA_VERSION_MISMATCH")
    if dispatch.get("stage_id") != STAGE_ID or dispatch.get("status") != STATUS:
        raise GateFailure("DISPATCH_STAGE_OR_STATUS_MISMATCH")
    if dispatch.get("recovery_checkpoint") != RECOVERY_CHECKPOINT:
        raise GateFailure("DISPATCH_RECOVERY_CHECKPOINT_MISMATCH")

    runner = dispatch.get("runner")
    if not isinstance(runner, dict):
        raise GateFailure("DISPATCH_RUNNER_NOT_OBJECT")
    exact_keys(runner, {"path", "raw_bytes", "raw_sha256", "role"}, "runner")
    expected_runner_path = RUNNER_PATH.relative_to(REPOSITORY_ROOT).as_posix()
    if runner.get("path") != expected_runner_path or fingerprint(RUNNER_PATH) != {
        "raw_bytes": runner.get("raw_bytes"),
        "raw_sha256": runner.get("raw_sha256"),
    }:
        raise GateFailure("RUNNER_IDENTITY_MISMATCH")

    checkpoint_binding = dispatch.get("checkpoint_binding")
    if checkpoint_binding != {
        "method": "CALLER_SUPPLIED_EXACT_40_HEX_MUST_EQUAL_RUNTIME_HEAD",
        "argument": "--checkpoint",
        "recovery_checkpoint_must_be_ancestor": RECOVERY_CHECKPOINT,
        "self_referential_head_embedded": False,
    }:
        raise GateFailure("DISPATCH_CHECKPOINT_BINDING_MISMATCH")

    if dispatch.get("python_control") != {
        "path": str(PYTHON_EXE),
        "raw_bytes": PYTHON_BYTES,
        "raw_sha256": PYTHON_SHA256,
        "version_info": list(PYTHON_VERSION_INFO),
        "implementation": PYTHON_IMPLEMENTATION,
        "architecture_bits": PYTHON_ARCHITECTURE_BITS,
        "required_flags": ["-I", "-B"],
    }:
        raise GateFailure("DISPATCH_PYTHON_CONTROL_MISMATCH")

    if dispatch.get("git_control") != {
        "path": str(GIT_EXE),
        "raw_bytes": GIT_BYTES,
        "raw_sha256": GIT_SHA256,
        "version": GIT_VERSION,
        "optional_locks": False,
        "ambient_environment": False,
        "system_and_global_config": False,
        "fsmonitor": False,
        "untracked_cache": False,
    }:
        raise GateFailure("DISPATCH_GIT_CONTROL_MISMATCH")

    if dispatch.get("host_lock") != {
        "platform": "Windows",
        "major": EXPECTED_WINDOWS_MAJOR,
        "build": EXPECTED_WINDOWS_BUILD,
        "elevation_required": False,
    }:
        raise GateFailure("DISPATCH_HOST_LOCK_MISMATCH")

    if dispatch.get("query_api") != {
        "dll": str(PROCESSMODEL_DLL),
        "dll_raw_bytes": PROCESSMODEL_BYTES,
        "dll_raw_sha256": PROCESSMODEL_SHA256,
        "query_export": QUERY_EXPORT,
        "create_export_guard_only": CREATE_EXPORT,
        "source_signature": QUERY_SIGNATURE,
        "success_semantics": QUERY_SUCCESS_SEMANTICS,
        "failure_semantics": QUERY_FAILURE_SEMANTICS,
        "restype": "ctypes.c_int32",
        "output_type": "ctypes.c_uint64",
        "create_process_capability_bit": CREATE_CAPABILITY_BIT,
        "call_count": 1,
        "fallback_create_call": False,
    }:
        raise GateFailure("DISPATCH_QUERY_API_MISMATCH")

    if dispatch.get("source_candidate") != {
        "repository": SOURCE_REPOSITORY,
        "tag": SOURCE_TAG,
        "commit": SOURCE_COMMIT,
        "asset_url": ASSET_URL,
        "observed_final_host": ASSET_FINAL_HOST,
        "asset_raw_bytes": ASSET_BYTES,
        "asset_raw_sha256": ASSET_SHA256,
    }:
        raise GateFailure("DISPATCH_SOURCE_CANDIDATE_MISMATCH")

    if dispatch.get("source_materialization") != {
        "status": "NOT_DOWNLOADED",
        "network_allowed": False,
        "write_allowed": False,
        "external_root_created": False,
    }:
        raise GateFailure("DISPATCH_SOURCE_MATERIALIZATION_MISMATCH")

    if dispatch.get("roots") != {
        "candidate_root": str(EXTERNAL_ROOT),
        "dataset_root_guard": str(DATA_ROOT),
        "environment_root_guard": str(ENV_ROOT),
        "parent_bootstrap_status": "PARENT_BOOTSTRAP_REQUIRED_BUT_NOT_AUTHORIZED",
    }:
        raise GateFailure("DISPATCH_ROOTS_MISMATCH")

    if dispatch.get("modes") != {
        "preflight": "READ_ONLY_QUERY_ONCE_NO_NETWORK_NO_WRITE",
        "materialize": "DENIED",
        "probe": "DENIED",
    }:
        raise GateFailure("DISPATCH_MODES_MISMATCH")

    if dispatch.get("execution_scope") != {
        "network": "NO_NETWORK_REQUESTED_NO_SYSTEM_WIDE_TRACE",
        "filesystem": "NO_WRITE_REQUESTED_POST_QUERY_CLOSURE_REQUIRED",
        "process_creation": "NO_CHILD_EXCEPT_FROZEN_GIT_READ_ONLY",
        "host_mutation": "DACL_FIREWALL_ELEVATION_HOST_PREP_FORBIDDEN",
        "scientific_execution": "TRAINING_EVALUATION_BENCHMARK_FORBIDDEN",
    }:
        raise GateFailure("DISPATCH_EXECUTION_SCOPE_MISMATCH")

    if dispatch.get("admission_logic") != {
        "bool_zero": "FAIL_QUERY_UNKNOWN_OUTPUT_INVALID",
        "bool_nonzero_bit_clear": "FAIL_HOST_CAPABILITY_ABSENT",
        "bool_nonzero_bit_set": "INCOMPLETE_POLICY_TEST_REQUIRED",
        "pass_reachable_in_this_runner_version": False,
    }:
        raise GateFailure("DISPATCH_ADMISSION_LOGIC_MISMATCH")

    if dispatch.get("exit_codes") != {
        "summary": "0=PASS;1=FAIL;2=INCOMPLETE",
        "pass": EXIT_PASS,
        "fail": EXIT_FAIL,
        "incomplete": EXIT_INCOMPLETE,
    }:
        raise GateFailure("DISPATCH_EXIT_CODES_MISMATCH")

    if dispatch.get("truth_state") != {
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
        "scientific_execution_performed": False,
        "benchmark_admitted": False,
    }:
        raise GateFailure("DISPATCH_TRUTH_STATE_MISMATCH")

    return dispatch, verify_frozen_inputs(dispatch)


def verify_host() -> dict[str, Any]:
    if platform.system() != "Windows" or os.name != "nt":
        raise GateFailure("WINDOWS_HOST_REQUIRED")
    version = sys.getwindowsversion()
    if version.major != EXPECTED_WINDOWS_MAJOR or version.build != EXPECTED_WINDOWS_BUILD:
        raise GateFailure(
            f"WINDOWS_BUILD_MISMATCH:{version.major}.{version.minor}.{version.build}"
        )
    return {
        "platform": platform.system(),
        "major": version.major,
        "minor": version.minor,
        "build": version.build,
        "elevation_requested": False,
    }


def verify_absent_roots_and_ancestry() -> dict[str, Any]:
    guarded = [EXTERNAL_ROOT, DATA_ROOT, ENV_ROOT]
    for path in guarded:
        if path.exists() or path.is_symlink():
            raise GateFailure(f"GUARDED_ROOT_MUST_BE_ABSENT:{path}")
    missing_chain: list[str] = []
    cursor = EXTERNAL_ROOT
    while not cursor.exists() and not cursor.is_symlink():
        missing_chain.append(str(cursor))
        parent = cursor.parent
        if parent == cursor:
            raise GateFailure("NO_EXISTING_ANCESTOR_FOR_EXTERNAL_ROOT")
        cursor = parent
    if cursor.is_symlink() or is_reparse(cursor) or not cursor.is_dir():
        raise GateFailure(f"NEAREST_EXISTING_ANCESTOR_NOT_ORDINARY_DIRECTORY:{cursor}")
    return {
        "guarded_roots_absent": [str(path) for path in guarded],
        "candidate_missing_chain": missing_chain,
        "nearest_existing_ancestor": str(cursor),
        "parent_bootstrap_status": "PARENT_BOOTSTRAP_REQUIRED_BUT_NOT_AUTHORIZED",
    }


def pe_exports(path: Path) -> set[str]:
    require_ordinary_file(path, max_bytes=MAX_PE_BYTES)
    payload = path.read_bytes()
    if len(payload) < 0x100 or payload[:2] != b"MZ":
        raise GateFailure("PROCESSMODEL_INVALID_DOS_HEADER")
    pe_offset = struct.unpack_from("<I", payload, 0x3C)[0]
    if pe_offset + 24 > len(payload) or payload[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise GateFailure("PROCESSMODEL_INVALID_PE_HEADER")
    file_header = pe_offset + 4
    section_count = struct.unpack_from("<H", payload, file_header + 2)[0]
    optional_size = struct.unpack_from("<H", payload, file_header + 16)[0]
    optional = file_header + 20
    if optional + optional_size > len(payload):
        raise GateFailure("PROCESSMODEL_TRUNCATED_OPTIONAL_HEADER")
    magic = struct.unpack_from("<H", payload, optional)[0]
    if magic == 0x20B:
        directory = optional + 112
    elif magic == 0x10B:
        directory = optional + 96
    else:
        raise GateFailure(f"PROCESSMODEL_UNSUPPORTED_PE_MAGIC:{magic:#x}")
    if directory + 8 > optional + optional_size:
        raise GateFailure("PROCESSMODEL_EXPORT_DIRECTORY_MISSING")
    export_rva, export_size = struct.unpack_from("<II", payload, directory)
    if export_rva == 0 or export_size == 0:
        raise GateFailure("PROCESSMODEL_NO_EXPORT_TABLE")
    section_table = optional + optional_size
    sections: list[tuple[int, int, int, int]] = []
    for index in range(section_count):
        offset = section_table + index * 40
        if offset + 40 > len(payload):
            raise GateFailure("PROCESSMODEL_TRUNCATED_SECTION_TABLE")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", payload, offset + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_offset, raw_size))

    def rva_offset(rva: int, length: int = 1) -> int:
        for virtual_address, span, raw_offset, raw_size in sections:
            if virtual_address <= rva < virtual_address + span:
                delta = rva - virtual_address
                if delta + length > raw_size or raw_offset + delta + length > len(payload):
                    raise GateFailure(f"PROCESSMODEL_RVA_OUTSIDE_RAW_SECTION:{rva:#x}")
                return raw_offset + delta
        raise GateFailure(f"PROCESSMODEL_RVA_UNMAPPED:{rva:#x}")

    export_offset = rva_offset(export_rva, 40)
    name_count = struct.unpack_from("<I", payload, export_offset + 24)[0]
    names_rva = struct.unpack_from("<I", payload, export_offset + 32)[0]
    if name_count == 0 or name_count > 65_536:
        raise GateFailure(f"PROCESSMODEL_EXPORT_NAME_COUNT_INVALID:{name_count}")
    names_offset = rva_offset(names_rva, name_count * 4)
    exports: set[str] = set()
    for index in range(name_count):
        name_rva = struct.unpack_from("<I", payload, names_offset + index * 4)[0]
        start = rva_offset(name_rva)
        end = payload.find(b"\0", start, min(len(payload), start + 512))
        if end < 0:
            raise GateFailure("PROCESSMODEL_UNTERMINATED_EXPORT_NAME")
        try:
            exports.add(payload[start:end].decode("ascii", errors="strict"))
        except UnicodeDecodeError as exc:
            raise GateFailure("PROCESSMODEL_NON_ASCII_EXPORT_NAME") from exc
    return exports


def verify_processmodel_identity_and_exports(path: Path = PROCESSMODEL_DLL) -> dict[str, Any]:
    observed = fingerprint(path)
    if observed != {"raw_bytes": PROCESSMODEL_BYTES, "raw_sha256": PROCESSMODEL_SHA256}:
        raise GateFailure("PROCESSMODEL_DLL_IDENTITY_MISMATCH")
    exports = pe_exports(path)
    required = {QUERY_EXPORT, CREATE_EXPORT}
    if not required.issubset(exports):
        raise GateFailure(f"PROCESSMODEL_REQUIRED_EXPORTS_MISSING:{sorted(required - exports)}")
    return {"dll": str(path), **observed, "required_exports_present": sorted(required)}


def loaded_module_path(module_handle: int) -> Path:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_module_filename = kernel32.GetModuleFileNameW
    get_module_filename.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar),
        ctypes.c_uint32,
    ]
    get_module_filename.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32_768)
    length = int(
        get_module_filename(
            ctypes.c_void_p(module_handle),
            buffer,
            ctypes.c_uint32(len(buffer)),
        )
    )
    if length == 0 or length >= len(buffer):
        raise GateFailure(f"GET_MODULE_FILENAME_FAILED:{ctypes.get_last_error()}")
    return Path(buffer.value)


def classify_query_result(bool_return: int, capability_mask: int | None) -> dict[str, Any]:
    if bool_return == 0:
        return {
            "classification": "QUERY_FAILURE_OUTPUT_MASK_INVALID",
            "exit_code": EXIT_FAIL,
            "capability_mask_valid": False,
            "create_process_capability_present": None,
        }
    mask = int(capability_mask)
    if mask & CREATE_CAPABILITY_BIT == 0:
        return {
            "classification": "FAIL_HOST_CAPABILITY_ABSENT",
            "exit_code": EXIT_FAIL,
            "capability_mask_valid": True,
            "create_process_capability_present": False,
        }
    return {
        "classification": "INCOMPLETE_POLICY_TEST_REQUIRED",
        "exit_code": EXIT_INCOMPLETE,
        "capability_mask_valid": True,
        "create_process_capability_present": True,
    }


def query_sandbox_support() -> dict[str, Any]:
    query_export = "Experimental_QuerySandboxSupport"
    if query_export != QUERY_EXPORT:
        raise GateFailure("QUERY_EXPORT_LITERAL_LOCK_MISMATCH")
    library = ctypes.WinDLL(str(PROCESSMODEL_DLL), winmode=LOAD_LIBRARY_SEARCH_SYSTEM32)
    actual_loaded_path = loaded_module_path(int(library._handle))
    expected = os.path.normcase(os.path.abspath(str(PROCESSMODEL_DLL)))
    observed = os.path.normcase(os.path.abspath(str(actual_loaded_path)))
    if observed != expected:
        raise GateFailure(f"PROCESSMODEL_LOADED_PATH_MISMATCH:{actual_loaded_path}")
    loaded_identity = verify_processmodel_identity_and_exports(actual_loaded_path)
    query = getattr(library, query_export)
    query.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    query.restype = ctypes.c_int32
    capabilities = ctypes.c_uint64(0)
    bool_return = int(query(ctypes.byref(capabilities)))
    if bool_return == 0:
        return {
            "query_export": query_export,
            "bool_return": bool_return,
            "capability_mask": None,
            "call_count": 1,
            "fallback_create_call": False,
            "loaded_module": loaded_identity,
        }
    capability_mask = int(capabilities.value)
    return {
        "query_export": query_export,
        "bool_return": bool_return,
        "capability_mask": capability_mask,
        "call_count": 1,
        "fallback_create_call": False,
        "loaded_module": loaded_identity,
    }


def post_query_closure(
    expected_head: str,
    tracked_paths: list[str],
    loaded_module: dict[str, Any],
) -> dict[str, Any]:
    git_state = verify_git_control(expected_head, tracked_paths)
    roots = verify_absent_roots_and_ancestry()
    dll = verify_processmodel_identity_and_exports(Path(loaded_module["dll"]))
    if dll != loaded_module:
        raise GateFailure("PROCESSMODEL_POST_QUERY_IDENTITY_CHANGED")
    return {
        "git_state": git_state,
        "roots": roots,
        "processmodel": dll,
        "network_trace_scope": "NO_SYSTEM_WIDE_TRACE_PERFORMED",
        "runner_network_request": False,
        "runner_filesystem_write_request": False,
    }


def emit(event: dict[str, Any]) -> None:
    print(json.dumps(event, ensure_ascii=True, sort_keys=True), flush=True)


def run_preflight(checkpoint: str) -> int:
    verify_checkpoint_argument(checkpoint)
    python_control = verify_python_control_runtime()
    dispatch, frozen = verify_dispatch()
    tracked_paths = [row["path"] for row in frozen]
    tracked_paths.extend(
        [
            RUNNER_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
            DISPATCH_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
        ]
    )
    git_before = verify_git_control(checkpoint, tracked_paths)
    host = verify_host()
    roots_before = verify_absent_roots_and_ancestry()
    processmodel_before = verify_processmodel_identity_and_exports()
    query = query_sandbox_support()
    closure = post_query_closure(checkpoint, tracked_paths, query["loaded_module"])
    classification = classify_query_result(query["bool_return"], query["capability_mask"])
    common = {
        "schema_version": "stage1e-e4-r6-pc0-query-attempt002-result-1.0",
        "stage_id": STAGE_ID,
        "mode": "preflight",
        "runner_status": STATUS,
        "exact_checkpoint": checkpoint,
        "dispatch_created_at": dispatch["created_at"],
        "python_control": python_control,
        "git_before": git_before,
        "host": host,
        "roots_before": roots_before,
        "processmodel_before": processmodel_before,
        "query": query,
        "post_query_closure": closure,
        "network_requested_by_runner": False,
        "filesystem_write_requested_by_runner": False,
        "system_wide_network_trace_performed": False,
        "child_process_scope": "FROZEN_GIT_READ_ONLY_ONLY",
        "source_materialized": False,
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
        "scientific_execution_performed": False,
        "benchmark_admitted": False,
    }
    if classification["classification"] == "QUERY_FAILURE_OUTPUT_MASK_INVALID":
        emit(
            {
                **common,
                "classification": classification,
                "result_status": "FAIL",
                "reason": "QUERY_SANDBOX_SUPPORT_BOOL_ZERO_OUTPUT_MASK_INVALID",
                "next_gate": "QUERY_FAILURE_NO_CANDIDATE_ADMISSION_OR_REJECTION",
            }
        )
        return EXIT_FAIL
    if classification["classification"] == "FAIL_HOST_CAPABILITY_ABSENT":
        emit(
            {
                **common,
                "classification": classification,
                "result_status": "FAIL",
                "reason": "CREATE_PROCESS_IN_SANDBOX_CAPABILITY_BIT_CLEAR",
                "next_gate": "REJECT_MXC_CANDIDATE_OR_CHANGE_HOST",
            }
        )
        return EXIT_FAIL
    emit(
        {
            **common,
            "classification": classification,
            "result_status": "INCOMPLETE",
            "reason": "POLICY_TEST_REQUIRED",
            "next_gate": "SEPARATE_PC1_TOY_CONTAINMENT_AUTHORITY_REQUIRED",
        }
    )
    return EXIT_INCOMPLETE


def run_materialize() -> int:
    emit(
        {
            "stage_id": STAGE_ID,
            "mode": "materialize",
            "result_status": "DENIED",
            "reason": "MATERIALIZE_DENIED_IN_QUERY_ONLY_ATTEMPT002",
        }
    )
    return EXIT_FAIL


def run_probe() -> int:
    emit(
        {
            "stage_id": STAGE_ID,
            "mode": "probe",
            "result_status": "DENIED",
            "reason": "DOWNLOADED_PROBE_DENIED_IN_QUERY_ONLY_ATTEMPT002",
        }
    )
    return EXIT_FAIL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="R6-PC0 attempt-002 read-only MXC capability query; no network and no write"
    )
    parser.add_argument("mode", choices=("preflight", "materialize", "probe"))
    parser.add_argument("--checkpoint", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "preflight":
            return run_preflight(args.checkpoint)
        if args.mode == "materialize":
            return run_materialize()
        return run_probe()
    except Exception as exc:
        emit(
            {
                "schema_version": "stage1e-e4-r6-pc0-query-attempt002-failure-1.0",
                "stage_id": STAGE_ID,
                "mode": args.mode,
                "exact_checkpoint_argument": args.checkpoint,
                "result_status": "FAIL",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "network_requested_by_runner": False,
                "filesystem_write_requested_by_runner": False,
                "system_wide_network_trace_performed": False,
                "test_set_opened": "NO",
                "accepted_result_rows": 0,
                "scientific_execution_performed": False,
                "benchmark_admitted": False,
            }
        )
        return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
