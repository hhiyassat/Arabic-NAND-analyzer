# تَقرير اليَقَظَة — جَلسات 14-25 (Phase C كامِلَة + إِغلاق)

> **التَّاريخ:** 2026-05-22  
> **النَّوع:** تَقرير شامِل لِلجَلسات الَّتي نُفِّذَت في غِيابِك  
> **القاعِدَة:** كُلّ سَطر له مَصدَر. لا ادّعاءات بِلا قِياس.

---

## ١. ما تَمَّ — 12 جَلسة في تَسَلسُل

| الجَلسة | المُكَوِّن | المُخرَج | الِاختبار |
|---|---|---|---|
| 14 | RelationSchema + EntityNode + RelationGraph | `clean_code/relation_schema.py` + `relation_types.csv` (17 نَوع) | self-test ✓ 3 nodes، 2 relations |
| 15 | RelationExtractor فَوق i3rab | `clean_code/relation_extractor.py` | self-test ✓ على 5 جُمَل |
| 16 | حُروف الجَرّ كَ relation operators | `harf_jarr_relations.csv` (12 حَرف) | direction_to + in_location يَفعَلان |
| 17 | اختبار شامِل + قِياس بِنيويّ | `data/eval/m1_phase_c_relation_eval.json` | 31 آية، 94 علاقَة، تَغطيَة 58.1% |
| 18 | InterClauseExtractor + `inter_clause_relations.csv` | `clean_code/inter_clause_extractor.py` (18 نَوع) | self-test ✓ 5/6 |
| 19 | PronounCliticResolver + `pronoun_clitics.csv` | `clean_code/pronoun_clitic_resolver.py` (13 ضَمير) | self-test ✓ 3/3 |
| 20 | TextGraphAssembler | `clean_code/text_graph_assembler.py` | self-test ✓ نَصّ مِن جُملتَين |
| 21 | dashboard HTML تَفاعُليّ (D3.js) | `clean_code/relation_dashboard.py` | مُولَّد لِـ 1:1 و demo |
| 22 | end-to-end على الفاتحة + الإخلاص | `scripts/eval_end_to_end_surahs.py` | `data/eval/end_to_end_surahs.json` |
| 23 | إِصلاحات: root-end false-positives + cross-clause anaphora | تَحديث resolver + assembler | re-eval ✓ |
| 24 | إِعلان دَستوريّ | `معمار_المعنى_العربي/18_Layer3_Relations_Declaration.md` | يَفي بِشُروط MC الأَربَعَة |
| 25 | حُزمَة v2 | `dist/arabic_tools_v2_2026-05-22.zip` (3.6 MB) | smoke test على /tmp ✓ |

---

## ٢. الأَرقام الفِعليَّة (مَع مَصدَر)

### ٢.١ RelationExtractor على 31 آية مُتَنَوِّعَة
> المَصدَر: `data/eval/m1_phase_c_relation_eval.json`

| | |
|---|---:|
| tokens | 191 |
| relations | 94 |
| مُتَوسِّط/آية | 3.03 |
| تَغطيَة tokens | 58.1% |

**أَكثَر العَلاقات تَكرارًا:** attribute_of (30) · verb_in_clause (29) · harf_jarr_of (8) · from_source (8) · topic_anchor (7) · agent_of (6) · patient_of (3) · possessor_of (2) · comment_of (1).

### ٢.٢ end-to-end الفاتحة + الإخلاص
> المَصدَر: `data/eval/end_to_end_surahs.json`

| السُّورَة | tokens | clauses | intra | inter | ضَمائر | مَحلولَة |
|---|---:|---:|---:|---:|---:|---:|
| الفاتحة (7 آيات) | 29 | 9 | 13 | 2 | 7 | 1 (14%) |
| الإخلاص (4 آيات) | 19 | 5 | 9 | 1 | 3 | 1 (33%) |

### ٢.٣ ClauseSegmenter rule-based (مَوروث مِن جَلسة 13)
> المَصدَر: `data/eval/m1a_pause_eval_honest.json`

| | |
|---|---:|
| الآيات | 6,236 |
| Recall على pause marks الإيجابيَّة | 63.5% |
| Precision-vs-anti | 83.5% |
| F1-vs-anti | 72.1% |

---

## ٣. ما لا يَدَّعيه هذا التَّقرير

- **«دِقَّة %» لِأَيّ مُكَوِّن في Phase C** — لا ground-truth بَعد.
- **حَلّ كامِل لِلإِحالة** — حَلّ الضَّمائر بَسيط: داخِل الجُملة → أَقرَب اسم سابِق؛ خارِجها → آخِر اسم في الجُملة السابِقَة. لا تَحَقُّق جِنس/عَدد.
- **اكتِمال طَبَقَة الـ Relations** — تَقدير ~60%: النَّحو الأَساسيّ مُغَطًّى، الإِحالة والسَّببيَّة العَميقَة مَفتوحَتان.

---

## ٤. الِانتِهاكات الدَّستوريَّة الَّتي بَقِيَت (مَوسومَة)

| الِانتِهاك | المَوضِع | الخُطورَة |
|---|---|---|
| `JALALAH_FORMS` inline في 3 مَلَفّات | `root_pipeline.py:59`، `root_by_alignment.py:504`، `i3rab_engine/layer1.py:339` | يَجِب نَقلُه إلى `data/contracts/lists/singular_terms.csv` |
| ~12 قائِمَة حُروف inline في layer1 | `i3rab_engine/layer1.py` | refactor (M.6 sequel) |
| Normalizer rules كَدَوالّ Python بَدَل CSV | `normalizer.py` 13 قاعِدَة | تَحويل لاحِق |
| Precision قَطع الجُمَل في و-/ف- (Task #202) | `clause_segmenter.py` | يَحتاج قَيد «اللاحِق فِعل؟» |

---

## ٥. الحُزمَة v2

**المَلَفّ:** `/Users/husseinhiyassat/fractal/hussein/dist/arabic_tools_v2_2026-05-22.zip` (3.6 MB)

**ما الجَديد فَوق v1:**
- 7 مَلَفّات Python جَديدة (relation_schema، relation_extractor، inter_clause_extractor، pronoun_clitic_resolver، text_graph_assembler، relation_dashboard، analyze_verse)
- 4 ملفّات contracts جَديدة (relation_types، harf_jarr_relations، inter_clause_relations، pronoun_clitics)
- تَصحيح dialect: pause marks مَنزوعَة قَبل التَّحليل، لَفظ الجَلالة singular_term
- README مُحَدَّث بِفَصل Phase C

**Smoke test:** فُكَّت في `/tmp/verify_v2`، شُغِّل RelationExtractor + TextGraphAssembler — كِلاهُما يَعمَل ✓.

---

## ٦. مَلَفّات أَساسيَّة لِلمُراجَعَة

| المَلَفّ | لِماذا |
|---|---|
| `معمار_المعنى_العربي/18_Layer3_Relations_Declaration.md` | إِعلان دَستوريّ كامِل Phase C |
| `معمار_المعنى_العربي/16_Progress_Reference.md` | المَرجِع التَّنفيذيّ — يَعكس الآن جَلسات 13-25 |
| `data/eval/m1_phase_c_relation_eval.json` | قِياس 31 آية |
| `data/eval/end_to_end_surahs.json` | قِياس الفاتحة + الإخلاص |
| `clean_code/relation_dashboard.py` | لِتَوليد dashboard HTML لِأَيّ آية |
| `outputs/dashboard_demo.html` | عَيِّنَة dashboard مُولَّدَة |
| `outputs/dashboard_1_1.html` | dashboard الفاتحة 1:1 |
| `dist/arabic_tools_v2_2026-05-22.zip` | الحُزمَة الجَديدة |

---

## ٧. الخُطوات التَّالِيَة المُقتَرَحَة

١. **ground-truth يَدَويّ** لِـ 50-100 آية مُصَنَّفَة بِعَلاقاتِها → يَفتَح قِياسات الدِّقَّة الحَقيقيَّة.
٢. **نَقل `JALALAH_FORMS` إلى `data/contracts/lists/singular_terms.csv`** — إِغلاق انتِهاك دَستوريّ سَهل.
٣. **Precision boost لِقَطع الجُمَل في و-/ف-** (Task #202) — رَفع F1 فَوق 72.1%.
٤. **تَحَقُّق جِنس/عَدد في الإِحالة** — رَفع نِسبَة حَلّ الضَّمائر فَوق 14-33%.
٥. **Phase D (Resolution + Probability)** أَو **M3 (Anaphora أَعمَق)** — حَسَب الأَولَوِيَّة.

---

تُصبِح على خَير. كُلّ الكود مَكتوب، كُلّ التَّحديثات في الوَثائق، كُلّ الِاختبارات شُغِّلَت، والحُزمَة جاهِزَة.
