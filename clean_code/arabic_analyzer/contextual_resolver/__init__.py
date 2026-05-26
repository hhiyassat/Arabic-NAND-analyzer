"""arabic_analyzer.contextual_resolver — Phase 4 ContextualAmbiguityResolver.

Standalone resolver لِـ 7 ambiguous surfaces + بِما compound.
لا يُفَعَّل تِلقائيًّا في Layer 1.
"""
from .schema import Resolution, ALLOWED_FUNCTIONS
from .context_features import extract_context_features
from .resolution_rules import get_rule
from .resolver import ContextualAmbiguityResolver, HANDLED_SURFACES_NORMALIZED
from .integration import (
    is_enabled, maybe_apply_resolver,
    reset_integration_stats, get_integration_stats,
)

__all__ = [
    "Resolution",
    "ALLOWED_FUNCTIONS",
    "extract_context_features",
    "get_rule",
    "ContextualAmbiguityResolver",
    "HANDLED_SURFACES_NORMALIZED",
    "is_enabled",
    "maybe_apply_resolver",
    "reset_integration_stats",
    "get_integration_stats",
]
