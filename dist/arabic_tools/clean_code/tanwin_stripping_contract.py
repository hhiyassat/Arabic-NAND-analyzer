"""tanwin_stripping_contract.py — Named contract for tanwin stripping.

Per 14_Minimal_Complete_Theory: language rules must be named contracts
backed by data files, not inline if-statements.

This contract replaces the inline ``_strip_tanwin_for_match`` that used
to live in root_pipeline.py. The rules are now declarative in
``contracts/rules/tanwin_stripping.csv``.

Use:
    from tanwin_stripping_contract import TanwinStrippingContract
    contract = TanwinStrippingContract()
    stripped, applied = contract.apply("كِتَابًا")
    # stripped="كِتَاب", applied={"suffix":"ًا","kind":"tanwin_fath_tanwin_first"}
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import load_tanwin_stripping_rules


CONTRACT_NAME = "TanwinStrippingContract:v1"


class TanwinStrippingContract:
    """Strip tanwin markers from a word per declared rules.

    Rules are loaded from ``data/contracts/rules/tanwin_stripping.csv``.
    Each rule has: suffix, strip_chars, kind, note. First matching rule
    fires (rules are ordered by specificity in the CSV).
    """

    def __init__(self) -> None:
        # Load + sort by suffix length descending so longer suffixes
        # match before shorter ones (e.g., "ًا" before "ً")
        rules = load_tanwin_stripping_rules()
        self._rules = sorted(
            rules,
            key=lambda r: -len(r.get("suffix", "")),
        )

    def apply(self, word: str) -> tuple[str, Optional[dict]]:
        """Return (stripped_word, applied_rule).

        If no rule matches, returns (word, None).
        """
        for rule in self._rules:
            suffix = rule.get("suffix", "")
            if suffix and word.endswith(suffix):
                strip_n = int(rule.get("strip_chars", "1"))
                return word[:-strip_n], dict(rule)
        return word, None

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = TanwinStrippingContract()
    tests = [
        "كِتَابًا",   # tanwin then alif
        "كِتَابَاً",  # alif then tanwin
        "سِجَالَاً",  # alif then tanwin (real user case)
        "كِتَابٌ",    # tanwin damm
        "كِتَابٍ",    # tanwin kasr
        "حَدِيقَةً",  # tanwin fath on taa marbuta (no alif)
        "كِتَاب",     # no tanwin at all
    ]
    print(f"contract: {c.source()}")
    print(f"rules loaded: {len(c._rules)}")
    print()
    for w in tests:
        stripped, applied = c.apply(w)
        if applied:
            print(f"  {w:<14} → {stripped:<12} (rule: {applied['kind']})")
        else:
            print(f"  {w:<14} → {stripped:<12} (no tanwin)")
