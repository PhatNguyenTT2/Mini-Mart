from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service.config import Settings
from ai_service.data.dataset import PurchaseBatch
from ai_service.data.rule_readiness import assess_training_rule_readiness
from ai_service.data.rules import AprioriRuleMiner, load_rule_artifact
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError


def _snapshot(tmp_path: Path) -> Snapshot:
    catalog = pd.DataFrame({"product_id": [10, 11, 12], "unit_price": [1, 2, 3]})
    frame = pd.DataFrame(
        {
            "event_id": ["a", "b", "c", "d"],
            "internal_user_id": [1, 1, 2, 2],
            "internal_product_id": [0, 1, 1, 2],
            "event_type": ["purchase"] * 4,
            "event_origin": ["organic"] * 4,
            "event_ts": pd.date_range("2026-01-01", periods=4, tz="UTC"),
        }
    )
    baskets = pd.DataFrame({"order_id": [1, 1, 2, 2], "internal_product_id": [0, 1, 1, 2]})
    return Snapshot(
        manifest=SimpleNamespace(num_items=3, artifact_id="fixture", content_sha256="a" * 64),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=frame,
        val_df=frame.iloc[0:0].copy(),
        test_df=frame.iloc[0:0].copy(),
        order_baskets_df=baskets,
        product_map={10: 0, 11: 1, 12: 2},
        raw_product_map={0: 10, 1: 11, 2: 12},
        user_map={1: 1, 2: 2},
        raw_user_map={1: 1, 2: 2},
        persona_map={1: 0, 2: 0},
        cold_item_ids=(),
        price_boundaries=np.asarray([2.0]),
    )


def _batch() -> PurchaseBatch:
    return PurchaseBatch(
        user_idx=torch.tensor([1, 2]),
        persona_idx=torch.tensor([0, 0]),
        context_item_idx=torch.tensor([0, 1]),
        positive_item_idx=torch.tensor([1, 2]),
        explicit_negative_idx=torch.tensor([[2, 0], [0, 1]]),
        positive_mask=torch.tensor([[True, False], [False, True]]),
        denominator_mask=torch.tensor([[True, True], [True, True]]),
        confidence=torch.ones(2),
        history_item_idx=torch.zeros((2, 1), dtype=torch.long),
        history_mask=torch.ones((2, 1), dtype=torch.bool),
        history_age_days=torch.zeros((2, 1)),
        in_batch_wide_values=torch.ones((2, 2, 3)),
        in_batch_rule_present=torch.tensor([[True, False], [False, True]]),
        explicit_wide_values=torch.ones((2, 2, 3)),
        explicit_rule_present=torch.tensor([[False, True], [False, False]]),
    )


def test_training_rule_readiness_uses_purchase_masks_and_rows() -> None:
    report = assess_training_rule_readiness([_batch()], minimum_rows_with_any_rule=0.5)
    assert report.passed is True
    assert report.in_batch_rule_present_rate == 0.5
    assert report.explicit_rule_present_rate == 0.25
    assert report.rows_with_any_rule_rate == 1.0


def test_training_rule_readiness_restores_epoch_one_after_scan() -> None:
    class RecordingLoader:
        def __init__(self) -> None:
            self.epochs: list[int] = []

        def set_epoch(self, epoch: int) -> None:
            self.epochs.append(epoch)

        def __iter__(self):
            yield _batch()

    loader = RecordingLoader()

    assess_training_rule_readiness(loader, minimum_rows_with_any_rule=0.5)

    assert loader.epochs == [1, 1]


def test_v3_rule_artifact_contains_organic_coverage(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.data.min_rule_count = 1
    artifact = AprioriRuleMiner(settings).mine(_snapshot(tmp_path))
    assert artifact.manifest.feature_schema_version == "3.0.0"
    assert artifact.manifest.coverage_semantics_version == "semantic-trap-purchase-v2"
    assert artifact.manifest.coverage is not None
    assert artifact.manifest.coverage.non_trap_directed_rules == 4

    legacy_document = json.loads(
        (artifact.artifact_dir / "manifest.json").read_text(encoding="utf-8")
    )
    legacy_document.pop("coverage_semantics_version")
    (artifact.artifact_dir / "manifest.json").write_text(
        json.dumps(legacy_document), encoding="utf-8"
    )
    legacy = load_rule_artifact(artifact.artifact_dir, num_items=3)
    with pytest.raises(ArtifactIntegrityError, match="organic coverage evidence"):
        legacy.require_training_capability(settings)

    legacy_document["coverage_semantics_version"] = "semantic-trap-only-v1"
    (artifact.artifact_dir / "manifest.json").write_text(
        json.dumps(legacy_document), encoding="utf-8"
    )
    legacy_v1 = load_rule_artifact(artifact.artifact_dir, num_items=3)
    with pytest.raises(ArtifactIntegrityError, match="organic coverage evidence"):
        legacy_v1.require_training_capability(settings)


def test_v3_rule_coverage_treats_only_semantic_trap_events_as_traps(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.data.min_rule_count = 1
    snapshot = _snapshot(tmp_path)
    frame = snapshot.train_df.copy()
    frame["event_origin"] = ["cold_start", "organic", "organic", "semantic_trap"]

    artifact = AprioriRuleMiner(settings).mine(replace(snapshot, train_df=frame))

    assert artifact.manifest.coverage is not None
    assert artifact.manifest.coverage.non_trap_directed_rules == 2
    assert artifact.manifest.coverage.trap_anchored_directed_rules == 2


def test_v3_rule_coverage_uses_only_purchase_history_and_context(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.data.min_rule_count = 1
    snapshot = _snapshot(tmp_path)
    train = snapshot.train_df.iloc[:2].copy()
    train["internal_product_id"] = [0, 2]
    train["event_type"] = ["purchase", "view"]
    train["event_origin"] = ["organic", "organic"]
    val = train.iloc[:1].copy()
    val["event_id"] = ["val-purchase"]
    val["internal_product_id"] = [2]
    val["event_type"] = ["purchase"]
    val["event_ts"] = [pd.Timestamp("2026-01-02T00:00:00Z")]

    artifact = AprioriRuleMiner(settings).mine(replace(snapshot, train_df=train, val_df=val))

    assert artifact.manifest.coverage is not None
    assert artifact.manifest.coverage.eligible_val_context_users == 1
    assert artifact.manifest.coverage.val_context_users_with_rule == 1
