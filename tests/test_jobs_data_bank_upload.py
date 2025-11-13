from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

import api.jobs as jobs_mod
from api.config import Settings


class _RedisStub:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(
        self,
        name: str,
        key: str | None = None,
        value: str | None = None,
        mapping: dict[str, str] | None = None,
    ) -> int:
        cur = self.hashes.get(name, {})
        if mapping is not None:
            cur.update(mapping)
        elif key is not None and value is not None:
            cur[key] = value
        else:
            raise TypeError("hset expected mapping or key/value")
        self.hashes[name] = cur
        return 1


def _seed_processing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Svc:
        def __init__(self, _root: str) -> None: ...
        def stream(self, _spec: object) -> Iterator[str]:
            yield "hello"

    monkeypatch.setenv("TURKIC_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(jobs_mod, "LocalCorpusService", _Svc)
    monkeypatch.setattr(jobs_mod, "to_ipa", lambda s, _l: s)
    monkeypatch.setattr(
        jobs_mod,
        "ensure_corpus_file",
        lambda *a, **k: tmp_path / "corpus" / "oscar_kk.txt",
    )


def test_upload_success_records_file_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_processing(monkeypatch, tmp_path)

    # Stub httpx.post to emulate 201 response with JSON
    class _Resp:
        def __init__(self) -> None:
            self.status_code = 201
            self.text = '{"file_id":"deadbeef"}'

    monkeypatch.setattr("api.jobs.httpx.post", lambda *a, **k: _Resp())

    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        data_dir=str(tmp_path),
        environment="test",
        data_bank_api_url="http://db",
        data_bank_api_key="k",
    )
    logger = logging.getLogger(__name__)

    out = jobs_mod.process_corpus_impl(
        "jid1",
        {
            "source": "oscar",
            "language": "kk",
            "max_sentences": 1,
            "transliterate": True,
            "confidence_threshold": 0.9,
        },
        redis=redis,
        settings=settings,
        logger=logger,
    )
    assert out["status"] == "completed"
    h = redis.hashes.get("job:jid1", {})
    assert h.get("file_id") == "deadbeef"


@pytest.mark.parametrize("status", [400, 401, 403, 500])
def test_upload_failure_does_not_break_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int
) -> None:
    _seed_processing(monkeypatch, tmp_path)

    class _Resp:
        def __init__(self, s: int) -> None:
            self.status_code = s
            self.text = "{}"

    monkeypatch.setattr("api.jobs.httpx.post", lambda *a, **k: _Resp(status))

    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        data_dir=str(tmp_path),
        environment="test",
        data_bank_api_url="http://db",
        data_bank_api_key="k",
    )
    logger = logging.getLogger(__name__)

    out = jobs_mod.process_corpus_impl(
        "jid2",
        {
            "source": "oscar",
            "language": "kk",
            "max_sentences": 1,
            "transliterate": True,
            "confidence_threshold": 0.9,
        },
        redis=redis,
        settings=settings,
        logger=logger,
    )
    assert out["status"] == "completed"
    assert "file_id" not in redis.hashes.get("job:jid2", {})


def test_upload_2xx_missing_file_id_is_logged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_processing(monkeypatch, tmp_path)

    class _Resp:
        def __init__(self) -> None:
            self.status_code = 201
            self.text = "{}"  # JSON object without file_id

    monkeypatch.setattr("api.jobs.httpx.post", lambda *a, **k: _Resp())

    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        data_dir=str(tmp_path),
        environment="test",
        data_bank_api_url="http://db",
        data_bank_api_key="k",
    )
    logger = logging.getLogger(__name__)

    out = jobs_mod.process_corpus_impl(
        "jid3",
        {
            "source": "oscar",
            "language": "kk",
            "max_sentences": 1,
            "transliterate": True,
            "confidence_threshold": 0.9,
        },
        redis=redis,
        settings=settings,
        logger=logger,
    )
    assert out["status"] == "completed"
    assert "file_id" not in redis.hashes.get("job:jid3", {})


def test_upload_2xx_non_dict_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seed_processing(monkeypatch, tmp_path)

    class _Resp:
        def __init__(self) -> None:
            self.status_code = 200
            self.text = "[]"  # not a dict

    monkeypatch.setattr("api.jobs.httpx.post", lambda *a, **k: _Resp())

    redis = _RedisStub()
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        data_dir=str(tmp_path),
        environment="test",
        data_bank_api_url="http://db",
        data_bank_api_key="k",
    )
    logger = logging.getLogger(__name__)

    out = jobs_mod.process_corpus_impl(
        "jid4",
        {
            "source": "oscar",
            "language": "kk",
            "max_sentences": 1,
            "transliterate": True,
            "confidence_threshold": 0.9,
        },
        redis=redis,
        settings=settings,
        logger=logger,
    )
    assert out["status"] == "completed"
    assert "file_id" not in redis.hashes.get("job:jid4", {})
