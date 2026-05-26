"""samarrai_certified_operator_gate.py — PATCH 4 (2026-05-26).

KB.SAM Certified Operator Gate.

KB.SAM (samarrai_analyzer) does substring/prefix-based operator matching
that overmatches when an operator letter appears as part of a stem rather
than as a clitic. Example: كَاتِبٌ does NOT start with a كَاف-as-prep,
but KB.SAM emits «الكاف لِلتَّشبيه» because the surface starts with ك.

This module gates KB.SAM emissions against the PRODUCTION path:
  • L1/segmenter prefix tags  (PREP / CONJ / LAM_AL_AMR / HARF_NASB / ...)
  • L1/segmenter suffix tags  (POSS_PRON / DUAL / ...)
  • L1 word_class             (HARF / ISM_* / FIIL / ...)

Strict scope (per PATCH 4 spec):
  1. Does NOT change segmentation.
  2. Does NOT change L3 word_class/case/role.
  3. Does NOT touch L4/L5/L6/L8.
  4. Does NOT touch event_extractor / relation_extractor / resolution_engine.
  5. Does NOT refactor existing code.
  6. ONLY gates/filters KB.SAM retrieval/output.

Public entry point:
    gate_text_analysis(ta) → mutates ta.words[i].claims in place.

Each filtered-out claim is converted to Zero with a blocker explaining
which production-path check rejected it (so audit trails stay intact).
"""

from __future__ import annotations

import unicodedata
from typing import Optional


_DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


# ── Topics that the L1 production path can NEVER certify ─────────────
# These require contextual oath/prose evidence that does not appear in
# any L1 prefix/suffix tag. They are dropped unconditionally.
_NEVER_CERTIFIED_TOPICS = {
    "QASAM_PARTICLES",   # واو القَسَم / باء القَسَم / تاء القَسَم
    "QASAM_JAWAB",       # إِنَّ في جَواب القَسَم (oath-response emphasis)
}

# Meaning IDs that L1 can never certify (even if topic isn't blacklisted).
# Both live under topic PREP_WAW alongside legitimate atf/etc. — but
# qasam and rubba require oath/poetic context, which has no L1 tag, so
# they must be dropped even when وَ is correctly peeled as CONJ.
_NEVER_CERTIFIED_MEANINGS = {
    "WAW_QASAM",         # qasam oath — needs oath context, not just CONJ
    "WAW_RUBBA",         # poetic rubba — no L1 evidence in Quranic prose
}


# ── Prefix-clitic topics: require a matching L1 prefix tag ──────────
# Map: KB.SAM topic_id → (expected operator letter, allowed L1 prefix tags).
# If the segmenter did NOT peel that letter with one of these tags, the
# claim is dropped.
_PREFIX_REQUIRED: dict[str, tuple[str, set[str]]] = {
    "PREP_BA":   ("ب", {"PREP"}),
    "PREP_LAM":  ("ل", {"PREP"}),
    "PREP_KAF":  ("ك", {"PREP"}),
    "PREP_WAW":  ("و", {"CONJ"}),
    # فاء العَطف / فاء رابِطَة — both need ف as CONJ
    "SHART_FA_IDH": ("ف", {"CONJ"}),
}


# ── Pronoun-suffix topic: PRONOUN entries are about pronoun suffixes
# (كَ، هُ، نا، كُمْ …). Certify only if the segmenter peeled that letter
# as POSS_PRON. Without a suffix peel, the surface letter is part of the
# stem, not a pronoun.
_PRONOUN_SUFFIX_LETTERS = {
    "ك", "ه", "ي", "ن",  # 2nd-sg, 3rd-sg-m, 1st-sg, 1st-pl-letter
}


# ── Strict-form topics: require an exact (NFC) match of the word to
# the KB's vocalized_form. Used for lexemes that share a plain-form
# spelling with other particles (إِنْ / إِنَّ / أَنْ all collapse to «ان»
# after diacritic stripping — only the diacritic-strict form is correct).
_STRICT_FORM_TOPICS = {
    "SHART_IN",          # إِنْ (kasra) — NOT أَنْ (fatha)
    "JAZM_LA_NAHIYA",    # لا — only when standalone, not part of أَلَّا
}


# ── Sin (سَ) tanfis: no L1 prefix tag exists for future-marker س.
# Drop the SIN_TANFEES_QAREEB single-letter form. The standalone full
# word سَوفَ is allowed via exact match.
_SIN_TANFIS_MEANINGS = {"SIN_TANFEES_QAREEB"}


def _has_prefix_tag(seg, letter: str, allowed_tags: set[str]) -> bool:
    """True iff the segmenter peeled `letter` with one of `allowed_tags`."""
    prefixes = getattr(seg, "prefixes", None) or []
    prefix_tags = getattr(seg, "prefix_tags", None) or []
    for pfx, tag in zip(prefixes, prefix_tags):
        if _strip_diac(pfx) == letter and tag in allowed_tags:
            return True
    return False


def _has_suffix_tag(seg, letter: str, allowed_tags: set[str]) -> bool:
    """True iff the segmenter peeled a suffix ending in `letter` with
    one of `allowed_tags`."""
    suffixes = getattr(seg, "suffixes", None) or []
    suffix_tags = getattr(seg, "suffix_tags", None) or []
    for sfx, tag in zip(suffixes, suffix_tags):
        if _strip_diac(sfx).endswith(letter) and tag in allowed_tags:
            return True
    return False


def _seg_for_word(word: str):
    """Run the production segmenter on a single word. Returns None if
    segmenter not importable (sandbox / standalone test)."""
    try:
        from segmenter import segment  # type: ignore
    except ImportError:
        return None
    try:
        return segment(word, normalize_input=True)
    except Exception:
        return None


def _is_claim_certified(word: str, claim, seg) -> tuple[bool, str]:
    """Return (certified, rejection_reason). `seg` may be None when the
    segmenter is unavailable — in that case every claim passes (no gate)
    so we never silently break callers without the production path."""

    if seg is None:
        return True, ""

    topic = (getattr(claim, "topic_id", "") or "").strip()
    mid = (getattr(claim, "meaning_id", "") or "").strip()
    op_plain = _strip_diac(getattr(claim, "operator", "") or "")
    voc = getattr(claim, "vocalized_form", "") or ""

    # Skip Zero / no-match / context-injected claims — they aren't KB
    # lookups and shouldn't be filtered by the operator gate.
    proof_kind = getattr(claim, "proof_kind", "") or ""
    contract = getattr(claim, "contract", "") or ""
    if proof_kind == "Zero":
        return True, ""
    if contract.startswith("WawDisambiguationContract"):
        return True, ""

    # Rule 1 — unconditionally blacklisted topics / meanings
    if topic in _NEVER_CERTIFIED_TOPICS:
        return False, f"topic_{topic}_requires_oath_context_not_in_L1"
    if mid in _NEVER_CERTIFIED_MEANINGS:
        return False, f"meaning_{mid}_has_no_L1_evidence"
    if mid in _SIN_TANFIS_MEANINGS:
        return False, "sin_tanfis_has_no_L1_prefix_tag"

    # Rule 2 — prefix-required clitic topics
    if topic in _PREFIX_REQUIRED:
        letter, allowed_tags = _PREFIX_REQUIRED[topic]
        if not _has_prefix_tag(seg, letter, allowed_tags):
            return False, (
                f"topic_{topic}_requires_{letter}({'/'.join(sorted(allowed_tags))}) "
                f"in_L1_prefix_tags"
            )
        return True, ""

    # Rule 3 — PRONOUN topic with single-letter operator: require POSS_PRON suffix.
    if topic == "PRONOUN" and len(op_plain) == 1 and op_plain in _PRONOUN_SUFFIX_LETTERS:
        if not _has_suffix_tag(seg, op_plain, {"POSS_PRON"}):
            return False, f"pronoun_{op_plain}_not_in_L1_suffix_POSS_PRON"
        return True, ""

    # Rule 4 — strict-form topics: exact diacritic-sensitive match
    if topic in _STRICT_FORM_TOPICS:
        if voc and _nfc(voc) == _nfc(word):
            # Extra guard for لا: even if the surface is exactly «لا»,
            # if the segmenter sees the word as part of an assimilated
            # compound (e.g. أَلَّا = أن+لا), it's not standalone النَّاهيَة.
            if topic == "JAZM_LA_NAHIYA":
                # The word given to the gate is the already-tokenized
                # form; if it equals «لا» it's standalone. Otherwise,
                # this branch isn't reached. Safe to allow.
                pass
            return True, ""
        # Allow when the stem (after prefix peel) matches the strict
        # form, but only if no problematic compound condition fires.
        stem_plain = _nfc(getattr(seg, "stem", "") or "")
        if voc and _nfc(voc) == stem_plain:
            if topic == "JAZM_LA_NAHIYA":
                # لا as the stem of e.g. أَلَّا (assimilation أن+لا).
                # The حَرف نَصب prefix means this لا is لا النَّافيَة in a
                # subjunctive clause, NOT لا النَّاهيَة (which requires
                # standalone لا + jussive verb).
                prefix_tags = getattr(seg, "prefix_tags", None) or []
                if "HARF_NASB" in prefix_tags:
                    return False, "la_in_HARF_NASB_compound_is_nafiya_not_nahiya"
                # If the word differs from standalone لا and we don't
                # have a clear standalone-jussive context, drop.
                if _nfc(word) != _nfc(voc):
                    return False, "la_nahiya_requires_standalone_la"
            return True, ""
        return False, f"strict_form_{topic}_requires_word_eq_{voc!r}"

    # Default — allow (existing topics that aren't covered remain unchanged)
    return True, ""


def gate_text_analysis(ta) -> dict:
    """Apply the Certified Operator Gate to a TextAnalysis.

    Mutates `ta.words[i].claims` in place: claims that fail the gate are
    converted to proof_kind='Zero' with a CertifiedOperatorGate blocker.
    The display layer skips Zero claims, so the user-visible KB.SAM
    section is filtered.

    Returns a small summary dict: {"checked": N, "rejected": M, "kept": K}.
    """
    checked = rejected = kept = 0
    for wa in getattr(ta, "words", []) or []:
        word = getattr(wa, "word", "") or ""
        seg = _seg_for_word(word)
        for claim in getattr(wa, "claims", []) or []:
            checked += 1
            ok, reason = _is_claim_certified(word, claim, seg)
            if ok:
                kept += 1
                continue
            rejected += 1
            # Convert the claim to a Zero with a gate blocker. We keep
            # the record so audit trails / future debug can see what was
            # rejected and why — the display layer hides Zero claims.
            claim.proof_kind = "Zero"
            existing = list(getattr(claim, "blockers", []) or [])
            existing.append(f"CertifiedOperatorGate(PATCH4): {reason}")
            claim.blockers = existing
            claim.contract = "CertifiedOperatorGate:v1"
            claim.match_type = "gate_rejected"
    return {"checked": checked, "rejected": rejected, "kept": kept}
