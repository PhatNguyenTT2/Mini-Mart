"""Command line interface for the single production pipeline."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ai_service.contracts import DataSourceKind, EmbeddingSource
from ai_service.training.pipeline import execute_command

COMMANDS = (
    "audit-data",
    "probe-data",
    "snapshot",
    "features",
    "rules",
    "train",
    "evaluate",
    "export",
    "verify-bundle",
    "release-gate",
    "run-all",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        child = subparsers.add_parser(command)
        child.add_argument("--store-id", type=int, default=1)
        child.add_argument("--snapshot-id")
        child.add_argument("--run-id")
        child.add_argument("--run-ids", nargs=3)
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
        child.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
        child.add_argument("--config", type=Path)
        child.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    execute_command(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
