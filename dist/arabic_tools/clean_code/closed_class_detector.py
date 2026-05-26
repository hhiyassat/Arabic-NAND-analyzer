"""closed_class_detector.py — Detect closed-class words (مبنيات و عوامل).

ARCHITECTURAL PRINCIPLE: closed-class words have NO derivational root.
They must be detected and EXCLUDED from the wazn/root extraction pipeline
BEFORE the wazn matcher is invoked. The matcher is for open-class words
only (verbs, nouns, derivatives).

This module is the SINGLE gatekeeper:
  - Input: a vocalized Arabic word
  - Output: True if closed-class (skip wazn matching), False if open-class

Sources of truth:
  1. new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl
       — words tagged with specific NO_ROOT labels (ISM_MAWSOOL, DAMEER, ...)
  2. new_arabic_analyzer/data/quran/i3rab_ref/i3rab_operators.csv
       — operators (عوامل)

NO data hardcoded here. Pure delegation to canonical sources.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Sibling import
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from wazn_data import load_closed_class_from_quran, DIACRITICS, HAMZA_VARIANTS

try:
    from normalizer import normalize_for_root_extraction
except ImportError:
    normalize_for_root_extraction = None


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# Lazy-loaded singletons
_CACHE: Optional[set[str]] = None
_AMBIGUOUS_EXACT: Optional[dict[str, set[str]]] = None  # stripped → {exact_forms}


def _build_set() -> set[str]:
    """Build the exclusion set from canonical sources.

    Each closed-class word is stored in TWO forms to handle hamzat-wasl
    variants:
      1. diacritic-stripped original (e.g., الذين)
      2. diacritic-stripped post-normalization (e.g., إلذين after hamzat wasl)
    """
    out = set()
    for w in load_closed_class_from_quran():
        out.add(_strip_diac(w))
        if normalize_for_root_extraction is not None:
            try:
                norm = normalize_for_root_extraction(w)
                out.add(_strip_diac(norm))
            except Exception:
                pass
    return out


def _build_ambiguous_exact() -> dict[str, set[str]]:
    """Per `closed_class_exceptions.csv` mode=exact_only:
    stripped → {exact_forms} requiring exact-diacritic match.
    """
    out: dict[str, set[str]] = {}
    try:
        from contracts_loader import load_closed_class_exceptions  # type: ignore
        for stripped, info in load_closed_class_exceptions().items():
            if info.get("mode") == "exact_only" and info.get("exact_form"):
                out.setdefault(stripped, set()).add(info["exact_form"])
    except Exception:
        pass
    return out


def is_closed_class(word: str) -> bool:
    """True if the word is closed-class (مبني/عامل — no derivational root).

    THIS IS THE GATE. Call this BEFORE any wazn/root extraction.

    Honors `closed_class_exceptions.csv` mode=exact_only: for forms whose
    stripped-form lookup is ambiguous (e.g., رُبَّ particle vs رَبّ noun),
    require exact-diacritic equality with the listed exact_form.
    """
    global _CACHE, _AMBIGUOUS_EXACT
    if _CACHE is None:
        _CACHE = _build_set()
    if _AMBIGUOUS_EXACT is None:
        _AMBIGUOUS_EXACT = _build_ambiguous_exact()

    plain = _strip_diac(word)

    # Exact-only override: stripped form is ambiguous, require exact match
    if plain in _AMBIGUOUS_EXACT:
        return word in _AMBIGUOUS_EXACT[plain]

    if plain in _CACHE:
        return True
    # Also try normalized form (handles input variation)
    if normalize_for_root_extraction is not None:
        try:
            norm_plain = _strip_diac(normalize_for_root_extraction(word))
            if norm_plain in _CACHE:
                return True
        except Exception:
            pass
    return False


def get_closed_class_set_size() -> int:
    """Diagnostic: how many closed-class entries are loaded."""
    global _CACHE
    if _CACHE is None:
        _CACHE = _build_set()
    return len(_CACHE)
