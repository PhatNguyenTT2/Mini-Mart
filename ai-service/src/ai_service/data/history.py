"""Materialize strict prior-purchase profiles shared by evaluation and serving."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd
import torch

from ai_service.data.quality import filter_event_origin
from ai_service.data.snapshot import Snapshot
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@torch.no_grad()
def build_user_profile_vectors(
    model: HybridTwoTowerModel,
    snapshot: Snapshot,
    item_vectors: torch.Tensor,
    history: pd.DataFrame,
    *,
    max_history_items: int,
    device: torch.device,
) -> torch.Tensor:
    """Return `[num_users+1,D]`; row zero is the unknown-user profile."""
    if max_history_items < 1:
        raise ValueError("max_history_items must be positive")
    dimension = int(item_vectors.shape[-1])
    profiles = torch.zeros(
        (snapshot.manifest.num_users + 1, dimension),
        dtype=item_vectors.dtype,
        device=device,
    )
    purchases = filter_event_origin(history)
    purchases = purchases[purchases.event_type == "purchase"].sort_values(
        ["internal_user_id", "event_ts", "event_id"], kind="stable"
    )
    if purchases.empty:
        return profiles
    rows: list[tuple[int, np.ndarray, np.ndarray]] = []
    for raw_user, group in purchases.groupby("internal_user_id", sort=True):
        user = int(cast(Any, raw_user))
        selected = group.tail(max_history_items)
        timestamps = pd.to_datetime(selected.event_ts, utc=True)
        reference = timestamps.max()
        ages = (reference - timestamps).dt.total_seconds().to_numpy(np.float32) / 86_400
        rows.append(
            (
                user,
                selected.internal_product_id.to_numpy(np.int64),
                ages,
            )
        )
    batch_size = 1_024
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        width = max(len(items) for _, items, _ in batch)
        ids = np.zeros((len(batch), width), dtype=np.int64)
        mask = np.zeros((len(batch), width), dtype=np.bool_)
        ages = np.zeros((len(batch), width), dtype=np.float32)
        users = np.empty(len(batch), dtype=np.int64)
        for row_index, (user, items, item_ages) in enumerate(batch):
            users[row_index] = user
            ids[row_index, : len(items)] = items
            mask[row_index, : len(items)] = True
            ages[row_index, : len(items)] = item_ages
        encoded, _ = model.encode_history(
            item_vectors[torch.from_numpy(ids).to(device)],
            torch.from_numpy(mask).to(device),
            torch.from_numpy(ages).to(device),
        )
        profiles[torch.from_numpy(users).to(device)] = encoded
    return profiles
