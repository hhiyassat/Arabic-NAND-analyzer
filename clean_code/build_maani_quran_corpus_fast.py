"""build_maani_quran_corpus_fast.py — نُسخَة سَريعَة (تُغَطّي 6,236 آيَة في ~10 دَقائق).

تَتَجاوَز M1/Phase C/SpeechFrames/Gender — تَستَخدِم RootPipeline فَقَط لِجَلب الجَذر،
ثُمّ تَستَدعي maani_kb_loader لِلتِقاط المُطابَقات.

Package A: ① نَزع البَوادِئ + ② جَذر-أَفعال + ④ كُلّ لاحِقات إِيَّا

تَشغيل:
  python3 build_maani_quran_corpus_fast.py
  python3 build_maani_quran_corpus_fast.py --start 1:1 --end 2:286
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

import maani_kb_loader
import operators_loader
from analyze_verse import QURAN_TEXT_PATH


# ─── كاش جُذور القُرآن (سَريع جِدًّا) ──────────────────────────────────

_QURAN_ROOTS_CACHE = None


def _load_quran_roots_cache() -> dict[str, str]:
    """يُحَمِّل quran_roots.csv كَ خَريطَة Word → Root."""
    global _QURAN_ROOTS_CACHE
    if _QURAN_ROOTS_CACHE is not None:
        return _QURAN_ROOTS_CACHE
    path = PROJECT_ROOT / "data" / "quran_roots.csv"
    cache = {}
    if path.exists():
        import csv
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get("Word") or row.get("Without_Diacritics") or ""
                root = row.get("Root") or ""
                if word and root:
                    cache[word] = root
                # نُضيف نُسخَة بِلا تَشكيل أَيضًا
                plain = row.get("Without_Diacritics", "")
                if plain and root:
                    cache[plain] = root
    _QURAN_ROOTS_CACHE = cache
    return cache


PROJECT_ROOT = _HERE.parent
OUT_DIR = PROJECT_ROOT / "data" / "maani_quran"

DIACRITICS = "ًٌٍَُِّْـٰٓ"
PAUSE_MARKS = "ۖۗۘۙۚۛۜ۝ۭۢۥۤۧۨ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _strip_pause(s: str) -> str:
    return "".join(c for c in s if c not in PAUSE_MARKS)


def _tokenize(verse: str) -> list[str]:
    """تَقطيع بَسيط — مَسافات فَقَط."""
    cleaned = _strip_pause(verse)
    return [t for t in cleaned.split() if t.strip()]


def _iter_quran_ayahs(start, end):
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
            key = (s, a)
            if key < start or key > end:
                continue
            ayahs.append((s, a, parts[2]))
    return ayahs


def _parse_ref(ref):
    s, a = ref.split(":")
    return int(s), int(a)


def extract_maani_for_verse(verse: str, root_pipeline=None) -> tuple[list[dict], list[str]]:
    """يَلتَقِط maani hits مِن آيَة — سَريع، يَستَخدِم quran_roots.csv كَ كاش."""
    tokens = _tokenize(verse)
    hits = []
    seen_cids = set()
    roots_cache = _load_quran_roots_cache()

    # ① مُطابَقَة الفِعل + نَزع البَوادِئ (مَع الكاش لِلجَذر)
    for token in tokens:
        # نَجلِب الجَذر مِن الكاش
        root = roots_cache.get(token, "")
        if not root:
            root = roots_cache.get(_strip_diac(token), "")

        stripped_token = _strip_diac(token).replace("ٱ", "ا")
        # نُمَرِّر الكَلِمَة الأَصليَّة (مَع التَّشكيل) لِلـ verb filter
        c = maani_kb_loader.lookup_construction_for_verb(token, root=root)
        if c and c["construction_id"] not in seen_cids:
            seen_cids.add(c["construction_id"])
            match_info = c.get("_match_info", {})
            src_refs = c.get("source_refs") or [{}]
            hits.append({
                "token": token,
                "matched_lemma": match_info.get("matched_lemma", ""),
                "match_type": match_info.get("extension_type", "verb_lemma"),
                "construction_id": c["construction_id"],
                "construction_title": c.get("title", ""),
                "source_ref": src_refs[0] if src_refs else {},
            })

    # ② مُطابَقَة بِبادِئَة الكَلِمَة (إِيَّا+لاحِقَة)
    for token in tokens:
        c = maani_kb_loader.lookup_construction_for_word(token)
        if c and c["construction_id"] not in seen_cids:
            seen_cids.add(c["construction_id"])
            match_info = c.get("_match_info", {})
            src_refs = c.get("source_refs") or [{}]
            hits.append({
                "token": token,
                "matched_lemma": match_info.get("matched_prefix", ""),
                "match_type": "pronoun_suffix",
                "pronoun_features": match_info.get("pronoun_features"),
                "construction_id": c["construction_id"],
                "construction_title": c.get("title", ""),
                "source_ref": src_refs[0] if src_refs else {},
            })

    # ③ marker_words (إيا/إنما إلخ)
    word_list = [{"word": t} for t in tokens]
    om_list = maani_kb_loader.lookup_order_pattern_constructions(word_list)
    for om in om_list:
        c = om["construction"]
        if c["construction_id"] in seen_cids:
            continue
        seen_cids.add(c["construction_id"])
        src_refs = c.get("source_refs") or [{}]
        hits.append({
            "token": om["matched_token"],
            "matched_lemma": om["matched_marker"],
            "match_type": "order_pattern",
            "construction_id": c["construction_id"],
            "construction_title": c.get("title", ""),
            "source_ref": src_refs[0] if src_refs else {},
        })

    # ④ العَوامِل الـ 97 (operators_catalog)
    for token in tokens:
        op_match = operators_loader.lookup_in_word(token)
        if op_match is None:
            continue
        cid = f"OP_{op_match['group_id']}_{op_match['operator']}"
        if cid in seen_cids:
            continue
        seen_cids.add(cid)
        hits.append({
            "token": token,
            "matched_lemma": op_match["operator"],
            "match_type": "operator_catalog",
            "construction_id": cid,
            "construction_title": f"عامِل [{op_match['group_ar']}]",
            "purpose": op_match["purpose"],
            "group_id": op_match["group_id"],
            "is_priority": op_match["is_priority"],
            "source_ref": {"book": "operators_catalog", "group": op_match["group_id"]},
        })

    return hits, tokens


def build_corpus(start_ref="1:1", end_ref="114:6", sample=None, verbose=True):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = _parse_ref(start_ref)
    end = _parse_ref(end_ref)
    ayahs = _iter_quran_ayahs(start, end)
    if sample:
        import random
        random.seed(42)
        ayahs = random.sample(ayahs, min(sample, len(ayahs)))
        ayahs.sort()

    print(f"  ► آيات: {len(ayahs)}")
    print(f"  ► نِطاق: {start_ref} → {end_ref}")
    print(f"  ► تَحميل RootPipeline...")
    root_pipeline = RootPipeline()
    print()

    corpus_path = OUT_DIR / "maani_quran_corpus.jsonl"
    no_match_path = OUT_DIR / "maani_quran_no_match.jsonl"
    by_constr_path = OUT_DIR / "maani_quran_by_construction.jsonl"

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
    }

    t0 = time.time()
    for i, (surah, ayah, text) in enumerate(ayahs, 1):
        if verbose and i % 200 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(ayahs) - i) / rate if rate > 0 else 0
            print(f"    [{i}/{len(ayahs)}] {surah}:{ayah}  "
                  f"({rate:.1f}/s، ETA={eta:.0f}s، "
                  f"hits={stats['total_hits']})", flush=True)

        try:
            hits, tokens = extract_maani_for_verse(text, root_pipeline)
        except Exception as e:
            corpus_f.write(json.dumps({
                "surah": surah, "ayah": ayah, "verse_text": text,
                "error": str(e)[:200]
            }, ensure_ascii=False) + "\n")
            continue

        record = {
            "surah": surah, "ayah": ayah, "verse_text": text,
            "n_words": len(tokens),
            "n_hits": len(hits),
            "hits": hits,
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

    with open(by_constr_path, "w", encoding="utf-8") as f:
        for cid, refs in stats["by_construction_with_ayahs"].items():
            f.write(json.dumps({
                "construction_id": cid,
                "n_ayahs": len(refs),
                "ayahs": refs[:500],
            }, ensure_ascii=False) + "\n")

    write_stats_report(stats, t0)

    elapsed = time.time() - t0
    print()
    print(f"  ◆ {stats['total_hits']} مُطابَقَة في "
          f"{stats['ayahs_with_hits']}/{stats['total_ayahs']} آية "
          f"({stats['ayahs_with_hits']/stats['total_ayahs']*100:.1f}%) "
          f"في {elapsed:.0f}ث")
    print(f"  ◆ {corpus_path}")


def write_stats_report(stats, t0):
    path = OUT_DIR / "maani_quran_stats.md"
    elapsed = time.time() - t0
    lines = [
        "# تَقرير وَسم مَعاني النَّحو عَلى القُرآن (Fast)\n\n",
        f"## الإِحصاءات\n\n",
        f"- الآيات: **{stats['total_ayahs']}**\n",
        f"- آيات بِمُطابَقَة: **{stats['ayahs_with_hits']}** "
        f"({stats['ayahs_with_hits']/stats['total_ayahs']*100:.1f}%)\n",
        f"- إِجماليّ المُطابَقات: **{stats['total_hits']}**\n",
        f"- مُتَوَسِّط/آية: **{stats['total_hits']/stats['total_ayahs']:.2f}**\n",
        f"- وَقت: {elapsed:.0f}ث ({elapsed/stats['total_ayahs']*1000:.0f}ms/آيَة)\n\n",
        f"## التَّوزيع على التَّراكيب\n\n",
    ]
    for cid, n in stats["by_construction"].most_common():
        lines.append(f"- `{cid}`: **{n}**\n")
    lines.append("\n## تَوزيع نَوع التَّمديد (Package A)\n\n")
    for ext, n in stats["by_extension_type"].most_common():
        pct = n/stats['total_hits']*100 if stats['total_hits'] else 0
        lines.append(f"- `{ext}`: **{n}** ({pct:.1f}%)\n")
    lines.append("\n## أَكثَر السُّوَر تَنبيهًا (top 20)\n\n")
    for surah, n in sorted(stats["by_surah"].items(), key=lambda x: -x[1])[:20]:
        lines.append(f"- سورة {surah}: **{n}**\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"  ✓ تَقرير: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1:1")
    ap.add_argument("--end", default="114:6")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    build_corpus(args.start, args.end, args.sample, not args.quiet)


if __name__ == "__main__":
    main()
