"""Batched scoring and a vectorized full-catalog evaluator.

These paths change speed only: model outputs, ranking, tie-breaking and metrics match the reference
implementations in ``hybrid_recsys`` (checked by ``07_verify_numbers.py``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from scipy.stats import rankdata
from torch import Tensor

from hybrid_recsys.errors import ContractError, ScoreError
from hybrid_recsys.evaluation.metrics import UserMetrics, aggregate_user_metrics_at_k
from hybrid_recsys.models.confirmatory import ConfirmatoryTwoTower


class FastConfirmatoryTwoTower(ConfirmatoryTwoTower):
    """Encodes each distinct history item once per call instead of once per history."""

    def user_vectors(
        self,
        user_ids: Tensor,
        history_item_ids: Sequence[tuple[int, ...]],
    ) -> Tensor:
        if user_ids.dtype != torch.long or user_ids.ndim != 1:
            raise ContractError("user IDs must be an int64 vector")
        if user_ids.numel() != len(history_item_ids) or user_ids.numel() < 1:
            raise ContractError("user/history batch dimensions differ")
        device = user_ids.device
        lengths = torch.tensor([len(history) for history in history_item_ids], device=device)
        size = user_ids.numel()
        dimension = self.config.tower_output_dim
        weight = self.user_embedding.weight
        packed = torch.tensor(
            [item for history in history_item_ids for item in history], dtype=torch.long
        )
        if packed.numel():
            if int(packed.min()) < 0 or int(packed.max()) >= self.num_items:
                raise ContractError("item IDs are outside the confirmatory catalog")
            unique, inverse = torch.unique(packed, return_inverse=True)
            vectors = self._item_vectors_validated(unique.to(device))[inverse.to(device)]
            segments = torch.repeat_interleave(torch.arange(size, device=device), lengths)
            totals = torch.zeros(size, dimension, dtype=weight.dtype, device=device).index_add(
                0, segments, vectors
            )
            history_vectors = totals / lengths.clamp(min=1).unsqueeze(1).to(weight.dtype)
        else:
            history_vectors = torch.zeros(size, dimension, dtype=weight.dtype, device=device)
        raw = torch.cat((self.user_embedding(user_ids), history_vectors), dim=1)
        return F.normalize(self.user_tower(raw), p=2.0, dim=1, eps=1e-12)


def promote_to_fast(model: ConfirmatoryTwoTower) -> FastConfirmatoryTwoTower:
    """Switch an existing model to the fast path; parameters and state are untouched."""

    model.__class__ = FastConfirmatoryTwoTower
    return model  # type: ignore[return-value]


def batched_scores(
    model: ConfirmatoryTwoTower,
    user_ids: Sequence[int],
    histories: Sequence[tuple[int, ...]],
    *,
    batch_size: int = 512,
) -> Any:
    """Yield (position, scores) with all item vectors encoded once."""

    device = model.user_embedding.weight.device
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            items = model.item_vectors(
                torch.arange(model.num_items, dtype=torch.long, device=device)
            )
            for start in range(0, len(user_ids), batch_size):
                chunk = user_ids[start : start + batch_size]
                users = model.user_vectors(
                    torch.tensor(list(chunk), dtype=torch.long, device=device),
                    list(histories[start : start + batch_size]),
                )
                values = (users @ items.T).cpu().numpy().astype(np.float32)
                for offset, row in enumerate(values):
                    yield start + offset, row
    finally:
        model.train(was_training)


def wd_batched_scores(
    model: Any,
    user_ids: Sequence[int],
    histories: Sequence[tuple[int, ...]],
    *,
    batch_size: int = 16,
) -> Any:
    """Yield (position, scores) for W&D, with the first deep layer split into item and user terms."""

    device = model.wide.weight.device
    n = model.num_items
    d = model.user_embedding.embedding_dim
    wide = model.wide.weight.view(n, n)
    first, rest = model.deep[0], model.deep[1:]
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            candidates = torch.arange(n, device=device)
            item_side = torch.zeros((n, first.in_features), device=device)
            item_side[:, d : 2 * d] = model.item_embedding(candidates)
            item_side[:, 2 * d : 3 * d] = model.category_embedding(model.categories)
            item_side[:, 4 * d :] = model.text
            item_term = first(item_side)
            del item_side
            for start in range(0, len(user_ids), batch_size):
                chunk = list(user_ids[start : start + batch_size])
                users = torch.tensor(chunk, device=device)
                ids, mask = model.encode_histories(
                    list(histories[start : start + batch_size]), device
                )
                pooled = (model.item_embedding(ids) * mask[..., None]).sum(1)
                pooled = pooled / mask.sum(1).clamp_min(1)[:, None]
                user_side = torch.zeros((len(chunk), first.in_features), device=device)
                user_side[:, :d] = model.user_embedding(users)
                user_side[:, 3 * d : 4 * d] = pooled
                user_term = user_side @ first.weight.T
                deep = rest(item_term[None] + user_term[:, None, :]).squeeze(-1)
                wide_part = torch.stack(
                    [wide[ids[row][mask[row] > 0]].sum(0) for row in range(len(chunk))]
                )
                values = (wide_part + model.bias + deep).cpu().numpy().astype(np.float32)
                for offset, row in enumerate(values):
                    yield start + offset, row
    finally:
        model.train(was_training)


class FastEvaluator:
    """Same masking, ranking, tie-break and AUC as FullCatalogEvaluator, without Python set loops."""

    def __init__(self, protocol: Any) -> None:
        self.protocol = protocol
        self.user_ids = tuple(protocol.eligible_user_ids)
        self.raw = np.asarray(protocol.raw_item_ids, dtype=np.int64)
        self.cutoff = protocol.manifest.cutoff
        size = len(protocol.candidate_item_ids)
        if tuple(protocol.candidate_item_ids) != tuple(range(size)):
            raise ScoreError("fast evaluator requires dense candidate positions")
        self.size = size
        self.seen: list[Any] = []
        self.positive: list[Any] = []
        self.histories: list[tuple[int, ...]] = []
        for user in self.user_ids:
            case = protocol.case_for(user)
            self.seen.append(np.fromiter(case.history_item_ids, dtype=np.int64))
            self.positive.append(np.fromiter(case.positive_item_ids, dtype=np.int64))
            self.histories.append(tuple(sorted(case.history_item_ids)))
        self.idcg = np.cumsum(1.0 / np.log2(np.arange(2, self.cutoff + 2)))

    def user_metrics(self, position: int, scores: Any) -> UserMetrics:
        values = np.asarray(scores, dtype=np.float64)
        if values.shape != (self.size,) or not np.isfinite(values).all():
            raise ScoreError("score vector is invalid")
        seen = self.seen[position]
        positive = self.positive[position]
        available = np.ones(self.size, dtype=bool)
        available[seen] = False
        indices = np.flatnonzero(available)
        pool = -values[indices]
        k = self.cutoff
        if len(pool) > k:
            threshold = np.partition(pool, k - 1)[k - 1]
            kept = np.flatnonzero(pool <= threshold)
        else:
            kept = np.arange(len(pool))
        order = np.lexsort((self.raw[indices[kept]], pool[kept]))
        top = indices[kept[order]][:k]
        is_positive = np.zeros(self.size, dtype=bool)
        is_positive[positive] = True
        ranks = np.flatnonzero(is_positive[top]) + 1
        dcg = sum(1.0 / np.log2(rank + 1) for rank in ranks.tolist())
        idcg = float(self.idcg[min(len(positive), k) - 1])
        negative = np.flatnonzero(available & ~is_positive)
        auc = None
        if len(positive) and len(negative):
            combined = np.concatenate((values[positive], values[negative]))
            rank_sum = float(rankdata(combined, method="average")[: len(positive)].sum())
            pairs = len(positive) * len(negative)
            auc = (rank_sum - len(positive) * (len(positive) + 1) / 2.0) / pairs
        return UserMetrics(
            hit_rate=float(len(ranks) > 0),
            ndcg=float(dcg / idcg if idcg else 0.0),
            gauc=auc,
            ranked_indices=tuple(int(value) for value in top),
        )

    def evaluate(self, rows: Any) -> tuple[list[UserMetrics], dict[str, float | None]]:
        metrics: list[UserMetrics | None] = [None] * len(self.user_ids)
        for position, scores in rows:
            metrics[position] = self.user_metrics(position, scores)
        if any(row is None for row in metrics):
            raise ScoreError("fast evaluator did not receive every eligible user")
        finished = [row for row in metrics if row is not None]
        return finished, aggregate_user_metrics_at_k(finished, cutoff=self.cutoff)
