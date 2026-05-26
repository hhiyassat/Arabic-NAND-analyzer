"""segmenter.py — wrapper حَول legacy segmenter.

تَوصيَة المُستَخدِم 2026-05-26 (Step D):
  re-export فَقَط. لا تَغيير في:
    • segmentation output
    • segmentation timing
    • rules

  الـimplementation الفِعليّ في clean_code/segmenter.py
"""
from __future__ import annotations

import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from segmenter import (  # noqa: F401
    SegmentationResult as _LegacySegmentationResult,
    segment as _legacy_segment,
)


def segment_token(token: str, *, normalize_input: bool = True):
    """يَلُفّ segmenter.segment().

    Returns:
      SegmentationResult (legacy object) — مَتاح لِلكود الجَديد وَالقَديم.
    """
    return _legacy_segment(token, normalize_input=normalize_input)


def segment_verse(verse_text: str, *, normalize_input: bool = True) -> list:
    """يُقَطِّع آيَة كامِلَة token-by-token.

    Returns: list[SegmentationResult]
    """
    if not verse_text:
        return []
    tokens = verse_text.split()
    return [segment_token(t, normalize_input=normalize_input) for t in tokens]


def to_legacy_segments(result) -> dict:
    """تَحويل SegmentationResult إلى dict (legacy API)."""
    if isinstance(result, dict):
        return result
    return result.to_dict()


def from_legacy_segments(d: dict):
    """يُعيد بِناء SegmentationResult مِن dict — اختياريّ، لا يُغَيِّر السُّلوك."""
    return _LegacySegmentationResult(
        original=d.get("original", ""),
        normalized=d.get("normalized", ""),
        prefixes=list(d.get("prefixes", [])),
        stem=d.get("stem", ""),
        suffixes=list(d.get("suffixes", [])),
        prefix_tags=list(d.get("prefix_tags", [])),
        suffix_tags=list(d.get("suffix_tags", [])),
        audit=list(d.get("audit", [])),
        confidence=d.get("confidence", 1.0),
    )


# Re-export the legacy class for backward compat
SegmentationResult = _LegacySegmentationResult


__all__ = [
    "segment_token", "segment_verse",
    "to_legacy_segments", "from_legacy_segments",
    "SegmentationResult",
]
