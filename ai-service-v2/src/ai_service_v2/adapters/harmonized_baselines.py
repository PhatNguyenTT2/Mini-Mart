"""Objective-preserving conventional baselines for the harmonized v5 protocol.

These adapters are deliberately separate from the official RecBole reproduction
namespace.  Their algorithms and defaults are reviewed against the pinned
RecBole source, while training, persistence, score export, and evaluation remain
under the local hash-bound protocol.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, cast

import numpy as np

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.snapshot import Interaction, Snapshot
from ai_service_v2.errors import ContractError, IntegrityError, ScoreError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    load_strict_json,
    sha256_bytes,
)
from ai_service_v2.protocol import PreparedProtocol

RECBOLE_REPOSITORY_URL = "https://github.com/RUCAIBox/RecBole"
RECBOLE_SOURCE_COMMIT = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
BASELINE_KINDS = frozenset({"itemknn", "bpr_mf"})


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContractError(f"{name} must be a positive integer")
    return value


def _finite_float(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0) or (not positive and parsed < 0):
        raise ContractError(f"{name} is outside the admitted range")
    return parsed


@dataclass(frozen=True)
class HarmonizedBaselineSpec:
    """Strict configuration for one conventional harmonized-v5 comparator."""

    model_kind: str
    model_id: str
    parameters: dict[str, int | float | str]
    schema_version: str = "harmonized-baseline-spec/1.0"
    source_repository: str = RECBOLE_REPOSITORY_URL
    source_commit: str = RECBOLE_SOURCE_COMMIT

    _FIELDS: ClassVar[set[str]] = {
        "schema_version",
        "model_kind",
        "model_id",
        "parameters",
        "source_repository",
        "source_commit",
    }

    def __post_init__(self) -> None:
        if self.schema_version != "harmonized-baseline-spec/1.0":
            raise ContractError("unsupported harmonized baseline schema")
        if self.model_kind not in BASELINE_KINDS or not self.model_id:
            raise ContractError("unsupported or missing harmonized baseline identity")
        if self.source_repository != RECBOLE_REPOSITORY_URL:
            raise ContractError("baseline source repository differs from the frozen source")
        if self.source_commit != RECBOLE_SOURCE_COMMIT:
            raise ContractError("baseline source commit differs from the frozen revision")
        if self.model_kind == "itemknn":
            expected = {"top_k", "similarity", "interaction_signal"}
            if set(self.parameters) != expected:
                raise ContractError("ItemKNN parameters do not match the frozen schema")
            _positive_int(self.parameters["top_k"], "top_k")
            if self.parameters["similarity"] != "binary_cosine":
                raise ContractError("unsupported ItemKNN similarity")
            if self.parameters["interaction_signal"] != "purchase":
                raise ContractError("unsupported ItemKNN interaction signal")
        else:
            expected = {
                "embedding_dim",
                "epochs",
                "learning_rate",
                "l2",
                "negatives_per_positive",
                "interaction_signal",
            }
            if set(self.parameters) != expected:
                raise ContractError("BPR-MF parameters do not match the frozen schema")
            _positive_int(self.parameters["embedding_dim"], "embedding_dim")
            _positive_int(self.parameters["epochs"], "epochs")
            _finite_float(self.parameters["learning_rate"], "learning_rate", positive=True)
            _finite_float(self.parameters["l2"], "l2")
            if (
                _positive_int(self.parameters["negatives_per_positive"], "negatives_per_positive")
                != 1
            ):
                raise ContractError("the v1 adapter freezes one BPR negative per positive")
            if self.parameters["interaction_signal"] != "purchase":
                raise ContractError("unsupported BPR-MF interaction signal")

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> HarmonizedBaselineSpec:
        if set(value) != cls._FIELDS or not isinstance(value.get("parameters"), dict):
            raise ContractError("harmonized baseline fields do not match schema")
        model_kind = value.get("model_kind")
        model_id = value.get("model_id")
        if not isinstance(model_kind, str) or not isinstance(model_id, str):
            raise ContractError("harmonized baseline identity must be strings")
        parameters = value["parameters"]
        if any(not isinstance(key, str) for key in parameters):
            raise ContractError("harmonized baseline parameter names must be strings")
        return cls(
            schema_version=value["schema_version"],
            model_kind=model_kind,
            model_id=model_id,
            parameters=dict(parameters),
            source_repository=value["source_repository"],
            source_commit=value["source_commit"],
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "model_kind": self.model_kind,
            "model_id": self.model_id,
            "parameters": dict(self.parameters),
            "source_repository": self.source_repository,
            "source_commit": self.source_commit,
        }


def descriptor_for_baseline(spec: HarmonizedBaselineSpec) -> ModelDescriptor:
    """Describe the local adapter without relabeling it as native RecBole output."""

    if spec.model_kind == "itemknn":
        family = "item_neighborhood_collaborative_filtering"
        objective = "binary_cosine_top_k_neighborhood"
        negative_sampler = "not_applicable"
        source_path = "recbole/model/general_recommender/itemknn.py"
    else:
        family = "matrix_factorization"
        objective = "pairwise_bpr"
        negative_sampler = "train_purchase_seen_exclusion_pcg64"
        source_path = "recbole/model/general_recommender/bpr.py"
    return ModelDescriptor(
        model_id=spec.model_id,
        family=family,
        implementation_provenance=(
            "local_harmonized_adapter_reviewed_against_recbole_v1.2.1:" + source_path
        ),
        repository_url=spec.source_repository,
        repository_commit=spec.source_commit,
        objective=objective,
        negative_sampler=negative_sampler,
        input_features=("user_id", "train_purchase_history", "item_id"),
        config_sha256=canonical_json_sha256(spec.to_mapping()),
        adapter_revision="ai-service-v2:harmonized-conventional:v1",
    )


def _purchase_histories(events: tuple[Interaction, ...]) -> dict[int, frozenset[int]]:
    histories: dict[int, set[int]] = defaultdict(set)
    for event in events:
        if event.event_type == "purchase":
            histories[event.user_id].add(event.item_id)
    return {user_id: frozenset(item_ids) for user_id, item_ids in histories.items()}


class FittedItemKNN:
    """Sparse top-k binary-cosine ItemKNN fitted on TRAIN purchases only."""

    def __init__(
        self,
        snapshot: Snapshot,
        protocol: PreparedProtocol,
        spec: HarmonizedBaselineSpec,
        neighbor_indices: np.ndarray,
        neighbor_weights: np.ndarray,
        item_support: np.ndarray,
    ) -> None:
        item_count = snapshot.manifest.num_items
        top_k = _positive_int(spec.parameters["top_k"], "top_k")
        indices = np.asarray(neighbor_indices, dtype=np.int64)
        weights = np.asarray(neighbor_weights, dtype=np.float64)
        support = np.asarray(item_support, dtype=np.int64)
        if indices.shape != (item_count, min(top_k, max(1, item_count - 1))):
            raise IntegrityError("ItemKNN neighbor index shape is invalid")
        if weights.shape != indices.shape or support.shape != (item_count,):
            raise IntegrityError("ItemKNN parameter shapes are inconsistent")
        if np.any(indices < -1) or np.any(indices >= item_count):
            raise IntegrityError("ItemKNN neighbor index is outside the catalog")
        if not np.isfinite(weights).all() or np.any(weights < 0) or np.any(support < 0):
            raise IntegrityError("ItemKNN parameters contain invalid values")
        if np.any((indices == -1) != (weights == 0.0)):
            raise IntegrityError("ItemKNN padding and weights disagree")
        self.snapshot = snapshot
        self.protocol = protocol
        self.spec = spec
        self.neighbor_indices = indices
        self.neighbor_weights = weights
        self.item_support = support
        self.descriptor = descriptor_for_baseline(spec)
        self._query_history = _purchase_histories(snapshot.history_events(protocol.manifest.split))

    def describe(self) -> ModelDescriptor:
        return self.descriptor

    def parameter_arrays(self) -> dict[str, np.ndarray]:
        return {
            "neighbor_indices": self.neighbor_indices,
            "neighbor_weights": self.neighbor_weights,
            "item_support": self.item_support,
        }

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        if candidate_item_ids != self.protocol.candidate_item_ids:
            raise ScoreError("ItemKNN candidate order differs from the frozen protocol")
        scores = np.zeros(len(candidate_item_ids), dtype=np.float64)
        for source_item in self._query_history.get(user_id, frozenset()):
            neighbors = self.neighbor_indices[source_item]
            weights = self.neighbor_weights[source_item]
            valid = neighbors >= 0
            np.add.at(scores, neighbors[valid], weights[valid])
        return scores


class FittedBPRMF:
    """Pairwise matrix-factorization comparator trained on TRAIN purchases."""

    def __init__(
        self,
        snapshot: Snapshot,
        protocol: PreparedProtocol,
        spec: HarmonizedBaselineSpec,
        user_factors: np.ndarray,
        item_factors: np.ndarray,
    ) -> None:
        dimensions = _positive_int(spec.parameters["embedding_dim"], "embedding_dim")
        users = np.asarray(user_factors, dtype=np.float64)
        items = np.asarray(item_factors, dtype=np.float64)
        if users.shape != (snapshot.manifest.num_users, dimensions):
            raise IntegrityError("BPR-MF user-factor shape is invalid")
        if items.shape != (snapshot.manifest.num_items, dimensions):
            raise IntegrityError("BPR-MF item-factor shape is invalid")
        if not np.isfinite(users).all() or not np.isfinite(items).all():
            raise IntegrityError("BPR-MF factors contain non-finite values")
        self.snapshot = snapshot
        self.protocol = protocol
        self.spec = spec
        self.user_factors = users
        self.item_factors = items
        self.descriptor = descriptor_for_baseline(spec)

    def describe(self) -> ModelDescriptor:
        return self.descriptor

    def parameter_arrays(self) -> dict[str, np.ndarray]:
        return {"user_factors": self.user_factors, "item_factors": self.item_factors}

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        if candidate_item_ids != self.protocol.candidate_item_ids:
            raise ScoreError("BPR-MF candidate order differs from the frozen protocol")
        return np.asarray(self.item_factors[list(candidate_item_ids)] @ self.user_factors[user_id])


HarmonizedBaseline = FittedItemKNN | FittedBPRMF


def _fit_itemknn(
    snapshot: Snapshot, protocol: PreparedProtocol, spec: HarmonizedBaselineSpec
) -> tuple[FittedItemKNN, dict[str, Any]]:
    item_count = snapshot.manifest.num_items
    if snapshot.manifest.num_users > np.iinfo(np.uint16).max:
        raise ContractError("ItemKNN v1 co-occurrence counter supports at most 65535 users")
    histories = _purchase_histories(snapshot.events_by_split["train"])
    support = np.zeros(item_count, dtype=np.int64)
    cooccurrence = np.zeros((item_count, item_count), dtype=np.uint16)
    for item_ids in histories.values():
        if not item_ids:
            continue
        ordered = np.asarray(sorted(item_ids), dtype=np.int64)
        support[ordered] += 1
        cooccurrence[np.ix_(ordered, ordered)] += 1
    np.fill_diagonal(cooccurrence, 0)

    width = min(_positive_int(spec.parameters["top_k"], "top_k"), max(1, item_count - 1))
    indices = np.full((item_count, width), -1, dtype=np.int64)
    weights = np.zeros((item_count, width), dtype=np.float64)
    raw_item_ids = np.asarray(snapshot.raw_item_ids, dtype=np.int64)
    for item_id in range(item_count):
        candidates = np.flatnonzero(cooccurrence[item_id])
        if not len(candidates):
            continue
        denominator = np.sqrt(support[item_id] * support[candidates]).astype(np.float64)
        similarities = cooccurrence[item_id, candidates].astype(np.float64) / denominator
        order = np.lexsort((raw_item_ids[candidates], -similarities))[:width]
        selected = candidates[order]
        count = len(selected)
        indices[item_id, :count] = selected
        weights[item_id, :count] = similarities[order]
    model = FittedItemKNN(snapshot, protocol, spec, indices, weights, support)
    return model, {
        "schema_version": "harmonized-baseline-training-report/1.0",
        "model_kind": "itemknn",
        "fit_scope": "TRAIN_PURCHASES_ONLY",
        "num_training_users": len(histories),
        "num_supported_items": int(np.count_nonzero(support)),
        "top_k": width,
        "stochastic": False,
    }


def _stable_bpr_gradient(delta: float) -> float:
    if delta >= 0:
        exponential = math.exp(-delta)
        return exponential / (1.0 + exponential)
    return 1.0 / (1.0 + math.exp(delta))


def _fit_bpr_mf(
    snapshot: Snapshot,
    protocol: PreparedProtocol,
    spec: HarmonizedBaselineSpec,
    seed: int,
) -> tuple[FittedBPRMF, dict[str, Any]]:
    if seed < 0:
        raise ContractError("seed must be non-negative")
    parameters = spec.parameters
    dimensions = _positive_int(parameters["embedding_dim"], "embedding_dim")
    epochs = _positive_int(parameters["epochs"], "epochs")
    learning_rate = _finite_float(parameters["learning_rate"], "learning_rate", positive=True)
    l2 = _finite_float(parameters["l2"], "l2")
    rng = np.random.Generator(np.random.PCG64(seed))
    user_factors = rng.normal(0.0, 0.01, (snapshot.manifest.num_users, dimensions))
    item_factors = rng.normal(0.0, 0.01, (snapshot.manifest.num_items, dimensions))
    pairs = [
        (event.user_id, event.item_id)
        for event in snapshot.events_by_split["train"]
        if event.event_type == "purchase"
    ]
    histories = _purchase_histories(snapshot.events_by_split["train"])
    losses: list[float] = []
    updates = 0
    for _epoch in range(epochs):
        epoch_loss = 0.0
        epoch_updates = 0
        for pair_index in rng.permutation(len(pairs)):
            user_id, positive = pairs[int(pair_index)]
            seen = histories[user_id]
            if len(seen) >= snapshot.manifest.num_items:
                continue
            negative = int(rng.integers(0, snapshot.manifest.num_items))
            while negative in seen:
                negative = int(rng.integers(0, snapshot.manifest.num_items))
            user_vector = user_factors[user_id].copy()
            positive_vector = item_factors[positive].copy()
            negative_vector = item_factors[negative].copy()
            delta = float(user_vector @ (positive_vector - negative_vector))
            gradient = _stable_bpr_gradient(delta)
            user_factors[user_id] += learning_rate * (
                gradient * (positive_vector - negative_vector) - l2 * user_vector
            )
            item_factors[positive] += learning_rate * (
                gradient * user_vector - l2 * positive_vector
            )
            item_factors[negative] += learning_rate * (
                -gradient * user_vector - l2 * negative_vector
            )
            epoch_loss += float(np.logaddexp(0.0, -delta))
            epoch_updates += 1
        if not np.isfinite(user_factors).all() or not np.isfinite(item_factors).all():
            raise ScoreError("BPR-MF training produced non-finite factors")
        losses.append(epoch_loss / max(1, epoch_updates))
        updates += epoch_updates
    model = FittedBPRMF(snapshot, protocol, spec, user_factors, item_factors)
    return model, {
        "schema_version": "harmonized-baseline-training-report/1.0",
        "model_kind": "bpr_mf",
        "fit_scope": "TRAIN_PURCHASES_ONLY",
        "seed": seed,
        "epochs": epochs,
        "updates": updates,
        "mean_loss_by_epoch": losses,
        "stochastic": True,
    }


def fit_harmonized_baseline(
    snapshot: Snapshot,
    protocol: PreparedProtocol,
    spec: HarmonizedBaselineSpec,
    *,
    seed: int,
) -> tuple[HarmonizedBaseline, dict[str, Any]]:
    if protocol.manifest.split != "val" or protocol.manifest.test_set_opened:
        raise ContractError("harmonized baselines must be fitted against validation selection")
    if spec.model_kind == "itemknn":
        return _fit_itemknn(snapshot, protocol, spec)
    return _fit_bpr_mf(snapshot, protocol, spec, seed)


def save_harmonized_baseline_checkpoint(
    model: HarmonizedBaseline,
    *,
    root: Path,
    run_id: str,
    seed: int,
    checkpoint_rule: str,
) -> dict[str, Any]:
    if root.exists():
        raise IntegrityError(f"baseline checkpoint root already exists: {root}")
    root.mkdir(parents=True)
    arrays = model.parameter_arrays()
    checkpoint_path = root / "checkpoint.npz"
    try:
        with checkpoint_path.open("wb") as stream:
            np.savez(stream, **cast(Any, arrays))
        payload = checkpoint_path.read_bytes()
    except OSError as error:
        raise IntegrityError("could not persist harmonized baseline checkpoint") from error
    manifest = {
        "schema_version": "harmonized-baseline-checkpoint/1.0",
        "run_id": run_id,
        "model_id": model.spec.model_id,
        "seed": seed,
        "checkpoint_rule": checkpoint_rule,
        "checkpoint_sha256": sha256_bytes(payload),
        "arrays": {
            name: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for name, value in arrays.items()
        },
        "spec": model.spec.to_mapping(),
        "descriptor": model.describe().to_mapping(),
    }
    (root / "manifest.json").write_bytes(canonical_json_bytes(manifest) + b"\n")
    return manifest


def load_harmonized_baseline_checkpoint(
    root: Path,
    *,
    snapshot: Snapshot,
    protocol: PreparedProtocol,
) -> tuple[HarmonizedBaseline, dict[str, Any]]:
    expected_files = {"checkpoint.npz", "manifest.json"}
    if {path.name for path in root.iterdir() if path.is_file()} != expected_files:
        raise IntegrityError("harmonized baseline checkpoint file set is invalid")
    manifest = load_strict_json(root / "manifest.json")
    expected_fields = {
        "schema_version",
        "run_id",
        "model_id",
        "seed",
        "checkpoint_rule",
        "checkpoint_sha256",
        "arrays",
        "spec",
        "descriptor",
    }
    if set(manifest) != expected_fields:
        raise IntegrityError("harmonized baseline checkpoint fields do not match schema")
    if manifest["schema_version"] != "harmonized-baseline-checkpoint/1.0":
        raise IntegrityError("unsupported harmonized baseline checkpoint schema")
    checkpoint_path = root / "checkpoint.npz"
    payload = checkpoint_path.read_bytes()
    if sha256_bytes(payload) != manifest["checkpoint_sha256"]:
        raise IntegrityError("harmonized baseline checkpoint hash mismatch")
    with np.load(checkpoint_path, allow_pickle=False) as loaded:
        arrays = {name: np.asarray(loaded[name]) for name in loaded.files}
    declarations = manifest["arrays"]
    if not isinstance(declarations, dict) or set(arrays) != set(declarations):
        raise IntegrityError("harmonized baseline checkpoint arrays disagree")
    for name, value in arrays.items():
        declaration = declarations[name]
        if (
            not isinstance(declaration, dict)
            or set(declaration) != {"shape", "dtype"}
            or declaration["shape"] != list(value.shape)
            or declaration["dtype"] != str(value.dtype)
            or not np.isfinite(value).all()
        ):
            raise IntegrityError(f"invalid harmonized baseline array: {name}")
    if not isinstance(manifest["spec"], dict) or not isinstance(manifest["descriptor"], dict):
        raise IntegrityError("harmonized baseline identity payload is invalid")
    spec = HarmonizedBaselineSpec.from_mapping(manifest["spec"])
    descriptor = descriptor_for_baseline(spec)
    if manifest["model_id"] != spec.model_id or manifest["descriptor"] != descriptor.to_mapping():
        raise IntegrityError("harmonized baseline checkpoint identity mismatch")
    if spec.model_kind == "itemknn":
        model: HarmonizedBaseline = FittedItemKNN(
            snapshot,
            protocol,
            spec,
            arrays["neighbor_indices"],
            arrays["neighbor_weights"],
            arrays["item_support"],
        )
    else:
        model = FittedBPRMF(
            snapshot,
            protocol,
            spec,
            arrays["user_factors"],
            arrays["item_factors"],
        )
    return model, manifest


__all__ = [
    "BASELINE_KINDS",
    "RECBOLE_REPOSITORY_URL",
    "RECBOLE_SOURCE_COMMIT",
    "FittedBPRMF",
    "FittedItemKNN",
    "HarmonizedBaselineSpec",
    "descriptor_for_baseline",
    "fit_harmonized_baseline",
    "load_harmonized_baseline_checkpoint",
    "save_harmonized_baseline_checkpoint",
]
