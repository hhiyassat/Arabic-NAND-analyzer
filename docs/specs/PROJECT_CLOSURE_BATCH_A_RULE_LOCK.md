# Project Closure — Closure Batch A — L8 SHART_JAWAB Consumption — RULE_LOCK

> **Type:** RULE_LOCK (binding contract).
> **Date:** 2026-06-01
> **SPEC parent:** `docs/specs/PROJECT_CLOSURE_SPEC_DRAFT.md` (commit `1ca6306`).
> **Reference docs:** `docs/specs/WHERE_WE_ARE.md` (commit `3ad474c`).
> **Inherits Phase 5 Batch B edges from:** commit `236a885` (the L4/L7 condition/jawab structure).
> **Status:** Binding. Any violation rejects the batch.

Once approved, the boundaries below cannot be widened inside this batch. Any widening requires a new RULE_LOCK and a new batch.

---

## 0. Gate 2 findings (embedded preamble)

This RULE_LOCK is grounded in the read-only investigations completed on 2026-06-01 prior to drafting.

| # | Investigation | Finding |
|---|---|---|
| 1 | Baseline | HEAD = `1ca6306` on `main`. 2:282 L4 has `condition_tool_of` + `jawab_shart_of` (both Certificate). L7: 135 nodes, 43 links (16C + 27H), Entropy 0.0, consistency نَعَم. L8 currently asks 7 questions; **`ما جواب الشرط؟` is NOT among them.** |
| 2 | L8 ownership | `clean_code/reasoning_engine.py` owns question parsing + strategy dispatch via `class ReasoningEngine` (line 120), `answer(text, question)` (line 211), and `strategy_map` (line ~218). Strategies iterate `graph.edges` from `MeaningAssembler.assemble(text)`. |
| 3 | L8 rendering | `clean_code/analyze_verse_v3.show_reasoning_interactive(text)` (line 316) iterates a **hardcoded** question list at line 327 and calls `eng.answer(text, q)` per question. To surface a new question, this list must be edited. |
| 4 | Question routing | Data-driven via `clean_code/data/contracts/rules/query_types.csv` (30 rows). Triggers map to `query_type` + `answer_strategy`. New question requires a new CSV row pointing to a new strategy. |
| 5 | Edge accessibility | `MeaningGraph.edges` is fully accessible to `ReasoningEngine` strategies. Phase 5 Batch B edges (`condition_tool_of`, `jawab_shart_of`) flow through the existing `meaning_assembler` PASSTHROUGH whitelist with `edge_type`, `source`, `target`, `proof_kind`, `operator`, `source_of_claim` intact. **No new extraction is required.** |
| 6 | Phase 5 isolation | `reasoning_engine.py` is in the production-path Phase 5 isolation guard's blocked list. Batch A does **NOT** add a Phase 5 import to `reasoning_engine.py`; it reads `MeaningGraph` edges only. The guard stays in force; no guard-update needed. |
| 7 | Test runner | Test suites are stand-alone Python files; no central runner registration needed. New test file is invoked directly. |

Any drift from these findings between approval and implementation requires re-investigation, not silent adaptation.

---

## 1. Batch identity

| Field | Value |
|---|---|
| Batch name | **PROJECT_CLOSURE_BATCH_A_L8_SHART_JAWAB_CONSUMPTION** |
| Parent SPEC | `docs/specs/PROJECT_CLOSURE_SPEC_DRAFT.md` (commit `1ca6306`) |
| Type | L8 question/answer extension (consumes existing L4/L7 edges; no L4/L7 changes) |
| Source-of-truth | The existing `condition_tool_of` and `jawab_shart_of` edges in the MeaningGraph (produced by Phase 5 Batch B at `236a885`) |
| Inaugural use case | Verse 2:282, first إِذَا construction (carries forward from SHART_JAWAB pilot `7b77945` / Phase 5 Batch B `eb7720c`) |

---

## 2. Source-of-truth lock (binding)

| Constraint | Statement |
|---|---|
| L8 source of truth | `MeaningGraph.edges` produced by the existing pipeline (no new graph mutation, no new extraction). |
| Forbidden L4 mutation | The new strategy MUST NOT add, remove, or modify any edge in the graph. Read-only consumption. |
| Forbidden detection | The new strategy MUST NOT scan tokens for إِذَا / فَ patterns. No fallback. |
| Forbidden Phase 5 call | The new strategy MUST NOT import or call any Phase 5 module symbol directly. |
| Required block-and-skip | If no `jawab_shart_of` edge exists in the graph, return `Zero`. No Hypothesis fallback. |
| Required Certificate-only | If the `jawab_shart_of` edge is `Hypothesis` (e.g., from a future degraded path), return `Zero` rather than emit Hypothesis. **Certificate-or-Zero only.** |

---

## 3. Allowed implementation files (exactly 4)

The implementation batch may touch ONLY these paths:

| # | Path | Purpose | Required / Conditional |
|---|---|---|---|
| 1 | `clean_code/reasoning_engine.py` | Add new strategy method `_find_jawab_shart(query, graph, question) → Answer`. Register it in `strategy_map` (line ~218) under key `"find_jawab_shart"`. No other change. | **Required** |
| 2 | `clean_code/data/contracts/rules/query_types.csv` | Add **exactly 2 new rows** at priorities 31, 32 mapping `جَواب_الشَّرط` (vocalized) and `جواب_الشرط` (plain) → `query_type=conditional_answer` → `answer_strategy=find_jawab_shart`, `in_scope=true`. | **Required** |
| 3 | `clean_code/analyze_verse_v3.py` | Add the string `"ما جَواب الشَّرط؟"` to the hardcoded `questions` list at line ~327 of `show_reasoning_interactive`. Add exactly **one** new `elif` branch to the per-question explanation chain (lines ~356–378) describing the answer's structural meaning. No other change. | **Required** (Gate 2 §3 confirms the question list is hardcoded) |
| 4 | `clean_code/test_project_closure_batch_a_l8_shart_jawab.py` | **New test file** containing the 8 locked tests in §10. | **Required** |

The implementation batch's `git diff --name-only` must be **exactly this 4-file set, no more and no less**. Any file outside this list rejects the batch (§13).

### 3.1 Note on `data/*` interpretation

The user's forbidden list mentions "all data/*". This is interpreted as the **project-root `data/` directory** (e.g., `data/MASAQ.csv`, `data/quran-uthmani-with-pause-mark.txt`). The path `clean_code/data/contracts/rules/query_types.csv` is **inside `clean_code/`** and is explicitly allowed per §3 row 2 (Gate 2 §4 confirmed the question routing is data-driven via this CSV; without the row, the dispatch never reaches the new strategy).

---

## 4. Forbidden files (binding)

The following files MUST NOT be modified. Any modification rejects the batch.

### 4.1 L4/L7 surface (hard-forbidden — Batch A does NOT touch extraction)
- `clean_code/relation_extractor.py`
- `clean_code/meaning_assembler.py`
- `clean_code/phase5_clause_segmenter.py` (Phase 5 module remains untouched)

### 4.2 Other production layers (hard-forbidden)
- `clean_code/event_extractor.py`
- `clean_code/resolution_engine.py`
- `clean_code/i3rab_engine/*` (entire subtree)
- `clean_code/segmenter.py`
- `clean_code/normalizer.py`
- `clean_code/master_token_lookup.py`
- `clean_code/role_rules_contract.py`
- `clean_code/samarrai_analyzer.py`
- `clean_code/samarrai_certified_operator_gate.py`
- `clean_code/hidden_pronoun_signals.py`

### 4.3 Phase 5 isolation guard (hard-forbidden)
- `clean_code/test_production_path_segmentation.py` — Batch A does NOT change the Phase 5 isolation guard. `reasoning_engine.py` remains blocked from Phase 5 imports. Gate 2 §6 confirmed Batch A does not need any guard update.

### 4.4 MAANI / MASAQ / schema (hard-forbidden)
- All MAANI CSVs under `clean_code/data/contracts/maani/**`
- All MASAQ files (any path containing "masaq")
- `clean_code/data/contracts/maani/schema.md`
- `clean_code/samarrai_quran_sweep.py` + all sweep output files

### 4.5 Other data / docs / tests (hard-forbidden)
- `data/contracts/**` (top-level — project-root data directory)
- `data/MASAQ.csv`, `data/quran-uthmani-with-pause-mark.txt`
- `maani_alnahw/**`, `new_arabic_analyzer/**`, `archive/**`
- All other files under `docs/specs/` except this RULE_LOCK now (and the eventual Closure Batch A report under separate approval)
- `docs/specs/WHERE_WE_ARE.md` — **not** edited by Batch A (WHERE_WE_ARE update is reserved for the final closure report under §16.3)
- All other `test_*.py` files (no extensions to existing test files)

### 4.6 No untracked artifacts left behind
- No `out_*.txt`
- No `.pyc` modifications committed
- No `.claude/` content committed
- No stash content reintroduced

---

## 5. Implementation lock (binding)

### 5.1 The new strategy

A new method on `ReasoningEngine`:

```python
def _find_jawab_shart(self, query, graph, question) -> Answer:
    """Find the jawab of the conditional from existing L4/L7 edges
    (jawab_shart_of). Pure consumption; no detection."""
    # implementation body
```

Behavior step-by-step (binding):

1. Iterate `graph.edges`, collect every edge where `edge_type == "jawab_shart_of"`.
2. If no such edge: return `Answer(kind="Zero", ..., rejected_reason="لا جواب شرط مَكشوف في شَبَكَة المَعنى.")`.
3. Pick the highest-evidence edge: prefer one with `proof_kind == "Certificate"`. If none is Certificate: return `Zero` (Certificate-or-Zero per §2).
4. Resolve `jawab_node = graph.get_node(edge.source)` and `cond_node = graph.get_node(edge.target)`.
5. If either node is missing: return `Zero`.
6. Look up the matching `condition_tool_of` edge (same `target` node): collect it for `أداة الشرط` evidence. If not present, the answer still emits (the jawab is the primary fact), but the tool phrase is omitted.
7. Compose answer text **strictly factual, NO interpretation**:
   - Required substring: `جَواب الشَّرط`
   - Required substring: `فَٱكْتُبُوهُ` (in the 2:282 case — actually the value of `jawab_node.surface`; tests assert it equals `فَٱكْتُبُوهُ` for 2:282)
   - Required substring: `تَدَايَنتُم` (the value of `cond_node.surface` for 2:282)
   - Optional: `أداة الشرط: إِذَا` if `condition_tool_of` edge accessible
   - Optional: `فاء الجَواب فَ` if `edge.operator == "فَ"`
8. Return `Answer(kind="Certificate", answer=<text>, contract=self.CONTRACT_ANSWER)`.

### 5.2 Strategy registration

In `ReasoningEngine.answer()` at the existing `strategy_map` (line ~218), add exactly one entry:

```python
strategy_map = {
    # ... existing 13 entries ...
    "find_jawab_shart": self._find_jawab_shart,
}
```

No other change to `answer()` or its surrounding methods.

### 5.3 `query_types.csv` additions (exactly 2 rows, verbatim)

```
31,جَواب_الشَّرط,conditional_answer,true,find_jawab_shart,جَواب الشَّرط — يَستَهلِك الحافَة jawab_shart_of المَوجودَة
32,جواب_الشرط,conditional_answer,true,find_jawab_shart,جواب الشرط — تَطبيع بِلا تَشكيل
```

- `kind` column / new value: `query_type=conditional_answer`. The `query_type` column is open-set (existing values include `who`, `what`, `when`, `where`, `how`, `interpretation`, `judgment`, etc.). Adding `conditional_answer` matches the existing pattern. **Not a schema change.**
- `in_scope=true` and `answer_strategy=find_jawab_shart` are bound.
- The 2-row pair handles vocalized vs. plain trigger matching (consistent with the existing pairs at rows 4–5 / 6–8 / etc.).

### 5.4 `analyze_verse_v3.py` additions

In `show_reasoning_interactive(text)`:

1. Add the string `"ما جَواب الشَّرط؟"` to the `questions` list (line ~327). Recommended placement: between `"ما تَسَلسُل الأَحداث؟"` and `"إلى ماذا تَحَوَّلَ شَيء؟"` (groups conditional question near the sequence question).

2. Add exactly one new `elif` branch to the explanation chain (lines ~356–378), e.g.:
   ```python
   elif "جَواب" in _q or "جواب" in _q:
       if a.kind == "Certificate":
           _explain("استُخرِج جَواب الشَّرط مِن حافَة jawab_shart_of في L4؛ "
                    "هذا تَركيب نَحوي وَ ليس تَفسيرًا.")
       elif a.kind == "Zero":
           _explain("لا تُوجَد حافَة jawab_shart_of آمِنَة في شَبَكَة المَعنى؛ "
                    "النِّظام يُفَضِّل عَدَم اختِلاق جَواب.")
   ```

**No other change to `analyze_verse_v3.py`.** No edits to `argparse`, `main()`, `show_*()` other functions, or any other part of the file.

### 5.5 Question canonicalization (binding)

The canonical accepted question string is **exactly**:

```
ما جَواب الشَّرط؟
```

The `query_types.csv` triggers also accept normalized variants via the existing normalization (`جواب الشرط` without tashkeel). **The batch does NOT accept arbitrary paraphrases** (e.g., `ما هو جواب الشرط؟`, `أين جواب الشرط؟`, `ماذا يَجِب لِلشرط؟`) in this closure batch. Paraphrase coverage is deferred — and out of scope for closure entirely (would be a follow-up batch under fresh SPEC if ever needed).

### 5.6 Forbidden behaviors

The new strategy MUST NOT:
- Mutate `graph.edges` or `graph.nodes`.
- Iterate `sent.tokens` directly.
- Scan for إِذَا / فَ surface patterns.
- Import `phase5_clause_segmenter`, `Phase5Clause`, `Phase5ClauseGraph`, `segment_clauses_from_surfaces`, `segment_clauses`, or `build_clause_graph`.
- Call `RelationExtractor` directly (the strategy receives `graph`, not `sent`).
- Return `Hypothesis` proof_kind. Output is `Certificate` (when edge is Certificate) or `Zero` (any other case).
- Include any interpretive phrasing (tafsir / fiqh / scholarly opinion / fatwa). Strict factual phrasing only.
- Hardcode 2:282-specific surfaces (`إِذَا`, `تَدَايَنتُم`, `فَٱكْتُبُوهُ`) in the answer text. Use the `node.surface` values from the edge endpoints, which makes the strategy edge-driven (works on any verse where Phase 5 produces matching clauses).

---

## 6. Schema / ProofKind locks

### 6.1 Schema
- `query_types.csv` schema (`priority,trigger_word,query_type,in_scope,answer_strategy,description`) unchanged. Header unchanged. Column order unchanged.
- `query_type=conditional_answer` is a new open-set value. **Not a schema change.**
- No other schema change anywhere.

### 6.2 ProofKind
- `{Certificate, Hypothesis, Zero}` unchanged.
- Strategy emits ONLY `Certificate` or `Zero` (§5.1 step 3).
- Batch B monotonicity preserved.
- No code path that upgrades any other ProofKind.

---

## 7. Expected post-implementation metrics for verse 2:282

| Metric | Before (HEAD `1ca6306`) | After Batch A | Lock |
|---|---|---|---|
| **L4 condition_tool_of** | present (Certificate) | unchanged | ✅ Batch A reads only |
| **L4 jawab_shart_of** | present (Certificate) | unchanged | ✅ Batch A reads only |
| **L7 nodes** | 135 (52C + 83H) | **135 (unchanged)** | ✅ |
| **L7 links** | 43 (16C + 27H) | **43 (unchanged)** | ✅ no new edges |
| **L7 Entropy** | 0.0 | **0.0** | ✅ must remain |
| **L7 consistency** | نَعَم | **نَعَم** | ✅ must remain |
| **L8 questions count** | 7 | **8 (+1 for جواب الشرط)** | ✅ |
| **L8 answer for `ما جواب الشرط؟`** | (question not asked) | **Certificate** with `فَٱكْتُبُوهُ` linked to `تَدَايَنتُم` | ✅ |
| **L8 answer for other questions** | unchanged | unchanged | ✅ no regression |

Any L4/L7 metric drift rejects the batch (§13).

---

## 8. Question handling (binding)

| Canonical query | Accepted | Notes |
|---|---|---|
| `ما جَواب الشَّرط؟` | ✅ | Primary canonical form |
| `ما جواب الشرط؟` (no tashkeel) | ✅ | Matched via `_normalize` in `_load_query_types` |
| `جَواب الشَّرط؟` (no leading ما) | ❌ | Not in pilot scope; would require additional CSV row — deferred. |
| `ما هو جواب الشرط؟` | ❌ | Paraphrase out of scope — deferred. |
| `أين جواب الشرط؟` | ❌ | Paraphrase out of scope — deferred. |
| All other variants | ❌ | Out of scope. |

---

## 9. Tests required (binding)

The implementation batch MUST add **all** of the following tests to `clean_code/test_project_closure_batch_a_l8_shart_jawab.py`. Missing any rejects the batch.

### 9.1 Positive tests (binding pilot assertions)

| # | Test | Asserts |
|---|---|---|
| P1 | `t_l8_answers_jawab_shart_for_2_282` | `ReasoningEngine().answer(_2_282_TEXT, "ما جَواب الشَّرط؟")` returns an `Answer` with non-empty `answer` text. |
| P2 | `t_l8_jawab_shart_answer_contains_faktubu` | The answer text contains the substring `فَٱكْتُبُوهُ`. |
| P3 | `t_l8_jawab_shart_links_faktubu_to_tadayantum` | The answer text contains the substring `تَدَايَنتُم` AND the linkage phrasing (`مَربوط` or `بِفِعل الشَّرط` or equivalent locked phrase). |
| P4 | `t_l8_jawab_shart_answer_is_certificate` | The returned `Answer.kind == "Certificate"`. |
| P5 | `t_l8_jawab_shart_includes_idha_when_available` | The answer text contains `إِذَا` (the condition tool, available via `condition_tool_of` edge). |
| P6 | `t_l8_jawab_shart_records_fa_marker_when_available` | The answer text contains the literal `فَ` marker phrasing (e.g., `فاء الجَواب فَ` or equivalent locked phrase), proving the `edge.operator` evidence flows through. |

### 9.2 Negative tests (binding boundary guards)

| # | Test | Asserts |
|---|---|---|
| N1 | `t_l8_jawab_shart_zero_when_no_edge` | Synthesized scenario via a stub `MeaningGraph` containing zero `jawab_shart_of` edges. `_find_jawab_shart` returns `Answer(kind="Zero", ...)` with a `rejected_reason` mentioning the absence of جواب الشرط. The answer text MUST NOT contain `فَٱكْتُبُوهُ` or any other invented jawab surface. |
| N2 | `t_l8_jawab_shart_zero_when_edge_is_hypothesis` | Synthesized stub `MeaningGraph` where the `jawab_shart_of` edge has `proof_kind=Hypothesis`. `_find_jawab_shart` returns `Zero` (not `Hypothesis`). Tests Certificate-or-Zero discipline (§2 / §5.1 step 3). |

### 9.3 Regression tests (binding)

| # | Test | Asserts |
|---|---|---|
| R1 | `t_2_282_l4_l7_metrics_unchanged_after_batch_a` | Running the full pipeline on 2:282 (or comparing to a recorded baseline), assert L7 has exactly 135 nodes and exactly 43 links; Entropy = 0.0; consistency = True. Defends against accidental extraction-layer mutation. |
| R2 | `t_2_282_other_l8_questions_unchanged` | The 7 existing questions (`مَن الفاعِل؟`, `ماذا حَدَث؟`, `أَين حَدَث؟`, `متى حَدَث؟`, `ما تَسَلسُل الأَحداث؟`, `إلى ماذا تَحَوَّلَ شَيء؟`, `ما تَفسير هذه الآيَة؟`) for 2:282 still produce their existing ProofKind values (Hypothesis / Hypothesis / Zero / Certificate / Hypothesis / Zero / Zero respectively). |

### 9.4 Cross-suite regression (must remain green)

- `clean_code/test_shart_jawab_relations_pilot_2_282.py` — must remain **11/11**.
- `clean_code/test_production_path_segmentation.py` — must remain **159/159**.
- `clean_code/test_maani_batch_b_author_position.py` — must remain **6/6**.
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — must remain **20/20**.
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain **12/12**.

Any suite regressing rejects the batch.

### 9.5 New test file totals

`test_project_closure_batch_a_l8_shart_jawab.py` has **8 tests** (P1–P6 + N1–N2 + R1–R2 = 10; the R1/R2 regression tests may be included in this file OR cross-referenced; RULE_LOCK does not lock the inclusion location). Recommendation: include R1/R2 in the same file for locality. The implementer's report must declare the final test count for this file.

---

## 10. Acceptance criteria

The implementation batch is **acceptable** if and only if **all** of the following hold:

1. Exactly 4 files modified, matching §3 cell-for-cell.
2. `phase5_clause_segmenter.py` bit-for-bit unchanged.
3. `relation_extractor.py` bit-for-bit unchanged.
4. `meaning_assembler.py` bit-for-bit unchanged.
5. `test_production_path_segmentation.py` bit-for-bit unchanged.
6. `reasoning_engine.py` has exactly one new method (`_find_jawab_shart`) and one new entry in `strategy_map`.
7. `query_types.csv` has exactly 2 new rows at priorities 31, 32 per §5.3 verbatim text.
8. `analyze_verse_v3.py` has exactly one new entry in `questions` list and one new `elif` branch in the explanation chain.
9. New test file `test_project_closure_batch_a_l8_shart_jawab.py` exists with all §9.1–§9.3 tests passing.
10. L8 answer for `ما جواب الشرط؟` on 2:282 is Certificate AND contains `فَٱكْتُبُوهُ` AND contains `تَدَايَنتُم`.
11. L4/L7 metrics for 2:282 unchanged: nodes 135, links 43, Entropy 0.0, consistency نَعَم.
12. Cross-suite regression (§9.4) all green.
13. No file outside §3 modified.
14. No file in §4 modified.
15. No untracked artifacts (`.pyc`, `out_*.txt`, `.claude/`) committed.
16. A Batch A report at `docs/specs/PROJECT_CLOSURE_BATCH_A_REPORT.md` is produced (separately committed under separate approval).

If any of the 16 conditions fails, the batch is **rejected** (§13).

---

## 11. Rejection criteria

The implementation batch is **rejected** if any of the following occurs:

| Trigger | Reason |
|---|---|
| Any forbidden file in §4 modified | Forbidden-files lock violated. |
| Any file outside §3 modified | Allowed-files lock violated. |
| `phase5_clause_segmenter.py` modified | §4.1 violated. |
| `relation_extractor.py` or `meaning_assembler.py` modified | §4.1 violated (no L4/L7 mutation). |
| `_find_jawab_shart` scans tokens or fabricates a jawab | §5.6 violated (test N1 fails). |
| `_find_jawab_shart` returns `Hypothesis` | §5.1 step 3 / §2 violated (test N2 fails). |
| Any new relation or edge created | §2 violated. |
| Any new L7 node created | §7 violated. |
| 2:282 L7 link count drifts from 43 | §7 / R1 fails. |
| 2:282 L7 Entropy ≠ 0.0 | §7 / R1 fails. |
| 2:282 L7 consistency ≠ نَعَم | §7 / R1 fails. |
| Any other L8 question's answer changes for 2:282 | R2 fails. |
| `reasoning_engine.py` adds a Phase 5 import | Production guard fires; §4.3 violated. |
| Answer text adds interpretive content (tafsir / fiqh / scholarly opinion) | §5.6 violated. |
| Answer text hardcodes 2:282 surfaces instead of reading from `node.surface` | §5.6 violated (would defeat the edge-driven design). |
| `query_types.csv` adds rows other than the 2 in §5.3 | Schema-and-content lock violated. |
| `query_type=conditional_answer` value used for any row other than the 2 new ones | §5.3 violated. |
| New ProofKind value introduced | §6.2 violated. |
| Schema column rename / reorder / addition | §6.1 violated. |
| Untracked artifacts left in committed tree | Hygiene §4.6 violated. |
| Production tests regress below 159/159 | §9.4 violated. |
| Any other test suite regresses | §9.4 violated. |
| New paraphrase coverage added beyond §8 | §8 lock violated. |
| `WHERE_WE_ARE.md` modified by Batch A | §4.5 violated (WHERE_WE_ARE update is reserved for the final closure report). |

Rejection is total — partial acceptance is not permitted.

---

## 12. Rollback

If the batch is rejected per §13 or fails review after the implementation commit:

1. **Standard `git revert`** of the implementation commit. The revert restores `reasoning_engine.py`, `query_types.csv`, `analyze_verse_v3.py` to their pre-Batch-A state and deletes `test_project_closure_batch_a_l8_shart_jawab.py`.
2. **No force-push.** No `git reset --hard` on `main`.
3. **Phase 5 Batch B edges remain intact** on revert. The L4/L7 `condition_tool_of` + `jawab_shart_of` edges produced by Phase 5 Batch B at commit `236a885` are untouched; only the L8 answer path is removed.
4. **No data outside Batch A is touched.** MAANI, MASAQ, Phase 4, Phase 5 Batch A/B all remain intact.
5. **`WHERE_WE_ARE.md`** is unchanged on revert (it wasn't modified by Batch A).
6. **Other closure batches (B and C)** are independent and not affected.

If rollback itself requires destructive operations beyond `git revert`, halt and consult the user.

---

## 13. Source traceability

Every byte of the L8 answer emitted by `_find_jawab_shart` traces to specific existing graph data:

| Answer component | Source |
|---|---|
| Subject `جَواب الشَّرط` | Constant phrasing in strategy (lookup of fixed Arabic phrase) |
| Jawab surface (`فَٱكْتُبُوهُ` for 2:282) | `graph.get_node(edge.source).surface` where `edge.edge_type == "jawab_shart_of"` |
| Condition verb surface (`تَدَايَنتُم` for 2:282) | `graph.get_node(edge.target).surface` |
| Condition tool surface (`إِذَا` for 2:282) | `graph.get_node(condition_tool_of_edge.source).surface` (best-effort lookup) |
| Marker (`فَ`) | `jawab_shart_of_edge.operator` (Phase 5 Batch B set this to `"فَ"`) |
| ProofKind = Certificate | `jawab_shart_of_edge.proof_kind` (Phase 5 Batch B set this to `Certificate`) |

NO byte of the answer derives from token scanning, surface-pattern matching, or any bespoke detection inside `_find_jawab_shart`. **Pure edge consumption.**

---

## 14. Risks (acknowledged from Gate 2)

| # | Risk | Mitigation in this RULE_LOCK |
|---|---|---|
| R1 | L8 turns into tafsir | §5.6 forbids interpretive content; §11 rejection trigger asserts the same. |
| R2 | Broadening to other conditional tools | Strategy reads only `jawab_shart_of` edges; Phase 5 doesn't produce these for other tools today. Naturally bounded. |
| R3 | Inventing jawab when edge missing | §5.1 step 2 + N1 test enforce Zero output. §5.6 forbids token scanning. |
| R4 | L4/L7 metric drift | §7 + R1 test asserts metrics stable. §11 rejection trigger explicit. |
| R5 | Phase 5 behavior change | Phase 5 module forbidden (§4.1); no Phase 5 import in `reasoning_engine.py` (§5.6 + guard remains in force). |
| R6 | Overfitting display text | Answer uses `node.surface` from edge endpoints, not hardcoded 2:282 strings. §5.6 + N1 / N2 tests verify. |
| R7 | `query_types.csv` row collision with existing 30 rows | New rows at priorities 31, 32 with unique trigger words `جَواب_الشَّرط` / `جواب_الشرط`. Verified Gate 2 §4. |

---

## 15. Schema and ProofKind summary

- **Schema**: unchanged. No column rename / add / reorder anywhere.
- **ProofKind enum**: `{Certificate, Hypothesis, Zero}` unchanged.
- **No new node types** in `MeaningGraph`.
- **No new edge types** in L7 (Batch A reads existing edges only).
- **No new query types** beyond `conditional_answer` (open-set value in `query_types.csv`'s `query_type` column).

---

## 16. Governance

### 16.1 Approval gates (sequential)

| Gate | Action | Status |
|---|---|---|
| 1 | PROJECT_CLOSURE_SPEC_DRAFT approval | ✅ Complete at `1ca6306` |
| 2 | Closure Batch A Gate-2 read-only investigations | ✅ Complete 2026-06-01; findings embedded in §0 |
| 3 | Closure Batch A RULE_LOCK approval | this document — *pending review* |
| 4 | Implementation approval | separate explicit approval required |
| 5 | Test approval | after implementation, results reported back |
| 6 | Commit approval | user approves the specific commit hash |
| 7 | Report approval | `docs/specs/PROJECT_CLOSURE_BATCH_A_REPORT.md` written under separate approval |

Skipping any gate rejects the batch.

### 16.2 What is NEVER allowed inside Closure Batch A

- Modifying `phase5_clause_segmenter.py` or any production code outside §3.
- Creating any new L4 relation, L5 event, L6 resolution, or L7 node/edge.
- Importing `phase5_clause_segmenter` from `reasoning_engine.py`.
- Token scanning, surface-pattern matching, or any bespoke detection for إِذَا / فَ inside `_find_jawab_shart`.
- Emitting Hypothesis or any other ProofKind value besides Certificate / Zero from `_find_jawab_shart`.
- Adding interpretive (tafsir / fiqh / scholarly) phrasing to the answer.
- Supporting paraphrases beyond the canonical query string (§8).
- Editing `WHERE_WE_ARE.md` (reserved for final closure report).
- Touching MAANI / MASAQ / schema files.

### 16.3 What requires a different batch (NOT this one)

- **Closure Batch B** — Final 2:282 audit report (separate SPEC chain).
- **Closure Batch C** — `PROJECT_CLOSURE_BACKLOG.md` (separate SPEC chain).
- **Final closure report** + WHERE_WE_ARE update (after all three closure batches close).
- **Phase 5 Batches C / D / E** (deferred to backlog).
- **Other conditional tools** (إِنْ, لَوْ, مَنْ, ما, etc. — deferred to backlog).
- **Other relation families** (الاستثناء, التعليل, etc. — deferred to backlog).
- **MAANI directed expansion** — deferred to backlog.
- **MASAQ L1/L2/L3 stabilization** — deferred to backlog.
- **Quran-wide validation** — deferred to backlog.
- **User-facing interface** — deferred to backlog.

### 16.4 Concurrent-track coordination

Before the implementation batch begins, the implementer must:

1. `git log --oneline -20` — confirm no in-flight commits on Phase 5, MAANI, MASAQ, or any other production-path files since this RULE_LOCK.
2. `git status` — confirm working tree is clean except `.claude/`.
3. `git stash list` — confirm no untracked WIP exists that could be re-applied.

If any concurrent activity is found, postpone implementation until that activity completes.

---

## 17. One-screen recap

| Item | Value |
|---|---|
| Batch | Project Closure — Closure Batch A — L8 SHART_JAWAB Consumption |
| Type | L8 question/answer extension (pure consumption of existing L4/L7 edges; no L4/L7 changes) |
| Source-of-truth | `MeaningGraph.edges` (Batch B-produced); no new extraction |
| Inaugural use case | Verse 2:282, first إِذَا construction (carried from SHART_JAWAB pilot + Phase 5 Batch B) |
| Canonical query | `ما جَواب الشَّرط؟` (vocalized) / `ما جواب الشرط؟` (plain) |
| New strategy | `_find_jawab_shart(query, graph, question) → Answer` |
| Allowed files | **4**: `reasoning_engine.py`, `query_types.csv`, `analyze_verse_v3.py`, new test file |
| Forbidden | Phase 5 module + `relation_extractor.py` + `meaning_assembler.py` + 12+ other production modules + MAANI + MASAQ + schema + all other tests + `test_production_path_segmentation.py` + `WHERE_WE_ARE.md` |
| Phase 5 isolation guard | Untouched; `reasoning_engine.py` stays blocked from Phase 5 imports |
| Expected 2:282 metrics | nodes 135 unchanged; links 43 unchanged; Entropy 0.0; consistency نَعَم |
| L8 questions count | 7 → **8** (+1 for جواب الشرط) |
| New answer for 2:282 | **Certificate**: `جَواب الشَّرط هو فَٱكْتُبُوهُ، مَربوط بِفِعل الشَّرط تَدَايَنتُم (مَع فاء الجَواب فَ)` |
| ProofKind discipline | Certificate-or-Zero; no Hypothesis emission from `_find_jawab_shart` |
| Tests | 6 positive (P1–P6) + 2 negative (N1–N2) + 2 regression (R1–R2) = 10 in new file + 4 cross-suite regression |
| Schema changes | None |
| ProofKind enum | Unchanged |
| Rollback | `git revert`; restores L8; Phase 5 Batch B edges intact |
| Governance | 7 gates; 3 complete (SPEC, Gate 2, this RULE_LOCK pending); 4 remaining |
| WHERE_WE_ARE.md | NOT edited by Batch A (reserved for final closure report) |
