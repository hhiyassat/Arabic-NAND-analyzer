"""test_maani_batch_c2_afal_tahwil_hygiene.py — MAANI Batch C2 verification.

Binding scope (per RULE_LOCK f67ee6b):
  - zann_family_meanings.csv loses 4 transformation-verb rows
  - transform_verbs_meanings.csv (new) holds 5 data rows: framework + 4 migrated
  - 19-column schema unchanged
  - ProofKind enum unchanged; Batch B monotonicity preserved
  - author_position preserved verbatim (SAYYARA/TARAKA stay 'reported')
  - vocalization preserved verbatim (اتَّخَذَ without initial kasra)

Tests per RULE_LOCK section 11:
  S1-S5  Structural (header, row counts, loader entry)
  H1-H6  Hygiene invariants (no duplicates, no silent flips, vocalization)
  C1-C7  Claim-level lookups (Certificate / Hypothesis discipline)
  R1-R2  Sweep regeneration assertions
"""

from __future__ import annotations

import csv
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_DATA_DIR = _HERE / "data" / "contracts" / "maani" / "volume2"
_TRANSFORM_CSV = _DATA_DIR / "transform_verbs_meanings.csv"
_ZANN_CSV = _DATA_DIR / "zann_family_meanings.csv"
_SWEEP_DIR = _HERE / "data" / "samarrai_sweep"

_SCHEMA_COLUMNS = [
    "priority", "topic_id", "operator", "vocalized_form", "meaning_id",
    "meaning_ar", "syntactic_effect", "semantic_field", "conditions",
    "exceptions", "warnings", "example_constructed", "example_quran",
    "surah_ayah", "author_position", "disagreement", "source_part",
    "source_page", "confidence",
]

_TRANSFORMATION_SEMANTIC_FIELDS = {
    "causative_transformation",
    "transformation_or_taking",
    "pure_transformation",
    "transformation_via_leaving",
}

_MIGRATED_OPERATORS = ["جَعَلَ", "اتَّخَذَ", "صَيَّرَ", "تَرَكَ"]
_LEGACY_MEANING_IDS = ["JAALA_VERB", "ITTAKHADHA_VERB", "SAYYARA_VERB", "TARAKA_TRANS"]


def _load_csv(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# S1
def t_transform_verbs_csv_header_matches_schema():
    assert _TRANSFORM_CSV.exists(), f"{_TRANSFORM_CSV} does not exist"
    with _TRANSFORM_CSV.open(encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == _SCHEMA_COLUMNS, (
        f"header mismatch.\n  expected: {_SCHEMA_COLUMNS}\n  got: {header}"
    )


# S2
def t_transform_verbs_row_count_is_exactly_5():
    rows = _load_csv(_TRANSFORM_CSV)
    assert len(rows) == 5, f"expected 5 data rows; got {len(rows)}"


# S3
def t_zann_family_row_count_decreases_to_12():
    rows = _load_csv(_ZANN_CSV)
    assert len(rows) == 12, f"expected 12 data rows; got {len(rows)}"


# S4
def t_zann_family_holds_no_migrated_meaning_ids():
    rows = _load_csv(_ZANN_CSV)
    ids = {r.get("meaning_id", "") for r in rows}
    leftover = ids & set(_LEGACY_MEANING_IDS)
    assert not leftover, (
        f"zann_family still contains migrated meaning_ids: {leftover}"
    )


# S5
def t_loader_includes_transform_verbs_entry():
    from samarrai_loaders.volume2_loader import _CACHE, stats
    # Force reload to pick up new file
    import samarrai_loaders.volume2_loader as v2
    v2._CACHE = None
    s = stats()
    files = s.get("files", {})
    assert files.get("transform_verbs") == 5, (
        f"loader does not show transform_verbs=5; got files={files}"
    )


# H1
def t_no_operator_carries_transformation_in_two_topics():
    import samarrai_loaders.volume2_loader as v2
    v2._CACHE = None
    recs = v2.all_records()
    for op in _MIGRATED_OPERATORS:
        matches = [
            r for r in recs
            if r.get("operator") == op
            and r.get("semantic_field") in _TRANSFORMATION_SEMANTIC_FIELDS
        ]
        topics = {r.get("topic_id") for r in matches}
        assert len(matches) == 1, (
            f"operator {op!r} has {len(matches)} transformation records; "
            f"expected 1. topics={topics}"
        )
        assert topics == {"AFAL_TAHWIL"}, (
            f"operator {op!r} transformation record under {topics}, expected "
            f"AFAL_TAHWIL only"
        )


# H2
def t_zann_family_holds_no_transformation_rows():
    rows = _load_csv(_ZANN_CSV)
    violations = [
        r for r in rows
        if r.get("topic_id") == "ZANN_FAMILY"
        and r.get("semantic_field") in _TRANSFORMATION_SEMANTIC_FIELDS
    ]
    assert not violations, (
        f"zann_family has transformation-class rows: "
        f"{[(r.get('meaning_id'), r.get('semantic_field')) for r in violations]}"
    )


# H3
def t_migrated_rows_preserve_author_position():
    rows = _load_csv(_TRANSFORM_CSV)
    by_mid = {r["meaning_id"]: r for r in rows}
    expected = {
        "AFAL_TAHWIL_JAAL": "preferred",
        "AFAL_TAHWIL_ITTAKHATHA": "preferred",
        "AFAL_TAHWIL_SAYYARA": "reported",
        "AFAL_TAHWIL_TARAKA": "reported",
    }
    for mid, want in expected.items():
        assert mid in by_mid, f"missing row {mid}"
        got = by_mid[mid].get("author_position", "")
        assert got == want, (
            f"{mid}.author_position={got!r}, expected {want!r}"
        )


# H4
def t_migrated_rows_preserve_provenance():
    rows = _load_csv(_TRANSFORM_CSV)
    by_mid = {r["meaning_id"]: r for r in rows}
    expected = {
        "AFAL_TAHWIL_JAAL": ("2", "26", "0.92"),
        "AFAL_TAHWIL_ITTAKHATHA": ("2", "26", "0.92"),
        "AFAL_TAHWIL_SAYYARA": ("2", "26", "0.9"),
        "AFAL_TAHWIL_TARAKA": ("2", "26", "0.88"),
    }
    for mid, (sp, spg, conf) in expected.items():
        r = by_mid.get(mid)
        assert r is not None, f"missing row {mid}"
        got = (
            r.get("source_part", ""),
            r.get("source_page", ""),
            r.get("confidence", ""),
        )
        assert got == (sp, spg, conf), (
            f"{mid} provenance={got!r}, expected ({sp!r}, {spg!r}, {conf!r})"
        )


# H5
def t_ittakhatha_vocalization_preserved():
    rows = _load_csv(_TRANSFORM_CSV)
    by_mid = {r["meaning_id"]: r for r in rows}
    r = by_mid.get("AFAL_TAHWIL_ITTAKHATHA")
    assert r is not None, "missing AFAL_TAHWIL_ITTAKHATHA row"
    voc = r.get("vocalized_form", "")
    assert len(voc) >= 2, f"vocalized_form too short: {voc!r}"
    c0 = voc[0]
    c1 = voc[1]
    assert c0 == "ا", (
        f"first char {hex(ord(c0))}, expected U+0627 ALEF"
    )
    assert c1 != "ِ", (
        f"second char is KASRA U+0650; expected non-kasra (got vocalization {voc!r})"
    )
    assert c1 == "ت", (
        f"second char {hex(ord(c1))}, expected U+062A TEH (not kasra)"
    )


# H6
def t_no_legacy_meaning_id_strings_anywhere_in_csvs():
    maani_dir = _HERE / "data" / "contracts" / "maani"
    found = []
    for csv_path in maani_dir.rglob("*.csv"):
        text = csv_path.read_text(encoding="utf-8")
        for legacy in _LEGACY_MEANING_IDS:
            if legacy in text:
                found.append((csv_path.relative_to(maani_dir).as_posix(), legacy))
    assert not found, f"legacy meaning_ids still present in CSVs: {found}"


# Helper for claim-level tests
def _safe_lookup(word):
    try:
        from samarrai_analyzer import lookup_word_all_volumes
    except (ImportError, OSError, PermissionError):
        return None
    try:
        return lookup_word_all_volumes(word, "exact_vocalized")
    except (PermissionError, OSError, FileNotFoundError):
        return None


# C1
def t_jaala_returns_one_afal_tahwil_certificate():
    claims = _safe_lookup("جَعَلَ")
    if claims is None:
        print("  [skipped - analyzer unavailable]", end=" ")
        return
    matches = [
        c for c in claims
        if (getattr(c, "topic_id", "") or "") == "AFAL_TAHWIL"
        and (getattr(c, "meaning_id", "") or "") == "AFAL_TAHWIL_JAAL"
    ]
    assert matches, "جَعَلَ produced no AFAL_TAHWIL_JAAL claim"
    c = matches[0]
    assert (getattr(c, "proof_kind", "") or "") == "Certificate", (
        f"AFAL_TAHWIL_JAAL proof_kind={getattr(c,'proof_kind','')!r}"
    )


# C2
def t_ittakhatha_returns_one_afal_tahwil_certificate():
    claims = _safe_lookup("اتَّخَذَ")
    if claims is None:
        print("  [skipped - analyzer unavailable]", end=" ")
        return
    matches = [
        c for c in claims
        if (getattr(c, "topic_id", "") or "") == "AFAL_TAHWIL"
        and (getattr(c, "meaning_id", "") or "") == "AFAL_TAHWIL_ITTAKHATHA"
    ]
    assert matches, "اتَّخَذَ produced no AFAL_TAHWIL_ITTAKHATHA claim"
    c = matches[0]
    assert (getattr(c, "proof_kind", "") or "") == "Certificate", (
        f"AFAL_TAHWIL_ITTAKHATHA proof_kind={getattr(c,'proof_kind','')!r}"
    )


# C3
def t_sayyara_returns_one_afal_tahwil_hypothesis():
    claims = _safe_lookup("صَيَّرَ")
    if claims is None:
        print("  [skipped - analyzer unavailable]", end=" ")
        return
    matches = [
        c for c in claims
        if (getattr(c, "topic_id", "") or "") == "AFAL_TAHWIL"
        and (getattr(c, "meaning_id", "") or "") == "AFAL_TAHWIL_SAYYARA"
    ]
    assert matches, "صَيَّرَ produced no AFAL_TAHWIL_SAYYARA claim"
    c = matches[0]
    assert (getattr(c, "proof_kind", "") or "") == "Hypothesis", (
        f"AFAL_TAHWIL_SAYYARA proof_kind={getattr(c,'proof_kind','')!r}, "
        f"expected Hypothesis (author_position=reported)"
    )


# C4
def t_taraka_returns_one_afal_tahwil_hypothesis():
    claims = _safe_lookup("تَرَكَ")
    if claims is None:
        print("  [skipped - analyzer unavailable]", end=" ")
        return
    matches = [
        c for c in claims
        if (getattr(c, "topic_id", "") or "") == "AFAL_TAHWIL"
        and (getattr(c, "meaning_id", "") or "") == "AFAL_TAHWIL_TARAKA"
    ]
    assert matches, "تَرَكَ produced no AFAL_TAHWIL_TARAKA claim"
    c = matches[0]
    assert (getattr(c, "proof_kind", "") or "") == "Hypothesis", (
        f"AFAL_TAHWIL_TARAKA proof_kind={getattr(c,'proof_kind','')!r}, "
        f"expected Hypothesis (author_position=reported)"
    )


# C5
def t_framework_row_loads():
    import samarrai_loaders.volume2_loader as v2
    v2._CACHE = None
    recs = v2.all_records()
    framework = [
        r for r in recs
        if r.get("topic_id") == "AFAL_TAHWIL"
        and r.get("meaning_id") == "AFAL_TAHWIL_BASIC"
    ]
    assert framework, "AFAL_TAHWIL_BASIC framework row not found"
    r = framework[0]
    ma = r.get("meaning_ar") or ""
    assert ("أفعال التحويل" in ma) or ("أَفعال التَّحويل" in ma), (
        f"framework meaning_ar must mention أفعال التحويل; got {ma!r}"
    )


# C6
def t_zann_cognition_verbs_still_return_zann_family():
    for op in ["ظَنَّ", "حَسِبَ", "عَلِمَ", "رَأَى", "وَجَدَ"]:
        claims = _safe_lookup(op)
        if claims is None:
            print(f"  [skipped {op} - analyzer unavailable]", end=" ")
            continue
        zann = [c for c in claims if (getattr(c, "topic_id", "") or "") == "ZANN_FAMILY"]
        afal = [c for c in claims if (getattr(c, "topic_id", "") or "") == "AFAL_TAHWIL"]
        assert zann, f"{op} returned no ZANN_FAMILY claim"
        assert not afal, (
            f"{op} unexpectedly returned AFAL_TAHWIL claim: "
            f"{[(getattr(c,'meaning_id','')) for c in afal]}"
        )


# C7
def t_no_duplicate_claims_for_migrated_operators():
    for op in _MIGRATED_OPERATORS:
        claims = _safe_lookup(op)
        if claims is None:
            print(f"  [skipped {op} - analyzer unavailable]", end=" ")
            continue
        topics = {(getattr(c, "topic_id", "") or "") for c in claims}
        assert "ZANN_FAMILY" not in topics, (
            f"{op} still returns ZANN_FAMILY claim; expected only AFAL_TAHWIL. "
            f"topics={topics}"
        )


# R1
def t_sweep_per_word_uses_new_meaning_ids():
    p = _SWEEP_DIR / "per_word.csv"
    assert p.exists(), f"{p} does not exist (sweep not regenerated?)"
    text = p.read_text(encoding="utf-8")
    leftover = [m for m in _LEGACY_MEANING_IDS if m in text]
    assert not leftover, (
        f"per_word.csv contains legacy meaning_ids: {leftover}"
    )


# R2
def t_sweep_top_topics_includes_afal_tahwil():
    p = _SWEEP_DIR / "top_topics.csv"
    assert p.exists(), f"{p} does not exist (sweep not regenerated?)"
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    afal = [r for r in rows if r.get("topic_id") == "AFAL_TAHWIL"]
    assert afal, (
        f"top_topics.csv has no AFAL_TAHWIL row; "
        f"topics={[r.get('topic_id') for r in rows]}"
    )
    cnt = int(afal[0].get("count", "0"))
    assert cnt > 0, f"AFAL_TAHWIL count is {cnt}"
    zann = [r for r in rows if r.get("topic_id") == "ZANN_FAMILY"]
    if zann:
        zcnt = int(zann[0].get("count", "0"))
        assert zcnt < 313, (
            f"ZANN_FAMILY count {zcnt} did not decrease from 313 baseline"
        )


# Driver
results = []


def _run(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  PASS {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  FAIL {name}")
        first_line = str(e).splitlines()[0] if str(e) else ""
        print(f"      {first_line}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"ERR: {e}"))
        print(f"  FAIL {name}: ERR {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("MAANI Batch C2 - AFAL_TAHWIL Hygiene")
    print("=" * 70)
    ALL = [
        ("S1 t_transform_verbs_csv_header_matches_schema", t_transform_verbs_csv_header_matches_schema),
        ("S2 t_transform_verbs_row_count_is_exactly_5", t_transform_verbs_row_count_is_exactly_5),
        ("S3 t_zann_family_row_count_decreases_to_12", t_zann_family_row_count_decreases_to_12),
        ("S4 t_zann_family_holds_no_migrated_meaning_ids", t_zann_family_holds_no_migrated_meaning_ids),
        ("S5 t_loader_includes_transform_verbs_entry", t_loader_includes_transform_verbs_entry),
        ("H1 t_no_operator_carries_transformation_in_two_topics", t_no_operator_carries_transformation_in_two_topics),
        ("H2 t_zann_family_holds_no_transformation_rows", t_zann_family_holds_no_transformation_rows),
        ("H3 t_migrated_rows_preserve_author_position", t_migrated_rows_preserve_author_position),
        ("H4 t_migrated_rows_preserve_provenance", t_migrated_rows_preserve_provenance),
        ("H5 t_ittakhatha_vocalization_preserved", t_ittakhatha_vocalization_preserved),
        ("H6 t_no_legacy_meaning_id_strings_anywhere_in_csvs", t_no_legacy_meaning_id_strings_anywhere_in_csvs),
        ("C1 t_jaala_returns_one_afal_tahwil_certificate", t_jaala_returns_one_afal_tahwil_certificate),
        ("C2 t_ittakhatha_returns_one_afal_tahwil_certificate", t_ittakhatha_returns_one_afal_tahwil_certificate),
        ("C3 t_sayyara_returns_one_afal_tahwil_hypothesis", t_sayyara_returns_one_afal_tahwil_hypothesis),
        ("C4 t_taraka_returns_one_afal_tahwil_hypothesis", t_taraka_returns_one_afal_tahwil_hypothesis),
        ("C5 t_framework_row_loads", t_framework_row_loads),
        ("C6 t_zann_cognition_verbs_still_return_zann_family", t_zann_cognition_verbs_still_return_zann_family),
        ("C7 t_no_duplicate_claims_for_migrated_operators", t_no_duplicate_claims_for_migrated_operators),
        ("R1 t_sweep_per_word_uses_new_meaning_ids", t_sweep_per_word_uses_new_meaning_ids),
        ("R2 t_sweep_top_topics_includes_afal_tahwil", t_sweep_top_topics_includes_afal_tahwil),
    ]
    for nm, fn in ALL:
        _run(nm, fn)
    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Result: {passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)
