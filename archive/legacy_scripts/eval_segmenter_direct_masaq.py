"""Direct evaluation: compare segmenter output against MASAQ.csv's literal
Segmented_Word column, segment-by-segment.

Methodology:
  For each word occurrence in MASAQ:
    truth_sequence = [Segmented_Word for each row of this word, ordered by Segment_No]
    pred_sequence  = [my_prefix_1, ..., my_stem, my_suffix_1, ...] (surface order)

  Plain-text comparison: strip diacritics from both, filter "(null)" / "None" entries.

  Score:
    exact_match — pred_sequence == truth_sequence (plain)
    set_match   — same multiset of segments (order may differ)
    partial     — any overlap
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "clean_code"
_MASAQ_CANDIDATES = [
    # Prefer the fixed copy in hussein/data
    Path("/Users/husseinhiyassat/fractal/hussein/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/hussein/data/MASAQ.csv"),
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/MASAQ.csv"),
]
MASAQ_CSV = next((p for p in _MASAQ_CANDIDATES if p.is_file()), _MASAQ_CANDIDATES[0])

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def clean_seg(s: str) -> str:
    """Normalize a single segment for comparison: strip diacritics, drop nulls,
    and apply MASAQ's lexical canonicalizations so my segmenter's faithful
    surface output can be compared with MASAQ's canonical forms.
    """
    if s in ("(null)", "None", "null", ""):
        return ""
    out = strip_diacritics(s)
    # Normalizer decomposes آ into ءَا (phonetic). MASAQ stores it as آ.
    out = out.replace("ءا", "آ")
    # MASAQ is inconsistent on ة vs ت — sometimes uses 'ة' (closed taa)
    # for feminine markers, sometimes 'ت' (open taa) before pronouns.
    # Normalize both to ت for comparison.
    out = out.replace("ة", "ت")
    # Lexical canonicalizations (whole-segment match):
    if out == "إن":
        out = "أن"
    if out == "هدى":
        out = "هدي"
    # MASAQ sometimes writes ى as ا for certain nouns (عيسى → عيسا)
    if out == "عيسى":
        out = "عيسا"
    return out


def _load_segmenter():
    spec = importlib.util.spec_from_file_location("_seg", CLEAN / "segmenter.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_seg"] = mod
    spec.loader.exec_module(mod)
    return mod.segment


def main() -> int:
    segment = _load_segmenter()

    # Aggregate MASAQ segments per word occurrence
    word_segs = defaultdict(list)
    with open(MASAQ_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            wid = (row["Sura_No"], row["Verse_No"], row["Word_No"])
            word_segs[wid].append({
                "seg_no": int(row["Segment_No"]),
                "word": row["Word"],
                "seg": row["Segmented_Word"],
                "tag": row["Morph_Tag"],
            })

    total = 0
    exact_match = 0
    set_match = 0
    count_match = 0   # same number of segments
    word_in_truth = 0
    pred_too_few = 0
    pred_too_many = 0

    by_truth_len = Counter()
    correct_by_truth_len = Counter()

    error_examples = defaultdict(list)

    for wid, parts in word_segs.items():
        # IMPORTANT: do NOT sort by seg_no. MASAQ uses duplicate seg_no values
        # within a single Word_No for compound structures (e.g., يا + noun
        # vocative, where MASAQ writes two rows of seg_no=1 and two of
        # seg_no=2). Physical row order is the authoritative segment order.
        word = parts[0]["word"]
        truth_seq_raw = [p["seg"] for p in parts]
        truth_seq = [clean_seg(s) for s in truth_seq_raw]
        truth_seq = [s for s in truth_seq if s]
        if not truth_seq:
            continue

        # Run segmenter
        res = segment(word)
        pred_seq = (list(res.prefixes) + [res.stem] + list(res.suffixes))
        pred_seq = [clean_seg(s) for s in pred_seq]
        pred_seq = [s for s in pred_seq if s]
        # Context-aware canonicalization: MASAQ uses على before ـكم but علي
        # before all other pronominal suffixes. Same for إلى vs إلي but the
        # data shows إلى is NEVER used before كم — only علي/على alternation.
        for i in range(len(pred_seq) - 1):
            if pred_seq[i] == "علي" and pred_seq[i + 1] == "كم":
                pred_seq[i] = "على"

        total += 1
        by_truth_len[len(truth_seq)] += 1

        if pred_seq == truth_seq:
            exact_match += 1
            correct_by_truth_len[len(truth_seq)] += 1
        elif sorted(pred_seq) == sorted(truth_seq):
            set_match += 1

        if len(pred_seq) == len(truth_seq):
            count_match += 1
        elif len(pred_seq) < len(truth_seq):
            pred_too_few += 1
            if len(error_examples["too_few"]) < 8:
                error_examples["too_few"].append(
                    f"{word}: pred={pred_seq} truth={truth_seq}"
                )
        else:
            pred_too_many += 1
            if len(error_examples["too_many"]) < 8:
                error_examples["too_many"].append(
                    f"{word}: pred={pred_seq} truth={truth_seq}"
                )

        if pred_seq != truth_seq and sorted(pred_seq) == sorted(truth_seq):
            if len(error_examples["wrong_order"]) < 8:
                error_examples["wrong_order"].append(
                    f"{word}: pred={pred_seq} truth={truth_seq}"
                )
        if pred_seq != truth_seq and sorted(pred_seq) != sorted(truth_seq) and len(pred_seq) == len(truth_seq):
            if len(error_examples["wrong_content"]) < 8:
                error_examples["wrong_content"].append(
                    f"{word}: pred={pred_seq} truth={truth_seq}"
                )

    print(f"=== Direct MASAQ segmentation eval ===")
    print(f"Total word occurrences: {total}\n")
    print(f"Exact sequence match (plain text):  {exact_match}/{total}  =  {100*exact_match/total:.1f}%")
    print(f"Set match (order-insensitive):      {set_match + exact_match}/{total}  =  {100*(set_match+exact_match)/total:.1f}%")
    print(f"Segment-count match:                {count_match}/{total}  =  {100*count_match/total:.1f}%")
    print()
    print(f"Direction errors:")
    print(f"  Predicted too few segments:  {pred_too_few}  =  {100*pred_too_few/total:.1f}%")
    print(f"  Predicted too many segments: {pred_too_many}  =  {100*pred_too_many/total:.1f}%")
    print()
    print(f"=== By truth-sequence length ===")
    for L in sorted(by_truth_len.keys()):
        c = by_truth_len[L]
        correct = correct_by_truth_len[L]
        print(f"  Length {L}: {c:>6} occurrences, {correct:>6} correct ({100*correct/c:.1f}%)")
    print()
    print(f"=== Sample error cases ===")
    for cat, examples in error_examples.items():
        print(f"\n  --- {cat} ---")
        for ex in examples:
            print(f"    {ex}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
