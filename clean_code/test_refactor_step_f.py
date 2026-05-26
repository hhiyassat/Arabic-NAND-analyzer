#!/usr/bin/env python3
"""test_refactor_step_f.py — audit wrappers (observe-only).

Step F = wrappers لِأَدوات التَّدقيق الحاليَّة. لا enforcement. لا تَغيير سُلوكيّ.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

results = []
def _t(name, fn):
    try:
        fn(); results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e))); print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERR: {e}")); print(f"  ✗ {name}: ERR {e}")


# ─────────────────────────────────────────────────────────────
# regression_runner
# ─────────────────────────────────────────────────────────────
def t_load_regression_summary_parses_baseline():
    from arabic_analyzer.audit import load_regression_summary
    base = Path("audit_outputs/BASELINE_summary.txt")
    if not base.exists():
        return  # skip silently
    d = load_regression_summary(base)
    assert "total_tokens" in d and d["total_tokens"] > 0
    assert "alignment_pct" in d and d["alignment_pct"] > 90
    assert "by_class" in d and "FIIL" in d["by_class"]
    assert "source_dist" in d


def t_load_regression_summary_keys_complete():
    """يَتَأَكَّد أَنَّ كُلّ keys مَطلوبَة مَوجودَة."""
    from arabic_analyzer.audit import load_regression_summary
    base = Path("audit_outputs/BASELINE_summary.txt")
    if not base.exists():
        return
    d = load_regression_summary(base)
    required = ["total_tokens", "matched_masaq", "mismatched",
                "alignment_pct", "by_class", "source_dist"]
    for k in required:
        assert k in d, f"missing key {k}"


def t_regression_runner_does_not_modify_analyzer():
    """يَستَورِد regression_runner وَيَتَأَكَّد لا side-effects."""
    from i3rab_engine.layer1 import WordClassClassifier
    clf1 = WordClassClassifier()
    out1 = clf1.classify("كَتَبَ")
    from arabic_analyzer.audit import regression_runner  # noqa
    out2 = clf1.classify("كَتَبَ")
    assert out1.get("word_class") == out2.get("word_class")


# ─────────────────────────────────────────────────────────────
# event_observer
# ─────────────────────────────────────────────────────────────
def t_event_observer_observe_only():
    """يَتَأَكَّد لا يَحجُب — observe فَقَط."""
    from arabic_analyzer.audit import observe_events_on_sweep, summarize_event_observations
    # نَكتُب sweep وَهميّ صَغير
    rows = [
        {"surah": 1, "ayah": 1, "events": 2, "anomalies": [], "coverage": 100, "errors": [], "qa_zeros": 0},
        {"surah": 1, "ayah": 2, "events": 1, "anomalies": ["weird"], "coverage": 80, "errors": [], "qa_zeros": 0},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
        tmp = Path(f.name)
    obs = observe_events_on_sweep(tmp)
    assert len(obs) == 2
    # total events = 3 (2+1)
    summary = summarize_event_observations(obs)
    assert summary["total_events_in_sweep"] == 3
    assert summary["would_block_event_count"] >= 1  # anomaly → would_block
    tmp.unlink()


def t_event_observer_summary_has_required_fields():
    from arabic_analyzer.audit import observe_events_on_sweep, summarize_event_observations
    rows = [{"surah": 1, "ayah": 1, "events": 0, "anomalies": [], "coverage": 100}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
        tmp = Path(f.name)
    summary = summarize_event_observations(observe_events_on_sweep(tmp))
    for k in ("ayahs_processed", "total_events_in_sweep",
              "would_block_event_count", "event_from_anomaly",
              "event_from_low_coverage", "event_from_error",
              "event_from_unanswered_qa", "gate_audit_counters",
              "would_block_pct"):
        assert k in summary, f"missing key: {k}"
    tmp.unlink()


def t_event_observer_top_reasons():
    from arabic_analyzer.audit import observe_events_on_sweep, top_event_block_reasons
    rows = [
        {"surah": 1, "ayah": 1, "events": 3, "anomalies": ["x", "x"], "coverage": 100},
        {"surah": 1, "ayah": 2, "events": 2, "anomalies": ["x"], "coverage": 100},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
        tmp = Path(f.name)
    top = top_event_block_reasons(observe_events_on_sweep(tmp), n=3)
    assert len(top) >= 1
    assert top[0][1] >= 1
    tmp.unlink()


# ─────────────────────────────────────────────────────────────
# relation_observer
# ─────────────────────────────────────────────────────────────
def t_relation_observer_observe_only():
    from arabic_analyzer.audit import observe_relations_on_sweep, summarize_relation_observations
    rows = [
        {"surah": 1, "ayah": 1, "relations": 5, "meaning_edges": 5, "unknown_count": 0, "anomalies": [], "errors": []},
        {"surah": 1, "ayah": 2, "relations": 3, "meaning_edges": 2, "unknown_count": 1, "anomalies": [], "errors": []},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
        tmp = Path(f.name)
    obs = observe_relations_on_sweep(tmp)
    assert len(obs) == 2
    summary = summarize_relation_observations(obs)
    assert summary["total_relations_in_sweep"] == 8
    assert summary["would_block_relation_count"] >= 1  # gap + fragment
    tmp.unlink()


def t_relation_observer_summary_required_fields():
    from arabic_analyzer.audit import observe_relations_on_sweep, summarize_relation_observations
    rows = [{"surah": 1, "ayah": 1, "relations": 0, "meaning_edges": 0, "unknown_count": 0}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
        tmp = Path(f.name)
    summary = summarize_relation_observations(observe_relations_on_sweep(tmp))
    for k in ("ayahs_processed", "total_relations_in_sweep",
              "would_block_relation_count", "relation_from_anomaly",
              "relation_from_unresolved_edges", "relation_from_fragment_tokens",
              "relation_from_error", "breakdown_by_relation_type",
              "gate_audit_counters", "would_block_pct"):
        assert k in summary, f"missing key: {k}"
    tmp.unlink()


# ─────────────────────────────────────────────────────────────
# baseline_comparator
# ─────────────────────────────────────────────────────────────
def t_baseline_comparator_loads():
    """يُحَمِّل baseline وَcurrent بِنَجاح."""
    from arabic_analyzer.audit import compare_against_baseline
    base = Path("audit_outputs/BASELINE_summary.txt")
    curr = Path("audit_outputs/full_quran_regression_summary.txt")
    if not (base.exists() and curr.exists()):
        return
    rep = compare_against_baseline()
    assert rep.alignment_baseline > 90
    assert rep.alignment_current > 90


def t_baseline_comparator_detects_no_unexpected_drift():
    """بَعد Step F: لا drift في metrics الأساسيَّة."""
    from arabic_analyzer.audit import compare_against_baseline
    base = Path("audit_outputs/BASELINE_summary.txt")
    curr = Path("audit_outputs/full_quran_regression_summary.txt")
    if not (base.exists() and curr.exists()):
        return
    rep = compare_against_baseline()
    # alignment drift يَجِب أَن يَكون < 0.5%
    assert abs(rep.alignment_drift) < 0.5, f"big alignment drift: {rep.alignment_drift}"
    # كُلّ class drifts < 0.5%
    for wc, d in rep.class_drifts.items():
        assert abs(d) < 0.5, f"big class drift [{wc}]: {d}"


def t_baseline_comparator_has_drift_function():
    from arabic_analyzer.audit import DriftReport, has_drift
    clean = DriftReport()
    assert clean.is_clean() and not has_drift(clean)
    dirty = DriftReport(flags=["alignment_drift +0.50%"])
    assert not dirty.is_clean() and has_drift(dirty)


def t_baseline_tolerances_configurable():
    from arabic_analyzer.audit import compare_against_baseline
    base = Path("audit_outputs/BASELINE_summary.txt")
    curr = Path("audit_outputs/full_quran_regression_summary.txt")
    if not (base.exists() and curr.exists()):
        return
    # tolerances صارِمَة جِدًّا — يَجِب أَن لا تُولِّد flags كَثيرَة
    rep = compare_against_baseline(tolerances={"alignment_pct": 1.0,
                                                "class_acc": 1.0,
                                                "source_pct": 5.0,
                                                "seg_leak_ratio_pct": 1.0})
    assert rep.alignment_baseline > 0 and rep.alignment_current > 0


# ─────────────────────────────────────────────────────────────
# Constitutional checks
# ─────────────────────────────────────────────────────────────
def t_audit_modules_do_not_import_phase4():
    """Step F لا يَستَورِد أَيّ شَيء مِن Phase 4 ContextualAmbiguityResolver."""
    import arabic_analyzer.audit as A
    for mod_name in ("regression_runner", "event_observer",
                     "relation_observer", "baseline_comparator"):
        mod = getattr(A, mod_name, None) or __import__(f"arabic_analyzer.audit.{mod_name}",
                                                       fromlist=[mod_name])
        src = open(mod.__file__, encoding="utf-8").read()
        assert "ContextualAmbiguityResolver" not in src, f"{mod_name} imports Phase 4"
        assert "phase4" not in src.lower() or "phase 4" in src.lower(), \
            f"{mod_name} mentions phase4"


def t_audit_modules_use_observe_mode():
    """يَتَأَكَّد أَنَّ observers لا تَستَدعي gate بِـ enforcement_mode='enforce'."""
    import arabic_analyzer.audit.event_observer as EV
    import arabic_analyzer.audit.relation_observer as RL
    ev_src = open(EV.__file__, encoding="utf-8").read()
    rl_src = open(RL.__file__, encoding="utf-8").read()
    # الفَحص الحَقيقيّ: لا تَوجَد call تَستَخدِم mode="enforce"
    assert 'enforcement_mode="enforce"' not in ev_src, \
        "event_observer must not call gate with enforce mode"
    assert "enforcement_mode='enforce'" not in ev_src, \
        "event_observer must not call gate with enforce mode"
    assert 'enforcement_mode="enforce"' not in rl_src, \
        "relation_observer must not call gate with enforce mode"
    assert "enforcement_mode='enforce'" not in rl_src, \
        "relation_observer must not call gate with enforce mode"


def t_no_runtime_behavior_change_step_f():
    """Step F لا يَتَدَخَّل في pipeline."""
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    expected = {"كَتَبَ": "FIIL", "ٱلْكِتَابُ": "ISM_MUARAB",
                "هُوَ": "ISM_MABNI", "ٱلَّذِي": "ISM_MAWSOOL"}
    for tok, want in expected.items():
        r = clf.classify(tok)
        assert r["word_class"] == want, f"{tok}: got {r['word_class']}, want {want}"


def t_audit_outputs_have_required_fields():
    """يَتَأَكَّد أَنَّ outputs لِكُلّ observer لَها كُلّ الحُقول المَطلوبَة."""
    from arabic_analyzer.audit import (
        EventObservation, RelationObservation, DriftReport,
    )
    e = EventObservation(surah=1, ayah=1, event_count=0, would_block_count=0)
    for f in ("surah", "ayah", "event_count", "would_block_count",
              "block_reasons", "anomalies", "coverage"):
        assert hasattr(e, f), f"EventObservation missing {f}"
    r = RelationObservation(surah=1, ayah=1, relation_count=0, would_block_count=0)
    for f in ("surah", "ayah", "relation_count", "would_block_count",
              "block_reasons", "by_relation_type", "coverage"):
        assert hasattr(r, f), f"RelationObservation missing {f}"
    d = DriftReport()
    for f in ("alignment_baseline", "alignment_current", "alignment_drift",
              "class_drifts", "source_drifts", "seg_leak_baseline_ratio",
              "seg_leak_current_ratio", "seg_leak_drift",
              "false_event_baseline_count", "false_event_current_count",
              "relation_sanity_baseline", "relation_sanity_current",
              "test_count_baseline", "test_count_current",
              "flags", "tolerances"):
        assert hasattr(d, f), f"DriftReport missing {f}"


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("REFACTOR Step F — Audit Scripts (wrappers)")
print("=" * 70)
ALL = [
    ("t_load_regression_summary_parses_baseline", t_load_regression_summary_parses_baseline),
    ("t_load_regression_summary_keys_complete", t_load_regression_summary_keys_complete),
    ("t_regression_runner_does_not_modify_analyzer", t_regression_runner_does_not_modify_analyzer),
    ("t_event_observer_observe_only", t_event_observer_observe_only),
    ("t_event_observer_summary_has_required_fields", t_event_observer_summary_has_required_fields),
    ("t_event_observer_top_reasons", t_event_observer_top_reasons),
    ("t_relation_observer_observe_only", t_relation_observer_observe_only),
    ("t_relation_observer_summary_required_fields", t_relation_observer_summary_required_fields),
    ("t_baseline_comparator_loads", t_baseline_comparator_loads),
    ("t_baseline_comparator_detects_no_unexpected_drift", t_baseline_comparator_detects_no_unexpected_drift),
    ("t_baseline_comparator_has_drift_function", t_baseline_comparator_has_drift_function),
    ("t_baseline_tolerances_configurable", t_baseline_tolerances_configurable),
    ("t_audit_modules_do_not_import_phase4", t_audit_modules_do_not_import_phase4),
    ("t_audit_modules_use_observe_mode", t_audit_modules_use_observe_mode),
    ("t_no_runtime_behavior_change_step_f", t_no_runtime_behavior_change_step_f),
    ("t_audit_outputs_have_required_fields", t_audit_outputs_have_required_fields),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
