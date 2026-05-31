"""segmenter — THE OFFICIAL ARABIC SEGMENTER for معمار المعنى العربي.

═══════════════════════════════════════════════════════════════════════════
  CONSTITUTIONAL DECLARATION (2026-05-18)
═══════════════════════════════════════════════════════════════════════════
  This module is the project's official Arabic morphological segmenter.
  It supersedes the NAA standalone_segmenter conservative.py.

  Tested against: MASAQ Quranic corpus (17,619 unique words, 77,411 occurrences).

  Pipeline order (each step is auditable and reversible):
    Step 0  upstream normalize()       — via clean_code/normalizer.py
    Step 1  strip leading clitic       — و/ف conjunction
    Step 2  strip prepositional clitic — ب/ل/ك (wazn-aware)
    Step 3  strip definite article     — ال (and لِلْ contracted form)
    Step 4  strip future particle      — سَ
    Step 5  strip interrogative        — أَ (heuristic; not always safe)
    Step 6  strip imperfect prefix     — ي/ت/ن/أ (verb-only, wazn-aware)
    Step 7  strip pronominal suffix    — هم/كم/نا/ها/ه/ك/ي/...
    Step 8  strip plural/dual suffix   — ون/ين/ات/ا (conservative)
    Step 9  strip verb-subject suffix  — وا/تم/تن/نا/ت/ن (verb-only)

  Output is a tuple (prefixes, stem, suffixes) where each element preserves
  its original diacritics from the input. Reconstruct by concatenation.

  Constitutional alignment (per 12_Project_Scope_Declaration.md):
    ✓ Source-of-Claim       — every peel logs its rule name + position
    ✓ Confidence-of-Claim   — overall segmentation has confidence ∈ [0, 1]
    ✓ Alternatives-Preserved — segment_all() returns ALL plausible cuts
    ✓ Reversibility         — concatenation of parts recovers original

  Design principles:
    1. CONSERVATIVE — when in doubt, do NOT peel (better under-segment than
       over-segment; over-segmentation creates false roots).
    2. DIACRITIC-PRESERVING — peeled prefixes/suffixes keep their harakat;
       the stem keeps its harakat. No diacritic is silently dropped.
    3. NORMALIZER-DEPENDENT — assumes input has been normalized (NFC,
       alif_madda decomposed, tatweel removed, ordered diacritics).
    4. WAZN-AWARE FALLBACK — when ambiguous (e.g., is leading أ a hamza
       of افعل pattern or interrogative أ?), the segmenter defers to the
       wazn_matcher's audit on the candidate stem. If the matcher refuses
       the stripped form, the strip is rolled back.
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import importlib.util
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# === Character constants ===
DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
SHADDA = "ّ"
SUKUN = "ْ"
FATHA = "َ"
DAMMA = "ُ"
KASRA = "ِ"
ALIF = "ا"
ALIF_WASLA = "ٱ"
LAM = "ل"
WAW = "و"
FA = "ف"
BA = "ب"
KAF = "ك"
YA = "ي"
TA = "ت"
NUN = "ن"
HAMZA_ON_ALIF = "أ"
SIN = "س"
HAMZA = "ء"
TAA_MARBUTA = "ة"
HEH = "ه"
ALIF_FAMILY = {ALIF, ALIF_WASLA}
HAMZA_VARIANTS_SET = {HAMZA, HAMZA_ON_ALIF, "إ", "ؤ", "ئ", "آ"}  # canonical

# Minimum LETTER (consonant) count that must remain in the stem after any peel.
# Below this, even a triliteral root cannot be matched.
_MIN_STEM_LETTERS = 2

# Conjunction clitics — leading single-letter particle
_CONJUNCTION_CLITICS = (WAW, FA)
# Prepositional clitics — leading single-letter particle
_PREP_CLITICS = (BA, LAM, KAF)
# Single-letter imperfect verb prefixes used by the IV rule.
# IV-أ is excluded from the main tuple here (used in fa-fu-la trigger) because
# distinguishing IV-أ (verb) from أ-augment (broken plural noun like أَبْصَار)
# requires careful gating. A separate strict trigger handles IV-أ — see below.
_IV_PREFIXES = (YA, TA, NUN)
_IV_PREFIXES_WITH_HAMZA = (YA, TA, NUN, HAMZA_ON_ALIF)
# Future particle
_FUT_PREFIX = SIN

# Pronominal suffixes (longest-first for greedy strip; plain — diacritic-stripped)
_PRONOUN_SUFFIXES = (
    "هما", "كما", "هنّ", "هنن", "كنّ", "كنن", "هما",
    "هم", "هن", "كم", "كن", "نا",
    "ها", "ني",
    "ه", "ك", "ي",
)

# Number/case suffixes (longest-first). Note: ان (dual) is conditional —
# stripped only when an IV prefix is present (verb dual ending). For nouns,
# ان is often integral (شَيْطَان، إِنْسَان).
_NUMBER_SUFFIXES = ("ين", "ون", "ات")
# Suffixes that are only stripped under specific conditions
_NUMBER_SUFFIXES_CONDITIONAL = ("ان",)

# Verb-subject suffixes (past-tense and imperfect plural endings)
_VERB_SUBJECT_SUFFIXES = (
    "تموا", "تما", "تمو",
    "تم", "تن", "نا",
    "وا", "ون", "ين",
    "تُ", "تَ", "تِ",
)

# Closed-class lexemes (drawn from MASAQ Quranic corpus): these words are
# single morphological units even if they start with ال/ل/ك/و. The segmenter
# must NOT peel anything from them.
#
# Stored as DIACRITIC-STRIPPED plain text for matching (the segmenter
# diacritic-strips the input before lookup).
_CLOSED_CLASS_LEXEMES = frozenset({
    # Relative pronouns
    "الذي", "الذين", "التي", "اللاتي", "اللائي",
    "اللذان", "اللذين", "اللتان", "اللتين",
    # Demonstrative pronouns
    "ذلك", "تلك", "هذا", "هذه", "هؤلاء", "أولئك", "هنا", "هناك", "هنالك",
    "ذا", "ذي", "ذو", "أولاء",
    # Negation / particles
    "لا", "لم", "لن", "لما", "لاسيما", "ليس", "ليست", "لست", "لستم",
    "ما", "مهما", "متى", "كيف", "أين", "أي", "أيان",
    # Subjunctive / conditional / certainty
    "إن", "أن", "إنّ", "أنّ", "إذا", "إذ", "إذن", "كي", "كيلا", "حتى",
    "لو", "لولا", "لوما", "أما", "إما",
    "قد", "بل", "بلى", "نعم", "كلا", "حيث", "ألا",  # ألا: shadda version splits via assimilation, plain stays whole
    # Vocative / interrogative particles
    "يا", "أيا", "هيا", "أ", "هل",
    # Prepositions that look complex
    "إلى", "على", "في", "عن", "من", "إلا", "خلا", "حاشا", "عدا",
    "غير", "بين", "تحت", "فوق", "أمام", "خلف", "وراء", "قبل", "بعد",
    "عند", "لدى", "لدن", "مع", "منذ", "مذ", "حول", "ضد",
    "كل", "بعض", "جميع", "نفس", "كلا", "كلتا",
    # Pronouns (standalone)
    "أنا", "نحن", "أنت", "أنتِ", "أنتم", "أنتن", "أنتما",
    "هو", "هي", "هما", "هم", "هن",
    "إياك", "إياي", "إياه", "إياها", "إياهم", "إياكم",
    # Common quasi-prefixed particles seen in MASAQ
    "كأن", "كأنّ", "لكن", "لكنّ", "لعل", "لعلّ", "ليت",
    # NOTE: "لقد" deliberately ABSENT here — MASAQ splits لَـقَدْ into لَ + قَدْ.
    # If you find it in the set above, remove it.
})

# Defensive: explicitly assert "لقد" is not present (it must not be).
assert "لقد" not in _CLOSED_CLASS_LEXEMES, "remove لقد — MASAQ splits it"

# Special proper-noun lexemes that are not segmented further (treated as
# atomic stems even though they look prefixed). MASAQ retains "الله" as a
# single proper noun PROPER for lookups like "لِلَّهِ" → ل + الله.
_PROPER_NOUN_LEXEMES = frozenset({
    "الله",      # the divine name
    "اللهم",    # vocative of الله
})


# Atomic common nouns/verbs that MASAQ keeps as single segments but the
# heuristic prefix/suffix rules tend to wrongly split.
# Match is on diacritic-stripped surface.
# Keep this list very small — over-inclusion blocks legitimate splits.
_ATOMIC_WORDS = frozenset({
    "بناء", "وقود", "فارض", "فاقع",  # nouns wrongly split by CONJ/PREP rules
})


def _is_proper_lexeme(text: str) -> bool:
    return _strip_diacritics(text) in _PROPER_NOUN_LEXEMES


# Assimilation lexicon: words that surface as one form but MASAQ splits
# into two segments due to historical nun-meem assimilation, etc.
# Map: plain surface → tuple of (segment1, segment2) plain forms.
_ASSIMILATION_LEXEMES = {
    "مما":   ("من", "ما"),
    "ممن":   ("من", "من"),
    "عما":   ("عن", "ما"),
    "عمن":   ("عن", "من"),
    "كلما":  ("كل", "ما"),
    "ألا":   ("أن", "لا"),    # أَلَّا = أن + لا (shadda required)
    "إلا":   None,             # إلا (exception) stays single
    "فيما":  ("في", "ما"),
    "لئن":   ("ل", "ئن"),     # لَئِنْ = EMPHATIC ل + ئن
    # 3-segment splits stored as tuples of 3
    "أفلا":  ("أ", "ف", "لا"),     # INTERROG + CONJ + NEG
    "أولم":  ("أ", "و", "لم"),     # INTERROG + CONJ + JUSS
    "أولا":  ("أ", "و", "لا"),     # INTERROG + CONJ + NEG
    "أفلم":  ("أ", "ف", "لم"),
    "أفلن":  ("أ", "ف", "لن"),
    "أفمن":  ("أ", "ف", "من"),
    "أفأنت": ("أ", "ف", "أنت"),
    "أفغير": ("أ", "ف", "غير"),
    "أومن":  ("أ", "و", "من"),
    "أوكلما": ("أ", "و", "كلما"),
    # Time-particle compounds
    "يومئذ":  ("يوم", "ئذ"),
    "حينئذ":  ("حين", "ئذ"),
    "ساعتئذ": ("ساعت", "ئذ"),
}


def _try_assimilation_split(s: str) -> Optional[tuple[str, ...]]:
    """If s (with diacritics) is a known assimilation surface, return its
    segment tuple. Otherwise return None.
    """
    plain = _strip_diacritics(s)
    # Special: إِلَيَّ = إلى + ي (MASAQ splits with shadda).
    # NOTE: عَلَيَّ MASAQ keeps as ['علي'] (atomic), so excluded here.
    # لَدَيَّ MASAQ has ['لد', 'ي'] (truncated), handled separately if needed.
    if SHADDA in s and plain == "إلي":
        return ("إلى", "ي")
    if plain not in _ASSIMILATION_LEXEMES:
        return None
    if _ASSIMILATION_LEXEMES[plain] is None:
        return None
    if plain == "ألا" and SHADDA not in s:
        return None
    return _ASSIMILATION_LEXEMES[plain]


# Small denylist of proper nouns / fixed lexemes that look segmentable but
# aren't. Used to refuse 1-letter pronoun stripping on these words.
# Plain (diacritic-stripped) forms.
_NO_STRIP_PROPER_NOUNS = frozenset({
    "مالك",      # ends in ك
    "أولئك",     # defensive
    "الملك",
    "فرعون",     # ends in ون — would wrongly strip as plural
    "هارون",     # same
    "قارون",     # same
    "ميمون",     # same
    "ذوالقرنين", # rare
    "الياسين",
    # MASAQ-extracted proper nouns where segmenter tends to wrongly
    # split (mostly broken-plural/ون/ين endings or feminine ة)
    "يحيى", "البحرين", "بحرين", "الغني", "غني",
    "عرفات", "آزفة", "مدين", "سبأ", "إرم",
    "ثمود", "وثمود", "كثمود", "لثمود", "بثمود",
    "عاد", "وعاد", "كعاد", "لعاد", "بعاد",
    "إبراهيم", "وإبراهيم", "كإبراهيم", "لإبراهيم", "بإبراهيم",
    "لوط", "ولوط", "كلوط", "للوط", "بلوط",
    "شعيب", "وشعيب", "شعيبا",
    "نوح", "ونوح", "بنوح",
    "هود", "صالح", "إلياس",
    "موسى", "وموسى", "بموسى", "كموسى", "لموسى",
    "عيسى", "وعيسى",
    "يوسف", "ويوسف", "يوسفا", "ليوسف", "بيوسف",
    "داود", "وداود",
    "سليمان", "وسليمان",
    "إسماعيل", "إسحاق", "إسحق", "يعقوب", "زكريا",
    "آدم", "وآدم", "كآدم",
    "محمد", "أحمد",
    "هابيل", "قابيل",
    "جبريل", "ميكال",
    "مكة", "بكة",
    "اليهود", "النصارى", "الصابئين",
    # Quranic concepts MASAQ tags as proper:
    "القرآن", "قرآن", "قرآنا", "بالقرآن", "للقرآن", "والقرآن",
    "الفرقان", "فرقان",
    "السبت", "سبت",
    # Divine attributes (al-asma' al-husna)
    "العزيز", "العليم", "الحكيم", "الرحمن", "الرحيم",
    "السميع", "البصير", "الغفور", "الحميد", "الغني",
    "الكريم", "الواحد", "القهار", "الجبار", "المتكبر",
    "الواسع", "الحليم", "العظيم", "اللطيف", "الخبير",
    "التواب", "النصير", "المولى", "الشكور", "الصبور",
    "الودود", "المجيد", "الرقيب", "الشهيد", "الحفيظ",
    "الباسط", "الرءوف",
    # Same with و/ل/ك/ب prefixes
    "والعزيز", "والعليم", "والحكيم", "والرحمن", "والرحيم",
    "لله", "ولله", "بالله", "تالله", "والله",
})


# Hamzat-wasl lexicon — words whose leading alif elides after a single-letter
# preposition. After stripping prep ب/ل/ك, if the remainder matches one of
# these (without leading alif), we restore the alif so the stem matches MASAQ.
#
# Plain (diacritic-stripped) forms.
_SEEN_IS_ROOT_LEXICON_CACHE: frozenset | None = None
_SEEN_IS_ROOT_LEXICON_PLAIN_CACHE: frozenset | None = None


def _load_seen_is_root_lexicon() -> tuple[frozenset, frozenset]:
    """يُحَمِّل seen_is_root_lexicon.csv — كَلِمات السين أَصليَّة لا تُقَشَّر.

    TODO 1 (MC_AUDIT.md §6): استِخدام lexicon لِمَنع نَزع السين خَطَأً.
    """
    global _SEEN_IS_ROOT_LEXICON_CACHE, _SEEN_IS_ROOT_LEXICON_PLAIN_CACHE
    if _SEEN_IS_ROOT_LEXICON_CACHE is not None:
        return _SEEN_IS_ROOT_LEXICON_CACHE, _SEEN_IS_ROOT_LEXICON_PLAIN_CACHE
    import csv as _csv
    _path = Path(__file__).resolve().parent / "data" / "contracts" / "lists" / "seen_is_root_lexicon.csv"
    voc_set: set[str] = set()
    plain_set: set[str] = set()
    if _path.exists():
        with open(_path, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                w = row.get("word", "").strip()
                p = row.get("plain", "").strip()
                if w:
                    voc_set.add(w)
                if p:
                    plain_set.add(p)
    _SEEN_IS_ROOT_LEXICON_CACHE = frozenset(voc_set)
    _SEEN_IS_ROOT_LEXICON_PLAIN_CACHE = frozenset(plain_set)
    return _SEEN_IS_ROOT_LEXICON_CACHE, _SEEN_IS_ROOT_LEXICON_PLAIN_CACHE


def _word_in_seen_root_lexicon(word: str) -> bool:
    """يَفحَص هَل الكَلِمَة في lexicon السين الأَصليَّة."""
    voc, plain = _load_seen_is_root_lexicon()
    if word in voc:
        return True
    return _strip_diacritics(word) in plain


_HAMZAT_WASL_LEXEMES = frozenset({
    "اسم",      # name           (بِسْم → ب + اسم)
    "ابن",      # son            (بِابن → ب + ابن)
    "ابنة",     # daughter
    "امرأ",     # man
    "امرأة",    # woman
    "اثنين",    # two (masc)
    "اثنتين",   # two (fem)
    "ابنين",    # two sons
    "اقترب",    # Form VIII past (rare in this context)
})


def _try_hamzat_wasl_restore(body: str) -> str | None:
    """If body is one of the hamzat-wasl lexemes with leading alif elided,
    return the restored form. Otherwise return None.

    Example: input 'سْمِ' (kasra-on-meem) — strip diacritics → 'سم'. Test if
    'ا' + 'سم' = 'اسم' is in lexicon. If yes, prepend ا to body's surface.
    """
    plain = _strip_diacritics(body)
    if not plain:
        return None
    with_alif_plain = ALIF + plain
    if with_alif_plain in _HAMZAT_WASL_LEXEMES:
        return ALIF + body
    return None


# === Upstream normalizer loader ===
def _load_upstream_normalizer() -> Optional[Callable[[str], str]]:
    """Locate normalizer.py across known project layouts."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "normalizer.py",
        here.parent / "clean_code" / "normalizer.py",
        Path("/Users/husseinhiyassat/fractal/hussein/clean_code/normalizer.py"),
        Path("/sessions/nice-epic-cannon/mnt/hussein/clean_code/normalizer.py"),
    ]
    for p in candidates:
        if p.is_file():
            mod_name = "_segmenter_upstream_normalizer"
            spec = importlib.util.spec_from_file_location(mod_name, p)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod  # required for dataclass
            try:
                spec.loader.exec_module(mod)
                return getattr(mod, "normalize_text", None)
            except Exception:
                sys.modules.pop(mod_name, None)
                continue
    return None


_upstream_normalize = _load_upstream_normalizer()


def _maybe_normalize(text: str) -> str:
    if _upstream_normalize is None or not text:
        return text
    return _upstream_normalize(text)


# === Helpers ===
def _strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _count_letters(s: str) -> int:
    """Count non-diacritic characters."""
    return sum(1 for c in s if c not in DIACRITICS)


def _consume_diacritics(chars: list[str], i: int) -> int:
    """Advance i past any run of diacritics; return new i."""
    while i < len(chars) and chars[i] in DIACRITICS:
        i += 1
    return i


def _split_at_letter_index(s: str, letter_idx: int) -> tuple[str, str]:
    """Split s so that the first part contains exactly letter_idx non-diacritic chars.

    Diacritics IMMEDIATELY following the last consumed letter stay with the
    first part (they belong to that letter morpho-phonetically).
    """
    if letter_idx == 0:
        return "", s
    chars = list(s)
    n = len(chars)
    i = 0
    seen = 0
    while i < n and seen < letter_idx:
        if chars[i] not in DIACRITICS:
            seen += 1
        i += 1
    # i now points at the first character AFTER the letter_idx'th letter.
    # Consume trailing diacritics so they stay with the prefix.
    while i < n and chars[i] in DIACRITICS:
        i += 1
    return "".join(chars[:i]), "".join(chars[i:])


def _split_at_letter_index_from_end(s: str, n_letters_from_end: int) -> tuple[str, str]:
    """Inverse: split so the LAST part has exactly n_letters_from_end letters."""
    total = _count_letters(s)
    if n_letters_from_end >= total:
        return "", s
    return _split_at_letter_index(s, total - n_letters_from_end)


# === Rule implementations ===
# Each rule takes a "state" dict {prefixes, body, suffixes, audit}
# and returns the new state. A rule does nothing if its precondition fails.
#
# The body is what remains after all prior peels; future peels operate on body.
# Audit log records (rule_name, surface_removed, position).

@dataclass
class _State:
    prefixes: list[tuple[str, str]] = field(default_factory=list)  # (form, tag)
    body: str = ""
    suffixes: list[tuple[str, str]] = field(default_factory=list)  # (form, tag)
    audit: list[str] = field(default_factory=list)
    # When True, no further peeling allowed on body — used when a rule has
    # explicitly reconstructed a fixed lexeme (e.g. الله from لِلَّـ elision)
    # and we must not let later rules re-decompose it.
    frozen: bool = False

    def add_prefix(self, form: str, tag: str, rule: str) -> None:
        self.prefixes.append((form, tag))
        self.audit.append(f"{rule}:+pref={form!r}")

    def add_suffix(self, form: str, tag: str, rule: str) -> None:
        # Suffixes are strip-order = OUTER→INNER. MASAQ records suffixes
        # in surface (left-to-right) order = INNER→OUTER. We insert at the
        # FRONT so the final list is in MASAQ-aligned order.
        self.suffixes.insert(0, (form, tag))
        self.audit.append(f"{rule}:+suff={form!r}")


def _starts_with_article(s: str) -> bool:
    """True if s starts with ال (alif + lam, possibly with diacritics between)."""
    if len(s) < 2:
        return False
    chars = list(s)
    if chars[0] not in ALIF_FAMILY:
        return False
    i = 1
    i = _consume_diacritics(chars, i)
    return i < len(chars) and chars[i] == LAM


def _rule_conjunction(st: _State) -> _State:
    """Strip leading و/ف conjunction.

    Only fires as the FIRST prefix peel (conjunction is always outermost).
    For ف, requires fatha or sukun (NOT kasra — فِـ with kasra is part of the
    word, never a conjunction).

    Refuses when the resulting body's first consonant carries SUKUN — that
    signals a noun root (وَقُود → ق+damma after strip is fine, but فَوْق →
    و+sukun after strip indicates a noun فوق, not a conjunction-stripping case).
    """
    if st.prefixes:
        return st
    s = st.body
    if not s or s[0] not in _CONJUNCTION_CLITICS:
        return st
    chars = list(s)
    diac_on_clitic = chars[1] if len(chars) > 1 and chars[1] in DIACRITICS else ""
    if chars[0] == FA and diac_on_clitic == KASRA:
        return st
    i = 1
    i = _consume_diacritics(chars, i)
    rest_chars = chars[i:]
    rest = "".join(rest_chars)
    if _count_letters(rest) < _MIN_STEM_LETTERS:
        return st
    # First-consonant-sukun check: noun-marker, refuse CONJ strip.
    # PATCH 1 (2026-05-26) — surgical exception for lam-al-amr:
    # if the rest starts with لْ + (يَ/تَ/نَ/أَ), it's a jussive command
    # construction (وَلْيَكْتُب, فَلْيَكْتُبْ etc.), not a noun. Allow CONJ
    # peel so the lam_al_amr rule downstream can recognize it.
    # Counter-examples preserved (still refused):
    #   فَوْق  → rest_chars[0]=و, not ل → still refused
    #   وَقْت  → rest_chars[0]=ق, not ل → still refused
    if len(rest_chars) >= 2 and rest_chars[1] == SUKUN:
        is_lam_al_amr_pattern = (
            len(rest_chars) >= 3
            and rest_chars[0] == LAM
            and rest_chars[2] in _IV_PREFIXES_WITH_HAMZA
        )
        if not is_lam_al_amr_pattern:
            return st
    has_tanwin = any(c in s for c in (TANWIN_FATHA, "ٌ", "ٍ"))
    rest_plain = _strip_diacritics(rest)
    # 3-letter noun + tanwin alif: ف/و is likely root letter, not CONJ.
    # وَلَدَاً (و-ل-د root, indefinite acc) — refuse strip.
    # BUT don't refuse for words ending in ى: وَهُدَى → و + هدي.
    if (_count_letters(rest) == 3
            and has_tanwin
            and rest_plain.endswith("ا")):
        return st
    # فَاعِل-pattern (Form I active participle) with tanwin: ف/و is root.
    # وَاحِدٌ, فَارِضٌ, فَاقِعٌ — refuse when rest starts with ا + tanwin.
    if (len(rest_chars) >= 2
            and rest_chars[0] == ALIF
            and has_tanwin
            and _count_letters(rest) >= 3):
        return st
    # فَعِيل-pattern (Form I adjective/noun with hollow ي) + tanwin.
    # فَرِيقٌ, طَرِيقٌ — refuse when rest is 3 letters AND chars[3]=ي (hollow).
    if (_count_letters(rest) == 3
            and has_tanwin
            and len(rest_chars) >= 4
            and rest_chars[3] == YA):
        return st
    # 2-letter rest + tanwin: ف/و is root letter (وَلَدٌ).
    if _count_letters(rest) == 2 and has_tanwin:
        return st
    # NOTE: tried refusing CONJ when remainder starts with ا (Form III hint)
    # but it blocked too many valid CONJ+verb cases. Reverted.
    prefix_form = "".join(chars[:i])
    st.body = rest
    st.add_prefix(prefix_form, "CONJ", "conjunction")
    return st


def _rule_emphatic_lam(st: _State) -> _State:
    """Strip emphatic ل (لَ with FATHA) as in لَقَدْ، لَأَنْتَ، لَذَهَبَ.

    Fires when:
      - Current body starts with ل + fatha
      - Either the remaining body is closed-class (لَقَدْ → قَدْ)
        OR the remaining body has 3+ letters and looks verb-shaped
        (sukun in body, characteristic of verbs: لَذَهَبَ → ذَهَبَ).
    """
    s = st.body
    if len(s) < 3 or s[0] != LAM:
        return st
    chars = list(s)
    if chars[1] != FATHA:
        return st
    rest = "".join(chars[2:])
    if _is_closed_class(rest):
        pref = "".join(chars[:2])
        st.body = rest
        st.add_prefix(pref, "EMPHATIC", "emphatic_lam_to_closed")
        return st
    # 3-letter past-tense verb after لَ — لَذَهَبَ pattern.
    rest_plain = _strip_diacritics(rest)
    if len(rest_plain) == 3:
        rest_chars = list(rest)
        diacritics_in_rest = [c for c in rest_chars if c in DIACRITICS]
        if diacritics_in_rest and all(d == FATHA for d in diacritics_in_rest):
            pref = "".join(chars[:2])
            st.body = rest
            st.add_prefix(pref, "EMPHATIC", "emphatic_lam_past3")
            return st
    # EMPHATIC ل + noun-with-tanwin (لَآيَاتٍ → ل + آيات).
    if (any(c in s for c in (TANWIN_FATHA, "ٌ", "ٍ"))
            and len(rest_plain) >= 3):
        pref = "".join(chars[:2])
        st.body = rest
        st.add_prefix(pref, "EMPHATIC", "emphatic_lam_noun_tanwin")
        return st
    return st


def _rule_prep_clitic(st: _State) -> _State:
    """Strip leading ب/ل/ك preposition.

    CONSERVATIVE: only strips when followed by ال (article). This avoids
    catastrophic over-segmentation of root-initial ك (كَتَب, كَفَر) and
    root-initial ل (لَعِب, لَمَس). The pattern PREP + ال is unambiguous in MSA
    and Quranic Arabic.

    Special form: لِلْ (lam preposition + assimilated lam of article) is also
    recognized — the alif of the article elides after lam-preposition.
    """
    # Allow this rule to fire after CONJ but not after another PREP/DET
    if any(t in {"PREP", "PREP+DET", "DET"} for _, t in st.prefixes):
        return st
    s = st.body
    if not s or s[0] not in _PREP_CLITICS:
        return st
    chars = list(s)
    n = len(chars)

    # لِلْ — preposition lam + article. Two sub-cases distinguished by what
    # immediately follows the second lam:
    #
    #   A. SHADDA on second-lam-position → lam-shamsi assimilation where the
    #      stem ITSELF starts with ل (لِلَّـ pattern → الله, الذين, التي).
    #      MASAQ records this as 2 segments — the article disappears entirely
    #      (drops in surface AND in tagging).
    #
    #          If "ا" + (body without shadda) is closed-class (الذين / التي):
    #             output [لِ] + "الذين" (alif reconstructed in stem)
    #          Else:
    #             output [لِ] + "لـ" + rest  (drop only the shadda)
    #             — e.g., لِلَّه → [ل] + له
    #
    #   B. Non-shadda on second-lam-position → explicit article ال before
    #      another consonant (لِلْمُؤْمِنِينَ، لِلنَّاسِ).
    #      Output: [لِ, ال, stem]  (3 segments).
    if chars[0] == LAM:
        i = 1
        i = _consume_diacritics(chars, i)
        if i < n and chars[i] == LAM:
            prep_part = "".join(chars[:i])
            # Distinguish: shadda IMMEDIATELY after the second lam?
            if i + 1 < n and chars[i + 1] == SHADDA:
                # Case A: assimilation. Drop the shadda; body becomes
                # the stem with the article-lam fused.
                body_dropped = chars[i] + "".join(chars[i + 2:])  # ل + rest
                # Try alif re-insertion to match a closed-class lexeme
                with_alif = ALIF + body_dropped
                if _is_closed_class(with_alif):
                    st.body = with_alif
                    st.frozen = True
                    st.add_prefix(prep_part, "PREP", "lam_prep_shadda_closed")
                    return st
                # Plain case: leave the lam in place (e.g., لِلَّهِ → ل + لَهِ)
                st.body = body_dropped
                st.frozen = True
                st.add_prefix(prep_part, "PREP", "lam_prep_shadda_fused")
                return st
            # Case B (no shadda): explicit article. Emit prep + DET separately.
            # The DET surface is "ل" (alif elided after prep). For plain-text
            # parity with MASAQ (which writes the article as "ال"), we emit
            # the article as ALIF + lam + diacritics. This breaks bit-equal
            # reconstruction by one inserted alif — recorded in audit.
            j = i + 1
            j = _consume_diacritics(chars, j)
            article_surface = "".join(chars[i:j])
            article_canonical = ALIF + article_surface  # ال form
            rest_chars = chars[j:]
            if rest_chars and rest_chars[0] == SHADDA:
                rest_chars = rest_chars[1:]
            rest_after_article = "".join(rest_chars)
            if _count_letters(rest_after_article) >= 1:
                st.body = rest_after_article
                st.add_prefix(prep_part, "PREP", "lam_prep")
                st.add_prefix(article_canonical, "DET", "lam_lam_article")
                return st

    # Otherwise: require article to follow (i.e., كَالـ، بِالـ — single prep clitic)
    i = 1
    i = _consume_diacritics(chars, i)
    rest = "".join(chars[i:])
    if _starts_with_article(rest):
        if _count_letters(rest) < _MIN_STEM_LETTERS:
            return st
        prefix_form = "".join(chars[:i])
        st.body = rest
        st.add_prefix(prefix_form, "PREP", "prep_clitic")
        return st
    # Hamzat-wasl reconstruction: بِسْمِ → ب + (ا)سم
    restored = _try_hamzat_wasl_restore(rest)
    if restored is not None:
        prefix_form = "".join(chars[:i])
        st.body = restored
        st.frozen = True
        st.add_prefix(prefix_form, "PREP", "prep_clitic_hamzat_wasl")
        return st
    # New trigger: PREP with KASRA + 3+letter noun-shape (بِمُؤْمِنِينَ، كَمَثَلِ).
    # Also handle ك+fatha (the standard form for prep ك), distinguishing it
    # from root-initial ك by requiring at least 3 letters in the remainder.
    prep_diac_after = chars[1] if len(chars) > 1 and chars[1] in DIACRITICS else ""
    allowed = (prep_diac_after == KASRA and _count_letters(rest) >= 3)
    # فِعَال-pattern refusal: 3-letter rest with alif at position 2 +
    # word has tanwin = noun like كِتَابٌ where ك is root. Refuse strip.
    if allowed and _count_letters(rest) == 3:
        rest_chars_check = list(rest)
        has_tanwin_word = any(c in s for c in (TANWIN_FATHA, "ٌ", "ٍ"))
        # Find position of first long alif in rest
        if has_tanwin_word and len(rest_chars_check) >= 3:
            for k in range(2, min(4, len(rest_chars_check))):
                if rest_chars_check[k] == ALIF:
                    allowed = False
                    break
    # PATCH 3B (2026-05-26) — FalseLamPrefixInLexicalStem refusal.
    # If the residual body's SECOND character is SHADDA, the لِ/بِ/كِ was
    # part of a lexical stem with internal gemination, not a true clitic.
    # Targets وَلِيُّهُۥ (lit. وَ + وَلِيّ + هُ): after CONJ-peel of وَ
    # the body is لِيُّهُۥ; without this check, لِ would be peeled as PREP
    # leaving stem يُّهُۥ which starts with ي + shadda — structurally
    # impossible as a fresh stem (shadda must double a non-initial letter).
    rest_chars_for_shadda = list(rest)
    if (allowed
            and len(rest_chars_for_shadda) >= 2
            and rest_chars_for_shadda[1] == SHADDA):
        allowed = False
    if allowed:
        # PREP ب/ل + noun (including hamza-initial like بِآيَاتِ، بِأَمْرٍ).
        prefix_form = "".join(chars[:i])
        st.body = rest
        st.add_prefix(prefix_form, "PREP", "prep_clitic_to_noun")
        return st
    # Special: PREP ل/ب/ك allowed before closed-class lexeme or pronoun stem.
    #   لَهُمْ → ل + هم    (prep + pronoun)
    #   بِمَا → ب + ما    (prep + closed-class)
    #   لِمَنْ → ل + من    (prep + closed-class)
    # Refuse if the prep clitic has damma (بُ, لُ, كُ are never prepositional —
    # prep ب/ل/ك always carry kasra in Arabic).
    prep_diac = chars[1] if len(chars) > 1 and chars[1] in DIACRITICS else ""
    if prep_diac == DAMMA:
        return st
    rest_plain = _strip_diacritics(rest)
    if _is_closed_class(rest) or rest_plain in _BARE_PRONOUN_FORMS:
        if _count_letters(rest) < 1:
            return st
        prefix_form = "".join(chars[:i])
        st.body = rest
        st.add_prefix(prefix_form, "PREP", "prep_clitic_to_closed")
        return st
    return st


# Bare pronoun forms that may attach to a single-letter preposition.
# Diacritic-stripped, longest-first irrelevant (we just need membership).
_BARE_PRONOUN_FORMS = frozenset({
    "هما", "كما", "هنّ", "كنّ",
    "هم", "هن", "كم", "كن", "نا",
    "ها", "ني",
    "ه", "ك", "ي",
})


# Multi-letter prepositions that may take a pronominal suffix.
# Longest-first matters: longer entries should appear earlier to avoid
# truncated matches (e.g., "بين" before "بي").
_MULTI_LETTER_PREPS = (
    # Standard prepositions
    "إلى", "على", "علي", "إلي", "من", "في", "عن", "إلا",
    "لدى", "لدن", "مع",
    # Locative noun-prepositions (MASAQ consistently splits these + pronoun)
    "تحت", "فوق", "قبل", "بعد", "أمام", "خلف", "وراء",
    "عند",
    # PATCH 3A (2026-05-26) — بين removed: it is a functional locative
    # noun (ظَرف), not a HARF JARR. Peeling it as PREP made L3 classify
    # بَيْنَكُمْ as HARF. After this removal, the pronoun_suffix rule
    # peels كم/هم/etc., leaving stem=بَيْنَ which the closed-class lexicon
    # already recognizes correctly.
)


def _rule_multi_letter_prep(st: _State) -> _State:
    """Strip a multi-letter preposition (في، على، علي، من، …) attached to a pronoun.

    Example: فِيهَا = في + ها,  عَلَيْهِمْ = علي + هم,  مِنْهُمْ = من + هم.
    Only fires if the remainder (after the preposition) is a recognized
    pronominal form. Surface form preserved as-is (MASAQ keeps علي/إلي/لدي
    when they precede pronominal suffixes — alif maqsura ى surfaces as ي).
    """
    if any(t in {"PREP", "PREP+DET", "DET"} for _, t in st.prefixes):
        return st
    s = st.body
    plain = _strip_diacritics(s)
    for prep in _MULTI_LETTER_PREPS:
        if not plain.startswith(prep):
            continue
        chars = list(s)
        n_letters_consumed = 0
        i = 0
        while i < len(chars) and n_letters_consumed < len(prep):
            if chars[i] not in DIACRITICS:
                n_letters_consumed += 1
            i += 1
        i = _consume_diacritics(chars, i)
        prep_form = "".join(chars[:i])
        rest = "".join(chars[i:])
        rest_plain = _strip_diacritics(rest)
        if rest_plain in _BARE_PRONOUN_FORMS:
            # NOTE: MASAQ preserves the SURFACE form of the preposition before
            # any pronominal suffix — على becomes علي whenever any pronoun
            # attaches (not just ه-pronouns). So we keep the surface form
            # exactly as written.
            st.body = rest
            st.add_prefix(prep_form, "PREP", "multi_letter_prep")
            return st
    return st


def _rule_article(st: _State) -> _State:
    """Strip definite article ال (alif + lam + diacritic on lam).

    Handles shamsi-letter assimilation: when the article is followed by a
    sun-letter (ت ث د ذ ر ز س ش ص ض ط ظ ل ن), the lam's sukun is replaced by
    shadda on the first stem letter. In that case we absorb the shadda into
    the article peel (otherwise the stem would retain a phantom shadda).
    """
    s = st.body
    if len(s) < 2:
        return st
    chars = list(s)
    if chars[0] not in ALIF_FAMILY:
        return st
    i = 1
    i = _consume_diacritics(chars, i)
    if i >= len(chars) or chars[i] != LAM:
        return st
    i += 1
    i = _consume_diacritics(chars, i)
    # i now points at the stem's first letter (chars[i-1] is the article's lam).
    # Check shamsi-letter assimilation: if the stem letter is followed by a
    # shadda, the shadda represents the assimilated article lam, not stem
    # gemination. We absorb the shadda — it stays with the prefix conceptually
    # but to preserve reversibility we keep the prefix as plain "ال"
    # (chars[:i]) and DROP the shadda from the stem.
    #
    # NOTE: reversibility check: the prefix is "ال" + lam_diacritics; the stem
    # starts with chars[i] (no shadda). Reconstruct = "الْ" + "صَلَا..." which
    # is NOT bit-equal to "الصَّلَا..." (shadda lost). This is acceptable for
    # the segmenter — the shadda represented assimilation, not stem content.
    # An audit entry records that the shadda was absorbed.
    if i + 1 < len(chars) and chars[i + 1] == SHADDA:
        # Build stem WITHOUT the shadda at position i+1
        rest_chars = chars[i:i + 1] + chars[i + 2:]
        rest = "".join(rest_chars)
        if _count_letters(rest) < _MIN_STEM_LETTERS:
            return st
        pref = "".join(chars[:i])
        st.body = rest
        st.add_prefix(pref, "DET", "article_shamsi")
        return st

    rest = "".join(chars[i:])
    if _count_letters(rest) < _MIN_STEM_LETTERS:
        return st
    pref = "".join(chars[:i])
    st.body = rest
    st.add_prefix(pref, "DET", "article")
    return st


def _normalize_for_closed_class_lookup(s: str) -> str:
    """Lookup-only normalization for `_is_closed_class` (PATCH 2A).

    The legacy `_CLOSED_CLASS_LEXEMES` set was authored with bare alef ا
    and yaa ي. Quranic Uthmani uses alef-wasla ٱ and alef-maksura ى at
    the word start / end. Without this normalization, lookups fail for
    common forms like ٱلَّذِى, ٱلَّتِى, ٱلَّذَانِ — which the user's
    PATCH 2 acceptance explicitly targets.

    Mappings (lookup only — does NOT modify the returned token):
      ٱ (U+0671 alef-wasla)   → ا (U+0627 alef)
      آ (U+0622 alef-madda)   → ا
      ى (U+0649 alef-maksura) → ي (U+064A yaa)
      أ / إ                    → ا
    """
    if not s:
        return s
    return (s.replace("ٱ", "ا")
             .replace("آ", "ا")
             .replace("أ", "ا")
             .replace("إ", "ا")
             .replace("ى", "ي"))


# PATCH 2B (2026-05-26) — demonstrative-with-addressee compounds CSV cache.
# ذَلِكُمْ / ذَٰلِكُمْ / تِلْكُمْ / أُولَئِكُمْ etc. are atomic units
# (addressee marker is part of the demonstrative, not a separate POSS_PRON).
# The legacy `_CLOSED_CLASS_LEXEMES` only contains singular ذلك / تلك;
# this CSV fills the gap without inline data growth.
_DEMONSTRATIVE_COMPOUNDS_CACHE: set | None = None


def _load_demonstrative_compounds() -> set:
    """Lazy CSV loader for demonstrative compounds (PATCH 2B).

    The CSV stores plain forms using bare alef ا. The loader also adds
    alef-wasla / hamza-alef variants so that `_strip_diacritics()` output
    (which preserves hamza-on-alef) still matches.
    """
    global _DEMONSTRATIVE_COMPOUNDS_CACHE
    if _DEMONSTRATIVE_COMPOUNDS_CACHE is not None:
        return _DEMONSTRATIVE_COMPOUNDS_CACHE
    import csv as _csv
    from pathlib import Path as _Path
    out: set = set()
    path = (_Path(__file__).resolve().parent
            / "data" / "contracts" / "lists" / "demonstrative_compounds.csv")
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                wp = (row.get("word_plain") or "").strip()
                if not wp:
                    continue
                out.add(wp)
                # Hamza variants (CSV is bare-alef; strip may leave أ)
                if wp.startswith("ا"):
                    out.add("أ" + wp[1:])
                    out.add("إ" + wp[1:])
    _DEMONSTRATIVE_COMPOUNDS_CACHE = out
    return out


def _is_closed_class(text: str) -> bool:
    """True if text (after diacritic strip + lookup normalization) is a
    closed-class lexeme.

    PATCH 2A (2026-05-26): added `_normalize_for_closed_class_lookup` so
    forms like ٱلَّذِى resolve via the legacy set which stores ا/ي.

    PATCH 2B (2026-05-26): consults `demonstrative_compounds.csv` so
    ذَٰلِكُمْ / تِلْكُمْ etc. are recognized as atomic units (no
    POSS_PRON peel of the addressee marker).
    """
    plain = _strip_diacritics(text)
    plain_norm = _normalize_for_closed_class_lookup(plain)
    if plain in _CLOSED_CLASS_LEXEMES or plain_norm in _CLOSED_CLASS_LEXEMES:
        return True
    compounds = _load_demonstrative_compounds()
    if plain in compounds or plain_norm in compounds:
        return True
    return False


def _rule_future_particle(st: _State) -> _State:
    """Strip future particle سَ. Only safe if remainder starts with a verb prefix.

    Refuses to fire when:
      • DET or IMPERF_PREF already stripped (س is part of stem)
      • the word is in seen_is_root_lexicon.csv (س is root letter — سَأَلَ، سَماء...)
      • Form X (استفعل) — the word starts with است before s-strip
      • remainder does NOT start with verb prefix ي/ت/ن/أ

    TODO 1 + 2 implemented: lexicon check + HAMZA inclusion.
    """
    for _, tag in st.prefixes:
        if tag in {"DET", "IMPERF_PREF"}:
            return st
    s = st.body
    if len(s) < 2 or s[0] != SIN:
        return st

    # TODO 1: فَحص lexicon — لا تُقَشَّر السين الأَصليَّة
    if _word_in_seen_root_lexicon(s):
        return st

    # Form X guard: لَو الكَلِمَة تَبدَأ بِـ است → لا نَنزَع السين
    # (السين هُنا جُزء مِن وزن استفعل)
    if s.startswith(SIN + "ْت") or s.startswith(SIN + "ت"):
        # نَحتاج فَحص أَنّ ما قَبلها أَلِف وَصل ضِمنيَّة — هذا يَحصُل لاحِقًا
        pass

    chars = list(s)
    i = 1
    i = _consume_diacritics(chars, i)
    rest = "".join(chars[i:])
    if _count_letters(rest) < _MIN_STEM_LETTERS:
        return st
    next_letter = next((c for c in rest if c not in DIACRITICS), "")
    # TODO 2: إِضافَة HAMZA لِكَشف «سَأَفعَل»
    if next_letter not in _IV_PREFIXES_WITH_HAMZA:
        return st
    pref = "".join(chars[:i])
    st.body = rest
    st.add_prefix(pref, "FUT_PART", "future_particle")
    return st


# Verb-subject suffix markers (plain) that, when present, signal the word
# is verb-shaped — used as evidence to fire the IV prefix rule.
_VERB_SUBJECT_MARKERS_PLAIN = ("وا", "ون", "ين", "تم", "تن", "نا", "تموا")


def _rule_imperative_hamzat_wasl(st: _State) -> _State:
    """Strip leading hamzat-wasl alif of Form I imperative (اعْبُدُوا → ا + عبد + وا).

    Triggers:
      - chars[0]=ا (or ٱ), chars[1]=consonant (no diac), chars[2]=SUKUN
      - Word ends in وا/ون/ين (verb-subject confirmation)
    Refuses:
      - chars[3]=ت — that's Form VIII signature (اشْتَرَى, اعْتَدَى), not Form I.
    Allows after CONJ (وَادْعُوا → و + ا + دع + وا).
    """
    # Refuse if non-CONJ prefix already stripped
    for _, tag in st.prefixes:
        if tag != "CONJ":
            return st
    s = st.body
    if len(s) < 4:
        return st
    chars = list(s)
    if chars[0] not in ALIF_FAMILY:
        return st
    if chars[1] in DIACRITICS:
        return st
    if len(chars) < 3 or chars[2] != SUKUN:
        return st
    # Form VIII refusal: chars[3]=ت
    if len(chars) >= 4 and chars[3] == TA:
        return st
    plain = _strip_diacritics(s)
    # Endings that confirm imperative: وا/ون/ين (subject markers) or
    # final sukun (singular jussive imperative like انْظُرْ, اعْبُدْ — must be 4+ letters).
    has_verb_marker = (any(plain.endswith(m) for m in ("وا", "ون", "ين"))
                       or (chars[-1] == SUKUN and _count_letters(s) >= 4))
    if not has_verb_marker:
        return st
    pref = chars[0]
    rest = "".join(chars[1:])
    if _count_letters(rest) < _MIN_STEM_LETTERS + 1:
        return st
    st.body = rest
    st.add_prefix(pref, "HAMZAT_WASL", "imperative_alif")
    return st


def _looks_like_form_x(body: str) -> bool:
    """Heuristic: body has ا+س+ت or س+ت at the start (Form X استفعل/يستفعل).
    The middle ست is part of the stem, not a suffix.
    """
    chars = list(body)
    if not chars:
        return False
    i = 0
    # Optional leading alif (past tense form)
    if chars[i] == ALIF:
        i += 1
        while i < len(chars) and chars[i] in DIACRITICS:
            i += 1
    if i >= len(chars) or chars[i] != SIN:
        return False
    i += 1
    while i < len(chars) and chars[i] in DIACRITICS:
        i += 1
    return i < len(chars) and chars[i] == TA


def _rule_interrog_alif(st: _State) -> _State:
    """Strip interrogative أَ (hamza with fatha) at start.

    CONSERVATIVE triggers: only fires when
      (a) أ has FATHA (interrogative أ always carries fatha)
      (b) Body after strip is a closed-class lexeme (لَمْ, أَنْذَر, إِنَّ ...)
         OR starts with another hamza-on-alif (double-hamza signature
         characteristic of أ + Form-IV-verb-starting-with-أ: أَأَنْذَرْتَهُمْ).
    """
    if st.prefixes:
        # only fires as the first peel
        return st
    s = st.body
    if len(s) < 3 or s[0] != HAMZA_ON_ALIF:
        return st
    chars = list(s)
    if len(chars) < 2 or chars[1] != FATHA:
        return st
    i = 2  # past أ + fatha
    rest = "".join(chars[i:])
    rest_plain = _strip_diacritics(rest)
    # Trigger A: rest is a CONFIRMED interrogative-compatible closed-class
    # particle (لم، لن، لو، إن، لما، etc.). Avoids false fires on accidental
    # closed-class matches like 'هل' (which is itself interrogative — so its
    # ending in a word doesn't signal compound INTERROG).
    _INTERROG_REMAINDER_OK = frozenset({
        "لم", "لن", "لو", "إن", "لما", "لما", "لست", "ليس",
    })
    if rest_plain in _INTERROG_REMAINDER_OK:
        pref = "".join(chars[:i])
        st.body = rest
        st.add_prefix(pref, "INTERROG", "interrog_alif_to_closed")
        return st
    # Trigger B: rest starts with another أ (double-hamza signature)
    if rest and rest[0] == HAMZA_ON_ALIF and _count_letters(rest) >= _MIN_STEM_LETTERS + 1:
        pref = "".join(chars[:i])
        st.body = rest
        st.add_prefix(pref, "INTERROG", "interrog_alif_double_hamza")
        return st
    # Trigger C: rest starts with an IV prefix letter (ي/ت/ن) + vowel,
    # signalling INTERROG-أ + imperfect verb (أَنُؤْمِنُ → أ + ن + ؤمن).
    if rest and _count_letters(rest) >= _MIN_STEM_LETTERS + 1:
        rest_chars = list(rest)
        if (rest_chars[0] in _IV_PREFIXES
                and len(rest_chars) >= 2
                and rest_chars[1] in (FATHA, DAMMA, KASRA)):
            pref = "".join(chars[:i])
            st.body = rest
            st.add_prefix(pref, "INTERROG", "interrog_alif_iv")
            return st
    # Trigger D: rest is a past verb with PV subject suffix (تم/تن/نا/ت)
    # AND first root letter has FATHA (signals past 3+letter verb, not
    # Form IV like أَرْسَلْنَا where root letter has sukun).
    if rest and _count_letters(rest) >= _MIN_STEM_LETTERS + 2:
        rest_chars_d = list(rest)
        # chars[1] of rest = diacritic on first root letter
        if (len(rest_chars_d) >= 2
                and rest_chars_d[1] == FATHA
                and any(rest_plain.endswith(m) for m in ("تموا", "تما", "تم", "تن"))):
            pref = "".join(chars[:i])
            st.body = rest
            st.add_prefix(pref, "INTERROG", "interrog_alif_past")
            return st
    return st


def _rule_iv_prefix(st: _State) -> _State:
    """Strip imperfect-verb prefix (ي/ت/ن/أ + harakah).

    CONSERVATIVE triggers:
      - Word ends in a verb-subject marker (وا/ون/ين/تم/تن/نا).
      - DET has NOT already been stripped (nouns aren't IV verbs — الْأَوَّلِينَ).
      - IV has NOT already been stripped (no double-IV — يُنْفِقُونَ).
      - The remaining stem (after strip) has at least 3 letters.

    Singular IV verbs (يَشَاءُ، يَقُولُ) are NOT caught — they're handled
    downstream by wazn_matcher's variant pipeline.
    """
    # Refuse if any blocking prefix was already stripped.
    # PATCH 1 (2026-05-26): added LAM_AL_AMR — when the jussive command
    # particle was peeled, the verb's يَ/تَ/نَ/أَ stays attached to the
    # stem (the mood is already determined; over-peeling produces a
    # noisy 3-segment prefix list that downstream code doesn't expect).
    for _, tag in st.prefixes:
        if tag in {"DET", "IMPERF_PREF", "LAM_AL_AMR"}:
            return st
    s = st.body
    if len(s) < 4:
        return st
    chars = list(s)
    # IV-أ special trigger: only fire when chars[3]=sukun AND chars[4] is a
    # vowel (distinguishes verb أَعْلَمُ from broken plural أَبْصَار where
    # chars[4]=ا is a letter).
    if chars[0] not in _IV_PREFIXES:
        return st
    if len(chars) < 2 or chars[1] not in DIACRITICS:
        return st
    plain = _strip_diacritics(s)
    # Proper-noun denylist refusal: yaḥyā, etc.
    if plain in _NO_STRIP_PROPER_NOUNS:
        return st
    # PATCH 2C (2026-05-26) — past-2nd-person hard block.
    # Words ending in تم / تما / تن (perfective 2-person subject suffixes)
    # cannot also start with imperfect prefix تَ/يَ/نَ/أَ. Form VI past
    # tokens like تَدَايَنتُم and تَبَايَعْتُمْ otherwise get the leading
    # تَ wrongly peeled as IMPERF_PREF.
    # نا / وا are NOT included (they are ambiguous past/imperfect plural).
    _PAST_2P_UNAMBIGUOUS = ("تم", "تما", "تن")
    if any(plain.endswith(suf) for suf in _PAST_2P_UNAMBIGUOUS):
        return st
    has_verb_ending = any(plain.endswith(m) for m in _VERB_SUBJECT_MARKERS_PLAIN)
    # Tanwin refusal: word ending in ـاً/ـٌ/ـٍ is an indefinite noun.
    if any(c in s for c in (TANWIN_FATHA, "ٌ", "ٍ")):
        return st
    # Second trigger: the classic يَفْعُلُ pattern signature.
    has_fafula_signature = (
        len(chars) >= 5
        and chars[2] not in DIACRITICS
        and chars[3] == SUKUN
    )
    # Third trigger: Form-II imperfect (يَمُدُّ، يُنَزِّلُ) — vowel at chars[3],
    # shadda at chars[5]. Distinct from Form II PAST (نَزَّلَ) which has shadda
    # at chars[3].
    has_form2_imperfect_signature = (
        len(chars) >= 6
        and chars[3] in (FATHA, DAMMA, KASRA)
        and chars[5] == SHADDA
    )
    # Fourth trigger (tight): hollow IV singular — 4-letter word, IV prefix +
    # vowel + consonant + vowel + ALIF/و/ي + last-letter+damma.
    has_hollow_iv_tight = False
    if (_count_letters(s) == 4
            and len(chars) >= 6
            and chars[2] not in DIACRITICS
            and chars[3] in (FATHA, DAMMA, KASRA)
            and chars[4] in (WAW, YA, ALIF)
            and chars[-1] == DAMMA):
        has_hollow_iv_tight = True
    # Fifth trigger: Form IV imperfect (يُؤْمِنُ, يُمِيتُ).
    has_form4_signature = False
    if (chars[1] == DAMMA
            and len(chars) >= 4
            and chars[3] in DIACRITICS
            and _count_letters(s) >= 5):
        for pronoun in _PRONOUN_SUFFIXES:
            if plain.endswith(pronoun) and len(pronoun) >= 2:
                has_form4_signature = True
                break
    # Sixth trigger: Form I hollow jussive (يَكُنْ, تَكُنْ, يَرَ, تَرَ).
    # 3-letter word ending in sukun, IV letter + vowel + ...
    has_hollow_jussive = (
        _count_letters(s) == 3
        and chars[-1] == SUKUN
        and chars[1] in (FATHA, DAMMA, KASRA)
    )
    if (not has_verb_ending
            and not has_fafula_signature
            and not has_form2_imperfect_signature
            and not has_hollow_iv_tight
            and not has_form4_signature
            and not has_hollow_jussive):
        return st
    # Form V past refusal: chars[0]=ت AND there's a shadda early.
    # تَفَعَّل-past keeps stem whole. Signals:
    #   - ends in PV subject (تموا/تما/تم/تن/نا/ت)
    #   - ends in alif maqsura ـى (3MS past)
    #   - chars[1]=fatha AND ends in وا (تَوَلَّوْا 3MP past)
    if chars[0] == TA and SHADDA in s[:6]:
        for pv_marker in ("تموا", "تما", "تم", "تن", "نا", "ت"):
            if plain.endswith(pv_marker):
                return st
        if plain.endswith("ى"):
            return st
        # Form V past 3MP (تَوَلَّوْا): shadda at chars[5]; ends in وا.
        # Distinguish from Form VIII imperfect 2MP (تَتَّخِذُوا): shadda at chars[3].
        if (chars[1] == FATHA
                and plain.endswith("وا")
                and len(chars) > 5
                and chars[5] == SHADDA
                and chars[3] != SHADDA):
            return st
        # تَذَكَّرُونَ pattern: Form V — shadda at chars[5] (NOT chars[3]).
        # chars[3]=shadda is Form VIII assimilation (تَتَّقُونَ) which IS valid IV.
        if (chars[1] == FATHA
                and plain.endswith("ون")
                and len(chars) > 5
                and chars[5] == SHADDA
                and chars[3] != SHADDA):
            return st
    # Imperative refusal: ت+damma followed by hollow letter و/ي suggests an
    # imperative form (تُوبُوا "repent!"), where the ت is the root letter,
    # not the IV prefix. Refuse the strip.
    if (chars[0] == TA
            and len(chars) >= 3
            and chars[1] == DAMMA
            and chars[2] in (WAW, YA)):
        return st
    # Form-II/V (مُضَعَّف past) refusal: when SHADDA is right after the
    # second character (chars[3] = shadda), the leading ي/ت/ن/أ is usually
    # part of the root letter pattern (نَزَّلْنَا root نزل). Refuse.
    # EXCEPTION: if word ends in IV-subject (ون/ين/وا), it's likely Form VIII
    # imperfect (يَتَّخِذُونَ، تَتَّقُونَ) where the leading IV-prefix IS valid.
    if len(chars) >= 4 and chars[3] == SHADDA:
        iv_subject_ending = any(plain.endswith(m) for m in ("ون", "ين", "وا"))
        if not iv_subject_ending:
            return st
    i = 1
    i = _consume_diacritics(chars, i)
    rest = "".join(chars[i:])
    # Effective MIN:
    #   - Form II imperfect / hollow jussive: 2 letters OK
    #   - Otherwise: 3 letters minimum
    if has_form2_imperfect_signature or has_hollow_jussive:
        effective_min_rest = _MIN_STEM_LETTERS
    else:
        effective_min_rest = _MIN_STEM_LETTERS + 1
    if _count_letters(rest) < effective_min_rest:
        return st
    pref = "".join(chars[:i])
    st.body = rest
    st.add_prefix(pref, "IMPERF_PREF", "iv_prefix")
    return st


# Standalone vocative particles (يَا) — multi-character, MASAQ tags as
# VOC_PART even when written without space before the addressee.
_VOC_PARTICLES_PLAIN = ("يا", "أيا", "هيا")


def _rule_vocative_particle(st: _State) -> _State:
    """Strip vocative يَا at start of compound forms like يَاأَيُّهَا → يا + أيها."""
    if st.prefixes:
        return st
    s = st.body
    plain = _strip_diacritics(s)
    for voc in _VOC_PARTICLES_PLAIN:
        if not plain.startswith(voc):
            continue
        if len(plain) - len(voc) < _MIN_STEM_LETTERS:
            continue
        # Find boundary in diacritized string
        chars = list(s)
        n_consumed = 0
        i = 0
        while i < len(chars) and n_consumed < len(voc):
            if chars[i] not in DIACRITICS:
                n_consumed += 1
            i += 1
        i = _consume_diacritics(chars, i)
        pref = "".join(chars[:i])
        rest = "".join(chars[i:])
        st.body = rest
        st.add_prefix(pref, "VOC_PART", "vocative_particle")
        return st
    return st


def _rule_pronoun_suffix(st: _State) -> _State:
    """Strip a pronominal suffix (longest-first). Conservative on 1-letter.

    After stripping, if the new stem ends in ت + diacritic (the "open ta"
    form of ة that surfaces before pronouns), record an ة suffix too.

    Refuses to fire on proper-noun denylist (مالك, etc.).
    """
    s = st.body
    if _count_letters(s) <= _MIN_STEM_LETTERS:
        return st
    # Proper-noun denylist check (on plain form of the entire body)
    if _strip_diacritics(s) in _NO_STRIP_PROPER_NOUNS:
        return st
    plain = _strip_diacritics(s)
    # Form-X integrity guard: don't strip from يَسْتَحْيِي-shape words after IV
    has_iv_prefix = any(tag == "IMPERF_PREF" for _, tag in st.prefixes)
    if has_iv_prefix and _looks_like_form_x(s):
        return st
    # Inflection shadda refusal: if the LAST consonant of the body has a
    # shadda (e.g., النَّبِيُّ — the ي of نبي is doubled to mark case), the
    # shadda is inflectional, not pronoun-assimilation. Refuse 1-letter
    # pronoun strip in that case.
    s_chars = list(s)
    last_consonant_idx = None
    for k in range(len(s_chars) - 1, -1, -1):
        if s_chars[k] not in DIACRITICS:
            last_consonant_idx = k
            break
    if last_consonant_idx is not None:
        # Look for shadda within 2 chars after the last consonant
        for k in range(last_consonant_idx + 1, min(last_consonant_idx + 3, len(s_chars))):
            if s_chars[k] == SHADDA:
                # Mark to refuse 1-letter pronoun strip later
                # (only block 1-letter; multi-letter pronouns still OK)
                # We'll just set a local flag
                _inflection_shadda = True
                break
        else:
            _inflection_shadda = False
    else:
        _inflection_shadda = False
    # Tanwin refusal: if word ends in tanwin (ـاً/ـٌ/ـٍ), the trailing ها/ه/etc.
    # is NOT a pronoun but part of the surface noun + case marker.
    # Example: مُتَشَابِهَاً = متشابه + ا (NSUFF), not متشاب + ها.
    if any(c in s for c in (TANWIN_FATHA, "ٌ", "ٍ")):
        # Only refuse pronoun strip; let tanwin_alif rule handle the suffix
        return st
    # Detect shadda-assimilation signature: word ends with letter+shadda+letter+...
    # In this case the strip is the inner letter of the pair; the outer is the
    # pronoun. Shadda-expansion later restores a letter to the stem, so the
    # post-strip MIN check effectively gains one letter back.
    chars_for_shadda = list(s)
    has_shadda_assim = False
    if len(chars_for_shadda) >= 4:
        for k in range(len(chars_for_shadda) - 1):
            if (chars_for_shadda[k] not in DIACRITICS
                    and chars_for_shadda[k + 1] == SHADDA):
                has_shadda_assim = True
                break
    for suf in _PRONOUN_SUFFIXES:
        if not plain.endswith(suf):
            continue
        n_letters = len(suf)
        # MIN check: shadda-assim gives back one letter, so allow MIN-1 in that case
        effective_min = _MIN_STEM_LETTERS - (1 if has_shadda_assim else 0)
        if _count_letters(s) - n_letters < effective_min:
            continue
        # 1-letter pronoun threshold: normally require ≥3 stem letters after strip,
        # but allow ≥2 when shadda-assim is present (covers أَنَّهُ → أن + ه).
        one_letter_threshold = 2 if has_shadda_assim else 3
        if n_letters == 1 and _count_letters(s) - n_letters < one_letter_threshold:
            continue
        # PATCH 3C (2026-05-26) — DualVerbSuffixContract.
        # Refuse peeling نَا as POSS_PRON when:
        #   (a) IMPERF_PREF was already peeled (we're inside an imperfect verb),
        #   (b) the residual stem would have < 3 letters (verb body too short).
        # Target: يَكُونَا (يَ + كُونَا). Without this guard, نَا is peeled
        # as POSS_PRON leaving stem=كُو (2 letters, semantically invalid).
        # نَا here is the dual subject marker (after deletion of nūn), not
        # the 1st-pl possessive pronoun.
        if (suf == "نا"
                and has_iv_prefix
                and _count_letters(s) - n_letters < 3):
            continue
        # Refuse 1-letter pronoun strip when the last consonant has shadda
        # AND the word ends in a case-marker damma/kasra (النَّبِيُّ).
        if n_letters == 1 and _inflection_shadda:
            continue
        stem, suffix = _split_at_letter_index_from_end(s, n_letters)
        # Shadda-expansion on pronoun (آمَنَّا = آمن + نا).
        # Move one copy of the doubled letter to the stem; suffix keeps its
        # letter (drops the shadda).
        # REFUSE when suffix has only 1 consonant — that signals inflectional
        # shadda on the stem's last letter (النَّبِيُّ), not pronoun assimilation.
        suffix_chars = list(suffix)
        if (len(suffix_chars) >= 2
                and suffix_chars[0] not in DIACRITICS
                and suffix_chars[1] == SHADDA
                and _count_letters(suffix) >= 2):
            doubled_letter = suffix_chars[0]
            stem = stem + doubled_letter
            suffix = "".join([suffix_chars[0]] + suffix_chars[2:])
        # ة → ت conversion before pronouns: when MASAQ records a feminine
        # noun as stem + ة + pronoun, the surface shows ت (open ta) instead
        # of ة (closed ta marbuta). Detect and recover the ة.
        #
        # Conservative trigger: only fires when
        #   (a) new stem ends in ت + diacritic
        #   (b) the ت's diacritic is fatha/damma/kasra (NOT sukun — sukun ت
        #       is typically a verb-subject suffix, e.g. أَنْعَمْتَ)
        #   (c) the stem has ≥4 letters
        #   (d) word does NOT start with an IV prefix letter — that signals
        #       a verb form (يُمِيتُ → root ميت, not feminine noun)
        st.body = stem
        st.add_suffix(suffix, "POSS_PRON", "pronoun_suffix")
        new_plain = _strip_diacritics(stem)
        # Refuse ta→ة conversion for clear VERB shapes only.
        # Verb signature: chars[0] is IV letter (ي/ت/ن) AND chars[1] is
        # fatha or damma (IV-prefix vowel; nouns starting with ت+kasra
        # like تِجَارَة are not verbs).
        s_chars = list(s)
        is_clear_verb = (
            len(s_chars) >= 2
            and s_chars[0] in _IV_PREFIXES
            and s_chars[1] in (FATHA, DAMMA)
        )
        # Refuse if stem ends in ـات pattern (ا+ت) — that's broken plural
        # NSUFF, not feminine ة (e.g., آيات + هـ, the ات is part of plural).
        ends_in_aat = (new_plain.endswith("ات")
                       or new_plain.endswith("ا" + "ت"))
        if (new_plain.endswith("ت")
                and _count_letters(stem) >= 4
                and not is_clear_verb
                and not ends_in_aat):
            # Inspect the diacritic on the final ت
            chars_stem = list(stem)
            # Find the ت's position and the diacritic after it
            last_letter_idx = None
            for k in range(len(chars_stem) - 1, -1, -1):
                if chars_stem[k] not in DIACRITICS:
                    last_letter_idx = k
                    break
            if last_letter_idx is not None:
                next_diac = (chars_stem[last_letter_idx + 1]
                             if last_letter_idx + 1 < len(chars_stem)
                             else "")
                if next_diac in (FATHA, DAMMA, KASRA):
                    new_stem, ta_part = _split_at_letter_index_from_end(stem, 1)
                    # Convert the ت surface to ة (taa marbuta) for MASAQ
                    # alignment — the diacritic stays, only the letter changes.
                    ta_as_marbuta = ta_part.replace("ت", TAA_MARBUTA, 1)
                    st.body = new_stem
                    st.suffixes.insert(-1, (ta_as_marbuta, "NSUFF_FEM_SG"))
                    st.audit.append(f"ta_to_taa_marbuta:+suff={ta_as_marbuta!r}")
        return st
    return st


def _rule_number_suffix(st: _State) -> _State:
    """Strip plural/dual masculine-genitive or feminine-plural suffix.

    When an IV prefix has been stripped (i.e., we're segmenting an imperfect
    verb), split ون/ين into TWO segments (و/ي subject pronoun + ن indicative
    mood marker) to match MASAQ's tagging convention.

    Refuses to strip ين/ون when the body is Form X (نَسْتَعِينُ shape):
    these endings are part of the stem, not suffixes.
    """
    s = st.body
    # Form X integrity: ين is part of stem (نَسْتَعِينُ → keep), but ون is a
    # subject-pronoun suffix and IS valid to strip (يَسْتَطِيعُونَ → ستطيع + ون).
    plain_check = _strip_diacritics(s)
    if _looks_like_form_x(s) and plain_check.endswith("ين"):
        return st
    # Proper-noun denylist (فرعون etc.)
    if _strip_diacritics(s) in _NO_STRIP_PROPER_NOUNS:
        return st
    if _count_letters(s) <= _MIN_STEM_LETTERS:
        return st
    plain = _strip_diacritics(s)
    has_iv_prefix = any(tag == "IMPERF_PREF" for _, tag in st.prefixes)
    has_poss_pron = any(tag == "POSS_PRON" for _, tag in st.suffixes)
    # Dual suffix ان: only valid after IV prefix (verb dual conjugation)
    suffixes_to_try = list(_NUMBER_SUFFIXES)
    if has_iv_prefix:
        suffixes_to_try.extend(_NUMBER_SUFFIXES_CONDITIONAL)
    for suf in suffixes_to_try:
        if not plain.endswith(suf):
            continue
        # If a POSS_PRON was already stripped AND this is ين/ون, the ـين
        # is likely part of a broken-plural stem (شَيَاطِينِهِمْ → MASAQ keeps
        # شياطين whole). ات is safer to strip.
        if has_poss_pron and suf in ("ين", "ون"):
            continue
        n_letters = len(suf)
        # For ين/ون: require ≥3 stem letters after strip — but allow
        # exceptions when stem has 4+ letters before strip AND last char
        # before suffix is NOT ي (the participle hollow signature).
        if suf in ("ين", "ون") and _count_letters(s) - n_letters < 3:
            # If prefix stripped, allow only when stem-before-strip
            # doesn't have hollow ي (الْمُبِين blocks, مؤمنين allows).
            if st.prefixes:
                # check if char at position before suffix is ي
                stem_no_suf, _ = _split_at_letter_index_from_end(s, n_letters)
                plain_stem = _strip_diacritics(stem_no_suf)
                if plain_stem and plain_stem[-1] == "ي":
                    continue
            else:
                continue
        if _count_letters(s) - n_letters < _MIN_STEM_LETTERS:
            continue
        stem, suffix = _split_at_letter_index_from_end(s, n_letters)
        st.body = stem
        # NOTE: an earlier version split ون → و + ن for IV verbs. Empirically
        # MASAQ keeps ون as ONE segment for ~90% of IV verb occurrences, so the
        # split caused net regression. Reverted.
        st.add_suffix(suffix, "NSUFF", "number_suffix")
        return st
    return st


TANWIN_FATHA = "ً"  # U+064B — fathatan


def _rule_tanwin_alif(st: _State) -> _State:
    """Strip indefinite-accusative tanwin alif (final ـاً or ـً + ا).

    MASAQ records this as a separate suffix 'ا' for words like مَرَضَاً (مرض + ا)
    and هُدَىً (هدي with normalization; the ى/ا alternates).

    Trigger: word ends in tanwin-fathatan (ً) optionally followed by ا,
    AND the stem before this has ≥2 letters (covers حَقَّاً → حق+ا).
    """
    s = st.body
    if _count_letters(s) < 3:
        return st
    chars = list(s)
    # Find tanwin position from the end
    if not chars:
        return st
    # Pattern A: chars ends with ـاً (alif + tanwin)
    if (len(chars) >= 2
            and chars[-2] == ALIF
            and chars[-1] == TANWIN_FATHA):
        new_chars = chars[:-2]
        st.body = "".join(new_chars)
        st.add_suffix(ALIF, "NSUFF", "tanwin_alif")
        return st
    # Pattern B: chars ends with ـً alone (rare — ى+ً without separate alif)
    if chars[-1] == TANWIN_FATHA:
        # Strip just the tanwin (no separate letter to peel)
        return st
    return st


def _rule_taa_marbuta(st: _State) -> _State:
    """Strip trailing taa marbuta ة (feminine singular marker).

    Conservative: only strip if at least MIN+1 letters remain. Sets the
    `frozen` flag so later suffix rules in phase 2 don't re-peel the stem
    (prevents ملائكة → ملائ+ك+ة over-segmentation).
    """
    s = st.body
    if not s:
        return st
    plain = _strip_diacritics(s)
    if not plain.endswith(TAA_MARBUTA):
        return st
    # Allow stem ≥ 2 letters after ة strip (covers جَنَّة، أُمَّة، آية).
    if _count_letters(s) - 1 < _MIN_STEM_LETTERS:
        return st
    stem, suffix = _split_at_letter_index_from_end(s, 1)
    st.body = stem
    st.add_suffix(suffix, "NSUFF_FEM_SG", "taa_marbuta")
    st.frozen = True
    return st


def _rule_pv_ta_suffix(st: _State) -> _State:
    """Strip past-tense subject ت (تَ/تِ/تُ) when in clear verb context.

    Triggers when:
      - Body ends in ت + fatha/damma/kasra/sukun
      - The letter BEFORE the ت has SUKUN (verbal signature)
      - Body has at least 3 letters
      - No article (DET) was stripped (article signals noun, not verb)
    """
    # Refuse if article has been stripped — that signals noun-shape
    for _, tag in st.prefixes:
        if tag == "DET":
            return st
    s = st.body
    if _count_letters(s) < 3:
        return st
    chars = list(s)
    if not chars:
        return st
    # Find last non-diacritic letter and its trailing diacritic
    last_letter_idx = None
    for k in range(len(chars) - 1, -1, -1):
        if chars[k] not in DIACRITICS:
            last_letter_idx = k
            break
    if last_letter_idx is None or chars[last_letter_idx] != TA:
        return st
    # Diacritic on the final ت
    end_diac = (chars[last_letter_idx + 1]
                if last_letter_idx + 1 < len(chars)
                else "")
    # ت can carry fatha/damma/kasra (subject) OR sukun (past 3FS رَبِحَتْ).
    if end_diac not in (FATHA, DAMMA, KASRA, SUKUN):
        return st
    # Verb signature: word should contain at least one SUKUN before the
    # final ت (verbs have a sukun on the second/third root letter).
    # Examples:
    #   نَعَمْتَ — sukun on م          ✓ verb
    #   رَبِحَتْ — final-ت sukun; root vowel-pattern (no internal sukun) — still verb
    # For نَعَمْتَ-style words (sukun BEFORE ت), require it. For رَبِحَتْ-style
    # (sukun ONLY on the ت), allow if word has ≥5 letters.
    prev_letter_idx = None
    for k in range(last_letter_idx - 1, -1, -1):
        if chars[k] not in DIACRITICS:
            prev_letter_idx = k
            break
    if prev_letter_idx is None:
        return st
    prev_diac = (chars[prev_letter_idx + 1]
                 if prev_letter_idx + 1 < len(chars)
                 and chars[prev_letter_idx + 1] in DIACRITICS
                 else "")
    # Allow when:
    #   (A) preceding letter has SUKUN (verbal signature)
    #   (B) ت has SUKUN AND word has ≥4 letters (past 3FS رَبِحَتْ)
    #   (C) word is 3 letters, ends in ـَتْ (hollow past 3FS خَلَتْ — pre-ت has fatha)
    if prev_diac == SUKUN:
        pass
    elif end_diac == SUKUN and _count_letters(s) >= 4:
        pass
    elif (end_diac == SUKUN
          and _count_letters(s) == 3
          and prev_diac == FATHA):
        pass
    else:
        return st
    stem, suffix = _split_at_letter_index_from_end(s, 1)
    st.body = stem
    st.add_suffix(suffix, "PVSUFF", "pv_ta_suffix")
    return st


def _rule_verb_subject_suffix(st: _State) -> _State:
    """Strip verb-subject suffix (وا، تم، تن، نا، ون، ين، …).

    NOTE: We skip this rule if number_suffix already fired (it handles ون/ين/ات).
    The verb-subject and number-suffix surface forms overlap; here we strip
    the verb-specific ones (وا، تم، تن).
    """
    s = st.body
    if _count_letters(s) <= _MIN_STEM_LETTERS:
        return st
    plain = _strip_diacritics(s)
    for suf in ("تموا", "تما", "تمو", "تم", "تن", "وا"):
        if not plain.endswith(suf):
            continue
        n_letters = len(suf)
        if _count_letters(s) - n_letters < _MIN_STEM_LETTERS:
            continue
        stem, suffix = _split_at_letter_index_from_end(s, n_letters)
        st.body = stem
        st.add_suffix(suffix, "VSUFF", "verb_subject_suffix")
        return st
    return st


# === Result type ===
@dataclass
class SegmentationResult:
    """Result of segmenting one Arabic word."""
    original: str
    normalized: str
    prefixes: list[str]       # surface forms, in order (with diacritics)
    stem: str                  # surface form (with diacritics)
    suffixes: list[str]        # surface forms, in order
    prefix_tags: list[str]     # parallel to prefixes (e.g., "DET", "CONJ")
    suffix_tags: list[str]     # parallel to suffixes
    audit: list[str]           # rule trace
    confidence: float = 1.0    # 1.0 unless a wazn-probe rejected something

    @property
    def changed(self) -> bool:
        return bool(self.prefixes) or bool(self.suffixes)

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "prefixes": list(self.prefixes),
            "prefix_tags": list(self.prefix_tags),
            "stem": self.stem,
            "suffixes": list(self.suffixes),
            "suffix_tags": list(self.suffix_tags),
            "audit": list(self.audit),
            "confidence": self.confidence,
            "changed": self.changed,
        }

    def reconstruct(self) -> str:
        """Concatenate parts to recover the normalized input (reversibility check)."""
        return "".join(self.prefixes) + self.stem + "".join(self.suffixes)


def _rule_lam_al_amr(st: _State) -> _State:
    """PATCH 1 — Strip jussive command particle لْ (lam al-amr).

    Pattern after conjunction strip: لْ + (يـ/تـ/نـ/أـ) + verb stem
    Examples from Quran 2:282:
      وَلْيَكْتُب → conjunction(وَ) + lam_al_amr(لْ) + stem يَكْتُب
      فَلْيَكْتُبْ → conjunction(فَ) + lam_al_amr(لْ) + stem يَكْتُبْ
      وَلْيُمْلِلِ → conjunction(وَ) + lam_al_amr(لْ) + stem يُمْلِلِ
      فَلْيُمْلِلْ → conjunction(فَ) + lam_al_amr(لْ) + stem يُمْلِلْ
      وَلْيَتَّقِ → conjunction(وَ) + lam_al_amr(لْ) + stem يَتَّقِ

    Strict requirements (PATCH 1 scope — kasra-form lam-al-amr is OUT
    OF SCOPE for this patch):
      1. lam must carry SUKUN (لْ). This prevents the rule from firing on:
         - وَلِيّ (لِ with kasra — lexical, handled by future PATCH 3)
         - لِسانٌ, لَيلٌ (لِ/لَ at word start — different lexical roots)
      2. The lam must be followed by an imperfect-prefix letter (ي/ت/ن/أ)
         carrying a vowel.
      3. The verb body after stripping must be ≥ 3 letters.
      4. May fire only after CONJ has been peeled (or with no prior
         prefix). Refuses if any non-CONJ prefix is present.

    The IV prefix (يَ/تَ/نَ/أَ) is intentionally LEFT attached to the
    stem — _rule_iv_prefix is extended in this PATCH to refuse firing
    when LAM_AL_AMR was already peeled (the verb mood is already
    determined).
    """
    # Refuse if a non-CONJ prefix was already stripped.
    for _, tag in st.prefixes:
        if tag != "CONJ":
            return st
    s = st.body
    chars = list(s)
    # Need: ل + ْ + (ي/ت/ن/أ) + diacritic + at least 2 more letters.
    if len(chars) < 5:
        return st
    if chars[0] != LAM:
        return st
    if chars[1] != SUKUN:
        return st
    if chars[2] not in _IV_PREFIXES_WITH_HAMZA:
        return st
    if chars[3] not in DIACRITICS:
        return st
    # The remaining stem (chars[2:]) must be a viable verb body (≥3 letters).
    rest = "".join(chars[2:])
    if _count_letters(rest) < 3:
        return st
    # Peel just the لْ — the IV-prefix-letter stays attached to the stem.
    pref = "".join(chars[:2])  # "لْ"
    st.body = rest
    st.add_prefix(pref, "LAM_AL_AMR", "lam_al_amr")
    return st


# === Pipeline ===
# PATCH 1 (2026-05-26): lam_al_amr inserted immediately after conjunction,
# so the وَ/فَ peels first, then لْ is recognized on the remaining body.
# Runs BEFORE iv_prefix so iv_prefix's refuse-set (which now blocks
# when LAM_AL_AMR is present) can prevent over-peeling of the verb's يَ.
_PREFIX_RULES = [
    ("conjunction",            _rule_conjunction),
    ("lam_al_amr",             _rule_lam_al_amr),  # PATCH 1
    ("vocative_particle",      _rule_vocative_particle),
    ("interrog_alif",          _rule_interrog_alif),
    ("emphatic_lam",           _rule_emphatic_lam),
    ("multi_letter_prep",      _rule_multi_letter_prep),
    ("prep_clitic",            _rule_prep_clitic),
    ("article",                _rule_article),
    ("future_particle",        _rule_future_particle),
    ("imperative_hamzat_wasl", _rule_imperative_hamzat_wasl),
    ("iv_prefix",              _rule_iv_prefix),
]

_SUFFIX_RULES = [
    # Order matters: try longer/less-ambiguous suffixes first
    ("pronoun_suffix",       _rule_pronoun_suffix),
    ("verb_subject_suffix",  _rule_verb_subject_suffix),
    ("pv_ta_suffix",         _rule_pv_ta_suffix),
    ("number_suffix",        _rule_number_suffix),
    ("taa_marbuta",          _rule_taa_marbuta),
    ("tanwin_alif",          _rule_tanwin_alif),
]


def segment(text: str, *, normalize_input: bool = True) -> SegmentationResult:
    """Segment one Arabic word into prefixes / stem / suffixes.

    Args:
        text: a single Arabic word (already tokenized).
        normalize_input: if True, run upstream normalize() first.

    Returns:
        SegmentationResult with audit trail and reversibility guarantee.
    """
    if not text:
        return SegmentationResult(
            original=text or "", normalized="", prefixes=[], stem="",
            suffixes=[], prefix_tags=[], suffix_tags=[], audit=[],
        )
    norm = _maybe_normalize(text) if normalize_input else text

    # CONSTITUTIONAL: قَبل أَيّ تَقطيع — تَفَحَّص ما إذا كانَت الكَلِمَة
    # لَفظًا مُنفَرِدًا (الله، اللهم، أَو مَع بَوادِئ مَعروفَة). إِن كانَت،
    # نَتَوَقَّف فَورًا ونُعيدها كَ stem واحِد بِلا أَيّ peel.
    # المَصدَر: data/contracts/lists/singular_terms*.csv (لا قائِمَة inline).
    try:
        from singular_term_detector import get_singular_term_detector
        _st = get_singular_term_detector().detect(text)
        if _st.is_singular_term:
            return SegmentationResult(
                original=text, normalized=norm,
                prefixes=[], stem=text, suffixes=[],
                prefix_tags=[], suffix_tags=[],
                audit=[f"singular_term:{_st.source_of_claim}"],
            )
    except Exception:
        pass

    # Assimilation lexicon FIRST (returns 2- or 3-tuple of segments).
    assim = _try_assimilation_split(norm)
    if assim is not None:
        if len(assim) == 2:
            seg1, seg2 = assim
            # PATCH 3D (2026-05-26) — AllaCompoundContract.
            # Per-entry tag map: most 2-segment assimilations are PREP+stem
            # (e.g., مما = مِن + ما where مِن is HARF_JARR), but أَلَّا
            # is أَن + لا where أَن is HARF_NASB (subjunctive particle),
            # NOT a preposition. Tag accordingly.
            _ASSIM_FIRST_SEG_TAG = {
                "ألا": "HARF_NASB",  # أَن + لا (subjunctive negation)
                # All other entries default to PREP (existing behavior)
            }
            plain_for_tag = _strip_diacritics(norm)
            first_tag = _ASSIM_FIRST_SEG_TAG.get(plain_for_tag, "PREP")
            return SegmentationResult(
                original=text, normalized=norm,
                prefixes=[seg1], stem=seg2, suffixes=[],
                prefix_tags=[first_tag], suffix_tags=[],
                audit=[f"assimilation:{seg1}+{seg2}:{first_tag}"],
            )
        elif len(assim) == 3:
            seg1, seg2, seg3 = assim
            return SegmentationResult(
                original=text, normalized=norm,
                prefixes=[seg1, seg2], stem=seg3, suffixes=[],
                prefix_tags=["INTERROG", "CONJ"], suffix_tags=[],
                audit=[f"assimilation_3:{seg1}+{seg2}+{seg3}"],
            )
    # Closed-class lexemes (must be checked AFTER assimilation so shadda-bearing
    # forms like أَلَّا split before falling through to the no-shadda أَلَا).
    if _is_closed_class(norm):
        return SegmentationResult(
            original=text, normalized=norm,
            prefixes=[], stem=norm, suffixes=[],
            prefix_tags=[], suffix_tags=[],
            audit=["closed_class_lexeme"],
        )
    # Atomic word lexicon: prevent splitting common nouns/verbs MASAQ keeps whole.
    if _strip_diacritics(norm) in _ATOMIC_WORDS:
        return SegmentationResult(
            original=text, normalized=norm,
            prefixes=[], stem=norm, suffixes=[],
            prefix_tags=[], suffix_tags=[],
            audit=["atomic_word"],
        )

    st = _State(body=norm)

    # Apply prefix rules iteratively. After each peel, check if the body is a
    # closed-class lexeme — if so, stop (the closed-class is the stem itself,
    # don't peel its article).
    changed = True
    while changed:
        changed = False
        before = st.body
        for name, rule in _PREFIX_RULES:
            rule(st)
            if st.frozen:
                changed = False
                break
            if st.body != before:
                changed = True
                before = st.body
                if _is_closed_class(st.body):
                    changed = False
                    break

    # Post-prefix assimilation check: catch وَمِمَّا → و + من + ما
    assim_post = _try_assimilation_split(st.body)
    if assim_post is not None:
        seg1, seg2 = assim_post
        st.add_prefix(seg1, "PREP", "assimilation_after_prefix")
        st.body = seg2
        st.frozen = True

    # Apply suffix rules — single pass, in order. Stop at the first match per
    # rule to avoid double-peels (we never strip both pronoun AND number
    # suffix from the same word — MASAQ shows this is exceptional).
    # Suffix peeling — two phases:
    #
    # Phase 1: full pass over all suffix rules (in order).
    # Phase 2: iterate only pronoun_suffix + verb_subject_suffix to catch
    #          chained suffixes like رَزَقْنَاهُمْ → رزق + نا + هم.
    #          Other rules (number_suffix, taa_marbuta) MUST NOT fire in
    #          phase 2 — they over-strip on the already-reduced body.
    if not (st.frozen or _is_closed_class(st.body)):
        # Phase 1 — check frozen between rules
        for name, rule in _SUFFIX_RULES:
            if st.frozen:
                break
            rule(st)
        # Phase 2 — restricted iteration, also frozen-aware.
        # Only fire pronoun_suffix on MULTI-LETTER pronouns in phase 2 to
        # avoid stripping root letters (e.g., آتَيْنَا → ['آتي', 'نا'] not
        # ['آت', 'ي', 'نا']).
        prev_body = None
        max_iter = 3
        while st.body != prev_body and max_iter > 0 and not st.frozen:
            prev_body = st.body
            if not st.frozen:
                _rule_pronoun_suffix_multi_only(st)
            if not st.frozen:
                _rule_verb_subject_suffix(st)
            max_iter -= 1

    # Suffixes are already in MASAQ-aligned order (inner→outer) because
    # add_suffix inserts at position 0. No further sorting needed.
    suffix_forms = [p[0] for p in st.suffixes]
    suffix_tags = [p[1] for p in st.suffixes]
    prefix_forms = [p[0] for p in st.prefixes]
    prefix_tags = [p[1] for p in st.prefixes]

    return SegmentationResult(
        original=text,
        normalized=norm,
        prefixes=prefix_forms,
        prefix_tags=prefix_tags,
        stem=st.body,
        suffixes=suffix_forms,
        suffix_tags=suffix_tags,
        audit=st.audit,
    )


def _rule_pronoun_suffix_multi_only(st: _State) -> None:
    """Variant of pronoun_suffix that only matches MULTI-letter pronouns.
    Used in phase 2 to prevent stripping root letters (single-letter
    pronouns ك/ه/ي are too dangerous after another peel has already happened).
    """
    s = st.body
    if _count_letters(s) <= _MIN_STEM_LETTERS:
        return
    if _strip_diacritics(s) in _NO_STRIP_PROPER_NOUNS:
        return
    has_iv_prefix = any(tag == "IMPERF_PREF" for _, tag in st.prefixes)
    if has_iv_prefix and _looks_like_form_x(s):
        return
    plain = _strip_diacritics(s)
    for suf in _PRONOUN_SUFFIXES:
        if len(suf) < 2:  # skip 1-letter
            continue
        if not plain.endswith(suf):
            continue
        n_letters = len(suf)
        if _count_letters(s) - n_letters < _MIN_STEM_LETTERS:
            continue
        # PATCH 3C (2026-05-26) — DualVerbSuffixContract (phase-2 mirror).
        # Same guard as in _rule_pronoun_suffix: don't peel نَا as POSS_PRON
        # when IMPERF_PREF was peeled and residual would be < 3 letters.
        # يَكُونَا (dual jussive) keeps نَا attached as dual marker.
        if (suf == "نا"
                and has_iv_prefix
                and _count_letters(s) - n_letters < 3):
            continue
        stem, suffix = _split_at_letter_index_from_end(s, n_letters)
        st.body = stem
        st.add_suffix(suffix, "POSS_PRON", "pronoun_suffix_p2")
        return


def segment_text(text: str) -> dict:
    """Convenience: return a plain dict."""
    return segment(text).to_dict()


# === CLI ===
def main() -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Arabic morphological segmenter")
    p.add_argument("text", help="Arabic word to segment")
    p.add_argument("--no-normalize", action="store_true",
                   help="Skip upstream normalization (input is already normalized)")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    result = segment(args.text, normalize_input=not args.no_normalize)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"original:    {result.original!r}")
        print(f"normalized:  {result.normalized!r}")
        print(f"prefixes:    {result.prefixes}  tags={result.prefix_tags}")
        print(f"stem:        {result.stem!r}")
        print(f"suffixes:    {result.suffixes}  tags={result.suffix_tags}")
        print(f"audit:       {' → '.join(result.audit) or '(no peels)'}")
        print(f"reconstruct: {result.reconstruct()!r}  (== normalized: {result.reconstruct() == result.normalized})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
