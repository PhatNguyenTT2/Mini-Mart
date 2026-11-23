"""Determinism settings and a RecBole epoch trainer for the reference baselines."""

from __future__ import annotations

import logging
import os
import random
from typing import Any

import numpy as np
import torch


def deterministic(seed: int) -> None:
    """Seed every generator and force deterministic kernels."""
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_num_threads(4)


def recbole_epoch_trainer(config: Any, model: Any) -> Any:
    """A RecBole ``Trainer`` used only for ``_train_epoch``.

    Evaluation runs through the shared full-catalog evaluator, so RecBole's own fit, evaluate and
    checkpoint routes are disabled. Requires the optional ``recbole`` dependency.
    """
    from recbole.trainer import Trainer  # type: ignore[import-untyped]

    class EpochTrainer(Trainer):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(config, model)
            self.logger = logging.getLogger("hybrid_recsys.recbole")

        def fit(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("use _train_epoch and the shared evaluator")

        def evaluate(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("use the shared evaluator")

        def _save_checkpoint(self, *args: Any, **kwargs: Any) -> Any:
            return None

    return EpochTrainer()
