#!/usr/bin/env python3
"""morph.py — المحلّل الصرفي العربي.

يأخذ كلمة أو نصًّا ويُخرج: الجذر، الوزن، نوع الكلمة، التقطيع.

أوضاع التشغيل:

    # 1. كلمة واحدة
    python3 morph.py "يَكْتُبُ"

    # 2. نصّ كامل (يحلّل كل كلمة)
    python3 morph.py "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ"

    # 3. من ملف نصّي
    python3 morph.py --file my_text.txt

    # 4. من stdin
    echo "بِسْمِ اللَّهِ" | python3 morph.py -

    # 5. من CSV → CSV
    python3 morph.py --csv words.csv --csv-out analysis.csv

    # 6. JSON
    python3 morph.py --json "كَتَبَ"

    # 7. تفاصيل المصادر
    python3 morph.py -v "اسْتَخْرَجَ"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Resolve clean_code: try sibling first (bundled layout: morph.py next to
# clean_code/), then parent (scripts/ layout: scripts/morph.py with
# clean_code/ at the parent level).
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
    from root_pipeline import RootPipeline  # type: ignore
    from segmenter import segment  # type: ignore
    from normalizer import normalize as normalize_full  # type: ignore
except ImportError as e:
    print(f"خطأ في تحميل المحرّك: {e}", file=sys.stderr)
    sys.exit(1)


_STATUS_AR = {
    "jalalah": "لفظ الجلالة",
    "closed_class": "مبني/عامل",
    "jamid": "اسم جامد",
    "open_class": "مشتق (له جذر ووزن)",
    "no_match": "لم يُطابَق",
}

# تَرجمات شفرات source للعرض
_AR_SOURCE_MORPH = {
    "closed_class_detector":     "معجم المبنيات",
    "jamid_detector":            "معجم الجوامد",
    "jalalah_lexical":           "لفظ الجلالة",
    "jalalah_convention":        "لفظ الجلالة",
    "wazn_alignment":            "محاذي الأوزان",
    "no_wazn_matched":           "لا وزن مُطابق",
}


def _ar_morph_source(src: str) -> str:
    if not src:
        return ""
    if ":" in src:
        key, _, rest = src.partition(":")
        ar = _AR_SOURCE_MORPH.get(key)
        if ar:
            return f"{ar}: {rest}" if rest else ar
    return _AR_SOURCE_MORPH.get(src, src)


def tokenize_text(text: str) -> list[str]:
    """تقسيم بسيط على المسافات (يحتفظ بالتشكيل)."""
    return [t for t in (text or "").split() if t]


def analyze_token(token: str, pipe: RootPipeline) -> dict:
    """تحليل صرفي شامل لكلمة واحدة."""
    norm = normalize_full(token)
    seg = segment(token, normalize_input=True)
    ana = pipe.analyze(token)
    return {
        "token": token,
        "normalized": norm.normalized,
        "normalization_changed": norm.changed,
        "normalization_steps": norm.transformations,
        "prefixes": list(seg.prefixes),
        "stem": seg.stem,
        "suffixes": list(seg.suffixes),
        "prefix_tags": list(seg.prefix_tags),
        "suffix_tags": list(seg.suffix_tags),
        "status": ana.status,
        "status_ar": _STATUS_AR.get(ana.status, ana.status),
        "root": ana.root,
        "wazn": ana.wazn,
        "source_of_claim": ana.source_of_claim,
    }


def render_table(rows: list[dict], *, verbose: bool = False) -> str:
    out = []
    header = (
        f"{'الكلمة':<22} {'الحالة':<18} {'الجذر':<8} {'الوزن':<14} "
        f"{'البادئات':<10} {'الجذع':<14} {'اللواحق':<10}"
    )
    out.append(header)
    out.append("-" * 110)
    for r in rows:
        prefixes = "+".join(r["prefixes"]) or "—"
        stem = r["stem"] or "—"
        suffixes = "+".join(r["suffixes"]) or "—"
        out.append(
            f"{r['token']:<22} {r['status_ar']:<18} {r['root'] or '—':<8} "
            f"{r['wazn'] or '—':<14} {prefixes:<10} {stem:<14} {suffixes:<10}"
        )
        if verbose:
            details = []
            if r["normalization_changed"]:
                details.append(
                    f"تطبيع: {r['normalized']!r} ({', '.join(r['normalization_steps'])})"
                )
            tags_p = "+".join(r["prefix_tags"]) or ""
            tags_s = "+".join(r["suffix_tags"]) or ""
            if tags_p or tags_s:
                details.append(f"تصنيف اللواصق: بادئة=[{tags_p}] لاحقة=[{tags_s}]")
            details.append(f"المصدر: {_ar_morph_source(r['source_of_claim'])}")
            for d in details:
                out.append(f"    {d}")
    return "\n".join(out)


def write_csv(out_path: Path, rows: list[dict], *, verbose: bool = False) -> None:
    fields = [
        "token", "status", "status_ar", "root", "wazn",
        "prefixes", "stem", "suffixes",
    ]
    if verbose:
        fields += [
            "normalized", "normalization_steps",
            "prefix_tags", "suffix_tags", "source_of_claim",
        ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            row = {
                "token": r["token"],
                "status": r["status"],
                "status_ar": r["status_ar"],
                "root": r["root"],
                "wazn": r["wazn"],
                "prefixes": "+".join(r["prefixes"]),
                "stem": r["stem"],
                "suffixes": "+".join(r["suffixes"]),
            }
            if verbose:
                row["normalized"] = r["normalized"]
                row["normalization_steps"] = ", ".join(r["normalization_steps"])
                row["prefix_tags"] = "+".join(r["prefix_tags"])
                row["suffix_tags"] = "+".join(r["suffix_tags"])
                row["source_of_claim"] = r["source_of_claim"]
            w.writerow(row)


def read_csv_input(path: Path, column: str) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"ملف CSV غير موجود: {path}")
    out: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        first = sample.split("\n", 1)[0]
        has_header = any(c.isalpha() and c.isascii() for c in first)
        if has_header:
            r = csv.DictReader(f)
            cols = r.fieldnames or []
            col = column if column in cols else (cols[0] if cols else "word")
            for row in r:
                v = (row.get(col) or "").strip()
                if v:
                    out.append(v)
        else:
            r = csv.reader(f)
            for row in r:
                if row and row[0].strip():
                    out.append(row[0].strip())
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="المحلّل الصرفي العربي — جذر + وزن + تقطيع.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("text", nargs="?",
                   help='النصّ أو الكلمة (أو "-" للقراءة من stdin)')
    p.add_argument("--file", "-f", type=Path, help="قراءة من ملف نصّي")
    p.add_argument("--csv", type=Path, help="قراءة الكلمات/الجمل من CSV")
    p.add_argument("--column", default="word",
                   help="اسم العمود في CSV (افتراضي: word)")
    p.add_argument("--csv-out", type=Path, help="حفظ النتائج في CSV")
    p.add_argument("--json", "-j", action="store_true", help="JSON")
    p.add_argument("--verbose", "-v", action="store_true", help="تفاصيل المصدر")
    p.add_argument("--quiet", action="store_true", help="إخفاء التقدّم")
    args = p.parse_args(argv)

    # Gather tokens
    tokens: list[str] = []
    if args.csv:
        try:
            for entry in read_csv_input(args.csv, args.column):
                tokens.extend(tokenize_text(entry))
        except FileNotFoundError as e:
            p.error(str(e))
    elif args.file:
        tokens = tokenize_text(args.file.read_text(encoding="utf-8"))
    elif args.text == "-" or (args.text is None and not sys.stdin.isatty()):
        tokens = tokenize_text(sys.stdin.read())
    elif args.text:
        tokens = tokenize_text(args.text)
    else:
        p.error("لا يوجد إدخال. مرّر نصًّا أو --file أو --csv.")

    if not tokens:
        p.error("لا توجد كلمات صالحة في الإدخال.")

    # Initialize engine
    if not args.quiet:
        print("جاري تهيئة المحلّل (تحميل الأوزان والمعجم)...", file=sys.stderr)
    pipe = RootPipeline()
    if not args.quiet:
        print(f"تمّت التهيئة. جاري تحليل {len(tokens)} كلمة...", file=sys.stderr)

    rows = []
    for i, tok in enumerate(tokens, start=1):
        rows.append(analyze_token(tok, pipe))
        if not args.quiet and i % 100 == 0:
            print(f"  ... {i}/{len(tokens)}", file=sys.stderr)

    # Output
    if args.csv_out:
        write_csv(args.csv_out, rows, verbose=args.verbose)
        if not args.quiet:
            print(f"تمّ. الناتج في: {args.csv_out}", file=sys.stderr)
        return 0
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print()
    print(render_table(rows, verbose=args.verbose))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
