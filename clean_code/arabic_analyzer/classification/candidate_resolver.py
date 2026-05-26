"""candidate_resolver.py — wrapper حَول registry resolution.

تَوصيَة المُستَخدِم 2026-05-26 (Step C):
  classification module يَستَخدِم legacy implementation. لا إِعادَة كَتابَة.

API:
  resolve_candidates(token) → list[Candidate]
    يُرجِع المُرَشَّحات مَع features مِن registry.

  classify_via_registry(token) → Decision | None
    Decision كامِل إِن وُجِد في registry. None لَو لَم يوجَد.

كُلّ الدَّوال تُحَوِّل output الـlegacy إلى Decision/Candidate models،
بِدون تَغيير في:
  • candidate ordering
  • certainty logic
  • cross-source conflict
"""
from __future__ import annotations

from ..core import Candidate, Decision
from ..registry import lookup_before_segmentation, lookup_compound


def resolve_candidates(token: str) -> list[Candidate]:
    """يَستَدعي registry.resolve_strict وَ يُرجِع المُرَشَّحات."""
    r = lookup_before_segmentation(token)
    if not r.get("found"):
        return []
    return [
        Candidate(word_class=c, confidence=1.0, source_ids=tuple([r.get("source","")]))
        for c in (r.get("candidates") or [])
    ]


def classify_via_registry(token: str) -> Decision | None:
    """يُرجِع Decision لَو wujida في registry، أَو None.

    لا يَستَخدِم heuristics — هَذه وَظيفَة fallback_classifier.
    """
    r = lookup_before_segmentation(token)
    if not r.get("found"):
        return None
    cands = r.get("candidates") or []
    top = cands[0] if cands else "UNKNOWN"
    return Decision(
        surface=token,
        word_class=top,
        candidates=list(cands),
        certainty=r.get("certainty", "Zero"),
        source=r.get("source", ""),
        source_ids=[r.get("source", "")],
        proof_kind=r.get("certainty", "Zero"),
        needs_context=r.get("requires_context", False),
        blockers=list(r.get("blockers") or []),
    )


def classify_via_compound(token: str) -> Decision | None:
    """compound lookup (لِمَاذَا = لِ + ما + ذَا)."""
    comp = lookup_compound(token)
    if not comp:
        return None
    head = comp["head"]
    return Decision(
        surface=token,
        word_class=head.candidate_classes[0] if head.candidate_classes else "UNKNOWN",
        candidates=list(head.candidate_classes),
        certainty="Hypothesis",  # compound = أَخفّ ثِقَة
        source=f"compound:{'+'.join(s['surface'] for s in comp['segments'])}",
        needs_context=head.requires_context,
        blockers=["compound_token"] + list(head.blockers),
    )


__all__ = ["resolve_candidates", "classify_via_registry", "classify_via_compound"]
