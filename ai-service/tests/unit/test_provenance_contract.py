from __future__ import annotations

from argparse import Namespace

import pytest

from ai_service.errors import ConfigurationError
from ai_service.training import provenance


@pytest.mark.parametrize("value", ["", "A" * 40, "0" * 39, "g" * 40, None])
def test_git_commit_sha_validation_rejects_invalid_values(value: object) -> None:
    assert not provenance.is_git_commit_sha(value)


@pytest.mark.parametrize("value", ["0" * 40, "a" * 64])
def test_git_commit_sha_validation_accepts_supported_values(value: str) -> None:
    assert provenance.is_git_commit_sha(value)
    assert provenance.SourceRevision(value, None).commit_sha == value


def test_resolve_source_revision_fails_closed_on_git_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provenance.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("git unavailable")),
    )
    with pytest.raises(ConfigurationError, match="provenance command failed"):
        provenance.resolve_source_revision()


@pytest.mark.parametrize("stdout", ["", "A" * 40, "not-a-sha"])
def test_resolve_source_revision_rejects_invalid_head(
    monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    monkeypatch.setattr(provenance.subprocess, "run", lambda *_a, **_k: Namespace(stdout=stdout))
    with pytest.raises(ConfigurationError, match="valid Git commit SHA"):
        provenance.resolve_source_revision()


def test_require_frozen_source_revision_checks_clean_pushed_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("status", "--porcelain", "--untracked-files=normal"): "",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main",
        ("rev-parse", "@{u}"): "0" * 40,
        ("rev-parse", "HEAD"): "0" * 40,
    }
    monkeypatch.setattr(provenance, "_git_output", lambda arguments: responses[tuple(arguments)])
    revision = provenance.require_frozen_source_revision()
    assert revision.commit_sha == "0" * 40
    assert revision.upstream_ref == "origin/main"

    monkeypatch.setattr(
        provenance,
        "_git_output",
        lambda arguments: (
            "dirty.py"
            if tuple(arguments) == ("status", "--porcelain", "--untracked-files=normal")
            else responses[tuple(arguments)]
        ),
    )
    with pytest.raises(ConfigurationError, match="clean Git worktree"):
        provenance.require_frozen_source_revision()


def test_require_frozen_source_revision_rejects_missing_or_mismatched_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("status", "--porcelain", "--untracked-files=normal"): "",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main",
        ("rev-parse", "@{u}"): "1" * 40,
        ("rev-parse", "HEAD"): "0" * 40,
    }
    monkeypatch.setattr(provenance, "_git_output", lambda arguments: responses[tuple(arguments)])
    with pytest.raises(ConfigurationError, match="not synchronized"):
        provenance.require_frozen_source_revision()

    monkeypatch.setattr(
        provenance,
        "_git_output",
        lambda arguments: (
            (_ for _ in ()).throw(ConfigurationError("no upstream"))
            if tuple(arguments) == ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            else responses[tuple(arguments)]
        ),
    )
    with pytest.raises(ConfigurationError, match="configured upstream"):
        provenance.require_frozen_source_revision()
