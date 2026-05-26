"""predicate_engine.py — مُحَرِّك تَقييم predicates مَدفوع بِالـ CSV.

MC-COMPLIANT (Contract D): لا inline rules.
كُلّ predicate مُعَرَّف في CSV بِـ:
  • predicate_type: نَوع العَمَليَّة (startswith_any، contains_at_position، equals...)
  • target: الحَقل المُستَهدَف مِن الـ context
  • operation: العَمَليَّة الفِعليَّة
  • operand: المُعامِل (CSV list مَفصول بِفاصِلَة)

الـ12 عَمَليَّة المَدعومَة هي البَدائِيَّات الذَّرّيَّة فَقَط — لَيسَت قَواعِد دَلاليَّة.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class PredicateEngine:
    """مُحَرِّك تَقييم predicates مَدفوع بِالـ CSV."""

    def __init__(self, predicates_csv: Path):
        self.predicates: dict[str, dict] = {}
        self._load(predicates_csv)

    def _load(self, path: Path):
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = row.get("atom_id") or row.get("predicate_name", "")
                if not pid:
                    continue
                operand = row.get("operand", "").strip()
                operands = [o.strip() for o in operand.split(",")] if operand else []
                self.predicates[pid.strip()] = {
                    "predicate_type": row.get("predicate_type", "").strip(),
                    "target": row.get("target") or row.get("target_field", ""),
                    "operation": row.get("operation", "").strip(),
                    "operands": operands,
                    "description": row.get("description", "").strip(),
                }

    def evaluate(self, predicate_id: str, ctx: dict) -> bool:
        """يُقَيِّم predicate واحِد ضِدّ السِّياق."""
        pred = self.predicates.get(predicate_id.strip())
        if not pred:
            return False
        ptype = pred["predicate_type"]
        target = pred["target"]
        operands = pred["operands"]

        # العَمَليَّات الذَّرّيَّة الـ12
        if ptype == "always_true":
            return True
        elif ptype == "startswith_any":
            value = self._get_target_value(target, ctx)
            return any(value.startswith(op) for op in operands)
        elif ptype == "not_startswith":
            value = self._get_target_value(target, ctx)
            if not value:
                return False
            return not any(value.startswith(op) for op in operands)
        elif ptype == "not_startswith_any":
            value = self._get_target_value(target, ctx)
            return not any(value.startswith(op) for op in operands)
        elif ptype == "endswith":
            value = self._get_target_value(target, ctx)
            return any(value.endswith(op) for op in operands)
        elif ptype == "contains_at_position":
            value = self._get_target_value(target, ctx)
            position = pred["operation"]
            if position == "middle" and len(value) >= 3:
                return any(op in value[1:-1] for op in operands)
            return False
        elif ptype == "contains_any":
            value = self._get_target_value(target, ctx)
            return any(op in value for op in operands)
        elif ptype == "not_contains_any":
            value = self._get_target_value(target, ctx)
            return not any(op in value for op in operands)
        elif ptype == "equals":
            # target في الشَّكل "field1_vs_field2"
            a, b = self._get_two_fields(target, ctx)
            if not a or not b:
                return False
            return a == b
        elif ptype == "not_equals":
            a, b = self._get_two_fields(target, ctx)
            if not a or not b:
                return False
            return a != b
        elif ptype == "is_empty":
            value = self._get_target_value(target, ctx)
            return not value
        return False

    def _get_target_value(self, target: str, ctx: dict) -> str:
        """يَجلِب قِيمَة الحَقل مِن الـ context."""
        return ctx.get(target, "")

    def _get_two_fields(self, target: str, ctx: dict) -> tuple[str, str]:
        """يَفهَم target بِالشَّكل 'field1_vs_field2'."""
        if "_vs_" not in target:
            return "", ""
        a_field, b_field = target.split("_vs_", 1)
        return ctx.get(a_field, ""), ctx.get(b_field, "")

    def evaluate_condition(self, condition: str, ctx: dict) -> bool:
        """يُقَيِّم condition (AND-joined atoms)."""
        if not condition:
            return False
        atoms = [a.strip() for a in condition.split("AND")]
        return all(self.evaluate(a, ctx) for a in atoms)


# Singletons
_ISSUE_ENGINE: PredicateEngine | None = None
_CONSTRUCTION_ENGINE: PredicateEngine | None = None


def get_issue_predicate_engine() -> PredicateEngine:
    global _ISSUE_ENGINE
    if _ISSUE_ENGINE is None:
        path = Path(__file__).resolve().parent / "data" / "contracts" / "rules" / "issue_atoms.csv"
        _ISSUE_ENGINE = PredicateEngine(path)
    return _ISSUE_ENGINE


def get_construction_predicate_engine() -> PredicateEngine:
    global _CONSTRUCTION_ENGINE
    if _CONSTRUCTION_ENGINE is None:
        path = Path(__file__).resolve().parent / "data" / "contracts" / "rules" / "construction_predicates.csv"
        _CONSTRUCTION_ENGINE = PredicateEngine(path)
    return _CONSTRUCTION_ENGINE


if __name__ == "__main__":
    eng = get_issue_predicate_engine()
    ctx = {"word": "سَأَلَ", "audited_root": "سءل", "engine_root": "سال"}
    for pid in ["word_starts_with_seen", "audited_root_not_starts_with_seen"]:
        print(f"  {pid}: {eng.evaluate(pid, ctx)}")
