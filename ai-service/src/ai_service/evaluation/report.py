"""Immutable paired-evaluation artifacts with verified lineage and schemas."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, model_validator

from ai_service.contracts import EVALUATION_SCHEMA_VERSION, SplitName, VictoryMatrix
from ai_service.errors import ArtifactIntegrityError

METRIC_KEYS = (
    "user_ids",
    "hybrid_hr",
    "hybrid_ndcg",
    "hybrid_gauc",
    "deep_hr",
    "deep_ndcg",
    "deep_gauc",
    "apriori_hr",
    "apriori_ndcg",
    "apriori_gauc",
    "sbert_hr",
    "sbert_ndcg",
    "sbert_gauc",
    "item_cf_hr",
    "item_cf_ndcg",
    "item_cf_gauc",
    "persona_hr",
    "persona_ndcg",
    "persona_gauc",
    "noisy_hybrid_hr",
    "noisy_hybrid_ndcg",
    "noisy_hybrid_gauc",
    "random_hr",
    "random_ndcg",
    "random_gauc",
)


class EvaluationArtifactManifest(BaseModel):
    schema_version: Literal["5.2.0"]
    split: SplitName
    hybrid_run_id: str
    deep_run_id: str
    hybrid_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deep_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    comparison_signature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool
    per_user_metrics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    victory_matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def pair_is_distinct(self) -> EvaluationArtifactManifest:
        if not self.hybrid_run_id.strip() or not self.deep_run_id.strip():
            raise ValueError("evaluation run IDs cannot be empty")
        if self.hybrid_run_id == self.deep_run_id:
            raise ValueError("evaluation pair must contain distinct runs")
        return self


@dataclass(frozen=True)
class EvaluationArtifactSet:
    directory: Path
    manifest: EvaluationArtifactManifest
    victory_matrix: VictoryMatrix
    metrics: dict[str, np.ndarray]
    report_path: Path
    metrics_path: Path
    victory_matrix_path: Path

    @property
    def victory_matrix_sha256(self) -> str:
        return self.manifest.victory_matrix_sha256


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_victory_matrix_sha(matrix: VictoryMatrix) -> str:
    document = matrix.model_dump(mode="json")
    document.pop("sha256", None)
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_metrics(metrics: Mapping[str, object]) -> dict[str, np.ndarray]:
    if set(metrics) != set(METRIC_KEYS):
        missing = sorted(set(METRIC_KEYS) - set(metrics))
        extra = sorted(set(metrics) - set(METRIC_KEYS))
        raise ArtifactIntegrityError(
            f"evaluation metrics keys mismatch; missing={missing}, extra={extra}"
        )
    try:
        arrays = {name: np.asarray(metrics[name]) for name in METRIC_KEYS}
        user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ArtifactIntegrityError("evaluation metrics cannot be converted to arrays") from error
    if (
        arrays["user_ids"].dtype != np.int64
        or user_ids.ndim != 1
        or not len(user_ids)
        or np.any(user_ids <= 0)
        or np.any(np.diff(user_ids) <= 0)
    ):
        raise ArtifactIntegrityError("evaluation user IDs must be sorted unique positive int64")
    users = len(user_ids)
    for name, array in arrays.items():
        if name == "user_ids":
            continue
        if array.ndim != (2 if name.startswith("random_") else 1):
            raise ArtifactIntegrityError(f"evaluation metric has invalid rank: {name}")
        if name.startswith("random_"):
            if array.shape != (10, users):
                raise ArtifactIntegrityError(f"random metric must have shape [10,U]: {name}")
        elif array.shape != (users,):
            raise ArtifactIntegrityError(f"evaluation metric user dimension mismatch: {name}")
        try:
            normalized = np.asarray(array, dtype=np.float64)
        except (TypeError, ValueError, OverflowError) as error:
            raise ArtifactIntegrityError(f"evaluation metric is not numeric: {name}") from error
        if not np.isfinite(normalized).all() or np.any(normalized < 0) or np.any(normalized > 1):
            raise ArtifactIntegrityError(f"evaluation metric values are invalid: {name}")
        arrays[name] = normalized
    arrays["user_ids"] = user_ids
    return arrays


def publish_evaluation_artifacts(
    *,
    run_dir: Path,
    split: SplitName,
    hybrid_run_id: str,
    deep_run_id: str,
    hybrid_checkpoint_sha256: str,
    deep_checkpoint_sha256: str,
    lineage: dict[str, str],
    comparison_signature_sha256: str,
    metrics: Mapping[str, object],
    results: Mapping[str, object],
    victory_matrix: VictoryMatrix,
) -> EvaluationArtifactSet:
    if set(lineage) != {"snapshot", "embedding", "rules"}:
        raise ArtifactIntegrityError("evaluation lineage requires snapshot, embedding, and rules")
    if any(not isinstance(value, str) or len(value) != 64 for value in lineage.values()):
        raise ArtifactIntegrityError("evaluation lineage contains an invalid SHA")
    if victory_matrix.comparison_signature != comparison_signature_sha256:
        raise ArtifactIntegrityError("Victory Matrix comparison signature mismatch")
    if canonical_victory_matrix_sha(victory_matrix) != victory_matrix.sha256:
        raise ArtifactIntegrityError("Victory Matrix canonical SHA is invalid")
    arrays = _validate_metrics(metrics)
    root = run_dir / "evaluation"
    root.mkdir(parents=True, exist_ok=True)
    destination = root / split.value
    if destination.exists():
        raise ArtifactIntegrityError(f"evaluation artifact already exists: {destination}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{split.value}-", dir=root))
    try:
        metrics_path = temporary / "per-user-metrics.npz"
        np.savez_compressed(metrics_path, **arrays)  # type: ignore[arg-type]
        matrix_path = temporary / "victory-matrix.json"
        matrix_path.write_text(
            json.dumps(victory_matrix.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        manifest = EvaluationArtifactManifest(
            schema_version=EVALUATION_SCHEMA_VERSION,
            split=split,
            hybrid_run_id=hybrid_run_id,
            deep_run_id=deep_run_id,
            hybrid_checkpoint_sha256=hybrid_checkpoint_sha256,
            deep_checkpoint_sha256=deep_checkpoint_sha256,
            snapshot_sha256=lineage["snapshot"],
            embedding_sha256=lineage["embedding"],
            rule_sha256=lineage["rules"],
            comparison_signature_sha256=comparison_signature_sha256,
            passed=victory_matrix.all_passed,
            per_user_metrics_sha256=_file_sha256(metrics_path),
            victory_matrix_sha256=victory_matrix.sha256,
        )
        report_path = temporary / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "manifest": manifest.model_dump(mode="json"),
                    "results": dict(results),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        for path in (metrics_path, matrix_path, report_path):
            with path.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        # Verify the temporary directory before publishing it.
        load_evaluation_artifacts(
            temporary,
            expected_split=split,
            expected_hybrid_run_id=hybrid_run_id,
            expected_deep_run_id=deep_run_id,
            expected_comparison_signature=comparison_signature_sha256,
            expected_lineage=lineage,
        )
        if destination.exists():
            raise ArtifactIntegrityError(f"evaluation artifact already exists: {destination}")
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return load_evaluation_artifacts(
        destination,
        expected_split=split,
        expected_hybrid_run_id=hybrid_run_id,
        expected_deep_run_id=deep_run_id,
        expected_comparison_signature=comparison_signature_sha256,
        expected_lineage=lineage,
    )


def load_evaluation_artifacts(
    directory_or_run_dir: Path,
    *,
    expected_split: SplitName,
    expected_hybrid_run_id: str,
    expected_deep_run_id: str,
    expected_comparison_signature: str,
    expected_lineage: dict[str, str],
) -> EvaluationArtifactSet:
    directory = directory_or_run_dir
    if not (directory / "report.json").is_file():
        directory = directory_or_run_dir / "evaluation" / expected_split.value
    report_path = directory / "report.json"
    metrics_path = directory / "per-user-metrics.npz"
    matrix_path = directory / "victory-matrix.json"
    if not all(path.is_file() for path in (report_path, metrics_path, matrix_path)):
        raise ArtifactIntegrityError("evaluation artifact set is incomplete")
    manifest, _ = _load_report(report_path)
    if manifest.split is not expected_split:
        raise ArtifactIntegrityError("evaluation split mismatch")
    if (
        manifest.hybrid_run_id != expected_hybrid_run_id
        or manifest.deep_run_id != expected_deep_run_id
    ):
        raise ArtifactIntegrityError("evaluation pair mismatch")
    if manifest.comparison_signature_sha256 != expected_comparison_signature:
        raise ArtifactIntegrityError("evaluation comparison signature mismatch")
    actual_lineage = {
        "snapshot": manifest.snapshot_sha256,
        "embedding": manifest.embedding_sha256,
        "rules": manifest.rule_sha256,
    }
    if actual_lineage != expected_lineage:
        raise ArtifactIntegrityError("evaluation lineage mismatch")
    matrix = _load_matrix(matrix_path)
    if (
        matrix.sha256 != manifest.victory_matrix_sha256
        or canonical_victory_matrix_sha(matrix) != matrix.sha256
    ):
        raise ArtifactIntegrityError("evaluation Victory Matrix hash mismatch")
    if manifest.passed != matrix.all_passed:
        raise ArtifactIntegrityError("evaluation manifest pass flag disagrees with matrix")
    if _file_sha256(metrics_path) != manifest.per_user_metrics_sha256:
        raise ArtifactIntegrityError("evaluation metrics hash mismatch")
    arrays = _load_metric_archive(metrics_path)
    return EvaluationArtifactSet(
        directory=directory,
        manifest=manifest,
        victory_matrix=matrix,
        metrics=arrays,
        report_path=report_path,
        metrics_path=metrics_path,
        victory_matrix_path=matrix_path,
    )


def _load_report(path: Path) -> tuple[EvaluationArtifactManifest, dict[str, object]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("report root must be an object")
        manifest = EvaluationArtifactManifest.model_validate(document.get("manifest", {}))
        results = document.get("results", {})
        if not isinstance(results, dict):
            raise ValueError("report results must be an object")
        return manifest, results
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError("evaluation report cannot be read") from error


def _load_matrix(path: Path) -> VictoryMatrix:
    try:
        return VictoryMatrix.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError("evaluation Victory Matrix cannot be read") from error


def _load_metric_archive(path: Path) -> dict[str, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            return _validate_metrics({name: archive[name] for name in archive.files})
    except (OSError, TypeError, ValueError, KeyError) as error:
        raise ArtifactIntegrityError("evaluation metrics archive cannot be read") from error


__all__ = [
    "METRIC_KEYS",
    "EvaluationArtifactManifest",
    "EvaluationArtifactSet",
    "canonical_victory_matrix_sha",
    "load_evaluation_artifacts",
    "publish_evaluation_artifacts",
]
