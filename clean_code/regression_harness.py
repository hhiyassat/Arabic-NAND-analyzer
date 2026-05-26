#!/usr/bin/env python3
"""regression_harness.py — قِياس accuracy ضِدّ MASAQ.

يُقَدِّم لِكُلّ token في القُرآن:
  expected (MASAQ) vs predicted (Layer 1 classifier)

يُبَلِّغ:
  • accuracy إِجماليّ
  • تَوزيع المُطابَقَة لِكُلّ word_class
  • أَوَّل N regression cases (mismatches)

CLI:
  python3 regression_harness.py [--sample 1000] [--detail]
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from i3rab_engine.layer1 import WordClassClassifier
from build_master_token_table import masaq_tag_to_word_class

HERE = Path(__file__).resolve().parent
MASAQ = HERE.parent / "data" / "MASAQ.csv"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=0,
                   help="فَقَط أَوَّل N word entries (0 = كُلّ)")
    p.add_argument("--detail", action="store_true",
                   help="اطبَع كُلّ mismatch")
    p.add_argument("--max-mismatches", type=int, default=20,
                   help="أَقصى عَدَد mismatches لِلطِّباعَة")
    p.add_argument("--out", default="regression_report.csv",
                   help="مَلَفّ CSV لِكَتابَة mismatches")
    args = p.parse_args()

    clf = WordClassClassifier()
    total = 0
    correct = 0
    by_class_correct = defaultdict(int)
    by_class_total = defaultdict(int)
    mismatches = []
    source_dist = Counter()
    confusion = defaultdict(lambda: Counter())

    print(f"Loading MASAQ from {MASAQ}…")
    # نَجمَع الكَلِمات الفَريدَة (Stem segment فَقَط، لِكُلّ word)
    seen_words = {}
    with MASAQ.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Morph_Type") != "Stem":
                continue
            key = (int(row.get("Sura_No", 0)),
                   int(row.get("Verse_No", 0)),
                   int(row.get("Word_No", 0)))
            if key in seen_words:
                continue
            seen_words[key] = row

    items = list(seen_words.values())
    if args.sample > 0:
        items = items[:args.sample]
    print(f"Evaluating {len(items)} tokens…\n")

    for i, row in enumerate(items):
        if i and i % 5000 == 0:
            print(f"  …{i}/{len(items)}  (accuracy so far: {correct/total*100:.1f}%)")
        surface = (row.get("Word") or "").strip()
        if not surface:
            continue
        expected_tag = (row.get("Morph_Tag") or "").strip()
        expected_wc = masaq_tag_to_word_class(expected_tag)
        if expected_wc == "UNKNOWN":
            continue  # تَخَطَّى تَصنيفات غَير مَعروفَة

        result = clf.classify(surface)
        predicted_wc = result.get("word_class", "UNKNOWN")
        src = result.get("source", "")
        source_dist[src.split(":")[0] or "unknown"] += 1

        total += 1
        by_class_total[expected_wc] += 1
        if predicted_wc == expected_wc:
            correct += 1
            by_class_correct[expected_wc] += 1
        else:
            confusion[expected_wc][predicted_wc] += 1
            if len(mismatches) < args.max_mismatches * 5:
                mismatches.append({
                    "surah": row.get("Sura_No"),
                    "ayah": row.get("Verse_No"),
                    "word_idx": row.get("Word_No"),
                    "surface": surface,
                    "expected": expected_wc,
                    "expected_tag": expected_tag,
                    "predicted": predicted_wc,
                    "source": src,
                })

    print()
    print("=" * 70)
    print(f"REGRESSION REPORT — {len(items)} MASAQ tokens")
    print("=" * 70)
    print(f"\nOverall accuracy:  {correct}/{total} = {correct/total*100:.2f}%\n")

    print("Per-class accuracy:")
    for wc in sorted(by_class_total.keys()):
        c = by_class_correct[wc]; t = by_class_total[wc]
        print(f"  {wc:<14s}  {c}/{t} = {c/t*100:5.1f}%")

    print("\nSource distribution (where Layer 1 got its answer):")
    for src, n in source_dist.most_common(10):
        print(f"  {src:<30s} {n} ({n/total*100:.1f}%)")

    print(f"\nTop confusions (expected → predicted):")
    flat = []
    for exp, preds in confusion.items():
        for pred, n in preds.items():
            flat.append((n, exp, pred))
    flat.sort(reverse=True)
    for n, exp, pred in flat[:10]:
        print(f"  {n:4d}  {exp:<14s} → {pred}")

    # Write CSV
    out_path = HERE / args.out
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "surah","ayah","word_idx","surface","expected","expected_tag",
            "predicted","source"])
        w.writeheader()
        for m in mismatches:
            w.writerow(m)
    print(f"\n✓ Wrote {len(mismatches)} mismatches to {out_path}")

    if args.detail:
        print(f"\nFirst {min(args.max_mismatches, len(mismatches))} mismatches:")
        for m in mismatches[:args.max_mismatches]:
            print(f"  {m['surah']}:{m['ayah']}:{m['word_idx']} "
                  f"{m['surface']:<22s} exp={m['expected']:<14s} "
                  f"got={m['predicted']:<14s} src={m['source'][:30]}")


if __name__ == "__main__":
    main()
