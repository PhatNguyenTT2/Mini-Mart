from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    AggregateReleaseReport,
    PipelineState,
    RunStatus,
    SplitName,
    TrainingVariant,
)
from ai_service.data.features import EmbeddingArtifact
from ai_service.data.rules import RuleArtifact, RuleManifest
from ai_service.errors import ArtifactIntegrityError, ConfigurationError, DataIntegrityError
from ai_service.training import pipeline
from tests.support.v5_factories import make_metric_gate, make_settings, make_snapshot

LINEAGE = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}


def _state(
    *, run_id: str = "winner", checkpoint: str | None = None, test: bool = False
) -> PipelineState:
    return PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id=run_id,
        training_variant=TrainingVariant.HYBRID,
        snapshot_id="snapshot",
        embedding_path="embedding",
        rule_path="rules",
        checkpoint_path=checkpoint,
        paired_run_id="deep-winner" if test else None,
        validation_gate_passed=test,
        test_gate_passed=test,
        validation_victory_matrix_path="val" if test else None,
        test_victory_matrix_path="test" if test else None,
        bundle_path=None,
    )


def test_pipeline_config_and_rule_selector_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings()
    monkeypatch.setattr(pipeline, "load_settings", lambda _config: settings)
    configured = pipeline._configure(
        Namespace(
            command="snapshot",
            store_id=2,
            snapshot_id="snapshot-v5",
            benchmark_run_id="benchmark",
            seed=2027,
            source="postgres",
            embedding_source="real",
            bundle_id=None,
            run_id=None,
        )
    )
    assert configured.data.store_id == 2
    assert configured.data.snapshot_id == "snapshot-v5"
    assert configured.data.benchmark_run_id == "benchmark"
    settings.serving.environment = "production"
    with pytest.raises(ConfigurationError, match="production requires"):
        pipeline._configure(
            Namespace(
                command="snapshot",
                store_id=1,
                snapshot_id=None,
                benchmark_run_id=None,
                seed=42,
                source="synthetic",
                embedding_source="mock",
                bundle_id=None,
                run_id=None,
            )
        )

    root = tmp_path / "rules" / "broken"
    root.mkdir(parents=True)
    (root / "manifest.json").write_text("{", encoding="utf-8")
    settings.data.artifact_root = tmp_path
    with pytest.raises(ArtifactIntegrityError, match="found 0"):
        pipeline._find_training_rule_artifact(settings, "a" * 64)
    pipeline._emit({"fixture": True})
    with pytest.raises(ArtifactIntegrityError, match="does not exist"):
        pipeline._load_state(settings, "missing")


def test_pipeline_training_preflight_rejects_mismatched_rule_before_run(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path / "snapshot")
    embedding = EmbeddingArtifact(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = RuleArtifact(
        store=SimpleNamespace(),
        manifest=RuleManifest(
            artifact_id="rule",
            content_sha256="c" * 64,
            parent_sha256={"snapshot": snapshot.manifest.content_sha256},
            snapshot_sha256=snapshot.manifest.content_sha256,
            num_directed_rules=0,
            train_basket_count=1,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
            q99_log_lift=1.0,
            feature_schema_version="1.0.0",
            has_full_statistics=True,
        ),
        artifact_dir=tmp_path / "rules",
    )
    with pytest.raises(ArtifactIntegrityError, match="does not match resolved config"):
        pipeline._train(
            settings,
            snapshot,
            embedding,
            rules,
            run_id="mismatch",
            device=torch.device("cpu"),
            require_frozen_source=False,
        )
    assert not (tmp_path / "runs" / "mismatch").exists()


def test_pipeline_export_preflight_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings(tmp_path)
    dummy = SimpleNamespace(
        manifest=SimpleNamespace(content_sha256="a" * 64),
    )
    embedding = SimpleNamespace(manifest=SimpleNamespace(content_sha256="b" * 64))
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256="c" * 64))
    with pytest.raises(DataIntegrityError, match="test-evaluated"):
        pipeline._export(settings, dummy, embedding, rules, dummy, _state())

    run_dir = tmp_path / "runs" / "winner"
    checkpoint = run_dir / "checkpoints" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    state = _state(checkpoint=str(checkpoint), test=True)
    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda _path: SimpleNamespace(status=RunStatus.TRAINING, document={}),
    )
    with pytest.raises(DataIntegrityError, match="sealed"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)

    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda _path: SimpleNamespace(status=RunStatus.SEALED, document={}),
    )
    with pytest.raises(DataIntegrityError, match="no comparison"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)
    comparison = settings.comparison_signature_sha256()
    monkeypatch.setattr(
        pipeline.RunLifecycle,
        "load",
        lambda _path: SimpleNamespace(
            status=RunStatus.SEALED,
            document={"comparison_signature_sha256": comparison},
        ),
    )
    with pytest.raises(DataIntegrityError, match="aggregate"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)

    release_path = tmp_path / "releases" / comparison / "release-gate.json"
    release_path.parent.mkdir(parents=True)
    report = AggregateReleaseReport(
        schema_version=MODEL_SCHEMA_VERSION,
        split=SplitName.TEST,
        passed=True,
        comparison_signature_sha256=comparison,
        hybrid_run_ids=("winner", "h2", "h3"),
        deep_run_ids=("deep-winner", "d2", "d3"),
        selected_run_id="h2",
        selected_seed=42,
        selected_victory_matrix_sha256="e" * 64,
        gates=tuple(
            make_metric_gate(name) for name in ("aggregate_gauc", "aggregate_ndcg", "aggregate_hr")
        ),
        artifact_sha256="0" * 64,
    )
    document = report.model_dump(mode="json")
    without_sha = {key: value for key, value in document.items() if key != "artifact_sha256"}
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(without_sha, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    release_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(DataIntegrityError, match="not selected"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)

    document["artifact_sha256"] = "0" * 64
    release_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(DataIntegrityError, match="report hash"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)

    document["selected_run_id"] = "winner"
    without_sha = {key: value for key, value in document.items() if key != "artifact_sha256"}
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(without_sha, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    release_path.write_text(json.dumps(document), encoding="utf-8")
    matrix_file = run_dir / "evaluation" / "test" / "victory-matrix.json"
    matrix_file.parent.mkdir(parents=True)
    matrix_file.write_text("{}", encoding="utf-8")
    state = pipeline._update_pipeline_state(state, test_victory_matrix_path=str(matrix_file))
    no_pair_state = pipeline._update_pipeline_state(state, paired_run_id=None)
    with pytest.raises(DataIntegrityError, match="paired Deep"):
        pipeline._export(settings, dummy, embedding, rules, dummy, no_pair_state)
    monkeypatch.setattr(
        pipeline,
        "load_evaluation_artifacts",
        lambda *_args, **_kwargs: SimpleNamespace(
            victory_matrix=SimpleNamespace(all_passed=False, sha256="e" * 64)
        ),
    )
    with pytest.raises(DataIntegrityError, match="did not pass"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)
    monkeypatch.setattr(
        pipeline,
        "load_evaluation_artifacts",
        lambda *_args, **_kwargs: SimpleNamespace(
            victory_matrix=SimpleNamespace(all_passed=True, sha256="f" * 64)
        ),
    )
    with pytest.raises(DataIntegrityError, match="does not match release"):
        pipeline._export(settings, dummy, embedding, rules, dummy, state)


@pytest.mark.parametrize(
    "mutation", ["status", "lineage", "signature", "variant", "commit", "checkpoint"]
)
def test_pipeline_resume_preflight_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path / "snapshot")
    embedding = SimpleNamespace(
        manifest=SimpleNamespace(content_sha256="b" * 64),
        artifact_dir=tmp_path / "features",
        vectors=np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
    )
    rules = SimpleNamespace(
        manifest=SimpleNamespace(
            content_sha256="c" * 64,
            feature_schema_version="2.0.0",
            snapshot_sha256=snapshot.manifest.content_sha256,
            min_count=settings.data.min_rule_count,
            min_lift=settings.data.min_rule_lift,
        ),
        require_training_capability=object,
    )
    lifecycle = SimpleNamespace(
        status=RunStatus.INTERRUPTED if mutation != "status" else RunStatus.TRAINING,
        document={
            "lineage": dict(LINEAGE),
            "training_signature_sha256": settings.training_signature_sha256(),
            "training_variant": settings.train.training_variant.value,
            "git_commit": "0" * 40,
        },
    )
    monkeypatch.setattr(
        pipeline, "resolve_source_revision", lambda: SimpleNamespace(commit_sha="0" * 40)
    )
    if mutation == "lineage":
        lifecycle.document["lineage"] = {**LINEAGE, "rules": "f" * 64}
    elif mutation == "signature":
        lifecycle.document["training_signature_sha256"] = "f" * 64
    elif mutation == "variant":
        lifecycle.document["training_variant"] = TrainingVariant.DEEP_ONLY.value
    elif mutation == "commit":
        lifecycle.document["git_commit"] = "1" * 40
    monkeypatch.setattr(pipeline.RunLifecycle, "load", lambda _path: lifecycle)
    with pytest.raises(
        ArtifactIntegrityError,
        match=r"only an interrupted|differs|checkpoint manifest missing",
    ):
        pipeline._train(
            settings,
            snapshot,
            embedding,  # type: ignore[arg-type]
            rules,  # type: ignore[arg-type]
            run_id="resume",
            device=torch.device("cpu"),
            resume=True,
            require_frozen_source=False,
        )


def test_resume_history_preflight_requires_contiguous_checkpoint_epoch(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "resume"
    history_path = run_dir / "training" / "history.jsonl"
    history_path.parent.mkdir(parents=True)
    history_path.write_text('{"epoch":1}\n{"epoch":2}\n', encoding="utf-8")

    pipeline._require_resume_history(run_dir, checkpoint_epoch=2)
    with pytest.raises(ArtifactIntegrityError, match="epochs differ"):
        pipeline._require_resume_history(run_dir, checkpoint_epoch=3)

    history_path.write_text('{"epoch":1}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="invalid epoch record"):
        pipeline._require_resume_history(run_dir, checkpoint_epoch=2)


def test_pipeline_test_pair_validation_gate_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = Settings()
    base.data.artifact_root = tmp_path
    signature = "a" * 64

    def loaded() -> SimpleNamespace:
        lineage = {"snapshot": "b" * 64, "embedding": "c" * 64, "rules": "d" * 64}
        return SimpleNamespace(
            settings=SimpleNamespace(
                train=SimpleNamespace(seed=42),
                comparison_signature_sha256=lambda: signature,
            ),
            snapshot=SimpleNamespace(manifest=SimpleNamespace(content_sha256=lineage["snapshot"])),
            embedding=SimpleNamespace(
                manifest=SimpleNamespace(content_sha256=lineage["embedding"])
            ),
            rules=SimpleNamespace(manifest=SimpleNamespace(content_sha256=lineage["rules"])),
            state=SimpleNamespace(checkpoint_path="checkpoint"),
            lifecycle=SimpleNamespace(document={"git_commit": "0" * 40}),
        )

    hybrid = loaded()
    deep = loaded()
    monkeypatch.setattr(
        pipeline,
        "_load_run_context",
        lambda *_args, **kwargs: (
            hybrid if kwargs.get("expected_variant") is TrainingVariant.HYBRID else deep
        ),
    )
    deep.lifecycle.document["git_commit"] = "1" * 40
    with pytest.raises(ArtifactIntegrityError, match="source revisions"):
        pipeline._evaluate_pair(
            base,
            hybrid_run_id="hybrid",
            deep_run_id="deep",
            split=SplitName.VAL,
            device=torch.device("cpu"),
        )
    deep.lifecycle.document["git_commit"] = "0" * 40
    release_dir = tmp_path / "releases" / signature
    release_dir.mkdir(parents=True)
    report = AggregateReleaseReport(
        schema_version=MODEL_SCHEMA_VERSION,
        split=SplitName.VAL,
        passed=True,
        comparison_signature_sha256=signature,
        hybrid_run_ids=("hybrid", "h2", "h3"),
        deep_run_ids=("deep", "d2", "d3"),
        selected_run_id="hybrid",
        selected_seed=42,
        selected_victory_matrix_sha256="e" * 64,
        gates=tuple(
            make_metric_gate(name) for name in ("aggregate_gauc", "aggregate_ndcg", "aggregate_hr")
        ),
        artifact_sha256="0" * 64,
    )
    document = report.model_dump(mode="json")
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in document.items() if key != "artifact_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    gate_path = release_dir / "validation-gate.json"
    gate_path.write_text(json.dumps(document), encoding="utf-8")
    base_document = document
    for mutation, message in (
        ("hash", "hash mismatch"),
        ("split", "did not pass"),
        ("signature", "signature differs"),
        ("pair", "not part"),
    ):
        current = json.loads(json.dumps(base_document))
        if mutation == "hash":
            current["artifact_sha256"] = "0" * 64
        elif mutation == "split":
            current["passed"] = False
            current["gates"][0]["passed"] = False
            current["gates"][0]["failure_reason"] = "fixture"
        elif mutation == "signature":
            current["comparison_signature_sha256"] = "f" * 64
        else:
            current["deep_run_ids"] = ["other-deep", "d2", "d3"]
        if mutation != "hash":
            current["artifact_sha256"] = hashlib.sha256(
                json.dumps(
                    {key: value for key, value in current.items() if key != "artifact_sha256"},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        gate_path.write_text(json.dumps(current), encoding="utf-8")
        with pytest.raises(ArtifactIntegrityError, match=message):
            pipeline._evaluate_pair(
                base,
                hybrid_run_id="hybrid",
                deep_run_id="deep",
                split=SplitName.TEST,
                device=torch.device("cpu"),
            )
