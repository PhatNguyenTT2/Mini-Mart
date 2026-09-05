from __future__ import annotations

import copy
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from ai_service_v2.cli import main
from ai_service_v2.errors import IntegrityError
from ai_service_v2.evaluation.artifacts import load_score_matrix
from ai_service_v2.evaluation.components import load_hybrid_score_components
from ai_service_v2.evaluation.persistence import load_evaluation
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json, sha256_bytes
from ai_service_v2.models.registry import ModelRunSpec, default_spec, descriptor_for_spec
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


def test_cli_keeps_legacy_model_specs_inspection_only_before_run_creation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "legacy-run"
    config_path = tmp_path / "legacy-model-spec.json"
    assert main(["build-protocol", str(FIXTURE_ROOT), str(protocol_path), "--cutoff", "5"]) == 0
    legacy = default_spec("hybrid", feature_dimensions=8).to_mapping()
    legacy.pop("fusion_normalization")
    legacy["schema_version"] = "model-run-spec/1.0"
    config_path.write_bytes(canonical_json_bytes(legacy) + b"\n")

    result = main(
        [
            "train",
            str(FIXTURE_ROOT),
            str(protocol_path),
            str(run_root),
            "--config",
            str(config_path),
            "--fixture-only",
        ]
    )

    assert result == 2
    assert "inspection-only" in capsys.readouterr().out
    assert not run_root.exists()


def test_cli_non_fixture_training_requires_process_argv_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "non-fixture-run"
    environment_lock = tmp_path / "environment.lock"
    environment_lock.write_bytes(b"immutable environment lock")
    assert main(["build-protocol", str(FIXTURE_ROOT), str(protocol_path), "--cutoff", "5"]) == 0
    capsys.readouterr()

    # Use the repository fixture only as a bounded input carrier; these gates
    # make the admission path treat it as an admitted non-fixture snapshot.
    monkeypatch.setattr("ai_service_v2.cli._is_repository_fixture", lambda _manifest: False)
    monkeypatch.setattr(
        "ai_service_v2.cli.assess_snapshot_suitability",
        lambda _snapshot: SimpleNamespace(
            verdict="PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY",
            blocking_findings=(),
        ),
    )

    result = main(
        [
            "train",
            str(FIXTURE_ROOT),
            str(protocol_path),
            str(run_root),
            "--environment-lock",
            str(environment_lock),
        ]
    )

    assert result == 2
    assert "process_sys_argv" in capsys.readouterr().out
    assert not run_root.exists()


@pytest.mark.parametrize("command", ("export-scores", "export-score-components"))
def test_cli_refuses_evidence_export_from_an_inspectable_legacy_run(
    command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run"
    output_root = tmp_path / "evidence"
    assert main(["build-protocol", str(FIXTURE_ROOT), str(protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(FIXTURE_ROOT),
                str(protocol_path),
                str(run_root),
                "--fixture-only",
                "--model-kind",
                "hybrid",
                "--feature-dim",
                "8",
                "--wide-weight",
                "0.5",
            ]
        )
        == 0
    )

    legacy = default_spec("hybrid", feature_dimensions=8, wide_weight=0.5).to_mapping()
    legacy.pop("fusion_normalization")
    legacy["schema_version"] = "model-run-spec/1.0"
    legacy_spec = ModelRunSpec.from_mapping(legacy)
    legacy_descriptor = descriptor_for_spec(legacy_spec).to_mapping()
    (run_root / "config.json").write_bytes(canonical_json_bytes(legacy) + b"\n")
    model_artifact_path = run_root / "model_artifact.json"
    model_artifact = load_strict_json(model_artifact_path)
    model_artifact["model_spec_sha256"] = sha256_bytes(canonical_json_bytes(legacy))
    model_artifact["descriptor"] = legacy_descriptor
    model_artifact["fusion_normalization"] = "none"
    model_artifact_path.write_bytes(canonical_json_bytes(model_artifact) + b"\n")
    checkpoint_manifest_path = run_root / "checkpoint" / "manifest.json"
    checkpoint_manifest = load_strict_json(checkpoint_manifest_path)
    checkpoint_manifest["descriptor"] = legacy_descriptor
    checkpoint_manifest_path.write_bytes(canonical_json_bytes(checkpoint_manifest) + b"\n")

    result = main(
        [
            command,
            str(FIXTURE_ROOT),
            str(run_root),
            str(protocol_path),
            str(output_root),
        ]
    )

    assert result == 2
    assert "inspection-only" in capsys.readouterr().out
    assert not output_root.exists()


def test_cli_pass_run_consumers_replay_persisted_command_before_use(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run"
    score_root = tmp_path / "scores"
    component_root = tmp_path / "components"
    assert main(["build-protocol", str(FIXTURE_ROOT), str(protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(FIXTURE_ROOT),
                str(protocol_path),
                str(run_root),
                "--fixture-only",
                "--model-kind",
                "hybrid",
                "--feature-dim",
                "8",
            ]
        )
        == 0
    )
    command_path = run_root / "command.json"
    command = load_strict_json(command_path)
    command["argv"].append("--tampered-after-run")
    command_path.write_bytes(canonical_json_bytes(command) + b"\n")

    assert (
        main(
            [
                "export-scores",
                str(FIXTURE_ROOT),
                str(run_root),
                str(protocol_path),
                str(score_root),
            ]
        )
        == 2
    )
    assert "command hash" in capsys.readouterr().out
    assert not score_root.exists()

    assert (
        main(
            [
                "export-score-components",
                str(FIXTURE_ROOT),
                str(run_root),
                str(protocol_path),
                str(component_root),
            ]
        )
        == 2
    )
    assert "command hash" in capsys.readouterr().out
    assert not component_root.exists()

    assert main(["summarize-run", str(run_root)]) == 2
    assert "command hash" in capsys.readouterr().out


def test_cli_pass_run_consumers_reject_missing_persisted_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol_path = tmp_path / "val-protocol.json"
    run_root = tmp_path / "run"
    score_root = tmp_path / "scores"
    assert main(["build-protocol", str(FIXTURE_ROOT), str(protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(FIXTURE_ROOT),
                str(protocol_path),
                str(run_root),
                "--fixture-only",
                "--model-kind",
                "mostpop",
            ]
        )
        == 0
    )
    (run_root / "command.json").unlink()

    assert (
        main(
            [
                "export-scores",
                str(FIXTURE_ROOT),
                str(run_root),
                str(protocol_path),
                str(score_root),
            ]
        )
        == 2
    )
    assert not score_root.exists()
    assert main(["summarize-run", str(run_root)]) == 2
    assert "command.json" in capsys.readouterr().out


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


def test_validation_selected_run_can_score_matching_explicit_test_protocol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot_root = tmp_path / "snapshot"
    val_protocol_path = tmp_path / "val-protocol.json"
    test_protocol_path = tmp_path / "test-protocol.json"
    run_root = tmp_path / "run-mostpop"
    val_score_root = tmp_path / "val-scores"
    test_score_root = tmp_path / "test-scores"
    test_evaluation_root = tmp_path / "test-evaluation"
    application_ref_root = tmp_path / "test-application-references"
    application_ref_root.mkdir()
    application_ref = application_ref_root / "run-mostpop.json"

    assert main(["materialize-snapshot", str(FIXTURE_ROOT), str(snapshot_root)]) == 0
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(val_protocol_path),
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
                str(val_protocol_path),
                str(run_root),
                "--fixture-only",
                "--model-kind",
                "mostpop",
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
                str(val_protocol_path),
                str(val_score_root),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build-protocol",
                str(snapshot_root),
                str(test_protocol_path),
                "--split",
                "test",
                "--allow-test",
                "--cutoff",
                "5",
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
                str(test_protocol_path),
                str(test_score_root),
                "--application-ref",
                str(application_ref),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "evaluate",
                str(test_protocol_path),
                str(test_score_root),
                str(test_evaluation_root),
            ]
        )
        == 0
    )

    assert (run_root / "score_artifact_ref.json").is_file()
    assert not (run_root / "score_artifact_ref.test.json").exists()
    test_reference = load_strict_json(application_ref)
    assert test_reference["split"] == "test"
    assert test_reference["test_set_opened"] is True
    assert (
        test_reference["selection_protocol_manifest_sha256"]
        != test_reference["scoring_protocol_manifest_sha256"]
    )
    assert load_evaluation(test_evaluation_root).receipt.verdict == "PASS"
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "PASS"


def test_test_score_export_rejects_different_validation_cutoff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    val_protocol_path = tmp_path / "val-protocol.json"
    test_protocol_path = tmp_path / "test-protocol.json"
    run_root = tmp_path / "run-mostpop"
    score_root = tmp_path / "test-scores"
    application_ref_root = tmp_path / "test-application-references"
    application_ref_root.mkdir()

    assert main(["build-protocol", str(FIXTURE_ROOT), str(val_protocol_path), "--cutoff", "5"]) == 0
    assert (
        main(
            [
                "train",
                str(FIXTURE_ROOT),
                str(val_protocol_path),
                str(run_root),
                "--fixture-only",
                "--model-kind",
                "mostpop",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build-protocol",
                str(FIXTURE_ROOT),
                str(test_protocol_path),
                "--split",
                "test",
                "--allow-test",
                "--cutoff",
                "4",
            ]
        )
        == 0
    )

    result = main(
        [
            "export-scores",
            str(FIXTURE_ROOT),
            str(run_root),
            str(test_protocol_path),
            str(score_root),
            "--application-ref",
            str(application_ref_root / "run-mostpop.json"),
        ]
    )

    assert result == 2
    assert "validation counterpart" in capsys.readouterr().out
    assert not score_root.exists()


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

    semantic_mutations: dict[str, Callable[[dict[str, Any]], None]] = {
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
