"""Confirmatory Deep-only, Rule-only, and artifact-bound Hybrid surfaces."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F

from ai_service_v2.array_types import Array
from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.pair_rules import PairRuleTable
from ai_service_v2.errors import ContractError, IntegrityError, ScoreError
from ai_service_v2.evaluation.artifacts import (
    MaterializedScores,
    ScoreBatch,
    iter_score_batches,
    materialize_scores,
)
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_bytes,
    sha256_file,
)
from ai_service_v2.protocol import EvaluationProtocol, protocol_manifest_sha256

HYBRID_LAMBDAS = frozenset({0.25, 0.5, 1.0, 2.0})
TEXT_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TEXT_DIMENSION = 384
CATEGORY_DIMENSION = 32


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True)
class ConfirmatoryTwoTowerConfig:
    tower_output_dim: int
    tower_hidden_dim: int
    negatives_per_positive: int
    learning_rate: float = 0.001
    weight_decay: float = 0.00001
    effective_batch_size: int = 1024
    max_epochs: int = 200
    early_stopping_patience: int = 20
    schema_version: str = "confirmatory-two-tower-config/1.0"
    budget_authority_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version not in {
            "confirmatory-two-tower-config/1.0",
            "confirmatory-two-tower-config/1.1",
        }:
            raise ContractError("unsupported confirmatory two-tower config")
        if self.tower_output_dim not in {64, 128}:
            raise ContractError("tower_output_dim is outside the frozen grid")
        if self.tower_hidden_dim not in {128, 256}:
            raise ContractError("tower_hidden_dim is outside the frozen grid")
        if self.negatives_per_positive not in {1, 4}:
            raise ContractError("negatives_per_positive is outside the frozen grid")
        fixed_values_differ = (
            self.learning_rate != 0.001
            or self.weight_decay != 0.00001
            or self.effective_batch_size != 1024
            or self.early_stopping_patience != 20
        )
        if fixed_values_differ:
            raise ContractError("two-tower fixed training values differ from authority")
        if self.schema_version == "confirmatory-two-tower-config/1.0":
            if self.max_epochs != 200 or self.budget_authority_sha256 is not None:
                raise ContractError("historical two-tower budget differs from authority")
            return
        if (
            self.tower_output_dim != 128
            or self.tower_hidden_dim != 256
            or self.negatives_per_positive != 4
            or self.max_epochs != 16
            or self.budget_authority_sha256 is None
            or not _is_sha256(self.budget_authority_sha256)
        ):
            raise ContractError("deadline two-tower budget differs from authority")

    def to_mapping(self) -> dict[str, Any]:
        mapping = {
            "schema_version": self.schema_version,
            "tower_output_dim": self.tower_output_dim,
            "tower_hidden_dim": self.tower_hidden_dim,
            "negatives_per_positive": self.negatives_per_positive,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "effective_batch_size": self.effective_batch_size,
            "max_epochs": self.max_epochs,
            "early_stopping_patience": self.early_stopping_patience,
            "objective": "PAIRWISE_BPR",
        }
        if self.budget_authority_sha256 is not None:
            mapping["budget_authority_sha256"] = self.budget_authority_sha256
        return mapping


@dataclass(frozen=True)
class ConfirmatoryItemFeatures:
    text_embeddings: Array
    category_ids: Array
    num_categories: int
    text_repository_revision: str
    text_model_materialization_sha256: str
    category_mapping_sha256: str
    candidate_order_sha256: str
    text_model_id: str = TEXT_MODEL_ID
    schema_version: str = "confirmatory-item-features/1.0"

    def __post_init__(self) -> None:
        text = np.asarray(self.text_embeddings)
        categories = np.asarray(self.category_ids)
        if (
            self.schema_version != "confirmatory-item-features/1.0"
            or self.text_model_id != TEXT_MODEL_ID
            or len(self.text_repository_revision) != 40
            or not all(
                _is_sha256(value)
                for value in (
                    self.text_model_materialization_sha256,
                    self.category_mapping_sha256,
                    self.candidate_order_sha256,
                )
            )
        ):
            raise ContractError("confirmatory item-feature authority mismatch")
        if (
            text.dtype != np.float32
            or text.ndim != 2
            or text.shape[1] != TEXT_DIMENSION
            or text.shape[0] < 1
            or not np.isfinite(text).all()
        ):
            raise ContractError("MiniLM feature matrix must be finite float32 [items,384]")
        if (
            categories.dtype != np.int64
            or categories.shape != (text.shape[0],)
            or self.num_categories < 1
            or bool((categories < 0).any())
            or bool((categories >= self.num_categories).any())
        ):
            raise ContractError("category IDs violate the frozen train-fit mapping")
        text_copy = np.array(text, dtype=np.float32, copy=True)
        category_copy = np.array(categories, dtype=np.int64, copy=True)
        text_copy.setflags(write=False)
        category_copy.setflags(write=False)
        object.__setattr__(self, "text_embeddings", cast(Array, text_copy))
        object.__setattr__(self, "category_ids", cast(Array, category_copy))

    @property
    def num_items(self) -> int:
        return int(self.text_embeddings.shape[0])

    @property
    def content_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(
            canonical_json_bytes(
                {
                    "schema_version": self.schema_version,
                    "text_model_id": self.text_model_id,
                    "text_repository_revision": self.text_repository_revision,
                    "text_model_materialization_sha256": self.text_model_materialization_sha256,
                    "category_mapping_sha256": self.category_mapping_sha256,
                    "candidate_order_sha256": self.candidate_order_sha256,
                    "num_items": self.num_items,
                    "num_categories": self.num_categories,
                    "text_dimension": TEXT_DIMENSION,
                    "category_dimension": CATEGORY_DIMENSION,
                    "price_included": False,
                }
            )
        )
        digest.update(np.asarray(self.text_embeddings, dtype="<f4").tobytes(order="C"))
        digest.update(np.asarray(self.category_ids, dtype="<i8").tobytes(order="C"))
        return digest.hexdigest()


class ConfirmatoryTwoTower(nn.Module):
    """Frozen MP2 two-tower architecture; checkpoint selection is external."""

    frozen_text_embeddings: Tensor
    frozen_category_ids: Tensor

    def __init__(
        self,
        *,
        num_users: int,
        features: ConfirmatoryItemFeatures,
        config: ConfirmatoryTwoTowerConfig,
    ) -> None:
        super().__init__()
        if num_users < 1:
            raise ContractError("confirmatory two-tower requires at least one user")
        output = config.tower_output_dim
        hidden = config.tower_hidden_dim
        self.num_users = num_users
        self.num_items = features.num_items
        self.config = config
        self.feature_content_sha256 = features.content_sha256
        self.candidate_order_sha256 = features.candidate_order_sha256
        self.user_embedding = nn.Embedding(num_users, output)
        self.item_embedding = nn.Embedding(features.num_items, output)
        self.category_embedding = nn.Embedding(features.num_categories, CATEGORY_DIMENSION)
        self.item_tower = nn.Sequential(
            nn.Linear(output + TEXT_DIMENSION + CATEGORY_DIMENSION, hidden),
            nn.GELU(),
            nn.Linear(hidden, output),
        )
        self.user_tower = nn.Sequential(
            nn.Linear(output * 2, hidden),
            nn.GELU(),
            nn.Linear(hidden, output),
        )
        self.register_buffer(
            "frozen_text_embeddings",
            torch.from_numpy(np.array(features.text_embeddings, dtype=np.float32, copy=True)),
            persistent=True,
        )
        self.register_buffer(
            "frozen_category_ids",
            torch.from_numpy(np.array(features.category_ids, dtype=np.int64, copy=True)),
            persistent=True,
        )
        self.frozen_text_embeddings.requires_grad_(False)
        self.frozen_category_ids.requires_grad_(False)

    def item_vectors(self, item_ids: Tensor) -> Tensor:
        if item_ids.dtype != torch.long or item_ids.ndim != 1 or item_ids.numel() < 1:
            raise ContractError("item IDs must be a non-empty int64 vector")
        if int(item_ids.min()) < 0 or int(item_ids.max()) >= self.num_items:
            raise ContractError("item IDs are outside the confirmatory catalog")
        return self._item_vectors_validated(item_ids)

    def _item_vectors_validated(self, item_ids: Tensor) -> Tensor:
        """Encode IDs already checked by a public entry point."""
        raw = torch.cat(
            (
                self.item_embedding(item_ids),
                self.frozen_text_embeddings[item_ids],
                self.category_embedding(self.frozen_category_ids[item_ids]),
            ),
            dim=1,
        )
        return F.normalize(self.item_tower(raw), p=2.0, dim=1, eps=1e-12)

    def user_vectors(
        self,
        user_ids: Tensor,
        history_item_ids: Sequence[tuple[int, ...]],
    ) -> Tensor:
        if user_ids.dtype != torch.long or user_ids.ndim != 1:
            raise ContractError("user IDs must be an int64 vector")
        if user_ids.numel() != len(history_item_ids) or user_ids.numel() < 1:
            raise ContractError("user/history batch dimensions differ")
        if int(user_ids.min()) < 0 or int(user_ids.max()) >= self.num_users:
            raise ContractError("user IDs are outside the confirmatory mapping")
        # Keep each history's tower call, reduction and autograd order unchanged.
        # Validate on the host once, then transfer one packed ID tensor instead
        # of synchronizing CUDA twice and transferring IDs for every history.
        packed = torch.tensor(
            [item for history in history_item_ids for item in history], dtype=torch.long
        )
        if packed.numel() and (int(packed.min()) < 0 or int(packed.max()) >= self.num_items):
            raise ContractError("item IDs are outside the confirmatory catalog")
        packed = packed.to(user_ids.device)
        offset = 0
        histories: list[Tensor] = []
        for history in history_item_ids:
            if not history:
                histories.append(
                    torch.zeros(
                        self.config.tower_output_dim,
                        dtype=self.user_embedding.weight.dtype,
                        device=user_ids.device,
                    )
                )
                continue
            item_tensor = packed[offset : offset + len(history)]
            offset += len(history)
            histories.append(self._item_vectors_validated(item_tensor).mean(dim=0))
        history_vectors = torch.stack(histories, dim=0)
        raw = torch.cat((self.user_embedding(user_ids), history_vectors), dim=1)
        return F.normalize(self.user_tower(raw), p=2.0, dim=1, eps=1e-12)

    def pairwise_scores(
        self,
        user_ids: Tensor,
        history_item_ids: Sequence[tuple[int, ...]],
        positive_item_ids: Tensor,
        negative_item_ids: Tensor,
    ) -> tuple[Tensor, Tensor]:
        if positive_item_ids.shape != user_ids.shape or negative_item_ids.shape != user_ids.shape:
            raise ContractError("pairwise item tensors must match the user batch")
        users = self.user_vectors(user_ids, history_item_ids)
        positives = self.item_vectors(positive_item_ids)
        negatives = self.item_vectors(negative_item_ids)
        return (users * positives).sum(dim=1), (users * negatives).sum(dim=1)

    def score_user(
        self,
        user_id: int,
        history_item_ids: tuple[int, ...],
        candidate_item_ids: tuple[int, ...],
    ) -> Array:
        if candidate_item_ids != tuple(range(self.num_items)):
            raise ScoreError("deep scorer candidate order differs from the frozen catalog")
        device = self.user_embedding.weight.device
        was_training = self.training
        self.eval()
        try:
            with torch.no_grad():
                candidates = torch.arange(self.num_items, dtype=torch.long, device=device)
                user = self.user_vectors(
                    torch.tensor([user_id], dtype=torch.long, device=device),
                    [history_item_ids],
                )[0]
                values = self.item_vectors(candidates) @ user
        finally:
            self.train(was_training)
        result = values.detach().cpu().numpy().astype(np.float32, copy=False)
        if result.shape != (self.num_items,) or not np.isfinite(result).all():
            raise ScoreError("deep two-tower emitted an invalid score vector")
        return cast(Array, result.copy())

    def state_sha256(self) -> str:
        digest = hashlib.sha256()
        for name, value in sorted(self.state_dict().items()):
            tensor = value.detach().cpu().contiguous()
            digest.update(
                canonical_json_bytes(
                    {
                        "name": name,
                        "shape": list(tensor.shape),
                        "dtype": str(tensor.dtype),
                    }
                )
            )
            digest.update(tensor.numpy().tobytes(order="C"))
        return digest.hexdigest()


def build_confirmatory_two_tower(
    *,
    num_users: int,
    features: ConfirmatoryItemFeatures,
    config: ConfirmatoryTwoTowerConfig,
    seed: int,
) -> ConfirmatoryTwoTower:
    if seed < 0:
        raise ContractError("two-tower seed must be non-negative")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return ConfirmatoryTwoTower(num_users=num_users, features=features, config=config)


def descriptor_for_deep(
    config: ConfirmatoryTwoTowerConfig,
    features: ConfirmatoryItemFeatures,
) -> ModelDescriptor:
    return ModelDescriptor(
        model_id="Deep-only",
        family="independent_deep_two_tower",
        implementation_provenance="ai-service-v2:confirmatory-two-tower:v1",
        repository_url=None,
        repository_commit=None,
        objective="pairwise_bpr",
        negative_sampler=(
            "uniform_train_catalog_excluding_prefix_history_and_target_atomic_basket"
        ),
        input_features=(
            "user_id",
            "item_id",
            "strict_prefix_history",
            "frozen_minilm_384d",
            "train_fit_category_32d",
        ),
        config_sha256=canonical_json_sha256(
            {
                "config": config.to_mapping(),
                "feature_content_sha256": features.content_sha256,
                "price_included": False,
            }
        ),
        adapter_revision="ai-service-v2:confirmatory-two-tower:v1",
    )


class DeepOnlyScorer:
    def __init__(
        self,
        protocol: EvaluationProtocol,
        model: ConfirmatoryTwoTower,
        descriptor: ModelDescriptor,
    ) -> None:
        if protocol.candidate_item_ids != tuple(range(model.num_items)):
            raise IntegrityError("deep scorer protocol candidate order mismatch")
        if protocol.manifest.candidate_order_sha256 != model.candidate_order_sha256:
            raise IntegrityError("deep scorer candidate hash mismatch")
        if "price" in descriptor.input_features:
            raise ContractError("price is prohibited from confirmatory Deep-only")
        self.protocol = protocol
        self.model = model
        self.descriptor = descriptor

    def describe(self) -> ModelDescriptor:
        return self.descriptor

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        history = tuple(sorted(self.protocol.case_for(user_id).history_item_ids))
        return self.model.score_user(user_id, history, candidate_item_ids)


class CachedDeepOnlyScorer:
    """Full-run scorer that computes the frozen candidate tower once."""

    def __init__(
        self,
        protocol: EvaluationProtocol,
        model: ConfirmatoryTwoTower,
        descriptor: ModelDescriptor,
    ) -> None:
        if protocol.candidate_item_ids != tuple(range(model.num_items)):
            raise IntegrityError("cached deep scorer protocol candidate order mismatch")
        if protocol.manifest.candidate_order_sha256 != model.candidate_order_sha256:
            raise IntegrityError("cached deep scorer candidate hash mismatch")
        if "price" in descriptor.input_features:
            raise ContractError("price is prohibited from confirmatory Deep-only")
        self.protocol = protocol
        self.model = model
        self.descriptor = descriptor
        device = model.user_embedding.weight.device
        was_training = model.training
        model.eval()
        try:
            with torch.no_grad():
                item_ids = torch.arange(model.num_items, dtype=torch.long, device=device)
                self._candidate_vectors = model.item_vectors(item_ids).detach()
        finally:
            model.train(was_training)

    def describe(self) -> ModelDescriptor:
        return self.descriptor

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        if candidate_item_ids != self.protocol.candidate_item_ids:
            raise ScoreError("cached deep scorer candidate order differs from protocol")
        history = tuple(sorted(self.protocol.case_for(user_id).history_item_ids))
        device = self.model.user_embedding.weight.device
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                user = self.model.user_vectors(
                    torch.tensor([user_id], dtype=torch.long, device=device),
                    [history],
                )[0]
                values = self._candidate_vectors @ user
        finally:
            self.model.train(was_training)
        result = values.detach().cpu().numpy().astype(np.float32, copy=False)
        if result.shape != (self.model.num_items,) or not np.isfinite(result).all():
            raise ScoreError("cached deep two-tower emitted an invalid score vector")
        return cast(Array, result.copy())


class ConfirmatoryRuleScorer:
    def __init__(self, protocol: EvaluationProtocol, rules: PairRuleTable) -> None:
        if protocol.manifest.candidate_order_sha256 != rules.candidate_order_sha256:
            raise IntegrityError("rule scorer candidate authority mismatch")
        self.protocol = protocol
        self.rules = rules

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        return self.rules.score(
            self.protocol.case_for(user_id).history_item_ids,
            candidate_item_ids,
        )


class _ScoreRowStream:
    def __init__(
        self,
        materialized: MaterializedScores,
        protocol: EvaluationProtocol,
    ) -> None:
        self._batches = iter_score_batches(
            materialized,
            protocol.eligible_user_ids,
            protocol.candidate_item_ids,
        )
        self._rows: Iterator[tuple[int, Array]] = iter(())

    def _batch_rows(self, batch: ScoreBatch) -> Iterator[tuple[int, Array]]:
        for index, user_id in enumerate(batch.user_ids):
            yield user_id, np.asarray(batch.scores[index], dtype=np.float32)

    def next(self) -> tuple[int, Array]:
        try:
            return next(self._rows)
        except StopIteration:
            try:
                batch = next(self._batches)
            except StopIteration as error:
                raise ScoreError("component score artifact ended early") from error
            self._rows = self._batch_rows(batch)
            return next(self._rows)


def _population_zscore_unmasked(
    values: Array,
    *,
    history_item_ids: frozenset[int],
    candidate_item_ids: tuple[int, ...],
) -> Array:
    scores = np.asarray(values, dtype=np.float64)
    if scores.shape != (len(candidate_item_ids),) or not np.isfinite(scores).all():
        raise ScoreError("Hybrid component score vector is invalid")
    positions = {item_id: index for index, item_id in enumerate(candidate_item_ids)}
    mask = np.ones(len(candidate_item_ids), dtype=bool)
    for item_id in history_item_ids:
        try:
            mask[positions[item_id]] = False
        except KeyError as error:
            raise IntegrityError("Hybrid history item is outside the candidate catalog") from error
    result = np.zeros(len(candidate_item_ids), dtype=np.float32)
    selected = scores[mask]
    if selected.size < 1:
        return cast(Array, result)
    standard_deviation = float(np.std(selected, ddof=0))
    if not math.isfinite(standard_deviation) or standard_deviation <= 0.0:
        return cast(Array, result)
    result[mask] = ((selected - float(np.mean(selected))) / standard_deviation).astype(np.float32)
    return cast(Array, result)


class HybridArtifactScorer:
    """One-pass fusion over immutable Deep and Rule score artifacts."""

    def __init__(
        self,
        protocol: EvaluationProtocol,
        deep_scores: MaterializedScores,
        rule_scores: MaterializedScores,
        *,
        rule_weight_lambda: float,
    ) -> None:
        parsed_lambda = float(rule_weight_lambda)
        if parsed_lambda not in HYBRID_LAMBDAS:
            raise ContractError("Hybrid lambda is outside the frozen grid")
        _validate_hybrid_component_authority(protocol, deep_scores, rule_scores)
        self.protocol = protocol
        self.rule_weight_lambda = parsed_lambda
        self._deep = _ScoreRowStream(deep_scores, protocol)
        self._rule = _ScoreRowStream(rule_scores, protocol)

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        if candidate_item_ids != self.protocol.candidate_item_ids:
            raise ScoreError("Hybrid candidate order differs from protocol")
        deep_user, deep = self._deep.next()
        rule_user, rule = self._rule.next()
        if deep_user != user_id or rule_user != user_id:
            raise IntegrityError("Hybrid component user order differs from protocol")
        return _fuse_hybrid_row(
            self.protocol,
            user_id,
            deep,
            rule,
            candidate_item_ids,
            self.rule_weight_lambda,
        )


def _validate_hybrid_component_authority(
    protocol: EvaluationProtocol,
    deep_scores: MaterializedScores,
    rule_scores: MaterializedScores,
) -> None:
    expected_protocol = protocol_manifest_sha256(protocol)
    deep_manifest = deep_scores.manifest
    rule_manifest = rule_scores.manifest
    if (
        deep_manifest.protocol_manifest_sha256 != expected_protocol
        or rule_manifest.protocol_manifest_sha256 != expected_protocol
        or deep_manifest.user_order_sha256 != rule_manifest.user_order_sha256
        or deep_manifest.candidate_order_sha256 != rule_manifest.candidate_order_sha256
        or deep_manifest.score_shape != rule_manifest.score_shape
        or deep_manifest.num_users != len(protocol.eligible_user_ids)
        or deep_manifest.num_candidates != len(protocol.candidate_item_ids)
    ):
        raise IntegrityError("Hybrid component score authorities differ")


def _fuse_hybrid_row(
    protocol: EvaluationProtocol,
    user_id: int,
    deep: Array,
    rule: Array,
    candidate_item_ids: tuple[int, ...],
    rule_weight_lambda: float,
) -> Array:
    history = protocol.case_for(user_id).history_item_ids
    normalized_deep = _population_zscore_unmasked(
        deep,
        history_item_ids=history,
        candidate_item_ids=candidate_item_ids,
    )
    normalized_rule = _population_zscore_unmasked(
        rule,
        history_item_ids=history,
        candidate_item_ids=candidate_item_ids,
    )
    fused = normalized_deep + rule_weight_lambda * normalized_rule
    if not np.isfinite(fused).all():
        raise ScoreError("Hybrid fusion produced a non-finite value")
    return np.asarray(fused, dtype=np.float32)


@dataclass(frozen=True)
class HybridScoreBatch:
    """Paired component batches and their transient fused representation."""

    deep: ScoreBatch
    rule: ScoreBatch
    hybrid: ScoreBatch

    def __post_init__(self) -> None:
        if (
            self.deep.first_user_index != self.rule.first_user_index
            or self.deep.first_user_index != self.hybrid.first_user_index
            or self.deep.user_ids != self.rule.user_ids
            or self.deep.user_ids != self.hybrid.user_ids
            or self.deep.scores.shape != self.rule.scores.shape
            or self.deep.scores.shape != self.hybrid.scores.shape
        ):
            raise IntegrityError("streaming Hybrid batch authorities differ")
        for values in (self.deep.scores, self.rule.scores, self.hybrid.scores):
            if (
                np.asarray(values).dtype != np.float32
                or np.asarray(values).ndim != 2
                or not np.isfinite(values).all()
            ):
                raise ScoreError("streaming Hybrid batch contains invalid scores")


def iter_hybrid_score_batches(
    protocol: EvaluationProtocol,
    deep_scores: MaterializedScores,
    rule_scores: MaterializedScores,
    *,
    rule_weight_lambda: float,
    batch_size: int = 128,
) -> Iterator[HybridScoreBatch]:
    """Yield bounded paired Deep/Rule/Hybrid batches without a full matrix."""

    parsed_lambda = float(rule_weight_lambda)
    if parsed_lambda not in HYBRID_LAMBDAS:
        raise ContractError("Hybrid lambda is outside the frozen grid")
    if batch_size < 1 or batch_size > 128:
        raise ContractError("streaming Hybrid batch size must be in [1,128]")
    _validate_hybrid_component_authority(protocol, deep_scores, rule_scores)
    deep_rows = _ScoreRowStream(deep_scores, protocol)
    rule_rows = _ScoreRowStream(rule_scores, protocol)
    users = protocol.eligible_user_ids
    candidates = protocol.candidate_item_ids
    for first in range(0, len(users), batch_size):
        selected_users = users[first : first + batch_size]
        deep_matrix = np.empty((len(selected_users), len(candidates)), dtype=np.float32)
        rule_matrix = np.empty_like(deep_matrix)
        for row_index, user_id in enumerate(selected_users):
            deep_user, deep = deep_rows.next()
            rule_user, rule = rule_rows.next()
            if deep_user != user_id or rule_user != user_id:
                raise IntegrityError("streaming Hybrid component user order differs")
            deep_matrix[row_index] = np.asarray(deep, dtype=np.float32)
            rule_matrix[row_index] = np.asarray(rule, dtype=np.float32)
        hybrid_matrix = np.empty_like(deep_matrix)
        for row_index, user_id in enumerate(selected_users):
            hybrid_matrix[row_index] = _fuse_hybrid_row(
                protocol,
                user_id,
                deep_matrix[row_index],
                rule_matrix[row_index],
                candidates,
                parsed_lambda,
            )
        yield HybridScoreBatch(
            deep=ScoreBatch(first, selected_users, deep_matrix),
            rule=ScoreBatch(first, selected_users, rule_matrix),
            hybrid=ScoreBatch(first, selected_users, hybrid_matrix),
        )


def _score_batch_sha256(batch: ScoreBatch) -> str:
    values = np.asarray(batch.scores, dtype="<f4", order="C")
    return sha256_bytes(values.tobytes(order="C"))


def _score_batch_user_order_sha256(batch: ScoreBatch) -> str:
    return canonical_json_sha256({"user_ids": list(batch.user_ids)})


def hybrid_streaming_batch_binding(batch: HybridScoreBatch) -> dict[str, Any]:
    """Return the deterministic bytes binding for one transient batch."""

    return {
        "schema_version": "hybrid-streaming-batch/1.0",
        "first_user_index": batch.hybrid.first_user_index,
        "user_count": len(batch.hybrid.user_ids),
        "user_ids_sha256": _score_batch_user_order_sha256(batch.hybrid),
        "score_shape": list(batch.hybrid.scores.shape),
        "score_dtype": "float32",
        "deep_scores_sha256": _score_batch_sha256(batch.deep),
        "rule_scores_sha256": _score_batch_sha256(batch.rule),
        "hybrid_scores_sha256": _score_batch_sha256(batch.hybrid),
        "finite": True,
    }


@dataclass(frozen=True)
class HybridFusionReceipt:
    deep_manifest_sha256: str
    rule_manifest_sha256: str
    hybrid_manifest_sha256: str
    protocol_manifest_sha256: str
    rule_weight_lambda: float
    float_tolerance: float = 1e-6
    schema_version: str = "hybrid-fusion-receipt/1.0"

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "deep_manifest_sha256": self.deep_manifest_sha256,
            "rule_manifest_sha256": self.rule_manifest_sha256,
            "hybrid_manifest_sha256": self.hybrid_manifest_sha256,
            "protocol_manifest_sha256": self.protocol_manifest_sha256,
            "rule_weight_lambda": self.rule_weight_lambda,
            "normalization": "POPULATION_ZSCORE_OVER_UNMASKED_CANDIDATES",
            "zero_or_nonfinite_standard_deviation": "ALL_ZERO_COMPONENT_VECTOR",
            "formula": "ZSCORE_DEEP_PLUS_LAMBDA_TIMES_ZSCORE_RULE",
            "float_tolerance": self.float_tolerance,
            "component_artifacts_mutated": False,
            "training_performed": False,
            "metrics_computed": False,
            "test_accessed": False,
        }


def materialize_hybrid_scores(
    protocol: EvaluationProtocol,
    deep_scores: MaterializedScores,
    rule_scores: MaterializedScores,
    *,
    root: Path,
    run_id: str,
    rule_weight_lambda: float,
    chunk_size: int = 128,
) -> tuple[MaterializedScores, HybridFusionReceipt]:
    deep_manifest_path = deep_scores.root / "manifest.json"
    rule_manifest_path = rule_scores.root / "manifest.json"
    deep_before = sha256_file(deep_manifest_path)
    rule_before = sha256_file(rule_manifest_path)
    scorer = HybridArtifactScorer(
        protocol,
        deep_scores,
        rule_scores,
        rule_weight_lambda=rule_weight_lambda,
    )
    hybrid = materialize_scores(
        protocol,
        scorer,
        root=root,
        run_id=run_id,
        model_id="Hybrid",
        chunk_size=chunk_size,
    )
    if (
        sha256_file(deep_manifest_path) != deep_before
        or sha256_file(rule_manifest_path) != rule_before
    ):
        raise IntegrityError("Hybrid fusion mutated a selected component artifact")
    receipt = HybridFusionReceipt(
        deep_manifest_sha256=deep_before,
        rule_manifest_sha256=rule_before,
        hybrid_manifest_sha256=sha256_file(root / "manifest.json"),
        protocol_manifest_sha256=protocol_manifest_sha256(protocol),
        rule_weight_lambda=float(rule_weight_lambda),
    )
    return hybrid, receipt


def hybrid_config_sha256(
    *,
    deep_manifest_sha256: str,
    rule_manifest_sha256: str,
    rule_weight_lambda: float,
) -> str:
    if not _is_sha256(deep_manifest_sha256) or not _is_sha256(rule_manifest_sha256):
        raise ContractError("Hybrid component manifest hash is invalid")
    if float(rule_weight_lambda) not in HYBRID_LAMBDAS:
        raise ContractError("Hybrid lambda is outside the frozen grid")
    return canonical_json_sha256(
        {
            "deep_manifest_sha256": deep_manifest_sha256,
            "rule_manifest_sha256": rule_manifest_sha256,
            "rule_weight_lambda": float(rule_weight_lambda),
            "normalization": "POPULATION_ZSCORE_OVER_UNMASKED_CANDIDATES",
            "formula": "ZSCORE_DEEP_PLUS_LAMBDA_TIMES_ZSCORE_RULE",
        }
    )


__all__ = [
    "CATEGORY_DIMENSION",
    "HYBRID_LAMBDAS",
    "TEXT_DIMENSION",
    "TEXT_MODEL_ID",
    "CachedDeepOnlyScorer",
    "ConfirmatoryItemFeatures",
    "ConfirmatoryRuleScorer",
    "ConfirmatoryTwoTower",
    "ConfirmatoryTwoTowerConfig",
    "DeepOnlyScorer",
    "HybridArtifactScorer",
    "HybridFusionReceipt",
    "HybridScoreBatch",
    "build_confirmatory_two_tower",
    "descriptor_for_deep",
    "hybrid_config_sha256",
    "hybrid_streaming_batch_binding",
    "iter_hybrid_score_batches",
    "materialize_hybrid_scores",
]
