"""Independent ONNX checker, parity, and measured kernel latency."""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass

import numpy as np
import onnx
import onnxruntime as ort
import pandas as pd
import torch

from ai_service.config import Settings
from ai_service.contracts import ModelVariant
from ai_service.data.history import build_user_profile_vectors
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ExportValidationError
from ai_service.export.onnx import OnnxPaths
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class ParityReport:
    max_abs_error: float
    graph_errors: dict[str, float]
    kernel_latency_ms: dict[str, float]
    tested_shapes: tuple[tuple[int, int], ...]
    hardware: dict[str, str]
    ranking_parity_users: int


def _session(path: object, settings: Settings) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = settings.serving.ort_intra_op_threads
    options.inter_op_num_threads = settings.serving.ort_inter_op_threads
    return ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])


def verify_onnx_parity(
    model: HybridTwoTowerModel,
    settings: Settings,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    paths: OnnxPaths,
    *,
    warmups: int = 200,
    iterations: int = 2_000,
) -> ParityReport:
    for path in (paths.item_encoder, paths.ranker):
        onnx.checker.check_model(onnx.load(path, load_external_data=True), full_check=True)
    model = model.cpu().eval()
    catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
    category = catalog.internal_leaf_category_id.to_numpy(np.int64)
    price = catalog.price_bucket_id.to_numpy(np.int64)
    item_ids = np.arange(snapshot.manifest.num_items, dtype=np.int64)
    is_cold = np.isin(item_ids, np.asarray(snapshot.cold_item_ids, dtype=np.int64))
    item_session = _session(paths.item_encoder, settings)
    ranker_session = _session(paths.ranker, settings)
    with torch.no_grad():
        torch_items = model.encode_items(
            torch.from_numpy(np.array(embeddings, dtype=np.float32, copy=True)),
            torch.from_numpy(category),
            torch.from_numpy(price),
            item_idx=torch.from_numpy(item_ids),
            is_cold=torch.from_numpy(is_cold),
        ).numpy()
    ort_items = item_session.run(
        None,
        {
            "sbert": np.asarray(embeddings, dtype=np.float32),
            "category_idx": category,
            "price_idx": price,
            "item_idx": item_ids,
            "is_cold": is_cold,
        },
    )[0]
    errors = {"item_encoder": float(np.max(np.abs(torch_items - ort_items)))}
    shapes = ((1, 1), (3, 7), (1, 256), (1, snapshot.manifest.num_items))
    rng = np.random.default_rng(42)
    last_feed: dict[str, np.ndarray] | None = None
    for batch, candidates in shapes:
        users = rng.integers(0, settings.data.num_users + 1, size=batch, dtype=np.int64)
        personas = rng.integers(0, settings.data.num_personas + 1, size=batch, dtype=np.int64)
        history_vectors = rng.normal(size=(batch, settings.model.item_emb_dim)).astype(np.float32)
        history_vectors /= np.maximum(
            np.linalg.norm(history_vectors, axis=1, keepdims=True),
            np.finfo(np.float32).eps,
        )
        history_present = rng.random(batch) > 0.25
        history_vectors[~history_present] = 0.0
        selected = rng.integers(0, len(torch_items), size=(batch, candidates))
        candidate_vectors = torch_items[selected].astype(np.float32)
        wide = rng.random((batch, candidates, 3), dtype=np.float32)
        wide[..., 0] *= 4.0
        wide[..., 2] *= 8.0
        present = rng.random((batch, candidates)) > 0.5
        with torch.no_grad():
            expected = model.score_cached(
                torch.from_numpy(users),
                torch.from_numpy(personas),
                torch.from_numpy(candidate_vectors),
                torch.from_numpy(wide),
                torch.from_numpy(present),
                ModelVariant.HYBRID,
                history_vector=torch.from_numpy(history_vectors),
                history_present=torch.from_numpy(history_present),
            ).numpy()
        feed: dict[str, np.ndarray] = {
            "user_idx": users,
            "persona_idx": personas,
            "history_vector": history_vectors,
            "history_present": history_present,
            "candidate_vectors": candidate_vectors,
            "wide_values": wide,
            "rule_present": present,
        }
        actual = ranker_session.run(None, feed)[0]
        errors[f"ranker_{batch}x{candidates}"] = float(np.max(np.abs(expected - actual)))
        if batch == 1 and candidates == snapshot.manifest.num_items:
            last_feed = feed
    history = pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True)
    torch_item_tensor = torch.from_numpy(torch_items)
    profiles = build_user_profile_vectors(
        model,
        snapshot,
        torch_item_tensor,
        history,
        max_history_items=settings.train.max_history_items,
        device=torch.device("cpu"),
    ).numpy()
    if not settings.train.use_history_profiles:
        profiles.fill(0.0)
    purchases = history[history.event_type == "purchase"].sort_values(
        ["event_ts", "event_id"], kind="stable"
    )
    last_purchases = purchases.groupby("internal_user_id").internal_product_id.last()
    contexts = dict(
        zip(
            last_purchases.index.to_numpy(dtype=np.int64).tolist(),
            last_purchases.to_numpy(dtype=np.int64).tolist(),
            strict=True,
        )
    )
    real_users = [0, *range(1, min(snapshot.manifest.num_users, 100) + 1)]
    raw_ids = np.asarray(
        [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
        dtype=np.int64,
    )
    all_candidates = np.arange(snapshot.manifest.num_items, dtype=np.int64)
    cold_candidates = np.asarray(snapshot.cold_item_ids, dtype=np.int64)
    semantic_vectors = np.asarray(embeddings, dtype=np.float32)
    semantic_vectors = semantic_vectors / np.maximum(
        np.linalg.norm(semantic_vectors, axis=1, keepdims=True),
        np.finfo(np.float32).eps,
    )
    for offset in range(0, len(real_users), 10):
        users = np.asarray(real_users[offset : offset + 10], dtype=np.int64)
        personas = np.asarray(
            [
                settings.data.num_personas
                if user == 0
                else snapshot.persona_map.get(
                    snapshot.raw_user_map[int(user)], settings.data.num_personas
                )
                for user in users
            ],
            dtype=np.int64,
        )
        context_ids = np.asarray([contexts.get(int(user), -1) for user in users], dtype=np.int64)
        candidate_matrix = np.broadcast_to(all_candidates, (len(users), len(all_candidates)))
        wide, present = rule_store.batch_lookup(context_ids, candidate_matrix)
        candidate_vectors = np.broadcast_to(torch_items, (len(users), *torch_items.shape)).copy()
        history_vectors = profiles[users].astype(np.float32)
        history_present = np.linalg.norm(history_vectors, axis=1) > 0
        with torch.no_grad():
            expected = model.score_cached(
                torch.from_numpy(users),
                torch.from_numpy(personas),
                torch.from_numpy(candidate_vectors),
                torch.from_numpy(wide),
                torch.from_numpy(present),
                ModelVariant.HYBRID,
                history_vector=torch.from_numpy(history_vectors),
                history_present=torch.from_numpy(history_present),
            ).numpy()
        feed = {
            "user_idx": users,
            "persona_idx": personas,
            "history_vector": history_vectors,
            "history_present": history_present,
            "candidate_vectors": candidate_vectors,
            "wide_values": wide,
            "rule_present": present,
        }
        actual = ranker_session.run(None, feed)[0]
        errors[f"runtime_policy_{offset}"] = float(np.max(np.abs(expected - actual)))
        for expected_row, actual_row in zip(expected, actual, strict=True):
            expected_order = np.lexsort((raw_ids, -expected_row))
            actual_order = np.lexsort((raw_ids, -actual_row))
            if not np.array_equal(expected_order, actual_order):
                raise ExportValidationError("evaluator and ONNX runtime ranking order differ")
    maximum = max(errors.values())
    if not np.isfinite(maximum) or maximum > 1e-5:
        raise ExportValidationError(f"ONNX parity {maximum} exceeds 1e-5")
    if last_feed is None:
        raise ExportValidationError("full-catalog parity shape was not exercised")
    for _ in range(warmups):
        ranker_session.run(None, last_feed)
    durations = np.empty(iterations, dtype=np.float64)
    for index in range(iterations):
        started = time.perf_counter_ns()
        ranker_session.run(None, last_feed)
        durations[index] = (time.perf_counter_ns() - started) / 1_000_000
    latency = {
        "p50": float(np.quantile(durations, 0.50)),
        "p95": float(np.quantile(durations, 0.95)),
        "p99": float(np.quantile(durations, 0.99)),
    }
    hardware = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "logical_cpu_count": str(os.cpu_count() or "unknown"),
        "onnxruntime_version": ort.__version__,
        "provider": "CPUExecutionProvider",
    }
    return ParityReport(maximum, errors, latency, shapes, hardware, len(real_users))
