"""word_class_decision_kernel.py — orchestrator أَعلى.

تَوصيَة المُستَخدِم 2026-05-26 (Step C):
  وَظيفَة هَذا الـmodule:
    يُمَرِّر الـtoken إِلى legacy Layer 1 (الَّذي يَحوي السِّلسِلَة الكامِلَة)
    وَ يُحَوِّل النَّتيجَة إِلى Decision.

  لا يُكَرِّر السِّلسِلَة. لا يُعيد ترتيبها. لا يُغَيِّر certainty.

  Layer 1 الحاليّ هُو DecisionKernel الفِعليّ. هَذا فَقَط facade.
"""
from __future__ import annotations

from ..core import Decision
from .fallback_classifier import classify_via_heuristics


def classify(token: str) -> Decision:
    """Top-level classification entry point.

    يُرجِع Decision مَع كُلّ الحُقول (word_class, candidates, certainty, source…).

    حاليًّا — يَستَدعي legacy Layer 1 كَما هُوَ. الـrefactor الفِعليّ
    لِلسِّلسِلَة سَيَحدُث في Phase 4+ بَعد اعتِماد هَذا الـrefactor.
    """
    return classify_via_heuristics(token)


def classify_legacy_dict(token: str) -> dict:
    """نَفس الـAPI القَديم — يُرجِع dict (لِلكود الَّذي يَتَوَقَّعها)."""
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    return clf.classify(token)


__all__ = ["classify", "classify_legacy_dict"]
