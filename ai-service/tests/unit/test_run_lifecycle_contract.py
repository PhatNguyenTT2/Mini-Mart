from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_service.config import Settings
from ai_service.contracts import RunStatus
from ai_service.errors import ArtifactIntegrityError
from ai_service.training import run as run_module
from ai_service.training.run import RunLifecycle


def test_run_lifecycle_persists_resolved_provenance_and_rejects_illegal_transition(
    tmp_path: Path,
) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path / "machine-only"
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    run_dir = tmp_path / "run-1"

    run = RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage=lineage,
        git_commit="0" * 40,
    )
    run.transition(RunStatus.TRAINING)
    run.transition(RunStatus.EVALUATED)
    run.transition(RunStatus.SEALED)

    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    resolved = json.loads((run_dir / "resolved-config.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "sealed"
    assert manifest["lineage"] == lineage
    assert manifest["training_signature_sha256"] == settings.training_signature_sha256()
    assert manifest["git_commit"] == "0" * 40
    assert "chatbot_database_url" not in resolved["data"]

    with pytest.raises(ArtifactIntegrityError, match="illegal run transition"):
        run.transition(RunStatus.TRAINING)


def test_training_run_can_be_marked_interrupted(tmp_path: Path) -> None:
    run = RunLifecycle.create(
        tmp_path / "run-2",
        settings=Settings(),
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="1" * 40,
    )
    run.transition(RunStatus.TRAINING)
    run.transition(RunStatus.INTERRUPTED, reason="operator request")

    manifest = json.loads((tmp_path / "run-2" / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert manifest["status_reason"] == "operator request"


def test_run_create_failure_does_not_publish_partial_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_atomic_write_json = run_module.atomic_write_json
    calls = 0

    def fail_manifest_once(path: Path, document: dict[str, object]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("manifest write failed")
        real_atomic_write_json(path, document)

    monkeypatch.setattr(run_module, "atomic_write_json", fail_manifest_once)
    runs_root = tmp_path / "runs"
    run_dir = runs_root / "partial"
    with pytest.raises(OSError, match="manifest write failed"):
        RunLifecycle.create(
            run_dir,
            settings=Settings(),
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            git_commit="0" * 40,
        )
    assert not run_dir.exists()
    assert list(runs_root.glob(".partial-*")) == []


def test_run_create_rejects_changed_resolved_config_before_publish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_atomic_write_json = run_module.atomic_write_json

    def corrupt_resolved_config(path: Path, document: dict[str, object]) -> None:
        if path.name == "resolved-config.json":
            real_atomic_write_json(path, {"corrupt": True})
            return
        real_atomic_write_json(path, document)

    monkeypatch.setattr(run_module, "atomic_write_json", corrupt_resolved_config)
    runs_root = tmp_path / "runs"
    run_dir = runs_root / "corrupt-config"
    with pytest.raises(ArtifactIntegrityError, match="changed during publication"):
        RunLifecycle.create(
            run_dir,
            settings=Settings(),
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            git_commit="0" * 40,
        )
    assert not run_dir.exists()
    assert list(runs_root.glob(".corrupt-config-*")) == []


def test_transition_persistence_failure_does_not_mutate_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = RunLifecycle.create(
        tmp_path / "run-transition",
        settings=Settings(),
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="0" * 40,
    )
    original_document = dict(run.document)
    monkeypatch.setattr(
        run_module,
        "atomic_write_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("transition write failed")),
    )
    with pytest.raises(OSError, match="transition write failed"):
        run.transition(RunStatus.TRAINING)
    assert run.status is RunStatus.STAGING
    assert run.document == original_document


@pytest.mark.parametrize("git_commit", ["unknown", "fixture", "", "A" * 40, "0" * 39])
def test_run_lifecycle_rejects_invalid_git_commit(tmp_path: Path, git_commit: str) -> None:
    with pytest.raises(ArtifactIntegrityError, match="invalid Git commit SHA"):
        RunLifecycle.create(
            tmp_path / f"invalid-{len(git_commit)}",
            settings=Settings(),
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            git_commit=git_commit,
        )
