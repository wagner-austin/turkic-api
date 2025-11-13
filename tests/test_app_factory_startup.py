from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app


def test_app_factory_and_health_endpoint() -> None:
    app = create_app()
    client: TestClient = TestClient(app)

    r = client.get("/api/v1/health")
    # The health endpoint is designed to always return 200 with a structured
    # payload even on subsystem failures (handled centrally).
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in {"healthy", "degraded", "unhealthy"}
