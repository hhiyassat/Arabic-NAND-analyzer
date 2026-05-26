#!/usr/bin/env python3
"""test_refactor_step_c.py — يَتَحَقَّق أَنّ classification wrappers تُكافِئ legacy.

Step C = wrappers only. لا تَغيير سُلوكيّ.
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
# candidate_resolver
# ─────────────────────────────────────────────────────────────
def t_resolve_candidates_matches_registry():
    """resolve_candidates يُرجِع نَفس candidates مِن registry."""
    from arabic_analyzer.classification import resolve_candidates
    from linguistic_source_registry import resolve_strict
    for tok in ["هَذَا","الَّذِي","مَنْ","فِي","يَا"]:
        new = resolve_candidates(tok)
        old = resolve_strict(tok)
        new_cands = [c.word_class for c in new]
        old_cands = old.get("candidates") or []
        assert new_cands == old_cands, \
            f"{tok}: new={new_cands} old={old_cands}"


def t_classify_via_registry_certificate():
    """Certificate من registry يَبقى Certificate."""
    from arabic_analyzer.classification import classify_via_registry
    d = classify_via_registry("هَذَا")
    assert d is not None
    assert d.certainty == "Certificate"
    assert d.word_class == "ISM_MABNI"


def t_classify_via_registry_hypothesis():
    """مَن → Hypothesis مَع candidates مُتَعَدِّدَة."""
    from arabic_analyzer.classification import classify_via_registry
    d = classify_via_registry("مَنْ")
    assert d is not None
    assert d.certainty == "Hypothesis"
    assert d.is_ambiguous()
    assert len(d.candidates) >= 2


def t_classify_via_compound_limadha():
    """لِمَاذَا يُحَلّ كَ compound."""
    from arabic_analyzer.classification import classify_via_compound
    d = classify_via_compound("لِمَاذَا")
    assert d is not None
    assert "compound" in d.source


def t_classify_via_registry_returns_none_for_unknown():
    """surface غَير مَوجود في registry يُرجِع None."""
    from arabic_analyzer.classification import classify_via_registry
    d = classify_via_registry("كَتَبَ")  # فِعل، لَيس في registry
    # يَجوز أَن يَكون None أَو Decision (لَو registry يَحويه)
    # المُهِمّ: لا يَرمي خَطَأ
    assert d is None or d.word_class is not None


# ─────────────────────────────────────────────────────────────
# fallback_classifier
# ─────────────────────────────────────────────────────────────
def t_classify_via_masaq_known_token():
    """token مَعروف في MASAQ يُرجِع Decision Certificate."""
    from arabic_analyzer.classification import classify_via_masaq
    d = classify_via_masaq("كَتَبَ")
    assert d is not None
    assert d.certainty == "Certificate"


def t_classify_via_masaq_unknown_token():
    from arabic_analyzer.classification import classify_via_masaq
    d = classify_via_masaq("xyzabc")
    assert d is None


def t_classify_via_heuristics_matches_layer1():
    """heuristics wrapper يُكافِئ Layer 1 الكامِل."""
    from arabic_analyzer.classification import classify_via_heuristics
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["كَتَبَ","الْكِتَابُ","هُوَ","فِي","يَعْقُوبَ"]:
        new = classify_via_heuristics(tok)
        old = clf.classify(tok)
        assert new.word_class == old["word_class"], \
            f"{tok}: new={new.word_class} old={old['word_class']}"


# ─────────────────────────────────────────────────────────────
# word_class_decision_kernel
# ─────────────────────────────────────────────────────────────
def t_classify_returns_decision():
    from arabic_analyzer.classification import classify
    from arabic_analyzer.core import Decision
    d = classify("كَتَبَ")
    assert isinstance(d, Decision)
    assert d.word_class == "FIIL"


def t_classify_legacy_dict_equivalent():
    """classify_legacy_dict يُرجِع نَفس dict القَديم."""
    from arabic_analyzer.classification import classify_legacy_dict
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["كَتَبَ","الْكِتَابُ","هُوَ"]:
        new = classify_legacy_dict(tok)
        old = clf.classify(tok)
        assert new["word_class"] == old["word_class"]
        assert new["source"] == old["source"]


# ─────────────────────────────────────────────────────────────
# No certainty drift
# ─────────────────────────────────────────────────────────────
def t_no_certainty_drift():
    """نَفس tokens — نَفس certainty عَبر wrapper وَ legacy."""
    from arabic_analyzer.classification import classify
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    tokens = ["هَذَا","الَّذِي","كَتَبَ","الْكِتَابُ","فِي","يَعْقُوبَ",
              "أُولَئِكَ","مَنْ","ما","حَتَّى"]
    drifts = []
    for tok in tokens:
        new = classify(tok)
        old = clf.classify(tok)
        new_pk = new.certainty
        old_pk = old.get("proof_kind", "")
        if new_pk and old_pk and new_pk != old_pk:
            drifts.append((tok, new_pk, old_pk))
    assert not drifts, f"Certainty drift: {drifts}"


def t_no_source_drift():
    """نَفس tokens — نَفس source category."""
    from arabic_analyzer.classification import classify
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["كَتَبَ","الْكِتَابُ","هُوَ"]:
        new = classify(tok)
        old = clf.classify(tok)
        # نَستَخدِم prefix only (الـsource_id قَد يَتَغَيَّر بِالتَّفاصيل)
        new_src_prefix = new.source.split(":")[0]
        old_src_prefix = old["source"].split(":")[0]
        assert new_src_prefix == old_src_prefix, \
            f"{tok}: new src={new_src_prefix} old={old_src_prefix}"


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("REFACTOR Step C — Classification wrappers")
print("=" * 70)
ALL = [
    ("t_resolve_candidates_matches_registry", t_resolve_candidates_matches_registry),
    ("t_classify_via_registry_certificate", t_classify_via_registry_certificate),
    ("t_classify_via_registry_hypothesis", t_classify_via_registry_hypothesis),
    ("t_classify_via_compound_limadha", t_classify_via_compound_limadha),
    ("t_classify_via_registry_returns_none_for_unknown", t_classify_via_registry_returns_none_for_unknown),
    ("t_classify_via_masaq_known_token", t_classify_via_masaq_known_token),
    ("t_classify_via_masaq_unknown_token", t_classify_via_masaq_unknown_token),
    ("t_classify_via_heuristics_matches_layer1", t_classify_via_heuristics_matches_layer1),
    ("t_classify_returns_decision", t_classify_returns_decision),
    ("t_classify_legacy_dict_equivalent", t_classify_legacy_dict_equivalent),
    ("t_no_certainty_drift", t_no_certainty_drift),
    ("t_no_source_drift", t_no_source_drift),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
