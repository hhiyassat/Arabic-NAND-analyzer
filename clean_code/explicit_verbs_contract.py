"""explicit_verbs_contract.py — مُعجَم أَفعال صَريحَة لا تَكشِفها العُقود الصَّرفيَّة.

تَوصيَة المُستَخدِم 2026-05-25 (الجَلسَة المُتأَخِّرَة):

  "ImperativeShortVerbContract: قُلْ، خُذْ، كُلْ، ائتِ، ائتِنَا
   WeakPastVerbContract: هَدَىٰ، جَآءَ، حَقَّ، شَآءَ"

هَذه الأَفعال:
  • قَصيرَة (≤4 حُروف) فَلا تَدخُل أَنماط VerbFormContract الصارِمَة
  • مُعتَلَّة (هَدَىٰ، جَآءَ) أَو مُضَعَّفَة (حَقَّ، ضَلَّ) فَلا تُطابِق نَمَط فَعَلَ
  • مُلتَبِسَة مَع أَسماء (قُلْ vs قَوْل) فَتَحتاج قَرار لُغَويّ

الحَلّ: مُعجَم صَريح في explicit_verbs_lexicon.csv.

API:
  is_explicit_verb(token) → bool
  get_verb_info(token) → dict | None
"""

from __future__ import annotations

import csv
from pathlib import Path

_DIACRITICS = set("ًٌٍَُِّْٰـ")
_SUBLETTERS = set("ٰۭٓۚۖۗۘۙۛۜ۝ۥۦ")

_HERE = Path(__file__).resolve().parent
_CSV_PATH = _HERE / "data" / "contracts" / "lists" / "explicit_verbs_lexicon.csv"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


def _strip_all(s: str) -> str:
    return "".join(c for c in (s or "")
                   if c not in _DIACRITICS and c not in _SUBLETTERS)


def _normalize(s: str) -> str:
    return (s or "").replace("ٱ", "ا").replace("آ", "ا")


# ─────────────────────────────────────────────────────────────────
# Lexicon
# ─────────────────────────────────────────────────────────────────

_VERB_EXACT: dict[str, dict] = {}
_VERB_PLAIN: dict[str, dict] = {}
_VERB_BARE: dict[str, dict] = {}


def _load() -> None:
    if _VERB_EXACT:
        return
    if not _CSV_PATH.is_file():
        return
    with _CSV_PATH.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            surf = (row.get("surface") or "").strip()
            if not surf:
                continue
            _VERB_EXACT[surf] = row
            _VERB_PLAIN.setdefault(_strip_diac(surf), row)
            bare = _strip_all(_normalize(surf))
            _VERB_BARE.setdefault(bare, row)


def is_explicit_verb(token: str) -> bool:
    """True إِذا الـtoken في مُعجَم الأَفعال الصَّريحَة.

    تَقييد صارِم: exact match فَقَط أَو diacritic-only stripping.
    لا bare matching (يَفقِد الشَّدّة وَيُلتَبِس عِلْمِهِ بِـ عَلَّمَهُ).
    """
    _load()
    if not token:
        return False
    if token in _VERB_EXACT:
        return True
    # plain match يُحافِظ عَلى الشَّدّة (لا يَستَخدِم _strip_all)
    plain = _strip_diac(token)
    if plain in _VERB_PLAIN:
        # تَأَكَّد أَنّ الـsurface المَطابِق له نَفس عَدَد الشَّدّات
        matched = _VERB_PLAIN[plain]
        matched_surf = matched.get("surface", "")
        if token.count("ّ") == matched_surf.count("ّ"):
            return True
    # نَزع و/ف prefix إِذا كانَت بادِئة عَطف
    if token.startswith(("وَ", "فَ")) and len(token) > 2:
        return is_explicit_verb(token[2:])
    if token.startswith(("و", "ف")) and len(token) > 1:
        rest = token[1:]
        if rest in _VERB_EXACT:
            return True
        rest_plain = _strip_diac(rest)
        if rest_plain in _VERB_PLAIN:
            matched = _VERB_PLAIN[rest_plain]
            if rest.count("ّ") == matched.get("surface","").count("ّ"):
                return True
    return False


def get_verb_info(token: str) -> dict | None:
    """يَرُدّ الـrow أَو None — مَع نَفس التَّقييد الصارِم."""
    _load()
    if not token:
        return None
    if token in _VERB_EXACT:
        return _VERB_EXACT[token]
    plain = _strip_diac(token)
    if plain in _VERB_PLAIN:
        matched = _VERB_PLAIN[plain]
        if token.count("ّ") == matched.get("surface","").count("ّ"):
            return matched
    if token.startswith(("وَ", "فَ")) and len(token) > 2:
        info = get_verb_info(token[2:])
        if info:
            return info
    if token.startswith(("و", "ف")) and len(token) > 1:
        info = get_verb_info(token[1:])
        if info:
            return info
    return None


if __name__ == "__main__":
    cases = [
        ("قُلْ", True), ("ٱئْتِنَا", True), ("هَدَىٰ", True),
        ("حَقَّ", True), ("جَآءَهُمْ", True), ("قَالَ", True),
        ("وَجَآءَ", True), ("فَقَالَ", True),
        ("كِتَاب", False), ("الْكِتَابُ", False),
    ]
    for tok, exp in cases:
        got = is_explicit_verb(tok)
        mark = "✓" if got == exp else "✗"
        print(f"  {mark} {tok:18s} expected={exp} got={got}")
