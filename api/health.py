from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from redis import Redis
from redis import exceptions as redis_exceptions

from api.config import Settings
from api.errors import HealthStatusError
from api.models import HealthResponse


def compute_health(
    redis: Redis, settings: Settings, logger: logging.Logger
) -> HealthResponse:
    """Compute service health.

    On subsystem failure, raises HealthStatus which is handled centrally to
    return a 200 OK with a structured payload. This avoids swallowing
    exceptions in request handlers while still providing a stable contract.
    """
    volume_ok = Path(settings.data_dir).exists()
    try:
        redis_ok = bool(redis.ping())
    except redis_exceptions.RedisError as exc:
        logger.warning("Redis health check failed", exc_info=exc)
        derived_status: Literal["healthy", "degraded", "unhealthy"] = (
            "degraded" if volume_ok else "unhealthy"
        )
        # Raise domain exception with full status so handler can respond 200
        raise HealthStatusError(
            status=derived_status, redis=False, volume=volume_ok
        ) from exc

    overall: Literal["healthy", "degraded", "unhealthy"]
    if redis_ok and volume_ok:
        overall = "healthy"
    elif redis_ok or volume_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall, redis=redis_ok, volume=volume_ok, timestamp=datetime.utcnow()
    )
