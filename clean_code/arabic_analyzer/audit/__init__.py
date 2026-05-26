"""arabic_analyzer.audit — أَدوات التَّدقيق (Step F: wrappers فَقَط).

لا تُغَيِّر سُلوك التَّحليل. كُلّ المُكَوِّنات observe-only.

  - regression_runner: يَلُفّ full_quran_audit + regression_harness
  - event_observer:    يُشَغِّل EventGate في observe mode على sweep records
  - relation_observer: يُشَغِّل RelationGate في observe mode على sweep records
  - baseline_comparator: يُقارِن metrics ضِدّ BASELINE_*.csv
"""
from .regression_runner import (
    run_regression_sample, run_regression_full,
    load_regression_summary,
)
from .event_observer import (
    EventObservation, observe_events_on_sweep,
    summarize_event_observations, top_event_block_reasons,
)
from .relation_observer import (
    RelationObservation, observe_relations_on_sweep,
    summarize_relation_observations, top_relation_block_reasons,
)
from .baseline_comparator import (
    DriftReport, compare_against_baseline, has_drift,
)

__all__ = [
    "run_regression_sample", "run_regression_full", "load_regression_summary",
    "EventObservation", "observe_events_on_sweep",
    "summarize_event_observations", "top_event_block_reasons",
    "RelationObservation", "observe_relations_on_sweep",
    "summarize_relation_observations", "top_relation_block_reasons",
    "DriftReport", "compare_against_baseline", "has_drift",
]
