# ١٨ — إِعلان دَستوريّ: طَبَقَة العَلاقات الأَوَّليَّة (Phase C)

> **التَّاريخ:** 2026-05-22  
> **النِّطاق:** جَلسات 14-23 (Phase C الأَوَّل + الثَّاني + اختبار + إِصلاحات)  
> **النَّوع:** إِعلان مُجَمَّد — أَيّ تَغيير في المُكَوِّنات أَدناه يَستَوجِب إِعلانًا جَديدًا.  
> **القاعِدَة:** كُلّ ادّعاء في هذا الإِعلان يَحمِل مَصدَره. الأَرقام بِلا مَصدَر مُؤَشَّرة `[بدون قياس]`.

---

## ١. ما تَمَّ إِنجازه

| المُكَوِّن | المَلَفّ | المَصدَر |
|---|---|---|
| Relation / EntityNode / RelationGraph (schema) | `clean_code/relation_schema.py` | جَلسة 14 — self-test ✓ |
| `relation_types.csv` (17 نَوع عَلاقَة) | `clean_code/data/contracts/rules/relation_types.csv` | جَلسة 14 |
| RelationExtractor (مَنّ i3rab → relations) | `clean_code/relation_extractor.py` | جَلسة 15 — self-test ✓ |
| `harf_jarr_relations.csv` (12 حَرف جَرّ) | `clean_code/data/contracts/rules/harf_jarr_relations.csv` | جَلسة 16 |
| `inter_clause_relations.csv` (18 نَوع عَلاقَة بَين الجُمَل) | `clean_code/data/contracts/rules/inter_clause_relations.csv` | جَلسة 18 |
| InterClauseExtractor | `clean_code/inter_clause_extractor.py` | جَلسة 18 — 5/6 self-test ✓ |
| `pronoun_clitics.csv` (13 ضَمير مُتَّصِل) | `clean_code/data/contracts/rules/pronoun_clitics.csv` | جَلسة 19 |
| PronounCliticResolver | `clean_code/pronoun_clitic_resolver.py` | جَلسة 19 — 3/3 self-test ✓ |
| TextGraphAssembler (نَصّ كامِل → graph واحِد) | `clean_code/text_graph_assembler.py` | جَلسة 20 — self-test ✓ |
| dashboard HTML (D3.js) | `clean_code/relation_dashboard.py` | جَلسة 21 — مُولَّد لِـ 1:1 + demo |
| Script قِياس end-to-end على الفاتحة + الإخلاص | `scripts/eval_end_to_end_surahs.py` | جَلسة 22 — `data/eval/end_to_end_surahs.json` |
| إِصلاح false-positive في PronounResolver (root-end) | (في الـ resolver نَفسِه) | جَلسة 23 |
| إِصلاح cross-clause anaphora fallback | (في TextGraphAssembler) | جَلسة 23 |

---

## ٢. القِياسات الفِعليَّة (لا ادّعاءات بِلا مَصدَر)

### ٢.١ RelationExtractor — 31 آية مُتَنَوِّعَة

> المَصدَر: `data/eval/m1_phase_c_relation_eval.json` — جَلسة 17

| المِقياس | القِيمَة |
|---|---:|
| الآيات | 31 |
| مَجموع الـ tokens | 191 |
| مَجموع العَلاقات | 94 |
| مُتَوسِّط/آية | 3.03 |
| مُتَوسِّط/token | 0.49 |
| تَغطيَة الـ tokens (token له ≥1 عَلاقَة) | 58.1% |

**تَوزيع أَسماء العَلاقات (الأَكثَر تَكرارًا):**

| العَلاقَة | العَدَد |
|---|---:|
| attribute_of | 30 |
| verb_in_clause | 29 |
| harf_jarr_of | 8 |
| from_source | 8 |
| topic_anchor | 7 |
| agent_of | 6 |
| patient_of | 3 |
| possessor_of | 2 |
| comment_of | 1 |

### ٢.٢ End-to-end — الفاتحة + الإخلاص

> المَصدَر: `data/eval/end_to_end_surahs.json` — جَلسة 22

| السُّورة | الآيات | tokens | clauses | intra | inter | ضَمائر | مَحلولَة |
|---|---:|---:|---:|---:|---:|---:|---:|
| الفاتحة | 7 | 29 | 9 | 13 | 2 | 7 | 1 (14%) |
| الإخلاص | 4 | 19 | 5 | 9 | 1 | 3 | 1 (33%) |

**مُلاحَظات:**
- `intra` = العَلاقات داخِل الجُمَل (RelationExtractor)
- `inter` = العَلاقات بَين الجُمَل (InterClauseExtractor)
- نِسبَة حَلّ الضَّمائر مُنخَفِضَة — مَوسومَة كَ open work (انظُر §٤).

---

## ٣. ما يَلتَزِم بِه هذا الإِعلان

١. **كُلّ Relation تَحمِل `source_of_claim` صَريح** — مِن أَيّ role في i3rab + أَيّ قاعِدَة في `relation_types.csv` (أَو `harf_jarr_relations.csv`).
٢. **kind ∈ {Certificate, Hypothesis, Zero}** — مَوروث مِن i3rab. مُعظَم العَلاقات Hypothesis لأنَّ i3rab نَفسه يَستَنتِج الدَّور positional.
٣. **alternatives مَحفوظة** — حَقل في كُلّ Relation (فارِغ حاليًّا في v1، يُستَخدَم في v2).
٤. **لا قَواعد inline** — كُلّ الـ mappings في CSVs (relation_types، harf_jarr_relations، inter_clause_relations، pronoun_clitics).
٥. **Pause marks ground-truth فَقَط** (مَوروثَة مِن إِعلان جَلسة 13).
٦. **لَفظ الجَلالة = لَفظ مُنفَرِد** — يَنتَقِل عَبر EntityNode كـ `is_singular_term=True`.

---

## ٤. ما لَم يُنجَز بَعد (open work)

| البَند | الحالة | السَّبَب |
|---|---|---|
| ground-truth يَدَويّ لِـ 50-100 آية مُصَنَّفَة بِعَلاقاتِها | open | يَحتاج وَقت بَشريّ + قَرار حَول الـ schema لِكُلّ نَوع |
| دِقَّة (precision/recall) لِـ RelationExtractor | open | يَتطَلَّب ground-truth |
| Cross-clause anaphora عَلى مَقياس | partial | الـ fallback في الـ assembler يَختار آخَر اسم — تَحتاج تَحَقُّق جِنس/عَدد |
| precision قَطع الجُمَل في و-/ف- (Task #202) | open | كَثير مِن الـ false-positives — حُلّها يَحتاج «اللاحِق فِعل؟» |
| نَقل JALALAH_FORMS إلى `singular_terms.csv` | open | inline في 3 مَلَفّات الآن |
| i3rab_engine/layer1.py inline letter-sets (~12) | open | تَحتاج refactor إلى CSVs (M.6 sequel) |

---

## ٥. ما لا يَدَّعيه هذا الإِعلان

١. **«دِقَّة %» لِأَيّ مُكَوِّن في Phase C** — لا ground-truth بَعد.
٢. **حَلّ كامِل لِلإِحالة** — حَلّ الضَّمائر بَسيط، يَختار آخِر اسم سابِق.
٣. **عَلاقات سَببيَّة عَميقَة** — حاليًّا «ف» = sequence_with_cause، لَكِنّ المُنطَلَق نَحويّ لا دَلاليّ.
٤. **اكتِمال طَبَقَة الـ Relations** — حَوالَى 60% (تَقدير): النَّحو الأَساسيّ مُغَطًّى، الإِحالة مَفتوحَة، السَّببيَّة العَميقَة مَفتوحَة.

---

## ٦. الكِتاب ا مَفتوح المُؤَجَّل (للجَلسات القادِمَة)

- بِناء ground-truth لِـ Phase C (50-100 آية) — يَحبس قِياسات الدِّقَّة
- تَحَقُّق جِنس/عَدد في الإِحالة (انتِظار 1)
- نَقل inline lists إلى CSVs (انتِظار 2 — Task #202 + JALALAH refactor)
- تَوسعة عَلاقات بَين الجُمَل لِتَتَعَدّى جُملتَين مُتَتاليَتَين (مَفتوح)
- M3 (Anaphora) — تَوسعة `pronoun_clitic_resolver` إلى ضَمائر مُنفَصِلَة + إِشارة + مَوصول
- M4 (Reasoning) — لا يَبدأ قَبل M3

---

## ٧. التَّوقيع الدَّستوريّ

هذا الإِعلان يَفي بِالشُّروط الأَربَعَة لِلـ Minimum Complete Theory:

| الشَّرط | كَيف يُحَقَّق |
|---|---|
| Source-of-Claim | كُلّ Relation تَحمِل اسم role + اسم قاعِدَة في CSV |
| Confidence-of-Claim | kind ∈ {Certificate, Hypothesis, Zero} في كُلّ مُخرَج |
| Alternatives-Preserved | حَقل `alternatives` في Relation و EntityNode |
| Reversible-Pipeline | كُلّ Relation تَحمِل سِلسِلَة المَصادِر — قابِل لِلتَّتَبُّع |

كُلّ نِسبَة وَرَدَت في §٢ مَصدَرُها مُحَدَّد. كُلّ ادّعاء «بِلا قِياس» مَوسوم في §٤.

— نِهايَة الإِعلان.
