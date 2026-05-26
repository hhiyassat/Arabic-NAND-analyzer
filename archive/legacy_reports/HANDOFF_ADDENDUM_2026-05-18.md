# HANDOFF ADDENDUM — 2026-05-18

> **Purpose:** This is a supplement to `/Users/husseinhiyassat/fractal/HANDOFF_TO_CLAUDE.md`.
> It records what was added/changed in the May 17–18 session, so a new Claude session has up-to-date context.
>
> **How to use:** Read the original `HANDOFF_TO_CLAUDE.md` first, then read this addendum.
> Everything in the original is still valid except where this addendum explicitly supersedes it.

---

## 1. NEW: Official wazn matcher → `hussein/clean_code/`

A new self-contained folder was created as the project's **official word→wazn+root analyzer**.

```
hussein/clean_code/
├── wazn_matcher.py                          ← THE official analyzer (formerly analyzer_v2)
├── README.md                                ← user-facing documentation
├── FREEZE_v2.4.md                           ← stable-release marker + deferred work
└── data/
    ├── Mushtaqat_Full_Weights_Table.xlsx    ← 79 canonical mushtaqat weights
    ├── wazn_db_extensions.csv               ← 60+ broken-plural / quadriliteral patterns
    ├── unified_wazn_database.csv            ← 403 patterns from 3 merged sources
    ├── mishkat_word_root.csv                ← 16,423 (root, word, count) from Quranic corpus
    ├── mishkat_word_root_with_wazn.csv      ← 10,219 derived wazns (from derive_wazn_from_mishkat.py)
    ├── verb_db.csv                          ← 195 verb-only patterns
    ├── noun_extracted_db.csv                ← 148 noun patterns new from Quran
    ├── huruf_muqattaa.csv                   ← 14 Quranic surah-openers (الم/كهيعص/...)
    └── golden_name_base.csv                 ← 231 EXCLUDED proper nouns (الله/موسى/فرعون/...)
```

### Quick usage

```python
from clean_code.wazn_matcher import AnalyzerV2

a = AnalyzerV2()
matches = a.analyze("كَاتِبٌ", max_results=3)
# matches[0].wazn == "فَاعِل", matches[0].root == "كتب"
```

### CLI

```bash
python3 hussein/clean_code/wazn_matcher.py "اتَّخَذَ" --max 5
python3 hussein/clean_code/wazn_matcher.py "اللَّهِ" --json
```

### Performance (MASAQ, 10,000 unique words)

| Metric | wazn_matcher | alasmaa baseline | Improvement |
|---|---:|---:|---:|
| Coverage | 86.3% | 21.2% | ×4 |
| **Top-1** | **59.3%** | 16.8% | **×3.5** |
| **Top-3** | **64.6%** | 16.8% | **×3.8** |

Per-category Top-1: سالم 90.3%, مهموز 94.4%, معتل 57.8%, مضاعَف 62.3%, رباعي 57.1%.

---

## 2. NEW: Constitutional rules #21 and #22

Two new top-level constitutional principles, recorded in `معمار_المعنى_العربي/قاعدة_دستورية_عليا.md`:

### Rule #21 — Project Scope (2026-05-17)
> **The project aspires to "transparent analytical simulation governable by humans", NOT "human-understanding simulation".**

Four binding commitments derived from this:
1. **Source-of-Claim** — every assertion cites its data/rule source
2. **Confidence-of-Claim** — every assertion carries `confidence ∈ [0, 1]`
3. **Alternatives-Preserved** — all viable readings returned, no winner-takes-all
4. **Reversibility** — every decision can be inspected and rejected by user

Full details: `12_Project_Scope_Declaration.md`.

### Rule #22 — Official Wazn Matcher (2026-05-18)
> **`hussein/clean_code/wazn_matcher.py` is the project's official word→wazn+root analyzer.**
> It supersedes `alasmaa/analyze_word.py`.

Full details: `13_Wazn_Matcher_Declaration.md`.

---

## 3. NEW: Pipeline integration plan (NOT yet executed)

The `architecture_test` pipeline (in `hussein/src/architecture_test/`) currently uses `analyze_word_adapter.py` which wraps `alasmaa/analyze_word.py`. **This integration is unchanged in this session.**

When ready, the pipeline can swap to wazn_matcher by:
- Replacing the `analyze_word_adapter` import with `clean_code.wazn_matcher`
- Translating the WaznMatch dataclass to the existing `analyze_word` per-token dict shape

**Status: deferred** — wazn_matcher is production-grade as a standalone tool. Pipeline swap requires testing the full architecture_test on all 16k mishkat rows. Holding off until Foundation work completes.

---

## 4. NEW: Eval and benchmarking tooling

Three scripts under `hussein/scripts/`:

| Script | Purpose |
|---|---|
| `derive_wazn_from_mishkat.py` | Forward direction: (root, word) → wazn. Generates `mishkat_word_root_with_wazn.csv`. |
| `merge_wazn_database.py` | Merges canonical_table + extensions + mishkat-extracted → `unified_wazn_database.csv`. |
| `split_extracted_wazn_by_morph.py` | Splits mishkat-extracted into `verb_db.csv` and `noun_extracted_db.csv`. |
| `eval_analyzer_v2_vs_alasmaa.py` | Compares wazn_matcher vs alasmaa on mishkat. |
| `run_analyzer_v2_on_masaq.py` | Runs wazn_matcher on MASAQ unique words. Validates against mishkat truth. |

All outputs land in `hussein/data/extracted/`.

---

## 5. NEW: Architecture documentation

Added to `معمار_المعنى_العربي/`:

| File | Content |
|---|---|
| `12_Project_Scope_Declaration.md` | Full Rule #21 with the 4 commitments |
| `13_Wazn_Matcher_Declaration.md` | Full Rule #22 with metrics and deferred work |
| `Benchmarks_vs_State_of_the_Art.md` | Honest comparison vs MADAMIRA/CAMeL Tools/Farasa/AlKhalil |
| `M1_Plan_Recorded.md` | Plan for M1.A-D (still pending — Foundation first) |

Updated:
- `قاعدة_دستورية_عليا.md` — added rules #21 and #22
- `Project_Status.md` — current decision: wazn_matcher v2.4 STABLE; moving to Foundation (Normalizer)

---

## 6. CHANGED: Status of wazn analysis in the project

| Component | Before this session | After this session |
|---|---|---|
| Official analyzer | alasmaa/analyze_word.py (only) | **clean_code/wazn_matcher.py** |
| Patterns | 80 (alasmaa) | **403 unified** (canonical + extensions + mishkat) |
| Variant generation | 4-8 strips | **20+ tiered strips** |
| Confidence | not present | **scored ∈ [0, 1]** |
| Multi-reading | best-only | **list[WaznMatch] ranked** |
| Quranic openers | wrong wazn extracted | **`bab=quranic_opener, root=N/A`** |
| Proper nouns | wrong wazn extracted | **`bab=excluded_name, root=N/A`** |
| Divine name (الله) | wrong wazn extracted | **`root=ءله, divine_name`** |
| Form X verbs | unsupported | **يَسْتَفْعِلُ / نَسْتَفْعِلُ etc. — works** |
| Form VIII assimilation | unsupported | **اتَّخَذَ → افْتَعَل / ءخذ — works** |
| Geminate | 24% top-1 | **62.3% top-1** |
| MASAQ coverage | 21% | **86%** |
| MASAQ top-1 | 17% | **59.3%** |

---

## 7. CHANGED: Audited roots — now mishkat-augmented

`load_audited_roots()` in wazn_matcher now combines:
1. Salehan `audited_roots.csv` (~3,163 roots, limited to letters خ-ي)
2. Mishkat `mishkat_word_root.csv` (~4,500 unique roots across the full alphabet)

Together: ~7,000 unique audited roots, used as confidence-boost evidence during matching.

---

## 8. NEW: Major patterns added (key wins)

Patterns that were missing in alasmaa's 80 and are now in unified_db:

- **Broken plurals:** أَفْعَال, فُعُول, فِعَال, مَفَاعِل, مَفَاعِيل, فَوَاعِل, فَعَائِل, أَفَاعِيل (10+)
- **Quadriliterals:** فَعْلَل, فَعْلَال, فُعْلُول, فِعْلِيل, فَعَالِل, فَعَالِيل
- **Verb forms:** يَسْتَفْعِلُ family, تَسْتَفْعِلُ, نَسْتَفْعِلُ, يَفْتَعِلُ family
- **Special:** فَعَائِلَة (ملائكة), فَعْلَان (رحمن), فَعَلَان (إنسان), فُعَّال (حُجَّاج)

Full list: `data/wazn_db_extensions.csv`.

---

## 9. UNCHANGED (preserved per original handoff)

The following original commitments are still respected:

- ✅ `alasmaa/analyze_word.py` — **NOT modified** (user constraint)
- ✅ ALASMA freeze — still in effect
- ✅ `fractal/segmenter` canonical API — unchanged
- ✅ NAA's `normalize.py` — unchanged
- ✅ GPT52 diacritization integration — unchanged
- ✅ Quran-uthmani ayah loading — unchanged
- ✅ Existing architecture_test pipeline (Step −2…6) — unchanged
- ✅ Repo map and data paths — unchanged

---

## 10. CURRENT DECISION (2026-05-18)

> **wazn_matcher v2.4 is FROZEN STABLE. Project priority shifts to Foundation #52 (Normalizer) and #53 (Segmenter).**

Reason: the wazn matcher currently generates 20+ variant transformations to compensate for imperfect normalization and segmentation. With cleaner Foundation layers, the analyzer can be simplified AND its accuracy can rise.

After Foundation work completes:
- Return to wazn_matcher v3.0
- Address the 5 deferred improvements listed in `clean_code/FREEZE_v2.4.md`
- Target: top-1 ≥ 75% on MASAQ

---

## 11. Deferred wazn improvements (recorded for future)

From `clean_code/FREEZE_v2.4.md`:

1. **Verb conjugation table for weak verbs** → would raise معتل to ~75%+
2. **Geminate verb patterns deep** → would raise مضاعَف to ~75%+
3. **Validation on the 35% of MASAQ without mishkat truth** → unknown accuracy floor
4. **Confidence calibration** → make conf=0.9 actually mean 90% accuracy
5. **Quadriliteral pattern coverage** → currently 47 entries

---

## 12. Where things live now (quick reference)

```
fractal/
├── alasmaa/                              ← FROZEN, do not modify
├── new_arabic_analyzer/ (NAA)            ← unchanged
├── salehan/                              ← unchanged
├── segmenter/                            ← canonical, unchanged this session
└── hussein/
    ├── clean_code/                       ★ NEW — official wazn_matcher home
    │   ├── wazn_matcher.py
    │   ├── README.md
    │   ├── FREEZE_v2.4.md
    │   └── data/                         ← self-contained data
    │
    ├── src/architecture_test/            ← pipeline (unchanged this session)
    │   └── analyzer_v2.py                ← synced copy of wazn_matcher
    │
    ├── scripts/                          ← derive/merge/split/eval scripts
    │
    ├── data/                             ← project data
    │   ├── Mushtaqat_Full_Weights_Table.xlsx
    │   ├── extracted/                    ← derived outputs
    │   ├── huruf_muqattaa.csv            ★ NEW
    │   └── golden_name_base.csv          ★ NEW
    │
    └── معمار_المعنى_العربي/                ← constitutional documents
        ├── 12_Project_Scope_Declaration.md     ★ NEW
        ├── 13_Wazn_Matcher_Declaration.md      ★ NEW
        ├── Benchmarks_vs_State_of_the_Art.md   ★ NEW
        ├── M1_Plan_Recorded.md                  ★ NEW (deferred)
        ├── قاعدة_دستورية_عليا.md                ← updated with rules #21, #22
        └── Project_Status.md                    ← updated
```

★ = new this session.

---

## 13. JSON result shape (wazn_matcher)

For programmatic callers, `WaznMatch.to_dict()` returns:

```json
{
  "wazn": "فَاعِل",
  "wazn_plain": "فاعل",
  "bab": "اسم الفاعل | اسم الآلة",
  "morph_type": "noun | verb",
  "root": "كتب",
  "confidence": 1.000,
  "source": "canonical_table | mishkat_extracted",
  "variant_label": "original",
  "variant_form": "كَاتِبٌ",
  "evidence": [
    "variant=original (cost=0.00)",
    "source=canonical_table | mishkat_extracted",
    "morph=noun | verb",
    "movement_sim=0.75",
    "root audited ✓"
  ]
}
```

Special `bab` values to be aware of:
- `quranic_opener` — Quranic disconnected letters (الم, كهيعص, ...)
- `excluded_name` — proper nouns / Quranic-conceptual lexemes
- `closed_class_lexeme` — relative pronouns, demonstratives (الذي, هذا, ...)
- `divine_name` — forms of الله (returns root=ءله)

When you see any of these, the analyzer is **correctly refusing to assign a wazn**.

---

## 14. PYTHONPATH usage

```bash
# Run wazn_matcher standalone (from any directory)
cd hussein
python3 -m clean_code.wazn_matcher "كَاتِبٌ" --max 3

# Or import from another script
import sys
sys.path.insert(0, '/Users/husseinhiyassat/fractal/hussein')
from clean_code.wazn_matcher import AnalyzerV2
```

---

## 15. Next-session checklist

When picking up where we left off:

1. [ ] Read `HANDOFF_TO_CLAUDE.md` (original) for repo overview
2. [ ] Read this addendum for what's new
3. [ ] Check `معمار_المعنى_العربي/Project_Status.md` for current decision
4. [ ] If working on Foundation: see Task #52 (Normalizer) / #53 (Segmenter)
5. [ ] If returning to wazn improvements: see `clean_code/FREEZE_v2.4.md`
6. [ ] If extending eval: see `scripts/run_analyzer_v2_on_masaq.py`

---

## 16. Do NOT do (added to original handoff's do-not list)

- ❌ Do not modify `clean_code/wazn_matcher.py` without bumping version (currently v2.4)
- ❌ Do not edit data files in `clean_code/data/` — regenerate via scripts instead
- ❌ Do not modify `Mushtaqat_Full_Weights_Table.xlsx` (the canonical 79 weights)
- ❌ Do not promise SOTA accuracy (we're at 59.3% top-1, see Benchmarks doc)
- ❌ Do not claim "wazn analysis is done" — the deferred improvements list (FREEZE_v2.4.md) is the truth
- ❌ Do not skip the constitutional rules — every new module must satisfy rule #21 (Source/Confidence/Alternatives/Reversibility)

---

## 17. Summary in one sentence

The wazn matcher is now a self-contained, transparent, multi-source, governable analyzer with 59.3% top-1 on Quranic words — production-ready for sound/hamza forms, acceptable for weak/geminate, frozen at v2.4 pending Foundation (Normalizer + Segmenter) work.

---

*End of addendum.*
