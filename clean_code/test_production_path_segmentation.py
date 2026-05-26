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

def t_walyaktub_segments_with_lam_al_amr():
    """PATCH 1 target. Current = bug. After PATCH 1: must split."""
    r = segment("وَلْيَكْتُب")
    # PATCH 1 ACCEPTANCE: this assertion must change after the fix.
    # Current buggy behavior:
    assert _eq(r.stem, "وَلْيَكْتُب") and r.prefixes == [] and r.suffixes == [], (
        f"PATCH 1 TARGET — current output: {_describe(r)}.\n"
        f"After PATCH 1, expected something like:\n"
        f"  prefixes=['وَ', 'لْ'] (tags=['CONJ', 'LAM_AL_AMR']) | stem='يَكْتُب' | suffixes=[]\n"
        f"If you see this failure, PATCH 1 has shipped — UPDATE this test."
    )


def t_falyaktub_segments_with_lam_al_amr():
    r = segment("فَلْيَكْتُبْ")
    assert _eq(r.stem, "فَلْيَكْتُبْ") and r.prefixes == [] and r.suffixes == [], (
        f"PATCH 1 TARGET — current output: {_describe(r)}"
    )


def t_walyumlil_segments_with_lam_al_amr():
    r = segment("وَلْيُمْلِلِ")
    assert _eq(r.stem, "وَلْيُمْلِلِ") and r.prefixes == [] and r.suffixes == [], (
        f"PATCH 1 TARGET — current output: {_describe(r)}"
    )


def t_falyumlil_segments_with_lam_al_amr():
    r = segment("فَلْيُمْلِلْ")
    assert _eq(r.stem, "فَلْيُمْلِلْ") and r.prefixes == [] and r.suffixes == [], (
        f"PATCH 1 TARGET — current output: {_describe(r)}"
    )


def t_walyattaqi_segments_with_lam_al_amr():
    r = segment("وَلْيَتَّقِ")
    assert _eq(r.stem, "وَلْيَتَّقِ") and r.prefixes == [] and r.suffixes == [], (
        f"PATCH 1 TARGET — current output: {_describe(r)}"
    )


# ── PATCH 2 (A) — closed forms (BUG: ٱلَّذِى splits as الَّ + ذِى) ──

def t_alladhi_locked_no_det_split():
    """PATCH 2A target. Current = bug. After PATCH 2A: atomic."""
    r = segment("ٱلَّذِى")
    # Current buggy: prefixes=['الَّ'](DET), stem='ذِى'
    assert "DET" in (r.prefix_tags or []) and r.stem != "ٱلَّذِى", (
        f"PATCH 2A TARGET — current output: {_describe(r)}.\n"
        f"After PATCH 2A, expected: prefixes=[] | stem='ٱلَّذِى' | suffixes=[]"
    )


def t_alladhina_must_remain_atomic():
    """Regression guard: ٱلَّذِينَ is already atomic — must not regress."""
    r = segment("ٱلَّذِينَ")
    assert r.prefixes == [] and r.suffixes == [], (
        f"REGRESSION GUARD — ٱلَّذِينَ stopped being atomic: {_describe(r)}"
    )


def t_dhalikum_must_remain_atomic():
    """Regression guard: ذَٰلِكُمْ atomic via Batch 6. Must not regress."""
    r = segment("ذَٰلِكُمْ")
    assert r.prefixes == [] and r.suffixes == [], (
        f"REGRESSION GUARD — ذَٰلِكُمْ stopped being atomic: {_describe(r)}"
    )


# ── PATCH 2 (B) — Form VI past (BUG: تَ treated as IMPERF_PREF) ──

def t_tadayantum_currently_misread_as_imperfect():
    """PATCH 2B target. Current = bug. After PATCH 2B: past, no تَ-prefix peel."""
    r = segment("تَدَايَنتُم")
    # Current buggy: prefixes=['تَ'](IMPERF_PREF), stem='دَا', suffixes=['يَن'(NSUFF), 'تُم'(VSUFF)]
    pref_tags = r.prefix_tags or []
    assert "IMPERF_PREF" in pref_tags, (
        f"PATCH 2B TARGET — current output: {_describe(r)}.\n"
        f"After PATCH 2B, expected:\n"
        f"  prefixes=[] | stem='تَدَايَنْ' | suffixes=['تُم'(VSUFF)]"
    )


def t_tabaya3tum_currently_misread_as_imperfect():
    """PATCH 2B target. تَبَايَعْتُمْ also Form VI past."""
    r = segment("تَبَايَعْتُمْ")
    pref_tags = r.prefix_tags or []
    assert "IMPERF_PREF" in pref_tags, (
        f"PATCH 2B TARGET — current output: {_describe(r)}"
    )


# ── PATCH 3 — functional nouns, false-lam, dual-verb, alla ─────────

def t_baynakum_currently_split_as_prep():
    """PATCH 3 target. بَيْنَ should be functional noun, not PREP."""
    r = segment("بَيْنَكُمْ")
    pref_tags = r.prefix_tags or []
    assert "PREP" in pref_tags, (
        f"PATCH 3 TARGET — current output: {_describe(r)}.\n"
        f"After PATCH 3: بَيْنَ should not be peeled as PREP."
    )


def t_waliyyuhu_currently_split_as_lam_prep():
    """PATCH 3 target. وَلِيُّهُ = وَ + وَلِيّ + هُ, not و+ل(PREP)+يُّه."""
    r = segment("وَلِيُّهُۥ")
    pref_tags = r.prefix_tags or []
    assert "PREP" in pref_tags, (
        f"PATCH 3 TARGET — current output: {_describe(r)}"
    )


def t_yakuna_currently_treats_na_as_possessive():
    """PATCH 3 target. يَكُونَا = dual imperfect, نا is dual marker not POSS_PRON."""
    r = segment("يَكُونَا")
    suf_tags = r.suffix_tags or []
    assert "POSS_PRON" in suf_tags, (
        f"PATCH 3 TARGET — current output: {_describe(r)}"
    )


def t_alla_currently_tags_an_as_prep():
    """PATCH 3 target. أَلَّا = أن + لا. أن is HARF_NASB, not PREP."""
    r = segment("أَلَّا")
    pref_tags = r.prefix_tags or []
    assert "PREP" in pref_tags, (
        f"PATCH 3 TARGET — current output: {_describe(r)}.\n"
        f"After PATCH 3: tag should be HARF_NASB, not PREP."
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


print("PATCH 0 — PRODUCTION PATH CHARACTERIZATION (segment() integration)")
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
    # PATCH 2A — closed forms
    ("t_alladhi_locked_no_det_split", t_alladhi_locked_no_det_split),
    ("t_alladhina_must_remain_atomic", t_alladhina_must_remain_atomic),
    ("t_dhalikum_must_remain_atomic", t_dhalikum_must_remain_atomic),
    # PATCH 2B — Form VI past
    ("t_tadayantum_currently_misread_as_imperfect",
     t_tadayantum_currently_misread_as_imperfect),
    ("t_tabaya3tum_currently_misread_as_imperfect",
     t_tabaya3tum_currently_misread_as_imperfect),
    # PATCH 3
    ("t_baynakum_currently_split_as_prep",
     t_baynakum_currently_split_as_prep),
    ("t_waliyyuhu_currently_split_as_lam_prep",
     t_waliyyuhu_currently_split_as_lam_prep),
    ("t_yakuna_currently_treats_na_as_possessive",
     t_yakuna_currently_treats_na_as_possessive),
    ("t_alla_currently_tags_an_as_prep",
     t_alla_currently_tags_an_as_prep),
    ("t_target_words_are_real_from_2_282",
     t_target_words_are_real_from_2_282),
]
for nm, fn in ALL:
    _t(nm, fn)
print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed (current buggy state captured)")
print()
print("─" * 70)
print("PATCH 0 interpretation:")
print("  Tests that pass right now = production segment() produces buggy output.")
print("  When PATCH 1 ships, t_*_lam_al_amr tests must be REWRITTEN to assert")
print("  the new correct output. If they pass without being rewritten, the")
print("  patch didn't reach the production path.")
print("─" * 70)
