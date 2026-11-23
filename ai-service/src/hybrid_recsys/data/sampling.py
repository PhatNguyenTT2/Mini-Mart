"""Deterministic negative sampling for pairwise and sampled-BCE training."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from hybrid_recsys.errors import ContractError, IntegrityError

NEGATIVES_PER_POSITIVE = 4


def sample_negative_items(
    *,
    positive_item_id: int,
    history_item_ids: Sequence[int],
    num_items: int,
    seed: int,
    count: int = NEGATIVES_PER_POSITIVE,
    excluded_item_ids: Sequence[int] = (),
) -> tuple[int, ...]:
    """Sample exactly ``count`` distinct catalog items that the user has not interacted with."""
    if count not in {1, NEGATIVES_PER_POSITIVE}:
        raise ContractError("training uses one or four negatives per positive")
    excluded = (
        {int(value) for value in history_item_ids}
        | {int(value) for value in excluded_item_ids}
        | {int(positive_item_id)}
    )
    excluded_in_catalog = {item_id for item_id in excluded if 0 <= item_id < num_items}
    if num_items - len(excluded_in_catalog) < count:
        raise IntegrityError("catalog is too small for the requested negative count")
    rng = np.random.Generator(np.random.PCG64(seed))
    selected: list[int] = []
    selected_set: set[int] = set()
    while len(selected) < count:
        candidate = int(rng.integers(0, num_items))
        if candidate in excluded_in_catalog or candidate in selected_set:
            continue
        selected.append(candidate)
        selected_set.add(candidate)
    return tuple(selected)
