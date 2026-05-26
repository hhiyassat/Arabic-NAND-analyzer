"""relation_observer.py — observe-only relation audit (Step F).

يَستَخدِم RelationGate مِن Step E بِـ enforcement_mode="observe":
  • لا يَحجُب أَيّ relation
  • يُسَجِّل ما كان سَيُحجَب وَلِماذا

API:
  • observe_relations_on_sweep(jsonl_path) -> list[RelationObservation]
  • summarize_relation_observations(observations) -> dict
  • top_relation_block_reasons(observations, n=5) -> list[tuple[str,int]]
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..relations import can_emit_relation, reset_relation_audit, get_relation_audit
from ..core import Decision


@dataclass
class RelationObservation:
    """نَتيجَة observe لِعَلاقات آيَة."""
    surah: int
    ayah: int
    relation_count: int
    would_block_count: int
    block_reasons: list[str] = field(default_factory=list)
    by_relation_type: dict = field(default_factory=dict)
    coverage: float = 0.0


def _gate_check_proxy(d: dict) -> tuple[int, list[str], dict]:
    """proxy: في غِياب per-relation metadata في sweep records،
    نَستَخدِم إِشارات الـsweep لِنَستَنتِج would_block.

    Signals:
      - anomalies → block proportional count
      - meaning_edges < relations → نَقص graph → block
      - errors → block
      - unknown_count كَبير → fragments → block
    """
    reasons: list[str] = []
    n_rel = d.get("relations", 0)
    would_block = 0
    by_type: dict = {}

    if d.get("anomalies"):
        would_block += min(n_rel, len(d["anomalies"]))
        for a in d["anomalies"]:
            reasons.append(f"anomaly:{a}")

    n_edges = d.get("meaning_edges", n_rel)
    if n_edges < n_rel:
        gap = n_rel - n_edges
        would_block += gap
        reasons.append(f"unresolved_edges:{gap}")

    unk = d.get("unknown_count", 0)
    if unk > 0:
        would_block += min(n_rel, unk)
        reasons.append(f"fragment_tokens:{unk}")

    if d.get("errors"):
        would_block += min(n_rel, len(d["errors"]))
        for e in d["errors"]:
            reasons.append(f"error:{str(e)[:40]}")

    would_block = min(would_block, n_rel)
    # by_relation_type proxy: في sweeps الحالِيَّة لا يُحفَظ النَّوع
    # نَترُك dict فارِغ حَتَّى يَتَكامَل gate مَع pipeline
    return would_block, reasons, by_type


def observe_relations_on_sweep(jsonl_path: Path) -> list[RelationObservation]:
    """يَقرأ sweep JSONL ويُنشِئ RelationObservation لِكُلّ سَجِل."""
    p = Path(jsonl_path)
    if not p.exists():
        raise FileNotFoundError(p)

    reset_relation_audit()
    observations: list[RelationObservation] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            wb, reasons, by_type = _gate_check_proxy(d)
            observations.append(RelationObservation(
                surah=int(d.get("surah", 0)),
                ayah=int(d.get("ayah", 0)),
                relation_count=int(d.get("relations", 0)),
                would_block_count=wb,
                block_reasons=reasons,
                by_relation_type=by_type,
                coverage=float(d.get("coverage", 0.0)),
            ))
    return observations


def summarize_relation_observations(obs: Iterable[RelationObservation]) -> dict:
    """يُلَخِّص list[RelationObservation] إلى metrics dict."""
    obs = list(obs)
    total_relations = sum(o.relation_count for o in obs)
    would_block = sum(o.would_block_count for o in obs)

    reason_counts: Counter = Counter()
    for o in obs:
        for r in o.block_reasons:
            if r.startswith("anomaly:"):
                cat = "from_anomaly"
            elif r.startswith("unresolved_edges"):
                cat = "from_unresolved_edges"
            elif r.startswith("fragment_tokens"):
                cat = "from_fragment_tokens"
            elif r.startswith("error:"):
                cat = "from_error"
            else:
                cat = "other"
            reason_counts[cat] += 1

    # by-relation-type breakdown
    type_counts: Counter = Counter()
    for o in obs:
        for t, n in o.by_relation_type.items():
            type_counts[t] += n

    gate_audit = get_relation_audit()

    return {
        "ayahs_processed": len(obs),
        "total_relations_in_sweep": total_relations,
        "would_block_relation_count": would_block,
        "relation_from_anomaly": reason_counts.get("from_anomaly", 0),
        "relation_from_unresolved_edges": reason_counts.get("from_unresolved_edges", 0),
        "relation_from_fragment_tokens": reason_counts.get("from_fragment_tokens", 0),
        "relation_from_error": reason_counts.get("from_error", 0),
        "breakdown_by_relation_type": dict(type_counts),
        "gate_audit_counters": gate_audit,
        "would_block_pct": (would_block / max(total_relations, 1)) * 100,
    }


def top_relation_block_reasons(obs: Iterable[RelationObservation],
                               n: int = 5) -> list[tuple[str, int]]:
    """يُرجِع أَكثَر n reasons تَكرارًا."""
    c: Counter = Counter()
    for o in obs:
        for r in o.block_reasons:
            c[r] += 1
    return c.most_common(n)


__all__ = [
    "RelationObservation",
    "observe_relations_on_sweep",
    "summarize_relation_observations",
    "top_relation_block_reasons",
]
