"""wazn_matcher_v3.py — Constitutional root + wazn analyzer.

DESIGN:
  v3 = Extractor + Verifier
  - Extractor (root_extractor.py): produces candidates by PURE RULES
  - Verifier (root_verifier.py): annotates each candidate with reference flags
  - This file glues them and re-ranks based on verification status

CONSTITUTIONAL IMPROVEMENT OVER v2:
  - v2 looked up roots in a database and used that as the answer
  - v3 extracts roots by rules, then checks if the rule's output is attested
  - The reference DBs (mishkat, audited, canonical) inform CONFIDENCE,
    not the root choice itself.

CURRENT SCOPE (phase 4, paired with extractor's phase 2.1):
  - Sound trilateral only
  - For weak/hamza roots, returns out_of_scope_v2_fallback flag
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import sys

# Import sibling modules from the same directory
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import root_extractor as _ext
import root_verifier as _ver


# ============================================================================
# Output data structure
# ============================================================================

@dataclass
class V3Match:
    """A single root+wazn match with full constitutional provenance."""
    root: str
    wazn: str
    form: str                         # I, II, ... or "noun"
    confidence: float                 # final score (0.0 - 1.0)
    # Extraction provenance (from root_extractor)
    rule_id: str
    rule_name: str
    transformations: list[str] = field(default_factory=list)
    # Verification flags (from root_verifier)
    in_mishkat: bool = False
    in_audited: bool = False
    in_canonical: bool = False
    quran_count: int = 0
    verification_strength: str = "unverified"
    reference_sources: list[str] = field(default_factory=list)

    @property
    def source_of_claim(self) -> str:
        """Compact provenance string for MEEMAR.csv."""
        parts = [f"extracted:{self.rule_id}"]
        if self.in_mishkat:
            parts.append(f"verified_in_mishkat({self.quran_count}x)")
        if self.in_audited:
            parts.append("verified_in_audited_roots")
        if self.in_canonical:
            parts.append("verified_in_canonical")
        if not (self.in_mishkat or self.in_audited or self.in_canonical):
            parts.append("UNVERIFIED")
        return " | ".join(parts)


# ============================================================================
# Confidence re-ranking weights
# ============================================================================

# Boost factors applied to extractor's base confidence based on verification
VERIFICATION_BOOST = {
    "unverified":        0.5,   # significant penalty
    "single_reference":  1.0,   # no change
    "double_reference":  1.1,   # mild boost
    "triple_reference":  1.15,
}


# ============================================================================
# Main analyzer
# ============================================================================

class AnalyzerV3:
    """Rule-based root extractor + reference verifier."""

    def __init__(self):
        self.verifier = _ver.RootVerifier()

    def analyze(self, word: str) -> list[V3Match]:
        """Extract candidate roots and annotate with verification.

        Returns ranked list (best first). Empty list if out of scope.
        """
        if not word:
            return []

        ext_result = _ext.extract(word)
        if ext_result.out_of_scope_reason:
            return []  # phase 2.1 doesn't handle this — callers fall back

        matches: list[V3Match] = []
        for c in ext_result.candidates:
            v = self.verifier.verify(c.root)
            # Apply verification boost / penalty
            boost = VERIFICATION_BOOST.get(v.verification_strength, 1.0)
            final_conf = min(1.0, c.confidence * boost)
            matches.append(V3Match(
                root=c.root,
                wazn=c.wazn,
                form=c.form,
                confidence=final_conf,
                rule_id=c.rule_id,
                rule_name=c.rule_name,
                transformations=c.transformations,
                in_mishkat=v.in_mishkat,
                in_audited=v.in_audited,
                in_canonical=v.in_canonical,
                quran_count=v.quran_count,
                verification_strength=v.verification_strength,
                reference_sources=v.reference_sources,
            ))

        # Re-rank by final confidence (verified candidates come first)
        matches.sort(key=lambda m: (-m.confidence, -m.quran_count))
        return matches


# ============================================================================
# Self-test
# ============================================================================

def _self_test():
    print("=== wazn_matcher_v3 self-test ===\n")
    a = AnalyzerV3()
    test_words = [
        "كَتَبَ",         # كتب — should be top
        "يَكْتُبُ",       # كتب
        "مَكْتُوبٌ",      # كتب (passive participle)
        "مَكْتَبٌ",       # كتب (location noun)
        "اسْتَخْرَجَ",    # خرج (Form X)
        "يَنْصُرُونَ",    # نصر
        "مُجْتَهِدٌ",     # جهد (Form VIII active participle)
        "قَالَ",           # weak — should be out of scope (phase 2.1)
    ]
    for w in test_words:
        matches = a.analyze(w)
        if not matches:
            print(f"  {w!r}: OUT OF SCOPE (weak/hamza)")
            continue
        top = matches[0]
        print(f"  {w!r}: root={top.root!r}  wazn={top.wazn}  conf={top.confidence:.2f}")
        print(f"    {top.source_of_claim}")
        if len(matches) > 1:
            alt = matches[1:4]
            print(f"    alternatives: {[(m.root, m.wazn, round(m.confidence,2)) for m in alt]}")
        print()


if __name__ == "__main__":
    _self_test()
