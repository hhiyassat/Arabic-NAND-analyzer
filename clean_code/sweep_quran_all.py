#!/usr/bin/env python3
"""sweep_quran_all.py — تَطبيق analyze_verse_v3 --all عَلى كُلّ القُرآن وَ تَجميع الإِخفاقات.

يَدور عَلى كُلّ آية، يَستَدعي الـ layers كَ ما يَستَدعيها analyze_verse_v3، وَ يَجمَع:
  • Python exceptions (خَلَل في الكود)
  • Zero answers مِن Phase G (أَسئلَة بِلا جَواب — مُؤَشِّر فَجوَة)
  • Empty relations / events / resolutions عَلى آية يَنبَغي أَن تَملِكها
  • فَشَل i3rab أَو morph

CLI:
  python3 sweep_quran_all.py                 # كُلّ القُرآن
  python3 sweep_quran_all.py --start 1:1     # ابدَأ مِن آية مُحَدَّدَة
  python3 sweep_quran_all.py --end 1:7       # تَوَقَّف عِندَ آية مُحَدَّدَة
  python3 sweep_quran_all.py --limit 20      # أَوَّل 20 آية فَقَط
  python3 sweep_quran_all.py --surah 1       # سُورَة كامِلَة
  python3 sweep_quran_all.py --report-only   # لا تَطبَع آية آية، فَقَط الإِجماليّ
"""

from __future__ import annotations

import argparse
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
QURAN_PATH = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"


def load_all_verses() -> list[tuple[int, int, str]]:
    """يُحَمِّل كُلّ الآيات: list[(surah, ayah, text)]."""
    out = []
    with open(QURAN_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                try:
                    out.append((int(parts[0]), int(parts[1]), parts[2]))
                except ValueError:
                    pass
    return out


def parse_ref(s: str) -> tuple[int, int]:
    a, b = s.split(":")
    return int(a), int(b)


_ENGINE_CACHE = {}


def _get_engines():
    """Cache engines across calls for performance."""
    if _ENGINE_CACHE:
        return _ENGINE_CACHE
    from i3rab_engine.engine import I3rabEngine
    from relation_extractor import RelationExtractor
    from event_extractor import EventExtractor
    from resolution_engine import ResolutionEngine
    from meaning_assembler import MeaningAssembler
    from reasoning_engine import ReasoningEngine
    _ENGINE_CACHE["i3rab"] = I3rabEngine()
    _ENGINE_CACHE["rel"] = RelationExtractor()
    _ENGINE_CACHE["ev"] = EventExtractor()
    _ENGINE_CACHE["res"] = ResolutionEngine()
    _ENGINE_CACHE["assembler"] = MeaningAssembler()
    _ENGINE_CACHE["reasoning"] = ReasoningEngine()
    return _ENGINE_CACHE


def run_layers_on_verse(text: str, prior_context: list | None = None) -> dict:
    """يُشَغِّل كُلّ الـ layers عَلى آية، يَرُدّ تَقريرًا.

    تَقرير: {
        'i3rab_ok': bool, 'i3rab_err': str,
        'tokens': int, 'fiil_count': int, 'ism_count': int, 'harf_count': int,
        'relations': int, 'rel_certs': int, 'rel_hyps': int,
        'events': int, 'event_with_agent': int, 'event_with_patient': int,
        'resolutions': int, 'res_certs': int,
        'meaning_nodes': int, 'meaning_edges': int, 'coverage': float,
        'qa_results': dict[question -> kind],
        'errors': list[str],
    }
    """
    report = {
        "i3rab_ok": False, "i3rab_err": "",
        "tokens": 0, "fiil_count": 0, "ism_count": 0, "harf_count": 0,
        "unknown_count": 0,  # NEW
        "relations": 0, "rel_certs": 0, "rel_hyps": 0,
        "events": 0, "event_with_agent": 0, "event_with_patient": 0,
        "resolutions": 0, "res_certs": 0,
        "meaning_nodes": 0, "meaning_edges": 0, "coverage": 0.0,
        "qa_results": {},
        "errors": [],
        "anomalies": [],  # NEW — suspicious classifications worth investigating
    }

    engines = _get_engines()
    # Layer 1: i3rab
    try:
        sent = engines["i3rab"].analyze_sentence(text)
        report["i3rab_ok"] = True
        report["tokens"] = len(sent.tokens)
        # Pause-mark unicode chars (should NEVER appear as tokens after fix #1)
        PAUSE_MARK_CHARS = set("ۚۖۗۘۙۛۜ۠ۡۢۤۥۦۭۧۨ۟")
        # Verb prefix signature: starts with يَ/تَ/نَ/أَ + sukun on root letter
        # — these are unambiguous verbs, ISM classification = bug
        VERB_PREFIX_CHARS = {"يَ", "تَ", "نَ", "أَ", "يُ", "تُ", "نُ", "أُ"}

        for i, t in enumerate(sent.tokens):
            wc = t.word_class
            tok = getattr(t, "token", "") or ""
            if wc == "FIIL":
                report["fiil_count"] += 1
            elif wc in ("ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM", "JALALAH"):
                report["ism_count"] += 1
            elif wc == "HARF":
                report["harf_count"] += 1
            elif wc == "UNKNOWN":
                report["unknown_count"] += 1
                report["anomalies"].append(f"UNKNOWN:{tok}")

            # ── Anomaly checks ──
            # A1: a token containing a pause mark
            if any(c in PAUSE_MARK_CHARS for c in tok):
                report["anomalies"].append(f"PAUSE_MARK_IN_TOKEN:{tok}")
            # A2: token classified as ISM but unambiguously a verb.
            #     pattern = يَ/تَ/نَ/أَ + CONSONANT (not weak letter) + ـْ
            #     Excludes hollow nouns (يَوْم has و in 2nd position).
            WEAK_LETTERS = {"و", "ي", "ا", "ى", "ٱ"}
            if wc in ("ISM_MUARAB", "JAMID"):
                if (len(tok) >= 5 and tok[:2] in VERB_PREFIX_CHARS
                        and len(tok) > 2 and tok[2] not in WEAK_LETTERS):
                    # 3rd char is consonant (not weak); check sukun on it
                    if len(tok) >= 4 and tok[3] == "ْ":
                        # Exclude tanwin (definitely noun) and ال prefix
                        if not any(c in tok for c in ("ٌ", "ٍ", "ً")):
                            report["anomalies"].append(f"VERB_AS_ISM:{tok}")
            # A3: ـهۥ / ـهۦ tail not stripped (rare diacritic dagger)
            if "هۥ" in tok or "هۦ" in tok:
                report["anomalies"].append(f"DAGGER_PRON:{tok}")
    except Exception as e:
        report["i3rab_err"] = f"{type(e).__name__}: {e}"
        report["errors"].append(f"i3rab: {report['i3rab_err']}")
        return report

    # Layer 2: relations
    try:
        rg = engines["rel"].extract(sent)
        report["relations"] = len(rg.relations)
        report["rel_certs"] = sum(1 for r in rg.relations if r.kind == "Certificate")
        report["rel_hyps"] = sum(1 for r in rg.relations if r.kind == "Hypothesis")
    except Exception as e:
        report["errors"].append(f"relations: {type(e).__name__}: {e}")
        rg = None

    # Layer 3: events
    eg = None
    if rg is not None:
        try:
            eg = engines["ev"].extract(sent, rg)
            report["events"] = len(eg.events)
            report["event_with_agent"] = sum(1 for e in eg.events if e.agent)
            report["event_with_patient"] = sum(1 for e in eg.events if e.patient)
        except Exception as e:
            report["errors"].append(f"events: {type(e).__name__}: {e}")

    # Layer 4: resolution
    try:
        res = engines["res"].resolve(sent, eg, prior_context=prior_context or [])
        report["resolutions"] = len(res.resolutions)
        report["res_certs"] = sum(1 for r in res.resolutions if r.kind == "Certificate")
    except Exception as e:
        report["errors"].append(f"resolution: {type(e).__name__}: {e}")

    # Layer 5: meaning + reasoning
    try:
        graph = engines["assembler"].assemble(text)
        s = graph.stats()
        report["meaning_nodes"] = s.get("nodes", 0)
        report["meaning_edges"] = s.get("edges", 0)
        report["coverage"] = s.get("coverage_pct", 0.0)
    except Exception as e:
        report["errors"].append(f"meaning: {type(e).__name__}: {e}")

    # Phase G: Q/A
    try:
        eng = engines["reasoning"]
        questions = [
            "مَن الفاعِل؟",
            "ماذا حَدَث؟",
            "أَين حَدَث؟",
            "متى حَدَث؟",
        ]
        for q in questions:
            a = eng.answer(text, q)
            report["qa_results"][q] = a.kind
    except Exception as e:
        report["errors"].append(f"reasoning: {type(e).__name__}: {e}")

    return report


def build_prior_context(surah: int, ayah: int) -> list[dict]:
    """يَبني سِياقًا بَسيطًا لِلسُّورَة (سَتُتَوَسَّع لاحِقًا).

    سُورَة 1 (الفاتِحَة): المُتَكَلِّم العَبد، المُخاطَب اللَّه (مِن 1:5).
    """
    if surah == 1 and ayah >= 5:
        return [
            {"id": "speaker_servant", "role": "speaker", "surface": "العَبد",
             "gender": "M", "number": "PL"},
            {"id": "addressee_allah", "role": "addressee", "surface": "اللَّه",
             "gender": "M", "number": "SG"},
        ]
    return []


def main():
    p = argparse.ArgumentParser(description="Sweep --all عَلى القُرآن مَع تَجميع الإِخفاقات")
    p.add_argument("--start", help="ابدَأ مِن سُورَة:آية (مَثَلًا 1:1)")
    p.add_argument("--end", help="تَوَقَّف عِندَ سُورَة:آية شامِلَة")
    p.add_argument("--limit", type=int, help="أَوَّل N آية فَقَط")
    p.add_argument("--surah", type=int, help="سُورَة كامِلَة")
    p.add_argument("--report-only", action="store_true", help="لا تَطبَع آية آية")
    p.add_argument("--errors-only", action="store_true", help="اطبَع فَقَط الآيات بِها أَخطاء")
    p.add_argument("--save-jsonl", help="احفَظ نَتائِج كُلّ آية في مَلَفّ JSONL")
    p.add_argument("--resume-from", help="اقرَأ JSONL سابِق وَ ابدَأ مِن بَعد آخِر آية تَمَّت")
    p.add_argument("--aggregate-jsonl", help="اقرَأ JSONL وَ اعرِض تَقريرًا تَجميعيًّا (لا sweep)")
    args = p.parse_args()

    # وَضع تَجميع: لا sweep، فَقَط قِراءَة JSONL وَ تَقرير
    if args.aggregate_jsonl:
        import json as _json
        verses_done = []
        with open(args.aggregate_jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    verses_done.append(_json.loads(line))
                except _json.JSONDecodeError:
                    continue
        _print_aggregate_report(verses_done)
        return

    verses = load_all_verses()

    if args.surah:
        verses = [v for v in verses if v[0] == args.surah]

    if args.start:
        ss, sa = parse_ref(args.start)
        verses = [v for v in verses if (v[0], v[1]) >= (ss, sa)]

    if args.end:
        es, ea = parse_ref(args.end)
        verses = [v for v in verses if (v[0], v[1]) <= (es, ea)]

    # وَضع الِاستِئناف: اقرَأ JSONL سابِق + ابدَأ مِن بَعد آخِر آية مَوجودَة
    skip_until = None
    if args.resume_from:
        import json as _json
        last_ref = None
        try:
            with open(args.resume_from, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = _json.loads(line)
                        last_ref = (rec["surah"], rec["ayah"])
                    except (_json.JSONDecodeError, KeyError):
                        continue
        except FileNotFoundError:
            last_ref = None
        if last_ref:
            skip_until = last_ref
            verses = [v for v in verses if (v[0], v[1]) > last_ref]
            print(f"  ↻ استِئناف بَعد {last_ref[0]}:{last_ref[1]} — {len(verses)} آية مُتَبَقِّيَة")

    if args.limit:
        verses = verses[:args.limit]

    # مَلَفّ JSONL لِلكِتابَة
    jsonl_f = None
    if args.save_jsonl:
        jsonl_f = open(args.save_jsonl, "a", encoding="utf-8")

    # تَجميع
    error_classes: Counter = Counter()
    qa_zero_counts: Counter = Counter()
    zero_verses: list = []
    error_verses: list = []
    coverage_buckets: Counter = Counter()
    n_total = len(verses)
    n_full_zero = 0  # كُلّ الـ4 أَسئلَة Zero
    n_no_events = 0
    n_no_relations = 0
    n_perfect = 0  # 100% Q/A بِدون Zero

    print(f"\n📊 Sweep بِدأ — {n_total} آية\n")

    for idx, (surah, ayah, text) in enumerate(verses, 1):
        ref = f"{surah}:{ayah}"
        ctx = build_prior_context(surah, ayah)
        report = run_layers_on_verse(text, prior_context=ctx)

        # تَصنيف
        for err in report["errors"]:
            error_classes[err.split(":")[0]] += 1
        if report["errors"]:
            error_verses.append((ref, report["errors"]))

        zeros_in_qa = sum(1 for k in report["qa_results"].values() if k == "Zero")
        if zeros_in_qa == 4:
            n_full_zero += 1
        if zeros_in_qa == 0 and report["qa_results"]:
            n_perfect += 1
        if report["events"] == 0:
            n_no_events += 1
        if report["relations"] == 0:
            n_no_relations += 1

        for q, k in report["qa_results"].items():
            if k == "Zero":
                qa_zero_counts[q] += 1

        cov = report["coverage"]
        if cov >= 100:
            coverage_buckets["100+"] += 1
        elif cov >= 75:
            coverage_buckets["75-99"] += 1
        elif cov >= 50:
            coverage_buckets["50-74"] += 1
        elif cov > 0:
            coverage_buckets["1-49"] += 1
        else:
            coverage_buckets["0"] += 1

        # طِباعَة آيَة آيَة
        if not args.report_only:
            should_print = not args.errors_only or report["errors"]
            if should_print:
                marker = "❌" if report["errors"] else ("✅" if zeros_in_qa == 0 else "⚠")
                print(f"  {marker} [{ref}] tok={report['tokens']} rel={report['relations']} "
                      f"ev={report['events']} res={report['resolutions']} "
                      f"cov={cov:.0f}% qa_zeros={zeros_in_qa}/4")
                if report["errors"]:
                    for e in report["errors"][:2]:
                        print(f"      ❌ {e[:120]}")

        # احفَظ JSONL إِن طُلِب
        if jsonl_f is not None:
            import json as _json
            rec = {
                "surah": surah, "ayah": ayah,
                "tokens": report["tokens"], "fiil_count": report["fiil_count"],
                "ism_count": report["ism_count"], "harf_count": report["harf_count"],
                "unknown_count": report.get("unknown_count", 0),
                "relations": report["relations"], "events": report["events"],
                "resolutions": report["resolutions"],
                "meaning_nodes": report["meaning_nodes"],
                "meaning_edges": report["meaning_edges"],
                "coverage": report["coverage"],
                "qa_results": report["qa_results"],
                "errors": report["errors"],
                "anomalies": report.get("anomalies", []),
                "qa_zeros": zeros_in_qa,
                "is_perfect": zeros_in_qa == 0,
            }
            jsonl_f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
            jsonl_f.flush()

        # تَحديث مُؤَشِّر التَّقَدُّم
        if idx % 50 == 0:
            print(f"  ── تَقَدُّم: {idx}/{n_total} ({100*idx/n_total:.1f}%) ──")

    if jsonl_f is not None:
        jsonl_f.close()

    # تَقرير نِهائيّ
    print(f"\n{'='*70}")
    print(f"📈 التَّقرير النِّهائيّ — {n_total} آية")
    print(f"{'='*70}\n")
    print(f"  بِلا أَخطاء Python:       {n_total - len(error_verses)} ({100*(n_total-len(error_verses))/n_total:.1f}%)")
    print(f"  بِلا relations:             {n_no_relations} ({100*n_no_relations/n_total:.1f}%)")
    print(f"  بِلا events:                {n_no_events} ({100*n_no_events/n_total:.1f}%)")
    print(f"  كُلّ الـQ/A Zero:           {n_full_zero} ({100*n_full_zero/n_total:.1f}%)")
    print(f"  أَيّ Q/A لَه إِجابَة:        {n_total - n_full_zero} ({100*(n_total-n_full_zero)/n_total:.1f}%)")
    print(f"  جَواب عَلى كُلّ الأَسئلَة:    {n_perfect} ({100*n_perfect/n_total:.1f}%)")

    print(f"\n  📊 توزيع MeaningGraph coverage:")
    for bucket in ["100+", "75-99", "50-74", "1-49", "0"]:
        c = coverage_buckets.get(bucket, 0)
        print(f"     {bucket:8s}: {c} ({100*c/n_total:.1f}%)")

    print(f"\n  ❓ Zeros حَسَب السُّؤال:")
    for q, c in qa_zero_counts.most_common():
        print(f"     {q:25s} → Zero في {c}/{n_total} ({100*c/n_total:.1f}%)")

    if error_classes:
        print(f"\n  ❌ تَصنيف أَخطاء Python:")
        for cls, c in error_classes.most_common():
            print(f"     {cls:20s}: {c}")

    if error_verses and not args.report_only:
        print(f"\n  ❌ أَوَّل 10 آيات بِها أَخطاء:")
        for ref, errs in error_verses[:10]:
            print(f"     [{ref}] {errs[0][:100]}")

    print()


def _print_aggregate_report(records: list[dict]) -> None:
    """يَطبَع تَقريرًا تَجميعيًّا مِن سِجِلّات JSONL."""
    if not records:
        print("⚠ لا سِجِلّات")
        return
    n = len(records)
    print(f"\n{'='*70}")
    print(f"📈 تَقرير تَجميعيّ مِن JSONL — {n} آية")
    print(f"{'='*70}\n")

    # إِجماليّ
    n_err = sum(1 for r in records if r.get("errors"))
    n_perfect = sum(1 for r in records if r.get("is_perfect"))
    n_full_zero = sum(1 for r in records if r.get("qa_zeros", 0) == 4)
    n_no_events = sum(1 for r in records if r.get("events", 0) == 0)
    n_no_relations = sum(1 for r in records if r.get("relations", 0) == 0)

    print(f"  بِلا أَخطاء Python:       {n - n_err} ({100*(n-n_err)/n:.1f}%)")
    print(f"  بِلا relations:             {n_no_relations} ({100*n_no_relations/n:.1f}%)")
    print(f"  بِلا events:                {n_no_events} ({100*n_no_events/n:.1f}%)")
    print(f"  كُلّ الـQ/A Zero:           {n_full_zero} ({100*n_full_zero/n:.1f}%)")
    print(f"  أَيّ Q/A لَه إِجابَة:        {n - n_full_zero} ({100*(n-n_full_zero)/n:.1f}%)")
    print(f"  جَواب عَلى كُلّ الأَسئلَة:    {n_perfect} ({100*n_perfect/n:.1f}%)")

    # توزيع coverage
    buckets = Counter()
    for r in records:
        cov = r.get("coverage", 0)
        if cov >= 100:
            buckets["100+"] += 1
        elif cov >= 75:
            buckets["75-99"] += 1
        elif cov >= 50:
            buckets["50-74"] += 1
        elif cov > 0:
            buckets["1-49"] += 1
        else:
            buckets["0"] += 1
    print(f"\n  📊 توزيع MeaningGraph coverage:")
    for bucket in ["100+", "75-99", "50-74", "1-49", "0"]:
        c = buckets.get(bucket, 0)
        print(f"     {bucket:8s}: {c} ({100*c/n:.1f}%)")

    # Zeros per question
    qa_zeros = Counter()
    for r in records:
        for q, k in r.get("qa_results", {}).items():
            if k == "Zero":
                qa_zeros[q] += 1
    print(f"\n  ❓ Zeros حَسَب السُّؤال:")
    for q, c in qa_zeros.most_common():
        print(f"     {q:25s} → Zero في {c}/{n} ({100*c/n:.1f}%)")

    # تَجميع حَسَب السُّورَة
    by_surah = defaultdict(list)
    for r in records:
        by_surah[r["surah"]].append(r)
    print(f"\n  📚 ملَخَّص لِكُلّ سُورَة ({len(by_surah)} سُورَة):")
    print(f"     {'سُورَة':<8} {'آيات':<6} {'Perfect':<10} {'Errs':<6} {'AvgCov':<8}")
    for s in sorted(by_surah):
        recs = by_surah[s]
        ns = len(recs)
        nperf = sum(1 for r in recs if r.get("is_perfect"))
        nerr = sum(1 for r in recs if r.get("errors"))
        avg_cov = sum(r.get("coverage", 0) for r in recs) / ns
        print(f"     {s:<8} {ns:<6} {nperf:<3} ({100*nperf/ns:>3.0f}%)  "
              f"{nerr:<6} {avg_cov:<6.1f}%")

    # أَكثَر الأَخطاء
    err_classes = Counter()
    for r in records:
        for e in r.get("errors", []):
            err_classes[e.split(":")[0]] += 1
    if err_classes:
        print(f"\n  ❌ تَصنيف أَخطاء Python:")
        for cls, c in err_classes.most_common():
            print(f"     {cls:20s}: {c}")

    # تَصنيف الـ anomalies (الأَخطاء الَّتي لا تَقلِب Python لَكِنّها تَدُلّ عَلى bug)
    anom_classes = Counter()
    anom_examples = defaultdict(list)
    for r in records:
        for a in r.get("anomalies", []):
            cls, _, val = a.partition(":")
            anom_classes[cls] += 1
            if len(anom_examples[cls]) < 5:
                anom_examples[cls].append((r["surah"], r["ayah"], val))
    if anom_classes:
        print(f"\n  ⚠ تَصنيف الـ Anomalies (إِشارات bug خَفِيّ):")
        for cls, c in anom_classes.most_common():
            print(f"     {cls:25s}: {c}")
            for surah, ayah, val in anom_examples[cls][:3]:
                print(f"        مَثَل [{surah}:{ayah}] {val[:40]}")
    print()


if __name__ == "__main__":
    main()
