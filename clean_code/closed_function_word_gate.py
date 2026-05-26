"""closed_function_word_gate.py — البَوّابَة العُلوى: الأَدوات المُغلَقَة.

تَوصيَة المُستَخدِم 2026-05-25:

  "ClosedFunctionWordContract يَجِب أَن يَسبِق VerbFormContract.
   لا يَجوز أَن تَدخُل هَذه الكَلِمات أَصلًا إلى مَسار الفِعل."

  مَثَل: مِمَّن، إِلَّا، فَإِنَّهُ، إِذَا، كَمَا، أَن، أَلَّا، وَلَا

القاعِدَة:
  إِذا كانَت الكَلِمَة في قائِمَة أَدوات مُغلَقَة
    → احسِمها HARF / MABNI / FUNCTIONAL
    → امنَع VerbFormContract مِن العَمَل عَلَيها
    إِلّا إذا كانَت في whitelist صَريح لِفِعل مُزدَوج الِاحتِمال.

مَصدَر القَواعِد: data/contracts/lists/closed_function_words.csv
(لا inline rules.)

تَأكيد: "ابدأ بـ ClosedFunctionWordOverrideGate.
لأَنّه سَيَمنَع تَوليد أَحداث وَهميَّة مِن الأَدوات،
وَيَحمي L4/L5 قَبل أَن نُكمِل AgentWindow."
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DIACRITICS = set("ًٌٍَُِّْٰـ")
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝ۥۦ۠")

_HERE = Path(__file__).resolve().parent
_CSV_PATH = _HERE / "data" / "contracts" / "lists" / "closed_function_words.csv"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _strip_all(s: str) -> str:
    return "".join(c for c in (s or "")
                   if c not in _DIACRITICS and c not in _SUBLETTERS)


def _normalize_alif(s: str) -> str:
    return (s or "").replace("ٱ", "ا")


# ─────────────────────────────────────────────────────────────────
# Lexicon
# ─────────────────────────────────────────────────────────────────

_FUNCTION_SURFACES: set[str] = set()         # exact diacritized surface
_FUNCTION_SURFACES_PLAIN: set[str] = set()   # stripped of diacritics
_FUNCTION_SURFACES_BARE: set[str] = set()    # also stripped of subletters
_INFO: dict[str, dict] = {}


def _load() -> None:
    if _FUNCTION_SURFACES:
        return
    if not _CSV_PATH.is_file():
        return
    with _CSV_PATH.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            surf = (row.get("surface") or "").strip()
            if not surf:
                continue
            _FUNCTION_SURFACES.add(surf)
            _FUNCTION_SURFACES_PLAIN.add(_strip_diac(surf))
            _FUNCTION_SURFACES_BARE.add(_strip_all(surf))
            # نَخزِن أَيضًا النَّسخَة المُطَبَّعَة ٱ→ا
            _FUNCTION_SURFACES_BARE.add(_strip_all(_normalize_alif(surf)))
            _INFO[surf] = row


# ─────────────────────────────────────────────────────────────────
# Main check
# ─────────────────────────────────────────────────────────────────

@dataclass
class FunctionWordResult:
    is_function: bool
    category: str = ""
    matched_surface: str = ""
    note: str = ""


def check_closed_function_word(token: str) -> FunctionWordResult:
    """يَفحَص هَل الـtoken في قائِمَة الأَدوات المُغلَقَة.

    يُحاوِل المُطابَقَة بِـ 3 مُستَويات (الأَدَقّ أَوَّلًا):
      1. surface كامِل بِالتَّشكيل   (دائِمًا مَسموح)
      2. stripped of diacritics       (مَسموح فَقَط بِلا تَنوين)
      3. stripped of all marks + ٱ→ا (مَسموح فَقَط بِلا تَنوين)

    تَوصيَة المُستَخدِم 2026-05-25:
      "ClosedFunctionWordOverrideGate يَجِب أَن يَعمَل بِالمُطابَقَة
       الكامِلَة فَقَط، وَلا يَحكُم HARF إذا وُجد تَنوين أَو علامَة
       اسميَّة قَويَّة."

    أَجَلٍ (اسم بِتَنوين كَسر) كانَ يُطابِق أَجَلْ (إِيجاب) عَبر
    الـstripped match. الآن يُمنَع.
    """
    _load()

    if not token or not token.strip():
        return FunctionWordResult(is_function=False)

    # Level 1: exact match (مَسموح دائِمًا)
    if token in _FUNCTION_SURFACES:
        row = _INFO.get(token, {})
        return FunctionWordResult(
            is_function=True,
            category=row.get("category", ""),
            matched_surface=token,
            note=row.get("note", ""),
        )

    # === HARD GATE: تَنوين عَلى الـtoken → اسم قَطعًا، لا أداة ===
    if any(c in token for c in ("ٌ", "ٍ", "ً")):
        return FunctionWordResult(is_function=False)

    # === HARD GATE: ال التَّعريف → اسم قَطعًا ===
    plain_check = _strip_diac(token).replace("ٱ", "ا")
    if plain_check.startswith("ال") and len(plain_check) >= 3:
        return FunctionWordResult(is_function=False)

    # === HARD GATE: تاء مَربوطَة → اسم ===
    if plain_check.endswith("ة"):
        return FunctionWordResult(is_function=False)

    # Level 2: stripped of diacritics — must match shadda count
    plain = _strip_diac(token)
    if plain in _FUNCTION_SURFACES_PLAIN:
        # Verify shadda parity to avoid هَمَّ matching هُمْ
        for surf in _FUNCTION_SURFACES:
            if _strip_diac(surf) == plain:
                if token.count("ّ") == surf.count("ّ"):
                    return FunctionWordResult(
                        is_function=True,
                        category=_INFO.get(surf, {}).get("category", "(stripped)"),
                        matched_surface=surf,
                        note="diacritic-insensitive match with shadda parity",
                    )
                break

    # Level 3: bare (no diacritics, no subletters, ٱ→ا) — also check shadda parity
    bare = _strip_all(_normalize_alif(token))
    if bare in _FUNCTION_SURFACES_BARE:
        for surf in _FUNCTION_SURFACES:
            surf_bare = _strip_all(_normalize_alif(surf))
            if surf_bare == bare and token.count("ّ") == surf.count("ّ"):
                return FunctionWordResult(
                    is_function=True,
                    category=_INFO.get(surf, {}).get("category", "(bare)"),
                    matched_surface=surf,
                    note="bare match with shadda parity",
                )

    return FunctionWordResult(is_function=False)


def is_closed_function_word(token: str) -> bool:
    """Quick yes/no."""
    return check_closed_function_word(token).is_function


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (token, expected_is_function)
        # Compounds that were leaking
        ("مِمَّن",      True),
        ("إِلَّا",      True),
        ("إِلَّآ",      True),
        ("فَإِنَّهُ",   True),
        ("فَإِنَّهُۥ",  True),
        ("أَن",         True),
        ("أَلَّا",      True),
        ("وَلَا",       True),
        ("كَمَا",       True),
        ("إِذَا",       True),
        ("إِنَّمَا",    True),
        ("لَكِنَّ",     True),
        # Real verbs — must NOT be function
        ("كَتَبَ",      False),
        ("يَكْتُبُ",    False),
        ("فَٱكْتُبُوهُ", False),
        ("وَلْيَكْتُبْ", False),
        # Real nouns
        ("كِتَابٌ",     False),
        ("ٱللَّهَ",     False),
    ]
    print(f"{'token':<22} {'expected':<10} {'got':<10} {'category':<20} note")
    print("-" * 100)
    for tok, exp in cases:
        r = check_closed_function_word(tok)
        mark = "✓" if r.is_function == exp else "✗"
        exp_s = "FUNC" if exp else "OK"
        got_s = "FUNC" if r.is_function else "OK"
        print(f"{mark} {tok:<20} {exp_s:<10} {got_s:<10} {r.category:<20} {r.note}")
