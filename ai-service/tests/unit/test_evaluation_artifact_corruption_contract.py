from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from ai_service.contracts import SplitName
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation.report import (
    METRIC_KEYS,
    load_evaluation_artifacts,
    publish_evaluation_artifacts,
)
from tests.support.v5_factories import make_settings, make_victory_matrix


def _metrics() -> dict[str, np.ndarray]:
    users = np.arange(1, 5, dtype=np.int64)
    scalar = np.full(4, 0.5, dtype=np.float64)
    return {
        "user_ids": users,
        **{
            name: np.tile(scalar, (10, 1)) if name.startswith("random_") else scalar.copy()
            for name in METRIC_KEYS
            if name != "user_ids"
        },
    }


def _publish(tmp_path: Path) -> Path:
    settings = make_settings(tmp_path)
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    return publish_evaluation_artifacts(
        run_dir=tmp_path / "run",
        split=SplitName.VAL,
        hybrid_run_id="hybrid-corruption",
        deep_run_id="deep-corruption",
        hybrid_checkpoint_sha256="d" * 64,
        deep_checkpoint_sha256="e" * 64,
        lineage=lineage,
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        metrics=_metrics(),
        results={"fixture": True},
        victory_matrix=matrix,
    ).directory


def _load(directory: Path, tmp_path: Path) -> object:
    settings = make_settings(tmp_path)
    return load_evaluation_artifacts(
        directory,
        expected_split=SplitName.VAL,
        expected_hybrid_run_id="hybrid-corruption",
        expected_deep_run_id="deep-corruption",
        expected_comparison_signature=settings.comparison_signature_sha256(),
        expected_lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
    )


def test_evaluation_report_parse_error_is_integrity_error(tmp_path: Path) -> None:
    directory = _publish(tmp_path)
    (directory / "report.json").write_text("{", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="report cannot be read"):
        _load(directory, tmp_path)


def test_evaluation_npz_object_dtype_is_rejected_without_pickle(tmp_path: Path) -> None:
    directory = _publish(tmp_path)
    with np.load(directory / "per-user-metrics.npz", allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    arrays["hybrid_hr"] = np.asarray(["bad"] * 4, dtype=object)
    np.savez_compressed(directory / "per-user-metrics.npz", **arrays)

    with pytest.raises(ArtifactIntegrityError, match="metrics hash mismatch"):
        _load(directory, tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("manifest.hybrid_run_id", "", "report cannot be read"),
        ("manifest.comparison_signature_sha256", "x" * 64, "report cannot be read"),
    ],
)
def test_evaluation_manifest_corruption_is_rejected(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    directory = _publish(tmp_path)
    report_path = directory / "report.json"
    document = json.loads(report_path.read_text(encoding="utf-8"))
    cursor = document
    parts = field.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value
    report_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match=message):
        _load(directory, tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "keys mismatch"),
        ("extra", "keys mismatch"),
        ("ids", "user IDs"),
        ("random", r"shape \[10,U\]"),
        ("rank", "invalid rank"),
        ("numeric", "not numeric"),
        ("range", "values are invalid"),
    ],
)
def test_publish_rejects_metric_shape_and_value_corruption(
    tmp_path: Path, mutation: str, message: str
) -> None:
    settings = make_settings(tmp_path)
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    metrics = _metrics()
    if mutation == "missing":
        metrics.pop("hybrid_hr")
    elif mutation == "extra":
        metrics["unexpected"] = np.zeros(4)
    elif mutation == "ids":
        metrics["user_ids"] = np.asarray([1, 1, 2, 3], dtype=np.int64)
    elif mutation == "random":
        metrics["random_hr"] = np.zeros((9, 4))
    elif mutation == "rank":
        metrics["hybrid_hr"] = np.zeros((4, 1))
    elif mutation == "numeric":
        metrics["hybrid_hr"] = np.asarray(["bad"] * 4, dtype=object)
    else:
        metrics["hybrid_hr"] = np.asarray([2.0] * 4)

    with pytest.raises(ArtifactIntegrityError, match=message):
        publish_evaluation_artifacts(
            run_dir=tmp_path / "run",
            split=SplitName.VAL,
            hybrid_run_id="hybrid-corruption",
            deep_run_id="deep-corruption",
            hybrid_checkpoint_sha256="d" * 64,
            deep_checkpoint_sha256="e" * 64,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            metrics=metrics,
            results={},
            victory_matrix=matrix,
        )


def test_evaluation_loader_supports_run_directory_and_rejects_matrix_corruption(
    tmp_path: Path,
) -> None:
    directory = _publish(tmp_path)
    loaded = _load(tmp_path / "run", tmp_path)
    assert loaded.directory == directory  # type: ignore[union-attr]
    (directory / "victory-matrix.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="Victory Matrix cannot be read"):
        _load(directory, tmp_path)


def test_evaluation_manifest_pair_and_property_contracts(tmp_path: Path) -> None:
    directory = _publish(tmp_path)
    loaded = _load(directory, tmp_path)
    assert loaded.victory_matrix_sha256 == loaded.manifest.victory_matrix_sha256  # type: ignore[union-attr]

    settings = make_settings(tmp_path / "same")
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    with pytest.raises(ValueError, match="distinct runs"):
        publish_evaluation_artifacts(
            run_dir=tmp_path / "same" / "run",
            split=SplitName.VAL,
            hybrid_run_id="same",
            deep_run_id="same",
            hybrid_checkpoint_sha256="d" * 64,
            deep_checkpoint_sha256="e" * 64,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            metrics=_metrics(),
            results={},
            victory_matrix=matrix,
        )


def test_evaluation_loader_rejects_mismatched_split_pair_signature_lineage_and_pass_flag(
    tmp_path: Path,
) -> None:
    directory = _publish(tmp_path)
    report_path = directory / "report.json"
    original = json.loads(report_path.read_text(encoding="utf-8"))
    for field, value, message in (
        ("split", "test", "split mismatch"),
        ("hybrid_run_id", "other", "pair mismatch"),
        ("comparison_signature_sha256", "f" * 64, "comparison signature mismatch"),
        ("snapshot_sha256", "f" * 64, "lineage mismatch"),
        ("passed", False, "pass flag"),
    ):
        document = json.loads(json.dumps(original))
        document["manifest"][field] = value
        report_path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(ArtifactIntegrityError, match=message):
            _load(directory, tmp_path)
    report_path.write_text(json.dumps(original), encoding="utf-8")


def test_evaluation_loader_wraps_invalid_metrics_archive_after_hash_check(tmp_path: Path) -> None:
    directory = _publish(tmp_path)
    metrics_path = directory / "per-user-metrics.npz"
    with np.load(metrics_path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    arrays["hybrid_hr"] = np.asarray(["bad"] * 4, dtype=object)
    np.savez_compressed(metrics_path, **arrays)
    digest = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
    report_path = directory / "report.json"
    document = json.loads(report_path.read_text(encoding="utf-8"))
    document["manifest"]["per_user_metrics_sha256"] = digest
    report_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="metrics archive cannot be read"):
        _load(directory, tmp_path)


def test_evaluation_publish_rename_failure_cleans_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    monkeypatch.setattr(
        "ai_service.evaluation.report.os.replace",
        lambda *_: (_ for _ in ()).throw(OSError("rename failed")),
    )
    with pytest.raises(OSError, match="rename failed"):
        publish_evaluation_artifacts(
            run_dir=tmp_path / "run",
            split=SplitName.VAL,
            hybrid_run_id="hybrid-race",
            deep_run_id="deep-race",
            hybrid_checkpoint_sha256="d" * 64,
            deep_checkpoint_sha256="e" * 64,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            metrics=_metrics(),
            results={},
            victory_matrix=matrix,
        )
    assert not (tmp_path / "run" / "evaluation" / "val").exists()
