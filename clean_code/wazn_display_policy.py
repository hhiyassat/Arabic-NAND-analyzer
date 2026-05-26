"""wazn_display_policy.py — Canonical vs surface wazn after alignment.

Post-processing only; does not change root extraction or closed-class gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from root_by_alignment import AlignmentResult, _strip_diac

_HERE = Path(__file__).resolve().parent

# Teaching canonical for Form VIII (defective / surface ى endings)
CANONICAL_FORM_VIII = "افْتَعَل"

# Preferred pattern for elided فَعْلَان (رَحْمَن، شَيْطَان، …)
CANONICAL_FA3LAN = "فَعْلَان"

# Short wazn patterns that may wrongly win over فَعْلَان on 4-letter stems
_SHORT_NOUN_WAZN = frozenset({"فَعْل", "فعل", "فَعَل", "فعل"})  # canonical

_DIVINE_STEMS = frozenset({"رحمن", "رحمان", "الرحمن"})  # canonical


@dataclass
class RefinedWaznDisplay:
    """Display-oriented wazn pair after alignment."""

    canonical_wazn: str
    surface_wazn: str
    root: str
    proper_name: bool = False
    divine_name: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def has_canonical_split(self) -> bool:
        return (
            self.canonical_wazn
            and self.surface_wazn
            and self.canonical_wazn != self.surface_wazn
        )


def _load_proper_noun_stems() -> set[str]:
    path = _HERE / "data" / "masaq_proper_nouns.csv"
    stems: set[str] = set()
    if not path.is_file():
        return stems
    import csv

    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or row.get("Word") or "").strip()
            if w:
                stems.add(_strip_diac(w))
    return stems


_PROPER_NOUN_STEMS: Optional[set[str]] = None


def _proper_noun_stems() -> set[str]:
    global _PROPER_NOUN_STEMS
    if _PROPER_NOUN_STEMS is None:
        _PROPER_NOUN_STEMS = _load_proper_noun_stems()
    return _PROPER_NOUN_STEMS


def _stem_plain(word: str, stem: str | None = None) -> str:
    if stem:
        return _strip_diac(stem)
    return _strip_diac(word)


def _looks_fa3lan_elided(stem_plain: str) -> bool:
    """True for Quranic فَعْلَان with elided alef (e.g. رحمن not رحمان)."""
    s = stem_plain
    if len(s) < 4:
        return False
    if s.endswith("ان") or s.endswith("انُ") or s.endswith("انِ"):
        return True
    # 4+ letter stem ending in ن (رحمن، شيطان، …) — not ة
    if s.endswith("ن") and not s.endswith("ة"):
        consonants = re.sub(r"[^ء-ي]", "", s)
        return len(consonants) >= 4
    return False


def _is_form_viii_word(word_plain: str, aligned_wazn_plain: str) -> bool:
    if word_plain.startswith(("اس", "است", "إست", "أست")):
        return True
    w = aligned_wazn_plain
    return "فتع" in w or "فْتَع" in w


def _canonicalize_form_viii(
    word: str, result: AlignmentResult
) -> Optional[RefinedWaznDisplay]:
    word_plain = _strip_diac(word)
    wazn_plain = _strip_diac(result.wazn)
    if not _is_form_viii_word(word_plain, wazn_plain):
        return None
    return RefinedWaznDisplay(
        canonical_wazn=CANONICAL_FORM_VIII,
        surface_wazn=result.wazn,
        root=result.root,
        notes=["form_viii: canonical باب افْتَعَل، surface = alignment"],
    )


def _prefer_fa3lan(
    word: str,
    stem_plain: str,
    result: AlignmentResult,
) -> Optional[RefinedWaznDisplay]:
    if result.wazn not in _SHORT_NOUN_WAZN:
        return None
    if not _looks_fa3lan_elided(stem_plain):
        return None
    divine = stem_plain in _DIVINE_STEMS or stem_plain.endswith("رحمن")
    proper = divine or stem_plain in _proper_noun_stems()
    notes = ["fa3lan_gate: stem looks فَعْلَان (elided alef); do not reduce to فَعْل"]
    if divine:
        notes.append("divine_name convention")
    return RefinedWaznDisplay(
        canonical_wazn=CANONICAL_FA3LAN,
        surface_wazn=result.wazn,
        root=result.root,
        proper_name=proper,
        divine_name=divine,
        notes=notes,
    )


def refine_wazn_display(
    word: str,
    result: AlignmentResult,
    *,
    stem: str | None = None,
) -> RefinedWaznDisplay:
    """Map raw alignment to canonical + surface display pair."""
    stem_plain = _stem_plain(word, stem)

    for rule in (_canonicalize_form_viii,):
        refined = rule(word, result)
        if refined is not None:
            return refined

    fa3lan = _prefer_fa3lan(word, stem_plain, result)
    if fa3lan is not None:
        return fa3lan

    return RefinedWaznDisplay(
        canonical_wazn=result.wazn,
        surface_wazn=result.wazn,
        root=result.root,
    )
