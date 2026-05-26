"""root_pipeline_types.py — shared dataclasses.

Extracted to break circular imports between root_pipeline (which uses
ProofObject) and proof_object (which extends WordAnalysis).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class WordAnalysis:
    """Final analysis result for a word (legacy schema, preserved).

    New code should prefer the richer ``ProofObject`` (subclass) which
    adds ``kind``, ``contract``, ``blockers``, ``alternatives``.
    """
    word: str = ""
    word_plain: str = ""
    status: Literal[
        "open_class", "closed_class", "jamid",
        "singular_term",  # لَفظ مُنفَرِد — اللَّه (لا جَذر، لا وَزن، خارِج التَّصنيف)
        "jalalah",        # legacy alias for singular_term — kept for back-compat
        "no_match",
    ] = "no_match"
    is_singular_term: bool = False
    root: str = ""
    wazn: str = ""
    canonical_wazn: str = ""
    surface_wazn: str = ""
    source_of_claim: str = ""
    proper_name: bool = False
    divine_name: bool = False
    display_notes: list = field(default_factory=list)

    # Optional alignment details (only for open_class success)
    prefix_len: int = 0
    suffix_len: int = 0
    transformations: list = field(default_factory=list)
