# wazn_matcher v2.4 — FREEZE MARKER

> **Status:** STABLE — frozen on 2026-05-18  
> **Reason:** Foundation work (Normalizer, Segmenter) needs to land first.  
> **Resume after:** Foundation tasks #52 and #53 complete.

---

## Final accepted metrics on MASAQ (10,000 unique words)

| Metric | Value |
|---|---:|
| Coverage | 86.3% |
| **Top-1 accuracy** | **59.3%** |
| **Top-3 accuracy** | **64.6%** |

### Per-category Top-1 (after exclusion correction)

| Category | Top-1 | Top-3 | Status |
|---|---:|---:|---|
| **مهموز سالم** | 94.4% | 95.4% | ✅ production |
| **سالم سليم** | 90.3% | 94.1% | ✅ production |
| **معتل** | 57.8% | 69.9% | 🟡 acceptable, needs verb conjugation table |
| **مضاعَف** | 62.3% | 68.0% | 🟡 acceptable after fixes |
| **رباعي** | 57.1% | 57.1% | 🟡 small sample, needs more patterns |

---

## Deferred improvements (resume after Foundation)

### 1. Verb conjugation table for weak verbs
- Status: missing
- Impact: would raise معتل from 57% to ~75%+
- Effort: 1-2 weeks
- Files to add: `verb_weak_conjugations.csv` (هَدَى/يَهْدِي/اِهْدِ × all persons × all forms)

### 2. Geminate verb patterns deep
- Status: partial (we have shadda × pronoun × no_al × no_mudaari combos)
- Impact: would raise مضاعَف from 62% to ~75%+
- Effort: 1 week
- Approach: add 30+ shadda-specific patterns for forms I-X

### 3. Validation on the 35% of MASAQ without mishkat truth
- Status: unmeasured (~28,000 unique words)
- Impact: unknown accuracy floor
- Effort: 2-3 days
- Approach: cross-reference with another corpus or run human-spot-check

### 4. Confidence calibration
- Status: confidence is raw composite score, not statistically calibrated
- Impact: when v2 says conf=0.9, no guarantee it's actually 90% correct
- Effort: 1 week
- Approach: Platt scaling or isotonic regression on per-row eval data

### 5. Quadriliteral pattern coverage
- Status: 47 entries, mostly from mishkat
- Impact: improves رباعي + plural patterns
- Effort: a few hours
- Approach: add 20-30 more patterns from classical morphology tables

---

## Why freeze now?

The remaining wazn improvements depend on better:

- **Normalization** (Foundation #52): consistent handling of hamza variants, dagger alif, kashida, NFC normalization across all inputs. Currently the Quranic forms with elided alifs (الرَّحْمَن) are partially handled via `alif_insert` variant — but a proper normalizer would handle this uniformly upstream.

- **Segmentation** (Foundation #53): better clitic/prefix detection. Currently we generate 20+ variants because we don't trust the segmenter. With a robust segmenter, we'd need fewer variants and get cleaner matches.

These foundation improvements feed BACK into the wazn_matcher:
- Less variant generation needed → less noise → cleaner top-1
- Consistent input → reproducible behavior
- Proper segmentation gives the analyzer a verified stem to match against

Patching the wazn_matcher to compensate for foundation issues would be **technical debt**. Better to fix the foundation, then return to wazn with cleaner data.

---

## Resume checklist (after Foundation #52 + #53)

When returning to wazn_matcher improvements:

1. [ ] Re-run MASAQ eval with new normalizer + segmenter feeding analyzer
2. [ ] Measure how much of the current variant-generation logic becomes redundant
3. [ ] Address deferred improvements 1-5 in order of impact (verb conjugation first)
4. [ ] Target: top-1 ≥ 75% on MASAQ
5. [ ] Add documentation tests for each category
6. [ ] Promote v3.0 release marker

---

## Files frozen at v2.4

| File | Hash/Size | Frozen at |
|---|---|---|
| `wazn_matcher.py` | ~50 KB | 2026-05-18 |
| `data/unified_wazn_database.csv` | 403 patterns | 2026-05-18 |
| `data/wazn_db_extensions.csv` | 60+ entries | 2026-05-18 |
| `data/mishkat_word_root_with_wazn.csv` | 10,219 rows | 2026-05-18 |
| `data/verb_db.csv` | 195 patterns | 2026-05-18 |
| `data/noun_extracted_db.csv` | 148 patterns | 2026-05-18 |
| `data/huruf_muqattaa.csv` | 14 entries | 2026-05-18 |
| `data/golden_name_base.csv` | 231 entries | 2026-05-18 |

Any changes after 2026-05-18 should bump the version (v2.5+).

---

*The wazn_matcher is the strongest module in the project right now. Don't break it while fixing the foundation.*
