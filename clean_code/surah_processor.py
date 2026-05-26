"""surah_processor.py — يُعالِج سُورَة كامِلَة مَع تَتَبُّع الخِطاب عَبر الآيات.

PromiseBox: المُخاطَب في «يا أَيُّها الَّذينَ آمَنوا» في آية 1 يَستَمِرّ في
آية 2، 3، 4 ... إلى أَن يَتَغَيَّر بِنِداء جَديد أَو «قال X لـ Y».

الِاستخدام:
    sp = SurahProcessor()
    for verse_ref, verse_text in verses_in_surah:
        result = sp.process_verse(verse_text, ref=verse_ref)
        # result يَحوي SpeechFrames + ResolvedReferences مَع context تَراكُميّ
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from speech_frame_extractor import SpeechFrameExtractor
from anaphora_resolver_v2 import AnaphoraResolverV2
from discourse_entity_tracker import DiscourseEntityTracker
from speech_stack import SpeechStack
from speech_frame import SpeechFrame, DiscourseEntity
from i3rab_engine.engine import I3rabEngine


CONTRACT_NAME = "SurahProcessor:v1"


class SurahProcessor:
    """مُعالِج سُورَة كامِلَة مَع state تَراكُميّ."""

    def __init__(self):
        self._extractor = SpeechFrameExtractor()
        self._resolver = AnaphoraResolverV2()
        self._engine = I3rabEngine()
        # state تَراكُميّ عَبر الآيات
        self._tracker = DiscourseEntityTracker()
        self._stack = SpeechStack()
        self._all_frames: list[SpeechFrame] = []
        # المُخاطَب الحاليّ (يَستَمِرّ عَبر الآيات حَتّى تَغَيُّر صَريح)
        self._active_addressee: Optional[DiscourseEntity] = None
        self._active_speaker: Optional[DiscourseEntity] = None
        self._verse_count = 0

    def reset(self):
        """يَبدَأ سُورَة جَديدَة (يَمسَح كُلّ الـ state)."""
        self._tracker = DiscourseEntityTracker()
        self._stack = SpeechStack()
        self._all_frames = []
        self._active_addressee = None
        self._active_speaker = None
        self._verse_count = 0

    def process_verse(self, verse_text: str, ref: str = "") -> dict:
        """يُعالِج آية واحِدَة مَع الـ state التَّراكُميّ مِن الآيات السابِقَة."""
        self._verse_count += 1

        # i3rab للآية
        sent = self._engine.analyze_sentence(verse_text)

        # SpeechFrames لِهذه الآية (مَع word_class)
        result = self._extractor.extract(verse_text, i3rab_tokens=sent.tokens)
        verse_frames = result["frames"]
        verse_tracker_local = result["tracker"]

        # دَمج tracker الآية مَع الـ tracker العامّ (التَّراكُميّ)
        for entity in verse_tracker_local.all_entities():
            # نَنقُل لِلتَّراكُميّ
            self._tracker.add_or_update(
                entity.surface,
                word_class=entity.word_class,
                position=self._verse_count * 1000 + entity.last_position,
                gender=entity.gender,
                number=entity.number,
            )
            if entity.is_addressee_candidate:
                self._tracker.mark_as_addressee(entity.surface)
            if entity.is_speaker_candidate:
                self._tracker.mark_as_speaker(entity.surface)

        # تَحديث المُخاطَب الحاليّ
        # إِن كانَ في هذه الآية نِداء أَو frame مَع addressee صَريح، نُحَدِّث
        for f in verse_frames:
            if f.addressee and f.addressee.type in ("addressee_match", "vocative_match"):
                self._active_addressee = f.addressee
            if f.speaker and f.speaker.type == "explicit":
                self._active_speaker = f.speaker
            # نَضيف لِـ stack
            self._all_frames.append(f)

        # لَو لَم يَكُن في الآية أَيّ frame جَديد لَكِنّ لَدَينا active_addressee،
        # نَفتَح frame ضِمنيّ يَستَخدِم الـ active_addressee
        if not verse_frames and self._active_addressee:
            implicit_frame = SpeechFrame(
                speech_type="continuation",
                introduced_by=f"(مُتَّصِل بِالنِّداء السابِق: {self._active_addressee.text})",
                confidence="medium",
            )
            implicit_frame.addressee = self._active_addressee
            implicit_frame.speaker = self._active_speaker
            verse_frames = [implicit_frame]

        # حَلّ الضَّمائر بِاستخدام الـ frames (وَ-الـ active addressee إن وُجِد)
        # نَستَخدِم الـ tracker التَّراكُميّ لِلغائِب
        # نَستَخدِم الـ active_addressee لِلمُخاطَب (يَتَجاوَز هذه الآية)
        effective_frames = list(verse_frames)
        if self._active_addressee and not any(f.addressee for f in effective_frames):
            # أَضِف pseudo-frame بِالمُخاطَب الحاليّ
            pseudo = SpeechFrame(
                speech_type="continuation_pseudo",
                introduced_by=f"(active_addressee from prior verse: {self._active_addressee.text})",
                confidence="low",
            )
            pseudo.addressee = self._active_addressee
            pseudo.speaker = self._active_speaker
            effective_frames.append(pseudo)

        v2_refs = self._resolver.resolve(
            sent.tokens,
            frames=effective_frames,
            tracker=self._tracker,
        )

        return {
            "ref": ref,
            "verse_count": self._verse_count,
            "frames": verse_frames,
            "active_addressee": self._active_addressee.to_dict() if self._active_addressee else None,
            "active_speaker": self._active_speaker.to_dict() if self._active_speaker else None,
            "pronoun_refs": [r.to_dict() for r in v2_refs],
            "contract": CONTRACT_NAME,
        }


# ============================================================================
# Self-test على سُورة الإِخلاص + مَطلَع البَقَرَة
# ============================================================================

if __name__ == "__main__":
    # مَحاكاة: «يا أَيُّها الَّذين آمَنوا» في 2:104، ثُمَّ آيات لاحِقَة
    # نَتَوَقَّع: المُخاطَب يَستَمِرّ
    verses = [
        ("test:1", "يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوا لَا تَقُولُوا رَٰعِنَا"),
        ("test:2", "وَقُولُوا ٱنظُرْنَا وَٱسْمَعُوا"),  # كم في ٱنظُرْنَا، اسمَعوا
        ("test:3", "وَلِلْكَٰفِرِينَ عَذَابٌ أَلِيمٌ"),
    ]
    sp = SurahProcessor()
    for ref, t in verses:
        r = sp.process_verse(t, ref=ref)
        print(f"\n=== {ref}: {t}")
        if r["active_addressee"]:
            print(f"  المُخاطَب الحاليّ: {r['active_addressee'].get('text', '')}")
        for f in r["frames"]:
            print(f"  frame [{f.speech_type}]: قائِل={f.speaker.text if f.speaker else '—'}  مُخاطَب={f.addressee.text if f.addressee else '—'}")
        for ref_d in r["pronoun_refs"]:
            print(f"    ⤺ «{ref_d['clitic']}» في «{ref_d['host_token']}» → «{ref_d['referent_text']}»  src={ref_d['referent_source']}")
