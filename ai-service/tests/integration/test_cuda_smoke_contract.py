from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from ai_service.cli import main


@pytest.mark.gpu
def test_cuda_smoke_publishes_only_training_checkpoints(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise the guarded synthetic CUDA path without touching production roots."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    repository_root = Path(__file__).parents[2]
    source_config = repository_root / "configs" / "smoke" / "v5.toml"
    artifact_root = (tmp_path / "artifacts").resolve()
    config_text = source_config.read_text(encoding="utf-8").replace(
        'artifact_root = "artifacts/smoke-v5"',
        f'artifact_root = "{artifact_root.as_posix()}"',
    )
    config_path = tmp_path / "v5.toml"
    config_path.write_text(config_text, encoding="utf-8")
    run_id = "smoke-v5-test"

    assert (
        main(
            [
                "run-all",
                "--config",
                str(config_path),
                "--source",
                "synthetic",
                "--embedding-source",
                "mock",
                "--run-id",
                run_id,
                "--seed",
                "42",
                "--device",
                "cuda",
            ]
        )
        == 0
    )

    state = json.loads(capsys.readouterr().out)
    run_dir = artifact_root / "runs" / run_id
    assert state["model_schema_version"] == "5.0.0"
    assert state["training_variant"] == "deep_only"
    assert (run_dir / "checkpoints" / "best.pt").is_file()
    assert (run_dir / "checkpoints" / "last.pt").is_file()
    assert not (run_dir / "evaluation").exists()
    assert not (artifact_root / "releases").exists()
    assert not state["validation_gate_passed"]
    assert not state["test_gate_passed"]
    assert state["bundle_path"] is None
