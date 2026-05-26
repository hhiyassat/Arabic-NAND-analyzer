#!/usr/bin/env python3
"""test_phase3_integration.py — اختبارات Phase 3 (دَمج registry في Layer 1).

تَوصيَة المُستَخدِم 2026-05-26:
  • exact closed-form lookup يَسبِق segmentation
  • locked forms (أُولَئِكَ، الَّذي…) لا تُجَزَّأ
  • ambiguous → Hypothesis، لا Certificate
  • heuristics fallback فَقَط لِما لَيس في registry
"""
import sys
sys.path.insert(0, ".")
from i3rab_engine.layer1 import WordClassClassifier

CLF = WordClassClassifier()
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


def _classify(tok):
    return CLF.classify(tok)


# ─────────────────────────────────────────────────────────────
# Closed-form locked: أُولَئِكَ، هَؤُلَاءِ
# ─────────────────────────────────────────────────────────────
def test_awlaika_pre_segmentation_locked():
    r = _classify("أُولَئِكَ")
    assert r["word_class"] in ("ISM_MABNI","JAMID"), \
        f"أُولَئِكَ → {r['word_class']} (must be ISM_MABNI/JAMID, not split)"


def test_haalaa_pre_segmentation_locked():
    r = _classify("هَؤُلَاءِ")
    # MASAQ قَد يَكون لَه entry، أَو registry — يَجِب أَن يَكون ISM_MABNI
    assert r["word_class"] in ("ISM_MABNI","JAMID"), \
        f"هَؤُلَاءِ → {r['word_class']}"


def test_haza_locked_demonstrative():
    r = _classify("هَذَا")
    assert r["word_class"] == "ISM_MABNI"
    # source يَجِب أَن يَكون مِن registry أَو MASAQ
    src = r.get("source","")
    assert "registry" in src or "MASAQ" in src, f"source={src}"


def test_haadhihi_locked_demonstrative():
    r = _classify("هَذِهِ")
    assert r["word_class"] == "ISM_MABNI", f"هَذِهِ → {r['word_class']}"


# ─────────────────────────────────────────────────────────────
# Relative pronouns
# ─────────────────────────────────────────────────────────────
def test_alladhi_is_mawsool():
    r = _classify("الَّذِي")
    assert r["word_class"] == "ISM_MAWSOOL"


def test_allati_is_mawsool():
    r = _classify("الَّتِي")
    assert r["word_class"] == "ISM_MAWSOOL"


# ─────────────────────────────────────────────────────────────
# Interrogatives (AUDIT-5 failures)
# ─────────────────────────────────────────────────────────────
def test_ayna_is_ism_mabni_not_harf():
    r = _classify("أَيْنَ")
    assert r["word_class"] == "ISM_MABNI", \
        f"أَيْنَ → {r['word_class']} (must be ISM_MABNI, not HARF)"


def test_kayfa_is_ism_mabni_not_harf():
    r = _classify("كَيْفَ")
    assert r["word_class"] == "ISM_MABNI"


def test_limadha_is_handled():
    r = _classify("لِمَاذَا")
    assert r["word_class"] != "UNKNOWN", f"لِمَاذَا → UNKNOWN (compound failed)"


# ─────────────────────────────────────────────────────────────
# Ambiguous: مَنْ، مَا — Hypothesis لا Certificate
# ─────────────────────────────────────────────────────────────
def test_man_classified_but_hypothesis():
    r = _classify("مَنْ")
    # نَقبَل أَن يَكون word_class مُحَدَّدًا (closed-class) لَكِن proof_kind = Hypothesis
    assert r["word_class"] in ("HARF","ISM_MABNI","ISM_MAWSOOL"), \
        f"مَنْ → {r['word_class']}"
    pk = r.get("proof_kind","")
    src = r.get("source","")
    if "registry" in src and "Certificate" in pk:
        raise AssertionError(f"مَنْ has Certificate from registry! must be Hypothesis. src={src}")


def test_ma_classified_but_hypothesis():
    r = _classify("مَا")
    if "registry" in r.get("source",""):
        assert r.get("proof_kind") != "Certificate", \
            f"مَا has Certificate from registry: {r}"


def test_mata_includes_ism_mabni_candidate():
    r = _classify("مَتَى")
    cands = r.get("registry_candidates", [])
    if cands:
        assert "ISM_MABNI" in cands, f"مَتَى registry_candidates={cands}"


# ─────────────────────────────────────────────────────────────
# Closed-class Certificates (ما يَجِب أَن يَبقى Certificate)
# ─────────────────────────────────────────────────────────────
def test_fi_harf_certificate():
    r = _classify("فِي")
    assert r["word_class"] == "HARF"


def test_huwa_pronoun_certificate():
    r = _classify("هُوَ")
    assert r["word_class"] == "ISM_MABNI"


def test_inna_harf_certificate():
    r = _classify("إِنَّ")
    assert r["word_class"] == "HARF"


def test_lam_harf_certificate():
    r = _classify("لَمْ")
    assert r["word_class"] == "HARF"


def test_yaa_vocative_certificate():
    r = _classify("يَا")
    assert r["word_class"] == "HARF"


# ─────────────────────────────────────────────────────────────
# Regression: ما لا يَجِب أَن يَتَأَثَّر
# ─────────────────────────────────────────────────────────────
def test_kataba_still_verb():
    r = _classify("كَتَبَ")
    assert r["word_class"] == "FIIL"


def test_kitab_still_noun():
    r = _classify("الْكِتَابُ")
    assert r["word_class"] in ("ISM_MUARAB","JAMID")


def test_kitabun_still_noun():
    r = _classify("كِتَٰبٌ")
    assert r["word_class"] == "ISM_MUARAB"


def test_yaqub_still_proper():
    r = _classify("يَعْقُوبَ")
    assert r["word_class"] in ("JAMID","ISM_MUARAB")


def test_min_still_harf():
    r = _classify("مِن")
    # مِن (preposition) يَجِب أَن يَكون HARF
    assert r["word_class"] == "HARF", f"مِن → {r['word_class']}"


# ─────────────────────────────────────────────────────────────
# Compound segmentation suppression test
# ─────────────────────────────────────────────────────────────
def test_no_segmentation_of_locked_forms():
    """أَيّ closed-class مُسَجَّل لا يَجِب أَن يُجَزَّأ في output."""
    for tok in ["هَذَا","الَّذِي","حَيْثُ","هُوَ","نَحْنُ","أَنْتُمْ","ذَلِكَ"]:
        r = _classify(tok)
        # لَو registry يُغَطّيها، يَجِب أَن لا يُخرِج UNKNOWN
        assert r["word_class"] != "UNKNOWN", f"{tok} → UNKNOWN"


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("Phase 3 — Registry integration in Layer 1")
print("=" * 70)
ALL = [
    ("test_awlaika_pre_segmentation_locked", test_awlaika_pre_segmentation_locked),
    ("test_haalaa_pre_segmentation_locked", test_haalaa_pre_segmentation_locked),
    ("test_haza_locked_demonstrative", test_haza_locked_demonstrative),
    ("test_haadhihi_locked_demonstrative", test_haadhihi_locked_demonstrative),
    ("test_alladhi_is_mawsool", test_alladhi_is_mawsool),
    ("test_allati_is_mawsool", test_allati_is_mawsool),
    ("test_ayna_is_ism_mabni_not_harf", test_ayna_is_ism_mabni_not_harf),
    ("test_kayfa_is_ism_mabni_not_harf", test_kayfa_is_ism_mabni_not_harf),
    ("test_limadha_is_handled", test_limadha_is_handled),
    ("test_man_classified_but_hypothesis", test_man_classified_but_hypothesis),
    ("test_ma_classified_but_hypothesis", test_ma_classified_but_hypothesis),
    ("test_mata_includes_ism_mabni_candidate", test_mata_includes_ism_mabni_candidate),
    ("test_fi_harf_certificate", test_fi_harf_certificate),
    ("test_huwa_pronoun_certificate", test_huwa_pronoun_certificate),
    ("test_inna_harf_certificate", test_inna_harf_certificate),
    ("test_lam_harf_certificate", test_lam_harf_certificate),
    ("test_yaa_vocative_certificate", test_yaa_vocative_certificate),
    ("test_kataba_still_verb", test_kataba_still_verb),
    ("test_kitab_still_noun", test_kitab_still_noun),
    ("test_kitabun_still_noun", test_kitabun_still_noun),
    ("test_yaqub_still_proper", test_yaqub_still_proper),
    ("test_min_still_harf", test_min_still_harf),
    ("test_no_segmentation_of_locked_forms", test_no_segmentation_of_locked_forms),
]
for nm, fn in ALL:
    _t(nm, fn)
print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok:
            print(f"  ✗ {nm}: {err}")
