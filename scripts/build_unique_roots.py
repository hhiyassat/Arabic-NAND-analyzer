"""build_unique_roots.py — Build CSV of unique roots with one example each.

Input:  data/quran_roots.csv (open-class derived words only).
Output: data/quran_unique_roots.csv with columns:

    Root                    — the root (e.g., كتب)
    Example_Word            — most-frequent surface form for this root
    Example_Wazn            — wazn of the example
    Example_Count           — occurrences of the example surface
    Unique_Words            — number of distinct surface forms for this root
    Total_Occurrences       — sum of Count across all forms of this root

Sorted by Total_Occurrences descending.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / "data" / "quran_roots.csv"
OUT_PATH = ROOT / "data" / "quran_unique_roots.csv"


def main() -> int:
    if not IN_PATH.is_file():
        print(f"error: input not found: {IN_PATH}", file=sys.stderr)
        return 1

    # root -> list of (count, word, wazn)
    per_root: dict[str, list[tuple[int, str, str]]] = defaultdict(list)

    with IN_PATH.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            root = (row.get("Root") or "").strip()
            word = (row.get("Word") or "").strip()
            wazn = (row.get("Wazn") or "").strip()
            try:
                cnt = int((row.get("Count") or "0").strip())
            except ValueError:
                cnt = 0
            if not root or not word:
                continue
            per_root[root].append((cnt, word, wazn))

    # Build summary rows
    rows = []
    for root, items in per_root.items():
        # Sort by count desc, then word for stability
        items.sort(key=lambda t: (-t[0], t[1]))
        top_cnt, top_word, top_wazn = items[0]
        total = sum(c for c, _, _ in items)
        rows.append({
            "Root": root,
            "Example_Word": top_word,
            "Example_Wazn": top_wazn,
            "Example_Count": top_cnt,
            "Unique_Words": len(items),
            "Total_Occurrences": total,
        })

    rows.sort(key=lambda r: (-r["Total_Occurrences"], r["Root"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "Root", "Example_Word", "Example_Wazn",
            "Example_Count", "Unique_Words", "Total_Occurrences",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"=== Build complete ===")
    print(f"Output: {OUT_PATH}")
    print(f"Unique roots: {len(rows)}")
    print()
    print("=== Top 20 most frequent roots ===")
    print(f"{'Root':<10} {'Example':<18} {'Wazn':<12} {'ExCnt':>6}  {'Forms':>5}  {'Total':>6}")
    print("-" * 70)
    for r in rows[:20]:
        print(
            f"{r['Root']:<10} {r['Example_Word']:<18} {r['Example_Wazn']:<12} "
            f"{r['Example_Count']:>6}  {r['Unique_Words']:>5}  "
            f"{r['Total_Occurrences']:>6}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
