from __future__ import annotations

import bz2
import html
import os
import re
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

import requests

from core.langid import build_lang_script_filter
from core.models import ProcessSpec

# NOTE: We deliberately avoid Any/casts/ignores. External library usage is
# narrowed to typed access patterns.


_OSCAR_DATASET: Final[str] = "oscar-corpus/OSCAR-2301"


def stream_oscar(lang: str) -> Generator[str, None, None]:
    """Stream sentences from OSCAR via Hugging Face datasets (streaming mode).

    Requires the "datasets" package at runtime. Uses HF_TOKEN from environment
    if present for gated datasets.
    """
    # Import locally to keep import surface minimal and tests simple to stub.
    try:
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - exercised via tests with stub
        raise RuntimeError("datasets package is required for OSCAR streaming") from exc

    ds = load_dataset(
        _OSCAR_DATASET,
        lang,
        split="train",
        streaming=True,
        trust_remote_code=True,
        token=os.getenv("HF_TOKEN"),
    )
    for row in ds:
        if isinstance(row, dict):
            text_obj = row.get("text")
            if isinstance(text_obj, str):
                s = text_obj.strip()
                if s:
                    yield s


def stream_wikipedia_xml(lang: str) -> Generator[str, None, None]:
    """Stream sentences from Wikipedia XML dump for language "lang".

    Uses the latest dump and streams/decompresses on the fly.
    """
    dump_version = "latest"
    dump_name = f"{lang}wiki-{dump_version}-pages-articles.xml.bz2"
    url = f"https://dumps.wikimedia.org/{lang}wiki/{dump_version}/{dump_name}"
    with requests.get(url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        bz_stream = bz2.BZ2File(resp.raw)
        for _, elem in ET.iterparse(bz_stream, events=("end",)):
            if (elem.tag.endswith("}text") or elem.tag == "text") and elem.text:
                txt = html.unescape(re.sub(r"(?s)<.*?>", " ", elem.text))
                for s in re.split(r"[.!?]", txt):
                    s = s.strip()
                    if s:
                        yield s
                elem.clear()
            else:
                elem.clear()


def _write_lines(dest: Path, lines: Iterable[str], limit: int) -> int:
    count = 0
    with dest.open("w", encoding="utf-8") as fh:
        for s in lines:
            fh.write(s.replace("\n", " ").replace("\r", " ").strip() + "\n")
            count += 1
            if count >= limit:
                break
    return count


def ensure_corpus_file(
    spec: ProcessSpec, data_dir: str, script: str | None = None
) -> Path:
    """Ensure a local corpus file exists for the given spec.

    Creates data_dir/corpus/{source}_{language}.txt if missing by streaming
    from the configured remote source. Returns the path.
    """
    corpus_dir = Path(data_dir) / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    path = corpus_dir / f"{spec.source}_{spec.language}.txt"
    if path.exists():
        return path

    if spec.source == "oscar":
        stream = stream_oscar(spec.language)
    elif spec.source == "wikipedia":
        stream = stream_wikipedia_xml(spec.language)
    else:  # pragma: no cover - guarded by is_source in caller
        raise ValueError(f"Unsupported corpus source: {spec.source}")

    # Optionally filter by language/script using FastText when a positive
    # confidence threshold is provided OR when a script filter is requested.
    if spec.confidence_threshold > 0.0 or script is not None:
        keep = build_lang_script_filter(
            target_lang=spec.language,
            script=script,
            threshold=spec.confidence_threshold,
            data_dir=data_dir,
        )

        def _filtered(src: Iterable[str]) -> Iterable[str]:
            for s in src:
                if keep(s):
                    yield s

        source_iter: Iterable[str] = _filtered(stream)
    else:
        source_iter = stream

    written = _write_lines(path, source_iter, spec.max_sentences)
    if written == 0:
        # Remove zero-byte files to avoid confusion
        from contextlib import suppress

        with suppress(Exception):
            path.unlink(missing_ok=True)
        raise RuntimeError("No sentences were written for the requested corpus")
    # Touch mtime for traceability
    path.touch(exist_ok=True)
    return path
