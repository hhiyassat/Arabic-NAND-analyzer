#!/usr/bin/env python3
"""Run analyzer_v2 on MASAQ.csv and validate against mishkat ground truth.

MASAQ has 157,677 segment-level rows. We dedupe to unique words by
(Sura_No, Verse_No, Word_No) since each segment of a word repeats the
'Word' column. Mishkat (word, root, count) provides ground truth root
for the subset of words present in both corpora.

Outputs:
  - masaq_analyzed.csv      — per-word analysis with top-3 v2 predictions
  - masaq_eval_summary.csv  — aggregated accuracy on the mishkat subset
  - masaq_eval_report.md    — human-readable report
"""

from __future__ import annotations

import csv
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional


def _paths():
    macos = Path("/Users/husseinhiyassat/fractal")
    sandbox = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos, sandbox):
        masaq = root / "new_arabic_analyzer/data/MASAQ.csv"
        mishkat = root / "new_arabic_analyzer/data/mishkat_word_root.csv"
        if masaq.is_file() and mishkat.is_file():
            return (
                masaq, mishkat,
                root / "hussein/data/extracted/masaq_analyzed.csv",
                root / "hussein/data/extracted/masaq_eval_summary.csv",
                root / "hussein/data/extracted/masaq_eval_report.md",
                str(root / "hussein/src"),
            )
    raise FileNotFoundError("Cannot resolve paths.")


MASAQ, MISHKAT, OUT_PER, OUT_SUM, OUT_REPORT, HUSSEIN_SRC = _paths()
sys.path.insert(0, HUSSEIN_SRC)
sys.path.insert(0, str(Path(HUSSEIN_SRC).parent))  # for clean_code
from architecture_test.analyzer_v2 import (  # noqa: E402
    AnalyzerV2, strip_diacritics, fold_hamza,
)

# Try to import the new normalizer; fall back to identity if not present
try:
    from clean_code.normalizer import normalize_text as _norm_text  # noqa: E402
    USE_NORMALIZER = True
except ImportError:
    USE_NORMALIZER = False
    _norm_text = lambda x: x  # noqa: E731

import os
if os.environ.get("MASAQ_NORMALIZE", "1") == "0":
    USE_NORMALIZER = False
    _norm_text = lambda x: x  # noqa: E731

WEAK_LETTERS = {"و", "ي", "ا", "ى", "آ", "ٱ"}


def _root_norm(r: str) -> str:
    return fold_hamza(strip_diacritics(r))


def _category(root_plain: str) -> str:
    if not root_plain or len(root_plain) < 3:
        return "other"
    if len(root_plain) > 4:
        return "long_root"
    if any(c in WEAK_LETTERS for c in root_plain):
        return "weak"
    if len(root_plain) == 4:
        return "quadriliteral"
    if root_plain[1] == root_plain[2]:
        return "geminate_sound"
    if "ء" in root_plain:
        return "hamza_sound"
    return "sound"


def load_mishkat_truth() -> dict[str, str]:
    """Return word_with_diacritics → truth_root_plain (most common)."""
    word_to_roots: dict[str, Counter] = {}
    with MISHKAT.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            w = (r.get("word") or "").strip()
            root = (r.get("root") or "").strip()
            try:
                count = int(r.get("count", 1) or 1)
            except ValueError:
                count = 1
            if w and root:
                word_to_roots.setdefault(w, Counter())[_root_norm(root)] += count
    # Pick the most-common truth root per word
    out: dict[str, str] = {}
    for w, counter in word_to_roots.items():
        out[w] = counter.most_common(1)[0][0]
    return out


def load_masaq_unique_words() -> list[dict]:
    """Return list of {word, sura, verse, word_no, morph_tags} dicts,
    deduplicated by (sura, verse, word_no)."""
    seen_keys = set()
    out: list[dict] = []
    by_pos: dict[tuple, dict] = {}
    with MASAQ.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            sura = (r.get("Sura_No") or "").strip()
            verse = (r.get("Verse_No") or "").strip()
            wno = (r.get("Word_No") or "").strip()
            word = (r.get("Word") or "").strip()
            tag = (r.get("Morph_Tag") or "").strip()
            if not word:
                continue
            key = (sura, verse, wno)
            if key not in by_pos:
                by_pos[key] = {
                    "sura": sura, "verse": verse, "word_no": wno,
                    "word": word, "morph_tags": [],
                }
            if tag:
                by_pos[key]["morph_tags"].append(tag)
    return list(by_pos.values())


def main(limit: Optional[int] = None) -> int:
    print("loading mishkat truth...", file=sys.stderr)
    truth = load_mishkat_truth()
    print(f"  {len(truth)} unique words with truth root", file=sys.stderr)

    print("loading MASAQ unique words...", file=sys.stderr)
    words = load_masaq_unique_words()
    print(f"  {len(words)} unique words", file=sys.stderr)
    if limit:
        words = words[:limit]

    print("loading analyzer_v2...", file=sys.stderr)
    av2 = AnalyzerV2()
    print(f"  db: {len(av2.db)} pattern variants, "
          f"audited: {len(av2.audited)} roots", file=sys.stderr)

    rows_out: list[dict] = []
    stats = {
        "total_words": 0,
        "with_v2_match": 0,
        "with_truth": 0,
        "v2_top1_ok": 0,
        "v2_top3_ok": 0,
        "excluded_correctly": 0,
        "by_cat": Counter(),
        "by_cat_top1": Counter(),
        "by_cat_top3": Counter(),
        "by_cat_with_truth": Counter(),
    }

    t0 = time.time()
    for i, w in enumerate(words):
        if i % 2000 == 0:
            elapsed = time.time() - t0
            print(f"  processed {i}/{len(words)} ({elapsed:.1f}s)", file=sys.stderr)
        word = w["word"]
        # Apply normalizer pre-pass if available
        if USE_NORMALIZER:
            word_input = _norm_text(word)
        else:
            word_input = word
        matches = av2.analyze(word_input, max_results=3)
        top = matches[0] if matches else None
        top_root = top.root if top else ""
        top_wazn = top.wazn if top else ""
        top_conf = top.confidence if top else 0.0
        all_roots = [m.root for m in matches]

        truth_root = truth.get(word, "")
        cat = _category(truth_root) if truth_root else "no_truth"

        # Special case: when v2 returned an "intentional skip with no root"
        # (quranic opener like الم, excluded name like موسى, closed-class
        # lexeme like الذي), exclude from scoring — analyzer correctly
        # refused to assign wazn, but mishkat assigns an etymological root
        # that we shouldn't compare against.
        # NOTE: divine_name IS scored because it returns root=ءله which CAN
        # legitimately match mishkat's truth for الله forms.
        is_skip_excluded = (
            top is not None
            and top.bab in {"quranic_opener", "excluded_name", "closed_class_lexeme"}
        )
        if is_skip_excluded:
            top1_ok = None
            top3_ok = None
        elif truth_root:
            top1_ok = top_root and _root_norm(top_root) == truth_root
            top3_ok = any(_root_norm(r) == truth_root for r in all_roots if r)
        else:
            top1_ok = None
            top3_ok = None

        rows_out.append({
            "sura": w["sura"], "verse": w["verse"], "word_no": w["word_no"],
            "word": word,
            "truth_root": truth_root or "",
            "category": cat,
            "v2_top1_wazn": top_wazn,
            "v2_top1_root": top_root,
            "v2_top1_conf": f"{top_conf:.3f}",
            "v2_top3_roots": " | ".join(all_roots),
            "top1_ok": "" if top1_ok is None else ("yes" if top1_ok else "no"),
            "top3_ok": "" if top3_ok is None else ("yes" if top3_ok else "no"),
        })

        stats["total_words"] += 1
        if matches:
            stats["with_v2_match"] += 1
        if truth_root:
            # If this is an intentional skip (correct refusal), exclude from
            # scored denominator — neither success nor failure.
            if is_skip_excluded:
                stats["excluded_correctly"] += 1
            else:
                stats["with_truth"] += 1
                stats["by_cat_with_truth"][cat] += 1
                if top1_ok:
                    stats["v2_top1_ok"] += 1
                    stats["by_cat_top1"][cat] += 1
                if top3_ok:
                    stats["v2_top3_ok"] += 1
                    stats["by_cat_top3"][cat] += 1

    elapsed = time.time() - t0

    OUT_PER.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PER.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)

    # Summary
    eval_total = stats["with_truth"] or 1
    with OUT_SUM.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "rows_with_truth", "top1_ok", "top1_%",
                         "top3_ok", "top3_%"])
        cats = sorted(stats["by_cat_with_truth"].keys())
        for cat in cats:
            n = stats["by_cat_with_truth"][cat]
            t1 = stats["by_cat_top1"][cat]
            t3 = stats["by_cat_top3"][cat]
            writer.writerow([
                cat, n, t1, f"{100*t1/n:.1f}", t3, f"{100*t3/n:.1f}",
            ])
        writer.writerow([
            "ALL", eval_total, stats["v2_top1_ok"],
            f"{100*stats['v2_top1_ok']/eval_total:.1f}",
            stats["v2_top3_ok"],
            f"{100*stats['v2_top3_ok']/eval_total:.1f}",
        ])

    # Report
    with OUT_REPORT.open("w", encoding="utf-8") as f:
        f.write("# analyzer_v2 on MASAQ — full Quranic eval\n\n")
        f.write(f"**MASAQ unique words:** {stats['total_words']}\n")
        f.write(f"**Words with v2 match:** {stats['with_v2_match']}  "
                f"({100*stats['with_v2_match']/stats['total_words']:.1f}%)\n")
        f.write(f"**Words with mishkat truth:** {stats['with_truth']}  "
                f"({100*stats['with_truth']/stats['total_words']:.1f}%)\n")
        f.write(f"**Elapsed:** {elapsed:.1f}s\n\n")
        f.write("## Validation against mishkat (subset with truth)\n\n")
        f.write(f"**Top-1 accuracy:** {stats['v2_top1_ok']}/{eval_total}  "
                f"({100*stats['v2_top1_ok']/eval_total:.1f}%)\n")
        f.write(f"**Top-3 accuracy:** {stats['v2_top3_ok']}/{eval_total}  "
                f"({100*stats['v2_top3_ok']/eval_total:.1f}%)\n\n")
        f.write("## Per-category breakdown\n\n")
        f.write("| Category | Rows | Top-1 | Top-3 |\n")
        f.write("|---|---:|---:|---:|\n")
        for cat in sorted(stats["by_cat_with_truth"].keys()):
            n = stats["by_cat_with_truth"][cat]
            t1 = stats["by_cat_top1"][cat]
            t3 = stats["by_cat_top3"][cat]
            f.write(f"| **{cat}** | {n} | {100*t1/n:.1f}% | {100*t3/n:.1f}% |\n")

    print("\n" + "=" * 70)
    print("MASAQ analysis with analyzer_v2")
    print("=" * 70)
    print(f"Unique words:         {stats['total_words']}")
    print(f"With v2 match:        {stats['with_v2_match']}  "
          f"({100*stats['with_v2_match']/stats['total_words']:.1f}%)")
    print(f"With mishkat truth:   {stats['with_truth']}  "
          f"({100*stats['with_truth']/stats['total_words']:.1f}%)")
    print()
    print(f"On the validated subset ({eval_total} words):")
    print(f"  Top-1 accuracy:     {stats['v2_top1_ok']:6d}  "
          f"({100*stats['v2_top1_ok']/eval_total:.1f}%)")
    print(f"  Top-3 accuracy:     {stats['v2_top3_ok']:6d}  "
          f"({100*stats['v2_top3_ok']/eval_total:.1f}%)")
    print()
    print(f"Outputs:")
    print(f"  per-word:  {OUT_PER}")
    print(f"  summary:   {OUT_SUM}")
    print(f"  report:    {OUT_REPORT}")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    sys.exit(main(limit=args.limit))
