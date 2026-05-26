"""Evaluate clean_code/segmenter.py against MASAQ segmentation truth.

Comparison metric:
  For each unique word in MASAQ:
    - MASAQ truth: (prefix_plain, stem_plain, suffix_plain)
      where _plain means diacritic-stripped.
    - Segmenter output: (prefix_plain, stem_plain, suffix_plain) similarly.
  Score:
    full_match    — all three components match exactly
    stem_only     — stem matches, prefixes/suffixes may differ
    prefix_only   — prefix list matches as plain text
    suffix_only   — suffix list matches
    no_segments   — both have no peels (single-stem words)

Usage:
  python3 eval_segmenter_on_masaq.py
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "clean_code"

MASAQ_TRUTH = CLEAN / "data" / "masaq_segmentation_truth.csv"

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    seg_mod = _load_module(CLEAN / "segmenter.py", "_seg")
    segment = seg_mod.segment

    if not MASAQ_TRUTH.is_file():
        print(f"MASAQ truth file not found: {MASAQ_TRUTH}", file=sys.stderr)
        return 1

    total = 0
    full_match = 0
    stem_match = 0
    prefix_match = 0
    suffix_match = 0
    no_seg_both = 0
    no_seg_truth = 0
    no_seg_pred = 0
    overseg = 0  # we strip; truth doesn't
    underseg = 0  # truth strips; we don't

    # Bucket breakdown
    by_truth_shape = Counter()  # (n_prefixes, n_suffixes) → count
    by_pred_shape = Counter()
    correct_by_truth_shape = Counter()

    # Detailed error categories
    error_examples = defaultdict(list)

    with open(MASAQ_TRUTH, encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)

    for row in rows:
        word = row["word"]
        truth_pref = [p for p in row["prefixes"].split("|") if p]
        truth_stem = row["stem"]
        truth_suff = [s for s in row["suffixes"].split("|") if s]
        freq = int(row["frequency"])

        # Segmenter output
        res = segment(word)
        pred_pref_plain = [strip_diacritics(p) for p in res.prefixes]
        pred_stem_plain = strip_diacritics(res.stem)
        pred_suff_plain = [strip_diacritics(s) for s in res.suffixes]

        # MASAQ truth segments are already diacritic-stripped (mostly).
        # Normalize "(null)" / "None" to empty.
        def _clean_masaq_seg(s):
            if s in ("(null)", "None", "null"):
                return ""
            return strip_diacritics(s)

        truth_pref_plain = [_clean_masaq_seg(p) for p in truth_pref]
        truth_pref_plain = [p for p in truth_pref_plain if p]
        truth_stem_plain = _clean_masaq_seg(truth_stem)
        truth_suff_plain = [_clean_masaq_seg(s) for s in truth_suff]
        truth_suff_plain = [s for s in truth_suff_plain if s]

        total += freq

        truth_shape = (len(truth_pref_plain), len(truth_suff_plain))
        pred_shape = (len(pred_pref_plain), len(pred_suff_plain))
        by_truth_shape[truth_shape] += freq
        by_pred_shape[pred_shape] += freq

        p_eq = (pred_pref_plain == truth_pref_plain)
        s_eq = (pred_suff_plain == truth_suff_plain)
        stem_eq = (pred_stem_plain == truth_stem_plain)

        if p_eq and s_eq and stem_eq:
            full_match += freq
            correct_by_truth_shape[truth_shape] += freq
        if stem_eq:
            stem_match += freq
        if p_eq:
            prefix_match += freq
        if s_eq:
            suffix_match += freq

        if not truth_pref_plain and not truth_suff_plain:
            no_seg_truth += freq
        if not pred_pref_plain and not pred_suff_plain:
            no_seg_pred += freq
        if (not truth_pref_plain and not truth_suff_plain
                and not pred_pref_plain and not pred_suff_plain):
            no_seg_both += freq

        # Error classification
        if truth_pref_plain == [] and pred_pref_plain != []:
            overseg += freq
            if len(error_examples["overseg_prefix"]) < 10:
                error_examples["overseg_prefix"].append(
                    f"{word}: pred_pref={pred_pref_plain} truth=∅"
                )
        elif truth_pref_plain != [] and pred_pref_plain == []:
            underseg += freq
            if len(error_examples["underseg_prefix"]) < 10:
                error_examples["underseg_prefix"].append(
                    f"{word}: pred_pref=∅ truth={truth_pref_plain}"
                )
        elif truth_pref_plain != pred_pref_plain:
            if len(error_examples["mismatch_prefix"]) < 10:
                error_examples["mismatch_prefix"].append(
                    f"{word}: pred={pred_pref_plain} truth={truth_pref_plain}"
                )

    print(f"=== Segmenter eval on MASAQ ({total} word occurrences, {len(rows)} unique) ===\n")
    print(f"Full match (prefix + stem + suffix): {full_match}/{total}  =  {100*full_match/total:.1f}%")
    print(f"Stem-only match (plain stem equal):  {stem_match}/{total}  =  {100*stem_match/total:.1f}%")
    print(f"Prefix list match:                   {prefix_match}/{total}  =  {100*prefix_match/total:.1f}%")
    print(f"Suffix list match:                   {suffix_match}/{total}  =  {100*suffix_match/total:.1f}%")
    print()
    print(f"No-segmentation cases:")
    print(f"  Both agree (no peels): {no_seg_both}/{total}  =  {100*no_seg_both/total:.1f}%")
    print(f"  MASAQ has no peels:    {no_seg_truth}/{total}  =  {100*no_seg_truth/total:.1f}%")
    print(f"  Segmenter no peels:    {no_seg_pred}/{total}  =  {100*no_seg_pred/total:.1f}%")
    print()
    print(f"Direction errors:")
    print(f"  Over-segmentation (we peel; MASAQ doesn't): {overseg}/{total}  =  {100*overseg/total:.1f}%")
    print(f"  Under-segmentation (MASAQ peels; we don't): {underseg}/{total}  =  {100*underseg/total:.1f}%")
    print()
    print(f"=== By truth shape (n_prefixes, n_suffixes) ===")
    for shape, c in sorted(by_truth_shape.items(), key=lambda x: -x[1])[:10]:
        correct = correct_by_truth_shape[shape]
        print(f"  {shape}: {c:>6} occurrences, {correct:>6} fully correct ({100*correct/c:.1f}%)")
    print()
    print(f"=== Sample error cases ===")
    for cat, examples in error_examples.items():
        print(f"\n  --- {cat} ({len(examples)} shown) ---")
        for ex in examples[:8]:
            print(f"    {ex}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
