"""Execute one hash-bound conventional baseline through the shared evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ai_service_v2.adapters.harmonized_baselines import (
    HarmonizedBaselineSpec,
    descriptor_for_baseline,
    fit_harmonized_baseline,
    load_harmonized_baseline_checkpoint,
    save_harmonized_baseline_checkpoint,
)
from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.data.suitability import assess_snapshot_suitability
from ai_service_v2.errors import ContractError, IntegrityError, ProtocolError, ScoreError
from ai_service_v2.evaluation.artifacts import (
    MatrixScoreProvider,
    load_materialized_scores,
    materialize_scores,
)
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.evaluation.persistence import save_evaluation
from ai_service_v2.hashing import (
    canonical_json_sha256,
    load_strict_json,
    sha256_file,
)
from ai_service_v2.protocol import build_protocol, load_protocol
from ai_service_v2.training import (
    ProcessCommand,
    create_run,
    load_run,
    load_run_command,
    update_run_status,
    validate_external_application_artifact,
    write_run_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run-harmonized-baseline")
    commands = parser.add_subparsers(dest="command", required=True)

    train = commands.add_parser("train-val")
    train.add_argument("snapshot_root", type=Path)
    train.add_argument("protocol", type=Path)
    train.add_argument("run_root", type=Path)
    train.add_argument("score_root", type=Path)
    train.add_argument("evaluation_root", type=Path)
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--environment-lock", type=Path, required=True)
    train.add_argument("--seed", type=int, required=True)
    train.add_argument("--chunk-size", type=int, default=128)

    apply = commands.add_parser("score-evaluate")
    apply.add_argument("snapshot_root", type=Path)
    apply.add_argument("run_root", type=Path)
    apply.add_argument("protocol", type=Path)
    apply.add_argument("score_root", type=Path)
    apply.add_argument("evaluation_root", type=Path)
    apply.add_argument("--chunk-size", type=int, default=128)
    apply.add_argument(
        "--application-ref",
        type=Path,
        help="fresh external JSON receipt path required when applying a frozen run to TEST",
    )
    return parser


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _protocol_hash(protocol: Any) -> str:
    return canonical_json_sha256(protocol.manifest.to_mapping())


def _dataset_hash(snapshot: Any) -> str:
    return canonical_json_sha256(snapshot.manifest.to_mapping())


def _write_reference(
    run_root: Path,
    *,
    filename: str,
    score_root: Path,
    evaluation_root: Path,
    selection_protocol_sha256: str,
    scoring_protocol_sha256: str,
    split: str,
    process_command: ProcessCommand,
) -> None:
    write_run_artifact(
        run_root,
        filename,
        {
            "schema_version": "harmonized-baseline-evidence-ref/1.0",
            "score_root": str(score_root.resolve()),
            "score_manifest_sha256": sha256_file(score_root / "manifest.json"),
            "evaluation_root": str(evaluation_root.resolve()),
            "evaluation_receipt_sha256": sha256_file(evaluation_root / "evaluation_receipt.json"),
            "selection_protocol_manifest_sha256": selection_protocol_sha256,
            "scoring_protocol_manifest_sha256": scoring_protocol_sha256,
            "split": split,
            "test_set_opened": split == "test",
            "application_command": process_command.to_mapping(),
            "application_command_sha256": canonical_json_sha256(process_command.to_mapping()),
        },
    )


def _evaluate_materialized(protocol: Any, score_root: Path, evaluation_root: Path) -> Any:
    scores = load_materialized_scores(score_root)
    if scores.manifest.protocol_manifest_sha256 != _protocol_hash(protocol):
        raise IntegrityError("score artifact protocol hash differs from the scoring protocol")
    if scores.manifest.candidate_order_sha256 != protocol.manifest.candidate_order_sha256:
        raise IntegrityError("score artifact candidate order differs from the protocol")
    provider = MatrixScoreProvider(
        scores,
        protocol.eligible_user_ids,
        protocol.candidate_item_ids,
    )
    result = FullCatalogEvaluator(protocol).evaluate(
        provider,
        run_id=scores.manifest.run_id,
        model_id=scores.manifest.model_id,
    )
    return save_evaluation(result, evaluation_root)


def _train_val(args: argparse.Namespace, process_command: ProcessCommand) -> int:
    if args.seed < 0 or args.chunk_size < 1:
        raise ContractError("seed and chunk size are outside the admitted range")
    protocol = load_protocol(args.protocol)
    if protocol.manifest.split != "val" or protocol.manifest.test_set_opened:
        raise ProtocolError("baseline training requires a sealed validation protocol")
    snapshot = load_canonical_snapshot(args.snapshot_root, required_splits=("train", "val"))
    protocol = load_protocol(args.protocol, snapshot=snapshot)
    suitability = assess_snapshot_suitability(snapshot)
    if suitability.verdict != "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY":
        raise IntegrityError(
            "dataset suitability gate failed: " + ", ".join(suitability.blocking_findings)
        )
    if process_command.argv_source != "process_sys_argv":
        raise IntegrityError("scientific baseline execution requires process_sys_argv")
    spec_document = load_strict_json(args.config)
    spec = HarmonizedBaselineSpec.from_mapping(spec_document)
    if not args.environment_lock.is_file():
        raise IntegrityError("environment lock is missing")
    for root in (args.run_root, args.score_root, args.evaluation_root):
        if root.exists():
            raise IntegrityError(f"output root already exists: {root}")

    checkpoint_rule = (
        "train_only_binary_cosine_top_k_fit"
        if spec.model_kind == "itemknn"
        else "final_training_state_after_fixed_epochs"
    )
    run = create_run(
        root=args.run_root,
        run_id=args.run_root.name,
        model_id=spec.model_id,
        dataset_manifest_sha256=_dataset_hash(snapshot),
        protocol_manifest_sha256=_protocol_hash(protocol),
        seed=args.seed,
        environment_lock_sha256=sha256_file(args.environment_lock),
        checkpoint_rule=checkpoint_rule,
        process_command=process_command,
    )
    try:
        write_run_artifact(run.root, "config.json", spec.to_mapping())
        model, report = fit_harmonized_baseline(snapshot, protocol, spec, seed=args.seed)
        checkpoint = save_harmonized_baseline_checkpoint(
            model,
            root=run.root / "checkpoint",
            run_id=run.manifest.run_id,
            seed=args.seed,
            checkpoint_rule=checkpoint_rule,
        )
        write_run_artifact(
            run.root,
            "model_artifact.json",
            {
                "schema_version": "harmonized-baseline-model-artifact/1.0",
                "model_id": spec.model_id,
                "model_kind": spec.model_kind,
                "spec_sha256": canonical_json_sha256(spec.to_mapping()),
                "descriptor": descriptor_for_baseline(spec).to_mapping(),
                "checkpoint_directory": "checkpoint",
                "checkpoint_manifest_sha256": sha256_file(
                    run.root / "checkpoint" / "manifest.json"
                ),
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            },
        )
        write_run_artifact(run.root, "training_report.json", report)
        materialize_scores(
            protocol,
            model,
            root=args.score_root,
            run_id=run.manifest.run_id,
            model_id=spec.model_id,
            chunk_size=args.chunk_size,
        )
        persisted = _evaluate_materialized(protocol, args.score_root, args.evaluation_root)
        _write_reference(
            run.root,
            filename="validation_evidence_ref.json",
            score_root=args.score_root,
            evaluation_root=args.evaluation_root,
            selection_protocol_sha256=_protocol_hash(protocol),
            scoring_protocol_sha256=_protocol_hash(protocol),
            split="val",
            process_command=process_command,
        )
        completed = update_run_status(
            run,
            status="PASS",
            checkpoint_sha256=checkpoint["checkpoint_sha256"],
        )
    except Exception:
        update_run_status(run, status="INCOMPLETE")
        raise
    _print(
        {
            "status": completed.manifest.status,
            "run_id": completed.manifest.run_id,
            "model_id": completed.manifest.model_id,
            "split": "val",
            "test_set_opened": False,
            "aggregate_metrics": persisted.receipt.aggregate_metrics,
            "checkpoint_sha256": completed.manifest.checkpoint_sha256,
        }
    )
    return 0


def _load_bound_baseline(snapshot: Any, protocol: Any, run_root: Path) -> tuple[Any, Any]:
    run = load_run(run_root)
    load_run_command(run)
    if run.manifest.status != "PASS":
        raise IntegrityError("only PASS baseline runs may be applied")
    if run.manifest.dataset_manifest_sha256 != _dataset_hash(snapshot):
        raise IntegrityError("baseline run dataset binding differs from snapshot")
    selection = build_protocol(
        snapshot,
        split="val",
        cutoff=protocol.manifest.cutoff,
        metric_version=protocol.manifest.metric_version,
    )
    if run.manifest.protocol_manifest_sha256 != _protocol_hash(selection):
        raise IntegrityError("baseline run is not bound to the matching validation protocol")
    artifact = load_strict_json(run.root / "model_artifact.json")
    expected_artifact_fields = {
        "schema_version",
        "model_id",
        "model_kind",
        "spec_sha256",
        "descriptor",
        "checkpoint_directory",
        "checkpoint_manifest_sha256",
        "checkpoint_sha256",
    }
    if set(artifact) != expected_artifact_fields:
        raise IntegrityError("harmonized baseline model artifact fields are invalid")
    if artifact["schema_version"] != "harmonized-baseline-model-artifact/1.0":
        raise IntegrityError("unsupported harmonized baseline model artifact")
    config = load_strict_json(run.root / "config.json")
    spec = HarmonizedBaselineSpec.from_mapping(config)
    if (
        artifact["model_id"] != spec.model_id
        or artifact["model_kind"] != spec.model_kind
        or artifact["spec_sha256"] != canonical_json_sha256(spec.to_mapping())
        or artifact["descriptor"] != descriptor_for_baseline(spec).to_mapping()
        or artifact["checkpoint_directory"] != "checkpoint"
        or artifact["checkpoint_manifest_sha256"]
        != sha256_file(run.root / "checkpoint" / "manifest.json")
    ):
        raise IntegrityError("harmonized baseline model artifact binding failed")
    model, checkpoint = load_harmonized_baseline_checkpoint(
        run.root / "checkpoint", snapshot=snapshot, protocol=protocol
    )
    if (
        checkpoint["run_id"] != run.manifest.run_id
        or checkpoint["model_id"] != run.manifest.model_id
        or checkpoint["seed"] != run.manifest.seed
        or checkpoint["checkpoint_sha256"] != run.manifest.checkpoint_sha256
        or checkpoint["checkpoint_sha256"] != artifact["checkpoint_sha256"]
    ):
        raise IntegrityError("harmonized baseline checkpoint/run binding failed")
    return run, model


def _score_evaluate(args: argparse.Namespace, process_command: ProcessCommand) -> int:
    if args.chunk_size < 1:
        raise ContractError("chunk size must be positive")
    protocol = load_protocol(args.protocol)
    application_ref: Path | None = None
    if protocol.manifest.split == "test":
        if args.application_ref is None:
            raise ProtocolError(
                "TEST scoring requires --application-ref outside the frozen validation run"
            )
        application_ref = validate_external_application_artifact(
            source_run_root=args.run_root,
            artifact_path=args.application_ref,
            output_roots=(args.score_root, args.evaluation_root),
        )
    elif args.application_ref is not None:
        raise ProtocolError("--application-ref is reserved for TEST scoring")
    required_splits = (
        ("train", "val", "test") if protocol.manifest.split == "test" else ("train", "val")
    )
    snapshot = load_canonical_snapshot(args.snapshot_root, required_splits=required_splits)
    protocol = load_protocol(args.protocol, snapshot=snapshot)
    for root in (args.score_root, args.evaluation_root):
        if root.exists():
            raise IntegrityError(f"output root already exists: {root}")
    run, model = _load_bound_baseline(snapshot, protocol, args.run_root)
    materialize_scores(
        protocol,
        model,
        root=args.score_root,
        run_id=run.manifest.run_id,
        model_id=run.manifest.model_id,
        chunk_size=args.chunk_size,
    )
    persisted = _evaluate_materialized(protocol, args.score_root, args.evaluation_root)
    reference_name = (
        "test_evidence_ref.json"
        if protocol.manifest.split == "test"
        else "validation_replay_evidence_ref.json"
    )
    reference_path = (
        application_ref if application_ref is not None else run.root / reference_name
    )
    _write_reference(
        reference_path.parent,
        filename=reference_path.name,
        score_root=args.score_root,
        evaluation_root=args.evaluation_root,
        selection_protocol_sha256=run.manifest.protocol_manifest_sha256,
        scoring_protocol_sha256=_protocol_hash(protocol),
        split=protocol.manifest.split,
        process_command=process_command,
    )
    _print(
        {
            "status": persisted.receipt.verdict,
            "run_id": run.manifest.run_id,
            "model_id": run.manifest.model_id,
            "split": protocol.manifest.split,
            "test_set_opened": protocol.manifest.test_set_opened,
            "aggregate_metrics": persisted.receipt.aggregate_metrics,
        }
    )
    return 0


def main() -> int:
    args = _parser().parse_args()
    process_command = ProcessCommand(
        executable=str(Path(sys.executable).resolve()),
        argv=tuple(sys.argv),
        argv_source="process_sys_argv",
    )
    try:
        if args.command == "train-val":
            return _train_val(args, process_command)
        return _score_evaluate(args, process_command)
    except (ContractError, IntegrityError, ProtocolError, ScoreError, OSError, ValueError) as error:
        _print({"status": "FAIL", "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
