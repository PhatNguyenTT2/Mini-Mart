from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from ai_service_v2.array_types import Array
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.evaluation.artifacts import (
    MaterializedScores,
    load_score_matrix,
    materialize_scores,
)
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.models.confirmatory import (
    CachedDeepOnlyScorer,
    ConfirmatoryItemFeatures,
    ConfirmatoryTwoTowerConfig,
    DeepOnlyScorer,
    build_confirmatory_two_tower,
    descriptor_for_deep,
    hybrid_streaming_batch_binding,
    iter_hybrid_score_batches,
    materialize_hybrid_scores,
)
from ai_service_v2.protocol import PreparedProtocol, build_protocol


def _features(protocol: PreparedProtocol) -> ConfirmatoryItemFeatures:
    num_items = len(protocol.candidate_item_ids)
    text = np.arange(num_items * 384, dtype=np.float32).reshape(num_items, 384)
    text /= 10_000.0
    categories = np.asarray([index % 3 for index in range(num_items)], dtype=np.int64)
    return ConfirmatoryItemFeatures(
        text_embeddings=text,
        category_ids=categories,
        num_categories=3,
        text_repository_revision="c" * 40,
        text_model_materialization_sha256="d" * 64,
        category_mapping_sha256="e" * 64,
        candidate_order_sha256=protocol.manifest.candidate_order_sha256,
    )


def _config() -> ConfirmatoryTwoTowerConfig:
    return ConfirmatoryTwoTowerConfig(
        tower_output_dim=64,
        tower_hidden_dim=128,
        negatives_per_positive=1,
    )


def test_confirmatory_two_tower_is_deterministic_normalized_and_price_free(
    snapshot: Snapshot,
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    features = _features(protocol)
    first = build_confirmatory_two_tower(
        num_users=snapshot.manifest.num_users,
        features=features,
        config=_config(),
        seed=42,
    )
    second = build_confirmatory_two_tower(
        num_users=snapshot.manifest.num_users,
        features=features,
        config=_config(),
        seed=42,
    )
    assert first.state_sha256() == second.state_sha256()
    assert first.frozen_text_embeddings.requires_grad is False
    assert first.category_embedding.embedding_dim == 32
    item_vectors = first.item_vectors(torch.arange(features.num_items, dtype=torch.long))
    assert torch.allclose(
        torch.linalg.vector_norm(item_vectors, dim=1),
        torch.ones(features.num_items),
        atol=1e-6,
    )
    descriptor = descriptor_for_deep(_config(), features)
    assert "price" not in descriptor.input_features
    assert descriptor.objective == "pairwise_bpr"


def test_deep_only_scorer_exports_finite_full_catalog_scores(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    features = _features(protocol)
    model = build_confirmatory_two_tower(
        num_users=snapshot.manifest.num_users,
        features=features,
        config=_config(),
        seed=7,
    )
    scorer = DeepOnlyScorer(protocol, model, descriptor_for_deep(_config(), features))
    user_id = protocol.eligible_user_ids[0]
    values = scorer(user_id, protocol.candidate_item_ids)
    assert values.shape == (snapshot.manifest.num_items,)
    assert values.dtype == np.float32
    assert np.isfinite(values).all()


def test_cached_deep_scorer_matches_uncached_scores(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    features = _features(protocol)
    model = build_confirmatory_two_tower(
        num_users=snapshot.manifest.num_users,
        features=features,
        config=_config(),
        seed=11,
    )
    descriptor = descriptor_for_deep(_config(), features)
    uncached = DeepOnlyScorer(protocol, model, descriptor)
    cached = CachedDeepOnlyScorer(protocol, model, descriptor)
    for user_id in protocol.eligible_user_ids:
        assert np.allclose(
            cached(user_id, protocol.candidate_item_ids),
            uncached(user_id, protocol.candidate_item_ids),
            atol=1e-6,
        )


def test_confirmatory_config_rejects_nonfrozen_dimensions() -> None:
    with pytest.raises(ContractError, match="output_dim"):
        ConfirmatoryTwoTowerConfig(
            tower_output_dim=32,
            tower_hidden_dim=128,
            negatives_per_positive=1,
        )


class _FixedScorer:
    def __init__(self, protocol: PreparedProtocol, *, reverse: bool = False) -> None:
        self.protocol = protocol
        self.reverse = reverse

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        assert candidate_item_ids == self.protocol.candidate_item_ids
        values = np.arange(len(candidate_item_ids), dtype=np.float32)
        if self.reverse:
            values = values[::-1].copy()
        return values + np.float32(user_id / 10.0)


def _zscore_unmasked(
    values: np.ndarray,
    history: frozenset[int],
) -> np.ndarray:
    mask = np.ones(len(values), dtype=bool)
    mask[list(history)] = False
    result = np.zeros(len(values), dtype=np.float32)
    selected = values[mask].astype(np.float64)
    standard_deviation = float(np.std(selected, ddof=0))
    if standard_deviation > 0:
        result[mask] = ((selected - float(np.mean(selected))) / standard_deviation).astype(
            np.float32
        )
    return result


def test_hybrid_fusion_reuses_immutable_components_and_masks_before_zscore(
    snapshot: Snapshot,
    tmp_path: Path,
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    deep = materialize_scores(
        protocol,
        _FixedScorer(protocol),
        root=tmp_path / "deep",
        run_id="deep-fixture",
        model_id="Deep-only",
        chunk_size=1,
    )
    rule = materialize_scores(
        protocol,
        _FixedScorer(protocol, reverse=True),
        root=tmp_path / "rule",
        run_id="rule-fixture",
        model_id="Rule-only",
        chunk_size=2,
    )
    deep_before = (deep.root / "manifest.json").read_bytes()
    rule_before = (rule.root / "manifest.json").read_bytes()
    hybrid, receipt = materialize_hybrid_scores(
        protocol,
        deep,
        rule,
        root=tmp_path / "hybrid",
        run_id="hybrid-fixture",
        rule_weight_lambda=0.5,
        chunk_size=2,
    )
    assert (deep.root / "manifest.json").read_bytes() == deep_before
    assert (rule.root / "manifest.json").read_bytes() == rule_before
    assert receipt.to_mapping()["component_artifacts_mutated"] is False
    matrix = load_score_matrix(hybrid)
    for row_index, user_id in enumerate(protocol.eligible_user_ids):
        deep_values = _FixedScorer(protocol)(user_id, protocol.candidate_item_ids)
        rule_values = _FixedScorer(protocol, reverse=True)(user_id, protocol.candidate_item_ids)
        history = protocol.case_for(user_id).history_item_ids
        expected = _zscore_unmasked(deep_values, history) + 0.5 * _zscore_unmasked(
            rule_values, history
        )
        assert np.allclose(matrix[row_index], expected, atol=1e-6)


def test_streaming_hybrid_is_byte_ranking_and_metric_equivalent(
    snapshot: Snapshot,
    tmp_path: Path,
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    deep = materialize_scores(
        protocol,
        _FixedScorer(protocol),
        root=tmp_path / "deep",
        run_id="deep-stream-fixture",
        model_id="Deep-only",
        chunk_size=1,
    )
    rule = materialize_scores(
        protocol,
        _FixedScorer(protocol, reverse=True),
        root=tmp_path / "rule",
        run_id="rule-stream-fixture",
        model_id="Rule-only",
        chunk_size=1,
    )
    hybrid, _ = materialize_hybrid_scores(
        protocol,
        deep,
        rule,
        root=tmp_path / "hybrid",
        run_id="hybrid-stream-fixture",
        rule_weight_lambda=0.5,
        chunk_size=1,
    )
    bundles = tuple(
        iter_hybrid_score_batches(
            protocol,
            deep,
            rule,
            rule_weight_lambda=0.5,
            batch_size=128,
        )
    )
    streamed_matrix = np.concatenate(
        [np.asarray(bundle.hybrid.scores) for bundle in bundles],
        axis=0,
    )
    assert len(bundles) == 1
    assert len(bundles[0].hybrid.user_ids) < 128
    assert np.array_equal(streamed_matrix, load_score_matrix(hybrid))
    binding = hybrid_streaming_batch_binding(bundles[0])
    assert binding["finite"] is True
    assert binding["score_shape"] == list(streamed_matrix.shape)

    evaluator = FullCatalogEvaluator(protocol)
    streamed = evaluator.evaluate_batches(
        (bundle.hybrid for bundle in bundles),
        run_id="hybrid-stream-fixture",
        model_id="Hybrid",
    )
    assert streamed == evaluator.evaluate_artifact(hybrid)


def test_streaming_hybrid_zero_variance_and_callback_crash_preserve_components(
    snapshot: Snapshot,
    tmp_path: Path,
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    def constant_scorer(user_id: int, candidate_item_ids: tuple[int, ...]) -> Array:
        del user_id
        return np.ones(len(candidate_item_ids), dtype=np.float32)

    deep = materialize_scores(
        protocol,
        constant_scorer,
        root=tmp_path / "deep",
        run_id="deep-zero",
        model_id="Deep-only",
        chunk_size=1,
    )
    rule = materialize_scores(
        protocol,
        constant_scorer,
        root=tmp_path / "rule",
        run_id="rule-zero",
        model_id="Rule-only",
        chunk_size=1,
    )
    bundles = tuple(
        iter_hybrid_score_batches(
            protocol,
            deep,
            rule,
            rule_weight_lambda=1.0,
            batch_size=128,
        )
    )
    assert np.count_nonzero(bundles[0].hybrid.scores) == 0

    def fail_after_metrics(*_: object) -> None:
        raise RuntimeError("simulated custody failure")

    with pytest.raises(RuntimeError, match="custody failure"):
        FullCatalogEvaluator(protocol).evaluate_batches(
            (bundle.hybrid for bundle in bundles),
            run_id="hybrid-zero",
            model_id="Hybrid",
            on_batch_evaluated=fail_after_metrics,
        )
    assert all((deep.root / chunk.name).is_file() for chunk in deep.chunks)
    assert all((rule.root / chunk.name).is_file() for chunk in rule.chunks)


def test_streaming_hybrid_rejects_authority_and_chunk_hash_mismatch(
    snapshot: Snapshot,
    tmp_path: Path,
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    deep = materialize_scores(
        protocol,
        _FixedScorer(protocol),
        root=tmp_path / "deep",
        run_id="deep-corrupt",
        model_id="Deep-only",
        chunk_size=1,
    )
    rule = materialize_scores(
        protocol,
        _FixedScorer(protocol, reverse=True),
        root=tmp_path / "rule",
        run_id="rule-corrupt",
        model_id="Rule-only",
        chunk_size=1,
    )
    mismatched = MaterializedScores(
        root=rule.root,
        manifest=replace(rule.manifest, user_order_sha256="f" * 64),
        chunks=rule.chunks,
    )
    with pytest.raises(IntegrityError, match="authorities differ"):
        next(
            iter_hybrid_score_batches(
                protocol,
                deep,
                mismatched,
                rule_weight_lambda=0.5,
            )
        )

    corrupt_path = deep.root / deep.chunks[0].name
    matrix = np.load(corrupt_path, allow_pickle=False)
    matrix[0, 0] += np.float32(1.0)
    with corrupt_path.open("wb") as stream:
        np.save(stream, matrix, allow_pickle=False)
    with pytest.raises(IntegrityError, match="hash mismatch"):
        next(
            iter_hybrid_score_batches(
                protocol,
                deep,
                rule,
                rule_weight_lambda=0.5,
            )
        )
