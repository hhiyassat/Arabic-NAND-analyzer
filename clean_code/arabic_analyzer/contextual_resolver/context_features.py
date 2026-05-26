"""context_features.py — استِخراج إِشارات سِياقيَّة (Phase 4).

يَفحَص prev_tokens / next_tokens ويُرجِع dict مِن feature → bool/value.

كُلّ الـheuristics rule-based، لا ML، لا inline data ضِخمَة.
"""
from __future__ import annotations

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Normalize helpers
# ─────────────────────────────────────────────────────────────
_DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭ]")
_ALEF_VARIANTS = re.compile(r"[ٱآأإ]")


def _strip(s: str) -> str:
    """تَطبيع خَفيف — حَذف التَّشكيل + alef variants → ا."""
    s = _DIACRITICS.sub("", s or "")
    s = _ALEF_VARIANTS.sub("ا", s)
    return s


# ─────────────────────────────────────────────────────────────
# Verb-shape heuristics
# ─────────────────────────────────────────────────────────────
# Present verb prefixes (مُضارِع)
_PRESENT_PREFIXES = ("يَ", "تَ", "نَ", "أَ", "ي", "ت", "ن", "أ", "ٱ")

# Question verbs (preceded interrogative context)
_QUESTION_VERBS = {
    "قال", "قَالَ", "قُل", "قُلْ", "يَقُولُ", "يَقول",
    "سَأَل", "سَأَلَ", "سَأَلَك", "يَسأَل", "يَسأَلُك", "يَسأَلونَ",
    "أَسأَلُ",
}


def _looks_like_present_verb(tok: str) -> bool:
    """heuristic: يَبدأ بِـ ي/ت/ن/أ + لَيس نون اسم مَوصول."""
    if not tok or len(tok) < 3:
        return False
    bare = _strip(tok)
    if not bare:
        return False
    # exclude common nouns starting with يَ/تَ
    if bare in ("يوم", "يا", "يومئذ"):
        return False
    return tok.startswith(_PRESENT_PREFIXES)


def _looks_like_past_verb(tok: str) -> bool:
    """heuristic: pattern faعَلَ/faعِلَ (3 letters, fatha endings)."""
    if not tok or len(tok) < 3:
        return False
    bare = _strip(tok)
    if len(bare) < 3 or len(bare) > 7:
        return False
    if _looks_like_present_verb(tok):
        return False
    # exclude function words and obvious nouns
    if bare.startswith(("ال", "ا")):
        return False
    # crude: ends in fatha or absence (past markers)
    if tok.endswith(("َ", "ْ", "ا", "وا", "ت")):
        return True
    return False


def _looks_like_jussive_verb(tok: str) -> bool:
    """مَجزوم: مُضارِع يَنتَهي بِسُكون أَو حَذف."""
    if not _looks_like_present_verb(tok):
        return False
    # ends in sukun or bare
    return tok.endswith("ْ") or (
        not tok.endswith(("ُ", "َ", "ِ", "ٌ", "ٍ", "ً", "ا"))
    )


def _looks_like_genitive_nominal(tok: str) -> bool:
    """تَنوين كَسرَة أَو كَسرَة في النِّهايَة + لَيس فِعلًا."""
    if not tok or _looks_like_present_verb(tok) or _looks_like_past_verb(tok):
        return False
    return tok.endswith(("ٍ", "ِ"))


def _is_question_verb_form(tok: str) -> bool:
    """قال/سأل وَأَخواتها."""
    if not tok:
        return False
    bare = _strip(tok)
    return bare in {_strip(q) for q in _QUESTION_VERBS}


def _starts_with_interrogative_hamza(tok: str) -> bool:
    """أَ + شَيء (هَل أَلَيس)؟"""
    if not tok or len(tok) < 2:
        return False
    return tok[0] in ("أ", "أَ") and not tok.startswith(("أَل", "أَلَّ", "ٱل"))


# ─────────────────────────────────────────────────────────────
# Particles
# ─────────────────────────────────────────────────────────────
_PREPOSITIONS = {"مِن", "إِلى", "إلى", "عَن", "على", "عَلى", "في",
                 "فِي", "ب", "بِ", "ل", "لِ", "ك", "كَ"}

_INTERROGATIVE_PARTICLES = {"هَل", "هل", "أَ", "أ"}

_JAWAB_PREFIXES = ("فَ", "ف")  # ف الجواب في الشرط


# ─────────────────────────────────────────────────────────────
# Main feature extractor
# ─────────────────────────────────────────────────────────────
def extract_context_features(
    surface: str,
    prev_tokens: Optional[list[str]] = None,
    next_tokens: Optional[list[str]] = None,
) -> dict:
    """يَستَخرِج كُلّ الـfeatures المُحتاجَة لِقَواعِد الحَلّ.

    prev_tokens: tokens قَبلَ الـsurface (آخِرُها أَقرَب)
    next_tokens: tokens بَعدَ الـsurface (أَوَّلُها أَقرَب)
    """
    prev_tokens = prev_tokens or []
    next_tokens = next_tokens or []

    nx = next_tokens[0] if next_tokens else ""
    pv = prev_tokens[-1] if prev_tokens else ""
    pv2 = prev_tokens[-2] if len(prev_tokens) >= 2 else ""

    # Detect jawab al-shart pattern (ف في token بَعد الفِعل)
    has_jawab = False
    for nt in next_tokens[1:5]:
        if nt and nt.startswith(_JAWAB_PREFIXES):
            has_jawab = True
            break

    # Question context: previous interrogative verb/particle within 3 tokens
    preceded_by_question = False
    for pt in prev_tokens[-3:]:
        if _is_question_verb_form(pt) or pt in _INTERROGATIVE_PARTICLES:
            preceded_by_question = True
            break

    return {
        "surface": surface,
        "next_token": nx,
        "prev_token": pv,
        "prev2_token": pv2,
        "next_is_present_verb": _looks_like_present_verb(nx),
        "next_is_past_verb": _looks_like_past_verb(nx),
        "next_is_jussive_verb": _looks_like_jussive_verb(nx),
        "next_is_genitive_nominal": _looks_like_genitive_nominal(nx),
        "next_starts_with_alef_lam": nx.startswith(("ٱل", "ال")),
        "preceded_by_question_verb": preceded_by_question,
        "preceded_by_preposition": pv in _PREPOSITIONS,
        "preceded_by_interrogative_particle": pv in _INTERROGATIVE_PARTICLES,
        "starts_with_interrogative_hamza": _starts_with_interrogative_hamza(pv),
        "has_jawab_al_shart_pattern": has_jawab,
        "is_sentence_initial": len(prev_tokens) == 0,
        "next_token_count": len(next_tokens),
        "prev_token_count": len(prev_tokens),
    }


__all__ = ["extract_context_features"]
