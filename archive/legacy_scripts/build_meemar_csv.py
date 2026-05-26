"""Build MEEMAR.csv — our own version of MASAQ.csv structure.

Approach:
  - Read MASAQ.csv to get every unique word occurrence (Sura, Verse, Word_No, Word)
  - Run our segmenter on each word to produce segments
  - Run wazn_matcher on the stem to extract root + wazn + confidence
  - Write one row per segment with anchors + our analysis + agreement flag

Schema follows MASAQ's 18 columns + our additions:
  - Tier 1 (filled):  ID, Sura_No, Verse_No, Word_No, Segment_No,
                       Word, Without_Diacritics, Segmented_Word
  - Tier 1.5 (ours):  Our_Root, Our_Wazn, Our_Confidence, Source_Of_Claim,
                       Alternatives, Agreement_With_MASAQ
  - Tier 2 (empty for now): Morph_Tag, Morph_Type, Case_Mood,
                              Case_Mood_Marker, Invariable_Declinable
  - Tier 3 (empty for now): Syntactic_Role, Possessive_Construct,
                              Phrase, Phrasal_Function, Punctuation_Mark

Usage:
  python3 scripts/build_meemar_csv.py              # all Quran
  python3 scripts/build_meemar_csv.py --sura 1     # just Sura 1
  python3 scripts/build_meemar_csv.py --sura 1 --sura 2  # Suras 1+2
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "clean_code"
sys.path.insert(0, str(CLEAN))

import segmenter as _segmenter  # noqa: E402
from wazn_matcher_v3 import AnalyzerV3  # noqa: E402

MASAQ_PATH = ROOT / "data" / "MASAQ.csv"
OUT_PATH = ROOT / "data" / "MEEMAR.csv"

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# All MEEMAR.csv columns in order — Tier 2 headers are bilingual English/Arabic
MEEMAR_COLUMNS = [
    # Anchors (T1)
    "ID", "Sura_No", "Verse_No", "Word_No", "Segment_No",
    "Word", "Without_Diacritics",
    # Segmentation (T1)
    "Segmented_Word",
    # Our additions (T1.5)
    "Our_Root", "Our_Wazn", "Our_Confidence",
    "Source_Of_Claim", "Alternatives", "Agreement_With_MASAQ",
    # Tier 2 — bilingual headers (English / Arabic)
    "Morph_Tag",
    "Morph_Type / النوع_الموضعي",
    "Case_Mood / الحالة_الإعرابية",
    "Case_Mood_Marker / علامة_الإعراب",
    "Invariable_Declinable / مبني_معرب",
    # Tier 3 — Arabic-only headers (filled by future M1 work)
    "الوظيفة_النحوية",
    "الإضافة",
    "الجملة",
    "وظيفة_الجملة",
    # Misc
    "Punctuation_Mark",
]


# ============================================================================
# Tier 2 — derivation logic
# ============================================================================

# Closed-class invariables — Arabic-script lookup (plain, no diacritics)
INVARIABLE_PRONOUNS_DISJ = {
    "أنا", "نحن", "أنت", "أنتما", "أنتم", "أنتن",
    "هو", "هي", "هما", "هم", "هن",
    "إياي", "إيانا", "إياك", "إياكم", "إياكن", "إياه", "إياها", "إياهما",
    "إياهم", "إياهن",
}
INVARIABLE_PRONOUNS_JONT = {"ي", "نا", "ك", "كم", "كن", "كما", "ه", "ها", "هما", "هم", "هن"}
DEMONSTRATIVES = {
    "هذا", "هذه", "هذان", "هذين", "هاتان", "هاتين",
    "هؤلاء", "ذلك", "تلك", "ذانك", "تانك", "أولئك",
    "هنا", "هناك", "هنالك", "ثم", "ثمة",
}
RELATIVE_NOUNS = {
    "الذي", "التي", "اللذان", "اللذين", "اللتان", "اللتين",
    "الذين", "اللاتي", "اللائي", "اللواتي",
    "من", "ما", "أي",
}
CONDITIONAL_NOUNS = {
    "من", "ما", "متى", "أين", "أينما", "حيثما", "كيفما",
    "إذا", "إذما", "أنى", "كلما",
}
INTERROGATIVE_NOUNS = {
    "من", "ما", "ماذا", "متى", "أين", "كيف", "كم", "أي", "أيان", "أنى", "لم", "لماذا",
}

# حروف النفي المبنية
NEGATION_PARTICLES = {"لا", "ما", "لم", "لن", "ليس"}
EXCEPTION_PARTICLES = {"إلا", "خلا", "حاشا", "عدا"}  # غير/سوى are nouns, not particles
EMPHATIC_PARTICLES = {"إن", "أن", "لكن", "كأن", "ليت", "لعل"}
ANSWER_PARTICLES = {"نعم", "بلى", "لا", "كلا", "أجل", "إي"}
ADVERB_PARTICLES = {"حيث", "هنا", "هناك", "ثم", "قبل", "بعد", "فوق", "تحت",
                     "أمام", "خلف", "يمين", "يسار", "وراء"}


def strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def derive_morph_type(is_stem: bool, segment_index: int,
                       num_prefixes: int, num_suffixes: int, total: int) -> str:
    """Returns Morph_Type / النوع_الموضعي bilingual value."""
    if is_stem:
        return "Stem / جذع"
    if segment_index <= num_prefixes:
        return "Prefix / سابقة"
    # else it's a suffix
    return "Suffix / لاحقة"


# Diacritic → marker name
HARAKAH_MAP = {
    "ُ": "ضمة",
    "َ": "فتحة",
    "ِ": "كسرة",
    "ْ": "سكون",
    "ٌ": "ضمتان",
    "ً": "فتحتان",
    "ٍ": "كسرتان",
    "ّ": "شدة",
}

# Mood → bilingual Case_Mood value
MOOD_MAP = {
    "ضمة": "NOMINATIVE / رفع",
    "ضمتان": "NOMINATIVE / رفع",
    "فتحة": "ACCUSATIVE / نصب",
    "فتحتان": "ACCUSATIVE / نصب",
    "كسرة": "GENITIVE / جر",
    "كسرتان": "GENITIVE / جر",
    "سكون": "JUSSIVE / جزم",
    # Sound masculine plural / dual markers (context: noun)
    "واو_جماعة": "NOMINATIVE / رفع",      # جمع مذكر سالم — رفع
    "ياء_جماعة": "GENITIVE / جر",         # جمع مذكر سالم — جر/نصب (default جر)
    "ألف_تثنية": "NOMINATIVE / رفع",      # مثنى — رفع
}

# Honorific terminology for the Divine Name (لفظ الجلالة)
# Convention: لفظ الجلالة uses "في محل X" instead of standard inflection terms.
JALALAH_VARIANTS = {"الله", "اللَّهُ", "اللَّهِ", "اللَّهَ", "للَّهِ", "لِلَّهِ",
                     "لله", "بالله", "بِاللَّهِ", "والله", "وَاللَّهِ", "تالله",
                     "تَاللَّهِ", "اللهمّ", "اللَّهُمَّ"}

# ============================================================================
# الأدوات (particles) — لا جذر لها، لأنها closed-class function words.
# الـ wazn_matcher يفترض أن لكل كلمة جذراً، فيُجبر تخمين خاطئ (مثل إنّ → ءنن).
# لكل كلمة هنا، نضع جذراً "—" و wazn "حرف" مع توضيح النوع.
# ============================================================================
PARTICLES_NO_ROOT = {
    # حروف الجر
    "في": "حرف جر", "على": "حرف جر", "إلى": "حرف جر", "من": "حرف جر",
    "عن": "حرف جر", "ب": "حرف جر", "بِ": "حرف جر", "ل": "حرف جر", "لِ": "حرف جر",
    "ك": "حرف جر", "كَ": "حرف جر", "حتى": "حرف جر",
    "عند": "ظرف مكان", "عندي": "ظرف مكان", "عندك": "ظرف مكان",
    "خلال": "ظرف", "عبر": "ظرف", "مع": "ظرف",
    "فوق": "ظرف مكان", "تحت": "ظرف مكان",
    "أمام": "ظرف مكان", "خلف": "ظرف مكان", "وراء": "ظرف مكان",
    # حروف العطف
    "و": "حرف عطف", "وَ": "حرف عطف",
    "ف": "حرف عطف", "فَ": "حرف عطف",
    "ثم": "حرف عطف", "أو": "حرف عطف", "بل": "حرف إضراب",
    "أم": "حرف عطف", "لكن": "حرف استدراك",
    # حروف النفي
    "لا": "حرف نفي", "ما": "حرف نفي", "لم": "حرف نفي/جزم", "لن": "حرف نفي/نصب",
    "لما": "حرف نفي/جزم", "ليس": "فعل ناقص",
    # حروف الاستفهام
    "هل": "حرف استفهام", "أ": "حرف استفهام",
    # حروف التوكيد والنواسخ
    "إن": "حرف توكيد", "أن": "حرف توكيد/مصدري",
    "إنّ": "حرف توكيد", "أنّ": "حرف توكيد",
    "كأن": "حرف تشبيه", "كأنّ": "حرف تشبيه",
    "ليت": "حرف تمنّي", "لعل": "حرف ترجّي", "لعلّ": "حرف ترجّي",
    "إنما": "حرف حصر",
    # حروف الاستثناء (الأدوات منها)
    "إلا": "حرف استثناء", "إلّا": "حرف استثناء",
    # حروف الجواب
    "نعم": "حرف جواب", "بلى": "حرف جواب", "كلا": "حرف ردع",
    "أجل": "حرف جواب", "إي": "حرف جواب",
    # حروف التحضيض
    "ألا": "حرف تحضيض", "لولا": "حرف تحضيض/شرط", "هلا": "حرف تحضيض",
    # حروف المصدر
    "كي": "حرف مصدري", "لو": "حرف شرط",
    # حروف التنبيه
    "ها": "حرف تنبيه", "أما": "حرف تفصيل",
    # حروف النداء
    "يا": "حرف نداء", "أيا": "حرف نداء", "هيا": "حرف نداء",
    # حروف الاستقبال
    "قد": "حرف تحقيق", "لقد": "حرف توكيد",
    "س": "حرف استقبال", "سَ": "حرف استقبال", "سوف": "حرف استقبال",
    # ظروف الزمان والمكان (بعضها مبني)
    "إذ": "ظرف زمان", "إذا": "ظرف/شرط",
    "حين": "ظرف زمان", "وقت": "ظرف زمان",
    "قبل": "ظرف زمان", "بعد": "ظرف زمان",
    "ثَمَّ": "ظرف مكان", "هنا": "ظرف مكان", "هناك": "ظرف مكان",
    # أدوات الشرط الجازمة
    "متى": "اسم شرط", "أين": "اسم شرط", "أينما": "اسم شرط",
    "حيثما": "اسم شرط", "كيفما": "اسم شرط", "أنى": "اسم شرط",
    "كلما": "اسم شرط", "إذما": "اسم شرط",
    # ذوات الإشارة والموصول والأسماء المبنية (closed-class بدون جذر)
    "هذا": "اسم إشارة", "هذه": "اسم إشارة", "ذلك": "اسم إشارة",
    "تلك": "اسم إشارة", "أولئك": "اسم إشارة",
    "هذان": "اسم إشارة", "هاتان": "اسم إشارة",
    "الذي": "اسم موصول", "التي": "اسم موصول",
    "الذين": "اسم موصول", "اللاتي": "اسم موصول", "اللائي": "اسم موصول",
    "اللواتي": "اسم موصول",
    # الضمائر المنفصلة
    "أنا": "ضمير منفصل", "نحن": "ضمير منفصل",
    "أنت": "ضمير منفصل", "أنتما": "ضمير منفصل", "أنتم": "ضمير منفصل", "أنتن": "ضمير منفصل",
    "هو": "ضمير منفصل", "هي": "ضمير منفصل", "هما": "ضمير منفصل",
    "هم": "ضمير منفصل", "هن": "ضمير منفصل",
    "إياي": "ضمير نصب", "إيانا": "ضمير نصب", "إياك": "ضمير نصب",
    "إياكم": "ضمير نصب", "إياكن": "ضمير نصب",
    "إياه": "ضمير نصب", "إياها": "ضمير نصب", "إياهم": "ضمير نصب", "إياهن": "ضمير نصب",
    # ضمائر متصلة في موضع stem (بعد تقطيع segmenter)
    "ه": "ضمير متصل", "ها": "ضمير متصل", "هم": "ضمير متصل", "هن": "ضمير متصل",
    "ك": "ضمير متصل", "كم": "ضمير متصل", "كن": "ضمير متصل", "كما": "ضمير متصل", "نا": "ضمير متصل",
}


# === Known-root overrides for closed-class lexemes ===
# When wazn_matcher returns multiple candidates with tied confidence, it
# picks alphabetically/first. For words whose root is well-established but
# non-obvious from the surface, override with the linguistically-correct root.
# Format: {word_plain (no diacritics): (correct_root, reason)}
# Reason is logged in Source_Of_Claim for audit/reversibility.
KNOWN_ROOTS = {
    # The five "أسماء خمسة" + اسم/يد etc. — their letter sequence is reduced
    "اسم":   ("سمو", "اسم: root=سمو (plural أسماء, verb سمَّى)"),
    "أسماء": ("سمو", "أسماء: plural of اسم"),
    "اسمه":  ("سمو", "اسم + هـ"),
    "اسمها": ("سمو", "اسم + ها"),
    "اسمي":  ("سمو", "اسم + ي"),
    "أسمائكم": ("سمو", "جمع اسم + كم"),
    "أسماؤهم": ("سمو", "جمع اسم + هم"),
    "أخ":    ("اخو", "أخ: root=اخو (dual أخوان, plural إخوة)"),
    "أخت":   ("اخو", "أخت: feminine of أخ"),
    "أب":    ("ابو", "أب: root=ابو (dual أبوان)"),
    "أبو":   ("ابو", "أبو: nominative case form"),
    "أبا":   ("ابو", "أبا: accusative case form"),
    "أبي":   ("ابو", "أبي: genitive case form"),
    "ابن":   ("بنو", "ابن: root=بنو (plural بنون/أبناء)"),
    "بن":    ("بنو", "بن: clitic form"),
    "بنو":   ("بنو", "بنو: plural"),
    "بنون":  ("بنو", "بنون: plural masculine"),
    "أبناء": ("بنو", "أبناء: plural"),
    "بنت":   ("بنو", "بنت: feminine of ابن"),
    "بنات":  ("بنو", "بنات: feminine plural"),
    "أم":    ("امم", "أم: root=امم (verb أمّ يؤمّ)"),
    "أمه":   ("امم", "أمه: أم + هـ"),
    "أمها":  ("امم", "أمها: أم + ها"),
    "أمهات": ("امم", "أمهات: feminine plural"),
    "يد":    ("يدي", "يد: root=يدي"),
    "يدي":   ("يدي", "يدي: dual yad"),
    "يداه":  ("يدي", "يداه: يد + dual + هـ"),
    "أيدي":  ("يدي", "أيدي: plural"),
    "أيديكم": ("يدي", "أيدي + كم"),
    "أيديهم": ("يدي", "أيدي + هم"),
    "دم":    ("دمو", "دم: root=دمو"),
    "دماء":  ("دمو", "دماء: plural"),
    "فم":    ("فمو", "فم: root=فمو"),
    "أفواه": ("فمو", "أفواه: plural"),
    "ذو":    ("ذوو", "ذو: nominative"),
    "ذا":    ("ذوو", "ذا: accusative"),
    "ذي":    ("ذوو", "ذي: genitive"),
    "ذوي":   ("ذوو", "ذوي: plural"),
    "ذوو":   ("ذوو", "ذوو: plural"),
    "ذواتا": ("ذوو", "ذواتا: feminine dual"),
}
JALALAH_CASE = {
    "NOMINATIVE / رفع": "لفظ الجلالة في محل رفع",
    "GENITIVE / جر":   "لفظ الجلالة في محل جر",
    "ACCUSATIVE / نصب": "لفظ الجلالة في محل نصب",
}


def derive_case_marker(segment_diac: str, is_last: bool,
                       is_stem_or_after: bool,
                       segment_tag: str = "",
                       prefix_tags: list = None) -> str:
    """Extract Arabic case marker from final diacritic of the segment.
    Only meaningful for the LAST segment of a word (the case ending).

    Handles:
      - Standard harakah (ضمة/فتحة/كسرة/سكون)
      - Tanwin (ضمتان/فتحتان/كسرتان)
      - Sound masculine plural / dual markers (ون/ين/ان) via NSUFF tag
    """
    if not is_last or not is_stem_or_after:
        return ""
    prefix_tags = prefix_tags or []
    plain = strip_diac(segment_diac)

    # Sound masculine plural / dual: when the SEGMENT itself is the suffix
    # ون/ين/ان (NSUFF tag means it's a noun-suffix, not verb-stem ending).
    if segment_tag == "NSUFF":
        if plain in ("ون", "ين", "ان"):
            if plain == "ون":
                return "واو_جماعة"
            if plain == "ين":
                return "ياء_جماعة"
            if plain == "ان":
                return "ألف_تثنية"

    # Walk from end, pick last harakah character
    for c in reversed(segment_diac):
        if c in HARAKAH_MAP:
            return HARAKAH_MAP[c]
        if c.isspace():
            continue
        if 0x0600 <= ord(c) <= 0x06FF:
            # Special cases: ends with ا or ى → ألف (often مبني or منصوب منوي)
            if c in ("ا", "ى"):
                return "ألف"
            if c == "و":
                return "واو"
            if c == "ي":
                return "ياء"
            if c == "ن":
                return "نون"
            return ""
    return ""


def derive_case_mood(case_marker: str, segment_plain: str,
                     is_invariable: bool,
                     word_plain: str = "") -> str:
    """Derive Case_Mood from case marker.

    Special-case: لفظ الجلالة (the Divine Name) uses honorific terminology
    "لفظ الجلالة في محل X" instead of standard "مجرور/مرفوع/منصوب".
    Checks the FULL WORD (not the stem segment) since الله is often split
    as ال + له after prefix stripping.
    """
    if is_invariable:
        return "INVARIABLE / مبني"
    standard = MOOD_MAP.get(case_marker, "")
    # Honorific override for Divine Name (check full word)
    if word_plain in JALALAH_VARIANTS and standard in JALALAH_CASE:
        return JALALAH_CASE[standard]
    return standard


# Mabni verb stems (closed-class): past tense and imperative are مبني
# We detect this from segmenter tag context, not by string matching
def derive_invariable_extended(segment_plain: str, segment_tag: str,
                                is_stem: bool, prefix_tags: list,
                                suffix_tags: list, full_segs: list) -> str:
    """Extended version that detects mabni verbs and single-particle words."""
    # If stem with NO IMPERF_PREF in prefix_tags AND has a PVSUFF or
    # VSUFF in suffix_tags → past/imperative verb stem → MABNI
    if is_stem:
        has_imperf_pref = "IMPERF_PREF" in prefix_tags
        has_pv_suff = "PVSUFF" in suffix_tags  # past tense suffix (ت, نا, تم, etc.)
        if has_pv_suff:
            return "INVAR / مبني_فعل_ماض"
        # Imperative: no IMPERF_PREF, no PVSUFF, but the word starts with hamzat
        # wasl OR has IMPERF_PREF stripped? Heuristic: if the original word
        # has form "اXXX" (hamzat wasl + 3-letter) without imperf prefix.
        # Simpler: if segment_plain starts with ا and length 3-5 and no IV pref
        # — this is a heuristic for imperative
        if (not has_imperf_pref and not has_pv_suff
            and segment_plain.startswith("ا")
            and 3 <= len(segment_plain) <= 6
            and segment_tag == "STEM"):
            # Likely imperative (اضرب, اقرأ, اهدي)
            return "INVAR / مبني_فعل_أمر"

    # Fallback to default
    return derive_invariable(segment_plain, segment_tag, is_stem)


def derive_invariable(segment_plain: str, segment_tag: str,
                       is_stem: bool) -> str:
    """Returns Invariable_Declinable / مبني_معرب bilingual value.
    Most prefixes/suffixes are مبني; stems depend on closed-class lookup.
    """
    # Tag-based determination first
    if segment_tag == "DET":
        return "DEF_ART / أداة_تعريف"
    if segment_tag in ("POSS_PRON", "VSUFF", "PVSUFF") or segment_tag.startswith("POSS"):
        return "JONT_PRON / ضمير_متصل"
    if segment_tag in ("CONJ", "PREP", "INTERROG", "VOC_PART", "FUT_PART",
                        "EMPHATIC", "HAMZAT_WASL", "IMPERF_PREF"):
        return "INVAR / مبني"
    if segment_tag in ("NSUFF", "NSUFF_FEM_SG"):
        # Noun suffixes are case markers — usually declinable indicators
        return "DECLN / معرب"
    # Stem — check closed-class
    if is_stem:
        if segment_plain in INVARIABLE_PRONOUNS_DISJ:
            return "DISJ_PRON / ضمير_منفصل"
        if segment_plain in DEMONSTRATIVES:
            return "DEM_NOUN / اسم_إشارة"
        if segment_plain in RELATIVE_NOUNS:
            return "REL_PRON / اسم_موصول"
        if segment_plain in CONDITIONAL_NOUNS:
            return "COND_NOUN / اسم_شرط"
        if segment_plain in INTERROGATIVE_NOUNS:
            return "INTROG_NOUN / اسم_استفهام"
        # حروف مبنية
        if segment_plain in NEGATION_PARTICLES:
            return "INVAR / حرف_نفي"
        if segment_plain in EXCEPTION_PARTICLES:
            return "INVAR / حرف_استثناء"
        if segment_plain in EMPHATIC_PARTICLES:
            return "INVAR / حرف_توكيد"
        if segment_plain in ANSWER_PARTICLES:
            return "INVAR / حرف_جواب"
        if segment_plain in ADVERB_PARTICLES:
            return "INVAR / ظرف_مبني"
        return "DECLN / معرب"
    return "INVAR / مبني"


def build_word_index(masaq_rows):
    """Group MASAQ rows by (Sura, Verse, Word_No) preserving row order."""
    by_word = defaultdict(list)
    for row in masaq_rows:
        key = (row["Sura_No"], row["Verse_No"], row["Word_No"])
        by_word[key].append(row)
    return by_word


def normalize_seg_for_compare(s: str) -> str:
    """Permissive normalize for agreement check."""
    out = strip_diacritics(s or "")
    out = out.replace("ى", "ي").replace("ة", "ت").replace("ٱ", "ا")
    for h in ("أ", "إ", "ؤ", "ئ"):
        out = out.replace(h, "ء")
    return out


def compute_agreement(our_segs, masaq_rows):
    """Return 'Full' / 'Partial' / 'None' agreement with MASAQ.

    Compares our segment list (in surface order) against MASAQ's segments
    (already in physical row order — no sort on Segment_No).
    """
    masaq_segs = [r["Segmented_Word"] for r in masaq_rows
                  if r["Segmented_Word"] and r["Segmented_Word"] not in ("None", "(null)")]
    our_clean = [normalize_seg_for_compare(s) for s in our_segs if s]
    masaq_clean = [normalize_seg_for_compare(s) for s in masaq_segs]
    if our_clean == masaq_clean:
        return "Full"
    if sorted(our_clean) == sorted(masaq_clean):
        return "SetMatch"
    # any overlap?
    if set(our_clean) & set(masaq_clean):
        return "Partial"
    return "None"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sura", type=int, action="append",
                    help="Limit to specific sura(s); repeatable. Default: all 114.")
    ap.add_argument("--out", default=str(OUT_PATH),
                    help="Output CSV path")
    args = ap.parse_args(argv)

    suras_filter = set(str(s) for s in (args.sura or []))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not MASAQ_PATH.is_file():
        print(f"MASAQ.csv not found at {MASAQ_PATH}")
        return 1

    print(f"Loading MASAQ from {MASAQ_PATH} ...")
    with open(MASAQ_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} MASAQ rows.")

    # Filter by sura if requested
    if suras_filter:
        rows = [r for r in rows if r["Sura_No"] in suras_filter]
        print(f"Filtered to {len(rows)} rows in suras {sorted(suras_filter, key=int)}")

    word_index = build_word_index(rows)
    print(f"Indexed {len(word_index)} word occurrences.")

    print("Initializing wazn_matcher_v3 (extractor + verifier) ...")
    analyzer = AnalyzerV3()

    out_rows = []
    row_id = 0
    t0 = time.time()
    n_full = n_partial = n_none = n_setmatch = 0

    for i, (wid, masaq_rows_for_word) in enumerate(word_index.items()):
        sura, verse, word_no = wid
        word = masaq_rows_for_word[0]["Word"]
        if not word:
            continue
        word_plain = strip_diacritics(word)

        # Run our segmenter
        try:
            seg_result = _segmenter.segment(word)
        except Exception as e:
            print(f"  segmenter failed on {word!r}: {e}")
            continue

        our_segs = list(seg_result.prefixes) + [seg_result.stem] + list(seg_result.suffixes)
        our_tags = (list(seg_result.prefix_tags) + ["STEM"]
                    + list(seg_result.suffix_tags))

        # Run wazn_matcher_v3 on stem (extractor + verifier)
        try:
            wazn_results = analyzer.analyze(seg_result.stem) or []
        except Exception:
            wazn_results = []

        # v3 returns V3Match objects with .wazn_plain → .wazn, plus more fields
        # Wrap for backwards compatibility with downstream code
        top = wazn_results[0] if wazn_results else None
        if top is not None:
            # V3Match has .wazn (not .wazn_plain). Alias for compatibility.
            from types import SimpleNamespace
            top = SimpleNamespace(
                root=top.root,
                wazn_plain=top.wazn,
                confidence=top.confidence,
                source=top.source_of_claim,
            )

        # === Particle override (الأدوات لا جذر لها) ===
        # If the word OR the stem is a particle (closed-class function word),
        # set root="—" and wazn="حرف" — particles have no derivational root.
        known_root_reason = ""
        stem_plain = strip_diac(seg_result.stem)
        is_particle = False
        particle_type = ""
        if word_plain in PARTICLES_NO_ROOT:
            is_particle = True
            particle_type = PARTICLES_NO_ROOT[word_plain]
        elif stem_plain in PARTICLES_NO_ROOT:
            is_particle = True
            particle_type = PARTICLES_NO_ROOT[stem_plain]

        if is_particle:
            from types import SimpleNamespace
            top = SimpleNamespace(
                root="—",
                wazn_plain=particle_type,
                confidence=1.0,
            )
            known_root_reason = f"particle_override:{particle_type}"
        elif word_plain in JALALAH_VARIANTS:
            # Divine name — assign canonical root ءله per project convention
            from types import SimpleNamespace
            top = SimpleNamespace(
                root="ءله",
                wazn_plain="لفظ الجلالة",
                confidence=1.0,
            )
            known_root_reason = "jalalah_override:divine_name"
        else:
            # === Known-root override (closed-class lexemes with stable roots) ===
            override_key = None
            if word_plain in KNOWN_ROOTS:
                override_key = word_plain
            elif stem_plain in KNOWN_ROOTS:
                override_key = stem_plain
            if override_key is not None:
                correct_root, reason = KNOWN_ROOTS[override_key]
                override = next((w for w in wazn_results if w.root == correct_root), None)
                if override is not None:
                    # v3 uses .wazn not .wazn_plain — alias for compatibility
                    from types import SimpleNamespace
                    top = SimpleNamespace(
                        root=override.root,
                        wazn_plain=getattr(override, 'wazn', None) or getattr(override, 'wazn_plain', ''),
                        confidence=override.confidence,
                    )
                    known_root_reason = reason
                else:
                    from types import SimpleNamespace
                    first_wazn = ""
                    if wazn_results:
                        first_wazn = (getattr(wazn_results[0], 'wazn', None) or
                                       getattr(wazn_results[0], 'wazn_plain', ''))
                    top = SimpleNamespace(
                        root=correct_root,
                        wazn_plain=first_wazn,
                        confidence=1.0,
                    )
                    known_root_reason = reason + " [forced override]"

        alternatives = []
        for w in wazn_results[1:4]:  # top 3 alternatives
            wz = getattr(w, 'wazn', None) or getattr(w, 'wazn_plain', '')
            alternatives.append(f"{w.root}/{wz}@{w.confidence:.2f}")
        alt_str = " ; ".join(alternatives) if alternatives else ""

        agreement = compute_agreement(our_segs, masaq_rows_for_word)
        if agreement == "Full":
            n_full += 1
        elif agreement == "SetMatch":
            n_setmatch += 1
        elif agreement == "Partial":
            n_partial += 1
        else:
            n_none += 1

        # Write one row per segment
        num_prefixes = len(seg_result.prefixes)
        num_suffixes = len(seg_result.suffixes)
        total_segs = len(our_segs)
        for seg_idx, (seg, tag) in enumerate(zip(our_segs, our_tags), start=1):
            row_id += 1
            is_stem = (tag == "STEM")
            is_last = (seg_idx == total_segs)
            seg_plain = strip_diac(seg)

            # === Tier 2 derivations ===
            morph_type = derive_morph_type(
                is_stem, seg_idx, num_prefixes, num_suffixes, total_segs)
            case_marker = derive_case_marker(
                seg, is_last, is_stem_or_after=(seg_idx > num_prefixes),
                segment_tag=tag,
                prefix_tags=list(seg_result.prefix_tags))
            inv_decln = derive_invariable_extended(
                seg_plain, tag, is_stem,
                list(seg_result.prefix_tags),
                list(seg_result.suffix_tags),
                our_segs)
            is_invariable = inv_decln.startswith("INVAR") or inv_decln.startswith("DEM_") \
                or inv_decln.startswith("REL_") or inv_decln.startswith("COND_") \
                or inv_decln.startswith("INTROG") or inv_decln.startswith("DISJ_") \
                or inv_decln.startswith("JONT_") or inv_decln.startswith("DEF_ART")
            case_mood = derive_case_mood(case_marker, seg_plain, is_invariable,
                                         word_plain=word_plain)

            row = {
                "ID": row_id,
                "Sura_No": sura,
                "Verse_No": verse,
                "Word_No": word_no,
                "Segment_No": seg_idx,
                "Word": word,
                "Without_Diacritics": word_plain,
                "Segmented_Word": seg,
                "Our_Root": top.root if (is_stem and top) else "",
                "Our_Wazn": top.wazn_plain if (is_stem and top) else "",
                "Our_Confidence": f"{top.confidence:.3f}" if (is_stem and top) else "",
                "Source_Of_Claim": (
                    (getattr(top, 'source', '') + " | " if top and getattr(top, 'source', '') else "") +
                    (";".join(seg_result.audit[:3])
                     if seg_result.audit else "rule:default")
                ) if is_stem else
                (";".join(seg_result.audit[:3]) if seg_result.audit else "rule:default"),
                "Alternatives": alt_str if is_stem else "",
                "Agreement_With_MASAQ": agreement,
                "Morph_Tag": tag,
                "Morph_Type / النوع_الموضعي": morph_type,
                "Case_Mood / الحالة_الإعرابية": case_mood,
                "Case_Mood_Marker / علامة_الإعراب": case_marker,
                "Invariable_Declinable / مبني_معرب": inv_decln,
                "الوظيفة_النحوية": "",
                "الإضافة": "",
                "الجملة": "",
                "وظيفة_الجملة": "",
                "Punctuation_Mark": "",
            }
            out_rows.append(row)

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(word_index) - (i + 1)) / rate
            print(f"  ... {i+1}/{len(word_index)} words processed "
                  f"({rate:.0f}/s, ETA {eta:.0f}s)")

    # Write CSV
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MEEMAR_COLUMNS)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    total = n_full + n_setmatch + n_partial + n_none
    elapsed = time.time() - t0
    print()
    print("=== MEEMAR.csv build summary ===")
    print(f"  Words processed:        {total}")
    print(f"  Rows written:           {len(out_rows)}")
    print(f"  Time elapsed:           {elapsed:.1f}s")
    print()
    print(f"  Agreement with MASAQ:")
    print(f"    Full match:           {n_full}  ({100*n_full/total:.1f}%)")
    print(f"    Set match (reorder):  {n_setmatch}  ({100*n_setmatch/total:.1f}%)")
    print(f"    Partial overlap:      {n_partial}  ({100*n_partial/total:.1f}%)")
    print(f"    No overlap:           {n_none}  ({100*n_none/total:.1f}%)")
    print()
    print(f"Output: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
