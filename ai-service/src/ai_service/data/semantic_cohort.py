"""Typed semantic-trap cohort construction and verification for v5 snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, model_validator

from ai_service.contracts import SplitName
from ai_service.data.benchmark_spec import VerifiedBenchmarkSpec
from ai_service.errors import ArtifactIntegrityError


class SemanticCohortCase(BaseModel):
    """One immutable anchor-to-target replay request."""

    trap_id: int = Field(ge=1, le=10)
    user_id: int = Field(gt=0)
    anchor_product_id: int = Field(gt=0)
    target_product_id: int = Field(gt=0)
    split: Literal["val", "test"]
    anchor_event_id: str = Field(min_length=1)
    target_event_id: str = Field(min_length=1)
    anchor_event_ts: datetime
    target_event_ts: datetime

    @model_validator(mode="after")
    def anchor_precedes_target(self) -> SemanticCohortCase:
        if self.anchor_event_ts.tzinfo is None or self.target_event_ts.tzinfo is None:
            raise ValueError("semantic cohort timestamps must be timezone-aware")
        if self.anchor_event_ts >= self.target_event_ts:
            raise ValueError("semantic cohort anchor must precede its target")
        if self.anchor_event_id == self.target_event_id:
            raise ValueError("semantic cohort anchor and target events must differ")
        return self


class SemanticCohortDocument(BaseModel):
    """The only accepted v5 wire document for semantic evaluation."""

    schema_version: Literal["1.0.0"]
    benchmark_run_id: str = Field(min_length=1)
    benchmark_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cases: tuple[SemanticCohortCase, ...]

    @model_validator(mode="after")
    def cases_are_unique_and_complete(self) -> SemanticCohortDocument:
        if not self.cases:
            raise ValueError("semantic cohort document has no cases")
        key = {(case.split, case.trap_id, case.user_id, case.target_product_id) for case in self.cases}
        if len(key) != len(self.cases):
            raise ValueError("semantic cohort document contains duplicate target cases")
        if {case.trap_id for case in self.cases} != set(range(1, 11)):
            raise ValueError("semantic cohort document must contain all ten trap IDs")
        if {case.split for case in self.cases} != {"val", "test"}:
            raise ValueError("semantic cohort document must contain VAL and TEST cases")
        return self


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ArtifactIntegrityError("semantic cohort object keys must be strings")
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_canonical_value(item) for item in value]
    raise ArtifactIntegrityError("semantic cohort contains an unsupported JSON value")


def canonical_semantic_cohort_bytes(document: Mapping[str, object]) -> bytes:
    """Encode a cohort document as canonical compact UTF-8 JSON."""

    try:
        return json.dumps(
            _canonical_value(document),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ArtifactIntegrityError("semantic cohort cannot be canonicalized") from error


def cases_for_split(
    document: SemanticCohortDocument,
    split: SplitName | Literal["val", "test"],
) -> tuple[SemanticCohortCase, ...]:
    """Return the immutable, deterministically ordered replay cases for one split."""

    split_value = split.value if isinstance(split, SplitName) else split
    if split_value not in {"val", "test"}:
        raise ArtifactIntegrityError("semantic cohort supports only VAL and TEST")
    cases = tuple(case for case in document.cases if case.split == split_value)
    if not cases:
        raise ArtifactIntegrityError("semantic cohort has no cases for requested split")
    return cases


def load_semantic_cohort(
    snapshot_dir: Path,
    *,
    expected_sha256: str | None = None,
) -> SemanticCohortDocument:
    """Strict-load one snapshot-owned typed semantic cohort document."""

    path = snapshot_dir / "semantic-cohort.json"
    if not path.is_file():
        raise ArtifactIntegrityError("snapshot semantic cohort is missing")
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ArtifactIntegrityError("snapshot semantic cohort cannot be parsed") from error
    if not isinstance(document, dict):
        raise ArtifactIntegrityError("snapshot semantic cohort must be a typed document object")
    canonical = canonical_semantic_cohort_bytes(document)
    if raw != canonical:
        raise ArtifactIntegrityError("snapshot semantic cohort is not canonical")
    actual_sha256 = hashlib.sha256(canonical).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ArtifactIntegrityError("snapshot semantic cohort checksum mismatch")
    try:
        return SemanticCohortDocument.model_validate(document)
    except (TypeError, ValueError) as error:
        raise ArtifactIntegrityError(f"snapshot semantic cohort typed document is invalid: {error}") from error


def _as_utc_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif hasattr(value, "to_pydatetime"):
        result = value.to_pydatetime()  # type: ignore[union-attr]
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ArtifactIntegrityError("semantic cohort event timestamp is invalid")
    if result.tzinfo is None:
        raise ArtifactIntegrityError("semantic cohort event timestamp is timezone-naive")
    return result.astimezone(UTC)


def _trap_id(value: object) -> int:
    match = re.fullmatch(r"semantic-(\d+)", str(value))
    if match is None:
        raise ArtifactIntegrityError("semantic cohort event has an invalid cohort ID")
    trap_id = int(match.group(1))
    if trap_id not in range(1, 11):
        raise ArtifactIntegrityError("semantic cohort event has an invalid trap ID")
    return trap_id


def _event_record(row: Mapping[str, object], *, trap_id: int) -> dict[str, object]:
    try:
        return {
            "trap_id": trap_id,
            "user_id": int(row["user_id"]),
            "product_id": int(row["product_id"]),
            "event_id": str(row["event_id"]),
            "event_ts": _as_utc_datetime(row["event_ts"]),
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("semantic cohort event row is malformed") from error


def build_semantic_cohort(
    events: pd.DataFrame,
    *,
    benchmark_run_id: str,
    spec: VerifiedBenchmarkSpec,
) -> SemanticCohortDocument:
    """Build the 2,000 typed cases from the Node-owned session identifiers."""

    required = {"event_id", "user_id", "product_id", "event_ts", "session_id", "event_origin", "cohort_id"}
    if missing := required - set(events.columns):
        raise ArtifactIntegrityError(f"semantic cohort source is missing columns: {sorted(missing)}")
    pattern = re.compile(
        rf"^{re.escape(benchmark_run_id)}:(val|test):semantic_trap:(anchor|target):(\d+)$"
    )
    anchors: dict[tuple[str, int], dict[str, object]] = {}
    targets: dict[tuple[str, int], dict[str, object]] = {}
    semantic_rows = events.loc[events["event_origin"].astype(str) == "semantic_trap"]
    for row in semantic_rows.to_dict(orient="records"):
        session_id = str(row["session_id"])
        match = pattern.fullmatch(session_id)
        if match is None:
            if session_id.startswith(f"{benchmark_run_id}:train:semantic:"):
                continue
            raise ArtifactIntegrityError("semantic cohort event has an invalid session ID")
        split, phase, index_text = match.groups()
        trap_id = _trap_id(row["cohort_id"])
        key = (split, int(index_text))
        destination = anchors if phase == "anchor" else targets
        if key in destination:
            raise ArtifactIntegrityError("semantic cohort session contains duplicate phase events")
        destination[key] = _event_record(row, trap_id=trap_id)
    cases: list[SemanticCohortCase] = []
    for target_key, target in targets.items():
        split, index = target_key
        anchor_key = ("train" if split == "val" else "val", index)
        anchor = anchors.get(anchor_key)
        if anchor is None:
            raise ArtifactIntegrityError("semantic cohort target has no paired anchor session")
        if anchor["trap_id"] != target["trap_id"] or anchor["user_id"] != target["user_id"]:
            raise ArtifactIntegrityError("semantic cohort anchor/target lineage differs")
        cases.append(
            SemanticCohortCase(
                trap_id=int(target["trap_id"]),
                user_id=int(target["user_id"]),
                anchor_product_id=int(anchor["product_id"]),
                target_product_id=int(target["product_id"]),
                split=split,
                anchor_event_id=str(anchor["event_id"]),
                target_event_id=str(target["event_id"]),
                anchor_event_ts=anchor["event_ts"],
                target_event_ts=target["event_ts"],
            )
        )
    if len(anchors) != len(targets):
        raise ArtifactIntegrityError("semantic cohort has an unpaired anchor session")
    document = SemanticCohortDocument(
        schema_version="1.0.0",
        benchmark_run_id=benchmark_run_id,
        benchmark_spec_sha256=spec.sha256,
        cases=tuple(
            sorted(
                cases,
                key=lambda case: (
                    case.split,
                    case.trap_id,
                    case.user_id,
                    case.target_product_id,
                ),
            )
        ),
    )
    validate_semantic_cohort(document, spec=spec)
    return document


def validate_semantic_cohort(
    document: SemanticCohortDocument,
    *,
    spec: VerifiedBenchmarkSpec,
    train: pd.DataFrame | None = None,
    val: pd.DataFrame | None = None,
    test: pd.DataFrame | None = None,
) -> None:
    """Bind typed cases to the verified spec and, when provided, frozen splits."""

    if document.benchmark_spec_sha256 != spec.sha256:
        raise ArtifactIntegrityError("semantic cohort spec hash differs from benchmark spec")
    trap_by_id = {trap.trap_id: trap for trap in spec.semantic_traps}
    split_counts = {"val": spec.validation_users_per_trap, "test": spec.test_users_per_trap}
    for split, expected_count in split_counts.items():
        split_cases = cases_for_split(document, split)
        for trap_id in range(1, 11):
            cases = tuple(case for case in split_cases if case.trap_id == trap_id)
            if len(cases) != expected_count:
                raise ArtifactIntegrityError(
                    f"semantic cohort {split} trap {trap_id} has {len(cases)} cases; "
                    f"expected {expected_count}"
                )
            trap = trap_by_id[trap_id]
            if any(case.anchor_product_id != trap.anchor for case in cases):
                raise ArtifactIntegrityError("semantic cohort anchor differs from verified trap spec")
            if {case.target_product_id for case in cases} - set(trap.targets):
                raise ArtifactIntegrityError("semantic cohort target differs from verified trap spec")
            if {case.target_product_id for case in cases} != set(trap.targets):
                raise ArtifactIntegrityError("semantic cohort does not cover every target direction")
    if train is None or val is None or test is None:
        return
    required = {"event_id", "user_id", "product_id", "event_ts"}
    if any(required - set(frame.columns) for frame in (train, val, test)):
        raise ArtifactIntegrityError("snapshot splits cannot verify semantic cohort events")
    by_event: dict[str, dict[str, object]] = {}
    for frame in (train, val, test):
        for row in frame.to_dict(orient="records"):
            event_id = str(row["event_id"])
            if event_id in by_event:
                raise ArtifactIntegrityError("snapshot splits contain duplicate event IDs")
            by_event[event_id] = row
    test_history = pd.concat((train, val), ignore_index=True)
    for case in document.cases:
        anchor = by_event.get(case.anchor_event_id)
        target = by_event.get(case.target_event_id)
        if anchor is None or target is None:
            raise ArtifactIntegrityError("semantic cohort event is absent from snapshot splits")
        if (
            int(anchor["user_id"]) != case.user_id
            or int(anchor["product_id"]) != case.anchor_product_id
            or _as_utc_datetime(anchor["event_ts"]) != case.anchor_event_ts
            or int(target["user_id"]) != case.user_id
            or int(target["product_id"]) != case.target_product_id
            or _as_utc_datetime(target["event_ts"]) != case.target_event_ts
        ):
            raise ArtifactIntegrityError("semantic cohort event fields differ from snapshot splits")
        history = train if case.split == "val" else test_history
        prior = history.loc[
            (history["user_id"].astype(int) == case.user_id)
            & (history["product_id"].astype(int) == case.target_product_id)
        ]
        if not prior.empty:
            raise ArtifactIntegrityError("semantic cohort target is not novel before its split")


__all__ = [
    "SemanticCohortCase",
    "SemanticCohortDocument",
    "build_semantic_cohort",
    "canonical_semantic_cohort_bytes",
    "cases_for_split",
    "load_semantic_cohort",
    "validate_semantic_cohort",
]
