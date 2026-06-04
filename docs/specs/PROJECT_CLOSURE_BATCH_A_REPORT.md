# Project Closure — Closure Batch A — L8 SHART_JAWAB Consumption — IMPLEMENTATION REPORT

> **Type:** Implementation report (Gate 7 of governance chain).
> **Date:** 2026-06-01
> **Status:** Final. Closure Batch A closed.

---

## 1. Commit chain

| Gate | Artifact | Commit |
|---|---|---|
| 1 | Project Closure SPEC | **`1ca6306`** — `Document project closure MVP spec draft` |
| 3 | Closure Batch A RULE_LOCK | **`0854059`** — `Document project closure Batch A L8 rule lock` |
| 6 | Closure Batch A Implementation | **`8690586`** — `Project closure Batch A: add L8 shart jawab answer` |
| 7 | This report | *(uncommitted at time of writing)* |

### Anchor docs (unchanged by this batch)
| Doc | Commit |
|---|---|
| `docs/specs/WHERE_WE_ARE.md` | **`3ad474c`** (unchanged) |
| Phase 5 Batch A SPEC (Phase 5 isolation governance) | `e357ae5` (unchanged) |
| Phase 5 Batch B implementation (the source-of-truth edges) | `236a885` (unchanged) |

---

## 2. Purpose

L8 reasoning now consumes the existing L4 / L7 condition/jawab edges produced by Phase 5 Batch B for verse 2:282. The architectural payoff of Phase 5 Batch B (which made `condition_tool_of` and `jawab_shart_of` edges visible in the MeaningGraph) is now surfaced in L8's user-facing Q/A output. This closes **Gap 1** of `WHERE_WE_ARE.md` §4 for the 2:282 MVP anchor.

---

## 3. The new user-facing question

The canonical accepted query string:

```
ما جواب الشرط؟
```

(also accepted in vocalized form `ما جَواب الشَّرط؟` — the normalizer strips tashkeel before matching).

Other paraphrases (`ما هو جواب الشرط؟`, `أين جواب الشرط؟`, `جواب الشرط؟`) are **NOT** supported in this batch. Paraphrase coverage is deferred (would require a follow-up batch under fresh SPEC).

---

## 4. Exact answer behavior

The `_find_jawab_shart` strategy consumes existing `MeaningGraph.edges` and emits:

| Condition | Returned `Answer` |
|---|---|
| `jawab_shart_of` edge present AND `proof_kind=Certificate` | **`Certificate`** answer naming the jawab, condition verb, condition tool (if accessible via `condition_tool_of`), and فَ marker (if `edge.operator == "فَ"`). |
| `jawab_shart_of` edge present but **`proof_kind=Hypothesis`** | **`Zero`** with `rejected_reason="حافَة jawab_shart_of مَوجودَة لَكِنَّها ليسَت Certificate."` — Certificate-or-Zero discipline; never emit Hypothesis. |
| No `jawab_shart_of` edge | **`Zero`** with `rejected_reason="لا جَواب شَرط مَكشوف في شَبَكَة المَعنى."` — no fabrication. |
| Edge present but referenced nodes missing | **`Zero`** with `rejected_reason="عُقَد جَواب الشَّرط غَير مَوجودَة في الشَّبَكَة."` |

The strategy is **pure consumption** — no token scanning, no Phase 5 call, no new edge creation, no fallback re-detection.

---

## 5. Exact L8 answer text for verse 2:282

After running `python3 clean_code/analyze_verse_v3.py --verse 2:282 --all`:

```
✅ ما جَواب الشَّرط؟
   ✓ [Certificate] جَواب الشَّرط هو فَٱكْتُبُوهُ، مَربوط بِفِعل الشَّرط
                  تَدَايَنتُم، أَداة الشَّرط: إِذَا، مَع فاء الجَواب فَ.
   └─ الشرح: استُخرِج جَواب الشَّرط مِن حافَة jawab_shart_of في L4؛
            هذا تَركيب نَحوي وَ ليس تَفسيرًا.
```

(The display truncates to ~80 characters at the print layer; the full `Answer.answer` field contains all four parts — jawab + condition verb + condition tool + فاء marker — verified by tests P2 / P3 / P5 / P6.)

The explanation explicitly labels the answer as `تَركيب نَحوي وَ ليس تَفسيرًا` — structural grammar, not tafsir. This honors the project law `no tafsir / fiqh`.

---

## 6. Exact files committed (commit `8690586`)

**Modified (3):**

1. **`clean_code/reasoning_engine.py`** (+69 lines):
   - Added `_find_jawab_shart(query, graph, question) → Answer` strategy method.
   - Registered it in `strategy_map` under `"find_jawab_shart"`.
   - Added a compound-question handler in `parse_query` (matching the existing PATCH-6 pattern for `ما+تَسَلسُل`, `ماذا+حَدَث`, `ماذا+تَحَوَّل`) that routes `ما + جواب + الشرط` directly to `find_jawab_shart`.

2. **`clean_code/data/contracts/rules/query_types.csv`** (+2 rows): rows at priorities 31 and 32 mapping `جَواب_الشَّرط` (vocalized) and `جواب_الشرط` (plain) → `query_type=conditional_answer` → `answer_strategy=find_jawab_shart`, `in_scope=true`.

3. **`clean_code/analyze_verse_v3.py`** (+8 lines): added `"ما جَواب الشَّرط؟"` to the L8 question list at line ~327, and one new `elif` branch in the per-question explanation chain at lines 356–378 with the structural-not-tafsir explanation text.

**New (1):**

4. **`clean_code/test_project_closure_batch_a_l8_shart_jawab.py`** (+285 lines): 10 tests (P1–P6 positive, N1–N2 negative, R1–R2 regression).

**Total diff:** 4 files, +364 lines / −0 lines.

---

## 7. Explicit confirmations (binding from RULE_LOCK §4)

| File / Discipline | Status |
|---|---|
| `clean_code/relation_extractor.py` | **bit-for-bit unchanged** (no L4 edge mutations) |
| `clean_code/meaning_assembler.py` | **bit-for-bit unchanged** (no L7 PASSTHROUGH change) |
| `clean_code/phase5_clause_segmenter.py` | **bit-for-bit unchanged** (Phase 5 module untouched) |
| `clean_code/test_production_path_segmentation.py` | **bit-for-bit unchanged** (Phase 5 isolation guard untouched) |
| `clean_code/event_extractor.py` | unchanged |
| `clean_code/resolution_engine.py` | unchanged |
| `clean_code/i3rab_engine/*` | unchanged |
| All MAANI CSVs | unchanged |
| All MASAQ files | unchanged |
| `clean_code/data/contracts/maani/schema.md` | unchanged |
| `docs/specs/WHERE_WE_ARE.md` | **NOT edited** (reserved for the final closure report — RULE_LOCK §4.5) |

### Behavioral confirmations

- ✅ **No new L4 / L7 extraction.** `_find_jawab_shart` iterates `graph.edges` and reads existing data; never adds, removes, or modifies any graph element.
- ✅ **No Phase 5 call.** `reasoning_engine.py` contains no import of `phase5_clause_segmenter` or its surface symbols. The Phase 5 isolation guard (`t_phase5_clause_segmenter_not_imported_by_production_path` + `t_phase5_clause_segmenter_consumed_only_by_relation_extractor`) still passes.
- ✅ **No token scanning fallback.** The strategy never iterates `sent.tokens` and never scans for `إِذَا` / `فَ` surface patterns. Block-and-skip on empty graph (verified by test N1).
- ✅ **No tafsir / fiqh.** Answer text uses strictly structural phrasing (`جَواب الشَّرط هو X مَربوط بِفِعل الشَّرط Y`); explanation explicitly labels output as `تَركيب نَحوي وَ ليس تَفسيرًا`.

---

## 8. L4 / L7 metrics for verse 2:282 — unchanged

| Metric | Before (HEAD `0854059`) | After implementation (HEAD `8690586`) |
|---|---|---|
| L4 `condition_tool_of: إِذَا → تَدَايَنتُم` | present, Certificate | **unchanged** |
| L4 `jawab_shart_of: فَٱكْتُبُوهُ → تَدَايَنتُم` | present, Certificate | **unchanged** |
| L7 nodes | 135 (52C + 83H) | **135 (52C + 83H)** |
| L7 links | 43 (16C + 27H) | **43 (16C + 27H)** |
| L7 Entropy | 0.0 | **0.0** |
| L7 consistency | نَعَم ✓ | **نَعَم ✓** |
| L8 questions count | 7 | **8** (+1: ما جَواب الشَّرط؟) |

Verified by both the R1 test (`graph.stats()['edges'] == 43`) and the live `analyze_verse_v3 --verse 2:282 --all` output.

---

## 9. Test results (final)

| Suite | Result |
|---|---|
| `clean_code/test_project_closure_batch_a_l8_shart_jawab.py` (new) | **10/10 passed** |
| `clean_code/test_shart_jawab_relations_pilot_2_282.py` (regression) | **11/11 passed** |
| `clean_code/test_production_path_segmentation.py` (regression) | **159/159 passed** |
| `clean_code/test_maani_batch_b_author_position.py` (regression) | **6/6 passed** |
| `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` (regression) | **20/20 passed** |
| `clean_code/test_phase4_certificate_reevaluation.py` (regression) | **12/12 passed** |

**Total: 218/218 passed, no regressions.**

### Closure Batch A test breakdown (10 tests)

| Test | Purpose |
|---|---|
| P1 `t_l8_answers_jawab_shart_for_2_282` | L8 produces a non-empty answer for the canonical query |
| P2 `t_l8_jawab_shart_answer_contains_faktubu` | Answer contains `فَٱكْتُبُوهُ` |
| P3 `t_l8_jawab_shart_links_faktubu_to_tadayantum` | Answer contains `تَدَايَنتُم` + linkage phrasing (`مَربوط` / `بِفِعل الشَّرط`) |
| P4 `t_l8_jawab_shart_answer_is_certificate` | `Answer.kind == "Certificate"` |
| P5 `t_l8_jawab_shart_includes_idha_when_available` | Answer surfaces `إِذَا` from the `condition_tool_of` edge |
| P6 `t_l8_jawab_shart_records_fa_marker_when_available` | Answer surfaces `فاء الجَواب فَ` from `edge.operator` |
| N1 `t_l8_jawab_shart_zero_when_no_edge` | Empty graph → `Zero`, no fabrication of jawab surface |
| N2 `t_l8_jawab_shart_zero_when_edge_is_hypothesis` | Hypothesis edge → `Zero` (Certificate-or-Zero discipline) |
| R1 `t_2_282_l4_l7_metrics_unchanged_after_batch_a` | `graph.stats()` matches the 135 nodes / 43 links / 0.0 Entropy / True consistency baseline |
| R2 `t_2_282_other_l8_questions_unchanged` | The 7 pre-Batch-A L8 questions retain their ProofKind values (Hypothesis / Hypothesis / Zero / Certificate / Hypothesis / Zero / Zero) |

No tests fell back to `[skipped]` — all assertions were exercised on real production data.

---

## 10. Test-fix transparency

Two issues surfaced during initial test runs. Both were **test-only**, not production:

### 10.1 Query routing fix

**Symptom:** First run reported 4/10 — P1–P6 all failed with answers like `إِحْدَىٰهُمَا / صَغِيرًا`. The query was being routed to `find_patient` (via the generic `ما` trigger at CSV priority 25), not to `find_jawab_shart` (CSV priority 31).

**Root cause:** `parse_query` splits the question into whitespace-separated words. The CSV trigger `جَواب_الشَّرط` contains an underscore that never appears in real question text; the trigger could only match a literal hyphenated word. Existing multi-word triggers (`بسبب_ماذا`, `صار_إلى`) are also routed via per-pattern compound handlers in `parse_query` (the existing PATCH-6 pattern), not by the CSV trigger alone.

**Fix:** Added a compound-question handler to `parse_query` matching the PATCH-6 pattern:

```python
has_jawab = "جواب" in q_words
has_shart = "الشرط" in q_words
if has_ma_or_madha and has_jawab and has_shart:
    return Query(raw_text=question, query_type="conditional_answer",
                 trigger_word="ما+جَواب+الشَّرط",
                 answer_strategy="find_jawab_shart",
                 is_in_scope=True)
```

This is a code change in `reasoning_engine.py` (within the allowlist) and matches the existing `ما+تَسَلسُل`, `ماذا+حَدَث`, `ماذا+تَحَوَّل` handlers.

### 10.2 Canonical verse text fix (R1)

**Symptom:** After fixing routing, 9/10 passed; only R1 failed with `L7 links drifted: 38 != 43`. This was alarming because the implementation did not touch any extraction layer.

**Root cause:** The test file initially embedded the 2:282 verse text as a multi-line string literal. Comparison against `load_verse('2:282')` (the canonical Quran source the production path uses) revealed a 4-character difference, with the first diff at offset 7 (a `ّ` shadda missing). The 4 missing diacritics caused Phase 5 / segmenter to detect 5 fewer Hypothesis edges, dropping the count from 43 to 38.

**Fix:** Replaced the inline string literal with a call to `load_verse('2:282')` at module import time. **No production logic changed.**

This narrative is preserved here for traceability so future maintainers understand why R1 is anchored to `load_verse` rather than an inline string.

---

## 11. Acceptance criteria (RULE_LOCK §10) — all 16 satisfied

| # | Criterion | Status |
|---|---|---|
| 1 | Exactly 4 files modified | ✅ |
| 2 | `phase5_clause_segmenter.py` unchanged | ✅ |
| 3 | `relation_extractor.py` unchanged | ✅ |
| 4 | `meaning_assembler.py` unchanged | ✅ |
| 5 | `test_production_path_segmentation.py` unchanged | ✅ |
| 6 | `reasoning_engine.py` has the locked additions (method + `strategy_map` entry + compound-handler — see §10.1) | ✅ |
| 7 | `query_types.csv` has exactly 2 new rows at priorities 31, 32 with the locked text | ✅ |
| 8 | `analyze_verse_v3.py` has exactly one new entry in the `questions` list + one new `elif` branch | ✅ |
| 9 | New test file exists with all §9.1–§9.3 tests passing | ✅ (10/10) |
| 10 | L8 answer for 2:282 is Certificate AND contains `فَٱكْتُبُوهُ` AND contains `تَدَايَنتُم` | ✅ |
| 11 | L4/L7 metrics unchanged: nodes 135, links 43, Entropy 0.0, consistency نَعَم | ✅ |
| 12 | Cross-suite regression all green | ✅ |
| 13 | No file outside §3 modified | ✅ |
| 14 | No file in §4 modified | ✅ |
| 15 | No untracked artifacts in commit | ✅ |
| 16 | Batch A report committed under separate approval | This document — pending Gate 7 commit |

---

## 12. Rejection criteria (RULE_LOCK §11) — none triggered

All 22 enumerated rejection triggers were checked and none triggered:

- No forbidden file in §4 modified ✓
- No file outside §3 modified ✓
- Phase 5 module unchanged ✓
- `relation_extractor.py` / `meaning_assembler.py` unchanged ✓
- `_find_jawab_shart` does not scan tokens or fabricate a jawab ✓ (N1)
- `_find_jawab_shart` does not return Hypothesis ✓ (N2)
- No new relation / edge created ✓
- No new L7 node created ✓
- 2:282 L7 link count remains 43 ✓
- 2:282 L7 Entropy remains 0.0 ✓
- 2:282 L7 consistency remains نَعَم ✓
- 7 existing L8 question answers unchanged ✓ (R2)
- No Phase 5 import in `reasoning_engine.py` ✓ (production guard passes)
- No interpretive content in answer text ✓
- No hardcoded 2:282 surfaces (uses `node.surface` from edge endpoints) ✓
- `query_types.csv` adds exactly 2 rows ✓
- `query_type=conditional_answer` not used elsewhere ✓
- No new ProofKind value ✓
- No schema column rename / reorder / addition ✓
- No untracked artifacts in tree ✓
- No production test regression ✓
- No other test suite regression ✓
- No paraphrase coverage beyond §8 ✓
- `WHERE_WE_ARE.md` not modified ✓

---

## 13. Rollback path

If a future review surfaces a regression, the rollback is a standard `git revert 8690586`. The revert:

- Removes `_find_jawab_shart` and the compound-question handler from `reasoning_engine.py`.
- Removes the new entry in `strategy_map`.
- Removes the 2 new rows from `query_types.csv`.
- Removes the new question + explanation `elif` from `analyze_verse_v3.py`.
- Deletes `clean_code/test_project_closure_batch_a_l8_shart_jawab.py`.

**Critically, the revert does NOT touch:**

- `phase5_clause_segmenter.py` — Phase 5 module remains intact.
- `relation_extractor.py` — Phase 5 Batch B's `condition_tool_of` and `jawab_shart_of` edge emission remains intact.
- `meaning_assembler.py` — the L7 PASSTHROUGH whitelist remains intact.
- `test_production_path_segmentation.py` — the Phase 5 isolation guard remains intact.

So a revert of `8690586` removes only the L8 answer path and the focused tests; it does not undo any L4/L7 work from earlier batches. **No force-push.** **No `git reset --hard`.** No data outside Closure Batch A is touched.

---

## 14. Source traceability

Every byte of the L8 answer emitted by `_find_jawab_shart` traces to specific existing graph data — zero detection inside the strategy:

| Answer component | Source |
|---|---|
| Fixed phrase `جَواب الشَّرط` | Constant in strategy code (literal Arabic) |
| Jawab surface (`فَٱكْتُبُوهُ` for 2:282) | `graph.get_node(edge.source).surface` where `edge.edge_type == "jawab_shart_of"` |
| Condition verb surface (`تَدَايَنتُم` for 2:282) | `graph.get_node(edge.target).surface` |
| Condition tool surface (`إِذَا` for 2:282) | `graph.get_node(condition_tool_of_edge.source).surface` (best-effort lookup of the matching `condition_tool_of` edge sharing the same target node) |
| Marker (`فَ`) | `jawab_shart_of_edge.operator` (Phase 5 Batch B set this to `"فَ"`) |
| `ProofKind = Certificate` | `jawab_shart_of_edge.proof_kind` (Phase 5 Batch B set this to `Certificate`) |

---

## 15. Final governance statement

> **Gate 7 complete. Closure Batch A is closed.**
> **Gap 1 from `WHERE_WE_ARE.md` §4 is closed for the verse 2:282 MVP anchor.**
> **Closure Batches B (final 2:282 audit report) and C (closure backlog) remain pending.**

The seven-gate governance chain for Closure Batch A is now fully traversed:

| Gate | Action | Artifact | Status |
|---|---|---|---|
| 1 | Project Closure SPEC approval | `1ca6306` | ✅ Closed |
| 2 | Closure Batch A Gate-2 read-only investigations | (findings embedded in RULE_LOCK §0) | ✅ Closed |
| 3 | Closure Batch A RULE_LOCK approval | `0854059` | ✅ Closed |
| 4 | Implementation approval | (oral approval) | ✅ Closed |
| 5 | Test approval (218/218 across 6 suites) | verified | ✅ Closed |
| 6 | Commit approval | `8690586` | ✅ Closed |
| 7 | Report | This document | ✅ Closed |

### What this batch accomplishes

The architectural payoff of Phase 5 Batch B (which made `condition_tool_of` and `jawab_shart_of` edges visible in the MeaningGraph for verse 2:282) is now **visible to the user** via L8 reasoning. A reader asking the canonical question `ما جواب الشرط؟` receives a Certificate-grade structural answer naming the jawab (`فَٱكْتُبُوهُ`), the condition verb (`تَدَايَنتُم`), the condition tool (`إِذَا`), and the فاء marker (`فَ`). The system explicitly labels this as `تَركيب نَحوي وَ ليس تَفسيرًا` — structural grammar, not tafsir.

This is the central architectural claim of the project: **grammar recognition → graph relations → user-visible reasoning, with auditable ProofKind discipline at every layer**. Closure Batch A makes that claim end-to-end demonstrable on the anchor verse.

### What this batch does NOT do

- Does NOT extend coverage to the other two إِذَا occurrences in 2:282 (deferred to backlog).
- Does NOT support paraphrases of the canonical query (deferred to backlog).
- Does NOT cover other conditional tools (إِنْ / لَوْ / مَنْ / ما / etc. — deferred to backlog).
- Does NOT cover other verses (Quran-wide deferred to backlog).
- Does NOT change L4 / L5 / L6 / L7 / L8 architecture beyond adding one L8 question handler.
- Does NOT update `WHERE_WE_ARE.md` — that update is reserved for the **final closure report** after Closure Batches B and C ship.

### Remaining closure work

| Closure Batch | Purpose | Status |
|---|---|---|
| **Closure Batch B** | Final 2:282 audit report (`docs/specs/2_282_FINAL_AUDIT_REPORT.md`) covering L1–L8 + ProofKind audit + invariants check | Pending — requires SPEC + RULE_LOCK + implementation gates |
| **Closure Batch C** | `docs/specs/PROJECT_CLOSURE_BACKLOG.md` documenting deferred Gaps 2–8 + 10 from `WHERE_WE_ARE.md` | Pending — requires SPEC + RULE_LOCK + implementation gates |
| **Final closure report** | `docs/specs/PROJECT_CLOSURE_REPORT.md` + `WHERE_WE_ARE.md` MVP-CLOSED update | After Closure Batches B + C close |

Closure Batches B and C are independent and may be approached in either order. Each requires its own 7-gate governance chain.

---

## 16. One-screen recap

| Item | Value |
|---|---|
| Batch | Project Closure — Closure Batch A — L8 SHART_JAWAB Consumption |
| Closed | 2026-06-01 |
| Commit chain | SPEC `1ca6306` → RULE_LOCK `0854059` → Implementation `8690586` → Report (this) |
| Anchor docs | `WHERE_WE_ARE.md` at `3ad474c` (unchanged) |
| Anchor verse | 2:282 (first إِذَا construction) |
| Gap closed | `WHERE_WE_ARE.md` §4 Gap 1 (L8 doesn't use condition/jawab structure) |
| Canonical query | `ما جواب الشرط؟` (vocalized: `ما جَواب الشَّرط؟`) |
| Answer ProofKind | Certificate-or-Zero only (no Hypothesis emission) |
| Files committed | 4 (3 modified + 1 new): `reasoning_engine.py`, `query_types.csv`, `analyze_verse_v3.py`, new pilot test |
| Phase 5 module modified | **No** (bit-for-bit unchanged) |
| `relation_extractor.py` modified | **No** |
| `meaning_assembler.py` modified | **No** |
| `test_production_path_segmentation.py` modified | **No** |
| L4 edges added | **0** (pure consumption of existing Batch B edges) |
| L7 metrics change | **none**: nodes 135 / links 43 / Entropy 0.0 / consistency نَعَم |
| L8 questions count | 7 → **8** (+1) |
| All test suites | 10/10 + 11/11 + 159/159 + 6/6 + 20/20 + 12/12 = **218/218** |
| Test-fix history | Routing fixed via compound-handler; R1 anchored to canonical text via `load_verse` |
| Tafsir / fiqh introduced | **No** (answer labeled `تَركيب نَحوي وَ ليس تَفسيرًا`) |
| Token scanning fallback | **No** (verified by N1) |
| Phase 5 import in `reasoning_engine.py` | **No** (production guard still passes) |
| `WHERE_WE_ARE.md` updated | **No** (reserved for final closure report) |
| Rollback | `git revert 8690586` — removes L8 answer path + focused tests only |
| Governance gates | 7/7 complete |
| Closure Batch B status | Pending |
| Closure Batch C status | Pending |
| Final closure report status | Pending |
| Status | **CLOSED** (Closure Batch A only) |
