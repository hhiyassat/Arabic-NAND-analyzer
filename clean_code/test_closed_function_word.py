#!/usr/bin/env python3
"""test_closed_function_word.py — اختبارات ClosedFunctionWordOverrideGate.

تَوصيَة المُستَخدِم 2026-05-25:
  test_mimman_not_verb
  test_illa_not_verb
  test_fa_innahu_not_verb
  test_function_word_never_enters_verb_form_contract
  test_no_event_for_mimman
  test_no_event_for_illa
  test_no_event_for_fa_innahu
  test_no_agent_of_fusuq_to_fa_innahu
"""

from __future__ import annotations

from closed_function_word_gate import (
    check_closed_function_word,
    is_closed_function_word,
)
from verb_form_contract import evaluate_verb_form
from i3rab_engine.layer1 import WordClassClassifier
from i3rab_engine.engine import I3rabEngine
from relation_extractor import RelationExtractor
from event_extractor import EventExtractor

CLF = WordClassClassifier()
ENG = I3rabEngine()
REL = RelationExtractor()
EV = EventExtractor()


def _analyze(text):
    sent = ENG.analyze_sentence(text)
    rg = REL.extract(sent)
    eg = EV.extract(sent, rg)
    return sent, rg, eg


def _classify(t):
    return CLF.classify(t)


results = []


def test(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERROR: {type(e).__name__}: {e}"))
        print(f"  ✗ {name}: ERROR {e}")


# ─────────────────────────────────────────────────────────────────
# 1. Specific function-word compounds (per user)
# ─────────────────────────────────────────────────────────────────

def test_mimman_not_verb():
    """مِمَّن — أداة مُرَكَّبَة (من + من). لَيس فِعل."""
    assert is_closed_function_word("مِمَّن"), "مِمَّن must be function word"
    v = evaluate_verb_form("مِمَّن")
    assert v.kind == "Zero", f"contract: مِمَّن must be Zero, got {v.kind}"
    r = _classify("مِمَّن")
    assert r["word_class"] == "HARF", \
        f"layer1: مِمَّن must be HARF, got {r['word_class']}"


def test_illa_not_verb():
    """إِلَّا / إِلَّآ — أداة استثناء."""
    for surface in ("إِلَّا", "إِلَّآ"):
        assert is_closed_function_word(surface), f"{surface} must be function"
        v = evaluate_verb_form(surface)
        assert v.kind == "Zero", f"contract: {surface} must be Zero, got {v.kind}"
        r = _classify(surface)
        assert r["word_class"] == "HARF", \
            f"layer1: {surface} must be HARF, got {r['word_class']}"


def test_fa_innahu_not_verb():
    """فَإِنَّهُ / فَإِنَّهُۥ — تَركيب: ف + إنّ + هـ."""
    for surface in ("فَإِنَّهُ", "فَإِنَّهُۥ"):
        v = evaluate_verb_form(surface)
        assert v.kind == "Zero", f"contract: {surface} must be Zero, got {v.kind}"
        r = _classify(surface)
        assert r["word_class"] == "HARF", \
            f"layer1: {surface} must be HARF, got {r['word_class']}"


def test_function_word_never_enters_verb_form_contract():
    """كُلّ الأَدوات يَجِب أَن تَخرُج بِـZero فَورًا مِن VerbFormContract."""
    function_words = [
        "مِمَّن", "إِلَّا", "إِلَّآ",
        "فَإِنَّهُ", "فَإِنَّهُۥ",
        "أَن", "أَلَّا", "وَلَا", "كَمَا", "إِذَا",
        "إِنَّمَا", "لَكِنَّ", "أَنَّ", "إِنَّ",
        "حَتَّى", "لَوْ", "لَوْلَا",
    ]
    for w in function_words:
        v = evaluate_verb_form(w)
        assert v.kind == "Zero", \
            f"{w} reached VerbFormContract verdict={v.kind}"


# ─────────────────────────────────────────────────────────────────
# 2. End-to-end: function words must not generate events
# ─────────────────────────────────────────────────────────────────

def _no_event_for(text, target_token):
    sent, rg, eg = _analyze(text)
    # نَجِد index الـtoken
    target_idx = None
    for i, t in enumerate(sent.tokens):
        if (t.token or "").strip() == target_token:
            target_idx = i
            break
    if target_idx is None:
        return  # لَم نَجِد — OK
    for e in eg.events:
        verb_id = getattr(e, "verb_id", "")
        if verb_id == f"t{target_idx}":
            raise AssertionError(
                f"Event generated for function word {target_token}: {e}"
            )


def test_no_event_for_mimman():
    _no_event_for("الَّذِينَ تَرْضَوْنَ مِمَّن الشُّهَدَآءِ", "مِمَّن")


def test_no_event_for_illa():
    _no_event_for("لَا إِلَهَ إِلَّا اللَّهُ", "إِلَّا")


def test_no_event_for_fa_innahu():
    _no_event_for("تَفْعَلُوا فَإِنَّهُ فُسُوقٌ بِكُمْ", "فَإِنَّهُ")


def test_no_agent_of_fusuq_to_fa_innahu():
    """فُسُوقٌ يَجِب أَلّا يَكون agent_of(فُسُوقٌ → فَإِنَّهُ)."""
    text = "وَإِن تَفْعَلُوا فَإِنَّهُ فُسُوقٌ بِكُمْ"
    sent, rg, _ = _analyze(text)
    # نَجِد index لـ فَإِنَّهُ
    fa_idx = None
    for i, t in enumerate(sent.tokens):
        if "فَإِنَّهُ" in (t.token or ""):
            fa_idx = i
            break
    if fa_idx is None:
        return  # لَم نَجِد — OK
    for r in rg.relations:
        if r.name == "agent_of" and r.target_id == f"t{fa_idx}":
            raise AssertionError(
                f"agent_of emitted onto function word فَإِنَّهُ: {r}"
            )


# ─────────────────────────────────────────────────────────────────
# 3. Real verbs/nouns must remain unaffected
# ─────────────────────────────────────────────────────────────────

def test_real_verbs_unaffected():
    real_verbs = [
        "كَتَبَ", "يَكْتُبُ", "فَٱكْتُبُوهُ", "وَلْيَكْتُبْ",
        "عَلَّمَهُ", "وَيُعَلِّمُكُمُ", "كَانَ", "فَلَيْسَ",
    ]
    for w in real_verbs:
        assert not is_closed_function_word(w), \
            f"{w} should NOT be flagged as function word"
        r = _classify(w)
        assert r["word_class"] == "FIIL", \
            f"{w} must remain FIIL, got {r['word_class']}"


def test_real_nouns_unaffected():
    for w in ("كِتَابٌ", "أَجَلِهِ", "وَلِيُّهُۥ"):
        assert not is_closed_function_word(w), \
            f"{w} should NOT be flagged as function word"


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("ClosedFunctionWord Gate Tests")
print("=" * 60)

test("test_mimman_not_verb", test_mimman_not_verb)
test("test_illa_not_verb", test_illa_not_verb)
test("test_fa_innahu_not_verb", test_fa_innahu_not_verb)
test("test_function_word_never_enters_verb_form_contract",
     test_function_word_never_enters_verb_form_contract)
test("test_no_event_for_mimman", test_no_event_for_mimman)
test("test_no_event_for_illa", test_no_event_for_illa)
test("test_no_event_for_fa_innahu", test_no_event_for_fa_innahu)
test("test_no_agent_of_fusuq_to_fa_innahu", test_no_agent_of_fusuq_to_fa_innahu)
test("test_real_verbs_unaffected", test_real_verbs_unaffected)
test("test_real_nouns_unaffected", test_real_nouns_unaffected)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
