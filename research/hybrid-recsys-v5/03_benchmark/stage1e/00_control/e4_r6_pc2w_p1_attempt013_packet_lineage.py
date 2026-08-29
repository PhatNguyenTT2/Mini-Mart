"""Pure packet-lineage predicate for Attempt-013 Revision 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Any


CONTROL_PREFIX = (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
)
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


class PacketLineageError(ValueError):
    """Stable fail-closed error from the public lineage seam."""

    def __init__(self, code: str, facts: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.facts = dict(facts or {})


@dataclass(frozen=True, order=True)
class DeltaEntry:
    status: str
    path: str


@dataclass(frozen=True)
class PacketBlobFact:
    path: str
    raw_bytes: int
    raw_sha256: str


@dataclass(frozen=True)
class OriginBinding:
    path: str
    origin_commit: str
    origin_raw_bytes: int
    origin_raw_sha256: str
    final_raw_bytes: int
    final_raw_sha256: str


@dataclass(frozen=True)
class PacketLineageSpec:
    aggregate_roster: tuple[str, ...]
    frozen_r0_bindings: tuple[OriginBinding, ...]
    support_bindings: tuple[OriginBinding, ...]
    sealing_parent: str
    expected_sealing_delta: tuple[DeltaEntry, ...]


@dataclass(frozen=True)
class PacketLineageObservation:
    packet_commit: str
    packet_parents: tuple[str, ...]
    observed_sealing_delta: tuple[DeltaEntry, ...]
    final_packet_blobs: tuple[PacketBlobFact, ...]
    packet_is_ancestor_of_execution_head: bool


@dataclass(frozen=True)
class PacketLineageEvidence:
    packet_commit: str
    sealing_parent: str
    aggregate_roster_count: int
    frozen_r0_count: int
    support_count: int
    sealing_delta_count: int
    predicate_passed: bool


def _fail(code: str, **facts: Any) -> None:
    raise PacketLineageError(code, facts)


def _validate_commit(value: str, label: str) -> str:
    normalized = value.casefold()
    if value != normalized or HEX40.fullmatch(normalized) is None:
        _fail("INVALID_COMMIT_ID", label=label, value=value)
    return normalized


def _validate_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value.startswith(CONTROL_PREFIX)
        or path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail("INVALID_PACKET_PATH", path=value)
    return value


def _unique_paths(paths: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(_validate_path(path) for path in paths)
    folded = [path.casefold() for path in normalized]
    if len(folded) != len(set(folded)):
        _fail("DUPLICATE_PACKET_PATH", label=label)
    return normalized


def _validate_sha(value: str, label: str) -> str:
    normalized = value.casefold()
    if value != normalized or HEX64.fullmatch(normalized) is None:
        _fail("INVALID_SHA256", label=label)
    return normalized


def _validate_delta(entries: tuple[DeltaEntry, ...], label: str) -> tuple[DeltaEntry, ...]:
    paths = _unique_paths(tuple(entry.path for entry in entries), label)
    result = []
    for entry, path in zip(entries, paths, strict=True):
        if entry.status not in {"A", "M", "D"}:
            _fail("INVALID_DELTA_STATUS", label=label, status=entry.status, path=path)
        result.append(DeltaEntry(entry.status, path))
    return tuple(sorted(result))


def _validate_binding(binding: OriginBinding, label: str) -> None:
    _validate_path(binding.path)
    _validate_commit(binding.origin_commit, f"{label}.origin_commit")
    if binding.origin_raw_bytes < 0 or binding.final_raw_bytes < 0:
        _fail("INVALID_BLOB_BYTES", label=label, path=binding.path)
    _validate_sha(binding.origin_raw_sha256, f"{label}.origin_raw_sha256")
    _validate_sha(binding.final_raw_sha256, f"{label}.final_raw_sha256")
    if (
        binding.origin_raw_bytes != binding.final_raw_bytes
        or binding.origin_raw_sha256 != binding.final_raw_sha256
    ):
        _fail("ORIGIN_BLOB_DRIFT", label=label, path=binding.path)


def _validate_blob_fact(fact: PacketBlobFact) -> None:
    _validate_path(fact.path)
    if fact.raw_bytes < 0:
        _fail("INVALID_BLOB_BYTES", label="final_packet_blob", path=fact.path)
    _validate_sha(fact.raw_sha256, "final_packet_blob.raw_sha256")


def validate_packet_lineage(
    spec: PacketLineageSpec,
    observed: PacketLineageObservation,
) -> PacketLineageEvidence:
    """Validate immutable packet lineage without performing any I/O."""

    packet_commit = _validate_commit(observed.packet_commit, "packet_commit")
    sealing_parent = _validate_commit(spec.sealing_parent, "sealing_parent")
    parents = tuple(
        _validate_commit(parent, "packet_parent") for parent in observed.packet_parents
    )
    if parents != (sealing_parent,):
        _fail(
            "PACKET_PARENT_MISMATCH",
            expected_parent=sealing_parent,
            observed_parents=parents,
        )

    roster = _unique_paths(spec.aggregate_roster, "aggregate_roster")
    for binding in spec.frozen_r0_bindings:
        _validate_binding(binding, "frozen_r0")
    for binding in spec.support_bindings:
        _validate_binding(binding, "support")

    observed_delta = _validate_delta(
        observed.observed_sealing_delta, "observed_sealing_delta"
    )

    expected_delta = _validate_delta(
        spec.expected_sealing_delta, "expected_sealing_delta"
    )
    frozen_paths = _unique_paths(
        tuple(binding.path for binding in spec.frozen_r0_bindings),
        "frozen_r0_bindings",
    )
    support_paths = _unique_paths(
        tuple(binding.path for binding in spec.support_bindings),
        "support_bindings",
    )
    sealing_paths = tuple(entry.path for entry in expected_delta)
    partition = (*frozen_paths, *support_paths, *sealing_paths)
    folded_partition = tuple(path.casefold() for path in partition)
    if (
        len(folded_partition) != len(set(folded_partition))
        or set(folded_partition) != {path.casefold() for path in roster}
    ):
        _fail(
            "ROSTER_PARTITION_MISMATCH",
            aggregate_roster_count=len(roster),
            partition_count=len(partition),
        )
    for fact in observed.final_packet_blobs:
        _validate_blob_fact(fact)
    final_blob_paths = _unique_paths(
        tuple(fact.path for fact in observed.final_packet_blobs),
        "final_packet_blobs",
    )
    if {path.casefold() for path in final_blob_paths} != {
        path.casefold() for path in roster
    }:
        _fail(
            "FINAL_BLOB_ROSTER_MISMATCH",
            aggregate_roster_count=len(roster),
            final_blob_count=len(final_blob_paths),
        )
    final_by_path = {
        fact.path.casefold(): fact for fact in observed.final_packet_blobs
    }
    for binding in (*spec.frozen_r0_bindings, *spec.support_bindings):
        fact = final_by_path[binding.path.casefold()]
        if (
            fact.raw_bytes != binding.final_raw_bytes
            or fact.raw_sha256 != binding.final_raw_sha256
        ):
            _fail("FINAL_BLOB_BINDING_MISMATCH", path=binding.path)
    if observed_delta != expected_delta:
        _fail(
            "SEALING_DELTA_MISMATCH",
            aggregate_roster_count=len(roster),
            expected_seal_rows=len(expected_delta),
            expected_seal_statuses=tuple(sorted({row.status for row in expected_delta})),
            observed_seal_rows=len(observed_delta),
            observed_seal_statuses=tuple(sorted({row.status for row in observed_delta})),
            frozen_r0_count=len(spec.frozen_r0_bindings),
        )

    if observed.packet_is_ancestor_of_execution_head is not True:
        _fail("PACKET_NOT_ANCESTOR_OF_EXECUTION_HEAD")

    return PacketLineageEvidence(
        packet_commit=packet_commit,
        sealing_parent=sealing_parent,
        aggregate_roster_count=len(roster),
        frozen_r0_count=len(spec.frozen_r0_bindings),
        support_count=len(spec.support_bindings),
        sealing_delta_count=len(expected_delta),
        predicate_passed=True,
    )
