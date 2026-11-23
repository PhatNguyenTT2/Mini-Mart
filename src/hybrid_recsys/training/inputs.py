"""Load pipeline inputs: canonical snapshot, item features and the evaluation protocols."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from hybrid_recsys.contracts import ProtocolManifest
from hybrid_recsys.data.io import load_canonical_snapshot
from hybrid_recsys.data.snapshot import Snapshot
from hybrid_recsys.errors import IntegrityError
from hybrid_recsys.hashing import canonical_json_sha256, sha256_file
from hybrid_recsys.models.confirmatory import ConfirmatoryItemFeatures
from hybrid_recsys.protocol import PreparedProtocol, UserEvaluationCase


@dataclass(frozen=True)
class FeatureIdentity:
    """Provenance of the item features; recorded in the feature descriptor hash.

    ``None`` fields are filled at load time: the text-model revision with forty zeros, the text and
    category hashes with the SHA-256 of ``text_embeddings.npy`` and ``category_ids.npy``.
    """

    text_repository_revision: str | None = None
    text_model_materialization_sha256: str | None = None
    category_mapping_sha256: str | None = None


@dataclass(frozen=True)
class PipelineInputs:
    snapshot: Snapshot
    validation_protocol: PreparedProtocol
    features: ConfirmatoryItemFeatures
    snapshot_root: Path
    feature_root: Path
    item_id_map: Mapping[int, int]

    def __post_init__(self) -> None:
        if set(self.snapshot.events_by_split) != {"train", "val"}:
            raise IntegrityError("pipeline inputs must contain TRAIN and VAL only")
        if self.validation_protocol.manifest.test_set_opened:
            raise IntegrityError("validation protocol unexpectedly opened TEST")
        if (
            self.features.candidate_order_sha256
            != self.validation_protocol.manifest.candidate_order_sha256
        ):
            raise IntegrityError("feature candidate order differs from validation protocol")
        if tuple(sorted(self.item_id_map.values())) != tuple(range(len(self.item_id_map))):
            raise IntegrityError("item map is not dense")


def _load_feature_array(root: Path, name: str) -> NDArray[Any]:
    path = root / name
    try:
        values = np.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as error:
        raise IntegrityError(f"cannot load feature array: {path}") from error
    if not isinstance(values, np.ndarray):
        raise IntegrityError(f"feature file is not an ndarray: {path}")
    return values


def load_pipeline_inputs(
    snapshot_root: Path,
    feature_root: Path,
    *,
    dataset_id: str | None = None,
    identity: FeatureIdentity = FeatureIdentity(),
) -> PipelineInputs:
    """Load TRAIN/VAL and features without opening ``test.jsonl``.

    ``feature_root`` holds ``raw_item_ids.npy`` (int64), ``text_embeddings.npy`` (float32 matrix)
    and ``category_ids.npy`` (int64), aligned row by row. The candidate catalog is exactly the
    set of items observed in TRAIN.
    """
    snapshot = load_canonical_snapshot(snapshot_root, required_splits=("train", "val"))
    dataset_id = dataset_id or snapshot.manifest.dataset_id
    raw_item_ids_array = _load_feature_array(feature_root, "raw_item_ids.npy")
    if raw_item_ids_array.dtype != np.int64 or raw_item_ids_array.ndim != 1:
        raise IntegrityError("raw_item_ids.npy must be a 1-D int64 array")
    raw_item_ids = tuple(int(value) for value in raw_item_ids_array.tolist())
    raw_to_internal = {int(raw): internal for internal, raw in enumerate(snapshot.raw_item_ids)}
    candidate_internal_ids = tuple(
        raw_to_internal[raw] for raw in raw_item_ids if raw in raw_to_internal
    )
    if len(candidate_internal_ids) != len(raw_item_ids):
        raise IntegrityError("feature catalog is not contained in the snapshot")
    if len(set(candidate_internal_ids)) != len(candidate_internal_ids):
        raise IntegrityError("feature catalog contains duplicate items")
    if set(candidate_internal_ids) != {
        event.item_id for event in snapshot.events_by_split["train"]
    }:
        raise IntegrityError("feature catalog is not exactly the TRAIN-observed catalog")
    item_id_map = {internal: index for index, internal in enumerate(candidate_internal_ids)}

    history: dict[int, set[int]] = {user: set() for user in snapshot.users}
    for event in snapshot.events_by_split["train"]:
        if event.item_id in item_id_map:
            history[event.user_id].add(item_id_map[event.item_id])
    targets: dict[int, set[int]] = {user: set() for user in snapshot.users}
    for event in snapshot.events_by_split["val"]:
        if event.event_type == "purchase" and event.event_origin == "organic":
            if event.item_id in item_id_map:
                targets[event.user_id].add(item_id_map[event.item_id])
    cases = {
        user: UserEvaluationCase(
            user, frozenset(history[user]), frozenset(targets[user] - history[user])
        )
        for user in snapshot.users
        if targets[user] - history[user]
    }
    candidate_hash = canonical_json_sha256(
        {"internal_item_ids": list(range(len(raw_item_ids))), "raw_item_ids": list(raw_item_ids)}
    )
    manifest = ProtocolManifest(
        protocol_id=f"{dataset_id}:val:full-train-observed-catalog-v1",
        dataset_id=dataset_id,
        dataset_manifest_sha256=canonical_json_sha256(snapshot.manifest.to_mapping()),
        split="val",
        split_hash=snapshot.manifest.split_hashes["val"],
        candidate_item_ids=tuple(range(len(raw_item_ids))),
        candidate_order_sha256=candidate_hash,
        eligible_user_rule="user_has_at_least_one_novel_organic_purchase_in_validation_train_catalog",
        positive_rule="organic_validation_purchase_minus_train_history_and_catalog_intersection",
        seen_masking="all_prior_interacted_items_to_negative_infinity",
        cutoff=min(10, len(raw_item_ids)),
        tie_break="descending_score_then_ascending_raw_product_id",
        metric_version="ranking-v1",
        test_set_opened=False,
    )
    protocol = PreparedProtocol(
        manifest=manifest,
        raw_item_ids=raw_item_ids,
        cases=cases,
        num_total_users=snapshot.manifest.num_users,
    )
    text = _load_feature_array(feature_root, "text_embeddings.npy")
    categories = _load_feature_array(feature_root, "category_ids.npy")
    if text.dtype != np.float32 or text.ndim != 2:
        raise IntegrityError("text_embeddings.npy must be a float32 matrix")
    if categories.dtype != np.int64 or categories.ndim != 1:
        raise IntegrityError("category_ids.npy must be a 1-D int64 array")
    if text.shape[0] != len(raw_item_ids) or categories.shape[0] != len(raw_item_ids):
        raise IntegrityError("feature arrays do not match raw_item_ids.npy")
    features = ConfirmatoryItemFeatures(
        text_embeddings=np.asarray(text, dtype=np.float32),
        category_ids=np.asarray(categories, dtype=np.int64),
        num_categories=int(np.max(categories)) + 1,
        text_repository_revision=identity.text_repository_revision or "0" * 40,
        text_model_materialization_sha256=identity.text_model_materialization_sha256
        or sha256_file(feature_root / "text_embeddings.npy"),
        category_mapping_sha256=identity.category_mapping_sha256
        or sha256_file(feature_root / "category_ids.npy"),
        candidate_order_sha256=candidate_hash,
    )
    return PipelineInputs(snapshot, protocol, features, snapshot_root, feature_root, item_id_map)


def build_test_protocol(
    snapshot: Snapshot, validation: PreparedProtocol, item_id_map: Mapping[int, int]
) -> PreparedProtocol:
    """TEST protocol: TRAIN+VAL history, the TRAIN-observed catalog, novel organic targets."""
    if set(snapshot.events_by_split) != {"train", "val", "test"}:
        raise IntegrityError("TEST snapshot must contain TRAIN, VAL and TEST")
    if validation.manifest.test_set_opened:
        raise IntegrityError("validation template already opened TEST")
    if tuple(sorted(item_id_map.values())) != validation.candidate_item_ids:
        raise IntegrityError("TEST item mapping differs from the validation catalog")
    if any(
        snapshot.raw_item_ids[old] != validation.raw_item_ids[new]
        for old, new in item_id_map.items()
    ):
        raise IntegrityError("TEST raw candidate mapping differs")
    history: dict[int, set[int]] = {user: set() for user in snapshot.users}
    targets: dict[int, set[int]] = {user: set() for user in snapshot.users}
    for split in ("train", "val"):
        for event in snapshot.events_by_split[split]:
            if event.item_id in item_id_map:
                history[event.user_id].add(item_id_map[event.item_id])
    for event in snapshot.events_by_split["test"]:
        if event.event_type == "purchase" and event.event_origin == "organic":
            if event.item_id in item_id_map:
                targets[event.user_id].add(item_id_map[event.item_id])
    cases = {
        user: UserEvaluationCase(
            user, frozenset(history[user]), frozenset(targets[user] - history[user])
        )
        for user in snapshot.users
        if targets[user] - history[user]
    }
    manifest = replace(
        validation.manifest,
        protocol_id=f"{validation.manifest.dataset_id}:test:full-train-observed-catalog-v1",
        split="test",
        split_hash=snapshot.manifest.split_hashes["test"],
        eligible_user_rule="user_has_at_least_one_novel_organic_purchase_in_test_train_catalog",
        positive_rule="organic_test_purchase_minus_train_and_validation_history_and_catalog_intersection",
        test_set_opened=True,
    )
    return PreparedProtocol(manifest, validation.raw_item_ids, cases, snapshot.manifest.num_users)
