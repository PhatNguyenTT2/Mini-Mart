"""Deterministic sanity scorers used only by local contract tests."""

from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np

from ai_service_v2.data.snapshot import Interaction


class RandomScorer:
    """Per-user deterministic pseudo-random scores; no global RNG state."""

    def __init__(self, seed: int = 42) -> None:
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self.seed = seed

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        key = f"random-v1:{self.seed}:{user_id}".encode()
        derived_seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
        rng = np.random.Generator(np.random.PCG64(derived_seed))
        # Consume candidates in their frozen order; item IDs are still checked
        # by the evaluator and are intentionally not re-sorted here.
        return rng.random(len(candidate_item_ids), dtype=np.float64)


class MostPopScorer:
    """Train-only popularity scorer for a sanity/control condition."""

    def __init__(self, train_events: tuple[Interaction, ...]) -> None:
        self._counts = Counter(
            event.item_id for event in train_events if event.event_type == "purchase"
        )

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        del user_id
        return np.asarray(
            [self._counts.get(item_id, 0) for item_id in candidate_item_ids], dtype=float
        )


__all__ = ["MostPopScorer", "RandomScorer"]
