"""hidden_pronoun_signals.py — PATCH 13 Batch A read-only signal extractor.

Implements §5 of the discovery spec
(docs/specs/HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md) as a
pure-function module that reads a single i3rab corpus row's free-text
i3rab and emits three structured signal kinds:

  A1 — HiddenSubjectFromI3rabText
       trigger: "مستتر" + "تقديره <pronoun>" within window
       output : hidden_subject ∈ {أنا, نحن, أنت, هو, هي, هم, هن}
       guards : suppress if the row's WORD itself is an explicit pronoun;
                suppress phonological تقدير (السكون/الضمة/الفتحة/الكسرة)

  A2 — PassiveVerbSignal
       trigger: "لم يسم فاعله"
       output : voice = "passive"

  A3 — NaibFaailMarker
       trigger: i3rab text starts (after lead punctuation/quotes)
                with "نائب فاعل"
       output : role = "naib_faail"

Constitutional boundaries respected:
  • Does NOT modify segmenter / i3rab_engine / relation_extractor /
    event_extractor / resolution_engine / reasoning_engine / KB.SAM.
  • Does NOT wire these signals into L4/L5 agent output (that is a
    Batch B/C decision, see spec §4.4 / §7.2).
  • Pure-function: no global state mutation, no I/O except the optional
    `load_i3rab_row` helper that reads the corpus CSV from a fixed
    candidate path list.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

# Standard Arabic diacritics + tatweel + dagger-alif + small-alif-maddah
_DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    """Strip standard diacritics AND normalize hamza variants to bare
    alif. Hamza normalization is required so the pronoun lookup
    matches both أَنْتَ → 'انت' and أَنَا → 'انا' against the
    canonical plain-form pronoun set."""
    out = "".join(c for c in (s or "") if c not in _DIACRITICS)
    return (out
            .replace("ٱ", "ا").replace("أ", "ا")
            .replace("إ", "ا").replace("آ", "ا"))


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


# Canonical pronoun surface set (diacritic-stripped). The corpus writes
# pronouns inside i3rab text typically with diacritics; after stripping
# they collapse to these short forms.
_PRONOUNS_PLAIN = ("انا", "نحن", "انت", "هو", "هي", "هم", "هن")

# Display canonicalisation: the canonical form the SPEC mandates as
# `hidden_subject` value.
_PRONOUNS_DISPLAY = {
    "انا": "أنا",
    "نحن": "نحن",
    "انت": "أنت",
    "هو":  "هو",
    "هي":  "هي",
    "هم":  "هم",
    "هن":  "هن",
}

# Phonological case-estimation markers — distinguish from pronoun
# استتار. If "تقديره" is immediately preceded (within 12 chars) by
# one of these, the row is doing case-mark estimation, NOT hidden
# pronoun. Per spec §5 / Rule A1 negative #2.
_PHONOLOGICAL_NEAR_TAQDIR = (
    "السكون", "الضمة", "الفتحة", "الكسرة",
)

# Explicit-pronoun word surfaces (diacritic-stripped). If the corpus
# row's *own word* is one of these, the row's i3rab text is describing
# a multi-clause span and the hidden pronoun belongs to a different
# clause. Suppress A1 per spec §5 / Rule A1 negative #1.
_EXPLICIT_PRONOUN_WORD_SURFACES_PLAIN = {
    "هو", "هي", "هم", "هن", "هما",
    "انا", "نحن",
    "انت", "انتم", "انتما", "انتن",
}

# Arabic letter range — used to extract clean tokens from i3rab text
# after diacritic stripping, so the pronoun match is a true word, not
# a substring of another word.
_ARABIC_LETTER_RE = re.compile(r"[ء-ي]+")


@dataclass
class HiddenPronounSignal:
    """Read-only signal carrier. Each field is None/empty by default;
    one or more rules may populate fields independently.

    Per SPEC: this dataclass is NOT consumed by event_extractor.py in
    Batch A. Downstream consumption is a separate RULE_LOCK decision
    (Batch B/C)."""
    surah: Optional[int] = None
    ayah: Optional[int] = None
    word: str = ""

    # A1
    hidden_subject: Optional[str] = None      # one of: أنا/نحن/أنت/هو/هي/هم/هن
    # A2
    voice: Optional[str] = None               # "passive" if A2 fired
    # A3
    role: Optional[str] = None                # "naib_faail" if A3 fired

    # Proof metadata
    proof_kind: str = "Hypothesis"            # upgraded to Certificate when any A* fires
    source: str = ""                          # source-of-claim string(s), ; -separated
    rules_fired: list = field(default_factory=list)

    @property
    def any_signal(self) -> bool:
        return bool(self.hidden_subject or self.voice or self.role)


def _a1_hidden_subject(text_plain: str, word_plain: str) -> Optional[str]:
    """Return the resolved hidden-subject pronoun (display form) per
    Rule A1, or None if A1 does not fire on this text."""
    if "مستتر" not in text_plain:
        return None
    if word_plain in _EXPLICIT_PRONOUN_WORD_SURFACES_PLAIN:
        # Per spec negative #1: row's own word is an explicit pronoun;
        # the i3rab is talking about a different clause.
        return None

    # Find the FIRST مستتر occurrence; look for تقديره within the next
    # ~200 chars (spec says "within nearby window" — 200 is generous).
    mu_pos = text_plain.find("مستتر")
    search_end = mu_pos + 200
    taq_marker = "تقديره"
    taq_local = text_plain[mu_pos:search_end].find(taq_marker)
    if taq_local < 0:
        return None
    global_taq = mu_pos + taq_local

    # Phonological suppression: 12-char preceding window must not
    # contain any of السكون/الضمة/الفتحة/الكسرة.
    before = text_plain[max(0, global_taq - 12): global_taq]
    if any(p in before for p in _PHONOLOGICAL_NEAR_TAQDIR):
        return None

    # Pronoun lookup: clean tokens within 30 chars after `تقديره`.
    after_start = global_taq + len(taq_marker)
    after = text_plain[after_start: after_start + 30]
    for tok in _ARABIC_LETTER_RE.findall(after):
        if tok in _PRONOUNS_PLAIN:
            return _PRONOUNS_DISPLAY[tok]
    return None


def _a2_passive_voice(text_plain: str) -> bool:
    """Return True iff Rule A2 fires (passive-verb signal)."""
    # Diacritic-stripped form: لم يسم فاعله. Also accept the slightly
    # different verbal pattern  لم يسم فاعل with no possessive ـه.
    return "لم يسم فاعله" in text_plain or "لم يسم فاعل" in text_plain


def _a3_naib_faail_head(text_plain: str) -> bool:
    """Return True iff Rule A3 fires (naib-faail head marker).

    HEAD position only: the i3rab text must START (after optional
    leading whitespace, punctuation, or quotes) with the literal
    `نائب فاعل`. Later mentions deeper in the text MUST NOT fire."""
    if not text_plain:
        return False
    lead = text_plain.lstrip(" \t،,.()\"«»")
    return lead.startswith("نائب فاعل")


def extract_signals(i3rab_text: str, word: str = "",
                     surah: Optional[int] = None,
                     ayah: Optional[int] = None) -> HiddenPronounSignal:
    """Apply Batch A rules A1/A2/A3 to a single i3rab text + word.

    Returns a `HiddenPronounSignal`. All rules may fire independently
    on the same row. `proof_kind` is `Certificate` iff any rule fired
    (the i3rab text is authoritative for this exact word, per spec)."""
    sig = HiddenPronounSignal(surah=surah, ayah=ayah, word=word)
    if not i3rab_text:
        return sig

    text_plain = _strip_diac(_nfc(i3rab_text))
    word_plain = _strip_diac(_nfc(word))

    sources: list[str] = []

    # A1
    a1 = _a1_hidden_subject(text_plain, word_plain)
    if a1:
        sig.hidden_subject = a1
        sig.rules_fired.append("A1")
        sources.append("quran_i3rab_text:mustatir+taqdiruhu")

    # A2
    if _a2_passive_voice(text_plain):
        sig.voice = "passive"
        sig.rules_fired.append("A2")
        sources.append("quran_i3rab_text:lam_yusamma_faailuhu")

    # A3
    if _a3_naib_faail_head(text_plain):
        sig.role = "naib_faail"
        sig.rules_fired.append("A3")
        sources.append("quran_i3rab_text:naib_faail_head")

    if sig.rules_fired:
        sig.proof_kind = "Certificate"
        sig.source = "; ".join(sources)
    return sig


# ============================================================================
# Optional corpus helpers — used by tests to look up known smoke targets
# ============================================================================

def _corpus_candidate_paths() -> list:
    """Candidate paths for `quran_i3rab.csv`. The corpus lives outside
    the clean_code tree (per the existing project layout). Tests may
    skip gracefully when none of these is present (sandboxed runs)."""
    from pathlib import Path
    return [
        Path("/Users/husseinhiyassat/fractal/Huda/data/quran_i3rab.csv"),
        Path("/Users/husseinhiyassat/fractal/hussein/data/quran_i3rab.csv"),
        Path(__file__).resolve().parent.parent / "data" / "quran_i3rab.csv",
    ]


def load_i3rab_rows(surah: int, ayah: int, word: str) -> list:
    """Return ALL corpus rows whose (surah, ayah, word) match. Some
    Quranic words occur multiple times within the same ayah (e.g.
    كَاتِبٌ in 2:282 — three rows); A3 may fire on only one of them."""
    import csv as _csv
    rows = []
    word_nfc = _nfc(word)
    for path in _corpus_candidate_paths():
        if not path.is_file():
            continue
        # encoding="utf-8-sig" strips the BOM the corpus file ships with.
        with path.open(encoding="utf-8-sig") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                try:
                    if (int(row["surah"]) == int(surah)
                            and int(row["ayah"]) == int(ayah)
                            and _nfc(row["word"]) == word_nfc):
                        rows.append({
                            "surah": int(row["surah"]),
                            "ayah": int(row["ayah"]),
                            "word": row["word"],
                            "i3rab": row.get("i3rab", "") or "",
                        })
                except (KeyError, ValueError):
                    continue
        if rows:
            break
    return rows


def load_i3rab_row(surah: int, ayah: int, word: str) -> Optional[dict]:
    """Return the FIRST matching corpus row, or None."""
    rows = load_i3rab_rows(surah, ayah, word)
    return rows[0] if rows else None


def extract_signals_for(surah: int, ayah: int, word: str
                         ) -> Optional[HiddenPronounSignal]:
    """Convenience: load + apply A1 on the FIRST matching row."""
    row = load_i3rab_row(surah, ayah, word)
    if not row:
        return None
    return extract_signals(row["i3rab"], word=row["word"],
                            surah=surah, ayah=ayah)


def extract_signals_any_row(surah: int, ayah: int, word: str
                             ) -> Optional[HiddenPronounSignal]:
    """Return a merged signal across ALL matching rows: if rule A* fires
    on ANY row, the merged signal carries it. Used for A3 where the
    naib-faail row may not be the first occurrence of the surface."""
    rows = load_i3rab_rows(surah, ayah, word)
    if not rows:
        return None
    merged = HiddenPronounSignal(surah=surah, ayah=ayah,
                                  word=rows[0]["word"])
    sources: list[str] = []
    for row in rows:
        s = extract_signals(row["i3rab"], word=row["word"],
                             surah=surah, ayah=ayah)
        if s.hidden_subject and not merged.hidden_subject:
            merged.hidden_subject = s.hidden_subject
            merged.rules_fired.append("A1")
            sources.append("quran_i3rab_text:mustatir+taqdiruhu")
        if s.voice and not merged.voice:
            merged.voice = s.voice
            merged.rules_fired.append("A2")
            sources.append("quran_i3rab_text:lam_yusamma_faailuhu")
        if s.role and not merged.role:
            merged.role = s.role
            merged.rules_fired.append("A3")
            sources.append("quran_i3rab_text:naib_faail_head")
    if merged.rules_fired:
        merged.proof_kind = "Certificate"
        merged.source = "; ".join(sources)
    return merged
