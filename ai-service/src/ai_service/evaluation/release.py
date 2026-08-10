"""Aggregate three locked finalist seeds before any serving export is authorized."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ai_service.config import Settings
from ai_service.contracts import RunStatus
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.metrics import paired_bootstrap_delta
from ai_service.training.run import RunLifecycle


def _atomic_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            json.dump(document, destination, indent=2, sort_keys=True)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def aggregate_three_seed_release(
    settings: Settings,
    run_dirs: tuple[Path, Path, Path],
) -> dict[str, Any]:
    if len({path.resolve() for path in run_dirs}) != 3:
        raise DataIntegrityError("release gate requires three distinct runs")
    records: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        lifecycle = RunLifecycle.load(run_dir)
        if lifecycle.status is not RunStatus.EVALUATED:
            raise DataIntegrityError(f"run is not evaluated: {run_dir.name}")
        resolved = json.loads((run_dir / "resolved-config.json").read_text(encoding="utf-8"))
        report = json.loads((run_dir / "evaluation" / "report.json").read_text(encoding="utf-8"))
        metrics = np.load(run_dir / "evaluation" / "per-user-metrics.npz")
        state = json.loads((run_dir / "pipeline-state.json").read_text(encoding="utf-8"))
        checkpoint_manifest = json.loads(
            Path(state["checkpoint_path"])
            .with_suffix(".pt.manifest.json")
            .read_text(encoding="utf-8")
        )
        records.append(
            {
                "run_dir": run_dir,
                "lifecycle": lifecycle,
                "seed": int(resolved["train"]["seed"]),
                "experiment_signature": lifecycle.document["experiment_signature_sha256"],
                "lineage": lifecycle.document["lineage"],
                "report": report["results"],
                "metrics": metrics,
                "best_val_ndcg": float(checkpoint_manifest["best_val_ndcg_at_k"]),
            }
        )
    if {record["seed"] for record in records} != {42, 2027, 31415}:
        raise DataIntegrityError("finalist seeds must be exactly 42, 2027, and 31415")
    signatures = {record["experiment_signature"] for record in records}
    lineages = {json.dumps(record["lineage"], sort_keys=True) for record in records}
    if len(signatures) != 1 or len(lineages) != 1:
        raise ArtifactIntegrityError(
            "three-seed runs do not share experiment semantics and lineage"
        )
    if any(not bool(record["report"]["passed"]) for record in records):
        raise DataIntegrityError("at least one seed failed its individual evaluation gates")
    user_ids = [record["metrics"]["user_ids"] for record in records]
    if any(not np.array_equal(user_ids[0], values) for values in user_ids[1:]):
        raise DataIntegrityError("three-seed reports do not contain identical eligible users")

    hybrid = {
        metric: np.stack([record["metrics"][f"hybrid_{metric}"] for record in records])
        for metric in ("hr", "ndcg", "gauc")
    }
    baselines = {
        name: {
            metric: np.stack([record["metrics"][f"{name}_{metric}"] for record in records])
            for metric in ("hr", "ndcg", "gauc")
        }
        for name in ("deep", "wide", "item_cf")
    }
    strongest_name = max(
        baselines,
        key=lambda name: float(baselines[name]["ndcg"].mean()),
    )
    mean_hybrid = {metric: values.mean(axis=0) for metric, values in hybrid.items()}
    mean_baselines = {
        name: {metric: values.mean(axis=0) for metric, values in metrics.items()}
        for name, metrics in baselines.items()
    }
    intervals: dict[str, dict[str, Any]] = {}
    passed = True
    for name, baseline in mean_baselines.items():
        metric_intervals = {
            metric: paired_bootstrap_delta(
                mean_hybrid[metric],
                baseline[metric],
                samples=settings.eval.bootstrap_samples,
                seed=settings.train.seed,
            )
            for metric in ("hr", "ndcg", "gauc")
        }
        gauc_margin = -0.010 if name == "item_cf" else -0.002
        gate = (
            metric_intervals["gauc"].lower >= gauc_margin and metric_intervals["hr"].lower >= -0.001
        )
        if name != "item_cf":
            gate &= metric_intervals["ndcg"].lower >= -0.001
        intervals[name] = {
            "passed": gate,
            **{metric: asdict(value) for metric, value in metric_intervals.items()},
        }
        passed &= gate
    strongest_mean = float(mean_baselines[strongest_name]["ndcg"].mean())
    hybrid_mean = float(mean_hybrid["ndcg"].mean())
    strongest_delta = paired_bootstrap_delta(
        mean_hybrid["ndcg"],
        mean_baselines[strongest_name]["ndcg"],
        samples=settings.eval.bootstrap_samples,
        seed=settings.train.seed,
    )
    ndcg_seed_means = np.asarray(
        [float(record["metrics"]["hybrid_ndcg"].mean()) for record in records]
    )
    coefficient_of_variation = float(
        ndcg_seed_means.std(ddof=0) / max(ndcg_seed_means.mean(), np.finfo(float).eps)
    )
    final_gate = (
        passed
        and hybrid_mean >= strongest_mean * 1.05
        and strongest_delta.lower > 0
        and coefficient_of_variation < 0.10
    )
    if not final_gate:
        raise DataIntegrityError("aggregate three-seed release gates failed")
    selected = max(records, key=lambda record: (record["best_val_ndcg"], -record["seed"]))
    experiment_signature = str(next(iter(signatures)))
    document = {
        "schema_version": "1.0.0",
        "passed": True,
        "experiment_signature_sha256": experiment_signature,
        "run_ids": [record["run_dir"].name for record in records],
        "seeds": sorted(record["seed"] for record in records),
        "selected_run_id": selected["run_dir"].name,
        "selection_policy": "highest validation NDCG; seed ascending tie-break",
        "hybrid_ndcg_mean": hybrid_mean,
        "strongest_baseline": strongest_name,
        "strongest_baseline_ndcg_mean": strongest_mean,
        "strongest_ndcg_delta_ci": asdict(strongest_delta),
        "ndcg_seed_means": ndcg_seed_means.tolist(),
        "ndcg_coefficient_of_variation": coefficient_of_variation,
        "guardrail_intervals": intervals,
    }
    release_path = (
        settings.data.artifact_root.resolve()
        / "releases"
        / experiment_signature
        / "release-gate.json"
    )
    if release_path.exists():
        raise ArtifactIntegrityError(f"immutable release gate already exists: {release_path}")
    _atomic_json(release_path, document)
    for record in records:
        record["lifecycle"].transition(RunStatus.SEALED)
    return document
