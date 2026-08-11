"""Fail-closed removal of generated benchmark outputs before the v5 seed.

The command never touches source/configuration and refuses an artifact root
outside the repository.  It is intentionally separate from training so the
operator can review the read-only plan before confirming deletion.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ai_service.errors import ConfigurationError

_OUTPUT_DIRS = ("runs", "snapshots", "features", "rules", "diagnostics", "releases", "bundles")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def plan_purge(artifact_root: Path) -> dict[str, object]:
    root = artifact_root.resolve()
    repository = _repository_root()
    if root.parent != repository or root.name != "artifacts":
        raise ConfigurationError(
            "purge root must be the repository-local ai-service/artifacts directory"
        )
    entries = {
        name: sorted(
            str(path.relative_to(root)) for path in (root / name).glob("*") if path.exists()
        )
        for name in _OUTPUT_DIRS
    }
    return {
        "artifact_root": str(root),
        "entries": entries,
        "entry_count": sum(len(values) for values in entries.values()),
    }


def purge_benchmark_outputs(artifact_root: Path, *, confirmation: str) -> dict[str, object]:
    plan = plan_purge(artifact_root)
    expected = "PURGE_AI_SERVICE_ARTIFACTS_V4_TO_V5"
    if confirmation != expected:
        raise ConfigurationError("exact purge confirmation token is required")
    root = Path(str(plan["artifact_root"]))
    removed: dict[str, int] = {}
    for name in _OUTPUT_DIRS:
        directory = root / name
        children = list(directory.glob("*")) if directory.is_dir() else []
        for child in children:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        removed[name] = len(children)
    return {"status": "purged", "artifact_root": str(root), "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    if args.plan:
        print(plan_purge(args.artifact_root))
        return 0
    print(purge_benchmark_outputs(args.artifact_root, confirmation=args.confirm or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
