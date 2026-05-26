"""matcher_heuristics_contract.py — Heuristics للمُحاذي مَوسومة.

هذا contract documentation-only — لا يُعيد كتابة الـ algorithmic core
لـ root_by_alignment (الذي يَحوي ~500 سطر من المعالجة اللسانيّة الدقيقة).

ما يَفعله:
1. يُوثّق كل expansion heuristic في root_by_alignment باسم rule مُعَلَن
2. يَربط كل rule بـ family (doubled/hollow/defective/assimilated)
3. يُوفّر API بحث:  .lookup(rule_id) → {family, note}
4. يَكون مَرجعًا لِأيّ مُراجع يَريد فهم لماذا اتُّخذ قرار في المُحاذي

تَوصية مستقبليّة: نَقل الـ expansions نفسها إلى rule table بمنطق DSL.
المرحلة الحاليّة: التوثيق + الـ registry.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "MatcherHeuristicsContract:v1"


class MatcherHeuristicsContract:
    """Documentation registry for wazn matcher expansion heuristics.

    The actual expansion algorithms remain in root_by_alignment.py
    (they require imperative tree manipulation that doesn't fit data
    tables cleanly). This contract provides the NAMING + DOCUMENTATION
    layer so every heuristic has an identity.
    """

    def __init__(self) -> None:
        self._rules = _load_rows("root_expansion_rules.csv")
        self._by_id = {r["rule_id"]: r for r in self._rules}

    def lookup(self, rule_id: str) -> dict | None:
        return self._by_id.get(rule_id)

    def all_rules(self) -> list[dict]:
        return list(self._rules)

    def by_family(self, family: str) -> list[dict]:
        return [r for r in self._rules if r.get("family") == family]

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = MatcherHeuristicsContract()
    print(f"contract: {c.source()}")
    print(f"rules loaded: {len(c.all_rules())}")
    print()
    for family in ("doubled", "hollow", "defective", "assimilated"):
        rules = c.by_family(family)
        print(f"  {family} ({len(rules)}):")
        for r in rules:
            print(f"    {r['rule_id']:<22} {r['note']}")
