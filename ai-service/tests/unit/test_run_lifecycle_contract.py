from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_service.config import Settings
from ai_service.contracts import RunStatus
from ai_service.errors import ArtifactIntegrityError
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
        git_commit="0123456789abcdef",
    )
    run.transition(RunStatus.TRAINING)
    run.transition(RunStatus.EVALUATED)
    run.transition(RunStatus.SEALED)

    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    resolved = json.loads((run_dir / "resolved-config.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "sealed"
    assert manifest["lineage"] == lineage
    assert manifest["training_signature_sha256"] == settings.training_signature_sha256()
    assert manifest["git_commit"] == "0123456789abcdef"
    assert "chatbot_database_url" not in resolved["data"]

    with pytest.raises(ArtifactIntegrityError, match="illegal run transition"):
        run.transition(RunStatus.TRAINING)


def test_training_run_can_be_marked_interrupted(tmp_path: Path) -> None:
    run = RunLifecycle.create(
        tmp_path / "run-2",
        settings=Settings(),
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="unknown",
    )
    run.transition(RunStatus.TRAINING)
    run.transition(RunStatus.INTERRUPTED, reason="operator request")

    manifest = json.loads((tmp_path / "run-2" / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert manifest["status_reason"] == "operator request"
