from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from ai_service.errors import CatastrophicTrainingError, ModelTrainingError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.trainer import Trainer, _module_gradient_norm
from tests.support.v5_factories import make_settings, make_snapshot


def test_trainer_preflight_rejects_lineage_and_embedding_contracts(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    trainer = Trainer(
        HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run", device="cpu"
    )
    evaluator = object()
    with pytest.raises(ModelTrainingError, match="lineage"):
        trainer.fit(
            [],
            snapshot,
            np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32),
            evaluator,  # type: ignore[arg-type]
            {},
        )
    lineage = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}
    with pytest.raises(ModelTrainingError, match="wrong shape"):
        trainer.fit(
            [],
            snapshot,
            np.zeros((1, settings.model.sbert_dim), dtype=np.float32),
            evaluator,  # type: ignore[arg-type]
            lineage,
        )
    with pytest.raises(CatastrophicTrainingError, match="NaN"):
        trainer.fit(
            [],
            snapshot,
            np.full(
                (snapshot.manifest.num_items, settings.model.sbert_dim),
                np.nan,
                dtype=np.float32,
            ),
            evaluator,  # type: ignore[arg-type]
            lineage,
        )


def test_trainer_scheduler_and_gradient_norm_seams(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    trainer = Trainer(
        HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run", device="cpu"
    )
    scheduler = trainer._build_scheduler(steps_per_epoch=2)
    for _ in range(4):
        scheduler.step()
    assert scheduler.get_last_lr()[0] >= 0
    parameter = torch.nn.Parameter(torch.ones(2))
    module = torch.nn.Linear(2, 1)
    assert _module_gradient_norm(module) == 0.0
    (module(parameter).sum()).backward()
    assert _module_gradient_norm(module) > 0.0
