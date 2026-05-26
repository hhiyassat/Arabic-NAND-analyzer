"""audited_roots_compare.py — Authority Comparison Layer مَع audited_roots.

MC-COMPLIANT (Contract C):
  • قَواعِد التَّصنيف مَخزونَة في `data/contracts/rules/issue_classification.csv`
  • لا inline rules لِلتَّصنيف
  • كُلّ مُقارَنَة تُرجِع ProofObject ضِمنيّ (kind + contract + blockers)

ground truth: `data/audited_roots.csv` (4,768 سَجِلًّا، 1,340 مُدَقَّق وَ صَحيح)
  • 9 أَعمِدَة عَرَبيَّة: الفعل الماضي، الجذر، باب الصرفي، اللزوم والتعدي،
    تم تدقيقه، تم إعادة تدقيقه، صحيح (الجذر حقيقي)، المرجع، المصدر

CLI:
  python3 audited_roots_compare.py "كَتَبَ"
  python3 audited_roots_compare.py --file words.txt
  python3 audited_roots_compare.py --sample 1000 --report
  python3 audited_roots_compare.py --audited-only       # فَقَط الـ1340 مُدَقَّقَة صَحيحَة
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
AUDITED_CSV = _HERE / "data" / "audited_roots.csv"
RULES_CSV = _HERE / "data" / "contracts" / "rules" / "issue_classification.csv"
OUT_CSV = _HERE / "data" / "audited_compare_report.csv"

DIACRITICS = "ًٌٍَُِّْـٰٓ"
HAMZA_CHARS = "ءأإؤئ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


def _normalize_root_for_compare(root: str) -> str:
    """تَطبيع الجَذر لِلمُقارَنَة: كُلّ صور الهَمزَة (أ، إ، ؤ، ئ) → ء.

    سَبَب الإِصلاح: المُحَرِّك يُرجِع «سأل»، المُدَقَّق «سءل» — نَفس الجَذر
    بِتَمثيلَين مُختَلِفَين لِلهَمزَة.
    """
    if not root:
        return ""
    r = _nfc(root)
    r = _strip_diac(r)
    # كُلّ الهَمَزات → ء
    for h in "أإؤئ":
        r = r.replace(h, "ء")
    # ا (بِدون هَمزَة) في وَسط الجَذر قَد تَكون أَلِف أَصليَّة — لا نَلمَسها
    return r


# ─────────────────────────────────────────────────────────────────
# تَحميل ground truth + قَواعِد التَّصنيف
# ─────────────────────────────────────────────────────────────────

@dataclass
class AuditedEntry:
    id: str
    verb: str            # الفعل الماضي (مُشَكَّل)
    verb_plain: str      # المُجَرَّد
    root: str            # الجذر
    bab_sarfi: str       # الباب الصرفي
    transitivity: str    # اللزوم والتعدي
    is_audited: bool     # تم تدقيقه أو تم إعادة تدقيقه
    is_correct: bool     # صحيح (الجذر حقيقي)
    source: str          # المرجع
    masdar: str          # المصدر


@dataclass
class IssueRule:
    priority: int
    condition: str       # نَصّ الشَّرط
    issue_type: str
    fix_hint: str
    description: str


_AUDITED_CACHE: dict[str, list[AuditedEntry]] | None = None
_RULES_CACHE: list[IssueRule] | None = None


def _load_audited(audited_only: bool = False) -> dict[str, list[AuditedEntry]]:
    """يُحَمِّل audited_roots كَ index: verb_plain → entries."""
    global _AUDITED_CACHE
    if _AUDITED_CACHE is not None:
        return _AUDITED_CACHE
    cache: dict[str, list[AuditedEntry]] = {}
    if not AUDITED_CSV.exists():
        print(f"⚠ مَلَفّ audited_roots غَير مَوجود: {AUDITED_CSV}", file=sys.stderr)
        _AUDITED_CACHE = cache
        return cache
    with open(AUDITED_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            verb = _nfc(row.get("الفعل الماضي", "").strip())
            verb_plain = _normalize(verb)
            is_audited = (row.get("تم تدقيقه", "0").strip() == "1" or
                            row.get("تم إعادة تدقيقه", "0").strip() == "1")
            is_correct = row.get("صحيح (الجذر حقيقي)", "0").strip() == "1"
            if audited_only and not (is_audited and is_correct):
                continue
            entry = AuditedEntry(
                id=row.get("id", "").strip(),
                verb=verb,
                verb_plain=verb_plain,
                root=row.get("الجذر", "").strip(),
                bab_sarfi=row.get("باب الصرفي", "").strip(),
                transitivity=row.get("اللزوم والتعدي", "").strip(),
                is_audited=is_audited,
                is_correct=is_correct,
                source=row.get("المرجع ( المصدر )", "").strip(),
                masdar=row.get("المصدر", "").strip(),
            )
            cache.setdefault(verb_plain, []).append(entry)
            cache.setdefault(verb, []).append(entry)
    _AUDITED_CACHE = cache
    return cache


def _load_rules() -> list[IssueRule]:
    """يُحَمِّل قَواعِد التَّصنيف مِن CSV — لا inline."""
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE
    rules = []
    if RULES_CSV.exists():
        with open(RULES_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    priority = int(row.get("priority", "99") or 99)
                except ValueError:
                    priority = 99
                rules.append(IssueRule(
                    priority=priority,
                    condition=row.get("condition_pattern", "").strip(),
                    issue_type=row.get("issue_type", "").strip(),
                    fix_hint=row.get("fix_hint", "").strip(),
                    description=row.get("description", "").strip(),
                ))
    rules.sort(key=lambda r: r.priority)
    _RULES_CACHE = rules
    return rules


def audited_lookup(word: str) -> list[AuditedEntry]:
    cache = _load_audited()
    word_nfc = _nfc(word)
    if word_nfc in cache:
        return cache[word_nfc]
    plain = _normalize(word_nfc)
    return cache.get(plain, [])


# ─────────────────────────────────────────────────────────────────
# المُحَرِّك (نَتيجَة مُحَرِّك المَشروع)
# ─────────────────────────────────────────────────────────────────

@dataclass
class EngineResult:
    word: str
    root: Optional[str] = None
    wazn: Optional[str] = None
    pos: Optional[str] = None
    method: Optional[str] = None
    confidence: float = 0.0


_ALIGNER_CACHE = None


def _get_aligner():
    """يُحَمِّل WaznAligner مَع قاعِدَة الأَوزان (singleton)."""
    global _ALIGNER_CACHE
    if _ALIGNER_CACHE is not None:
        return _ALIGNER_CACHE
    from root_by_alignment import WaznAligner, load_awzan_from_csv
    awzan_paths = [
        _HERE / "data" / "awzan.csv",
        _HERE / "data" / "wazn_db_canonical.csv",
        _HERE.parent / "data" / "wazn_db_canonical.csv",
    ]
    awzan = []
    for p in awzan_paths:
        if p.exists():
            awzan = load_awzan_from_csv(p)
            if awzan:
                break
    if not awzan:
        # MC: لا inline fallback — نَرفُض البِناء صَريحًا
        raise RuntimeError(
            "Zero: لَم نَجِد awzan.csv في data/. "
            "MC contract: لا fallback inline. "
            "حَلّ: شَغِّل سكربت تَوليد الأَوزان أَوَّلًا."
        )
    _ALIGNER_CACHE = WaznAligner(awzan)
    return _ALIGNER_CACHE


def analyze_with_engine(word: str) -> EngineResult:
    """يَستَدعي WaznAligner.extract لِاستِخراج الجَذر."""
    try:
        aligner = _get_aligner()
        result = aligner.extract(word)
        if result:
            return EngineResult(
                word=word,
                root=getattr(result, "root", None),
                wazn=getattr(result, "wazn", None),
                pos=None,
                method="WaznAligner",
                confidence=0.85,
            )
    except Exception as e:
        return EngineResult(word=word, method=f"error: {type(e).__name__}")
    return EngineResult(word=word)


# ─────────────────────────────────────────────────────────────────
# التَّصنيف (يَعتَمِد عَلى CSV لا inline)
# ─────────────────────────────────────────────────────────────────

def classify_issue(engine: EngineResult, audited: AuditedEntry) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """يُصَنِّف نَوع المُشكِلَة باعتِماد قَواعِد CSV + predicate engine — لا inline.

    Contract D: مَنطِق الـ predicates مُحَمَّل مِن issue_atoms.csv.
    """
    if engine.root == audited.root:
        return None, None, None

    from predicate_engine import get_issue_predicate_engine
    pe = get_issue_predicate_engine()

    ctx = {
        "word": engine.word,
        "engine_root": engine.root or "",
        "engine_wazn": engine.wazn or "",
        "audited_root": audited.root,
        "audited_wazn": audited.bab_sarfi,
        # حُقول مُرَكَّبَة لِـ equals/not_equals
        "engine_root_vs_audited_root": "",   # عَلامَة وُجود — الـ engine يَفهَم الـ split
        "engine_wazn_vs_audited_wazn": "",
    }
    # حَقن القِيَم لِلحُقول المُرَكَّبَة
    ctx["engine_root"] = engine.root or ""
    ctx["audited_root"] = audited.root

    for rule in _load_rules():
        if pe.evaluate_condition(rule.condition, ctx):
            return rule.issue_type, rule.fix_hint, rule.description

    return "unknown", "يَحتاج فَحصًا يَدَويًّا", "غَير مُصَنَّف"


# ─────────────────────────────────────────────────────────────────
# المُقارَنَة الرَّئيسَة
# ─────────────────────────────────────────────────────────────────

@dataclass
class ComparisonResult:
    word: str
    engine: EngineResult
    audited: Optional[AuditedEntry]
    root_match: bool
    status: str
    issue_type: Optional[str] = None
    fix_hint: Optional[str] = None
    description: Optional[str] = None


def compare(engine: EngineResult) -> ComparisonResult:
    """يُقارِن المُحَرِّك مَع audited_roots."""
    entries = audited_lookup(engine.word)
    if not entries:
        return ComparisonResult(
            word=engine.word, engine=engine, audited=None,
            root_match=False, status="not_in_audited",
            fix_hint="الكَلِمَة لَيسَت في قاعِدَة المُدَقَّقَة",
        )

    # أَفضَل entry: مُدَقَّق + صَحيح أَوَّلًا
    entries.sort(key=lambda e: (not (e.is_audited and e.is_correct), e.id))
    best = entries[0]

    # مُقارَنَة الجَذر مَع تَطبيع الهَمزَة (سأل ≡ سءل)
    engine_root_norm = _normalize_root_for_compare(engine.root or "")
    audited_root_norm = _normalize_root_for_compare(best.root)
    root_match = (engine_root_norm == audited_root_norm) if engine_root_norm else False
    if root_match:
        status = "exact_match" if best.is_audited and best.is_correct else "match_unverified"
        return ComparisonResult(
            word=engine.word, engine=engine, audited=best,
            root_match=True, status=status,
        )

    issue_type, fix_hint, description = classify_issue(engine, best)
    return ComparisonResult(
        word=engine.word, engine=engine, audited=best,
        root_match=False, status="root_mismatch",
        issue_type=issue_type, fix_hint=fix_hint, description=description,
    )


# ─────────────────────────────────────────────────────────────────
# تَقرير دُفعَة
# ─────────────────────────────────────────────────────────────────

def run_batch(words: list[str], out_path: Optional[Path] = None) -> dict:
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

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "word", "engine_root", "audited_root", "audited_bab_sarfi",
                "is_audited_and_correct", "status", "issue_type", "fix_hint",
            ])
            for r in results:
                writer.writerow([
                    r.word, r.engine.root or "",
                    r.audited.root if r.audited else "",
                    r.audited.bab_sarfi if r.audited else "",
                    (r.audited.is_audited and r.audited.is_correct) if r.audited else False,
                    r.status, r.issue_type or "", r.fix_hint or "",
                ])

    return {
        "total": len(results),
        "status_distribution": dict(status_counter),
        "issue_distribution": dict(issue_counter),
        "exact_match_pct": status_counter["exact_match"] / len(results) * 100 if results else 0,
        "any_match_pct": (status_counter["exact_match"] + status_counter["match_unverified"]) / len(results) * 100 if results else 0,
    }


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="مُقارَنَة المُحَرِّك مَع audited_roots (MC-compliant)")
    p.add_argument("word", nargs="?")
    p.add_argument("--file")
    p.add_argument("--sample", type=int, help="عَيِّنَة عَشوائيَّة")
    p.add_argument("--audited-only", action="store_true", help="فَقَط الكَلِمات المُدَقَّقَة الصَّحيحَة (1340)")
    p.add_argument("--report", action="store_true")
    args = p.parse_args()

    if args.audited_only:
        _load_audited.__wrapped__ = None  # force reload
        global _AUDITED_CACHE
        _AUDITED_CACHE = None
        _load_audited(audited_only=True)

    if args.word:
        engine = analyze_with_engine(args.word)
        cmp = compare(engine)
        print(f"الكَلِمَة: {cmp.word}")
        print(f"المُحَرِّك:    جَذر={cmp.engine.root}  وزن={cmp.engine.wazn}")
        if cmp.audited:
            verified = "✓" if cmp.audited.is_audited and cmp.audited.is_correct else "?"
            print(f"المُدَقَّق {verified}: جَذر={cmp.audited.root}  باب={cmp.audited.bab_sarfi}")
            print(f"            مَصدَر={cmp.audited.masdar}  مرجع={cmp.audited.source}")
        print(f"الحالَة:    {cmp.status}")
        if cmp.issue_type:
            print(f"المُشكِلَة:  {cmp.issue_type}")
            print(f"الوَصف:    {cmp.description}")
            print(f"الإِصلاح:  {cmp.fix_hint}")
        return

    # دُفعَة
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
    elif args.sample:
        cache = _load_audited(audited_only=args.audited_only)
        all_words = list({e.verb for entries in cache.values() for e in entries if e.verb})
        random.seed(42)
        words = random.sample(all_words, min(args.sample, len(all_words)))
    else:
        p.print_help()
        return

    out = OUT_CSV if args.report else None
    stats = run_batch(words, out_path=out)

    print(f"\n=== تَقرير المُقارَنَة مَع audited_roots ===")
    print(f"  ground truth: data/audited_roots.csv")
    print(f"  قَواعِد التَّصنيف: data/contracts/rules/issue_classification.csv")
    print(f"  الكُلّيّ: {stats['total']}")
    print(f"  تَطابُق مَع مُدَقَّق صَحيح: {stats['exact_match_pct']:.1f}%")
    print(f"  أَيّ تَطابُق: {stats['any_match_pct']:.1f}%")
    print(f"\n  تَوزيع الحالات:")
    for s, n in sorted(stats['status_distribution'].items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")
    print(f"\n  تَوزيع المُشكِلات (مِن CSV):")
    for i, n in sorted(stats['issue_distribution'].items(), key=lambda x: -x[1]):
        print(f"    {i}: {n}")
    if out:
        print(f"\n  التَّقرير: {out}")


if __name__ == "__main__":
    main()
