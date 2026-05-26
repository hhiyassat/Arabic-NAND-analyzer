#!/usr/bin/env python3
"""test_refactor_step_a.py — اختبارات data models الجَديدَة.

Step A لا يُغَيِّر السُّلوك. يَتَحَقَّق فَقَط أَنّ:
  • Decision/Candidate/Evidence/SourceRecord تَعمَل
  • safe predicates صَحيحَة
  • from_legacy_dict / to_legacy_dict تَحفَظ الـbehavior
"""
import sys
sys.path.insert(0, ".")
from arabic_analyzer.core import (
    Decision, Candidate, Evidence, SourceRecord,
    decide_certainty, is_certified, is_hypothesis, is_zero,
)

results = []


def _t(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERR: {e}"))
        print(f"  ✗ {name}: ERR {e}")


# ─────────────────────────────────────────────────────────────
# SourceRecord
# ─────────────────────────────────────────────────────────────
def t_sourcerecord_basic():
    s = SourceRecord(source_id="MASAQ:1", source_type="benchmark", authority=10)
    assert s.source_id == "MASAQ:1"
    assert s.authority == 10
    assert str(s) == "benchmark:MASAQ:1"


def t_sourcerecord_immutable():
    s = SourceRecord(source_id="x", source_type="rule")
    try:
        s.source_id = "y"  # frozen
        raise AssertionError("SourceRecord should be frozen")
    except (AttributeError, Exception):
        pass


# ─────────────────────────────────────────────────────────────
# Evidence
# ─────────────────────────────────────────────────────────────
def t_evidence_positive():
    s = SourceRecord(source_id="x", source_type="rule")
    e = Evidence(kind="positive", reason="ok", source=s, strength=8, targets=("FIIL",))
    assert e.kind == "positive"
    assert "FIIL" in e.targets


def t_evidence_blocker():
    s = SourceRecord(source_id="x", source_type="rule")
    e = Evidence(kind="blocker", reason="tanwin", source=s)
    assert e.kind == "blocker"


# ─────────────────────────────────────────────────────────────
# Certainty rules
# ─────────────────────────────────────────────────────────────
def t_certainty_certificate():
    c = decide_certainty(n_candidates=1, has_source_conflict=False,
                         requires_context=False, priority=9)
    assert c == "Certificate", c


def t_certainty_conflict_blocks():
    """priority alone must not override conflict."""
    c = decide_certainty(n_candidates=1, has_source_conflict=True,
                         requires_context=False, priority=10)
    assert c == "Hypothesis", c


def t_certainty_multiple_candidates():
    c = decide_certainty(n_candidates=3, has_source_conflict=False,
                         requires_context=False, priority=9)
    assert c == "Hypothesis", c


def t_certainty_requires_context():
    c = decide_certainty(n_candidates=1, has_source_conflict=False,
                         requires_context=True, priority=9)
    assert c == "Hypothesis", c


def t_certainty_low_priority():
    c = decide_certainty(n_candidates=1, has_source_conflict=False,
                         requires_context=False, priority=5)
    assert c == "Hypothesis", c


def t_certainty_zero_when_no_candidates():
    c = decide_certainty(n_candidates=0, has_source_conflict=False,
                         requires_context=False, priority=10)
    assert c == "Zero", c


# ─────────────────────────────────────────────────────────────
# Decision predicates
# ─────────────────────────────────────────────────────────────
def t_decision_certified_fiil():
    d = Decision(surface="كَتَبَ", word_class="FIIL", candidates=["FIIL"],
                 certainty="Certificate", priority=10,
                 segmentation_status="Certificate")
    assert d.is_certified_fiil()
    assert d.allows_event_emission()
    assert d.allows_relation_emission()
    assert not d.is_ambiguous()


def t_decision_ambiguous_hypothesis_blocks_event():
    d = Decision(surface="مَنْ", word_class="ISM_MAWSOOL",
                 candidates=["ISM_MAWSOOL","HARF","ISM_MABNI"],
                 certainty="Hypothesis", needs_context=True,
                 segmentation_status="Certificate")
    assert d.is_ambiguous()
    assert not d.allows_event_emission(), "Hypothesis ambiguous must not emit Event"


def t_decision_zero_blocks_everything():
    d = Decision(surface="?", certainty="Zero")
    assert d.is_zero()
    assert not d.allows_event_emission()
    assert not d.allows_relation_emission()


def t_decision_no_segmentation_blocks_event():
    d = Decision(surface="كَتَبَ", word_class="FIIL", candidates=["FIIL"],
                 certainty="Certificate", priority=10,
                 segmentation_status="Zero")
    assert not d.allows_event_emission(), "fragment must not emit Event"


def t_decision_conflict_blocks_relation():
    d = Decision(surface="x", word_class="FIIL", candidates=["FIIL","ISM_MUARAB"],
                 certainty="Hypothesis", segmentation_status="Certificate",
                 blockers=["conflicting_candidates"])
    assert not d.allows_relation_emission()


# ─────────────────────────────────────────────────────────────
# Legacy compatibility
# ─────────────────────────────────────────────────────────────
def t_decision_to_legacy_dict():
    d = Decision(surface="كَتَبَ", word_class="FIIL", candidates=["FIIL"],
                 certainty="Certificate", source="MASAQ:1",
                 features={"root":"كتب","wazn":"فعل","tense":None,"voice":None,
                          "person":None,"number":None,"gender":None,"case":None})
    legacy = d.to_legacy_dict()
    assert legacy["word_class"] == "FIIL"
    assert legacy["root"] == "كتب"
    assert legacy["proof_kind"] == "Certificate"


def t_decision_from_legacy_dict():
    legacy = {
        "word_class": "FIIL",
        "source": "MASAQ:1",
        "root": "كتب",
        "wazn": "فعل",
        "proof_kind": "Certificate",
        "registry_candidates": ["FIIL"],
        "registry_requires_context": False,
        "proof_blockers": [],
    }
    d = Decision.from_legacy_dict(legacy, surface="كَتَبَ")
    assert d.word_class == "FIIL"
    assert d.features["root"] == "كتب"
    assert d.certainty == "Certificate"


# Run
print("REFACTOR Step A — Data models")
print("=" * 70)
ALL = [
    ("t_sourcerecord_basic", t_sourcerecord_basic),
    ("t_sourcerecord_immutable", t_sourcerecord_immutable),
    ("t_evidence_positive", t_evidence_positive),
    ("t_evidence_blocker", t_evidence_blocker),
    ("t_certainty_certificate", t_certainty_certificate),
    ("t_certainty_conflict_blocks", t_certainty_conflict_blocks),
    ("t_certainty_multiple_candidates", t_certainty_multiple_candidates),
    ("t_certainty_requires_context", t_certainty_requires_context),
    ("t_certainty_low_priority", t_certainty_low_priority),
    ("t_certainty_zero_when_no_candidates", t_certainty_zero_when_no_candidates),
    ("t_decision_certified_fiil", t_decision_certified_fiil),
    ("t_decision_ambiguous_hypothesis_blocks_event", t_decision_ambiguous_hypothesis_blocks_event),
    ("t_decision_zero_blocks_everything", t_decision_zero_blocks_everything),
    ("t_decision_no_segmentation_blocks_event", t_decision_no_segmentation_blocks_event),
    ("t_decision_conflict_blocks_relation", t_decision_conflict_blocks_relation),
    ("t_decision_to_legacy_dict", t_decision_to_legacy_dict),
    ("t_decision_from_legacy_dict", t_decision_from_legacy_dict),
]
for nm, fn in ALL:
    _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok:
            print(f"  ✗ {nm}: {err}")
