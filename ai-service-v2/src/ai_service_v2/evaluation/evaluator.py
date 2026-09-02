"""Independent full-catalog evaluator for every model and adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ai_service_v2.contracts import EvaluationReceipt
from ai_service_v2.errors import ScoreError
from ai_service_v2.evaluation.metrics import (
    UserMetrics,
    aggregate_user_metrics_at_k,
    ranking_metrics,
)
from ai_service_v2.hashing import canonical_json_bytes, sha256_bytes
from ai_service_v2.protocol import PreparedProtocol

ScoreProvider = Callable[[int, tuple[int, ...]], np.ndarray]
"""Small seam: a model emits one score vector in frozen catalog order."""


@dataclass(frozen=True)
class EvaluationResult:
    receipt: EvaluationReceipt
    user_ids: tuple[int, ...]
    per_user_metrics: dict[str, tuple[float | None, ...]]
    top_k_by_user: dict[int, tuple[int, ...]]


def per_user_metrics_mapping(
    user_ids: tuple[int, ...],
    per_user_metrics: dict[str, tuple[float | None, ...]],
    cutoff: int,
) -> dict[str, list[dict[str, object]]]:
    """Build the canonical per-user payload used by receipts and persistence."""

    required = {f"HR@{cutoff}", f"NDCG@{cutoff}", "GAUC"}
    if set(per_user_metrics) != required:
        raise ScoreError("per-user metric keys do not match evaluator protocol")
    if any(len(values) != len(user_ids) for values in per_user_metrics.values()):
        raise ScoreError("per-user metric vector lengths do not match user IDs")
    payload: list[dict[str, object]] = [
        {
            "user_id": user_id,
            f"HR@{cutoff}": per_user_metrics[f"HR@{cutoff}"][index],
            f"NDCG@{cutoff}": per_user_metrics[f"NDCG@{cutoff}"][index],
            "GAUC": per_user_metrics["GAUC"][index],
        }
        for index, user_id in enumerate(user_ids)
    ]
    return {"rows": payload}


def per_user_metrics_sha256(
    user_ids: tuple[int, ...],
    per_user_metrics: dict[str, tuple[float | None, ...]],
    cutoff: int,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(per_user_metrics_mapping(user_ids, per_user_metrics, cutoff))
    )


def _per_user_hash(user_ids: tuple[int, ...], rows: list[UserMetrics], cutoff: int) -> str:
    per_user = {
        f"HR@{cutoff}": tuple(row.hit_rate for row in rows),
        f"NDCG@{cutoff}": tuple(row.ndcg for row in rows),
        "GAUC": tuple(row.gauc for row in rows),
    }
    return per_user_metrics_sha256(user_ids, per_user, cutoff)


class FullCatalogEvaluator:
    """Own masking, ranking, denominators, and aggregation; never trains."""

    def __init__(self, protocol: PreparedProtocol, *, evaluator_version: str = "full-catalog-v1"):
        if len(protocol.raw_item_ids) != len(protocol.candidate_item_ids):
            raise ValueError("protocol raw IDs and candidate IDs must have equal length")
        self.protocol = protocol
        self.evaluator_version = evaluator_version

    def evaluate(self, scorer: ScoreProvider, *, run_id: str, model_id: str) -> EvaluationResult:
        user_ids = self.protocol.eligible_user_ids
        if not user_ids:
            raise ScoreError("protocol has no eligible users")
        candidates = self.protocol.candidate_item_ids
        candidate_position = {item_id: index for index, item_id in enumerate(candidates)}
        rows: list[UserMetrics] = []
        top_k_by_user: dict[int, tuple[int, ...]] = {}
        for user_id in user_ids:
            raw_scores = scorer(user_id, candidates)
            masked_scores = self.protocol.mask_scores(user_id, raw_scores)
            case = self.protocol.case_for(user_id)
            try:
                positive_positions = {candidate_position[item] for item in case.positive_item_ids}
                seen_positions = {candidate_position[item] for item in case.history_item_ids}
            except KeyError as error:
                raise ScoreError("protocol case references an unknown candidate") from error
            negative_positions = set(range(len(candidates))) - positive_positions - seen_positions
            user_row = ranking_metrics(
                scores=masked_scores,
                positive_indices=positive_positions,
                negative_indices=negative_positions,
                raw_item_ids=np.asarray(self.protocol.raw_item_ids),
                k=self.protocol.manifest.cutoff,
            )
            rows.append(user_row)
            top_k_by_user[user_id] = tuple(candidates[index] for index in user_row.ranked_indices)

        cutoff = self.protocol.manifest.cutoff
        aggregates = aggregate_user_metrics_at_k(rows, cutoff=cutoff)
        user_ids_tuple = tuple(user_ids)
        per_user = {
            f"HR@{cutoff}": tuple(row.hit_rate for row in rows),
            f"NDCG@{cutoff}": tuple(row.ndcg for row in rows),
            "GAUC": tuple(row.gauc for row in rows),
        }
        denominators = {
            f"HR@{cutoff}": len(rows),
            f"NDCG@{cutoff}": len(rows),
            "GAUC": sum(row.gauc is not None for row in rows),
        }
        receipt = EvaluationReceipt(
            run_id=run_id,
            model_id=model_id,
            protocol_id=self.protocol.manifest.protocol_id,
            evaluator_version=self.evaluator_version,
            per_user_metrics_sha256=_per_user_hash(user_ids_tuple, rows, cutoff),
            num_total_users=self.protocol.num_total_users,
            num_eligible_users=len(rows),
            candidate_count=len(candidates),
            cutoff=self.protocol.manifest.cutoff,
            aggregate_metrics=aggregates,
            denominator_by_metric=denominators,
            verdict="PASS",
        )
        return EvaluationResult(
            receipt=receipt,
            user_ids=user_ids_tuple,
            per_user_metrics=per_user,
            top_k_by_user=top_k_by_user,
        )


__all__ = [
    "EvaluationResult",
    "FullCatalogEvaluator",
    "ScoreProvider",
    "per_user_metrics_mapping",
    "per_user_metrics_sha256",
]
