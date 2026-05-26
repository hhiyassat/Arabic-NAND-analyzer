"""normalize.py — wrapper حَول دَوال التَّطبيع المَوجودَة.

تَوصيَة المُستَخدِم 2026-05-26 (Refactor Step B):
  re-export فَقَط، لا تَعديل في السُّلوك.

يَلُفّ:
  • linguistic_source_registry.strip_diac, strip_all, normalize, _strong_normalize
  • normalizer.py الأَصليّ (لَو وُجِد)
"""
from __future__ import annotations

# Re-export the existing functions WITHOUT modification
import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from linguistic_source_registry import (
    strip_diac as _strip_diac,
    strip_all as _strip_all,
    normalize as _normalize,
)

# _strong_normalize defined inline (same logic as in non_verb_override_gate)
def _strong_normalize_impl(s: str) -> str:
    return ((s or "")
            .replace("ٱ", "ا")
            .replace("آ", "ا")
            .replace("إ", "ا")
            .replace("أ", "ا")
            .replace("ؤ", "ا")
            .replace("ٰ", "ا"))


def strip_diacritics(s: str) -> str:
    """نَزع التَّشكيل (الحَرَكات + الشَّدَّة)."""
    return _strip_diac(s)


def strip_all_marks(s: str) -> str:
    """نَزع التَّشكيل + علامات التِّلاوة (sub-letters)."""
    return _strip_all(s)


def normalize_light(s: str) -> str:
    """تَطبيع خَفيف: ٱ → ا، آ → ا. يَحفَظ التَّشكيل + أ/إ."""
    return _normalize(s)


def normalize_strong(s: str) -> str:
    """تَطبيع شامِل: ٱ/آ/إ/أ/ٰ → ا، ؤ → ا."""
    return _strong_normalize_impl(s)


__all__ = [
    "strip_diacritics",
    "strip_all_marks",
    "normalize_light",
    "normalize_strong",
]
