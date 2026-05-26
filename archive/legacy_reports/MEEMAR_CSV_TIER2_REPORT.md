# MEEMAR.csv — Tier 2 مكتمل ✓
**التاريخ:** 2026-05-19
**الموقع:** `/Users/husseinhiyassat/fractal/hussein/data/MEEMAR.csv`
**الحجم:** 29.1 MB · 146,918 صف · 77,411 كلمة مرجعية

---

## الأعمدة (24 عمود — Tier 1 + 1.5 + 2)

| # | العمود | اللغة | الحالة |
|---:|---|---|---|
| 1-7 | ID, Sura_No, Verse_No, Word_No, Segment_No, Word, Without_Diacritics | English | T1 |
| 8 | Segmented_Word | English | T1 |
| 9-14 | Our_Root, Our_Wazn, Our_Confidence, Source_Of_Claim, Alternatives, Agreement_With_MASAQ | English | T1.5 |
| 15 | Morph_Tag | English | T1 |
| 16 | **Morph_Type / النوع_الموضعي** | Bilingual | T2 ✓ |
| 17 | **Case_Mood / الحالة_الإعرابية** | Bilingual | T2 ✓ |
| 18 | **Case_Mood_Marker / علامة_الإعراب** | Bilingual | T2 ✓ |
| 19 | **Invariable_Declinable / مبني_معرب** | Bilingual | T2 ✓ |
| 20 | الوظيفة_النحوية | Arabic | T3 (فارغ) |
| 21 | الإضافة | Arabic | T3 (فارغ) |
| 22 | الجملة | Arabic | T3 (فارغ) |
| 23 | وظيفة_الجملة | Arabic | T3 (فارغ) |
| 24 | Punctuation_Mark | English | T3 (فارغ) |

## التغطية (Tier 2)

| العمود | التغطية |
|---|---:|
| Morph_Type / النوع_الموضعي | 100.0% (146,918) |
| Case_Mood / الحالة_الإعرابية | 73.9% (108,622) |
| Case_Mood_Marker / علامة_الإعراب | 52.6% (77,252) |
| Invariable_Declinable / مبني_معرب | 100.0% (146,918) |

## توزيع Case_Mood

| القيمة | العدد | النسبة |
|---|---:|---:|
| INVARIABLE / مبني | 71,261 | 65.6% |
| ACCUSATIVE / نصب | 14,420 | 13.3% |
| GENITIVE / جر | 10,409 | 9.6% |
| NOMINATIVE / رفع | 8,524 | 7.8% |
| JUSSIVE / جزم | 4,008 | 3.7% |

## مثال (سورة الفاتحة)

```
ID  | Segment   | Tag   | Morph_Type        | Case_Mood              | Marker | معرب/مبني
1   | بِ        | PREP  | Prefix / سابقة    | INVARIABLE / مبني     |        | INVAR / مبني
2   | اسْمِ     | STEM  | Stem / جذع        | GENITIVE / جر          | كسرة   | DECLN / معرب
3   | ال        | DET   | Prefix / سابقة    | INVARIABLE / مبني     |        | DEF_ART / أداة_تعريف
4   | لَهِ      | STEM  | Stem / جذع        | GENITIVE / جر          | كسرة   | DECLN / معرب
6   | رَحْمَنِ  | STEM  | Stem / جذع        | GENITIVE / جر          | كسرة   | DECLN / معرب
8   | رَحِيمِ   | STEM  | Stem / جذع        | GENITIVE / جر          | كسرة   | DECLN / معرب
```

البسملة كلها مجرورة (بِ + اسم + الله الرحمن الرحيم) — التحليل صحيح.

## الـ logic (للمراجعة)

### Morph_Type — النوع الموضعي
- `Stem / جذع` → tag == "STEM"
- `Prefix / سابقة` → seg_idx ≤ num_prefixes
- `Suffix / لاحقة` → seg_idx > num_prefixes + 1

### Case_Mood_Marker — علامة الإعراب
- يستخرج من **آخر حركة** في الـ segment الأخير
- ُ → ضمة, َ → فتحة, ِ → كسرة, ْ → سكون
- ٌ → ضمتان, ً → فتحتان, ٍ → كسرتان
- إذا انتهى بـ ا/ى/و/ي/ن دون حركة → ألف/واو/ياء/نون

### Case_Mood — الحالة الإعرابية
- ضمة/ضمتان → NOMINATIVE / رفع
- فتحة/فتحتان → ACCUSATIVE / نصب
- كسرة/كسرتان → GENITIVE / جر
- سكون → JUSSIVE / جزم
- مبني → INVARIABLE / مبني

### Invariable_Declinable — مبني/معرب
**فئات مبنيّة من segmenter tags:**
- DET → DEF_ART / أداة_تعريف
- POSS_PRON/VSUFF/PVSUFF → JONT_PRON / ضمير_متصل
- CONJ/PREP/INTERROG/VOC_PART/FUT_PART/EMPHATIC → INVAR / مبني

**فئات مبنيّة من معجم مغلق:**
- ضمائر منفصلة: أنا/أنت/هو/نحن/هم → DISJ_PRON / ضمير_منفصل
- أسماء إشارة: هذا/ذلك/تلك → DEM_NOUN / اسم_إشارة
- أسماء موصولة: الذي/التي/الذين → REL_PRON / اسم_موصول
- أسماء شرط: من/ما/متى/أينما → COND_NOUN / اسم_شرط
- أسماء استفهام: كيف/أين/متى/كم/ماذا → INTROG_NOUN / اسم_استفهام

**الباقي:** DECLN / معرب

## المقارنة مع MASAQ

| Case_Mood قيمة | MASAQ | نحن |
|---|---:|---:|
| INVARIABLE | 53,687 (57.4%) | 71,261 (65.6%) |
| NOMINATIVE | 27,014 (28.9%) | 8,524 (7.8%) |
| GENITIVE | 23,255 (24.9%) | 10,409 (9.6%) |
| ACCUSATIVE | 19,327 (20.7%) | 14,420 (13.3%) |
| JUSSIVE | 1,490 (1.6%) | 4,008 (3.7%) |

**فجوة معروفة:** نحن نُصنّف INVARIABLE أكثر لأن كل prefix/suffix يُعدّ مبنياً. NOMINATIVE/GENITIVE/ACCUSATIVE أقل لأن detection من diacritics فقط يفقد حالات (ضمة مقدرة، حركات على الـ stems الأجوف، الخ).

**فرصة Tier 2.5:** رفع التغطية بـ:
- detection للحركات المقدّرة (الأسماء المعتلة)
- ربط Marker مع Morph_Tag (إذا STEM وانتهى بـ ا → معرب لكن مرفوع منوياً)
- اعتبار noun-suffix النون كحركة الرفع للمثنى والجمع

## الـ logic موجود في
`/Users/husseinhiyassat/fractal/hussein/scripts/build_meemar_csv.py`

دوال:
- `derive_morph_type()` — لتحديد جذع/سابقة/لاحقة
- `derive_case_marker()` — لاستخراج الحركة
- `derive_case_mood()` — لتحديد الإعراب
- `derive_invariable()` — لتمييز المبني والمعرب

## ما يأتي (Tier 3)

| العمود | المطلوب |
|---|---|
| الوظيفة_النحوية | dependency parser (فاعل/مفعول/مبتدأ/خبر) — يحتاج M1.A |
| الإضافة | parser للمضاف والمضاف إليه — قواعد سياقية |
| الجملة | تقسيم الجمل (M1.A — Multi-clause Segmenter) |
| وظيفة_الجملة | تحديد الـ function (شرط/جواب/صفة/حال) |
