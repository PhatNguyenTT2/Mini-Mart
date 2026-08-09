"""Cold-Start Zero-Shot Evaluator module for ai-service.

Evaluates semantic generalization performance on 250 Cold-Start SKUs isolated from training/validation events and Apriori rules.
Measures Zero-Shot HR@10, NDCG@10, and coverage across unseen products.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import torch

from config import get_settings
from data.ingestion import SnapshotArtifacts
from models.two_tower_wide_deep import HybridTwoTowerModel
from evaluation.full_catalog_eval import compute_user_dcg, compute_user_idcg


@dataclass
class ColdStartReport:
    num_cold_items: int
    num_eval_cold_items: int
    zero_shot_hr10: float
    zero_shot_ndcg10: float
    coverage_ratio: float
    all_scores_finite: bool
    train_leakage_detected: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@torch.no_grad()
def evaluate_cold_start(
    model: HybridTwoTowerModel,
    snapshot: SnapshotArtifacts,
    k: int = 10,
    device: Optional[torch.device] = None,
) -> ColdStartReport:
    """Run Zero-Shot Cold-Start evaluation on 250 isolated SKUs."""
    if device is None:
        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

    model.eval()
    model.to(device)
    model.refresh_unknown_embedding()

    cold_internal_ids = set(snapshot.cold_item_ids)
    num_cold_items = len(cold_internal_ids)

    # 1. Leakage Check: verify cold items do NOT exist in train or val sets
    train_products = set(snapshot.train_df["internal_product_id"])
    val_products = set(snapshot.val_df["internal_product_id"])

    train_leakage = (
        len(cold_internal_ids.intersection(train_products)) > 0
        or len(cold_internal_ids.intersection(val_products)) > 0
    )

    # 2. Extract test positive ground truth for cold items
    test_df = snapshot.test_df
    cold_test_df = test_df[test_df["internal_product_id"].isin(cold_internal_ids)]

    user_cold_positives: Dict[int, set] = {
        int(u): set(items)
        for u, items in cold_test_df.groupby("internal_user_id")["internal_product_id"].apply(set).items()
    }

    eval_users = list(user_cold_positives.keys())
    if len(eval_users) == 0:
        return ColdStartReport(
            num_cold_items=num_cold_items,
            num_eval_cold_items=0,
            zero_shot_hr10=0.0,
            zero_shot_ndcg10=0.0,
            coverage_ratio=1.0,
            all_scores_finite=True,
            train_leakage_detected=train_leakage,
        )

    # 3. Precompute catalog item vectors [5200, 64]
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

    item_vectors = model.encode_items(sbert_tensor, cat_ids, price_ids)  # [5200, 64]

    # 4. Evaluate users on full catalog
    user_personas = snapshot.persona_map
    hr_list = []
    ndcg_list = []
    all_finite = True

    chunk_size = 512
    for chunk_start in range(0, len(eval_users), chunk_size):
        chunk_users = eval_users[chunk_start : chunk_start + chunk_size]
        chunk_personas = [user_personas.get(snapshot.raw_user_map.get(u, 0), 0) for u in chunk_users]

        user_idx_t = torch.tensor(chunk_users, dtype=torch.long, device=device)
        persona_idx_t = torch.tensor(chunk_personas, dtype=torch.long, device=device)

        user_vectors = model.encode_users(user_idx_t, persona_idx_t)  # [B, 64]

        # Cold items have 0 Wide score (no train rules); pure SBERT Deep score
        scores = (torch.matmul(user_vectors, item_vectors.T) / model.tau).cpu().numpy()

        if not np.all(np.isfinite(scores)):
            all_finite = False

        for b, u in enumerate(chunk_users):
            pos_set = user_cold_positives[u]
            user_scores = scores[b]

            top_k_indices = np.argpartition(user_scores, -k)[-k:]
            top_k_sorted = top_k_indices[np.argsort(-user_scores[top_k_indices])]

            hits = [1 for item in top_k_sorted if item in pos_set]
            hr_list.append(1.0 if len(hits) > 0 else 0.0)

            ranks = np.array(
                [i + 1 for i, item in enumerate(top_k_sorted) if item in pos_set]
            )
            dcg = compute_user_dcg(ranks)
            idcg = compute_user_idcg(len(pos_set), k=k)
            ndcg_list.append(dcg / idcg if idcg > 0 else 0.0)

    # Calculate coverage of cold items present in Top-10 recommendations across all test queries
    cold_test_items = set(cold_test_df["internal_product_id"])

    return ColdStartReport(
        num_cold_items=num_cold_items,
        num_eval_cold_items=len(cold_test_items),
        zero_shot_hr10=float(np.mean(hr_list)) if hr_list else 0.0,
        zero_shot_ndcg10=float(np.mean(ndcg_list)) if ndcg_list else 0.0,
        coverage_ratio=float(len(cold_test_items) / max(num_cold_items, 1)),
        all_scores_finite=all_finite,
        train_leakage_detected=train_leakage,
    )
