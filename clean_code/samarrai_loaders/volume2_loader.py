"""volume2_loader.py — مُحَمِّل قَواعِد المُجَلَّد الثَّاني (الأَفعال + المَفاعيل).

يَقرَأ CSVs مِن `data/contracts/maani/volume2/`:
  • zann_family_meanings.csv         — ظَنّ + أَخواتها + التَّحويل + التَّعليق
  • fail_naib_meanings.csv           — الفاعِل + نائِبه
  • mafool_bih_meanings.csv          — المَفعول بِه + الأَساليب
  • mafool_mutlaq_meanings.csv       — المَفعول المُطلَق + الظَّرف

CONSTITUTIONAL:
  • لا inline rules
  • التَّشكيل مَطلوب — vocalized_form أَوَّلًا
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
_CONTRACTS = _HERE.parent / "data" / "contracts" / "maani" / "volume2"

CONTRACT_NAME = "Volume2Loader:v1"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


_CACHE: dict | None = None

CSV_FILES = [
    ("zann_family", "zann_family_meanings.csv"),
    ("fail_naib", "fail_naib_meanings.csv"),
    ("mafool_bih", "mafool_bih_meanings.csv"),
    ("mafool_mutlaq", "mafool_mutlaq_meanings.csv"),
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
                    sp = rec.get("source_part", "")
                    spg = rec.get("source_page", "")
                    cache["by_source"].setdefault(f"ج{sp}_ص{spg}", []).append(rec)
        cache["file_loaded"][name] = len(records)
    _CACHE = cache
    return cache


def lookup_word(word: str, *, require_vocalized: bool = True) -> list[dict]:
    """يَجِد قَواعِد لِكَلِمَة (مَع التَّشكيل أَو بِدونه fallback)."""
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


def by_topic(topic_id: str) -> list[dict]:
    return _load()["by_topic_id"].get(topic_id, [])


def all_topics() -> list[str]:
    return sorted(_load()["by_topic_id"].keys())


def all_records() -> list[dict]:
    return _load()["all_records"]


def stats() -> dict:
    cache = _load()
    return {
        "contract": CONTRACT_NAME,
        "total_records": len(cache["all_records"]),
        "files": cache["file_loaded"],
        "topics": list(cache["by_topic_id"].keys()),
        "topics_count": len(cache["by_topic_id"]),
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

    print(f"\n=== اختبار lookup_word ===")
    tests = ["ظَنَّ", "حَسِبَ", "عَلِمَ", "رَأَى", "وَجَدَ", "جَعَلَ", "اتَّخَذَ"]
    for w in tests:
        results = lookup_word(w)
        if results:
            print(f"  «{w}» → {len(results)} سَجِلّ")
            for r in results[:2]:
                print(f"    ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")
                print(f"      مَصدَر: ج{r.get('source_part')} ص{r.get('source_page')}")
        else:
            print(f"  «{w}» → لا سِجِلّات")
