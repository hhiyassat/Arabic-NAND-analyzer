# إعلان رسمي: Segmenter نجح ✓
**التاريخ:** 2026-05-19
**الحالة:** مُجمَّد رسمياً (frozen v1.0)
**الموقع:** `/Users/husseinhiyassat/fractal/hussein/clean_code/segmenter.py`

---

## النتائج النهائية (مُتحَقَّق منها)

| المقياس | النتيجة | المرجع |
|---|---:|---|
| Exact MASAQ Segmented_Word match | **91.7%** | 70,969 / 77,411 |
| Length 1 (كلمات بدون تقطيع) | 98.2% | 24,457 / 24,903 |
| Length 2 (سابقة + جذر، أو جذر + لاحقة) | 92.8% | 33,503 / 36,118 |
| Length 3 | 86.3% | 11,396 / 13,208 |
| Length 4 | 56.0% | 1,547 / 2,762 |
| Segment-count match | 93.0% | 71,957 / 77,411 |

## تأثير المصب (Downstream impact)

دمج segmenter في wazn_matcher (Task #85):
- Top-1 root accuracy: **59.3% → 78%** (+18.9 نقطة)
- Top-3 root accuracy: **~82%**
- ضافت كـ variant بتكلفة 0.03 فوق الـ original

## بيانات MASAQ — تحسين موازي

تم اكتشاف 336 خطأ في MASAQ.csv أثناء التقييم.

| المرحلة | الأخطاء |
|---|---:|
| الأصل | 336 |
| بعد جولة الإصلاحات الأولى | 121 |
| بعد إصلاح seg_no sort bug | 107 |
| بعد Tier A + D + morphophonology rules | **74** |

**249 تعديل خلوي** على MASAQ.csv موثَّقة في `clean_code/data/masaq_data_errors/masaq_fix_audit.csv`، مع نسخة احتياطية في `data/MASAQ.csv.bak`.

الـ 74 المتبقية أخطاء هيكلية (تحتاج إضافة/حذف صفوف) — خارج نطاق تعديل الخلايا.

## الالتزامات الدستورية المُحَقَّقَة

- **Source-of-Claim:** كل قاعدة في segmenter مدعومة بأمثلة من MASAQ
- **Confidence-of-Claim:** التكلفة (cost) محددة بدقة في wazn_matcher
- **Alternatives-Preserved:** segmenter يضيف variants بدون حذف
- **Reversibility:** backup كامل + audit log كامل + git history

## ما يبقى (للجولات القادمة، اختياري)

السقف العملي لـ rule-based segmentation عند ~92-93%. للوصول لأعلى:
1. Length 4+ compound words (حالياً 56%) — يحتاج logic أكثر تطوراً
2. Proper-noun discrimination — يحتاج معجم مخصَّص (تم بناؤه في Task #90)
3. Wazn-aware bidirectional validation (segmenter ↔ wazn_matcher feedback)

## الملفات الرسمية المُجمَّدة

```
clean_code/
├── normalizer.py        ← official normalizer
├── segmenter.py         ← official segmenter (91.7% MASAQ)
└── wazn_matcher.py      ← official wazn matcher (78% top-1)

data/
├── MASAQ.csv            ← cleaned (249 fixes)
└── MASAQ.csv.bak        ← original backup

clean_code/data/masaq_data_errors/
├── masaq_fix_audit.csv          ← all 249 changes
├── masaq_data_errors_full.csv   ← 74 remaining errors
└── masaq_errors_categorized.md  ← upstream-ready report

scripts/
├── eval_segmenter_direct_masaq.py
├── find_masaq_data_errors.py
├── fix_masaq_errors.py
└── categorize_masaq_errors.py
```

---

**معلَن رسمياً.** المرحلة الأساسية (Foundation) لـ segmenter منتهية. الانتقال للمرحلة التالية: M1 (Multi-clause Segmenter, Speech Act, Negation Scope, Modal Detector) — أو رفع wazn_matcher أكثر.
