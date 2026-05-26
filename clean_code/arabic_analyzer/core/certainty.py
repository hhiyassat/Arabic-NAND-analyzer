"""certainty.py — قاعِدَة Certificate الصارِمَة.

تَوصيَة المُستَخدِم 2026-05-26 (Phase 2.5):
  Certificate يَنفُذ فَقَط إذا:
    • candidate_classes = 1
    • لا source conflict
    • requires_context = false
    • priority >= 8

  priority وَحدها لا تَطغى عَلى class conflict.
"""
from __future__ import annotations

from typing import Literal

Certainty = Literal["Certificate", "Hypothesis", "Zero"]

CERTIFICATE_PRIORITY_THRESHOLD = 8


def decide_certainty(
    *,
    n_candidates: int,
    has_source_conflict: bool,
    requires_context: bool,
    priority: int,
    has_blockers: bool = False,
) -> Certainty:
    """يُقَرِّر Certificate / Hypothesis / Zero وَفق القَواعِد الصارِمَة.

    Returns:
      Certificate — كُلّ الشُّروط مُسْتَوْفاة
      Hypothesis — هُناك تَرَدُّد لَكِن لَدَينا candidate
      Zero       — لا candidate أَو blocker قاطِع
    """
    if n_candidates == 0:
        return "Zero"
    if has_blockers and priority < CERTIFICATE_PRIORITY_THRESHOLD:
        return "Zero"
    if (n_candidates == 1
        and not has_source_conflict
        and not requires_context
        and priority >= CERTIFICATE_PRIORITY_THRESHOLD):
        return "Certificate"
    return "Hypothesis"


def is_certified(certainty: Certainty) -> bool:
    return certainty == "Certificate"


def is_hypothesis(certainty: Certainty) -> bool:
    return certainty == "Hypothesis"


def is_zero(certainty: Certainty) -> bool:
    return certainty == "Zero"
