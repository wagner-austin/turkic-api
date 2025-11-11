from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import requests

_MODEL_DIRNAME: Final[str] = "models"
_URL_218E: Final[str] = "https://dl.fbaipublicfiles.com/nllb/lid/lid218e.bin"
_URL_176: Final[str] = (
    "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def ensure_model_path(data_dir: str, prefer_218e: bool = True) -> Path:
    base = Path(data_dir) / _MODEL_DIRNAME
    path_218e = base / "lid218e.bin"
    path_176 = base / "lid.176.bin"
    if prefer_218e:
        if not path_218e.exists():
            _download(_URL_218E, path_218e)
        return path_218e
    if not path_176.exists():
        _download(_URL_176, path_176)
    return path_176


def _normalize_label(raw: str) -> str:
    label = raw.replace("__label__", "")
    # For 218e labels like "kaz_Cyrl" or "uzn_Latn"
    lang3 = label.split("_", 1)[0] if "_" in label else label
    mapping: dict[str, str] = {
        "kaz": "kk",
        "kir": "ky",
        "tur": "tr",
        "uzn": "uz",
        "uzs": "uz",
        "uig": "ug",
        "kk": "kk",
        "ky": "ky",
        "tr": "tr",
        "uz": "uz",
        "ug": "ug",
    }
    return mapping.get(lang3, lang3)


def build_lang_filter(
    target_lang: str, threshold: float, data_dir: str
) -> Callable[[str], bool]:
    """Return a predicate that keeps sentences matching target_lang above threshold.

    Loads a FastText language-ID model from $data_dir/models, downloading it
    if necessary. The filter returns True if the predicted language equals
    target_lang and the probability >= threshold.
    """
    model_path = ensure_model_path(data_dir, prefer_218e=True)

    # Import locally to keep it optional in dev environments.
    import fasttext

    model = fasttext.load_model(str(model_path))

    def _keep(text: str) -> bool:
        labels, probs = model.predict(text.replace("\n", " "), k=1)
        label = labels[0] if labels else ""
        prob = float(probs[0]) if probs else 0.0
        lang = _normalize_label(label)
        return lang == target_lang and prob >= threshold

    return _keep
