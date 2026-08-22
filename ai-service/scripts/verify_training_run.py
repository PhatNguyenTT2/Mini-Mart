"""CLI adapter for the read-only training-run verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_service.contracts import TrainingVariant
from ai_service.training.run_verifier import verify_training_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--expected-variant", choices=[variant.value for variant in TrainingVariant], required=True
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
