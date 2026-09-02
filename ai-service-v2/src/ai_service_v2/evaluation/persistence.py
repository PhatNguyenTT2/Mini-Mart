"""Immutable persistence and replay for evaluator outputs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_service_v2.contracts import EvaluationReceipt
from ai_service_v2.errors import IntegrityError
from ai_service_v2.evaluation.evaluator import (
    EvaluationResult,
    evaluator_implementation_sha256,
    per_user_metrics_mapping,
    per_user_metrics_sha256,
)
from ai_service_v2.hashing import canonical_json_bytes, loads_strict_json


@dataclass(frozen=True)
class PersistedEvaluation:
    root: Path
    receipt: EvaluationReceipt
    user_ids: tuple[int, ...]
    per_user_metrics: dict[str, tuple[float | None, ...]]


def _write_new(path: Path, document: dict[str, Any]) -> None:
    if path.exists():
        raise IntegrityError(f"evaluation output already exists: {path}")
    try:
        path.write_bytes(canonical_json_bytes(document) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write evaluation artifact: {path}") from error


def _load_canonical(path: Path) -> dict[str, Any]:
    """Load one receipt document and reject formatting-only mutations."""

    try:
        payload = path.read_bytes()
        document = loads_strict_json(payload, source=str(path))
    except OSError as error:
        raise IntegrityError(f"could not read evaluation artifact: {path}") from error
    if payload != canonical_json_bytes(document) + b"\n":
        raise IntegrityError(f"evaluation artifact canonical hash/bytes mismatch: {path}")
    return document


def save_evaluation(result: EvaluationResult, root: Path) -> PersistedEvaluation:
    """Persist evaluator output without changing its receipt or metrics."""

    if root.exists():
        raise IntegrityError(f"evaluation output already exists: {root}")
    try:
        root.mkdir(parents=True)
    except OSError as error:
        raise IntegrityError(f"could not create evaluation output: {root}") from error

    cutoff = result.receipt.cutoff
    per_user_document = {
        "schema_version": "per-user-metrics/1.0",
        "run_id": result.receipt.run_id,
        "model_id": result.receipt.model_id,
        "protocol_id": result.receipt.protocol_id,
        "protocol_manifest_sha256": result.receipt.protocol_manifest_sha256,
        "candidate_order_sha256": result.receipt.candidate_order_sha256,
        "cutoff": cutoff,
        "user_ids": list(result.user_ids),
        "metrics": per_user_metrics_mapping(result.user_ids, result.per_user_metrics, cutoff)[
            "rows"
        ],
    }
    aggregate_document = {
        "schema_version": "aggregate-metrics/1.0",
        "run_id": result.receipt.run_id,
        "model_id": result.receipt.model_id,
        "protocol_id": result.receipt.protocol_id,
        "protocol_manifest_sha256": result.receipt.protocol_manifest_sha256,
        "candidate_order_sha256": result.receipt.candidate_order_sha256,
        "aggregate_metrics": result.receipt.aggregate_metrics,
        "denominator_by_metric": result.receipt.denominator_by_metric,
    }
    receipt_document = {
        "schema_version": "evaluation-receipt/1.1",
        "receipt": result.receipt.to_mapping(),
        "per_user_metrics_file": "per_user_metrics.json",
        "aggregate_metrics_file": "aggregate_metrics.json",
    }
    _write_new(root / "per_user_metrics.json", per_user_document)
    _write_new(root / "aggregate_metrics.json", aggregate_document)
    _write_new(root / "evaluation_receipt.json", receipt_document)
    return PersistedEvaluation(root, result.receipt, result.user_ids, result.per_user_metrics)


def load_evaluation(root: Path) -> PersistedEvaluation:
    """Load an evaluation bundle and verify all logical and byte bindings."""

    expected_files = {
        "per_user_metrics.json",
        "aggregate_metrics.json",
        "evaluation_receipt.json",
    }
    try:
        actual_files = {path.name for path in root.iterdir() if path.is_file()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect evaluation root: {root}") from error
    if actual_files != expected_files:
        raise IntegrityError("evaluation bundle contains an unexpected or missing file")
    receipt_document = _load_canonical(root / "evaluation_receipt.json")
    if set(receipt_document) != {
        "schema_version",
        "receipt",
        "per_user_metrics_file",
        "aggregate_metrics_file",
    }:
        raise IntegrityError("evaluation receipt wrapper fields do not match schema")
    if (
        receipt_document["schema_version"] != "evaluation-receipt/1.1"
        or receipt_document["per_user_metrics_file"] != "per_user_metrics.json"
        or receipt_document["aggregate_metrics_file"] != "aggregate_metrics.json"
        or not isinstance(receipt_document["receipt"], dict)
    ):
        raise IntegrityError("evaluation receipt wrapper is invalid")
    receipt = EvaluationReceipt.from_mapping(receipt_document["receipt"])
    if receipt.evaluator_implementation_sha256 != evaluator_implementation_sha256():
        raise IntegrityError("evaluation receipt binds a different evaluator implementation")
    per_user_document = _load_canonical(root / "per_user_metrics.json")
    if set(per_user_document) != {
        "schema_version",
        "run_id",
        "model_id",
        "protocol_id",
        "protocol_manifest_sha256",
        "candidate_order_sha256",
        "cutoff",
        "user_ids",
        "metrics",
    }:
        raise IntegrityError("per-user metric document fields do not match schema")
    if per_user_document["schema_version"] != "per-user-metrics/1.0":
        raise IntegrityError("unsupported per-user metric schema")
    if (
        per_user_document["run_id"] != receipt.run_id
        or per_user_document["model_id"] != receipt.model_id
        or per_user_document["protocol_id"] != receipt.protocol_id
        or per_user_document["protocol_manifest_sha256"] != receipt.protocol_manifest_sha256
        or per_user_document["candidate_order_sha256"] != receipt.candidate_order_sha256
        or per_user_document["cutoff"] != receipt.cutoff
    ):
        raise IntegrityError("per-user metric identity does not match receipt")
    user_ids = per_user_document["user_ids"]
    rows = per_user_document["metrics"]
    if (
        not isinstance(user_ids, list)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in user_ids)
        or tuple(user_ids) != tuple(sorted(user_ids))
        or len(set(user_ids)) != len(user_ids)
        or not isinstance(rows, list)
        or len(rows) != len(user_ids)
    ):
        raise IntegrityError("per-user metric user order is invalid")
    if len(user_ids) != receipt.num_eligible_users:
        raise IntegrityError("receipt eligible user count does not match per-user rows")
    cutoff = receipt.cutoff
    metric_keys = {f"HR@{cutoff}", f"NDCG@{cutoff}", "GAUC"}
    parsed: dict[str, list[float | None]] = {key: [] for key in metric_keys}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"user_id", *metric_keys}:
            raise IntegrityError("per-user metric row fields do not match schema")
        if row["user_id"] != user_ids[index]:
            raise IntegrityError("per-user metric rows are out of order")
        for key in metric_keys:
            value = row[key]
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise IntegrityError(f"invalid per-user metric value: {key}")
            if value is not None and not math.isfinite(float(value)):
                raise IntegrityError(f"non-finite per-user metric value: {key}")
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise IntegrityError(f"per-user metric value is outside [0, 1]: {key}")
            parsed[key].append(None if value is None else float(value))
    per_user = {key: tuple(values) for key, values in parsed.items()}
    if (
        per_user_metrics_sha256(tuple(user_ids), per_user, cutoff)
        != receipt.per_user_metrics_sha256
    ):
        raise IntegrityError("per-user metric hash does not match receipt")

    expected_denominators = {
        f"HR@{cutoff}": len(user_ids),
        f"NDCG@{cutoff}": len(user_ids),
        "GAUC": sum(value is not None for value in per_user["GAUC"]),
    }
    if receipt.denominator_by_metric != expected_denominators:
        raise IntegrityError("receipt denominators do not match per-user rows")
    expected_aggregates: dict[str, float | None] = {}
    for key, values in per_user.items():
        defined = [value for value in values if value is not None]
        expected_aggregates[key] = float(sum(defined) / len(defined)) if defined else None
    for key, expected in expected_aggregates.items():
        actual = receipt.aggregate_metrics[key]
        if expected is None:
            if actual is not None:
                raise IntegrityError(f"receipt aggregate is defined for empty metric: {key}")
        elif actual is None or not math.isclose(
            float(actual), expected, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise IntegrityError(f"receipt aggregate does not match per-user rows: {key}")

    aggregate_document = _load_canonical(root / "aggregate_metrics.json")
    if set(aggregate_document) != {
        "schema_version",
        "run_id",
        "model_id",
        "protocol_id",
        "protocol_manifest_sha256",
        "candidate_order_sha256",
        "aggregate_metrics",
        "denominator_by_metric",
    }:
        raise IntegrityError("aggregate metric document fields do not match schema")
    if aggregate_document["schema_version"] != "aggregate-metrics/1.0":
        raise IntegrityError("unsupported aggregate metric schema")
    if (
        aggregate_document["run_id"] != receipt.run_id
        or aggregate_document["model_id"] != receipt.model_id
        or aggregate_document["protocol_id"] != receipt.protocol_id
        or aggregate_document["protocol_manifest_sha256"] != receipt.protocol_manifest_sha256
        or aggregate_document["candidate_order_sha256"] != receipt.candidate_order_sha256
        or aggregate_document["aggregate_metrics"] != receipt.aggregate_metrics
        or aggregate_document["denominator_by_metric"] != receipt.denominator_by_metric
    ):
        raise IntegrityError("aggregate metrics do not match receipt")
    return PersistedEvaluation(root, receipt, tuple(user_ids), per_user)


__all__ = ["PersistedEvaluation", "load_evaluation", "save_evaluation"]
