"""negation_detector.py — M1.C: Detect negation markers and their scope.

Per 14_Minimal_Complete_Theory: markers in CSV. Detector locates negation
particles in a clause and returns Negation objects with ProofObject-like
fields. Scope is APPROXIMATED (proper scope requires syntactic parse from
i3rab; this layer reports the marker + a candidate scope).

Constitutional commitments:
  1. Source-of-Claim — rule name + marker position
  2. Confidence      — Certificate vs Hypothesis
  3. Alternatives    — preserved if multiple negation rules might apply
  4. Reversible      — M2 gap

Input: clause text
Output: list[Negation] (zero, one, or more per clause)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from wazn_data import DIACRITICS


CONTRACT_NAME = "NegationDetector:v1"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


@dataclass
class Negation:
    marker: str                # the marker as it appeared
    marker_position: int       # word index in the clause (0-based)
    scope_target: str          # next_verb_iv | next_verb_pv | next_noun | whole_clause
    polarity_effect: str       # negate_event | negate_attribute | negate_existence
    scope_words: list = field(default_factory=list)  # candidate words in scope
    kind: str = "Hypothesis"
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "marker": self.marker,
            "marker_position": self.marker_position,
            "scope_target": self.scope_target,
            "polarity_effect": self.polarity_effect,
            "scope_words": self.scope_words,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": self.alternatives,
        }


class NegationDetector:
    """Find negation markers in a clause; report marker + candidate scope."""

    def __init__(self) -> None:
        rules = _load_rows("negation_markers.csv")
        rules.sort(key=lambda r: int(r.get("priority", "99")))
        self._rules = rules
        # Build marker → list-of-rules index (stripped form)
        self._by_marker: dict[str, list[dict]] = {}
        for r in rules:
            mp = _strip_diac(r.get("marker", ""))
            if mp:
                self._by_marker.setdefault(mp, []).append(r)

    def detect(self, clause_text: str) -> list[Negation]:
        if not clause_text or not clause_text.strip():
            return []
        words = re.split(r"\s+", clause_text.strip())
        plain_words = [_strip_diac(w.rstrip(".،,؛:؟?!")) for w in words]

        out: list[Negation] = []
        for i, pw in enumerate(plain_words):
            # Also try stripping و/ف clitic prefix (وَلَمْ → لم)
            pw_no_clitic = pw
            if len(pw) > 1 and pw[0] in ("و", "ف") and pw[1:] in self._by_marker:
                pw_no_clitic = pw[1:]
            if pw in self._by_marker:
                pass  # exact match path below
            elif pw_no_clitic in self._by_marker:
                pw = pw_no_clitic
            if pw in self._by_marker:
                matching = self._by_marker[pw]
                # Choose highest-priority (sorted), keep others as alternatives
                primary = matching[0]
                alts = [{
                    "rule": r["name"],
                    "polarity_effect": r["polarity_effect"],
                    "confidence": r["confidence"],
                } for r in matching[1:]]

                # Candidate scope: next 1-3 words depending on scope_target
                scope_target = primary.get("scope_target", "")
                scope_words = self._extract_scope(words, i, scope_target)

                out.append(Negation(
                    marker=words[i],
                    marker_position=i,
                    scope_target=scope_target,
                    polarity_effect=primary.get("polarity_effect", ""),
                    scope_words=scope_words,
                    kind=primary.get("confidence", "Hypothesis"),
                    source_of_claim=primary.get("name", ""),
                    alternatives=alts,
                ))
        return out

    def _extract_scope(self, words: list[str], i: int, target: str) -> list[str]:
        """Crude scope estimation: next 1-3 words after the marker."""
        if target == "whole_clause":
            return words[i+1:]
        max_n = 3 if "verb" in target else 2
        return words[i+1:i+1+max_n]

    def source(self) -> str:
        return CONTRACT_NAME


if __name__ == "__main__":
    det = NegationDetector()
    print(f"contract: {det.source()}  rules={len(det._rules)}")
    tests = [
        ("لَا تَأْكُلِ السُّحْتَ", 1, "negate_event"),
        ("لَمْ يَلِدْ وَلَمْ يُولَدْ", 2, "negate_event"),
        ("لَنْ تَنَالُوا الْبِرَّ", 1, "negate_event"),
        ("لَيْسَ كَمِثْلِهِ شَيْءٌ", 1, "negate_attribute"),
        ("الْحَمْدُ لِلَّهِ", 0, None),
        ("غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ", 1, "negate_attribute"),
    ]
    passes = 0
    for text, expected_count, expected_eff in tests:
        results = det.detect(text)
        ok_count = len(results) == expected_count
        ok_eff = True
        if expected_eff and results:
            ok_eff = results[0].polarity_effect == expected_eff
        ok = ok_count and ok_eff
        if ok:
            passes += 1
        mark = "✓" if ok else "✗"
        print(f"  {mark} {text}  → {len(results)} negation(s)")
        for n in results:
            print(f"      [{n.marker_position}] {n.marker} ({n.kind}) eff={n.polarity_effect} scope={n.scope_words}")
    print(f"\n{passes}/{len(tests)}")
