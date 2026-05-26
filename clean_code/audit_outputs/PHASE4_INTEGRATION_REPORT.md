# PHASE 4 INTEGRATION — Flag-Controlled Hook (Final Report)

تاريخ: 2026-05-25

## Scope

تَكامُل ContextualAmbiguityResolver خَلف feature flag:
- env var: `ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER=1`
- default: OFF (لا تَغيير سُلوكيّ)

## Integration point

`WordClassClassifier.classify_with_context(token, prev_tokens, next_tokens)`:
- يَستَدعي `classify(token)` العاديّ
- ثُمَّ `maybe_apply_resolver()` (في `arabic_analyzer/contextual_resolver/integration.py`)

شَرط التَّطبيق (كُلّ التَّالي يَجِب أَن يَتَحَقَّق):
1. surface في `HANDLED_SURFACES_NORMALIZED` (مَن، ما، أَيّ، متى، أين، أنى، حيث، بما)
2. `proof_kind == "Hypothesis"`
3. `needs_context` OR ≥2 candidates

قَواعِد:
- `Certificate` → تَرقيَة + `source = "ContextualAmbiguityResolver"` + حِفظ candidates الأَصليَّة
- `Hypothesis` (function clear) → metadata-only (لا تَرقيَة)
- `unresolved_ambiguous` → لا تَغيير
- خارِج النِّطاق → لا تَغيير
- flag OFF → byte-identical لِـ baseline

## Tests

| Suite | Pass |
|---|---|
| test_phase4_integration.py | 11/11 ✓ |
| test_phase4_resolver.py (standalone) | 30/30 ✓ |
| Full regression flag OFF | **290/290 ✓** |
| Full regression flag ON  | **290/290 ✓** |

## Measurement — sample 800 ambiguity rows

| المِعيار | flag OFF | flag ON |
|---|---|---|
| tokens in scope | 800 | 800 |
| → Certificate (resolver promoted) | 0 | **311 (38.9%)** |
| → Hypothesis metadata-only | 0 | 171 (21.4%) |
| → No resolver change | 800 | 318 (39.7%) |

### Promoted by function (flag ON)

| function | count |
|---|---|
| prepositional_phrase_component | 308 |
| interrogative_tool | 3 |

### Promoted by surface (flag ON)

| surface | promoted |
|---|---|
| من | 310 |
| ما | 1 |

### Class changes (flag ON)

- `HARF → HARF`: 308 (تَأكيد resolver لِـ مِنْ كَحَرف جَرّ)
- `ISM_MAWSOOL → ISM_MABNI`: 3 (مَن في سِياق استِفهام)

## Acceptance vs spec

| المِعيار | الحالَة |
|---|---|
| flag OFF baseline byte-identical | ✓ (test_flag_off_output_identical_to_baseline) |
| flag ON resolves Hypothesis tokens | ✓ 38.9% promoted |
| لا تَدَخُّل في event/relation extractor | ✓ |
| لا enforce في أَيّ gate | ✓ would_block_*_count = 0 |
| لا integration لِـ 04_nahw/awzan/03_juthur | ✓ |
| original candidates مَحفوظة | ✓ phase4_original_candidates |
| masaq_compatible_class مُنفَصِل | ✓ |
| reason + context_features مَوجودَة | ✓ |
| لا default للـflag | ✓ |
| all tests pass | ✓ 290/290 |

## Notes

- 39.7% مِن tokens في scope لَم يَتَدَخَّل resolver لَهَا — هذِه إِمّا:
  • `unresolved_ambiguous` (لا signals كافِيَة)
  • أَو لَم تَكُن مُؤَهَّلَة (مَثَلًا certainty أَصلًا Certificate)
- المُكَسَّب الأَكبَر: مِنْ (preposition) — 308 case تَأكيد بِـ reason صَريح
- 3 cases مَن (interrogative) — تَغَيُّر selected_class مَع masaq_compatible_class مَحفوظ

## التَّوصيَة

⚠ **لا تُحَوِّل flag إلى default الآن.**

Phase 4 integration يَعمَل صَحيحًا، لَكِن:
1. التَّأثير على qa_zeros و unresolved_edges يَحتاج قياس كامِل (full Quran rerun بَعد integration بـ Phase D/G).
2. تَوسيع `unresolved_ambiguous` (الـ318 case) قَد يَزيد العائِد قَبل التَّفعيل العامّ.
3. القَرار: نَنتَظِر تَوجيه المُستَخدِم — هَل نَتَوَسَّع في context features أَوَّلًا؟ أَم نُجَرِّب enforcement تَدريجيّ؟
