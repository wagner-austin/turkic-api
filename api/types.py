from __future__ import annotations

from typing import Protocol


class LoggerProtocol(Protocol):
    """Protocol for a minimal structured logger interface."""

    def debug(self, msg: str, **kwargs: object) -> None: ...

    def info(self, msg: str, **kwargs: object) -> None: ...

    def warning(self, msg: str, **kwargs: object) -> None: ...

    def error(self, msg: str, **kwargs: object) -> None: ...


class QueueProtocol(Protocol):
    """Minimal interface for a background job queue."""

    def enqueue(self, func: str, *args: object, **kwargs: object) -> object: ...
