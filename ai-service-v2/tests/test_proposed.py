from __future__ import annotations

import numpy as np

from ai_service_v2.data.rules import AprioriRuleTable
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.models.proposed import (
    HybridScorer,
    RuleOnlyScorer,
    TwoTowerConfig,
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
