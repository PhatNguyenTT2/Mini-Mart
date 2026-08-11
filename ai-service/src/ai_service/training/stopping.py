"""Strict Early-stopping controller and catastrophic failure detector."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from ai_service.contracts import CheckpointAction, TerminalAction


@dataclass(frozen=True)
class EarlyStoppingState:
    highest_gauc: float
    selected_epoch: int
    selected_gauc: float
    selected_ndcg: float
    selected_hr: float
    patience_used: int


@dataclass(frozen=True)
class StoppingDecision:
    checkpoint_action: CheckpointAction
    terminal_action: TerminalAction
    reason: str
    patience_used: int
    best_epoch: int
    best_gauc: float
    best_ndcg: float
    best_hr: float


class EarlyStoppingController:
    def __init__(
        self,
        *,
        patience: int = 4,
        min_delta: float = 1e-4,
        minimum_gauc: float = 0.50,
        max_wall_minutes: int = 90,
    ) -> None:
        if patience < 1 or min_delta < 0 or minimum_gauc < 0.5 or max_wall_minutes < 1:
            raise ValueError("invalid early-stopping controller limits")
        self.patience = patience
        self.min_delta = min_delta
        self.minimum_gauc = minimum_gauc
        self.max_wall_minutes = max_wall_minutes
        self.highest_gauc = -float("inf")
        self.selected_gauc = -float("inf")
        self.selected_ndcg = -float("inf")
        self.selected_hr = -float("inf")
        self.selected_epoch = 0
        self.patience_used = 0

    @property
    def state(self) -> EarlyStoppingState:
        return EarlyStoppingState(
            highest_gauc=self.highest_gauc,
            selected_epoch=self.selected_epoch,
            selected_gauc=self.selected_gauc,
            selected_ndcg=self.selected_ndcg,
            selected_hr=self.selected_hr,
            patience_used=self.patience_used,
        )

    def state_dict(self) -> dict[str, object]:
        return {
            "highest_gauc": self.highest_gauc,
            "selected_epoch": self.selected_epoch,
            "selected_gauc": self.selected_gauc,
            "selected_ndcg": self.selected_ndcg,
            "selected_hr": self.selected_hr,
            "patience_used": self.patience_used,
        }

    def load_state_dict(self, state: Mapping[str, object]) -> None:
        required = {
            "highest_gauc",
            "selected_epoch",
            "selected_gauc",
            "selected_ndcg",
            "selected_hr",
            "patience_used",
        }
        if set(state) != required:
            raise ValueError("early-stopping state fields do not match")
        values = {name: state[name] for name in required}
        floats = ("highest_gauc", "selected_gauc", "selected_ndcg", "selected_hr")
        if any(
            not isinstance(values[name], (int, float)) or isinstance(values[name], bool)
            for name in floats
        ):
            raise ValueError("early-stopping metric state must be numeric")
        if any(
            not math.isfinite(float(cast(float, values[name])))
            for name in floats
            if float(cast(float, values[name])) != -float("inf")
        ):
            raise ValueError("early-stopping metric state must be finite")
        self.highest_gauc = float(cast(float, values["highest_gauc"]))
        selected_epoch_value = values["selected_epoch"]
        patience_value = values["patience_used"]
        if (
            not isinstance(selected_epoch_value, int)
            or isinstance(selected_epoch_value, bool)
            or not isinstance(patience_value, int)
            or isinstance(patience_value, bool)
        ):
            raise ValueError("early-stopping counters must be integers")
        self.selected_epoch = selected_epoch_value
        self.selected_gauc = float(cast(float, values["selected_gauc"]))
        self.selected_ndcg = float(cast(float, values["selected_ndcg"]))
        self.selected_hr = float(cast(float, values["selected_hr"]))
        self.patience_used = patience_value
        if self.selected_epoch < 0 or self.patience_used < 0:
            raise ValueError("early-stopping counters cannot be negative")
        initial = self.selected_epoch == 0
        if initial and (
            self.highest_gauc != -float("inf")
            or self.selected_gauc != -float("inf")
            or self.selected_ndcg != -float("inf")
            or self.selected_hr != -float("inf")
            or self.patience_used != 0
        ):
            raise ValueError("selected_epoch zero is only valid for the initial state")
        if not initial and (
            not math.isfinite(self.highest_gauc)
            or not math.isfinite(self.selected_gauc)
            or not math.isfinite(self.selected_ndcg)
            or not math.isfinite(self.selected_hr)
            or self.highest_gauc < self.selected_gauc
        ):
            raise ValueError("selected early-stopping state is inconsistent")

    def check_wall_time(
        self, *, start_time: datetime, current_time: datetime
    ) -> StoppingDecision | None:
        """Return an interruption decision without mutating metric state."""
        elapsed_minutes = (current_time - start_time).total_seconds() / 60.0
        if elapsed_minutes <= self.max_wall_minutes:
            return None
        return StoppingDecision(
            checkpoint_action=CheckpointAction.NONE,
            terminal_action=TerminalAction.INTERRUPTED,
            reason=(
                f"wall time limit exceeded ({elapsed_minutes:.1f} > {self.max_wall_minutes} min)"
            ),
            patience_used=self.patience_used,
            best_epoch=self.selected_epoch,
            best_gauc=self.selected_gauc,
            best_ndcg=self.selected_ndcg,
            best_hr=self.selected_hr,
        )

    def evaluate(
        self,
        epoch: int,
        gauc: float,
        ndcg: float,
        hr: float,
        *,
        start_time: datetime,
        current_time: datetime,
        non_finite_reason: str | None = None,
        checkpoint_eligible: bool = True,
        eligibility_reason: str = "",
    ) -> StoppingDecision:
        if non_finite_reason or not all(math.isfinite(value) for value in (gauc, ndcg, hr)):
            detail = non_finite_reason or "validation metrics contain NaN or Inf"
            return StoppingDecision(
                checkpoint_action=CheckpointAction.NONE,
                terminal_action=TerminalAction.FAILED,
                reason=f"catastrophic non-finite signal: {detail}",
                patience_used=self.patience_used,
                best_epoch=self.selected_epoch,
                best_gauc=self.selected_gauc,
                best_ndcg=self.selected_ndcg,
                best_hr=self.selected_hr,
            )

        if gauc < self.minimum_gauc:
            return StoppingDecision(
                checkpoint_action=CheckpointAction.NONE,
                terminal_action=TerminalAction.FAILED,
                reason=(
                    f"catastrophic kill-switch: val_gauc ({gauc}) below minimum "
                    f"threshold ({self.minimum_gauc})"
                ),
                patience_used=self.patience_used,
                best_epoch=self.selected_epoch,
                best_gauc=self.selected_gauc,
                best_ndcg=self.selected_ndcg,
                best_hr=self.selected_hr,
            )

        wall_decision = self.check_wall_time(start_time=start_time, current_time=current_time)
        if wall_decision is not None:
            return wall_decision

        if gauc > self.highest_gauc + self.min_delta:
            self.highest_gauc = gauc
            if checkpoint_eligible:
                self.selected_gauc = gauc
                self.selected_ndcg = ndcg
                self.selected_hr = hr
                self.selected_epoch = epoch
                self.patience_used = 0
            else:
                self.patience_used += 1
            terminal_action = (
                TerminalAction.STOP_PLATEAU
                if not checkpoint_eligible and self.patience_used >= self.patience
                else TerminalAction.CONTINUE
            )
            return StoppingDecision(
                checkpoint_action=(
                    CheckpointAction.SAVE_BEST if checkpoint_eligible else CheckpointAction.NONE
                ),
                terminal_action=terminal_action,
                reason=(
                    "val_gauc improved to "
                    f"{gauc:.4f} but checkpoint is ineligible: {eligibility_reason}"
                    if not checkpoint_eligible
                    else f"val_gauc improved to {gauc:.4f}"
                ),
                patience_used=self.patience_used,
                best_epoch=epoch,
                best_gauc=gauc,
                best_ndcg=ndcg,
                best_hr=hr,
            )

        # No significant GAUC improvement -> increment patience
        self.patience_used += 1
        is_tied = abs(gauc - self.highest_gauc) <= self.min_delta
        checkpoint_action = CheckpointAction.NONE

        if (
            checkpoint_eligible
            and is_tied
            and (
                ndcg > self.selected_ndcg or (ndcg == self.selected_ndcg and hr > self.selected_hr)
            )
        ):
            self.selected_gauc = gauc
            self.selected_ndcg = ndcg
            self.selected_hr = hr
            self.selected_epoch = epoch
            checkpoint_action = CheckpointAction.SAVE_BEST_TIE

        terminal_action = (
            TerminalAction.STOP_PLATEAU
            if self.patience_used >= self.patience
            else TerminalAction.CONTINUE
        )
        reason = (
            f"early stopping plateau reached ({self.patience_used}/{self.patience} epochs)"
            if terminal_action is TerminalAction.STOP_PLATEAU
            else f"val_gauc ({gauc:.4f}) did not exceed best ({self.highest_gauc:.4f})"
        )

        return StoppingDecision(
            checkpoint_action=checkpoint_action,
            terminal_action=terminal_action,
            reason=reason,
            patience_used=self.patience_used,
            best_epoch=self.selected_epoch,
            best_gauc=self.selected_gauc,
            best_ndcg=self.selected_ndcg,
            best_hr=self.selected_hr,
        )

    def evaluate_epoch(
        self,
        *,
        epoch: int,
        gauc: float,
        ndcg: float,
        hr: float,
        start_time: datetime,
        current_time: datetime,
        non_finite_reason: str | None = None,
    ) -> StoppingDecision:
        return self.evaluate(
            epoch,
            gauc,
            ndcg,
            hr,
            start_time=start_time,
            current_time=current_time,
            non_finite_reason=non_finite_reason,
        )
