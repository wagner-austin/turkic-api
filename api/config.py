from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment in a type-safe, framework-free way."""

    redis_url: str
    data_dir: str
    environment: str

    @staticmethod
    def from_env() -> Settings:
        prefix = "TURKIC_"
        redis_url = os.getenv(f"{prefix}REDIS_URL", "redis://localhost:6379/0").strip()
        data_dir = os.getenv(f"{prefix}DATA_DIR", "/data").strip() or "/data"
        environment = os.getenv(f"{prefix}ENV", "local").strip() or "local"
        return Settings(redis_url=redis_url, data_dir=data_dir, environment=environment)
