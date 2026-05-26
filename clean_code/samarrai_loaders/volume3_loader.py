"""volume3_loader.py — مُحَمِّل قَواعِد المُجَلَّد الثَّالِث (حُروف الجَرّ + التَّضمين).

يَقرَأ CSVs مِن `data/contracts/maani/volume3/`:
  • tadmin_and_policy.csv      — قاعِدَة التَّضمين + سياسَة عَدَم النِّيابَة
  • prep_ila_meanings.csv      — حَرف إلى (5 مَعانٍ)
  • prep_ba_meanings.csv       — حَرف الباء (10 مَعانٍ)
  • prep_lam_meanings.csv      — حَرف اللام (8 مَعانٍ)
  • prep_others_meanings.csv   — مِن، عَن، على، في، الكاف، الواو، حَتَّى

CONSTITUTIONAL:
  • لا inline rules
  • التَّشكيل مَطلوب
  • source_part + source_page لِكُلّ سَطر
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Optional


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)

_HERE = Path(__file__).resolve().parent
_CONTRACTS = _HERE.parent / "data" / "contracts" / "maani" / "volume3"

CONTRACT_NAME = "Volume3Loader:v1"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


_CACHE: dict | None = None

CSV_FILES = [
    ("tadmin_policy", "tadmin_and_policy.csv"),
    ("prep_ila", "prep_ila_meanings.csv"),
    ("prep_ba", "prep_ba_meanings.csv"),
    ("prep_lam", "prep_lam_meanings.csv"),
    ("prep_others", "prep_others_meanings.csv"),
    ("prep_supplementary", "prep_supplementary_meanings.csv"),
]


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cache = {
        "all_records": [],
        "by_vocalized": {},
        "by_plain": {},
        "by_topic_id": {},
        "by_preposition": {},   # خَريطَة سَريعَة: «إلى» → list of meanings
        "by_source": {},
        "file_loaded": {},
    }
    for name, fname in CSV_FILES:
        path = _CONTRACTS / fname
        records = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rec = dict(row)
                    voc = _nfc(rec.get("vocalized_form", "").strip())
                    op = _nfc(rec.get("operator", "").strip())
                    rec["vocalized_form"] = voc
                    rec["plain"] = _normalize(voc) if voc and voc != "—" else ""
                    rec["source_file"] = fname
                    records.append(rec)
                    cache["all_records"].append(rec)
                    if voc and voc != "—":
                        cache["by_vocalized"].setdefault(voc, []).append(rec)
                        cache["by_plain"].setdefault(rec["plain"], []).append(rec)
                    tid = rec.get("topic_id", "")
                    if tid:
                        cache["by_topic_id"].setdefault(tid, []).append(rec)
                    if op and op != "—":
                        cache["by_preposition"].setdefault(op, []).append(rec)
                        op_plain = _normalize(op)
                        if op_plain != op:
                            cache["by_preposition"].setdefault(op_plain, []).append(rec)
                    sp = rec.get("source_part", "")
                    spg = rec.get("source_page", "")
                    cache["by_source"].setdefault(f"ج{sp}_ص{spg}", []).append(rec)
        cache["file_loaded"][name] = len(records)
    _CACHE = cache
    return cache


def lookup_word(word: str, *, require_vocalized: bool = True) -> list[dict]:
    if not word:
        return []
    cache = _load()
    word_nfc = _nfc(word)
    # مُطابَقَة مُشَكَّلَة دَقيقَة → لا plain fallback
    if require_vocalized and word_nfc in cache["by_vocalized"]:
        return list(cache["by_vocalized"][word_nfc])
    plain = _normalize(word_nfc)
    if plain in cache["by_plain"]:
        return list(cache["by_plain"][plain])
    return []


def by_preposition(prep: str) -> list[dict]:
    """يَجِد كُلّ مَعاني حَرف جَرّ بِعَينه."""
    cache = _load()
    return cache["by_preposition"].get(prep, []) or \
           cache["by_preposition"].get(_normalize(prep), [])


def by_topic(topic_id: str) -> list[dict]:
    return _load()["by_topic_id"].get(topic_id, [])


def all_topics() -> list[str]:
    return sorted(_load()["by_topic_id"].keys())


def get_tadmin_principle() -> list[dict]:
    """يَجلِب كُلّ قَواعِد التَّضمين."""
    return _load()["by_topic_id"].get("TADMIN", [])


def get_no_substitution_policy() -> list[dict]:
    return _load()["by_topic_id"].get("PREP_POLICY", [])


def stats() -> dict:
    cache = _load()
    return {
        "contract": CONTRACT_NAME,
        "total_records": len(cache["all_records"]),
        "files": cache["file_loaded"],
        "topics": list(cache["by_topic_id"].keys()),
        "topics_count": len(cache["by_topic_id"]),
        "prepositions_known": sorted(
            [p for p in cache["by_preposition"].keys() if p != "—"]
        ),
    }


if __name__ == "__main__":
    s = stats()
    print(f"contract: {CONTRACT_NAME}")
    print(f"\n=== الإِحصاءات ===")
    print(f"  إِجماليّ السِّجِلّات: {s['total_records']}")
    print(f"  المَلَفّات:")
    for name, n in s['files'].items():
        print(f"    {name}: {n}")
    print(f"  الأَبواب ({s['topics_count']}):")
    for t in s['topics']:
        print(f"    - {t}")
    print(f"  الحُروف المَعروفَة ({len(s['prepositions_known'])}):")
    print(f"    {s['prepositions_known']}")

    print(f"\n=== اختبار by_preposition ===")
    for prep in ["إِلَى", "بِ", "لِ", "مِنْ", "عَلَى", "في", "كَ", "رُبَّ", "مُنذُ", "تَ", "خَلا", "كَيْ"]:
        results = by_preposition(prep)
        if results:
            print(f"  «{prep}» → {len(results)} مَعنى:")
            for r in results[:3]:
                print(f"    ▸ {r.get('meaning_ar', '')[:60]}")
        else:
            print(f"  «{prep}» → لا مَعانٍ")

    print(f"\n=== التَّضمين ===")
    for r in get_tadmin_principle()[:3]:
        print(f"  ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:70]}")
