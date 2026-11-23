"""Hash-bound, TEST-locked adapter for the admitted Instacart runtime view."""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from hybrid_recsys.array_types import Array
from hybrid_recsys.contracts import ProtocolManifest
from hybrid_recsys.data.snapshot import ItemRecord
from hybrid_recsys.errors import IntegrityError, ProtocolError, ScoreError
from hybrid_recsys.hashing import canonical_json_sha256, load_strict_json, sha256_file
from hybrid_recsys.protocol import UserEvaluationCase

_RUNTIME_FILES = {
    "admitted_users.csv.gz",
    "candidate_catalog.csv.gz",
    "candidate_features.csv.gz",
    "candidate_product_ids.npy",
    "order_assignments.csv.gz",
    "product_features.csv.gz",
    "train_seen_user_item_keys.npy",
    "validation_eligible_users.csv.gz",
    "validation_novel_targets.csv.gz",
    "validation_novel_user_item_keys.npy",
    "validation_target_audit.csv.gz",
}


@dataclass(frozen=True)
class TrainPairBatch:
    """One dense-ID batch of unique TRAIN user-item pairs."""

    user_ids: Array
    item_ids: Array


@dataclass(frozen=True)
class InstacartTrainingBasket:
    """One TRAIN basket with deterministic dense IDs and no within-basket order."""

    user_id: int
    order_number: int
    raw_order_id: int
    item_ids: tuple[int, ...]


class InstacartValidationProtocol:
    """Validation protocol backed by sorted, memory-mapped P3 pair arrays."""

    def __init__(
        self,
        *,
        manifest: ProtocolManifest,
        raw_user_ids: tuple[int, ...],
        raw_item_ids: tuple[int, ...],
        eligible_user_ids: tuple[int, ...],
        train_keys: Array,
        validation_keys: Array,
        key_multiplier: int,
    ) -> None:
        self.manifest = manifest
        self.raw_user_ids = raw_user_ids
        self.raw_item_ids = raw_item_ids
        self.num_total_users = len(raw_user_ids)
        self._eligible_user_ids = eligible_user_ids
        self._eligible_user_set = frozenset(eligible_user_ids)
        self._train_keys = train_keys
        self._validation_keys = validation_keys
        self._key_multiplier = key_multiplier

    @property
    def candidate_item_ids(self) -> tuple[int, ...]:
        return self.manifest.candidate_item_ids

    @property
    def eligible_user_ids(self) -> tuple[int, ...]:
        return self._eligible_user_ids

    def _items_for(self, keys: Array, raw_user_id: int) -> frozenset[int]:
        lower = raw_user_id * self._key_multiplier
        upper = (raw_user_id + 1) * self._key_multiplier
        first = int(np.searchsorted(keys, lower, side="left"))
        last = int(np.searchsorted(keys, upper, side="left"))
        raw_products = np.asarray(keys[first:last] % self._key_multiplier, dtype=np.int64)
        positions = np.searchsorted(np.asarray(self.raw_item_ids), raw_products)
        if len(positions) and (
            bool((positions >= len(self.raw_item_ids)).any())
            or not np.array_equal(np.asarray(self.raw_item_ids)[positions], raw_products)
        ):
            raise IntegrityError(
                "Instacart pair references a product outside the candidate catalog"
            )
        return frozenset(int(value) for value in positions)

    def case_for(self, user_id: int) -> UserEvaluationCase:
        if user_id not in self._eligible_user_set:
            raise ProtocolError(f"user is not eligible: {user_id}")
        raw_user_id = self.raw_user_ids[user_id]
        history = self._items_for(self._train_keys, raw_user_id)
        positives = self._items_for(self._validation_keys, raw_user_id)
        if not positives or history & positives:
            raise IntegrityError("Instacart validation case violates novelty semantics")
        return UserEvaluationCase(user_id, history, positives)

    def mask_scores(self, user_id: int, scores: Array) -> Array:
        values = np.asarray(scores, dtype=np.float64)
        if values.shape != (len(self.candidate_item_ids),):
            raise ScoreError("score vector shape does not match candidate catalog")
        if not np.isfinite(values).all():
            raise ScoreError("model emitted NaN or non-finite scores")
        masked = values.copy()
        for item_id in self.case_for(user_id).history_item_ids:
            masked[item_id] = -np.inf
        return cast(Array, masked)


@dataclass(frozen=True)
class InstacartRuntimeView:
    """Deep interface over the admitted TRAIN/validation runtime artifacts."""

    root: Path
    manifest_sha256: str
    raw_user_ids: tuple[int, ...]
    raw_item_ids: tuple[int, ...]
    validation_protocol: InstacartValidationProtocol
    _train_keys: Array
    _key_multiplier: int
    _prior_source_path: Path
    _prior_source_bytes: int
    _prior_source_sha256: str
    _train_order_count: int

    @property
    def test_access_state(self) -> str:
        return "LOCKED_NOT_ACCESSED"

    def iter_train_pairs(self, *, batch_size: int = 262_144) -> Iterator[TrainPairBatch]:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        raw_users = np.asarray(self.raw_user_ids, dtype=np.int64)
        raw_items = np.asarray(self.raw_item_ids, dtype=np.int64)
        for first in range(0, len(self._train_keys), batch_size):
            keys = np.asarray(self._train_keys[first : first + batch_size], dtype=np.int64)
            source_users = keys // self._key_multiplier
            source_items = keys % self._key_multiplier
            user_ids = np.searchsorted(raw_users, source_users)
            item_ids = np.searchsorted(raw_items, source_items)
            if (
                bool((user_ids >= len(raw_users)).any())
                or bool((item_ids >= len(raw_items)).any())
                or not np.array_equal(raw_users[user_ids], source_users)
                or not np.array_equal(raw_items[item_ids], source_items)
            ):
                raise IntegrityError("TRAIN pair cannot be mapped to dense admitted IDs")
            yield TrainPairBatch(
                user_ids=user_ids.astype(np.int32, copy=False),
                item_ids=item_ids.astype(np.int32, copy=False),
            )

    def iter_item_records(self) -> Iterator[ItemRecord]:
        """Yield frozen text/category features in dense candidate order."""

        path = self.root / "candidate_features.csv.gz"
        expected_header = [
            "product_id",
            "item_text",
            "item_category",
            "aisle_id",
            "department_id",
        ]
        observed_raw_ids: list[int] = []
        try:
            with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != expected_header:
                    raise IntegrityError(f"Instacart CSV header mismatch: {path}")
                for item_id, row in enumerate(reader):
                    raw_item_id = int(row["product_id"])
                    text = row["item_text"]
                    category = row["item_category"]
                    aisle_id = int(row["aisle_id"])
                    department_id = int(row["department_id"])
                    if not text or category != (
                        f"department_id={department_id}|aisle_id={aisle_id}"
                    ):
                        raise IntegrityError("Instacart candidate feature row is invalid")
                    observed_raw_ids.append(raw_item_id)
                    yield ItemRecord(item_id, raw_item_id, text, category, None)
        except (OSError, UnicodeError, ValueError, KeyError) as error:
            raise IntegrityError(f"cannot read Instacart candidate features: {path}") from error
        if tuple(observed_raw_ids) != self.raw_item_ids:
            raise IntegrityError("Instacart candidate feature order does not match catalog")

    def _train_order_index(self) -> tuple[Array, Array, Array]:
        path = self.root / "order_assignments.csv.gz"
        order_ids = np.empty(self._train_order_count, dtype=np.int32)
        raw_users = np.empty(self._train_order_count, dtype=np.int32)
        order_numbers = np.empty(self._train_order_count, dtype=np.int16)
        index = 0
        try:
            with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != ["user_id", "order_number", "order_id", "split"]:
                    raise IntegrityError(f"Instacart CSV header mismatch: {path}")
                for row in reader:
                    split = row["split"]
                    if split not in {"train", "validation", "TEST_LOCKED"}:
                        raise IntegrityError("Instacart order assignment split is invalid")
                    if split != "train":
                        continue
                    if index >= self._train_order_count:
                        raise IntegrityError("Instacart TRAIN order count exceeds manifest")
                    order_ids[index] = int(row["order_id"])
                    raw_users[index] = int(row["user_id"])
                    order_numbers[index] = int(row["order_number"])
                    index += 1
        except (OSError, UnicodeError, ValueError, KeyError) as error:
            raise IntegrityError(f"cannot read Instacart order assignments: {path}") from error
        if index != self._train_order_count:
            raise IntegrityError("Instacart TRAIN order count does not match manifest")
        raw_user_ids = np.asarray(self.raw_user_ids, dtype=np.int64)
        user_ids = np.searchsorted(raw_user_ids, raw_users)
        if bool((user_ids >= len(raw_user_ids)).any()) or not np.array_equal(
            raw_user_ids[user_ids], raw_users
        ):
            raise IntegrityError("Instacart TRAIN order references an unknown admitted user")
        order = np.argsort(order_ids, kind="stable")
        sorted_order_ids = order_ids[order]
        if bool((sorted_order_ids[1:] <= sorted_order_ids[:-1]).any()):
            raise IntegrityError("Instacart TRAIN order IDs must be unique")
        return (
            sorted_order_ids,
            user_ids[order].astype(np.int32, copy=False),
            order_numbers[order],
        )

    def _basket_for(
        self,
        raw_order_id: int,
        raw_products: list[int],
        train_order_ids: Array,
        train_user_ids: Array,
        train_order_numbers: Array,
        train_index: int,
    ) -> InstacartTrainingBasket | None:
        if train_index >= len(train_order_ids) or int(train_order_ids[train_index]) != raw_order_id:
            return None
        if len(set(raw_products)) != len(raw_products):
            raise IntegrityError("Instacart TRAIN basket contains a duplicate product")
        unique_products = np.asarray(sorted(raw_products), dtype=np.int64)
        raw_item_ids = np.asarray(self.raw_item_ids, dtype=np.int64)
        item_ids = np.searchsorted(raw_item_ids, unique_products)
        if bool((item_ids >= len(raw_item_ids)).any()) or not np.array_equal(
            raw_item_ids[item_ids], unique_products
        ):
            raise IntegrityError("Instacart TRAIN basket contains an item outside the catalog")
        return InstacartTrainingBasket(
            user_id=int(train_user_ids[train_index]),
            order_number=int(train_order_numbers[train_index]),
            raw_order_id=raw_order_id,
            item_ids=tuple(int(value) for value in item_ids),
        )

    def iter_train_baskets(self) -> Iterator[InstacartTrainingBasket]:
        """Stream hash-bound provider-prior rows and yield only TRAIN baskets."""

        if (
            not self._prior_source_path.is_file()
            or self._prior_source_path.stat().st_size != self._prior_source_bytes
            or sha256_file(self._prior_source_path) != self._prior_source_sha256
        ):
            raise IntegrityError("Instacart provider-prior source binding mismatch")
        train_order_ids, train_user_ids, train_order_numbers = self._train_order_index()
        train_index = 0
        yielded = 0
        current_order_id: int | None = None
        current_products: list[int] = []
        try:
            with self._prior_source_path.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != [
                    "order_id",
                    "product_id",
                    "add_to_cart_order",
                    "reordered",
                ]:
                    raise IntegrityError("Instacart provider-prior header mismatch")
                for row in reader:
                    order_id = int(row["order_id"])
                    product_id = int(row["product_id"])
                    if current_order_id is None:
                        current_order_id = order_id
                    if order_id < current_order_id:
                        raise IntegrityError("Instacart provider-prior order IDs regressed")
                    if order_id != current_order_id:
                        if (
                            train_index < len(train_order_ids)
                            and int(train_order_ids[train_index]) < current_order_id
                        ):
                            raise IntegrityError("Instacart TRAIN order has no prior basket")
                        basket = self._basket_for(
                            current_order_id,
                            current_products,
                            train_order_ids,
                            train_user_ids,
                            train_order_numbers,
                            train_index,
                        )
                        if basket is not None:
                            yield basket
                            yielded += 1
                            train_index += 1
                        current_order_id = order_id
                        current_products = []
                    current_products.append(product_id)
        except (OSError, UnicodeError, ValueError, KeyError) as error:
            raise IntegrityError("cannot stream Instacart provider-prior source") from error
        if current_order_id is not None:
            basket = self._basket_for(
                current_order_id,
                current_products,
                train_order_ids,
                train_user_ids,
                train_order_numbers,
                train_index,
            )
            if basket is not None:
                yield basket
                yielded += 1
                train_index += 1
        if yielded != self._train_order_count or train_index != len(train_order_ids):
            raise IntegrityError("Instacart TRAIN basket coverage does not match manifest")


def _require_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IntegrityError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _load_sorted_array(path: Path, dtype: np.dtype[Any]) -> Array:
    try:
        values = np.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as error:
        raise IntegrityError(f"cannot load Instacart runtime array: {path}") from error
    if values.ndim != 1 or values.dtype != dtype or not len(values):
        raise IntegrityError(f"Instacart runtime array has invalid shape or dtype: {path}")
    if bool((values[1:] <= values[:-1]).any()):
        raise IntegrityError(f"Instacart runtime array must be strictly increasing: {path}")
    return cast(Array, values)


def _read_id_column(path: Path, expected_header: list[str], column: str) -> tuple[int, ...]:
    values: list[int] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected_header:
                raise IntegrityError(f"Instacart CSV header mismatch: {path}")
            for row in reader:
                value = int(row[column])
                if value < 1:
                    raise IntegrityError(f"Instacart ID must be positive: {path}")
                values.append(value)
    except (OSError, UnicodeError, ValueError, KeyError) as error:
        raise IntegrityError(f"cannot read Instacart runtime CSV: {path}") from error
    if not values or values != sorted(set(values)):
        raise IntegrityError(f"Instacart ID column must be sorted and unique: {path}")
    return tuple(values)


def _validate_manifest(root: Path, expected_sha256: str) -> dict[str, Any]:
    manifest_path = root / "runtime_materialization_manifest.json"
    if sha256_file(manifest_path) != expected_sha256:
        raise IntegrityError("Instacart runtime manifest hash mismatch")
    document = load_strict_json(manifest_path)
    required = {
        "schema_version",
        "created_at",
        "dataset_id",
        "materialized_root",
        "source_archive_sha256",
        "source_archive_bytes",
        "source_files",
        "test_boundary",
        "split_order_counts",
        "cohort",
        "artifact_count",
        "artifacts",
        "training_performed",
        "metrics_computed",
        "test_accessed",
    }
    if set(document) != required:
        raise IntegrityError("Instacart runtime manifest fields do not match schema")
    if (
        document["schema_version"] != "instacart-runtime-materialization/1.0"
        or document["dataset_id"] != "INSTACART_EXTERNAL"
        or Path(str(document["materialized_root"])).resolve() != root.resolve()
        or document["training_performed"] is not False
        or document["metrics_computed"] is not False
        or document["test_accessed"] is not False
    ):
        raise IntegrityError("Instacart runtime manifest authority mismatch")
    boundary = document["test_boundary"]
    if not isinstance(boundary, dict) or boundary != {
        "test_outcome_file": "order_products__train.csv",
        "content_parsed": False,
        "inspection_scope": "ARCHIVE_CRC_FILE_HASH_AND_HEADER_ONLY",
        "test_result_rows": 0,
    }:
        raise IntegrityError("Instacart TEST boundary is not sealed")
    source_files = document["source_files"]
    if not isinstance(source_files, list):
        raise IntegrityError("Instacart source_files must be a list")
    locked_rows = [
        row
        for row in source_files
        if isinstance(row, dict) and row.get("name") == "order_products__train.csv"
    ]
    if len(locked_rows) != 1 or locked_rows[0].get("row_content_parsed") is not False:
        raise IntegrityError("Instacart TEST outcome source is not locked")
    prior_rows = [
        row
        for row in source_files
        if isinstance(row, dict) and row.get("name") == "order_products__prior.csv"
    ]
    if len(prior_rows) != 1 or prior_rows[0].get("row_content_parsed") is not True:
        raise IntegrityError("Instacart provider-prior source binding is invalid")
    artifacts = document["artifacts"]
    if not isinstance(artifacts, list) or document["artifact_count"] != len(artifacts):
        raise IntegrityError("Instacart runtime artifact count mismatch")
    names: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict) or set(row) != {
            "path",
            "bytes",
            "sha256",
            "contains_test_outcomes",
        }:
            raise IntegrityError("Instacart runtime artifact row is invalid")
        name = row["path"]
        if not isinstance(name, str) or Path(name).name != name or name in names:
            raise IntegrityError("Instacart runtime artifact name is invalid")
        names.add(name)
        path = root / name
        if row["contains_test_outcomes"] is not False:
            raise IntegrityError("Instacart runtime artifact contains TEST outcomes")
        if path.stat().st_size != _require_int(row["bytes"], f"{name}.bytes"):
            raise IntegrityError(f"Instacart runtime artifact byte mismatch: {name}")
        if sha256_file(path) != row["sha256"]:
            raise IntegrityError(f"Instacart runtime artifact hash mismatch: {name}")
    if names != _RUNTIME_FILES:
        raise IntegrityError("Instacart runtime artifact set mismatch")
    return document


def load_instacart_runtime_view(
    root: Path,
    *,
    expected_manifest_sha256: str,
    cutoff: int = 10,
) -> InstacartRuntimeView:
    """Replay a P3 runtime view without opening the provider TEST outcome file."""

    runtime_root = root.resolve()
    document = _validate_manifest(runtime_root, expected_manifest_sha256)
    raw_user_ids = _read_id_column(
        runtime_root / "admitted_users.csv.gz",
        ["user_id", "test_order_id", "max_order_number", "validation_order_id"],
        "user_id",
    )
    eligible_raw_users = _read_id_column(
        runtime_root / "validation_eligible_users.csv.gz", ["user_id"], "user_id"
    )
    raw_user_array = np.asarray(raw_user_ids, dtype=np.int64)
    eligible_user_ids_array = np.searchsorted(raw_user_array, np.asarray(eligible_raw_users))
    if bool((eligible_user_ids_array >= len(raw_user_array)).any()) or not np.array_equal(
        raw_user_array[eligible_user_ids_array], eligible_raw_users
    ):
        raise IntegrityError("eligible user is outside the admitted user mapping")
    eligible_user_ids = tuple(int(value) for value in eligible_user_ids_array)

    candidate_array = _load_sorted_array(
        runtime_root / "candidate_product_ids.npy", np.dtype(np.int32)
    )
    raw_item_ids = tuple(int(value) for value in candidate_array)
    if cutoff < 1 or cutoff > len(raw_item_ids):
        raise ProtocolError("cutoff must be inside the Instacart candidate catalog")
    train_keys = _load_sorted_array(
        runtime_root / "train_seen_user_item_keys.npy", np.dtype(np.int64)
    )
    validation_keys = _load_sorted_array(
        runtime_root / "validation_novel_user_item_keys.npy", np.dtype(np.int64)
    )
    cohort = document["cohort"]
    if not isinstance(cohort, dict):
        raise IntegrityError("Instacart cohort receipt must be an object")
    multiplier = _require_int(
        cohort.get("user_item_key_multiplier"),
        "user_item_key_multiplier",
        minimum=1,
    )
    if (
        cohort.get("candidate_item_count") != len(raw_item_ids)
        or cohort.get("train_distinct_user_item_pairs") != len(train_keys)
        or cohort.get("validation_novel_positive_count") != len(validation_keys)
        or cohort.get("validation_eligible_user_count") != len(eligible_user_ids)
        or cohort.get("main_cohort_gate") != "PASS"
    ):
        raise IntegrityError("Instacart cohort counts do not match runtime arrays")
    candidate_ids = tuple(range(len(raw_item_ids)))
    candidate_order_sha256 = canonical_json_sha256(
        {"internal_item_ids": list(candidate_ids), "raw_item_ids": list(raw_item_ids)}
    )
    artifact_hashes = {
        str(row["path"]): str(row["sha256"])
        for row in document["artifacts"]
        if isinstance(row, dict)
    }
    split_hash = canonical_json_sha256(
        {
            "candidate_product_ids.npy": artifact_hashes["candidate_product_ids.npy"],
            "train_seen_user_item_keys.npy": artifact_hashes["train_seen_user_item_keys.npy"],
            "validation_novel_user_item_keys.npy": artifact_hashes[
                "validation_novel_user_item_keys.npy"
            ],
            "validation_eligible_users.csv.gz": artifact_hashes["validation_eligible_users.csv.gz"],
        }
    )
    manifest = ProtocolManifest(
        protocol_id="INSTACART_EXTERNAL:val:full-catalog-v1",
        dataset_id="INSTACART_EXTERNAL",
        dataset_manifest_sha256=expected_manifest_sha256,
        split="val",
        split_hash=split_hash,
        candidate_item_ids=candidate_ids,
        candidate_order_sha256=candidate_order_sha256,
        eligible_user_rule="at_least_one_novel_item_in_validation_order_after_catalog_and_seen_mask",
        positive_rule="novel_item_in_penultimate_order_after_train_catalog_intersection",
        seen_masking="all_train_seen_items_to_negative_infinity",
        cutoff=cutoff,
        tie_break="descending_score_then_ascending_raw_product_id",
        metric_version="ranking-v1",
        test_set_opened=False,
    )
    protocol = InstacartValidationProtocol(
        manifest=manifest,
        raw_user_ids=raw_user_ids,
        raw_item_ids=raw_item_ids,
        eligible_user_ids=eligible_user_ids,
        train_keys=train_keys,
        validation_keys=validation_keys,
        key_multiplier=multiplier,
    )
    source_files = document["source_files"]
    if not isinstance(source_files, list):
        raise IntegrityError("Instacart source_files must be a list")
    prior_row = next(
        row
        for row in source_files
        if isinstance(row, dict) and row.get("name") == "order_products__prior.csv"
    )
    split_order_counts = document["split_order_counts"]
    if not isinstance(split_order_counts, dict):
        raise IntegrityError("Instacart split_order_counts must be an object")
    return InstacartRuntimeView(
        root=runtime_root,
        manifest_sha256=expected_manifest_sha256,
        raw_user_ids=raw_user_ids,
        raw_item_ids=raw_item_ids,
        validation_protocol=protocol,
        _train_keys=train_keys,
        _key_multiplier=multiplier,
        _prior_source_path=Path(str(prior_row["absolute_path"])),
        _prior_source_bytes=_require_int(
            prior_row.get("bytes"), "order_products__prior.csv.bytes", minimum=1
        ),
        _prior_source_sha256=str(prior_row["sha256"]),
        _train_order_count=_require_int(
            split_order_counts.get("train"), "split_order_counts.train", minimum=1
        ),
    )


__all__ = [
    "InstacartRuntimeView",
    "InstacartTrainingBasket",
    "InstacartValidationProtocol",
    "TrainPairBatch",
    "load_instacart_runtime_view",
]
