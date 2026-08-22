"""Semantic-trap ranking acceptance gate."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from ai_service.config import Settings
from ai_service.data.rules import RuleStore
from ai_service.data.semantic_cohort import cases_for_split, load_semantic_cohort
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.full_catalog import (
    FullCatalogEvaluator,
    PreparedEvaluationSplit,
    TargetReplayRequest,
)
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


def _rank(scores: np.ndarray, target_indices: Sequence[int], raw_ids: np.ndarray) -> int:
    order = np.lexsort((raw_ids, -scores))
    positions = np.empty(len(order), dtype=np.int64)
    positions[order] = np.arange(1, len(order) + 1)
    return int(min(positions[target_indices]))


def semantic_replay_requests(
    snapshot: Snapshot,
    prepared_split: PreparedEvaluationSplit,
) -> tuple[tuple[TargetReplayRequest, ...], dict[int, tuple[int, tuple[int, ...]]]]:
    """Map the verified typed cohort into serving-equivalent replay requests."""

    manifest = getattr(snapshot, "manifest", None)
    expected_sha256 = getattr(manifest, "semantic_cohort_sha256", None)
    if expected_sha256 is not None and not isinstance(expected_sha256, str):
        raise DataIntegrityError("snapshot semantic cohort checksum is invalid")
    try:
        document = load_semantic_cohort(
            snapshot.snapshot_dir,
            expected_sha256=expected_sha256,
        )
    except ArtifactIntegrityError as error:
        raise DataIntegrityError(f"semantic cohort is invalid: {error}") from error
    split = prepared_split.split
    cases = cases_for_split(document, split)
    eligible_users = {int(user_id) for user_id in prepared_split.eligible_users}
    requests: list[TargetReplayRequest] = []
    trap_targets: dict[int, set[int]] = {trap_id: set() for trap_id in range(1, 11)}
    trap_anchors: dict[int, int] = {}
    for case in cases:
        try:
            user_id = int(snapshot.user_map[case.user_id])
            anchor = int(snapshot.product_map[case.anchor_product_id])
            target = int(snapshot.product_map[case.target_product_id])
        except KeyError as error:
            raise DataIntegrityError(
                "semantic cohort references an unmapped user or product"
            ) from error
        if user_id not in eligible_users:
            raise DataIntegrityError("semantic cohort user is not eligible for its split")
        if prepared_split.latest_prior_purchase_contexts.get(user_id) != anchor:
            raise DataIntegrityError("semantic cohort anchor is not the serving history context")
        if target not in prepared_split.organic_novel_truth.get(user_id, set()):
            raise DataIntegrityError("semantic cohort target is not novel split truth")
        previous_anchor = trap_anchors.setdefault(case.trap_id, case.anchor_product_id)
        if previous_anchor != case.anchor_product_id:
            raise DataIntegrityError("semantic cohort trap anchor is inconsistent")
        trap_targets[case.trap_id].add(case.target_product_id)
        requests.append(
            TargetReplayRequest(
                trap_id=case.trap_id,
                user_id=user_id,
                target_item_ids=(target,),
            )
        )
    if set(trap_anchors) != set(range(1, 11)):
        raise DataIntegrityError("semantic cohort must define all ten traps for its split")
    definitions = {
        trap_id: (trap_anchors[trap_id], tuple(sorted(trap_targets[trap_id])))
        for trap_id in range(1, 11)
    }
    if any(not targets for _, targets in definitions.values()):
        raise DataIntegrityError("semantic cohort trap has no target direction")
    return tuple(requests), definitions


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
    # The fixture remains only for the legacy item-as-query diagnostic path.
    # Prepared R3/R4 evaluation always replays the immutable typed cohort.
    fixtures = (
        json.loads(fixture_path.read_text(encoding="utf-8")) if prepared_split is None else []
    )
    device = torch.device(device)
    hybrid_model = hybrid_model.to(device).eval()
    if deep_model is None:
        raise ValueError("deep_model is required for semantic trap evaluation")
    deep_model = deep_model.to(device).eval()

    if prepared_split is not None:
        cohort_path = snapshot.snapshot_dir / "semantic-cohort.json"
        use_typed_cohort = cohort_path.is_file() or (
            settings is not None and settings.data.rule_feature_schema_version == "3.0.0"
        )
        if use_typed_cohort:
            requests, trap_specs = semantic_replay_requests(snapshot, prepared_split)
        else:
            # The legacy non-v5 fixture path is intentionally isolated from
            # prepared v5 evaluation and never selects a user in production.
            fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
            requests = tuple(
                TargetReplayRequest(
                    trap_id=int(fixture["trap_id"]),
                    user_id=int(prepared_split.eligible_users[0]),
                    target_item_ids=tuple(
                        snapshot.product_map[int(value)]
                        for value in fixture["target_product_ids"]
                    ),
                )
                for fixture in fixtures
            )
            trap_specs = {
                int(fixture["trap_id"]): (
                    int(fixture["anchor_product_id"]),
                    tuple(int(value) for value in fixture["target_product_ids"]),
                )
                for fixture in fixtures
            }
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
            target_requests=requests,
            device=device,
        )
        serving_results: list[TrapResult] = []
        for trap_id in sorted(trap_specs):
            anchor_product_id, target_product_ids = trap_specs[trap_id]
            trap_rows = [row for row in replay.targets if row.trap_id == trap_id]
            if not trap_rows:
                raise DataIntegrityError(f"semantic trap {trap_id} has no replay cases")
            passed_top_k = all(row.hybrid_rank <= k for row in trap_rows)
            not_worse = all(row.hybrid_rank <= row.deep_rank for row in trap_rows)
            strict_improvement = any(row.hybrid_rank < row.deep_rank for row in trap_rows)
            serving_results.append(
                TrapResult(
                    trap_id=trap_id,
                    anchor_product_id=anchor_product_id,
                    target_product_ids=target_product_ids,
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
