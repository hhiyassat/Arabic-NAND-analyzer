"""inter_clause_extractor.py — جَلسة 18: استخراج العَلاقات بَين الجُمَل.

يَأخُذ نَتيجَة `ClauseSegmenter` (مِن `clause_segmenter.py`) ويُنتِج قائِمَة
عَلاقات بَين الجُمَل: تَعاقُب، سَبَب، شَرط، نَفي، تَفسير، مَقول قَول.

كُلّ علاقَة بَين جُملتَين تَعتَمِد على:
  • مَصدَر القَطع لِلجُملة (مِن `Clause.source_of_claim`)
  • الـ connective الَّذي يَبدأ بِه الجُملة الثَّانيَة (مِن `Clause.connective`)
  • أَدوات الشَّرط الَّتي يَبدأ بِها clause (مِن `_detect_conditional`)
  • وُجود فِعل قَول في الجُملة السَّابِقَة (مَقول قَول)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from clause_segmenter import ClauseSegmenter, _strip_diac


CONTRACT_NAME = "InterClauseExtractor:v1"


@dataclass
class InterClauseRelation:
    """عَلاقَة بَين جُملتَين."""
    name: str = ""
    kind_type: str = ""           # coordinate / causal / contrast / condition / negation / explanation / quotation / disjunction
    source_clause_idx: int = -1
    target_clause_idx: int = -1
    trigger: Optional[str] = None
    kind: str = "Hypothesis"
    source_of_claim: str = ""
    contract: str = CONTRACT_NAME
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind_type": self.kind_type,
            "source_clause_idx": self.source_clause_idx,
            "target_clause_idx": self.target_clause_idx,
            "trigger": self.trigger,
            "kind": self.kind,
            "source_of_claim": self.source_of_claim,
            "contract": self.contract,
            "alternatives": list(self.alternatives),
        }


_QAWL_VERBS = {"قال", "قالت", "قالوا", "يقول", "تقول", "يقولون", "قيل", "قُل"}
_QAWL_VERBS_PLAIN = {_strip_diac(w) for w in _QAWL_VERBS}


class InterClauseExtractor:

    def __init__(self) -> None:
        self._rules = _load_rows("inter_clause_relations.csv")
        # فِهرس بِالـ trigger_marker (بَعد تَجريد التَّشكيل)
        self._by_marker: dict[str, list[dict]] = {}
        for r in self._rules:
            mk = _strip_diac(r.get("trigger_marker", ""))
            self._by_marker.setdefault(mk, []).append(r)

    def extract(self, clauses: list) -> list[InterClauseRelation]:
        rels: list[InterClauseRelation] = []
        for i in range(1, len(clauses)):
            prev = clauses[i - 1]
            curr = clauses[i]
            # 1. اعتماد connective: لو الجُملة الحاليَّة connective غَير فارِغ
            conn = curr.connective or ""
            conn_plain = _strip_diac(conn) if conn else ""
            if conn_plain and conn_plain in self._by_marker:
                for rule in self._by_marker[conn_plain]:
                    if rule.get("trigger_source", "").startswith("clause_connective"):
                        rels.append(self._build(rule, i, i - 1, conn))
                        break
            # 2. اعتماد conditional: لو الجُملة الحاليَّة تَبدَأ بِأَداة شَرط
            first_word = _strip_diac(curr.text.split()[0] if curr.text.split() else "")
            if first_word and first_word in self._by_marker:
                for rule in self._by_marker[first_word]:
                    if rule.get("trigger_source", "").startswith("clause_conditional"):
                        rels.append(self._build(rule, i, i - 1, first_word))
                        break
            # 3. اعتماد نَفي: لو الجُملة تَبدأ بِـ لا/ما/لم/لن
            if first_word in {"لا", "ما", "لم", "لن"}:
                for rule in self._by_marker.get(first_word, []):
                    if rule.get("trigger_source", "").startswith("clause_negation"):
                        rels.append(self._build(rule, i, i - 1, first_word))
                        break
            # 4. اعتماد تَفسير: لو الجُملة السَّابِقَة انتَهَت بِنُقطَتَين
            prev_src = prev.source_of_claim or ""
            if "colon" in prev_src.lower() or prev.text.endswith(":"):
                # نَتَحَقَّق مِن وُجود فِعل قَول في الجُملة السَّابِقَة
                prev_words = [_strip_diac(w) for w in prev.text.split()]
                has_qawl = any(w in _QAWL_VERBS_PLAIN for w in prev_words)
                if has_qawl:
                    for rule in self._by_marker.get("قال", []):
                        if rule.get("trigger_source", "").startswith("clause_quotative"):
                            rels.append(self._build(rule, i, i - 1, "قول"))
                            break
                else:
                    # explanation عامَّة
                    for rule in self._by_marker.get(":", []):
                        if rule.get("trigger_source", "").startswith("clause_punct"):
                            rels.append(self._build(rule, i, i - 1, ":"))
                            break
        return rels

    @staticmethod
    def _build(rule: dict, src_idx: int, tgt_idx: int, trigger: str) -> InterClauseRelation:
        return InterClauseRelation(
            name=rule.get("creates_relation", "?"),
            kind_type=rule.get("relation_kind", "?"),
            source_clause_idx=src_idx,
            target_clause_idx=tgt_idx,
            trigger=trigger,
            kind="Hypothesis",
            source_of_claim=(
                f"trigger:{trigger} + clause[{src_idx}] follows clause[{tgt_idx}] + "
                f"inter_clause_relations:{rule.get('name','?')}"
            ),
        )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    seg = ClauseSegmenter()
    extr = InterClauseExtractor()

    tests = [
        ("أَمَرَه فَأَطَاعَ", ["sequence_with_cause"]),
        ("جاءَ زَيدٌ ثُمَّ خَرَجَ عَمرٌو", ["sequence_delayed"]),
        ("قُمْ. لا تَنَمْ.", ["negation"]),
        ("إِنْ تَجتَهِدْ تَنجَحْ", ["condition"]),
        ("قَالَ مُوسَى: اعبُدوا اللَّهَ", ["quotation"]),
        ("ذَهَبَ زَيدٌ. وَكَتَبَ عَمرٌو", ["sequence"]),
    ]
    for text, expected in tests:
        clauses = seg.segment(text)
        rels = extr.extract(clauses)
        names = [r.name for r in rels]
        ok = any(e in names for e in expected) if expected else True
        mark = "✓" if ok else "✗"
        print(f"{mark} «{text}» → clauses={len(clauses)} rels={names}")
        for r in rels:
            print(f"    • {r.name} ({r.kind_type}): clause[{r.source_clause_idx}] ← clause[{r.target_clause_idx}] via «{r.trigger}»")
