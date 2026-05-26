#!/usr/bin/env python3
"""audit_harness.py — تَدقيق شامِل بِلا data leakage.

يُجري:
  AUDIT-2: ablation عَلى 3 modes (lookup-only، heuristic-only، hybrid)
  AUDIT-3: holdout 80/20 — بِناء جَدول مِن 80% وَ اختبار 20% (seen vs OOV)
  AUDIT-4: source conflict (MASAQ vs MEEMAR) — أَيّ Certificate رُغم خِلاف
  AUDIT-6: regression_errors.csv بِالشَّكل المُحَدَّد

التَّسميَة الصَّحيحَة لِكُلّ رَقم: "MASAQ alignment" لا "Arabic accuracy".
"""
import argparse
import csv
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
MASAQ = HERE.parent / "data" / "MASAQ.csv"
MEEMAR = HERE.parent / "data" / "MEEMAR.csv"

random.seed(42)

from build_master_token_table import masaq_tag_to_word_class


def load_masaq_words():
    """يَحَمِّل MASAQ ويُرجِع list[dict] لِكُلّ Stem segment فَريد."""
    seen = {}
    with MASAQ.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Morph_Type") != "Stem":
                continue
            key = (int(row.get("Sura_No",0)),
                   int(row.get("Verse_No",0)),
                   int(row.get("Word_No",0)))
            if key in seen:
                continue
            seen[key] = row
    return list(seen.values())


def evaluate(items, classify_fn, label=""):
    """يُقَيِّم classify_fn عَلى items. يُرجِع dict إِحصائيّ."""
    total = 0
    correct = 0
    by_class_total = defaultdict(int)
    by_class_correct = defaultdict(int)
    confusion = defaultdict(lambda: Counter())
    src_dist = Counter()
    none_count = 0
    for row in items:
        surface = (row.get("Word") or "").strip()
        if not surface:
            continue
        expected_tag = (row.get("Morph_Tag") or "").strip()
        expected_wc = masaq_tag_to_word_class(expected_tag)
        if expected_wc == "UNKNOWN":
            continue
        result = classify_fn(surface)
        if result is None:
            none_count += 1
            predicted_wc = "UNKNOWN"
            src = "no_classifier_answer"
        else:
            predicted_wc = result.get("word_class", "UNKNOWN")
            src = result.get("source", "")
        src_key = src.split(":")[0] or "unknown"
        src_dist[src_key] += 1
        total += 1
        by_class_total[expected_wc] += 1
        if predicted_wc == expected_wc:
            correct += 1
            by_class_correct[expected_wc] += 1
        else:
            confusion[expected_wc][predicted_wc] += 1
    return {
        "label": label,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0,
        "none_count": none_count,
        "by_class": {wc: (by_class_correct[wc], by_class_total[wc])
                     for wc in by_class_total},
        "confusion": {e: dict(p) for e, p in confusion.items()},
        "src_dist": dict(src_dist),
    }


def print_eval(stats):
    print(f"\n— {stats['label']} —")
    print(f"  total:    {stats['total']}")
    print(f"  correct:  {stats['correct']}")
    print(f"  accuracy: {stats['accuracy']*100:.2f}%")
    print(f"  no-answer (UNKNOWN): {stats['none_count']}")
    print(f"  per-class accuracy:")
    for wc in sorted(stats["by_class"]):
        c, t = stats["by_class"][wc]
        print(f"    {wc:<14s} {c}/{t} = {c/t*100:5.1f}%" if t else f"    {wc}: 0/0")
    print(f"  top confusions:")
    flat = [(n, e, p) for e, preds in stats["confusion"].items()
            for p, n in preds.items()]
    flat.sort(reverse=True)
    for n, e, p in flat[:5]:
        print(f"    {n:4d}  {e:<14s} → {p}")
    print(f"  source distribution:")
    for src, n in sorted(stats["src_dist"].items(), key=lambda x: -x[1])[:5]:
        print(f"    {src:<25s} {n}")


# ─────────────────────────────────────────────────────────────
# Three modes
# ─────────────────────────────────────────────────────────────

def mode_lookup_only():
    """Mode A: MASAQ lookup فَقَط، لا heuristics."""
    from master_token_lookup import lookup
    return lookup


def mode_heuristic_only():
    """Mode B: heuristics فَقَط (Layer 1 بِدون Step 0)."""
    # نُعَطِّل master_token_lookup مُؤَقَّتًا
    import master_token_lookup
    saved = master_token_lookup.lookup
    master_token_lookup.lookup = lambda t: None
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    def classify(t):
        return clf.classify(t)
    return classify, lambda: setattr(master_token_lookup, "lookup", saved)


def mode_hybrid_closed_only():
    """Mode C: lookup لِلـclosed classes فَقَط (HARF/ISM_MABNI/ISM_MAWSOOL/JAMID)."""
    from master_token_lookup import lookup as raw_lookup
    OPEN_CLASSES = {"FIIL", "ISM_MUARAB"}  # هَذه نَترُكها لِلـheuristics
    def lookup_closed_only(t):
        e = raw_lookup(t)
        if e and e.get("word_class") in OPEN_CLASSES:
            return None  # خَلِّ heuristics تَتَكَفَّل
        return e
    import master_token_lookup
    saved = master_token_lookup.lookup
    master_token_lookup.lookup = lookup_closed_only
    from i3rab_engine.layer1 import WordClassClassifier
    # نَحتاج إِعادَة تَحميل لِيَلتَقِط الـlookup المُعَدَّل
    import importlib
    from i3rab_engine import layer1 as l1
    importlib.reload(l1)
    clf = l1.WordClassClassifier()
    def classify(t):
        return clf.classify(t)
    return classify, lambda: setattr(master_token_lookup, "lookup", saved)


def run_three_modes(sample_size=None):
    print("\n" + "═"*70)
    print("AUDIT-2: 3 MODES — same data, different classifiers")
    print("═"*70)
    items = load_masaq_words()
    if sample_size:
        random.shuffle(items)
        items = items[:sample_size]
    print(f"Evaluating {len(items)} tokens\n")

    # Mode A: lookup-only
    print("Loading Mode A: lookup-only…")
    lookup = mode_lookup_only()
    a_stats = evaluate(items, lookup, "Mode A — lookup-only (MASAQ table)")
    print_eval(a_stats)

    # Mode B: heuristics-only
    print("\nLoading Mode B: heuristics-only (lookup disabled)…")
    fn_b, restore_b = mode_heuristic_only()
    b_stats = evaluate(items, fn_b, "Mode B — heuristics-only (no MASAQ lookup)")
    print_eval(b_stats)
    restore_b()

    # Mode C: hybrid (closed-class lookup only)
    print("\nLoading Mode C: hybrid (lookup for closed classes only)…")
    fn_c, restore_c = mode_hybrid_closed_only()
    c_stats = evaluate(items, fn_c, "Mode C — hybrid (lookup ⊕ heuristics for open)")
    print_eval(c_stats)
    restore_c()

    print("\n" + "─"*70)
    print("COMPARISON")
    print("─"*70)
    print(f"  Mode A (lookup-only):       {a_stats['accuracy']*100:.2f}%")
    print(f"  Mode B (heuristics-only):   {b_stats['accuracy']*100:.2f}%")
    print(f"  Mode C (hybrid):            {c_stats['accuracy']*100:.2f}%")
    print()
    print("INTERPRETATION:")
    print(f"  A: high but TRIVIAL (memorized) — proves table lookup works.")
    print(f"  B: the REAL generalization metric — heuristics on unseen surfaces.")
    print(f"  C: best of both — closed classes from lookup, open from rules.")


# ─────────────────────────────────────────────────────────────
# AUDIT-3: holdout 80/20
# ─────────────────────────────────────────────────────────────

def build_holdout_table(train_items, out_path):
    """يَبني master_token_table.csv مِن train_items فَقَط (80%)."""
    from build_master_token_table import (
        masaq_tag_to_word_class, aspect_of, load_meemar_index,
    )
    meem = load_meemar_index()
    surface_entries = {}
    for row in train_items:
        key = (int(row.get("Sura_No",0)),
               int(row.get("Verse_No",0)),
               int(row.get("Word_No",0)))
        surface = (row.get("Word") or "").strip()
        plain = (row.get("Without_Diacritics") or "").strip()
        tag = (row.get("Morph_Tag") or "").strip()
        wc = masaq_tag_to_word_class(tag)
        meem_row = meem.get(key, {})
        entry = {
            "surface": surface, "plain": plain, "word_class": wc,
            "masaq_tag": tag, "lemma": "", "root": meem_row.get("root",""),
            "wazn": meem_row.get("wazn",""), "aspect": aspect_of(tag),
            "case": (row.get("Case_Mood") or "").strip(),
            "role": (row.get("Syntactic_Role") or "").strip(),
            "source": f"MASAQ:{row.get('ID','')}",
            "agreement_with_masaq": meem_row.get("agreement","Unknown"),
            "confidence": "Certificate",
            "first_seen_at": f"{key[0]}:{key[1]}:{key[2]}",
        }
        if surface and surface not in surface_entries:
            surface_entries[surface] = entry
    fields = ["surface","plain","word_class","masaq_tag","lemma","root","wazn",
              "aspect","case","role","source","agreement_with_masaq",
              "confidence","first_seen_at","ambiguous"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for surf, e in sorted(surface_entries.items()):
            row = {k: e.get(k, "") for k in fields}
            w.writerow(row)
    return len(surface_entries)


def run_holdout():
    print("\n" + "═"*70)
    print("AUDIT-3: HOLDOUT 80/20 — generalization to unseen tokens")
    print("═"*70)
    items = load_masaq_words()
    random.shuffle(items)
    split = int(len(items) * 0.8)
    train, test = items[:split], items[split:]
    print(f"Train: {len(train)} tokens   Test: {len(test)} tokens")

    train_surfaces = {(r.get("Word") or "").strip() for r in train}
    seen_in_test = [r for r in test if (r.get("Word") or "").strip() in train_surfaces]
    unseen_in_test = [r for r in test if (r.get("Word") or "").strip() not in train_surfaces]
    print(f"Test breakdown: seen={len(seen_in_test)}  unseen(OOV)={len(unseen_in_test)}")

    # نَبني جَدول مِن train فَقَط
    holdout_path = HERE / "data" / "master_token_table_holdout.csv"
    n_built = build_holdout_table(train, holdout_path)
    print(f"Built holdout table: {n_built} unique surfaces\n")

    # نُبَدِّل الـtable في الـlookup
    import master_token_lookup as mtl
    saved_path = mtl._TABLE_PATH
    mtl._TABLE_PATH = holdout_path
    mtl._EXACT_INDEX = None  # force reload
    mtl._PLAIN_INDEX = None
    mtl._NORMALIZED_INDEX = None

    import importlib
    from i3rab_engine import layer1 as l1
    importlib.reload(l1)
    clf = l1.WordClassClassifier()
    def classify(t): return clf.classify(t)

    # قَيِّم عَلى seen vs unseen
    seen_stats = evaluate(seen_in_test, classify, "TEST — SEEN tokens (in training set)")
    unseen_stats = evaluate(unseen_in_test, classify,
                            "TEST — UNSEEN tokens (OOV — true generalization)")
    print_eval(seen_stats)
    print_eval(unseen_stats)

    # رَجِّع
    mtl._TABLE_PATH = saved_path
    mtl._EXACT_INDEX = None

    print("\n" + "─"*70)
    print("HOLDOUT RESULTS")
    print("─"*70)
    print(f"  SEEN (lookup hit):    {seen_stats['accuracy']*100:.2f}%   ← trivial (memorized)")
    print(f"  UNSEEN/OOV:           {unseen_stats['accuracy']*100:.2f}%   ← TRUE generalization")
    print()
    print("INTERPRETATION:")
    print(f"  SEEN accuracy tests memorization (should be ~100%).")
    print(f"  UNSEEN accuracy tests heuristic generalization to new surfaces.")
    print(f"  GAP between them = how much we rely on memorization.")


# ─────────────────────────────────────────────────────────────
# AUDIT-4: source conflict (MASAQ vs MEEMAR)
# ─────────────────────────────────────────────────────────────

def run_source_conflict_audit():
    print("\n" + "═"*70)
    print("AUDIT-4: SOURCE CONFLICTS (MASAQ vs MEEMAR)")
    print("═"*70)
    items = load_masaq_words()
    from build_master_token_table import load_meemar_index
    meem = load_meemar_index()

    # نَفحَص الـAgreement_With_MASAQ مِن MEEMAR rows
    conflicts = 0
    cert_with_conflict = 0
    agreement_dist = Counter()
    for row in items:
        key = (int(row.get("Sura_No",0)),
               int(row.get("Verse_No",0)),
               int(row.get("Word_No",0)))
        masaq_tag = (row.get("Morph_Tag") or "").strip()
        masaq_wc = masaq_tag_to_word_class(masaq_tag)
        meem_row = meem.get(key, {})
        agreement = meem_row.get("agreement", "Unknown")
        agreement_dist[agreement] += 1
        if agreement in ("Partial", "None", "Disagree"):
            conflicts += 1
            # هَل master_token_table يُصدِر Certificate رُغم الخِلاف؟
            # في بِنائنا الحاليّ: نَعَم — confidence = Certificate دائِمًا
            cert_with_conflict += 1

    print(f"Total tokens:      {len(items)}")
    print(f"Agreement distribution:")
    for k, v in agreement_dist.most_common():
        print(f"  {k:<15s} {v} ({v/len(items)*100:.1f}%)")
    print(f"\nTokens with MASAQ-MEEMAR conflict:  {conflicts} ({conflicts/len(items)*100:.1f}%)")
    print(f"Certificates issued despite conflict: {cert_with_conflict}")
    print()
    print("INTERPRETATION:")
    print(f"  Per user spec: any disagreement → Hypothesis, not Certificate.")
    print(f"  Current build script: ALL entries get Certificate.")
    print(f"  → {cert_with_conflict} entries should be downgraded to Hypothesis.")


# ─────────────────────────────────────────────────────────────
# AUDIT-6: regression_errors.csv
# ─────────────────────────────────────────────────────────────

def export_regression_errors(out_path):
    print("\n" + "═"*70)
    print("AUDIT-6: EXPORT regression_errors.csv")
    print("═"*70)
    items = load_masaq_words()
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()

    errors = []
    for row in items:
        surface = (row.get("Word") or "").strip()
        if not surface: continue
        plain = (row.get("Without_Diacritics") or "").strip()
        gold_tag = (row.get("Morph_Tag") or "").strip()
        gold_wc = masaq_tag_to_word_class(gold_tag)
        if gold_wc == "UNKNOWN": continue
        result = clf.classify(surface)
        pred_wc = result.get("word_class", "UNKNOWN")
        if pred_wc == gold_wc: continue
        # حَدِّد error_family
        if gold_wc == "HARF" and pred_wc == "ISM_MAWSOOL":
            family = "harf_vs_mawsool_ambiguity"
        elif gold_wc == "ISM_MUARAB" and pred_wc == "FIIL":
            family = "noun_misread_as_verb"
        elif gold_wc == "FIIL" and pred_wc == "ISM_MUARAB":
            family = "verb_misread_as_noun"
        elif gold_wc == "JAMID" and pred_wc == "ISM_MUARAB":
            family = "proper_noun_misclassified"
        else:
            family = f"{gold_wc}_to_{pred_wc}"
        errors.append({
            "ayah": f"{row.get('Sura_No')}:{row.get('Verse_No')}",
            "token_index": row.get("Word_No"),
            "surface": surface,
            "plain": plain,
            "gold_class": gold_wc,
            "predicted_class": pred_wc,
            "source": result.get("source", "")[:60],
            "proof_kind": result.get("proof_kind", ""),
            "error_family": family,
        })

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "ayah","token_index","surface","plain","gold_class",
            "predicted_class","source","proof_kind","error_family"])
        w.writeheader()
        for e in errors:
            w.writerow(e)
    print(f"Wrote {len(errors)} errors to {out_path}")
    fam = Counter(e["error_family"] for e in errors)
    print(f"Error families:")
    for f, n in fam.most_common():
        print(f"  {n:5d}  {f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--audit", choices=["2","3","4","6","all"], default="all")
    p.add_argument("--sample", type=int, default=10000,
                   help="عَدَد tokens لِلـmodes test")
    args = p.parse_args()

    if args.audit in ("2","all"):
        run_three_modes(sample_size=args.sample)
    if args.audit in ("3","all"):
        run_holdout()
    if args.audit in ("4","all"):
        run_source_conflict_audit()
    if args.audit in ("6","all"):
        export_regression_errors(HERE / "regression_errors.csv")
