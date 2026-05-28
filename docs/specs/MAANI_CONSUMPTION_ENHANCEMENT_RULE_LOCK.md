# MAANI CONSUMPTION ENHANCEMENT — RULE_LOCK (Batch A)

> **Status:** BINDING — Batch A only.
> **Date:** 2026-05-28
> **Predecessor SPEC:** [`MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md`](./MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md)
> **Approval:** User said «start by Batch A» on 2026-05-28.

This RULE_LOCK binds **three** narrow changes. Anything outside this contract is rejected.

---

## Hard boundaries (must hold)

1. **Files allowed to change in this commit:**
   - `clean_code/samarrai_certified_operator_gate.py`  (A2 — 2 new dict entries)
   - `clean_code/meaning_assembler.py`  (A1 + A3 — single loop addition in step 6)
   - `clean_code/test_production_path_segmentation.py`  (3 new tests + registration)
   - `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md`  (this file)
   - `docs/specs/MAANI_BATCH_A_REPORT.md`  (the short report)

2. **Files that MUST NOT change:**
   - `segmenter.py`
   - `i3rab_engine/*`
   - `relation_extractor.py`
   - `event_extractor.py`
   - `resolution_engine.py`
   - `alasmaa/*`
   - `samarrai_analyzer.py`  (no new prefix-strip heuristics)
   - any file under `data/contracts/maani/*` (no CSV row additions in this batch)
   - `linguistic_source_registry.py`

3. **Schema discipline:**
   - No new fields on `MeaningNode` or `MeaningEdge`.
   - No new edge_type collisions: the existing fallback bucket
     `edge_type="operator_meaning"` (lines 231, 250 of
     `meaning_assembler.py`) is RESERVED — A1 uses the distinct name
     `samarrai_operator_meaning`.
   - No change to `ConstructionMatch` / `SamarraiClaim` dataclasses.

4. **No generalisation:**
   - A2 adds exactly two map entries — no other lam-topics.
   - A1's new edge writes only when the surviving claim has the four
     "always-safe" topics: `PREP_BA`, `PREP_KAF`, `PREP_LAM` (after A2),
     `PREP_WAW`. Other topics are skipped in this batch.
   - A3 fires only for `construction_id == "TAQDIM_AL_MA3MOOL_LI_IKHTISAS"`.

---

## Rule A2 — Gate extension for lam-jussive / lam-jawab

### File
`clean_code/samarrai_certified_operator_gate.py`

### Exact change
In the `_PREFIX_REQUIRED` dict (currently lines 69–76), add two new entries:

```python
# Lam-jussive (لِام الأَمر) — requires segmenter's LAM_AL_AMR prefix tag.
"JAZM_LAM_AMR":     ("ل", {"LAM_AL_AMR"}),
# Lam-jawab (لام جواب القَسَم / لام جواب لو / لام الِابتداء)
# — requires the segmenter to have peeled ل with PREP tag.
"SHART_LAM_JAWAB":  ("ل", {"PREP"}),
```

### Why this is safe
- Both keys are already present as `topic_id` in the SAM CSV
  (`volume4/jussive_particles.csv` for the first;
  `volume4/shart_constructions.csv` for the second).
- Default-allow gate behavior is preserved for every OTHER topic.
- Existing rule R2 simply consults the dict and drops the claim if the
  tag is absent; behavior on real لِ-clitics (`لِزَيدٍ`, `لِكِتابٍ`)
  is unchanged because L1 peels their ل with `PREP`.
- The `لِلَّهِ` regression scenario: L1 treats `الله` atomically,
  so `prefixes=[]`. After A2, the four lam-readings (`LAM_AMR`,
  `LAM_JAWAB_LAW`, `LAM_JAWAB_QASAM`, `LAM_IBTIDA`) on this word
  will be rejected by the gate. Each rejection records its own
  blocker `topic_*_requires_ل(...)`.

### Smoke target
Word `لِلَّهِ` in `وَأَتِمُّوا الْحَجَّ وَالْعُمْرَةَ لِلَّهِ ...` (2:196).

---

## Rule A1 — `samarrai_operator_meaning` edge in MeaningGraph

### File
`clean_code/meaning_assembler.py`

### Exact change
Inside the existing `if self.samarrai_analyze:` block of `assemble()`
(step 6, currently starts at line 263), AFTER the `for cm in
ta.constructions:` loop closes and BEFORE the outer `except Exception:`
catch closes, add **one** new nested loop that iterates per-word claims:

```python
# 6b. PATCH MAANI Batch A — A1: per-word operator_meaning edges.
# Promote surviving (post-gate) Samarrai claims to typed edges so they
# reach Reasoning Phase G. Scoped to the 4 prep-letter topics already
# governed by the certified-operator gate. Other topics stay display-only.
try:
    from samarrai_certified_operator_gate import gate_text_analysis
    gate_text_analysis(ta)
except Exception:
    pass  # gate unavailable → fall through; claims remain ungated
_A1_ALLOWED_TOPICS = {"PREP_BA", "PREP_KAF", "PREP_LAM", "PREP_WAW"}
for wa in ta.words:
    if wa.position < 0 or wa.position >= len(sent.tokens):
        continue
    token_id = f"t{wa.position}"
    for c in wa.claims:
        if c.proof_kind == "Zero":
            continue
        if c.topic_id not in _A1_ALLOWED_TOPICS:
            continue
        edge_id = f"sam_op_{wa.position}_{c.topic_id}_{c.meaning_id}"
        graph.add_edge(MeaningEdge(
            edge_id=edge_id,
            edge_type="samarrai_operator_meaning",
            source=token_id,
            target=token_id,  # self-attribution (no second node)
            operator=c.operator,
            proof_kind=c.proof_kind,
            contract=c.contract or "SamarraiClaim:v2",
            source_of_claim=(
                f"السامرَّائيّ ج{c.source_part}/ص{c.source_page} "
                f"[{c.topic_id}/{c.meaning_id}]"
            ),
        ))
```

### Why this is safe
- A1 calls `gate_text_analysis(ta)` so claims rejected by A2 (and by
  every existing gate rule) never become edges.
- Topics are explicitly whitelisted (`_A1_ALLOWED_TOPICS`) — no other
  SAM topics produce edges in Batch A. Future batches can expand.
- The edge_type `samarrai_operator_meaning` is NEW — it does not
  collide with the existing fallback `operator_meaning` bucket.
- `source == target` is a deliberate convention for self-attribution
  edges (the operator's meaning attaches to itself). Display/Reasoning
  layers that iterate edges by `source != target` continue to work.
- If `wa.position` is out of bounds (defensive), the iteration is
  skipped.

### Smoke target
Word `بِدَيْنٍ` in `إِذَا تَدَايَنْتُمْ بِدَيْنٍ ...` (2:282). Expected: at least one new edge with `edge_type="samarrai_operator_meaning"` and `source_of_claim` mentioning ج3.

---

## Rule A3 — `modality="ikhtisas"` on event node from TAQDIM construction

### File
`clean_code/meaning_assembler.py`

### Exact change
Inside the same `for cm in ta.constructions:` loop (step 6, currently
lines 266–294), AFTER the existing `graph.add_node(...)` for the
construction node and AFTER the inner `for pos in cm.span_words: ...`
edge-adding loop, append **one** small block:

```python
# A3: when the construction is TAQDIM_AL_MA3MOOL_LI_IKHTISAS, stamp
# the verb's event node (if any) with modality="ikhtisas". The verb
# is at span_words[1] per detect_constructions in samarrai_analyzer.py.
if cm.construction_id == "TAQDIM_AL_MA3MOOL_LI_IKHTISAS" and len(cm.span_words) >= 2:
    verb_pos = cm.span_words[1]
    for n in graph.nodes:
        if n.node_type in ("event", "transformation") and n.position == verb_pos:
            n.attributes["modality"] = "ikhtisas"
            n.attributes["modality_source"] = (
                f"construction:{cm.construction_id} "
                f"(السامرَّائيّ ج{cm.claim.volume}/ص{cm.claim.source_page})"
            )
            break  # event positions are unique per verb
```

### Why this is safe
- Locked to a single construction_id — no other construction modifies
  any event.
- Mutates only `attributes` on an event node that already exists.
  Does not create new edges, does not change `proof_kind`, does not
  rewire arguments.
- Idempotent: re-running on the same graph re-sets the same two
  attribute keys to the same values.
- `break` after first match — if no event node exists for that
  position (verb wasn't extracted), the block is a no-op.

### Smoke target
Verse `إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ` (1:5).
Expected: event node for `نَعْبُدُ` carries
`attributes["modality"] == "ikhtisas"`.

---

## Tests (3 new, appended to `test_production_path_segmentation.py`)

| Test name | Verifies | Sandbox runnable? |
|---|---|---|
| `t_2_196_lillahi_lam_topics_dropped` | A2: gate drops `JAZM_LAM_AMR` and `SHART_LAM_JAWAB` claims on `لِلَّهِ` | YES (segmenter + gate are both sandbox-callable) |
| `t_2_282_bidaynin_has_operator_meaning_edge` | A1: MeaningAssembler produces ≥1 edge with `edge_type="samarrai_operator_meaning"` on word `بِدَيْنٍ` | NO — needs full assembler stack (i3rab_engine → wazn_data); will skip in sandbox, run on user machine |
| `t_1_5_nabudu_event_has_ikhtisas_modality` | A3: event node for `نَعْبُدُ` carries `attributes["modality"] == "ikhtisas"` | NO — same as above; sandbox-skipped |

Existing 26 tests must remain green.

---

## Acceptance criteria (binding)

After Batch A is committed and user reruns the suite:

1. `python3 test_production_path_segmentation.py` reports **29/29 passed** (2 of which were already sandbox-skipped before this batch; the two new L7 tests will run for real on the user's machine).
2. `python3 analyze_verse_v3.py --verse 2:196 --samarrai`: KB.SAM output for `لِلَّهِ` no longer shows any of `JAZM_LAM_AMR/LAM_AMR`, `SHART_LAM_JAWAB/LAM_JAWAB_LAW`, `SHART_LAM_JAWAB/LAM_JAWAB_QASAM`, `SHART_LAM_JAWAB/LAM_IBTIDA`.
3. `python3 analyze_verse_v3.py --verse 2:282 --meaning`: MeaningGraph stats show ≥1 extra edge compared to pre-Batch-A baseline.
4. `python3 analyze_verse_v3.py --verse 1:5 --meaning`: event node attributes for `نَعْبُدُ` include `modality=ikhtisas`.

### Rejection cases (the patch is REJECTED if any of these fire)
- A real `لِ`-prep word (e.g. `لِزَيدٍ` if it appears in any of the 3 smoke verses) stops getting `PREP_LAM` reading.
- The existing 26 production-path tests show any regression.
- Any `MeaningEdge` collision (two edges with the same `edge_id`).
- `بِدَيْنٍ` does NOT get a `samarrai_operator_meaning` edge.
- `نَعْبُدُ` event does NOT carry `modality=ikhtisas`.
