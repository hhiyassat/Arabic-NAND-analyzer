"""arabic_analyzer.classification — wrappers لِلتَّصنيف.

Step C scope (re-export فَقَط):
  candidate_resolver  — registry-based candidate generation
  fallback_classifier — heuristic gates (master_token + Layer 1)
  word_class_decision_kernel — top-level facade
"""
from .candidate_resolver import (
    resolve_candidates,
    classify_via_registry,
    classify_via_compound,
)
from .fallback_classifier import (
    classify_via_masaq,
    classify_via_heuristics,
)
from .word_class_decision_kernel import classify, classify_legacy_dict

__all__ = [
    "resolve_candidates", "classify_via_registry", "classify_via_compound",
    "classify_via_masaq", "classify_via_heuristics",
    "classify", "classify_legacy_dict",
]
