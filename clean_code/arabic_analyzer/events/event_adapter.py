"""event_adapter.py — يَلُفّ event_schema القَديم.

Step E (observe): تَحويل records بِين legacy وَ standard schema.
لا تَغيير في output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StandardEvent:
    """تَنسيق مُوَحَّد لِلـEvent (مُتَوافِق مَع event_schema القَديم)."""
    lemma: str                       # جذر/lemma الفِعل
    surface: str = ""                # surface form
    tense: str = "unknown"           # past / present / command / future
    agent: Optional[str] = None
    patient: Optional[str] = None
    patient2: Optional[str] = None
    instrument: Optional[str] = None
    location: Optional[str] = None
    time: Optional[str] = None
    manner: Optional[str] = None
    kind: str = "Event"              # Event / Transformation
    role_kind: str = "Hypothesis"
    source_of_claim: str = ""
    metadata: dict = field(default_factory=dict)


def event_to_legacy(e: StandardEvent) -> dict:
    """تَحويل StandardEvent إلى dict تَنسيق Layer 4."""
    return {
        "lemma": e.lemma,
        "surface": e.surface,
        "tense": e.tense,
        "agent": e.agent, "patient": e.patient, "patient2": e.patient2,
        "instrument": e.instrument, "location": e.location,
        "time": e.time, "manner": e.manner,
        "kind": e.kind,
        "role_kind": e.role_kind,
        "source_of_claim": e.source_of_claim,
        **e.metadata,
    }


def event_from_legacy(d: dict | Any) -> StandardEvent:
    """يُنشِئ StandardEvent مِن dict أَو Event object."""
    if hasattr(d, "lemma"):
        return StandardEvent(
            lemma=getattr(d, "lemma", ""),
            surface=getattr(d, "surface", ""),
            tense=getattr(d, "tense", "unknown"),
            agent=getattr(d, "agent", None),
            patient=getattr(d, "patient", None),
            patient2=getattr(d, "patient2", None),
            instrument=getattr(d, "instrument", None),
            location=getattr(d, "location", None),
            time=getattr(d, "time", None),
            manner=getattr(d, "manner", None),
            kind=getattr(d, "kind", "Event"),
            role_kind=getattr(d, "role_kind", "Hypothesis"),
            source_of_claim=getattr(d, "source_of_claim", ""),
        )
    return StandardEvent(
        lemma=d.get("lemma", ""),
        surface=d.get("surface", ""),
        tense=d.get("tense", "unknown"),
        agent=d.get("agent"), patient=d.get("patient"),
        patient2=d.get("patient2"),
        instrument=d.get("instrument"), location=d.get("location"),
        time=d.get("time"), manner=d.get("manner"),
        kind=d.get("kind", "Event"),
        role_kind=d.get("role_kind", "Hypothesis"),
        source_of_claim=d.get("source_of_claim", ""),
        metadata={k: v for k, v in d.items()
                 if k not in ("lemma","surface","tense","agent","patient",
                              "patient2","instrument","location","time",
                              "manner","kind","role_kind","source_of_claim")},
    )


__all__ = ["StandardEvent", "event_to_legacy", "event_from_legacy"]
