from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from ai_service.contracts import CheckpointAction, TerminalAction
from ai_service.training.stopping import EarlyStoppingController


def test_gauc_improvement_resets_patience() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    now = datetime.now(UTC)

    # Epoch 1: initial best
    decision1 = controller.evaluate(
        epoch=1, gauc=0.70, ndcg=0.30, hr=0.20, start_time=now, current_time=now
    )
    assert decision1.checkpoint_action is CheckpointAction.SAVE_BEST
    assert decision1.terminal_action is TerminalAction.CONTINUE
    assert decision1.patience_used == 0

    # Epoch 2: improvement by > 1e-4
    decision2 = controller.evaluate(
        epoch=2, gauc=0.72, ndcg=0.31, hr=0.21, start_time=now, current_time=now
    )
    assert decision2.checkpoint_action is CheckpointAction.SAVE_BEST
    assert decision2.terminal_action is TerminalAction.CONTINUE
    assert decision2.patience_used == 0
    assert decision2.best_epoch == 2


def test_plateau_after_patience() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    now = datetime.now(UTC)

    # Epoch 1: best
    controller.evaluate(epoch=1, gauc=0.70, ndcg=0.30, hr=0.20, start_time=now, current_time=now)

    # Epochs 2 to 4: no improvement
    for epoch in range(2, 5):
        decision = controller.evaluate(
            epoch=epoch, gauc=0.69, ndcg=0.29, hr=0.19, start_time=now, current_time=now
        )
        assert decision.terminal_action is TerminalAction.CONTINUE
        assert decision.patience_used == epoch - 1

    # Epoch 5: 4th epoch of no improvement -> STOP_PLATEAU
    decision5 = controller.evaluate(
        epoch=5, gauc=0.69, ndcg=0.29, hr=0.19, start_time=now, current_time=now
    )
    assert decision5.terminal_action is TerminalAction.STOP_PLATEAU
    assert decision5.patience_used == 4


def test_gauc_tie_ndcg_better_saves_no_reset() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    now = datetime.now(UTC)

    # Epoch 1: best
    controller.evaluate(epoch=1, gauc=0.70, ndcg=0.30, hr=0.20, start_time=now, current_time=now)

    # Epoch 2: GAUC tied, NDCG improved
    decision2 = controller.evaluate(
        epoch=2, gauc=0.70, ndcg=0.35, hr=0.20, start_time=now, current_time=now
    )
    assert decision2.checkpoint_action is CheckpointAction.SAVE_BEST_TIE
    assert decision2.terminal_action is TerminalAction.CONTINUE
    assert decision2.patience_used == 1
    assert decision2.best_epoch == 2


def test_catastrophic_gauc_below_050() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    now = datetime.now(UTC)

    decision = controller.evaluate(
        epoch=1, gauc=0.49, ndcg=0.30, hr=0.20, start_time=now, current_time=now
    )
    assert decision.terminal_action is TerminalAction.FAILED
    assert (
        "below minimum threshold" in decision.reason.lower()
        or "catastrophic" in decision.reason.lower()
        or "0.5" in decision.reason
    )


def test_catastrophic_nan_inf() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    now = datetime.now(UTC)

    decision_nan = controller.evaluate(
        epoch=1, gauc=math.nan, ndcg=0.30, hr=0.20, start_time=now, current_time=now
    )
    assert decision_nan.terminal_action is TerminalAction.FAILED

    decision_inf = controller.evaluate(
        epoch=1, gauc=math.inf, ndcg=0.30, hr=0.20, start_time=now, current_time=now
    )
    assert decision_inf.terminal_action is TerminalAction.FAILED


def test_wall_time_exceeded() -> None:
    controller = EarlyStoppingController(patience=4, min_delta=1e-4, max_wall_minutes=90)
    start_time = datetime.now(UTC)
    current_time = start_time + timedelta(minutes=91)

    decision = controller.evaluate(
        epoch=1, gauc=0.75, ndcg=0.40, hr=0.30, start_time=start_time, current_time=current_time
    )
    assert decision.terminal_action is TerminalAction.INTERRUPTED
    assert "wall time" in decision.reason.lower()


def test_stopping_state_round_trip_and_explicit_non_finite_reason() -> None:
    now = datetime.now(UTC)
    controller = EarlyStoppingController()
    controller.evaluate_epoch(
        epoch=1,
        gauc=0.8,
        ndcg=0.2,
        hr=0.3,
        start_time=now,
        current_time=now,
    )
    payload = controller.state_dict()
    restored = EarlyStoppingController()
    restored.load_state_dict(payload)
    assert restored.state == controller.state
    decision = restored.evaluate_epoch(
        epoch=2,
        gauc=0.8,
        ndcg=0.2,
        hr=0.3,
        start_time=now,
        current_time=now,
        non_finite_reason="validation logits",
    )
    assert decision.terminal_action is TerminalAction.FAILED
