from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.cli import main
from ai_service_v2.errors import IntegrityError
from ai_service_v2.evaluation.artifacts import load_score_matrix
from ai_service_v2.evaluation.components import load_hybrid_score_components
from ai_service_v2.evaluation.persistence import load_evaluation
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json, sha256_bytes
from ai_service_v2.protocol import load_protocol
from ai_service_v2.training import load_run_command

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
    train_argv = [
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
    assert main(train_argv) == 0
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
    command = load_run_command(run_root)
    assert command.executable == str(Path(sys.executable).resolve())
    assert command.argv == tuple(train_argv)
    assert command.argv_source == "provided_main_argv"
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "PASS"


def test_cli_has_no_self_asserted_command_text_option(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "train",
                str(tmp_path / "snapshot"),
                str(tmp_path / "protocol.json"),
                str(tmp_path / "run"),
                "--command-text",
                "caller-controlled prose",
            ]
        )


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


def test_cli_validation_and_fixture_training_work_with_test_file_absent(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshot-with-sealed-test"
    snapshot_root.mkdir()
    for source in FIXTURE_ROOT.iterdir():
        if source.name != "test.jsonl":
            (snapshot_root / source.name).write_bytes(source.read_bytes())
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run"

    assert main(["build-protocol", str(snapshot_root), str(protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(snapshot_root),
                str(protocol_path),
                str(run_root),
                "--fixture-only",
                "--feature-dim",
                "8",
            ]
        )
        == 0
    )
    assert not (snapshot_root / "test.jsonl").exists()
    assert load_run_command(run_root).argv[0] == "train"


def test_cli_requires_explicit_fixture_authorization(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert main(["build-protocol", str(snapshot_root), str(protocol_path), "--cutoff", "5"]) == 0
    assert main(["train", str(snapshot_root), str(protocol_path), str(tmp_path / "run")]) == 2
    assert "explicit --fixture-only" in capsys.readouterr().out


def test_fixture_only_rejects_forged_fixture_labels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    manifest_path = snapshot_root / "manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["dataset_id"] = "fixture-counterfeit"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    assert main(["build-protocol", str(snapshot_root), str(protocol_path), "--cutoff", "5"]) == 0

    result = main(
        [
            "train",
            str(snapshot_root),
            str(protocol_path),
            str(run_root),
            "--fixture-only",
            "--feature-dim",
            "8",
        ]
    )

    assert result == 2
    assert "exact repository fixture" in capsys.readouterr().out


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
    loaded = load_hybrid_score_components(
        component_root,
        run_root=run_root,
        protocol=load_protocol(protocol_path),
    )
    deep = load_score_matrix(loaded.components["deep"])
    wide = load_score_matrix(loaded.components["wide"])
    hybrid = load_score_matrix(loaded.components["hybrid"])
    assert np.allclose(hybrid, deep + 0.5 * wide)
    manifest = load_strict_json(component_root / "component_manifest.json")
    assert set(manifest["components"]) == {"deep", "wide", "hybrid"}
    assert manifest["fusion_normalization"] == "per_user_zscore"
    assert (run_root / "component_score_artifact_ref.json").is_file()
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["test_set_opened"] is False


def test_hybrid_component_loader_rejects_encoding_and_binding_drift(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run-hybrid"
    component_root = tmp_path / "components-hybrid"
    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert main(["build-protocol", str(snapshot_root), str(protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(snapshot_root),
                str(protocol_path),
                str(run_root),
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
    protocol = load_protocol(protocol_path)
    manifest_path = component_root / "component_manifest.json"
    reference_path = run_root / "component_score_artifact_ref.json"
    original = load_strict_json(manifest_path)
    original_payload = manifest_path.read_bytes()
    original_reference = load_strict_json(reference_path)

    def assert_rejected(payload: bytes) -> None:
        manifest_path.write_bytes(payload)
        reference = copy.deepcopy(original_reference)
        reference["manifest_sha256"] = sha256_bytes(payload)
        reference_path.write_bytes(canonical_json_bytes(reference) + b"\n")
        with pytest.raises(IntegrityError):
            load_hybrid_score_components(
                component_root,
                run_root=run_root,
                protocol=protocol,
            )

    semantic_mutations = {
        "unknown": lambda value: value.update({"unknown": "field"}),
        "model_spec": lambda value: value["model_spec"].update({"wide_weight": 0.75}),
        "descriptor": lambda value: value["descriptor"].update({"config_sha256": "0" * 64}),
        "model_artifact": lambda value: value.update({"model_artifact_sha256": "0" * 64}),
        "checkpoint_manifest": lambda value: value.update({"checkpoint_manifest_sha256": "0" * 64}),
        "checkpoint": lambda value: value.update({"checkpoint_sha256": "0" * 64}),
        "feature": lambda value: value.update({"feature_content_sha256": "0" * 64}),
        "rule": lambda value: value.update({"rule_artifact_sha256": "0" * 64}),
        "protocol": lambda value: value.update({"protocol_manifest_sha256": "0" * 64}),
        "candidate": lambda value: value.update({"candidate_order_sha256": "0" * 64}),
        "normalization": lambda value: value.update({"fusion_normalization": "none"}),
        "weight": lambda value: value.update({"wide_weight": 0.75}),
        "child": lambda value: value["components"]["deep"].update({"manifest_sha256": "0" * 64}),
    }
    for mutate in semantic_mutations.values():
        changed = copy.deepcopy(original)
        mutate(changed)
        assert_rejected(canonical_json_bytes(changed) + b"\n")

    canonical = canonical_json_bytes(original) + b"\n"
    assert_rejected(b"\xef\xbb\xbf" + canonical)
    assert_rejected(
        canonical.replace(
            b'{"candidate_order_sha256":',
            b'{"run_id":"duplicate-a","run_id":"duplicate-b","candidate_order_sha256":',
            1,
        )
    )
    assert_rejected(b'{"Run_ID":"case-collision",' + canonical[1:])

    manifest_path.write_bytes(original_payload)
    reference_path.write_bytes(canonical_json_bytes(original_reference) + b"\n")
    load_hybrid_score_components(component_root, run_root=run_root, protocol=protocol)
