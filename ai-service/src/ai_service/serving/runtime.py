"""Immutable ONNX Runtime recommendation module."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from ai_service.config import Settings
from ai_service.contracts import ModelBundleManifest
from ai_service.errors import ServingUnavailableError
from ai_service.export.bundle import verify_bundle
from ai_service.serving.schemas import ProductRanking, RecommendRequest, RecommendResponse


@dataclass(frozen=True)
class _RuleIndex:
    crow: np.ndarray
    columns: np.ndarray
    features: np.ndarray
    raw_lifts: np.ndarray
    counts: np.ndarray

    def lookup(
        self,
        context: int,
        candidates: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        output = np.zeros((1, len(candidates), 3), dtype=np.float32)
        present = np.zeros((1, len(candidates)), dtype=np.bool_)
        if context < 0:
            return output, present
        start, end = int(self.crow[context]), int(self.crow[context + 1])
        row_columns = self.columns[start:end]
        positions = np.searchsorted(row_columns, candidates)
        valid = positions < len(row_columns)
        matched = np.zeros(len(candidates), dtype=np.bool_)
        matched[valid] = row_columns[positions[valid]] == candidates[valid]
        present[0] = matched
        matched_positions = positions[matched]
        output[0, matched] = self.features[start:end][matched_positions]
        return output, present


class RecommenderRuntime:
    def __init__(
        self,
        *,
        settings: Settings,
        bundle_path: Path,
        manifest: ModelBundleManifest,
        session: ort.InferenceSession,
        item_vectors: np.ndarray,
        user_profile_vectors: np.ndarray,
        temperature: float,
        product_map: dict[int, int],
        user_map: dict[int, int],
        persona_map: dict[int, int],
        rules: _RuleIndex,
    ) -> None:
        self.settings = settings
        self.bundle_path = bundle_path
        self.manifest = manifest
        self.session = session
        self.item_vectors = item_vectors
        self.user_profile_vectors = user_profile_vectors
        self.temperature = temperature
        self.product_map = product_map
        self.user_map = user_map
        self.persona_map = persona_map
        self.rules = rules

    @classmethod
    def load(cls, bundle_path: Path, settings: Settings) -> RecommenderRuntime:
        try:
            bundle = verify_bundle(bundle_path)
            options = ort.SessionOptions()
            options.intra_op_num_threads = settings.serving.ort_intra_op_threads
            options.inter_op_num_threads = settings.serving.ort_inter_op_threads
            session = ort.InferenceSession(
                str(bundle.path / "ranker.onnx"),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            vectors = np.load(bundle.path / "item_vectors.npy", mmap_mode="r")
            user_profiles = np.load(bundle.path / "user_profile_vectors.npy", mmap_mode="r")
            mappings = json.loads((bundle.path / "mappings.json").read_text(encoding="utf-8"))
            normalization = json.loads(
                (bundle.path / "normalization.json").read_text(encoding="utf-8")
            )
            arrays = np.load(bundle.path / "rules.npz")
            return cls(
                settings=settings,
                bundle_path=bundle.path,
                manifest=bundle.manifest,
                session=session,
                item_vectors=vectors,
                user_profile_vectors=user_profiles,
                temperature=float(normalization["tau"]),
                product_map={
                    int(key): int(value) for key, value in mappings["product_map"].items()
                },
                user_map={int(key): int(value) for key, value in mappings["user_map"].items()},
                persona_map={
                    int(key): int(value) for key, value in mappings["persona_map"].items()
                },
                rules=_RuleIndex(
                    arrays["crow_indices"],
                    arrays["col_indices"],
                    arrays["features"],
                    arrays["raw_lifts"],
                    arrays["counts"],
                ),
            )
        except Exception as error:
            raise ServingUnavailableError(f"cannot load model bundle: {error}") from error

    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        manifest = self.manifest
        if request.store_id != manifest.store_id:
            raise ValueError("request store does not match model bundle")
        unknown = [
            value for value in request.candidate_product_ids if value not in self.product_map
        ]
        if unknown:
            raise ValueError(f"unknown candidate product IDs: {unknown}")
        if (
            request.context_product_id is not None
            and request.context_product_id not in self.product_map
        ):
            raise ValueError("unknown context product ID")
        candidates = np.asarray(
            [self.product_map[value] for value in request.candidate_product_ids], dtype=np.int64
        )
        user_idx = self.user_map.get(request.user_id, 0) if request.user_id is not None else 0
        if request.persona_cluster is None:
            persona_idx = (
                self.persona_map.get(request.user_id, self.settings.data.num_personas)
                if request.user_id is not None
                else self.settings.data.num_personas
            )
        else:
            persona_idx = request.persona_cluster
        context = (
            self.product_map[request.context_product_id]
            if request.context_product_id is not None
            else -1
        )
        wide, present = self.rules.lookup(context, candidates)
        started = time.perf_counter_ns()
        logits = self.session.run(
            None,
            {
                "user_idx": np.asarray([user_idx], dtype=np.int64),
                "persona_idx": np.asarray([persona_idx], dtype=np.int64),
                "history_vector": np.asarray(
                    self.user_profile_vectors[[user_idx]], dtype=np.float32
                ),
                "history_present": np.asarray(
                    [bool(np.linalg.norm(self.user_profile_vectors[user_idx]) > 0)],
                    dtype=np.bool_,
                ),
                "candidate_vectors": np.asarray(
                    self.item_vectors[candidates][None, ...], dtype=np.float32
                ),
                "wide_values": wide,
                "rule_present": present,
            },
        )[0][0]
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        raw_ids = np.asarray(request.candidate_product_ids, dtype=np.int64)
        order = np.lexsort((raw_ids, -logits))
        rankings = [
            ProductRanking(
                product_id=int(raw_ids[item_index]),
                rank=rank + 1,
                ai_score=float(logits[item_index]),
            )
            for rank, item_index in enumerate(order)
        ]
        return RecommendResponse(
            rankings=rankings,
            inference_ms=elapsed,
            model_version=manifest.model_version,
            bundle_id=manifest.bundle_id,
        )
