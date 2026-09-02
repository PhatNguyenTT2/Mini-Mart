"""Small, deterministic proposed-model implementation for the research runner.

The implementation is intentionally dependency-light: it uses NumPy and a
manual BPR update so the protocol/evaluator can be exercised before a training
runtime is admitted.  It is a research implementation, not evidence that the
model outperforms any baseline.  A later reference adapter may replace the
trainer while preserving the same score-provider seam.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.rules import AprioriRuleTable
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError, ScoreError
from ai_service_v2.hashing import canonical_json_sha256
from ai_service_v2.protocol import PreparedProtocol


@dataclass(frozen=True)
class ItemFeatureMatrix:
    """Dense item features supplied to a content-aware tower."""

    values: np.ndarray
    source: str
    content_sha256: str

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=np.float32)
        if values.ndim != 2 or not values.shape[0] or not values.shape[1]:
            raise ContractError("item feature matrix must be a non-empty 2-D array")
        if not np.isfinite(values).all():
            raise ContractError("item feature matrix must be finite")
        if not self.source or len(self.content_sha256) != 64:
            raise ContractError("feature source and content hash are required")
        object.__setattr__(self, "values", np.array(values, dtype=np.float32, copy=True))


def item_text_hash_features(snapshot: Snapshot, *, dimensions: int = 32) -> ItemFeatureMatrix:
    """Create deterministic hashed text/category/price features for fixtures.

    This helper is explicitly labelled as a hash-feature source.  It is not a
    substitute for the source-bound encoder required by the final paper run.
    """

    if dimensions < 4:
        raise ValueError("dimensions must be at least four")
    values = np.zeros((snapshot.manifest.num_items, dimensions), dtype=np.float32)
    for item_id in snapshot.items:
        record = snapshot.item_records[item_id]
        tokens = (record.text + " " + record.category).lower().split()
        for token in tokens:
            token_digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(token_digest[:4], "big") % (dimensions - 2)
            values[item_id, index] += 1.0
        values[item_id, -2] = float(record.price or 0.0)
        values[item_id, -1] = 1.0
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    values = values / np.maximum(norms, 1e-12)
    content_digest = hashlib.sha256(values.tobytes()).hexdigest()
    return ItemFeatureMatrix(values, "deterministic_hash_features", content_digest)


@dataclass(frozen=True)
class TwoTowerConfig:
    embedding_dim: int = 16
    hidden_dim: int = 32
    epochs: int = 5
    learning_rate: float = 0.03
    l2: float = 1e-5
    negatives_per_positive: int = 1

    def __post_init__(self) -> None:
        if self.embedding_dim < 2 or self.hidden_dim < 2:
            raise ContractError("tower dimensions must be at least two")
        if self.epochs < 1 or self.negatives_per_positive < 1:
            raise ContractError("epochs and negatives_per_positive must be positive")
        if self.learning_rate <= 0 or self.l2 < 0:
            raise ContractError("learning_rate must be positive and l2 non-negative")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "negatives_per_positive": self.negatives_per_positive,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> TwoTowerConfig:
        allowed = {
            "embedding_dim",
            "hidden_dim",
            "epochs",
            "learning_rate",
            "l2",
            "negatives_per_positive",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ContractError(f"unknown two-tower config fields: {', '.join(unknown)}")
        return cls(**value)


@dataclass
class _Parameters:
    user_embedding: np.ndarray
    history_embedding: np.ndarray
    item_embedding: np.ndarray
    content_projection: np.ndarray
    user_w1: np.ndarray
    user_b1: np.ndarray
    user_w2: np.ndarray
    user_b2: np.ndarray
    item_w1: np.ndarray
    item_b1: np.ndarray
    item_w2: np.ndarray
    item_b2: np.ndarray


@dataclass(frozen=True)
class TrainingReport:
    seed: int
    epochs: int
    update_count: int
    mean_loss_by_epoch: tuple[float, ...]
    config_sha256: str


class TrainedTwoTower:
    """Nonlinear user/item towers exposing only a score-provider interface."""

    def __init__(
        self,
        snapshot: Snapshot,
        features: ItemFeatureMatrix,
        parameters: _Parameters,
        descriptor: ModelDescriptor,
        train_history: dict[int, frozenset[int]],
    ) -> None:
        if features.values.shape[0] != snapshot.manifest.num_items:
            raise ContractError("feature matrix item count does not match snapshot")
        self.snapshot = snapshot
        self.features = features
        self._p = parameters
        self._descriptor = descriptor
        self._train_history = train_history

    def describe(self) -> ModelDescriptor:
        return self._descriptor

    def with_descriptor(self, descriptor: ModelDescriptor) -> TrainedTwoTower:
        """Return a view with an explicit registry descriptor."""

        if descriptor.config_sha256 != self._descriptor.config_sha256:
            raise ContractError("replacement descriptor config hash does not match model")
        return TrainedTwoTower(
            self.snapshot,
            self.features,
            self._p,
            descriptor,
            self._train_history,
        )

    def parameter_arrays(self) -> dict[str, np.ndarray]:
        """Return defensive copies in a stable order for checkpointing."""

        p = self._p
        return {
            "user_embedding": p.user_embedding.copy(),
            "history_embedding": p.history_embedding.copy(),
            "item_embedding": p.item_embedding.copy(),
            "content_projection": p.content_projection.copy(),
            "user_w1": p.user_w1.copy(),
            "user_b1": p.user_b1.copy(),
            "user_w2": p.user_w2.copy(),
            "user_b2": p.user_b2.copy(),
            "item_w1": p.item_w1.copy(),
            "item_b1": p.item_b1.copy(),
            "item_w2": p.item_w2.copy(),
            "item_b2": p.item_b2.copy(),
        }

    @classmethod
    def from_parameter_arrays(
        cls,
        snapshot: Snapshot,
        features: ItemFeatureMatrix,
        arrays: dict[str, np.ndarray],
        descriptor: ModelDescriptor,
    ) -> TrainedTwoTower:
        """Restore a model only from a complete, shape-compatible checkpoint."""

        required = {
            "user_embedding",
            "history_embedding",
            "item_embedding",
            "content_projection",
            "user_w1",
            "user_b1",
            "user_w2",
            "user_b2",
            "item_w1",
            "item_b1",
            "item_w2",
            "item_b2",
        }
        if set(arrays) != required:
            raise ContractError("checkpoint arrays do not match the two-tower schema")
        copied = {
            name: np.asarray(value, dtype=np.float64).copy() for name, value in arrays.items()
        }
        if any(array.ndim != 2 for name, array in copied.items() if name.endswith("embedding")):
            raise ContractError("embedding checkpoint arrays must be two-dimensional")
        if copied["user_w1"].ndim != 2 or copied["item_w1"].ndim != 2:
            raise ContractError("tower weight arrays must be two-dimensional")
        dimensions = copied["user_embedding"].shape[1]
        hidden = copied["user_w1"].shape[1]
        feature_count = features.values.shape[1]
        expected_shapes = {
            "user_embedding": (snapshot.manifest.num_users, dimensions),
            "history_embedding": (snapshot.manifest.num_users, dimensions),
            "item_embedding": (snapshot.manifest.num_items, dimensions),
            "content_projection": (feature_count, dimensions),
            "user_w1": (dimensions, hidden),
            "user_b1": (hidden,),
            "user_w2": (hidden, dimensions),
            "user_b2": (dimensions,),
            "item_w1": (dimensions, hidden),
            "item_b1": (hidden,),
            "item_w2": (hidden, dimensions),
            "item_b2": (dimensions,),
        }
        for name, expected in expected_shapes.items():
            if copied[name].shape != expected:
                raise ContractError(f"checkpoint array shape mismatch: {name}")
            if not np.isfinite(copied[name]).all():
                raise ContractError(f"checkpoint array is non-finite: {name}")
        return cls(
            snapshot,
            features,
            _Parameters(**copied),
            descriptor,
            _train_history_for_snapshot(snapshot),
        )

    def _user_vector(self, user_id: int) -> np.ndarray:
        if user_id < 0 or user_id >= self.snapshot.manifest.num_users:
            raise ScoreError("unknown user ID")
        p = self._p
        hidden = np.tanh(
            (p.user_embedding[user_id] + p.history_embedding[user_id]) @ p.user_w1 + p.user_b1
        )
        return cast(np.ndarray, hidden @ p.user_w2 + p.user_b2)

    def _item_vectors(self, item_ids: tuple[int, ...]) -> np.ndarray:
        if any(item < 0 or item >= self.snapshot.manifest.num_items for item in item_ids):
            raise ScoreError("unknown candidate item ID")
        p = self._p
        base = p.item_embedding[list(item_ids)] + (
            self.features.values[list(item_ids)] @ p.content_projection
        )
        hidden = np.tanh(base @ p.item_w1 + p.item_b1)
        return cast(np.ndarray, hidden @ p.item_w2 + p.item_b2)

    def deep_scores(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        user_vector = self._user_vector(user_id)
        item_vectors = self._item_vectors(candidate_item_ids)
        return np.asarray(item_vectors @ user_vector, dtype=np.float64)

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        return self.deep_scores(user_id, candidate_item_ids)


class RuleOnlyScorer:
    """Wide association-rule condition using TRAIN history only."""

    def __init__(self, protocol: PreparedProtocol, rules: AprioriRuleTable) -> None:
        self.protocol = protocol
        self.rules = rules

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        history = set(self.protocol.case_for(user_id).history_item_ids)
        return np.asarray(
            [self.rules.score(history, item_id) for item_id in candidate_item_ids], dtype=np.float64
        )


@dataclass(frozen=True)
class HybridScoreBreakdown:
    deep_scores: np.ndarray
    wide_scores: np.ndarray
    hybrid_scores: np.ndarray


class HybridScorer:
    """Additive fusion with a frozen, explicit wide coefficient."""

    def __init__(
        self,
        deep: TrainedTwoTower,
        wide: RuleOnlyScorer,
        *,
        wide_weight: float = 1.0,
        fusion_normalization: str = "none",
    ) -> None:
        if not math.isfinite(wide_weight) or wide_weight < 0:
            raise ContractError("wide_weight must be finite and non-negative")
        if fusion_normalization not in {"none", "per_user_zscore"}:
            raise ContractError("unsupported hybrid fusion normalization")
        self.deep = deep
        self.wide = wide
        self.wide_weight = wide_weight
        self.fusion_normalization = fusion_normalization

    def _normalize(self, values: np.ndarray) -> np.ndarray:
        if self.fusion_normalization == "none":
            return values
        standard_deviation = float(np.std(values))
        if standard_deviation <= 1e-12:
            return np.zeros_like(values, dtype=np.float64)
        return np.asarray((values - float(np.mean(values))) / standard_deviation, dtype=np.float64)

    def deep_component_scores(
        self, user_id: int, candidate_item_ids: tuple[int, ...]
    ) -> np.ndarray:
        """Return the exact normalized Deep component consumed by fusion."""

        return self._normalize(self.deep.deep_scores(user_id, candidate_item_ids))

    def wide_component_scores(
        self, user_id: int, candidate_item_ids: tuple[int, ...]
    ) -> np.ndarray:
        """Return the exact normalized Wide component consumed by fusion."""

        return self._normalize(self.wide(user_id, candidate_item_ids))

    def breakdown(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> HybridScoreBreakdown:
        deep_scores = self.deep_component_scores(user_id, candidate_item_ids)
        wide_scores = self.wide_component_scores(user_id, candidate_item_ids)
        hybrid_scores = deep_scores + self.wide_weight * wide_scores
        return HybridScoreBreakdown(deep_scores, wide_scores, hybrid_scores)

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        return self.breakdown(user_id, candidate_item_ids).hybrid_scores


def _initial_parameters(
    snapshot: Snapshot, feature_count: int, config: TwoTowerConfig, seed: int
) -> _Parameters:
    rng = np.random.Generator(np.random.PCG64(seed))
    d, h = config.embedding_dim, config.hidden_dim
    scale = 1.0 / math.sqrt(d)
    item_embedding = rng.normal(0, scale, (snapshot.manifest.num_items, d)).astype(np.float64)
    train_history = _train_history_for_snapshot(snapshot)
    history_embedding = np.zeros((snapshot.manifest.num_users, d), dtype=np.float64)
    for user, items in train_history.items():
        if items:
            history_embedding[user] = item_embedding[sorted(items)].mean(axis=0)
    return _Parameters(
        user_embedding=rng.normal(0, scale, (snapshot.manifest.num_users, d)),
        history_embedding=history_embedding,
        item_embedding=item_embedding,
        content_projection=rng.normal(0, 0.05, (feature_count, d)),
        user_w1=rng.normal(0, 0.05, (d, h)),
        user_b1=np.zeros(h),
        user_w2=rng.normal(0, 0.05, (h, d)),
        user_b2=np.zeros(d),
        item_w1=rng.normal(0, 0.05, (d, h)),
        item_b1=np.zeros(h),
        item_w2=rng.normal(0, 0.05, (h, d)),
        item_b2=np.zeros(d),
    )


def _train_history_for_snapshot(snapshot: Snapshot) -> dict[int, frozenset[int]]:
    history: dict[int, set[int]] = defaultdict(set)
    for event in snapshot.events_by_split["train"]:
        history[event.user_id].add(event.item_id)
    return {user: frozenset(items) for user, items in history.items()}


def _train_pairs(
    snapshot: Snapshot, seed: int, negatives_per_positive: int
) -> list[tuple[int, int, int]]:
    rng = np.random.Generator(np.random.PCG64(seed))
    all_items = np.arange(snapshot.manifest.num_items, dtype=np.int64)
    seen: dict[int, set[int]] = defaultdict(set)
    positives_by_user: dict[int, list[int]] = defaultdict(list)
    for event in snapshot.events_by_split["train"]:
        seen[event.user_id].add(event.item_id)
        if event.event_type == "purchase":
            positives_by_user[event.user_id].append(event.item_id)
    pairs: list[tuple[int, int, int]] = []
    for user_id in sorted(positives_by_user):
        seen_items = np.fromiter(sorted(seen[user_id]), dtype=np.int64)
        available = np.setdiff1d(
            all_items,
            seen_items,
            assume_unique=True,
        )
        if not len(available):
            continue
        for positive in positives_by_user[user_id]:
            for _ in range(negatives_per_positive):
                negative = int(available[rng.integers(0, len(available))])
                pairs.append((user_id, positive, negative))
    if not pairs:
        raise ContractError("training data produced no valid BPR pairs")
    return pairs


def _tower_forward_user(p: _Parameters, user_id: int) -> tuple[np.ndarray, np.ndarray]:
    pre = (p.user_embedding[user_id] + p.history_embedding[user_id]) @ p.user_w1 + p.user_b1
    hidden = np.tanh(pre)
    return hidden, hidden @ p.user_w2 + p.user_b2


def _tower_forward_item(
    p: _Parameters, features: np.ndarray, item_id: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base = p.item_embedding[item_id] + features[item_id] @ p.content_projection
    pre = base @ p.item_w1 + p.item_b1
    hidden = np.tanh(pre)
    return base, hidden, hidden @ p.item_w2 + p.item_b2


def _apply_pair_update(
    p: _Parameters,
    features: np.ndarray,
    user_id: int,
    positive: int,
    negative: int,
    learning_rate: float,
    l2: float,
) -> float:
    user_hidden, user_vector = _tower_forward_user(p, user_id)
    pos_base, pos_hidden, pos_vector = _tower_forward_item(p, features, positive)
    neg_base, neg_hidden, neg_vector = _tower_forward_item(p, features, negative)
    delta = float(np.dot(user_vector, pos_vector - neg_vector))
    sigmoid_negative = 1.0 / (1.0 + math.exp(min(60.0, max(-60.0, delta))))
    gradient = -sigmoid_negative

    grad_user_vector = gradient * (pos_vector - neg_vector)
    grad_pos_vector = gradient * user_vector
    grad_neg_vector = -gradient * user_vector

    grad_user_w2 = np.outer(user_hidden, grad_user_vector)
    grad_user_b2 = grad_user_vector
    grad_user_hidden = grad_user_vector @ p.user_w2.T
    grad_user_pre = grad_user_hidden * (1.0 - user_hidden * user_hidden)
    grad_user_input = grad_user_pre @ p.user_w1.T
    grad_user_w1 = np.outer(p.user_embedding[user_id] + p.history_embedding[user_id], grad_user_pre)
    grad_user_b1 = grad_user_pre

    grad_item_w2 = np.outer(pos_hidden, grad_pos_vector) + np.outer(neg_hidden, grad_neg_vector)
    grad_item_b2 = grad_pos_vector + grad_neg_vector
    grad_pos_hidden = grad_pos_vector @ p.item_w2.T
    grad_neg_hidden = grad_neg_vector @ p.item_w2.T
    grad_pos_pre = grad_pos_hidden * (1.0 - pos_hidden * pos_hidden)
    grad_neg_pre = grad_neg_hidden * (1.0 - neg_hidden * neg_hidden)
    grad_pos_base = grad_pos_pre @ p.item_w1.T
    grad_neg_base = grad_neg_pre @ p.item_w1.T
    grad_item_w1 = np.outer(pos_base, grad_pos_pre) + np.outer(neg_base, grad_neg_pre)
    grad_item_b1 = grad_pos_pre + grad_neg_pre

    p.user_w2 -= learning_rate * (grad_user_w2 + l2 * p.user_w2)
    p.user_b2 -= learning_rate * grad_user_b2
    p.user_w1 -= learning_rate * (grad_user_w1 + l2 * p.user_w1)
    p.user_b1 -= learning_rate * grad_user_b1
    p.user_embedding[user_id] -= learning_rate * (grad_user_input + l2 * p.user_embedding[user_id])
    p.history_embedding[user_id] -= learning_rate * (
        grad_user_input + l2 * p.history_embedding[user_id]
    )
    p.item_w2 -= learning_rate * (grad_item_w2 + l2 * p.item_w2)
    p.item_b2 -= learning_rate * grad_item_b2
    p.item_w1 -= learning_rate * (grad_item_w1 + l2 * p.item_w1)
    p.item_b1 -= learning_rate * grad_item_b1
    p.item_embedding[positive] -= learning_rate * (grad_pos_base + l2 * p.item_embedding[positive])
    p.item_embedding[negative] -= learning_rate * (grad_neg_base + l2 * p.item_embedding[negative])
    p.content_projection -= learning_rate * (
        np.outer(features[positive], grad_pos_base)
        + np.outer(features[negative], grad_neg_base)
        + l2 * p.content_projection
    )
    return float(math.log1p(math.exp(min(60.0, max(-60.0, -delta)))))


def train_two_tower(
    snapshot: Snapshot,
    features: ItemFeatureMatrix,
    *,
    config: TwoTowerConfig | None = None,
    seed: int = 42,
    model_id: str = "independent-deep-two-tower-v1",
    descriptor: ModelDescriptor | None = None,
) -> tuple[TrainedTwoTower, TrainingReport]:
    """Train a deterministic BPR two-tower candidate on TRAIN only."""

    config = config or TwoTowerConfig()
    if features.values.shape[0] != snapshot.manifest.num_items:
        raise ContractError("feature matrix item count does not match snapshot")
    if seed < 0:
        raise ContractError("seed must be non-negative")
    parameters = _initial_parameters(snapshot, features.values.shape[1], config, seed)
    pairs = _train_pairs(snapshot, seed, config.negatives_per_positive)
    training_features = features.values.astype(np.float64)
    losses: list[float] = []
    update_count = 0
    for _epoch in range(config.epochs):
        epoch_losses: list[float] = []
        for user_id, positive, negative in pairs:
            epoch_losses.append(
                _apply_pair_update(
                    parameters,
                    training_features,
                    user_id,
                    positive,
                    negative,
                    config.learning_rate,
                    config.l2,
                )
            )
            update_count += 1
        losses.append(float(np.mean(epoch_losses)))
    config_hash = canonical_json_sha256(config.to_mapping())
    if descriptor is None:
        descriptor = ModelDescriptor(
            model_id=model_id,
            family="deep_two_tower",
            implementation_provenance="local-research-runner-v1",
            repository_url=None,
            repository_commit=None,
            objective="pairwise_bpr",
            negative_sampler="train_seen_exclusion_pcg64",
            input_features=(
                "user_id",
                "train_history",
                "item_text_features",
                "category",
                "price",
            ),
            config_sha256=config_hash,
            adapter_revision="ai-service-v2:proposed:v1",
        )
    elif (
        descriptor.model_id != model_id
        or descriptor.objective != "pairwise_bpr"
        or descriptor.negative_sampler != "train_seen_exclusion_pcg64"
        or descriptor.adapter_revision != "ai-service-v2:proposed:v1"
    ):
        raise ContractError("supplied two-tower descriptor is incompatible with the trainer")
    history = defaultdict(set)
    for event in snapshot.events_by_split["train"]:
        history[event.user_id].add(event.item_id)
    model = TrainedTwoTower(
        snapshot,
        features,
        parameters,
        descriptor,
        {user: frozenset(items) for user, items in history.items()},
    )
    return model, TrainingReport(seed, config.epochs, update_count, tuple(losses), config_hash)


__all__ = [
    "HybridScoreBreakdown",
    "HybridScorer",
    "ItemFeatureMatrix",
    "RuleOnlyScorer",
    "TrainedTwoTower",
    "TrainingReport",
    "TwoTowerConfig",
    "item_text_hash_features",
    "train_two_tower",
]
