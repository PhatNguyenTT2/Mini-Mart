"""Fail-closed removal of generated benchmark outputs before the v5 seed.

The command never touches source/configuration and refuses an artifact root
outside the repository.  It is intentionally separate from training so the
operator can review the read-only plan before confirming deletion.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from ai_service.errors import ConfigurationError

_OUTPUT_DIRS = (
    "_archive",
    "snapshots",
    "features",
    "rules",
    "runs",
    "diagnostics",
    "releases",
    "bundles",
)
_CONFIRMATION = "PURGE_ALL_PRE_V5_OUTPUTS"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def plan_purge(artifact_root: Path) -> dict[str, object]:
    if artifact_root.is_symlink() or _is_reparse_point(artifact_root):
        raise ConfigurationError("purge root cannot be a symlink or junction")
    root = artifact_root.resolve(strict=False)
    repository = _repository_root()
    if root.parent != repository or root.name != "artifacts" or not root.is_dir():
        raise ConfigurationError(
            "purge root must be the repository-local ai-service/artifacts directory"
        )
    if _is_reparse_point(root):
        raise ConfigurationError("purge root cannot be a symlink or junction")
    unexpected = sorted(child.name for child in root.iterdir() if child.name not in _OUTPUT_DIRS)
    if unexpected:
        raise ConfigurationError(f"artifact root has unexpected children: {unexpected}")
    entries = {
        name: sorted(str(path.relative_to(root)) for path in (root / name).glob("*"))
        for name in _OUTPUT_DIRS
    }
    return {
        "artifact_root": str(root),
        "entries": entries,
        "entry_count": sum(len(values) for values in entries.values()),
    }


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & 0x400)


def _validate_child(root: Path, child: Path) -> None:
    resolved = child.resolve(strict=False)
    if root not in resolved.parents:
        raise ConfigurationError(f"purge path escapes artifact root: {child}")
    if child.is_symlink() or _is_reparse_point(child):
        raise ConfigurationError(f"purge refuses symlink/junction: {child}")


def purge_benchmark_outputs(artifact_root: Path, *, confirmation: str) -> dict[str, object]:
    plan = plan_purge(artifact_root)
    if confirmation != _CONFIRMATION:
        raise ConfigurationError("exact purge confirmation token is required")
    root = Path(str(plan["artifact_root"]))
    removed: dict[str, int] = {}
    for name in _OUTPUT_DIRS:
        directory = root / name
        if directory.exists() and (directory.is_symlink() or _is_reparse_point(directory)):
            raise ConfigurationError(f"purge refuses symlink/junction: {directory}")
        children = list(directory.iterdir()) if directory.is_dir() else []
        for child in children:
            _validate_child(root, child)
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        if name == "_archive" and directory.exists():
            directory.rmdir()
        removed[name] = len(children)
    return {"status": "purged", "artifact_root": str(root), "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=_repository_root() / "artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    if args.dry_run:
        print(plan_purge(args.artifact_root))
        return 0
    print(purge_benchmark_outputs(args.artifact_root, confirmation=args.confirm or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
