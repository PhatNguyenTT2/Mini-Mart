from __future__ import annotations

from pathlib import Path

import pytest

from ai_service.errors import ConfigurationError
from scripts.purge_benchmark_outputs import plan_purge, purge_benchmark_outputs


def test_purge_plan_is_scoped_to_repo_artifact_root(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="repository-local"):
        plan_purge(tmp_path)


def test_purge_requires_exact_confirmation() -> None:
    root = Path(__file__).parents[2] / "artifacts"
    with pytest.raises(ConfigurationError, match="exact purge confirmation"):
        purge_benchmark_outputs(root, confirmation="yes")
