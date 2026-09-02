"""Command-line entry points for the local, fail-closed research runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai_service_v2 import __version__
from ai_service_v2.adapters.v5_source import materialize_v5_source_bundle
from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.data.io import load_canonical_snapshot, materialize_snapshot
from ai_service_v2.data.rules import load_rule_table, save_rule_table
from ai_service_v2.data.suitability import assess_snapshot_suitability
from ai_service_v2.errors import ContractError, IntegrityError, ProtocolError
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
    sha256_bytes,
    sha256_file,
)
from ai_service_v2.models.baselines import MostPopScorer, RandomScorer
from ai_service_v2.models.proposed import (
    HybridScorer,
    RuleOnlyScorer,
    TwoTowerConfig,
    item_text_hash_features,
)
from ai_service_v2.models.registry import (
    MODEL_KINDS,
    ModelRunSpec,
    default_spec,
    descriptor_for_spec,
    train_local_model,
)
from ai_service_v2.protocol import build_protocol, load_protocol, save_protocol
from ai_service_v2.training import (
    create_run,
    load_checkpoint,
    load_run,
    save_checkpoint,
    update_run_status,
    write_run_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-v2")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-manifest")
    validate.add_argument("path", type=Path)

    snapshot = commands.add_parser("validate-snapshot")
    snapshot.add_argument("root", type=Path)

    materialize = commands.add_parser("materialize-snapshot")
    materialize.add_argument("source_root", type=Path)
    materialize.add_argument("output_root", type=Path)

    materialize_v5 = commands.add_parser("materialize-v5-source")
    materialize_v5.add_argument("source_root", type=Path)
    materialize_v5.add_argument("output_root", type=Path)

    assess = commands.add_parser("assess-snapshot")
    assess.add_argument("snapshot_root", type=Path)

    protocol = commands.add_parser("build-protocol")
    protocol.add_argument("snapshot_root", type=Path)
    protocol.add_argument("output", type=Path)
    protocol.add_argument("--split", choices=("val", "test"), default="val")
    protocol.add_argument("--allow-test", action="store_true")
    protocol.add_argument("--cutoff", type=int, default=10)
    protocol.add_argument("--metric-version", default="ranking-v1")

    train = commands.add_parser("train")
    train.add_argument("snapshot_root", type=Path)
    train.add_argument("protocol", type=Path)
    train.add_argument("run_root", type=Path)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--config", type=Path)
    train.add_argument("--feature-dim", type=int, default=32)
    train.add_argument("--model-kind", choices=sorted(MODEL_KINDS), default=None)
    train.add_argument("--model-id")
    train.add_argument("--wide-weight", type=float, default=1.0)
    train.add_argument("--rule-min-support", type=int, default=1)
    train.add_argument(
        "--fixture-only",
        action="store_true",
        help="allow only the repository's explicitly labeled non-scientific test fixture",
    )
    train.add_argument("--environment-lock", type=Path)
    train.add_argument(
        "--command-text",
        dest="command_text",
        default="ai-v2 train (command not supplied by caller)",
        help="exact command description to bind into the run manifest",
    )

    export = commands.add_parser("export-scores")
    export.add_argument("snapshot_root", type=Path)
    export.add_argument("run_root", type=Path)
    export.add_argument("protocol", type=Path)
    export.add_argument("score_root", type=Path)
    export.add_argument("--chunk-size", type=int, default=128)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("protocol", type=Path)
    evaluate.add_argument("score_root", type=Path)
    evaluate.add_argument("output_root", type=Path)

    summarize = commands.add_parser("summarize-run")
    summarize.add_argument("run_root", type=Path)

    hashed = commands.add_parser("hash-json")
    hashed.add_argument("path", type=Path)
    return parser


def _print(document: dict[str, Any]) -> None:
    print(json.dumps(document, ensure_ascii=False, sort_keys=True))


def _dataset_manifest_hash(snapshot: Any) -> str:
    return canonical_json_sha256(snapshot.manifest.to_mapping())


def _protocol_manifest_hash(protocol: Any) -> str:
    return canonical_json_sha256(protocol.manifest.to_mapping())


def _load_model_spec(args: argparse.Namespace) -> tuple[dict[str, Any], ModelRunSpec]:
    """Load one explicit local model specification without implicit overrides."""

    if args.config is None:
        kind = args.model_kind or "deep_two_tower"
        spec = default_spec(
            kind,
            feature_dimensions=args.feature_dim,
            wide_weight=args.wide_weight,
            rule_min_support=args.rule_min_support,
            model_id=args.model_id,
        )
        return spec.to_mapping(), spec

    document = load_strict_json(args.config)
    if document.get("schema_version") == "model-run-spec/1.0":
        spec = ModelRunSpec.from_mapping(document)
    elif document.get("schema_version") == "training-config/1.0":
        # Read old fixture configs so historical local runs remain inspectable;
        # new runs always persist the registry schema below.
        required = {
            "schema_version",
            "model_kind",
            "feature_source",
            "feature_dimensions",
            "two_tower",
        }
        if set(document) != required or document["model_kind"] != "deep_two_tower":
            raise ContractError("legacy training config is not a deep two-tower config")
        if document["feature_source"] != "deterministic_hash_features":
            raise ContractError("unsupported local feature source")
        dimensions = document["feature_dimensions"]
        two_tower = document["two_tower"]
        if (
            isinstance(dimensions, bool)
            or not isinstance(dimensions, int)
            or dimensions < 4
            or not isinstance(two_tower, dict)
        ):
            raise ContractError("legacy training config values are invalid")
        spec = default_spec(
            "deep_two_tower",
            feature_dimensions=dimensions,
            two_tower_config=TwoTowerConfig.from_mapping(two_tower),
            model_id=args.model_id,
        )
        document = spec.to_mapping()
    else:
        raise ContractError("unsupported model config schema")

    if args.model_kind is not None and args.model_kind != spec.model_kind:
        raise ContractError("--model-kind conflicts with the supplied model config")
    if args.model_id is not None and args.model_id != spec.model_id:
        raise ContractError("--model-id conflicts with the supplied model config")
    return spec.to_mapping(), spec


def _environment_hash(path: Path | None) -> str:
    if path is None:
        # Explicitly local-only; this is not a paper runtime lock.
        return sha256_bytes(b"environment-unpinned-fixture-only")
    return sha256_file(path)


def _training_report_document(bundle: Any, seed: int) -> dict[str, Any]:
    report = bundle.training_report
    if report is None:
        return {
            "schema_version": "training-report/1.0",
            "model_id": bundle.descriptor.model_id,
            "model_kind": bundle.spec.model_kind,
            "seed": seed,
            "fit_scope": "TRAIN_ONLY" if bundle.rules is not None else "NON_LEARNING_CONTROL",
            "epochs": 0,
            "update_count": 0,
            "mean_loss_by_epoch": [],
            "config_sha256": bundle.descriptor.config_sha256,
        }
    return {
        "schema_version": "training-report/1.0",
        "model_id": bundle.descriptor.model_id,
        "model_kind": bundle.spec.model_kind,
        "seed": report.seed,
        "epochs": report.epochs,
        "update_count": report.update_count,
        "mean_loss_by_epoch": list(report.mean_loss_by_epoch),
        "config_sha256": report.config_sha256,
    }


def _cmd_validate_manifest(path: Path) -> int:
    parsed = load_strict_json(path)
    manifest = DatasetManifest.from_mapping(parsed)
    _print(
        {
            "status": "PASS",
            "dataset_id": manifest.dataset_id,
            "dataset_sha256": manifest.dataset_sha256,
            "manifest_sha256": canonical_json_sha256(parsed),
            "num_users": manifest.num_users,
            "num_items": manifest.num_items,
            "num_interactions": manifest.num_interactions,
        }
    )
    return 0


def _cmd_validate_snapshot(root: Path) -> int:
    snapshot = load_canonical_snapshot(root)
    _print(
        {
            "status": "PASS",
            "dataset_id": snapshot.manifest.dataset_id,
            "dataset_sha256": snapshot.manifest.dataset_sha256,
            "num_users": snapshot.manifest.num_users,
            "num_items": snapshot.manifest.num_items,
            "num_interactions": snapshot.manifest.num_interactions,
            "splits": {split: len(events) for split, events in snapshot.events_by_split.items()},
        }
    )
    return 0


def _cmd_build_protocol(args: argparse.Namespace) -> int:
    snapshot = load_canonical_snapshot(args.snapshot_root)
    if args.split == "test" and not args.allow_test:
        raise ProtocolError("TEST is sealed; pass --allow-test explicitly")
    protocol = build_protocol(
        snapshot,
        split=args.split,
        allow_test=args.allow_test,
        cutoff=args.cutoff,
        metric_version=args.metric_version,
    )
    path = save_protocol(protocol, args.output)
    _print(
        {
            "status": "PASS",
            "protocol": str(path),
            "protocol_id": protocol.manifest.protocol_id,
            "protocol_manifest_sha256": _protocol_manifest_hash(protocol),
            "split": args.split,
            "test_set_opened": protocol.manifest.test_set_opened,
            "eligible_users": len(protocol.eligible_user_ids),
        }
    )
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    snapshot = load_canonical_snapshot(args.snapshot_root)
    suitability = assess_snapshot_suitability(snapshot)
    manifest = snapshot.manifest
    fixture_override = (
        args.fixture_only
        and manifest.schema_version == "dataset-manifest/1.0"
        and manifest.dataset_id.startswith("fixture-")
        and manifest.source_kind == "fixture"
        and manifest.provenance_status == "FIXTURE_ONLY"
        and manifest.license_status == "TEST_ONLY"
    )
    if (
        suitability.verdict != "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY"
        and not fixture_override
    ):
        raise IntegrityError(
            "dataset suitability gate is not admitted: " + ", ".join(suitability.blocking_findings)
        )
    protocol = load_protocol(args.protocol, snapshot=snapshot)
    if protocol.manifest.split == "test":
        raise ProtocolError("training must bind to a validation protocol, not TEST")
    config_document, spec = _load_model_spec(args)
    config_hash = canonical_json_sha256(config_document)
    command_hash = sha256_bytes(args.command_text.encode("utf-8"))
    if spec.model_kind in {"deep_two_tower", "hybrid"}:
        checkpoint_rule = "final_training_state_after_fixed_epochs"
    elif spec.model_kind == "rule_only":
        checkpoint_rule = "train_only_rule_fit"
    else:
        checkpoint_rule = "not_applicable_non_learning_control"
    run = create_run(
        root=args.run_root,
        run_id=args.run_root.name,
        model_id=spec.model_id,
        dataset_manifest_sha256=_dataset_manifest_hash(snapshot),
        protocol_manifest_sha256=_protocol_manifest_hash(protocol),
        seed=args.seed,
        environment_lock_sha256=_environment_hash(args.environment_lock),
        checkpoint_rule=checkpoint_rule,
        command_sha256=command_hash,
    )
    try:
        write_run_artifact(run.root, "config.json", config_document)
        bundle = train_local_model(snapshot, protocol, spec, seed=args.seed)
        if bundle.descriptor != descriptor_for_spec(spec):
            raise IntegrityError("local model descriptor does not match registry spec")

        checkpoint_sha256: str | None = None
        checkpoint_directory: str | None = None
        if bundle.deep_model is not None:
            checkpoint = save_checkpoint(
                bundle.deep_model,
                root=run.root / "checkpoint",
                run_id=run.manifest.run_id,
                seed=args.seed,
                checkpoint_rule=run.manifest.checkpoint_rule,
            )
            checkpoint_sha256 = checkpoint.checkpoint_sha256
            checkpoint_directory = "checkpoint"

        rule_artifact_sha256: str | None = None
        rule_artifact_file: str | None = None
        if bundle.rules is not None:
            rule_path = save_rule_table(bundle.rules, run.root / "rule_artifact.json")
            rule_artifact_sha256 = sha256_file(rule_path)
            rule_artifact_file = rule_path.name

        write_run_artifact(
            run.root, "training_report.json", _training_report_document(bundle, args.seed)
        )
        write_run_artifact(
            run.root,
            "model_artifact.json",
            {
                "schema_version": "model-artifact/1.0",
                "model_kind": spec.model_kind,
                "model_id": spec.model_id,
                "model_spec_sha256": canonical_json_sha256(spec.to_mapping()),
                "descriptor": bundle.descriptor.to_mapping(),
                "checkpoint_directory": checkpoint_directory,
                "checkpoint_sha256": checkpoint_sha256,
                "rule_artifact_file": rule_artifact_file,
                "rule_artifact_sha256": rule_artifact_sha256,
            },
        )
        completed = update_run_status(run, status="PASS", checkpoint_sha256=checkpoint_sha256)
    except Exception:
        update_run_status(run, status="INCOMPLETE")
        raise
    _print(
        {
            "status": completed.manifest.status,
            "run_root": str(completed.root),
            "run_id": completed.manifest.run_id,
            "model_id": completed.manifest.model_id,
            "checkpoint_sha256": completed.manifest.checkpoint_sha256,
            "config_sha256": config_hash,
            "model_kind": spec.model_kind,
        }
    )
    return 0


def _load_model_spec_from_run(run: Any) -> ModelRunSpec:
    """Load a run's frozen registry specification without repairing it."""

    config = load_strict_json(run.root / "config.json")
    if config.get("schema_version") == "model-run-spec/1.0":
        spec = ModelRunSpec.from_mapping(config)
    elif config.get("schema_version") == "training-config/1.0":
        # Compatibility for the original deep-only fixture runner. New runs
        # always use the registry schema and emit model_artifact.json.
        required = {
            "schema_version",
            "model_kind",
            "feature_source",
            "feature_dimensions",
            "two_tower",
        }
        if set(config) != required or config["model_kind"] != "deep_two_tower":
            raise IntegrityError("legacy run config is not a deep two-tower config")
        dimensions = config["feature_dimensions"]
        two_tower = config["two_tower"]
        if (
            isinstance(dimensions, bool)
            or not isinstance(dimensions, int)
            or dimensions < 4
            or not isinstance(two_tower, dict)
        ):
            raise IntegrityError("legacy run config values are invalid")
        spec = default_spec(
            "deep_two_tower",
            feature_dimensions=dimensions,
            two_tower_config=TwoTowerConfig.from_mapping(two_tower),
            model_id=run.manifest.model_id,
        )
    else:
        raise IntegrityError("unsupported run config schema")
    if spec.model_id != run.manifest.model_id:
        raise IntegrityError("run model ID does not match model config")
    if spec.feature_source != "deterministic_hash_features":
        raise IntegrityError("unsupported run feature source")
    return spec


def _load_rule_artifact_for_run(run: Any, artifact: dict[str, Any]) -> Any:
    filename = artifact.get("rule_artifact_file")
    digest = artifact.get("rule_artifact_sha256")
    if (
        filename != "rule_artifact.json"
        or not isinstance(filename, str)
        or Path(filename).name != filename
        or not isinstance(digest, str)
    ):
        raise IntegrityError("rule artifact reference is invalid")
    path = run.root / filename
    if sha256_file(path) != digest:
        raise IntegrityError("rule artifact hash does not match model artifact")
    return load_rule_table(path)


def _load_model_for_run(snapshot: Any, protocol: Any, run: Any) -> Any:
    spec = _load_model_spec_from_run(run)
    expected_descriptor = descriptor_for_spec(spec)
    artifact_path = run.root / "model_artifact.json"

    if not artifact_path.is_file():
        # Only pre-registry deep-only runs may use this compatibility path.
        if spec.model_kind != "deep_two_tower":
            raise IntegrityError("model artifact is required for registry model runs")
        features = item_text_hash_features(snapshot, dimensions=spec.feature_dimensions)
        model, checkpoint = load_checkpoint(
            run.root / "checkpoint", snapshot=snapshot, features=features
        )
        if checkpoint.run_id != run.manifest.run_id or checkpoint.model_id != run.manifest.model_id:
            raise IntegrityError("checkpoint identity does not match run manifest")
        if checkpoint.seed != run.manifest.seed:
            raise IntegrityError("checkpoint seed does not match run manifest")
        if run.manifest.checkpoint_sha256 != checkpoint.checkpoint_sha256:
            raise IntegrityError("run manifest checkpoint hash does not match payload")
        if checkpoint.descriptor["config_sha256"] != canonical_json_sha256(spec.two_tower or {}):
            raise IntegrityError("checkpoint descriptor config hash does not match run config")
        return model

    artifact = load_strict_json(artifact_path)
    required = {
        "schema_version",
        "model_kind",
        "model_id",
        "model_spec_sha256",
        "descriptor",
        "checkpoint_directory",
        "checkpoint_sha256",
        "rule_artifact_file",
        "rule_artifact_sha256",
    }
    if set(artifact) != required or artifact["schema_version"] != "model-artifact/1.0":
        raise IntegrityError("model artifact fields do not match schema")
    if (
        artifact["model_kind"] != spec.model_kind
        or artifact["model_id"] != spec.model_id
        or artifact["model_spec_sha256"] != canonical_json_sha256(spec.to_mapping())
        or artifact["descriptor"] != expected_descriptor.to_mapping()
    ):
        raise IntegrityError("model artifact identity does not match registry spec")

    kind = spec.model_kind
    checkpoint_directory = artifact["checkpoint_directory"]
    checkpoint_sha256 = artifact["checkpoint_sha256"]
    if kind in {"random", "mostpop", "rule_only"}:
        if checkpoint_directory is not None or checkpoint_sha256 is not None:
            raise IntegrityError("non-learning local model cannot carry a checkpoint")
        if run.manifest.checkpoint_sha256 is not None:
            raise IntegrityError("non-learning run cannot carry a checkpoint hash")
    else:
        if checkpoint_directory != "checkpoint" or not isinstance(checkpoint_sha256, str):
            raise IntegrityError("deep model checkpoint reference is invalid")
        if run.manifest.checkpoint_sha256 != checkpoint_sha256:
            raise IntegrityError("run checkpoint hash does not match model artifact")

    if kind == "random":
        if (
            artifact["rule_artifact_file"] is not None
            or artifact["rule_artifact_sha256"] is not None
        ):
            raise IntegrityError("random model cannot carry a rule artifact")
        return RandomScorer(run.manifest.seed)
    if kind == "mostpop":
        if (
            artifact["rule_artifact_file"] is not None
            or artifact["rule_artifact_sha256"] is not None
        ):
            raise IntegrityError("mostpop model cannot carry a rule artifact")
        return MostPopScorer(snapshot.events_by_split["train"])

    rules = None
    if kind in {"rule_only", "hybrid"}:
        rules = _load_rule_artifact_for_run(run, artifact)
        if rules.min_support != spec.rule_min_support:
            raise IntegrityError("rule artifact support does not match model spec")
    elif artifact["rule_artifact_file"] is not None or artifact["rule_artifact_sha256"] is not None:
        raise IntegrityError("deep-only model cannot carry a rule artifact")

    if kind == "rule_only":
        assert rules is not None
        return RuleOnlyScorer(protocol, rules)

    features = item_text_hash_features(snapshot, dimensions=spec.feature_dimensions)
    model, checkpoint = load_checkpoint(
        run.root / "checkpoint", snapshot=snapshot, features=features
    )
    if checkpoint.run_id != run.manifest.run_id or checkpoint.model_id != run.manifest.model_id:
        raise IntegrityError("checkpoint identity does not match run manifest")
    if checkpoint.seed != run.manifest.seed:
        raise IntegrityError("checkpoint seed does not match run manifest")
    if checkpoint.checkpoint_sha256 != checkpoint_sha256:
        raise IntegrityError("checkpoint payload hash does not match model artifact")
    if checkpoint.descriptor != expected_descriptor.to_mapping():
        raise IntegrityError("checkpoint descriptor does not match model artifact")
    if kind == "deep_two_tower":
        return model
    assert rules is not None
    return HybridScorer(model, RuleOnlyScorer(protocol, rules), wide_weight=spec.wide_weight)


def _cmd_export_scores(args: argparse.Namespace) -> int:
    snapshot = load_canonical_snapshot(args.snapshot_root)
    run = load_run(args.run_root)
    if run.manifest.status != "PASS":
        raise IntegrityError("only PASS runs may export scores")
    protocol = load_protocol(args.protocol, snapshot=snapshot)
    if run.manifest.dataset_manifest_sha256 != _dataset_manifest_hash(snapshot):
        raise IntegrityError("run dataset binding does not match snapshot")
    if run.manifest.protocol_manifest_sha256 != _protocol_manifest_hash(protocol):
        raise IntegrityError("run protocol binding does not match protocol")
    model = _load_model_for_run(snapshot, protocol, run)
    materialized = materialize_scores(
        protocol,
        model,
        root=args.score_root,
        run_id=run.manifest.run_id,
        model_id=run.manifest.model_id,
        chunk_size=args.chunk_size,
    )
    write_run_artifact(
        run.root,
        "score_artifact_ref.json",
        {
            "schema_version": "score-artifact-ref/1.0",
            "root": str(materialized.root),
            "manifest_sha256": sha256_file(materialized.root / "manifest.json"),
        },
    )
    _print(
        {
            "status": "PASS",
            "score_root": str(materialized.root),
            "run_id": materialized.manifest.run_id,
            "model_id": materialized.manifest.model_id,
            "shape": list(materialized.manifest.score_shape),
        }
    )
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    protocol = load_protocol(args.protocol)
    scores = load_materialized_scores(args.score_root)
    if scores.manifest.protocol_manifest_sha256 != _protocol_manifest_hash(protocol):
        raise IntegrityError("score artifact protocol binding does not match protocol")
    if scores.manifest.candidate_order_sha256 != protocol.manifest.candidate_order_sha256:
        raise IntegrityError("score artifact candidate order does not match protocol")
    provider = MatrixScoreProvider(scores, protocol.eligible_user_ids, protocol.candidate_item_ids)
    result = FullCatalogEvaluator(protocol).evaluate(
        provider,
        run_id=scores.manifest.run_id,
        model_id=scores.manifest.model_id,
    )
    persisted = save_evaluation(result, args.output_root)
    _print(
        {
            "status": persisted.receipt.verdict,
            "evaluation_root": str(persisted.root),
            "run_id": persisted.receipt.run_id,
            "model_id": persisted.receipt.model_id,
            "aggregate_metrics": persisted.receipt.aggregate_metrics,
            "denominator_by_metric": persisted.receipt.denominator_by_metric,
        }
    )
    return 0


def _cmd_summarize_run(root: Path) -> int:
    run = load_run(root)
    summary: dict[str, Any] = {
        "status": "PASS",
        "run": run.manifest.to_mapping(),
        "artifacts": {
            "config": (root / "config.json").is_file(),
            "model_artifact": (root / "model_artifact.json").is_file(),
            "checkpoint": (root / "checkpoint" / "manifest.json").is_file(),
            "rule_artifact": (root / "rule_artifact.json").is_file(),
            "training_report": (root / "training_report.json").is_file(),
            "score_artifact_ref": (root / "score_artifact_ref.json").is_file(),
        },
    }
    if (root / "checkpoint" / "manifest.json").is_file():
        checkpoint = load_strict_json(root / "checkpoint" / "manifest.json")
        summary["checkpoint"] = {
            "checkpoint_sha256": checkpoint.get("checkpoint_sha256"),
            "seed": checkpoint.get("seed"),
        }
    if (root / "score_artifact_ref.json").is_file():
        summary["score_artifact_ref"] = load_strict_json(root / "score_artifact_ref.json")
    _print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-manifest":
            return _cmd_validate_manifest(args.path)
        if args.command == "validate-snapshot":
            return _cmd_validate_snapshot(args.root)
        if args.command == "materialize-snapshot":
            snapshot = materialize_snapshot(args.source_root, args.output_root)
            _print(
                {
                    "status": "PASS",
                    "dataset_id": snapshot.manifest.dataset_id,
                    "dataset_sha256": snapshot.manifest.dataset_sha256,
                    "output_root": str(args.output_root),
                }
            )
            return 0
        if args.command == "materialize-v5-source":
            snapshot = materialize_v5_source_bundle(args.source_root, args.output_root)
            _print(
                {
                    "status": "PASS",
                    "dataset_id": snapshot.manifest.dataset_id,
                    "dataset_sha256": snapshot.manifest.dataset_sha256,
                    "source_bundle_sha256": snapshot.manifest.source_bundle_sha256,
                    "output_root": str(args.output_root),
                }
            )
            return 0
        if args.command == "assess-snapshot":
            report = assess_snapshot_suitability(load_canonical_snapshot(args.snapshot_root))
            _print(report.to_mapping())
            return 0 if report.verdict == "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY" else 2
        if args.command == "build-protocol":
            return _cmd_build_protocol(args)
        if args.command == "train":
            return _cmd_train(args)
        if args.command == "export-scores":
            return _cmd_export_scores(args)
        if args.command == "evaluate":
            return _cmd_evaluate(args)
        if args.command == "summarize-run":
            return _cmd_summarize_run(args.run_root)
        if args.command == "hash-json":
            _print({"sha256": canonical_json_sha256(load_strict_json(args.path))})
            return 0
    except (ContractError, IntegrityError, OSError) as error:
        _print({"status": "FAIL", "error": str(error)})
        return 2
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
