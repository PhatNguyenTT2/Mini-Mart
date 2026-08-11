from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support.v5_factories import make_settings, make_snapshot


@pytest.fixture
def v5_settings_factory(tmp_path: Path) -> Callable[..., object]:
    return lambda **kwargs: make_settings(tmp_path, **kwargs)


@pytest.fixture
def v5_snapshot_factory(tmp_path: Path) -> Callable[..., object]:
    return lambda **kwargs: make_snapshot(tmp_path, **kwargs)


@pytest.fixture
def v5_checkpoint_factory() -> None:
    """Reserved seam; checkpoint fixtures must call CheckpointManager.save."""

    return None


@pytest.fixture
def v5_evaluation_factory() -> None:
    """Reserved seam; evaluation fixtures must call the production publisher."""

    return None


@pytest.fixture
def v5_finalist_set_factory() -> None:
    """Reserved seam; finalist fixtures must use production manifests/writers."""

    return None


@pytest.fixture
def v5_bundle_factory() -> None:
    """Reserved seam; bundle fixtures must call BundlePublisher.publish."""

    return None


@pytest.fixture
def v5_trainer_factory() -> None:
    return None
