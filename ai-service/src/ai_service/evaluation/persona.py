"""Prepared, streaming Persona baseline shared by probes and release evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import PreparedEvaluationSplit


@dataclass(frozen=True)
class PreparedPersonaBaseline:
    score_vectors: np.ndarray
    persona_by_user: np.ndarray


def prepare_persona_baseline(
    snapshot: Snapshot,
    prepared_split: PreparedEvaluationSplit,
) -> PreparedPersonaBaseline:
    """Aggregate organic purchase-category affinity once for all scoring batches."""
    history = prepared_split.history_events
    purchases = history[history.event_type == "purchase"]
    category_by_item = snapshot.catalog_df.sort_values(
        "internal_product_id", kind="stable"
    ).internal_leaf_category_id.to_numpy(np.int64)
    persona_by_user = np.zeros(snapshot.manifest.num_users + 1, dtype=np.int64)
    for user, persona in prepared_split.personas.items():
        persona_by_user[int(user)] = int(persona)
    num_personas = int(persona_by_user.max(initial=0)) + 1
    counts = np.zeros((num_personas, int(category_by_item.max(initial=0)) + 1), dtype=np.float64)
    for user, item in purchases[["internal_user_id", "internal_product_id"]].itertuples(
        index=False, name=None
    ):
        counts[persona_by_user[int(user)], category_by_item[int(item)]] += 1.0
    popularity = np.log1p(
        np.bincount(
            history.internal_product_id.to_numpy(np.int64),
            minlength=snapshot.manifest.num_items,
        ).astype(np.float64)
    )
    score_vectors = counts[:, category_by_item] + popularity[None, :] * 1e-4
    score_vectors = np.asarray(score_vectors, dtype=np.float32)
    score_vectors.setflags(write=False)
    persona_by_user.setflags(write=False)
    return PreparedPersonaBaseline(score_vectors=score_vectors, persona_by_user=persona_by_user)


def score_persona_batch(
    prepared: PreparedPersonaBaseline,
    users: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    users = np.asarray(users, dtype=np.int64)
    candidates = np.asarray(candidates, dtype=np.int64)
    return np.asarray(
        prepared.score_vectors[prepared.persona_by_user[users]][:, candidates],
        dtype=np.float32,
    )


__all__ = ["PreparedPersonaBaseline", "prepare_persona_baseline", "score_persona_batch"]
