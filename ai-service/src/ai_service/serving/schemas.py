"""FastAPI Pydantic Request & Response Schemas for HTTP Serving."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    store_id: int = Field(default=1, description="Target store ID")
    user_id: Optional[int] = Field(default=None, description="Raw User ID")
    persona_cluster: Optional[int] = Field(default=None, ge=0, le=7, description="Persona cluster 0..7")
    candidate_product_ids: List[int] = Field(..., min_length=1, max_length=256, description="List of candidate raw product IDs")
    context_product_id: Optional[int] = Field(default=None, description="Anchor raw product ID for Apriori Wide rules")


class ProductRanking(BaseModel):
    product_id: int
    ai_score: float


class RecommendResponse(BaseModel):
    rankings: List[ProductRanking]
    inference_ms: float
    model_version: str


class HealthResponse(BaseModel):
    status: str
    service: str
    model_version: str
    cached_products: int
    onnx_ready: bool
