from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader

from ai_service.contracts import CheckpointAction, SplitName, TerminalAction, TrainingVariant
from ai_service.data.dataset import HybridImplicitDataset, collate_candidate_groups
from ai_service.data.rules import RuleStore
from ai_service.errors import (
    CatastrophicTrainingError,
    ModelTrainingError,
    TrainingInterruptedError,
)
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.stopping import EarlyStoppingController, StoppingDecision
from ai_service.training.trainer import Trainer
from tests.support.trainer_fixtures import RecordingValidationEvaluator
from tests.support.v5_factories import make_settings, make_snapshot, make_training_validation_pass

LINEAGE = {"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64}


class _CacheSink:
    def __init__(self) -> None:
        self.updates = 0

    def update_model_hard_cache(self, _cache: np.ndarray) -> None:
        self.updates += 1


class _LoaderProxy:
    def __init__(self, loader: DataLoader[dict[str, object]], sampler: _CacheSink) -> None:
        self._loader = loader
        self.sampler = sampler

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._loader)

    def __len__(self) -> int:
        return len(self._loader)


def _fixture(
    root: Path,
    *,
    max_epochs: int = 1,
    variant: TrainingVariant = TrainingVariant.DEEP_ONLY,
) -> tuple[object, object, object, np.ndarray, _LoaderProxy]:
    settings = make_settings(root, variant=variant)
    settings.train.objective = "legacy_bce"
    settings.train.max_epochs = max_epochs
    snapshot = make_snapshot(root)
    dataset = HybridImplicitDataset(
        snapshot,
        RuleStore(snapshot.manifest.num_items, [(0, 1, 3.0)]),
        split=SplitName.TRAIN,
        negative_ratio=1,
    )
    loader = DataLoader(dataset, batch_size=2, collate_fn=collate_candidate_groups)
    sink = _CacheSink()
    return (
        settings,
        snapshot,
        dataset,
        np.eye(snapshot.manifest.num_items, 8, dtype=np.float32),
        _LoaderProxy(loader, sink),
    )


def test_fit_resume_matches_uninterrupted_run(tmp_path: Path) -> None:
    settings, snapshot, _dataset, embeddings, loader = _fixture(
        tmp_path / "reference", max_epochs=3
    )
    passes = tuple(
        make_training_validation_pass(snapshot, gauc=0.75 + epoch * 0.01) for epoch in range(3)
    )
    baseline = HybridTwoTowerModel(settings)
    initial_state = {name: value.detach().clone() for name, value in baseline.state_dict().items()}
    reference_eval = RecordingValidationEvaluator(passes)
    reference = Trainer(
        baseline, settings=settings, run_dir=tmp_path / "reference" / "run", device="cpu"
    ).fit(loader, snapshot, embeddings, reference_eval, LINEAGE)

    partial_settings, partial_snapshot, _dataset, partial_embeddings, partial_loader = _fixture(
        tmp_path / "partial", max_epochs=3
    )
    interrupted_model = HybridTwoTowerModel(partial_settings)
    interrupted_model.load_state_dict(initial_state)

    class InterruptAfterOne(RecordingValidationEvaluator):
        def evaluate_training_epoch(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
            if self.calls >= 1:
                raise TrainingInterruptedError("diagnostic interruption")
            return super().evaluate_training_epoch(*args, **kwargs)

    interrupting = InterruptAfterOne((passes[0],))
    interrupted_trainer = Trainer(
        interrupted_model,
        settings=partial_settings,
        run_dir=tmp_path / "partial" / "run",
        device="cpu",
    )
    with pytest.raises(TrainingInterruptedError, match="diagnostic interruption"):
        interrupted_trainer.fit(
            partial_loader, partial_snapshot, partial_embeddings, interrupting, LINEAGE
        )

    resume_model = HybridTwoTowerModel(partial_settings)
    resume_eval = RecordingValidationEvaluator((passes[1], passes[2]))
    resumed = Trainer(
        resume_model,
        settings=partial_settings,
        run_dir=tmp_path / "partial" / "run",
        device="cpu",
    ).fit(
        partial_loader,
        partial_snapshot,
        partial_embeddings,
        resume_eval,
        LINEAGE,
        resume_from=tmp_path / "partial" / "run" / "checkpoints" / "last.pt",
    )

    assert resumed.best_epoch == reference.best_epoch
    assert resumed.best_gauc == pytest.approx(reference.best_gauc)
    assert resumed.best_ndcg_at_k == pytest.approx(reference.best_ndcg_at_k)
    assert resumed.best_hr_at_k == pytest.approx(reference.best_hr_at_k)
    assert [row.epoch for row in resumed.history] == [row.epoch for row in reference.history]
    assert [row.global_step for row in resumed.history] == [
        row.global_step for row in reference.history
    ]


def test_fit_terminal_summary_completed_and_cache_count(tmp_path: Path) -> None:
    settings, snapshot, _dataset, embeddings, loader = _fixture(tmp_path, max_epochs=2)
    passes = tuple(make_training_validation_pass(snapshot) for _ in range(2))
    evaluator = RecordingValidationEvaluator(passes)
    result = Trainer(
        HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run", device="cpu"
    ).fit(loader, snapshot, embeddings, evaluator, LINEAGE)
    assert result.terminal_action is TerminalAction.COMPLETED
    assert evaluator.calls == 2
    assert loader.sampler.updates == 2
    summary = json.loads((tmp_path / "run" / "training" / "summary.json").read_text())
    assert summary["terminal_action"] == TerminalAction.COMPLETED.value
    assert summary["best_epoch"] == result.best_epoch
    assert all(row.model_hard_cache_updated for row in result.history)


def test_fit_deep_only_keeps_wide_byte_identical(tmp_path: Path) -> None:
    settings, snapshot, _dataset, embeddings, loader = _fixture(tmp_path, max_epochs=1)
    model = HybridTwoTowerModel(settings)
    before = {name: value.detach().clone() for name, value in model.wide_layer.state_dict().items()}
    result = Trainer(model, settings=settings, run_dir=tmp_path / "run", device="cpu").fit(
        loader,
        snapshot,
        embeddings,
        RecordingValidationEvaluator((make_training_validation_pass(snapshot),)),
        LINEAGE,
    )
    after = model.wide_layer.state_dict()
    assert all(torch.equal(before[name], after[name]) for name in before)
    assert result.history[0].wide_gradient_norm == 0.0


def test_fit_rejects_invalid_preflight_without_training(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path / "snapshot")
    trainer = Trainer(HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run")
    embeddings = np.zeros((snapshot.manifest.num_items, settings.model.sbert_dim), dtype=np.float32)
    with pytest.raises(ModelTrainingError, match="lineage"):
        trainer.fit([], snapshot, embeddings, object(), {})  # type: ignore[arg-type]
    with pytest.raises(ModelTrainingError, match="wrong shape"):
        trainer.fit([], snapshot, np.zeros((1, 8), dtype=np.float32), object(), LINEAGE)  # type: ignore[arg-type]


def test_fit_failed_validation_writes_terminal_summary(tmp_path: Path) -> None:
    settings, snapshot, _dataset, embeddings, loader = _fixture(tmp_path, max_epochs=1)
    bad = make_training_validation_pass(snapshot, gauc=0.49)
    trainer = Trainer(HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run")
    with pytest.raises(CatastrophicTrainingError, match="below minimum"):
        trainer.fit(loader, snapshot, embeddings, RecordingValidationEvaluator((bad,)), LINEAGE)
    summary = json.loads((tmp_path / "run" / "training" / "summary.json").read_text())
    assert summary["terminal_action"] == TerminalAction.FAILED.value
    assert "below minimum" in summary["terminal_reason"]
    assert not (tmp_path / "run" / "checkpoints" / "best.pt").exists()


def test_fit_interrupted_batch_writes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, snapshot, _dataset, embeddings, loader = _fixture(tmp_path, max_epochs=1)
    trainer = Trainer(HybridTwoTowerModel(settings), settings=settings, run_dir=tmp_path / "run")
    monkeypatch.setattr(
        EarlyStoppingController,
        "check_wall_time",
        lambda *_args, **_kwargs: StoppingDecision(
            checkpoint_action=CheckpointAction.NONE,
            terminal_action=TerminalAction.INTERRUPTED,
            reason="batch wall limit",
            patience_used=0,
            best_epoch=0,
            best_gauc=-float("inf"),
            best_ndcg=-float("inf"),
            best_hr=-float("inf"),
        ),
    )
    with pytest.raises(TrainingInterruptedError, match="batch wall limit"):
        trainer.fit(
            loader,
            snapshot,
            embeddings,
            RecordingValidationEvaluator((make_training_validation_pass(snapshot),)),
            LINEAGE,
        )
    summary = json.loads((tmp_path / "run" / "training" / "summary.json").read_text())
    assert summary["terminal_action"] == TerminalAction.INTERRUPTED.value
    assert summary["terminal_reason"] == "batch wall limit"
