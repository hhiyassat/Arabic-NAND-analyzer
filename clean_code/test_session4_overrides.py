#!/usr/bin/env python3
"""test_session4_overrides.py — اختبارات الجَلسَة 4 (5 عائِلات جَديدَة).

J. PastSpeakerNaContract
K. StablePronounOverrideContract
L. WeakPastVerbContract (regression fix لِـ شَآءَ)
M. EventAttachmentGuard
N. FusedPrepPronoun regression
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
        results.append((name, False, f"ERROR: {e}"))
        print(f"  ✗ {name}: {e}")


def _wc(tok):
    return CLF.classify(tok)["word_class"]


def _info(tok):
    return CLF.classify(tok)


def _check(tok, exp_kinds):
    wc = _wc(tok)
    assert wc in exp_kinds, f"{tok} → {wc} (expected {exp_kinds})"


# ─────────────────────────────────────────────────────────────
# J. PastSpeakerNa
# ─────────────────────────────────────────────────────────────
def test_akhadhna_is_past_verb():
    _check("أَخَذْنَا", {"FIIL"})


def test_wa_arsalna_is_past_verb():
    _check("وَأَرْسَلْنَآ", {"FIIL"})


def test_wa_arsalna_is_past_no_alif():
    _check("وَأَرْسَلْنَا", {"FIIL"})


def test_arsalna_is_past_verb():
    _check("أَرْسَلْنَا", {"FIIL"})


def test_jaalna_is_past_verb():
    _check("جَعَلْنَا", {"FIIL"})


def test_khalaqna_is_past_verb():
    _check("خَلَقْنَا", {"FIIL"})


def test_baathnakum_remains_past_verb():
    _check("بَعَثْنَٰكُم", {"FIIL"})


def test_na_past_tense_not_present():
    info = _info("أَخَذْنَا")
    if info.get("word_class") == "FIIL":
        tense = info.get("tense") or info.get("verb_tense") or ""
        # accept "past" or empty — must NOT be "present"
        assert tense != "present", f"أَخَذْنَا tense={tense}"


# ─────────────────────────────────────────────────────────────
# K. StablePronounOverride
# ─────────────────────────────────────────────────────────────
def test_huwa_is_ism_mabni():
    _check("هُوَ", {"ISM_MABNI"})


def test_huwa_not_harf():
    wc = _wc("هُوَ")
    assert wc != "HARF", f"هُوَ → {wc} (must not be HARF)"


def test_hum_is_ism_mabni():
    _check("هُمْ", {"ISM_MABNI"})


def test_hiya_is_ism_mabni():
    _check("هِيَ", {"ISM_MABNI"})


def test_anta_is_ism_mabni():
    _check("أَنْتَ", {"ISM_MABNI"})


def test_ana_is_ism_mabni():
    _check("أَنَا۠", {"ISM_MABNI", "ISM_MUARAB"})


def test_wa_huwa_is_pronoun_class():
    # وَهُوَ should be treated as conjunction + pronoun
    # The composite tok may either be split or classified as ISM_MABNI
    wc = _wc("وَهُوَ")
    assert wc in {"ISM_MABNI", "HARF"}, f"وَهُوَ → {wc}"


# ─────────────────────────────────────────────────────────────
# L. WeakPastVerb regression
# ─────────────────────────────────────────────────────────────
def test_sha_a_is_past_verb():
    _check("شَآءَ", {"FIIL"})


def test_sha_a_not_ism_muarab():
    wc = _wc("شَآءَ")
    assert wc != "ISM_MUARAB", f"شَآءَ → {wc} (must not be ISM_MUARAB)"


def test_jaa_is_past_verb():
    _check("جَآءَ", {"FIIL"})


def test_jaahum_is_past_verb():
    _check("جَآءَهُمْ", {"FIIL"})


def test_hada_is_past_verb():
    _check("هَدَىٰ", {"FIIL"})


def test_haqqa_is_past_verb():
    _check("حَقَّ", {"FIIL"})


def test_wa_sha_a_is_past_verb():
    _check("وَشَآءَ", {"FIIL"})


def test_fa_sha_a_is_past_verb():
    _check("فَشَآءَ", {"FIIL"})


# ─────────────────────────────────────────────────────────────
# N. FusedPrepPronoun regression
# ─────────────────────────────────────────────────────────────
def test_faminhum_is_harf():
    _check("فَمِنْهُم", {"HARF"})


def test_waminhum_is_harf():
    _check("وَمِنْهُم", {"HARF"})


def test_anhu_is_harf():
    _check("عَنْهُ", {"HARF"})


def test_bihi_is_harf():
    _check("بِهِ", {"HARF"})


def test_lahu_is_harf():
    _check("لَهُ", {"HARF"})


# ─────────────────────────────────────────────────────────────
# M. EventAttachmentGuard (طَبَقَة Layer4/5 — اختِبار وَجود الفِعل)
# ─────────────────────────────────────────────────────────────
def test_tahwa_is_present_verb():
    _check("تَهْوَىٰ", {"FIIL"})


def test_anfusuhum_is_noun_not_verb():
    _check("أَنفُسُهُمْ", {"ISM_MUARAB", "JAMID"})


# ─────────────────────────────────────────────────────────────
# Regression (no breakage)
# ─────────────────────────────────────────────────────────────
def test_hamma_remains_verb():
    _check("هَمَّ", {"FIIL"})


def test_allamahu_remains_verb():
    _check("عَلَّمَهُۥ", {"FIIL"})


def test_kataba_remains_verb():
    _check("كَتَبَ", {"FIIL"})


def test_alkitabu_remains_noun():
    _check("الْكِتَابُ", {"ISM_MUARAB", "JAMID"})


def test_min_remains_harf():
    _check("مِن", {"HARF"})


print("Session 4 Override Contracts Tests")
print("=" * 70)

ALL = [
    # J
    ("test_akhadhna_is_past_verb", test_akhadhna_is_past_verb),
    ("test_wa_arsalna_is_past_verb", test_wa_arsalna_is_past_verb),
    ("test_wa_arsalna_is_past_no_alif", test_wa_arsalna_is_past_no_alif),
    ("test_arsalna_is_past_verb", test_arsalna_is_past_verb),
    ("test_jaalna_is_past_verb", test_jaalna_is_past_verb),
    ("test_khalaqna_is_past_verb", test_khalaqna_is_past_verb),
    ("test_baathnakum_remains_past_verb", test_baathnakum_remains_past_verb),
    ("test_na_past_tense_not_present", test_na_past_tense_not_present),
    # K
    ("test_huwa_is_ism_mabni", test_huwa_is_ism_mabni),
    ("test_huwa_not_harf", test_huwa_not_harf),
    ("test_hum_is_ism_mabni", test_hum_is_ism_mabni),
    ("test_hiya_is_ism_mabni", test_hiya_is_ism_mabni),
    ("test_anta_is_ism_mabni", test_anta_is_ism_mabni),
    ("test_ana_is_ism_mabni", test_ana_is_ism_mabni),
    ("test_wa_huwa_is_pronoun_class", test_wa_huwa_is_pronoun_class),
    # L
    ("test_sha_a_is_past_verb", test_sha_a_is_past_verb),
    ("test_sha_a_not_ism_muarab", test_sha_a_not_ism_muarab),
    ("test_jaa_is_past_verb", test_jaa_is_past_verb),
    ("test_jaahum_is_past_verb", test_jaahum_is_past_verb),
    ("test_hada_is_past_verb", test_hada_is_past_verb),
    ("test_haqqa_is_past_verb", test_haqqa_is_past_verb),
    ("test_wa_sha_a_is_past_verb", test_wa_sha_a_is_past_verb),
    ("test_fa_sha_a_is_past_verb", test_fa_sha_a_is_past_verb),
    # N
    ("test_faminhum_is_harf", test_faminhum_is_harf),
    ("test_waminhum_is_harf", test_waminhum_is_harf),
    ("test_anhu_is_harf", test_anhu_is_harf),
    ("test_bihi_is_harf", test_bihi_is_harf),
    ("test_lahu_is_harf", test_lahu_is_harf),
    # M
    ("test_tahwa_is_present_verb", test_tahwa_is_present_verb),
    ("test_anfusuhum_is_noun_not_verb", test_anfusuhum_is_noun_not_verb),
    # regression
    ("test_hamma_remains_verb", test_hamma_remains_verb),
    ("test_allamahu_remains_verb", test_allamahu_remains_verb),
    ("test_kataba_remains_verb", test_kataba_remains_verb),
    ("test_alkitabu_remains_noun", test_alkitabu_remains_noun),
    ("test_min_remains_harf", test_min_remains_harf),
]

for nm, fn in ALL:
    _t(nm, fn)

print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print()
    print("=== FAILURES ===")
    for nm, ok, err in results:
        if not ok:
            print(f"  ✗ {nm}: {err}")
