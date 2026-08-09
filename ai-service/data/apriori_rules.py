"""Leakage-safe Apriori rule artifact builder and CSR RuleStore lookup module for ai-service.

Mines association rules strictly from train-period order baskets (order_date < validation_cutoff), excluding cold products.
Normalizes lift values via f(L) = log1p(L) and stores rules in sorted CSR arrays for O(1) serving lookups and PyTorch sparse matrix evaluation.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from data.ingestion import SnapshotArtifacts, compute_sha256


class RuleStore:
    """CSR sparse rule store supporting O(1) lookup and batch indexing."""

    def __init__(
        self,
        indptr: np.ndarray,
        indices: np.ndarray,
        log_lift: np.ndarray,
        count: np.ndarray,
        num_items: int = 5200,
    ):
        self.indptr = indptr.astype(np.int64)
        self.indices = indices.astype(np.int32)
        self.log_lift = log_lift.astype(np.float32)
        self.count = count.astype(np.int32)
        self.num_items = num_items

    def lookup(self, context_item_idx: int, candidate_item_idx: int) -> float:
        """Lookup log1p(lift) for a (context, candidate) pair. Return 0.0 if no rule exists."""
        if context_item_idx < 0 or context_item_idx >= self.num_items:
            return 0.0
        if candidate_item_idx < 0 or candidate_item_idx >= self.num_items:
            return 0.0

        start = self.indptr[context_item_idx]
        end = self.indptr[context_item_idx + 1]

        if start == end:
            return 0.0

        row_indices = self.indices[start:end]
        pos = np.searchsorted(row_indices, candidate_item_idx)

        if pos < len(row_indices) and row_indices[pos] == candidate_item_idx:
            return float(self.log_lift[start + pos])
        return 0.0

    def lookup_batch(self, context_item_idx: int, candidate_indices: np.ndarray) -> np.ndarray:
        """Lookup log1p(lift) for one context item against a batch of candidate item indices."""
        scores = np.zeros(len(candidate_indices), dtype=np.float32)
        if context_item_idx < 0 or context_item_idx >= self.num_items:
            return scores

        start = self.indptr[context_item_idx]
        end = self.indptr[context_item_idx + 1]

        if start == end:
            return scores

        row_indices = self.indices[start:end]
        row_lifts = self.log_lift[start:end]

        for i, cand_idx in enumerate(candidate_indices):
            pos = np.searchsorted(row_indices, cand_idx)
            if pos < len(row_indices) and row_indices[pos] == cand_idx:
                scores[i] = row_lifts[pos]
        return scores


def build_rule_store(
    snapshot: SnapshotArtifacts,
    min_count: int = 3,
    min_lift: float = 1.0,
) -> RuleStore:
    """Mine leakage-safe Apriori association rules from train order baskets."""
    snapshot_dir = snapshot.snapshot_dir
    val_min_ts = pd.to_datetime(snapshot.manifest.val_min_ts, utc=True)

    baskets_df = snapshot.order_baskets_df.copy()
    baskets_df["order_date"] = pd.to_datetime(baskets_df["order_date"], utc=True)

    # Filter to train-period baskets only
    train_baskets = baskets_df[baskets_df["order_date"] < val_min_ts].copy()

    # Map raw product IDs to internal product indices
    product_map = snapshot.product_map
    cold_set = set(snapshot.cold_item_ids)

    train_baskets["internal_product_id"] = train_baskets["product_id"].map(product_map)

    # Filter out missing/cold items
    train_baskets = train_baskets[
        train_baskets["internal_product_id"].notna()
        & ~train_baskets["internal_product_id"].isin(cold_set)
    ].copy()

    train_baskets["internal_product_id"] = train_baskets["internal_product_id"].astype(int)

    # Total train basket count N
    basket_groups = train_baskets.groupby("order_id")["internal_product_id"].apply(set)
    N = max(len(basket_groups), 1)

    # Single item frequencies c_A
    item_counts: Dict[int, int] = {}
    pair_counts: Dict[Tuple[int, int], int] = {}

    for items in basket_groups:
        item_list = list(items)
        for item in item_list:
            item_counts[item] = item_counts.get(item, 0) + 1

        for i in range(len(item_list)):
            for j in range(i + 1, len(item_list)):
                p1, p2 = item_list[i], item_list[j]
                if p1 > p2:
                    p1, p2 = p2, p1
                pair_counts[(p1, p2)] = pair_counts.get((p1, p2), 0) + 1

    # Filter pairs with co_purchase_count >= min_count and calculate Lift
    valid_rules: Dict[Tuple[int, int], Tuple[float, int]] = {}

    for (p1, p2), count in pair_counts.items():
        if count < min_count:
            continue
        c_A = item_counts.get(p1, 0)
        c_B = item_counts.get(p2, 0)

        if c_A == 0 or c_B == 0:
            continue

        lift = (count * N) / (c_A * c_B)
        if lift > min_lift and np.isfinite(lift):
            log_lift_val = float(np.log1p(lift))
            # Materialize both directions: p1 -> p2 and p2 -> p1
            valid_rules[(p1, p2)] = (log_lift_val, count)
            valid_rules[(p2, p1)] = (log_lift_val, count)

    num_items = snapshot.manifest.num_items

    # Group valid rules by source item (O(num_rules) instead of O(num_items * num_rules))
    adj: Dict[int, List[Tuple[int, float, int]]] = {i: [] for i in range(num_items)}
    for (src, tgt), (l_val, cnt) in valid_rules.items():
        if 0 <= src < num_items:
            adj[src].append((tgt, l_val, cnt))

    indptr = [0]
    indices = []
    log_lift_list = []
    count_list = []

    for item_a in range(num_items):
        targets = adj[item_a]
        targets.sort(key=lambda x: x[0])
        for tgt, l_val, cnt in targets:
            indices.append(tgt)
            log_lift_list.append(l_val)
            count_list.append(cnt)

        indptr.append(len(indices))

    indptr_arr = np.array(indptr, dtype=np.int64)
    indices_arr = np.array(indices, dtype=np.int32)
    log_lift_arr = np.array(log_lift_list, dtype=np.float32)
    count_arr = np.array(count_list, dtype=np.int32)

    # Persist npz artifact
    output_npz_path = snapshot_dir / "apriori_rules.npz"
    np.savez_compressed(
        output_npz_path,
        indptr=indptr_arr,
        indices=indices_arr,
        log_lift=log_lift_arr,
        count=count_arr,
    )

    return RuleStore(
        indptr=indptr_arr,
        indices=indices_arr,
        log_lift=log_lift_arr,
        count=count_arr,
        num_items=num_items,
    )


def load_rule_store(snapshot_dir: Path) -> RuleStore:
    """Load CSR RuleStore from apriori_rules.npz artifact."""
    npz_path = snapshot_dir / "apriori_rules.npz"
    if not npz_path.exists():
        raise FileNotFoundError(f"Apriori rule artifact not found: {npz_path}")

    data = np.load(npz_path)
    return RuleStore(
        indptr=data["indptr"],
        indices=data["indices"],
        log_lift=data["log_lift"],
        count=data["count"],
        num_items=len(data["indptr"]) - 1,
    )
