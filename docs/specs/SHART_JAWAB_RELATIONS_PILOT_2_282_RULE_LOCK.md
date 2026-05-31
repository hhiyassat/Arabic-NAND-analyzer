# SHART/JAWAB Relations Pilot — Verse 2:282 — RULE_LOCK

> **Type:** RULE_LOCK (binding contract).
> **Date:** 2026-05-31
> **SPEC parent:** `docs/specs/SHART_JAWAB_RELATIONS_PILOT_2_282_SPEC_DRAFT.md` (commit `cd83d7f`).
> **Status:** Binding. Any violation rejects the batch.

Once approved, the boundaries below cannot be widened inside this batch. Any widening requires a new RULE_LOCK and a new batch.

---

## 0. Gate 2 findings (embedded preamble)

This RULE_LOCK is grounded in the read-only investigations completed on 2026-05-31 prior to drafting. The findings are reproduced here so the binding contract is anchored in current repo state, not in stale assumptions.

| # | Investigation | Finding (as of 2026-05-31 against commit `cd83d7f`) |
|---|---|---|
| 1 | Current baseline (2:282) | L3 correctly tags `إِذَا` as ظرف شرط; L4 emits `verb_in_clause` for `تَدَايَنتُم` and `فَٱكْتُبُوهُ` separately with no linking edge; L5 already carries `time=when_future` on both verbs; L7 = 135 nodes / 41 links / Entropy 0.0 / consistency نَعَم. The gap is purely structural-link-missing. |
| 2 | **Phase 5 is the source of truth** | `clean_code/phase5_clause_segmenter.py` already detects the conditional structure. Probed with 2:282 first conditional, it returns: `C002 type=condition head=إِذَا tokens 3-8 source=ConditionalScopeContract Certificate` + `C003 type=condition_answer_command head=فَٱكْتُبُوهُ tokens 9-9 parent_clause_id=C002 introduced_by=فَ Hypothesis`. **The linguistic detection is already done.** The pilot's job is to bridge this output into L4 token relations and L7 typed edges. |
| 3 | Naming audit | Existing relation conventions: `<role>_of` with source holding the role w.r.t. target. 13 active relations in `relation_extractor.py` + 4 more in `relation_types.csv`. No existing condition/shart/jawab relation names. Phase 5 uses `condition`, `condition_answer_command`, `ConditionalScopeContract`, `ConditionAnswerLinker` naming. The pilot names align. |
| 4 | Safety window | Token indices (whitespace-split): إِذَا=3, تَدَايَنتُم=4, فَٱكْتُبُوهُ=9, pause-mark `ۚ`=10. Offset تَدَايَنتُم→فَٱكْتُبُوهُ=5, fits within `min(idx+10=14, next-pause=10, EOV)`. No competing فَ-prefixed token in window. Phase 5's A2 ConditionalScopeContract already enforces the bounded scope. |
| 5 | Proof evidence | All of: (a) إِذَا L3 role=ظرف شرط, (b) Phase 5 C002 Certificate, (c) Phase 5 C003 with parent=C002, (d) فَ prefix on jawab segmented as CONJ, (e) no pause-mark between C002 and C003. **Sufficient for Certificate** on the bridged L4 edges. |
| 6 | Test scope | New file `test_shart_jawab_relations_pilot_2_282.py` (per-batch isolation pattern). Production runner doesn't require explicit registration. |
| 7 | File ownership | `relation_extractor.py` is primary owner (add a new pass consuming Phase 5 output). `meaning_assembler.py` needs PASSTHROUGH whitelist extension. `relation_types.csv` path is `clean_code/data/contracts/rules/relation_types.csv` (note `/rules/` subdirectory). Phase 5 file forbidden from edits. |

Any drift from these findings between this RULE_LOCK approval and implementation execution requires re-investigation, not silent adaptation.

---

## 1. Batch identity

| Field | Value |
|---|---|
| Batch name | **SHART_JAWAB_RELATIONS_PILOT_2_282** |
| Parent SPEC | `docs/specs/SHART_JAWAB_RELATIONS_PILOT_2_282_SPEC_DRAFT.md` (commit `cd83d7f`) |
| Type | L4 relation bridge + L7 edge whitelisting (NOT new linguistic detection; NOT Phase 5 edit) |
| Pilot target | **First `إِذَا … فَ` construction in verse 2:282 only** |
| Source restriction | Phase 5 (`phase5_clause_segmenter.py`) is the binding source of truth |
| Source-of-truth lock | The pilot does NOT reimplement conditional detection; it BRIDGES existing Phase 5 output into L4/L7 |

---

## 2. Pilot target (binding scope)

The pilot binds exactly one construction:

```
يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوٓا۟ إِذَا تَدَايَنتُم بِدَيْنٍ إِلَىٰٓ أَجَلٍ مُّسَمًّى فَٱكْتُبُوهُ ۚ
                                       ↑          ↑                              ↑
                                      idx 3     idx 4                         idx 9
                                       TOOL      EVENT (شرط)                   JAWAB (مع فاء)
```

**Explicitly out of pilot scope (binding):**
- The other two `إِذَا` occurrences in 2:282 (`إِذَا مَا دُعُوا۟`, `إِذَا تَبَايَعْتُمْ`).
- All four `فَإِن` occurrences in 2:282.
- All `إِذَا` outside 2:282.
- All other conditional tools: `إِنْ`, `إِذْمَا`, `لَوْ`, `لَوْلَا`, `أَمَّا`, `مَنْ`, `أَيّ`, `أَيْنَ`, `أَيْنَمَا`, `كَيْفَمَا`, `مَتَى`, `حَيْثُمَا`, `أَنَّى`, `مَهْمَا`, `كُلَّمَا`, `مَا` (شرطية), `لَمَّا`.
- All Quran-wide conditional handling.
- Conditionals without an explicit فَ marker.

Any of the above appearing in the implementation rejects the batch (§13).

---

## 3. Locked relation design — exactly 2 edges (NOT 3)

### 3.1 Decision (binding)

After analyzing the three candidate names suggested in the user's RULE_LOCK request (`condition_tool_of`, `shart_event_of`, `jawab_shart_of`) plus the SPEC's earlier `jawab_marker_of`, this RULE_LOCK locks **exactly 2 emitted edges per pilot construction**, NOT 3.

**Reasoning** (each candidate adjudicated):

| Candidate | Decision | Why |
|---|---|---|
| `condition_tool_of` | ✅ **Emit as edge** | إِذَا → تَدَايَنتُم. Distinct (source, target, type). Matches `harf_jarr_of` convention. |
| `jawab_shart_of` | ✅ **Emit as edge** | فَٱكْتُبُوهُ → تَدَايَنتُم. Distinct (source, target, type). |
| `shart_event_of` | ❌ **Do NOT emit as edge** | Would be the inverse direction of `condition_tool_of` (تَدَايَنتُم → إِذَا) — semantic inverse of an already-emitted edge. The condition-event role of تَدَايَنتُم is **implicit**: it is the target of `condition_tool_of` and the target of `jawab_shart_of`, so its role as the shart event is unambiguously recoverable without a third edge. |
| `jawab_marker_of` (from SPEC) | ❌ **Do NOT emit as edge** | Per user instruction: "If jawab_marker_of would duplicate the same source/target as jawab_shart_of, do NOT create a separate edge. Instead encode فاء evidence as an attribute/source_of_claim on jawab_shart_of." It would duplicate (فَٱكْتُبُوهُ → تَدَايَنتُم). Encoded inside `jawab_shart_of.source_of_claim` instead. |

**Result: +2 L7 edges per pilot construction.** The "+2 or +3" range in the user's request resolves to **+2**.

### 3.2 Locked edge specifications

#### Edge 1: `condition_tool_of`

| Field | Value |
|---|---|
| Relation name | `condition_tool_of` |
| Source token | `إِذَا` at idx 3 in 2:282 |
| Target token | `تَدَايَنتُم` at idx 4 in 2:282 |
| Direction | إِذَا → تَدَايَنتُم (source = tool; target = condition verb) |
| Semantics | إِذَا is the conditional tool of تَدَايَنتُم. |
| ProofKind | **Certificate** (per §6, all evidence available) |
| `source_of_claim` (required text) | `phase5:C002.head=إِذَا + L3:role=ظرف_شرط + ConditionalScopeContract:Certificate` |
| `operator` | `إِذَا` |
| `contract` | `relation_extractor:condition_tool_from_phase5` |

#### Edge 2: `jawab_shart_of`

| Field | Value |
|---|---|
| Relation name | `jawab_shart_of` |
| Source token | `فَٱكْتُبُوهُ` at idx 9 in 2:282 |
| Target token | `تَدَايَنتُم` at idx 4 in 2:282 |
| Direction | فَٱكْتُبُوهُ → تَدَايَنتُم (source = jawab; target = condition verb) |
| Semantics | فَٱكْتُبُوهُ is the جواب of the condition verb تَدَايَنتُم. |
| ProofKind | **Certificate** (per §6, Phase 5 explicitly links C003.parent_clause_id=C002 with `introduced_by=فَ`) |
| `source_of_claim` (required text) | `phase5:C003.parent_clause_id=C002 + introduced_by=فَ + ImperativeFormContract+ConditionAnswerLinker` |
| `operator` | `فَ` (the marker) |
| `contract` | `relation_extractor:jawab_shart_from_phase5` |

### 3.3 Anchor invariant

Both edges target the **condition verb** (`تَدَايَنتُم`), making it the structural anchor of the conditional. This means:
- The condition verb is the only node receiving conditional edges.
- The condition tool (إِذَا) and the jawab (فَٱكْتُبُوهُ) point INTO this anchor.
- Queries like "what conditional structure includes verb X?" resolve by finding nodes pointing to X via these two relation names.

### 3.4 What is NOT a relation but recoverable

| Implicit role | How to recover |
|---|---|
| تَدَايَنتُم is the **شرط event** | It is the target of `condition_tool_of` ← therefore by construction a condition verb. |
| فَ is the **jawab marker** | Recorded inside `jawab_shart_of.operator="فَ"` and `source_of_claim` text. No separate edge. |
| The condition is bounded by a clause | Recoverable from Phase 5 C002 itself if downstream needs the boundary; not exposed as L4 edge. |

---

## 4. Allowed implementation files

The implementation batch may touch ONLY these paths:

| # | Path | Purpose | Required / Conditional |
|---|---|---|---|
| 1 | `clean_code/relation_extractor.py` | Add a new pass `_pN_condition_jawab_from_phase5()` that consumes Phase 5 condition / condition_answer_command clauses and emits the 2 locked relations per §3.2. | **Required** |
| 2 | `clean_code/meaning_assembler.py` | Extend the `PASSTHROUGH` set (around line 220) by adding exactly two entries: `"condition_tool_of"` and `"jawab_shart_of"`. | **Required** |
| 3 | `clean_code/data/contracts/rules/relation_types.csv` | Add exactly 2 rows at priorities 18 and 19. *(Note: path includes `/rules/` subdirectory — confirmed in Gate 2 Investigation 7.)* | **Required** |
| 4 | `clean_code/test_shart_jawab_relations_pilot_2_282.py` | New test file per §10. | **Required** |
| 5 | `clean_code/test_production_path_segmentation.py` | **Conditional — only** if the implementation discovers the production runner explicitly registers per-test-file entries and needs a one-line registration for the new test file. If the runner discovers tests dynamically (Gate 6 likely investigation), this file is NOT touched. | **Conditional** |

The implementation batch's `git diff --name-only` must be a subset of the above. Any file outside this list is grounds for rejection (§13).

---

## 5. Forbidden files (binding)

The following files **MUST NOT** be modified in this pilot. Any modification rejects the batch.

### 5.1 Source-of-truth (hard-forbidden — pilot principle)
- `clean_code/phase5_clause_segmenter.py` — **READ-ONLY**. The pilot bridges Phase 5 output; it does not modify the detector.

### 5.2 L1/L2/L3/L5/L6/L8 layers (hard-forbidden)
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/i3rab_engine/*` (entire subtree — إِذَا role already correct per layer3 patch 11)
- `clean_code/event_extractor.py` (L5 unchanged — no new events, only relations)
- `clean_code/resolution_engine.py` (L6 unchanged)
- `clean_code/reasoning_engine.py` (L8 unchanged — surfaces conditional through standard pipeline; no rule injection. Gate 2 found no evidence requiring L8 edits.)
- `clean_code/samarrai_analyzer.py`
- `clean_code/samarrai_certified_operator_gate.py`

### 5.3 MAANI / MASAQ / Schema (hard-forbidden)
- All MAANI CSVs under `clean_code/data/contracts/maani/**`
- All MASAQ files (any path containing "masaq")
- `clean_code/data/contracts/maani/schema.md`
- `clean_code/samarrai_quran_sweep.py`
- All sweep output files

### 5.4 Other data / docs (hard-forbidden)
- `data/contracts/**` outside `clean_code/data/contracts/rules/relation_types.csv`
- `data/MASAQ.csv`
- `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**`
- `new_arabic_analyzer/**`
- `archive/**`
- All other files under `docs/specs/` except this RULE_LOCK (no doc edits during implementation)

### 5.5 Other tests (hard-forbidden)
- `clean_code/test_maani_batch_b_author_position.py`
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py`
- `clean_code/test_phase4_certificate_reevaluation.py`
- All other existing `test_*.py` files except for the conditional registration in §4 entry 5

### 5.6 No untracked artifacts
- No `out_*.txt`
- No `.pyc` modifications committed
- No `.claude/` content committed
- No stash content reintroduced

---

## 6. Proof discipline (binding)

### 6.1 Certificate criteria (ALL must hold)

For each of the two edges in §3.2, emit `Certificate` ONLY IF all of the following hold:

| # | Criterion | Verifiable how |
|---|---|---|
| C1 | Phase 5 output for the verse contains a clause with `type="condition"` whose `head_token` is `إِذَا` at idx 3 (for 2:282) | Read Phase 5 clause graph in the relation_extractor pass |
| C2 | Phase 5 output for the verse contains a clause with `type="condition_answer_command"` whose `parent_clause_id` matches the condition clause's `clause_id` | Read Phase 5 clause graph |
| C3 | The condition clause's `confidence` is `Certificate` (i.e., `ConditionalScopeContract` certified) | Phase 5 already enforces this |
| C4 | The condition_answer_command clause's `introduced_by` is `فَ` | Phase 5 already records this |
| C5 | The condition verb token (target of both edges) has L3 class `FIIL` and is at the position recorded by Phase 5 as the verb head of the condition clause | Read L3 + Phase 5 |

If all of C1–C5 hold, emit BOTH edges per §3.2 with `proof_kind=Certificate`.

### 6.2 Blocked / Stop behavior

Per the user's instruction:
> "If Phase 5 data is unavailable to relation_extractor, implementation must stop and report blocked rather than inventing a relation."

If, at implementation time, Phase 5 output is not reachable from `relation_extractor.py` (e.g., the bridge is not wired through the analysis pipeline), the implementer **MUST**:

1. **Stop implementation immediately**.
2. **Report the blocker to the user** with concrete evidence (the exact location where Phase 5 output should arrive and the actual state).
3. **Do not invent a fallback** that re-detects conditional structure inside `relation_extractor.py`. Such re-detection would violate the source-of-truth lock (§1) and is grounds for rejection (§13).

### 6.3 No Hypothesis fallback in this pilot

Unlike the SPEC's earlier §4.3 sketch, this RULE_LOCK does NOT permit Hypothesis emission for this pilot. Either:
- All §6.1 criteria hold → emit Certificate, OR
- Any criterion fails → emit **nothing** (no edge).

Rationale: the pilot is bounded to one verified construction. Hypothesis-level conditional edges are deferred to a future expansion batch that explicitly defines partial-evidence rules.

### 6.4 No Zero node required

Per the user's instruction: "No Zero node required; absence of relation is enough outside the pilot." If criteria fail, simply do not emit. Do not emit a sentinel `Zero` edge.

---

## 7. Schema lock

- The 19-column MAANI schema and all i3rab structures are unchanged.
- `clean_code/data/contracts/rules/relation_types.csv` is the only schema-style file edited. **Exactly 2 rows added** (priorities 18, 19), matching the existing column order (`priority, name, kind, role_source, role_target, note`).
- No new column types.
- No inline relation definitions in Python beyond the two-relation extraction pass.

### 7.1 Locked `relation_types.csv` additions

```
18,condition_tool_of,conditional,أداة_شرط,FIIL,أَداة الشَّرط (إِذَا) تَدُلّ على الفِعل الشَّرطيّ
19,jawab_shart_of,conditional,جواب_شرط,FIIL,جَواب الشَّرط (الفِعل الَّذي يَأتي بَعد فاء الجَواب) — يَرتَبِط بِفِعل الشَّرط
```

`kind=conditional` is a new value in the `kind` column. This is **NOT** a schema change — the `kind` column is open-set (existing values include `subj_pred`, `topic_comment`, `possession`, `attribute`, `coordination`, `apposition`, `vocative`, `prep_phrase`, `clause_anchor`). Adding `conditional` as a new kind matches the existing pattern.

---

## 8. ProofKind lock

- ProofKind enum `{Certificate, Hypothesis, Zero}` is unchanged.
- Per §6.1 + §6.3, the two new edges emit only `Certificate` or nothing.
- Batch B monotonicity (no Certificate→Hypothesis upgrades) preserved.
- No new ProofKind values introduced.
- No code path added that upgrades any other ProofKind.

---

## 9. Expected post-implementation metrics for verse 2:282

| Metric | Pre-pilot baseline | Post-pilot expected |
|---|---|---|
| L7 nodes | 135 (52C + 83H) | **135 (unchanged)** — no new nodes |
| L7 links | 41 (14C + 27H) | **43 (16C + 27H)** — +2 Certificate edges |
| L7 coverage | 63.2% | likely 63.2% — 65% (more elements participate, but not new nodes) |
| L7 Entropy | 0.0 | **must remain 0.0** |
| L7 consistency | نَعَم ✓ | **must remain نَعَم** |
| L6 resolutions | 5 Zero (relatives/anaphora) | **unchanged** — pilot adds no L6 edges |
| L8 `مَتى حَدَث؟` | ✓ Certificate when_future | **unchanged** |
| L8 `ما تَسَلسُل الأَحداث؟` | flat textual order | **may show conditional grouping** — but exact format is not locked in this RULE_LOCK; test P5 only asserts that the conditional dependency is recoverable from the answer, not the exact display format |

Any other 2:282 metric drift rejects the batch (§13).

---

## 10. Tests required

The implementation batch MUST add **all** of the following tests to `clean_code/test_shart_jawab_relations_pilot_2_282.py`. Missing any rejects the batch.

### 10.1 Positive tests (binding pilot assertions)

| # | Test | Asserts |
|---|---|---|
| P1 | `t_2_282_first_idha_condition_tool_of_tadayantum` | After analyzing 2:282, L4 contains exactly one `condition_tool_of` edge with `source` token surface = `إِذَا` at idx 3 and `target` token surface = `تَدَايَنتُم` at idx 4. ProofKind = Certificate. |
| P2 | `t_2_282_jawab_shart_of_faktubu_to_tadayantum` | L4 contains exactly one `jawab_shart_of` edge with `source` = `فَٱكْتُبُوهُ` at idx 9 and `target` = `تَدَايَنتُم` at idx 4. ProofKind = Certificate. |
| P3 | `t_2_282_jawab_shart_source_of_claim_records_fa_marker` | The `jawab_shart_of` edge's `source_of_claim` field contains `introduced_by=فَ` (or equivalent text proving the فاء evidence was preserved per §3.2 Edge 2). |
| P4 | `t_2_282_l7_contains_condition_and_jawab_edges_as_typed` | L7 MeaningGraph has at least one edge with `edge_type=="condition_tool_of"` and at least one with `edge_type=="jawab_shart_of"`. Neither has collapsed to `operator_meaning`. |
| P5 | `t_2_282_l7_entropy_remains_zero_and_consistent` | L7 Entropy == 0.0 AND consistency == True (نَعَم) after the new edges are added. |
| P6 | `t_2_282_two_new_edges_are_both_certificate` | Both new edges have `proof_kind == "Certificate"`. |

### 10.2 Negative tests (binding boundary guards)

| # | Test | Asserts |
|---|---|---|
| N1 | `t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot` | No `condition_tool_of` edge sourced from the second `إِذَا` (`إِذَا مَا دُعُوا۟`) or third `إِذَا` (`إِذَا تَبَايَعْتُمْ`) in 2:282. Pilot scope guard. |
| N2 | `t_2_282_no_unrelated_fa_token_linked_to_first_idha` | No `jawab_shart_of` edge with `target=تَدَايَنتُم` and `source` other than `فَٱكْتُبُوهُ`. (Tests against `فَلْيَكْتُبْ`, `فَلْيُمْلِلْ`, `فَإِن`, `فَتُذَكِّرَ`, `فَرَجُلٌ`, `فَلَيْسَ`, `فَإِنَّهُۥ` all NOT being linked to the first إِذَا.) |
| N3 | `t_2_282_no_condition_edge_for_other_tools` | No `condition_tool_of` edge has a source whose surface is one of: `إِنْ`, `إِذْمَا`, `لَوْ`, `لَوْلَا`, `أَمَّا`, `مَنْ`, `أَيّ`, `أَيْنَ`, `أَيْنَمَا`, `كَيْفَمَا`, `مَتَى`, `حَيْثُمَا`, `أَنَّى`, `مَهْمَا`, `كُلَّمَا`, `مَا`, `لَمَّا`. Pilot is إِذَا-only. |
| N4 | `t_implementation_blocked_if_phase5_unavailable` | A unit-style test that, given a synthesized scenario where Phase 5 output is absent, the relation extractor pass emits **zero** condition/jawab edges (does NOT fall back to re-detection). |
| N5 | `t_no_relation_when_no_fa_jawab_in_window` | A synthesized scenario where إِذَا is followed by a condition verb but no فَ-prefixed answer in window — verify zero edges. |

### 10.3 Cross-suite regression (must remain green at current baselines)

- `clean_code/test_production_path_segmentation.py` — must remain **158/158**.
- `clean_code/test_maani_batch_b_author_position.py` — must remain **6/6**.
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — must remain **20/20**.
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain at its current count.

Any suite regressing rejects the batch.

---

## 11. Acceptance criteria

The implementation batch is **acceptable** if and only if **all** of the following hold:

1. Exactly 2 new relations emitted per pilot construction in 2:282 (`condition_tool_of` + `jawab_shart_of`), per §3.2.
2. Both edges' source/target/direction/ProofKind/source_of_claim match §3.2 cell-for-cell.
3. `condition_tool_of` and `jawab_shart_of` appear in L7 MeaningGraph as typed edges (not collapsed to `operator_meaning`).
4. 2:282 L7 Entropy remains 0.0 (§9).
5. 2:282 L7 consistency remains نَعَم (§9).
6. 2:282 L7 nodes unchanged at 135 (§9).
7. 2:282 L7 links increases by exactly 2 (41 → 43) (§9).
8. All §10.1 positive tests pass.
9. All §10.2 negative tests pass.
10. Cross-suite regression green (§10.3).
11. Only files in §4 modified. (If §4 entry 5 was NOT needed, the diff is 4 files; if it WAS needed, the diff is 5 files.)
12. No file in §5 modified.
13. No untracked artifacts (`.pyc`, `out_*.txt`, `.claude/`) committed.
14. `relation_types.csv` has exactly 2 new rows at priorities 18, 19 per §7.1.
15. `meaning_assembler.py` PASSTHROUGH whitelist extended by exactly 2 entries.
16. A batch report at `docs/specs/SHART_JAWAB_RELATIONS_PILOT_2_282_REPORT.md` is produced (separately committed under separate approval).

If any of the 16 conditions fails, the batch is **rejected** (§13).

---

## 12. Rejection criteria

The implementation batch is **rejected** if any of the following occurs:

| Trigger | Reason |
|---|---|
| Any file outside §4 modified | Allowed-files lock violated. |
| Any file in §5 modified | Forbidden-files lock violated. |
| `phase5_clause_segmenter.py` modified | Source-of-truth lock §1 / §5.1 violated. |
| More than 2 condition/jawab edges emitted per pilot construction | §3.1 lock violated. |
| `shart_event_of` or `jawab_marker_of` emitted as separate edges | §3.1 explicit rejection. |
| Either locked edge has a different direction than §3.2 | Direction lock violated. |
| Either locked edge emits with `proof_kind` other than `Certificate` (or fails to emit at all) | §6.3 violated. |
| A condition relation emitted for the second or third `إِذَا` in 2:282 | Scope lock §2 violated (test N1 fails). |
| A condition relation emitted for any verse other than 2:282 | Scope lock §2 violated. |
| A condition relation emitted for any tool other than إِذَا | Scope lock §2 violated (test N3 fails). |
| A condition relation emitted when Phase 5 output is unavailable (fallback re-detection) | §6.2 violated (test N4 fails). |
| Any new ProofKind value introduced | §8 violated. |
| Any ProofKind upgrade code path added | Batch B monotonicity violated. |
| Schema change to `relation_types.csv` (column rename / reorder) | §7 violated. |
| `kind="conditional"` used for any row besides the two new ones in `relation_types.csv` | §7.1 violated. |
| 2:282 L7 Entropy != 0.0 post-implementation | §9 / test P5 violated. |
| 2:282 L7 consistency != نَعَم post-implementation | §9 / test P5 violated. |
| 2:282 L7 link count delta != +2 | §9 violated. |
| Unsafe L6 link introduced (e.g., new anaphora/relative resolution) | Out-of-scope for pilot. |
| `test_production_path_segmentation.py` regresses below 158/158 | §10.3 violated. |
| Any other test suite regresses | §10.3 violated. |
| Untracked artifacts (`out_*.txt`, `.pyc`) left in committed tree | Hygiene lock §5.6 violated. |
| Goldens regress on MASAQ goldens (2:282, 2:196, 28:7, 1:1) | Cross-track stability violated. |
| Any expansion of conditional grammar beyond the one pilot construction | Scope lock §2 violated. |

Rejection is total — partial acceptance is not permitted.

---

## 13. Rollback

If the batch is rejected per §12 or fails review after the implementation commit:

1. **Standard `git revert`** of the implementation commit. The revert restores `relation_extractor.py`, `meaning_assembler.py`, `relation_types.csv`, deletes the new test file, and (if applicable) reverts the production test runner registration.
2. **No force-push.** No `git reset --hard` on shared branches.
3. **No data outside this pilot is touched** in the rollback. Phase 5, all MAANI commits, all MASAQ commits, and the historical artifacts (SPEC `cd83d7f`) remain intact.
4. **Working tree post-revert** matches `cd83d7f` + `.claude/`.
5. **Stash list and prior commits** must not be touched in the rollback.

If the rollback itself requires destructive operations beyond `git revert`, halt and consult the user. Do not amend the rejected commit.

---

## 14. Source traceability

Every relation emitted by this pilot traces to Phase 5 output, NOT to bespoke detection logic in `relation_extractor.py`.

| Emitted edge | Phase 5 evidence |
|---|---|
| `condition_tool_of: إِذَا → تَدَايَنتُم` (Certificate) | Phase 5 clause `C002`: `type=condition`, `head_token=إِذَا`, `head_kind=particle`, `source=ConditionalScopeContract`, `confidence=Certificate`. |
| `jawab_shart_of: فَٱكْتُبُوهُ → تَدَايَنتُم` (Certificate) | Phase 5 clause `C003`: `type=condition_answer_command`, `head_token=فَٱكْتُبُوهُ`, `parent_clause_id=C002`, `introduced_by=فَ`, `source=ImperativeFormContract+ConditionAnswerLinker`. The target (`تَدَايَنتُم`) is the verb head of C002. |

Any edge content not traceable to Phase 5 is **not admissible** in this pilot.

---

## 15. Governance

### 15.1 Approval gates (sequential; each requires separate explicit approval)

1. **SPEC review + approval** — `docs/specs/SHART_JAWAB_RELATIONS_PILOT_2_282_SPEC_DRAFT.md`. ✅ Completed at commit `cd83d7f`.
2. **Gate-2 read-only investigations** — ✅ Completed 2026-05-31; findings embedded in §0.
3. **RULE_LOCK approval** — this document. *Pending review at time of writing.*
4. **Implementation approval** — separate explicit approval before any file under §4 is touched.
5. **Test approval** — after implementation, test results reported back to user.
6. **Commit approval** — user approves the specific commit hash for the implementation.
7. **Report approval** — `docs/specs/SHART_JAWAB_RELATIONS_PILOT_2_282_REPORT.md` written and committed under separate approval after the implementation commit lands.

Skipping any gate rejects the batch.

### 15.2 What is NEVER allowed inside this pilot
- Modifying `phase5_clause_segmenter.py` (source-of-truth lock §1 / §5.1).
- Adding more than 2 condition/jawab edges per pilot construction.
- Emitting `shart_event_of` or `jawab_marker_of` as separate edges (§3.1).
- Hypothesis emission for these edges (§6.3).
- Re-detecting conditional structure inside `relation_extractor.py` when Phase 5 is absent (§6.2).
- Schema changes to `relation_types.csv` columns.
- ProofKind enum changes (§8).
- Touching any file in §5 (no conditional-lift clause).
- Adding any operator/tool/verse beyond the locked scope (§2).
- Citing or consuming any external source.
- Modifying any committed historical artifact (`cd83d7f`).

### 15.3 What requires a new RULE_LOCK (NOT this one)
- Handling the second or third إِذَا in 2:282 — separate expansion batch.
- Handling any other conditional tool — separate per-tool batch.
- Conditionals without explicit فَ markers — separate batch.
- Extending the relation set with `shart_event_of` as a non-inverse meaningful edge — would require a new relation design.
- L8 reasoning enhancements that go beyond passive surfacing of the new edges — separate L8 batch.
- L6 conditional-anaphora resolution (e.g., resolving the implicit subject in conditional clauses) — separate L6 batch.

### 15.4 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. `git log --oneline -20` — confirm no in-flight commits on Phase 5 or MAANI files since this RULE_LOCK.
2. `git status` — confirm working tree is clean except `.claude/`.
3. `git stash list` — confirm no untracked WIP exists.

If any concurrent activity is found, postpone implementation until that activity completes.

---

## 16. One-screen recap

| Item | Value |
|---|---|
| Batch | SHART_JAWAB_RELATIONS_PILOT_2_282 |
| Type | L4 bridge + L7 whitelisting (NOT new detection) |
| Source of truth | Phase 5 (`phase5_clause_segmenter.py`), forbidden from edits |
| Pilot construction | `إِذَا تَدَايَنتُم … فَٱكْتُبُوهُ` (verse 2:282, first occurrence only) |
| Locked edges | **Exactly 2**: `condition_tool_of` (إِذَا→تَدَايَنتُم) + `jawab_shart_of` (فَٱكْتُبُوهُ→تَدَايَنتُم) |
| Rejected candidate edges | `shart_event_of` (inverse of `condition_tool_of`); `jawab_marker_of` (duplicate of `jawab_shart_of`). فاء evidence inside `jawab_shart_of.source_of_claim`. |
| ProofKind | Certificate only; no Hypothesis fallback; no Zero edge. Block-and-report if Phase 5 unavailable. |
| Allowed files | 4 required + 1 conditional = max 5 (`relation_extractor.py`, `meaning_assembler.py`, `relation_types.csv`, new test file, optional production runner registration) |
| Forbidden | Phase 5 + i3rab + event_extractor + L1/L2/L6/L8 + MAANI + MASAQ + schema.md + all other tests |
| Expected metrics for 2:282 | L7 nodes 135 (unchanged); L7 links 41→43 (+2 Certificate); Entropy 0.0; consistency نَعَم |
| Tests | 6 positive (P1–P6) + 5 negative (N1–N5) + cross-suite regression (158/158, 6/6, 20/20, Phase 4) |
| Schema changes | None (kind="conditional" is an open-set value, not a column change) |
| ProofKind enum | Unchanged |
| Rollback | `git revert`; no force-push; Phase 5 untouched throughout |
| Governance | 7 gates; 3 complete (SPEC, Gate 2, this RULE_LOCK pending approval); 4 remaining |
