# MAANI — Track Handoff & Expansion Vision

> **Type:** Track handoff for a new agent or session resuming MAANI work.
> **Date:** 2026-05-29
> **Status:** Batches A and B implemented. Batch B awaiting final commit approval.
> **Audience:** Any agent or contributor picking this thread up cold.

---

## 0. One-screen summary

The MAANI track wires **Samarrai's «مَعاني النَّحو»** (4 volumes, 245 curated CSV rows) into the production Arabic-analysis pipeline as a controlled, ProofObject-disciplined source of operator and construction meanings. Two batches have shipped:

- **Batch A** — surfaced Samarrai per-word operator readings as typed `samarrai_operator_meaning` edges in MeaningGraph; extended the certified-operator gate; stamped `modality="ikhtisas"` on event nodes when the TAQDIM construction fires.
- **Batch B** — converted SAM claims whose `author_position == "reported"` from `Certificate` to `Hypothesis`, honestly labeling evidence strength.

The **forward goal** is to **widen the same disciplined approach** to:
1. Phenomena Samarrai discussed but did not provide CSV rows for (كان وأخواتها, أفعال المقاربة, أفعال المدح والذمّ, تَضمين examples).
2. Phenomena beyond Samarrai but still Quranic (other classical nahw scholars: Ibn Hisham, Ibn Aqil, Suyuti).
3. Phenomena in general/MSA Arabic that have no Quranic counterpart but need consistent operator semantics for any downstream Arabic analyzer.

**The discipline does NOT change** as the scope widens. Every new row remains: schema-conformant, source-attributed (volume + page or equivalent), ProofObject-tagged, gate-filterable, and added through the SPEC → RULE_LOCK → narrow implementation → tests → smoke pipeline.

---

## 1. What is MAANI? (for an agent picking this up cold)

`hussein/clean_code/data/contracts/maani/` is a curated, schema-locked, CSV-driven knowledge base of Arabic **operator meanings** — the semantic readings of grammatical operators (حُروف الجَرّ, ضَمائر, أسماء الإشارَة, أَدَوات الشَّرط, etc.) and **constructions** (compound patterns like اختصاص / تحذير).

It is consumed by:

- `clean_code/samarrai_analyzer.py` — KB.SAM layer. Looks up each word in the corpus across all four volumes and emits `SamarraiClaim` objects (with ProofKind, source citation, confidence).
- `clean_code/samarrai_certified_operator_gate.py` — filters KB.SAM claims by cross-checking against L1 prefix/suffix tags (drops over-matches like «كاف للتشبيه» on lexical `كاتب`).
- `clean_code/meaning_assembler.py` — promotes surviving claims into MeaningGraph nodes/edges and applies construction-driven modality stamps.

It is **not** the lexicon. It is not the i3rab parser. It is the **operator-semantics layer**. Lexical word identity, grammatical role, and case are decided upstream (i3rab_engine); MAANI's job is to attach **what each operator means in context**.

### Source provenance

| Source ID in CSV | Identity |
|---|---|
| `source_part` 1–4 | السامرَّائيّ — معاني النحو (4 volumes), edition cited in the schema doc |
| `source_page` | page number within that volume |
| `author_position` | `preferred` (Samarrai's own view) or `reported` (a view he documents from others) |
| `confidence` | numeric in 0.0–1.0 |

Every claim is traceable to a specific page in a specific volume. This provenance discipline is non-negotiable as the scope widens.

---

## 2. Architectural principles (must be preserved as scope widens)

### 2.1 CSV-driven, not inline
No operator meanings live in Python. Every claim is one row in one CSV under `data/contracts/maani/**`. New phenomena → new rows (with RULE_LOCK), not new inline match conditions.

### 2.2 Per-row provenance
Every row carries `source_part`, `source_page`, `author_position`, `confidence`. When sources beyond Samarrai are added, the schema must be extended (or the convention adapted) so external scholars/sources are similarly citable. **Never** add a row whose source can't be cited to a specific page or document.

### 2.3 ProofObject discipline
Every `SamarraiClaim` carries a `proof_kind ∈ {Certificate, Hypothesis, Zero}`. Today's rules:

- `Certificate` — match_type is `exact_vocalized` AND `author_position` is not `"reported"`
- `Hypothesis` — match_type is `prefix_stripped`/`prefix_as_operator`/`pattern_construction` OR `author_position == "reported"`
- `Zero` — no match, blacklisted topic, or gate rejection

Any new source/category must declare which ProofKind tier it lives in and why.

### 2.4 Gate-based filtering
`samarrai_certified_operator_gate.py` is the **single point of L1-grounding**. It cross-checks every claim against the segmenter's actual prefix/suffix tags before the claim reaches MeaningGraph. New operators must be added to one of the existing gate rule maps (`_PREFIX_REQUIRED`, `_PRONOUN_SUFFIX_LETTERS`, `_STRICT_FORM_TOPICS`, `_NEVER_CERTIFIED_TOPICS`, `_NEVER_CERTIFIED_MEANINGS`) — never bypass the gate.

### 2.5 No broad migration
Bulk import of e.g. `maani_alnahw/.../construction_rules.jsonl` (1,043 raw extractions) is **explicitly prohibited**. Every row must pass through hand-curation + RULE_LOCK + tests. A pilot of 3–5 rows is the largest single migration unit ever attempted in one batch.

### 2.6 Author-position downgrade (Batch B contract)
The rule from Batch B is **monotonic**: it can only DOWNGRADE certainty (`Certificate → Hypothesis`), never upgrade. Future extensions of this idea must preserve monotonicity.

### 2.7 Boundary respect with concurrent tracks
MAANI work runs alongside:
- **versebyverse track** — touches `segmenter.py`, `event_extractor.py`, `relation_extractor.py`
- **MASAQ F3 track** — touches `master_token_lookup.py`, `role_rules_contract.py`, `test_production_path_segmentation.py`
- **i3rab/Stage 10–17 (ALASMA) track** — separate repo segment

A MAANI batch must touch only `samarrai_analyzer.py`, `meaning_assembler.py`, `samarrai_certified_operator_gate.py`, files under `data/contracts/maani/**`, and its own test file. Any wider edit needs cross-track coordination.

---

## 3. What is in the tree today (state as of 2026-05-29)

### 3.1 Data: `data/contracts/maani/` — 245 rows, 24 files

| Volume | Rows | Files | Coverage |
|---|---:|---:|---|
| 1 — المعارف + الإسناد | 82 | 5 | pronouns (36), demonstratives (13), relatives (14), AL definite (10), mubtada/khabar (9) |
| 2 — الأفعال + المفاعيل | 42 | 4 | فاعل/نائب فاعل (10), مفعول به + 5 special styles (8), مفعول مطلق + ظَرف (8), ظَنّ family (16) |
| 3 — حُروف الجَرّ + التَّضمين | 62 | 6 | باء (10), إلى (5), لام (8), other preps (21), supplementary (10), تَضمين definitions (8) |
| 4 — الجَزم + الشَّرط + التَّوكيد + القَسَم + التَّقديم | 57 | 8 | shart particles (13), tawkid (9), taqdim/takhir (7), qasam (7), shart constructions (7), future/amr (7), jussive particles (4), تَعَجُّب (3) |
| `constructions/patterns.csv` | **2** | 1 | TAQDIM_AL_MA3MOOL_LI_IKHTISAS, TAHZHEER_BASIC |

**Schema (19 columns):** `priority, topic_id, operator, vocalized_form, meaning_id, meaning_ar, syntactic_effect, semantic_field, conditions, exceptions, warnings, example_constructed, example_quran, surah_ayah, author_position, disagreement, source_part, source_page, confidence`.

Schema doc: `data/contracts/maani/schema.md`. No schema deviation across files.

**Author-position distribution:** 196 preferred (80.7%) · 34 reported (14.0%) · 7 empty (2.9%) · 6 corrupted-where-a-surah:ayah-string-leaked-into-author-position (2.5%).

### 3.2 Code consumption summary

- `samarrai_analyzer.py`:
  - Loads CSVs via `samarrai_loaders/volume{1..4}_loader.py`.
  - Per-word lookup via `lookup_word_all_volumes(word, match_type)`.
  - Pattern detection via `detect_constructions()` reading `constructions/patterns.csv`.
  - `best_claim` ranking uses `author_position == "preferred"` to bias selection.
  - **Batch B hook** (post-2026-05-29): inside `_lookup_in_volume`, sets `proof_kind = "Hypothesis"` when row's `author_position.strip() == "reported"`.
- `samarrai_certified_operator_gate.py` (PATCH 4 + PATCH 14):
  - Rule R1: unconditionally drops topics requiring oath context (QASAM_PARTICLES, QASAM_JAWAB) and specific meaning IDs (WAW_QASAM, WAW_RUBBA, SIN_TANFEES_QAREEB).
  - Rule R2: prefix-clitic topics require matching L1 prefix tag (PREP_BA, PREP_LAM, PREP_KAF, PREP_WAW, SHART_FA_IDH, JAZM_LAM_AMR, SHART_LAM_JAWAB).
  - Rule R3: PRONOUN topic with single-letter operator requires POSS_PRON suffix tag.
  - Rule R4: strict-form topics (SHART_IN, JAZM_LA_NAHIYA) require exact NFC equality.
- `meaning_assembler.py` (Batch A):
  - Step 6: builds construction nodes from `ta.constructions`.
  - Step 6a: stamps `modality="ikhtisas"` on verb event node when TAQDIM construction fires.
  - Step 6b: emits `edge_type="samarrai_operator_meaning"` edges for surviving claims whose topic is in `{PREP_BA, PREP_KAF, PREP_LAM, PREP_WAW}`.

### 3.3 Tests

- `test_production_path_segmentation.py` carries existing PATCH-1 through PATCH-15 tests including PATCH 14 MAANI A2 gate tests.
- `test_maani_batch_b_author_position.py` carries Batch B's 6 unit + acceptance tests.

### 3.4 Other source documents

- `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md` — original SPEC (Batch A planning).
- `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md` — binding contract for Batch A.
- `docs/specs/MAANI_BATCH_A_REPORT.md` — Batch A implementation report.
- `docs/specs/HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md` — sibling thread, separate RULE_LOCK pending.
- This file: `docs/specs/MAANI_EXPANSION_HANDOFF.md`.

### 3.5 Related but distinct resources

- `maani_alnahw/data/processed/maani_alnahw/` — raw OCR pipeline output from Samarrai's volumes:
  - `construction_rules.jsonl` (1,043 rows, raw extractions, NOT migrated)
  - `meaning_cards.jsonl` (1,818 rows, mostly `interpretive_note`)
  - `semantic_claims.jsonl` (5,800 rows, raw)
  - `curated_constructions.jsonl` (3 rows, hand-curated)
  - `operators_enriched.jsonl` (102 rows, joined with NAA's operators_catalog)
- `new_arabic_analyzer/data/operators_catalog_split_vocalized.csv` — NAA's operator catalog (102 rows, 92 distinct operators). Broader-but-shallower than SAM. **Not wired** into hussein/clean_code.
- `new_arabic_analyzer/data/02_mabniyat/hidden_pronouns.json` — 11 teaching examples. **Not wired**.

---

## 4. What Batch A delivered (already committed)

**Commit:** `ad59eaa Document MAANI Batch A rule lock and report` and earlier MAANI/PATCH commits.

### 4.1 A1 — `samarrai_operator_meaning` edge in MeaningGraph
Inside `meaning_assembler.assemble()` step 6, after the certified-operator gate filters claims, iterate `ta.words[i].claims` and emit one new `MeaningEdge(edge_type="samarrai_operator_meaning")` per surviving claim whose `topic_id ∈ {PREP_BA, PREP_KAF, PREP_LAM, PREP_WAW}`. `source==target` self-attribution convention. Carries the claim's `proof_kind` (which after Batch B may be Hypothesis for reported rows).

### 4.2 A2 — Gate extension
In `samarrai_certified_operator_gate.py`, added two entries to `_PREFIX_REQUIRED`:
- `JAZM_LAM_AMR → (ل, {LAM_AL_AMR})`
- `SHART_LAM_JAWAB → (ل, {PREP})`

Effect: `لِلَّهِ` (which L1 keeps atomic because الله is a protected lexeme) no longer leaks JAZM/JAWAB lam-readings into the display layer.

### 4.3 A3 — Ikhtisas modality
When the construction match has `construction_id == "TAQDIM_AL_MA3MOOL_LI_IKHTISAS"`, the verb event node at `span_words[1]` is stamped with `attributes["modality"] = "ikhtisas"` plus a `modality_source` citing volume/page.

---

## 5. What Batch B delivered (staged but not yet committed at handoff time)

### 5.1 The rule
Inside `_lookup_in_volume` in `samarrai_analyzer.py`:

```python
row_author = (rec.get("author_position", "") or "").strip()
row_proof_kind = "Hypothesis" if row_author == "reported" else proof_kind
```

`proof_kind` here is the value previously computed from `kind_for_match_type(match_type)`. Batch B only DOWNGRADES Certificate→Hypothesis for reported rows; preferred / empty / em-dash / corruption all fall through unchanged.

### 5.2 Verified counts on real data

- 196 `preferred` rows → Certificate (unchanged)
- **34 `reported` rows → Hypothesis** (the rule's targets)
- 7 empty/em-dash rows → Certificate (fail-open)
- 6 corruption rows (surah:ayah strings that landed in author_position by CSV error) → Certificate (fail-open; deliberately NOT repaired in this batch)

### 5.3 What Batch B did NOT change
- `best_claim` ranking (still prefers preferred)
- `samarrai_certified_operator_gate` (unchanged)
- `meaning_assembler` (unchanged; the edge inherits the new proof_kind through Batch A's existing wiring)
- The 6 corrupted rows (data hygiene is a separate batch)
- Any L1/L3/L4/L5/L6 module

### 5.4 Files staged at handoff time
- `clean_code/samarrai_analyzer.py` — 13-line hook
- `clean_code/test_maani_batch_b_author_position.py` — 250-line new test file

---

## 6. The broader vision — widen the impact

### 6.1 Why widen at all?

Samarrai's 245 curated rows are excellent for what they cover, but the **operator-semantics layer** as a whole has structural gaps that any production-quality Arabic analyzer must address:

- A reader of Quran 19:24 (`فَنَادَىٰهَا مِن تَحْتِهَا أَلَّا تَحْزَنِي`) needs to understand that `أَلَّا` here is `أَنْ + لا` (تَفسيريّة) — a construction Samarrai may discuss but for which no CSV row currently exists.
- A reader of a modern Arabic news article uses operators like `حَسْب` («according to»), `بِناءً عَلى` («based on»), `وَفْقاً لـ` («in accordance with») — operator phrases never used in Quran, never indexed by Samarrai, but critical for any general Arabic analyzer.
- A reader of classical poetry encounters operator usages (e.g. `إِذَن` as a connector, particular uses of `لَوْ`) that Ibn Hisham and other classical scholars discussed but Samarrai abbreviated.

**The vision:** treat Samarrai as the *canonical seed* and widen the same disciplined approach (schema-conformant rows, ProofObject discipline, per-row provenance, gate filtering, RULE_LOCK gating) to:

1. **Phenomena Samarrai discussed but did not enter as CSV rows** — recover them from his book pages via `maani_alnahw/.../*.jsonl` with hand curation.
2. **Phenomena in classical Arabic Samarrai did not cover** — pull from other classical sources with attribution.
3. **Phenomena in modern/MSA Arabic** — add a parallel volume with its own provenance convention (modern grammar reference works, journalistic-corpus-derived patterns).
4. **Cross-source disagreement modeling** — when Samarrai's `preferred` view conflicts with Ibn Hisham's, both readings carry ProofKind=Hypothesis with provenance, and the assembler can surface the conflict.

### 6.2 Why the approach generalizes cleanly

The MAANI approach has four ingredients that are not tied to Quran or to Samarrai:

| Ingredient | Why it generalizes |
|---|---|
| **19-column schema** | Already supports `source_part`/`source_page` — extend to `source_author`, `source_corpus`, or use `source_part` as a structured reference. |
| **ProofObject discipline** | Certificate / Hypothesis / Zero is independent of the source. Any new source declares its Certificate threshold. |
| **Gate cross-check** | The gate cross-checks L1 prefix/suffix tags, not Samarrai-specific signals. Any new operator works the same way. |
| **MeaningGraph edge** | `samarrai_operator_meaning` is a name; it could become `operator_meaning_v2` with a `source_school` attribute. |

---

## 7. Coverage map — what Samarrai covers vs what's missing

### 7.1 Covered well (the strong areas)

- **Prepositions** — every common preposition has 5–13 readings (ب: 10, ل: 8, مِن: 7, إلى: 5, etc.).
- **Pronouns** — 36 rows cover all forms × person × number × subject/object.
- **Conditional particles** — 13 rows, one per particle (إن, مَن, ما, متى, أين, أنّى, …).
- **Demonstratives** — 13 rows including dual-addressee forms.
- **Relative pronouns** — 14 rows including reduced/elided forms.
- **التَّوكيد** — 9 rows covering معنويّ, لفظيّ, nun, قد.
- **القَسَم** — 7 rows for particles + جواب القسم.
- **التَّقديم/التَّأخير** — 7 rows including the famous «إِيَّاكَ نَعْبُدُ» اختصاص construction.

### 7.2 Discussed but not in CSV rows (recoverable from Samarrai's pages)

- **كان وأخواتها** — Samarrai covers these in volume 2 prose; no CSV rows. أصبح، أمسى، أضحى، ظلّ، بات، صار، لَيْسَ.
- **أفعال المُقارَبَة** — كاد, عَسى, أَوْشَك. Discussed in volume 2; no rows.
- **أفعال المَدْح والذَّمّ** — نِعْم, بِئْس, حَبَّذا, لا حَبَّذا. Discussed; no rows.
- **التَّضمين examples** — `tadmin_and_policy.csv` has 6 definitions + 2 policies but **zero practical matchable examples** (which verb takes which preposition's meaning in which context). Samarrai's volume 3 is full of examples; they need extraction + curation.
- **More construction patterns** — `maani_alnahw/.../construction_rules.jsonl` has 1,043 raw OCR extractions. Most are mid-quality, but a hand-picked subset (estimated 30–80 patterns) is genuinely production-ready.

### 7.3 Beyond Samarrai but still classical Arabic

- **Ibn Hisham** (المُغْنيّ اللَّبيب) — encyclopedic operator dictionary; ~700 entries, many overlap with Samarrai with finer distinctions.
- **Ibn Aqil** — pedagogical organization of Alfiyya; different emphasis.
- **As-Suyuti** (الإِتقان) — Quran-specific operator usage with cross-verse comparisons.
- **Ar-Radhi** (شَرح الكافِيَة) — heavy on disagreement modeling, ideal for populating the `disagreement` column.

### 7.4 General/MSA Arabic operators not covered by classical nahw

- **Compound prepositions:** بِناءً عَلى, وَفْقاً لـ, اِستِناداً إلى, نِسبَةً إلى, خِلافاً لـ, عَلى عَكس.
- **Discourse connectors:** عِلاوَةً عَلى ذلِك, مِن جِهَةٍ أُخرى, بِالإِضافَة إلى ذلِك, عَلى الرَّغم مِن.
- **Modern conditionals:** إذا ما, لَو لا أَنّ, في حال أَنّ.
- **Modal expressions:** مِن المُحتَمَل أَنْ, لا بُدَّ مِن أَنْ, يَجِب عَلى, يَنبَغي.
- **Periphrastic structures from translation Arabic:** قام بِـ + maṣdar, يَتِمّ + maṣdar.

These are not in Samarrai (he wrote about classical Arabic). They are in everyday Arabic text. A general Arabic analyzer needs them.

---

## 8. Proposed expansion vectors (in safety order)

Each vector is described as: **scope**, **safety**, **risk**, **suggested batch unit**, and **RULE_LOCK template**.

### Vector V1 — author_position downgrade extensions
**Scope:** Add per-claim suppression (Zero, not just Hypothesis) for `author_position == "rejected"` if/when such rows exist. Currently the schema enum doesn't include "rejected" — Samarrai's `author_position` only has `preferred` and `reported`. But future sources might.
**Safety:** Highest (mirrors Batch B mechanism exactly).
**Risk:** Low.
**Suggested unit:** Per-value extension (one batch per new author_position value).

### Vector V2 — Conditions/exceptions consumption (gradual, structured)
**Scope:** The `conditions` and `exceptions` columns are 90% / 24% populated but prose. Build a SMALL structured matcher CSV (`data/contracts/maani/conditions_matchers.csv`) that maps prose phrases to matchable tests. Examples:
- "أَن يَتَّصِل المَجرور بِالفِعل" → `condition_id="ATTACHED_TO_VERB"`, `matcher="surface_window:verb_within_3"`.
- "بَعد فِعل أَو مَعنى قَسَم" → `condition_id="AFTER_OATH_SIGNAL"`, `matcher="topic_in_prev_3:QASAM_*"`.

Then a per-claim condition check at SamarraiClaim build time: if `condition_id` doesn't fire, downgrade to Hypothesis.
**Safety:** Medium — requires a new schema + matcher layer.
**Risk:** Medium — prose parsing risk if matchers are too lax.
**Suggested unit:** Per topic family (e.g. Batch C = PREP_BA conditions only, 10 rows mapped).

### Vector V3 — Construction migration pilot
**Scope:** Hand-pick 3–5 construction patterns from `maani_alnahw/.../construction_rules.jsonl` (1,043 candidates) and add them to `data/contracts/maani/constructions/patterns.csv` (currently 2 rows). Candidates:
- إِيَّا + اسم لِلتَّحذير (`TAHZHEER_DISTANT_OBJECT` — different from current `TAHZHEER_BASIC`)
- مفعول مقدّم بِـ إِنَّما (`HASR_INNAMA`)
- أن المصدريّة + فعل (`MASDAR_MUAWWAL`)
**Safety:** Medium.
**Risk:** Medium — new constructions can fire on unintended sequences.
**Suggested unit:** 3–5 patterns per batch, each with golden verse + reject case.

### Vector V4 — كان وأخواتها rows
**Scope:** Add 7 rows for كان, أصبح, أمسى, أضحى, ظلّ, بات, صار, لَيْسَ to a new file `volume2/kana_sisters_meanings.csv`. Each row carries one اِسم raising + خبر nasb relation pattern. Samarrai discusses these in volume 2 pages X–Y (to be confirmed from his book; or pulled from `maani_alnahw/.../meaning_cards.jsonl`).
**Safety:** Medium.
**Risk:** Medium — these interact with the i3rab pipeline's existing handling of nominal vs verbal sentences.
**Suggested unit:** One batch = one new file + ~8 rows + 1 new construction node `KANA_FAMILY_TOPIC_OF`.

### Vector V5 — أفعال المُقارَبَة
**Scope:** كاد, عَسى, أَوْشَك, طَفِق, جَعَل (as inceptive), أَخَذ (as inceptive). Three rows per verb (active, with خبر فِعل مضارع, with خبر مرفوع), so ~18 rows.
**Safety:** Medium.
**Risk:** Medium — كاد polysemy is hard.
**Suggested unit:** One new file `volume2/approximation_verbs.csv`.

### Vector V6 — أفعال المَدْح والذَّمّ
**Scope:** نِعْم, بِئْس, حَبَّذا, لا حَبَّذا. ~6 rows.
**Safety:** Medium.
**Risk:** Low — these have very stable surface patterns.
**Suggested unit:** One new file `volume2/praise_blame_verbs.csv`.

### Vector V7 — Tadmin practical examples
**Scope:** Add 10–20 rows to `volume3/tadmin_and_policy.csv` of the form «verb X here is تَضمين of meaning Y». Each row identifies one verb + one preposition combination that classically signals تَضمين, with a Quranic example. E.g. «اِشْتَرَوْا الضَّلَالَةَ بِالْهُدَى» — `اِشتَرى` is `تَضمين` of `اِستَبدَل`, triggered by `بِ + thing-replaced` pattern.
**Safety:** Medium — depends on accurate تَضمين identification.
**Risk:** Medium.
**Suggested unit:** Per verb family (Batch X = اِشتَرى family, 5 rows; Batch Y = آمَنَ family, 5 rows).

### Vector V8 — author_position extension to other sources
**Scope:** Add a new column `source_school ∈ {samarrai, ibn_hisham, ibn_aqil, suyuti, modern, …}` to the schema. Migrate existing rows with `source_school=samarrai`. New rows from other classical scholars use their school name. Multi-school agreement on a meaning_id increases `confidence`; disagreement adds rows to `disagreement` column.
**Safety:** Lower — schema change.
**Risk:** Higher — affects every loader, every consumer.
**Suggested unit:** Two batches — (Batch X = schema extension + migration of existing 245 rows; Batch Y = first cross-source addition, e.g. 10 Ibn Hisham rows).

### Vector V9 — MSA / general Arabic volume
**Scope:** New top-level folder `data/contracts/maani/modern/` containing rows for compound prepositions and discourse connectors. Schema same as classical (with `source_part="modern"` or new `source_school="modern"`).
**Safety:** Lower — entirely new category.
**Risk:** Higher — needs a modern Arabic provenance convention (which reference grammar? whose authority?).
**Suggested unit:** One batch per phrase family (compound preps: ~30 rows; discourse connectors: ~25 rows; modals: ~20 rows).

### Vector V10 — NAA operators_catalog reconciliation
**Scope:** The NAA `operators_catalog_split_vocalized.csv` (102 rows, 92 distinct operators) is broader-but-shallower than SAM. 63 operators are NAA-only (mostly verbs SAM doesn't cover). RULE_LOCK + migrate the 63 NAA-only operators into `data/contracts/maani/` as new rows with `source_part="naa_operators_catalog"`.
**Safety:** Medium — NAA's curation quality is consistent.
**Risk:** Medium — may surface SAM-vs-NAA disagreements for the 29 overlap operators (in a future batch).
**Suggested unit:** One batch per category (e.g. exception particles batch, sister-verbs batch).

### Vector V11 — Beyond-Samarrai pages from `maani_alnahw` JSONL (curated subset)
**Scope:** Hand-pick the ~30–80 `meaning_cards.jsonl` rows tagged `engine_applicability != "interpretive_note"`. Each picked row gets a RULE_LOCK and becomes a CSV row.
**Safety:** Medium — depends on curation quality.
**Risk:** Medium.
**Suggested unit:** 5 rows per batch (so each row gets serious review).

---

## 9. Hard constraints that survive the widening

### 9.1 Never broaden these (constitutional)
- ALASMA Stages 10–17 are governed by their own SPECs and RULE_LOCKs. **No MAANI batch may touch them.**
- The hidden-pronoun thread (`HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md`) is separate. Different RULE_LOCK.
- Phase 5 ClauseGraph integration is separate.
- The Balagha / Rhetorical layer (e.g. ردّ العجز على الصدر) is **explicitly deferred** to a future track with its own SPEC. Never include in a MAANI batch.

### 9.2 Never do these even within MAANI
- No inline data in code. Ever.
- No bulk migration. Ever. (Hard ceiling: 5 rows per batch unless the schema is being extended.)
- No fuzzy matching of `author_position` or any other field. Exact-match only.
- No data repair of corrupted rows during a code-batch. Hygiene is a separate batch.
- No upgrading of ProofKind. Only downgrading (per Batch B's monotonicity rule).
- No new `proof_kind` value beyond the existing enum without a schema-extension batch.

### 9.3 Always coordinate with concurrent tracks
- Check `git log` for recent activity on:
  - `clean_code/segmenter.py` (versebyverse)
  - `clean_code/master_token_lookup.py` (MASAQ F3)
  - `clean_code/role_rules_contract.py` (MASAQ F3)
  - `clean_code/event_extractor.py` / `relation_extractor.py` (versebyverse)
- Check `git status` for in-flight (uncommitted) work in these files before starting a MAANI batch.
- If any of these files have uncommitted work from another track, postpone the MAANI batch — even if MAANI wouldn't directly touch them, they may be involved in MAANI's downstream tests.

---

## 10. Open questions for the next agent

1. **Schema extension for non-Samarrai sources** — is a new `source_school` column the right move, or should `source_part` be repurposed as a structured reference (`"samarrai:3"`, `"ibn_hisham:1.45"`, `"modern:al_najjar.78"`)?
2. **Cross-source disagreement representation** — when Samarrai's preferred view conflicts with Ibn Hisham's, do we:
   - Emit two SamarraiClaim objects (one per source) for the same operator, OR
   - Emit one claim with disagreement populated and let the assembler render a contradiction node?
3. **MSA volume provenance convention** — what's the citation form for modern Arabic? Page from a specific grammar (e.g. النَّحو الوافي للنَّجَّار)? Or corpus-derived patterns with frequency tags?
4. **MeaningGraph edge naming when source diversifies** — keep `samarrai_operator_meaning` for backward compat? Add `operator_meaning_v2` with a `source_school` attribute?
5. **Conditions matcher language** — when V2 (conditions/exceptions consumption) is opened, what's the matcher DSL? CSV-based atomic predicates? Or a tiny embedded language?
6. **Test infrastructure scaling** — `test_production_path_segmentation.py` is now 2000+ lines and shared by multiple tracks. Should MAANI move to per-batch test files (already started with Batch B)?

These should be answered in a SPEC before the relevant vector is opened.

---

## 11. The standing pipeline (preserve as scope widens)

Every batch, regardless of which vector, follows:

1. **SPEC** — `docs/specs/MAANI_<batch_name>_SPEC_DRAFT.md` describing scope, motivation, rows-to-add, allowed/forbidden files, non-goals.
2. **Review + approval** — user (or governance) approves the SPEC.
3. **RULE_LOCK** — `docs/specs/MAANI_<batch_name>_RULE_LOCK.md` with binding scope, exact files, exact tests, acceptance/rejection/rollback.
4. **Narrow implementation** — only the allowed files, only the rule.
5. **Tests** — at minimum 3 tests (one positive, one negative, one fail-open if applicable).
6. **243-row acceptance** (or whatever the new count becomes) — verify ProofKind distribution.
7. **Regression check** — `test_production_path_segmentation.py` must remain at or above its current pass count, modulo the known sandbox flake.
8. **Report** — `docs/specs/MAANI_<batch_name>_REPORT.md` with what was done, evidence, and any deferred items.
9. **Commit approval gate** — user approves the commit hash, NOT just the patch.

Skipping any step → batch is rejected.

---

## 12. Recommended next batch (if you resume cold)

**Default recommendation:** if Batch B has been committed and you need the next safest, highest-value step, pick **Vector V4 — كان وأخواتها**.

Why:
- Single CSV file addition (`volume2/kana_sisters_meanings.csv`).
- ~7–8 rows total.
- Samarrai's prose is available in volume 2 pages, so provenance is clean.
- These operators are central to Arabic syntax — high downstream impact.
- The gate already has a slot pattern (PREP_*) that can be extended to a new family without redesigning the gate.

If Batch B is **not** committed yet, do NOT open a new batch. Wait for commit, then re-check git state, then proceed.

**Alternative:** if you prefer a lower-risk step than V4, pick **Vector V1** (extending Batch B's mechanism for any new `author_position` enum value when one appears) — but only if there's a new value to handle. If `author_position` is still binary, V1 has no work to do.

---

## 13. Quick-reference: where to look

| Question | File / Path |
|---|---|
| Schema spec | `data/contracts/maani/schema.md` |
| Raw OCR pipeline (Samarrai book) | `maani_alnahw/data/processed/maani_alnahw/*.jsonl` |
| Samarrai analyzer (loads claims) | `clean_code/samarrai_analyzer.py` |
| Gate (filters claims) | `clean_code/samarrai_certified_operator_gate.py` |
| MeaningGraph builder | `clean_code/meaning_assembler.py` |
| MeaningGraph schema | `clean_code/meaning_graph.py` |
| Volume loaders | `clean_code/samarrai_loaders/volume{1..4}_loader.py` |
| Construction patterns | `data/contracts/maani/constructions/patterns.csv` |
| Batch A SPEC | `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md` |
| Batch A RULE_LOCK | `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md` |
| Batch A report | `docs/specs/MAANI_BATCH_A_REPORT.md` |
| Batch B test file | `clean_code/test_maani_batch_b_author_position.py` |
| Production-path integration tests | `clean_code/test_production_path_segmentation.py` |
| Hidden-pronoun sibling thread | `docs/specs/HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md` |
| NAA operators catalog | `new_arabic_analyzer/data/operators_catalog_split_vocalized.csv` |
| Quranic i3rab corpus | `new_arabic_analyzer/data/quran/quran_i3rab.csv` |

---

## 14. The principle in one sentence

**Treat every Arabic operator and construction as a row in a CSV with traceable provenance, gate it against L1 segmentation, and let the MeaningGraph carry an honest ProofKind — extend the cast (Samarrai → other classical scholars → modern Arabic) without changing the discipline.**

That is what Batches A and B established. That is what every future MAANI batch should preserve.
