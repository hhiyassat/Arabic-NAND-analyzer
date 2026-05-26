"""test_operators_samples.py — اختبار 102 جُملَة عَوامِل بِـ SamarraiAnalyzer.

يَقرَأ `sample_operators_test.txt` (102 جُملَة مُشَكَّلَة) وَ يَفحَص كُلّ جُملَة
بِالمُحَلِّل الجَديد، ثُمّ يُخرِج:
  • تَقرير لِكُلّ جُملَة (عَدَد الكَلِمات، التَّغطيَة، أَبرَز topic)
  • مُلَخَّص عامّ + CSV نَتائِج

CLI:
  python3 test_operators_samples.py                # كُلّ الجُمَل + تَقرير
  python3 test_operators_samples.py --verbose      # كامِل الِادِّعاءات
  python3 test_operators_samples.py --line 6       # جُملَة واحِدَة (6 = «وَاللَّهِ لَأَشْرَبَنَّ»)
  python3 test_operators_samples.py --csv          # حِفظ النَّتائِج في CSV فَقَط
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from samarrai_analyzer import analyze, format_analysis

SAMPLES = Path(__file__).resolve().parent / "sample_operators_test.txt"
OUT_CSV = Path(__file__).resolve().parent / "data" / "samarrai_sweep" / "operators_samples_results.csv"


def load_samples() -> list[str]:
    lines = []
    with open(SAMPLES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def run(verbose: bool = False, only_line: int | None = None, csv_only: bool = False):
    sentences = load_samples()
    print(f"=== اختبار {len(sentences)} جُملَة بِـ SamarraiAnalyzer ===\n")

    rows = []
    topic_counter = Counter()
    construction_counter = Counter()
    total_words = 0
    total_matched = 0
    total_constructions = 0

    for i, sent in enumerate(sentences, 1):
        if only_line and i != only_line:
            continue

        ta = analyze(sent)
        n_claims = sum(len(w.claims) for w in ta.words)

        # أَكثَر topic ظُهورًا في الجُملَة
        topics_here = Counter()
        for w in ta.words:
            for c in w.claims:
                topics_here[c.topic_id] += 1
                topic_counter[c.topic_id] += 1
        top_topic = topics_here.most_common(1)[0][0] if topics_here else "—"

        construction_ids = [cm.construction_id for cm in ta.constructions]
        for cid in construction_ids:
            construction_counter[cid] += 1

        total_words += ta.total_words
        total_matched += ta.words_with_match
        total_constructions += len(ta.constructions)

        # جَمع المَعاني الفِعليَّة (أَوَّل ادِّعاء لِكُلّ كَلِمَة) كَنَصّ
        meanings_per_word = []
        for w in ta.words:
            if w.claims:
                bc = w.best_claim
                if bc:
                    meanings_per_word.append(f"«{w.word}»→{bc.meaning_ar[:60]}")
        meanings_str = " | ".join(meanings_per_word)

        rows.append({
            "line": i,
            "sentence": sent,
            "n_words": ta.total_words,
            "n_matched": ta.words_with_match,
            "coverage": round(ta.coverage * 100, 1),
            "n_claims": n_claims,
            "top_topic": top_topic,
            "constructions": ",".join(construction_ids) or "—",
            "meanings": meanings_str,
        })

        if not csv_only:
            if verbose:
                print(format_analysis(ta, verbose=False))
                print("─" * 60)
            else:
                cov_str = f"{ta.coverage*100:5.1f}%"
                cons_str = f" [{','.join(construction_ids)}]" if construction_ids else ""
                print(f"\n  [{i:3d}] «{sent}»")
                print(f"        {cov_str} ({ta.words_with_match}/{ta.total_words}) | "
                      f"claims={n_claims} | topic={top_topic}{cons_str}")
                if meanings_per_word:
                    for m in meanings_per_word:
                        print(f"        ▸ {m}")

    # ── حِفظ CSV ──
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # ── مُلَخَّص ──
    print()
    print("=" * 60)
    print("=== المُلَخَّص ===")
    print("=" * 60)
    print(f"  الجُمَل: {len(rows)}")
    print(f"  إِجماليّ الكَلِمات: {total_words}")
    print(f"  الكَلِمات المَكشوفَة: {total_matched} ({total_matched/total_words*100:.1f}%)")
    print(f"  التَّراكيب المَكشوفَة: {total_constructions}")
    if construction_counter:
        print(f"\n=== التَّراكيب ===")
        for cid, n in construction_counter.most_common():
            print(f"  {cid}: {n}")
    print(f"\n=== أَكثَر 10 أَبواب (topic_id) ===")
    for tid, n in topic_counter.most_common(10):
        print(f"  {tid}: {n}")
    print(f"\nالنَّتائِج: {OUT_CSV}")


def main():
    p = argparse.ArgumentParser(description="اختبار 102 جُملَة عَوامِل")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--line", type=int, help="جُملَة واحِدَة فَقَط (1-102)")
    p.add_argument("--csv", action="store_true", help="حِفظ CSV فَقَط بِلا طِباعَة")
    args = p.parse_args()
    run(verbose=args.verbose, only_line=args.line, csv_only=args.csv)


if __name__ == "__main__":
    main()
