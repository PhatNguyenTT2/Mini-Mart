"""Validated HTTP request and response models."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator


class RecommendRequest(BaseModel):
    store_id: int = Field(gt=0)
    user_id: int | None = Field(default=None, gt=0)
    persona_cluster: int | None = Field(default=None, ge=0, le=7)
    candidate_product_ids: list[int] = Field(min_length=1, max_length=256)
    context_product_id: int | None = Field(default=None, gt=0)

    @field_validator("candidate_product_ids")
    @classmethod
    def validate_candidates(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("candidate IDs must be positive")
        if len(values) != len(set(values)):
            raise ValueError("candidate IDs must be unique")
        return values


class ProductRanking(BaseModel):
    product_id: int
    rank: int = Field(gt=0)
    ai_score: float

    @field_validator("ai_score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("score must be finite")
        return value


class RecommendResponse(BaseModel):
    rankings: list[ProductRanking]
    inference_ms: float = Field(ge=0)
    model_version: str
    bundle_id: str


class HealthResponse(BaseModel):
    status: str
    ready: bool
    model_version: str | None = None
    bundle_id: str | None = None
