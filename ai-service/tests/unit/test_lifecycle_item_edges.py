from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from ai_service.contracts import RunStatus
from ai_service.errors import ArtifactIntegrityError
from ai_service.models.item_tower import ItemTower
from ai_service.training.run import RunLifecycle
from tests.support.v5_factories import make_settings


def _valid_lifecycle(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    settings = make_settings(tmp_path)
    run_dir = tmp_path / "runs" / "run-edge"
    lifecycle = RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="0" * 40,
    )
    return run_dir, lifecycle.document


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("status", "status is invalid"),
        ("schema", "schema version"),
        ("model", "model schema"),
        ("sha", "comparison or variant"),
        ("git_commit", "invalid Git commit SHA"),
        ("variant", "training variant"),
        ("run_id", "ID does not"),
        ("lineage", "lineage"),
        ("terminal", "terminal run status"),
    ],
)
def test_run_manifest_loader_rejects_every_identity_boundary(
    tmp_path: Path, mutation: str, message: str
) -> None:
    run_dir, document = _valid_lifecycle(tmp_path)
    if mutation == "status":
        document["status"] = "bogus"
    elif mutation == "schema":
        document["schema_version"] = "0.0.0"
    elif mutation == "model":
        document["model_schema_version"] = "4.0.0"
    elif mutation == "sha":
        document["comparison_signature_sha256"] = "not-hex"
    elif mutation == "git_commit":
        document["git_commit"] = "unknown"
    elif mutation == "variant":
        document["training_variant"] = "unknown"
    elif mutation == "run_id":
        document["run_id"] = "other"
    elif mutation == "lineage":
        document["lineage"] = {"snapshot": "a" * 64}
    else:
        document["status"] = "failed"
        document["status_reason"] = None
    (run_dir / "run-manifest.json").write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match=message):
        RunLifecycle.load(run_dir)


def test_run_create_rejects_duplicate_and_invalid_lineage(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    run_dir = tmp_path / "runs" / "duplicate"
    RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        git_commit="0" * 40,
    )
    with pytest.raises(ArtifactIntegrityError, match="immutable run already exists"):
        RunLifecycle.create(
            run_dir,
            settings=settings,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            git_commit="0" * 40,
        )
    with pytest.raises(ArtifactIntegrityError, match="invalid SHA"):
        RunLifecycle.create(
            tmp_path / "runs" / "bad-lineage",
            settings=settings,
            lineage={"snapshot": "bad", "embedding": "b" * 64, "rules": "c" * 64},
            git_commit="0" * 40,
        )


def test_training_terminal_transition_checks_summary_contract(tmp_path: Path) -> None:
    run_dir, _ = _valid_lifecycle(tmp_path)
    lifecycle = RunLifecycle.load(run_dir)
    with pytest.raises(ArtifactIntegrityError, match="requires FAILED"):
        lifecycle.transition_training_terminal(RunStatus.TRAINING, reason="stop")
    with pytest.raises(ArtifactIntegrityError, match="requires a training summary"):
        lifecycle.transition_training_terminal(RunStatus.FAILED, reason="stop")
    summary = run_dir / "training" / "summary.json"
    summary.parent.mkdir()
    summary.write_text("not-json", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="cannot be read"):
        lifecycle.transition_training_terminal(RunStatus.FAILED, reason="stop")
    summary.write_text(json.dumps({"terminal_reason": "different"}), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="reason does not match"):
        lifecycle.transition_training_terminal(RunStatus.FAILED, reason="stop")
    summary.write_text(
        json.dumps({"terminal_reason": "stop", "terminal_action": "interrupted"}),
        encoding="utf-8",
    )
    with pytest.raises(ArtifactIntegrityError, match="terminal action"):
        lifecycle.transition_training_terminal(RunStatus.FAILED, reason="stop")
    summary.write_text(
        json.dumps({"terminal_reason": "stop", "terminal_action": "failed"}),
        encoding="utf-8",
    )
    lifecycle.transition_training_terminal(RunStatus.FAILED, reason="stop")
    assert lifecycle.status is RunStatus.FAILED


def test_item_tower_validates_all_optional_feature_paths(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    tower = ItemTower(settings).eval()
    sbert = torch.zeros((2, settings.model.sbert_dim))
    category = torch.ones(2, dtype=torch.int64)
    price = torch.ones(2, dtype=torch.int64)
    item_idx = torch.tensor([0, 1], dtype=torch.int64)
    cold = torch.tensor([False, True])
    encoded = tower(sbert, category, price, item_idx=item_idx, is_cold=cold)
    assert encoded.shape == (2, settings.model.item_emb_dim)
    assert torch.isfinite(encoded).all()
    assert tower(sbert, category, price).shape == encoded.shape
    with pytest.raises(ValueError, match="sbert must end"):
        tower(torch.zeros((2, 3)), category, price)
    with pytest.raises(ValueError, match="indices must be int64"):
        tower(sbert, category.float(), price)
    with pytest.raises(ValueError, match="shapes differ"):
        tower(sbert, category[:1], price[:1])
    with pytest.raises(ValueError, match="item_idx"):
        tower(sbert, category, price, item_idx=torch.zeros(2, dtype=torch.int32))
    with pytest.raises(ValueError, match="is_cold"):
        tower(sbert, category, price, is_cold=torch.ones(2, dtype=torch.int64))
    with pytest.raises(ValueError, match="outside configured range"):
        tower(
            sbert, torch.full((2,), settings.data.num_leaf_categories + 1, dtype=torch.int64), price
        )


def test_item_tower_rejects_nonfinite_sbert_and_indices(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    tower = ItemTower(settings)
    sbert = torch.zeros((1, settings.model.sbert_dim))
    category = torch.ones(1, dtype=torch.int64)
    price = torch.ones(1, dtype=torch.int64)
    with pytest.raises(ValueError, match="finite"):
        tower(torch.full_like(sbert, float("nan")), category, price)
    with pytest.raises(ValueError, match="item index"):
        tower(sbert, category, price, item_idx=torch.tensor([settings.data.num_items]))


def test_price_ablation_does_not_instantiate_price_parameters(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.model.use_price_features = False
    tower = ItemTower(settings).eval()
    assert tower.price_embedding is None
    assert not any(name.startswith("price_embedding") for name, _ in tower.named_parameters())
    sbert = torch.zeros((2, settings.model.sbert_dim))
    category = torch.ones(2, dtype=torch.int64)
    first = tower(sbert, category, torch.ones(2, dtype=torch.int64))
    second = tower(sbert, category, torch.full((2,), 2, dtype=torch.int64))
    assert torch.equal(first, second)
