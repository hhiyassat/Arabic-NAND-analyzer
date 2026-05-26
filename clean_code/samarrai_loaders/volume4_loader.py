"""volume4_loader.py — مُحَمِّل قَواعِد المُجَلَّد الرَّابِع (الجَزم + الشَّرط + التَّوكيد + القَسَم + التَّقديم).

يَقرَأ CSVs مِن `data/contracts/maani/volume4/`:
  • jussive_particles.csv    — لَم، لَمَّا، لام الأَمر، لا النَّاهيَة
  • shart_particles.csv      — إِن، مَن، ما، مَتى، أَين، أَنَّى، حَيثُما، كَيفَما، أَيّ، إِذا، لَو، لَولا، أَمَّا
  • shart_constructions.csv  — لام الجَواب، ما الزَّائِدَة، تَقديم الاسم، فاء الجَواب، إِذا الفُجائيَّة
  • tawkid.csv               — التَّوكيد اللَّفظيّ + المَعنَويّ + نون التَّوكيد + قَد
  • qasam.csv                — حُروف القَسَم + جَواب القَسَم + القَسَم المُقَدَّر
  • tajaub.csv               — ما أَفعَلَهُ + أَفعِل بِه + سَماعيّ
  • taqdim_takhir.csv        — التَّقديم لِلِاختِصاص/الِاهتِمام + التَّأخير
  • future_amr_asma.csv      — السين، سَوفَ، فِعل الأَمر، أَسماء الأَفعال

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
_CONTRACTS = _HERE.parent / "data" / "contracts" / "maani" / "volume4"

CONTRACT_NAME = "Volume4Loader:v1"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _nfc(s)
    s = _strip_diac(s)
    return s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")


_CACHE: dict | None = None

CSV_FILES = [
    ("jussive_particles", "jussive_particles.csv"),
    ("shart_particles", "shart_particles.csv"),
    ("shart_constructions", "shart_constructions.csv"),
    ("tawkid", "tawkid.csv"),
    ("qasam", "qasam.csv"),
    ("tajaub", "tajaub.csv"),
    ("taqdim_takhir", "taqdim_takhir.csv"),
    ("future_amr_asma", "future_amr_asma.csv"),
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
        "by_operator": {},
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
                        cache["by_operator"].setdefault(op, []).append(rec)
                        op_plain = _normalize(op)
                        if op_plain != op:
                            cache["by_operator"].setdefault(op_plain, []).append(rec)
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


def by_operator(op: str) -> list[dict]:
    """يَجِد كُلّ مَعاني عامِل بِعَينه (مَثَلًا «إِن»، «لَم»، «لَو»)."""
    cache = _load()
    return cache["by_operator"].get(op, []) or \
           cache["by_operator"].get(_normalize(op), [])


def by_topic(topic_id: str) -> list[dict]:
    return _load()["by_topic_id"].get(topic_id, [])


def all_topics() -> list[str]:
    return sorted(_load()["by_topic_id"].keys())


def get_jussive_rules() -> list[dict]:
    """جَوازِم المُضارع: لَم، لَمَّا، لام الأَمر، لا النَّاهيَة."""
    cache = _load()
    out = []
    for tid in ("JAZM_LAM", "JAZM_LAMMA", "JAZM_LAM_AMR", "JAZM_LA_NAHIYA"):
        out.extend(cache["by_topic_id"].get(tid, []))
    return out


def get_shart_rules(*, jazim_only: bool = False) -> list[dict]:
    """أَدَوات الشَّرط (جازِمَة وَ غَير جازِمَة)."""
    cache = _load()
    out = []
    for tid, rules in cache["by_topic_id"].items():
        if not tid.startswith("SHART_"):
            continue
        for r in rules:
            if jazim_only and "non_jussive" in r.get("syntactic_effect", ""):
                continue
            out.append(r)
    return out


def get_tawkid_rules() -> list[dict]:
    cache = _load()
    out = []
    for tid in ("TAWKID_LAFDHI", "TAWKID_MAANAWI", "TAWKID_NUN", "TAWKID_QAD"):
        out.extend(cache["by_topic_id"].get(tid, []))
    return out


def get_qasam_rules() -> list[dict]:
    cache = _load()
    out = []
    for tid in ("QASAM_PARTICLES", "QASAM_JAWAB", "QASAM_HAZF"):
        out.extend(cache["by_topic_id"].get(tid, []))
    return out


def get_taqdim_rules() -> list[dict]:
    cache = _load()
    out = []
    for tid in cache["by_topic_id"]:
        if tid.startswith("TAQDIM") or tid.startswith("TAKHEER"):
            out.extend(cache["by_topic_id"][tid])
    return out


def stats() -> dict:
    cache = _load()
    return {
        "contract": CONTRACT_NAME,
        "total_records": len(cache["all_records"]),
        "files": cache["file_loaded"],
        "topics": list(cache["by_topic_id"].keys()),
        "topics_count": len(cache["by_topic_id"]),
        "operators_known": sorted(
            [o for o in cache["by_operator"].keys() if o != "—"]
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
    print(f"  العَوامِل المَعروفَة ({len(s['operators_known'])}):")
    print(f"    {s['operators_known']}")

    print(f"\n=== الجَوازِم ===")
    for r in get_jussive_rules():
        print(f"  ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")

    print(f"\n=== أَدَوات الشَّرط (الجازِمَة فَقَط) ===")
    for r in get_shart_rules(jazim_only=True):
        print(f"  ▸ {r.get('operator', '')}: {r.get('meaning_ar', '')[:60]}")

    print(f"\n=== التَّوكيد ===")
    for r in get_tawkid_rules()[:5]:
        print(f"  ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")

    print(f"\n=== القَسَم ===")
    for r in get_qasam_rules()[:4]:
        print(f"  ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")

    print(f"\n=== التَّقديم وَ التَّأخير ===")
    for r in get_taqdim_rules():
        print(f"  ▸ {r.get('meaning_id', '')}: {r.get('meaning_ar', '')[:60]}")

    print(f"\n=== اختبار by_operator ===")
    for op in ["إِنْ", "لَمْ", "لَوْ", "لِ", "وَ", "سَ"]:
        results = by_operator(op)
        if results:
            print(f"  «{op}» → {len(results)} مَعنى:")
            for r in results[:2]:
                print(f"    ▸ {r.get('meaning_ar', '')[:55]}")
        else:
            print(f"  «{op}» → لا مَعانٍ")
