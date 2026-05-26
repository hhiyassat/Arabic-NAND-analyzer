"""contracts_loader.py — Loaders for all canonical contract files.

Per 14_Minimal_Complete_Theory.md, every closed list / rule table /
translation map must live in a data file, NOT embedded in code.

Layout under clean_code/data/contracts/:

  <root>/                       — closed-class form lists (HARF_JARR, etc.)
  rules/                        — language-rule tables (tanwin stripping, etc.)
  translations/                 — display translation maps (Arabic labels)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

_CONTRACT_ROOTS = [
    _HERE / "data" / "contracts",
    _HERE.parent / "data" / "contracts",
]


def _find_root() -> Path | None:
    for p in _CONTRACT_ROOTS:
        if p.is_dir():
            return p
    return None


_CACHE: dict[str, set[str]] = {}


def _load_set(filename: str, *, col: str = "form",
              subdir: str = "") -> set[str]:
    """Load a column from a contract CSV. Cached."""
    cache_key = f"{subdir}/{filename}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    root = _find_root()
    out: set[str] = set()
    if root is not None:
        p = (root / subdir / filename) if subdir else (root / filename)
        if p.is_file():
            with p.open(encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    v = (row.get(col) or "").strip()
                    if v:
                        out.add(v)
    _CACHE[cache_key] = out
    return out


def _load_dict(filename: str, *, key_col: str, value_col: str,
               subdir: str = "translations") -> dict[str, str]:
    """Load a translation dict from a CSV."""
    cache_key = f"{subdir}/{filename}/{key_col}>{value_col}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    root = _find_root()
    out: dict[str, str] = {}
    if root is not None:
        p = root / subdir / filename if subdir else root / filename
        if p.is_file():
            with p.open(encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    k = (row.get(key_col) or "").strip()
                    v = (row.get(value_col) or "").strip()
                    if k:
                        out[k] = v
    _CACHE[cache_key] = out  # type: ignore
    return out


def _load_rows(filename: str, *, subdir: str = "rules") -> list[dict]:
    """Load CSV as list of row dicts."""
    cache_key = f"rows/{subdir}/{filename}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]  # type: ignore
    root = _find_root()
    out: list[dict] = []
    if root is not None:
        p = root / subdir / filename if subdir else root / filename
        if p.is_file():
            with p.open(encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    out.append(dict(row))
    _CACHE[cache_key] = out  # type: ignore
    return out


# ============================================================================
# Closed-class form sets — root contracts/
# ============================================================================

def load_harf_jarr() -> set[str]:
    return _load_set("harf_jarr.csv")


def load_harf_nasb() -> set[str]:
    return _load_set("harf_nasb.csv")


def load_harf_jazm() -> set[str]:
    return _load_set("harf_jazm.csv")


def load_harf_inna() -> set[str]:
    return _load_set("harf_inna.csv")


def load_kana_family() -> set[str]:
    return _load_set("kana_family.csv")


def load_ism_ishara() -> set[str]:
    return _load_set("ism_ishara.csv")


def load_verb_base_wazns() -> dict[str, dict]:
    rows = _load_rows("verb_base_wazns.csv", subdir="")
    return {
        r["wazn"]: {
            "aspect": (r.get("aspect") or "").strip(),
            "family": (r.get("family") or "").strip(),
            "note": (r.get("note") or "").strip(),
        }
        for r in rows if r.get("wazn")
    }


def load_closed_class_exceptions() -> dict[str, dict]:
    """Per `closed_class_exceptions.csv`: rows that must NOT be
    diacritic-blind-matched in the closed-class detector.

    Modes:
      - exclude    : drop the stripped form from the closed-class set entirely
                     (e.g., لله is a fused HARF_JARR+JALALAH, not a particle)
      - exact_only : keep ONLY the exact_form, not the stripped form
                     (e.g., رُبَّ is the particle; رَبّ noun must not match)

    Returns: dict mapping stripped_form → {mode, exact_form, actual_split, note}
    """
    rows = _load_rows("closed_class_exceptions.csv", subdir="")
    out: dict[str, dict] = {}
    for r in rows:
        sf = (r.get("stripped_form") or "").strip()
        if not sf:
            continue
        out[sf] = {
            "mode": (r.get("mode") or "").strip(),
            "exact_form": (r.get("exact_form") or "").strip(),
            "actual_split": (r.get("actual_split") or "").strip(),
            "note": (r.get("note") or "").strip(),
        }
    return out


# ============================================================================
# Language rules — contracts/rules/
# ============================================================================

def load_tanwin_stripping_rules() -> list[dict]:
    """Rules for stripping tanwin markers before wazn alignment.

    CSV columns:
      suffix      — the byte pattern at end of word (e.g., "ًا", "اً", "ٌ")
      strip_chars — how many chars to remove from the end
      kind        — "tanwin_fath_alif_first" | "tanwin_fath_tanwin_first"
                    | "tanwin_damm" | "tanwin_kasr" | etc.
      note        — human-readable explanation
    """
    return _load_rows("tanwin_stripping.csv")


# ============================================================================
# Translation tables — contracts/translations/
# ============================================================================

def load_word_class_ar() -> dict[str, str]:
    """English WordClass code → Arabic display name."""
    return _load_dict("word_class.csv", key_col="code", value_col="ar")


def load_proof_kind_ar() -> dict[str, str]:
    """Certificate/Hypothesis/Zero → Arabic."""
    return _load_dict("proof_kind.csv", key_col="code", value_col="ar")


def load_verb_aspect_ar() -> dict[str, str]:
    """PV/IV/CV → Arabic."""
    return _load_dict("verb_aspect.csv", key_col="code", value_col="ar")


def load_harf_kind_ar() -> dict[str, str]:
    """HARF_JARR/HARF_NASB/... → Arabic."""
    return _load_dict("harf_kind.csv", key_col="code", value_col="ar")


def load_source_ar() -> dict[str, str]:
    """Internal source code → Arabic display."""
    return _load_dict("source_codes.csv", key_col="code", value_col="ar")


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    print(f"contracts root: {_find_root()}")
    print()
    print(f"HARF_JARR:        {sorted(load_harf_jarr())[:6]}...")
    print(f"HARF_NASB:        {sorted(load_harf_nasb())}")
    print(f"HARF_JAZM:        {sorted(load_harf_jazm())}")
    print(f"VERB_BASE_WAZNS:  {len(load_verb_base_wazns())} entries")
    print()
    print("--- Translations ---")
    for fn, getter in [
        ("word_class", load_word_class_ar),
        ("proof_kind", load_proof_kind_ar),
        ("verb_aspect", load_verb_aspect_ar),
        ("harf_kind", load_harf_kind_ar),
        ("source_codes", load_source_ar),
    ]:
        d = getter()
        print(f"  {fn}: {len(d)} entries")
    print()
    print("--- Rules ---")
    r = load_tanwin_stripping_rules()
    print(f"  tanwin_stripping: {len(r)} rules")
