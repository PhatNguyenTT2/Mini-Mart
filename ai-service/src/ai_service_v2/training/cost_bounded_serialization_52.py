"""Fixed-cap native serializers for production checkpoint and score writers."""

from __future__ import annotations

import io
import os
import shutil
import stat
import sys
import threading
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import torch

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, sha256_file
from ai_service_v2.training.cost_bounded_io_01 import allocation_unit, policy_caps
from ai_service_v2.training.cost_control_storage_01 import safe_name
from ai_service_v2.training.cost_engineering_write_guard_33 import reject_withdrawn_engineering_root

DOCUMENT_BOUND_BYTES = 8 * 1024 * 1024
JSONL_RECORD_BOUND_BYTES = 64 * 1024
_PAYLOAD_BUDGET_LOCK = threading.RLock()
_ACTIVE_PAYLOAD_BUDGET: BoundedPayloadBudget | None = None
_ACTIVE_CAMPAIGN_OUTPUT: tuple[Path, tuple[int, int]] | None = None
_CAMPAIGN_AUDIT_INSTALLED = False


def _campaign_audit(event: str, args: tuple[Any, ...]) -> None:
    scope = _ACTIVE_CAMPAIGN_OUTPUT
    if scope is None:
        return
    root, owner = scope
    if owner != (os.getpid(), threading.get_ident()):
        if event in {
            "open",
            "os.mkdir",
            "os.rename",
            "os.remove",
            "os.rmdir",
            "os.link",
            "os.symlink",
            "os.chdir",
            "subprocess.Popen",
        }:
            raise IntegrityError("CAMPAIGN_OUTPUT_FOREIGN_WRITER")
        return
    if event == "open":
        mode = args[1]
        flags = args[2]
        writing = (isinstance(mode, str) and any(character in mode for character in "wax+")) or (
            isinstance(flags, int)
            and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        )
        paths = args[:1] if writing else ()
    elif event in {"os.mkdir", "os.remove", "os.rmdir"}:
        paths = args[:1]
    elif event == "os.rename":
        paths = args[:2]
    elif event == "subprocess.Popen" and os.name == "nt" and args == (None, "lscpu", None, None):
        raise FileNotFoundError("no platform probe subprocess in campaign output scope")
    elif event in {"os.link", "os.symlink", "os.chdir", "subprocess.Popen"}:
        raise IntegrityError(f"CAMPAIGN_OUTPUT_UNADMITTED_MUTATION:{event}")
    else:
        return
    for value in paths:
        if not isinstance(value, (str, os.PathLike)):
            raise IntegrityError("CAMPAIGN_OUTPUT_PATH_UNRESOLVED")
        path = Path(value).absolute()
        if not path.is_relative_to(root) or path != path.resolve():
            raise IntegrityError("CAMPAIGN_OUTPUT_PATH_OUTSIDE_NAMESPACE")


@contextmanager
def enforce_campaign_output_root(root: Path) -> Iterator[None]:
    """Constrain adapted worker destinations to one current campaign namespace."""
    from ai_service_v2.training.cost_runtime_custody import reject_reparse_path

    global _ACTIVE_CAMPAIGN_OUTPUT, _CAMPAIGN_AUDIT_INSTALLED
    if not root.is_absolute() or root.absolute() != root.resolve() or not root.is_dir():
        raise IntegrityError("CAMPAIGN_OUTPUT_ROOT_NOT_CANONICAL")
    reject_reparse_path(root)
    owner = (os.getpid(), threading.get_ident())
    with _PAYLOAD_BUDGET_LOCK:
        if _ACTIVE_CAMPAIGN_OUTPUT is not None:
            raise IntegrityError("CAMPAIGN_OUTPUT_SCOPE_ALREADY_ACTIVE")
        if not _CAMPAIGN_AUDIT_INSTALLED:
            sys.addaudithook(_campaign_audit)
            _CAMPAIGN_AUDIT_INSTALLED = True
        _ACTIVE_CAMPAIGN_OUTPUT = (root, owner)
    try:
        yield
    finally:
        with _PAYLOAD_BUDGET_LOCK:
            _ACTIVE_CAMPAIGN_OUTPUT = None


class BoundedPayloadBudget:
    """Prospective aggregate reservation for explicitly adapted serializers only."""

    def __init__(
        self,
        root: Path,
        *,
        file_bounds: Mapping[str, int],
        maximum_allocated_bytes: int,
        replacement_limits: Mapping[str, int] | None = None,
        directory_publications: Mapping[str, str] | None = None,
        directory_rotations: Mapping[str, str] | None = None,
        directory_disposals: Mapping[str, int] | None = None,
        payload_disposals: Sequence[str] | None = None,
        maximum_file_count: int = 4096,
    ) -> None:
        if (
            not root.is_absolute()
            or ".." in root.parts
            or type(maximum_allocated_bytes) is not int
            or maximum_allocated_bytes < 1
            or type(maximum_file_count) is not int
            or maximum_file_count not in {4096, 4650, 4751}
            or not 1 <= len(file_bounds) <= maximum_file_count
        ):
            raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_GEOMETRY")
        validate_payload_destination(root)
        if root.exists():
            raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_NAMESPACE_ALREADY_USED")
        self._root = root
        self._bounds: dict[Path, int] = {}
        directories = {root}
        for name, bound in file_bounds.items():
            if (
                type(name) is not str
                or "\\" in name
                or Path(name).is_absolute()
                or Path(name).as_posix() != name
                or type(bound) is not int
                or not 1 <= bound <= max(policy_caps()["checkpoint"], policy_caps()["scores"])
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_FILE_ROSTER")
            safe_name(name)
            path = root / name
            if path in self._bounds:
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_DUPLICATE_PATH")
            self._bounds[path] = bound
            directories.update(parent for parent in path.parents if parent.is_relative_to(root))
        if set(self._bounds) & directories:
            raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_FILE_DIRECTORY_OVERLAP")
        self._directory_publications: dict[Path, Path] = {}
        for stage_name, target_name in (directory_publications or {}).items():
            for name in (stage_name, target_name):
                if (
                    type(name) is not str
                    or "\\" in name
                    or Path(name).is_absolute()
                    or Path(name).as_posix() != name
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_ROSTER")
                safe_name(name)
            stage, target = root / stage_name, root / target_name
            files = {path.name for path in self._bounds if path.parent == stage}
            if (
                stage.parent != target.parent
                or stage == target
                or files != {"checkpoint.pt", "manifest.json"}
                or any(path.is_relative_to(target) for path in self._bounds)
                or any(path.is_relative_to(stage) and path.parent != stage for path in self._bounds)
                or target in self._bounds
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_ROSTER")
            self._directory_publications[stage] = target
            directories.add(target)
        stages = set(self._directory_publications)
        targets = set(self._directory_publications.values())
        roles = stages | targets
        if stages & targets or any(
            left != right and left.is_relative_to(right) for left in roles for right in roles
        ):
            raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_ROLE_OVERLAP")
        self._directory_rotations: dict[Path, Path] = {}
        self._directory_disposals: dict[Path, int] = {}
        for source_name, target_name in (directory_rotations or {}).items():
            for name in (source_name, target_name):
                if (
                    type(name) is not str
                    or "\\" in name
                    or Path(name).is_absolute()
                    or Path(name).as_posix() != name
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_ROTATION_ROSTER")
                safe_name(name)
            source, target = root / source_name, root / target_name
            if (
                source not in targets
                or source.parent != target.parent
                or target in roles
                or target in self._directory_rotations.values()
                or any(path.is_relative_to(target) for path in self._bounds)
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_ROTATION_ROSTER")
            self._directory_rotations[source] = target
            directories.add(target)
        for name, limit in (directory_disposals or {}).items():
            path = root / name
            if (
                path not in self._directory_rotations.values()
                or path.relative_to(root).as_posix() != name
                or type(limit) is not int
                or not 1 <= limit <= 100
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_ROSTER")
            self._directory_disposals[path] = limit
        if set(self._directory_disposals) != set(self._directory_rotations.values()):
            raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_ROSTER")
        self._rotation_counts: dict[Path, int] = {}
        self._disposal_counts: dict[Path, int] = {}
        self._vacated_directories: set[Path] = set()
        self._pending_directory: tuple[Path, Path] | None = None
        self._retired_directories: set[Path] = set()
        self._publication_file_identities: dict[Path, tuple[int, int, int, int]] = {}
        self._published_directories: set[Path] = set()
        self._replacement_limits: dict[Path, int] = {}
        self._replacement_staging: dict[Path, Path] = {}
        for name, limit in (replacement_limits or {}).items():
            if type(name) is not str:
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_ROSTER")
            target = root / name
            temporary = target.with_suffix(target.suffix + ".tmp")
            if (
                target not in self._bounds
                or temporary not in self._bounds
                or target.relative_to(root).as_posix() != name
                or type(limit) is not int
                or not 1 <= limit <= 100
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_ROSTER")
            self._replacement_limits[target] = limit
            self._replacement_staging[temporary] = target
        if set(self._replacement_limits) & self._replacement_staging.keys():
            raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_ROLE_OVERLAP")
        self._replacement_counts: dict[Path, int] = {}
        self._replacement_identities: dict[Path, tuple[int, int, int, int]] = {}
        self._pending_replacement: tuple[Path, Path] | None = None
        self._payload_disposals: set[Path] = set()
        for name in payload_disposals or ():
            if type(name) is not str or name not in file_bounds:
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_ROSTER")
            path = root / name
            if (
                path in self._payload_disposals
                or path in self._replacement_limits
                or path in self._replacement_staging
                or path.parent in self._directory_publications
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_ROSTER")
            self._payload_disposals.add(path)
        self._disposal_file_identities: dict[Path, tuple[int, int, int, int]] = {}
        self._disposed_payloads: set[Path] = set()
        for parent in root.parents:
            if parent.exists():
                break
            directories.add(parent)
        self._directories = directories
        self._directory_identities: dict[Path, tuple[int, int]] = {}
        for parent in root.parents:
            try:
                info = parent.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(info.st_mode) or not info.st_ino:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_IDENTITY_DRIFT")
            self._directory_identities[parent] = (info.st_dev, info.st_ino)
        self._unit = allocation_unit(root)
        self._maximum = maximum_allocated_bytes
        self._charged = len(directories) * self._unit
        if self._charged > self._maximum:
            raise IntegrityError("BOUNDED_PAYLOAD_AGGREGATE_ALLOCATION_CAP")
        self._written: dict[Path, int] = {}
        self._owner = (os.getpid(), threading.get_ident())
        self._state = "PREPARED"

    @property
    def maximum_allocated_bytes(self) -> int:
        return self._maximum

    @contextmanager
    def enforce(self) -> Iterator[None]:
        global _ACTIVE_PAYLOAD_BUDGET
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "PREPARED"
                or _ACTIVE_PAYLOAD_BUDGET is not None
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            if self._root.exists():
                self._state = "FAILED"
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_NAMESPACE_ALREADY_USED")
            self._check_directory_identities()
            self._state = "ACTIVE"
            _ACTIVE_PAYLOAD_BUDGET = self
        try:
            yield
            if self._state != "ACTIVE":
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_POISONED")
            if self._state == "ACTIVE":
                self._check_directory_identities()
                self._check_replacement_identities()
                self._check_publication_identities()
                self._check_disposal_identities()
                if self._pending_replacement is not None:
                    raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_INCOMPLETE")
                if self._pending_directory is not None:
                    raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_INCOMPLETE")
        except BaseException:
            self._state = "FAILED"
            raise
        finally:
            with _PAYLOAD_BUDGET_LOCK:
                _ACTIVE_PAYLOAD_BUDGET = None
                if self._state == "ACTIVE":
                    self._state = "SEALED"

    def _check_directory_identities(self) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            try:
                if any(
                    os.path.lexists(path)
                    for path in self._retired_directories | self._vacated_directories
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_RESURRECTION")
                for parent, identity in self._directory_identities.items():
                    info = parent.lstat()
                    if (
                        not stat.S_ISDIR(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 0x400
                        or (info.st_dev, info.st_ino) != identity
                    ):
                        raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_IDENTITY_DRIFT")
                for parent in self._directories - self._directory_identities.keys():
                    try:
                        info = parent.lstat()
                    except FileNotFoundError:
                        continue
                    if (
                        not stat.S_ISDIR(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 0x400
                        or not info.st_ino
                    ):
                        raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_IDENTITY_DRIFT")
                    self._directory_identities[parent] = (info.st_dev, info.st_ino)
            except (IntegrityError, OSError) as error:
                self._state = "FAILED"
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_IDENTITY_DRIFT") from error

    def reserve(
        self, path: Path, byte_count: int, *, previous_byte_count: int | None = None
    ) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            try:
                if (
                    self._owner != (os.getpid(), threading.get_ident())
                    or self._state != "ACTIVE"
                    or _ACTIVE_PAYLOAD_BUDGET is not self
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
                self._check_directory_identities()
                target = path.absolute()
                self._check_disposal_identities()
                if ".." in path.parts or target not in self._bounds:
                    raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_UNDECLARED_PATH")
                if target.parent in self._directory_publications and self._pending_directory != (
                    target.parent,
                    self._directory_publications[target.parent],
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_LIFECYCLE_REQUIRED")
                if target in self._replacement_limits or (
                    target in self._replacement_staging
                    and self._pending_replacement != (self._replacement_staging[target], target)
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_LIFECYCLE_REQUIRED")
                previous = 0
                if previous_byte_count is not None and target in self._written:
                    info = target.stat()
                    if (
                        type(previous_byte_count) is not int
                        or previous_byte_count != self._written[target]
                        or info.st_size != previous_byte_count
                        or info.st_nlink != 1
                    ):
                        raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_APPEND_DRIFT")
                    previous = previous_byte_count
                elif (
                    target in self._written
                    or target.exists()
                    or previous_byte_count not in {None, 0}
                ):
                    raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_NAMESPACE_ALREADY_USED")
                if type(byte_count) is not int or byte_count < previous:
                    raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_WRITE_GEOMETRY")
                if byte_count > self._bounds[target]:
                    raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_FILE_CAP")
                charge = (
                    (byte_count + self._unit - 1) // self._unit
                    - (previous + self._unit - 1) // self._unit
                ) * self._unit
                if self._charged + charge > self._maximum:
                    raise IntegrityError("BOUNDED_PAYLOAD_AGGREGATE_ALLOCATION_CAP")
                self._charged += charge
                self._written[target] = byte_count
            except BaseException:
                self._state = "FAILED"
                raise

    @staticmethod
    def _replacement_identity(path: Path) -> tuple[int, int, int, int]:
        try:
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or not info.st_ino
                or info.st_nlink != 1
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_IDENTITY_DRIFT")
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
        except OSError as error:
            raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_IDENTITY_DRIFT") from error

    def _check_replacement_identities(self) -> None:
        for target, identity in self._replacement_identities.items():
            if self._replacement_identity(target) != identity:
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_IDENTITY_DRIFT")

    def _check_publication_identities(self) -> None:
        for path, identity in self._publication_file_identities.items():
            validate_payload_destination(path)
            if self._replacement_identity(path) != identity:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FILE_DRIFT")
        for target in self._published_directories:
            if {path.name for path in target.iterdir()} != {"checkpoint.pt", "manifest.json"}:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FILE_ROSTER")

    def _begin_directory_publication(self, stage: Path, target: Path) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            self._check_directory_identities()
            self._check_publication_identities()
            self._check_disposal_identities()
            if self._directory_publications.get(stage) != target:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_LIFECYCLE_REQUIRED")
            if (
                self._pending_directory is not None
                or stage in self._retired_directories
                or os.path.lexists(stage)
                or os.path.lexists(target)
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FOREIGN_OR_USED")
            validate_payload_destination(stage)
            validate_payload_destination(target)
            self._pending_directory = stage, target

    def _record_publication_file(self, path: Path) -> None:
        path = path.absolute()
        if path.parent in self._directory_publications:
            identity = self._replacement_identity(path)
            if self._written.get(path) != identity[2]:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FILE_DRIFT")
            self._publication_file_identities[path] = identity
        if path in self._payload_disposals:
            self._disposal_file_identities[path] = self._replacement_identity(path)

    def _check_disposal_identities(self) -> None:
        if any(os.path.lexists(path) for path in self._disposed_payloads):
            raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_RESURRECTION")
        for path, identity in self._disposal_file_identities.items():
            validate_payload_destination(path)
            if self._replacement_identity(path) != identity:
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_IDENTITY_DRIFT")

    def _dispose_payload(self, path: Path, digest: str) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            self._check_directory_identities()
            self._check_disposal_identities()
            if path not in self._payload_disposals or path not in self._disposal_file_identities:
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_UNOWNED_OR_UNDECLARED")
            validate_payload_destination(path)
            if self._written.get(path) != path.stat().st_size or sha256_file(path) != digest:
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_DIGEST_DRIFT")
            path.unlink()
            if os.path.lexists(path):
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_INCOMPLETE")
            self._disposal_file_identities.pop(path)
            self._disposed_payloads.add(path)

    def _commit_directory_publication(self, stage: Path, target: Path) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
                or self._pending_directory != (stage, target)
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_PUBLICATION_INCOMPLETE")
            self._check_directory_identities()
            self._check_publication_identities()
            validate_payload_destination(stage)
            validate_payload_destination(target)
            files = {stage / "checkpoint.pt", stage / "manifest.json"}
            if (
                set(stage.iterdir()) != files
                or not files <= self._publication_file_identities.keys()
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FILE_ROSTER")
            if os.path.lexists(target):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_FOREIGN_OR_USED")
            identity = self._directory_identities[stage]
            os.rename(stage, target)
            self._directory_identities.pop(stage)
            self._directories.remove(stage)
            self._retired_directories.add(stage)
            self._directory_identities[target] = identity
            for path in files:
                moved = target / path.name
                self._publication_file_identities[moved] = self._publication_file_identities.pop(
                    path
                )
                self._written[moved] = self._written.pop(path)
            self._published_directories.add(target)
            self._vacated_directories.discard(target)
            self._pending_directory = None
            self._check_directory_identities()
            self._check_publication_identities()

    def _rotate_directory(self, source: Path, target: Path) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            self._check_directory_identities()
            self._check_publication_identities()
            if (
                self._directory_rotations.get(source) != target
                or source not in self._published_directories
                or self._pending_directory is not None
                or os.path.lexists(target)
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_ROTATION_LIFECYCLE")
            count = self._rotation_counts.get(target, 0)
            if count >= self._directory_disposals[target]:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_ROTATION_LIMIT")
            validate_payload_destination(source)
            validate_payload_destination(target)
            os.rename(source, target)
            self._directory_identities[target] = self._directory_identities.pop(source)
            for name in ("checkpoint.pt", "manifest.json"):
                old, new = source / name, target / name
                self._publication_file_identities[new] = self._publication_file_identities.pop(old)
                self._written[new] = self._written.pop(old)
            self._published_directories.remove(source)
            self._published_directories.add(target)
            self._vacated_directories.add(source)
            self._vacated_directories.discard(target)
            self._rotation_counts[target] = count + 1
            self._check_directory_identities()
            self._check_publication_identities()

    def _dispose_directory(self, path: Path, archived: Path, digest: str) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            self._check_directory_identities()
            self._check_publication_identities()
            if (
                path not in self._directory_disposals
                or path not in self._published_directories
                or not any(
                    self._directory_rotations.get(source) == path
                    for source in self._published_directories
                )
                or self._pending_directory is not None
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_SUCCESSOR")
            count = self._disposal_counts.get(path, 0)
            if count >= self._directory_disposals[path]:
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_LIMIT")
            validate_payload_destination(path)
            validate_payload_destination(archived)
            if (
                archived not in self._bounds
                or archived.is_relative_to(path)
                or self._written.get(archived) is None
                or self._replacement_identity(archived)[2] != self._written[archived]
                or sha256_file(archived) != digest
                or sha256_file(path / "manifest.json") != digest
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_ARCHIVE")
            self._publication_file_identities[archived] = self._replacement_identity(archived)
            self._disposal_counts[path] = count + 1
            shutil.rmtree(path)
            if os.path.lexists(path):
                raise IntegrityError("BOUNDED_PAYLOAD_DIRECTORY_DISPOSAL_INCOMPLETE")
            self._directory_identities.pop(path)
            for name in ("checkpoint.pt", "manifest.json"):
                self._publication_file_identities.pop(path / name)
                self._written.pop(path / name)
            self._published_directories.remove(path)
            self._vacated_directories.add(path)
            self._check_directory_identities()
            self._check_publication_identities()

    def _begin_replacement(self, path: Path, temporary: Path, byte_count: int) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_OWNER_OR_TERMINAL")
            self._check_directory_identities()
            self._check_replacement_identities()
            target, staging = path.absolute(), temporary.absolute()
            if target not in self._replacement_limits:
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_LIFECYCLE_REQUIRED")
            if (
                self._replacement_staging.get(staging) != target
                or self._pending_replacement is not None
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_INCOMPLETE")
            if self._replacement_counts.get(target, 0) >= self._replacement_limits[target]:
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_LIMIT")
            if target not in self._replacement_identities and target.exists():
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_FOREIGN_TARGET")
            if byte_count > min(self._bounds[target], self._bounds[staging]):
                raise IntegrityError("BOUNDED_PAYLOAD_BUDGET_FILE_CAP")
            self._pending_replacement = target, staging

    def _commit_replacement(self, path: Path, temporary: Path, data: bytes) -> None:
        with _PAYLOAD_BUDGET_LOCK:
            target, staging = path.absolute(), temporary.absolute()
            if (
                self._owner != (os.getpid(), threading.get_ident())
                or self._state != "ACTIVE"
                or _ACTIVE_PAYLOAD_BUDGET is not self
                or self._pending_replacement != (target, staging)
            ):
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_INCOMPLETE")
            self._check_directory_identities()
            self._check_replacement_identities()
            validate_payload_destination(target)
            validate_payload_destination(staging)
            identity = self._replacement_identity(staging)
            if self._written.get(staging) != len(data) or identity[2] != len(data):
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_IDENTITY_DRIFT")
            if target not in self._replacement_identities and target.exists():
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_FOREIGN_TARGET")
            os.replace(staging, target)
            if self._replacement_identity(target) != identity or target.read_bytes() != data:
                raise IntegrityError("BOUNDED_PAYLOAD_REPLACEMENT_READBACK")
            self._replacement_identities[target] = identity
            self._replacement_counts[target] = self._replacement_counts.get(target, 0) + 1
            self._written[target] = self._written.pop(staging)
            self._pending_replacement = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "scope": "CHECKED_SERIALIZERS_ONLY_NOT_NATIVE_SANDBOX_OR_ADMISSION",
            "root": str(self._root),
            "allocation_unit_bytes": self._unit,
            "maximum_allocated_bytes": self._maximum,
            "charged_bytes": self._charged,
            "reserved_file_count": len(self._written),
            "allocation_credit_bytes": 0,
            "scientific_execution_authorized": False,
        }


def json_payload_bytes(document: Mapping[str, Any]) -> bytes:
    """Bound canonical metadata, including its newline, before filesystem mutation."""
    data = canonical_json_bytes(document) + b"\n"
    if len(data) > DOCUMENT_BOUND_BYTES:
        raise IntegrityError("BOUNDED_JSON_DOCUMENT_LOGICAL_CAP_EXCEEDED")
    return data


def write_exclusive_document(path: Path, document: Mapping[str, Any]) -> None:
    """Publish metadata with the same prohibition, durability and readback checks."""
    write_exclusive_payload(path, json_payload_bytes(document))


def replace_document(path: Path, document: Mapping[str, Any]) -> None:
    """Bound both retained and temporary metadata; failed staging is never repaired."""
    replace_payload(path, json_payload_bytes(document))


def replace_payload(path: Path, data: bytes) -> None:
    """Replace through an owned finite staging lifecycle when a budget is active."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        validate_payload_destination(path)
        validate_payload_destination(temporary)
        if budget is not None:
            budget._begin_replacement(path, temporary, len(data))
        write_exclusive_payload(temporary, data)
        if budget is not None:
            budget._commit_replacement(path, temporary, data)
        else:
            validate_payload_destination(path)
            validate_payload_destination(temporary)
            os.replace(temporary, path)
            if path.read_bytes() != data:
                raise IntegrityError("BOUNDED_JSON_REPLACEMENT_READBACK")
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        raise


@contextmanager
def checkpoint_directory_publication(target: Path, *, completed_epoch: int) -> Iterator[Path]:
    """Publish an exact owned checkpoint stage; retain failed admitted staging."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    stage = target.parent / (
        f".{target.name}.epoch-{completed_epoch:03d}.tmp"
        if budget is not None
        else f".{target.name}.tmp-{uuid.uuid4().hex}"
    )
    created = False
    try:
        validate_payload_destination(target)
        validate_payload_destination(stage)
        if budget is not None:
            budget._begin_directory_publication(stage.absolute(), target.absolute())
        elif target.exists() or stage.exists():
            raise IntegrityError("checkpoint root or temporary root already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
        created = True
        if budget is not None:
            budget._check_directory_identities()
        yield stage
        if budget is not None:
            budget._commit_directory_publication(stage.absolute(), target.absolute())
        else:
            validate_payload_destination(target)
            validate_payload_destination(stage)
            os.replace(stage, target)
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        elif created and stage.exists():
            shutil.rmtree(stage)
        raise


def rotate_checkpoint_directory(source: Path, target: Path) -> None:
    """Move one owned checkpoint to its explicit finite predecessor slot."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    try:
        validate_payload_destination(source)
        validate_payload_destination(target)
        if budget is None:
            os.replace(source, target)
        else:
            budget._rotate_directory(source.absolute(), target.absolute())
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        raise


def payload_budget_active() -> bool:
    return _ACTIVE_PAYLOAD_BUDGET is not None


def dispose_owned_payload(path: Path, *, expected_sha256: str) -> None:
    """Dispose current score bytes after the caller verifies semantic custody."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    try:
        validate_payload_destination(path)
        if budget is None:
            if sha256_file(path) != expected_sha256:
                raise IntegrityError("BOUNDED_PAYLOAD_DISPOSAL_DIGEST_DRIFT")
            path.unlink()
        else:
            budget._dispose_payload(path.absolute(), expected_sha256)
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        raise


def dispose_checkpoint_directory(
    path: Path, *, preserved_manifest: Path, manifest_sha256: str
) -> None:
    """Dispose an owned managed predecessor only after successor/archive checks."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    try:
        validate_payload_destination(path)
        validate_payload_destination(preserved_manifest)
        if budget is None:
            shutil.rmtree(path)
        else:
            budget._dispose_directory(
                path.absolute(), preserved_manifest.absolute(), manifest_sha256
            )
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        raise


class BoundedJsonlWriter:
    """One owned, non-resumable log, bounded by bytes and its frozen row population.

    This covers this log only, not campaign admission or unadapted native I/O.
    Failed writes retain their bytes and poison the handle; no recovery credit.
    """

    def __init__(self, path: Path, *, maximum_records: int) -> None:
        if type(maximum_records) is not int or maximum_records < 1:
            raise IntegrityError("BOUNDED_JSONL_RECORD_POPULATION")
        validate_payload_destination(path)
        if path.exists():
            raise IntegrityError("BOUNDED_JSONL_ALREADY_EXISTS")
        self._path = path.absolute()
        self._maximum_records = maximum_records
        self._owner = (os.getpid(), threading.get_ident())
        self._payload = b""
        self._identity: tuple[int, int] | None = None
        self._records = 0
        self._failed = False
        self._sealed = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def maximum_records(self) -> int:
        return self._maximum_records

    @property
    def record_count(self) -> int:
        return self._records

    @property
    def byte_count(self) -> int:
        return len(self._payload)

    def _check_owner(self) -> None:
        if self._owner != (os.getpid(), threading.get_ident()):
            raise IntegrityError("BOUNDED_JSONL_FOREIGN_OWNER")
        if self._failed or self._sealed:
            raise IntegrityError("BOUNDED_JSONL_TERMINAL_HANDLE")

    def append(self, document: Mapping[str, Any]) -> None:
        self._check_owner()
        try:
            data = json_payload_bytes(document)
            if len(data) > JSONL_RECORD_BOUND_BYTES:
                raise IntegrityError("BOUNDED_JSONL_RECORD_BYTE_CAP")
            if self._records >= self.maximum_records:
                raise IntegrityError("BOUNDED_JSONL_RECORD_COUNT_CAP")
            expected = self._payload + data
            if len(expected) > DOCUMENT_BOUND_BYTES:
                raise IntegrityError("BOUNDED_JSONL_AGGREGATE_BYTE_CAP")
            validate_payload_destination(self.path)
            if _ACTIVE_PAYLOAD_BUDGET is not None:
                _ACTIVE_PAYLOAD_BUDGET.reserve(
                    self.path, len(expected), previous_byte_count=len(self._payload)
                )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            validate_payload_destination(self.path)
            if _ACTIVE_PAYLOAD_BUDGET is not None:
                _ACTIVE_PAYLOAD_BUDGET._check_directory_identities()
            mode = "xb+" if self._identity is None else "r+b"
            with self.path.open(mode) as stream:
                info = os.fstat(stream.fileno())
                identity = (info.st_dev, info.st_ino)
                if (
                    info.st_nlink != 1
                    or (self._identity is not None and self._identity != identity)
                    or info.st_size != len(self._payload)
                    or stream.read(DOCUMENT_BOUND_BYTES + 1) != self._payload
                ):
                    raise IntegrityError("BOUNDED_JSONL_PREFIX_DRIFT")
                self._identity = identity
                validate_payload_destination(self.path)
                observed = self.path.stat()
                if (observed.st_dev, observed.st_ino) != identity:
                    raise IntegrityError("BOUNDED_JSONL_IDENTITY_DRIFT")
                if stream.write(data) != len(data):
                    raise IntegrityError("BOUNDED_JSONL_PARTIAL_WRITE")
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                if stream.read(DOCUMENT_BOUND_BYTES + 1) != expected:
                    raise IntegrityError("BOUNDED_JSONL_READBACK")
            self._payload = expected
            self._records += 1
        except Exception:
            self._failed = True
            if _ACTIVE_PAYLOAD_BUDGET is not None:
                _ACTIVE_PAYLOAD_BUDGET._state = "FAILED"
            raise

    def seal(self) -> None:
        self._check_owner()
        try:
            if self._records != self.maximum_records:
                raise IntegrityError("BOUNDED_JSONL_TERMINAL_ROSTER_OR_DRIFT")
            validate_payload_destination(self.path)
            info = self.path.stat()
            if (
                self._records != self.maximum_records
                or (info.st_dev, info.st_ino) != self._identity
                or info.st_nlink != 1
                or info.st_size != len(self._payload)
                or self.path.read_bytes() != self._payload
            ):
                raise IntegrityError("BOUNDED_JSONL_TERMINAL_ROSTER_OR_DRIFT")
        except Exception:
            self._failed = True
            raise
        self._sealed = True


def torch_payload_bytes(payload: Any, *, pickle_protocol: int = 2) -> bytes:
    """Serialize a checkpoint before touching disk and enforce the fixed cap."""
    stream = io.BytesIO()
    torch.save(payload, stream, pickle_protocol=pickle_protocol)
    data = stream.getvalue()
    if len(data) > policy_caps()["checkpoint"]:
        raise IntegrityError("BOUNDED_TORCH_CHECKPOINT_LOGICAL_CAP_EXCEEDED")
    return data


def numpy_payload_bytes(array: np.ndarray[Any, Any]) -> bytes:
    """Serialize one score chunk before touching disk and enforce its cap."""
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    data = stream.getvalue()
    if len(data) > policy_caps()["scores"]:
        raise IntegrityError("BOUNDED_NUMPY_SCORE_LOGICAL_CAP_EXCEEDED")
    return data


def score_output_bound_bytes(*, user_count: int, candidate_count: int, chunk_size: int) -> int:
    """Preflight all primitive float32 chunks and one bounded manifest.

    The existing native serializer proof bounds each NPY header by256 bytes.
    This is a logical bound, not allocation rounding, staging or admission.
    """
    if any(
        type(value) is not int or value < 1 for value in (user_count, candidate_count, chunk_size)
    ):
        raise IntegrityError("BOUNDED_SCORE_OUTPUT_POPULATION")
    chunks = (user_count + chunk_size - 1) // chunk_size
    bound = user_count * candidate_count * 4 + chunks * 256 + DOCUMENT_BOUND_BYTES
    if bound > policy_caps()["scores"]:
        raise IntegrityError("BOUNDED_SCORE_AGGREGATE_LOGICAL_CAP")
    return bound


def validate_payload_destination(path: Path) -> None:
    """Reject aliases and current prohibitions before any directory is created."""
    from ai_service_v2.training.cost_runtime_custody import reject_reparse_path

    parts = path.parts[1:] if path.anchor else path.parts
    safe_name("/".join(parts))
    reject_withdrawn_engineering_root(path.absolute())
    with _PAYLOAD_BUDGET_LOCK:
        scope = _ACTIVE_CAMPAIGN_OUTPUT
    if scope is not None:
        root, owner = scope
        if owner != (os.getpid(), threading.get_ident()):
            raise IntegrityError("CAMPAIGN_OUTPUT_FOREIGN_WRITER")
        reject_reparse_path(path)
        if path.absolute() != path.resolve() or not path.absolute().is_relative_to(root):
            raise IntegrityError("CAMPAIGN_OUTPUT_PATH_OUTSIDE_NAMESPACE")


def write_exclusive_payload(path: Path, data: bytes) -> None:
    """Write bounded bytes with durable flush and exact readback."""
    budget = _ACTIVE_PAYLOAD_BUDGET
    try:
        validate_payload_destination(path)
        if len(data) > max(policy_caps()["checkpoint"], policy_caps()["scores"]):
            raise IntegrityError("BOUNDED_SERIALIZATION_LOGICAL_CAP_EXCEEDED")
        if budget is not None:
            budget.reserve(path, len(data))
        path.parent.mkdir(parents=True, exist_ok=True)
        validate_payload_destination(path)
        if budget is not None:
            budget._check_directory_identities()
        with path.open("xb") as stream:
            if stream.write(data) != len(data):
                raise IntegrityError("BOUNDED_SERIALIZATION_PARTIAL_WRITE")
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != data:
            raise IntegrityError("BOUNDED_SERIALIZATION_READBACK")
        if budget is not None:
            budget._record_publication_file(path)
    except BaseException:
        if budget is not None:
            budget._state = "FAILED"
        raise
