import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from ai_service.config import Settings
from ai_service.contracts import ModelVariant, SplitName, TrainingVariant
from ai_service.data.dataset import (
    HybridImplicitDataset,
    PurchaseBatchIterator,
    build_purchase_training_index,
    collate_candidate_groups,
)
from ai_service.data.rules import RuleStore
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ModelTrainingError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.trainer import Trainer


def test_trainer_requires_real_validation_evaluator(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.num_users = 4
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 8
    trainer = Trainer(
        HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path, device="cpu"
    )

    with pytest.raises(ModelTrainingError, match="validation evaluator"):
        trainer.fit(
            train_loader=[],  # type: ignore[arg-type]
            snapshot=None,  # type: ignore[arg-type]
            embeddings=None,  # type: ignore[arg-type]
            val_evaluator=None,
            lineage={},
        )


class _Evaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
        reports = (
            SimpleNamespace(gauc=0.60, hr_at_k=0.20, ndcg_at_k=0.30),
            SimpleNamespace(gauc=0.70, hr_at_k=0.20, ndcg_at_k=0.20),
            SimpleNamespace(gauc=0.80, hr_at_k=0.20, ndcg_at_k=0.10),
        )
        report = reports[min(self.calls, len(reports) - 1)]
        self.calls += 1
        return SimpleNamespace(report=report)

    def evaluate_training_epoch(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
        reports = (
            SimpleNamespace(gauc=0.60, hr_at_k=0.20, ndcg_at_k=0.30),
            SimpleNamespace(gauc=0.70, hr_at_k=0.20, ndcg_at_k=0.20),
            SimpleNamespace(gauc=0.80, hr_at_k=0.20, ndcg_at_k=0.10),
        )
        report = reports[min(self.calls, len(reports) - 1)]
        self.calls += 1
        snapshot = _args[1]
        warm = [
            item
            for item in range(snapshot.manifest.num_items)
            if item not in snapshot.cold_item_ids
        ]
        width = min(4, len(warm))
        cache = np.full((snapshot.manifest.num_users + 1, width), -1, dtype=np.int32)
        for user in range(1, snapshot.manifest.num_users + 1):
            seen = {
                int(item)
                for item in snapshot.train_df.loc[
                    snapshot.train_df.internal_user_id == user, "internal_product_id"
                ]
            }
            cache[user] = np.asarray(
                [item for item in warm if item not in seen][:width], dtype=np.int32
            )
        return SimpleNamespace(
            variants={
                ModelVariant.HYBRID: SimpleNamespace(report=report),
                ModelVariant.DEEP_ONLY: SimpleNamespace(report=report),
                ModelVariant.WIDE_ONLY: SimpleNamespace(report=report),
            },
            model_hard_cache=cache,
            deep_logit_rms=1.0,
            wide_logit_rms=1.0,
            hybrid_logit_rms=1.0,
        )


def test_trainer_optimizes_valid_batches_and_reloads_best_checkpoint(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.num_users = 4
    settings.data.num_items = 8
    settings.data.num_cold_items = 1
    settings.data.num_personas = 8
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 8
    settings.train.objective = "legacy_bce"
    settings.train.max_epochs = 3
    settings.train.batch_size = 2
    settings.train.negative_ratio = 1
    settings.train.early_stopping_patience = 2
    timestamps = pd.date_range("2026-01-01", periods=8, freq="h", tz="UTC")
    train = pd.DataFrame(
        {
            "event_id": [f"event-{index}" for index in range(8)],
            "internal_user_id": [1, 2, 3, 4, 1, 2, 3, 4],
            "internal_product_id": [0, 1, 2, 3, 4, 5, 6, 0],
            "event_type": ["purchase", "view"] * 4,
            "event_ts": timestamps,
            "interaction_weight": [1.0, 0.5] * 4,
        }
    )
    catalog = pd.DataFrame(
        {
            "product_id": np.arange(101, 109),
            "internal_product_id": np.arange(8),
            "internal_leaf_category_id": [1, 2, 3, 4, 1, 2, 3, 4],
            "price_bucket_id": [1, 1, 1, 1, 2, 2, 2, 2],
        }
    )
    snapshot = Snapshot(
        manifest=SimpleNamespace(num_items=8, num_users=4),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=train,
        val_df=train.iloc[0:0].copy(),
        test_df=train.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={idx + 101: idx for idx in range(8)},
        raw_product_map={idx: idx + 101 for idx in range(8)},
        user_map={idx + 10: idx for idx in range(1, 5)},
        raw_user_map={idx: idx + 10 for idx in range(1, 5)},
        persona_map={idx + 10: idx - 1 for idx in range(1, 5)},
        cold_item_ids=(7,),
        price_boundaries=np.asarray([5.0]),
    )
    rules = RuleStore(8, [(0, 4, 3.0)])
    dataset = HybridImplicitDataset(
        snapshot,
        rules,
        split=SplitName.TRAIN,
        negative_ratio=1,
    )
    loader = DataLoader(dataset, batch_size=2, collate_fn=collate_candidate_groups)

    class _CacheSampler:
        def __init__(self) -> None:
            self.calls = 0

        def update_model_hard_cache(self, _cache: np.ndarray) -> None:
            self.calls += 1

    cache_sampler = _CacheSampler()

    class _LoaderProxy:
        sampler = cache_sampler

        def __iter__(self):
            return iter(loader)

        def __len__(self) -> int:
            return len(loader)

    loader_proxy = _LoaderProxy()
    model = HybridTwoTowerModel(settings)
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}

    evaluator = _Evaluator()
    run_dir = tmp_path / "run"
    result = Trainer(model, settings=settings, run_dir=run_dir, device="cpu").fit(
        loader_proxy,  # type: ignore[arg-type]
        snapshot,
        np.eye(8, dtype=np.float32),
        evaluator,  # type: ignore[arg-type]
        lineage,
    )

    # GAUC is the primary checkpoint metric; declining NDCG does not override
    # a material GAUC improvement.
    assert result.best_epoch == 3
    assert result.checkpoint_path.is_file()
    assert torch.isfinite(torch.tensor(result.history[0].train_loss))
    assert evaluator.calls == 3
    assert cache_sampler.calls == 3
    assert len(result.history) == 3
    assert result.history[0].wide_gradient_norm > 0.0
    assert all(row.model_hard_cache_updated for row in result.history)
    assert (run_dir / "checkpoints" / "last.pt").is_file()
    assert (run_dir / "training" / "summary.json").is_file()
    assert not (run_dir / "checkpoints" / "pareto").exists()
    history = [
        json.loads(line)
        for line in (run_dir / "training" / "history.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["epoch"] for row in history] == [1, 2, 3]
    assert history[0]["is_best"] is True
    assert history[1]["is_best"] is True
    assert history[2]["is_best"] is True


def test_trainer_runs_purchase_sampled_softmax_with_history(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.num_users = 4
    settings.data.num_items = 8
    settings.data.num_cold_items = 1
    settings.data.num_personas = 8
    settings.data.num_leaf_categories = 4
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 8
    settings.train.objective = "sampled_softmax"
    settings.train.explicit_negative_ratio = 4
    settings.train.max_history_items = 2
    settings.train.max_epochs = 1
    settings.train.batch_size = 2
    settings.train.view_auxiliary_weight = 0.1
    timestamps = pd.date_range("2026-01-01", periods=8, freq="h", tz="UTC")
    train = pd.DataFrame(
        {
            "event_id": [f"event-{index}" for index in range(8)],
            "event_origin": ["organic"] * 8,
            "internal_user_id": [1, 1, 2, 2, 3, 3, 4, 4],
            "internal_product_id": [0, 1, 2, 3, 4, 5, 6, 0],
            "event_type": ["purchase"] * 7 + ["view"],
            "event_ts": timestamps,
            "interaction_weight": [1.0] * 8,
        }
    )
    catalog = pd.DataFrame(
        {
            "product_id": np.arange(101, 109),
            "internal_product_id": np.arange(8),
            "internal_leaf_category_id": [1, 2, 3, 4, 1, 2, 3, 4],
            "price_bucket_id": [1, 1, 1, 1, 2, 2, 2, 2],
        }
    )
    snapshot = Snapshot(
        manifest=SimpleNamespace(num_items=8, num_users=4),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=train,
        val_df=train.iloc[0:0].copy(),
        test_df=train.iloc[0:0].copy(),
        order_baskets_df=pd.DataFrame(),
        product_map={idx + 101: idx for idx in range(8)},
        raw_product_map={idx: idx + 101 for idx in range(8)},
        user_map={idx + 10: idx for idx in range(1, 5)},
        raw_user_map={idx: idx + 10 for idx in range(1, 5)},
        persona_map={idx + 10: idx - 1 for idx in range(1, 5)},
        cold_item_ids=(7,),
        price_boundaries=np.asarray([5.0]),
    )
    embeddings = np.eye(8, dtype=np.float32)
    index = build_purchase_training_index(snapshot, max_history_items=2)
    sampler = MixedNegativeSampler(index, snapshot, embeddings, ratio=4)
    loader = PurchaseBatchIterator(
        index, sampler, RuleStore(8, [(0, 1, 3.0)]), batch_size=2, seed=42
    )
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}

    result = Trainer(
        HybridTwoTowerModel(settings),
        settings=settings,
        run_dir=tmp_path / "sampled-run",
        device="cpu",
    ).fit(
        loader,  # type: ignore[arg-type]
        snapshot,
        embeddings,
        _Evaluator(),  # type: ignore[arg-type]
        lineage,
    )

    assert len(result.history) == 1
    assert np.isfinite(result.history[0].train_loss)
    assert 0.0 <= result.history[0].sampled_pair_accuracy <= 1.0
    assert 0.0 <= result.history[0].all_negative_win_rate <= 1.0
    assert result.history[0].purchase_loss > 0
    assert result.history[0].view_loss > 0


def test_purchase_batch_iterator_requires_rule_store(tmp_path: Path) -> None:
    snapshot = Snapshot(
        manifest=SimpleNamespace(num_items=8, num_users=4),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame({"product_id": range(8), "internal_product_id": range(8)}),
        train_df=pd.DataFrame(
            {
                "event_id": ["e1"],
                "internal_user_id": [1],
                "internal_product_id": [0],
                "event_type": ["purchase"],
                "event_ts": pd.date_range("2026-01-01", periods=1, tz="UTC"),
                "event_origin": ["organic"],
            }
        ),
        val_df=pd.DataFrame(),
        test_df=pd.DataFrame(),
        order_baskets_df=pd.DataFrame(),
        product_map={i: i for i in range(8)},
        raw_product_map={i: i for i in range(8)},
        user_map={i: i for i in range(4)},
        raw_user_map={i: i for i in range(4)},
        persona_map={i: 0 for i in range(4)},
        cold_item_ids=(),
        price_boundaries=np.array([5.0]),
    )
    index = build_purchase_training_index(snapshot, max_history_items=2)
    sampler = MixedNegativeSampler(index, snapshot, np.eye(8, dtype=np.float32), ratio=4)

    # Passing no rule_store should fail in v5
    with pytest.raises(TypeError, match="rule_store"):
        PurchaseBatchIterator(index, sampler, batch_size=2, seed=42)  # type: ignore[call-arg]


def test_deep_only_excludes_wide_parameters(tmp_path: Path) -> None:
    settings = Settings()
    settings.train.training_variant = TrainingVariant.DEEP_ONLY
    model = HybridTwoTowerModel(settings)
    trainer = Trainer(
        model,
        settings=settings,
        run_dir=tmp_path,
        training_variant=TrainingVariant.DEEP_ONLY,
        device="cpu",
    )

    wide_param_ids = {id(p) for p in model.wide_layer.parameters()}
    optimizer_param_ids = {
        id(p) for group in trainer.optimizer.param_groups for p in group["params"]
    }

    # Deep-only optimizer MUST NOT contain Wide parameters
    assert wide_param_ids.isdisjoint(optimizer_param_ids)
