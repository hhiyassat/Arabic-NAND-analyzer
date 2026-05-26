"""samarrai_quran_sweep.py — مَسح القُرآن كامِلًا بِـ SamarraiAnalyzer.

يَفحَص كُلّ آية في القُرآن (6,236 آية) عَبر الـ KB الجَديدَة (243 قاعِدَة)
وَ يُخرِج:
  • per_verse.csv     — لِكُلّ آية: عَدَد الكَلِمات، التَّغطيَة، الِادِّعاءات، التَّراكيب
  • per_word.csv      — لِكُلّ كَلِمَة مَكشوفَة: المَوضِع، meaning_id، المُجَلَّد
  • constructions.csv — كُلّ التَّراكيب المَكشوفَة (TAQDIM, TAHZHEER...)
  • top_operators.csv — أَكثَر العَوامِل ظُهورًا
  • summary.txt       — تَقرير عامّ

CLI:
  python3 samarrai_quran_sweep.py                        # كامِل القُرآن
  python3 samarrai_quran_sweep.py --max 1000             # أَوَّل 1000 آية
  python3 samarrai_quran_sweep.py --surah 1              # سُورَة واحِدَة
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

from samarrai_analyzer import analyze, kb_stats

QURAN_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani-with-pause-mark.txt"
OUT_DIR = Path(__file__).resolve().parent / "data" / "samarrai_sweep"


def load_quran() -> list[tuple[int, int, str]]:
    """يُحَمِّل القُرآن كَ قائِمَة (سُورَة، آية، نَصّ)."""
    verses = []
    with open(QURAN_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                try:
                    verses.append((int(parts[0]), int(parts[1]), parts[2]))
                except ValueError:
                    continue
    return verses


def run_sweep(max_verses: int | None = None, only_surah: int | None = None) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    verses = load_quran()
    if only_surah:
        verses = [v for v in verses if v[0] == only_surah]
    if max_verses:
        verses = verses[:max_verses]

    print(f"بَدء المَسح: {len(verses)} آية")
    print(f"الـ KB: 243 قاعِدَة في 4 مُجَلَّدات\n")

    per_verse_rows = []
    per_word_rows = []
    construction_rows = []
    operator_counter = Counter()
    topic_counter = Counter()
    construction_counter = Counter()

    total_words = 0
    total_words_matched = 0
    total_claims = 0
    total_constructions = 0

    t0 = time.time()
    for idx, (surah, ayah, text) in enumerate(verses):
        if (idx + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (idx + 1) / elapsed
            eta = (len(verses) - idx - 1) / rate
            print(f"  {idx+1}/{len(verses)} ({rate:.1f} آية/ث، ETA {eta:.0f}s)")

        ta = analyze(text)
        ref = f"{surah}:{ayah}"

        total_words += ta.total_words
        total_words_matched += ta.words_with_match
        verse_claims = sum(len(w.claims) for w in ta.words)
        total_claims += verse_claims
        total_constructions += len(ta.constructions)

        per_verse_rows.append({
            "surah": surah,
            "ayah": ayah,
            "ref": ref,
            "text": text,
            "n_words": ta.total_words,
            "n_words_matched": ta.words_with_match,
            "coverage": round(ta.coverage * 100, 1),
            "n_claims": verse_claims,
            "n_constructions": len(ta.constructions),
        })

        for wa in ta.words:
            for c in wa.claims:
                per_word_rows.append({
                    "ref": ref,
                    "position": wa.position,
                    "word": wa.word,
                    "volume": c.volume,
                    "topic_id": c.topic_id,
                    "meaning_id": c.meaning_id,
                    "operator": c.operator,
                    "vocalized_form": c.vocalized_form,
                    "source_part": c.source_part,
                    "source_page": c.source_page,
                    "confidence": c.confidence,
                })
                if c.operator and c.operator != "—":
                    operator_counter[c.operator] += 1
                topic_counter[c.topic_id] += 1

        for cm in ta.constructions:
            construction_rows.append({
                "ref": ref,
                "construction_id": cm.construction_id,
                "trigger_word": cm.trigger_word,
                "span": ",".join(map(str, cm.span_words)),
                "pattern": cm.pattern_name,
                "source_part": cm.claim.source_part,
                "source_page": cm.claim.source_page,
            })
            construction_counter[cm.construction_id] += 1

    elapsed = time.time() - t0

    # ── كِتابَة المَلَفّات ──
    _write_csv(OUT_DIR / "per_verse.csv", per_verse_rows)
    _write_csv(OUT_DIR / "per_word.csv", per_word_rows)
    _write_csv(OUT_DIR / "constructions.csv", construction_rows)

    top_ops = operator_counter.most_common(50)
    _write_csv(OUT_DIR / "top_operators.csv",
               [{"operator": op, "count": c} for op, c in top_ops])

    top_topics = topic_counter.most_common(50)
    _write_csv(OUT_DIR / "top_topics.csv",
               [{"topic_id": t, "count": c} for t, c in top_topics])

    # ── تَقرير ──
    summary = []
    summary.append("=" * 60)
    summary.append("تَقرير مَسح القُرآن بِـ SamarraiAnalyzer")
    summary.append("=" * 60)
    summary.append(f"\nالآيات المَفحوصَة: {len(verses)}")
    summary.append(f"الزَّمَن: {elapsed:.1f} ثانيَة ({len(verses)/elapsed:.1f} آية/ث)")
    summary.append(f"\n=== تَغطيَة الكَلِمات ===")
    summary.append(f"  إِجماليّ الكَلِمات: {total_words:,}")
    summary.append(f"  الكَلِمات المَكشوفَة: {total_words_matched:,} ({total_words_matched/total_words*100:.1f}%)")
    summary.append(f"  إِجماليّ الِادِّعاءات: {total_claims:,}")
    summary.append(f"  إِجماليّ التَّراكيب: {total_constructions:,}")
    summary.append(f"\n=== التَّراكيب المَكشوفَة ===")
    for cid, n in construction_counter.most_common():
        summary.append(f"  {cid}: {n:,}")
    summary.append(f"\n=== أَكثَر 15 عامِل ===")
    for op, n in operator_counter.most_common(15):
        summary.append(f"  «{op}»: {n:,}")
    summary.append(f"\n=== أَكثَر 15 باب (topic_id) ===")
    for tid, n in topic_counter.most_common(15):
        summary.append(f"  {tid}: {n:,}")
    summary.append(f"\nالمَلَفّات في: {OUT_DIR}")

    summary_text = "\n".join(summary)
    (OUT_DIR / "summary.txt").write_text(summary_text, encoding="utf-8")
    print("\n" + summary_text)

    return {
        "verses": len(verses),
        "words": total_words,
        "words_matched": total_words_matched,
        "claims": total_claims,
        "constructions": total_constructions,
        "elapsed": elapsed,
    }


def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {path.name}: {len(rows):,} صَفًّا")


def main():
    parser = argparse.ArgumentParser(description="مَسح القُرآن بِـ SamarraiAnalyzer")
    parser.add_argument("--max", type=int, help="أَقصى عَدَد آيات (لِلِاختبار)")
    parser.add_argument("--surah", type=int, help="سُورَة واحِدَة فَقَط")
    args = parser.parse_args()
    run_sweep(max_verses=args.max, only_surah=args.surah)


if __name__ == "__main__":
    main()
