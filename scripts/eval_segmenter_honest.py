"""eval_segmenter_honest.py — Honest evaluation of ClauseSegmenter.

CONSTITUTIONAL CORRECTION (2026-05-22):

The prior eval (eval_clause_segmenter_on_pause_marks.py) was self-fulfilling
because the segmenter consumed pause marks as input rules. That produced
"Recall 99.9% / Precision 100%" — meaningless.

This eval is honest:
  1. Pause marks are STRIPPED from the verse before the segmenter sees it.
  2. The segmenter operates on rule-based signals only (punctuation,
     connectives, conditionals).
  3. Pause marks define ground-truth boundaries by their position in the
     ORIGINAL verse, mapped to word-index space (between word i and i+1).
  4. We compare the segmenter's proposed boundaries (word-index space) to
     ground truth and report Recall, Precision, F1.

Pause-mark roles (per Quranic mushaf convention):
  ۖ ۚ ۛ → "split" pause marks  → YES boundaries (ground truth POSITIVE)
  ۘ     → mandatory pause       → YES boundaries (ground truth POSITIVE)
  ۗ ۙ   → "do not split"        → NEGATIVE boundaries — segmenter should NOT
                                   propose a clause break at that position.
  ۜ     → permissible pause     → counted as POSITIVE (loose).

Output: data/eval/m1a_pause_eval_honest.json
"""

from __future__ import annotations

import json
import sys
import re
from pathlib import Path

# Add clean_code to path
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "clean_code"))

from clause_segmenter import ClauseSegmenter, _strip_pause_marks  # noqa: E402


QURAN_PATH = _REPO / "data" / "quran-uthmani-with-pause-mark.txt"
OUT_PATH = _REPO / "data" / "eval" / "m1a_pause_eval_honest.json"

# Positive pause marks (signal a clause boundary in mushaf convention)
POSITIVE_PAUSE = {"ۘ", "ۖ", "ۚ", "ۛ", "ۜ"}
# Negative pause marks (signal NO boundary)
NEGATIVE_PAUSE = {"ۗ", "ۙ"}
ALL_PAUSE = POSITIVE_PAUSE | NEGATIVE_PAUSE


# ============================================================================
# Word-level boundary extraction
# ============================================================================

def _tokenize_words_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Return list of (word, start_char, end_char) — whitespace tokenization.
    Pause marks (if attached to a word) stay attached to that word."""
    out = []
    i = 0
    while i < len(text):
        # skip whitespace
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        start = i
        while i < len(text) and not text[i].isspace():
            i += 1
        out.append((text[start:i], start, i))
    return out


def _extract_ground_truth_boundaries(verse_original: str) -> tuple[set[int], set[int], list[str]]:
    """From the original verse (with pause marks), determine ground-truth
    boundaries in WORD-INDEX space (on the cleaned tokenization).

    A boundary "i" means: there is a clause break BEFORE word index i
    in the cleaned (pause-stripped) word list.

    Returns:
      (positive_boundaries, negative_boundaries, clean_words)
    """
    # First, build the cleaned word list (pause marks removed).
    cleaned = _strip_pause_marks(verse_original)
    clean_tokens = _tokenize_words_with_offsets(cleaned)
    clean_words = [w for (w, _, _) in clean_tokens]
    n_words = len(clean_words)

    # Walk the original text and pair each pause-mark occurrence with the
    # WORD INDEX in the cleaned list that begins AFTER the pause mark.
    positive: set[int] = set()
    negative: set[int] = set()

    # To map: count how many cleaned-words have been "completed" up to a
    # given original position. We do this by walking both in parallel.
    orig = verse_original
    i_orig = 0
    i_clean = 0
    completed_clean_words = 0

    # We need a mapping: at every original position, what is the index of
    # the next NOT-YET-STARTED cleaned word?
    # Simpler: walk original; whenever we are at the start of a non-pause,
    # non-whitespace character that begins a new word in cleaned text,
    # increment a counter. When we encounter a pause mark, record:
    # boundary is at "next word in cleaned text" = current_word_index + 1
    # if we are currently inside word current_word_index, or = current_word_index
    # if we are between words.

    # Easier algorithm: scan original. Track "current cleaned word index"
    # (the index of the next word we will start once we leave whitespace
    # and pause marks). Each time we hit a pause mark:
    #   boundary_index = next-word-index-after-this-pause
    # Implementation: maintain `next_word_idx` = index in clean_words of
    # the NEXT clean word that will begin.
    next_word_idx = 0
    in_word = False

    j = 0
    while j < len(orig):
        ch = orig[j]
        if ch in ALL_PAUSE:
            # We're at a pause mark. Skip it. The boundary it implies is at
            # next_word_idx (= the next clean word that will start AFTER
            # this pause). If we're currently inside a word, the boundary is
            # next_word_idx (after this word ends). If we're between words,
            # boundary is also next_word_idx.
            if in_word:
                # Pause inside a word — close the word first.
                next_word_idx += 1
                in_word = False
            boundary = next_word_idx
            if ch in POSITIVE_PAUSE:
                if boundary > 0 and boundary < n_words:
                    positive.add(boundary)
            elif ch in NEGATIVE_PAUSE:
                if boundary > 0 and boundary < n_words:
                    negative.add(boundary)
            j += 1
            continue
        if ch.isspace():
            if in_word:
                next_word_idx += 1
                in_word = False
            j += 1
            continue
        # Regular character → part of a word
        in_word = True
        j += 1

    return positive, negative, clean_words


# ============================================================================
# Segmenter boundaries → word-index space
# ============================================================================

def _segmenter_boundaries(segmenter: ClauseSegmenter, verse_original: str) -> set[int]:
    """Run segmenter on cleaned text; return set of word-indices where a
    new clause begins (excluding 0)."""
    cleaned = _strip_pause_marks(verse_original)
    clauses = segmenter.segment(cleaned)
    if not clauses:
        return set()

    # Build char_offset → word_index map for cleaned text
    tokens = _tokenize_words_with_offsets(cleaned)
    # For each clause, find which word index its text starts at
    boundaries: set[int] = set()
    for c in clauses:
        # Find first word whose start_char >= clause.start_idx (after lstrip)
        # Use the clause's recorded start_idx
        clause_start = c.start_idx
        # Skip leading whitespace within the clause
        text_at = cleaned[clause_start:c.end_idx]
        offset = len(text_at) - len(text_at.lstrip())
        actual_start = clause_start + offset
        for w_idx, (_, ws, _) in enumerate(tokens):
            if ws >= actual_start:
                if w_idx > 0:
                    boundaries.add(w_idx)
                break
    return boundaries


# ============================================================================
# Main eval loop
# ============================================================================

def main():
    if not QURAN_PATH.exists():
        print(f"ERROR: {QURAN_PATH} not found", file=sys.stderr)
        sys.exit(1)

    seg = ClauseSegmenter()

    tp = 0  # positive ground truth boundary AND segmenter proposed
    fn = 0  # positive ground truth boundary BUT segmenter missed
    fp = 0  # segmenter proposed boundary BUT no positive ground truth
    # (note: we don't penalize for proposing boundaries where there's no
    #  pause mark at all, since pause marks don't mark EVERY boundary —
    #  only the ones the mushaf chose to annotate. We only penalize when
    #  the segmenter proposes a boundary at a NEGATIVE pause position.)
    fp_strict = 0   # proposed boundary at any position not in positive set
    fp_anti = 0     # proposed boundary at a NEGATIVE pause position
    n_verses = 0
    n_verses_with_any_positive = 0

    per_verse_log = []

    with QURAN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            surah, ayah, verse = parts
            n_verses += 1

            positive, negative, clean_words = _extract_ground_truth_boundaries(verse)
            proposed = _segmenter_boundaries(seg, verse)

            if positive:
                n_verses_with_any_positive += 1

            verse_tp = len(proposed & positive)
            verse_fn = len(positive - proposed)
            verse_fp_anti = len(proposed & negative)
            verse_fp_strict = len(proposed - positive)

            tp += verse_tp
            fn += verse_fn
            fp_anti += verse_fp_anti
            fp_strict += verse_fp_strict

            if len(per_verse_log) < 20:
                per_verse_log.append({
                    "ref": f"{surah}:{ayah}",
                    "n_words": len(clean_words),
                    "positive_gt": sorted(positive),
                    "negative_gt": sorted(negative),
                    "proposed": sorted(proposed),
                    "tp": verse_tp,
                    "fn": verse_fn,
                    "fp_anti": verse_fp_anti,
                })

    # Metric A: Recall on positive pause marks (does segmenter catch them?)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    # Metric B: Precision under STRICT interpretation (every proposed
    # boundary not at a positive pause mark is a false positive). This is
    # harsh because pause marks don't cover every legitimate boundary.
    precision_strict = tp / (tp + fp_strict) if (tp + fp_strict) > 0 else 0.0
    # Metric C: Precision under MUSHAF interpretation — only count
    # boundaries at NEGATIVE pause marks as false positives.
    precision_against_anti = tp / (tp + fp_anti) if (tp + fp_anti) > 0 else 0.0
    # F1 against strict precision (the honest one)
    f1_strict = (
        2 * recall * precision_strict / (recall + precision_strict)
        if (recall + precision_strict) > 0 else 0.0
    )
    f1_anti = (
        2 * recall * precision_against_anti / (recall + precision_against_anti)
        if (recall + precision_against_anti) > 0 else 0.0
    )

    result = {
        "contract": "M1.A_HonestEval:v1",
        "segmenter_contract": seg.source(),
        "n_verses": n_verses,
        "n_verses_with_positive_pause": n_verses_with_any_positive,
        "ground_truth_source": "quran-uthmani-with-pause-mark.txt (pause marks)",
        "ground_truth_role": (
            "POSITIVE pause marks (ۘۖۚۛۜ) mark TRUE boundaries; "
            "NEGATIVE pause marks (ۗۙ) mark FORBIDDEN boundaries. "
            "Pause marks are STRIPPED from segmenter input."
        ),
        "counts": {
            "tp": tp,
            "fn": fn,
            "fp_strict": fp_strict,
            "fp_against_anti_marks": fp_anti,
        },
        "metrics": {
            "recall_on_positive_pause": round(recall, 4),
            "precision_strict": round(precision_strict, 4),
            "precision_against_anti_only": round(precision_against_anti, 4),
            "f1_strict": round(f1_strict, 4),
            "f1_against_anti_only": round(f1_anti, 4),
        },
        "metric_definitions": {
            "recall_on_positive_pause": (
                "Of all positive pause marks (boundaries the mushaf "
                "explicitly annotates), how many did the segmenter "
                "propose? Higher = better."
            ),
            "precision_strict": (
                "Of every boundary the segmenter proposed, how many "
                "coincide with a positive pause mark? Note: pause marks "
                "don't mark EVERY clause boundary, so this is harsh."
            ),
            "precision_against_anti_only": (
                "Of every boundary the segmenter proposed, how many "
                "are NOT at a 'do-not-split' pause mark? This is the "
                "fairer reading — penalizes only constitutional errors."
            ),
        },
        "sample_first_20_verses": per_verse_log,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT_PATH}")
    print()
    print(f"  Verses analyzed:                  {n_verses}")
    print(f"  Verses with positive pause mark:  {n_verses_with_any_positive}")
    print()
    print(f"  TP (positive pause caught):       {tp}")
    print(f"  FN (positive pause missed):       {fn}")
    print(f"  FP_strict (any extra boundary):   {fp_strict}")
    print(f"  FP_anti (at NO-SPLIT pause mark): {fp_anti}")
    print()
    print(f"  Recall (positive pause):          {recall:.2%}")
    print(f"  Precision (strict):               {precision_strict:.2%}")
    print(f"  Precision (against anti only):    {precision_against_anti:.2%}")
    print(f"  F1 (strict):                      {f1_strict:.2%}")
    print(f"  F1 (against anti only):           {f1_anti:.2%}")


if __name__ == "__main__":
    main()
