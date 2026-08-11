from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import PipelineState, SplitName, TrainingVariant
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.release import (
    _load_finalist_run,
    _pair_finalists_by_seed,
    evaluate_three_seed,
)
from ai_service.evaluation.report import (
    canonical_victory_matrix_sha,
    publish_evaluation_artifacts,
)
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.run import RunLifecycle
from tests.support.v5_factories import make_settings, make_victory_matrix

LINEAGE = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}


def _metrics(score: float, baseline: float) -> dict[str, np.ndarray]:
    users = np.arange(1, 5, dtype=np.int64)
    candidate = np.full(4, score, dtype=np.float64)
    control = np.full(4, baseline, dtype=np.float64)
    return {
        "user_ids": users,
        "hybrid_hr": candidate,
        "hybrid_ndcg": candidate,
        "hybrid_gauc": candidate,
        "deep_hr": control,
        "deep_ndcg": control,
        "deep_gauc": control,
        "apriori_hr": control,
        "apriori_ndcg": control,
        "apriori_gauc": control,
        "sbert_hr": control,
        "sbert_ndcg": control,
        "sbert_gauc": control,
        "item_cf_hr": control,
        "item_cf_ndcg": control,
        "item_cf_gauc": control,
        "noisy_hybrid_hr": candidate,
        "noisy_hybrid_ndcg": candidate,
        "noisy_hybrid_gauc": candidate,
        "random_hr": np.full((10, 4), 0.5, dtype=np.float64),
        "random_ndcg": np.full((10, 4), 0.5, dtype=np.float64),
        "random_gauc": np.full((10, 4), 0.5, dtype=np.float64),
    }


def _create_run(
    tmp_path: Path,
    *,
    seed: int,
    variant: TrainingVariant,
    paired_run_id: str,
    best_gauc: float,
) -> Path:
    settings = make_settings(tmp_path, variant=variant, seed=seed)
    run_dir = (
        tmp_path
        / "runs"
        / (f"hybrid-s{seed}" if variant is TrainingVariant.HYBRID else f"deep-s{seed}")
    )
    lifecycle = RunLifecycle.create(
        run_dir,
        settings=settings,
        lineage=LINEAGE,
        git_commit="fixture",
    )
    lifecycle.transition(
        __import__("ai_service.contracts", fromlist=["RunStatus"]).RunStatus.TRAINING
    )
    lifecycle.transition(
        __import__("ai_service.contracts", fromlist=["RunStatus"]).RunStatus.EVALUATED
    )
    model = HybridTwoTowerModel(settings)
    optimizer = AdamW(model.parameters())
    scheduler = ReduceLROnPlateau(optimizer)
    scaler = SimpleNamespace(state_dict=lambda: {}, load_state_dict=lambda _state: None)
    checkpoint_path = run_dir / "checkpoints" / "best.pt"
    CheckpointManager.save(
        checkpoint_path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        scaler=scaler,
        epoch=1,
        metrics={
            "val_gauc": best_gauc,
            "val_ndcg_at_k": best_gauc,
            "val_hr_at_k": best_gauc,
            "train_loss": 0.2,
        },
        stopping_state={
            "highest_gauc": best_gauc,
            "selected_epoch": 1,
            "selected_gauc": best_gauc,
            "selected_ndcg": best_gauc,
            "selected_hr": best_gauc,
            "patience_used": 0,
        },
        checkpoint_kind="best",
        lineage=LINEAGE,
        training_signature_sha256=settings.training_signature_sha256(),
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        training_variant=variant,
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id=run_dir.name,
    )
    state = PipelineState(
        model_schema_version=MODEL_SCHEMA_VERSION,
        run_id=run_dir.name,
        training_variant=variant,
        snapshot_id="snapshot",
        embedding_path="embedding",
        rule_path="rules",
        checkpoint_path=str(checkpoint_path),
        paired_run_id=paired_run_id,
        validation_gate_passed=False,
        test_gate_passed=False,
        validation_victory_matrix_path=None,
        test_victory_matrix_path=None,
        bundle_path=None,
    )
    (run_dir / "pipeline-state.json").write_text(
        json.dumps(state.model_dump(mode="json")), encoding="utf-8"
    )
    return run_dir


def _publish_pair_artifacts(
    tmp_path: Path,
    hybrid_dirs: tuple[Path, Path, Path],
    deep_dirs: tuple[Path, Path, Path],
) -> None:
    for hybrid_dir, deep_dir, seed in zip(hybrid_dirs, deep_dirs, (42, 2027, 31415), strict=True):
        settings = make_settings(tmp_path, variant=TrainingVariant.HYBRID, seed=seed)
        matrix = make_victory_matrix(
            split=SplitName.VAL,
            seed=seed,
            comparison_signature=settings.comparison_signature_sha256(),
        )
        deep_manifest = json.loads(
            (deep_dir / "checkpoints" / "best.pt.manifest.json").read_text(encoding="utf-8")
        )
        hybrid_manifest = json.loads(
            (hybrid_dir / "checkpoints" / "best.pt.manifest.json").read_text(encoding="utf-8")
        )
        for split in (SplitName.VAL, SplitName.TEST):
            split_matrix = matrix.model_copy(update={"split": split})
            # Recompute the canonical hash after changing the split.
            split_matrix = split_matrix.model_copy(
                update={"sha256": canonical_victory_matrix_sha(split_matrix)}
            )
            publish_evaluation_artifacts(
                run_dir=hybrid_dir,
                split=split,
                hybrid_run_id=hybrid_dir.name,
                deep_run_id=deep_dir.name,
                hybrid_checkpoint_sha256=hybrid_manifest["content_sha256"],
                deep_checkpoint_sha256=deep_manifest["content_sha256"],
                lineage=LINEAGE,
                comparison_signature_sha256=settings.comparison_signature_sha256(),
                metrics=_metrics(0.8, 0.5),
                results={"passed": True},
                victory_matrix=split_matrix,
            )


def _make_fixture(tmp_path: Path) -> tuple[tuple[Path, Path, Path], tuple[Path, Path, Path]]:
    seeds = (42, 2027, 31415)
    hybrids: list[Path] = []
    deeps: list[Path] = []
    for seed in seeds:
        hybrid_id = f"hybrid-s{seed}"
        deep_id = f"deep-s{seed}"
        hybrids.append(
            _create_run(
                tmp_path,
                seed=seed,
                variant=TrainingVariant.HYBRID,
                paired_run_id=deep_id,
                best_gauc={42: 0.75, 2027: 0.72, 31415: 0.70}[seed],
            )
        )
        deeps.append(
            _create_run(
                tmp_path,
                seed=seed,
                variant=TrainingVariant.DEEP_ONLY,
                paired_run_id=hybrid_id,
                best_gauc=0.55,
            )
        )
    result = (tuple(hybrids), tuple(deeps))
    _publish_pair_artifacts(tmp_path, *result)
    return result


def test_three_seed_release_gate_requires_six_runs(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        evaluate_three_seed(Settings(), (tmp_path / "h1", tmp_path / "h2", tmp_path / "h3"))  # type: ignore[call-arg]


def test_three_seed_release_gate_validation_and_test(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    val_res = evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    assert val_res.passed is True
    assert val_res.selected_run_id == "hybrid-s42"
    test_res = evaluate_three_seed(
        split=SplitName.TEST,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    assert test_res.passed is True
    assert test_res.selected_run_id == "hybrid-s42"


def test_pairing_seam_loads_verified_hybrid_owned_artifacts(tmp_path: Path) -> None:
    hybrids, deeps = _make_fixture(tmp_path)
    hybrid_records = tuple(_load_finalist_run(path, TrainingVariant.HYBRID) for path in hybrids)
    deep_records = tuple(_load_finalist_run(path, TrainingVariant.DEEP_ONLY) for path in deeps)
    pairs = _pair_finalists_by_seed(hybrid_records, deep_records, split=SplitName.VAL)
    assert [pair.hybrid.seed for pair in pairs] == [42, 2027, 31415]
    assert all(pair.evaluation.manifest.hybrid_run_id.startswith("hybrid-") for pair in pairs)


def test_release_rejects_ambient_comparison_signature_mismatch(tmp_path: Path) -> None:
    hybrids, deeps = _make_fixture(tmp_path)
    settings = make_settings(tmp_path)
    settings.eval.hr_guardrail_delta = -0.5
    with pytest.raises(ArtifactIntegrityError, match="ambient settings comparison signature"):
        evaluate_three_seed(
            split=SplitName.VAL,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )


def test_test_release_rejects_training_finalist_without_auto_heal(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    manifest_path = hybrids[1] / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "training"
    manifest["status_reason"] = None
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    with pytest.raises(DataIntegrityError, match="TEST aggregate requires"):
        evaluate_three_seed(
            split=SplitName.TEST,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )
    reloaded = RunLifecycle.load(hybrids[1])
    assert reloaded.status.value == "training"


def test_three_seed_release_gate_rejects_wrong_seed_set(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    with pytest.raises(DataIntegrityError, match="three distinct"):
        evaluate_three_seed(
            split=SplitName.VAL,
            hybrid_run_dirs=(hybrids[0], hybrids[1], hybrids[1]),
            deep_run_dirs=deeps,
            settings=settings,
        )


def test_three_seed_test_gate_rejects_stale_validation_run_set(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    gate_path = (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    )
    document = json.loads(gate_path.read_text(encoding="utf-8"))
    document["hybrid_run_ids"] = ["stale-a", "stale-b", "stale-c"]
    document["selected_run_id"] = "stale-a"
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in document.items() if key != "artifact_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    gate_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match=r"finalist set differs|selected run differs"):
        evaluate_three_seed(
            split=SplitName.TEST,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )
