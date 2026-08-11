"""Cold-start validity and ranking metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import torch

from ai_service.config import Settings
from ai_service.contracts import ColdParityReport
from ai_service.data.history import build_user_profile_vectors
from ai_service.data.quality import filter_event_origin
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import DataIntegrityError
from ai_service.evaluation.full_catalog import EvaluationResult, PreparedEvaluationSplit
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class ColdStartReport:
    num_cold_items: int
    num_cold_items_with_test_purchase: int
    ground_truth_coverage: float
    recommendation_coverage: float
    hr_at_k: float
    ndcg_at_k: float
    num_eligible_users: int


def evaluate_cold_start(
    result: EvaluationResult,
    snapshot: Snapshot,
    rule_store: RuleStore,
) -> ColdStartReport:
    cold = set(snapshot.cold_item_ids)
    test_purchases = snapshot.test_df[snapshot.test_df.event_type == "purchase"]
    cold_rows = test_purchases[test_purchases.internal_product_id.isin(cold)]
    covered = set(cold_rows.internal_product_id.astype(int))
    if covered != cold:
        raise DataIntegrityError(
            f"cold benchmark invalid: {len(covered)}/{len(cold)} items have test purchase"
        )
    for item in cold:
        row_start = int(rule_store.crow_indices[item])
        row_end = int(rule_store.crow_indices[item + 1])
        if row_start != row_end or bool((rule_store.col_indices == item).any()):
            raise DataIntegrityError("cold item exists in Apriori rules")
    truth_by_user = cold_rows.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
    hits: list[float] = []
    ndcgs: list[float] = []
    recommended: set[int] = set()
    for user, truth in truth_by_user.items():
        top = result.top_k_by_user.get(cast(int, user), ())
        recommended.update(cold & set(top))
        relevant_ranks = [rank + 1 for rank, item in enumerate(top) if item in truth]
        hits.append(float(bool(relevant_ranks)))
        dcg = sum(1.0 / np.log2(rank + 1) for rank in relevant_ranks)
        ideal = sum(
            1.0 / np.log2(rank + 1) for rank in range(1, min(len(truth), result.report.k) + 1)
        )
        ndcgs.append(float(dcg / ideal if ideal else 0.0))
    return ColdStartReport(
        num_cold_items=len(cold),
        num_cold_items_with_test_purchase=len(covered),
        ground_truth_coverage=len(covered) / len(cold) if cold else 1.0,
        recommendation_coverage=len(recommended) / len(cold) if cold else 1.0,
        hr_at_k=float(np.mean(hits)) if hits else 0.0,
        ndcg_at_k=float(np.mean(ndcgs)) if ndcgs else 0.0,
        num_eligible_users=len(truth_by_user),
    )


def evaluate_cold_parity(
    hybrid_model: HybridTwoTowerModel,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    *,
    prepared_split: PreparedEvaluationSplit,
    settings: Settings,
    device: torch.device,
) -> ColdParityReport:
    if prepared_split.split.value != "test":
        raise DataIntegrityError("cold parity requires a prepared test split")
    cold_ids = np.asarray(snapshot.cold_item_ids, dtype=np.int64)
    expected_cold = settings.data.num_cold_items
    if len(cold_ids) != expected_cold:
        raise DataIntegrityError(
            "cold benchmark invalid: expected exactly "
            f"{expected_cold} cold items, got {len(cold_ids)}"
        )

    for item in cold_ids:
        row_start = int(rule_store.crow_indices[item])
        row_end = int(rule_store.crow_indices[item + 1])
        if row_start != row_end or bool((rule_store.col_indices == item).any()):
            raise DataIntegrityError("cold item exists in Apriori rules")

    required_test_columns = {
        "event_type",
        "event_origin",
        "internal_user_id",
        "internal_product_id",
    }
    if not required_test_columns.issubset(snapshot.test_df.columns):
        raise DataIntegrityError(
            "cold benchmark invalid: expected at least 250 cohort users "
            "with a cold-start fixture purchase"
        )
    cold_test = filter_event_origin(snapshot.test_df, "cold_start")
    cold_test = cold_test[
        (cold_test.event_type == "purchase") & cold_test.internal_product_id.isin(cold_ids)
    ]
    eligible_users = sorted(
        {int(user) for user in cold_test.internal_user_id},
        key=lambda user: int(snapshot.raw_user_map[user]),
    )
    if len(eligible_users) < expected_cold:
        raise DataIntegrityError(
            f"cold benchmark invalid: expected at least {expected_cold} cohort users "
            "with a cold-start fixture purchase"
        )
    cohort_users = np.asarray(eligible_users[:expected_cold], dtype=np.int64)

    # Get latest organic train+val prior purchase context for cohort users
    history = prepared_split.history_events
    cohort_contexts = np.array(
        [prepared_split.latest_prior_purchase_contexts.get(int(u), -1) for u in cohort_users],
        dtype=np.int64,
    )

    candidate_matrix = np.broadcast_to(cold_ids[None, :], (len(cohort_users), len(cold_ids)))
    wide_values, rule_present = rule_store.batch_lookup(cohort_contexts, candidate_matrix)
    wide_tensor = torch.from_numpy(wide_values).to(device)
    present_tensor = torch.from_numpy(rule_present).to(device)

    catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
    all_items = torch.arange(snapshot.manifest.num_items, dtype=torch.int64, device=device)
    cold_mask = torch.zeros(snapshot.manifest.num_items, dtype=torch.bool, device=device)
    cold_mask[torch.from_numpy(cold_ids).to(device)] = True
    with torch.no_grad():
        item_vectors = (
            hybrid_model.to(device)
            .eval()
            .encode_items(
                torch.from_numpy(np.asarray(embeddings, dtype=np.float32)).to(device),
                torch.from_numpy(catalog.internal_leaf_category_id.to_numpy(np.int64)).to(device),
                torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(device),
                item_idx=all_items,
                is_cold=cold_mask,
            )
        )
        profiles = build_user_profile_vectors(
            hybrid_model,
            snapshot,
            item_vectors,
            history,
            max_history_items=settings.train.max_history_items,
            device=device,
        )
        user_tensor = torch.from_numpy(cohort_users).to(device)
        personas = torch.tensor(
            [
                snapshot.persona_map.get(snapshot.raw_user_map[int(user)], 0)
                for user in cohort_users
            ],
            dtype=torch.int64,
            device=device,
        )
        profile_batch = profiles[user_tensor]
        user_vectors = hybrid_model.encode_user(
            user_tensor,
            personas,
            history_vector=profile_batch,
            history_present=torch.linalg.vector_norm(profile_batch, dim=-1) > 0,
        )
        deep_scores = (
            torch.matmul(user_vectors, item_vectors[cold_ids].T) / hybrid_model._temperature
        )
        wide_scores = hybrid_model.wide_layer(wide_tensor, present_tensor)
        hybrid_scores = deep_scores + wide_scores

    deep_np = deep_scores.cpu().numpy()
    hybrid_np = hybrid_scores.cpu().numpy()
    wide_np = wide_scores.cpu().numpy()
    max_abs_wide = float(np.max(np.abs(wide_np)))
    max_abs_diff = float(np.max(np.abs(hybrid_np - deep_np)))
    raw_ids = np.asarray([snapshot.raw_product_map[int(item)] for item in cold_ids], dtype=np.int64)
    truth_by_user = cold_test.groupby("internal_user_id").internal_product_id.apply(set).to_dict()

    def _metrics(scores: np.ndarray) -> tuple[float, float, list[np.ndarray]]:
        hits: list[float] = []
        ndcgs: list[float] = []
        orders: list[np.ndarray] = []
        for row, user in enumerate(cohort_users):
            order = np.lexsort((raw_ids, -scores[row]))
            orders.append(order)
            top = cold_ids[order[: settings.eval.k]]
            truth = {int(item) for item in truth_by_user.get(int(user), set())}
            ranks = [rank + 1 for rank, item in enumerate(top) if int(item) in truth]
            hits.append(float(bool(ranks)))
            dcg = sum(1.0 / np.log2(rank + 1) for rank in ranks)
            ideal = sum(
                1.0 / np.log2(rank + 1) for rank in range(1, min(len(truth), settings.eval.k) + 1)
            )
            ndcgs.append(float(dcg / ideal if ideal else 0.0))
        return float(np.mean(hits)), float(np.mean(ndcgs)), orders

    deep_hr, deep_ndcg, deep_orders = _metrics(deep_np)
    hybrid_hr, hybrid_ndcg, hybrid_orders = _metrics(hybrid_np)
    order_equality = all(
        np.array_equal(left, right) for left, right in zip(deep_orders, hybrid_orders, strict=True)
    )
    passed = bool(
        max_abs_wide <= settings.eval.wide_zero_atol
        and max_abs_diff <= settings.eval.cold_score_atol
        and order_equality
        and abs(deep_hr - hybrid_hr) <= 1e-6
        and abs(deep_ndcg - hybrid_ndcg) <= 1e-6
    )

    return ColdParityReport(
        max_abs_wide_logit=max_abs_wide,
        max_abs_hybrid_minus_deep=max_abs_diff,
        cold_only_order_equality=order_equality,
        deep_cold_hr_at_k=deep_hr,
        deep_cold_ndcg_at_k=deep_ndcg,
        hybrid_cold_hr_at_k=hybrid_hr,
        hybrid_cold_ndcg_at_k=hybrid_ndcg,
        passed=passed,
        num_cold_items=expected_cold,
        num_cohort_users=expected_cold,
        wide_zero_atol=settings.eval.wide_zero_atol,
        cold_score_atol=settings.eval.cold_score_atol,
    )
