"""Full-Catalog GPU Evaluator for Zero-Sampling Evaluation."""

from dataclasses import dataclass, asdict
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import torch

from ai_service.config import Settings
from ai_service.contracts import ModelVariant
from ai_service.data.snapshot import Snapshot
from ai_service.data.rules import RuleStore, load_rule_store
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


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


class FullCatalogEvaluator:
    """Full-Catalog Zero-Sampling Evaluator."""

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()
        self.settings = settings

    @torch.no_grad()
    def evaluate(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        split: str = "test",
        k: int = 10,
        variant: ModelVariant = ModelVariant.HYBRID,
        rule_store: Optional[RuleStore] = None,
        device: Optional[torch.device] = None,
    ) -> EvaluationReport:
        t0 = time.time()
        if device is None:
            device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

        model.eval()
        model.to(device)

        # Do NOT auto-load Wide rules if variant is DEEP_ONLY or RANDOM
        include_wide = (variant == ModelVariant.HYBRID or variant == ModelVariant.NOISY_HYBRID or variant == ModelVariant.WIDE_ONLY)

        if include_wide and rule_store is None:
            try:
                rule_store = load_rule_store(snapshot.snapshot_dir)
            except Exception:
                rule_store = None

        catalog_df = snapshot.catalog_df.sort_values(by="internal_product_id").reset_index(drop=True)
        num_items = len(catalog_df)

        cat_ids = torch.tensor(catalog_df["internal_leaf_category_id"].values, dtype=torch.long, device=device)
        price_ids = torch.tensor(catalog_df["price_bucket_id"].values, dtype=torch.long, device=device)

        sbert_path = snapshot.snapshot_dir / "sbert_embeddings.npy"
        if sbert_path.exists():
            sbert_np = np.load(sbert_path)
        else:
            sbert_np = np.zeros((num_items, 768), dtype=np.float32)
        sbert_tensor = torch.tensor(sbert_np, dtype=torch.float32, device=device)

        # Precompute item vectors [num_items, 64]
        item_vectors = model.encode_items(sbert_tensor, cat_ids, price_ids)

        # Select split events
        if split == "val":
            split_df = snapshot.val_df
        elif split == "test":
            split_df = snapshot.test_df
        else:
            split_df = snapshot.train_df

        # Ground truth positives per user in target split
        ground_truth: Dict[int, Set[int]] = split_df.groupby("internal_user_id")["internal_product_id"].apply(set).to_dict()
        
        # History positives per user to mask (Train + Val if evaluating Test)
        if split == "test":
            history_df = pd.concat([snapshot.train_df, snapshot.val_df])
        else:
            history_df = snapshot.train_df
        history_positives: Dict[int, Set[int]] = history_df.groupby("internal_user_id")["internal_product_id"].apply(set).to_dict()

        eval_users = sorted(ground_truth.keys())
        if len(eval_users) == 0:
            return EvaluationReport(
                split=split, num_eval_users=0, num_catalog_items=num_items,
                hr10=0.0, ndcg10=0.0, gauc=0.0, avg_latency_ms=0.0, total_eval_time_sec=0.0
            )

        user_tensor = torch.tensor([u for u in eval_users], dtype=torch.long, device=device)
        raw_uids = [snapshot.raw_user_map.get(u, 0) for u in eval_users]
        persona_tensor = torch.tensor([snapshot.persona_map.get(ru, 0) for ru in raw_uids], dtype=torch.long, device=device)

        user_vectors = model.encode_user(user_tensor, persona_tensor) # [num_eval_users, 64]

        # Compute Deep scores matrix [num_eval_users, num_items]
        deep_scores = torch.matmul(user_vectors, item_vectors.T) / model.tau

        all_scores = deep_scores.cpu().numpy()

        # Add Wide scores if active
        if include_wide and rule_store is not None:
            # Find context item for each eval user
            user_last_item: Dict[int, int] = {}
            for u, p in zip(history_df["internal_user_id"].values, history_df["internal_product_id"].values):
                user_last_item[int(u)] = int(p)

            for u_idx, u in enumerate(eval_users):
                if u in user_last_item:
                    ctx_item = user_last_item[u]
                    for cand_item in range(num_items):
                        log_lift = rule_store.lookup(ctx_item, cand_item)
                        if log_lift > 0.0:
                            # Forward through wide layer
                            lift_t = torch.tensor([[log_lift]], dtype=torch.float32, device=device)
                            w_score = model.wide_layer(lift_t).item()
                            all_scores[u_idx, cand_item] += w_score

        hits: List[int] = []
        ndcgs: List[float] = []
        aucs: List[float] = []

        for u_idx, u in enumerate(eval_users):
            pos_set = ground_truth[u]
            hist_set = history_positives.get(u, set())

            scores = all_scores[u_idx].copy()
            # Mask historical items
            for item in hist_set:
                if item not in pos_set and item < num_items:
                    scores[item] = -1e9

            # Rank items
            ranked_indices = np.argsort(-scores)
            top_k = ranked_indices[:k]

            # Hit Rate@K
            hit = 1 if any(item in pos_set for item in top_k) else 0
            hits.append(hit)

            # NDCG@K
            pos_ranks = []
            for rank_idx, item in enumerate(top_k):
                if item in pos_set:
                    pos_ranks.append(rank_idx + 1)
            dcg = compute_user_dcg(np.array(pos_ranks))
            idcg = compute_user_idcg(len(pos_set), k=k)
            ndcg = (dcg / idcg) if idcg > 0 else 0.0
            ndcgs.append(ndcg)

            # Per-user GAUC
            pos_indices = np.array([i for i in pos_set if i < num_items])
            neg_indices = np.array([i for i in range(num_items) if i not in pos_set and i not in hist_set])
            if len(pos_indices) > 0 and len(neg_indices) > 0:
                user_auc = compute_user_auc(scores[pos_indices], scores[neg_indices])
                if user_auc is not None:
                    aucs.append(user_auc)

        total_time = time.time() - t0
        avg_latency = (total_time / len(eval_users)) * 1000.0

        return EvaluationReport(
            split=split,
            num_eval_users=len(eval_users),
            num_catalog_items=num_items,
            hr10=float(np.mean(hits)),
            ndcg10=float(np.mean(ndcgs)),
            gauc=float(np.mean(aucs)) if len(aucs) > 0 else 0.5,
            avg_latency_ms=avg_latency,
            total_eval_time_sec=total_time,
        )
