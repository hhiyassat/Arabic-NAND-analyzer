# Project Status — حالة المشروع
## معمار المعنى العربي متعدد الطبقات

> **آخر تحديث:** 2026-05-18.  
> هذا الملف يلخّص أين نقف الآن: الإنجازات الدستورية، الإنجازات الحاسوبية، الفجوات المتبقية، والخطوات اللاحقة.

---

## 0. الوضع الحالي (2026-05-18)

**إعلانات دستورية نَفذت:**
- القاعدة #21 — المشروع "محاكاة تحليلية شفافة قابلة للحوكمة" (انظر `12_Project_Scope_Declaration.md`)
- القاعدة #22 — `clean_code/wazn_matcher.py` هو المُحلِّل الرسمي (انظر `13_Wazn_Matcher_Declaration.md`)

**التَقدُّم على الأسس الثلاثة:**

| الأساس | الحالة | الأداء الحالي |
|---|---|---|
| **Wazn/Root Extraction** | ✅ **مُجمَّد v2.4 stable** | top-1=59.3%، top-3=64.6% على MASAQ. تَفاصيل: `clean_code/FREEZE_v2.4.md` |
| **Normalizer v2** | ⏳ التالي | Task #52 — يُبدأ الآن |
| **Segmenter v2** | ⏳ بعد Normalizer | Task #53 |

**القرار الحالي:** الانتقال من الـ wazn_matcher (المُكتمل لمستوى مقبول) إلى Normalizer كأولوية فورية. التحسينات المؤجَّلة على الـ wazn_matcher مُسجَّلة في `clean_code/FREEZE_v2.4.md` وتُستأنف بعد إكمال Foundation.

**M1 (M1.A-D)** مؤجَّل لما بعد Foundation، مُسجَّل في `M1_Plan_Recorded.md`.

---

## 1. الموقع المعماري

المشروع **خرج رسميًا من مرحلة "التثبيت الداخلي"** إلى مرحلة **التوسع الحاسوبي المنضبط** بعد تحقق جميع شروط الانتقال في `10_Stabilization_Tracker.md`:

| الشرط الدستوري | الحالة |
|---|---|
| Q1 (المركز) محسوم | ✅ Layer-Centric Dynamic System |
| Q2 (State) محسوم | ✅ خمسة أنماط متمايزة |
| اثنان من الفروق الستة محسومان | ✅ Entity vs State + Identity vs Continuity |
| Canonical Definitions مختبَرة | ✅ في `02_Core_Concepts.md` |
| `11_Abstraction_Levels.md` مكتوب | ✅ مكتمل |

---

## 2. الأسئلة الأربع المؤسسة

| السؤال | الحالة |
|---|---|
| **Q1** — مركز النظام | ✅ محسوم: Layer-Centric، مراكز محلية لكل طبقة، Meaning Flow مركز جامع أعلى |
| **Q2** — طبيعة State | ✅ محسوم: عائلة من 5 أنماط (Event-Residue، Event-Continuation، Identity-Pattern، Pure Attribute، Structural-Condition Inducer) |
| **Q3** — موقع اللغة | 🟡 مفتوح — تمهيد في `11_Abstraction_Levels.md` |
| **Q4** — منع التضخم | 🟡 مفتوح — معيار غير صريح |

## 3. الفروق الستة الجوهرية

| الفرق | الحالة |
|---|---|
| Entity vs State | ✅ محسوم جزئيًا (Q1 + Q2) |
| Identity vs Continuity | ✅ محسوم في `Distinction_Identity_vs_Continuity.md` |
| Event vs Transformation | 🟡 معلَّق |
| Relation vs Attribute | 🟡 معلَّق |
| Meaning vs Interpretation | 🟡 معلَّق |
| Context vs Environment | 🟡 معلَّق |

---

## 4. وثائق المشروع الدستورية

### الملفات الأساسية الـ 12 (في `معمار_المعنى_العربي/`)

| رقم | الملف | الحالة |
|---|---|---|
| 00 | `Project_Constitution.md` | ✅ مكتمل |
| 01 | `General_Framework.md` | ✅ مكتمل |
| 02 | `Core_Concepts.md` | ✅ محدَّث (Q2 + Identity/Continuity) |
| 03 | `Meaning_Flow.md` | ✅ مكتمل |
| 04 | `Core_Ontology_Primitives.md` | ✅ محدَّث (Entity كعقدة مشتقة) |
| 05 | `Relations_and_Events.md` | ✅ مكتمل |
| 06 | `Arabic_Language_Layer.md` | ✅ مكتمل |
| 07 | `Context_Probability_Resolution.md` | ✅ مكتمل |
| 08 | `Future_Files_Map.md` | ✅ مكتمل |
| 09 | `Open_Questions.md` | ✅ مكتمل |
| 10 | `Stabilization_Tracker.md` | ✅ محدَّث (Q1, Q2, الفروق، آثار الاختبارات) |
| 11 | `Abstraction_Levels.md` | ✅ مكتمل |
| — | `قاعدة_دستورية_عليا.md` | ✅ |

### الوثائق التحليلية

| الملف | الوصف |
|---|---|
| `Q2_State_Test_From_Huruf.md` | اختبار سلوكي على 7 حروف |
| `Q2_State_Test_From_Entities.md` | اختبار على 4 حالات كيانية |
| `Architecture_Test_Sample_01.md` | تطبيقي على نص قاعدي (إنّ مع العسر) |
| `Architecture_Test_Sample_02.md` | تطبيقي على نص حدثي (ألقى موسى عصاه) |
| `Distinction_Identity_vs_Continuity.md` | حسم الفرق الثاني |
| `Computational_Linkage.md` | ربط البيانات بالكود بالمعمار |
| `Required_Datasets.md` | قائمة البيانات المطلوبة |
| `Remaining_Data_Gaps.md` | الفجوات الفعلية المتبقية |
| `Project_Status.md` (هذا) | الحالة الحالية |

---

## 5. الكود (في `src/architecture_test/`)

### Loaders (11)

| الـ Loader | المصدر | الحجم/الوظيفة |
|---|---|---|
| `huruf_loader.py` | `huruf_maani_normalization/huruf_maani_unified_master.xlsx` | 179 حرف موحَّد |
| `jawamid_loader.py` | `data/الجوامد.xlsx` | 20 تصنيف، 116 مثال |
| `mushtaqat_loader.py` | `data/Mushtaqat_*.xlsx` | 80 وزن، 16 باب |
| `aalam_loader.py` | `data/extracted/aalam_from_masaq.csv` | 193 علم مصنَّف |
| `verb_frames_loader.py` | `data/extracted/verb_frames_from_quran_i3rab.csv` | 6,757 فعل مع توزيع الأدوار |
| `semantic_fields_loader.py` | `data/extracted/semantic_fields/*.json` | 8 حقول، 200 عضو |
| `conjugation_loader.py` | `data/extracted/verb_conjugations_past.csv` | 2,981 جذر × 13 صيغة |
| `verb_suffix_classifier.py` | جدول صرفي داخلي | 10 لواحق فعلية (تُ، تَ، تِ، تْ، نَا، وا، تُمْ، تُنَّ، نَ، تُمُو) → person/number/gender |
| `analyze_word_adapter.py` | `alasmaa/analyze_word.py` (live import) | استخراج الوزن والجذر |
| `segmenter_adapter.py` | `salehan/segmenter.py` + `new_arabic_analyzer/normalize.py` | normalize + فصل البادئات واللواحق |
| **`diacritizer_adapter.py`** | **`salehan/Models_gpt52`** | **تشكيل آلي للنصوص غير المشكَّلة (Step −2)** |
| `alasmaa_analyzer.py` | shim شفاف | للتكامل القديم |

### Pipeline (`pipeline.py`)

**الخطوات الكاملة (14):**
1. **Step −2** — Diacritization (salehan/Models_gpt52) — تشكيل آلي إن كان النص غير مشكَّل
2. **Step −1** — Normalize (NFC + آ → ءَ)
3. **Step 0a** — Segmenter (فصل البادئات واللواحق)
4. **Step 0b** — analyze_word (الوزن + الجذر، مع stem-retry)
5. **Step 1** — Meaning Flow (10 مراحل من العلامة إلى الفهم)
6. **Step 2** — Layer-Centric Decomposition (9 طبقات)
7. **Step 3** — Huruf dataset matching
8. **Step 3.5** — Word classification (اسم/فعل/حرف + wazn + root)
9. **Step 3.55** — Semantic Field membership
10. **Step 3.6** — Frame Semantics from Quran
11. **Step 3.65** — Verb suffix classification (تاء/نون/واو/ألف → ضمير/عدد/جنس)
12. **Step 3.7** — Past-tense conjugation match (مُضيَّق بأدلة 3.65)
13. **Step 4** — Five state patterns (Q2)
14. **Step 5** — Resolution & probability
15. **Step 6** — Verdict (held / gaps)

**سلوك Step 3.65 (Verb suffix classification):**
- يستخرج معلومات الضمير/العدد/الجنس من لواحق الأفعال التي يكشفها الـ segmenter.
- يعمل **حتى لو فشل تطابق الوزن من الـ 80** (مثال: GPT52 ينتج رَايَتْ بدل رَأَيْتُ — تْ → تاء التأنيث الساكنة → 3sg_f → هي).
- لواحق مغطاة: تُ، تَ، تِ، تْ، نَا، وا، تُمْ، تُنَّ، نَ، تُمُو (10 لواحق).
- نتائجه تُستخدم في Step 3.7 لتضييق مرشحي الضمير عند تطابق الصيغة في جدول التصريف.
- **بوابة word_class:** استبعاد قاسٍ لـ aalam/jamid/harf/operator (مثل رَمَضَانَ لا يُحلَّل لاحقتُه نَ). يُسمح لـ verb بكل اللواحق؛ يُسمح لـ mushtaq/unknown فقط إن كانت اللاحقة قطعية الفعلية (تُ/تَ/تِ/تُمْ/تُنَّ/نَا/تُمُو/وا) لتجاوز خطأ alasmaa في تصنيف الماضي كصفة مشبهة.
- **تمييز نون النسوة من نون الرفع:** بحسب نهاية الجذع — جذع ينتهي بـ و/ا قبل نَ → نون الرفع مضارع (تَشْكُرُونَ، أنتم/هم)؛ ينتهي بـ ي → نون الرفع 2sg-f (تَكْتُبِينَ، أنتِ)؛ ينتهي بساكن → نون النسوة ماضٍ (ذَهَبْنَ، هن).
- **تمييز واو الجماعة مضارع من ماضٍ:** جذع يبدأ بـ تـ → 2pl_m (لِتُكْمِلُوا = أنتم)؛ غير ذلك → 3pl_m (ذَهَبُوا = هم).

**سلوك Step −2 (Diacritization):**
- إذا كان النص غير مشكَّل (نسبة الحركات < 8%) → يُشغَّل GPT52 تلقائيًا.
- إذا كان مشكَّلًا مسبقًا → يُتخطى GPT52 مباشرة.
- خيارات CLI: `--gpt52-dir`، `--skip-diacritize`، `--force-diacritize`.
- النص الأصلي والمُشكَّل يُطبعان على stderr قبل التقرير.
- **ملاحظة:** جودة التشكيل تعتمد على النموذج (GPT52 قد ينتج رَايَتْ بدل رَأَيْتُ). هذا حدّ نموذجي، لا حدّ معماري.

### Word Classification Priority (الأولوية الدستورية)

```
harf > operator > jamid > aalam > verb-heuristic > mushtaq > pattern-only > unknown
```

---

## 6. البيانات (إجمالي)

### في `hussein/data/` (محلي)

| الملف | الحجم |
|---|---|
| `Huruf_Maani_Five_Scholars_With_Ibn_Hisham.xlsx` | 401 إدخال خام |
| `Mushtaqat_Full_Weights_Table.xlsx` | جدول كامل |
| `Mushtaqat_Weights_Final_Corrected_With_Fa3l-minimall.xlsx` | 80 وزن |
| `الجوامد.xlsx` | 20 تصنيف، 116 مثال |
| `audited_roots.csv` | 4,769 جذر مدقَّق |
| `extracted/aalam_from_masaq.csv` | 193 علم |
| `extracted/verb_frames_from_quran_i3rab.csv` | 6,757 فعل |
| `extracted/verb_conjugations_past.csv` | 38,753 صيغة فعلية |
| `extracted/semantic_fields/*.json` | 200 عضو في 8 حقول |
| `huruf_maani_normalization/huruf_maani_unified_master.xlsx` | 179 حرف |

### في مشاريع شقيقة (موارد خارجية مربوطة)

- `alasmaa/` — analyze_word.py + Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx + operators
- `salehan/` — segmenter.py + zarf_engine + mabni_registry
- `new_arabic_analyzer/` — normalize.py + 02_mabniyat (29 ملف) + 03_juthur_mushtaqat + 04_nahw + 01_phonology + MASAQ + quran_i3rab

---

## 7. الفجوات البيانية (G1-G17)

| ID | الفجوة | الحالة |
|---|---|---|
| G1 | شبكة المرادفات/الأضداد | 🔴 مفتوحة (تحتاج WordNet) |
| G2 | معاني الجذور الجامعة | 🔴 مفتوحة (تحتاج لسان العرب رقمي) |
| G3 | تعريفات الكلمات | 🔴 مفتوحة (تحتاج معجم) |
| **G4** | **الأعلام الموسَّعة** | ✅ **منجَزة v1** |
| **G5** | **Frame Semantics للأفعال** | ✅ **منجَزة v1** |
| G6 | كوربس الحديث | 🟡 مفتوحة |
| G7 | كوربس الشعر | 🟡 مفتوحة |
| G8 | Sentiment/Connotation | 🟡 مفتوحة |
| G9 | المعاني الحضارية | 🟡 مفتوحة |
| **G10** | **جداول التصريف** | ✅ **منجَزة v1** (الماضي + الصحيح السالم) |
| **G11** | **الحقول الدلالية** | ✅ **منجَزة v1** (8 حقول) |
| G12 | الأعداد الكاملة | 🟡 مفتوحة |
| G13-G17 | تحسينات صغيرة | 🟢 مفتوحة |

**نسبة الإنجاز:** 4 من 17 فجوة (24%) أُغلِقت في الجولة الأولى من الإنجاز الحاسوبي.

---

## 8. الخطوات الموصى بها (لا تُنفَّذ تلقائيًا)

### أولوية قريبة

1. **تنقية يدوية لـ G4** — مراجعة 85 إدخال "other" + إصلاح bug تقشير "فرعون".
2. **توسعة G10** — المضارع والأمر للأفعال الصحيحة السالمة.
3. **اختبار شامل Sample 03** — على نص متنوع (ليس قرآنيًا) لرؤية أداء loaders جديدة.

### أولوية متوسطة

4. **G12 (الأعداد)** — توليد آلي قابل.
5. **G6 (كوربس الحديث)** — استيراد من مصادر مفتوحة.
6. **G7 (كوربس الشعر)** — استيراد من Diwan API.

### أولوية عالية لكن جهد كبير

7. **G1 (المرادفات/الأضداد)** — استيراد Arabic WordNet أو بناء seed يدوي.
8. **G2 + G3** — مشروع فرعي لمعالجة لسان العرب رقميًا.

### الأسئلة الدستورية المتبقية

9. **Q3 (موقع اللغة)** — يحتاج تصميم اختبار جديد.
10. **Q4 (منع التضخم)** — معيار صريح للقبول.
11. **الفروق الأربعة المتبقية** — Event vs Transformation، Relation vs Attribute، Meaning vs Interpretation، Context vs Environment.

---

## 9. الإحصائيات الكلية

- **12 ملف دستوري + 7 وثائق تحليلية** = 19 ملف معماري.
- **11 loaders** في pipeline متكاملة (يشمل diacritizer GPT52).
- **14 خطوة pipeline** (من Diacritization إلى Verdict).
- **45,910+ إدخال بياني** أُضيف في الجولة الأخيرة.
- **8 ملفات بيانات** في `hussein/data/`.
- **4 مشاريع شقيقة مربوطة:**
  - `alasmaa/` — analyze_word + Mushtaqat weights.
  - `salehan/` — segmenter + zarf_engine + **Models_gpt52 (diacritizer)**.
  - `new_arabic_analyzer/` — normalize + 02_mabniyat + MASAQ + quran_i3rab + audited resources.
  - `huruf_maani_normalization/` — الحروف الموحَّدة.
- **17 فجوة بيانية مرصودة**، 4 منها مُنجَزة، 3 منها 🔴 صعبة، 7 منها 🟡 ممكنة، 3 منها 🟢 سهلة.
- **قدرة جديدة:** قبول النصوص **غير المشكَّلة** كمدخل (يُشكِّلها GPT52 تلقائيًا).

---

## 10. القاعدة الحاكمة على هذا الموقع

> **المشروع في وضع نموذجي:** نواة دستورية مستقرة، فجوات موثَّقة بدقة، أدوات حاسوبية متكاملة بصرامة، توسع منضبط بحسب أولويات صريحة. اللحظة المثالية للانتقال من **التوسع البياني** إلى **الاختبار التطبيقي الكبير** على كوربس حقيقي.
