# PHASE 4 — ContextualAmbiguityResolver — التَّقرير النِّهائيّ
# تاريخ: 2026-05-25

## Scope
- Resolver standalone module: `arabic_analyzer/contextual_resolver/`
- لا integration بِالـpipeline (لا تَغيير سُلوكيّ runtime).
- 7 surfaces + بِما compound: مَن، ما، أَيّ، مَتَى، أَيْنَ، أَنَّى، حَيْثُ، بِما

## Tests
- 30/30 tests pass (test_phase4_resolver.py)
- Full regression: 279/279 across A/B/C/D/E/F + Phase 2.5/3/4 + sessions 4/5/6 + S3 contracts

## Before/After — ambiguity_cases.csv
| المِعيار | القيمَة |
|---|---|
| Total ambiguity rows (baseline) | 6766 |
| In Phase-4 scope                 | 4116 |
| → Certificate                    | 2070 (50.3%) |
| → Hypothesis (function clear)    | 1000 (24.3%) |
| → unresolved_ambiguous           | 1041 (25.3%) |

## Per-surface breakdown
| surface | count | top function |
|---|---|---|
| من | 2857 | prepositional_phrase_component (1739) |
| ما | 943 | negative_particle (361) |
| بما | 311 | prepositional_phrase_component (311) |

## By selected_function
| function | count |
|---|---|
| prepositional_phrase_component | 2050 |
| unresolved_ambiguous | 1041 |
| relative_pronoun | 537 |
| negative_particle | 361 |
| conditional_tool | 93 |
| interrogative_tool | 20 |
| extra_particle | 9 |

## Hypothesis → Certificate upgrades
| surface | upgrades |
|---|---|
| من | +1750 |
| ما | +9 |

## MASAQ-compatibility
- matches gold:    2284
- mismatches gold: 1827
- ⚠ نَتيجَة طَبيعيَّة: resolver يُحَدِّد selected_class بِنَموذَج لُغَويّ داخِليّ
  (مَن غالِبًا ISM_MABNI) بَينَما MASAQ يَستَخدِم HARF.
- masaq_compatible_class مَحفوظ لِلتَّوافُق.

## Acceptance vs spec
| المِعيار | الحالَة |
|---|---|
| all tests pass | ✓ 279/279 |
| no Event[ئك] | ✓ 0 |
| segmentation_leak_count remains 0 | ✓ |
| fragment_event_count remains 0 | ✓ |
| ambiguous_token_count decreases (in scope) | ✓ 3070 of 4116 resolved (74.6%) |
| unresolved_ambiguity_count decreases | ✓ مِن 4116 إلى 1041 |
| no event/relation gate enforcement yet | ✓ observe-only |
| no direct changes to event/relation extractor logic | ✓ resolver standalone |

## Notes
- qa_zeros / unresolved_edges لا يَتَغَيَّران بِدون integration — هذا مُتَوَقَّع.
- Integration في Layer 1 = قَرار مُنفَصِل (لِلـsession التَّاليَة).
- VERB_AS_ISM (أَعْلَمُ): backlog (46× في sweep_v5).

## التَّوصيَة لِلخُطوَة التَّاليَة
1. مُراجَعَة 1041 unresolved_ambiguous — هل يَحتاجون features إِضافيَّة في context_features.py؟
2. integration اختِياريّ خَلف flag في Layer 1 لِقياس أَثَر downstream.
3. ثُمَّ تَشغيل observe report ثانيَةً لِمُقارَنَة would_block_relations / would_block_events.
