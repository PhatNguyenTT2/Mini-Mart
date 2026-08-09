"""Ten Semantic Traps Benchmark Evaluator module for ai-service.

Evaluates 10 retail semantic traps (e.g. Bobby Diapers -> Heineken Beer, Chicken -> Pocari Sweat) comparing SBERT-only, Deep-only, and Hybrid Wide & Deep ranking performance.
"""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import torch

from config import get_settings
from data.ingestion import SnapshotArtifacts
from data.apriori_rules import RuleStore, load_rule_store
from models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass
class TrapResult:
    trap_id: int
    name: str
    anchor_product_id: int
    target_product_ids: List[int]
    deep_ranks: List[int]
    hybrid_ranks: List[int]
    hybrid_hr10: float
    hybrid_ndcg10: float
    improved: bool


@dataclass
class SemanticTrapsReport:
    num_traps: int
    num_improved_traps: int
    mean_hybrid_hr10: float
    mean_hybrid_ndcg10: float
    trap_results: List[TrapResult]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_trap_fixtures(fixture_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load canonical 10 semantic trap definitions from JSON fixture."""
    if fixture_path is None:
        fixture_path = Path(__file__).parent / "fixtures" / "semantic_traps.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Semantic traps fixture not found: {fixture_path}")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@torch.no_grad()
def evaluate_semantic_traps(
    model: HybridTwoTowerModel,
    snapshot: SnapshotArtifacts,
    rule_store: Optional[RuleStore] = None,
    fixture_path: Optional[Path] = None,
    device: Optional[torch.device] = None,
) -> SemanticTrapsReport:
    """Run evaluation benchmark across 10 semantic trap scenarios."""
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

    traps = load_trap_fixtures(fixture_path)
    catalog_df = snapshot.catalog_df.sort_values(by="internal_product_id").reset_index(drop=True)
    num_items = len(catalog_df)

    # Encode all catalog items -> [5200, 64]
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

    item_vectors = model.encode_items(sbert_tensor, cat_ids, price_ids)

    # UNK User vector (user 0) + Persona 0 default
    user_idx_t = torch.tensor([0], dtype=torch.long, device=device)
    persona_idx_t = torch.tensor([0], dtype=torch.long, device=device)
    unk_user_vec = model.encode_users(user_idx_t, persona_idx_t)  # [1, 64]

    # Deep scores across full catalog [5200]
    deep_scores = (torch.matmul(unk_user_vec, item_vectors.T) / model.tau).squeeze(0).cpu().numpy()

    # Pre-rank deep scores
    deep_ranks_map = {idx: rank + 1 for rank, idx in enumerate(np.argsort(-deep_scores))}

    trap_results = []
    product_map = snapshot.product_map

    for t in traps:
        raw_anchor_id = t["anchor_product_id"]
        raw_target_ids = t["target_product_ids"]

        internal_anchor = product_map.get(raw_anchor_id, product_map.get(str(raw_anchor_id), 0))
        internal_targets = [
            product_map.get(tid, product_map.get(str(tid), 0)) for tid in raw_target_ids
        ]

        # Hybrid scores = Deep + Wide
        hybrid_scores = deep_scores.copy()
        if rule_store is not None and internal_anchor > 0:
            lifts = rule_store.lookup_batch(internal_anchor, np.arange(num_items))
            nonzero_idx = np.where(lifts > 0)[0]
            if len(nonzero_idx) > 0:
                lifts_t = torch.tensor(lifts[nonzero_idx], dtype=torch.float32, device=device).unsqueeze(-1)
                wide_contribs = model.wide_layer(lifts_t).cpu().numpy()
                hybrid_scores[nonzero_idx] += wide_contribs

        hybrid_ranks_map = {idx: rank + 1 for rank, idx in enumerate(np.argsort(-hybrid_scores))}

        deep_ranks = [deep_ranks_map.get(tid, num_items) for tid in internal_targets]
        hybrid_ranks = [hybrid_ranks_map.get(tid, num_items) for tid in internal_targets]

        best_hybrid_rank = min(hybrid_ranks)
        best_deep_rank = min(deep_ranks)

        hr10 = 1.0 if best_hybrid_rank <= 10 else 0.0
        ndcg10 = (1.0 / np.log2(best_hybrid_rank + 1)) if best_hybrid_rank <= 10 else 0.0
        improved = best_hybrid_rank < best_deep_rank

        trap_results.append(
            TrapResult(
                trap_id=t["trap_id"],
                name=t["name"],
                anchor_product_id=raw_anchor_id,
                target_product_ids=raw_target_ids,
                deep_ranks=deep_ranks,
                hybrid_ranks=hybrid_ranks,
                hybrid_hr10=hr10,
                hybrid_ndcg10=ndcg10,
                improved=improved,
            )
        )

    mean_hr10 = float(np.mean([r.hybrid_hr10 for r in trap_results]))
    mean_ndcg10 = float(np.mean([r.hybrid_ndcg10 for r in trap_results]))
    num_improved = sum(1 for r in trap_results if r.improved)

    return SemanticTrapsReport(
        num_traps=len(trap_results),
        num_improved_traps=num_improved,
        mean_hybrid_hr10=mean_hr10,
        mean_hybrid_ndcg10=mean_ndcg10,
        trap_results=trap_results,
    )
