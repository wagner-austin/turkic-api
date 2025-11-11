from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.errors import (
    HealthStatusError,
    health_exception_handler,
    http_exception_handler,
)


def _req(path: str) -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


def test_http_exception_handler_mappings() -> None:
    # 422 -> INVALID_REQUEST
    r1 = asyncio.run(
        http_exception_handler(
            _req("/api/v1/jobs/abc"), HTTPException(status_code=422, detail="bad")
        )
    )
    assert r1.status_code == 422
    assert b"INVALID_REQUEST" in r1.body

    # 429 -> RATE_LIMIT_EXCEEDED
    r2 = asyncio.run(
        http_exception_handler(
            _req("/api/v1/jobs/abc"), HTTPException(status_code=429, detail="rate")
        )
    )
    assert r2.status_code == 429
    assert b"RATE_LIMIT_EXCEEDED" in r2.body

    # 410 -> JOB_FAILED
    r3 = asyncio.run(
        http_exception_handler(
            _req("/api/v1/jobs/abc"), HTTPException(status_code=410, detail="gone")
        )
    )
    assert r3.status_code == 410
    assert b"JOB_FAILED" in r3.body

    # 404 but not jobs path -> INTERNAL_ERROR
    r4 = asyncio.run(
        http_exception_handler(
            _req("/api/v1/health"), HTTPException(status_code=404, detail="nope")
        )
    )
    assert r4.status_code == 404
    assert b"INTERNAL_ERROR" in r4.body
    # Non-HTTPException falls back to unhandled handler (500)
    r5 = asyncio.run(
        http_exception_handler(_req("/api/v1/health"), RuntimeError("oops"))
    )
    assert r5.status_code == 500
    assert b"INTERNAL_ERROR" in r5.body


def test_health_exception_handler_re_raises_for_unexpected() -> None:
    req = _req("/api/v1/health")
    with pytest.raises(RuntimeError):
        # Pass a generic exception to ensure re-raise path is covered
        asyncio.run(health_exception_handler(req, RuntimeError("boom")))


def test_health_exception_handler_serializes_health() -> None:
    req = _req("/api/v1/health")
    resp = asyncio.run(
        health_exception_handler(
            req, HealthStatusError(status="degraded", redis=False, volume=True)
        )
    )
    assert resp.status_code == 200
    assert b"degraded" in resp.body
