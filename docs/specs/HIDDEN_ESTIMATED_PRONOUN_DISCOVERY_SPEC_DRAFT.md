# HIDDEN / ESTIMATED PRONOUN DISCOVERY — SPEC DRAFT

> **Status:** DRAFT — discovery only. Read-only investigation.
> **Date:** 2026-05-28
> **Scope:** What can be mined from the existing `quran_i3rab.csv` corpus
> and the `hidden_pronouns.json` teaching set, to inform a future
> RULE_LOCK batch around **الضمير المستتر / المقدر** (hidden / estimated
> pronouns) and adjacent ellipsis phenomena.
> **NOT a production change. NO code in this commit besides this document.**

---

## 1. Executive Summary

### عربي

الكوربس `data/quran/quran_i3rab.csv` يحتوي نَصّاً إعرابياً تقليدياً لكل
كلمة في القرآن (77,374 سطر). البَحث المُقفَل أعاد إشارات قوية ومستقرة:

- **6,937 سطر** فيه «مستتر» (≈ 9% من كلمات القرآن).
- **99.3%** من هذه الأسطر تكشف الضميرَ المستترَ مباشرةً عبر النَمَط
  النَصِّيّ «تقديره (هو / هي / أنت / أنا / نحن / …)» — تَوزيع متوازن
  يَطابِق أنماط `hidden_pronouns.json`.
- **1,135 سطر** فيه عبارة «لم يسم فاعله»، و **1,181 سطر** فيه «نائب
  فاعل» — تَطابُق جُزْئيّ (743 سطراً يجمع الإشارَتين)، يُوافِق المَجهول.
- **322 سطر** فيه «الخبر/المبتدأ/فعل محذوف» مع «تقدير …» — حذف
  تَركيبي (ellipsis) لا يتعلَّق بالمستتر.
- **5,080 سطر** فيه «السكون/الضمة/الكسرة/الفتحة المقدَّر(ة)» — تقدير
  صوتي (phonological)، **ليس** ضميراً مقدَّراً، ويَجب فَصْله.

البَنية الإنتاجية الحالية في `hussein/clean_code/event_extractor.py`
تَأخذ `agent` من `RelationGraph` فقط؛ عند غيابه يَكون `None` — لا يُوجد
أي مَسار يَستنبط فاعلاً مستتراً. هذه هي الفجوة التشغيلية.

`hidden_pronouns.json` (11 إدخالاً) **غير محمَّل** في
`linguistic_source_registry.py`، وفي شجرة `i3rab_engine/` لا تُوجد أي
إشارة إلى `mustatir` / `hidden_pron` / `estimated_pron`. الموردُ موجودٌ
كَنَموذج تَعليميّ شامِل (يَغطّي كل الضمائر السبعة × رُتْبَتَيْن: وجوباً /
جوازاً) لكنَّه غير مَوصول.

### English (brief)

The corpus has clean, abundant evidence: 6,937 word-level rows carry the
free-text marker «مستتر» (hidden pronoun), of which 99.3% resolve the
implied pronoun via the stereotyped phrase «تقديره X». Passive-voice
signals («لم يسم فاعله» / «نائب فاعل») are independently detectable.
A separate, polysemous «مقدر/تقدير» field also tags phonological
case-estimation (5,080 rows — must be filtered out) and predicate
ellipsis (322 rows — distinct phenomenon).

The instructional dataset `hidden_pronouns.json` (11 entries) is not
loaded by `hussein/clean_code` and is currently dead weight. The
consumption-side gap is in `event_extractor.py`: `agent` is read only
from explicit `agent_of` relations and never inferred from a hidden
pronoun signal.

---

## 2. Pattern Table (counts from `quran_i3rab.csv`, 77,374 rows)

Patterns counted by **substring match after diacritic stripping**. Counts
are row-level (one Quranic word per row); a row may match more than one
pattern.

| # | Pattern (normalized) | Hits | What it signals |
|---|---|---:|---|
| 1 | `مستتر` | **6,937** | Hidden pronoun on a verb (or on `كان` and sisters as اسم). Pair almost always with «تقديره X». |
| 2 | `تقدير` | 7,528 | Generic "estimation" — overlaps with #1 (تقديره) and with phonological / ellipsis categories. Polysemous, needs sub-filtering. |
| 3 | `تقديره` | 7,414 | Almost always introduces an explicit estimated value: pronoun, verb, predicate, … |
| 4 | `مقدر` | 5,449 | Polysemous — mainly phonological case marking (السكون/الضمة المقدَّر) but also «الخبر محذوف والتقدير …». |
| 5 | `محذوف` | 1,849 | Ellipsis (الخبر/المبتدأ/فعل/جواب الشرط محذوف). Distinct from hidden pronoun. |
| 6 | `نائب فاعل` | 1,181 | The noun standing in for the dropped agent (in مبني للمجهول). |
| 7 | `لم يسم فاعله` | 1,135 | Verb-side passive marker. Overlaps strongly with #6 (743 shared rows). |
| 8 | `مضمر` | 439 | Older synonym for مستتر; usually attached to a حرف or فعل. |

### Sub-classification of the «مقدر / تقدير» family (11,811 rows)

Non-exclusive — a row may fall in more than one bucket:

| Sub-bucket | Pattern | Hits | Class |
|---|---|---:|---|
| `phonological` | السكون/الضمة/الكسرة/الفتحة المقدر(ة) (...للتعذر / للثقل / لالتقاء الساكنين) | **5,080** | NOT pronoun — exclude from this SPEC's scope |
| `estimated_pronoun_in_i3rab` | تقديره (هو/هي/أنت/أنا/نحن/هم/هن) | **7,008** | The core target — overlaps with #1 above (مستتر) |
| `ellipsis` | الخبر/المبتدأ/فعل محذوف ... والتقدير ... | 322 | Distinct phenomenon (predicate ellipsis), out of scope for Batch A |
| `uncategorised` | none of the above | 564 | Need manual review — sample at end of this section |

### Estimated-pronoun distribution (from «تقديره X» where X is a pronoun)

| Pronoun | Hits | Maps to `hidden_pronouns.json` entries |
|---|---:|---|
| هو | 4,034 | id=4 |
| أنت | 1,480 | id=2, 9, 10 |
| نحن | 599 | id=8 |
| هي | 402 | id=5 |
| أنا | 372 | id=1 |
| هم | 1 | id=6 (severely under-represented in this normalisation; collation needs work) |
| هن | 0 | id=7, 11 (likely written as «هنّ» — captured only with diacritic) |

> **Note on diacritics:** the corpus writes هنّ (with shadda) for the
> feminine plural. The stripping rule used here removes shadda too, so
> «هن» and «هنّ» should collapse; the zero count suggests the search
> regex needs a tighter pronoun-token list, not a real corpus gap. A
> future tightening pass should re-run with both surface forms.

### Top hosts of «مستتر» (verbs that conceal the pronoun, top 20)

`قَالَ` (326), `قُلْ` (263), `كَانَ` (164), `يَشَاءُ` (105), `يَعْلَمُ`
(54), `خَلَقَ` (48), `يَهْدِي` (39), `يُحِبُّ` (38), `أُنْزِلَ` (36),
`جَعَلَ` (34), `تَرَ` (31), `قُلِ` (30), `وَجَعَلَ` (29), `يُرِيدُ`
(26), `هُوَ` (26), `يَقُولُ` (24), `وَقَالَ` (23), `آمَنَ` (20),
`كَانَتْ` (20), `شَاءَ` (20).

> The presence of `هُوَ` (26 hits) is interesting — it shows that even
> the explicit pronoun word `هُوَ` can sit on a row whose i3rab text
> *also* describes a hidden pronoun (typically because the row's i3rab
> commentary spans multiple clauses).

### 2:282 evidence (smoke target)

| Word | Signal | i3rab excerpt (first 110 chars after diacritic strip) |
|---|---|---|
| `يَكْتُبَ` | مستتر | «فعل مضارع منصوب وعلامة نصبه الفتحة الظاهرة، والفاعل ضمير مستتر تقديره " هو "…» |
| `فَلْيَكْتُبْ` | مستتر | «(يكتب) : فعل مضارع مجزوم ... والفاعل ضمير مستتر تقديره " هو "» |
| `وَلْيَتَّقِ` | مستتر | «(يتق) : فعل مضارع مجزوم ... ضمير مستتر تقديره " هو "» |
| `يَبْخَسْ` | مستتر | «فعل مضارع مجزوم ... والفاعل ضمير مستتر تقديره " هو "» |
| `يَسْتَطِيعُ` | مستتر | «فعل مضارع معطوف مرفوع ... والفاعل ضمير مستتر تقديره " هو "» |
| `يُمِلَّ` | مستتر | «فعل مضارع منصوب ... والفاعل ضمير مستتر تقديره " هو "» |
| `تَكُونَ` | مستتر | «فعل مضارع ناسخ منصوب ... واسم (تكون) : ضمير مستتر تقديره " هي "» |
| `دُعُوا` | لم يسم فاعله | «فعل ماض مبني لما لم يسم فاعله ...» |
| `كَاتِبٌ` | نائب فاعل | «نائب فاعل مرفوع وعلامة رفعه الضمة الظاهرة» |

7 hidden-pronoun cases + 1 passive verb + 1 explicit نائب فاعل — the
verse is genuinely rich evidence for Batch A smoke tests.

### 2:196 evidence (smoke target)

| Word | Signal | i3rab excerpt |
|---|---|---|
| `اسْتَيْسَرَ` | مستتر | «فعل ماض ... والفاعل ضمير مستتر تقديره " هو "» |
| `كَانَ` | مستتر | «فعل ماض ناسخ ... واسم كان ضمير مستتر تقديره " هو "» |
| `تَمَتَّعَ` | مستتر | «فعل ماض ... والفاعل ضمير مستتر تقديره " هو "» |
| `يَجِدْ` | مستتر | «فعل مضارع فعل الشرط مجزوم ... والفاعل ضمير مستتر تقديره " هو "» |
| `أَذًى` | (مقدر — phonological) | «مبتدأ مؤخر مرفوع وعلامة رفعه الضمة المقدرة للتعذر» — NOT in scope |

---

## 3. Attack Surface — What Can Be Automated, What Cannot

### Automatable with high confidence (Tier 1)

For each row, given the i3rab text after diacritic stripping:

**T1.A — Hidden-pronoun extraction**
- Detect: substring `مستتر` is present.
- Resolve: search a fixed window after `تقديره` for one of
  `{أنا, نحن, أنت, هو, هي, هم, هن}` (canonical surface set).
- Output schema:
  ```
  HiddenPronounSignal(
      surah, ayah, word,
      pronoun_resolved,        # one of the 7 (or None if not extractable)
      ruling=None,             # cannot infer وجوب/جواز from corpus alone
      source="quran_i3rab_text",
      proof_kind=Certificate   # the i3rab text is authoritative for THIS word
  )
  ```
- Expected coverage: **≥ 99% pronoun resolution** on the 6,937 hits.
- Conflict policy: if a row has multiple `تقديره X` matches, take the
  one closest to the first `مستتر` occurrence.

**T1.B — Passive-voice noun-as-agent slot**
- Detect: `لم يسم فاعله` ⇒ verb is passive.
- Detect: `نائب فاعل` ⇒ this row's word is the surrogate agent.
- These are two halves of the same construction; they typically appear
  on adjacent rows of the same ayah (verb then noun). Wire them only as
  Hypothesis-level signals — formal pairing requires sentence-window
  logic that does not exist yet.

### Automatable with moderate confidence (Tier 2 — needs guards)

**T2.A — Ellipsis tagging (الخبر/المبتدأ/فعل محذوف)**
- 322 rows. Useful as a *flag* on the row, but the **estimated content**
  is free Arabic prose (e.g. «والتقدير: سؤالنا») and cannot be slotted
  into a fixed enum. Best treated as an unstructured `proof_blockers`
  annotation, not a typed field.

**T2.B — Mapping `hidden_pronouns.json` rulings (وجوبا / جوازا) to
specific Quranic rows**
- The teaching set encodes the morphological/syntactic conditions for
  each ruling, but the corpus rows do NOT carry the ruling explicitly.
  Cross-tagging requires a separate inference step (verb tense + form +
  surface subject absence) that crosses into Stage-10-level reasoning.
  **Out of scope for Batch A** — propose Batch B / C if needed.

### Not automatable in this scope (Tier 3 — human review required)

- The 564 «uncategorised مقدر/تقدير» rows. Sample shows mixed cases:
  some are «الضمة المقدرة لاشتغال المحل بحركة المناسبة للياء» (a deep
  phonological estimation that wasn't matched by the generic regex),
  some are «جواب الشرط محذوف» (ellipsis again), some «بحرف جر محذوف
  والتقدير: بأن لهم …» (preposition ellipsis with prose tafsir).
- The 26 rows where the word `هُوَ` itself carries «مستتر» in its
  i3rab — this is i3rab text that covers a multi-word clause; cannot be
  attributed to the single word without sentence-level disambiguation.

---

## 4. Non-Goals

This SPEC explicitly does **not** propose any of the following:

1. **Generalising hidden-pronoun inference to every verb without an
   explicit subject.** The signal source is the *i3rab corpus text*, not
   a morphological rule.
2. **Merging with ALASMA Stages 10–17.** ALASMA's word-type and
   nominal-internal layers are governed by separate SPECs and
   RULE_LOCKs.
3. **Fixing Stage 10 (word-type classification) via this layer.** Any
   `هو/هي/أنت/...` resolved here is a *posited agent*, not a re-class of
   the verb.
4. **Touching `segmenter.py`, `i3rab_engine/*`, `relation_extractor.py`,
   `event_extractor.py`, `resolution_engine.py`, or any file under
   `alasmaa/`** in the implementation of Batch A. The only production
   code change Batch A would require is a *new* module
   (`hidden_pronoun_signals.py` or similar) plus a SPEC-approved hook in
   `event_extractor.py`'s agent-fallback path — and that hook itself is
   a Batch B decision, not Batch A's.
5. **Committing the mined JSONL output (`hidden_pronoun_signals.jsonl`)
   as a checked-in data file.** It can be generated on demand by the
   build tool; only the SPEC, the tool source, and small fixtures should
   be committed.
6. **Inferring ruling (وجوبا vs جوازا)** from corpus alone — out of
   scope for Batch A.
7. **Resolving anaphora** ("who is this هو?") — that is a separate
   resolution-engine concern.

---

## 5. Proposed RULE_LOCK — Batch A (3 rules, max)

> **All three are context-locked to a single i3rab text-pattern. No
> generalisation. Hypothesis by default; Certificate only when the
> i3rab text explicitly resolves the pronoun.**

### Rule A1 — `HiddenSubjectFromI3rabText`
- **Trigger:** for a corpus row `(surah, ayah, word)`, the diacritic-
  stripped i3rab text contains **both**:
  1. the substring `مستتر`, AND
  2. a `تقديره` … pronoun-token within the next 30 characters.
- **Output:**
  - `hidden_subject = pronoun_token` (one of: `أنا, نحن, أنت, هو, هي, هم, هن`)
  - `proof_kind = Certificate`
  - `source = "quran_i3rab_text:mustatir+taqdiruhu"`
- **Negative constraints:**
  - If the row's word IS itself an explicit pronoun (`هُوَ, هِيَ, أَنْتَ, ...`), suppress the signal (the i3rab is describing a different clause).
  - If `تقديره` is preceded by `السكون / الضمة / الكسرة / الفتحة` within 5 chars, suppress — this is phonological, not pronoun.

### Rule A2 — `PassiveVerbSignal`
- **Trigger:** the row's diacritic-stripped i3rab text contains `لم يسم فاعله`.
- **Output:**
  - `voice = passive`
  - `proof_kind = Certificate`
  - `source = "quran_i3rab_text:lam_yusamma_faailuhu"`
- **No agent inference** — the agent is unspecified by definition.

### Rule A3 — `NaibFaailMarker`
- **Trigger:** the row's diacritic-stripped i3rab text starts (after
  optional leading punctuation) with `نائب فاعل`.
- **Output:**
  - `role = naib_faail`
  - `proof_kind = Certificate`
  - `source = "quran_i3rab_text:naib_faail_head"`
- **Negative constraint:** other mentions of `نائب فاعل` deeper in the
  text (e.g. in a relative-clause i3rab embedded later) MUST NOT fire.
  Head-position match only.

That is the entire proposed Batch A scope: 3 rules, all single-row,
all certificate-grade because they read what the traditional i3rab text
*itself* says about *this exact word*.

---

## 6. Smoke Tests (proposed `(surah, ayah, word)` set)

All targets verified present in `quran_i3rab.csv` during this discovery
pass.

### A1 — HiddenSubjectFromI3rabText

| # | Surah:Ayah | Word | Expected `hidden_subject` |
|---|---|---|---|
| 1 | 2:282 | `يَكْتُبَ` | هو |
| 2 | 2:282 | `فَلْيَكْتُبْ` | هو |
| 3 | 2:282 | `يَبْخَسْ` | هو |
| 4 | 2:282 | `تَكُونَ` | هي |
| 5 | 2:196 | `اسْتَيْسَرَ` | هو |
| 6 | 2:196 | `تَمَتَّعَ` | هو |
| 7 | 1:5  | `نَعْبُدُ` | نحن |
| 8 | 1:5  | `نَسْتَعِينُ` | نحن |
| 9 | 1:6  | `اهْدِنَا` | أنت |
| 10 | 2:6 | `تُنْذِرْهُمْ` | أنت |

### A1-negative (must NOT fire)

| # | Surah:Ayah | Word | Why |
|---|---|---|---|
| n1 | 2:196 | `أَذًى` | i3rab has «الضمة المقدرة للتعذر» — phonological, not pronoun |
| n2 | 1:1 | `بِسْمِ` | i3rab has «لفعل محذوف تقديره: أبتدئ» — ellipsis of verb, not hidden-subject pronoun |

### A2 — PassiveVerbSignal

| # | Surah:Ayah | Word | Expected |
|---|---|---|---|
| 1 | 2:282 | `دُعُوا` | voice=passive |
| 2 | 2:25 | `وَأُتُوا` | voice=passive (uncategorised sample showed this row matches) |

### A3 — NaibFaailMarker

| # | Surah:Ayah | Word | Expected |
|---|---|---|---|
| 1 | 2:282 | `كَاتِبٌ` | role=naib_faail |

---

## 7. Dependencies

### 7.1 New external evaluation tool

Extend `new_arabic_analyzer/tools/build_i3rab_labels.py` (already a
discovery-only tool, not on the production path) with three new label
codes:

| Code | Trigger (after diacritic strip) | Notes |
|---|---|---|
| `MUSTATIR` | substring `مستتر` | The host word's i3rab declares a hidden subject |
| `MUSTATIR_RESOLVED_<X>` | `مستتر` + `تقديره X` where X ∈ {أنا, نحن, أنت, هو, هي, هم, هن} | One label per resolved pronoun for analytics |
| `LAM_YUSAMMA_FAAIL` | `لم يسم فاعله` | Verb is passive |
| `NAIB_FAAIL_HEAD` | primary i3rab clause starts with `نائب فاعل` | This word is the surrogate agent |

This stays outside the production path. It is purely for
evaluation/coverage analysis and to produce the smoke-test ground truth.

### 7.2 NOT required for Batch A

- **No change** to `linguistic_source_registry.py`. `hidden_pronouns.json`
  remains unloaded for now; Batch A reads from the i3rab corpus only.
  Wiring the teaching set as a *secondary* validation source belongs in
  a possible Batch B.
- **No change** to `event_extractor.py`'s agent-resolution path. Whether
  to consume a `HiddenPronounSignal` in the `agent` fallback is a Batch
  B / C decision and requires its own RULE_LOCK with explicit
  proof-kind handling (Hypothesis vs Certificate propagation through to
  L5 event signature).
- **No change** to MASAQ tag handling. The corpus i3rab text is a
  separate evidence channel from MASAQ; they should remain independent
  until cross-source validation is itself SPEC'd.

### 7.3 Open questions for governance before Batch A is opened

1. Should the i3rab corpus be addressed via a new module file
   (`clean_code/i3rab_text_signals.py`) consulted from a dedicated
   layer, or via the existing `linguistic_source_registry.py`?
2. Should `HiddenPronounSignal` be a first-class type in `types.py` or a
   `proof_blockers` annotation only?
3. For the 26 rows where `هُوَ` itself carries a `مستتر` annotation
   (which describes a *different* clause's verb), is suppression by
   "is the row's word itself a pronoun?" sufficient, or do we need a
   sentence-window check?

These are SPEC-level decisions and should be answered before the
RULE_LOCK is drafted — not in the implementation pass.

---

## 8. Artifacts produced by this discovery pass

| Path | Type | Status |
|---|---|---|
| `hussein/docs/specs/HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md` | This document | Committed |
| Mining script (one-shot, inline) | Python | Not committed — re-runnable from §2 query patterns |
| `outputs/i3rab_mining_results.json` | Discovery scratch | Sandbox-only, not committed |

No production code modified. No data files added.

---

## 9. Strict boundaries respected in this discovery

- `clean_code/segmenter.py` — **not touched**
- `clean_code/i3rab_engine/*` — **not touched**
- `clean_code/relation_extractor.py` — **not touched**
- `clean_code/event_extractor.py` — **not touched** (only read for the
  agent-fallback gap analysis)
- `clean_code/resolution_engine.py` — **not touched**
- `alasmaa/*` — **not touched**
- Large CSV/JSONL outputs — **not committed**
- ALASMA Stage 18 — **not opened**
