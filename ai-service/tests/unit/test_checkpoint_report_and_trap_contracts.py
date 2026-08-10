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
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation.report import write_evaluation_report
from ai_service.evaluation.semantic_traps import evaluate_semantic_traps
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager


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

    manifest = CheckpointManager.save(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        epoch=2,
        metrics={"val_gauc": 0.6, "train_loss": 0.3},
        lineage=lineage,
        training_signature_sha256="d" * 64,
        model_schema_version="5.0.0",
        run_id="run-test",
    )
    original = {name: value.detach().clone() for name, value in model.state_dict().items()}
    expected_rng = (random.random(), float(np.random.random()), float(torch.rand(())))
    with torch.no_grad():
        next(model.parameters()).add_(1.0)
    state = CheckpointManager.load(
        path,
        model=model,
        expected_lineage=lineage,
        expected_training_signature="d" * 64,
        expected_model_schema_version="5.0.0",
        restore_rng=True,
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

    with pytest.raises(ArtifactIntegrityError, match="model schema"):
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
    lineage = {
        "snapshot": "a" * 64,
        "embedding": "b" * 64,
        "rules": "c" * 64,
        "checkpoint": "d" * 64,
    }
    json_path, markdown_path = write_evaluation_report(
        tmp_path / "report",
        payload={"actual_rule_count": 2, "latency_ms": 0.7},
        lineage=lineage,
    )
    document = json.loads(json_path.read_text(encoding="utf-8"))
    assert document["results"]["actual_rule_count"] == 2
    assert "Report SHA-256" in markdown_path.read_text(encoding="utf-8")

    fixture = tmp_path / "traps.json"
    fixture.write_text(
        json.dumps([{"trap_id": 1, "anchor_product_id": 101, "target_product_ids": [102]}]),
        encoding="utf-8",
    )
    model = HybridTwoTowerModel(_settings())
    trap_report = evaluate_semantic_traps(
        model,
        None,
        _snapshot(tmp_path),
        np.eye(4, dtype=np.float32),
        RuleStore(4, [(0, 1, 10.0)]),
        fixture,
        k=2,
    )
    assert trap_report.total == 1
    assert trap_report.results[0].target_product_ids == (102,)
