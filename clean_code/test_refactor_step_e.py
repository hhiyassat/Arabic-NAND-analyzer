#!/usr/bin/env python3
"""test_refactor_step_e.py — relation/event gates (observe-only).

Step E = gates + adapters. لا enforcement. لا تَغيير سُلوكيّ.
"""
import sys
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
# Relation Gate (observe-only)
# ─────────────────────────────────────────────────────────────
def t_relation_gate_observe_preserves_legacy():
    """observe mode: دائِمًا allowed=True مَهما كان."""
    from arabic_analyzer.relations import can_emit_relation, reset_relation_audit
    from arabic_analyzer.core import Decision
    reset_relation_audit()
    # حَتَّى مَع decision سَيِّء، observe لا يَمنَع
    bad_src = Decision(surface="x", certainty="Zero")
    v = can_emit_relation(source_decision=bad_src, enforcement_mode="observe")
    assert v.allowed is True, "observe must always allow"
    assert v.would_block is True, "but should record would_block"


def t_relation_gate_detects_fragment_candidate():
    from arabic_analyzer.relations import can_emit_relation, reset_relation_audit, get_relation_audit
    from arabic_analyzer.core import Decision
    reset_relation_audit()
    frag = Decision(surface="ك", word_class="FIIL", segmentation_status="Zero")
    v = can_emit_relation(source_decision=frag)
    assert "source_token_is_fragment" in v.reasons
    audit = get_relation_audit()
    assert audit["fragment_relation_candidates"] >= 1


def t_relation_gate_detects_hypothesis_candidate():
    from arabic_analyzer.relations import can_emit_relation, reset_relation_audit
    from arabic_analyzer.core import Decision
    reset_relation_audit()
    h = Decision(surface="مَنْ", word_class="ISM_MAWSOOL",
                 candidates=["ISM_MAWSOOL","HARF","ISM_MABNI"],
                 certainty="Hypothesis", needs_context=True)
    v = can_emit_relation(source_decision=h)
    assert "source_hypothesis_needs_context" in v.reasons


def t_relation_gate_clear_pass_when_certified():
    from arabic_analyzer.relations import can_emit_relation, reset_relation_audit
    from arabic_analyzer.core import Decision
    reset_relation_audit()
    good = Decision(surface="كَتَبَ", word_class="FIIL",
                    candidates=["FIIL"], certainty="Certificate",
                    priority=10, segmentation_status="Certificate")
    v = can_emit_relation(source_decision=good, target_decision=good)
    assert v.allowed and not v.would_block


def t_relation_gate_enforce_mode_blocks():
    from arabic_analyzer.relations import can_emit_relation
    from arabic_analyzer.core import Decision
    frag = Decision(surface="ك", segmentation_status="Zero")
    v = can_emit_relation(source_decision=frag, enforcement_mode="enforce")
    assert not v.allowed, "enforce mode must block"


# ─────────────────────────────────────────────────────────────
# Event Gate (observe-only)
# ─────────────────────────────────────────────────────────────
def t_event_gate_observe_preserves_legacy():
    from arabic_analyzer.events import can_emit_event, reset_event_audit
    from arabic_analyzer.core import Decision
    reset_event_audit()
    bad = Decision(surface="x", certainty="Zero")
    v = can_emit_event(verb_decision=bad, enforcement_mode="observe")
    assert v.allowed is True


def t_event_gate_detects_fragment_candidate():
    from arabic_analyzer.events import can_emit_event, reset_event_audit, get_event_audit
    from arabic_analyzer.core import Decision
    reset_event_audit()
    frag = Decision(surface="ك", word_class="FIIL",
                    certainty="Certificate", segmentation_status="Zero")
    v = can_emit_event(verb_decision=frag)
    assert "verb_is_fragment" in v.reasons
    audit = get_event_audit()
    assert audit["fragment_event_candidates"] >= 1


def t_event_gate_detects_non_certified_fiil():
    from arabic_analyzer.events import can_emit_event, reset_event_audit
    from arabic_analyzer.core import Decision
    reset_event_audit()
    noun = Decision(surface="كِتَابٌ", word_class="ISM_MUARAB",
                    certainty="Certificate", segmentation_status="Certificate")
    v = can_emit_event(verb_decision=noun)
    assert any("not_certified_fiil" in r for r in v.reasons)


def t_event_gate_certified_fiil_passes():
    from arabic_analyzer.events import can_emit_event, reset_event_audit
    from arabic_analyzer.core import Decision
    reset_event_audit()
    good = Decision(surface="كَتَبَ", word_class="FIIL",
                    candidates=["FIIL"], certainty="Certificate",
                    priority=10, segmentation_status="Certificate")
    v = can_emit_event(verb_decision=good)
    assert v.allowed and not v.would_block


# ─────────────────────────────────────────────────────────────
# Adapters
# ─────────────────────────────────────────────────────────────
def t_relation_adapter_roundtrip_legacy():
    from arabic_analyzer.relations import StandardRelation, relation_to_legacy, relation_from_legacy
    r = StandardRelation(name="agent_of", source_id="t0", target_id="t1",
                         role_kind="Certificate")
    d = relation_to_legacy(r)
    r2 = relation_from_legacy(d)
    assert r2.name == r.name
    assert r2.source_id == r.source_id
    assert r2.target_id == r.target_id
    assert r2.role_kind == r.role_kind


def t_event_adapter_roundtrip_legacy():
    from arabic_analyzer.events import StandardEvent, event_to_legacy, event_from_legacy
    e = StandardEvent(lemma="كتب", surface="كَتَبَ", tense="past", agent="زَيْدٌ")
    d = event_to_legacy(e)
    e2 = event_from_legacy(d)
    assert e2.lemma == e.lemma
    assert e2.tense == e.tense
    assert e2.agent == e.agent


# ─────────────────────────────────────────────────────────────
# No runtime behavior change
# ─────────────────────────────────────────────────────────────
def t_no_runtime_behavior_change_step_e():
    """Step E لا يَتَدَخَّل في pipeline. Layer 1 + analyze_verse ما زالا يَعمَلان."""
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["كَتَبَ","ٱلْكِتَابُ","هُوَ","ٱلَّذِي"]:
        r = clf.classify(tok)
        assert r["word_class"] in ("FIIL","ISM_MUARAB","JAMID","ISM_MABNI",
                                    "HARF","ISM_MAWSOOL","SINGULAR_TERM")


def t_audit_counters_exist():
    from arabic_analyzer.relations import get_relation_audit
    from arabic_analyzer.events import get_event_audit
    ra = get_relation_audit()
    ea = get_event_audit()
    # required counters per user spec
    for k in ("would_block_relation_count","fragment_relation_candidates",
              "hypothesis_relation_candidates","ambiguous_relation_candidates",
              "conflicting_candidate_relation_count"):
        assert k in ra, f"missing counter: {k}"
    for k in ("would_block_event_count","fragment_event_candidates",
              "hypothesis_event_candidates","ambiguous_event_candidates",
              "conflicting_candidate_event_count"):
        assert k in ea, f"missing counter: {k}"


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("REFACTOR Step E — Relation/Event Gates (observe-only)")
print("=" * 70)
ALL = [
    ("t_relation_gate_observe_preserves_legacy", t_relation_gate_observe_preserves_legacy),
    ("t_relation_gate_detects_fragment_candidate", t_relation_gate_detects_fragment_candidate),
    ("t_relation_gate_detects_hypothesis_candidate", t_relation_gate_detects_hypothesis_candidate),
    ("t_relation_gate_clear_pass_when_certified", t_relation_gate_clear_pass_when_certified),
    ("t_relation_gate_enforce_mode_blocks", t_relation_gate_enforce_mode_blocks),
    ("t_event_gate_observe_preserves_legacy", t_event_gate_observe_preserves_legacy),
    ("t_event_gate_detects_fragment_candidate", t_event_gate_detects_fragment_candidate),
    ("t_event_gate_detects_non_certified_fiil", t_event_gate_detects_non_certified_fiil),
    ("t_event_gate_certified_fiil_passes", t_event_gate_certified_fiil_passes),
    ("t_relation_adapter_roundtrip_legacy", t_relation_adapter_roundtrip_legacy),
    ("t_event_adapter_roundtrip_legacy", t_event_adapter_roundtrip_legacy),
    ("t_no_runtime_behavior_change_step_e", t_no_runtime_behavior_change_step_e),
    ("t_audit_counters_exist", t_audit_counters_exist),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
