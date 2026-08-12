from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ai_service.cli import build_parser
from ai_service.config import Settings
from ai_service.contracts import (
    ArtifactLineage,
    ArtifactLineageV5,
    DataProbeReport,
    PipelineState,
    RuleManifest,
    SplitName,
    TrainingVariant,
)
from ai_service.data.features import EmbeddingArtifact
from ai_service.data.semantic_cohort import load_semantic_cohort
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.evaluation import r3_diagnostics
from ai_service.evaluation.ablation import R3FeatureSelection
from ai_service.evaluation.promotion import (
    load_r4_promotion,
    publish_r4_promotion,
)
from ai_service.training import pipeline, preflight
from tests.unit.test_pipeline_error_edges import make_settings, make_snapshot


def _lineage() -> ArtifactLineageV5:
    return ArtifactLineageV5(
        snapshot="a" * 64,
        embedding="b" * 64,
        rules="c" * 64,
        benchmark_spec="d" * 64,
        semantic_cohort="e" * 64,
        order_metadata="f" * 64,
    )


def test_probe_report_keeps_typed_readiness_and_legacy_evidence() -> None:
    report = DataProbeReport.model_validate(
        {"passed": True, "label_permutation_sanity": {"gauc": 0.5}, "persona": {"gauc": 0.7}}
    )
    assert report.passed is True
    assert report["persona"] == {"gauc": 0.7}


def test_semantic_cohort_requires_all_traps_and_rejects_duplicates(tmp_path: Path) -> None:
    rows = [
        {
            "cohort_id": f"semantic-{trap}",
            "event_id": f"semantic-{trap}:val:0",
            "user_id": trap,
            "anchor_product_id": 100 + trap,
            "target_product_ids": [200 + trap],
        }
        for trap in range(1, 11)
    ]
    (tmp_path / "semantic-cohort.json").write_text(json.dumps(rows), encoding="utf-8")
    cases = load_semantic_cohort(tmp_path)
    assert len(cases) == 10
    rows.append(rows[0])
    (tmp_path / "semantic-cohort.json").write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="duplicate"):
        load_semantic_cohort(tmp_path)


def test_r4_promotion_is_immutable_and_hash_verified(tmp_path: Path) -> None:
    selection = tmp_path / "report.json"
    deep_config = tmp_path / "deep.toml"
    hybrid_config = tmp_path / "hybrid.toml"
    for path, value in ((selection, "selection"), (deep_config, "deep"), (hybrid_config, "hybrid")):
        path.write_text(value, encoding="utf-8")
    output = tmp_path / "promotion.json"
    report = publish_r4_promotion(
        output,
        deep_selection_report=selection,
        selected_deep_run_id="deep",
        selected_deep_checkpoint_sha256="1" * 64,
        h3b_hybrid_run_id="hybrid",
        h3b_hybrid_checkpoint_sha256="2" * 64,
        h3b_victory_matrix_sha256="3" * 64,
        lineage=_lineage(),
        diagnostic_git_commit="4" * 40,
        production_git_commit="5" * 40,
        deep_config=deep_config,
        hybrid_config=hybrid_config,
        feature_selection={"include_user_id": False, "include_price": False},
        objective_settings={"rule_auxiliary_weight": 0.1},
    )
    assert load_r4_promotion(output) == report
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        output.write_text(
            output.read_text(encoding="utf-8").replace(
                '"selected_deep_run_id": "deep"', '"selected_deep_run_id": "other"'
            ),
            encoding="utf-8",
        )
        load_r4_promotion(output)


def test_preflight_delegation_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(serving=SimpleNamespace(environment="development"))
    readiness = SimpleNamespace(passed=True)
    prepared = SimpleNamespace(
        snapshot=SimpleNamespace(manifest=SimpleNamespace(artifact_id="snapshot")),
        embedding=SimpleNamespace(vectors=[]),
        rules=SimpleNamespace(),
        lineage=_lineage(),
        rule_readiness=readiness,
    )
    audit = SimpleNamespace(training_suitability_passed=True, model_dump=lambda mode=None: {})
    probes = DataProbeReport(passed=True)
    monkeypatch.setattr(preflight, "prepare_training_inputs", lambda _settings: prepared)
    monkeypatch.setattr(preflight.DataQualityAuditor, "audit", lambda _self, _snapshot: audit)
    monkeypatch.setattr(preflight, "run_data_probes", lambda *_args: probes)
    monkeypatch.setattr(
        preflight,
        "R3PreflightReceipt",
        lambda **kwargs: SimpleNamespace(passed=True, **kwargs),
    )
    receipt = preflight.run_r3_preflight(settings, device=torch.device("cpu"))
    assert receipt.passed is True

    probes.passed = False
    with pytest.raises(ArtifactIntegrityError, match="probe"):
        preflight.run_r3_preflight(settings, device=torch.device("cpu"))


def test_preflight_artifact_selectors_and_preparation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    feature_root = tmp_path / "features"
    feature_root.mkdir()
    (feature_root / "one").mkdir()
    (feature_root / "one" / "manifest.json").write_text(
        json.dumps({"snapshot_sha256": "a" * 64}), encoding="utf-8"
    )
    assert preflight._find_feature(feature_root, "a" * 64).name == "one"
    with pytest.raises(ArtifactIntegrityError, match="one feature"):
        preflight._find_feature(tmp_path / "missing", "a" * 64)

    settings = SimpleNamespace(
        data=SimpleNamespace(
            artifact_root=tmp_path,
            snapshot_id="snapshot",
            rule_feature_schema_version="3.0.0",
            min_rule_count=3,
            min_rule_lift=1.0,
            minimum_training_rows_with_any_rule=0.0,
            minimum_training_target_rule_rate=0.0,
        ),
        train=SimpleNamespace(
            max_history_items=1,
            explicit_negative_ratio=4,
            seed=42,
            batch_size=1,
            rule_hard_negative_count=0,
        ),
    )
    rule_root = tmp_path / "rules" / "rule"
    rule_root.mkdir(parents=True)
    manifest = RuleManifest(
        artifact_id="rule",
        content_sha256="c" * 64,
        parent_sha256={},
        snapshot_sha256="a" * 64,
        num_directed_rules=1,
        train_basket_count=1,
        min_count=3,
        min_lift=1.0,
        q99_log_lift=1.0,
        feature_schema_version="3.0.0",
        has_full_statistics=True,
    )
    (rule_root / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    assert preflight._find_rule(settings, "a" * 64).name == "rule"

    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(artifact_id="snap", content_sha256="a" * 64, num_items=1)
    )
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "feature",
        vectors=[],
    )
    rules = SimpleNamespace(
        manifest=SimpleNamespace(),
        store=object(),
        require_training_capability=lambda _s: None,
    )
    monkeypatch.setattr(preflight, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(preflight, "load_embedding_artifact", lambda _path: embedding)
    monkeypatch.setattr(preflight, "load_rule_artifact", lambda *_args: rules)
    monkeypatch.setattr(preflight, "resolve_artifact_lineage", lambda *_args, **_kwargs: _lineage())
    loaded = preflight._load_base_inputs(settings)
    assert loaded[0] is snapshot and loaded[2] is rules

    prepared = SimpleNamespace(
        snapshot=snapshot,
        embedding=SimpleNamespace(vectors=[]),
        rules=rules,
        lineage=_lineage(),
        purchase_index=object(),
        sampler=object(),
        train_loader=object(),
        rule_readiness=SimpleNamespace(passed=True),
    )
    monkeypatch.setattr(preflight, "_load_base_inputs", lambda _s: loaded)
    monkeypatch.setattr(preflight, "build_purchase_training_index", lambda *_a, **_k: object())
    monkeypatch.setattr(preflight, "MixedNegativeSampler", lambda *_a, **_k: object())
    monkeypatch.setattr(preflight, "PurchaseBatchIterator", lambda *_a, **_k: object())
    monkeypatch.setattr(
        preflight, "assess_training_rule_readiness", lambda *_a, **_k: prepared.rule_readiness
    )
    result = preflight.prepare_training_inputs(settings)
    assert result.lineage == _lineage()


def test_promote_r4_command_has_explicit_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    files = {}
    for name, value in (
        ("selection", "{}"),
        ("lineage", _lineage().model_dump_json()),
        ("features", "{}"),
        ("objective", "{}"),
        ("deep", "deep"),
        ("hybrid", "hybrid"),
    ):
        path = (
            tmp_path / f"{name}.json"
            if name not in {"deep", "hybrid"}
            else tmp_path / f"{name}.toml"
        )
        path.write_text(value, encoding="utf-8")
        files[name] = path
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline,
        "publish_r4_promotion",
        lambda destination, **kwargs: (
            observed.update(kwargs)
            or SimpleNamespace(model_dump=lambda mode=None: {"passed": True})
        ),
    )
    args = build_parser().parse_args(
        [
            "promote-r4",
            "--selection-report",
            str(files["selection"]),
            "--selected-deep-run-id",
            "deep",
            "--selected-deep-checkpoint-sha256",
            "1" * 64,
            "--h3b-hybrid-run-id",
            "hybrid",
            "--h3b-hybrid-checkpoint-sha256",
            "2" * 64,
            "--h3b-victory-matrix-sha256",
            "3" * 64,
            "--lineage-json",
            str(files["lineage"]),
            "--deep-config",
            str(files["deep"]),
            "--hybrid-config",
            str(files["hybrid"]),
            "--diagnostic-git-commit",
            "4" * 40,
            "--production-git-commit",
            "5" * 40,
            "--feature-selection-json",
            str(files["features"]),
            "--objective-settings-json",
            str(files["objective"]),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    pipeline.execute_command(args)
    assert observed["selected_deep_run_id"] == "deep"


def test_r3_metric_archive_validator_accepts_exact_schema_and_rejects_corruption(
    tmp_path: Path,
) -> None:
    users = np.asarray([1, 2], dtype=np.int64)
    metrics: dict[str, object] = {
        "user_ids": users,
        "aligned_mask": np.asarray([True, False], dtype=np.bool_),
    }
    for key in (
        "deep_hr",
        "deep_ndcg",
        "deep_gauc",
        "hybrid_hr",
        "hybrid_ndcg",
        "hybrid_gauc",
    ):
        metrics[key] = np.asarray([0.1, 0.2], dtype=np.float64)
    for key in ("alpha_hr", "alpha_ndcg", "alpha_gauc"):
        metrics[key] = np.full((7, 2), 0.1, dtype=np.float64)
    path = tmp_path / "metrics.npz"
    np.savez(path, **metrics)
    loaded = r3_diagnostics._validate_metrics(path)
    assert loaded["alpha_gauc"].shape == (7, 2)
    path.write_bytes(b"not an npz")
    with pytest.raises(ArtifactIntegrityError, match="NPZ"):
        r3_diagnostics._validate_metrics(path)
    bad = dict(metrics)
    bad["aligned_mask"] = np.asarray([1, 0], dtype=np.int64)
    np.savez(path, **bad)
    with pytest.raises(ArtifactIntegrityError, match="aligned_mask"):
        r3_diagnostics._validate_metrics(path)
    bad = dict(metrics)
    bad["alpha_gauc"] = np.zeros((1, 2), dtype=np.float64)
    np.savez(path, **bad)
    with pytest.raises(ArtifactIntegrityError, match="alpha metric"):
        r3_diagnostics._validate_metrics(path)


def test_r3_diagnostic_helpers_cover_cohorts_and_fixture_requests(tmp_path: Path) -> None:
    user_ids = np.asarray([1, 2], dtype=np.int64)
    deep = np.asarray([[0.2, 0.3], [0.1, 0.2], [0.05, 0.1]])
    hybrid = deep + 0.1
    aligned = r3_diagnostics._cohort_delta("aligned", user_ids, {1}, deep, hybrid)
    unaligned = r3_diagnostics._cohort_delta("unaligned", user_ids, {1}, deep, hybrid)
    empty = r3_diagnostics._cohort_delta("aligned", user_ids, set(), deep, hybrid)
    assert aligned.user_count == unaligned.user_count == 1
    assert empty.user_count == 0

    values = {
        key: np.zeros((7, 2), dtype=np.float64)
        if key.startswith("alpha")
        else np.zeros(2, dtype=np.float64)
        for key in r3_diagnostics._METRIC_KEYS
    }
    values["user_ids"] = user_ids
    values["aligned_mask"] = np.asarray([True, False], dtype=np.bool_)
    path = tmp_path / "written.npz"
    r3_diagnostics._write_metrics(path, values)
    assert path.is_file()

    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            [
                {
                    "trap_id": 1,
                    "anchor_product_id": 10,
                    "target_product_ids": [20],
                }
            ]
        ),
        encoding="utf-8",
    )
    snapshot = SimpleNamespace(
        product_map={10: 0, 20: 1},
        snapshot_dir=tmp_path / "missing",
    )
    prepared = SimpleNamespace(
        eligible_users=np.asarray([1], dtype=np.int64),
        seen_items={1: set()},
    )
    requests = r3_diagnostics._target_requests(snapshot, prepared, fixture)
    assert requests[0].target_item_ids == (1,)


def test_production_train_checks_promotion_before_building_loader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path)
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.train.campaign_stage = "production"
    settings.train.r3_selection_artifact_sha256 = "d" * 64
    settings.train.r4_promotion_report_path = str(tmp_path / "promotion.json")
    snapshot = make_snapshot(tmp_path)
    snapshot.manifest.benchmark_spec_sha256 = "d" * 64
    snapshot.manifest.semantic_cohort_sha256 = "e" * 64
    snapshot.manifest.order_metadata_sha256 = "f" * 64
    embedding = SimpleNamespace(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features" / "embedding",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = SimpleNamespace(
        manifest=SimpleNamespace(
            feature_schema_version="3.0.0",
            snapshot_sha256=snapshot.manifest.content_sha256,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
            content_sha256="c" * 64,
        ),
        require_training_capability=lambda _settings: object(),
    )
    promotion = SimpleNamespace(production_git_commit="4" * 40, lineage=_lineage())
    monkeypatch.setattr(
        pipeline, "require_frozen_source_revision", lambda: SimpleNamespace(commit_sha="4" * 40)
    )
    monkeypatch.setattr(pipeline, "load_r4_promotion", lambda _path: promotion)
    monkeypatch.setattr(pipeline, "require_selected_r3_pair", lambda **_kwargs: None)
    failure = RuntimeError("loader")
    monkeypatch.setattr(
        pipeline,
        "build_purchase_training_index",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
    )
    with pytest.raises(RuntimeError, match="loader"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="production-check",
            device=torch.device("cpu"),
            require_frozen_source=True,
        )


def test_legacy_preflight_path_is_fail_closed_and_serializes_probe_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    snapshot = SimpleNamespace(
        manifest=SimpleNamespace(artifact_id="snap", content_sha256="a" * 64, num_items=2)
    )
    embedding = SimpleNamespace(
        artifact_dir=tmp_path / "feature",
        vectors=np.zeros((2, settings.model.sbert_dim), dtype=np.float32),
        manifest=SimpleNamespace(content_sha256="b" * 64),
    )
    rules = SimpleNamespace(
        artifact_dir=tmp_path / "rule",
        store=object(),
        manifest=SimpleNamespace(content_sha256="c" * 64),
    )
    readiness = SimpleNamespace(passed=True, model_dump=lambda mode=None: {"passed": True})
    audit = SimpleNamespace(
        training_suitability_passed=True,
        gate_failures=(),
        model_dump=lambda mode=None: {"training_suitability_passed": True},
    )
    monkeypatch.setattr(pipeline, "load_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        pipeline, "_find_single_parent_artifact", lambda *_args, **_kwargs: tmp_path
    )
    monkeypatch.setattr(pipeline, "load_embedding_artifact", lambda _path: embedding)
    monkeypatch.setattr(pipeline, "_find_training_rule_artifact", lambda *_args: tmp_path)
    monkeypatch.setattr(pipeline, "load_rule_artifact", lambda *_args: rules)
    monkeypatch.setattr(pipeline, "_require_rule_training_capability", lambda _r, _s: rules.store)
    monkeypatch.setattr(
        pipeline,
        "resolve_artifact_lineage",
        lambda *_args, **_kwargs: ArtifactLineage(
            snapshot_sha256="a" * 64, embedding_sha256="b" * 64, rule_sha256="c" * 64
        ),
    )
    monkeypatch.setattr(
        pipeline, "build_purchase_training_index", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(pipeline, "MixedNegativeSampler", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(pipeline, "PurchaseBatchIterator", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        pipeline, "assess_training_rule_readiness", lambda *_args, **_kwargs: readiness
    )
    monkeypatch.setattr(pipeline.DataQualityAuditor, "audit", lambda *_args: audit)
    monkeypatch.setattr(pipeline, "run_data_probes", lambda *_args: DataProbeReport(passed=True))
    result = pipeline._preflight_r3(settings, device=torch.device("cpu"))
    assert result["snapshot_id"] == "snap"
    assert result["probes"]["passed"] is True


def test_production_settings_reject_malformed_or_duplicate_database_identities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cert = tmp_path / "ca.crt"
    cert.write_text("CA", encoding="utf-8")
    values = {
        "AI_ARTIFACT_ROOT": str(tmp_path.resolve()),
        "AI_STORE_ID": "1",
        "SUPABASE_DB_CA_PATH": str(cert.resolve()),
        "CHATBOT_DATABASE_URL": "postgresql://u:p@db.example/chat",
        "CATALOG_DATABASE_URL": "postgresql://u:p@db.example/catalog",
        "ORDER_DATABASE_URL": "postgresql://u:p@db.example/order",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    settings = Settings()
    settings.serving.environment = "production"
    settings.validate_production()
    monkeypatch.setenv("ORDER_DATABASE_URL", values["CHATBOT_DATABASE_URL"])
    with pytest.raises(ConfigurationError, match="three distinct"):
        settings.validate_production()


def test_r3_existing_pair_metric_loader_validates_hybrid_owned_archive(tmp_path: Path) -> None:
    hybrid_dir = tmp_path / "hybrid" / "evaluation" / "val"
    deep_dir = tmp_path / "deep" / "evaluation" / "val"
    hybrid_dir.mkdir(parents=True)
    deep_dir.mkdir(parents=True)
    users = np.asarray([1, 2], dtype=np.int64)

    def write(path: Path, prefix: str) -> None:
        np.savez(
            path / "per-user-metrics.npz",
            user_ids=users,
            **{
                f"{prefix}_{name}": np.asarray([0.1, 0.2], dtype=np.float64)
                for name in ("hr", "ndcg", "gauc")
            },
        )

    write(hybrid_dir, "hybrid")
    write(deep_dir, "deep")
    hybrid = SimpleNamespace(run_dir=tmp_path / "hybrid")
    deep = SimpleNamespace(run_dir=tmp_path / "deep")
    result = r3_diagnostics._load_existing_pair_metrics(hybrid, deep)
    assert set(result) == {
        "user_ids",
        "deep_hr",
        "deep_ndcg",
        "deep_gauc",
        "hybrid_hr",
        "hybrid_ndcg",
        "hybrid_gauc",
    }
    (deep_dir / "per-user-metrics.npz").unlink()
    with np.load(hybrid_dir / "per-user-metrics.npz") as archive:
        existing = {key: np.asarray(archive[key]) for key in archive.files}
    existing.update(
        {
            "deep_hr": np.asarray([0.2, 0.3], dtype=np.float64),
            "deep_ndcg": np.asarray([0.2, 0.3], dtype=np.float64),
            "deep_gauc": np.asarray([0.2, 0.3], dtype=np.float64),
        }
    )
    np.savez(hybrid_dir / "per-user-metrics.npz", **existing)
    fallback = r3_diagnostics._load_existing_pair_metrics(hybrid, deep)
    assert fallback["deep_gauc"].shape == (2,)
    with pytest.raises(ArtifactIntegrityError, match="missing source"):
        r3_diagnostics._load_existing_pair_metrics(
            SimpleNamespace(run_dir=tmp_path / "missing"), deep
        )


def test_semantic_loader_rejects_missing_empty_and_incomplete_documents(tmp_path: Path) -> None:
    with pytest.raises(ArtifactIntegrityError, match="missing"):
        load_semantic_cohort(tmp_path)
    path = tmp_path / "semantic-cohort.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="no cases"):
        load_semantic_cohort(tmp_path)
    path.write_text(
        json.dumps(
            [
                {
                    "cohort_id": "semantic-1",
                    "event_id": "x:val:0",
                    "user_id": 1,
                    "anchor_product_id": 1,
                    "target_product_ids": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactIntegrityError, match="malformed"):
        load_semantic_cohort(tmp_path)


def test_preflight_rule_selector_rejects_malformed_and_duplicate_candidates(
    tmp_path: Path,
) -> None:
    root = tmp_path / "rules"
    (root / "bad").mkdir(parents=True)
    (root / "bad" / "manifest.json").write_text("{}", encoding="utf-8")
    settings = SimpleNamespace(
        data=SimpleNamespace(
            artifact_root=tmp_path,
            rule_feature_schema_version="3.0.0",
            min_rule_count=3,
            min_rule_lift=1.0,
        )
    )
    with pytest.raises(ArtifactIntegrityError, match="one rule"):
        preflight._find_rule(settings, "a" * 64)


def test_r4_promotion_rejects_missing_inputs_and_non_object_documents(tmp_path: Path) -> None:
    with pytest.raises(ArtifactIntegrityError, match="cannot be read"):
        load_r4_promotion(tmp_path / "missing.json")
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="object"):
        load_r4_promotion(path)
    with pytest.raises(ArtifactIntegrityError, match="input is missing"):
        publish_r4_promotion(
            tmp_path / "out.json",
            deep_selection_report=tmp_path / "selection.json",
            selected_deep_run_id="deep",
            selected_deep_checkpoint_sha256="1" * 64,
            h3b_hybrid_run_id="hybrid",
            h3b_hybrid_checkpoint_sha256="2" * 64,
            h3b_victory_matrix_sha256="3" * 64,
            lineage=_lineage(),
            diagnostic_git_commit="4" * 40,
            production_git_commit="5" * 40,
            deep_config=tmp_path / "deep.toml",
            hybrid_config=tmp_path / "hybrid.toml",
            feature_selection={},
            objective_settings={},
        )


def test_pipeline_state_loader_rejects_v5_three_field_lineage(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.data.rule_feature_schema_version = "3.0.0"
    run_dir = tmp_path / "runs" / "run"
    run_dir.mkdir(parents=True)
    state = PipelineState(
        model_schema_version="5.0.0",
        run_id="run",
        training_variant=TrainingVariant.DEEP_ONLY,
        snapshot_id="snapshot",
        embedding_path="embedding",
        rule_path="rules",
        checkpoint_path=None,
        paired_run_id=None,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
        lineage={
            "snapshot_sha256": "a" * 64,
            "embedding_sha256": "b" * 64,
            "rule_sha256": "c" * 64,
        },
    )
    (run_dir / "pipeline-state.json").write_text(state.model_dump_json(), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="six-field"):
        pipeline._load_state(settings, "run")


def _valid_r3_arrays() -> dict[str, np.ndarray]:
    return {
        "user_ids": np.asarray([1, 2], dtype=np.int64),
        "aligned_mask": np.asarray([True, False], dtype=np.bool_),
        **{
            key: np.asarray([0.1, 0.2], dtype=np.float64)
            for key in (
                "deep_hr",
                "deep_ndcg",
                "deep_gauc",
                "hybrid_hr",
                "hybrid_ndcg",
                "hybrid_gauc",
            )
        },
        **{
            key: np.full((7, 2), 0.1, dtype=np.float64)
            for key in ("alpha_hr", "alpha_ndcg", "alpha_gauc")
        },
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("aligned_mask", np.asarray([1, 0], dtype=np.int64), "aligned_mask"),
        ("alpha_hr", np.zeros((2, 2), dtype=np.float64), "alpha metric"),
        ("deep_hr", np.asarray([0.1], dtype=np.float64), "deep_hr"),
        ("hybrid_ndcg", np.asarray([np.nan, 0.2], dtype=np.float64), "outside"),
    ],
)
def test_r3_metric_archive_rejects_invalid_shapes_dtype_and_values(
    tmp_path: Path, field: str, value: np.ndarray, message: str
) -> None:
    arrays = _valid_r3_arrays()
    arrays[field] = value
    path = tmp_path / "metrics.npz"
    np.savez(path, **arrays)
    with pytest.raises(ArtifactIntegrityError, match=message):
        r3_diagnostics._validate_metrics(path)


def test_semantic_loader_rejects_wrong_split_and_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "semantic-cohort.json"
    path.write_text(
        json.dumps(
            [
                {
                    "cohort_id": "semantic-1",
                    "event_id": "semantic-1:test:0",
                    "user_id": 1,
                    "anchor_product_id": 2,
                    "target_product_ids": [3],
                },
                {
                    "cohort_id": "semantic-2",
                    "event_id": "semantic-2:val:0",
                    "user_id": 1,
                    "anchor_product_id": 2,
                    "target_product_ids": [3],
                },
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactIntegrityError, match="all ten"):
        load_semantic_cohort(tmp_path)
    with pytest.raises(ArtifactIntegrityError, match="all ten"):
        load_semantic_cohort(tmp_path, split=SplitName.TEST)
    path.write_text(json.dumps(["not-a-row"]), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="row is invalid"):
        load_semantic_cohort(tmp_path)


def test_preflight_selectors_reject_zero_and_multiple_matches(tmp_path: Path) -> None:
    root = tmp_path / "features"
    root.mkdir()
    settings = SimpleNamespace(data=SimpleNamespace(artifact_root=tmp_path))
    with pytest.raises(ArtifactIntegrityError, match="one feature"):
        preflight._find_feature(root, "a" * 64)
    (root / "first").mkdir()
    (root / "first" / "manifest.json").write_text(
        json.dumps({"snapshot_sha256": "a" * 64}), encoding="utf-8"
    )
    (root / "second").mkdir()
    (root / "second" / "manifest.json").write_text(
        json.dumps({"snapshot_sha256": "a" * 64}), encoding="utf-8"
    )
    with pytest.raises(ArtifactIntegrityError, match="one feature"):
        preflight._find_feature(root, "a" * 64)
    assert settings.data.artifact_root == tmp_path


def test_r4_promotion_rejects_tampered_existing_receipt(tmp_path: Path) -> None:
    selection = tmp_path / "report.json"
    deep_config = tmp_path / "deep.toml"
    hybrid_config = tmp_path / "hybrid.toml"
    for path in (selection, deep_config, hybrid_config):
        path.write_text("content", encoding="utf-8")
    output = tmp_path / "promotion.json"
    publish_r4_promotion(
        output,
        deep_selection_report=selection,
        selected_deep_run_id="deep",
        selected_deep_checkpoint_sha256="1" * 64,
        h3b_hybrid_run_id="hybrid",
        h3b_hybrid_checkpoint_sha256="2" * 64,
        h3b_victory_matrix_sha256="3" * 64,
        lineage=_lineage(),
        diagnostic_git_commit="4" * 40,
        production_git_commit="5" * 40,
        deep_config=deep_config,
        hybrid_config=hybrid_config,
        feature_selection={"include_price": False},
        objective_settings={"rule_weight": 0.1},
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    document["selected_deep_run_id"] = "other"
    output.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        load_r4_promotion(output)


def test_r3_diagnostic_small_helpers_cover_empty_cohort_and_metric_publication(
    tmp_path: Path,
) -> None:
    user_ids = np.asarray([1, 2], dtype=np.int64)
    deep = np.asarray([[0.1, 0.2], [0.2, 0.3], [0.4, 0.5]], dtype=np.float64)
    hybrid = deep + 0.1
    aligned = r3_diagnostics._cohort_delta("aligned", user_ids, {1}, deep, hybrid)
    unaligned = r3_diagnostics._cohort_delta("unaligned", user_ids, {1}, deep, hybrid)
    empty = r3_diagnostics._cohort_delta("aligned", user_ids, set(), deep, hybrid)
    assert aligned.user_count == 1
    assert unaligned.user_count == 1
    assert empty.user_count == 0
    document = {"value": 1, "artifact_sha256": "stale"}
    assert r3_diagnostics._report_without_hash(document) == {"value": 1}
    path = tmp_path / "metrics.npz"
    r3_diagnostics._write_metrics(path, _valid_r3_arrays())
    assert path.is_file()


def test_r4_promotion_rejects_corrupt_existing_destination_and_write_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    selection = tmp_path / "report.json"
    deep_config = tmp_path / "deep.toml"
    hybrid_config = tmp_path / "hybrid.toml"
    for path in (selection, deep_config, hybrid_config):
        path.write_text("content", encoding="utf-8")
    output = tmp_path / "promotion.json"
    output.write_text("not-json", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="cannot be read"):
        publish_r4_promotion(
            output,
            deep_selection_report=selection,
            selected_deep_run_id="deep",
            selected_deep_checkpoint_sha256="1" * 64,
            h3b_hybrid_run_id="hybrid",
            h3b_hybrid_checkpoint_sha256="2" * 64,
            h3b_victory_matrix_sha256="3" * 64,
            lineage=_lineage(),
            diagnostic_git_commit="4" * 40,
            production_git_commit="5" * 40,
            deep_config=deep_config,
            hybrid_config=hybrid_config,
            feature_selection={},
            objective_settings={},
        )
    output.unlink()
    monkeypatch.setattr(
        "ai_service.evaluation.promotion.immutable_write_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(ArtifactIntegrityError, match="publication failed"):
        publish_r4_promotion(
            output,
            deep_selection_report=selection,
            selected_deep_run_id="deep",
            selected_deep_checkpoint_sha256="1" * 64,
            h3b_hybrid_run_id="hybrid",
            h3b_hybrid_checkpoint_sha256="2" * 64,
            h3b_victory_matrix_sha256="3" * 64,
            lineage=_lineage(),
            diagnostic_git_commit="4" * 40,
            production_git_commit="5" * 40,
            deep_config=deep_config,
            hybrid_config=hybrid_config,
            feature_selection={},
            objective_settings={},
        )


def test_pipeline_config_and_terminal_summary_handle_explicit_spec_and_corrupt_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.serving.environment = "development"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    spec = tmp_path / "benchmark-spec.json"
    spec.write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        command="snapshot",
        config=None,
        store_id=1,
        snapshot_id=None,
        benchmark_run_id=None,
        benchmark_spec=str(spec),
        seed=123,
        r3_selection_report=None,
        r4_promotion_report=None,
        source="synthetic",
        embedding_source="mock",
        bundle_id=None,
        run_id=None,
    )
    configured = pipeline._configure(args)
    assert configured.data.benchmark_spec_path == spec.resolve()
    with pytest.raises(ConfigurationError, match="benchmark spec does not exist"):
        pipeline._configure(
            SimpleNamespace(**{**vars(args), "benchmark_spec": str(tmp_path / "missing")})
        )

    run_dir = tmp_path / "run" / "training"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"epochs_completed": "bad", "kept": True}), encoding="utf-8"
    )
    pipeline._ensure_training_terminal_summary(
        run_dir.parent, action=pipeline.TerminalAction.FAILED, reason="boom"
    )
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["epochs_completed"] == 0
    assert summary["kept"] is True


def test_pipeline_config_materializes_exact_selection_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings()
    settings.data.rule_feature_schema_version = "3.0.0"
    settings.train.r3_feature_selection_mode = "selection_artifact"
    settings.train.campaign_stage = "diagnostic"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    artifact = SimpleNamespace(
        report=SimpleNamespace(
            diagnostic_pause=False,
            selected_run_id="deep-selected",
            selected_feature_selection=R3FeatureSelection(
                use_user_id_embedding=False, use_price_features=True
            ),
            artifact_sha256="a" * 64,
        )
    )
    monkeypatch.setattr(pipeline, "load_deep_ablation_artifact", lambda _path: artifact)
    args = SimpleNamespace(
        command="train",
        config=None,
        store_id=1,
        snapshot_id=None,
        benchmark_run_id=None,
        benchmark_spec=None,
        seed=42,
        r3_selection_report=str(report_path),
        r4_promotion_report=None,
        source="synthetic",
        embedding_source="mock",
        bundle_id=None,
        run_id=None,
    )
    resolved = pipeline._configure(args)
    assert resolved.model.use_user_id_embedding is False
    assert resolved.model.use_price_features is True
    assert resolved.train.r3_selected_deep_run_id == "deep-selected"
    assert resolved.train.r3_selection_artifact_sha256 == "a" * 64


def test_pipeline_config_rejects_selection_mode_and_paused_reports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")

    def args() -> SimpleNamespace:
        return SimpleNamespace(
            command="train",
            config=None,
            store_id=1,
            snapshot_id=None,
            benchmark_run_id=None,
            benchmark_spec=None,
            seed=42,
            r3_selection_report=str(report_path),
            r4_promotion_report=None,
            source="synthetic",
            embedding_source="mock",
            bundle_id=None,
            run_id=None,
        )

    fixed = Settings()
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: fixed)
    with pytest.raises(ConfigurationError, match="selection_artifact config mode"):
        pipeline._configure(args())

    diagnostic = Settings()
    diagnostic.data.rule_feature_schema_version = "3.0.0"
    diagnostic.train.r3_feature_selection_mode = "selection_artifact"
    diagnostic.train.campaign_stage = "diagnostic"
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: diagnostic)
    monkeypatch.setattr(
        pipeline,
        "load_deep_ablation_artifact",
        lambda _path: SimpleNamespace(
            report=SimpleNamespace(
                diagnostic_pause=True,
                selected_run_id=None,
                selected_feature_selection=None,
            )
        ),
    )
    with pytest.raises(ConfigurationError, match="diagnostic pause"):
        pipeline._configure(args())
    monkeypatch.setattr(
        pipeline,
        "load_deep_ablation_artifact",
        lambda _path: SimpleNamespace(
            report=SimpleNamespace(
                diagnostic_pause=False,
                selected_run_id="deep",
                selected_feature_selection=None,
            )
        ),
    )
    with pytest.raises(ConfigurationError, match="no feature selection"):
        pipeline._configure(args())
