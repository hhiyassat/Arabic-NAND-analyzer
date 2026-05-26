"""end_to_end_test.py — اختبار شامِل لِـ v2 + MASAQ compliance.

3 اختبارات:
  1. samarrai_analyzer v2 عَلى كامِل القُرآن (6,236 آية)
  2. audited_roots_compare عَلى كامِل الـ1,340 مُدَقَّق صَحيح
  3. MASAQ.csv compliance — هَل تَصنيفات المُحَرِّك تُطابِق MASAQ؟

CLI:
  python3 end_to_end_test.py                  # كُلّ الـ3 اختبارات
  python3 end_to_end_test.py --skip-quran     # تَخَطّي القُرآن
  python3 end_to_end_test.py --skip-masaq     # تَخَطّي MASAQ
  python3 end_to_end_test.py --max-quran 1000 # عَيِّنَة قُرآن
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
QURAN_PATH = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
MASAQ_PATH = _HERE.parent / "data" / "MASAQ.csv"
AUDITED_PATH = _HERE / "data" / "audited_roots.csv"
OUT_DIR = _HERE / "data" / "end_to_end_results"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─────────────────────────────────────────────────────────────────
# اختبار 1: samarrai_analyzer v2 عَلى القُرآن
# ─────────────────────────────────────────────────────────────────

def test_quran_samarrai(max_verses: int | None = None) -> dict:
    from samarrai_analyzer import analyze
    print(f"\n{'='*60}")
    print(f"اختبار 1: samarrai_analyzer v2 عَلى القُرآن")
    print(f"{'='*60}")

    verses = []
    with open(QURAN_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                verses.append((int(parts[0]), int(parts[1]), parts[2]))
    if max_verses:
        verses = verses[:max_verses]

    t0 = time.time()
    kind_counter = Counter()
    match_counter = Counter()
    construction_counter = Counter()
    total_words = 0
    total_words_matched = 0
    total_claims = 0
    total_constructions = 0

    for i, (s, a, text) in enumerate(verses):
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(verses)}")
        ta = analyze(text)
        total_words += ta.total_words
        total_words_matched += ta.words_with_match
        total_constructions += len(ta.constructions)
        for wa in ta.words:
            for c in wa.claims:
                kind_counter[c.proof_kind] += 1
                match_counter[c.match_type] += 1
                total_claims += 1
        for cm in ta.constructions:
            construction_counter[cm.construction_id] += 1

    elapsed = time.time() - t0
    coverage = total_words_matched / total_words * 100 if total_words else 0

    print(f"\nالنَّتائِج:")
    print(f"  الآيات: {len(verses):,}")
    print(f"  الكَلِمات: {total_words:,}")
    print(f"  مَكشوفَة: {total_words_matched:,} ({coverage:.1f}%)")
    print(f"  الِادِّعاءات: {total_claims:,}")
    print(f"  التَّراكيب: {total_constructions:,}")
    print(f"  الزَّمَن: {elapsed:.1f}ث ({len(verses)/elapsed:.0f} آية/ث)")
    print(f"\n  تَوزيع ProofKind:")
    for k, n in kind_counter.most_common():
        print(f"    {k:15s}: {n:8,} ({n/total_claims*100:.1f}%)")
    print(f"\n  تَوزيع match_type:")
    for m, n in match_counter.most_common():
        print(f"    {m:25s}: {n:8,} ({n/total_claims*100:.1f}%)")
    print(f"\n  التَّراكيب المَكشوفَة:")
    for cid, n in construction_counter.most_common():
        print(f"    {cid:40s}: {n:5,}")

    return {
        "verses": len(verses),
        "words": total_words,
        "matched": total_words_matched,
        "coverage_pct": coverage,
        "claims": total_claims,
        "constructions": total_constructions,
        "kind_distribution": dict(kind_counter),
        "match_distribution": dict(match_counter),
        "construction_distribution": dict(construction_counter),
        "elapsed_sec": elapsed,
    }


# ─────────────────────────────────────────────────────────────────
# اختبار 2: audited_roots عَلى الـ1,340 مُدَقَّق
# ─────────────────────────────────────────────────────────────────

def test_audited_roots_full() -> dict:
    from audited_roots_compare import _load_audited, analyze_with_engine, compare

    print(f"\n{'='*60}")
    print(f"اختبار 2: audited_roots على كُلّ الـ1,340 مُدَقَّق صَحيح")
    print(f"{'='*60}")

    cache = _load_audited(audited_only=True)
    words = list({e.verb for entries in cache.values() for e in entries if e.verb})
    print(f"  العَدَد: {len(words):,}")

    t0 = time.time()
    status_counter = Counter()
    issue_counter = Counter()
    for i, w in enumerate(words):
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(words)}")
        engine = analyze_with_engine(w)
        cmp = compare(engine)
        status_counter[cmp.status] += 1
        if cmp.issue_type:
            issue_counter[cmp.issue_type] += 1

    elapsed = time.time() - t0
    exact = status_counter["exact_match"]
    any_match = exact + status_counter.get("match_unverified", 0)

    print(f"\nالنَّتائِج:")
    print(f"  الكَلِمات: {len(words):,}")
    print(f"  exact_match: {exact} ({exact/len(words)*100:.1f}%)")
    print(f"  أَيّ تَطابُق: {any_match} ({any_match/len(words)*100:.1f}%)")
    print(f"  الزَّمَن: {elapsed:.1f}ث")
    print(f"\n  تَوزيع الحالات:")
    for s, n in sorted(status_counter.items(), key=lambda x: -x[1]):
        print(f"    {s:25s}: {n:5,}")
    print(f"\n  أَنماط المُشكِلات:")
    for i, n in sorted(issue_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"    {i:25s}: {n:5,}")

    return {
        "total": len(words),
        "exact_pct": exact / len(words) * 100,
        "any_match_pct": any_match / len(words) * 100,
        "status_distribution": dict(status_counter),
        "issue_distribution": dict(issue_counter),
        "elapsed_sec": elapsed,
    }


# ─────────────────────────────────────────────────────────────────
# اختبار 3: MASAQ.csv compliance — تَوافُق التَّصنيفات
# ─────────────────────────────────────────────────────────────────

def _load_masaq_mapping() -> dict[str, dict]:
    """يُحَمِّل خَريطَة MASAQ → نَوع مُتَوَقَّع مِن CSV (MC: لا inline)."""
    import csv as _csv
    path = _HERE / "data" / "contracts" / "rules" / "masaq_tag_mapping.csv"
    if not path.exists():
        raise RuntimeError(
            "Zero: لَم نَجِد masaq_tag_mapping.csv. MC: لا inline fallback."
        )
    mapping: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            tag = row.get("masaq_tag", "").strip()
            if tag:
                mapping[tag] = {
                    "expected_class": row.get("expected_engine_class", "").strip(),
                    "scenario": row.get("test_scenario", "").strip(),
                    "description": row.get("description", "").strip(),
                }
    return mapping


def test_masaq_compliance(max_words: int = 5000) -> dict:
    """يُقارِن تَصنيف الكَلِمات في MASAQ مَع المُحَرِّك.

    Contract: masaq_tag_mapping.csv يُحَدِّد كُلّ tag وَ السيناريو المُتَوَقَّع.
    """
    print(f"\n{'='*60}")
    print(f"اختبار 3: MASAQ.csv compliance test")
    print(f"{'='*60}")

    try:
        from closed_class_detector import is_closed_class
        from jamid_detector import is_jamid
    except ImportError as e:
        print(f"  ⚠ تَخَطّي — {e}")
        return {"skipped": True, "reason": str(e)}

    mapping = _load_masaq_mapping()
    print(f"  خَريطَة: {len(mapping)} tag مِن masaq_tag_mapping.csv")

    masaq_words = []
    with open(MASAQ_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            w = r.get("Word", "").strip()
            tag = r.get("Morph_Tag", "").strip()
            if w and tag:
                masaq_words.append((w, tag))
            if len(masaq_words) >= max_words:
                break

    print(f"  العَيِّنَة: {len(masaq_words):,} كَلِمَة")

    # سيناريو 1: closed_class_positive
    closed_total = closed_correct = 0
    closed_misses: list = []
    # سيناريو 2: jamid_positive
    jamid_total = jamid_correct = 0
    jamid_misses: list = []
    # سيناريو 3: verb_negative
    verb_total = verb_wrong = 0
    verb_misses: list = []

    for w, tag in masaq_words:
        rule = mapping.get(tag)
        if not rule:
            continue
        scenario = rule["scenario"]
        if scenario == "closed_class_positive":
            closed_total += 1
            if is_closed_class(w):
                closed_correct += 1
            elif len(closed_misses) < 10:
                closed_misses.append((w, tag))
        elif scenario == "jamid_positive":
            jamid_total += 1
            if is_jamid(w):
                jamid_correct += 1
            elif len(jamid_misses) < 10:
                jamid_misses.append((w, tag))
        elif scenario == "verb_negative":
            verb_total += 1
            if is_closed_class(w) or is_jamid(w):
                verb_wrong += 1
                if len(verb_misses) < 10:
                    verb_misses.append((w, tag))
    verb_correct = verb_total - verb_wrong

    print(f"\nالنَّتائِج:")
    print(f"\n  Closed-class (PREP/CONJ/DET/PRON...):")
    print(f"    المَجموع: {closed_total}")
    if closed_total:
        print(f"    المُحَرِّك يَكشِف: {closed_correct} ({closed_correct/closed_total*100:.1f}%)")
        if closed_misses:
            print(f"    عَيِّنَة فَوَّت: {closed_misses[:5]}")
    print(f"\n  Jamid (NOUN_CONCRETE):")
    print(f"    المَجموع: {jamid_total}")
    if jamid_total:
        print(f"    المُحَرِّك يَكشِف: {jamid_correct} ({jamid_correct/jamid_total*100:.1f}%)")
        if jamid_misses:
            print(f"    عَيِّنَة فَوَّت: {jamid_misses[:5]}")
    print(f"\n  Verbs (PV/IV) — يَجِب أَن لا تَكون closed أَو jamid:")
    print(f"    المَجموع: {verb_total}")
    if verb_total:
        print(f"    صَحيح: {verb_correct} ({verb_correct/verb_total*100:.1f}%)")
        if verb_misses:
            print(f"    عَيِّنَة خَطَأ: {verb_misses[:5]}")

    return {
        "sample_size": len(masaq_words),
        "closed_class": {
            "total": closed_total, "correct": closed_correct,
            "pct": closed_correct / closed_total * 100 if closed_total else 0,
        },
        "jamid": {
            "total": jamid_total, "correct": jamid_correct,
            "pct": jamid_correct / jamid_total * 100 if jamid_total else 0,
        },
        "verb_negative": {
            "total": verb_total, "correct": verb_correct,
            "pct": verb_correct / verb_total * 100 if verb_total else 0,
        },
    }


# ─────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skip-quran", action="store_true")
    p.add_argument("--skip-audited", action="store_true")
    p.add_argument("--skip-masaq", action="store_true")
    p.add_argument("--max-quran", type=int)
    p.add_argument("--max-masaq", type=int, default=5000)
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}

    if not args.skip_quran:
        summary["quran"] = test_quran_samarrai(args.max_quran)
    if not args.skip_audited:
        summary["audited"] = test_audited_roots_full()
    if not args.skip_masaq:
        summary["masaq_compliance"] = test_masaq_compliance(args.max_masaq)

    # حِفظ JSON
    import json
    out = OUT_DIR / "summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n\n=== مُلَخَّص مَحفوظ في {out} ===")


if __name__ == "__main__":
    main()
