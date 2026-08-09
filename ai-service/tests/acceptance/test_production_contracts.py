"""Acceptance tests for the deployable ``src/ai_service`` package.

These tests intentionally target production imports instead of the coexisting
legacy modules at the repository root.  Each assertion is derived from the
accepted remediation plan and should remain as a regression gate.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints

import numpy as np
import pandas as pd
import pytest
import torch
from pydantic import ValidationError

from ai_service.config import Settings
from ai_service.contracts import EmbeddingSource, SplitName
from ai_service.data.dataset import HybridImplicitDataset
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot, SnapshotBuilder
from ai_service.data.sources import RawDataset
from ai_service.errors import DataIntegrityError, ModelTrainingError
from ai_service.evaluation.baselines import run_seven_way_baselines
from ai_service.evaluation.full_catalog import EvaluationReport, FullCatalogEvaluator
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.serving.schemas import RecommendRequest
from ai_service.training.trainer import Trainer


@pytest.mark.parametrize(
    "module_name",
    [
        "ai_service.evaluation.semantic_traps",
        "ai_service.evaluation.cold_start",
    ],
)
def test_required_production_evaluation_modules_exist(module_name: str) -> None:
    importlib.import_module(module_name)


def test_api_request_requires_store_id() -> None:
    with pytest.raises(ValidationError):
        RecommendRequest(candidate_product_ids=[1001])


def test_real_embedding_failure_does_not_fallback_to_mock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ai_service.data import features

    class BrokenProvider:
        def __init__(self) -> None:
            raise OSError("model unavailable")

    monkeypatch.setattr(features, "SentenceTransformerProvider", BrokenProvider)
    catalog = pd.DataFrame({"internal_product_id": [0], "name": ["coffee"]})

    with pytest.raises(OSError, match="model unavailable"):
        features.precompute_embeddings(
            catalog,
            tmp_path,
            provider=None,
            source_kind=EmbeddingSource.REAL,
        )


def test_trainer_rejects_missing_validation_evaluator(tmp_path: Path) -> None:
    settings = _small_settings()
    trainer = Trainer(HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path)

    with pytest.raises(ModelTrainingError, match="validation evaluator"):
        trainer.fit([], snapshot=None, val_evaluator=None)  # type: ignore[arg-type]


def test_negative_ratio_is_a_runtime_dataset_contract() -> None:
    parameters = inspect.signature(HybridImplicitDataset).parameters
    assert "negative_ratio" in parameters or "settings" in parameters


def test_context_is_latest_strictly_earlier_purchase(tmp_path: Path) -> None:
    timestamps = pd.to_datetime(
        [
            "2026-01-01T00:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T01:00:00Z",
            "2026-01-01T02:00:00Z",
        ],
        utc=True,
    )
    train_df = pd.DataFrame(
        {
            "internal_user_id": [1, 1, 1, 1],
            "internal_product_id": [0, 1, 2, 3],
            "event_type": ["order", "view", "order", "order"],
            "event_ts": timestamps,
            "interaction_weight": [1.0, 0.5, 1.0, 1.0],
        }
    )
    snapshot = _minimal_snapshot(tmp_path, train_df)
    dataset = HybridImplicitDataset(snapshot, RuleStore(8, []), split="train")

    actual = [(ref.item_idx, ref.present) for ref in dataset.context_refs]
    assert actual == [(-1, False), (0, True), (0, True), (2, True)]


def test_snapshot_rejects_incomplete_cold_purchase_ground_truth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ai_service.data import snapshot as snapshot_module

    monkeypatch.setattr(snapshot_module, "DATA_ARTIFACTS_DIR", tmp_path)
    settings = _small_settings(num_items=10, num_cold_items=2)
    raw = _raw_dataset(
        num_items=10,
        timestamps=pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC"),
        final_product_ids=[9, 1],
        final_event_types=["view", "order"],
    )

    with pytest.raises(DataIntegrityError, match="cold.*purchase|ground truth"):
        SnapshotBuilder(settings).build(raw, snapshot_id="incomplete-cold")


def test_temporal_split_keeps_equal_timestamp_group_together(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ai_service.data import snapshot as snapshot_module

    monkeypatch.setattr(snapshot_module, "DATA_ARTIFACTS_DIR", tmp_path)
    settings = _small_settings(num_items=10, num_cold_items=1)
    timestamps = list(pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC"))
    timestamps[16] = timestamps[15]
    raw = _raw_dataset(
        num_items=10,
        timestamps=pd.DatetimeIndex(timestamps),
        final_product_ids=[1, 10],
        final_event_types=["order", "order"],
    )

    snapshot = SnapshotBuilder(settings).build(raw, snapshot_id="timestamp-groups")
    assert snapshot.train_df["event_ts"].max() < snapshot.val_df["event_ts"].min()
    assert snapshot.val_df["event_ts"].max() < snapshot.test_df["event_ts"].min()


def test_rule_store_uses_sparse_csr_tensor() -> None:
    store = RuleStore(4, [(0, 1, 2.0), (1, 0, 2.0)])
    tensors = [value for value in vars(store).values() if isinstance(value, torch.Tensor)]
    assert any(tensor.layout == torch.sparse_csr for tensor in tensors)


def test_full_catalog_split_is_typed_enum() -> None:
    split_annotation = get_type_hints(FullCatalogEvaluator.evaluate)["split"]
    assert split_annotation is SplitName


def test_gauc_implementation_does_not_allocate_positive_by_negative_matrix() -> None:
    source = inspect.getsource(importlib.import_module("ai_service.evaluation.full_catalog"))
    assert "pos_scores[:, None] - neg_scores[None, :]" not in source


def test_seven_way_baseline_harness_has_all_required_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _small_settings()
    report = EvaluationReport(
        split="test",
        num_eval_users=1,
        num_catalog_items=settings.data.num_items,
        hr10=0.0,
        ndcg10=0.0,
        gauc=0.5,
        avg_latency_ms=0.0,
        total_eval_time_sec=0.0,
    )
    monkeypatch.setattr(FullCatalogEvaluator, "evaluate", lambda *args, **kwargs: report)

    result = run_seven_way_baselines(
        HybridTwoTowerModel(settings),
        snapshot=SimpleNamespace(),  # type: ignore[arg-type]
        settings=settings,
    )

    assert len(result.baselines) == 7
    assert {
        "Rule-based Apriori",
        "SBERT User Centroid",
        "Item-Item CF",
        "Deep-Only Two-Tower",
        "Proposed Hybrid (Ours)",
        "Noisy 10% Hybrid",
        "Random Base (Sanity Check)",
    } == set(result.baselines)


def _small_settings(num_items: int = 8, num_cold_items: int = 1) -> Settings:
    settings = Settings()
    settings.data.num_users = 4
    settings.data.num_items = num_items
    settings.data.num_cold_items = num_cold_items
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 8
    settings.train.max_epochs = 1
    settings.train.batch_size = 2
    return settings


def _minimal_snapshot(tmp_path: Path, train_df: pd.DataFrame) -> Snapshot:
    catalog_df = pd.DataFrame(
        {
            "product_id": np.arange(1, 9),
            "internal_product_id": np.arange(8),
            "internal_leaf_category_id": np.ones(8, dtype=np.int64),
            "price_bucket_id": np.ones(8, dtype=np.int64),
        }
    )
    manifest = SimpleNamespace(num_items=8)
    return Snapshot(
        manifest=manifest,  # type: ignore[arg-type]
        snapshot_dir=tmp_path,
        catalog_df=catalog_df,
        train_df=train_df,
        val_df=train_df.iloc[0:0].copy(),
        test_df=train_df.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={idx + 1: idx for idx in range(8)},
        raw_product_map={idx: idx + 1 for idx in range(8)},
        user_map={1: 1},
        raw_user_map={1: 1},
        persona_map={1: 0},
        cold_item_ids=[7],
        price_boundaries=np.array([5.0]),
    )


def _raw_dataset(
    num_items: int,
    timestamps: pd.DatetimeIndex,
    final_product_ids: list[int],
    final_event_types: list[str],
) -> RawDataset:
    products = pd.DataFrame(
        {
            "product_id": np.arange(1, num_items + 1),
            "name": [f"item-{idx}" for idx in range(1, num_items + 1)],
            "unit_price": np.arange(1, num_items + 1, dtype=float),
            "leaf_category_id": (np.arange(num_items) % 4) + 1,
        }
    )
    event_count = len(timestamps)
    product_ids = [1 + (idx % max(num_items - 2, 1)) for idx in range(event_count - 2)]
    product_ids.extend(final_product_ids)
    event_types = ["order"] * (event_count - 2) + final_event_types
    events = pd.DataFrame(
        {
            "event_id": [f"event-{idx:03d}" for idx in range(event_count)],
            "store_id": [1] * event_count,
            "user_id": [1 + (idx % 4) for idx in range(event_count)],
            "product_id": product_ids,
            "persona_cluster": [idx % 4 for idx in range(event_count)],
            "event_type": event_types,
            "event_ts": timestamps,
            "interaction_weight": [1.0] * event_count,
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": [1],
            "user_id": [1],
            "product_id": [1],
            "quantity": [1],
            "created_at": [timestamps[0]],
        }
    )
    return RawDataset(events, products, orders, source_kind="synthetic")
