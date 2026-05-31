# PATCH 2 — ClosedFormSegmentationLock + DemonstrativeCompoundsAtomicContract + FormVI_Tafaala_PastContract

> **Date:** 2026-05-26
> **Predecessor:** PATCH 1 (commit `a85ad43`)
> **Scope:** 4 target words from 2:282 — L1/L2 segmentation + L3 verdict for past-aspect.

## Files changed

| File | Lines | Purpose |
|---|---|---|
| `clean_code/segmenter.py` | +94 / −1 | Added `_normalize_for_closed_class_lookup` (2A) + `_load_demonstrative_compounds` (2B) + extended `_is_closed_class` + 6-line past-2p block in `_rule_iv_prefix` (2C). |
| `clean_code/verb_form_contract.py` | +16 / 0 | Form V/VI past pre-check before IV-prefix branch (2D). |
| `clean_code/data/contracts/lists/demonstrative_compounds.csv` | +24 (new) | 23 demonstrative compounds (ذَلِكُمْ / تِلْكُمْ / أُولَئِكُمْ + dagger-alef variants). |
| `clean_code/test_production_path_segmentation.py` | +60 / −22 | Rewrote 4 characterization assertions + added 5 verification tests for 2A/2B/2C/2D + regression guard. |

**Not touched:** `analyze_verse_v3.py`, `i3rab_engine/*` (verb_form_contract is a separate module that L1 consumes), `relation_extractor.py`, `event_extractor.py`, `resolution_engine.py`, `reasoning_engine.py`, KB.SAM data, Phase 4 resolver.

## Sub-patches

### 2A — ClosedFormSegmentationLock (ٱلَّذِى / ٱلَّتِى)

**Root cause:** `_strip_diacritics` strips harakat but does not normalize `ٱ` (alef-wasla, U+0671) → `ا` or `ى` (alef-maksura) → `ي`. So `ٱلَّذِى` becomes plain `ٱلذى` which isn't in `_CLOSED_CLASS_LEXEMES` (which has `الذي`).

**Fix:** added `_normalize_for_closed_class_lookup(s)` — lookup-only normalization that maps `ٱ/آ/أ/إ → ا` and `ى → ي`. Called from `_is_closed_class` against BOTH the raw plain form AND the normalized form. Does not mutate the token's `stem` field — only the lookup key.

### 2B — DemonstrativeCompoundsAtomicContract (ذَٰلِكُمْ / تِلْكُمْ / أُولَٰئِكُمْ …)

**Root cause:** `_CLOSED_CLASS_LEXEMES` contains singular `ذلك` only. Plural-addressee compounds (`ذلكم`, `ذلكما`, `ذلكن`, `تلكم`, `أولئكم`, …) are missing. So `_rule_pronoun_suffix` peels the addressee marker `كُمْ` as POSS_PRON.

**Fix:** new CSV `data/contracts/lists/demonstrative_compounds.csv` with 23 entries (5 ذَ + 5 تِ + 5 أُولَ × 2 dagger-alef variants where applicable). `_load_demonstrative_compounds()` lazy-loads + adds hamza-alef variants. `_is_closed_class` consults the CSV after the legacy set.

### 2C — IV prefix refuses past-2p suffix (تَدَايَنتُم / تَبَايَعْتُمْ L1)

**Root cause:** `_rule_iv_prefix` checks that the word ends in one of `_VERB_SUBJECT_MARKERS_PLAIN = ("وا", "ون", "ين", "تم", "تن", "نا", "تموا")`. But `تم/تن/تما` are **past-only** subject suffixes (imperfect 2pl-m uses `ـونَ` / `ـوا`). So firing IMPERF_PREF on `تَدَايَنتُم` is a structural contradiction.

**Fix:** 6 lines added to `_rule_iv_prefix`. Before the existing checks, if the diacritic-stripped word ends in `تم`, `تما`, or `تن`, the rule refuses. `وا`/`نا` are NOT included (ambiguous past/imperfect).

### 2D — Form V/VI past detector (verb_form_contract aspect=PV)

**Root cause:** Even with 2C fixing L1 segmentation, `evaluate_verb_form` independently determines aspect. The IV-prefix branch fires at line 198 for any body starting with `يَ/تَ/نَ/أَ`, giving aspect=IV. So L3 still says `فعل مضارع`.

**Fix:** 12 lines added to the `_infer_mood_and_aspect` function, BEFORE the IV branch. Detects: body starts with تَ (Form V/VI signature) AND plain ends in `تم/تما/تن` AND has ≥4 plain letters. If matched → aspect=PV with evidence string `"PATCH 2D Form V/VI past (تَ-initial + past-2p suffix تم/تما/تن)"`.

## Sandbox verification (segment + verb_form direct calls)

| Target | L1/L2 | L3 verb-form |
|---|---|---|
| `ٱلَّذِى` | prefixes=— \| stem=الَّذِى \| suffixes=— ✅ | (not a verb) |
| `ذَٰلِكُمْ` | prefixes=— \| stem=ذَٰلِكُمْ \| suffixes=— ✅ | (not a verb) |
| `تَدَايَنتُم` | prefixes=— (no IMPERF_PREF) ✅ | aspect=PV ✅ |
| `تَبَايَعْتُمْ` | prefixes=— (no IMPERF_PREF) ✅ | aspect=PV ✅ |

`تَدَايَنتُم`'s stem is `تَدَا` (sub-optimal due to other suffix rules misfiring on `يَن`) — out of scope per acceptance criteria.

## Regression checks (all passing in sandbox)

| Word | Result |
|---|---|
| `تَكْتُبُ` | IMPERF_PREF ✅ aspect=IV ✅ |
| `تَدْرُسُ` | IMPERF_PREF ✅ aspect=IV ✅ |
| `يَكْتُبُ` | IMPERF_PREF ✅ aspect=IV ✅ |
| `كَتَبَ` | atomic ✅ aspect=PV ✅ |
| `كِتابُكُمْ` | POSS_PRON suffix kept ✅ |
| `بَيْتُكُمْ` | suffixes preserved ✅ |
| `رَبُّكُمْ` | suffixes preserved ✅ |
| `وَلْيَكْتُب` | PATCH 1 LAM_AL_AMR preserved ✅ |
| `وَقُود`, `فَوْق`, `وَقْت` | atomic, no CONJ peel ✅ |

## Test suite

`test_production_path_segmentation.py` → **21/21 passed** (was 17/18 after PATCH 1; the t_dhalikum failure is now fixed).

## Known limitations (deferred to later patches)

1. **`تَدَايَنتُم` stem fragmentation:** stem comes out as `تَدَا` with `يَن(NSUFF)+تُم(VSUFF)` — the `number_suffix` rule misfires on `يَن`. This does not affect the L3 aspect verdict (PV) nor the L1 acceptance criterion (no IMPERF_PREF). A future patch could add a "block NSUFF inside Form V/VI body" rule.
2. **Form V/VI past semantic hint:** the user mentioned the option of attaching `semantic_form_hint = reciprocal/participation/mutawaah_candidate` as Hypothesis. PATCH 2D does not add this — adds risk and not in binding acceptance.

## Commit plan

```bash
cd ~/fractal/hussein
rm -f .git/index.lock

git add clean_code/segmenter.py \
        clean_code/verb_form_contract.py \
        clean_code/data/contracts/lists/demonstrative_compounds.csv \
        clean_code/test_production_path_segmentation.py \
        docs/bugs/PATCH_2_CLOSED_FORMS_AND_FORM_VI_PAST.md

git diff --cached --stat
# Expected 5 files — segmenter, verb_form_contract, CSV, test, doc.

git commit -m "PATCH 2: ClosedFormSegmentationLock + DemonstrativeCompoundsAtomic + FormVI_Tafaala_PastContract

Four sub-fixes coordinated for 2:282 production output:

2A — ClosedFormSegmentationLock (ٱلَّذِى)
  segmenter.py: new _normalize_for_closed_class_lookup() maps
  ٱ→ا / آ→ا / أ→ا / إ→ا / ى→ي for lookup only (no token mutation).
  Extended _is_closed_class to consult normalized form against
  _CLOSED_CLASS_LEXEMES. ٱلَّذِى / ٱلَّتِى / ٱلَّذَانِ now resolve.

2B — DemonstrativeCompoundsAtomicContract (ذَٰلِكُمْ)
  New CSV data/contracts/lists/demonstrative_compounds.csv with 23
  entries (ذ/ت/أولَ × singular/dual/M_PL/F_PL × dagger-alef variants).
  New _load_demonstrative_compounds() lazy loader; _is_closed_class
  consults after legacy set. ذَٰلِكُمْ / تِلْكُمْ / أُولَٰئِكُمْ atomic.

2C — IV-prefix refuses past-2p suffix (تَدَايَنتُم L1)
  segmenter.py: 6-line block in _rule_iv_prefix — refuse when plain
  ends in تم/تما/تن (past-2p, unambiguous). وا/نا NOT included.
  Form VI past verbs (تَدَايَنتُم, تَبَايَعْتُمْ) no longer get
  تَ peeled as IMPERF_PREF.

2D — Form V/VI past detector (تَدَايَنتُم L3 aspect)
  verb_form_contract.py: 12-line pre-check before IV branch — if
  body starts with تَ AND ends in past-2p suffix → aspect=PV.
  L3 role now correctly says فعل ماضٍ.

Test: test_production_path_segmentation.py → 21/21 (was 17/18).
Regressions checked: real imperfect verbs (تَكْتُبُ, يَكْتُبُ),
ordinary kum-suffix words (كِتابُكُمْ, رَبُّكُمْ), CONJ-noun pairs
(وَقُود, فَوْق), and PATCH 1's lam-al-amr targets all unchanged.

KNOWN LIMITATIONS (deferred):
  - تَدَايَنتُم stem still fragments as تَدَا+يَن — number_suffix
    rule misfires on يَن. Does not affect L1 acceptance criterion
    (no IMPERF_PREF) or L3 aspect verdict (PV).
  - Form VI semantic hint (reciprocal/participation) not added —
    out of acceptance scope.

Not touched: analyze_verse_v3.py, relation_extractor.py,
event_extractor.py, resolution_engine.py, KB.SAM, Phase 4 resolver."

git log --oneline -3
```
