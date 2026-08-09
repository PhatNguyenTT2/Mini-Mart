"""Apriori Association Rule Mining and CSR Sparse Store."""

from collections import Counter
import hashlib
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import numpy as np
import pandas as pd

from ai_service.config import Settings
from ai_service.contracts import RuleManifestV2
from ai_service.data.snapshot import Snapshot


class RuleStore:
    """Fast CSR sparse matrix lookup for Apriori lift scores."""

    def __init__(
        self,
        num_items: int,
        rule_pairs: List[Tuple[int, int, float]],
        min_lift: float = 1.0,
    ):
        self.num_items = num_items
        self.min_lift = min_lift

        # Build dict for O(1) pairwise lookup
        self.lift_dict: Dict[Tuple[int, int], float] = {}
        for item_a, item_b, lift in rule_pairs:
            if lift >= min_lift:
                self.lift_dict[(int(item_a), int(item_b))] = float(lift)

    def lookup(self, context_item_idx: int, candidate_item_idx: int) -> float:
        """Lookup log1p(lift) value for context vs candidate item pair."""
        if context_item_idx < 0:
            return 0.0
        lift = self.lift_dict.get((context_item_idx, candidate_item_idx), 0.0)
        if lift <= 1.0:
            return 0.0
        return float(np.log1p(lift))

    def batch_lookup(self, context_indices: np.ndarray, candidate_indices: np.ndarray) -> np.ndarray:
        """Batch lookup log1p(lift) for candidate groups [B, C]."""
        batch_size, num_cands = candidate_indices.shape
        log_lifts = np.zeros((batch_size, num_cands, 1), dtype=np.float32)

        for b in range(batch_size):
            ctx_idx = int(context_indices[b])
            if ctx_idx >= 0:
                for c in range(num_cands):
                    cand_idx = int(candidate_indices[b, c])
                    log_lifts[b, c, 0] = self.lookup(ctx_idx, cand_idx)
        return log_lifts


class AprioriRuleMiner:
    """Mines Apriori co-purchase association rules from train-period order baskets."""

    def __init__(self, min_support_count: int = 3, min_lift: float = 1.0):
        self.min_support_count = min_support_count
        self.min_lift = min_lift

    def mine(self, snapshot: Snapshot) -> RuleStore:
        orders_df = snapshot.order_baskets_df.copy()
        cold_set = set(snapshot.cold_item_ids)

        # Filter out cold items
        warm_orders = orders_df[~orders_df["internal_product_id"].isin(cold_set)]

        # Group by order_id to form baskets
        baskets = warm_orders.groupby("order_id")["internal_product_id"].apply(set)

        item_counts: Counter = Counter()
        pair_counts: Counter = Counter()
        total_baskets = len(baskets)

        for basket in baskets:
            sorted_items = sorted(basket)
            for item in sorted_items:
                item_counts[item] += 1
            for a, b in combinations(sorted_items, 2):
                pair_counts[(a, b)] += 1
                pair_counts[(b, a)] += 1

        rule_pairs: List[Tuple[int, int, float]] = []

        for (a, b), count in pair_counts.items():
            if count >= self.min_support_count:
                support_a = item_counts[a] / total_baskets
                support_b = item_counts[b] / total_baskets
                support_ab = count / total_baskets
                lift = support_ab / (support_a * support_b)

                if lift >= self.min_lift:
                    rule_pairs.append((int(a), int(b), float(lift)))

        # Save to snapshot artifacts
        out_dir = snapshot.snapshot_dir
        rule_data = np.array(rule_pairs, dtype=np.float32) if len(rule_pairs) > 0 else np.zeros((0, 3), dtype=np.float32)
        np.savez_compressed(out_dir / "apriori_rules.npz", rules=rule_data)

        checksum = hashlib.sha256(rule_data.tobytes()).hexdigest()[:16]
        manifest = RuleManifestV2(
            num_rules=len(rule_pairs),
            min_support=float(self.min_support_count / max(total_baskets, 1)),
            min_confidence=0.0,
            min_lift=self.min_lift,
            train_basket_count=total_baskets,
            checksum=checksum,
        )
        (out_dir / "apriori_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        return RuleStore(
            num_items=snapshot.manifest.num_items,
            rule_pairs=rule_pairs,
            min_lift=self.min_lift,
        )


def load_rule_store(snapshot_dir: Path, min_lift: float = 1.0) -> RuleStore:
    """Load pre-mined Apriori rules from snapshot directory."""
    rule_file = snapshot_dir / "apriori_rules.npz"
    if not rule_file.exists():
        return RuleStore(num_items=5200, rule_pairs=[], min_lift=min_lift)

    data = np.load(rule_file)
    rules_arr = data["rules"]
    rule_pairs = [(int(r[0]), int(r[1]), float(r[2])) for r in rules_arr]
    return RuleStore(num_items=5200, rule_pairs=rule_pairs, min_lift=min_lift)
