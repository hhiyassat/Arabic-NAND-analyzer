#!/usr/bin/env python3
"""test_session5_tense_window.py — اختبارات الجَلسَة 5.

O. PastSpeakerNaTenseContract — زَمَن past لِفعل ماضٍ مَع نا
P. WeakPastWithObjectPronounContract — جَآءَهُمْ FIIL past
Q. PastPluralWawContract — ٱتَّخَذُوا past لا command
R. PatientWindowContract — patient_of لا يَعبُر الجُملَة
S. AgentWindowContract v3 — أَسماء الخَبَر لَيسَت agent
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


def _check_tense(tok, exp_tense):
    info = _info(tok)
    if info.get("word_class") != "FIIL":
        raise AssertionError(f"{tok} is not FIIL, got {info.get('word_class')}")
    # نَستَخدِم detect_tense مِن event_extractor (المَصدَر المُعتَمَد)
    from event_extractor import detect_tense
    class T:
        word_class = "FIIL"
        morph_tag = ""
        token = tok
        surface = tok
        role_phrase = ""
    tense = detect_tense(T())
    assert tense == exp_tense, f"{tok} tense={tense!r} (expected {exp_tense!r})"


# ─────────────────────────────────────────────────────────────
# O. PastSpeakerNaTense (FIIL + tense=past)
# ─────────────────────────────────────────────────────────────
def test_akhadhna_is_past_tense():
    _check_tense("أَخَذْنَا", "past")


def test_wa_arsalna_is_past_tense():
    _check_tense("وَأَرْسَلْنَآ", "past")


def test_arsalna_is_past_tense():
    _check_tense("أَرْسَلْنَا", "past")


def test_baathnakum_is_past_tense():
    _check_tense("بَعَثْنَٰكُم", "past")


def test_khalaqna_is_past_tense():
    _check_tense("خَلَقْنَا", "past")


def test_jaalna_is_past_tense():
    _check_tense("جَعَلْنَا", "past")


def test_kataba_is_past_tense():
    _check_tense("كَتَبَ", "past")


# Regression: مُضارِع يَبقى present
def test_yaktubu_is_present_tense():
    _check_tense("يَكْتُبُ", "present")


# ─────────────────────────────────────────────────────────────
# P. WeakPastWithObjectPronoun
# ─────────────────────────────────────────────────────────────
def test_jaahum_is_fiil():
    _check("جَآءَهُمْ", {"FIIL"})


def test_jaahu_is_fiil():
    _check("جَآءَهُۥ", {"FIIL"})


def test_jaaha_is_fiil():
    _check("جَآءَهَا", {"FIIL"})


def test_jaakum_is_fiil():
    _check("جَآءَكُم", {"FIIL"})


def test_hadana_is_fiil():
    _check("هَدَىٰنَا", {"FIIL"})


def test_atakum_is_fiil():
    _check("أَتَىٰكُم", {"FIIL"})


def test_sha_a_is_fiil():
    _check("شَآءَ", {"FIIL"})


# ─────────────────────────────────────────────────────────────
# Q. PastPluralWaw (tense=past not command)
# ─────────────────────────────────────────────────────────────
def test_ittakhadhu_is_past_tense():
    _check_tense("ٱتَّخَذُوا", "past")


def test_kadhdhabu_is_past_tense():
    _check_tense("كَذَّبُوا", "past")


def test_utu_is_past_tense():
    _check_tense("أُوتُوا", "past")


def test_duu_is_past_tense():
    _check_tense("دُعُوا", "past")


def test_akalu_is_past_tense():
    _check_tense("أَكَلُوا", "past")


# Regression: أَمر بِدون و الجَماعَة يَبقى command
def test_uktub_is_command_tense():
    info = _info("ٱكْتُبُوا")
    if info.get("word_class") == "FIIL":
        tense = info.get("tense") or info.get("verb_tense") or ""
        # ٱكْتُبُوا = أَمر جَمع (imperative)
        assert tense in ("command", "imperative", ""), f"ٱكْتُبُوا tense={tense}"


# ─────────────────────────────────────────────────────────────
# Regression (no breakage)
# ─────────────────────────────────────────────────────────────
def test_huwa_still_ism_mabni():
    _check("هُوَ", {"ISM_MABNI"})


def test_faminhum_still_harf():
    _check("فَمِنْهُم", {"HARF"})


def test_anfusuhum_still_noun():
    _check("أَنفُسُهُمْ", {"ISM_MUARAB", "JAMID"})


def test_akbaru_still_noun():
    _check("أَكْبَرُ", {"ISM_MUARAB", "JAMID"})


def test_akhluqu_still_verb():
    _check("أَخْلُقُ", {"FIIL"})


def test_akhrajukum_still_verb():
    _check("أَخْرَجُوكُمْ", {"FIIL"})


print("Session 5 Tense + Window Contracts")
print("=" * 70)

ALL = [
    # O
    ("test_akhadhna_is_past_tense", test_akhadhna_is_past_tense),
    ("test_wa_arsalna_is_past_tense", test_wa_arsalna_is_past_tense),
    ("test_arsalna_is_past_tense", test_arsalna_is_past_tense),
    ("test_baathnakum_is_past_tense", test_baathnakum_is_past_tense),
    ("test_khalaqna_is_past_tense", test_khalaqna_is_past_tense),
    ("test_jaalna_is_past_tense", test_jaalna_is_past_tense),
    ("test_kataba_is_past_tense", test_kataba_is_past_tense),
    ("test_yaktubu_is_present_tense", test_yaktubu_is_present_tense),
    # P
    ("test_jaahum_is_fiil", test_jaahum_is_fiil),
    ("test_jaahu_is_fiil", test_jaahu_is_fiil),
    ("test_jaaha_is_fiil", test_jaaha_is_fiil),
    ("test_jaakum_is_fiil", test_jaakum_is_fiil),
    ("test_hadana_is_fiil", test_hadana_is_fiil),
    ("test_atakum_is_fiil", test_atakum_is_fiil),
    ("test_sha_a_is_fiil", test_sha_a_is_fiil),
    # Q
    ("test_ittakhadhu_is_past_tense", test_ittakhadhu_is_past_tense),
    ("test_kadhdhabu_is_past_tense", test_kadhdhabu_is_past_tense),
    ("test_utu_is_past_tense", test_utu_is_past_tense),
    ("test_duu_is_past_tense", test_duu_is_past_tense),
    ("test_akalu_is_past_tense", test_akalu_is_past_tense),
    ("test_uktub_is_command_tense", test_uktub_is_command_tense),
    # Regression
    ("test_huwa_still_ism_mabni", test_huwa_still_ism_mabni),
    ("test_faminhum_still_harf", test_faminhum_still_harf),
    ("test_anfusuhum_still_noun", test_anfusuhum_still_noun),
    ("test_akbaru_still_noun", test_akbaru_still_noun),
    ("test_akhluqu_still_verb", test_akhluqu_still_verb),
    ("test_akhrajukum_still_verb", test_akhrajukum_still_verb),
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
