# حَوكَمَة مَعمار المَعنى العَرَبيّ

> **النَّوع:** وَثيقَة حَوكَمَة وَ تَوحيد المُسَمَّيات
> **التَّاريخ:** 2026-05-24
> **الحالَة:** ★ مَرجِع وَحيد لِلتَّسميات (single source of truth)
> **المُكَمِّلات:** `CONSTITUTION.md` (القَواعِد) + `RULES.md` (التَّفاصيل اللُّغَويَّة)

---

## القاعِدَة الذَّهَبيَّة

> **اسم واحِد لِكُلّ مَفهوم. رَقم واحِد لِكُلّ طَبَقَة. مَصدَر واحِد لِكُلّ تَعريف.**

كُلّ مَلَفّ، CSV، وَ مَخرَج يَجِب أَن يَستَخدِم المُسَمَّيات المُعتَمَدَة هُنا. أَيّ اسم بَديل (مَثَلًا "Phase C" بَدَل "L4") يُعتَبَر مَخالَفَة دُستوريَّة.

---

# الفَصل ① — الطَّبَقات الـ9 (L0 → L8)

سَلسَلَة هَرَميَّة. كُلّ طَبَقَة تَأخُذ مَخرَج الَّتي قَبلها وَ تُنتِج لِالَّتي بَعدها.

| الرَّمز | الِاسم العَرَبيّ | الِاسم اللاتينيّ | المُدخَل | المُخرَج | المِلَفّ الرَّئيس | المَجال |
|---|---|---|---|---|---|---|
| **L0** | التَّطبيع | Normalization | نَصّ خام | نَصّ NFC مُوَحَّد | `normalizer.py` | Foundation |
| **L1** | التَّقطيع | Segmentation | كَلِمَة | بَوادِئ + جَذع + لَواحِق | `segmenter.py` | Foundation |
| **L2** | الصَّرف | Morphology | جَذع | جَذر + وَزن + نَوع | `root_pipeline.py` | Foundation |
| **L3** | الإِعراب | I3rab | جُملَة | tokens مَع word_class + case + role | `i3rab_engine/engine.py` | Syntax |
| **L4** | العَلاقات | Relations | sentence + i3rab | RelationGraph (17 نَوع) | `relation_extractor.py` | Syntax |
| **L5** | الأَحداث | Events | RelationGraph | EventGraph + Transformations | `event_extractor.py` | Semantics |
| **L6** | التَّعيين | Resolution | sentence + events + context | ResolutionGraph (6 أَنواع) | `resolution_engine.py` | Semantics |
| **L7** | شَبَكَة المَعنى | MeaningGraph | كُلّ ما سَبَق | MeaningGraph (عُقَد + رَوابِط + تَناقُضات) | `meaning_assembler.py` | Semantics |
| **L8** | الِاستِدلال | Reasoning | MeaningGraph + سُؤال | Answer (Certificate/Hypothesis/Zero) | `reasoning_engine.py` | Pragmatics |

**خَريطَة قَديم → جَديد:**

| الِاسم القَديم | الِاسم الجَديد |
|---|---|
| Phase A (Morph) | L0 + L1 + L2 |
| Layer 1 (i3rab WordClass) | جُزء مِن L3 |
| Layer 2 (i3rab Case) | جُزء مِن L3 |
| Layer 3 (i3rab Role) | جُزء مِن L3 |
| Phase C | L4 |
| Phase D | L5 |
| Phase E | L6 |
| Phase F | L7 |
| Phase G | L8 |

---

# الفَصل ② — المَعارِف المُلحَقَة (KB.*)

قَواعِد مَعرِفيَّة لَيسَت طَبَقات لَكِنَّها مَصادِر لِجَميع الطَّبَقات.

| الرَّمز | الِاسم العَرَبيّ | المَصدَر | الحَجم |
|---|---|---|---|
| **KB.SAM** | مَعاني السَّامَرّائيّ | 4 مُجَلَّدات | 243 قاعِدَة، 23 CSV |
| **KB.ROOTS** | الجُذور المُحَقَّقَة | audited_roots.csv | 1,340 جَذر |
| **KB.WAZN** | الأَوزان | awzan.csv | 1,905 وَزن |
| **KB.FRAMES** | إِطارات الأَفعال | verb_frames | 6,757 إِطار |
| **KB.OPS** | العَوامِل المِئَة | operators_catalog.csv | 102 عامِل |
| **KB.QURAN** | نَصّ القُرآن المُشَكَّل | quran-uthmani-with-pause-mark.txt | 6,236 آية |

---

# الفَصل ③ — أَنواع البُرهان (Proof Kinds)

كُلّ ادِّعاء في النِّظام يَنتَمي لِواحِد مِن ثَلاثَة فَقَط:

| الرَّمز | المُسَمَّى العَرَبيّ | المُسَمَّى اللاتينيّ | الدَّلالَة | الأَيقونَة |
|---|---|---|---|---|
| **C** | يَقين | Certificate | شَواهِد كامِلَة، لا غُموض | ✓ |
| **H** | فَرضيَّة | Hypothesis | شَواهِد كافيَة لَكِنّ بَدائِل مُمكِنَة | ? |
| **Z** | صِفر | Zero | لا شَواهِد — نَفي صَريح | ✗ |

**سياسات الأَيقونات في العَرض:**
- ✅ يُستَخدَم لِسُؤال داخِل النِّطاق (in_scope)
- 🚫 يُستَخدَم لِسُؤال خارِج النِّطاق (out_of_scope)
- ⊕ يُستَخدَم لِعُقدَة ضِمنيَّة (implicit)

---

# الفَصل ④ — العَلاقات الـ17 (L4)

| الرَّمز | الِاسم العَرَبيّ | English | المَصدَر |
|---|---|---|---|
| 1 | agent_of | الفاعِل | i3rab/فاعِل |
| 2 | patient_of | المَفعول | i3rab/مفعول به |
| 3 | patient2_of | المَفعول الثَّاني | post_detect |
| 4 | possessor_of | المُضاف إِليه | i3rab/مضاف إِليه |
| 5 | attribute_of | النَّعت | i3rab/نعت |
| 6 | topic_of / comment_of | المُبتَدَأ / الخَبَر | i3rab |
| 7 | inna_topic_of / inna_comment_of | اسم/خَبَر إِنّ | i3rab |
| 8 | kana_topic_of / kana_comment_of | اسم/خَبَر كانَ | post_detect |
| 9 | harf_jarr_of | حَرف الجَرّ | i3rab |
| 10 | in_location | ظَرف مَكان | harf_jarr_relations: في |
| 11 | on_surface | عَلى سَطح | harf_jarr_relations: على |
| 12 | direction_to | اتِّجاه | harf_jarr_relations: إلى |
| 13 | from_source | مَصدَر | harf_jarr_relations: من |
| 14 | with_instrument | بِأَداة | harf_jarr_relations: ب |
| 15 | coordinate_of | المَعطوف | i3rab/معطوف |
| 16 | substitute_of | البَدَل | post_detect |
| 17 | vocative_of | المُنادى | i3rab/منادى |

---

# الفَصل ⑤ — أَنواع التَّعيين الـ6 (L6)

| الرَّمز | الِاسم | الوَصف |
|---|---|---|
| 1 | anaphora | الإِحالَة الخَلفيَّة (هو، هي، هم) |
| 2 | deixis | الإِشارَة (هذا، تلك) |
| 3 | relative | المَوصول (الَّذي، الَّتي) |
| 4 | bridging | الإِشارَة الضِّمنيَّة (ضَمير الشَّأن) |
| 5 | identity_transformation | تَتَبُّع الكِيان عَبر التَّحَوُّل |
| 6 | detached_pronoun | الضَّمائر المُنفَصِلَة (إِيَّاكَ، أَنتَ، نَحنُ) |

---

# الفَصل ⑥ — سياسَة العَرض (Display Policy)

كُلّ مَخرَج CLI أَو tag في وَثيقَة يَجِب أَن يَتبَع:

## ⑥.1 رَأس الطَّبَقَة
```
{emoji} L{n} — {الِاسم العَرَبيّ}
─────────────────────────────
```
أَمثِلَة:
- 🔤 L1 — التَّقطيع
- 🔍 L3 — الإِعراب
- 🔗 L4 — العَلاقات
- ⚡ L5 — الأَحداث
- 🎯 L6 — التَّعيين
- 🧠 L7 — شَبَكَة المَعنى
- ❓ L8 — الِاستِدلال

## ⑥.2 تَسمية العَلاقات
- في الكود: snake_case lowercase (`agent_of`)
- في العَرض: الِاسم العَرَبيّ (الفاعِل)
- في الـ CSV: snake_case

## ⑥.3 أَيقونات الـ Proof
- ✓ Certificate
- ? Hypothesis
- ✗ Zero
- ⊕ Implicit node
- ✅ In-scope question
- 🚫 Out-of-scope question

---

# الفَصل ⑦ — حَوكَمَة التَّعديل (Change Governance)

## ⑦.1 إِضافَة طَبَقَة جَديدَة (L9+)

يَتَطَلَّب:
1. تَوثيق المُدخَل/المُخرَج في هذه الوَثيقَة
2. إِنشاء ملَفّ Python بِاسم `{action}_{type}.py`
3. إِنشاء schema dataclass في `{action}_schema.py`
4. ProofObject لِكُلّ ادِّعاء
5. اختبار end-to-end عَلى الفاتِحَة قَبل الدَّمج

## ⑦.2 إِضافَة عَلاقَة جَديدَة (Relation #18+)

يَتَطَلَّب:
1. تَحديث `data/contracts/rules/relation_types.csv`
2. تَحديث جَدوَل العَلاقات في هذه الوَثيقَة
3. تَحديث `meaning_assembler.PASSTHROUGH` whitelist
4. اختبار عَلى ≥3 جُمَل تَحوي النَّمَط

## ⑦.3 إِضافَة CSV قاعِدَة جَديدَة

يَتَطَلَّب:
1. وَضعها تَحت `data/contracts/{lists|rules|maani}/`
2. أَوَّل صَفّ = headers صَريحَة
3. التَّحميل عَبر `contracts_loader` (لا قِراءَة مُباشِرَة)
4. caching عَبر module-level singleton

## ⑦.4 سياسَة MC (Minimum Complete)

- ❌ لا inline lists في كود Python
- ❌ لا if/elif لِقَواعِد لُغَويَّة (يَنبَغي CSV)
- ❌ لا ادِّعاء بِلا source_of_claim
- ✅ كُلّ تَحليل = ProofObject مَع contract + kind + blockers

---

# الفَصل ⑧ — التَّتَبُّع (Provenance)

كُلّ ادِّعاء يَنبَغي أَن يَحوي:

```python
source_of_claim = f"{contract_name}: {input_summary} → {output_summary} [{csv_file}:{row}]"
```

أَمثِلَة جَيِّدَة:
- `role:فاعل + last_verb_idx:0 + relation_types:agent_of`
- `post_detect: detached_pronoun(2/singular/masculine) preceding FIIL → patient_of [detached_pronouns.csv]`
- `implicit_agent: iv_prefix=ن + suffix=— + person=1/number=plural/gender=common [implicit_agents.csv]`

---

# الفَصل ⑨ — الِاختِبار المُعتَمَد (Canonical Tests)

| المُستَوى | الأَمر | ما يَختَبِر |
|---|---|---|
| آيَة واحِدَة | `python3 analyze_verse_v3.py --verse 1:5 --all` | كُلّ الـ9 طَبَقات |
| سُورَة | `python3 sweep_quran_all.py --surah 1` | اتِّساق + إِحصاء |
| القُرآن | `python3 sweep_quran_all.py --save-jsonl results.jsonl --resume-from results.jsonl` | إِجماليّ |
| تَقرير | `python3 sweep_quran_all.py --aggregate-jsonl results.jsonl` | تَجميع |
| جُملَة حُرَّة | `python3 analyze_verse_v3.py "نَصّ مُشَكَّل" --all` | تَجريب |

---

# الفَصل ⑩ — الِامتِثال (Compliance Checklist)

قَبل دَمج أَيّ تَغيير، أَجِب «نَعَم» عَلى كُلّ هذه:

- [ ] هَل أَستَخدِم رَموز L0–L8 (لا Phase/Layer مَنفَصِلَة)؟
- [ ] هَل كُلّ inline data نُقِلَت إلى CSV؟
- [ ] هَل كُلّ تَحليل يُرجِع ProofObject؟
- [ ] هَل source_of_claim يَحوي اسم CSV + الصَّفّ؟
- [ ] هَل اختَبَرتُ عَلى آيَة مِن `sweep_quran_all.py --surah 1`؟
- [ ] هَل عَدَّلتُ هذه الوَثيقَة لَو أَضَفتُ مَفهومًا جَديدًا؟

---

## الخاتِمَة

هذه الوَثيقَة هي **العَقد الإِداريّ** لِلمَشروع. أَيّ تَناقُض بَينها وَ بَين الكود يُحَلّ بِتَعديل الكود لا الوَثيقَة. أَيّ مُسَمَّى لا يَظهَر هُنا = اسم غَير رَسميّ يَجِب تَوحيده.

**سَلسَلَة الـ9 طَبَقات + 6 KBs + 17 عَلاقَة + 6 تَعيينات + 3 أَنواع بُرهان = الحَدّ الأَدنى المُكتَمِل.**
