"""Full-Catalog GPU Evaluator module for ai-service.

Performs zero-sampling Full-Catalog Ranking evaluation (5,000 users x 5,200 SKUs = 26,000,000 predictions per pass) using GPU matrix multiplication (U * V^T / tau) and sparse Wide rule scatter addition.
Computes Hit Rate@10, NDCG@10, and per-user Group AUC (GAUC).
"""

from dataclasses import dataclass, asdict
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import torch

from config import get_settings, Settings
from data.ingestion import SnapshotArtifacts
from data.apriori_rules import RuleStore, load_rule_store
from models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass
class EvaluationReport:
    split: str
    num_eval_users: int
    num_catalog_items: int
    hr10: float
    ndcg10: float
    gauc: float
    avg_latency_ms: float
    total_eval_time_sec: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_user_auc(pos_scores: np.ndarray, neg_scores: np.ndarray) -> Optional[float]:
    """Compute exact per-user ROC-AUC score between positive and negative item scores."""
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return None

    # Count pairs where pos > neg (1.0) and pos == neg (0.5)
    # Using broadcast matrix comparison
    diff = pos_scores[:, None] - neg_scores[None, :]
    wins = np.sum(diff > 0)
    ties = np.sum(diff == 0)
    total_pairs = len(pos_scores) * len(neg_scores)

    if total_pairs == 0:
        return None
    return float((wins + 0.5 * ties) / total_pairs)


def compute_user_dcg(ranks: np.ndarray) -> float:
    """Compute DCG@10 given 1-based ranks of relevant positive items in top 10."""
    valid_ranks = ranks[ranks <= 10]
    if len(valid_ranks) == 0:
        return 0.0
    return float(np.sum(1.0 / np.log2(valid_ranks + 1)))


def compute_user_idcg(num_positives: int, k: int = 10) -> float:
    """Compute Ideal DCG@10 for a given number of relevant positive items."""
    n = min(num_positives, k)
    if n <= 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float(np.sum(1.0 / np.log2(ranks + 1)))


@torch.no_grad()
def evaluate_full_catalog(
    model: HybridTwoTowerModel,
    snapshot: SnapshotArtifacts,
    split: str = "test",
    k: int = 10,
    rule_store: Optional[RuleStore] = None,
    device: Optional[torch.device] = None,
) -> EvaluationReport:
    """Run full-catalog ranking evaluation across all test/val users."""
    t0 = time.time()
    if device is None:
        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

    model.eval()
    model.to(device)
    model.refresh_unknown_embedding()

    if rule_store is None:
        try:
            rule_store = load_rule_store(snapshot.snapshot_dir)
        except Exception:
            rule_store = None

    # 1. Precompute catalog item vectors [5200, 64]
    catalog_df = snapshot.catalog_df.sort_values(by="internal_product_id").reset_index(drop=True)
    num_items = len(catalog_df)

    cat_ids = torch.tensor(
        catalog_df["internal_leaf_category_id"].values, dtype=torch.long, device=device
    )
    price_ids = torch.tensor(
        catalog_df["price_bucket_id"].values, dtype=torch.long, device=device
    )

    sbert_path = snapshot.snapshot_dir / "sbert_embeddings.npy"
    if sbert_path.exists():
        sbert_arr = np.load(sbert_path)
        sbert_tensor = torch.tensor(sbert_arr, dtype=torch.float32, device=device)
    else:
        sbert_tensor = torch.randn(num_items, 768, dtype=torch.float32, device=device)

    # Encode all catalog items -> [5200, 64]
    item_vectors = model.encode_items(sbert_tensor, cat_ids, price_ids)  # [5200, 64]

    # 2. Extract split positive ground truth per user
    split_df = (
        snapshot.test_df
        if split == "test"
        else (snapshot.val_df if split == "val" else snapshot.train_df)
    )

    user_split_positives: Dict[int, set] = {
        int(u): set(items)
        for u, items in split_df.groupby("internal_user_id")["internal_product_id"].apply(set).items()
    }

    # Train positive items to mask out from evaluation (except split positives)
    train_positives: Dict[int, set] = {
        int(u): set(items)
        for u, items in snapshot.train_df.groupby("internal_user_id")["internal_product_id"].apply(set).items()
    }

    # Map user personas
    user_personas = snapshot.persona_map

    # Unique evaluation users
    eval_user_ids = sorted(list(user_split_positives.keys()))
    num_eval_users = len(eval_user_ids)

    hr_list = []
    ndcg_list = []
    auc_list = []
    user_latencies_ms = []

    # Pre-build user last prior context item map (O(N) vectorized C-speed dict zip)
    user_ids_arr = snapshot.train_df["internal_user_id"].values
    prod_ids_arr = snapshot.train_df["internal_product_id"].values
    user_last_context: Dict[int, int] = dict(zip(user_ids_arr, prod_ids_arr))

    # Evaluate in user chunks of 512
    chunk_size = 512
    for chunk_start in range(0, num_eval_users, chunk_size):
        chunk_users = eval_user_ids[chunk_start : chunk_start + chunk_size]
        chunk_personas = [user_personas.get(snapshot.raw_user_map.get(u, 0), 0) for u in chunk_users]

        user_idx_t = torch.tensor(chunk_users, dtype=torch.long, device=device)
        persona_idx_t = torch.tensor(chunk_personas, dtype=torch.long, device=device)

        t_user_start = time.time()
        # Encode user chunk -> [B, 64]
        user_vectors = model.encode_users(user_idx_t, persona_idx_t)  # [B, 64]

        # GPU Matrix Multiplication: S_deep = (U * V^T) / tau -> [B, 5200]
        deep_scores = torch.matmul(user_vectors, item_vectors.T) / model.tau  # [B, 5200]

        # Wide score scatter addition if rule_store available
        joint_scores = deep_scores.clone()
        if rule_store is not None:
            # Look up last prior context item for each user in chunk
            for b, u in enumerate(chunk_users):
                ctx_item = user_last_context.get(u, 0)
                if ctx_item > 0:
                    # Vectorized lookup across 5,200 items
                    lifts = rule_store.lookup_batch(ctx_item, np.arange(num_items))
                    nonzero_indices = np.where(lifts > 0)[0]
                    if len(nonzero_indices) > 0:
                        lifts_t = torch.tensor(
                            lifts[nonzero_indices], dtype=torch.float32, device=device
                        ).unsqueeze(-1)
                        wide_contribs = model.wide_layer(lifts_t)
                        joint_scores[b, nonzero_indices] += wide_contribs

        t_user_elapsed = (time.time() - t_user_start) * 1000.0 / len(chunk_users)

        # Process per-user metrics on CPU
        scores_np = joint_scores.cpu().numpy()

        for b, u in enumerate(chunk_users):
            user_latencies_ms.append(t_user_elapsed)
            pos_set = user_split_positives[u]
            if len(pos_set) == 0:
                continue

            user_scores = scores_np[b].copy()

            # Mask train positives that are NOT in current test set with -infinity
            seen_to_mask = train_positives.get(u, set()) - pos_set
            if len(seen_to_mask) > 0:
                mask_indices = np.array(list(seen_to_mask), dtype=int)
                user_scores[mask_indices] = -1e9

            # Top-K ranking
            top_k_indices = np.argpartition(user_scores, -k)[-k:]
            top_k_sorted = top_k_indices[np.argsort(-user_scores[top_k_indices])]

            # HR@10
            hits = [1 for item in top_k_sorted if item in pos_set]
            hr_list.append(1.0 if len(hits) > 0 else 0.0)

            # NDCG@10
            ranks = np.array(
                [i + 1 for i, item in enumerate(top_k_sorted) if item in pos_set]
            )
            dcg = compute_user_dcg(ranks)
            idcg = compute_user_idcg(len(pos_set), k=k)
            ndcg_list.append(dcg / idcg if idcg > 0 else 0.0)

            # GAUC: Vectorized boolean mask for negative item selection
            pos_indices = np.array(list(pos_set), dtype=int)
            neg_mask = np.ones(num_items, dtype=bool)
            neg_mask[pos_indices] = False
            if len(seen_to_mask) > 0:
                neg_mask[mask_indices] = False
            neg_indices = np.where(neg_mask)[0]

            auc = compute_user_auc(user_scores[pos_indices], user_scores[neg_indices])
            if auc is not None:
                auc_list.append(auc)

    total_time = time.time() - t0

    return EvaluationReport(
        split=split,
        num_eval_users=num_eval_users,
        num_catalog_items=num_items,
        hr10=float(np.mean(hr_list)) if hr_list else 0.0,
        ndcg10=float(np.mean(ndcg_list)) if ndcg_list else 0.0,
        gauc=float(np.mean(auc_list)) if auc_list else 0.5,
        avg_latency_ms=float(np.mean(user_latencies_ms)) if user_latencies_ms else 0.0,
        total_eval_time_sec=float(total_time),
    )
