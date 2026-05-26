"""arabic_analyzer.core — data models لِلـDecision Kernel.

Exposes:
  Decision           — token classification result (standard schema)
  Candidate          — single word_class candidate with features
  Evidence           — supporting/blocking evidence record
  SourceRecord       — provenance (MC trace)
  Certainty, decide_certainty
"""
from .certainty import (
    Certainty,
    CERTIFICATE_PRIORITY_THRESHOLD,
    decide_certainty,
    is_certified,
    is_hypothesis,
    is_zero,
)
from .decision import Candidate, Decision
from .evidence import Evidence
from .sources import SourceRecord

__all__ = [
    "Decision", "Candidate", "Evidence", "SourceRecord",
    "Certainty", "CERTIFICATE_PRIORITY_THRESHOLD",
    "decide_certainty", "is_certified", "is_hypothesis", "is_zero",
]
