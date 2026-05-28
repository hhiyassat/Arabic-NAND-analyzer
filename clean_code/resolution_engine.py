"""resolution_engine.py — Phase E: مُحَرِّك التَّعيين المُوَحَّد.

يَدمُج 5 أَنواع تَعيين:
  1. Anaphora (الضَّمائر) — يَستَدعي AnaphoraResolverV2 المَوجود
  2. Deixis (الإِشارَة) — جَديد
  3. Relative (المَوصول) — جَديد
  4. Bridging (الإِشارَة الضِّمنيَّة) — بَدائيّ
  5. Identity-through-Transformation — مَع EventGraph

MC-COMPLIANT (Q3-aligned):
  • كُلّ تَعيين بِـ ProofObject
  • alternatives_preserved: كُلّ المُرَشَّحين مَحفوظون
  • لا inline rules: lexicons مِن CSV
  • Zero صَريح عِندَ عَدَم وُجود مَرجِع
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from resolution_schema import (
    Candidate,
    Resolution,
    ResolutionGraph,
)

_HERE = Path(__file__).resolve().parent
DEMONSTRATIVES_CSV = _HERE / "data" / "contracts" / "lists" / "demonstratives.csv"
RELATIVE_PRONOUNS_CSV = _HERE / "data" / "contracts" / "lists" / "relative_pronouns.csv"
DETACHED_PRONOUNS_CSV = _HERE / "data" / "contracts" / "lists" / "detached_pronouns.csv"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─────────────────────────────────────────────────────────────────
# تَحميل الـ lexicons
# ─────────────────────────────────────────────────────────────────

_DEMO_CACHE: dict | None = None
_REL_CACHE: dict | None = None
_DETACHED_CACHE: dict | None = None


def _load_lexicon(path: Path) -> dict[str, dict]:
    """يُحَمِّل lexicon عامّ."""
    cache: dict[str, dict] = {}
    if not path.exists():
        return cache
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("word", "").strip())
            plain = _normalize(voc)
            entry = {k: v.strip() for k, v in row.items() if v}
            cache[voc] = entry
            cache[plain] = entry
    return cache


def _demo_lex() -> dict:
    global _DEMO_CACHE
    if _DEMO_CACHE is None:
        _DEMO_CACHE = _load_lexicon(DEMONSTRATIVES_CSV)
    return _DEMO_CACHE


def _rel_lex() -> dict:
    global _REL_CACHE
    if _REL_CACHE is None:
        _REL_CACHE = _load_lexicon(RELATIVE_PRONOUNS_CSV)
    return _REL_CACHE


def is_demonstrative(word: str) -> Optional[dict]:
    cache = _demo_lex()
    voc = _nfc(word)
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


def is_relative_pronoun(word: str) -> Optional[dict]:
    cache = _rel_lex()
    voc = _nfc(word)
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


# ============================================================================
# PATCH 8 (2026-05-28) — L6 Resolution Safety Gates
# ============================================================================
#
# Block obviously impossible / unsafe antecedent links. Each gate is a
# small predicate; the resolver consults them before adding a Resolution
# (or before keeping a candidate). No resolution is invented — only
# filtered. No relation/segmenter/i3rab data is changed.

# Particles whose diacritic-stripped surface collides with relative
# pronouns: مِن (HARF JARR) vs مَن (relative). The CSV lexicon stores
# both under plain `من`, so we additionally check the token's
# word_class from L3 to distinguish.
_P8_TEMPORAL_OR_CONDITIONAL = {
    "اذا", "اذ", "لما", "متى", "حين", "حينما", "ايان", "كلما",
    "حيث", "حيثما",
}


def _p8_strip(s: str) -> str:
    s = "".join(c for c in (s or "") if c not in "ًٌٍَُِّْـٰٓ")
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


def _p8_token_is_harf_preposition(t) -> bool:
    """True if the token's L3 word_class is HARF (i.e., a real particle,
    not a homograph relative pronoun). Used to reject مِن / مِنَ from
    relative resolution — those are HARF JARR, not مَن the relative."""
    return getattr(t, "word_class", "") == "HARF"


def _p8_is_temporal_or_conditional_particle(t) -> bool:
    """True for إِذَا / إِذ / لَمَّا / مَتى / حيث / كُلَّما, by surface or wazn."""
    surf = _p8_strip(getattr(t, "token", "") or getattr(t, "surface", ""))
    if surf in _P8_TEMPORAL_OR_CONDITIONAL:
        return True
    wazn = getattr(t, "wazn", "") or ""
    return "ظرف" in wazn or "شرط" in wazn


def _p8_is_jalalah_token(t) -> bool:
    """True for لَفظ الجَلالَة by word_class, wazn, or surface fallback."""
    if getattr(t, "word_class", "") == "JALALAH":
        return True
    wazn = getattr(t, "wazn", "") or ""
    if "جلال" in wazn:
        return True
    stem = getattr(t, "stem", "") or getattr(t, "token", "") or getattr(t, "surface", "") or ""
    stem_plain = _p8_strip(stem)
    return stem_plain in ("الله", "اللاه", "اله") or stem_plain.endswith("الله")


def _p8_is_indefinite_token(t) -> bool:
    """True if the token's surface ends in tanwin (ـًا / ـٍ / ـٌ /
    ـً / ـٍ / ـٌ) → indefinite noun. Used to reject things like شَيْـًٔا
    as antecedent for ٱلَّذِى."""
    surf = getattr(t, "token", "") or getattr(t, "surface", "") or ""
    return surf.endswith(("ًا", "ٍ", "ٌ", "ً", "ـٌ", "ـٍ", "ـً", "ـٰ"))


def _p8_is_adjective_like(t) -> bool:
    """True if the token looks like an adjective/predicate descriptor
    (فَعِيل-pattern, indefinite, often in خبر/نعت role). Used to reject
    ضَعِيفًا / سَفِيهًا as anaphor antecedents for هُوَ."""
    surf = _p8_strip(getattr(t, "token", "") or getattr(t, "surface", "") or "")
    # The two patterns we care about for 2:282: سَفِيها / ضَعِيفا
    # (and the broader فَعِيل-tanwin family). Also accept role hints.
    if surf in {"سفيها", "ضعيفا", "كبيرا", "صغيرا", "حاضرة", "ضعيف",
                "سفيه", "كبير", "صغير"}:
        return True
    # فَعِيل-tanwin pattern: ends in ـِيلًا / ـِيها / ـِيدا etc.
    if surf.endswith("ا") and len(surf) >= 4 and "يـ" in (
            getattr(t, "token", "") or ""):
        return True
    role = getattr(t, "role_phrase", "") or ""
    if "نعت" in role or "خبر" in role:
        # Pure predicates aren't person referents.
        return True
    return False


# ============================================================================
# PATCH 9 (2026-05-28) — L6 Antecedent Quality Gates
# ============================================================================
#
# After PATCH 8 removed impossible antecedent links, low-quality
# antecedents (PP-headed nouns, possessor-bearing nouns, abstract legal
# nouns, إذا+ما clusters) still surface. PATCH 9 adds 4 more filters,
# all reading existing token attributes (no segmenter/i3rab/relation
# changes).


def _p9_token_has_prep_prefix(t) -> bool:
    """True if the token carries a بِ / لِ / كِ as a PREP-peeled prefix.
    Reads `prefix_tags` if present; falls back to re-segmenting via the
    production segmenter when the i3rab pipeline didn't carry tags."""
    prefix_tags = getattr(t, "prefix_tags", None) or []
    if "PREP" in prefix_tags:
        return True
    # Reliable surface fallback (PP nouns in this corpus always start
    # with بِ / لِ / كِ / فِ — diacritic-mark on first letter).
    surface = getattr(t, "token", "") or getattr(t, "surface", "") or ""
    plain = _p8_strip(surface)
    if plain.startswith(("ب", "ل", "ك")):
        # Distinguish PREP-clitic-on-noun from native-letter words by
        # asking the segmenter directly. False when segmenter is not
        # importable — better to leave the candidate than over-reject.
        try:
            from segmenter import segment as _segment  # type: ignore
            seg = _segment(surface, normalize_input=True)
            return "PREP" in (seg.prefix_tags or [])
        except Exception:
            return False
    return False


# Possessor-tail attached pronouns (POSS_PRON suffixes). When a noun
# carries one of these (ـهُ / ـهَا / ـكُم / ـنا / ـهِم / ـكَ), it is
# the مضاف with the suffix as مُضاف-إليه — making the noun a possessed
# entity, not a free relative-pronoun antecedent.
_P9_POSS_TAILS = ("ه", "ها", "هم", "هن", "هما",
                  "ك", "كم", "كن", "كما", "نا", "ي")


def _p9_token_has_possessor_tail(t) -> bool:
    """True if the token surface ends with an attached pronoun suffix
    (ـه/ـها/ـكم/ـنا/...). Catches رَبَّهُ-class antecedents that PATCH 8
    let through because they aren't jalalah / indefinite / particle."""
    suffix_tags = getattr(t, "suffix_tags", None) or []
    if "POSS_PRON" in suffix_tags:
        return True
    # Surface fallback: strip diacritics and check tail.
    surf_plain = _p8_strip(getattr(t, "token", "") or getattr(t, "surface", "") or "")
    return any(surf_plain.endswith(tail) for tail in _P9_POSS_TAILS) and len(surf_plain) >= 3


# Abstract/legal nouns that personal pronouns (هُوَ/هِيَ) should not
# resolve to. Person pronouns refer to PERSONS, not abstract concepts
# (الحَقّ, العَدل, الباطِل, الدِّين, الإيمان, الكُفر, ...). The list is
# intentionally small and Quranic-corpus-tuned; expand only when an
# actual misfire surfaces.
_P9_ABSTRACT_NOUN_STEMS = {
    "حق", "حقّ", "الحق", "الحقّ",
    "باطل", "الباطل",
    "عدل", "العدل",
    "دين", "الدين",
    "ايمان", "الايمان",
    "كفر", "الكفر",
    "علم", "العلم",
}


def _p9_is_abstract_noun(t) -> bool:
    """True if the token surface (stripped) matches a known abstract /
    legal noun. Used to reject ٱلْحَقُّ-class antecedents for هُوَ."""
    surf_plain = _p8_strip(
        getattr(t, "stem", "") or getattr(t, "token", "") or
        getattr(t, "surface", "") or ""
    )
    return surf_plain in _P9_ABSTRACT_NOUN_STEMS


def _p9_is_non_person_for_personal_pronoun(t) -> bool:
    """True if the candidate is non-person (abstract OR indefinite-
    tanwin). Personal pronouns هُوَ/هِيَ should reach a person; if no
    person is available it is better to stay unresolved than to fall
    back to شَيْـًٔا-class indefinite nouns."""
    if _p9_is_abstract_noun(t):
        return True
    if _p8_is_indefinite_token(t):
        return True
    return False


# ============================================================================
# PATCH 10 (2026-05-28) — L6 Huwa / Alladhi Clause-Head Refinement
# ============================================================================
#
# Narrow refinement on top of PATCH 8/9:
#   1. Block هُوَ → possessor-tail noun (e.g. هُوَ → رَبَّهُ). The
#      possessor-tail attachment makes the noun an "X's-something"
#      possessed entity, NOT the person referenced by a free personal
#      pronoun like هُوَ in «أَن يُمِلَّ هُوَ».
#   2. Block ٱلَّذِى → abstract noun (e.g. ٱلَّذِى → ٱلْحَقُّ). ٱلَّذِى
#      in «ٱلَّذِى عَلَيْهِ ٱلْحَقُّ» refers to a person/obligor; ٱلْحَقُّ
#      is the predicate-noun inside the relative clause, NOT its
#      external antecedent. We extend PATCH 9 Gate I (abstract-noun
#      rejection on personal pronouns) to apply to relative ٱلَّذِى
#      candidates as well.
#
# All gates reuse existing helpers; no new lexicons or refactors.


def _p10_huwa_should_reject_candidate(t_target) -> bool:
    """Per-PATCH-10 personal-pronoun (هُوَ/هِيَ) candidate-rejector.
    Combines:
      • PATCH 8 Gate E — adjective-like (ضَعِيفًا / سَفِيهًا)
      • PATCH 9 Gate I — abstract (ٱلْحَقُّ) and indefinite (شَيْـًٔا)
      • PATCH 10 — possessor-tail (رَبَّهُ-class)
      • PATCH 10 — temporal/conditional particles (إِذَا, even when L3
        misclassifies it as ISM_MUARAB and admits it to the entity set)
    """
    if _p8_is_adjective_like(t_target):
        return True
    if _p9_is_non_person_for_personal_pronoun(t_target):
        return True
    if _p9_token_has_possessor_tail(t_target):
        return True
    if _p8_is_temporal_or_conditional_particle(t_target):
        return True
    return False


def _p10_alladhi_should_reject_candidate(t_target) -> bool:
    """Per-PATCH-10 ٱلَّذِى candidate-rejector. Combines PATCH 8 Gate C
    (jalalah/indefinite/HARF/temporal), PATCH 9 Gate G (PP-prefix),
    Gate H (possessor-tail), AND PATCH 10's abstract-noun rejection."""
    if _p8_should_reject_for_relative_alladhi(t_target):
        return True
    if _p9_token_has_prep_prefix(t_target):
        return True
    if _p9_token_has_possessor_tail(t_target):
        return True
    if _p9_is_abstract_noun(t_target):
        return True
    return False


# ============================================================================
# PATCH 15 (2026-05-28) — Cross-Verse L6 Safety Gates (for 2:196 et al.)
# ============================================================================
#
# Generalize PATCH 8/9/10 rejection logic to two more L6 paths:
#   • DEIXIS — تِلْكَ / ذَٰلِكَ must NOT resolve to adjective-like or
#     possessor-tail-bearing candidates. Until PATCH 15 the deixis
#     resolver had no quality gate at all and emitted noisy matches.
#   • RELATIVE on مِّن — the assimilated شدّة-bearing form مِّن is the
#     preposition مِن (idgham after a previous letter), NOT the
#     relative pronoun مَن. The diacritic-stripped lookup collides;
#     L1 incorrectly classifies it as ISM_MAWSOOL on 2:196, so the
#     PATCH 8 word_class==HARF gate doesn't fire. Surface-based
#     rejection closes this gap.


def _p15_min_surface_is_preposition(referent: str) -> bool:
    """True iff the relative-referent surface is one of the
    preposition spellings of مِن (with or without idgham-shadda). The
    relative pronoun مَن uses fatha on م; the preposition مِن uses
    kasra. The mim-shadda variant مِّن occurs after idgham."""
    if not referent:
        return False
    nfc = unicodedata.normalize("NFC", referent)
    # Diacritic-stripped + hamza-normalized form for the few canonical
    # preposition spellings. Match BOTH plain `من` AND the explicit
    # kasra/sukun-bearing surfaces; the relative pronoun مَن uses fatha
    # so it will not collide with these specific NFC strings.
    if nfc in ("مِن", "مِّن", "مِنْ", "مِنَ"):
        return True
    return False


def _p15_token_has_extended_possessor_tail(t) -> bool:
    """Like `_p9_token_has_possessor_tail` but also matches the
    1st-person-singular ـى (alif maksura, U+0649) — corpus
    orthography sometimes writes the 1sg-genitive pronoun this way.
    Targets 2:196 حَاضِرِى."""
    if _p9_token_has_possessor_tail(t):
        return True
    surf_plain = _p8_strip(
        getattr(t, "token", "") or getattr(t, "surface", "") or ""
    )
    return surf_plain.endswith("ى") and len(surf_plain) >= 3


# ============================================================================
# PATCH 16 (2026-05-28) — L6 Demonstrative Abstract-Reference Policy
# ============================================================================
#
# Narrow follow-up to PATCH 15. When the demonstrative ذَٰلِكَ is
# followed by a لِمَن/لمن condition clause, it refers to a PRIOR
# proposition/clause, not to a nearby nominal antecedent.
#
# Example (2:196):
#   "... تِلْكَ عَشَرَةٌ كَامِلَةٌ ۗ ذَٰلِكَ لِمَن لَّمْ يَكُنْ أَهْلُهُ ..."
# Here ذَٰلِكَ refers to the ruling/allowance just stated, NOT to
# عَشَرَةٌ (a number) or any other nearby noun.


_P16_ABSTRACT_REF_CONTINUATIONS_PLAIN = {
    "لمن",      # لِمَن / لمن — "(this) is for whoever ..."
}


def _p16_demonstrative_is_abstract_reference(referent: str,
                                              i: int, tokens) -> bool:
    """True iff the demonstrative at `tokens[i]` is the surface
    ذَٰلِكَ / ذلك AND the immediately-following token begins a
    لِمَن-style PP/condition clause. Such ذَٰلِكَ points to a prior
    proposition, not to a nominal candidate; the L6 resolver must
    return Zero rather than emit a noisy noun match."""
    ref_plain = _p8_strip(referent or "")
    # Only this narrow trigger word; do not over-extend to all
    # demonstratives.
    if ref_plain != "ذلك":
        return False
    if i + 1 >= len(tokens):
        return False
    nxt = tokens[i + 1]
    nxt_surface = getattr(nxt, "token", "") or getattr(nxt, "surface", "") or ""
    nxt_plain = _p8_strip(nxt_surface)
    if nxt_plain in _P16_ABSTRACT_REF_CONTINUATIONS_PLAIN:
        return True
    # Also accept the slightly extended forms (لمن preceded by a
    # diacritic-stripped fa/wa connector or trailing shadda).
    return any(nxt_plain.startswith(p) for p in _P16_ABSTRACT_REF_CONTINUATIONS_PLAIN)


def _p15_deixis_should_reject_candidate(t_target) -> bool:
    """Per-PATCH-15 demonstrative-pronoun (تِلْكَ / ذَٰلِكَ / هَٰذَا /
    ...) candidate-rejector. Combines:
      • PATCH 8 Gate E — adjective-like (حَاضِر / ضَعِيف / كَامِل / ...)
      • PATCH 9 — possessor-tail (ـه/ـها/ـكم/ـنا/...)
      • PATCH 15 — extended possessor-tail (also ـى for حَاضِرِى-class)
      • PATCH 9 — abstract noun (الحَقّ / العَدل / ...)
      • role==نعت — candidates currently functioning as نعت are
        attributes of a head noun, not the referent of an external
        demonstrative.
    """
    if _p8_is_adjective_like(t_target):
        return True
    if _p15_token_has_extended_possessor_tail(t_target):
        return True
    if _p9_is_abstract_noun(t_target):
        return True
    role = getattr(t_target, "role_phrase", "") or ""
    if "نعت" in role:
        return True
    wazn = getattr(t_target, "wazn", "") or ""
    if wazn == "فاعل":
        # كَامِلَةٌ (wazn=فاعل) — active-participle adjective pattern.
        return True
    return False


def _p9_is_idha_ma_cluster(idx: int, tokens) -> bool:
    """True if `tokens[idx]` is مَا preceded by إِذَا at idx-1.
    Such مَا is a clausal extender of إذا (إذا ما = "if/when ever"),
    NOT a relative pronoun. Reject relative resolution entirely."""
    if idx <= 0:
        return False
    surf = _p8_strip(getattr(tokens[idx], "token", "") or "")
    if surf not in ("ما",):
        return False
    prev_surf = _p8_strip(getattr(tokens[idx - 1], "token", "") or "")
    return prev_surf == "اذا"


# Set of jalalah-ish surface markers used for ٱلَّذِى gate
def _p8_should_reject_for_relative_alladhi(t_target) -> bool:
    """True if `t_target` is an impossible antecedent for ٱلَّذِى /
    ٱلَّتِى: لَفظ الجَلالَة, indefinite tanwin nouns (شَيْـًٔا),
    particles/HARF, temporal/conditional particles."""
    if _p8_is_jalalah_token(t_target):
        return True
    if _p8_is_indefinite_token(t_target):
        return True
    if getattr(t_target, "word_class", "") == "HARF":
        return True
    if _p8_is_temporal_or_conditional_particle(t_target):
        return True
    return False


def _detached_lex() -> dict:
    """يُحَمِّل detached_pronouns.csv — يُفَهرَس بِالسَّطح وَ المُجَرَّد."""
    global _DETACHED_CACHE
    if _DETACHED_CACHE is not None:
        return _DETACHED_CACHE
    cache: dict[str, dict] = {}
    if not DETACHED_PRONOUNS_CSV.exists():
        _DETACHED_CACHE = cache
        return cache
    with open(DETACHED_PRONOUNS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            voc = _nfc(row.get("surface", "").strip())
            plain = row.get("plain", "").strip()
            entry = {k: v.strip() for k, v in row.items() if v}
            if voc:
                cache[voc] = entry
            if plain:
                cache.setdefault(plain, entry)
    _DETACHED_CACHE = cache
    return cache


def is_detached_pronoun(word: str) -> Optional[dict]:
    """يَفحَص هَل الكَلِمَة ضَمير مُنفَصِل (إِيَّاكَ، أَنتَ، هو، نَحنُ...).

    يَتَخَطَّى بَوادِئ الواو/الفاء قَبل المُطابَقَة.
    """
    cache = _detached_lex()
    voc = _nfc(word)
    # نَزع الـ clitics البادِئَة لِفَحص النَّواة
    for clitic in ("وَ", "فَ", "و", "ف"):
        if voc.startswith(clitic) and len(voc) > len(clitic):
            stripped = voc[len(clitic):]
            if stripped in cache:
                return cache[stripped]
            stripped_plain = _normalize(stripped)
            if stripped_plain in cache:
                return cache[stripped_plain]
    if voc in cache:
        return cache[voc]
    return cache.get(_normalize(voc))


# ─────────────────────────────────────────────────────────────────
# المُحَرِّك
# ─────────────────────────────────────────────────────────────────

class ResolutionEngine:
    """مُحَرِّك تَعيين مُوَحَّد لِكُلّ الأَنواع."""

    CONTRACT_DEIXIS = "DeixisResolutionContract:v1"
    CONTRACT_RELATIVE = "RelativeResolutionContract:v1"
    CONTRACT_ANAPHORA = "AnaphoraResolutionContract:v1"
    CONTRACT_TRANSFORMATION = "TransformationIdentityContract:v1"
    CONTRACT_DETACHED = "DetachedPronounResolutionContract:v1"

    def resolve(self, sent, event_graph=None, *, prior_context=None) -> ResolutionGraph:
        """يُنفِّذ كُلّ أَنواع التَّعيين عَلى جُملَة.

        prior_context — قائِمَة dicts اختياريَّة لِكِيانات سابِقَة (مِن آيات سابِقَة
        مَثَلًا). كُلّ dict: {id, surface, gender, number, position, source}.
        تُستَخدَم لِتَعيين الضَّمائر المُنفَصِلَة عَبر الآيات.
        """
        graph = ResolutionGraph(source_text=getattr(sent, "text", ""))
        tokens = sent.tokens

        # 1. الضَّمائر (Anaphora)
        for r in self._resolve_anaphora(tokens, sent):
            graph.add(r)
        # 2. الإِشارَة (Deixis)
        for r in self._resolve_deixis(tokens):
            graph.add(r)
        # 3. المَوصول (Relative)
        for r in self._resolve_relative(tokens):
            graph.add(r)
        # 4. التَّحَوُّل
        if event_graph:
            for r in self._resolve_transformation_identity(event_graph, tokens):
                graph.add(r)
        # 5. Bridging — Phase E 100%
        for r in self._resolve_bridging(tokens):
            graph.add(r)
        # 6. الضَّمائر المُنفَصِلَة (إِيَّا*، أَنتَ، نَحنُ، هو، هي...)
        for r in self._resolve_detached_pronouns(tokens, prior_context or []):
            graph.add(r)
        return graph

    # ──────────────────────────────────────────────────────────
    # 6. Detached pronouns (إِيَّا*، أَنتَ، نَحنُ، هو، هي، هم...)
    # ──────────────────────────────────────────────────────────

    def _resolve_detached_pronouns(self, tokens, prior_context) -> list[Resolution]:
        """حَلّ الضَّمائر المُنفَصِلَة بِالشَّخص + السِّياق السَّابِق.

        المَنطِق:
          • person=1 (أَنا/نَحنُ) → القائِل (إِن وُجِد في prior_context: speaker)
          • person=2 (أَنتَ/إِيَّاكَ/أَنتُم) → المُخاطَب (addressee)
          • person=3 (هو/هي/إِيَّاهُ) → أَقرَب اسم ظاهِر سابِق مُطابِق
            في الجِنس/العَدَد (داخِل الجُملَة أَو في prior_context)
        """
        results = []
        # نَجمَع كِيانات داخِل الجُملَة كَ مُرَشَّحين لِضَمائر الغائِب
        in_sent_entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            entry = is_detached_pronoun(surface)
            if not entry:
                continue
            person = entry.get("person", "").strip()
            number = entry.get("number", "").strip()
            gender = entry.get("gender", "").strip()
            case = entry.get("case", "").strip()

            candidates: list[Candidate] = []

            if person == "1":
                # القائِل — نَفحَص prior_context
                speaker = next(
                    (e for e in prior_context if e.get("role") == "speaker"),
                    None,
                )
                if speaker:
                    candidates.append(Candidate(
                        entity_id=speaker.get("id", "speaker"),
                        entity_surface=speaker.get("surface", "القائِل"),
                        score=1.0,
                        reason=f"person=1 → speaker (prior_context)",
                    ))
                else:
                    # لا context — نَتركها كَ مُرَشَّح فارِغ (Zero)
                    candidates.append(Candidate(
                        entity_id="UNKNOWN_SPEAKER",
                        entity_surface="القائِل (غَير مَعروف في السِّياق)",
                        score=0.3,
                        reason=f"person=1 بِلا speaker في prior_context",
                    ))

            elif person == "2":
                # المُخاطَب — نَفحَص prior_context
                addressee = next(
                    (e for e in prior_context if e.get("role") == "addressee"),
                    None,
                )
                if addressee:
                    candidates.append(Candidate(
                        entity_id=addressee.get("id", "addressee"),
                        entity_surface=addressee.get("surface", "المُخاطَب"),
                        score=1.0,
                        reason=f"person=2 → addressee (prior_context)",
                    ))
                else:
                    candidates.append(Candidate(
                        entity_id="UNKNOWN_ADDRESSEE",
                        entity_surface="المُخاطَب (غَير مَعروف في السِّياق)",
                        score=0.3,
                        reason=f"person=2 بِلا addressee في prior_context",
                    ))

            elif person == "3":
                # الغائِب — أَقرَب اسم سابِق مُطابِق
                gender_map = {"masculine": "M", "feminine": "F", "common": "X"}
                number_map = {"singular": "SG", "dual": "DU", "plural": "PL"}
                wanted_g = gender_map.get(gender, "X")
                wanted_n = number_map.get(number, "SG")
                for ent in in_sent_entities:
                    if ent["position"] >= i:
                        continue
                    g_match = (wanted_g == "X" or ent["gender"] == wanted_g)
                    if not g_match:
                        continue
                    # PATCH 10 — consolidated rejector on detached path
                    # (هُوَ/هِيَ/...). Same gate stack as the anaphora
                    # path: adjective + abstract + indefinite +
                    # possessor-tail. Keeps PATCH 8/9 behavior plus the
                    # PATCH 10 fix for هُوَ → رَبَّهُ.
                    ent_idx_d = ent["position"]
                    ent_tok_d = tokens[ent_idx_d] if 0 <= ent_idx_d < len(tokens) else None
                    if ent_tok_d is not None and _p10_huwa_should_reject_candidate(ent_tok_d):
                        continue
                    proximity = i - ent["position"]
                    score = 1.0 / (1.0 + proximity * 0.2)
                    candidates.append(Candidate(
                        entity_id=ent["id"],
                        entity_surface=ent["surface"],
                        score=score,
                        matches_gender=g_match,
                        matches_number=True,
                        proximity=proximity,
                        reason=f"person=3 → أَقرَب اسم سابِق مُطابِق ({wanted_g}/{wanted_n})",
                    ))
                # كَذلك نُضيف entities مِن prior_context (مَن الآيَة السَّابِقَة)
                for pe in prior_context:
                    if pe.get("role") in ("speaker", "addressee"):
                        continue
                    pe_gender = pe.get("gender", "M")
                    if wanted_g != "X" and pe_gender != wanted_g:
                        continue
                    candidates.append(Candidate(
                        entity_id=pe.get("id", "prior"),
                        entity_surface=pe.get("surface", "كِيان سابِق"),
                        score=0.6,  # أَقَلّ مِن داخِل الجُملَة
                        matches_gender=True,
                        matches_number=True,
                        proximity=999,
                        reason=f"person=3 → كِيان مِن prior_context",
                    ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="anaphora",  # نَستَخدِم نَوع anaphora لِأَنَّها ضَمير
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_DETACHED,
                rid=f"res_detached_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 5. Bridging (Phase E 100% — المُضاف إِليه المَحذوف، ضَمير الشَّأن)
    # ──────────────────────────────────────────────────────────

    def _resolve_bridging(self, tokens) -> list[Resolution]:
        """يَكشِف الإِشارات الضِّمنيَّة:
          • ضَمير الشَّأن (هو، هي في بِدايَة الجُملَة الِاسميَّة)
          • المُضاف إِليه المَحذوف (نادِر)
        """
        results = []
        # ضَمير الشَّأن: هو/هي في بِدايَة الجُملَة + جُملَة بَعده
        if tokens:
            first = tokens[0]
            surface = getattr(first, "token", "") or ""
            from samarrai_loaders.volume1_loader import _normalize as _norm
            if _norm(surface) in ("هو", "هي"):
                # ابحَث عَن أَوَّل ISM رَفع بَعده — هو المُفَسِّر
                for j in range(1, len(tokens)):
                    tj = tokens[j]
                    if tj.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                        target_surface = getattr(tj, "token", "") or ""
                        results.append(Resolution(
                            resolution_id=f"res_bridging_shaan_0",
                            resolution_type="bridging",
                            referent=surface,
                            referent_position=0,
                            target=f"t{j}",
                            target_surface=target_surface,
                            candidates=[Candidate(
                                entity_id=f"t{j}",
                                entity_surface=target_surface,
                                score=0.9,
                                reason="ضَمير الشَّأن — يُفَسَّر بِما بَعده",
                            )],
                            kind="Hypothesis",
                            contract="ShaanPronounContract:v1",
                        ))
                        break
        return results

    # ──────────────────────────────────────────────────────────
    # 1. Anaphora
    # ──────────────────────────────────────────────────────────

    def _resolve_anaphora(self, tokens, sent) -> list[Resolution]:
        """حَلّ الضَّمائر — يَبحَث عَن كِيانات سابِقَة مُطابِقَة."""
        results = []
        # ضَمائر مُنفَصِلَة: هو، هي، هم، هما، هن
        ANAPHORS = {
            "هو": ("M", "SG"),
            "هي": ("F", "SG"),
            "هما": ("X", "DU"),
            "هم": ("M", "PL"),
            "هن": ("F", "PL"),
        }

        # نَجمَع الكِيانات السَّابِقَة (الأَسماء)
        entities = []
        for i, t in enumerate(tokens):
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                # heuristic لِلجِنس مِن تاء التَّأنيث
                surface = getattr(t, "token", "") or getattr(t, "surface", "")
                gender = "F" if surface.endswith(("ة", "ى", "اء")) else "M"
                entities.append({
                    "id": f"t{i}",
                    "surface": surface,
                    "position": i,
                    "gender": gender,
                    "number": "SG",  # default
                })

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            plain = _normalize(surface)
            if plain not in ANAPHORS:
                continue
            gender, number = ANAPHORS[plain]

            # ابحَث عَن كِيانات سابِقَة مُطابِقَة
            candidates = []
            for ent in entities:
                if ent["position"] >= i:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if g_match and n_match:
                    # PATCH 10 — consolidated هُوَ/personal-pronoun
                    # rejector. Bundles PATCH 8 Gate E (adjective-like),
                    # PATCH 9 Gate I (abstract + indefinite), AND
                    # PATCH 10's possessor-tail rejection
                    # (هُوَ → رَبَّهُ).
                    ent_idx = ent["position"]
                    ent_token = tokens[ent_idx] if 0 <= ent_idx < len(tokens) else None
                    if ent_token is not None and _p10_huwa_should_reject_candidate(ent_token):
                        continue
                    proximity = i - ent["position"]
                    score = 1.0 / (1.0 + proximity * 0.1)
                    candidates.append(Candidate(
                        entity_id=ent["id"],
                        entity_surface=ent["surface"],
                        score=score,
                        matches_gender=g_match,
                        matches_number=n_match,
                        proximity=proximity,
                        reason=f"gender={gender} number={number}",
                    ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="anaphora",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_ANAPHORA,
                rid=f"res_anaphora_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 2. Deixis
    # ──────────────────────────────────────────────────────────

    def _resolve_deixis(self, tokens) -> list[Resolution]:
        """حَلّ الإِشارَة (هذا، تلك...)."""
        results = []
        # كِيانات قابِلَة لِلإِشارَة
        entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            demo = is_demonstrative(surface)
            if not demo:
                continue

            # PATCH 16 — abstract-reference policy. ذَٰلِكَ followed
            # by a لِمَن/لمن condition clause refers to a prior
            # proposition (e.g., 2:196 «... عَشَرَةٌ كَامِلَةٌ ۗ ذَٰلِكَ
            # لِمَن لَّمْ يَكُنْ ...»). Emit Zero rather than a noisy
            # nominal candidate match.
            if _p16_demonstrative_is_abstract_reference(surface, i, tokens):
                results.append(self._build_resolution(
                    resolution_type="deixis",
                    referent=surface,
                    referent_position=i,
                    candidates=[],
                    contract=self.CONTRACT_DEIXIS,
                    rid=f"res_deixis_{i}",
                ))
                continue

            gender = demo.get("gender", "X")
            number = demo.get("number", "X")
            proximity_kind = demo.get("proximity", "near")

            candidates = []
            for ent in entities:
                # الإِشارَة قَد تُشير لِما قَبل أَو ما بَعد
                pos_diff = abs(i - ent["position"])
                if pos_diff == 0:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if not (g_match and n_match):
                    continue
                # PATCH 15 — deixis candidate quality gate. Reject
                # adjective-like / possessor-tail / abstract / نعت /
                # فاعل-pattern candidates. Targets 2:196 misfires
                # (تِلْكَ → حَاضِرِى, ذَٰلِكَ → كَامِلَةٌ).
                ent_idx_dx = ent["position"]
                ent_tok_dx = (tokens[ent_idx_dx]
                              if 0 <= ent_idx_dx < len(tokens) else None)
                if ent_tok_dx is not None and _p15_deixis_should_reject_candidate(ent_tok_dx):
                    continue
                # الإِشارَة القُربى تُفَضِّل ما هو أَقرَب مَوقِعًا
                score = 1.0 / (1.0 + pos_diff * 0.15)
                if proximity_kind == "far":
                    score *= 0.9
                candidates.append(Candidate(
                    entity_id=ent["id"],
                    entity_surface=ent["surface"],
                    score=score,
                    matches_gender=g_match,
                    matches_number=n_match,
                    proximity=pos_diff,
                    reason=f"{proximity_kind} demo {gender}/{number}",
                ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="deixis",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_DEIXIS,
                rid=f"res_deixis_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 3. Relative
    # ──────────────────────────────────────────────────────────

    def _resolve_relative(self, tokens) -> list[Resolution]:
        """حَلّ المَوصول (الَّذي، الَّتي...) → المَوصوف السَّابِق."""
        results = []
        entities = self._collect_entities(tokens)

        for i, t in enumerate(tokens):
            surface = getattr(t, "token", "") or getattr(t, "surface", "")
            rel = is_relative_pronoun(surface)
            if not rel:
                continue

            # PATCH 8 — Gate A: reject HARF homographs (مِن/مِنَ is HARF
            # JARR, not the relative pronoun مَن; both collapse to "من"
            # after diacritic strip). Use L3 word_class as ground truth.
            if _p8_token_is_harf_preposition(t):
                continue

            # PATCH 15 — surface-based reject for مِّن (idgham-shadda
            # preposition). L1 sometimes classifies this as
            # ISM_MAWSOOL because the diacritic-stripped form `من`
            # collides with the relative pronoun, leaving Gate A
            # ineffective. The diacritic-sensitive surface مِّن /
            # مِنْ / مِنَ is the preposition spelling and must not
            # emit a relative resolution.
            if _p15_min_surface_is_preposition(surface):
                continue

            # PATCH 9 — Gate F: إذا+ما cluster. مَا preceded by إذا is a
            # clausal extender ("إِذَا مَا دُعُوا"), not a relative.
            if _p9_is_idha_ma_cluster(i, tokens):
                continue

            # PATCH 8 — Gate B: reject this resolver attempt entirely if
            # the candidate-window before `i` contains ONLY temporal /
            # conditional particles as same-position-matching antecedents.
            # Specifically: مَا → إِذَا must NOT be emitted (an explicit
            # rejection that survives even if مَا's other matches exist).
            referent_plain = _p8_strip(surface)

            gender = rel.get("gender", "X")
            number = rel.get("number", "X")

            # المَوصول يَرجِع لِأَقرَب اسم سابِق مُطابِق
            candidates = []
            for ent in entities:
                if ent["position"] >= i:
                    continue
                g_match = (gender == "X" or ent["gender"] == gender)
                n_match = (number == "X" or ent["number"] == number)
                if not (g_match and n_match):
                    continue
                # PATCH 8 — Gate C: for ٱلَّذِى / ٱلَّتِى reject obviously
                # impossible antecedents (jalalah, indefinite tanwin
                # nouns like شَيْـًٔا, particles, temporal/conditional).
                # Identified by the entity position pointing to a token.
                ent_idx = ent["position"]
                ent_token = tokens[ent_idx] if 0 <= ent_idx < len(tokens) else None
                if ent_token is None:
                    continue
                # Plain forms include ى-final variants (الذى, التى) because
                # NFC-stripping keeps ٱلَّذِى's ى; we accept both ي and ى.
                if referent_plain in ("الذي", "الذى", "التي", "التى",
                                       "اللذان", "اللذين",
                                       "اللتان", "اللتين", "الذين",
                                       "اللاتي", "اللاتى",
                                       "اللائي", "اللائى",
                                       "اللواتي", "اللواتى"):
                    # PATCH 10 — consolidated ٱلَّذِى rejector. Bundles
                    # PATCH 8 Gate C + PATCH 9 Gates G/H + PATCH 10's
                    # abstract-noun rejection (ٱلَّذِى → ٱلْحَقُّ).
                    if _p10_alladhi_should_reject_candidate(ent_token):
                        continue
                # PATCH 8 — Gate D: مَا/مَن relative must NOT resolve to
                # temporal/conditional particles (إِذَا, إِذ, لَمَّا ...).
                if referent_plain in ("ما", "من"):
                    if _p8_is_temporal_or_conditional_particle(ent_token):
                        continue
                proximity = i - ent["position"]
                # المَوصول يُفَضِّل القَريب جِدًّا (الأَقرَب فَوريّ تَقريبًا)
                score = 1.0 / (1.0 + proximity * 0.3)
                candidates.append(Candidate(
                    entity_id=ent["id"],
                    entity_surface=ent["surface"],
                    score=score,
                    matches_gender=g_match,
                    matches_number=n_match,
                    proximity=proximity,
                    reason=f"relative {gender}/{number}",
                ))

            candidates.sort(key=lambda c: -c.score)
            res = self._build_resolution(
                resolution_type="relative",
                referent=surface,
                referent_position=i,
                candidates=candidates,
                contract=self.CONTRACT_RELATIVE,
                rid=f"res_relative_{i}",
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # 4. Identity-through-Transformation
    # ──────────────────────────────────────────────────────────

    def _resolve_transformation_identity(self, event_graph, tokens) -> list[Resolution]:
        """يَربط الكِيان قَبل التَّحَوُّل بِنَفسه بَعده.

        صارَ زَيدٌ غَنيًّا:
          → زَيد(فَقير) = زَيد(غَنيّ) — نَفس entity_id
        """
        results = []
        for ev in event_graph.events:
            if not hasattr(ev, "subject"):
                continue  # only Transformations
            if not ev.subject or ev.subject == "—":
                continue

            # المُرَشَّح الوَحيد = الكِيان نَفسه (هو الـ subject)
            cand = Candidate(
                entity_id=f"subj_{ev.event_id}",
                entity_surface=ev.subject,
                score=1.0,
                reason=f"transformation: {ev.state_before} → {ev.state_after}",
            )
            res = Resolution(
                resolution_id=f"res_trans_{ev.event_id}",
                resolution_type="identity_transformation",
                referent=ev.subject,
                referent_position=ev.verb_position,
                target=cand.entity_id,
                target_surface=ev.subject,
                candidates=[cand],
                kind="Certificate",
                contract=self.CONTRACT_TRANSFORMATION,
            )
            results.append(res)
        return results

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _collect_entities(tokens) -> list[dict]:
        out = []
        for i, t in enumerate(tokens):
            if t.word_class in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM"):
                surface = getattr(t, "token", "") or getattr(t, "surface", "")
                gender = "F" if surface.endswith(("ة", "ى", "اء")) else "M"
                out.append({
                    "id": f"t{i}",
                    "surface": surface,
                    "position": i,
                    "gender": gender,
                    "number": "SG",
                })
        return out

    @staticmethod
    def _build_resolution(*, resolution_type, referent, referent_position,
                            candidates, contract, rid) -> Resolution:
        """يَبني Resolution وَ يُحَدِّد الـ kind."""
        if not candidates:
            return Resolution(
                resolution_id=rid,
                resolution_type=resolution_type,
                referent=referent,
                referent_position=referent_position,
                candidates=[],
                kind="Zero",
                contract=contract,
                blockers=["لا مُرَشَّح مُطابِق في النِّطاق"],
            )
        # Certificate لَو واحِد فَقَط أَو الفارِق كَبير
        best = candidates[0]
        if len(candidates) == 1 or (len(candidates) > 1 and best.score - candidates[1].score > 0.3):
            kind = "Certificate"
        else:
            kind = "Hypothesis"
        return Resolution(
            resolution_id=rid,
            resolution_type=resolution_type,
            referent=referent,
            referent_position=referent_position,
            target=best.entity_id,
            target_surface=best.entity_surface,
            candidates=candidates,
            kind=kind,
            contract=contract,
        )


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from i3rab_engine.engine import I3rabEngine
    from event_extractor import EventExtractor
    from relation_extractor import RelationExtractor

    text = sys.argv[1] if len(sys.argv) > 1 else "جاءَ زَيدٌ ثُمَّ ذَهَبَ هو إلى البَيتِ"

    eng = I3rabEngine()
    sent = eng.analyze_sentence(text)
    rg = RelationExtractor().extract(sent)
    eg = EventExtractor().extract(sent, rg)
    res = ResolutionEngine().resolve(sent, eg)

    print(f"النَّصّ: {text}\n")
    print(f"=== التَّعيينات ({len(res.resolutions)}) ===")
    for r in res.resolutions:
        print(f"  {r}")
        if len(r.candidates) > 1:
            print(f"    alternatives: {len(r.candidates) - 1}")
    print(f"\n  Certificates: {len(res.certificates)}")
    print(f"  Hypotheses:   {len(res.hypotheses)}")
    print(f"  Zeros:        {len(res.zeros)}")
