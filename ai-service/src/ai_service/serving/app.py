"""FastAPI Application for ONNX Serving Microservice."""

import time
from typing import Optional
from fastapi import FastAPI, HTTPException, status
import numpy as np
import uvicorn

from ai_service.config import get_settings
from ai_service.serving.schemas import RecommendRequest, RecommendResponse, ProductRanking, HealthResponse
from ai_service.data.snapshot import load_snapshot
from ai_service.data.rules import load_rule_store

app = FastAPI(title="POSMART AI Inference Microservice", version="2.0.0")
settings = get_settings()

snapshot = None
rule_store = None


@app.on_event("startup")
def startup_event():
    global snapshot, rule_store
    try:
        snapshot = load_snapshot(settings.data.snapshot_id, settings)
        rule_store = load_rule_store(snapshot.snapshot_dir, settings.data.min_rule_lift)
        print("✅ AI Service data snapshot and rule store loaded successfully.")
    except Exception as err:
        print(f"⚠️ Warning: Snapshot loading failed on startup: {err}")


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        service="ai-service",
        model_version=settings.serving.model_version,
        cached_products=settings.data.num_items,
        onnx_ready=snapshot is not None,
    )


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    t0 = time.perf_counter()

    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Service data snapshot not initialized",
        )

    rankings: list[ProductRanking] = []
    
    # Map raw candidate product IDs to internal IDs
    internal_cands = [snapshot.product_map.get(pid, -1) for pid in req.candidate_product_ids]
    valid_cands = [(raw_pid, int_pid) for raw_pid, int_pid in zip(req.candidate_product_ids, internal_cands) if int_pid >= 0]

    if not valid_cands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid candidate product IDs provided",
        )

    # Compute Wide scores if context_product_id provided
    ctx_internal = snapshot.product_map.get(req.context_product_id, -1) if req.context_product_id else -1

    for raw_pid, int_pid in valid_cands:
        score = 0.5  # Base score
        if rule_store is not None and ctx_internal >= 0:
            lift = rule_store.lookup(ctx_internal, int_pid)
            score += float(lift)
        rankings.append(ProductRanking(product_id=raw_pid, ai_score=round(score, 4)))

    # Sort descending by AI score
    rankings.sort(key=lambda r: r.ai_score, reverse=True)

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return RecommendResponse(
        rankings=rankings,
        inference_ms=round(latency_ms, 3),
        model_version=settings.serving.model_version,
    )


def run():
    uvicorn.run("ai_service.serving.app:app", host=settings.serving.host, port=settings.serving.port)


if __name__ == "__main__":
    run()
