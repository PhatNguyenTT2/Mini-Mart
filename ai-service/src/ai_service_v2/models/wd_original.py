"""Adapted Cheng-style linear crosses + MLP; not the frozen Hybrid model."""

from collections.abc import Sequence

import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F


class WideDeepOriginal(nn.Module):
    def __init__(
        self,
        num_users: int,
        text: np.ndarray,
        categories: np.ndarray,
        embedding_dim: int = 32,
        hidden: tuple[int, ...] = (1024, 512, 256),
    ):
        super().__init__()
        if text.ndim != 2 or text.shape[1] != 384 or len(text) != len(categories):
            raise ValueError("W&D requires aligned 384-dimensional text/category arrays")
        self.num_items = len(text)
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(self.num_items, embedding_dim)
        self.category_embedding = nn.Embedding(int(categories.max()) + 1, embedding_dim)
        self.register_buffer("text", torch.as_tensor(text.copy(), dtype=torch.float32))
        self.register_buffer("categories", torch.as_tensor(categories.copy(), dtype=torch.long))
        layers: list[nn.Module] = []
        size = embedding_dim * 4 + 384
        for width in hidden:
            layers.extend((nn.Linear(size, width), nn.ReLU()))
            size = width
        layers.append(nn.Linear(size, 1))
        self.deep = nn.Sequential(*layers)
        self.wide = nn.Embedding(self.num_items * self.num_items, 1)
        nn.init.zeros_(self.wide.weight)
        self.bias = nn.Parameter(torch.zeros(()))

    def encode_histories(self, histories: Sequence[Sequence[int]], device: torch.device):
        unique = [sorted(set(h)) for h in histories]
        width = max(1, max(map(len, unique), default=0))
        ids = torch.zeros((len(unique), width), dtype=torch.long)
        mask = torch.zeros((len(unique), width), dtype=torch.float32)
        for row, values in enumerate(unique):
            if values and (values[0] < 0 or values[-1] >= self.num_items):
                raise ValueError("history ID outside catalog")
            ids[row, : len(values)] = torch.tensor(values, dtype=torch.long)
            mask[row, : len(values)] = 1
        return ids.to(device), mask.to(device)

    def parts(self, users: Tensor, histories: Sequence[Sequence[int]], candidates: Tensor):
        if users.ndim != 1 or candidates.ndim != 2 or len(users) != len(histories):
            raise ValueError("invalid W&D batch")
        if len(candidates) != len(users) or not len(users):
            raise ValueError("invalid candidate batch")
        ids, mask = self.encode_histories(histories, users.device)
        pooled = (self.item_embedding(ids) * mask[..., None]).sum(1)
        pooled = pooled / mask.sum(1).clamp_min(1)[:, None]
        count = candidates.shape[1]
        raw = torch.cat(
            (
                self.user_embedding(users)[:, None, :].expand(-1, count, -1),
                self.item_embedding(candidates),
                self.category_embedding(self.categories[candidates]),
                pooled[:, None, :].expand(-1, count, -1),
                self.text[candidates],
            ),
            dim=2,
        )
        deep = self.deep(raw).squeeze(-1)
        cross_ids = ids[:, :, None] * self.num_items + candidates[:, None, :]
        wide = (self.wide(cross_ids).squeeze(-1) * mask[:, :, None]).sum(1) + self.bias
        return wide, deep

    def forward(self, users: Tensor, histories: Sequence[Sequence[int]], candidates: Tensor):
        wide, deep = self.parts(users, histories, candidates)
        return wide + deep

    def optimizer(self, lr_wide: float):
        wide_parameters = [self.wide.weight, self.bias]
        excluded = {id(p) for p in wide_parameters}
        return torch.optim.AdamW(
            [
                {"params": [p for p in self.parameters() if id(p) not in excluded], "lr": 0.001},
                {"params": wide_parameters, "lr": lr_wide},
            ],
            weight_decay=1e-5,
        )

    @torch.no_grad()
    def score_user(self, user_id: int, history: Sequence[int], chunk: int = 512):
        device = self.wide.weight.device
        self.eval()
        outputs = []
        users = torch.tensor([user_id], device=device)
        for start in range(0, self.num_items, chunk):
            candidates = torch.arange(start, min(start + chunk, self.num_items), device=device)
            outputs.append(self(users, [history], candidates[None, :]).flatten().cpu())
        values = torch.cat(outputs).numpy().astype(np.float32, copy=False)
        if not np.isfinite(values).all():
            raise ValueError("non-finite inference scores")
        return values


def sampled_bce(model, examples, *, negative_seed: int, device: torch.device):
    """One positive and four distinct negatives, not four duplicated positives."""
    from ai_service_v2.training.local_v5_qualification import sample_negative_items

    candidates = []
    for index, example in enumerate(examples):
        negatives = sample_negative_items(
            positive_item_id=example.positive_item_id,
            history_item_ids=example.history_item_ids,
            excluded_item_ids=example.target_basket_item_ids,
            num_items=model.num_items,
            seed=negative_seed + index,
            count=4,
        )
        candidates.append((example.positive_item_id, *negatives))
    users = torch.tensor([e.user_id for e in examples], dtype=torch.long, device=device)
    logits = model(
        users,
        [e.history_item_ids for e in examples],
        torch.tensor(candidates, dtype=torch.long, device=device),
    )
    labels = torch.zeros_like(logits)
    labels[:, 0] = 1
    return F.binary_cross_entropy_with_logits(logits, labels, reduction="sum"), logits.numel()
