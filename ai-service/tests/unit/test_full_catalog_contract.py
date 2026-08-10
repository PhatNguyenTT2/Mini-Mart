from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.baselines import run_seven_way_baselines
from ai_service.evaluation.cold_start import evaluate_cold_start
from ai_service.evaluation.full_catalog import FullCatalogEvaluator
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


def _fixture(tmp_path: Path) -> tuple[Settings, Snapshot, np.ndarray]:
    settings = Settings()
    settings.data.num_users = 1
    settings.data.num_items = 4
    settings.data.num_cold_items = 1
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 4
    settings.eval.k = 2
    catalog = pd.DataFrame(
        {
            "product_id": [10, 20, 30, 40],
            "internal_product_id": [0, 1, 2, 3],
            "internal_leaf_category_id": [1, 1, 2, 2],
            "price_bucket_id": [1, 1, 2, 2],
        }
    )
    columns = [
        "event_id",
        "internal_user_id",
        "internal_product_id",
        "event_type",
        "event_ts",
        "interaction_weight",
    ]
    train = pd.DataFrame(
        [
            ("a", 1, 0, "view", pd.Timestamp("2026-01-01", tz="UTC"), 0.5),
            ("b", 1, 1, "purchase", pd.Timestamp("2026-01-02", tz="UTC"), 1.0),
        ],
        columns=columns,
    )
    val = pd.DataFrame(
        [("c", 1, 2, "purchase", pd.Timestamp("2026-02-01", tz="UTC"), 1.0)],
        columns=columns,
    )
    test = pd.DataFrame(
        [("d", 1, 3, "purchase", pd.Timestamp("2026-03-01", tz="UTC"), 1.0)],
        columns=columns,
    )
    snapshot = Snapshot(
        manifest=SimpleNamespace(
            num_items=4, num_users=1, artifact_id="fixture", content_sha256="a" * 64
        ),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=train,
        val_df=val,
        test_df=test,
        order_baskets_df=pd.DataFrame(),
        product_map={10: 0, 20: 1, 30: 2, 40: 3},
        raw_product_map={0: 10, 1: 20, 2: 30, 3: 40},
        user_map={100: 1},
        raw_user_map={1: 100},
        persona_map={100: 0},
        cold_item_ids=(3,),
        price_boundaries=np.array([20.0]),
    )
    embeddings = np.eye(4, dtype=np.float32)
    return settings, snapshot, embeddings


def test_precomputed_full_catalog_masks_history_and_uses_novel_purchases(tmp_path: Path) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    evaluator = FullCatalogEvaluator(settings, embeddings, RuleStore(4, []))
    result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.TEST,
        variant=ModelVariant.RANDOM,
        scores_by_user={1: np.array([100.0, 90.0, 80.0, 1.0])},
        k=2,
    )

    assert result.report.num_eligible_users == 1
    assert result.report.hr_at_k == 1.0
    assert result.report.ndcg_at_k == 1.0
    assert result.report.num_catalog_items == 4
    cold = evaluate_cold_start(result, snapshot, RuleStore(4, []))
    assert cold.ground_truth_coverage == 1.0
    assert cold.hr_at_k == 1.0
    assert cold.num_cold_items_with_test_purchase == 1


def test_seven_way_harness_returns_distinct_named_methods(tmp_path: Path) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    report = run_seven_way_baselines(
        HybridTwoTowerModel(settings),
        snapshot,
        embeddings=embeddings,
        rule_store=RuleStore(4, []),
        split=SplitName.TEST,
        settings=settings,
        device="cpu",
    )
    assert set(report.baselines) == {
        "Rule-based Apriori",
        "SBERT User Centroid",
        "Item-Item CF",
        "Deep-Only Two-Tower",
        "Proposed Hybrid (Ours)",
        "Noisy 10% Hybrid",
        "Random Base (Sanity Check)",
    }


def test_headline_full_catalog_metrics_exclude_fixture_targets(tmp_path: Path) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    snapshot.train_df["event_origin"] = "organic"
    snapshot.val_df["event_origin"] = "organic"
    fixture = snapshot.val_df.iloc[[0]].copy()
    fixture["event_id"] = "fixture"
    fixture["internal_product_id"] = 3
    fixture["event_origin"] = "semantic_trap"
    snapshot = replace(snapshot, val_df=pd.concat((snapshot.val_df, fixture), ignore_index=True))
    evaluator = FullCatalogEvaluator(settings, embeddings, RuleStore(4, []))

    result = evaluator.evaluate_scores(
        snapshot,
        split=SplitName.VAL,
        variant=ModelVariant.RANDOM,
        scores_by_user={1: np.array([0.0, 0.0, 0.1, 10.0])},
        k=1,
    )

    assert result.report.hr_at_k == 0.0
