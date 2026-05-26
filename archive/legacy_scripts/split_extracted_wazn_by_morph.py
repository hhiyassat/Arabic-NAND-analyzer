#!/usr/bin/env python3
"""Split mishkat-extracted-only wazn patterns into verb_db and noun_extracted_db.

Reads:
  - mishkat_word_root_with_wazn.csv (with morph_type column)
  - unified_wazn_database.csv (to identify which patterns are mishkat-only)

Produces:
  - verb_db.csv          — patterns where verb tokens dominate
  - noun_extracted_db.csv — noun patterns NOT already in alasmaa/extensions
  - mixed_patterns.csv   — patterns ambiguous between noun and verb

Each row aggregated by core_pattern_key with:
  - wazn_plain, voweled_variants
  - dominant_morph (noun/verb/mixed)
  - noun_token_count, noun_row_count
  - verb_token_count, verb_row_count
  - sample_examples (root+word from real Quran usage)
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


# Import the canonical-key function from the merger
sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_wazn_database import (  # noqa: E402
    core_pattern_key, plain_key, strip_diacritics, fold_hamza,
)


def _resolve_paths():
    macos = Path("/Users/husseinhiyassat/fractal")
    sandbox = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos, sandbox):
        mish = root / "hussein/data/extracted/mishkat_word_root_with_wazn.csv"
        if mish.is_file():
            return (
                mish,
                root / "hussein/data/extracted/unified_wazn_database.csv",
                root / "hussein/data/extracted/verb_db.csv",
                root / "hussein/data/extracted/noun_extracted_db.csv",
                root / "hussein/data/extracted/mixed_patterns.csv",
            )
    raise FileNotFoundError("Cannot resolve paths.")


MISHKAT, UNIFIED, OUT_VERB, OUT_NOUN, OUT_MIXED = _resolve_paths()


class PatternAgg:
    __slots__ = (
        "key", "voweled_variants",
        "noun_rows", "noun_tokens",
        "verb_rows", "verb_tokens",
        "noun_examples", "verb_examples",
    )

    def __init__(self, key: str):
        self.key = key
        self.voweled_variants: set[str] = set()
        self.noun_rows = 0
        self.noun_tokens = 0
        self.verb_rows = 0
        self.verb_tokens = 0
        self.noun_examples: list[tuple[str, str]] = []  # (root, word)
        self.verb_examples: list[tuple[str, str]] = []

    def add(self, morph: str, count: int, voweled: str, root: str, word: str):
        if voweled:
            self.voweled_variants.add(voweled)
        if morph == "verb":
            self.verb_rows += 1
            self.verb_tokens += count
            if len(self.verb_examples) < 5:
                self.verb_examples.append((root, word))
        else:
            self.noun_rows += 1
            self.noun_tokens += count
            if len(self.noun_examples) < 5:
                self.noun_examples.append((root, word))

    @property
    def total_tokens(self) -> int:
        return self.noun_tokens + self.verb_tokens

    @property
    def dominant_morph(self) -> str:
        if self.verb_tokens > self.noun_tokens * 2:
            return "verb"
        if self.noun_tokens > self.verb_tokens * 2:
            return "noun"
        if self.verb_tokens == 0:
            return "noun"
        if self.noun_tokens == 0:
            return "verb"
        return "mixed"


def load_curated_keys() -> set[str]:
    """Return the set of core-pattern keys present in the curated sources
    (canonical_table or user_extensions). Used to decide whether a noun
    pattern found in mishkat is genuinely 'new' (not already in our curated DB).
    """
    curated: set[str] = set()
    if not UNIFIED.is_file():
        return curated
    with UNIFIED.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            srcs = row.get("sources", "")
            if "canonical_table" in srcs or "user_extensions" in srcs:
                curated.add(row["wazn_plain"])
    return curated


def main() -> int:
    curated_keys = load_curated_keys()
    print(f"loaded curated keys (alasmaa + extensions): {len(curated_keys)}",
          file=sys.stderr)

    agg: dict[str, PatternAgg] = {}
    with MISHKAT.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            voweled = (row.get("wazn_canonical") or "").strip()
            morph = (row.get("morph_type") or "noun").strip()
            try:
                count = int(row.get("count", 1) or 1)
            except ValueError:
                count = 1
            root = (row.get("root") or "").strip()
            word = (row.get("word") or "").strip()
            if not voweled:
                continue
            key = core_pattern_key(voweled)
            p = agg.setdefault(key, PatternAgg(key))
            p.add(morph, count, voweled, root, word)

    # Classify each pattern
    verb_rows: list[PatternAgg] = []
    new_noun_rows: list[PatternAgg] = []
    mixed_rows: list[PatternAgg] = []

    for p in agg.values():
        dom = p.dominant_morph
        is_curated = p.key in curated_keys
        if dom == "verb":
            verb_rows.append(p)
        elif dom == "noun":
            # Only emit "new noun" if not already in curated DB
            if not is_curated:
                new_noun_rows.append(p)
        else:  # mixed
            mixed_rows.append(p)

    # Sort by total tokens descending
    verb_rows.sort(key=lambda p: -p.total_tokens)
    new_noun_rows.sort(key=lambda p: -p.total_tokens)
    mixed_rows.sort(key=lambda p: -p.total_tokens)

    def _examples_str(exs: list[tuple[str, str]]) -> str:
        return " | ".join(f"{r}+{w}" for r, w in exs[:5])

    # Write verb_db.csv
    with OUT_VERB.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "wazn_plain", "voweled_variants", "rows", "tokens",
            "examples",
        ])
        for p in verb_rows:
            w.writerow([
                p.key,
                " | ".join(sorted(p.voweled_variants)),
                p.verb_rows,
                p.verb_tokens,
                _examples_str(p.verb_examples),
            ])

    # Write noun_extracted_db.csv (new noun patterns not in curated)
    with OUT_NOUN.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "wazn_plain", "voweled_variants", "rows", "tokens",
            "examples",
        ])
        for p in new_noun_rows:
            w.writerow([
                p.key,
                " | ".join(sorted(p.voweled_variants)),
                p.noun_rows,
                p.noun_tokens,
                _examples_str(p.noun_examples),
            ])

    # Write mixed_patterns.csv (ambiguous)
    with OUT_MIXED.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "wazn_plain", "voweled_variants",
            "noun_rows", "noun_tokens",
            "verb_rows", "verb_tokens",
            "noun_examples", "verb_examples",
        ])
        for p in mixed_rows:
            w.writerow([
                p.key,
                " | ".join(sorted(p.voweled_variants)),
                p.noun_rows, p.noun_tokens,
                p.verb_rows, p.verb_tokens,
                _examples_str(p.noun_examples),
                _examples_str(p.verb_examples),
            ])

    # Report
    print("=" * 60)
    print("Split mishkat-extracted by morph_type")
    print("=" * 60)
    print(f"Total unique patterns:          {len(agg)}")
    print(f"  verb-dominant (verb_db):      {len(verb_rows)}")
    print(f"  noun-only NEW (noun_ext_db):  {len(new_noun_rows)}")
    print(f"  mixed (mixed_patterns):       {len(mixed_rows)}")
    print(f"  noun-only in curated already: "
          f"{sum(1 for p in agg.values() if p.dominant_morph=='noun' and p.key in curated_keys)}")
    print()
    total_verb_tokens = sum(p.verb_tokens for p in verb_rows)
    total_noun_tokens = sum(p.noun_tokens for p in new_noun_rows)
    print(f"Verb tokens covered:            {total_verb_tokens}")
    print(f"New-noun tokens covered:        {total_noun_tokens}")
    print()
    print(f"OUTPUTS:")
    print(f"  verb_db:        {OUT_VERB}")
    print(f"  noun_extracted: {OUT_NOUN}")
    print(f"  mixed:          {OUT_MIXED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
