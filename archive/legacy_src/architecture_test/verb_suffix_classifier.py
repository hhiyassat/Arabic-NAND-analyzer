"""Classify verb suffixes detected by the segmenter into person/number/gender info.

The salehan segmenter identifies verb suffixes via `_VERB_SUFFIX_PATTERNS`:
    تُمُو, تُنَّ, تُمْ, نَا, وا, تُ, تَ, تِ, نَ, تْ

Each suffix encodes:
  - the speaker/listener/third-person relation
  - number (singular/dual/plural)
  - gender where marked
  - optional ambiguity (e.g., نَا can be 1pl OR pronoun ها)

This module surfaces that information so verb tokens carry concrete
person/number/gender data even when wazn matching fails (common with
imperfect diacritizations from GPT52 or vocabulary outside the
80-wazn table).

Computational-level helper. Per 11_Abstraction_Levels.md: serves the
LINGUISTIC level (تصريف العربية الكلاسيكي), no philosophical claim.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Optional

_DIACRITICS = set("ًٌٍَُِّْٰٓٔ")


def _strip_d(s: str) -> str:
    return ''.join(c for c in str(s or "") if c not in _DIACRITICS and c != 'ـ')


@dataclass(frozen=True)
class VerbSuffixInfo:
    suffix: str  # the original (vocalized) suffix
    label_ar: str  # تاء الفاعل، تاء التأنيث، نون النسوة، واو الجماعة، إلخ
    person: str  # 1sg / 2sg_m / 2sg_f / 2du / 2pl_m / 2pl_f / 3sg_m / 3sg_f / 3pl_m / 3pl_f
    number: str  # مفرد / مثنى / جمع
    gender: Optional[str]  # م / ث / —
    pronoun_ar: str  # أنا / أنتَ / أنتِ / أنتما / أنتم / أنتن / هو / هي / هم / هن
    ambiguity: Optional[str] = None  # explanation if same surface form maps to multiple readings


# Suffix → info. Plain forms are keys (after diacritic stripping).
# Longest-first ordering matters when matching; index by plain length.
_SUFFIX_TABLE: dict[str, VerbSuffixInfo] = {
    "تمو": VerbSuffixInfo("تُمُو", "تاء الفاعل + واو إشباع", "2pl_m", "جمع", "م", "أنتم"),
    "تن": VerbSuffixInfo("تُنَّ", "تاء الفاعل + نون النسوة", "2pl_f", "جمع", "ث", "أنتن"),
    "تم": VerbSuffixInfo("تُمْ", "تاء الفاعل (جمع مذكر)", "2pl_m", "جمع", "م", "أنتم"),
    "نا": VerbSuffixInfo(
        "نَا", "نا الفاعلين", "1pl", "جمع", None, "نحن",
        ambiguity="قد تكون ضمير المتكلمين (1pl) أو ضمير الغائب المتصل (ها/هما)",
    ),
    "وا": VerbSuffixInfo("وا", "واو الجماعة", "3pl_m", "جمع", "م", "هم"),
    "ت": VerbSuffixInfo(
        "تْ / تُ / تَ / تِ", "تاء (فاعل أو تأنيث)", "ambiguous_t", "مفرد", None, "متعدد",
        ambiguity="تَ=أنتَ، تِ=أنتِ، تُ=أنا، تْ=هي (تأنيث ساكنة) — الحركة تميز الضمير",
    ),
    "ن": VerbSuffixInfo("نَ", "نون النسوة", "3pl_f", "جمع", "ث", "هن"),
}


# Vocalized "ت" variants → precise person
_T_BY_HARAKAH: dict[str, VerbSuffixInfo] = {
    "تُ": VerbSuffixInfo("تُ", "تاء الفاعل (متكلم)", "1sg", "مفرد", None, "أنا"),
    "تَ": VerbSuffixInfo("تَ", "تاء الفاعل (مخاطب مذكر)", "2sg_m", "مفرد", "م", "أنتَ"),
    "تِ": VerbSuffixInfo("تِ", "تاء الفاعل (مخاطب مؤنث)", "2sg_f", "مفرد", "ث", "أنتِ"),
    "تْ": VerbSuffixInfo("تْ", "تاء التأنيث الساكنة", "3sg_f", "مفرد", "ث", "هي"),
    "ت": VerbSuffixInfo(
        "ت", "تاء (غير محدَّدة الحركة)", "ambiguous_t", "مفرد", None, "متعدد",
        ambiguity="غير محدد بدون حركة؛ احتمالات: أنا (تُ) / أنتَ (تَ) / أنتِ (تِ) / هي (تْ)",
    ),
}


def classify_suffix(suffix_raw: str) -> Optional[VerbSuffixInfo]:
    """Classify a verb suffix extracted by the segmenter.

    Returns None if the suffix is not a recognized verb suffix.
    """
    s = str(suffix_raw or "").strip()
    if not s:
        return None
    # Try exact vocalized lookup for ت variants first (most informative)
    if s in _T_BY_HARAKAH:
        return _T_BY_HARAKAH[s]
    # Fall back to plain (diacritic-stripped) lookup
    plain = _strip_d(s)
    if plain in _SUFFIX_TABLE:
        return _SUFFIX_TABLE[plain]
    return None


def classify_segmentation_suffixes(suffixes: list[str]) -> list[VerbSuffixInfo]:
    """Classify all suffixes from a segmentation result. Skips unknown ones."""
    out = []
    for s in suffixes or []:
        info = classify_suffix(s)
        if info is not None:
            out.append(info)
    return out


# Long vowels — when one of these precedes a final نَ, that نَ is
# نون الرفع (مضارع marker, e.g. تَشْكُرُونَ / تَكْتُبِينَ), NOT نون النسوة.
_LONG_VOWELS = set("اويىآ")  # alif, waw, yaa, alif-maqsura, alif-madda


def _stem_ends_in_long_vowel(stem: str) -> bool:
    if not stem:
        return False
    plain = _strip_d(stem)
    return bool(plain) and plain[-1] in _LONG_VOWELS


_NUN_AR_RAFA = VerbSuffixInfo(
    suffix="نَ",
    label_ar="نون الرفع (علامة رفع المضارع)",
    person="2pl_m_or_3pl_m_pres",  # surface alone doesn't pick 2nd vs 3rd
    number="جمع",
    gender="م",
    pronoun_ar="أنتم/هم",
    ambiguity="نون الرفع لا تحدد المتكلم/المخاطب/الغائب وحدها؛ يحدّدها السياق.",
)

_NUN_AR_RAFA_F = VerbSuffixInfo(
    suffix="نَ",
    label_ar="نون الرفع (مع ياء المخاطبة)",
    person="2sg_f_pres",
    number="مفرد",
    gender="ث",
    pronoun_ar="أنتِ",
)

_WAW_JAMA_2PL_M = VerbSuffixInfo(
    suffix="وا",
    label_ar="واو الجماعة (مضارع مع تاء الخطاب)",
    person="2pl_m",
    number="جمع",
    gender="م",
    pronoun_ar="أنتم",
)


# Imperfect-prefix evidence — مضارع verbs in Arabic begin with one of أ/ن/ي/ت.
# When a verb has واو الجماعة attached, the prefix tells 2nd vs 3rd person:
#   ت + ... + وا  → 2pl_m (لِتُكْمِلُوا = "so that you-pl complete")
#   ي + ... + وا  → 3pl_m (يَكْتُبُوا)
#   ا + ... + وا  → imperative 2pl_m (اكْتُبُوا)
# Otherwise (ماضي past tense): واو الجماعة → 3pl_m (ذَهَبُوا = "they-pl went")
_IMPERFECT_PREFIX_CHARS = set("يتنأ")


def _surface_first_letter(s: str) -> str:
    """First non-diacritic letter of a surface form (handles لِـ، فَـ، وَـ، الـ prefixes
    by walking past them — caller may pass the segmenter's stripped form too)."""
    plain = _strip_d(s or "")
    return plain[:1]


def classify_segmentation_suffixes_with_context(
    suffixes: list[str],
    stem: str | None = None,
    word_class: str | None = None,
) -> list[VerbSuffixInfo]:
    """Stem-aware classifier with word-class gating.

    Refinements over the bare classifier:
      1. **Gate by word_class** — only fire on verb-like tokens. Names (aalam),
         jamid nouns (e.g. رَمَضَانَ), particles, and operators must NOT receive
         person/number/gender from their surface tail; their final letters
         belong to the lexical pattern, not to a verb-suffix inflection.
      2. **نَ disambiguation by stem ending** — when the suffix is نَ:
            stem ends in و/ا  → نون الرفع on مضارع جمع (تَشْكُرُونَ)  → not نون النسوة
            stem ends in ي    → نون الرفع on مضارع 2sg-f (تَكْتُبِينَ) → not نون النسوة
            stem ends in consonant+sukoon → نون النسوة (ذَهَبْنَ)
    """
    # Gate: hard-exclude word classes that definitely don't take verb suffixes,
    # but allow mushtaq/unknown through when the surface suffix is *itself*
    # unambiguously verbal (e.g. تُ، تَ، تِ، تُمْ، تُنَّ، نَا، تُمُو، وا).
    # This is needed because alasmaa often misclassifies past-tense verbs as
    # mushtaq (the past 3sg-m فَعَلَ surface-collides with the active-participle
    # pattern فَعِل/الصفة المشبهة). The segmenter's detection of a strong
    # verb suffix is reliable evidence to override that misclassification.
    HARD_EXCLUDE = {"aalam", "jamid", "harf", "operator"}
    if word_class in HARD_EXCLUDE:
        return []
    # Risky suffixes (نَ, تْ) can attach to nouns too (نون النسوة on فعل ماضٍ
    # vs feminine-plural marker on nouns like مسلمات; تْ vs تاء التأنيث on a
    # noun). For these, require an explicit verb classification.
    RISKY_SUFFIXES = {"ن", "ت"}  # plain (diacritic-stripped) forms
    STRONG_VERB_SUFFIXES = {"تُ", "تَ", "تِ", "تُمْ", "تُنَّ", "نَا", "تُمُو", "وا"}
    if word_class != "verb":
        # mushtaq / mushtaq_pattern_only / unknown / None — admit only if at
        # least one suffix is unambiguously verbal.
        plain_set = {_strip_d(s) for s in suffixes or []}
        has_risky_only = bool(plain_set) and plain_set.issubset(RISKY_SUFFIXES)
        has_strong = any(s in STRONG_VERB_SUFFIXES for s in (suffixes or []))
        if has_risky_only and not has_strong:
            return []
        if not has_strong:
            return []

    stem_first = _surface_first_letter(stem) if stem else ""

    out: list[VerbSuffixInfo] = []
    for s in suffixes or []:
        info = classify_suffix(s)
        if info is None:
            continue
        # نَ refinement: distinguish نون الرفع from نون النسوة using stem tail.
        if info.label_ar == "نون النسوة" and stem:
            plain_tail = _strip_d(stem)
            if plain_tail:
                last = plain_tail[-1]
                if last in {"ا", "و"}:
                    info = _NUN_AR_RAFA  # تَشْكُرُونَ pattern
                elif last == "ي":
                    info = _NUN_AR_RAFA_F  # تَكْتُبِينَ pattern
                # else: keep نون النسوة (ذَهَبْنَ pattern)
        # وا refinement: in مضارع, واو الجماعة attached to a verb beginning with
        # تـ is 2pl_m, not 3pl_m. The stem (after prefix stripping by segmenter)
        # typically starts with the مضارع marker letter for tokens that retained it.
        elif info.label_ar == "واو الجماعة" and stem_first == "ت":
            info = _WAW_JAMA_2PL_M
        out.append(info)
    return out


# Map our compact person codes → the labels used by conjugation_loader.PAST_PERSONS.
# These labels are what `lookup_by_form` returns in its `person` field.
SUFFIX_TO_CONJ_PERSON: dict[str, list[str]] = {
    "1sg":      ["أنا_1sg"],
    "1pl":      ["نحن_1pl"],
    "2sg_m":    ["أنتَ_2sg_m"],
    "2sg_f":    ["أنتِ_2sg_f"],
    "2du":      ["أنتما_2du"],
    "2pl_m":    ["أنتم_2pl_m"],
    "2pl_f":    ["أنتن_2pl_f"],
    "3sg_m":    ["هو_3sg_m"],
    "3sg_f":    ["هي_3sg_f"],
    "3du_m":    ["هما_3du_m"],
    "3du_f":    ["هما_3du_f"],
    "3pl_m":    ["هم_3pl_m"],
    "3pl_f":    ["هن_3pl_f"],
    # Ambiguous ت without a clear harakah → any of the four ت-readings is plausible.
    "ambiguous_t": ["أنا_1sg", "أنتَ_2sg_m", "أنتِ_2sg_f", "هي_3sg_f"],
}


def conj_persons_from_suffix_infos(infos: list[VerbSuffixInfo]) -> list[str]:
    """Collect the candidate conjugation-loader person labels implied by these suffixes.

    Returns [] when no suffix info is available — caller should treat that as
    "no disambiguation evidence" rather than "no valid person".
    """
    allowed: list[str] = []
    for info in infos or []:
        for label in SUFFIX_TO_CONJ_PERSON.get(info.person, []):
            if label not in allowed:
                allowed.append(label)
    return allowed
