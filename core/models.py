from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeGuard

Source = Literal["oscar", "wikipedia"]
Language = Literal["kk", "ky", "uz", "tr", "ug"]


@dataclass(frozen=True)
class ProcessSpec:
    source: Source
    language: Language
    max_sentences: int
    transliterate: bool
    confidence_threshold: float


def is_source(value: str) -> TypeGuard[Source]:
    return value in ("oscar", "wikipedia")


def is_language(value: str) -> TypeGuard[Language]:
    return value in ("kk", "ky", "uz", "tr", "ug")
