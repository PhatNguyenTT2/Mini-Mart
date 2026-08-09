"""Unit tests for trainer.py module."""

import torch
import pytest
from torch.utils.data import DataLoader, Dataset
from config import get_settings
from models.two_tower_wide_deep import HybridTwoTowerModel
from training.trainer import Trainer
from data.dataset import TrainingBatch


class DummyDataset(Dataset):
    """Dummy Dataset for testing Trainer lifecycle."""

    def __init__(self):
        self.snapshot = type("Snapshot", (), {})()
        self.snapshot.snapshot_dir = Path("./") if False else None  # type: ignore

    def __len__(self):
        return 10

    def __getitem__(self, idx):
        return idx


def dummy_collator(batch):
    B = len(batch)
    return TrainingBatch(
        user_idx=torch.randint(0, 5000, (B,)),
        persona_idx=torch.randint(0, 8, (B,)),
        candidate_item_idx=torch.randint(0, 5200, (B, 5)),
        context_item_idx=torch.zeros(B, dtype=torch.long),
        log_lift=torch.zeros(B, 5, 1),
        labels=torch.tensor([[1.0, 0.0, 0.0, 0.0, 0.0]] * B),
        sample_weight=torch.ones(B),
    )


def test_trainer_checkpoint_saving(tmp_path):
    settings = get_settings()
    model = HybridTwoTowerModel(settings)
    trainer = Trainer(model, settings, run_dir=tmp_path)

    trainer.save_checkpoint(tmp_path / "best.pt", epoch=1, val_gauc=0.85)

    assert (tmp_path / "best.pt").exists()
    checkpoint = torch.load(tmp_path / "best.pt")
    assert checkpoint["epoch"] == 1
    assert checkpoint["val_gauc"] == 0.85
    assert "model_state" in checkpoint
    assert "optimizer_state" in checkpoint
