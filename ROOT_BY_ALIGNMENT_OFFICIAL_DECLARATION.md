# إعلان رسمي: root_by_alignment.py
**التاريخ:** 2026-05-20
**الإصدار:** v1.0 (مع post-processing rules)
**الحالة:** ✅ **معتمد رسمياً** كأداة الإنتاج لاستخراج الوزن والجذر

---

## ١. الإعلان الجوهري

**`clean_code/root_by_alignment.py` هو الأداة الرسمية المعتمدة في معمار المعنى العربي لاستخراج الوزن والجذر لأي كلمة عربية مُشكَّلة.**

يحل محل:
- `wazn_matcher.py` (v2) → مجمَّد كـ `wazn_matcher_legacy.py`
- `wazn_matcher_v3.py` (hybrid) → مجمَّد كـ `wazn_matcher_v3_legacy.py`

سبب الاستبدال:
- **نظافة دستورية**: rule-based pure، لا lookup كمصدر للجذر
- **شفافية كاملة**: كل قاعدة في `salehan/awzan_cleaned.csv` نصاً مقروءاً
- **قابلية التوسع**: أي وزن جديد يُضاف في CSV بدون لمس الكود

---

## ٢. المقارنة على MASAQ كاملاً (Ground Truth: mishkat)

تم القياس على **10,813 كلمة** قرآنية فريدة (بعد استثناء 5,836 closed-class + 970 بدون ground truth):

| الأداة | الدقة | الفجوة | الطبيعة |
|---|---:|---:|---|
| wazn_matcher_v3 (legacy) | 65.6% | baseline | hybrid (DB selection) |
| **root_by_alignment (officiel)** | **64.6%** | **-1.0 pp** | **rule-based pure** |

**الفجوة 1 نقطة فقط** — مقابلة بالنظافة الدستورية الكاملة. v3 كان يستخدم mishkat كمصدر لاختيار الجذر؛ root_by_alignment يستخدم الأوزان فقط ويستخرج الجذر بقواعد ف-ع-ل.

### تطور الدقة خلال هذه الجلسة
| المرحلة | الدقة | تحسن |
|---|---:|---:|
| Initial alignment | 49.0% | — |
| Doubled expansion (مقيّد) | 53.7% | +4.7 |
| Wazn expansion (مُفْعِل، تصاريف...) | 59.0% | +5.3 |
| Defective/hollow expansion | 60.9% | +1.9 |
| ـة + ضمير combinations | 62.2% | +1.3 |
| Tanwin alif fix | 63.4% | +1.2 |
| Form IV doubled + مَفْعِيل | 64.2% | +0.8 |
| Hollow PV/IV + suffixes | **64.6%** | +0.4 |

**+15.6 نقطة في جلسة واحدة بدون تخريب البنية.**

---

## ٣. المنهج الدستوري

```
كلمة مُشكَّلة
   ↓
[1] normalize_word()  →  clean_code/normalizer.py
       - NFC + alif madda + alif wasla
       - lam-shamsi un-assimilation (الشَّمْس → الشَمْس)
       - hamzat wasl resolution (اكْتُبْ → أُكْتُبْ)
   ↓
[2] is_closed_class()  →  استثناء المبنيات/العوامل
       - من new_arabic_analyzer (8,365+ كلمة من القرآن)
       - + قاموس الأساس
   ↓
[3] align()  →  مطابقة substring مع 634 وزن
       - من salehan/awzan_cleaned.csv (المصدر الرسمي)
       - السكون والشدة صارمتان
       - حركة آخر موضع الوزن متساهلة (لـ suffix)
   ↓
[4] post-processing rules (rule-based, no DB):
       a. doubled expansion: فَعَّ + رَدَّ → ر د د (3 letters)
       b. hollow expansion: فَال + قَال → ق و ل
       c. defective expansion: يَفْعَى + يَخْشَى → خ ش ي
   ↓
نتيجة: (root, wazn, source_of_claim)
```

---

## ٤. المصادر الرسمية

| البيانات | المصدر | عدد |
|---|---|---:|
| **الأوزان** | `salehan/Salehan19-6-67/data/awzan_cleaned.csv` | **634** |
| المبنيات/العوامل | `new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl` | 8,365+ |
| العوامل النحوية | `new_arabic_analyzer/data/quran/i3rab_ref/i3rab_operators.csv` | 97 |
| التطبيع | `clean_code/normalizer.py` | — |

**كل التحسينات القادمة تُضاف هنا**، لا في الكود.

---

## ٥. الالتزامات الدستورية المُحَقَّقَة

| الالتزام | الحالة | الدليل |
|---|---|---|
| **Source-of-Claim** | ✅ | كل match يحمل الوزن الذي طابق + موضع المطابقة |
| **Confidence-of-Claim** | ✅ | (length × literal × clitics) |
| **Alternatives-Preserved** | ✅ | `extract_all()` يُرجع كل المطابقات |
| **Reversibility** | ✅ | كل وزن سطر في CSV — يُحذف ويُعاد التشغيل |
| **No DB-as-Source** | ✅ | الجذر يُستخرَج من قواعد الوزن، لا lookup |
| **Single Source per Data** | ✅ | الأوزان في ملف، المبنيات في ملف، التطبيع في ملف |

---

## ٦. القيود المعروفة (موثقة، للمعالجة لاحقاً)

### ٦.١ الـ و/ي Ambiguity في الجذور الناقصة
- **مثال:** أَدْنَى → root=ي vs و (الصحيح: دنو)
- **السبب:** لا يمكن التمييز من السطح بدون lookup
- **التأثير:** ~50-100 كلمة
- **الحل المستقبلي:** قاعدة preference + DB validation (اختياري)

### ٦.٢ الـ و/ي في الجذور الجوفاء
- **مثال:** قَالَ → root=و (صحيح). بَاعَ → ربما و (لكن الصحيح ي)
- الحل الحالي: نأخذ و كافتراضي
- التأثير: ~30 كلمة

### ٦.٣ كلمات مركَّبة نادرة
- **مثال:** الشَّهَادَتِهِمَا، أُمَّهَاتُهُمْ
- معظمها يُغطَّى بأوزان متخصصة قد تحتاج إضافة

---

## ٧. حدود الاستخدام (Scope)

### ✅ يعمل على
- كل كلمات القرآن المُشكَّلة (تغطية 64.6% من المُحلَّل)
- نصوص عربية فصيحة مُشكَّلة (modern standard or classical)
- استثناء صحيح للمبنيات والعوامل (33.1% من القرآن)

### ❌ خارج النطاق
- النصوص غير المُشكَّلة (بالتصميم — `--require-diacritics`)
- اللهجات العامية
- الأعلام الأجنبية (موسى، إبراهيم، فرعون)
- الجذور النادرة غير المُغطَّاة بالأوزان (يمكن إضافتها)

---

## ٨. كيفية الإضافة والتعديل

### إضافة وزن جديد
```bash
# 1. أضف للملف الرسمي مع مثال + CV pattern
echo "الوزن,مثال,CV_الوزن,CV_مثال" >> awzan_cleaned.csv
# مثال: مُسْتَفْعَلَة, مُسْتَخْرَجَة, ...

# 2. أعد التشغيل (لا تعديل في الكود)
python3 clean_code/root_by_alignment.py
```

### استثناء كلمة (closed-class)
```bash
# أضف لـ new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl
```

---

## ٩. الملفات الرسمية

```
clean_code/
├── normalizer.py             ← التطبيع الرسمي (NFC + hamzat wasl + lam-shamsi)
├── segmenter.py              ← التقطيع (للـ MEEMAR، not for root extraction)
├── wazn_data.py              ← Loaders (لا data)
├── root_by_alignment.py      ← ★ الأداة الرسمية ★
├── wazn_matcher.py           ← ⛔ deprecated (legacy)
├── wazn_matcher_legacy.py    ← v2 backup
├── wazn_matcher_v3_legacy.py ← v3 backup (just frozen)
└── data/
    └── ... (other resources)

salehan/Salehan19-6-67/data/
└── awzan_cleaned.csv         ← ★ المصدر الرسمي للأوزان (634 وزن) ★

new_arabic_analyzer/data/quran/
├── quran_i3rab_labels.jsonl  ← المبنيات
└── i3rab_ref/
    └── i3rab_operators.csv   ← العوامل
```

---

## ١٠. الاستخدام

```python
from clean_code.root_by_alignment import WaznAligner
from clean_code.wazn_data import load_awzan

aligner = WaznAligner(load_awzan())

result = aligner.extract("كَتَبَ")
# result.root = "كتب"
# result.wazn = "فَعَل"
# result.length = 3
# result.prefix_len = 0
# result.suffix_len = 0
```

```bash
# CLI
python3 clean_code/root_by_alignment.py --word "كَسَبْتُمْ"
python3 clean_code/root_by_alignment.py --corpus data/MASAQ.csv --limit 5000
```

---

## ١١. الإعلان النهائي

✅ **معلَن رسمياً (2026-05-20):**

> `clean_code/root_by_alignment.py` هو الأداة المعتمدة للإنتاج لاستخراج الوزن والجذر لأي كلمة عربية مُشكَّلة في معمار المعنى العربي.

التحول من v3 إلى root_by_alignment:
- **خسارة 1 نقطة** في الدقة (65.6% → 64.6%)
- **مكسب كامل** في النظافة الدستورية
- **آلاف الجذور** تصبح rule-traceable بدلاً من DB-mediated

### الالتزامات المستقبلية

**كل تحسين قادم** سيكون عبر:
1. **إضافة وزن** → في `awzan_cleaned.csv` فقط
2. **post-processing rule** → في `root_by_alignment.py` مع Source-of-Claim واضح
3. **مصدر بيانات جديد** → ملف منفصل، تحميل بـ loader في `wazn_data.py`

**ممنوع:**
- ❌ data hardcoded في الكود
- ❌ DB lookup كمصدر للجذر  
- ❌ استبدال هذه الأداة دون إعلان رسمي جديد
- ❌ استعمال v3 legacy في الإنتاج الجديد

### للمقارنة مع v3 (الأداء النهائي)

| المقياس | v3 (legacy) | root_by_alignment (official) |
|---|---:|---:|
| Accuracy على MASAQ | 65.6% | **64.6%** |
| Pure rule-based | ❌ no | ✅ yes |
| Source-of-Claim | partial | ✅ full |
| Reversibility | ❌ DB binding | ✅ CSV editable |
| Constitutional grade | C | **A** |

**القرار:** نضحّي بـ 1 نقطة دقة مقابل **درجة دستورية كاملة**.
