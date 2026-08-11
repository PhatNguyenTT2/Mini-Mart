from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ai_service.artifact_io import canonical_json_sha256
from ai_service.cli import build_parser
from ai_service.contracts import (
    ArtifactLineage,
    CohortMetricDelta,
    R3DiagnosticReport,
    RuleAlignmentEvidence,
    TrapDiagnosticEvidence,
)
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation.r3_diagnostics import (
    _cohort_delta,
    _load_existing_pair_metrics,
    _repo_file,
    _sha256_file,
    _target_requests,
    _validate_metrics,
    _write_metrics,
    load_r3_diagnostic,
)


def _report() -> R3DiagnosticReport:
    delta = (
        CohortMetricDelta(
            cohort_name="aligned",
            user_count=1,
            hybrid_minus_deep_gauc=0.1,
            hybrid_minus_deep_hr_at_k=0.1,
            hybrid_minus_deep_ndcg_at_k=0.1,
        ),
        CohortMetricDelta(
            cohort_name="unaligned",
            user_count=1,
            hybrid_minus_deep_gauc=0.0,
            hybrid_minus_deep_hr_at_k=0.0,
            hybrid_minus_deep_ndcg_at_k=0.0,
        ),
    )
    trap = tuple(
        TrapDiagnosticEvidence(
            trap_id=trap_id,
            anchor_raw_id=1000 + trap_id,
            target_raw_ids=(2000 + trap_id,),
            anchor_internal_id=trap_id,
            target_internal_ids=(trap_id + 1,),
            rule_present=(True,),
            raw_lifts=(2.0,),
            item_query_deep_rank=11,
            item_query_hybrid_rank=10,
            serving_deep_rank=11,
            serving_hybrid_rank=10,
            deep_top_k_cutoff=0.1,
            learned_wide_bonus=1.0,
            required_wide_bonus=0.1,
        )
        for trap_id in range(1, 11)
    )
    return R3DiagnosticReport(
        schema_version="1.0.0",
        evaluation_schema_version="5.2.0",
        split="val",
        hybrid_run_id="hybrid",
        deep_run_id="deep",
        hybrid_checkpoint_sha256="a" * 64,
        deep_checkpoint_sha256="b" * 64,
        git_commit="c" * 40,
        lineage=ArtifactLineage(
            snapshot_sha256="d" * 64,
            embedding_sha256="e" * 64,
            rule_sha256="f" * 64,
        ),
        comparison_signature_sha256="1" * 64,
        benchmark_spec_sha256="2" * 64,
        semantic_cohort_sha256="3" * 64,
        rule_alignment=RuleAlignmentEvidence(
            training_targets=1,
            strict_training_rule_targets=1,
            strict_training_rule_rate=1.0,
            positive_other_rule_hits=0,
            in_batch_negative_rule_hits=0,
            explicit_negative_rule_hits=0,
            negative_only_rows=0,
            val_eligible_users=1,
            val_rule_aligned_users=1,
            val_rule_aligned_rate=1.0,
        ),
        cohort_deltas=delta,
        trap_evidence=trap,
        alpha_sweep=tuple(
            {
                "alpha": alpha,
                "gauc": 0.7,
                "hr_at_k": 0.15,
                "ndcg_at_k": 0.08,
                "meets_absolute_floors": True,
            }
            for alpha in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
        ),
        per_user_metrics_sha256="4" * 64,
        artifact_sha256="5" * 64,
    )


def test_r3_contract_requires_all_traps_and_canonical_alpha() -> None:
    report = _report()
    assert len(report.trap_evidence) == 10
    with pytest.raises(ValueError, match="trap IDs"):
        R3DiagnosticReport.model_validate(
            {**report.model_dump(), "trap_evidence": report.trap_evidence[:-1]}
        )


def test_r3_cli_is_read_only_val_only() -> None:
    args = build_parser().parse_args(["diagnose-r3", "--hybrid-run-id", "h", "--deep-run-id", "d"])
    assert args.command == "diagnose-r3"
    assert args.split == "val"


def test_r3_metrics_loader_rejects_extra_keys(tmp_path: Path) -> None:
    path = tmp_path / "metrics.npz"
    np.savez(
        path,
        user_ids=np.asarray([1], dtype=np.int64),
        deep_hr=np.asarray([0.0], dtype=np.float64),
        deep_ndcg=np.asarray([0.0], dtype=np.float64),
        deep_gauc=np.asarray([0.5], dtype=np.float64),
        hybrid_hr=np.asarray([0.0], dtype=np.float64),
        hybrid_ndcg=np.asarray([0.0], dtype=np.float64),
        hybrid_gauc=np.asarray([0.5], dtype=np.float64),
        alpha_hr=np.zeros(7, dtype=np.float64),
        alpha_ndcg=np.zeros(7, dtype=np.float64),
        alpha_gauc=np.ones(7, dtype=np.float64) * 0.5,
        extra=np.asarray([1]),
    )
    with pytest.raises(ArtifactIntegrityError, match="unexpected key"):
        _validate_metrics(path)


def test_r3_metrics_loader_accepts_exact_archive_and_cohort_math(tmp_path: Path) -> None:
    values = {
        "user_ids": np.asarray([1, 2], dtype=np.int64),
        "aligned_mask": np.asarray([True, False], dtype=np.bool_),
        "deep_hr": np.asarray([0.0, 1.0], dtype=np.float64),
        "deep_ndcg": np.asarray([0.0, 0.5], dtype=np.float64),
        "deep_gauc": np.asarray([0.5, 0.6], dtype=np.float64),
        "hybrid_hr": np.asarray([1.0, 1.0], dtype=np.float64),
        "hybrid_ndcg": np.asarray([0.5, 0.5], dtype=np.float64),
        "hybrid_gauc": np.asarray([0.7, 0.8], dtype=np.float64),
        "alpha_hr": np.zeros((7, 2), dtype=np.float64),
        "alpha_ndcg": np.zeros((7, 2), dtype=np.float64),
        "alpha_gauc": np.ones((7, 2), dtype=np.float64) * 0.5,
    }
    path = tmp_path / "metrics.npz"
    _write_metrics(path, values)
    loaded = _validate_metrics(path)
    assert loaded["user_ids"].tolist() == [1, 2]
    delta = _cohort_delta(
        "aligned",
        loaded["user_ids"],
        {1},
        np.vstack((values["deep_gauc"], values["deep_hr"], values["deep_ndcg"])),
        np.vstack((values["hybrid_gauc"], values["hybrid_hr"], values["hybrid_ndcg"])),
    )
    assert delta.user_count == 1
    assert delta.hybrid_minus_deep_hr_at_k == 1.0


def test_r3_pair_metrics_use_hybrid_owned_deep_arrays(tmp_path: Path) -> None:
    hybrid_dir = tmp_path / "hybrid" / "evaluation" / "val"
    hybrid_dir.mkdir(parents=True)
    np.savez(
        hybrid_dir / "per-user-metrics.npz",
        user_ids=np.asarray([1, 2], dtype=np.int64),
        hybrid_hr=np.asarray([0.0, 1.0]),
        hybrid_ndcg=np.asarray([0.0, 0.5]),
        hybrid_gauc=np.asarray([0.5, 0.6]),
        deep_hr=np.asarray([0.0, 0.5]),
        deep_ndcg=np.asarray([0.0, 0.25]),
        deep_gauc=np.asarray([0.4, 0.5]),
    )
    loaded = _load_existing_pair_metrics(
        SimpleNamespace(run_dir=tmp_path / "hybrid"),
        SimpleNamespace(run_dir=tmp_path / "deep"),
    )
    assert loaded["deep_gauc"].tolist() == [0.4, 0.5]


def test_r3_helpers_cover_hash_and_target_request_contract(tmp_path: Path) -> None:
    fixture = tmp_path / "traps.json"
    fixture.write_text(
        '[{"trap_id": 1, "anchor_product_id": 200, "target_product_ids": [201]}]',
        encoding="utf-8",
    )
    prepared = SimpleNamespace(eligible_users=np.asarray([1, 2]), seen_items={1: set(), 2: {1}})
    snapshot = SimpleNamespace(product_map={200: 0, 201: 1})
    requests = _target_requests(snapshot, prepared, fixture)
    assert requests[0].user_id == 1
    assert len(_sha256_file(fixture)) == 64
    assert _repo_file("benchmark-spec-v4.json").is_file()


def test_r3_metrics_rejects_wrong_alpha_shape_and_cohort_delta_is_stable(tmp_path: Path) -> None:
    values = {
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
    path = tmp_path / "metrics.npz"
    _write_metrics(path, values)
    loaded = _validate_metrics(path)
    assert loaded["aligned_mask"].dtype == np.bool_
    with pytest.raises(ArtifactIntegrityError):
        _write_metrics(path, {**values, "alpha_hr": np.zeros(7, dtype=np.float64)})
    delta = _cohort_delta(
        "unaligned",
        np.asarray([1, 2], dtype=np.int64),
        {1},
        np.asarray([[0.5, 0.5], [0.1, 0.1], [0.2, 0.2]]),
        np.asarray([[0.6, 0.4], [0.2, 0.3], [0.3, 0.1]]),
    )
    assert delta.user_count == 1
    assert delta.hybrid_minus_deep_hr_at_k == pytest.approx(0.2)


def test_r3_verified_loader_binds_report_and_npz_hashes(tmp_path: Path) -> None:
    directory = tmp_path / "diagnostic"
    directory.mkdir()
    values = {
        "user_ids": np.asarray([1], dtype=np.int64),
        "aligned_mask": np.asarray([True], dtype=np.bool_),
        "deep_hr": np.asarray([0.1], dtype=np.float64),
        "deep_ndcg": np.asarray([0.1], dtype=np.float64),
        "deep_gauc": np.asarray([0.6], dtype=np.float64),
        "hybrid_hr": np.asarray([0.2], dtype=np.float64),
        "hybrid_ndcg": np.asarray([0.2], dtype=np.float64),
        "hybrid_gauc": np.asarray([0.7], dtype=np.float64),
        "alpha_hr": np.zeros((7, 1), dtype=np.float64),
        "alpha_ndcg": np.zeros((7, 1), dtype=np.float64),
        "alpha_gauc": np.full((7, 1), 0.5, dtype=np.float64),
    }
    metrics_path = directory / "per-user-metrics.npz"
    _write_metrics(metrics_path, values)
    report = _report().model_dump(mode="json")
    report["hybrid_run_id"] = "hybrid"
    report["deep_run_id"] = "deep"
    report["per_user_metrics_sha256"] = _sha256_file(metrics_path)
    report["artifact_sha256"] = canonical_json_sha256(
        {key: value for key, value in report.items() if key != "artifact_sha256"}
    )
    (directory / "report.json").write_text(
        R3DiagnosticReport.model_validate(report).model_dump_json(), encoding="utf-8"
    )
    loaded = load_r3_diagnostic(
        directory,
        expected_hybrid_run_id="hybrid",
        expected_deep_run_id="deep",
        expected_lineage=R3DiagnosticReport.model_validate(report).lineage,
        expected_comparison_signature="1" * 64,
    )
    assert loaded.report.artifact_sha256 == report["artifact_sha256"]
    metrics_path.write_bytes(metrics_path.read_bytes() + b"tamper")
    with pytest.raises(ArtifactIntegrityError, match="metrics hash"):
        load_r3_diagnostic(
            directory,
            expected_hybrid_run_id="hybrid",
            expected_deep_run_id="deep",
            expected_lineage=R3DiagnosticReport.model_validate(report).lineage,
            expected_comparison_signature="1" * 64,
        )
