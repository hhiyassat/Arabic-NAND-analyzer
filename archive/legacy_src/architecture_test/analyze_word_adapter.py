"""Bridge to ``alasmaa/analyze_word.py`` — Mushtaqat wazn per token (Step 0)."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from typing import Any

_FRACTAL_ROOT = Path(__file__).resolve().parents[3]
_ANALYZE_WORD_PATH = _FRACTAL_ROOT / "alasmaa" / "analyze_word.py"
_DEFAULT_WEIGHTS = _FRACTAL_ROOT / "alasmaa" / "Mushtaqat_Weights_Final_Corrected_With_Fa3ll.csv"
_DEFAULT_WEIGHTS_XLSX = _FRACTAL_ROOT / "alasmaa" / "Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx"


def load_analyze_word_module():
    name = "analyze_word_architecture_test"
    spec = importlib.util.spec_from_file_location(name, _ANALYZE_WORD_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load analyze_word from {_ANALYZE_WORD_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_mushtaqat_weights(
    aw_mod: Any,
    path: Path | None = None,
    *,
    sheet: str = "الأوزان_المصححة",
) -> list:
    weights_path = path or _DEFAULT_WEIGHTS
    if not weights_path.is_file():
        weights_path = _DEFAULT_WEIGHTS_XLSX
    if not weights_path.is_file():
        raise FileNotFoundError(
            f"Mushtaqat weights not found (tried CSV and xlsx under alasmaa/)"
        )

    suffix = weights_path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        return aw_mod.load_weights_from_excel(str(weights_path), sheet_name=sheet)

    weights = []
    with weights_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = (
                row.get("الوزن مضبوطًا")
                or row.get("الوزن")
                or row.get("weight")
                or ""
            ).strip()
            if not w:
                continue
            wid = row.get("م") or row.get("id") or len(weights)
            bab = (row.get("باب المشتق") or row.get("bab") or "").strip()
            note = (row.get("ملاحظة") or row.get("note") or "").strip()
            weights.append(aw_mod.Wazn(id=wid, bab=bab, weight=w, note=note))
    return weights


def extract_root_from_match(aw_mod: Any, best: dict) -> str | None:
    weight = best.get("weight") or ""
    variant = best.get("variant") or ""
    w = aw_mod.normalize_for_match(weight)
    x = aw_mod.normalize_for_match(variant)
    if len(w) != len(x):
        return None
    mapping: dict[str, str] = {}
    for wc, xc in zip(w, x):
        if wc in aw_mod.PATTERN:
            if wc in mapping and mapping[wc] != xc:
                return None
            mapping[wc] = xc
        elif wc != xc:
            return None
    if not all(k in mapping for k in ("ف", "ع", "ل")):
        return None
    return mapping["ف"] + mapping["ع"] + mapping["ل"]


_DIAS = set("ًٌٍَُِّْٰٓٔ")


def _strip_al_clean(surface: str) -> str:
    """Strip leading 'الْ' / 'ال' and ALSO the orphan sukoon that alasmaa's
    `remove_al` leaves behind (bug in upstream — it removes ا+ل but keeps the
    sukoon that was sitting on the ل).
    """
    s = str(surface or "")
    # Skip optional kasrah/fathah-on-ال, then 'ا', then 'ل', then optional
    # sukoon/shadda/dagger that belonged to the ل.
    i = 0
    # leading harakah on alif (rare)
    if i < len(s) and s[i] in _DIAS:
        return s  # alif must come first; if there's a harakah first, abort
    if i < len(s) and s[i] == "ا":
        i += 1
    else:
        return s
    # skip any harakah on alif
    while i < len(s) and s[i] in _DIAS:
        i += 1
    if i < len(s) and s[i] == "ل":
        i += 1
    else:
        return s
    # skip harakah on ل (typically sukoon, sometimes shadda for assimilated ال)
    while i < len(s) and s[i] in _DIAS:
        i += 1
    return s[i:]


def _strip_sound_plural(surface: str) -> str:
    """Strip a trailing sound-masculine-plural suffix:
        ـِينَ / ـِين / ـُونَ / ـُون  →  remove final ي/و + ن (and following harakah).
    """
    s = str(surface or "")
    # Strip final case marker if any
    if s and s[-1] in _DIAS:
        s = s[:-1]
    if not s.endswith("ن"):
        return surface
    # Strip the ن
    s2 = s[:-1]
    # Skip optional sukoon on ن
    while s2 and s2[-1] in _DIAS:
        s2 = s2[:-1]
    # Now we need ي or و
    if not (s2.endswith("ي") or s2.endswith("و")):
        return surface
    s3 = s2[:-1]
    # Strip the long-vowel-supporting kasrah/dammah (the harakah BEFORE ي/و)
    while s3 and s3[-1] in _DIAS:
        s3 = s3[:-1]
    return s3 or surface


def analyze_token_surface(
    aw_mod: Any,
    weights: list,
    surface: str,
) -> dict[str, Any]:
    if aw_mod.is_operator_surface(surface):
        return {
            "status": "OPERATOR_SKIPPED",
            "best_wazn": None,
            "bab": None,
            "variant_label": None,
            "extracted_root": None,
            "candidate_count": 0,
        }

    # Try the surface as-is, then progressively-cleaned variants. The cleaned
    # variants compensate for two alasmaa quirks:
    #   1. `remove_al` leaves an orphan sukoon on the ل
    #   2. `strip_suffixes` only fires after other operations; doesn't always
    #      reach the ـِين / ـُون / ـات suffixes when ال is also present
    best, candidates = aw_mod.analyze_token(surface, weights)
    fallback_label = None
    if not best:
        # Try with proper ال-stripping (no orphan sukoon)
        cleaned_al = _strip_al_clean(surface)
        if cleaned_al != surface:
            b2, c2 = aw_mod.analyze_token(cleaned_al, weights)
            if b2:
                best, candidates = b2, c2
                fallback_label = "via_al_strip"
    if not best:
        # Try with plural suffix stripped (ـِين / ـُون)
        cleaned_plural = _strip_sound_plural(surface)
        if cleaned_plural != surface:
            b3, c3 = aw_mod.analyze_token(cleaned_plural, weights)
            if b3:
                best, candidates = b3, c3
                fallback_label = "via_sound_plural"
    if not best:
        # Try BOTH: strip ال then plural
        cleaned_both = _strip_sound_plural(_strip_al_clean(surface))
        if cleaned_both not in (surface, _strip_al_clean(surface), _strip_sound_plural(surface)):
            b4, c4 = aw_mod.analyze_token(cleaned_both, weights)
            if b4:
                best, candidates = b4, c4
                fallback_label = "via_al_and_plural"

    if not best:
        return {
            "status": "NO_WAZN",
            "best_wazn": None,
            "bab": None,
            "variant_label": None,
            "extracted_root": None,
            "candidate_count": 0,
        }

    root = extract_root_from_match(aw_mod, best)
    variant_label = best.get("variant_label") or best.get("variant")
    if fallback_label:
        variant_label = f"{variant_label or 'unknown'}+{fallback_label}"
    return {
        "status": "MATCHED" if root else "NO_ROOT_FROM_WAZN",
        "best_wazn": best.get("weight"),
        "bab": best.get("bab"),
        "variant_label": variant_label,
        "extracted_root": root,
        "candidate_count": len(candidates),
    }


def attach_analyze_word(
    tokens: list[dict[str, Any]],
    aw_mod: Any,
    weights: list,
) -> list[dict[str, Any]]:
    out = []
    for tok in tokens:
        analysis = analyze_token_surface(aw_mod, weights, tok["surface"])
        out.append({**tok, "analyze_word": analysis})
    return out


def run_analyze_word_step(
    tokens: list[dict[str, Any]],
    *,
    weights_path: Path | None = None,
    sheet: str = "الأوزان_المصححة",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Analyze every token; return enriched tokens + summary block."""
    aw_mod = load_analyze_word_module()
    weights = load_mushtaqat_weights(aw_mod, weights_path, sheet=sheet)
    enriched = attach_analyze_word(tokens, aw_mod, weights)

    counts: dict[str, int] = {}
    per_token = []
    for t in enriched:
        st = t["analyze_word"]["status"]
        counts[st] = counts.get(st, 0) + 1
        row = {
            "index": t["index"],
            "surface": t["surface"],
            **t["analyze_word"],
        }
        per_token.append(row)

    summary = {
        "source": str(_ANALYZE_WORD_PATH),
        "weights_path": str(weights_path or _DEFAULT_WEIGHTS),
        "weights_count": len(weights),
        "status_counts": counts,
        "per_token": per_token,
    }
    return enriched, summary
