# Phase 5 — Clause and Sentence Segmentation Specification Draft

> **Status:** DRAFT — discovery + design only. No production code change.
> **Date:** 2026-05-29
> **Scope:** Identify the architectural gap left by Phase 1–4, propose
> an L3.5 Clause Segmentation layer that sits between word-level i3rab
> (L3) and relation/event extraction (L4/L5), and specify a conservative
> Batch A rule set that can run standalone without altering any
> downstream layer.
> **This document is the deliverable. No code, no tests, no generated
> outputs accompany it.**

---

## 1. Problem statement

The production pipeline today is word-anchored end to end:

| Layer | Unit | What it produces |
|---|---|---|
| L1/L2 | token | segmented surface form + morphology |
| L3 | token | i3rab (word_class, case, role, wazn) |
| L4 | token-pair | relations (`agent_of`, `patient_of`, …) |
| L5 | token (verb) | events (one per verb, possibly transformations) |
| L6 | token | resolutions (anaphora, deixis, relative) |
| L7 | graph | MeaningGraph (nodes from L1–L6, edges from L4) |
| L8 | graph | reasoning Q/A |

There is **no independent clause/sentence layer**. The smoking gun is
visible in every L4 output:

```
verb_in_clause : <verb> → —
```

The `→ —` says "this verb belongs to some clause" *but no clause object
exists*. There is no `clause_id`, no start/end token span, no parent
clause, no scope status. Each layer that needs clause structure has
been forced to invent a private, per-call approximation:

| Layer | Private clause workaround | Cost |
|---|---|---|
| L5 `TimeScopeGate` (PATCH 5) | walks left token-by-token, stops on Quranic pause marks reconstructed from `sent.text` re-alignment | every time-adverb scope decision repeats the alignment cost; no shared truth |
| L4 PATCH-7 / PATCH-12 guards | rely on `last_noun_idx`, `last_verb_idx`, surface فَ-of-apodosis heuristics | each guard is local; cross-clause reasoning is impossible |
| L6 PATCH 8/9/10/15/16 gates | reject candidates via single-token features (PP-prefix, possessor-tail, إذا+ما cluster) | cannot ask "is this candidate *outside the relative clause* of ٱلَّذِى?" because the clause isn't represented |
| L8 PATCH-6 Answer-Type Gate | flattens all events across the verse into one bag for "what / who / when" | "ما تَسَلسُل الأَحداث؟" cannot distinguish nested events from coordinated ones |
| Hidden-pronoun signals (PATCH 13) | extractor is read-only because there is no clause to attach a `hidden_subject` slot to | A1's `hidden_subject = هو` resolved from i3rab text cannot flow to an L5 event's `agent` field without inventing a per-clause anchor |

### Direct consequences observed on 2:282 / 2:196 evidence

- **Time scope is approximated by pause-mark walks.** PATCH 5 had to
  rebuild pause positions from `sent.text` because the i3rab tokenizer
  drops them. A clause layer would replace this with a one-time lookup.
- **Condition / answer-of-condition is invisible.** `إِذَا تَدَايَنتُم
  بِدَيْنٍ ... فَٱكْتُبُوهُ` produces independent L5 events for
  تَدَايَنتُم and فَٱكْتُبُوهُ with no link saying فَٱكْتُبُوهُ is the
  *jawab* of the إذا condition. L8 "ما تَسَلسُل الأَحداث؟" can only
  list verbs left-to-right.
- **Relative-clause scope is opaque to L6.** PATCH 10 had to add the
  "ٱلَّذِى → ٱلْحَقُّ rejection" as a per-target abstract-noun blacklist
  rather than the more principled "ٱلْحَقُّ is *inside* ٱلَّذِى's own
  relative clause, so it cannot be its external antecedent."
- **أن + verb complement clauses are not first-class.** Every
  occurrence of أَن يَكْتُبَ / أَن يُمِلَّ / أَن تَكْتُبُوهُ is just
  two unrelated tokens to L4/L5.
- **Lam-al-amr command clauses are correctly tense+mood-tagged at L5
  (PATCH 5)** but the *clause boundary* (where the command starts and
  ends) is implicit — downstream consumers must re-derive it.
- **Hidden pronoun integration (PATCH 13 Batch A, currently
  signal-only)** cannot be wired into L5 agent slots without a clause
  representation: which event's agent slot does `hidden_subject=هو`
  fill? Today the answer is "guess from token position." With a clause
  layer the answer is "the event whose verb is the head of the clause
  the signal was extracted from."

### Why a separate layer (not patches on existing ones)

Every per-layer workaround above has been added defensively, one at a
time, costing ~50–100 LOC each. The accumulated complexity is now
greater than a single clause-segmentation module would be. More
importantly, none of the per-layer workarounds can *combine* — L5's
pause walk cannot inform L6's relative-clause boundary; L6's PATCH 16
abstract-reference heuristic cannot inform L8's sequence answer.

A clause layer is the smallest unit that lets the existing layers stop
re-discovering the same structure independently.

---

## 2. Proposed layer name

**L3.5 Clause Segmentation.**

Justification:

- It must run **after** L1/L2/L3 because clause typing needs word_class
  / role / wazn / aspect from those layers.
- It must run **before** L4 because relations are properly *intra-clause*
  in classical Arabic grammar (e.g., the *faail* of a verb is in the
  same clause as that verb; cross-clause relations like *mudaaf-ilayh*
  require both clauses to exist first).
- A name like "L4a" or "L4 ClauseGraph" implies it's a sibling of
  relation extraction; this misrepresents the dependency. L3.5 makes
  the ordering explicit.
- The fractional name preserves the existing layer numbering (no
  cascading renames in test names, docs, or analyze_verse_v3 section
  headers).

Rejected alternative: **L4a ClauseGraph.** Reads as a relation-layer
sibling and risks the misimpression that clauses are derivable from
relations rather than the other way around.

---

## 3. Target output object

```
Clause(
    clause_id="C001",
    verse="2:282",
    type="condition | condition_answer | command | prohibition |
          relative | complement_an | nominal | verbal | oath |
          apposition | unknown",
    start_token_index=int,            # inclusive, into sent.tokens
    end_token_index=int,              # inclusive
    text="...",                       # joined surface forms in span
    head_token="...",                 # NFC surface of the clause head
    head_kind="verb | operator | noun | particle",
    parent_clause_id="C000 | null",   # nesting (e.g. condition_answer
                                      # is child of condition)
    introduced_by="إذا | إن | من | أن | لا | فـ | و | ...",  # opener
    scope_status="open | closed",     # "open" = unterminated at verse
                                      # end (rare); "closed" = bounded
    confidence="Certificate | Hypothesis | Zero",
    source="PauseBoundaryContract | ConditionalScopeContract |
            AnComplementContract | RelativeClauseContract |
            LamAlAmrCommandContract | DefaultVerbalContract | ...",
)
```

Container:
```
ClauseGraph(
    verse_ref="2:282",
    clauses=[Clause, Clause, ...],   # ordered by start_token_index
    relations=[                       # optional, Batch A may emit empty list
        ClauseRelation(name="answer_of",  source="C003", target="C002"),
        ClauseRelation(name="complement_of", source="C006", target="C005"),
        ClauseRelation(name="relative_of",   source="C0xx", target="C0yy"),
    ],
    source_text="...",
    contract="ClauseGraph:v1",
)
```

Storage location proposal: a new `clean_code/clause_segmentation.py`
plus a `clean_code/clause_schema.py` for the dataclasses (mirroring
the existing `event_extractor.py` / `event_schema.py` split).

---

## 4. Initial Batch A rules only

Batch A is **conservative and read-only**. It produces a `ClauseGraph`
but does NOT mutate `sent.tokens`, `RelationGraph`, `EventGraph`,
`ResolutionGraph`, or `MeaningGraph`.

### Rule A1 — `PauseBoundaryClauseSplit`

- **Trigger:** Quranic pause marks ۚ ۖ ۗ ۙ ۛ ۜ (and the rarer ۘ ۝ ۞)
  in `sent.text`.
- **Action:** Create a candidate clause window between consecutive
  pause-mark positions (aligned via the same `_build_pause_before`
  technique PATCH 5 already uses for time scope).
- **Confidence:** `Hypothesis` by default. A pause is a *hint*; the
  clause type/head is determined by A2–A5 rules. If no other rule
  fires for the window, classify as `nominal` or `verbal` based on
  whether the window contains a FIIL.
- **Negative constraint:** Do NOT treat every pause as a full
  sentence boundary. Long verses (2:282) use pauses inside clauses
  too; a pause that falls inside a recognized conditional scope (A2)
  is kept as an intra-clause boundary only.

### Rule A2 — `ConditionalScopeClause`

- **Trigger:** any of the following as clause-head tokens:
  - `إِذَا` / `إِذ` / `لَمَّا` (time-conditional)
  - `إِنْ` / `فَإِنْ` (hypothetical conditional)
  - `مَنْ` / `فَمَنْ` (relative-conditional for persons)
  - `مَا` / `فَمَا` (relative-conditional for non-persons)
  - `فَإِذَا` (apodosis-then-conditional)
- **Action:**
  - Open a `condition` clause from the trigger token.
  - Close it at the first ۚ pause OR at the first فَـ-headed clause
    candidate, whichever comes first.
  - If a فَـ-headed candidate follows within the same pause window,
    emit a sibling `condition_answer` clause whose `parent_clause_id`
    points at the condition clause.
- **Worked example (2:282):**
  - `إِذَا تَدَايَنتُم بِدَيْنٍ إِلَىٰ أَجَلٍ مُّسَمًّى` →
    `Clause(type="condition", head_token="إِذَا",
    introduced_by="إِذَا", ...)`
  - `فَٱكْتُبُوهُ` →
    `Clause(type="condition_answer", parent_clause_id="<condition_id>",
    head_token="فَٱكْتُبُوهُ", ...)`
- **Confidence:** `Certificate` when both opener and answer are
  detected; `Hypothesis` if only the condition opener is present.

### Rule A3 — `LamAlAmrCommandClause`

- **Trigger:** any token whose L1 prefix tags include `LAM_AL_AMR`
  (already certified by PATCH 1 / PATCH 5).
- **Action:** Create a `command` clause headed by the verb. Span runs
  from the لْ-bearing token to the next ۚ pause OR the next CONJ-
  opened clause (وَ / فَ on a new lam-al-amr or imperative head),
  whichever comes first.
- **Examples (2:282):** `وَلْيَكْتُب`, `فَلْيَكْتُبْ`, `وَلْيُمْلِلِ`,
  `وَلْيَتَّقِ`, `فَلْيُمْلِلْ` each open their own command clause.
- **Confidence:** `Certificate` (the L1 LAM_AL_AMR tag is itself
  Certificate-grade per PATCH 1).
- **Negative constraint:** Do NOT alter L5 mood / speech_act on these
  events. The clause record exists alongside; existing L5 keeps its
  PATCH-5 `mood=jussive_command, speech_act=command`.

### Rule A4 — `AnComplementClause`

- **Trigger:** token sequence `أَن` (HARF_NASB per PATCH 3D) +
  immediate following imperfect verb (IMPERF_PREF in prefix tags).
- **Action:** Create a `complement_an` clause from `أَن` up to the
  next ۚ pause OR the next clause-opener (whichever earlier). Mark
  `parent_clause_id` as the most recent verb-headed clause to the
  left (parent link kept `Hypothesis` in Batch A — the closest
  verb may or may not be the actual governor).
- **Examples (2:282):** `أَن يَكْتُبَ` (complement of يَأْبَ),
  `أَن يُمِلَّ` (complement of يَسْتَطِيعُ), `أَن تَضِلَّ` (complement
  of an elided causal verb), `أَن تَكْتُبُوهُ` (complement of
  تَسْـَٔمُوٓا), `أَن تَكُونَ` (complement of إِلَّآ).
- **Confidence:** clause itself `Certificate` (segmentation is
  mechanical); parent link `Hypothesis` (needs intra-clause syntax
  to confirm).

### Rule A5 — `RelativeClauseShell`

- **Trigger:** ism-mawsul tokens (per the existing `relative_pronouns.csv`):
  `الذي / الذين / التي / اللذان / اللذين / اللتان / اللتين /
   اللاتي / اللائي / مَن / مَا`.
- **Action:** Open a `relative` clause from the relative pronoun.
  Close it on the next ۚ pause OR the next CONJ-opener (وَ / فَ /
  ثُمَّ) on a verb-headed candidate.
- **Constraint:** Do **NOT** resolve the antecedent here — that
  remains L6's job. Batch A only emits the clause *shell*: span,
  head, type. L6 is unaltered.
- **Confidence:** `Hypothesis`. Distinguishing the relative ـى-form
  مَن from the conditional مَنْ requires diacritic-sensitive context
  that Batch A does not check; over-collection followed by L6's
  existing PATCH-8 gates is acceptable.

---

## 5. Example expected segmentation for 2:282 (illustrative)

```
C001  type=vocative/opening      span=(0..2)   head=يَٰٓأَيُّهَا
      text: «يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوا»

C002  type=condition             span=(3..9)   head=إِذَا   introduced_by=إِذَا
      text: «إِذَا تَدَايَنتُم بِدَيْنٍ إِلَىٰ أَجَلٍ مُّسَمًّى»

C003  type=condition_answer      span=(10..10) head=فَٱكْتُبُوهُ
      parent=C002    introduced_by=فَـ
      text: «فَٱكْتُبُوهُ»

C004  type=command               span=(12..15) head=وَلْيَكْتُب
      text: «وَلْيَكْتُب بَّيْنَكُمْ كَاتِبٌ بِٱلْعَدْلِ»

C005  type=prohibition           span=(17..19) head=وَلَا يَأْبَ
      text: «وَلَا يَأْبَ كَاتِبٌ»

C006  type=complement_an         span=(20..21) head=أَن
      parent=C005    introduced_by=أَن
      text: «أَن يَكْتُبَ»

C007  type=manner/comparison     span=(22..24) head=كَمَا
      text: «كَمَا عَلَّمَهُ ٱللَّهُ»

C008  type=command               span=(26..26) head=فَلْيَكْتُبْ
      text: «فَلْيَكْتُبْ»

C009  type=command               span=(27..30) head=وَلْيُمْلِلِ
      contains relative-shell C009a (head=ٱلَّذِى) over span=(28..30)
      text: «وَلْيُمْلِلِ ٱلَّذِى عَلَيْهِ ٱلْحَقُّ»

C010  type=command               span=(31..33) head=وَلْيَتَّقِ
      text: «وَلْيَتَّقِ ٱللَّهَ رَبَّهُ»

C011  type=prohibition           span=(35..38) head=وَلَا يَبْخَسْ
      text: «وَلَا يَبْخَسْ مِنْهُ شَيْـًٔا»
```

(Token indices are placeholders; the actual indices come from
`sent.tokens` at runtime. Verse 2:282 continues past C011; the
illustration stops at the first major pause group to keep the
example readable.)

The single sample establishes the shape, not the full segmentation;
implementing Batch A would produce ~20–25 clauses for the full 2:282
verse based on a back-of-envelope count of pauses + lam-al-amr +
أن-complements + relative pronouns.

---

## 6. Required non-goals

This SPEC explicitly does NOT propose any of the following in Batch A:

- **No change to tokenization.** `segmenter.py` is untouched.
- **No change to morphology.** `i3rab_engine/layer1.py`/`layer2.py`
  are untouched.
- **No change to i3rab.** `i3rab_engine/layer3.py` is untouched.
- **No change to L4 relations.** `relation_extractor.py` is untouched.
  In particular, the existing `verb_in_clause : <verb> → —` lines
  remain unchanged in Batch A. Wiring clause IDs into L4 is Batch B.
- **No change to L5 events.** `event_extractor.py` is untouched. The
  existing PATCH-5 mood/time/scope behavior is unchanged. Wiring
  clause scope into TimeScopeGate is Batch C.
- **No change to L6 resolution.** `resolution_engine.py` is untouched.
  All PATCH 8/9/10/15/16 gates remain in force. Using clause spans to
  improve relative-antecedent search is Batch D.
- **No hidden-pronoun integration.** `hidden_pronoun_signals.py` is
  untouched. The signal extractor stays read-only. Wiring signals to
  clause-anchored event agents is Batch D.
- **No MAANI Rule A1/A3 implementation.** Those are tracked
  separately in `MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md`.
- **No MeaningGraph change.** `meaning_assembler.py` is untouched.
  Clause nodes can be added to L7 in a future batch but not in A.
- **No L8 reasoning change.** `reasoning_engine.py` is untouched.
- **No KB.SAM change.** `samarrai_certified_operator_gate.py` and
  `samarrai_analyzer.py` are untouched.

The Batch A module produces a `ClauseGraph` and exposes a
`segment_into_clauses(sent)` entry point. Nothing in the rest of the
codebase imports it in Batch A.

---

## 7. Future consumption plan

Batches B–E are speculative scopes for future review. They are **NOT**
authorized by this SPEC; each requires its own SPEC + RULE_LOCK +
approval.

| Batch | Consumer | What it does |
|---|---|---|
| **B** | `relation_extractor.py` | Stamp every emitted relation with `clause_id` (source-token's clause). Add inter-clause relations like `agent_of_in_clause`. Replace `verb_in_clause : <verb> → —` with `verb_in_clause : <verb> → <clause_id>`. |
| **C** | `event_extractor.py` + TimeScopeGate | Replace PATCH-5's per-call pause-walk with a clause-window lookup. Add `Event.clause_id` and `Event.parent_clause_id` so L5 sequence reasoning can distinguish coordinated events (sibling clauses) from nested events (parent-child). |
| **D** | `hidden_pronoun_signals.py` → `event_extractor.py` | Wire each `HiddenPronounSignal` to the event whose verb is the head of the same clause as the signal source. Use this to fill `event.agent` when no explicit `agent_of` relation exists. (Closes the Batch B/C gap identified in the hidden-pronoun spec §4.4.) |
| **E** | `reasoning_engine.py` (L8) | Use ClauseGraph to answer "ما تَسَلسُل الأَحداث؟" with proper nesting: parent-clause events bracketing child-clause events. Use condition/answer pairs to answer "ماذا يَجِب لو …؟". |

Each batch is independent — Batch B can land before Batch C without
forcing the others. The shared dependency is only the Batch A clause
module itself.

---

## 8. Test plan (proposed — NOT to be implemented in this SPEC)

Smoke tests Batch A would justify on the existing 2:282 corpus:

```
t_clause_2_282_has_at_least_n_clauses
  # 2:282 produces ≥ 18 clause objects (lower bound, allowing
  # cautious segmentation; the full count is closer to ~22-25).

t_clause_2_282_all_lam_al_amr_verbs_are_command_heads
  # وَلْيَكْتُب, فَلْيَكْتُبْ, وَلْيُمْلِلِ, فَلْيُمْلِلْ, وَلْيَتَّقِ
  # each head exactly one Clause(type="command").

t_clause_2_282_idha_condition_with_fa_answer
  # «إِذَا تَدَايَنتُم ... فَٱكْتُبُوهُ»:
  #   - exactly one Clause(type="condition", head=إِذَا)
  #   - exactly one Clause(type="condition_answer",
  #       parent_clause_id=<that condition's id>)

t_clause_2_282_an_complement_clauses
  # أَن يَكْتُبَ, أَن يُمِلَّ, أَن تَضِلَّ, أَن تَكْتُبُوهُ, أَن تَكُونَ
  # each produce a Clause(type="complement_an").

t_clause_relative_shell_alladhi
  # ٱلَّذِى عَلَيْهِ ٱلْحَقُّ produces a Clause(type="relative",
  #   head=ٱلَّذِى) spanning ٱلَّذِى ... ٱلْحَقُّ. No L6 change.

t_clause_no_production_path_change
  # Same guard pattern as PATCH 13: grep clean_code/ for any consumer
  # of `clause_segmentation`. Must be empty in Batch A.

t_clause_module_standalone
  # The module imports without pulling segmenter / i3rab_engine
  # internals beyond what `engine.analyze_sentence().tokens` already
  # exposes. Confirms Batch A is genuinely additive.
```

All seven smoke tests are *guard tests* in the same vein as the PATCH
13 production-isolation test (`t_patch13_no_production_path_change`).
They verify the layer exists and is correctly isolated, not that the
rest of the pipeline has begun consuming it.

---

## 9. Governance

- This document is a **SPEC draft only**.
- **No production code is changed** by this SPEC.
- **No tests are added or modified** by this SPEC.
- **No generated JSONL or CSV outputs** accompany this SPEC.
- Implementation must be reviewed as **Phase 5 Batch A**, not as
  "PATCH 17." The stabilization track (PATCH 0–16) is closed. Phase 5
  opens a new track with its own RULE_LOCK that this SPEC will
  eventually feed.
- Batches B–E in §7 are speculative and require their own SPECs.
- The author of any Batch A implementation must explicitly verify that
  `clean_code/segmenter.py`, `clean_code/i3rab_engine/*`,
  `clean_code/relation_extractor.py`, `clean_code/event_extractor.py`,
  `clean_code/resolution_engine.py`, `clean_code/reasoning_engine.py`,
  `clean_code/meaning_assembler.py`,
  `clean_code/hidden_pronoun_signals.py`, and
  `clean_code/samarrai_certified_operator_gate.py` remain unchanged
  after Batch A lands.

### Author's stopping point

This document is the entire deliverable for this round. After
writing it, the implementation action is `git status` to confirm only
this file changed, then **stop**. Do not commit. Do not stage. Do not
draft Batch A implementation in the same pass.
