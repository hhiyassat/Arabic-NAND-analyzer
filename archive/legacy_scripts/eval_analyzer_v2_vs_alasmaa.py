#!/usr/bin/env python3
"""Eval suite: compare analyzer_v2 against alasmaa/analyze_word.py on mishkat.

For each (root, word) pair in mishkat_word_root.csv:
  - run analyzer_v2(word) → top-K matches with extracted roots
  - run alasmaa.analyze_token(word) → top match with extracted root
  - compare extracted roots vs the truth root

Metrics:
  - Coverage:        % of rows where the analyzer returned ANY match
  - Top-1 accuracy:  % of rows where the BEST match's root equals truth
  - Top-3 accuracy:  % of rows where truth root is in top-3 matches
  - Per-category accuracy: noun vs verb, sound vs weak, mahmuz vs not, etc.

Output:
  - eval_per_row.csv   — detailed per-word comparison
  - eval_summary.csv   — aggregated stats
  - eval_report.md     — human-readable report
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


# === Resolve paths (macOS or sandbox) ===
def _paths():
    macos = Path("/Users/husseinhiyassat/fractal")
    sandbox = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos, sandbox):
        mishkat = root / "new_arabic_analyzer/data/mishkat_word_root.csv"
        if mishkat.is_file():
            return (
                mishkat,
                root / "alasmaa/analyze_word.py",
                root / "hussein/data/Mushtaqat_Full_Weights_Table.xlsx",
                root / "hussein/data/extracted/eval_per_row.csv",
                root / "hussein/data/extracted/eval_summary.csv",
                root / "hussein/data/extracted/eval_report.md",
                str(root / "hussein/src"),
            )
    raise FileNotFoundError("Cannot resolve paths.")


(MISHKAT, ALASMAA_PY, ALASMAA_WEIGHTS,
 OUT_ROWS, OUT_SUMMARY, OUT_REPORT, HUSSEIN_SRC) = _paths()


# === Setup imports ===
sys.path.insert(0, HUSSEIN_SRC)
from architecture_test.analyzer_v2 import (
    AnalyzerV2, strip_diacritics, fold_hamza,
)


def _load_alasmaa():
    """Dynamically import alasmaa's analyze_word module."""
    spec = importlib.util.spec_from_file_location("alasmaa_aw", ALASMAA_PY)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load alasmaa/analyze_word.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["alasmaa_aw"] = mod
    spec.loader.exec_module(mod)
    return mod


WEAK_LETTERS = {"و", "ي", "ا", "ى", "آ", "ٱ"}


def _root_plain(root: str) -> str:
    return fold_hamza(strip_diacritics(root))


def _is_weak(root_plain: str) -> bool:
    return any(c in WEAK_LETTERS for c in root_plain)


def _has_hamza(root_plain: str) -> bool:
    return "ء" in root_plain


def _is_geminate(root_plain: str) -> bool:
    return len(root_plain) >= 3 and root_plain[1] == root_plain[2]


def _is_quadriliteral(root_plain: str) -> bool:
    return len(root_plain) == 4


def _category(root_plain: str) -> str:
    if not root_plain or len(root_plain) < 3:
        return "other"
    if len(root_plain) > 4:
        return "long_root"
    if _is_weak(root_plain):
        return "weak"
    if _is_quadriliteral(root_plain):
        return "quadriliteral"
    if _is_geminate(root_plain):
        return "geminate_sound"
    if _has_hamza(root_plain):
        return "hamza_sound"
    return "sound"


def _root_matches(extracted: Optional[str], truth_plain: str) -> bool:
    """True iff the extracted root (after normalize) equals the truth root."""
    if not extracted:
        return False
    return fold_hamza(strip_diacritics(extracted)) == truth_plain


def _alasmaa_root_from_match(aw_mod, match: dict) -> Optional[str]:
    """Use alasmaa's own root-extraction helper to derive root from a wazn match."""
    if not match:
        return None
    weight = match.get("weight") or ""
    variant = match.get("variant") or ""
    w = aw_mod.normalize_for_match(weight)
    x = aw_mod.normalize_for_match(variant)
    if len(w) != len(x):
        return None
    mapping: dict[str, str] = {}
    for wc, xc in zip(w, x):
        if wc in aw_mod.PATTERN:
            if wc in mapping and mapping[wc] != xc:
                return None
            mapping[wc] = xc
        elif wc != xc:
            return None
    if not all(k in mapping for k in ("ف", "ع", "ل")):
        return None
    return mapping["ف"] + mapping["ع"] + mapping["ل"]


def main(limit: Optional[int] = None) -> int:
    print("loading mishkat...", file=sys.stderr)
    rows = []
    with MISHKAT.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if limit:
        rows = rows[:limit]
    print(f"  rows: {len(rows)}", file=sys.stderr)

    print("loading analyzer_v2...", file=sys.stderr)
    av2 = AnalyzerV2()
    print(f"  v2 db: {len(av2.db)} pattern variants", file=sys.stderr)

    print("loading alasmaa...", file=sys.stderr)
    aw_mod = _load_alasmaa()
    aw_weights = aw_mod.load_weights_from_excel(str(ALASMAA_WEIGHTS))
    print(f"  alasmaa weights: {len(aw_weights)}", file=sys.stderr)

    per_row_results: list[dict] = []
    stats = defaultdict(Counter)  # (category, metric) → count

    t0 = time.time()
    for i, row in enumerate(rows):
        if i % 500 == 0:
            elapsed = time.time() - t0
            print(f"  processed {i}/{len(rows)} ({elapsed:.1f}s)", file=sys.stderr)
        word = (row.get("word") or "").strip()
        truth = (row.get("root") or "").strip()
        truth_plain = _root_plain(truth)
        try:
            token_count = int(row.get("count", 1) or 1)
        except ValueError:
            token_count = 1
        cat = _category(truth_plain)

        # analyzer_v2
        v2_matches = av2.analyze(word, max_results=3)
        v2_top1_root = v2_matches[0].root if v2_matches else None
        v2_top1_wazn = v2_matches[0].wazn if v2_matches else None
        v2_top1_ok = _root_matches(v2_top1_root, truth_plain)
        v2_top3_ok = any(_root_matches(m.root, truth_plain) for m in v2_matches)
        v2_has_match = bool(v2_matches)

        # alasmaa analyze_word
        try:
            aw_best, aw_all = aw_mod.analyze_token(word, aw_weights)
        except Exception:
            aw_best, aw_all = None, []
        aw_root = _alasmaa_root_from_match(aw_mod, aw_best) if aw_best else None
        aw_wazn = aw_best.get("weight") if aw_best else None
        aw_top1_ok = _root_matches(aw_root, truth_plain)
        aw_top3_ok = any(
            _root_matches(_alasmaa_root_from_match(aw_mod, m), truth_plain)
            for m in (aw_all[:3] if aw_all else [])
        )
        aw_has_match = bool(aw_best)

        # Stats — weight by token_count
        stats[cat]["total"] += 1
        stats[cat]["total_weighted"] += token_count
        stats["ALL"]["total"] += 1
        stats["ALL"]["total_weighted"] += token_count
        if v2_has_match:
            stats[cat]["v2_coverage"] += 1
            stats[cat]["v2_coverage_w"] += token_count
            stats["ALL"]["v2_coverage"] += 1
            stats["ALL"]["v2_coverage_w"] += token_count
        if aw_has_match:
            stats[cat]["aw_coverage"] += 1
            stats[cat]["aw_coverage_w"] += token_count
            stats["ALL"]["aw_coverage"] += 1
            stats["ALL"]["aw_coverage_w"] += token_count
        if v2_top1_ok:
            stats[cat]["v2_top1"] += 1
            stats[cat]["v2_top1_w"] += token_count
            stats["ALL"]["v2_top1"] += 1
            stats["ALL"]["v2_top1_w"] += token_count
        if v2_top3_ok:
            stats[cat]["v2_top3"] += 1
            stats[cat]["v2_top3_w"] += token_count
            stats["ALL"]["v2_top3"] += 1
            stats["ALL"]["v2_top3_w"] += token_count
        if aw_top1_ok:
            stats[cat]["aw_top1"] += 1
            stats[cat]["aw_top1_w"] += token_count
            stats["ALL"]["aw_top1"] += 1
            stats["ALL"]["aw_top1_w"] += token_count
        if aw_top3_ok:
            stats[cat]["aw_top3"] += 1
            stats[cat]["aw_top3_w"] += token_count
            stats["ALL"]["aw_top3"] += 1
            stats["ALL"]["aw_top3_w"] += token_count

        per_row_results.append({
            "root_truth": truth,
            "word": word,
            "count": token_count,
            "category": cat,
            "v2_wazn": v2_top1_wazn or "",
            "v2_root": v2_top1_root or "",
            "v2_top1_ok": int(v2_top1_ok),
            "v2_top3_ok": int(v2_top3_ok),
            "aw_wazn": aw_wazn or "",
            "aw_root": aw_root or "",
            "aw_top1_ok": int(aw_top1_ok),
            "aw_top3_ok": int(aw_top3_ok),
        })

    elapsed = time.time() - t0
    print(f"\ndone in {elapsed:.1f}s", file=sys.stderr)

    # Write per-row file
    OUT_ROWS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ROWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_row_results[0].keys()))
        w.writeheader()
        w.writerows(per_row_results)

    # Write summary
    categories = ["ALL", "sound", "hamza_sound", "geminate_sound",
                  "quadriliteral", "weak", "long_root", "other"]
    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "category", "rows", "tokens",
            "v2_cov_rows_%", "aw_cov_rows_%",
            "v2_top1_rows_%", "aw_top1_rows_%",
            "v2_top3_rows_%", "aw_top3_rows_%",
            "v2_top1_tokens_%", "aw_top1_tokens_%",
        ])
        for cat in categories:
            s = stats[cat]
            total = s["total"] or 1
            total_w = s["total_weighted"] or 1
            w.writerow([
                cat, s["total"], s["total_weighted"],
                f"{100*s['v2_coverage']/total:.1f}",
                f"{100*s['aw_coverage']/total:.1f}",
                f"{100*s['v2_top1']/total:.1f}",
                f"{100*s['aw_top1']/total:.1f}",
                f"{100*s['v2_top3']/total:.1f}",
                f"{100*s['aw_top3']/total:.1f}",
                f"{100*s['v2_top1_w']/total_w:.1f}",
                f"{100*s['aw_top1_w']/total_w:.1f}",
            ])

    # Write markdown report
    with OUT_REPORT.open("w", encoding="utf-8") as f:
        f.write("# analyzer_v2 vs alasmaa eval\n\n")
        f.write(f"**Mishkat rows:** {len(rows)}\n")
        f.write(f"**Elapsed:** {elapsed:.1f}s\n\n")
        f.write("## Per-category accuracy (by ROW count)\n\n")
        f.write("| Category | Rows | v2 cov | aw cov | v2 top1 | aw top1 | v2 top3 | aw top3 | Δtop1 |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for cat in categories:
            s = stats[cat]
            total = s["total"]
            if total == 0:
                continue
            v2_t1 = 100*s["v2_top1"]/total
            aw_t1 = 100*s["aw_top1"]/total
            delta = v2_t1 - aw_t1
            f.write(
                f"| **{cat}** | {total} | "
                f"{100*s['v2_coverage']/total:.1f}% | "
                f"{100*s['aw_coverage']/total:.1f}% | "
                f"{v2_t1:.1f}% | "
                f"{aw_t1:.1f}% | "
                f"{100*s['v2_top3']/total:.1f}% | "
                f"{100*s['aw_top3']/total:.1f}% | "
                f"{delta:+.1f}% |\n"
            )
        f.write("\n## Per-category accuracy (by TOKEN count, weighted)\n\n")
        f.write("| Category | Tokens | v2 top1 (w) | aw top1 (w) | Δ |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for cat in categories:
            s = stats[cat]
            tw = s["total_weighted"]
            if tw == 0:
                continue
            v2 = 100*s["v2_top1_w"]/tw
            aw = 100*s["aw_top1_w"]/tw
            f.write(
                f"| **{cat}** | {tw} | {v2:.1f}% | {aw:.1f}% | {v2-aw:+.1f}% |\n"
            )

    # Print summary
    print("\n" + "=" * 70)
    print("EVAL RESULTS")
    print("=" * 70)
    s = stats["ALL"]
    total = s["total"]
    print(f"\nTotal rows evaluated: {total}")
    print(f"\nCoverage (rows with ANY match):")
    print(f"  analyzer_v2:  {s['v2_coverage']:6d} ({100*s['v2_coverage']/total:.1f}%)")
    print(f"  alasmaa:      {s['aw_coverage']:6d} ({100*s['aw_coverage']/total:.1f}%)")
    print(f"\nTop-1 accuracy (best match has correct root):")
    print(f"  analyzer_v2:  {s['v2_top1']:6d} ({100*s['v2_top1']/total:.1f}%)")
    print(f"  alasmaa:      {s['aw_top1']:6d} ({100*s['aw_top1']/total:.1f}%)")
    print(f"\nTop-3 accuracy (correct root in top-3 matches):")
    print(f"  analyzer_v2:  {s['v2_top3']:6d} ({100*s['v2_top3']/total:.1f}%)")
    print(f"  alasmaa:      {s['aw_top3']:6d} ({100*s['aw_top3']/total:.1f}%)")
    print(f"\nOutputs:")
    print(f"  per-row:  {OUT_ROWS}")
    print(f"  summary:  {OUT_SUMMARY}")
    print(f"  report:   {OUT_REPORT}")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None,
                   help="Process only first N rows (for testing)")
    args = p.parse_args()
    sys.exit(main(limit=args.limit))
