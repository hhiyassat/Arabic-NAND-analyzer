# M1 — خطة المكونات الأربعة (مُسجَّلة للمستقبل)

> **الحالة:** مؤجَّلة بقرار من 2026-05-17  
> **سبب التأجيل:** تحسين الأسس الثلاثة أولًا (normalizer، segmenter، wazn/root extraction) لِيَبنى M1 على بنية موثوقة لا على بنية تَنشر أخطاءها للأعلى  
> **مرتبط بـ:** `12_Project_Scope_Declaration.md` (الإعلان الدستوري الذي يَحكم M1)  
> **الأولوية الحالية:** Foundation Hardening قبل M1

---

## الخطة الكاملة لـ M1

| المكوّن | المعرف | الأسابيع | الفرع الرياضي | المُخرَج |
|---|---|---|---|---|
| **A. Multi-clause Segmenter** | M1.A | 2-3 | finite automata + قواعد سطحية | `clauses: list[Clause]` لكل نص |
| **B. Speech Act Detector** | M1.B | 2 | منطق propositional + قائمة أفعال قول | `speech_act: {assertion, command, question, vocative}` |
| **C. Negation Scope** | M1.C | 2-3 | scope analysis (تشبه bracket matching) | `negation_scope: [start, end]` لكل أداة نفي |
| **D. Modal Detector** | M1.D | 2 | قائمة موسومة + تصنيف ثنائي (deontic/epistemic) | `modal: {marker, type, strength}` |

**المجموع التقديري:** 8-10 أسابيع للأربعة معًا.

**ترتيب التنفيذ المقترح:** A → B → (C ‖ D بالتوازي)
- A أولًا لأنه يُجزّئ النص لِكل ما بعده يَعمل على وحدات أصغر
- B بعده مباشرة لأنه يَستفيد من تجزئة A
- C و D مستقلان نسبيًا، يمكن التوازي بينهما

---

## ١. M1.A — Multi-clause Segmenter

**الهدف:** تقسيم النص إلى جُمل/clausal units مستقلة مع علاقاتها.

**القواعد السطحية:**
- علامات الترقيم (`. , ؛ ؟ !`)
- حروف العطف المرتبطة بفعل جديد (`و`, `ف`, `ثم`, `بل`, `لكن`)
- أفعال القول (`قال`, `سأل`, `أجاب`, `روى`, `زعم`) → embedded clause يَبدأ بعدها
- صيغ الشرط (`إذا`, `إن`, `لو`, `كلما`) → جملة شرط + جملة جواب

**المُخرَج:**
```python
@dataclass
class Clause:
    text: str
    start_idx: int
    end_idx: int
    type: str  # main, embedded, conditional_protasis, conditional_apodosis, ...
    connective: Optional[str]  # العاطف بينها وبين السابقة
    parent_clause_id: Optional[int]  # للجملة المضمَّنة
    confidence: float  # [0,1]
    alternatives: list[Clause]  # قراءات بديلة
```

**أمثلة الاختبار:**
- "أنا حسين قال لي صالح قم لنصلي" → 3 clauses: identity, speech_act, embedded
- "إن جئتَ زرتُك" → 2 clauses: protasis, apodosis

---

## ٢. M1.B — Speech Act Detector

**الهدف:** تصنيف نوع كل clause إلى فعل خطابي.

**الأصناف الأربعة:**
| الصنف | علامات الكشف |
|---|---|
| `assertion` | جملة خبرية، فعل ماضٍ أو مضارع، لا أمر/استفهام |
| `command` | فعل أمر، لام الأمر مع مضارع، نون الأمر |
| `question` | أداة استفهام (هل/أ/من/ما/كيف/متى/أين/لماذا) |
| `vocative` | أداة نداء (يا/أيها/أيتها) |

**المُخرَج:**
```python
@dataclass
class SpeechAct:
    clause_id: int
    act_type: str  # assertion | command | question | vocative
    markers: list[str]  # الأدلة السطحية
    confidence: float
    alternatives: list[str]
```

---

## ٣. M1.C — Negation Scope

**الهدف:** تحديد ما يَنفيه كل أداة نفي.

**الأدوات المغطاة:**
- `لا` (نهي / نفي مضارع)
- `ما` (نفي ماضٍ غالبًا)
- `ليس` (نفي اسمي)
- `لم` (نفي مضارع جزم)
- `لن` (نفي مضارع نصب — مستقبل)

**القواعد:**
- نطاق `لا/ما/لم/لن` السطحي = الفعل التالي مباشرة + معمولاته
- نطاق `ليس` = الخبر التالي

**المُخرَج:**
```python
@dataclass
class Negation:
    marker: str        # لا / ما / ليس / لم / لن
    marker_idx: int
    scope_start: int
    scope_end: int
    polarity_effect: str  # negate_event | negate_attribute | negate_existence
    confidence: float
```

---

## ٤. M1.D — Modal Detector

**الهدف:** كشف الصيغ المُساعدة/الموجِّهة.

**القائمة الموسومة:**
| المُؤشِّر | النوع | القوة |
|---|---|---|
| يجب / لا بد / حتمًا | deontic | 1.0 (قطعي) |
| ينبغي / يَلزم | deontic | 0.8 |
| يَستحسن / يُفضَّل | deontic | 0.5 |
| يمكن / يجوز / قد | epistemic | 0.5 |
| لعل / عسى | epistemic | 0.4 (تَرجٍّ) |
| ربما / يَحتمل | epistemic | 0.3 |

**المُخرَج:**
```python
@dataclass
class Modal:
    marker: str
    marker_idx: int
    modal_type: str  # deontic | epistemic
    strength: float  # [0,1]
    scope_event: Optional[int]  # token index للفعل المتعلق به
    confidence: float
```

---

## ٥. متطلبات دستورية تُطبَّق على الأربعة

كل مكوّن **يجب** أن يَستوفي الالتزامات الأربعة من `12_Project_Scope_Declaration.md`:

1. ✅ **Source-of-Claim** — كل قرار يُسجّل قاعدته/مصدره
2. ✅ **Confidence-of-Claim** — نسبة ثقة `[0,1]` لكل ادعاء
3. ✅ **Alternatives-Preserved** — القراءات البديلة في الإخراج
4. ✅ **Reversible** — قابل للنَقض من واجهة المستخدم

---

## ٦. الشرط المسبق قبل البدء بـ M1

**M1 لن يَبدأ قبل اكتمال Foundation Hardening:**

| التحسين | الموقع | المعيار |
|---|---|---|
| Normalizer v2 | `normalize_text_pre_pipeline` | تغطية جميع أنواع الهمزة، الألف، التاء المربوطة، الكشيدة، الـ NFC variants |
| Segmenter v2 | `segmenter_adapter` | معالجة صحيحة لـ الله/لله/بالله، تمييز ـِين plural من ـنَ verb suffix، حماية المركَّبات |
| Wazn/Root Extraction v2 | `analyze_word_adapter` + قواعد alasmaa | تغطية فَعّ، فَاعَل، حلّ الـ orphan sukoon، root accuracy ≥ 50% (من 29.6% حاليًا) |

عند اكتمال هذه الثلاثة بمستوى مقبول، يُفتَح M1 رسميًا.

---

## ٧. تذكير

هذه الخطة **مُجمَّدة لحظيًا، ليست مُلغاة**. الـ tasks في النظام تَظلّ موجودة (#48-51) بحالة `pending`. عند العودة، يُحدَّث هذا الملف بالـ baseline القياسي للأسس الثلاثة قبل المتابعة.
