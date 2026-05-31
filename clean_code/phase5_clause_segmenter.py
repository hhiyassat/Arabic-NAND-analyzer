"""phase5_clause_segmenter.py — Phase 5 / Batch A standalone clause segmenter.

Reference SPEC:
    docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md

Implements `Phase5Clause` + `Phase5ClauseGraph` dataclasses and a
rule-based segmenter that recognises six clause types per the SPEC:

    A1 PauseBoundaryClauseSplit      ۚ ۖ ۗ ۙ ۛ ۜ as span endings
    A2 ConditionalScopeClause        إِذَا / إِنْ / فَإِنْ / فَمَن / فَإِذَا
    A3 CommandClause                 lam-al-amr (وَلْيَكْتُب-class) +
                                      named imperative whitelist
    A4 ProhibitionClause             وَلَا / فَلَا / لَا + imperfect verb
    A5 AnComplementClause            أَن / أَنْ + imperfect verb
    A6 RelativeClauseShell           ٱلَّذِى / ٱلَّذِينَ / مَا / مَن

CONSTITUTIONAL (Phase 5 / Batch A governance):
  • Pure standalone module — NO production-path consumer
    (segmenter / i3rab_engine / relation_extractor / event_extractor /
     resolution_engine / reasoning_engine / meaning_assembler /
     hidden_pronoun_signals / samarrai_certified_operator_gate /
     analyze_verse_v3) imports this module.
  • Read-only: zero mutation of any production token, relation,
    event, or graph object.
  • Does NOT alter L1/L2/L3/L4/L5/L6/L7/L8 output.
  • This file is INDEPENDENT of the legacy `clause_segmenter.py`
    (which defines its own `Clause` / `ClauseSegmenter` API for
    m1_pipeline / text_graph_assembler / inter_clause_extractor /
    analyze_verse / analyze_surah and is unaffected by Phase 5).
  • Future Batches B–E wiring (clause_id into L4 / L5 / L6 / L8) is
    out of scope; each will require its own SPEC.

Public API:
    segment_clauses(tokens, verse_ref) -> list[Phase5Clause]
    segment_clauses_from_surfaces(surfaces, verse_ref) -> list[Phase5Clause]
    build_clause_graph(tokens, verse_ref, source_text="") -> Phase5ClauseGraph
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ── NFC normalisation helpers ───────────────────────────────────────

_P5_DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _p5_nfc(s):
    return unicodedata.normalize("NFC", s or "")


def _p5_strip(s):
    """NFC + diacritic strip + hamza-alif normalisation."""
    out = "".join(c for c in _p5_nfc(s) if c not in _P5_DIACRITICS)
    return (out
            .replace("ٱ", "ا").replace("أ", "ا")
            .replace("إ", "ا").replace("آ", "ا"))


# ── Quranic pause marks (A1 boundary hints) ─────────────────────────

_P5_PAUSE_MARKS = frozenset({
    "ۖ", "ۗ", "ۘ", "ۙ", "ۚ", "ۛ", "ۜ",
    "۝", "۞",
    "،", "؛",
})


def _p5_is_pause(s):
    if not s:
        return False
    nfc = _p5_nfc(s).strip()
    if not nfc:
        return False
    return all(ch in _P5_PAUSE_MARKS for ch in nfc)


# ── A2 — ConditionalScopeClause openers (NFC-strict) ────────────────
# NFC-strict so إِنْ (kasra, condition) does NOT match أَنْ (fatha,
# complementizer — that one is A5).

_P5_A2_CONDITION_NFC = frozenset({
    "إِذَا", "إِذَآ", "فَإِذَا", "فَإِذَآ",
    "إِنْ", "إِن", "فَإِنْ", "فَإِن",
    "وَإِنْ", "وَإِن",
    "مَنْ", "مَن", "فَمَنْ", "فَمَن",
    "وَمَنْ", "وَمَن",
    "فَمَا", "فَإِنَّهُۥ", "فَإِنَّهُ",
})


# ── A4 — ProhibitionClause: وَلَا / فَلَا / لَا + imperfect ────────

_P5_A4_NEG_NFC = frozenset({"وَلَا", "فَلَا", "لَا"})


# ── A5 — AnComplementClause: أَن / أَنْ (fatha-on-hamza) ─────────────

_P5_A5_AN_NFC = frozenset({"أَن", "أَنْ"})


# ── A3b — Named imperative forms (Batch A whitelist) ────────────────
# Surface-strict NFC, including the ۟ / ٓ / ا variants the corpus uses.
# Past-tense ـوا plurals are NOT in this set, so they cannot
# false-positive as commands.

_P5_A3_KNOWN_IMPERATIVE_NFC = frozenset({
    # 2:282
    "فَٱكْتُبُوهُ", "فَاكْتُبُوهُ",
    "وَٱسْتَشْهِدُوا۟", "وَٱسْتَشْهِدُوا", "وَاسْتَشْهِدُوا",
    "وَأَشْهِدُوٓا۟", "وَأَشْهِدُوا",
    "وَٱتَّقُوا۟", "وَٱتَّقُوا", "وَاتَّقُوا",
    # 2:196
    "وَأَتِمُّوا۟", "وَأَتِمُّوا",
    "وَٱعْلَمُوٓا۟", "وَٱعْلَمُوا", "وَاعْلَمُوا",
    # bare forms
    "فَٱكْتُبُوا", "فَاكْتُبُوا",
})


# ── A6 — RelativeClauseShell heads + collision-blocker for مِن ──────

_P5_A6_RELATIVE_NFC = frozenset({
    "ٱلَّذِى", "ٱلَّذِي", "الَّذِى", "الَّذِي", "الذي",
    "ٱلَّذِينَ", "ٱلَّذِيْنَ", "الَّذِينَ", "الذين",
    "ٱلَّتِى", "ٱلَّتِي", "الَّتِى", "الَّتِي", "التي",
    "مَا", "مَن", "مَنْ",
})

# Preposition NFC surfaces whose diacritic-stripped form COLLIDES with
# "من" / "ما" but which are HARF JARR, not relative pronouns.
_P5_A6_PREP_NFC = frozenset({
    "مِن", "مِنَ", "مِنْ", "مِّن", "مِّنَ", "مِّنْ",
})


def _p5_is_imperfect_verb_surface(nfc_surface):
    """True if NFC surface begins with an imperfect-verb prefix
    (يَ/يُ/يْ/تَ/تُ/تْ/نَ/نُ/نْ/أَ/أُ/أْ). Used as a lookahead by A4
    and A5; over-collection is acceptable here because both
    constructions (negation + verb, an + verb) accept any verb form."""
    if not nfc_surface or len(nfc_surface) < 2:
        return False
    return nfc_surface[:2] in (
        "يَ", "يُ", "يْ",
        "تَ", "تُ", "تْ",
        "نَ", "نُ", "نْ",
        "أَ", "أُ", "أْ",
    )


def _p5_is_lam_al_amr_surface(nfc_surface):
    """Surface match for lam-al-amr verbs (وَلْيَكْتُب-class). Strip an
    optional CONJ prefix (وَ / فَ), then require the residue to begin
    with لْ (lam + sukun) and have ≥ 3 letters total."""
    residue = nfc_surface
    if residue.startswith(("وَ", "فَ")):
        residue = residue[2:]
    elif residue.startswith(("و", "ف")) and len(residue) >= 2:
        residue = residue[1:]
    return residue.startswith("لْ") and len(residue) >= 3


# ────────────────────────────────────────────────────────────────────
# Phase 5 dataclasses
# ────────────────────────────────────────────────────────────────────

@dataclass
class Phase5Clause:
    """SPEC-conformant Phase-5 clause object."""
    clause_id: str
    verse: str
    type: str
    start_token_index: int
    end_token_index: int
    text: str
    head_token: str
    head_kind: str
    parent_clause_id: Optional[str] = None
    introduced_by: str = ""
    scope_status: str = "closed"
    confidence: str = "Hypothesis"
    source: str = ""


@dataclass
class Phase5ClauseGraph:
    verse_ref: str
    clauses: list = field(default_factory=list)
    source_text: str = ""
    contract: str = "Phase5ClauseGraph:v1"


# ────────────────────────────────────────────────────────────────────
# Rule dispatch
# ────────────────────────────────────────────────────────────────────

def _p5_classify_opener_at(nfc_surfaces, i):
    """Inspect token at position `i` and return
        (rule_id, clause_type, head_kind, introduced_by,
         confidence, source)
    if any A2–A6 rule fires; otherwise None.

    A1 (pause-boundary) is handled at span level, not by this function."""
    if i < 0 or i >= len(nfc_surfaces):
        return None
    nfc = nfc_surfaces[i]
    if _p5_is_pause(nfc):
        return None
    nxt = nfc_surfaces[i + 1] if i + 1 < len(nfc_surfaces) else ""

    # A2 — Condition opener
    if nfc in _P5_A2_CONDITION_NFC:
        return ("A2", "condition", "particle", nfc,
                "Certificate", "ConditionalScopeContract")

    # A4 — Prohibition: وَلَا / فَلَا / لَا + imperfect
    if nfc in _P5_A4_NEG_NFC and _p5_is_imperfect_verb_surface(nxt):
        return ("A4", "prohibition", "particle", nfc,
                "Certificate", "ProhibitionContract")

    # A5 — An-complement: أَن / أَنْ + imperfect
    if nfc in _P5_A5_AN_NFC and _p5_is_imperfect_verb_surface(nxt):
        return ("A5", "complement_an", "particle", nfc,
                "Certificate", "AnComplementContract")

    # A3a — Lam-al-amr command
    if _p5_is_lam_al_amr_surface(nfc):
        introducer = nfc[:2] if nfc.startswith(("وَ", "فَ")) else ""
        return ("A3a", "command", "verb", introducer,
                "Certificate", "LamAlAmrCommandContract")

    # A3b — Named imperative form
    if nfc in _P5_A3_KNOWN_IMPERATIVE_NFC:
        introducer = nfc[:2] if nfc.startswith(("وَ", "فَ")) else ""
        return ("A3b", "command", "verb", introducer,
                "Hypothesis", "ImperativeFormContract")

    # A6 — Relative-clause shell (preposition collision blocked)
    if nfc in _P5_A6_PREP_NFC:
        return None
    if nfc in _P5_A6_RELATIVE_NFC:
        return ("A6", "relative_shell", "noun", nfc,
                "Hypothesis", "RelativeClauseShellContract")

    return None


def _p5_find_span_end(nfc_surfaces, start, opener_positions):
    """Inclusive end-of-span index for a clause that starts at `start`.
    Per A1, the span ends just before the next opener OR the next
    pause-mark OR the end of the surface list — whichever comes first."""
    n = len(nfc_surfaces)
    for k in range(start + 1, n):
        if _p5_is_pause(nfc_surfaces[k]):
            return k - 1
        if k in opener_positions:
            return k - 1
    return n - 1


# ────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────

def _p5_surfaces_from_input(tokens):
    """Normalise a heterogeneous input into a list of NFC surface
    strings. Accepts either plain strings or token-like objects
    exposing `.token` / `.surface`."""
    out = []
    for t in tokens or []:
        if isinstance(t, str):
            out.append(_p5_nfc(t))
            continue
        # Duck-typed token object
        s = getattr(t, "token", None) or getattr(t, "surface", None) or ""
        out.append(_p5_nfc(s))
    return out


def segment_clauses_from_surfaces(surfaces, verse_ref):
    """Primary Phase-5 entry. Walk `surfaces` (NFC-normalised
    whitespace-split of the verse text including pause marks) and
    return an ordered `list[Phase5Clause]`."""
    if not surfaces:
        return []
    nfc_surfaces = [_p5_nfc(s) for s in surfaces]

    # Pass 1: classify every position; record opener positions.
    classifications = {}
    for i in range(len(nfc_surfaces)):
        cls = _p5_classify_opener_at(nfc_surfaces, i)
        if cls is not None:
            classifications[i] = cls
    opener_positions = set(classifications.keys())

    # Pass 2: emit clauses in order; link condition_answer when a
    # فَـ-headed command follows an unconsumed condition.
    clauses = []
    pending_condition_id = None
    next_cid = 1
    for i in sorted(opener_positions):
        rule_id, ctype, head_kind, intro, conf, source = classifications[i]
        end = _p5_find_span_end(nfc_surfaces, i, opener_positions)
        text = " ".join(nfc_surfaces[i: end + 1]).strip()
        head_token = nfc_surfaces[i]

        parent = None

        # condition_answer linkage
        if (rule_id in ("A3a", "A3b")
                and head_token.startswith("فَ")
                and pending_condition_id is not None):
            ctype = "condition_answer_command"
            parent = pending_condition_id
            pending_condition_id = None
            source = source + "+ConditionAnswerLinker"
        elif rule_id == "A2":
            # Open a fresh pending-condition slot. Any prior unconsumed
            # condition is forgotten (sequence of conditions without an
            # explicit فَـ answer between them).
            pending_condition_id = f"C{next_cid:03d}"
        elif rule_id in ("A3a", "A3b", "A4") and pending_condition_id is not None:
            # A non-فَـ command/prohibition between condition and answer
            # breaks the pending link.
            pending_condition_id = None

        clauses.append(Phase5Clause(
            clause_id=f"C{next_cid:03d}",
            verse=verse_ref,
            type=ctype,
            start_token_index=i,
            end_token_index=end,
            text=text,
            head_token=head_token,
            head_kind=head_kind,
            parent_clause_id=parent,
            introduced_by=intro,
            scope_status="closed",
            confidence=conf,
            source=source,
        ))
        next_cid += 1

    return clauses


def segment_clauses(tokens, verse_ref):
    """Convenience wrapper: accepts either a list of strings or a list
    of token-like objects with a `.token` attribute (i3rab engine
    output, segmenter output, etc.). Returns the same
    `list[Phase5Clause]` as `segment_clauses_from_surfaces`."""
    surfaces = _p5_surfaces_from_input(tokens)
    return segment_clauses_from_surfaces(surfaces, verse_ref)


def build_clause_graph(tokens, verse_ref, source_text=""):
    """Package the clause list into a `Phase5ClauseGraph`."""
    clauses = segment_clauses(tokens, verse_ref)
    return Phase5ClauseGraph(
        verse_ref=verse_ref,
        clauses=clauses,
        source_text=source_text or "",
    )
