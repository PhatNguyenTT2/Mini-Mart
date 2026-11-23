"""Stages 04 -> 05 -> 06 --open -> 07 -> 08 on a tiny synthetic fixture, on CPU."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("recbole")

from tests.pipeline_fixture import build

PIPELINE = Path(__file__).resolve().parents[1] / "pipeline"


def stage(config: Path, script: str, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    return subprocess.run(
        [sys.executable, script, "--config", str(config), *extra],
        cwd=PIPELINE,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


def ok(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-4000:]
    return result.stdout


@pytest.mark.integration
def test_pipeline_end_to_end(tmp_path: Path) -> None:
    config = build(tmp_path)
    work = tmp_path / "work"

    ok(stage(config, "04_train_validate.py"))
    ok(stage(config, "05_freeze.py"))
    freeze = json.loads((work / "freeze.json").read_text(encoding="utf-8"))
    assert freeze["test_rows_used"] == 0 and freeze["cohort"]["pass"]
    assert "dry run ok" in ok(stage(config, "06_score_test.py", "--dry-run"))

    sealed = stage(config, "06_score_test.py", "--open")
    assert sealed.returncode != 0 and "sealed" in (sealed.stdout + sealed.stderr)
    (work / "open_authorized.json").write_text('{"by": "test"}', encoding="utf-8")
    ok(stage(config, "06_score_test.py", "--open"))
    again = stage(config, "06_score_test.py", "--open")
    assert again.returncode != 0 and "only once" in (again.stdout + again.stderr)

    ok(stage(config, "07_group_analysis.py", "--transition-users", "20"))
    ok(stage(config, "08_verify_numbers.py"))

    report = json.loads((work / "test/test_results.json").read_text(encoding="utf-8"))
    assert report["users"] > 0 and "ItemKNN|NDCG@10" in report["contrasts"]
    groups = json.loads((work / "test/results_groups.json").read_text(encoding="utf-8"))
    assert groups["raw_rebuild"]["eligible_users"] == report["cohort"]["eligible_users"]
    final = json.loads((work / "test/results_final.json").read_text(encoding="utf-8"))
    assert max(final["verification_worst"].values()) < 1e-9
