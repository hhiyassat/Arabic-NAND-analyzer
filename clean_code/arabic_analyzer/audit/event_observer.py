"""event_observer.py — observe-only event audit (Step F).

يَستَخدِم EventGate مِن Step E بِـ enforcement_mode="observe":
  • لا يَحجُب أَيّ event
  • يُسَجِّل ما كان سَيُحجَب وَلِماذا

يَقرأ sweep_v*.jsonl (مُلَخَّصات الـbatch sweeps السابِقَة) ويُحَلِّل
events فيها مَع gate verdicts.

NOTE: في sweep records الحالِيَّة، الـevents مُجَرَّد counts. هذا الـ
observer يَفحَص الإِشارات المُتاحَة (count, fiil_count, anomalies) ويُسَجِّل
أَنماط ما كانَ سَيُحجَب لَو تَوَفَّرَت per-event metadata.

API:
  • observe_events_on_sweep(jsonl_path) -> list[EventObservation]
  • summarize_event_observations(observations) -> dict
  • top_event_block_reasons(observations, n=5) -> list[tuple[str,int]]
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from ..events import can_emit_event, reset_event_audit, get_event_audit
from ..core import Decision


@dataclass
class EventObservation:
    """نَتيجَة observe لِحَدَث واحِد (أَو مَجموعَة أَحداث في آية)."""
    surah: int
    ayah: int
    event_count: int            # كَم event صَدَر فِعلًا
    would_block_count: int      # كَم كانَ سَيُحجَب لَو enforce
    block_reasons: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    coverage: float = 0.0


def _gate_check_proxy(d: dict) -> tuple[int, list[str]]:
    """proxy: في غِياب per-event metadata في sweep records،
    نَستَخدِم إِشارات الـsweep لِنَستَنتِج would_block.

    Signals:
      - anomalies غَير فارِغَة → يَزيد would_block
      - coverage < 50% → عَدَم اكتِمال → would_block
      - errors → would_block
      - qa_zeros > 0 → unanswered → would_block

    NOTE: هذا proxy لِلـsweeps السابِقَة. عِندَ تَكامُل gate مَع pipeline
    سَتُحَلَّ الـevents مُباشَرَةً عَبر can_emit_event().
    """
    reasons: list[str] = []
    n_events = d.get("events", 0)
    would_block = 0
    if d.get("anomalies"):
        would_block += min(n_events, len(d["anomalies"]))
        for a in d["anomalies"]:
            reasons.append(f"anomaly:{a}")
    cov = d.get("coverage", 100.0)
    if cov < 50.0 and n_events:
        would_block += 1
        reasons.append(f"coverage_low:{cov:.0f}%")
    if d.get("errors"):
        would_block += min(n_events, len(d["errors"]))
        for e in d["errors"]:
            reasons.append(f"error:{str(e)[:40]}")
    qa_zeros = d.get("qa_zeros", 0)
    if qa_zeros > 0:
        reasons.append(f"qa_zeros:{qa_zeros}")
    would_block = min(would_block, n_events)
    return would_block, reasons


def observe_events_on_sweep(jsonl_path: Path) -> list[EventObservation]:
    """يَقرأ sweep JSONL ويُنشِئ EventObservation لِكُلّ سَجِل."""
    p = Path(jsonl_path)
    if not p.exists():
        raise FileNotFoundError(p)

    # reset gate audit counters لِجَلسَة نَظيفَة
    reset_event_audit()

    observations: list[EventObservation] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            wb, reasons = _gate_check_proxy(d)
            observations.append(EventObservation(
                surah=int(d.get("surah", 0)),
                ayah=int(d.get("ayah", 0)),
                event_count=int(d.get("events", 0)),
                would_block_count=wb,
                block_reasons=reasons,
                anomalies=list(d.get("anomalies", [])),
                coverage=float(d.get("coverage", 0.0)),
            ))
    return observations


def summarize_event_observations(obs: Iterable[EventObservation]) -> dict:
    """يُلَخِّص list[EventObservation] إلى metrics dict."""
    obs = list(obs)
    total_events = sum(o.event_count for o in obs)
    would_block = sum(o.would_block_count for o in obs)
    # tally reasons
    reason_counts: Counter = Counter()
    for o in obs:
        for r in o.block_reasons:
            # تَصنيف القَواعِد إلى فِئات
            if r.startswith("anomaly:"):
                cat = "from_anomaly"
            elif r.startswith("coverage_low"):
                cat = "from_low_coverage"
            elif r.startswith("error:"):
                cat = "from_error"
            elif r.startswith("qa_zeros"):
                cat = "from_unanswered_qa"
            else:
                cat = "other"
            reason_counts[cat] += 1

    # دَمج audit counters مِن EventGate نَفسه (إِن وُجِدَت events فُحِصَت)
    gate_audit = get_event_audit()

    return {
        "ayahs_processed": len(obs),
        "total_events_in_sweep": total_events,
        "would_block_event_count": would_block,
        "event_from_anomaly": reason_counts.get("from_anomaly", 0),
        "event_from_low_coverage": reason_counts.get("from_low_coverage", 0),
        "event_from_error": reason_counts.get("from_error", 0),
        "event_from_unanswered_qa": reason_counts.get("from_unanswered_qa", 0),
        "gate_audit_counters": gate_audit,
        "would_block_pct": (would_block / max(total_events, 1)) * 100,
    }


def top_event_block_reasons(obs: Iterable[EventObservation],
                            n: int = 5) -> list[tuple[str, int]]:
    """يُرجِع أَكثَر n reasons تَكرارًا."""
    c: Counter = Counter()
    for o in obs:
        for r in o.block_reasons:
            c[r] += 1
    return c.most_common(n)


__all__ = [
    "EventObservation",
    "observe_events_on_sweep",
    "summarize_event_observations",
    "top_event_block_reasons",
]
