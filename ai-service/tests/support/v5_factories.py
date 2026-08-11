"""Small production-interface factories used by contract tests.

The factories deliberately compose the public artifact writers instead of
recreating v5 JSON by hand.  This keeps the tests on the same seams as the
pipeline callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    CheckpointManifest,
    MetricGateResult,
    ModelVariant,
    SplitName,
    TrainingVariant,
    VictoryMatrix,
)
from ai_service.data.rules import RuleStore
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import EvaluationResult, TrainingValidationPass
from ai_service.evaluation.report import (
    METRIC_KEYS,
    canonical_victory_matrix_sha,
    publish_evaluation_artifacts,
)
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager


@dataclass(frozen=True)
class CheckpointFixture:
    path: Path
    manifest: CheckpointManifest
    model: HybridTwoTowerModel
    settings: Settings
    lineage: dict[str, str]


@dataclass(frozen=True)
class EvaluationFixture:
    directory: Path
    settings: Settings
    matrix: VictoryMatrix
    metrics: dict[str, np.ndarray]


def make_checkpoint_fixture(
    root: Path,
    *,
    variant: TrainingVariant = TrainingVariant.HYBRID,
    seed: int = 42,
    checkpoint_kind: str = "best",
) -> CheckpointFixture:
    settings = make_settings(root, variant=variant, seed=seed)
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters(), lr=1e-3)
    path = (
        root / "runs" / f"fixture-{variant.value}-{seed}" / "checkpoints" / f"{checkpoint_kind}.pt"
    )
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    manifest = CheckpointManager.save(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=ReduceLROnPlateau(optimizer),
        scaler=SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _: None),
        epoch=1,
        metrics={
            "val_gauc": 0.8,
            "val_ndcg_at_k": 0.2,
            "val_hr_at_k": 0.3,
            "train_loss": 0.5,
        },
        stopping_state={
            "highest_gauc": 0.8,
            "selected_epoch": 1,
            "selected_gauc": 0.8,
            "selected_ndcg": 0.2,
            "selected_hr": 0.3,
            "patience_used": 0,
        },
        checkpoint_kind=checkpoint_kind,  # type: ignore[arg-type]
        lineage=lineage,
        training_signature_sha256=settings.training_signature_sha256(),
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        training_variant=variant,
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id=path.parents[1].name,
    )
    return CheckpointFixture(path, manifest, model, settings, lineage)


def make_evaluation_fixture(root: Path) -> EvaluationFixture:
    settings = make_settings(root)
    metrics = {
        "user_ids": np.arange(1, 5, dtype=np.int64),
        **{
            name: (
                np.full((10, 4), 0.5, dtype=np.float64)
                if name.startswith("random_")
                else np.full(4, 0.5, dtype=np.float64)
            )
            for name in METRIC_KEYS
            if name != "user_ids"
        },
    }
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=settings.train.seed,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    artifact = publish_evaluation_artifacts(
        run_dir=root / "run",
        split=SplitName.VAL,
        hybrid_run_id="hybrid-fixture",
        deep_run_id="deep-fixture",
        hybrid_checkpoint_sha256="d" * 64,
        deep_checkpoint_sha256="e" * 64,
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        metrics=metrics,
        results={"fixture": True},
        victory_matrix=matrix,
    )
    return EvaluationFixture(artifact.directory, settings, matrix, metrics)


def make_settings(
    artifact_root: Path,
    *,
    variant: TrainingVariant = TrainingVariant.HYBRID,
    seed: int = 42,
) -> Settings:
    settings = Settings(
        {
            "data": {
                "artifact_root": str(artifact_root),
                "num_users": 4,
                "num_items": 80,
                "num_cold_items": 8,
                "num_personas": 4,
                "num_leaf_categories": 4,
                "num_price_buckets": 2,
            },
            "model": {"sbert_dim": 8},
            "train": {
                "training_variant": variant.value,
                "seed": seed,
                "max_epochs": 1,
                "batch_size": 2,
                "validation_user_batch_size": 2,
            },
            "eval": {"k": 10, "random_seeds": 10},
        }
    )
    return settings


def make_snapshot(
    root: Path,
    *,
    num_users: int = 4,
    num_items: int = 80,
    num_cold_items: int = 8,
) -> Snapshot:
    warm_items = num_items - num_cold_items
    catalog = pd.DataFrame(
        {
            "product_id": np.arange(10_001, 10_001 + num_items),
            "internal_product_id": np.arange(num_items),
            "internal_leaf_category_id": (np.arange(num_items) % 4) + 1,
            "price_bucket_id": (np.arange(num_items) % 2) + 1,
        }
    )
    rows: list[tuple[str, int, int, str, pd.Timestamp, float]] = []
    for user in range(1, num_users + 1):
        first = (user - 1) % max(1, warm_items)
        second = (first + num_users) % max(1, warm_items)
        rows.extend(
            [
                (
                    f"train-{user}-1",
                    user,
                    first,
                    "purchase",
                    pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(days=user),
                    1.0,
                ),
                (
                    f"train-{user}-2",
                    user,
                    second,
                    "purchase",
                    pd.Timestamp("2026-01-02", tz="UTC") + pd.Timedelta(days=user),
                    1.0,
                ),
            ]
        )
    columns = [
        "event_id",
        "internal_user_id",
        "internal_product_id",
        "event_type",
        "event_ts",
        "interaction_weight",
    ]
    train = pd.DataFrame(rows, columns=columns)
    val_rows = [
        (
            f"val-{user}",
            user,
            (user + 2 * num_users) % max(1, warm_items),
            "purchase",
            pd.Timestamp("2026-02-01", tz="UTC") + pd.Timedelta(days=user),
            1.0,
        )
        for user in range(1, num_users + 1)
    ]
    test_rows = [
        (
            f"test-{user}",
            user,
            warm_items + ((user - 1) % max(1, num_cold_items)),
            "purchase",
            pd.Timestamp("2026-03-01", tz="UTC") + pd.Timedelta(days=user),
            1.0,
        )
        for user in range(1, num_users + 1)
    ]
    val = pd.DataFrame(val_rows, columns=columns)
    test = pd.DataFrame(test_rows, columns=columns)
    return Snapshot(
        manifest=SimpleNamespace(
            num_items=num_items,
            num_users=num_users,
            store_id=1,
            artifact_id="fixture-v5",
            content_sha256="a" * 64,
        ),
        snapshot_dir=root,
        catalog_df=catalog,
        train_df=train,
        val_df=val,
        test_df=test,
        order_baskets_df=pd.DataFrame(),
        product_map={10_001 + i: i for i in range(num_items)},
        raw_product_map={i: 10_001 + i for i in range(num_items)},
        user_map={100 + i: i + 1 for i in range(num_users)},
        raw_user_map={i + 1: 100 + i for i in range(num_users)},
        persona_map={100 + i: i % 4 for i in range(num_users)},
        cold_item_ids=tuple(range(warm_items, num_items)),
        price_boundaries=np.asarray([100.0]),
    )


def make_full_stat_rule_store(num_items: int = 80) -> RuleStore:
    return RuleStore(
        num_items,
        [(0, 1, 3.0, 0.2, 0.8, 3), (1, 2, 2.0, 0.1, 0.5, 2)],
    )


def make_metric_gate(name: str, *, passed: bool = True) -> MetricGateResult:
    return MetricGateResult(
        name=name,
        passed=passed,
        observed=0.8,
        target=0.75,
        description=f"fixture {name}",
        candidate_name="hybrid",
        baseline_name="deep_only",
        candidate_mean=0.8,
        baseline_mean=0.6,
        delta_mean=0.2,
        ci_lower=0.1,
        ci_upper=0.3,
        threshold=0.0,
        failure_reason=None if passed else f"fixture {name} failed",
    )


def make_victory_matrix(
    *,
    split: SplitName,
    seed: int,
    comparison_signature: str,
    passed: bool = True,
) -> VictoryMatrix:
    names = (
        "random_gauc",
        "hybrid_gauc",
        "hr_domination",
        "relative_ndcg",
        "semantic_traps",
        "cold_parity",
    )
    gates = [make_metric_gate(name, passed=passed) for name in names]
    document = {
        "random_gauc_passed": passed,
        "hybrid_gauc_passed": passed,
        "hr_domination_passed": passed,
        "relative_ndcg_passed": passed,
        "semantic_traps_passed": passed,
        "cold_parity_passed": passed,
        "all_passed": passed,
        "gates": [gate.model_dump(mode="json") for gate in gates],
        "seed": seed,
        "split": split,
        "comparison_signature": comparison_signature,
        "strongest_hr_baseline": "deep_only",
        "sha256": "0" * 64,
    }
    matrix = VictoryMatrix.model_validate(document)
    return matrix.model_copy(update={"sha256": canonical_victory_matrix_sha(matrix)})


def _result(variant: ModelVariant, *, gauc: float, ndcg: float, hr: float) -> EvaluationResult:
    users = np.arange(1, 5, dtype=np.int64)
    return EvaluationResult(
        report=SimpleNamespace(gauc=gauc, ndcg_at_k=ndcg, hr_at_k=hr),
        user_ids=users,
        per_user_hr=np.full(len(users), hr, dtype=np.float64),
        per_user_ndcg=np.full(len(users), ndcg, dtype=np.float64),
        per_user_gauc=np.full(len(users), gauc, dtype=np.float64),
        top_k_by_user={int(user): tuple() for user in users},
    )


def make_training_validation_pass(
    snapshot: Snapshot,
    *,
    gauc: float = 0.75,
    ndcg: float = 0.20,
    hr: float = 0.30,
) -> TrainingValidationPass:
    width = min(64, snapshot.manifest.num_items - len(snapshot.cold_item_ids))
    cache = np.full((snapshot.manifest.num_users + 1, width), -1, dtype=np.int32)
    warm = [
        item for item in range(snapshot.manifest.num_items) if item not in snapshot.cold_item_ids
    ]
    for user in range(1, snapshot.manifest.num_users + 1):
        seen = {
            int(item)
            for item in snapshot.train_df.loc[
                snapshot.train_df.internal_user_id == user, "internal_product_id"
            ]
        }
        available = [item for item in warm if item not in seen]
        if len(available) < width:
            raise ValueError("fixture does not have enough unseen warm items")
        cache[user] = np.asarray(available[:width], dtype=np.int32)
    return TrainingValidationPass(
        variants={
            ModelVariant.HYBRID: _result(ModelVariant.HYBRID, gauc=gauc, ndcg=ndcg, hr=hr),
            ModelVariant.DEEP_ONLY: _result(
                ModelVariant.DEEP_ONLY, gauc=gauc - 0.05, ndcg=ndcg, hr=hr
            ),
            ModelVariant.WIDE_ONLY: _result(
                ModelVariant.WIDE_ONLY, gauc=gauc - 0.10, ndcg=ndcg, hr=hr
            ),
        },
        model_hard_cache=cache,
        deep_logit_rms=1.0,
        wide_logit_rms=0.1,
        hybrid_logit_rms=1.1,
    )


__all__ = [
    "CheckpointFixture",
    "EvaluationFixture",
    "make_checkpoint_fixture",
    "make_evaluation_fixture",
    "make_full_stat_rule_store",
    "make_metric_gate",
    "make_settings",
    "make_snapshot",
    "make_training_validation_pass",
    "make_victory_matrix",
]
