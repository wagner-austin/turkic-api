from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

import core.langid as lid


def test_download_writes_only_nonempty_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "models" / "x.bin"

    class _Resp:
        def __init__(self) -> None:
            self._chunks = [b"", b"abc", b"", b"def"]
            self._idx = 0

        def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
            yield from self._chunks

        def raise_for_status(self) -> None:
            return None

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr("core.langid.requests.get", lambda *_a, **_k: _Resp())
    lid._download("http://example/x", dest)
    assert dest.read_bytes() == b"abcdef"


def test_ensure_model_path_218e_downloads_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _fake_download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"bin")

    monkeypatch.setattr(lid, "_download", _fake_download)
    out = lid.ensure_model_path(str(tmp_path), prefer_218e=True)
    assert out.name == "lid218e.bin"
    assert out.exists()
    assert calls != []
    assert "lid218e" in calls[0]


def test_ensure_model_path_218e_existing_no_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "models" / "lid218e.bin"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"bin")

    def _boom(_u: str, _d: Path) -> None:  # pragma: no cover - should not be called
        raise AssertionError("download should not be called")

    monkeypatch.setattr(lid, "_download", _boom)
    out = lid.ensure_model_path(str(tmp_path), prefer_218e=True)
    assert out == p


def test_ensure_model_path_176_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _fake_download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"bin")

    monkeypatch.setattr(lid, "_download", _fake_download)
    out = lid.ensure_model_path(str(tmp_path), prefer_218e=False)
    assert out.name == "lid.176.bin"
    assert calls != []
    assert "lid.176" in calls[0]

    # Call again after file exists: should not download
    calls.clear()
    out2 = lid.ensure_model_path(str(tmp_path), prefer_218e=False)
    assert out2 == out
    assert calls == []


def test_build_lang_filter_with_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Stub ensure_model_path to avoid filesystem
    monkeypatch.setattr(
        lid, "ensure_model_path", lambda *_a, **_k: tmp_path / "models" / "m.bin"
    )

    class _Model:
        def predict(self, text: str, k: int = 1) -> tuple[list[str], list[float]]:
            # Return variants to hit mapping logic: __label__kk and kaz_Cyrl
            if "cyrl" in text.lower():
                return (["__label__kaz_Cyrl"], [0.95])
            return (["__label__kk"], [0.80])

    class _FastText(ModuleType):
        @staticmethod
        def load_model(_path: str) -> _Model:
            return _Model()

    sys.modules["fasttext"] = _FastText("fasttext")
    try:
        keep = lid.build_lang_filter(
            target_lang="kk", threshold=0.90, data_dir=str(tmp_path)
        )
        assert keep("foo cyrl") is True  # kaz_Cyrl maps to kk
        assert keep("bar") is False  # prob below threshold
    finally:
        del sys.modules["fasttext"]


def test_build_lang_script_filter_match_and_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Avoid filesystem
    monkeypatch.setattr(
        lid, "ensure_model_path", lambda *_a, **_k: tmp_path / "models" / "m.bin"
    )

    class _Model:
        def predict(self, text: str, k: int = 1) -> tuple[list[str], list[float]]:
            t = text.lower()
            if "latn" in t:
                return (["__label__kaz_Latn"], [0.99])
            if "cyrl" in t:
                return (["__label__kaz_Cyrl"], [0.99])
            return (["__label__eng"], [0.99])

    class _FastText(ModuleType):
        @staticmethod
        def load_model(_path: str) -> _Model:
            return _Model()

    sys.modules["fasttext"] = _FastText("fasttext")
    try:
        # Script normalized from lower-case
        keep = lid.build_lang_script_filter(
            target_lang="kk", script="latn", threshold=0.5, data_dir=str(tmp_path)
        )
        assert keep("text latn") is True
        assert keep("text cyrl") is False  # script mismatch -> return False
        # Lang mismatch -> return False
        assert keep("english") is False
        # No script filter
        keep2 = lid.build_lang_script_filter(
            target_lang="kk", script=None, threshold=0.5, data_dir=str(tmp_path)
        )
        assert keep2("text latn") is True
    finally:
        del sys.modules["fasttext"]


def test_build_lang_script_filter_blank_script_treated_as_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        lid, "ensure_model_path", lambda *_a, **_k: tmp_path / "models" / "m.bin"
    )

    class _Model:
        def predict(self, text: str, k: int = 1) -> tuple[list[str], list[float]]:
            return (["__label__kaz_Latn"], [0.99])

    class _FastText(ModuleType):
        @staticmethod
        def load_model(_path: str) -> _Model:
            return _Model()

    sys.modules["fasttext"] = _FastText("fasttext")
    try:
        keep = lid.build_lang_script_filter(
            target_lang="kk", script="   ", threshold=0.5, data_dir=str(tmp_path)
        )
        # Blank script should be treated as None (no script gating)
        assert keep("anything") is True
    finally:
        del sys.modules["fasttext"]
