from __future__ import annotations

import json
import os
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
from fastapi.testclient import TestClient

from ai_service.config import Settings
from ai_service.export.bundle import verify_bundle
from ai_service.serving.app import create_app


def _bundle_path() -> Path:
    configured = os.environ.get("AI_BENCHMARK_BUNDLE_PATH")
    if not configured:
        pytest.skip("AI_BENCHMARK_BUNDLE_PATH is required on the fixed benchmark runner")
    path = Path(configured).resolve()
    verify_bundle(path)
    return path


@pytest.mark.benchmark
def test_full_catalog_kernel_p95_is_below_one_millisecond() -> None:
    path = _bundle_path()
    vectors = np.load(path / "item_vectors.npy", mmap_mode="r")
    assert vectors.shape == (5_200, 64)
    session = ort.InferenceSession(str(path / "ranker.onnx"), providers=["CPUExecutionProvider"])
    feed = {
        "user_idx": np.asarray([0], dtype=np.int64),
        "persona_idx": np.asarray([8], dtype=np.int64),
        "history_vector": np.zeros((1, 64), dtype=np.float32),
        "history_present": np.zeros(1, dtype=np.bool_),
        "candidate_vectors": np.asarray(vectors[None, ...], dtype=np.float32),
        "wide_values": np.zeros((1, 5_200, 3), dtype=np.float32),
        "rule_present": np.zeros((1, 5_200), dtype=np.bool_),
    }
    for _ in range(200):
        session.run(None, feed)
    durations = np.empty(2_000, dtype=np.float64)
    for index in range(len(durations)):
        started = time.perf_counter_ns()
        session.run(None, feed)
        durations[index] = (time.perf_counter_ns() - started) / 1_000_000

    p95 = float(np.quantile(durations, 0.95))
    print({"hardware": platform.platform(), "kernel_p95_ms": p95})
    assert p95 < 1.0


@pytest.mark.benchmark
def test_http_p95_is_at_most_fifty_milliseconds_at_concurrency_sixteen() -> None:
    path = _bundle_path()
    settings = Settings()
    settings.data.model_bundle_path = path
    bundle = verify_bundle(path)
    mappings = json.loads((path / "mappings.json").read_text(encoding="utf-8"))
    candidates = [int(value) for value in list(mappings["product_map"])[:256]]
    payload = {
        "store_id": bundle.manifest.store_id,
        "user_id": None,
        "persona_cluster": None,
        "candidate_product_ids": candidates,
        "context_product_id": None,
    }
    with TestClient(create_app(settings)) as client:
        for _ in range(50):
            assert client.post("/recommend", json=payload).status_code == 200

        def request_once(_: int) -> float:
            started = time.perf_counter_ns()
            response = client.post("/recommend", json=payload)
            assert response.status_code == 200
            return (time.perf_counter_ns() - started) / 1_000_000

        with ThreadPoolExecutor(max_workers=16) as executor:
            durations = list(executor.map(request_once, range(320)))

    p95 = float(np.quantile(durations, 0.95))
    print({"hardware": platform.platform(), "http_p95_ms": p95})
    assert p95 <= 50.0
