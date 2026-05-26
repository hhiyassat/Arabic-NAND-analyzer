"""pre_segmentation_lookup.py — البَحث في registry قَبل segmentation.

تَوصيَة المُستَخدِم 2026-05-26 (Step B):
  re-export wrapper فَقَط. لا تَغيير في السُّلوك.

الـimplementation الفِعليّ في:
  • linguistic_source_registry.resolve_strict (Phase 2 + 2.5 + 3.1)
  • i3rab_engine.layer1 — Step -1 (يَستَدعي resolve_strict)

هَذا الـwrapper يُقَدِّم API نَظيف لِلكود الجَديد:
  lookup_before_segmentation(token) → dict (registry_strict_result)

الكود القَديم في layer1.py لا يَتَغَيَّر — هَذا فَقَط alias.
"""
from __future__ import annotations

import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from linguistic_source_registry import (
    resolve_strict as _resolve_strict,
    resolve_compound as _resolve_compound,
    build_registry as _build_registry,
)


def lookup_before_segmentation(token: str, registry: dict | None = None) -> dict:
    """يَبحَث في registry قَبل segmentation.

    Returns:
      نَفس بِنيَة resolve_strict — لا تَغيير:
        {
          "surface", "found", "candidates", "certainty",
          "requires_context", "source", "matched_entries", "blockers"
        }

    قَواعِد Phase 3 (مَحفوظَة كَما هي):
      • exact-tashkīl match يَستَخدِم original_candidates (قَبل cross-merge)
      • Certificate يَتَطَلَّب 4 شُروط (priority>=8، single class، no conflict، no ctx)
      • compound fallback لِـ لِمَاذَا = لِ + ما + ذَا
      • plain-match مَع shadda parity (هَمَّ ≠ هُمْ)
    """
    return _resolve_strict(token, registry)


def lookup_compound(token: str, registry: dict | None = None) -> dict | None:
    """يَبحَث عَن compound (مَع prefix stripping)."""
    return _resolve_compound(token, registry)


def get_shared_registry() -> dict:
    """يُرجِع registry مُشتَرَك (lazy-built singleton).

    لا يُعيد بِناءَه في كُلّ مَرَّة — يُحَمَّل مَرَّة واحِدَة في الذاكِرَة.
    """
    global _SHARED_REGISTRY
    if "_SHARED_REGISTRY" not in globals() or _SHARED_REGISTRY is None:
        _SHARED_REGISTRY = _build_registry()
    return _SHARED_REGISTRY


_SHARED_REGISTRY: dict | None = None


__all__ = [
    "lookup_before_segmentation",
    "lookup_compound",
    "get_shared_registry",
]
