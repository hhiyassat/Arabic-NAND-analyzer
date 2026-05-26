#!/usr/bin/env python3
"""Derive wazn (pattern) from each (root, word) pair in mishkat_word_root.csv.

The wazn is obtained by walking the word and replacing each root letter
in order with ف / ع / ل (and ل again for 4-letter roots). Diacritics
travel with the replacement letter; non-root letters are preserved.

Rules:
  1. If root contains any weak letter (و/ي/ا/ى/آ) → row → no_wazn.csv
  2. If root is 1-2 letters or 5+ letters → row → no_wazn.csv (out of scope)
  3. Hamza (ء) is sound — apply transformation. Hamza variants أ/إ/ؤ/ئ/آ
     match the root's ء via a hamza equivalence class.
  4. Geminate roots (root[1]==root[2] for triliteral):
     - Pattern A: doubled letter explicit in word → naive walk works
     - Pattern B: shadda compresses the doubled letter → expand on the fly
       (insert sukoon on previous letter, emit next fa3l-letter)
  5. Quadriliteral roots (4 letters) use pattern ف-ع-ل-ل
  6. Alignment failure (couldn't match all root letters in order)
     → row → no_wazn.csv with reason=alignment_failed

Outputs:
  /Users/husseinhiyassat/fractal/hussein/data/extracted/mishkat_word_root_with_wazn.csv
  /Users/husseinhiyassat/fractal/hussein/data/extracted/no_wazn.csv
"""

from __future__ import annotations

import csv
import sys
import unicodedata
from pathlib import Path
from typing import Optional


def _resolve_paths():
    """Return SRC, OUT_OK, OUT_NO, AUDITED, WEIGHTS, EXTENSIONS paths."""
    macos_root = Path("/Users/husseinhiyassat/fractal")
    sandbox_root = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos_root, sandbox_root):
        src = root / "new_arabic_analyzer/data/mishkat_word_root.csv"
        if src.is_file():
            return (
                src,
                root / "hussein/data/extracted/mishkat_word_root_with_wazn.csv",
                root / "hussein/data/extracted/no_wazn.csv",
                root / "salehan/Salehan19-6-67/data/audited_roots.csv",
                root / "alasmaa/Mushtaqat_Weights_Final_Corrected_With_Fa3ll.csv",
                root / "hussein/data/extracted/wazn_db_extensions.csv",
            )
    raise FileNotFoundError("Cannot resolve project paths on either macOS or sandbox layout.")


SRC, OUT_OK, OUT_NO, AUDITED_PATH, WEIGHTS_PATH, EXTENSIONS_PATH = _resolve_paths()

# Diacritics (drop from root, keep in word for diacritic-passthrough)
DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
SHADDA = "ّ"
SUKUN = "ْ"
TATWEEL = "ـ"

# Weak letters — root containing any → no_wazn
WEAK_LETTERS = {"و", "ي", "ا", "ى", "آ", "ٱ"}

# Hamza equivalence — root's ء matches any of these in the word
HAMZA_VARIANTS = {"ء", "أ", "إ", "ؤ", "ئ", "آ"}


def strip_diacritics(s: str) -> str:
    """Remove diacritics, shadda, tatweel — leaves only base letters."""
    return "".join(c for c in s if c not in DIACRITICS and c != TATWEEL)


def normalize_letter_for_match(c: str) -> str:
    """Normalize a letter for ROOT-vs-WORD comparison.

    Hamza variants collapse to ء so that root letter ء matches any of
    أ / إ / ؤ / ئ / آ / ء found in the word.
    Taa marbuta ة and haa ه collapse together — many roots list ـه as
    the final radical even when the surface word uses ـة (e.g. سنه + سَنَةً
    where the root-letter is ه but the word writes it as ة). Both
    directions are accepted.
    """
    if c in HAMZA_VARIANTS:
        return "ء"
    if c == "ة":
        return "ه"
    return c


def is_weak_root(root_plain: str) -> bool:
    return any(c in WEAK_LETTERS for c in root_plain)


def _restore_form_viii_hamza(word: str, root_letters: list[str]) -> Optional[str]:
    """Restore the assimilated hamza in Form VIII (اِفْتَعَلَ) of hamza-initial roots.

    Trigger conditions:
      - root[0] == 'ء'
      - root does NOT contain ت (so the ت we're about to find is the افتعل augment)
      - the word contains a ت immediately followed (through optional non-shadda
        diacritics) by a SHADDA

    Effect: insert ء + sukoon BEFORE the ت, drop the SHADDA.
    Example: ءخذ + اتَّخَذَ → اءْتَخَذَ (logical) → normal walk yields اِفْتَعَلَ

    Returns the transformed word string, or None if pattern doesn't match.
    """
    if not root_letters or root_letters[0] != "ء":
        return None
    if "ت" in root_letters:
        return None
    chars = list(word)
    n = len(chars)
    for i in range(n):
        if chars[i] != "ت":
            continue
        j = i + 1
        shadda_pos = -1
        while j < n and chars[j] in DIACRITICS:
            if chars[j] == SHADDA:
                shadda_pos = j
                break
            j += 1
        if shadda_pos == -1:
            continue
        # Found: insert ء + sukoon BEFORE the ت, drop the shadda.
        new_chars = (
            chars[:i] + ["ء", SUKUN] + chars[i:shadda_pos] + chars[shadda_pos + 1 :]
        )
        return "".join(new_chars)
    return None


def _al_prefix_end(chars: list[str]) -> int:
    """If word starts with ال (alif + lam), return the index right after it.

    Returns 0 if there's no ال prefix. Handles diacritics on the alif and
    lam (most commonly: ا + ـْ + ل, or ٱ + ل for hamzat-al-wasl).

    Why this matters: a root starting with ل (e.g. لؤلؤ → اللُّؤْلُؤُ) collides
    with the article's ل under greedy matching. By skipping ال up-front we
    ensure the FIRST root letter is found after the article.
    """
    n = len(chars)
    if n < 3:
        return 0
    i = 0
    if chars[i] not in ("ا", "ٱ"):
        return 0
    i += 1
    while i < n and chars[i] in DIACRITICS:
        i += 1
    if i >= n or chars[i] != "ل":
        return 0
    i += 1
    while i < n and chars[i] in DIACRITICS:
        i += 1
    # There must be at least one more letter after — otherwise this isn't ال + word.
    if i >= n:
        return 0
    return i


def derive_wazn(root: str, word: str) -> tuple[Optional[str], Optional[str]]:
    """Return (wazn, reason_if_failed).

    On success: (wazn_string, None)
    On failure: (None, reason)  where reason ∈
        {"weak_root", "root_too_short", "root_too_long",
         "alignment_failed", "empty"}
    """
    root_plain = strip_diacritics(root)
    if not root_plain or not word:
        return None, "empty"
    if len(root_plain) < 3:
        return None, "root_too_short"
    if len(root_plain) > 4:
        return None, "root_too_long"
    if is_weak_root(root_plain):
        return None, "weak_root"

    # Special-case: forms of root ءله — these are all reverential references
    # to the Divine (الله, إله, آلهة, اللهم, ...). Per project convention they
    # are NOT given a wazn — they are proper-noun lexemes treated by the
    # aalam_loader's divine_name category. Route all of them to a single
    # explicit no_wazn reason.
    if root_plain == "ءله":
        return None, "divine_lexeme"

    # Pattern letters for the wazn — extend with ل for quadriliteral
    fa3l = ["ف", "ع", "ل", "ل"][: len(root_plain)]

    root_letters = list(root_plain)
    # Geminate trigger: root_letters[i] == root_letters[i+1]
    is_geminate_pair = [
        i < len(root_letters) - 1 and root_letters[i] == root_letters[i + 1]
        for i in range(len(root_letters))
    ]

    out: list[str] = []
    idx = 0  # which root letter to look for next
    last_matched_was_root = False  # was the most recent output a fa3l letter?

    # Pre-process: restore assimilated hamza in Form VIII verbs.
    # Surface اتَّخَذَ → restored ائْتَخَذَ which then walks cleanly to افْتَعَلَ.
    restored = _restore_form_viii_hamza(word, root_letters)
    if restored is not None:
        word = restored
    # Pre-process: expand alif-madda آ to its logical components ء + fatha + ا.
    # The fatha is implicit in آ; without it the wazn for forms like آلِهَة
    # comes out as "فاعِلَة" (missing fatha on ف). Decomposition: آ → ءَا.
    word = word.replace("آ", "ءَا")
    chars = list(word)
    # If word starts with ال AND the first root letter is also ل, the greedy
    # match would consume the article's ل as the root letter. Skip past ال
    # in that case (we still output ال in the wazn).
    #
    # Also: after AL-skip for a lam-initial root, the SHADDA that appears on
    # the first root letter is from lam-shamsi assimilation (ال + ل → اللّ).
    # That shadda doesn't belong to the wazn — drop it on output.
    i = 0
    drop_first_root_shadda = False
    if root_letters[0] == "ل":
        al_end = _al_prefix_end(chars)
        if al_end > 0:
            for c in chars[:al_end]:
                out.append(c)
            i = al_end
            drop_first_root_shadda = True
    while i < len(chars):
        c = chars[i]
        if c == TATWEEL:
            i += 1
            continue
        if c in DIACRITICS:
            if c == SHADDA:
                # Drop lam-shamsi shadda on the first root letter when we
                # already skipped ال — that shadda represents the assimilated
                # article's ل, not a root feature.
                if drop_first_root_shadda and idx == 1:
                    drop_first_root_shadda = False  # only drop once
                    i += 1
                    continue
                # Geminate detection:
                # If last matched root letter equals the next root letter to match,
                # then this shadda represents the doubled root letter.
                #
                # Logical decomposition of the input around the shadda:
                #   [prev fa3l-letter] + [diacritics_a] + SHADDA + [diacritics_b]
                # Logical wazn output should be:
                #   [prev fa3l-letter] + SUKUN + [next fa3l-letter] + diacritics_a + diacritics_b
                # i.e. diacritics_a (typically the kasra/fatha/tanwin written before
                # the shadda) belong phonetically to the SECOND (doubled) root letter.
                if (
                    last_matched_was_root
                    and idx > 0
                    and idx < len(root_letters)
                    and root_letters[idx - 1] == root_letters[idx]
                ):
                    # Find where the previous fa3l letter sits in `out`
                    # and pull off any diacritics emitted between it and now.
                    prev_fa3l = fa3l[idx - 1]
                    # Walk back from end of out to find the last occurrence of prev_fa3l
                    j = len(out) - 1
                    while j >= 0 and out[j] != prev_fa3l:
                        j -= 1
                    diacritics_a = out[j + 1 :] if j >= 0 else []
                    # Rebuild: keep up to and including the prev_fa3l, add sukoon,
                    # add new fa3l letter, then re-emit the captured diacritics
                    out = out[: j + 1]
                    out.append(SUKUN)
                    out.append(fa3l[idx])
                    out.extend(diacritics_a)
                    idx += 1
                    last_matched_was_root = True
                    i += 1
                    continue
                # Otherwise — non-geminate shadda (e.g. assimilation of ال+ن,
                # or doubling on non-root letter) — pass through.
                out.append(c)
                i += 1
                continue
            # Non-shadda diacritic — pass through
            out.append(c)
            i += 1
            continue

        # Consonant letter
        if idx < len(root_letters):
            target = root_letters[idx]
            if normalize_letter_for_match(c) == normalize_letter_for_match(target):
                out.append(fa3l[idx])
                idx += 1
                last_matched_was_root = True
                i += 1
                continue
        # Non-root letter (or already matched all)
        out.append(c)
        last_matched_was_root = False
        i += 1

    if idx < len(root_letters):
        return None, "alignment_failed"

    return "".join(out), None


def load_audited_roots(path: Path) -> set[str]:
    """Return the set of plain (diacritic-stripped) audited roots."""
    out: set[str] = set()
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            r = (row.get("الجذر") or "").strip()
            if r:
                out.add(strip_diacritics(r))
    return out


def _hamza_to_alif(s: str) -> str:
    """For wazn-database matching: normalize all hamza-on-X variants to bare ا.
    This lets أَفْعَل / إِفْعَال / آلِهَة all match against the same canonical
    pattern entry in the 80-weights table.
    """
    return (
        s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
         .replace("ؤ", "ء").replace("ئ", "ء")
    )


def _normalize_for_db(s: str) -> str:
    """Plain (no diacritics) + hamza folded to alif. Used for db membership."""
    return _hamza_to_alif(strip_diacritics(s))


def load_wazn_patterns(path: Path, extensions_path: Path | None = None) -> set[str]:
    """Return the set of canonical wazn patterns (plain, hamza-folded).

    Loads the official 80 mushtaqat weights, plus an optional extension file
    that adds broken plurals, quadriliterals, and rare-but-attested patterns.
    """
    out: set[str] = set()
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                w = (row.get("الوزن مضبوطًا") or "").strip()
                if w:
                    out.add(_normalize_for_db(w))
                f_form = (row.get("الصورة بالتاء / المؤنث") or "").strip()
                if f_form:
                    out.add(_normalize_for_db(f_form))
    if extensions_path and extensions_path.is_file():
        with extensions_path.open(encoding="utf-8", newline="") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # CSV row: category,wazn,example,notes
                parts = line.split(",")
                if len(parts) >= 2 and parts[1].strip() and parts[1] != "wazn":
                    out.add(_normalize_for_db(parts[1].strip()))
    return out


# Single-letter clitic prefixes that may attach before a noun pattern.
_CLITIC_PREFIXES = set("وفبكل")
# Pronoun suffix forms (plain, ordered longest-first for greedy strip).
_PRONOUN_SUFFIXES = ("هما", "كما", "هنّ", "هم", "هن", "كم", "كن", "نا", "ها", "ه", "ك", "ي")

# Sound plural / dual / tanwin-alif suffixes — strip to recover the singular
# pattern (الفاعلون → فاعل, فعلات → فعلة, فعلًا → فعل).
_NUMBER_SUFFIXES = ("ين", "ون", "ان", "ات", "ا")


def _strip_suffix_from_chars(chars: list[str], suffix_plain: str) -> list[str]:
    """If chars' plain form ends with suffix_plain, remove the suffix letters
    (and their diacritics). Returns a (possibly-shortened) list."""
    plain = strip_diacritics("".join(chars))
    if not plain.endswith(suffix_plain):
        return chars
    j = len(chars) - 1
    removed = 0
    while j >= 0 and removed < len(suffix_plain):
        if chars[j] not in DIACRITICS:
            removed += 1
        j -= 1
    return chars[: j + 1]


def _strip_suffixes_and_final_harakah(chars: list[str]) -> list[str]:
    """Strip pronoun suffix (if any) + sound-plural/tanwin-alif suffix (if any)
    + trailing diacritics."""
    for suf in _PRONOUN_SUFFIXES:
        new = _strip_suffix_from_chars(chars, suf)
        if new is not chars and len(new) < len(chars):
            chars = new
            break
    # Then strip number/tanwin suffix
    for suf in _NUMBER_SUFFIXES:
        new = _strip_suffix_from_chars(chars, suf)
        if new is not chars and len(new) < len(chars):
            chars = new
            break
    while chars and chars[-1] in DIACRITICS:
        chars.pop()
    return chars


def canonicalize_wazn_variants(wazn: str) -> list[str]:
    """Return candidate canonical forms of a derived wazn to test against the
    pattern database. We try multiple strip combinations because:
      - The wazn may start with the pattern's own ف (so we MUST NOT strip)
      - Or with a clitic + ف (so we MUST strip)
      - Or with ال (definite article)
      - Or with clitic + ال (e.g. وَال...)
    Returning all candidates and checking membership of ANY is more robust
    than guessing which strip was correct.
    """
    if not wazn:
        return [wazn]
    chars = list(wazn)
    n = len(chars)
    variants: list[list[str]] = []

    # Variant 1: as-is
    variants.append(chars[:])

    # Variant 2: strip 1 clitic letter (and its diacritic)
    if n >= 3 and chars[0] in _CLITIC_PREFIXES:
        j = 1
        while j < n and chars[j] in DIACRITICS:
            j += 1
        variants.append(chars[j:])

    # Variant 3: strip ال from start
    if n >= 3 and chars[0] == "ا" and chars[1] == "ل":
        j = 2
        while j < n and chars[j] in DIACRITICS:
            j += 1
        variants.append(chars[j:])

    # Variant 4: strip clitic + ال (e.g. وَال, فَال)
    if n >= 5 and chars[0] in _CLITIC_PREFIXES:
        j = 1
        while j < n and chars[j] in DIACRITICS:
            j += 1
        if j + 1 < n and chars[j] == "ا" and chars[j + 1] == "ل":
            j += 2
            while j < n and chars[j] in DIACRITICS:
                j += 1
            variants.append(chars[j:])

    # Variant 5: strip لِ + ل (lam-jar + article-lam with elided alif).
    # In writing: لِلْـ → ل + ـِ + ل + ـْ (no ا between the two ل's).
    # Distinct from variants 1-4 because there's no ا.
    if n >= 4 and chars[0] == "ل":
        j = 1
        while j < n and chars[j] in DIACRITICS:
            j += 1
        if j < n and chars[j] == "ل":
            j += 1
            while j < n and chars[j] in DIACRITICS:
                j += 1
            # Only emit if there's at least one more letter after
            if j < n:
                variants.append(chars[j:])

    # Variant 6: strip clitic + لل (e.g. وَلِلْـ، فَلِلْـ — for + the + noun)
    if n >= 5 and chars[0] in _CLITIC_PREFIXES:
        j = 1
        while j < n and chars[j] in DIACRITICS:
            j += 1
        if j < n and chars[j] == "ل":
            j += 1
            while j < n and chars[j] in DIACRITICS:
                j += 1
            if j < n and chars[j] == "ل":
                j += 1
                while j < n and chars[j] in DIACRITICS:
                    j += 1
                if j < n:
                    variants.append(chars[j:])

    # Strip pronoun suffix + final harakah from each variant
    out = ["".join(_strip_suffixes_and_final_harakah(v[:])) for v in variants]
    # Dedupe preserving order
    seen = set()
    deduped = []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def canonicalize_wazn(wazn: str) -> str:
    """Backwards-compat: return the FIRST (most-conservative) variant."""
    variants = canonicalize_wazn_variants(wazn)
    return variants[0] if variants else wazn


# === Morphological classification (verb vs noun) ===
#
# A wazn is classified as a VERB if its canonical form matches one of the
# known verb shapes (past, mudaari', imperative, or any of the augmented
# verb forms I-X). Otherwise it's classified as a NOUN (singular pattern,
# مشتق, plural, or quadriliteral noun).
#
# Diacritics matter: فَعَلَ (past verb) and فَعْل (noun) are distinct.

_PAST_VERB_PATTERNS = {
    # Form I (ثلاثي مجرد): فَعَلَ، فَعِلَ، فَعُلَ
    "فعل",  # — but only when the canonical form has vowels matching فَعَلَ/فَعِلَ/فَعُلَ
}

# Plain (no-diacritic, hamza-folded) patterns that are definitively verb forms:
_VERB_PLAIN_PATTERNS = {
    # Past forms
    "فعل", "ففعل", "وفعل",  # I (only when vowels match — we cross-check)
    "افعل",                  # IV (أفعلَ) - shape "افعل"
    "فاعل",                  # III - same plain as فاعل noun, disambiguate by وزن
    "تفعل", "تفاعل",          # V, VI
    "انفعل", "افتعل",         # VII, VIII
    "افعل", "افعال",          # IX (افعلَّ → افعل plain)
    "استفعل",                # X
    "افعوعل", "افعول",        # rare augments
    # Mudaari' forms (start with ي/ت/ن/أ + ف)
    "يفعل", "تفعل", "نفعل", "افعل",
    "يفاعل", "تفاعل", "نفاعل", "افاعل",
    "يتفعل", "تتفعل", "نتفعل", "اتفعل",
    "يتفاعل", "تتفاعل", "نتفاعل", "اتفاعل",
    "ينفعل", "تنفعل", "ننفعل", "انفعل",
    "يفتعل", "تفتعل", "نفتعل", "افتعل",
    "يستفعل", "تستفعل", "نستفعل", "استفعل",
    # Imperative
    "افعل", "افتعل", "استفعل",
}

# Past verb conjugation suffixes (plain): the wazn ends with these when
# a past-tense verb has subject suffix attached.
_PAST_VERB_SUFFIXES_PLAIN = (
    "تما", "تما", "تن", "تما", "تم", "ت",
    "نا", "ن", "وا", "تا",
)


def _strip_only_prefixes(wazn: str) -> str:
    """Strip clitic prefix (و/ف/ب/ك/ل + diacritic) and ال from start, BUT
    keep all suffixes (especially وا, تم, نا which are verb-conjugation
    markers we need for morph_type detection)."""
    chars = list(wazn)
    i = 0
    n = len(chars)
    if i < n and chars[i] in _CLITIC_PREFIXES:
        i += 1
        while i < n and chars[i] in DIACRITICS:
            i += 1
    if i + 1 < n and chars[i] == "ا" and chars[i + 1] == "ل":
        i += 2
        while i < n and chars[i] in DIACRITICS:
            i += 1
    return "".join(chars[i:])


def classify_morph_type(wazn: str, root: str) -> str:
    """Return 'verb' or 'noun' for a derived wazn.

    Critical: this runs on the wazn AFTER stripping clitic+ال only — pronoun
    and number suffixes are KEPT because they are the strongest verb-conjugation
    signal (وا = جماعة الغائبين, تُم = جمع مخاطب, ـنَ = نون النسوة, ـت = تاء
    التأنيث). Stripping them would erase the verb signal.

    Heuristics (in order):
      1. Mudaari' shape: starts with ي/ت/ن/أ immediately followed by ف.
      2. Past with conjugation suffix: ends with تما/تم/تن/نا/ن/وا/ت AND
         residue before suffix matches a past verb pattern.
      3. Augmented past forms (bare): plain == one of افتعل/استفعل/...
      4. Past form I: ف + harakah + ع + harakah + ل + فتحة (vowels matter).
      5. Else → noun.
    """
    if not wazn:
        return "noun"
    # Check ORIGINAL wazn first (most informative for past+ضمير cases like
    # فُعِلُوا where the leading ف IS the pattern letter, not a clitic).
    if _looks_like_verb(wazn, wazn):
        return "verb"
    # Then prefix-stripped version (catches وَيَفْعَلُ-style cases)
    stripped = _strip_only_prefixes(wazn)
    if stripped != wazn and _looks_like_verb(stripped, wazn):
        return "verb"
    # Fallback: also try the fuller canonical variants
    for canon in canonicalize_wazn_variants(wazn):
        if _looks_like_verb(canon, wazn):
            return "verb"
    return "noun"


def _strip_pronoun_suffix_plain(plain: str) -> str:
    """Strip a single trailing pronoun-suffix substring (plain), if present.
    Pronouns: ـه/ـها/ـهم/ـهن/ـك/ـكم/ـكن/ـنا/ـي/ـوها/ـوهم/ـوكم
    Used to peel an object pronoun BEFORE checking subject-verb conjugation."""
    pronouns = ("وها", "وهم", "وكم", "وني", "هما", "كما",
                "ها", "هم", "هن", "كم", "كن", "نا", "ه", "ك", "ي")
    for p in pronouns:
        if plain.endswith(p) and len(plain) > len(p) + 2:
            return plain[: -len(p)]
    return plain


def _looks_like_verb(canon: str, original_wazn: str) -> bool:
    """Heuristic verb detection on a canonicalized wazn (with diacritics)."""
    if not canon:
        return False
    plain = _normalize_for_db(canon)

    # Future prefix س + يفعل: سَيُبْطِلُهُ → سَيُفْعِلُهُ → plain سيفعل
    if plain.startswith("س") and len(plain) >= 4 and plain[1] in "يتنا" and plain[2] == "ف":
        return True
    # Imperative form with لـ + مضارع: فَلْيَأْكُل → فَلْيَفْعُل → "ليفعل"
    if plain.startswith("ل") and len(plain) >= 4 and plain[1] in "يتنا" and plain[2] == "ف":
        return True
    # Vocative يا + اسم (يَا + اسم) — يا is a particle (not verb), STILL noun, but
    # strip the يا for normal noun pattern matching elsewhere. Here we leave it.

    # 1. Mudaari' — starts with ي/ت/ن/أ followed by one of:
    #    ف (forms I, IV: يَفْعَلُ / يُفْعِلُ)
    #    ست (form X: يَسْتَفْعِلُ)
    #    ن (form VII: يَنْفَعِلُ)
    #    تف (forms V, VI: يَتَفَعَّلُ / يَتَفَاعَلُ)
    if len(plain) >= 3 and plain[0] in "يتنا":
        if plain[1] == "ف":
            return True
        if len(plain) >= 4 and plain[1:3] == "ست" and plain[3] == "ف":
            return True
        if len(plain) >= 4 and plain[1] == "ن" and plain[2] == "ف":
            return True
        if len(plain) >= 4 and plain[1] == "ت" and plain[2] == "ف":
            return True
    # 2. Past with conjugation suffix — check residue + suffix shape.
    # First peel an OBJECT pronoun (if any) since verb + subject-suffix +
    # object-pronoun is common: فَعَلُوكُم = فَعَلُوا + كم, تَرَكْتُمُوهَا = تَرَكْتُمُو + ها
    _PAST_RESIDUES = {
        "فعل", "افعل", "فاعل", "تفعل", "تفاعل",
        "انفعل", "افتعل", "استفعل",
        "افعل", "افاعل", "اتفعل", "اتفاعل",
        "ففعل", "وفعل", "لفعل", "كفعل", "بفعل",
        "فعلل", "تفعلل",
    }
    # Try plain as-is, and also after stripping one object pronoun
    candidates = [plain, _strip_pronoun_suffix_plain(plain)]
    for cand in candidates:
        for suf in ("تموا", "تما", "تمو", "تم", "تن", "نا", "ت", "ن", "وا"):
            if cand.endswith(suf):
                residue = cand[: -len(suf)]
                if residue in _PAST_RESIDUES:
                    return True
    # 3. Augmented past form bare (no suffix yet) — diacritic-aware
    diacs = _extract_root_letter_diacritics(canon)
    # Find ع and ل by letter identity (not position — different patterns put
    # them at different positions: فعل→1, فاعل→2, مفعل→2 etc.)
    ain_idx = next((i for i, (c, _) in enumerate(diacs) if c == "ع"), None)
    lam_idx = next((i for i, (c, _) in enumerate(diacs) if c == "ل"), None)
    ain_h = diacs[ain_idx][1] if ain_idx is not None else ""
    lam_h = diacs[lam_idx][1] if lam_idx is not None else ""

    if plain == "فعل":
        # فَعْل/فُعْل/فِعْل = noun (sukoon on ع)
        # فَعَلَ/فَعِلَ/فَعُلَ = verb (vowel on ع + fath on ل)
        if ain_h == "ْ":
            return False
        if ain_h in {"َ", "ُ", "ِ"} and lam_h == "َ":
            return True
        return False  # ambiguous → noun by default
    if plain == "فاعل":
        # فَاعِل = noun اسم الفاعل (kasra on ع)
        # فَاعَلَ = verb form III past (fatha on ع + fatha on ل)
        if ain_h == "ِ":
            return False
        if ain_h == "َ" and lam_h == "َ":
            return True
        return False
    if plain == "افعل":
        # أَفْعَل = noun اسم التفضيل (or form IV mudaari prefix أ)
        # أَفْعَلَ = verb form IV past (fath on ل)
        if lam_h == "َ":
            return True
        return False
    if plain == "تفعل":
        # تَفْعَلُ / تَفْعَلَ / تَفَعَّلَ → almost always verb (mudaari or past V)
        return True
    # All other matched augmented forms (انفعل, افتعل, استفعل, افعال) are
    # exclusively verb patterns in classical morphology.
    if plain in {"تفاعل", "انفعل", "افتعل", "استفعل"}:
        return True
    return False


def _extract_root_letter_diacritics(wazn: str) -> list[tuple[str, str]]:
    """Return [(letter, immediate_following_harakah), ...] for each base letter
    in the canonical wazn. Used by verb/noun disambiguation."""
    out = []
    chars = list(wazn)
    i = 0
    n = len(chars)
    while i < n:
        c = chars[i]
        if c in DIACRITICS:
            i += 1
            continue
        # Base letter — collect following non-shadda diacritic
        i += 1
        harakah = ""
        while i < n and chars[i] in DIACRITICS:
            if chars[i] != SHADDA:
                harakah = chars[i]
            i += 1
        out.append((c, harakah))
    return out


def main() -> int:
    if not SRC.is_file():
        print(f"ERROR: source not found: {SRC}", file=sys.stderr)
        return 1
    OUT_OK.parent.mkdir(parents=True, exist_ok=True)

    audited_roots = load_audited_roots(AUDITED_PATH)
    wazn_db = load_wazn_patterns(WEIGHTS_PATH, EXTENSIONS_PATH)
    print(f"loaded audited roots: {len(audited_roots)}", file=sys.stderr)
    print(f"loaded wazn patterns: {len(wazn_db)}", file=sys.stderr)

    stats = {
        "total": 0,
        "ok": 0,
        "no_wazn_total": 0,
        "reasons": {},
        "by_root_len": {},
        "geminate_ok": 0,
        "root_audited_true": 0,
        "root_audited_false": 0,
        "wazn_in_db_true": 0,
        "wazn_in_db_false": 0,
    }

    ok_rows: list[dict] = []
    no_rows: list[dict] = []

    with SRC.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            root = (row.get("root") or "").strip()
            word = (row.get("word") or "").strip()
            count = (row.get("count") or "").strip()

            root_plain = strip_diacritics(root)
            stats["by_root_len"][len(root_plain)] = (
                stats["by_root_len"].get(len(root_plain), 0) + 1
            )

            wazn, reason = derive_wazn(root, word)
            if wazn is not None:
                root_audited = root_plain in audited_roots
                variants = canonicalize_wazn_variants(wazn)
                wazn_canon = variants[0] if variants else ""
                wazn_in_db = any(_normalize_for_db(v) in wazn_db for v in variants)
                morph_type = classify_morph_type(wazn, root)
                ok_rows.append(
                    {
                        "root": root,
                        "word": word,
                        "count": count,
                        "wazn": wazn,
                        "wazn_canonical": wazn_canon,
                        "morph_type": morph_type,
                        "root_audited": "true" if root_audited else "false",
                        "wazn_in_db": "true" if wazn_in_db else "false",
                    }
                )
                stats["ok"] += 1
                if len(root_plain) == 3 and root_plain[1] == root_plain[2]:
                    stats["geminate_ok"] += 1
                if root_audited:
                    stats["root_audited_true"] += 1
                else:
                    stats["root_audited_false"] += 1
                if wazn_in_db:
                    stats["wazn_in_db_true"] += 1
                else:
                    stats["wazn_in_db_false"] += 1
            else:
                no_rows.append(
                    {
                        "root": root,
                        "word": word,
                        "count": count,
                        "reason": reason,
                    }
                )
                stats["no_wazn_total"] += 1
                stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1

    # Write outputs
    with OUT_OK.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "root", "word", "count", "wazn",
                "wazn_canonical", "morph_type",
                "root_audited", "wazn_in_db",
            ],
        )
        writer.writeheader()
        writer.writerows(ok_rows)

    with OUT_NO.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["root", "word", "count", "reason"]
        )
        writer.writeheader()
        writer.writerows(no_rows)

    # Report
    print("=" * 60)
    print("Wazn derivation from mishkat_word_root.csv")
    print("=" * 60)
    print(f"Source:           {SRC}")
    print(f"Total rows:       {stats['total']}")
    print(f"OK (with wazn):   {stats['ok']}  ({100*stats['ok']/stats['total']:.1f}%)")
    print(f"  of which geminate-handled: {stats['geminate_ok']}")
    print(f"Cross-checks (on OK rows):")
    ok = stats['ok'] or 1
    print(f"  root_audited=true:     {stats['root_audited_true']:6d}  ({100*stats['root_audited_true']/ok:.1f}%)")
    print(f"  root_audited=false:    {stats['root_audited_false']:6d}  ({100*stats['root_audited_false']/ok:.1f}%)")
    print(f"  wazn_in_db=true:       {stats['wazn_in_db_true']:6d}  ({100*stats['wazn_in_db_true']/ok:.1f}%)")
    print(f"  wazn_in_db=false:      {stats['wazn_in_db_false']:6d}  ({100*stats['wazn_in_db_false']/ok:.1f}%)")
    # morph_type breakdown
    nouns = [r for r in ok_rows if r["morph_type"] == "noun"]
    verbs = [r for r in ok_rows if r["morph_type"] == "verb"]
    noun_in_db = sum(1 for r in nouns if r["wazn_in_db"] == "true")
    verb_in_db = sum(1 for r in verbs if r["wazn_in_db"] == "true")
    print(f"Morph-type breakdown:")
    print(f"  nouns:    {len(nouns):6d}  ({100*len(nouns)/ok:.1f}%)   "
          f"in_db={noun_in_db} ({100*noun_in_db/(len(nouns) or 1):.1f}% of nouns)")
    print(f"  verbs:    {len(verbs):6d}  ({100*len(verbs)/ok:.1f}%)   "
          f"in_db={verb_in_db} ({100*verb_in_db/(len(verbs) or 1):.1f}% of verbs)")
    print(f"No wazn:          {stats['no_wazn_total']}")
    print("  reasons:")
    for reason, count in sorted(stats["reasons"].items(), key=lambda x: -x[1]):
        print(f"    {reason:25s} {count:6d}")
    print("Root length distribution:")
    for length, count in sorted(stats["by_root_len"].items()):
        print(f"  len={length}: {count}")
    print()
    print(f"OK file:    {OUT_OK}")
    print(f"NO file:    {OUT_NO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
