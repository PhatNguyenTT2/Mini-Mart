from __future__ import annotations

from pathlib import Path

import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json
from ai_service_v2.models.proposed import (
    TwoTowerConfig,
    item_text_hash_features,
    train_two_tower,
)
from ai_service_v2.training import (
    create_run,
    load_checkpoint,
    save_checkpoint,
    update_run_status,
)

HASH = "0" * 64


def test_run_and_checkpoint_are_hash_bound(snapshot: Snapshot, tmp_path: Path) -> None:
    model, _ = train_two_tower(
        snapshot,
        item_text_hash_features(snapshot, dimensions=8),
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=42,
    )
    run = create_run(
        root=tmp_path / "run",
        run_id="fixture-run",
        model_id=model.describe().model_id,
        dataset_manifest_sha256=HASH,
        protocol_manifest_sha256=HASH,
        seed=42,
        environment_lock_sha256=HASH,
        checkpoint_rule="fixed_epoch_final",
        command_sha256=HASH,
    )
    checkpoint = save_checkpoint(
        model,
        root=run.root / "checkpoint",
        run_id=run.manifest.run_id,
        seed=42,
    )
    completed = update_run_status(
        run,
        status="PASS",
        checkpoint_sha256=checkpoint.checkpoint_sha256,
    )
    parsed = load_strict_json(completed.root / "run_manifest.json")
    assert parsed["status"] == "PASS"
    assert parsed["checkpoint_sha256"] == checkpoint.checkpoint_sha256
    assert (completed.root / "checkpoint" / "checkpoint.npz").is_file()


def test_run_and_checkpoint_refuse_existing_namespaces(snapshot: Snapshot, tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    with pytest.raises(IntegrityError, match="already exists"):
        create_run(
            root=root,
            run_id="run",
            model_id="model",
            dataset_manifest_sha256=HASH,
            protocol_manifest_sha256=HASH,
            seed=1,
            environment_lock_sha256=HASH,
            checkpoint_rule="none",
            command_sha256=HASH,
        )


def test_checkpoint_payload_mutation_is_rejected(snapshot: Snapshot, tmp_path: Path) -> None:
    model, _ = train_two_tower(
        snapshot,
        item_text_hash_features(snapshot, dimensions=8),
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=42,
    )
    checkpoint_root = tmp_path / "checkpoint"
    save_checkpoint(model, root=checkpoint_root, run_id="run", seed=42)
    payload_path = checkpoint_root / "checkpoint.npz"
    payload_path.write_bytes(payload_path.read_bytes() + b"mutation")

    with pytest.raises(IntegrityError, match="payload hash"):
        load_checkpoint(
            checkpoint_root,
            snapshot=snapshot,
            features=item_text_hash_features(snapshot, dimensions=8),
        )


def test_checkpoint_array_declaration_mutation_is_rejected(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    model, _ = train_two_tower(
        snapshot,
        item_text_hash_features(snapshot, dimensions=8),
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=42,
    )
    checkpoint_root = tmp_path / "checkpoint"
    save_checkpoint(model, root=checkpoint_root, run_id="run", seed=42)
    manifest_path = checkpoint_root / "manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["arrays"]["user_embedding"]["dtype"] = "float32"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")

    with pytest.raises(IntegrityError, match="array declaration"):
        load_checkpoint(
            checkpoint_root,
            snapshot=snapshot,
            features=item_text_hash_features(snapshot, dimensions=8),
        )


def test_checkpoint_loader_rejects_extra_files(snapshot: Snapshot, tmp_path: Path) -> None:
    model, _ = train_two_tower(
        snapshot,
        item_text_hash_features(snapshot, dimensions=8),
        config=TwoTowerConfig(embedding_dim=4, hidden_dim=5, epochs=1),
        seed=42,
    )
    checkpoint_root = tmp_path / "checkpoint"
    save_checkpoint(model, root=checkpoint_root, run_id="run", seed=42)
    (checkpoint_root / "unexpected.txt").write_text("x", encoding="utf-8")

    with pytest.raises(IntegrityError, match="unexpected"):
        load_checkpoint(
            checkpoint_root,
            snapshot=snapshot,
            features=item_text_hash_features(snapshot, dimensions=8),
        )
