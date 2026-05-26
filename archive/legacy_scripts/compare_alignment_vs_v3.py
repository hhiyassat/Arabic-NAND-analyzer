"""Compare root_by_alignment vs wazn_matcher_v3 on full MASAQ.

Ground truth: mishkat_word_root.csv (Quranic word→root mapping by Eqratech).

Outputs:
  - Summary stats per tool
  - Cases where alignment is RIGHT but v3 wrong (alignment_wins)
  - Cases where v3 is RIGHT but alignment wrong (v3_wins)
  - Cases where BOTH are wrong (both_wrong)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

# Import both tools
from root_by_alignment import WaznAligner, normalize_word, is_closed_class
from wazn_data import load_awzan
from wazn_matcher_v3 import AnalyzerV3
import segmenter

# Constants
DIAC = set("ًٌٍَُِّْٰٓٔ")
HAMZA_VARIANTS = {"أ", "إ", "ؤ", "ئ", "آ", "ٱ"}


def strip_diac(s):
    return "".join(c for c in s if c not in DIAC)


def normalize_root(r):
    """Normalize a root for comparison: strip diacritics, fold hamza to ء."""
    if not r:
        return ""
    r = strip_diac(r)
    out = []
    for c in r:
        if c in HAMZA_VARIANTS:
            out.append("ء")
        elif c == "ا":
            out.append("ء")  # treat bare alif as ء for comparison
        else:
            out.append(c)
    return "".join(out)


def roots_match(r1: str, r2: str) -> bool:
    """Compare two roots tolerantly.

    Rules:
      1. Exact match after hamza normalization
      2. Doubled match: if one is 2 chars and other is 3 chars where last 2 are same
         e.g., "رد" vs "ردد" → match
      3. Order match: same letters in same order (for noun roots like سمو/سوم)
    """
    n1 = normalize_root(r1)
    n2 = normalize_root(r2)
    if n1 == n2:
        return True
    # Doubled root: 2-letter result vs 3-letter expected (LLL where last two same)
    if len(n1) == 2 and len(n2) == 3 and n2[1] == n2[2] and n1 == n2[:2]:
        return True
    if len(n2) == 2 and len(n1) == 3 and n1[1] == n1[2] and n2 == n1[:2]:
        return True
    return False


def load_mishkat_ground_truth() -> dict[str, str]:
    """Load mishkat_word_root.csv → {word_plain: root}."""
    path = Path("/sessions/nice-epic-cannon/mnt/hussein/clean_code/data/mishkat_word_root.csv")
    if not path.is_file():
        path = Path("/Users/husseinhiyassat/fractal/hussein/clean_code/data/mishkat_word_root.csv")
    if not path.is_file():
        path = Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/mishkat_word_root.csv")
    if not path.is_file():
        return {}
    out = {}
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            w = strip_diac(row["word"])
            out[w] = row["root"]
    return out


def main():
    print("Loading MASAQ...", file=sys.stderr)
    masaq_words = set()
    with open("/sessions/nice-epic-cannon/mnt/hussein/data/MASAQ.csv", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("Word"):
                masaq_words.add(row["Word"])

    print(f"MASAQ unique words: {len(masaq_words)}", file=sys.stderr)

    print("Loading mishkat ground truth...", file=sys.stderr)
    mishkat = load_mishkat_ground_truth()
    print(f"Mishkat words with roots: {len(mishkat)}", file=sys.stderr)

    print("Initializing alignment + v3...", file=sys.stderr)
    awzan = load_awzan()
    aligner = WaznAligner(awzan)
    v3 = AnalyzerV3()

    # Categorize
    counts = Counter()
    align_wins = []
    v3_wins = []
    both_wrong = []
    both_right = []
    no_ground_truth = 0

    print(f"Comparing {len(masaq_words)} words...", file=sys.stderr)
    for i, w in enumerate(masaq_words):
        if i % 5000 == 0 and i > 0:
            print(f"  ... {i}/{len(masaq_words)}", file=sys.stderr)

        plain = strip_diac(w)
        expected = mishkat.get(plain)

        # Skip closed-class
        w_norm = normalize_word(w)
        if is_closed_class(w_norm):
            counts["excluded_closed_class"] += 1
            continue

        if not expected:
            counts["no_ground_truth"] += 1
            no_ground_truth += 1
            continue

        # Run alignment
        align_r = aligner.extract(w)
        align_root = align_r.root if align_r else None

        # Run v3
        seg = segmenter.segment(w)
        v3_results = v3.analyze(seg.stem)
        v3_root = v3_results[0].root if v3_results else None
        v3_verified = v3_results[0].in_mishkat if v3_results else False

        # Score
        align_correct = align_root and roots_match(align_root, expected)
        v3_correct = v3_root and roots_match(v3_root, expected)

        if align_correct and v3_correct:
            counts["both_right"] += 1
            both_right.append((w, expected, align_root, v3_root))
        elif align_correct and not v3_correct:
            counts["alignment_wins"] += 1
            if len(align_wins) < 25:
                align_wins.append((w, expected, align_root, v3_root))
        elif not align_correct and v3_correct:
            counts["v3_wins"] += 1
            if len(v3_wins) < 25:
                v3_wins.append((w, expected, align_root, v3_root))
        else:
            counts["both_wrong"] += 1
            if len(both_wrong) < 25:
                both_wrong.append((w, expected, align_root, v3_root))

    # Compute accuracy excluding closed-class and no-ground-truth
    compared = (counts["both_right"] + counts["alignment_wins"] +
                counts["v3_wins"] + counts["both_wrong"])

    print()
    print("=" * 60)
    print("COMPARISON: root_by_alignment vs wazn_matcher_v3")
    print("=" * 60)
    print(f"\nTotal MASAQ unique words:       {len(masaq_words)}")
    print(f"Excluded (closed-class):        {counts['excluded_closed_class']}  ({100*counts['excluded_closed_class']/len(masaq_words):.1f}%)")
    print(f"No ground truth in mishkat:     {counts['no_ground_truth']}  ({100*counts['no_ground_truth']/len(masaq_words):.1f}%)")
    print(f"Comparable cases:               {compared}  ({100*compared/len(masaq_words):.1f}%)")
    print()
    print(f"  Both right:                   {counts['both_right']}  ({100*counts['both_right']/compared:.1f}% of comparable)")
    print(f"  Alignment wins (v3 wrong):    {counts['alignment_wins']}  ({100*counts['alignment_wins']/compared:.1f}%)")
    print(f"  v3 wins (alignment wrong):    {counts['v3_wins']}  ({100*counts['v3_wins']/compared:.1f}%)")
    print(f"  Both wrong:                   {counts['both_wrong']}  ({100*counts['both_wrong']/compared:.1f}%)")

    align_total_right = counts["both_right"] + counts["alignment_wins"]
    v3_total_right = counts["both_right"] + counts["v3_wins"]
    print()
    print(f"=== ACCURACY ===")
    print(f"  root_by_alignment correct:    {align_total_right}/{compared}  ({100*align_total_right/compared:.1f}%)")
    print(f"  wazn_matcher_v3 correct:      {v3_total_right}/{compared}  ({100*v3_total_right/compared:.1f}%)")
    diff = align_total_right - v3_total_right
    print(f"  ΔΔ alignment - v3 = {diff:+d} ({100*diff/compared:+.1f} percentage points)")

    print()
    print(f"=== SAMPLE: Alignment wins ===")
    for w, exp, ar, vr in align_wins[:15]:
        print(f"  {w:<20} expected={exp:<6}  align={ar or '—':<6} v3={vr or '—'}")

    print()
    print(f"=== SAMPLE: v3 wins ===")
    for w, exp, ar, vr in v3_wins[:15]:
        print(f"  {w:<20} expected={exp:<6}  align={ar or '—':<6} v3={vr or '—'}")

    print()
    print(f"=== SAMPLE: Both wrong ===")
    for w, exp, ar, vr in both_wrong[:10]:
        print(f"  {w:<20} expected={exp:<6}  align={ar or '—':<6} v3={vr or '—'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
