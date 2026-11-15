"""Scalable TRAIN-only pair-association rule artifacts for confirmatory runs."""

from __future__ import annotations

import math
import sqlite3
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np

from ai_service_v2.adapters.instacart import InstacartTrainingBasket
from ai_service_v2.array_types import Array
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    load_strict_json,
    sha256_file,
)
from ai_service_v2.protocol import EvaluationProtocol

SUPPORT_FRACTIONS = frozenset({0.0005, 0.001, 0.002})


class RuleTrainingView(Protocol):
    manifest_sha256: str
    raw_item_ids: tuple[int, ...]

    @property
    def test_access_state(self) -> str: ...

    def iter_train_baskets(self) -> Iterator[InstacartTrainingBasket]: ...


@dataclass(frozen=True)
class PairRuleTable:
    """Memory-mapped one-item-to-one-item confidence rules."""

    root: Path
    manifest_sha256: str
    num_items: int
    basket_count: int
    min_support_fraction: float
    min_support_count: int
    pair_count: int
    candidate_order_sha256: str
    context_counts: Array
    offsets: Array
    candidate_ids: Array
    confidences: Array
    support_counts: Array

    def close(self) -> None:
        """Release NumPy memory maps before artifact cleanup on Windows."""

        for values in (
            self.context_counts,
            self.offsets,
            self.candidate_ids,
            self.confidences,
            self.support_counts,
        ):
            memory_map = getattr(values, "_mmap", None)
            if memory_map is not None:
                memory_map.close()

    @property
    def antecedent_ids(self) -> tuple[int, ...]:
        counts = np.asarray(self.offsets[1:] - self.offsets[:-1])
        return tuple(int(value) for value in np.flatnonzero(counts > 0))

    def has_antecedent(self, history_item_ids: frozenset[int] | set[int]) -> bool:
        for item_id in history_item_ids:
            if item_id < 0 or item_id >= self.num_items:
                raise ContractError("rule history contains an item outside the catalog")
            if int(self.offsets[item_id + 1]) > int(self.offsets[item_id]):
                return True
        return False

    def score(
        self,
        history_item_ids: frozenset[int] | set[int],
        candidate_item_ids: tuple[int, ...],
    ) -> Array:
        if candidate_item_ids != tuple(range(self.num_items)):
            raise ContractError("rule scorer requires the frozen dense candidate order")
        result = np.zeros(self.num_items, dtype=np.float32)
        for context_id in sorted(history_item_ids):
            if context_id < 0 or context_id >= self.num_items:
                raise ContractError("rule history contains an item outside the catalog")
            first = int(self.offsets[context_id])
            last = int(self.offsets[context_id + 1])
            if first == last:
                continue
            candidates = np.asarray(self.candidate_ids[first:last], dtype=np.int64)
            confidence = np.asarray(self.confidences[first:last], dtype=np.float32)
            np.add.at(result, candidates, confidence)
        if not np.isfinite(result).all():
            raise IntegrityError("rule scoring produced a non-finite value")
        return cast(Array, result)


def _artifact_row(root: Path, path: Path, role: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "role": role,
        "contains_validation_or_test_outcomes": False,
    }


def _write_array(path: Path, values: Array) -> None:
    try:
        with path.open("wb") as stream:
            np.save(stream, values, allow_pickle=False)
    except OSError as error:
        raise IntegrityError(f"cannot write pair-rule array: {path}") from error


def _flush_pairs(
    connection: sqlite3.Connection,
    pair_counts: Counter[tuple[int, int]],
) -> None:
    if not pair_counts:
        return
    connection.executemany(
        "INSERT INTO pair_counts(context_id, candidate_id, support_count) "
        "VALUES (?, ?, ?) ON CONFLICT(context_id, candidate_id) DO UPDATE SET "
        "support_count = support_count + excluded.support_count",
        ((left, right, count) for (left, right), count in pair_counts.items()),
    )
    connection.commit()
    pair_counts.clear()


def _validate_fraction(value: float) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed not in SUPPORT_FRACTIONS:
        raise ContractError("pair-rule support fraction is outside the frozen grid")
    return parsed


def materialize_pair_rules(
    view: RuleTrainingView,
    *,
    root: Path,
    min_support_fraction: float,
    max_pairs_in_memory: int = 250_000,
) -> PairRuleTable:
    """Mine bounded-memory pair rules from TRAIN baskets only."""

    support_fraction = _validate_fraction(min_support_fraction)
    if view.test_access_state != "LOCKED_NOT_ACCESSED":
        raise IntegrityError("pair-rule materialization requires a locked TEST boundary")
    if max_pairs_in_memory < 1:
        raise ContractError("max_pairs_in_memory must be positive")
    num_items = len(view.raw_item_ids)
    if num_items < 1 or len(set(view.raw_item_ids)) != num_items:
        raise IntegrityError("pair-rule candidate catalog is empty or duplicated")
    target = root.resolve()
    if target.exists():
        raise IntegrityError(f"pair-rule materialization root already exists: {target}")
    target.mkdir(parents=True)
    database = target / ".pair-counts.sqlite3"
    context_counts: Counter[int] = Counter()
    pair_buffer: Counter[tuple[int, int]] = Counter()
    basket_count = 0
    try:
        connection = sqlite3.connect(database)
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute(
            "CREATE TABLE pair_counts ("
            "context_id INTEGER NOT NULL, candidate_id INTEGER NOT NULL, "
            "support_count INTEGER NOT NULL, "
            "PRIMARY KEY (context_id, candidate_id)) WITHOUT ROWID"
        )
        for basket in view.iter_train_baskets():
            items = basket.item_ids
            if (
                not items
                or items != tuple(sorted(set(items)))
                or items[0] < 0
                or items[-1] >= num_items
            ):
                raise IntegrityError("TRAIN basket violates pair-rule ordering")
            basket_count += 1
            context_counts.update(items)
            for left in items:
                for right in items:
                    if left != right:
                        pair_buffer[(left, right)] += 1
            if len(pair_buffer) >= max_pairs_in_memory:
                _flush_pairs(connection, pair_buffer)
        _flush_pairs(connection, pair_buffer)
        if basket_count < 1:
            raise IntegrityError("pair-rule materialization received no TRAIN baskets")
        min_support_count = math.ceil(support_fraction * basket_count)
        pair_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM pair_counts WHERE support_count >= ?",
                (min_support_count,),
            ).fetchone()[0]
        )
        per_context = np.zeros(num_items, dtype=np.int64)
        candidate_ids = np.empty(pair_count, dtype=np.int32)
        confidences = np.empty(pair_count, dtype=np.float32)
        support_counts = np.empty(pair_count, dtype=np.int64)
        cursor = connection.execute(
            "SELECT context_id, candidate_id, support_count FROM pair_counts "
            "WHERE support_count >= ? ORDER BY context_id, candidate_id",
            (min_support_count,),
        )
        position = 0
        previous: tuple[int, int] | None = None
        for left_value, right_value, count_value in cursor:
            left = int(left_value)
            right = int(right_value)
            count = int(count_value)
            observed = (left, right)
            if (
                left < 0
                or left >= num_items
                or right < 0
                or right >= num_items
                or left == right
                or count < min_support_count
                or (previous is not None and observed <= previous)
            ):
                raise IntegrityError("pair-rule database emitted an invalid row")
            denominator = context_counts[left]
            if denominator < count:
                raise IntegrityError("pair-rule support exceeds antecedent support")
            candidate_ids[position] = right
            confidences[position] = count / denominator
            support_counts[position] = count
            per_context[left] += 1
            previous = observed
            position += 1
        if position != pair_count:
            raise IntegrityError("pair-rule count changed during materialization")
    except (OSError, sqlite3.DatabaseError) as error:
        raise IntegrityError("cannot materialize disk-backed pair rules") from error
    finally:
        if "connection" in locals():
            connection.close()
    try:
        database.unlink()
    except OSError as error:
        raise IntegrityError("cannot remove pair-rule staging database") from error

    offsets = np.zeros(num_items + 1, dtype=np.int64)
    np.cumsum(per_context, out=offsets[1:])
    context_array = np.zeros(num_items, dtype=np.int64)
    for item_id, count in context_counts.items():
        context_array[item_id] = count
    paths = {
        "context_counts": target / "context_counts.npy",
        "offsets": target / "rule_offsets.npy",
        "candidate_ids": target / "candidate_ids.npy",
        "confidences": target / "confidences.npy",
        "support_counts": target / "support_counts.npy",
    }
    _write_array(paths["context_counts"], cast(Array, context_array))
    _write_array(paths["offsets"], cast(Array, offsets))
    _write_array(paths["candidate_ids"], cast(Array, candidate_ids))
    _write_array(paths["confidences"], cast(Array, confidences))
    _write_array(paths["support_counts"], cast(Array, support_counts))
    candidate_order_sha256 = canonical_json_sha256(
        {
            "internal_item_ids": list(range(num_items)),
            "raw_item_ids": list(view.raw_item_ids),
        }
    )
    artifacts = [
        _artifact_row(target, paths["context_counts"], "TRAIN_ANTECEDENT_BASKET_COUNTS"),
        _artifact_row(target, paths["offsets"], "RULE_CONTEXT_OFFSETS"),
        _artifact_row(target, paths["candidate_ids"], "RULE_CONSEQUENT_ITEM_IDS"),
        _artifact_row(target, paths["confidences"], "PAIR_CONFIDENCE_WEIGHTS"),
        _artifact_row(target, paths["support_counts"], "PAIR_SUPPORT_COUNTS"),
    ]
    document = {
        "schema_version": "pair-rule-artifact/1.0",
        "source_manifest_sha256": view.manifest_sha256,
        "candidate_order_sha256": candidate_order_sha256,
        "num_items": num_items,
        "basket_count": basket_count,
        "min_support_fraction": support_fraction,
        "min_support_count": min_support_count,
        "support_count_rule": "CEILING_FRACTION_TIMES_TRAIN_BASKET_COUNT",
        "antecedent_size": 1,
        "consequent_size": 1,
        "pair_weight": "CONFIDENCE",
        "pair_count": pair_count,
        "aggregation": "BOUNDED_MEMORY_SQLITE_SPILL",
        "max_pairs_in_memory": max_pairs_in_memory,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "test_access_state": view.test_access_state,
        "training_performed": False,
        "metrics_computed": False,
        "test_accessed": False,
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(document) + b"\n")
    return load_pair_rule_table(
        target,
        expected_manifest_sha256=sha256_file(manifest_path),
    )


def load_pair_rule_table(
    root: Path,
    *,
    expected_manifest_sha256: str,
) -> PairRuleTable:
    target = root.resolve()
    manifest_path = target / "manifest.json"
    if not manifest_path.is_file() or sha256_file(manifest_path) != expected_manifest_sha256:
        raise IntegrityError("pair-rule manifest hash mismatch")
    document = load_strict_json(manifest_path)
    required = {
        "schema_version",
        "source_manifest_sha256",
        "candidate_order_sha256",
        "num_items",
        "basket_count",
        "min_support_fraction",
        "min_support_count",
        "support_count_rule",
        "antecedent_size",
        "consequent_size",
        "pair_weight",
        "pair_count",
        "aggregation",
        "max_pairs_in_memory",
        "artifact_count",
        "artifacts",
        "test_access_state",
        "training_performed",
        "metrics_computed",
        "test_accessed",
    }
    if set(document) != required:
        raise IntegrityError("pair-rule manifest fields do not match schema")
    integer_fields = (
        "num_items",
        "basket_count",
        "min_support_count",
        "pair_count",
        "max_pairs_in_memory",
    )
    if any(
        isinstance(document[field], bool)
        or not isinstance(document[field], int)
        or document[field] < (0 if field == "pair_count" else 1)
        for field in integer_fields
    ):
        raise IntegrityError("pair-rule manifest counts are invalid")
    support_fraction = _validate_fraction(float(document["min_support_fraction"]))
    if (
        document["schema_version"] != "pair-rule-artifact/1.0"
        or document["min_support_count"] != math.ceil(support_fraction * document["basket_count"])
        or document["support_count_rule"] != "CEILING_FRACTION_TIMES_TRAIN_BASKET_COUNT"
        or document["antecedent_size"] != 1
        or document["consequent_size"] != 1
        or document["pair_weight"] != "CONFIDENCE"
        or document["aggregation"] != "BOUNDED_MEMORY_SQLITE_SPILL"
        or document["test_access_state"] != "LOCKED_NOT_ACCESSED"
        or document["training_performed"] is not False
        or document["metrics_computed"] is not False
        or document["test_accessed"] is not False
    ):
        raise IntegrityError("pair-rule manifest authority mismatch")
    artifacts = document["artifacts"]
    if (
        not isinstance(artifacts, list)
        or document["artifact_count"] != len(artifacts)
        or len(artifacts) != 5
    ):
        raise IntegrityError("pair-rule artifact count mismatch")
    declared: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {
            "path",
            "bytes",
            "sha256",
            "role",
            "contains_validation_or_test_outcomes",
        }:
            raise IntegrityError("pair-rule artifact row is invalid")
        relative = row["path"]
        if not isinstance(relative, str) or relative in declared or ".." in Path(relative).parts:
            raise IntegrityError("pair-rule artifact path is invalid")
        path = target / relative
        if (
            row["contains_validation_or_test_outcomes"] is not False
            or not path.is_file()
            or path.stat().st_size != row["bytes"]
            or sha256_file(path) != row["sha256"]
        ):
            raise IntegrityError(f"pair-rule artifact mismatch: {relative}")
        declared.add(relative)
    observed = {
        path.relative_to(target).as_posix()
        for path in target.iterdir()
        if path.is_file() and path != manifest_path
    }
    if observed != declared:
        raise IntegrityError("pair-rule file set differs from manifest")
    try:
        context_counts = np.load(target / "context_counts.npy", mmap_mode="r", allow_pickle=False)
        offsets = np.load(target / "rule_offsets.npy", mmap_mode="r", allow_pickle=False)
        candidate_ids = np.load(target / "candidate_ids.npy", mmap_mode="r", allow_pickle=False)
        confidences = np.load(target / "confidences.npy", mmap_mode="r", allow_pickle=False)
        support_counts = np.load(target / "support_counts.npy", mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as error:
        raise IntegrityError("cannot load pair-rule arrays") from error
    num_items = int(document["num_items"])
    pair_count = int(document["pair_count"])
    if (
        context_counts.dtype != np.int64
        or context_counts.shape != (num_items,)
        or offsets.dtype != np.int64
        or offsets.shape != (num_items + 1,)
        or candidate_ids.dtype != np.int32
        or candidate_ids.shape != (pair_count,)
        or confidences.dtype != np.float32
        or confidences.shape != (pair_count,)
        or support_counts.dtype != np.int64
        or support_counts.shape != (pair_count,)
        or int(offsets[0]) != 0
        or int(offsets[-1]) != pair_count
        or bool((offsets[1:] < offsets[:-1]).any())
        or bool((context_counts < 0).any())
        or bool((candidate_ids < 0).any())
        or bool((candidate_ids >= num_items).any())
        or not np.isfinite(confidences).all()
        or bool((confidences < 0).any())
        or bool((confidences > 1).any())
        or bool((support_counts < int(document["min_support_count"])).any())
    ):
        raise IntegrityError("pair-rule arrays violate their manifest")
    return PairRuleTable(
        root=target,
        manifest_sha256=expected_manifest_sha256,
        num_items=num_items,
        basket_count=int(document["basket_count"]),
        min_support_fraction=support_fraction,
        min_support_count=int(document["min_support_count"]),
        pair_count=pair_count,
        candidate_order_sha256=str(document["candidate_order_sha256"]),
        context_counts=cast(Array, context_counts),
        offsets=cast(Array, offsets),
        candidate_ids=cast(Array, candidate_ids),
        confidences=cast(Array, confidences),
        support_counts=cast(Array, support_counts),
    )


def rule_aligned_user_ids(
    protocol: EvaluationProtocol,
    rules: PairRuleTable,
) -> tuple[int, ...]:
    if protocol.manifest.candidate_order_sha256 != rules.candidate_order_sha256:
        raise IntegrityError("RULE_ALIGNED cohort candidate authority mismatch")
    return tuple(
        user_id
        for user_id in protocol.eligible_user_ids
        if rules.has_antecedent(protocol.case_for(user_id).history_item_ids)
    )


__all__ = [
    "SUPPORT_FRACTIONS",
    "PairRuleTable",
    "RuleTrainingView",
    "load_pair_rule_table",
    "materialize_pair_rules",
    "rule_aligned_user_ids",
]
