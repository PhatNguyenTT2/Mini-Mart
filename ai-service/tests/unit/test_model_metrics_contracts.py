from __future__ import annotations

import numpy as np
import pytest
import torch

from ai_service.config import Settings
from ai_service.contracts import ModelVariant
from ai_service.evaluation.metrics import paired_bootstrap_delta, ranking_metrics, user_auc
from ai_service.export.onnx import ItemEncoderGraph, RankerGraph
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


def _settings() -> Settings:
    settings = Settings()
    settings.data.num_users = 4
    settings.data.num_personas = 8
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 8
    return settings


def test_hybrid_model_tensor_contract_and_dedicated_unknown_persona() -> None:
    model = HybridTwoTowerModel(_settings()).eval()
    user = torch.tensor([0, 1], dtype=torch.int64)
    persona = torch.tensor([8, 2], dtype=torch.int64)
    sbert = torch.randn(2, 3, 8)
    category = torch.ones(2, 3, dtype=torch.int64)
    price = torch.ones(2, 3, dtype=torch.int64)
    wide = torch.rand(2, 3, 3)
    present = torch.tensor([[True, False, True], [False, False, True]])

    user_vectors = model.encode_user(user, persona)
    item_vectors = model.encode_items(sbert, category, price)
    logits = model(
        user,
        persona,
        sbert,
        category,
        price,
        wide,
        present,
        ModelVariant.HYBRID,
    )

    assert user_vectors.shape == (2, 64)
    assert item_vectors.shape == (2, 3, 64)
    assert logits.shape == (2, 3)
    torch.testing.assert_close(torch.linalg.vector_norm(user_vectors, dim=-1), torch.ones(2))
    torch.testing.assert_close(torch.linalg.vector_norm(item_vectors, dim=-1), torch.ones(2, 3))
    assert torch.isfinite(logits).all()


def test_hybrid_fusion_adds_learned_wide_logit() -> None:
    settings = _settings()
    model = HybridTwoTowerModel(settings).eval()
    deep = torch.tensor([[1.0, -1.0]])
    wide = torch.tensor([[0.5, 0.0]])

    fused = model.fuse_scores(deep, wide)

    torch.testing.assert_close(fused, deep + wide)


def test_scoring_constants_are_part_of_the_checkpoint_state() -> None:
    settings = _settings()
    model = HybridTwoTowerModel(settings)

    state = model.state_dict()

    assert "_temperature" in state
    assert float(state["_temperature"]) == pytest.approx(settings.model.tau)


def test_item_id_residual_is_disabled_for_cold_items() -> None:
    settings = _settings()
    settings.data.num_items = 4
    model = HybridTwoTowerModel(settings).eval()
    sbert = torch.randn(2, settings.model.sbert_dim)
    category = torch.ones(2, dtype=torch.int64)
    price = torch.ones(2, dtype=torch.int64)
    item_idx = torch.tensor([0, 1], dtype=torch.int64)

    content_only = model.encode_items(sbert, category, price)
    encoded = model.encode_items(
        sbert,
        category,
        price,
        item_idx=item_idx,
        is_cold=torch.tensor([True, False]),
    )

    torch.testing.assert_close(encoded[0], content_only[0])
    assert not torch.allclose(encoded[1], content_only[1])


def test_strict_history_profile_changes_user_representation() -> None:
    model = HybridTwoTowerModel(_settings()).eval()
    users = torch.tensor([1], dtype=torch.int64)
    personas = torch.tensor([0], dtype=torch.int64)
    without_history = model.encode_user(users, personas)
    with_history = model.encode_user(
        users,
        personas,
        history_vector=torch.nn.functional.normalize(torch.ones(1, 64), dim=-1),
        history_present=torch.tensor([True]),
    )

    assert not torch.allclose(without_history, with_history)


def test_export_graphs_share_item_residual_history_and_wide_fusion_contract() -> None:
    settings = _settings()
    settings.data.num_items = 4
    model = HybridTwoTowerModel(settings).eval()
    item_graph = ItemEncoderGraph(model).eval()
    ranker_graph = RankerGraph(model).eval()
    sbert = torch.randn(3, settings.model.sbert_dim)
    category = torch.tensor([1, 2, 3], dtype=torch.int64)
    price = torch.tensor([1, 1, 2], dtype=torch.int64)
    item_ids = torch.tensor([0, 1, 2], dtype=torch.int64)
    cold = torch.tensor([False, True, False])
    candidate_vectors = item_graph(sbert, category, price, item_ids, cold).unsqueeze(0)
    users = torch.tensor([1], dtype=torch.int64)
    personas = torch.tensor([2], dtype=torch.int64)
    history_vector = torch.nn.functional.normalize(torch.ones(1, 64), dim=-1)
    history_present = torch.tensor([True])
    wide = torch.tensor([[[0.5, 0.4, 2.0], [0.0, 0.0, 0.0], [0.2, 0.1, 1.0]]])
    present = torch.tensor([[True, False, True]])

    expected = model.score_cached(
        users,
        personas,
        candidate_vectors,
        wide,
        present,
        history_vector=history_vector,
        history_present=history_present,
    )
    actual = ranker_graph(
        users,
        personas,
        history_vector,
        history_present,
        candidate_vectors,
        wide,
        present,
    )

    torch.testing.assert_close(actual, expected)


def test_wide_layer_zero_masks_missing_rule_and_rejects_nan() -> None:
    model = HybridTwoTowerModel(_settings()).eval()
    values = torch.tensor([[[0.5, 0.4, 2.0], [0.5, 0.4, 2.0]]])
    present = torch.tensor([[True, False]])
    output = model.wide_layer(values, present)

    assert output.shape == (1, 2)
    assert output[0, 1] == 0
    with pytest.raises(ValueError, match="finite"):
        model.wide_layer(torch.tensor([[[float("nan"), 0.4, 2.0]]]), torch.tensor([[True]]))


def test_rank_auc_counts_ties_without_pairwise_matrix() -> None:
    assert user_auc(np.array([0.9, 0.5]), np.array([0.5, 0.1])) == pytest.approx(0.875)


def test_ranking_metrics_uses_stable_product_id_tie_break() -> None:
    result = ranking_metrics(
        scores=np.array([0.5, 0.5, 0.1]),
        positive_indices={1},
        raw_product_ids=np.array([20, 10, 30]),
        k=2,
    )
    assert result.ranked_indices.tolist() == [1, 0]
    assert result.hit == 1.0
    assert result.ndcg == 1.0


def test_paired_bootstrap_is_deterministic_and_rejects_unpaired_vectors() -> None:
    candidate = np.asarray([0.6, 0.7, 0.8, 0.9])
    baseline = np.asarray([0.5, 0.5, 0.5, 0.5])
    first = paired_bootstrap_delta(candidate, baseline, samples=100, seed=42)
    second = paired_bootstrap_delta(candidate, baseline, samples=100, seed=42)

    assert first == second
    assert first.lower > 0
    with pytest.raises(ValueError, match="equal shape"):
        paired_bootstrap_delta(candidate, baseline[:-1])
