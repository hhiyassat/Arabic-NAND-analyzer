#!/usr/bin/env python3
"""test_new_contracts_session3.py — اختبارات الجَلسَة الثالِثَة (5 عُقود جَديدَة).

1. ClosedPrepPronounContract
2. PronounAndNasikhOverrideContract
3. FusedParticlePrepositionContract
4. PossessiveNominalBlocker v2 + PassiveVerb + PastVerbWithObjectPronoun + ColorState
"""
from i3rab_engine.layer1 import WordClassClassifier
CLF = WordClassClassifier()
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
        results.append((name, False, f"ERROR: {e}"))
        print(f"  ✗ {name}: {e}")


def _wc(tok): return CLF.classify(tok)["word_class"]


def _check(tok, exp_kinds):
    wc = _wc(tok)
    assert wc in exp_kinds, f"{tok} → {wc} (expected {exp_kinds})"


# 1. ClosedPrepPronoun
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
def test_fiha_is_harf():
    _check("فِيهَا", {"HARF"})

# 2. PronounAndNasikh
def test_hum_is_pronoun():
    _check("هُمْ", {"ISM_MABNI"})
def test_huwa_is_pronoun():
    _check("هُوَ", {"ISM_MABNI"})
def test_nahnu_is_pronoun():
    _check("نَحْنُ", {"ISM_MABNI"})
def test_antum_is_pronoun():
    _check("أَنْتُمْ", {"ISM_MABNI"})
def test_laallakum_is_nasikh():
    _check("لَعَلَّكُمْ", {"HARF"})
def test_innahum_is_nasikh():
    _check("إِنَّهُمْ", {"HARF"})

# 3. FusedParticlePrep
def test_fafi_is_harf():
    _check("فَفِى", {"HARF"})
def test_fafi_yaa_is_harf():
    _check("فَفِي", {"HARF"})

# 4. PossessiveBlocker v2 + Passive + PastVerb+Pron + ColorState
def test_ilmihi_is_noun():
    _check("عِلْمِهِ", {"ISM_MUARAB","JAMID"})
def test_imanikum_is_noun():
    _check("إِيمَانِكُمْ", {"ISM_MUARAB","JAMID"})
def test_utu_is_passive_verb():
    _check("أُوتُوا", {"FIIL"})
def test_duu_is_passive_verb():
    _check("دُعُوا", {"FIIL"})
def test_umirna_is_passive_verb():
    _check("أُمِرْنَا", {"FIIL"})
def test_baathnakum_is_past_verb():
    _check("بَعَثْنَٰكُم", {"FIIL"})
def test_ibyaddat_is_past_verb():
    _check("ٱبْيَضَّتْ", {"FIIL"})

# Regression
def test_hamma_remains_verb():
    _check("هَمَّ", {"FIIL"})
def test_allamahu_remains_verb():
    _check("عَلَّمَهُۥ", {"FIIL"})


print("Session 3 New Contracts Tests")
print("=" * 60)

for nm, fn in [
    ("test_faminhum_is_harf", test_faminhum_is_harf),
    ("test_waminhum_is_harf", test_waminhum_is_harf),
    ("test_anhu_is_harf", test_anhu_is_harf),
    ("test_bihi_is_harf", test_bihi_is_harf),
    ("test_lahu_is_harf", test_lahu_is_harf),
    ("test_fiha_is_harf", test_fiha_is_harf),
    ("test_hum_is_pronoun", test_hum_is_pronoun),
    ("test_huwa_is_pronoun", test_huwa_is_pronoun),
    ("test_nahnu_is_pronoun", test_nahnu_is_pronoun),
    ("test_antum_is_pronoun", test_antum_is_pronoun),
    ("test_laallakum_is_nasikh", test_laallakum_is_nasikh),
    ("test_innahum_is_nasikh", test_innahum_is_nasikh),
    ("test_fafi_is_harf", test_fafi_is_harf),
    ("test_fafi_yaa_is_harf", test_fafi_yaa_is_harf),
    ("test_ilmihi_is_noun", test_ilmihi_is_noun),
    ("test_imanikum_is_noun", test_imanikum_is_noun),
    ("test_utu_is_passive_verb", test_utu_is_passive_verb),
    ("test_duu_is_passive_verb", test_duu_is_passive_verb),
    ("test_umirna_is_passive_verb", test_umirna_is_passive_verb),
    ("test_baathnakum_is_past_verb", test_baathnakum_is_past_verb),
    ("test_ibyaddat_is_past_verb", test_ibyaddat_is_past_verb),
    ("test_hamma_remains_verb", test_hamma_remains_verb),
    ("test_allamahu_remains_verb", test_allamahu_remains_verb),
]:
    test(nm, fn)

print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
