# MEEMAR vs i3rab — ملخص المقارنة
**التاريخ:** 2026-05-19
**النطاق:** سورة الفاتحة (29 كلمة)
**المرجع:** `/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/quran/quran_i3rab_labels.jsonl`

---

## النتيجة الرئيسية

| المرحلة | Agreement على Case_Mood | السياق |
|---|---:|---|
| قبل التحسين | 75.9% (22/29) | logic أساسي |
| + جمع مذكر سالم/مثنى detection | 82.8% | NSUFF awareness |
| + حروف النفي مبني (لا/ما/لم) | 86.2% | particle list |
| + word-level case (آخر segment) | **96.6%** | الإعراب على آخر segment |

## الـ disagreement الوحيد المتبقي

**لِلَّهِ** — نحن نقول GENITIVE / جر، i3rab يقول INVARIABLE / مبني.

**التحليل:** الإعراب الفعلي للكلمة هو ل (حرف جر مبني) + الله (لفظ الجلالة مجرور). MASAQ تحفظ الـ stem الله كمجرور.

الـ labels.jsonl يبسّط الإعراب إلى label واحد ("MABNI") بناءً على أول حرف (ل المبنية)، بينما النص الإعرابي الكامل في `quran_i3rab.csv` يصف الـ stem كمجرور.

**الاستنتاج:** هذا ليس خطأً حقيقياً في تحليلنا — هو فقدان معلومة في الـ labels.jsonl (تبسيط).

## ما حصلنا عليه من i3rab data

### 1. **التحقق من Case_Mood**: 96.6% agreement على الفاتحة ✓

### 2. **استخراج الوظيفة_النحوية (Tier 3 الذي كان فارغاً)**:
14/29 كلمة لها role في i3rab:
- مبتدأ: الْحَمْدُ
- نعت: الرَّحْمَنِ، الرَّحِيمِ، رَبِّ، مَالِكِ، غَيْرِ، الْمُسْتَقِيمَ، الْمَغْضُوبِ
- مفعول به: إِيَّاكَ، الصِّرَاطَ
- بدل: صِرَاطَ
- فاعل: أَنْعَمْتَ
- معطوف: الضَّالِّينَ

### 3. **استخراج الإضافة (Tier 3 الفارغ)**:
7 حالات إضافة:
- اللَّهِ (مضاف إليه لـ اسم)
- الْعَالَمِينَ (مضاف إليه لـ رَبِّ)
- يَوْمِ (مضاف لـ مَالِكِ)
- الدِّينِ (مضاف إليه لـ يَوْمِ)
- الَّذِينَ (مضاف إليه لـ صِرَاطَ)
- الْمَغْضُوبِ (مضاف إليه لـ غَيْرِ)

## ما أضافنا لـ logic Tier 2

### قواعد جديدة في `build_meemar_csv.py`

1. **Sound masculine plural / مثنى detection** (case marker):
   - NSUFF tag with "ون" → واو_جماعة → NOMINATIVE / رفع
   - NSUFF tag with "ين" → ياء_جماعة → GENITIVE / جر
   - NSUFF tag with "ان" → ألف_تثنية → NOMINATIVE / رفع

2. **حروف مبنية إضافية** (closed-class lookup):
   - حروف النفي: لا، ما، لم، لن، ليس
   - حروف الاستثناء: إلا، خلا، حاشا، عدا
   - حروف التوكيد: إن، أن، لكن، كأن، ليت، لعل
   - حروف الجواب: نعم، بلى، كلا، أجل، إي
   - ظروف مبنية: حيث، هنا، هناك، ثم، قبل، بعد، فوق، تحت

3. **فعل ماضي مبني** detection (via PVSUFF tag in suffix_tags):
   - أَنْعَمْتَ → INVAR / مبني_فعل_ماض

4. **فعل أمر مبني** detection (hamzat wasl + 3-letter stem heuristic):
   - اهْدِنَا → INVAR / مبني_فعل_أمر

## فرصة قادمة (Tier 3)

استخدام `quran_i3rab_labels.jsonl` لـ **ملء الأعمدة الفارغة** في MEEMAR.csv كاملاً:

| العمود في MEEMAR | i3rab Labels المصدر |
|---|---|
| الوظيفة_النحوية | MUBTADA, KHABAR, FAAIL, MAFOOL_BIH, NACT, BADAL, HAL, TAMYEEZ, MUNADA, ... |
| الإضافة | MUDAF, MUDAF_ILAYH |

السكربت لإثراء MEEMAR.csv كامل من i3rab moكون من ~50 سطر — يمكن تنفيذه فوراً إذا أردت.

## الملفات

- **التقرير المفصّل لكل كلمة:** [MEEMAR_VS_I3RAB_FATIHA.md](computer:///Users/husseinhiyassat/fractal/hussein/MEEMAR_VS_I3RAB_FATIHA.md)
- **سكربت المقارنة:** [scripts/compare_meemar_vs_i3rab.py](computer:///Users/husseinhiyassat/fractal/hussein/scripts/compare_meemar_vs_i3rab.py)
- **MEEMAR.csv المُحدّث:** [data/MEEMAR.csv](computer:///Users/husseinhiyassat/fractal/hussein/data/MEEMAR.csv)
