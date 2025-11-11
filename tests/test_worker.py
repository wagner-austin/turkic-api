from __future__ import annotations

import logging
from pathlib import Path

import pytest

from api.config import Settings
from api.jobs import process_corpus_impl


class _RedisStub:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        # Merge mapping into existing hash to mimic Redis semantics
        cur = self.hashes.get(key, {})
        cur.update(mapping)
        self.hashes[key] = cur
        return 1


def test_process_corpus_impl_creates_file_and_updates_status(tmp_path: Path) -> None:
    pytest.importorskip("icu")
    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0", data_dir=str(tmp_path), environment="test"
    )
    logger = logging.getLogger(__name__)

    # Seed a local corpus file matching spec: oscar_kk.txt
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(exist_ok=True)
    (corpus_dir / "oscar_kk.txt").write_text("Қазақстан\n", encoding="utf-8")
    params = {
        "source": "oscar",
        "language": "kk",
        "max_sentences": 10,
        "transliterate": True,
        "confidence_threshold": 0.95,
    }
    result = process_corpus_impl(
        "w1", params, redis=redis, settings=settings, logger=logger
    )

    # File exists
    out = tmp_path / "results" / "w1.txt"
    assert out.exists()
    text = out.read_text(encoding="utf-8").strip()
    assert text  # at least one line produced

    # Redis status updated
    h = redis.hashes.get("job:w1")
    assert h is not None
    assert h.get("status") == "completed"
    assert h.get("progress") == "100"
    assert result["status"] == "completed"
