"""eval_accuracy_vs_meemar.py — قياس دِقَّة فِعليّ ضِدّ MEEMAR.csv (ground truth).

MEEMAR.csv هي ground truth بَشَريّ-مُراجَع لِكُلّ كَلِمَة في القُرآن مَع
صِفاتِها الصَّرفيَّة/الإِعرابيَّة:
  • Our_Root            — الجَذر الصَّحيح
  • Our_Wazn            — الوَزن الصَّحيح
  • Invariable_Declinable / مبني_معرب — مَبني أَو مُعرَب
  • Morph_Type / النوع_الموضعي — Prefix/Stem/Suffix
  • Case_Mood / الحالة_الإعرابية — الحالة

MEEMAR مُقَطَّعَة (segmented): كُلّ كَلِمَة مُقَسَّمَة إلى عِدَّة صُفوف
(prefix/stem/suffix). لِلمُقارَنَة مَع مُحَلِّلنا الَّذي يَعمَل على
الكَلِمَة الكامِلَة، نَأخُذ الصَّفّ الَّذي Morph_Type=STEM كَ الجَذر/الوَزن
المَرجِع.

النَّتائج:
  - دِقَّة الجَذر (root_accuracy)
  - دِقَّة الوَزن (wazn_accuracy)
  - دِقَّة التَّمييز مَبني/مُعرَب
  - دِقَّة status: مَع MEEMAR Morph_Tag (HARF→closed_class، STEM→...)

النَّتائج → data/eval/full_quran_accuracy_vs_meemar.json
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "clean_code"))

from root_pipeline import RootPipeline
from clause_segmenter import _strip_pause_marks


MEEMAR_PATH = _REPO / "data" / "MEEMAR.csv"
QURAN_PATH = _REPO / "data" / "quran-uthmani-with-pause-mark.txt"
OUT_PATH = _REPO / "data" / "eval" / "full_quran_accuracy_vs_meemar.json"
OUT_MD = _REPO / "data" / "eval" / "full_quran_accuracy_vs_meemar.md"
STATE = _REPO / "data" / "eval" / "accuracy_eval_state.json"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in "ًٌٍَُِّْـٰٓ")


def _normalize(s: str) -> str:
    """Match MEEMAR's `Without_Diacritics` style."""
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("ٲ", "ا").replace("ٳ", "ا")
    return s


def _load_meemar_ground_truth():
    """Build: (sura, verse, word_no) → {root, wazn, invariable, morph_type, ...}

    Aggregate per (sura, verse, word_no): we pick the STEM row when available,
    otherwise the first row.
    """
    by_word = {}
    if not MEEMAR_PATH.exists():
        return by_word
    with MEEMAR_PATH.open("r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            try:
                s = int(row["Sura_No"])
                v = int(row["Verse_No"])
                w = int(row["Word_No"])
            except Exception:
                continue
            key = (s, v, w)
            morph_type = (row.get("Morph_Type / النوع_الموضعي") or "").strip()
            # Prefer STEM rows; only overwrite if current key has no STEM yet
            if key in by_word and "STEM" in (by_word[key].get("morph_type") or ""):
                continue
            by_word[key] = {
                "word": row.get("Word", ""),
                "segmented": row.get("Segmented_Word", ""),
                "root": (row.get("Our_Root") or "").strip(),
                "wazn": (row.get("Our_Wazn") or "").strip(),
                "morph_type": morph_type,
                "invariable": (row.get("Invariable_Declinable / مبني_معرب") or "").strip(),
                "case": (row.get("Case_Mood / الحالة_الإعرابية") or "").strip(),
                "morph_tag": (row.get("Morph_Tag") or "").strip(),
            }
    return by_word


def _load_quran_verses():
    verses = []
    if not QURAN_PATH.exists():
        return verses
    with QURAN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|", 2)
            if len(parts) == 3:
                s, v, text = parts
                verses.append((int(s), int(v), _strip_pause_marks(text)))
    return verses


def _is_invariable(meemar_row) -> bool | None:
    """Return True if مَبني, False if مُعرَب, None if unclear."""
    inv = meemar_row.get("invariable", "")
    if "INVARIABLE" in inv or "مبني" in inv:
        return True
    if "DECLINABLE" in inv or "معرب" in inv:
        return False
    return None


def _our_is_invariable(status: str, word_class: str = "") -> bool | None:
    """Map our status to مَبني/مُعرَب prediction."""
    if status in ("closed_class", "singular_term"):
        return True  # singular_term not really invariable but no inflection
    if status in ("open_class", "jamid"):
        return False
    return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seconds", type=int, default=38)
    ap.add_argument("--restart", action="store_true")
    args = ap.parse_args()

    import time
    print("Loading MEEMAR ground truth...")
    meemar = _load_meemar_ground_truth()
    print(f"  {len(meemar)} (sura, verse, word) entries")

    verses = _load_quran_verses()
    print(f"Loaded {len(verses)} verses")

    pipe = RootPipeline()

    # Load state if exists
    if STATE.exists() and not args.restart:
        s = json.loads(STATE.read_text(encoding="utf-8"))
        start_idx = s["next_idx"]
        n_compared = s["n_compared"]
        n_root_correct = s["n_root_correct"]
        n_root_meemar_has = s["n_root_meemar_has"]
        n_wazn_correct = s["n_wazn_correct"]
        n_wazn_meemar_has = s["n_wazn_meemar_has"]
        n_invariable_correct = s["n_invariable_correct"]
        n_invariable_meemar_has = s["n_invariable_meemar_has"]
        root_mismatches = Counter({tuple(k.split("|||")): v for k, v in s["root_mismatches"].items()})
        wazn_mismatches = Counter({tuple(k.split("|||")): v for k, v in s["wazn_mismatches"].items()})
        inv_confusion = Counter({tuple(k.split("|||")): v for k, v in s["inv_confusion"].items()})
        print(f"Resuming from verse idx {start_idx}")
    else:
        start_idx = 0
        n_compared = 0
        n_root_correct = 0
        n_root_meemar_has = 0
        n_wazn_correct = 0
        n_wazn_meemar_has = 0
        n_invariable_correct = 0
        n_invariable_meemar_has = 0
        root_mismatches = Counter()
        wazn_mismatches = Counter()
        inv_confusion = Counter()

    t0 = time.time()

    # Walk verses → words
    i = start_idx
    while i < len(verses) and (time.time() - t0) < args.max_seconds:
        s, v, text = verses[i]
        words = text.split()
        for w_idx, word in enumerate(words, start=1):
            key = (s, v, w_idx)
            if key not in meemar:
                continue
            gt = meemar[key]
            ours = pipe.analyze(word)
            n_compared += 1

            # ── Root accuracy ──
            our_root = (getattr(ours, "root", "") or "").strip()
            gt_root = gt["root"].strip()
            if gt_root and gt_root not in {"—", "-"}:
                n_root_meemar_has += 1
                # Normalize for comparison
                our_r_norm = _normalize(our_root) if our_root not in {"—", ""} else ""
                gt_r_norm = _normalize(gt_root)
                if our_r_norm == gt_r_norm:
                    n_root_correct += 1
                else:
                    root_mismatches[(our_root or "(none)", gt_root)] += 1

            # ── Wazn accuracy ──
            our_wazn = (getattr(ours, "wazn", "") or "").strip()
            # Prefer canonical_wazn if available
            canon = (getattr(ours, "canonical_wazn", "") or "").strip()
            if canon:
                our_wazn = canon
            gt_wazn = gt["wazn"].strip()
            if gt_wazn and gt_wazn not in {"—", "-"}:
                n_wazn_meemar_has += 1
                our_w_norm = _normalize(our_wazn) if our_wazn not in {"—", ""} else ""
                gt_w_norm = _normalize(gt_wazn)
                if our_w_norm == gt_w_norm:
                    n_wazn_correct += 1
                else:
                    wazn_mismatches[(our_wazn or "(none)", gt_wazn)] += 1

            # ── مَبني/مُعرَب accuracy ──
            gt_inv = _is_invariable(gt)
            our_inv = _our_is_invariable(getattr(ours, "status", ""))
            if gt_inv is not None and our_inv is not None:
                n_invariable_meemar_has += 1
                if gt_inv == our_inv:
                    n_invariable_correct += 1
                else:
                    inv_confusion[(our_inv, gt_inv)] += 1
        i += 1

    # Save state
    STATE.write_text(json.dumps({
        "next_idx": i,
        "n_compared": n_compared,
        "n_root_correct": n_root_correct,
        "n_root_meemar_has": n_root_meemar_has,
        "n_wazn_correct": n_wazn_correct,
        "n_wazn_meemar_has": n_wazn_meemar_has,
        "n_invariable_correct": n_invariable_correct,
        "n_invariable_meemar_has": n_invariable_meemar_has,
        "root_mismatches": {"|||".join(map(str, k)): v for k, v in root_mismatches.items()},
        "wazn_mismatches": {"|||".join(map(str, k)): v for k, v in wazn_mismatches.items()},
        "inv_confusion": {"|||".join(map(str, k)): v for k, v in inv_confusion.items()},
    }, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - t0
    print(f"Processed {i - start_idx} verses in {elapsed:.1f}s")
    print(f"Progress: {i}/{len(verses)} ({i/len(verses)*100:.1f}%)")

    if i < len(verses):
        print("(not finished — re-run to continue)")
        return

    # ── Build result ──
    def pct(a, b):
        return round(a / b * 100, 2) if b else 0.0

    result = {
        "n_meemar_entries": len(meemar),
        "n_verses": len(verses),
        "n_words_compared": n_compared,
        "root": {
            "meemar_has_root": n_root_meemar_has,
            "correct": n_root_correct,
            "accuracy_pct": pct(n_root_correct, n_root_meemar_has),
        },
        "wazn": {
            "meemar_has_wazn": n_wazn_meemar_has,
            "correct": n_wazn_correct,
            "accuracy_pct": pct(n_wazn_correct, n_wazn_meemar_has),
        },
        "invariable_vs_declinable": {
            "comparable": n_invariable_meemar_has,
            "correct": n_invariable_correct,
            "accuracy_pct": pct(n_invariable_correct, n_invariable_meemar_has),
        },
        "top_root_mismatches": [
            {"our": k[0], "meemar": k[1], "count": v}
            for k, v in sorted(root_mismatches.items(), key=lambda kv: -kv[1])[:30]
        ],
        "top_wazn_mismatches": [
            {"our": k[0], "meemar": k[1], "count": v}
            for k, v in sorted(wazn_mismatches.items(), key=lambda kv: -kv[1])[:30]
        ],
        "invariable_confusion": {f"our={k[0]}_meemar={k[1]}": v for k, v in inv_confusion.items()},
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2,
                  default=lambda o: str(o))

    # Markdown
    md = [
        "# Accuracy vs MEEMAR Ground Truth\n",
        f"**Words compared:** {n_compared:,}\n",
        f"## Root accuracy\n- MEEMAR has root: {n_root_meemar_has:,}",
        f"- Our root correct: {n_root_correct:,}",
        f"- **Accuracy: {result['root']['accuracy_pct']}%**\n",
        f"## Wazn accuracy\n- MEEMAR has wazn: {n_wazn_meemar_has:,}",
        f"- Our wazn correct: {n_wazn_correct:,}",
        f"- **Accuracy: {result['wazn']['accuracy_pct']}%**\n",
        f"## مَبني/مُعرَب accuracy\n- Comparable: {n_invariable_meemar_has:,}",
        f"- Correct: {n_invariable_correct:,}",
        f"- **Accuracy: {result['invariable_vs_declinable']['accuracy_pct']}%**\n",
        "## Top root mismatches (our → MEEMAR)\n",
    ]
    for (our_r, gt_r), c in sorted(root_mismatches.items(), key=lambda kv: -kv[1])[:20]:
        md.append(f"- `{our_r}` → `{gt_r}` × {c}")
    md.append("\n## Top wazn mismatches\n")
    for (our_w, gt_w), c in sorted(wazn_mismatches.items(), key=lambda kv: -kv[1])[:20]:
        md.append(f"- `{our_w}` → `{gt_w}` × {c}")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print()
    print(f"Words compared: {n_compared:,}")
    print(f"Root accuracy:        {result['root']['accuracy_pct']}% ({n_root_correct:,}/{n_root_meemar_has:,})")
    print(f"Wazn accuracy:        {result['wazn']['accuracy_pct']}% ({n_wazn_correct:,}/{n_wazn_meemar_has:,})")
    print(f"مَبني/مُعرَب accuracy:  {result['invariable_vs_declinable']['accuracy_pct']}% ({n_invariable_correct:,}/{n_invariable_meemar_has:,})")
    print(f"\nWrote {OUT_PATH}")
    print(f"      {OUT_MD}")


if __name__ == "__main__":
    main()
