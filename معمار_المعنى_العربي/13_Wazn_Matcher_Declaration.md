# ١٣ — الإعلان الدستوري لِـ wazn_matcher الرسمي
## Official Wazn Matcher Declaration

> **تاريخ الإعلان:** 2026-05-18  
> **الحالة:** قاعدة دستورية تنفيذية، حاكمة على كل الكود التحليلي  
> **يَكمّل:** `12_Project_Scope_Declaration.md`  
> **يَستبدل:** الاعتماد على `alasmaa/analyzer_word.py`

---

## ١. النص الدستوري

> **الموديول `hussein/clean_code/wazn_matcher.py` هو المُحلِّل الرسمي  
> لاستخراج الوزن والجذر من الكلمة (word → wazn + root)  
> في معمار المعنى العربي.**

---

## ٢. التحوّل المعماري

| العنصر | قبل | بعد |
|---|---|---|
| المُحلِّل الرسمي | `alasmaa/analyze_word.py` | **`hussein/clean_code/wazn_matcher.py`** |
| قاعدة الأوزان | 80 (alasmaa) | **403 موحَّدة** (canonical + extensions + mishkat) |
| الـ variants | 4-8 | **20+** (clitic، ال، lam-lam، pronoun، number، shadda × combinations) |
| Coverage على MASAQ | 21% | **86%** |
| Top-1 على MASAQ | 17% | **57.5%** |
| Top-3 على MASAQ | 17% | **62.7%** |

---

## ٣. المُكوِّنات الرسمية للقاعدة

`wazn_matcher` يَستخدم ٣ مصادر متكاملة:

### المصدر ١: الجدول القانوني
- `clean_code/data/Mushtaqat_Full_Weights_Table.xlsx`
- 79 وزنًا قياسيًا للمشتقات (اسم الفاعل، اسم المفعول، الصفة المشبهة، صيغ المبالغة، إلخ)
- مصدر: hussein/data (محلي، لا اعتماد على alasmaa)

### المصدر ٢: الإضافات الدستورية
- `clean_code/data/wazn_db_extensions.csv`
- ٦٠+ نمط مضاف يدويًا:
  - جموع التكسير (أَفْعَال، فُعُول، فِعَال، مَفَاعِل، مَفَاعِيل، فَوَاعِل، فَعَائِل، أَفَاعِيل)
  - الرباعيات (فَعْلَل، فَعْلَال، فُعْلُول، فِعْلِيل، فَعَالِل، فَعَالِيل)
  - أوزان مضارع الأفعال (يَفْعَلُ، يَسْتَفْعِلُ، يَفْتَعِلُ، إلخ)
  - الشواذ (آلِهَة، أَنَا، إِيَّا، فَعَّال، فَوَاعِلَة)

### المصدر ٣: المُستخرَج من القرآن
- `clean_code/data/mishkat_word_root_with_wazn.csv`
- 10,219 صفًا (root, word, count, wazn) — جميعه قرآني
- مُستخرَج بـ `derive_wazn_from_mishkat.py`
- يُغذّي قاعدة المعجم القرآني (4,500+ جذر فريد)

---

## ٤. الالتزامات الدستورية المُحققَة

| الالتزام (من `12_Project_Scope_Declaration.md`) | كيف يُحقَّق |
|---|---|
| **Source-of-Claim** | كل match يَحمل `source` = canonical_table / user_extensions / mishkat_extracted (أو مجموعة) |
| **Confidence-of-Claim** | كل match يَحمل `confidence ∈ [0, 1]` محسوبة من 6 عوامل: variant_cost، src_boost، movement_sim، audit_boost، transformation_coherence، clitic_penalty |
| **Alternatives-Preserved** | `analyze()` يُرجع `list[WaznMatch]` مرتَّبة، لا قراءة واحدة |
| **Reversibility** | كل WaznMatch يَحمل `evidence: tuple[str]` و `variant_label`، فالمُستخدم يَكشف الـ pipeline ويَنقض أي قراءة |

---

## ٥. الأداء على القرآن (MASAQ 10,000 كلمة فريدة)

```
═══════════════════════════════════════════════════════════════════
                    wazn_matcher    alasmaa    تَحسّن
═══════════════════════════════════════════════════════════════════
 Coverage              86.3%         21.2%     ×4.1
 Top-1 accuracy        57.5%         16.8%     ×3.4
 Top-3 accuracy        62.7%         16.8%     ×3.7
═══════════════════════════════════════════════════════════════════
```

### بحسب الفئة (Top-1)

| الفئة | wazn_matcher | alasmaa |
|---|---:|---:|
| سالم سليم | **89.8%** | 26.6% |
| مهموز سليم | **94.4%** | 12.7% |
| معتل | **57.2%** | 6.4% |
| مضاعَف | **41.2%** | 7.0% |
| رباعي | **57.1%** | 0.0% |

---

## ٦. حدود الوزن المُعلَنة

أَسماء **لا يُحلَّلها** wazn_matcher (بقصد):

| الفئة | السبب | السلوك المُعلَن |
|---|---|---|
| **لفظ الجلالة** (الله وصوره) | قراءة دستورية (`12_Project_Scope_Declaration.md`): الاسم الإلهي لا يُسلَّط عليه تحليل وزن | Hardcoded → `root=ءله, bab=divine_name` |
| **الأسماء الموصولة** (الذي، الذين، التي، اللاتي) | كلمات مبنية مغلقة (closed-class)، لا اشتقاق وزني | Hardcoded → `bab=closed_class_lexeme` |
| **أسماء الإشارة** (هذا، هذه، ذلك، تلك) | كلمات مبنية مغلقة | Hardcoded → `bab=closed_class_lexeme` |
| **الأعلام الأعجمية** (إبراهيم، يونس...) | غير مشتقة | الـ `aalam_loader` يَتولاها |
| **ضمائر منفصلة** (أنا، أنت، هو، نحن، إيَّا) | كلمات مبنية | تحليل سطحي فقط |

---

## ٧. واجهة الاستخدام

```python
from clean_code.wazn_matcher import AnalyzerV2

analyzer = AnalyzerV2()
matches = analyzer.analyze("كَاتِبٌ", max_results=3)

for m in matches:
    print(m.wazn, m.root, m.confidence, m.source, m.evidence)
```

CLI:
```bash
python3 hussein/clean_code/wazn_matcher.py "اتَّخَذَ" --max 5
python3 hussein/clean_code/wazn_matcher.py "نَسْتَعِينُ" --json
```

---

## ٨. القرار الحاكم

| قرار | التأثير |
|---|---|
| wazn_matcher هو **الواجهة الوحيدة المُعتمَدة** لاستخراج وزن وجذر في المعمار | كل ملف يَستخدم تحليل وزن يَستورد من `clean_code/wazn_matcher.py` |
| alasmaa/analyze_word.py **مرجع تاريخي فقط** — لا يُستدعى من الـ pipeline | الـ adapter في `architecture_test/` يَنتقل لاستخدام wazn_matcher |
| الـ unified_wazn_database **القاعدة الرسمية للأوزان** | لا أوزان خارج هذه القاعدة تَدخل التحليل |
| التحسينات اللاحقة تَدخل عبر **PR على clean_code/** | المسار `src/architecture_test/analyzer_v2.py` نسخة عمل، يَتزامن دوريًا مع clean_code |

---

## ٩. الأرشيف والتاريخ

| الإصدار | تاريخ | top-1 MASAQ | محتوى |
|---|---|---:|---|
| baseline | (alasmaa) | ~17% | structural matching، 80 وزنًا |
| v2.0 | 2026-05-17 | 45.3% | قاعدة موحَّدة + 12 variant |
| v2.1 | 2026-05-18 | 53.5% | لفظ الجلالة + فَعْلَان + ى/ي |
| v2.2 | 2026-05-18 | 56.2% | Form X + ي/و alternation |
| v2.3 | 2026-05-18 | 56.3% | closed-class + smart shadda |
| **v2.4** | **2026-05-18** | **57.5%** | **shadda combos + article-augment penalty** |

---

## ١٠. التوقيع الدستوري

هذا الإعلان:
- **يَنفذ** فور إضافته (2026-05-18)
- **يَتفاعل** مع `12_Project_Scope_Declaration.md` بالتأكيد على أن الـ wazn_matcher أداة "محاكاة تحليلية شفافة" لا "محاكاة فهم"
- **لا يَستثني** المعتل/المضاعف من النطاق — يَعلن حدود الدقة لكل فئة بصراحة
- **يُلزم** بتحديث المتري في README فور كل تَحسين ملموس
