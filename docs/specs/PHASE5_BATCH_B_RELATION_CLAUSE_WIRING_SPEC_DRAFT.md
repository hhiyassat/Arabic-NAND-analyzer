# Phase 5 Batch B — Relation / Clause Wiring — SPEC DRAFT

> **Type:** SPEC draft (not RULE_LOCK).
> **Date:** 2026-05-31
> **Status:** Draft pending review. No implementation. No RULE_LOCK yet.
> **Parent track:** Phase 5 — Clause and Sentence Segmentation (Batch A shipped at commit `e357ae5`).
> **Reference SPEC:** `docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md` (dated 2026-05-29).
> **Scope:** Authorize a narrow production bridge from Phase 5 Batch A's standalone clause segmenter into **only** `relation_extractor.py`. Preserve Batch A's isolation discipline for every other production module. Support the SHART_JAWAB pilot for verse 2:282 first إِذَا as the inaugural use case.

---

## 0. Why this SPEC exists

The SHART_JAWAB pilot (`SHART_JAWAB_RELATIONS_PILOT_2_282`), committed at SPEC `cd83d7f` and RULE_LOCK `7b77945`, designated Phase 5 (`phase5_clause_segmenter.py`) as the binding source of truth for shart/jawab structure. RULE_LOCK §1 / §5.1 forbade editing Phase 5 itself, while RULE_LOCK §6.2 required the implementer to stop-and-report if Phase 5 output is unreachable from `relation_extractor.py`.

At Gate 4 implementation, the Phase 5 output proved unreachable. The block was traced to an explicit production guard test `t_phase5_clause_segmenter_not_imported_by_production_path` at `clean_code/test_production_path_segmentation.py:1771–1818`. The guard is **intentional**: Phase 5 Batch A's SPEC §6 explicitly lists "No change to L4 relations. `relation_extractor.py` is untouched. ... Wiring clause IDs into L4 is **Batch B**." And Phase 5 SPEC §7 ("Future consumption plan") explicitly reserves the wiring of clause data into `relation_extractor.py` as **"Batch B"**, requiring its own separate SPEC + RULE_LOCK + approval.

**This document is that Batch B SPEC.** It authorizes the narrow production wiring that Batch A intentionally deferred, while preserving every other isolation constraint Batch A enforced.

The SHART_JAWAB pilot's documents (`cd83d7f` SPEC, `7b77945` RULE_LOCK) are **not rewritten or deleted**. They remain historical artifacts of the path that surfaced the block. After Phase 5 Batch B ships, SHART_JAWAB implementation can resume under a re-approval gate (either an amended SHART_JAWAB RULE_LOCK or as a Batch B sub-scope per §6 below).

---

## 1. Problem statement

The production pipeline today has a deliberate gap: structural clause data (condition / jawab / relative shell / lam-al-amr command / أن-complement / pause-bounded scope) is detected by `phase5_clause_segmenter.py` but **cannot reach** any production layer. The guard test at `test_production_path_segmentation.py:1771–1818` enforces this isolation across 13 production files:

```python
production_files = [
    here / "segmenter.py",
    here / "i3rab_engine" / "layer1.py",
    here / "i3rab_engine" / "layer2.py",
    here / "i3rab_engine" / "layer3.py",
    here / "i3rab_engine" / "engine.py",
    here / "relation_extractor.py",          # ← this batch will authorize ONLY this one
    here / "event_extractor.py",
    here / "resolution_engine.py",
    here / "reasoning_engine.py",
    here / "meaning_assembler.py",
    here / "hidden_pronoun_signals.py",
    here / "samarrai_certified_operator_gate.py",
    here / "analyze_verse_v3.py",
]
phase5_markers = _re.compile(
    r"\b(phase5_clause_segmenter|Phase5Clause|Phase5ClauseGraph"
    r"|segment_clauses_from_surfaces|build_clause_graph)\b"
)
```

The guard does NOT exist because Phase 5 is unstable. It exists because Phase 5's Batch A made an explicit architectural commitment: ship the detector standalone first, then approve each production consumer through a separate batch (B for L4, C for L5, D for L6, E for L8). This SPEC authorizes the **B half** of that plan.

### Direct consequence (verse 2:282)

The Phase 5 SPEC §1 itself names the consequence verbatim:

> "Condition / answer-of-condition is invisible. `إِذَا تَدَايَنتُم بِدَيْنٍ ... فَٱكْتُبُوهُ` produces independent L5 events for تَدَايَنتُم and فَٱكْتُبُوهُ with no link saying فَٱكْتُبُوهُ is the *jawab* of the إذا condition. L8 'ما تَسَلسُل الأَحداث؟' can only list verbs left-to-right."

The SHART_JAWAB pilot exists to close exactly this gap. Phase 5 Batch B is the architectural enabler.

---

## 2. Source evidence

| Artifact | Path | Status |
|---|---|---|
| Phase 5 SPEC (Batch A + future plan) | `docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md` | 21,394 bytes, 2026-05-29 |
| Phase 5 standalone module | `clean_code/phase5_clause_segmenter.py` | 14,639 bytes |
| Phase 5 Batch A commit | `e357ae5 PHASE 5 Batch A: add standalone clause segmenter` | Single all-in-one commit |
| Isolation guard test | `clean_code/test_production_path_segmentation.py:1771–1818` (`t_phase5_clause_segmenter_not_imported_by_production_path`) | Part of 158/158 baseline |
| SHART_JAWAB pilot SPEC | `cd83d7f Document SHART_JAWAB relations pilot spec for 2:282` | Historical |
| SHART_JAWAB pilot RULE_LOCK | `7b77945 Document SHART_JAWAB relations pilot rule lock for 2:282` | Historical; blocked at implementation due to the guard |

All of the above are read-only evidence for this SPEC. None is amended by this SPEC.

---

## 3. Proposed Batch B scope

### 3.1 What Batch B authorizes (in scope)

- **Production wiring of Phase 5 into exactly one module**: `clean_code/relation_extractor.py`.
- A **narrowed isolation guard** that allows `relation_extractor.py` to import Phase 5 surface symbols, while continuing to block every other production module on the original guard's list.
- L7 propagation: `meaning_assembler.py` extends its `PASSTHROUGH` edge-type whitelist with the new relation names introduced by Batch B. **It does NOT import Phase 5.** It only sees `RelationGraph` objects with new `name` values; the names are strings.
- Inaugural use case: support the **SHART_JAWAB pilot for the first إِذَا construction in verse 2:282** (`إِذَا تَدَايَنتُم … فَٱكْتُبُوهُ`).
- A small extension to `relation_types.csv` at `clean_code/data/contracts/rules/relation_types.csv` for the two new relation names defined by SHART_JAWAB (`condition_tool_of`, `jawab_shart_of`).
- A new focused test file `clean_code/test_shart_jawab_relations_pilot_2_282.py` covering the pilot construction.

### 3.2 What Batch B does NOT do (out of scope — explicit deferrals)

- **Does NOT wire Phase 5 into `event_extractor.py` (Batch C).**
- **Does NOT wire Phase 5 into `resolution_engine.py` (Batch D).**
- **Does NOT wire Phase 5 into `reasoning_engine.py` (Batch E).**
- **Does NOT wire Phase 5 into `meaning_assembler.py`** as a direct importer. (Whitelist extension is consumer-only; the names flow through the existing `Relation` → `MeaningEdge` translation.)
- **Does NOT wire Phase 5 into `analyze_verse_v3.py`**, `i3rab_engine/*`, `segmenter.py`, `normalizer.py`, `master_token_lookup.py`, `samarrai_certified_operator_gate.py`, `samarrai_analyzer.py`, `hidden_pronoun_signals.py`.
- **Does NOT broaden conditional grammar** beyond the SHART_JAWAB pilot's first إِذَا construction in 2:282. Other إِذَا occurrences in 2:282, other conditional tools (إِنْ, لَوْ, لَوْلَا, أَمَّا, مَنْ, أَيّ, أَيْنَ, أَيْنَمَا, كَيْفَمَا, مَتَى, حَيْثُمَا, أَنَّى, مَهْمَا, كُلَّمَا, مَا, لَمَّا), and all verses other than 2:282 — all remain locked behind their own future SPECs.
- **Does NOT edit `phase5_clause_segmenter.py` itself.** Phase 5 Batch A's module remains the read-only source of truth.
- **Does NOT add new ProofKind values, schema columns, or MeaningGraph node types.**
- **Does NOT touch MAANI, MASAQ, or any non-MAANI track.**
- **Does NOT delete or weaken the isolation guard.** The guard narrows from a blanket block to an allow-list; every other production module remains blocked.

### 3.3 Inaugural use case scope (SHART_JAWAB sub-scope)

Batch B's implementation must satisfy the SHART_JAWAB pilot for **exactly one construction**:

```
إِذَا  تَدَايَنتُم  بِدَيْنٍ  إِلَىٰٓ  أَجَلٍ  مُّسَمًّى  فَٱكْتُبُوهُ
↑     ↑                              ↑
tool   shart event                    jawab event (marked by فَ)
```

Per the SHART_JAWAB RULE_LOCK `7b77945` §3 (its locked design):
- `condition_tool_of: إِذَا → تَدَايَنتُم` (Certificate)
- `jawab_shart_of: فَٱكْتُبُوهُ → تَدَايَنتُم` (Certificate)
- فَ evidence encoded inside `jawab_shart_of.source_of_claim`, NOT a separate `jawab_marker_of` edge.

The SHART_JAWAB pilot's edge design is **carried forward verbatim** into Batch B. Batch B does not redesign the relations; it authorizes the production wiring that makes the design implementable.

---

## 4. Allowed implementation files (proposed; RULE_LOCK to confirm)

The implementation batch that derives from the Batch B RULE_LOCK may touch ONLY these paths:

| # | Path | Purpose | Required / Conditional |
|---|---|---|---|
| 1 | `clean_code/relation_extractor.py` | Add a new pass that consumes Phase 5 output and emits `condition_tool_of` and `jawab_shart_of` relations for the pilot construction. This is the file that gains Phase 5 import permission. | **Required** |
| 2 | `clean_code/meaning_assembler.py` | Extend the L7 `PASSTHROUGH` edge-type whitelist by exactly the two new relation names. **No Phase 5 import.** | **Required** |
| 3 | `clean_code/data/contracts/rules/relation_types.csv` | Add two rows (priorities 18, 19) for `condition_tool_of` and `jawab_shart_of`. | **Required** |
| 4 | `clean_code/test_shart_jawab_relations_pilot_2_282.py` | New test file per the SHART_JAWAB RULE_LOCK `7b77945` §10. | **Required** |
| 5 | `clean_code/test_production_path_segmentation.py` | **Narrow the isolation guard from a blanket block to an allow-list.** Specifically: update `t_phase5_clause_segmenter_not_imported_by_production_path` to permit Phase 5 surface symbols in `relation_extractor.py` while continuing to forbid them in all other entries of the original `production_files` list. Add a second guard test (or extend the existing one) that **positively asserts** Phase 5 symbols are NOT in the other 12 production files. | **Required** (Batch B-specific change to the guard test only — not a relaxation of the discipline, a refinement of it) |

No other files. The implementation batch's `git diff --name-only` must be exactly this 5-file set. Any file outside this list rejects the batch.

---

## 5. Forbidden files (binding for the future RULE_LOCK)

### 5.1 Phase 5 module (hard-forbidden)
- `clean_code/phase5_clause_segmenter.py` — **READ-ONLY**. Batch B consumes; it does NOT edit.

### 5.2 L1/L2/L3/L5/L6/L8 production layers (hard-forbidden — guard remains in force for all these)
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/i3rab_engine/*` (entire subtree)
- `clean_code/event_extractor.py` (Batch C is the future authorization)
- `clean_code/resolution_engine.py` (Batch D)
- `clean_code/reasoning_engine.py` (Batch E)
- `clean_code/analyze_verse_v3.py` (no Phase 5 import here; orchestrator stays clean)
- `clean_code/hidden_pronoun_signals.py`
- `clean_code/samarrai_analyzer.py`
- `clean_code/samarrai_certified_operator_gate.py`

### 5.3 MAANI / MASAQ / schema (hard-forbidden)
- All MAANI CSVs under `clean_code/data/contracts/maani/**`
- All MASAQ files (any path containing "masaq")
- `clean_code/data/contracts/maani/schema.md`
- `clean_code/samarrai_quran_sweep.py` + all sweep outputs

### 5.4 Other data / docs / tests (hard-forbidden)
- `data/contracts/**` outside `clean_code/data/contracts/rules/relation_types.csv`
- `data/MASAQ.csv`
- `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**`, `new_arabic_analyzer/**`, `archive/**`
- All other files under `docs/specs/` except this SPEC and its forthcoming RULE_LOCK
- All other `test_*.py` files (Batch B touches only `test_shart_jawab_relations_pilot_2_282.py` (new) and the targeted guard update in `test_production_path_segmentation.py`)

### 5.5 No untracked artifacts left behind
- No `out_*.txt`
- No `.pyc` modifications committed
- No `.claude/` content committed
- No stash content reintroduced

---

## 6. Guard policy (binding intent — RULE_LOCK to lock the exact form)

### 6.1 The guard is NOT deleted

`t_phase5_clause_segmenter_not_imported_by_production_path` (or its successor under a new name) remains a binding test in `test_production_path_segmentation.py`. Removing it would lose the isolation discipline Phase 5 Batch A established.

### 6.2 The guard becomes a narrow allow-list

The new behavior:
- **Allowed**: `relation_extractor.py` may import any Phase 5 surface symbol (`phase5_clause_segmenter`, `Phase5Clause`, `Phase5ClauseGraph`, `segment_clauses_from_surfaces`, `build_clause_graph`).
- **Forbidden**: every other module previously in the guard's `production_files` list — including specifically `meaning_assembler.py`, `event_extractor.py`, `resolution_engine.py`, `reasoning_engine.py`, `analyze_verse_v3.py`, `segmenter.py`, `i3rab_engine/*`, `master_token_lookup.py`, `hidden_pronoun_signals.py`, `samarrai_certified_operator_gate.py` — continues to be blocked.

### 6.3 Two-test structure (recommended; RULE_LOCK to confirm)

The RULE_LOCK should consider whether to keep the policy in one test with an allow-list or split it into two:

- **Negative test** (`t_phase5_clause_segmenter_not_imported_by_non_b_production_modules`): asserts that Phase 5 surface markers do NOT appear in any of the 12 still-blocked production files.
- **Positive test** (`t_phase5_clause_segmenter_consumed_only_by_relation_extractor`): asserts that the ONLY production file referencing Phase 5 surface markers is `relation_extractor.py`. Catches accidental future imports in any other module.

If the RULE_LOCK chooses the two-test form, both pass before and after Batch B ships.

### 6.4 The guard is the architectural enforcement of the batch plan

Batch C (when authorized) will extend the allow-list to include `event_extractor.py`. Batch D will add `resolution_engine.py`. Batch E will add `reasoning_engine.py`. Each future batch updates the allow-list under its own SPEC + RULE_LOCK. This SPEC authorizes only the **B half** — `relation_extractor.py` only.

---

## 7. Non-goals (explicit deferrals; RULE_LOCK will enforce)

The following are NOT in Batch B and require separate SPEC + RULE_LOCK approval:

- **Phase 5 Batch C** — `event_extractor.py` consumption (Replace PATCH-5's pause-walk with clause-window lookup; add `Event.clause_id` and `Event.parent_clause_id`).
- **Phase 5 Batch D** — `resolution_engine.py` and `hidden_pronoun_signals.py` consumption (Use clause spans for relative-antecedent search; wire hidden-subject signals to clause-anchored event agents).
- **Phase 5 Batch E** — `reasoning_engine.py` consumption (Use ClauseGraph for nested event-sequence answers; condition/answer pairs for "ماذا يَجِب لو …؟").
- **`meaning_assembler.py` direct Phase 5 import.** Batch B only adds names to the PASSTHROUGH whitelist; consumption flows through relations.
- **`analyze_verse_v3.py` Phase 5 import.** The orchestrator stays clean of Phase 5.
- **Other إِذَا occurrences in 2:282** — second (`إِذَا مَا دُعُوا۟`) and third (`إِذَا تَبَايَعْتُمْ`) deferred to follow-up batches.
- **Other conditional tools** — `إِنْ`, `إِذْمَا`, `لَوْ`, `لَوْلَا`, `أَمَّا`, `مَنْ`, `أَيّ`, `أَيْنَ`, `أَيْنَمَا`, `كَيْفَمَا`, `مَتَى`, `حَيْثُمَا`, `أَنَّى`, `مَهْمَا`, `كُلَّمَا`, `مَا`, `لَمَّا` — each requires its own SPEC.
- **Conditionals without an explicit فَ marker.**
- **Quran-wide condition handling.**
- **L5 event rewiring.** Phase 5 SPEC §7 specifically reserves `Event.clause_id` for Batch C.
- **L6 resolution improvements.** Phase 5 SPEC §7 reserves clause-aware antecedent search for Batch D.
- **L8 reasoning-engine changes.** Phase 5 SPEC §7 reserves nested event-sequence answers for Batch E.
- **MAANI expansion** (no MAANI CSV changes).
- **MASAQ work** (entire MASAQ track untouched).
- **New ProofKind values** — `{Certificate, Hypothesis, Zero}` unchanged.
- **Schema changes** — 19-column MAANI schema unchanged; `relation_types.csv` column order unchanged.
- **Hypothesis fallback** for the SHART_JAWAB edges. Per SHART_JAWAB RULE_LOCK §6.3, Certificate-or-nothing.
- **Sweep regeneration.** Batch B does not change sweep outputs; new relation names are not sweep dimensions.

---

## 8. Tests proposed (RULE_LOCK to finalize)

### 8.1 Guard tests (binding for Batch B's isolation architecture)

| # | Test | Asserts |
|---|---|---|
| G1 | `t_phase5_clause_segmenter_not_imported_by_non_b_production_modules` | Phase 5 surface markers (`phase5_clause_segmenter`, `Phase5Clause`, `Phase5ClauseGraph`, `segment_clauses_from_surfaces`, `build_clause_graph`) appear in **none** of the 12 still-blocked production files (every entry in the original `production_files` list except `relation_extractor.py`). Replaces the blanket guard. |
| G2 | `t_phase5_clause_segmenter_consumed_only_by_relation_extractor` *(recommended)* | `relation_extractor.py` is the **only** production module that imports Phase 5 surface symbols. Catches accidental future imports in other modules. |

### 8.2 SHART_JAWAB pilot tests (carry the SHART_JAWAB RULE_LOCK `7b77945` §10 test list)

| # | Test | Asserts |
|---|---|---|
| P1 | `t_2_282_first_idha_condition_tool_of_tadayantum` | L4 has `condition_tool_of: إِذَا(idx3) → تَدَايَنتُم(idx4)`, Certificate. |
| P2 | `t_2_282_jawab_shart_of_faktubu_to_tadayantum` | L4 has `jawab_shart_of: فَٱكْتُبُوهُ(idx9) → تَدَايَنتُم(idx4)`, Certificate. |
| P3 | `t_2_282_jawab_shart_source_of_claim_records_fa_marker` | `jawab_shart_of.source_of_claim` contains `introduced_by=فَ`. |
| P4 | `t_2_282_l7_contains_condition_and_jawab_edges_as_typed` | L7 has both edges as typed (not collapsed to `operator_meaning`). |
| P5 | `t_2_282_l7_entropy_remains_zero_and_consistent` | L7 Entropy == 0.0 AND consistency == `نَعَم`. |
| P6 | `t_2_282_two_new_edges_are_both_certificate` | Both edges' `proof_kind == "Certificate"`. |
| N1 | `t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot` | Pilot scope guard. |
| N2 | `t_2_282_no_unrelated_fa_token_linked_to_first_idha` | `فَلْيَكْتُبْ`, `فَلْيُمْلِلْ`, `فَإِن`, `فَتُذَكِّرَ`, `فَرَجُلٌ`, `فَلَيْسَ`, `فَإِنَّهُۥ` NOT linked. |
| N3 | `t_2_282_no_condition_edge_for_other_tools` | No `condition_tool_of` for any tool other than إِذَا. |
| N4 | `t_implementation_blocked_if_phase5_unavailable` | Synthesized scenario without Phase 5 output → 0 edges (no fallback re-detection). |
| N5 | `t_no_relation_when_no_fa_jawab_in_window` | Synthesized condition without فَ jawab in window → 0 edges. |

### 8.3 Cross-suite regression (must remain green at current baselines)

- `clean_code/test_production_path_segmentation.py` — must remain **158/158** (with the narrowed guard test counted).
- `clean_code/test_maani_batch_b_author_position.py` — must remain **6/6**.
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — must remain **20/20**.
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain at its current count.

Any suite regressing rejects the batch.

### 8.4 Test note on the narrowed guard

When Batch B replaces the blanket guard with the allow-list guard(s), the **total test count** of `test_production_path_segmentation.py` stays at **158** if the original guard test is mutated in place. If a second positive guard test is added (G2), the count goes to **159**. The RULE_LOCK will decide between these two options; either way, **no test regresses**.

---

## 9. Acceptance criteria (sketch; RULE_LOCK to finalize)

The implementation batch is acceptable iff:

1. `relation_extractor.py` imports `phase5_clause_segmenter` and emits the two SHART_JAWAB relations for the first إِذَا in 2:282.
2. `meaning_assembler.py` PASSTHROUGH whitelist is extended by exactly two entries.
3. `relation_types.csv` has exactly two new rows (priorities 18, 19).
4. New test file `test_shart_jawab_relations_pilot_2_282.py` is created with all §8.2 tests passing.
5. `test_production_path_segmentation.py` retains the guard discipline (narrowed allow-list per §6.2) and passes at 158 or 159.
6. The 12 non-Batch-B production modules contain zero Phase 5 surface references (guard G1 passes).
7. Only `relation_extractor.py` references Phase 5 surface symbols among production modules (guard G2 passes, if added).
8. 2:282 L7 metrics: nodes unchanged at 135; links increase by exactly +2; Entropy 0.0; consistency `نَعَم`.
9. No file outside §4 modified.
10. No file in §5 modified.
11. No untracked artifacts in commit.
12. Batch B report committed under separate approval.

---

## 10. Rejection criteria (sketch)

- Phase 5 surface markers appear in any non-`relation_extractor.py` production module → guard violated.
- `phase5_clause_segmenter.py` modified → §5.1 violated.
- Any non-allowed file in §4 modified.
- Any file in §5 modified.
- More than 2 condition/jawab edges per pilot construction → SHART_JAWAB design violated.
- Either SHART_JAWAB edge emits with `proof_kind` other than Certificate.
- Any expansion to other إِذَا, other tools, other verses → scope violated.
- Production test suite regresses below 158.
- Other test suites regress.
- Untracked artifacts in committed tree.

---

## 11. Rollback

If the batch is rejected per §10 or fails review after the implementation commit:

1. **Standard `git revert`** of the implementation commit. The revert restores `relation_extractor.py`, `meaning_assembler.py`, `relation_types.csv`, the original blanket guard test in `test_production_path_segmentation.py`, and deletes the new test file.
2. **No force-push.** No `git reset --hard` on shared branches.
3. **Phase 5 Batch A status preserved.** The original isolation guard returns to its pre-Batch-B blanket form on revert.
4. **No data outside this batch is touched.** MAANI, MASAQ, Phase 4 commits remain intact.
5. **Working tree post-revert** matches whatever commit was HEAD before this batch's implementation commit.

---

## 12. Governance (gate chain)

| Gate | Action | Status |
|---|---|---|
| 1 | **SPEC draft** | This document — pending review |
| 2 | Read-only investigations (re-verify guard behavior under the proposed narrowing; trace Phase 5 → relation_extractor data flow; confirm sweep outputs unaffected) | Pending |
| 3 | RULE_LOCK draft | Pending |
| 4 | RULE_LOCK commit approval | Pending |
| 5 | Implementation approval | Pending |
| 6 | Test approval | Pending |
| 7 | Commit approval | Pending |
| 8 | Report approval | Pending |

Each gate requires separate explicit approval. Skipping any gate rejects the batch.

### 12.1 Relationship to SHART_JAWAB pilot

The SHART_JAWAB pilot's documents (`cd83d7f` SPEC, `7b77945` RULE_LOCK) are **not amended or deleted** by this batch. The SHART_JAWAB design (two edges: `condition_tool_of` + `jawab_shart_of`, both Certificate, anchored on the condition verb, فَ inside `source_of_claim`) is **carried forward verbatim** into Batch B's inaugural use case.

The SHART_JAWAB RULE_LOCK `7b77945` is **superseded for implementation only** by Batch B's eventual RULE_LOCK, in the narrow sense that:
- Batch B's RULE_LOCK authorizes the Phase 5 import that `7b77945` did not.
- Batch B's RULE_LOCK authorizes the guard narrowing that `7b77945` did not.

Other than these two authorizations, the SHART_JAWAB pilot's locked design is unchanged. After Batch B ships, the SHART_JAWAB implementation is no longer blocked.

### 12.2 What requires a NEW separate SPEC (not this one)

- Phase 5 Batch C (`event_extractor.py` consumption).
- Phase 5 Batch D (`resolution_engine.py` consumption).
- Phase 5 Batch E (`reasoning_engine.py` consumption).
- Any other conditional tool (إِنْ / لَوْ / مَنْ / مَا / etc.).
- Other إِذَا occurrences within 2:282 or elsewhere.
- Conditionals without explicit فَ markers.
- Direct Phase 5 import in `meaning_assembler.py`.
- Direct Phase 5 import in `analyze_verse_v3.py`.
- Any change to Phase 5's standalone module API.
- Any new ProofKind values.
- Any schema column changes.

---

## 13. Risks

### 13.1 Guard narrowing could be over-relaxed

If the RULE_LOCK or implementation accidentally turns the guard into a no-op (e.g., empties the blocked list, or removes Phase 5 markers from the regex), the isolation discipline is lost. Mitigation: §8.1 G1 explicitly asserts the still-blocked list is non-empty and that none of the 12 still-blocked files reference Phase 5.

### 13.2 Future drift — Batch C/D/E may grow their own assumptions

If a future Batch C wires Phase 5 into `event_extractor.py`, the new test G2 must be updated to include `event_extractor.py` in the allow-list. This is acceptable expansion (each batch updates the policy as authorized) but must happen under that batch's SPEC, not silently.

### 13.3 Phase 5 module API stability

The Phase 5 module exports `Phase5Clause`, `Phase5ClauseGraph`, `segment_clauses`, `segment_clauses_from_surfaces`, `build_clause_graph`. Once `relation_extractor.py` depends on these, changes to Phase 5's API become production-breaking. Mitigation: the SHART_JAWAB pilot uses `segment_clauses_from_surfaces` (per Gate 2 investigation), which is the stable public API documented in the Phase 5 module's docstring.

### 13.4 Test count drift

If the implementation chooses to add G2 as a new test (rather than mutating G1 in place), the test count for `test_production_path_segmentation.py` increases from 158 to 159. The implementation's report must declare which choice was made, and downstream regression baselines must update accordingly.

### 13.5 Sequencing with the broader SHART_JAWAB pilot

The SHART_JAWAB pilot's commits (`cd83d7f`, `7b77945`) describe a 7-gate governance chain. Batch B adds an 8-gate prefix (its own SPEC → RULE_LOCK → implementation → tests → commit → report). This is heavy but correct: the pilot was blocked by a real architectural constraint, and the constraint's resolution properly belongs in Phase 5 Batch B.

---

## 14. One-screen recap

| Item | Value |
|---|---|
| Batch | Phase 5 Batch B — Relation/Clause Wiring |
| Type | Narrow production wiring of Phase 5 into one consumer (`relation_extractor.py`) |
| Reference SPEC | `docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md` (Batch A) |
| Inaugural use case | SHART_JAWAB pilot for 2:282 first إِذَا (carried forward from SHART_JAWAB RULE_LOCK `7b77945`) |
| Sole authorized importer | `clean_code/relation_extractor.py` |
| Guard policy | NOT deleted; **narrowed to an allow-list**; the 12 other production modules remain forbidden |
| Allowed files | 5: `relation_extractor.py`, `meaning_assembler.py`, `relation_types.csv`, new test file, `test_production_path_segmentation.py` (guard narrowing only) |
| Forbidden | `phase5_clause_segmenter.py` itself; all other production modules; all MAANI/MASAQ; all other tests |
| Locked edges | 2 per pilot construction (per SHART_JAWAB RULE_LOCK `7b77945` §3): `condition_tool_of` + `jawab_shart_of`, both Certificate |
| Expected 2:282 metrics | L7 nodes 135 unchanged; links +2; Entropy 0.0; consistency `نَعَم` |
| Tests | 2 guard (G1, optionally G2) + 11 SHART_JAWAB (P1–P6, N1–N5) + cross-suite regression (158→158 or 159, 6/6, 20/20, Phase 4) |
| Schema changes | None |
| ProofKind enum | Unchanged |
| Deferred | Phase 5 Batches C / D / E; all other conditional tools; all other verses; all other consumers |
| Governance | 8 gates; this SPEC is Gate 1 |
| Relationship to SHART_JAWAB pilot | Supersedes RULE_LOCK `7b77945` for implementation only (authorizes the Phase 5 import). Pilot's edge design carried forward verbatim. SHART_JAWAB docs preserved as historical. |
