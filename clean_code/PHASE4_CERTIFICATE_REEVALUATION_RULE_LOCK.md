# PHASE 4 — CERTIFICATE RE-EVALUATION METADATA — RULE_LOCK

> **التَّاريخ:** 2026-05-26
> **الحالَة:** ★ Frozen executable subset — Batch A only.
> **الشَّقيق:** [`PHASE4_CERTIFICATE_REEVALUATION_SPEC.md`](PHASE4_CERTIFICATE_REEVALUATION_SPEC.md)
> **المَعنى:** كُلّ ادِّعاء في هَذِه الوَثيقَة قابِل لِلتَّنفيذ فَقَط داخِل القُيود أَدناه.
> **النَّمَط:** يَتَّبِع نَفس نَمَط `alasmaa/docs/*_RULE_LOCK.md`.

---

## ١. ما هَذِه الوَثيقَة لا تُجيزه (Negative locks — normative)

- **لا** تُجيز تَخفيض أَيّ Certificate إلى Hypothesis في `closed_function_word_gate`
  أَو `non_verb_override_gate` أَو في أَيّ مَكان.
- **لا** تُجيز تَعديل `result["word_class"]` في مَسار re-evaluation.
- **لا** تُجيز تَعديل `result["proof_kind"]` في مَسار re-evaluation.
- **لا** تُجيز تَعديل `result["source"]` في مَسار re-evaluation.
- **لا** تُجيز تَعديل `result["proof_contract"]` أَو `result["closed_class_kind"]`
  أَو `result["proof_alternatives"]` الأَصليَّة في مَسار re-evaluation.
- **لا** تُجيز توسيع `HANDLED_SURFACES_NORMALIZED` خارِج الـ8 surfaces الَّتي يُعَرِّفها
  `arabic_analyzer/contextual_resolver/resolver.py:22-24`.
- **لا** تُجيز توسيع الـ source-prefix gates خارِج الِاثنَين الواردَين في §٣.٢.
- **لا** تُجيز تَفعيل re-evaluation بِدون `ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER=1`.
- **لا** تُجيز استِهلاك أَيّ `phase4_*` مِفتاح في L4 (`relation_extractor.py`) أَو L5
  (`event_extractor.py`) أَو L6/L7.
- **لا** تُجيز ربط هَذِه القَواعِد بِأَيّ مِلَفّ في `04_nahw` / `03_juthur` / `awzan`
  أَو `data/contracts/maani/`.
- **لا** تُجيز تَفعيل re-evaluation عَلى Certificate صَدَرَ مِن `MasterTokenLookup`،
  `LinguisticSourceRegistry`، `TanwinHardBlock`، `ExplicitVerbsLexicon`،
  أَو أَيّ مَصدَر آخَر غَير الِاثنَين المَنصوصَين في §٣.٢.

---

## ٢. ما تُجيزه (Positive locks — single batch)

### قاعِدَة A1 — `Phase4_CertificateReevaluation:v1`

**المَجال:** `arabic_analyzer/contextual_resolver/integration.py`
**الإِجراء:** إِلحاق `phase4_*` metadata بِالـ `result` dict بِدون أَيّ تَأثير على
الحُقول غَير المَسبوقَة بِـ `phase4_`.

**شَرطا التَّفعيل (كِلاهُما إِلزاميّ):**

1. `is_enabled()` → `True` (الـ flag مُفَعَّل).
2. `_is_eligible_for_reevaluation(result, surface)` → `True`، بِمَعنى:
   - `_strip(surface) ∈ HANDLED_SURFACES_NORMALIZED`، أَيّ:
     `surface ∈ { "من", "ما", "أي", "متى", "أين", "أنى", "حيث", "بما" }`.
   - `result["proof_kind"] == "Certificate"`.
   - `result["source"]` يَبدَأ بِواحِد مِن:
     - `"closed_function_word"`
     - `"non_verb_override_gate"`
3. شَرط مُسبَق إِضافيّ: الـ standard `_is_eligible(result, surface)` كانَ `False`
   (لأَنّ `proof_kind != "Hypothesis"`). لِضَمان أَنّ هَذا الفَرع لا يَتَنافَس مَع الـ
   Hypothesis-path القائِم.

**المُخرَج المَلصوق (exact keys):**

| المِفتاح | القِيمَة | المَصدَر |
|---|---|---|
| `phase4_review_mode` | `"certificate_re_evaluation"` | ثابِت |
| `phase4_original_word_class` | snapshot قَبل re-eval | `result["word_class"]` |
| `phase4_original_source` | snapshot قَبل re-eval | `result["source"]` |
| `phase4_original_proof_kind` | `"Certificate"` ثابِت في هَذا الفَرع | `result["proof_kind"]` |
| `phase4_original_candidates` | `list[...]` | `result["registry_candidates"] or result["proof_alternatives"] or []` |
| `phase4_source` | `"ContextualAmbiguityResolver"` | ثابِت |
| `phase4_selected_function` | str | `res.selected_function` |
| `phase4_reason` | str / None | `res.reason` |
| `phase4_context_features` | dict | `res.context_features` |
| `phase4_masaq_compatible_class` | str / None | `res.masaq_compatible_class` |
| `phase4_certainty` | `"Certificate"` / `"Hypothesis"` | per §٢.٢ أَدناه |

### §٢.٢ — اشتِقاق `phase4_certainty`

```python
if res.selected_function == "unresolved_ambiguous":
    phase4_certainty = "Hypothesis"
else:
    phase4_certainty = res.certainty   # "Certificate" أَو "Hypothesis" مِن الـ resolver
```

`phase4_certainty` حَقل metadata. **لا** يَدخُل في `result["proof_kind"]`. **لا**
يَدخُل في ProofObject الرَّئيس. **لا** يُستَخدَم مِن L4/L5.

---

## ٣. النِّطاق المَحفوظ (Locked scope)

### ٣.١ الـ surfaces المَحصورَة

| # | Vocalized examples (لا حَصر) | Normalized |
|---|---|---|
| 1 | مَنْ، مِنْ، مِنَ، مَنِ | `من` |
| 2 | مَا، مَآ | `ما` |
| 3 | أَيُّ، أَيَّةَ | `أي` |
| 4 | مَتَى، مَتَىٰ | `متى` |
| 5 | أَيْنَ | `أين` |
| 6 | أَنَّى، أَنَىٰ | `أنى` |
| 7 | حَيْثُ | `حيث` |
| 8 | بِمَا، بِمَآ | `بما` |

أَيّ surface لَيسَ في هَذِه القائِمَة بَعد `_strip()` → خارِج النِّطاق → لا تَفعيل.

### ٣.٢ الـ source-prefix gates المَحصورَة

| Prefix exact | المَلَفّ المَصدَر | مِثال مِن A0 |
|---|---|---|
| `closed_function_word` | `closed_function_word_gate.py` (priority 0) | `source='closed_function_word:WHEN'` |
| `non_verb_override_gate` | `non_verb_override_gate.py` | `source='non_verb_override_gate:ends with ـى → maqsura noun ...'` |

الفَحص: `result["source"].startswith(prefix)`. لِكُلّ ما عَدا هَذَين → خارِج النِّطاق.

---

## ٤. ما لا يَتَغَيَّر (Invariants under A1)

أَيّ token دَخَلَ مَسار re-evaluation يَخرُج مَع الـ invariants التَّاليَة مَحفوظَة:

```python
assert result["word_class"]        == phase4_original_word_class
assert result["source"]            == phase4_original_source
assert result["proof_kind"]        == phase4_original_proof_kind  # "Certificate"
assert result["proof_kind"]        == "Certificate"
assert result.get("proof_contract") == <unchanged>
assert result.get("closed_class_kind") == <unchanged>
assert result.get("proof_alternatives") == <unchanged>
```

أَيّ test يَنتَهِك أَحَد هَذِه الـ invariants → فَشَل A1، يَجِب التَّراجُع.

---

## ٥. اختبار الحَذف (Removal test)

| لَو حُذِفَ | الأَثَر | الحُكم |
|---|---|---|
| `_is_eligible_for_reevaluation` | الـ resolver لا يَرى Certificates، Phase 4 يَعود dead weight | **غَير ضَروريّ لِأَيّ شَهادَة قائِمَة** — لِذلِك مَسموح إِضافَته خَلف flag |
| `phase4_*` metadata | L6/L7 لاحِقًا لا يُمكِن قِياس فائِدَة الـ resolver | غَير ضَروريّ اليَوم — ضَروريّ مُستَقبَلًا (SPEC جَديد) |

النَّتيجَة: قاعِدَة A1 لا تَكسِر MC ; هي **إِضافَة** لا **اعتِماد**.

---

## ٦. سُلوك flag OFF (مَضمون byte-identical)

```python
def maybe_apply_resolver(result, surface, *, prev_tokens=None, next_tokens=None) -> dict:
    if not is_enabled():
        return result            # ← أَوَّل سَطر — لا تَغيير
    ...
```

A1 لا يُدخِل أَيّ كود قَبل هَذا الـ guard. النَّتيجَة: على flag OFF، الـ output
byte-identical مَع الـ baseline.

A0 تَأكيد:

| metric | OFF قَبل A1 | OFF بَعد A1 |
|---|---:|---:|
| `phase4_selected_function_count` | 0 | 0 |
| `event_count` | 547 | 547 |
| `relation_count` | 1414 | 1414 |
| `TokenI3rab.phase4` لِكُلّ token | `{}` | `{}` |

---

## ٧. القَناة الوَحيدَة لِلتَّوسيع

أَيّ تَوسيع لاحِق (مَثَلًا Batch B لِيَشمَل surfaces أُخرى أَو gates أُخرى) يَتَطَلَّب:

1. SPEC جَديد بِاسم `PHASE4_CERTIFICATE_REEVALUATION_BATCH_B_SPEC.md`.
2. RULE_LOCK جَديد بِاسم `PHASE4_CERTIFICATE_REEVALUATION_BATCH_B_RULE_LOCK.md`.
3. تَطبيق ضَيِّق مُنفَصِل.
4. اختبارات مُسَمَّاة `t_batch_b_*`.
5. A0 بَعد التَّطبيق.

**مَمنوع** تَوسيع هَذا الـ RULE_LOCK بِإضافَة بُنود — هو مُجَمَّد على A1 فَقَط.

---

## ٨. مُلاحَظَة لِلمُتَلَقّي

> هَذِه القاعِدَة لا تَفتَح Phase 4 لِـ L6/L7. هي تُتيح فَقَط أَن نَرى — في الـ JSON
> output — ماذا يَقول الـ resolver عَلى surfaces مُسَلَّمَة سابِقًا. القَرار النِّهائيّ
> يَبقى لِلـ gate الَّذي أَخَذَه أَوَّلًا. الـ resolver يَكتُب رَأيه بِلا قَلَم تَنفيذ.
