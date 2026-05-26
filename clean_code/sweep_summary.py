#!/usr/bin/env python3
"""sweep_summary.py — مُلَخَّص مَشبوه لِنَتائج المَسح.

CLI:
  python3 sweep_summary.py sweep_v4.jsonl

يَطبَع:
  • top suspicious word classes
  • top suspicious relations
  • worst entropy verse
  • failed verses
  • contradictions count
"""
import json
import sys
from collections import Counter


def main(path):
    total = 0
    errors = 0
    anom_kind = Counter()
    anom_token = Counter()
    worst_entropy = (None, -1.0)
    contradictions = 0
    failed_verses = []
    no_relations = 0
    no_events = 0
    verses_seen = set()
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            key = (d.get("surah",0), d.get("ayah",0))
            if key in verses_seen:
                continue
            verses_seen.add(key)
            total += 1
            if not d.get("i3rab_ok", True):
                errors += 1
                failed_verses.append(f"{key[0]}:{key[1]}")
            if d.get("relations", 0) == 0:
                no_relations += 1
            if d.get("events", 0) == 0:
                no_events += 1
            ent = d.get("meaning_entropy", d.get("entropy", 0))
            if isinstance(ent, (int, float)) and ent > worst_entropy[1]:
                worst_entropy = (f"{key[0]}:{key[1]}", ent)
            if d.get("contradictions", 0):
                contradictions += d["contradictions"]
            for a in d.get("anomalies", []):
                kind = a.split(":")[0]
                anom_kind[kind] += 1
                if ":" in a:
                    anom_token[a] += 1
    print(f"\n=== Sweep Summary: {path} ===")
    print(f"Verses analyzed:      {total}")
    print(f"i3rab errors:         {errors}")
    print(f"No relations:         {no_relations}")
    print(f"No events:            {no_events}")
    print(f"Contradictions:       {contradictions}")
    print(f"Worst entropy verse:  {worst_entropy[0]} (entropy={worst_entropy[1]:.2f})")
    print()
    print("=== Top suspicious anomaly KINDS ===")
    for k, n in anom_kind.most_common(10):
        print(f"  {n:5d}  {k}")
    print()
    print("=== Top suspicious tokens (full anomaly:token) ===")
    for tok, n in anom_token.most_common(15):
        print(f"  {n:5d}  {tok}")
    print()
    print(f"=== Failed verses ({len(failed_verses)}) ===")
    for v in failed_verses[:15]:
        print(f"  {v}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sweep_v4.jsonl")
