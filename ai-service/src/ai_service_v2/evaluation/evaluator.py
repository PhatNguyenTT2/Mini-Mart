"""Independent full-catalog evaluator for every model and adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from ai_service_v2.array_types import Array
from ai_service_v2.contracts import EvaluationReceipt
from ai_service_v2.errors import ScoreError
from ai_service_v2.evaluation.metrics import (
    UserMetrics,
    aggregate_user_metrics_at_k,
    ranking_metrics,
)
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_bytes,
    sha256_file,
)
from ai_service_v2.protocol import EvaluationProtocol

if TYPE_CHECKING:
    from ai_service_v2.evaluation.artifacts import MaterializedScores, ScoreBatch

ScoreProvider = Callable[[int, tuple[int, ...]], Array]
"""Small seam: a model emits one score vector in frozen catalog order."""


_EVALUATOR_SOURCE_FILES = (
    "evaluation/evaluator.py",
    "evaluation/metrics.py",
    "protocol.py",
)


def evaluator_source_hashes() -> dict[str, str]:
    """Return hashes for the source files that define evaluation semantics."""

    package_root = Path(__file__).resolve().parents[1]
    hashes: dict[str, str] = {}
    for relative_path in _EVALUATOR_SOURCE_FILES:
        path = package_root / relative_path
        if not path.is_file():
            raise ScoreError(f"evaluator source file is missing: {relative_path}")
        hashes[relative_path] = sha256_file(path)
    return hashes


def evaluator_implementation_sha256() -> str:
    """Hash the exact evaluator/metric/protocol source bundle in use.

    The source manifest is deliberately small and explicit.  It gives every
    persisted metric receipt a stable implementation identity without hashing
    the receipt itself or depending on an absolute checkout path.
    """

    return canonical_json_sha256(
        {
            "schema_version": "evaluator-implementation/1.0",
            "files": evaluator_source_hashes(),
        }
    )


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

    def __init__(
        self,
        protocol: EvaluationProtocol,
        *,
        evaluator_version: str = "full-catalog-v1",
    ):
        if len(protocol.raw_item_ids) != len(protocol.candidate_item_ids):
            raise ValueError("protocol raw IDs and candidate IDs must have equal length")
        self.protocol = protocol
        self.evaluator_version = evaluator_version
        self.evaluator_implementation_sha256 = evaluator_implementation_sha256()

    def evaluate(self, scorer: ScoreProvider, *, run_id: str, model_id: str) -> EvaluationResult:
        candidates = self.protocol.candidate_item_ids
        return self._evaluate_rows(
            ((user_id, scorer(user_id, candidates)) for user_id in self.protocol.eligible_user_ids),
            run_id=run_id,
            model_id=model_id,
        )

    def evaluate_artifact(self, materialized: MaterializedScores) -> EvaluationResult:
        """Evaluate a bound score artifact while holding only one chunk in memory."""

        from ai_service_v2.evaluation.artifacts import iter_score_batches

        protocol_sha256 = canonical_json_sha256(self.protocol.manifest.to_mapping())
        if materialized.manifest.protocol_manifest_sha256 != protocol_sha256:
            raise ScoreError("score artifact protocol does not match evaluator protocol")
        if (
            materialized.manifest.candidate_order_sha256
            != self.protocol.manifest.candidate_order_sha256
        ):
            raise ScoreError("score artifact candidate order does not match evaluator protocol")
        if not materialized.manifest.finite:
            raise ScoreError("score artifact declares non-finite values")

        return self.evaluate_batches(
            iter_score_batches(
                materialized,
                self.protocol.eligible_user_ids,
                self.protocol.candidate_item_ids,
            ),
            run_id=materialized.manifest.run_id,
            model_id=materialized.manifest.model_id,
        )

    def evaluate_batches(
        self,
        batches: Iterable[ScoreBatch],
        *,
        run_id: str,
        model_id: str,
        on_batch_evaluated: Callable[[ScoreBatch, tuple[UserMetrics, ...]], None] | None = None,
    ) -> EvaluationResult:
        """Evaluate verified score batches in the frozen protocol order.

        The evaluator validates each transient batch before applying masking and
        ranking. The callback runs only after every row in that batch has
        produced a metric row, allowing custody before transient cleanup.
        """

        from ai_service_v2.evaluation.artifacts import ScoreBatch as RuntimeScoreBatch

        user_ids = self.protocol.eligible_user_ids
        if not user_ids:
            raise ScoreError("protocol has no eligible users")
        candidates = self.protocol.candidate_item_ids
        candidate_position = {item_id: index for index, item_id in enumerate(candidates)}
        rows: list[UserMetrics] = []
        top_k_by_user: dict[int, tuple[int, ...]] = {}
        expected_first = 0
        for batch in batches:
            if not isinstance(batch, RuntimeScoreBatch):
                raise ScoreError("score batch has an invalid type")
            expected_users = user_ids[expected_first : expected_first + len(batch.user_ids)]
            scores = np.asarray(batch.scores)
            if batch.first_user_index != expected_first:
                raise ScoreError("score batches have a gap or overlap in user order")
            if not batch.user_ids or tuple(batch.user_ids) != expected_users:
                raise ScoreError("score batch user order differs from frozen protocol")
            if scores.dtype != np.float32 or scores.shape != (
                len(batch.user_ids),
                len(candidates),
            ):
                raise ScoreError("score batch has an invalid shape or dtype")
            if not np.isfinite(scores).all():
                raise ScoreError("score batch contains non-finite values")
            batch_rows: list[UserMetrics] = []
            for row_index, user_id in enumerate(batch.user_ids):
                user_row, top_k = self._evaluate_user_row(
                    user_id,
                    scores[row_index],
                    candidate_position,
                )
                batch_rows.append(user_row)
                rows.append(user_row)
                top_k_by_user[user_id] = top_k
            if on_batch_evaluated is not None:
                on_batch_evaluated(batch, tuple(batch_rows))
            expected_first += len(batch.user_ids)
        if expected_first != len(user_ids):
            raise ScoreError("score batches do not cover every eligible user")
        return self._build_result(
            rows,
            top_k_by_user,
            run_id=run_id,
            model_id=model_id,
        )

    def _evaluate_rows(
        self,
        score_rows: Iterable[tuple[int, Array]],
        *,
        run_id: str,
        model_id: str,
    ) -> EvaluationResult:
        user_ids = self.protocol.eligible_user_ids
        if not user_ids:
            raise ScoreError("protocol has no eligible users")
        candidates = self.protocol.candidate_item_ids
        candidate_position = {item_id: index for index, item_id in enumerate(candidates)}
        rows: list[UserMetrics] = []
        top_k_by_user: dict[int, tuple[int, ...]] = {}
        observed_user_ids: list[int] = []
        for user_id, raw_scores in score_rows:
            expected_index = len(observed_user_ids)
            if expected_index >= len(user_ids) or user_id != user_ids[expected_index]:
                raise ScoreError("score rows do not follow the frozen user order")
            observed_user_ids.append(user_id)
            user_row, top_k = self._evaluate_user_row(
                user_id,
                raw_scores,
                candidate_position,
            )
            rows.append(user_row)
            top_k_by_user[user_id] = top_k
        if tuple(observed_user_ids) != user_ids:
            raise ScoreError("score rows do not cover every eligible user")

        return self._build_result(rows, top_k_by_user, run_id=run_id, model_id=model_id)

    def _evaluate_user_row(
        self,
        user_id: int,
        raw_scores: Array,
        candidate_position: dict[int, int],
    ) -> tuple[UserMetrics, tuple[int, ...]]:
        candidates = self.protocol.candidate_item_ids
        scores = np.asarray(raw_scores)
        if scores.shape != (len(candidates),):
            raise ScoreError("score vector has the wrong shape")
        if not np.isfinite(scores).all():
            raise ScoreError("score vector contains non-finite values")
        masked_scores = self.protocol.mask_scores(user_id, scores)
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
            excluded_indices=seen_positions,
            raw_item_ids=np.asarray(self.protocol.raw_item_ids),
            k=self.protocol.manifest.cutoff,
        )
        return user_row, tuple(candidates[index] for index in user_row.ranked_indices)

    def _build_result(
        self,
        rows: list[UserMetrics],
        top_k_by_user: dict[int, tuple[int, ...]],
        *,
        run_id: str,
        model_id: str,
    ) -> EvaluationResult:
        if not rows:
            raise ScoreError("protocol has no evaluated users")

        cutoff = self.protocol.manifest.cutoff
        aggregates = aggregate_user_metrics_at_k(rows, cutoff=cutoff)
        user_ids_tuple = self.protocol.eligible_user_ids
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
            protocol_manifest_sha256=canonical_json_sha256(self.protocol.manifest.to_mapping()),
            candidate_order_sha256=self.protocol.manifest.candidate_order_sha256,
            evaluator_version=self.evaluator_version,
            evaluator_implementation_sha256=self.evaluator_implementation_sha256,
            per_user_metrics_sha256=_per_user_hash(user_ids_tuple, rows, cutoff),
            num_total_users=self.protocol.num_total_users,
            num_eligible_users=len(rows),
            candidate_count=len(self.protocol.candidate_item_ids),
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
    "evaluator_implementation_sha256",
    "evaluator_source_hashes",
    "per_user_metrics_mapping",
    "per_user_metrics_sha256",
]
