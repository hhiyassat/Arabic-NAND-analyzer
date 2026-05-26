# i3rab Engine — Phase 1/2/3 Handoff

**Date**: 2026-05-20
**Status**: v1 يعمل end-to-end، اجتاز smoke tests، قياس أوّلي على 1000 آية: WordClass 92.4% / Case 82.4%.

## ما تمّ بناؤه

`clean_code/i3rab_engine/` — حزمة مكوَّنة من خمسة ملفّات:

| ملف | الدور |
|---|---|
| `types.py` | `TokenI3rab` + `SentenceI3rab` dataclasses + ثوابت `CASE_IDS` / `MARK_IDS` من `i3rab_ref/` |
| `refs.py` | تحميل canonical reference tables (cases, marks, roles, operators, labels.jsonl) + `closed_class_kind()` للتمييز بين HARF/ISM_MABNI/HARF_NASB/HARF_JAZM |
| `layer1.py` | **WordClass** — تصنيف كل كلمة ضمن {HARF, ISM_MABNI, ISM_MUARAB, FIIL, AALAM, JAMID, JALALAH, UNKNOWN} |
| `layer2.py` | **Case + Mark** — قواعد لتحديد الحالة الإعرابية (مرفوع/منصوب/مجرور/مجزوم/مبني) والعلامة من بين الـ 14 |
| `layer3.py` | **Role** — قواعد سياقية لتحديد الدور الإعرابي (مبتدأ/فاعل/مفعول به/خبر/نعت/معطوف/مضاف إليه/اسم مجرور/اسم إنّ/خبر إنّ/...) |
| `engine.py` | Orchestrator: `I3rabEngine().analyze_sentence(text) → SentenceI3rab` |

## القواعد المُطبَّقة

### Layer 1 (WordClass)
1. **JALALAH** override — `الله` / `اللهم`
2. **closed_class** → HARF (بأنواعه) أو ISM_MABNI (ضمير/إشارة/موصول/استفهام/شرط)
   - تجاوز: لو الكلمة لها label=FIIL أيضًا → فعل مع ضمير متّصل (مثل `اهْدِنَا`)
   - تجاوز: لو الكلمة في قائمة المُعرَب (`رَبّ`) رغم وجودها في الـ closed_class set → fall-through
3. **JAMID** ← `jamid_detector` (MASAQ NOUN_CONCRETE)
4. **AALAM** ← MASAQ NOUN_PROP (لو متاح)
5. **FIIL/ISM_MUARAB** ← `root_pipeline` + كاشف الفعل الذكي:
   - السطح فيه تنوين → اسم
   - السطح يبدأ بـ يَ/تَ/أَ/نَ → فعل مضارع
   - وزن `فَاعِل` (كسرة على ع) → اسم فاعل
   - وزن `فَاعَل` (فتحة على ع) → فعل ماضٍ form III
   - السطح ينتهي بـ ـوا/ـت/ـتم/ـنا + ساق فعلي → فعل ماضٍ + ضمير

### Layer 2 (Case + Mark)
- **HARF / ISM_MABNI** → مبني، علامته من الحركة الأخيرة (فتح/ضم/كسر/سكون)
- **FIIL ماضٍ** → مبني على الفتح/الضم/السكون حسب اللاحقة
- **FIIL مضارع**:
  - إذا سبقه HARF_NASB (لن، أن، كي، حتى، إذن) → منصوب بالفتحة
  - إذا سبقه HARF_JAZM (لم، لما) → مجزوم بالسكون
  - وإلا → مرفوع بالضمة (أو ثبوت النون لأفعال خمسة)
- **ISM_MUARAB / JAMID / AALAM / JALALAH**:
  - إذا سبقه HARF_JARR → مجرور بالكسرة (أو بالياء جمع مذكر سالم/مثنى)
  - وإلا → الحالة تُشتقّ من الحركة الأخيرة (ضم → مرفوع، فتح → منصوب، كسر → مجرور، تنوين → نفس الحالة + تنوين)
  - معالجة خاصة لـ ـون/ـين/ـان/ـات (جمع مذكر سالم/مثنى/جمع مؤنث سالم)

### Layer 3 (Role)
1. **اسم مجرور** بعد حرف جر
2. **اسم (إنّ) منصوب** بعد إنّ/أنّ/كأنّ/لكنّ/لعلّ/ليت
3. **خبر (إنّ) مرفوع** بعد اسم إنّ
4. **مفعول به منصوب** بعد فعل، اسم منصوب، لا حرف جر بينهما
5. **فاعل مرفوع** بعد فعل، اسم مرفوع، لا اسم مرفوع متقدّم
6. **مبتدأ مرفوع** أوّل اسم مرفوع، لا فعل قبله
7. **خبر مرفوع** اسم مرفوع بعد مبتدأ
8. **نعت** يطابق ما قبله في الإعراب والتعريف
9. **مضاف إليه مجرور** اسم مجرور غير مسبوق بحرف جر، بعده اسم آخر
10. **معطوف** بعد حرف عطف، يتبع ما قبله

## نتائج التقييم (1000 آية)

```
=== WordClass agreement (vs quran_i3rab_labels.jsonl) ===
  Agree:        12,940 (92.4% of comparable)
  Disagree:      1,072  (7.6% of comparable)
  No signal:     5,834

=== Case agreement ===
  Agree:        16,415 (82.4% of comparable)
  Disagree:      3,512 (17.6% of comparable)

=== Top WordClass confusions (predicted → expected) ===
  ISM_MUARAB → FIIL    600  (verb_wazn detector misses some patterns)
  UNKNOWN    → FIIL    121  (verbs with attached pronouns not classified)
  ISM_MABNI  → HARF     86  (kind ambiguity in labels.jsonl)
  FIIL       → AALAM    82  (proper nouns misclassified as verbs)

=== Top Case confusions (predicted → expected) ===
  MARFOO   → MABNI    660  (مبنيات not detected in closed_class)
  MAJROOR  → MANSOOB  541  (مفعول به mistaken for مجرور — needs Layer 3 to back-propagate to Layer 2)
  MANSOOB  → MABNI    286  (أسماء مبنية على الفتح)
  MAJZOOM  → MABNI    279  (أفعال أمر مبنية)
```

**Per-token CSV**: `data/eval/i3rab_engine_eval.csv` (19,927 rows)

## مخرج على الفاتحة (نموذجي)

```
[1:1] بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ
  بِسْمِ        HARF        مَبْنِي      —      حرف جر
  اللَّهِ       JALALAH     مَجْرُور     كسرة   اسم مجرور
  الرَّحْمَنِ   ISM_MUARAB  مَجْرُور     كسرة   نعت مجرور
  الرَّحِيمِ    ISM_MUARAB  مَجْرُور     كسرة   نعت مجرور
```

النصّ الكامل في `data/eval/fatiha_i3rab_showcase.txt`.

## أبرز الديون (Known limitations لـ v1)

1. **`اهْدِنَا` → UNKNOWN**: حالات FIIL+pronoun لا يلتقطها fall-through بعد OVERRIDE_AS_VERB. الإصلاح: بعد فشل closed_class، إعادة `is_jamid` و`root_pipeline` كاملًا.

2. **مفعول به/فاعل لا يُعَدّلان Layer 2**: الـ Role يحدّد دور `كتابًا = مفعول به` لكن Case في Layer 2 يكون "منصوب" بالاعتماد على التنوين فقط. لو الكلمة بلا تشكيل، نفقد المعلومة. اقتراح Phase 4: feedback loop يسمح لـ Layer 3 بإعادة-تحديد Case إذا كانت ambiguous في Layer 2.

3. **علامة المبني**: لا يوجد mark_id يطابق "مبني على الفتح/الكسر/السكون" بصيغة منظَّمة في `i3rab_marks.csv` (هذه تتعامل مع المعرب فقط). نتركها في notes حاليًا.

4. **بنية الجملة المتداخلة**: لا يوجد إدراك لـ شبه الجملة، الجمل في محل رفع/نصب، صلة الموصول، الجمل الشرطية. هذه تستلزم Task #48 (M1.A — Multi-clause Segmenter).

5. **حرف نصب/جزم**: الـ overrides اليدوية (`_HARF_NASB_FORMS` / `_HARF_JAZM_FORMS`) محدودة. الحلّ المُستدام: حصاد من `quran_i3rab.csv` للجمل التي تحوي "حرف جزم" / "حرف نصب" مع surface form.

## مفاتيح الاختبار

```bash
# Phase 1
cd hussein/clean_code && python3 -m i3rab_engine.layer1

# Phase 2
cd hussein/clean_code && python3 -m i3rab_engine.layer2

# Phase 3 (full engine on Fatiha)
cd hussein/clean_code && python3 -m i3rab_engine.layer3

# Full eval
cd hussein && python3 scripts/eval_i3rab_engine.py --max-ayahs 1000

# Showcase on Fatiha
cd hussein && python3 scripts/showcase_fatiha_i3rab.py
```

## الالتزامات الدستوريّة

- ✅ معماري: i3rab_engine حزمة منفصلة (لا يدخل في root_pipeline)
- ✅ مصادر canonical: كل البيانات تُحمَّل من `new_arabic_analyzer/data/quran/i3rab_ref/` و MASAQ
- ✅ source_of_claim لكل قرار (`closed_class:HARF_JARR`, `ending:كسرة → مجرور`, `mafool_bih_after_verb`, ...)
- ✅ Evaluation harness على corpus quran_i3rab_labels.jsonl
- ✅ لا يتدخّل في wazn/root adjudication
