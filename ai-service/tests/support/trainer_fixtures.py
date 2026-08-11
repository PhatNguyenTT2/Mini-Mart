"""Reusable public-seam adapters for ``Trainer.fit`` contract tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ai_service.evaluation.full_catalog import TrainingValidationPass


@dataclass
class RecordingValidationEvaluator:
    """Return deterministic validation passes while recording production calls."""

    passes: tuple[TrainingValidationPass, ...]
    calls: int = 0

    def evaluate_training_epoch(self, *args: Any, **kwargs: Any) -> TrainingValidationPass:
        del args, kwargs
        if not self.passes:
            raise AssertionError("fixture has no validation pass")
        index = min(self.calls, len(self.passes) - 1)
        self.calls += 1
        return self.passes[index]


class RecordingSampler:
    """Delegate sampling while recording the model-hard cache publication."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.update_calls = 0
        self.last_cache: np.ndarray | None = None

    def sample(self, *args: Any, **kwargs: Any) -> Any:
        return self.delegate.sample(*args, **kwargs)

    def update_model_hard_cache(self, cache: np.ndarray) -> None:
        self.update_calls += 1
        self.last_cache = np.array(cache, dtype=np.int32, copy=True)
        self.delegate.update_model_hard_cache(cache)


__all__ = ["RecordingSampler", "RecordingValidationEvaluator"]
