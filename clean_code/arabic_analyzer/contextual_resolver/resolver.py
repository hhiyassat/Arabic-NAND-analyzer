"""resolver.py — ContextualAmbiguityResolver (Phase 4 facade).

API:
  resolver = ContextualAmbiguityResolver()
  if resolver.can_resolve(surface):
      res = resolver.resolve(surface, prev_tokens=[...], next_tokens=[...])
      print(res.selected_function, res.certainty)

INTEGRATION: لا يُفَعَّل تِلقائيًّا في Layer 1.
لِلتَّكامُل المُتَحَكَّم بِه، اضبُط:
  WordClassClassifier(use_phase4_resolver=True)
"""
from __future__ import annotations

from typing import Optional

from .context_features import extract_context_features
from .resolution_rules import get_rule
from .schema import Resolution

# الـsurfaces المَدعومَة (مَحصورَة بِالـ7 + بِما)
HANDLED_SURFACES_NORMALIZED = {
    "من", "ما", "أي", "متى", "أين", "أنى", "حيث", "بما",
}


class ContextualAmbiguityResolver:
    """Resolver لِـ 7 ambiguous surfaces + بِما compound."""

    def __init__(self):
        self._stats: dict = {
            "total_calls": 0,
            "certificate_count": 0,
            "hypothesis_count": 0,
            "zero_count": 0,
            "unresolved_ambiguous_count": 0,
            "by_surface": {},
            "by_function": {},
        }

    def can_resolve(self, surface: str) -> bool:
        """True إذا الـsurface مَدعوم."""
        return get_rule(surface) is not None

    def resolve(
        self,
        surface: str,
        prev_tokens: Optional[list[str]] = None,
        next_tokens: Optional[list[str]] = None,
    ) -> Resolution:
        """يَحُلّ surface غامِض في السِّياق."""
        rule = get_rule(surface)
        if rule is None:
            raise ValueError(f"surface not handled: {surface}")
        ctx = extract_context_features(surface, prev_tokens, next_tokens)
        res = rule(surface, ctx)
        self._record(res)
        return res

    def reset_stats(self) -> None:
        self.__init__()

    def get_stats(self) -> dict:
        return dict(self._stats)

    def _record(self, res: Resolution) -> None:
        self._stats["total_calls"] += 1
        if res.certainty == "Certificate":
            self._stats["certificate_count"] += 1
        elif res.certainty == "Hypothesis":
            self._stats["hypothesis_count"] += 1
        else:
            self._stats["zero_count"] += 1
        if res.selected_function == "unresolved_ambiguous":
            self._stats["unresolved_ambiguous_count"] += 1
        bs = self._stats["by_surface"].setdefault(res.normalized, 0)
        self._stats["by_surface"][res.normalized] = bs + 1
        bf = self._stats["by_function"].setdefault(res.selected_function, 0)
        self._stats["by_function"][res.selected_function] = bf + 1


__all__ = ["ContextualAmbiguityResolver", "HANDLED_SURFACES_NORMALIZED"]
