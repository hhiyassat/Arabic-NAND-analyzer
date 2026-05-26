# Benchmarks vs State-of-the-Art

> **آخر تحديث:** 2026-05-18  
> **الغرض:** تَتبُّع الفجوة بين wazn_matcher (مشروعنا) وأفضل الأنظمة الموجودة في تحليل الصرف العربي. لكي نَبقى صادقين مع أنفسنا.

---

## ١. المقارنة الكمية (Top-1 على القرآن أو نص مماثل)

| النظام | Top-1 | الفجوة عنّا |
|---|---:|---:|
| **CAMeL Tools** (NYU، 2020+) | ~96% | +38.7% |
| **MADAMIRA** (Stanford/Columbia/CMU، 2014+) | ~95% | +37.7% |
| **Farasa** (QCRI، 2016+) | ~93% | +35.7% |
| **AlKhalil** (UMP، 2014+) | ~90% | +32.7% |
| **wazn_matcher** (مشروعنا، 3 أسابيع) | **57.3%** | — |

---

## ٢. التفاصيل التقنية لكل نظام

### CAMeL Tools — NYU
- **Approach:** ML-based hybrid (rule + neural)
- **Training data:** Penn Arabic Treebank, ATB1-3, MADAMIRA gold corpus (~1M words)
- **Years of dev:** 5+
- **Team:** Owen Rambow et al., Computational Approaches to Modeling Language Lab
- **Key metric:** 96% root identification on MSA, ~93% on Quranic
- **Why it wins:** trained on massive curated treebanks
- **Where it fails:** poetry, dialect, OOV (out-of-vocabulary), low-resource Arabic

### MADAMIRA — Stanford/Columbia/CMU
- **Approach:** Statistical disambiguation over AraMorph lexicon + SVM classifier
- **Training data:** PATB1 (1.4M tokens) + dictionary-based generation
- **Years of dev:** 10+
- **Team:** Habash, Pasha, Roth, El Kholy
- **Key metric:** 95% root, 96% lemma, 98% POS
- **Why it wins:** mature lexicon (~250k stem-tag pairs), refined disambiguation
- **Where it fails:** vocalized text without context, rare dialectal forms

### Farasa — QCRI
- **Approach:** SVM-based with hand-crafted features
- **Training data:** Arabic Treebank + diverse Arabic corpora
- **Years of dev:** 5+
- **Team:** Hamdy Mubarak et al.
- **Key metric:** 93% segmentation, 95% POS
- **Why it wins:** robust on noisy/dialect text, fast at inference
- **Where it fails:** rare classical patterns, fully-vocalized analysis

### AlKhalil — Université Sidi Mohamed Ben Abdellah, Morocco
- **Approach:** Rule-based morphological analyzer (الخليل بن أحمد inspired)
- **Training data:** 7,755 verbs, 30,000+ nouns lexicon
- **Years of dev:** 10+
- **Team:** Mohamed Boudchiche et al.
- **Key metric:** 90% on MSA, applies classical morphology rules
- **Why it interesting:** closest in spirit to our rule-based approach
- **Where it fails:** lower coverage, slower than ML

---

## ٣. ما يَخدم نظامنا (الفروقات الجوهرية)

| البُعد | الأنظمة الكبرى | wazn_matcher |
|---|---|---|
| **النهج** | ML/SVM/neural على corpus كبير | rule-based + lookup شفاف |
| **التَدريب** | عشرات الآلاف إلى مليون كلمة | ~16k mishkat، rules كتبتها يدًا |
| **زمن التطوير** | 5-10 سنوات | 3 أسابيع |
| **حجم الفريق** | فِرق بحثية أكاديمية | شخص واحد + AI assistant |
| **التَبعيات** | ATB، Penn Treebank، lexicons تجارية | Quran corpus محلي + ALasmaa weights |
| **القابلية للتفسير** | غالبًا "صندوق أسود" | كل قرار قابل للتتبع |
| **القابلية للحوكمة** | محدودة | كاملة (Source/Confidence/Alternatives/Reversibility) |
| **التَركيز** | عموم الفصحى الحديثة | القرآن أساسًا |

---

## ٤. ما لا يَخدم نظامنا

ولا بُد من ذكر هذا بصدق:

| العيب | السبب |
|---|---|
| Top-1 منخفض نسبيًا | لا تدريب على corpus ضخم |
| لا verb conjugation table | لم نَبنِها بعد |
| المعتل والمضاعَف ضعيفان | rule patterns غير كافية |
| الفجوة على الـ 35% non-Quranic | لم نُختبر خارج القرآن |
| لا confidence calibration | scores هي raw composites |

---

## ٥. ما الذي يَكون مُنصفًا للمقارنة؟

المقارنة المباشرة Top-1 ليست عادلة لأن:

1. **الأنظمة تلك مُدرَّبة على PATB**: التي ليست متاحة لنا (تجارية، ~5,000$/license)
2. **هم يَقيسون POS+lemma+root معًا**: نحن نَقيس root فقط
3. **نطاق المهمة مختلف**: هم general MSA، نحن Quranic أساسًا
4. **نهج مختلف**: نحن transparent rule-based، هم opaque ML

**معيار أكثر إنصافًا:** Top-1 على Quranic-only data، مع نظام rule-based فقط.

- وفقًا لـ AlKhalil على القرآن: ~90% root accuracy (لكن قياسه يَختلف)
- ووفقًا لنا: 90% top-1 على السالم القرآني، 57% إجمالي

في فئة rule-based-only، نحن **متوسط مقبول** بعد 3 أسابيع.

---

## ٦. الهدف الواقعي

**في 6 أشهر من العمل المُكَرَّس** (ليس 10 سنوات أكاديمية):

| الأساس | الهدف الواقعي |
|---|---|
| ✅ Foundation كامل (Normalizer + Segmenter v2) | 65% top-1 |
| ✅ Verb conjugation table | 72% top-1 |
| ✅ Deep geminate patterns | 78% top-1 |
| ✅ Confidence calibration | لا يُغير accuracy، لكن يُحسن usefulness |
| ✅ Confidence-weighted top-3 | 85% effective accuracy |

**حد سقف واقعي للمشروع (3 سنوات):** 85-88% top-1، مع الإبقاء على القابلية للتفسير.

**ما لا يُمكنا تَجاوزه دون ML:** 95%+ — يَتطلب trained model على corpus ضخم.

---

## ٧. ما يَستحق المتابعة في الأنظمة الأخرى

عيون مفتوحة على:

| النظام | لماذا نَتابعه |
|---|---|
| **CAMeL Tools** | يَنشر updates دورية، open source — قد نَستفيد من بنيته |
| **AlKhalil** | أقرب لنا نهجًا، fully rule-based — مرجع للقواعد |
| **AraBERT / CAMeLBERT** | نماذج لغوية، قد نَستخدمها كـ post-processor لـ disambiguation |
| **Quran Corpus Project** (Leeds) | لـ tags ground truth إضافية |
| **OpenITI corpus** | للقياس خارج القرآن |

---

## ٨. القاعدة الدستورية المُلازِمة

نحن **لا نَسعى لِأن نَكون نظام ML**. هدفنا الدستوري (القاعدة #21) هو:

> "محاكاة تحليلية شفافة قابلة للحوكمة"

لذا المقارنة المباشرة top-1 ضد ML systems **متحيِّزة**. الأهداف مختلفة:

- **هم:** أعلى accuracy على أي نص
- **نحن:** كل قرار قابل للتتبع، confidence محسوب، alternatives محفوظة، reversible

نظام بـ 60% top-1 شفاف **قد يَكون أكثر فائدة** لمستخدمنا (الباحث، المُفسِّر، الطالب) من نظام 95% opaque يَقول "هذا هو الجذر" دون شرح.

---

## ٩. الخلاصة الصادقة

| السؤال | الإجابة |
|---|---|
| هل نَحن state-of-the-art؟ | **لا**. نحن متوسطون كنظام rule-based. |
| هل نَفقد ٤٠% مقارنة بـ CAMeL Tools؟ | في top-1 raw — نعم. في explainability — نَتفوق. |
| هل المقارنة عادلة؟ | جزئيًا. نَفقد لأسباب بنيوية (ML vs rule)، لا أسباب جوهرية. |
| ما الهدف الواقعي 3 سنوات؟ | 85% top-1 مع شفافية كاملة. وراء هذا يَحتاج تَبدّل في النهج (إضافة ML layer). |
| هل نَستسلم؟ | لا. نَستمر، نَقيس، ونَكون صادقين عن الفجوة. |

---

## ١٠. تَحديث دوري

هذا الملف يُحدَّث كلما تَغيَّر أحد:
- إصدار جديد لـ wazn_matcher مع benchmark جديد
- نشر علمي/إصدار جديد من CAMeL/MADAMIRA/Farasa
- مرجع أكاديمي جديد لِقياس Quranic morphology

**مسؤول التحديث:** صاحب المشروع.  
**دورية المراجعة:** كل 3 أشهر أو عند إصدار جديد.

---

## ١١. روابط للمتابعة

- CAMeL Tools: <https://github.com/CAMeL-Lab/camel_tools>
- MADAMIRA: <https://camel.abudhabi.nyu.edu/madamira/>
- Farasa: <https://farasa.qcri.org/>
- AlKhalil: <https://sourceforge.net/projects/alkhalil/>
- Quran Corpus (Leeds): <https://corpus.quran.com/>
- Penn Arabic Treebank: <https://catalog.ldc.upenn.edu/LDC2010T13>

---

*الذي لا يَقيس نَفسه ضد الأفضل لا يَتطور.  
الذي يَقيس نفسه دون أمانة يَخدع نفسه.*
