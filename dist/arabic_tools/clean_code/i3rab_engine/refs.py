"""refs.py — Load reference tables from new_arabic_analyzer/data/quran/i3rab_ref/.

These are READ-ONLY canonical sources. No data hardcoded.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Optional

# Sibling import
_HERE = Path(__file__).resolve().parent
_CLEAN_CODE = _HERE.parent
sys.path.insert(0, str(_CLEAN_CODE))

from wazn_data import DIACRITICS  # type: ignore

DIAC = set(DIACRITICS)


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in DIAC)


# Candidate locations (bundled + dev paths)
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # …/<package>/
_I3RAB_ROOTS = [
    # 1) Bundled — data/ and data/i3rab_ref/ at package root
    _PACKAGE_ROOT / "data",
    # 2) Dev locations
    Path("/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran"),
    Path("/sessions/nice-epic-cannon/mnt/new_arabic_analyzer/data/quran"),
]


def _find_root() -> Optional[Path]:
    for p in _I3RAB_ROOTS:
        if p.is_dir():
            return p
    return None


# Lazy singletons
_OPERATORS: Optional[dict[str, dict]] = None
_LABELS_BY_TOKEN: Optional[dict[str, list[str]]] = None
_CASES: Optional[dict[int, str]] = None
_MARKS: Optional[dict[int, dict]] = None
_ROLES: Optional[dict[int, dict]] = None
_QURAN_I3RAB: Optional[dict[tuple[int, int, str], str]] = None


def load_operators() -> dict[str, dict]:
    """Map: vocalized operator token → {key, i3rab_text, occurrences}.

    Also adds a stripped-form index so callers with diacritic-light input
    still hit. Manual overrides are merged in.
    """
    global _OPERATORS
    if _OPERATORS is not None:
        return _OPERATORS
    root = _find_root()
    if root is None:
        _OPERATORS = {}
        return _OPERATORS
    out: dict[str, dict] = {}
    main = root / "i3rab_ref" / "i3rab_operators.csv"
    if main.is_file():
        with main.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                op = (row.get("operator") or "").strip()
                key = (row.get("operator_key") or "").strip()
                txt = (row.get("operator_i3rab") or "").strip()
                occ = (row.get("occurrences_in_quran") or "0").strip()
                if op:
                    out[op] = {"key": key, "i3rab": txt, "occ": occ}
                    out[_strip_diac(op)] = {
                        "key": key, "i3rab": txt, "occ": occ
                    }
    manual = root / "i3rab_ref" / "i3rab_operators_manual.csv"
    if manual.is_file():
        with manual.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (row.get("operator_key") or "").strip()
                txt = (row.get("operator_i3rab") or "").strip()
                if key and key not in out:
                    out[key] = {"key": key, "i3rab": txt, "occ": "manual"}
    _OPERATORS = out
    return _OPERATORS


def load_labels_jsonl() -> dict[str, list[str]]:
    """Map: vocalized Quran word → list of label codes (HARF_JARR, ...).

    Used to disambiguate HARF vs ISM_MABNI for closed-class words.
    Multiple labels per word — caller picks the most specific.
    """
    global _LABELS_BY_TOKEN
    if _LABELS_BY_TOKEN is not None:
        return _LABELS_BY_TOKEN
    root = _find_root()
    if root is None:
        _LABELS_BY_TOKEN = {}
        return _LABELS_BY_TOKEN
    path = root / "quran_i3rab_labels.jsonl"
    out: dict[str, list[str]] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    w = d.get("word", "")
                    labels = d.get("labels", [])
                    if w and labels:
                        # Last write wins for non-unique tokens — that's
                        # OK because labels are aggregated from i3rab text
                        # and are stable per surface form.
                        out[w] = labels
                        out.setdefault(_strip_diac(w), labels)
                except Exception:
                    continue
    _LABELS_BY_TOKEN = out
    return _LABELS_BY_TOKEN


def load_cases() -> dict[int, str]:
    """Map: case_id → Arabic case name."""
    global _CASES
    if _CASES is not None:
        return _CASES
    root = _find_root()
    out: dict[int, str] = {}
    if root is not None:
        path = root / "i3rab_ref" / "i3rab_cases.csv"
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    try:
                        cid = int((row.get("case_id") or "0").strip())
                        name = (row.get("case_name_ar") or "").strip()
                        if cid:
                            out[cid] = name
                    except ValueError:
                        continue
    _CASES = out
    return _CASES


def load_marks() -> dict[int, dict]:
    """Map: mark_id → {case_id, name, text}."""
    global _MARKS
    if _MARKS is not None:
        return _MARKS
    root = _find_root()
    out: dict[int, dict] = {}
    if root is not None:
        path = root / "i3rab_ref" / "i3rab_marks.csv"
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    try:
                        mid = int((row.get("mark_id") or "0").strip())
                        cid = int((row.get("case_id") or "0").strip())
                        name = (row.get("mark_name_ar") or "").strip()
                        text = (row.get("mark_text_ar") or "").strip()
                        if mid:
                            out[mid] = {
                                "case_id": cid, "name": name, "text": text
                            }
                    except ValueError:
                        continue
    _MARKS = out
    return _MARKS


def load_roles() -> dict[int, dict]:
    """Map: role_id → {case_id, name, phrase}."""
    global _ROLES
    if _ROLES is not None:
        return _ROLES
    root = _find_root()
    out: dict[int, dict] = {}
    if root is not None:
        path = root / "i3rab_ref" / "i3rab_roles.csv"
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    try:
                        rid = int((row.get("role_id") or "0").strip())
                        cid = int((row.get("case_id") or "0").strip())
                        name = (row.get("role_name_ar") or "").strip()
                        phrase = (row.get("role_phrase_ar") or "").strip()
                        if rid:
                            out[rid] = {
                                "case_id": cid, "name": name, "phrase": phrase
                            }
                    except ValueError:
                        continue
    _ROLES = out
    return _ROLES


def load_quran_i3rab(max_rows: int = 0) -> dict[tuple[int, int, str], str]:
    """Map: (surah, ayah, word) → full i3rab text. Used for evaluation."""
    global _QURAN_I3RAB
    if _QURAN_I3RAB is not None:
        return _QURAN_I3RAB
    root = _find_root()
    out: dict[tuple[int, int, str], str] = {}
    if root is not None:
        path = root / "quran_i3rab.csv"
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                r = csv.DictReader(f)
                for i, row in enumerate(r):
                    if max_rows and i >= max_rows:
                        break
                    try:
                        s = int(row.get("surah", ""))
                        a = int(row.get("ayah", ""))
                        w = (row.get("word") or "").strip()
                        ir = (row.get("i3rab") or "").strip()
                        if w:
                            out[(s, a, w)] = ir
                    except (ValueError, TypeError):
                        continue
    _QURAN_I3RAB = out
    return _QURAN_I3RAB


# Closed-class form sets — loaded from canonical contract files in
# clean_code/data/contracts/. Lists are NOT embedded in code.
# Per 14_Minimal_Complete_Theory.md, hidden contracts are forbidden.

try:
    from contracts_loader import (
        load_ism_ishara,
        load_harf_nasb,
        load_harf_jazm,
        load_harf_jarr,
    )
    # كل القوائم من ملفات contracts/ — لا inline overrides
    # (المبدأ: hash must not be source-of-claim → القوائم في ملفّ)
    _ISM_ISHARA_FALLBACK = load_ism_ishara()
    _HARF_NASB_FORMS = load_harf_nasb()
    _HARF_JAZM_FORMS = load_harf_jazm()
    _HARF_JARR_FORMS = load_harf_jarr()
except ImportError:
    _ISM_ISHARA_FALLBACK = set()
    _HARF_NASB_FORMS = set()
    _HARF_JAZM_FORMS = set()
    _HARF_JARR_FORMS = set()


def closed_class_kind(word: str) -> str:
    """Lookup the most-specific kind for a closed-class word.

    DISAMBIGUATION RULE: if a word has BOTH `FIIL` and `HARF` labels,
    the FIIL takes precedence (the HARF usually refers to an attached
    pronoun, not the lexical class of the main word — e.g. اهْدِنَا
    has FIIL + HARF because نا is a pronoun particle).

    Priority (high → low specificity):
      HARF_JARR, HARF_ATF, HARF_NIDA, HARF_NAFI, HARF_NASB, HARF_JAZM,
      HARF_TAWKEED, HARF_ISTIFHAM, HARF_ISTINAAD,
      ISM_MAWSOOL, ISM_ISHARA, ISM_SHART, ISM_ISTIFHAM, DAMEER,
      ZARF_ZAMAN_MABNI, ZARF_MAKAN_MABNI,
      MAWSOOL,
      HARF (generic).

    Fallbacks (when labels are missing/coarse):
      - Demonstrative surface → ISM_ISHARA
      - MABNI without any HARF*/specific tag → ISM_MABNI_GENERIC
    """
    labels_map = load_labels_jsonl()
    labels = labels_map.get(word) or labels_map.get(_strip_diac(word)) or []

    plain_lookup = _strip_diac(word)

    # === EARLIEST PRIORITY: explicit canonical contracts ===
    # These take precedence over labels.jsonl heuristic, which sometimes
    # mis-attributes FIIL to particles like في/على when the i3rab text
    # describes attached verbs in the same clause.
    if plain_lookup in _HARF_JARR_FORMS:
        return "HARF_JARR"
    if plain_lookup in _HARF_JAZM_FORMS:
        return "HARF_JAZM"
    if plain_lookup in _HARF_NASB_FORMS and plain_lookup not in {"ل", "ف", "و"}:
        return "HARF_NASB"

    # If word has FIIL label, it's verb-with-attached-pronoun, NOT closed.
    if "FIIL" in labels:
        return "OVERRIDE_AS_VERB"

    priority = [
        "HARF_JARR", "HARF_ATF", "HARF_NIDA", "HARF_NAFI", "HARF_NASB",
        "HARF_JAZM", "HARF_TAWKEED", "HARF_ISTIFHAM", "HARF_ISTINAAD",
        "ISM_MAWSOOL", "ISM_ISHARA", "ISM_SHART", "ISM_ISTIFHAM",
        "DAMEER", "ZARF_ZAMAN_MABNI", "ZARF_MAKAN_MABNI", "MAWSOOL",
        "HARF",
    ]
    for p in priority:
        if p in labels:
            return p

    # Fallback: surface-based demonstrative detection
    plain = _strip_diac(word)
    if plain in _ISM_ISHARA_FALLBACK:
        return "ISM_ISHARA"

    # Fallback: HARF_JARR قطعي من contracts
    if plain in _HARF_JARR_FORMS:
        return "HARF_JARR"

    # Fallback: HARF_NASB / HARF_JAZM particle override
    if plain in _HARF_JAZM_FORMS:
        return "HARF_JAZM"
    if plain in _HARF_NASB_FORMS and plain not in {"ل", "ف", "و"}:
        return "HARF_NASB"

    # Fallback: MABNI without specific kind → generic ism mabni
    if "MABNI" in labels and not any(l.startswith("HARF") for l in labels):
        return "ISM_MABNI_GENERIC"

    return ""
