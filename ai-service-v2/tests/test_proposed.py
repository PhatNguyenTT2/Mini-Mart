from __future__ import annotations

from dataclasses import replace

import numpy as np

from ai_service_v2.data.rules import AprioriRuleTable
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.models.proposed import (
    HybridScorer,
    RuleOnlyScorer,
    TwoTowerConfig,
    _train_pairs,
    item_text_hash_features,
    train_two_tower,
)
from ai_service_v2.protocol import build_protocol


def test_two_tower_training_is_deterministic_and_scoreable(snapshot: Snapshot) -> None:
    features = item_text_hash_features(snapshot, dimensions=8)
    config = TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=2, learning_rate=0.01)
    first, first_report = train_two_tower(snapshot, features, config=config, seed=17)
    second, second_report = train_two_tower(snapshot, features, config=config, seed=17)
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    first_scores = first(0, protocol.candidate_item_ids)
    second_scores = second(0, protocol.candidate_item_ids)
    assert np.array_equal(first_scores, second_scores)
    assert first_report == second_report
    assert first.describe().objective == "pairwise_bpr"
    assert first.describe().input_features[-1] == "price"


def test_hybrid_exposes_deep_and_rule_scores(snapshot: Snapshot) -> None:
    features = item_text_hash_features(snapshot, dimensions=8)
    model, _ = train_two_tower(
        snapshot,
        features,
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=1,
    )
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    rules = AprioriRuleTable.fit(snapshot)
    hybrid = HybridScorer(model, RuleOnlyScorer(protocol, rules), wide_weight=0.5)
    breakdown = hybrid.breakdown(0, protocol.candidate_item_ids)
    assert breakdown.deep_scores.shape == (5,)
    assert breakdown.wide_scores.shape == (5,)
    assert np.allclose(
        breakdown.hybrid_scores,
        breakdown.deep_scores + 0.5 * breakdown.wide_scores,
    )
    result = FullCatalogEvaluator(protocol).evaluate(hybrid, run_id="hybrid", model_id="hybrid")
    assert result.receipt.verdict == "PASS"


def test_hybrid_zscore_normalization_is_explicit_and_deterministic(snapshot: Snapshot) -> None:
    features = item_text_hash_features(snapshot, dimensions=8)
    model, _ = train_two_tower(
        snapshot,
        features,
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=3,
    )
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    rules = AprioriRuleTable.fit(snapshot)
    hybrid = HybridScorer(
        model,
        RuleOnlyScorer(protocol, rules),
        wide_weight=0.25,
        fusion_normalization="per_user_zscore",
    )
    first = hybrid.breakdown(0, protocol.candidate_item_ids)
    second = hybrid.breakdown(0, protocol.candidate_item_ids)
    assert np.array_equal(first.deep_scores, second.deep_scores)
    assert np.array_equal(first.wide_scores, second.wide_scores)
    assert np.isclose(np.mean(first.deep_scores), 0.0)
    assert np.isclose(np.std(first.deep_scores), 1.0)
    assert np.allclose(first.hybrid_scores, first.deep_scores + 0.25 * first.wide_scores)


def test_negative_sampler_excludes_every_train_history_item(snapshot: Snapshot) -> None:
    train = list(snapshot.events_by_split["train"])
    train[-1] = replace(
        train[-1],
        user_id=0,
        item_id=3,
        event_type="view",
        basket_id=None,
    )
    modified = Snapshot.from_fixture(
        snapshot.manifest,
        {
            "train": tuple(train),
            "val": snapshot.events_by_split["val"],
            "test": snapshot.events_by_split["test"],
        },
        snapshot.item_records,
        raw_item_ids=snapshot.raw_item_ids,
        training_baskets=snapshot.training_baskets,
    )
    pairs = _train_pairs(modified, seed=11, negatives_per_positive=8)
    user_zero_negatives = {negative for user, _positive, negative in pairs if user == 0}
    assert user_zero_negatives
    assert user_zero_negatives.isdisjoint({0, 1, 3})
