from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from redis import Redis

from api.config import Settings
from api.logging import get_logger
from core.corpus import LocalCorpusService
from core.corpus_download import ensure_corpus_file
from core.models import ProcessSpec, is_language, is_source
from core.translit import to_ipa


def process_corpus_impl(
    job_id: str,
    params: dict[str, object],
    *,
    redis: Redis,
    settings: Settings,
    logger: logging.Logger,
) -> dict[str, object]:
    """Implementation for corpus processing with explicit injected deps.

    This function updates job status in Redis, writes a results file under
    settings.data_dir/results/{job_id}.txt, and returns a typed summary.
    """
    now = datetime.utcnow().isoformat()
    redis.hset(
        f"job:{job_id}",
        mapping={
            "status": "processing",
            "updated_at": now,
            "progress": "0",
            "message": "started",
        },
    )

    # Build processing specification from validated parameters
    src_val = params.get("source", "")
    lang_val = params.get("language", "")
    max_val = params.get("max_sentences", 1000)
    translit_val = params.get("transliterate", True)
    thr_val = params.get("confidence_threshold", 0.95)

    if not isinstance(src_val, str) or not isinstance(lang_val, str):
        raise TypeError("source and language must be strings")
    lang_raw = lang_val.strip()
    src_raw = src_val.strip()

    if not isinstance(max_val, int):
        raise TypeError("max_sentences must be int")
    max_sentences = max_val

    if not isinstance(translit_val, bool):
        raise TypeError("transliterate must be bool")
    transliterate = translit_val

    if not isinstance(thr_val, (int, float)):
        raise TypeError("confidence_threshold must be a number")
    thr = float(thr_val)
    if not is_source(src_raw) or not is_language(lang_raw):
        raise ValueError("Invalid source or language in job parameters")
    spec = ProcessSpec(
        source=src_raw,
        language=lang_raw,
        max_sentences=max_sentences,
        transliterate=transliterate,
        confidence_threshold=thr,
    )

    # Ensure local corpus exists (download if missing)
    try:
        ensure_corpus_file(spec, settings.data_dir)
    except Exception as exc:
        redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "failed",
                "updated_at": datetime.utcnow().isoformat(),
                "message": "download_failed",
                "error": type(exc).__name__,
            },
        )
        raise

    svc = LocalCorpusService(settings.data_dir)

    out_dir = Path(settings.data_dir) / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{job_id}.txt"
    written = 0
    with out_path.open("w", encoding="utf-8") as out:
        for line in svc.stream(spec):
            out.write(
                (to_ipa(line, spec.language) if spec.transliterate else line) + "\n"
            )
            written += 1
            if written % 50 == 0:
                redis.hset(
                    f"job:{job_id}",
                    mapping={
                        "progress": str(min(99, written)),
                        "updated_at": datetime.utcnow().isoformat(),
                        "message": "processing",
                    },
                )

    redis.hset(
        f"job:{job_id}",
        mapping={
            "status": "completed",
            "updated_at": datetime.utcnow().isoformat(),
            "progress": "100",
            "message": "done",
        },
    )
    logger.info("Job completed", extra={"job_id": job_id})
    return {"job_id": job_id, "status": "completed", "result": str(out_path)}


def process_corpus(job_id: str, params: dict[str, object]) -> dict[str, object]:
    """RQ job entry point. Loads deps from env and delegates to the impl."""
    settings = Settings.from_env()
    logger = get_logger(__name__)
    client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        return process_corpus_impl(
            job_id, params, redis=client, settings=settings, logger=logger
        )
    finally:
        client.close()
