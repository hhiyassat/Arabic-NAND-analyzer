"""arabic_analyzer.registry — wrappers لِلـregistry وَ pre-segmentation lookup.

Re-exports فَقَط — لا تَعديل في:
  • candidate ordering
  • certainty logic
  • cross-source conflict
  • shadda parity
  • compound lookup
"""
from .linguistic_source_registry import (
    Entry,
    build_registry,
    resolve,
    resolve_strict,
    resolve_compound,
    conflict_audit,
    save_registry,
)
from .pre_segmentation_lookup import (
    lookup_before_segmentation,
    lookup_compound,
    get_shared_registry,
)

__all__ = [
    "Entry",
    "build_registry", "resolve", "resolve_strict", "resolve_compound",
    "conflict_audit", "save_registry",
    "lookup_before_segmentation", "lookup_compound", "get_shared_registry",
]
