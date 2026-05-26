#!/usr/bin/env python3
"""test_refactor_step_b.py — يَتَأَكَّد أَنّ wrappers تُرجِع نَفس النَّتائج.

Step B = re-export فَقَط. لا تَغيير سُلوكيّ.
"""
import sys
sys.path.insert(0, ".")

results = []
def _t(name, fn):
    try:
        fn(); results.append((name, True, ""))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e))); print(f"  ✗ {name}: {e}")
    except Exception as e:
        results.append((name, False, f"ERR: {e}")); print(f"  ✗ {name}: ERR {e}")


# ─────────────────────────────────────────────────────────────
# Normalization wrapper
# ─────────────────────────────────────────────────────────────
def t_normalization_strip_diac_equivalent():
    from arabic_analyzer.normalization import strip_diacritics
    import linguistic_source_registry as old
    assert strip_diacritics("كَتَبَ") == old.strip_diac("كَتَبَ")


def t_normalization_strong_normalize_equivalent():
    from arabic_analyzer.normalization import normalize_strong
    # _strong_normalize logic: ٱ/آ/إ/أ/ؤ/ٰ → ا
    expected = "ابراهيم"
    got = normalize_strong("إِبْرَٰهِيمَ")
    # Strip diacritics manually to compare letters
    DIA = set("ًٌٍَُِّْـ")
    got_letters = "".join(c for c in got if c not in DIA)
    assert got_letters == "ابراهيم", f"got_letters={got_letters!r}"


def t_normalization_light_equivalent():
    from arabic_analyzer.normalization import normalize_light
    import linguistic_source_registry as old
    assert normalize_light("ٱللَّهُ") == old.normalize("ٱللَّهُ")


# ─────────────────────────────────────────────────────────────
# Registry wrapper — exactly same output as old module
# ─────────────────────────────────────────────────────────────
def t_registry_build_equivalent():
    from arabic_analyzer.registry import build_registry as new_build
    from linguistic_source_registry import build_registry as old_build
    new = new_build(); old = old_build()
    assert len(new["entries"]) == len(old["entries"])
    assert len(new["by_surface"]) == len(old["by_surface"])
    assert set(new["by_plain"].keys()) == set(old["by_plain"].keys())


def t_registry_resolve_strict_equivalent():
    from arabic_analyzer.registry import resolve_strict as new_resolve
    from linguistic_source_registry import resolve_strict as old_resolve
    for tok in ["هَذَا","الَّذِي","حَيْثُ","أَيْنَ","مَنْ","مَا",
                "إِنَّ","يَا","فِي","لَمْ","وَ","هُوَ","لِمَاذَا"]:
        new_r = new_resolve(tok); old_r = old_resolve(tok)
        assert new_r["candidates"] == old_r["candidates"], \
            f"{tok}: new={new_r['candidates']} old={old_r['candidates']}"
        assert new_r["certainty"] == old_r["certainty"], \
            f"{tok}: new cert={new_r['certainty']} old={old_r['certainty']}"
        assert new_r["source"] == old_r["source"]


def t_registry_compound_equivalent():
    from arabic_analyzer.registry import resolve_compound as new_c
    from linguistic_source_registry import resolve_compound as old_c
    for tok in ["لِمَاذَا","فَكَيفَ","وَمَن"]:
        nr = new_c(tok); orr = old_c(tok)
        if nr is None and orr is None: continue
        if nr is None or orr is None:
            raise AssertionError(f"{tok}: divergent None: new={nr is None} old={orr is None}")
        assert nr["head"].surface == orr["head"].surface


# ─────────────────────────────────────────────────────────────
# pre_segmentation_lookup
# ─────────────────────────────────────────────────────────────
def t_pre_segmentation_lookup_equivalent():
    from arabic_analyzer.registry import lookup_before_segmentation
    from linguistic_source_registry import resolve_strict
    for tok in ["هَذَا","مَنْ","فِي","لِمَاذَا","أُولَئِكَ"]:
        new_r = lookup_before_segmentation(tok)
        old_r = resolve_strict(tok)
        assert new_r["candidates"] == old_r["candidates"]
        assert new_r["certainty"] == old_r["certainty"]


def t_shared_registry_singleton():
    from arabic_analyzer.registry import get_shared_registry
    r1 = get_shared_registry()
    r2 = get_shared_registry()
    assert r1 is r2, "shared registry must be singleton (not rebuilt each call)"


# ─────────────────────────────────────────────────────────────
# Backward compatibility — Layer 1 still works
# ─────────────────────────────────────────────────────────────
def t_layer1_still_works():
    from i3rab_engine.layer1 import WordClassClassifier
    clf = WordClassClassifier()
    # Same expected outputs as Phase 3 tests
    cases = [
        ("هَذَا", "ISM_MABNI"),
        ("الَّذِي", "ISM_MAWSOOL"),
        ("كَتَبَ", "FIIL"),
        ("فِي", "HARF"),
        ("يَعْقُوبَ", ("JAMID","ISM_MUARAB")),
    ]
    for tok, exp in cases:
        r = clf.classify(tok)
        wc = r["word_class"]
        if isinstance(exp, tuple):
            assert wc in exp, f"{tok}: got {wc}, expected one of {exp}"
        else:
            assert wc == exp, f"{tok}: got {wc}, expected {exp}"


print("REFACTOR Step B — wrappers (re-export only)")
print("=" * 70)
ALL = [
    ("t_normalization_strip_diac_equivalent", t_normalization_strip_diac_equivalent),
    ("t_normalization_strong_normalize_equivalent", t_normalization_strong_normalize_equivalent),
    ("t_normalization_light_equivalent", t_normalization_light_equivalent),
    ("t_registry_build_equivalent", t_registry_build_equivalent),
    ("t_registry_resolve_strict_equivalent", t_registry_resolve_strict_equivalent),
    ("t_registry_compound_equivalent", t_registry_compound_equivalent),
    ("t_pre_segmentation_lookup_equivalent", t_pre_segmentation_lookup_equivalent),
    ("t_shared_registry_singleton", t_shared_registry_singleton),
    ("t_layer1_still_works", t_layer1_still_works),
]
for nm, fn in ALL: _t(nm, fn)
print()
passed = sum(1 for _,ok,_ in results if ok)
print(f"Result: {passed}/{len(results)} passed")
if passed < len(results):
    print("\n=== FAILURES ===")
    for nm, ok, err in results:
        if not ok: print(f"  ✗ {nm}: {err}")
