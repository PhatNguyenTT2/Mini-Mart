"""Standalone ONNX Runtime Serving Test Harness for ai-service.

Verifies PyTorch vs ONNX output parity (atol < 1e-4) and measures warm-start candidate reranking latency (< 1.0 ms requirement for 32 users x 5 candidate items).
"""

import time
import pytest
import numpy as np
import torch

try:
    import onnxruntime as ort
    HAS_ONNX_RUNTIME = True
except ImportError:
    HAS_ONNX_RUNTIME = False

from config import get_settings
from models.two_tower_wide_deep import HybridTwoTowerModel
from export.export_onnx import export_all_onnx_models


@pytest.mark.skipif(not HAS_ONNX_RUNTIME, reason="onnxruntime is not installed")
def test_onnx_export_and_inference_parity(tmp_path):
    model = HybridTwoTowerModel()
    model.eval()

    export_paths = export_all_onnx_models(model, export_dir=tmp_path)

    # 1. Test User Tower ONNX Parity
    user_session = ort.InferenceSession(str(export_paths["user_tower"]))
    u_idx = np.array([1, 42], dtype=np.int64)
    p_idx = np.array([0, 2], dtype=np.int64)

    with torch.no_grad():
        pt_user_vec = (
            model.encode_users(torch.tensor(u_idx), torch.tensor(p_idx)).cpu().numpy()
        )

    onnx_user_vec = user_session.run(
        None, {"user_idx": u_idx, "persona_idx": p_idx}
    )[0]

    np.testing.assert_allclose(pt_user_vec, onnx_user_vec, atol=1e-4, rtol=1e-4)

    # 2. Test Item Tower ONNX Parity
    item_session = ort.InferenceSession(str(export_paths["item_tower"]))
    sbert = np.random.randn(2, 5, 768).astype(np.float32)
    cat = np.random.randint(0, 41, (2, 5)).astype(np.int64)
    price = np.random.randint(0, 9, (2, 5)).astype(np.int64)

    with torch.no_grad():
        pt_item_vec = (
            model.encode_items(
                torch.tensor(sbert), torch.tensor(cat), torch.tensor(price)
            )
            .cpu()
            .numpy()
        )

    onnx_item_vec = item_session.run(
        None,
        {
            "sbert_embedding": sbert,
            "category_idx": cat,
            "price_idx": price,
        },
    )[0]

    np.testing.assert_allclose(pt_item_vec, onnx_item_vec, atol=1e-4, rtol=1e-4)

    # 3. Test Full Hybrid Recommender Candidate Reranking ONNX Parity & Warm Latency
    hybrid_session = ort.InferenceSession(str(export_paths["hybrid_recommender"]))

    user_vecs = np.random.randn(32, 64).astype(np.float32)
    item_vecs = np.random.randn(32, 5, 64).astype(np.float32)
    log_lift = np.random.randn(32, 5, 1).astype(np.float32)

    with torch.no_grad():
        pt_logits = (
            model.score_candidates(
                torch.tensor(user_vecs),
                torch.tensor(item_vecs),
                torch.tensor(log_lift),
            )
            .logits.cpu()
            .numpy()
        )

    onnx_logits = hybrid_session.run(
        None,
        {
            "user_vector": user_vecs,
            "item_vector": item_vecs,
            "log_lift": log_lift,
        },
    )[0]

    np.testing.assert_allclose(pt_logits, onnx_logits, atol=1e-4, rtol=1e-4)

    # 4. Latency Benchmark: 100 warm iterations for [32 users x 5 candidate items]
    # Warm-up pass
    for _ in range(10):
        _ = hybrid_session.run(
            None,
            {
                "user_vector": user_vecs,
                "item_vector": item_vecs,
                "log_lift": log_lift,
            },
        )

    t0 = time.time()
    num_runs = 100
    for _ in range(num_runs):
        _ = hybrid_session.run(
            None,
            {
                "user_vector": user_vecs,
                "item_vector": item_vecs,
                "log_lift": log_lift,
            },
        )
    total_time_ms = (time.time() - t0) * 1000.0
    avg_latency_ms = total_time_ms / num_runs

    # Production Budget Assertion: Warm ONNX Candidate Reranking MUST be < 1.0 ms
    assert (
        avg_latency_ms < 1.0
    ), f"ONNX scoring latency {avg_latency_ms:.3f} ms exceeds < 1.0 ms production budget"
