#!/usr/bin/env python3
"""i3rab.py — أعرب نصًا عربيًا من سطر الأوامر.

أوضاع التشغيل:

    # 1. نصّ مباشر
    python3 scripts/i3rab.py "الحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ"

    # 2. من ملف نصّي
    python3 scripts/i3rab.py --file my_text.txt

    # 3. من الإدخال القياسي
    echo "بِسْمِ اللَّهِ" | python3 scripts/i3rab.py -

    # 4. من CSV: عمود اسمه 'sentence' افتراضيًّا
    python3 scripts/i3rab.py --csv data/sample_sentences.csv

    # 5. CSV → CSV (إعراب كل جملة، صف لكل token)
    python3 scripts/i3rab.py --csv data/sample_sentences.csv \\
        --csv-out data/sample_i3rab_results.csv

    # 6. JSON
    python3 scripts/i3rab.py --json "نَصْرٌ مِنَ اللَّهِ"

    # 7. تفاصيل المصدر لكل token
    python3 scripts/i3rab.py --verbose "إِنَّ اللَّهَ غَفُورٌ"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Resolve clean_code: try sibling first (bundled layout),
# then parent (scripts/ layout).
_HERE = Path(__file__).resolve().parent
ROOT = None
for _cand in (_HERE / "clean_code", _HERE.parent / "clean_code"):
    if _cand.is_dir():
        sys.path.insert(0, str(_cand))
        ROOT = _cand.parent
        break
if ROOT is None:
    print("خطأ: مجلّد clean_code غير موجود بجوار السكربت أو في مجلده الأب",
          file=sys.stderr)
    sys.exit(1)

try:
    from i3rab_engine import I3rabEngine  # type: ignore
    from i3rab_engine.types import CASE_IDS, MARK_IDS  # type: ignore
except ImportError as e:
    print(f"خطأ في تحميل المحرّك: {e}", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# جداول الترجمة — تُحمَّل من contracts/translations/*.csv
# (المعرّفات الداخليّة الإنجليزيّة تَبقى في الكود؛ العرض فقط يَستهلك العربيّة)
# ============================================================================

try:
    from contracts_loader import (
        load_word_class_ar,
        load_proof_kind_ar,
        load_verb_aspect_ar,
        load_harf_kind_ar,
        load_source_ar,
    )
    _AR_WORD_CLASS = load_word_class_ar()
    _AR_VERB_ASPECT = load_verb_aspect_ar()
    _AR_HARF_KIND = load_harf_kind_ar()
    # proof_kind has a 'short' column too; load via raw rows for the letter map
    import csv as _csv
    from pathlib import Path as _Path
    _AR_PROOF_KIND: dict = {}
    _AR_PROOF_LETTER: dict = {}
    for _root in [
        _Path(ROOT) / "clean_code" / "data" / "contracts" / "translations",
        _Path(ROOT) / "data" / "contracts" / "translations",
    ]:
        _pk = _root / "proof_kind.csv"
        if _pk.is_file():
            with _pk.open(encoding="utf-8", newline="") as _f:
                for _r in _csv.DictReader(_f):
                    _AR_PROOF_KIND[_r["code"]] = _r["ar"]
                    _AR_PROOF_LETTER[_r["code"]] = _r.get("short", _r["code"][:1])
            break
except ImportError:
    _AR_WORD_CLASS = {"HARF": "حرف", "ISM_MABNI": "اسم مبني",
                      "ISM_MUARAB": "اسم معرب", "FIIL": "فعل",
                      "JAMID": "اسم جامد", "AALAM": "علم",
                      "JALALAH": "لفظ الجلالة", "UNKNOWN": "—"}
    _AR_PROOF_KIND = {"Certificate": "قاطع", "Hypothesis": "مُحتمَل", "Zero": "خالٍ"}
    _AR_PROOF_LETTER = {"Certificate": "ق", "Hypothesis": "ح", "Zero": "ص"}
    _AR_VERB_ASPECT = {"PV": "ماضٍ", "IV": "مضارع", "CV": "أمر", "": ""}
    _AR_HARF_KIND = {}

def _ar_harf_kind(k: str) -> str:
    return _AR_HARF_KIND.get(k, k)


# قاموس شفرات المصدر — مُحَمَّل بالكامل من
# clean_code/data/contracts/translations/source_codes.csv
# (لا قواميس مدمجة في الكود — مبدأ الحد الأدنى المكتمل)
try:
    _AR_SOURCE = load_source_ar()
except Exception:
    _AR_SOURCE = {}


def _ar_word_class(wc: str) -> str:
    return _AR_WORD_CLASS.get(wc, wc)


def _ar_proof(kind: str, *, short: bool = False) -> str:
    if short:
        return _AR_PROOF_LETTER.get(kind, kind[:1] if kind else "")
    return _AR_PROOF_KIND.get(kind, kind)


def _is_arabic(s: str) -> bool:
    """هل النصّ عربيّ في معظمه؟ (لتجنّب ترجمة ما هو عربيّ أصلًا)."""
    if not s:
        return False
    ar = sum(1 for c in s if "؀" <= c <= "ۿ")
    en = sum(1 for c in s if c.isascii() and c.isalpha())
    return ar > en


def _ar_source(src: str) -> str:
    """ترجمة شفرة المصدر إلى عربيّة. تُعالَج 3 صيغ:
      1. النصّ عربيّ أصلًا → يُعاد كما هو
      2. ``key(arg)``  مثل  ``after_HARF_JARR(فِي)`` → "بعد حرف جر (فِي)"
      3. ``key:value`` مثل  ``fiil_aspect:PV``     → "نوع الفعل: ماضٍ"
    """
    if not src:
        return ""
    if _is_arabic(src):
        return src
    # صيغة (1): key(arg)
    if "(" in src and src.endswith(")"):
        key, _, rest = src.partition("(")
        arg = rest[:-1]
        ar_key = _AR_SOURCE.get(key, key)
        return f"{ar_key} ({arg})"
    # صيغة (2): key:value
    if ":" in src:
        key, _, rest = src.partition(":")
        ar_key = _AR_SOURCE.get(key)
        # ترجمة الجزء الثاني (rest): جرّب _AR_SOURCE ثم _AR_HARF_KIND
        rest_s = rest.strip()
        ar_rest = (
            _AR_SOURCE.get(rest_s)
            or _AR_HARF_KIND.get(rest_s)
            or rest_s
        )
        if ar_key:
            return f"{ar_key}: {ar_rest}" if ar_rest else ar_key
        ar_full = _AR_SOURCE.get(src)
        if ar_full:
            return ar_full
    return _AR_SOURCE.get(src, src)


def _mark_label(t) -> str:
    """يَبني نَصّ علامة الإعراب — صيغة موحَّدة.

    مع تنوين: «تنوين الضمّ» / «تنوين الفتح» / «تنوين الكسر»
    بلا تنوين: «الضمّة» / «الفتحة» / «الكسرة» / «السكون» / ...
    """
    if not t.mark_id:
        return "—"
    base = MARK_IDS[t.mark_id][0]
    tanwin = getattr(t, "tanwin", "") or ""
    if tanwin:
        if base == "ضمة":   return "تنوين الضمّ"
        if base == "فتحة":  return "تنوين الفتح"
        if base == "كسرة":  return "تنوين الكسر"
    _AL_FORMS = {
        "ضمة": "الضمّة", "فتحة": "الفتحة", "كسرة": "الكسرة",
        "سكون": "السكون", "ألف": "الألف", "واو": "الواو",
        "ياء": "الياء", "نون": "النون",
        "حذف النون": "حذف النون", "حذف نون": "حذف النون",
        "فتحة ممنوع": "الفتحة (ممنوع من الصرف)",
    }
    return _AL_FORMS.get(base, base)


def split_sentences(text: str) -> list[str]:
    """تقسيم النصّ إلى جمل عند علامات الترقيم العربية والإنكليزية."""
    # إستبدال علامات الترقيم بفاصل موحَّد
    out: list[str] = []
    cur: list[str] = []
    for ch in text:
        if ch in ".!?؟।":
            if cur:
                out.append("".join(cur).strip())
                cur = []
        else:
            cur.append(ch)
    if cur:
        s = "".join(cur).strip()
        if s:
            out.append(s)
    return out or ([text.strip()] if text.strip() else [])


def render_table(sentence_result, *, verbose: bool = False) -> str:
    """جدول نصّي عربيّ بالكامل لكل token."""
    lines = []
    lines.append(
        f"{'الكلمة':<22} {'النوع':<14} {'الحالة':<10} "
        f"{'العلامة':<16} {'الدور الإعرابي':<32}"
    )
    lines.append("-" * 105)
    for t in sentence_result.tokens:
        case_name = CASE_IDS.get(t.case_id, "—") if t.case_id else "—"
        mark_name = _mark_label(t)
        wc_ar = _ar_word_class(t.word_class)
        line = (
            f"{t.token:<22} {wc_ar:<14} {case_name:<10} "
            f"{mark_name:<16} {t.role_phrase:<32}"
        )
        lines.append(line)
        if verbose:
            details = []
            if t.root:
                details.append(f"جذر={t.root}")
            if t.wazn:
                details.append(f"وزن={t.wazn}")
            if t.verb_aspect:
                details.append(f"نوع_الفعل={_AR_VERB_ASPECT.get(t.verb_aspect, t.verb_aspect)}")
            if t.closed_class_kind:
                details.append(f"نوع_الحرف={_ar_harf_kind(t.closed_class_kind)}")
            if details:
                lines.append("    " + "  |  ".join(details))
            # مصادر القرارات بالعربيّة
            src_lines = []
            if t.case_source:
                src_lines.append(f"الحالة ← {_ar_source(t.case_source)}")
            if t.role_source:
                src_lines.append(f"الدور ← {_ar_source(t.role_source)}")
            for ln in src_lines:
                lines.append(f"    {ln}")
            # الإثبات لكل طبقة بالعربية
            proof = []
            if getattr(t, "wordclass_kind", ""):
                proof.append(f"النوع={_ar_proof(t.wordclass_kind)}")
            if getattr(t, "case_kind", ""):
                proof.append(f"الحالة={_ar_proof(t.case_kind)}")
            if getattr(t, "role_kind", ""):
                proof.append(f"الدور={_ar_proof(t.role_kind)}")
            if proof:
                lines.append("    الإثبات: " + " · ".join(proof))
            if t.notes:
                lines.append("    ملاحظات: " + " · ".join(t.notes))
            # IntegrityContract seal — proof_trace_hash يَختِم، لا يَشرح
            integ = getattr(t, "integrity", None) or {}
            seal = integ.get("proof_trace_hash", "")
            if seal:
                short = seal.split(":", 1)[-1][:12] + "…"
                lines.append(f"    [الختم]: sha256:{short}")
    return "\n".join(lines)


def render_json(sentence_results) -> str:
    out = [s.to_dict() for s in sentence_results]
    return json.dumps(out, ensure_ascii=False, indent=2)


def read_input(args) -> str:
    """قراءة المدخل: من --file، من stdin (`-`), أو من args.text."""
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text == "-" or (args.text is None and not sys.stdin.isatty()):
        return sys.stdin.read()
    if args.text is not None:
        return args.text
    return ""


def read_csv_sentences(path: Path, column: str) -> list[tuple[int, str]]:
    """قراءة الجمل من ملف CSV.

    إن وُجد عمود ``column`` يُؤخذ منه، وإلا فيُؤخذ أوّل عمود.
    لو لم يكن للملف ترويسة (أوّل صف يبدو كجملة عربية، لا اسم عمود)،
    تُؤخذ كل الصفوف من أوّل عمود.

    Returns: قائمة من (rownum, sentence).
    """
    if not path.is_file():
        raise FileNotFoundError(f"ملف CSV غير موجود: {path}")
    out: list[tuple[int, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        # حاول قراءة الترويسة
        sample = f.read(2048)
        f.seek(0)
        # Sniff: لو السطر الأوّل لاتيني — هذه ترويسة
        first_line = sample.split("\n", 1)[0]
        has_header = any(c.isalpha() and c.isascii() for c in first_line)

        if has_header:
            reader = csv.DictReader(f)
            # Pick column
            cols = reader.fieldnames or []
            col = column if column in cols else (cols[0] if cols else "sentence")
            for i, row in enumerate(reader, start=1):
                txt = (row.get(col) or "").strip()
                if txt:
                    out.append((i, txt))
        else:
            reader = csv.reader(f)
            for i, row in enumerate(reader, start=1):
                if not row:
                    continue
                txt = (row[0] or "").strip()
                if txt:
                    out.append((i, txt))
    return out


def write_csv_results(out_path: Path, results: list, *, verbose: bool = False) -> None:
    """كتابة نتائج الإعراب إلى CSV: صف لكل token.

    الأعمدة:
      sentence_id, sentence, position, token, word_class, case, mark,
      role, root, wazn, closed_class_kind, case_source, role_source
    """
    fields = [
        "sentence_id", "sentence", "position", "token",
        "word_class", "case", "mark", "role",
        "root", "wazn", "closed_class_kind",
    ]
    if verbose:
        fields += ["case_source", "role_source", "word_class_source", "notes"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid, sent in results:
            for t in sent.tokens:
                case_name = CASE_IDS.get(t.case_id, "") if t.case_id else ""
                mark_name = MARK_IDS[t.mark_id][0] if t.mark_id else ""
                row = {
                    "sentence_id": sid,
                    "sentence": sent.text,
                    "position": t.position,
                    "token": t.token,
                    "word_class": t.word_class,
                    "case": case_name,
                    "mark": mark_name,
                    "role": t.role_phrase,
                    "root": t.root,
                    "wazn": t.wazn,
                    "closed_class_kind": t.closed_class_kind,
                }
                if verbose:
                    row["case_source"] = t.case_source
                    row["role_source"] = t.role_source
                    row["word_class_source"] = t.word_class_source
                    row["notes"] = " · ".join(t.notes) if t.notes else ""
                w.writerow(row)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="محرّك إعراب عربي — قواعدي، يستهلك نصًّا ويُخرج إعرابه.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "text",
        nargs="?",
        help='النصّ العربي المراد إعرابه (أو "-" للقراءة من stdin)',
    )
    p.add_argument(
        "--file", "-f",
        type=Path,
        help="قراءة النصّ من ملف نصّي",
    )
    p.add_argument(
        "--csv",
        type=Path,
        help="قراءة الجمل من ملف CSV (جملة لكل صف)",
    )
    p.add_argument(
        "--column",
        type=str,
        default="sentence",
        help="اسم عمود الجمل في CSV (افتراضي: sentence)",
    )
    p.add_argument(
        "--csv-out",
        type=Path,
        help="حفظ نتائج الإعراب في CSV (صف لكل token)",
    )
    p.add_argument(
        "--json", "-j",
        action="store_true",
        help="إخراج JSON بدل الجدول النصّي",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="عرض تفاصيل كل قرار (المصدر، الجذر، الوزن)",
    )
    p.add_argument(
        "--no-split",
        action="store_true",
        help="عدم تقسيم النصّ إلى جمل (تعامل كجملة واحدة)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="إخفاء رسائل التقدّم — للاستخدام في pipelines",
    )
    args = p.parse_args(argv)

    # === Mode 1: CSV input ===
    if args.csv:
        try:
            sentences_with_id = read_csv_sentences(args.csv, args.column)
        except (FileNotFoundError, KeyError) as exc:
            p.error(str(exc))
        if not sentences_with_id:
            p.error(f"لا توجد جمل في الملف: {args.csv}")

        if not args.quiet:
            print(
                f"جاري تهيئة المحرّك (تحميل MASAQ والمراجع)...",
                file=sys.stderr,
            )
        eng = I3rabEngine()
        if not args.quiet:
            print(
                f"تمّت التهيئة. جاري إعراب {len(sentences_with_id)} جملة...",
                file=sys.stderr,
            )

        results = []
        for sid, text in sentences_with_id:
            s = eng.analyze_sentence(text)
            results.append((sid, s))
            if not args.quiet and sid % 25 == 0:
                print(f"  ... {sid}/{len(sentences_with_id)}", file=sys.stderr)

        # Output: CSV file or stdout tables
        if args.csv_out:
            write_csv_results(args.csv_out, results, verbose=args.verbose)
            if not args.quiet:
                print(
                    f"تمّ. الناتج في: {args.csv_out}",
                    file=sys.stderr,
                )
        elif args.json:
            out = [
                {"sentence_id": sid, **s.to_dict()}
                for sid, s in results
            ]
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            # Print all tables to stdout
            for sid, s in results:
                print(f"\n══════════════════════════════════════════════════════════════════════")
                print(f"  [#{sid}]  {s.text}")
                print(f"══════════════════════════════════════════════════════════════════════")
                print(render_table(s, verbose=args.verbose))
            print()
        return 0

    # === Mode 2/3/4: text / file / stdin ===
    text = read_input(args).strip()
    if not text:
        p.error(
            "لا يوجد نصّ. مرّر النصّ كحجّة، أو --file، أو --csv، "
            "أو عبر stdin."
        )

    if args.no_split:
        sentences = [text]
    else:
        sentences = split_sentences(text)

    if not args.quiet:
        print(
            "جاري تهيئة المحرّك (تحميل MASAQ والمراجع)...",
            file=sys.stderr,
        )
    eng = I3rabEngine()
    if not args.quiet:
        print(
            f"تمّت التهيئة. عدد الجمل: {len(sentences)}",
            file=sys.stderr,
        )
        print(file=sys.stderr)

    sent_results = []
    for sent_text in sentences:
        if not sent_text.strip():
            continue
        s = eng.analyze_sentence(sent_text)
        sent_results.append(s)

    # Output dispatching
    if args.csv_out:
        # Even text input can be saved to CSV
        results_with_ids = [(i + 1, s) for i, s in enumerate(sent_results)]
        write_csv_results(args.csv_out, results_with_ids, verbose=args.verbose)
        if not args.quiet:
            print(f"تمّ. الناتج في: {args.csv_out}", file=sys.stderr)
        return 0

    if args.json:
        print(render_json(sent_results))
        return 0

    for i, s in enumerate(sent_results, start=1):
        if len(sent_results) > 1:
            print(f"\n══════════════════════════════════════════════════════════════════════")
            print(f"  جملة {i}/{len(sent_results)}:  {s.text}")
            print(f"══════════════════════════════════════════════════════════════════════")
        else:
            print(f"\nالنصّ:  {s.text}\n")
        print(render_table(s, verbose=args.verbose))

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
