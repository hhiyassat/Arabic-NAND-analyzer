"""i3rab_engine — rule-based Arabic i'rab (grammatical analysis) engine.

Three layers, each independently testable:

    Layer 1 (WordClass)  → HARF / ISM_MABNI / ISM_MUARAB / FIIL / AALAM /
                            JAMID / JALALAH
    Layer 2 (Case+Mark)  → case_id (1-5) + mark_id (1-14)
    Layer 3 (Role)       → role_id (from i3rab_ref/i3rab_roles.csv)

Output: TokenI3rab per token + SentenceI3rab for the whole input.

Constitutional commitments (matching project policy):
  - Pure rule-based; no data hardcoded in modules
  - All data loaded from canonical sources (MASAQ, i3rab_ref/)
  - Every decision carries a source_of_claim
  - i3rab is EVALUATION-only: never wired into wazn/root adjudication
"""

from .types import TokenI3rab, SentenceI3rab, WORD_CLASSES, CASE_IDS, MARK_IDS
from .engine import I3rabEngine

__all__ = [
    "TokenI3rab",
    "SentenceI3rab",
    "WORD_CLASSES",
    "CASE_IDS",
    "MARK_IDS",
    "I3rabEngine",
]
