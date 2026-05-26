"""event_schema.py — Phase D: Event + Transformation schemas.

MC-COMPLIANT:
  • كُلّ Event يَحوي ProofObject ضِمنيّ (kind + contract + source)
  • Transformation يَرِث Event (لَيس بَديلًا عَنه)
  • الأَفعال التَّحَوُّليَّة مُحَمَّلَة مِن CSV (transformation_verbs.csv)

يُرجَع إِليه:
  • Distinction_Event_vs_Transformation.md (الـ gate الدُّستوريّ)
  • 15_Executive_Roadmap.md §4 (Phase D)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

EventKind = Literal["Certificate", "Hypothesis", "Zero"]


@dataclass
class Event:
    """حَدَث — واقِعَة في زَمَن، حَتَّى لَو لا تَغَيُّر حالَة."""

    event_id: str                                  # e.g. "ev0"
    type: str                                       # نَوع الحَدَث (lemma الفِعل)
    verb_surface: str                               # الفِعل كَما وَرَدَ (مُشَكَّل)
    verb_position: int                              # مَوضِع الفِعل في الجُملَة
    agent: Optional[str] = None                    # الفاعِل (entity_id)
    patient: Optional[str] = None                  # المَفعول
    patient2: Optional[str] = None                 # المَفعول الثَّاني
    instrument: Optional[str] = None               # الأَداة (بِـ)
    time: Optional[str] = None                     # الزَّمَن (ظَرف زَمان)
    location: Optional[str] = None                 # المَكان (في، عِندَ، ظَرف مَكان)
    manner: Optional[str] = None                   # الكَيفيَّة (حال)
    result: Optional[str] = None                   # النَّتيجَة
    tense: str = "unknown"                          # past / present / future / command
    time_value: Optional[str] = None               # قِيمَة الزَّمَن المُحَدَّدَة (yesterday، now...)
    frame_observed: list = field(default_factory=list)  # الأَدوار المُشاهَدَة مِن verb_frames
    # ─── MC metadata ────────────────────────────
    # NOTE MC FIX 2026-05-24 (per user critique): default Hypothesis.
    # An Event becomes Certificate ONLY if every relation feeding it
    # (agent_of, patient_of, in_location...) is a Certificate AND
    # the underlying graph has no contradictions. Default Certificate
    # was over-trusting and propagated noisy relations as if proven.
    kind: EventKind = "Hypothesis"
    contract: str = "EventSchema:v1"
    source_of_claim: str = ""
    blockers: list = field(default_factory=list)

    @property
    def is_certificate(self) -> bool:
        return self.kind == "Certificate"

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(self.kind, "·")
        parts = [f"{sym} Event[{self.type}]"]
        if self.agent: parts.append(f"agent={self.agent}")
        if self.patient: parts.append(f"patient={self.patient}")
        if self.location: parts.append(f"location={self.location}")
        return " | ".join(parts)


@dataclass
class Transformation(Event):
    """تَحَوُّل = Event + StateChange.

    يَرِث Event وَ يُضيف:
      • subject — الكِيان المُتَحَوِّل
      • state_before / state_after — الحالَتان
      • transformation_kind — نَوع التَّحَوُّل (general، explicit، life_to_death...)
    """

    subject: Optional[str] = None
    state_before: str = "—"
    state_after: str = "—"
    transformation_kind: str = "general"

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(self.kind, "·")
        sb = self.state_before
        sa = self.state_after
        return f"{sym} Transformation[{self.type}] {self.subject}: {sb} → {sa}"


@dataclass
class EventGraph:
    """مَجموع الأَحداث في جُملَة/نَصّ."""

    source_text: str
    events: list[Event] = field(default_factory=list)
    contract: str = "EventGraph:v1"

    def add_event(self, e: Event):
        self.events.append(e)

    @property
    def transformations(self) -> list[Transformation]:
        return [e for e in self.events if isinstance(e, Transformation)]

    @property
    def pure_events(self) -> list[Event]:
        return [e for e in self.events if not isinstance(e, Transformation)]

    def __str__(self) -> str:
        out = [f"EventGraph({len(self.events)} events، {len(self.transformations)} transformations)"]
        for e in self.events:
            out.append(f"  {e}")
        return "\n".join(out)
