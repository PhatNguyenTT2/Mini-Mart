"""Training examples and the epoch loop for the two-tower Deep branch."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from hybrid_recsys.data.sampling import NEGATIVES_PER_POSITIVE, sample_negative_items
from hybrid_recsys.data.snapshot import Snapshot
from hybrid_recsys.errors import ContractError, IntegrityError
from hybrid_recsys.models.confirmatory import ConfirmatoryTwoTower

EFFECTIVE_BATCH_SIZE = 1024
MICROBATCH_SIZE = 256


@dataclass(frozen=True)
class TrainingExample:
    user_id: int
    history_item_ids: tuple[int, ...]
    positive_item_id: int
    target_basket_item_ids: tuple[int, ...]


def build_train_examples(
    snapshot: Snapshot, item_id_map: Mapping[int, int] | None = None
) -> tuple[TrainingExample, ...]:
    """One example per novel item of each organic TRAIN basket, with the strict-prefix history.

    Items of the same basket never appear in each other's history, and the whole basket is
    excluded from negative sampling.
    """
    history: dict[int, list[int]] = {user: [] for user in snapshot.users}
    grouped: dict[tuple[int, str], list[Any]] = {}
    for event in snapshot.events_by_split["train"]:
        if event.event_type == "purchase" and event.event_origin == "organic":
            basket = event.basket_id or f"event:{event.event_id}"
            grouped.setdefault((event.user_id, basket), []).append(event)
    baskets = sorted(
        grouped.values(),
        key=lambda rows: (
            rows[0].user_id,
            min(row.timestamp for row in rows),
            rows[0].basket_id or f"event:{rows[0].event_id}",
        ),
    )
    examples: list[TrainingExample] = []
    for rows in baskets:
        user = rows[0].user_id
        items = tuple(
            sorted(
                {
                    int(item_id_map[row.item_id] if item_id_map is not None else row.item_id)
                    for row in rows
                    if item_id_map is None or row.item_id in item_id_map
                }
            )
        )
        if not items:
            continue
        prefix = history[user]
        for positive in (item for item in items if item not in prefix):
            examples.append(TrainingExample(user, tuple(prefix), positive, items))
        prefix.extend(items)
    if not examples:
        raise IntegrityError("TRAIN produced no examples")
    return tuple(examples)


def _pairwise_batch(
    model: ConfirmatoryTwoTower,
    examples: Sequence[TrainingExample],
    *,
    negative_seed: int,
    device: torch.device,
    negatives_per_positive: int,
) -> tuple[Tensor, int]:
    users: list[int] = []
    positives: list[int] = []
    negatives: list[int] = []
    histories: list[tuple[int, ...]] = []
    for index, example in enumerate(examples):
        for negative in sample_negative_items(
            positive_item_id=example.positive_item_id,
            history_item_ids=example.history_item_ids,
            num_items=model.num_items,
            seed=negative_seed + index,
            excluded_item_ids=example.target_basket_item_ids,
            count=negatives_per_positive,
        ):
            users.append(example.user_id)
            positives.append(example.positive_item_id)
            negatives.append(negative)
            histories.append(example.history_item_ids)
    positive_scores, negative_scores = model.pairwise_scores(
        torch.tensor(users, dtype=torch.long, device=device),
        histories,
        torch.tensor(positives, dtype=torch.long, device=device),
        torch.tensor(negatives, dtype=torch.long, device=device),
    )
    loss = -F.logsigmoid(positive_scores - negative_scores).sum()
    return loss, len(negatives)


def train_deep_epoch(
    model: ConfirmatoryTwoTower,
    optimizer: torch.optim.Optimizer,
    examples: Sequence[TrainingExample],
    *,
    epoch: int,
    device: torch.device,
    effective_batch_size: int = EFFECTIVE_BATCH_SIZE,
    microbatch_size: int = MICROBATCH_SIZE,
    negatives_per_positive: int = NEGATIVES_PER_POSITIVE,
) -> dict[str, float | int]:
    """One epoch of BPR loss with gradient accumulation over micro-batches."""
    if not examples:
        raise ContractError("no training examples")
    if not 1 <= microbatch_size <= effective_batch_size:
        raise ContractError("microbatch size is invalid")
    model.train()
    total_loss = 0.0
    total_pairs = 0
    steps = 0
    for group_start in range(0, len(examples), effective_batch_size):
        group = examples[group_start : group_start + effective_batch_size]
        optimizer.zero_grad(set_to_none=True)
        for micro_start in range(0, len(group), microbatch_size):
            loss, pairs = _pairwise_batch(
                model,
                group[micro_start : micro_start + microbatch_size],
                negative_seed=epoch * 1_000_000 + group_start + micro_start,
                device=device,
                negatives_per_positive=negatives_per_positive,
            )
            total_loss += float(loss.detach().cpu())
            (loss / float(len(group) * negatives_per_positive)).backward()  # type: ignore[no-untyped-call]
            total_pairs += pairs
        optimizer.step()
        steps += 1
    if total_pairs < 1 or not math.isfinite(total_loss):
        raise IntegrityError("epoch produced a non-finite or empty loss")
    return {
        "epoch": epoch,
        "optimizer_steps": steps,
        "pair_count": total_pairs,
        "mean_pairwise_loss": total_loss / total_pairs,
    }
