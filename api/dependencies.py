from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from redis import Redis

from api.config import Settings
from api.logging import get_logger
from api.types import QueueProtocol


def get_settings() -> Settings:
    """Dependency: typed application settings from environment."""
    return Settings.from_env()


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_redis(settings: SettingsDep) -> Generator[Redis, None, None]:
    """Dependency: Redis client using URL from settings; closes on teardown."""
    client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        yield client
    finally:
        client.close()


def get_request_logger() -> logging.Logger:
    """Dependency: request-scoped logger (delegates to global logger)."""
    return get_logger(__name__)


def get_queue(
    redis: Annotated[Redis, Depends(get_redis)],
) -> QueueProtocol:
    """Dependency: RQ queue bound to provided Redis connection.

    This import is local to keep import graph light and to enable easy dependency
    overriding in tests.
    """
    from rq import Queue

    q: QueueProtocol = Queue(connection=redis)
    return q
