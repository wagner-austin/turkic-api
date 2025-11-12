from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from redis import Redis

from api.models import JobCreate, JobResponse, JobStatus
from api.types import QueueProtocol


class JobService:
    """Service for job lifecycle; all dependencies are injected explicitly."""

    def __init__(
        self,
        *,
        redis: Redis,
        logger: logging.Logger,
        queue: QueueProtocol,
        data_dir: str = "/data",
    ) -> None:
        self._redis = redis
        self._logger = logger
        self._queue = queue
        self._data_dir = data_dir

    async def create_job(self, job: JobCreate) -> JobResponse:
        """Create a new job and enqueue background processing."""
        job_id = str(uuid4())
        now = datetime.utcnow()

        self._logger.debug(
            "Enqueuing job", extra={"job_id": job_id, "language": job.language}
        )

        # Persist job metadata snapshot
        self._redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "queued",
                "source": job.source,
                "language": job.language,
                "created_at": now.isoformat(),
            },
        )

        # Enqueue background job via injected queue (RQ serializes callables by import path)
        self._queue.enqueue(
            "api.jobs.process_corpus", job_id, job.model_dump(mode="json")
        )

        return JobResponse(job_id=job_id, status="queued", created_at=now)

    def _result_path(self, job_id: str) -> Path:
        return Path(self._data_dir) / "results" / f"{job_id}.txt"

    def get_job_status(self, job_id: str) -> JobStatus | None:
        """Fetch job status from Redis and build a typed response; returns None if not found."""
        data = self._redis.hgetall(f"job:{job_id}")  # expected dict[str, str]
        if not data:
            return None

        status = data.get("status", "queued")
        progress = int(data.get("progress", "0"))
        message = data.get("message")
        error = data.get("error")
        created_at_raw = data.get("created_at")
        updated_at_raw = data.get("updated_at", created_at_raw)
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.utcnow()
        )
        updated_at = (
            datetime.fromisoformat(updated_at_raw) if updated_at_raw else created_at
        )

        result_url: str | None = None
        file_id: str | None = data.get("file_id") if "file_id" in data else None
        if status == "completed" and self._result_path(job_id).exists():
            result_url = f"/api/v1/jobs/{job_id}/result"

        return JobStatus(
            job_id=job_id,
            status=status,  # Literal type validated by model
            progress=progress,
            message=message,
            result_url=result_url,
            file_id=file_id,
            created_at=created_at,
            updated_at=updated_at,
            error=error,
        )
