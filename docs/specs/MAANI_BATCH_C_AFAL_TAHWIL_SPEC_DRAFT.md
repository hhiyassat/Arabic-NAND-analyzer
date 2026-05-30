# MAANI Batch C — أَفعال التَّحويل / AFAL_AL_TAHWIL — SPEC DRAFT

> **Type:** SPEC draft (not RULE_LOCK).
> **Date:** 2026-05-30
> **Status:** Draft pending review. No implementation. No RULE_LOCK yet.
> **Source restriction:** Samarrai only. No external scholars. No modern Arabic.

---

## 1. Problem statement

MAANI currently encodes Samarrai's **cognitive two-object verbs** (ZANN family: ظَنَّ, حَسِبَ, خَالَ, زَعَمَ, عَلِمَ, رَأَى, وَجَدَ, أَلْفَى — `data/contracts/maani/volume2/zann_family_meanings.csv`, 16 rows). These verbs take two accusative objects expressing **predication under modal/cognitive operators** (verb + obj₁ + obj₂ where obj₂ is a property attributed to obj₁ under belief/perception).

A **sibling family** discussed by Samarrai in volume 2 is **not yet encoded**: the **transformation verbs** (أَفعال التَّحويل / التَّصيير). These verbs share the same structural shape (two accusative objects) but carry a different modality — **causative transformation**: subject *makes* obj₁ *become* obj₂. The semantic relation is transformation, not belief.

The asymmetry creates a gap: a reader of `وَاتَّخَذَ ٱللَّهُ إِبْرَاهِيمَ خَلِيلًا` ("And Allah took Ibrahim as a close friend" — النساء 125) receives no MAANI operator-meaning support, even though Samarrai documents the construction.

**Batch C's narrow goal**: add the framework row + the 3 most canonical transformation verbs (جَعَلَ, اِتَّخَذَ, صَيَّرَ) as 4 new CSV rows in a sibling file alongside the existing ZANN CSV.

---

## 2. Source evidence

### 2.1 Primary source: curated rule card

`maani_alnahw/data/processed/maani_alnahw/rule_cards.jsonl` — row with `rule_id = "AFAL_AL_TAHWIL__P2_001"`.

**Provenance** (from the rule card's `source` field):
- Book: «معاني النحو»
- Author: فاضل صالح السامرائي
- Volume (part): **2**
- Page range: **pp. 26 – 279**

**Confidence** (from the rule card): **0.93**

**Author position** (from the rule card): `"السَّامَرَّائيّ يُفَرِّق المَعاني المُتَعَدِّدَة لِـ جَعَل"` — the author distinguishes the multiple readings of جَعَل (transformation vs creation vs belief). This warning translates directly into a `warnings` column entry on the جَعَلَ row.

### 2.2 Rule card content (verbatim, for traceability)

**Trigger:**
- `type = "verb_class"`
- `lemmas = [جعل, اتخذ, ترك, صير, رد, تخذ, وهب]` *(Batch C consumes the first 3 of the canonical 4: جعل, اتخذ, صير; the rest are deferred.)*
- `construction_parent = "ZANN_WA_AKHAWATUHA"` *(confirms sibling relationship with the already-implemented ZANN family.)*

**Syntactic effect:**
- `valency = 2`
- `case_pattern = "accusative + accusative"`
- `first_object`: المَفعول الأَوَّل: الَّذي يُحَوَّل
- `second_object`: المَفعول الثَّاني: الحالَة الجَديدَة

**Semantic effect:**
- `relation = "transformation"`
- `deep_structure = "object_1 صارَ object_2 بِفِعل الفاعِل"`
- `modality = "causative_transformation"`

**Conditions:**
1. أَن يَكون الفِعل دالًّا على نَقل المَفعول الأَوَّل لِحالَة جَديدَة
2. أَن يَكون المَفعول الثَّاني هُو الحالَة لا الذَّات

**Exceptions / warnings:**
1. جَعَل تَأتي بِمَعنى التَّحويل وَ بِمَعنى الخَلق وَ بِمَعنى الاعتِقاد — السِّياق يُحَدِّد
2. اتَّخَذ بِمَعنى التَّحويل تَكون لِمَفعولَين، وَ بِمَعنى الأَخذ لِمَفعول واحِد

**Examples** (the rule card carries 3, two of which are Quranic — both are used as Batch C example anchors):

| # | text | first object | second object | Quranic source |
|---|---|---|---|---|
| 1 | جعلت الطين خزفًا | الطين | خزفًا | (constructed) |
| 2 | وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا | إِبْرَاهِيمَ | خَلِيلًا | النساء : 125 |
| 3 | وَجَعَلْنَا مِنْهُمْ أَئِمَّةً يَهْدُونَ | مِنْهُمْ | أَئِمَّةً | السجدة : 24 |

The rule card does not provide a Quranic anchor specifically for صَيَّرَ, so Batch C uses a constructed example for that row (or leaves `example_quran` empty — see §4 row design).

---

## 3. Proposed CSV

**Path**: `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv`

**New file** (does not exist today). Sibling to:
- `clean_code/data/contracts/maani/volume2/zann_family_meanings.csv` (16 rows, already shipped)
- `clean_code/data/contracts/maani/volume2/fail_naib_meanings.csv` (10 rows)
- `clean_code/data/contracts/maani/volume2/mafool_bih_meanings.csv` (8 rows)
- `clean_code/data/contracts/maani/volume2/mafool_mutlaq_meanings.csv` (8 rows)

After Batch C ships, `volume2/` will contain 5 files / 46 rows (was 4 / 42).

---

## 4. Proposed rows (exactly 4)

All rows use `topic_id = "AFAL_TAHWIL"`. All cite `source_part=2`. All carry `confidence` derived from the rule card's `0.93` (with framework slightly higher at `0.95` matching ZANN's framework row precedent).

### Row 1 — Framework

| column | value |
|---|---|
| `priority` | `1` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `—` |
| `vocalized_form` | `—` |
| `meaning_id` | `AFAL_TAHWIL_BASIC` |
| `meaning_ar` | `أفعال التحويل / التصيير — أَفعال تَنقُل المَفعول الأَوَّل إلى حالَة جَديدَة هي المَفعول الثَّاني` |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `conditions` | `أَن يَكون الفِعل دالًّا على نَقل المَفعول الأَوَّل لِحالَة جَديدَة \| أَن يَكون المَفعول الثَّاني هُو الحالَة لا الذَّات` |
| `exceptions` | `بَعض هذه الأَفعال لَها مَعانٍ أُخرى غَير التَّحويل — السِّياق يُحَدِّد` |
| `warnings` | `سِبلِنغ بَنية لِـ ZANN_FAMILY (مَفعولان مَنصوبان) — يَتَمَيَّز عَنها بِالمُوداليتي (تَحويل لا اعتِقاد)` |
| `example_constructed` | `جَعَلْتُ الطِّينَ خَزَفًا` |
| `example_quran` | `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` |
| `surah_ayah` | `النساء:125` |
| `author_position` | `preferred` |
| `disagreement` | (empty) |
| `source_part` | `2` |
| `source_page` | `26` |
| `confidence` | `0.95` |

### Row 2 — جَعَلَ (transformation reading)

| column | value |
|---|---|
| `priority` | `2` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `جَعَلَ` |
| `vocalized_form` | `جَعَلَ` |
| `meaning_id` | `AFAL_TAHWIL_JAAL` |
| `meaning_ar` | `جَعَلَ بِمَعنى التَّحويل / التَّصيير — جَعَلَ X (مَفعول أَوَّل) Y (مَفعول ثانٍ)` |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `conditions` | `أَن يَكون السِّياق دالًّا على التَّحويل لا الخَلق وَ لا الاعتِقاد` |
| `exceptions` | `جَعَلَ بِمَعنى الخَلق (مَفعول واحِد) — مِثل «خَلَقَ» \| جَعَلَ بِمَعنى الاعتِقاد (يَقترِب مِن ZANN_FAMILY)` |
| `warnings` | `جَعَل تَأتي بِمَعنى التَّحويل وَ بِمَعنى الخَلق وَ بِمَعنى الاعتِقاد — السِّياق يُحَدِّد` |
| `example_constructed` | `جَعَلْتُ الطِّينَ خَزَفًا` |
| `example_quran` | `وَجَعَلْنَا مِنْهُمْ أَئِمَّةً يَهْدُونَ` |
| `surah_ayah` | `السجدة:24` |
| `author_position` | `preferred` |
| `disagreement` | `السَّامَرَّائيّ يُفَرِّق المَعاني المُتَعَدِّدَة لِـ جَعَل` |
| `source_part` | `2` |
| `source_page` | `26` |
| `confidence` | `0.93` |

### Row 3 — اِتَّخَذَ (transformation reading)

| column | value |
|---|---|
| `priority` | `3` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `اِتَّخَذَ` |
| `vocalized_form` | `اِتَّخَذَ` |
| `meaning_id` | `AFAL_TAHWIL_ITTAKHATHA` |
| `meaning_ar` | `اِتَّخَذَ بِمَعنى التَّحويل — اِتَّخَذَ X (مَفعول أَوَّل) Y (مَفعول ثانٍ)` |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `conditions` | `أَن يَتَعَدَّى الفِعل لِمَفعولَين (تَحويل) لا لِمَفعول واحِد (أَخذ)` |
| `exceptions` | `اِتَّخَذَ بِمَعنى الأَخذ (مَفعول واحِد) — لا تَنطَبِق هذه القاعِدَة` |
| `warnings` | `اتَّخَذ بِمَعنى التَّحويل تَكون لِمَفعولَين، وَ بِمَعنى الأَخذ لِمَفعول واحِد` |
| `example_constructed` | `اِتَّخَذْتُ زَيدًا صَديقًا` |
| `example_quran` | `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` |
| `surah_ayah` | `النساء:125` |
| `author_position` | `preferred` |
| `disagreement` | (empty) |
| `source_part` | `2` |
| `source_page` | `26` |
| `confidence` | `0.93` |

### Row 4 — صَيَّرَ (transformation reading)

| column | value |
|---|---|
| `priority` | `4` |
| `topic_id` | `AFAL_TAHWIL` |
| `operator` | `صَيَّرَ` |
| `vocalized_form` | `صَيَّرَ` |
| `meaning_id` | `AFAL_TAHWIL_SAYYARA` |
| `meaning_ar` | `صَيَّرَ بِمَعنى التَّحويل — صَيَّرَ X (مَفعول أَوَّل) Y (مَفعول ثانٍ)؛ هو الأَوضَح في الدَّلالَة على التَّحويل` |
| `syntactic_effect` | `nasb_two_objects` |
| `semantic_field` | `causative_transformation` |
| `conditions` | `أَن يَكون المَفعول الثَّاني حالَة جَديدَة لِلمَفعول الأَوَّل` |
| `exceptions` | (empty — صَيَّرَ has the cleanest single reading among the three) |
| `warnings` | `أَوضَح أَفعال التَّحويل دَلالَة — لا يَكاد يَلتَبِس مَع غَيره` |
| `example_constructed` | `صَيَّرْتُ العَدُوَّ صَديقًا` |
| `example_quran` | (empty — the rule card does not anchor صَيَّرَ to a specific verse) |
| `surah_ayah` | (empty) |
| `author_position` | `preferred` |
| `disagreement` | (empty) |
| `source_part` | `2` |
| `source_page` | `26` |
| `confidence` | `0.93` |

---

## 5. Schema

**Existing 19-column schema** (per `data/contracts/maani/schema.md`):

`priority, topic_id, operator, vocalized_form, meaning_id, meaning_ar, syntactic_effect, semantic_field, conditions, exceptions, warnings, example_constructed, example_quran, surah_ayah, author_position, disagreement, source_part, source_page, confidence`

**Batch C uses ALL 19 columns**. No new columns. No new column types. No new conventions.

**New `topic_id` value**: `AFAL_TAHWIL` — added to the topic_id enumeration (consistent with how `ZANN_FAMILY` was added when the ZANN file shipped). Topic IDs are open-set in the schema doc, so this is not a schema change.

---

## 6. Code impact

### 6.1 Data-only batch — preferred outcome

**Prefer zero code changes.** Verify before writing the RULE_LOCK that the existing loader chain auto-discovers a new CSV under `volume2/`:

- `clean_code/samarrai_loaders/volume2_loader.py` is expected to glob `*.csv` under its directory and load all rows. **Confirm this in the next step** before RULE_LOCK.
- If volume2_loader uses a hardcoded file list, the loader must be extended to include `transform_verbs_meanings.csv`. This would be a single-line addition; still within MAANI's allowed scope (`samarrai_loaders` is part of the MAANI consumer surface).

### 6.2 No L1/L2/L3 changes
- `clean_code/i3rab_engine/*` — **not touched**
- `clean_code/master_token_lookup.py` — **not touched**
- `clean_code/segmenter.py` — **not touched**

### 6.3 No gate changes unless investigation proves needed
The new rows are verb-class operators, not prefix-clitic operators. The certified-operator gate (`samarrai_certified_operator_gate.py`) currently has:
- `_PREFIX_REQUIRED`: prefix-letter clitic topics (PREP_BA, PREP_LAM, PREP_KAF, PREP_WAW, SHART_FA_IDH, JAZM_LAM_AMR, SHART_LAM_JAWAB) — `AFAL_TAHWIL` does NOT belong here.
- `_PRONOUN_SUFFIX_LETTERS`: pronoun-suffix topics — not applicable.
- `_STRICT_FORM_TOPICS`: strict-form topics (SHART_IN, JAZM_LA_NAHIYA) — not applicable.

The existing gate's **default-allow** behavior covers `AFAL_TAHWIL` rows correctly. **No gate change planned in Batch C.** Behavior matches how `ZANN_FAMILY` rows are gated today (i.e., default-allow because the ZANN topic is not in any gate filter).

If smoke-testing reveals an unexpected gate interaction, the SPEC will be re-opened before any gate edit. RULE_LOCK will explicitly forbid drive-by gate changes.

### 6.4 No MeaningGraph changes unless existing wiring fails
The Batch A wiring in `meaning_assembler.py` emits `samarrai_operator_meaning` edges for surviving claims whose `topic_id ∈ {PREP_BA, PREP_KAF, PREP_LAM, PREP_WAW}` (per the MAANI Batch A report). **`AFAL_TAHWIL` is NOT in that whitelist.**

Two routing options to evaluate during RULE_LOCK draft:
- **Option 6.4.a (no MeaningGraph change in Batch C)** — `AFAL_TAHWIL` rows survive as `SamarraiClaim` objects but do NOT emit MeaningGraph edges. They are display-only (visible in the SAM panel of `analyze_verse_v3`'s output). This matches the current ZANN behavior — ZANN rows are not in the edge whitelist either, and the system functions correctly.
- **Option 6.4.b (extend whitelist)** — add `AFAL_TAHWIL` to the topic whitelist in step 6b of `meaning_assembler.assemble()`. This is a single-line addition. Risk: the edge emission emits one edge per surviving claim, so any over-fire on a transformation verb token would create a spurious meaning-graph edge.

**SPEC preference: 6.4.a.** Ship display-only first. If downstream consumers (Reasoning Phase G) need the verb-class edges, a follow-up batch can extend the whitelist after smoke evidence.

### 6.5 Loader auto-discovery check (TODO before RULE_LOCK)
Before the RULE_LOCK is written, run a read-only check:
```
python3 -c "from samarrai_loaders.volume2_loader import lookup_word; print(lookup_word('جَعَلَ'))"
```
to confirm whether the loader auto-discovers a new CSV. If yes → data-only batch. If no → minimal loader extension (one-line file-list update or glob change).

---

## 7. ProofKind

**Batch C uses ONLY the existing ProofKind enum** {Certificate, Hypothesis, Zero}. No new values.

Per the established MAANI rules (Batch A + Batch B):
- `Certificate` ← match_type is `exact_vocalized` AND `author_position != "reported"`
- `Hypothesis` ← match_type is `prefix_stripped` / `prefix_as_operator` / `pattern_construction` OR `author_position == "reported"`
- `Zero` ← no match, blacklisted topic, gate rejection

**All 4 Batch C rows have `author_position = "preferred"`** (per row design in §4). When matched as `exact_vocalized`, they emit `proof_kind = "Certificate"`. When matched via `prefix_stripped` or `prefix_as_operator` (e.g., the verb appears with a CONJ prefix), they emit `proof_kind = "Hypothesis"` per the Batch A precedent.

**No ProofKind upgrades.** Per Batch B's monotonicity rule, the only proof-kind change anywhere in the pipeline is `Certificate → Hypothesis`, never the reverse. Batch C does not alter this.

---

## 8. Tests

### 8.1 Test file location
Place new tests in a per-batch file (mirroring Batch B's pattern):
`clean_code/test_maani_batch_c_afal_tahwil.py`

This per-batch test file isolates Batch C's surface from the 2000+ line `test_production_path_segmentation.py` and follows the trend started by Batch B.

### 8.2 Tests proposed

| # | Test | Asserts |
|---|---|---|
| 1 | `t_afal_tahwil_jaala_transformation_claim` | Samarrai analyzer returns a `SamarraiClaim` with `topic_id="AFAL_TAHWIL"`, `meaning_id="AFAL_TAHWIL_JAAL"`, `proof_kind="Certificate"` when looking up `جَعَلَ` (exact-vocalized match). |
| 2 | `t_afal_tahwil_ittakhatha_transformation_claim` | Same for `اِتَّخَذَ` → `AFAL_TAHWIL_ITTAKHATHA`. Bonus: verify the Quranic anchor `وَاتَّخَذَ اللَّهُ إِبْرَاهِيمَ خَلِيلًا` is on the claim's `example_quran` field. |
| 3 | `t_afal_tahwil_sayyara_transformation_claim` | Same for `صَيَّرَ` → `AFAL_TAHWIL_SAYYARA`. (Constructed example only — rule card has no Quranic anchor for this verb.) |
| 4 | `t_afal_tahwil_framework_row_loads` | Verify the framework row (`AFAL_TAHWIL_BASIC`) is loaded; meaning_ar text matches expected. |
| 5 | **`t_afal_tahwil_negative_zann_family_stays_zann`** | Negative regression — `ظَنَّ` continues to resolve to `topic_id="ZANN_FAMILY"`, NOT `AFAL_TAHWIL`. Confirms the new sibling family does not steal claims from the existing one. |
| 6 | **`t_afal_tahwil_negative_non_transformation_jaala`** | Negative — verify that if a `جَعَلَ`-as-creation reading exists in the corpus (e.g., `جَعَلَ الظُّلُمَاتِ وَالنُّورَ`), the system does not silently emit a wrong transformation interpretation. **Acceptance:** the test passes if EITHER (a) the system returns the transformation reading AS Hypothesis (acceptable — modality applied but with Hypothesis ProofKind, per the warning column), OR (b) the system returns the transformation reading but downstream reasoning correctly notes the alternate readings, OR (c) the row's `warnings` field is surfaced. Strict assertion: the wrong reading must NOT carry Certificate ProofKind without a hedge. |

If `samarrai_loaders/volume2_loader.py` requires the file list to be extended (per §6.5), add one structural test:

| 7 | `t_afal_tahwil_loader_discovers_file` | Verify that `lookup_word` for any of the 3 verbs returns at least one claim (proves the loader picked up the new file). |

### 8.3 Production-suite regression
Both existing test files must continue to pass with no modification:
- `clean_code/test_production_path_segmentation.py` (158/158 currently)
- `clean_code/test_maani_batch_b_author_position.py` (6/6 currently)

---

## 9. Acceptance

A Batch C release is acceptable if and only if **all** of:

1. **Row count increases by exactly 4** in `data/contracts/maani/volume2/transform_verbs_meanings.csv` (4 new rows + the CSV header line = 5 lines total in the new file).
2. **Total MAANI row count** rises from 245 to **249**.
3. **Schema validation passes** — the new CSV's header matches `schema.md`'s 19-column contract exactly.
4. `samarrai_analyzer.lookup_word_all_volumes("جَعَلَ", "exact_vocalized")` returns at least one claim with `topic_id="AFAL_TAHWIL"`.
5. Same for `اِتَّخَذَ` and `صَيَّرَ`.
6. **`test_maani_batch_b_author_position.py` still passes** (6/6).
7. **`test_production_path_segmentation.py` still passes** (158/158 currently).
8. **`test_maani_batch_c_afal_tahwil.py` passes** (6 or 7 tests per §8.2).
9. **No changes to `clean_code/i3rab_engine/*`**.
10. **No changes to MASAQ-related files** (`master_token_lookup.py`, `role_rules_contract.py`).
11. **No changes to L6 / L7 / L8** (`resolution_engine.py`, `meaning_assembler.py` step 7+, `reasoning_engine.py`).
12. **No changes to `samarrai_certified_operator_gate.py`** unless §6.3 investigation surfaces a real conflict.

If any of these is violated, the batch is rejected and the SPEC is re-opened.

---

## 10. Non-goals (explicit deferrals)

The following are NOT in Batch C and any work on them requires a separate SPEC and RULE_LOCK:

- **The remaining 4 transformation verbs**: تَرَكَ, رَدَّ, تَخِذَ, وَهَبَ. Deferred to a possible Batch C₂ once Batch C ships and proves stable.
- **كان وأخواتها** (Vector V4 in the handoff) — the copular family (كان, أصبح, أمسى, أضحى, ظل, بات, صار, ليس). The handoff's preferred V4 default; deferred because curated rule-card evidence is sparser than for AFAL_TAHWIL.
- **أفعال المُقارَبَة** (Vector V5) — كاد, عَسى, أَوْشَك.
- **أفعال المَدْح والذَّمّ** (Vector V6) — نِعْم, بِئْس, حَبَّذا, لا حَبَّذا. The L1 `UninflectedVerbContract` (commit `4c8b953`) already classifies these structurally; MAANI semantics is a natural future extension but is **not** Batch C.
- **التَّضمين practical examples** (Vector V7) — extending `volume3/tadmin_and_policy.csv` beyond its current 8 framework rows.
- **Bulk migration of `construction_rules.jsonl`** (Vector V3) — the 1,043-row raw extraction. Hard rule: never bulk-migrate.
- **Bulk migration of `meaning_cards.jsonl`** (Vector V11) — the 256 direct_rule + 878 heuristic_rule pool. Same hard rule.
- **External classical scholars** — Ibn Hisham, Ibn Aqil, Suyuti, Ar-Radhi (Vector V8 / V9).
- **Modern Arabic operators** (Vector V9) — compound prepositions, discourse connectors.
- **NAA operators_catalog reconciliation** (Vector V10).
- **Cross-source disagreement modeling** (Vector V8's `source_school` extension).
- **Conditions/exceptions matcher DSL** (Vector V2).
- **MeaningGraph edge whitelist extension** to include AFAL_TAHWIL — see §6.4 option 6.4.b; deferred to a follow-up batch with smoke evidence.
- **Whether or not to upgrade صَيَّرَ's row from `confidence=0.93` to a higher value** once a Quranic anchor is located — deferred to a sub-batch with explicit search.
- **Re-curation of the 6 corrupted-author_position rows** flagged in the Batch B report — separate data-hygiene batch.

---

## 11. Risk

### 11.1 Main risk
**Polysemy of جَعَلَ.** Samarrai explicitly notes in the rule card's `exceptions_or_warnings` that جَعَل can mean transformation, creation, OR belief. A static row stating "جَعَلَ = transformation" without contextual disambiguation could **overclaim** the transformation reading when the actual verse intends creation (e.g., `جَعَلَ الظُّلُمَاتِ وَالنُّورَ` ← creation, not transformation) or belief.

### 11.2 Mitigation
**Five layered safeguards**:

1. **Exact rows only.** The lexicon is 4 rows. Not a broad runtime heuristic; not a pattern-matcher. Behavior is bounded by what the rows say.
2. **ProofKind tier.** Per §7, only exact-vocalized matches with `author_position="preferred"` emit `Certificate`. Surface variants (CONJ-prefix, suffix-attached) emit `Hypothesis`. Downstream consumers see the proof-kind tier and can hedge.
3. **Explicit `warnings` column.** Row 2 (جَعَلَ) carries the warning text "جَعَل تَأتي بِمَعنى التَّحويل وَ بِمَعنى الخَلق وَ بِمَعنى الاعتِقاد — السِّياق يُحَدِّد" — preserving Samarrai's own qualifier into the data.
4. **No MeaningGraph edge emission** (per §6.4 option 6.4.a). Display-only first; the verb-class operator does NOT generate a typed edge until smoke evidence justifies a follow-up batch.
5. **Negative test** (§8.2 test #6) explicitly asserts that the system does not silently emit a wrong transformation interpretation with Certificate ProofKind on a known non-transformation usage.

### 11.3 Other risks (lower severity)

- **اِتَّخَذَ's one-object reading** — when اِتَّخَذَ takes only one object, the meaning is "to take" (not "to transform into"). The row's `exceptions` and `warnings` columns document this; the gate's default-allow path does NOT distinguish single-object vs two-object verb usage. Acceptable for Batch C; a follow-up batch could add per-row valency conditions if needed.
- **Loader behavior** — if `volume2_loader.py` uses a hardcoded file list, a one-line edit is needed (see §6.5). Risk mitigation: the §6.5 check runs **before** the RULE_LOCK is written.
- **Confidence value choice (0.93 vs 0.95)** — using the rule card's source value for verb rows and slightly higher for the framework row matches the ZANN pattern (ZANN framework is 0.95, ZANN verb rows are 0.93). No risk.

### 11.4 What this batch is NOT trying to fix
- It does NOT extract roles/cases from running text. That's the i3rab layer's job.
- It does NOT decide on a per-verse basis whether a usage is transformation vs creation. That's downstream reasoning's job.
- It does NOT remove the polysemy from جَعَلَ. It encodes Samarrai's view; the polysemy remains in the language.

---

## 12. Standing pipeline (per handoff §11)

Batch C must follow the standard MAANI pipeline:

1. **SPEC** ← *this document* (draft pending approval).
2. **SPEC review + approval** ← user decision.
3. **RULE_LOCK** ← `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_RULE_LOCK.md`, written only after this SPEC is approved.
4. **Loader auto-discovery investigation** ← read-only, §6.5.
5. **Narrow implementation** ← only the allowed files: the new CSV, the new test file, and (if §6.5 requires it) a one-line `volume2_loader.py` edit.
6. **Tests** ← per §8.2.
7. **Row-count acceptance + ProofKind distribution check** ← per §9.
8. **Production-suite regression check** ← `test_production_path_segmentation.py` (158/158) + `test_maani_batch_b_author_position.py` (6/6).
9. **Report** ← `docs/specs/MAANI_BATCH_C_AFAL_TAHWIL_REPORT.md`.
10. **Commit approval gate** ← user approves the commit hash, not just the patch.

Skipping any step → batch is rejected.

---

## 13. One-screen recap

| Item | Value |
|---|---|
| Batch | C |
| Family | أَفعال التَّحويل (Samarrai's transformation verbs) |
| Source | `rule_cards.jsonl` row `AFAL_AL_TAHWIL__P2_001` |
| Provenance | Vol 2, pp. 26–279, confidence 0.93 |
| New CSV | `clean_code/data/contracts/maani/volume2/transform_verbs_meanings.csv` |
| Rows | 4 (framework + جَعَلَ + اِتَّخَذَ + صَيَّرَ) |
| Schema | unchanged 19-column |
| L1/L2/L3 touched | NO |
| L6 / L7 / L8 touched | NO |
| MASAQ touched | NO |
| Gate touched | NO (planned) |
| MeaningGraph edge whitelist | unchanged (Option 6.4.a) |
| ProofKind enum extended | NO |
| Tests added | 6–7 in new file `test_maani_batch_c_afal_tahwil.py` |
| Total MAANI rows after batch | 249 (was 245) |
| Main risk | polysemy of جَعَلَ |
| Main mitigation | exact rows + ProofKind tier + warnings column + no edge emission + negative test |
| Deferred families | كان, مُقارَبَة, مَدْح/ذَمّ, تَضمين, bulk-migration, external scholars, modern Arabic |
