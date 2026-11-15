"""Isolated engineering profile diagnostics; never scientific execution authority."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_sha256, sha256_bytes, sha256_file
from ai_service_v2.training.cost_runtime_custody import (
    EngineeringJournal,
    read_canonical_json,
    reject_reparse_path,
    write_exclusive_json,
)

PACKET_ID = "deep-baseline"
STAGES = {
    "WORKLOAD_ENTERED",
    "RUNTIME_DETERMINISM",
    "INPUT_LOAD",
    "DEEP_SEGMENT",
    "RECEIPT_VERIFICATION",
    "WORKLOAD_RETURNED",
    "JOURNAL_COMPLETION_PERSISTENCE",
}
ERROR_CODES = {
    "checkpoint continuation CUBLAS workspace is not locked": "CUBLAS_ENVIRONMENT_MISSING",
    "CUBLAS_ENVIRONMENT_CONFLICT": "CUBLAS_ENVIRONMENT_CONFLICT",
    "PROFILE_DEADLINE_EXCEEDED": "PROFILE_DEADLINE_EXCEEDED",
    "PROFILE_AUTHORITY_REQUIRED": "PROFILE_AUTHORITY_REQUIRED",
    "PROFILE_COMMAND_INVALID": "PROFILE_COMMAND_INVALID",
    "PROFILE_AUTHORITY_SCHEMA_OR_BINDING_MISMATCH": "PROFILE_AUTHORITY_SCHEMA_OR_BINDING_MISMATCH",
}


def require_equal(actual: Any, expected: Any, code: str) -> None:
    if canonical_json_sha256(actual) != canonical_json_sha256(expected):
        raise IntegrityError(code)


def artifact_inventory(root: Path) -> list[dict[str, Any]]:
    reject_reparse_path(root)
    rows = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            reject_reparse_path(path)
            if path.is_file():
                rows.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    return rows


def claim_profile(root: Path, guard: dict[str, Any]) -> None:
    reject_reparse_path(root)
    try:
        root.mkdir()
    except FileExistsError as error:
        raise IntegrityError("PROFILE_ALREADY_CLAIMED_NO_RETRY") from error
    write_exclusive_json(root / "invocation_guard.json", guard)


def structured_error(error: Exception) -> dict[str, Any]:
    message = str(error)
    kind = type(error).__name__
    locations = []
    trace = error.__traceback__
    while trace is not None:
        filename = Path(trace.tb_frame.f_code.co_filename).name
        function = trace.tb_frame.f_code.co_name
        locations.append(
            {
                "file": filename if re.fullmatch(r"[A-Za-z0-9_.-]+", filename) else "REDACTED",
                "function": function if re.fullmatch(r"[A-Za-z0-9_<>]+", function) else "REDACTED",
                "line": trace.tb_lineno,
            }
        )
        trace = trace.tb_next
    code = ERROR_CODES.get(message, "UNCLASSIFIED_EXCEPTION")
    return {
        "type": kind if re.fullmatch(r"[A-Za-z0-9_]+", kind) else "Exception",
        "code": code,
        "message": message if code != "UNCLASSIFIED_EXCEPTION" else "REDACTED",
        "message_sha256": sha256_bytes(message.encode("utf-8", errors="replace")),
        "traceback_locations": locations[-20:],
        "authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
    }


class ProfileContext:
    def __init__(self, root: Path, binding: str, authorization_state: str) -> None:
        self.root = root
        self.binding = binding
        self.authorization_state = authorization_state
        self.entered = False
        self.returned = False
        self.current_stage = "WORKLOAD_ENTERED"
        self.index = 0
        self.diagnostics_failed = False

    def identity(self) -> dict[str, Any]:
        return {
            "binding_sha256": self.binding,
            "authorization_state": self.authorization_state,
            "packet_id": PACKET_ID,
            "invocation_guard_sha256": sha256_file(self.root / "invocation_guard.json"),
        }

    def stage(self, name: str) -> None:
        if name not in STAGES:
            raise IntegrityError("PROFILE_STAGE_INVALID")
        self.current_stage = name
        document = {
            "schema_version": "mp2-cost-profile-stage/1.0",
            **self.identity(),
            "index": self.index,
            "stage": name,
            "monotonic_ns": time.monotonic_ns(),
            "worker_entered": self.entered,
            "worker_returned": self.returned,
            "timing_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
        }
        write_exclusive_json(self.root / "diagnostics" / f"stage-{self.index:03d}.json", document)
        self.index += 1

    def failure(self, error: Exception, *, unresolved_journal: bool = False) -> None:
        diagnostic = structured_error(error)
        if unresolved_journal:
            diagnostic["code"] = "JOURNAL_CUSTODY_ERROR_UNRESOLVED"
        write_exclusive_json(
            self.root / "diagnostics/failure.json",
            {
                "schema_version": "mp2-cost-profile-diagnostics/1.0",
                **self.identity(),
                "state": "FAILED_TERMINAL_NO_RETRY",
                "stage": self.current_stage,
                "worker_entered": self.entered,
                "worker_returned": self.returned,
                "error": diagnostic,
                "artifacts": artifact_inventory(self.root / "workloads"),
                "stages": stage_inventory(self.root / "diagnostics"),
            },
        )


class ProfileSession:
    """Companion diagnostics around the immutable engineering journal."""

    def __init__(self, root: Path, binding: str, authorization_state: str) -> None:
        reject_reparse_path(root)
        if authorization_state not in {"ENGINEERING_ONLY", "NON_AUTHORIZING"}:
            raise IntegrityError("PROFILE_CANNOT_AUTHORIZE_SCIENTIFIC_EXECUTION")
        self.root = root
        self.binding = binding
        self.authorization_state = authorization_state

    def execute(self, workload: Callable[[ProfileContext], dict[str, Any]]) -> dict[str, Any]:
        read_canonical_json(self.root / "invocation_guard.json")
        try:
            (self.root / "diagnostics").mkdir()
        except FileExistsError as error:
            raise IntegrityError("PROFILE_ALREADY_CLAIMED_NO_RETRY") from error
        context = ProfileContext(self.root, self.binding, self.authorization_state)
        journal = EngineeringJournal(
            self.root / "journal",
            binding_sha256=self.binding,
            authorization_state=self.authorization_state,
        )

        def wrapped() -> dict[str, Any]:
            try:
                context.entered = True
                context.stage("WORKLOAD_ENTERED")
                result = workload(context)
                context.returned = True
                context.stage("WORKLOAD_RETURNED")
                write_exclusive_json(
                    self.root / "diagnostics/completion.json",
                    {
                        "schema_version": "mp2-cost-profile-diagnostics/1.0",
                        **context.identity(),
                        "state": "COMPLETE_NON_AUTHORIZING",
                        "worker_entered": True,
                        "worker_returned": True,
                        "result_sha256": canonical_json_sha256(result),
                        "artifacts": artifact_inventory(self.root / "workloads"),
                        "stages": stage_inventory(self.root / "diagnostics"),
                    },
                )
                return result
            except Exception as error:
                try:
                    context.failure(error)
                except (IntegrityError, OSError):
                    context.diagnostics_failed = True
                    raise
                raise

        result = journal.execute(PACKET_ID, wrapped)
        if context.diagnostics_failed:
            return {"state": "IN_DOUBT"}
        if (
            result["state"] != "COMPLETE_NON_AUTHORIZING"
            and not (self.root / "diagnostics/failure.json").exists()
        ):
            try:
                context.current_stage = "JOURNAL_COMPLETION_PERSISTENCE"
                context.failure(
                    IntegrityError("journal detail unavailable"), unresolved_journal=True
                )
            except (IntegrityError, OSError):
                return {"state": "IN_DOUBT"}
        return self.status()

    def status(self) -> dict[str, Any]:
        try:
            return self.replay()
        except (IntegrityError, OSError, KeyError, TypeError, ValueError):
            return {"state": "IN_DOUBT"}

    def replay(self) -> dict[str, Any]:
        read_canonical_json(self.root / "invocation_guard.json")
        if not (self.root / "journal").is_dir():
            raise IntegrityError("PROFILE_GUARD_ONLY_IN_DOUBT")
        journal = EngineeringJournal(
            self.root / "journal",
            binding_sha256=self.binding,
            authorization_state=self.authorization_state,
        ).replay(PACKET_ID)
        failure_path = self.root / "diagnostics/failure.json"
        if journal["state"] == "FAILED_TERMINAL":
            diagnostic = read_canonical_json(failure_path)
            state = "FAILED_TERMINAL_NO_RETRY"
            fields = {"stage", "error", "worker_entered", "worker_returned"}
        else:
            if journal["state"] != "COMPLETE_NON_AUTHORIZING" or failure_path.exists():
                raise IntegrityError("PROFILE_HAS_FAILURE_OR_PARTIAL_CUSTODY")
            diagnostic = read_canonical_json(self.root / "diagnostics/completion.json")
            state = "COMPLETE_NON_AUTHORIZING"
            fields = {"result_sha256", "worker_entered", "worker_returned"}
            require_equal(
                diagnostic.get("result_sha256"),
                canonical_json_sha256(journal["worker_result"]),
                "PROFILE_RESULT_HASH_MISMATCH",
            )
        context = ProfileContext(self.root, self.binding, self.authorization_state)
        expected = set(context.identity()) | {"schema_version", "state", "artifacts", "stages"}
        if set(diagnostic) != expected | fields:
            raise IntegrityError("PROFILE_DIAGNOSTICS_SCHEMA_MISMATCH")
        require_equal(diagnostic["schema_version"], "mp2-cost-profile-diagnostics/1.0", "SCHEMA")
        require_equal(diagnostic["state"], state, "PROFILE_DIAGNOSTICS_STATE_MISMATCH")
        for key, value in context.identity().items():
            require_equal(diagnostic[key], value, "PROFILE_DIAGNOSTICS_IDENTITY_MISMATCH")
        if (
            type(diagnostic["worker_entered"]) is not bool
            or type(diagnostic["worker_returned"]) is not bool
            or diagnostic["worker_entered"] is not True
            or (journal.get("worker_returned", True) and not diagnostic["worker_returned"])
        ):
            raise IntegrityError("PROFILE_WORKLOAD_ENTRY_RETURN_MISMATCH")
        require_equal(
            diagnostic["artifacts"], artifact_inventory(self.root / "workloads"), "ARTIFACTS"
        )
        stages = stage_inventory(self.root / "diagnostics")
        names = {p.name for p in (self.root / "diagnostics").iterdir()}
        allowed_names = {r["path"] for r in stages} | {"completion.json", "failure.json"}
        if not stages or not names <= allowed_names:
            raise IntegrityError("PROFILE_DIAGNOSTICS_PARTIAL_OR_UNKNOWN")
        require_equal(diagnostic["stages"], stages, "PROFILE_STAGE_HASH_MISMATCH")
        for index, row in enumerate(stages):
            if row["path"] != f"stage-{index:03d}.json":
                raise IntegrityError("PROFILE_STAGE_SEQUENCE_MISMATCH")
            event = read_canonical_json(self.root / "diagnostics" / row["path"])
            event_fields = set(context.identity()) | {
                "schema_version",
                "index",
                "stage",
                "monotonic_ns",
                "worker_entered",
                "worker_returned",
                "timing_authority",
            }
            if (
                set(event) != event_fields
                or event["stage"] not in STAGES
                or type(event["monotonic_ns"]) is not int
                or event["monotonic_ns"] <= 0
                or type(event["worker_entered"]) is not bool
                or type(event["worker_returned"]) is not bool
            ):
                raise IntegrityError("PROFILE_STAGE_SCHEMA_MISMATCH")
            require_equal(event["schema_version"], "mp2-cost-profile-stage/1.0", "STAGE_SCHEMA")
            require_equal(event["timing_authority"], "UNAUTHENTICATED_RAW_BYTES_ONLY", "TIMING")
            require_equal(event["index"], index, "PROFILE_STAGE_INDEX_MISMATCH")
            for key, value in context.identity().items():
                require_equal(event[key], value, "PROFILE_STAGE_IDENTITY_MISMATCH")
        return {"state": state, "journal": journal, "diagnostics": diagnostic}


def stage_inventory(root: Path) -> list[dict[str, Any]]:
    return [row for row in artifact_inventory(root) if row["path"].startswith("stage-")]


def locked_child_environment(parent: Mapping[str, str]) -> dict[str, str]:
    value = parent.get("CUBLAS_WORKSPACE_CONFIG")
    if value is not None and value != ":4096:8":
        raise IntegrityError("CUBLAS_ENVIRONMENT_CONFLICT")
    return {**parent, "CUBLAS_WORKSPACE_CONFIG": ":4096:8"}
