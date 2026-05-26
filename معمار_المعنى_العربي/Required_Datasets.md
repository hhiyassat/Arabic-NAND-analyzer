# قائمة البيانات المطلوبة للمشروع
## Required Datasets Inventory

> هذه قائمة شاملة بأنواع البيانات التي يحتاجها معمار المعنى العربي ليعمل على أكمل وجه.  
> مقسَّمة إلى: **(A) متوفر فعلًا** — **(B) ناقص / غير مكتمل** — **(C) مستقبلي / توسعي**.  
> تُحدَّث دوريًا، ويُسجَّل عند كل جلسة ما أُضيف وما يبقى.

---

## القاعدة الحاكمة على هذا الملف

> **هذا الملف يقع في المستوى الحاسوبي (انظر `11_Abstraction_Levels.md`). البيانات هنا تخدم المستويين اللغوي والإدراكي، ولا تستبدلهما. الكمال البياني ليس شرطًا للكمال الفلسفي، لكنه شرط للتنفيذ التشغيلي.**

---

## A. متوفر فعلًا (موجود محليًا أو في مشاريع شقيقة مربوطة)

### A.0 الموارد الخارجية الكبيرة (في `/Users/husseinhiyassat/fractal/new_arabic_analyzer/data/`)

> **اكتشاف مهم:** كثير من البيانات التي ظُنّت "ناقصة" متوفرة في new_arabic_analyzer بصورة شاملة جدًا.

#### الجذور والمعاجم الجذرية

> **تنبيه:** المصدر الأساسي للجذور هو `hussein/data/audited_roots.csv` (محلي، مدقَّق). موارد new_arabic_analyzer ثانوية ومرجعية فقط.

| الملف | الموقع | الحجم | المحتوى |
|---|---|---|---|
| **`audited_roots.csv`** ⭐ | `hussein/data/` | **4,769** | جذور مدقَّقة مع: الفعل الماضي، الجذر، الباب الصرفي، اللزوم والتعدي، المصدر، ومرجع (لسان العرب). يحوي علم تدقيق (تم تدقيقه / تم إعادة تدقيقه / صحيح الجذر حقيقي). **المصدر المعتمد للجذور.** |
| `mishkat_word_root.csv` | new_arabic_analyzer | 16,424 | كلمة ↔ جذر مع عدد التكرار في كوربس مشكاة (مرجعي للاستعلام) |
| ~~`root_three_letters.csv`~~ | new_arabic_analyzer | ~~5,184~~ | **لا يُستخدم** — مجرد قائمة جذور بلا تدقيق ولا metadata؛ `audited_roots.csv` يحل محله |
| `horof_muaqatah.csv` | new_arabic_analyzer | 1,844 | حروف مقطعة (مرجعي) |

#### المبنيات بالكامل (`data/02_mabniyat/` — 29 ملفًا، ~545 إدخالًا)

| الملف | الإدخالات | المحتوى |
|---|---|---|
| `demonstrative_pronouns.json` | 53 | أسماء الإشارة (هذا، هذه، ذلك، تلك، هَاهُنَا، إلخ) مع الجنس، العدد، البعد، التحليل |
| `pronouns_classification.json` | 43 | الضمائر المنفصلة والمتصلة مع تصنيفها الكامل |
| `relative_pronouns.json` | 48 | أسماء الموصول مع الجنس والعدد |
| `hidden_pronouns.json` | 11 | الضمائر المستترة (وجوبًا/جوازًا) |
| `preposition_meanings.json` | 56 | حروف الجر ومعانيها |
| `built_in_adverbs.json` | 21 | الظروف المبنية |
| `vocative_particles.json` | 9 | أدوات النداء |
| `interrogative_letters_tools.json` | 6 | أدوات الاستفهام (حروف) |
| `interrogative_tools_categories.json` | 17 | تصنيفات أدوات الاستفهام |
| `conditional_letters_tools.json` | 21 | أدوات الشرط |
| `jazm_tools.json` | 20 | أدوات الجزم |
| `present_naseb_tools.json` | 10 | نواصب المضارع |
| `coordinating_conjunctions.json` | 23 | حروف العطف |
| `copulative_particle.json` | 7 | حروف القَسَم |
| `letters_answers.json` | 10 | أحرف الجواب |
| `kinaya_names.json` | 9 | أسماء الكناية (كم، كذا، إلخ) |
| `compound_numbers.json` + `_details` | 12 | الأعداد المركبة |
| `verb_name.json` | **57** | أسماء الأفعال |
| `imperative_verb_building.json` | 10 | بناء فعل الأمر |
| `past_tense_conjugation_rules.json` | 11 | قواعد تصريف الماضي |
| `present_tense_building_cases.json` | 3 | حالات بناء المضارع |
| `verb_building_rules.json` | 10 | قواعد بناء الفعل |
| `grammatical_construction_cases.json` | 55 | حالات البناء النحوية |
| `building_regulations.json` | 4 | قواعد البناء |
| `estimated_parsing_indeclinables.json` | 4 | المبنيات بإعراب تقديري |
| `functional_indeclinable_substitutes.json` | 7 | بدائل المبنيات الوظيفية |
| `indeclinable_discourse_roles.json` | 5 | أدوار المبنيات الخطابية |
| `types_of_i3rab.json` | 3 | أنواع الإعراب |

#### الاشتقاق والصرف (`data/03_juthur_mushtaqat/`)

| الملف | المحتوى |
|---|---|
| `triliteral_active_participles.json` | أسماء الفاعل الثلاثية |
| `passive_participles_triliteral.json` | أسماء المفعول الثلاثية |
| `non_passive_participles.json` | المشتقات غير الانفعالية |
| `descriptive_adjective_forms.json` | الصفات الوصفية |
| `quad_verb_analysis.json` | تحليل الأفعال الرباعية |
| `marra_conditions.json` + `_sources` | اسم المرة |
| `shadda_positions.json` + `_types` + `_weight_rules` | قواعد الشدة |
| `tamyeez_guides.json` | التمييز |

#### النحو (`data/04_nahw/` — 20 ملفًا)

| الملف | المحتوى |
|---|---|
| `kana_sisters.json` | كان وأخواتها |
| `accusative_verbs.json` | الأفعال الناصبة |
| `verb_classifications.json` | تصنيفات الأفعال |
| `verbs_five_forms.json` | الأفعال الخمسة |
| `noun_classification.json` | تصنيف الأسماء |
| `noun_extension_rules.json` | قواعد تمدد الأسماء |
| `comparative_nouns.json` + `_rules` + `_exceptions` | اسم التفضيل |
| `maf3ool_types.json` | أنواع المفعول |
| `verb_subject_rules.json` | قواعد الفاعل |
| `exception_ahkam_illa.json` + `_ghayr_siwa` + `_khala_ada_hasha` | أحكام الاستثناء |
| `al_ism_almaqsur.json` | الاسم المقصور |
| `extended_nouns.json` | الأسماء الممدودة |
| `sound_verb_types.json` | الأفعال الصحيحة |
| `nominative_cases.json` | الحالات الرفعية |
| `ta_fael.json` | تاء الفاعل |

#### الصوتيات (`data/01_phonology/`)

| الملف | المحتوى |
|---|---|
| `arabic_word_types.json` | أنواع الكلمة |
| `letter_origins.json` | مخارج الحروف |
| `phoneme_meaning.json` | معاني الفونيمات |
| `i3lal.json` | الإعلال |

#### كوربسات وموارد إضافية

| الملف | المحتوى |
|---|---|
| `MASAQ.csv` (18MB) | كوربس قرآني ضخم |
| `masaq_ayahs.csv` | آيات MASAQ |
| `quran/` (مجلد) | بيانات قرآنية |
| `operators_catalog_split_vocalized.csv` | 103 عامل مع مثال مشكَّل |
| `data_bank.csv` | بنك بيانات عام |
| `awzan_cleaned_with_example.csv` | أوزان مع أمثلة |
| `awzan_merged_final100.csv` | 100 وزن مدمج |

---

### A.1 الحروف (Huruf)

| البيانات | الموقع | الحجم | الحالة |
|---|---|---|---|
| الحروف الخام (5 علماء) | `data/Huruf_Maani_Five_Scholars_With_Ibn_Hisham.xlsx` | 401 إدخال | خام |
| الحروف الموحَّدة (canonical) | `huruf_maani_normalization/huruf_maani_unified_master.xlsx` | 179 كيان | معالَجة، مع تشكيل كامل + تصنيف + قواعد |
| المتغيرات | `huruf_maani_normalization/huruf_maani_variants.xlsx` | 25 سجل | مكتمل |
| الخلافات | `huruf_maani_normalization/huruf_maani_disagreements.xlsx` | 102 سجل | مكتمل |
| المتشابهات للمراجعة | `huruf_maani_normalization/huruf_maani_duplicates_review.xlsx` | 21 زوج | مكتمل |

### A.2 المشتقات (Mushtaqat)

| البيانات | الموقع | الحجم | الحالة |
|---|---|---|---|
| أوزان المشتقات (corrected) | `data/Mushtaqat_Weights_Final_Corrected_With_Fa3l-minimall.xlsx` | 80 وزن، 16 باب | مكتمل |
| الجدول الكامل | `data/Mushtaqat_Full_Weights_Table.xlsx` | — | مرجعي |
| أوزان alasmaa الإضافية | `/Users/husseinhiyassat/fractal/alasmaa/Mushtaqat_Weights_Final_Corrected_With_Fa3ll.xlsx` | 80 وزن | مع وزن fa3ll الإضافي |

### A.3 الجوامد (Jamid)

| البيانات | الموقع | الحجم | الحالة |
|---|---|---|---|
| تصنيف الجوامد (seed) | `data/الجوامد.xlsx` | 20 تصنيف، 116 مثال | seed موسَّع بعد إضافة شَهْر/سَنَة/عَام |

**التصنيفات الـ 20 الموجودة:**
1. اسم ذات • 2. اسم جنس • 3. اسم علم • 4. اسم معنى جامد • 5. اسم عدد • 6. اسم مكان جامد • 7. **اسم زمان جامد** (موسَّع) • 8. اسم إشارة • 9. اسم موصول • 10. ضمير • 11. اسم شرط • 12. اسم استفهام • 13. اسم صوت • 14. اسم فعل • 15. مصدر جامد/غير قياسي • 16. أسماء الكنايات • 17. أسماء الظروف المبنية • 18. أسماء الجهات • 19. أسماء المقادير والمكاييل • 20. الأسماء الأعجمية والمعرّبة.

### A.4 موارد خارجية مربوطة

| البيانات | المصدر | الاستخدام |
|---|---|---|
| Operator surfaces (closed-class) | alasmaa/analyze_word.py + operators_catalog | كشف العوامل المغلقة |
| Salehan ZAMAN_WORDS | salehan/zarf_engine.py | المدد الزمنية (متسق مع جدولنا الآن) |
| Salehan segmenter rules | salehan/segmenter.py | فصل البادئات واللواحق |
| NAA normalize | new_arabic_analyzer/normalize.py | NFC + آ → ءَ |
| Sun/Moon letters | salehan (constants) | الإدغام الشمسي |

---

## B. ناقص أو ينتظر **الربط** (المعظم متوفر خارجيًا، لم يُربط بعد)

> **تنبيه:** بعد مراجعة `new_arabic_analyzer/data/`، تبيَّن أن أكثر الفجوات التي ظُنّت "غير موجودة" متوفرة بصورة شاملة في المشروع الشقيق. السطر الحاكم في كل فقرة الآن: **موجود خارجيًا — يحتاج loader في `src/architecture_test/`**.

### B.1 الجذور (Roots) — ✅ **متوفر محليًا، يحتاج loader فقط**

| ما المطلوب | الحالة | المصدر المعتمد |
|---|---|---|
| قاعدة جذور مدقَّقة | ✅ **متوفر** | `hussein/data/audited_roots.csv` — **4,769 جذر مدقَّق** |
| الجذر + الفعل الماضي + الباب الصرفي | ✅ **متوفر** | نفس الملف (الفعل الماضي + باب الصرفي) |
| اللزوم والتعدي | ✅ **متوفر** | نفس الملف (لازم/متعدي/مشترك) |
| المصدر الفعلي لكل جذر | ✅ **متوفر** | نفس الملف (عمود "المصدر": غُرُوب، خَتْل، إلخ) |
| المرجع التراثي | ✅ **متوفر** | نفس الملف (المرجع: لسان العرب لمعظمها) |
| flags التدقيق | ✅ **متوفر** | تم تدقيقه / تم إعادة تدقيقه / صحيح الجذر |
| ربط الكلمة بجذرها (word→root) | ✅ خارجي مساعد | `new_arabic_analyzer/mishkat_word_root.csv` — 16,424 إدخال (للاستعلام السريع) |
| الجذور مع المعنى الأم (دلالة جامعة) | ❌ غير موجود | يحتاج بناء يدوي من معاجم تراثية لاحقًا |
| الجذور المهموزة/المعتلة/المضعفة | ضمني | يمكن استخراجه من بنية الجذر |

**الأثر:** يحتاج `roots_loader.py` يقرأ `audited_roots.csv` ويوفر:
- `lookup_root(root)` → metadata الكامل
- `lookup_by_past_verb(verb)` → الجذر
- `roots_by_bab(bab)` → كل جذور باب صرفي معين
- التحقق من صحة الجذر (audit flags)

### B.2 الأعلام والأسماء الخاصة — **أولوية: بناء (محدود)**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| أسماء الأشخاص (مذكر/مؤنث) | جزئي | seed صغير في الجوامد + بحث في mishkat_word_root |
| أسماء الأماكن (مدن، بلدان، أنهار، جبال) | جزئي | يمكن استخراج بعضها من MASAQ القرآني |
| أسماء قبائل وقوميات | غير موجود | يحتاج بناء seed |
| الأعلام القرآنية (أنبياء، شخصيات) | ضمني في MASAQ | يحتاج استخراج |
| الأعلام الأعجمية المعرَّبة | seed صغير | يحتاج توسعة |

**الأثر:** هذه فجوة فعلية. يحتاج بناء seed موسَّع للأعلام بأنواعها.

### B.3 الضمائر والإحالة — ✅ **متوفر بالكامل خارجيًا**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| الضمائر المنفصلة | ✅ **متوفر** | `02_mabniyat/pronouns_classification.json` — 43 إدخال |
| الضمائر المتصلة (متكلم/مخاطب/غائب) | ✅ **متوفر** | في نفس الملف |
| الضمائر المستترة (وجوبًا/جوازًا) | ✅ **متوفر** | `02_mabniyat/hidden_pronouns.json` — 11 إدخال |
| ضمائر الفصل والشأن | جزئي في نفس الملف | — |

**الأثر:** يحتاج فقط `pronouns_loader.py`. ملف `14_Pronoun_and_Reference_System.md` المحجوز في `08_Future_Files_Map.md` يمكن كتابته **استنادًا إلى هذه البيانات**.

### B.4 الأفعال — ✅ **متوفر جزئيًا خارجيًا**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| تصريف الماضي | ✅ **متوفر** | `02_mabniyat/past_tense_conjugation_rules.json` — 11 |
| بناء المضارع | ✅ **متوفر** | `02_mabniyat/present_tense_building_cases.json` — 3 |
| بناء الأمر | ✅ **متوفر** | `02_mabniyat/imperative_verb_building.json` — 10 |
| قواعد بناء الفعل عمومًا | ✅ **متوفر** | `02_mabniyat/verb_building_rules.json` — 10 |
| كان وأخواتها | ✅ **متوفر** | `04_nahw/kana_sisters.json` |
| الأفعال الناصبة | ✅ **متوفر** | `04_nahw/accusative_verbs.json` |
| تصنيفات الأفعال | ✅ **متوفر** | `04_nahw/verb_classifications.json` |
| الأفعال الخمسة | ✅ **متوفر** | `04_nahw/verbs_five_forms.json` |
| الأفعال الصحيحة | ✅ **متوفر** | `04_nahw/sound_verb_types.json` |
| نواصب المضارع | ✅ **متوفر** | `02_mabniyat/present_naseb_tools.json` |
| أدوات الجزم | ✅ **متوفر** | `02_mabniyat/jazm_tools.json` |
| أسماء الأفعال (هيهات، شتان، إلخ) | ✅ **متوفر بشمول** | `02_mabniyat/verb_name.json` — 57 |
| الأفعال المعتلة (مثال، أجوف، ناقص، لفيف) | ضمني | يحتاج تصنيف صريح |
| Frame semantics للأفعال | غير موجود | يحتاج بناء |

**الأثر:** يحتاج `verbs_loader.py` يجمع هذه الملفات.

### B.5 العناصر المورفولوجية المنفصلة — ✅ **متوفر**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| أل التعريف ومعانيها | ✅ ضمنيًا في `preposition_meanings.json` + `data_bank.csv` | — |
| التنوين وأنواعه | ✅ في `04_nahw/types_of_i3rab.json` + grammatical_construction_cases | — |
| نون النسوة، نون التوكيد، نون الوقاية | ✅ في `building_regulations.json` | — |
| تاء التأنيث، تاء الفاعل | ✅ `04_nahw/ta_fael.json` | — |

### B.6 شبه الحروف (Quasi-Particles) — ✅ **متوفر**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| حروف الجر الكاملة (56 إدخالًا) | ✅ **متوفر** | `02_mabniyat/preposition_meanings.json` |
| العوامل المغلقة + 103 عامل مشكَّل | ✅ **متوفر** | `operators_catalog_split_vocalized.csv` |
| مع، عند، لدى، نحو | ✅ في data_bank + horof_muaqatah | — |
| سوى، غير، خلا، حاشا، عدا | ✅ في exception_ahkam | `04_nahw/exception_ahkam_*.json` |

### B.7 العلاقات الدلالية (Lexical Relations) — **فجوة فعلية**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| المرادفات (Synonyms) | ❌ غير موجود | يحتاج بناء |
| الأضداد (Antonyms) | ❌ غير موجود | يحتاج بناء |
| العام والخاص (Hypo/Hypernyms) | ❌ غير موجود | يحتاج بناء |
| الكل والجزء (Mereology) | ❌ غير موجود | يحتاج بناء |
| التصنيفات الموضوعية | جزئي | في الجوامد (اسم جنس، اسم ذات) |

**الأثر:** هذه فجوة حقيقية. لا يحلها new_arabic_analyzer. يحتاج بناء WordNet عربي أو استيراد Arabic WordNet موجود.

### B.8 الجموع الشاذة والممنوع من الصرف — ✅ **متوفر**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| الممنوع من الصرف | ✅ في `noun_extension_rules.json` + `comparative_exceptions.json` | — |
| الأسماء الستة | ✅ ضمني في `extended_nouns.json` | — |
| المثنى والملحق به | ✅ في `compound_numbers.json` + grammatical_construction_cases | — |
| جموع التكسير الشاذة | جزئي | يحتاج dataset مستقل |

### B.9 القواعد الصوتية — ✅ **متوفر**

| ما المطلوب | الحالة | المصدر |
|---|---|---|
| قواعد الإعلال | ✅ **متوفر** | `01_phonology/i3lal.json` |
| مخارج الحروف | ✅ **متوفر** | `01_phonology/letter_origins.json` |
| معاني الفونيمات | ✅ **متوفر** | `01_phonology/phoneme_meaning.json` |
| الحروف الشمسية والقمرية | ضمني في salehan | يحتاج dataset رسمي |
| قواعد الإدغام التفصيلية | جزئي في salehan | يحتاج توسعة |

---

## C. مستقبلي / توسعي (للمراحل التالية)

### C.1 الكوربس النصي (Text Corpora)

| ما المطلوب | الوصف |
|---|---|
| النص القرآني الكامل | مع التشكيل، القراءات، الإعراب |
| الحديث النبوي | كتب الصحاح بإسناد |
| الشعر الكلاسيكي | المعلقات، ديوان المتنبي، إلخ |
| النثر الكلاسيكي | الجاحظ، البيان والتبيين، إلخ |
| النصوص المعاصرة | مقالات، أخبار، أدب حديث |

**الاستخدام:** اختبار المعمار على نطاق واسع، تحسين المطابقة، تجميع إحصاءات.

### C.2 الكوربسات المُعلَّمة (Annotated Corpora)

| ما المطلوب | الوصف |
|---|---|
| إعراب القرآن | عربي ولاتيني، مع شرح الوظائف النحوية |
| ال POS-tagged corpus | كلمة + part of speech |
| Dependency-parsed corpus | علاقات نحوية بين الكلمات |
| Semantically-annotated | علاقات دلالية موثَّقة |

### C.3 طبقات Extension (مؤجَّلة دستوريًا)

(بحسب `00_Project_Constitution.md`: الطبقات التوسعية المؤجلة.)

- **النفسية:** مفردات الانفعال، الإرادة، الوعي.
- **الاجتماعية:** الأدوار الاجتماعية، العلاقات الأسرية، التراتب.
- **القانونية:** المصطلحات الشرعية، الفقه، الأحكام.
- **الثقافية:** المرجعيات الحضارية، الكنايات الثقافية.
- **القرآنية الخاصة:** أسباب النزول، القراءات السبع، الناسخ والمنسوخ، التفاسير.

### C.4 الفهارس الإحصائية واللغوية

| ما المطلوب | الوصف |
|---|---|
| تكرارات الجذور | إحصاء استعمالها في كوربس قرآني/شعري |
| توزيع الأوزان | أيها أكثر إنتاجًا |
| Collocations | الكلمات التي تظهر متجاورة كثيرًا |
| n-grams | ثنائيات وثلاثيات الكلمات الشائعة |

### C.5 خرائط معرفية تفصيلية

| ما المطلوب | الوصف |
|---|---|
| Knowledge Graph للقرآن | الكيانات والأحداث وعلاقاتها |
| Knowledge Graph للسيرة النبوية | الأشخاص، الأحداث، الأماكن، الأزمنة |
| Ontology لكل طبقة Extension | بعد فك التجميد الدستوري |

### C.6 موارد متعددة اللهجات والمستويات

| ما المطلوب | الوصف |
|---|---|
| Dialect data | عامية مصرية، شامية، خليجية، مغاربية |
| المستويات اللغوية | فصحى تراثية، فصحى معاصرة، شبه فصحى |
| Borrowed vocabulary | كلمات إنجليزية/فرنسية/فارسية/تركية معرَّبة |

---

## ملخص الأولويات (محدَّث بعد اكتشاف new_arabic_analyzer)

| الأولوية | البيانات | المصدر | الإجراء المطلوب |
|---|---|---|---|
| 🔴 عالية | **الجذور المدقَّقة** (4,769 جذر) | **`hussein/data/audited_roots.csv`** ⭐ | بناء `roots_loader.py` |
| 🔴 عالية | **word→root** (16,424 إدخال — مساعد) | new_arabic_analyzer/mishkat_word_root.csv | lookup ثانوي |
| 🔴 عالية | **الضمائر الكاملة** | new_arabic_analyzer/02_mabniyat/pronouns_classification.json + hidden_pronouns.json | بناء `pronouns_loader.py` |
| 🔴 عالية | **حروف الجر الـ 56** | new_arabic_analyzer/02_mabniyat/preposition_meanings.json | دمج مع huruf |
| 🔴 عالية | **أسماء الإشارة الـ 53** | new_arabic_analyzer/02_mabniyat/demonstrative_pronouns.json | بناء loader |
| 🔴 عالية | **الأسماء الموصولة الـ 48** | new_arabic_analyzer/02_mabniyat/relative_pronouns.json | بناء loader |
| 🔴 عالية | **أسماء الأفعال الـ 57** | new_arabic_analyzer/02_mabniyat/verb_name.json | بناء loader |
| 🟡 متوسطة | الأفعال (تصريف، أنواع، نواصب، جوازم) | new_arabic_analyzer/02_mabniyat/* + 04_nahw/* | بناء `verbs_loader.py` موحَّد |
| 🟡 متوسطة | الظروف، أدوات النداء، الاستفهام، الشرط | new_arabic_analyzer/02_mabniyat/* | بناء loaders |
| 🟡 متوسطة | الإعلال، مخارج الحروف، فونيمات | new_arabic_analyzer/01_phonology/* | بناء phonology_loader |
| 🟡 متوسطة | الاستثناء، التفضيل، أنواع المفعول | new_arabic_analyzer/04_nahw/* | بناء nahw_loader |
| 🟡 متوسطة | الأعلام (أشخاص، أماكن، قبائل) | جزئي — يحتاج بناء seed موسَّع | جمع من mishkat + إضافة |
| 🟢 فجوة فعلية | **العلاقات الدلالية** (مرادفات، أضداد، عام/خاص) | غير موجود في أي مصدر متاح | يحتاج بناء WordNet عربي أو استيراد |
| 🟢 منخفضة | الجموع الشاذة، الفعل المعتل التصنيفي | جزئي في 04_nahw | تحسينات |
| 🔵 مستقبلية | كوربسات (MASAQ 18MB موجود!)، فهارس، طبقات Extension | MASAQ متاح في new_arabic_analyzer | للاستخدام لاحقًا |

---

## ملاحظات منهجية على بناء البيانات

### مبدأ 1: عدم التضخم
لا تُضاف dataset جديدة لمجرد توفرها. كل dataset يجب أن:
- تخدم حاجة موثَّقة في الاختبارات أو الفجوات.
- تكون مرتبطة بمستوى محدد من الـ Abstraction Levels.
- يكون لها loader في `src/architecture_test/` يستوردها.

### مبدأ 2: التشكيل قياسي
كل dataset جديدة تستلزم تشكيلًا كاملًا قياسيًا في الأمثلة، حتى لو كان البحث يجريها بدون تشكيل (مثل ما حدث في تحديث `الجوامد.xlsx` بإضافة شَهْر، سَنَة، عَام، أُسْبُوع، إلخ).

### مبدأ 3: الـ seed لا lexicon
كل dataset جديدة تُعامل **seed مفتوح**، لا قائمة مغلقة. غياب الكلمة من الـ seed لا يعني أنها ليست من النوع.

### مبدأ 4: التوافق مع المصادر الخارجية
عند إضافة dataset، تُراعى المطابقة الجزئية مع:
- alasmaa (للأوزان والعوامل)
- salehan (للقطاعات السيمانتية، zarf_engine، mabni_registry)
- new_arabic_analyzer (للتطبيع والإعراب)

### مبدأ 5: التوثيق في `Computational_Linkage.md`
كل dataset جديدة تضاف، يُحدَّث ملف `Computational_Linkage.md` لتوثيق ربطها بالمعمار.

---

## خطة عمل مقترحة (محدَّثة — معظمها ربط لا بناء)

بعد مراجعة new_arabic_analyzer، الخطة أصبحت **ربط loaders جديدة** للبيانات المتوفرة، لا **بناء** بيانات من الصفر:

### المرحلة 1 — Loaders للبيانات الموجودة خارجيًا (أولوية عالية)

1. **`roots_loader.py`** — يحمّل `root_three_letters.csv` + `mishkat_word_root.csv`، يوفر `lookup_root(word)`.
2. **`pronouns_loader.py`** — يحمّل ملفات الضمائر الثلاثة، يصنف الضمير ويحدد المرجع.
3. **`prepositions_loader.py`** — يحمّل `preposition_meanings.json` ويدمج مع huruf.
4. **`demonstratives_loader.py`** — `demonstrative_pronouns.json` (53 إدخالًا).
5. **`relatives_loader.py`** — `relative_pronouns.json` (48 إدخالًا).
6. **`verb_names_loader.py`** — `verb_name.json` (57 إدخالًا).
7. **`naa_data_adapter.py`** — adapter موحَّد يجمع كل الـ loaders السابقة تحت واجهة واحدة.

### المرحلة 2 — تكامل مع pipeline

8. **توسيع `_step_word_classification`** — إضافة تصنيفات جديدة:
   - `pronoun_separate` / `pronoun_attached` / `pronoun_hidden`
   - `demonstrative` (مع البعد والجنس والعدد)
   - `relative`
   - `verb_name` (اسم فعل)
9. **توسيع segmenter integration** — استعمال قواعد بناء الفعل وتصريفه.

### المرحلة 3 — البناء الجزئي (للفجوات الفعلية)

10. **seed موسَّع للأعلام** — استخراج من mishkat + إضافة يدوية:
    - أنبياء قرآنيون (موسى، عيسى، إبراهيم، نوح، إلخ).
    - صحابة كبار.
    - مواضع قرآنية (مكة، المدينة، الطور، إلخ).
11. **WordNet عربي بسيط** — بنية أولية للمرادفات والأضداد (يحتاج بحث).

### المرحلة 4 — التوثيق المتراكم

12. **تحديث `Computational_Linkage.md`** بعد كل loader.
13. **كتابة `12_Huruf_System.md`** و`14_Pronoun_and_Reference_System.md` المحجوزين في `08_Future_Files_Map.md` استنادًا إلى البيانات الموجودة.
14. **اختبارات Sample 03/04/05** على نصوص أكثر تنوعًا (شعر، حوار، سرد).

### قاعدة منهجية حاكمة على الخطة

> **الربط أولًا، البناء آخرًا.** كل ساعة تُصرف على Loader جديد لبيانات موجودة تساوي أيامًا على بناء dataset من الصفر. new_arabic_analyzer وفّر طريقًا قصيرًا — استخدمه ولا تكرر العمل.
