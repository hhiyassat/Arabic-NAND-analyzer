# PATCH 0 — Production Path Verification

> **Date:** 2026-05-26
> **Scope:** verification only — no logic fix.
> **Mandate (verbatim from user prompt):**
> > "Do not implement fixes yet in Patch 0. Commit only if you add the production-path integration test."
> **Deliverables:**
> - this document
> - `clean_code/test_production_path_segmentation.py` (16 tests, all passing on current buggy state)

## The diagnosis the user demanded

The user observed that the file `out_2_282_phase4_off-cd4bcbc7.txt` shows the same L1/L2/L3 errors as the original `out_2_282_phase4_off.txt` — `وَلْيَكْتُب` still appears as a whole stem, `ٱلَّذِى` still splits as `الَّ(DET) + ذِى`, `تَدَايَنتُم` still has `تَ(IMPERF_PREF)`, etc. — despite the prior session writing 7 batches of "fixes" with passing unit tests.

The user's diagnostic checklist:
> 1. Did Claude modify a helper that isn't used?
> 2. Are there two versions of segmenter?
> 3. Does analyze_verse_v3.py read an old segmenter?
> 4. Does the display layer print old segmentation cached on another object?
> 5. Do tests run against a contract directly and not the production pipeline?

PATCH 0 answers all five.

---

## Findings

### Finding #1 — there is ONE production segmenter

Four files on disk contain "segmenter" code, but only one is on the production path:

| File | Reached by `analyze_verse_v3.py`? |
|---|---|
| `clean_code/segmenter.py` | **YES — production** (imported at `analyze_verse_v3.py:67`) |
| `clean_code/arabic_analyzer/segmentation/segmenter.py` | No — it's a wrapper that re-exports from `clean_code/segmenter.py` |
| `archive/legacy_src/architecture_test/segmenter_adapter.py` | No — legacy artifact |
| `dist/arabic_tools/clean_code/segmenter.py` | No — distribution copy |

**Answer to checklist Q2 + Q4:** no duplicate segmenter. Editing `clean_code/segmenter.py` does reach production.

### Finding #2 — the production path is a single function

```
CLI:  python3 analyze_verse_v3.py --verse 2:282 --all
  └─ analyze_verse_v3.main()
     └─ show_morph(text)                             [line 347]
        └─ from segmenter import segment             [line 67, runtime import]
        └─ for word in text.split():
           └─ r = segment(word)                       [calls segmenter.py:1698]
           └─ prints r.prefixes / r.prefix_tags
                    r.stem
                    r.suffixes / r.suffix_tags
```

There is no other code path that produces the L1/L2 lines. Edit `segmenter.segment()` ⇒ the L1/L2 lines change. Don't edit it ⇒ they don't.

**Answer to checklist Q1 + Q3:** the prior session's experimental "fixes" never modified `segmenter.segment()` for the lam-al-amr / تَدَايَنتُم / بَيْنَكُمْ cases. They added helpers, CSVs, and wrapper contracts that `segment()` does not consult. That's why the output is unchanged.

### Finding #3 — the smoking gun: helper-only tests pass while production unchanged

`test_verb_form_contract.py:82` already has:

```python
def test_wa_l_yaktub_is_jussive_command_verb():
    v = evaluate_verb_form("وَلْيَكْتُبْ")
    assert v.kind == "Certificate", f"expected Certificate, got {v.kind}"
    assert v.aspect == "IV", f"expected IV, got {v.aspect}"
    assert v.mood == "JUSS", f"expected JUSS, got {v.mood}"
    assert v.prefix_stack.has_lam_amr, "expected has_lam_amr"
    assert v.prefix_stack.has_conj, "expected has_conj"
```

This test **passes today**. The helper `evaluate_verb_form()` correctly identifies `وَلْيَكْتُبْ` as IV + JUSS + lam_amr + conj.

But:

```bash
grep -nE "evaluate_verb_form|verb_form_contract" segmenter.py
# → (no output)
```

`segmenter.py` has **zero references** to `evaluate_verb_form` or `verb_form_contract`. The two modules are **completely disconnected**. So:

- `evaluate_verb_form("وَلْيَكْتُبْ")` → "yes, it's a jussive command verb" ✓ test passes
- `segment("وَلْيَكْتُبْ")` → "I don't know what this is, leave it as stem" ✗ output broken

**This is the structural cause of the user's complaint.** Every existing test for the problem words (lam-al-amr forms, تَدَايَنتُم, بَيْنَكُمْ, ٱلَّذِى) calls a helper. **None** of them call `segment()`.

Audit of existing tests:

| Test | Calls production `segment()`? | What it tests |
|---|---|---|
| `test_verb_form_contract.py::test_wa_l_yaktub_is_jussive_command_verb` | ❌ | `evaluate_verb_form()` — a helper L1 consumes for word_class only, NOT a helper segmenter consumes |
| `test_non_verb_override.py::test_real_verbs_still_pass` | ❌ | `WordClassClassifier.classify()` — also L3, not L1 segmentation |
| `test_closed_function_word.py::test_real_verbs_unaffected` | ❌ | `is_closed_function_word()` + `_classify()` — neither calls segment |
| `test_demonstrative_compounds_atomic.py::*` (Batch 6) | ✅ | `segment()` directly — that's why ذَٰلِكُمْ atomic shows up in production output |
| `test_segmenter_display_stem.py::*` (Batch 7) | ✅ | `segment()` directly — that's why display_stem changes show |

**Answer to checklist Q5:** yes — exactly as the user feared, most tests run helpers, not the production pipeline. Only Batches 6 and 7 happened to test production `segment()`, and **only those two show effects** in the actual output.

### Finding #4 (bonus) — NFC is mandatory even in tests

While writing the integration test I hit a Unicode trap. `وَلْيَتَّقِ` in my Python literal uses `…ت + َ + ّ + ق + ِ` ordering. The Quran file uses Uthmani `…ت + ّ + َ + ق + ِ`. Visually identical, byte-different. Both produce identical NFC. Without NFC normalization on both sides, `target in verse` returns `False` for 5 of the 14 target words.

**Implication:** any future PATCH must NFC-normalize both production code AND test fixtures whenever Arabic strings are compared. The patch's own logic could be perfect and still produce false-negative tests.

CONSTITUTION.md §2.2 already mandates NFC at load + lookup time. PATCH 0 simply confirms this applies to test code too.

---

## The integration test (PATCH 0 deliverable)

`clean_code/test_production_path_segmentation.py` — 16 tests, runs in <1s, **all pass against the current buggy code**.

### How to read the results

The test file is a *characterization test*. Each assertion captures **what `segment()` returns today**, not what it should return.

```
✓ t_walyaktub_segments_with_lam_al_amr     ← passes BECAUSE the bug exists
✓ t_alladhi_locked_no_det_split             ← passes BECAUSE الَّ(DET) is wrongly split
✓ t_tadayantum_currently_misread_as_imperfect  ← passes BECAUSE تَ is wrongly peeled
✓ t_baynakum_currently_split_as_prep        ← passes BECAUSE بَيْنَ wrongly tagged PREP
✓ t_yakuna_currently_treats_na_as_possessive ← passes BECAUSE نَا wrongly tagged POSS_PRON
✓ t_alla_currently_tags_an_as_prep          ← passes BECAUSE أن wrongly tagged PREP
```

### How this proves a future PATCH worked

When PATCH 1 lands and fixes lam-al-amr in `segmenter.py`:

1. `t_walyaktub_segments_with_lam_al_amr` will **fail** (because the assertion `r.stem == "وَلْيَكْتُب"` will no longer hold — the stem will be `يَكْتُب` after the prefix peel).
2. PATCH 1's author MUST rewrite the assertion to the new expected output.
3. The rewritten test passes against the fixed code.

If PATCH 1 lands and these characterization tests **still pass without modification**, that's the signal that PATCH 1's fix didn't reach the production path. The patch must be rejected.

### Regression guards (also in the file)

Two assertions intentionally lock in **good** current behavior:

- `t_alladhina_must_remain_atomic` — Batch 6's positive effect; must not regress.
- `t_dhalikum_must_remain_atomic` — same.

These FAIL if a future patch accidentally re-breaks them.

---

## What PATCH 0 does NOT contain

- No logic change in `segmenter.py`.
- No logic change in `analyze_verse_v3.py`. (The `--json` flag from PHASE 0.5 is separate; it does not affect `segment()` behavior.)
- No new contracts, no new CSVs.
- No claim that any bug is fixed.

PATCH 0's sole effect: a test file that calls the real production function with target words, so PATCH 1 onwards has a binary fail/pass signal grounded in production behavior.

---

## Production path call chain — final summary

For PATCH 1+ authors: the call chain that produces the L1/L2 output for `--verse 2:282 --all` is exactly:

```
1. clean_code/analyze_verse_v3.py::main()                  line 401
2.   → show_all calculated                                 line 522-525
3.   → if --json: JSON branch (PHASE 0.5 addition)         line 527-589
4.   → else: human-readable path                           line 591+
5.     → show_morph(text)                                  line 605-606
6.       → from segmenter import segment                   line 67
7.       → for word in text.split():
8.         → r = segment(word)                             segmenter.py:1698
9.         → print prefixes/prefix_tags/stem/suffixes/suffix_tags
```

Edit point that changes L1/L2 output: **`clean_code/segmenter.py` line 1698 (the `segment` function) and the rules it dispatches to**.

Anything else — `verb_form_contract.py`, `non_verb_override_gate.py`, `i3rab_engine/layer1.py`, `closed_function_word_gate.py` — only affects L3 (`class=…`, `role=…`, `root=…`, `wazn=…`), not the L1 segmentation line.

---

## Acceptance checklist for PATCH 0

- [x] Identify the exact production function path. → `segmenter.segment()` at `segmenter.py:1698`.
- [x] List the exact files involved. → `analyze_verse_v3.py`, `segmenter.py` (one each; no duplicates).
- [x] Confirm whether existing tests hit production or helpers. → mostly helpers; documented.
- [x] Add ONE production-path integration test. → `test_production_path_segmentation.py` (16 tests, all passing).
- [x] No logic fix in this commit.
- [ ] Commit created.

## Commit plan

```bash
cd ~/fractal/hussein
rm -f .git/index.lock

git add docs/bugs/PATCH_0_PRODUCTION_PATH_TRACE.md
git add clean_code/test_production_path_segmentation.py

git diff --cached --stat
# Expected exactly 2 files.

git commit -m "PATCH 0: trace production path + add integration test (no logic fix)

Verifies before any code-behavior patch:
  - segmenter.segment() at clean_code/segmenter.py:1698 is the ONE
    function producing the L1/L2 output of analyze_verse_v3.py.
  - No duplicate segmenters reach production.
  - Existing helper-level tests (e.g. test_verb_form_contract.py:82)
    pass while production output is unchanged — they call
    evaluate_verb_form() which segmenter.py does not consume.

Adds clean_code/test_production_path_segmentation.py: 16 tests that
call segment() directly with target words from 2:282. Tests pass
against current buggy state — capturing the bug. Future PATCH 1+
must rewrite these assertions when production behavior changes; if
assertions still pass unchanged, the patch did not reach production.

No segmenter.py edit. No engine edit. No logic change."
```

Stop after this commit. Await explicit approval for PATCH 1 (LamAlAmrSegmentationContract — the first patch that actually edits `segmenter.py`).
