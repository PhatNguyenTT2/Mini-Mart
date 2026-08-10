"""Semantic-trap ranking acceptance gate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import DataIntegrityError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class TrapResult:
    trap_id: int
    anchor_product_id: int
    target_product_ids: tuple[int, ...]
    deep_control_rank: int
    hybrid_deep_ablation_rank: int
    hybrid_rank: int
    passed_top_k: bool
    improved_over_deep: bool
    passed: bool


@dataclass(frozen=True)
class SemanticTrapReport:
    passed: int
    total: int
    all_passed: bool
    results: tuple[TrapResult, ...]


def _rank(scores: np.ndarray, target_indices: list[int], raw_ids: np.ndarray) -> int:
    order = np.lexsort((raw_ids, -scores))
    positions = np.empty(len(order), dtype=np.int64)
    positions[order] = np.arange(1, len(order) + 1)
    return int(min(positions[target_indices]))


@torch.no_grad()
def evaluate_semantic_traps(
    hybrid_model: HybridTwoTowerModel,
    deep_model: HybridTwoTowerModel | None,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    fixture_path: Path,
    *,
    k: int = 10,
    device: str | torch.device = "cpu",
) -> SemanticTrapReport:
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    device = torch.device(device)
    hybrid_model = hybrid_model.to(device).eval()
    if deep_model is None:
        deep_model = hybrid_model
    else:
        deep_model = deep_model.to(device).eval()

    catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
    item_ids = torch.arange(snapshot.manifest.num_items, dtype=torch.int64, device=device)
    cold_mask = torch.zeros(snapshot.manifest.num_items, dtype=torch.bool, device=device)
    if snapshot.cold_item_ids:
        cold_mask[torch.tensor(snapshot.cold_item_ids, dtype=torch.int64, device=device)] = True

    hybrid_item_vectors = hybrid_model.encode_items(
        torch.from_numpy(np.array(embeddings, dtype=np.float32, copy=True)).to(device),
        torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)).to(device),
        torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(device),
        item_idx=item_ids,
        is_cold=cold_mask,
    )
    deep_item_vectors = deep_model.encode_items(
        torch.from_numpy(np.array(embeddings, dtype=np.float32, copy=True)).to(device),
        torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)).to(device),
        torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(device),
        item_idx=item_ids,
        is_cold=cold_mask,
    )
    raw_ids = np.asarray(
        [snapshot.raw_product_map[index] for index in range(snapshot.manifest.num_items)],
        dtype=np.int64,
    )
    results: list[TrapResult] = []
    all_candidates = np.arange(snapshot.manifest.num_items, dtype=np.int64).reshape(1, -1)
    for fixture in fixtures:
        anchor_raw = int(fixture["anchor_product_id"])
        target_raw = [int(value) for value in fixture["target_product_ids"]]
        if anchor_raw not in snapshot.product_map or any(
            value not in snapshot.product_map for value in target_raw
        ):
            raise DataIntegrityError(
                f"semantic trap {fixture['trap_id']} references missing product"
            )
        anchor = snapshot.product_map[anchor_raw]
        targets = [snapshot.product_map[value] for value in target_raw]

        deep_control_scores = (
            torch.matmul(deep_item_vectors[anchor], deep_item_vectors.T).cpu().numpy()
            / deep_model.tau
        )
        hybrid_deep_scores = (
            torch.matmul(hybrid_item_vectors[anchor], hybrid_item_vectors.T).cpu().numpy()
            / hybrid_model.tau
        )

        wide_values, present = rule_store.batch_lookup(
            np.asarray([anchor], dtype=np.int64), all_candidates
        )
        wide_scores = (
            hybrid_model.wide_layer(
                torch.from_numpy(wide_values).to(device), torch.from_numpy(present).to(device)
            )[0]
            .cpu()
            .numpy()
        )

        hybrid_scores = hybrid_deep_scores + wide_scores

        deep_control_rank = _rank(deep_control_scores, targets, raw_ids)
        hybrid_deep_ablation_rank = _rank(hybrid_deep_scores, targets, raw_ids)
        hybrid_rank = _rank(hybrid_scores, targets, raw_ids)

        passed_top_k = hybrid_rank <= k
        improved = hybrid_rank < deep_control_rank
        passed = passed_top_k and improved

        results.append(
            TrapResult(
                trap_id=int(fixture["trap_id"]),
                anchor_product_id=anchor_raw,
                target_product_ids=tuple(target_raw),
                deep_control_rank=deep_control_rank,
                hybrid_deep_ablation_rank=hybrid_deep_ablation_rank,
                hybrid_rank=hybrid_rank,
                passed_top_k=passed_top_k,
                improved_over_deep=improved,
                passed=passed,
            )
        )

    passed_count = sum(result.passed for result in results)
    total_count = len(results)
    return SemanticTrapReport(
        passed=passed_count,
        total=total_count,
        all_passed=passed_count == total_count,
        results=tuple(results),
    )
