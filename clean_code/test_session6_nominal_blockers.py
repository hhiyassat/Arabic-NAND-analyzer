#!/usr/bin/env python3
"""test_session6_nominal_blockers.py — اختبارات الجَلسَة 6.

T. NominalSurfaceBlocker v3 — تَنوين/جَمع تَكسير/اسم+ضَمير لا تَدخُل VerbFormContract
U. ProperNounOverrideContract — أَعلام (يَعْقُوبَ، إِسْمَٰعِيلَ، إِبْرَٰهِيمَ) لَيسَت FIIL
V. PastPluralWawContract tense — ٱتَّخَذُوا past لا command
W. RelativePronounClosedList v2 — ٱلَّتِى/ٱلَّذِي/ٱلَّذِينَ = ISM_MAWSOOL
X. FunctionalNounBlocker — غَيْرَ/بَعْدَ/بَيْنَ/دُونِ/عِندَ لَيسَت FIIL
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


def _wc(tok): return CLF.classify(tok)["word_class"]


def _check(tok, exp_kinds):
    wc = _wc(tok)
    assert wc in exp_kinds, f"{tok} → {wc} (expected {exp_kinds})"


def _not_fiil(tok):
    wc = _wc(tok)
    assert wc != "FIIL", f"{tok} → {wc} (must NOT be FIIL)"


def _check_tense(tok, exp_tense):
    info = CLF.classify(tok)
    if info.get("word_class") != "FIIL":
        raise AssertionError(f"{tok} is not FIIL")
    from event_extractor import detect_tense
    class T:
        word_class = "FIIL"; morph_tag = ""; token = tok; surface = tok; role_phrase = ""
    tense = detect_tense(T())
    assert tense == exp_tense, f"{tok} tense={tense!r} (expected {exp_tense!r})"


# T. NominalSurfaceBlocker v3
def t_kitabun_not_fiil(): _not_fiil("كِتَٰبٌ")
def t_kitabun2_not_fiil(): _not_fiil("كِتَابٌ")
def t_marqumun_not_fiil(): _not_fiil("مَّرْقُومٌ")
def t_marqumun2_not_fiil(): _not_fiil("مَرْقُومٌ")
def t_amwalakum_not_fiil(): _not_fiil("أَمْوَٰلَكُمُ")
def t_amwalakum2_not_fiil(): _not_fiil("أَمْوَٰلَكُمْ")
def t_amwalukum_not_fiil(): _not_fiil("أَمْوَٰلُكُمْ")
def t_jannatu_not_fiil(): _not_fiil("جَنَّاتٌ")
def t_rasulun_not_fiil(): _not_fiil("رَسُولٌ")
def t_kitabuhum_not_fiil(): _not_fiil("كِتَٰبُهُمْ")

# U. ProperNounOverrideContract
def u_yaqub_not_fiil(): _not_fiil("يَعْقُوبَ")
def u_ismail_not_fiil(): _not_fiil("وَإِسْمَٰعِيلَ")
def u_ishaq_not_fiil(): _not_fiil("وَإِسْحَٰقَ")
def u_ibrahim_not_fiil(): _not_fiil("إِبْرَٰهِيمَ")
def u_israil_not_fiil(): _not_fiil("إِسْرَٰٓءِيلَ")
def u_musa_not_fiil(): _not_fiil("مُوسَىٰ")
def u_isa_not_fiil(): _not_fiil("عِيسَىٰ")
def u_yusuf_not_fiil(): _not_fiil("يُوسُفَ")
def u_nuh_not_fiil(): _not_fiil("نُوحٌ")
def u_dawud_not_fiil(): _not_fiil("دَاوُۥدَ")

# V. PastPluralWaw tense
def v_ittakhadhu_past(): _check_tense("ٱتَّخَذُوا", "past")
def v_zalamu_past(): _check_tense("ظَلَمُوا", "past")
def v_qalu_past(): _check_tense("قَالُوا", "past")
def v_kanu_past(): _check_tense("كَانُوا", "past")
def v_amanu_past(): _check_tense("ءَامَنُوا", "past")
def v_kafaru_past(): _check_tense("كَفَرُوا", "past")

# W. RelativePronounClosedList v2
def w_allati_mawsool(): _check("ٱلَّتِى", {"ISM_MAWSOOL"})
def w_allati_yaa_mawsool(): _check("ٱلَّتِي", {"ISM_MAWSOOL"})
def w_alladhi_mawsool(): _check("ٱلَّذِى", {"ISM_MAWSOOL"})
def w_alladhi_yaa_mawsool(): _check("ٱلَّذِي", {"ISM_MAWSOOL"})
def w_alladhina_mawsool(): _check("ٱلَّذِينَ", {"ISM_MAWSOOL"})

# X. FunctionalNounBlocker
def x_ghayra_not_fiil(): _not_fiil("غَيْرَ")
def x_baada_not_fiil(): _not_fiil("بَعْدَ")
def x_bayna_not_fiil(): _not_fiil("بَيْنَ")
def x_duni_not_fiil(): _not_fiil("دُونِ")
def x_inda_not_fiil(): _not_fiil("عِندَ")
def x_qabla_not_fiil(): _not_fiil("قَبْلَ")
def x_fawqa_not_fiil(): _not_fiil("فَوْقَ")
def x_tahta_not_fiil(): _not_fiil("تَحْتَ")

# Regression — no breakage
def r_kataba_still_verb(): _check("كَتَبَ", {"FIIL"})
def r_yaktubu_still_verb(): _check("يَكْتُبُ", {"FIIL"})
def r_qul_still_verb(): _check("قُلْ", {"FIIL"})
def r_alkitab_still_noun(): _check("الْكِتَابُ", {"ISM_MUARAB","JAMID"})
def r_min_still_harf(): _check("مِن", {"HARF"})
def r_huwa_still_pronoun(): _check("هُوَ", {"ISM_MABNI"})


print("Session 6 Nominal Blockers Tests")
print("=" * 70)
ALL = [
    ("t_kitabun_not_fiil", t_kitabun_not_fiil),
    ("t_kitabun2_not_fiil", t_kitabun2_not_fiil),
    ("t_marqumun_not_fiil", t_marqumun_not_fiil),
    ("t_marqumun2_not_fiil", t_marqumun2_not_fiil),
    ("t_amwalakum_not_fiil", t_amwalakum_not_fiil),
    ("t_amwalakum2_not_fiil", t_amwalakum2_not_fiil),
    ("t_amwalukum_not_fiil", t_amwalukum_not_fiil),
    ("t_jannatu_not_fiil", t_jannatu_not_fiil),
    ("t_rasulun_not_fiil", t_rasulun_not_fiil),
    ("t_kitabuhum_not_fiil", t_kitabuhum_not_fiil),
    ("u_yaqub_not_fiil", u_yaqub_not_fiil),
    ("u_ismail_not_fiil", u_ismail_not_fiil),
    ("u_ishaq_not_fiil", u_ishaq_not_fiil),
    ("u_ibrahim_not_fiil", u_ibrahim_not_fiil),
    ("u_israil_not_fiil", u_israil_not_fiil),
    ("u_musa_not_fiil", u_musa_not_fiil),
    ("u_isa_not_fiil", u_isa_not_fiil),
    ("u_yusuf_not_fiil", u_yusuf_not_fiil),
    ("u_nuh_not_fiil", u_nuh_not_fiil),
    ("u_dawud_not_fiil", u_dawud_not_fiil),
    ("v_ittakhadhu_past", v_ittakhadhu_past),
    ("v_zalamu_past", v_zalamu_past),
    ("v_qalu_past", v_qalu_past),
    ("v_kanu_past", v_kanu_past),
    ("v_amanu_past", v_amanu_past),
    ("v_kafaru_past", v_kafaru_past),
    ("w_allati_mawsool", w_allati_mawsool),
    ("w_allati_yaa_mawsool", w_allati_yaa_mawsool),
    ("w_alladhi_mawsool", w_alladhi_mawsool),
    ("w_alladhi_yaa_mawsool", w_alladhi_yaa_mawsool),
    ("w_alladhina_mawsool", w_alladhina_mawsool),
    ("x_ghayra_not_fiil", x_ghayra_not_fiil),
    ("x_baada_not_fiil", x_baada_not_fiil),
    ("x_bayna_not_fiil", x_bayna_not_fiil),
    ("x_duni_not_fiil", x_duni_not_fiil),
    ("x_inda_not_fiil", x_inda_not_fiil),
    ("x_qabla_not_fiil", x_qabla_not_fiil),
    ("x_fawqa_not_fiil", x_fawqa_not_fiil),
    ("x_tahta_not_fiil", x_tahta_not_fiil),
    ("r_kataba_still_verb", r_kataba_still_verb),
    ("r_yaktubu_still_verb", r_yaktubu_still_verb),
    ("r_qul_still_verb", r_qul_still_verb),
    ("r_alkitab_still_noun", r_alkitab_still_noun),
    ("r_min_still_harf", r_min_still_harf),
    ("r_huwa_still_pronoun", r_huwa_still_pronoun),
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
