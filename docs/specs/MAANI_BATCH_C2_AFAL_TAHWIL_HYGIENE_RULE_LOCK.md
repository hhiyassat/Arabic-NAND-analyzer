# MAANI Batch C₂ — AFAL_TAHWIL Hygiene & Migration — RULE_LOCK

> **Type:** RULE_LOCK (binding contract).
> **Date:** 2026-05-30
> **SPEC parent:** `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_SPEC_DRAFT.md` (commit `667e94b`).
> **Supersedes (for implementation):** `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (commit `6d91650`) and `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_RULE_LOCK.md` (commit `e1474ab`). Those documents remain in git history unchanged; this RULE_LOCK is the binding contract for the C₂ implementation.
> **Status:** Binding. Any violation rejects the batch.

Once approved, the boundaries below cannot be widened inside this batch. Any widening requires a new RULE_LOCK and a new batch.

---

## 0. Gate 2 findings (embedded preamble)

This RULE_LOCK is grounded in the read-only investigations completed on 2026-05-30 prior to drafting. The findings are reproduced here so the binding contract is anchored in current repo state, not in stale assumptions.

| # | Investigation | Finding (as of 2026-05-30 against commit `667e94b`) |
|---|---|---|
| 1 | Loader auto-discovery | `clean_code/samarrai_loaders/volume2_loader.py` uses a hardcoded `CSV_FILES` list (lines 46–51, 4 entries). No `glob`/`listdir`/`iterdir`/`os.walk`/`Path.rglob` primitives. **Loader edit is required**, not conditional. |
| 2 | Reference scan | Zero Python (non-test), zero test, zero docs (`TESTS.md`, `RULES.md`) references to the 4 migrated `meaning_id` strings. The only references outside the source CSV row itself are 139 lines in `clean_code/data/samarrai_sweep/per_word.csv` (regenerable artifact). |
| 3 | Row audit | `zann_family_meanings.csv` contains exactly 16 data rows + 1 header line; rows 11–14 are the 4 transformation rows in scope. Provenance fields verified verbatim. |
| 4 | Rule-card alignment | Rule card `AFAL_AL_TAHWIL__P2_001` lists `[جعل, اتخذ, ترك, صير, رد, تخذ, وهب]` as `trigger.lemmas` with `construction_parent: ZANN_WA_AKHAWATUHA`. All 4 migrate candidates align to existing ZANN rows. `رَدَّ` / `تَخِذَ` / `وَهَبَ` have no existing ZANN row — deferred (out of hygiene scope). |
| 5 | Baselines | `test_maani_batch_b_author_position.py` 6/6; `test_production_path_segmentation.py` 158/158. Batch B test has zero references to migrated `meaning_id`s — no test edits needed inside C₂. |
| 6 | Sweep generator | `clean_code/samarrai_quran_sweep.py` exists (202 lines), CLI-runnable (`python3 samarrai_quran_sweep.py`), deterministic, produces 5 outputs in `clean_code/data/samarrai_sweep/`. Regeneration is feasible in-batch. |

Any drift from these findings between this RULE_LOCK approval and implementation execution requires re-investigation, not silent adaptation.

---

## 1. Batch identity

| Field | Value |
|---|---|
| Batch name | **MAANI Batch C₂ — AFAL_TAHWIL Hygiene & Migration** |
| Parent SPEC | `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_SPEC_DRAFT.md` (commit `667e94b`) |
| Purpose | Make `AFAL_TAHWIL` the single proper home for Samarrai transformation-verb claims; eliminate duplicate curated facts between `ZANN_FAMILY` and `AFAL_TAHWIL`. |
| Source restriction | **Samarrai only** |
| Source artifact | `maani_alnahw/data/processed/maani_alnahw/rule_cards.jsonl`, row id `AFAL_AL_TAHWIL__P2_001`; plus the existing `zann_family_meanings.csv` rows 11–14 (source of the migrated content). |
| Source provenance | Vol 2, pp. 26 – 279; rule-card confidence `0.93`; existing-row confidence per migrated row (preserved verbatim — see §10). |

No other source may be cited or consumed in C₂. No external classical scholars, no modern Arabic, no NAA, no `meaning_cards.jsonl`, no `semantic_claims.jsonl`, no `construction_rules.jsonl`, no `operators_enriched.jsonl`. Evidence outside the source artifacts above is **not admissible** for C₂ row content.

---

## 2. Core invariant (binding)

> **لا تخزّن ما تستطيع توليده** — *Do not duplicate curated facts.*

Operationalized as four binding rules:

| # | Rule | Test gate |
|---|---|---|
| I1 | No operator carries transformation-class claims under two `topic_id`s simultaneously. | §11 test H1 |
| I2 | If a claim already exists, migrate it; do not re-encode it. Adding a new `AFAL_TAHWIL_X` row for an operator that has a transformation-classified ZANN_FAMILY row requires removing that ZANN_FAMILY row in the same batch. | §11 tests H1 + H2 |
| I3 | Migration preserves `author_position` verbatim. A `reported` row remains `reported` (→ Hypothesis); a `preferred` row remains `preferred` (→ Certificate). No silent flips. | §11 test H3 |
| I4 | Migration preserves provenance (`source_part`, `source_page`, `confidence`) verbatim per row. | §11 test H4 |

Violating any of I1–I4 rejects the batch (§13).

---

## 3. Allowed implementation files (exactly 9)

The implementation batch may touch ONLY these paths:

| # | Path | Purpose | Required / Conditional |
|---|---|---|---|
| 1 | `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` | Remove rows 11–14; surgical edit to `ZANN_BASIC.conditions` (see §7.3) | **Required** |
| 2 | `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` | New file; framework row + 4 migrated rows | **Required** |
| 3 | `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` | New test file (see §11) | **Required** |
| 4 | `clean_code/samarrai_loaders/volume2_loader.py` | One-line addition to `CSV_FILES` list | **Required** (Gate-2 §0 row 1 confirms necessity) |
| 5 | `clean_code/data/samarrai_sweep/per_word.csv` | Regenerated by sweep | **Required** (§9) |
| 6 | `clean_code/data/samarrai_sweep/top_topics.csv` | Regenerated by sweep | **Required** (§9) |
| 7 | `clean_code/data/samarrai_sweep/per_verse.csv` | Regenerated by sweep | **Required** (§9, consistency) |
| 8 | `clean_code/data/samarrai_sweep/constructions.csv` | Regenerated by sweep | **Required** (§9, consistency) |
| 9 | `clean_code/data/samarrai_sweep/summary.txt` | Regenerated by sweep | **Required** (§9, consistency) |

The implementation batch's `git diff --name-only` must be **exactly this 9-file set, no more and no less** (the 9 are all promoted to required by Gate-2 findings; conditional clauses are exhausted). Any file outside this list appearing in the diff is grounds for rejection (§13).

---

## 4. Forbidden files (binding)

The following files **MUST NOT** be modified in C₂. Any modification rejects the batch.

### 4.1 i3rab / parser surface (hard-forbidden)
- `clean_code/i3rab_engine/*` — entire subtree
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`

### 4.2 Downstream layers (hard-forbidden)
- `clean_code/event_extractor.py`
- `clean_code/relation_extractor.py`
- `clean_code/resolution_engine.py`
- `clean_code/reasoning_engine.py`
- `clean_code/meaning_assembler.py`
- `clean_code/samarrai_analyzer.py`
- `clean_code/samarrai_certified_operator_gate.py`

Unlike the prior RULE_LOCK `e1474ab`, **C₂ has no conditional-forbidden lift clause** for the downstream layers. Gate 2 found zero Python code references to the migrated `meaning_id`s; therefore there is no plausible scenario in which the migration could require editing these files. Any attempt to lift the forbid is automatic rejection.

### 4.3 Schema / governance / sweep generator
- `clean_code/data/contracts/maani/schema.md` — schema locked at 19 columns (§8).
- `clean_code/samarrai_quran_sweep.py` — the sweep **generator** is forbidden from edits; only its **outputs** (allow-list entries 5–9 in §3) may change. Running the generator is allowed; editing it is not.
- All other files under `docs/specs/` except this RULE_LOCK file. No "while we're here" doc edits.
- `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_SPEC_DRAFT.md` (commit `6d91650`) — frozen historical artifact.
- `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_RULE_LOCK.md` (commit `e1474ab`) — frozen historical artifact.
- `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_SPEC_DRAFT.md` (commit `667e94b`) — frozen reference; do not amend.

### 4.4 MASAQ surface (hard-forbidden)
- Any file containing "masaq" in its path.
- All MASAQ-related committed paths.

### 4.5 Other tracks (hard-forbidden)
- `data/contracts/maani/**` outside the two allowed CSV paths in §3 (entries 1 + 2). No edits to `volume1/*`, `volume3/*`, `volume4/*`, `constructions/*`, or any other `volume2/*.csv` besides `zann_family_meanings.csv` and `transform_verbs_meanings.csv`.
- `data/contracts/lists/*`
- `data/contracts/rules/*`
- `data/contracts/translations/*`
- `data/MASAQ.csv`
- `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**` — read-only reference. No edits to the source JSONL.
- `new_arabic_analyzer/**`
- `archive/**`

### 4.6 No new or edited test files outside the C₂ test file
- `clean_code/test_production_path_segmentation.py` — unchanged.
- `clean_code/test_maani_batch_b_author_position.py` — unchanged (Gate-2 §0 row 5 confirms it has zero references to migrated `meaning_id`s).
- `clean_code/test_phase4_certificate_reevaluation.py` — unchanged.
- All other existing test files — unchanged.

### 4.7 No untracked artifacts left behind
- No `out_*.txt`.
- No `.pyc` modifications committed.
- No `.claude/` content committed.
- No stash content reintroduced.

---

## 5. Locked target row state (precise counts)

After the implementation batch, the row state must be **exactly**:

### 5.1 `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` (new)

- **6 lines total** = 1 header line + 5 data rows.
- The 5 data rows are: 1 framework row + 4 migrated verb rows.
- Adding fewer or more data rows rejects the batch.

### 5.2 `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` (existing, after rows removed)

- **Before:** 17 lines total = 1 header line + 16 data rows.
- **After:** 13 lines total = 1 header line + 12 data rows.
- The 4 removed rows are exactly the rows whose `meaning_id` is in `{JAALA_VERB, ITTAKHADHA_VERB, SAYYARA_VERB, TARAKA_TRANS}`.
- All other rows remain unchanged in content **except** for the `conditions` field of the `ZANN_BASIC` row (see §7.3).

### 5.3 Total MAANI row count

- Before C₂: 245 MAANI rows total (per Batch B report).
- After C₂: **246** MAANI rows total (−4 from ZANN + 5 new in transform_verbs = +1 net, accounting for the framework row).

Any other row count rejects the batch.

---

## 6. Locked migrated rows (field-by-field)

The 4 migrated rows in `transform_verbs_meanings.csv` carry **content copied verbatim from the source rows in `zann_family_meanings.csv`**, with exactly three field-level changes per row:
- `priority` is reassigned per the new file's ordering.
- `topic_id` changes from `ZANN_FAMILY` → `AFAL_TAHWIL`.
- `meaning_id` changes per the rename map below.

No other field may be silently changed. In particular, `vocalized_form`, `meaning_ar`, `syntactic_effect`, `semantic_field`, `conditions`, `exceptions`, `warnings`, `example_constructed`, `example_quran`, `surah_ayah`, `author_position`, `disagreement`, `source_part`, `source_page`, `confidence` are all **carried verbatim** from the source row (no re-curation, no normalization, no formatting changes — including whitespace and trailing punctuation).

### 6.1 Rename map (binding)

| Source row `meaning_id` | New row `meaning_id` |
|---|---|
| `JAALA_VERB` | `AFAL_TAHWIL_JAAL` |
| `ITTAKHADHA_VERB` | `AFAL_TAHWIL_ITTAKHATHA` |
| `SAYYARA_VERB` | `AFAL_TAHWIL_SAYYARA` |
| `TARAKA_TRANS` | `AFAL_TAHWIL_TARAKA` |

No aliases retained. Old IDs do not appear anywhere in the post-migration tree (verified by §11 test H6).

### 6.2 Row 2 — جَعَلَ (migrated from `JAALA_VERB`)

| Field | Required value |
|---|---|
| `priority` | `2` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `جَعَلَ` *(verbatim from source row)* |
| `vocalized_form` | `جَعَلَ` *(verbatim — preserved)* |
| `meaning_id` | `AFAL_TAHWIL_JAAL` *(renamed per §6.1)* |
| `meaning_ar` | `جَعَلَ مِن أَفعال التَّحويل — تَنصِب مَفعولَين` *(verbatim from source row)* |
| `syntactic_effect` | `nasb_two_objects` *(verbatim)* |
| `semantic_field` | `causative_transformation` *(verbatim)* |
| `conditions` | `مِن أَفعال التَّحويل` *(verbatim)* |
| `exceptions` | `قَد تَأتي بِمَعنى خَلَقَ أَو ظَنَّ` *(verbatim)* |
| `warnings` | `لا تَخلِط بَين أَنواعها` *(verbatim)* |
| `example_constructed` | `جَعَلتُ الطِّينَ خَزَفًا` *(verbatim)* |
| `example_quran` | `وَجَعَلَ الْقَمَرَ فِيهِنَّ نُورًا` *(verbatim)* |
| `surah_ayah` | `نوح:16` *(verbatim)* |
| `author_position` | `preferred` *(preserved → Certificate)* |
| `disagreement` | *(empty — verbatim)* |
| `source_part` | `2` *(preserved)* |
| `source_page` | `26` *(preserved)* |
| `confidence` | `0.92` *(preserved — NOT normalized to 0.93)* |

### 6.3 Row 3 — اتَّخَذَ (migrated from `ITTAKHADHA_VERB`)

| Field | Required value |
|---|---|
| `priority` | `3` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `اتَّخَذَ` *(verbatim — WITHOUT initial kasra; see §10.1)* |
| `vocalized_form` | `اتَّخَذَ` *(verbatim — WITHOUT initial kasra; see §10.1)* |
| `meaning_id` | `AFAL_TAHWIL_ITTAKHATHA` |
| `meaning_ar` | `اتَّخَذَ بِمَعنى التَّحويل تَنصِب مَفعولَين، بِمَعنى الأَخذ تَنصِب مَفعولًا` *(verbatim)* |
| `syntactic_effect` | `nasb_two_or_one` *(verbatim)* |
| `semantic_field` | `transformation_or_taking` *(verbatim)* |
| `conditions` | `بِحَسَب valency` *(verbatim)* |
| `exceptions` | `لا تَخلِط بَين المَعنَيَين` *(verbatim)* |
| `warnings` | *(empty — verbatim from source row, which leaves `warnings` empty for ITTAKHADHA_VERB)* |
| `example_constructed` | *(empty — verbatim)* |
| `example_quran` | `اتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` *(verbatim)* |
| `surah_ayah` | `النساء:125` *(verbatim)* |
| `author_position` | `preferred` *(preserved → Certificate)* |
| `disagreement` | *(empty — verbatim)* |
| `source_part` | `2` *(preserved)* |
| `source_page` | `26` *(preserved)* |
| `confidence` | `0.92` *(preserved)* |

### 6.4 Row 4 — صَيَّرَ (migrated from `SAYYARA_VERB`)

| Field | Required value |
|---|---|
| `priority` | `4` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `صَيَّرَ` *(verbatim)* |
| `vocalized_form` | `صَيَّرَ` *(verbatim)* |
| `meaning_id` | `AFAL_TAHWIL_SAYYARA` |
| `meaning_ar` | `صَيَّرَ مِن أَفعال التَّحويل المَحضَة` *(verbatim)* |
| `syntactic_effect` | `nasb_two_objects` *(verbatim)* |
| `semantic_field` | `pure_transformation` *(verbatim)* |
| `conditions` | `مِن أَفعال التَّحويل` *(verbatim)* |
| `exceptions` | *(empty — verbatim)* |
| `warnings` | *(empty — verbatim)* |
| `example_constructed` | `صَيَّرتُ الطِّينَ خَزَفًا` *(verbatim)* |
| `example_quran` | *(empty — verbatim)* |
| `surah_ayah` | *(empty — verbatim)* |
| `author_position` | **`reported`** *(preserved → Hypothesis; NO silent upgrade to `preferred`)* |
| `disagreement` | *(empty — verbatim)* |
| `source_part` | `2` *(preserved)* |
| `source_page` | `26` *(preserved)* |
| `confidence` | `0.9` *(preserved — NOT normalized to 0.93)* |

### 6.5 Row 5 — تَرَكَ (migrated from `TARAKA_TRANS`)

| Field | Required value |
|---|---|
| `priority` | `5` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `تَرَكَ` *(verbatim)* |
| `vocalized_form` | `تَرَكَ` *(verbatim)* |
| `meaning_id` | `AFAL_TAHWIL_TARAKA` |
| `meaning_ar` | `تَرَكَ مِن أَفعال التَّحويل بِمَعنى صَيَّرَ،` *(verbatim — including the trailing Arabic comma `،` present in the source row)* |
| `syntactic_effect` | `nasb_two_objects` *(verbatim)* |
| `semantic_field` | `transformation_via_leaving` *(verbatim)* |
| `conditions` | `بِمَعنى التَّحويل` *(verbatim)* |
| `exceptions` | `بِمَعنى الهَجر تَنصِب مَفعولًا واحِدًا` *(verbatim)* |
| `warnings` | *(empty — verbatim)* |
| `example_constructed` | `تَرَكتُ زَيدًا قائِمًا` *(verbatim)* |
| `example_quran` | `فَتَرَكَهُ صَلْدًا` *(verbatim)* |
| `surah_ayah` | `البقرة:264` *(verbatim)* |
| `author_position` | **`reported`** *(preserved → Hypothesis; NO silent upgrade)* |
| `disagreement` | *(empty — verbatim)* |
| `source_part` | `2` *(preserved)* |
| `source_page` | `26` *(preserved)* |
| `confidence` | `0.88` *(preserved — NOT normalized to 0.93)* |

---

## 7. Other locked changes

### 7.1 Framework row — Row 1 of `transform_verbs_meanings.csv` (new content)

| Field | Required value |
|---|---|
| `priority` | `1` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `—` |
| `vocalized_form` | `—` |
| `meaning_id` | `AFAL_TAHWIL_BASIC` |
| `meaning_ar` | Must begin with `أفعال التحويل / التصيير` and describe the two-object causative-transformation construction. Recommended text per SPEC `667e94b` §6.1 / prior SPEC `6d91650` §4 Row 1. |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `conditions` | Per SPEC `6d91650` §4 Row 1 (the two-condition list from rule card `AFAL_AL_TAHWIL__P2_001`) |
| `exceptions` | Per SPEC `6d91650` §4 Row 1 |
| `warnings` | Per SPEC `6d91650` §4 Row 1 |
| `example_constructed` | `جَعَلْتُ الطِّينَ خَزَفًا` |
| `example_quran` | `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` |
| `surah_ayah` | `النساء:125` |
| `author_position` | `preferred` |
| `disagreement` | *(empty)* |
| `source_part` | `2` |
| `source_page` | `26` |
| `confidence` | `0.95` (framework-row precedent; matches `ZANN_BASIC`'s 0.95) |

The framework row is the **only** new curated content in C₂. Its source is the rule card `AFAL_AL_TAHWIL__P2_001`; deviation from that source's content rejects the batch.

### 7.2 Locked deletions in `zann_family_meanings.csv`

The implementation must delete **exactly four rows** from `zann_family_meanings.csv`, identified by `meaning_id`:

1. The row with `meaning_id = "JAALA_VERB"` (currently line 12 / row 11)
2. The row with `meaning_id = "ITTAKHADHA_VERB"` (currently line 13 / row 12)
3. The row with `meaning_id = "SAYYARA_VERB"` (currently line 14 / row 13)
4. The row with `meaning_id = "TARAKA_TRANS"` (currently line 15 / row 14)

After deletion, the remaining `priority` column values may be renumbered to be contiguous (`1..12`) **or** left as-is (with gaps at the removed positions). Both are acceptable. RULE_LOCK does not mandate renumbering. The implementation report must declare which choice was made.

### 7.3 Locked surgical edit to `ZANN_BASIC` (the only field edit allowed in `zann_family_meanings.csv`)

**Clarification — field-location correction.** The SPEC §4.5 spoke of rewriting `ZANN_BASIC.meaning_ar` to remove an inaccurate "أو التحويل" phrase. Gate-2 Investigation 3 verified that the actual location of the phrase is the **`conditions`** column, **not** `meaning_ar`. The user's intent (remove the now-inaccurate transformation reference) governs; the field-name correction is reflected here so the implementation is unambiguous.

**Required edit, exactly one cell in `zann_family_meanings.csv`:**

- Row: the row with `meaning_id = "ZANN_BASIC"` (currently line 2 / row 1).
- Column: `conditions`.
- Before: `أَن يَكون الفِعل مِن أَفعال القُلوب أَو التَّحويل النَّاصِبَة لِمَفعولَين`
- After: `أَن يَكون الفِعل مِن أَفعال القُلوب النَّاصِبَة لِمَفعولَين`

That is, the substring `أَو التَّحويل ` (including the trailing space) is removed; nothing else in the cell is changed.

No other field of `ZANN_BASIC` is edited. No other row of `zann_family_meanings.csv` is edited (besides the four deletions in §7.2). The 11 retained verb/principle rows (ZANN_VERB, HASIB_VERB, KHAL_VERB, ZAEM_VERB, ALIMA_VERB, RAA_VERB, WAJADA_VERB, ALFA_VERB, DARA_VERB, TALEEQ_PRINCIPLE, DHIKR_HADHF_PRINCIPLE) are bit-for-bit unchanged.

### 7.4 Locked loader edit

In `clean_code/samarrai_loaders/volume2_loader.py`, exactly one line is added to the `CSV_FILES` list (placement at the end of the list is required for diff cleanliness):

```python
    ("transform_verbs", "transform_verbs_meanings.csv"),
```

No other change to the loader. No logic edit. No comment edit. No whitespace edit elsewhere in the file.

---

## 8. Schema lock

- The 19-column schema in `clean_code/data/contracts/maani/schema.md` is unchanged. No additions, renames, or reorders.
- `schema.md` is not edited.
- No new column types.
- No inline operator meanings in Python code.
- The new `topic_id` value `AFAL_TAHWIL` is an open-set entry (consistent with how new topic_ids have shipped historically). Not a schema change.
- The header line of `transform_verbs_meanings.csv` must be exactly the 19-column schema, in order:
  `priority,topic_id,operator,vocalized_form,meaning_id,meaning_ar,syntactic_effect,semantic_field,conditions,exceptions,warnings,example_constructed,example_quran,surah_ayah,author_position,disagreement,source_part,source_page,confidence`

---

## 9. ProofKind lock & sweep regeneration policy

### 9.1 ProofKind enum (unchanged)
- `{Certificate, Hypothesis, Zero}`. No new values.
- `Certificate` ← `match_type == "exact_vocalized"` AND `author_position != "reported"`.
- `Hypothesis` ← `match_type in {"prefix_stripped", "prefix_as_operator", "pattern_construction"}` OR `author_position == "reported"`.
- `Zero` ← no match, blacklisted topic, or gate rejection.
- Batch B monotonicity (Certificate may only DOWNGRADE to Hypothesis, never upgrade) is preserved. C₂ adds no code path that increases proof-kind certainty.

### 9.2 ProofKind impact of migration (binding)

| Operator | Migrated `author_position` | Resulting ProofKind for `exact_vocalized` match |
|---|---|---|
| جَعَلَ → `AFAL_TAHWIL_JAAL` | `preferred` | `Certificate` |
| اتَّخَذَ → `AFAL_TAHWIL_ITTAKHATHA` | `preferred` | `Certificate` |
| صَيَّرَ → `AFAL_TAHWIL_SAYYARA` | **`reported`** | **`Hypothesis`** |
| تَرَكَ → `AFAL_TAHWIL_TARAKA` | **`reported`** | **`Hypothesis`** |
| Framework `AFAL_TAHWIL_BASIC` | `preferred` | `Certificate` (when matched) |

Producing `Certificate` for `AFAL_TAHWIL_SAYYARA` or `AFAL_TAHWIL_TARAKA` rejects the batch (§13).

### 9.3 Sweep regeneration policy
- The Samarrai sweep artifacts must be regenerated by running `python3 clean_code/samarrai_quran_sweep.py` from the project root after the CSV migration is complete and the loader edit is in place.
- **Hand-editing sweep outputs is forbidden** (§4.3). Sweep outputs are admitted into the allow-list (§3 entries 5–9) **only** because they are generated artifacts.
- The regenerated outputs must reflect the new topic state: zero stale `JAALA_VERB` / `ITTAKHADHA_VERB` / `SAYYARA_VERB` / `TARAKA_TRANS` strings in `per_word.csv`; an `AFAL_TAHWIL` row in `top_topics.csv`.
- The generator must be run from the same Python environment as the test suite to ensure deterministic output. The implementer reports the Python version + the row counts of the regenerated files in the C₂ report.

---

## 10. Vocalization and provenance lock

### 10.1 Vocalization lock

For each migrated row, the `vocalized_form` and `operator` values are **carried verbatim from the source row**. Specifically:

| Source row | Source `vocalized_form` | Migrated `vocalized_form` | Note |
|---|---|---|---|
| `JAALA_VERB` | `جَعَلَ` | `جَعَلَ` | Same |
| `ITTAKHADHA_VERB` | `اتَّخَذَ` *(WITHOUT initial kasra)* | `اتَّخَذَ` *(WITHOUT initial kasra)* | **Important** — the prior Batch C SPEC `6d91650` §4 Row 3 suggested `اِتَّخَذَ` with initial kasra. C₂ **rejects** that change. Vocalization re-curation is a separate deferred batch; the migration preserves the existing form. |
| `SAYYARA_VERB` | `صَيَّرَ` | `صَيَّرَ` | Same |
| `TARAKA_TRANS` | `تَرَكَ` | `تَرَكَ` | Same |

Any vocalization change inside C₂ rejects the batch (§13).

### 10.2 Provenance lock

For each migrated row, the values of `source_part`, `source_page`, and `confidence` are **bit-for-bit identical** to the source row:

| Migrated row | `source_part` | `source_page` | `confidence` |
|---|:---:|:---:|:---:|
| `AFAL_TAHWIL_JAAL` | `2` | `26` | `0.92` |
| `AFAL_TAHWIL_ITTAKHATHA` | `2` | `26` | `0.92` |
| `AFAL_TAHWIL_SAYYARA` | `2` | `26` | `0.9` |
| `AFAL_TAHWIL_TARAKA` | `2` | `26` | `0.88` |

Normalizing `0.9` to `0.90` or `0.93` rejects the batch. Normalizing `0.88` to `0.93` rejects the batch.

### 10.3 author_position lock

For each migrated row, `author_position` is **bit-for-bit identical** to the source row:

| Migrated row | `author_position` |
|---|---|
| `AFAL_TAHWIL_JAAL` | `preferred` |
| `AFAL_TAHWIL_ITTAKHATHA` | `preferred` |
| `AFAL_TAHWIL_SAYYARA` | **`reported`** |
| `AFAL_TAHWIL_TARAKA` | **`reported`** |

A silent change of `reported` to `preferred` (or vice versa) rejects the batch (§13).

---

## 11. Tests required

The implementation batch must add **all** of the following tests to `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py`. If any required test is missing, the implementation batch is rejected.

### 11.1 Structural tests (CSV-level)

| # | Test | Asserts |
|---|---|---|
| S1 | `t_transform_verbs_csv_header_matches_schema` | The new CSV's header row exactly matches the 19 columns of `schema.md`, in order, with no trailing/leading whitespace. |
| S2 | `t_transform_verbs_row_count_is_exactly_5` | The new CSV has exactly 5 data rows (6 lines total including header). |
| S3 | `t_zann_family_row_count_decreases_to_12` | `zann_family_meanings.csv` has exactly 12 data rows (13 lines including header) after migration. |
| S4 | `t_zann_family_holds_no_migrated_meaning_ids` | None of `{JAALA_VERB, ITTAKHADHA_VERB, SAYYARA_VERB, TARAKA_TRANS}` appears in `zann_family_meanings.csv`. |
| S5 | `t_loader_includes_transform_verbs_entry` | `volume2_loader.stats()["files"]` includes `"transform_verbs": 5`. |

### 11.2 Hygiene-invariant tests (the binding C₂ gates)

| # | Test | Asserts |
|---|---|---|
| H1 | `t_no_operator_carries_transformation_in_two_topics` | For each of `{جَعَلَ, اتَّخَذَ, صَيَّرَ, تَرَكَ}`, loading all volume2 records yields **exactly one** row whose `semantic_field` ∈ `{causative_transformation, transformation_or_taking, pure_transformation, transformation_via_leaving}` — and that row's `topic_id == "AFAL_TAHWIL"`. **Binding test for invariant I1.** |
| H2 | `t_zann_family_holds_no_transformation_rows` | Loading `zann_family_meanings.csv`, no row has `topic_id == "ZANN_FAMILY"` AND a transformation `semantic_field` value. **Binding test for invariant I2.** |
| H3 | `t_migrated_rows_preserve_author_position` | `AFAL_TAHWIL_JAAL`.author_position == `preferred`; `AFAL_TAHWIL_ITTAKHATHA`.author_position == `preferred`; `AFAL_TAHWIL_SAYYARA`.author_position == `reported`; `AFAL_TAHWIL_TARAKA`.author_position == `reported`. **Binding test for invariant I3.** |
| H4 | `t_migrated_rows_preserve_provenance` | For each migrated row, `(source_part, source_page, confidence)` is exactly `(2, 26, 0.92)` for jaal/ittakhatha, `(2, 26, 0.9)` for sayyara, `(2, 26, 0.88)` for taraka. **Binding test for invariant I4.** |
| H5 | `t_ittakhatha_vocalization_preserved` | `AFAL_TAHWIL_ITTAKHATHA`.vocalized_form starts with `ا` (alif without initial kasra), not `اِ`. Specifically, the first character is U+0627 ALEF followed by U+062A TEH, not U+0627 ALEF followed by U+0650 KASRA. |
| H6 | `t_no_legacy_meaning_id_strings_anywhere_in_csvs` | After migration, none of the four legacy `meaning_id` strings appears in any CSV under `clean_code/data/contracts/maani/`. |

### 11.3 Claim-level lookup tests

| # | Test | Asserts |
|---|---|---|
| C1 | `t_jaala_returns_one_afal_tahwil_certificate` | `samarrai_analyzer.lookup_word_all_volumes("جَعَلَ", "exact_vocalized")` returns at least one `SamarraiClaim` with `topic_id == "AFAL_TAHWIL"`, `meaning_id == "AFAL_TAHWIL_JAAL"`, `proof_kind == "Certificate"`. |
| C2 | `t_ittakhatha_returns_one_afal_tahwil_certificate` | Same for `اتَّخَذَ` → `AFAL_TAHWIL_ITTAKHATHA`, `Certificate`. The lookup key uses the **non-kasra** vocalization. |
| C3 | `t_sayyara_returns_one_afal_tahwil_hypothesis` | `صَيَّرَ` → `AFAL_TAHWIL_SAYYARA`, **`Hypothesis`** (because `author_position=="reported"`). |
| C4 | `t_taraka_returns_one_afal_tahwil_hypothesis` | `تَرَكَ` → `AFAL_TAHWIL_TARAKA`, **`Hypothesis`**. |
| C5 | `t_framework_row_loads` | `AFAL_TAHWIL_BASIC` is in `volume2_loader.all_records()` with `topic_id == "AFAL_TAHWIL"` and `meaning_ar` containing `أفعال التحويل / التصيير`. |
| C6 | `t_zann_cognition_verbs_still_return_zann_family` | `ظَنَّ`, `حَسِبَ`, `عَلِمَ`, `رَأَى`, `وَجَدَ` continue to return at least one `ZANN_FAMILY` claim; none returns an `AFAL_TAHWIL` claim. Boundary guard. |
| C7 | `t_no_duplicate_claims_for_migrated_operators` | For each of `{جَعَلَ, اتَّخَذَ, صَيَّرَ, تَرَكَ}`, the set of `topic_id`s returned by `lookup_word_all_volumes(op, "exact_vocalized")` is exactly `{"AFAL_TAHWIL"}` (no `ZANN_FAMILY` claim remains). |

### 11.4 Sweep regeneration tests

| # | Test | Asserts |
|---|---|---|
| R1 | `t_sweep_per_word_uses_new_meaning_ids` | `per_word.csv` contains zero rows referencing `{JAALA_VERB, ITTAKHADHA_VERB, SAYYARA_VERB, TARAKA_TRANS}`. May reference the new `AFAL_TAHWIL_*` IDs (count not asserted exactly — generator-dependent). |
| R2 | `t_sweep_top_topics_includes_afal_tahwil` | `top_topics.csv` contains a row whose `topic_id` is `AFAL_TAHWIL` with a count > 0. The `ZANN_FAMILY` row's count is strictly less than its pre-migration count of 313. |

### 11.5 Cross-suite regression
The implementation batch must verify (and the report must record) that all of the following remain green post-implementation:

- `clean_code/test_maani_batch_b_author_position.py` — must remain 6/6.
- `clean_code/test_production_path_segmentation.py` — must remain 158/158 (current baseline confirmed by Gate-2 Investigation 5).
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain at its current pass count.

Any suite regressing rejects the batch.

---

## 12. Acceptance criteria

The implementation batch is **acceptable** if and only if **all** of the following hold:

1. `transform_verbs_meanings.csv` has exactly 5 data rows + 1 header (§5.1).
2. `zann_family_meanings.csv` has exactly 12 data rows + 1 header (§5.2).
3. The 4 migrated rows match §6.2–§6.5 cell-for-cell, including vocalization (§10.1), provenance (§10.2), and author_position (§10.3).
4. The framework row matches §7.1.
5. The only edit to `zann_family_meanings.csv` outside the 4 deletions is the §7.3 surgical `ZANN_BASIC.conditions` edit.
6. Schema validation passes — header matches `schema.md` exactly (test S1).
7. Loader edit is exactly the one line in §7.4.
8. Sweep artifacts are regenerated, not hand-edited (§9.3); sweep tests R1 + R2 pass.
9. All §11.1 + §11.2 + §11.3 tests pass.
10. Cross-suite regression: Batch B 6/6, production 158/158, Phase 4 unchanged.
11. No file outside §3 is modified.
12. No file in §4 is modified.
13. No untracked artifacts (`out_*.txt`, `.pyc`, `.claude/` content) left in the committed tree.
14. The implementation diff is exactly the 9-file set in §3 — no more, no less.
15. A batch report at `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_REPORT.md` is produced (separately committed under separate approval) documenting evidence, test results, sweep regeneration provenance (Python version + row counts), and any flagged-for-followup findings.

If any of the 15 conditions fails, the batch is **rejected** (see §13).

---

## 13. Rejection criteria

The implementation batch is **rejected** if any of the following occurs:

| Trigger | Rejection reason |
|---|---|
| Any operator appears under two `topic_id`s with a transformation `semantic_field` post-migration | Invariant I1 violated. |
| Any source row (`JAALA_VERB`, etc.) remains in `zann_family_meanings.csv` | Invariant I2 violated. |
| Any migrated row's `author_position` differs from the source row's value | Invariant I3 violated (silent flip). |
| Any migrated row's `source_part`, `source_page`, or `confidence` differs from the source row's value | Invariant I4 violated. |
| `AFAL_TAHWIL_SAYYARA` or `AFAL_TAHWIL_TARAKA` emits `Certificate` | ProofKind lock §9.2 violated. |
| Any extra row beyond `{framework, jaal, ittakhatha, sayyara, taraka}` in `transform_verbs_meanings.csv` | Row-count lock §5.1 violated. |
| Any missing row from the 5-row set | Row-count lock §5.1 violated. |
| `zann_family_meanings.csv` has any data row count other than 12 | Row-count lock §5.2 violated. |
| Any field of any retained ZANN row is edited besides `ZANN_BASIC.conditions` per §7.3 | Locked-deletions discipline §7.2 violated. |
| `ZANN_BASIC.meaning_ar` is edited | §7.3 location-correction violated. |
| Vocalization of اتَّخَذَ changed to `اِتَّخَذَ` | §10.1 violated. |
| Any deferred verb (`رَدَّ`, `تَخِذَ`, `وَهَبَ`, or any non-AFAL_TAHWIL family) is introduced | Scope-deferral lock §1/§4.5 violated. |
| Any file outside §3 modified | Allowed-files lock §3 violated. |
| Any file in §4 modified | Forbidden-files lock §4 violated. |
| `schema.md` modified | Schema lock §8 violated. |
| `samarrai_quran_sweep.py` modified | §4.3 violated (the generator is forbidden). |
| Any new column / column rename / column reorder | Schema lock §8 violated. |
| Inline operator meanings introduced in Python code | Hard rule violated. |
| Any new `proof_kind` value beyond `{Certificate, Hypothesis, Zero}` | ProofKind lock §9.1 violated. |
| Any code path added that upgrades ProofKind | Batch B monotonicity violated. |
| Any external source cited or consumed | Source restriction §1 violated. |
| Any required test in §11 missing | Test-suite lock §11 violated. |
| `test_production_path_segmentation.py` regresses below 158/158 | Cross-suite regression §11.5 failed. |
| `test_maani_batch_b_author_position.py` regresses below 6/6 | Cross-suite regression §11.5 failed. |
| Sweep outputs hand-edited (not regenerated) | §9.3 violated. |
| Sweep outputs contain stale `JAALA_VERB` / `ITTAKHADHA_VERB` / `SAYYARA_VERB` / `TARAKA_TRANS` strings | §9.3 + §11.4 R1 violated. |
| Untracked artifacts left in committed tree | Hygiene lock §4.7 violated. |
| Goldens regress for MASAQ goldens (2:282, 2:196, 28:7, 1:1) | Cross-track stability violated. |

Rejection is total — partial acceptance is not permitted.

---

## 14. Rollback

If the batch is rejected per §13 or fails review after the implementation commit:

1. **Standard `git revert`** of the implementation commit. The revert restores `zann_family_meanings.csv` to its pre-migration content, deletes `transform_verbs_meanings.csv`, reverts the loader edit, deletes the test file, and reverts the sweep outputs to their pre-migration content.
2. **No force-push.** No `git reset --hard` on shared branches.
3. **No data outside C₂ is touched** in the rollback. Batches A, B, all MASAQ commits, and the historical artifacts (SPEC `6d91650`, RULE_LOCK `e1474ab`, SPEC `667e94b`) remain intact.
4. **Working tree post-revert** matches `667e94b` + `.claude/`.
5. **Stash list and prior commits** must not be touched in the rollback.

If the rollback itself requires destructive operations beyond `git revert`, halt and consult the user. Do not amend the rejected commit.

---

## 15. Source traceability

Every locked-row content element in §6 and §7.1 traces to either the rule card `AFAL_AL_TAHWIL__P2_001` or the existing source row in `zann_family_meanings.csv` (rows 11–14):

| Element | Source |
|---|---|
| Framework row `meaning_ar`, `conditions`, `exceptions`, `warnings` | Rule card `AFAL_AL_TAHWIL__P2_001` fields `syntactic_effect` + `semantic_effect` + `conditions` + `exceptions_or_warnings` (composed per SPEC `6d91650` §4 Row 1) |
| Framework row `example_quran` / `surah_ayah` | Rule card `examples[1].text` + `examples[1].source` |
| Migrated `AFAL_TAHWIL_JAAL` row content (all fields except topic_id/meaning_id/priority) | `zann_family_meanings.csv` row with `meaning_id="JAALA_VERB"` |
| Migrated `AFAL_TAHWIL_ITTAKHATHA` row content | `zann_family_meanings.csv` row with `meaning_id="ITTAKHADHA_VERB"` |
| Migrated `AFAL_TAHWIL_SAYYARA` row content | `zann_family_meanings.csv` row with `meaning_id="SAYYARA_VERB"` |
| Migrated `AFAL_TAHWIL_TARAKA` row content | `zann_family_meanings.csv` row with `meaning_id="TARAKA_TRANS"` |

Any row content not traceable to one of these sources is **not admissible** in C₂.

---

## 16. Governance

### 16.1 Approval gates (sequential; each requires separate explicit approval)

1. **SPEC review + approval** — `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_SPEC_DRAFT.md`. **Completed** at commit `667e94b`.
2. **Gate-2 read-only investigations** — **Completed** on 2026-05-30; findings embedded in §0 above.
3. **RULE_LOCK approval** — this document. *Pending review at time of writing.*
4. **Implementation approval** — separate explicit approval before any file under §3 is touched.
5. **Test approval** — after implementation, test results reported back to user.
6. **Commit approval** — user approves the specific commit hash for the implementation.
7. **Report approval** — `docs/specs/MAANI_BATCH_C2_AFAL_TAHWIL_HYGIENE_REPORT.md` written and committed under separate approval after the implementation commit lands.

Skipping any gate rejects the batch.

### 16.2 What is NEVER allowed inside C₂
- Schema changes (§8).
- ProofKind enum changes (§9.1).
- Editing the sweep generator `samarrai_quran_sweep.py` (§4.3).
- Touching any file in §4 (no conditional-lift clause — Gate 2 findings exhausted the conditional cases).
- Adding rows beyond the 5 locked in §5.1.
- Removing rows from `zann_family_meanings.csv` beyond the 4 locked in §7.2.
- Editing any field of `zann_family_meanings.csv` beyond §7.3.
- Renormalizing `confidence`, `author_position`, or vocalization on migrated rows (§10).
- Citing or consuming any non-Samarrai source.
- Modifying any committed historical artifact (`6d91650`, `e1474ab`, `667e94b`).

### 16.3 What requires a new RULE_LOCK (NOT this one)
- Adding the deferred transformation verbs (`رَدَّ`, `تَخِذَ`, `وَهَبَ`) — separate expansion batch with new SPEC + RULE_LOCK.
- Extending the MeaningGraph edge whitelist to include `AFAL_TAHWIL` — separate edge-emission batch with smoke evidence.
- Re-curating any `reported` row to `preferred` — separate re-curation batch with `disagreement` documentation.
- Normalizing the vocalization of اتَّخَذَ to `اِتَّخَذَ` — separate vocalization-normalization batch.
- Any other Samarrai family (`كان وأخواتها`, `مُقارَبَة`, `مَدْح/ذَمّ`, `تَضمين`) — separate per-family SPEC + RULE_LOCK.
- Bulk migration of `construction_rules.jsonl` / `meaning_cards.jsonl` — explicitly forbidden track.

### 16.4 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. `git log --oneline -20` — confirm no in-flight commits on MASAQ-related files since this RULE_LOCK.
2. `git status` — confirm working tree is clean except `.claude/`.
3. `git stash list` — confirm no untracked WIP exists that could be re-applied.

If any concurrent activity is found on MASAQ / versebyverse / hidden-pronoun tracks, postpone C₂ implementation until that activity completes.

---

## 17. One-screen recap

| Item | Value |
|---|---|
| Batch | C₂ |
| Type | Hygiene + migration (not addition) |
| Supersedes (for implementation) | SPEC `6d91650`, RULE_LOCK `e1474ab` |
| Parent SPEC | `667e94b` |
| Source | Rule card `AFAL_AL_TAHWIL__P2_001` (Samarrai vol 2, pp 26–279) + existing `zann_family_meanings.csv` rows 11–14 |
| Core invariant | لا تخزّن ما تستطيع توليده (operationalized as I1–I4) |
| Migration set | 4 verbs: جَعَلَ + اتَّخَذَ + صَيَّرَ + تَرَكَ |
| Renames | JAALA_VERB → AFAL_TAHWIL_JAAL; ITTAKHADHA_VERB → AFAL_TAHWIL_ITTAKHATHA; SAYYARA_VERB → AFAL_TAHWIL_SAYYARA; TARAKA_TRANS → AFAL_TAHWIL_TARAKA |
| Vocalization for اتَّخَذَ | Preserved without initial kasra |
| Author position preservation | Verbatim per row (2× preferred, 2× reported) |
| Confidence preservation | Verbatim per row (0.92 / 0.92 / 0.9 / 0.88) |
| New CSV row count | 1 header + 5 data rows |
| ZANN CSV after migration | 1 header + 12 data rows |
| ZANN_BASIC edit | One cell: `conditions` field; remove substring `أَو التَّحويل ` |
| Total MAANI rows after | 246 (was 245) |
| Schema | Unchanged 19-column |
| ProofKind enum | Unchanged |
| Allowed implementation files | 9 (§3); all required |
| Sweep regeneration | Required via `python3 clean_code/samarrai_quran_sweep.py`; sweep generator forbidden from edits |
| Tests | 5 structural + 6 hygiene + 7 claim-level + 2 sweep + 3 cross-suite = 23 |
| Forbidden | i3rab, MASAQ, L6/L7/L8, schema.md, sweep generator, gate files, external sources, deferred verbs/families, bulk migration |
| Conditional-forbidden lift | **None** (no clause; all conditional cases settled by Gate 2) |
| Rollback | `git revert` of implementation commit; no force-push |
| Governance gates | 7 (3 complete: SPEC commit + Gate 2 + this RULE_LOCK pending; 4 remaining) |
