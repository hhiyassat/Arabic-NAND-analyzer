"""test_project_closure_batch_a_l8_shart_jawab.py — Closure Batch A L8 tests.

Binding scope (per RULE_LOCK 0854059):

- L8 must answer the canonical query "ما جَواب الشَّرط؟" for verse 2:282
  by consuming the existing L4/L7 edges produced by Phase 5 Batch B
  (condition_tool_of, jawab_shart_of).
- Pure consumption: no detection, no token scan, no Phase 5 call.
- Certificate-or-Zero discipline: if no jawab_shart_of edge, or if the
  edge is Hypothesis, return Zero (never Hypothesis from this strategy).
- L4/L7 metrics for 2:282 must remain unchanged.
- Existing L8 question answers for 2:282 must remain unchanged.

Tests:
  P1-P6  positive (edge present, Certificate, surfaces flow through)
  N1-N2  negative (no edge → Zero; Hypothesis edge → Zero)
  R1-R2  regression (L4/L7 metrics unchanged; existing L8 answers unchanged)
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# Load the canonical 2:282 text from the project's Quran source — using
# any other transcription risks subtle diacritic drift that changes the
# graph (R1 regression baselines are anchored to the canonical text).
def _load_2_282() -> str:
    from analyze_verse_v3 import load_verse
    text = load_verse("2:282")
    if not text:
        raise RuntimeError("could not load canonical 2:282 from Quran source")
    return text


_2_282_TEXT = _load_2_282()

_CANONICAL_Q = "ما جَواب الشَّرط؟"


# ── Fake graph plumbing for N1 / N2 ────────────────────────────────
class _FakeNode:
    def __init__(self, surface):
        self.surface = surface


class _FakeEdge:
    def __init__(self, edge_type, source, target,
                 proof_kind="Certificate", operator=""):
        self.edge_type = edge_type
        self.source = source
        self.target = target
        self.proof_kind = proof_kind
        self.operator = operator
        self.edge_id = f"fake_{edge_type}_{source}_{target}"


class _FakeGraph:
    def __init__(self, edges=None, nodes=None):
        self.edges = edges or []
        self._nodes = nodes or {}

    def get_node(self, node_id):
        return self._nodes.get(node_id)


def _make_query():
    """Construct a parsed Query object matching the canonical question."""
    from reasoning_engine import ReasoningEngine
    return ReasoningEngine().parse_query(_CANONICAL_Q)


# ── P1 ───────────────────────────────────────────────────────────
def t_l8_answers_jawab_shart_for_2_282():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    assert a.answer, (
        f"answer text is empty; kind={a.kind!r}, reason={a.rejected_reason!r}"
    )


# ── P2 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_answer_contains_faktubu():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    assert "فَٱكْتُبُوهُ" in (a.answer or ""), (
        f"answer must contain فَٱكْتُبُوهُ; got {a.answer!r}"
    )


# ── P3 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_links_faktubu_to_tadayantum():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    ans = a.answer or ""
    assert "تَدَايَنتُم" in ans, (
        f"answer must mention تَدَايَنتُم (condition verb); got {ans!r}"
    )
    assert ("مَربوط" in ans or "بِفِعل الشَّرط" in ans), (
        f"answer must use the linkage phrasing (مَربوط / بِفِعل الشَّرط); "
        f"got {ans!r}"
    )


# ── P4 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_answer_is_certificate():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    assert a.kind == "Certificate", (
        f"answer kind must be Certificate; got {a.kind!r} "
        f"(reason={a.rejected_reason!r})"
    )


# ── P5 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_includes_idha_when_available():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    assert "إِذَا" in (a.answer or ""), (
        f"answer must surface إِذَا (condition tool); got {a.answer!r}"
    )


# ── P6 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_records_fa_marker_when_available():
    from reasoning_engine import ReasoningEngine
    a = ReasoningEngine().answer(_2_282_TEXT, _CANONICAL_Q)
    ans = a.answer or ""
    assert "فاء الجَواب" in ans and "فَ" in ans, (
        f"answer must record فاء الجَواب فَ marker; got {ans!r}"
    )


# ── N1 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_zero_when_no_edge():
    """No jawab_shart_of edge in graph → Zero. No fabrication."""
    from reasoning_engine import ReasoningEngine
    engine = ReasoningEngine()
    query = _make_query()
    fake_graph = _FakeGraph(edges=[], nodes={})
    a = engine._find_jawab_shart(query, fake_graph, _CANONICAL_Q)
    assert a.kind == "Zero", (
        f"absent edge must yield Zero; got {a.kind!r}"
    )
    assert "فَٱكْتُبُوهُ" not in (a.answer or ""), (
        f"answer must NOT fabricate jawab surface when edge absent; "
        f"got {a.answer!r}"
    )
    assert a.rejected_reason, "Zero answer must carry a rejected_reason"


# ── N2 ───────────────────────────────────────────────────────────
def t_l8_jawab_shart_zero_when_edge_is_hypothesis():
    """jawab_shart_of edge present but Hypothesis → Zero (Certificate-only)."""
    from reasoning_engine import ReasoningEngine
    engine = ReasoningEngine()
    query = _make_query()
    nodes = {
        "t9": _FakeNode("فَٱكْتُبُوهُ"),
        "t4": _FakeNode("تَدَايَنتُم"),
    }
    edges = [_FakeEdge(
        "jawab_shart_of", source="t9", target="t4",
        proof_kind="Hypothesis", operator="فَ",
    )]
    fake_graph = _FakeGraph(edges=edges, nodes=nodes)
    a = engine._find_jawab_shart(query, fake_graph, _CANONICAL_Q)
    assert a.kind == "Zero", (
        f"Hypothesis edge must yield Zero (Certificate-only discipline); "
        f"got {a.kind!r}"
    )


# ── R1 ───────────────────────────────────────────────────────────
def t_2_282_l4_l7_metrics_unchanged_after_batch_a():
    """L4/L7 metrics for 2:282 must remain stable:
    nodes 135, links 43, Entropy 0.0, consistency True."""
    try:
        from meaning_assembler import MeaningAssembler
    except ImportError:
        print("  [skipped - meaning_assembler unavailable]", end=" ")
        return
    graph = MeaningAssembler().assemble(_2_282_TEXT)
    # Use stats() — same source the analyze_verse_v3 display reads;
    # raw len(graph.edges) may include internal entries not shown.
    s = graph.stats()
    n_nodes = s["nodes"]
    n_edges = s["edges"]
    entropy = graph.entropy
    consistent = graph.is_consistent
    assert n_nodes == 135, f"L7 nodes drifted: {n_nodes} != 135"
    assert n_edges == 43, f"L7 links drifted: {n_edges} != 43"
    assert entropy == 0.0, f"L7 Entropy must remain 0.0; got {entropy!r}"
    assert consistent is True, (
        f"L7 consistency must remain True (نَعَم); got {consistent!r}"
    )


# ── R2 ───────────────────────────────────────────────────────────
def t_2_282_other_l8_questions_unchanged():
    """The 7 pre-Batch-A L8 questions for 2:282 must produce their
    existing ProofKind values; Batch A only adds a new question."""
    try:
        from reasoning_engine import ReasoningEngine
    except ImportError:
        print("  [skipped - reasoning_engine unavailable]", end=" ")
        return
    eng = ReasoningEngine()
    expected = [
        ("مَن الفاعِل؟", "Hypothesis"),
        ("ماذا حَدَث؟", "Hypothesis"),
        ("أَين حَدَث؟", "Zero"),
        ("متى حَدَث؟", "Certificate"),
        ("ما تَسَلسُل الأَحداث؟", "Hypothesis"),
        ("إلى ماذا تَحَوَّلَ شَيء؟", "Zero"),
        ("ما تَفسير هذه الآيَة؟", "Zero"),
    ]
    bad = []
    for q, want in expected:
        a = eng.answer(_2_282_TEXT, q)
        if a.kind != want:
            bad.append((q, a.kind, want))
    assert not bad, (
        f"some existing L8 question answers regressed: "
        f"{[(q, got, want) for q, got, want in bad]}"
    )


# ── Driver ────────────────────────────────────────────────────────
results = []


def _run(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  PASS {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  FAIL {name}")
        first_line = str(e).splitlines()[0] if str(e) else ""
        print(f"      {first_line}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"ERR: {e}"))
        print(f"  FAIL {name}: ERR {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("Closure Batch A — L8 SHART_JAWAB Consumption")
    print("=" * 70)
    ALL = [
        ("P1 t_l8_answers_jawab_shart_for_2_282",
         t_l8_answers_jawab_shart_for_2_282),
        ("P2 t_l8_jawab_shart_answer_contains_faktubu",
         t_l8_jawab_shart_answer_contains_faktubu),
        ("P3 t_l8_jawab_shart_links_faktubu_to_tadayantum",
         t_l8_jawab_shart_links_faktubu_to_tadayantum),
        ("P4 t_l8_jawab_shart_answer_is_certificate",
         t_l8_jawab_shart_answer_is_certificate),
        ("P5 t_l8_jawab_shart_includes_idha_when_available",
         t_l8_jawab_shart_includes_idha_when_available),
        ("P6 t_l8_jawab_shart_records_fa_marker_when_available",
         t_l8_jawab_shart_records_fa_marker_when_available),
        ("N1 t_l8_jawab_shart_zero_when_no_edge",
         t_l8_jawab_shart_zero_when_no_edge),
        ("N2 t_l8_jawab_shart_zero_when_edge_is_hypothesis",
         t_l8_jawab_shart_zero_when_edge_is_hypothesis),
        ("R1 t_2_282_l4_l7_metrics_unchanged_after_batch_a",
         t_2_282_l4_l7_metrics_unchanged_after_batch_a),
        ("R2 t_2_282_other_l8_questions_unchanged",
         t_2_282_other_l8_questions_unchanged),
    ]
    for nm, fn in ALL:
        _run(nm, fn)
    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Result: {passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)
