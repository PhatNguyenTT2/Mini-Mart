from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ai_service.contracts import EvaluationReport, ModelVariant, SplitName
from ai_service.errors import ArtifactIntegrityError, VictoryGateError
from ai_service.evaluation.ablation import (
    compare_deep_ablations,
    load_deep_ablation_artifact,
    publish_deep_ablation_artifact,
    require_hybrid_diagnostic_signal,
    require_selected_r3_pair,
)
from ai_service.evaluation.full_catalog import EvaluationResult

_R3_LINEAGE = {"snapshot": "1" * 64, "embedding": "2" * 64, "rules": "3" * 64}


def _result(gauc: float, ndcg: float = 0.2, hr: float = 0.3) -> EvaluationResult:
    users = np.arange(1, 33, dtype=np.int64)
    return EvaluationResult(
        report=EvaluationReport(
            run_id="diagnostic",
            split=SplitName.VAL,
            variant=ModelVariant.DEEP_ONLY,
            num_total_users=len(users),
            num_eligible_users=len(users),
            num_users_without_novel_purchase=0,
            num_catalog_items=80,
            hr_at_k=hr,
            ndcg_at_k=ndcg,
            gauc=gauc,
            k=10,
        ),
        user_ids=users,
        per_user_hr=np.full(len(users), hr, dtype=np.float64),
        per_user_ndcg=np.full(len(users), ndcg, dtype=np.float64),
        per_user_gauc=np.full(len(users), gauc, dtype=np.float64),
        top_k_by_user={int(user): () for user in users},
    )


def test_ablation_selects_best_clear_improvement_and_publishes_immutably(
    tmp_path: Path,
) -> None:
    report, metrics = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(0.60),
        candidates={
            "diag-no-price": ("deep-no-price", _result(0.66, 0.25, 0.35)),
            "diag-no-user": ("deep-no-user-id", _result(0.70, 0.30, 0.40)),
            "diag-no-both": ("deep-no-price-no-user-id", _result(0.68, 0.28, 0.38)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    assert report.diagnostic_pause is False
    assert report.selected_run_id == "diag-no-user"
    assert all(candidate.eligible for candidate in report.candidates)
    artifact = publish_deep_ablation_artifact(
        tmp_path,
        diagnostic_signature="a" * 64,
        report=report,
        metrics=metrics,
        diagnostic_git_commit="a" * 40,
        lineage=_R3_LINEAGE,
    )
    assert artifact.report_path.is_file()
    assert artifact.metrics_path.is_file()
    assert load_deep_ablation_artifact(artifact.directory).report == artifact.report
    with pytest.raises(ArtifactIntegrityError, match="already exists"):
        publish_deep_ablation_artifact(
            tmp_path,
            diagnostic_signature="a" * 64,
            report=report,
            metrics=metrics,
            diagnostic_git_commit="a" * 40,
            lineage=_R3_LINEAGE,
        )


def test_ablation_artifact_rejects_corrupt_or_malformed_metrics(tmp_path: Path) -> None:
    report, metrics = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(0.60),
        candidates={
            "diag-a": ("deep-no-price", _result(0.66)),
            "diag-b": ("deep-no-user-id", _result(0.70)),
            "diag-c": ("deep-no-price-no-user-id", _result(0.68)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    with pytest.raises(ArtifactIntegrityError, match="unexpected keys"):
        publish_deep_ablation_artifact(
            tmp_path,
            diagnostic_signature="c" * 64,
            report=report,
            metrics={**metrics, "extra": np.ones(32, dtype=np.float64)},
            diagnostic_git_commit="a" * 40,
            lineage=_R3_LINEAGE,
        )
    assert not (tmp_path / "diagnostics" / "r3" / ("c" * 64)).exists()

    artifact = publish_deep_ablation_artifact(
        tmp_path,
        diagnostic_signature="d" * 64,
        report=report,
        metrics=metrics,
        diagnostic_git_commit="a" * 40,
        lineage=_R3_LINEAGE,
    )
    artifact.metrics_path.write_bytes(artifact.metrics_path.read_bytes() + b"corrupt")
    with pytest.raises(ArtifactIntegrityError, match="metrics file SHA mismatch"):
        load_deep_ablation_artifact(artifact.directory)


def test_ablation_artifact_rejects_metric_dtype_and_user_order(tmp_path: Path) -> None:
    report, metrics = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(0.60),
        candidates={
            "diag-a": ("deep-no-price", _result(0.66)),
            "diag-b": ("deep-no-user-id", _result(0.70)),
            "diag-c": ("deep-no-price-no-user-id", _result(0.68)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    wrong_dtype = dict(metrics)
    wrong_dtype["control_gauc"] = wrong_dtype["control_gauc"].astype(np.float32)
    with pytest.raises(ArtifactIntegrityError, match="finite float64"):
        publish_deep_ablation_artifact(
            tmp_path,
            diagnostic_signature="e" * 64,
            report=report,
            metrics=wrong_dtype,
            diagnostic_git_commit="a" * 40,
            lineage=_R3_LINEAGE,
        )
    wrong_users = dict(metrics)
    wrong_users["user_ids"] = wrong_users["user_ids"][::-1].copy()
    with pytest.raises(ArtifactIntegrityError, match="sorted unique int64"):
        publish_deep_ablation_artifact(
            tmp_path,
            diagnostic_signature="f" * 64,
            report=report,
            metrics=wrong_users,
            diagnostic_git_commit="a" * 40,
            lineage=_R3_LINEAGE,
        )


@pytest.mark.parametrize(
    ("control_gauc", "candidate_gauc", "reason"),
    [
        (0.54, 0.60, "control Deep GAUC is below 0.55"),
        (0.60, 0.60, "no ablation has positive paired GAUC CI versus control"),
        (0.60, 0.49, "catastrophic threshold 0.50"),
    ],
)
def test_ablation_diagnostic_pause_paths(
    control_gauc: float,
    candidate_gauc: float,
    reason: str,
) -> None:
    report, _ = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(control_gauc),
        candidates={
            "diag-a": ("deep-no-price", _result(candidate_gauc)),
            "diag-b": ("deep-no-user-id", _result(candidate_gauc)),
            "diag-c": ("deep-no-price-no-user-id", _result(candidate_gauc)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    assert report.diagnostic_pause is True
    assert report.selected_run_id is None
    assert any(reason in value for value in report.pause_reasons)


def test_ablation_rejects_gauc_only_candidate_with_topk_regression() -> None:
    report, _ = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(0.60, ndcg=0.20, hr=0.30),
        candidates={
            "diag-a": ("deep-no-price", _result(0.72, ndcg=0.01, hr=0.02)),
            "diag-b": ("deep-no-user-id", _result(0.61, ndcg=0.20, hr=0.30)),
            "diag-c": ("deep-no-price-no-user-id", _result(0.62, ndcg=0.20, hr=0.30)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    rejected = next(candidate for candidate in report.candidates if candidate.run_id == "diag-a")
    assert rejected.eligible is False
    assert report.diagnostic_pause is False
    assert report.selected_run_id != "diag-a"


def test_selected_pair_and_hybrid_wide_signal_are_required(tmp_path: Path) -> None:
    report, metrics = compare_deep_ablations(
        control_run_id="diag-control",
        control=_result(0.60),
        candidates={
            "diag-selected": ("deep-no-price", _result(0.70)),
            "diag-b": ("deep-no-user-id", _result(0.66)),
            "diag-c": ("deep-no-price-no-user-id", _result(0.68)),
        },
        random_per_user_gauc=np.full(32, 0.50, dtype=np.float64),
        random_per_user_hr=np.full(32, 0.05, dtype=np.float64),
        random_per_user_ndcg=np.full(32, 0.02, dtype=np.float64),
        bootstrap_samples=64,
        minimum_control_gauc=0.55,
        gauc_guardrail_delta=-0.002,
        hr_guardrail_delta=-0.001,
        ndcg_guardrail_delta=-0.001,
    )
    artifact = publish_deep_ablation_artifact(
        tmp_path,
        diagnostic_signature="b" * 64,
        report=report,
        metrics=metrics,
        diagnostic_git_commit="a" * 40,
        lineage=_R3_LINEAGE,
    )
    selected = require_selected_r3_pair(
        artifact_root=tmp_path,
        selected_deep_run_id="diag-selected",
        hybrid_flags=(True, False),
        deep_flags=(True, False),
    )
    assert selected.selected_diagnostic_run_id == "diag-selected"
    production_selected = require_selected_r3_pair(
        artifact_root=tmp_path,
        hybrid_flags=(True, False),
        deep_flags=(True, False),
        campaign_stage="production",
        selection_artifact_sha256=artifact.report.artifact_sha256,
        lineage=_R3_LINEAGE,
    )
    assert production_selected.selected_diagnostic_run_id == "diag-selected"
    with pytest.raises(ArtifactIntegrityError, match="flags"):
        require_selected_r3_pair(
            artifact_root=tmp_path,
            selected_deep_run_id="diag-selected",
            hybrid_flags=(False, True),
            deep_flags=(True, False),
        )

    history = tmp_path / "history.jsonl"
    history.write_text(
        "\n".join(
            (
                '{"epoch":1,"wide_gradient_norm":0.2,"rows_with_any_rule_rate":0.5,'
                '"wide_to_deep_logit_rms_ratio":0.02,"hybrid_deep_top_k_change_rate":0.06}',
                '{"epoch":2,"wide_gradient_norm":0.1,"rows_with_any_rule_rate":0.6,'
                '"wide_to_deep_logit_rms_ratio":0.03,"hybrid_deep_top_k_change_rate":0.08}',
            )
        ),
        encoding="utf-8",
    )
    require_hybrid_diagnostic_signal(
        history,
        best_epoch=2,
        minimum_rule_row_rate=0.4,
        minimum_wide_deep_ratio=0.01,
        minimum_top_k_change_rate=0.05,
    )
    history.write_text(
        '{"epoch":1,"wide_gradient_norm":0.0,"rows_with_any_rule_rate":0.5,'
        '"wide_to_deep_logit_rms_ratio":0.02,"hybrid_deep_top_k_change_rate":0.06}',
        encoding="utf-8",
    )
    with pytest.raises(VictoryGateError, match="Wide gradient"):
        require_hybrid_diagnostic_signal(
            history,
            best_epoch=1,
            minimum_rule_row_rate=0.4,
            minimum_wide_deep_ratio=0.01,
            minimum_top_k_change_rate=0.05,
        )
