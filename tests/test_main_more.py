from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

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
