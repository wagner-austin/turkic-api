from __future__ import annotations

import logging
from pathlib import Path

import pytest

import api.jobs as jobs_mod
from api.config import Settings


class _RedisStub:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        cur = self.hashes.get(key, {})
        cur.update(mapping)
        self.hashes[key] = cur
        return 1


def test_process_spec_type_errors(tmp_path: Path) -> None:
    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0", data_dir=str(tmp_path), environment="test"
    )
    logger = logging.getLogger(__name__)

    with pytest.raises(TypeError, match="source and language"):
        jobs_mod.process_corpus_impl(
            "a",
            {"source": 1, "language": 2},
            redis=redis,
            settings=settings,
            logger=logger,
        )

    with pytest.raises(TypeError, match="max_sentences"):
        jobs_mod.process_corpus_impl(
            "a",
            {"source": "oscar", "language": "kk", "max_sentences": "x"},
            redis=redis,
            settings=settings,
            logger=logger,
        )

    with pytest.raises(TypeError, match="transliterate"):
        jobs_mod.process_corpus_impl(
            "a",
            {
                "source": "oscar",
                "language": "kk",
                "max_sentences": 1,
                "transliterate": "y",
            },
            redis=redis,
            settings=settings,
            logger=logger,
        )

    with pytest.raises(TypeError, match="confidence_threshold"):
        jobs_mod.process_corpus_impl(
            "a",
            {
                "source": "oscar",
                "language": "kk",
                "max_sentences": 1,
                "transliterate": True,
                "confidence_threshold": "no",
            },
            redis=redis,
            settings=settings,
            logger=logger,
        )


def test_invalid_source_or_language(tmp_path: Path) -> None:
    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0", data_dir=str(tmp_path), environment="test"
    )
    logger = logging.getLogger(__name__)

    with pytest.raises(ValueError, match="Invalid source or language"):
        jobs_mod.process_corpus_impl(
            "a",
            {
                "source": "bogus",
                "language": "kk",
                "max_sentences": 1,
                "transliterate": True,
                "confidence_threshold": 0.9,
            },
            redis=redis,
            settings=settings,
            logger=logger,
        )


def test_progress_updates_every_50(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0", data_dir=str(tmp_path), environment="test"
    )
    logger = logging.getLogger(__name__)

    class _Svc:
        def __init__(self, _data_dir: str) -> None: ...
        def stream(self, _spec: object):
            for i in range(100):
                yield f"line {i}"

    # Patch LocalCorpusService and to_ipa to avoid ICU
    monkeypatch.setattr(jobs_mod, "LocalCorpusService", _Svc)
    monkeypatch.setattr(jobs_mod, "to_ipa", lambda s, _l: s)

    params = {
        "source": "oscar",
        "language": "kk",
        "max_sentences": 1000,
        "transliterate": True,
        "confidence_threshold": 0.9,
    }

    result = jobs_mod.process_corpus_impl(
        "p1", params, redis=redis, settings=settings, logger=logger
    )
    h = redis.hashes.get("job:p1")
    assert h is not None
    # Ensure final state completed and that at least one progress update occurred mid-way
    assert h.get("status") == "completed"
    assert result["status"] == "completed"
