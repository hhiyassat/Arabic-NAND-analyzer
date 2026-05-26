"""build_maani_quran_corpus.py — وَسم القُرآن بِـ Maani-KB.

يَمُرّ على كُلّ آية في القُرآن (6,236)، يُشَغِّل analyze_verse عَلَيها،
يَستَخرِج maani hits، وَ يَكتُب مُساقًا مَوسومًا.

Package A: ① نَزع البَوادِئ + ② جَذر-أَفعال + ④ كُلّ لاحِقات إِيَّا

مُخرَجات:
  data/maani_quran/maani_quran_corpus.jsonl       — سَطر لِكُلّ آية
  data/maani_quran/maani_quran_by_construction.jsonl — لِكُلّ construction قائِمَة الآيات
  data/maani_quran/maani_quran_stats.md           — تَقرير
  data/maani_quran/maani_quran_no_match.jsonl     — آيات بِلا مُطابَقَة (لِلتَّحَسين)

تَشغيل:
  python3 build_maani_quran_corpus.py
  python3 build_maani_quran_corpus.py --start 1:1 --end 2:286
  python3 build_maani_quran_corpus.py --sample 100  # عَيِّنَة عَشوائيَّة
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from analyze_verse import _load_ayah, analyze_verse, QURAN_TEXT_PATH


PROJECT_ROOT = _HERE.parent
OUT_DIR = PROJECT_ROOT / "data" / "maani_quran"


def _iter_quran_ayahs(start: tuple[int, int] = (1, 1),
                       end: tuple[int, int] = (114, 6)) -> list[tuple[int, int, str]]:
    """يَمُرّ على كُلّ آية بَين البِدايَة وَ النِّهايَة، يُرجِع (surah, ayah, text)."""
    if QURAN_TEXT_PATH is None or not QURAN_TEXT_PATH.exists():
        raise FileNotFoundError("مَلَفّ القُرآن غَير مَوجود")
    ayahs = []
    with open(QURAN_TEXT_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 2)
            if len(parts) != 3:
                continue
            try:
                s, a = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            text = parts[2]
            key = (s, a)
            if key < start or key > end:
                continue
            ayahs.append((s, a, text))
    return ayahs


def _parse_ref(ref: str) -> tuple[int, int]:
    s, a = ref.split(":")
    return int(s), int(a)


def build_corpus(start_ref: str = "1:1", end_ref: str = "114:6",
                  sample: int = None, verbose: bool = True):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = _parse_ref(start_ref)
    end = _parse_ref(end_ref)
    ayahs = _iter_quran_ayahs(start, end)
    if sample:
        import random
        random.seed(42)
        ayahs = random.sample(ayahs, min(sample, len(ayahs)))
        ayahs.sort()

    print(f"  ► آيات لِلمُعالَجَة: {len(ayahs)}")
    print(f"  ► النِّطاق: {start_ref} → {end_ref}")
    if sample:
        print(f"  ► عَيِّنَة: {sample}")
    print()

    corpus_path = OUT_DIR / "maani_quran_corpus.jsonl"
    no_match_path = OUT_DIR / "maani_quran_no_match.jsonl"
    by_constr_path = OUT_DIR / "maani_quran_by_construction.jsonl"

    # نَفتَح المَلَفّات
    corpus_f = open(corpus_path, "w", encoding="utf-8")
    no_match_f = open(no_match_path, "w", encoding="utf-8")

    stats = {
        "total_ayahs": len(ayahs),
        "ayahs_with_hits": 0,
        "ayahs_without_hits": 0,
        "total_hits": 0,
        "by_construction": Counter(),
        "by_extension_type": Counter(),
        "by_surah": defaultdict(int),
        "by_construction_with_ayahs": defaultdict(list),
        "errors": [],
    }

    t0 = time.time()
    for i, (surah, ayah, text) in enumerate(ayahs, 1):
        if verbose and i % 100 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(ayahs) - i) / rate if rate > 0 else 0
            print(f"    [{i}/{len(ayahs)}] {surah}:{ayah}  "
                  f"({rate:.1f}/s، ETA={eta:.0f}s، "
                  f"hits={stats['total_hits']})", flush=True)

        try:
            result = analyze_verse(text, source=f"quran:{surah}:{ayah}")
            hits = (result.get("maani_kb") or {}).get("hits", [])
            tokens = (result.get("tokens") or {}).get("words", [])
        except Exception as e:
            stats["errors"].append({"ref": f"{surah}:{ayah}", "error": str(e)[:200]})
            continue

        record = {
            "surah": surah,
            "ayah": ayah,
            "verse_text": text,
            "n_words": len(tokens),
            "n_hits": len(hits),
            "hits": [
                {
                    "token": h.get("token"),
                    "construction_id": h.get("construction_id"),
                    "construction_title": h.get("construction_title"),
                    "match_type": h.get("match_type"),
                    "matched_lemma": h.get("matched_lemma"),
                    "extension_info": h.get("extension_info", {}),
                    "modality": h.get("modality"),
                    "source_ref": h.get("source_ref"),
                }
                for h in hits
            ],
        }

        corpus_f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if hits:
            stats["ayahs_with_hits"] += 1
            stats["total_hits"] += len(hits)
            stats["by_surah"][surah] += len(hits)
            for h in hits:
                cid = h.get("construction_id", "")
                ext = h.get("match_type", "")
                stats["by_construction"][cid] += 1
                stats["by_extension_type"][ext] += 1
                stats["by_construction_with_ayahs"][cid].append({
                    "surah": surah, "ayah": ayah,
                    "token": h.get("token"),
                    "match_type": ext,
                })
        else:
            stats["ayahs_without_hits"] += 1
            no_match_f.write(json.dumps(
                {"surah": surah, "ayah": ayah, "verse_text": text},
                ensure_ascii=False) + "\n")

    corpus_f.close()
    no_match_f.close()

    # by_construction
    with open(by_constr_path, "w", encoding="utf-8") as f:
        for cid, refs in stats["by_construction_with_ayahs"].items():
            f.write(json.dumps({
                "construction_id": cid,
                "n_ayahs": len(refs),
                "ayahs": refs[:200],  # حَدّ أَعلى لِمَنع تَضَخُّم
            }, ensure_ascii=False) + "\n")

    # تَقرير
    write_stats_report(stats, t0)

    print()
    elapsed = time.time() - t0
    print(f"  ✓ المُساق: {corpus_path}")
    print(f"  ✓ بِلا مُطابَقَة: {no_match_path}")
    print(f"  ✓ بِالتَّركيب: {by_constr_path}")
    print(f"  ◆ {stats['total_hits']} مُطابَقَة في "
          f"{stats['ayahs_with_hits']}/{stats['total_ayahs']} آية "
          f"({stats['ayahs_with_hits']/stats['total_ayahs']*100:.1f}%) "
          f"في {elapsed:.0f}ث")


def write_stats_report(stats: dict, t0: float):
    path = OUT_DIR / "maani_quran_stats.md"
    elapsed = time.time() - t0
    lines = []
    lines.append("# تَقرير وَسم مَعاني النَّحو عَلى القُرآن\n\n")
    lines.append(f"## الإِحصاءات العامَّة\n\n")
    lines.append(f"- الآيات المُعالَجَة: **{stats['total_ayahs']}**\n")
    lines.append(f"- آيات بِمُطابَقَة: **{stats['ayahs_with_hits']}** "
                 f"({stats['ayahs_with_hits']/stats['total_ayahs']*100:.1f}%)\n")
    lines.append(f"- آيات بِلا مُطابَقَة: **{stats['ayahs_without_hits']}**\n")
    lines.append(f"- إِجماليّ المُطابَقات: **{stats['total_hits']}**\n")
    lines.append(f"- مُتَوَسِّط/آية: **{stats['total_hits']/stats['total_ayahs']:.2f}**\n")
    lines.append(f"- وَقت المُعالَجَة: {elapsed:.0f} ثانيَة\n\n")

    lines.append(f"## تَوزيع المُطابَقات على التَّراكيب\n\n")
    for cid, n in stats["by_construction"].most_common():
        lines.append(f"- `{cid}`: **{n}** مُطابَقَة\n")
    lines.append("\n")

    lines.append(f"## تَوزيع حَسَب نَوع التَّمديد\n\n")
    for ext, n in stats["by_extension_type"].most_common():
        lines.append(f"- `{ext}`: **{n}** ({n/stats['total_hits']*100:.1f}%)\n")
    lines.append("\n")

    lines.append(f"## أَكثَر السُّوَر تَنبيهًا (top 20)\n\n")
    surah_sorted = sorted(stats["by_surah"].items(), key=lambda x: -x[1])
    for surah, n in surah_sorted[:20]:
        lines.append(f"- السورَة {surah}: **{n}** مُطابَقَة\n")
    lines.append("\n")

    if stats.get("errors"):
        lines.append(f"## أَخطاء ({len(stats['errors'])})\n\n")
        for err in stats["errors"][:30]:
            lines.append(f"- {err['ref']}: {err['error']}\n")

    path.write_text("".join(lines), encoding="utf-8")
    print(f"  ✓ تَقرير: {path}")


def main():
    ap = argparse.ArgumentParser(description="بِناء مُساق مَعاني النَّحو عَلى القُرآن")
    ap.add_argument("--start", default="1:1", help="آية البِدايَة (سُورَة:آية)")
    ap.add_argument("--end", default="114:6", help="آية النِّهايَة")
    ap.add_argument("--sample", type=int, default=None,
                    help="عَيِّنَة عَشوائيَّة بَدَل المَدى الكامِل")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    build_corpus(
        start_ref=args.start,
        end_ref=args.end,
        sample=args.sample,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
