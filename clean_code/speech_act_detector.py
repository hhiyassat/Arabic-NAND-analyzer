"""speech_act_detector.py — M1.B: Classify each clause as a speech act.

Per 14_Minimal_Complete_Theory: all markers live in CSV. The detector
inspects the leading word, trailing punctuation, or morphology cues of
each clause and assigns one of four act types:

  assertion | command | question | vocative

Returns SpeechAct objects with ProofObject-like fields.

Constitutional commitments:
  1. Source-of-Claim — rule name + matched marker preserved
  2. Confidence      — Certificate vs Hypothesis from rule confidence
  3. Alternatives    — preserved when multiple rules fire (e.g., أ ambiguous)
  4. Reversible      — M2 gap, not enforced here

Input: a single Clause (text) or list of Clauses
Output: SpeechAct per clause
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


CONTRACT_NAME = "SpeechActDetector:v1"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


# ============================================================================
# Schema
# ============================================================================

@dataclass
class SpeechAct:
    """A speech act classification for a single clause."""
    clause_text: str
    act_type: str = "assertion"  # assertion | command | question | vocative
    markers: list = field(default_factory=list)  # rule_name + matched_marker
    kind: str = "Hypothesis"  # Certificate | Hypothesis | Zero
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "act_type": self.act_type,
            "markers": self.markers,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": self.alternatives,
        }


# ============================================================================
# Engine
# ============================================================================

class SpeechActDetector:
    """Classify each clause into one of {assertion, command, question, vocative}."""

    def __init__(self) -> None:
        rules = _load_rows("speech_act_markers.csv")
        rules.sort(key=lambda r: int(r.get("priority", "99")))
        self._rules = rules
        # Index by act_type for alternative-tracking
        self._by_type = {}
        for r in rules:
            self._by_type.setdefault(r.get("act_type"), []).append(r)
        # Embedded clause rules (M1.B session 6)
        try:
            self._embedded_rules = _load_rows("embedded_clause_rules.csv")
        except Exception:
            self._embedded_rules = []
        self._embedding_verbs = {r["verb_stripped"]: r for r in self._embedded_rules
                                 if r.get("verb_stripped")}

    def detect_embedding(self, clause_text: str) -> Optional[dict]:
        """If the clause starts with a speech-act verb (قال، سأل، ...) return
        its rule entry. Indicates the NEXT clause is embedded under it.
        """
        first = self._first_word_plain(clause_text)
        # Try exact match first
        if first in self._embedding_verbs:
            return self._embedding_verbs[first]
        # Try stripping prefix و / ف (common in Quranic discourse: وقال، فقال)
        for prefix in ("و", "ف"):
            if first.startswith(prefix) and first[1:] in self._embedding_verbs:
                rule = dict(self._embedding_verbs[first[1:]])
                rule["matched_with_prefix"] = prefix
                return rule
        return None

    def detect(self, clause_text: str) -> SpeechAct:
        """Classify the speech act type of a single clause."""
        if not clause_text or not clause_text.strip():
            return SpeechAct(
                clause_text=clause_text,
                act_type="assertion",
                kind="Zero",
                source_of_claim="empty_input",
            )

        text = clause_text.strip()
        first_word = self._first_word_plain(text)
        last_punct = self._last_punctuation(text)

        matched: list[tuple[dict, str]] = []  # (rule, matched_value)
        for rule in self._rules:
            mk = rule.get("marker_kind")
            marker = rule.get("marker", "")
            marker_plain = _strip_diac(marker)
            if not marker and mk != "fallback":
                continue

            if mk == "prefix_word":
                if first_word == marker_plain:
                    matched.append((rule, marker))
            elif mk == "prefix_letter":
                if first_word.startswith(marker_plain) and len(first_word) > 1:
                    matched.append((rule, marker))
            elif mk == "suffix_punct":
                if last_punct == marker:
                    matched.append((rule, marker))
            elif mk == "morphology":
                # Skipped at this layer (would require morpho-engine round-trip)
                pass
            elif mk == "fallback":
                # Always matches if nothing else does
                pass

        # Choose the highest-priority (already sorted), but prefer Certificate
        certificate_matches = [m for m in matched if m[0].get("confidence") == "Certificate"]
        if certificate_matches:
            chosen, mvalue = certificate_matches[0]
        elif matched:
            chosen, mvalue = matched[0]
        else:
            # Fallback to assertion
            fallback = next((r for r in self._rules if r.get("marker_kind") == "fallback"), None)
            chosen = fallback or {"act_type": "assertion", "name": "default", "confidence": "Hypothesis"}
            mvalue = ""

        # Build SpeechAct
        markers_list = [{"rule": chosen.get("name", ""), "marker": mvalue}]
        alternatives = []
        for r, m in matched:
            if r is not chosen:
                alternatives.append({
                    "act_type": r.get("act_type"),
                    "rule": r.get("name", ""),
                    "marker": m,
                    "confidence": r.get("confidence"),
                })

        return SpeechAct(
            clause_text=clause_text,
            act_type=chosen.get("act_type", "assertion"),
            markers=markers_list,
            kind=chosen.get("confidence", "Hypothesis"),
            source_of_claim=chosen.get("name", ""),
            alternatives=alternatives,
        )

    def detect_batch(self, clauses: list) -> list[SpeechAct]:
        """Apply detect() to a list of Clause objects or strings."""
        out = []
        for c in clauses:
            text = c.text if hasattr(c, "text") else str(c)
            out.append(self.detect(text))
        return out

    def _first_word_plain(self, text: str) -> str:
        sp = re.split(r"\s+", text.strip(), maxsplit=1)
        first = sp[0] if sp else ""
        first = first.rstrip(".،,؛:؟?!")
        return _strip_diac(first)

    def _last_punctuation(self, text: str) -> str:
        text = text.rstrip()
        if not text:
            return ""
        last = text[-1]
        return last if last in ".،,؛:؟?!" else ""

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    det = SpeechActDetector()
    print(f"contract: {det.source()}")
    print(f"rules loaded: {len(det._rules)}")
    print()

    tests = [
        # (text, expected_act)
        ("الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "assertion"),
        ("هَلْ جَاءَكَ حَدِيثُ الْغَاشِيَةِ", "question"),
        ("كَيْفَ تَكْفُرُونَ بِاللَّهِ", "question"),
        ("يَا أَيُّهَا النَّاسُ", "vocative"),
        ("أَيُّهَا الَّذِينَ آمَنُوا", "vocative"),
        ("ادْخُلُوا الْجَنَّةَ", "assertion"),  # imperative needs morpho — fallback
        ("لَا تَأْكُلْ", "command"),
        ("مَتَى نَصْرُ اللَّهِ", "question"),
        ("أَأَنْذَرْتَهُمْ أَمْ لَمْ تُنْذِرْهُمْ", "question"),
    ]

    passes = 0
    for text, expected in tests:
        result = det.detect(text)
        ok = "✓" if result.act_type == expected else "✗"
        if result.act_type == expected:
            passes += 1
        alt = f" [+{len(result.alternatives)} alt]" if result.alternatives else ""
        print(f"  {ok} {text}")
        print(f"      → {result.act_type} ({result.kind}) src={result.source_of_claim}{alt}")
    print(f"\nنتيجة: {passes}/{len(tests)}")
