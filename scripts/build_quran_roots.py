"""build_quran_roots.py — Build CSV of unique Quran words with root + wazn.

Uses the OFFICIAL pipeline (root_pipeline.RootPipeline) which guarantees:
  - Closed-class words NEVER enter the wazn matcher
  - Jalalah forms get the conventional root ءله
  - Open-class words go through alignment + post-processing

FILTER POLICY (per user spec): the output CSV contains ONLY open-class words
(الكلمات المشتقّة التي لها جذر ووزن). Closed-class, jalalah, and no_match
rows are excluded from the file but still counted in stderr stats.

Output: data/quran_roots.csv
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

from root_pipeline import RootPipeline

DIAC = set("ًٌٍَُِّْٰٓٔ")


def strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIAC)


def main():
    print("Loading MASAQ...", file=sys.stderr)
    word_occurrences = Counter()
    with open(ROOT / "data/MASAQ.csv", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            w = row.get("Word", "").strip()
            if w:
                word_occurrences[w] += 1

    print(f"Unique vocalized words: {len(word_occurrences)}", file=sys.stderr)
    print(f"Total word occurrences: {sum(word_occurrences.values())}", file=sys.stderr)

    print("Initializing RootPipeline (official)...", file=sys.stderr)
    pipe = RootPipeline()

    out_path = ROOT / "data/quran_roots.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []      # every analyzed row (for stderr stats only)
    open_rows = []     # only open_class — these go to the CSV
    stats = Counter()
    sorted_words = sorted(word_occurrences.items(), key=lambda kv: (-kv[1], kv[0]))

    for i, (word, count) in enumerate(sorted_words):
        if i % 2000 == 0 and i > 0:
            print(f"  ... {i}/{len(word_occurrences)}", file=sys.stderr)

        analysis = pipe.analyze(word)
        stats[analysis.status] += 1

        row = {
            "Word": word,
            "Without_Diacritics": analysis.word_plain,
            "Count": count,
            "Root": analysis.root if analysis.root else "",
            "Wazn": analysis.wazn if analysis.wazn else "",
            "Status": analysis.status,
            "Source_Of_Claim": analysis.source_of_claim,
        }
        all_rows.append(row)
        # Only open-class words enter the CSV — they are the words that
        # are DERIVED (مشتقّة) and have both root and wazn.
        if analysis.status == "open_class":
            open_rows.append(row)

    # Write CSV — open-class only
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "Word", "Without_Diacritics", "Count",
            "Root", "Wazn", "Status", "Source_Of_Claim",
        ])
        w.writeheader()
        for r in open_rows:
            w.writerow(r)

    total = len(word_occurrences)
    print(f"\n=== Build complete ===")
    print(f"Output: {out_path}")
    print(f"Rows written (open-class only): {len(open_rows)}")
    print(f"Rows excluded: {total - len(open_rows)} "
          f"(closed_class + jalalah + no_match)")
    print(f"\nStatus breakdown (all words seen):")
    for status, n in stats.most_common():
        print(f"  {status:<15} {n:>6}  ({100*n/total:.1f}%)")

    # Top 10 most common OPEN-CLASS words
    print(f"\n=== Top 10 most common open-class words (in output) ===")
    open_sorted = sorted(open_rows, key=lambda r: -int(r["Count"]))
    for r in open_sorted[:10]:
        print(f"  [{int(r['Count']):>5}x] {r['Word']:<15} → root={r['Root']:<6} wazn={r['Wazn']}")

    # Top roots
    root_counts = Counter(r["Root"] for r in open_rows)
    print(f"\n=== Top 15 most common open-class roots ===")
    for root, n in root_counts.most_common(15):
        occ = sum(int(r["Count"]) for r in open_rows if r["Root"] == root)
        print(f"  {root:<10} unique_words={n:<4} total_occurrences={occ}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
