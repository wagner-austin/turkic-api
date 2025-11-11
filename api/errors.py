from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from api.models import ErrorResponse


def _code_for(
    status_code: int, path: str
) -> Literal[
    "INVALID_REQUEST",
    "JOB_NOT_FOUND",
    "JOB_FAILED",
    "RATE_LIMIT_EXCEEDED",
    "INTERNAL_ERROR",
]:
    if status_code == 404 and "/jobs/" in path:
        return "JOB_NOT_FOUND"
    if status_code == 422:
        return "INVALID_REQUEST"
    if status_code == 429:
        return "RATE_LIMIT_EXCEEDED"
    if status_code == 410:
        return "JOB_FAILED"
    return "INTERNAL_ERROR"


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        code = _code_for(exc.status_code, str(request.url.path))
        payload = ErrorResponse(
            error=str(exc.detail),
            code=code,
            details=None,
            timestamp=datetime.utcnow(),
        )
        return JSONResponse(
            status_code=exc.status_code, content=payload.model_dump(mode="json")
        )
    # Fallback: treat as unhandled
    return await unhandled_exception_handler(request, exc)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    payload = ErrorResponse(
        error="Internal server error",
        code="INTERNAL_ERROR",
        details={"type": type(exc).__name__},
        timestamp=datetime.utcnow(),
    )
    return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))
