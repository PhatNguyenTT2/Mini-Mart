"""Role-bound Windows subprocess admission and bounded child-error custody."""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO

import psutil  # type: ignore[import-untyped]

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import sha256_file
from ai_service_v2.training.cost_profile_runtime import require_equal, structured_error
from ai_service_v2.training.cost_runtime_custody import (
    read_canonical_json,
    reject_reparse_path,
    write_exclusive_json,
)

STREAM_LIMIT = 65536
ROLES = {"supervisor", "worker", "cold-red", "cold-green"}
KNOWN_PROCESS_ERRORS = {
    "PROFILE_BASE_INTERPRETER_UNRESOLVED",
    "PROFILE_PROCESS_IDENTITY_INVALID",
    "PROFILE_PROCESS_DESCRIPTOR_SHAPE",
    "PROFILE_PROCESS_COMMAND_OR_RUNTIME_DRIFT",
    "PROFILE_PROCESS_IDENTITY_DRIFT",
    "PROFILE_PROCESS_COMMAND_DRIFT",
    "PROFILE_WRAPPER_TOPOLOGY_INVALID",
    "PROFILE_WRAPPER_COMMAND_DRIFT",
    "PROFILE_RUNTIME_PROCESS_INVALID",
    "PROFILE_DIRECT_PARENT_DRIFT",
    "PROFILE_PARENT_IDENTITY_DRIFT",
    "PROFILE_PROCESS_HANDSHAKE_TIMEOUT",
    "PROFILE_CHILD_GUARD_SHAPE",
    "PROFILE_CHILD_ADMISSION_BINDING",
    "PROFILE_ROLE_COMMAND_MISMATCH",
    "PROFILE_CHILD_ROLE_INVALID",
}


def process_error(error: Exception) -> dict[str, Any]:
    result = structured_error(error)
    if isinstance(error, IntegrityError) and str(error) in KNOWN_PROCESS_ERRORS:
        result["code"] = str(error)
        result["message"] = str(error)
    return result


def base_executable() -> Path:
    value = vars(sys).get("_base_executable")
    if not isinstance(value, str):
        raise IntegrityError("PROFILE_BASE_INTERPRETER_UNRESOLVED")
    return Path(value).resolve()


def process_identity(process: Any) -> dict[str, Any]:
    return {
        "pid": process.pid,
        "creation_time_100ns": int(process.create_time() * 10_000_000),
        "executable": str(Path(process.exe()).resolve()),
    }


def validate_identity(identity: dict[str, Any]) -> None:
    if (
        set(identity) != {"pid", "creation_time_100ns", "executable"}
        or type(identity["pid"]) is not int
        or identity["pid"] <= 0
        or type(identity["creation_time_100ns"]) is not int
        or identity["creation_time_100ns"] <= 0
        or not isinstance(identity["executable"], str)
        or str(Path(identity["executable"]).resolve()) != identity["executable"]
    ):
        raise IntegrityError("PROFILE_PROCESS_IDENTITY_INVALID")


def spawn_descriptor(pid: int, command: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "mp2-cost-role-process/1.0",
        "spawned": process_identity(psutil.Process(pid)),
        "parent": process_identity(psutil.Process()),
        "command": command,
        "launcher_executable": str(Path(command[0]).resolve()),
        "base_executable": str(base_executable()),
        "telemetry_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
    }


class _JobLimits(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_longlong),
        ("job_time", ctypes.c_longlong),
        ("flags", wintypes.DWORD),
        ("minimum_working_set", ctypes.c_size_t),
        ("maximum_working_set", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class _ExtendedJobLimits(ctypes.Structure):
    _fields_ = [
        ("basic", _JobLimits),
        ("io_counters", ctypes.c_ulonglong * 6),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


class _JobAccounting(ctypes.Structure):
    _fields_ = [
        ("user_time", ctypes.c_longlong),
        ("kernel_time", ctypes.c_longlong),
        ("period_user_time", ctypes.c_longlong),
        ("period_kernel_time", ctypes.c_longlong),
        ("page_faults", wintypes.DWORD),
        ("total_processes", wintypes.DWORD),
        ("active_processes", wintypes.DWORD),
        ("terminated_processes", wintypes.DWORD),
    ]


class _GeneratedProcessTree:
    """Kernel membership includes late descendants, not just sampled PIDs."""

    def __init__(self, *, terminate_on_owner_exit: bool = False) -> None:
        if type(terminate_on_owner_exit) is not bool:
            raise IntegrityError("GENERATED_PROCESS_OWNER_EXIT_POLICY_INVALID")
        if os.name != "nt":
            raise IntegrityError("GENERATED_PROCESS_WINDOWS_JOB_REQUIRED")
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "DebugActiveProcessStop": ([wintypes.DWORD], wintypes.BOOL),
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "SetInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "QueryInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p],
                wintypes.BOOL,
            ),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _JobLimits()
        limits.flags = 8 | (0x2000 if terminate_on_owner_exit else 0)
        limits.active_process_limit = 8
        # Direct scientific jobs die with their noninherited supervisor handle.
        extended = _ExtendedJobLimits()
        extended.basic = limits
        information = extended if terminate_on_owner_exit else limits
        if not self.api.SetInformationJobObject(
            self.handle,
            9 if terminate_on_owner_exit else 2,
            ctypes.byref(information),
            ctypes.sizeof(information),
        ):
            error = ctypes.WinError(ctypes.get_last_error())
            self.api.CloseHandle(self.handle)
            raise error

    def assign_suspended(self, pid: int) -> None:
        process_handle = self.api.OpenProcess(0x100 | 0x1, False, pid)
        if not process_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process_handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(process_handle)

    def snapshot(self) -> dict[str, Any]:
        observation = _JobAccounting()
        if not self.api.QueryInformationJobObject(
            self.handle, 1, ctypes.byref(observation), ctypes.sizeof(observation), None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return {
            "containment": "WINDOWS_JOB_BEFORE_FIRST_INSTRUCTION",
            "active_processes": int(observation.active_processes),
            "total_processes": int(observation.total_processes),
            "terminated_processes": int(observation.terminated_processes),
            "active_process_limit": 8,
        }

    def release_creation_debugger(self, pid: int) -> None:
        """Detach only after Job assignment replaces creation-time crash protection."""
        if not self.api.DebugActiveProcessStop(pid):
            raise ctypes.WinError(ctypes.get_last_error())

    def wait_empty(self, deadline_ns: int) -> dict[str, Any]:
        while True:
            observation = self.snapshot()
            if not observation["active_processes"]:
                return observation
            if time.monotonic_ns() >= deadline_ns:
                raise IntegrityError("GENERATED_PROCESS_DEADLINE_EXPIRED")
            time.sleep(0.01)

    def terminate_at_deadline(self) -> None:
        if not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        self.wait_empty(time.monotonic_ns() + 5_000_000_000)

    def close_if_empty(self) -> None:
        if not self.snapshot()["active_processes"]:
            if not self.api.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())


class GeneratedProcessDeadline:
    """External deadline for a bound generated child and observed descendants.

    No control I/O runs on the watchdog thread. This does not certify complete
    process-tree coverage, stream EOF, or invocation acceptance.
    """

    def __init__(
        self,
        *,
        authority: Path,
        guard: Path,
        descriptor: dict[str, Any],
        process_tree: _GeneratedProcessTree | None = None,
    ) -> None:
        document = read_canonical_json(authority)
        claim = read_canonical_json(guard)
        policy = document.get("native_invocation_deadline")
        command = document.get("native_supervised_command")
        if (
            document.get("scientific_execution_authorized") is not False
            or type(policy) is not dict
            or policy
            != {
                "route": "GENERATED_REHEARSAL",
                "limit_seconds": 7200,
                "clock": "MONOTONIC_NS_FROM_DURABLE_CLAIM",
            }
            or type(policy.get("limit_seconds")) is not int
            or type(command) is not list
            or not command
            or any(type(argument) is not str for argument in command)
            or claim.get("authority_sha256") != sha256_file(authority)
            or claim.get("automatic_retry") is not False
            or type(claim.get("claim_monotonic_ns")) is not int
            or not 0 < claim["claim_monotonic_ns"] <= time.monotonic_ns()
            or descriptor.get("command") != command
        ):
            raise IntegrityError("GENERATED_PROCESS_AUTHORITY_BINDING")
        validate_identity(descriptor["spawned"])
        validate_identity(descriptor["parent"])
        root = psutil.Process(descriptor["spawned"]["pid"])
        if (
            descriptor["parent"] != process_identity(psutil.Process())
            or root.ppid() != os.getpid()
            or process_identity(root) != descriptor["spawned"]
            or root.cmdline() != command
            or descriptor.get("launcher_executable") != str(Path(sys.executable).resolve())
            or descriptor.get("base_executable") != str(base_executable())
        ):
            raise IntegrityError("GENERATED_PROCESS_OWNERSHIP_BINDING")
        children = root.children(recursive=True)
        if len(children) > 8:
            raise IntegrityError("GENERATED_PROCESS_TREE_BOUND")
        self._root = root
        self._process_tree = process_tree
        self._owned = [(child, process_identity(child)) for child in children]
        self._owned.insert(0, (root, descriptor["spawned"]))
        self._deadline_ns = claim["claim_monotonic_ns"] + 7200000000000
        self._stop = threading.Event()
        self._finished = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self.expired = False
        self.termination_error: str | None = None

    def __enter__(self) -> GeneratedProcessDeadline:
        self._thread.start()
        return self

    def wait_for_expiry(self, timeout: float) -> bool:
        return self._finished.wait(timeout) and self.expired

    def _watch(self) -> None:
        while True:
            remaining_ns = self._deadline_ns - time.monotonic_ns()
            if remaining_ns <= 0:
                break
            if self._stop.wait(remaining_ns / 1e9):
                return
        self.expired = True
        try:
            if self._process_tree is not None:
                self._process_tree.terminate_at_deadline()
            if self._root.is_running():
                known = {identity["pid"] for _, identity in self._owned}
                for child in self._root.children(recursive=True):
                    if child.pid not in known:
                        self._owned.append((child, process_identity(child)))
            for child, identity in reversed(self._owned):
                try:
                    if child.is_running():
                        if process_identity(child) != identity:
                            raise IntegrityError("GENERATED_PROCESS_TIMEOUT_IDENTITY_DRIFT")
                        child.kill()
                except psutil.NoSuchProcess:
                    continue
            psutil.wait_procs([child for child, _ in self._owned], timeout=5)
            if any(child.is_running() for child, _ in self._owned):
                raise IntegrityError("GENERATED_PROCESS_TIMEOUT_EXIT_UNOBSERVED")
        except Exception as error:
            self.termination_error = str(error)
        finally:
            self._finished.set()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self.expired and time.monotonic_ns() >= self._deadline_ns:
            self._finished.wait(6)
        if self.expired:
            self._finished.wait(6)
            raise IntegrityError("GENERATED_PROCESS_DEADLINE_EXPIRED")
        if any(child.is_running() for child, _ in self._owned):
            # Do not disarm or kill early on a terminal-publication error.
            raise IntegrityError("GENERATED_PROCESS_TERMINAL_TAIL_STILL_ACTIVE")
        if self._process_tree is not None and self._process_tree.snapshot()["active_processes"]:
            raise IntegrityError("GENERATED_PROCESS_TERMINAL_TREE_STILL_ACTIVE")
        self._stop.set()
        self._thread.join(timeout=1)
        if self._thread.is_alive():
            raise IntegrityError("GENERATED_PROCESS_WATCHDOG_STOP_UNOBSERVED")


def resolve_owned_process(
    descriptor: dict[str, Any], command: list[str], *, check_parent: bool = True
) -> dict[str, Any]:
    if set(descriptor) != {
        "schema_version",
        "spawned",
        "parent",
        "command",
        "launcher_executable",
        "base_executable",
        "telemetry_authority",
    }:
        raise IntegrityError("PROFILE_PROCESS_DESCRIPTOR_SHAPE")
    for field, expected in {
        "schema_version": "mp2-cost-role-process/1.0",
        "command": command,
        "launcher_executable": str(Path(sys.executable).resolve()),
        "base_executable": str(base_executable()),
        "telemetry_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
    }.items():
        require_equal(descriptor[field], expected, "PROFILE_PROCESS_COMMAND_OR_RUNTIME_DRIFT")
    validate_identity(descriptor["spawned"])
    validate_identity(descriptor["parent"])
    current = psutil.Process()
    spawned = current if current.pid == descriptor["spawned"]["pid"] else current.parent()
    if spawned is None:
        raise IntegrityError("PROFILE_PROCESS_IDENTITY_DRIFT")
    require_equal(
        process_identity(spawned), descriptor["spawned"], "PROFILE_PROCESS_IDENTITY_DRIFT"
    )
    require_equal(list(spawned.cmdline()), command, "PROFILE_PROCESS_COMMAND_DRIFT")
    if spawned.pid != current.pid:
        if (
            process_identity(spawned)["executable"] != descriptor["launcher_executable"]
            or process_identity(current)["executable"] != descriptor["base_executable"]
        ):
            raise IntegrityError("PROFILE_WRAPPER_TOPOLOGY_INVALID")
        require_equal(
            list(current.cmdline()),
            [descriptor["base_executable"], *command[1:]],
            "PROFILE_WRAPPER_COMMAND_DRIFT",
        )
    elif process_identity(current)["executable"] not in {
        descriptor["launcher_executable"],
        descriptor["base_executable"],
    }:
        raise IntegrityError("PROFILE_RUNTIME_PROCESS_INVALID")
    if spawned.ppid() != descriptor["parent"]["pid"]:
        raise IntegrityError("PROFILE_DIRECT_PARENT_DRIFT")
    if check_parent:
        require_equal(
            process_identity(psutil.Process(spawned.ppid())),
            descriptor["parent"],
            "PROFILE_PARENT_IDENTITY_DRIFT",
        )
    return process_identity(current)


def await_document(path: Path, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() >= deadline:
            raise IntegrityError("PROFILE_PROCESS_HANDSHAKE_TIMEOUT")
        time.sleep(0.01)
    # A partial write is terminal, not retried or repaired.
    return read_canonical_json(path)


def admit_child(root: Path, role: str, authority: str, invocation: str) -> dict[str, Any]:
    if role not in ROLES:
        raise IntegrityError("PROFILE_CHILD_ROLE_INVALID")
    case_root = root / "children" / role
    try:
        launch = read_canonical_json(case_root / "launch_guard.json")
        if set(launch) != {
            "schema_version",
            "role",
            "authority_sha256",
            "invocation_guard_sha256",
            "command",
            "automatic_retry",
        }:
            raise IntegrityError("PROFILE_CHILD_GUARD_SHAPE")
        require_equal(
            launch,
            {
                "schema_version": "mp2-cost-child-launch/1.0",
                "role": role,
                "authority_sha256": authority,
                "invocation_guard_sha256": invocation,
                "command": launch["command"],
                "automatic_retry": False,
            },
            "PROFILE_CHILD_ADMISSION_BINDING",
        )
        descriptor = await_document(case_root / "spawned_identity.json")
        current = resolve_owned_process(descriptor, launch["command"])
        result = {
            "schema_version": "mp2-cost-child-admission/1.0",
            "role": role,
            "launch_guard_sha256": sha256_file(case_root / "launch_guard.json"),
            "spawned_identity_sha256": sha256_file(case_root / "spawned_identity.json"),
            "runtime_identity": current,
            "state": "ADMITTED",
            "telemetry_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
        }
        write_exclusive_json(case_root / "admission.json", result)
        return result
    except Exception as error:
        write_exclusive_json(
            case_root / "admission_failure.json",
            {
                "schema_version": "mp2-cost-child-admission-failure/1.0",
                "role": role,
                "stage": "CHILD_ADMISSION",
                "error": process_error(error),
                "workload_entered": False,
                "state": "FAILED_TERMINAL_NO_RETRY",
            },
        )
        raise


class BoundedStream:
    def __init__(self) -> None:
        self.digest = hashlib.sha256()
        self.count = 0
        self.payload = bytearray()
        self.error = False

    def read(self, stream: BinaryIO) -> None:
        try:
            while block := stream.read(4096):
                self.digest.update(block)
                self.count += len(block)
                if len(self.payload) < STREAM_LIMIT:
                    self.payload.extend(block[: STREAM_LIMIT - len(self.payload)])
        except OSError:
            self.error = True
        finally:
            stream.close()

    def observation(self) -> dict[str, Any]:
        return {
            "bytes": self.count,
            "sha256": self.digest.hexdigest(),
            "overflow": self.count > STREAM_LIMIT,
            "read_error": self.error,
            "content_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
        }


def run_bounded_generated_child(publisher: Any) -> dict[str, Any]:
    """Observe one stdin-released generated child with bounded control custody.

    The command must wait for byte 1 before entering its workload. This process
    observation is not an authority, a sandbox, or complete invocation acceptance.
    """
    from ai_service_v2.training import cost_bounded_io_01 as bounded

    if type(publisher) is not bounded.BoundedControlPublisher:
        raise IntegrityError("GENERATED_PROCESS_BOUNDED_PUBLISHER_REQUIRED")
    publisher._authenticate()
    authority = read_canonical_json(publisher.authority)
    guard_path = publisher.namespace / "invocation_guard.json"
    claim = read_canonical_json(guard_path)
    command = authority.get("native_supervised_command")
    expected_sources = [
        {"path": str(path), "sha256": sha256_file(path)}
        for path in (Path(__file__), Path(bounded.__file__))
    ]
    policy = authority.get("native_invocation_deadline")
    if (
        authority.get("native_process_source_bindings") != expected_sources
        or authority.get("scientific_execution_authorized") is not False
        or type(command) is not list
        or len(command) < 3
        or any(type(argument) is not str for argument in command)
        or command[:2] != [sys.executable, "-B"]
        or type(policy) is not dict
        or policy
        != {
            "route": "GENERATED_REHEARSAL",
            "limit_seconds": 7200,
            "clock": "MONOTONIC_NS_FROM_DURABLE_CLAIM",
        }
        or type(policy.get("limit_seconds")) is not int
        or type(claim.get("claim_monotonic_ns")) is not int
        or not 0 < claim["claim_monotonic_ns"] <= time.monotonic_ns()
    ):
        raise IntegrityError("GENERATED_PROCESS_PRECLAIM_BINDING")
    names = tuple(
        f"children/worker/{name}.json" for name in ("launch_guard", "spawned_identity", "outcome")
    )
    if any(name not in publisher.roster or (publisher.namespace / name).exists() for name in names):
        raise IntegrityError("GENERATED_PROCESS_FIXED_UNUSED_CONTROL_ROSTER_REQUIRED")
    deadline_ns = claim["claim_monotonic_ns"] + 7200000000000

    def remaining_seconds() -> float:
        remaining = (deadline_ns - time.monotonic_ns()) / 1e9
        if remaining <= 0:
            raise IntegrityError("GENERATED_PROCESS_DEADLINE_EXPIRED")
        return float(remaining)

    remaining_seconds()
    publisher.write_json(
        names[0],
        {
            "schema_version": "mp2-cost-child-launch/1.0",
            "role": "worker",
            "authority_sha256": publisher.authority_sha256,
            "invocation_guard_sha256": sha256_file(guard_path),
            "command": command,
            "automatic_retry": False,
        },
    )
    environment = dict(os.environ)
    environment.update(
        PYTHONDONTWRITEBYTECODE="1", TEMP=str(publisher.namespace), TMP=str(publisher.namespace)
    )
    process_tree = _GeneratedProcessTree()
    child = subprocess.Popen(
        command,
        cwd=publisher.namespace,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW | 0x4,
    )
    streams = [BoundedStream(), BoundedStream()]
    threads: list[threading.Thread] = []
    resumed = False
    try:
        process_tree.assign_suspended(child.pid)
        descriptor = spawn_descriptor(child.pid, command)
        with GeneratedProcessDeadline(
            authority=publisher.authority,
            guard=guard_path,
            descriptor=descriptor,
            process_tree=process_tree,
        ):
            try:
                publisher.write_json(names[1], descriptor)
                assert child.stdout is not None and child.stderr is not None
                assert child.stdin is not None
                for sink, pipe in zip(streams, (child.stdout, child.stderr), strict=True):
                    thread = threading.Thread(target=sink.read, args=(pipe,), daemon=True)
                    thread.start()
                    threads.append(thread)
                psutil.Process(child.pid).resume()
                resumed = True
                child.stdin.write(b"1")
                child.stdin.flush()
                child.stdin.close()
                code = child.wait(timeout=remaining_seconds())
                for thread in threads:
                    thread.join(timeout=remaining_seconds())
                eof = all(not thread.is_alive() for thread in threads)
                observations = [stream.observation() for stream in streams]
                observations[1]["diagnostic_prefix"] = {
                    "hex": bytes(streams[1].payload[:4096]).hex(),
                    "limit_bytes": 4096,
                    "truncated": streams[1].count > 4096,
                }
                tree_observation = process_tree.wait_empty(deadline_ns)
                if expected_sources != [
                    {"path": row["path"], "sha256": sha256_file(Path(row["path"]))}
                    for row in expected_sources
                ]:
                    raise IntegrityError("GENERATED_PROCESS_SOURCE_DRIFT")
                report = {
                    "schema_version": "mp2-cost-child-outcome/1.0",
                    "state": "GENERATED_PROCESS_OBSERVATION_NOT_INVOCATION_ACCEPTANCE",
                    "authority_sha256": publisher.authority_sha256,
                    "guard_sha256": sha256_file(guard_path),
                    "descriptor_sha256": sha256_file(publisher.namespace / names[1]),
                    "exit_code": code,
                    "streams_eof": eof,
                    "process_tree": tree_observation,
                    "stdout": observations[0],
                    "stderr": observations[1],
                    "process_observation_pass": code == 0
                    and eof
                    and observations[1]["bytes"] == 0
                    and not any(row["overflow"] or row["read_error"] for row in observations),
                    "invocation_terminal_qualified": False,
                    "scientific_execution_authorized": False,
                }
                publisher.write_json(names[2], report)
                remaining_seconds()
                return report
            finally:
                # An unreleased worker sees EOF, not admission; no kill/retry.
                if child.stdin is not None and not child.stdin.closed:
                    child.stdin.close()
                if not resumed and child.poll() is None:
                    psutil.Process(child.pid).resume()
                    resumed = True
                if child.poll() is None:
                    child.wait(timeout=remaining_seconds())
    finally:
        if child.stdin is not None and not child.stdin.closed:
            child.stdin.close()
        if not resumed and child.poll() is None:
            # Rejected before release: resume to observe EOF, never send byte1.
            psutil.Process(child.pid).resume()
        if child.poll() is None:
            child.wait(timeout=max(0.001, (deadline_ns - time.monotonic_ns()) / 1e9) + 6)
        for thread in threads:
            thread.join(timeout=1)
        if not threads:
            for unused_pipe in (child.stdout, child.stderr):
                if unused_pipe is not None:
                    unused_pipe.close()
        process_tree.close_if_empty()


def prepare_child(
    root: Path, role: str, command: list[str], authority: str, invocation: str
) -> Path:
    if role not in ROLES:
        raise IntegrityError("PROFILE_CHILD_ROLE_INVALID")
    reject_reparse_path(root)
    children = root / "children"
    children.mkdir(exist_ok=True)
    case_root = children / role
    case_root.mkdir()
    write_exclusive_json(
        case_root / "launch_guard.json",
        {
            "schema_version": "mp2-cost-child-launch/1.0",
            "role": role,
            "authority_sha256": authority,
            "invocation_guard_sha256": invocation,
            "command": command,
            "automatic_retry": False,
        },
    )
    return case_root


def run_child(
    root: Path,
    role: str,
    command: list[str],
    authority: str,
    invocation: str,
    *,
    timeout: float,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    if role not in ROLES or timeout <= 0:
        raise IntegrityError("PROFILE_CHILD_ROLE_OR_DEADLINE_INVALID")
    case_root = prepare_child(root, role, command, authority, invocation)
    started = time.monotonic()
    streams = [BoundedStream(), BoundedStream()]
    threads: list[threading.Thread] = []
    child: subprocess.Popen[bytes] | None = None
    timed_out = False
    exception: dict[str, Any] | None = None
    stage = "CHILD_LAUNCH"
    try:
        child = subprocess.Popen(
            command,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        descriptor = spawn_descriptor(child.pid, command)
        write_exclusive_json(case_root / "spawned_identity.json", descriptor)
        assert child.stdout is not None and child.stderr is not None
        for sink, pipe in zip(streams, (child.stdout, child.stderr), strict=True):
            thread = threading.Thread(target=sink.read, args=(pipe,), daemon=True)
            thread.start()
            threads.append(thread)
        stage = "CHILD_EXECUTION"
        child.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
    except subprocess.TimeoutExpired as error:
        timed_out = True
        exception = structured_error(error)
        stage = "CHILD_TIMEOUT"
        if child is not None:
            # Only this descriptor-bound spawned tree may be killed, at deadline.
            require_equal(
                process_identity(psutil.Process(child.pid)),
                descriptor["spawned"],
                "PROFILE_TIMEOUT_PROCESS_IDENTITY_DRIFT",
            )
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                check=True,
                capture_output=True,
                timeout=30,
            )
            child.wait(timeout=30)
    except Exception as error:
        exception = structured_error(error)
        # Admission/persistence ambiguity does not permit an early kill or restart.
        if child is not None and child.poll() is None:
            try:
                child.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                timed_out = True
                if "descriptor" not in locals():
                    raise IntegrityError("PROFILE_CHILD_OWNERSHIP_UNRESOLVED") from error
                require_equal(
                    process_identity(psutil.Process(child.pid)),
                    descriptor["spawned"],
                    "PROFILE_TIMEOUT_PROCESS_IDENTITY_DRIFT",
                )
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                child.wait(timeout=30)
    for thread in threads:
        thread.join(timeout=5)
    incomplete = any(thread.is_alive() for thread in threads)
    outcome = {
        "schema_version": "mp2-cost-child-outcome/1.0",
        "role": role,
        "launch_guard_sha256": sha256_file(case_root / "launch_guard.json"),
        "spawned_identity_sha256": sha256_file(case_root / "spawned_identity.json")
        if (case_root / "spawned_identity.json").is_file()
        else None,
        "admission_sha256": sha256_file(case_root / "admission.json")
        if (case_root / "admission.json").is_file()
        else None,
        "admission_failure_sha256": sha256_file(case_root / "admission_failure.json")
        if (case_root / "admission_failure.json").is_file()
        else None,
        "returncode": None if child is None else child.poll(),
        "stage": stage,
        "timed_out": timed_out,
        "exception": exception,
        "stdout": streams[0].observation(),
        "stderr": streams[1].observation(),
        "reader_incomplete": incomplete,
        "state": "CHILD_RETURNED" if exception is None else "FAILED_TERMINAL_NO_RETRY",
    }
    write_exclusive_json(case_root / "outcome.json", outcome)
    # The publication marker is last: readable outcome bytes alone are not custody.
    staged = case_root / "outcome_authority.staged.json"
    write_exclusive_json(
        staged,
        {
            "schema_version": "mp2-cost-child-outcome-authority/1.0",
            "outcome_sha256": sha256_file(case_root / "outcome.json"),
            "outcome_bytes": (case_root / "outcome.json").stat().st_size,
            "launch_guard_sha256": sha256_file(case_root / "launch_guard.json"),
            "scope": "PERSISTED_READBACK_OUTCOME_NOT_SUCCESS_VERDICT",
        },
    )
    os.link(staged, case_root / "outcome_authority.json")
    replay_child(root, role, authority, invocation)
    return {
        "returncode": outcome["returncode"],
        "outcome": outcome,
        "stdout_text": bytes(streams[0].payload).decode("utf-8", errors="strict"),
    }


def replay_child(root: Path, role: str, authority: str, invocation: str) -> dict[str, Any]:
    case_root = root / "children" / role
    launch = read_canonical_json(case_root / "launch_guard.json")
    require_equal(
        launch,
        {
            "schema_version": "mp2-cost-child-launch/1.0",
            "role": role,
            "authority_sha256": authority,
            "invocation_guard_sha256": invocation,
            "command": launch.get("command"),
            "automatic_retry": False,
        },
        "PROFILE_CHILD_GUARD_REPLAY",
    )
    require_equal(launch["role"], role, "PROFILE_CHILD_ROLE_DRIFT")
    require_equal(launch["authority_sha256"], authority, "PROFILE_CHILD_AUTHORITY_DRIFT")
    require_equal(launch["invocation_guard_sha256"], invocation, "PROFILE_CHILD_INVOCATION_DRIFT")
    outcome = read_canonical_json(case_root / "outcome.json")
    require_equal(
        read_canonical_json(case_root / "outcome_authority.json"),
        {
            "schema_version": "mp2-cost-child-outcome-authority/1.0",
            "outcome_sha256": sha256_file(case_root / "outcome.json"),
            "outcome_bytes": (case_root / "outcome.json").stat().st_size,
            "launch_guard_sha256": sha256_file(case_root / "launch_guard.json"),
            "scope": "PERSISTED_READBACK_OUTCOME_NOT_SUCCESS_VERDICT",
        },
        "PROFILE_CHILD_COMPLETION_READBACK_AUTHORITY_REQUIRED",
    )
    if (
        set(outcome)
        != {
            "schema_version",
            "role",
            "launch_guard_sha256",
            "spawned_identity_sha256",
            "admission_sha256",
            "admission_failure_sha256",
            "returncode",
            "stage",
            "timed_out",
            "exception",
            "stdout",
            "stderr",
            "reader_incomplete",
            "state",
        }
        or outcome["schema_version"] != "mp2-cost-child-outcome/1.0"
    ):
        raise IntegrityError("PROFILE_CHILD_OUTCOME_SCHEMA")
    if (
        (outcome["returncode"] is not None and type(outcome["returncode"]) is not int)
        or type(outcome["timed_out"]) is not bool
        or type(outcome["reader_incomplete"]) is not bool
        or outcome["state"] not in {"CHILD_RETURNED", "FAILED_TERMINAL_NO_RETRY"}
        or outcome["stage"] not in {"CHILD_LAUNCH", "CHILD_EXECUTION", "CHILD_TIMEOUT"}
    ):
        raise IntegrityError("PROFILE_CHILD_OUTCOME_NUMERIC_OR_STATE")
    for stream in (outcome["stdout"], outcome["stderr"]):
        if (
            set(stream) != {"bytes", "sha256", "overflow", "read_error", "content_authority"}
            or type(stream["bytes"]) is not int
            or stream["bytes"] < 0
            or type(stream["overflow"]) is not bool
            or type(stream["read_error"]) is not bool
            or stream["overflow"] != (stream["bytes"] > STREAM_LIMIT)
            or not isinstance(stream["sha256"], str)
            or len(stream["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in stream["sha256"])
            or stream["content_authority"] != "UNAUTHENTICATED_RAW_BYTES_ONLY"
        ):
            raise IntegrityError("PROFILE_CHILD_STREAM_SCHEMA")
    require_equal(outcome["role"], role, "PROFILE_CHILD_ROLE_DRIFT")
    require_equal(
        outcome["launch_guard_sha256"],
        sha256_file(case_root / "launch_guard.json"),
        "PROFILE_CHILD_LAUNCH_DRIFT",
    )
    for field, filename in (
        ("spawned_identity_sha256", "spawned_identity.json"),
        ("admission_sha256", "admission.json"),
        ("admission_failure_sha256", "admission_failure.json"),
    ):
        path = case_root / filename
        require_equal(
            outcome[field],
            sha256_file(path) if path.is_file() else None,
            "PROFILE_CHILD_CUSTODY_DRIFT",
        )
    if outcome["reader_incomplete"] or any(
        observation["read_error"] for observation in (outcome["stdout"], outcome["stderr"])
    ):
        raise IntegrityError("PROFILE_CHILD_STREAM_CUSTODY_IN_DOUBT")
    if outcome["admission_sha256"] is not None and outcome["admission_failure_sha256"] is None:
        replay_admission(root, role, authority, invocation, launch["command"])
    return outcome


def replay_admission(
    root: Path, role: str, authority: str, invocation: str, command: list[str]
) -> dict[str, Any]:
    case_root = root / "children" / role
    launch = read_canonical_json(case_root / "launch_guard.json")
    require_equal(
        launch,
        {
            "schema_version": "mp2-cost-child-launch/1.0",
            "role": role,
            "authority_sha256": authority,
            "invocation_guard_sha256": invocation,
            "command": command,
            "automatic_retry": False,
        },
        "PROFILE_CHILD_GUARD_REPLAY",
    )
    descriptor = read_canonical_json(case_root / "spawned_identity.json")
    if set(descriptor) != {
        "schema_version",
        "spawned",
        "parent",
        "command",
        "launcher_executable",
        "base_executable",
        "telemetry_authority",
    }:
        raise IntegrityError("PROFILE_PROCESS_DESCRIPTOR_SHAPE")
    validate_identity(descriptor["spawned"])
    validate_identity(descriptor["parent"])
    require_equal(descriptor["command"], command, "PROFILE_PROCESS_COMMAND_DRIFT")
    require_equal(descriptor["schema_version"], "mp2-cost-role-process/1.0", "PROCESS_SCHEMA")
    require_equal(
        descriptor["launcher_executable"],
        str(Path(command[0]).resolve()),
        "PROFILE_PROCESS_INTERPRETER_DRIFT",
    )
    require_equal(
        descriptor["base_executable"],
        str(base_executable()),
        "PROFILE_BASE_INTERPRETER_DRIFT",
    )
    require_equal(
        descriptor["telemetry_authority"],
        "UNAUTHENTICATED_RAW_BYTES_ONLY",
        "PROCESS_TELEMETRY_AUTHORITY",
    )
    admission = read_canonical_json(case_root / "admission.json")
    if set(admission) != {
        "schema_version",
        "role",
        "launch_guard_sha256",
        "spawned_identity_sha256",
        "runtime_identity",
        "state",
        "telemetry_authority",
    }:
        raise IntegrityError("PROFILE_ADMISSION_SCHEMA")
    validate_identity(admission["runtime_identity"])
    require_equal(
        admission,
        {
            "schema_version": "mp2-cost-child-admission/1.0",
            "role": role,
            "launch_guard_sha256": sha256_file(case_root / "launch_guard.json"),
            "spawned_identity_sha256": sha256_file(case_root / "spawned_identity.json"),
            "runtime_identity": admission["runtime_identity"],
            "state": "ADMITTED",
            "telemetry_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
        },
        "PROFILE_ADMISSION_REPLAY",
    )
    if (case_root / "admission_failure.json").exists() or (
        case_root / "startup_failure.json"
    ).exists():
        raise IntegrityError("PROFILE_CHILD_FAILURE_COMPANION")
    return admission


def require_child_success(outcome: dict[str, Any]) -> None:
    if (
        type(outcome["returncode"]) is not int
        or outcome["returncode"] != 0
        or outcome["state"] != "CHILD_RETURNED"
        or outcome["timed_out"]
        or outcome["exception"] is not None
        or outcome["admission_sha256"] is None
        or outcome["admission_failure_sha256"] is not None
        or outcome["stderr"]["bytes"] != 0
        or outcome["stdout"]["overflow"]
        or outcome["stderr"]["overflow"]
    ):
        raise IntegrityError("PROFILE_CHILD_FAILED_TERMINAL_NO_RETRY")
