from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ai_service.config import Settings
from ai_service.data.quality import DataQualityAuditor
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.probes import run_data_probes


def test_data_quality_report_distinguishes_integrity_from_training_suitability(
    tmp_path: Path,
) -> None:
    columns = [
        "event_id",
        "internal_user_id",
        "internal_product_id",
        "event_type",
        "event_ts",
        "session_id",
        "event_origin",
    ]
    train = pd.DataFrame(
        [
            ("a", 1, 0, "view", "2026-01-01T00:00:00Z", "s1", "organic"),
            ("b", 1, 0, "purchase", "2026-01-01T00:01:00Z", "s1", "organic"),
            ("c", 2, 1, "purchase", "2026-01-02T00:00:00Z", "s2", "organic"),
            ("d", 2, 2, "view", "2026-01-02T00:01:00Z", "s2", "organic"),
        ],
        columns=columns,
    )
    val = pd.DataFrame(
        [("e", 1, 2, "purchase", "2026-02-01T00:00:00Z", "s3", "organic")],
        columns=columns,
    )
    test = pd.DataFrame(
        [("f", 2, 3, "purchase", "2026-03-01T00:00:00Z", "s4", "cold_start")],
        columns=columns,
    )
    for frame in (train, val, test):
        frame["event_ts"] = pd.to_datetime(frame.event_ts, utc=True)
    snapshot = Snapshot(
        manifest=SimpleNamespace(num_users=2, num_items=4),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame({"internal_product_id": range(4)}),
        train_df=train,
        val_df=val,
        test_df=test,
        order_baskets_df=pd.DataFrame(),
        product_map={10: 0, 20: 1, 30: 2, 40: 3},
        raw_product_map={0: 10, 1: 20, 2: 30, 3: 40},
        user_map={100: 1, 200: 2},
        raw_user_map={1: 100, 2: 200},
        persona_map={100: 0, 200: 1},
        cold_item_ids=(3,),
        price_boundaries=np.asarray([10.0]),
    )

    report = DataQualityAuditor().audit(snapshot)

    assert report.total_events == 6
    assert report.unique_user_item_pairs == 5
    assert report.converted_pairs == 1
    assert report.purchase_with_prior_view_fraction == 0.5
    assert report.fixture_event_counts == {"cold_start": 1}
    assert report.organic_novel_purchase_users == {"val": 1, "test": 0}
    assert report.training_suitability_passed is False
    assert "purchase_prior_view_fraction_below_0.8" in report.gate_failures


def test_data_probes_measure_each_non_neural_signal(tmp_path: Path) -> None:
    columns = [
        "event_id",
        "internal_user_id",
        "internal_product_id",
        "event_type",
        "event_ts",
        "session_id",
        "event_origin",
    ]
    train = pd.DataFrame(
        [
            ("a", 1, 0, "purchase", "2026-01-01T00:00:00Z", "s1", "organic"),
            ("b", 1, 1, "purchase", "2026-01-02T00:00:00Z", "s2", "organic"),
            ("c", 2, 1, "purchase", "2026-01-03T00:00:00Z", "s3", "organic"),
            ("d", 2, 2, "view", "2026-01-04T00:00:00Z", "s4", "organic"),
        ],
        columns=columns,
    )
    val = pd.DataFrame(
        [
            ("e", 1, 2, "purchase", "2026-02-01T00:00:00Z", "s5", "organic"),
            ("f", 2, 3, "purchase", "2026-02-02T00:00:00Z", "s6", "organic"),
        ],
        columns=columns,
    )
    for frame in (train, val):
        frame["event_ts"] = pd.to_datetime(frame.event_ts, utc=True)
    empty = val.iloc[0:0].copy()
    snapshot = Snapshot(
        manifest=SimpleNamespace(
            num_users=2,
            num_items=4,
            artifact_id="probe-snapshot",
            content_sha256="a" * 64,
        ),
        snapshot_dir=tmp_path,
        catalog_df=pd.DataFrame(
            {
                "internal_product_id": range(4),
                "internal_leaf_category_id": [1, 1, 2, 2],
            }
        ),
        train_df=train,
        val_df=val,
        test_df=empty,
        order_baskets_df=pd.DataFrame(),
        product_map={10: 0, 20: 1, 30: 2, 40: 3},
        raw_product_map={0: 10, 1: 20, 2: 30, 3: 40},
        user_map={100: 1, 200: 2},
        raw_user_map={1: 100, 2: 200},
        persona_map={100: 0, 200: 1},
        cold_item_ids=(),
        price_boundaries=np.asarray([10.0]),
    )
    settings = Settings()
    settings.eval.k = 2

    report = run_data_probes(settings, snapshot, np.eye(4, dtype=np.float32))

    assert report["embedding_shape"] == [4, 4]
    assert report["popularity_only"]["eligible_users"] == 2
    assert report["persona_only"]["eligible_users"] == 2
    assert report["sbert_centroid"]["eligible_users"] == 2
    assert report["item_item_cf"]["eligible_users"] == 2
    assert isinstance(report["label_permutation_sanity"]["passed"], bool)
