from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch
from fastapi.testclient import TestClient

from ai_service.config import Settings
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.export.bundle import BundlePublisher
from ai_service.export.onnx import export_onnx_models
from ai_service.export.parity import verify_onnx_parity
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.serving.app import create_app
from ai_service.serving.runtime import RecommenderRuntime
from ai_service.serving.schemas import RecommendRequest


def test_export_bundle_and_runtime_use_real_ranker_graph(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.num_users = 2
    settings.data.num_items = 4
    settings.data.num_cold_items = 1
    settings.data.num_leaf_categories = 2
    settings.data.num_price_buckets = 2
    settings.model.sbert_dim = 4
    catalog = pd.DataFrame(
        {
            "product_id": [10, 20, 30, 40],
            "internal_product_id": [0, 1, 2, 3],
            "internal_leaf_category_id": [1, 1, 2, 2],
            "price_bucket_id": [1, 1, 2, 2],
        }
    )
    empty = pd.DataFrame(
        columns=["event_id", "internal_user_id", "internal_product_id", "event_type", "event_ts"]
    )
    snapshot = Snapshot(
        manifest=SimpleNamespace(
            num_items=4,
            num_users=2,
            store_id=1,
            artifact_id="fixture",
            content_sha256="a" * 64,
        ),
        snapshot_dir=tmp_path,
        catalog_df=catalog,
        train_df=empty,
        val_df=empty,
        test_df=empty,
        order_baskets_df=pd.DataFrame(),
        product_map={10: 0, 20: 1, 30: 2, 40: 3},
        raw_product_map={0: 10, 1: 20, 2: 30, 3: 40},
        user_map={100: 1, 200: 2},
        raw_user_map={1: 100, 2: 200},
        persona_map={100: 0, 200: 1},
        cold_item_ids=(3,),
        price_boundaries=np.array([20.0]),
    )
    embeddings = np.eye(4, dtype=np.float32)
    embeddings[3] = embeddings[0]
    model = HybridTwoTowerModel(settings).eval()
    rules = RuleStore(4, [(0, 1, 4.0)])
    export_dir = tmp_path / "run" / "export"
    paths = export_onnx_models(model, settings, export_dir)
    parity = verify_onnx_parity(
        model,
        settings,
        snapshot,
        embeddings,
        rules,
        paths,
        warmups=1,
        iterations=5,
    )
    item_vectors = (
        model.encode_items(
            torch.from_numpy(embeddings),
            torch.tensor([1, 1, 2, 2]),
            torch.tensor([1, 1, 2, 2]),
            item_idx=torch.arange(4),
            is_cold=torch.tensor([False, False, False, True]),
        )
        .detach()
        .numpy()
    )
    profiles = np.zeros((3, settings.model.item_emb_dim), dtype=np.float32)
    profiles[1] = item_vectors[2]
    profiles[2] = item_vectors[1]
    bundle = BundlePublisher(settings).publish(
        bundle_id="bundle-test",
        run_id="run-test",
        snapshot=snapshot,
        rule_store=rules,
        ranker_path=paths.ranker,
        item_vectors=item_vectors,
        user_profile_vectors=profiles,
        checkpoint_sha256="b" * 64,
        parity=parity,
    )
    runtime = RecommenderRuntime.load(bundle.path, settings)
    response = runtime.recommend(
        RecommendRequest(
            store_id=1,
            user_id=100,
            persona_cluster=0,
            candidate_product_ids=[10, 20, 30, 40],
            context_product_id=10,
        )
    )
    unknown_response = runtime.recommend(
        RecommendRequest(
            store_id=1,
            user_id=None,
            persona_cluster=0,
            candidate_product_ids=[10, 20, 30],
            context_product_id=None,
        )
    )
    settings.data.model_bundle_path = bundle.path
    with TestClient(create_app(settings)) as client:
        ready = client.get("/health/ready")
        http_response = client.post(
            "/recommend",
            json={
                "store_id": 1,
                "user_id": 100,
                "persona_cluster": 0,
                "candidate_product_ids": [10, 20, 30, 40],
                "context_product_id": 10,
            },
        )

    assert paths.item_encoder.exists()
    assert paths.ranker.exists()
    assert parity.max_abs_error <= 1e-5
    assert parity.ranking_parity_users >= 3
    assert bundle.manifest.ranking_parity_users >= 3
    assert {ranking.product_id for ranking in response.rankings} == {10, 20, 30, 40}
    assert response.bundle_id == "bundle-test"
    assert [ranking.ai_score for ranking in response.rankings[:3]] != [
        ranking.ai_score for ranking in unknown_response.rankings
    ]
    assert ready.status_code == 200
    assert ready.json()["bundle_id"] == "bundle-test"
    assert http_response.status_code == 200
    assert len(http_response.json()["rankings"]) == 4
