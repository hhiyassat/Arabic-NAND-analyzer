"""verbal_wazn_contract.py — قاعدة كَشف الوزن الفعلي.

Per 14_Minimal_Complete_Theory: language rules in data, not in code.

Replaces inline ``_is_verbal_wazn`` and ``_looks_like_verb_by_surface``
in i3rab_engine/layer1.py. The rules are declarative in
``contracts/rules/verbal_wazn_rules.csv``.

Each rule has:
  rule_id  — unique identifier (NV_001, IV_001, PV_001…)
  phase    — early_reject | prefix | suffix_past | hamzat_wasl | three_letter
  pattern  — DSL string describing the pattern (see _match below)
  kind     — verbal | nominal
  aspect   — PV | IV | CV | (empty)
  note     — human-readable Arabic explanation
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from wazn_data import DIACRITICS


CONTRACT_NAME = "VerbalWaznContract:v1"
_DIAC = set(DIACRITICS)


def _strip(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIAC)


def _vowel_after(wazn: str, ch: str) -> str:
    """Return diacritic immediately after first occurrence of ch."""
    i = wazn.find(ch)
    if i < 0 or i + 1 >= len(wazn):
        return ""
    nxt = wazn[i + 1]
    return nxt if nxt in {"َ", "ِ", "ُ", "ْ", "ّ"} else ""


def _match_pattern(wazn: str, surface: str, pattern: str) -> bool:
    """Evaluate a single rule pattern.

    Pattern DSL:
      starts:<str>          — wazn starts with this prefix (diacritized)
      starts_in:<a b c>     — wazn starts with any of these (space-separated)
      ends:<str>            — plain wazn ends with this
      plain_equals:<str>    — plain wazn equals this
      faail_with_kasra      — special: فَاعِل with kasra on ع
      3chars_with_vowel_endings — three-letter wazn with vowels on all
    """
    plain = _strip(wazn)
    surf_plain = _strip(surface) if surface else ""

    if pattern.startswith("starts:"):
        return wazn.startswith(pattern[len("starts:"):])

    if pattern.startswith("starts_in:"):
        options = pattern[len("starts_in:"):].split()
        return any(wazn.startswith(o) for o in options)

    if pattern.startswith("ends:"):
        return plain.endswith(pattern[len("ends:"):])

    if pattern.startswith("plain_equals:"):
        return plain == pattern[len("plain_equals:"):]

    if pattern == "faail_with_kasra":
        return plain.startswith("فاعل") and _vowel_after(wazn, "ع") == "ِ"

    if pattern == "faail_with_fatha":
        return plain.startswith("فاعل") and _vowel_after(wazn, "ع") == "َ"

    if pattern == "3chars_with_vowel_endings":
        # 3 letters in stripped form, with vowel on first two
        if len(plain) != 3:
            return False
        letter_positions = [i for i, c in enumerate(wazn) if c not in _DIAC]
        if len(letter_positions) < 3:
            return False
        first_d_idx = letter_positions[0] + 1
        second_l_idx = letter_positions[1]
        first_d = wazn[first_d_idx] if first_d_idx < second_l_idx else ""
        second_d_idx = letter_positions[1] + 1
        third_l_idx = letter_positions[2]
        second_d = wazn[second_d_idx] if second_d_idx < third_l_idx else ""
        return first_d in {"َ", "ُ", "ِ"} and second_d in {"َ", "ُ", "ِ"}

    return False


class VerbalWaznContract:
    """Determines whether a wazn is verbal, with explicit rule attribution."""

    def __init__(self) -> None:
        rules = _load_rows("verbal_wazn_rules.csv")
        # Group by phase for ordered evaluation
        self._early_reject = [r for r in rules if r["phase"] == "early_reject"]
        self._verbal_rules = [r for r in rules if r["kind"] == "verbal"]

    def classify(self, wazn: str, *, surface: str = "") -> dict:
        """Return {kind, aspect, rule_id, note} or {kind:'unknown', ...}."""
        if not wazn:
            return {"kind": "unknown", "aspect": "", "rule_id": "",
                    "note": "empty wazn"}

        # Phase 1: early rejects → nominal
        for r in self._early_reject:
            if _match_pattern(wazn, surface, r["pattern"]):
                return {
                    "kind": "nominal",
                    "aspect": "",
                    "rule_id": r["rule_id"],
                    "note": r["note"],
                }

        # Phase 2: verbal rules
        for r in self._verbal_rules:
            if _match_pattern(wazn, surface, r["pattern"]):
                return {
                    "kind": "verbal",
                    "aspect": r.get("aspect", ""),
                    "rule_id": r["rule_id"],
                    "note": r["note"],
                }

        return {"kind": "unknown", "aspect": "", "rule_id": "",
                "note": "no rule matched"}

    def is_verbal(self, wazn: str, *, surface: str = "") -> tuple[bool, str]:
        """Legacy-shape interface: returns (is_verb, aspect)."""
        c = self.classify(wazn, surface=surface)
        return c["kind"] == "verbal", c.get("aspect", "")

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = VerbalWaznContract()
    print(f"contract: {c.source()}")
    print()
    tests = [
        ("فَعَل", "كَتَبَ", "verbal/PV"),
        ("يَفْعُل", "يَكْتُبُ", "verbal/IV"),
        ("فَاعِل", "كَاتِب", "nominal (active participle)"),
        ("فَاعَل", "قَاتَل", "verbal/PV form III"),
        ("مَفْعُول", "مَكْتُوب", "nominal (passive participle)"),
        ("مُفْتَعِل", "مُسْتَخْرِج", "nominal"),
        ("فِعَال", "كِتَاب", "nominal (مصدر)"),
        ("فَعِيل", "عَظِيم", "nominal (صفة مشبهة)"),
        ("فَالُوا", "قَالُوا", "verbal/PV hollow + suffix"),
    ]
    print(f"{'الوزن':<12} {'السطح':<14} {'النوع':<10} {'aspect':<6} {'rule':<8} {'الوصف'}")
    print("-" * 90)
    for wazn, surface, expected in tests:
        r = c.classify(wazn, surface=surface)
        print(f"{wazn:<12} {surface:<14} {r['kind']:<10} {r['aspect']:<6} "
              f"{r['rule_id']:<8} {r['note']}")
