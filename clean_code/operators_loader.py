"""operators_loader.py — مُحَمِّل العَوامِل النَّحويَّة الـ 97 («العَوامِل المِئَة»).

يَقرَأ `data/contracts/lists/operators_catalog.csv` (22 مَجموعَة، 97 عامِل فَريد)
وَ يُوَفِّر API لِلبَحث وَ التَّصنيف.

أَولَويَّة: ZANN (مَج 13) + KANA (مَج 10) + INNA (مَج 2) + AFAL_MUQARABA (مَج 11)

تَركيب الـ CSV:
  Group Number, Arabic Group Name, English Group Name, Operator,
  Purpose/Usage, Example, Note, Example_Vocalized

تَركيب الـ KB:
  • by_operator(token) — يَرجِع كُلّ السِّجِلّات الَّتي تَحوي العامِل
  • by_group(group_id) — كُلّ سِجِلّات مَجموعَة
  • all_priority_operators() — قائِمَة الأولَويَّة لِلدَّمج

CONSTITUTIONAL: مَصدَر الادِّعاء = operators_catalog (لا inline rules).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_CATALOG_PATH = _HERE / "data" / "contracts" / "lists" / "operators_catalog.csv"

CONTRACT_NAME = "OperatorsCatalog:v1"

# مَجموعات الأولَويَّة (عاليَة التَّأثير في القُرآن)
PRIORITY_GROUPS = {
    "2": "إنَّ_وَ_أَخواتها",          # 6 عَوامِل
    "10": "كانَ_وَ_أَخواتها",         # 13 عامِلًا
    "11": "أَفعال_المُقارَبَة",        # 4
    "13": "أَفعال_القُلوب_الناصِبَة",  # 7 (ZANN family)
}

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return s


_CACHE: dict | None = None


def _load_catalog() -> dict:
    """يُحَمِّل الكاتالوغ مَرَّة واحِدَة."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not _CATALOG_PATH.exists():
        _CACHE = {"records": [], "by_op": {}, "by_op_plain": {}, "by_group": {}}
        return _CACHE

    records = []
    by_op: dict[str, list] = {}
    by_op_plain: dict[str, list] = {}
    by_group: dict[str, list] = {}

    with open(_CATALOG_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # نَتَجاوَز header الـ duplicate (إِن وُجِد)
            if row.get("Group Number", "").startswith("Group"):
                continue
            gn = row.get("Group Number", "").strip()
            if not gn:
                continue
            record = {
                "group_id": gn,
                "group_ar": row.get("Arabic Group Name", "").strip(),
                "group_en": row.get("English Group Name", "").strip(),
                "operator": row.get("Operator", "").strip(),
                "operator_plain": _normalize(row.get("Operator", "").strip()),
                "purpose": row.get("Purpose/Usage", "").strip(),
                "example": row.get("Example", "").strip(),
                "example_vocalized": row.get("Example_Vocalized", "").strip(),
                "note": row.get("Note", "").strip(),
                "is_priority": gn in PRIORITY_GROUPS,
                "priority_name": PRIORITY_GROUPS.get(gn, ""),
            }
            records.append(record)
            by_op.setdefault(record["operator"], []).append(record)
            by_op_plain.setdefault(record["operator_plain"], []).append(record)
            by_group.setdefault(gn, []).append(record)

    _CACHE = {
        "records": records,
        "by_op": by_op,
        "by_op_plain": by_op_plain,
        "by_group": by_group,
    }
    return _CACHE


# ─── API ───────────────────────────────────────────────────────────────

def all_operators() -> list[dict]:
    return _load_catalog()["records"]


def all_groups() -> dict[str, list]:
    return _load_catalog()["by_group"]


def by_operator(token: str, normalize: bool = True) -> list[dict]:
    """يَجِد كُلّ السِّجِلّات الَّتي تَحوي العامِل (مَع/بِلا تَطبيع)."""
    kb = _load_catalog()
    if not normalize:
        return kb["by_op"].get(token, [])
    plain = _normalize(token)
    return kb["by_op_plain"].get(plain, [])


def by_group(group_id: str) -> list[dict]:
    return _load_catalog()["by_group"].get(group_id, [])


def _strip_first_prefix_keep_diac(word: str) -> str:
    """يَنزَع بادِئَة واحِدَة (و/ف/ب/ل) بِالاحتِفاظ بِالتَّشكيل لِلباقي."""
    if not word:
        return word
    if word[0] not in "وفبلكس":
        return word
    i = 1
    while i < len(word) and word[i] in DIACRITICS:
        i += 1
    return word[i:]


def lookup_in_word(word: str) -> Optional[dict]:
    """يَفحَص هَل الكَلِمَة هي عامِل.

    Strategy:
      1. تَطابُق حَرفيّ كامِل (مَع التَّشكيل) — يُفَرِّق «كَانَ» عَن «كَأَنَّ»
      2. تَطابُق بَعد نَزع بادِئَة واحِدَة (مَع التَّشكيل)
      3. تَطابُق بِالتَّجريد (fallback أَخير)
    """
    if not word:
        return None
    kb = _load_catalog()

    # 1. تَطابُق مُشَكَّل مُباشَر
    if word in kb["by_op"]:
        records = kb["by_op"][word]
        r = sorted(records, key=lambda r: not r["is_priority"])[0]
        return {**r, "_match_info": {"matched_form": word, "match_type": "exact_vocalized",
                                       "original_word": word, "alternatives_count": len(records)}}

    # 2. تَطابُق مُشَكَّل بَعد نَزع بادِئَة
    w1 = _strip_first_prefix_keep_diac(word)
    if w1 != word and w1 in kb["by_op"]:
        records = kb["by_op"][w1]
        r = sorted(records, key=lambda r: not r["is_priority"])[0]
        return {**r, "_match_info": {"matched_form": w1, "match_type": "prefix_stripped_vocalized",
                                       "original_word": word, "alternatives_count": len(records)}}

    # 3. تَطابُق مُجَرَّد (fallback)
    plain = _normalize(word)
    candidates = [plain]
    for p in ["و", "ف", "ل", "ب"]:
        if plain.startswith(p) and len(plain) > len(p) + 1:
            candidates.append(plain[len(p):])
    for cand in candidates:
        records = kb["by_op_plain"].get(cand)
        if records:
            r = sorted(records, key=lambda r: not r["is_priority"])[0]
            return {**r, "_match_info": {"matched_form": cand, "match_type": "plain_fallback",
                                           "original_word": word, "alternatives_count": len(records)}}
    return None


def stats() -> dict:
    kb = _load_catalog()
    priority_count = sum(1 for r in kb["records"] if r["is_priority"])
    return {
        "contract": CONTRACT_NAME,
        "total_records": len(kb["records"]),
        "unique_operators": len(kb["by_op"]),
        "groups": len(kb["by_group"]),
        "priority_records": priority_count,
        "priority_groups": list(PRIORITY_GROUPS.values()),
    }


# ─── self-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"contract: {CONTRACT_NAME}")
    s = stats()
    print(f"\n=== الإِحصائيَّات ===")
    for k, v in s.items():
        print(f"  {k}: {v}")

    print(f"\n=== مَجموعات الأولَويَّة ===")
    for gid, name in PRIORITY_GROUPS.items():
        recs = by_group(gid)
        ops = sorted(set(r["operator"] for r in recs))
        print(f"  مَج {gid} ({name}): {len(ops)} عامِل")
        print(f"    {ops}")

    print(f"\n=== اختِبار lookup_in_word ===")
    for w in ["كَانَ", "إِنَّ", "ظَنَّ", "كَادَ", "أَصْبَحَ", "وَكَانَ", "فَإِنَّ",
              "لَيْسَ", "الكتاب", "خَلَقَ"]:
        r = lookup_in_word(w)
        if r:
            print(f"  «{w}» → عامِل [مَج {r['group_id']}: {r['group_ar']}]"
                  f" — {r['purpose'][:50]}")
        else:
            print(f"  «{w}» → لَيس عامِلًا")
