import json
from pathlib import Path

import numpy as np

from ai_service.config import Settings
from ai_service.evaluation.release import aggregate_three_seed_release


def _run(tmp_path: Path, seed: int, best_val: float) -> Path:
    run_dir = tmp_path / "runs" / f"run-s{seed}"
    evaluation = run_dir / "evaluation"
    checkpoints = run_dir / "checkpoints"
    evaluation.mkdir(parents=True)
    checkpoints.mkdir()
    settings = Settings()
    settings.train.seed = seed
    (run_dir / "run-manifest.json").write_text(
        json.dumps(
            {
                "status": "evaluated",
                "experiment_signature_sha256": settings.experiment_signature_sha256(),
                "lineage": {"snapshot": "a", "embedding": "b", "rules": "c"},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "resolved-config.json").write_text(
        json.dumps(settings.resolved_document()), encoding="utf-8"
    )
    (evaluation / "report.json").write_text(
        json.dumps({"results": {"passed": True}}), encoding="utf-8"
    )
    users = np.arange(100)
    hybrid = np.linspace(0.7, 0.9, 100)
    baseline = np.linspace(0.3, 0.5, 100)
    np.savez_compressed(
        evaluation / "per-user-metrics.npz",
        user_ids=users,
        hybrid_hr=hybrid,
        hybrid_ndcg=hybrid,
        hybrid_gauc=hybrid,
        deep_hr=baseline,
        deep_ndcg=baseline,
        deep_gauc=baseline,
        wide_hr=baseline,
        wide_ndcg=baseline,
        wide_gauc=baseline,
        item_cf_hr=baseline,
        item_cf_ndcg=baseline,
        item_cf_gauc=baseline,
    )
    checkpoint = checkpoints / "release-candidate.pt"
    checkpoint.write_bytes(b"checkpoint")
    checkpoint.with_suffix(".pt.manifest.json").write_text(
        json.dumps({"best_val_ndcg_at_k": best_val}), encoding="utf-8"
    )
    (run_dir / "pipeline-state.json").write_text(
        json.dumps({"checkpoint_path": str(checkpoint)}), encoding="utf-8"
    )
    return run_dir


def test_three_seed_release_gate_selects_by_validation_and_seals_runs(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    settings.eval.bootstrap_samples = 100
    runs = (
        _run(tmp_path, 42, 0.4),
        _run(tmp_path, 2027, 0.6),
        _run(tmp_path, 31415, 0.5),
    )

    report = aggregate_three_seed_release(settings, runs)

    assert report["passed"] is True
    assert report["selected_run_id"] == "run-s2027"
    for run_dir in runs:
        manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "sealed"
