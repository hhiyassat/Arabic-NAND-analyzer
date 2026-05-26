# MEEMAR.csv — Tier 1 مكتمل ✓
**التاريخ:** 2026-05-19
**الموقع:** `/Users/husseinhiyassat/fractal/hussein/data/MEEMAR.csv`
**الحجم:** 21.2 MB · 146,918 صف · 77,411 كلمة مرجعية

---

## النتائج الإجمالية

| المقياس | القيمة |
|---|---:|
| إجمالي rows | 146,918 |
| إجمالي word occurrences | 77,411 |
| Full agreement مع MASAQ | **69,569 (89.9%)** |
| Partial agreement | 5,502 (7.1%) |
| لا تطابق | 2,340 (3.0%) |
| وقت البناء الإجمالي | ~111 ثانية |
| السرعة | ~700 word/s |

> الـ 89.9% هنا هو **agreement على مستوى الكلمة الكاملة** (whole-word match). الـ 91.7% المُعلَن سابقاً هو **segment-by-segment** بعد normalization (متريك أكثر تفصيلاً).

## الـ Schema (24 عمود)

### Tier 1 — Anchors + Segmentation (مُملَّأة بالكامل)
| Column | Source |
|---|---|
| ID | auto-generated sequential |
| Sura_No, Verse_No, Word_No | من MASAQ |
| Segment_No | من segmenter (ترتيب surface) |
| Word | surface مع تشكيل |
| Without_Diacritics | strip_diacritics |
| Segmented_Word | **segmenter.py output** |

### Tier 1.5 — إضافاتنا الدستورية (مُملَّأة)
| Column | المحتوى |
|---|---|
| Our_Root | جذر من wazn_matcher (على صف الـ stem فقط) |
| Our_Wazn | الوزن (e.g., فعيل) |
| Our_Confidence | درجة الثقة (0-1) |
| Source_Of_Claim | audit trail من segmenter |
| Alternatives | top 2-3 بدائل من wazn_matcher |
| Agreement_With_MASAQ | Full / Partial / None |

### Tier 2 — حقول نحوية (فارغة، للمرحلة القادمة)
- Morph_Tag (موجود لكن بـ tags بسيطة: STEM, DET, CONJ, إلخ)
- Morph_Type, Case_Mood, Case_Mood_Marker, Invariable_Declinable

### Tier 3 — حقول مركبة (فارغة، تحتاج M1.A)
- Syntactic_Role, Possessive_Construct, Phrase, Phrasal_Function, Punctuation_Mark

## أمثلة (سورة الفاتحة)

```
ID  | Word        | Segment | Root | Wazn  | Conf  | Agree
8   | الرَّحِيمِ  | ال      |      |       |       | Full
9   | الرَّحِيمِ  | رَحِيمِ | رحم  | فعيل  | 1.000 | Full
6   | الرَّحْمَنِ | رَحْمَنِ | رحمن | فعلل  | 0.832 | Full
2   | بِسْمِ      | اسْمِ   | سوم  | فعل   | 0.880 | Partial
```

## الـ 3% الذي لا يتطابق — لماذا؟

من فحص العينات:
1. **بسم** — surface diacritized يحفظ "اسم"، MASAQ يكتب "سم" (basmala elision)
2. **يحيى/عيسى** — نحن نحفظ ى، MASAQ أحياناً يكتبها ا
3. **اللات** — MASAQ يخصصها لـ "اللات" wholeword، نحن نقسم لـ ال + لات
4. **الكلمات المعتلة المركبة** — segmenter يكافح length 4+ words

كل هذه موثقة في `Source_Of_Claim` ضمن MEEMAR.csv نفسه.

## ما يأتي (Tier 2)

| المهمة | المنهج |
|---|---|
| Morph_Tag detailed | حالياً STEM/DET/CONJ — نحتاج: PV/IV/CV (perfect/imperfect/imperative)، NOUN_CONCRETE/ABSTRACT، PREP، etc. مصدر: wazn_matcher.morph_type + قواعد إضافية |
| Morph_Type | derive من Morph_Tag → noun/verb/particle |
| Case_Mood_Marker | حركة آخر حرف (ضمة/فتحة/كسرة/سكون) |
| Case_Mood | derive من marker + context → رفع/نصب/جر/جزم |
| Invariable_Declinable | قائمة المبنيات (ضمائر، إشارة، موصول، شرط) + باقي معرب |

تقدير الوقت: ~2-3 ساعات لـ Tier 2 كاملاً.

## السكربت

- **Source:** `/Users/husseinhiyassat/fractal/hussein/scripts/build_meemar_csv.py`
- **Usage:** `python3 scripts/build_meemar_csv.py [--sura N] --out data/MEEMAR.csv`
- يعتمد على: clean_code/segmenter.py + clean_code/wazn_matcher.py

## الالتزامات الدستورية المُحَقَّقَة في MEEMAR.csv

✓ **Source-of-Claim**: عمود `Source_Of_Claim` يحفظ أي قاعدة من segmenter أنتجت كل segment
✓ **Confidence-of-Claim**: عمود `Our_Confidence` يحفظ الثقة لكل root prediction
✓ **Alternatives-Preserved**: عمود `Alternatives` يحفظ top 2-3 بدائل
✓ **Reversibility**: MEEMAR.csv قابل للإعادة من MASAQ.csv بسكربت واحد + audit في `Source_Of_Claim`
