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
    strict_target_rule_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    other_positive_rule_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    valid_negative_rule_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    explicit_negative_rule_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    negative_only_row_rate: float = Field(default=0.0, ge=0.0, le=1.0)


@dataclass(frozen=True)
class RuleCoverageRates:
    in_batch_rule_present_rate: float
    explicit_rule_present_rate: float
    rows_with_any_rule_rate: float
    examined_rows: int
    strict_target_rule_rate: float = 0.0
    other_positive_rule_rate: float = 0.0
    valid_negative_rule_rate: float = 0.0
    explicit_negative_rule_rate: float = 0.0
    negative_only_row_rate: float = 0.0


@dataclass
class RuleCoverageAccumulator:
    in_batch_present: int = 0
    in_batch_total: int = 0
    explicit_present: int = 0
    explicit_total: int = 0
    rows_with_rule: int = 0
    examined_rows: int = 0
    strict_target_present: int = 0
    strict_target_total: int = 0
    other_positive_present: int = 0
    other_positive_total: int = 0
    valid_negative_present: int = 0
    valid_negative_total: int = 0
    negative_only_rows: int = 0

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
        diagonal = torch.eye(len(batch.user_idx), dtype=torch.bool, device=in_batch.device)
        strict = in_batch & diagonal
        other_positive = in_batch & batch.positive_mask.bool() & ~diagonal
        valid_negative = in_batch & batch.denominator_mask.bool() & ~batch.positive_mask.bool()
        self.strict_target_present += int(strict.sum().item())
        self.strict_target_total += len(batch.user_idx)
        self.other_positive_present += int(other_positive.sum().item())
        self.other_positive_total += int(
            batch.positive_mask.bool().logical_and(~diagonal).sum().item()
        )
        self.valid_negative_present += int(valid_negative.sum().item())
        self.valid_negative_total += int(
            batch.denominator_mask.bool().logical_and(~batch.positive_mask.bool()).sum().item()
        )
        self.negative_only_rows += int(
            (~strict.any(dim=1) & (valid_negative.any(dim=1) | explicit.any(dim=1))).sum().item()
        )

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
        rates = tuple(
            (
                *values,
                self.strict_target_present / self.strict_target_total
                if self.strict_target_total
                else 0.0,
                self.other_positive_present / self.other_positive_total
                if self.other_positive_total
                else 0.0,
                self.valid_negative_present / self.valid_negative_total
                if self.valid_negative_total
                else 0.0,
                self.explicit_present / self.explicit_total,
                self.negative_only_rows / self.examined_rows,
            )
        )
        if not all(math.isfinite(value) for value in rates):
            raise DataIntegrityError("rule readiness contains non-finite coverage")
        return RuleCoverageRates(
            *values,
            examined_rows=self.examined_rows,
            strict_target_rule_rate=rates[0],
            other_positive_rule_rate=rates[1],
            valid_negative_rule_rate=rates[2],
            explicit_negative_rule_rate=rates[3],
            negative_only_row_rate=rates[4],
        )


def assess_training_rule_readiness(
    train_loader: Any,
    *,
    minimum_rows_with_any_rule: float,
    minimum_training_target_rule_rate: float | None = None,
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
    target_floor = minimum_training_target_rule_rate
    if target_floor is not None and values.strict_target_rule_rate < target_floor:
        failures.append(
            f"strict_target_rule_rate={values.strict_target_rule_rate:.6f} < {target_floor:.6f}"
        )
    return TrainingRuleReadiness(
        in_batch_rule_present_rate=values.in_batch_rule_present_rate,
        explicit_rule_present_rate=values.explicit_rule_present_rate,
        rows_with_any_rule_rate=values.rows_with_any_rule_rate,
        examined_rows=values.examined_rows,
        passed=not failures,
        failure_reasons=tuple(failures),
        strict_target_rule_rate=values.strict_target_rule_rate,
        other_positive_rule_rate=values.other_positive_rule_rate,
        valid_negative_rule_rate=values.valid_negative_rule_rate,
        explicit_negative_rule_rate=values.explicit_negative_rule_rate,
        negative_only_row_rate=values.negative_only_row_rate,
    )


__all__ = [
    "RuleCoverageAccumulator",
    "RuleCoverageRates",
    "TrainingRuleReadiness",
    "assess_training_rule_readiness",
]
