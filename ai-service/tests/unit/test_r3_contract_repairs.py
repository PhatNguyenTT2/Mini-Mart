from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from ai_service.config import Settings
from ai_service.contracts import (
    ArtifactLineage,
    ArtifactLineageV5,
    EvaluationReport,
    ModelVariant,
    SplitName,
    TerminalAction,
    TrainingVariant,
    normalize_artifact_lineage,
)
from ai_service.data.dataset import build_rule_pair_index
from ai_service.data.rules import RuleStore
from ai_service.data.sampling import MixedNegativeBatch
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation import ablation
from ai_service.evaluation.ablation import DeepAblationRun, R3ArtifactLineage
from ai_service.evaluation.full_catalog import EvaluationResult
from ai_service.evaluation.r3_diagnostics import _cohort_delta, _target_requests, _validate_metrics
from ai_service.evaluation.report import (
    EvaluationArtifactManifest,
    publish_evaluation_artifacts,
)
from ai_service.lineage import resolve_artifact_lineage
from ai_service.training import pipeline as training_pipeline
from ai_service.training.diagnostic_stop import (
    DiagnosticStopReport,
    load_diagnostic_stop,
    publish_diagnostic_stop,
)
from ai_service.training.objectives import multi_positive_sampled_softmax, rule_pairwise_wide_loss
from ai_service.training.trainer import Trainer, _ValidationEpochPass
from tests.support.v5_factories import make_victory_matrix


def test_v5_lineage_resolver_requires_matching_parent_artifacts() -> None:
    snapshot = SimpleNamespace(
        content_sha256="a" * 64,
        benchmark_spec_sha256="d" * 64,
        semantic_cohort_sha256="e" * 64,
        order_metadata_sha256="f" * 64,
    )
    embedding = SimpleNamespace(snapshot_sha256="b" * 64, content_sha256="b" * 64)
    rules = SimpleNamespace(snapshot_sha256="a" * 64, content_sha256="c" * 64)
    with pytest.raises(ArtifactIntegrityError, match="embedding does not belong"):
        resolve_artifact_lineage(snapshot, embedding, rules, require_v5=True)  # type: ignore[arg-type]
    embedding.snapshot_sha256 = "a" * 64
    resolved = resolve_artifact_lineage(snapshot, embedding, rules, require_v5=True)  # type: ignore[arg-type]
    assert isinstance(resolved, ArtifactLineageV5)
    assert resolved.order_metadata == "f" * 64
    rules.snapshot_sha256 = "9" * 64
    with pytest.raises(ArtifactIntegrityError, match="rules do not belong"):
        resolve_artifact_lineage(snapshot, embedding, rules, require_v5=True)  # type: ignore[arg-type]


def _report(variant: ModelVariant, *, gauc: float, hr: float, ndcg: float) -> EvaluationReport:
    return EvaluationReport(
        run_id="diagnostic",
        split=SplitName.VAL,
        variant=variant,
        num_total_users=1,
        num_eligible_users=1,
        num_users_without_novel_purchase=0,
        num_catalog_items=32,
        hr_at_k=hr,
        ndcg_at_k=ndcg,
        gauc=gauc,
        k=10,
    )


def _validation(
    *,
    hybrid: tuple[float, float, float],
    deep: tuple[float, float, float],
    wide: tuple[float, float, float],
    ratio: float = 0.02,
    changed: float = 0.10,
) -> _ValidationEpochPass:
    return _ValidationEpochPass(
        hybrid_report=_report(ModelVariant.HYBRID, gauc=hybrid[0], hr=hybrid[1], ndcg=hybrid[2]),
        deep_report=_report(ModelVariant.DEEP_ONLY, gauc=deep[0], hr=deep[1], ndcg=deep[2]),
        wide_report=_report(ModelVariant.WIDE_ONLY, gauc=wide[0], hr=wide[1], ndcg=wide[2]),
        deep_logit_rms=1.0,
        wide_logit_rms=ratio,
        hybrid_logit_rms=1.0,
        hybrid_deep_top_k_change_rate=changed,
        model_hard_cache_updated=True,
    )


def test_r3_checkpoint_eligibility_is_warmup_and_guardrail_aware(tmp_path: Path) -> None:
    settings = Settings()
    settings.train.campaign_stage = "diagnostic"
    settings.train.diagnostic_warmup_epochs = 3
    trainer = object.__new__(Trainer)
    trainer.settings = settings
    trainer.training_variant = TrainingVariant.HYBRID

    eligible, reason = Trainer._checkpoint_eligibility(
        trainer,
        epoch=1,
        validation=_validation(hybrid=(0.9, 0.3, 0.2), deep=(0.8, 0.2, 0.1), wide=(0.7, 0.1, 0.05)),
    )
    assert not eligible and reason == "diagnostic warmup"

    eligible, reason = Trainer._checkpoint_eligibility(
        trainer,
        epoch=3,
        validation=_validation(
            hybrid=(0.6, 0.05, 0.01),
            deep=(0.7, 0.2, 0.1),
            wide=(0.7, 0.2, 0.1),
            ratio=0.001,
            changed=0.0,
        ),
    )
    assert not eligible and "absolute GAUC floor" in reason
    assert "Wide RMS ratio" in reason and "top-k change rate" in reason

    settings.train.campaign_stage = "legacy"
    eligible, reason = Trainer._checkpoint_eligibility(
        trainer,
        epoch=1,
        validation=_validation(hybrid=(0.1, 0.0, 0.0), deep=(0.1, 0.0, 0.0), wide=(0.1, 0.0, 0.0)),
    )
    assert eligible and reason == "legacy training contract"


def test_r3_deep_checkpoint_eligibility_uses_all_diagnostic_floors() -> None:
    settings = Settings()
    settings.train.campaign_stage = "diagnostic"
    settings.train.diagnostic_warmup_epochs = 3
    trainer = object.__new__(Trainer)
    trainer.settings = settings
    trainer.training_variant = TrainingVariant.DEEP_ONLY

    eligible, reason = Trainer._checkpoint_eligibility(
        trainer,
        epoch=3,
        validation=_validation(
            hybrid=(0.8, 0.2, 0.1),
            deep=(0.70, 0.12, 0.05),
            wide=(0.1, 0.0, 0.0),
        ),
    )
    assert eligible
    assert reason == "Deep diagnostic floors"

    eligible, reason = Trainer._checkpoint_eligibility(
        trainer,
        epoch=3,
        validation=_validation(
            hybrid=(0.8, 0.2, 0.1),
            deep=(0.64, 0.09, 0.03),
            wide=(0.1, 0.0, 0.0),
        ),
    )
    assert not eligible
    assert "Deep diagnostic GAUC floor" in reason
    assert "Deep diagnostic HR floor" in reason
    assert "Deep diagnostic NDCG floor" in reason


def test_r3_v5_snapshot_without_expanded_lineage_is_rejected_before_run_creation(
    tmp_path: Path,
) -> None:
    settings = Settings(
        {
            "data": {
                "artifact_root": tmp_path,
                "rule_feature_schema_version": "3.0.0",
            },
            "train": {"campaign_stage": "diagnostic"},
        }
    )
    manifest_type = type("SnapshotManifest", (), {})
    # The type-name check is deliberately strict for real SnapshotManifest
    # instances; this adapter exercises the same fail-closed branch without
    # constructing a database-backed snapshot fixture.
    snapshot = SimpleNamespace(manifest=manifest_type())
    snapshot.manifest.content_sha256 = "a" * 64
    embedding = SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64))
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256="c" * 64))

    with pytest.raises(ArtifactIntegrityError, match="expanded lineage"):
        training_pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="diag-v5-lineage-mismatch",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    assert not (tmp_path / "runs" / "diag-v5-lineage-mismatch").exists()

    snapshot.manifest.benchmark_spec_sha256 = "d" * 64
    with pytest.raises(ArtifactIntegrityError, match="expanded lineage"):
        training_pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="diag-v5-lineage-partial",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    assert not (tmp_path / "runs" / "diag-v5-lineage-partial").exists()


def test_r3_v5_snapshot_expanded_lineage_is_materialized_before_preflight_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        {
            "data": {
                "artifact_root": tmp_path,
                "rule_feature_schema_version": "3.0.0",
            },
            "train": {"campaign_stage": "diagnostic"},
        }
    )
    snapshot = SimpleNamespace(
        manifest=training_pipeline.SnapshotManifest(
            artifact_id="snapshot-v5",
            content_sha256="a" * 64,
            benchmark_run_id="benchmark-v5",
            store_id=1,
            source_kind="synthetic",
            num_events=1,
            num_users=1,
            num_items=1,
            num_cold_items=0,
            split_counts={SplitName.TRAIN: 1, SplitName.VAL: 0, SplitName.TEST: 0},
            split_boundaries={},
            benchmark_spec_sha256="d" * 64,
            semantic_cohort_sha256="e" * 64,
            order_metadata_sha256="f" * 64,
        )
    )
    embedding = SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64))
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256="c" * 64))
    monkeypatch.setattr(
        training_pipeline,
        "_require_rule_training_capability",
        lambda *_: (_ for _ in ()).throw(ArtifactIntegrityError("preflight stop")),
    )

    with pytest.raises(ArtifactIntegrityError, match="preflight stop"):
        training_pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="diag-v5-expanded-lineage",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    assert not (tmp_path / "runs" / "diag-v5-expanded-lineage").exists()


def test_evaluation_publisher_rejects_invalid_lineage_and_matrix_sha(tmp_path: Path) -> None:
    settings = Settings()
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    metrics = {
        "user_ids": np.asarray([1], dtype=np.int64),
        **{
            name: (np.zeros((10, 1)) if name.startswith("random_") else np.zeros(1))
            for name in (
                "hybrid_hr",
                "hybrid_ndcg",
                "hybrid_gauc",
                "deep_hr",
                "deep_ndcg",
                "deep_gauc",
                "apriori_hr",
                "apriori_ndcg",
                "apriori_gauc",
                "sbert_hr",
                "sbert_ndcg",
                "sbert_gauc",
                "item_cf_hr",
                "item_cf_ndcg",
                "item_cf_gauc",
                "noisy_hybrid_hr",
                "noisy_hybrid_ndcg",
                "noisy_hybrid_gauc",
                "random_hr",
                "random_ndcg",
                "random_gauc",
            )
        },
    }
    kwargs = {
        "run_dir": tmp_path / "run",
        "split": SplitName.VAL,
        "hybrid_run_id": "hybrid",
        "deep_run_id": "deep",
        "hybrid_checkpoint_sha256": "1" * 64,
        "deep_checkpoint_sha256": "2" * 64,
        "lineage": {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        "comparison_signature_sha256": settings.comparison_signature_sha256(),
        "metrics": metrics,
        "results": {},
        "victory_matrix": matrix,
    }
    with pytest.raises(ArtifactIntegrityError, match="lineage is invalid"):
        publish_evaluation_artifacts(**{**kwargs, "lineage": {"snapshot": "bad"}})
    with pytest.raises(ArtifactIntegrityError, match="canonical SHA"):
        publish_evaluation_artifacts(
            **{**kwargs, "victory_matrix": matrix.model_copy(update={"sha256": "0" * 64})}
        )


def test_pipeline_resume_history_and_terminal_summary_fail_closed(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "training").mkdir(parents=True)
    with pytest.raises(ArtifactIntegrityError, match="no durable"):
        training_pipeline._require_resume_history(run_dir, checkpoint_epoch=1)

    history = run_dir / "training" / "history.jsonl"
    history.write_text('{"epoch":"bad"}\n', encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="invalid epoch"):
        training_pipeline._require_resume_history(run_dir, checkpoint_epoch=1)

    history.write_text('{"epoch":2}\n', encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="epochs differ"):
        training_pipeline._require_resume_history(run_dir, checkpoint_epoch=1)

    summary = run_dir / "training" / "summary.json"
    summary.write_text('{"epochs_completed":-1}', encoding="utf-8")
    training_pipeline._ensure_training_terminal_summary(
        run_dir,
        action=TerminalAction.FAILED,
        reason="diagnostic stop",
    )
    document = json.loads(summary.read_text(encoding="utf-8"))
    assert document["epochs_completed"] == 0
    assert document["terminal_reason"] == "diagnostic stop"


def test_evaluation_manifest_rejects_partial_v5_metadata_lineage() -> None:
    with pytest.raises(ValueError, match="all metadata hashes"):
        EvaluationArtifactManifest(
            schema_version="5.2.0",
            split=SplitName.VAL,
            hybrid_run_id="hybrid",
            deep_run_id="deep",
            hybrid_checkpoint_sha256="a" * 64,
            deep_checkpoint_sha256="b" * 64,
            snapshot_sha256="c" * 64,
            embedding_sha256="d" * 64,
            rule_sha256="e" * 64,
            benchmark_spec_sha256="f" * 64,
            comparison_signature_sha256="1" * 64,
            passed=False,
            per_user_metrics_sha256="2" * 64,
            victory_matrix_sha256="3" * 64,
        )


def test_mixed_negative_batch_exposes_numpy_compatibility() -> None:
    batch = MixedNegativeBatch(
        item_ids=np.asarray([[1, 2]], dtype=np.int64),
        source_tags=np.asarray([["rule_hard", "warm"]]),
        rule_hard_mask=np.asarray([[True, False]]),
    )
    assert batch.shape == (1, 2)
    np.testing.assert_array_equal(np.asarray(batch), batch.item_ids)


def _valid_metric_values() -> dict[str, np.ndarray]:
    return {
        "user_ids": np.asarray([1, 2], dtype=np.int64),
        "aligned_mask": np.asarray([True, False], dtype=np.bool_),
        "deep_hr": np.zeros(2, dtype=np.float64),
        "deep_ndcg": np.zeros(2, dtype=np.float64),
        "deep_gauc": np.full(2, 0.5, dtype=np.float64),
        "hybrid_hr": np.ones(2, dtype=np.float64),
        "hybrid_ndcg": np.ones(2, dtype=np.float64),
        "hybrid_gauc": np.ones(2, dtype=np.float64),
        "alpha_hr": np.zeros((7, 2), dtype=np.float64),
        "alpha_ndcg": np.zeros((7, 2), dtype=np.float64),
        "alpha_gauc": np.full((7, 2), 0.5, dtype=np.float64),
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("user_ids", np.asarray([1, 1], dtype=np.int64), "sorted"),
        ("user_ids", np.asarray([0, 2], dtype=np.int64), "sorted"),
        ("aligned_mask", np.asarray([1, 0], dtype=np.int64), "aligned_mask"),
        ("deep_hr", np.asarray([0.1], dtype=np.float64), "deep_hr"),
        ("deep_gauc", np.asarray([np.nan, 0.5], dtype=np.float64), "deep_gauc"),
        ("hybrid_ndcg", np.asarray([-0.1, 0.5], dtype=np.float64), "hybrid_ndcg"),
        ("alpha_hr", np.zeros((6, 2), dtype=np.float64), "alpha_hr"),
        ("alpha_gauc", np.full((7, 2), 1.1, dtype=np.float64), "alpha_gauc"),
    ],
)
def test_r3_metrics_loader_rejects_invalid_contract_fields(
    tmp_path: Path, field: str, value: np.ndarray, message: str
) -> None:
    path = tmp_path / f"{field}.npz"
    values = _valid_metric_values()
    values[field] = value
    np.savez(path, **values)
    with pytest.raises(ArtifactIntegrityError, match=message):
        _validate_metrics(path)


def test_r3_cohort_delta_empty_cohort_is_zero() -> None:
    delta = _cohort_delta(
        "aligned",
        np.asarray([1], dtype=np.int64),
        set(),
        np.asarray([[0.5], [0.1], [0.2]]),
        np.asarray([[0.6], [0.2], [0.3]]),
    )
    assert delta.user_count == 0
    assert delta.hybrid_minus_deep_gauc == 0.0


def test_diagnostic_stop_is_immutable_and_hash_verified(tmp_path: Path) -> None:
    report = DiagnosticStopReport(
        run_id="diag",
        epoch=3,
        reason="quality floor",
        best_gauc=0.7,
        best_hr_at_k=0.1,
        best_ndcg_at_k=0.04,
        thresholds={"gauc": 0.65, "hr_at_k": 0.1, "ndcg_at_k": 0.04},
    )
    path = publish_diagnostic_stop(tmp_path, report)
    loaded = load_diagnostic_stop(path, expected_run_id="diag")
    assert loaded.artifact_sha256 is not None
    assert publish_diagnostic_stop(tmp_path, report) == path
    with pytest.raises(ArtifactIntegrityError, match="different content"):
        publish_diagnostic_stop(tmp_path, report.model_copy(update={"epoch": 4}))
    path.write_text(
        path.read_text(encoding="utf-8").replace("quality floor", "tampered"), encoding="utf-8"
    )
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        load_diagnostic_stop(path)


def test_diagnostic_stop_loader_accepts_unhashed_legacy_fixture(tmp_path: Path) -> None:
    report = DiagnosticStopReport(
        run_id="legacy",
        epoch=1,
        reason="fixture",
        best_gauc=0.6,
        best_hr_at_k=0.1,
        best_ndcg_at_k=0.02,
        thresholds={},
    )
    document = report.model_dump(mode="json")
    document["artifact_sha256"] = None
    path = tmp_path / "diagnostic-stop.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_diagnostic_stop(path).artifact_sha256 is None


def test_diagnostic_stop_binds_v5_lineage_and_run_id(tmp_path: Path) -> None:
    lineage = ArtifactLineageV5(
        snapshot="a" * 64,
        embedding="b" * 64,
        rules="c" * 64,
        benchmark_spec="d" * 64,
        semantic_cohort="e" * 64,
        order_metadata="f" * 64,
    )
    report = DiagnosticStopReport(
        run_id="diag-v5",
        epoch=3,
        reason="quality floor",
        best_gauc=0.7,
        best_hr_at_k=0.1,
        best_ndcg_at_k=0.04,
        thresholds={"gauc": 0.65},
        lineage=lineage,
        comparison_signature_sha256="1" * 64,
    )
    path = publish_diagnostic_stop(tmp_path, report)
    assert load_diagnostic_stop(path, expected_run_id="diag-v5").lineage == lineage
    with pytest.raises(ArtifactIntegrityError, match="run ID"):
        load_diagnostic_stop(path, expected_run_id="other")
    with pytest.raises(ValueError, match="lineage"):
        DiagnosticStopReport(
            run_id="bad",
            epoch=1,
            reason="bad",
            best_gauc=0.5,
            best_hr_at_k=0.1,
            best_ndcg_at_k=0.1,
            thresholds={},
            lineage={"snapshot": "a" * 64},
        )


def test_r3_metrics_loader_rejects_missing_or_corrupt_npz(tmp_path: Path) -> None:
    with pytest.raises(ArtifactIntegrityError, match="cannot be loaded"):
        _validate_metrics(tmp_path / "missing.npz")
    path = tmp_path / "bad.npz"
    path.write_bytes(b"not an npz")
    with pytest.raises(ArtifactIntegrityError, match="cannot be loaded"):
        _validate_metrics(path)


def test_rule_index_separates_organic_and_protected_trap_edges() -> None:
    snapshot = type(
        "SnapshotAdapter",
        (),
        {
            "order_baskets_df": pd.DataFrame(
                {
                    "order_id": [1, 1, 2, 2],
                    "internal_product_id": [0, 1, 0, 2],
                    "benchmark_kind": ["organic", "organic", "semantic_trap", "semantic_trap"],
                }
            ),
            "train_df": pd.DataFrame(),
        },
    )()
    index = build_rule_pair_index(snapshot)
    assert index.neighbors[0] == (1,)
    assert index.protected[0] == (2,)
    store = RuleStore(3, [(0, 1, 2.0), (0, 2, 3.0)])
    assert store.candidates(0).tolist() == [1, 2]
    assert store.candidates(-1).size == 0


def test_r3_v5_lineage_properties_are_canonical() -> None:
    lineage = ArtifactLineageV5(
        snapshot="a" * 64,
        embedding="b" * 64,
        rules="c" * 64,
        benchmark_spec="d" * 64,
        semantic_cohort="e" * 64,
        order_metadata="f" * 64,
    )
    assert lineage.snapshot_sha256 == "a" * 64
    assert lineage.as_mapping()["order_metadata"] == "f" * 64
    assert normalize_artifact_lineage(lineage) == lineage.as_mapping()
    assert (
        normalize_artifact_lineage(
            {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
        )["rules"]
        == "c" * 64
    )

    with pytest.raises(ValueError, match="keys are incomplete"):
        normalize_artifact_lineage({"snapshot": "a" * 64})


def test_lineage_rejects_partial_expanded_metadata() -> None:
    with pytest.raises(ValueError, match="all metadata hashes"):
        ArtifactLineage(
            snapshot_sha256="a" * 64,
            embedding_sha256="b" * 64,
            rule_sha256="c" * 64,
            benchmark_spec_sha256="d" * 64,
        )


def test_legacy_lineage_serializes_both_supported_shapes() -> None:
    legacy = R3ArtifactLineage(
        snapshot_sha256="a" * 64,
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
    )
    assert set(legacy.as_mapping()) == {"snapshot", "embedding", "rules"}
    expanded = R3ArtifactLineage(
        snapshot_sha256="a" * 64,
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
        benchmark_spec_sha256="d" * 64,
        semantic_cohort_sha256="e" * 64,
        order_metadata_sha256="f" * 64,
    )
    assert expanded.as_mapping()["semantic_cohort"] == "e" * 64


def test_r3_semantic_cohort_target_requests_use_immutable_rows(tmp_path: Path) -> None:
    cohort = tmp_path / "semantic-cohort.json"
    cohort.write_text(
        '[{"cohort_id":"semantic-1","event_id":"semantic-1:val:target:0",'
        '"user_id":10,"product_id":201,"anchor_product_id":200,"target_product_ids":[201]}]',
        encoding="utf-8",
    )
    fixture = tmp_path / "traps.json"
    fixture.write_text(
        '[{"trap_id":1,"anchor_product_id":200,"target_product_ids":[201]}]',
        encoding="utf-8",
    )
    snapshot = type(
        "SnapshotAdapter",
        (),
        {
            "snapshot_dir": tmp_path,
            "user_map": {10: 1},
            "product_map": {200: 0, 201: 1},
        },
    )()
    prepared = type(
        "PreparedAdapter",
        (),
        {
            "split": SplitName.VAL,
            "eligible_users": np.asarray([1]),
            "latest_prior_purchase_contexts": {1: 0},
            "organic_novel_truth": {1: {1}},
        },
    )()
    requests = _target_requests(snapshot, prepared, fixture)
    assert len(requests) == 1
    assert requests[0].target_item_ids == (1,)


def test_r3_semantic_cohort_requests_reject_missing_or_misaligned_metadata(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "traps.json"
    fixture.write_text(
        '[{"trap_id":1,"anchor_product_id":200,"target_product_ids":[201]}]',
        encoding="utf-8",
    )
    snapshot = type(
        "SnapshotAdapter",
        (),
        {
            "snapshot_dir": tmp_path,
            "user_map": {10: 1},
            "product_map": {200: 0, 201: 1, 202: 2},
        },
    )()
    prepared = type(
        "PreparedAdapter",
        (),
        {
            "split": SplitName.VAL,
            "eligible_users": np.asarray([1]),
            "latest_prior_purchase_contexts": {1: 0},
            "organic_novel_truth": {1: {1}},
        },
    )()
    cohort = tmp_path / "semantic-cohort.json"
    cohort.write_text(
        '[{"cohort_id":"semantic-1","event_id":"run:val:target:0","user_id":10,"product_id":201}]',
        encoding="utf-8",
    )
    with pytest.raises(DataIntegrityError, match="malformed"):
        _target_requests(snapshot, prepared, fixture)

    cohort.write_text(
        '[{"cohort_id":"semantic-1","event_id":"run:val:target:0",'
        '"user_id":10,"product_id":201,"anchor_product_id":202,'
        '"target_product_ids":[201]}]',
        encoding="utf-8",
    )
    with pytest.raises(DataIntegrityError, match="anchor"):
        _target_requests(snapshot, prepared, fixture)


def test_r3_semantic_cohort_requests_reject_empty_val_projection(tmp_path: Path) -> None:
    fixture = tmp_path / "traps.json"
    fixture.write_text("[]", encoding="utf-8")
    (tmp_path / "semantic-cohort.json").write_text(
        '[{"cohort_id":"cold-1","event_id":"run:val:target:0","user_id":10,"product_id":201}]',
        encoding="utf-8",
    )
    snapshot = type("SnapshotAdapter", (), {"snapshot_dir": tmp_path})()
    prepared = type("PreparedAdapter", (), {"split": SplitName.VAL})()
    with pytest.raises(DataIntegrityError, match="no serving-equivalent"):
        _target_requests(snapshot, prepared, fixture)


def test_r3_deep_comparison_orchestrates_four_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.train.campaign_stage = "diagnostic"
    settings.data.rule_feature_schema_version = "2.0.0"
    settings.train.seed = 42
    users = np.arange(1, 5, dtype=np.int64)

    def result(gauc: float) -> EvaluationResult:
        return EvaluationResult(
            report=_report(ModelVariant.DEEP_ONLY, gauc=gauc, hr=0.3, ndcg=0.2),
            user_ids=users,
            per_user_hr=np.full(4, 0.3),
            per_user_ndcg=np.full(4, 0.2),
            per_user_gauc=np.full(4, gauc),
            top_k_by_user={int(user): () for user in users},
        )

    class Evaluator:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def evaluate(self, *_args: object, **_kwargs: object) -> EvaluationResult:
            return result(0.7)

    monkeypatch.setattr(ablation, "FullCatalogEvaluator", Evaluator)
    monkeypatch.setattr(ablation, "prepare_split", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        ablation,
        "evaluate_random_baselines",
        lambda **_kwargs: [result(0.5) for _ in range(10)],
    )
    sentinel = object()
    monkeypatch.setattr(
        ablation, "publish_deep_ablation_artifact", lambda *args, **kwargs: sentinel
    )
    flags = ((True, True), (False, True), (True, False), (False, False))
    runs = tuple(
        DeepAblationRun(
            run_id=f"run-{index}",
            settings=copy.deepcopy(settings),
            lifecycle_status=ablation.RunStatus.TRAINING,
            git_commit="a" * 40,
            lineage={"snapshot": "b" * 64, "embedding": "c" * 64, "rules": "d" * 64},
            snapshot=object(),
            embeddings=np.zeros((4, 2), dtype=np.float32),
            rule_store=object(),
            model=object(),
        )
        for index, _flag in enumerate(flags)
    )
    for run, flag in zip(runs, flags, strict=True):
        run.settings.model.use_user_id_embedding = flag[0]
        run.settings.model.use_price_features = flag[1]
    published = ablation.run_deep_ablation_comparison(
        runs, artifact_root=tmp_path, device=torch.device("cpu")
    )
    assert published is sentinel


def test_rule_objective_masks_false_negative_and_routes_wide_gradient() -> None:
    positive = torch.tensor([1.0, 0.5], requires_grad=True)
    negative = torch.tensor([[0.0, 0.5], [0.0, -0.5]], requires_grad=True)
    mask = torch.tensor([[True, False], [True, True]])
    loss = rule_pairwise_wide_loss(positive, negative, negative_mask=mask)
    loss.backward()
    assert torch.isfinite(loss)
    assert negative.grad is not None
    assert negative.grad[0, 1].item() == 0.0

    vectors = torch.eye(2, requires_grad=True)
    positives = torch.eye(2)
    explicit = torch.zeros((2, 2, 2), requires_grad=True)
    zeros = torch.zeros((2, 2))
    explicit_wide = torch.zeros((2, 2), requires_grad=True)
    result = multi_positive_sampled_softmax(
        vectors,
        positives,
        explicit,
        positive_mask=torch.eye(2, dtype=torch.bool),
        denominator_mask=torch.ones((2, 2), dtype=torch.bool),
        confidence=torch.ones(2),
        temperature=torch.tensor(1.0),
        in_batch_wide_logits=zeros,
        explicit_wide_logits=explicit_wide,
        rule_positive_mask=torch.eye(2, dtype=torch.bool),
        rule_negative_mask=torch.ones((2, 2), dtype=torch.bool),
        rule_weight=0.1,
    )
    result.loss.backward()
    assert torch.isfinite(result.rule_loss)


def test_rule_objective_rejects_shape_and_empty_mask_contracts() -> None:
    with pytest.raises(ValueError, match="shapes"):
        rule_pairwise_wide_loss(torch.ones(1, 1), torch.ones(1, 2))
    with pytest.raises(ValueError, match="batch"):
        rule_pairwise_wide_loss(torch.ones(1), torch.ones(2, 2))
    with pytest.raises(ValueError, match="shape differs"):
        rule_pairwise_wide_loss(
            torch.ones(1), torch.ones(1, 2), negative_mask=torch.ones(1, 3, dtype=torch.bool)
        )
    empty = rule_pairwise_wide_loss(
        torch.ones(1, requires_grad=True),
        torch.ones(1, 2, requires_grad=True),
        negative_mask=torch.zeros(1, 2, dtype=torch.bool),
    )
    assert empty.item() == 0.0

    vectors = torch.eye(2)
    explicit = torch.zeros((2, 1, 2))
    kwargs = dict(
        positive_mask=torch.eye(2, dtype=torch.bool),
        denominator_mask=torch.ones((2, 2), dtype=torch.bool),
        confidence=torch.ones(2),
        temperature=torch.tensor(1.0),
        in_batch_wide_logits=torch.zeros((2, 2)),
        explicit_wide_logits=torch.zeros((2, 1)),
    )
    with pytest.raises(ValueError, match="rule_positive_mask"):
        multi_positive_sampled_softmax(
            vectors,
            vectors,
            explicit,
            **kwargs,
            rule_weight=0.1,
            rule_positive_mask=torch.zeros(1, 1, dtype=torch.bool),
        )
