"""mishkat_compare.py — طَبَقَة مُقارَنَة Authority مَع مرجِع مشكاة.

يَستَخدِم `data/mishkat_word_root_with_wazn.csv` (≥40,000 كَلِمَة قُرآنيَّة) كَمَرجِع
خارِجيّ لِلتَّحَقُّق مِن نَتائِج المُحَرِّك (root_by_alignment + wazn_matcher).

CONSTITUTIONAL:
  • مشكاة لَيسَت بَديلًا عَن المُحَرِّك — هي Authority Comparison Layer
  • أَيّ اختلاف يُصَنَّف بِنَوع المُشكِلَة لِتَوجيه الإِصلاح
  • النَّتيجَة تَبقى مِن المُحَرِّك، المُقارَنَة لِلتَّقرير فَقَط

CLI:
  python3 mishkat_compare.py "كَتَبَ"                # كَلِمَة واحِدَة
  python3 mishkat_compare.py --file words.txt        # قائِمَة كَلِمات
  python3 mishkat_compare.py --quran-sample 1000     # عَيِّنَة عَشوائيَّة
  python3 mishkat_compare.py --report                # تَقرير CSV كامِل
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
MISHKAT_CSV = _HERE / "data" / "mishkat_word_root_with_wazn.csv"
OUT_CSV = _HERE / "data" / "mishkat_compare_report.csv"

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
# تَحميل مشكاة
# ─────────────────────────────────────────────────────────────────

@dataclass
class MishkatEntry:
    word: str             # الكَلِمَة المُشَكَّلَة
    word_plain: str       # المُجَرَّدَة
    root: str             # الجَذر
    wazn: str             # الوزن الكامِل
    wazn_canonical: str   # الوزن المُختَزَل
    morph_type: str       # noun / verb
    count: int            # تَكرار في القُرآن


_MISHKAT_CACHE: dict[str, list[MishkatEntry]] | None = None


def _load_mishkat() -> dict[str, list[MishkatEntry]]:
    """يُحَمِّل مشكاة كَ index: word_plain → list[MishkatEntry]."""
    global _MISHKAT_CACHE
    if _MISHKAT_CACHE is not None:
        return _MISHKAT_CACHE
    cache: dict[str, list[MishkatEntry]] = {}
    if not MISHKAT_CSV.exists():
        print(f"⚠ مَلَفّ مشكاة غَير مَوجود: {MISHKAT_CSV}", file=sys.stderr)
        _MISHKAT_CACHE = cache
        return cache
    with open(MISHKAT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = _nfc(row.get("word", "").strip())
            word_plain = _normalize(word)
            try:
                count = int(row.get("count", "0") or 0)
            except ValueError:
                count = 0
            entry = MishkatEntry(
                word=word,
                word_plain=word_plain,
                root=row.get("root", "").strip(),
                wazn=row.get("wazn", "").strip(),
                wazn_canonical=row.get("wazn_canonical", "").strip(),
                morph_type=row.get("morph_type", "").strip(),
                count=count,
            )
            cache.setdefault(word_plain, []).append(entry)
            # أَيضًا index بِالكَلِمَة المُشَكَّلَة
            cache.setdefault(word, []).append(entry)
    _MISHKAT_CACHE = cache
    return cache


def mishkat_lookup(word: str) -> list[MishkatEntry]:
    cache = _load_mishkat()
    word_nfc = _nfc(word)
    # مُحاوَلَة المُشَكَّل أَوَّلًا
    if word_nfc in cache:
        return cache[word_nfc]
    # ثُمّ المُجَرَّد
    plain = _normalize(word_nfc)
    return cache.get(plain, [])


# ─────────────────────────────────────────────────────────────────
# المُقارَنَة
# ─────────────────────────────────────────────────────────────────

@dataclass
class EngineResult:
    word: str
    root: Optional[str] = None
    wazn: Optional[str] = None
    pos: Optional[str] = None
    method: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ComparisonResult:
    word: str
    engine: EngineResult
    mishkat: Optional[MishkatEntry]
    root_match: bool
    wazn_match: bool
    pos_match: bool
    status: str             # exact_match / root_match_wazn_diff / etc.
    issue_type: Optional[str] = None  # prefix_seen / hamza / weak_root / form_x / etc.
    fix_hint: Optional[str] = None


def _classify_issue(engine: EngineResult, mishkat: MishkatEntry) -> tuple[Optional[str], Optional[str]]:
    """يُصَنِّف نَوع المُشكِلَة وَ يَقتَرِح إِصلاحًا."""
    if engine.root == mishkat.root and engine.wazn == mishkat.wazn:
        return None, None

    # خَطَأ السين
    if engine.root and mishkat.root:
        if engine.word.startswith(("س", "سَ")) and not mishkat.root.startswith("س"):
            return "seen_prefix_error", "أَضِف الكَلِمَة إلى seen_is_root_lexicon.csv"

    # خَطَأ الهَمزَة
    if engine.root and mishkat.root:
        engine_norm = _normalize(engine.root)
        mishkat_norm = _normalize(mishkat.root)
        if "ا" in mishkat_norm and "و" in engine_norm and not engine_norm == mishkat_norm:
            return "weak_root_error", "أَجوف — تَفَقَّد _expand_hollow_root"

    # خَطَأ Form X
    if engine.word.startswith(("است", "اِست")):
        if engine.root != mishkat.root:
            return "form_x_error", "تَفَقَّد كَشف وزن استفعل"

    # وزن مُختَلِف فَقَط
    if engine.root == mishkat.root and engine.wazn != mishkat.wazn:
        return "wazn_diff_only", "تَفَقَّد wazn matcher — الجذر صَحيح"

    # جذر مُختَلِف فَقَط
    if engine.wazn == mishkat.wazn and engine.root != mishkat.root:
        return "root_diff_only", "تَفَقَّد مَوضِع ف/ع/ل في root_by_alignment"

    return "unknown", "يَحتاج فَحصًا يَدَويًّا"


def compare(engine: EngineResult, prefer_max_count: bool = True) -> ComparisonResult:
    """يُقارِن نَتيجَة المُحَرِّك مَع مشكاة."""
    mishkat_entries = mishkat_lookup(engine.word)

    if not mishkat_entries:
        return ComparisonResult(
            word=engine.word, engine=engine, mishkat=None,
            root_match=False, wazn_match=False, pos_match=False,
            status="not_in_mishkat",
            fix_hint="الكَلِمَة لَيسَت في مشكاة (قَد تَكون خارِج القُرآن)",
        )

    # اختيار أَفضَل entry (أَكثَر تَكرارًا)
    if prefer_max_count:
        mishkat_entries.sort(key=lambda e: -e.count)
    best = mishkat_entries[0]

    root_match = (engine.root == best.root) if engine.root else False
    wazn_match = (engine.wazn == best.wazn or engine.wazn == best.wazn_canonical) if engine.wazn else False
    pos_match = (engine.pos == best.morph_type) if engine.pos else False

    if root_match and wazn_match and pos_match:
        status = "exact_match"
    elif root_match and not wazn_match:
        status = "root_match_wazn_diff"
    elif wazn_match and not root_match:
        status = "wazn_match_root_diff"
    elif root_match:
        status = "root_match_only"
    else:
        status = "full_mismatch"

    issue_type, fix_hint = _classify_issue(engine, best)

    return ComparisonResult(
        word=engine.word, engine=engine, mishkat=best,
        root_match=root_match, wazn_match=wazn_match, pos_match=pos_match,
        status=status, issue_type=issue_type, fix_hint=fix_hint,
    )


# ─────────────────────────────────────────────────────────────────
# واجَهَة المُحَرِّك (يُمكِن استِبدالها)
# ─────────────────────────────────────────────────────────────────

def analyze_with_engine(word: str) -> EngineResult:
    """يَستَدعي root_by_alignment لِاستِخراج الجذر + الوزن."""
    try:
        from root_by_alignment import analyze_word
        result = analyze_word(word)
        if result and result.get("root"):
            return EngineResult(
                word=word,
                root=result.get("root"),
                wazn=result.get("wazn"),
                pos=result.get("pos"),
                method="root_by_alignment",
                confidence=float(result.get("confidence", 0.0)),
            )
    except (ImportError, AttributeError):
        pass
    return EngineResult(word=word)


# ─────────────────────────────────────────────────────────────────
# تَقرير مُجَمَّع
# ─────────────────────────────────────────────────────────────────

def run_batch(words: list[str], out_path: Optional[Path] = None) -> dict:
    """يُقارِن قائِمَة كَلِمات وَ يُخرِج تَقريرًا."""
    results = []
    status_counter = Counter()
    issue_counter = Counter()

    for w in words:
        engine = analyze_with_engine(w)
        cmp = compare(engine)
        results.append(cmp)
        status_counter[cmp.status] += 1
        if cmp.issue_type:
            issue_counter[cmp.issue_type] += 1

    # كِتابَة CSV
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "word", "engine_root", "engine_wazn", "engine_pos",
                "mishkat_root", "mishkat_wazn", "mishkat_pos",
                "root_match", "wazn_match", "pos_match",
                "status", "issue_type", "fix_hint",
            ])
            for r in results:
                writer.writerow([
                    r.word,
                    r.engine.root or "", r.engine.wazn or "", r.engine.pos or "",
                    r.mishkat.root if r.mishkat else "",
                    r.mishkat.wazn if r.mishkat else "",
                    r.mishkat.morph_type if r.mishkat else "",
                    r.root_match, r.wazn_match, r.pos_match,
                    r.status, r.issue_type or "", r.fix_hint or "",
                ])

    return {
        "total": len(results),
        "status_distribution": dict(status_counter),
        "issue_distribution": dict(issue_counter),
        "exact_match_pct": status_counter["exact_match"] / len(results) * 100 if results else 0,
    }


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="مُقارَنَة المُحَرِّك مَع مشكاة")
    p.add_argument("word", nargs="?", help="كَلِمَة واحِدَة لِلمُقارَنَة")
    p.add_argument("--file", help="مَلَفّ نَصّيّ بِكَلِمَة في كُلّ سَطر")
    p.add_argument("--quran-sample", type=int, help="عَيِّنَة عَشوائيَّة مِن مشكاة")
    p.add_argument("--report", action="store_true", help="حِفظ تَقرير CSV كامِل")
    args = p.parse_args()

    if args.word:
        engine = analyze_with_engine(args.word)
        cmp = compare(engine)
        print(f"الكَلِمَة: {cmp.word}")
        print(f"المُحَرِّك:  جذر={cmp.engine.root}  وزن={cmp.engine.wazn}  نَوع={cmp.engine.pos}")
        if cmp.mishkat:
            print(f"مشكاة:    جذر={cmp.mishkat.root}  وزن={cmp.mishkat.wazn}  نَوع={cmp.mishkat.morph_type}")
        print(f"الحالَة:   {cmp.status}")
        if cmp.issue_type:
            print(f"المُشكِلَة: {cmp.issue_type}")
            print(f"الإِصلاح:  {cmp.fix_hint}")
        return

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
    elif args.quran_sample:
        cache = _load_mishkat()
        all_words = list({e.word for entries in cache.values() for e in entries})
        random.seed(42)
        words = random.sample(all_words, min(args.quran_sample, len(all_words)))
    else:
        p.print_help()
        return

    out = OUT_CSV if args.report else None
    stats = run_batch(words, out_path=out)

    print(f"\n=== تَقرير المُقارَنَة ===")
    print(f"  الكُلّيّ: {stats['total']}")
    print(f"  تَطابُق كامِل: {stats['exact_match_pct']:.1f}%")
    print(f"\n  تَوزيع الحالات:")
    for s, n in sorted(stats['status_distribution'].items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")
    print(f"\n  تَوزيع المُشكِلات:")
    for i, n in sorted(stats['issue_distribution'].items(), key=lambda x: -x[1]):
        print(f"    {i}: {n}")
    if out:
        print(f"\n  التَّقرير: {out}")


if __name__ == "__main__":
    main()
