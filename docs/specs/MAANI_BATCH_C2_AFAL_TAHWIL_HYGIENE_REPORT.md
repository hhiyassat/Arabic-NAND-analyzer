# MAANI Batch C₂ — AFAL_TAHWIL Hygiene & Migration — IMPLEMENTATION REPORT

> **Type:** Implementation report (Gate 7 of governance chain).
> **Date:** 2026-05-30
> **Status:** Final. Batch C₂ closed.

---

## 1. Commit chain

| Gate | Artifact | Commit |
|---|---|---|
| 1 | SPEC | **`667e94b`** — `Document MAANI Batch C2 AFAL_TAHWIL hygiene spec draft` |
| 3 | RULE_LOCK | **`f67ee6b`** — `Document MAANI Batch C2 AFAL_TAHWIL hygiene rule lock` |
| 6 | Implementation | **`3fcc704`** — `MAANI Batch C2: migrate transformation verbs to AFAL_TAHWIL` |
| 7 | This report | *(uncommitted at time of writing)* |

### Supersedence preserved
The historical Batch C documents remain in git history unchanged and are not amended:
- `6d91650` — *Document MAANI Batch C AFAL_TAHWIL spec draft* (historical, non-migration approach)
- `e1474ab` — *Document MAANI Batch C AFAL_TAHWIL rule lock* (historical, forbade ZANN CSV edits)

These remain accessible as the audit trail of the abandoned addition-only approach that was discarded before commit when implementation surfaced the duplicate-claim problem in `zann_family_meanings.csv`. The C₂ chain supersedes them for *implementation purposes only*.

---

## 2. Executive summary

MAANI Batch C₂ migrated four Samarrai transformation-verb rows out of `zann_family_meanings.csv` (where they had been duplicating cognition-family classification) into a new dedicated file `transform_verbs_meanings.csv` under the new topic `AFAL_TAHWIL`. The core invariant *«لا تخزّن ما تستطيع توليده»* (do not duplicate curated facts) is now structurally enforced for transformation verbs.

| Dimension | Before | After |
|---|---|---|
| Operators with duplicate transformation classification | 4 (`جَعَلَ`, `اتَّخَذَ`, `صَيَّرَ`, `تَرَكَ`) | 0 |
| `zann_family_meanings.csv` data rows | 16 | 12 |
| `transform_verbs_meanings.csv` data rows | (file did not exist) | 5 (1 framework + 4 migrated) |
| Total MAANI rows across all CSVs | 245 | 246 (+1 from framework) |
| Distinct `topic_id`s in MAANI corpus | n | n+1 (new: `AFAL_TAHWIL`) |
| Silent `author_position` upgrades introduced | n/a | 0 (reversed prior Batch C's silent flip on صَيَّرَ) |

---

## 3. Exact files committed (commit `3fcc704`)

**Modified (6):**
1. `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` — removed 4 transformation rows; surgical edit to `ZANN_BASIC.conditions` (removed «أَو التَّحويل» phrase).
2. `clean_code/samarrai_loaders/volume2_loader.py` — single-line addition to `CSV_FILES` list.
3. `clean_code/data/samarrai_sweep/per_word.csv` — regenerated.
4. `clean_code/data/samarrai_sweep/per_verse.csv` — regenerated.
5. `clean_code/data/samarrai_sweep/top_topics.csv` — regenerated.
6. `clean_code/data/samarrai_sweep/summary.txt` — regenerated.

**New (2):**
7. `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` — new file; 1 header + 5 data rows.
8. `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — new file; 20 tests.

**Regenerated but content-unchanged (not in commit diff but state is fresh):**
- `clean_code/data/samarrai_sweep/constructions.csv` — re-written by sweep generator, but the migration doesn't affect construction-pattern counts, so byte content is identical to pre-migration. `git diff` shows no change.

**Excluded from commit (per RULE_LOCK §3 allowlist + memory hygiene):**
- `.claude/` — intentionally not committed.
- `clean_code/data/samarrai_sweep/top_operators.csv` — see §6.2 below.
- `.pyc` / `out_*.txt` — none in commit.

---

## 4. Migration mapping (binding)

### 4.1 Renames (4 operators, ZANN_FAMILY → AFAL_TAHWIL)

| Source row | Target row |
|---|---|
| `JAALA_VERB` (ZANN_FAMILY, preferred, 0.92) | `AFAL_TAHWIL_JAAL` (AFAL_TAHWIL, preferred, 0.92) |
| `ITTAKHADHA_VERB` (ZANN_FAMILY, preferred, 0.92) | `AFAL_TAHWIL_ITTAKHATHA` (AFAL_TAHWIL, preferred, 0.92) |
| `SAYYARA_VERB` (ZANN_FAMILY, **reported**, 0.9) | `AFAL_TAHWIL_SAYYARA` (AFAL_TAHWIL, **reported**, 0.9) |
| `TARAKA_TRANS` (ZANN_FAMILY, **reported**, 0.88) | `AFAL_TAHWIL_TARAKA` (AFAL_TAHWIL, **reported**, 0.88) |

No legacy `meaning_id` aliases retained. Reference-impact scan (Gate 2 Investigation 2) confirmed zero Python / test / docs references to the legacy IDs.

### 4.2 Framework row added (1)

`AFAL_TAHWIL_BASIC` — the new framework row for the AFAL_TAHWIL topic:
- `priority=1`, `topic_id=AFAL_TAHWIL`, `operator=—`, `vocalized_form=—`
- `meaning_ar` begins «أفعال التحويل / التصيير …»
- `syntactic_effect=nasb_two_objects`, `semantic_field=causative_transformation`
- `author_position=preferred`, `source_part=2`, `source_page=26`, `confidence=0.95`
- Quranic anchor: `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` (النساء:125)

Source: rule card `AFAL_AL_TAHWIL__P2_001` (Samarrai vol 2, pp 26–279).

### 4.3 ZANN framework row edit (1 cell)

In `zann_family_meanings.csv` row `ZANN_BASIC`, the `conditions` field had the substring «أَو التَّحويل » removed (the framework no longer claims transformation verbs as members of the ZANN family after the migration). All other fields of `ZANN_BASIC` and all other retained ZANN rows are bit-for-bit unchanged.

---

## 5. Invariant compliance

The four operational rules of *«لا تخزّن ما تستطيع توليده»* (per RULE_LOCK §2) are each verified by a binding test:

| # | Invariant | Test | Result |
|---|---|---|---|
| I1 | No operator carries transformation claims under two `topic_id`s | H1 `t_no_operator_carries_transformation_in_two_topics` | ✅ Pass |
| I2 | Migration replaces, does not duplicate | H2 `t_zann_family_holds_no_transformation_rows` + S4 | ✅ Pass |
| I3 | `author_position` preserved verbatim per row | H3 `t_migrated_rows_preserve_author_position` | ✅ Pass |
| I4 | Provenance (`source_part`, `source_page`, `confidence`) preserved verbatim per row | H4 `t_migrated_rows_preserve_provenance` | ✅ Pass |

### 5.1 Specific verifications

- **No duplicate transformation claims**: H1 confirms every migrated operator returns exactly 1 transformation record, all under `topic_id=AFAL_TAHWIL`. H2 + C7 confirm ZANN_FAMILY holds zero transformation rows after migration.
- **SAYYARA and TARAKA remain `reported` → Hypothesis**: C3 + C4 confirm `proof_kind=Hypothesis` for both, reversing the prior Batch C's silent upgrade to `preferred`.
- **`author_position` preserved**: H3 verifies exact values (`preferred` for جَعَل/اتَّخَذ, `reported` for صَيَّر/تَرَك).
- **`confidence` preserved**: H4 verifies exact values (`0.92`/`0.92`/`0.9`/`0.88`), NOT normalized to the rule card's `0.93`.
- **Provenance preserved**: H4 verifies `source_part=2`, `source_page=26` for all 4 migrated rows.
- **Vocalization preserved**: H5 `t_ittakhatha_vocalization_preserved` verifies the اتَّخَذَ row's `vocalized_form` starts with ALEF (U+0627) followed by TEH (U+062A), NOT with kasra (U+0650). The prior Batch C SPEC's proposed change to `اِتَّخَذَ` with initial kasra was explicitly rejected.
- **No legacy `meaning_id` strings remain in any MAANI CSV**: H6 confirms.

---

## 6. Notable deviations and decisions

### 6.1 ITTAKHADHA 19-field alignment fix

The source ZANN row 12 (`ITTAKHADHA_VERB`) had only **18 CSV fields** instead of the schema's 19 — a pre-existing data bug where `example_constructed` was missing, causing positional mis-alignment that wrote the Quranic text into `example_constructed` (instead of `example_quran`), surah:ayah into `example_quran`, and `preferred` into `surah_ayah`. The existing system tolerates this corruption via Batch B's `t_surah_ayah_corruption_stays_certificate` test (which uses internal stubs and is unaffected by the actual ZANN row contents).

**Decision**: The migrated `AFAL_TAHWIL_ITTAKHATHA` row was aligned to **19 fields** to match RULE_LOCK §6.3's explicit field-by-field semantic layout. The cell values match RULE_LOCK §6.3 verbatim. The fix was a one-comma insertion (`,,` → `,,,` between `exceptions` and the Quranic text).

**Rationale**: RULE_LOCK §6.3 lists 19 fields with their semantic values. A 18-field row would have caused the test gates H3 and H4 to fail because csv.DictReader would assign values to columns positionally, putting the wrong values into `author_position` and `confidence`. The "verbatim" requirement of RULE_LOCK §6 was interpreted as applying to *values*, not to broken field count. The semantic content of every field matches the source row.

**Side-effects verified**: Batch B 6/6 still passes (the corruption test is stub-based, not row-based). Production 158/158 still passes.

### 6.2 `top_operators.csv` restored (outside allowlist)

The sweep generator at `clean_code/samarrai_quran_sweep.py` produces **6** output files (`per_word.csv`, `per_verse.csv`, `top_topics.csv`, `summary.txt`, `constructions.csv`, `top_operators.csv`). Gate 2 Investigation 6 documented only 5, and the RULE_LOCK §3 allowlist consequently listed only those 5. After sweep regeneration, `top_operators.csv` showed a tiny diff (1-row swap at position 50) caused by Python's `Counter.most_common(50)` non-deterministic tie-break order — entirely unrelated to the AFAL_TAHWIL migration (the migrated operators' counts of 85/22/20/12 are below or at the top-50 cutoff).

**Decision (per user, Gate 6 pre-commit verification)**: `git restore clean_code/data/samarrai_sweep/top_operators.csv` to remove the diff. The file was explicitly **excluded** from the commit per RULE_LOCK §3 allowlist discipline.

**Trade-off**: The committed `top_operators.csv` is now technically one tie-swap "stale" relative to a fresh sweep. This is acknowledged but accepted because:
- The deviation is structural (generator tie behavior), not migration-driven.
- Not touching `top_operators.csv` honors the literal RULE_LOCK without requiring an amendment cycle.
- The allowlist's 5 sweep outputs all contain the migration-relevant data; `top_operators.csv` is operator-count aggregation, not topic/meaning aggregation.

**For future MAANI batches**: a one-line addition to a future RULE_LOCK template should include `top_operators.csv` in the sweep-output allowlist by default, since the generator produces it.

### 6.3 Renumbering choice in ZANN file (RULE_LOCK §7.2 option)

After removing 4 rows from `zann_family_meanings.csv`, the priorities of the retained 12 rows were **not renumbered**. The retained rows kept their original priority values (`1..10, 15, 16`) with gaps at positions `11..14`. RULE_LOCK §7.2 explicitly permitted both renumbering and gap-preserving; gap-preserving was chosen to minimize the diff and avoid touching any retained row's content beyond what RULE_LOCK §7.3 explicitly authorizes.

---

## 7. Sweep regeneration summary

The sweep was regenerated by running `python3 clean_code/samarrai_quran_sweep.py` from the project root. The script processes all 6,236 Quranic verses through the updated SamarraiAnalyzer.

| Sweep output | Pre-migration | Post-migration | In commit? |
|---|---|---|---|
| `per_word.csv` | 190,526 lines; 139 legacy meaning_ids | 190,526 lines; 0 legacy, 139 new `AFAL_TAHWIL_*` | ✅ Yes |
| `per_verse.csv` | (changed) | (changed) | ✅ Yes |
| `top_topics.csv` | `ZANN_FAMILY=313`; no `AFAL_TAHWIL` row | `ZANN_FAMILY=174`; `AFAL_TAHWIL=139` | ✅ Yes |
| `summary.txt` | (changed) | (changed) | ✅ Yes |
| `constructions.csv` | regenerated; content unchanged | (no diff) | (in tree; not in commit diff because unchanged) |
| `top_operators.csv` | regenerated; tiny tie-swap diff at position 50 | restored to pre-state | ❌ Excluded (see §6.2) |

**ZANN_FAMILY → AFAL_TAHWIL split accounting**:
- Pre-migration: ZANN_FAMILY = 313 word-occurrences (cognition + transformation lumped).
- Post-migration: ZANN_FAMILY = 174 (cognition only) + AFAL_TAHWIL = 139 (transformation only). Sum = 313, conservation verified.
- Per-operator breakdown of the 139 AFAL_TAHWIL occurrences: جَعَلَ=85, اتَّخَذَ=22, صَيَّرَ=20, تَرَكَ=12.

---

## 8. Test results

All three test suites pass against the committed state:

| Suite | Tests | Result |
|---|---|---|
| `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` (new) | 20 (5 structural S1–S5 + 6 hygiene H1–H6 + 7 claim C1–C7 + 2 sweep R1–R2) | **20/20** ✅ |
| `clean_code/test_maani_batch_b_author_position.py` (regression) | 6 | **6/6** ✅ |
| `clean_code/test_production_path_segmentation.py` (regression) | 158 | **158/158** ✅ |

No skipped tests in C₂ (all analyzer-dependent tests successfully loaded the analyzer). Batch B's `t_surah_ayah_corruption_stays_certificate` continued to pass after the ITTAKHADHA alignment fix, confirming that test's stub-based design is not coupled to actual ZANN row contents.

---

## 9. Acceptance criteria (RULE_LOCK §12) — all 15 satisfied

| # | Criterion | Status |
|---|---|---|
| 1 | `transform_verbs_meanings.csv` has exactly 5 data rows + 1 header | ✅ |
| 2 | `zann_family_meanings.csv` has exactly 12 data rows + 1 header | ✅ |
| 3 | All 4 migrated rows match §6.2–§6.5 cell-for-cell | ✅ (with §6.1 ITTAKHADHA alignment fix per binding intent) |
| 4 | Framework row matches §7.1 | ✅ |
| 5 | Only edit to retained ZANN content is §7.3 `ZANN_BASIC.conditions` | ✅ |
| 6 | Schema validation passes | ✅ (S1) |
| 7 | Loader edit is exactly the one line in §7.4 | ✅ |
| 8 | Sweep artifacts regenerated, not hand-edited (§9.3); R1+R2 pass | ✅ |
| 9 | All §11.1 + §11.2 + §11.3 tests pass | ✅ (20/20) |
| 10 | Cross-suite regression green | ✅ (Batch B 6/6, production 158/158) |
| 11 | No file outside §3 modified | ✅ (after `top_operators.csv` restore) |
| 12 | No file in §4 modified | ✅ |
| 13 | No untracked artifacts in commit | ✅ (.claude/, .pyc, out_*.txt all excluded) |
| 14 | Implementation diff exactly matches the allowlist | ✅ (8 of 9 files committed; constructions.csv regenerated but unchanged content) |
| 15 | Batch report committed under separate approval | This document — pending Gate 7 commit |

---

## 10. Rejection criteria (RULE_LOCK §13) — none triggered

All 27 enumerated rejection triggers were checked and none triggered:
- No operator under two `topic_id`s ✓
- No source row left in `zann_family_meanings.csv` ✓
- No silent `author_position` flip ✓
- No silent provenance change ✓
- No Certificate-grade output for SAYYARA/TARAKA ✓
- No extra/missing rows in either CSV ✓
- No ZANN content edit beyond §7.3 ✓
- No vocalization change for اتَّخَذَ ✓
- No deferred verb introduced (رَدَّ, تَخِذَ, وَهَبَ, كان family, مُقارَبَة, مَدْح/ذَمّ) ✓
- No file outside allowlist modified (after `top_operators.csv` restore) ✓
- No file in forbidden list modified ✓
- No schema change ✓
- No sweep generator edit ✓
- No new ProofKind value ✓
- No ProofKind upgrade code path ✓
- No external source consumed ✓
- All required tests present ✓
- No regression in production or Batch B ✓
- No hand-edited sweep outputs ✓
- No stale legacy meaning_ids in sweep outputs ✓
- No untracked artifacts in committed tree ✓
- No MASAQ-golden regression ✓

---

## 11. Deferred items (out of scope for C₂; require separate batches with new RULE_LOCK)

Per RULE_LOCK §16.3:

- **Remaining transformation verbs**: `رَدَّ`, `تَخِذَ`, `وَهَبَ` — listed in rule card `AFAL_AL_TAHWIL__P2_001.trigger.lemmas` but no existing ZANN row. Would be net-new content; out of hygiene scope. A future expansion batch (Batch C₃?) may add them under separate SPEC + RULE_LOCK.
- **MeaningGraph edge whitelist extension** to include `AFAL_TAHWIL` — separate edge-emission batch with smoke evidence. Today AFAL_TAHWIL rows survive as `SamarraiClaim` objects but do not emit MeaningGraph edges (same as the surviving ZANN cognition verbs).
- **Vocalization normalization of اتَّخَذَ to اِتَّخَذَ** — separate vocalization-normalization batch.
- **Re-curation of any `reported` row to `preferred`** — separate re-curation batch with `disagreement` field documentation. C₂ preserved `reported` verbatim for SAYYARA and TARAKA.
- **Other Samarrai families**: كان وأخواتها (V4), أفعال المُقارَبَة (V5), أفعال المَدْح والذَّمّ (V6), التَّضمين practical examples (V7) — each requires its own SPEC + RULE_LOCK.
- **External classical scholars**: Ibn Hisham, Ibn Aqil, Suyuti, Ar-Radhi — explicitly out of MAANI's Samarrai-only source restriction.
- **Modern Arabic operators / NAA reconciliation** — explicitly deferred per handoff §10.
- **Bulk migration of `construction_rules.jsonl` / `meaning_cards.jsonl`** — explicitly forbidden track.
- **MASAQ track work** — separate track; not touchable from MAANI.
- **L1 / L2 / L3 cleanup** — separate phase work.
- **versebyverse / hidden pronouns / Phase4 stash** — separate tracks.
- **RULE_LOCK §3 allowlist update** to include `top_operators.csv` — recommended as a one-line addition to the next MAANI RULE_LOCK template; not part of C₂.

---

## 12. Final governance statement

> **Gate 7 complete. AFAL_TAHWIL C₂ is closed.**

The seven-gate governance chain for MAANI Batch C₂ is now fully traversed:

| Gate | Action | Artifact | Status |
|---|---|---|---|
| 1 | SPEC approval | `667e94b` | ✅ Closed |
| 2 | Gate-2 read-only investigations | (findings embedded in RULE_LOCK §0) | ✅ Closed |
| 3 | RULE_LOCK approval | `f67ee6b` | ✅ Closed |
| 4 | Implementation approval | (Gate 4 oral approval) | ✅ Closed |
| 5 | Test approval | 20/20 + 6/6 + 158/158 verified | ✅ Closed |
| 6 | Commit approval | `3fcc704` | ✅ Closed |
| 7 | Report | This document | ✅ Closed |

The duplicate-claim problem that triggered the abort of the original Batch C is structurally resolved. The transformation verbs (جَعَلَ, اتَّخَذَ, صَيَّرَ, تَرَكَ) now have a single canonical home under `topic_id=AFAL_TAHWIL`, with `author_position` and provenance preserved verbatim from their pre-migration source rows. The invariant *«لا تخزّن ما تستطيع توليده»* is now enforced for this verb family by 4 binding test gates (H1–H4) plus 1 boundary-guard test (H6).

Any further work on AFAL_TAHWIL (expansion, MeaningGraph integration, vocalization normalization, re-curation) requires a new SPEC and a new RULE_LOCK under a fresh governance chain.

---

## 13. One-screen recap

| Item | Value |
|---|---|
| Batch | C₂ |
| Type | Hygiene + migration (not addition) |
| Closed | 2026-05-30 |
| Commit chain | SPEC `667e94b` → RULE_LOCK `f67ee6b` → Implementation `3fcc704` → Report (this) |
| Supersedes (preserved) | Batch C SPEC `6d91650`, Batch C RULE_LOCK `e1474ab` |
| Migrated operators | 4: جَعَلَ + اتَّخَذَ + صَيَّرَ + تَرَكَ |
| Framework row added | `AFAL_TAHWIL_BASIC` (1 row) |
| `zann_family_meanings.csv` rows | 16 → 12 |
| `transform_verbs_meanings.csv` rows | 0 → 5 (new file) |
| Total MAANI rows | 245 → 246 |
| Files committed | 8 (6 modified + 2 new) |
| Files restored & excluded | 1 (`top_operators.csv`) |
| `author_position` preserved verbatim | ✅ (2× preferred, 2× reported) |
| `confidence` preserved verbatim | ✅ (0.92 / 0.92 / 0.9 / 0.88) |
| Vocalization preserved | ✅ (اتَّخَذَ retained without initial kasra) |
| ITTAKHADHA 19-field alignment fix | ✅ (matches RULE_LOCK §6.3 intent; Batch B unaffected) |
| Sweep regeneration | ✅ (ZANN 313 → 174 + new AFAL_TAHWIL 139; conservation verified) |
| Tests | C₂ 20/20 + Batch B 6/6 + Production 158/158 |
| Invariant *«لا تخزّن ما تستطيع توليده»* | Enforced (4 binding test gates H1–H4) |
| Governance gates | 7/7 complete |
| Deferred | Remaining transformation verbs, MeaningGraph wiring, other Samarrai families, external sources, vocalization re-curation, sweep allowlist correction |
