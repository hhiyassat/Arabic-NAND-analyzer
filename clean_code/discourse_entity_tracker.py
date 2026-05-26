"""discourse_entity_tracker.py — قائِمَة الكِيانات المَفتوحَة عَبر النَّصّ.

يَحفَظ كُلّ كِيان لُغَويّ ذُكِر مُسبَقًا (موسى، قومه، الملائكة، فرعون، …)
مَع سِماتِه (gender, number, person) لِيَتُمَّ حَلّ الضَّمائر إليه.

نَهج بَسيط (v1):
  • نَنشِئ كِيانًا لِكُلّ AALAM (عَلَم) و JAMID و ISM_MUARAB يَظهَر في النَّصّ
  • نَحفَظ آخِر ظُهور لِكُلّ كِيان (لِلتَّفضيل عِندَ التَّعارُض)
  • نَدعَم البَحث بِالـ gender/number/person
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


CONTRACT_NAME = "DiscourseEntityTracker:v1"


@dataclass
class Entity:
    canonical: str = ""        # شَكل قَنونيّ بِلا تَشكيل
    surface: str = ""          # آخِر شَكل ظَهَر بِه
    word_class: str = ""       # AALAM / JAMID / ISM_MUARAB / SINGULAR_TERM
    gender: str = ""           # M / F / X
    number: str = ""           # SG / DU / PL
    last_position: int = -1    # آخِر مَوقِع ظَهَر فيه (token index)
    mentions: int = 1
    is_addressee_candidate: bool = False  # هَل وَرَد في نِداء؟
    is_speaker_candidate: bool = False    # هَل وَرَد كَ فاعِل فِعل قَول؟


class DiscourseEntityTracker:
    """يَحفَظ الكِيانات المَفتوحَة عَبر النَّصّ."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}   # canonical → Entity
        # المُخاطَب الحاليّ (مِن آخِر نِداء)
        self._active_addressee: Optional[str] = None
        # القائِل الحاليّ (مِن آخِر فِعل قَول)
        self._active_speaker: Optional[str] = None

    def _canonical(self, surface: str) -> str:
        diacritics = "ًٌٍَُِّْـٰٓ"
        s = "".join(c for c in surface if c not in diacritics)
        # تَطبيع الأَلِف
        s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        # حَذف ال التَّعريف
        if s.startswith("ال") and len(s) > 3:
            s = s[2:]
        return s

    # heuristics قَديمَة (تُتَجاوَز عَبر GenderDetector / NumberDetector)
    @staticmethod
    def _infer_gender(surface: str) -> str:
        """يُفَوِّض إلى GenderDetector لِلكَشف الكامِل."""
        try:
            from gender_detector import GenderDetector
            if not hasattr(DiscourseEntityTracker, "_gd_instance"):
                DiscourseEntityTracker._gd_instance = GenderDetector()
            r = DiscourseEntityTracker._gd_instance.detect(surface)
            return r.gender if r.gender in ("M", "F") else ""
        except Exception:
            return ""

    @staticmethod
    def _infer_number(surface: str) -> str:
        """يُفَوِّض إلى NumberDetector لِلكَشف الكامِل."""
        try:
            from number_detector import NumberDetector
            if not hasattr(DiscourseEntityTracker, "_nd_instance"):
                DiscourseEntityTracker._nd_instance = NumberDetector()
            r = DiscourseEntityTracker._nd_instance.detect(surface)
            if r.number in ("SG", "DU", "PL"):
                return r.number
            return "SG"  # افتراض
        except Exception:
            return "SG"

    def add_or_update(self, surface: str, *, word_class: str = "",
                      position: int = -1, gender: str = "",
                      number: str = "") -> Entity:
        canon = self._canonical(surface)
        if not canon:
            return Entity()
        # heuristic لِلجِنس والعَدد إِن لَم يُمَرَّرا
        if not gender:
            gender = self._infer_gender(surface)
        if not number:
            number = self._infer_number(surface)
        if canon in self._entities:
            e = self._entities[canon]
            e.surface = surface
            e.last_position = position
            e.mentions += 1
            if gender and not e.gender:
                e.gender = gender
            if number and not e.number:
                e.number = number
        else:
            e = Entity(
                canonical=canon,
                surface=surface,
                word_class=word_class,
                gender=gender,
                number=number,
                last_position=position,
                mentions=1,
            )
            self._entities[canon] = e
        return e

    def mark_as_addressee(self, surface: str):
        canon = self._canonical(surface)
        if canon in self._entities:
            self._entities[canon].is_addressee_candidate = True
        self._active_addressee = canon

    def mark_as_speaker(self, surface: str):
        canon = self._canonical(surface)
        if canon in self._entities:
            self._entities[canon].is_speaker_candidate = True
        self._active_speaker = canon

    @property
    def active_addressee(self) -> Optional[Entity]:
        if self._active_addressee and self._active_addressee in self._entities:
            return self._entities[self._active_addressee]
        return None

    @property
    def active_speaker(self) -> Optional[Entity]:
        if self._active_speaker and self._active_speaker in self._entities:
            return self._entities[self._active_speaker]
        return None

    def find_compatible(self, *, gender: str, number: str, person: str,
                        before_position: int = 99999,
                        strict_gender: bool = True) -> Optional[Entity]:
        """يَبحَث عَن أَحدَث كِيان مُتَوافِق مَع الجِنس/العَدد/الشَّخص قَبل
        المَوقِع المُحَدَّد.

        strict_gender=True (افتراضيّ): لَو الضَّمير مُؤَنَّث (F) أَو مُذَكَّر (M)،
        نَطلُب أَنّ الكِيان يَحمِل نَفس الجِنس صَراحَة. لا نَقبَل entities بِجِنس
        غَير مَعروف (X/"") عِندَ مُطابَقَة مُؤَنَّث/مُذَكَّر صَريح.
        """
        candidates = []
        for e in self._entities.values():
            if e.last_position >= before_position:
                continue
            # تَطابُق جِنس صارِم
            if gender and gender != "X":
                if strict_gender:
                    if e.gender != gender:
                        continue
                else:
                    if e.gender and e.gender != "X" and gender != e.gender:
                        continue
            # تَطابُق عَدد
            if number and e.number and number != "X" and e.number != "X" and number != e.number:
                continue
            candidates.append(e)
        if not candidates:
            return None
        # رَتِّب بِالأَقرَب
        candidates.sort(key=lambda x: -x.last_position)
        return candidates[0]

    def find_all_compatible(self, *, gender: str, number: str, person: str,
                            before_position: int = 99999,
                            strict_gender: bool = True) -> list[Entity]:
        """يُرجِع كُلّ الكِيانات المُتَوافِقَة، مُرَتَّبَة بِالأَحدَث."""
        candidates = []
        for e in self._entities.values():
            if e.last_position >= before_position:
                continue
            if gender and gender != "X":
                if strict_gender:
                    if e.gender != gender:
                        continue
                else:
                    if e.gender and e.gender != "X" and gender != e.gender:
                        continue
            if number and e.number and number != "X" and e.number != "X" and number != e.number:
                continue
            candidates.append(e)
        candidates.sort(key=lambda x: -x.last_position)
        return candidates

    def all_entities(self) -> list[Entity]:
        return list(self._entities.values())

    def to_dict(self) -> dict:
        return {
            "contract": CONTRACT_NAME,
            "active_speaker": self._active_speaker,
            "active_addressee": self._active_addressee,
            "entities": {
                k: {
                    "canonical": e.canonical,
                    "surface": e.surface,
                    "word_class": e.word_class,
                    "gender": e.gender,
                    "number": e.number,
                    "mentions": e.mentions,
                    "is_addressee_candidate": e.is_addressee_candidate,
                    "is_speaker_candidate": e.is_speaker_candidate,
                }
                for k, e in self._entities.items()
            },
        }
