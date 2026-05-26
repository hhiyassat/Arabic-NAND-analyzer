"""defective_verb_contract.py — عَقد الأَفعال الناقِصَة (كَان وَ أَخواتُها).

تَنفيذ تَوصيَة المُستَخدِم 2026-05-25:

  "كان وَ ليس تَحتاج عُقود ناقِصَة، لا agent/patient عاديّ.
   هَذه عَلاقات اسم/خَبَر، لا فاعل/مَفعول.

   إذن أَضِف: DefectiveVerbContract
   يُحَوِّل: كَانَ، لَيْسَ، صار، بات...
   إلى: defective_verb
   وَيُصدِر: ism_of_kana / khabar_of_kana / ism_of_laysa / khabar_of_laysa
   ولا يَسمَح لها بِإِنتاج agent_of / patient_of."

البَوّابَة:
  is_defective_verb(token, lemma=None) -> bool
    True إذا lemma في kana_family أو الـsurface مَعروف

وَقَوائم العَلاقات الخاصَّة:
  defective_relation_for(lemma) -> {topic_relation, comment_relation}

مَصدَر القاعِدَة: data/contracts/lists/kana_family.csv
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DIACRITICS = set("ًٌٍَُِّْٰـ")

_HERE = Path(__file__).resolve().parent
_KANA_CSV = _HERE / "data" / "contracts" / "lists" / "kana_family.csv"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


# ─────────────────────────────────────────────────────────────────
# Lexicon
# ─────────────────────────────────────────────────────────────────

_KANA_SURFACES: set[str] = set()       # all kana-family surface forms (vocalized)
_KANA_SURFACES_PLAIN: set[str] = set() # stripped
_KANA_LEMMAS: set[str] = set()         # lemma list (كان، ليس، ...)
_SURFACE_TO_LEMMA: dict[str, str] = {}


def _load() -> None:
    if _KANA_SURFACES:
        return
    if not _KANA_CSV.is_file():
        return
    with _KANA_CSV.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            surf = (row.get("surface") or "").strip()
            lemma = (row.get("lemma") or "").strip()
            if not surf:
                continue
            _KANA_SURFACES.add(surf)
            _KANA_SURFACES_PLAIN.add(_strip_diac(surf))
            if lemma:
                _KANA_LEMMAS.add(lemma)
                _SURFACE_TO_LEMMA[surf] = lemma
                _SURFACE_TO_LEMMA[_strip_diac(surf)] = lemma


# Relation-name mapping per lemma. كان family → kana_*, ليس → laysa_*
_LEMMA_TO_RELATIONS: dict[str, dict[str, str]] = {
    "كان":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "صار":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "أصبح":  {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "أمسى":  {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "أضحى":  {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "ظل":    {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "بات":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "عاد":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "زال":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "برح":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "فتئ":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "انفك":  {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    "دام":   {"topic": "ism_of_kana",   "comment": "khabar_of_kana"},
    # ليس مُسْتَقِلّ — يَصلُح أَيضًا kana-family لَكِن نُمَيِّزه
    "ليس":   {"topic": "ism_of_laysa",  "comment": "khabar_of_laysa"},
}


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

@dataclass
class DefectiveVerbInfo:
    is_defective: bool
    lemma: str = ""
    topic_relation: str = ""    # ism_of_kana / ism_of_laysa
    comment_relation: str = ""  # khabar_of_kana / khabar_of_laysa


def check_defective_verb(token: str, *, lemma_hint: str = "") -> DefectiveVerbInfo:
    """يَفحَص هَل الـtoken/lemma فِعل ناقِص.

    Args:
      token: السَّطح (مَع/بِدون تَشكيل)
      lemma_hint: إذا الـlayer1 أَعطى lemma بِالفِعل، نَستَخدِمه مُباشَرَة

    Returns:
      DefectiveVerbInfo(is_defective, lemma, topic_relation, comment_relation)
    """
    _load()

    # طَريق 1: lemma صَريح
    if lemma_hint:
        rels = _LEMMA_TO_RELATIONS.get(lemma_hint, {})
        if rels:
            return DefectiveVerbInfo(
                is_defective=True,
                lemma=lemma_hint,
                topic_relation=rels.get("topic", ""),
                comment_relation=rels.get("comment", ""),
            )

    # طَريق 2: surface lookup
    if token in _KANA_SURFACES or _strip_diac(token) in _KANA_SURFACES_PLAIN:
        lemma = _SURFACE_TO_LEMMA.get(token) or _SURFACE_TO_LEMMA.get(_strip_diac(token), "")
        rels = _LEMMA_TO_RELATIONS.get(lemma, {})
        return DefectiveVerbInfo(
            is_defective=True,
            lemma=lemma,
            topic_relation=rels.get("topic", "ism_of_kana"),
            comment_relation=rels.get("comment", "khabar_of_kana"),
        )

    # طَريق 3: نَزع بادِئة عَطف/جَزم وَ إِعادَة البَحث
    plain = _strip_diac(token)
    for prefix_len in (1, 2):
        if len(plain) <= prefix_len + 1:
            continue
        body = plain[prefix_len:]
        if body in _KANA_SURFACES_PLAIN:
            lemma = _SURFACE_TO_LEMMA.get(body, "")
            rels = _LEMMA_TO_RELATIONS.get(lemma, {})
            return DefectiveVerbInfo(
                is_defective=True,
                lemma=lemma,
                topic_relation=rels.get("topic", "ism_of_kana"),
                comment_relation=rels.get("comment", "khabar_of_kana"),
            )

    return DefectiveVerbInfo(is_defective=False)


def is_defective_verb(token: str, *, lemma_hint: str = "") -> bool:
    """Quick yes/no — يُستَدعى في relation_extractor قَبل agent/patient emission."""
    return check_defective_verb(token, lemma_hint=lemma_hint).is_defective


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = [
        # (token, lemma_hint, expected_defective, expected_topic_rel)
        ("كَانَ",   "كان",  True,  "ism_of_kana"),
        ("لَيْسَ",  "ليس",  True,  "ism_of_laysa"),
        ("فَلَيْسَ", "ليس", True,  "ism_of_laysa"),
        ("وَكَانَ", "كان",  True,  "ism_of_kana"),
        ("صَارَ",   "صار",  True,  "ism_of_kana"),
        ("أَصْبَحَتْ", "أصبح", True, "ism_of_kana"),
        ("بَاتُوا", "بات",  True,  "ism_of_kana"),
        # Non-defective verbs
        ("كَتَبَ",   "كتب",  False, ""),
        ("يَكْتُبُ", "كتب",  False, ""),
        ("اكْتُبْ",  "كتب",  False, ""),
        # No lemma hint
        ("كَانَ",   "",     True,  "ism_of_kana"),
        ("لَيْسَ",  "",     True,  "ism_of_laysa"),
    ]
    print(f"{'token':<14} {'lemma':<8} {'expected':<10} {'got':<14} {'topic_rel'}")
    print("-" * 80)
    for tok, lh, exp, exp_rel in cases:
        info = check_defective_verb(tok, lemma_hint=lh)
        ok = (info.is_defective == exp) and (exp_rel == "" or info.topic_relation == exp_rel)
        mark = "✓" if ok else "✗"
        exp_str = "DEF" if exp else "NOT"
        got_str = f"DEF({info.lemma})" if info.is_defective else "NOT"
        print(f"{mark} {tok:<12} {lh:<8} {exp_str:<10} {got_str:<14} {info.topic_relation}")
