# PROJECT CLOSURE — Arabic Quranic Analyzer — SPEC DRAFT

> **Type:** SPEC draft (not RULE_LOCK).
> **Date:** 2026-06-01
> **Status:** Draft pending review. No implementation. No RULE_LOCK yet.
> **Scope:** Close the Arabic Quranic Analyzer as an **MVP**, not as universal Quranic grammar coverage. Bridge the gap between `docs/specs/WHERE_WE_ARE.md` (commit `3ad474c`) and the currently implemented reality on `main` (HEAD `3ad474c`).
> **Reference docs:** `docs/specs/WHERE_WE_ARE.md`, all batch SPECs/RULE_LOCKs/reports already merged on `main`.

---

## 0. Why this SPEC exists

`WHERE_WE_ARE.md` (committed at `3ad474c`) catalogs 10 remaining gaps and recommends Phase 5 Batch E as the next step. But "next step" is open-ended. The project does not need to grow indefinitely — it needs a defined **closure point** that:

- Proves the central architectural claim (grammar recognition → graph relations → user-visible reasoning) on a single anchor verse (2:282).
- Files everything not-yet-done into a controlled **backlog** so the project ends as an MVP, not as a never-finished sprawl.
- Leaves `main` in a clean, defensible state with a final closure report.

This SPEC defines **exactly three closure batches** (A, B, C). Each is narrow. After the three batches close, the project enters **MVP-closed** status: no new expansion until a future user re-opens it through a fresh SPEC.

---

## 1. Current state (as of HEAD `3ad474c`)

### 1.1 What `main` contains

- Phase 5 Batch B closed (`a715cb3` report).
- SHART_JAWAB pilot for 2:282 first إِذَا implemented at L4/L7 (`236a885` impl).
- MAANI Batch C2 AFAL_TAHWIL hygiene/migration closed (`05a7f25` report).
- MAANI Batch B + earlier MAANI work merged.
- MASAQ F3 classification + lookup fixes merged.
- Surah 1 verse-by-verse audit fixes merged.
- `NO_DIACRITIC_STRIPPING_RULE.md` governance doc merged (`07f5f0a`).
- `WHERE_WE_ARE.md` living project map merged (`3ad474c`).

### 1.2 What 2:282 currently shows

```
L4:
  ✓ condition_tool_of [إِذَا] : إِذَا → تَدَايَنتُم      (Certificate)
  ✓ jawab_shart_of    [فَ]   : فَٱكْتُبُوهُ → تَدَايَنتُم   (Certificate)

L7:
  العُقَد:        135 (52C + 83H)
  الرَّوابِط:     43 (16C + 27H)
  التَّغطيَة:    63.2%
  Entropy:        0.0
  مُتَّسِق:       نَعَم ✓

L8:
  ✓ مَتى حَدَث؟ → Certificate when_future
  ? ما تَسَلسُل الأَحداث؟ → flat textual order (Hypothesis)
  ✗ ما تَفسير هذه الآيَة؟ → out of scope (correct refusal)
```

### 1.3 Test baseline

| Suite | Count |
|---|---|
| `test_shart_jawab_relations_pilot_2_282.py` | 11/11 |
| `test_production_path_segmentation.py` | 159/159 |
| `test_maani_batch_b_author_position.py` | 6/6 |
| `test_maani_batch_c2_afal_tahwil_hygiene.py` | 20/20 |
| `test_phase4_certificate_reevaluation.py` | 12/12 |
| **Total** | **208/208** |

### 1.4 Project laws on `main` (binding for all closure work)

- **لا إزالة للتشكيل** — diacritic preservation across all layers.
- **لا تخزّن ما تستطيع توليده** — no duplicate curated facts.
- **No silent ProofKind upgrades** — Certificate may only downgrade.
- **Zero preferred over unsafe guessing** — "بِلا مَرجِع" is a legitimate output.
- **No tafsir / fiqh** — out of project scope.

---

## 2. Gap-to-closure mapping

This SPEC closes a deliberately small subset of the 10 gaps in `WHERE_WE_ARE.md` §4. The rest go to backlog.

| Gap | WHERE_WE_ARE source | Closure approach |
|---|---|---|
| **Gap 1** — L8 doesn't use new condition/jawab structure | §4 Gap 1 | **Closure Batch A** — close it |
| **Gap 9** — Quran-wide validation incomplete | §4 Gap 9 | **Closure Batch B** — close *for 2:282 only*; rest to backlog |
| **Gaps 2–8, 10** — L5/L6 scope, L1/L2/L3 stabilization, other conditional tools, other relation families, MAANI expansion, user interface | §4 Gaps 2–8 + 10 | **Closure Batch C** — backlog document |

After all three batches close, every gap from `WHERE_WE_ARE.md` is **either closed or filed as backlog**. No gap is left as silent unfinished work.

---

## 3. Closure Batch A — L8 consumes existing L4/L7 condition/jawab edges

### 3.1 Purpose

Make L8 display the structural knowledge that L4 and L7 already have. No new grammar. No new relation extraction. The gap closed is **Gap 1** of `WHERE_WE_ARE.md` §4.

### 3.2 Scope

- **Only 2:282 first إِذَا construction.**
- **Input already exists** (no detection logic added):
  - `condition_tool_of: إِذَا → تَدَايَنتُم` (Certificate, in L4 RelationGraph and L7 MeaningGraph)
  - `jawab_shart_of: فَٱكْتُبُوهُ → تَدَايَنتُم` (Certificate)
- **L8 changes only.** The reasoning engine consumes existing edges; it does NOT detect anything new.

### 3.3 What L8 should produce

For verse 2:282, alongside the existing `ما تَسَلسُل الأَحداث؟` answer, L8 should also expose:

```
✅ ما جَواب الشَّرط؟
   ✓ [Certificate] جَواب الشَّرط هو فَٱكْتُبُوهُ، مَربوط بِفِعل الشَّرط
                   تَدَايَنتُم عَبر jawab_shart_of (مَع فاء الجَواب فَ).
```

OR (equivalent rendering): inside the existing event-sequence answer, add a conditional grouping marker:

```
✅ ما تَسَلسُل الأَحداث؟
   ? [Hypothesis] ءَامَنُوٓا → [إِذَا تَدَايَنتُم ⇒ فَٱكْتُبُوهُ] → وَلْيَكْتُب → ...
```

RULE_LOCK to pick exactly one rendering format (new question vs sequence-grouping). SPEC preference: **new dedicated question `ما جَواب الشَّرط؟`** because it's clean, doesn't break existing answers, and surfaces the structural fact directly.

### 3.4 ProofKind discipline

The new L8 answer emits:
- `Certificate` when **both** `condition_tool_of` AND `jawab_shart_of` exist in the RelationGraph with `proof_kind=Certificate`.
- `Zero` ("لا جواب شرط مكشوف") otherwise. No Hypothesis fallback.
- **Block-and-report** if RelationGraph is missing or empty.

### 3.5 Likely allowed implementation files (for the later RULE_LOCK)

| Path | Purpose | Required / Conditional |
|---|---|---|
| `clean_code/reasoning_engine.py` | Add the new `ما جَواب الشَّرط؟` question handler that consumes existing `condition_tool_of` + `jawab_shart_of` edges. | **Required** |
| `clean_code/analyze_verse_v3.py` | If L8 output requires routing the new question, may need a 1-3 line edit to surface it. | **Conditional** — only if the question isn't auto-rendered by the existing L8 loop |
| `clean_code/test_shart_jawab_relations_pilot_2_282.py` | Add 1-2 tests asserting L8 shows the conditional answer. | **Required** |
| `clean_code/test_production_path_segmentation.py` | Possibly a guard update (similar to Phase 5 Batch B if `reasoning_engine.py` needs to be removed from an existing forbidden list — Gate 2 investigation needed). | **Conditional** |

### 3.6 Forbidden for Batch A

- `clean_code/relation_extractor.py` — no new edges (Batch B did that).
- `clean_code/meaning_assembler.py` — no L7 changes.
- `clean_code/phase5_clause_segmenter.py` — Phase 5 untouched.
- `clean_code/i3rab_engine/*` — no L3 changes.
- `clean_code/event_extractor.py` — no L5 changes.
- `clean_code/resolution_engine.py` — no L6 changes.
- All MAANI / MASAQ files.
- `schema.md`.
- All other test files.

### 3.7 Done when

- L8 output for 2:282 shows the conditional answer in some auditable form.
- L4/L7 metrics stay stable: nodes 135, links 43, Entropy 0.0, consistency نَعَم.
- 2:282 produces `Certificate` for "ما جواب الشرط؟" (or equivalent locked rendering).
- Other verses without condition/jawab edges produce `Zero` for the same question (negative test).
- All cross-suite regression suites pass.
- `WHERE_WE_ARE.md` Gap 1 is moved from "current gap" to "closed in Closure Batch A".

### 3.8 Why this is the most important closure patch

L4/L7 already encode the conditional structure (verified at HEAD `3ad474c`). L8 not using that structure is the only remaining visible gap between the architecture and the user experience. **Closing this gap makes the architectural payoff of Phase 5 Batch B + SHART_JAWAB visible.** Without it, the project's central claim ("grammar recognition → graph relations → user-visible reasoning") is unproven to anyone reading L8 output.

---

## 4. Closure Batch B — Final 2:282 audit report

### 4.1 Purpose

Produce one final "project proof" document and runnable artifact for verse 2:282. This is the closure equivalent of a release announcement: it shows that 2:282 — the anchor verse the entire project has converged on — exhibits the full L1–L8 behavior that the project aimed for.

### 4.2 Scope

- **2:282 only.** No Quran-wide run.
- Document-only output (a Markdown report), optionally accompanied by a one-shot runnable script that regenerates the report from current code.

### 4.3 What the report contains

A new doc `docs/specs/2_282_FINAL_AUDIT_REPORT.md` containing for verse 2:282:

| Section | Content |
|---|---|
| L1/L2 summary | Token table (138 tokens) with prefix / stem / suffix; flag known issues (e.g., `تَدَايَنتُم` over-segmentation) without fixing |
| L3 key classifications | Word-class + role for إِذَا, تَدَايَنتُم, فَٱكْتُبُوهُ; flag known wazn issues without fixing |
| L4 condition/jawab relations | `condition_tool_of` + `jawab_shart_of` with full `source_of_claim` text |
| L5 events around the condition | `Event[تَدَايَنتُم]` + `Event[فَٱكْتُبُوهُ]` with tense / mood / time_scope |
| L6 safe Zero behavior | The 5 "بِلا مَرجِع" resolutions, explaining each is intentional, not a bug |
| L7 metrics | nodes 135 / links 43 / C/H split / coverage / Entropy / consistency |
| L8 conditional answer | The new "ما جواب الشرط؟" answer from Closure Batch A |
| ProofKind audit | A summary table: how many Certificate, Hypothesis, Zero across L4 / L5 / L6 / L8 for this verse |
| Invariants check | Confirm `لا إزالة للتشكيل` (no diacritic stripping), `لا تخزّن ما تستطيع توليده` (no duplicate facts), no silent ProofKind upgrades, Zero preferred over guessing |
| Project laws compliance | Statement that 2:282 obeys all 5 laws from §1.4 |

### 4.4 Allowed implementation files (for the later RULE_LOCK)

| Path | Purpose | Required / Conditional |
|---|---|---|
| `docs/specs/2_282_FINAL_AUDIT_REPORT.md` | The audit document itself | **Required** |
| Possibly a one-shot regeneration script (e.g., `clean_code/scripts/audit_2_282.py`) | Optional automation | **Conditional** — RULE_LOCK to decide |

### 4.5 Forbidden for Batch B

- All code under `clean_code/*` except the optional regeneration script.
- All data files.
- All MAANI / MASAQ files.
- All other tests.

### 4.6 Done when

- `docs/specs/2_282_FINAL_AUDIT_REPORT.md` exists and is accurate against current code.
- The report explicitly answers: "أين جواب إذا؟" → فَٱكْتُبُوهُ.
- The report shows graph consistency (Entropy 0.0, نَعَم).
- The report records the test suite results.
- The report states explicitly: this proves the project's central architectural claim on the anchor verse.

### 4.7 Why narrow to 2:282

2:282 is the verse the project has converged on through every batch:
- SHART_JAWAB pilot (`7b77945`) — 2:282 first إِذَا.
- Phase 5 Batch B (`eb7720c`) — 2:282 first إِذَا.
- VERSEBYVERSE Surah 1 → established the per-verse audit pattern.
- 2:282 references appear throughout MASAQ F3 commits as a test case.

It is the **anchor verse**. Quran-wide validation is Gap 9 in `WHERE_WE_ARE.md` and goes to backlog (Closure Batch C). Closing 2:282 proves the architecture; Quran-wide is future work.

---

## 5. Closure Batch C — Backlog document for deferred gaps

### 5.1 Purpose

Do NOT solve every gap now. Document them in a controlled backlog so the project ends as MVP, not as never-finished sprawl. Gap 2 through Gap 8, plus Gap 10, all go here.

### 5.2 Output

A new doc `docs/specs/PROJECT_CLOSURE_BACKLOG.md` containing 8 backlog categories:

| # | Category | Maps to WHERE_WE_ARE Gap | Brief |
|---|---|---|---|
| 1 | **Phase 5 Batch C** — event scope | Gap 2 | Wire Phase 5 clauses into `event_extractor.py`. Add `Event.clause_id` and `Event.parent_clause_id`. Replace PATCH-5's pause-walk. |
| 2 | **Phase 5 Batch D** — resolution scope | Gap 3 | Wire Phase 5 clauses into `resolution_engine.py` and `hidden_pronoun_signals.py`. Improve L6 antecedent search. |
| 3 | **MASAQ L1/L2/L3 stabilization** | Gaps 4 + 5 | Per-issue SPECs for known false segmentation (e.g., `تَدَايَنتُم`) and false role / wazn classifications. Batch-based, not random. |
| 4 | **Additional conditional tools** | Gap 6 | `إِنْ`, `مَنْ`, `مَا الشرطية`, `لَوْ`, `لَوْلَا`, `أَمَّا`, `كُلَّمَا`, `لَمَّا`, `مَتَى`, `أَيْنَمَا`, `حَيْثُمَا`. Each requires Phase 5 detector extension + SHART_JAWAB-style sub-pilot. |
| 5 | **Other relation families** | Gap 7 | الاستثناء, التعليل, الغاية, التفصيل, الحال, التمييز, البدل (sub-types), النعت السببي, العطف البنيوي, التوكيد. Each family is its own SPEC. |
| 6 | **MAANI directed expansion** | Gap 8 | Vector V4/V5/V6/V7 from the handoff (كان وأخواتها, أفعال المُقارَبَة, أفعال المَدْح والذَّمّ, التَّضمين). Each Vector is its own batch. |
| 7 | **Quran-wide validation** | Gap 9 | Pilot → nearby verses → surah → 1000-ayah → full Quran sweep with goldens. Only after a relation family stabilizes. |
| 8 | **User-facing interface** | Gap 10 | Cleaner output layer (condition / answer / relation / ProofKind / audit path) without raw L1–L8 debug verbosity. |

### 5.3 Required content per backlog item

For each of the 8 categories, the backlog entry MUST include:

| Field | Purpose |
|---|---|
| `why_deferred` | One paragraph: why this is not in MVP closure. |
| `trigger_for_reopening` | What concrete event would justify opening this category (e.g., "a downstream user requests Quran-wide condition coverage"). |
| `likely_files` | A 5-10-line list of files the category would likely touch when opened. |
| `invariants_to_preserve` | Which of the 5 project laws this category must obey. |
| `next_spec_template` | A 3-line skeleton of what the SPEC for this category would look like. |

### 5.4 Allowed implementation files (for the later RULE_LOCK)

| Path | Purpose | Required / Conditional |
|---|---|---|
| `docs/specs/PROJECT_CLOSURE_BACKLOG.md` | The backlog document | **Required** |

### 5.5 Forbidden for Batch C

- All `clean_code/*` files.
- All data files.
- All MAANI / MASAQ files.
- All tests.

### 5.6 Done when

- `docs/specs/PROJECT_CLOSURE_BACKLOG.md` exists.
- All 8 categories have all 5 required fields populated.
- Each category links back to the corresponding Gap in `WHERE_WE_ARE.md`.
- `WHERE_WE_ARE.md` is updated to mark Gaps 2–8 + 10 as "filed to backlog".

### 5.7 Why a backlog is the closure mechanism

A backlog converts **silent unfinished work** into **controlled future work**. Without it, the project's gaps stay scattered across `WHERE_WE_ARE.md` §4 forever. With it, each gap has an explicit re-opening contract: trigger, files, invariants, template. The project can be re-opened by any future user (or session) by reading the backlog entry and following the same SPEC → RULE_LOCK → implementation → tests → commit → report governance.

---

## 6. Final closure report

After Closure Batches A + B + C all ship, a **single project closure report** is written.

### 6.1 Output

`docs/specs/PROJECT_CLOSURE_REPORT.md` containing:

- Statement: "Arabic Quranic Analyzer is closed as MVP, not as universal Quranic grammar coverage."
- What the project now achieves (L1–L8 on the anchor verse 2:282 with auditable ProofKind discipline).
- What was proven on 2:282 (the central architectural claim).
- What remains deferred (pointer to `PROJECT_CLOSURE_BACKLOG.md`).
- Why deferred gaps do not block MVP closure.
- Test results (the 208/208 baseline at closure).
- Git state at closure (HEAD commit hash).
- `main` branch status.
- `WHERE_WE_ARE.md` final state at closure.

### 6.2 Allowed implementation files

| Path | Purpose |
|---|---|
| `docs/specs/PROJECT_CLOSURE_REPORT.md` | The final closure document |
| `docs/specs/WHERE_WE_ARE.md` | Updated to mark Gap 1 closed (by Batch A) and Gaps 2–8 + 10 filed to backlog; project status → MVP-closed |

### 6.3 The report's central statement

> The Arabic Quronic Analyzer is closed as MVP. It produces L1–L8 analysis with auditable ProofKind discipline, exposes condition/jawab structural relations on the anchor verse 2:282 (verified at L4, L7, and L8), and respects the project's binding laws (no diacritic stripping, no duplicate curated facts, no silent ProofKind upgrades, no tafsir/fiqh scope, Zero preferred over guessing). Further expansion is documented in `PROJECT_CLOSURE_BACKLOG.md` and can be re-opened by any future SPEC.

---

## 7. Tests required (across all three batches)

### 7.1 At closure

All of the following must pass at the closure commit:

| Suite | Expected count |
|---|---|
| `clean_code/test_shart_jawab_relations_pilot_2_282.py` | 11/11 (plus 1-2 new tests for L8 condition answer from Batch A) |
| `clean_code/test_production_path_segmentation.py` | 159/159 (or 160/161 if Batch A requires a guard or runner update) |
| `clean_code/test_maani_batch_b_author_position.py` | 6/6 |
| `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` | 20/20 |
| `clean_code/test_phase4_certificate_reevaluation.py` | 12/12 |

Total: ~208–211 passed depending on Batch A's exact test additions.

### 7.2 New tests for Batch A (binding)

| # | Test | Asserts |
|---|---|---|
| L8-1 | `t_2_282_l8_jawab_shart_answer_is_certificate` | L8's "ما جواب الشرط؟" answer for 2:282 returns Certificate with `فَٱكْتُبُوهُ` named as the jawab. |
| L8-2 | `t_l8_jawab_shart_returns_zero_when_no_condition_edges` | A verse without `condition_tool_of` + `jawab_shart_of` edges returns Zero for the same question (no fabrication). |

### 7.3 Final 2:282 acceptance check (Batch B)

The audit report must be regenerable from current code. If a regeneration script ships (per §4.4), it must produce output bit-for-bit consistent with the report at the closure commit (within a tolerance for whitespace).

---

## 8. Definition of finished (binding)

The project is finished for this phase only when **all** of the following hold:

1. `main` is clean and pushed to origin.
2. `WHERE_WE_ARE.md` is committed and current (Gap 1 marked closed; Gaps 2–8 + 10 marked filed to backlog).
3. L8 displays the 2:282 condition/jawab relation in some auditable form (Batch A done).
4. Final 2:282 audit report exists and is accurate (Batch B done).
5. `PROJECT_CLOSURE_BACKLOG.md` exists with all 8 categories populated (Batch C done).
6. `PROJECT_CLOSURE_REPORT.md` exists (the final report).
7. All 5 required test suites pass at expected counts.
8. Working tree clean except `.claude/`.
9. No new batch is open.
10. No unfinished work outside the backlog.

If any of these 10 conditions fails, the project is **not** closed — it is in-progress.

---

## 9. Rollback plan

If any closure batch is rejected or fails review after its commit:

1. **Standard `git revert`** of the implementation commit. The revert restores the affected layer (L8 for Batch A; the audit doc for Batch B; the backlog doc for Batch C) to its pre-batch state.
2. **No force-push.** No `git reset --hard` on `main`.
3. **WHERE_WE_ARE.md** is reverted to its pre-batch state if it was edited.
4. **No data outside the batch is touched.** All earlier work (Phase 5 Batch B, MAANI C2, MASAQ F3, etc.) remains intact.
5. The other closure batches are NOT auto-rolled-back. Each is independent.

If rollback itself requires destructive operations, halt and consult the user.

---

## 10. Governance (gate chain per closure batch)

Each closure batch follows the same 7-gate chain established by all prior project batches:

| Gate | Action |
|---|---|
| 1 | SPEC (this document covers all three at once) |
| 2 | Read-only investigations (per closure batch) |
| 3 | RULE_LOCK (per closure batch) |
| 4 | Implementation approval |
| 5 | Test approval |
| 6 | Commit approval |
| 7 | Report approval |

After all three closure batches close (Gates 1–7 ×3), a **final closure report** (§6) is written under one additional governance round.

Each gate requires separate explicit approval. **Skipping any gate rejects that closure batch.**

---

## 11. Final STOP rule (binding for the entire project after closure)

After the closure report ships, the project enters **MVP-CLOSED** status. The binding rule:

> **No new SPEC, RULE_LOCK, implementation, or commit may be opened against this project without explicit user re-opening.**

Re-opening requires:

1. A user instruction explicitly stating "re-open the project" or "open backlog item X".
2. A fresh SPEC pointing to the backlog category being re-opened.
3. Full re-traversal of the 7-gate governance chain for the new work.

In MVP-CLOSED status, Claude must respond to grammar / analysis / batch requests with:

> "The project is in MVP-CLOSED status (per `PROJECT_CLOSURE_REPORT.md`). To open new work, please reference a backlog category from `PROJECT_CLOSURE_BACKLOG.md` and confirm you want to re-open it. Otherwise the project remains closed."

This prevents drift back into open-ended expansion.

---

## 12. Forbidden tracks (binding for closure work)

Throughout all three closure batches and the final report, the following remain hard-forbidden:

- No MAANI family additions or migrations.
- No MASAQ work (broad sweep or per-token).
- No Phase 5 Batch C / D / E SPEC (these are backlog).
- No hidden-pronoun work.
- No verse-by-verse loop on verses other than 2:282.
- No Quran-wide validation run.
- No broad conditional grammar (other tools beyond إِذَا).
- No new relation families beyond what L4 already has.
- No construction_rules bulk migration.
- No external sources.
- No modern Arabic sources.
- No tafsir / fiqh.
- No new ProofKind values.
- No schema changes.
- No L1 / L2 / L3 stabilization batches (those go to backlog).
- No L6 resolution improvements.
- No edits to `phase5_clause_segmenter.py`.

The complete list of "do-not-open-now" items from `WHERE_WE_ARE.md` §5 applies in full.

---

## 13. One-screen recap

| Item | Value |
|---|---|
| Type | PROJECT CLOSURE SPEC (MVP closure, not universal coverage) |
| Closure batches | **3** — A (L8 consumption) + B (2:282 audit) + C (backlog) |
| Final report | `PROJECT_CLOSURE_REPORT.md` after all three batches close |
| Anchor verse | 2:282 (no Quran-wide work) |
| Gaps closed | Gap 1 (by Batch A); Gap 9 partial (2:282 only, by Batch B) |
| Gaps filed to backlog | Gaps 2–8 + 10 (by Batch C) |
| Allowed files (Batch A) | `reasoning_engine.py`, the pilot test file, conditional production runner registration |
| Allowed files (Batch B) | `2_282_FINAL_AUDIT_REPORT.md` + optional regeneration script |
| Allowed files (Batch C) | `PROJECT_CLOSURE_BACKLOG.md` |
| Allowed files (final report) | `PROJECT_CLOSURE_REPORT.md` + `WHERE_WE_ARE.md` update |
| Forbidden tracks | MAANI, MASAQ, Phase 5 C/D/E, hidden pronouns, versebyverse, Quran-wide, broad conditional grammar, new relation families, external sources, tafsir |
| Tests at closure | 208+ passed (depending on Batch A additions) |
| Project laws preserved | لا إزالة للتشكيل, لا تخزّن ما تستطيع توليده, no silent ProofKind upgrades, Zero over guessing, no tafsir/fiqh |
| Definition of finished | 10 binding conditions in §8 |
| Rollback | `git revert` per batch; no force-push |
| Post-closure STOP rule | MVP-CLOSED; new work requires explicit re-opening + fresh SPEC |
| Governance | 7 gates per batch × 3 batches + 1 final report round |
