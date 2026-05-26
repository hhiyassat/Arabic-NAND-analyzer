# clean_code — Official Wazn Matcher for معمار المعنى العربي

> **Constitutional declaration (2026-05-18):** the module in this folder is the project's official word → wazn + root analyzer. It supersedes `alasmaa/analyze_word.py`.

---

## Contents

| File | Role |
|---|---|
| `wazn_matcher.py` | The official analyzer (formerly `analyzer_v2.py`) |
| `data/unified_wazn_database.csv` | 403 unique wazn patterns merged from 3 sources |
| `data/Mushtaqat_Full_Weights_Table.xlsx` | Canonical 80 wazns (source 1) |
| `data/wazn_db_extensions.csv` | 60+ broken-plural and rare patterns (source 2) |
| `data/mishkat_word_root_with_wazn.csv` | 10,219 (root, word, wazn) from Quranic corpus (source 3) |
| `data/verb_db.csv` | 195 verb patterns derived from mishkat |
| `data/noun_extracted_db.csv` | 148 new noun patterns observed in Quran |

---

## Quick start

```python
from clean_code.wazn_matcher import AnalyzerV2

analyzer = AnalyzerV2()
matches = analyzer.analyze("كَاتِبٌ", max_results=3)
for m in matches:
    print(f"{m.wazn}  root={m.root}  conf={m.confidence:.2f}  src={m.source}")
```

Output:
```
فَاعِل  root=كتب  conf=1.00  src=canonical_table | mishkat_extracted
فَاعَل  root=كتب  conf=0.98  src=canonical_table | mishkat_extracted
فَاعُل  root=كتب  conf=0.98  src=canonical_table | mishkat_extracted
```

### CLI

```bash
cd hussein/clean_code
python3 wazn_matcher.py "اتَّخَذَ" --max 5
python3 wazn_matcher.py "كَاتِبٌ" --json
```

### Full ayah pipeline (normalizer + segmenter + wazn)

```bash
cd hussein
PYTHONPATH=. python3 scripts/analyze_clean_code_text.py \\
  --masaq ../new_arabic_analyzer/data/MASAQ.csv --ayah 2:282
PYTHONPATH=. python3 scripts/analyze_clean_code_text.py -t "كَاتِبٌ" --json
```

---

## Performance benchmarks

**Tested against:** MASAQ corpus (10,000 unique Quranic words), with mishkat as ground truth.

| Metric | wazn_matcher (v2) | alasmaa baseline | Improvement |
|---|---:|---:|---:|
| Coverage | **86.3%** | 21.2% | +65% |
| Top-1 accuracy | **57.5%** | 16.8% | **×3.4** |
| Top-3 accuracy | **62.7%** | 16.8% | **×3.7** |

### Per-category accuracy (MASAQ Top-1)

| Category | wazn_matcher | alasmaa |
|---|---:|---:|
| سالم سليم (sound triliteral) | **89.8%** | 26.6% |
| مهموز سالم | **94.4%** | 12.7% |
| معتل (weak) | 57.2% | 6.4% |
| مضاعَف (geminate) | 41.2% | 7.0% |
| رباعي (quadriliteral) | 57.1% | 0.0% |

---

## Architecture

```
INPUT: vocalized Arabic word
   │
   ├─ Special-lexeme check (الله, الذي, ذلك, ...) → fast return
   │
   ├─ Generate variants (up to 20+):
   │    • original / no_irab
   │    • no_clitic, no_al, no_lam_lam
   │    • no_pronoun (ـه/ـها/ـك/ـكم/ـنا/...)
   │    • no_number (ـين/ـون/ـات)
   │    • shadda_expanded (× no_al × no_number × no_pronoun × no_mudaari)
   │    • form_viii_hamza_restored
   │    • form_viii_t_root_restored
   │    • no_mudaari_prefix (يستفعل → ستفعل)
   │    • alif_madda_expanded (آ → ءَا)
   │    • alif_insert_before_last (رحمن → رحمان)
   │
   ├─ For each variant × each wazn pattern in unified_db:
   │    • structural_match (letter pattern, with hamza-class normalization)
   │    • extract root letters
   │    • compute movement_similarity (diacritic agreement)
   │
   ├─ Confidence formula:
   │   conf = (1 - variant_cost)
   │        × source_boost          [canonical/extensions/mishkat]
   │        × movement_boost        [diacritic similarity]
   │        × audit_boost           [root in audited list]
   │        × transformation_boost  [coherence: form VIII + hamza root]
   │        × clitic_penalty        [demote clitic-confused readings]
   │
   ├─ Generate weak-root alternatives:
   │    Tier 1: ا↔و, ا↔ي, ى↔ي direct substitution
   │    Tier 2: position permutation (audited-only)
   │
   └─ Return ranked WaznMatch[] with evidence trail
```

---

## Constitutional commitments

Every match satisfies the four pillars of `12_Project_Scope_Declaration.md`:

1. **Source-of-Claim** — Each match cites its database source
2. **Confidence-of-Claim** — Numeric confidence ∈ [0, 1]
3. **Alternatives-Preserved** — `analyze()` returns `list[WaznMatch]`, never winner-takes-all
4. **Reversibility** — Caller can inspect any reading via `m.to_dict()` and accept/reject

---

## Known limitations

| Limitation | Status |
|---|---|
| Defective verb conjugations (يَدْعُو, نَسْتَغْنِي) | Partial: 57% top-1; needs verb conjugation table |
| Proper nouns (إبراهيم, يونس) | Out of scope — use aalam_loader |
| Pronouns and demonstratives (الذي, هذا) | Correctly returns `closed_class_lexeme` — but mishkat scores them differently |
| Lam-shamsi geminate (الَّذِينَ) | Hard-coded as closed-class |

---

## Files derived from this module (do NOT edit by hand)

| File | Generation |
|---|---|
| `data/unified_wazn_database.csv` | Run `scripts/merge_wazn_database.py` |
| `data/mishkat_word_root_with_wazn.csv` | Run `scripts/derive_wazn_from_mishkat.py` |
| `data/verb_db.csv`, `data/noun_extracted_db.csv` | Run `scripts/split_extracted_wazn_by_morph.py` |

To rebuild:
```bash
cd hussein
python3 scripts/derive_wazn_from_mishkat.py
python3 scripts/merge_wazn_database.py
python3 scripts/split_extracted_wazn_by_morph.py
# Then copy outputs from data/extracted/ → clean_code/data/
```

---

## Version history

| Version | Date | Top-1 (MASAQ) | Note |
|---|---|---:|---|
| baseline (alasmaa) | — | ~17% | structural-only matching, 80 weights |
| v2.0 | 2026-05-17 | 45.3% | initial unified-db reverse matcher |
| v2.1 | 2026-05-18 | 53.5% | + لفظ الجلالة + فعلان + ى/ي |
| v2.2 | 2026-05-18 | 56.2% | + Form X + ي/و alternation |
| v2.3 | 2026-05-18 | 56.3% | + closed-class + smart shadda |
| **v2.4** (current) | **2026-05-18** | **57.5%** | **+ shadda combos + article-augment penalty** |

---

*This folder is the project's analytical heart. Treat it as production code.*
