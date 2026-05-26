"""proof_object.py — Certificate / Hypothesis / Zero.

Per ``معمار_المعنى_العربي/14_Minimal_Complete_Theory.md``: every analytical
result must be one of three explicit outcomes, with a named contract and
a documented source-of-claim.

  Certificate  — closed, no blockers, unique path. Deterministic lookup
                 (closed_class, jamid, jalalah) or a wazn match with
                 zero alternatives.
  Hypothesis   — possible analysis with residue, ambiguity, or heuristic
                 confidence. Wazn alignment (which is structural inference)
                 normally lands here.
  Zero         — out of domain, no match, or refuted. NOT a guess.

ProofObject is a SUBCLASS of WordAnalysis, so legacy callers (``r.root``,
``r.wazn``, ``r.status``) keep working. New callers can read ``r.kind``,
``r.contract``, ``r.blockers``, ``r.alternatives``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# We import the legacy WordAnalysis class so ProofObject can extend it.
# Importing lazily inside the dataclass file is fine (no circular).
from root_pipeline_types import WordAnalysis  # type: ignore

ProofKind = Literal["Certificate", "Hypothesis", "Zero"]


@dataclass
class ProofObject(WordAnalysis):
    """WordAnalysis enriched with proof-theoretic metadata.

    Adds (relative to WordAnalysis):
      kind          — Certificate | Hypothesis | Zero
      contract      — name of the contract that produced this result
                       (e.g., "jalalah_convention", "closed_class_detector",
                        "jamid_detector", "wazn_aligner")
      blockers      — list of reasons preventing Certificate (if any)
      alternatives  — other candidate results not chosen (for Hypothesis)

    Legacy attributes (.word, .root, .wazn, .status, .source_of_claim, ...)
    are inherited from WordAnalysis. Old code keeps working.
    """

    kind: ProofKind = "Zero"
    contract: str = ""
    blockers: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)

    # --------------------------------------------------------------
    # Convenience predicates
    # --------------------------------------------------------------

    @property
    def is_certificate(self) -> bool:
        return self.kind == "Certificate"

    @property
    def is_hypothesis(self) -> bool:
        return self.kind == "Hypothesis"

    @property
    def is_zero(self) -> bool:
        return self.kind == "Zero"

    # --------------------------------------------------------------
    # Serialization
    # --------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "contract": self.contract,
            "word": self.word,
            "word_plain": self.word_plain,
            "status": self.status,
            "root": self.root,
            "wazn": self.wazn,
            "canonical_wazn": self.canonical_wazn,
            "surface_wazn": self.surface_wazn,
            "source_of_claim": self.source_of_claim,
            "proper_name": self.proper_name,
            "divine_name": self.divine_name,
            "blockers": list(self.blockers),
            "alternatives": list(self.alternatives),
            "display_notes": list(self.display_notes),
            "prefix_len": self.prefix_len,
            "suffix_len": self.suffix_len,
            "transformations": list(self.transformations),
        }


# ----------------------------------------------------------------------
# Factory helpers — for callers to construct ProofObjects without dealing
# with field initialization. Each one names the contract explicitly.
# ----------------------------------------------------------------------


def certificate(contract: str, source_of_claim: str, **kwargs) -> ProofObject:
    """Construct a Certificate with the named contract."""
    return ProofObject(
        kind="Certificate",
        contract=contract,
        source_of_claim=source_of_claim,
        **kwargs,
    )


def hypothesis(
    contract: str,
    source_of_claim: str,
    *,
    blockers: list | None = None,
    alternatives: list | None = None,
    **kwargs,
) -> ProofObject:
    """Construct a Hypothesis with the named contract and (optional) blockers."""
    return ProofObject(
        kind="Hypothesis",
        contract=contract,
        source_of_claim=source_of_claim,
        blockers=list(blockers) if blockers else [],
        alternatives=list(alternatives) if alternatives else [],
        **kwargs,
    )


def zero(contract: str, source_of_claim: str, **kwargs) -> ProofObject:
    """Construct a Zero with the named contract and reason."""
    return ProofObject(
        kind="Zero",
        contract=contract,
        source_of_claim=source_of_claim,
        **kwargs,
    )
