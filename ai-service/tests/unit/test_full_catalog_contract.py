from __future__ import annotations

from pathlib import Path

import numpy as np

from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.rules import RuleStore
from ai_service.evaluation.baselines import run_full_catalog_comparison
from ai_service.evaluation.full_catalog import FullCatalogEvaluator, prepare_split
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from tests.support.v5_factories import make_settings, make_snapshot


def _fixture(tmp_path: Path):
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    embeddings = np.eye(snapshot.manifest.num_items, settings.model.sbert_dim, dtype=np.float32)
    return settings, snapshot, embeddings


def test_prepared_full_catalog_masks_history_and_uses_novel_purchases(tmp_path: Path) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    evaluator = FullCatalogEvaluator(
        settings, embeddings, RuleStore(snapshot.manifest.num_items, [])
    )
    prepared = prepare_split(snapshot, SplitName.TEST)

    def scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        values = np.zeros((len(users), len(candidates)), dtype=np.float32)
        for row, user in enumerate(users):
            positive = next(iter(prepared.organic_novel_truth[int(user)]))
            values[row, positive] = 100.0
        return values

    result = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.RANDOM,
        scorer=scorer,
        k=settings.eval.k,
    )

    assert result.report.num_eligible_users == snapshot.manifest.num_users
    assert result.report.hr_at_k == 1.0
    assert result.report.ndcg_at_k == 1.0
    assert all(
        int(top[0]) in prepared.organic_novel_truth[user]
        for user, top in result.top_k_by_user.items()
    )


def test_seven_way_harness_returns_distinct_named_methods(tmp_path: Path) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    prepared = prepare_split(snapshot, SplitName.TEST)
    hybrid = HybridTwoTowerModel(settings)
    deep = HybridTwoTowerModel(settings)
    report = run_full_catalog_comparison(
        hybrid_model=hybrid,
        deep_model=deep,
        snapshot=snapshot,
        embeddings=embeddings,
        rule_store=RuleStore(snapshot.manifest.num_items, []),
        prepared_split=prepared,
        settings=settings,
        device="cpu",
    )
    assert set(report.baselines) == {
        "apriori_only",
        "persona_only",
        "sbert_centroid",
        "item_cf",
        "deep_only",
        "hybrid",
        "noisy_hybrid",
        "random",
    }
    assert report.deep_only is not report.hybrid


def test_training_epoch_builds_deep_warm_only_cache_and_streams_external_scores(
    tmp_path: Path,
) -> None:
    settings, snapshot, embeddings = _fixture(tmp_path)
    settings.train.validation_user_batch_size = 2
    evaluator = FullCatalogEvaluator(
        settings, embeddings, RuleStore(snapshot.manifest.num_items, [])
    )
    model = HybridTwoTowerModel(settings)
    prepared = prepare_split(snapshot, SplitName.VAL)

    validation = evaluator.evaluate_training_epoch(
        model,
        snapshot,
        prepared_split=prepared,
        k=settings.eval.k,
        device="cpu",
    )
    cache = validation.model_hard_cache
    assert cache.dtype == np.int32
    assert cache.shape == (snapshot.manifest.num_users + 1, 64)
    assert np.all(cache[0] == -1)
    assert np.all(cache[1:] >= 0)
    assert not np.any(np.isin(cache[1:], snapshot.cold_item_ids))
    for user, row in enumerate(cache[1:], start=1):
        assert len(np.unique(row)) == len(row)
        assert not set(row).intersection(set(prepared.seen_items.get(user, set())))

    seen_batch_sizes: list[int] = []

    def scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        seen_batch_sizes.append(len(users))
        return np.broadcast_to(
            np.arange(len(candidates), dtype=np.float32),
            (len(users), len(candidates)),
        )

    external = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.ITEM_CF,
        scorer=scorer,
        k=settings.eval.k,
    )
    assert external.report.num_eligible_users == len(prepared.eligible_users)
    assert max(seen_batch_sizes) <= settings.train.validation_user_batch_size
