"""Command line interface with command-specific argument parsers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ai_service.contracts import DataSourceKind, EmbeddingSource, SplitName, TrainingVariant
from ai_service.training.pipeline import execute_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Data/Snapshot/Feature management commands
    for command in ("audit-data", "probe-data", "snapshot", "features", "rules"):
        child = subparsers.add_parser(command)
        child.add_argument("--store-id", type=int, default=1)
        child.add_argument("--snapshot-id")
        child.add_argument("--run-id")
        child.add_argument("--bundle-id")
        child.add_argument(
            "--source", choices=[kind.value for kind in DataSourceKind], default="postgres"
        )
        child.add_argument(
            "--embedding-source",
            choices=[kind.value for kind in EmbeddingSource],
            default="real",
        )
        child.add_argument("--seed", type=int, default=42)
        child.add_argument("--benchmark-run-id")
        child.add_argument("--benchmark-spec", type=Path)
        child.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
        child.add_argument("--config", type=Path)

    smoke_cmd = subparsers.add_parser(
        "run-all", help="run one explicit synthetic/mock Deep-only smoke epoch"
    )
    smoke_cmd.add_argument("--run-id", required=True)
    smoke_cmd.add_argument("--config", type=Path, required=True)
    smoke_cmd.add_argument("--source", choices=(DataSourceKind.SYNTHETIC.value,), required=True)
    smoke_cmd.add_argument(
        "--embedding-source", choices=(EmbeddingSource.MOCK.value,), required=True
    )
    smoke_cmd.add_argument("--seed", type=int, default=42)
    smoke_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    smoke_cmd.add_argument("--store-id", type=int, default=1)

    # 2. train command parser
    train_cmd = subparsers.add_parser("train")
    train_cmd.add_argument("--run-id", required=True)
    train_cmd.add_argument("--variant", choices=[v.value for v in TrainingVariant], required=True)
    train_cmd.add_argument("--config", type=Path, required=True)
    train_cmd.add_argument("--snapshot-id")
    train_cmd.add_argument("--seed", type=int, default=42)
    train_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    train_cmd.add_argument("--resume", action="store_true")
    train_cmd.add_argument("--r3-selection-report", type=Path)
    train_cmd.add_argument("--r4-promotion-report", type=Path)
    train_cmd.add_argument("--store-id", type=int, default=1)
    train_cmd.add_argument(
        "--source", choices=[kind.value for kind in DataSourceKind], default="postgres"
    )
    train_cmd.add_argument(
        "--embedding-source",
        choices=[kind.value for kind in EmbeddingSource],
        default="real",
    )

    # 3. evaluate command parser
    eval_cmd = subparsers.add_parser("evaluate")
    eval_cmd.add_argument(
        "--split", choices=[s.value for s in SplitName if s != SplitName.TRAIN], required=True
    )
    eval_cmd.add_argument("--hybrid-run-id", required=True)
    eval_cmd.add_argument("--deep-run-id", required=True)
    eval_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")

    preflight_cmd = subparsers.add_parser(
        "preflight-r3", help="run read-only v5 R3 readiness checks"
    )
    preflight_cmd.add_argument("--config", type=Path, required=True)
    preflight_cmd.add_argument("--snapshot-id", required=True)
    preflight_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    preflight_cmd.add_argument("--store-id", type=int, default=1)

    # 4. release-gate command parser
    gate_cmd = subparsers.add_parser("release-gate")
    gate_cmd.add_argument(
        "--split", choices=[s.value for s in SplitName if s != SplitName.TRAIN], required=True
    )
    gate_cmd.add_argument("--hybrid-run-ids", nargs=3, required=True)
    gate_cmd.add_argument("--deep-run-ids", nargs=3, required=True)

    diagnostic_cmd = subparsers.add_parser("compare-deep-ablations")
    diagnostic_cmd.add_argument("--control-run-id", required=True)
    diagnostic_cmd.add_argument("--candidate-run-ids", nargs=3, required=True)
    diagnostic_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")

    r3_cmd = subparsers.add_parser(
        "diagnose-r3", help="replay a paired R3 validation failure without mutating runs"
    )
    r3_cmd.add_argument("--hybrid-run-id", required=True)
    r3_cmd.add_argument("--deep-run-id", required=True)
    r3_cmd.add_argument("--split", choices=(SplitName.VAL.value,), default=SplitName.VAL.value)
    r3_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")

    promotion_cmd = subparsers.add_parser(
        "promote-r4", help="publish the immutable R4-to-production hand-off receipt"
    )
    promotion_cmd.add_argument("--selection-report", type=Path, required=True)
    promotion_cmd.add_argument("--selected-deep-run-id", required=True)
    promotion_cmd.add_argument("--selected-deep-checkpoint-sha256", required=True)
    promotion_cmd.add_argument("--h3b-hybrid-run-id", required=True)
    promotion_cmd.add_argument("--h3b-hybrid-checkpoint-sha256", required=True)
    promotion_cmd.add_argument("--h3b-victory-matrix-sha256", required=True)
    promotion_cmd.add_argument("--lineage-json", type=Path, required=True)
    promotion_cmd.add_argument("--deep-config", type=Path, required=True)
    promotion_cmd.add_argument("--hybrid-config", type=Path, required=True)
    promotion_cmd.add_argument("--diagnostic-git-commit", required=True)
    promotion_cmd.add_argument("--production-git-commit", required=True)
    promotion_cmd.add_argument("--feature-selection-json", type=Path, required=True)
    promotion_cmd.add_argument("--objective-settings-json", type=Path, required=True)
    promotion_cmd.add_argument("--output", type=Path, required=True)

    # 5. export command parser
    export_cmd = subparsers.add_parser("export")
    export_cmd.add_argument("--run-id", required=True)
    export_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")

    # 6. verify-bundle command parser
    bundle_cmd = subparsers.add_parser("verify-bundle")
    bundle_ids = bundle_cmd.add_mutually_exclusive_group()
    bundle_ids.add_argument("--bundle-id")
    bundle_ids.add_argument("--run-id")
    bundle_cmd.add_argument("--device", choices=("cpu", "cuda"), default="cuda")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    execute_command(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
