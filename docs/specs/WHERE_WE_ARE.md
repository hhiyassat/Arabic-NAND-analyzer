# WHERE WE ARE — Arabic Quranic Analyzer

> **Type:** Living status document. The single "where we are" map for the whole project.
> **Last updated:** 2026-05-31 (post-PR-#1 merge)
> **HEAD on `main`:** `9f5033b` (merge commit) — preserves gated history of all batches below.

This file is updated after **every** completed batch, report, merge, or major decision. It is the operational map Claude must consult before recommending any next step.

---

## 1. Project aim

Build a **layered Quranic linguistic analyzer** that produces, for each verse:

| Layer | Output |
|---|---|
| **L1** | segmentation (prefixes / stem / suffixes) |
| **L2** | morphology (root, wazn, tense, etc.) |
| **L3** | i3rab / word-class / role classification |
| **L4** | relations (agent_of, patient_of, condition_tool_of, jawab_shart_of, …) |
| **L5** | events (per-verb, with tense / mood / time_scope) |
| **L6** | resolution (anaphora, deixis, relative-clause antecedent) |
| **L7** | MeaningGraph (unified node + edge graph) |
| **L8** | technical reasoning / Q&A (who? what? when? where? sequence? transformation?) |

Every claim in every layer must be **auditable** and must carry one of:

- **Certificate** — supported by direct rule or strong evidence
- **Hypothesis** — linguistically plausible but unresolved
- **Zero** — no safe answer; system declines rather than guesses

### Project limits

- **No tafsir / fiqh interpretation.** Out of scope. L8 explicitly refuses interpretive questions.
- **Zero is preferred over unsafe guessing.** "بِلا مَرجِع" is a legitimate output.
- **No silent ProofKind upgrades.** Monotonicity preserved (Certificate may only downgrade, never upgrade).
- **No stripping Arabic diacritics.** Tashkeel is sacred to the input; only Quranic-only marks (ٱ آ ٰ ٓ ۟ ـ) may be folded.
- **No duplicate curated facts.** One claim → one proper home.

### Two foundational project laws

- **لا إزالة للتشكيل** — diacritic preservation is binding across all layers and tools.
- **لا تخزّن ما تستطيع توليده** — do not duplicate curated facts; one claim has exactly one proper home.

---

## 2. Current integrated state

The broad production-path branch (`patch0-production-path-trace`) was merged into `main` via **PR #1** using a **merge commit** (`9f5033b`), preserving the full gated history.

- ✅ `main` contains the gated history of every batch listed in §3.
- ✅ `patch0-production-path-trace` still exists as a preserved branch (not deleted post-merge).
- ✅ Working tree on `main` is clean except for `.claude/` (untracked, intentionally never committed).
- ✅ All 5 active test suites green on `main` at the merge commit:
  - `test_shart_jawab_relations_pilot_2_282.py` — 11/11
  - `test_production_path_segmentation.py` — 159/159
  - `test_maani_batch_b_author_position.py` — 6/6
  - `test_maani_batch_c2_afal_tahwil_hygiene.py` — 20/20
  - `test_phase4_certificate_reevaluation.py` — 12/12
  - **Total: 208/208**

### Tracks merged into `main`

| Track | Status | Latest commit on track |
|---|---|---|
| **Phase 5 Batch B** (relation/clause wiring) | Closed | `a715cb3` (report) |
| **SHART_JAWAB pilot for 2:282** | Implemented (under Batch B) | `236a885` |
| **MAANI Batch C2** (AFAL_TAHWIL hygiene/migration) | Closed | `05a7f25` (report) |
| **MAANI Batch B** (author_position downgrade) | Closed | `63438ec` |
| **MASAQ F3** (classification + lookup fixes) | Multiple commits; foundational | `c66b559` and others |
| **Surah 1 VERSEBYVERSE audit** | Completed for Surah 1; not a default ongoing track | `2fe56fb` (report) |
| **NO_DIACRITIC_STRIPPING_RULE** | Governance doc, binding | `07f5f0a` |
| **Phase 4 / production-path stabilization** | Multiple commits; foundational | various |

---

## 3. What is finished

### 3.1 SHART_JAWAB / Phase 5 Batch B

**Phase 5 Batch B is closed.** The SHART_JAWAB pilot for verse 2:282 first إِذَا construction is implemented at L4 and L7.

Current relation output for 2:282:

```
✓ condition_tool_of [إِذَا] : إِذَا → تَدَايَنتُم          (Certificate)
✓ jawab_shart_of    [فَ]   : فَٱكْتُبُوهُ → تَدَايَنتُم      (Certificate)
```

Architectural facts preserved:

- ✅ Phase 5 module (`clean_code/phase5_clause_segmenter.py`) remains **untouched**.
- ✅ `relation_extractor.py` is the **only** production consumer of Phase 5.
- ✅ Isolation guard was **narrowed**, not deleted (1 allow-list entry + 1 positive guard test + regex hardened to include bare `segment_clauses`).
- ✅ `meaning_assembler.py` consumes relation names as strings only — no Phase 5 import.
- ✅ Two new relation types added to `relation_types.csv` at priorities 18, 19 with `kind=conditional` (open-set; not a schema change).

### 3.2 MAANI C2 AFAL_TAHWIL

**MAANI Batch C2 is closed.** AFAL_TAHWIL is now handled as **hygiene/migration**, not duplicate addition.

Core achievements:

- ✅ Transformation claims migrated/reclassified from `ZANN_FAMILY` to `AFAL_TAHWIL`.
- ✅ Duplicate curated transformation facts removed (the invariant *«لا تخزّن ما تستطيع توليده»* enforced by H1/H2/C7 tests).
- ✅ `author_position` / `confidence` / `provenance` / `vocalization` preserved verbatim (H3 / H4 / H5 tests).
- ✅ `SAYYARA` and `TARAKA` remain `reported` → Hypothesis (no silent upgrades; reverses the abandoned Batch C path).
- ✅ `transform_verbs_meanings.csv` established as the single home for `AFAL_TAHWIL`.
- ✅ Samarrai sweep outputs (`per_word.csv` etc.) regenerated within the allowlist.
- ✅ ITTAKHADHA's pre-existing 18-field row corruption was fixed to 19-field alignment per the RULE_LOCK's binding 19-field intent (Batch B corruption test remains stub-based and unaffected).

### 3.3 MASAQ / L1–L3 stabilization

Several MASAQ F3 fixes are completed and integrated into `main`:

- Uninflected verb certification (بِئْسَ / نِعْمَ / عَسَى family)
- Interrogative pronoun forms (كَيْفَ / كَمْ / لِمَ / مَتَى / أَيْنَ / أَنَّى)
- Foreign proper noun handling (جَهَنَّم family → AALAM)
- Comparative adjective certification (`أَدْنَى` / `أُخْرَى` only; `أَعْلَمُ` rolled back for polysemy)
- Verb classification recovery via lookup fallback
- Genitive `naat` role suppression where unsafe
- Quranic-mark MTL fold + strict-form fallback recovering 7 PV/IV verbs

The **`لا إِزالة لِلتَّشكيل`** law was established as a binding governance document (`docs/specs/NO_DIACRITIC_STRIPPING_RULE.md`) covering all L1/L2/L3 work.

**But L1/L2/L3 still need controlled, batch-based stabilization later** (see Gaps 4 + 5).

### 3.4 Verse-by-verse work

Surah 1 verse-by-verse audit and per-verse fixes (1:1 / 1:4 / 1:6 / 1:7) are in history, plus a final `VERSEBYVERSE_SURAH_1_REPORT.md`.

**Verse-by-verse should NOT become the default next track unless explicitly approved.** It is structurally a slow, per-verse loop that risks distracting from the broader architectural gaps below.

---

## 4. Current gaps (priority order)

### Gap 1 — L8 does not yet use the new condition/jawab structure

**Current:** L4 and L7 know:

```
إِذَا → تَدَايَنتُم (condition_tool_of, Certificate)
فَٱكْتُبُوهُ → تَدَايَنتُم (jawab_shart_of, Certificate)
```

But L8's `ما تَسَلسُل الأَحداث؟` answer still renders events as a mostly flat textual order:

```
[Hypothesis] ءَامَنُوٓا → تَدَايَنتُم → فَٱكْتُبُوهُ → وَلْيَكْتُب → يَأْبَ → يَكْتُبَ → ...
```

**Needed later:** Phase 5 Batch E — structure-aware reasoning.

**Goal:** L8 should be able to answer:

```
إِذَا تَدَايَنتُم  →  فَٱكْتُبُوهُ
```

(structural conditional grouping, NOT tafsir; the answer is purely "X is conditioned by Y per the L4/L7 edges").

### Gap 2 — L5 event scope is still shallow

**Current:** L5 emits events per verb but does not deeply annotate event scope:

- shart event
- jawab event
- condition scope window
- answer scope window

Both `تَدَايَنتُم` and `فَٱكْتُبُوهُ` carry `time=when_future` (PATCH-5 behavior) but neither carries a structural marker linking them to a shared conditional scope.

**Needed later:** Phase 5 Batch C — event scope derived from clause graph (per the original Phase 5 SPEC §7).

### Gap 3 — L6 resolution remains cautious and weak

**Current:** Many pronouns and relatives in 2:282 resolve to `بِلا مَرجِع` / Zero (5 such in the current 2:282 run). This is **intentional** (Zero over unsafe guessing) but a known gap.

**Needed later:** Phase 5 Batch D — use Phase 5 clause boundaries to improve safe resolution (relative-clause antecedent search; hidden-subject signals to clause-anchored event agents).

### Gap 4 — L1/L2 segmentation issues remain

**Known examples:**

- `تَدَايَنتُم` segmented as stem `تَدَا` + `يَن(NSUFF)` + `تُم(VSUFF)` (over-eager NSUFF detection — the stem should be `تَدَايَن`, full 6-letter Form-VI past, with only `تُم(VSUFF)` as suffix).
- Other Form-VI / Form-VIII pattern words may have similar issues.
- More MASAQ-guided stabilization is still needed for known false-segmentation cases.

**Must obey:**

- لا إزالة للتشكيل
- no stripped-diacritic comparison
- no broad random fixes; only narrow batch-based corrections with SPEC + tests

### Gap 5 — L3 i3rab / classification still has weak roles

**Known issue family:** false FIIL, false HARF, weak roots / wazn / roles. Examples visible in 2:282 output:

- `أَجَلٍ` → wazn = `حرف جواب` despite role `اسم مجرور`
- `بِدَيْنٍ` → wazn = `فعل`
- `ٱلشُّهَدَآءِ` → wazn = `فعلاء`

Future work must be **batch-based, not random** (one false-role family per SPEC).

### Gap 6 — conditional tools beyond the first إِذَا are not implemented

**Do not claim general SHART coverage yet.** SHART_JAWAB Batch B pilot covers exactly **one** construction (first إِذَا in 2:282).

Future families requiring their own SPEC + RULE_LOCK (each):

- `إِنْ`
- `مَنْ` (الشرطية)
- `مَا` الشرطية
- `لَوْ`
- `لَوْلَا`
- `أَمَّا`
- `كُلَّمَا`
- `لَمَّا`
- `مَتَى`
- `أَيْنَمَا`
- `حَيْثُمَا`

Each requires Phase 5's own `ConditionalScopeContract` to extend first; then a SHART_JAWAB-style sub-pilot.

### Gap 7 — other relation families are missing

Future L4 relation families that the analyzer does not yet expose:

- الاستِثناء (exception)
- التَّعليل (causation)
- الغايَة (purpose / end)
- التَّفصيل (elaboration)
- الحال (circumstance / adverbial state)
- التَّمييز (specifier)
- البَدَل (apposition — partial; `substitute_of` exists but needs sub-types)
- النَّعت السَّبَبيّ (causative attribute)
- العَطف البِنيَويّ (structural conjunction)
- التَّوكيد (emphasis — partial; `tawkid` exists in some places but not as L4 edge)

### Gap 8 — MAANI still needs directed, not random, expansion

MAANI (Samarrai's «معاني النحو») should expand **only** when it supports a concrete relation/reasoning gap.

- ✗ Do NOT add rows simply because they exist in the source.
- ✗ Do NOT duplicate curated facts (Batch C2 invariant).
- ✓ Prefer: one fact → one proper semantic home.
- ✓ Expansion must follow Vector V4/V5/V6/V7 framing from the handoff document; each Vector is its own batch.

### Gap 9 — Quran-wide validation is not complete

**Current:** Pilot / sample / per-batch validation exists (e.g., MAANI C2's sweep test; SHART_JAWAB's single-verse test).

**Future workflow** (only after a relation family stabilizes):

1. Pilot verse (already done for إِذَا on 2:282)
2. Nearby verses (other إِذَا in 2:282 + surrounding)
3. Surah batch
4. ~1000-ayah sample
5. Full Quran sweep + golden regression

### Gap 10 — user-facing output layer is still not final

**Current:** Debug output (`analyze_verse_v3 --all`) is excellent for development. It exposes L1–L8 with explanations.

**Future:** A cleaner user-facing layer is needed that summarizes:

- the condition / answer pair
- the relation involved
- the ProofKind
- the audit path

…without the L1–L8 raw debug verbosity.

---

## 5. Do-not-open-now list (binding)

Unless explicitly approved, do **NOT** open:

| Track | Why blocked |
|---|---|
| MASAQ broad sweep | Risks tightening L1/L2/L3 with cascading effects without per-batch SPEC |
| All conditional tools | Each tool requires its own SPEC + Phase 5 extension first |
| Hidden pronouns | Out of scope for current track; needs its own SPEC |
| Phase 5 Batch C | Reserved future scope (event_extractor consumption) |
| Phase 5 Batch D | Reserved future scope (resolution_engine + hidden_pronoun_signals consumption) |
| Phase 5 Batch E | Reserved future scope (reasoning_engine consumption) — **but see §7** |
| New MAANI family | Requires Vector-specific SPEC + RULE_LOCK |
| Versebyverse loop | Distracts from architectural gaps; not the right default |
| Tafsir / fiqh layer | Out of project scope entirely |
| Quran-wide run | Only after per-family stabilization (Gap 9) |
| `construction_rules.jsonl` bulk migration | Explicitly forbidden track |
| External sources (Ibn Hisham, Ibn Aqil, Suyuti, Ar-Radhi) | MAANI is Samarrai-only |
| Modern Arabic sources | Out of MAANI's source restriction |

---

## 6. Recommended-next-step policy (binding for Claude)

Before recommending any next batch, Claude must answer:

1. **Which current gap does this batch close?** (Reference §4 by Gap number.)
2. **Is it the smallest batch that closes that gap?** If not, propose the smallest viable subset.
3. **Does it preserve all four invariants?**
   - لا إزالة للتشكيل
   - لا تخزّن ما تستطيع توليده
   - no silent ProofKind upgrade
   - Zero over unsafe guessing
4. **Does it require SPEC first?** Default = yes.
5. **What files are likely to be touched?** (Concrete allow-list.)
6. **What is explicitly out of scope?** (Concrete forbidden list + the §5 do-not-open-now list.)
7. **What would count as finished?** (Concrete acceptance criteria.)

Any recommendation that fails to answer all 7 questions is rejected.

---

## 7. Current recommended next step

**Option A — Phase 5 Batch E SPEC (recommended)**

**What:** Make L8 consume the existing L4/L7 condition/jawab relations for 2:282 so that `ما تَسَلسُل الأَحداث؟` can render conditional structure (e.g., `إِذَا تَدَايَنتُم → فَٱكْتُبُوهُ` as a conditional dependency, not a flat sequence).

**Why this is the recommended next step:**

- Closes **Gap 1** (the highest-priority remaining gap).
- The L4/L7 bridge is already implemented (Batch B closed); L8 consumption is the natural next consumer in Phase 5's planned rollout (Batch E per original Phase 5 SPEC §7).
- The most visible remaining gap to a project user is that L8 doesn't yet leverage the structural knowledge that L4/L7 already have. Closing this gap makes the architectural payoff of Batch B visible.
- It is closer to the project aim (auditable reasoning over conditional structure) than opening a new grammar family.
- It honors the Phase 5 batch-rollout governance — each batch authorized separately under its own SPEC.

**Strict scope (for the SPEC, when authorized):**

- SPEC only at first; no implementation.
- 2:282 first إِذَا only (carries forward SHART_JAWAB's pilot scope).
- No new L4 relation extraction (Batch B already did that).
- No MAANI work.
- No MASAQ work.
- No L1/L2/L3 changes.
- No L6 changes.
- No broad conditional grammar.
- Reuse Phase 5 isolation discipline: `reasoning_engine.py` would become the next allow-list entry, narrowed and asserted.

**Alternative if you prefer stabilization first:**

**Option B — MASAQ-guided L1/L2/L3 stabilization SPEC for known false classifications**

Close Gap 4 + Gap 5 partially by writing a SPEC that lists, for example, the `تَدَايَنتُم` Form-VI segmentation issue + 2-3 other concrete L3 wazn/role mismatches observed in 2:282. Tighten one family at a time. Strict scope: SPEC only; per-issue test cases; no broad MASAQ sweep.

**Either option requires explicit approval before SPEC drafting begins. Do not start either silently.**

---

## 8. Update protocol

After every completed batch or major decision, this file MUST be updated.

Update must include:

- New commit hash (and merge commit if a PR was merged).
- What changed (1–2 sentences per affected track).
- What Gap was closed (reference §4 by Gap number).
- What Gap remains (if the closure is partial).
- Test results (suite names + pass counts).
- Whether the four invariants were preserved.
- The next recommended step (§7) refreshed.

Claude must **not** allow this file to become a dumping ground. It must remain a **concise operational map**. If a section is growing too large, archive details into a per-batch report and keep only the summary line here.

---

## 9. Final rule

Do not say **"finished"** unless **all** of the following are true:

1. The current batch is committed and pushed.
2. The report is committed (if the batch's RULE_LOCK required one).
3. Working tree is clean except `.claude/`.
4. `WHERE_WE_ARE.md` is updated to reflect the new state, **or** the user has explicitly deferred the update.
5. The next step is clearly stated in §7, **or** the user has explicitly requested STOP.

If any of these is missing, the work is **not** finished — it is in-progress. Report it as such.
