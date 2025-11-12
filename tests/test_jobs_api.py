from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_queue, get_redis
from api.main import create_app


class _RedisStub:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self._hashes[key] = {**mapping}
        return 1

    def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {}).copy()


class _QueueStub:
    def enqueue(self, func: str, *args: object, **kwargs: object) -> object:
        return {"ok": True}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Point data dir to tmp for result files
    monkeypatch.setenv("TURKIC_DATA_DIR", str(tmp_path))
    app = create_app()
    r = _RedisStub()
    app.dependency_overrides[get_redis] = lambda: r
    app.dependency_overrides[get_queue] = lambda: _QueueStub()
    # Expose stub via module-level variable for tests that need to seed data
    global _redis_stub_for_tests
    _redis_stub_for_tests = r
    with TestClient(app) as c:
        yield c


def _seed_job(redis: _RedisStub, job_id: str, status: str, tmp_path: Path) -> None:
    # Minimal fields to emulate JobService
    redis.hset(
        f"job:{job_id}",
        {
            "status": status,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
    )
    if status == "completed":
        results_dir = tmp_path / "results"
        results_dir.mkdir(exist_ok=True)
        (results_dir / f"{job_id}.txt").write_text("hello\nworld\n", encoding="utf-8")


def test_job_status_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/jobs/doesnotexist")
    assert resp.status_code == 404


def test_job_status_found(client: TestClient, tmp_path: Path) -> None:
    # Access the overridden redis to seed data
    assert _redis_stub_for_tests is not None
    rstub: _RedisStub = _redis_stub_for_tests
    _seed_job(rstub, "abc", "processing", tmp_path)
    resp = client.get("/api/v1/jobs/abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == "abc"
    assert data["status"] == "processing"
    assert data["progress"] in range(101)


def test_job_result_not_ready(client: TestClient, tmp_path: Path) -> None:
    assert _redis_stub_for_tests is not None
    rstub: _RedisStub = _redis_stub_for_tests
    _seed_job(rstub, "j1", "queued", tmp_path)
    resp = client.get("/api/v1/jobs/j1/result")
    assert resp.status_code == 425


def test_job_result_completed(client: TestClient, tmp_path: Path) -> None:
    assert _redis_stub_for_tests is not None
    rstub: _RedisStub = _redis_stub_for_tests
    _seed_job(rstub, "j2", "completed", tmp_path)
    resp = client.get("/api/v1/jobs/j2/result")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "attachment;" in resp.headers.get("content-disposition", "")
    assert "hello" in resp.text


def test_job_result_missing_file_is_expired(client: TestClient, tmp_path: Path) -> None:
    assert _redis_stub_for_tests is not None
    redis_stub: _RedisStub = _redis_stub_for_tests
    # Seed completed status but do not create file
    redis_stub.hset(
        "job:j3",
        {
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
    )
    resp = client.get("/api/v1/jobs/j3/result")
    assert resp.status_code == 410


_redis_stub_for_tests: _RedisStub | None = None
