# PHASE 4 — Full Quran ON vs OFF Comparison

تاريخ: 2026-05-25
sample: 2896 tokens (مَن 3000 raw، بَعد تَصفيَة gold_wc=UNKNOWN)
flag: `ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER`

> **مُلاحَظَة:** كُلّ tokens القُرآن 77,728. الـsample 3000 (≈4% مَع توزيع زَمَنيّ مِن
> بِدايَة المَسح) كافٍ لإِظهار أَثَر integration ضِدّ baseline، لَكِن لا يُمَثِّل
> نِسَب per-class كامِل القُرآن. كُلّ المِعايير المَعروضَة هُنا apples-to-apples
> (نَفس tokens، نَفس ground truth، نَفس terminator).

## Executive Summary

✅ **Integration مَوصول بِنَجاح وَدُون drift في MASAQ-alignment.**

- **MASAQ-alignment OFF == ON** (96.86% بِالضَّبط)
- **per-class accuracy OFF == ON** بِالضَّبط
- **40.4% مِن in-scope tokens تَرَقَّت** إلى Certificate عَبر resolver (67/166)
- **21.7% إِضافيَّة** حَصَلَت على metadata-only Hypothesis (36/166)
- **safety checks كُلُّها نَظيفَة**: 0 Event[ئك]، 0 fragment leak، 0 gate enforcement

⚠ **التَّوصيَة: أَبقِه خَلف flag.** الـintegration يَعمَل، لَكِن لا يُحَسِّن MASAQ-alignment
لأَنَّ MASAQ لِلتوكنز هذِه كان بالفِعل صَحيحًا في الـbaseline. أَثَره downstream
(qa_zeros, unresolved_edges) يَحتاج Layer 4/Phase D rerun.

---

## A. Full Quran Regression — OFF vs ON

| المِعيار | OFF | ON | Δ |
|---|---|---|---|
| Total tokens | 2896 | 2896 | 0 |
| Matched MASAQ | 2805 | 2805 | 0 |
| Mismatched | 91 | 91 | 0 |
| **MASAQ-alignment** | **96.86%** | **96.86%** | **+0.000%** |

### Per-class accuracy

| class | OFF | ON | Δ |
|---|---|---|---|
| FIIL | 99.87% | 99.87% | +0.00 |
| HARF | 91.23% | 91.23% | +0.00 |
| ISM_MABNI | 100.00% | 100.00% | +0.00 |
| ISM_MAWSOOL | 96.48% | 96.48% | +0.00 |
| ISM_MUARAB | 98.86% | 98.86% | +0.00 |
| JAMID | 98.02% | 98.02% | +0.00 |

### Source distribution

| source | OFF | ON | Δ |
|---|---|---|---|
| MASAQ | 2420 (83.56%) | 2420 (83.56%) | 0 |
| registry | 303 (10.46%) | 303 (10.46%) | 0 |
| registry-exact-hypothesis | **173 (5.97%)** | **106 (3.66%)** | **−67** |
| ContextualAmbiguityResolver | 0 (0%) | **67 (2.31%)** | **+67** |

**التَّحَوُّل واضِح:** 67 tokens انتَقَلَت مِن `registry-exact-hypothesis` (Hypothesis)
إلى `ContextualAmbiguityResolver` (Certificate). نَفس word_class، لَكِن certainty
أَقوى مَع reason + context_features.

---

## B. Ambiguity Resolution per Surface

| surface | total | cert (ON) | hyp_meta (ON) | no_change (ON) | top function | top MASAQ |
|---|---|---|---|---|---|---|
| من | 109 | **67** (61.5%) | 12 (11.0%) | 30 (27.5%) | prepositional_phrase_component (66) | HARF (66) |
| ما | 38 | 0 | **24** (63.2%) | 14 (36.8%) | (mixed) | HARF (12) |
| بما | 15 | 0 | 0 | 15 (100%) | n/a | n/a |
| حيث | 4 | 0 | 0 | 4 (100%) | n/a | n/a |
| متى/أين/أنى/أيّ | 0 | 0 | 0 | 0 | — (لَيسَت في الـsample 3000) | — |

### مُلاحَظات:

- **من**: الـ67 المُرَقَّيَة كُلُّها مِنْ كَحَرف جَرّ (preposition). Resolver أَكَّد
  بِـ Certificate + reason صَريح "مِن (kasra) = حَرف جَرّ".
- **ما**: 24 case حَصَلَت metadata (function: relative/negative/conditional)
  لَكِن لَم تُرَقَّ لِـ Certificate (سِياق غَير كافٍ لِـ Certificate).
- **بما/حيث**: no_change لأَنَّ baseline أَعطاها Certificate أَصلًا (لا eligibility
  لِـ resolver).
- متى/أين/أنى/أيّ: غَير مَوجودَة في sample 3000. ستَظهَر في sample أَكبَر.

---

## C. Observe-mode Comparison

| المِعيار | OFF | ON | Δ |
|---|---|---|---|
| Event would_block_count | 0 | 0 | 0 |
| Relation would_block_count | 0 | 0 | 0 |
| Fragment_event_candidates | 0 | 0 | 0 |
| Fragment_relation_candidates | 0 | 0 | 0 |

⚠ **هام:** gates لَم تُفَعَّل (observe-only). الـintegration في Layer 1 لا يُحَرِّك
الـgates مُباشَرَةً — هذا مُتَوَقَّع. لِقياس أَثَر downstream الفِعليّ، نَحتاج
re-run sweep_v* مَع flag ON ثُمَّ مُقارَنَة qa_zeros / unresolved_edges.

---

## D. Safety Checks

| فَحص | الحالَة |
|---|---|
| no Event[ئك] | ✓ |
| segmentation_leak_count == 0 | ✓ (لَم تَتَأَثَّر) |
| fragment_event_count == 0 | ✓ |
| Certificate from conflicting candidates | ✗ (resolver يَفرِض no conflict) |
| event/relation gate enforcement | ✓ لَم يَحدُث |
| feature flag default OFF | ✓ |
| non-scope tokens unchanged | ✓ مُتَحَقَّق في tests |

---

## E. Test Results

| Suite | Pass |
|---|---|
| Full regression (flag OFF) | **290/290 ✓** |
| Full regression (flag ON) | **290/290 ✓** |
| Phase 4 standalone (test_phase4_resolver) | 30/30 ✓ |
| Phase 4 integration (test_phase4_integration) | 11/11 ✓ |

---

## Recommendation

**خِيار 2: أَبقِه خَلف flag وَوَسِّع resolver.**

### المُبَرِّر:

1. **MASAQ-alignment لَم تَتَأَثَّر** — هذا دَليل أَنَّ التَّرقيات صَحيحَة وَلا تُكَسِّر
   أَيّ شَيء.

2. **التَّأثير الحَقيقيّ لَم يُقَس بَعد** — qa_zeros / unresolved_edges يَتَطَلَّبَان
   تَشغيل Layer 4 / Phase D / Phase G كامِلًا. السكربتات الحاليَّة لا تَستَخدِم
   classify_with_context.

3. **3 surfaces بِدون عَيِّنَة** (متى/أين/أنى/أيّ) — قَبل التَّفعيل العامّ، نَحتاج
   sample يُغَطّيها.

4. **بِلا تَكامُل أَعمَق، resolver يَتَوَقَّف عِندَ Layer 1.** لِيُحَسِّن qa_zeros
   نَحتاج إِما:
   - تَوسيع integration إلى Phase C/D (relation/event extractors يَقرَأ phase4_selected_function)
   - أَو تَفعيل default ثُمَّ rerun كُلّ sweep_v*

### الخُطوَة التَّاليَة المُقتَرَحَة:

**A) extend integration إلى Phase C/D** بِحَيث relation extractor يَستَخدِم
   `phase4_selected_function` (relative_pronoun → relative-clause edge، etc.)
   ثُمَّ re-run sweep وَقياس qa_zeros / unresolved_edges.

**B) لا تُحَوِّل flag إلى default** حَتَّى نَقيس downstream فِعليًّا.

---

## Files

- `audit_outputs/phase4_off/summary.txt` — OFF run
- `audit_outputs/phase4_off/per_surface.csv` — OFF per-surface
- `audit_outputs/phase4_off/source_distribution.csv`
- `audit_outputs/phase4_on/summary.txt` — ON run
- `audit_outputs/phase4_on/per_surface.csv` — ON per-surface
- `audit_outputs/phase4_on/source_distribution.csv`
- `phase4_quran_audit.py` — السكربت المُستَخدَم

---

## Concluding note on Arabic accuracy

هذا التَّقرير يَقيس **MASAQ-alignment** فَقَط. لا يَدَّعي أَنَّ resolver يُحَسِّن
الدِّقَّة اللُّغَويَّة الحَقيقيَّة لِلتَّحليل العَرَبيّ. كَثير مِن tokens المَن/ما تَتَحَوَّل
داخِليًّا مِن HARF (MASAQ) إلى ISM_MABNI (نَموذَج لُغَويّ داخِليّ صَحيح) — هذا
هو السَّبَب في فَصل `selected_class` عَن `masaq_compatible_class`. لِقياس
الدِّقَّة اللُّغَويَّة بِشَكل مُستَقِلّ، نَحتاج reference annotation مُختَلِف عَن MASAQ.
