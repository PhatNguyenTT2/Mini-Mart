from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ai_service.config import Settings
from ai_service.serving.app import create_app


def test_health_readiness_stays_unavailable_when_bundle_is_missing(tmp_path: Path) -> None:
    settings = Settings()
    settings.data.model_bundle_path = tmp_path / "missing-bundle"
    application = create_app(settings)

    with TestClient(application) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        alias = client.get("/health")
        recommend = client.post(
            "/recommend",
            json={"store_id": 1, "candidate_product_ids": [1001]},
        )

    assert live.status_code == 200
    assert live.json() == {
        "status": "live",
        "ready": False,
        "model_version": None,
        "bundle_id": None,
    }
    assert ready.status_code == 503
    assert alias.status_code == 503
    assert recommend.status_code == 503
