# MAANI Batch C — أَفعال التَّحويل / AFAL_AL_TAHWIL — RULE_LOCK

> **Type:** RULE_LOCK (binding contract).
> **Date:** 2026-05-30
> **SPEC parent:** `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (commit `6d91650`).
> **Status:** Binding. Any violation rejects the batch.

This document is the binding contract for MAANI Batch C. The SPEC draft describes the design; this RULE_LOCK constrains the implementation. Once approved, the boundaries below cannot be widened inside this batch — any widening requires a new RULE_LOCK and a new batch.

---

## 1. Batch identity

| Field | Value |
|---|---|
| Batch name | **MAANI Batch C — AFAL_AL_TAHWIL / أَفعال التَّحويل** |
| Parent SPEC | `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (commit `6d91650`) |
| Source restriction | **Samarrai only** |
| Source artifact | `maani_alnahw/data/processed/maani_alnahw/rule_cards.jsonl` |
| Source row id | `AFAL_AL_TAHWIL__P2_001` |
| Source book | معاني النحو — فاضل صالح السامرَّائيّ |
| Source volume / page range | **Vol 2, pp. 26 – 279** |
| Source confidence | **0.93** (as recorded in the rule card) |

No other source may be cited or consumed in Batch C. No external classical scholars, no modern Arabic, no NAA, no `meaning_cards.jsonl`, no `semantic_claims.jsonl`, no `construction_rules.jsonl`, no `operators_enriched.jsonl`. Evidence outside `AFAL_AL_TAHWIL__P2_001` is **not admissible** for Batch C row content.

---

## 2. Allowed implementation files

The implementation batch (NOT this RULE_LOCK; the implementation comes later under separate approval) may touch ONLY these paths:

| Path | Purpose | Required / Conditional |
|---|---|---|
| `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` | New CSV holding exactly the 4 rows locked in §4 | **Required** |
| `clean_code/test_maani_batch_c_afal_tahwil.py` | New test file holding the tests locked in §7 | **Required** |
| `clean_code/samarrai_loaders/volume2_loader.py` | One-line edit if and only if auto-discovery investigation (§6.5 of SPEC) proves it does not pick up the new CSV | **Conditional — only if investigation justifies it** |

No other files. The implementation batch's `git diff --name-only` must be a subset of the above. Any file outside this list appearing in the implementation's diff is grounds for rejection (§9).

---

## 3. Forbidden files (binding)

The following files **MUST NOT** be modified in Batch C. Any modification to any file in this list rejects the batch.

### 3.1 i3rab / parser surface (hard-forbidden)
- `clean_code/i3rab_engine/*` — entire subtree
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`

### 3.2 Downstream layers (hard-forbidden)
- `clean_code/event_extractor.py`
- `clean_code/relation_extractor.py`
- `clean_code/resolution_engine.py`
- `clean_code/reasoning_engine.py`

### 3.3 MAANI consumer files (conditional-forbidden — requires test proof to lift)
- `clean_code/meaning_assembler.py` — forbidden unless a later test in this batch proves that existing Batch A wiring cannot surface AFAL_TAHWIL claims at all. If lifted, only step-6/6a/6b edge-emission code may be touched; no other change.
- `clean_code/samarrai_analyzer.py` — forbidden unless a loader/test proves the existing analyzer cannot load the new CSV after `volume2_loader.py` is consulted. If lifted, only `_lookup_in_volume` glue may be touched; no other change.
- `clean_code/samarrai_certified_operator_gate.py` — forbidden unless smoke testing surfaces a real gate conflict on a Batch C verb. If lifted, only the gate's existing rule maps may be extended; no rule redesign.

To lift any conditional-forbidden item, the implementation batch must produce a failing-test artifact demonstrating the necessity. Without that artifact, the file stays forbidden.

### 3.4 Schema / governance docs (hard-forbidden)
- `clean_code/data/contracts/maani/schema.md` — schema is locked at 19 columns (§5).
- All other files under `docs/specs/` except this RULE_LOCK file. No "while we're here" doc edits.
- `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (already committed at `6d91650`) — frozen reference; do not amend.

### 3.5 MASAQ surface (hard-forbidden)
- Any file containing "masaq" in its path.
- `/tmp/masaq_diff/*` — investigation artifacts only; not part of any batch.
- All MASAQ-related committed paths.

### 3.6 Other tracks (hard-forbidden)
- `data/contracts/maani/**` outside the single new CSV file path in §2. No edits to existing volume1/volume2/volume3/volume4/constructions CSVs.
- `data/contracts/lists/*`
- `data/contracts/rules/*`
- `data/contracts/translations/*`
- `data/MASAQ.csv`
- `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**` — read-only reference. No edits to the source JSONL.
- `new_arabic_analyzer/**`
- `archive/**`

### 3.7 No new test files outside `test_maani_batch_c_afal_tahwil.py`
- `clean_code/test_production_path_segmentation.py` — unchanged.
- `clean_code/test_maani_batch_b_author_position.py` — unchanged.
- `clean_code/test_phase4_certificate_reevaluation.py` — unchanged.
- All other existing test files — unchanged.

### 3.8 No untracked files left behind
- No `out_*.txt`.
- No `.pyc` modifications committed.
- No `.claude/` content committed.
- No stash content reintroduced.

---

## 4. Locked rows (exactly 4)

The implementation batch must add **exactly 4 rows** to `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv`. The row count must be exactly 4 (plus the header line = 5 lines total in the new file). Adding fewer or more rejects the batch.

### Row 1 — Framework

| Required field | Required value |
|---|---|
| `priority` | `1` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `—` |
| `vocalized_form` | `—` |
| `meaning_id` | `AFAL_TAHWIL_BASIC` |
| `meaning_ar` | Must begin with `أفعال التحويل / التصيير` and describe the two-object causative-transformation construction. |
| `author_position` | `preferred` |
| `source_part` | `2` |
| `source_page` | within the rule card's range (26 – 279); recommend `26` |
| `confidence` | `0.95` (matching the ZANN framework precedent; slightly above the rule card's verb-row baseline of `0.93`) |

Other columns (`syntactic_effect`, `semantic_field`, `conditions`, `exceptions`, `warnings`, `example_constructed`, `example_quran`, `surah_ayah`, `disagreement`) must be populated per the SPEC §4 Row-1 design; deviation must not silently introduce content from outside `AFAL_AL_TAHWIL__P2_001`.

### Row 2 — جَعَلَ (transformation reading)

| Required field | Required value |
|---|---|
| `priority` | `2` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `جَعَلَ` |
| `vocalized_form` | `جَعَلَ` |
| `meaning_id` | `AFAL_TAHWIL_JAAL` |
| `author_position` | `preferred` |
| `source_part` | `2` |
| `source_page` | within 26 – 279 |
| `confidence` | `0.93` (matching the rule card's source value) |
| `warnings` | **Must include** Samarrai's polysemy warning: «جَعَل تَأتي بِمَعنى التَّحويل وَ بِمَعنى الخَلق وَ بِمَعنى الاعتِقاد — السِّياق يُحَدِّد». The polysemy text is **mandatory** because it is the row's primary safety hedge against overclaim. |

### Row 3 — اِتَّخَذَ (transformation reading)

| Required field | Required value |
|---|---|
| `priority` | `3` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `اِتَّخَذَ` |
| `vocalized_form` | `اِتَّخَذَ` |
| `meaning_id` | `AFAL_TAHWIL_ITTAKHATHA` |
| `author_position` | `preferred` |
| `source_part` | `2` |
| `source_page` | within 26 – 279 |
| `confidence` | `0.93` |
| `example_quran` | Must be the Quranic anchor `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` (النساء : 125) — recorded directly from the rule card. |
| `warnings` | Must include the valency disambiguation: «اتَّخَذ بِمَعنى التَّحويل تَكون لِمَفعولَين، وَ بِمَعنى الأَخذ لِمَفعول واحِد». Mandatory. |

### Row 4 — صَيَّرَ (transformation reading)

| Required field | Required value |
|---|---|
| `priority` | `4` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `صَيَّرَ` |
| `vocalized_form` | `صَيَّرَ` |
| `meaning_id` | `AFAL_TAHWIL_SAYYARA` |
| `author_position` | `preferred` |
| `source_part` | `2` |
| `source_page` | within 26 – 279 |
| `confidence` | `0.93` |
| `example_quran` | Must be **empty** (the rule card provides no Quranic anchor for صَيَّرَ; do not invent one). |
| `surah_ayah` | Must be **empty**. |
| `example_constructed` | Must be populated with a clear two-object example (e.g., `صَيَّرْتُ العَدُوَّ صَديقًا`). |

### Row-level lock summary
- Total rows: **exactly 4**.
- All four use `topic_id = "AFAL_TAHWIL"` (new value, not previously in the topic enumeration).
- All four use `author_position = "preferred"`.
- All four cite `source_part = 2`, `source_page` within 26 – 279.
- No row may carry `author_position = "reported"` (which would trigger Batch B's automatic downgrade) — the rule card content is all author-preferred. Any "reported" row in Batch C is grounds for rejection.

---

## 5. Schema lock

- The new CSV must conform to the **existing 19-column schema** in `clean_code/data/contracts/maani/schema.md`, exact column order:
  `priority, topic_id, operator, vocalized_form, meaning_id, meaning_ar, syntactic_effect, semantic_field, conditions, exceptions, warnings, example_constructed, example_quran, surah_ayah, author_position, disagreement, source_part, source_page, confidence`
- **No schema changes** are permitted in Batch C. No new columns. No column renames. No column reorders. No change to `schema.md`.
- **No inline operator meanings in Python code.** Every claim is one CSV row; no row content embedded in `.py` files. (Hard rule per handoff §2.1.)
- **No new `proof_kind` value** beyond `{Certificate, Hypothesis, Zero}`. (Hard rule per handoff §9.2.)
- The new `topic_id` value `AFAL_TAHWIL` is an open-set entry (consistent with how `ZANN_FAMILY` was added when its file shipped). It is **not** considered a schema change.

---

## 6. ProofKind lock

The existing MAANI ProofKind rules apply unchanged:

- `Certificate` ← `match_type == "exact_vocalized"` AND `author_position != "reported"`.
- `Hypothesis` ← `match_type in {"prefix_stripped", "prefix_as_operator", "pattern_construction"}` OR `author_position == "reported"`.
- `Zero` ← no match, blacklisted topic, or gate rejection.

For Batch C specifically:

- All 4 rows have `author_position = "preferred"` (§4), so they emit `Certificate` when matched as `exact_vocalized`.
- The same 4 rows emit `Hypothesis` when matched via `prefix_stripped` / `prefix_as_operator` / `pattern_construction` (per existing Batch A precedent).
- **No proof_kind upgrades anywhere.** Batch B's monotonicity rule (Certificate may only DOWNGRADE to Hypothesis, never upgrade) is preserved. Batch C must not introduce any code path that increases proof_kind certainty.

---

## 7. Tests required (implementation batch)

The implementation batch must add **all** of the following tests to `clean_code/test_maani_batch_c_afal_tahwil.py`. If any required test is missing, the implementation batch is rejected.

### 7.1 Structural tests (CSV-level)

| # | Test | Asserts |
|---|---|---|
| T1 | `t_csv_header_matches_schema` | The new CSV's header row exactly matches the 19 columns of `schema.md`, in order, with no trailing/leading whitespace. |
| T2 | `t_csv_row_count_is_exactly_4` | The new CSV has exactly 4 data rows (5 lines total including header). Critical lock — adding a 5th row rejects the batch. |

### 7.2 Positive lookup tests (claim-level)

| # | Test | Asserts |
|---|---|---|
| T3 | `t_afal_tahwil_jaala_transformation_claim` | `samarrai_analyzer.lookup_word_all_volumes("جَعَلَ", "exact_vocalized")` returns at least one `SamarraiClaim` with `topic_id == "AFAL_TAHWIL"`, `meaning_id == "AFAL_TAHWIL_JAAL"`, `proof_kind == "Certificate"`, `author_position == "preferred"`. |
| T4 | `t_afal_tahwil_ittakhatha_transformation_claim` | Same for `اِتَّخَذَ` → `AFAL_TAHWIL_ITTAKHATHA`. Additionally verify `example_quran` equals `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا`. |
| T5 | `t_afal_tahwil_sayyara_transformation_claim` | Same for `صَيَّرَ` → `AFAL_TAHWIL_SAYYARA`. Verify `example_quran` is empty and `example_constructed` is populated. |
| T6 | `t_afal_tahwil_framework_row_loads` | Looking up the framework row (via meaning_id direct query or via topic-listing) returns the row with `meaning_id == "AFAL_TAHWIL_BASIC"` and `meaning_ar` containing `أفعال التحويل / التصيير`. |

### 7.3 Negative regression tests (boundary protection)

| # | Test | Asserts |
|---|---|---|
| T7 | `t_afal_tahwil_negative_zann_family_stays_zann` | Looking up `ظَنَّ` continues to return claims with `topic_id == "ZANN_FAMILY"` (NOT `AFAL_TAHWIL`). Boundary guard — the new sibling must not steal from the existing family. |
| T8 | `t_afal_tahwil_negative_non_transformation_jaala` | If a non-transformation `جَعَلَ` usage is identifiable in the corpus (e.g., creation reading `جَعَلَ الظُّلُمَاتِ وَالنُّورَ`), verify the system does NOT silently emit a Certificate-grade transformation interpretation. Acceptable outcomes: (a) the transformation reading is emitted as `Hypothesis` with the `warnings` text propagated, (b) the transformation reading is suppressed by a downstream gate, OR (c) the row's `warnings` field is surfaced. **Strict assertion**: a Certificate-grade transformation reading on a non-transformation usage rejects the batch. If no non-transformation example is available in the test fixtures, this test may be implemented as a unit test against a synthesized stub. |

### 7.4 Conditional structural test

| # | Test | Asserts |
|---|---|---|
| T9 | `t_afal_tahwil_loader_discovers_file` (conditional) | If `volume2_loader.py` requires the one-line edit per §2, this test must verify that lookup of any of the 3 verbs returns at least one claim. If no loader edit is required, this test may be omitted. |

### 7.5 Cross-suite regression
The implementation batch must verify (and the report must record) that both of the following remain green post-implementation:

- `clean_code/test_maani_batch_b_author_position.py` — must remain 6/6.
- `clean_code/test_production_path_segmentation.py` — must remain at its current pass count (158/158 as of this RULE_LOCK).

Either suite regressing rejects the batch.

---

## 8. Acceptance criteria

The implementation batch is **acceptable** if and only if **all** of the following hold:

1. **Exactly 4 rows** added to `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` per §4. (CSV has exactly 5 lines including header.)
2. **Schema validation passes** — header matches schema.md exactly per §5.
3. **Loader / analyzer surface** the new claims — T3, T4, T5, T6 pass per §7.2.
4. **Total MAANI row count** rises from 245 to exactly **249**.
5. **No `author_position = "reported"` rows** in the new CSV (all four are `preferred`).
6. **All required tests** in §7.1–§7.3 pass; T9 passes if loader edit was needed; otherwise T9 may be omitted.
7. **`test_maani_batch_b_author_position.py`** still passes 6/6.
8. **`test_production_path_segmentation.py`** still passes at its current count (158/158).
9. **No changes** to any file in §3 forbidden list.
10. **No untracked artifacts** left in the working tree (`out_*.txt`, `.pyc`, etc.) at the commit point.
11. **The implementation diff is a subset** of the allowed-files list in §2.
12. **A batch report** at `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_REPORT.md` is produced (separately committed under separate approval) documenting evidence, test results, and any deferred follow-ups.

If any of the 12 conditions fails, the batch is **rejected** (see §9).

---

## 9. Rejection criteria

The implementation batch is **rejected** if any of the following occurs:

| Trigger | Rejection reason |
|---|---|
| **More than 4 rows** added | Row-count lock (§4) violated. |
| **Any deferred verb** (تَرَكَ, رَدَّ, تَخِذَ, وَهَبَ, كان family, مُقارَبَة, مَدْح/ذَمّ, تَضمين examples, etc.) included | Scope-deferral lock (§10) violated. |
| **Any file outside the §2 allow-list** modified | Allowed-files lock (§2) violated. |
| **Any file in the §3 forbidden list** modified without lifting the conditional clause via a failing-test artifact | Forbidden-files lock (§3) violated. |
| **`schema.md` modified** | Schema lock (§5) violated. |
| **Any new column / column rename / column reorder** | Schema lock (§5) violated. |
| **Inline operator meanings introduced in Python code** | Hard rule (handoff §2.1) violated. |
| **Any new `proof_kind` value** introduced beyond `{Certificate, Hypothesis, Zero}` | ProofKind lock (§6) violated. |
| **A code path is added that upgrades ProofKind** (Hypothesis → Certificate anywhere) | Batch B monotonicity (handoff §2.6) violated. |
| **An external source** is cited or consumed (Ibn Hisham, modern Arabic, NAA, etc.) | Source restriction (§1) violated. |
| **Any required test in §7** is missing | Test-suite lock (§7) violated. |
| **`test_production_path_segmentation.py` regresses** below 158/158 | Cross-suite regression (§7.5) failed. |
| **`test_maani_batch_b_author_position.py` regresses** below 6/6 | Cross-suite regression (§7.5) failed. |
| **A Certificate-grade transformation reading** is emitted on a known non-transformation usage of جَعَلَ or اِتَّخَذَ | Polysemy safety (§4 warnings + §7.3 T8) violated. |
| **Untracked artifacts** (`out_*.txt`, `.pyc`, etc.) left in the committed tree | Hygiene lock (§3.8) violated. |
| **Goldens regress** for the four MASAQ goldens (2:282, 2:196, 28:7, 1:1) | Cross-track stability violated. |

Rejection is total — partial acceptance is not permitted. A rejected batch must be reverted (see §10) before any retry is attempted.

---

## 10. Rollback criteria

If the batch is rejected per §9 or fails review after implementation, the rollback procedure is:

1. **Revert the new CSV**: delete `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv`.
2. **Revert the new test file**: delete `clean_code/test_maani_batch_c_afal_tahwil.py`.
3. **Revert the optional `volume2_loader.py` edit** only if it was made.
4. **No data migration outside Batch C** is undone — Batches A, B, and all MASAQ commits remain untouched.
5. **Restore working tree to pre-implementation state**: `git status` must report only `.claude/` untracked.
6. **Stash list and prior commits** must not be touched in the rollback. Rollback only undoes Batch C's own additions.

If the rollback itself requires destructive operations (e.g., the implementation was committed before review and needs `git revert`), use `git revert <commit-hash>` to create a new revert commit. **Do not force-push.** Do not amend the rejected commit. Standard `git revert` discipline only.

---

## 11. Governance

### 11.1 Approval gates

This RULE_LOCK governs the **implementation batch only**. The implementation batch has its own approval gates which must be passed in order:

1. **RULE_LOCK approval** — this document. (Pending review at time of writing.)
2. **Loader auto-discovery investigation** — read-only, see SPEC §6.5. The result of this investigation determines whether T9 (loader test) is required and whether the optional `volume2_loader.py` edit in §2 is invoked. Investigation requires explicit approval before it runs.
3. **Implementation approval** — separate explicit approval after RULE_LOCK is committed. The implementation may not begin until this gate is passed.
4. **Test approval** — after implementation, the implementer must report test results. User reviews the test results before commit.
5. **Commit approval** — separate explicit approval for the implementation commit hash, not just the patch contents.
6. **Report approval** — `MAANI_BATCH_C_AFAL_TAHWIL_REPORT.md` written and committed under separate approval after the implementation commit lands.

Skipping any gate rejects the batch (§9).

### 11.2 What changes inside Batch C are NEVER allowed
- Schema changes (§5).
- ProofKind enum changes (§6).
- Touching any forbidden file in §3 without producing a failing-test artifact justifying the conditional lift.
- Adding rows beyond the 4 locked in §4.
- Including any deferred verb or family from §3.6 of the SPEC.
- Citing or consuming any non-Samarrai source.

### 11.3 What changes require a new RULE_LOCK (NOT this one)
- Adding the remaining transformation verbs (تَرَكَ, رَدَّ, تَخِذَ, وَهَبَ) — requires a Batch C₂ RULE_LOCK.
- Extending the MeaningGraph edge whitelist to include `AFAL_TAHWIL` — requires a follow-up RULE_LOCK with smoke evidence.
- Any conditions/exceptions matcher (Vector V2 of the handoff) — separate batch, separate RULE_LOCK.
- Schema extension to add `source_school` or any other column — separate schema-extension batch.

### 11.4 What is explicitly out of scope for the entire MAANI track
Per the handoff §9.1 (constitutional limits):

- ALASMA Stages 10–17 — separate SPECs / RULE_LOCKs; not touchable from MAANI.
- Hidden-pronoun thread — separate RULE_LOCK; not touchable.
- Phase 5 ClauseGraph integration — separate track.
- Balagha / rhetorical layer — explicitly deferred to a future track with its own SPEC.

Batch C must respect these constitutional limits. Any drift is total rejection.

### 11.5 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. Run `git log --oneline -20` to confirm no in-flight commits on MASAQ-related files since this RULE_LOCK.
2. Run `git status` to confirm the working tree is clean except for `.claude/`.
3. Check `git stash list` to confirm no untracked WIP exists that could be re-applied.

If any of these checks reveal concurrent activity on MASAQ / versebyverse / hidden-pronoun tracks, postpone Batch C implementation until the activity completes.

---

## 12. Source-traceability lock

Every row content element in §4 must be traceable to the source rule card `AFAL_AL_TAHWIL__P2_001`:

| Row element | Source field in rule card |
|---|---|
| `meaning_ar` (framework) | `syntactic_effect` + `semantic_effect` (composed) |
| `conditions` (framework) | `conditions` (verbatim or close paraphrase) |
| `exceptions` (Row 2) | `exceptions_or_warnings[0]` (verbatim or close paraphrase) |
| `warnings` (Row 2) | `exceptions_or_warnings[0]` (mandatory propagation per §4 Row 2 lock) |
| `warnings` (Row 3) | `exceptions_or_warnings[1]` (mandatory propagation per §4 Row 3 lock) |
| `example_quran` (Row 1) | `examples[1].text` + `examples[1].source` |
| `example_quran` (Row 2) | `examples[2].text` + `examples[2].source` |
| `example_quran` (Row 3) | `examples[1].text` + `examples[1].source` |
| `example_quran` (Row 4) | **MUST BE EMPTY** — no rule-card anchor available |
| `source_part` | `source.part` |
| `source_page` | within `[source.page_start, source.page_end]` = `[26, 279]` |
| `confidence` | derived from `source.confidence` = `0.93`; framework row may use `0.95` per ZANN precedent |
| `author_position` | derived from rule-card narrative (`السَّامَرَّائيّ يُفَرِّق المَعاني المُتَعَدِّدَة لِـ جَعَل`); maps to `"preferred"` |

Any row content that is **not** traceable to one of the above source elements is **not admissible** in Batch C.

---

## 13. One-screen recap

| Item | Value |
|---|---|
| Batch | C |
| Family | أَفعال التَّحويل (Samarrai's transformation verbs) |
| Source | rule_cards.jsonl row AFAL_AL_TAHWIL__P2_001 |
| Provenance | Vol 2, pp. 26–279, confidence 0.93 |
| New CSV path | `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` |
| New test path | `clean_code/test_maani_batch_c_afal_tahwil.py` |
| Optional code edit | `clean_code/samarrai_loaders/volume2_loader.py` (one-line; only if needed) |
| Row count | exactly 4 (framework + جَعَلَ + اِتَّخَذَ + صَيَّرَ) |
| Total MAANI rows after | 249 (was 245) |
| Schema | unchanged 19-column |
| ProofKind enum | unchanged |
| Tests | 6 required + 2 negatives + 1 conditional = 8 or 9 |
| Cross-suite regression | test_production_path_segmentation.py 158/158; test_maani_batch_b_author_position.py 6/6 |
| Forbidden | i3rab, MASAQ, L6/L7/L8, schema.md, external sources, bulk migration, deferred verbs |
| Conditional-forbidden lift | requires failing-test artifact |
| Rollback | delete new CSV + test (+ optional loader edit); no other files affected |
| Governance | SPEC → RULE_LOCK (this) → investigation → implementation → tests → commit → report — each gate requires explicit approval |
