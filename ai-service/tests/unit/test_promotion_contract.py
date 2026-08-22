from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_service.config import Settings
from ai_service.contracts import ArtifactLineageV5, TrainingVariant
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation import promotion
from ai_service.evaluation.ablation import R3FeatureSelection

_SELECTION_SHA = "a" * 64
_DIAGNOSTIC_COMMIT = "b" * 40
_PRODUCTION_COMMIT = "c" * 40
_DEEP_CHECKPOINT_SHA = "d" * 64
_HYBRID_CHECKPOINT_SHA = "e" * 64
_VICTORY_MATRIX_SHA = "f" * 64


def _lineage() -> ArtifactLineageV5:
    return ArtifactLineageV5(
        snapshot="1" * 64,
        embedding="2" * 64,
        rules="3" * 64,
        benchmark_spec="4" * 64,
        semantic_cohort="5" * 64,
        order_metadata="6" * 64,
    )


def _settings(*, variant: TrainingVariant, stage: str) -> Settings:
    return Settings(
        {
            "data": {"rule_feature_schema_version": "3.0.0"},
            "model": {
                "use_user_id_embedding": False,
                "use_price_features": False,
            },
            "train": {
                "objective": "sampled_softmax",
                "training_variant": variant.value,
                "campaign_stage": stage,
                "r3_feature_selection_mode": "selection_artifact",
                "r3_selection_artifact_sha256": _SELECTION_SHA,
                "r3_selected_deep_run_id": "deep-selected",
                "view_auxiliary_weight": 0.1,
                "rule_auxiliary_weight": 0.1,
                "rule_hard_negative_count": 4,
            },
        }
    )


def _production_config(*, variant: TrainingVariant) -> str:
    return f'''[data]
rule_feature_schema_version = "3.0.0"

[model]
use_user_id_embedding = false
use_price_features = false

[train]
objective = "sampled_softmax"
training_variant = "{variant.value}"
campaign_stage = "production"
r3_feature_selection_mode = "selection_artifact"
r3_selection_artifact_sha256 = "{_SELECTION_SHA}"
r3_selected_deep_run_id = "deep-selected"
view_auxiliary_weight = 0.1
rule_auxiliary_weight = 0.1
rule_hard_negative_count = 4
'''


def _promotion_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    artifact_root = tmp_path / "artifacts"
    selection_report = artifact_root / "diagnostics" / "r3" / "selection" / "report.json"
    selection_report.parent.mkdir(parents=True)
    selection_report.write_text('{"selection": "verified"}', encoding="utf-8")
    repository_root = tmp_path / "repository"
    config_root = repository_root / "configs" / "production"
    config_root.mkdir(parents=True)
    deep_config = config_root / "deep.toml"
    hybrid_config = config_root / "hybrid.toml"
    deep_config.write_text(_production_config(variant=TrainingVariant.DEEP_ONLY), encoding="utf-8")
    hybrid_config.write_text(_production_config(variant=TrainingVariant.HYBRID), encoding="utf-8")
    return artifact_root, selection_report, repository_root, deep_config, hybrid_config


def _patch_verified_evidence(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selection_report: Path,
    artifact_root: Path,
    passed: bool,
) -> None:
    lineage = _lineage()
    hybrid_settings = _settings(variant=TrainingVariant.HYBRID, stage="diagnostic")
    deep_settings = _settings(variant=TrainingVariant.DEEP_ONLY, stage="diagnostic")
    comparison_signature = hybrid_settings.comparison_signature_sha256()
    selection = SimpleNamespace(
        diagnostic_pause=False,
        selected_run_id="deep-selected",
        selected_feature_selection=R3FeatureSelection(
            use_user_id_embedding=False,
            use_price_features=False,
        ),
        comparison_signature_sha256=comparison_signature,
        lineage=lineage,
        diagnostic_git_commit=_DIAGNOSTIC_COMMIT,
        artifact_sha256=_SELECTION_SHA,
    )
    monkeypatch.setattr(
        promotion,
        "load_deep_ablation_artifact",
        lambda directory: SimpleNamespace(
            report=selection,
            report_path=directory / "report.json",
        ),
    )

    victory_path = artifact_root / "runs" / "hybrid-h3b" / "evaluation" / "val"
    victory_path.mkdir(parents=True)
    matrix_path = victory_path / "victory-matrix.json"
    matrix_path.write_text("{}", encoding="utf-8")
    deep = SimpleNamespace(
        run_id="deep-selected",
        run_dir=artifact_root / "runs" / "deep-selected",
        settings=deep_settings,
        state=SimpleNamespace(),
        checkpoint_manifest=SimpleNamespace(content_sha256=_DEEP_CHECKPOINT_SHA),
        lineage=lineage,
        git_commit=_DIAGNOSTIC_COMMIT,
    )
    hybrid = SimpleNamespace(
        run_id="hybrid-h3b",
        run_dir=artifact_root / "runs" / "hybrid-h3b",
        settings=hybrid_settings,
        state=SimpleNamespace(
            validation_gate_passed=passed,
            paired_run_id="deep-selected",
            validation_victory_matrix_path=str(matrix_path),
        ),
        checkpoint_manifest=SimpleNamespace(content_sha256=_HYBRID_CHECKPOINT_SHA),
        lineage=lineage,
        git_commit=_DIAGNOSTIC_COMMIT,
    )

    def load_run(
        root: Path,
        run_id: str,
        *,
        expected_variant: TrainingVariant,
    ) -> SimpleNamespace:
        assert root == artifact_root
        if expected_variant is TrainingVariant.DEEP_ONLY:
            assert run_id == "deep-selected"
            return deep
        assert expected_variant is TrainingVariant.HYBRID
        assert run_id == "hybrid-h3b"
        return hybrid

    monkeypatch.setattr(promotion, "_load_run_evidence", load_run)
    monkeypatch.setattr(
        promotion,
        "load_evaluation_artifacts",
        lambda run_dir, **kwargs: (
            run_dir == hybrid.run_dir
            and kwargs["expected_split"].value == "val"
            and kwargs["expected_hybrid_run_id"] == hybrid.run_id
            and kwargs["expected_deep_run_id"] == deep.run_id
            and SimpleNamespace(
                manifest=SimpleNamespace(
                    passed=passed,
                    hybrid_checkpoint_sha256=_HYBRID_CHECKPOINT_SHA,
                    deep_checkpoint_sha256=_DEEP_CHECKPOINT_SHA,
                ),
                victory_matrix=SimpleNamespace(all_passed=passed),
                victory_matrix_path=matrix_path,
                victory_matrix_sha256=_VICTORY_MATRIX_SHA,
            )
        ),
    )
    monkeypatch.setattr(
        promotion,
        "_validate_production_git",
        lambda **kwargs: (
            kwargs["repository_root"]
            and kwargs["diagnostic_commit"] == _DIAGNOSTIC_COMMIT
            and _PRODUCTION_COMMIT
        ),
    )


def test_promotion_api_derives_all_promotion_critical_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert tuple(inspect.signature(promotion.publish_r4_promotion).parameters) == (
        "destination",
        "selection_report",
        "hybrid_run_id",
        "deep_config",
        "hybrid_config",
        "artifact_root",
        "repository_root",
    )

    (
        artifact_root,
        selection_report,
        repository_root,
        deep_config,
        hybrid_config,
    ) = _promotion_inputs(tmp_path)
    _patch_verified_evidence(
        monkeypatch,
        selection_report=selection_report,
        artifact_root=artifact_root,
        passed=True,
    )
    destination = tmp_path / "promotion.json"

    report = promotion.publish_r4_promotion(
        destination,
        selection_report=selection_report,
        hybrid_run_id="hybrid-h3b",
        deep_config=deep_config,
        hybrid_config=hybrid_config,
        repository_root=repository_root,
    )

    assert promotion.load_r4_promotion(destination) == report
    assert report.selected_deep_run_id == "deep-selected"
    assert report.selected_deep_checkpoint_sha256 == _DEEP_CHECKPOINT_SHA
    assert report.h3b_hybrid_checkpoint_sha256 == _HYBRID_CHECKPOINT_SHA
    assert report.h3b_victory_matrix_sha256 == _VICTORY_MATRIX_SHA
    assert report.lineage == _lineage()
    assert report.diagnostic_git_commit == _DIAGNOSTIC_COMMIT
    assert report.production_git_commit == _PRODUCTION_COMMIT
    assert (
        report.deep_selection_report_sha256
        == hashlib.sha256(selection_report.read_bytes()).hexdigest()
    )
    assert report.deep_config_sha256 == hashlib.sha256(deep_config.read_bytes()).hexdigest()
    assert report.hybrid_config_sha256 == hashlib.sha256(hybrid_config.read_bytes()).hexdigest()
    assert report.feature_selection == {
        "use_user_id_embedding": False,
        "use_price_features": False,
    }
    assert report.objective_settings["rule_auxiliary_weight"] == 0.1
    assert report.objective_settings["rule_hard_negative_count"] == 4


def test_promotion_rejects_a_failed_h3b_validation_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        artifact_root,
        selection_report,
        repository_root,
        deep_config,
        hybrid_config,
    ) = _promotion_inputs(tmp_path)
    _patch_verified_evidence(
        monkeypatch,
        selection_report=selection_report,
        artifact_root=artifact_root,
        passed=False,
    )

    with pytest.raises(ArtifactIntegrityError, match="hybrid-owned VAL victory"):
        promotion.publish_r4_promotion(
            tmp_path / "promotion.json",
            selection_report=selection_report,
            hybrid_run_id="hybrid-h3b",
            deep_config=deep_config,
            hybrid_config=hybrid_config,
            repository_root=repository_root,
        )


def test_promotion_rejects_git_diff_outside_the_production_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root = tmp_path / "repository"
    config_root = repository_root / "configs" / "production"
    config_root.mkdir(parents=True)
    deep_config = config_root / "deep.toml"
    hybrid_config = config_root / "hybrid.toml"
    deep_config.write_text("deep", encoding="utf-8")
    hybrid_config.write_text("hybrid", encoding="utf-8")
    monkeypatch.setattr(
        promotion,
        "_require_frozen_production_commit",
        lambda _root: _PRODUCTION_COMMIT,
    )

    def git_output(_root: Path, arguments: tuple[str, ...]) -> str:
        if arguments[0] == "merge-base":
            return ""
        assert arguments[:2] == ("diff", "--name-only")
        return "configs/production/deep.toml\nconfigs/production/hybrid.toml\nunrelated.py"

    monkeypatch.setattr(promotion, "_git_output", git_output)

    with pytest.raises(ArtifactIntegrityError, match="exactly the two production config paths"):
        promotion._validate_production_git(
            repository_root=repository_root,
            diagnostic_commit=_DIAGNOSTIC_COMMIT,
            config_paths=(deep_config, hybrid_config),
        )
