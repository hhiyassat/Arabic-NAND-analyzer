# POST-PATCH-4 AUDIT CHECKPOINT — 2:282

**Date:** 2026-05-26
**Branch:** patch0-production-path-trace
**Head commit:** `67587e7` (PATCH 4: gate KB.SAM operator meanings by L1 prefix/suffix certification)
**Source output:** `out_2_282_after_patch4_checkpoint.txt` (740 lines)
**Test result:** `36/36 passed` (`python3 clean_code/test_production_path_segmentation.py`)

---

## 0. Git state (verbatim)

```
67587e7 PATCH 4: gate KB.SAM operator meanings by L1 prefix/suffix certification
c040294 PATCH 3: fix functional noun, false-lam, dual-verb, and alla in 2:282
fc30616 PATCH 2: fix closed forms and Form VI past recognition
a85ad43 PATCH 1: fix Lam al-amr segmentation in production path
931824e PATCH 0: trace production path and add segmentation characterization tests
38c9098 Document detailed bug families from 2:282 audit
b599cd4 Phase 4: add Certificate Re-evaluation test suite (12/12 passing) + untrack .pyc
7afaf07 Add gitignore and remove generated artifacts
```

Working tree: clean (only `.claude/` untracked, local).

---

## A. Fixed families — evidence from 2:282 (post PATCH 4)

### A1. PATCH 1 — Lam al-amr (L1)

```
 22:   وَلْيَكْتُب          ← prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) | stem=يَكْتُب  | suffixes=—
 36:   فَلْيَكْتُبْ         ← prefixes=فَ(CONJ)+لْ(LAM_AL_AMR) | stem=يَكْتُبْ | suffixes=—
 37:   وَلْيُمْلِلِ         ← prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) | stem=يُمْلِلِ | suffixes=—
 63:   فَلْيُمْلِلْ         ← prefixes=فَ(CONJ)+لْ(LAM_AL_AMR) | stem=يُمْلِلْ | suffixes=—
 41:   وَلْيَتَّقِ          ← prefixes=وَ(CONJ)+لْ(LAM_AL_AMR) | stem=يَتَّقِ  | suffixes=—
```

All 5 lam-al-amr forms correctly split CONJ + LAM_AL_AMR + verb stem.

### A2. PATCH 2 — Closed forms / demonstratives / Form VI past (L1)

```
 38:   ٱلَّذِى              ← prefixes=— | stem=الَّذِى | suffixes=—            (atomic, no DET peel)
106:   ذَٰلِكُمْ            ← prefixes=— | stem=ذَٰلِكُمْ | suffixes=—          (atomic)
 15:   تَدَايَنتُم          ← prefixes=— | stem=تَدَا | suffixes=يَن(NSUFF)+تُم(VSUFF)  (no IMPERF peel)
131:   تَبَايَعْتُمْ        ← prefixes=— | stem=تَبَايَعْ | suffixes=تُمْ(VSUFF) (no IMPERF peel)
```

Form VI past forms keep `aspect=PV`; demonstratives atomic.

### A3. PATCH 3 — Functional noun / false lam / dual نا / أَلَّا (L1 + L3)

L1:
```
 23:   بَّيْنَكُمْ          ← prefixes=— | stem=بَّيْنَ | suffixes=كُمْ(POSS_PRON)   (no PREP peel)
122:   بَيْنَكُمْ           ← prefixes=— | stem=بَيْنَ  | suffixes=كُمْ(POSS_PRON)   (no PREP peel)
 64:   وَلِيُّهُۥ           ← prefixes=وَ(CONJ) | stem=لِيُّهُۥ | suffixes=—         (no false-لِ peel)
 74:   يَكُونَا             ← prefixes=يَ(IMPERF_PREF) | stem=كُونَا | suffixes=—   (no نَا POSS_PRON)
113:   أَلَّا               ← prefixes=أن(HARF_NASB) | stem=لا | suffixes=—
126:   أَلَّا               ← prefixes=أن(HARF_NASB) | stem=لا | suffixes=—         (HARF_NASB, not PREP)
```

L3 (PATCH 3 FIXUP + PATCH 3E):
```
169:   بَّيْنَكُمْ          → class=ISM_MUARAB | role=ظرف مكان       | root=بين | wazn=فَّعْل
259:   بَيْنَكُمْ           → class=ISM_MUARAB | role=ظرف مكان       | root=—   | wazn=ضمير متصل
207:   وَلِيُّهُ            → class=ISM_MUARAB | role=فاعل مرفوع     | root=—   | wazn=—
215:   يَكُونَا             → class=FIIL       | role=فعل مضارع      | root=—   | wazn=—
251:   أَلَّا               → class=HARF       | role=حرف            | root=—   | wazn=حرف تحضيض
263:   أَلَّا               → class=HARF       | role=حرف            | root=—   | wazn=حرف تحضيض
```

(Note: أَلَّا wazn=`حرف تحضيض` is inaccurate — see Section B/L3. Acceptable for PATCH 3 acceptance: it is HARF, not noun.)

### A4. PATCH 4 — KB.SAM gate (post-filter)

All 7 target tokens now emit **zero** operator claims through KB.SAM:

```
309:   «وَلْيَكْتُب»:                ← (empty — قسم/رب filtered)
331:   «وَلْيُمْلِلِ»:                ← (empty — قسم/رب filtered)
335:   «وَلْيَتَّقِ»:                ← (empty — قسم/رب filtered)
311:   «كَاتِبٌۢ»:                    ← (empty — كاف operators filtered)
320:   «كَاتِبٌ»:                     ← (empty)
464:   «كَاتِبٌ»:                     ← (empty)
350:   «سَفِيهًا»:                    ← (empty — سين تنفيس filtered)
321/356/393/416/443:  «أَن»:           ← (empty — إِن الشرطية / إِنَّ filtered)
439/453:  «أَلَّا»:                   ← (empty — لا الناهية filtered)
```

Allowed meanings preserved:
```
312:  «بِٱلْعَدْلِ»:    ? [ج3] الباء لِلإِلصاق / الاستِعانَة / السَّبَبيَّة   (ب-PREP certified)
317:  «وَلَا»:           ✓ [ج3] واو العَطف — تُشرِك الثَّاني في إِعراب الأَوَّل  (CONJ-certified)
323:  «كَمَا»:           ? [ج3] الكاف لِلتَّشبيه / لِلتَّعليل                     (ك-PREP certified)
329:  «فَلْيَكْتُبْ»:   ? [ج4] فاء رابِطَة لِجَواب الشَّرط                       (ف-CONJ certified)
+ all «إِلَىٰٓ» and «إِذَا» full-form entries unchanged.
```

---

## B. Remaining known bugs in 2:282 (list-only, no fixes)

### B-L1. L1/L2 segmentation remaining issues

| Line | Token | Current segmentation | Issue |
|------|-------|----------------------|-------|
| 20 | `فَٱكْتُبُوهُ` | stem=`اكْتُبُو` + suf=`هُ` | Plural marker `وا` swallowed into stem; should be stem=`اكْتُب` + sufs `وا(NSUFF) + هُ(POSS_PRON)`. |
| 54 | `سَفِيهًا` | stem=`سَفِي` + suf=`هًا(POSS_PRON)` | **Wrong**: `هَا` is the noun's final radical + tanwin; not a 3sg-f pronoun. False POSS_PRON peel. |
| 81 / 91 | `ٱلشُّهَدَآءِ` / `ٱلشُّهَدَآءُ` | stem=`شُهَدَءَاءِ` / `شُهَدَءَاءُ` | Hamza-on-alif normalization injects duplicated `ءَا`. Cosmetic but breaks `root=ـ`. |
| 97 | `تَسْـَٔمُوٓا۟` | stem=`سَْٔمُوٓا۟` | Sukun-hamza ordering produces `سَْ` (sukun before glyph). Cosmetic. |
| 116 | `إِلَّآ` | stem=`إِلَّءَا` | Same hamza-alif duplication as B81. |
| 121 | `تُدِيرُونَهَا` | pref=`تُ` stem=`دِيرُونَ` suf=`هَا` | Plural marker `ونَ` swallowed into stem; should peel as NSUFF. |
| 142 | `فُسُوقٌۢ` | pref=`فُ(CONJ)` stem=`سُوقٌۢ` | **Wrong**: فاء العَطف is always فَـ (fatha); فُـ (damma) here is part of root ف‑س‑ق. False CONJ peel. |

### B-L3. L3 morphology / i3rab remaining issues

| Line | Token | Current L3 | Issue |
|------|-------|------------|-------|
| 161 / 232 / 266 | `إِذَا` | role=`مفعول به منصوب` | **Wrong**: إِذَا is ظَرف زَمان / أَداة شَرط — never مفعول به. |
| 165 | `أَجَلٍ` | wazn=`حرف جواب` | wazn wrong (it's a noun, not a particle). |
| 177 | `كَمَا` | class=`ISM_MAWSOOL` wazn=`ضمير متصل` | Should be كَ(PREP) + ما (mawsool/masdariyya). Composite analysis lost. |
| 183/190/195/261 | `عَلَيْهِ` / `مِنْهُ` / `عَلَيْكُمْ` | class=HARF role=حرف wazn=`ضمير متصل` | PREP+pronoun composites; pronoun referent invisible to L4. |
| 219 | `مِمَّن` | class=HARF wazn=empty | `min+man` composite; wazn missing. |
| 246 | `عِندَ` | class=HARF | **Same family as بَيْنَ (PATCH 3)** — عِندَ is a functional locative noun (ظَرف), should be ISM_MUARAB. PATCH 3 fix covered بَيْنَ only; عِندَ unfixed here. |
| 251 / 263 | `أَلَّا` | wazn=`حرف تحضيض` | Inaccurate: أَلَّا here = أَن النَّاصِبَة + لا النَّافيَة, not حرف تَحضيض. (Class HARF is correct.) |
| 282 | `وَٱللَّهُ` | role=`نعت مرفوع` | **Wrong**: should be مبتدأ مرفوع / معطوف. |
| 283 | `بِكُلِّ` | role=`ظرف مكان` | **PATCH 3 FIXUP false-positive**: `كُلَّ` is in `functional_nouns_lexicon.csv` (category=quantifier) and the L3 gate fires for any stem in that lexicon regardless of category. `كُلّ` is a quantifier, not a locative ظَرف; role should be اسم مجرور. |

### B-KBSAM. KB.SAM remaining overmatch / missing meaning

| Token | Current | Issue |
|-------|---------|-------|
| `لِلشَّهَٰدَةِ` | 3 hypotheses (ملك / اختصاص / تعليل) | All 3 surface as `?` Hypothesis; no disambiguation rule selects one. Not a gate bug — disambiguation gap. |
| `أَلَّا` (post-gate empty) | empty | Correct بعد الـ gate, but the legitimate `أن النَّاصِبَة` claim is missing (KB.SAM never had it as a separate entry). Missing-meaning, not overmatch. |
| `أَن` (post-gate empty) | empty | Same — legitimate `أن النَّاصِبَة` claim missing from KB.SAM. |
| `وَلَا` (standalone) | only واو العَطف when context fires | `WawDisambiguation` requires multi-word context. Single-word audit drops everything — acceptable for 2:282 (multi-word context fires correctly on lines 317, 338, etc.). |

### B-L4. L4 relation issues

| Line | Relation | Issue |
|------|----------|-------|
| 503 / 521 | `? possessor_of : بِٱلْعَدْلِ → كَاتِبٌ` / `→ وَلِيُّهُ` | Wrong: بِٱلْعَدْلِ is جار+مجرور adverbial of يَكْتُب/يُمْلِلْ, not a possessor. |
| 508 | `? agent_of : ٱللَّهُ → عَلَّمَهُ` | Should be Certificate, not Hypothesis (clear subject-verb). |
| 516 / 562 | `? ism_of_kana : ٱلْحَقُّ → كَانَ` | Wrong: ism of كان is the elided pronoun referring to ٱلَّذى; ٱلْحَقُّ is خبر of the relative clause. |
| 526 / 563 | `? ism_of_kana : فَرَجُلٌ → يَكُونَا` | Wrong: فَرَجُلٌ is جواب الشرط, not اسم يكونا. |
| 558 | `? agent_of : ٱللَّهُ → وَيُعَلِّمُكُمُ` | Correct relation, but Hypothesis instead of Certificate. |
| 559 | `? attribute_of : وَٱللَّهُ → ٱللَّهُ` | Wrong: separate occurrences, not attribution. |
| 565-578 | Many `? agent_of : ⊕<pron> → <verb>` | Implicit-agent hypotheses; several mis-target (e.g. `⊕هُوَ → يُضَآرَّ` should be `⊕هو/يضارّ‑ـه` passive-like; `⊕نَحْنُ → يَكُونَا` wrong — يَكُونَا is dual, agent is ⊕هُمَا). |

### B-L5. L5 event / time / mood issues

| Symptom | Where | Issue |
|---------|-------|-------|
| `time=when_future` on ALL events | every event (lines 583-699) | Universal — even past tenses (Event[ءمن] tense=past time=when_future, Event[تَدَايَنتُم] tense=past time=when_future, etc.). The time-resolution layer hardcodes `when_future` for everything. |
| Lam-al-amr verbs tagged `tense=present` | Event[وَلْيَكْتُب], Event[فَلْيَكْتُبْ], Event[وَلْيُمْلِلِ], Event[فَلْيُمْلِلْ], Event[وَلْيَتَّقِ] | **Mood not propagated**: production L1 correctly tags `لْ(LAM_AL_AMR)` and L3 says `فعل مضارع`, but L5 should mark mood=`jussive_command` (طَلَب). Currently indistinguishable from plain present. Same applies to لا الناهية + jussive (وَلَا يَأْبَ, وَلَا يَبْخَسْ, وَلَا تَسْـَٔمُوٓا). |
| Many events missing agent/patient | Event[كتب], Event[رضض], Event[ضلل], etc. | L4 has the relations but L5 doesn't ingest them; agent/patient slots empty. |
| Duplicate Event[ءمن] / Event[تَدَايَنتُم] under different patient labels | lines 582 / 586 | Hashing/dedup miss. |

### B-L6. L6 resolution issues

| Line | Resolution | Issue |
|------|------------|-------|
| 703 / 710 | `? anaphora : هُوَ → ضَعِيفًا (+15 alts)` | Wrong antecedent: هُوَ refers to ٱلَّذى عَلَيْهِ ٱلْحَقّ (the debtor), not ضَعِيفًا. |
| 704 | `✗ relative : ٱلَّذِينَ → بِلا مَرجِع` | Zero — the first relative pronoun unresolved. |
| 705 | `? relative : ٱلَّذِى → ٱللَّهُ (+8 alts)` | Wrong: ٱلَّذى refers to the debtor. |
| 706 | `? relative : ٱلَّذِى → شَيْـًٔا (+12 alts)` | Wrong: same — debtor antecedent. |
| 707-708 | `? relative : مِن → شَهِيدَيْنِ` / `مِنَ → وَٱمْرَأَتَانِ` | **Misclassification**: مِن / مِنَ are HARF JARR, never relative pronouns. The resolver is firing the relative-resolution rule on prepositions. |
| 709 | `? relative : مَا → إِذَا (+29 alts)` | Wrong target. |

### B-L8. L8 QA issues

| Line | Question | Issue |
|------|----------|-------|
| 723 | "مَن الفاعِل؟" → mixed list of agents | No per-event disambiguation; all candidates pooled. |
| 725 / 731 / 733 | "ماذا حَدَث؟" / "ما تَسَلسُل الأَحداث؟" / "إلى ماذا تَحَوَّلَ شَيء؟" | All three produce identical list (إِذَا / ٱللَّهَ / شَيْـًٔا / إِحْدَىٰهُمَا / صَغِيرًا). Different questions, same fallback answer. Answer-type gate not enforced. |
| 727 | "أَين حَدَث؟" → `أَجَلٍ / رِّجَالِكُمْ / أَجَلِهِ` | Conflates time (أَجَل = term) and entity (رِّجَال = men) with location. Location gate missing. |
| 729 | "متى حَدَث؟" → `tense:present / when_future / tense:past / tense:command` | Returns bare label strings, not actual time/temporal expressions (`إِذَا تَدَايَنتُم`, `إِذَا تَبَايَعْتُمْ`). |

### B-L7 (graph statistics)

```
العُقَد: 140 (52C + 88H)
الرَّوابِط: 68 (16C + 52H)
التَّغطيَة: 63.2%
Entropy (الغُموض): 28.68
مُتَّسِق: نَعَم ✓
```

Coverage 63.2%, certificate/hypothesis ratio low (52C/88H nodes, 16C/52H edges). Most remaining work is converting Hypothesis edges to Certificate.

---

## C. Recommended next patch — based on checkpoint evidence

**Recommendation: PATCH 5 = L5 LamAlAmrMoodPropagation / CommandLamEventMood.**

Evidence supporting this as the dominant family:

1. **Universal `time=when_future` bug** affects 100% of events on 2:282. This is the single most pervasive defect; every L5 event line is affected.
2. **Lam-al-amr mood lost** at L5 even though PATCH 1 fixed it at L1. Five verbs (وَلْيَكْتُب / فَلْيَكْتُبْ / وَلْيُمْلِلِ / فَلْيُمْلِلْ / وَلْيَتَّقِ) plus three لا-النَّافِيَة-jussive forms (وَلَا يَأْبَ × 2, وَلَا يَبْخَسْ, وَلَا تَسْـَٔمُوٓا) all surface as `tense=present` with no distinction from plain indicatives. This is the direct downstream consequence of PATCH 1 not being propagated.
3. **L8 "متى حَدَث؟" answer** returns bare `tense:*` label strings because L5 time data is empty/uniform. Fixing L5 unblocks L8 answer quality.
4. Scope is bounded: it touches `event_extractor.py` only (mood propagation + tense→time mapping), no segmentation/L1/L3 changes.

Runner-up families and why deferred:

- **L6 relative/anaphora resolver** — large-coverage issue (7 wrong resolutions on 2:282) but resolver overhaul is a Phase-level change, not a PATCH-sized one.
- **L4 relation safety gates** — several mis-attribution Hypotheses, but L4 is "correct relations buried in noise"; gating it requires deciding which Hypotheses to suppress, more design than fix.
- **L8 QA answer-type gate** — depends on L5 being correct first (the "متى" / "أين" gates need clean L5 time/location).
- **L1 cleanup batch (B-L1 items, including فُ(CONJ) false peel + سَفِيهًا false POSS_PRON peel)** — small, mechanical, could be a PATCH 5.5 sandwich; defer to keep PATCH 5 narrow.
- **L3 quantifier-gate fix for بِكُلِّ** — single one-line fix (filter `functional_nouns_lexicon` by category=locative in `layer3._is_functional_locative_noun`); should bundle with B-L1 batch.

---

## D. Regression scope recommendation

**Recommendation: small sample regression (5-10 verses) BEFORE PATCH 5.**

Rationale:
- PATCH 0-4 were all developed against 2:282 only. We have **zero evidence** that other verses are unaffected by the new gates (PATCH 3A `بَيْنَ`-as-functional-noun removal from PREP set, PATCH 3 FIXUP role override, PATCH 4 KB.SAM gate).
- A 5-10 verse sample is enough to catch broad regressions cheaply. Suggested verses: 1:1-7 (Fatiha, structurally different), 2:1-5 (intro, different particle mix), 2:43 (short imperative — exercises lam-al-amr family), 4:34 (long complex), 36:80 (different tense/aspect mix).
- 3000-token regression: too large for pre-PATCH-5 sanity; better positioned as a pre-merge gate later.
- Full Quran audit: **NOT now**. Reserve for after PATCH 5-8 lands and the small sample is green.

If small sample regression surfaces unexpected breakage from PATCH 0-4, fix before moving to PATCH 5. Otherwise proceed to PATCH 5 = L5 mood/time propagation.

---

## Strict-scope confirmation

This checkpoint **did not modify**:
- `segmenter.py`
- `i3rab_engine/*`
- `event_extractor.py`
- `relation_extractor.py`
- `resolution_engine.py`
- KB.SAM data
- Any committed code

Only artifact written: `out_2_282_after_patch4_checkpoint.txt` (untracked) and this report (untracked). **Not committed.**

---

## Addendum — PATCH 4.5

PATCH 4.5 fixed the L3 false-positive introduced by PATCH 3:
- بِكُلِّ no longer receives role=ظرف مكان.
- The locative override now applies only to functional nouns with category=locative.
- بَّيْنَكُمْ and بَيْنَكُمْ remain role=ظرف مكان.
- Production test now passes 37/37.
