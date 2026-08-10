"""FastAPI transport for the immutable recommender runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ai_service.config import Settings, get_settings
from ai_service.errors import ConfigurationError, ServingUnavailableError
from ai_service.serving.metrics import CANDIDATE_COUNT, INFERENCE_SECONDS, READY, REQUESTS
from ai_service.serving.runtime import RecommenderRuntime
from ai_service.serving.schemas import HealthResponse, RecommendRequest, RecommendResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runtime = None
        app.state.load_error = None
        try:
            settings.validate_production(serving=True)
            if settings.data.model_bundle_path is None:
                raise ServingUnavailableError("AI_MODEL_BUNDLE_PATH is not configured")
            app.state.runtime = RecommenderRuntime.load(
                settings.data.model_bundle_path.resolve(), settings
            )
            READY.set(1)
        except (ConfigurationError, ServingUnavailableError) as error:
            app.state.load_error = str(error)
            READY.set(0)
        yield
        app.state.runtime = None
        READY.set(0)

    application = FastAPI(title="POSMart AI Service", version="3.0.0", lifespan=lifespan)

    @application.get("/health/live", response_model=HealthResponse)
    def live() -> HealthResponse:
        return HealthResponse(status="live", ready=application.state.runtime is not None)

    def readiness() -> HealthResponse | JSONResponse:
        runtime = cast(RecommenderRuntime | None, application.state.runtime)
        if runtime is None:
            return JSONResponse(
                status_code=503,
                content=HealthResponse(status="not_ready", ready=False).model_dump(),
            )
        return HealthResponse(
            status="ready",
            ready=True,
            model_version=runtime.manifest.model_version,
            bundle_id=runtime.manifest.bundle_id,
        )

    application.get("/health/ready", response_model=HealthResponse)(readiness)
    application.get("/health", response_model=HealthResponse)(readiness)

    @application.post("/recommend", response_model=RecommendResponse)
    def recommend(request: RecommendRequest) -> RecommendResponse:
        runtime = cast(RecommenderRuntime | None, application.state.runtime)
        if runtime is None:
            REQUESTS.labels(status="unavailable").inc()
            raise HTTPException(status_code=503, detail="model bundle is not ready")
        CANDIDATE_COUNT.observe(len(request.candidate_product_ids))
        try:
            response = runtime.recommend(request)
        except ValueError as error:
            REQUESTS.labels(status="invalid").inc()
            raise HTTPException(status_code=422, detail=str(error)) from error
        REQUESTS.labels(status="ok").inc()
        INFERENCE_SECONDS.observe(response.inference_ms / 1_000)
        return response

    @application.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return application


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "ai_service.serving.app:app",
        host=settings.serving.host,
        port=settings.serving.port,
        workers=settings.serving.workers,
    )


if __name__ == "__main__":
    main()
