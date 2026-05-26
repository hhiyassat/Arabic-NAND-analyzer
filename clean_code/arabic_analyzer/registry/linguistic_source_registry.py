"""linguistic_source_registry.py — wrapper.

تَوصيَة المُستَخدِم 2026-05-26 (Step B):
  re-export فَقَط لِلوصول مِن المُجَلَّد الجَديد.
  لا تَعديل في:
    • candidate ordering
    • certainty logic
    • cross-source conflict detection
    • shadda parity
    • compound lookup

  الـimplementation تَبقى في clean_code/linguistic_source_registry.py
"""
from __future__ import annotations

import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# Re-export EVERYTHING from the existing module verbatim
from linguistic_source_registry import (  # noqa: F401
    Entry,
    build_registry,
    resolve,
    resolve_strict,
    resolve_compound,
    conflict_audit,
    save_registry,
    _STRIPPABLE_PREFIXES,
    strip_diac, strip_all, normalize,
)

__all__ = [
    "Entry",
    "build_registry", "resolve", "resolve_strict", "resolve_compound",
    "conflict_audit", "save_registry",
]
