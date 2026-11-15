"""Durable, non-scientific execution custody shared by engineering and fixtures."""

from __future__ import annotations

import os
import re
import stat
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from ai_service_v2.training.cost_optimization import ROUTE_ID, preparation_state


def reject_reparse_path(path: Path) -> None:
    for ancestor in (path, *path.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise IntegrityError("reparse/symlink paths are forbidden for execution custody")


def write_exclusive_json(path: Path, document: dict[str, Any]) -> None:
    """Leave any failed or partial claim in place; never repair it."""
    from ai_service_v2.training.cost_engineering_write_guard_33 import (
        reject_withdrawn_engineering_root,
    )

    reject_withdrawn_engineering_root(path)
    reject_reparse_path(path)
    payload = canonical_json_bytes(document) + b"\n"
    if len(payload) > 8 * 1024 * 1024:
        raise IntegrityError("CUSTODY_DOCUMENT_BYTE_BOUND")
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != payload or load_strict_json(path) != document:
            raise IntegrityError("durable JSON readback mismatch")
    except OSError as error:
        raise IntegrityError("exclusive custody creation failed; existing bytes remain") from error


def read_canonical_json(path: Path) -> dict[str, Any]:
    reject_reparse_path(path)
    document = load_strict_json(path)
    if path.read_bytes() != canonical_json_bytes(document) + b"\n":
        raise IntegrityError("noncanonical execution custody")
    return document


@contextmanager
def exclusive_lane(root: Path) -> Iterator[None]:
    """OS locks prevent concurrent packets; durable guards prevent crash recovery."""
    from ai_service_v2.training.cost_engineering_write_guard_33 import (
        reject_withdrawn_engineering_root,
    )

    reject_withdrawn_engineering_root(root)
    if os.name != "nt":
        raise IntegrityError("cost route execution supports the admitted Windows runtime only")
    lane_path = root / "lane.lock"
    reject_reparse_path(lane_path)
    with lane_path.open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"0")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise IntegrityError("execution lane already occupied") from error
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class EngineeringJournal:
    """One-shot per packet; this interface cannot authorize scientific execution.

    An immutable verified staging record is hard-linked into the completion
    authority as the last write. A receipt alone is never completion authority.
    """

    def __init__(
        self,
        root: Path,
        *,
        binding_sha256: str,
        authorization_state: str,
    ) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(root)
        if not re.fullmatch(r"[0-9a-f]{64}", binding_sha256):
            raise IntegrityError("journal binding SHA-256 is invalid")
        if authorization_state not in {"NON_AUTHORIZING", "ENGINEERING_ONLY"}:
            raise IntegrityError("journal cannot accept scientific authority")
        reject_reparse_path(root)
        if {"research", "ai-service-v2"} & {p.casefold() for p in root.parts}:
            raise IntegrityError(
                "engineering/fixture journals cannot write into research or source"
            )
        self.root = root.resolve()
        self.binding_sha256 = binding_sha256
        self.authorization_state = authorization_state
        self.root.mkdir(parents=True, exist_ok=True)

    def _packet_root(self, packet_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", packet_id) or packet_id in {
            "con",
            "prn",
            "aux",
            "nul",
            *(f"com{i}" for i in range(1, 10)),
            *(f"lpt{i}" for i in range(1, 10)),
        }:
            raise IntegrityError("invalid packet identity")
        path = self.root / packet_id
        reject_reparse_path(path)
        return path

    def _identity(self, packet_id: str) -> dict[str, Any]:
        return {
            "route_id": ROUTE_ID,
            "packet_id": packet_id,
            "binding_sha256": self.binding_sha256,
            **preparation_state(),
            "authorization_state": self.authorization_state,
        }

    def execute(
        self,
        packet_id: str,
        workload: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        self._packet_root(packet_id)
        with exclusive_lane(self.root):
            if (self.root / "terminal_failure.json").exists():
                raise IntegrityError("journal has terminal failure; no continuation")
            for entry in self.root.iterdir():
                if entry.name == "lane.lock":
                    continue
                if (
                    not entry.is_dir()
                    or self.status(entry.name)["state"] != "COMPLETE_NON_AUTHORIZING"
                ):
                    raise IntegrityError("journal contains terminal/IN_DOUBT custody")
            return self._execute_claimed(packet_id, workload)

    def _execute_claimed(
        self,
        packet_id: str,
        workload: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        directory = self._packet_root(packet_id)
        if (self.root / "terminal_failure.json").exists():
            raise IntegrityError("journal has terminal failure; no continuation")
        directory.mkdir(exist_ok=True)
        guard_path = directory / "guard.json"
        guard = {
            "schema_version": "mp2-cost-engineering-invocation-guard/1.0",
            **self._identity(packet_id),
            "invocation_id": str(uuid.uuid4()),
        }
        # Exclusive creation is the claim, even if fsync/readback subsequently fails.
        try:
            write_exclusive_json(guard_path, guard)
        except IntegrityError as error:
            raise IntegrityError("packet already claimed or claim is IN_DOUBT") from error
        entered = False
        returned = False
        try:
            if {p.name for p in directory.iterdir()} != {"guard.json"}:
                raise IntegrityError("packet namespace contains unexpected custody")
            entered = True
            output = workload()
            returned = True
            if not isinstance(output, dict):
                raise IntegrityError("engineering workload must return a JSON object")
            receipt = {
                "schema_version": "mp2-cost-engineering-completion/1.0",
                **self._identity(packet_id),
                "state": "COMPLETE_NON_AUTHORIZING",
                "guard_sha256": sha256_file(guard_path),
                "worker_result": output,
            }
            receipt_path = directory / "completion_receipt.json"
            write_exclusive_json(receipt_path, receipt)
            authority = {
                "schema_version": "mp2-cost-engineering-completion-authority/1.0",
                **self._identity(packet_id),
                "guard_sha256": sha256_file(guard_path),
                "receipt_sha256": sha256_file(receipt_path),
                "receipt_bytes": receipt_path.stat().st_size,
            }
            staged = directory / "completion_authority.staged.json"
            write_exclusive_json(staged, authority)
            # No cleanup or further persistence follows successful atomic publication.
            os.link(staged, directory / "completion_authority.json")
        except Exception as error:
            failure = {
                "schema_version": "mp2-cost-engineering-failure/1.0",
                **self._identity(packet_id),
                "state": "FAILED_TERMINAL",
                "guard_sha256": sha256_file(guard_path),
                "worker_entered": entered,
                "worker_returned": returned,
                "error_type": type(error).__name__,
                "error_authority": "UNAUTHENTICATED_RAW_BYTES_ONLY",
            }
            try:
                write_exclusive_json(self.root / "terminal_failure.json", failure)
                write_exclusive_json(directory / "failure.json", failure)
            except (IntegrityError, OSError):
                return {**self._identity(packet_id), "state": "IN_DOUBT"}
            return failure
        return receipt

    def status(self, packet_id: str) -> dict[str, Any]:
        try:
            return self.replay(packet_id)
        except (IntegrityError, OSError, KeyError, ValueError, TypeError):
            return {**self._identity(packet_id), "state": "IN_DOUBT"}

    def replay(self, packet_id: str) -> dict[str, Any]:
        directory = self._packet_root(packet_id)
        identity = self._identity(packet_id)
        if not directory.exists():
            return {**identity, "state": "NOT_CLAIMED"}
        guard = read_canonical_json(directory / "guard.json")
        if set(guard) != set(identity) | {"schema_version", "invocation_id"}:
            raise IntegrityError("guard schema mismatch")
        if guard["schema_version"] != "mp2-cost-engineering-invocation-guard/1.0":
            raise IntegrityError("guard schema mismatch")
        for field, value in identity.items():
            if canonical_json_bytes({field: guard[field]}) != canonical_json_bytes({field: value}):
                raise IntegrityError("guard identity mismatch")
        if str(uuid.UUID(guard["invocation_id"])) != guard["invocation_id"]:
            raise IntegrityError("guard invocation identity mismatch")
        guard_sha = sha256_file(directory / "guard.json")
        failure_path = directory / "failure.json"
        terminal_path = self.root / "terminal_failure.json"
        if failure_path.exists() or terminal_path.exists():
            failure = read_canonical_json(failure_path)
            terminal = read_canonical_json(terminal_path)
            if (
                failure != terminal
                or failure.get("guard_sha256") != guard_sha
                or failure.get("state") != "FAILED_TERMINAL"
            ):
                raise IntegrityError("terminal failure custody mismatch")
            if set(failure) != set(identity) | {
                "schema_version",
                "state",
                "guard_sha256",
                "worker_entered",
                "worker_returned",
                "error_type",
                "error_authority",
            } or any(
                failure.get(k) != v or type(failure.get(k)) is not type(v)
                for k, v in identity.items()
            ):
                raise IntegrityError("failure identity mismatch")
            return failure
        expected_names = {
            "guard.json",
            "completion_receipt.json",
            "completion_authority.json",
            "completion_authority.staged.json",
        }
        if {p.name for p in directory.iterdir()} != expected_names:
            raise IntegrityError("missing or partial durable completion authority")
        authority_path = directory / "completion_authority.json"
        authority = read_canonical_json(authority_path)
        staged = read_canonical_json(directory / "completion_authority.staged.json")
        receipt_path = directory / "completion_receipt.json"
        receipt = read_canonical_json(receipt_path)
        expected_authority = {
            "schema_version": "mp2-cost-engineering-completion-authority/1.0",
            **identity,
            "guard_sha256": guard_sha,
            "receipt_sha256": sha256_file(receipt_path),
            "receipt_bytes": receipt_path.stat().st_size,
        }
        if canonical_json_bytes(authority) != canonical_json_bytes(
            expected_authority
        ) or canonical_json_bytes(staged) != canonical_json_bytes(authority):
            raise IntegrityError("completion authority binding mismatch")
        expected_receipt_fields = set(identity) | {
            "schema_version",
            "state",
            "guard_sha256",
            "worker_result",
        }
        if set(receipt) != expected_receipt_fields or receipt.get("guard_sha256") != guard_sha:
            raise IntegrityError("completion receipt schema or guard binding mismatch")
        if (
            receipt.get("state") != "COMPLETE_NON_AUTHORIZING"
            or receipt.get("schema_version") != "mp2-cost-engineering-completion/1.0"
            or not isinstance(receipt.get("worker_result"), dict)
        ):
            raise IntegrityError("completion receipt cannot authorize this journal")
        for field, value in identity.items():
            if canonical_json_bytes({field: receipt[field]}) != canonical_json_bytes(
                {field: value}
            ):
                raise IntegrityError("completion identity mismatch")
        return receipt
