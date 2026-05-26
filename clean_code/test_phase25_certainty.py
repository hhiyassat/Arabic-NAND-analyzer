#!/usr/bin/env python3
"""test_phase25_certainty.py — اختبارات Phase 2.5.

تَوصيَة المُستَخدِم 2026-05-26:
  Certificate يَنفُذ فَقَط إذا:
    candidate_classes = 1  AND  no conflict  AND  not requires_context  AND  priority >= 8
"""
import sys
sys.path.insert(0, ".")
from linguistic_source_registry import (
    build_registry, resolve, resolve_compound, resolve_strict,
)

results = []
_reg = build_registry()


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


# ─────────────────────────────────────────────────────────────
# مَنْ — لا Certificate، candidates مُتَعَدِّدَة
# ─────────────────────────────────────────────────────────────
def test_man_not_harf_certificate():
    r = resolve_strict("مَنْ", _reg)
    assert r["certainty"] != "Certificate", \
        f"مَنْ certainty={r['certainty']} (must NOT be Certificate)"
    assert "HARF" not in r["candidates"] or len(r["candidates"]) > 1, \
        f"مَنْ candidates={r['candidates']} — must be ambiguous"


def test_man_returns_ambiguous_candidates():
    r = resolve_strict("مَنْ", _reg)
    expected = {"ISM_MABNI", "ISM_MAWSOOL", "HARF"}
    got = set(r["candidates"])
    assert expected.issubset(got) or "ISM_MAWSOOL" in got, \
        f"مَنْ candidates={got} — must include at least ISM_MAWSOOL"
    assert r["requires_context"], "مَنْ must require context"


def test_man_certainty_is_hypothesis():
    r = resolve_strict("مَنْ", _reg)
    assert r["certainty"] == "Hypothesis", \
        f"مَنْ certainty={r['certainty']} — must be Hypothesis"


# ─────────────────────────────────────────────────────────────
# مَتَى — ظَرف زَمان، لَيس HARF Certificate
# ─────────────────────────────────────────────────────────────
def test_mata_is_ism_mabni_not_harf_certificate():
    r = resolve_strict("مَتَى", _reg)
    assert r["certainty"] != "Certificate" or "HARF" not in r["candidates"], \
        f"مَتَى got HARF Certificate: {r}"


def test_mata_includes_ism_mabni():
    r = resolve_strict("مَتَى", _reg)
    assert "ISM_MABNI" in r["candidates"], \
        f"مَتَى candidates={r['candidates']} — must include ISM_MABNI"


def test_mata_requires_context_if_multiple_sources():
    r = resolve_strict("مَتَى", _reg)
    if len(r["candidates"]) > 1:
        assert r["requires_context"], \
            f"مَتَى has {len(r['candidates'])} candidates but requires_context=False"


# ─────────────────────────────────────────────────────────────
# لِمَاذَا — compound lookup
# ─────────────────────────────────────────────────────────────
def test_limadha_compound_lookup():
    comp = resolve_compound("لِمَاذَا", _reg)
    assert comp is not None, "لِمَاذَا must be parsable as compound"
    assert comp["is_compound"], "is_compound flag missing"


def test_limadha_not_no_match():
    r = resolve_strict("لِمَاذَا", _reg)
    assert r["found"], f"لِمَاذَا must be found (via compound), got: {r}"


def test_limadha_head_is_ism_mabni():
    r = resolve_strict("لِمَاذَا", _reg)
    # ماذا = اسم استِفهام مَبنيّ
    assert "ISM_MABNI" in r["candidates"] or "ISM_MAWSOOL" in r["candidates"], \
        f"لِمَاذَا head candidates={r['candidates']} — should be ISM_MABNI"


# ─────────────────────────────────────────────────────────────
# Certificate logic
# ─────────────────────────────────────────────────────────────
def test_registry_certificate_requires_single_class():
    """أَيّ entry بِـCertificate يَجِب أَن يَكون لَه candidate_class واحِد."""
    for e in _reg["entries"]:
        if e.certainty == "Certificate":
            assert len(e.candidate_classes) == 1, \
                f"Certificate entry has {len(e.candidate_classes)} classes: {e.source_id}"


def test_priority_does_not_override_conflict():
    """لَو الـsurface لَه class conflict عَبر sources، لا Certificate حَتَّى لَو priority=9."""
    for plain, cands in _reg["conflict_map"].items():
        if len(cands) <= 1: continue
        # كُلّ entries بِنَفس الـplain يَجِب أَن تَكون Hypothesis
        es = _reg["by_plain"].get(plain, [])
        for e in es:
            assert e.certainty == "Hypothesis", \
                f"Conflict surface '{plain}' has Certificate entry {e.source_id}!"


def test_ambiguous_registry_entry_blocks_certificate():
    r = resolve_strict("مَنْ", _reg)
    assert r["certainty"] == "Hypothesis", "مَنْ must produce Hypothesis"
    assert r["requires_context"], "مَنْ must require context"


# ─────────────────────────────────────────────────────────────
# Regression: الـclear cases ما زالَت Certificate
# ─────────────────────────────────────────────────────────────
def test_haza_still_certificate():
    r = resolve_strict("هَذَا", _reg)
    assert r["certainty"] == "Certificate", \
        f"هَذَا lost Certificate: {r['certainty']}"
    assert r["candidates"] == ["ISM_MABNI"]


def test_alladhi_still_certificate():
    r = resolve_strict("الَّذِي", _reg)
    assert r["certainty"] == "Certificate", \
        f"الَّذِي lost Certificate: {r['certainty']}"
    assert "ISM_MAWSOOL" in r["candidates"]


def test_yaa_still_certificate():
    r = resolve_strict("يَا", _reg)
    assert r["certainty"] == "Certificate"


def test_fi_still_certificate():
    r = resolve_strict("فِي", _reg)
    assert r["certainty"] == "Certificate"
    assert "HARF" in r["candidates"]


def test_huwa_still_certificate():
    r = resolve_strict("هُوَ", _reg)
    assert r["certainty"] == "Certificate"
    assert "ISM_MABNI" in r["candidates"]


def test_inna_still_certificate():
    r = resolve_strict("إِنَّ", _reg)
    assert r["certainty"] == "Certificate"


def test_lam_still_certificate():
    r = resolve_strict("لَمْ", _reg)
    assert r["certainty"] == "Certificate"


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────
print("Phase 2.5 — certainty logic + compound lookup")
print("=" * 70)
ALL = [
    ("test_man_not_harf_certificate", test_man_not_harf_certificate),
    ("test_man_returns_ambiguous_candidates", test_man_returns_ambiguous_candidates),
    ("test_man_certainty_is_hypothesis", test_man_certainty_is_hypothesis),
    ("test_mata_is_ism_mabni_not_harf_certificate", test_mata_is_ism_mabni_not_harf_certificate),
    ("test_mata_includes_ism_mabni", test_mata_includes_ism_mabni),
    ("test_mata_requires_context_if_multiple_sources", test_mata_requires_context_if_multiple_sources),
    ("test_limadha_compound_lookup", test_limadha_compound_lookup),
    ("test_limadha_not_no_match", test_limadha_not_no_match),
    ("test_limadha_head_is_ism_mabni", test_limadha_head_is_ism_mabni),
    ("test_registry_certificate_requires_single_class", test_registry_certificate_requires_single_class),
    ("test_priority_does_not_override_conflict", test_priority_does_not_override_conflict),
    ("test_ambiguous_registry_entry_blocks_certificate", test_ambiguous_registry_entry_blocks_certificate),
    ("test_haza_still_certificate", test_haza_still_certificate),
    ("test_alladhi_still_certificate", test_alladhi_still_certificate),
    ("test_yaa_still_certificate", test_yaa_still_certificate),
    ("test_fi_still_certificate", test_fi_still_certificate),
    ("test_huwa_still_certificate", test_huwa_still_certificate),
    ("test_inna_still_certificate", test_inna_still_certificate),
    ("test_lam_still_certificate", test_lam_still_certificate),
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
