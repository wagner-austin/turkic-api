from __future__ import annotations

import unicodedata as ud
from functools import lru_cache
from pathlib import Path
from typing import Protocol

_RULE_DIR = Path(__file__).with_suffix("").parent / "rules"


@lru_cache
def get_supported_languages() -> dict[str, list[str]]:
    supported: dict[str, list[str]] = {}
    for rule_file in _RULE_DIR.glob("*.rules"):
        filename = rule_file.stem
        if "_" in filename:
            lang, fmt = filename.split("_", 1)
            if fmt in {"lat2023", "lat"}:
                fmt = "latin"
            if lang not in supported:
                supported[lang] = []
            if fmt not in supported[lang]:
                supported[lang].append(fmt)
    return supported


class Transliterator(Protocol):
    def transliterate(self, text: str) -> str: ...


@lru_cache
def _icu_trans(name: str) -> Transliterator:
    import icu  # local import to avoid hard dependency at module import time

    txt = (_RULE_DIR / name).read_text(encoding="utf8")
    t: Transliterator = icu.Transliterator.createFromRules(name, txt, 0)
    return t


def to_latin(text: str, lang: str, include_arabic: bool = False) -> str:
    supported = get_supported_languages()
    if lang not in supported or "latin" not in supported[lang]:
        available = [code for code, fmts in supported.items() if "latin" in fmts]
        raise ValueError(
            f"Latin transliteration not supported for '{lang}'. "
            f"Available languages: {', '.join(sorted(available))}"
        )
    possible_rules = [
        f"{lang}_lat2023.rules",
        f"{lang}_lat.rules",
        f"{lang}_latin.rules",
    ]
    rule_file: str | None = None
    for rule in possible_rules:
        if (_RULE_DIR / rule).exists():
            rule_file = rule
            break
    if not rule_file:
        raise ValueError(f"No Latin rules file found for language '{lang}'")
    trans = _icu_trans(rule_file)
    if include_arabic:
        ar = _icu_trans("ar_lat.rules")
        text = ar.transliterate(text)
    out = trans.transliterate(text)
    return ud.normalize("NFC", out)


def to_ipa(text: str, lang: str) -> str:
    supported = get_supported_languages()
    if lang not in supported or "ipa" not in supported[lang]:
        available = [code for code, fmts in supported.items() if "ipa" in fmts]
        raise ValueError(
            f"IPA transliteration not supported for '{lang}'. "
            f"Available languages: {', '.join(sorted(available))}"
        )
    rule_file = f"{lang}_ipa.rules"
    if not (_RULE_DIR / rule_file).exists():
        raise ValueError(f"IPA rules file not found for language '{lang}'")
    trans = _icu_trans(rule_file)
    return ud.normalize("NFC", trans.transliterate(text))
