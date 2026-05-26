"""Adapter for salehan/Models_gpt52 Arabic diacritization (GPT-52).

If input is not sufficiently vocalized, run the transformer model first,
then pass the diacritized text to the rest of the architecture pipeline.

Path resolution (first match):
  env GPT52_DIR
  <fractal>/salehan/Models_gpt52
"""

from __future__ import annotations

import os
import pathlib
import sys
from typing import Any

from .tokenize import (
    count_arabic_letters,
    has_sufficient_diacritics,
    normalize_input_text,
)

_ENV = "GPT52_DIR"
_FRACTAL_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_GPT52 = _FRACTAL_ROOT / "salehan" / "Models_gpt52"

_predictor: Any = False  # False = not tried; None = unavailable


def _gpt52_dir(explicit: pathlib.Path | None = None) -> pathlib.Path | None:
    if explicit is not None:
        p = explicit.expanduser().resolve()
        return p if p.is_dir() else None
    env = os.environ.get(_ENV)
    if env:
        p = pathlib.Path(env).expanduser().resolve()
        return p if p.is_dir() else None
    return _DEFAULT_GPT52 if _DEFAULT_GPT52.is_dir() else None


def _load_predictor(gpt52_dir: pathlib.Path | None = None) -> Any | None:
    global _predictor
    if _predictor is not False and _predictor is not None:
        return _predictor
    if _predictor is False and gpt52_dir is None:
        # Already failed with default path; allow retry only if explicit dir given
        pass

    gpt52 = _gpt52_dir(gpt52_dir)
    if gpt52 is None:
        _predictor = None
        return None

    root = str(gpt52)
    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        from src.services.predictor import ModelPredictor  # type: ignore

        word_pt = (
            gpt52
            / "src"
            / "models"
            / "Word_level_scheduled"
            / "runs"
            / "teacher"
            / "best.pt"
        )
        char_pt = (
            gpt52
            / "src"
            / "models"
            / "Char_level_default"
            / "runs"
            / "teacher"
            / "best.pt"
        )
        model_path = word_pt if word_pt.exists() else (char_pt if char_pt.exists() else None)
        if model_path is None:
            _predictor = None
            return None

        _predictor = ModelPredictor(str(model_path))
        return _predictor
    except Exception:
        _predictor = None
        return None


def diacritize(text: str, *, gpt52_dir: pathlib.Path | None = None) -> str | None:
    """Return vocalized Arabic text, or None if the model is unavailable."""
    if not text or not text.strip():
        return None

    predictor = _load_predictor(gpt52_dir)
    if predictor is None:
        return None

    try:
        from src.core.normalization import normalize_arabic  # type: ignore

        clean = normalize_arabic(text)
        vocalized, _ids, _map = predictor.predict(clean)
        return vocalized if vocalized else None
    except Exception:
        return None


def diacritizer_available(gpt52_dir: pathlib.Path | None = None) -> bool:
    return _load_predictor(gpt52_dir) is not None


def prepare_vocalized_text(
    raw_text: str,
    *,
    gpt52_dir: pathlib.Path | None = None,
    skip_diacritize: bool = False,
    force_diacritize: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    Return text ready for analysis and a metadata block.

    If input lacks tashkil, runs Models_gpt52 and replaces text with vocalized form.
    """
    cleaned = normalize_input_text(raw_text)
    meta: dict[str, Any] = {
        "source_dir": str(_gpt52_dir(gpt52_dir) or ""),
        "available": diacritizer_available(gpt52_dir),
        "text_raw": raw_text,
        "text_cleaned": cleaned,
        "had_sufficient_diacritics": has_sufficient_diacritics(cleaned),
        "requested": False,
        "applied": False,
        "skipped": skip_diacritize,
        "forced": force_diacritize,
        "text_vocalized": cleaned,
        "error": None,
    }

    if skip_diacritize:
        return cleaned, meta

    needs = force_diacritize or not meta["had_sufficient_diacritics"]
    if not needs:
        return cleaned, meta

    meta["requested"] = True
    vocalized = diacritize(cleaned, gpt52_dir=gpt52_dir)
    if vocalized:
        meta["applied"] = True
        meta["text_vocalized"] = vocalized
        return vocalized, meta

    meta["error"] = "diacritizer unavailable or prediction failed"
    return cleaned, meta
