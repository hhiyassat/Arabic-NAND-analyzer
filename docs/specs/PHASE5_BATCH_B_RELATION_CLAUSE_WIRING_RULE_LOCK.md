# Phase 5 Batch B — Relation / Clause Wiring — RULE_LOCK

> **Type:** RULE_LOCK (binding contract).
> **Date:** 2026-05-31
> **SPEC parent:** `docs/specs/PHASE5_BATCH_B_RELATION_CLAUSE_WIRING_SPEC_DRAFT.md` (commit `e6d4308`).
> **Reference SPEC (Phase 5 Batch A):** `docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md`.
> **Inherits inaugural use case from:** SHART_JAWAB pilot RULE_LOCK `7b77945` (carried forward verbatim for the edge design).
> **Status:** Binding. Any violation rejects the batch.

Once approved, the boundaries below cannot be widened inside this batch. Any widening requires a new RULE_LOCK and a new batch.

---

## 0. Gate 2 findings (embedded preamble)

This RULE_LOCK is grounded in the read-only investigations completed on 2026-05-31 prior to drafting.

| # | Investigation | Finding |
|---|---|---|
| 1 | Guard structure | `t_phase5_clause_segmenter_not_imported_by_production_path` at `test_production_path_segmentation.py:1771–1818` blocks Phase 5 from 13 named production files. Regex matches `phase5_clause_segmenter`, `Phase5Clause`, `Phase5ClauseGraph`, `segment_clauses_from_surfaces`, `build_clause_graph`. **The regex does NOT match the bare `segment_clauses` symbol — a regex leak.** |
| 2 | Phase 5 public API | `Phase5Clause` (dataclass, line 172), `Phase5ClauseGraph` (dataclass, line 190), `segment_clauses` (line 351), `segment_clauses_from_surfaces` (line 284), `build_clause_graph` (line 360). Recommended for Batch B: `Phase5Clause` + `segment_clauses_from_surfaces`. |
| 3 | relation_extractor integration | `RelationExtractor.extract()` (lines 329–836) returns `g` at line 836. Best insertion point for the new pass: immediately before `return g`. Existing helpers `_p7_*` and `_p12_*` show the phase numbering convention. |
| 4 | meaning_assembler | `PASSTHROUGH` set at lines 215–229 contains 22 entries. Unknown relation names collapse to `operator_meaning`. Adding the new names is a 2-entry whitelist extension. **No Phase 5 import needed.** |
| 5 | relation_types.csv | At `clean_code/data/contracts/rules/relation_types.csv`. Schema: `priority,name,kind,role_source,role_target,note`. 17 rows currently (priorities 1–17). `kind` is an open-set column; adding `kind=conditional` matches the existing pattern. |
| 6 | Test naming | Recommend `clean_code/test_shart_jawab_relations_pilot_2_282.py` (per SHART_JAWAB RULE_LOCK `7b77945` §10) rather than a new Batch B-named file. The pilot test file IS the Batch B test file. |
| 7 | Baseline (2:282) | L7 nodes 135 (52C + 83H), links 41 (14C + 27H), coverage 63.2%, Entropy 0.0, consistency نَعَم. Zero existing condition/jawab/shart relations. |

Any drift from these findings between this RULE_LOCK approval and implementation execution requires re-investigation, not silent adaptation.

---

## 1. Batch identity

| Field | Value |
|---|---|
| Batch name | **Phase 5 Batch B — Relation / Clause Wiring** |
| Parent SPEC | `docs/specs/PHASE5_BATCH_B_RELATION_CLAUSE_WIRING_SPEC_DRAFT.md` (commit `e6d4308`) |
| Reference SPEC (Batch A) | `docs/specs/CLAUSE_SENTENCE_SEGMENTATION_SPEC_DRAFT.md` |
| Inaugural use case | SHART_JAWAB pilot for verse 2:282, first إِذَا construction (`إِذَا تَدَايَنتُم … فَٱكْتُبُوهُ`) |
| SHART_JAWAB RULE_LOCK | `7b77945` — its edge design (`condition_tool_of` + `jawab_shart_of`) is carried forward verbatim by this batch |
| Source of truth | `clean_code/phase5_clause_segmenter.py` (READ-ONLY) |
| Sole authorized importer (new) | `clean_code/relation_extractor.py` |

---

## 2. Source-of-truth lock (binding)

| Constraint | Statement |
|---|---|
| Source-of-truth module | `clean_code/phase5_clause_segmenter.py` — produces all conditional/answer structure consumed by this batch |
| Forbidden edit | Phase 5 module MUST NOT be edited (§5.1) |
| Forbidden re-detection | `relation_extractor.py` MUST NOT scan tokens manually for إِذَا / فَ patterns when Phase 5 output is absent (§6.4) |
| Forbidden silent fallback | If Phase 5 returns no condition/jawab clause for the verse, the new pass emits zero edges. No alternative detection is invoked. |
| Forbidden index guess | If token-index reconciliation between Phase 5 surfaces and `RelationExtractor` token positions fails for the pilot construction, the new pass emits zero edges (§6.5). No fuzzy or guessed mapping. |

---

## 3. Allowed implementation files (exactly 5)

The implementation batch may touch ONLY these paths:

| # | Path | Purpose | Required / Conditional |
|---|---|---|---|
| 1 | `clean_code/relation_extractor.py` | Import Phase 5 API at module top + add new pass `_pN_condition_jawab_from_phase5(self, g, sent, tokens)` invoked immediately before `return g` at line 836. The ONLY new production importer of Phase 5. | **Required** |
| 2 | `clean_code/meaning_assembler.py` | Extend the `PASSTHROUGH` set by exactly 2 string entries: `"condition_tool_of"` and `"jawab_shart_of"`. **No Phase 5 import.** | **Required** |
| 3 | `clean_code/data/contracts/rules/relation_types.csv` | Add exactly 2 rows at priorities 18, 19 (verbatim text in §7.2). | **Required** |
| 4 | `clean_code/test_shart_jawab_relations_pilot_2_282.py` | New test file with the 11 SHART_JAWAB pilot tests (P1–P6, N1–N5) per §10.2. | **Required** |
| 5 | `clean_code/test_production_path_segmentation.py` | (a) Narrow existing guard `t_phase5_clause_segmenter_not_imported_by_production_path` to remove `relation_extractor.py` from `production_files`. (b) Extend `phase5_markers` regex to include bare `segment_clauses` (closes the leak). (c) Add positive guard `t_phase5_clause_segmenter_consumed_only_by_relation_extractor`. | **Required** (Batch B-specific guard refinement, NOT a relaxation) |

The implementation batch's `git diff --name-only` must be exactly this 5-file set. Any file outside this list rejects the batch (§13).

---

## 4. Forbidden files (binding)

The following files MUST NOT be modified. Any modification rejects the batch.

### 4.1 Phase 5 module (hard-forbidden)
- `clean_code/phase5_clause_segmenter.py` — READ-ONLY consumer of Batch A. Batch B uses its API, does not edit it.

### 4.2 Production modules that remain blocked from Phase 5 (hard-forbidden — guard stays in force)
- `clean_code/event_extractor.py` (future Batch C)
- `clean_code/resolution_engine.py` (future Batch D)
- `clean_code/reasoning_engine.py` (future Batch E)
- `clean_code/analyze_verse_v3.py` (orchestrator stays clean of Phase 5)
- `clean_code/samarrai_analyzer.py`
- `clean_code/samarrai_certified_operator_gate.py`
- `clean_code/hidden_pronoun_signals.py`
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/i3rab_engine/*` (entire subtree)

### 4.3 MAANI / MASAQ / schema (hard-forbidden)
- All MAANI CSVs under `clean_code/data/contracts/maani/**`
- All MASAQ files (any path containing "masaq")
- `clean_code/data/contracts/maani/schema.md`
- `clean_code/samarrai_quran_sweep.py` + all sweep output files

### 4.4 Other data / docs / tests (hard-forbidden)
- `data/contracts/**` outside `clean_code/data/contracts/rules/relation_types.csv`
- `data/MASAQ.csv`
- `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**`, `new_arabic_analyzer/**`, `archive/**`
- All other files under `docs/specs/` except this RULE_LOCK
- All other `test_*.py` files (Batch B touches only the new pilot test file and the targeted guard updates in `test_production_path_segmentation.py`)

### 4.5 No untracked artifacts left behind
- No `out_*.txt`
- No `.pyc` modifications committed
- No `.claude/` content committed
- No stash content reintroduced

---

## 5. Guard policy (binding)

### 5.1 The guard is narrowed, not deleted

The existing test `t_phase5_clause_segmenter_not_imported_by_production_path` at `test_production_path_segmentation.py:1771–1818` is MODIFIED (not removed) by Batch B. The two binding changes:

#### 5.1.1 Remove `relation_extractor.py` from `production_files`

Before:
```python
production_files = [
    here / "segmenter.py",
    ...
    here / "relation_extractor.py",        # ← REMOVE
    ...
    here / "analyze_verse_v3.py",
]
```

After: the 12 other entries remain; `relation_extractor.py` is removed (it is now an authorized consumer).

#### 5.1.2 Extend the regex to include bare `segment_clauses`

Before:
```python
phase5_markers = _re.compile(
    r"\b(phase5_clause_segmenter|Phase5Clause|Phase5ClauseGraph"
    r"|segment_clauses_from_surfaces|build_clause_graph)\b"
)
```

After:
```python
phase5_markers = _re.compile(
    r"\b(phase5_clause_segmenter|Phase5Clause|Phase5ClauseGraph"
    r"|segment_clauses_from_surfaces|segment_clauses|build_clause_graph)\b"
)
```

This closes the regex leak surfaced in Gate 2 (Investigation 1).

#### 5.1.3 Rename or document

The test docstring should be updated to reflect the allow-list semantics. The test name may remain unchanged or be renamed to `t_phase5_clause_segmenter_not_imported_by_non_b_production_modules`. RULE_LOCK does NOT mandate the rename; either is acceptable.

### 5.2 New positive guard test (required)

Add a new test to `test_production_path_segmentation.py`:

`t_phase5_clause_segmenter_consumed_only_by_relation_extractor`

This test:
1. Walks `clean_code/` for `*.py` files.
2. Excludes `phase5_clause_segmenter.py` itself, all `test_*.py` files, and anything under `__pycache__/`.
3. Asserts the ONLY remaining `.py` file matching `phase5_markers` is `relation_extractor.py`.

This catches accidental future imports in any module not currently in the negative-guard's blocked list. It is the positive counterpart to the negative guard.

### 5.3 Both guards must pass

Post-Batch-B, both the narrowed negative guard AND the new positive guard MUST pass:
- Negative guard: zero Phase 5 markers in the 12 still-blocked production modules.
- Positive guard: Phase 5 markers appear in exactly one production module (`relation_extractor.py`).

### 5.4 `meaning_assembler.py` stays blocked

Per the negative guard, `meaning_assembler.py` MUST NOT import Phase 5. The PASSTHROUGH extension consumes the new relation names as plain strings via the `RelationGraph` → `MeaningEdge` translation; no Phase 5 import is required.

---

## 6. Implementation lock (binding)

### 6.1 Phase 5 import surface

`relation_extractor.py` MUST import only:
```python
from phase5_clause_segmenter import Phase5Clause, segment_clauses_from_surfaces
```

It MUST NOT import:
- `segment_clauses` (the bare variant — even though the regex covers it, this rule is for code clarity)
- `build_clause_graph` (not needed for the pilot)
- `Phase5ClauseGraph` (not needed; clauses are iterated directly from the `segment_clauses_from_surfaces` return)

Additional imports of other Phase 5 internal symbols (e.g., `_p5_nfc`, `_p5_is_pause`) are explicitly **forbidden** — they are private helpers.

### 6.2 New pass location and signature

The new pass is added to the `RelationExtractor` class:

```python
def _pN_condition_jawab_from_phase5(self, g, sent, tokens) -> None:
    """Phase 5 Batch B: bridge Phase 5 condition/condition_answer
    clauses into L4 condition_tool_of and jawab_shart_of relations.
    Pilot scope: SHART_JAWAB first إِذَا construction in 2:282.
    Per RULE_LOCK PHASE5_BATCH_B... — block-and-skip when Phase 5
    output is absent or token-index reconciliation fails."""
    ...
```

It is invoked at exactly one location in `RelationExtractor.extract()` — immediately before the final `return g` statement at line 836:

```python
        # ── Phase 5 Batch B: condition/jawab relations bridged from Phase 5 ──
        self._pN_condition_jawab_from_phase5(g, sent, tokens)

        return g
```

The placeholder `_pN_` should be replaced by the next available phase number in the existing convention (Gate 2 confirmed `_p7_` and `_p12_` exist; implementer chooses the next free integer, e.g., `_p13_`). RULE_LOCK does not lock the integer.

### 6.3 Behavior of the new pass

Step-by-step required behavior:

1. **Get surfaces**: `surfaces = [getattr(t, "token", "") for t in tokens]` (or equivalent attribute that yields the verse's token surfaces in the same order as `tokens`).
2. **Get verse ref**: `verse_ref = getattr(sent, "verse_ref", "") or ""`.
3. **Call Phase 5**: `clauses = segment_clauses_from_surfaces(surfaces, verse_ref)`.
4. **Index clauses by `clause_id`**.
5. **Find pilot candidate clauses**: for each clause `c` with `c.type == "condition_answer_command"` AND `c.parent_clause_id` referencing a clause `parent` with `parent.type == "condition"`:
   - Locate the condition verb token: the FIIL token within `parent.start_token_index .. parent.end_token_index` (inclusive). The condition verb is typically the first FIIL inside the condition clause span.
   - Locate the jawab verb token: the FIIL token within `c.start_token_index .. c.end_token_index`.
   - Locate the condition tool token: the token at `parent.start_token_index` whose surface equals `parent.head_token` (i.e., `إِذَا` for the pilot).
6. **Index reconciliation check** (§6.5):
   - The condition tool token must satisfy: `tokens[parent.start_token_index].token == parent.head_token`.
   - The condition verb must be a FIIL within the parent's span.
   - The jawab verb must be a FIIL within `c`'s span and must have `فَ` as a prefix.
   - If any of these checks fail, **emit no edges** and return.
7. **Emit `condition_tool_of`**:
   - source = condition tool token idx
   - target = condition verb token idx
   - kind = `Certificate`
   - `source_of_claim` = `f"phase5:{parent.clause_id}.head={parent.head_token} + ConditionalScopeContract:{parent.confidence}"`
8. **Emit `jawab_shart_of`**:
   - source = jawab verb token idx
   - target = condition verb token idx
   - kind = `Certificate`
   - `source_of_claim` = `f"phase5:{c.clause_id}.parent={parent.clause_id} + introduced_by={c.introduced_by} + {c.source}"`
   - The `introduced_by={c.introduced_by}` substring is the MANDATORY فَ-marker evidence; tests assert it explicitly (P3).
9. **No other clause types are consumed**. Specifically:
   - `command`, `relative_shell`, `complement_an`, `prohibition`, `pause_boundary` clauses → ignored by this pass.

### 6.4 Forbidden fallback re-detection (binding)

If `clauses` is empty, OR if no `condition_answer_command` with a valid `parent_clause_id` is found, OR if §6.6 reconciliation fails:

- **The pass MUST emit zero edges and return.**
- The pass MUST NOT scan `tokens` for إِذَا / فَ patterns.
- The pass MUST NOT call any other detection function as a fallback.
- The pass MUST NOT raise an exception on Phase 5 returning empty (this is a legitimate state for verses without conditionals).

This behavior is asserted by test N4.

### 6.5 Token-index reconciliation (binding)

Phase 5 operates on whitespace-split surfaces. `RelationExtractor` operates on `sent.tokens`. RULE_LOCK requires:

| Check | If passes | If fails |
|---|---|---|
| `len(tokens) == len(surfaces)` (surface count equals token count after whitespace split) | proceed | emit no edges and return |
| `tokens[idx].token == surfaces[idx]` for the indices needed (condition tool, condition verb, jawab verb) | proceed | emit no edges and return |
| Phase 5's `parent.start_token_index` is in `[0, len(tokens))` | proceed | emit no edges and return |

If reconciliation fails, the implementation report must record the failure for future investigation. The pass does NOT attempt to recover via fuzzy matching or normalization.

### 6.6 Bounded behavior on the pilot construction (2:282)

For 2:282 first conditional, the pass MUST produce exactly 2 edges (Certificate × 2), no more, no less. Specifically:
- 1 × `condition_tool_of: إِذَا(idx 3) → تَدَايَنتُم(idx 4)`
- 1 × `jawab_shart_of: فَٱكْتُبُوهُ(idx 9) → تَدَايَنتُم(idx 4)`

For 2:282 second and third إِذَا (`إِذَا مَا دُعُوا۟`, `إِذَا تَبَايَعْتُمْ`), Phase 5 does NOT currently produce condition_answer_command pairs for them (Gate 2 SHART_JAWAB investigation confirmed). The pass MUST NOT emit edges for them.

For verses without `إِذَا … فَ` structure, the pass MUST emit zero edges.

---

## 7. Relation specifications (binding)

### 7.1 Locked edge details

#### Edge 1: `condition_tool_of`

| Field | Value |
|---|---|
| Relation name | `condition_tool_of` |
| Direction | `إِذَا → تَدَايَنتُم` (source = condition tool; target = condition verb) |
| Pilot example | source = token idx 3 (`إِذَا`); target = token idx 4 (`تَدَايَنتُم`) |
| ProofKind | **Certificate** |
| `source_of_claim` shape | `phase5:{condition_clause_id}.head={head_token} + ConditionalScopeContract:{confidence}` |
| `kind` (in `RelationGraph`) | `conditional` (matches `relation_types.csv` row) |

#### Edge 2: `jawab_shart_of`

| Field | Value |
|---|---|
| Relation name | `jawab_shart_of` |
| Direction | `فَٱكْتُبُوهُ → تَدَايَنتُم` (source = jawab verb; target = condition verb) |
| Pilot example | source = token idx 9 (`فَٱكْتُبُوهُ`); target = token idx 4 (`تَدَايَنتُم`) |
| ProofKind | **Certificate** |
| `source_of_claim` shape | `phase5:{jawab_clause_id}.parent={condition_clause_id} + introduced_by=فَ + {source}` — MUST literally contain the substring `introduced_by=فَ` (P3 asserts this) |
| `kind` (in `RelationGraph`) | `conditional` |

### 7.2 Locked `relation_types.csv` additions

Exactly 2 rows added (verbatim text per the user's approval):

```
18,condition_tool_of,conditional,أداة_شرط,FIIL,أداة الشرط تدل على فعل الشرط
19,jawab_shart_of,conditional,جواب_شرط,FIIL,جواب الشرط يرتبط بفعل الشرط
```

The `kind=conditional` value is a new open-set entry, matching the existing pattern. **Not a schema change.** The column order, header, and existing 17 rows are unchanged.

### 7.3 Explicitly REJECTED relation candidates

- `shart_event_of` — would be the inverse of `condition_tool_of` (تَدَايَنتُم → إِذَا direction); semantically redundant; the condition verb's role is recoverable as the target of `condition_tool_of`. **MUST NOT be added.**
- `jawab_marker_of` — would duplicate (`فَٱكْتُبُوهُ → تَدَايَنتُم`) direction with `jawab_shart_of`; فاء evidence is encoded inside `jawab_shart_of.source_of_claim`. **MUST NOT be added.**

If either is emitted by the implementation, the batch is rejected (§13).

---

## 8. MeaningGraph integration (binding)

### 8.1 PASSTHROUGH extension

In `clean_code/meaning_assembler.py`, the existing `PASSTHROUGH` set at lines 215–229 is extended by EXACTLY two entries:

```python
PASSTHROUGH = {
    "agent_of", "patient_of", "patient2_of",
    # ... existing 22 entries unchanged ...
    "vocative_of", "substitute_of", "coordinate_of",
    # Phase 5 Batch B — conditional structure
    "condition_tool_of", "jawab_shart_of",
}
```

The order of entries inside the set literal does not matter. The comment header is recommended but not required.

### 8.2 No Phase 5 import in meaning_assembler

`meaning_assembler.py` MUST NOT contain any reference to Phase 5 surface symbols. The new relation names flow through as plain string `r.name` values from `RelationGraph` to `MeaningEdge`. The post-Batch-B negative guard MUST flag any Phase 5 import in `meaning_assembler.py` as a violation.

### 8.3 L8 untouched

`reasoning_engine.py` (L8) is in the forbidden list (§4.2). L8 consumes L7 generically; the new typed edges are visible to L8 as `MeaningEdge(edge_type="condition_tool_of"|"jawab_shart_of", ...)`. Whether L8's existing answer logic surfaces the conditional dependency in `ما تَسَلسُل الأَحداث؟` text is a separate Batch E concern.

---

## 9. Expected post-implementation metrics for verse 2:282

| Metric | Pre-Batch-B baseline | Post-Batch-B expected |
|---|---|---|
| L7 nodes | 135 (52C + 83H) | **135 (unchanged)** — no new nodes |
| L7 links | 41 (14C + 27H) | **43 (16C + 27H)** — +2 Certificate edges |
| L7 coverage | 63.2% | 63.2% – 65% (slight uptick allowed; not locked to exact value) |
| L7 Entropy | 0.0 | **must remain 0.0** |
| L7 consistency | نَعَم ✓ | **must remain نَعَم** |
| L6 resolutions | 5 Zero (anaphora/relative) | **unchanged** — pilot adds no L6 edges |

Any other 2:282 metric drift rejects the batch (§13).

---

## 10. Tests required

### 10.1 Production-path guard updates (in `test_production_path_segmentation.py`)

| # | Test | Action |
|---|---|---|
| G1 (mutate existing) | `t_phase5_clause_segmenter_not_imported_by_production_path` (or renamed `..._by_non_b_production_modules`) | Remove `relation_extractor.py` from `production_files`; extend regex to include `segment_clauses`. The 12 other modules continue to be checked. |
| G2 (new) | `t_phase5_clause_segmenter_consumed_only_by_relation_extractor` | Walk `clean_code/*.py` (excluding `phase5_clause_segmenter.py`, all `test_*.py`, and `__pycache__/`). Assert the only `.py` matching `phase5_markers` is `relation_extractor.py`. |

**Test count impact**: if G2 is added as a new test, `test_production_path_segmentation.py` goes from 158 to **159**. The implementation report MUST declare the exact post-Batch-B test count. The batch is rejected if ANY existing test of `test_production_path_segmentation.py` regresses; ADDITION of G2 (taking the count to 159) is acceptable and expected.

### 10.2 SHART_JAWAB pilot tests (in `clean_code/test_shart_jawab_relations_pilot_2_282.py`)

| # | Test | Asserts |
|---|---|---|
| P1 | `t_2_282_first_idha_condition_tool_of_tadayantum` | L4 has `condition_tool_of: إِذَا(idx3) → تَدَايَنتُم(idx4)`, `proof_kind=Certificate` |
| P2 | `t_2_282_jawab_shart_of_faktubu_to_tadayantum` | L4 has `jawab_shart_of: فَٱكْتُبُوهُ(idx9) → تَدَايَنتُم(idx4)`, `proof_kind=Certificate` |
| P3 | `t_2_282_jawab_shart_source_of_claim_records_fa_marker` | The `jawab_shart_of` edge's `source_of_claim` contains the literal substring `introduced_by=فَ` |
| P4 | `t_2_282_l7_contains_condition_and_jawab_edges_as_typed` | L7 MeaningGraph has at least one edge with `edge_type="condition_tool_of"` and at least one with `edge_type="jawab_shart_of"`. Neither collapses to `operator_meaning` |
| P5 | `t_2_282_l7_entropy_remains_zero_and_consistent` | L7 Entropy == 0.0 AND consistency True (نَعَم) |
| P6 | `t_2_282_two_new_edges_are_both_certificate` | Both new edges have `proof_kind == "Certificate"` |
| N1 | `t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot` | No `condition_tool_of` edge sourced from the 2nd or 3rd إِذَا in 2:282 |
| N2 | `t_2_282_no_unrelated_fa_token_linked_to_first_idha` | No `jawab_shart_of` edge with `target=تَدَايَنتُم` and source other than `فَٱكْتُبُوهُ` |
| N3 | `t_2_282_no_condition_edge_for_other_tools` | No `condition_tool_of` source surface ∈ `{إِنْ, إِذْمَا, لَوْ, لَوْلَا, أَمَّا, مَنْ, أَيّ, أَيْنَ, أَيْنَمَا, كَيْفَمَا, مَتَى, حَيْثُمَا, أَنَّى, مَهْمَا, كُلَّمَا, مَا, لَمَّا}` |
| N4 | `t_implementation_blocked_if_phase5_unavailable` | Synthesized scenario where `segment_clauses_from_surfaces` returns `[]` — the pass emits 0 edges (no fallback re-detection) |
| N5 | `t_no_relation_when_no_fa_jawab_in_phase5_output` | Synthesized scenario where Phase 5 returns a `condition` clause but no `condition_answer_command` — pass emits 0 edges |

### 10.3 Cross-suite regression (must remain green at current baselines)

- `clean_code/test_production_path_segmentation.py` — must remain at **158/158** (if G1 mutated in place) or **159/159** (if G2 added). No regression.
- `clean_code/test_maani_batch_b_author_position.py` — must remain **6/6**.
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — must remain **20/20**.
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain at its current count.

Any suite regressing rejects the batch.

---

## 11. Schema and ProofKind locks

### 11.1 Schema
- `relation_types.csv` schema (`priority,name,kind,role_source,role_target,note`) — unchanged. Header unchanged. Column order unchanged.
- `kind=conditional` is a new open-set value, NOT a schema change.
- MAANI 19-column schema unchanged.
- No new columns anywhere.

### 11.2 ProofKind
- Enum `{Certificate, Hypothesis, Zero}` — unchanged.
- Both new edges emit ONLY `Certificate` (per §6.3 — block-and-skip when criteria not met; no Hypothesis fallback).
- Batch B monotonicity (no Certificate → Hypothesis upgrades anywhere) preserved.
- No code path added that upgrades any other ProofKind.

---

## 12. Acceptance criteria

The implementation batch is **acceptable** if and only if **all** of the following hold:

1. Exactly 5 files modified, matching §3 cell-for-cell.
2. `phase5_clause_segmenter.py` is bit-for-bit unchanged.
3. `relation_extractor.py` imports ONLY `Phase5Clause` and `segment_clauses_from_surfaces` from Phase 5.
4. `meaning_assembler.py` contains zero Phase 5 surface references (negative guard G1 passes).
5. The positive guard G2 confirms `relation_extractor.py` is the ONLY production module importing Phase 5.
6. The negative guard G1 confirms the 12 still-blocked modules contain zero Phase 5 references.
7. `relation_types.csv` has exactly 2 new rows (priorities 18, 19) matching §7.2 text verbatim.
8. `meaning_assembler.py` PASSTHROUGH set has exactly 2 new entries: `condition_tool_of` and `jawab_shart_of`.
9. 2:282 produces exactly 2 new edges per §6.6, both Certificate.
10. SHART_JAWAB pilot tests P1–P6 + N1–N5 all pass.
11. `test_production_path_segmentation.py` passes at 158 (G1 mutation only) or 159 (G2 added). No regression.
12. Cross-suite regression (§10.3) all green.
13. 2:282 L7 nodes unchanged at 135 (§9).
14. 2:282 L7 links increases by exactly +2 (41 → 43).
15. 2:282 L7 Entropy remains 0.0; consistency remains نَعَم.
16. No file outside §3 modified.
17. No file in §4 modified.
18. No untracked artifacts (`.pyc`, `out_*.txt`, `.claude/`) committed.
19. The `phase5_markers` regex includes `segment_clauses` (closes the Gate-2 leak).
20. A batch report at `docs/specs/PHASE5_BATCH_B_RELATION_CLAUSE_WIRING_REPORT.md` is produced (separately committed under separate approval).

If any of the 20 conditions fails, the batch is **rejected** (§13).

---

## 13. Rejection criteria

The implementation batch is **rejected** if any of the following occurs:

| Trigger | Reason |
|---|---|
| `phase5_clause_segmenter.py` modified | §4.1 violated. |
| Any forbidden file in §4 modified | Forbidden-files lock violated. |
| Any production module other than `relation_extractor.py` imports Phase 5 | G1 or G2 fails. |
| `meaning_assembler.py` imports Phase 5 | §4.2 / §8.2 violated. |
| `analyze_verse_v3.py` imports Phase 5 | §4.2 violated. |
| Either new edge emits with `proof_kind` other than Certificate (or fails to emit) | §6.3 / §7.1 violated. |
| More than 2 condition/jawab edges per pilot construction | §6.6 violated. |
| `shart_event_of` or `jawab_marker_of` emitted as a separate edge | §7.3 violated. |
| Manual token-scanning fallback added to `_pN_condition_jawab_from_phase5` | §6.4 violated (test N4 fails). |
| Index reconciliation skipped or replaced with fuzzy matching | §6.5 violated. |
| A condition relation emitted for any tool other than إِذَا | Scope lock §6.6 violated (test N3 fails). |
| A condition relation emitted for the 2nd or 3rd إِذَا in 2:282 | Scope lock §6.6 violated (test N1 fails). |
| A condition relation emitted for any verse other than 2:282 with valid Phase 5 evidence | Out of pilot scope (note: Phase 5 may correctly produce condition/answer pairs for other verses; those edges ARE permitted if Phase 5 supports them — see §13.1 below) |
| Any new ProofKind value introduced | §11.2 violated. |
| Any ProofKind upgrade code path added | Batch B monotonicity violated. |
| `kind=conditional` used for any row in `relation_types.csv` besides the 2 new ones | §7.2 violated. |
| Schema change (column rename/add/reorder) | §11.1 violated. |
| `phase5_markers` regex does NOT include `segment_clauses` | §5.1.2 violated (leak still open). |
| The narrowed negative guard G1 still includes `relation_extractor.py` in `production_files` | §5.1.1 not done. |
| The new positive guard G2 is missing | §5.2 violated. |
| 2:282 L7 Entropy != 0.0 post-implementation | §9 / test P5 violated. |
| 2:282 L7 consistency != نَعَم post-implementation | §9 / test P5 violated. |
| 2:282 L7 link count delta != +2 | §9 violated. |
| `test_production_path_segmentation.py` ANY existing test regresses (other than G1's mutation) | Cross-suite §10.3 violated. |
| Any other test suite (Batch B / C2 / Phase 4) regresses | §10.3 violated. |
| Untracked artifacts left in committed tree | Hygiene §4.5 violated. |
| Unsafe L6 link introduced (new anaphora/relative resolution) | Out of pilot scope. |
| Phase 5 module's public API changed | §4.1 violated (we don't edit Phase 5 to change its API). |

Rejection is total — partial acceptance is not permitted.

### 13.1 Clarification on non-2:282 verses

For verses other than 2:282 that happen to contain `إِذَا ... فَ` structures detected by Phase 5: the pass MAY emit edges for them (Phase 5 is the source of truth, and if it detects them, they are legitimate). The pilot is **scoped to test on 2:282** but the pass is **general-purpose** — it processes any verse for which Phase 5 produces a `condition_answer_command` clause. This is consistent with the Phase 5 Batch B framing (Batch B = wire Phase 5 into L4 generally; 2:282 is the verified test case). What the pilot does NOT do is:
- Manually scan for إِذَا in verses where Phase 5 didn't detect a condition (forbidden — §6.4).
- Handle other conditional tools (Phase 5 must produce the structure; if Phase 5 expands later, the pass benefits automatically).

This clarification is binding: emitting an edge for a non-2:282 verse where Phase 5 legitimately produced the structure is NOT a rejection trigger. Test N3 only asserts: no source surface is one of the OTHER conditional tools (إِنْ / لَوْ / etc.) for the 2:282 verse specifically. Outside 2:282, the behavior is governed by whatever Phase 5 produces.

---

## 14. Rollback

If the batch is rejected per §13 or fails review after the implementation commit:

1. **Standard `git revert`** of the implementation commit. The revert restores:
   - `relation_extractor.py` to its pre-Batch-B state.
   - `meaning_assembler.py` PASSTHROUGH to its pre-Batch-B state.
   - `relation_types.csv` to its 17-row state.
   - The original blanket guard test in `test_production_path_segmentation.py` (with `relation_extractor.py` back in the production_files list and regex without `segment_clauses`).
   - Deletes `clean_code/test_shart_jawab_relations_pilot_2_282.py`.
2. **No force-push.** No `git reset --hard` on shared branches.
3. **Phase 5 Batch A isolation guard returns to blanket-block form** on revert.
4. **No data outside this batch is touched** in the rollback. MAANI, MASAQ, Phase 4 commits remain intact. The SHART_JAWAB pilot's SPEC `cd83d7f` and RULE_LOCK `7b77945` remain in history unchanged.
5. **Working tree post-revert** matches whatever commit was HEAD before this batch's implementation commit.

---

## 15. Source traceability

Every edge emitted by this batch traces to a specific Phase 5 clause in `phase5_clause_segmenter.py`'s output. NO edge derives from bespoke detection logic in `relation_extractor.py`.

| Emitted edge | Phase 5 evidence |
|---|---|
| `condition_tool_of: إِذَا → تَدَايَنتُم` (Certificate, 2:282) | Phase 5 clause `C002`: `type=condition`, `head_token=إِذَا`, `start_token_index=3`, `source=ConditionalScopeContract`, `confidence=Certificate`. |
| `jawab_shart_of: فَٱكْتُبُوهُ → تَدَايَنتُم` (Certificate, 2:282) | Phase 5 clause `C003`: `type=condition_answer_command`, `head_token=فَٱكْتُبُوهُ`, `start_token_index=9`, `parent_clause_id=C002`, `introduced_by=فَ`, `source=ImperativeFormContract+ConditionAnswerLinker`. |

Any edge content not traceable to Phase 5 clauses is **not admissible** in this batch.

---

## 16. Governance

### 16.1 Approval gates (sequential; each requires separate explicit approval)

1. **SPEC approval** — `docs/specs/PHASE5_BATCH_B_RELATION_CLAUSE_WIRING_SPEC_DRAFT.md`. ✅ Complete at commit `e6d4308`.
2. **Gate-2 read-only investigations**. ✅ Complete 2026-05-31; findings embedded in §0.
3. **RULE_LOCK approval** — this document. *Pending review at time of writing.*
4. **Implementation approval** — separate explicit approval before any file under §3 is touched.
5. **Test approval** — after implementation, test results reported back to user.
6. **Commit approval** — user approves the specific commit hash for the implementation.
7. **Report approval** — `docs/specs/PHASE5_BATCH_B_RELATION_CLAUSE_WIRING_REPORT.md` written and committed under separate approval after the implementation commit lands.

Skipping any gate rejects the batch.

### 16.2 What is NEVER allowed inside this batch
- Modifying `phase5_clause_segmenter.py` (§4.1).
- Importing Phase 5 from any production module other than `relation_extractor.py` (§5).
- Emitting `shart_event_of` or `jawab_marker_of` (§7.3).
- Adding a fallback re-detection inside `relation_extractor.py` (§6.4).
- Skipping the token-index reconciliation (§6.5).
- Schema changes to `relation_types.csv` columns (§11.1).
- ProofKind enum changes (§11.2).
- Touching any file in §4 (no conditional-lift clause).
- Modifying any committed historical artifact (SPEC `e6d4308`, SHART_JAWAB SPEC `cd83d7f`, SHART_JAWAB RULE_LOCK `7b77945`, Phase 5 Batch A commit `e357ae5`, Phase 5 SPEC).
- Adding any new conditional tool detection (إِنْ / لَوْ / مَنْ / ما / etc.) — Phase 5 itself must extend before any new tool is exposed.

### 16.3 What requires a new RULE_LOCK (NOT this one)
- Phase 5 Batch C (`event_extractor.py` consumption) — separate batch.
- Phase 5 Batch D (`resolution_engine.py` consumption) — separate batch.
- Phase 5 Batch E (`reasoning_engine.py` consumption) — separate batch.
- Direct Phase 5 import in `meaning_assembler.py` — separate batch.
- Direct Phase 5 import in `analyze_verse_v3.py` — separate batch.
- Phase 5 module API changes (adding/removing exports) — Phase 5 module governance, not Batch B.
- Adding a new clause type to Phase 5's detector (e.g., conditionals without فاء) — Phase 5 module governance.
- Expansion of conditional tools beyond what Phase 5 produces — Phase 5 module governance.

### 16.4 Relationship to SHART_JAWAB pilot

The SHART_JAWAB pilot SPEC `cd83d7f` and RULE_LOCK `7b77945` are NOT amended or deleted by this batch. The SHART_JAWAB edge design (2 edges, both Certificate, anchored on the condition verb) is carried forward verbatim into Batch B's §7.

The SHART_JAWAB RULE_LOCK `7b77945` is **superseded for implementation only** by this RULE_LOCK, in the narrow sense that:
- This RULE_LOCK authorizes the Phase 5 import that `7b77945` could not.
- This RULE_LOCK authorizes the guard narrowing that `7b77945` could not.

The SHART_JAWAB pilot's locked design is unchanged. After Batch B ships, the SHART_JAWAB implementation is no longer blocked. The SHART_JAWAB pilot's governance chain (Gates 1, 2, 3 ✅ → Gates 4, 5, 6, 7 still pending) effectively folds into this Batch B chain: a single implementation commit closes both.

### 16.5 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. `git log --oneline -20` — confirm no in-flight commits on Phase 5, MAANI, or MASAQ files since this RULE_LOCK.
2. `git status` — confirm working tree is clean except `.claude/`.
3. `git stash list` — confirm no untracked WIP exists.

If any concurrent activity is found, postpone implementation until that activity completes.

---

## 17. Risks

### 17.1 Token-index mismatch
Phase 5 uses whitespace-split surface indices. `RelationExtractor.extract()` uses `sent.tokens` indices. If these differ (e.g., segmenter splits some surfaces further or merges others), the pass's reconciliation check (§6.5) will fail and emit no edges. Mitigation: §6.5 mandates explicit reconciliation; failure is silent skip, not crash.

### 17.2 Phase 5 API evolution risk
After Batch B ships, `relation_extractor.py` depends on Phase 5's public API (`Phase5Clause`, `segment_clauses_from_surfaces`). Changes to Phase 5's API become production-breaking. Mitigation: Phase 5 module is owned by Phase 5 governance; changes there require their own approval gates that consider downstream consumers.

### 17.3 Guard regex completeness
The extended regex covers all five current Phase 5 exports. If Phase 5 adds a new exported function in the future, the regex must be updated to cover it. Mitigation: the positive guard G2 walks all `.py` files and matches the regex; if Phase 5 adds an export and a production module imports it, G2 still catches the leak via the existing regex IF the new symbol's name is similar to existing ones, OR can be updated easily.

### 17.4 Test count drift
Adding G2 takes `test_production_path_segmentation.py` from 158 to 159. The implementation report must declare which path was taken (G1 mutation only = 158; G1 + G2 = 159). Cross-suite regression baselines update accordingly.

### 17.5 Sequencing with SHART_JAWAB
The SHART_JAWAB pilot's RULE_LOCK `7b77945` is currently in history as a blocked artifact. Some users may inspect the chain and be confused about which RULE_LOCK governs implementation. Mitigation: this Batch B RULE_LOCK §16.4 explicitly addresses the supersedence relationship.

### 17.6 Coverage uptick variability
Post-Batch-B, 2:282 L7 coverage may increase from 63.2% to anywhere between 63.2% and ~65% depending on whether the new edges' endpoint nodes were previously counted as participating. RULE_LOCK does not lock coverage to an exact value (§9). The implementation report should record the exact post-impl coverage.

---

## 18. One-screen recap

| Item | Value |
|---|---|
| Batch | Phase 5 Batch B — Relation/Clause Wiring |
| Type | Narrow production wiring of Phase 5 into one consumer (`relation_extractor.py`) |
| Source of truth | `clean_code/phase5_clause_segmenter.py` (READ-ONLY) |
| Inaugural use case | SHART_JAWAB first إِذَا in 2:282; design carried verbatim from RULE_LOCK `7b77945` §3 |
| Sole authorized importer (new) | `clean_code/relation_extractor.py` |
| Guard policy | Narrowed, NOT deleted; regex extended to include `segment_clauses` (closes Gate-2 leak); new positive guard G2 added |
| Allowed files | **5**: `relation_extractor.py`, `meaning_assembler.py`, `relation_types.csv`, new test file, `test_production_path_segmentation.py` (guard updates) |
| Forbidden | Phase 5 module + 12 other production modules + MAANI + MASAQ + schema + all other tests + sweep |
| New relations | **2**: `condition_tool_of` (Certificate, إِذَا → تَدَايَنتُم) + `jawab_shart_of` (Certificate, فَٱكْتُبُوهُ → تَدَايَنتُم with `source_of_claim` containing `introduced_by=فَ`) |
| Explicitly REJECTED relations | `shart_event_of` (redundant inverse), `jawab_marker_of` (duplicate direction) |
| `relation_types.csv` change | +2 rows at priorities 18, 19 with `kind=conditional` (open-set value; not schema change) |
| `meaning_assembler.py` change | PASSTHROUGH +2 entries; NO Phase 5 import |
| Expected 2:282 metrics | nodes 135→135; links 41→43 (+2 Certificate); Entropy 0.0; consistency نَعَم |
| Tests | 2 guard (G1 mutation + G2 new) + 11 pilot (P1–P6 + N1–N5) + cross-suite regression (158 or 159 / 6 / 20 / Phase 4) |
| Schema changes | None |
| ProofKind enum | Unchanged |
| ProofKind discipline | Certificate-only for the 2 new edges; no Hypothesis fallback; no Zero edge |
| Rollback | `git revert`; restores blanket guard; Phase 5 module untouched throughout |
| Governance | 7 gates; 3 complete (SPEC, Gate 2, this RULE_LOCK pending approval); 4 remaining |
| Relationship to SHART_JAWAB pilot | RULE_LOCK `7b77945` superseded for implementation only (authorizes the Phase 5 import); design preserved verbatim |
