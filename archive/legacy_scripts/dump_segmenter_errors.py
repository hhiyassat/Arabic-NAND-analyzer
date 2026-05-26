"""Dump all segmenter errors against MASAQ for review.

Outputs:
  - segmenter_errors_full.csv  — every wrong word occurrence
  - segmenter_errors_by_word.csv — unique words, sorted by error count
  - segmenter_errors_categorized.csv — grouped by error type
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "clean_code"

_MASAQ_CANDIDATES = [
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/MASAQ.csv"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/MASAQ.csv"),
]
MASAQ_CSV = next((p for p in _MASAQ_CANDIDATES if p.is_file()), _MASAQ_CANDIDATES[0])

OUT_DIR = ROOT / "clean_code" / "data" / "segmenter_errors"

DIACRITICS = set("ًٌٍَُِّْٰٓٔ")


def strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def clean_seg(s: str) -> str:
    if s in ("(null)", "None", "null", ""):
        return ""
    out = strip_diacritics(s)
    out = out.replace("ءا", "آ")
    if out == "إن":
        out = "أن"
    if out == "هدى":
        out = "هدي"
    return out


def categorize(pred, truth):
    """Classify the type of error."""
    if len(pred) < len(truth):
        return "too_few_segments"
    if len(pred) > len(truth):
        return "too_many_segments"
    if sorted(pred) == sorted(truth):
        return "wrong_order"
    return "wrong_content"


def main() -> int:
    spec = importlib.util.spec_from_file_location("_seg", CLEAN / "segmenter.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_seg"] = mod
    spec.loader.exec_module(mod)
    segment = mod.segment

    OUT_DIR.mkdir(parents=True, exist_ok=True)

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

    # Collect errors
    full_errors = []  # per occurrence
    by_word = Counter()
    by_word_details = {}  # word → (pred, truth, category)
    by_category = Counter()

    total = 0
    for wid, parts in word_segs.items():
        parts.sort(key=lambda p: p["seg_no"])
        word = parts[0]["word"]
        truth_seq_raw = [p["seg"] for p in parts]
        truth_tags = [p["tag"] for p in parts]
        truth = [clean_seg(s) for s in truth_seq_raw]
        truth = [t for t in truth if t]
        if not truth:
            continue
        total += 1
        res = segment(word)
        pred_raw = list(res.prefixes) + [res.stem] + list(res.suffixes)
        pred = [clean_seg(s) for s in pred_raw]
        pred = [p for p in pred if p]
        # على/كم context canonicalization
        for i in range(len(pred) - 1):
            if pred[i] == "علي" and pred[i + 1] == "كم":
                pred[i] = "على"
        if pred == truth:
            continue
        # Error
        category = categorize(pred, truth)
        full_errors.append({
            "sura": wid[0],
            "verse": wid[1],
            "word_no": wid[2],
            "word": word,
            "pred": " | ".join(pred),
            "truth": " | ".join(truth),
            "truth_raw": " | ".join(truth_seq_raw),
            "truth_tags": " | ".join(truth_tags),
            "n_pred": len(pred),
            "n_truth": len(truth),
            "category": category,
        })
        by_word[word] += 1
        if word not in by_word_details:
            by_word_details[word] = (pred, truth, category)
        by_category[category] += 1

    # Write full errors
    full_path = OUT_DIR / "segmenter_errors_full.csv"
    with open(full_path, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "sura", "verse", "word_no", "word",
            "pred", "truth", "truth_raw", "truth_tags",
            "n_pred", "n_truth", "category"
        ])
        w.writeheader()
        for e in full_errors:
            w.writerow(e)

    # Write by-word
    by_word_path = OUT_DIR / "segmenter_errors_by_word.csv"
    with open(by_word_path, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["word", "count", "pred", "truth", "category"])
        for word, count in by_word.most_common():
            pred, truth, cat = by_word_details[word]
            w.writerow([word, count, " | ".join(pred), " | ".join(truth), cat])

    # Write by-category summary
    cat_path = OUT_DIR / "segmenter_errors_by_category.csv"
    with open(cat_path, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "count", "pct_of_total_errors"])
        total_errors = sum(by_category.values())
        for cat, count in by_category.most_common():
            w.writerow([cat, count, f"{100 * count / total_errors:.1f}%"])

    print(f"=== Segmenter error dump ===")
    print(f"Total word occurrences: {total}")
    print(f"Total errors:           {len(full_errors)} ({100 * len(full_errors) / total:.1f}%)")
    print(f"Unique error words:     {len(by_word)}")
    print()
    print(f"=== By category ===")
    for cat, count in by_category.most_common():
        print(f"  {cat:<25} {count:>5} ({100 * count / len(full_errors):.1f}%)")
    print()
    print(f"=== Top 50 error-contributing words ===")
    for word, count in by_word.most_common(50):
        pred, truth, cat = by_word_details[word]
        print(f"  {count:>4} {word:<25} → pred={pred} truth={truth}  [{cat}]")
    print()
    print(f"=== Output files ===")
    print(f"  {full_path}")
    print(f"  {by_word_path}")
    print(f"  {cat_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
