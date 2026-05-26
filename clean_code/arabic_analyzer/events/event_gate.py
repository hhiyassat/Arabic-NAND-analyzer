"""event_gate.py — EventGate (observe-only في Step E).

تَوصيَة المُستَخدِم 2026-05-26 (Step E):
  observe mode — لا يَحجِب. يُسَجِّل ما كان سَيُحجَب.

  Event يَتَطَلَّب (بَعد التَّفعيل):
    • verb_decision is_certified_fiil
    • segmentation_status == Certificate
    • لا ambiguous Hypothesis
    • لا conflicting candidates
    • لا blockers قاطِعَة
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..core import Decision
from ..segmentation import SegmentationDecision

EnforcementMode = Literal["observe", "enforce"]


# Observe-only counters
_AUDIT_COUNTERS: dict[str, int] = {
    "would_block_event_count": 0,
    "fragment_event_candidates": 0,
    "hypothesis_event_candidates": 0,
    "ambiguous_event_candidates": 0,
    "conflicting_candidate_event_count": 0,
    "non_certified_fiil_event_count": 0,
    "segmentation_uncertified_event_count": 0,
    "total_events_evaluated": 0,
    "total_events_passed_in_observe": 0,
}


def reset_audit() -> None:
    for k in _AUDIT_COUNTERS:
        _AUDIT_COUNTERS[k] = 0


def get_audit() -> dict:
    return dict(_AUDIT_COUNTERS)


@dataclass
class GateVerdict:
    allowed: bool
    would_block: bool = False
    reasons: list[str] = field(default_factory=list)
    enforcement_mode: EnforcementMode = "observe"


def can_emit_event(
    *,
    verb_decision: Decision | None = None,
    segmentation_decision: SegmentationDecision | None = None,
    enforcement_mode: EnforcementMode = "observe",
) -> GateVerdict:
    """يَفحَص هَل تَستَحِقّ الـEvent الإِصدار.

    observe mode: دائِمًا يُرجِع allowed=True مَع تَسجيل ما كان سَيُحجَب.
    """
    _AUDIT_COUNTERS["total_events_evaluated"] += 1
    reasons: list[str] = []

    if verb_decision is None:
        reasons.append("verb_decision_missing")
    else:
        # not certified FIIL
        if not verb_decision.is_certified_fiil():
            reasons.append(f"not_certified_fiil:{verb_decision.word_class}/{verb_decision.certainty}")
            _AUDIT_COUNTERS["non_certified_fiil_event_count"] += 1
        # ambiguous
        if verb_decision.is_ambiguous() and not verb_decision.is_certified():
            reasons.append("verb_ambiguous_uncertified")
            _AUDIT_COUNTERS["ambiguous_event_candidates"] += 1
        # hypothesis
        if verb_decision.is_hypothesis() and verb_decision.needs_context:
            reasons.append("verb_hypothesis_needs_context")
            _AUDIT_COUNTERS["hypothesis_event_candidates"] += 1
        # conflicting candidate classes
        if "conflicting_candidates" in verb_decision.blockers:
            reasons.append("verb_conflicting_candidates")
            _AUDIT_COUNTERS["conflicting_candidate_event_count"] += 1
        # fragment
        if verb_decision.segmentation_status == "Zero":
            reasons.append("verb_is_fragment")
            _AUDIT_COUNTERS["fragment_event_candidates"] += 1

    # Segmentation
    if segmentation_decision and segmentation_decision.segmentation_status != "Certificate":
        reasons.append(f"segmentation_status:{segmentation_decision.segmentation_status}")
        _AUDIT_COUNTERS["segmentation_uncertified_event_count"] += 1

    would_block = bool(reasons)
    if would_block:
        _AUDIT_COUNTERS["would_block_event_count"] += 1
    else:
        _AUDIT_COUNTERS["total_events_passed_in_observe"] += 1

    if enforcement_mode == "enforce":
        return GateVerdict(allowed=not would_block, would_block=would_block,
                          reasons=reasons, enforcement_mode="enforce")
    return GateVerdict(allowed=True, would_block=would_block,
                      reasons=reasons, enforcement_mode="observe")


def explain_event_gate(
    *, verb_decision: Decision | None = None,
    segmentation_decision: SegmentationDecision | None = None,
) -> str:
    v = can_emit_event(
        verb_decision=verb_decision,
        segmentation_decision=segmentation_decision,
        enforcement_mode="observe",
    )
    if not v.reasons:
        return "PASS"
    return f"WOULD_BLOCK: {'; '.join(v.reasons)}"


__all__ = [
    "GateVerdict", "EnforcementMode",
    "can_emit_event", "explain_event_gate",
    "reset_audit", "get_audit",
]
