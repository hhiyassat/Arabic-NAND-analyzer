# SHART/JAWAB Relations Pilot — Verse 2:282 — SPEC DRAFT

> **Type:** SPEC draft (not RULE_LOCK).
> **Date:** 2026-05-31
> **Status:** Draft pending review. No implementation. No RULE_LOCK yet.
> **Scope:** Verse 2:282 only, first إِذَا construction only.
> **Track:** Relations / L4 → MeaningGraph / L7 → Reasoning / L8.

---

## 0. Why this batch exists

A targeted gap was observed when running `python3 clean_code/analyze_verse_v3.py --verse 2:282 --all` against current HEAD (`05a7f25`):

- **L3** correctly tags `إِذَا` as `ظرف شرط` (per `clean_code/i3rab_engine/layer3.py` patch 11, dated 2026-05-28).
- **L4** correctly emits `verb_in_clause` for `تَدَايَنتُم` and `فَٱكْتُبُوهُ`.
- **KB.SAM** correctly exposes the claim *«فاء رابِطَة لِجَواب الشَّرط»* on `فَٱكْتُبُوهُ` (with `?` Hypothesis).

But the analyzer **never connects these three signals into a single conditional structure**. There is no L4 relation linking:
- `إِذَا` (condition tool)
- `تَدَايَنتُم` (condition event / فِعل الشَّرط)
- `فَٱكْتُبُوهُ` (jawab الشرط / answer event)
- the `فَـ` prefix (jawab marker / فاء جواب الشرط)

Consequently L7 MeaningGraph has no conditional edge, and L8 cannot answer *«ما تَسَلسُل الأَحداث؟»* in a way that says "فَٱكْتُبُوهُ is conditioned by تَدَايَنتُم" — it can only list events flatly.

This SPEC drafts a **narrow, verse-bounded pilot** that closes this specific gap, intentionally NOT generalizing to all `إِذَا` / `إِن` / `مَن` / `ما` constructions.

---

## 1. Problem statement

### 1.1 What the analyzer sees today (verse 2:282, first conditional clause)

```
إِذَا  تَدَايَنتُم  بِدَيْنٍ  إِلَىٰٓ  أَجَلٍ  مُّسَمًّى  فَٱكْتُبُوهُ
```

| Layer | Output today | Gap |
|---|---|---|
| L3 (`i3rab_engine`) | `إِذَا → class=ISM_MUARAB, role=ظرف شرط, wazn=ظرف/شرط` | ✓ correct |
| L3 | `فَٱكْتُبُوهُ → class=FIIL, role=فعل أمر`, prefix `فَ(CONJ)` | ✓ correct but the فَ is generic CONJ, not specifically marked as فاء جواب الشرط |
| L4 | `verb_in_clause: تَدَايَنتُم → —` and `verb_in_clause: فَٱكْتُبُوهُ → —` | ❌ no condition→answer edge |
| KB.SAM | On `فَٱكْتُبُوهُ`: `? [ج4] فاء رابِطَة لِجَواب الشَّرط — تَلزَم إذا كانَ الجَواب جُملَة` | ✓ claim exists but is unconnected to إِذَا or تَدَايَنتُم |
| L7 | 41 edges, none linking إِذَا → تَدَايَنتُم → فَٱكْتُبُوهُ | ❌ structure invisible |
| L8 | `ماذا حَدَث؟` → flat list of 34 events; `ما تَسَلسُل الأَحداث؟` → textual order, not logical/conditional order | ❌ conditional dependency not expressed |

### 1.2 What should happen

Three explicit L4 relations (proposed names in §3), promoted into L7 as typed edges, surfaced in L8 reasoning. The pilot covers exactly the first `إِذَا … فَ` construction in verse 2:282 — nothing more.

---

## 1A. Linguistic rationale (background only — not a KB ingestion)

The linguistic basis for treating الشَّرط as a four-part structural relation, per a definition the user supplied:

> حُروف الشَّرط / أَدَوات الشَّرط تَربِط بَين جُملَتَين أَو حَدَثَين، بِحَيث يَرتَبِط تَحَقُّق الحَدَث الثَّاني بِتَحَقُّق الحَدَث الأَوَّل. في النَّموذَج التِّقنيّ لِهذا المَشروع نُمَثِّل ذلِك كَعَلاقَة بَين:
>
> - أَداة الشَّرط
> - حَدَث الشَّرط
> - جَواب الشَّرط
> - عَلامَة جَواب الشَّرط إن وُجِدَت مِثل الفاء

This definition is consistent with the description of أدوات الشرط in classical Arabic grammar. **Reference (background only):** الأنصاري، عبد الله بن يوسف، *مغني اللبيب عن كتب الأعاريب*، ٢٠٠٠، دار الفكر، بيروت، ط١، ص ٤١٨.

### Boundary discipline for this reference

This citation is **NOT** an admissible source in the project's KB pipeline. Specifically:

| Forbidden derivative use | Reason |
|---|---|
| Creating CSV rows from this reference | Reference is cited as linguistic rationale, not as curated content. |
| Adding it to MAANI as a new author/volume | MAANI's source restriction is Samarrai only. |
| Generalizing to all conditional tools listed in classical grammar | The pilot is scoped to one construction (§2). |
| Including the full classical table (jazm-conditionals, non-jazm conditionals, their attached judgments) as data | Background only; not ingested. |

The reference appears here **solely to motivate** the four-part decomposition (tool / event / answer / marker) into project-level relation types (`condition_tool_of`, `jawab_shart_of`, `jawab_marker_of`). The relation extractor that implements this pilot derives its evidence from the verse's actual segmentation/morphology, not from this reference.

---

## 2. Pilot target (binding scope)

**Only this construction:**

```
إِذَا  تَدَايَنتُم  بِدَيْنٍ  إِلَىٰٓ  أَجَلٍ  مُّسَمًّى  فَٱكْتُبُوهُ
↑     ↑                              ↑
tool   condition_event                jawab + jawab_marker(فَ)
```

**Explicitly out of pilot:**
- The other two `إِذَا` occurrences in 2:282 (`إِذَا مَا دُعُوا۟`, `إِذَا تَبَايَعْتُمْ`) — these have additional complications (مَا الزائدة, no فاء جواب) and are deferred.
- The four `فَإِن` occurrences in 2:282 — different particle, deferred.
- All `إِذَا` outside 2:282 — deferred.
- `إِن` / `مَن` / `ما` / `مَهْمَا` / `كَيْفَمَا` / `أَيْنَمَا` / `لَمَّا` constructions — all deferred.
- Conditionals **without** a فاء marker (لام جواب القسم, جواب الشرط الفعلي بلا فاء) — deferred.

A future expansion batch (SHART_JAWAB_RELATIONS_V2 ?) can widen scope under a separate SPEC + RULE_LOCK with fresh evidence.

---

## 3. Proposed relation types

### 3.1 Naming convention

Existing project convention: `<role>_of` where the source token holds the role with respect to the target. Existing examples in `clean_code/relation_extractor.py`: `agent_of`, `patient_of`, `harf_jarr_of`, `attribute_of`, `comment_of`, `coordinate_of`, `possessor_of`, `substitute_of`, `vocative_of`, `in_location`, `direction_to`, `from_source`.

### 3.2 Three new relations (proposed)

| Relation name | Source → Target | Semantics |
|---|---|---|
| `condition_tool_of` | `إِذَا → تَدَايَنتُم` | إِذَا is the conditional-tool of the verb تَدَايَنتُم (which is therefore the فِعل الشَّرط). |
| `jawab_shart_of` | `فَٱكْتُبُوهُ → تَدَايَنتُم` | فَٱكْتُبُوهُ is the جَواب of the condition verb تَدَايَنتُم. |
| `jawab_marker_of` | `فَٱكْتُبُوهُ → تَدَايَنتُم` *(with marker_kind="فاء_جواب_الشرط")* | The فَ prefix on فَٱكْتُبُوهُ explicitly marks it as the answer (avoids confusing the فَ with عاطفة or استئنافية). |

**Design notes:**
- `condition_tool_of` and `jawab_shart_of` carry the structural skeleton (where is the conditional?).
- `jawab_marker_of` records the syntactic evidence (the فَ is what licenses the connection).
- All three edges are anchored on the **verbs** (تَدَايَنتُم and فَٱكْتُبُوهُ), not on the particles, because verbs are the stable structural nodes in L4/L7.
- The `condition_event` is implicit: it is the target of `condition_tool_of` and the target of `jawab_shart_of`.

### 3.3 RULE_LOCK will decide

Alternative naming (if existing internal conventions prefer Arabic-style or `shart_*` prefix): the RULE_LOCK may pick one of:
- `condition_tool_of` / `jawab_shart_of` / `jawab_marker_of` *(SPEC preference)*
- `shart_tool_of` / `shart_jawab_of` / `shart_jawab_marker_of`
- `adat_shart_of` / `jawab_of_shart` / `fa_jawab_marker`

SPEC preference: option 1 (mixes English token-naming with single-purpose Arabic concept where unavoidable, matches existing `harf_jarr_of`).

---

## 4. Proof discipline

Per project ProofObject discipline `{Certificate, Hypothesis, Zero}`:

### 4.1 Certificate criteria (ALL must hold)

For the pilot's first إِذَا construction, emit `Certificate` only if:
- (a) The condition token is exactly `إِذَا` (vocalized with U+0625, U+0630, U+0627 + diacritics; the existing layer3 patch-11 detection already handles this).
- (b) The *next* FIIL token (skipping any HARF) is a safe verb event — i.e., L4 already emits `verb_in_clause` for it, and its segment is not interrupted by a pause-mark (`ۚ ۖ ۗ ۞`) or a sentence boundary.
- (c) A subsequent FIIL token, within a bounded local window (see §4.2), begins with the prefix `فَ` AND that `فَ` is segmented as `CONJ` AND the token's verb wazn is consistent with an imperative or jussive/imperfect (i.e., not an obvious عاطفة on a non-verb).
- (d) No pause-mark (`ۚ ۖ ۗ`) sits between the condition verb and the proposed answer verb.
- (e) No competing earlier `فَ`-prefixed FIIL between them already captured the answer slot (left-most-wins within window).

If (a)–(e) all hold → emit three Certificate edges: `condition_tool_of`, `jawab_shart_of`, `jawab_marker_of`.

### 4.2 Bounded window

The answer search window is **bounded** to:
- Start: the token immediately after the condition verb.
- End: the **earlier** of (i) the next pause-mark, (ii) the token at position `condition_verb_idx + 10`, or (iii) end-of-verse.

For 2:282 first construction: `تَدَايَنتُم` at idx ≈ 5; `فَٱكْتُبُوهُ` at idx ≈ 10. Window covers `بِدَيْنٍ`, `إِلَىٰٓ`, `أَجَلٍ`, `مُّسَمًّى`, `فَٱكْتُبُوهُ` — found at relative offset 5, within the 10-token window, before the first `ۚ`. ✓

### 4.3 Hypothesis criteria

Emit `Hypothesis` (not Certificate) if (a) and (b) hold but:
- The فَ-prefixed verb is found but is **outside** the bounded window — likely belongs to a later clause.
- OR the فَ is present but the segment crosses one pause-mark (could be the same conditional, could be a separate clause).
- OR the condition verb is a multi-segment construction the segmenter didn't fully resolve (e.g., compound verb prefix).

In Hypothesis mode, still emit the three edges but with `proof_kind=Hypothesis` so downstream consumers can hedge.

### 4.4 Zero criteria

Emit no edges (Zero) if:
- No FIIL token follows إِذَا within the window.
- No `فَ`-prefixed FIIL within the window.
- The condition verb is interrupted by `إِلَّا` / `أَن` / nested conditional — defer to a future batch.

**Critical:** Never invent a jawab. Zero is the correct answer when evidence is missing.

---

## 5. Layer impact (proposed; RULE_LOCK to confirm)

### 5.1 Investigation findings (read-only, this SPEC)

| File | Size | Relevance |
|---|---|---|
| `clean_code/phase5_clause_segmenter.py` | 14,639 bytes | Already exists; references shart/jawab content (per grep). Likely already does clause boundary detection. **Candidate for clause-level conditional grouping.** |
| `clean_code/relation_extractor.py` | 1,621 lines | Owns all 10 existing relation types (agent_of, patient_of, harf_jarr_of, attribute_of, etc.). Has helper `_p7_is_temporal_or_conditional_particle` (line 68) and existing code at lines 60–68, 183 (mentions جواب الشرط), 413 (mentions "فَ is the جواب-of-conditional"), 480–484 (handles temporal/conditional particles). **Primary owner of the new relations.** |
| `clean_code/event_extractor.py` | 610 lines | Owns L5 events. Should NOT be changed for this pilot — the new relations are L4 (structural), not new events. |
| `clean_code/meaning_assembler.py` | 464 lines | Owns L7 MeaningGraph assembly. Has an edge-type whitelist (around line 220) that maps specific relation names to typed edges and collapses unknowns to `operator_meaning`. **Must whitelist the three new relations** so they appear as typed L7 edges, not collapsed. |
| `clean_code/i3rab_engine/layer3.py` | (line 220 patch 11) | Already tags إِذَا as ظَرف شَرط. **No change needed in L3.** |
| `clean_code/i3rab_engine/engine.py` | 306 lines | Orchestrates layers. **No change expected.** |

### 5.2 Proposed implementation locus

| Where | What | Why |
|---|---|---|
| `relation_extractor.py` | Add new detection pass `_pN_condition_jawab_relations()` that emits the three relations when §4.1 criteria hold. | Single owner for relation emission. Existing temporal/conditional particle helpers already in this file. |
| `meaning_assembler.py` | Extend the L7 edge-type whitelist (around line 220) to include `condition_tool_of`, `jawab_shart_of`, `jawab_marker_of`. | Without this, the new relations collapse to `operator_meaning` and the L7 structure stays invisible. |
| `phase5_clause_segmenter.py` | **Investigate but defer**. Likely contains clause boundary primitives the new pass can call. If not, RULE_LOCK may permit a *read-only* import; do not edit. | Don't widen scope into clause segmentation. |
| `data/contracts/rules/relation_types.csv` | Add three rows for the new relation types (priority, certificate criteria summary). The file is referenced at `relation_extractor.py:291`. | Configuration-driven; matches existing pattern. |
| `clean_code/test_shart_jawab_relations_pilot_2_282.py` | New test file. | Per-batch test isolation. |

### 5.3 Files explicitly NOT touched

- `clean_code/i3rab_engine/*` (L3 already does its part)
- `clean_code/event_extractor.py` (L5 unchanged — no new events)
- `clean_code/master_token_lookup.py` (L1/L2 untouched)
- `clean_code/segmenter.py` / `normalizer.py` (L1 untouched)
- `clean_code/resolution_engine.py` (L6 untouched)
- `clean_code/reasoning_engine.py` (L8 changes only through the standard pipeline — no direct rule-injection)
- All MAANI CSVs
- All MASAQ files
- `schema.md`

---

## 6. Required tests

### 6.1 Positive tests (the pilot's binding assertions)

| # | Test | Asserts |
|---|---|---|
| P1 | `t_2_282_first_idha_links_to_tadayantum_as_condition_event` | After analyzing 2:282, L4 contains exactly one `condition_tool_of` edge with `source=إِذَا` (first occurrence) and `target=تَدَايَنتُم`. |
| P2 | `t_2_282_jawab_shart_links_faktubu_to_tadayantum` | L4 contains exactly one `jawab_shart_of` edge with `source=فَٱكْتُبُوهُ` and `target=تَدَايَنتُم`. |
| P3 | `t_2_282_jawab_marker_on_faktubu` | L4 contains exactly one `jawab_marker_of` edge with `source=فَٱكْتُبُوهُ` and `target=تَدَايَنتُم` and `marker_kind=فاء_جواب_الشرط`. |
| P4 | `t_2_282_l7_contains_condition_edges` | L7 MeaningGraph has at least one edge of each of the three new types for the first إِذَا construction (i.e., the edges propagate through the meaning_assembler whitelist; they do NOT collapse to `operator_meaning`). |
| P5 | `t_2_282_l8_q_event_sequence_reflects_conditional` | When L8 answers `ما تَسَلسُل الأَحداث؟` for 2:282, the answer's structure reflects (in some technical form) that `فَٱكْتُبُوهُ` follows `تَدَايَنتُم` *as a jawab*, not merely as the next event in textual order. (Exact assertion format to be locked by RULE_LOCK — could be a new `Conditional[…→…]` token in the output, or a marker field on the event-sequence answer.) |
| P6 | `t_2_282_three_edges_are_all_certificate` | The three new edges all emit `proof_kind=Certificate` (per §4.1 the first إِذَا construction satisfies (a)–(e)). |

### 6.2 Negative tests (boundary guards)

| # | Test | Asserts |
|---|---|---|
| N1 | `t_2_282_unrelated_later_fa_tokens_not_linked_to_first_idha` | The first إِذَا must NOT spuriously link to other later `فَـ`-prefixed verbs in the verse (`فَلْيَكْتُبْ` after `كَمَا عَلَّمَهُ ٱللَّهُ ۚ`, `فَلْيُمْلِلْ`, `فَإِن`, etc.). Specifically: no `jawab_shart_of` edge with `target=تَدَايَنتُم` and `source` other than `فَٱكْتُبُوهُ`. |
| N2 | `t_2_282_no_idha_jawab_across_pause_mark` | Verify that the bounded-window rule §4.2 (d) blocks any edge that would cross a `ۚ`/`ۖ`/`ۗ` pause-mark. |
| N3 | `t_2_282_second_and_third_idha_have_no_condition_tool_of_in_pilot` | Pilot is scoped to the first إِذَا only. The second (`إِذَا مَا دُعُوا۟`) and third (`إِذَا تَبَايَعْتُمْ`) إِذَا occurrences must NOT receive `condition_tool_of` edges in this pilot. They will be addressed in a future batch. |
| N4 | `t_no_condition_edge_when_no_fa_jawab_present` | Synthesize a unit-test scenario (or use an actual verse) where إِذَا is followed by a condition verb but no `فَ`-prefixed answer within the window — verify zero edges emitted. |
| N5 | `t_no_certificate_when_answer_window_violated` | Synthesize a scenario where the فَ-prefixed verb sits outside the bounded window — verify the relation, if emitted at all, is `Hypothesis` not `Certificate`. |

### 6.3 Cross-suite regression (must pass at current baselines)

- `clean_code/test_production_path_segmentation.py` — must remain 158/158.
- `clean_code/test_maani_batch_b_author_position.py` — must remain 6/6.
- `clean_code/test_maani_batch_c2_afal_tahwil_hygiene.py` — must remain 20/20.
- `clean_code/test_phase4_certificate_reevaluation.py` — must remain at its current count.

---

## 7. Regression checks for verse 2:282 specifically

After implementation, running `python3 clean_code/analyze_verse_v3.py --verse 2:282 --all` must continue to satisfy:

| Metric | Pre-pilot baseline | Post-pilot acceptable |
|---|---|---|
| Entropy (L7) | 0.0 | **must remain 0.0** (no contradictions introduced) |
| Consistency | نَعَم ✓ | **must remain نَعَم** |
| L7 nodes | 135 (52C + 83H) | unchanged ±0 (no new nodes are created — only edges) |
| L7 links | 41 (14C + 27H) | **41 + 3 = 44** (14C + 3C + 27H = 17C + 27H) for the pilot construction |
| L8 `أَين حَدَث؟` | ✗ Zero | unchanged (this pilot doesn't address location) |
| L8 `إلى ماذا تَحَوَّلَ شَيء؟` | ✗ Zero | unchanged (pilot doesn't address transformations) |
| L6 resolutions | 5 Zero (all relatives/anaphora) | unchanged (pilot doesn't address pronouns) |

---

## 8. Non-goals (explicit deferrals)

- No MAANI CSV changes (this is L4/L7 wiring, not new operator meanings).
- No MASAQ changes.
- No L1/L2 segmentation fixes (including the previously-flagged `تَدَايَنتُم → تَدَا` over-segmentation; the pilot tolerates it by matching the surviving FIIL token, whatever its stem).
- No broad conditional grammar — `إِن`, `مَن`, `ما`, `مَهْمَا`, `كَيْفَمَا`, `أَيْنَمَا`, `لَمَّا`, `إِذَا` outside 2:282 first construction — all deferred.
- No Quran-wide batch.
- No تَفسير شَرعيّ — the pilot adds *structural* edges, not interpretive content.
- No L6 pronoun/relative resolution.
- No hidden-subject work.
- No new L5 events (the verbs are already extracted; we only add structural links).
- No new ProofKind values.
- No schema changes.
- No bulk migration.
- No external sources.
- No edits to `samarrai_quran_sweep.py` or sweep regeneration in this pilot (the new relations are not topic-ids; sweep is unaffected).

---

## 8A. Future scope (mentioned for awareness only — NOT in pilot)

The full classical list of conditional tools (أَدَوات الشَّرط) — comprising both الجازِمَة and غَير الجازِمَة — includes at least:

> إِنْ، إِذْمَا، لَوْ، لَوْلَا، أَمَّا، مَنْ، أَيّ، أَيْنَ، أَيْنَمَا، كَيْفَمَا، مَتَى، حَيْثُمَا، أَنَّى، مَهْمَا، إِذَا، كُلَّمَا، مَا، لَمَّا.

Each tool has its own particularities:
- جازمة (jussive): إِنْ، إِذْمَا، مَنْ، مَا، مَهْمَا، أَيّ، مَتَى، أَيْنَ، أَيْنَمَا، حَيْثُمَا، كَيْفَمَا، أَنَّى — affect verb mood (jussive on فِعل الشَّرط and جَواب).
- غير جازمة (non-jussive): إِذَا، لَوْ، لَوْلَا، أَمَّا، كُلَّمَا، لَمَّا — do not affect verb mood.
- Some require specific جَواب markers (e.g., لَوْلَا commonly with لـ + جَواب; أَمَّا commonly with فَ).
- Some are bound to specific clause shapes (e.g., كُلَّمَا requires a past-tense pair).

**This pilot implements exactly one construction**: the first `إِذَا … فَ` in verse 2:282 (§2). All other tools, all other constructions, and all other verses are explicitly deferred.

Adding any other conditional tool — even another `إِذَا` in the same verse — requires:
1. A separate SPEC drafting evidence for that tool's particular shape (jazm? marker? scope?).
2. A separate RULE_LOCK.
3. Independent test fixtures.
4. Independent acceptance and rejection criteria.

The pilot exists to prove the four-part relation model on the cleanest possible case. Expansion is a follow-up batch (working name: `SHART_JAWAB_RELATIONS_V2` or per-tool batches like `SHART_IN_RELATIONS`, `SHART_LAW_RELATIONS`).

---

## 9. Acceptance criteria (binding sketch — RULE_LOCK to finalize)

The implementation batch is acceptable iff:

1. The three new relation types (`condition_tool_of`, `jawab_shart_of`, `jawab_marker_of` — or whatever final names RULE_LOCK picks) are emitted by L4 for the first إِذَا construction in 2:282.
2. The three new edges appear in L7 MeaningGraph as typed edges (not collapsed to `operator_meaning`).
3. L8 reasoning can technically expose the conditional dependency (P5 passes).
4. No duplicate edges (each of the three edges appears exactly once for the pilot construction).
5. No contradictory edges (e.g., no `jawab_shart_of` linking unrelated tokens).
6. L7 Entropy remains 0.0 for verse 2:282.
7. L7 consistency remains `نَعَم`.
8. Production tests pass 158/158.
9. Batch B tests pass 6/6.
10. Batch C2 tests pass 20/20.
11. Phase 4 tests pass at current count.
12. All new positive tests (P1–P6) pass.
13. All new negative tests (N1–N5) pass.
14. Only approved files touched (see §5.2).
15. No file in §5.3 modified.
16. No untracked artifacts in commit (`.pyc`, `out_*.txt`, `.claude/`).

---

## 10. Governance (gate chain — separate explicit approval at each step)

| Gate | Action | Status |
|---|---|---|
| 1 | SPEC draft | *(this document — pending review)* |
| 2 | Read-only investigations (deeper inspection of `phase5_clause_segmenter.py`, `relation_extractor.py` line-by-line, `meaning_assembler.py` whitelist, `relation_types.csv` schema; verify negative-test scenarios are reproducible) | Pending |
| 3 | RULE_LOCK draft | Pending |
| 4 | RULE_LOCK commit approval | Pending |
| 5 | Implementation approval | Pending |
| 6 | Test approval | Pending |
| 7 | Commit approval | Pending |
| 8 | Report | Pending |

Skipping any gate rejects the batch.

---

## 11. One-screen recap

| Item | Value |
|---|---|
| Batch | SHART_JAWAB_RELATIONS_PILOT_2_282 |
| Type | L4 relation extraction + L7 edge whitelisting (NOT clause segmentation, NOT new events, NOT MAANI data) |
| Scope | Verse 2:282, **first** إِذَا construction only |
| Construction | `إِذَا تَدَايَنتُم … فَٱكْتُبُوهُ` |
| New relations | `condition_tool_of`, `jawab_shart_of`, `jawab_marker_of` (3) |
| ProofKind | Certificate when all of §4.1 (a)–(e) hold; Hypothesis when partial; Zero otherwise |
| Window | Bounded: condition_verb_idx+1 .. min(next_pause_mark, idx+10, end-of-verse) |
| Files (proposed) | `relation_extractor.py`, `meaning_assembler.py`, `data/contracts/rules/relation_types.csv`, new `test_shart_jawab_relations_pilot_2_282.py` |
| Files explicitly NOT touched | i3rab, event_extractor, master_token_lookup, segmenter, normalizer, resolution_engine, reasoning_engine, MAANI CSVs, MASAQ, schema.md |
| Tests | 6 positive (P1–P6) + 5 negative (N1–N5) + cross-suite regression (production 158/158, Batch B 6/6, Batch C2 20/20, Phase 4) |
| 2:282 invariants preserved | Entropy=0.0, consistency=نَعَم, L7 nodes ±0, L7 links +3 |
| Deferred | Other إِذَا in 2:282, all إِن/مَن/ما/مَهْمَا, conditionals without فَ, all verses ≠ 2:282 |
| Governance | 8 gates; one explicit approval per gate |
