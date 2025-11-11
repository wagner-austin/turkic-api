from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    source: Literal["oscar", "wikipedia"]
    language: Literal["kk", "ky", "uz", "tr", "ug"]
    script: Literal["Latn", "Cyrl", "Arab"] | None = None
    max_sentences: int = Field(ge=1, le=100000, default=1000)
    transliterate: bool = True
    confidence_threshold: float = Field(ge=0.0, le=1.0, default=0.95)


class JobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int
    message: str | None = None
    result_url: str | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    redis: bool
    volume: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    code: Literal[
        "INVALID_REQUEST",
        "JOB_NOT_FOUND",
        "JOB_FAILED",
        "RATE_LIMIT_EXCEEDED",
        "INTERNAL_ERROR",
    ]
    details: dict[str, object] | None = None
    timestamp: datetime
