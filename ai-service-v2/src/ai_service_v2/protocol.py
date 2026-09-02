"""Frozen split, eligibility, candidate, and masking preparation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ai_service_v2.contracts import DatasetManifest, ProtocolManifest
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError, ProtocolError, ScoreError
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, load_strict_json


@dataclass(frozen=True)
class UserEvaluationCase:
    user_id: int
    history_item_ids: frozenset[int]
    positive_item_ids: frozenset[int]


@dataclass(frozen=True)
class PreparedProtocol:
    """A protocol with all user truth and masking inputs frozen."""

    manifest: ProtocolManifest
    raw_item_ids: tuple[int, ...]
    cases: dict[int, UserEvaluationCase]
    num_total_users: int

    @property
    def candidate_item_ids(self) -> tuple[int, ...]:
        return self.manifest.candidate_item_ids

    @property
    def eligible_user_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self.cases))

    def case_for(self, user_id: int) -> UserEvaluationCase:
        try:
            return self.cases[user_id]
        except KeyError as error:
            raise ProtocolError(f"user is not eligible: {user_id}") from error

    def mask_scores(self, user_id: int, scores: np.ndarray) -> np.ndarray:
        """Apply the frozen seen-item mask without changing the input array."""

        values = np.asarray(scores, dtype=np.float64)
        if values.ndim != 1 or values.shape[0] != len(self.candidate_item_ids):
            raise ScoreError("score vector shape does not match candidate catalog")
        if not np.isfinite(values).all():
            raise ScoreError("model emitted NaN or non-finite scores")
        masked = values.copy()
        position = {item_id: index for index, item_id in enumerate(self.candidate_item_ids)}
        for item_id in self.case_for(user_id).history_item_ids:
            try:
                masked[position[item_id]] = -np.inf
            except KeyError as error:
                raise ProtocolError("history item is outside the candidate catalog") from error
        return masked

    def to_mapping(self) -> dict[str, Any]:
        """Return the complete replayable protocol document payload."""

        return prepared_protocol_mapping(self)


def _manifest_hash(manifest: DatasetManifest) -> str:
    return canonical_json_sha256(manifest.to_mapping())


def protocol_manifest_sha256(protocol: PreparedProtocol) -> str:
    """Hash only the frozen ``ProtocolManifest`` portion of a protocol."""

    return canonical_json_sha256(protocol.manifest.to_mapping())


def prepared_protocol_mapping(protocol: PreparedProtocol) -> dict[str, Any]:
    """Serialize truth, masking and ordering inputs without model state."""

    cases = [
        {
            "user_id": user_id,
            "history_item_ids": sorted(protocol.cases[user_id].history_item_ids),
            "positive_item_ids": sorted(protocol.cases[user_id].positive_item_ids),
        }
        for user_id in protocol.eligible_user_ids
    ]
    return {
        "schema_version": "prepared-protocol/1.0",
        "manifest": protocol.manifest.to_mapping(),
        "raw_item_ids": list(protocol.raw_item_ids),
        "cases": cases,
        "num_total_users": protocol.num_total_users,
        "protocol_manifest_sha256": protocol_manifest_sha256(protocol),
    }


def _protocol_file(path: Path) -> Path:
    return path / "protocol.json" if path.is_dir() else path


def save_protocol(protocol: PreparedProtocol, path: Path) -> Path:
    """Write one immutable, self-contained protocol document."""

    target = _protocol_file(path)
    if target.exists():
        raise IntegrityError(f"protocol output already exists: {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json_bytes(prepared_protocol_mapping(protocol)) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write protocol: {target}") from error
    return target


def _parse_id_list(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value
    ):
        raise IntegrityError(f"{name} must be a list of non-negative integers")
    if len(set(value)) != len(value):
        raise IntegrityError(f"{name} must not contain duplicate IDs")
    return tuple(value)


def load_protocol(path: Path, *, snapshot: Snapshot | None = None) -> PreparedProtocol:
    """Load and replay a protocol, optionally against a verified snapshot."""

    source = _protocol_file(path)
    document = load_strict_json(source)
    required = {
        "schema_version",
        "manifest",
        "raw_item_ids",
        "cases",
        "num_total_users",
        "protocol_manifest_sha256",
    }
    if set(document) != required:
        raise IntegrityError("protocol document fields do not match schema")
    if document["schema_version"] != "prepared-protocol/1.0":
        raise IntegrityError("unsupported prepared protocol schema")
    if not isinstance(document["manifest"], dict):
        raise IntegrityError("protocol manifest must be an object")
    manifest = ProtocolManifest.from_mapping(document["manifest"])
    raw_item_ids = _parse_id_list(document["raw_item_ids"], "raw_item_ids")
    total_users = document["num_total_users"]
    if isinstance(total_users, bool) or not isinstance(total_users, int) or total_users < 1:
        raise IntegrityError("num_total_users must be a positive integer")
    declared_hash = document["protocol_manifest_sha256"]
    if not isinstance(declared_hash, str) or declared_hash != canonical_json_sha256(
        manifest.to_mapping()
    ):
        raise IntegrityError("protocol manifest hash does not match manifest")

    raw_cases = document["cases"]
    if not isinstance(raw_cases, list):
        raise IntegrityError("protocol cases must be a list")
    cases: dict[int, UserEvaluationCase] = {}
    candidates = set(manifest.candidate_item_ids)
    for value in raw_cases:
        if not isinstance(value, dict) or set(value) != {
            "user_id",
            "history_item_ids",
            "positive_item_ids",
        }:
            raise IntegrityError("protocol case fields do not match schema")
        user_id = value["user_id"]
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 0:
            raise IntegrityError("protocol case user_id is invalid")
        if user_id in cases:
            raise IntegrityError("protocol cases contain duplicate users")
        history = _parse_id_list(value["history_item_ids"], "history_item_ids")
        positives = _parse_id_list(value["positive_item_ids"], "positive_item_ids")
        if not positives or set(history) & set(positives):
            raise IntegrityError("protocol case history and positives must be disjoint")
        if not set(history) <= candidates or not set(positives) <= candidates:
            raise IntegrityError("protocol case references an unknown candidate")
        cases[user_id] = UserEvaluationCase(
            user_id=user_id,
            history_item_ids=frozenset(history),
            positive_item_ids=frozenset(positives),
        )
    if tuple(sorted(cases)) != tuple(case["user_id"] for case in raw_cases):
        raise IntegrityError("protocol cases must be ordered by user_id")
    if len(raw_item_ids) != len(manifest.candidate_item_ids):
        raise IntegrityError("raw_item_ids and candidate catalog lengths differ")
    if (
        canonical_json_sha256(
            {
                "internal_item_ids": list(manifest.candidate_item_ids),
                "raw_item_ids": list(raw_item_ids),
            }
        )
        != manifest.candidate_order_sha256
    ):
        raise IntegrityError("protocol candidate order hash does not match catalog")

    protocol = PreparedProtocol(manifest, raw_item_ids, cases, total_users)
    if snapshot is not None:
        expected = build_protocol(
            snapshot,
            split=manifest.split,
            allow_test=manifest.test_set_opened,
            cutoff=manifest.cutoff,
            metric_version=manifest.metric_version,
        )
        if manifest.dataset_id != snapshot.manifest.dataset_id:
            raise IntegrityError("protocol dataset ID does not match snapshot")
        if manifest.dataset_manifest_sha256 != _manifest_hash(snapshot.manifest):
            raise IntegrityError("protocol dataset manifest hash does not match snapshot")
        if manifest.to_mapping() != expected.manifest.to_mapping():
            raise IntegrityError("protocol manifest cannot be replayed from snapshot")
        if protocol.raw_item_ids != expected.raw_item_ids or protocol.cases != expected.cases:
            raise IntegrityError("protocol cases cannot be replayed from snapshot")
        if protocol.num_total_users != expected.num_total_users:
            raise IntegrityError("protocol total user count does not match snapshot")
    return protocol


def build_protocol(
    snapshot: Snapshot,
    *,
    dataset_manifest_sha256: str | None = None,
    split: str,
    allow_test: bool = False,
    cutoff: int = 10,
    metric_version: str = "ranking-v1",
) -> PreparedProtocol:
    """Prepare one validation or test protocol from a verified snapshot.

    Validation uses TRAIN as history.  TEST uses TRAIN+VAL as history and is
    rejected unless ``allow_test`` is explicitly true.  No method or scorer is
    called while this function derives eligibility and truth.
    """

    if split not in {"val", "test"}:
        raise ProtocolError("only val and test protocols are supported")
    if split == "test" and not allow_test:
        raise ProtocolError("TEST is sealed; explicit allow_test=True is required")
    if cutoff < 1 or cutoff > snapshot.manifest.num_items:
        raise ProtocolError("cutoff must be inside the catalog")

    history = snapshot.history_events(split)
    target = snapshot.target_events(split)
    history_by_user: dict[int, set[int]] = {user: set() for user in snapshot.users}
    for event in history:
        history_by_user[event.user_id].add(event.item_id)
    target_by_user: dict[int, set[int]] = {user: set() for user in snapshot.users}
    for event in target:
        if event.event_type == "purchase" and event.event_origin == "organic":
            target_by_user[event.user_id].add(event.item_id)

    cases: dict[int, UserEvaluationCase] = {}
    for user in snapshot.users:
        novel = target_by_user[user] - history_by_user[user]
        if novel:
            cases[user] = UserEvaluationCase(
                user_id=user,
                history_item_ids=frozenset(history_by_user[user]),
                positive_item_ids=frozenset(novel),
            )

    candidate_ids = tuple(snapshot.items)
    candidate_hash = canonical_json_sha256(
        {
            "internal_item_ids": list(candidate_ids),
            "raw_item_ids": list(snapshot.raw_item_ids),
        }
    )
    opened = split == "test"
    protocol_manifest = ProtocolManifest(
        protocol_id=f"{snapshot.manifest.dataset_id}:{split}:full-catalog-v1",
        dataset_id=snapshot.manifest.dataset_id,
        dataset_manifest_sha256=dataset_manifest_sha256 or _manifest_hash(snapshot.manifest),
        split=split,
        split_hash=snapshot.manifest.split_hashes[split],
        candidate_item_ids=candidate_ids,
        candidate_order_sha256=candidate_hash,
        eligible_user_rule="user_has_at_least_one_novel_organic_purchase_in_target_split",
        positive_rule="organic_purchase_events_minus_all_history_items",
        seen_masking="all_prior_interacted_items_to_negative_infinity",
        cutoff=cutoff,
        tie_break="descending_score_then_ascending_raw_product_id",
        metric_version=metric_version,
        test_set_opened=opened,
    )
    return PreparedProtocol(
        manifest=protocol_manifest,
        raw_item_ids=snapshot.raw_item_ids,
        cases=cases,
        num_total_users=snapshot.manifest.num_users,
    )


def protocol_for_each_split(
    snapshot: Snapshot,
    builder: Callable[..., PreparedProtocol] = build_protocol,
) -> dict[str, PreparedProtocol]:
    """Build validation and test only when the caller explicitly opens TEST."""

    return {
        "val": builder(snapshot, split="val"),
    }


__all__ = [
    "PreparedProtocol",
    "UserEvaluationCase",
    "build_protocol",
    "load_protocol",
    "prepared_protocol_mapping",
    "protocol_for_each_split",
    "protocol_manifest_sha256",
    "save_protocol",
]
