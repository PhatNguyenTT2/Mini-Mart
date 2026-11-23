"""Shared configuration and helpers for the pipeline stages.

Every stage takes ``--config <file.json>``. Relative paths in the config are resolved against the
config file's directory. See ``configs/pipeline.example.json``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from hybrid_recsys.data.io import load_canonical_snapshot
from hybrid_recsys.data.snapshot import Interaction, Snapshot
from hybrid_recsys.training.inputs import FeatureIdentity, PipelineInputs, load_pipeline_inputs

METRICS = ("NDCG@10", "HR@10", "GAUC")


@dataclass(frozen=True)
class PipelineConfig:
    snapshot_root: Path
    feature_root: Path
    rules_root: Path
    work_root: Path
    dataset_id: str | None = None
    feature_identity: FeatureIdentity = field(default_factory=FeatureIdentity)
    seeds: tuple[int, ...] = (42, 2027, 31415)
    lambda_grid: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0)
    wd_lr_grid: tuple[float, ...] = (0.001, 0.01)
    deep_epochs: int = 16
    wd_max_epochs: int = 50
    wd_patience: int = 10
    reference_max_epochs: int = 100
    reference_patience: int = 20
    itemknn_k: int = 20
    bpr: dict[str, Any] = field(
        default_factory=lambda: {"embedding_size": 64, "learning_rate": 0.005}
    )
    lightgcn: dict[str, Any] = field(
        default_factory=lambda: {"embedding_size": 64, "learning_rate": 0.001, "n_layers": 2}
    )
    cohort_gates: dict[str, int] = field(
        default_factory=lambda: {
            "eligible_users_min": 500,
            "novel_positive_events_min": 1000,
            "distinct_target_items_min": 100,
        }
    )
    bootstrap_replicates: int = 2000
    bootstrap_seed: tuple[int, ...] = (42, 1)
    device: str = "auto"

    # Derived locations under work_root.
    @property
    def validation_root(self) -> Path:
        return self.work_root / "validation"

    @property
    def custody_root(self) -> Path:
        return self.work_root / "custody"

    @property
    def sealed_test(self) -> Path:
        return self.custody_root / "test_source_events.jsonl"

    @property
    def test_root(self) -> Path:
        return self.work_root / "test"

    @property
    def freeze_file(self) -> Path:
        return self.work_root / "freeze.json"

    @property
    def open_authorization(self) -> Path:
        return self.work_root / "open_authorized.json"


def load_config(path: str | Path) -> PipelineConfig:
    path = Path(path).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent

    def resolve(value: str) -> Path:
        candidate = Path(value).expanduser()
        return candidate if candidate.is_absolute() else (base / candidate).resolve()

    values: dict[str, Any] = {}
    for key in ("snapshot_root", "feature_root", "rules_root", "work_root"):
        values[key] = resolve(raw.pop(key))
    if "feature_identity" in raw:
        values["feature_identity"] = FeatureIdentity(**raw.pop("feature_identity"))
    for key in ("seeds", "lambda_grid", "wd_lr_grid", "bootstrap_seed"):
        if key in raw:
            values[key] = tuple(raw.pop(key))
    values.update(raw)
    known = {item.name for item in dataclasses.fields(PipelineConfig)}
    unknown = set(values) - known
    if unknown:
        raise SystemExit(f"unknown config keys: {sorted(unknown)}")
    return PipelineConfig(**values)


def parser(description: str) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--config", required=True, help="pipeline config JSON")
    return result


def device(config: PipelineConfig) -> Any:
    import torch

    if config.device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(config.device)


def inputs(config: PipelineConfig) -> PipelineInputs:
    return load_pipeline_inputs(
        config.snapshot_root,
        config.feature_root,
        dataset_id=config.dataset_id,
        identity=config.feature_identity,
    )


def zscore(values: Any, mask: Any) -> Any:
    """Per-user z-score over unmasked candidates; masked entries become zero."""
    result = np.zeros(len(values), dtype=np.float32)
    selected = np.asarray(values, dtype=np.float64)[mask]
    deviation = float(np.std(selected, ddof=0))
    if selected.size and np.isfinite(deviation) and deviation > 0.0:
        result[mask] = ((selected - float(np.mean(selected))) / deviation).astype(np.float32)
    return result


def per_user(rows: Any) -> dict[str, Any]:
    return {
        "NDCG@10": np.asarray([r.ndcg for r in rows]),
        "HR@10": np.asarray([r.hit_rate for r in rows]),
        "GAUC": np.asarray([np.nan if r.gauc is None else r.gauc for r in rows]),
    }


def split_of(line: bytes) -> str | None:
    """Split label encoded in a generated event's ``raw_event_id`` (``...:train:...``)."""
    marker = b'"raw_event_id":"'
    if marker not in line:
        return None
    head = line.split(marker, 1)[1][:90]
    for name in ("train", "val", "test"):
        if f":{name}:".encode() in head:
            return name
    return None


def load_source_events(path: Path, snapshot: Snapshot) -> tuple[Interaction, ...]:
    """Convert sealed TEST export rows into canonical interactions of ``snapshot``."""
    users = {int(raw): index for index, raw in enumerate(snapshot.raw_user_ids)}
    items = {int(raw): index for index, raw in enumerate(snapshot.raw_item_ids)}
    start = max(event.event_id for event in snapshot.events_by_split["val"]) + 1
    events: list[Interaction] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            moment = datetime.fromisoformat(row["event_ts"].replace("Z", "+00:00"))
            events.append(
                Interaction(
                    event_id=start + len(events),
                    user_id=users[row["raw_user_id"]],
                    item_id=items[row["raw_item_id"]],
                    timestamp=round(moment.timestamp() * 1_000_000),
                    event_type=row["event_type"],
                    raw_event_id=row["raw_event_id"],
                    event_origin=row["event_origin"],
                    session_id=row["session_id"],
                    cohort_id=row["cohort_id"],
                )
            )
    return tuple(events)


def snapshot_with_test(config: PipelineConfig) -> Snapshot:
    """TRAIN/VAL snapshot plus the sealed TEST events."""
    snapshot = load_canonical_snapshot(config.snapshot_root, required_splits=("train", "val"))
    splits = dict(snapshot.events_by_split)
    splits["test"] = load_source_events(config.sealed_test, snapshot)
    return dataclasses.replace(snapshot, events_by_split=splits)
