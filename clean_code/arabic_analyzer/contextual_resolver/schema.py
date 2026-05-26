"""schema.py — Resolution dataclass لِـ Phase 4 ContextualAmbiguityResolver.

كُلّ resolution تَحتَوي:
  • surface / normalized
  • selected_class (internal linguistic model)
  • selected_function (مِن قائِمَة مَحدودَة)
  • candidates (الفِئات المُتَنافِسَة)
  • context_features (ما لاحَظنا)
  • certainty (Certificate / Hypothesis / Zero)
  • source = "ContextualAmbiguityResolver"
  • masaq_compatible_class (لِلتَّوافُق مَع MASAQ scoring)
  • needs_context / blockers / reason
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# الدَّوال المَسموحَة (مَحصورَة)
ALLOWED_FUNCTIONS = {
    "relative_pronoun",
    "conditional_tool",
    "interrogative_tool",
    "temporal_adverb",
    "locative_adverb",
    "negative_particle",
    "extra_particle",
    "prepositional_phrase_component",
    "unresolved_ambiguous",
}

Certainty = Literal["Certificate", "Hypothesis", "Zero"]


@dataclass
class Resolution:
    """نَتيجَة حَلّ السِّياق لِـ token غامِض."""
    surface: str
    normalized: str
    selected_class: str  # FIIL/HARF/ISM_MABNI/ISM_MAWSOOL/ISM_MUARAB/JAMID
    selected_function: str  # واحِد مِن ALLOWED_FUNCTIONS
    candidates: list[str] = field(default_factory=list)
    context_features: dict = field(default_factory=dict)
    certainty: Certainty = "Hypothesis"
    source: str = "ContextualAmbiguityResolver"
    masaq_compatible_class: str = ""
    needs_context: bool = False
    blockers: list[str] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self):
        if self.selected_function not in ALLOWED_FUNCTIONS:
            raise ValueError(
                f"invalid selected_function: {self.selected_function}. "
                f"Allowed: {sorted(ALLOWED_FUNCTIONS)}"
            )
        if self.certainty not in ("Certificate", "Hypothesis", "Zero"):
            raise ValueError(f"invalid certainty: {self.certainty}")

    def to_dict(self) -> dict:
        """يُحَوِّل لِـ dict تَنسيق العَقد."""
        return {
            "surface": self.surface,
            "normalized": self.normalized,
            "selected_class": self.selected_class,
            "selected_function": self.selected_function,
            "candidates": list(self.candidates),
            "context_features": dict(self.context_features),
            "certainty": self.certainty,
            "source": self.source,
            "masaq_compatible_class": self.masaq_compatible_class,
            "needs_context": self.needs_context,
            "blockers": list(self.blockers),
            "reason": self.reason,
        }


__all__ = ["Resolution", "ALLOWED_FUNCTIONS", "Certainty"]
