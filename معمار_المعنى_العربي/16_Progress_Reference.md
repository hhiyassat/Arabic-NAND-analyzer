# ١٦ — مرجع الإنجاز التَّنفيذيّ

> **تاريخ القياس:** 2026-05-22  
> **القاعدة:** كل سَطر له مَصدر مُحدَّد. الأرقام بدون مصدر مُؤشَّرة `[بدون قياس]`.  
> **الغَرَض:** مَرجع للتطوير. بدون شَرح. لا يُحدَّث إلا بعد قياس فعلي.

> **تَصحيحان دَستوريّان — 2026-05-22 (جَلسة 13):**  
> (أ) **Pause marks ground-truth فَقَط** — سَحب ادّعاء M1.A السابق (Recall 99.9% / Precision 100%). كان self-fulfilling لأنّ علامات الوَقف القرآنيّة كانت تُمَرَّر كَ **مَدخَل** إلى الـ Segmenter، ثُمَّ قِيسَ ضِدَّها. الـ `clause_segmenter.py:v2` يَنزع pause marks قَبل أَيّ تَحليل ويَعتَمِد على قَواعد لُغَوِيّة فَقَط (تَرقيم + connectives + conditionals). الأَرقام الأَمينة في §8.  
> (ب) **لَفظ الجَلالة = لَفظ مُنفَرِد** — كانَ يُرجَع بِـ root="ءله" wazn="لفظ_الجلالة". الصَّحيح: اللَّه خارِج التَّصنيف (لا كُلِّيّ/جُزئيّ، لا جامِد/مُشتَقّ، لا جَذر، لا وَزن). الإصلاح في `root_pipeline.py` و `root_pipeline_types.py` و `root_by_alignment.py` و `i3rab_engine/layer1.py`.  
> (ج) **سكربت analyze_verse.py** — يُجري كُلّ التَّحلِيلات على آية واحِدة (نَصّ مُباشَر أَو رَقم 1:1، 2:285).

---

## ١. الأرضيّة (Phase A)

| المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---|
| Normalizer v2 | done | 100% | `clean_code/normalizer.py` + Task #52 |
| Segmenter v2 | done | 91.7% exact (70,969/77,411) | `SEGMENTER_OFFICIAL_DECLARATION.md` |
| Segmenter — Length 1 | done | 98.2% | same |
| Segmenter — Length 2 | done | 92.8% | same |
| Segmenter — Length 3 | done | 86.3% | same |
| Segmenter — Length 4 | partial | 56.0% | same |
| root_by_alignment | done | 64.6% (10,813 word) | `ROOT_BY_ALIGNMENT_OFFICIAL_DECLARATION.md` |
| root + segmenter downstream | done | top-1=78% top-3=82% | Task #85 |
| wazn_matcher v2.4 | frozen | top-1=59.3% top-3=64.6% | `archive/legacy_code/FREEZE_v2.4.md` |
| closed_class_detector | done | 100% | Task #130 + `clean_code/closed_class_detector.py` |
| jamid_detector | done | 100% | Task #18 + `clean_code/jamid_detector.py` |
| LivingRootContract | done | 100% | Task #157 + `clean_code/living_root_contract.py` |
| MASAQ.csv fixes | done | 249 cells | Tasks #91-95 + `data/masaq_data_errors/masaq_fix_audit.csv` |
| MASAQ structural errors | open | 74 remain | same |
| وزن فَعّ (مُضاعَف ثلاثي) | done | 109/5,000 = 2.2% من العَيِّنة القرآنيّة | جلسة 2 — قياس على MASAQ 2026-05-22 (الإصلاح كان قد تَمَّ في migration إلى root_by_alignment، Task #45 أُغلق) |
| وزن فَاعَل (Form III) | done | 91/5,000 = 1.8% من العَيِّنة القرآنيّة | جلسة 2 — نَفس المصدر، Task #46 أُغلق |
| Foundation: Wazn/Root v2 (overall) | open | [بدون قياس] | Task #54 |

---

## ٢. بُنية البُرهان (ProofObject + IntegrityContract + Minimum Complete)

| المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---|
| ProofObject dataclass | done | 100% | `clean_code/proof_object.py` + Task #140 |
| IntegrityContract / integrity_seal | done | 100% | `clean_code/integrity_seal.py` + Task #152 |
| root_pipeline returns ProofObject | done | 100% | Task #141 |
| Layer 1 returns ProofObject | done | 100% | Task #143 |
| Layer 2 returns ProofObject + blockers + alternatives | done | 100% | Task #144 |
| Layer 3 returns ProofObject + alternatives | done | 100% | Task #145 |
| FractalCoordinate | done | 100% | Task #146 |
| FractalCoordinate في Engine | done | 100% | Task #147 |
| فهرس fractal للقرآن | done | 100% | Task #148 |
| old_nand (hash كَدَرس مَعماري) | archived | 100% | Tasks #149-150 + `archive/old_nand/LESSON_v2.md` |

### نقل القواعد إلى ملفّات (Minimum Complete migration)

| المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---|
| M.A — بُنية contracts/rules/ + ProofContract base | done | 100% | Task #155 |
| M.1 — TanwinStrippingContract | done | 100% | Task #156 + `clean_code/tanwin_stripping_contract.py` + `data/contracts/rules/tanwin_stripping.csv` |
| M.2 — LivingRootContract | done | 100% | Task #157 |
| M.3 — translations CSV | done | 100% | Task #158 + `data/contracts/translations/*.csv` (5 ملفّات) |
| M.4 — refs.py overrides → contracts | done | 100% | Task #159 |
| M.5 — VerbalWaznContract (DSL pattern matcher) | done | 100% | Task #161 + `clean_code/verbal_wazn_contract.py` + `data/contracts/rules/verbal_wazn_rules.csv` |
| M.6 — MatcherHeuristicsContract | partial — documentation only | 60% (registry موجود؛ الـ algorithm الفعلي لا يزال في `root_by_alignment.py`) | Task #162 + `clean_code/matcher_heuristics_contract.py` + `data/contracts/rules/root_expansion_rules.csv` |
| M.7 — RoleRulesContract | done | 100% | Task #163 + `clean_code/role_rules_contract.py` + `data/contracts/rules/role_rules.csv` |
| M.8 — Constitutional linter | done | 100% (30 انتهاكًا متبقّيًا بَعد التَوسيم — كلّها canonical Unicode constants) | Task #160 + `scripts/constitutional_linter.py` |
| Closed-class data files (harf_jarr, harf_nasb, harf_jazm, harf_inna, ism_ishara, kana_family, verb_base_wazns) | done | 100% (7 ملفّات) | Task #142 + `data/contracts/*.csv` |
| ClosedClassExceptionsContract (exclude/exact_only) | done | 100% (3 صفوف: لله، رب، ال) | جلسة 1 — `data/contracts/closed_class_exceptions.csv` + `contracts_loader.load_closed_class_exceptions()` |

---

## ٣. دقّة i3rab (مَقيسة على 19,959 token من القرآن)

| المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---|
| Layer 1 — WordClass accuracy | partial | 87.0% (12,288/14,125 مُقَيَّم) | `data/eval/i3rab_engine_eval.csv` — قياس 2026-05-22 |
| Layer 1 — Certificate ratio | partial | 24.0% | same |
| Layer 1 — Hypothesis ratio | partial | 76.0% | same |
| Layer 1 — Zero ratio | done | 0% | same |
| Layer 2 — Case accuracy | partial | 82.8% (16,503/19,927) | same |
| Layer 2 — Certificate ratio | partial | 60.0% | same |
| Layer 2 — Hypothesis ratio | partial | 39.9% | same |
| Layer 3 — Role Certificate ratio | partial | 35.3% | same |
| Layer 3 — Role Hypothesis ratio | partial | 64.7% | same |

### أكبر أنماط الخَطأ (Layer 1 WordClass — للتطوير)

| نمط الخطأ | عدد الـ tokens | المصدر |
|---|---:|---|
| HARF → ISM_MABNI | 563 | `data/eval/i3rab_engine_eval.csv` |
| ISM_MUARAB → FIIL | 487 | same |
| JAMID → HARF | 421 | same |
| HARF → FIIL | 125 | same |
| ISM_MABNI → HARF | 103 | same |

### ثَغرات سُلوكيّة مُكتشَفة في smoke test

| الثغرة | الحالة | المصدر |
|---|---|---|
| لِلَّهِ يُصنَّف «حرف» (يَجب: HARF_JARR + JALALAH مُنفصلَين) | partial — لم يَعُد HARF (116 token)، لكنّ التَّقسيم الـ fused لم يُنفَّذ | جلسة 1 — 2026-05-22 + `data/contracts/closed_class_exceptions.csv` |
| رَبِّ يُصنَّف «حرف» (يَجب: ISM) | done — 128 token (100%) | جلسة 1 — exact_only mode على رُبَّ في exceptions |
| الْعَالَمِينَ يُصنَّف «فعل» (يَجب: ISM_MUARAB مجرور — نَعت/مُضاف إليه) | open | smoke test 2026-05-22 — مَشكلة في wazn matcher، خارج نِطاق جلسة 1 |

---

## ٤. الشَّحن (Shipping)

| المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---|
| arabic_tools.zip v2 | done | 70 ملفّ (3.7 MB) | `dist/arabic_tools.zip` — تاريخ 2026-05-22 |
| README بِفَصل Minimum Complete | done | 100% | `dist/arabic_tools/README.md` |
| morph.py + i3rab.py (dual-path) | done | 100% | smoke test 2026-05-22 |
| كل عقود contracts في الحزمة | done | 16 CSV | `dist/arabic_tools/clean_code/data/contracts/` |
| تَنظيف __pycache__ من zip | done | 100% | unzip verification |

---

## ٥. الـ G-Series (الفجوات البيانيّة)

| الفجوة | الوصف | الحالة | الإنجاز | المصدر |
|---|---|---|---:|---|
| G1 | شَبَكة المُرادفات/الأضداد | open | 0% | `Project_Status.md` |
| G2 | معاني الجذور الجامعة (لسان العرب) | open | 0% | same |
| G3 | تَعريفات الكلمات | open | 0% | same |
| G4 | الأعلام المُوسَّعة | done | 100% (193 علم) | Tasks #26+#30 + `data/extracted/aalam_from_masaq.csv` |
| G5 | Frame Semantics للأفعال | done | 100% (6,757 فعل) | Tasks #27+#31 + `data/extracted/verb_frames_from_quran_i3rab.csv` |
| G6 | كوربس الحديث | open | 0% | `Project_Status.md` |
| G7 | كوربس الشعر | open | 0% | same |
| G8 | Sentiment/Connotation | open | 0% | same |
| G9 | المعاني الحضاريّة | open | 0% | same |
| G10 | جداول التَّصريف | partial | 50% (الماضي فقط، 38,753 صيغة) | Tasks #29+#33 + `data/extracted/verb_conjugations_past.csv` |
| G11 | الحقول الدلاليّة | partial | ~40% (8 حقول من ~20) | Tasks #28+#32 + `data/extracted/semantic_fields/*.json` |
| G12 | الأعداد الكاملة | open | 0% | `Project_Status.md` |
| G13-G17 | تحسينات صغيرة | open | 0% | same |

---

## ٦. الأسئلة الدستوريّة (Q-Series)

| السؤال | الموضوع | الحالة | المصدر |
|---|---|---|---|
| Q1 | مَركَز النظام | resolved | `10_Stabilization_Tracker.md` — Layer-Centric |
| Q2 | طبيعة State | resolved | `Q2_State_Test_From_Huruf.md` + `Q2_State_Test_From_Entities.md` — 5 أنماط |
| Q3 | موقع اللُّغة من الإدراك | open | `09_Open_Questions.md` |
| Q4 | منع التضخُّم | open | `09_Open_Questions.md` (مُعَوَّض جُزئيًّا بإعلان #21) |

---

## ٧. الفُروق الجوهريّة الستّة

| الفرق | الحالة | المصدر |
|---|---|---|
| Entity vs State | resolved | Q1 + Q2 — `10_Stabilization_Tracker.md` |
| Identity vs Continuity | resolved | `Distinction_Identity_vs_Continuity.md` |
| Event vs Transformation | open | `09_Open_Questions.md` — يَحبس Phase D |
| Relation vs Attribute | resolved | `Distinction_Relation_vs_Attribute.md` — جَلسة 8، اختُبر على 30 جملة — Phase C مَفتوحة |
| Meaning vs Interpretation | open | `09_Open_Questions.md` — يَحبس Phase F |
| Context vs Environment | open | `09_Open_Questions.md` — يَحبس Phase E |

---

## ٨. الميل-ستونات (M-Series)

| الميل-ستون | المُكوّن | الحالة | الإنجاز | المصدر |
|---|---|---|---:|---|
| M1.A | Multi-clause Segmenter | done بِنيويًّا · مَقيس بِأَمانة | **Recall=63.5% / Precision-strict=13.5% / Precision-vs-anti=83.5% / F1-vs-anti=72.1% على 6,236 آية**. القِياس السابق (99.9%/100%) كان self-fulfilling لأنّ علامات الوَقف كانت مَدخَلًا. تَمَّ تَصحيحه دستوريًّا: pause marks تُستَخدَم كـ ground-truth فَقَط. | `clean_code/clause_segmenter.py:v2` (26 قاعدة rule-based، صِفر pause marks) + `scripts/eval_segmenter_honest.py` + `data/eval/m1a_pause_eval_honest.json` |
| M1.B | Speech Act Detector | done | 100% (تَكامل) / غير مَقيس على ground-truth | جلسة 5-6 — `clean_code/speech_act_detector.py` + 40 قاعدة CSV — self-test 9/9 |
| M1.C | Negation Scope | done | 100% (تَكامل) | جلسة 9 — `clean_code/negation_detector.py` + 10 قَواعد — self-test 6/6 |
| M1.D | Modal Detector | done | 100% (تَكامل) | جلسة 10 — `clean_code/modal_detector.py` + 20 قاعدة — self-test 7/7 |
| M1Pipeline | Orchestrator + ClauseAnalysis + M1Result | done | 100% | جلسة 11 — `clean_code/m1_pipeline.py` |
| M1 — اختبار على القرآن | عَيِّنة 22 آية من 4 سور | done — مَحفوظ | لا ground-truth مُصنَّفة بَعد | جلسة 12 — `data/eval/m1_eval_short_surahs.json` |
| M1.A — قِياس أَمين بَعد التَّصحيح | 6,236 آية بِنَزع pause marks | done | Recall 63.5% / Precision-strict 13.5% / Precision-vs-anti 83.5% / F1-vs-anti 72.1% | جلسة 13 — `scripts/eval_segmenter_honest.py` + `data/eval/m1a_pause_eval_honest.json` |
| تَصحيح أُنطولوجيّ — لَفظ الجَلالة | اللَّه = لَفظ مُنفَرِد | done | status=singular_term · root=— · wazn=— · is_singular_term=True | جلسة 13 — `clean_code/root_pipeline.py` + `root_pipeline_types.py` + `root_by_alignment.py` + `i3rab_engine/layer1.py` |
| analyze_verse.py — تَحليل آية شامِل | RootPipeline + M1Pipeline + ayah lookup | done | يَقبَل نَصّ أَو رَقم آية (1:1، 2:285) — يُخرِج تَقريرًا عَرَبيًّا أَو JSON | جلسة 13 — `clean_code/analyze_verse.py` |
| **Phase C الأَوَّل** — RelationSchema + Extractor + harf jarr | جَلسات 14-17 | done | 94 عَلاقَة على 31 آية، تَغطيَة 58.1% | `clean_code/relation_schema.py` + `relation_extractor.py` + 3 CSVs + `data/eval/m1_phase_c_relation_eval.json` |
| **Phase C الثَّاني** — inter-clause + إِحالَة + dashboard | جَلسات 18-21 | done | InterClauseExtractor 5/6 self-test، PronounResolver 3/3 self-test، dashboard HTML مُولَّد | `clean_code/inter_clause_extractor.py` + `pronoun_clitic_resolver.py` + `text_graph_assembler.py` + `relation_dashboard.py` |
| **end-to-end** — الفاتحة + الإخلاص | جَلسة 22 | done | الفاتحة: 13 intra + 2 inter + 7 ضَمائر؛ الإخلاص: 9 intra + 1 inter + 3 ضَمائر | `scripts/eval_end_to_end_surahs.py` + `data/eval/end_to_end_surahs.json` |
| إِصلاحات Phase C — pronoun false-positives + cross-clause | جَلسة 23 | done | root-end check + cross_clause_fallback في الـ assembler | تَحديث `pronoun_clitic_resolver.py` + `text_graph_assembler.py` |
| **إِعلان دَستوريّ Phase C** | جَلسة 24 | done | `معمار_المعنى_العربي/18_Layer3_Relations_Declaration.md` | يَفي بِشُروط MC الأَربَعَة |
| M2 | الحَوكمة (Source/Confidence/Alternatives/Reversible) | done | 100% بِنيويًّا | ProofObject + IntegrityContract — Tasks #140-152 |
| M3 | Anaphora Resolution | not started | 0% | `12_Project_Scope_Declaration.md` §5 — معيار ≥70% |
| M4 | الاستدلال على الكَمّيّات | not started | 0% | same — معيار ≥95% |
| Tier 3 — Syntactic_Role + Phrase في MEEMAR | open | 0% | Task #100 — مُرتَبط بـ M1.A |

---

## ٩. الطبقات الدستوريّة الثَّمان

| الطبقة | الاسم | الحالة | الإنجاز | المصدر |
|---|---|---|---:|---|
| 0 | Sign | done | 100% | `clean_code/normalizer.py` + `clean_code/segmenter.py` |
| 1 | Perception | partial | ~70% | Layer 1/2/3 من i3rab — لا يوجد مُكوّن «انتباه» مَوسوم |
| 2 | Conceptual / Probability | partial | ~85% | M1 رفعها — ProofObject + 4 detectors + 96 قاعدة CSV |
| 3 | Relations | **done بِنيويًّا** | ~60% | Phase C الأَوَّل + الثَّاني تَمَّ في جَلسات 14-23 · 17 نَوع عَلاقَة + 12 حَرف جَرّ + 18 inter-clause + 13 ضَمير — `18_Layer3_Relations_Declaration.md` |
| 4 | Resolution | not started | 0% | يَحبس على Q3 + Phase C |
| 5 | Semantic | not started | 0% | يَحبس على Meaning vs Interpretation |
| 6 | Event / Transformation | not started | 0% | يَحبس على Event vs Transformation |
| 7 | Reasoning | not started | 0% | يَحبس على كل ما سَبَق |

---

## ١٠. الـ Pipeline ذو 14 خطوة (من `Project_Status.md` §5)

| الخطوة | الحالة | الإنجاز | المصدر |
|---|---|---:|---|
| Step −2 — Diacritization (GPT52) | done | 100% | Task #35 |
| Step −1 — Normalize | done | 100% | `clean_code/normalizer.py` |
| Step 0a — Segmenter | done | 91.7% | §1 |
| Step 0b — analyze_word (Wazn + Root) | done | 64.6%-78% | §1 |
| Step 1 — Meaning Flow | partial | [بدون قياس] | `pipeline.py` |
| Step 2 — Layer-Centric Decomposition | partial | [بدون قياس] | same |
| Step 3 — Huruf dataset matching | done | 100% | `huruf_loader.py` |
| Step 3.5 — Word classification | done | 87.0% | §3 |
| Step 3.55 — Semantic Field membership | partial | ~40% (G11) | §5 |
| Step 3.6 — Frame Semantics | done | 100% data (G5) | §5 |
| Step 3.65 — Verb suffix classification | done | 100% (10 لواحق) | Tasks #36-40 |
| Step 3.7 — Past-tense conjugation match | partial | 50% (G10) | §5 |
| Step 4 — Five state patterns (Q2) | done | 100% theoretically | `Q2_State_Test_*.md` |
| Step 5 — Resolution & probability | not started | 0% | Phase E |
| Step 6 — Verdict | partial | [بدون قياس] | `pipeline.py` |

---

## ١١. تقييم الـ Roadmap (الملف 15) نفسه

| البند | الحالة | المصدر |
|---|---|---|
| §2 «أين نَقف» — أرقام مَقيسة | معدَّل بعد قياس 2026-05-22 | هذا الملفّ §3 + §9 |
| §4 تقدير «8-10 جَلسات لـ M1» | claim بدون مصدر | `M1_Plan_Recorded.md` نفسه يَقول «2-3 أسابيع لكلّ مكوّن» — تَقدير بَشريّ |
| §8 الجَدول الشَّهري — تَقسيم 4 جَلسات/شَهر | claim بدون مصدر | تَقدير |
| §10 معيار 85% Speech Act | مَأخوذ من الدستور | `12_Project_Scope_Declaration.md` §5 |
| §10 معيار 70% Anaphora | مَأخوذ من الدستور | same |
| §10 معيار 80% Causal Relations | مَأخوذ من الدستور | same |

---

## ١٢. الالتزامات الدستوريّة الأربعة (إعلان #21)

| الالتزام | الحالة في الكود | المصدر |
|---|---|---|
| Source-of-Claim | done — كل ProofObject يَحمل `source_of_claim` | `clean_code/proof_object.py` |
| Confidence-of-Claim | partial — kind ∈ {Certificate, Hypothesis, Zero}؛ لا يوجد بَعد scalar [0,1] | same |
| Alternatives-Preserved | done — حقل `alternatives` في ProofObject | same + Layer 2/3 يَملآنه |
| Reversible-Pipeline | not implemented — لا يوجد audit trail قابل للنَّقض من واجهة | لا مَلفّ |

---

## ١٣. مُلَخَّص الإنجاز الكُلّي (مع مصدر)

| المُحور | الإنجاز التَّقريبيّ | كيفيّة الاحتساب |
|---|---:|---|
| Phase A — Foundation | ~92% | متوسّط مُرَجَّح: Segmenter 91.7%، Wazn 64.6%، WC 87.0%، Case 82.8% — وفجوات #45+#46+المعالم الثلاث |
| ProofObject + IntegrityContract | 100% | كل 8 مُكوّنات في §2 done |
| Minimum Complete migration (M.A-M.8) | ~94% | 7/9 done + M.6 60% + linter 30 انتهاكًا مَوسومًا |
| Phase B — M1 | ~75% بِنيويًّا | M1.A done + مَقيس بِأَمانة (Recall 63.5% / Precision-vs-anti 83.5% / F1-vs-anti 72.1%، §8) — القِياس السابق 99.9%/100% كان self-fulfilling وتَمَّ سَحبُه · M1.B/C/D done بِنيويًّا (self-tests فَقَط، لا ground-truth) · Pipeline done · النَّاقِص: تَوسعة قَواعِد الـ Segmenter لِرَفع Recall + قياس B/C/D على عَيِّنة مُصنَّفة يَدويًّا |
| Phase C → G | 0% | لم يَبدأ — Phase C جاهزة للبَدء (Relation vs Attribute حُسم، §7) |
| الفُروق الستّة | 33% (2/6) | Entity-State + Identity-Continuity فقط |
| الأسئلة الأربع | 50% (2/4) | Q1 + Q2 فقط |
| G-Series البيانات | ~21% (3.6/17) | G4+G5 done، G10+G11 partial |
| الطبقات الثَّمان | ~26% | متوسّط مُرَجَّح: 100%, 70%, 40%, 0%, 0%, 0%, 0%, 0% |
| الالتزامات الدستوريّة الأربعة | 75% (3/4 بِالكامل أو جُزئيّ) | Reversibility ناقص |

> **النِّسبة الكلّيّة للمشروع** = `[بدون قياس قابل]` — المشروع متعدّد الطبقات لا يُختزَل في رَقَم واحد. كل صَفّ أعلاه يَحمل مَصدره. أيّ ادّعاء «نِسبة كلّيّة» بدون تَحديد المُحور يُعتبَر انتهاكًا لِـ Minimum Complete.
