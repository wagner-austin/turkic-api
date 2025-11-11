from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from redis import exceptions as redis_exceptions

from api.dependencies import get_queue, get_redis
from api.main import create_app


class _RedisStub:
    def ping(self) -> bool:
        return True

    def close(self) -> None: ...
    def hgetall(self, _k: str) -> dict[str, str]:
        return {}


class _QueueStub:
    def enqueue(self, func: str, *args: object, **kwargs: object) -> object:
        return {"ok": True}


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_redis] = lambda: _RedisStub()
    app.dependency_overrides[get_queue] = lambda: _QueueStub()
    with TestClient(app) as c:
        yield c


def test_get_job_result_404(client: TestClient) -> None:
    r = client.get("/api/v1/jobs/doesnotexist/result")
    assert r.status_code == 404


def test_health_handles_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _RedisErr:
        def ping(self) -> bool:  # pragma: no cover - behavior tested via exception path
            raise redis_exceptions.RedisError("unreachable")

        def close(self) -> None:
            pass

    app = create_app()
    app.dependency_overrides[get_redis] = lambda: _RedisErr()
    with TestClient(app) as c:
        # Force volume to appear mounted so we hit the degraded branch
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True, raising=False)
        r = c.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "degraded"
        assert data["redis"] is False
