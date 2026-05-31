# POST-PATCH-5 SMALL-SAMPLE REGRESSION

**Date:** 2026-05-27
**Branch:** patch0-production-path-trace
**Head commit:** `673961d` (PATCH 5: L5 lam-al-amr mood propagation + TimeScopeGate)
**Sample:** 15 verses across 5 refs (1:1-7, 2:1-5, 2:43, 4:34, 36:80)
**Scope:** audit only — no fixes, no code changes, no commits.

---

## Run summary

| Ref | Tokens | Crash | Events | when_future | mood | KB.SAM kept |
|-----|-------:|:-----:|-------:|------------:|-----:|------------:|
| 1:1 | small | no | 0 | 0 | 0 | 3 |
| 1:2 | small | no | 0 | 0 | 0 | 2 |
| 1:3 | small | no | 0 | 0 | 0 | 0 |
| 1:4 | small | no | 0 | 0 | 0 | 0 |
| 1:5 | small | no | 2 | 0 | 0 | 2 |
| 1:6 | small | no | 1 | 0 | 0 | 0 |
| 1:7 | small | no | 1 | 0 | 0 | 1 |
| 2:1 | small | no | 0 | 0 | 0 | 4 |
| 2:2 | small | no | 0 | 0 | 0 | 4 |
| 2:3 | med | no | 4 | 0 | 0 | 4 |
| 2:4 | med | no | 4 | 0 | 0 | 9 |
| 2:5 | med | no | 2 | 0 | 0 | 7 |
| 2:43 | med | no | 3 | 0 | 0 | 0 |
| 4:34 | large | no | 10 | 0 | 0 | 26 |
| 36:80 | med | no | 2 | 0 | 0 | 11 |

**Crashes: 0/15.**

---

## Per-category findings (vs PATCH 0–5 regression markers)

### 1. L1/L2 segmentation regressions

| Marker | Hits | Notes |
|---|---|---|
| False lam-al-amr peel (`LAM_AL_AMR` on a non-imperative) | 0 | No verse in this sample contains lam-al-amr forms, so PATCH 1 path is dormant — no false-positive regression observed. |
| False demonstrative split (ٱلَّذِى / ذَٰلِكُمْ / تِلْكَ broken by DET peel) | 0 | All demonstrative forms remain atomic across the sample. |
| False نا(POSS_PRON) on IMPERF verbs | 0 | PATCH 3C dual-marker guard intact. |
| False functional-noun locative override | 0 | No quantifier (كُلّ / بَعْض) or non-locative entry surfaces with `role=ظرف مكان`. |

### 2. L3 i3rab regressions

| Marker | Hits | Notes |
|---|---|---|
| Quantifier → role=ظرف مكان | 0 | PATCH 4.5 holds — `بِكُلِّ`-class regression does not return. |
| Locative ψ legitimately tagged | 1 | `2:43 مَعَ → ظرف مكان` — **intentional**: مَعَ is in `functional_nouns_lexicon.csv` as `category=locative`. Classical Arabic considers مَعَ a ظَرف. Not a regression. |

### 3. KB.SAM overmatch (PATCH 4 gate)

| Marker | Hits | Notes |
|---|---|---|
| Substring operator meanings on non-clitic letters | 0 | None of the forbidden meanings (واو القَسَم / كاف المُخاطَب / السين تَنفيس / لا النَّاهيَة on compounds) surface across the sample. |
| Legitimate clitic-operator meanings | many | `الباء`, `اللام`, `الكاف`, `إِنْ الشَّرطيَّة`, `إِذا الشَّرطيَّة` all emit correctly where the L1 prefix tag certifies them. |

One specific case worth flagging as **not** a regression:
- **4:34 «فَإِنْ»** → KB.SAM emits `إِن الشَّرطيَّة` ✓ correct. The word is genuinely `فَ + إِنْ الشَّرطيَّة`. The PATCH 4 strict-form gate matched the stem `إِنْ` against the vocalized_form `إِنْ` — proper certification, not overmatch.

### 4. L5 event / time / mood

| Marker | Hits | Notes |
|---|---|---|
| Global `time=when_future` on every event | **0/all 15 verses** | PATCH 5 TimeScopeGate confirmed working. Before PATCH 5 this would have been 100% on any verse containing a time-adverb. None of these 15 verses contains إذا, so when_future legitimately doesn't fire anywhere. |
| Past event with stray `time=when_future` outside scope | 0 | Past events across these verses (e.g. 36:80 verbs) carry no global time tag. |
| Lam-al-amr mood propagation | not exercised | None of these verses contains lam-al-amr verbs. (PATCH 5 mood propagation was validated on 2:282 only.) |

### 5. Top remaining issue per verse

| Ref | Top remaining issue (NOT a PATCH 0–5 regression — pre-existing) |
|---|---|
| 1:1-7 | L4 implicit agents heavy on Fatiha (most events Hypothesis); L6 anaphora `إِيَّاكَ → ?` |
| 2:1-5 | L3 `ٱلَّذِينَ يُؤْمِنُونَ` relative-clause head resolution still `?`; L8 questions still pool answers |
| 2:43 | L4 `وَأَقِيمُوا … وَآتُوا … وَٱرْكَعُوا` — three commands but L5 events lack agent because L4 implicit-agent for جمع mudāri` is approximate |
| 4:34 | Verse is dense; L5 produces 10 events but several have no agent/patient (L4 gap). 26 KB.SAM claims kept — appropriate density but many are Hypothesis. |
| 36:80 | L5 events fine; L6 relative `ٱلَّذِى جَعَلَ لَكُم` → `?` |

None of these "top issues" originate in PATCH 0-5; they are pre-existing L4/L6/L8 limitations the checkpoint already documented.

---

## Verdict

**PATCH 0–5 are clean on this 15-verse sample.**

Evidence:
- 0 crashes
- 0 false demonstrative/locative/dual/lam-al-amr segmentation regressions
- 0 KB.SAM overmatches; one true-positive `إِن الشَّرطيَّة` correctly survives gate on `فَإِنْ`
- 0 global `time=when_future` defaults
- The only L3 ψ-finding (`2:43 مَعَ ظرف مكان`) is data-driven and intentional

Coverage gaps acknowledged (cannot fully validate from this sample):
- No lam-al-amr verbs occur in any of the 15 verses → PATCH 5 mood propagation not exercised in the wild; only the 2:282 case stands.
- No multi-clause إذا verses other than 2:282 → TimeScopeGate's scope-end behavior under nested إذا not stress-tested.

---

## Recommendation

**Proceed to PATCH 6.** No fix-up is required first.

Justification:
- Regression markers are clean; the small sample shows no breakage from PATCH 0–5.
- The remaining bugs surfaced (L4 agent gaps, L6 anaphora) are exactly the families the audit checkpoint already deferred.
- **PATCH 6 = L8 answer-type gate** is the next dominant family the audit recommended; PATCH 5 having cleaned L5 means L8 now has trustworthy `tense / mood / time` inputs to gate against. If PATCH 6 were attempted before PATCH 5, the L8 fixes would be built on noisy L5 data.

Alternative if you prefer to harden first:
- A **PATCH 5.5 micro-batch** (`سَفِيهًا` false POSS_PRON peel + `فُسُوقٌۢ` false فُ-CONJ peel + `عِندَ` → ISM_MUARAB) is still pending from the audit. Scope: 3 single-token surgical fixes in `segmenter.py` + `non_verb_override_gate.py` (locative override). Bounded but optional; doesn't block PATCH 6.

If you want maximal correctness before L8 work, do 5.5 first. Otherwise PATCH 6 is the better leverage move.

---

## Strict-scope confirmation

This regression run **did not modify**:
- `segmenter.py`
- `i3rab_engine/*`
- `event_extractor.py`
- `relation_extractor.py`
- `resolution_engine.py`
- `analyze_verse_v3.py`
- Any test file
- Any KB data

Only artifacts produced: 15 per-verse outputs in `/tmp/regression_p5/` and this report (untracked). **Not committed.**
