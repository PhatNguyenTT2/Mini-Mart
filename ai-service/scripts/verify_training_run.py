"""Read-only structural verifier for one diagnostic or production training run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from ai_service.config import Settings
from ai_service.contracts import PipelineState, TrainingVariant
from ai_service.errors import ArtifactIntegrityError
from ai_service.training.run import RunLifecycle


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError(f"cannot read JSON artifact: {path}") from error
    if not isinstance(value, dict):
        raise ArtifactIntegrityError(f"JSON artifact is not an object: {path}")
    return value


def verify_training_run(
    artifact_root: Path,
    run_id: str,
    *,
    expected_variant: TrainingVariant,
    expected_stage: str,
    expected_snapshot_id: str,
) -> dict[str, object]:
    run_dir = artifact_root.resolve() / "runs" / run_id
    if not run_dir.is_dir():
        raise ArtifactIntegrityError(f"training run does not exist: {run_dir}")
    lifecycle = RunLifecycle.load(run_dir)
    if lifecycle.document.get("training_variant") != expected_variant.value:
        raise ArtifactIntegrityError("training variant does not match requested variant")
    resolved = Settings.from_resolved_document(_read_json(run_dir / "resolved-config.json"))
    if resolved.data.snapshot_id != expected_snapshot_id:
        raise ArtifactIntegrityError("training snapshot ID differs from expected snapshot")
    if resolved.train.campaign_stage != expected_stage:
        raise ArtifactIntegrityError("training campaign stage differs from expected stage")
    state = PipelineState.model_validate_json((run_dir / "pipeline-state.json").read_text())
    if state.run_id != run_id or state.training_variant is not expected_variant:
        raise ArtifactIntegrityError("pipeline state identity mismatch")
    if state.lineage is None:
        raise ArtifactIntegrityError("pipeline state is missing artifact lineage")
    manifest_lineage = lifecycle.document.get("lineage")
    if manifest_lineage != state.lineage.as_mapping():
        raise ArtifactIntegrityError("run manifest and pipeline state lineage differ")
    checkpoints = run_dir / "checkpoints"
    best = checkpoints / "best.pt"
    last = checkpoints / "last.pt"
    if not best.is_file() or not last.is_file():
        raise ArtifactIntegrityError("best.pt and last.pt are required")
    best_manifest = _read_json(checkpoints / "best.pt.manifest.json")
    last_manifest = _read_json(checkpoints / "last.pt.manifest.json")
    if best_manifest.get("content_sha256") != _sha256(best):
        raise ArtifactIntegrityError("best checkpoint checksum mismatch")
    if last_manifest.get("content_sha256") != _sha256(last):
        raise ArtifactIntegrityError("last checkpoint checksum mismatch")
    if state.checkpoint_path != str(best):
        raise ArtifactIntegrityError("pipeline state must point to checkpoints/best.pt")
    history_path = run_dir / "training" / "history.jsonl"
    rows = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ArtifactIntegrityError("training history is empty")
    epochs = [int(row["epoch"]) for row in rows]
    if epochs != list(range(1, len(epochs) + 1)):
        raise ArtifactIntegrityError("training history epochs are not continuous")
    for row in rows:
        for name, value in row.items():
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and not math.isfinite(float(value))
            ):
                raise ArtifactIntegrityError(f"history contains non-finite value: {name}")
        if not bool(row.get("model_hard_cache_updated", False)):
            raise ArtifactIntegrityError("model hard cache was not updated for an epoch")
        if (
            expected_variant is TrainingVariant.DEEP_ONLY
            and abs(float(row.get("wide_gradient_norm", 0.0))) > 1e-7
        ):
            raise ArtifactIntegrityError("Deep-only Wide gradient invariant failed")
        if float(row.get("val_gauc", 0.0)) < 0.50:
            raise ArtifactIntegrityError("training GAUC fell below catastrophic floor")
    for forbidden in (
        run_dir / "checkpoints" / "pareto",
        run_dir / "checkpoints" / "release-candidate.pt",
    ):
        if forbidden.exists():
            raise ArtifactIntegrityError(f"unexpected checkpoint side effect: {forbidden}")
    summary = _read_json(run_dir / "training" / "summary.json")
    if summary.get("run_id") not in (None, run_id):
        raise ArtifactIntegrityError("training summary run ID mismatch")
    return {
        "passed": True,
        "run_id": run_id,
        "status": lifecycle.status.value,
        "epochs": len(rows),
        "best_checkpoint_sha256": best_manifest.get("content_sha256"),
        "last_checkpoint_sha256": last_manifest.get("content_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--expected-variant", choices=[v.value for v in TrainingVariant], required=True
    )
    parser.add_argument("--expected-stage", choices=("diagnostic", "production"), required=True)
    parser.add_argument("--expected-snapshot-id", required=True)
    args = parser.parse_args()
    result = verify_training_run(
        args.artifact_root,
        args.run_id,
        expected_variant=TrainingVariant(args.expected_variant),
        expected_stage=args.expected_stage,
        expected_snapshot_id=args.expected_snapshot_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
