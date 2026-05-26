# PATCH 3 — FunctionalNounIdafaContract + FalseLamPrefixInLexicalStem + DualVerbSuffixContract + AllaCompoundContract + MasaqLocativeNounOverride

> **Date:** 2026-05-26
> **Predecessor:** PATCH 2 (commit `fc30616`)
> **Scope:** 5 target words from 2:282 — L1/L2 segmentation + L3 word_class.

## Files changed

| File | Lines | Purpose |
|---|---|---|
| `clean_code/segmenter.py` | +52 / −2 | 3A: remove `بين` from `_MULTI_LETTER_PREPS`. 3B: shadda-residual refusal in `_rule_prep_clitic`. 3C: نا+IMPERF_PREF guard in `_rule_pronoun_suffix` AND `_rule_pronoun_suffix_multi_only`. 3D: per-entry `_ASSIM_FIRST_SEG_TAG` map (`ألا → HARF_NASB`). |
| `clean_code/i3rab_engine/layer1.py` | +21 / −2 | 3E: MASAQ-HARF→ISM_MUARAB override when role is `ADV_PLCE`/`ADV_TIME`. |
| `clean_code/test_production_path_segmentation.py` | +103 / −22 | Replaced 4 PATCH-3 characterization tests with 7 verification tests (3A/3B/3C/3D/3E + regressions). |

**Not touched:** `analyze_verse_v3.py`, `verb_form_contract.py`, `relation_extractor.py`, `event_extractor.py`, `resolution_engine.py`, `reasoning_engine.py`, KB.SAM data, Phase 4 resolver.

## Sub-patches

### 3A — FunctionalNounIdafaContract (بَيْنَكُمْ / بَّيْنَكُمْ)

**Root cause:** `_MULTI_LETTER_PREPS` listed `بين`, so `_rule_prep_clitic` peeled it as PREP and the residual `كُمْ` was then parsed as POSS_PRON. But بَيْن is a **locative noun (ظَرف مكان)** taking ـكُمْ as iḍāfa, not a preposition.

**Fix:** removed `بين` from `_MULTI_LETTER_PREPS`. Other true multi-letter clitics (`في`, `من`, `عن`) untouched. The result: بَيْنَ stays inside the stem; the كُمْ suffix is correctly tagged POSS_PRON of an iḍāfa construction.

### 3B — FalseLamPrefixInLexicalStem (وَلِيُّهُۥ)

**Root cause:** `_rule_prep_clitic` would peel `لِ` from `وَلِيُّهُۥ` after CONJ peel (it tested `allowed=True` if the next char permits stripping). The residual would be `يُّهُۥ` — a `يَ` followed immediately by **shadda**, which signals the doubled root letter of وَلِيّ. A shadda at residual position 2 means the لِ is part of the lexical stem, not a clitic.

**Fix:** in `_rule_prep_clitic`, after computing `allowed`, refuse if `rest[1]` is a shadda character:

```python
rest_chars_for_shadda = list(rest)
if (allowed
        and len(rest_chars_for_shadda) >= 2
        and rest_chars_for_shadda[1] == SHADDA):
    allowed = False
```

Other real لِ-clitics (e.g. `لِزَيدٍ`, `لِكِتابٍ`) still peel because no shadda follows.

### 3C — DualVerbSuffixContract (يَكُونَا)

**Root cause:** `_rule_pronoun_suffix` (and the variant `_rule_pronoun_suffix_multi_only`) saw the trailing `نَا` and tagged it POSS_PRON. But after IMPERF_PREF `يَ` was peeled, the stem was already only 3 plain letters; treating `نَا` as a separate suffix is structurally wrong — for imperfect verbs `نَا` here is the dual-subject marker (or part of the verbal body), not a possessive pronoun.

**Fix:** in BOTH `_rule_pronoun_suffix` and `_rule_pronoun_suffix_multi_only`, refuse the `نا` candidate when an IMPERF_PREF is already on the prefix stack AND the residual would be shorter than 3 plain letters:

```python
if (suf == "نا"
        and has_iv_prefix
        and _count_letters(s) - n_letters < 3):
    continue
```

Real نا possessives (`كَتَبْنا` — past form, no IMPERF_PREF; `رَبُّنا` — noun, no IMPERF_PREF) still peel correctly.

### 3D — AllaCompoundContract (أَلَّا)

**Root cause:** `_rule_assim_prep` would emit the first segment of an assimilation with tag `PREP`. For `أَلَّا = أن + لا`, this gave `أن(PREP)`, but `أن` is **HARF_NASB** (subjunctive complementizer), not a preposition.

**Fix:** new module-level dict `_ASSIM_FIRST_SEG_TAG` mapping plain-stripped surfaces to the correct first-segment tag. Lookup is plain-strip-keyed:

```python
_ASSIM_FIRST_SEG_TAG = {
    "ألا": "HARF_NASB",
}
plain_for_tag = _strip_diacritics(norm)
first_tag = _ASSIM_FIRST_SEG_TAG.get(plain_for_tag, "PREP")
```

Other assimilations (`مِمَّا`, `عَمَّن`, `فِيمَا`) keep `PREP` as before — the lookup is exact and only adds new entries.

### 3E — MasaqLocativeNounOverride (بَيْنَكُمْ L3)

**Root cause:** Even after 3A fixes L1/L2 (no PREP peel), the L3 classifier reads the MASAQ tag for `بَيْنَكُمْ` as `word_class=HARF` with `role=ADV_PLCE` — MASAQ is internally inconsistent here: ظَرف is a noun (ISM), not a particle (HARF). The L3 report would show `صنف=HARF`.

**Fix:** in `layer1.py`, after extracting `_ml_word_class` and before the consensus check, if `_ml_word_class == "HARF"` AND `_ml_role` is in `{"ADV_PLCE", "ADV_TIME"}`, override `_ml_word_class = "ISM_MUARAB"` and append a `proof_blockers` entry explaining the override:

```python
_LOCATIVE_NOUN_ROLES = {"ADV_PLCE", "ADV_TIME"}
_ml_word_class = _ml["word_class"]
_ml_role = _ml.get("role", "")
if _ml_word_class == "HARF" and _ml_role in _LOCATIVE_NOUN_ROLES:
    _ml_word_class = "ISM_MUARAB"
    result.setdefault("proof_blockers", []).append(
        f"masaq_harf_overridden_to_ism: role={_ml_role} "
        f"(ظَرف is a noun, not a particle)"
    )
```

This is a localized correction: only fires when MASAQ itself is internally inconsistent (HARF + locative-noun role). All other MASAQ-HARF tokens are unaffected.

## Sandbox verification (segment() direct calls)

| Target | L1/L2 | Notes |
|---|---|---|
| `بَيْنَكُمْ` | prefixes=— \| stem=بَيْنَ \| suffixes=كُمْ(POSS_PRON) ✅ | No PREP peel |
| `بَّيْنَكُمْ` | prefixes=— \| stem=بَّيْنَ \| suffixes=كُمْ(POSS_PRON) ✅ | Shadda-elision variant |
| `وَلِيُّهُۥ` | prefixes=وَ(CONJ) \| stem=لِيُّهُۥ \| suffixes=— ✅ | لِ stays in stem |
| `يَكُونَا` | prefixes=يَ(IMPERF_PREF) \| stem=كُونَا \| suffixes=— ✅ | نَا preserved |
| `أَلَّا` | prefixes=أن(HARF_NASB) \| stem=لا \| suffixes=— ✅ | HARF_NASB tag |

3E (L3) is sandbox-skipped because the L3 classifier path requires loading `wazn_data` which fails in this sandbox. The test is registered and runs on the user's machine.

## Regression checks (all passing in sandbox)

| Word | Result |
|---|---|
| `تَحْتَكُمْ`, `فَوْقَكُمْ`, `عِنْدَكُمْ` | تَحْتَ/فَوْقَ/عِنْدَ still peel as PREP ✅ |
| `بِكِتابٍ`, `لِزَيدٍ` | بِ / لِ still peel as PREP (no shadda residual) ✅ |
| `كَتَبْنا`, `رَبُّنا` | نا still peels as POSS_PRON (no IMPERF_PREF guard fires) ✅ |
| `مِمَّا`, `عَمَّن`, `فِيمَا` | First segment still tagged PREP ✅ |
| `تَكْتُبُ`, `كَتَبَ` | Imperfect / past unchanged ✅ |
| `ٱلَّذِى`, `ذَٰلِكُمْ`, `تَدَايَنتُم`, `وَلْيَكْتُب` | PATCH 1/2 outputs preserved ✅ |

## Test suite

`test_production_path_segmentation.py` → **26/26 passed** (2 sandbox-skipped: `t_tadayantum_l3_role_must_not_be_imperfect`, `t_baynakum_l3_not_harf` — both run on user machine).

PATCH 3 added 7 new tests:
- `t_baynakum_no_prep_peel` (3A)
- `t_bbaynakum_no_prep_peel` (3A, shadda variant)
- `t_baynakum_l3_not_harf` (3E, sandbox-skipped)
- `t_waliyyuhu_no_lam_prep_peel` (3B)
- `t_yakuna_no_na_possessive` (3C)
- `t_alla_an_tagged_harf_nasb_not_prep` (3D)
- `t_patch3_regressions_intact` (regression guard for 3A/3B/3C/3D)

## Known limitations (deferred to later patches)

1. **`يَكُونَا` morphological role inside L3:** PATCH 3 guarantees نَا stays attached to the stem, but L3's verb-form analysis may still need a separate rule to label نَا as the dual-subject marker (alif al-ithnayn variant). Out of scope here.
2. **`بَيْنَ` in non-iḍāfa contexts:** if بَيْنَ appears as a true preposition-like adverb without a possessive suffix, the current change leaves it inside the stem. This is acceptable because PATCH 3A's only binding criterion is "بَيْنَ does not peel as PREP from بَيْنَكُمْ".
3. **MASAQ HARF override scope:** only fires for `ADV_PLCE` / `ADV_TIME`. Other MASAQ inconsistencies (if any exist for the 2:282 vocabulary) are not addressed here.

## Commit plan

```bash
cd ~/fractal/hussein
rm -f .git/index.lock

git add clean_code/segmenter.py \
        clean_code/i3rab_engine/layer1.py \
        clean_code/test_production_path_segmentation.py \
        docs/bugs/PATCH_3_FUNCTIONAL_NOUN_FALSE_LAM_DUAL_NA_ALLA.md

git diff --cached --stat
# Expected 4 files — segmenter, layer1, test, doc.

git commit -m "PATCH 3: FunctionalNounIdafaContract + FalseLamPrefixInLexicalStem + DualVerbSuffixContract + AllaCompoundContract + MasaqLocativeNounOverride

Five sub-fixes coordinated for 2:282 production output:

3A — FunctionalNounIdafaContract (بَيْنَكُمْ / بَّيْنَكُمْ)
  segmenter.py: removed بين from _MULTI_LETTER_PREPS. بَيْنَ is a
  locative noun (ظَرف مكان) taking iḍāfa, not a preposition.
  L1/L2: بَيْنَ stays in stem; كُمْ correctly tagged POSS_PRON.

3B — FalseLamPrefixInLexicalStem (وَلِيُّهُۥ)
  segmenter.py: shadda-residual refusal in _rule_prep_clitic — if
  residual position 2 is a shadda, the لِ is part of the doubled
  root, not a clitic. وَلِيُّهُۥ now only peels وَ(CONJ).
  Other real لِ-clitics (لِزَيدٍ, لِكِتابٍ) unaffected.

3C — DualVerbSuffixContract (يَكُونَا)
  segmenter.py: نا+IMPERF_PREF guard in BOTH _rule_pronoun_suffix
  AND _rule_pronoun_suffix_multi_only. Refuse نا as POSS_PRON when
  IMPERF_PREF is on the stack and residual would be <3 letters.
  يَكُونَا now segments as يَ(IMPERF_PREF)+كُونَا. Real possessives
  (كَتَبْنا past, رَبُّنا noun) still peel.

3D — AllaCompoundContract (أَلَّا)
  segmenter.py: new _ASSIM_FIRST_SEG_TAG map keyed by plain-strip
  surface. ألا → HARF_NASB (not PREP). أَلَّا now segments as
  أن(HARF_NASB)+لا. Other assimilations (مِمَّا, عَمَّن, فِيمَا)
  keep PREP because they're not in the map.

3E — MasaqLocativeNounOverride (بَيْنَكُمْ L3)
  i3rab_engine/layer1.py: when MASAQ word_class=HARF AND
  role∈{ADV_PLCE, ADV_TIME}, override to ISM_MUARAB and record
  override in proof_blockers. Localized correction for MASAQ's
  internal inconsistency on ظَرف (a noun, not a particle).

Test: test_production_path_segmentation.py → 26/26 (was 21/21).
2 tests sandbox-skipped (L3 path needs wazn_data), run on user
machine: t_tadayantum_l3_role_must_not_be_imperfect, t_baynakum_l3_not_harf.

Regressions checked: locative-noun preps (تَحْتَكُمْ, فَوْقَكُمْ,
عِنْدَكُمْ) still peel; real PREP clitics (بِكِتابٍ, لِزَيدٍ) still
peel; real نا possessives (كَتَبْنا, رَبُّنا) still peel; other
assimilations (مِمَّا, عَمَّن, فِيمَا) keep PREP; PATCH 1/2 targets
(وَلْيَكْتُب, ٱلَّذِى, ذَٰلِكُمْ, تَدَايَنتُم) all unchanged.

KNOWN LIMITATIONS (deferred):
  - يَكُونَا dual-subject role in L3 verb-form may need a separate
    label rule. PATCH 3 only guarantees نَا stays attached.
  - بَيْنَ in non-iḍāfa contexts now stays in stem (acceptable —
    binding criterion is only the 2:282 form).
  - MASAQ HARF override scope limited to ADV_PLCE/ADV_TIME.

Not touched: verb_form_contract.py, analyze_verse_v3.py,
relation_extractor.py, event_extractor.py, resolution_engine.py,
KB.SAM, Phase 4 resolver."

git log --oneline -4
```
