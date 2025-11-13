from __future__ import annotations

import json
import logging
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Final

import httpx
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
    script_val = params.get("script")

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
    # Validate optional script filter
    script: str | None
    if script_val is None:
        script = None
    elif isinstance(script_val, str):
        s = script_val.strip()
        if not s:
            script = None
        else:
            norm = s[0:1].upper() + s[1:].lower()
            if norm not in ("Latn", "Cyrl", "Arab"):
                raise ValueError("Invalid script; expected 'Latn', 'Cyrl', or 'Arab'")
            script = norm
    else:
        raise TypeError("script must be a string or null")
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
        ensure_corpus_file(spec, settings.data_dir, script=script)
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

    # Optional: upload result to data-bank-api and record file_id (non-blocking)
    url_cfg: Final[str] = settings.data_bank_api_url
    key_cfg: Final[str] = settings.data_bank_api_key
    logger.info(f"UPLOAD CHECK: url={url_cfg!r} key_len={len(key_cfg)}")
    if url_cfg.strip() != "" and key_cfg.strip() != "":

        class _UploadError(Exception):
            pass

        def _try_upload() -> None:
            headers = {"X-API-Key": key_cfg, "X-Request-ID": job_id}
            upload_url = f"{url_cfg.rstrip('/')}/files"
            logger.info(f"Starting upload to {upload_url}")
            with out_path.open("rb") as f:
                files = {"file": (f"{job_id}.txt", f, "text/plain; charset=utf-8")}
                logger.info(f"Sending POST request, file size: {out_path.stat().st_size}")
                resp = httpx.post(
                    upload_url, headers=headers, files=files, timeout=600.0
                )
            logger.info(f"Upload response: status={resp.status_code}")
            if 200 <= resp.status_code < 300:
                fid: str | None = None
                with suppress(json.JSONDecodeError):
                    obj = json.loads(resp.text)
                    if isinstance(obj, dict):
                        v = obj.get("file_id")
                        if isinstance(v, str) and v.strip() != "":
                            fid = v
                if fid is not None:
                    redis.hset(f"job:{job_id}", {"file_id": fid})
                    logger.info(
                        "data-bank upload succeeded",
                        extra={"job_id": job_id, "file_id": fid},
                    )
                else:
                    logger.error(
                        "data-bank upload missing file_id",
                        extra={"job_id": job_id, "status": resp.status_code},
                    )
                    raise _UploadError("missing file_id in response")
            else:
                logger.error(
                    "data-bank upload failed",
                    extra={"job_id": job_id, "status": resp.status_code},
                )
                raise _UploadError(f"upload failed: {resp.status_code}")

        with suppress(_UploadError, httpx.HTTPError, OSError):
            _try_upload()
    return {"job_id": job_id, "status": "completed", "result": str(out_path)}


def process_corpus(job_id: str, params: dict[str, object]) -> dict[str, object]:
    """RQ job entry point. Loads deps from env and delegates to the impl."""
    from api.logging import setup_logging
    setup_logging()  # Initialize logging for worker process
    settings = Settings.from_env()
    logger = get_logger(__name__)
    client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        return process_corpus_impl(
            job_id, params, redis=client, settings=settings, logger=logger
        )
    finally:
        client.close()
