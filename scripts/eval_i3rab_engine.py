"""eval_i3rab_engine.py — Evaluate i3rab_engine against quran_i3rab_labels.jsonl.

Per-token comparison: our predicted (WordClass, Case) vs the canonical
labels heuristically extracted from the corpus. Reports agreement %.

Output: data/eval/i3rab_engine_eval.csv
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "clean_code"))

from i3rab_engine import I3rabEngine  # type: ignore

LABELS_PATH = Path(
    "/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"
)
if not LABELS_PATH.is_file():
    LABELS_PATH = Path(
        "/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl"
    )

OUT_DIR = ROOT / "data" / "eval"
OUT_PATH = OUT_DIR / "i3rab_engine_eval.csv"


# Map our WordClass → canonical labels we'd expect
_WC_TO_CANON = {
    "HARF": {"HARF"},
    "ISM_MABNI": {"MABNI", "ISM"},
    "ISM_MUARAB": {"ISM"},
    "JAMID": {"ISM"},
    "AALAM": {"ISM"},
    "FIIL": {"FIIL"},
    "JALALAH": {"ISM"},
}

_CASE_TO_CANON = {
    1: "MARFOO",
    2: "MANSOOB",
    3: "MAJROOR",
    4: "MAJZOOM",
    5: "MABNI",
}


def main(max_ayahs: int = 0) -> int:
    if not LABELS_PATH.is_file():
        print(f"error: labels file not found: {LABELS_PATH}", file=sys.stderr)
        return 1

    # Group labels by (surah, ayah)
    ayahs: dict[tuple[int, int], list[dict]] = defaultdict(list)
    with LABELS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                key = (int(d["surah"]), int(d["ayah"]))
                ayahs[key].append(d)
            except Exception:
                continue

    # Order ayahs and limit
    keys = sorted(ayahs.keys())
    if max_ayahs:
        keys = keys[:max_ayahs]

    eng = I3rabEngine()

    # Counters
    stats = Counter()
    wc_confusion = Counter()
    case_confusion = Counter()
    # Proof-theoretic counters (Certificate/Hypothesis/Zero per layer)
    proof_kinds = Counter()  # ('layer', 'kind') → count
    rows = []

    for s, a in keys:
        tokens_data = ayahs[(s, a)]
        text = " ".join(d["word"] for d in tokens_data)
        sent = eng.analyze_sentence(text)
        # Pair predictions with labels (same index — both come from same word list)
        for i, (pred_tok, lbl_data) in enumerate(zip(sent.tokens, tokens_data)):
            stats["total_tokens"] += 1
            labels = set(lbl_data.get("labels", []))

            # === WordClass agreement ===
            expected_wc_set = set()
            if "HARF" in labels:
                expected_wc_set.add("HARF")
            if "FIIL" in labels:
                expected_wc_set.add("FIIL")
            if "ISM" in labels:
                # Could be ISM_MUARAB / ISM_MABNI / JAMID / AALAM
                if "MABNI" in labels and not any(l.startswith("HARF") for l in labels):
                    expected_wc_set.add("ISM_MABNI")
                else:
                    expected_wc_set.update({"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"})
            # If no clear expected, treat as "no_signal"
            wc_match = pred_tok.word_class in expected_wc_set if expected_wc_set else None

            if wc_match is True:
                stats["wc_agree"] += 1
            elif wc_match is False:
                stats["wc_disagree"] += 1
                wc_confusion[(pred_tok.word_class, tuple(sorted(expected_wc_set)))] += 1
            else:
                stats["wc_no_signal"] += 1

            # === Case agreement ===
            expected_case = None
            for c in ("MARFOO", "MANSOOB", "MAJROOR", "MAJZOOM", "MABNI"):
                if c in labels:
                    expected_case = c
                    break
            pred_case = _CASE_TO_CANON.get(pred_tok.case_id) if pred_tok.case_id else None

            if expected_case and pred_case:
                if expected_case == pred_case:
                    stats["case_agree"] += 1
                else:
                    stats["case_disagree"] += 1
                    case_confusion[(pred_case, expected_case)] += 1
            elif expected_case and not pred_case:
                stats["case_missing"] += 1
            elif not expected_case and pred_case:
                stats["case_extra"] += 1
            else:
                stats["case_no_signal"] += 1

            # === Proof-theoretic counters ===
            if pred_tok.wordclass_kind:
                proof_kinds[("wordclass", pred_tok.wordclass_kind)] += 1
            if pred_tok.case_kind:
                proof_kinds[("case", pred_tok.case_kind)] += 1
            if pred_tok.role_kind:
                proof_kinds[("role", pred_tok.role_kind)] += 1

            # Record row
            rows.append({
                "surah": s,
                "ayah": a,
                "position": i,
                "token": pred_tok.token,
                "pred_word_class": pred_tok.word_class,
                "expected_wc_set": "|".join(sorted(expected_wc_set)) or "—",
                "wc_match": "Y" if wc_match else ("N" if wc_match is False else "—"),
                "pred_case": pred_case or "—",
                "expected_case": expected_case or "—",
                "case_match": (
                    "Y" if (expected_case and pred_case and expected_case == pred_case)
                    else ("N" if (expected_case and pred_case) else "—")
                ),
                "pred_role": pred_tok.role_phrase,
                "labels": "|".join(sorted(labels)),
                "wc_kind": pred_tok.wordclass_kind,
                "case_kind": pred_tok.case_kind,
                "role_kind": pred_tok.role_kind,
                "wc_contract": pred_tok.wordclass_contract,
                "case_contract": pred_tok.case_contract,
                "role_contract": pred_tok.role_contract,
            })

    # Write CSV
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "surah", "ayah", "position", "token", "pred_word_class",
            "expected_wc_set", "wc_match", "pred_case", "expected_case",
            "case_match", "pred_role", "labels",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Print summary
    total = stats["total_tokens"]
    print(f"=== i3rab_engine evaluation ===")
    print(f"Ayahs scored: {len(keys)}")
    print(f"Total tokens: {total}")
    print()
    print("--- WordClass agreement ---")
    if total > 0:
        agree = stats["wc_agree"]
        disagree = stats["wc_disagree"]
        nosignal = stats["wc_no_signal"]
        comparable = agree + disagree
        if comparable > 0:
            print(f"  Agree:       {agree:>6} ({100*agree/comparable:.1f}% of comparable)")
            print(f"  Disagree:    {disagree:>6} ({100*disagree/comparable:.1f}% of comparable)")
        print(f"  No signal:   {nosignal:>6} ({100*nosignal/total:.1f}% of total)")
    print()
    print("--- Case agreement ---")
    agree = stats["case_agree"]
    disagree = stats["case_disagree"]
    missing = stats["case_missing"]
    extra = stats["case_extra"]
    nosignal = stats["case_no_signal"]
    comparable = agree + disagree
    if comparable > 0:
        print(f"  Agree:       {agree:>6} ({100*agree/comparable:.1f}% of comparable)")
        print(f"  Disagree:    {disagree:>6} ({100*disagree/comparable:.1f}% of comparable)")
    print(f"  Missing:     {missing:>6} (we have no prediction)")
    print(f"  Extra:       {extra:>6} (we predicted, no label)")
    print(f"  No signal:   {nosignal:>6}")
    print()
    print("--- Top 10 WordClass confusions (predicted → expected) ---")
    for (pred, exp), n in wc_confusion.most_common(10):
        print(f"  {pred:<14} → {exp[0] if exp else 'EMPTY':<20} ({n})")
    print()
    print("--- Top 5 Case confusions (predicted → expected) ---")
    for (pred, exp), n in case_confusion.most_common(5):
        print(f"  {pred:<10} → {exp:<10} ({n})")
    print()
    print("─" * 60)
    print("=== Proof-theoretic breakdown (Certificate/Hypothesis/Zero) ===")
    print("─" * 60)
    print(f"{'Layer':<12} {'Certificate':>12} {'Hypothesis':>12} {'Zero':>8} {'%C':>6} {'%H':>6} {'%Z':>6}")
    for layer in ("wordclass", "case", "role"):
        c = proof_kinds.get((layer, "Certificate"), 0)
        h = proof_kinds.get((layer, "Hypothesis"), 0)
        z = proof_kinds.get((layer, "Zero"), 0)
        tot = c + h + z
        if tot:
            print(
                f"{layer:<12} {c:>12} {h:>12} {z:>8} "
                f"{100*c/tot:>5.1f}% {100*h/tot:>5.1f}% {100*z/tot:>5.1f}%"
            )
    print()
    print(f"Per-token CSV: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--max-ayahs", type=int, default=0,
                   help="Limit number of ayahs (0 = all)")
    args = p.parse_args()
    sys.exit(main(max_ayahs=args.max_ayahs))
