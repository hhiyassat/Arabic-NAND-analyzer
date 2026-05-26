#!/usr/bin/env python3
"""phase4_quran_audit.py — مَسح كامِل القُرآن مَع classify_with_context.

يَقيس أَثَر Phase 4 ContextualAmbiguityResolver عَلى كامِل MASAQ stems.
يَحتَرِم env var ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER (OFF/ON).

Outputs:
  audit_outputs/phase4_{mode}/summary.txt
  audit_outputs/phase4_{mode}/per_surface.csv
  audit_outputs/phase4_{mode}/source_distribution.csv
"""
import argparse, csv, os, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
HERE = Path(__file__).resolve().parent
MASAQ = HERE.parent / "data" / "MASAQ.csv"

from build_master_token_table import masaq_tag_to_word_class
from i3rab_engine.layer1 import WordClassClassifier

# الـ surfaces المُستَهدَفَة (plain forms)
HANDLED = {"من", "ما", "أي", "أيّ", "متى", "أين", "أنى", "حيث", "بما"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["off", "on"], required=True)
    p.add_argument("--max", type=int, default=None, help="حَدّ tokens (لِلاختِبار)")
    args = p.parse_args()

    # تَعيين الـflag
    if args.mode == "on":
        os.environ["ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"] = "1"
    else:
        os.environ.pop("ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER", None)

    # تَأَكَّد مِن إِعادَة تَحميل integration module لِيَلتَقِط env
    import importlib
    if "arabic_analyzer.contextual_resolver.integration" in sys.modules:
        importlib.reload(sys.modules["arabic_analyzer.contextual_resolver.integration"])

    out_dir = HERE / "audit_outputs" / f"phase4_{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[phase4_{args.mode}] loading MASAQ…")
    stems = []
    with MASAQ.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("Morph_Type") or "").strip() != "Stem":
                continue
            stems.append(r)
    print(f"  loaded {len(stems)} stems")

    # context: prev/next surface per stem (in-ayah)
    by_ayah = defaultdict(list)
    for r in stems:
        try:
            k = (int(r.get("Sura_No", 0)), int(r.get("Verse_No", 0)))
        except ValueError:
            continue
        by_ayah[k].append(r)
    enriched = []
    for k, rows in by_ayah.items():
        rows.sort(key=lambda x: int(x.get("Word_No", 0)))
        for i, r in enumerate(rows):
            prev_surf = (rows[i-1].get("Word") or "").strip() if i > 0 else ""
            next_surf = (rows[i+1].get("Word") or "").strip() if i+1 < len(rows) else ""
            enriched.append({**r, "_prev": prev_surf, "_next": next_surf})
    if args.max:
        enriched = enriched[:args.max]

    print(f"[phase4_{args.mode}] running classifier…")
    clf = WordClassClassifier()

    total = 0
    correct = 0
    by_class_total = Counter()
    by_class_correct = Counter()
    source_dist = Counter()
    # Phase 4 specific metrics
    p4_total_in_scope = 0
    p4_certificate = 0
    p4_hypothesis_meta = 0
    p4_no_change = 0
    by_surface = defaultdict(lambda: {"total": 0, "cert": 0, "hyp": 0, "unres": 0,
                                       "fn": Counter(), "masaq_compat": Counter()})

    for idx, r in enumerate(enriched):
        if idx and idx % 20000 == 0:
            print(f"  …{idx}/{len(enriched)} ({correct/max(total,1)*100:.1f}%)")
        surface = (r.get("Word") or "").strip()
        if not surface: continue
        plain = (r.get("Without_Diacritics") or "").strip()
        gold_tag = (r.get("Morph_Tag") or "").strip()
        gold_wc = masaq_tag_to_word_class(gold_tag)
        if gold_wc == "UNKNOWN": continue

        prev = [r["_prev"]] if r["_prev"] else []
        nxt = [r["_next"]] if r["_next"] else []

        result = clf.classify_with_context(surface, prev_tokens=prev, next_tokens=nxt)
        pred_wc = result.get("word_class", "UNKNOWN")
        src = result.get("source", "")
        src_kind = ("ContextualAmbiguityResolver" if src == "ContextualAmbiguityResolver"
                    else "MASAQ" if src.startswith("MASAQ")
                    else "registry-exact-hypothesis" if "registry-exact-hypothesis" in src
                    else "registry" if "registry" in src
                    else "heuristic")
        source_dist[src_kind] += 1
        total += 1
        by_class_total[gold_wc] += 1
        if pred_wc == gold_wc:
            correct += 1
            by_class_correct[gold_wc] += 1

        # Phase 4 scope?
        if plain in HANDLED:
            p4_total_in_scope += 1
            d = by_surface[plain]
            d["total"] += 1
            if src == "ContextualAmbiguityResolver":
                p4_certificate += 1
                d["cert"] += 1
            elif result.get("phase4_selected_function"):
                p4_hypothesis_meta += 1
                d["hyp"] += 1
            else:
                p4_no_change += 1
                d["unres"] += 1
            fn = result.get("phase4_selected_function", "n/a")
            d["fn"][fn] += 1
            mcc = result.get("phase4_masaq_compatible_class", "")
            if mcc: d["masaq_compat"][mcc] += 1

    # write summary
    summary = out_dir / "summary.txt"
    with summary.open("w", encoding="utf-8") as f:
        f.write(f"PHASE 4 — Full Quran Audit (mode={args.mode})\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total tokens evaluated:  {total}\n")
        f.write(f"Matched MASAQ:           {correct}\n")
        f.write(f"Mismatched:              {total - correct}\n")
        f.write(f"MASAQ-alignment:         {correct/max(total,1)*100:.2f}%\n\n")
        f.write("ACCURACY BY CLASS\n" + "-" * 70 + "\n")
        for wc in sorted(by_class_total):
            c = by_class_correct[wc]; t = by_class_total[wc]
            f.write(f"  {wc:<15} {c}/{t} = {c/max(t,1)*100:.2f}%\n")
        f.write("\nSOURCE DISTRIBUTION\n" + "-" * 70 + "\n")
        for s in sorted(source_dist, key=lambda x: -source_dist[x]):
            cnt = source_dist[s]
            f.write(f"  {s:<35} {cnt} ({cnt/max(total,1)*100:.2f}%)\n")
        f.write("\nPHASE 4 STATS\n" + "-" * 70 + "\n")
        f.write(f"  in_scope_tokens          : {p4_total_in_scope}\n")
        f.write(f"  promoted_to_certificate  : {p4_certificate}\n")
        f.write(f"  hypothesis_metadata_only : {p4_hypothesis_meta}\n")
        f.write(f"  no_change                : {p4_no_change}\n")
    print(f"✓ {summary}")

    # per-surface CSV
    per_surf = out_dir / "per_surface.csv"
    with per_surf.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["surface", "total", "cert", "hyp_meta", "no_change",
                    "top_function", "top_function_count",
                    "top_masaq_class", "top_masaq_count"])
        for s in sorted(by_surface):
            d = by_surface[s]
            top_fn = d["fn"].most_common(1)[0] if d["fn"] else ("", 0)
            top_mc = d["masaq_compat"].most_common(1)[0] if d["masaq_compat"] else ("", 0)
            w.writerow([s, d["total"], d["cert"], d["hyp"], d["unres"],
                        top_fn[0], top_fn[1], top_mc[0], top_mc[1]])
    print(f"✓ {per_surf}")

    # source dist CSV
    src_csv = out_dir / "source_distribution.csv"
    with src_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "count", "pct"])
        for s, c in source_dist.most_common():
            w.writerow([s, c, f"{c/max(total,1)*100:.2f}"])
    print(f"✓ {src_csv}")
    print(f"\n[phase4_{args.mode}] done — alignment={correct/max(total,1)*100:.2f}%")


if __name__ == "__main__":
    main()
