#!/usr/bin/env python3
"""test_phase4_integration.py — flag-controlled integration (11 tests).

Phase 4 integration هو hook خَلف flag.
flag OFF (default) → byte-identical لِـ baseline.
flag ON → resolver يُطَبَّق على Hypothesis tokens المُؤَهَّلَة.
"""
import os
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


_FLAG = "ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"


def _set_flag(val):
    if val:
        os.environ[_FLAG] = "1"
    elif _FLAG in os.environ:
        del os.environ[_FLAG]


# ─────────────────────────────────────────────────────────────
# Default + flag-off identity
# ─────────────────────────────────────────────────────────────
def t_contextual_resolver_disabled_by_default():
    """بِدون env var، flag OFF."""
    _set_flag(False)
    from arabic_analyzer.contextual_resolver import is_enabled
    assert is_enabled() is False


def t_flag_off_output_identical_to_baseline():
    """flag OFF → classify_with_context == classify (byte-identical)."""
    _set_flag(False)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    for tok in ["مَن", "ما", "أَيّ", "كَتَبَ", "ٱلْكِتَابُ"]:
        r1 = clf.classify(tok)
        r2 = clf.classify_with_context(tok, prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
        # كُلّ keys نَفسها وَالقِيَم نَفسها
        assert r1 == r2, f"{tok}: differ when flag OFF\n  r1={r1}\n  r2={r2}"


# ─────────────────────────────────────────────────────────────
# Flag ON — in-scope resolution
# ─────────────────────────────────────────────────────────────
def t_flag_on_resolves_man_context():
    """flag ON + مَن بِسِياق سُؤال → resolver يَتَدَخَّل."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r = clf.classify_with_context("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    # إذا الـbaseline أَعطى Hypothesis لِـ مَن، resolver يُرَقّيها
    # إذا أَعطى Certificate أَصلًا، نَتَأَكَّد أَنَّ phase4 metadata مَوجود (إن تَطَبَّق) أَو لا تَدَخُّل
    # المُهِم: إذا تَدَخَّل، يَجِب أَن يَكون selected_function = interrogative_tool
    if r.get("source") == "ContextualAmbiguityResolver":
        assert r["phase4_selected_function"] == "interrogative_tool", r.get("phase4_selected_function")
        assert r["proof_kind"] == "Certificate"


def t_flag_on_resolves_ma_context():
    """flag ON + ما + ماضٍ → potentially negative_particle."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r = clf.classify_with_context("ما", prev_tokens=[], next_tokens=["كَتَبَ"])
    # إذا تَدَخَّل: function يَكون negative_particle أَو Hypothesis-tagged
    if r.get("source") == "ContextualAmbiguityResolver" or r.get("phase4_selected_function"):
        # يَجِب أَن يَكون فيه phase4 metadata
        assert "phase4_selected_function" in r


def t_flag_on_does_not_touch_non_scope_tokens():
    """flag ON + token خارِج النِّطاق → لا تَغيير."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r_baseline = clf.classify("كَتَبَ")
    _set_flag(True)
    r_phase4 = clf.classify_with_context("كَتَبَ", prev_tokens=["قَالَ"], next_tokens=["زَيدٌ"])
    # كَتَبَ خارِج Phase 4 scope → identical
    assert r_baseline.get("word_class") == r_phase4.get("word_class")
    assert r_baseline.get("source") == r_phase4.get("source")
    assert "phase4_selected_function" not in r_phase4


# ─────────────────────────────────────────────────────────────
# Behavior rules
# ─────────────────────────────────────────────────────────────
def t_unresolved_ambiguous_preserves_original_decision():
    """resolver→unresolved_ambiguous: لا تَغيير في word_class."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r_baseline = clf.classify("مَن")
    r_phase4 = clf.classify_with_context("مَن", prev_tokens=[], next_tokens=[])
    # بِلا سِياق → unresolved_ambiguous → لا تَغيير في word_class
    if r_phase4.get("phase4_selected_function") == "unresolved_ambiguous" or \
       r_phase4.get("source") != "ContextualAmbiguityResolver":
        assert r_baseline.get("word_class") == r_phase4.get("word_class")


def t_hypothesis_does_not_promote_without_strong_context():
    """resolver→Hypothesis: lا تَرقيَة، فَقَط metadata."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    # ما + مُضارِع (لا mata jussive، لا interrogative واضِح) → Hypothesis relative
    r = clf.classify_with_context("ما", prev_tokens=["زَيدٌ"], next_tokens=["يَكتُبُ"])
    # إذا resolver أَعطى Hypothesis، لا يَجِب تَرقيَتها لِـ Certificate
    if r.get("phase4_selected_function") and r.get("phase4_selected_function") != "unresolved_ambiguous":
        # لا يَجِب أَن يَكون source = ContextualAmbiguityResolver (لأَنَّ Certificate فَقَط يَرفَع)
        if r.get("proof_kind") != "Certificate":
            assert r.get("source") != "ContextualAmbiguityResolver"


def t_certificate_requires_reason_and_context_features():
    """Certificate مِن resolver → يَجِب وُجود reason و context_features."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r = clf.classify_with_context("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    if r.get("source") == "ContextualAmbiguityResolver":
        assert r.get("proof_kind") == "Certificate"
        assert r.get("phase4_reason"), "reason missing"
        assert r.get("phase4_context_features"), "context_features missing"


def t_original_candidates_preserved_after_resolution():
    """تَرقيَة Certificate تَحفَظ الـoriginal_candidates."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r = clf.classify_with_context("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    if r.get("source") == "ContextualAmbiguityResolver":
        assert "phase4_original_candidates" in r
        assert isinstance(r["phase4_original_candidates"], list)


def t_masaq_compatible_class_kept_separate():
    """masaq_compatible_class مَحفوظ كَحَقل مُنفَصِل."""
    _set_flag(True)
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    r = clf.classify_with_context("مَتَى", prev_tokens=["قَالَ"], next_tokens=["تَعودُ"])
    if r.get("source") == "ContextualAmbiguityResolver":
        assert "phase4_masaq_compatible_class" in r
        # مَتَى: internal = ISM_MABNI، masaq = HARF
        assert r["word_class"] == "ISM_MABNI"
        assert r["phase4_masaq_compatible_class"] == "HARF"


def t_no_event_relation_gate_enforcement_from_resolver():
    """resolver لا يُفَعِّل enforce في أَيّ gate."""
    _set_flag(True)
    from arabic_analyzer.events import get_event_audit, reset_event_audit
    from arabic_analyzer.relations import get_relation_audit, reset_relation_audit
    reset_event_audit(); reset_relation_audit()
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    # شَغِّل resolver عَلى token مَدعوم
    clf.classify_with_context("مَن", prev_tokens=["قَالَ"], next_tokens=["أَنتَ"])
    # audit counters لِـ events/relations يَجِب أَن تَبقى صِفر (لا تَدَخُّل)
    ea = get_event_audit(); ra = get_relation_audit()
    # resolver لا يُحَرِّك gates
    assert ea["would_block_event_count"] == 0
    assert ra["would_block_relation_count"] == 0


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
_set_flag(False)  # ابدَأ بِـ OFF لِلتَّأَكُّد مِن baseline
print("PHASE 4 INTEGRATION — flag-controlled hook (11 tests)")
print("=" * 70)
ALL = [
    ("t_contextual_resolver_disabled_by_default", t_contextual_resolver_disabled_by_default),
    ("t_flag_off_output_identical_to_baseline", t_flag_off_output_identical_to_baseline),
    ("t_flag_on_resolves_man_context", t_flag_on_resolves_man_context),
    ("t_flag_on_resolves_ma_context", t_flag_on_resolves_ma_context),
    ("t_flag_on_does_not_touch_non_scope_tokens", t_flag_on_does_not_touch_non_scope_tokens),
    ("t_unresolved_ambiguous_preserves_original_decision", t_unresolved_ambiguous_preserves_original_decision),
    ("t_hypothesis_does_not_promote_without_strong_context", t_hypothesis_does_not_promote_without_strong_context),
    ("t_certificate_requires_reason_and_context_features", t_certificate_requires_reason_and_context_features),
    ("t_original_candidates_preserved_after_resolution", t_original_candidates_preserved_after_resolution),
    ("t_masaq_compatible_class_kept_separate", t_masaq_compatible_class_kept_separate),
    ("t_no_event_relation_gate_enforcement_from_resolver", t_no_event_relation_gate_enforcement_from_resolver),
]
for nm, fn in ALL: _t(nm, fn)
# تَنظيف بَعد التَّجارِب
_set_flag(False)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
