"""modal_detector.py — M1.D: Detect modal markers (deontic / epistemic).

Per 14_Minimal_Complete_Theory: markers in CSV. Returns Modal objects
with strength in [0,1] (the only scalar-confidence in M1; M2 gap for
the others).

Constitutional commitments:
  1. Source-of-Claim — rule name + marker position
  2. Confidence      — Certificate vs Hypothesis + scalar strength
  3. Alternatives    — preserved
  4. Reversible      — M2 gap

Modal types:
  - deontic: obligation / permission / recommendation
  - epistemic: possibility / probability / belief
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from wazn_data import DIACRITICS


CONTRACT_NAME = "ModalDetector:v1"


def _strip_diac(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


@dataclass
class Modal:
    marker: str
    marker_position: int
    modal_type: str            # deontic | epistemic
    strength: float            # [0,1]
    kind: str = "Hypothesis"
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "marker": self.marker,
            "marker_position": self.marker_position,
            "modal_type": self.modal_type,
            "strength": self.strength,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": self.alternatives,
        }


class ModalDetector:

    def __init__(self) -> None:
        rules = _load_rows("modal_markers.csv")
        rules.sort(key=lambda r: int(r.get("priority", "99")))
        self._rules = rules
        # Index: stripped first-word → rule (for single-word markers)
        # Also keep list of multi-word markers for token-window matching
        self._single_word_idx: dict[str, list[dict]] = {}
        self._multi_word: list[dict] = []
        for r in rules:
            m = _strip_diac(r.get("marker", ""))
            if not m:
                continue
            if " " in m:
                self._multi_word.append(r)
            else:
                self._single_word_idx.setdefault(m, []).append(r)

    def detect(self, clause_text: str) -> list[Modal]:
        if not clause_text or not clause_text.strip():
            return []
        words = re.split(r"\s+", clause_text.strip())
        plain_words = [_strip_diac(w.rstrip(".،,؛:؟?!")) for w in words]

        out: list[Modal] = []
        # Match single-word markers — exact OR prefix-of-word (for لعلكم, عساه...)
        for i, pw in enumerate(plain_words):
            matched_key = None
            if pw in self._single_word_idx:
                matched_key = pw
            else:
                # Prefix match: لعلكم starts with لعل
                for key in self._single_word_idx:
                    if len(key) >= 3 and pw.startswith(key):
                        matched_key = key
                        break
            if matched_key is not None:
                matching = self._single_word_idx[matched_key]
                primary = matching[0]
                alts = [{
                    "rule": r["name"],
                    "modal_type": r["modal_type"],
                    "strength": float(r["strength"]),
                    "confidence": r["confidence"],
                } for r in matching[1:]]
                out.append(Modal(
                    marker=words[i],
                    marker_position=i,
                    modal_type=primary.get("modal_type", ""),
                    strength=float(primary.get("strength", "0.5")),
                    kind=primary.get("confidence", "Hypothesis"),
                    source_of_claim=primary.get("name", ""),
                    alternatives=alts,
                ))

        # Match multi-word markers (sliding window)
        n = len(plain_words)
        for rule in self._multi_word:
            m_stripped = _strip_diac(rule["marker"])
            m_tokens = m_stripped.split(" ")
            L = len(m_tokens)
            for i in range(n - L + 1):
                if plain_words[i:i+L] == m_tokens:
                    out.append(Modal(
                        marker=" ".join(words[i:i+L]),
                        marker_position=i,
                        modal_type=rule.get("modal_type", ""),
                        strength=float(rule.get("strength", "0.5")),
                        kind=rule.get("confidence", "Hypothesis"),
                        source_of_claim=rule.get("name", ""),
                    ))
        return out

    def source(self) -> str:
        return CONTRACT_NAME


if __name__ == "__main__":
    det = ModalDetector()
    print(f"contract: {det.source()}  rules={len(det._rules)}")
    tests = [
        ("يَجِبُ أَنْ نَذْهَبَ", 1, "deontic", 1.0),
        ("قَدْ أَفْلَحَ الْمُؤْمِنُونَ", 1, "epistemic", 0.5),
        ("لَعَلَّكُمْ تَتَّقُونَ", 1, "epistemic", 0.4),
        ("عَسَى رَبُّكُمْ أَنْ يَرْحَمَكُمْ", 1, "epistemic", 0.4),
        ("لَا بُدَّ مِنْ مُحَاوَلَةٍ", 1, "deontic", 1.0),
        ("الْحَمْدُ لِلَّهِ", 0, None, None),
        ("رُبَّمَا يَأْتِي غَدًا", 1, "epistemic", 0.3),
    ]
    passes = 0
    for text, expected_count, expected_type, expected_str in tests:
        results = det.detect(text)
        ok_count = len(results) == expected_count
        ok_type = True if expected_type is None or not results else results[0].modal_type == expected_type
        ok = ok_count and ok_type
        if ok:
            passes += 1
        mark = "✓" if ok else "✗"
        print(f"  {mark} {text}  → {len(results)} modal(s)")
        for m in results:
            print(f"      [{m.marker_position}] {m.marker} type={m.modal_type} str={m.strength} ({m.kind})")
    print(f"\n{passes}/{len(tests)}")
