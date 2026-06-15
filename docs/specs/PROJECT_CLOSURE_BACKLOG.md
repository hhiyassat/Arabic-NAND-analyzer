# Project Closure — Closure Batch C — Backlog of Deferred Gaps

> **Type:** Controlled backlog document (Closure Batch C).
> **Date:** 2026-06-14
> **Status:** Active. The deferred-work register for the post-MVP project.
> **HEAD on `main` at authoring:** `a3d2cac` (Closure Batch B audit report) — local; push pending.
> **SPEC reference:** `PROJECT_CLOSURE_SPEC_DRAFT.md` (`1ca6306`) §5.
> **Re-opening contract:** any future agent or user who wants to re-open any category MUST do so via the SPEC → RULE_LOCK → narrow implementation → tests → report governance chain. This backlog is the entry door.

---

## 0. What this document is — and what it is not

This is the **closure backlog**. It catalogs every gap from `WHERE_WE_ARE.md` §4 that is NOT in the MVP closure scope (Gaps 2 – 8 and 10), and converts each into a **controlled re-opening contract**.

It is **NOT**:

- An implementation roadmap with dates.
- A claim that any deferred gap will ever be opened.
- A scope-creep mechanism.
- A document that gets edited every time a deferred gap is touched. (Each re-opening produces its OWN SPEC + RULE_LOCK + report. This backlog stays stable.)

**Why a backlog converts the project to MVP closure:** without it, gaps stay scattered across `WHERE_WE_ARE.md` §4 indefinitely. With it, each gap has an explicit re-opening contract: trigger, files, invariants, template. The project can be re-opened by any future user or agent by reading the relevant backlog entry and following the same SPEC → RULE_LOCK → implementation → tests → commit → report chain.

---

## 1. Project laws (binding for any re-opened category)

Every backlog category, when re-opened in a future batch, MUST preserve all five binding project laws:

| # | Law | Source |
|---|---|---|
| L1 | **لا إزالة للتشكيل** — no diacritic stripping. Tashkeel is sacred to the input; only Quranic-only marks (ٱ آ ٰ ٓ ۟ ـ) may be folded. | `NO_DIACRITIC_STRIPPING_RULE.md` (`07f5f0a`) + `WHERE_WE_ARE.md` §1 |
| L2 | **لا تخزّن ما تستطيع توليده** — do not duplicate curated facts; one claim has exactly one proper home. | `WHERE_WE_ARE.md` §1 + MAANI Batch C2 invariant |
| L3 | **No silent ProofKind upgrade** — monotonicity preserved (Certificate may only downgrade to Hypothesis/Zero, never upgrade). | `WHERE_WE_ARE.md` §1 + MAANI Batch B rule |
| L4 | **Zero is preferred over unsafe guessing** — `بِلا مَرجِع` is a legitimate output. | `WHERE_WE_ARE.md` §1 |
| L5 | **No tafsir / fiqh** — out of project scope entirely. L8 explicitly refuses interpretive questions. | `WHERE_WE_ARE.md` §1 + Closure Batch A discipline |

If a re-opened category cannot honor all five, it is rejected at SPEC stage.

---

## 2. Backlog category index

| # | Category | Maps to WHERE_WE_ARE Gap | One-line summary |
|---|---|---|---|
| C1 | **Phase 5 Batch C** — event scope wiring | Gap 2 | Wire Phase 5 clause structure into `event_extractor.py`; add `Event.clause_id` and `Event.parent_clause_id`; replace PATCH-5's pause-walk. |
| C2 | **Phase 5 Batch D** — resolution / hidden-pronoun scope | Gap 3 | Wire Phase 5 clauses into `resolution_engine.py` and `hidden_pronoun_signals.py`; improve safe L6 antecedent search. |
| C3 | **MASAQ L1/L2/L3 stabilization** | Gaps 4 + 5 | Per-issue SPECs for known false segmentation (`تَدَايَنتُم` Form-VI) and false role / wazn / FIIL / HARF classifications. Batch-based, never random. |
| C4 | **Additional conditional tools** | Gap 6 | The eleven remaining SHART tools: `إِنْ`, `مَنْ`, `مَا الشرطية`, `لَوْ`, `لَوْلَا`, `أَمَّا`, `كُلَّمَا`, `لَمَّا`, `مَتَى`, `أَيْنَمَا`, `حَيْثُمَا`. Each requires its own Phase 5 detector extension + SHART_JAWAB-style sub-pilot. |
| C5 | **Other relation families** | Gap 7 | Ten missing L4 families: الاستثناء, التعليل, الغاية, التفصيل, الحال, التمييز, البدل sub-types, النعت السببي, العطف البنيوي, التوكيد as L4 edge. Each family is its own SPEC + RULE_LOCK. |
| C6 | **MAANI directed expansion** | Gap 8 | Vectors V4 / V5 / V6 / V7 from `MAANI_EXPANSION_HANDOFF.md`: كان وأخواتها, أفعال المُقارَبَة, أفعال المَدْح والذَّمّ, التَّضمين practical examples. Each Vector is its own batch. |
| C7 | **Quran-wide validation** | Gap 9 | Five-stage validation funnel: pilot verse → nearby verses → surah batch → ~1000-ayah sample → full Quran sweep + golden regression. Only after one relation family stabilizes. |
| C8 | **User-facing interface** | Gap 10 | Cleaner output summarizing (condition / answer / relation / ProofKind / audit path) without raw L1–L8 debug verbosity. |

---

## 3. Backlog entries

Each entry has exactly 5 required fields, per SPEC §5.3.

---

### C1 — Phase 5 Batch C: event scope wiring

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 2 |
| **why_deferred** | The current L5 emits one event per verb but does not annotate event structural role (`shart_event` / `jawab_event` / `condition_scope_window` / `answer_scope_window`). Both `تَدَايَنتُم` and `فَٱكْتُبُوهُ` already carry `time=when_future` via PATCH-5 propagation; the structural conditional pairing lives in L4/L7 edges only, not in L5 event metadata. Closing this requires wiring Phase 5 clause segmentation into `event_extractor.py` — a multi-day batch that must extend Phase 5's planned rollout (Batch C per original Phase 5 SPEC §7). The MVP closure (Batch A) handles the user-visible payoff via L8's `ما جواب الشرط؟` answer; deeper L5 structural annotation is *useful* but not *blocking* for MVP. |
| **trigger_for_reopening** | (a) a downstream consumer (e.g., reasoning_engine or a future user-facing layer) needs to query `Event.is_shart` or `Event.in_condition_scope`, OR (b) a per-event structural feature is required for any additional conditional tool's pilot (e.g., the `إِنْ` pilot in C4 needs per-event scope to disambiguate apodosis vs protasis sequencing). |
| **likely_files** | `clean_code/event_extractor.py` (primary — wires Phase 5 clauses into event emission), `clean_code/event_schema.py` (add `clause_id` and `parent_clause_id` fields), `clean_code/phase5_clause_segmenter.py` (consumed read-only; isolation guard updated to allow `event_extractor.py` as a new permitted consumer), `clean_code/test_production_path_segmentation.py` (Phase 5 isolation guard update), one new `clean_code/test_phase5_batch_c_event_scope.py` (per-batch test file), `docs/specs/PHASE5_BATCH_C_*.md` (SPEC + RULE_LOCK + report). |
| **invariants_to_preserve** | All 5 laws. Specifically: L3 (no silent ProofKind upgrade — new event annotations must carry their own ProofKind), L4 (Zero over guessing — events that cannot be unambiguously placed in a clause emit no annotation, not a guess), L5 (no tafsir — event annotations are purely structural). The PATCH-5 `time_scope` behavior MUST be preserved, not overwritten — the new clause-derived annotation is additive. |
| **next_spec_template** | `# Phase 5 Batch C — Event Scope Derived from Clause Graph` / `## 1. Purpose: wire Phase 5 clause segmentation into event_extractor.py to add structural event annotations (clause_id, parent_clause_id, in_shart_scope, in_jawab_scope) without altering existing PATCH-5 time_scope or any L4/L7 output. SPEC defines the data model, isolation guard, ProofKind discipline, golden tests on 2:282, and one regression assertion that 2:282's L4 condition/jawab edges and L7 metrics remain unchanged.` |

---

### C2 — Phase 5 Batch D: resolution / hidden-pronoun scope

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 3 |
| **why_deferred** | Five Zero / `بِلا مَرجِع` resolutions remain on 2:282 (verified by Closure Batch B audit §8). This is **intentional** — the project law `Zero is preferred over unsafe guessing` (L4 in §1 above) is honored. Improving L6 from Zero to safe Hypothesis requires Phase 5 clause boundaries (so antecedent search is scoped to a clause, not a flat verse-window) PLUS the hidden-pronoun infrastructure that was previously parked at SPEC stage (`HIDDEN_ESTIMATED_PRONOUN_DISCOVERY_SPEC_DRAFT.md`). Both are non-trivial and not blocking for MVP closure — the visible payoff (L8 conditional answer) ships without them. |
| **trigger_for_reopening** | (a) a user-facing query produces too many `بِلا مَرجِع` answers on a chosen surah to be useful, OR (b) Phase 5 Batch C (C1 above) ships and the per-event clause_id makes hidden-subject signals trivial to anchor, OR (c) the hidden-pronoun SPEC is explicitly approved by governance. |
| **likely_files** | `clean_code/resolution_engine.py` (extend antecedent search with clause-scope cutoff), `clean_code/hidden_pronoun_signals.py` (already a read-only extractor from PATCH 13; now consumed by resolution_engine for safe-Hypothesis antecedent suggestion), `clean_code/phase5_clause_segmenter.py` (isolation guard updated to allow `resolution_engine.py` as a permitted consumer), `clean_code/meaning_assembler.py` (potentially: add new edge type `safe_anaphora_hypothesis_to`), one new test file `test_phase5_batch_d_safe_anaphora.py`, `docs/specs/PHASE5_BATCH_D_*.md`. |
| **invariants_to_preserve** | All 5 laws. Specifically: L4 (the batch MUST keep Zero as the default — every Hypothesis-upgrade from Zero requires explicit clause-scope evidence; never guess from surface adjacency alone), L3 (no silent upgrade of an existing Zero to Certificate — the batch can only emit Hypothesis upgrades, never Certificate), L5 (no tafsir — antecedent resolution is purely structural). |
| **next_spec_template** | `# Phase 5 Batch D — Safe Antecedent Resolution via Clause Scope` / `## 1. Purpose: lift safe L6 antecedents from Zero to Hypothesis when (a) Phase 5 places the pronoun and the candidate antecedent in the same or directly-dominating clause, AND (b) a structural feature (gender, number, person) matches. SPEC defines the scope-narrowing rule, the per-claim ProofKind ceiling (Hypothesis-max), the regression assertion that 2:282's existing 5 Zero resolutions either stay Zero or upgrade to Hypothesis (never Certificate), and the golden test set drawn from a clause-rich verse sample.` |

---

### C3 — MASAQ L1/L2/L3 stabilization

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gaps 4 + 5 (combined — both arise from the same MASAQ-guided correction discipline) |
| **why_deferred** | L1/L2 still produces known false segmentations (e.g., `تَدَايَنتُم` over-segments to `تَدَا + يَن + تُم` instead of correct `تَدَايَن + تُم`; other Form-VI / Form-VIII patterns may share this issue). L3 still has weak roles for several words on 2:282 (`أَجَلٍ → wazn=حرف جواب` despite `role=اسم مجرور`; `بِدَيْنٍ → wazn=فعل`; `ٱلشُّهَدَآءِ → wazn=فعلاء`). These are real defects but they do NOT prevent the Closure Batch A / B claim — the conditional structure for 2:282 is still cleanly captured at L4/L7/L8 despite the L1/L2/L3 noise. Stabilization MUST be **per-issue and batch-based**, never a broad MASAQ sweep, which is on the do-not-open-now list in `WHERE_WE_ARE.md` §5. |
| **trigger_for_reopening** | (a) a downstream batch (e.g., a future conditional tool sub-pilot from C4) is blocked by one of these specific false classifications and needs the issue resolved as a precondition, OR (b) a user-facing batch from C8 reports the segmentation noise as a UX defect on a verse that matters to the user. |
| **likely_files** | `clean_code/segmenter.py` (per-issue narrow fix — same pattern as PATCH 1/2/3), `clean_code/i3rab_engine/layer1.py` and/or `layer3.py` (per-issue MASAQ override or wazn correction), `clean_code/master_token_lookup.py` (per-issue MASAQ classification fallback), `clean_code/data/contracts/lists/*.csv` (per-issue closed-class addition with provenance), `clean_code/test_production_path_segmentation.py` (per-issue test), `docs/specs/MASAQ_STABILIZATION_<issue>_*.md`. Each issue is one SPEC + one RULE_LOCK + one batch — NEVER bundle issues. |
| **invariants_to_preserve** | All 5 laws. Specifically: L1 (no diacritic stripping — every fix preserves tashkeel and uses NFC-aware comparisons), L2 (no duplicate curated facts — a corrected classification adds one row in one canonical CSV, never patches the same fact across multiple files), L4 (Zero preferred — if MASAQ source disagrees and the rule is unsafe, emit Zero, do not guess). |
| **next_spec_template** | `# MASAQ Stabilization — <issue name> — SPEC` / `## 1. Purpose: correct exactly one known false classification (one word, one word-family, or one wazn pattern). SPEC names the specific defect, the canonical reference (MASAQ row, dictionary citation, or peer-reviewed source), the per-row CSV addition or per-rule narrow edit, the regression golden showing the corrected output AND a regression assertion that no OTHER 2:282 classification changes. Forbidden in this batch: any broad sweep, any cross-issue refactor, any change to a file not in the per-issue allow-list.` |

---

### C4 — Additional conditional tools

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 6 |
| **why_deferred** | SHART_JAWAB Phase 5 Batch B + Closure Batch A together cover exactly **one** conditional tool (إِذَا) on exactly **one** verse (2:282 first construction). The eleven remaining tools (إِنْ, مَنْ, مَا الشرطية, لَوْ, لَوْلَا, أَمَّا, كُلَّمَا, لَمَّا, مَتَى, أَيْنَمَا, حَيْثُمَا) each have distinct morphological and syntactic signatures that the current Phase 5 detector does not handle. The MVP closure law is "do not claim general SHART coverage yet" — and this backlog enforces it: each tool requires its own SPEC + Phase 5 `ConditionalScopeContract` extension + SHART_JAWAB-style sub-pilot. Bundling tools or claiming general coverage is **explicitly forbidden by `WHERE_WE_ARE.md` §5** (do-not-open-now list). |
| **trigger_for_reopening** | A specific verse with a specific tool is requested by a downstream user, AND the tool's own per-tool SPEC has been approved by governance. Reopening **any** of the eleven requires opening only **that one** tool — never "بقية أَدَوات الشرط" as a batch. |
| **likely_files** | Per tool: `clean_code/phase5_clause_segmenter.py` (extend `ConditionalScopeContract` for the tool's morphological signature — note: this is the Phase 5 isolation rule's first amendment per tool), `clean_code/relation_extractor.py` (extend SHART_JAWAB relation-extraction logic to the tool), `clean_code/data/contracts/rules/relation_types.csv` (possibly: a per-tool variant `condition_tool_of_<TOOL>` if the tool has distinct semantic flavor), `clean_code/data/contracts/lists/closed_function_words.csv` (per-tool closed-class addition if not present), `clean_code/test_shart_jawab_<TOOL>_pilot.py` (per-tool pilot test), `docs/specs/SHART_JAWAB_<TOOL>_*.md`. |
| **invariants_to_preserve** | All 5 laws. Specifically: L1 (no diacritic stripping — diacritic variants of the tool, e.g. `إِنْ` vs `أَنْ`, are kept distinct), L4 (Zero preferred — if a tool is detected but the jawab is ambiguous, emit Zero, do not guess), L5 (no tafsir — even where Arabic exegesis traditions have multiple SHART readings for a verse, the project emits only the structurally certifiable reading or Zero). |
| **next_spec_template** | `# SHART_JAWAB <TOOL> Pilot — SPEC` / `## 1. Purpose: extend Phase 5's ConditionalScopeContract to detect <TOOL>, emit condition_tool_of and jawab_shart_of edges for the canonical pilot verse, and update L8's existing find_jawab_shart strategy to surface the same answer text for <TOOL>. Scope is ONE verse, ONE conditional construction, ONE tool. The eleven other tools, ALL other verses, and any general SHART grammar claim are explicitly out of scope. Regression assertion: 2:282 إِذَا output (the original anchor) remains bit-for-bit unchanged in L4, L7, L8.` |

---

### C5 — Other relation families

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 7 |
| **why_deferred** | The analyzer currently exposes a useful but incomplete L4 relation set (`agent_of`, `patient_of`, `harf_jarr_of`, `condition_tool_of`, `jawab_shart_of`, and several others). Ten relation families are NOT yet emitted: الاستثناء (exception), التعليل (causation), الغاية (purpose / end), التفصيل (elaboration), الحال (circumstance / adverbial state), التمييز (specifier), البدل sub-types (apposition; `substitute_of` exists but lacks sub-types), النعت السببي (causative attribute), العطف البنيوي (structural conjunction), التوكيد (emphasis — partial only). Each family requires its own SPEC because each has distinct triggering markers, distinct ProofKind discipline, and distinct downstream consumers. MVP closure does not claim coverage of any of these; the project's central architectural claim ("grammar recognition → graph relations → user-visible reasoning") is proven on the **one** condition/jawab family. |
| **trigger_for_reopening** | A downstream user needs structural extraction for one specific family (e.g., wants to query "all exception constructions in surah X") AND the family's own per-family SPEC has been drafted with at least one canonical pilot verse. Bundling families is forbidden. |
| **likely_files** | Per family: `clean_code/relation_extractor.py` (extend with the new relation kind), `clean_code/data/contracts/rules/relation_types.csv` (add new relation row with priority and `kind`), `clean_code/data/contracts/lists/<family_markers>.csv` (closed-class of markers triggering the family — e.g., `إِلَّا` / `سوى` for exception, `لِكَيْ` / `حَتَّى` for purpose), `clean_code/meaning_assembler.py` (PASSTHROUGH entry if the relation should reach L7 as the same edge type), `clean_code/test_<family>_relations_pilot.py`, `docs/specs/<FAMILY>_RELATIONS_*.md`. |
| **invariants_to_preserve** | All 5 laws. Specifically: L2 (no duplicate curated facts — markers go in one canonical list per family; a marker cannot appear in two family lists without explicit governance), L3 (no silent ProofKind upgrade — a relation that requires multi-clause evidence emits Hypothesis, not Certificate, unless explicit RULE_LOCK conditions are met), L5 (no tafsir — structural relations only). |
| **next_spec_template** | `# <FAMILY> Relations Pilot — SPEC` / `## 1. Purpose: open the <family> family in L4. Add the new relation type to relation_types.csv at priority N, register markers in <family>_markers.csv, extend relation_extractor.py with the per-family logic, certify against a single pilot verse, and update Phase 5 isolation guard if the family requires clause-scope reasoning. SPEC defines the family's structural signature, the regression assertion that all existing relation families (especially condition_tool_of / jawab_shart_of) remain unchanged on 2:282, and the per-family ProofKind discipline (Certificate vs Hypothesis vs Zero criteria).` |

---

### C6 — MAANI directed expansion

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 8 |
| **why_deferred** | MAANI (Samarrai's «معاني النحو») is at 245 curated rows across 4 volumes (verified at MAANI Batch C2 closure `05a7f25`). Several families are documented as missing in `MAANI_EXPANSION_HANDOFF.md` Vectors V4–V7: V4 = كان وأخواتها, V5 = أفعال المُقارَبَة (كاد / عسى / أوشك), V6 = أفعال المَدْح والذَّمّ (نعم / بئس / حبذا), V7 = التَّضمين practical examples. **The standing rule (MAANI Batch C2 invariant + `WHERE_WE_ARE.md` §1)** is "لا تخزّن ما تستطيع توليده" — MAANI expansion is justified ONLY when it supports a concrete downstream relation or reasoning gap. Adding rows because they exist in the source is explicitly forbidden. The MVP closure does not require any of V4–V7 because the conditional structure for 2:282 is fully covered by Samarrai's existing rows + Phase 5 Batch B's L4 edges. |
| **trigger_for_reopening** | A downstream batch (most likely from C5 — other relation families) requires a MAANI fact that is not currently in the CSV set, AND that fact is one of the V4–V7 Vectors. E.g., opening a "circumstance of state" (الحال) relation family in C5 may require known كان-sister verbs to be classified — which would trigger V4. The trigger MUST point to a specific downstream gap; "to complete the volume" is NEVER a valid trigger (this honors the L2 invariant: do not duplicate curated facts). |
| **likely_files** | Per Vector: `clean_code/data/contracts/maani/volume<N>/<vector>.csv` (the per-Vector new file — e.g., `volume2/kana_sisters_meanings.csv` for V4), `clean_code/samarrai_loaders/volume<N>_loader.py` (one line: include the new CSV in the loader's file list), `clean_code/data/contracts/maani/constructions/patterns.csv` (possibly: a per-Vector construction pattern), one new test file per Vector `test_maani_vector_<V>_<name>.py`, `docs/specs/MAANI_VECTOR_<V>_*.md`. No CSV row added without explicit MAANI Batch C2 invariant compliance check. |
| **invariants_to_preserve** | All 5 laws. Specifically: L2 (no duplicate curated facts — each Vector row has exactly one canonical home; if a fact is already implicit in another row, do not add), L3 (no silent ProofKind upgrade — MAANI Batch B's `author_position → ProofKind` mapping continues to apply: `reported` → Hypothesis, `preferred` → match-type-default, corruption → Certificate as fail-open), L5 (no tafsir — Samarrai-cited semantic readings only, no exegetical interpretation). |
| **next_spec_template** | `# MAANI Vector V<N> — <vector name> — SPEC` / `## 1. Purpose: add a new MAANI volume<N>/<vector>.csv file covering the <vector> family with N rows drawn DIRECTLY from Samarrai's «معاني النحو» volume <V> pages <P1>-<P2>. SPEC declares the specific downstream relation or reasoning gap this Vector unblocks (without which the SPEC is rejected), the per-row provenance discipline, the MAANI Batch C2 invariant compliance check (each fact has one canonical home), and the regression assertion that all existing MAANI tests (Batch B author_position, Batch C2 hygiene) remain unchanged.` |

---

### C7 — Quran-wide validation

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 9 |
| **why_deferred** | The current validation set is pilot-grade — one verse (2:282) for the conditional structure, plus the per-batch test suites (208 → 218 tests over the closure cycle). Quran-wide validation requires a five-stage funnel (pilot verse → nearby verses → surah batch → ~1000-ayah sample → full Quran sweep + golden regression). At each stage, regressions and false outputs are surfaced and either fixed (in their own narrow batches per C3 / C4 / C5) or filed as new backlog entries. **`WHERE_WE_ARE.md` §5** explicitly puts "Quran-wide run" on the do-not-open-now list and requires per-family stabilization first. The MVP closure proves the architectural claim on the anchor verse; Quran-wide is a separate, sequential effort. |
| **trigger_for_reopening** | At least ONE relation family from C4 or C5 stabilizes (i.e., ships its own commit with no known regressions on its pilot), AND a governance decision is made that the project should leave MVP-closed status to take on a validation cycle. Without a stabilized family, the funnel has nothing to test. |
| **likely_files** | `clean_code/validation/` (a new subdirectory — likely the first time this path appears in the repo), `clean_code/validation/per_verse_audit.py` (per-verse audit runner), `clean_code/validation/golden_outputs/<surah>/<ayah>.json` (per-verse golden regression file — one per audited verse), `clean_code/test_quran_wide_validation_<family>.py` (per-family Quran-wide test driver), `data/quran/` (the existing Quran text source; read-only, never modified by this category), `docs/specs/QURAN_WIDE_VALIDATION_*.md`. **NEW for this category:** the validation subdirectory is its own discipline tier — read-only with respect to all other `clean_code/` modules. |
| **invariants_to_preserve** | All 5 laws, applied at scale: L1 (validation must process Quranic text without diacritic stripping — Uthmani-mark folding only), L2 (do not duplicate golden facts — one golden per verse per audited family), L3 (no silent ProofKind upgrades — if a per-verse run reports a Certificate that was previously Hypothesis without a code-change rationale, the validation surfaces it as a defect), L4 (Zero is preferred — a verse where the analyzer cannot safely emit a relation is recorded as Zero in the golden, not skipped; "no output" is itself the validated output), L5 (no tafsir). |
| **next_spec_template** | `# Quran-Wide Validation Cycle — Family <name> — SPEC` / `## 1. Purpose: run the per-family validation funnel for <family>. SPEC declares the five-stage funnel boundaries (pilot verse, nearby verses, surah batch, ~1000-ayah sample, full Quran), the per-stage acceptance criteria (e.g., ≥X% Certificate or ≥Y% safe-Zero on the sample), the regression assertion that the anchor verse 2:282 results remain bit-for-bit unchanged across all stages, and the per-stage failure-to-backlog rule (if a stage surfaces N false outputs, the SPEC stops and each false output is filed back into C3/C4/C5).` |

---

### C8 — User-facing interface

| Field | Content |
|---|---|
| **Maps to gap** | `WHERE_WE_ARE.md` §4 Gap 10 |
| **why_deferred** | The current `analyze_verse_v3 --all` output is excellent for development debugging — it exposes L1–L8 with explanations. But for a user querying the analyzer, the raw L1–L8 debug verbosity is too much. A cleaner layer is needed that summarizes (condition / answer / relation / ProofKind / audit path) without the per-layer raw output. **This is deferred because the MVP closure proves the architectural claim via the debug output** — the analytical evidence chain is auditable. A polished user-facing layer is downstream UX, not core architecture. Adding it before MVP closure would couple the architectural proof to a UI choice and would have made Closure Batch A / B harder to scope. |
| **trigger_for_reopening** | A specific downstream user (web app, CLI consumer, API client) needs structured query access AND the L1–L8 debug output has been validated on at least one stable family (i.e., C7's pilot stage has shipped for at least one family). Without a stabilized family, the user-facing layer would expose unstable internals. |
| **likely_files** | `clean_code/user_api.py` (NEW — primary entry point, accepts a verse identifier and a question, returns a structured response), `clean_code/data/contracts/rules/user_query_routing.csv` (NEW — maps canonical user questions to the L8 strategy and the L4/L7 evidence selectors), `clean_code/user_response_formatter.py` (NEW — produces compact human-readable output), `clean_code/test_user_api.py`, `docs/specs/USER_INTERFACE_*.md`. **None** of the existing `clean_code/*` files (segmenter / i3rab_engine / relation_extractor / meaning_assembler / reasoning_engine) are touched by this category — the user API is strictly a downstream consumer. |
| **invariants_to_preserve** | All 5 laws. Specifically: L3 (ProofKind discipline propagates to the user-facing output — every answer carries its ProofKind label exactly as L8 produced it, no aggregation that silently upgrades), L4 (Zero is presented as `بِلا مَرجِع` to the user with the same dignity as a Certificate answer — never hidden), L5 (no tafsir — the user-facing layer MUST NOT add interpretive commentary even where a user requests "ما تفسير هذه الآية"; respond with the existing L8 refusal). |
| **next_spec_template** | `# User-Facing Interface — Phase 1 — SPEC` / `## 1. Purpose: provide a clean user-query API that wraps L1–L8 without exposing layer internals. SPEC declares the supported question set (initially: ما جواب الشرط؟, مَن الفاعل؟, ما الفعل؟, ماذا حدث؟), the response schema (answer, ProofKind, audit_path, evidence_edges), the rejection set (tafsir/fiqh questions → 400-equivalent), and the regression assertion that the existing analyze_verse_v3 --all behavior on 2:282 is bit-for-bit unchanged. The user API is additive only.` |

---

## 4. Cross-cutting constraints (binding for every re-opening)

Beyond the 5 project laws, every re-opening of any backlog category MUST also:

| Constraint | Why |
|---|---|
| **Open one category at a time.** | Bundling C-categories defeats the per-category re-opening contract and creates scope creep. |
| **Open one sub-category at a time** (e.g., one tool in C4, one family in C5, one Vector in C6). | Same reason — granularity is the discipline. |
| **Update `WHERE_WE_ARE.md` AFTER ship**, not before. | `WHERE_WE_ARE.md` reflects landed state, not in-flight intent. Per Closure Batch A RULE_LOCK §4.5. |
| **Run the existing test suites in their entirety** (currently 218/218 expected on the user's machine) and ensure no regression. | The existing tests are the safety floor for any re-opening. |
| **Honor the do-not-open-now list** in `WHERE_WE_ARE.md` §5 unless the re-opening explicitly removes the entry from that list with reasoning. | The do-not-open-now list is a governance gate, not a default. |
| **Cite this backlog entry** in the new batch's SPEC §1 to anchor the re-opening to the closure contract. | Traceability. |

---

## 5. Definition of "filed to backlog"

For each of the 8 categories above, "filed to backlog" means:

- ✅ The category has a one-line summary in §2.
- ✅ The category has all 5 required fields populated in §3.
- ✅ The category links back to the corresponding `WHERE_WE_ARE.md` Gap.
- ✅ The category does NOT contain implementation, test, or data changes.
- ✅ The category's re-opening trigger is concrete (not "when it feels right").
- ✅ The category's likely-files list is a 5-to-10-line concrete file set, not an open hand-wave.

After this Closure Batch C report ships, **all of Gaps 2 – 8 and Gap 10** in `WHERE_WE_ARE.md` §4 are filed to backlog. The final closure report (the next stage) will:

1. Mark Gap 1 as closed in `WHERE_WE_ARE.md` §4 (closed by Closure Batch A).
2. Mark Gaps 2 – 8 and 10 as "filed to PROJECT_CLOSURE_BACKLOG.md" in `WHERE_WE_ARE.md` §4.
3. Leave Gap 9 (Quran-wide) flagged separately as the only gap whose re-opening requires a category-from-backlog chain (C4 or C5 must stabilize first).

This update to `WHERE_WE_ARE.md` is **explicitly NOT performed by Closure Batch C** — it is the work of the final closure report (next stage), per the SPEC §5.6 and §6.

---

## 6. What this document is NOT (explicit non-claims)

This backlog does NOT:

- Claim that any deferred category will be opened by a specific date.
- Commit the project to opening any category at all — re-opening is conditional on the trigger and on governance approval.
- Re-rank the categories by priority. Order is presentation-only; the trigger field governs reopening order.
- Replace `WHERE_WE_ARE.md` §4 — the gaps stay there as the canonical source; this backlog provides the re-opening contract for each.
- Cover Gap 1 (already closed by Closure Batch A) or Gap 9's partial closure (2:282 only — handled by Closure Batch B audit).

---

## 7. Final statement

**Closure Batch C is complete: the closure backlog is filed. Gaps 2 – 8 and Gap 10 each have a controlled re-opening contract. The project is one batch away from MVP closure (the final closure report + `WHERE_WE_ARE.md` update).**

This batch performed:

- **Zero code changes.**
- **Zero data changes.**
- **Zero test changes.**
- **Zero MAANI / MASAQ changes.**
- **Zero changes to `WHERE_WE_ARE.md`** (deferred to the final closure report per SPEC §5.6).

Exactly one file is created by this batch: this document.
