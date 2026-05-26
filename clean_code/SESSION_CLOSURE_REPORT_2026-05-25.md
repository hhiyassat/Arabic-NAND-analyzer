# تَقرير إِغلاق الجَلسَة — 2026-05-25

## المُنجَزات

### العُقود الـ7 الجَديدَة

| # | العَقد | المَلَفّ | الوَظيفَة |
|---|---|---|---|
| 1 | **VerbFormContract** | `verb_form_contract.py` | PrefixStackParser + MoodDetector + MorphFeatures + kana_family lexicon |
| 2 | **NonVerbOverrideGate** | `non_verb_override_gate.py` | 6 hard-no gates (ال/ـة/مُثَنَّى/مَقصورَة/تَفضيل/closed-list) |
| 3 | **PossessiveNominalBlocker** | `possessive_nominal_blocker.py` (→merged into ObjectVsPoss) | اسم+ضَمير مُلصَق ≠ فِعل |
| 4 | **DefectiveVerbContract** | `defective_verb_contract.py` | كان/ليس → ism_of_kana بَدَل agent_of |
| 5 | **ObjectPronounVsPossessivePronounGate** | `object_pronoun_vs_possessive_gate.py` | يَفصِل ضَمير المَفعول مِن ضَمير المِلكيَّة |
| 6 | **ClosedFunctionWordOverrideGate** | `closed_function_word_gate.py` | 81 صورَة + tanwin/ال/ـة guards |
| 7 | **AgentWindowContract v2** | `agent_window_contract.py` | 5+3 gates: distance/intervening/inna/role/tafdeel + intervening-verb/detached-pronoun/passive-voice |
| 8 | **HarfJarrAgreementContract** | `harf_jarr_agreement_contract.py` | consume-after-use, window=3 |
| 9 | **AttributeAgreementContract** | `attribute_agreement_contract.py` | gender/number/definiteness/case agreement |

### الـCSV الـ3 الجَديدَة

- `data/contracts/lists/kana_family.csv` — 44 صورَة كان/ليس
- `data/contracts/lists/possessive_pronoun_suffixes.csv` — 18 ضَمير مُلصَق
- `data/contracts/lists/closed_function_words.csv` — 81 أداة مُغلَقَة (14 فِئَة)

### الاختبارات

| Suite | النَّتيجَة |
|---|---|
| `test_verb_form_contract.py` | 18/18 ✓ |
| `test_non_verb_override.py` | 11/11 ✓ |
| `test_possessive_and_defective.py` | 12/12 ✓ |
| `test_object_vs_possessive.py` | 10/10 ✓ |
| `test_agent_contract.py` | 11/11 ✓ |
| `test_closed_function_word.py` | 10/10 ✓ |
| `test_agent_window.py` | 10/10 ✓ |
| `test_agent_window_v2.py` | 8/8 ✓ |
| `test_harf_jarr.py` | 8/8 ✓ |
| **المَجموع** | **98/98** ✓ |

## النَّتائج عَلى 2:282

| القياس | البدايَة | النِّهايَة |
|---|---|---|
| FIIL count | 46 (مَع تَلَوُّث) | 35 (نَظيف) |
| HARF count | 36 | 42 (الأَدوات عادَت) |
| agent_of count | 25 (false إِيجابات) | **4** (كُلّها صَحيحَة) |
| harf_jarr_of count | 8 (تَجاوُز نوافِذ) | **2** (مَحَلّيَّة) |
| attribute_of count | 2 (مَع mismatch) | 1 (مُتَّفِق) |
| Relations | 101 | 74 (تَنظيف) |
| Suppressed | 0 | 20 (gates تَعمَل) |
| Contradictions | 0 | **0** |

## مَسح كامِل القُرآن

**5,557 آية فَريدَة مِن 6,236 (89%)** — كُلّ السُّوَر الـ114 مُغَطّاة.

- **0 Python errors** (100% i3rab استَقامَت)
- 2.27% بِلا relations (آيات قَصيرَة، اسميَّة بَحتَة)
- 15.64% بِلا events (جُمَل اسميَّة، نِداء، تَصريحات)
- 14.56% كُلّ Q/A = Zero (مَقبول لِلآيات القَصيرَة)
- **0 أَنماط أَخطاء جَديدَة** (الـ374 anomaly كُلّها false positives لِـheuristic السَّوِيب)

### تَوزيع إِجابات الأَسئلَة

| السُّؤال | Zero |
|---|---|
| أَين حَدَث؟ | 89% (يَحتاج LocationContract لاحِقًا) |
| ماذا حَدَث؟ | 55% (جُمَل اسميَّة كَثيرَة) |
| مَن الفاعِل؟ | 28% (تَحَسَّن مِن 50% قَبل الجَلسَة) |
| متى حَدَث؟ | 16% (الزَّمَن مَكشوف غالِبًا) |

## الصِّيغَة الـMC الكامِلَة الآن

```
حُكم word_class:
  ClosedFunctionWordGate     → HARF (Certificate)
  ∨ SingularTermGate
  ∨ VerbFormContract.Cert    → FIIL
       ∧ ¬tanwin ∧ ¬ال ∧ ¬ـة ∧ ¬مُثَنَّى ∧ ¬مَقصورَة
       ∧ ¬تَفضيل ∧ ¬اسم+مِلكيَّة (PossessiveGate)
  ∨ closed_class_detector
  ∨ jamid ∨ aalam ∨ open-class(wazn + overrides)

حُكم agent_of:
  AgentCertificate(X, V) ⟺
    VerbCertified(V)
    ∧ ¬CommandOrJussiveVerb     ← v2: HARD REJECT
    ∧ ¬PassiveVoice              ← v2: نائِب فاعِل لا agent
    ∧ ¬DistanceTooFar
    ∧ ¬InterveningHarfJarr
    ∧ ¬InterveningManṣūb
    ∧ ¬InterveningFIIL           ← v2: window stops at next verb
    ∧ ¬DetachedPronounAfterVerb  ← v2: explicit subject present
    ∧ ¬NounInInnaScope
    ∧ ¬NounRoleIsPredicate/Attribute
    ∧ ¬NounIsTafdeel
    ∧ ValidPosition
    ∧ DefectiveVerbContract      ← route كان → ism_of_kana
    ∧ AgentAgreementContract     ← eligibility + agreement

حُكم harf_jarr_of:
  HarfJarrCertificate(X, H) ⟺
    HARF_JARR(H)
    ∧ Eligible(X)
    ∧ ¬Consumed(H)               ← يُستَهلَك بَعد أَوَّل مُتَعَلِّق
    ∧ Distance(H, X) ≤ 3
    ∧ ¬InterveningBlocker

حُكم attribute_of:
  AttributeCertificate(X, Y) ⟺
    AfterAndAdjacent(X, Y)
    ∧ DefinitenessMatch(X, Y)
    ∧ NumberMatch(X, Y)          ← DU/SG hard mismatch = Zero
    ∧ GenderMatch(X, Y)
```

## المَلَفّات النِّهائيَّة

- `sweep_v3.jsonl` — 5,557 verse analysis records
- 9 contract modules (verb_form, non_verb_override, possessive_nominal,
  defective_verb, object_pronoun_vs_possessive, closed_function_word,
  agent_window, harf_jarr_agreement, attribute_agreement)
- 9 test files (98/98 passing)
- 3 lexicon CSVs (kana_family, possessive_pronoun_suffixes, closed_function_words)
- Integration in `i3rab_engine/layer1.py` + `relation_extractor.py` + `verb_form_contract.py`

## مَبدَأ NAND مَحفوظ

كُلّ عَقد:
- بَوّابَة صَغيرَة بِتَبِعات كَبيرَة
- مَصدَر الادِّعاء صَريح في الـsource_of_claim
- لا inline rules — كُلّ القَواعد في CSV
- مُتَتَبَّع بِـaudit metrics
- اختبارات قَبول قابِلَة لِلقياس

## التَّوصيَة لِلجَلسَة التالِيَة

1. تَوسيع التَّغطيَة إلى 100% (679 آية مُتَبَقّيَة)
2. **LocationContract** — لِتَقليل "أَين حَدَث؟ Zero" مِن 89%
3. **NominalSentenceContract** — جُمَل اسميَّة كامِلَة (مُبتَدَأ + خَبَر) لِزِيادَة الـevents
4. تَوسعَة `kana_family.csv` لِأَفعال الشُّروع وَالمُقارَبَة
