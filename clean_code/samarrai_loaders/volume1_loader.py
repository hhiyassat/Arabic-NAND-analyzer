"""volume1_loader.py — مُحَمِّل قَواعِد المُجَلَّد الأَوَّل (المَعارِف + الإِسناد).

يَقرَأ CSVs مِن `data/contracts/maani/volume1/`:
  • pronouns_meanings.csv
  • demonstratives_meanings.csv
  • al_definite_meanings.csv
  • relative_pronouns_meanings.csv
  • mubtada_khabar_meanings.csv

CONSTITUTIONAL:
  • لا inline rules
  • كُلّ سَطر يُحَمَّل مَع source_part + source_page
  • التَّشكيل مَطلوب — الـ lookup يَتِمّ عَلى vocalized_form أَوَّلًا
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_CONTRACTS = _HERE.parent / "data" / "contracts" / "maani" / "volume1"

CONTRACT_NAME = "Volume1Loader:v1"


DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    """تَطبيع Unicode — يُوَحِّد تَرتيب الشَّدَّة + الحَرَكَة (NFC)."""
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


# ─── الـ singleton state ───────────────────────────────────────────────

_CACHE: dict | None = None

CSV_FILES = [
    ("pronouns", "pronouns_meanings.csv"),
    ("demonstratives", "demonstratives_meanings.csv"),
    ("al_definite", "al_definite_meanings.csv"),
    ("relative", "relative_pronouns_meanings.csv"),
    ("mubtada_khabar", "mubtada_khabar_meanings.csv"),
]


def _load() -> dict:
    """يُحَمِّل كُلّ CSVs مَرَّة واحِدَة."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cache = {
        "all_records": [],
        "by_vocalized": {},    # vocalized_form → records
        "by_plain": {},         # plain (no diac) → records
        "by_topic_id": {},     # topic_id → records
        "by_source": {},        # source ("ج1 ص35") → records
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
                    # نُطَبِّع — NFC لِتَوحيد تَرتيب الشَّدَّة + الحَرَكَة
                    voc = _nfc(rec.get("vocalized_form", "").strip())
                    rec["vocalized_form"] = voc
                    rec["plain"] = _normalize(voc)
                    rec["source_file"] = fname
                    records.append(rec)
                    cache["all_records"].append(rec)
                    cache["by_vocalized"].setdefault(voc, []).append(rec)
                    cache["by_plain"].setdefault(rec["plain"], []).append(rec)
                    tid = rec.get("topic_id", "")
                    if tid:
                        cache["by_topic_id"].setdefault(tid, []).append(rec)
                    sp = rec.get("source_part", "")
                    spg = rec.get("source_page", "")
                    src_key = f"ج{sp}_ص{spg}"
                    cache["by_source"].setdefault(src_key, []).append(rec)
        cache["file_loaded"][name] = len(records)
    _CACHE = cache
    return cache


# ─── API ───────────────────────────────────────────────────────────────

def lookup_word(word: str, *, require_vocalized: bool = True) -> list[dict]:
    """يَجِد كُلّ القَواعِد المُتَعَلِّقَة بِكَلِمَة.

    require_vocalized=True: نُجَرِّب التَّطابُق المُشَكَّل أَوَّلًا، ثُمّ المُجَرَّد
    require_vocalized=False: نَلجَأ مُباشَرَة إلى المُجَرَّد
    """
    if not word:
        return []
    cache = _load()
    word_nfc = _nfc(word)
    # 1. مُحَكَّك بِالتَّشكيل — لَو وُجِدَت مُطابَقَة دَقيقَة فَلا fallback
    if require_vocalized and word_nfc in cache["by_vocalized"]:
        return list(cache["by_vocalized"][word_nfc])
    # 2. fallback مُجَرَّد فَقَط عِندَ غِياب التَّطابُق المُشَكَّل
    plain = _normalize(word_nfc)
    if plain in cache["by_plain"]:
        return list(cache["by_plain"][plain])
    return []


def by_topic(topic_id: str) -> list[dict]:
    """يَجِد كُلّ السِّجِلّات لِبابٍ مُعَيَّن."""
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


# ─── self-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    s = stats()
    print(f"contract: {CONTRACT_NAME}")
    print(f"\n=== الإِحصاءات ===")
    print(f"  إِجماليّ السِّجِلّات: {s['total_records']}")
    print(f"  المَلَفّات:")
    for name, n in s['files'].items():
        print(f"    {name}: {n}")
    print(f"  الأَبواب: {s['topics_count']}")
    for t in s['topics']:
        print(f"    - {t}")

    print(f"\n=== اختبار lookup_word ===")
    tests = ["إِيَّاكَ", "هَذَا", "ذَلِكَ", "الَّذِي", "هُوَ", "أَنتَ", "ذَلِكُمْ"]
    for w in tests:
        results = lookup_word(w)
        if results:
            print(f"  «{w}» → {len(results)} سَجِلّ")
            for r in results[:2]:
                print(f"    ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")
                print(f"      مَصدَر: ج{r.get('source_part')} ص{r.get('source_page')}")
        else:
            print(f"  «{w}» → لا سِجِلّات")
