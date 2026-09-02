"""Minimal adapter interface; native reference implementations stay outside it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.snapshot import Snapshot


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    seed: int
    config_sha256: str
    environment_lock_sha256: str
    checkpoint_rule: str


@dataclass(frozen=True)
class CheckpointRef:
    path: str
    sha256: str
    selected_by: str


class ModelAdapter(Protocol):
    """Deep interface hiding native training and exposing score vectors."""

    def describe(self) -> ModelDescriptor: ...

    def fit(self, snapshot: Snapshot, run: RunSpec) -> CheckpointRef: ...

    def score(
        self,
        snapshot: Snapshot,
        checkpoint: CheckpointRef,
        user_id: int,
        candidate_item_ids: tuple[int, ...],
    ) -> np.ndarray: ...


__all__ = ["CheckpointRef", "ModelAdapter", "RunSpec"]
