# MAANI Batch A — Implementation Report

> **Date:** 2026-05-28
> **RULE_LOCK:** [`MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md`](./MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md)
> **Predecessor SPEC:** [`MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md`](./MAANI_CONSUMPTION_ENHANCEMENT_SPEC_DRAFT.md)

## Summary

Batch A had three rules. Their landing status:

| Rule | What | Status |
|---|---|---|
| **A2** | Gate extension: `JAZM_LAM_AMR` + `SHART_LAM_JAWAB` require ل with `LAM_AL_AMR` / `PREP` tag | **Already in tree** as PATCH 14 (commit `bec29fb`) — no work needed |
| **A1** | New `samarrai_operator_meaning` edge in MeaningGraph for surviving prep-topic claims | Implemented in `meaning_assembler.py` (this commit) |
| **A3** | Stamp `modality="ikhtisas"` on event node when `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` fires | Implemented in `meaning_assembler.py` (this commit) |

## Files changed in this commit

| File | Lines | Purpose |
|---|---|---|
| `clean_code/meaning_assembler.py` | +47 / −0 | A1 + A3 — single block inside existing `if self.samarrai_analyze:` of `assemble()` step 6. Adds gate import, new edge_type `samarrai_operator_meaning`, and modality stamp on TAQDIM verb event. |
| `clean_code/test_production_path_segmentation.py` | +96 / 0 | 3 new tests + ALL registration: `t_2_196_lillahi_lam_topics_dropped`, `t_2_282_bidaynin_has_operator_meaning_edge`, `t_1_5_nabudu_event_has_ikhtisas_modality`. |
| `docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md` | +203 (new) | Binding RULE_LOCK for Batch A. |
| `docs/specs/MAANI_BATCH_A_REPORT.md` | +83 (new) | This file. |

**Not touched (constitutional):** `segmenter.py`, `i3rab_engine/*`, `relation_extractor.py`, `event_extractor.py`, `resolution_engine.py`, `alasmaa/*`, `samarrai_analyzer.py`, any CSV under `data/contracts/maani/`, `linguistic_source_registry.py`.

**Not touched in this commit (separate workstream):** `samarrai_certified_operator_gate.py` (A2 is already at HEAD per PATCH 14).

## Sandbox verification

### Test suite

```
python3 test_production_path_segmentation.py
→ Result: 95/95 passed
```

Two of the three new tests are sandbox-skipped (A1, A3) because they
need the full `MeaningAssembler` stack which loads `wazn_data`. They
will run for real on the user's machine. The third (A2 verification)
runs fully in sandbox and passes.

### A2 direct verification on `لِلَّهِ`

```
BEFORE gate: 13 claims, 13 non-Zero
AFTER  gate:  0 non-Zero claims remain
  ✓ DROPPED  JAZM_LAM_AMR/LAM_AMR              → topic_JAZM_LAM_AMR_requires_ل(LAM_AL_AMR) in_L1_prefix_tags
  ✓ DROPPED  SHART_LAM_JAWAB/LAM_JAWAB_LAW     → topic_SHART_LAM_JAWAB_requires_ل(PREP) in_L1_prefix_tags
  ✓ DROPPED  SHART_LAM_JAWAB/LAM_JAWAB_QASAM   → topic_SHART_LAM_JAWAB_requires_ل(PREP) in_L1_prefix_tags
  ✓ DROPPED  SHART_LAM_JAWAB/LAM_IBTIDA        → topic_SHART_LAM_JAWAB_requires_ل(PREP) in_L1_prefix_tags
```

## Acceptance step (user's action)

Per the RULE_LOCK's binding criteria, please run on your machine after committing:

```bash
cd ~/fractal/hussein/clean_code

# 1. Full test suite must show 95+/95+ — including the 2 sandbox-skipped tests now running for real
python3 test_production_path_segmentation.py

# 2. لِلَّهِ in 2:196 must NOT show any lam-jussive/jawab reading
python3 analyze_verse_v3.py --verse 2:196 --samarrai | grep -A 5 'لِلَّهِ'

# 3. بِدَيْنٍ in 2:282 must have a samarrai_operator_meaning edge
python3 analyze_verse_v3.py --verse 2:282 --meaning

# 4. نَعْبُدُ event in 1:5 must carry modality=ikhtisas
python3 analyze_verse_v3.py --verse 1:5 --meaning
```

### Rejection cases (reject Batch A if any of these fire)

- `لِزَيدٍ` or any real PREP-لِ word loses its `PREP_LAM` reading.
- The 95 existing tests regress.
- `بِدَيْنٍ` does NOT get a `samarrai_operator_meaning` edge.
- `نَعْبُدُ` event does NOT carry `modality=ikhtisas`.
- Any duplicate `MeaningEdge.edge_id` raised.

## Commit instructions

> **Important:** the working tree also contains uncommitted changes to
> `clean_code/resolution_engine.py` from an in-progress PATCH 15
> (cross-verse L6 safety gates). Those belong to a **separate** commit.
> The commands below stage **only** Batch A files.

```bash
cd ~/fractal/hussein
rm -f .git/index.lock

git add clean_code/meaning_assembler.py \
        clean_code/test_production_path_segmentation.py \
        docs/specs/MAANI_CONSUMPTION_ENHANCEMENT_RULE_LOCK.md \
        docs/specs/MAANI_BATCH_A_REPORT.md

git diff --cached --stat
# Expected: 4 files changed

git commit -m "MAANI Batch A: samarrai_operator_meaning edge + ikhtisas modality

Two narrow changes to clean_code/meaning_assembler.py inside the existing
step-6 Samarrai block. Both gated by ProofObject discipline.

A1 — samarrai_operator_meaning edges
  After the certified-operator gate filters surviving claims, iterate
  ta.words[i].claims and add one MeaningEdge per surviving claim whose
  topic_id is in {PREP_BA, PREP_KAF, PREP_LAM, PREP_WAW}. edge_type is
  the new 'samarrai_operator_meaning' (distinct from the existing
  fallback 'operator_meaning' bucket used for non-passthrough relations).
  source==target convention for self-attribution edges.

A3 — ikhtisas modality on event node
  When a construction match has construction_id ==
  'TAQDIM_AL_MA3MOOL_LI_IKHTISAS', find the event node at span_words[1]
  and stamp attributes['modality']='ikhtisas' plus a modality_source
  citing volume/page. Single break after first match.

A2 (gate extension) is already at HEAD as PATCH 14 (commit bec29fb).
This commit does NOT touch samarrai_certified_operator_gate.py.

Test: test_production_path_segmentation.py → 95/95 in sandbox.
Two new tests (t_2_282_bidaynin_has_operator_meaning_edge,
t_1_5_nabudu_event_has_ikhtisas_modality) sandbox-skip due to
MeaningAssembler requiring wazn_data; they will run on user machine.
Third new test (t_2_196_lillahi_lam_topics_dropped) runs fully in
sandbox and passes.

Not touched: segmenter.py, i3rab_engine/, relation_extractor.py,
event_extractor.py, resolution_engine.py, alasmaa/,
samarrai_analyzer.py, data/contracts/maani/, linguistic_source_registry.py.

Constitutional discipline: no new schema fields, no edge_type
collisions, single-block change scoped to step 6 of assemble()."

git log --oneline -3
```

## Known follow-ups (deferred — out of Batch A scope)

1. **Per-word claim reach beyond 4 prep-topics:** A1's whitelist is
   intentionally minimal. Future Batch B may add `SHART_*` (after
   gate extension), `RELATIVE`, `DEMONSTRATIVE` once a per-topic risk
   analysis is RULE_LOCKed.
2. **Construction node enrichment:** The 2-row `constructions/patterns.csv`
   only covers `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` and `TAHZHEER_BASIC`.
   `maani_alnahw/.../construction_rules.jsonl` has 1,043 candidates;
   migrating any of them is a separate JSONL→CSV RULE_LOCK exercise.
3. **NAA operators_catalog:** Still unwired. Awaits a Batch C decision
   on how to reconcile with SAM's deeper readings (per the SPEC §6).
4. **Hidden-pronoun thread:** still parked at SPEC stage. Independent
   from this batch.
