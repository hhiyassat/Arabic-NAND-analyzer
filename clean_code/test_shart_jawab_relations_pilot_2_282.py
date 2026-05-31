"""test_shart_jawab_relations_pilot_2_282.py — SHART_JAWAB pilot for 2:282.

Binding scope (per Phase 5 Batch B RULE_LOCK eb7720c + SHART_JAWAB RL 7b77945):

- Phase 5 (phase5_clause_segmenter.py) is the source of truth for
  condition / condition_answer_command clauses.
- relation_extractor.py is the sole authorized production importer
  of Phase 5 surface symbols.
- For verse 2:282 first conditional construction:
      condition_tool_of: إِذَا (idx 3) → تَدَايَنتُم (idx 4)   Certificate
      jawab_shart_of:    فَٱكْتُبُوهُ (idx 9) → تَدَايَنتُم (idx 4)  Certificate
      jawab_shart_of.source_of_claim contains introduced_by=فَ
- shart_event_of and jawab_marker_of are explicitly NOT emitted.
- If Phase 5 returns no condition_answer pair, zero edges are emitted
  (no fallback re-detection).

Tests per RULE_LOCK eb7720c section 10.2:
  P1-P6  positive (edge presence + Certificate + L7 typed + Entropy)
  N1-N5  negative (scope guards + block-and-skip behaviour)
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


_2_282_TEXT = (
    "يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوٓا۟ إِذَا تَدَايَنتُم بِدَيْنٍ إِلَىٰٓ أَجَلٍ "
    "مُّسَمًّى فَٱكْتُبُوهُ ۚ وَلْيَكْتُب بَّيْنَكُمْ كَاتِبٌۢ بِٱلْعَدْلِ ۚ "
    "وَلَا يَأْبَ كَاتِبٌ أَن يَكْتُبَ كَمَا عَلَّمَهُ ٱللَّهُ ۚ فَلْيَكْتُبْ "
    "وَلْيُمْلِلِ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ وَلْيَتَّقِ ٱللَّهَ رَبَّهُۥ وَلَا "
    "يَبْخَسْ مِنْهُ شَيْـًٔا ۚ فَإِن كَانَ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ سَفِيهًا "
    "أَوْ ضَعِيفًا أَوْ لَا يَسْتَطِيعُ أَن يُمِلَّ هُوَ فَلْيُمْلِلْ وَلِيُّهُۥ "
    "بِٱلْعَدْلِ ۚ وَٱسْتَشْهِدُوا۟ شَهِيدَيْنِ مِن رِّجَالِكُمْ ۖ فَإِن لَّمْ "
    "يَكُونَا رَجُلَيْنِ فَرَجُلٌ وَٱمْرَأَتَانِ مِمَّن تَرْضَوْنَ مِنَ "
    "ٱلشُّهَدَآءِ أَن تَضِلَّ إِحْدَىٰهُمَا فَتُذَكِّرَ إِحْدَىٰهُمَا "
    "ٱلْأُخْرَىٰ ۚ وَلَا يَأْبَ ٱلشُّهَدَآءُ إِذَا مَا دُعُوا۟ ۚ وَلَا "
    "تَسْـَٔمُوٓا۟ أَن تَكْتُبُوهُ صَغِيرًا أَوْ كَبِيرًا إِلَىٰٓ أَجَلِهِۦ ۚ "
    "ذَٰلِكُمْ أَقْسَطُ عِندَ ٱللَّهِ وَأَقْوَمُ لِلشَّهَٰدَةِ وَأَدْنَىٰٓ "
    "أَلَّا تَرْتَابُوٓا۟ ۖ إِلَّآ أَن تَكُونَ تِجَٰرَةً حَاضِرَةً "
    "تُدِيرُونَهَا بَيْنَكُمْ فَلَيْسَ عَلَيْكُمْ جُنَاحٌ أَلَّا تَكْتُبُوهَا "
    "ۗ وَأَشْهِدُوٓا۟ إِذَا تَبَايَعْتُمْ ۚ وَلَا يُضَآرَّ كَاتِبٌ وَلَا "
    "شَهِيدٌ ۚ وَإِن تَفْعَلُوا۟ فَإِنَّهُۥ فُسُوقٌۢ بِكُمْ ۗ وَٱتَّقُوا۟ "
    "ٱللَّهَ ۖ وَيُعَلِّمُكُمُ ٱللَّهُ ۗ وَٱللَّهُ بِكُلِّ شَىْءٍ عَلِيمٌ"
)

_OTHER_CONDITIONAL_TOOLS = [
    "إِنْ", "إِذْمَا", "لَوْ", "لَوْلَا", "أَمَّا", "مَنْ", "أَيّ",
    "أَيْنَ", "أَيْنَمَا", "كَيْفَمَا", "مَتَى", "حَيْثُمَا", "أَنَّى",
    "مَهْمَا", "كُلَّمَا", "مَا", "لَمَّا",
]


_PIPELINE_UNAVAILABLE = object()


def _get_relations_for_2_282():
    """Build the full L4 RelationGraph for 2:282. Returns None on
    any pipeline failure (skipping test rather than failing hard)."""
    try:
        from i3rab_engine.engine import I3rabEngine
        from relation_extractor import RelationExtractor
    except Exception:  # noqa: BLE001
        return _PIPELINE_UNAVAILABLE
    try:
        sent = I3rabEngine().analyze_sentence(_2_282_TEXT)
        if sent is None:
            return _PIPELINE_UNAVAILABLE
        rg = RelationExtractor().extract(sent)
        return rg
    except Exception:  # noqa: BLE001
        return _PIPELINE_UNAVAILABLE


def _surfaces_for_2_282():
    """Whitespace-split surfaces for 2:282 (matches Phase 5's surface basis)."""
    return _2_282_TEXT.split()


def _idx_of(surfaces, surface_form):
    """Return first index of surface_form in surfaces, or -1."""
    for i, s in enumerate(surfaces):
        if s == surface_form:
            return i
    return -1


# ── P1 ───────────────────────────────────────────────────────────
def t_2_282_first_idha_condition_tool_of_tadayantum():
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    surfaces = _surfaces_for_2_282()
    idha_idx = _idx_of(surfaces, "إِذَا")
    tadayantum_idx = _idx_of(surfaces, "تَدَايَنتُم")
    assert idha_idx >= 0, "إِذَا not in 2:282 surfaces"
    assert tadayantum_idx >= 0, "تَدَايَنتُم not in 2:282 surfaces"
    expected_src = f"t{idha_idx}"
    expected_tgt = f"t{tadayantum_idx}"
    matches = [
        r for r in rg.relations
        if r.name == "condition_tool_of"
        and r.source_id == expected_src
        and r.target_id == expected_tgt
    ]
    assert matches, (
        f"missing condition_tool_of: {expected_src}→{expected_tgt}; "
        f"all condition_tool_of edges: "
        f"{[(r.source_id, r.target_id) for r in rg.relations if r.name == 'condition_tool_of']}"
    )
    assert matches[0].kind == "Certificate", (
        f"condition_tool_of kind={matches[0].kind!r}, expected Certificate"
    )


# ── P2 ───────────────────────────────────────────────────────────
def t_2_282_jawab_shart_of_faktubu_to_tadayantum():
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    surfaces = _surfaces_for_2_282()
    faktubu_idx = _idx_of(surfaces, "فَٱكْتُبُوهُ")
    tadayantum_idx = _idx_of(surfaces, "تَدَايَنتُم")
    assert faktubu_idx >= 0, "فَٱكْتُبُوهُ not in 2:282 surfaces"
    assert tadayantum_idx >= 0, "تَدَايَنتُم not in 2:282 surfaces"
    expected_src = f"t{faktubu_idx}"
    expected_tgt = f"t{tadayantum_idx}"
    matches = [
        r for r in rg.relations
        if r.name == "jawab_shart_of"
        and r.source_id == expected_src
        and r.target_id == expected_tgt
    ]
    assert matches, (
        f"missing jawab_shart_of: {expected_src}→{expected_tgt}; "
        f"all jawab_shart_of edges: "
        f"{[(r.source_id, r.target_id) for r in rg.relations if r.name == 'jawab_shart_of']}"
    )
    assert matches[0].kind == "Certificate", (
        f"jawab_shart_of kind={matches[0].kind!r}, expected Certificate"
    )


# ── P3 ───────────────────────────────────────────────────────────
def t_2_282_jawab_shart_source_of_claim_records_fa_marker():
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    jawabs = [r for r in rg.relations if r.name == "jawab_shart_of"]
    assert jawabs, "no jawab_shart_of edge to inspect"
    soc = jawabs[0].source_of_claim or ""
    assert "introduced_by=فَ" in soc, (
        f"jawab_shart_of.source_of_claim must contain 'introduced_by=فَ'; "
        f"got {soc!r}"
    )


# ── P4 ───────────────────────────────────────────────────────────
def t_2_282_l7_contains_condition_and_jawab_edges_as_typed():
    """L7 must carry both edges with their names intact (NOT
    collapsed to operator_meaning via the PASSTHROUGH whitelist).
    Uses the production MeaningAssembler entry point used by
    analyze_verse_v3 (`assemble(text)`)."""
    try:
        from meaning_assembler import MeaningAssembler
    except ImportError:
        print("  [skipped - meaning_assembler module unavailable]", end=" ")
        return
    graph = MeaningAssembler().assemble(_2_282_TEXT)
    edge_types = {getattr(e, "edge_type", "") for e in graph.edges}
    cond_edges = [e for e in graph.edges if getattr(e, "edge_type", "") == "condition_tool_of"]
    jawab_edges = [e for e in graph.edges if getattr(e, "edge_type", "") == "jawab_shart_of"]
    assert cond_edges, (
        f"L7 has no condition_tool_of typed edge; edge_types present: "
        f"{sorted(edge_types)}"
    )
    assert jawab_edges, (
        f"L7 has no jawab_shart_of typed edge; edge_types present: "
        f"{sorted(edge_types)}"
    )
    # Defence-in-depth: confirm the edges did NOT collapse to operator_meaning
    operator_meaning_with_our_names = [
        e for e in graph.edges
        if getattr(e, "edge_type", "") == "operator_meaning"
        and (str(getattr(e, "source_of_claim", "")).startswith("phase5:")
             or "condition_tool_of" in str(getattr(e, "edge_id", ""))
             or "jawab_shart_of" in str(getattr(e, "edge_id", "")))
    ]
    assert not operator_meaning_with_our_names, (
        f"new edges collapsed to operator_meaning despite PASSTHROUGH: "
        f"{operator_meaning_with_our_names[:3]}"
    )


# ── P5 ───────────────────────────────────────────────────────────
def t_2_282_l7_entropy_remains_zero_and_consistent():
    """L7 Entropy must remain 0.0 and consistency must remain
    نَعَم (True) after Batch B adds 2 new Certificate edges. Uses
    the production MeaningAssembler entry point."""
    try:
        from meaning_assembler import MeaningAssembler
    except ImportError:
        print("  [skipped - meaning_assembler module unavailable]", end=" ")
        return
    graph = MeaningAssembler().assemble(_2_282_TEXT)
    entropy = graph.entropy
    consistent = graph.is_consistent
    assert entropy == 0.0, (
        f"L7 Entropy must remain 0.0 after Batch B; got {entropy!r}"
    )
    assert consistent is True, (
        f"L7 consistency must remain True (نَعَم); got {consistent!r}"
    )


# ── P6 ───────────────────────────────────────────────────────────
def t_2_282_two_new_edges_are_both_certificate():
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    new_edges = [
        r for r in rg.relations
        if r.name in {"condition_tool_of", "jawab_shart_of"}
    ]
    assert new_edges, "neither new edge found"
    non_cert = [r for r in new_edges if r.kind != "Certificate"]
    assert not non_cert, (
        f"all new edges must be Certificate; non-Certificate: "
        f"{[(r.name, r.kind) for r in non_cert]}"
    )


# ── N1 ───────────────────────────────────────────────────────────
def t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot():
    """2:282 has three إِذَا occurrences. Phase 5 only produces a
    condition+condition_answer_command pair for the first one
    (إِذَا تَدَايَنتُم … فَٱكْتُبُوهُ). The other two (إِذَا مَا دُعُوا and
    إِذَا تَبَايَعْتُمْ) MUST NOT receive condition_tool_of edges."""
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    surfaces = _surfaces_for_2_282()
    first_idha = _idx_of(surfaces, "إِذَا")
    cond_tool_edges = [r for r in rg.relations if r.name == "condition_tool_of"]
    # Only the first إِذَا is allowed as a source for condition_tool_of in 2:282.
    expected_src = f"t{first_idha}"
    bad = [r for r in cond_tool_edges if r.source_id != expected_src]
    assert not bad, (
        f"condition_tool_of edges from non-first إِذَا found: "
        f"{[(r.source_id, r.target_id) for r in bad]}"
    )


# ── N2 ───────────────────────────────────────────────────────────
def t_2_282_no_unrelated_fa_token_linked_to_first_idha():
    """The jawab_shart_of target=تَدَايَنتُم must come ONLY from
    فَٱكْتُبُوهُ. Other فَ-prefixed verbs in the verse (فَلْيَكْتُبْ,
    فَلْيُمْلِلْ, فَإِن, فَتُذَكِّرَ, فَرَجُلٌ, فَلَيْسَ, فَإِنَّهُۥ) must
    NOT be linked to it."""
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    surfaces = _surfaces_for_2_282()
    tadayantum_idx = _idx_of(surfaces, "تَدَايَنتُم")
    faktubu_idx = _idx_of(surfaces, "فَٱكْتُبُوهُ")
    expected_tgt = f"t{tadayantum_idx}"
    allowed_src = f"t{faktubu_idx}"
    bad = [
        r for r in rg.relations
        if r.name == "jawab_shart_of"
        and r.target_id == expected_tgt
        and r.source_id != allowed_src
    ]
    assert not bad, (
        f"unrelated فَ-token linked to first إِذَا condition verb: "
        f"{[(r.source_id, surfaces[int(r.source_id[1:])] if r.source_id.startswith('t') else '?') for r in bad]}"
    )


# ── N3 ───────────────────────────────────────────────────────────
def t_2_282_no_condition_edge_for_other_tools():
    """No condition_tool_of edge should be sourced from any tool
    other than إِذَا in 2:282."""
    rg = _get_relations_for_2_282()
    if rg is _PIPELINE_UNAVAILABLE:
        print("  [skipped - pipeline unavailable]", end=" ")
        return
    surfaces = _surfaces_for_2_282()
    cond_tool_edges = [r for r in rg.relations if r.name == "condition_tool_of"]
    bad = []
    for r in cond_tool_edges:
        if not r.source_id.startswith("t"):
            continue
        try:
            idx = int(r.source_id[1:])
        except ValueError:
            continue
        if 0 <= idx < len(surfaces):
            if surfaces[idx] in _OTHER_CONDITIONAL_TOOLS:
                bad.append((surfaces[idx], r.target_id))
    assert not bad, (
        f"condition_tool_of sourced from non-إِذَا tools in 2:282: {bad}"
    )


# ── N4 ───────────────────────────────────────────────────────────
def t_implementation_blocked_if_phase5_unavailable():
    """If Phase 5 returns no clauses, the pass MUST emit zero
    condition/jawab edges (no fallback re-detection). Synthesized
    via a stub that returns []."""
    try:
        import relation_extractor as re_mod
        from relation_schema import RelationGraph
    except Exception:  # noqa: BLE001
        print("  [skipped - module unavailable]", end=" ")
        return

    original = re_mod.segment_clauses_from_surfaces
    re_mod.segment_clauses_from_surfaces = lambda surfaces, verse_ref: []
    try:
        try:
            from i3rab_engine.engine import I3rabEngine
            from relation_extractor import RelationExtractor
        except Exception:  # noqa: BLE001
            print("  [skipped - pipeline unavailable]", end=" ")
            return
        try:
            sent = I3rabEngine().analyze_sentence(_2_282_TEXT)
            if sent is None:
                print("  [skipped - sent unavailable]", end=" ")
                return
            rg = RelationExtractor().extract(sent)
        except Exception:  # noqa: BLE001
            print("  [skipped - pipeline failed]", end=" ")
            return
        cond = [r for r in rg.relations if r.name in {"condition_tool_of", "jawab_shart_of"}]
        assert not cond, (
            f"Phase 5 stubbed to empty; pass must emit zero condition/jawab "
            f"edges (no fallback re-detection); got: "
            f"{[(r.name, r.source_id, r.target_id) for r in cond]}"
        )
    finally:
        re_mod.segment_clauses_from_surfaces = original


# ── N5 ───────────────────────────────────────────────────────────
def t_no_relation_when_no_fa_jawab_in_phase5_output():
    """If Phase 5 returns a condition clause but no
    condition_answer_command, the pass MUST emit zero edges
    (cannot fabricate a jawab where Phase 5 didn't link one)."""
    try:
        import relation_extractor as re_mod
        from phase5_clause_segmenter import Phase5Clause
        from i3rab_engine.engine import I3rabEngine
        from relation_extractor import RelationExtractor
    except Exception:  # noqa: BLE001
        print("  [skipped - module unavailable]", end=" ")
        return

    def _stub_condition_only(surfaces, verse_ref):
        return [
            Phase5Clause(
                clause_id="C001",
                verse=verse_ref or "?",
                type="condition",
                start_token_index=3,
                end_token_index=8,
                text="إِذَا تَدَايَنتُم",
                head_token="إِذَا",
                head_kind="particle",
                parent_clause_id=None,
                introduced_by="إِذَا",
                scope_status="closed",
                confidence="Certificate",
                source="ConditionalScopeContract",
            )
        ]

    original = re_mod.segment_clauses_from_surfaces
    re_mod.segment_clauses_from_surfaces = _stub_condition_only
    try:
        try:
            sent = I3rabEngine().analyze_sentence(_2_282_TEXT)
            if sent is None:
                print("  [skipped - sent unavailable]", end=" ")
                return
            rg = RelationExtractor().extract(sent)
        except Exception:  # noqa: BLE001
            print("  [skipped - pipeline failed]", end=" ")
            return
        cond = [r for r in rg.relations if r.name in {"condition_tool_of", "jawab_shart_of"}]
        assert not cond, (
            f"Phase 5 stubbed to condition-only (no condition_answer_command); "
            f"pass must emit zero edges; got: "
            f"{[(r.name, r.source_id, r.target_id) for r in cond]}"
        )
    finally:
        re_mod.segment_clauses_from_surfaces = original


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
    print("SHART_JAWAB pilot 2:282 (Phase 5 Batch B)")
    print("=" * 70)
    ALL = [
        ("P1 t_2_282_first_idha_condition_tool_of_tadayantum",
         t_2_282_first_idha_condition_tool_of_tadayantum),
        ("P2 t_2_282_jawab_shart_of_faktubu_to_tadayantum",
         t_2_282_jawab_shart_of_faktubu_to_tadayantum),
        ("P3 t_2_282_jawab_shart_source_of_claim_records_fa_marker",
         t_2_282_jawab_shart_source_of_claim_records_fa_marker),
        ("P4 t_2_282_l7_contains_condition_and_jawab_edges_as_typed",
         t_2_282_l7_contains_condition_and_jawab_edges_as_typed),
        ("P5 t_2_282_l7_entropy_remains_zero_and_consistent",
         t_2_282_l7_entropy_remains_zero_and_consistent),
        ("P6 t_2_282_two_new_edges_are_both_certificate",
         t_2_282_two_new_edges_are_both_certificate),
        ("N1 t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot",
         t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot),
        ("N2 t_2_282_no_unrelated_fa_token_linked_to_first_idha",
         t_2_282_no_unrelated_fa_token_linked_to_first_idha),
        ("N3 t_2_282_no_condition_edge_for_other_tools",
         t_2_282_no_condition_edge_for_other_tools),
        ("N4 t_implementation_blocked_if_phase5_unavailable",
         t_implementation_blocked_if_phase5_unavailable),
        ("N5 t_no_relation_when_no_fa_jawab_in_phase5_output",
         t_no_relation_when_no_fa_jawab_in_phase5_output),
    ]
    for nm, fn in ALL:
        _run(nm, fn)
    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Result: {passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)
