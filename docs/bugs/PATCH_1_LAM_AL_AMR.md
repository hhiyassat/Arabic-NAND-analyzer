# PATCH 1 — LamAlAmrSegmentationContract

> **Date:** 2026-05-26
> **Predecessor:** PATCH 0 (commit `931824e`, branch `patch0-production-path-trace`)
> **Scope:** L1/L2 segmentation only. 5 target words from 2:282.
> **Verification:** real `analyze_verse_v3.py --verse 2:282 --all` output, before/after lines confirmed by user.

## 1. What changed (files only)

| File | Lines | Purpose |
|---|---|---|
| `clean_code/segmenter.py` | +83 / −2 | New `_rule_lam_al_amr` + surgical exception to `_rule_conjunction`'s sukun-refusal + add `LAM_AL_AMR` to `_rule_iv_prefix` refuse-set + register in `_PREFIX_RULES` after `conjunction`. |
| `clean_code/test_production_path_segmentation.py` | +101 / −32 | Rewrite 5 lam-al-amr assertions to new expected output (CONJ+LAM_AL_AMR+stem). Add 2 regression-guard tests (ordinary lam words; noun-CONJ pairs). |

**Not touched:** `analyze_verse_v3.py`, `i3rab_engine/*`, `relation_extractor.py`, `event_extractor.py`, `resolution_engine.py`, `reasoning_engine.py`, `samarrai_analyzer.py`, KB.SAM data, Phase 4 resolver.

## 2. Production-path verification — the 5 target words

From real `analyze_verse_v3.py --verse 2:282 --all` output, confirmed by user:

| token | BEFORE | AFTER |
|---|---|---|
| `وَلْيَكْتُب` | `prefixes=— ǀ stem=وَلْيَكْتُب` | `prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) ǀ stem=يَكْتُب` |
| `فَلْيَكْتُبْ` | `prefixes=— ǀ stem=فَلْيَكْتُبْ` | `prefixes=فَ(CONJ)+لْ(LAM_AL_AMR) ǀ stem=يَكْتُبْ` |
| `وَلْيُمْلِلِ` | `prefixes=— ǀ stem=وَلْيُمْلِلِ` | `prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) ǀ stem=يُمْلِلِ` |
| `فَلْيُمْلِلْ` | `prefixes=— ǀ stem=فَلْيُمْلِلْ` | `prefixes=فَ(CONJ)+لْ(LAM_AL_AMR) ǀ stem=يُمْلِلْ` |
| `وَلْيَتَّقِ` | `prefixes=— ǀ stem=وَلْيَتَّقِ` | `prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) ǀ stem=يَتَّقِ` |

All 5 produce 2 prefixes + verb stem. None remain whole-stem.

## 3. Test results

`python3 clean_code/test_production_path_segmentation.py` → **17/18 passed**.

The 1 failure is `t_dhalikum_must_remain_atomic` — a pre-existing regression captured by PATCH 0's guard. Out of scope for PATCH 1. PATCH 2 will fix it under DemonstrativeCompoundsAtomicContract.

## 4. Known gaps left for later patches

PATCH 1 ONLY fixes L1/L2 segmentation. Downstream layers still show stale output for these tokens:

| Layer | Current output | Correct output | Patch |
|---|---|---|---|
| L3 role | `فعل مضارع` | `فعل أمر / فعل مضارع مجزوم` | `LamAlAmrMorphologyPropagation` (future) |
| L5 tense | `tense=present` | `tense=command` or `mood=jussive` | `CommandLamEventMood` (future) |

These are explicitly **out of scope** for PATCH 1 per the user's acceptance criteria.

## 5. Linguistic scope (strict)

PATCH 1 handles **only**:
- `وَ` / `فَ` (CONJ) **+** `لْ` (lam-al-amr with sukun) **+** imperfect-prefix letter (ي/ت/ن/أ) **+** verb stem.

Out of scope for this patch:
- Kasra-form lam-al-amr (`لِيَكْتُبْ`) — same construction with kasra on lam.
- Bare `لْ + IV` without CONJ — not in 2:282; will be covered if found.
- `لـ` as preposition (e.g. `لِزَيدٍ`) — already correctly handled by `_rule_prep_clitic`.
- Emphatic lam (`لَ + verb`) — already handled by `_rule_emphatic_lam`.

## 6. Regression guards (in the test file)

`t_lam_al_amr_does_not_fire_for_ordinary_lam_words` — verified that all of these do NOT trigger the new rule:
- `لَيلًا`, `لِسانٌ`, `لَا`, `وَلَا`, `لَنْ`, `لَهُمْ`.

`t_lam_al_amr_conjunction_exception_does_not_break_nouns` — verified that the surgical CONJ exception did NOT regress these:
- `وَقُود`, `فَوْق`, `وَقْت` (all remain atomic — CONJ correctly refused).

## 7. Commit plan

```bash
cd ~/fractal/hussein
rm -f .git/index.lock

git add clean_code/segmenter.py clean_code/test_production_path_segmentation.py
git add docs/bugs/PATCH_1_LAM_AL_AMR.md   # this file (optional)

git diff --cached --stat
# Expected 2 or 3 files; nothing under i3rab_engine/, relation_extractor.py, etc.

git commit -m "PATCH 1: LamAlAmrSegmentationContract — production-path fix for لْ+IV

5 target words from Quran 2:282 verified before/after in real
analyze_verse_v3.py output:
  وَلْيَكْتُب → وَ(CONJ)+لْ(LAM_AL_AMR)+stem=يَكْتُب
  فَلْيَكْتُبْ → فَ(CONJ)+لْ(LAM_AL_AMR)+stem=يَكْتُبْ
  وَلْيُمْلِلِ → وَ(CONJ)+لْ(LAM_AL_AMR)+stem=يُمْلِلِ
  فَلْيُمْلِلْ → فَ(CONJ)+لْ(LAM_AL_AMR)+stem=يُمْلِلْ
  وَلْيَتَّقِ  → وَ(CONJ)+لْ(LAM_AL_AMR)+stem=يَتَّقِ

Three local changes in segmenter.py:
  1. NEW _rule_lam_al_amr — strips لْ when followed by IV-prefix letter.
  2. _rule_conjunction — surgical 6-line exception so the sukun-on-2nd-char
     refusal does NOT block لْ+IV pattern. Counter-examples (فَوْق,
     وَقُود, وَقْت) remain refused (verified by regression test).
  3. _rule_iv_prefix — adds LAM_AL_AMR to refuse-set so the verb's يَ
     stays attached to stem after lam-al-amr peel.

Test: test_production_path_segmentation.py → 17/18 passed.
The 1 failure (t_dhalikum_must_remain_atomic) is a pre-existing
regression captured by PATCH 0's guard; deferred to PATCH 2.

KNOWN GAPS (deferred to future patches per scope):
  - L3 still says role=فعل مضارع for these tokens
    → LamAlAmrMorphologyPropagation (future patch)
  - L5 still says tense=present
    → CommandLamEventMood (future patch)

Not touched: analyze_verse_v3.py, i3rab_engine/*, relation_extractor.py,
event_extractor.py, resolution_engine.py, KB.SAM, Phase 4 resolver."

git log --oneline -3
```
