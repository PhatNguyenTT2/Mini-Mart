from __future__ import annotations

import json
import random
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import Settings
from ai_service.contracts import SplitName, TrainingVariant
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.cold_start import evaluate_cold_parity
from ai_service.evaluation.report import publish_evaluation_artifacts
from ai_service.evaluation.semantic_traps import evaluate_semantic_traps
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from tests.support.v5_factories import make_victory_matrix


def _settings() -> Settings:
    settings = Settings()
    settings.data.num_users = 2
    settings.data.num_items = 4
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 4
    return settings


def _snapshot(tmp_path: Path) -> Snapshot:
    empty = pd.DataFrame(
        columns=["event_id", "internal_user_id", "internal_product_id", "event_type", "event_ts"]
    )
    return Snapshot(
        manifest=SimpleNamespace(
            num_items=4,
            num_users=2,
            store_id=1,
            artifact_id="fixture",
            content_sha256="a" * 64,
        ),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame(
            {
                "product_id": [101, 102, 103, 104],
                "internal_product_id": [0, 1, 2, 3],
                "internal_leaf_category_id": [1, 1, 2, 2],
                "price_bucket_id": [1, 1, 2, 2],
            }
        ),
        train_df=empty,
        val_df=empty,
        test_df=empty,
        order_baskets_df=empty,
        product_map={101: 0, 102: 1, 103: 2, 104: 3},
        raw_product_map={0: 101, 1: 102, 2: 103, 3: 104},
        user_map={11: 1, 12: 2},
        raw_user_map={1: 11, 2: 12},
        persona_map={11: 0, 12: 1},
        cold_item_ids=(),
        price_boundaries=np.asarray([10.0]),
    )


def test_checkpoint_round_trip_is_strict_and_checksum_backed(tmp_path: Path) -> None:
    settings = _settings()
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    path = tmp_path / "checkpoints" / "best.pt"
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    scaler = SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _state: None)
    stopping_state = {
        "highest_gauc": 0.6,
        "selected_epoch": 2,
        "selected_gauc": 0.6,
        "selected_ndcg": 0.5,
        "selected_hr": 0.7,
        "patience_used": 0,
    }

    manifest = CheckpointManager.save(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        epoch=2,
        metrics={"val_gauc": 0.6, "val_ndcg_at_k": 0.5, "val_hr_at_k": 0.7, "train_loss": 0.3},
        stopping_state=stopping_state,
        checkpoint_kind="best",
        lineage=lineage,
        training_signature_sha256="d" * 64,
        comparison_signature_sha256="e" * 64,
        training_variant=TrainingVariant.HYBRID,
        model_schema_version="5.0.0",
        run_id="run-test",
        scaler=scaler,
    )
    original = {name: value.detach().clone() for name, value in model.state_dict().items()}
    expected_rng = (random.random(), float(np.random.random()), float(torch.rand(())))
    with torch.no_grad():
        next(model.parameters()).add_(1.0)
    state = CheckpointManager.load(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        scaler=scaler,
        expected_lineage=lineage,
        expected_training_signature="d" * 64,
        expected_model_schema_version="5.0.0",
        restore_rng=True,
        expected_checkpoint_kind="best",
    )
    actual_rng = (random.random(), float(np.random.random()), float(torch.rand(())))

    assert manifest.best_epoch == 2
    assert state["epoch"] == 2
    assert actual_rng == pytest.approx(expected_rng)
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value, original[name])

    with pytest.raises(ArtifactIntegrityError, match="training signature"):
        CheckpointManager.load(
            path,
            model=model,
            expected_lineage=lineage,
            expected_training_signature="e" * 64,
            expected_model_schema_version="5.0.0",
        )

    with pytest.raises(ArtifactIntegrityError, match="comparison signature"):
        CheckpointManager.load(
            path,
            model=model,
            expected_lineage=lineage,
            expected_comparison_signature="f" * 64,
        )

    with pytest.raises(ArtifactIntegrityError, match="training variant"):
        CheckpointManager.load(
            path,
            model=model,
            expected_lineage=lineage,
            expected_training_variant=TrainingVariant.DEEP_ONLY,
        )

    with pytest.raises(ArtifactIntegrityError, match="checkpoint schema mismatch"):
        CheckpointManager.load(
            path,
            model=model,
            expected_lineage=lineage,
            expected_training_signature="d" * 64,
            expected_model_schema_version="6.0.0",
        )

    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        CheckpointManager.load(path, model=model)


def test_report_and_semantic_trap_outputs_are_measured_not_hard_coded(tmp_path: Path) -> None:
    settings = _settings()
    lineage = {
        "snapshot": "a" * 64,
        "embedding": "b" * 64,
        "rules": "c" * 64,
    }
    users = np.asarray([1, 2], dtype=np.int64)
    metric = np.asarray([0.5, 0.6], dtype=np.float64)
    metrics = {
        "user_ids": users,
        **{
            name: metric
            for name in (
                "hybrid_hr",
                "hybrid_ndcg",
                "hybrid_gauc",
                "deep_hr",
                "deep_ndcg",
                "deep_gauc",
                "apriori_hr",
                "apriori_ndcg",
                "apriori_gauc",
                "sbert_hr",
                "sbert_ndcg",
                "sbert_gauc",
                "item_cf_hr",
                "item_cf_ndcg",
                "item_cf_gauc",
                "noisy_hybrid_hr",
                "noisy_hybrid_ndcg",
                "noisy_hybrid_gauc",
            )
        },
        "random_hr": np.tile(metric, (10, 1)),
        "random_ndcg": np.tile(metric, (10, 1)),
        "random_gauc": np.tile(metric, (10, 1)),
    }
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    artifact = publish_evaluation_artifacts(
        run_dir=tmp_path / "run",
        split=SplitName.VAL,
        hybrid_run_id="hybrid-report",
        deep_run_id="deep-report",
        hybrid_checkpoint_sha256="d" * 64,
        deep_checkpoint_sha256="e" * 64,
        lineage=lineage,
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        metrics=metrics,
        results={"actual_rule_count": 2, "latency_ms": 0.7},
        victory_matrix=matrix,
    )
    document = json.loads(artifact.report_path.read_text(encoding="utf-8"))
    assert document["results"]["actual_rule_count"] == 2
    assert artifact.manifest.passed is True

    fixture = tmp_path / "traps.json"
    fixture.write_text(
        json.dumps([{"trap_id": 1, "anchor_product_id": 101, "target_product_ids": [102]}]),
        encoding="utf-8",
    )
    model = HybridTwoTowerModel(_settings())
    trap_report = evaluate_semantic_traps(
        model,
        model,
        _snapshot(tmp_path),
        np.eye(4, dtype=np.float32),
        RuleStore(4, [(0, 1, 10.0)]),
        fixture,
        k=2,
    )
    assert trap_report.total == 1
    assert trap_report.results[0].target_product_ids == (102,)


def test_evaluate_cold_parity_requires_exact_cohort(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.num_users = 250
    settings.data.num_items = 500
    settings.data.num_cold_items = 250
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    model = HybridTwoTowerModel(settings)
    prepared_test = SimpleNamespace(
        split=SplitName.TEST,
        history_events=pd.DataFrame(
            columns=[
                "event_id",
                "internal_user_id",
                "internal_product_id",
                "event_type",
                "event_ts",
            ]
        ),
        latest_prior_purchase_contexts={},
    )

    # 1. Fewer than 250 cold items fails integrity
    snap_small = _snapshot(tmp_path)
    with pytest.raises(DataIntegrityError, match="expected exactly 250 cold items"):
        evaluate_cold_parity(
            hybrid_model=model,
            snapshot=snap_small,
            embeddings=np.eye(4, dtype=np.float32),
            rule_store=RuleStore(4, []),
            prepared_split=prepared_test,
            settings=settings,
            device=torch.device("cpu"),
        )

    # 2. 250 cold items but fewer than 250 cohort users fails integrity
    snap_250_items = Snapshot(
        manifest=SimpleNamespace(num_items=500, num_users=100),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame(
            {
                "product_id": range(1, 501),
                "internal_product_id": range(500),
                "internal_leaf_category_id": np.ones(500, dtype=int),
                "price_bucket_id": np.ones(500, dtype=int),
            }
        ),
        train_df=pd.DataFrame(),
        val_df=pd.DataFrame(),
        test_df=pd.DataFrame(),
        order_baskets_df=pd.DataFrame(),
        product_map={i + 1: i for i in range(500)},
        raw_product_map={i: i + 1 for i in range(500)},
        user_map={i + 1: i for i in range(100)},
        raw_user_map={i: i + 1 for i in range(100)},
        persona_map={i + 1: 0 for i in range(100)},
        cold_item_ids=tuple(range(250, 500)),
        price_boundaries=np.array([20.0]),
    )
    with pytest.raises(DataIntegrityError, match="expected at least 250 cohort users"):
        evaluate_cold_parity(
            hybrid_model=model,
            snapshot=snap_250_items,
            embeddings=np.zeros((500, 768), dtype=np.float32),
            rule_store=RuleStore(500, []),
            prepared_split=prepared_test,
            settings=settings,
            device=torch.device("cpu"),
        )

    # 3. Exactly 250 cold items and 250 cohort users passes parity
    snap_valid = Snapshot(
        manifest=SimpleNamespace(num_items=500, num_users=250),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame(
            {
                "product_id": range(1, 501),
                "internal_product_id": range(500),
                "internal_leaf_category_id": np.ones(500, dtype=int),
                "price_bucket_id": np.ones(500, dtype=int),
            }
        ),
        train_df=pd.DataFrame(
            {
                "event_id": ["e1"],
                "internal_user_id": [0],
                "internal_product_id": [0],
                "event_type": ["purchase"],
                "event_ts": pd.date_range("2026-01-01", periods=1, tz="UTC"),
                "event_origin": ["organic"],
            }
        ),
        val_df=pd.DataFrame(),
        test_df=pd.DataFrame(
            {
                "event_id": [f"cold-{i}" for i in range(250)],
                "internal_user_id": list(range(250)),
                "internal_product_id": [250 + (i % 250) for i in range(250)],
                "event_type": ["purchase"] * 250,
                "event_ts": pd.date_range("2026-02-01", periods=250, tz="UTC"),
                "event_origin": ["organic"] * 250,
            }
        ),
        order_baskets_df=pd.DataFrame(),
        product_map={i + 1: i for i in range(500)},
        raw_product_map={i: i + 1 for i in range(500)},
        user_map={i + 1: i for i in range(250)},
        raw_user_map={i: i + 1 for i in range(250)},
        persona_map={i + 1: 0 for i in range(250)},
        cold_item_ids=tuple(range(250, 500)),
        price_boundaries=np.array([20.0]),
    )
    # 2.5 Cold item present in rules fails integrity
    with pytest.raises(DataIntegrityError, match="cold item exists in Apriori rules"):
        evaluate_cold_parity(
            hybrid_model=model,
            snapshot=snap_valid,
            embeddings=np.zeros((500, 768), dtype=np.float32),
            rule_store=RuleStore(500, [(0, 250, 10.0)]),
            prepared_split=prepared_test,
            settings=settings,
            device=torch.device("cpu"),
        )

    report = evaluate_cold_parity(
        hybrid_model=model,
        snapshot=snap_valid,
        embeddings=np.zeros((500, 768), dtype=np.float32),
        rule_store=RuleStore(500, []),
        prepared_split=prepared_test,
        settings=settings,
        device=torch.device("cpu"),
    )
    assert report.cold_only_order_equality is True
    assert report.max_abs_wide_logit <= 1e-7
