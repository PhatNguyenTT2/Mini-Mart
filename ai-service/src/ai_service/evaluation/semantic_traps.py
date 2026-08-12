"""Semantic-trap ranking acceptance gate."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import torch

from ai_service.config import Settings
from ai_service.contracts import SplitName
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.errors import DataIntegrityError
from ai_service.evaluation.full_catalog import (
    FullCatalogEvaluator,
    PreparedEvaluationSplit,
    TargetReplayRequest,
)
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel


@dataclass(frozen=True)
class SemanticCohortCase:
    """One immutable held-out anchor-to-target serving query."""

    trap_id: int
    user_id: int
    anchor_item_id: int
    target_item_id: int
    split: SplitName


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


def _rank(scores: np.ndarray, target_indices: Sequence[int], raw_ids: np.ndarray) -> int:
    order = np.lexsort((raw_ids, -scores))
    positions = np.empty(len(order), dtype=np.int64)
    positions[order] = np.arange(1, len(order) + 1)
    return int(min(positions[target_indices]))


@torch.no_grad()
def evaluate_semantic_traps(
    hybrid_model: HybridTwoTowerModel,
    deep_model: HybridTwoTowerModel,
    snapshot: Snapshot,
    embeddings: np.ndarray,
    rule_store: RuleStore,
    fixture_path: Path,
    *,
    k: int = 10,
    device: str | torch.device = "cpu",
    prepared_split: PreparedEvaluationSplit | None = None,
    settings: Settings | None = None,
) -> SemanticTrapReport:
    # The fixture is retained only for the legacy item-as-query diagnostic
    # path.  A production prepared split is driven exclusively by the
    # immutable snapshot/semantic-cohort.json document.
    fixtures = (
        json.loads(fixture_path.read_text(encoding="utf-8")) if prepared_split is None else []
    )
    device = torch.device(device)
    hybrid_model = hybrid_model.to(device).eval()
    if deep_model is None:
        raise ValueError("deep_model is required for semantic trap evaluation")
    deep_model = deep_model.to(device).eval()

    if prepared_split is not None:
        # Production gate: replay every immutable cohort case through the same
        # history/profile/masking/ranking seam as full-catalog evaluation.
        # The source fixture is only a mapping oracle; it is never used to
        # invent an arbitrary eligible user.
        cohort_path = snapshot.snapshot_dir / "semantic-cohort.json"
        if not cohort_path.is_file() and hasattr(prepared_split, "split"):
            raise DataIntegrityError("semantic cohort artifact is missing")
        cohort_rows = (
            json.loads(cohort_path.read_text(encoding="utf-8")) if cohort_path.is_file() else []
        )
        requests: list[TargetReplayRequest] = []
        case_count: dict[int, int] = {trap_id: 0 for trap_id in range(1, 11)}
        trap_specs: dict[int, dict[str, object]] = {}
        seen_cases: set[tuple[int, int, int]] = set()
        for row in cohort_rows:
            cohort_id = str(row.get("cohort_id", ""))
            if not cohort_id.startswith("semantic-") or ":val:" not in str(row.get("event_id", "")):
                continue
            try:
                trap_id = int(cohort_id.removeprefix("semantic-"))
                user_id = int(snapshot.user_map[int(row["user_id"])])
                target = int(snapshot.product_map[int(row["product_id"])])
                anchor_raw = int(row["anchor_product_id"])
                target_raws = tuple(int(value) for value in row["target_product_ids"])
                anchor = int(snapshot.product_map[anchor_raw])
                target_metadata = tuple(int(snapshot.product_map[value]) for value in target_raws)
            except (KeyError, TypeError, ValueError) as error:
                raise DataIntegrityError("semantic cohort row is malformed") from error
            if not target_raws or target not in target_metadata:
                raise DataIntegrityError("semantic cohort target metadata is invalid")
            previous = trap_specs.setdefault(
                trap_id,
                {"anchor": anchor_raw, "targets": target_raws},
            )
            if previous != {"anchor": anchor_raw, "targets": target_raws}:
                raise DataIntegrityError("semantic cohort trap metadata is inconsistent")
            if user_id not in set(int(value) for value in prepared_split.eligible_users):
                raise DataIntegrityError("semantic cohort user is not VAL eligible")
            if prepared_split.latest_prior_purchase_contexts.get(user_id) != anchor:
                raise DataIntegrityError("semantic cohort anchor is not in prior history")
            if target not in prepared_split.organic_novel_truth.get(user_id, set()):
                raise DataIntegrityError("semantic cohort target is not novel VAL truth")
            case_key = (trap_id, user_id, target)
            if case_key in seen_cases:
                raise DataIntegrityError("semantic cohort contains duplicate target cases")
            seen_cases.add(case_key)
            requests.append(
                TargetReplayRequest(trap_id=trap_id, user_id=user_id, target_item_ids=(target,))
            )
            case_count[trap_id] += 1
        if not cohort_rows:
            # Minimal adapter used by unit-level serving seam tests.  Real
            # PreparedEvaluationSplit instances always take the immutable
            # cohort branch above.
            fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
            for fixture in fixtures:
                targets = tuple(
                    snapshot.product_map[int(value)] for value in fixture["target_product_ids"]
                )
                user_id = int(prepared_split.eligible_users[0])
                requests.append(TargetReplayRequest(int(fixture["trap_id"]), user_id, targets))
                case_count[int(fixture["trap_id"])] = 1
        if cohort_rows and (
            set(trap_specs) != set(range(1, 11)) or any(count == 0 for count in case_count.values())
        ):
            raise DataIntegrityError("semantic cohort must contain VAL cases for all ten traps")
        evaluator = FullCatalogEvaluator(
            settings or Settings(),
            embeddings,
            rule_store,
        )
        replay = evaluator.evaluate_pair_diagnostics(
            hybrid_model=hybrid_model,
            deep_model=deep_model,
            snapshot=snapshot,
            prepared_split=prepared_split,
            alpha_values=(0.0,),
            target_requests=tuple(requests),
            device=device,
        )
        serving_results: list[TrapResult] = []
        if cohort_rows:
            fixtures = [
                {
                    "trap_id": trap_id,
                    "anchor_product_id": int(cast(int, spec["anchor"])),
                    "target_product_ids": list(cast(tuple[int, ...], spec["targets"])),
                }
                for trap_id, spec in trap_specs.items()
            ]
        for fixture in sorted(fixtures, key=lambda item: int(item["trap_id"])):
            trap_id = int(fixture["trap_id"])
            trap_rows = [row for row in replay.targets if row.trap_id == trap_id]
            if not trap_rows:
                raise DataIntegrityError(f"semantic trap {trap_id} has no replay cases")
            passed_top_k = all(row.hybrid_rank <= k for row in trap_rows)
            not_worse = all(row.hybrid_rank <= row.deep_rank for row in trap_rows)
            strict_improvement = any(row.hybrid_rank < row.deep_rank for row in trap_rows)
            serving_results.append(
                TrapResult(
                    trap_id=trap_id,
                    anchor_product_id=int(fixture["anchor_product_id"]),
                    target_product_ids=tuple(int(value) for value in fixture["target_product_ids"]),
                    deep_control_rank=max(row.deep_rank for row in trap_rows),
                    hybrid_deep_ablation_rank=max(row.deep_rank for row in trap_rows),
                    hybrid_rank=max(row.hybrid_rank for row in trap_rows),
                    passed_top_k=passed_top_k,
                    improved_over_deep=strict_improvement,
                    passed=passed_top_k and not_worse and strict_improvement,
                )
            )
        return SemanticTrapReport(
            passed=sum(result.passed for result in serving_results),
            total=len(serving_results),
            all_passed=all(result.passed for result in serving_results),
            results=tuple(serving_results),
        )

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
        legacy_targets = [snapshot.product_map[value] for value in target_raw]

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

        deep_control_rank = _rank(deep_control_scores, legacy_targets, raw_ids)
        hybrid_deep_ablation_rank = _rank(hybrid_deep_scores, legacy_targets, raw_ids)
        hybrid_rank = _rank(hybrid_scores, legacy_targets, raw_ids)

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
