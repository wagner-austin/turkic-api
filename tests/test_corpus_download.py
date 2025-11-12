from __future__ import annotations

import io
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest

from core.corpus_download import ensure_corpus_file, stream_oscar, stream_wikipedia_xml
from core.models import ProcessSpec


def _gen_lines(lines: list[str]) -> Iterator[str]:
    yield from lines


def test_ensure_corpus_file_writes_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub stream_oscar to avoid network
    monkeypatch.setattr(
        "core.corpus_download.stream_oscar",
        lambda _lang: _gen_lines(["a", "b", "", "c"]),
    )
    spec = ProcessSpec(
        source="oscar",
        language="kk",
        max_sentences=2,
        transliterate=True,
        confidence_threshold=0.0,
    )
    path = ensure_corpus_file(spec, str(tmp_path))
    assert path.exists()
    assert path.read_text(encoding="utf-8").strip().splitlines() == ["a", "b"]
    # Second call should early-return without rewriting
    same = ensure_corpus_file(spec, str(tmp_path))
    assert same == path


def test_ensure_corpus_file_zero_written_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub wikipedia stream to yield no lines
    monkeypatch.setattr(
        "core.corpus_download.stream_wikipedia_xml", lambda _lang: _gen_lines([])
    )
    spec = ProcessSpec(
        source="wikipedia",
        language="kk",
        max_sentences=10,
        transliterate=True,
        confidence_threshold=0.0,
    )
    with pytest.raises(RuntimeError, match="No sentences"):
        ensure_corpus_file(spec, str(tmp_path))
    out = tmp_path / "corpus" / "wikipedia_kk.txt"
    assert not out.exists()


def test_stream_wikipedia_xml_parses_sentences(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create a minimal XML with <text> content and compress via bz2
    xml = b"<page><revision><text>One. Two! Three?</text></revision></page>"
    import bz2

    raw = io.BytesIO(bz2.compress(xml))

    class _Resp:
        def __init__(self) -> None:
            self.raw = raw

        def raise_for_status(self) -> None:
            return None

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr("requests.get", lambda *_a, **_k: _Resp())

    out = list(stream_wikipedia_xml("kk"))
    # Empty splits removed; punctuation-split applied
    assert out == ["One", "Two", "Three"]


def test_stream_oscar_uses_datasets(monkeypatch: pytest.MonkeyPatch) -> None:
    # Provide a dummy datasets module with load_dataset
    class _DS:
        def __iter__(self) -> Iterator[object]:
            yield {"text": "x"}
            yield {"text": "  y  "}
            yield {"text": ""}
            yield {"text": 99}
            yield 123  # non-dict row to cover branch

    class _Mod(ModuleType):
        @staticmethod
        def load_dataset(*_a: object, **_k: object) -> _DS:
            return _DS()

    sys.modules["datasets"] = _Mod("datasets")
    try:
        out = list(stream_oscar("kk"))
        assert out == ["x", "y"]
    finally:
        del sys.modules["datasets"]


def test_ensure_corpus_file_applies_lang_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub stream to emit mixed sentences
    monkeypatch.setattr(
        "core.corpus_download.stream_oscar",
        lambda _lang: _gen_lines(["keep one", "drop x", "keep two"]),
    )
    # Stub filter to keep sentences containing 'keep'
    monkeypatch.setattr(
        "core.corpus_download.build_lang_script_filter",
        lambda target_lang, script, threshold, data_dir: (lambda s: "keep" in s),
    )
    spec = ProcessSpec(
        source="oscar",
        language="kk",
        max_sentences=10,
        transliterate=True,
        confidence_threshold=0.9,
    )
    path = ensure_corpus_file(spec, str(tmp_path))
    assert path.exists()
    assert path.read_text(encoding="utf-8").splitlines() == ["keep one", "keep two"]


def test_ensure_corpus_file_applies_script_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub stream to emit mixed sentences
    monkeypatch.setattr(
        "core.corpus_download.stream_oscar",
        lambda _lang: _gen_lines(["CYRL hello", "LATN world", "LATN again"]),
    )

    # Keep only 'Latn' script sentences
    def _builder(
        target_lang: str, script: str | None, threshold: float, data_dir: str
    ) -> Callable[[str], bool]:
        assert target_lang == "kk"
        assert script == "Latn"
        assert threshold == 0.0

        def _keep(s: str) -> bool:
            return s.startswith("LATN ")

        return _keep

    monkeypatch.setattr(
        "core.corpus_download.build_lang_script_filter",
        _builder,
    )
    spec = ProcessSpec(
        source="oscar",
        language="kk",
        max_sentences=10,
        transliterate=True,
        confidence_threshold=0.0,
    )
    path = ensure_corpus_file(spec, str(tmp_path), script="Latn")
    assert path.exists()
    assert path.read_text(encoding="utf-8").splitlines() == ["LATN world", "LATN again"]
