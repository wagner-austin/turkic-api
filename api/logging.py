from __future__ import annotations

import json
import logging
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logs with stable keys."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting
        data: dict[str, object] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Optional contextual fields
        if hasattr(record, "job_id"):
            data["job_id"] = record.job_id
        if hasattr(record, "language"):
            data["language"] = record.language

        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configure global structured logging; idempotent-ish."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    # Avoid duplicate handlers if setup is called multiple times
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return module logger."""
    return logging.getLogger(name)
