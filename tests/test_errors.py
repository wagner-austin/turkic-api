from __future__ import annotations

import asyncio

from fastapi import HTTPException
from starlette.requests import Request

from api.errors import http_exception_handler, unhandled_exception_handler


def _make_request(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
    }
    return Request(scope)


def test_http_exception_handler_job_not_found() -> None:
    req = _make_request("/api/v1/jobs/abc")
    exc = HTTPException(status_code=404, detail="Job not found")
    resp = asyncio.run(http_exception_handler(req, exc))
    assert resp.status_code == 404
    assert b"JOB_NOT_FOUND" in resp.body


def test_unhandled_exception_handler() -> None:
    req = _make_request("/api/v1/health")
    exc = RuntimeError("boom")
    resp = asyncio.run(unhandled_exception_handler(req, exc))
    assert resp.status_code == 500
    assert b"INTERNAL_ERROR" in resp.body
