"""speech_frame.py — هَيكَل إِطار الخِطاب (SpeechFrame) لِطَبَقَة M3.

كُلّ مَقطَع قَول يَحمِل:
  • utterance        — النَّصّ المَقول
  • speaker          — القائِل (DiscourseEntity)
  • addressee        — المُخاطَب (DiscourseEntity)
  • speech_type      — direct / indirect / commanded_speech / prayer / vocative / quotation
  • introduced_by    — فِعل القَول أَو السِّياق الَّذي فَتَح الإِطار
  • evidence         — قائِمَة الأَدِلَّة (token + role)
  • confidence       — high / medium / low (أَو رَقم 0-1)
  • parent_frame_id  — الـ frame الحاوي (لِلقَول داخِل قَول)
  • frame_id         — مُعَرِّف فَريد لِهذا الإِطار

كُلّ EntityNode يَحمِل:
  • text  — النَّصّ الظاهِر (موسى، قومه، الملائكة، ...)
  • type  — explicit / implicit / pronoun_resolved / vocative_match / addressee_match
  • person/gender/number — إِن أُمكِن
  • source_of_claim — كَيف عُرِف
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


CONTRACT_NAME = "SpeechFrame:v1"


@dataclass
class DiscourseEntity:
    text: str = ""                  # النَّصّ الظاهِر، مَثَلًا «موسى»
    canonical: str = ""             # الشَّكل القَنونيّ بِلا تَشكيل
    type: str = "explicit"          # explicit / implicit / pronoun_resolved / vocative / addressee
    person: str = ""                # 1 / 2 / 3
    gender: str = ""                # M / F / X
    number: str = ""                # SG / DU / PL
    source_of_claim: str = ""
    contract: str = "DiscourseEntity:v1"

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "canonical": self.canonical,
            "type": self.type,
            "person": self.person,
            "gender": self.gender,
            "number": self.number,
            "source_of_claim": self.source_of_claim,
        }


@dataclass
class Evidence:
    token: str = ""
    role: str = ""    # speech_verb / speaker / addressee / vocative_addressee / imperative_to_plural / ...
    position: int = -1

    def to_dict(self) -> dict:
        return {"token": self.token, "role": self.role, "position": self.position}


@dataclass
class SpeechFrame:
    frame_id: str = ""
    utterance: str = ""
    speaker: Optional[DiscourseEntity] = None
    addressee: Optional[DiscourseEntity] = None
    speech_type: str = "direct"      # direct / indirect / commanded_speech / prayer / vocative / quotation
    introduced_by: str = ""          # نَصّ المُقَدِّم (مَثَلًا «قال موسى لقومه»)
    evidence: list = field(default_factory=list)  # list[Evidence]
    confidence: str = "medium"       # high / medium / low
    parent_frame_id: Optional[str] = None
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "utterance": self.utterance,
            "speaker": self.speaker.to_dict() if self.speaker else None,
            "addressee": self.addressee.to_dict() if self.addressee else None,
            "speech_type": self.speech_type,
            "introduced_by": self.introduced_by,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "parent_frame_id": self.parent_frame_id,
            "contract": self.contract,
        }
