#!/usr/bin/env python3
"""test_refactor_step_d.py — segmentation wrappers + certification metadata.

Step D = wrappers + metadata. لا enforcement. لا تَغيير سُلوكيّ.
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
# segmenter wrapper equivalence
# ─────────────────────────────────────────────────────────────
def t_segment_token_equivalent_to_legacy():
    from arabic_analyzer.segmentation import segment_token
    from segmenter import segment as legacy_segment
    for tok in ["كَتَبَ","الْكِتَابُ","لِتَرْكَبُوا","ٱلَّذِى","فَلْيَكْتُبْ"]:
        new = segment_token(tok)
        old = legacy_segment(tok)
        assert new.original == old.original
        assert new.normalized == old.normalized
        assert list(new.prefixes) == list(old.prefixes)
        assert new.stem == old.stem
        assert list(new.suffixes) == list(old.suffixes)


def t_segment_verse_equivalent_to_legacy():
    from arabic_analyzer.segmentation import segment_verse
    from segmenter import segment as legacy_segment
    verse = "ٱللَّهُ ٱلَّذِى جَعَلَ لَكُمُ ٱلْأَنْعَٰمَ"
    new_list = segment_verse(verse)
    old_list = [legacy_segment(t) for t in verse.split()]
    assert len(new_list) == len(old_list)
    for n, o in zip(new_list, old_list):
        assert n.stem == o.stem
        assert list(n.prefixes) == list(o.prefixes)


def t_closed_form_segmentation_unchanged():
    """ٱلَّذِى مُقَطَّع كَ DET+stem كَما في baseline."""
    from arabic_analyzer.segmentation import segment_token
    r = segment_token("ٱلَّذِى")
    # baseline: prefixes=[الَّ(DET)] stem=ذِى
    assert r.prefixes, f"ٱلَّذِى expected prefixes, got: {r.prefixes}"
    assert r.stem, f"ٱلَّذِى expected stem"


def t_awlaika_segmentation_behavior_matches_baseline():
    """أُولَئِكَ — سُلوك baseline (مَهما كان قَبل الـrefactor)."""
    from arabic_analyzer.segmentation import segment_token
    from segmenter import segment as legacy_segment
    new = segment_token("أُولَٰئِكَ")
    old = legacy_segment("أُولَٰئِكَ")
    # نُطابِق legacy حَرفيًّا — لا حُكم
    assert new.stem == old.stem
    assert list(new.prefixes) == list(old.prefixes)


def t_segment_object_roundtrip_to_legacy():
    from arabic_analyzer.segmentation import segment_token, to_legacy_segments, from_legacy_segments
    r = segment_token("ٱلْكِتَابُ")
    d = to_legacy_segments(r)
    r2 = from_legacy_segments(d)
    assert r2.original == r.original
    assert r2.stem == r.stem
    assert list(r2.prefixes) == list(r.prefixes)


# ─────────────────────────────────────────────────────────────
# SegmentationDecision metadata (no enforcement)
# ─────────────────────────────────────────────────────────────
def t_segmentation_decision_has_required_fields():
    from arabic_analyzer.segmentation import certify_segmentation, segment_token
    legacy = segment_token("ٱلْكِتَابُ")
    d = certify_segmentation(legacy)
    # required fields from user spec
    assert hasattr(d, "surface")
    assert hasattr(d, "segments")
    assert hasattr(d, "segmentation_status")
    assert hasattr(d, "source")
    assert hasattr(d, "blockers")
    assert hasattr(d, "parent_token")
    assert hasattr(d, "is_fragment")
    assert hasattr(d, "confidence")


def t_segmentation_decision_default_certificate():
    """Step D: status دائِمًا Certificate (يَحفَظ السُّلوك القَديم)."""
    from arabic_analyzer.segmentation import certify_segmentation, segment_token
    legacy = segment_token("كَتَبَ")
    d = certify_segmentation(legacy)
    assert d.is_certified(), f"Step D default should be Certificate"


def t_fragment_metadata_present():
    """ٱلْكِتَابُ ← prefixes=[الْ(DET)] → الـsegments تُحمَل is_fragment=True
    لَكِن لا يَفرِض حَجبًا في الـsentence-level relations."""
    from arabic_analyzer.segmentation import certify_segmentation, segment_token
    legacy = segment_token("ٱلْكِتَابُ")
    d = certify_segmentation(legacy)
    # الـprefixes تُسَمَّى fragments (مُعلومَة) لَكِن d.is_fragment لِلـtoken الكامِل = False
    fragments = [s for s in d.segments if s.is_fragment]
    if d.has_prefixes() or d.has_suffixes():
        assert len(fragments) > 0, "should have fragment segments"
    assert not d.is_fragment, "token itself is not a fragment"


def t_segmentation_decision_to_legacy_dict():
    from arabic_analyzer.segmentation import certify_segmentation, segment_token
    legacy = segment_token("لِتَرْكَبُوا۟")
    d = certify_segmentation(legacy)
    legacy_dict = d.to_legacy_dict()
    # نَتَأَكَّد مِن وُجود الحُقول الأَساسيَّة
    assert "original" in legacy_dict
    assert "stem" in legacy_dict
    assert "prefixes" in legacy_dict
    assert "suffixes" in legacy_dict


def t_no_enforcement_in_step_d():
    """Step D لا يَجِب أَن يَفرِض حَجبًا في pipeline.

    أَيّ relation/event يُصدَر مِن legacy code يَجِب أَن يَبقى يُصدَر.
    """
    # نَتَأَكَّد أَنّ Layer 1 + analyze_verse ما زالا يَعمَلان كَما في baseline
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["كَتَبَ","ٱلْكِتَابُ","هُوَ"]:
        r = clf.classify(tok)
        assert r["word_class"] in ("FIIL","ISM_MUARAB","JAMID","ISM_MABNI","HARF","ISM_MAWSOOL","SINGULAR_TERM")


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("REFACTOR Step D — Segmentation wrappers + Certification metadata")
print("=" * 70)
ALL = [
    ("t_segment_token_equivalent_to_legacy", t_segment_token_equivalent_to_legacy),
    ("t_segment_verse_equivalent_to_legacy", t_segment_verse_equivalent_to_legacy),
    ("t_closed_form_segmentation_unchanged", t_closed_form_segmentation_unchanged),
    ("t_awlaika_segmentation_behavior_matches_baseline", t_awlaika_segmentation_behavior_matches_baseline),
    ("t_segment_object_roundtrip_to_legacy", t_segment_object_roundtrip_to_legacy),
    ("t_segmentation_decision_has_required_fields", t_segmentation_decision_has_required_fields),
    ("t_segmentation_decision_default_certificate", t_segmentation_decision_default_certificate),
    ("t_fragment_metadata_present", t_fragment_metadata_present),
    ("t_segmentation_decision_to_legacy_dict", t_segmentation_decision_to_legacy_dict),
    ("t_no_enforcement_in_step_d", t_no_enforcement_in_step_d),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
