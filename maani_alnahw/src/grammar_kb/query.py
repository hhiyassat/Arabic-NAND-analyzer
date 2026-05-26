"""grammar_kb/query.py — استِعلام عَن قاعِدَة المَعرِفَة.

يُحَمِّل rule_cards.jsonl + construction_rules.jsonl + topics.jsonl
وَ يُتيح بَحثًا بِـ:
  • lemma → list[RuleCard]
  • construction_id → ConstructionRule
  • topic_id → list[RuleCard]
  • find_by_text(query) → list (مُطابَقَة جُزئيَّة)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class GrammarKB:
    """قاعِدَة مَعرِفَة قابِلَة لِلِاستِعلام."""

    def __init__(self, processed_dir: str | Path):
        self.dir = Path(processed_dir)
        self._rules: list[dict] = []
        self._constructions: list[dict] = []
        self._topics: list[dict] = []
        self._examples: list[dict] = []
        self._opinions: list[dict] = []
        self._load()
        self._build_indices()

    def _load(self):
        def _read(fname):
            p = self.dir / fname
            if not p.exists():
                return []
            out = []
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return out

        self._rules = _read("rule_cards.jsonl")
        self._constructions = _read("construction_rules.jsonl")
        self._topics = _read("topics.jsonl")
        self._examples = _read("examples.jsonl")
        self._opinions = _read("opinions.jsonl")

    def _build_indices(self):
        # lemma → rules
        self._by_lemma: dict[str, list[dict]] = {}
        for r in self._rules:
            for lemma in (r.get("trigger") or {}).get("lemmas", []):
                self._by_lemma.setdefault(lemma, []).append(r)
        # construction_id → construction rule
        self._by_construction: dict[str, dict] = {}
        for c in self._constructions:
            cid = c.get("construction_id")
            if cid:
                self._by_construction[cid] = c
        # topic_id → rules
        self._by_topic: dict[str, list[dict]] = {}
        for r in self._rules:
            tid = r.get("topic_id")
            if tid:
                self._by_topic.setdefault(tid, []).append(r)

    # ── API ────────────────────────────────────────────────────────────────

    def by_lemma(self, lemma: str) -> list[dict]:
        """يُرجِع قَواعِد مُرتَبِطَة بِفِعل (مثل ظنّ)."""
        return self._by_lemma.get(lemma, [])

    def by_construction(self, construction_id: str) -> Optional[dict]:
        """يُرجِع قاعِدَة تَركيب (مثل ZANN_WA_AKHAWATUHA)."""
        return self._by_construction.get(construction_id)

    def by_topic(self, topic_id: str) -> list[dict]:
        return self._by_topic.get(topic_id, [])

    def all_constructions(self) -> list[dict]:
        return list(self._constructions)

    def all_rules(self) -> list[dict]:
        return list(self._rules)

    def all_topics(self) -> list[dict]:
        return list(self._topics)

    def find_by_text(self, query: str) -> list[dict]:
        """بَحث جُزئيّ في عَناوين القَواعِد وَ المَواضيع."""
        results = []
        for r in self._rules:
            if query in r.get("title", "") or query in (r.get("semantic_effect", {}).get("description") or ""):
                results.append({"type": "rule", "record": r})
        for t in self._topics:
            if query in t.get("title", ""):
                results.append({"type": "topic", "record": t})
        return results

    def examples_for_rule(self, rule_id: str) -> list[dict]:
        return [e for e in self._examples if e.get("rule_id") == rule_id]

    def opinions_for_topic(self, topic_id: str) -> list[dict]:
        return [o for o in self._opinions if o.get("topic_id") == topic_id]

    def stats(self) -> dict:
        return {
            "rules": len(self._rules),
            "constructions": len(self._constructions),
            "topics": len(self._topics),
            "examples": len(self._examples),
            "opinions": len(self._opinions),
        }
