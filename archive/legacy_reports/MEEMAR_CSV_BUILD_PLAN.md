# خطة بناء MEEMAR.csv
**التاريخ:** 2026-05-19
**المرجع:** MASAQ.csv (157,676 row × 18 column)
**الهدف:** بناء ملفنا الخاص بنفس الـ schema + إضافاتنا، يستفيد من segmenter + wazn_matcher

---

## تحليل حقول MASAQ الـ 18

| # | الحقل | الوصف | الأولوية لنا | المصدر عندنا |
|---:|---|---|:-:|---|
| 1 | ID | معرّف فريد | T1 | auto-generate |
| 2 | Sura_No | رقم السورة | T1 | من MASAQ |
| 3 | Verse_No | رقم الآية | T1 | من MASAQ |
| 4 | Word_No | ترتيب الكلمة | T1 | من MASAQ |
| 5 | Segment_No | ترتيب الـ segment | T1 | من segmenter |
| 6 | Word | الكلمة المُشكَّلة | T1 | من MASAQ |
| 7 | Without_Diacritics | الكلمة بدون تشكيل | T1 | strip_diacritics |
| 8 | **Segmented_Word** | الـ segment نفسه | **T1** | **segmenter.py ✓** |
| 9 | **Morph_Tag** | POS tag تفصيلي | **T2** | derive + wazn_matcher |
| 10 | **Morph_Type** | verb/noun/particle | **T2** | derive من Tag |
| 11 | Punctuation_Mark | علامة ترقيم | T3 | derive |
| 12 | **Invariable_Declinable** | معرب/مبني | **T2** | rule-based |
| 13 | **Syntactic_Role** | الوظيفة النحوية (فاعل/مفعول) | **T3** | يحتاج parser نحوي |
| 14 | Possessive_Construct | في إضافة؟ | T3 | يحتاج parser |
| 15 | **Case_Mood** | رفع/نصب/جر/جزم | **T2** | rule + Case_Mood_Marker |
| 16 | Case_Mood_Marker | علامة الإعراب | T2 | derive from diacritic |
| 17 | **Phrase** | الجملة الفرعية | **T3** | يحتاج M1.A |
| 18 | Phrasal_Function | وظيفة الجملة | T3 | يحتاج M1.A + M1.B |

## الترتيب الزمني (Tiered execution)

### **Tier 1: الأنكر + التجزئة (انطلاقة فورية)**
حقول: ID, Sura_No, Verse_No, Word_No, Segment_No, Word, Without_Diacritics, **Segmented_Word**

- لدينا كل شيء جاهز
- ننتج الـ schema الأساسي عمود بعمود
- نقارنه مع MASAQ كـ regression check

### **Tier 1.5: إضافاتنا الدستورية (Our_-prefixed columns)**
حقول مُضافة لا توجد في MASAQ:

| الحقل | المحتوى | المصدر |
|---|---|---|
| `Our_Root` | الجذر | wazn_matcher.top1.root |
| `Our_Wazn` | الوزن | wazn_matcher.top1.wazn |
| `Our_Confidence` | درجة الثقة | wazn_matcher.top1.cost (مقلوب) |
| `Source_Of_Claim` | أي قاعدة فيها | rule_id من segmenter |
| `Alternatives` | بدائل أخرى | wazn_matcher.top3[1:] |
| `Agreement_With_MASAQ` | True/False/Partial | مقارنة مع Segmented_Word |

### **Tier 2: المعلومات النحوية الأساسية (تتطلب logic إضافي)**
حقول: Morph_Tag, Morph_Type, Case_Mood, Case_Mood_Marker, Invariable_Declinable

- Morph_Tag: نستخرج من tag الموجود في wazn_matcher + قواعد إضافية
- Morph_Type: derive من Morph_Tag (noun/verb/particle)
- Case_Mood_Marker: من التشكيل (الحرف الأخير + الحركة)
- Case_Mood: derive من Case_Mood_Marker + سياق
- Invariable_Declinable: قائمة مغلقة من المبنيات + باقي معرب

### **Tier 3: المعلومات النحوية المركبة (تحتاج بحث منفصل)**
حقول: Syntactic_Role, Possessive_Construct, Phrase, Phrasal_Function

- تحتاج dependency parser نحوي
- يرتبط بمهام M1.A (Multi-clause Segmenter) و M1.B-D
- نتركها كأعمدة فارغة في T1/T2 — نملأها لاحقاً

---

## خطة التنفيذ الفورية

**الخطوة الحالية: Tier 1 على سورة الفاتحة (test) → ثم كامل القرآن**

سكربت: `scripts/build_meemar_csv.py`

```
INPUT:  data/MASAQ.csv (للحصول على Quranic text + word positions)
OUTPUT: data/MEEMAR.csv (نسختنا)

LOGIC:
  لكل (sura, verse, word_no) في MASAQ:
    word = surface مع تشكيل
    word_plain = strip_diacritics(word)
    
    # تشغيل segmenter
    seg_result = segmenter.segment(word)
    segments = prefixes + [stem] + suffixes
    
    # تشغيل wazn_matcher على الـ stem
    wazn_result = wazn_matcher.match(seg_result.stem)
    
    لكل segment in segments:
      row = {
        ID: auto,
        Sura_No, Verse_No, Word_No,
        Segment_No: index,
        Word: word,
        Without_Diacritics: word_plain,
        Segmented_Word: segment,
        Our_Root: wazn_result.root (only on stem row),
        Our_Wazn: wazn_result.wazn (only on stem row),
        Our_Confidence: ...,
        Source_Of_Claim: rule_id,
        Agreement_With_MASAQ: compare(segment, masaq_segment)
      }
      write(row)
```

**نقاط مهمة:**
1. الـ schema يطابق MASAQ في الأنكر الـ 8 الأولى → سهولة المقارنة
2. الأعمدة الـ T2/T3 موجودة لكن فارغة في البداية
3. كل صف له `Source_Of_Claim` — التزام دستوري
4. الـ regression metric: % Agreement مع MASAQ = 91.7% (نتيجتنا الحالية)
