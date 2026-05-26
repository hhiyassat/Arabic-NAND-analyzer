"""wazn_data.py — Data loaders for root-by-alignment extraction.

CONSTITUTIONAL: this module does NOT define data constants. Instead it LOADS
from canonical sources:

  Awzan:            salehan/Salehan19-6-67/data/awzan_cleaned.csv
                    (EXTRA wazns like فَعَّ, مُفْتَعِل, etc. are appended here)

  Closed-class:     new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl
                    + new_arabic_analyzer/data/quran/i3rab_ref/i3rab_operators.csv

  Diacritics/Hamza: clean_code/normalizer.py (the canonical normalizer)

  Clitics:          Hardcoded here BECAUSE there's no canonical source file
                    for them yet. (TODO: extract to data file.)

  NO_ROOT_LABELS:   Hardcoded mapping rules (which i3rab labels imply no-root).
                    These are LOGIC, not data — they define how to interpret
                    labels from the source.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Import character constants from the canonical normalizer (no duplicates)
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from normalizer import DIACRITICS, SHADDA, SUKUN, DAGGER_ALIF, ALIF_WASLA

# ROOT placeholder letters (wazn-specific — they don't belong in normalizer)
ROOT_PLACEHOLDERS = {"ف", "ع", "ل"}

# Hamza variants — used for letter-class matching during alignment.
# These belong here because alignment's matching semantics is wazn-specific.
HAMZA_VARIANTS = {"ء", "أ", "إ", "ؤ", "ئ", "آ", "ٱ", "ا"}


# ============================================================================
# Awzan loader — from canonical salehan/awzan_cleaned.csv
# ============================================================================

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # …/<package>/
_AWZAN_PATHS = [
    # 1) Bundled (shipping) location
    _PACKAGE_ROOT / "data" / "awzan_cleaned.csv",
    # 2) Dev locations
    Path("/Users/husseinhiyassat/fractal/salehan/Salehan19-6-67/data/awzan_cleaned.csv"),
    Path("/sessions/nice-epic-cannon/mnt/salehan/Salehan19-6-67/data/awzan_cleaned.csv"),
]


def load_awzan() -> list[str]:
    """Load all awzan from the canonical salehan file.

    Returns unique list. The salehan file is the single source of truth —
    if you want to add a wazn, add it THERE, not in code.
    """
    awzan = set()
    for p in _AWZAN_PATHS:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                wz = row.get("الوزن", "").strip()
                if wz:
                    awzan.add(wz)
        break
    return list(awzan)


# ============================================================================
# Awzan that look like data errors / non-standard — exclude from matching
# ============================================================================

BLACKLIST_AWZAN = {
    "فَفُعِل", "فَفُعَل", "فَفُعْل",  # double ف (typo)
}


# ============================================================================
# Clitics — TODO: extract to data file. For now, hardcoded.
# ============================================================================

KNOWN_PREFIX_LETTERS = {
    # Single particles
    "و", "ف", "ب", "ك", "ل", "س",
    # 2-letter combos
    "وا", "فا", "با", "كا", "لا", "وب", "ول", "فب", "فل",
    "ال", "ول", "فل", "بل", "كل",
    # 3-letter prefix + def-article
    "وال", "فال", "بال", "كال", "ولل", "فلل", "وأل", "فأل",
    # Future particles
    "وس", "فس",
}

KNOWN_SUFFIX_LETTERS = {
    # Singletons
    "ه", "ها", "هم", "هن", "هما", "ك", "كم", "كن", "كما", "ي", "نا",
    # Plural/dual markers
    "ا", "ن", "ون", "ين", "ان", "ات", "وا",
    # PV suffixes
    "ت", "تم", "تن", "تما", "تموا",
    # Combined (waw + pronoun)
    "وها", "وهم", "وكم", "وك", "وه", "ون",
    # Combined (nun + pronoun)
    "نه", "نها", "نهم", "نهن", "نك", "نكم", "نا", "نني",
    "كهم", "كها", "كنا",
    "ينا", "ينه", "ينها", "ينهم",
    # Imperfect plural + pronoun
    "ونه", "ونها", "ونهم", "ونهن", "ونك", "ونكم", "ونكما", "ونني",
    "ونا", "ونني",
    # Imperfect feminine + pronoun
    "ينه", "ينها", "ينهم",
    # Past + masc pl + pronoun
    "وكم", "وكما", "وكن", "وها", "وهم", "وهما", "وهن", "وني",
    # Past + ـتم + pronoun
    "تموه", "تموها", "تموهم", "تموني", "تمونا",
    # ـة (feminine noun) + pronoun (ة opens to ت when suffix attaches)
    "ته", "تها", "تهم", "تهن", "تهما",
    "تك", "تكم", "تكن", "تكما",
    "تي", "تنا",
    # ـة + tanwin
    "ةٌ", "ةٍ", "ةً",
    # Empty (no suffix)
    "",
}


# ============================================================================
# Closed-class loader — from new_arabic_analyzer's labels + operators
# ============================================================================

_QURAN_LABELS_PATHS = [
    _PACKAGE_ROOT / "data" / "quran_i3rab_labels.jsonl",
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"),
]
_OPERATORS_PATHS = [
    _PACKAGE_ROOT / "data" / "i3rab_ref" / "i3rab_operators.csv",
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran/i3rab_ref/i3rab_operators.csv"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/i3rab_ref/i3rab_operators.csv"),
]

# Labels in quran_i3rab_labels.jsonl that mean "closed-class (no root)"
NO_ROOT_LABELS = {
    "HARF", "HARF_JARR", "HARF_ATF", "HARF_NIDA", "HARF_NAFI",
    "HARF_NASB", "HARF_JAZM", "HARF_TAWKEED", "HARF_ISTIFHAM",
    "ISM_MAWSOOL", "ISM_ISHARA", "ISM_SHART", "ISM_ISTIFHAM",
    "DAMEER", "MAWSOOL",
    "ZARF_ZAMAN_MABNI", "ZARF_MAKAN_MABNI",
}

# Labels that mean "has a root" — DO NOT exclude even if MABNI
HAS_ROOT_LABELS = {"FIIL", "ISM", "FAAIL", "MAFOOL"}


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# ============================================================================
# Jamid loader — from MASAQ NOUN_CONCRETE rows
# ============================================================================

_MASAQ_PATHS = [
    _PACKAGE_ROOT / "data" / "MASAQ.csv",
    Path("/Users/husseinhiyassat/fractal/hussein/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/hussein/data/MASAQ.csv"),
]


def load_verbal_roots_from_masaq() -> set[str]:
    """تَحميل الجذور التي لها فعل حيّ في MASAQ (PV/IV/CV).

    تُستَخدم لِتَمييز:
      - الجامد الحقيقي (جذره لا فعل له: الأرض، الحجر، الماء، الجبل)
      - المُشتقّ ذي الدلالة المحسوسة (جذره له فعل: كتاب من كتب، مدرسة من درس)

    المعيار اللسانيّ: إذا ظَهَر الجذر يومًا كـ PV/IV/CV في MASAQ → الجذر
    إنتاجيّ، فالاسم الذي يَخرج منه على وزن إنتاجيّ هو مشتق.
    """
    verbal_tags = {"PV", "IV", "CV", "PV_PASS", "IV_PASS", "CV_PASS"}
    out: set[str] = set()
    for p in _MASAQ_PATHS:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                tag = (row.get("Morph_Tag") or "").strip()
                if tag not in verbal_tags:
                    continue
                stem = (row.get("Segmented_Word") or "").strip()
                stem_plain = _strip_diac(stem)
                if 2 <= len(stem_plain) <= 4:
                    out.add(stem_plain)
        break
    return out


def load_jamid_from_masaq() -> tuple[set[str], set[str]]:
    """Load jawamid (essence nouns: السماء، الأرض، البحر، الجبل، ...) from MASAQ.

    Returns a tuple ``(vocalized_set, unambiguous_stripped_set)`` so the
    detector can disambiguate homographs:

      - **vocalized_set**: full vocalized Word values (e.g., ``كُتُبٌ``)
        whose Morph_Tag is NOUN_CONCRETE on the Stem segment. Exact match
        keys.
      - **unambiguous_stripped_set**: stripped Without_Diacritics values
        that appear ONLY as NOUN_CONCRETE in MASAQ (never as a verb, مشتق,
        proper noun, ...). Safe to match diacritic-blind.

    Why two sets? ``كتب`` (stripped) is BOTH ``كَتَبَ`` (verb) AND ``كُتُبٌ``
    (jamid plural of كتاب). Matching the stripped form alone would falsely
    flag verbs as jamid. So:

      Match plan in jamid_detector:
        1. Try vocalized exact → if hit, jamid.
        2. Else try stripped against unambiguous_stripped_set → only fires
           when no other word in the Quran shares that consonant skeleton.

    CONSTITUTIONAL NOTE: jawamid have no derivational root by definition —
    they are essence-nouns (geonyms, zoonyms, astroyms, phytonyms, …), not
    forms derived from a verbal root via a wazn template.
    """
    vocalized: set[str] = set()
    # Per-stripped-form count of distinct (tag, vocalized) signatures
    # we observed.  If a stripped form has more than one signature AND any
    # of them is non-jamid, it's ambiguous.
    stripped_tags: dict[str, set[str]] = {}

    for p in _MASAQ_PATHS:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                typ = (row.get("Morph_Type") or "").strip()
                if typ != "Stem":
                    continue
                tag = (row.get("Morph_Tag") or "").strip()
                word = (row.get("Word") or "").strip()
                surf = (row.get("Without_Diacritics") or "").strip()
                if not word or not surf:
                    continue
                if tag == "NOUN_CONCRETE":
                    vocalized.add(word)
                # Track every stem tag we see for each stripped form.
                stripped_tags.setdefault(surf, set()).add(tag)
        break

    # A stripped form is "unambiguous jamid" iff it appears as NOUN_CONCRETE
    # AND it has no other Stem tag in the data.
    unambiguous_stripped: set[str] = {
        surf for surf, tags in stripped_tags.items()
        if tags == {"NOUN_CONCRETE"}
    }
    return vocalized, unambiguous_stripped


def load_closed_class_from_quran() -> set[str]:
    """Load closed-class words from new_arabic_analyzer.

    Logic: specific NO_ROOT labels (ISM_MAWSOOL, DAMEER, etc.) OVERRIDE
    generic HAS_ROOT (ISM). A word labeled BOTH ISM and ISM_MAWSOOL is
    closed-class (it's a relative pronoun, the ISM is just the generic class).
    Only the generic FIIL/ISM/MAFOOL/FAAIL WITHOUT any NO_ROOT label means
    "has root".

    Exceptions (per `data/contracts/closed_class_exceptions.csv`):
      - mode=exclude    → don't add the stripped form at all (fused tokens)
      - mode=exact_only → add only the exact_form, not the stripped form
        (diacritic-sensitive particles whose stripped form is also a noun)
    """
    # Load constitutional exceptions
    try:
        # Import-here to avoid circular import (contracts_loader imports from us)
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parent))
        from contracts_loader import load_closed_class_exceptions  # type: ignore
        exceptions = load_closed_class_exceptions()
    except Exception:
        exceptions = {}

    out = set()

    def _add(stripped: str, original: str) -> None:
        """Honor closed_class_exceptions when adding to the set."""
        ex = exceptions.get(stripped)
        if ex is None:
            out.add(stripped)
            return
        if ex["mode"] == "exclude":
            return  # drop entirely
        if ex["mode"] == "exact_only":
            ef = ex.get("exact_form") or ""
            if ef and (original == ef or stripped == _strip_diac(ef)):
                out.add(ef)  # exact form only
            return
        # unknown mode → fall through to default add
        out.add(stripped)

    # From labels.jsonl
    for p in _QURAN_LABELS_PATHS:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    labels = r.get("labels", [])
                    # MC FIX 2026-05-24: Contradictory labels — if a word is
                    # tagged BOTH FIIL and HARF, the data source is unreliable.
                    # A verb is NEVER closed-class. Skip such entries so the
                    # imperative «اهدنا» doesn't end up mis-classified as HARF.
                    if "FIIL" in labels:
                        continue
                    # Sub-token-only HARF labels: if any HARF_* sublabel is
                    # attached but the word starts with a clitic prefix
                    # (و/ف/ب/ل/ك/س), the data source is tagging only the
                    # clitic — the body is the real content. Skip such rows
                    # so verbs like وَاتَّقُوا، فَٱكْتُبُوهُ، فَلْيَكْتُبْ don't
                    # leak into closed_class as "حرف".
                    orig_for_check = r.get("word", "")
                    _CLITIC_HARF_LABELS = {
                        "HARF_ATF", "HARF_ISTINAAD", "HARF_JARR",
                        "HARF_NIDA", "HARF_TAHQEEQ", "HARF_AMR", "HARF_NAFY",
                        "HARF_SHART", "HARF_TAKHFEEF",
                    }
                    _PREFIX_CLITICS = (
                        "و", "وَ", "ف", "فَ",
                        "بِ", "ب", "لِ", "ل", "كَ", "ك", "سَ", "س",
                    )
                    # Strip clitic prefix to get body length (no diacritics)
                    _stripped_full = _strip_diac(orig_for_check)
                    _body_after_clitic = _stripped_full
                    if _stripped_full[:1] in {"و","ف","ب","ل","ك","س"}:
                        _body_after_clitic = _stripped_full[1:]
                    # Heuristic: real particles are short (≤3 chars stripped).
                    # If body after clitic is ≥4 chars, it's a verb/noun whose
                    # HARF tag applies only to the prefix.
                    if (
                        any(lbl in _CLITIC_HARF_LABELS for lbl in labels)
                        and orig_for_check.startswith(_PREFIX_CLITICS)
                        and len(_body_after_clitic) >= 4
                    ):
                        continue
                    # Bare ["HARF","MABNI"] (no sub-label) on a long-body
                    # word with a clitic prefix → also a mis-tag of the clitic.
                    if (
                        set(labels) <= {"HARF", "MABNI"}
                        and "HARF" in labels
                        and orig_for_check.startswith(_PREFIX_CLITICS)
                        and len(_body_after_clitic) >= 4
                    ):
                        continue
                    # Specific NO_ROOT label takes priority over generic ISM/FIIL
                    if any(lbl in NO_ROOT_LABELS for lbl in labels):
                        orig = r["word"]
                        _add(_strip_diac(orig), orig)
                except Exception:
                    continue
        break

    # From operators
    # MC FIX 2026-05-24 (per user critique): the operators CSV includes
    # kana-family verbs (كان، ليس، صار...) with i3rab annotated as
    # «فِعْلٌ مَاضٍ نَاسِخٌ». These are VERBS not closed-class. Skip them
    # when the i3rab description contains «فعل».
    for p in _OPERATORS_PATHS:
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                op = row.get("operator_key", "").strip()
                i3rab = row.get("operator_i3rab", "") or ""
                if op:
                    # skip if i3rab says verb (فعل ماضٍ، فعل مضارع، فعل أمر)
                    if "فِعْل" in i3rab or "فعل" in i3rab:
                        continue
                    _add(_strip_diac(op), op)
        break

    return out
