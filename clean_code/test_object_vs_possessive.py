#!/usr/bin/env python3
"""test_object_vs_possessive.py — اختبارات ObjectPronounVsPossessivePronounGate.

تَوصيَة المُستَخدِم 2026-05-25:
  test_fa_uktubuhu_remains_imperative_verb
  test_hu_suffix_after_imperative_is_object_not_possessive
  test_allamahu_remains_verb_with_object_pronoun
  test_yuallimukum_remains_verb_with_object_pronoun

  + إِبقاء اختبارات الـpossessive (regression):
  test_ajalihi_remains_blocked
  test_rabbihi_remains_blocked
"""

from __future__ import annotations

from object_pronoun_vs_possessive_gate import (
    classify_attached_pronoun,
    AttachedPronounRole,
)
from verb_form_contract import evaluate_verb_form
from i3rab_engine.layer1 import WordClassClassifier

CLF = WordClassClassifier()


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
# Object pronoun (مَفعول) — يَجِب أَلّا يَكسِر الفِعل
# ─────────────────────────────────────────────────────────────────

def test_fa_uktubuhu_remains_imperative_verb():
    """فَٱكْتُبُوهُ — ف + اكتبوا + هـ مَفعول. يَجِب أَن يَبقى فِعل أَمر."""
    cls = classify_attached_pronoun("فَٱكْتُبُوهُ")
    assert cls.role == AttachedPronounRole.OBJECT_OF_VERB, \
        f"فَٱكْتُبُوهُ should be OBJECT, got {cls.role}"
    v = evaluate_verb_form("فَٱكْتُبُوهُ")
    assert v.kind == "Certificate", f"contract: must be Certificate, got {v.kind}"
    r = _classify("فَٱكْتُبُوهُ")
    assert r["word_class"] == "FIIL", \
        f"layer1: فَٱكْتُبُوهُ must be FIIL, got {r['word_class']}"


def test_hu_suffix_after_imperative_is_object_not_possessive():
    """اكْتُبْهُ — هـ بَعد فِعل أَمر = مَفعول لا مِلكيَّة."""
    cls = classify_attached_pronoun("اكْتُبْهُ")
    assert cls.role == AttachedPronounRole.OBJECT_OF_VERB
    v = evaluate_verb_form("اكْتُبْهُ")
    assert v.kind == "Certificate"


def test_allamahu_remains_verb_with_object_pronoun():
    """عَلَّمَهُ — فِعل form II + هـ مَفعول."""
    cls = classify_attached_pronoun("عَلَّمَهُ")
    assert cls.role == AttachedPronounRole.OBJECT_OF_VERB
    r = _classify("عَلَّمَهُ")
    assert r["word_class"] == "FIIL", \
        f"عَلَّمَهُ should be FIIL, got {r['word_class']}"


def test_yuallimukum_remains_verb_with_object_pronoun():
    """وَيُعَلِّمُكُمُ — و + يُعَلِّمُ + كُم مَفعول."""
    cls = classify_attached_pronoun("وَيُعَلِّمُكُمُ")
    assert cls.role == AttachedPronounRole.OBJECT_OF_VERB
    r = _classify("وَيُعَلِّمُكُمُ")
    assert r["word_class"] == "FIIL", \
        f"وَيُعَلِّمُكُمُ should be FIIL, got {r['word_class']}"


def test_nazzalaha_remains_verb_with_object():
    """نَزَّلَهَا — فِعل form II + ها مَفعول."""
    cls = classify_attached_pronoun("نَزَّلَهَا")
    assert cls.role == AttachedPronounRole.OBJECT_OF_VERB


# ─────────────────────────────────────────────────────────────────
# Possessive (مِلكيَّة) — يَجِب أَن يَبقى مَحجوبًا (regression)
# ─────────────────────────────────────────────────────────────────

def test_ajalihi_remains_blocked():
    """أَجَلِهِ — اسم مَجرور + هـ مِلكيَّة. لا يَزال مَحجوب."""
    cls = classify_attached_pronoun("أَجَلِهِ")
    assert cls.role == AttachedPronounRole.POSSESSIVE_OF_NOUN
    v = evaluate_verb_form("أَجَلِهِ")
    assert v.kind == "Zero"
    r = _classify("أَجَلِهِ")
    assert r["word_class"] != "FIIL"


def test_rabbihi_remains_blocked():
    """رَبِّهِ — اسم مَجرور + هـ مِلكيَّة."""
    cls = classify_attached_pronoun("رَبِّهِ")
    assert cls.role == AttachedPronounRole.POSSESSIVE_OF_NOUN


def test_kitabihi_remains_blocked():
    """كِتَابِهِ — اسم مَجرور + هـ مِلكيَّة."""
    cls = classify_attached_pronoun("كِتَابِهِ")
    assert cls.role == AttachedPronounRole.POSSESSIVE_OF_NOUN


# ─────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────

def test_no_suffix_returns_none():
    cls = classify_attached_pronoun("كَتَبَ")
    assert cls.role == AttachedPronounRole.NONE


def test_rabbahu_after_verb_distinction():
    """رَبَّهُ — نَهايَة فَتحَة عَلى ب + هـ. غامِض (يُمكِن أَن يَكون اسم
    أَو فِعل مُضَعَّف رَبَّ + هـ مَفعول). نَتأَكَّد فَقَط أَنّ النَّظام
    لا يُسَبِّب exception."""
    cls = classify_attached_pronoun("رَبَّهُ")
    assert cls.role in (
        AttachedPronounRole.OBJECT_OF_VERB,
        AttachedPronounRole.POSSESSIVE_OF_NOUN,
    )


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("ObjectPronoun vs Possessive Gate Tests")
print("=" * 60)

test("test_fa_uktubuhu_remains_imperative_verb", test_fa_uktubuhu_remains_imperative_verb)
test("test_hu_suffix_after_imperative_is_object_not_possessive",
     test_hu_suffix_after_imperative_is_object_not_possessive)
test("test_allamahu_remains_verb_with_object_pronoun",
     test_allamahu_remains_verb_with_object_pronoun)
test("test_yuallimukum_remains_verb_with_object_pronoun",
     test_yuallimukum_remains_verb_with_object_pronoun)
test("test_nazzalaha_remains_verb_with_object", test_nazzalaha_remains_verb_with_object)
test("test_ajalihi_remains_blocked", test_ajalihi_remains_blocked)
test("test_rabbihi_remains_blocked", test_rabbihi_remains_blocked)
test("test_kitabihi_remains_blocked", test_kitabihi_remains_blocked)
test("test_no_suffix_returns_none", test_no_suffix_returns_none)
test("test_rabbahu_after_verb_distinction", test_rabbahu_after_verb_distinction)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
