"""Strict Early-stopping controller and catastrophic failure detector."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class StoppingAction(StrEnum):
    CONTINUE = "continue"
    SAVE_BEST = "save_best"
    SAVE_BEST_TIE = "save_best_tie"
    STOP_PLATEAU = "stop_plateau"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class EpochObservation:
    epoch: int
    gauc: float
    ndcg: float
    hr: float
    elapsed_seconds: float
    non_finite_reason: str | None = None


@dataclass(frozen=True)
class StoppingDecision:
    action: StoppingAction
    reason: str
    best_epoch: int
    best_gauc: float
    best_ndcg: float
    best_hr: float
    patience_count: int


class EarlyStoppingController:
    def __init__(
        self,
        *,
        patience: int = 4,
        min_delta: float = 1e-4,
        minimum_gauc: float = 0.50,
    ) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self.minimum_gauc = minimum_gauc
        self.best_gauc = -float("inf")
        self.best_ndcg = -float("inf")
        self.best_hr = -float("inf")
        self.best_epoch = 0
        self.patience_count = 0

    def observe(self, obs: EpochObservation) -> StoppingDecision:
        if obs.non_finite_reason:
            return StoppingDecision(
                action=StoppingAction.FAILED,
                reason=f"catastrophic non-finite signal: {obs.non_finite_reason}",
                best_epoch=self.best_epoch,
                best_gauc=self.best_gauc,
                best_ndcg=self.best_ndcg,
                best_hr=self.best_hr,
                patience_count=self.patience_count,
            )

        if not math.isfinite(obs.gauc) or obs.gauc < self.minimum_gauc:
            return StoppingDecision(
                action=StoppingAction.FAILED,
                reason=f"catastrophic kill-switch: val_gauc ({obs.gauc:.4f}) below minimum threshold ({self.minimum_gauc:.2f})",
                best_epoch=self.best_epoch,
                best_gauc=self.best_gauc,
                best_ndcg=self.best_ndcg,
                best_hr=self.best_hr,
                patience_count=self.patience_count,
            )

        if obs.gauc > self.best_gauc + self.min_delta:
            self.best_gauc = obs.gauc
            self.best_ndcg = obs.ndcg
            self.best_hr = obs.hr
            self.best_epoch = obs.epoch
            self.patience_count = 0
            return StoppingDecision(
                action=StoppingAction.SAVE_BEST,
                reason=f"val_gauc improved to {obs.gauc:.4f}",
                best_epoch=self.best_epoch,
                best_gauc=self.best_gauc,
                best_ndcg=self.best_ndcg,
                best_hr=self.best_hr,
                patience_count=0,
            )

        if abs(obs.gauc - self.best_gauc) <= self.min_delta:
            self.patience_count += 1
            if obs.ndcg > self.best_ndcg or (obs.ndcg == self.best_ndcg and obs.hr > self.best_hr):
                self.best_gauc = obs.gauc
                self.best_ndcg = obs.ndcg
                self.best_hr = obs.hr
                self.best_epoch = obs.epoch
                action = StoppingAction.SAVE_BEST_TIE
                reason = f"val_gauc tied, improved NDCG ({obs.ndcg:.4f})/HR ({obs.hr:.4f})"
            else:
                action = StoppingAction.CONTINUE
                reason = f"val_gauc within delta ({obs.gauc:.4f})"

            if self.patience_count >= self.patience:
                return StoppingDecision(
                    action=StoppingAction.STOP_PLATEAU,
                    reason=f"early stopping plateau reached ({self.patience_count}/{self.patience} epochs without GAUC improvement)",
                    best_epoch=self.best_epoch,
                    best_gauc=self.best_gauc,
                    best_ndcg=self.best_ndcg,
                    best_hr=self.best_hr,
                    patience_count=self.patience_count,
                )

            return StoppingDecision(
                action=action,
                reason=reason,
                best_epoch=self.best_epoch,
                best_gauc=self.best_gauc,
                best_ndcg=self.best_ndcg,
                best_hr=self.best_hr,
                patience_count=self.patience_count,
            )

        self.patience_count += 1
        if self.patience_count >= self.patience:
            return StoppingDecision(
                action=StoppingAction.STOP_PLATEAU,
                reason=f"early stopping plateau reached ({self.patience_count}/{self.patience} epochs without GAUC improvement)",
                best_epoch=self.best_epoch,
                best_gauc=self.best_gauc,
                best_ndcg=self.best_ndcg,
                best_hr=self.best_hr,
                patience_count=self.patience_count,
            )

        return StoppingDecision(
            action=StoppingAction.CONTINUE,
            reason=f"val_gauc decreased to {obs.gauc:.4f}",
            best_epoch=self.best_epoch,
            best_gauc=self.best_gauc,
            best_ndcg=self.best_ndcg,
            best_hr=self.best_hr,
            patience_count=self.patience_count,
        )
