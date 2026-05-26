#!/usr/bin/env python3
"""full_quran_audit.py — تَدقيق شامِل بَعد Phase 3 وَ قَبل Phase 4.

تَوصيَة المُستَخدِم 2026-05-26:
  لا تُكمِل Phase 4 قَبل مَسح كامِل القُرآن.

يُنتِج 6 ملَفّات:
  1. full_quran_regression_summary.txt
  2. full_quran_regression_errors.csv
  3. ambiguity_cases.csv (مَن/ما/متى/أَيّ/أَن/إِن/حَتَّى/غَير/دون)
  4. segmentation_leak_audit.csv (أُولَئِكَ/هَؤُلَاءِ/إِبْرَاهِيم…)
  5. false_event_audit.csv
  6. relation_sanity_audit.csv
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
MASAQ = HERE.parent / "data" / "MASAQ.csv"
OUT_DIR = HERE / "audit_outputs"
OUT_DIR.mkdir(exist_ok=True)

from build_master_token_table import masaq_tag_to_word_class
from i3rab_engine.layer1 import WordClassClassifier

# Tokens we care about for ambiguity audit
AMBIGUOUS_PLAIN = {"من","ما","بما","متى","اي","ايّ","أي","أن","ان","إن",
                   "حتى","غير","دون","الا","إلا","أيا","ايّا"}
# Tokens we care about for segmentation leak
SEG_LEAK_TOKENS = {"اولئك","هؤلاء","ابراهيم","اسماعيل","اسحاق",
                   "هذا","هذه","ذلك","تلك","اللذين","اللاتي"}


def _strip(s):
    DIA = set("ًٌٍَُِّْٰـ")
    return "".join(c for c in (s or "") if c not in DIA)


def load_masaq_stems():
    """يَحَمِّل MASAQ ويُرجِع list[dict] لِكُلّ Stem segment فَريد بِسِياقها."""
    rows_by_word = {}
    all_rows = []
    with MASAQ.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            all_rows.append(row)
    # Group all segments per word for context
    word_segments = defaultdict(list)
    for row in all_rows:
        try:
            k = (int(row.get("Sura_No",0)),
                 int(row.get("Verse_No",0)),
                 int(row.get("Word_No",0)))
        except: continue
        word_segments[k].append(row)
    # Get Stem segment for each word, and prev/next words
    sorted_keys = sorted(word_segments.keys())
    out = []
    for i, k in enumerate(sorted_keys):
        segs = word_segments[k]
        stem = None
        for s in segs:
            if (s.get("Morph_Type") or "").strip() == "Stem":
                stem = s; break
        if stem is None:
            continue
        # prev/next within same surah
        prev_surf = ""
        next_surf = ""
        if i > 0:
            pk = sorted_keys[i-1]
            if pk[0] == k[0] and pk[1] == k[1]:
                p_stem = next((x for x in word_segments[pk] if x.get("Morph_Type")=="Stem"), None)
                if p_stem: prev_surf = (p_stem.get("Word") or "").strip()
        if i < len(sorted_keys)-1:
            nk = sorted_keys[i+1]
            if nk[0] == k[0] and nk[1] == k[1]:
                n_stem = next((x for x in word_segments[nk] if x.get("Morph_Type")=="Stem"), None)
                if n_stem: next_surf = (n_stem.get("Word") or "").strip()
        out.append({**stem, "_prev": prev_surf, "_next": next_surf, "_key": k})
    return out


# ─────────────────────────────────────────────────────────────
# Main audit
# ─────────────────────────────────────────────────────────────

def run_audit(start=0, end=None, checkpoint=None):
    """Chunkable audit. start/end يَحدُد نِطاق tokens."""
    print("Loading MASAQ stems with context…")
    stems = load_masaq_stems()
    if end is None: end = len(stems)
    stems_slice = stems[start:end]
    print(f"  loaded {len(stems)} stems total, processing {len(stems_slice)} ({start}-{end})")
    print()

    clf = WordClassClassifier()
    print("Running classifier on all tokens…")

    total = 0
    correct = 0
    by_class_total = defaultdict(int)
    by_class_correct = defaultdict(int)
    confusion = defaultdict(lambda: Counter())
    source_dist = Counter()
    errors = []
    ambiguity_cases = []
    seg_leak_cases = []

    # Resume from checkpoint if exists
    if checkpoint and checkpoint.exists():
        with checkpoint.open() as f:
            prev = json.load(f)
        total = prev["total"]; correct = prev["correct"]
        by_class_total = defaultdict(int, prev["by_class_total"])
        by_class_correct = defaultdict(int, prev["by_class_correct"])
        confusion = defaultdict(lambda: Counter())
        for k, v in prev["confusion"].items():
            confusion[k] = Counter(v)
        source_dist = Counter(prev["source_dist"])
        errors = prev["errors"]
        ambiguity_cases = prev["ambiguity_cases"]
        seg_leak_cases = prev["seg_leak_cases"]
        print(f"  resumed from checkpoint: {total} done, {correct} correct")

    for idx, row in enumerate(stems_slice):
        if idx and idx % 10000 == 0:
            print(f"  …{idx}/{len(stems)}  ({correct/max(total,1)*100:.1f}%)")
        surface = (row.get("Word") or "").strip()
        if not surface: continue
        plain = (row.get("Without_Diacritics") or "").strip()
        gold_tag = (row.get("Morph_Tag") or "").strip()
        gold_wc = masaq_tag_to_word_class(gold_tag)
        if gold_wc == "UNKNOWN": continue

        result = clf.classify(surface)
        pred_wc = result.get("word_class", "UNKNOWN")
        src = result.get("source", "")
        src_kind = "MASAQ" if src.startswith("MASAQ") else \
                   "registry-exact-hypothesis" if "registry-exact-hypothesis" in src else \
                   "registry" if "registry" in src else \
                   "heuristic"
        source_dist[src_kind] += 1
        total += 1
        by_class_total[gold_wc] += 1

        is_correct = (pred_wc == gold_wc)
        if is_correct:
            correct += 1
            by_class_correct[gold_wc] += 1
        else:
            confusion[gold_wc][pred_wc] += 1
            # error_family
            if gold_wc == "HARF" and pred_wc == "ISM_MAWSOOL":
                family = "harf_vs_mawsool"
            elif gold_wc == "HARF" and pred_wc == "ISM_MABNI":
                family = "harf_vs_mabni"
            elif gold_wc == "ISM_MUARAB" and pred_wc == "FIIL":
                family = "noun_misread_as_verb"
            elif gold_wc == "FIIL" and pred_wc == "ISM_MUARAB":
                family = "verb_misread_as_noun"
            elif gold_wc == "JAMID" and pred_wc == "ISM_MUARAB":
                family = "proper_misclassified"
            else:
                family = f"{gold_wc}_to_{pred_wc}"
            errors.append({
                "surah": row.get("Sura_No"), "ayah": row.get("Verse_No"),
                "token_index": row.get("Word_No"),
                "surface": surface, "plain": plain,
                "prev": row.get("_prev",""), "next": row.get("_next",""),
                "gold_class": gold_wc, "pred_class": pred_wc,
                "candidates": "|".join(result.get("registry_candidates", []) or []),
                "certainty": result.get("proof_kind",""),
                "source": src[:60], "proof_kind": result.get("proof_kind",""),
                "error_family": family,
            })

        # Ambiguity audit
        if plain in AMBIGUOUS_PLAIN or _strip(surface) in AMBIGUOUS_PLAIN:
            ambiguity_cases.append({
                "surah": row.get("Sura_No"), "ayah": row.get("Verse_No"),
                "token_index": row.get("Word_No"),
                "surface": surface, "plain": plain,
                "prev": row.get("_prev",""), "next": row.get("_next",""),
                "gold": gold_wc, "pred": pred_wc,
                "candidates": "|".join(result.get("registry_candidates", []) or []),
                "certainty": result.get("proof_kind",""),
                "needs_context": result.get("registry_requires_context", False),
                "resolution_reason": src[:80],
            })

        # Segmentation leak audit
        if plain in SEG_LEAK_TOKENS or _strip(surface).replace("ٱ","ا") in SEG_LEAK_TOKENS:
            seg_leak_cases.append({
                "surah": row.get("Sura_No"), "ayah": row.get("Verse_No"),
                "token_index": row.get("Word_No"),
                "surface": surface, "plain": plain,
                "gold": gold_wc, "pred": pred_wc,
                "is_match": is_correct,
                "source": src[:60],
                "proof_kind": result.get("proof_kind",""),
            })

    # Save checkpoint
    if checkpoint:
        with checkpoint.open("w") as f:
            json.dump({
                "total": total, "correct": correct,
                "by_class_total": dict(by_class_total),
                "by_class_correct": dict(by_class_correct),
                "confusion": {k: dict(v) for k,v in confusion.items()},
                "source_dist": dict(source_dist),
                "errors": errors,
                "ambiguity_cases": ambiguity_cases,
                "seg_leak_cases": seg_leak_cases,
            }, f, ensure_ascii=False)
        print(f"  checkpoint saved → {checkpoint}")

    print()
    print(f"Done: {correct}/{total} = {correct/total*100:.2f}% MASAQ alignment")
    print()

    # ═══════════════════════════════════════════════════════
    # OUTPUT 1: summary
    # ═══════════════════════════════════════════════════════
    summary_path = OUT_DIR / "full_quran_regression_summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("FULL QURAN REGRESSION SUMMARY (Phase 3 active)\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total tokens evaluated:  {total}\n")
        f.write(f"Matched MASAQ:           {correct}\n")
        f.write(f"Mismatched:              {total - correct}\n")
        f.write(f"MASAQ-alignment:         {correct/total*100:.2f}%\n\n")
        f.write("ACCURACY BY CLASS (MASAQ-aligned only)\n")
        f.write("-"*70 + "\n")
        for wc in sorted(by_class_total):
            c = by_class_correct[wc]; t = by_class_total[wc]
            f.write(f"  {wc:<15s} {c}/{t} = {c/t*100:5.2f}%\n")
        f.write("\nSOURCE DISTRIBUTION (where the answer came from)\n")
        f.write("-"*70 + "\n")
        for s, n in source_dist.most_common():
            f.write(f"  {s:<30s} {n} ({n/total*100:5.2f}%)\n")
        f.write("\nTOP CONFUSION PAIRS (gold → predicted)\n")
        f.write("-"*70 + "\n")
        flat = [(n,e,p) for e,preds in confusion.items() for p,n in preds.items()]
        flat.sort(reverse=True)
        for n,e,p in flat[:20]:
            f.write(f"  {n:5d}  {e:<14s} → {p}\n")
        f.write("\nERROR FAMILIES\n")
        f.write("-"*70 + "\n")
        fam = Counter(err["error_family"] for err in errors)
        for k, n in fam.most_common():
            f.write(f"  {n:5d}  {k}\n")
    print(f"✓ {summary_path}")

    # ═══════════════════════════════════════════════════════
    # OUTPUT 2: errors CSV
    # ═══════════════════════════════════════════════════════
    err_path = OUT_DIR / "full_quran_regression_errors.csv"
    with err_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "surah","ayah","token_index","surface","plain","prev","next",
            "gold_class","pred_class","candidates","certainty","source",
            "proof_kind","error_family"])
        w.writeheader()
        for e in errors: w.writerow(e)
    print(f"✓ {err_path}  ({len(errors)} errors)")

    # ═══════════════════════════════════════════════════════
    # OUTPUT 3: ambiguity cases
    # ═══════════════════════════════════════════════════════
    ambig_path = OUT_DIR / "ambiguity_cases.csv"
    with ambig_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "surah","ayah","token_index","surface","plain","prev","next",
            "gold","pred","candidates","certainty","needs_context","resolution_reason"])
        w.writeheader()
        for c in ambiguity_cases: w.writerow(c)
    print(f"✓ {ambig_path}  ({len(ambiguity_cases)} cases)")

    # ═══════════════════════════════════════════════════════
    # OUTPUT 4: segmentation leak audit
    # ═══════════════════════════════════════════════════════
    seg_path = OUT_DIR / "segmentation_leak_audit.csv"
    with seg_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "surah","ayah","token_index","surface","plain",
            "gold","pred","is_match","source","proof_kind"])
        w.writeheader()
        for c in seg_leak_cases: w.writerow(c)
    seg_total = len(seg_leak_cases)
    seg_match = sum(1 for c in seg_leak_cases if c["is_match"])
    print(f"✓ {seg_path}  ({seg_total} tokens, {seg_match} matched gold)")

    return {
        "total": total, "correct": correct,
        "errors": errors,
        "ambig": ambiguity_cases,
        "seg_leak": seg_leak_cases,
        "source_dist": dict(source_dist),
        "by_class": {wc: (by_class_correct[wc], by_class_total[wc]) for wc in by_class_total},
        "confusion": dict(confusion),
    }


# ─────────────────────────────────────────────────────────────
# OUTPUTS 5 + 6: false events + relation sanity (need sweep)
# ─────────────────────────────────────────────────────────────

def audit_events_relations(stats):
    """يَستَخدِم آخَر sweep لِفَحص الـevents/relations."""
    sweep_files = [
        HERE/"sweep_v9_next1k.jsonl",
        HERE/"sweep_v10_fatiha.jsonl",
        HERE/"sweep_v5.jsonl",
    ]
    all_data = []
    for f in sweep_files:
        if f.exists():
            with f.open() as fh:
                for line in fh:
                    try: all_data.append(json.loads(line))
                    except: pass
    print(f"\nLoaded {len(all_data)} sweep records for event/relation audit\n")

    # OUTPUT 5: false_event_audit
    # نَعتَمِد عَلى MASAQ verb counts كَ ground truth
    masaq_verbs_per_ayah = defaultdict(int)
    for row_key, segs in {(int(r.get("Sura_No",0)),int(r.get("Verse_No",0)),int(r.get("Word_No",0))):None for r in []}.items():
        pass
    # احسِب verbs مِن MASAQ
    import csv as _csv
    with MASAQ.open(encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            if (row.get("Morph_Type") or "").strip() != "Stem": continue
            tag = (row.get("Morph_Tag") or "").strip().upper()
            if tag in ("PV","IV","CV","PV_PASS","IV_PASS"):
                try:
                    k = (int(row.get("Sura_No",0)), int(row.get("Verse_No",0)))
                    masaq_verbs_per_ayah[k] += 1
                except: pass

    false_event_rows = []
    seen_ayahs = set()
    for d in all_data:
        k = (d.get("surah",0), d.get("ayah",0))
        if k in seen_ayahs or k not in masaq_verbs_per_ayah: continue
        seen_ayahs.add(k)
        gold_v = masaq_verbs_per_ayah[k]
        pred_e = d.get("events", 0)
        if pred_e != gold_v:
            false_event_rows.append({
                "surah": k[0], "ayah": k[1],
                "gold_verbs": gold_v,
                "pred_events": pred_e,
                "diff": pred_e - gold_v,
                "diff_type": "over" if pred_e > gold_v else "under",
            })

    fe_path = OUT_DIR / "false_event_audit.csv"
    with fe_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["surah","ayah","gold_verbs","pred_events","diff","diff_type"])
        w.writeheader()
        for r in false_event_rows: w.writerow(r)
    over = sum(1 for r in false_event_rows if r["diff_type"]=="over")
    under = sum(1 for r in false_event_rows if r["diff_type"]=="under")
    print(f"✓ {fe_path}  ({len(false_event_rows)} ayahs, {over} over-generated, {under} under)")

    # OUTPUT 6: relation_sanity_audit
    # نَعتَمِد عَلى Layer 1 source/proof_kind لِكُلّ token
    rel_path = OUT_DIR / "relation_sanity_audit.csv"
    with rel_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric","value","note"])
        w.writerow(["total_sweep_records", len(all_data), "from sweep_v*.jsonl"])
        w.writerow(["ayahs_with_event_mismatch", len(false_event_rows), "vs MASAQ verbs"])
        w.writerow(["event_over_generation", over, ""])
        w.writerow(["event_under_generation", under, ""])
        # Hypothesis tokens fraction (from main audit)
        h_count = stats["source_dist"].get("registry-exact-hypothesis", 0)
        c_count = stats["source_dist"].get("registry", 0)
        m_count = stats["source_dist"].get("MASAQ", 0)
        hr_count = stats["source_dist"].get("heuristic", 0)
        w.writerow(["tokens_from_MASAQ_certificate", m_count, ""])
        w.writerow(["tokens_from_registry_certificate", c_count, ""])
        w.writerow(["tokens_from_registry_hypothesis", h_count,
                    "should NOT issue Event/relation Certificate"])
        w.writerow(["tokens_from_heuristics", hr_count, ""])
    print(f"✓ {rel_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--skip-events", action="store_true")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--checkpoint", type=str, default=str(OUT_DIR/"audit_checkpoint.json"))
    p.add_argument("--finalize", action="store_true", help="write CSVs from checkpoint")
    args = p.parse_args()

    ckpt_path = Path(args.checkpoint)
    if args.finalize:
        # Just write CSVs from existing checkpoint
        if not ckpt_path.exists():
            print(f"ERROR: checkpoint not found: {ckpt_path}")
            sys.exit(1)
        # Re-run with no new tokens (just to trigger CSV writes)
        stats = run_audit(start=0, end=0, checkpoint=ckpt_path)
    else:
        stats = run_audit(start=args.start, end=args.end, checkpoint=ckpt_path)
    if not args.skip_events:
        audit_events_relations(stats)

    print(f"\n{'='*70}")
    print(f"AUDIT COMPLETE → {OUT_DIR}/")
    print(f"{'='*70}\n")
