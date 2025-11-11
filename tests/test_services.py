from __future__ import annotations

import asyncio
import logging

from api.models import JobCreate
from api.services import JobService


class _RedisStub:
    def __init__(self) -> None:
        self.hset_calls: list[tuple[str, dict[str, str]]] = []

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hset_calls.append((key, mapping))
        return 1


class _QueueStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def enqueue(
        self, func: str, *args: object, **kwargs: object
    ) -> object:  # QueueProtocol
        self.calls.append((func, args, kwargs))
        return {"ok": True}


def test_job_service_create_job_enqueues_and_sets_metadata() -> None:
    r = _RedisStub()
    q = _QueueStub()
    service = JobService(redis=r, logger=logging.getLogger(__name__), queue=q)
    job = JobCreate(
        source="oscar",
        language="kk",
        max_sentences=5,
        transliterate=True,
        confidence_threshold=0.9,
    )

    resp = asyncio.run(service.create_job(job))

    assert resp.status == "queued"
    assert len(r.hset_calls) == 1
    key, mapping = r.hset_calls[0]
    assert key.startswith("job:")
    assert mapping["status"] == "queued"
    assert q.calls
    assert q.calls[0][0] == "api.jobs.process_corpus"
