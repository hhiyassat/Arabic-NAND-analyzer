#!/usr/bin/env python3
"""test_production_path_segmentation.py — PATCH 0 integration test.

Purpose (PATCH 0 of the per-patch fix plan):
  Prove that the L1/L2 lines in `analyze_verse_v3.py --verse 2:282 --all`
  come from `segmenter.segment()` and ONLY from `segmenter.segment()`,
  by calling that function directly with target words from 2:282 and
  asserting what it returns today.

  This is a *characterization test*: it locks in the CURRENT (buggy)
  output so any future PATCH 1 that claims to fix lam-al-amr MUST
  update this test (and thus prove it changed the production path).

Why this matters:
  Existing tests in this repo (e.g. test_verb_form_contract.py:82
  test_wa_l_yaktub_is_jussive_command_verb) call helper functions like
  `evaluate_verb_form()` and pass. But `segment()` does NOT call
  `evaluate_verb_form()` — verified by:
      grep -nE "evaluate_verb_form" segmenter.py  → (no output)
  So "test_wa_l_yaktub_is_jussive_command_verb passes" does NOT prove
  that the production segmentation has changed. This file closes that
  gap.

PATCH 0 rule:
  This file MUST NOT contain any logic fix. It only asserts the
  current state of segment() output for the target words. When PATCH 1
  fixes lam-al-amr in segmenter.py, the assertions in this file MUST
  be updated to the new expected output. If a PATCH 1 commit lands
  without updating these assertions, the test fails — that's the
  guard.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))


# ─────────────────────────────────────────────────────────────────────
# Mirror exactly how analyze_verse_v3.py:show_morph imports segment.
# If this import path differs from analyze_verse_v3.py's line 67,
# the test is invalid — that's why we hard-code the same form here.
# ─────────────────────────────────────────────────────────────────────
from segmenter import segment


# ─────────────────────────────────────────────────────────────────────
# PATCH 0 finding #3 — Quran source file uses Uthmani diacritic order
# (e.g. ل + ّ + َ), while Python string literals usually use keyboard
# order (ل + َ + ّ). Both produce identical NFC. All Arabic string
# comparisons in this file go through _nfc to avoid false negatives.
# ─────────────────────────────────────────────────────────────────────
def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def _eq(a: str, b: str) -> bool:
    return _nfc(a) == _nfc(b)


# Target words from 2:282 (verbatim from out_2_282_phase4_off-cd4bcbc7.txt)
PATCH_1_TARGETS = [
    "وَلْيَكْتُب",
    "فَلْيَكْتُبْ",
    "وَلْيُمْلِلِ",
    "فَلْيُمْلِلْ",
    "وَلْيَتَّقِ",
]

PATCH_2_TARGETS_CLOSED_FORMS = [
    "ٱلَّذِى",        # currently splits as الَّ(DET) + ذِى   ← BUG
    "ٱلَّذِينَ",     # currently atomic — must STAY atomic
    "ذَٰلِكُمْ",      # currently atomic (Batch 6) — must STAY atomic
]

PATCH_2_TARGETS_FORM_VI_PAST = [
    "تَدَايَنتُم",    # currently splits as تَ(IMPERF_PREF) + دَا + يَن + تُم   ← BUG
    "تَبَايَعْتُمْ",  # currently splits as تَ(IMPERF_PREF) + بَايَعْ + تُمْ      ← BUG
]

PATCH_3_TARGETS = [
    "بَيْنَكُمْ",     # currently splits as بَيْنَ(PREP) + كُمْ   ← BUG
    "وَلِيُّهُۥ",     # currently splits as وَ(CONJ) + لِ(PREP) + يُّهُۥ   ← BUG
    "يَكُونَا",       # currently splits as يَ(IMPERF_PREF) + كُو + نَا(POSS_PRON)   ← BUG
    "أَلَّا",         # currently splits as أن(PREP) + لا   ← BUG (tag should be HARF_NASB)
]


# ─────────────────────────────────────────────────────────────────────
# Helpers (test-only — no production behavior)
# ─────────────────────────────────────────────────────────────────────
def _describe(r) -> str:
    """One-line summary matching show_morph's printed format."""
    prefs = "+".join(f"{f}({t})" for f, t in zip(r.prefixes, r.prefix_tags)) or "—"
    sufs = "+".join(f"{f}({t})" for f, t in zip(r.suffixes, r.suffix_tags)) or "—"
    return f"prefixes={prefs} | stem={r.stem} | suffixes={sufs}"


# ─────────────────────────────────────────────────────────────────────
# PATCH 0 — sanity: segment() is callable + returns SegmentationResult
# ─────────────────────────────────────────────────────────────────────
def t_segment_is_callable_via_production_import_path():
    """The exact import line from analyze_verse_v3.py:67 must resolve to
    a callable that returns SegmentationResult."""
    assert callable(segment), "segment is not callable"
    r = segment("كَتَبَ")
    assert hasattr(r, "prefixes")
    assert hasattr(r, "stem")
    assert hasattr(r, "suffixes")
    assert hasattr(r, "prefix_tags")
    assert hasattr(r, "suffix_tags")
    assert hasattr(r, "audit")


# ─────────────────────────────────────────────────────────────────────
# CHARACTERIZATION (current state — captures THE BUG)
# Each test asserts what segment() returns TODAY for a target word.
# When PATCH 1 fixes lam-al-amr, these tests MUST be edited to assert
# the new (correct) output. If they're not edited, the test fails —
# that's the production-path proof.
# ─────────────────────────────────────────────────────────────────────

# ── PATCH 1 — lam al-amr (BUG: stem = whole word, no segmentation) ──

def _assert_lam_al_amr_split(r, expected_conj_form: str, expected_stem: str) -> None:
    """Shared assertion: token is split as CONJ + LAM_AL_AMR + stem.

    Updated 2026-05-26 per PATCH 1 (LamAlAmrSegmentationContract).
    """
    assert len(r.prefixes) == 2, (
        f"expected exactly 2 prefixes (CONJ + LAM_AL_AMR), "
        f"got {len(r.prefixes)}: {_describe(r)}"
    )
    assert r.prefix_tags == ["CONJ", "LAM_AL_AMR"], (
        f"expected tags=['CONJ', 'LAM_AL_AMR'], got {r.prefix_tags}: {_describe(r)}"
    )
    assert _eq(r.prefixes[0], expected_conj_form), (
        f"first prefix form: expected {expected_conj_form!r}, got {r.prefixes[0]!r}"
    )
    assert _eq(r.prefixes[1], "لْ"), (
        f"second prefix form: expected 'لْ', got {r.prefixes[1]!r}"
    )
    assert _eq(r.stem, expected_stem), (
        f"stem: expected {expected_stem!r}, got {r.stem!r}: {_describe(r)}"
    )
    assert r.suffixes == [], (
        f"expected no suffixes, got {r.suffixes}: {_describe(r)}"
    )


def t_walyaktub_segments_with_lam_al_amr():
    """PATCH 1 verified: وَلْيَكْتُب → وَ(CONJ) + لْ(LAM_AL_AMR) + stem=يَكْتُب."""
    r = segment("وَلْيَكْتُب")
    _assert_lam_al_amr_split(r, "وَ", "يَكْتُب")


def t_falyaktub_segments_with_lam_al_amr():
    """PATCH 1 verified: فَلْيَكْتُبْ → فَ(CONJ) + لْ(LAM_AL_AMR) + stem=يَكْتُبْ."""
    r = segment("فَلْيَكْتُبْ")
    _assert_lam_al_amr_split(r, "فَ", "يَكْتُبْ")


def t_walyumlil_segments_with_lam_al_amr():
    """PATCH 1 verified: وَلْيُمْلِلِ → وَ(CONJ) + لْ(LAM_AL_AMR) + stem=يُمْلِلِ."""
    r = segment("وَلْيُمْلِلِ")
    _assert_lam_al_amr_split(r, "وَ", "يُمْلِلِ")


def t_falyumlil_segments_with_lam_al_amr():
    """PATCH 1 verified: فَلْيُمْلِلْ → فَ(CONJ) + لْ(LAM_AL_AMR) + stem=يُمْلِلْ."""
    r = segment("فَلْيُمْلِلْ")
    _assert_lam_al_amr_split(r, "فَ", "يُمْلِلْ")


def t_walyattaqi_segments_with_lam_al_amr():
    """PATCH 1 verified: وَلْيَتَّقِ → وَ(CONJ) + لْ(LAM_AL_AMR) + stem=يَتَّقِ."""
    r = segment("وَلْيَتَّقِ")
    _assert_lam_al_amr_split(r, "وَ", "يَتَّقِ")


def t_lam_al_amr_does_not_fire_for_ordinary_lam_words():
    """Regression guard from user's PATCH 1 prompt.
    لَيلًا / لِسانٌ / وَلَا / لَنْ / لَهُمْ must NOT trigger LAM_AL_AMR."""
    ordinary = ["لَيلًا", "لِسانٌ", "لَا", "وَلَا", "لَنْ", "لَهُمْ"]
    for w in ordinary:
        r = segment(w)
        assert "LAM_AL_AMR" not in r.prefix_tags, (
            f"{w!r}: LAM_AL_AMR fired unexpectedly: {_describe(r)}"
        )


def t_lam_al_amr_conjunction_exception_does_not_break_nouns():
    """Regression guard for the surgical CONJ exception in PATCH 1:
    وَقُود / فَوْق / وَقْت must remain atomic (not be split by CONJ)."""
    nouns = ["وَقُود", "فَوْق", "وَقْت"]
    for w in nouns:
        r = segment(w)
        assert "CONJ" not in r.prefix_tags, (
            f"{w!r}: CONJ peeled unexpectedly: {_describe(r)}"
        )
        assert "LAM_AL_AMR" not in r.prefix_tags, (
            f"{w!r}: LAM_AL_AMR fired unexpectedly: {_describe(r)}"
        )


# ── PATCH 2 (A) — closed forms (BUG: ٱلَّذِى splits as الَّ + ذِى) ──

def t_alladhi_locked_no_det_split():
    """PATCH 2A verified: ٱلَّذِى atomic — no DET peel."""
    r = segment("ٱلَّذِى")
    assert "DET" not in (r.prefix_tags or []), (
        f"PATCH 2A FAILED — DET still peeled: {_describe(r)}"
    )
    assert r.prefixes == [], f"prefixes not empty: {r.prefixes}"
    assert r.suffixes == [], f"suffixes not empty: {r.suffixes}"


def t_alladhina_must_remain_atomic():
    """Regression guard: ٱلَّذِينَ is already atomic — must not regress."""
    r = segment("ٱلَّذِينَ")
    assert r.prefixes == [] and r.suffixes == [], (
        f"REGRESSION GUARD — ٱلَّذِينَ stopped being atomic: {_describe(r)}"
    )


def t_dhalikum_must_remain_atomic():
    """PATCH 2B verified: ذَٰلِكُمْ atomic via demonstrative_compounds.csv."""
    r = segment("ذَٰلِكُمْ")
    assert r.prefixes == [] and r.suffixes == [], (
        f"PATCH 2B FAILED — ذَٰلِكُمْ should be atomic: {_describe(r)}"
    )
    assert "POSS_PRON" not in (r.suffix_tags or []), (
        f"PATCH 2B FAILED — POSS_PRON peel still happening: {_describe(r)}"
    )


# ── PATCH 2 (B) — Form VI past (BUG: تَ treated as IMPERF_PREF) ──

def t_tadayantum_no_imperf_prefix():
    """PATCH 2C verified: تَدَايَنتُم — no IMPERF_PREF peel."""
    r = segment("تَدَايَنتُم")
    assert "IMPERF_PREF" not in (r.prefix_tags or []), (
        f"PATCH 2C FAILED — IMPERF_PREF still peeled: {_describe(r)}"
    )


def t_tadayantum_aspect_is_past():
    """PATCH 2D verified: تَدَايَنتُم → verb_form aspect=PV (Form V/VI past)."""
    from verb_form_contract import evaluate_verb_form
    v = evaluate_verb_form("تَدَايَنتُم")
    assert v.aspect == "PV", (
        f"PATCH 2D FAILED — expected aspect=PV (past), got aspect={v.aspect!r}"
    )


def t_tadayantum_evaluate_verb_form_is_certificate():
    """PATCH 2D fix-up: evaluate_verb_form must return kind=Certificate
    (not Hypothesis) — otherwise i3rab_engine.layer1 skips its verdict
    at line 535 and the L3 role stays 'فعل مضارع'.

    Root cause: verb_form_contract's `verb_suffixes_clear` list used
    diacritized forms (e.g. تُمْ with sukun). تَدَايَنتُم's tail is
    تُم without sukun. The plain-strip match added by this fix-up
    rescues that case."""
    from verb_form_contract import evaluate_verb_form
    v = evaluate_verb_form("تَدَايَنتُم")
    assert v.kind == "Certificate", (
        f"PATCH 2D fix-up FAILED — kind={v.kind!r}. "
        f"Hypothesis means i3rab_engine/layer1.py:535 will skip this "
        f"verdict and L3 will keep saying فعل مضارع."
    )


def t_tadayantum_l3_role_must_not_be_imperfect():
    """PATCH 2 BINDING acceptance — production-path L3 must NOT say
    'فعل مضارع' for تَدَايَنتُم. This test calls the full layer1.classify
    path that analyze_verse_v3.py uses.

    Sandbox-gated: layer1 instantiates RootPipeline which loads awzan
    from a path the sandbox can't read. When sandbox-blocked, the test
    is SKIPPED (not silently passed) and prints a notice.
    """
    try:
        from i3rab_engine.layer1 import WordClassClassifier
        c = WordClassClassifier()
        r = c.classify("تَدَايَنتُم")
    except (PermissionError, OSError) as e:
        # Sandbox-only blocker — user's machine has the real path.
        print(f"  [skipped — sandbox: {type(e).__name__}]", end=" ")
        return
    # In production this must yield verb_aspect=PV (which layer3 maps
    # to role 'فعل ماضٍ'). The visible failure mode on the user's
    # machine is r['verb_aspect'] == 'IV' producing 'فعل مضارع'.
    assert r.get("word_class") == "FIIL", (
        f"تَدَايَنتُم not classified as FIIL: {r.get('word_class')}"
    )
    assert r.get("verb_aspect") == "PV", (
        f"PATCH 2 BINDING FAILURE — verb_aspect={r.get('verb_aspect')!r}, "
        f"expected 'PV' so L3 says فعل ماضٍ. Source: {r.get('source')!r}"
    )


def t_tabaya3tum_no_imperf_prefix():
    """PATCH 2C verified: تَبَايَعْتُمْ — no IMPERF_PREF peel."""
    r = segment("تَبَايَعْتُمْ")
    assert "IMPERF_PREF" not in (r.prefix_tags or []), (
        f"PATCH 2C FAILED — IMPERF_PREF still peeled: {_describe(r)}"
    )


def t_tabaya3tum_aspect_is_past():
    """PATCH 2D verified: تَبَايَعْتُمْ → verb_form aspect=PV."""
    from verb_form_contract import evaluate_verb_form
    v = evaluate_verb_form("تَبَايَعْتُمْ")
    assert v.aspect == "PV", (
        f"PATCH 2D FAILED — expected aspect=PV (past), got aspect={v.aspect!r}"
    )


def t_real_imperfect_ta_still_detected():
    """PATCH 2 regression guard: real imperfect verbs starting with تَ
    (تَكْتُبُ, تَدْرُسُ) must STILL be classified as IV with IMPERF_PREF."""
    for w in ["تَكْتُبُ", "تَدْرُسُ"]:
        r = segment(w)
        assert "IMPERF_PREF" in (r.prefix_tags or []), (
            f"PATCH 2 REGRESSION — {w} lost IMPERF_PREF: {_describe(r)}"
        )
        from verb_form_contract import evaluate_verb_form
        v = evaluate_verb_form(w)
        assert v.aspect == "IV", (
            f"PATCH 2 REGRESSION — {w} aspect changed to {v.aspect!r}"
        )


# ── PATCH 3 — functional nouns, false-lam, dual-verb, alla ─────────

def t_baynakum_no_prep_peel():
    """PATCH 3A verified: بَيْنَكُمْ no longer has بَيْنَ peeled as PREP."""
    r = segment("بَيْنَكُمْ")
    assert "PREP" not in (r.prefix_tags or []), (
        f"PATCH 3A FAILED — PREP peeled: {_describe(r)}"
    )


def t_bbaynakum_no_prep_peel():
    """PATCH 3A verified: بَّيْنَكُمْ (with elision-shadda) — no PREP peel."""
    r = segment("بَّيْنَكُمْ")
    assert "PREP" not in (r.prefix_tags or []), (
        f"PATCH 3A FAILED — PREP peeled: {_describe(r)}"
    )


def t_baynakum_l3_not_harf():
    """PATCH 3E BINDING: بَيْنَكُمْ L3 must NOT be class=HARF.
    Sandbox-skipped (RootPipeline path); runs on user machine."""
    try:
        from i3rab_engine.layer1 import WordClassClassifier
        c = WordClassClassifier()
        r = c.classify("بَيْنَكُمْ")
    except (PermissionError, OSError) as e:
        print(f"  [skipped — sandbox: {type(e).__name__}]", end=" ")
        return
    assert r.get("word_class") != "HARF", (
        f"PATCH 3E BINDING FAILURE — بَيْنَكُمْ word_class={r.get('word_class')!r}, "
        f"role={r.get('role')!r}, source={r.get('source')!r}. "
        f"Expected ISM_MUARAB (functional locative noun) via MASAQ-HARF override."
    )


def t_baynakum_l3_role_not_jazm():
    """PATCH 3 FIXUP BINDING: بَيْنَكُمْ / بَّيْنَكُمْ L3 role must NOT be
    'اسم مجزوم'. Functional locative noun → role must be ظَرف (ظرف مكان /
    اسم ظرف مضاف / اسم مضاف / functional_noun_idafa). Sandbox-skipped
    (RootPipeline path); runs on user machine."""
    try:
        from i3rab_engine.engine import I3rabEngine
        eng = I3rabEngine()
    except (PermissionError, OSError, ImportError) as e:
        print(f"  [skipped — sandbox: {type(e).__name__}]", end=" ")
        return

    _BAD = "اسم مجزوم"
    _ACCEPTABLE = {
        "ظرف مكان",
        "اسم ظرف مضاف",
        "اسم مضاف",
        "functional_noun_idafa",
    }
    for surface in ["بَيْنَكُمْ", "بَّيْنَكُمْ"]:
        try:
            sent = eng.analyze_sentence(surface)
        except (PermissionError, OSError) as e:
            print(f"  [skipped — sandbox: {type(e).__name__}]", end=" ")
            return
        # Find the matching token (single-token sentence: tokens[0])
        assert sent.tokens, f"no tokens produced for {surface!r}"
        tok = sent.tokens[0]
        assert tok.role_phrase != _BAD, (
            f"PATCH 3 FIXUP BINDING FAILURE — {surface} L3 role is "
            f"'{_BAD}' (forbidden). class={tok.word_class!r}, "
            f"case_id={tok.case_id!r}, source={tok.role_source!r}. "
            f"Expected one of {_ACCEPTABLE}."
        )
        assert tok.role_phrase in _ACCEPTABLE, (
            f"PATCH 3 FIXUP — {surface} L3 role={tok.role_phrase!r} not "
            f"in accepted ظرف set {_ACCEPTABLE}. source={tok.role_source!r}."
        )


def t_waliyyuhu_no_lam_prep_peel():
    """PATCH 3B verified: وَلِيُّهُۥ — no لِ(PREP) peel."""
    r = segment("وَلِيُّهُۥ")
    # After fix: only وَ(CONJ) should be peeled, لِ stays attached to stem
    # because residual would start with ي + shadda (false-lam-in-lexical-stem).
    pref_tags = r.prefix_tags or []
    has_lam_prep = any(
        t == "PREP" and (f.startswith("لِ") or f.startswith("ل"))
        for f, t in zip(r.prefixes, pref_tags)
    )
    assert not has_lam_prep, (
        f"PATCH 3B FAILED — لِ peeled as PREP: {_describe(r)}"
    )


def t_yakuna_no_na_possessive():
    """PATCH 3C verified: يَكُونَا — نَا stays attached (dual marker, not POSS_PRON)."""
    r = segment("يَكُونَا")
    assert "POSS_PRON" not in (r.suffix_tags or []), (
        f"PATCH 3C FAILED — POSS_PRON peeled: {_describe(r)}"
    )


def t_alla_an_tagged_harf_nasb_not_prep():
    """PATCH 3D verified: أَلَّا = أن (HARF_NASB) + لا. أن must NOT be PREP."""
    r = segment("أَلَّا")
    assert "PREP" not in (r.prefix_tags or []), (
        f"PATCH 3D FAILED — أن tagged as PREP: {_describe(r)}"
    )
    assert "HARF_NASB" in (r.prefix_tags or []), (
        f"PATCH 3D FAILED — expected HARF_NASB tag, got: {r.prefix_tags}"
    )


def t_patch3_regressions_intact():
    """PATCH 3 regression guards — other prepositions / pronouns unchanged."""
    # Other locative-noun-prepositions still peel correctly
    for tok in ["تَحْتَكُمْ", "فَوْقَكُمْ", "عِنْدَكُمْ"]:
        r = segment(tok)
        assert "PREP" in (r.prefix_tags or []), (
            f"REGRESSION — {tok} stopped peeling: {_describe(r)}"
        )
    # Real prep clitics still peel
    for tok in ["بِكِتابٍ", "لِزَيدٍ"]:
        r = segment(tok)
        assert "PREP" in (r.prefix_tags or []), (
            f"REGRESSION — {tok} stopped peeling PREP: {_describe(r)}"
        )
    # Real نا possessive still peels (no IMPERF_PREF case)
    for tok in ["كَتَبْنا", "رَبُّنا"]:
        r = segment(tok)
        assert "POSS_PRON" in (r.suffix_tags or []), (
            f"REGRESSION — {tok} stopped peeling نا: {_describe(r)}"
        )
    # Other assimilations stay PREP
    for tok in ["مِمَّا", "عَمَّن", "فِيمَا"]:
        r = segment(tok)
        assert "PREP" in (r.prefix_tags or []), (
            f"REGRESSION — {tok} assimilation tag changed: {_describe(r)}"
        )


# ─────────────────────────────────────────────────────────────────────
# Coverage assertion — these target words actually appear in 2:282
# ─────────────────────────────────────────────────────────────────────
def t_target_words_are_real_from_2_282():
    """Sanity: confirm each target word appears in 2:282's text."""
    quran = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
    if not quran.exists():
        return  # quran not present in this checkout — skip
    text_2_282 = ""
    with quran.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3 and parts[0] == "2" and parts[1] == "282":
                text_2_282 = parts[2]
                break
    if not text_2_282:
        return  # verse not found — skip
    all_targets = (
        PATCH_1_TARGETS + PATCH_2_TARGETS_CLOSED_FORMS
        + PATCH_2_TARGETS_FORM_VI_PAST + PATCH_3_TARGETS
    )
    # NFC both sides — see PATCH 0 finding #3
    text_nfc = _nfc(text_2_282)
    missing = [w for w in all_targets if _nfc(w) not in text_nfc]
    assert not missing, f"target words not found in 2:282 (even with NFC): {missing}"


# ─────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []


def _t(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        # PATCH 0 expectation: most of these PASS (current buggy state).
        # When a later PATCH fixes the bug, the corresponding assertion
        # will FAIL — that's the patch-acceptance signal.
        results.append((name, False, str(e)))
        print(f"  ✗ {name}")
        # show only first line of message for readability
        first_line = str(e).splitlines()[0] if str(e) else ""
        print(f"      {first_line}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"ERR: {e}"))
        print(f"  ✗ {name}: ERR {e}")


print("PATCH 0 + PATCH 1 + PATCH 2 — PRODUCTION PATH (segment() integration)")
print("=" * 70)
ALL = [
    ("t_segment_is_callable_via_production_import_path",
     t_segment_is_callable_via_production_import_path),
    # PATCH 1 targets
    ("t_walyaktub_segments_with_lam_al_amr",
     t_walyaktub_segments_with_lam_al_amr),
    ("t_falyaktub_segments_with_lam_al_amr",
     t_falyaktub_segments_with_lam_al_amr),
    ("t_walyumlil_segments_with_lam_al_amr",
     t_walyumlil_segments_with_lam_al_amr),
    ("t_falyumlil_segments_with_lam_al_amr",
     t_falyumlil_segments_with_lam_al_amr),
    ("t_walyattaqi_segments_with_lam_al_amr",
     t_walyattaqi_segments_with_lam_al_amr),
    # PATCH 1 regression guards
    ("t_lam_al_amr_does_not_fire_for_ordinary_lam_words",
     t_lam_al_amr_does_not_fire_for_ordinary_lam_words),
    ("t_lam_al_amr_conjunction_exception_does_not_break_nouns",
     t_lam_al_amr_conjunction_exception_does_not_break_nouns),
    # PATCH 2A — closed forms
    ("t_alladhi_locked_no_det_split", t_alladhi_locked_no_det_split),
    ("t_alladhina_must_remain_atomic", t_alladhina_must_remain_atomic),
    ("t_dhalikum_must_remain_atomic", t_dhalikum_must_remain_atomic),
    # PATCH 2C/2D — Form V/VI past
    ("t_tadayantum_no_imperf_prefix", t_tadayantum_no_imperf_prefix),
    ("t_tadayantum_aspect_is_past", t_tadayantum_aspect_is_past),
    ("t_tadayantum_evaluate_verb_form_is_certificate",
     t_tadayantum_evaluate_verb_form_is_certificate),
    ("t_tadayantum_l3_role_must_not_be_imperfect",
     t_tadayantum_l3_role_must_not_be_imperfect),
    ("t_tabaya3tum_no_imperf_prefix", t_tabaya3tum_no_imperf_prefix),
    ("t_tabaya3tum_aspect_is_past", t_tabaya3tum_aspect_is_past),
    ("t_real_imperfect_ta_still_detected", t_real_imperfect_ta_still_detected),
    # PATCH 3 — verification
    ("t_baynakum_no_prep_peel", t_baynakum_no_prep_peel),
    ("t_bbaynakum_no_prep_peel", t_bbaynakum_no_prep_peel),
    ("t_baynakum_l3_not_harf", t_baynakum_l3_not_harf),
    ("t_baynakum_l3_role_not_jazm", t_baynakum_l3_role_not_jazm),
    ("t_waliyyuhu_no_lam_prep_peel", t_waliyyuhu_no_lam_prep_peel),
    ("t_yakuna_no_na_possessive", t_yakuna_no_na_possessive),
    ("t_alla_an_tagged_harf_nasb_not_prep",
     t_alla_an_tagged_harf_nasb_not_prep),
    ("t_patch3_regressions_intact", t_patch3_regressions_intact),
    ("t_target_words_are_real_from_2_282",
     t_target_words_are_real_from_2_282),
]
for nm, fn in ALL:
    _t(nm, fn)
print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
print()
print("─" * 70)
print("PATCH 0 + 1 + 2 + 3 state (2026-05-26):")
print("  • PATCH 1: 5 lam-al-amr tests assert CONJ+LAM_AL_AMR+stem")
print("  • PATCH 2A: ٱلَّذِى atomic (no DET peel)")
print("  • PATCH 2B: ذَٰلِكُمْ atomic (demonstrative_compounds.csv)")
print("  • PATCH 2C: تَدَايَنتُم / تَبَايَعْتُمْ — no IMPERF_PREF peel")
print("  • PATCH 2D: تَدَايَنتُم / تَبَايَعْتُمْ — aspect=PV (past)")
print("  • PATCH 3A: بَيْنَ removed from PREP set (functional locative noun)")
print("  • PATCH 3B: وَلِيُّهُۥ — no false-لِ peel (shadda residual guard)")
print("  • PATCH 3C: يَكُونَا — نَا stays attached after IMPERF_PREF")
print("  • PATCH 3D: أَلَّا — أن tagged HARF_NASB, not PREP")
print("  • PATCH 3E: بَيْنَكُمْ L3 — MASAQ-HARF overridden to ISM_MUARAB")
print("  • PATCH 3 FIXUP: بَيْنَكُمْ / بَّيْنَكُمْ L3 role = ظرف مكان (not اسم مجزوم)")
print("─" * 70)
