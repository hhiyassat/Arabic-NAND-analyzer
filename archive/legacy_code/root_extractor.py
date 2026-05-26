"""root_extractor.py — Pure rule-based root extraction.

PHILOSOPHY:
  This module extracts an Arabic root from a surface word using PURE
  morphological rules. It MUST NOT consult any database to choose the root.
  Verification against mishkat/audited_roots happens in root_verifier.py.

CONSTITUTIONAL COMMITMENTS:
  - Source-of-Claim: every extraction returns the rule_id that fired
  - Confidence-of-Claim: every candidate has confidence ∈ [0,1]
  - Alternatives-Preserved: returns ranked list, not single answer
  - Reversibility: every rule has explicit examples_pass + examples_fail

CURRENT SCOPE (phase 2.1):
  - Sound trilateral roots (سالم ثلاثي) only
  - Forms I-X (with limitations documented per rule)
  - Words containing weak letters (و، ي، ا، ى) are returned as
    "out_of_scope" — they'll be handled in phase 2.2+

API:
  extract(word: str) -> RootExtractionResult
    Returns a result with .candidates (list of Candidate), each candidate
    has .root, .wazn, .confidence, .rule_id, .transformations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import unicodedata


# ============================================================================
# Constants
# ============================================================================

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
SHADDA = "ّ"
SUKUN = "ْ"
FATHA = "َ"
KASRA = "ِ"
DAMMA = "ُ"
TANWIN_FATH = "ً"
TANWIN_KASR = "ٍ"
TANWIN_DAMM = "ٌ"

# Letters considered "weak" — words containing these are out of scope
# for the sound-trilateral phase. They'll be handled by later phases.
WEAK_LETTERS = {"و", "ي", "ا", "ى", "آ", "ٱ"}

# Hamza equivalence — for matching purposes only (extraction preserves variants)
HAMZA_VARIANTS = {"ء", "أ", "إ", "ؤ", "ئ", "آ"}


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class Candidate:
    """One root hypothesis with full provenance."""
    root: str                       # e.g. "كتب"
    wazn: str                       # e.g. "فعل" or "افتعل"
    form: str                       # I, II, III, ... or "noun"
    confidence: float               # 0.0 - 1.0
    rule_id: str                    # R-EXTRACT-S01, R-EXTRACT-S02, ...
    rule_name: str                  # human-readable name
    transformations: list[str] = field(default_factory=list)


@dataclass
class RootExtractionResult:
    """Full result of extracting roots from a word."""
    word: str                       # original (with diacritics)
    word_normalized: str            # after prefix/suffix stripping
    candidates: list[Candidate]     # ranked best-first
    out_of_scope_reason: Optional[str] = None  # if no candidates produced


# ============================================================================
# Helpers
# ============================================================================

def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def is_sound_trilateral_candidate(plain: str) -> bool:
    """True if the plain (no-diacritic) string COULD potentially be a sound
    trilateral root — i.e., has no weak letters AND no hamza.
    Used by phase 2.1 (sound) rules.
    """
    if not plain:
        return False
    for c in plain:
        if c in WEAK_LETTERS:
            return False
        if c in HAMZA_VARIANTS or c == "ء":
            return False
    return True


def is_no_weak_letter(plain: str) -> bool:
    """True if the string has no weak letters (و/ي/ا/ى/آ).
    Hamza variants are ALLOWED.
    Used by phase 2.2 (hamza) rules.
    """
    if not plain:
        return False
    for c in plain:
        if c in WEAK_LETTERS and c != "آ":  # آ handled separately
            return False
    return True


def normalize_hamza_to_baseline(s: str) -> str:
    """Convert all hamza variants (أ، إ، ؤ، ئ، آ) to canonical ء.
    Alif-madda آ expands to ءا (logical hamza + alif).
    """
    if not s:
        return s
    out = []
    for c in s:
        if c == "آ":
            out.append("ءا")
        elif c in HAMZA_VARIANTS:
            out.append("ء")
        else:
            out.append(c)
    return "".join(out)


def has_hamza(plain: str) -> bool:
    """True if the string contains at least one hamza variant."""
    return any(c in HAMZA_VARIANTS or c == "ء" for c in plain)


# ============================================================================
# Prefix / suffix stripping rules
# ============================================================================

# Order matters: longer/more-specific prefixes first
# NOTE: all patterns here are DIACRITIC-FREE since we match against word_plain
NOUN_PREFIXES = [
    # Conjunctions + preps + det stack
    ("وال", "CONJ+DET"), ("فال", "CONJ+DET"),
    ("بال", "PREP+DET"), ("كال", "PREP+DET"), ("لل", "PREP+DET"),
    # Single prefix + det
    ("ال", "DET"),
    # Single particles
    ("و", "CONJ"), ("ف", "CONJ"),
    ("ب", "PREP"), ("ك", "PREP"), ("ل", "PREP"),
]

VERB_PREFIXES = [
    # Future + imperfect
    ("سي", "FUT+IV"), ("ست", "FUT+IV"), ("سن", "FUT+IV"), ("سأ", "FUT+IV"),
    ("سوف", "FUT"),
    # Conjunction + imperfect
    ("وي", "CONJ+IV"), ("وت", "CONJ+IV"), ("ون", "CONJ+IV"), ("وأ", "CONJ+IV"),
    ("في", "CONJ+IV"), ("فت", "CONJ+IV"), ("فن", "CONJ+IV"), ("فأ", "CONJ+IV"),
    # Imperfect alone
    ("ي", "IV"), ("ت", "IV"), ("ن", "IV"), ("أ", "IV"),
]

NOUN_SUFFIXES = [
    # Plurals + duals + feminine (diacritic-free)
    ("ون", "PL_MASC"), ("ين", "PL_MASC_OBL"),
    ("ات", "PL_FEM"),
    ("ان", "DUAL"),
    # Pronominal suffixes
    ("هما", "POSS_DUAL"), ("هن", "POSS_FEM_PL"), ("هم", "POSS_MASC_PL"),
    ("كما", "POSS_DUAL"), ("كن", "POSS_FEM_PL"), ("كم", "POSS_MASC_PL"),
    ("ها", "POSS_FEM_SG"), ("ه", "POSS_MASC_SG"), ("ك", "POSS_2ND_SG"),
    ("نا", "POSS_1ST_PL"), ("ي", "POSS_1ST_SG"),
    # Case markers
    ("ة", "FEM"),
]

VERB_SUFFIXES = [
    ("تما", "PV_2ND_DU"), ("تن", "PV_2ND_FEM_PL"), ("تم", "PV_2ND_MASC_PL"),
    ("نا", "PV_1ST_PL"), ("ت", "PV_2ND_OR_3RD_FEM"),
    ("وا", "PV_3RD_PL_MASC"), ("ن", "PV_3RD_FEM_PL"),
    ("ون", "IV_PL_MASC"), ("ين", "IV_PL_FEM"),
]


def _peel_prefix(word: str, candidates: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Strip the longest matching prefix from `word` once. Returns (rest, [tag])."""
    for pref, tag in sorted(candidates, key=lambda x: -len(x[0])):
        if word.startswith(pref):
            return word[len(pref):], [f"prefix_{tag}={pref}"]
    return word, []


def _peel_suffix(word: str, candidates: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Strip the longest matching suffix from `word` once."""
    for suf, tag in sorted(candidates, key=lambda x: -len(x[0])):
        if word.endswith(suf):
            return word[:-len(suf)], [f"suffix_{tag}={suf}"]
    return word, []


# ============================================================================
# Wazn-pattern rules — each defines how to extract root letters from a stem
# ============================================================================

@dataclass
class WaznRule:
    """A single morphological pattern rule."""
    rule_id: str
    name: str
    form: str                     # I, II, III, ... or "noun"
    wazn: str                     # the pattern, e.g. "فعل" or "افتعل"
    stem_length_after_diac_strip: int
    extract_fn: callable          # (stem_plain: str) -> Optional[str]   (returns 3-letter root or None)
    examples_pass: list[tuple[str, str]]  # (stem_plain, expected_root)
    examples_fail: list[str] = field(default_factory=list)
    confidence: float = 0.9
    version: str = "1.0"


# --- Rule R-EXTRACT-S01: Form I sound trilateral (فَعَل) ---
def _extract_form_I_sound(stem_plain: str) -> Optional[str]:
    """فَعَل / فَعِل / فَعُل — exactly 3 sound consonants."""
    if len(stem_plain) == 3 and is_sound_trilateral_candidate(stem_plain):
        return stem_plain
    return None


R_S01 = WaznRule(
    rule_id="R-EXTRACT-S01",
    name="Form I sound trilateral (فَعَل)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_form_I_sound,
    examples_pass=[("كتب", "كتب"), ("ذهب", "ذهب"), ("شرب", "شرب")],
    confidence=0.95,
)


# --- Rule R-EXTRACT-S02: Form II (فَعَّل) — middle letter doubled ---
def _extract_form_II_sound(stem_plain: str) -> Optional[str]:
    """فَعَّل with shadda stripped → فعل (3 letters). After shadda strip,
    the middle letter appears once. Sound trilateral version.

    Note: by the time we get here, shadda was stripped during normalization.
    So Form II's surface "كتّب" → "كتب" (same as Form I). We can't distinguish
    Form II from Form I at the stem level alone — both extract to same root.
    """
    if len(stem_plain) == 3 and is_sound_trilateral_candidate(stem_plain):
        return stem_plain
    return None


R_S02 = WaznRule(
    rule_id="R-EXTRACT-S02",
    name="Form II sound (فَعَّل)",
    form="II",
    wazn="فعّل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_form_II_sound,
    examples_pass=[("كتب", "كتب"), ("علم", "علم")],
    confidence=0.8,  # ambiguous with Form I from stem alone
)


# --- Rule R-EXTRACT-S03: Form III (فَاعَل) — alif between L1 and L2 ---
def _extract_form_III_sound(stem_plain: str) -> Optional[str]:
    """فَاعَل: drop the ا that sits between L1 and L2.
    Surface like "كاتب" (4 letters) → root "كتب"."""
    if len(stem_plain) == 4 and stem_plain[1] == "ا":
        candidate = stem_plain[0] + stem_plain[2] + stem_plain[3]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S03 = WaznRule(
    rule_id="R-EXTRACT-S03",
    name="Form III (فَاعَل)",
    form="III",
    wazn="فاعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_form_III_sound,
    examples_pass=[("كاتب", "كتب"), ("شارك", "شرك")],
    confidence=0.9,
)


# --- Rule R-EXTRACT-S04: Form V (تَفَعَّل) — ت prefix ---
def _extract_form_V_sound(stem_plain: str) -> Optional[str]:
    """تَفَعَّل: drop the leading ت."""
    if len(stem_plain) == 4 and stem_plain[0] == "ت":
        candidate = stem_plain[1:]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S04 = WaznRule(
    rule_id="R-EXTRACT-S04",
    name="Form V (تَفَعَّل)",
    form="V",
    wazn="تفعّل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_form_V_sound,
    examples_pass=[("تعلم", "علم"), ("تكلم", "كلم")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-S05: Form VI (تَفَاعَل) — ت + ا ---
def _extract_form_VI_sound(stem_plain: str) -> Optional[str]:
    """تَفَاعَل: drop ت + ا → 3-letter root."""
    if len(stem_plain) == 5 and stem_plain[0] == "ت" and stem_plain[2] == "ا":
        candidate = stem_plain[1] + stem_plain[3] + stem_plain[4]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S05 = WaznRule(
    rule_id="R-EXTRACT-S05",
    name="Form VI (تَفَاعَل)",
    form="VI",
    wazn="تفاعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_VI_sound,
    examples_pass=[("تعارف", "عرف"), ("تشارك", "شرك")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-S06: Form VII (انفعل) — ا + ن ---
def _extract_form_VII_sound(stem_plain: str) -> Optional[str]:
    """انفَعَل: drop ا + ن → 3-letter root."""
    if len(stem_plain) == 5 and stem_plain[0] == "ا" and stem_plain[1] == "ن":
        candidate = stem_plain[2:]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S06 = WaznRule(
    rule_id="R-EXTRACT-S06",
    name="Form VII (انْفَعَل)",
    form="VII",
    wazn="انفعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_VII_sound,
    examples_pass=[("انكسر", "كسر"), ("انفطر", "فطر")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-S07: Form VIII (افتعل) — ا + ت ---
def _extract_form_VIII_sound(stem_plain: str) -> Optional[str]:
    """افتَعَل: drop ا + ت → 3-letter root."""
    if len(stem_plain) == 5 and stem_plain[0] == "ا" and stem_plain[2] == "ت":
        candidate = stem_plain[1] + stem_plain[3] + stem_plain[4]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S07 = WaznRule(
    rule_id="R-EXTRACT-S07",
    name="Form VIII (افْتَعَل)",
    form="VIII",
    wazn="افتعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_VIII_sound,
    examples_pass=[("اشترك", "شرك"), ("اقتسم", "قسم")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-S08: Form X (استفعل) — ا + س + ت ---
def _extract_form_X_sound(stem_plain: str) -> Optional[str]:
    """استَفْعَل: drop ا + س + ت → 3-letter root."""
    if len(stem_plain) == 6 and stem_plain[:3] == "است":
        candidate = stem_plain[3:]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S08 = WaznRule(
    rule_id="R-EXTRACT-S08",
    name="Form X (اسْتَفْعَل)",
    form="X",
    wazn="استفعل",
    stem_length_after_diac_strip=6,
    extract_fn=_extract_form_X_sound,
    examples_pass=[("استخرج", "خرج"), ("استغفر", "غفر")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-S09: مَفْعَل / مَفْعِل / مَفْعَلَة (noun derivation) ---
def _extract_noun_meem(stem_plain: str) -> Optional[str]:
    """Nouns starting with م: مَفْعَل، مَفْعِل، مَفْعَلَة → drop م."""
    if len(stem_plain) == 4 and stem_plain[0] == "م":
        candidate = stem_plain[1:]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S09 = WaznRule(
    rule_id="R-EXTRACT-S09",
    name="Noun pattern مَفْعَل / مَفْعِل",
    form="noun",
    wazn="مفعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_noun_meem,
    examples_pass=[("مكتب", "كتب"), ("مذهب", "ذهب"), ("مشرق", "شرق")],
    confidence=0.8,
)


# --- Rule R-EXTRACT-S10: مَفْعُول (passive participle) ---
def _extract_mafuul(stem_plain: str) -> Optional[str]:
    """مَفْعُول: drop م + و → 3-letter root."""
    if len(stem_plain) == 5 and stem_plain[0] == "م" and stem_plain[3] == "و":
        candidate = stem_plain[1] + stem_plain[2] + stem_plain[4]
        if is_sound_trilateral_candidate(candidate):
            return candidate
    return None


R_S10 = WaznRule(
    rule_id="R-EXTRACT-S10",
    name="Passive participle (مَفْعُول)",
    form="noun",
    wazn="مفعول",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_mafuul,
    examples_pass=[("مكتوب", "كتب"), ("مشروب", "شرب"), ("مشهور", "شهر")],
    confidence=0.9,
)


# All sound-trilateral rules in priority order (longer/more-specific first)
SOUND_TRILATERAL_RULES = [
    R_S08, R_S10, R_S05, R_S06, R_S07, R_S04, R_S03, R_S09, R_S01, R_S02,
]


# ============================================================================
# Phase 2.2: Hamza-trilateral rules (مهموز الفاء / العين / اللام)
# ============================================================================
# Approach: normalize all hamza variants (أ، إ، ؤ، ئ، آ) → ء before extraction.
# Then the same Form-I-X patterns work, with one extra rule for Form IV
# (أَفْعَل) where the LEADING أ is the form's prefix, not a root letter.

def _is_hamza_3_letters(stem_plain: str) -> bool:
    """True if stem is 3 letters and contains a hamza (otherwise sound rules handle it)."""
    if len(stem_plain) != 3:
        return False
    if not has_hamza(stem_plain):
        return False
    # Reject pure weak letters (this distinguishes hamza from weak)
    for c in stem_plain:
        if c in WEAK_LETTERS and c != "آ":
            return False
    return True


# --- Rule R-EXTRACT-H01: Form I hamzated trilateral (any position) ---
def _extract_form_I_hamza(stem_plain: str) -> Optional[str]:
    """Form I with hamza in any of the 3 root positions.
    Examples: أكل → ءكل, سأل → سءل, قرأ → قرء
    """
    if _is_hamza_3_letters(stem_plain):
        # Normalize hamza variants to canonical ء
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in stem_plain)
    return None


R_H01 = WaznRule(
    rule_id="R-EXTRACT-H01",
    name="Form I hamzated trilateral",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_form_I_hamza,
    examples_pass=[("أكل", "ءكل"), ("سأل", "سءل"), ("قرأ", "قرء"),
                   ("أمر", "ءمر"), ("أخذ", "ءخذ")],
    confidence=0.95,
)


# --- Rule R-EXTRACT-H02: Form IV (أَفْعَل) — leading أ is FORM prefix not root ---
def _extract_form_IV_hamza(stem_plain: str) -> Optional[str]:
    """أَفْعَل: 4 letters starting with أ, root is letters [1:4].
    Examples: أكرم → كرم, أحسن → حسن, أرسل → رسل.

    AMBIGUITY: if root is مهموز الفاء (root[0]=ء), then أَفْعَل surface
    becomes "آفعل" (alif-madda from أ + ء). That's handled by H04 below.
    """
    if len(stem_plain) != 4:
        return None
    if stem_plain[0] not in ("أ", "ء"):
        return None
    candidate = stem_plain[1:]
    # Should be sound or hamzated trilateral
    if is_no_weak_letter(candidate):
        # Don't return if the root would itself start with hamza (that's Form I)
        return candidate if not (candidate[0] in HAMZA_VARIANTS or candidate[0] == "ء") else None
    return None


R_H02 = WaznRule(
    rule_id="R-EXTRACT-H02",
    name="Form IV (أَفْعَل)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_form_IV_hamza,
    examples_pass=[("أكرم", "كرم"), ("أحسن", "حسن"), ("أرسل", "رسل")],
    confidence=0.9,
)


# --- Rule R-EXTRACT-H03: Form II hamzated (فَعَّل with hamza in root) ---
def _extract_form_II_hamza(stem_plain: str) -> Optional[str]:
    """فَعَّل with hamza in one of the 3 root letters."""
    if _is_hamza_3_letters(stem_plain):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in stem_plain)
    return None


R_H03 = WaznRule(
    rule_id="R-EXTRACT-H03",
    name="Form II hamzated (فَعَّل)",
    form="II",
    wazn="فعّل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_form_II_hamza,
    examples_pass=[("أكل", "ءكل"), ("أمر", "ءمر")],
    confidence=0.8,
)


# --- Rule R-EXTRACT-H04: Form IV of hamza-initial root (آفَعَل) ---
def _extract_form_IV_hamza_initial(stem_plain: str) -> Optional[str]:
    """آفَعَل from root ء.f.l → surface starts with آ.
    After "آ → ءا" expansion, stem starts with "ءا".
    Length after expansion: 5, drop "ء + ا" → 3-letter root starting with ء.
    Example: آمن → ءمن (root ءمن, Form IV).
    """
    if len(stem_plain) != 5:
        return None
    if not stem_plain.startswith("ءا"):
        return None
    candidate = "ء" + stem_plain[2:]
    if len(candidate) == 4 and is_no_weak_letter(candidate[1:]):
        return candidate
    return None


R_H04 = WaznRule(
    rule_id="R-EXTRACT-H04",
    name="Form IV of hamza-initial root (آفَعَل)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_IV_hamza_initial,
    examples_pass=[("ءامن", "ءمن")],  # post آ→ءا normalization; final-weak goes to phase 2.3+
    confidence=0.85,
)


# --- Rule R-EXTRACT-H05: Active participle (فاعل) with hamza in root ---
def _extract_active_participle_hamza(stem_plain: str) -> Optional[str]:
    """فاعِل (active participle): drop ا at position 1.
    Examples: آكِل → ءكل, سائل → سءل, قارئ → قرء.
    """
    if len(stem_plain) != 4 or stem_plain[1] != "ا":
        return None
    candidate = stem_plain[0] + stem_plain[2] + stem_plain[3]
    candidate = "".join(("ء" if c in HAMZA_VARIANTS else c) for c in candidate)
    if has_hamza(candidate) and is_no_weak_letter(candidate):
        return candidate
    return None


R_H05 = WaznRule(
    rule_id="R-EXTRACT-H05",
    name="Active participle hamzated (فاعِل)",
    form="active_participle",
    wazn="فاعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_active_participle_hamza,
    examples_pass=[("سائل", "سءل"), ("قارئ", "قرء")],
    confidence=0.85,
)


# --- Rule R-EXTRACT-H06: Passive participle (مفعول) with hamza in root ---
def _extract_mafuul_hamza(stem_plain: str) -> Optional[str]:
    """مَفْعُول with hamza in root.
    Example: مأكول → ءكل, مسؤول → سءل, مقروء → قرء.
    """
    if len(stem_plain) != 5 or stem_plain[0] != "م" or stem_plain[3] != "و":
        return None
    candidate = stem_plain[1] + stem_plain[2] + stem_plain[4]
    candidate = "".join(("ء" if c in HAMZA_VARIANTS else c) for c in candidate)
    if has_hamza(candidate) and is_no_weak_letter(candidate):
        return candidate
    return None


R_H06 = WaznRule(
    rule_id="R-EXTRACT-H06",
    name="Passive participle hamzated (مَفْعُول)",
    form="passive_participle",
    wazn="مفعول",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_mafuul_hamza,
    examples_pass=[("مءكول", "ءكل"), ("مسءول", "سءل")],
    confidence=0.9,
)


HAMZA_TRILATERAL_RULES = [R_H04, R_H06, R_H05, R_H02, R_H01, R_H03]


# ============================================================================
# Phase 2.3: Hollow roots (الأجوف) — middle letter is و or ي
# ============================================================================
# Strategy: when surface is 3 letters with middle ا (e.g., قال), return BOTH
# قول and قيل as candidates. Verifier picks the one attested in references.

def _is_hollow_pattern_3(stem_plain: str) -> bool:
    """3-letter stem with middle ا (hollow pattern)."""
    return len(stem_plain) == 3 and stem_plain[1] == "ا" and \
           stem_plain[0] not in WEAK_LETTERS and stem_plain[2] not in WEAK_LETTERS


def _extract_hollow_form_I(stem_plain: str) -> Optional[list[str]]:
    """قال/باع/نام → return both [قول, قيل] candidates."""
    if not _is_hollow_pattern_3(stem_plain):
        return None
    return [stem_plain[0] + "و" + stem_plain[2],
            stem_plain[0] + "ي" + stem_plain[2]]


# We'll handle multi-candidate rules differently — see below.

R_OL01_W = WaznRule(
    rule_id="R-EXTRACT-OL01a",
    name="Hollow Form I (و-variant)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=lambda s: (s[0] + "و" + s[2]) if _is_hollow_pattern_3(s) else None,
    examples_pass=[("قال", "قول"), ("نام", "نوم"), ("خاف", "خوف")],
    confidence=0.85,
)

R_OL01_Y = WaznRule(
    rule_id="R-EXTRACT-OL01b",
    name="Hollow Form I (ي-variant)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=lambda s: (s[0] + "ي" + s[2]) if _is_hollow_pattern_3(s) else None,
    examples_pass=[("باع", "بيع"), ("سار", "سير"), ("طاب", "طيب")],
    confidence=0.85,
)


# --- R-EXTRACT-OL02: Hollow Form IV (أَفَعَل with hollow root) ---
def _extract_hollow_form_IV(stem_plain: str, vowel: str) -> Optional[str]:
    """أَقَامَ/أَنَامَ — 4 letters: أ + 2-letter stem + ا? Actually surface is
    أَقَامَ → 4 letters: أ ق ا م. Root: ق و م.
    Pattern: أ + L1 + ا + L3 → root L1 + (و/ي) + L3.
    """
    if len(stem_plain) != 4:
        return None
    if stem_plain[0] != "أ":
        return None
    if stem_plain[2] != "ا":
        return None
    return stem_plain[1] + vowel + stem_plain[3]


R_OL02_W = WaznRule(
    rule_id="R-EXTRACT-OL02a",
    name="Hollow Form IV (و-variant) (أَفَعَل)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_form_IV(s, "و"),
    examples_pass=[("أقام", "قوم"), ("أنام", "نوم")],
    confidence=0.85,
)

R_OL02_Y = WaznRule(
    rule_id="R-EXTRACT-OL02b",
    name="Hollow Form IV (ي-variant)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_form_IV(s, "ي"),
    examples_pass=[("أراد", "ريد"), ("أعان", "عين")],
    confidence=0.85,
)


# --- R-EXTRACT-OL03: Hollow Form VIII (افْتَعَل) ---
# اختار → خ ي ر, اعتاد → ع و د
def _extract_hollow_form_VIII(stem_plain: str, vowel: str) -> Optional[str]:
    """افْتَعَل with hollow root: 5 letters ا + L1 + ت + ا + L3 → root L1+v+L3.
    Examples: اختار → خ + ي + ر (ي variant); اعتاد → ع + و + د (و variant).
    """
    if len(stem_plain) != 5:
        return None
    if stem_plain[0] != "ا" or stem_plain[2] != "ت" or stem_plain[3] != "ا":
        return None
    return stem_plain[1] + vowel + stem_plain[4]


R_OL03_W = WaznRule(
    rule_id="R-EXTRACT-OL03a",
    name="Hollow Form VIII (و-variant)",
    form="VIII",
    wazn="افتعل",
    stem_length_after_diac_strip=5,
    extract_fn=lambda s: _extract_hollow_form_VIII(s, "و"),
    examples_pass=[("اعتاد", "عود")],
    confidence=0.8,
)

R_OL03_Y = WaznRule(
    rule_id="R-EXTRACT-OL03b",
    name="Hollow Form VIII (ي-variant)",
    form="VIII",
    wazn="افتعل",
    stem_length_after_diac_strip=5,
    extract_fn=lambda s: _extract_hollow_form_VIII(s, "ي"),
    examples_pass=[("اختار", "خير"), ("اعتاش", "عيش")],
    confidence=0.8,
)


# --- R-EXTRACT-OL04: Hollow Form X (استَفَعَل) ---
# استقام → ق و م, استعان → ع و ن
def _extract_hollow_form_X(stem_plain: str, vowel: str) -> Optional[str]:
    """استَفَعَل with hollow root: 6 letters ا + س + ت + L1 + ا + L3."""
    if len(stem_plain) != 6:
        return None
    if stem_plain[:3] != "است" or stem_plain[4] != "ا":
        return None
    return stem_plain[3] + vowel + stem_plain[5]


R_OL04_W = WaznRule(
    rule_id="R-EXTRACT-OL04a",
    name="Hollow Form X (و-variant)",
    form="X",
    wazn="استفعل",
    stem_length_after_diac_strip=6,
    extract_fn=lambda s: _extract_hollow_form_X(s, "و"),
    examples_pass=[("استقام", "قوم"), ("استعان", "عون")],
    confidence=0.85,
)


# --- R-EXTRACT-OL05: Hollow active participle (فاعل) — uses ء substitute ---
# قائل → قول, سائر → سير, بائع → بيع
def _extract_hollow_active_participle(stem_plain: str, vowel: str) -> Optional[str]:
    """4 letters: L1 + ا + ء + L3 → root L1 + (و/ي) + L3."""
    if len(stem_plain) != 4:
        return None
    if stem_plain[1] != "ا":
        return None
    if stem_plain[2] not in ("ء", "ئ"):
        return None
    return stem_plain[0] + vowel + stem_plain[3]


R_OL05_W = WaznRule(
    rule_id="R-EXTRACT-OL05a",
    name="Hollow active participle (و)",
    form="active_participle",
    wazn="فاعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_active_participle(s, "و"),
    examples_pass=[("قائل", "قول")],
    confidence=0.85,
)

R_OL05_Y = WaznRule(
    rule_id="R-EXTRACT-OL05b",
    name="Hollow active participle (ي)",
    form="active_participle",
    wazn="فاعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_active_participle(s, "ي"),
    examples_pass=[("بائع", "بيع"), ("سائر", "سير")],
    confidence=0.85,
)


# --- R-EXTRACT-OL06: Passive participle hollow ---
# مقول → قول, مبيع → بيع. Pattern: م + L1 + (و/ي) + L3, 4 letters.
def _extract_hollow_passive_participle(stem_plain: str, vowel: str) -> Optional[str]:
    """مَفُول/مَفِيل: 4 letters م + L1 + (و/ي) + L3."""
    if len(stem_plain) != 4 or stem_plain[0] != "م":
        return None
    if stem_plain[2] != vowel:
        return None
    return stem_plain[1] + vowel + stem_plain[3]


R_OL06_W = WaznRule(
    rule_id="R-EXTRACT-OL06a",
    name="Hollow passive participle (مَفُول)",
    form="passive_participle",
    wazn="مفعول",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_passive_participle(s, "و"),
    examples_pass=[("مقول", "قول")],
    confidence=0.8,
)

R_OL06_Y = WaznRule(
    rule_id="R-EXTRACT-OL06b",
    name="Hollow passive participle (مَفِيل)",
    form="passive_participle",
    wazn="مفعيل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_hollow_passive_participle(s, "ي"),
    examples_pass=[("مبيع", "بيع")],
    confidence=0.8,
)


# --- R-EXTRACT-OL07: Hollow IV imperfect: surface has و/ي visible ---
# يقول → root قول directly (stem after stripping ي = قول)
# يبيع → root بيع directly
def _extract_hollow_3_letters_with_weak(stem_plain: str) -> Optional[str]:
    """3-letter stem with و or ي in middle (already in root form)."""
    if len(stem_plain) != 3:
        return None
    if stem_plain[1] not in ("و", "ي"):
        return None
    if stem_plain[0] in WEAK_LETTERS or stem_plain[2] in WEAK_LETTERS:
        return None
    return stem_plain


R_OL07 = WaznRule(
    rule_id="R-EXTRACT-OL07",
    name="Hollow stem already in root form (يَقُول → قول)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_hollow_3_letters_with_weak,
    examples_pass=[("قول", "قول"), ("بيع", "بيع"), ("نوم", "نوم")],
    confidence=0.9,
)


HOLLOW_RULES = [
    R_OL04_W, R_OL05_W, R_OL05_Y, R_OL06_W, R_OL06_Y,
    R_OL03_W, R_OL03_Y, R_OL02_W, R_OL02_Y,
    R_OL01_W, R_OL01_Y, R_OL07,
]


# ============================================================================
# Phase 2.4: Defective roots (الناقص) — final letter is و/ي
# ============================================================================
# Examples: دعا (د ع و), رمى (ر م ي), هدى (ه د ي)

def _extract_defective_form_I(stem_plain: str, final_letter: str) -> Optional[str]:
    """Form I defective: 3 letters where last is ا (from و) or ى (from ي).
    Surface رمى → root ر م ي. Surface دعا → root د ع و.
    """
    if len(stem_plain) != 3:
        return None
    if stem_plain[2] not in ("ا", "ى"):
        return None
    if stem_plain[0] in WEAK_LETTERS or stem_plain[1] in WEAK_LETTERS:
        return None
    return stem_plain[0] + stem_plain[1] + final_letter


R_DEF01_W = WaznRule(
    rule_id="R-EXTRACT-DEF01a",
    name="Defective Form I (و-final)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=lambda s: _extract_defective_form_I(s, "و"),
    examples_pass=[("دعا", "دعو"), ("شكا", "شكو")],
    confidence=0.85,
)

R_DEF01_Y = WaznRule(
    rule_id="R-EXTRACT-DEF01b",
    name="Defective Form I (ي-final)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=lambda s: _extract_defective_form_I(s, "ي"),
    examples_pass=[("رمى", "رمي"), ("هدى", "هدي")],
    confidence=0.85,
)


def _extract_defective_already_form(stem_plain: str) -> Optional[str]:
    """3-letter stem with و/ي as last (already in root form).
    Example: يدعو (after ي- strip) → دعو ; يرمي → رمي."""
    if len(stem_plain) != 3:
        return None
    if stem_plain[2] not in ("و", "ي"):
        return None
    if stem_plain[0] in WEAK_LETTERS or stem_plain[1] in WEAK_LETTERS:
        return None
    return stem_plain


R_DEF02 = WaznRule(
    rule_id="R-EXTRACT-DEF02",
    name="Defective stem already in root form (يدعو → دعو)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_defective_already_form,
    examples_pass=[("دعو", "دعو"), ("رمي", "رمي"), ("هدي", "هدي")],
    confidence=0.9,
)


# Form IV defective: أَفَعَى (أعطى → ع ط و). 4 letters أ + 3-letter defective.
def _extract_defective_form_IV(stem_plain: str, final: str) -> Optional[str]:
    if len(stem_plain) != 4:
        return None
    if stem_plain[0] != "أ":
        return None
    if stem_plain[3] not in ("ا", "ى"):
        return None
    return stem_plain[1] + stem_plain[2] + final


R_DEF03_W = WaznRule(
    rule_id="R-EXTRACT-DEF03a",
    name="Defective Form IV (و-final)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_defective_form_IV(s, "و"),
    examples_pass=[("أعطى", "عطو")],
    confidence=0.8,
)

R_DEF03_Y = WaznRule(
    rule_id="R-EXTRACT-DEF03b",
    name="Defective Form IV (ي-final)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=lambda s: _extract_defective_form_IV(s, "ي"),
    examples_pass=[("أبكى", "بكي"), ("أحيى", "حيي")],
    confidence=0.8,
)


DEFECTIVE_RULES = [R_DEF03_W, R_DEF03_Y, R_DEF01_W, R_DEF01_Y, R_DEF02]


# ============================================================================
# Phase 2.5: Assimilated roots (المثال) — first letter is و or ي
# ============================================================================
# Examples: وصل (و ص ل), وعد (و ع د), يسر (ي س ر)
# Imperfect form drops the و: يصل from وصل, يعد from وعد

def _extract_assimilated_form_I(stem_plain: str) -> Optional[str]:
    """3-letter stem with و or ي at position 0."""
    if len(stem_plain) != 3:
        return None
    if stem_plain[0] not in ("و", "ي"):
        return None
    if stem_plain[1] in WEAK_LETTERS or stem_plain[2] in WEAK_LETTERS:
        return None
    return stem_plain


R_AS01 = WaznRule(
    rule_id="R-EXTRACT-AS01",
    name="Assimilated stem already in root form",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_assimilated_form_I,
    examples_pass=[("وصل", "وصل"), ("وعد", "وعد"), ("يسر", "يسر")],
    confidence=0.9,
)


# Form IV assimilated: أَوْصَل → root و ص ل. Surface 4 letters: أ + و + L2 + L3
def _extract_assimilated_form_IV(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 4 or stem_plain[0] != "أ":
        return None
    if stem_plain[1] not in ("و", "ي"):
        return None
    return stem_plain[1] + stem_plain[2] + stem_plain[3]


R_AS02 = WaznRule(
    rule_id="R-EXTRACT-AS02",
    name="Assimilated Form IV (أَوْفَعَل)",
    form="IV",
    wazn="أفعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_assimilated_form_IV,
    examples_pass=[("أوصل", "وصل"), ("أوجد", "وجد")],
    confidence=0.85,
)


# Form VIII assimilated: اتّصل ← ا + و + ت + ص + ل → اتصل (و → ت).
# The doubled ت represents the assimilated و.
def _extract_assimilated_form_VIII(stem_plain: str) -> Optional[str]:
    """4 letters: ا + ت + L2 + L3, assuming و was assimilated.
    Examples: اتصل → root وصل, اتفق → root وفق."""
    if len(stem_plain) != 4:
        return None
    if stem_plain[0] != "ا" or stem_plain[1] != "ت":
        return None
    return "و" + stem_plain[2] + stem_plain[3]


R_AS03 = WaznRule(
    rule_id="R-EXTRACT-AS03",
    name="Assimilated Form VIII (اتّصل ← وصل)",
    form="VIII",
    wazn="افتعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_assimilated_form_VIII,
    examples_pass=[("اتصل", "وصل"), ("اتفق", "وفق")],
    confidence=0.75,
)


# Passive participle assimilated: موصول → root وصل
def _extract_assimilated_passive(stem_plain: str) -> Optional[str]:
    """مَفْعُول pattern: م + و + ص + و + ل (5 letters). The first و is the
    root letter (assimilated nature of root is irrelevant here — it's the
    passive participle pattern of a و-initial root).
    Actually: surface موصول for root وصل → م + و + ص + و + ل = 5 letters
    Pattern: م + root[0] + root[1] + و + root[2] = م + و + ص + و + ل.
    """
    if len(stem_plain) != 5 or stem_plain[0] != "م" or stem_plain[3] != "و":
        return None
    if stem_plain[1] not in ("و", "ي"):
        return None
    return stem_plain[1] + stem_plain[2] + stem_plain[4]


R_AS04 = WaznRule(
    rule_id="R-EXTRACT-AS04",
    name="Assimilated passive participle (موصول)",
    form="passive_participle",
    wazn="مفعول",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_assimilated_passive,
    examples_pass=[("موصول", "وصل"), ("مولود", "ولد")],
    confidence=0.8,
)


ASSIMILATED_RULES = [R_AS04, R_AS02, R_AS03, R_AS01]


# ============================================================================
# Phase 2.6: Doubled roots (المضاعف) — L2 == L3
# ============================================================================
# Examples: ردّ (ر د د), شدّ (ش د د), مدّ (م د د)
# Surface has shadda compressing the doubled letter.

def _expand_shadda(s: str) -> str:
    """Expand each shadda by duplicating the preceding letter.
    Note: input has diacritics stripped, so we operate on plain letters.
    Shadda was already removed by strip_diacritics. We can't easily
    reconstruct without the original.

    This helper is meant for use BEFORE diacritic strip — but our pipeline
    strips first. So doubled-root detection uses a different signal:
    surface length 2 → expand to 3 by duplicating L2.
    """
    return s


def _extract_doubled_form_I(stem_plain: str) -> Optional[str]:
    """Doubled root Form I past: 2-letter surface (after stripping diacritics
    and shadda). Examples: رد (from ردّ) → ر د د. شد → ش د د.
    """
    if len(stem_plain) != 2:
        return None
    if stem_plain[0] in WEAK_LETTERS or stem_plain[1] in WEAK_LETTERS:
        return None
    return stem_plain + stem_plain[1]


R_DBL01 = WaznRule(
    rule_id="R-EXTRACT-DBL01",
    name="Doubled root Form I (2-letter surface)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=2,
    extract_fn=_extract_doubled_form_I,
    examples_pass=[("رد", "ردد"), ("شد", "شدد"), ("مد", "مدد")],
    confidence=0.85,
)


def _extract_doubled_3_letters(stem_plain: str) -> Optional[str]:
    """Doubled root surface where the geminate IS written explicitly.
    E.g., رَدَد (rare verbal form), but more importantly: noun forms where
    the doubled letter appears twice. Just verify L2 == L3."""
    if len(stem_plain) != 3:
        return None
    if stem_plain[1] != stem_plain[2]:
        return None
    if stem_plain[0] in WEAK_LETTERS:
        return None
    return stem_plain


R_DBL02 = WaznRule(
    rule_id="R-EXTRACT-DBL02",
    name="Doubled root explicit (e.g., حدَد → حدد)",
    form="I",
    wazn="فعل",
    stem_length_after_diac_strip=3,
    extract_fn=_extract_doubled_3_letters,
    examples_pass=[("ردد", "ردد"), ("شدد", "شدد")],
    confidence=0.9,
)


# Form X doubled: استمدّ → root م د د. Surface استمد (5 letters: ا س ت م د).
def _extract_doubled_form_X(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5:
        return None
    if stem_plain[:3] != "است":
        return None
    last = stem_plain[3:]
    if len(last) != 2 or last[0] in WEAK_LETTERS or last[1] in WEAK_LETTERS:
        return None
    return last + last[1]


R_DBL03 = WaznRule(
    rule_id="R-EXTRACT-DBL03",
    name="Doubled Form X (استمد ← م د د)",
    form="X",
    wazn="استفعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_doubled_form_X,
    examples_pass=[("استمد", "مدد"), ("استعد", "عدد")],
    confidence=0.8,
)


DOUBLED_RULES = [R_DBL03, R_DBL02, R_DBL01]


# ============================================================================
# Phase 2.7: Quadriliteral roots (الرباعي)
# ============================================================================
# Examples: دحرج (د ح ر ج), بعثر, زلزل

def _is_sound_quad(plain: str) -> bool:
    """4 letters, all sound (no weak, no hamza)."""
    return (len(plain) == 4 and
            all(c not in WEAK_LETTERS and c not in HAMZA_VARIANTS and c != "ء"
                for c in plain))


def _extract_quad_form_I(stem_plain: str) -> Optional[str]:
    """فَعْلَل: 4 sound letters. دحرج → د ح ر ج."""
    if _is_sound_quad(stem_plain):
        return stem_plain
    return None


R_QD01 = WaznRule(
    rule_id="R-EXTRACT-QD01",
    name="Quadriliteral Form I (فَعْلَل)",
    form="I_quad",
    wazn="فعلل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_quad_form_I,
    examples_pass=[("دحرج", "دحرج"), ("بعثر", "بعثر"), ("زلزل", "زلزل")],
    confidence=0.85,
)


# Quad Form II (تَفَعْلَل): تدحرج → د ح ر ج. 5 letters with leading ت.
def _extract_quad_form_II(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5:
        return None
    if stem_plain[0] != "ت":
        return None
    cand = stem_plain[1:]
    return cand if _is_sound_quad(cand) else None


R_QD02 = WaznRule(
    rule_id="R-EXTRACT-QD02",
    name="Quad Form II (تَفَعْلَل)",
    form="II_quad",
    wazn="تفعلل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_quad_form_II,
    examples_pass=[("تدحرج", "دحرج"), ("تبعثر", "بعثر")],
    confidence=0.85,
)


QUAD_RULES = [R_QD02, R_QD01]


# ============================================================================
# Phase 2.8: Specialized — alif-maqsura ى as root letter (final-weak ي)
# ============================================================================
# Final ى often comes from underlying ي — handled by DEFECTIVE_RULES.
# But surface forms also write ى for some cases. Add coverage rule.

# ============================================================================
# Phase 2.8: Verbal nouns (مصادر) — derived forms with distinctive patterns
# ============================================================================

# Form I verbal nouns: فِعَال (كِتَاب), فُعُول (دُخُول), فَعَال (طَعَام)
def _extract_fi3al_VN(stem_plain: str) -> Optional[str]:
    """فِعَال/فَعَال/فُعَال pattern: 4 letters with ا in position 2.
    Examples: كتاب → كتب, شراب → شرب, طعام → طعم.
    """
    if len(stem_plain) != 4 or stem_plain[2] != "ا":
        return None
    cand = stem_plain[0] + stem_plain[1] + stem_plain[3]
    if is_sound_trilateral_candidate(cand):
        return cand
    return None


R_VN01 = WaznRule(
    rule_id="R-EXTRACT-VN01",
    name="Verbal noun فِعَال (كِتَاب → كتب)",
    form="verbal_noun",
    wazn="فعال",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_fi3al_VN,
    examples_pass=[("كتاب", "كتب"), ("شراب", "شرب"), ("طعام", "طعم")],
    confidence=0.85,
)


# فُعُول pattern: 5 letters L1 + L2 + و + ل + (no, actually 5)
# دخول = د خ و ل → root د خ ل
def _extract_fu3ul_VN(stem_plain: str) -> Optional[str]:
    """فُعُول pattern: 4 letters with و at position 2.
    Examples: دخول → دخل, خروج → خرج, ركوع → ركع."""
    if len(stem_plain) != 4 or stem_plain[2] != "و":
        return None
    cand = stem_plain[0] + stem_plain[1] + stem_plain[3]
    if is_sound_trilateral_candidate(cand):
        return cand
    return None


R_VN02 = WaznRule(
    rule_id="R-EXTRACT-VN02",
    name="Verbal noun فُعُول (دخول → دخل)",
    form="verbal_noun",
    wazn="فعول",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_fu3ul_VN,
    examples_pass=[("دخول", "دخل"), ("خروج", "خرج"), ("ركوع", "ركع")],
    confidence=0.85,
)


# Form IV verbal noun: إِفْعَال (إخراج, إكرام). 5 letters: إ + L1 + L2 + ا + L3
def _extract_form_IV_VN(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5:
        return None
    if stem_plain[0] not in ("ا", "إ", "أ"):
        return None
    if stem_plain[3] != "ا":
        return None
    cand = stem_plain[1] + stem_plain[2] + stem_plain[4]
    # Allow hamza in root
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_VN03 = WaznRule(
    rule_id="R-EXTRACT-VN03",
    name="Form IV verbal noun (إفعال) — إخراج → خرج",
    form="IV_VN",
    wazn="إفعال",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_IV_VN,
    examples_pass=[("إخراج", "خرج"), ("إكرام", "كرم"), ("إنزال", "نزل")],
    confidence=0.85,
)


# Form V verbal noun: تَفَعُّل. 5 letters: ت + L1 + L2 + و + L3? Actually
# تَعَلُّم has shadda which is stripped → تعلم (4 letters). Need separate rule
# already handled by R-EXTRACT-S04. Skip.


# Form X verbal noun: اسْتِفْعَال (استغفار). 7 letters: ا س ت + L1 + L2 + ا + L3.
def _extract_form_X_VN(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 7:
        return None
    if stem_plain[:3] != "است":
        return None
    if stem_plain[5] != "ا":
        return None
    cand = stem_plain[3] + stem_plain[4] + stem_plain[6]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_VN04 = WaznRule(
    rule_id="R-EXTRACT-VN04",
    name="Form X verbal noun (استفعال) — استغفار → غفر",
    form="X_VN",
    wazn="استفعال",
    stem_length_after_diac_strip=7,
    extract_fn=_extract_form_X_VN,
    examples_pass=[("استغفار", "غفر"), ("استخراج", "خرج")],
    confidence=0.85,
)


# Form VIII verbal noun: افْتِعَال (اشتراك → شرك)
def _extract_form_VIII_VN(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 6:
        return None
    if stem_plain[0] != "ا" or stem_plain[2] != "ت":
        return None
    if stem_plain[4] != "ا":
        return None
    cand = stem_plain[1] + stem_plain[3] + stem_plain[5]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_VN05 = WaznRule(
    rule_id="R-EXTRACT-VN05",
    name="Form VIII verbal noun (افتعال) — اشتراك → شرك",
    form="VIII_VN",
    wazn="افتعال",
    stem_length_after_diac_strip=6,
    extract_fn=_extract_form_VIII_VN,
    examples_pass=[("اشتراك", "شرك"), ("اقتراب", "قرب")],
    confidence=0.85,
)


VERBAL_NOUN_RULES = [R_VN04, R_VN05, R_VN03, R_VN01, R_VN02]


# ============================================================================
# Phase 2.9: Broken plurals (جموع التكسير)
# ============================================================================

# أَفْعَال pattern (أجناس → جنس, أموال → مول, أعمال → عمل)
def _extract_afaal_BP(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5:
        return None
    if stem_plain[0] not in ("أ", "ا", "إ"):
        return None
    if stem_plain[3] != "ا":
        return None
    cand = stem_plain[1] + stem_plain[2] + stem_plain[4]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_BP01 = WaznRule(
    rule_id="R-EXTRACT-BP01",
    name="Broken plural أَفْعَال (أعمال → عمل)",
    form="broken_plural",
    wazn="أفعال",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_afaal_BP,
    examples_pass=[("أعمال", "عمل"), ("أحمال", "حمل"), ("أصحاب", "صحب")],
    confidence=0.8,
)


# فُعَلاء pattern (شُعَراء → شعر)
def _extract_fu3ala_BP(stem_plain: str) -> Optional[str]:
    """فُعَلاء: 5 letters with ا at position 3 + ء at position 4."""
    if len(stem_plain) != 5:
        return None
    if stem_plain[3] != "ا":
        return None
    if stem_plain[4] not in ("ء", "أ"):
        return None
    cand = stem_plain[0] + stem_plain[1] + stem_plain[2]
    if is_sound_trilateral_candidate(cand):
        return cand
    return None


R_BP02 = WaznRule(
    rule_id="R-EXTRACT-BP02",
    name="Broken plural فُعَلاء (شعراء → شعر)",
    form="broken_plural",
    wazn="فعلاء",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_fu3ala_BP,
    examples_pass=[("شعراء", "شعر")],
    confidence=0.8,
)


# فَوَاعِل / فَوَاعِيل patterns (نوافذ → نفذ, دواوين → دون)
# Sound trilateral broken plural fawa3il
def _extract_fawa3il_BP(stem_plain: str) -> Optional[str]:
    """فَوَاعِل: 5 letters L1 + و + ا + L2 + L3."""
    if len(stem_plain) != 5:
        return None
    if stem_plain[1] != "و" or stem_plain[2] != "ا":
        return None
    cand = stem_plain[0] + stem_plain[3] + stem_plain[4]
    if is_sound_trilateral_candidate(cand):
        return cand
    return None


R_BP03 = WaznRule(
    rule_id="R-EXTRACT-BP03",
    name="Broken plural فَوَاعِل (نوافذ → نفذ)",
    form="broken_plural",
    wazn="فواعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_fawa3il_BP,
    examples_pass=[("نوافذ", "نفذ")],
    confidence=0.75,
)


# مَفَاعِل: 5 letters م + L1 + ا + L2 + L3. Examples: مصابيح → صبح, مفاتيح → فتح
def _extract_mafa3il_BP(stem_plain: str) -> Optional[str]:
    """مَفَاعِل/مَفَاعِيل."""
    if len(stem_plain) not in (5, 6):
        return None
    if stem_plain[0] != "م":
        return None
    if stem_plain[2] != "ا":
        return None
    if len(stem_plain) == 5:
        cand = stem_plain[1] + stem_plain[3] + stem_plain[4]
    else:  # 6 letters (with ي)
        if stem_plain[4] != "ي":
            return None
        cand = stem_plain[1] + stem_plain[3] + stem_plain[5]
    if is_no_weak_letter(cand):
        return cand
    return None


R_BP04 = WaznRule(
    rule_id="R-EXTRACT-BP04",
    name="Broken plural مَفَاعِل/مَفَاعِيل",
    form="broken_plural",
    wazn="مفاعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_mafa3il_BP,
    examples_pass=[("منازل", "نزل"), ("مدارس", "درس")],
    confidence=0.8,
)


# فُعُول broken plural (already handled by VN02 — same pattern)


BROKEN_PLURAL_RULES = [R_BP04, R_BP01, R_BP02, R_BP03]


# ============================================================================
# Phase 2.10: Active participles of derived forms
# ============================================================================

# Form II active participle: مُفَعِّل (after shadda strip: مفعل, 4 letters with م prefix)
# But this is same as R_S09 (noun pattern مَفْعَل). The disambiguation is via
# the م + 3 letters where 3-letter is the root.
# Already handled.

# Form IV active participle: مُفْعِل (مكرم, محسن). 4 letters: م + L1 + L2 + L3
# Same as R_S09.

# Form VIII active participle: مُفْتَعِل (مجتهد, متخذ). 5 letters: م + L1 + ت + L2 + L3
def _extract_form_VIII_AP(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5 or stem_plain[0] != "م":
        return None
    if stem_plain[2] != "ت":
        return None
    cand = stem_plain[1] + stem_plain[3] + stem_plain[4]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_AP01 = WaznRule(
    rule_id="R-EXTRACT-AP01",
    name="Form VIII active participle (مُفْتَعِل)",
    form="VIII_AP",
    wazn="مفتعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_VIII_AP,
    examples_pass=[("مجتهد", "جهد"), ("مقتدر", "قدر")],
    confidence=0.85,
)


# Form X active participle: مُسْتَفْعِل (مستغفر, مستخرج)
def _extract_form_X_AP(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 6:
        return None
    if stem_plain[:4] != "مست":
        # Check for "مست" with the م
        if stem_plain[0] == "م" and stem_plain[1] == "س" and stem_plain[2] == "ت":
            pass
        else:
            return None
    cand = stem_plain[3] + stem_plain[4] + stem_plain[5]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_AP02 = WaznRule(
    rule_id="R-EXTRACT-AP02",
    name="Form X active participle (مُسْتَفْعِل)",
    form="X_AP",
    wazn="مستفعل",
    stem_length_after_diac_strip=6,
    extract_fn=_extract_form_X_AP,
    examples_pass=[("مستغفر", "غفر"), ("مستخرج", "خرج")],
    confidence=0.85,
)


# Form V active participle: مُتَفَعِّل (متعلم). After shadda strip: 5 letters م+ت+L1+L2+L3.
def _extract_form_V_AP(stem_plain: str) -> Optional[str]:
    if len(stem_plain) != 5 or stem_plain[0] != "م" or stem_plain[1] != "ت":
        return None
    cand = stem_plain[2:]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_AP03 = WaznRule(
    rule_id="R-EXTRACT-AP03",
    name="Form V active participle (مُتَفَعِّل)",
    form="V_AP",
    wazn="متفعل",
    stem_length_after_diac_strip=5,
    extract_fn=_extract_form_V_AP,
    examples_pass=[("متعلم", "علم"), ("متقدم", "قدم")],
    confidence=0.85,
)


AP_RULES = [R_AP02, R_AP01, R_AP03]


# ============================================================================
# Phase 2.11: Imperative with hamzat wasl + intensive patterns
# ============================================================================

# Form I imperative with leading ا (hamzat wasl): اضرب, ارحم
def _extract_form_I_imperative(stem_plain: str) -> Optional[str]:
    """4 letters: ا + L1 + L2 + L3, sound trilateral root."""
    if len(stem_plain) != 4 or stem_plain[0] != "ا":
        return None
    cand = stem_plain[1:]
    if is_sound_trilateral_candidate(cand):
        return cand
    return None


R_IMP01 = WaznRule(
    rule_id="R-EXTRACT-IMP01",
    name="Form I imperative with hamzat wasl (ارحم → رحم)",
    form="I_imperative",
    wazn="افعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_form_I_imperative,
    examples_pass=[("ارحم", "رحم"), ("اذكر", "ذكر"), ("افعل", "فعل")],
    confidence=0.85,
)


# فَعَّال intensive (تَوَّاب, ضَرَّاب, خَلَّاق): 4 letters L1 + L2 + ا + L3 (shadda stripped)
# Actually تواب after strip = تواب (4 letters: ت و ا ب). The shadda was on the و.
# So root is ت و ب (toob? No, this is تَوْب). Wait, تَوَّاب pattern is:
# tawwāb = t-w-w-ā-b, root is t-w-b (توب).
# After diacritic strip: تواب (4 letters). To get root: drop position 2 (ا)?
# Actually we need to drop the duplicate after shadda — but shadda is stripped.
# تواب → ت + و + ا + ب: looks like فعال pattern. Root would be ت و ب (توب).
# Same extraction as فعال VN: drop position 2 (ا) → ت و ب.

# That's already handled by R_VN01! Let me check:
# R_VN01 extracts: stem[0]+stem[1]+stem[3]. For "تواب" → ت + و + ب = توب.
# But is_sound_trilateral_candidate rejects this because of و in middle!

# Need a hollow-allowing variant.
def _extract_fa33al_intensive(stem_plain: str) -> Optional[str]:
    """فَعَّال intensive: 4 letters where position 2 is ا.
    Root is L1 + L2 + L3 (after dropping ا). Hollow-tolerant.
    """
    if len(stem_plain) != 4 or stem_plain[2] != "ا":
        return None
    cand = stem_plain[0] + stem_plain[1] + stem_plain[3]
    if is_no_weak_letter(cand):
        return "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    return None


R_INT01 = WaznRule(
    rule_id="R-EXTRACT-INT01",
    name="فَعَّال intensive (هلty hollow-tolerant)",
    form="intensive",
    wazn="فعال",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_fa33al_intensive,
    examples_pass=[("تواب", "توب"), ("غفار", "غفر"), ("رحام", "رحم")],
    confidence=0.75,
)


# مفعل of hamza-initial: مأكل → root ءكل
def _extract_maf3al_hamza(stem_plain: str) -> Optional[str]:
    """مَفْعَل with hamza in root."""
    if len(stem_plain) != 4 or stem_plain[0] != "م":
        return None
    cand = stem_plain[1:]
    cand_norm = "".join(("ء" if c in HAMZA_VARIANTS else c) for c in cand)
    if has_hamza(cand_norm) and is_no_weak_letter(cand_norm):
        return cand_norm
    return None


R_INT02 = WaznRule(
    rule_id="R-EXTRACT-INT02",
    name="مَفْعَل with hamza in root (مأكل → ءكل)",
    form="noun",
    wazn="مفعل",
    stem_length_after_diac_strip=4,
    extract_fn=_extract_maf3al_hamza,
    examples_pass=[("مأكل", "ءكل"), ("مأمن", "ءمن")],
    confidence=0.8,
)


# Hollow noun: 3 letters with و/ي in middle, often نون pattern (يوم, نور, etc.)
def _extract_hollow_noun(stem_plain: str) -> Optional[str]:
    """3-letter noun with و or ي in middle (already root form)."""
    if len(stem_plain) != 3:
        return None
    if stem_plain[1] not in ("و", "ي"):
        return None
    if stem_plain[0] in WEAK_LETTERS or stem_plain[2] in WEAK_LETTERS:
        return None
    return stem_plain


# Already covered by R_OL07. Skip duplicate.


# Defective noun: 3 letters with و/ي at end (already root form)
# Covered by R_DEF02.


# Form II of doubled root: فَعَّل → after shadda strip looks like 3 letters
# but doubled like ردد. e.g., يَردُّ → ر د د. Surface stem "رد" (2 letters).
# Already covered by R_DBL01.


# Form IV passive participle: مُكْرَم. 4 letters م + L1 + L2 + L3 (no و).
# Already covered by R_S09.


SPECIAL_RULES = [R_INT01, R_INT02, R_IMP01]


# Final ALL_RULES
ALL_RULES = (SOUND_TRILATERAL_RULES + HAMZA_TRILATERAL_RULES +
             HOLLOW_RULES + DEFECTIVE_RULES + ASSIMILATED_RULES +
             DOUBLED_RULES + QUAD_RULES + VERBAL_NOUN_RULES +
             BROKEN_PLURAL_RULES + AP_RULES + SPECIAL_RULES)


# ============================================================================
# Compile all rules
# ============================================================================

ALL_RULES = (SOUND_TRILATERAL_RULES + HAMZA_TRILATERAL_RULES +
             HOLLOW_RULES + DEFECTIVE_RULES + ASSIMILATED_RULES +
             DOUBLED_RULES + QUAD_RULES + VERBAL_NOUN_RULES +
             BROKEN_PLURAL_RULES + AP_RULES)


# ============================================================================
# Main extraction pipeline
# ============================================================================

def extract(word: str) -> RootExtractionResult:
    """Extract candidate roots for `word` using pure rules.

    Algorithm:
      1. Strip diacritics for analysis (preserve original for output)
      2. Peel one prefix (try noun-prefixes first, then verb)
      3. Peel one suffix (try noun-suffixes first, then verb)
      4. Try each WaznRule against the stem
      5. Collect successful candidates, rank by confidence

    Returns:
      RootExtractionResult with ranked candidates, or out_of_scope reason.
    """
    if not word or not word.strip():
        return RootExtractionResult(
            word=word, word_normalized="",
            candidates=[],
            out_of_scope_reason="empty_input",
        )

    word_plain = strip_diacritics(word)
    # Expand alif-madda آ to ءا (logical hamza+alif) — enables H04 detection
    word_plain_expanded = word_plain.replace("آ", "ءا")
    transformations = [f"diac_strip:{word!r}→{word_plain!r}"]
    if word_plain_expanded != word_plain:
        transformations.append(f"alif_madda_expand:{word_plain!r}→{word_plain_expanded!r}")
        word_plain = word_plain_expanded

    # Try multiple prefix/suffix combinations
    # Strategy: peel 0 or 1 prefix × peel 0 or 1 suffix, generate variants
    candidates_collected: list[Candidate] = []
    seen_stems = set()

    prefix_options = [("", [])] + [
        (pref, [f"prefix_{tag}={pref}"])
        for pref, tag in NOUN_PREFIXES + VERB_PREFIXES
        if word_plain.startswith(pref)
    ]
    suffix_options = [("", [])] + [
        (suf, [f"suffix_{tag}={suf}"])
        for suf, tag in NOUN_SUFFIXES + VERB_SUFFIXES
        if word_plain.endswith(suf)
    ]

    for (pref, pref_trans) in prefix_options:
        rest_after_pref = word_plain[len(pref):] if pref else word_plain
        for (suf, suf_trans) in suffix_options:
            stem = rest_after_pref[:-len(suf)] if suf else rest_after_pref
            if not stem or stem in seen_stems:
                continue
            seen_stems.add(stem)
            stem_trans = transformations + pref_trans + suf_trans + [
                f"stem={stem!r}"
            ]
            # Try all rules
            for rule in ALL_RULES:
                if len(stem) != rule.stem_length_after_diac_strip:
                    continue
                root = rule.extract_fn(stem)
                if root:
                    candidates_collected.append(Candidate(
                        root=root,
                        wazn=rule.wazn,
                        form=rule.form,
                        confidence=rule.confidence,
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        transformations=stem_trans + [
                            f"matched_rule={rule.rule_id}",
                            f"root_extracted={root!r}",
                        ],
                    ))

    # Deduplicate (root, wazn) pairs — keep highest confidence
    deduped: dict[tuple[str, str], Candidate] = {}
    for c in candidates_collected:
        key = (c.root, c.wazn)
        if key not in deduped or c.confidence > deduped[key].confidence:
            deduped[key] = c
    candidates = sorted(deduped.values(), key=lambda c: -c.confidence)

    if not candidates:
        # No rule fired — out of scope for current phases
        if not is_no_weak_letter(word_plain):
            return RootExtractionResult(
                word=word, word_normalized=word_plain,
                candidates=[],
                out_of_scope_reason="contains_weak_letter_و_ي_ا_ى",
            )
        return RootExtractionResult(
            word=word, word_normalized=word_plain,
            candidates=[],
            out_of_scope_reason="no_rule_matched",
        )

    return RootExtractionResult(
        word=word,
        word_normalized=word_plain,
        candidates=candidates,
    )


# ============================================================================
# Self-test
# ============================================================================

def _self_test():
    """Run all rules' examples_pass through extract() and verify."""
    print("=== root_extractor self-test ===\n")
    n_pass = n_fail = 0
    for rule in ALL_RULES:
        for stem, expected_root in rule.examples_pass:
            result = extract(stem)
            roots = [c.root for c in result.candidates]
            ok = expected_root in roots
            mark = "✓" if ok else "✗"
            if ok:
                n_pass += 1
            else:
                n_fail += 1
            print(f"  {mark} [{rule.rule_id}] extract({stem!r}) → roots={roots}, expected={expected_root!r}")
    print(f"\n{n_pass} passed, {n_fail} failed")
    return n_fail == 0


if __name__ == "__main__":
    _self_test()
