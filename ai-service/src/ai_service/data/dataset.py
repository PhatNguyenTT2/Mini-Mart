"""Dynamic Negative Sampling PyTorch Dataset with Deterministic Sampling."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set, cast
import zlib
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from ai_service.contracts import ContextRef
from ai_service.data.snapshot import Snapshot
from ai_service.data.rules import RuleStore


@dataclass
class TrainingBatch:
    """Grouped tensor batch for Hybrid Two-Tower Wide & Deep model training."""

    user_idx: torch.Tensor             # [B] int64
    persona_idx: torch.Tensor          # [B] int64
    candidate_item_idx: torch.Tensor   # [B, 5] int64
    context_item_idx: torch.Tensor     # [B] int64 (-1 if missing)
    context_present: torch.Tensor      # [B] bool
    log_lift: torch.Tensor             # [B, 5, 1] float32
    labels: torch.Tensor               # [B, 5] float32 (1.0 for pos, 0.0 for neg)
    sample_weight: torch.Tensor        # [B] float32


def collate_candidate_groups(batch_list: List[Dict[str, Any]]) -> TrainingBatch:
    """Collate individual sample dicts into batch tensors."""
    user_idx = torch.tensor([b["user_idx"] for b in batch_list], dtype=torch.long)
    persona_idx = torch.tensor([b["persona_idx"] for b in batch_list], dtype=torch.long)
    candidate_item_idx = torch.tensor(
        np.array([b["candidate_item_idx"] for b in batch_list]), dtype=torch.long
    )
    context_item_idx = torch.tensor([b["context_item_idx"] for b in batch_list], dtype=torch.long)
    context_present = torch.tensor([b["context_present"] for b in batch_list], dtype=torch.bool)
    log_lift = torch.tensor(
        np.array([b["log_lift"] for b in batch_list]), dtype=torch.float32
    )
    labels = torch.tensor([b["labels"] for b in batch_list], dtype=torch.float32)
    sample_weight = torch.tensor([b["sample_weight"] for b in batch_list], dtype=torch.float32)

    return TrainingBatch(
        user_idx=user_idx,
        persona_idx=persona_idx,
        candidate_item_idx=candidate_item_idx,
        context_item_idx=context_item_idx,
        context_present=context_present,
        log_lift=log_lift,
        labels=labels,
        sample_weight=sample_weight,
    )


class HybridImplicitDataset(Dataset):
    """Implicit feedback dataset with deterministic 1:4 negative sampling."""

    def __init__(
        self,
        snapshot: Snapshot,
        rule_store: RuleStore,
        split: str = "train",
        seed: int = 42,
    ):
        self.snapshot = snapshot
        self.rule_store = rule_store
        self.split = split
        self.seed = seed
        self.epoch = 0

        if split == "train":
            self.df = snapshot.train_df.copy()
        elif split == "val":
            self.df = snapshot.val_df.copy()
        else:
            self.df = snapshot.test_df.copy()

        self.df = self.df.sort_values(by=["internal_user_id", "event_ts"]).reset_index(drop=True)

        self.user_ids = self.df["internal_user_id"].values.astype(np.int64)
        self.product_ids = self.df["internal_product_id"].values.astype(np.int64)
        self.weights = self.df["interaction_weight"].values.astype(np.float32) if "interaction_weight" in self.df.columns else np.ones(len(self.df), dtype=np.float32)

        # Warm item catalog pool (excluding cold items)
        all_item_indices = np.arange(snapshot.manifest.num_items, dtype=np.int64)
        cold_set = set(snapshot.cold_item_ids)
        self.warm_item_indices = np.array(
            [i for i in all_item_indices if i not in cold_set], dtype=np.int64
        )

        # Popularity counts for Hard Negatives pool
        train_counts = snapshot.train_df["internal_product_id"].value_counts()
        sorted_warm = [i for i in train_counts.index if i not in cold_set and i < snapshot.manifest.num_items]
        num_popular = max(int(0.20 * len(self.warm_item_indices)), 10)
        self.popular_warm_pool = np.array(sorted_warm[:num_popular], dtype=np.int64)

        # User positive sets to prevent false negative sampling
        user_pos_groups = snapshot.train_df.groupby("internal_user_id")["internal_product_id"].apply(set)
        self.user_positive_sets: Dict[int, Set[int]] = {
            int(cast(Any, u)): set(items) for u, items in user_pos_groups.items()
        }

        self.context_refs = self._compute_context_refs()

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def _compute_context_refs(self) -> List[ContextRef]:
        """Compute context reference per event (using -1 to indicate missing context)."""
        n_rows = len(self.df)
        context_refs: List[ContextRef] = []
        user_last_item: Dict[int, int] = {}

        user_ids = self.df["internal_user_id"].values
        product_ids = self.df["internal_product_id"].values

        for idx in range(n_rows):
            u = int(user_ids[idx])
            p = int(product_ids[idx])
            if u in user_last_item:
                context_refs.append(ContextRef(item_idx=user_last_item[u], present=True))
            else:
                context_refs.append(ContextRef(item_idx=-1, present=False))
            user_last_item[u] = p

        return context_refs

    def __len__(self) -> int:
        return len(self.user_ids)

    def _deterministic_hash(self, key: Tuple[int, int, int]) -> int:
        return zlib.crc32(str(key).encode("utf-8"))

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        user_idx = int(self.user_ids[idx])
        pos_item_idx = int(self.product_ids[idx])
        sample_weight = float(self.weights[idx])

        raw_uid = self.snapshot.raw_user_map.get(user_idx, 0)
        persona_idx = int(self.snapshot.persona_map.get(raw_uid, 0))

        ctx = self.context_refs[idx]
        pos_set = self.user_positive_sets.get(user_idx, {pos_item_idx})

        # Sample 4 distinct negative candidates that are NOT in user's positive set
        negatives: List[int] = []
        salt = 0
        while len(negatives) < 2:
            salt += 1
            h = self._deterministic_hash((idx, self.epoch, salt))
            cand = int(self.popular_warm_pool[h % len(self.popular_warm_pool)])
            if cand not in pos_set and cand not in negatives:
                negatives.append(cand)

        while len(negatives) < 4:
            salt += 1
            h = self._deterministic_hash((idx, self.epoch, salt))
            cand = int(self.warm_item_indices[h % len(self.warm_item_indices)])
            if cand not in pos_set and cand not in negatives:
                negatives.append(cand)

        candidate_indices = np.array([pos_item_idx] + negatives, dtype=np.int64)

        # Lookup log1p(lift)
        log_lifts = np.zeros((5, 1), dtype=np.float32)
        if ctx.present:
            for i, cand_idx in enumerate(candidate_indices):
                log_lifts[i, 0] = self.rule_store.lookup(ctx.item_idx, int(cand_idx))

        labels = np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)

        return {
            "user_idx": user_idx,
            "persona_idx": persona_idx,
            "candidate_item_idx": candidate_indices,
            "context_item_idx": ctx.item_idx,
            "context_present": ctx.present,
            "log_lift": log_lifts,
            "labels": labels,
            "sample_weight": sample_weight,
        }
