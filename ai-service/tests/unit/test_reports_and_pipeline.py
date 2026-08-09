"""Unit tests for report generator and pipeline script modules."""

import pytest
from reports.generate_report import build_markdown_report, generate_evaluation_reports
from evaluation.full_catalog_eval import EvaluationReport
from evaluation.semantic_traps import SemanticTrapsReport, TrapResult
from evaluation.cold_start_eval import ColdStartReport
from evaluation.baselines import BaselineComparisonReport


def test_generate_report_markdown_and_json(tmp_path):
    eval_report = EvaluationReport(
        split="test",
        num_eval_users=50,
        num_catalog_items=5200,
        hr10=0.25,
        ndcg10=0.18,
        gauc=0.78,
        avg_latency_ms=0.85,
        total_eval_time_sec=1.2,
    )

    trap_res = [
        TrapResult(
            trap_id=1,
            name="Tã quần Bobby -> Bia Heineken",
            anchor_product_id=1010,
            target_product_ids=[1050],
            deep_ranks=[450],
            hybrid_ranks=[3],
            hybrid_hr10=1.0,
            hybrid_ndcg10=0.5,
            improved=True,
        )
    ]
    traps_report = SemanticTrapsReport(
        num_traps=1,
        num_improved_traps=1,
        mean_hybrid_hr10=1.0,
        mean_hybrid_ndcg10=0.5,
        trap_results=trap_res,
    )

    cold_report = ColdStartReport(
        num_cold_items=250,
        num_eval_cold_items=250,
        zero_shot_hr10=0.12,
        zero_shot_ndcg10=0.08,
        coverage_ratio=1.0,
        all_scores_finite=True,
        train_leakage_detected=False,
    )

    baselines_report = BaselineComparisonReport(
        num_eval_users=50,
        num_catalog_items=5200,
        baselines={"Proposed Hybrid (Ours)": eval_report},
    )

    md_path, json_path = generate_evaluation_reports(
        eval_report, traps_report, cold_report, baselines_report, output_dir=tmp_path
    )

    assert md_path.exists()
    assert json_path.exists()

    content = md_path.read_text(encoding="utf-8")
    assert "Production Hybrid Recommender AI-Service" in content
    assert "Macro-GAUC" in content
    assert "Zero-Leakage Guarantee" in content
