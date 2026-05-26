"""relation_gate.py — RelationGate (observe-only في Step E).

تَوصيَة المُستَخدِم 2026-05-26 (Step E):
  observe mode — لا يَحجِب شَيئًا. يُسَجِّل ما كان سَيُحجَب لاحِقًا.

  enforcement = "observe" : دائِمًا يُرجِع allowed=True
                            + يُحَدِّث counters
  enforcement = "enforce" : يَفرِض الحَجب فِعليًّا (مُؤَجَّل لِما بَعد Step E)

البِنيَة:
  GateVerdict — {allowed, would_block, reasons}
  RelationGate — يَفحَص الـpair (source, target, relation_type)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from ..core import Decision
from ..segmentation import SegmentationDecision

EnforcementMode = Literal["observe", "enforce"]


# ─────────────────────────────────────────────────────────────
# Observe-only counters
# ─────────────────────────────────────────────────────────────

_AUDIT_COUNTERS: dict[str, int] = {
    "would_block_relation_count": 0,
    "fragment_relation_candidates": 0,
    "hypothesis_relation_candidates": 0,
    "ambiguous_relation_candidates": 0,
    "conflicting_candidate_relation_count": 0,
    "segmentation_uncertified_relation_count": 0,
    "total_relations_evaluated": 0,
    "total_relations_passed_in_observe": 0,
}


def reset_audit() -> None:
    for k in _AUDIT_COUNTERS:
        _AUDIT_COUNTERS[k] = 0


def get_audit() -> dict:
    return dict(_AUDIT_COUNTERS)


@dataclass
class GateVerdict:
    """نَتيجَة الـgate.

    في observe mode:
      allowed دائِمًا True.
      would_block يُحتسَب لِلتَّقرير.
      reasons يَحوي ما كان سَيُسَبِّب الحَجب.
    """
    allowed: bool
    would_block: bool = False
    reasons: list[str] = field(default_factory=list)
    enforcement_mode: EnforcementMode = "observe"


# ─────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────

def can_emit_relation(
    *,
    source_decision: Decision | None = None,
    target_decision: Decision | None = None,
    relation_type: str = "",
    segmentation_decision: SegmentationDecision | None = None,
    enforcement_mode: EnforcementMode = "observe",
) -> GateVerdict:
    """يَفحَص هَل تَستَحِقّ الـrelation الإِصدار.

    في observe mode: يَدرُس لَكِن لا يَمنَع.
    """
    _AUDIT_COUNTERS["total_relations_evaluated"] += 1
    reasons: list[str] = []

    # Fragment check
    if source_decision and source_decision.segmentation_status == "Zero":
        reasons.append("source_token_is_fragment")
        _AUDIT_COUNTERS["fragment_relation_candidates"] += 1
    if target_decision and target_decision.segmentation_status == "Zero":
        reasons.append("target_token_is_fragment")
        _AUDIT_COUNTERS["fragment_relation_candidates"] += 1

    # Segmentation not certified
    if segmentation_decision and segmentation_decision.segmentation_status != "Certificate":
        reasons.append(f"segmentation_status:{segmentation_decision.segmentation_status}")
        _AUDIT_COUNTERS["segmentation_uncertified_relation_count"] += 1

    # Hypothesis-level candidates (relations need at least one resolved side)
    if source_decision and source_decision.is_hypothesis() and source_decision.needs_context:
        reasons.append("source_hypothesis_needs_context")
        _AUDIT_COUNTERS["hypothesis_relation_candidates"] += 1
    if target_decision and target_decision.is_hypothesis() and target_decision.needs_context:
        reasons.append("target_hypothesis_needs_context")
        _AUDIT_COUNTERS["hypothesis_relation_candidates"] += 1

    # Ambiguous (multiple candidates)
    if source_decision and source_decision.is_ambiguous() and not source_decision.is_certified():
        reasons.append("source_ambiguous_uncertified")
        _AUDIT_COUNTERS["ambiguous_relation_candidates"] += 1

    # Conflicting candidate classes blocker
    if source_decision and "conflicting_candidates" in source_decision.blockers:
        reasons.append("source_conflicting_candidates")
        _AUDIT_COUNTERS["conflicting_candidate_relation_count"] += 1
    if target_decision and "conflicting_candidates" in target_decision.blockers:
        reasons.append("target_conflicting_candidates")
        _AUDIT_COUNTERS["conflicting_candidate_relation_count"] += 1

    would_block = bool(reasons)
    if would_block:
        _AUDIT_COUNTERS["would_block_relation_count"] += 1
    else:
        _AUDIT_COUNTERS["total_relations_passed_in_observe"] += 1

    if enforcement_mode == "enforce":
        return GateVerdict(allowed=not would_block, would_block=would_block,
                          reasons=reasons, enforcement_mode="enforce")
    # observe: دائِمًا allowed
    return GateVerdict(allowed=True, would_block=would_block,
                      reasons=reasons, enforcement_mode="observe")


def explain_relation_gate(
    *, source_decision: Decision | None = None,
    target_decision: Decision | None = None,
    relation_type: str = "",
    segmentation_decision: SegmentationDecision | None = None,
) -> str:
    """يُرجِع شَرحًا نَصيًّا لِقرار الـgate."""
    v = can_emit_relation(
        source_decision=source_decision,
        target_decision=target_decision,
        relation_type=relation_type,
        segmentation_decision=segmentation_decision,
        enforcement_mode="observe",
    )
    if not v.reasons:
        return f"PASS ({relation_type})"
    return f"WOULD_BLOCK ({relation_type}): {'; '.join(v.reasons)}"


__all__ = [
    "GateVerdict",
    "EnforcementMode",
    "can_emit_relation",
    "explain_relation_gate",
    "reset_audit",
    "get_audit",
]
