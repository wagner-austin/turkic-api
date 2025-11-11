from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_queue, get_redis
from api.main import create_app


class _RedisStub:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self._store[key] = {**mapping}
        return 1


class _QueueStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def enqueue(
        self, func: str, *args: object, **kwargs: object
    ) -> object:  # QueueProtocol
        self.calls.append((func, args, kwargs))
        return {"ok": True}


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    fake = _RedisStub()
    app.dependency_overrides[get_redis] = lambda: fake
    q = _QueueStub()
    app.dependency_overrides[get_queue] = lambda: q
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Default stub returns redis=True and we simulate volume=False here to hit degraded path
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False, raising=False)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"degraded"}
    assert isinstance(data["redis"], bool)
    assert isinstance(data["volume"], bool)
    assert isinstance(data["timestamp"], str)


def test_create_job_enqueues_and_returns_id(client: TestClient) -> None:
    payload = {
        "source": "oscar",
        "language": "kk",
        "max_sentences": 10,
        "transliterate": True,
        "confidence_threshold": 0.95,
    }
    resp = client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert isinstance(data["job_id"], str)
    assert data["job_id"]


def test_health_healthy_and_unhealthy_paths(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Healthy: redis True, volume True
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True, raising=False)
    resp = client.get("/api/v1/health")
    assert resp.json()["status"] == "healthy"

    # Unhealthy: redis False, volume False
    class _RedisFalse(_RedisStub):
        def ping(self) -> bool:
            return False

    app = create_app()
    app.dependency_overrides[get_redis] = lambda: _RedisFalse()
    with TestClient(app) as alt:
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False, raising=False)
        r2 = alt.get("/api/v1/health")
        assert r2.json()["status"] == "unhealthy"
