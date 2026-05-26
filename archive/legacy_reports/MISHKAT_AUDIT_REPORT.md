# مراجعة دستورية: mishkat database في wazn_matcher
**التاريخ:** 2026-05-19
**النطاق:** كل قواعد البيانات التي يستهلكها `clean_code/wazn_matcher.py`

---

## النتيجة العامة: ✅ **نظيف دستورياً** (مع تحفّظ واحد محدود)

كل قواعد البيانات التي يستهلكها wazn_matcher إما:
- **عمل المستخدم نفسه** (Eqratech، alasmaa، salehan — كلها مشاريع Hussein Hiyassat)
- **مُستخرَجة rule-based** من ذلك العمل بسكربتات في hussein/scripts
- **مُدقَّقة يدوياً** مع citations لـ لسان العرب

ولا يوجد نسخ من مصدر خارجي opaque (لا CAMeL، لا MADAMIRA، لا labels.jsonl غير معلومة المصدر).

---

## التفصيل: 4 قواعد بيانات مستهلَكة

### 1. `mishkat_word_root.csv` — Word→Root mapping (16,423 صف)

**المصدر الأصلي:** `/Users/husseinhiyassat/fractal/Eqratech_Hussein_Hiyassat_Project/data/`

**التوثيق الصريح في DEVELOPMENT_GUIDE_AR.md:**
> "ابحث **أولًا** داخل `new_arabic_analyzer`. ابحث **بعده** داخل `Eqratech_Hussein_Hiyassat_Project` كـ **مرجع فقط**."

**القراءة:** Eqratech_Hussein_Hiyassat_Project مشروع المستخدم نفسه (الاسم الأخير Hiyassat = اسم المستخدم). الـ mishkat هنا اسم نظام، وليس استيراد لمشكاة خارجية.

**الـ Schema:** `root, word, count` — ربط word→root بسيط.

**تحفّظ:** لا يوجد سكربت في الـ session الحالية يُظهر كيف بُني mishkat_word_root.csv أصلاً داخل Eqratech. هذا خارج نطاق المراجعة الحالية ولكنه عمل المستخدم.

**تصنيف:** 🟢 **عمل المستخدم — موثَّق المصدر**

---

### 2. `mishkat_word_root_with_wazn.csv` — Wazn derivation (10,219 صف)

**المصدر:** مُشتقّ من #1 عبر `scripts/derive_wazn_from_mishkat.py`

**الطريقة:** Rule-based extraction بقواعد صريحة في الكود. القراءة المباشرة للملف تكشف:

```python
def derive_wazn(root, word):
    # القاعدة 1: استبعد الجذور المعتلة (تُكتب في no_wazn.csv)
    if is_weak_root(root_plain): return None, "weak_root"
    
    # القاعدة 2: استبعد الجذور < 3 حروف أو > 4
    # القاعدة 3: لـ ءله (الله/إله/آلهة) — لا وزن (proper noun)
    if root_plain == "ءله": return None, "divine_lexeme"
    
    # القاعدة 4: مشي حرف بحرف، استبدال أحرف الجذر بـ ف ع ل (+ ل للرباعي)
    fa3l = ["ف", "ع", "ل", "ل"][:len(root_plain)]
    
    # القاعدة 5: معالجة الإدغام (geminate) عبر شدة
    # القاعدة 6: معالجة افتعل مع همزة (اتَّخَذَ)
    # القاعدة 7: تخطّي أداة التعريف ال
    # القاعدة 8: مَدّ الألف آ → ءَا
```

**التحقّق:** كل صف في الملف يحمل عمود `wazn_in_db` و `root_audited` — cross-check ضد:
- `Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx` (للتحقق من وجود الوزن في DB)
- `salehan/audited_roots.csv` (للتحقق من تدقيق الجذر)

**تصنيف:** 🟢 **Rule-based بالكامل — كل قاعدة في الكود**

---

### 3. `audited_roots.csv` — الجذور المُدقَّقة يدوياً (4,769 صف)

**المصدر:** `/Users/husseinhiyassat/fractal/salehan/Salehan19-6-67/data/audited_roots.csv`

**Schema:**
```
id, الفعل الماضي, الجذر, باب الصرفي, اللزوم والتعدي,
تم تدقيقه, تم إعادة تدقيقه, صحيح (الجذر حقيقي),
المرجع (المصدر), المصدر
```

**عينة:**
```
3121, غَرَبَ, غرب, فَعَلَ يَفْعُلُ, لازم, 0, 1, 1, لسان العرب, غُرُوب
3122, غَرِبَ, غرب, فَعِلَ يَفْعَلُ, لازم, 0, 1, 1, لسان العرب, غَرَب
```

**القراءة:** هذا **عمل يدوي مُدقَّق** مع citation صريح لـ **لسان العرب** (أوثق معجم عربي كلاسيكي). كل صف عليه audit flags (تم تدقيقه، تم إعادة تدقيقه، صحيح).

**تصنيف:** 🟢 **Human-audited مع citations**

---

### 4. `canonical_table` — قاعدة الأوزان الأساسية

**المصدر:** `/Users/husseinhiyassat/fractal/alasmaa/Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx`

**القراءة:**
- مشروع alasmaa هو أحد مشاريع المستخدم
- الاسم "Final_Corrected" يشير إلى تنقيح يدوي
- يُستخدم في wazn_matcher كـ canonical source

**تصنيف:** 🟢 **عمل المستخدم — مُنقَّح يدوياً**

---

## الـ wazn_matcher.py نفسه — Logic Layer

كل المنطق rule-based:

| المكوّن | الطبيعة |
|---|---|
| `generate_variants()` | قواعد توليد variants بترتيب cost (0.0 → 1.0) |
| `_letter_distance()` | حساب رياضي صريح |
| `_movement_similarity()` | rule-based scoring |
| `_score_source()` | تفضيل canonical_table + mishkat مع canonical |
| `analyze()` | جمع matches + ranking |

كل قرار له:
- **Source-of-Claim:** الـ source DB يُكتب في كل match
- **Confidence-of-Claim:** [0,1] score
- **Alternatives-Preserved:** يُرجع list[WaznMatch] (top-K)

---

## التحفّظ الوحيد (للتسجيل الكامل)

**أصل `mishkat_word_root.csv` داخل Eqratech_Hussein_Hiyassat_Project:**

الـ session الحالية لا تحتوي على Eqratech project. لو أراد المستخدم audit كامل، يحتاج:
1. عرض الـ build script لـ mishkat_word_root.csv داخل Eqratech
2. عرض المصدر الأصلي (هل من تحليل نص آلي للقرآن؟ أم من مرجع لغوي؟)

**اقتراحي:** هذا التحفّظ نُسجّله ولا يَمنع التقدُّم — لأن:
- المستخدم هو صاحب Eqratech (Hiyassat)
- البيانات داخل مشاريعه الخاصة
- نملك audited_roots كـ ground-truth cross-check
- نملك mishkat_extracted كـ Quran-attested cross-check

كأمان إضافي، نستخدم flag `root_audited=true` في الـ rows التي تجاوزت cross-check.

---

## المقارنة مع labels.jsonl (للتذكير بالفرق)

| الجانب | mishkat (المستخدم) | labels.jsonl (مشروع آخر) |
|---|---|---|
| المصدر | Eqratech_Hussein_Hiyassat_Project | new_arabic_analyzer (نفس عائلة المشاريع لكن أداة مستقلة) |
| الـ extraction script | متاح: `derive_wazn_from_mishkat.py` | متاح: `tools/build_i3rab_labels.py` (في new_arabic_analyzer) |
| Rule-based? | نعم (نقرأ كل قاعدة) | نعم (الفريق ذكر أنها rule-based) |
| لكن — ملكية الـ rules؟ | نملكها نحن | نملكها لكنّها في مشروع شقيق |

**الفرق الجوهري الذي أثرتَه:** لو نسخنا labels.jsonl → نضع labels في MEEMAR.csv دون أن **نراجع كل rule** بأنفسنا. مع mishkat، نملك السكربت ونفهم كل قاعدة.

**الـ Layer A الصحيح** يكتب rules جديدة في `clean_code/i3rab_rules.py` نملكها بالكامل، وليس استيراد labels.

---

## التوصية

✅ **wazn_matcher نظيف للمضي قُدماً في Layer A**

كل المعلومات في عمود `Our_Root` و `Our_Wazn` في MEEMAR.csv قابلة للتتبع إلى:
- mishkat (Eqratech) → audit available outside session
- audited_roots (salehan) → لسان العرب citations
- canonical_table (alasmaa) → Final_Corrected

**أقترح المضي مباشرة لـ Layer A** — كتابة `clean_code/i3rab_rules.py` rule-based نملك كل قاعدة فيها.

---

## ملف audit للتتبع

ملف: `MISHKAT_AUDIT_REPORT.md` (هذا الملف)
الحالة: ✅ Cleared
الوصف: كل DB في wazn_matcher مصدره موثَّق، إما عمل المستخدم أو مُستخرَج rule-based منه.
