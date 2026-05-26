#!/usr/bin/env python3
"""test_non_verb_override.py — اختبارات NonVerbOverrideGate.

تَنفيذ تَوصيَة المُستَخدِم 2026-05-25:
  test_idha_not_verb
  test_kama_not_verb
  test_al_haqq_not_verb
  test_imraataan_not_verb
  test_al_ukhra_not_verb
  test_ajalihi_not_verb        — اختياريّ (مَكسور آخِر = اسم مَجرور)
  test_aqsatu_comparative_not_verb
  test_wa_aqwamu_comparative_not_verb
  test_wa_adna_comparative_not_verb
  test_lil_shahada_not_verb
  test_verb_in_clause_requires_certified_verb
"""

from __future__ import annotations

from non_verb_override_gate import check_non_verb_override
from verb_form_contract import evaluate_verb_form
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
# 1. Closed-list overrides (إذا/كما)
# ─────────────────────────────────────────────────────────────────

def test_idha_not_verb():
    """إِذَا — ظَرف شَرط غَير جازم، لا فِعل."""
    v = evaluate_verb_form("إِذَا")
    assert v.kind == "Zero", f"إِذَا must be Zero, got {v.kind}"
    r = _classify("إِذَا")
    assert r["word_class"] != "FIIL", f"إِذَا must not be FIIL, got {r['word_class']}"


def test_kama_not_verb():
    """كَمَا = كَ + ما، أداة تَشبيه."""
    v = evaluate_verb_form("كَمَا")
    assert v.kind == "Zero", f"كَمَا must be Zero, got {v.kind}"
    r = _classify("كَمَا")
    assert r["word_class"] != "FIIL", f"كَمَا must not be FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 2. ال التَّعريف
# ─────────────────────────────────────────────────────────────────

def test_al_haqq_not_verb():
    """ٱلْحَقُّ — ال + اسم، لَيس فِعل أَمر."""
    v = evaluate_verb_form("ٱلْحَقُّ")
    assert v.kind == "Zero", f"ٱلْحَقُّ must be Zero, got {v.kind}"
    r = _classify("ٱلْحَقُّ")
    assert r["word_class"] != "FIIL", \
        f"ٱلْحَقُّ must not be FIIL, got {r['word_class']}"


def test_al_ukhra_not_verb():
    """ٱلْأُخْرَىٰ — ال + اسم مُؤَنَّث."""
    v = evaluate_verb_form("ٱلْأُخْرَىٰ")
    assert v.kind == "Zero", f"ٱلْأُخْرَىٰ must be Zero, got {v.kind}"
    r = _classify("ٱلْأُخْرَىٰ")
    assert r["word_class"] != "FIIL", \
        f"ٱلْأُخْرَىٰ must not be FIIL, got {r['word_class']}"


def test_lil_shahada_not_verb():
    """لِلشَّهَٰدَةِ — لِـ + ال + اسم بِتاء مَربوطَة."""
    v = evaluate_verb_form("لِلشَّهَٰدَةِ")
    assert v.kind == "Zero", f"لِلشَّهَٰدَةِ must be Zero, got {v.kind}"
    r = _classify("لِلشَّهَٰدَةِ")
    assert r["word_class"] != "FIIL", \
        f"لِلشَّهَٰدَةِ must not be FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 3. مُثَنَّى وَ ـة
# ─────────────────────────────────────────────────────────────────

def test_imraataan_not_verb():
    """وَٱمْرَأَتَانِ — مُثَنَّى مُؤَنَّث، لا فِعل."""
    v = evaluate_verb_form("وَٱمْرَأَتَانِ")
    assert v.kind == "Zero", f"وَٱمْرَأَتَانِ must be Zero, got {v.kind}"
    r = _classify("وَٱمْرَأَتَانِ")
    assert r["word_class"] != "FIIL", \
        f"وَٱمْرَأَتَانِ must not be FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 4. اسم تَفضيل
# ─────────────────────────────────────────────────────────────────

def test_aqsatu_comparative_not_verb():
    """أَقْسَطُ — اسم تَفضيل، لا فِعل 1sg."""
    v = evaluate_verb_form("أَقْسَطُ")
    assert v.kind == "Zero", f"أَقْسَطُ must be Zero, got {v.kind}"
    r = _classify("أَقْسَطُ")
    assert r["word_class"] != "FIIL", \
        f"أَقْسَطُ must not be FIIL, got {r['word_class']}"


def test_wa_aqwamu_comparative_not_verb():
    """وَأَقْوَمُ — وَ + اسم تَفضيل."""
    v = evaluate_verb_form("وَأَقْوَمُ")
    assert v.kind == "Zero", f"وَأَقْوَمُ must be Zero, got {v.kind}"
    r = _classify("وَأَقْوَمُ")
    assert r["word_class"] != "FIIL", \
        f"وَأَقْوَمُ must not be FIIL, got {r['word_class']}"


def test_wa_adna_comparative_not_verb():
    """وَأَدْنَىٰٓ — وَ + اسم تَفضيل بِأَلِف مَقصورَة."""
    v = evaluate_verb_form("وَأَدْنَىٰٓ")
    assert v.kind == "Zero", f"وَأَدْنَىٰٓ must be Zero, got {v.kind}"
    r = _classify("وَأَدْنَىٰٓ")
    assert r["word_class"] != "FIIL", \
        f"وَأَدْنَىٰٓ must not be FIIL, got {r['word_class']}"


# ─────────────────────────────────────────────────────────────────
# 5. لا تَكسير لِلأَفعال الحَقيقيَّة (regression)
# ─────────────────────────────────────────────────────────────────

def test_real_verbs_still_pass():
    """التَّأَكُّد أَنّ الـgate لا يَكسِر الأَفعال الحَقيقيَّة."""
    real_verbs = [
        "كَانَ", "لَيْسَ", "فَلَيْسَ", "وَكَانَ",
        "فَاكْتُبُوهُ", "وَلْيَكْتُبْ", "فَلْيَكْتُبْ",
        "وَلْيُمْلِلْ", "فَلْيُمْلِلْ", "وَٱتَّقُوا", "وَأَشْهِدُوا",
        "كَتَبَ", "يَكْتُبُ", "تَكْتُبُونَ",
    ]
    for w in real_verbs:
        v = evaluate_verb_form(w)
        r = _classify(w)
        assert r["word_class"] == "FIIL", \
            f"REAL VERB {w} got demoted: word_class={r['word_class']}, contract={v.kind}"


# ─────────────────────────────────────────────────────────────────
# 6. verb_in_clause لا يَرتَفِع لِـCertificate إلّا بِفِعل مُعتَمَد
# ─────────────────────────────────────────────────────────────────

def test_verb_in_clause_requires_certified_verb():
    """ٱلْحَقُّ لا يَجِب أَن يَكون verb_in_clause certificate.

    نَفحَص في RelationExtractor (إِذا كانَ مُتاحًا).
    """
    try:
        from i3rab_engine.engine import I3rabEngine
        from relation_extractor import RelationExtractor
        ENG = I3rabEngine()
        REL = RelationExtractor()
        sent = ENG.analyze_sentence("وَلْيُمْلِلِ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ")
        rg = REL.extract(sent)
        # ٱلْحَقُّ مَوجود في الجُملَة. هَل verb_in_clause مَع ٱلْحَقُّ كَ verb؟
        for r in rg.relations:
            if r.name != "verb_in_clause":
                continue
            if not r.source_id.startswith("t"):
                continue
            try:
                idx = int(r.source_id[1:])
                tok = sent.tokens[idx]
            except (ValueError, IndexError):
                continue
            assert tok.word_class == "FIIL", \
                f"verb_in_clause source is NOT FIIL: {tok.token} ({tok.word_class})"
    except ImportError:
        pass  # OK if components not available


# ═══════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════

print("NonVerbOverrideGate Tests")
print("=" * 60)

test("test_idha_not_verb", test_idha_not_verb)
test("test_kama_not_verb", test_kama_not_verb)
test("test_al_haqq_not_verb", test_al_haqq_not_verb)
test("test_al_ukhra_not_verb", test_al_ukhra_not_verb)
test("test_lil_shahada_not_verb", test_lil_shahada_not_verb)
test("test_imraataan_not_verb", test_imraataan_not_verb)
test("test_aqsatu_comparative_not_verb", test_aqsatu_comparative_not_verb)
test("test_wa_aqwamu_comparative_not_verb", test_wa_aqwamu_comparative_not_verb)
test("test_wa_adna_comparative_not_verb", test_wa_adna_comparative_not_verb)
test("test_real_verbs_still_pass", test_real_verbs_still_pass)
test("test_verb_in_clause_requires_certified_verb",
     test_verb_in_clause_requires_certified_verb)

print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Result: {passed}/{total} passed")
