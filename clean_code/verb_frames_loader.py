"""verb_frames_loader.py — تَحميل verb argument frames مِن القُرآن.

المَصدَر: `data/extracted/verb_frames_from_quran_i3rab.csv` (6,758 فِعل)
كُلّ فِعل لَه إِحصاءات عَن أَدوار الـ arguments المُشاهَدَة:
  • role_subject (الفاعِل)
  • role_direct_object (المَفعول بِه)
  • role_prep_phrase (شِبه جُملَة)
  • role_state (حال)
  • role_predicate (خَبَر)
  • ...إِلخ

يُستَخدَم في event_extractor لِـ:
  1. تَوَقُّع الـ arguments المُحتَمَلَة لِفِعل
  2. تَرجيح argument structure
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
VERB_FRAMES_CSV = _HERE.parent / "data" / "extracted" / "verb_frames_from_quran_i3rab.csv"

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


@dataclass
class VerbFrame:
    """frame إِحصائيّ لِفِعل: ما الأَدوار المُشاهَدَة في القُرآن."""

    verb_surface: str             # الكَلِمَة كَما وَرَدَت (بِلا تَشكيل غالِبًا)
    occurrences: int              # عَدَد مَرّات الظُّهور
    total_args: int               # مَجموع الأَدوار المُشاهَدَة
    roles: dict[str, int] = field(default_factory=dict)

    @property
    def has_subject(self) -> bool:
        return self.roles.get("role_subject", 0) > 0

    @property
    def has_object(self) -> bool:
        return self.roles.get("role_direct_object", 0) > 0

    @property
    def takes_prep(self) -> bool:
        return self.roles.get("role_prep_phrase", 0) > 0

    @property
    def is_copular(self) -> bool:
        """فِعل ناقِص (يَأخُذ خَبَر) — مِثل كانَ وَ أَخَواتها."""
        return self.roles.get("role_predicate", 0) > self.roles.get("role_direct_object", 0)

    def most_common_roles(self, top_n: int = 5) -> list[tuple[str, int]]:
        return sorted(self.roles.items(), key=lambda x: -x[1])[:top_n]


_CACHE: dict[str, VerbFrame] | None = None


def _load() -> dict[str, VerbFrame]:
    """يُحَمِّل verb frames — index: verb_plain → VerbFrame."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    cache: dict[str, VerbFrame] = {}
    if not VERB_FRAMES_CSV.exists():
        _CACHE = cache
        return cache
    with open(VERB_FRAMES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            surface = row.get("verb_surface", "").strip()
            if not surface:
                continue
            surface_plain = _strip_diac(_nfc(surface))
            try:
                occ = int(row.get("occurrences", 0))
                total = int(row.get("total_args", 0))
            except ValueError:
                continue
            roles = {}
            for k, v in row.items():
                if k and k.startswith("role_") and v:
                    try:
                        roles[k] = int(float(v))
                    except (ValueError, TypeError):
                        pass
            frame = VerbFrame(
                verb_surface=surface,
                occurrences=occ,
                total_args=total,
                roles=roles,
            )
            cache[surface] = frame
            if surface_plain != surface:
                cache[surface_plain] = frame
    _CACHE = cache
    return cache


def get_frame(verb: str) -> Optional[VerbFrame]:
    """يَجِب frame لِفِعل (مَع التَّطبيع)."""
    cache = _load()
    voc = _nfc(verb)
    if voc in cache:
        return cache[voc]
    plain = _strip_diac(voc)
    return cache.get(plain)


def stats() -> dict:
    cache = _load()
    return {
        "total_verbs": len({f.verb_surface for f in cache.values()}),
        "total_entries": len(cache),
        "top_10_verbs": sorted(
            {f.verb_surface: f.occurrences for f in cache.values()}.items(),
            key=lambda x: -x[1]
        )[:10],
    }


if __name__ == "__main__":
    s = stats()
    print(f"verb_frames: {s['total_verbs']} فِعل فَريد")
    print(f"\nأَكثَر 10 أَفعال:")
    for v, n in s['top_10_verbs']:
        print(f"  {v}: {n}")

    print(f"\n=== اختبار قال ===")
    f = get_frame("قال")
    if f:
        print(f"  occurrences: {f.occurrences}")
        print(f"  is_copular: {f.is_copular}")
        print(f"  takes_prep: {f.takes_prep}")
        print(f"  most_common roles:")
        for role, n in f.most_common_roles():
            print(f"    {role}: {n}")

    print(f"\n=== اختبار كان ===")
    f = get_frame("كان")
    if f:
        print(f"  is_copular: {f.is_copular}")
        print(f"  role_predicate: {f.roles.get('role_predicate', 0)}")
        print(f"  role_direct_object: {f.roles.get('role_direct_object', 0)}")
