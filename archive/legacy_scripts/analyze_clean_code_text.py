#!/usr/bin/env python3
"""
Analyze Arabic text with hussein/clean_code: normalizer → segmenter → wazn_matcher.

From ``hussein/`` root::

    PYTHONPATH=. python3 scripts/analyze_clean_code_text.py "النص هنا"
    PYTHONPATH=. python3 scripts/analyze_clean_code_text.py \\
        --masaq ../new_arabic_analyzer/data/MASAQ.csv --ayah 2:282
    PYTHONPATH=. python3 scripts/analyze_clean_code_text.py \\
        --masaq ../new_arabic_analyzer/data/MASAQ.csv --range 2:282-2:283
    PYTHONPATH=. python3 scripts/analyze_clean_code_text.py --json -t "كَاتِبٌ"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

_HUSSEIN_ROOT = Path(__file__).resolve().parents[1]
if str(_HUSSEIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_HUSSEIN_ROOT))

from clean_code.normalizer import normalize as normalize_full
from clean_code.normalizer import normalize_text
from clean_code.segmenter import segment
from clean_code.wazn_matcher import AnalyzerV2, WaznMatch

_DEFAULT_MASAQ = _HUSSEIN_ROOT.parent / "new_arabic_analyzer" / "data" / "MASAQ.csv"


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").strip().split())


def _canon_col(name: str) -> str:
    return str(name).replace("\ufeff", "").strip().lower()


def get_col(row: dict[str, Any], candidates: list[str]) -> str | None:
    lower_map = {_canon_col(str(k)): k for k in row.keys()}
    for c in candidates:
        key = lower_map.get(_canon_col(c))
        if key is not None and row.get(key):
            return str(row[key])
    return None


def parse_ayah_ref(s: str) -> tuple[int, int]:
    raw = (s or "").strip()
    if ":" not in raw:
        raise ValueError(f"Invalid ayah ref {s!r} (expected SURAH:AYAH)")
    x, y = raw.split(":", 1)
    return int(x), int(y)


def parse_ayah_range(s: str) -> tuple[tuple[int, int], tuple[int, int]]:
    raw = (s or "").strip()
    if "-" not in raw:
        raise ValueError(f"Invalid range {s!r}")
    left, right = raw.split("-", 1)
    start = parse_ayah_ref(left)
    if ":" in right:
        end = parse_ayah_ref(right)
    else:
        end = (start[0], int(right))
    return start, end


def row_ref(row: dict[str, Any]) -> tuple[int, int] | None:
    s = get_col(row, ["Sura_No", "Sura", "Surah", "surah", "sura_no", "surah_id"])
    a = get_col(row, ["Verse_No", "Verse", "Ayah", "ayah", "ayah_no", "verse_no"])
    if s is None or a is None:
        return None
    try:
        return int(str(s).strip()), int(str(a).strip())
    except ValueError:
        return None


def _to_int(v: str | None, default: int) -> int:
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except ValueError:
        return default


def load_masaq_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"MASAQ CSV not found: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"MASAQ CSV has no rows: {path}")
    return rows


def detect_csv_mode(rows: list[dict[str, Any]]) -> str:
    header_keys = {_canon_col(str(k)) for k in rows[0].keys()}
    if header_keys & {"ayah_text", "text", "uthmani", "text_uthmani"}:
        return "ayah"
    if "word" in header_keys and "word_no" in header_keys:
        return "word"
    raise ValueError(
        "Unsupported MASAQ format: need ayah text column or Word+Word_No columns"
    )


def build_ayah_text_from_word_rows(rows_for_ayah: list[dict[str, Any]]) -> str | None:
    if not rows_for_ayah:
        return None
    items = sorted(
        rows_for_ayah,
        key=lambda r: (
            _to_int(get_col(r, ["Word_No", "word_no"]), 10**9),
            _to_int(get_col(r, ["Segment_No", "segment_no"]), 10**9),
        ),
    )
    seen_word_no: set[int] = set()
    words: list[str] = []
    for r in items:
        w = get_col(r, ["Word", "word"])
        if not w:
            continue
        wno = _to_int(get_col(r, ["Word_No", "word_no"]), -1)
        seg = _to_int(get_col(r, ["Segment_No", "segment_no"]), -1)
        if wno >= 0:
            if wno in seen_word_no:
                continue
            seen_word_no.add(wno)
            words.append(w)
        elif seg == 1:
            words.append(w)
    return _normalize_ws(" ".join(words)) or None


def group_masaq_by_ayah(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        ref = row_ref(row)
        if ref is None:
            continue
        grouped.setdefault(ref, []).append(row)
    return grouped


def tokenize_ayah(text: str) -> list[str]:
    norm_ayah = normalize_text(text)
    return [t for t in norm_ayah.split() if t]


def analyze_token(
    surface: str,
    analyzer: AnalyzerV2,
    *,
    max_results: int,
) -> dict[str, Any]:
    norm_res = normalize_full(surface)
    seg_res = segment(surface, normalize_input=True)
    stem_matches = analyzer.analyze(seg_res.stem, max_results=max_results)
    surface_matches = (
        analyzer.analyze(surface, max_results=max_results)
        if seg_res.stem != norm_res.normalized
        else []
    )
    return {
        "surface": surface,
        "normalization": norm_res.to_dict(),
        "segmentation": seg_res.to_dict(),
        "wazn_stem": [m.to_dict() for m in stem_matches],
        "wazn_surface": [m.to_dict() for m in surface_matches],
    }


def format_match_line(m: dict[str, Any]) -> str:
    return (
        f"{m.get('wazn', '?')}  root={m.get('root', '?')}  "
        f"conf={m.get('confidence', 0):.2f}  src={m.get('source', '')}"
    )


def print_ayah_report(
    header: str | None,
    text: str,
    analyzer: AnalyzerV2,
    *,
    max_results: int,
) -> None:
    if header:
        print(header)
    print(f"Text ({len(text.split())} tokens): {text[:120]}{'…' if len(text) > 120 else ''}")
    print("─" * 72)
    tokens = tokenize_ayah(text)
    for i, tok in enumerate(tokens, start=1):
        row = analyze_token(tok, analyzer, max_results=max_results)
        seg = row["segmentation"]
        norm = row["normalization"]
        print(f"[{i:03d}] {tok}")
        if norm.get("changed"):
            print(f"      norm: {norm['normalized']!r}  ({', '.join(norm.get('transformations') or [])})")
        pref = "+".join(seg.get("prefixes") or []) or "—"
        suf = "+".join(seg.get("suffixes") or []) or "—"
        print(f"      seg:  prefixes=[{pref}]  stem={seg.get('stem', '')!r}  suffixes=[{suf}]")
        if seg.get("audit"):
            print(f"            audit: {' → '.join(seg['audit'][:6])}")
        wstem = row["wazn_stem"]
        if wstem:
            print(f"      wazn (stem):")
            for m in wstem[:max_results]:
                print(f"            {format_match_line(m)}")
        else:
            print("      wazn (stem): (no match)")
        wsurf = row["wazn_surface"]
        if wsurf:
            print("      wazn (surface):")
            for m in wsurf[:2]:
                print(f"            {format_match_line(m)}")
    print("─" * 72)


def resolve_inputs(args: argparse.Namespace) -> list[tuple[str | None, str]]:
    if args.masaq is not None:
        modes = int(bool(args.ayah)) + int(bool(args.range_ref)) + int(bool(args.all_rows))
        if modes != 1:
            raise ValueError("with --masaq, choose exactly one of --ayah / --range / --all")
        rows = load_masaq_rows(args.masaq)
        mode = detect_csv_mode(rows)
        if mode == "ayah":
            by_ref: dict[tuple[int, int], str] = {}
            for row in rows:
                ref = row_ref(row)
                txt = get_col(row, ["Ayah_Text", "text", "ayah_text", "uthmani", "text_uthmani"])
                if ref and txt:
                    by_ref[ref] = _normalize_ws(txt)
        else:
            grouped = group_masaq_by_ayah(rows)
            by_ref = {
                ref: build_ayah_text_from_word_rows(grouped[ref]) or ""
                for ref in grouped
            }
            by_ref = {k: v for k, v in by_ref.items() if v}

        if args.ayah:
            target = parse_ayah_ref(args.ayah)
            txt = by_ref.get(target)
            if not txt:
                raise ValueError(f"ayah not found in MASAQ: {args.ayah}")
            return [(f"=== Surah {target[0]} Ayah {target[1]} ===", txt)]

        if args.range_ref:
            start, end = parse_ayah_range(args.range_ref)
            out: list[tuple[str | None, str]] = []
            refs = sorted(by_ref.keys())
            started = False
            for ref in refs:
                if ref == start:
                    started = True
                if started:
                    out.append((f"=== Surah {ref[0]} Ayah {ref[1]} ===", by_ref[ref]))
                if ref == end:
                    break
            if not out:
                raise ValueError(f"range not found: {args.range_ref}")
            return out

        return [
            (f"=== Surah {ref[0]} Ayah {ref[1]} ===", txt)
            for ref, txt in sorted(by_ref.items())
        ]

    if args.ayah or args.range_ref or args.all_rows:
        raise ValueError("--ayah/--range/--all require --masaq")

    raw = _normalize_ws(args.text or " ".join(args.text_positional or []))
    if not raw:
        raise ValueError("provide text, --text/-t, or --masaq with --ayah")
    return [(None, raw)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Analyze text with clean_code normalizer + segmenter + wazn_matcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("text_positional", nargs="*", help="Arabic text (positional)")
    p.add_argument("--text", "-t", help="Arabic input text")
    p.add_argument(
        "--masaq",
        type=Path,
        default=None,
        help=f"MASAQ CSV (default: {_DEFAULT_MASAQ})",
    )
    p.add_argument("--ayah", help="Surah:ayah from MASAQ (e.g. 2:282)")
    p.add_argument("--range", dest="range_ref", help="Ayah range e.g. 2:282-2:283")
    p.add_argument("--all", dest="all_rows", action="store_true", help="All ayahs in MASAQ")
    p.add_argument("--max-results", type=int, default=3, help="Max wazn readings per token")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args(argv)

    if args.text_positional and args.text:
        p.error("Use positional text or --text, not both")

    if not args.text and args.text_positional:
        args.text = " ".join(args.text_positional)

    masaq_path = args.masaq
    if masaq_path is None and (args.ayah or args.range_ref or args.all_rows):
        masaq_path = _DEFAULT_MASAQ
    args.masaq = masaq_path

    try:
        inputs = resolve_inputs(args)
    except (ValueError, FileNotFoundError) as exc:
        p.error(str(exc))

    analyzer = AnalyzerV2()
    all_results: list[dict[str, Any]] = []

    for idx, (header, txt) in enumerate(inputs):
        if args.json:
            tokens = tokenize_ayah(txt)
            block = {
                "header": header,
                "text": txt,
                "tokens": [
                    analyze_token(t, analyzer, max_results=args.max_results)
                    for t in tokens
                ],
            }
            all_results.append(block)
        else:
            if idx > 0:
                print()
            print_ayah_report(header, txt, analyzer, max_results=args.max_results)

    if args.json:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
