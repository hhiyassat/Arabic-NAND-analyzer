#!/usr/bin/env python3
"""Merge three wazn sources into a unified database.

Sources:
  1. alasmaa/Mushtaqat_Weights_Final_Corrected_With_Fa3ll.csv (80 curated)
  2. hussein/data/extracted/wazn_db_extensions.csv (~33 broken plurals + rare)
  3. hussein/data/extracted/mishkat_word_root_with_wazn.csv (10,219 derived
     wazn rows with their canonical forms, sources, and frequencies)

The output is a single CSV with one row per UNIQUE plain (hamza-folded) wazn
pattern, aggregating:
  - All voweled variants found
  - Source(s) that contain it
  - Total token frequency from mishkat
  - Example root + word from mishkat
  - Morph type (noun/verb if known)
  - Bab (mushtaq category if known from alasmaa)
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional


DIACRITICS = set("ًٌٍَُِّْٰٓٔ")
TATWEEL = "ـ"


def strip_diacritics(s: str) -> str:
    return "".join(c for c in str(s or "") if c not in DIACRITICS and c != TATWEEL)


def fold_hamza(s: str) -> str:
    return (
        s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        .replace("ؤ", "ء").replace("ئ", "ء")
    )


# Clitic prefixes — note: ف is excluded because it's a canonical pattern
# letter (root[0]). Stripping ف from فعل would yield "عل" which is invalid.
# This means "ففعل" (with ف clitic) won't collapse to فعل, but that's
# acceptable — keeps the canonical فعل entry intact.
_CLITIC_PREFIXES = set("وبكل")
# Pronoun suffixes (plain) ordered longest-first for greedy match
_PRONOUN_SUFFIXES = ("هما", "كما", "هنّ", "هم", "هن", "كم", "كن", "نا",
                     "ها", "ه", "ك", "ي")
# Number / tanwin suffixes. NOTE: ان is INTENTIONALLY EXCLUDED from this list
# even though it's the dual suffix. Reason: many distinct singular patterns
# end in ـان (فَعْلَان, فَعَلَان, فِعْلَان — like رَحْمَن, غَلَيَان). Stripping ـان would
# erase these patterns and merge them with فَعْل/فَعَل, losing critical
# distinctions for words like الرَّحْمَن.
_NUMBER_SUFFIXES = ("ين", "ون", "ات", "ا")


def _strip_prefixes_plain(p: str) -> str:
    """Strip clitic letter + ال (or any combination) from start of plain wazn."""
    if not p:
        return p
    n = len(p)
    i = 0
    # Optional single clitic
    if i < n and p[i] in _CLITIC_PREFIXES:
        i += 1
    # Then optional ال
    if i + 1 < n and p[i] == "ا" and p[i + 1] == "ل":
        i += 2
    # OR a single ل (li-al with elided alif, e.g. لل)
    elif i < n and p[i] == "ل" and (i == 0 or i == 1):
        # only strip if next is consonant (start of pattern letter)
        if i + 1 < n:
            i += 1
    return p[i:] if i > 0 else p


def _strip_suffixes_plain(p: str) -> str:
    """Strip a pronoun suffix THEN a number/tanwin suffix from end of plain wazn."""
    if not p:
        return p
    for suf in _PRONOUN_SUFFIXES:
        if p.endswith(suf) and len(p) > len(suf) + 2:
            p = p[: -len(suf)]
            break
    for suf in _NUMBER_SUFFIXES:
        if p.endswith(suf) and len(p) > len(suf) + 2:
            p = p[: -len(suf)]
            break
    return p


def plain_key(s: str) -> str:
    """Plain + hamza-folded canonical key used as the dictionary anchor."""
    return fold_hamza(strip_diacritics(s))


def core_pattern_key(s: str) -> str:
    """Aggressive canonical: strip clitic prefixes, ال, pronoun and number
    suffixes. Used as the UNIFIED-DB grouping key so that الفعل + فعل + وفعل +
    بفعل + الفعلون all collapse to a single entry 'فعل'."""
    p = plain_key(s)
    p = _strip_prefixes_plain(p)
    p = _strip_suffixes_plain(p)
    return p


def _resolve_paths():
    """The canonical wazn source is the LOCAL xlsx file under hussein/data/.
    The previous alasmaa/Mushtaqat_*.csv was replaced per user request — see
    'Mushtaqat_Full_Weights_Table.xlsx' which contains the same 79-row table
    (without the disabled 'فَعّ' that alasmaa had as #80).
    """
    macos = Path("/Users/husseinhiyassat/fractal")
    sandbox = Path("/sessions/nice-epic-cannon/mnt")
    for root in (macos, sandbox):
        local_xlsx = root / "hussein/data/Mushtaqat_Full_Weights_Table.xlsx"
        if local_xlsx.is_file():
            return (
                local_xlsx,
                root / "hussein/data/extracted/wazn_db_extensions.csv",
                root / "hussein/data/extracted/mishkat_word_root_with_wazn.csv",
                root / "hussein/data/extracted/unified_wazn_database.csv",
            )
    raise FileNotFoundError("Cannot find hussein/data/Mushtaqat_Full_Weights_Table.xlsx")


CANONICAL_WAZNS, EXTENSIONS, MISHKAT, OUT = _resolve_paths()


# Per-pattern accumulator
class Entry:
    __slots__ = (
        "plain", "voweled_variants", "sources", "babs", "morph_types",
        "token_count", "row_count", "examples",
    )

    def __init__(self, plain: str):
        self.plain = plain
        self.voweled_variants: set[str] = set()
        self.sources: set[str] = set()
        self.babs: set[str] = set()
        self.morph_types: set[str] = set()
        self.token_count = 0
        self.row_count = 0
        self.examples: list[tuple[str, str]] = []  # (root, word)

    def add_voweled(self, v: str):
        if v:
            self.voweled_variants.add(v)


def _iter_canonical_rows(path: Path):
    """Yield rows from the canonical wazn source (xlsx or csv).

    The xlsx file (`Mushtaqat_Full_Weights_Table.xlsx`) has 3 sheets; we want
    the `الأوزان_المصححة` sheet. CSV fallback supported for compatibility.
    """
    if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = "الأوزان_المصححة" if "الأوزان_المصححة" in wb.sheetnames else wb.sheetnames[-1]
        ws = wb[sheet]
        header = None
        for r in ws.iter_rows(values_only=True):
            if header is None:
                header = list(r)
                continue
            yield {h: (v if v is not None else "") for h, v in zip(header, r)}
    else:
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                yield row


def load_canonical_wazns(path: Path, store: dict[str, Entry]) -> int:
    """Load the canonical wazn table (now hussein/data/Mushtaqat_Full_Weights_Table.xlsx).
    Each pattern is tagged source='canonical_table' (was alasmaa_80 previously).
    """
    n = 0
    if not path.is_file():
        return 0
    for row in _iter_canonical_rows(path):
        voweled = str(row.get("الوزن مضبوطًا") or "").strip()
        bab = str(row.get("باب المشتق") or "").strip()
        example = str(row.get("مثال مضبوط") or "").strip()
        if not voweled:
            continue
        key = core_pattern_key(voweled)
        e = store.setdefault(key, Entry(key))
        e.add_voweled(voweled)
        e.sources.add("canonical_table")
        if bab:
            e.babs.add(bab)
        if example:
            e.examples.append(("(curated)", example))
        f_form = str(row.get("الصورة بالتاء / المؤنث") or "").strip()
        f_ex = str(row.get("مثال مؤنث مضبوط") or "").strip()
        if f_form:
            f_key = core_pattern_key(f_form)
            fe = store.setdefault(f_key, Entry(f_key))
            fe.add_voweled(f_form)
            fe.sources.add("canonical_table")
            if bab:
                fe.babs.add(bab + " (feminine)")
            if f_ex:
                fe.examples.append(("(curated)", f_ex))
        n += 1
    return n


def load_extensions(path: Path, store: dict[str, Entry]) -> int:
    n = 0
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 2 or parts[1].strip() == "wazn":
                continue
            category = parts[0].strip()
            voweled = parts[1].strip()
            example = parts[2].strip() if len(parts) > 2 else ""
            if not voweled:
                continue
            key = core_pattern_key(voweled)
            e = store.setdefault(key, Entry(key))
            e.add_voweled(voweled)
            e.sources.add("user_extensions")
            if category:
                e.babs.add(category)
            if example:
                e.examples.append(("(curated)", example))
            n += 1
    return n


def load_mishkat(path: Path, store: dict[str, Entry]) -> int:
    n = 0
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            canon = (row.get("wazn_canonical") or "").strip()
            if not canon:
                continue
            try:
                count = int(row.get("count", 1) or 1)
            except ValueError:
                count = 1
            morph = (row.get("morph_type") or "").strip()
            root = (row.get("root") or "").strip()
            word = (row.get("word") or "").strip()
            key = core_pattern_key(canon)
            e = store.setdefault(key, Entry(key))
            e.add_voweled(canon)
            e.sources.add("mishkat_extracted")
            if morph:
                e.morph_types.add(morph)
            e.token_count += count
            e.row_count += 1
            if len(e.examples) < 5:
                e.examples.append((root, word))
            n += 1
    return n


def main() -> int:
    store: dict[str, Entry] = {}
    n_canonical = load_canonical_wazns(CANONICAL_WAZNS, store)
    n_ext = load_extensions(EXTENSIONS, store)
    n_mishkat = load_mishkat(MISHKAT, store)
    print(f"loaded: canonical_table={n_canonical}  extensions={n_ext}  "
          f"mishkat={n_mishkat}", file=sys.stderr)
    print(f"  canonical source: {CANONICAL_WAZNS}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Sort: by token_count desc (most-used first), then alphabetic plain
    rows = sorted(
        store.values(),
        key=lambda e: (-e.token_count, e.plain),
    )

    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "wazn_plain", "voweled_variants", "sources",
            "babs", "morph_types", "token_count", "row_count",
            "examples",
        ])
        for e in rows:
            writer.writerow([
                e.plain,
                " | ".join(sorted(e.voweled_variants)),
                " | ".join(sorted(e.sources)),
                " | ".join(sorted(e.babs)),
                " | ".join(sorted(e.morph_types)),
                e.token_count,
                e.row_count,
                " | ".join(f"{r}+{w}" for r, w in e.examples[:5]),
            ])

    # Report
    total = len(store)
    only_canonical = sum(1 for e in store.values() if e.sources == {"canonical_table"})
    only_ext = sum(1 for e in store.values() if e.sources == {"user_extensions"})
    only_mishkat = sum(1 for e in store.values() if e.sources == {"mishkat_extracted"})
    in_both_curated_and_mishkat = sum(
        1 for e in store.values()
        if "mishkat_extracted" in e.sources and len(e.sources) > 1
    )
    print("=" * 60)
    print("Unified wazn database")
    print("=" * 60)
    print(f"Total unique plain patterns: {total}")
    print(f"  in canonical_table only:             {only_canonical}")
    print(f"  in user_extensions only:             {only_ext}")
    print(f"  in mishkat_extracted only:           {only_mishkat}")
    print(f"  in mishkat AND curated (overlap):    {in_both_curated_and_mishkat}")
    print(f"Output: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
