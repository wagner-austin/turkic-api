from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

import api.jobs as jobs_mod


class _RedisStub:
    def __init__(self) -> None:
        self.closed = False
        self.hashes: dict[str, dict[str, str]] = {}

    def close(self) -> None:
        self.closed = True

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        cur = self.hashes.get(key, {})
        cur.update(mapping)
        self.hashes[key] = cur
        return 1


def test_process_corpus_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Ensure data dir and data-bank config
    monkeypatch.setenv("TURKIC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TURKIC_DATA_BANK_API_URL", "http://db")
    monkeypatch.setenv("TURKIC_DATA_BANK_API_KEY", "k")

    # Stub Redis.from_url
    stub = _RedisStub()
    monkeypatch.setattr(
        jobs_mod,
        "Redis",
        type("R", (), {"from_url": staticmethod(lambda *a, **k: stub)}),
    )

    # Stub corpus and transliteration
    class _Svc:
        def __init__(self, _root: str) -> None: ...
        def stream(self, _spec: object) -> Iterator[str]:
            yield "hello"

    monkeypatch.setattr(jobs_mod, "LocalCorpusService", _Svc)
    monkeypatch.setattr(jobs_mod, "to_ipa", lambda s, _l: s)
    # Avoid network in test: pretend corpus file exists (single patch)
    monkeypatch.setattr(
        jobs_mod,
        "ensure_corpus_file",
        lambda *a, **k: tmp_path / "corpus" / "oscar_kk.txt",
    )

    class _Resp:
        def __init__(self) -> None:
            self.status_code = 201
            self.text = '{"file_id":"deadbeef"}'

    monkeypatch.setattr("api.jobs.httpx.post", lambda *a, **k: _Resp())

    params = {
        "source": "oscar",
        "language": "kk",
        "max_sentences": 1,
        "transliterate": True,
        "confidence_threshold": 0.9,
    }

    result = jobs_mod.process_corpus("e1", params)
    assert result["status"] == "completed"
    assert stub.closed is True
    out = tmp_path / "results" / "e1.txt"
    assert out.exists()
