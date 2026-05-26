# PHASE 4 — CERTIFICATE RE-EVALUATION METADATA — SPEC

> **التَّاريخ:** 2026-05-26
> **النِّطاق:** `arabic_analyzer/contextual_resolver/integration.py`
> **النَّوع:** تَوسيع سياسَة الأَهليَّة لِلـ Phase 4 resolver (metadata-only).
> **الحَوكَمَة:** SPEC (هذا) → RULE_LOCK → تَطبيق ضَيِّق → اختبار → A0 → مُلاحَظَة/تَجميد.
> **يُكَمِّل:**
> - `CONSTITUTION.md` §1.2 (ProofObject) + §1.3 (Alternatives-Preserved)
> - `GOVERNANCE.md` §⑦.2 (تَعديل عَلاقَة) — لا يَنطَبِق هُنا لأَنّه لا تُضاف عَلاقَة
> - `معمار_المعنى_العربي/14_Minimal_Complete_Theory.md` (شَرط `SemanticBarrier`)
> - `clean_code/arabic_analyzer/contextual_resolver/resolver.py`
> - `clean_code/arabic_analyzer/contextual_resolver/integration.py`

---

## 1) السُّؤال (Core Question)

> هَل يُمكِن لِـ `ContextualAmbiguityResolver` أَن يُلحِق `phase4_*` metadata لِـ Certificate
> أَلصَقها عَقد سابِق على نَفس الـ surface — **بِدون** أَن يَنقُض القَرار الأَصليّ؟

الإجابَة الدُّستوريَّة (per [§5](#5) أَدناه): **نَعَم، لكن metadata فَقَط**، خَلف flag،
عَلى مَجموعَة surfaces مَحصورَة، وَ مِن مَصادِر مَحصورَة، وَ بِدون أَيّ تَأثير على
`word_class` / `proof_kind` / `source` الأَصليَّة.

---

## 2) الدّافِع (Why)

A0 (2026-05-26) أَثبَتَت أَنّ Layer 1 hook يَعمَل (`classify_with_context_call_count = 2038`)،
لَكِنّ `phase4_selected_function_count = 0`. السَّبَب: كُلّ surface مَدعوم مِن
`HANDLED_SURFACES_NORMALIZED` يَأخُذ Certificate مِن `ClosedFunctionWordGate`
(layer1.py:452, مَع priority 0) أَو مِن `non_verb_override_gate` قَبل أَن يَصِل إلى
`maybe_apply_resolver`، فَيَفشَل الـ resolver في `_is_eligible` لأَنّ
`proof_kind != "Hypothesis"`.

النَّتيجَة: Phase 4 لا يَفعَل شَيئًا في الإِنتاج، مَع أَنَّ الـ plumbing سَليمَة.

**خيارات الإِصلاح المُمكِنَة:**

| الخِيار | الأَثَر | المَخاطِر |
|---|---|---|
| A — الوَضع الحاليّ | لا يَتَغَيَّر شَيء، Phase 4 ميِّت | عَمَل الـ resolver كلُّه dead weight |
| B — تَخفيض الـ gate إلى Hypothesis | يَفتَح المَجال لِـ Phase 4 يُرَقّي | يُغَيِّر قَرار Layer 1 لِـ 8 surfaces — احتِمال انحِدارات في L4/L5 |
| C — **هذا الـ SPEC** | يُشَغِّل Phase 4 على Certificate كَ metadata-only | لا يُغَيِّر أَيّ قَرار قائِم — يُضيف طَبَقَة ملاحَظَة فَقَط |

اختيارُنا: **C** — لأنَّه يَحفَظ MC (no over-claim)، يَحفَظ NAND (no decision flip)،
وَ يُتيح لِـ L6/L7 لاحِقًا أَن يَستَفيد مِن `phase4_selected_function` بِدون أَن يَكسِر
شَيئًا اليَوم.

---

## 3) النِّطاق (Scope)

### 3.1 المَلَفّات المَسموح تَعديلها

- `arabic_analyzer/contextual_resolver/integration.py` — إِضافَة دالَّة
  `_is_eligible_for_reevaluation()` وَ فَرع جَديد في `maybe_apply_resolver()`.
- `test_phase4_certificate_reevaluation.py` — مَلَفّ اختبار جَديد.

### 3.2 المَلَفّات المَمنوع تَعديلها

| المَلَفّ | السَّبَب |
|---|---|
| `i3rab_engine/layer1.py` | لا تَغيير في priority chain |
| `i3rab_engine/engine.py` | الـ hook مُسَلَّم مِن جَلسَة 2026-05-26 |
| `i3rab_engine/types.py` | حَقل `phase4: dict` كافٍ — لا حُقول جَديدَة |
| `closed_function_word_gate.py` | الـ gate يَبقى يُصدِر Certificate (هذا أَساس C) |
| `non_verb_override_gate.py` | نَفس السَّبَب |
| `relation_extractor.py` / `event_extractor.py` | L4/L5 خارِج النِّطاق |
| `resolver.py` / `resolution_rules.py` / `context_features.py` | المَنطِق الدَّاخِليّ ثابِت |
| `data/awzan_cleaned.csv` / `data/contracts/maani/**` / `04_nahw` / `03_juthur` | خارِج النِّطاق |

### 3.3 المَجموعَة المَحصورَة لِلـ surfaces

`HANDLED_SURFACES_NORMALIZED` كَما هي مُعَرَّفَة في `resolver.py:22-24`:

```python
{ "من", "ما", "أي", "متى", "أين", "أنى", "حيث", "بما" }
```

أَيّ surface خارِج هذه المَجموعَة **لا** يَدخُل re-evaluation — يَبقى كَما هو.

### 3.4 المَجموعَة المَحصورَة لِلـ source-prefix gates

| Prefix | المَلَفّ المَصدَر | المُسَوِّغ |
|---|---|---|
| `closed_function_word` | `closed_function_word_gate.py` (priority 0) | A0 أَثبَتَت أَنَّه يَلتَقِط مَن/مَا/مَتَى/أَين/حَيث/بِمَا |
| `non_verb_override_gate` | `non_verb_override_gate.py` | A0 أَثبَتَت أَنَّه يَلتَقِط أَي/أَنَى |

أَيّ `source` لا يَبدَأ بِأَحَد هَذَين الـ prefixes **لا** يَدخُل re-evaluation — مَثَلًا
Certificate مِن `MasterTokenLookup` (MASAQ) أَو `LinguisticSourceRegistry` يَبقى
كَما هو، حَتَّى لَو كانَ الـ surface في `HANDLED_SURFACES_NORMALIZED`.

---

## 4) القَواعِد المَحظورَة (Negative claims)

هذا الـ SPEC لا يَسمَح بِـ:

- تَخفيض أَيّ Certificate إلى Hypothesis في أَيّ مَكان.
- تَعديل `result["word_class"]` في مَسار re-evaluation.
- تَعديل `result["proof_kind"]` في مَسار re-evaluation.
- تَعديل `result["source"]` في مَسار re-evaluation.
- تَعديل `result["closed_class_kind"]` أَو `result["proof_contract"]` أَو
  `result["proof_alternatives"]` الأَصليَّة في مَسار re-evaluation.
- توسيع `HANDLED_SURFACES_NORMALIZED` خارِج الـ8 surfaces.
- توسيع الـ source-prefix gates خارِج الِاثنَين أَعلاه.
- تَفعيل re-evaluation عِندَما الـ flag OFF.
- استِخدام `phase4_*` metadata في L4/L5 (هَذا يَستَوجِب SPEC مُستَقِلّ لاحِق).
- ربط re-evaluation بِأَيّ قاعِدَة مِن `04_nahw` / `03_juthur` / `awzan` / المَعاني.

---

## 5) السُّلوك المَطلوب (Required behavior)

### 5.1 شَرطا الأَهليَّة الجَديدَة

```python
_is_eligible_for_reevaluation(result, surface) ⇔
    _strip(surface) ∈ HANDLED_SURFACES_NORMALIZED
  ∧ result["proof_kind"] == "Certificate"
  ∧ result["source"] starts with one of:
        "closed_function_word",
        "non_verb_override_gate"
```

### 5.2 إِجراء re-evaluation

عِندَما تَتَحَقَّق الأَهليَّة الجَديدَة (وَ الـ standard `_is_eligible` فَشِلَت أَوَّلًا):

1. **Snapshot** الـ originals:
   - `original_word_class = result["word_class"]`
   - `original_source = result["source"]`
   - `original_proof_kind = result["proof_kind"]`
   - `original_candidates = list(result["registry_candidates"] or result["proof_alternatives"] or [])`

2. **Run** الـ resolver عَلى الـ surface مَع الـ context windows.

3. **Attach** الـ metadata الآتيَة فَقَط (بِدون تَعديل أَيّ حَقل غَير مَسبوق بِـ `phase4_`):
   ```python
   result["phase4_review_mode"]            = "certificate_re_evaluation"
   result["phase4_original_word_class"]    = original_word_class
   result["phase4_original_source"]        = original_source
   result["phase4_original_proof_kind"]    = original_proof_kind
   result["phase4_original_candidates"]    = original_candidates
   result["phase4_source"]                 = "ContextualAmbiguityResolver"
   result["phase4_selected_function"]      = res.selected_function
   result["phase4_reason"]                 = res.reason
   result["phase4_context_features"]       = res.context_features
   result["phase4_masaq_compatible_class"] = res.masaq_compatible_class
   ```

4. **Derive** `phase4_certainty` (metadata فَقَط — لا يَمَسّ `proof_kind` الرَّئيس):
   - إِذا `res.selected_function == "unresolved_ambiguous"` → `"Hypothesis"`.
   - وَإِلّا → `res.certainty` كَما هو (`"Certificate"` أَو `"Hypothesis"`).

### 5.3 ترتيب الأَولويَّة في `maybe_apply_resolver`

```
if not is_enabled():               return result        # 1. flag OFF — byte-identical
if _is_eligible(result, surface):  return promote(...)  # 2. Hypothesis path (unchanged)
if _is_eligible_for_reevaluation(result, surface):
                                    return reeval(...)  # 3. NEW: Certificate metadata-only
return result                                            # 4. else — no change
```

الـ standard path (الـ Hypothesis path القائِم) **يَبقى مُقَدَّمًا** على re-evaluation. لا
يُمكِن لِكِلا الـ paths أَن يَنفُذا عَلى نَفس الـ token: الـ standard يَتَطَلَّب Hypothesis
وَ الـ new يَتَطَلَّب Certificate، وَهما mutually exclusive عَلى `proof_kind`.

---

## 6) عَلاقَة مَع ProofObject (CONSTITUTION §1.2)

- الـ `proof_kind` الأَصليّ ثابِت → الـ ProofObject الرَّئيس لا يَتَأَثَّر.
- الـ `phase4_certainty` حَقل metadata مُسَتَقِلّ، **لا يُعتَبَر** ProofKind ثانيًا.
- الـ `source_of_claim` لِلقَرار النِّهائيّ يَبقى `closed_function_word:<CAT>` أَو
  `non_verb_override_gate:<reason>` — أَيّ ادِّعاء يَستَنِد إلى الـ word_class
  يَستَنِد لِلـ source الأَصليّ.
- الـ `phase4_source = "ContextualAmbiguityResolver"` يُفَسِّر مَن أَلصَق الـ metadata،
  لا مَن أَخَذ القَرار. لا يُسمَح لأَيّ ادِّعاء لاحِق أَن يَستَنِد إلى `phase4_source`
  كَـ source-of-claim لِـ `word_class`.

---

## 7) عَلاقَة مَع MC (CONSTITUTION §1.4)

اختِبار الحَذف: **لَو حَذَفنا re-evaluation، هَل تَنهار شَهادَة قائِمَة؟**

- الـ word_class الأَصليّ مَحفوظ → لا تَنهار.
- الـ proof_kind الأَصليّ مَحفوظ → لا تَنهار.
- الـ source الأَصليّ مَحفوظ → لا تَنهار.
- L4/L5 لا تَستَخدِم `phase4_*` → لا تَنهار.

**النَّتيجَة:** re-evaluation **لَيسَ** عَقدًا ضَروريًّا لِأَيّ شَهادَة قائِمَة اليَوم —
وَلِذلِك يَجوز إِضافَتُه خَلف flag بِدون انتِهاك MC. عِندَما يَستَفيد L6/L7 مِنه
لاحِقًا، سَيُصبِح ضَروريًّا، وَ سَيَنتَقِل خارِج الـ flag بِـ SPEC جَديد.

---

## 8) عَلاقَة مَع NAND (Alternatives-Preserved)

- `phase4_original_candidates` يَحفَظ الـ alternatives الأَصليَّة كَما كانَت قَبل
  re-evaluation.
- الـ `proof_alternatives` الرَّئيس لا يُلمَس.
- لا winner-takes-all — كِلا الـ originals وَ الـ phase4 موجودان.

---

## 9) سُلوك flag OFF (Byte-identical guarantee)

عِندَما `ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER` غَير مُفَعَّل:

- `maybe_apply_resolver` يُرجِع `result` كَما هو — أَوَّل سَطر في الدالَّة.
- لا تَفعيل لِلـ resolver.
- لا attach لِأَيّ `phase4_*` key.
- النَّتيجَة على A0 OFF: مُماثِلَة تَمامًا لِما قَبل هَذا التَّغيير.

`TokenI3rab.phase4` يَبقى `{}` على flag OFF لأَنّ `_extract_phase4_metadata`
في `engine.py:51-78` لا يَجِد أَيّ مِفتاح `phase4_*` في `r1`.

---

## 10) القياسات المُتَوَقَّعَة (Expected A0 metrics)

| metric | OFF | ON قَبل C | ON بَعد C |
|---|---:|---:|---:|
| classify_call_count | 2038 | 2038 | 2038 |
| classify_with_context_call_count | 0 | 2038 | 2038 |
| contextual_resolver_applications | 0 | 0 | **> 0** |
| phase4_selected_function_count | 0 | 0 | **> 0** |
| event_count | 547 | 547 | **547** (لا تَغيير) |
| relation_count | 1414 | 1414 | **1414** (لا تَغيير) |
| segmentation_leak_count | 0 | 0 | 0 |
| fragment_event_count | 0 | 0 | 0 |

أَيّ تَغيير في `event_count` أَو `relation_count` يَدُلّ عَلى انتِهاك §4 — يَجِب
التَّحَقُّق وَ التَّراجُع.

---

## 11) ما لا يَنُصّ علَيه هَذا الـ SPEC

- لا يُحَدِّد كَيف يَستَهلِك L6/L7 الـ `phase4_*` metadata — هَذا SPEC مُستَقِلّ.
- لا يُلزِم بِتَقديم رِأي على هَل تَخفيض الـ gate مُناسِب لاحِقًا (الخِيار B) — قَرار
  مُؤَجَّل لِسَجَل حَوكَمَة جَديد إِذا لَزِم.
- لا يَفتَح بَطاقَات جَديدَة في `closed_function_words.csv` أَو
  `non_verb_override_gate.py`.
- لا يَتَدَخَّل في حَوكَمَة ALASMA (`alasmaa/`) أَو NAA (`new_arabic_analyzer/`) —
  هذا الـ SPEC داخِل `hussein/clean_code/` فَقَط.

---

## 12) القاعِدَة الذَّهَبيَّة

> **`phase4_*` metadata يَزيد المَعرِفَة، لا يَنقُض الشَّهادَة.**
>
> الـ Certificate الَّذي أَلصَقه `closed_function_word_gate` يَبقى Certificate.
> الـ resolver فَقَط يَقول: «لَو نَظَرت إلى السِّياق، هذا هو الدَّور الَّذي أَراه — حَفِظتُه
> لَك لِلقِياس، وَلَم أَمَسّ قَرارَك».
