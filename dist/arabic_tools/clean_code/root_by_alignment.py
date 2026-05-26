"""root_by_alignment.py — Extract root by aligning wazn diacritic pattern.

PIPELINE (per user spec):
  1. NORMALIZE     — delegated to clean_code/normalizer.py
                     (NFC, alif madda, lam-shamsi un-assimilation, hamzat wasl)
  2. EXCLUDE       — closed-class words (مبنيات وعوامل) get root=None
  3. ALIGN         — try each wazn as substring; pick best match

ALIGNMENT RULES (per user spec):
  - The wazn is contained INSIDE the word as a substring; chars before/after
    are clitics (و، ف، بال، الـ، هم، ها، إلخ).
  - SUKUN and SHADDA are the most important diacritics — STRICT matching.
  - At the wazn's last position (boundary), the word's diacritic is flexible
    because following suffix may force sukun (e.g., فَعَل + تُمْ → kasab-tum).
  - For ف/ع/ل placeholders, the word's letter at that position is a root letter.

DATA is in clean_code/wazn_data.py.

USAGE:
  python3 root_by_alignment.py             # self-test
  python3 root_by_alignment.py --word كَتَبَ
  python3 root_by_alignment.py --corpus data/MASAQ.csv --limit 5000
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Sibling imports
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from wazn_data import (
    load_awzan,                    # canonical wazn loader (salehan)
    load_closed_class_from_quran,  # closed-class loader (new_arabic_analyzer)
    KNOWN_PREFIX_LETTERS, KNOWN_SUFFIX_LETTERS, BLACKLIST_AWZAN,
    DIACRITICS, SUKUN, SHADDA, HAMZA_VARIANTS, ROOT_PLACEHOLDERS,
)

try:
    from normalizer import normalize_for_root_extraction as _norm_for_root
except ImportError:
    _norm_for_root = None


# ============================================================================
# Normalization (Step 1) — delegate to official normalizer
# ============================================================================

def normalize_word(word: str) -> str:
    """Delegate to the official normalizer's root-extraction mode.

    Applies: NFC + alif-madda + alif-wasla + lam-shamsi un-assimilation
             + hamzat-wasl resolution.
    """
    if not word or _norm_for_root is None:
        return word
    return _norm_for_root(word)


# ============================================================================
# Closed-class exclusion (Step 2)
# ============================================================================

def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _strip_and_normalize_hamza(s: str) -> str:
    """Strip diacritics AND collapse hamza variants to bare ا (for lookup)."""
    s = _strip_diac(s)
    return "".join("ا" if c in HAMZA_VARIANTS and c != "ء" else c for c in s)


_EXCLUSION_SET_CACHE: Optional[set[str]] = None


def _get_exclusion_set() -> set[str]:
    """Combined closed-class set (cached). Stored in TWO forms:
      1. plain diacritic-stripped (e.g., الذين)
      2. normalized stripped (e.g., إلذين — after hamzat-wasl)
    This way lookup works regardless of which form the input arrives in.
    """
    global _EXCLUSION_SET_CACHE
    if _EXCLUSION_SET_CACHE is None:
        _EXCLUSION_SET_CACHE = set()
        for w in load_closed_class_from_quran():
            # Form 1: just diacritic stripped
            _EXCLUSION_SET_CACHE.add(_strip_diac(w))
            # Form 2: after normalize_word (hamzat wasl + lam-shamsi)
            try:
                norm = normalize_word(w)
                _EXCLUSION_SET_CACHE.add(_strip_diac(norm))
            except Exception:
                pass
    return _EXCLUSION_SET_CACHE


def is_closed_class(word: str) -> bool:
    """True if word is in closed-class (has no derivational root).

    Uses diacritic strip ONLY (no hamza normalization) to avoid conflating
    distinct words like آلله (interrogative + الله, tagged HARF) with الله
    (the Divine Name, which DOES have a root).
    """
    return _strip_diac(word) in _get_exclusion_set()


# ============================================================================
# Tokenization — split into (letter, diacritic_cluster) pairs
# ============================================================================

def to_pairs(s: str) -> list[tuple[str, str]]:
    """Split string into [(letter, diacritic_cluster), ...] pairs.

    Special handling: trailing TANWIN ALIF (ـاً) is orthographic — the bare
    ا at end with tanwin-fath diacritic is just a script convention for
    accusative tanwin. We absorb it into the previous letter's diacritic
    so it isn't treated as a root letter.
    """
    pairs = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in DIACRITICS:
            i += 1
            continue
        j = i + 1
        diac = ""
        while j < len(s) and s[j] in DIACRITICS:
            diac += s[j]
            j += 1
        pairs.append((c, diac))
        i = j
    # Post-process: if last pair is (ا, tanwin_fath) AND there's a previous
    # pair, absorb the tanwin into the previous letter's diacritic.
    TANWIN_FATH = "ً"
    if (len(pairs) >= 2 and pairs[-1][0] == "ا" and
            TANWIN_FATH in pairs[-1][1]):
        prev_letter, prev_diac = pairs[-2]
        new_diac = prev_diac + TANWIN_FATH
        pairs = pairs[:-2] + [(prev_letter, new_diac)]
    return pairs


# ============================================================================
# Diacritic + letter matching rules
# ============================================================================

def _normalize_diac(d: str) -> str:
    """Canonical form of a diacritic cluster (sorted)."""
    return "".join(sorted(d))


def _normalize_letter(c: str) -> str:
    """Hamza variants + bare alif all collapse to "ا"."""
    return "ا" if c in HAMZA_VARIANTS else c


def _letters_match(wazn_letter: str, word_letter: str) -> bool:
    """Hamza variants all match each other."""
    if wazn_letter == word_letter:
        return True
    return _normalize_letter(wazn_letter) == _normalize_letter(word_letter)


def _diacritics_compatible(wazn_diac: str, word_diac: str) -> bool:
    """STRICT matching for sukun and shadda (per user spec).

    - Sukun: must match exactly (presence in both or neither)
    - Shadda: must match exactly + same companion vowel
    - Other vowels: empty side is wildcard
    - Tanwin in word: dropped for comparison (case-ending tolerance)
    """
    TANWIN = {"ً", "ٌ", "ٍ"}  # canonical

    wazn_has_sukun = SUKUN in wazn_diac
    word_has_sukun = SUKUN in word_diac
    if wazn_has_sukun != word_has_sukun:
        return False

    wazn_has_shadda = SHADDA in wazn_diac
    word_has_shadda = SHADDA in word_diac
    if wazn_has_shadda != word_has_shadda:
        return False

    if wazn_has_shadda and word_has_shadda:
        wv = wazn_diac.replace(SHADDA, "")
        wo = word_diac.replace(SHADDA, "")
        wo = "".join(c for c in wo if c not in TANWIN)
        if wv and wo and _normalize_diac(wv) != _normalize_diac(wo):
            return False
        return True

    if wazn_has_sukun:
        return True  # both have sukun, equivalent

    if wazn_diac == "" or word_diac == "":
        return True

    word_d = "".join(c for c in word_diac if c not in TANWIN)
    if not word_d:
        return True

    return _normalize_diac(wazn_diac) == _normalize_diac(word_d)


def _boundary_diacritics_compatible(wazn_diac: str, word_diac: str) -> bool:
    """Lenient check at the wazn substring's BOUNDARY (last position).

    When a suffix attaches, the word's last root letter takes sukun
    (e.g., bare wazn فَعَل + suffix تُمْ → فَعَلْتُمْ where ل now has sukun).
    """
    TANWIN = {"ً", "ٌ", "ٍ"}  # canonical

    wazn_has_shadda = SHADDA in wazn_diac
    word_has_shadda = SHADDA in word_diac
    if wazn_has_shadda != word_has_shadda:
        return False

    if wazn_diac == "":
        return True  # boundary: word can have anything

    if SUKUN in wazn_diac:
        return SUKUN in word_diac

    if SUKUN in word_diac:
        return False  # wazn has explicit vowel but word has sukun

    if word_diac == "":
        return True

    word_d = "".join(c for c in word_diac if c not in TANWIN)
    if not word_d:
        return True

    return _normalize_diac(wazn_diac) == _normalize_diac(word_d)


# ============================================================================
# Alignment — try wazn as substring in word
# ============================================================================

@dataclass
class AlignmentResult:
    wazn: str
    root: str
    length: int               # wazn letter positions
    prefix_len: int = 0
    suffix_len: int = 0
    transformations: list = field(default_factory=list)

    @property
    def clitic_count(self) -> int:
        return self.prefix_len + self.suffix_len


def _normalize_for_clitic_check(s: str) -> str:
    """Collapse hamza variants to ا for clitic comparison."""
    return "".join("ا" if c in HAMZA_VARIANTS and c != "ء" else c for c in s)


def _expand_defective_root(root_letters: list[str], wazn_pairs: list) -> list[str]:
    """Defective-root expansion: when wazn ends with و/ي/ى/ا as a LITERAL
    (non-placeholder) and root has fewer letters than expected, the final
    weak letter IS the third root letter.

    Mapping: ى → ي, ا → و, و → و, ي → ي.

    Examples:
      wazn=يَفْعَى + word=يَخْشَى  → root=[خ,ش]  → +ي → [خ,ش,ي]
      wazn=يَفْعُو + word=يَدْعُو  → root=[د,ع]  → +و → [د,ع,و]
      wazn=فَاعٍ  + word=دَاعٍ    → root=[د,ع]  → +ي → [د,ع,ي]
    """
    if len(root_letters) >= 3:
        return root_letters  # already 3+ letters
    # Find last placeholder position in wazn
    last_placeholder_idx = -1
    for i, (letter, _) in enumerate(wazn_pairs):
        if letter in ROOT_PLACEHOLDERS:
            last_placeholder_idx = i
    if last_placeholder_idx == -1:
        return root_letters
    # Find LITERAL weak letters AFTER the last placeholder
    final_weaks = []
    for letter, _ in wazn_pairs[last_placeholder_idx + 1:]:
        if letter in ("ى", "ا", "و", "ي"):
            final_weaks.append(letter)
    if not final_weaks:
        return root_letters
    # Use the LAST weak letter — that's the root's missing letter
    final = final_weaks[-1]
    # Mapping rule: ى → ي, ا → و
    if final == "ى":
        return root_letters + ["ي"]
    if final == "ا":
        return root_letters + ["و"]
    return root_letters + [final]


def _expand_hollow_root(root_letters: list[str], wazn_pairs: list) -> list[str]:
    """Hollow-root expansion: when wazn has ا as LITERAL in MIDDLE position
    between two placeholders and root has only 2 letters, the ا represents
    a weak middle letter (و or ي).

    Default: assume و (more common in Arabic). If word's vowel context
    suggests ي, return ي variant.

    Examples:
      wazn=فَال + word=قَال → root=[ق,ل] → +و → [ق,و,ل] (root قول)
    """
    if len(root_letters) >= 3:
        return root_letters
    if len(root_letters) != 2:
        return root_letters
    # Look for ا between two placeholders
    pos_placeholders = []
    pos_alif_after_first = -1
    for i, (letter, _) in enumerate(wazn_pairs):
        if letter in ROOT_PLACEHOLDERS:
            pos_placeholders.append(i)
        elif letter == "ا" and len(pos_placeholders) == 1:
            pos_alif_after_first = i
    if (pos_alif_after_first > 0 and len(pos_placeholders) == 2 and
            pos_placeholders[1] > pos_alif_after_first):
        # ا is between placeholder 1 and 2 → hollow middle
        return [root_letters[0], "و", root_letters[1]]
    return root_letters


def _expand_doubled_root(root_letters: list[str], wazn_pairs: list) -> list[str]:
    """Doubled-root expansion rule (RESTRICTED to Form I doubled surface).

    Fires ONLY when:
      - The wazn has EXACTLY 2 root placeholders (فَعَّ, يَفَعُّ, etc.)
      - One of those placeholders has shadda (indicating doubling)

    Does NOT fire for:
      - Form II (فَعَّل) — 3 placeholders, shadda is for the form
      - Form V (تَفَعَّل) — 3 placeholders, shadda is for the form
      - Form II AP (مُفَعِّل) — 3 placeholders
      - Any wazn with 3+ placeholders

    Examples (FIRES):
      wazn=فَعَّ + word=رَدَّ      → root=[ر, د]  → expanded=[ر, د, د]
      wazn=يَفَعُّ + word=يَوَدُّوا → root=[و, د]  → expanded=[و, د, د]
    Examples (NO EXPANSION):
      wazn=فَعَّل + word=كَلَّم  → root=[ك, ل, م]  (Form II, NOT doubled)
    """
    # Count root placeholders in the wazn
    n_placeholders = sum(1 for letter, _ in wazn_pairs if letter in ROOT_PLACEHOLDERS)
    if n_placeholders != 2:
        return root_letters  # only expand for 2-placeholder wazns (Form I doubled)

    # Apply expansion: duplicate the placeholder letter that has shadda
    expanded = list(root_letters)
    root_idx = 0
    insert_offset = 0
    for letter, diac in wazn_pairs:
        if letter in ROOT_PLACEHOLDERS:
            if SHADDA in diac and root_idx < len(root_letters):
                insert_at = root_idx + insert_offset + 1
                expanded.insert(insert_at, root_letters[root_idx])
                insert_offset += 1
            root_idx += 1
    return expanded


def align(word: str, wazn: str) -> Optional[AlignmentResult]:
    """Try to align `wazn` as a substring of `word` at any position.

    Returns the best AlignmentResult (fewest clitics) or None.
    Applies doubled-root expansion when the wazn has shadda on a placeholder.
    """
    word_pairs = to_pairs(word)
    wazn_pairs = to_pairs(wazn)

    if len(wazn_pairs) > len(word_pairs):
        return None

    best = None

    for start in range(len(word_pairs) - len(wazn_pairs) + 1):
        root_letters: list[str] = []
        ok = True
        last_idx = len(wazn_pairs) - 1
        for i, (wazn_letter, wazn_diac) in enumerate(wazn_pairs):
            word_letter, word_diac = word_pairs[start + i]
            is_last = (i == last_idx)
            has_suffix_after = (start + len(wazn_pairs) < len(word_pairs))

            # Boundary-tolerant on last wazn position when suffix follows
            check_fn = (_boundary_diacritics_compatible
                        if (is_last and has_suffix_after)
                        else _diacritics_compatible)
            if not check_fn(wazn_diac, word_diac):
                ok = False
                break

            if wazn_letter in ROOT_PLACEHOLDERS:
                root_letters.append(word_letter)
            else:
                if not _letters_match(wazn_letter, word_letter):
                    ok = False
                    break

        if not ok:
            continue

        prefix_len = start
        suffix_len = len(word_pairs) - start - len(wazn_pairs)

        # Validate clitics
        prefix_letters = "".join(p for p, _ in word_pairs[:prefix_len])
        suffix_letters = "".join(p for p, _ in word_pairs[start + len(wazn_pairs):])
        prefix_norm = _normalize_for_clitic_check(prefix_letters)
        suffix_norm = _normalize_for_clitic_check(suffix_letters)
        prefix_valid = (prefix_len == 0 or
                        prefix_letters in KNOWN_PREFIX_LETTERS or
                        prefix_norm in KNOWN_PREFIX_LETTERS)
        suffix_valid = (suffix_len == 0 or
                        suffix_letters in KNOWN_SUFFIX_LETTERS or
                        suffix_norm in KNOWN_SUFFIX_LETTERS)
        if not (prefix_valid and suffix_valid):
            continue

        # Apply rule-based post-processing in priority order:
        # 1. Doubled-root expansion (for شَدَّ، فَعَّ patterns)
        # 2. Hollow-root expansion (for قَال، فَال patterns)
        # 3. Defective-root expansion (for رَمَى، يَفْعَى patterns)
        final_root = _expand_doubled_root(root_letters, wazn_pairs)
        if len(final_root) == 2:
            final_root = _expand_hollow_root(final_root, wazn_pairs)
        if len(final_root) == 2:
            final_root = _expand_defective_root(final_root, wazn_pairs)
        result = AlignmentResult(
            wazn=wazn,
            root="".join(final_root),
            length=len(wazn_pairs),
            prefix_len=prefix_len,
            suffix_len=suffix_len,
            transformations=[
                f"matched at position {start}",
                f"prefix={prefix_letters!r}, suffix={suffix_letters!r}",
                f"doubled_expanded" if len(final_root) > len(root_letters) else "no_expansion",
            ],
        )
        if best is None or result.clitic_count < best.clitic_count:
            best = result

    return best


# ============================================================================
# WaznAligner — picks best match across all awzan
# ============================================================================

def _wazn_specificity(wazn: str) -> tuple[int, int]:
    """(length, literal_letter_count). Higher = more specific."""
    pairs = to_pairs(wazn)
    literal = sum(1 for p, _ in pairs if p not in ROOT_PLACEHOLDERS)
    return (len(pairs), literal)


class WaznAligner:
    """Picks the best wazn alignment across a corpus of awzan."""

    def __init__(self, awzan: list[str]):
        awzan = [w for w in set(awzan) if w not in BLACKLIST_AWZAN]
        # Normalize awzan list (so hamzat-wasl wazns also match normalized words)
        normalized = set(awzan)
        for w in awzan:
            n = normalize_word(w)
            if n != w:
                normalized.add(n)
        awzan = list(normalized)
        # Sort by specificity (longer + more anchors first)
        self.awzan = sorted(awzan, key=lambda w: (
            -_wazn_specificity(w)[0], -_wazn_specificity(w)[1]
        ))

    def extract(self, word: str) -> Optional[AlignmentResult]:
        """Pipeline: normalize → jalalah-override → exclude → align.

        Returns None for closed-class words OR if no wazn aligns.

        Ranking among matches (priorities):
          1. Prefer 3-letter (or 4-letter) ROOT — rooted in trilateral/quad system
          2. Fewer clitics (most of word covered by wazn)
          3. Longest wazn (more specific morphology)
          4. Most literal anchor letters in wazn
        """
        # Jalalah short-circuit (data-driven عَبر SingularTermDetector).
        # كانَ سابِقًا inline list هنا — أُلغِيَ. كُلّ القَواعد في
        # data/contracts/lists/singular_terms*.csv.
        from singular_term_detector import get_singular_term_detector
        if get_singular_term_detector().detect(word).is_singular_term:
            return None

        word = normalize_word(word)
        if is_closed_class(word):
            return None

        candidates = []
        for wazn in self.awzan:
            r = align(word, wazn)
            if r:
                candidates.append(r)
        if not candidates:
            return None

        def _root_size_penalty(r):
            """Penalize roots not of standard length 3 or 4.
            Standard: 3-letter (triliteral) and 4-letter (quadriliteral) roots.
            Returns: 0 if 3-letter, 1 if 4-letter, 10 if other (penalized).
            """
            n = len(r.root)
            if n == 3: return 0
            if n == 4: return 1
            if n == 2: return 2  # doubled but didn't expand — borderline
            return 10  # off-standard, penalize

        candidates.sort(key=lambda r: (
            _root_size_penalty(r),       # prefer standard root lengths
            r.clitic_count,              # fewer clitics
            -r.length,                   # longer wazn
            -_wazn_specificity(r.wazn)[1],  # more literal anchors
        ))
        return candidates[0]

    def extract_all(self, word: str) -> list[AlignmentResult]:
        """Return ALL successful alignments (longest first)."""
        word = normalize_word(word)
        if is_closed_class(word):
            return []
        results = [r for r in (align(word, w) for w in self.awzan) if r]
        results.sort(key=lambda r: -r.length)
        return results


# ============================================================================
# Loading awzan from CSV
# ============================================================================

def load_awzan_from_csv(path: Path) -> list[str]:
    """Load awzan from a CSV file (col: الوزن).

    DEPRECATED: prefer wazn_data.load_awzan() which uses the canonical path.
    Kept for --awzan-from CLI flag (custom path).
    """
    awzan = []
    if not path.is_file():
        return awzan
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            wz = row.get("الوزن", "").strip()
            if wz:
                awzan.append(wz)
    return list(set(awzan))


# ============================================================================
# Self-test + CLI
# ============================================================================

_TEST_CASES = [
    ("كَتَبَ", "كتب"),
    ("يَكْتُبُ", "كتب"),
    ("مَكْتُوب", "كتب"),
    ("اسْتَخْرَج", "خرج"),
    ("يَنْصُرُونَ", "نصر"),
    ("سَمِعَ", "سمع"),
    ("مُجْتَهِد", "جهد"),
    ("اقْتَرَب", "قرب"),
    ("أَكْبَر", "كبر"),
    ("كَاتِب", "كتب"),
    ("اسْتَغْفِر", "غفر"),
    ("كَسَبْتُمْ", "كسب"),
    ("رَدَّ", "ردد"),       # doubled root expanded
    ("مُسْتَفْعِل", "فعل"),
    ("مُنْكَسِر", "كسر"),
    ("اكْتُبْ", "كتب"),
]

_CLOSED_CLASS_TESTS = ["هَذَا", "الَّذِي", "هُوَ", "فِي", "إِنَّ"]


def _self_test():
    print("=== root_by_alignment self-test ===\n")
    awzan = load_awzan()  # canonical loader from wazn_data
    print(f"Loaded {len(awzan)} awzan from salehan/awzan_cleaned.csv\n")
    aligner = WaznAligner(awzan)

    n_pass = n_fail = 0
    for word, expected_root in _TEST_CASES:
        r = aligner.extract(word)
        ok = r and r.root == expected_root
        mark = "✓" if ok else "✗"
        if ok:
            n_pass += 1
        else:
            n_fail += 1
        got = r.root if r else "—"
        wz = r.wazn if r else "—"
        print(f"  {mark} {word} → root={got} (wazn={wz}), expected={expected_root}")

    print(f"\n  --- Closed-class (must return None) ---")
    for word in _CLOSED_CLASS_TESTS:
        r = aligner.extract(word)
        ok = (r is None)
        mark = "✓" if ok else "✗"
        if ok:
            n_pass += 1
        else:
            n_fail += 1
        print(f"  {mark} {word} → {'None' if r is None else r.root}")

    print(f"\n{n_pass} passed, {n_fail} failed")
    return n_fail == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", help="Single word test")
    ap.add_argument("--awzan-from", help="Path to awzan_cleaned.csv")
    ap.add_argument("--corpus", help="Path to MASAQ-like CSV to evaluate")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--show-all", action="store_true",
                    help="Show all matched awzan for the word")
    ap.add_argument("--sample-unmatched", action="store_true")
    args = ap.parse_args()

    # Load awzan (canonical path unless --awzan-from overrides)
    if args.awzan_from:
        awzan_path = Path(args.awzan_from)
        awzan = load_awzan_from_csv(awzan_path)
        print(f"Loaded {len(awzan)} awzan from {awzan_path.name}", file=sys.stderr)
    else:
        awzan = load_awzan()
        print(f"Loaded {len(awzan)} awzan from canonical salehan/awzan_cleaned.csv",
              file=sys.stderr)
    aligner = WaznAligner(awzan)

    if args.word:
        if args.show_all:
            results = aligner.extract_all(args.word)
            if results:
                print(f"word={args.word}  ({len(results)} matches)")
                for r in results[:8]:
                    print(f"  wazn={r.wazn:<20} root={r.root}")
            else:
                print(f"NO MATCH (or closed-class) for {args.word!r}")
        else:
            r = aligner.extract(args.word)
            if r:
                print(f"word={args.word}")
                print(f"  wazn:   {r.wazn}")
                print(f"  root:   {r.root}")
                print(f"  length: {r.length} positions")
                print(f"  clitics: prefix={r.prefix_len} suffix={r.suffix_len}")
            else:
                print(f"NO MATCH (or closed-class) for {args.word!r}")
        return 0

    if args.corpus:
        from collections import Counter
        words = set()
        with open(args.corpus, encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get("Word"):
                    words.add(row["Word"])
        words_list = list(words)[:args.limit]
        print(f"Evaluating {len(words_list)} unique words...", file=sys.stderr)
        stats = Counter()
        unmatched_sample = []
        for w in words_list:
            r = aligner.extract(w)
            if r:
                stats["matched"] += 1
            elif is_closed_class(normalize_word(w)):
                stats["excluded_closed_class"] += 1
            else:
                stats["unmatched"] += 1
                if args.sample_unmatched and len(unmatched_sample) < 20:
                    unmatched_sample.append(w)
        total = len(words_list)
        print(f"\n=== Eval results ===")
        for k, n in stats.most_common():
            print(f"  {k}: {n} ({100*n/total:.1f}%)")
        if unmatched_sample:
            print(f"\nUnmatched samples:")
            for w in unmatched_sample:
                print(f"  {w}")
        return 0

    _self_test()


if __name__ == "__main__":
    sys.exit(main())
