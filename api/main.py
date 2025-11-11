from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from redis import Redis

from api.config import Settings
from api.dependencies import get_queue, get_redis, get_request_logger, get_settings
from api.errors import HealthStatusError, health_exception_handler
from api.health import compute_health
from api.logging import setup_logging
from api.models import HealthResponse, JobCreate, JobResponse, JobStatus
from api.services import JobService
from api.types import QueueProtocol


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Turkic API", version="1.0.0")
    # Centralized exception handler for health probe results
    app.add_exception_handler(HealthStatusError, health_exception_handler)

    @app.post("/api/v1/jobs", response_model=JobResponse)
    async def create_job(
        job: JobCreate,
        redis: Annotated[Redis, Depends(get_redis)],
        logger: Annotated[logging.Logger, Depends(get_request_logger)],
        queue: Annotated[QueueProtocol, Depends(get_queue)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> JobResponse:
        service = JobService(
            redis=redis, logger=logger, queue=queue, data_dir=settings.data_dir
        )
        return await service.create_job(job)

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health(
        redis: Annotated[Redis, Depends(get_redis)],
        settings: Annotated[Settings, Depends(get_settings)],
        logger: Annotated[logging.Logger, Depends(get_request_logger)],
    ) -> HealthResponse:
        return compute_health(redis=redis, settings=settings, logger=logger)

    @app.get("/api/v1/jobs/{job_id}", response_model=JobStatus)
    async def get_job(
        job_id: str,
        redis: Annotated[Redis, Depends(get_redis)],
        logger: Annotated[logging.Logger, Depends(get_request_logger)],
        queue: Annotated[QueueProtocol, Depends(get_queue)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> JobStatus:
        service = JobService(
            redis=redis, logger=logger, queue=queue, data_dir=settings.data_dir
        )
        status_obj = service.get_job_status(job_id)
        if status_obj is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return status_obj

    @app.get("/api/v1/jobs/{job_id}/result")
    async def get_job_result(
        job_id: str,
        redis: Annotated[Redis, Depends(get_redis)],
        logger: Annotated[logging.Logger, Depends(get_request_logger)],
        queue: Annotated[QueueProtocol, Depends(get_queue)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> FileResponse:
        service = JobService(
            redis=redis, logger=logger, queue=queue, data_dir=settings.data_dir
        )
        status_obj = service.get_job_status(job_id)
        if status_obj is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if status_obj.status != "completed":
            raise HTTPException(status_code=425, detail="Job not completed")
        result_path = (Path(settings.data_dir) / "results" / f"{job_id}.txt").resolve()
        if not result_path.exists():
            # Treat missing result as expired
            raise HTTPException(status_code=410, detail="Job result expired")
        filename = f"result_{job_id}.txt"
        return FileResponse(
            path=str(result_path),
            media_type="text/plain; charset=utf-8",
            filename=filename,
        )

    return app
