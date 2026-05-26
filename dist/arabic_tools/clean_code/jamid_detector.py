"""jamid_detector.py — Detect jawamid (essence nouns: السماء، الأرض، الجبل، ...).

ARCHITECTURAL PRINCIPLE: jawamid (الجوامد) are essence-nouns that name a thing
in itself, not forms derived from a verbal root via a wazn template. They have
NO derivational root in the wazn/مشتق sense.

  - السَّمَاء (sky)              — geonym, no derived root
  - الْأَرْض (earth)              — geonym, no derived root
  - الْبَحْر (sea)                — geonym, no derived root
  - الْجَبَل (mountain)            — geonym, no derived root
  - الشَّمْس (sun), الْقَمَر (moon) — astroyms, no derived root

This module is THE GATE for jawamid:
  - Input: a vocalized Arabic word (possibly with prefixes/suffixes)
  - Output: True if jamid (skip wazn matching), False otherwise

Sources of truth:
  MASAQ.csv → rows where Morph_Tag = NOUN_CONCRETE on the Stem segment.
  We index by Without_Diacritics (the full surface form) so that callers
  receiving السَّمَاوَاتِ from real text get matched directly.

NO data hardcoded here. Pure delegation to canonical source.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from wazn_data import load_jamid_from_masaq, DIACRITICS

try:
    from normalizer import normalize_for_root_extraction
except ImportError:
    normalize_for_root_extraction = None


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# Lazy-loaded singletons:
#   _CACHE_VOC = full vocalized jamid forms (e.g., "كُتُبٌ"). Exact match.
#   _CACHE_AMB = stripped forms that are UNAMBIGUOUSLY jamid in MASAQ
#                (no other Stem tag shares that consonant skeleton). Safe
#                to match diacritic-blind.
_CACHE_VOC: Optional[set[str]] = None
_CACHE_AMB: Optional[set[str]] = None


def _ensure_loaded() -> None:
    global _CACHE_VOC, _CACHE_AMB
    if _CACHE_VOC is not None and _CACHE_AMB is not None:
        return
    vocalized, unambiguous_stripped = load_jamid_from_masaq()
    # Augment vocalized set with post-normalization equivalents so callers
    # whose input went through normalize_for_root_extraction still match.
    voc_expanded: set[str] = set(vocalized)
    if normalize_for_root_extraction is not None:
        for w in vocalized:
            try:
                voc_expanded.add(normalize_for_root_extraction(w))
            except Exception:
                pass
    _CACHE_VOC = voc_expanded
    _CACHE_AMB = unambiguous_stripped


def is_jamid(word: str) -> bool:
    """True if the word is a jamid (essence-noun — no derivational root).

    Match plan (in order, two-tier):
      1. EXACT vocalized match against MASAQ's NOUN_CONCRETE surfaces.
         (Catches السَّمَاوَاتِ, الْأَرْض, الشَّمْس, ...)
      2. STRIPPED match against the unambiguous-stripped set only.
         (Catches diacritic-light input safely, while NEVER firing for
         homographs like ``كتب`` that double as a verb.)

    THIS IS THE JAMID GATE. Call this BEFORE the wazn matcher, and AFTER
    the closed-class gate.
    """
    _ensure_loaded()
    assert _CACHE_VOC is not None and _CACHE_AMB is not None
    # Tier 1: exact vocalized
    if word in _CACHE_VOC:
        return True
    if normalize_for_root_extraction is not None:
        try:
            if normalize_for_root_extraction(word) in _CACHE_VOC:
                return True
        except Exception:
            pass
    # Tier 2: stripped (only if unambiguous in MASAQ)
    plain = _strip_diac(word)
    if plain in _CACHE_AMB:
        return True
    if normalize_for_root_extraction is not None:
        try:
            norm_plain = _strip_diac(normalize_for_root_extraction(word))
            if norm_plain in _CACHE_AMB:
                return True
        except Exception:
            pass
    return False


def get_jamid_set_size() -> tuple[int, int]:
    """Diagnostic: (vocalized count, unambiguous-stripped count)."""
    _ensure_loaded()
    assert _CACHE_VOC is not None and _CACHE_AMB is not None
    return len(_CACHE_VOC), len(_CACHE_AMB)


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    voc, amb = get_jamid_set_size()
    print(f"Jamid sets: vocalized={voc}, unambiguous_stripped={amb}")
    print()
    print("--- Expected JAMID ---")
    for w in ["السَّمَاء", "السَّمَاوَات", "الْأَرْض", "أَرْضِ",
              "الْبَحْر", "الْجَبَل", "النَّار", "الْمَاء",
              "الشَّمْس", "النَّجْم", "الْكِتَاب"]:
        r = is_jamid(w)
        mark = "✓" if r else "✗"
        print(f"  {mark} {w}: is_jamid={r}")
    print()
    print("--- Expected NOT JAMID (derived) ---")
    for w in ["كَتَبَ", "يَكْتُبُ", "كَاتِب", "مَكْتُوب",
              "اسْتَخْرَجَ", "آمَنُوا", "قَالُوا"]:
        r = is_jamid(w)
        mark = "✓" if not r else "✗"
        print(f"  {mark} {w}: is_jamid={r}")
