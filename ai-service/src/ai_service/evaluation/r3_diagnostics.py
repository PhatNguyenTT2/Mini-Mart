"""Read-only, serving-equivalent diagnostics for the failed R3 campaign.

The diagnostic artifact is deliberately separate from the release artifact.  It
replays the immutable checkpoints through the same streaming evaluator, stores
bounded per-user evidence, and publishes only after the temporary directory can
be loaded and verified again.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import torch

from ai_service.artifact_io import canonical_json_sha256, publish_directory_atomic
from ai_service.config import Settings
from ai_service.contracts import (
    AlphaSweepEvidence,
    ArtifactLineage,
    ArtifactLineageV5,
    CohortMetricDelta,
    DataSourceKind,
    R3DiagnosticReport,
    RuleAlignmentEvidence,
    SplitName,
    TrapDiagnosticEvidence,
)
from ai_service.data.dataset import build_purchase_training_index
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.full_catalog import (
    FullCatalogEvaluator,
    TargetReplayRequest,
    prepare_split,
)
from ai_service.evaluation.semantic_traps import evaluate_semantic_traps


class LoadedDiagnosticRun(Protocol):
    """Minimum immutable run surface needed by the diagnostic module."""

    @property
    def run_dir(self) -> Path: ...

    @property
    def checkpoint_manifest(self) -> Any: ...

    @property
    def settings(self) -> Settings: ...

    @property
    def lifecycle(self) -> Any: ...

    @property
    def state(self) -> Any: ...

    @property
    def snapshot(self) -> Any: ...

    @property
    def embedding(self) -> Any: ...

    @property
    def rules(self) -> Any: ...

    @property
    def model(self) -> Any: ...


@dataclass(frozen=True)
class R3DiagnosticArtifact:
    directory: Path
    report: R3DiagnosticReport
    metrics_path: Path
    report_path: Path


_ALPHAS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
_METRIC_KEYS = (
    "user_ids",
    "aligned_mask",
    "deep_hr",
    "deep_ndcg",
    "deep_gauc",
    "hybrid_hr",
    "hybrid_ndcg",
    "hybrid_gauc",
    "alpha_hr",
    "alpha_ndcg",
    "alpha_gauc",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_file(name: str) -> Path:
    return Path(__file__).parents[4] / "backend" / "docs" / "chatbot" / "seed-product" / name


def _validate_metrics(path: Path) -> dict[str, np.ndarray]:
    try:
        arrays = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("R3 metrics NPZ cannot be loaded") from error
    with arrays:
        if set(arrays.files) != set(_METRIC_KEYS):
            raise ArtifactIntegrityError("R3 metrics NPZ has an unexpected key set")
        result = {key: np.asarray(arrays[key]) for key in _METRIC_KEYS}
    user_ids = result["user_ids"]
    if user_ids.dtype != np.int64 or user_ids.ndim != 1 or len(user_ids) == 0:
        raise ArtifactIntegrityError("R3 user_ids must be a non-empty int64 vector")
    if np.any(user_ids <= 0) or np.any(np.diff(user_ids) <= 0):
        raise ArtifactIntegrityError("R3 user_ids must be sorted, unique, and non-zero")
    aligned = result["aligned_mask"]
    if aligned.dtype != np.bool_ or aligned.shape != (len(user_ids),):
        raise ArtifactIntegrityError("R3 aligned_mask must be bool [U]")
    user_metric_keys = (
        "deep_hr",
        "deep_ndcg",
        "deep_gauc",
        "hybrid_hr",
        "hybrid_ndcg",
        "hybrid_gauc",
    )
    for key in user_metric_keys:
        values = result[key]
        if values.shape != (len(user_ids),) or values.dtype != np.float64:
            raise ArtifactIntegrityError(f"R3 metric {key} has an invalid shape or dtype")
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ArtifactIntegrityError(f"R3 metric {key} is outside [0,1]")
    for key in ("alpha_hr", "alpha_ndcg", "alpha_gauc"):
        values = result[key]
        if values.shape != (len(_ALPHAS), len(user_ids)) or values.dtype != np.float64:
            raise ArtifactIntegrityError(f"R3 alpha metric {key} has an invalid shape or dtype")
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ArtifactIntegrityError(f"R3 alpha metric {key} is outside [0,1]")
    return result


def _write_metrics(path: Path, values: dict[str, np.ndarray]) -> None:
    normalized = {key: np.asarray(values[key]) for key in _METRIC_KEYS}
    np.savez(path, **normalized)  # type: ignore[arg-type]
    # Re-open immediately so publication never trusts an unverified NPZ.
    _validate_metrics(path)


def _load_existing_pair_metrics(
    hybrid_run: LoadedDiagnosticRun, deep_run: LoadedDiagnosticRun
) -> dict[str, np.ndarray]:
    """Use the verified production VAL score archive for the full cohort.

    R0 only replays the sparse trap/alpha overlay.  Re-reading the immutable
    VAL archives avoids a second 5,000 x 5,200 catalog pass while preserving
    exact per-user evidence from the production evaluator.
    """

    def read(path: Path, prefix: str) -> dict[str, np.ndarray]:
        if not path.is_file():
            raise ArtifactIntegrityError(f"missing source VAL metrics: {path}")
        with np.load(path, allow_pickle=False) as archive:
            required = ("user_ids", f"{prefix}_hr", f"{prefix}_ndcg", f"{prefix}_gauc")
            if not set(required).issubset(archive.files):
                raise ArtifactIntegrityError("source VAL metrics have an incomplete key set")
            user_ids = np.asarray(archive["user_ids"])
            if user_ids.dtype != np.int64 or user_ids.ndim != 1:
                raise ArtifactIntegrityError("source VAL user IDs have an invalid dtype")
            result = {"user_ids": user_ids}
            for key in required[1:]:
                values = np.asarray(archive[key])
                if values.shape != user_ids.shape or not np.isfinite(values).all():
                    raise ArtifactIntegrityError("source VAL metrics have invalid values")
                result[f"{prefix}_{key.split('_', 1)[1]}"] = values.astype(np.float64)
        return result

    hybrid = read(hybrid_run.run_dir / "evaluation" / "val" / "per-user-metrics.npz", "hybrid")
    deep_path = deep_run.run_dir / "evaluation" / "val" / "per-user-metrics.npz"
    if deep_path.is_file():
        deep = read(deep_path, "deep")
        if not np.array_equal(hybrid["user_ids"], deep["user_ids"]):
            raise ArtifactIntegrityError("source VAL metric user IDs differ between paired runs")
    else:
        # Evaluation artifacts are Hybrid-owned by contract; the Deep arrays
        # are part of that immutable paired archive.
        with np.load(
            hybrid_run.run_dir / "evaluation" / "val" / "per-user-metrics.npz", allow_pickle=False
        ) as archive:
            deep = {
                "user_ids": np.asarray(archive["user_ids"]),
                "deep_hr": np.asarray(archive["deep_hr"], dtype=np.float64),
                "deep_ndcg": np.asarray(archive["deep_ndcg"], dtype=np.float64),
                "deep_gauc": np.asarray(archive["deep_gauc"], dtype=np.float64),
            }
    return {
        "user_ids": hybrid["user_ids"],
        "deep_hr": deep["deep_hr"],
        "deep_ndcg": deep["deep_ndcg"],
        "deep_gauc": deep["deep_gauc"],
        "hybrid_hr": hybrid["hybrid_hr"],
        "hybrid_ndcg": hybrid["hybrid_ndcg"],
        "hybrid_gauc": hybrid["hybrid_gauc"],
    }


def _cohort_delta(
    name: str,
    user_ids: np.ndarray,
    aligned_users: set[int],
    deep: np.ndarray,
    hybrid: np.ndarray,
) -> CohortMetricDelta:
    mask = np.asarray([int(user) in aligned_users for user in user_ids], dtype=np.bool_)
    if name == "unaligned":
        mask = ~mask
    count = int(mask.sum())
    if count == 0:
        return CohortMetricDelta(
            cohort_name=name,
            user_count=0,
            hybrid_minus_deep_gauc=0.0,
            hybrid_minus_deep_hr_at_k=0.0,
            hybrid_minus_deep_ndcg_at_k=0.0,
        )
    delta = hybrid[:, mask] - deep[:, mask]
    return CohortMetricDelta(
        cohort_name=name,
        user_count=count,
        hybrid_minus_deep_gauc=float(delta[0].mean()),
        hybrid_minus_deep_hr_at_k=float(delta[1].mean()),
        hybrid_minus_deep_ndcg_at_k=float(delta[2].mean()),
    )


def _alignment_evidence(
    snapshot: Any, rule_store: Any, settings: Settings, semantic_embeddings: np.ndarray
) -> tuple[RuleAlignmentEvidence, set[int]]:
    index = build_purchase_training_index(
        snapshot, max_history_items=settings.train.max_history_items
    )
    if len(index.positive_items) == 0:
        raise DataIntegrityError("R3 alignment diagnostic found no training targets")
    context = index.context_items.astype(np.int64)
    positives = index.positive_items.astype(np.int64).reshape(-1, 1)
    _, present = rule_store.batch_raw_lift(context, positives)
    strict = present[:, 0]
    other_positive_hits = 0
    in_batch_negative_hits = 0
    explicit_negative_hits = 0
    negative_only_rows = 0
    sampler = MixedNegativeSampler(
        index,
        snapshot,
        semantic_embeddings,
        ratio=settings.train.explicit_negative_ratio,
        seed=settings.train.seed,
        rule_hard_negative_count=0,
    )
    batch_size = max(1, settings.train.batch_size)
    for offset in range(0, len(index.users), batch_size):
        end = min(len(index.users), offset + batch_size)
        batch_context = context[offset:end]
        batch_positive = positives[offset:end, 0]
        in_batch_candidates = np.broadcast_to(batch_positive[None, :], (end - offset, end - offset))
        _, in_present = rule_store.batch_raw_lift(batch_context, in_batch_candidates)
        diagonal = np.eye(end - offset, dtype=np.bool_)
        other_positive_hits += int((in_present & ~diagonal).sum())
        negatives = sampler.sample(
            index.users[offset:end],
            batch_positive,
            epoch=1,
            batch_index=offset // batch_size,
        )
        _, negative_present = rule_store.batch_raw_lift(batch_context, negatives)
        in_batch_negative_hits += int(negative_present.sum())
        explicit_negative_hits += int(negative_present.sum())
        negative_only_rows += int((~strict[offset:end] & negative_present.any(axis=1)).sum())
    aligned_users: set[int] = set()
    prepared = prepare_split(snapshot, SplitName.VAL)
    for user in prepared.eligible_users:
        user_id = int(user)
        context_item = prepared.latest_prior_purchase_contexts.get(user_id, -1)
        targets = prepared.organic_novel_truth.get(user_id, set())
        if context_item >= 0 and targets:
            candidate = np.asarray(sorted(targets), dtype=np.int64).reshape(1, -1)
            _, target_present = rule_store.batch_raw_lift(
                np.asarray([context_item], dtype=np.int64), candidate
            )
            if bool(target_present.any()):
                aligned_users.add(user_id)
    evidence = RuleAlignmentEvidence(
        training_targets=len(index.positive_items),
        strict_training_rule_targets=int(strict.sum()),
        strict_training_rule_rate=float(strict.mean()),
        positive_other_rule_hits=other_positive_hits,
        in_batch_negative_rule_hits=in_batch_negative_hits,
        explicit_negative_rule_hits=explicit_negative_hits,
        negative_only_rows=negative_only_rows,
        val_eligible_users=len(prepared.eligible_users),
        val_rule_aligned_users=len(aligned_users),
        val_rule_aligned_rate=float(
            len(aligned_users) / len(prepared.eligible_users)
            if len(prepared.eligible_users)
            else 0.0
        ),
    )
    return evidence, aligned_users


def _target_requests(
    snapshot: Any, prepared: Any, fixture_path: Path
) -> tuple[TargetReplayRequest, ...]:
    requests: list[TargetReplayRequest] = []
    snapshot_dir = getattr(snapshot, "snapshot_dir", None)
    cohort_path = (
        snapshot_dir / "semantic-cohort.json"
        if isinstance(snapshot_dir, Path)
        else Path("__missing_semantic_cohort__")
    )
    if (
        getattr(getattr(snapshot, "manifest", None), "source_kind", None) is DataSourceKind.POSTGRES
        and not cohort_path.is_file()
    ):
        raise DataIntegrityError("v5 semantic cohort artifact is missing")
    if cohort_path.is_file() and hasattr(prepared, "split"):
        trap_specs: dict[int, tuple[int, tuple[int, ...]]] = {}
        for row in json.loads(cohort_path.read_text(encoding="utf-8")):
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
            expected = (anchor_raw, target_raws)
            if trap_id in trap_specs and trap_specs[trap_id] != expected:
                raise DataIntegrityError("semantic cohort trap metadata is inconsistent")
            trap_specs[trap_id] = expected
            if prepared.latest_prior_purchase_contexts.get(user_id) != anchor:
                raise DataIntegrityError("semantic cohort anchor is not in prior history")
            if target not in prepared.organic_novel_truth.get(user_id, set()):
                raise DataIntegrityError("semantic cohort target is not novel VAL truth")
            requests.append(TargetReplayRequest(trap_id, user_id, (target,)))
        if not requests:
            raise DataIntegrityError("semantic cohort contains no serving-equivalent VAL cases")
        return tuple(requests)
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    eligible = [int(user) for user in prepared.eligible_users]
    selected_users: set[int] = set()
    for fixture in sorted(fixtures, key=lambda item: int(item["trap_id"])):
        trap_id = int(fixture["trap_id"])
        target_ids = tuple(int(item) for item in fixture["target_product_ids"])
        internal_targets = tuple(snapshot.product_map[item] for item in target_ids)
        selected: int | None = None
        anchor_internal = snapshot.product_map[int(fixture["anchor_product_id"])]
        has_cohort = hasattr(prepared, "organic_novel_truth") and hasattr(
            prepared, "latest_prior_purchase_contexts"
        )
        for user in eligible:
            seen = prepared.seen_items.get(user, set())
            if not has_cohort:
                if user not in selected_users and not any(
                    item in seen for item in internal_targets
                ):
                    selected = user
                    break
                continue
            truth = prepared.organic_novel_truth.get(user, set())
            if (
                user not in selected_users
                and prepared.latest_prior_purchase_contexts.get(user) == anchor_internal
                and set(internal_targets).issubset(truth)
                and not any(item in seen for item in internal_targets)
            ):
                selected = user
                break
        if selected is None:
            raise DataIntegrityError(f"no eligible serving user for semantic trap {trap_id}")
        requests.append(
            TargetReplayRequest(
                trap_id=trap_id,
                user_id=selected,
                target_item_ids=internal_targets,
            )
        )
        selected_users.add(selected)
    return tuple(requests)


def _report_without_hash(document: dict[str, object]) -> dict[str, object]:
    copy = dict(document)
    copy.pop("artifact_sha256", None)
    return copy


def publish_r3_diagnostic(
    *,
    hybrid_run: LoadedDiagnosticRun,
    deep_run: LoadedDiagnosticRun,
    split: SplitName,
    settings: Settings,
    artifact_root: Path,
    device: torch.device,
) -> R3DiagnosticArtifact:
    if split is not SplitName.VAL:
        raise ValueError("R3 diagnostic is validation-only")
    if hybrid_run.state.run_id == deep_run.state.run_id:
        raise ArtifactIntegrityError("R3 diagnostic requires distinct paired runs")
    if hybrid_run.lifecycle.document.get("git_commit") != deep_run.lifecycle.document.get(
        "git_commit"
    ):
        raise ArtifactIntegrityError("R3 diagnostic requires one frozen source revision")
    lineage = ArtifactLineageV5(
        snapshot=hybrid_run.snapshot.manifest.content_sha256,
        embedding=hybrid_run.embedding.manifest.content_sha256,
        rules=hybrid_run.rules.manifest.content_sha256,
        benchmark_spec=hybrid_run.snapshot.manifest.benchmark_spec_sha256,
        semantic_cohort=hybrid_run.snapshot.manifest.semantic_cohort_sha256,
        order_metadata=hybrid_run.snapshot.manifest.order_metadata_sha256,
    )
    deep_lineage = ArtifactLineageV5(
        snapshot=deep_run.snapshot.manifest.content_sha256,
        embedding=deep_run.embedding.manifest.content_sha256,
        rules=deep_run.rules.manifest.content_sha256,
        benchmark_spec=deep_run.snapshot.manifest.benchmark_spec_sha256,
        semantic_cohort=deep_run.snapshot.manifest.semantic_cohort_sha256,
        order_metadata=deep_run.snapshot.manifest.order_metadata_sha256,
    )
    if lineage != deep_lineage:
        raise ArtifactIntegrityError("R3 diagnostic requires matching artifact lineage")
    if (
        hybrid_run.settings.comparison_signature_sha256()
        != deep_run.settings.comparison_signature_sha256()
    ):
        raise ArtifactIntegrityError("R3 diagnostic requires matching comparison signatures")
    prepared = prepare_split(hybrid_run.snapshot, SplitName.VAL)
    evaluator = FullCatalogEvaluator(settings, hybrid_run.embedding.vectors, hybrid_run.rules.store)
    requests = _target_requests(
        hybrid_run.snapshot,
        prepared,
        Path(__file__).with_name("fixtures") / "semantic_traps.json",
    )
    replay = evaluator.evaluate_pair_diagnostics(
        hybrid_model=hybrid_run.model,
        deep_model=deep_run.model,
        snapshot=hybrid_run.snapshot,
        prepared_split=prepared,
        alpha_values=_ALPHAS,
        target_requests=requests,
        device=device,
    )
    source_metrics = _load_existing_pair_metrics(hybrid_run, deep_run)
    trap_report = evaluate_semantic_traps(
        hybrid_run.model,
        deep_run.model,
        hybrid_run.snapshot,
        hybrid_run.embedding.vectors,
        hybrid_run.rules.store,
        Path(__file__).with_name("fixtures") / "semantic_traps.json",
        k=settings.eval.k,
        device=device,
        prepared_split=prepared,
        settings=settings,
    )
    evidence, aligned_users = _alignment_evidence(
        hybrid_run.snapshot,
        hybrid_run.rules.store,
        settings,
        hybrid_run.embedding.vectors,
    )
    user_ids = source_metrics["user_ids"].astype(np.int64)
    aligned_mask = np.asarray([int(user) in aligned_users for user in user_ids], dtype=np.bool_)
    metrics: dict[str, np.ndarray] = {
        "user_ids": user_ids,
        "aligned_mask": aligned_mask,
        "deep_hr": source_metrics["deep_hr"],
        "deep_ndcg": source_metrics["deep_ndcg"],
        "deep_gauc": source_metrics["deep_gauc"],
        "hybrid_hr": source_metrics["hybrid_hr"],
        "hybrid_ndcg": source_metrics["hybrid_ndcg"],
        "hybrid_gauc": source_metrics["hybrid_gauc"],
        "alpha_hr": np.stack([replay.alpha_results[a].per_user_hr for a in _ALPHAS], axis=0).astype(
            np.float64
        ),
        "alpha_ndcg": np.stack(
            [replay.alpha_results[a].per_user_ndcg for a in _ALPHAS], axis=0
        ).astype(np.float64),
        "alpha_gauc": np.stack(
            [replay.alpha_results[a].per_user_gauc for a in _ALPHAS], axis=0
        ).astype(np.float64),
    }
    # Alpha values are a bounded summary, not per-user score dictionaries.
    # Trap metadata is read from the verified snapshot cohort.  The tracked
    # fixture remains only as a compatibility fallback for tiny legacy tests.
    cohort_path = hybrid_run.snapshot.snapshot_dir / "semantic-cohort.json"
    trap_specs: dict[int, tuple[int, tuple[int, ...]]] = {}
    if cohort_path.is_file():
        for row in json.loads(cohort_path.read_text(encoding="utf-8")):
            event_id = str(row.get("event_id", ""))
            cohort_id = str(row.get("cohort_id", ""))
            if ":target:" not in event_id or not cohort_id.startswith("semantic-"):
                continue
            trap_id = int(cohort_id.removeprefix("semantic-"))
            spec = (
                int(row["anchor_product_id"]),
                tuple(int(item) for item in row["target_product_ids"]),
            )
            if trap_id in trap_specs and trap_specs[trap_id] != spec:
                raise DataIntegrityError("semantic cohort trap metadata is inconsistent")
            trap_specs[trap_id] = spec
    else:
        fixture_path = Path(__file__).with_name("fixtures") / "semantic_traps.json"
        trap_specs = {
            int(item["trap_id"]): (
                int(item["anchor_product_id"]),
                tuple(int(value) for value in item["target_product_ids"]),
            )
            for item in json.loads(fixture_path.read_text(encoding="utf-8"))
        }
    if set(trap_specs) != set(range(1, 11)):
        raise DataIntegrityError("semantic cohort must contain all ten trap definitions")
    target_by_trap = {item.trap_id: item for item in replay.targets}
    item_by_trap = {item.trap_id: item for item in trap_report.results}
    trap_evidence = []
    for trap_id in range(1, 11):
        anchor_raw, target_raw_ids = trap_specs[trap_id]
        replay_row = target_by_trap[trap_id]
        item_row = item_by_trap[trap_id]
        anchor_internal = hybrid_run.snapshot.product_map[anchor_raw]
        target_internal = tuple(hybrid_run.snapshot.product_map[item] for item in target_raw_ids)
        lifts, present = hybrid_run.rules.store.batch_raw_lift(
            np.asarray([anchor_internal], dtype=np.int64),
            np.asarray([target_internal], dtype=np.int64),
        )
        trap_evidence.append(
            TrapDiagnosticEvidence(
                trap_id=trap_id,
                anchor_raw_id=anchor_raw,
                target_raw_ids=target_raw_ids,
                anchor_internal_id=anchor_internal,
                target_internal_ids=target_internal,
                rule_present=tuple(bool(item) for item in present[0]),
                raw_lifts=tuple(float(item) for item in lifts[0]),
                item_query_deep_rank=item_row.deep_control_rank,
                item_query_hybrid_rank=item_row.hybrid_rank,
                serving_deep_rank=replay_row.deep_rank,
                serving_hybrid_rank=replay_row.hybrid_rank,
                deep_top_k_cutoff=replay_row.deep_top_k_cutoff,
                learned_wide_bonus=replay_row.learned_wide_bonus,
                required_wide_bonus=replay_row.required_wide_bonus,
            )
        )
    deep_matrix = np.vstack((metrics["deep_gauc"], metrics["deep_hr"], metrics["deep_ndcg"]))
    hybrid_matrix = np.vstack(
        (metrics["hybrid_gauc"], metrics["hybrid_hr"], metrics["hybrid_ndcg"])
    )
    cohort_deltas = (
        _cohort_delta("aligned", user_ids, aligned_users, deep_matrix, hybrid_matrix),
        _cohort_delta("unaligned", user_ids, aligned_users, deep_matrix, hybrid_matrix),
    )
    alpha_sweep = tuple(
        AlphaSweepEvidence(
            alpha=alpha,
            gauc=float(metrics["alpha_gauc"][index].mean()),
            hr_at_k=float(metrics["alpha_hr"][index].mean()),
            ndcg_at_k=float(metrics["alpha_ndcg"][index].mean()),
            meets_absolute_floors=(
                float(metrics["alpha_gauc"][index].mean()) >= settings.eval.minimum_gauc
                and float(metrics["alpha_hr"][index].mean()) >= 0.15
                and float(metrics["alpha_ndcg"][index].mean()) >= 0.08
            ),
        )
        for index, alpha in enumerate(_ALPHAS)
    )
    cohort_file = hybrid_run.snapshot.snapshot_dir / "semantic-cohort.json"
    if not cohort_file.is_file():
        raise ArtifactIntegrityError("verified snapshot semantic cohort is missing")
    report = R3DiagnosticReport(
        schema_version="1.0.0",
        evaluation_schema_version="5.2.0",
        split=SplitName.VAL,
        hybrid_run_id=hybrid_run.state.run_id,
        deep_run_id=deep_run.state.run_id,
        hybrid_checkpoint_sha256=hybrid_run.checkpoint_manifest.content_sha256,
        deep_checkpoint_sha256=deep_run.checkpoint_manifest.content_sha256,
        git_commit=str(hybrid_run.lifecycle.document["git_commit"]),
        lineage=lineage,
        comparison_signature_sha256=hybrid_run.settings.comparison_signature_sha256(),
        benchmark_spec_sha256=str(lineage.benchmark_spec_sha256),
        semantic_cohort_sha256=str(lineage.semantic_cohort_sha256),
        order_metadata_sha256=str(lineage.order_metadata_sha256),
        rule_alignment=evidence,
        cohort_deltas=cohort_deltas,
        trap_evidence=tuple(trap_evidence),
        alpha_sweep=alpha_sweep,
        per_user_metrics_sha256="0" * 64,
        artifact_sha256="0" * 64,
    )
    root = artifact_root.resolve() / "diagnostics" / "r3"
    destination = root / f"{hybrid_run.state.run_id}__{deep_run.state.run_id}"
    root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".r3-", dir=root))
    try:
        metrics_path = temporary / "per-user-metrics.npz"
        _write_metrics(metrics_path, metrics)
        metrics_sha = _sha256_file(metrics_path)
        document = report.model_dump(mode="json")
        document["per_user_metrics_sha256"] = metrics_sha
        document["artifact_sha256"] = canonical_json_sha256(_report_without_hash(document))
        report = R3DiagnosticReport.model_validate(document)
        report_path = temporary / "report.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8", newline="\n")
        with report_path.open("r+", encoding="utf-8") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        _validate_metrics(metrics_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        publish_directory_atomic(temporary, destination)
        temporary = Path()
    finally:
        if str(temporary) not in {"", "."}:
            shutil.rmtree(temporary, ignore_errors=True)
    return R3DiagnosticArtifact(
        destination, report, destination / "per-user-metrics.npz", destination / "report.json"
    )


def load_r3_diagnostic(
    directory: Path,
    *,
    expected_hybrid_run_id: str,
    expected_deep_run_id: str,
    expected_lineage: ArtifactLineage | ArtifactLineageV5,
    expected_comparison_signature: str,
) -> R3DiagnosticArtifact:
    directory = directory.resolve()
    report_path = directory / "report.json"
    metrics_path = directory / "per-user-metrics.npz"
    if not directory.is_dir() or not report_path.is_file() or not metrics_path.is_file():
        raise ArtifactIntegrityError("R3 diagnostic directory is incomplete")
    try:
        report = R3DiagnosticReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("R3 diagnostic report is invalid") from error
    if report.hybrid_run_id != expected_hybrid_run_id or report.deep_run_id != expected_deep_run_id:
        raise ArtifactIntegrityError("R3 diagnostic pair does not match expected runs")
    if (
        report.lineage.model_dump(mode="json") != expected_lineage.model_dump(mode="json")
        or report.comparison_signature_sha256 != expected_comparison_signature
    ):
        raise ArtifactIntegrityError("R3 diagnostic lineage/signature mismatch")
    if _sha256_file(metrics_path) != report.per_user_metrics_sha256:
        raise ArtifactIntegrityError("R3 diagnostic metrics hash mismatch")
    document = report.model_dump(mode="json")
    claimed = document.pop("artifact_sha256")
    if canonical_json_sha256(document) != claimed:
        raise ArtifactIntegrityError("R3 diagnostic report hash mismatch")
    _validate_metrics(metrics_path)
    return R3DiagnosticArtifact(directory, report, metrics_path, report_path)


__all__ = [
    "LoadedDiagnosticRun",
    "R3DiagnosticArtifact",
    "load_r3_diagnostic",
    "publish_r3_diagnostic",
]
