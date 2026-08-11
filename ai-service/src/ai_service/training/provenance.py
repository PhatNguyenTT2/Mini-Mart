"""Fail-closed source provenance for training lifecycle records."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

from ai_service.errors import ConfigurationError

_GIT_SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def is_git_commit_sha(value: object) -> TypeGuard[str]:
    """Return whether ``value`` is a lowercase Git SHA-1 or SHA-256."""

    return isinstance(value, str) and _GIT_SHA_PATTERN.fullmatch(value) is not None


@dataclass(frozen=True)
class SourceRevision:
    """The source revision used to create a training run."""

    commit_sha: str
    upstream_ref: str | None

    def __post_init__(self) -> None:
        if not is_git_commit_sha(self.commit_sha):
            raise ConfigurationError("repository HEAD is not a valid Git commit SHA")


def _git_output(arguments: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=_REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        command = "git " + " ".join(arguments)
        raise ConfigurationError(f"repository provenance command failed: {command}") from error
    return result.stdout.strip()


def resolve_source_revision() -> SourceRevision:
    """Resolve a valid HEAD for diagnostic/smoke runs."""

    commit_sha = _git_output(("rev-parse", "HEAD"))
    if not is_git_commit_sha(commit_sha):
        raise ConfigurationError("repository HEAD is not a valid Git commit SHA")
    return SourceRevision(commit_sha=commit_sha, upstream_ref=None)


def require_frozen_source_revision() -> SourceRevision:
    """Resolve HEAD only when the worktree is clean and pushed upstream."""

    status = _git_output(("status", "--porcelain", "--untracked-files=normal"))
    if status:
        raise ConfigurationError("production training requires a clean Git worktree")
    try:
        upstream_ref = _git_output(("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"))
        upstream_commit = _git_output(("rev-parse", "@{u}"))
    except ConfigurationError as error:
        raise ConfigurationError(
            "production training requires a pushed branch with a configured upstream"
        ) from error
    revision = resolve_source_revision()
    if not is_git_commit_sha(upstream_commit) or upstream_commit != revision.commit_sha:
        raise ConfigurationError(
            f"production branch {upstream_ref!r} is not synchronized with HEAD"
        )
    return SourceRevision(commit_sha=revision.commit_sha, upstream_ref=upstream_ref)
