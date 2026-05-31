# MAANI CONSUMPTION ENHANCEMENT — SPEC DRAFT

> **Status:** DRAFT — read-only investigation. No production code changed.
> **Date:** 2026-05-28
> **Predecessor:** [`HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md`](./HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md) — separate thread; NOT merged into this RULE_LOCK.
> **Scope:** Map how the maani sources (Samarrai 4 vols + Maani al-Nahw JSONL + NAA operators catalog) are consumed today by `hussein/clean_code`, identify gaps to L4–L6 consumption, and propose a 3-step risk-ordered enhancement path that respects NAND / ProofObject / `samarrai_certified_operator_gate`.

---

## 1. Executive Summary

### عربي

في `hussein/clean_code` ثَلاثَة مَصادِر لِلمَعاني، **يَجِب عَدَم خَلطها** في
RULE_LOCK واحِد:

1. **معاني السامرَّائيّ (CSV — مُعتَمَد)** — 245 سَطراً عَبر 4 مُجَلَّدات +
   ملفَّيْن في `constructions/`. مُحَمَّلَة عَبر `samarrai_loaders/*`،
   مُستَهلَكَة في `samarrai_analyzer.py` (طَبَقَة KB.SAM)، ومُفلتَرَة بِـ
   `samarrai_certified_operator_gate.py` (PATCH 4، 2026-05-26) قَبل
   العَرض في `analyze_verse_v3 --samarrai`.
2. **معاني النحو (JSONL — استِخراج OCR خام)** — ~20 ملفّ في
   `maani_alnahw/data/processed/`، إِجماليّ ~10–20 أَلف عُنصُر (1,043
   construction_rules، 1,818 meaning_cards، 5,800 semantic_claims…).
   **غير على مَسار v3**. مُستَهلَك فَقَط في `analyze_verse.py` القَديم وَ
   `build_maani_quran_corpus_fast.py` عَبر `maani_kb_loader.py` →
   `GrammarKB`.
3. **NAA operators_catalog (CSV)** — 102 سَطر، 92 operator مُتَمَيِّز.
   **غير مَوصول** بِـ `hussein/clean_code`. تَقاطُع 29 operator فَقَط مَع
   SAM؛ يَتَفَوَّق على SAM في عَرض العَوامِل (verbs، exception particles)،
   لَكِنَّ SAM يَتَفَوَّق في عُمق المَعاني (ل: NAA قِراءَة واحِدَة، SAM 13).

`meaning_assembler.py` يَستَهلِك مِن SAM **التَّراكيب فَقَط**
(constructions كَ node_type="construction") — لا يَستَهلِك ادِّعاءات
الكَلِمَة المُفرَدَة. هذه فَجوَة استِهلاكٍ كَبيرَة.

العَيِّنَة عَلى ثَلاث آيات بَيَّنَت:
- تَغطيَة 40–50% مِن كَلِمات الآيَة بِادِّعاءات بَعد البَوّابَة.
- 44% مِن الادِّعاءات الخامَّة تُسقِطها البَوّابَة في 2:196 (أَكبَر سَبَب:
  `PREP_LAM` على «لِلَّهِ» الَّتي تُعالَج ذَرّيّاً في L1 — صَحيح).
- ثُغرَة في البَوّابَة: قِراءات أُخرى لِلامِ (`JAZM_LAM_AMR`،
  `SHART_LAM_JAWAB`، `LAM_IBTIDA`) **لا** يُطلَب لَها prefix-tag وَ تَمُرّ
  دونَ تَحَقُّق سياقيّ.
- 1:5 كَشَفَت تَركيب `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` مَرَّتَيْن — هذا هُو
  حالَة الاستِخدام الأَنجَح حاليّاً.

### English (brief)

Three maani sources exist; they are **not** redundant and must not be
merged in one RULE_LOCK. Samarrai CSVs (245 rows, curated) are wired
through `samarrai_analyzer` → `samarrai_certified_operator_gate` →
display; only their `constructions` slice flows into `meaning_assembler`
(as `node_type="construction"` nodes). The Maani al-Nahw JSONL pipeline
(~10–20k items, OCR-extracted) is off the v3 path and only used by
legacy `analyze_verse.py`. The NAA operators catalog (102 rows) is
broader-but-shallower than SAM and is not wired in at all. Coverage on
the 3 sample verses is 40–50% of words; the gate drops up to 44% of raw
claims (correctly) but a per-topic gap (lam-topics other than `PREP_LAM`)
lets context-less readings through.

---

## 2. Source → Layer → Consumer → Gap Table

| # | Source | Path | Loader | Layer(s) it feeds today | Already consumed? | Gap |
|---|---|---|---|---|---|---|
| 1 | Samarrai CSV (vol1: 82 rows) | `data/contracts/maani/volume1/*.csv` (5 files) | `samarrai_loaders/volume1_loader.py` | KB.SAM display; meaning_assembler (via constructions only) | Partial | Per-word claims never flow into `MeaningGraph` nodes; `meaning_assembler` reads only `ta.constructions`, not `ta.words[i].claims`. |
| 2 | Samarrai CSV (vol2: 42 rows) | `volume2/*.csv` (4 files) | `samarrai_loaders/volume2_loader.py` | Same as above | Partial | Same gap. Vol 2 is about فاعل/نائب/مفعول — natural candidates for L4 role-attribute enrichment. |
| 3 | Samarrai CSV (vol3: 62 rows) | `volume3/*.csv` (6 files) | `samarrai_loaders/volume3_loader.py` | Same | Partial | Same gap. Vol 3 is prep-letter semantics; this is exactly what L4 `agent_of`/`patient_of`/`prep_of` relations should be able to consult. |
| 4 | Samarrai CSV (vol4: 57 rows) | `volume4/*.csv` (8 files) | `samarrai_loaders/volume4_loader.py` | Same | Partial | Same gap. Vol 4 covers shart/qasam/taqdim — high-value for L5 event-modality. |
| 5 | Samarrai constructions CSV (2 rows) | `data/contracts/maani/constructions/patterns.csv` | `samarrai_analyzer.detect_constructions` | `meaning_assembler` step 6 (construction nodes) | **Yes** | Pattern set is tiny (2 rows). Real construction patterns documented in `maani_alnahw/curated_constructions.jsonl` (3 rows) and `construction_rules.jsonl` (1,043 rows) are not migrated. |
| 6 | Maani al-Nahw — construction_rules.jsonl (1,043 rows) | `maani_alnahw/data/processed/maani_alnahw/` | `maani_kb_loader.get_kb()` → `GrammarKB` | `analyze_verse.py` (LEGACY), `build_maani_quran_corpus_fast.py` | **No on v3 path** | Not loaded by `analyze_verse_v3`. Migrating the **engine-applicable** subset (those tagged `engine_applicability != "interpretive_note"`) to `contracts/maani/constructions/` would lift coverage without code change. |
| 7 | Maani al-Nahw — meaning_cards (1,818) | same dir | same | same | **No on v3 path** | Most carry `meaning_type="author_preference"` — likely interpretive_note, not enforceable. Sub-filter needed before any migration. |
| 8 | Maani al-Nahw — semantic_claims (5,800) | same dir | (not loaded by loader) | none | **No** | Raw extraction layer. Migration not advisable without per-claim verification. |
| 9 | Maani al-Nahw — curated_constructions.jsonl (3 rows) | same dir | `maani_kb_loader._load_curated_constructions` | LEGACY `analyze_verse.py` only | **No on v3 path** | Already curated! Trivial to expose to v3 as a complementary construction source. |
| 10 | Maani al-Nahw — operators_enriched.jsonl (102 rows) | same dir | none on v3 | none | **No** | Already joined with operators_catalog. Could serve as the bridge between SAM and NAA without re-curation. |
| 11 | NAA operators_catalog (102 rows) | `new_arabic_analyzer/data/operators_catalog_split_vocalized.csv` | none | none | **No** | Not wired into `hussein/clean_code`. See §6 for the NAA-vs-SAM overlap analysis. |
| 12 | hidden_pronouns.json (11 rows) | `new_arabic_analyzer/data/02_mabniyat/` | none | none | **No** | Tracked in the separate [hidden-pronoun SPEC](./HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md). |

### Per-layer opportunity vs current inline practice (L3–L6)

| Layer | Currently in code | Could be CSV-driven from | Risk |
|---|---|---|---|
| L3 (i3rab — word_class / case / role) | hard-coded in `i3rab_engine/layer1.py` (MASAQ + adjudication) | Vol 1 (pronoun/demo/relative meanings) for **annotation only** — not for re-classifying | Touching L3 reclassification is high risk and out of scope for any maani batch. |
| L4 (relations — `agent_of`, `patient_of`, `prep_of`, `governor_of`, …) | rule-based in `relation_extractor.py` (17 relation types) | Vol 3 (prep semantics, تَضمين), Vol 2 (فاعل/مفعول semantics) — to enrich a relation with `semantic_field` annotation, NOT to create relations | Low if read-only annotation; high if creation. |
| L5 (events — `agent`, `patient`, `time`, `manner`, …) | in `event_extractor.py` (reads RelationGraph) | Vol 4 (taqdim, tawkid, qasam, shart-fa, shart-idha → event modality flags) | Medium — flags only, no slot-changes. |
| L6 (resolution) | in `resolution_engine.py` | Vol 1 (pronoun/demo refs) — already done via implicit nodes; no real maani gap | Low — but no obvious win. |
| L7 (MeaningGraph assembly) | `meaning_assembler.py` | Per-word SAM claims could become `claim`-type nodes; topic_id could become an edge-attribute | Medium — schema change in MeaningGraph required. |

### samarrai_certified_operator_gate behavior (PATCH 4, audited in §A3)

The gate has four filtering rules over claims emitted by `samarrai_analyzer.analyze(text)`:

| Rule | Trigger | Action | Notes |
|---|---|---|---|
| **R1** Blacklist topics/meanings | topic ∈ `{QASAM_PARTICLES, QASAM_JAWAB}` or meaning_id ∈ `{WAW_QASAM, WAW_RUBBA, SIN_TANFEES_QAREEB}` | Drop unconditionally | Reason: requires oath/poetic context not in any L1 tag. |
| **R2** Prefix-required clitic topics | topic ∈ `{PREP_BA, PREP_LAM, PREP_KAF, PREP_WAW, SHART_FA_IDH}` | Require the matching letter peeled with the matching L1 prefix tag; else drop | The certified-operator concept. |
| **R3** Pronoun-suffix topics | topic = `PRONOUN`, operator is single letter ∈ `{ك, ه, ي, ن}` | Require POSS_PRON suffix; else drop | |
| **R4** Strict-form topics | topic ∈ `{SHART_IN, JAZM_LA_NAHIYA}` | Require exact NFC equality to vocalized_form (with special handling for لا inside HARF_NASB compounds like أَلَّا) | |

Anything not matched by R1–R4 is **allowed unconditionally** (default-allow). This is the biggest design point of the gate.

---

## 3. Coverage Numbers — Sample Verses (1:5, 2:196, 2:282)

Computed by calling `samarrai_analyzer.analyze(text)` then
`samarrai_certified_operator_gate.gate_text_analysis(ta)` directly
(bypassing `analyze_verse_v3` because the sandbox cannot load
`wazn_data`; v3 wraps the same two calls in `show_samarrai()` per
[lines 90–120](../../clean_code/analyze_verse_v3.py)).

| Verse (truncated to representative clause) | Words | Raw claims (non-Zero) | Kept after gate | Drop rate | Words with ≥1 claim | Constructions |
|---|---:|---:|---:|---:|---:|---:|
| 1:5 «إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ» | 4 | 6 | 3 | 50% | 2/4 (50%) | **2** (TAQDIM_AL_MA3MOOL_LI_IKHTISAS × 2) |
| 2:196 «وَأَتِمُّوا … لِلَّهِ فَإِنْ أُحْصِرْتُمْ …» | 10 | 36 | 20 | 44% | 4/10 (40%) | 0 |
| 2:282 «… الَّذِينَ آمَنُوا إِذَا تَدَايَنْتُمْ بِدَيْنٍ …» | 11 | 20 | 18 | 10% | 5/11 (45%) | 0 |

### Notable observations

1. **Coverage ceiling ≈ 45%** on Arabic prose, with 245 rules. The
   remaining 55% are non-operator nouns/verbs that SAM does not catalog
   by design — that is expected and *not* a defect.
2. **Construction detection is sparse** (2 fires across 3 verses). All
   in 1:5. This shows the `patterns.csv` (only 2 rows) is the
   bottleneck, not the detector.
3. **Gate dropped 16/36 claims in 2:196** — the dominant rejection
   was `PREP_LAM_requires_ل(PREP) in_L1_prefix_tags` on `لِلَّهِ`,
   which L1 (correctly) treats as atomic because `الله` is a protected
   lexeme. The gate is *doing the right thing*.
4. **Gate gap found:** on the same word `لِلَّهِ`, four other
   lam-topics survived (`JAZM_LAM_AMR / LAM_AMR`, `SHART_LAM_JAWAB /
   LAM_JAWAB_LAW`, `SHART_LAM_JAWAB / LAM_JAWAB_QASAM`,
   `SHART_LAM_JAWAB / LAM_IBTIDA`) — none of these topics is in the
   gate's `_PREFIX_REQUIRED` map, so the default-allow rule passed them
   through. These readings need verbal-jussive / qasam / sentence-initial
   context that L1 does not certify either. Flag as a gate extension
   candidate (see §5, Rule A2).

### Maani al-Nahw JSONL vs samarrai/constructions overlap (§B3)

`maani_alnahw/.../construction_rules.jsonl` (1,043 rows) and
`hussein/clean_code/data/contracts/maani/constructions/patterns.csv` (2
rows) are **NOT** duplicates:

- JSONL is the *auto-extracted, OCR-derived* candidate set, organised
  by `meaning_type` and `triggers.particles`. Most entries carry an
  `engine_applicability` field whose values include
  `interpretive_note`, `definitional`, and `enforceable` (a small
  subset). The format is JSON, free-form, page-anchored.
- CSV is the *curated, normalized, schema-locked* production set,
  matching `data/contracts/maani/schema.md`.

The CSV is the **production source of truth**. The JSONL is a
candidate pool. Migration of any JSONL row into the CSV is a
RULE_LOCK-gated act (one row at a time, with `confidence` and
`source_part/page` fields populated).

---

## 4. Non-Goals

This SPEC explicitly does **not** propose any of the following:

1. **No re-OCR / no re-extraction.** The JSONL pipeline is frozen.
2. **No `volume5/` directory** without an extension to
   `data/contracts/maani/schema.md` agreed upstream (currently only
   vols 1–4 are schema-locked).
3. **No replacement of i3rab corpus** (the traditional Quranic i3rab
   prose at `quran_i3rab.csv`) by maani. The two are complementary
   evidence channels: i3rab is *per-word factual*, maani is
   *operator-semantic possibility space*.
4. **No fix to ALASMA Stage 10** via maani. Word-type classification is
   governed by ALASMA's own SPECs; maani cannot reclass a token.
5. **No generic prefix-stripping heuristics in `samarrai_analyzer.py`.**
   Current `_try_strip_prefix` is the only prefix logic — extending it
   would create overmatches the gate would then have to filter back
   out. Honor the existing ProofObject/match_type contract.
6. **No merge** of the hidden-pronoun thread (separate SPEC, separate
   RULE_LOCK).
7. **No commit** of generated coverage JSONL or per-verse claim dumps.

---

## 5. Proposed RULE_LOCK — Batch A (3 L1-certified operators, 1 CSV row each)

> Goal of Batch A: prove the end-to-end loop **CSV row → samarrai_analyzer hit → gate certifies → reaches MeaningGraph as a typed node**, with **zero regression** to the existing gated display. Three rules, three words, three smoke verses. All three are operators whose certification key (L1 prefix tag) already exists in `_PREFIX_REQUIRED`.

### Rule A1 — `PREP_BA on بِدَيْنٍ (2:282)`

- **CSV row source:** `volume3/prep_ba_meanings.csv`, row `BA_ILSAQ` (الإِلصاق).
- **Trigger:** word `بِدَيْنٍ` in 2:282.
- **L1 certification:** segmenter yields `prefixes=[(ب, PREP)]` (confirmed in sandbox — see §B2 surviving claims).
- **Gate certification:** R2 fires (PREP_BA → ب + PREP). Passes.
- **New consumption:** add a `MeaningEdge(edge_type="operator_meaning", source=t<i>, target=stem_node, attributes={topic_id, meaning_id, semantic_field, source_part, source_page})` in `meaning_assembler` step 6's loop. This is the only `meaning_assembler` change.
- **Expected outcome on 2:282:** بِدَيْنٍ now contributes an `operator_meaning` edge (`BA_ILSAQ` first, alternatives in node attributes) instead of being silently consumed by the display layer.

### Rule A2 — `PREP_LAM gate extension on لِلَّهِ (2:196)` — *gate-only fix*

- **CSV row source:** none (no new row). This rule extends the **gate** (`samarrai_certified_operator_gate.py`), not the CSV data.
- **Trigger:** any claim whose topic ∈ {`JAZM_LAM_AMR`, `SHART_LAM_JAWAB`} on a word that L1 did NOT peel as `ل` with `LAM_AL_AMR` (for the first) or as `ل` with `PREP` (for the second, jawab-qasam-style lam).
- **L1 certification:** segmenter on `لِلَّهِ` yields `prefixes=[]` (atomic — الله is protected). All lam-topics on this word should therefore drop.
- **Gate certification:** **NEW** entry in `_PREFIX_REQUIRED` mapping `JAZM_LAM_AMR → (ل, {LAM_AL_AMR})` and `SHART_LAM_JAWAB → (ل, {PREP})`.
- **Expected outcome on 2:196:** the 4 false-positive lam readings on `لِلَّهِ` move to `proof_kind=Zero` with `CertifiedOperatorGate(PATCH4): topic_*_requires_ل(...)` blocker. No effect on real لِ- words.

### Rule A3 — `TAQDIM_AL_MA3MOOL_LI_IKHTISAS construction on 1:5` — *promotion to L5 modality*

- **CSV row source:** `data/contracts/maani/constructions/patterns.csv`, row `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` (already firing — see §B2 1:5 output).
- **Trigger:** existing construction match on إِيَّاكَ + نَعْبُدُ.
- **New consumption:** `meaning_assembler` step 6 already adds a construction NODE. Extend the existing nested loop (where it iterates `cm.span_words`) to *also* set an attribute on the verb's event node (when L5 exists for that token): `attributes["modality"] = "ikhtisas"`.
- **Expected outcome on 1:5:** the event corresponding to `نَعْبُدُ` carries `modality=ikhtisas` in its node attributes. Display & downstream consumers can act on it; no relation/edge schema change needed.

Three rules, three single-line changes (one CSV-driven new edge type, one new gate map entry, one event-attribute write). No new files, no schema changes, no `segmenter.py`/`i3rab_engine`/`relation_extractor`/`event_extractor`/`resolution_engine`/`alasmaa` modifications.

---

## 6. NAA vs SAM Overlap (where the two operator catalogs intersect)

Measured (§B4):

| Metric | NAA | SAM | Overlap | NAA-only | SAM-only |
|---|---:|---:|---:|---:|---:|
| Distinct operators (diac-stripped) | **92** | **109** | **29** | 63 | 80 |
| Rows | 102 | 245 | — | — | — |

**Profile of NAA-only operators (sample):**
`أصبح, أضحى, أمسى, بات, أوشك` (sister-verbs of كان), `بئس, نعم, حبذا` (verbs of praise/blame), `إلا, بله, خلا, عدا, حاشا` (exception particles), `زعمت, خلت, حسبت, رأيت` (verbs of certainty).

**Profile of SAM-only operators (sample):**
`أنا, أنت, أنتم, أنتما, إياك, إياكم, إياي…` (pronouns), `ال` (definite article), `التي, الذي` (relative pronouns), `أين, ألفى, اتخذ` (relative + transformation verbs), `أجمع` (تَوكيد).

**Profile of operators in BOTH — depth ratio (NAA readings : SAM readings):**

| Operator | NAA | SAM | Insight |
|---|---:|---:|---|
| ل | 1 | **13** | SAM is the deeper source |
| ب | 2 | **11** | SAM deeper |
| من | 2 | **9** | SAM deeper |
| ما | 2 | **5** | SAM deeper |
| إلى | 1 | **5** | SAM deeper |
| و | 3 | 3 | Tied |

**Recommendation on the NAA/SAM overlap:**

NAA and SAM are **complementary**, not duplicate. NAA is wider (verbs,
exception particles); SAM is deeper (multiple semantic readings per
operator letter). Any future RULE_LOCK that mentions NAA should:

1. Treat NAA as the authoritative **list of "is X an operator at all?"**
   for words that SAM does not cover (the 63 NAA-only entries).
2. Treat SAM as the authoritative **list of "given X is a known
   operator, what are its possible semantic readings?"** for the 29
   overlap and the 80 SAM-only operators.
3. **Never** silently override SAM with NAA on overlap (the readings
   differ in depth and granularity).

This SPEC does not propose wiring NAA into the v3 path in Batch A.
Batch B/C may do so once the overlap reconciliation is RULE_LOCKed.

---

## 7. Smoke Tests + Verification Path

### Smoke tests proposed for Batch A

| # | Verse | Word | Rule | Pre-Batch-A observation | Post-Batch-A expectation |
|---|---|---|---|---|---|
| 1 | 2:282 | `بِدَيْنٍ` | A1 | KB.SAM shows 6 ba-readings; none flow into MeaningGraph | MeaningGraph carries one `operator_meaning` edge for `BA_ILSAQ` plus alternatives in node attributes |
| 2 | 2:196 | `لِلَّهِ` | A2 | 4 lam-topics (`JAZM_LAM_AMR`, `LAM_JAWAB_LAW`, `LAM_JAWAB_QASAM`, `LAM_IBTIDA`) survive gate | All 4 become `proof_kind=Zero` with PATCH-4 blocker; surviving claim count drops from 4 to 0 on this word |
| 3 | 1:5 | `نَعْبُدُ` | A3 | Construction node present, but verb event has no modality attribute | Event for `نَعْبُدُ` carries `attributes["modality"] = "ikhtisas"` |

### Verification path (after Batch A is implemented)

`test_production_path_segmentation.py` is the binding test surface.
After Batch A, add three new tests there (in addition to the existing
26):

1. `t_2_282_bidaynin_has_operator_meaning_edge` — assembles MeaningGraph for 2:282 and asserts at least one edge with `edge_type=="operator_meaning"` and `attributes["meaning_id"]=="BA_ILSAQ"` exists.
2. `t_2_196_lillahi_lam_topics_dropped` — runs `samarrai_analyzer.analyze` + `gate_text_analysis` on `لِلَّهِ` and asserts the count of non-Zero claims with topic in `{JAZM_LAM_AMR, SHART_LAM_JAWAB}` equals zero.
3. `t_1_5_nabudu_event_has_ikhtisas_modality` — assembles MeaningGraph for 1:5 and asserts an event node corresponding to `نَعْبُدُ` carries `attributes["modality"]=="ikhtisas"`.

The pre-Batch-A baseline must run all three tests as **failing** before
Batch A is implemented (this proves the tests cover real behavior, not
the existing default). All three should turn green after the patch.

The full existing smoke command remains:
```bash
cd ~/fractal/hussein/clean_code
python3 analyze_verse_v3.py --verse 2:282 --all
python3 analyze_verse_v3.py --verse 2:196 --all
python3 analyze_verse_v3.py --verse 1:5  --all
```

Regression bars:
- The 26 existing tests in `test_production_path_segmentation.py` must all remain green.
- The gate `kept` count on each of the three sample verses must not *increase* by more than the construction node and operator_meaning edge that A1/A3 newly produce. (Numerically: A1 adds 0 kept claims on the display side because operator_meaning edges live in MeaningGraph, not in the claims list; A3 likewise. A2 *decreases* kept count on 2:196.)

---

## 8. Recommendation (single-path)

**Implement only Batch A (3 rules above) as the next maani RULE_LOCK.**

The three paths the handoff offered map as follows:

| Path the handoff proposed | Risk | Map to Batch A |
|---|---|---|
| **(1) Reporting-only:** richer `source_of_claim` in display | Lowest | Subsumed: A1 and A3 already make claims/constructions reach MeaningGraph (a stronger form of "reporting") without changing decisions. |
| **(2) Limited L4/L6 wiring** when operator is L1-certified | Medium | This **is** A1 — `PREP_BA on بِدَيْنٍ` is exactly an L1-certified operator with its CSV reading promoted into a MeaningGraph edge. |
| **(3) Wire `maani_kb_loader` into v3 behind `--maani-kb`** | Highest | **Defer**. The JSONL pipeline is voluminous (~10k items) and the engine-applicability field is not uniformly populated. Wire only after a JSONL→CSV migration policy is RULE_LOCKed. |

Path 2 (Batch A) is the right next step because:

- It exercises the existing gate (no gate code change for A1; tiny gate extension for A2).
- It produces visible enrichment in `MeaningGraph` (A1, A3) without changing any L3/L4/L5 decision.
- A2 actively *tightens* the gate where it currently leaks — clear net positive.
- It does not depend on the hidden-pronoun thread at all.
- It can be smoke-tested entirely with `samarrai_analyzer` + gate calls (the sandbox can run these standalone).

If governance prefers an even smaller first step: implement **A2 only**
(gate extension, no MeaningGraph changes). This is the lowest-risk and
shippable in a single sitting.

---

## 9. Strict boundaries respected in this discovery

- `clean_code/segmenter.py` — **not touched**
- `clean_code/i3rab_engine/*` — **not touched**
- `clean_code/relation_extractor.py` — **not touched**
- `clean_code/event_extractor.py` — **not touched**
- `clean_code/resolution_engine.py` — **not touched**
- `alasmaa/*` — **not touched**
- `clean_code/data/contracts/maani/*.csv` — **not modified** (no RULE_LOCK in this draft)
- `samarrai_analyzer.py` — **not extended** with new prefix-strip heuristics
- No large JSONL/CSV files generated or committed
- ALASMA Stage 18 — **not opened**

This SPEC is read-only investigation only. Batch A above is a *proposal*, not an implementation.
