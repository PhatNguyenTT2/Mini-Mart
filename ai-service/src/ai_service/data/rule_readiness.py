"""Deterministic, pre-GPU checks for model-specific Wide rule coverage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import torch
from pydantic import BaseModel, Field

from ai_service.data.dataset import PurchaseBatch
from ai_service.errors import DataIntegrityError


class TrainingRuleReadiness(BaseModel):
    in_batch_rule_present_rate: float = Field(ge=0.0, le=1.0)
    explicit_rule_present_rate: float = Field(ge=0.0, le=1.0)
    rows_with_any_rule_rate: float = Field(ge=0.0, le=1.0)
    examined_rows: int = Field(ge=0)
    passed: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class RuleCoverageRates:
    in_batch_rule_present_rate: float
    explicit_rule_present_rate: float
    rows_with_any_rule_rate: float
    examined_rows: int


@dataclass
class RuleCoverageAccumulator:
    in_batch_present: int = 0
    in_batch_total: int = 0
    explicit_present: int = 0
    explicit_total: int = 0
    rows_with_rule: int = 0
    examined_rows: int = 0

    def observe_purchase_batch(self, batch: PurchaseBatch) -> None:
        denominator = batch.denominator_mask.bool()
        in_batch = batch.in_batch_rule_present.bool()
        explicit = batch.explicit_rule_present.bool()
        if (
            in_batch.shape != denominator.shape
            or explicit.ndim != 2
            or explicit.shape[0] != len(batch.user_idx)
            or int(denominator.sum().item()) == 0
            or explicit.numel() == 0
        ):
            raise DataIntegrityError("purchase rule-coverage denominator is invalid")
        valid_in_batch = in_batch & denominator
        self.in_batch_present += int(valid_in_batch.sum().item())
        self.in_batch_total += int(denominator.sum().item())
        self.explicit_present += int(explicit.sum().item())
        self.explicit_total += int(explicit.numel())
        self.rows_with_rule += int((valid_in_batch.any(dim=1) | explicit.any(dim=1)).sum().item())
        self.examined_rows += len(batch.user_idx)

    def observe_legacy_mask(self, present: torch.Tensor) -> None:
        values = present.bool()
        if values.ndim != 2 or values.numel() == 0:
            raise DataIntegrityError("legacy rule-coverage denominator is invalid")
        present_count = int(values.sum().item())
        self.in_batch_present += present_count
        self.in_batch_total += int(values.numel())
        self.explicit_present += present_count
        self.explicit_total += int(values.numel())
        self.rows_with_rule += int(values.any(dim=1).sum().item())
        self.examined_rows += int(values.shape[0])

    def rates(self) -> RuleCoverageRates:
        if self.in_batch_total == 0 or self.explicit_total == 0 or self.examined_rows == 0:
            raise DataIntegrityError("rule-coverage denominator is empty")
        values = (
            self.in_batch_present / self.in_batch_total,
            self.explicit_present / self.explicit_total,
            self.rows_with_rule / self.examined_rows,
        )
        if not all(math.isfinite(value) for value in values):
            raise DataIntegrityError("rule readiness contains non-finite coverage")
        return RuleCoverageRates(*values, examined_rows=self.examined_rows)


def assess_training_rule_readiness(
    train_loader: Any,
    *,
    minimum_rows_with_any_rule: float,
) -> TrainingRuleReadiness:
    """Scan epoch one sampler output without constructing a model or CUDA tensors."""
    coverage = RuleCoverageAccumulator()
    if hasattr(train_loader, "set_epoch"):
        train_loader.set_epoch(1)
    try:
        for batch in train_loader:
            if not isinstance(batch, PurchaseBatch):
                raise DataIntegrityError("rule readiness requires PurchaseBatch batches")
            coverage.observe_purchase_batch(batch)
    finally:
        if hasattr(train_loader, "set_epoch"):
            train_loader.set_epoch(1)
    values = coverage.rates()
    failures: list[str] = []
    if values.rows_with_any_rule_rate < minimum_rows_with_any_rule:
        failures.append(
            "rows_with_any_rule_rate="
            f"{values.rows_with_any_rule_rate:.6f} < {minimum_rows_with_any_rule:.6f}"
        )
    return TrainingRuleReadiness(
        in_batch_rule_present_rate=values.in_batch_rule_present_rate,
        explicit_rule_present_rate=values.explicit_rule_present_rate,
        rows_with_any_rule_rate=values.rows_with_any_rule_rate,
        examined_rows=values.examined_rows,
        passed=not failures,
        failure_reasons=tuple(failures),
    )


__all__ = [
    "RuleCoverageAccumulator",
    "RuleCoverageRates",
    "TrainingRuleReadiness",
    "assess_training_rule_readiness",
]
