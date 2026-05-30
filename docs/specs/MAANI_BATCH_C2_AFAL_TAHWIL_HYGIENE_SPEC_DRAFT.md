# MAANI Batch C₂ — AFAL_TAHWIL Hygiene & Migration — SPEC DRAFT

> **Type:** SPEC draft (not RULE_LOCK).
> **Date:** 2026-05-30
> **Status:** Draft pending review. No implementation. No RULE_LOCK yet.
> **Source restriction:** Samarrai only. No external scholars. No modern Arabic.
> **Supersedes (for implementation purposes):** `MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (commit `6d91650`) and `MAANI_BATCH_C_AFAL_TAHWIL_RULE_LOCK.md` (commit `e1474ab`). Those documents remain in git history as historical artifacts of the aborted non-migration Batch C; this SPEC and the RULE_LOCK that will derive from it are the new binding chain.

---

## 0. Why this document exists

The original MAANI Batch C (SPEC `6d91650`, RULE_LOCK `e1474ab`) framed AFAL_TAHWIL as a **pure addition**: a new CSV (`transform_verbs_meanings.csv`) holding 4 rows for the transformation verbs (framework + جَعَلَ + اِتَّخَذَ + صَيَّرَ), with the existing `zann_family_meanings.csv` explicitly forbidden from modification (§3.6 of the prior RULE_LOCK).

That implementation was completed and tested (9/9 Batch C tests + 6/6 Batch B + 158/158 production), then **discarded before commit** when implementation surfaced a discovery that invalidates the addition-only premise.

**The discovery:** `zann_family_meanings.csv` already contains four transformation-verb rows that the prior Batch C re-introduces under a parallel `topic_id`:

| Operator | Existing row in `zann_family_meanings.csv` | Prior Batch C row in `transform_verbs_meanings.csv` |
|---|---|---|
| جَعَلَ | `JAALA_VERB` (ZANN_FAMILY, preferred, 2/26, conf 0.92) — meaning_ar: *«جَعَلَ مِن أَفعال التَّحويل — تَنصِب مَفعولَين»* | `AFAL_TAHWIL_JAAL` (AFAL_TAHWIL, preferred, 2/26, conf 0.93) |
| اتَّخَذَ ↔ اِتَّخَذَ | `ITTAKHADHA_VERB` (ZANN_FAMILY, preferred, 2/26, conf 0.92) — vocalized *without* initial kasra | `AFAL_TAHWIL_ITTAKHATHA` (AFAL_TAHWIL, preferred, 2/26, conf 0.93) — vocalized *with* initial kasra |
| صَيَّرَ | `SAYYARA_VERB` (ZANN_FAMILY, **reported**, 2/26, conf 0.9) — meaning_ar: *«صَيَّرَ مِن أَفعال التَّحويل المَحضَة»* | `AFAL_TAHWIL_SAYYARA` (AFAL_TAHWIL, **preferred**, 2/26, conf 0.93) |
| تَرَكَ | `TARAKA_TRANS` (ZANN_FAMILY, reported, 2/26, conf 0.88) — meaning_ar: *«تَرَكَ مِن أَفعال التَّحويل بِمَعنى صَيَّرَ»* | (deferred in prior Batch C — not in the 4-row set) |

Three operators were duplicated outright. A fourth (`تَرَكَ`) was deferred but already classified as a transformation verb under ZANN_FAMILY. One pair (`صَيَّرَ`) carries **contradictory `author_position`** between the two sources — `reported` (→ Hypothesis) in ZANN vs `preferred` (→ Certificate) in the new file — about Samarrai's *own* stance, the same scholar cited in both rows from the same vol-2/p-26 source range.

This is a direct violation of the project invariant **«لا تخزّن ما تستطيع توليده»** (do not duplicate curated facts). The discovery is structural, not cosmetic: the prior Batch C scope cannot satisfy the invariant because its RULE_LOCK forbids editing `zann_family_meanings.csv`, which is where the duplicates live.

**Batch C₂ exists to fix this.** It reframes the work as a **migration / data-hygiene batch**: transformation verbs are removed from `zann_family_meanings.csv` and re-homed in `transform_verbs_meanings.csv`, leaving the ZANN file as the canonical home for cognition-family rows only.

---

## 1. Core invariant (binding)

> **لا تخزّن ما تستطيع توليده** — *Do not duplicate curated facts.*

Operationalized for Batch C₂:

1. **One operator + one semantic family ⇒ one row.** No operator may carry transformation-class claims under two `topic_id`s simultaneously.
2. **If a claim already exists, migrate it; do not re-encode it.** Adding a new `AFAL_TAHWIL_X` row for an operator that already has a transformation-classified ZANN_FAMILY row requires removing the ZANN_FAMILY row in the same batch.
3. **Honesty in `author_position`.** If the existing row carried `reported`, the migrated row must carry `reported` too (which downgrades to Hypothesis per Batch B). The migration must not silently upgrade Samarrai's position. If the curator believes `preferred` is more accurate, that re-curation is a *separate* decision documented as a `disagreement` field entry, not a quiet flip.
4. **Provenance preserved.** `source_part`, `source_page`, and `confidence` of the migrated row must match the source row's values (not the rule card's defaults) unless the SPEC explicitly justifies a divergence in §6.

The RULE_LOCK that will derive from this SPEC must encode invariant (1) as a binding test gate and (3) as a binding migration rule.

---

## 2. What was discarded

For traceability: the prior Batch C implementation (now reverted) consisted of three uncommitted changes that were discarded as one unit on 2026-05-30:

| File | Status before discard | Action |
|---|---|---|
| `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` | Untracked (5 lines, 4 rows) | Deleted |
| `clean_code/test_maani_batch_c_afal_tahwil.py` | Untracked (9 tests, all passing) | Deleted |
| `clean_code/samarrai_loaders/volume2_loader.py` | Modified (+1 line: `("transform_verbs", "transform_verbs_meanings.csv")`) | Restored via `git restore` |

Working tree returned to commit `e1474ab` + only `.claude/` untracked. The audit, the row designs, the test patterns, and the loader investigation findings are not lost — they all transfer directly into the Batch C₂ work (see §6, §10, §11).

---

## 3. Reference-impact audit (read-only, done before this SPEC)

Before scoping the migration, the four duplicate `meaning_id`s (`JAALA_VERB`, `ITTAKHADHA_VERB`, `SAYYARA_VERB`, `TARAKA_TRANS`) were grep'd across the repo.

| Location | Reference type | Migration impact |
|---|---|---|
| `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` | Source rows (the 4 rows themselves) | **In-scope to remove.** This is what the migration changes. |
| `clean_code/data/samarrai_sweep/per_word.csv` | ~80+ references — every Quranic word that matched one of the four rows | **Generated artifact.** Regenerable from the source CSVs; out-of-date until the sweep is rerun. SPEC must decide whether the sweep is re-run inside Batch C₂ or deferred (§7.4). |
| `clean_code/data/samarrai_sweep/top_topics.csv` | Topic count summary | **Generated artifact.** Same treatment as `per_word.csv`. |
| `clean_code/TESTS.md` | Documentation mention | Read-only doc; not edited in Batch C₂ unless it asserts row counts that would regress (verify in §10 investigation). |
| `clean_code/RULES.md` | Documentation mention | Same. |
| Other `*.py` files | **Zero references** | **No Python code depends on these meaning_id strings.** Critical finding — the migration is data-only at the runtime layer. |
| Other `*.csv` source files | None (outside `samarrai_sweep`) | Clean. |

**Implication for scope:** the migration touches at most four files: the existing ZANN CSV (remove 3 or 4 rows), the new transform-verbs CSV (add the framework + the migrated rows), `volume2_loader.py` (one-line file-list entry if needed), and the test file. The two `samarrai_sweep` artifacts are generated outputs and are handled per §7.4.

---

## 4. Scope of Batch C₂

### 4.1 In scope (binding)

1. **Remove transformation-classified rows from `zann_family_meanings.csv`.** The three duplicates and (per §4.3 decision) optionally `TARAKA_TRANS`.
2. **Create `transform_verbs_meanings.csv`** as the single home for the AFAL_TAHWIL topic.
3. **Add a framework row** for AFAL_TAHWIL (`AFAL_TAHWIL_BASIC`).
4. **Migrate the 3 (or 4) transformation operators** into the new file under `topic_id = AFAL_TAHWIL`, preserving each row's `author_position` honestly.
5. **One-line loader edit** to `volume2_loader.py` if and only if investigation (§10) proves the loader does not auto-discover the new CSV.
6. **New test file** `test_maani_batch_c2_afal_tahwil_hygiene.py` enforcing the invariant and the migration mapping.
7. **Hygiene of generated artifacts** per §7.4.

### 4.2 Operators in scope

| Operator | Existing row | Decision |
|---|---|---|
| جَعَلَ | `JAALA_VERB` | **Migrate.** Remove from ZANN file; re-home as `AFAL_TAHWIL_JAAL`. |
| اِتَّخَذَ | `ITTAKHADHA_VERB` | **Migrate.** Remove from ZANN file; re-home as `AFAL_TAHWIL_ITTAKHATHA`. *Vocalization decision:* see §6.3 — RULE_LOCK must pick a single canonical vocalized form (existing `اتَّخَذَ` without initial kasra vs new `اِتَّخَذَ` with initial kasra). |
| صَيَّرَ | `SAYYARA_VERB` | **Migrate.** Remove from ZANN file; re-home as `AFAL_TAHWIL_SAYYARA`. *`author_position` carried as-is (`reported` → Hypothesis); upgrade to `preferred` is a separate re-curation decision (§5).* |
| تَرَكَ | `TARAKA_TRANS` | **Open — RULE_LOCK to decide.** See §4.3. Recommended: migrate, because deferring while leaving the existing ZANN row in place would leave a latent cross-classification (تَرَكَ classified as transformation under ZANN). The SPEC's preferred outcome is migration with the row's `author_position="reported"` preserved. |

### 4.3 Open decision: scope-creep risk vs hygiene completeness

The strict reading of the prior Batch C scope said "exactly 3 verbs: جَعَلَ + اِتَّخَذَ + صَيَّرَ." The pragmatic reading says "all four ZANN_FAMILY rows that are actually classified as transformation should move together — leaving تَرَكَ behind perpetuates the duplication problem in a different shape."

**SPEC preference:** include `تَرَكَ` in the migration. Rationale:
- The ZANN row's own meaning_ar (*«تَرَكَ مِن أَفعال التَّحويل بِمَعنى صَيَّرَ»*) self-classifies it as transformation.
- The rule card `AFAL_AL_TAHWIL__P2_001` lists تَرَكَ in its `lemmas`.
- Leaving it behind requires a follow-up Batch C₃, defeating the hygiene goal.
- Migration is a single-row reshuffle, not new content.

**RULE_LOCK to decide:** 3-verb migration (strict, matches old scope) vs 4-verb migration (complete hygiene, SPEC preference). Either way, the framework row is added.

### 4.4 Out of scope (deferred — RULE_LOCK must enforce as forbidden)

- **Remaining transformation verbs from the rule card** that have **no existing ZANN row**: `رَدَّ`, `تَخِذَ`, `وَهَبَ`. Deferred. Cannot be added in Batch C₂ because Batch C₂ is hygiene + migration, not expansion. A follow-up SPEC may add them later.
- **كان وأخواتها** (copular family — Vector V4 in the handoff).
- **أفعال المُقارَبَة** (V5).
- **أفعال المَدْح والذَّمّ** (V6).
- **التَّضمين practical examples** (V7).
- **Bulk migration of `construction_rules.jsonl`** (V3).
- **Bulk migration of `meaning_cards.jsonl`** (V11).
- **External classical scholars** (Ibn Hisham, Ibn Aqil, Suyuti, Ar-Radhi — V8 / V9).
- **Modern Arabic operators** (V9).
- **NAA reconciliation** (V10).
- **MeaningGraph edge whitelist extension to include AFAL_TAHWIL** — separate batch with smoke evidence.
- **Schema extension for `source_school`** — separate schema batch.
- **Re-curation of any other `reported` rows** in the existing MAANI corpus — separate hygiene batch.
- **Schema change** of any kind. The 19-column schema is locked.
- **ProofKind enum change** — `{Certificate, Hypothesis, Zero}` is locked.

### 4.5 What ZANN_FAMILY becomes after migration

After Batch C₂, `zann_family_meanings.csv` holds **only cognition-family rows**:

- Framework row `ZANN_BASIC` *(retain — it covers cognition verbs)*
- ظَنَّ, حَسِبَ, خَالَ, زَعَمَ, عَلِمَ, رَأَى, وَجَدَ, أَلْفَى, دَرَى *(rows 2–10 — retain)*
- ~~JAALA_VERB, ITTAKHADHA_VERB, SAYYARA_VERB~~ *(remove — migrated)*
- ~~TARAKA_TRANS~~ *(remove if §4.3 chooses 4-verb migration)*
- `TALEEQ_PRINCIPLE`, `DHIKR_HADHF_PRINCIPLE` *(retain — apply to cognition verbs)*

**Open question for RULE_LOCK:** the framework row `ZANN_BASIC` currently says *«ظَنَّ وَ أَخواتها أَفعال تَدخُل عَلى المُبتَدَأ وَ الخَبَر فَتَنصِبهما مَفعولَين عَلى أَنَّهُما **مَفعولان مَنسوبان لِأَفعال القُلوب أَو التَّحويل**»* — it explicitly mentions أَفعال التَّحويل. After migration, that phrase becomes inaccurate. Two options:
- **Option A:** rewrite ZANN_BASIC's meaning_ar to remove the التَّحويل phrase. Minimal edit, keeps the row count change clean.
- **Option B:** leave ZANN_BASIC untouched and accept the minor inaccuracy until a future framework-row hygiene batch.

SPEC preference: **Option A** — the rewrite is one cell, surgical, and consistent with the invariant. RULE_LOCK to decide.

---

## 5. Honest `author_position` handling

The existing rows carry these `author_position` values:

| Row | `author_position` | ProofKind impact |
|---|---|---|
| `JAALA_VERB` | `preferred` | Certificate (preserved on migration) |
| `ITTAKHADHA_VERB` | `preferred` | Certificate (preserved on migration) |
| `SAYYARA_VERB` | **`reported`** | Hypothesis (preserved on migration — would have flipped to Certificate under the prior Batch C; that flip is now explicitly disallowed) |
| `TARAKA_TRANS` | **`reported`** | Hypothesis (preserved on migration) |

The prior Batch C SPEC §4 Row 4 set صَيَّرَ to `preferred`. That was a silent upgrade — Samarrai's position on صَيَّرَ in the existing ZANN_FAMILY row was recorded as `reported` (text-attestation, not author-preferred). Batch C₂ **does not perform that upgrade.** Any change to a row's `author_position` requires a separate re-curation entry with documented `disagreement` rationale, and is **deferred** to a future re-curation batch (see §4.4).

**Binding rule for RULE_LOCK:** migration preserves `author_position` cell-for-cell. The new `transform_verbs_meanings.csv` will therefore carry a mix of `preferred` and `reported` rows — not a uniform `preferred` set as the prior Batch C SPEC assumed.

---

## 6. Proposed row design

Final row text will be locked in the RULE_LOCK. The SPEC sketches the migration mapping; field-by-field text is per the existing ZANN row, lightly normalized:

### 6.1 Framework row (new)

| Column | Value |
|---|---|
| `priority` | `1` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` / `vocalized_form` | `—` / `—` |
| `meaning_id` | `AFAL_TAHWIL_BASIC` |
| `meaning_ar` | Per prior SPEC §4 Row 1, beginning *«أفعال التحويل / التصيير …»* |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `author_position` | `preferred` |
| `source_part` / `source_page` | `2` / `26` |
| `confidence` | `0.95` (ZANN framework-row precedent) |

### 6.2 Migrated verb rows (3 or 4)

For each migrated row:
- `meaning_id`: chosen per RULE_LOCK — recommendation is the prior SPEC's naming (`AFAL_TAHWIL_JAAL`, `AFAL_TAHWIL_ITTAKHATHA`, `AFAL_TAHWIL_SAYYARA`, optionally `AFAL_TAHWIL_TARAKA`). Old IDs (`JAALA_VERB`, etc.) are **not retained as aliases** since no Python code references them by string.
- `meaning_ar`: copy from existing row, refined to remove any "في باب ظنّ وأخواتها" framing if present (the existing rows don't carry such framing, so usually verbatim).
- `operator` / `vocalized_form`: per §6.3 vocalization decision.
- `author_position`: **copied verbatim** from existing row (per §5).
- `source_part`, `source_page`, `confidence`: copied verbatim.
- `conditions`, `exceptions`, `warnings`: copied verbatim from existing row; the rule-card's mandatory warnings (polysemy for جَعَل, valency for اِتَّخَذ) are merged in where the existing row doesn't carry them. RULE_LOCK to specify per row.
- `example_constructed`, `example_quran`, `surah_ayah`: copied verbatim. (The existing ZANN rows for these operators carry stronger Quranic anchors than the rule-card defaults — e.g., `وَجَعَلَ الْقَمَرَ فِيهِنَّ نُورًا` (نوح:16) on `JAALA_VERB` — and those are preserved.)

### 6.3 Open decision: canonical vocalization for اِتَّخَذَ

The existing row uses `اتَّخَذَ` (no initial kasra). The prior Batch C SPEC used `اِتَّخَذَ` (with initial kasra). These are the same lemma; under the loader's plain-fallback normalization they collide on `اتخذ`. The vocalized lookup key differs.

**SPEC preference:** **`اِتَّخَذَ`** (with initial kasra) — matches the form in `وَاتَّخَذَ` after wasla resolution, and aligns with the Form-VIII pattern's underlying kasra. RULE_LOCK to confirm.

If RULE_LOCK picks the other form (`اتَّخَذَ`), all references in the new row must use that form consistently.

---

## 7. Source restriction, schema, ProofKind, and artifact hygiene

### 7.1 Source restriction

- Primary source: `maani_alnahw/data/processed/maani_alnahw/rule_cards.jsonl`, row `AFAL_AL_TAHWIL__P2_001`.
- Author: Samarrai only. No external classical scholars, no modern Arabic, no NAA.
- Vol 2, pp. 26 – 279. Confidence baseline 0.93 (from the rule card), but **migrated rows preserve their existing confidence values** (0.92 / 0.92 / 0.9 / 0.88) — see §1 invariant (4).

### 7.2 Schema lock

- Existing 19-column schema only. No column additions, renames, or reorders.
- `schema.md` is not edited.
- No inline operator meanings in Python code.

### 7.3 ProofKind lock

- Enum `{Certificate, Hypothesis, Zero}` unchanged.
- Mapping rules unchanged: `exact_vocalized + (author_position != "reported") → Certificate`; `prefix_stripped` / `prefix_as_operator` / `pattern_construction` OR `author_position == "reported"` → `Hypothesis`.
- Batch B monotonicity (Certificate may only downgrade) preserved.
- **No proof upgrades from this batch.** Migration of `SAYYARA_VERB` (currently Hypothesis-via-reported) emits the migrated row as Hypothesis. The prior Batch C's silent flip to Certificate is reversed.

### 7.4 Generated-artifact hygiene

`clean_code/data/samarrai_sweep/per_word.csv` and `top_topics.csv` are **regenerable sweeps** built from the source CSVs. After migration:

- Every word currently rowed against `JAALA_VERB` / `SAYYARA_VERB` / `ITTAKHADHA_VERB` / `TARAKA_TRANS` will instead row against `AFAL_TAHWIL_JAAL` / `AFAL_TAHWIL_SAYYARA` / `AFAL_TAHWIL_ITTAKHATHA` / `AFAL_TAHWIL_TARAKA`.
- The sweep files become out-of-date the moment the migration ships.

**Two RULE_LOCK options:**
- **Option 7.4.a (regenerate in batch).** Re-run the sweep generator after the migration; commit the regenerated CSVs as part of Batch C₂. Pros: ships consistent. Cons: large diff (~80+ row changes in `per_word.csv`); RULE_LOCK must whitelist these regenerated files.
- **Option 7.4.b (defer regeneration).** Leave the sweep files stale; document the deferral in the Batch C₂ report; regenerate in a follow-up commit. Pros: small clean batch diff. Cons: temporary inconsistency between source CSVs and sweep output.

**SPEC preference:** **Option 7.4.a**, on the principle that the invariant *«لا تخزّن ما تستطيع توليده»* also applies here — leaving stale meaning_id strings in `per_word.csv` is itself a form of "wrong stored fact." If RULE_LOCK chooses 7.4.b, the report must contain a regenerate-then-commit follow-up gate.

RULE_LOCK to confirm. Either way, the choice must be explicit, not implicit.

---

## 8. Allowed implementation files (for the later implementation batch)

The implementation batch that derives from the RULE_LOCK may touch **only** these paths:

| Path | Purpose | Required / Conditional |
|---|---|---|
| `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` | Remove 3 (or 4) transformation rows; optionally rewrite `ZANN_BASIC.meaning_ar` per §4.5 Option A | **Required** |
| `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` | New file holding framework row + migrated rows | **Required** |
| `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` | New test file enforcing invariant + migration mapping | **Required** |
| `clean_code/samarrai_loaders/volume2_loader.py` | One-line addition to `CSV_FILES` list | **Conditional** — only if §10 investigation confirms the loader does not auto-discover the new CSV |
| `clean_code/data/samarrai_sweep/per_word.csv` | Regenerated sweep | **Conditional** — only if §7.4 chooses Option 7.4.a |
| `clean_code/data/samarrai_sweep/top_topics.csv` | Regenerated sweep | **Conditional** — only if §7.4 chooses Option 7.4.a |

No other files. The implementation's `git diff --name-only` must be a subset of the above.

---

## 9. Forbidden files (for the later implementation batch — to be enumerated in RULE_LOCK)

Same hard-forbidden families as the prior RULE_LOCK §3:

- `clean_code/i3rab_engine/*` — entire subtree
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`
- `clean_code/event_extractor.py`
- `clean_code/relation_extractor.py`
- `clean_code/resolution_engine.py`
- `clean_code/reasoning_engine.py`
- `clean_code/meaning_assembler.py` — unless a failing-test artifact proves existing Batch A wiring cannot surface AFAL_TAHWIL claims
- `clean_code/samarrai_analyzer.py` — unless loader/test proves the analyzer cannot load the new CSV after `volume2_loader.py` is consulted
- `clean_code/samarrai_certified_operator_gate.py` — unless smoke testing surfaces a real gate conflict
- `clean_code/data/contracts/maani/schema.md`
- All MASAQ files (any path containing "masaq")
- All MAANI volume3/volume4/constructions CSVs (only the two volume2 files in §8 are in scope)
- `data/contracts/lists/*`, `data/contracts/rules/*`, `data/contracts/translations/*`
- `maani_alnahw/**` — read-only reference
- All non-MAANI doc paths under `docs/specs/` (only this SPEC and its RULE_LOCK are produced)
- `archive/**`, `new_arabic_analyzer/**`

---

## 10. Investigation gates (must pass BEFORE RULE_LOCK is written)

The RULE_LOCK can only be drafted after these read-only investigations are complete and their results are written into the RULE_LOCK:

### 10.1 Loader auto-discovery (re-confirm)

Re-run the loader probe (the prior Batch C investigation showed `CSV_FILES` is hardcoded). Confirm no one has refactored it since. If still hardcoded, the conditional `volume2_loader.py` edit in §8 is required.

### 10.2 Backward-reference scan for migrated meaning_id strings

Re-grep for `JAALA_VERB`, `ITTAKHADHA_VERB`, `SAYYARA_VERB`, `TARAKA_TRANS` across the repo to confirm the §3 finding still holds (no Python code references them by string). If any new references have appeared since, RULE_LOCK must address them.

### 10.3 Docs consistency check

Inspect `clean_code/TESTS.md` and `clean_code/RULES.md` for any assertion that depends on the four migrated meaning_id strings or on the row count of `zann_family_meanings.csv` (16 today). If row-count assertions exist, RULE_LOCK must specify whether the docs are updated in Batch C₂ or in a follow-up doc batch.

### 10.4 Production-suite regression sanity check

Re-run `clean_code/test_production_path_segmentation.py` against current HEAD to confirm baseline 158/158 still holds (no drift since the discard). The Batch C₂ implementation must not regress this.

### 10.5 Batch B regression sanity check

Re-run `clean_code/test_maani_batch_b_author_position.py` against current HEAD to confirm baseline 6/6 still holds. Critically: check whether any Batch B test references `SAYYARA_VERB` or any other migrated meaning_id — if so, the test will need to be updated in Batch C₂ (and RULE_LOCK must whitelist that one test file edit, otherwise Batch B test edits remain forbidden).

### 10.6 Sweep regenerator availability

Locate the generator that produces `clean_code/data/samarrai_sweep/per_word.csv` and `top_topics.csv`. Confirm it runs to completion and is deterministic. If the generator is missing or broken, Option 7.4.a is infeasible and 7.4.b is the only option.

Each of these gates produces a one-paragraph finding that goes into RULE_LOCK §0 (preamble) so the binding contract is grounded in current repo state, not stale assumptions.

---

## 11. Tests (anticipated; RULE_LOCK will lock the final list)

The new test file `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` must include:

### 11.1 Invariant enforcement (the core hygiene tests)

| # | Test | Asserts |
|---|---|---|
| H1 | `t_no_operator_carries_transformation_in_two_topics` | For each migrated operator (جَعَلَ / اِتَّخَذَ / صَيَّرَ / [تَرَكَ]), loading all volume2 records yields **exactly one** row whose `semantic_field ∈ {causative_transformation, pure_transformation, transformation_via_leaving, transformation_or_taking}` — and that row's `topic_id == "AFAL_TAHWIL"`, not `"ZANN_FAMILY"`. **This is the binding test for invariant (1).** |
| H2 | `t_zann_family_holds_no_transformation_rows` | Loading `zann_family_meanings.csv`, no row has `topic_id == "ZANN_FAMILY"` AND a transformation `semantic_field`. Boundary guard on the migration. |
| H3 | `t_migrated_rows_preserve_author_position` | For each migrated row, the new row's `author_position` matches the pre-migration row's value exactly. Specifically: `AFAL_TAHWIL_JAAL` is `preferred`, `AFAL_TAHWIL_ITTAKHATHA` is `preferred`, `AFAL_TAHWIL_SAYYARA` is **`reported`**, `AFAL_TAHWIL_TARAKA` (if in scope) is `reported`. **Binding test for invariant (3).** |
| H4 | `t_migrated_rows_preserve_provenance` | For each migrated row, `source_part`, `source_page`, `confidence` match the pre-migration values verbatim (`2`/`26`/`0.92` for jaal & ittakhatha, `2`/`26`/`0.9` for sayyara, `2`/`26`/`0.88` for taraka). **Binding test for invariant (4).** |

### 11.2 Structural tests

| # | Test | Asserts |
|---|---|---|
| S1 | `t_csv_header_matches_schema` | The new CSV's header is the 19-column schema, exact order. |
| S2 | `t_row_count_matches_scope` | The new CSV has exactly `1 + N` rows (`N=3` strict, `N=4` if §4.3 chooses 4-verb migration). The ZANN CSV has exactly `16 − N` rows post-migration. |
| S3 | `t_meaning_ids_unique_across_volume2` | No `meaning_id` appears in more than one row across all volume2 CSVs. |
| S4 | `t_loader_discovers_new_csv` (conditional) | If the loader edit was needed, `volume2_loader.stats()["files"]` includes `transform_verbs` with the expected row count. |

### 11.3 Claim-level tests

| # | Test | Asserts |
|---|---|---|
| C1 | `t_jaala_returns_afal_tahwil_certificate` | `lookup_word_all_volumes("جَعَلَ", "exact_vocalized")` returns at least one claim with `topic_id="AFAL_TAHWIL"`, `meaning_id="AFAL_TAHWIL_JAAL"`, `proof_kind="Certificate"`. |
| C2 | `t_ittakhatha_returns_afal_tahwil_certificate` | Same for اِتَّخَذَ (or اتَّخَذَ per §6.3 RULE_LOCK decision). |
| C3 | `t_sayyara_returns_afal_tahwil_hypothesis` | `صَيَّرَ` returns a claim with `topic_id="AFAL_TAHWIL"`, `meaning_id="AFAL_TAHWIL_SAYYARA"`, and **`proof_kind="Hypothesis"`** (because `author_position="reported"` per §5). **Critical test** — locks in the no-silent-upgrade rule. |
| C4 | `t_taraka_returns_afal_tahwil_hypothesis` (conditional on §4.3) | Same shape as C3. |
| C5 | `t_zann_family_still_returns_dhann` | `ظَنَّ` continues to resolve to `topic_id="ZANN_FAMILY"`. Boundary guard — the new family does not steal cognition claims. |
| C6 | `t_no_duplicate_claims_for_migrated_operators` | For each migrated operator, `lookup_word_all_volumes(op, "exact_vocalized")` returns rows whose `topic_id` set is exactly `{"AFAL_TAHWIL"}` (no `ZANN_FAMILY` row remains). |

### 11.4 Cross-suite regression

- `clean_code/test_production_path_segmentation.py` — must still pass 158/158.
- `clean_code/test_maani_batch_b_author_position.py` — must still pass at its current count (recheck per §10.5; may need a one-line edit if it references a migrated meaning_id, but that edit must be explicitly whitelisted in RULE_LOCK).
- `clean_code/test_phase4_certificate_reevaluation.py` — must still pass at its current count.

### 11.5 Sweep regeneration tests (conditional on §7.4 choice)

If Option 7.4.a is chosen, add:

| # | Test | Asserts |
|---|---|---|
| R1 | `t_sweep_per_word_uses_new_meaning_ids` | `per_word.csv` contains zero references to the four migrated `meaning_id` strings, and contains expected counts of the new ones. |
| R2 | `t_sweep_top_topics_reflects_new_topic` | `top_topics.csv` shows `AFAL_TAHWIL` as a topic and `ZANN_FAMILY` count is decremented by the migrated row count. |

---

## 12. Acceptance criteria (binding sketch — RULE_LOCK will finalize)

The implementation batch is acceptable iff:

1. Migration mapping is complete: every operator listed in §4.2 appears exactly once across all volume2 CSVs, and only under `AFAL_TAHWIL`.
2. No duplicate transformation claims exist (test H1 passes).
3. `author_position` of every migrated row matches the pre-migration value (test H3 passes).
4. Provenance fields are preserved verbatim (test H4 passes).
5. Schema validation passes (header is the 19-column schema exactly).
6. Row counts: `transform_verbs_meanings.csv` has `1 + N` rows; `zann_family_meanings.csv` has `16 − N` rows. (`N` = 3 or 4 per §4.3.)
7. Loader discovers the new file (test S4 passes if loader edit was needed).
8. All claim-level tests (C1–C6) pass.
9. Cross-suite regression: production 158/158, Batch B unchanged, Phase 4 unchanged.
10. If sweep regeneration is in scope (Option 7.4.a), R1 + R2 pass.
11. No file outside §8 modified.
12. No file in §9 modified (unless conditionally lifted with a failing-test artifact).
13. Working tree clean except `.claude/`; no `out_*.txt`, no `.pyc`.
14. Batch C₂ report committed separately under separate approval.

---

## 13. Rejection criteria (binding sketch — RULE_LOCK will finalize)

The batch is rejected if any of:

- Any migrated row's `author_position` differs from its pre-migration value (silent upgrade/downgrade forbidden — invariant (3)).
- Any operator appears under two `topic_id`s post-migration (invariant (1) violated).
- Any deferred operator (`رَدَّ`, `تَخِذَ`, `وَهَبَ`, or any non-AFAL_TAHWIL family from §4.4) is introduced.
- Any schema change is made.
- Any new ProofKind value is introduced.
- Any ProofKind upgrade code path is added (Batch B monotonicity violation).
- Any external source (Ibn Hisham, modern Arabic, NAA, etc.) is cited or consumed.
- Any required test in §11 is missing.
- `test_production_path_segmentation.py` regresses below 158/158.
- `test_maani_batch_b_author_position.py` regresses below its current count.
- A Certificate-grade transformation reading appears for an operator whose existing row was `reported` (specifically: `SAYYARA_VERB` and optionally `TARAKA_TRANS`).
- Untracked artifacts (`out_*.txt`, `.pyc`, etc.) left in committed tree.
- Goldens regress on the four MASAQ goldens (2:282, 2:196, 28:7, 1:1).
- Any file outside §8 modified.
- Any file in §9 modified without a failing-test artifact justifying the conditional lift.

---

## 14. Risks

### 14.1 Hidden references in sweep artifacts

`per_word.csv` carries ~80+ references to the migrated meaning_ids. If §7.4 chooses Option 7.4.b (defer regeneration), downstream consumers reading the sweep will see stale strings until the regenerate gate fires. Mitigation: SPEC preference for 7.4.a; if 7.4.b is chosen, RULE_LOCK includes a hard regenerate-then-commit follow-up gate.

### 14.2 Vocalization mismatch in اِتَّخَذَ

The existing row uses `اتَّخَذَ`; the prior Batch C used `اِتَّخَذَ`. RULE_LOCK must pick exactly one and use it consistently in the new row. If RULE_LOCK picks `اِتَّخَذَ`, `exact_vocalized` lookup of the existing `اتَّخَذَ` form (which is how the word actually appears in many corpus tokens after wasla resolution differs) will no longer match — RULE_LOCK should specify whether plain-fallback covers this or whether two vocalized aliases are needed in the same row (a constraint the schema does not currently support, so likely one form wins).

### 14.3 Batch B test interaction with `SAYYARA_VERB`

Batch B's regression test may assert on the existence of a specific `reported` row to verify the Hypothesis-downgrade path. If `SAYYARA_VERB` is that row, the test will fail after migration unless updated. Mitigation: §10.5 investigation must check; if true, RULE_LOCK whitelists a one-line edit to the Batch B test file (otherwise all test-file edits remain forbidden).

### 14.4 Loss of cross-classification cue

The existing ZANN framework row mentions أَفعال التَّحويل explicitly. Some downstream consumer (a doc, a future test) may have relied on ZANN as a single super-topic that included both cognition and transformation. After migration, ZANN is cognition-only. Mitigation: §4.5 (rewrite framework row + scan docs in §10.3). The cleaner taxonomy is itself a benefit, but the transition must be documented in the Batch C₂ report.

### 14.5 The framework row change ripples into ZANN tests

If any Batch A or Batch B test asserts on the exact text of `ZANN_BASIC.meaning_ar`, the §4.5 Option A rewrite will break it. Mitigation: §10.5 investigation.

### 14.6 Sweep regenerator may not exist or may be non-deterministic

If §10.6 reveals the sweep generator is missing, Option 7.4.a becomes infeasible mid-batch. Mitigation: §10.6 runs **before** RULE_LOCK is drafted, so the choice between 7.4.a and 7.4.b is informed.

---

## 15. Rollback

If Batch C₂ implementation is rejected or fails review after the implementation commit:

1. `git revert <implementation-commit-hash>` — creates a new revert commit that restores `zann_family_meanings.csv` to its pre-migration state, deletes `transform_verbs_meanings.csv`, deletes the new test file, reverts the loader edit, and (if applicable) reverts the sweep regeneration.
2. **No force-push.** No `git reset --hard` on shared branches.
3. **No data outside Batch C₂ is touched** in the rollback. Batches A, B, all MASAQ commits remain intact.
4. **Working tree post-revert** matches `e1474ab` + `.claude/`.
5. The reverted state is the pre-C₂ baseline. A follow-up batch must re-draft a new RULE_LOCK before any retry.

---

## 16. Governance

### 16.1 Approval gates (each requires separate explicit approval)

1. **SPEC review + approval** — this document. (Pending review at time of writing.)
2. **§10 investigation execution** — read-only re-confirmation of loader, references, docs, regression baselines, sweep generator availability. Each finding is recorded in the RULE_LOCK preamble.
3. **RULE_LOCK draft** — `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_RULE_LOCK.md`, written only after §10 findings are in.
4. **RULE_LOCK approval** — user reviews and approves the binding contract.
5. **Implementation approval** — separate approval before any file under §8 is touched.
6. **Test approval** — after implementation, test results reported back to user.
7. **Commit approval** — user approves the specific commit hash for the implementation.
8. **Report approval** — `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_REPORT.md` written and committed under separate approval after the implementation commit lands.

Skipping any gate rejects the batch.

### 16.2 What is NEVER allowed inside Batch C₂

- Schema changes.
- ProofKind enum changes.
- Touching any file in §9 without a failing-test artifact justifying the conditional lift.
- Silent `author_position` upgrades or downgrades.
- Adding any operator not listed in §4.2.
- Citing or consuming any non-Samarrai source.
- Modifying any committed historical artifact: `MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (`6d91650`) and `MAANI_BATCH_C_AFAL_TAHWIL_RULE_LOCK.md` (`e1474ab`) **must remain in history unchanged**.

### 16.3 What requires a new RULE_LOCK (NOT this one)

- Adding the remaining transformation verbs (`رَدَّ`, `تَخِذَ`, `وَهَبَ`) — separate expansion batch.
- Extending the MeaningGraph edge whitelist to include `AFAL_TAHWIL` — separate edge-emission batch with smoke evidence.
- Re-curating any `reported` row to `preferred` — separate re-curation batch with `disagreement` documentation.
- Any other family (كان وأخواتها, مُقارَبَة, مَدْح/ذَمّ, تَضمين) — separate per-family SPEC + RULE_LOCK.
- Bulk migration of `construction_rules.jsonl` / `meaning_cards.jsonl` — explicitly forbidden track.

### 16.4 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. `git log --oneline -20` — confirm no in-flight commits on MASAQ-related files since this SPEC.
2. `git status` — confirm working tree is clean except `.claude/`.
3. `git stash list` — confirm no untracked WIP exists that could be re-applied.

If any concurrent activity is found on MASAQ / versebyverse / hidden-pronoun tracks, postpone Batch C₂ implementation until that activity completes.

---

## 17. Open questions for RULE_LOCK (must be resolved before drafting)

| # | Question | SPEC preference |
|---|---|---|
| Q1 | 3-verb migration or 4-verb migration (include `تَرَكَ`)? | **4-verb** (complete hygiene) |
| Q2 | Vocalization for اِتَّخَذَ row? | **`اِتَّخَذَ`** (with initial kasra) |
| Q3 | Rewrite `ZANN_BASIC.meaning_ar` to remove التَّحويل phrase (Option A) or leave it (Option B)? | **Option A** (surgical rewrite) |
| Q4 | Regenerate sweep artifacts (Option 7.4.a) or defer (7.4.b)? | **7.4.a** (regenerate in batch) |
| Q5 | Whitelist a one-line edit to `test_maani_batch_b_author_position.py` if it asserts on a migrated meaning_id? | **Yes, only if §10.5 investigation proves it's needed.** |
| Q6 | Whitelist updates to `clean_code/TESTS.md` / `RULES.md` if they reference migrated meaning_ids? | **Defer** — separate doc batch. |
| Q7 | Keep prior `meaning_id`s (`JAALA_VERB`, etc.) as aliases? | **No** — clean rename. No Python references confirmed in §3. |

The RULE_LOCK must resolve each of these explicitly. Silent inheritance of the SPEC's preference is not enough — the RULE_LOCK is the binding contract.

---

## 18. One-screen recap

| Item | Value |
|---|---|
| Batch | C₂ |
| Type | Migration + hygiene (not addition) |
| Supersedes | SPEC `6d91650`, RULE_LOCK `e1474ab` (both retained in history) |
| Reason for existence | Discovery that ZANN_FAMILY already holds transformation rows; prior Batch C duplicated them |
| Core invariant | لا تخزّن ما تستطيع توليده |
| Source | `rule_cards.jsonl` row `AFAL_AL_TAHWIL__P2_001`, Samarrai only |
| Provenance | Vol 2, pp. 26 – 279 |
| Operators migrated | جَعَلَ + اِتَّخَذَ + صَيَّرَ + (تَرَكَ if Q1=4-verb) |
| Files touched (data) | `zann_family_meanings.csv` (rows removed), `transform_verbs_meanings.csv` (new), optionally `samarrai_sweep/*.csv` (regenerated) |
| Files touched (code) | `volume2_loader.py` (+1 line, conditional) |
| Files touched (tests) | new `test_maani_batch_c2_afal_tahwil_hygiene.py` |
| Schema | unchanged 19-column |
| ProofKind enum | unchanged |
| `author_position` discipline | preserved verbatim (no silent flips) |
| Total MAANI row change | net −2 to +1 (was +4 in prior Batch C; now net-neutral hygiene) |
| Investigation gates | 6 read-only checks must complete before RULE_LOCK |
| Tests | 4 invariant + 4 structural + 6 claim + 2 conditional sweep + 3 regression = 13 + 2 conditional + 3 cross-suite |
| Open questions for RULE_LOCK | 7 (see §17) |
| Forbidden | same as prior RULE_LOCK §3 + no silent author_position flips + no scope creep |
| Rollback | `git revert` of implementation commit; no force-push |
| Governance gates | 8 (each separate approval) |
