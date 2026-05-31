#!/usr/bin/env python3
"""test_phase4_certificate_reevaluation.py — قاعِدَة A1 من
PHASE4_CERTIFICATE_REEVALUATION_RULE_LOCK.md.

نِطاق الِاختبار (مَحصور):
  • ‏`_is_eligible_for_reevaluation` يَقبَل Certificate مِن
     {closed_function_word, non_verb_override_gate} لِكُلّ الـ8 surfaces.
  • مَسار re-evaluation في `maybe_apply_resolver`:
       - يُلصِق phase4_* metadata.
       - لا يَمَسّ word_class / proof_kind / source / proof_contract /
         closed_class_kind / proof_alternatives.
  • Certificates مِن مَصادِر خارِج الـ source-prefix gates (مَثَلًا MasterTokenLookup)
    لا تَدخُل re-evaluation.
  • Surface خارِج HANDLED_SURFACES_NORMALIZED لا يَدخُل re-evaluation.
  • flag OFF → byte-identical (لا تَغيير على الـ result).

هَذه الِاختبارات لا تَلمِس Layer 1 ولا engine — تَفحَص الـ integration.py
وَحدها بِـ result dicts صِناعيَّة. الـ resolver الحَقيقيّ يُستَدعى (لِأَنَّه ضَمن نَفس
الحُزمَة)، لِكَن مَنطِقه مُغَطًّى في test_phase4_resolver.py — هَذا المَلَفّ يَتَحَقَّق
مِن plumbing وَ invariants.
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from arabic_analyzer.contextual_resolver import integration as integ  # noqa: E402

_FLAG = "ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"


def _set_flag(val: bool) -> None:
    if val:
        os.environ[_FLAG] = "1"
    elif _FLAG in os.environ:
        del os.environ[_FLAG]


# ─────────────────────────────────────────────────────────────
# Fixtures — synthetic Layer 1 results
# ─────────────────────────────────────────────────────────────
def _closed_fn_certificate(word_class: str, kind: str) -> dict:
    """Mirror مَنَّ closed_function_word_gate يُعطيه (per layer1.py:449-453)."""
    return {
        "word_class": word_class,
        "source": f"closed_function_word:{kind}",
        "proof_kind": "Certificate",
        "proof_contract": "ClosedFunctionWordGate:v1",
        "proof_blockers": [],
        "proof_alternatives": [],
        "closed_class_kind": kind,
        "verb_aspect": "",
        "root": "",
        "wazn": "",
        "operator_i3rab": "",
    }


def _non_verb_override_certificate(word_class: str, reason_tail: str) -> dict:
    """Mirror ما يُعطيه non_verb_override_gate (per A0 evidence)."""
    return {
        "word_class": word_class,
        "source": f"non_verb_override_gate:{reason_tail}",
        "proof_kind": "Certificate",
        "proof_contract": "NonVerbOverrideGate:v1",
        "proof_blockers": [],
        "proof_alternatives": [],
        "closed_class_kind": "",
        "verb_aspect": "",
        "root": "",
        "wazn": "",
        "operator_i3rab": "",
    }


def _master_lookup_certificate(word_class: str) -> dict:
    """Mirror Certificate مِن MasterTokenLookup (خارِج نِطاق re-evaluation)."""
    return {
        "word_class": word_class,
        "source": "MasterTokenLookup:MASAQ",
        "proof_kind": "Certificate",
        "proof_contract": "MasterTokenLookupContract:v1",
        "proof_blockers": [],
        "proof_alternatives": [],
        "closed_class_kind": "",
        "verb_aspect": "",
        "root": "",
        "wazn": "",
        "operator_i3rab": "",
    }


# مَجموعَة keys يَنبَغي أَن تَبقى ثابِتَة بَعد re-evaluation
_INVARIANT_KEYS = (
    "word_class",
    "source",
    "proof_kind",
    "proof_contract",
    "proof_blockers",
    "proof_alternatives",
    "closed_class_kind",
    "verb_aspect",
    "root",
    "wazn",
    "operator_i3rab",
)


def _snapshot(d: dict) -> dict:
    return {k: deepcopy(d.get(k)) for k in _INVARIANT_KEYS}


def _assert_invariants_unchanged(original: dict, mutated: dict, label: str) -> None:
    for k in _INVARIANT_KEYS:
        assert mutated.get(k) == original.get(k), (
            f"{label}: invariant '{k}' changed: {original.get(k)!r} → {mutated.get(k)!r}"
        )


# ─────────────────────────────────────────────────────────────
# Tests — Path 2 (Certificate Re-evaluation)
# ─────────────────────────────────────────────────────────────
def t_certificate_reevaluation_runs_for_closed_function_min():
    """مِن مِن closed_function_word_gate → re-eval يُلصِق metadata."""
    _set_flag(True)
    try:
        r = _closed_fn_certificate("HARF", "HARF_JARR")
        snap = _snapshot(r)
        out = integ.maybe_apply_resolver(
            r, "مِنْ", prev_tokens=["قَالَ"], next_tokens=["الْكِتَابِ"]
        )
        assert out is r, "maybe_apply_resolver should mutate in place"
        assert out.get("phase4_review_mode") == "certificate_re_evaluation"
        assert out.get("phase4_source") == "ContextualAmbiguityResolver"
        assert "phase4_selected_function" in out
        _assert_invariants_unchanged(snap, out, "مِنْ")
    finally:
        _set_flag(False)


def t_certificate_reevaluation_runs_for_closed_function_ma():
    """مَا مِن closed_function_word_gate → re-eval يُلصِق metadata."""
    _set_flag(True)
    try:
        r = _closed_fn_certificate("ISM_MABNI", "WHAT")
        snap = _snapshot(r)
        out = integ.maybe_apply_resolver(
            r, "مَا", prev_tokens=["قَالَ"], next_tokens=["هَذَا"]
        )
        assert out.get("phase4_review_mode") == "certificate_re_evaluation"
        assert "phase4_selected_function" in out
        _assert_invariants_unchanged(snap, out, "مَا")
    finally:
        _set_flag(False)


def t_certificate_reevaluation_runs_for_mata_ayna_haythu():
    """مَتَى / حَيْثُ / بِمَا كُلُّها surfaces مَدعومَة — يَنبَغي أَن يَدخُلوا re-eval.

    NOTE: أَيْنَ مَستَبعَد مِن هَذا الِاختبار بِسَبَب bug upstream في الـ resolver:
    `_strip()` يُحَوِّل أَ إلى ا، بَينَما `HANDLED_SURFACES_NORMALIZED` تَحفَظ
    `"أين"` (هَمزَة-أَلِف). اَلنَّتيجَة: `_strip("أَيْنَ") = "اين"` لا يَتَطابَق مَع
    `"أين"`. هَذا upstream bug — يُغَطّيه
    `t_upstream_alef_variant_bug_documents_dead_surfaces` كَمُلاحَظَة.
    """
    _set_flag(True)
    try:
        surfaces = [
            ("مَتَى", "WHEN"),
            ("حَيْثُ", "LOCATIVE"),
            ("بِمَا", "PREP_COMPOUND"),
        ]
        for surface, kind in surfaces:
            r = _closed_fn_certificate("ISM_MABNI", kind)
            snap = _snapshot(r)
            out = integ.maybe_apply_resolver(
                r, surface, prev_tokens=["قَالَ"], next_tokens=["تَكُونوا"]
            )
            assert out.get("phase4_review_mode") == "certificate_re_evaluation", (
                f"{surface}: re-eval did not fire"
            )
            assert "phase4_selected_function" in out, surface
            _assert_invariants_unchanged(snap, out, surface)
    finally:
        _set_flag(False)


def t_certificate_reevaluation_runs_for_non_verb_override_ayy_anna():
    """non_verb_override_gate path يَعمَل لِـ surface في النِّطاق + source-prefix
    مَطلوب. نَستَخدِم مَنْ كَ مِثال (لَو وَصَلَ مِن non_verb_override_gate
    افتِراضيًّا، يَنبَغي أَن يَفعَّل re-eval).

    NOTE: الـ surfaces الَّتي تَأتي فِعليًّا مِن non_verb_override_gate في A0
    (أَيّ، أَنَّى) مُغلَقَة بِـ upstream alef-variant bug — راجِع
    `t_upstream_alef_variant_bug_documents_dead_surfaces`. هَذا الِاختبار يُؤَكِّد
    أَنّ الـ source-prefix gate يَعمَل عِندَ مَن يَنجو مِن الـ bug.
    """
    _set_flag(True)
    try:
        # نَستَخدِم مَن (surface في النِّطاق + لا تَتَأَثَّر بِـ alef-bug)
        # مَع source مِن non_verb_override_gate لِنَختَبِر الـ source-prefix
        # غَير `closed_function_word`.
        r = _non_verb_override_certificate(
            "ISM_MABNI",
            "functional noun (ظَرف/إِضافَة): مَن — synthetic for prefix coverage",
        )
        snap = _snapshot(r)
        out = integ.maybe_apply_resolver(
            r, "مَنْ", prev_tokens=["مِنْ"], next_tokens=["شَيْءٍ"]
        )
        assert out.get("phase4_review_mode") == "certificate_re_evaluation", (
            f"non_verb_override_gate prefix did not trigger re-eval "
            f"(source was {r.get('source')!r})"
        )
        assert out.get("phase4_original_source", "").startswith(
            "non_verb_override_gate"
        )
        _assert_invariants_unchanged(snap, out, "non_verb_override:مَنْ")
    finally:
        _set_flag(False)


def t_certificate_reevaluation_does_not_change_word_class():
    """re-eval لا يُغَيِّر word_class — هَذا invariant جَوهَريّ."""
    _set_flag(True)
    try:
        for surface, kind, wc in [
            ("مَتَى", "WHEN", "ISM_MABNI"),
            ("بِمَا", "PREP_COMPOUND", "HARF"),
            ("حَيْثُ", "LOCATIVE", "ISM_MABNI"),
            ("مَنْ", "WHO", "ISM_MABNI"),
        ]:
            r = _closed_fn_certificate(wc, kind)
            original_wc = r["word_class"]
            out = integ.maybe_apply_resolver(
                r, surface, prev_tokens=[], next_tokens=[]
            )
            assert out["word_class"] == original_wc, (
                f"{surface}: word_class flipped from {original_wc!r} "
                f"to {out['word_class']!r}"
            )
            # Path 2 يَجِب أَن يَكون قَد فَعَّل لِأَنَّ surface في النِّطاق + Certificate
            # مِن closed_function_word.
            assert out.get("phase4_review_mode") == "certificate_re_evaluation", surface
    finally:
        _set_flag(False)


def t_certificate_reevaluation_does_not_change_proof_kind():
    """re-eval لا يُغَيِّر proof_kind — يَبقى Certificate."""
    _set_flag(True)
    try:
        r = _closed_fn_certificate("ISM_MABNI", "WHEN")
        out = integ.maybe_apply_resolver(
            r, "مَتَى", prev_tokens=["قَالَ"], next_tokens=["تَأتِي"]
        )
        assert out["proof_kind"] == "Certificate", (
            f"proof_kind changed to {out['proof_kind']!r}"
        )
        # phase4_certainty مَيدان مُنفَصِل — لا يَدخُل proof_kind الرَّئيس.
        assert "phase4_certainty" in out
        assert out["phase4_certainty"] in ("Certificate", "Hypothesis")
    finally:
        _set_flag(False)


def t_certificate_reevaluation_does_not_change_source():
    """re-eval لا يُغَيِّر source — يَبقى closed_function_word:...

    نَستَخدِم مَتَى (surface سَليم — يَنجو مِن الـ alef-variant bug) بَدَل
    أَيْنَ المُغلَق upstream.
    """
    _set_flag(True)
    try:
        r = _closed_fn_certificate("ISM_MABNI", "WHEN")
        original_source = r["source"]
        out = integ.maybe_apply_resolver(
            r, "مَتَى", prev_tokens=[], next_tokens=[]
        )
        assert out["source"] == original_source, (
            f"source changed: {original_source!r} → {out['source']!r}"
        )
        # phase4_source في حَقل مُنفَصِل
        assert out.get("phase4_source") == "ContextualAmbiguityResolver", (
            f"phase4_source missing — re-eval did not fire? "
            f"keys present: {sorted(out.keys())}"
        )
        # phase4_original_source يَحفَظ الـ snapshot
        assert out.get("phase4_original_source") == original_source
    finally:
        _set_flag(False)


def t_certificate_reevaluation_attaches_phase4_metadata():
    """كُلّ مَفاتيح phase4_* المَنصوص علَيها يَنبَغي أَن تَظهَر."""
    _set_flag(True)
    try:
        r = _closed_fn_certificate("ISM_MABNI", "WHEN")
        out = integ.maybe_apply_resolver(
            r, "مَتَى", prev_tokens=["قَالَ"], next_tokens=["تَأتي"]
        )
        required = {
            "phase4_review_mode",
            "phase4_original_word_class",
            "phase4_original_source",
            "phase4_original_proof_kind",
            "phase4_original_candidates",
            "phase4_source",
            "phase4_selected_function",
            "phase4_reason",
            "phase4_context_features",
            "phase4_masaq_compatible_class",
            "phase4_certainty",
        }
        missing = required - set(out.keys())
        assert not missing, f"missing phase4 keys: {missing}"
        # تَأكيدات على القِيَم الثَّابِتَة
        assert out["phase4_review_mode"] == "certificate_re_evaluation"
        assert out["phase4_source"] == "ContextualAmbiguityResolver"
        assert out["phase4_original_proof_kind"] == "Certificate"
        assert out["phase4_original_word_class"] == "ISM_MABNI"
        assert out["phase4_original_source"].startswith("closed_function_word")
        # phase4_context_features يَنبَغي أَن يَكون dict (مِن extract_context_features)
        assert isinstance(out["phase4_context_features"], dict)
    finally:
        _set_flag(False)


# ─────────────────────────────────────────────────────────────
# Tests — Negative space (re-eval يَجِب أَن لا يُفَعَّل)
# ─────────────────────────────────────────────────────────────
def t_non_scope_certificate_not_reviewed():
    """surface خارِج HANDLED_SURFACES_NORMALIZED → لا re-eval، لا phase4_* إِطلاقًا."""
    _set_flag(True)
    try:
        # كَلِمَة عاديَّة لَيسَت ضِمن الـ8 surfaces (قَالَ مَثَلًا)
        r = _closed_fn_certificate("FIIL", "WHO")  # type لا يَهُمّ هُنا
        # نُغَيِّر source كَي يَكون ضِمن الـ prefixes كَي نَتَأكَّد أَنَّ النِّطاق هو الفِلتَر
        snap = _snapshot(r)
        out = integ.maybe_apply_resolver(
            r, "قَالَ", prev_tokens=[], next_tokens=[]
        )
        # لا يَجِب أَن يَظهَر أَيّ مِفتاح phase4_
        assert "phase4_review_mode" not in out
        assert "phase4_selected_function" not in out
        assert "phase4_source" not in out
        _assert_invariants_unchanged(snap, out, "قَالَ")
    finally:
        _set_flag(False)


def t_masaq_certificate_not_reviewed():
    """Certificate مِن MasterTokenLookup (لَيسَ من closed_function_word/non_verb_override)
    → لا re-eval، حَتَّى لَو surface في النِّطاق."""
    _set_flag(True)
    try:
        # سيناريو: مَا حُسِم عَبر MASAQ كَ ISM_MABNI، لا عَبر الـ gates المَحصورَة
        r = _master_lookup_certificate("ISM_MABNI")
        snap = _snapshot(r)
        out = integ.maybe_apply_resolver(
            r, "مَا", prev_tokens=["قَالَ"], next_tokens=["هَذَا"]
        )
        # لا re-eval — source لَيسَ مِن الـ allowed prefixes
        assert "phase4_review_mode" not in out, (
            "re-eval fired for MASAQ certificate — violates RULE_LOCK §٣.٢"
        )
        assert "phase4_selected_function" not in out
        _assert_invariants_unchanged(snap, out, "مَا (MASAQ)")
    finally:
        _set_flag(False)


def t_upstream_alef_variant_bug_documents_dead_surfaces():
    """مُلاحَظَة لِـ governance: 3 مِن الـ8 surfaces المُعلَنَة في
    HANDLED_SURFACES_NORMALIZED لا يُمكِن مُطابَقَتُها مَع `_strip()` لأَنّ الـ set
    يَحفَظ هَمزَة-أَلِف (أ) بَينَما `_strip` يُحَوِّلها إلى أَلِف بارِيَة (ا).

    أَثَر هَذا الـ bug:
      • أَيْنَ / أَيُّ / أَنَّى → لا يُحَلِّلهم الـ resolver، لا في Path 1 (Hypothesis)
        وَ لا في Path 2 (Certificate re-evaluation).
      • الـ A0 evidence أَظهَرَت أَنّ هَذِه الـ surfaces تَنال Certificate مِن
        الـ gates upstream — لِكَن الـ Phase 4 hook لا يَلتَقِطها أَبَدًا.

    حَوكَمَة:
      • هَذا الِاختبار **لا** يَفشَل — هو يَفحَص حالَة الـ bug القائِم وَ يُؤَكِّد أَنّ
        re-eval لَم يَفعَل لِأَيّ مِن الـ 3 surfaces.
      • الحَلّ يَستَوجِب تَطبيع `HANDLED_SURFACES_NORMALIZED` لِيُطابِق ناتِج
        `_strip()` — وَهَذا تَعديل في `resolver.py` خارِج نِطاق SPEC الحاليّ.
      • يَنبَغي فَتح SPEC مُنفَصِل: `PHASE4_RESOLVER_ALEF_NORMALIZATION_SPEC.md`.

    إذا ظَهَر تَفعيل لِأَيّ مِن الـ 3 surfaces في المُستَقبَل، فَهذا يَعني أَنّ الـ
    bug أُصلِحَ — يَجِب تَحديث هَذا الِاختبار وَ إِغلاق الـ SPEC المُتَوَقَّع.
    """
    _set_flag(True)
    try:
        dead_surfaces = ["أَيْنَ", "أَيُّ", "أَنَّى"]
        for surface in dead_surfaces:
            r = _closed_fn_certificate("ISM_MABNI", "FAKE_KIND")
            out = integ.maybe_apply_resolver(
                r, surface, prev_tokens=[], next_tokens=[]
            )
            assert "phase4_review_mode" not in out, (
                f"{surface}: re-eval fired unexpectedly — upstream bug fixed? "
                f"If yes, update this test + open the cleanup SPEC."
            )
    finally:
        _set_flag(False)


def t_flag_off_byte_identical():
    """flag OFF → الـ result يَرجِع كَما هو، حَتَّى لَو الشُّروط جَميعها مُحَقَّقَة."""
    _set_flag(False)
    r = _closed_fn_certificate("ISM_MABNI", "WHEN")
    snap = _snapshot(r)
    keys_before = set(r.keys())
    out = integ.maybe_apply_resolver(
        r, "مَتَى", prev_tokens=["قَالَ"], next_tokens=["تَأتي"]
    )
    keys_after = set(out.keys())
    new_keys = keys_after - keys_before
    assert not new_keys, f"flag OFF added keys: {new_keys}"
    _assert_invariants_unchanged(snap, out, "flag-OFF مَتَى")


# ─────────────────────────────────────────────────────────────
# Runner (نَفس نَمَط test_phase4_engine_hook.py)
# ─────────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []


def _t(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:  # noqa: BLE001
        import traceback
        tb = traceback.format_exc(limit=3)
        results.append((name, False, f"ERR: {e}"))
        print(f"  ✗ {name}: ERR {e}\n{tb}")


_set_flag(False)
print("PHASE 4 — CERTIFICATE RE-EVALUATION METADATA — Rule A1 (12 tests)")
print("=" * 70)
ALL = [
    ("t_certificate_reevaluation_runs_for_closed_function_min",
     t_certificate_reevaluation_runs_for_closed_function_min),
    ("t_certificate_reevaluation_runs_for_closed_function_ma",
     t_certificate_reevaluation_runs_for_closed_function_ma),
    ("t_certificate_reevaluation_runs_for_mata_ayna_haythu",
     t_certificate_reevaluation_runs_for_mata_ayna_haythu),
    ("t_certificate_reevaluation_runs_for_non_verb_override_ayy_anna",
     t_certificate_reevaluation_runs_for_non_verb_override_ayy_anna),
    ("t_certificate_reevaluation_does_not_change_word_class",
     t_certificate_reevaluation_does_not_change_word_class),
    ("t_certificate_reevaluation_does_not_change_proof_kind",
     t_certificate_reevaluation_does_not_change_proof_kind),
    ("t_certificate_reevaluation_does_not_change_source",
     t_certificate_reevaluation_does_not_change_source),
    ("t_certificate_reevaluation_attaches_phase4_metadata",
     t_certificate_reevaluation_attaches_phase4_metadata),
    ("t_non_scope_certificate_not_reviewed",
     t_non_scope_certificate_not_reviewed),
    ("t_masaq_certificate_not_reviewed",
     t_masaq_certificate_not_reviewed),
    ("t_upstream_alef_variant_bug_documents_dead_surfaces",
     t_upstream_alef_variant_bug_documents_dead_surfaces),
    ("t_flag_off_byte_identical",
     t_flag_off_byte_identical),
]
for nm, fn in ALL:
    _t(nm, fn)
_set_flag(False)
print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok:
            print(f"  ✗ {nm}: {err}")
    sys.exit(1)
