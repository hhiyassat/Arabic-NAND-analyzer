#!/usr/bin/env python3
"""test_verb_form_contract.py — اختبارات VerbFormContract.

تَنفيذ التَّوصيَة:
  test_fa_uktubuhu_is_verb_not_harf
  test_wa_l_yaktub_is_jussive_command_verb
  test_fa_l_yaktub_is_jussive_command_verb
  test_wa_l_yumlil_is_jussive_command_verb
  test_fa_l_yumlil_is_jussive_command_verb
  test_wa_ittaqoo_is_imperative_plural
  test_wa_ashhidoo_is_imperative_plural
  test_kana_is_verb_not_harf
  test_laysa_is_defective_verb_not_harf
  test_yaktub_indicative
  test_bare_pv_is_certificate
  test_nominal_not_verb
  test_tanwin_hard_gate
"""

from __future__ import annotations

from verb_form_contract import evaluate_verb_form, get_audit, reset_audit
from i3rab_engine.layer1 import WordClassClassifier


CLF = WordClassClassifier()


def _classify(token):
    return CLF.classify(token)


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
# 1. Imperative verbs (CV) with conjunctive prefix
# ─────────────────────────────────────────────────────────────────

def test_fa_uktubuhu_is_verb_not_harf():
    v = evaluate_verb_form("فَاكْتُبُوهُ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "CV", f"expected CV, got {v.aspect}"
    # Layer 1 integration
    r = _classify("فَاكْتُبُوهُ")
    assert r["word_class"] == "FIIL", f"expected FIIL, got {r['word_class']}"


def test_wa_ittaqoo_is_imperative_plural():
    v = evaluate_verb_form("وَٱتَّقُوا")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "CV", f"expected CV, got {v.aspect}"
    assert v.number == "PL", f"expected PL, got {v.number}"


def test_wa_ashhidoo_is_imperative_plural():
    v = evaluate_verb_form("وَأَشْهِدُوا")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    # MOOD could be JUSS (5-verbs noon-deleted) — both مَجزوم/أَمر acceptable
    r = _classify("وَأَشْهِدُوا")
    assert r["word_class"] == "FIIL", f"expected FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 2. Jussive command (ل + يَ/يُ + مُضارِع)
# ─────────────────────────────────────────────────────────────────

def test_wa_l_yaktub_is_jussive_command_verb():
    v = evaluate_verb_form("وَلْيَكْتُبْ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV", f"expected IV, got {v.aspect}"
    assert v.mood == "JUSS", f"expected JUSS, got {v.mood}"
    assert v.prefix_stack.has_lam_amr, "expected has_lam_amr"
    assert v.prefix_stack.has_conj, "expected has_conj"


def test_fa_l_yaktub_is_jussive_command_verb():
    v = evaluate_verb_form("فَلْيَكْتُبْ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV"
    assert v.mood == "JUSS"


def test_wa_l_yumlil_is_jussive_command_verb():
    v = evaluate_verb_form("وَلْيُمْلِلْ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV"
    assert v.mood == "JUSS"


def test_fa_l_yumlil_is_jussive_command_verb():
    v = evaluate_verb_form("فَلْيُمْلِلْ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV"
    assert v.mood == "JUSS"


# ─────────────────────────────────────────────────────────────────
# 3. kana-family (defective verbs)
# ─────────────────────────────────────────────────────────────────

def test_kana_is_verb_not_harf():
    v = evaluate_verb_form("كَانَ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.lemma == "كان", f"expected lemma كان, got {v.lemma}"
    r = _classify("كَانَ")
    assert r["word_class"] == "FIIL", f"expected FIIL, got {r['word_class']}"


def test_laysa_is_defective_verb_not_harf():
    v = evaluate_verb_form("لَيْسَ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.lemma == "ليس", f"expected lemma ليس, got {v.lemma}"
    r = _classify("لَيْسَ")
    assert r["word_class"] == "FIIL", f"expected FIIL, got {r['word_class']}"


def test_fa_laysa_is_verb_not_harf():
    """فَلَيْسَ — ف + ليس → فِعل (لَيس HARF)."""
    v = evaluate_verb_form("فَلَيْسَ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.lemma == "ليس", f"expected lemma ليس, got {v.lemma}"
    r = _classify("فَلَيْسَ")
    assert r["word_class"] == "FIIL", \
        f"فَلَيْسَ should be FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 4. Standard IV / PV — sanity
# ─────────────────────────────────────────────────────────────────

def test_yaktub_indicative():
    v = evaluate_verb_form("يَكْتُبُ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV"
    assert v.mood == "INDIC"


def test_bare_pv_certificate():
    v = evaluate_verb_form("كَتَبَ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "PV"


def test_taktuboon_indicative_not_subj():
    """تَكْتُبُونَ — جَمع مُذَكَّر سالِم مَرفوع، لَيس مَنصوب."""
    v = evaluate_verb_form("تَكْتُبُونَ")
    assert v.kind == "Certificate"
    assert v.mood == "INDIC", f"expected INDIC, got {v.mood}"


# ─────────────────────────────────────────────────────────────────
# 5. Non-verbs — must be Zero
# ─────────────────────────────────────────────────────────────────

def test_nominal_with_tanwin_is_zero():
    v = evaluate_verb_form("كِتَابٌ")
    assert v.kind == "Zero", f"tanwin must be Zero, got {v.kind}"


def test_tanwin_fath_hard_gate():
    v = evaluate_verb_form("تِجَارَةً")
    assert v.kind == "Zero", f"tanwin fath must be Zero, got {v.kind}"


def test_relative_pronoun_is_zero():
    v = evaluate_verb_form("ٱلَّذِينَ")
    assert v.kind == "Zero", f"relative pronoun must be Zero, got {v.kind}"


def test_tafdeel_afal_is_zero():
    """أَفْضَلُ — اسم تَفضيل، لَيس فِعل."""
    v = evaluate_verb_form("أَفْضَلُ")
    assert v.kind == "Zero", f"tafdeel must be Zero, got {v.kind}"


# ─────────────────────────────────────────────────────────────────
# 6. Layer-1 integration regression
# ─────────────────────────────────────────────────────────────────

def test_layer1_integration_kana_not_harf():
    """قَبل الإِصلاح كانَ كان/ليس يُصَنَّفان HARF بِسَبَب الـoperators CSV."""
    for w in ("كَانَ", "لَيْسَ", "وَكَانَ", "فَلَيْسَ"):
        r = _classify(w)
        assert r["word_class"] == "FIIL", \
            f"{w} should be FIIL after VerbFormContract, got {r['word_class']}"


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("VerbFormContract Tests")
print("=" * 60)

reset_audit()

test("test_fa_uktubuhu_is_verb_not_harf", test_fa_uktubuhu_is_verb_not_harf)
test("test_wa_ittaqoo_is_imperative_plural", test_wa_ittaqoo_is_imperative_plural)
test("test_wa_ashhidoo_is_imperative_plural", test_wa_ashhidoo_is_imperative_plural)
test("test_wa_l_yaktub_is_jussive_command_verb", test_wa_l_yaktub_is_jussive_command_verb)
test("test_fa_l_yaktub_is_jussive_command_verb", test_fa_l_yaktub_is_jussive_command_verb)
test("test_wa_l_yumlil_is_jussive_command_verb", test_wa_l_yumlil_is_jussive_command_verb)
test("test_fa_l_yumlil_is_jussive_command_verb", test_fa_l_yumlil_is_jussive_command_verb)
test("test_kana_is_verb_not_harf", test_kana_is_verb_not_harf)
test("test_laysa_is_defective_verb_not_harf", test_laysa_is_defective_verb_not_harf)
test("test_fa_laysa_is_verb_not_harf", test_fa_laysa_is_verb_not_harf)
test("test_yaktub_indicative", test_yaktub_indicative)
test("test_bare_pv_certificate", test_bare_pv_certificate)
test("test_taktuboon_indicative_not_subj", test_taktuboon_indicative_not_subj)
test("test_nominal_with_tanwin_is_zero", test_nominal_with_tanwin_is_zero)
test("test_tanwin_fath_hard_gate", test_tanwin_fath_hard_gate)
test("test_relative_pronoun_is_zero", test_relative_pronoun_is_zero)
test("test_tafdeel_afal_is_zero", test_tafdeel_afal_is_zero)
test("test_layer1_integration_kana_not_harf", test_layer1_integration_kana_not_harf)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
print()
print(f"audit: {get_audit()}")
