from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.cli import main
from ai_service_v2.evaluation.artifacts import load_materialized_scores, load_score_matrix
from ai_service_v2.evaluation.persistence import load_evaluation
from ai_service_v2.hashing import load_strict_json
from ai_service_v2.protocol import load_protocol

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fixture-retail-v1"


def test_cli_fixture_pipeline_keeps_test_sealed_and_persists_receipts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run-42"
    score_root = tmp_path / "scores-42"
    evaluation_root = tmp_path / "evaluation-42"

    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(protocol_path),
                "--split",
                "val",
                "--cutoff",
                "5",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "train",
                str(snapshot_root),
                str(protocol_path),
                str(run_root),
                "--seed",
                "42",
                "--feature-dim",
                "8",
                "--fixture-only",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "export-scores",
                str(snapshot_root),
                str(run_root),
                str(protocol_path),
                str(score_root),
                "--chunk-size",
                "1",
            ]
        )
        == 0
    )
    assert main(["evaluate", str(protocol_path), str(score_root), str(evaluation_root)]) == 0
    persisted = load_evaluation(evaluation_root)
    assert persisted.receipt.verdict == "PASS"
    assert persisted.receipt.num_eligible_users == 2
    assert load_protocol(protocol_path).manifest.test_set_opened is False
    assert load_strict_json(run_root / "run_manifest.json")["status"] == "PASS"
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "PASS"


def test_cli_refuses_test_protocol_without_explicit_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(tmp_path / "test-protocol.json"),
                "--split",
                "test",
            ]
        )
        == 2
    )
    assert "TEST is sealed" in capsys.readouterr().out


def test_cli_requires_explicit_fixture_authorization(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert main(["build-protocol", str(snapshot_root), str(protocol_path), "--cutoff", "5"]) == 0
    assert main(["train", str(snapshot_root), str(protocol_path), str(tmp_path / "run")]) == 2
    assert "explicit --fixture-only" in capsys.readouterr().out


@pytest.mark.parametrize("model_kind", ("random", "mostpop", "rule_only", "hybrid"))
def test_cli_supports_registered_local_ablations(
    model_kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / f"run-{model_kind}"
    score_root = tmp_path / f"scores-{model_kind}"
    evaluation_root = tmp_path / f"evaluation-{model_kind}"

    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(protocol_path),
                "--split",
                "val",
                "--cutoff",
                "5",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "train",
                str(snapshot_root),
                str(protocol_path),
                str(run_root),
                "--seed",
                "42",
                "--feature-dim",
                "8",
                "--fixture-only",
                "--model-kind",
                model_kind,
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "export-scores",
                str(snapshot_root),
                str(run_root),
                str(protocol_path),
                str(score_root),
                "--chunk-size",
                "1",
            ]
        )
        == 0
    )
    assert main(["evaluate", str(protocol_path), str(score_root), str(evaluation_root)]) == 0
    assert load_evaluation(evaluation_root).receipt.verdict == "PASS"
    assert capsys.readouterr().out.splitlines()[-1]


def test_cli_hybrid_exports_bound_deep_wide_and_hybrid_components(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run-hybrid"
    component_root = tmp_path / "components-hybrid"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(protocol_path),
                "--split",
                "val",
                "--cutoff",
                "5",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "train",
                str(snapshot_root),
                str(protocol_path),
                str(run_root),
                "--seed",
                "42",
                "--feature-dim",
                "8",
                "--fixture-only",
                "--model-kind",
                "hybrid",
                "--wide-weight",
                "0.5",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "export-score-components",
                str(snapshot_root),
                str(run_root),
                str(protocol_path),
                str(component_root),
                "--chunk-size",
                "1",
            ]
        )
        == 0
    )
    deep = load_score_matrix(load_materialized_scores(component_root / "deep"))
    wide = load_score_matrix(load_materialized_scores(component_root / "wide"))
    hybrid = load_score_matrix(load_materialized_scores(component_root / "hybrid"))
    assert np.allclose(hybrid, deep + 0.5 * wide)
    manifest = load_strict_json(component_root / "component_manifest.json")
    assert set(manifest["components"]) == {"deep", "wide", "hybrid"}
    assert manifest["fusion_normalization"] == "per_user_zscore"
    assert (run_root / "component_score_artifact_ref.json").is_file()
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["test_set_opened"] is False
