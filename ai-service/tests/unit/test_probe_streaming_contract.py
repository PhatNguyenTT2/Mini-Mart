from __future__ import annotations

from pathlib import Path

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import SnapshotBuilder
from ai_service.data.sources import SyntheticDatasetSource
from ai_service.evaluation.full_catalog import FullCatalogEvaluator, prepare_split


def _snapshot(tmp_path: Path):
    settings = Settings(
        {
            "data": {
                "artifact_root": str(tmp_path),
                "snapshot_id": "probe-streaming",
                "num_users": 16,
                "num_items": 96,
                "num_cold_items": 8,
                "num_leaf_categories": 8,
                "num_price_buckets": 4,
                "expected_event_count": 768,
                "expected_train_count": 512,
                "expected_val_count": 128,
                "expected_test_count": 128,
                "expected_order_count": 64,
            },
            "model": {"sbert_dim": 8},
            "train": {"validation_user_batch_size": 4},
        }
    )
    raw = SyntheticDatasetSource(settings).load(store_id=1, benchmark_run_id="probe-streaming")
    return settings, SnapshotBuilder(settings).build(raw, snapshot_id="probe-streaming")


def test_external_streaming_is_batch_size_invariant_and_has_no_legacy_score_map(
    tmp_path: Path,
) -> None:
    settings, snapshot = _snapshot(tmp_path)
    embeddings = np.arange(snapshot.manifest.num_items * 8, dtype=np.float32).reshape(
        snapshot.manifest.num_items, 8
    )
    evaluator = FullCatalogEvaluator(
        settings,
        embeddings,
        RuleStore(snapshot.manifest.num_items, []),
    )
    prepared = prepare_split(snapshot, SplitName.VAL)

    def scorer(users: np.ndarray, candidates: np.ndarray) -> np.ndarray:
        return np.asarray(
            candidates[None, :] + users[:, None].astype(np.float32) * 1e-3,
            dtype=np.float32,
        )

    batched = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.RANDOM,
        scorer=scorer,
        k=settings.eval.k,
    )
    settings.train.validation_user_batch_size = 1
    one_by_one = evaluator.evaluate_external_scores(
        snapshot,
        prepared_split=prepared,
        variant=ModelVariant.RANDOM,
        scorer=scorer,
        k=settings.eval.k,
    )

    np.testing.assert_array_equal(batched.user_ids, one_by_one.user_ids)
    np.testing.assert_allclose(batched.per_user_hr, one_by_one.per_user_hr, atol=1e-6)
    np.testing.assert_allclose(batched.per_user_ndcg, one_by_one.per_user_ndcg, atol=1e-6)
    np.testing.assert_allclose(batched.per_user_gauc, one_by_one.per_user_gauc, atol=1e-6)
    assert not hasattr(FullCatalogEvaluator, "evaluate_scores")
