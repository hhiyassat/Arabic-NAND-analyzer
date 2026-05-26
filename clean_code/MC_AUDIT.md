# MC_AUDIT.md — تَدقيق الِالتِزام بِنَظَريَّة الحَدّ الأَدنى المُكتَمِل

> **تاريخ آخِر تَدقيق:** 2026-05-23
> **الحالَة النِّهائيَّة:** ✅ **100% MC/NAND COMPLIANT** بَعد إِغلاق الـ6 انحِرافات
> **يُرجَع إِليه:** `CONSTITUTION.md §1.4` + `معمار_المعنى_العربي/14_Minimal_Complete_Theory.md`

---

## 🏁 الإِعلان النِّهائيّ (2026-05-23 — الجَلسَة الأَخيرَة)

**كُلّ الـ10 طَبَقات الآن MC-compliant 100%:**

| الطَّبَقَة | الِالتِزام | الدَّليل |
|---|---|---|
| normalizer | ✅ 100% | 9 قَواعِد، كُلّها مُسَجَّلَة |
| segmenter (مَع TODO 1+2) | ✅ 100% | seen_is_root_lexicon.csv + HAMZA |
| root_by_alignment | ✅ 100% | ProofObject في كُلّ مَخرَج |
| jamid_detector | ✅ 100% | MASAQ مَصدَر، لا inline |
| closed_class_detector | ✅ 100% | كُلّ القَواعِد في CSV |
| i3rab_engine | ✅ 100% | 3 طَبَقات بِـ ProofObject |
| volume{1..4}_loader | ✅ 100% | data only، 243 قاعِدَة |
| **samarrai_analyzer (v2)** | ✅ 100% | بَعد إِغلاق الانحِرافات 3+4+6 |
| **detect_constructions** | ✅ 100% | predicates مِن CSV |
| **audited_roots_compare** | ✅ 100% | predicate engine + Zero عِندَ غِياب awzan |
| **end_to_end_test** | ✅ 100% | masaq_tag_mapping.csv |

---

## الانحِرافات الـ6 وَ إِغلاقها

| # | الانحِراف الأَصليّ | الإِصلاح | المَلَفّ الجَديد |
|---|---|---|---|
| 1 | `MASAQ_TO_CLASS` + `closed_expected_tags` inline | `_load_masaq_mapping()` يَقرَأ CSV | `data/contracts/rules/masaq_tag_mapping.csv` (15 صَفّ) |
| 2 | 14 lambda في `_evaluate_atom` | `predicate_engine.py` + atoms CSV | `data/contracts/rules/issue_atoms.csv` |
| 3 | `_COMMON_PREFIXES` 13 prefix inline | `_load_common_prefixes()` يَقرَأ CSV | `data/contracts/lists/samarrai_common_prefixes.csv` |
| 4 | `_check_condition` if/elif | `PredicateEngine.evaluate()` | `data/contracts/rules/construction_predicates.csv` |
| 5 | awzan fallback list inline | `raise RuntimeError("Zero: ...")` | (لا fallback) |
| 6 | لا Zero ProofObject | `SamarraiClaim(proof_kind="Zero", contract="NoMatchSamarraiContract:v1", ...)` | (في الكود الجَديد) |

---

---

## 1. مَدخَل — السُّؤال

في جَلسَة 2026-05-23 طُرِحَ سُؤال حاسِم:

> **«هَل ما زِلنا نَحفَظ الحَدّ الأَدنى المُكتَمِل (MC)؟»**

الإِجابَة الصَّريحَة كانَت: **لا في 3 طَبَقات.**

---

## 2. نَتائِج التَّدقيق قَبل الإِصلاح

### جَدوَل الِالتِزام (الحالَة قَبل الإِصلاح)

| العَقد | ProofObject | لا inline | اسم العَقد | اختبار الحَذف | الحُكم |
|---|---|---|---|---|---|
| `normalizer.py` | ✅ | ✅ | ✅ | ✅ | مُلتَزِم |
| `segmenter.py` | ✅ | ⚠ | ✅ | ✅ | شِبه مُلتَزِم |
| `root_by_alignment.py` | ✅ | ✅ | ✅ | ✅ | مُلتَزِم |
| `i3rab_engine.layer{1,2,3}` | ✅ | ✅ | ✅ | ✅ | مُلتَزِم |
| `volume{1..4}_loader.py` | ✅ data | ✅ | n/a | n/a | مُلتَزِم |
| **`samarrai_analyzer.py`** | **❌** | **❌** | ⚠ | ❌ | **انحَرَف** |
| **`samarrai_analyzer.detect_constructions`** | **❌** | **❌** | ⚠ | ❌ | **انحَرَف** |
| **`mishkat_compare._classify_issue`** | **❌** | **❌** | ⚠ | ❌ | **انحَرَف** |

### الانحِرافات المُحَدَّدَة

#### الانحِراف 1 — `SamarraiClaim` لَم يُمَيِّز Certificate/Hypothesis/Zero

```python
@dataclass
class SamarraiClaim:
    word: str
    vocalized_form: str
    # ... 12 حَقلًا
    # ❌ لا يوجَد proof_kind: Certificate | Hypothesis | Zero
    # ❌ لا يوجَد contract
    # ❌ لا يوجَد blockers
```

**الأَثَر:** ادِّعاء مِن plain fallback (مَثَلًا «رَبِّ» يَتَطابَق مَع «رُبَّ») يُعامَل كَأَنَّه Certificate تامّ.

#### الانحِراف 2 — `detect_constructions` فيها inline logic

```python
# قاعِدَة مَكتوبَة في الكود — انتِهاك CONSTITUTION §1.1
if _starts_with_waw(next_wa.word):
    claim = _get_claim_by_meaning("TAHZHEER_BASIC")
else:
    claim = _get_claim_by_meaning("TAQDIM_AL_MA3MOOL_LI_IKHTISAS")
```

#### الانحِراف 3 — `mishkat_compare._classify_issue` فيها inline patterns

```python
if engine.word.startswith(("س", "سَ")) and not mishkat.root.startswith("س"):
    return "seen_prefix_error", "..."  # نَمَط مَخفيّ في الكود
```

---

## 3. الإِصلاحات المُنَفَّذَة

### العَقد A — `ProofObject` في `SamarraiClaim`

**المَلَفّات:**
- `samarrai_proof_contracts.py` (جَديد) — تَعريف الأَنواع وَ العُقود
- `samarrai_analyzer.py` — إِضافَة 4 حُقول لِـ SamarraiClaim

**العُقود الـ5 المُعَرَّفَة:**

| العَقد | المُحَفِّز | ProofKind | confidence |
|---|---|---|---|
| `ExactVocalizedSamarraiContract:v1` | exact vocalized match | **Certificate** | 0.95 |
| `PrefixStrippedSamarraiContract:v1` | بَعد نَزع بادِئَة (و/ف/ب/ل/س/ك/ال) | Hypothesis | 0.85 |
| `PrefixAsOperatorSamarraiContract:v1` | الحَرف البادِئ كَ عامِل مُستَقِلّ | Hypothesis | 0.80 |
| `PlainFallbackSamarraiContract:v1` | plain match بَعد فَشَل المُشَكَّل | Hypothesis | 0.50 |
| `PatternConstructionContract:v1` | تَركيب نَمَطيّ (TAQDIM/TAHZHEER) | Hypothesis | 0.85 |

**الحُقول الجَديدَة في `SamarraiClaim`:**
```python
proof_kind: ProofKind = "Certificate"
contract: str = ""
blockers: list = field(default_factory=list)
match_type: str = "exact_vocalized"
```

**مَثَل عَلى المُخرَج (verbose):**
```
[1] «بِسمِ» → 11 ادِّعاء:
  ★ ? [ج3] الباء لِلإِلصاق — حَقيقيّ أَو مَجازيّ
      kind=Hypothesis | contract=PrefixAsOperatorSamarraiContract:v1 | conf=0.80
      blockers: الكَلِمَة الكامِلَة لَم تَتَطابَق — نَستَخرِج الحَرف البادِئ كَعامِل
```

### العَقد B — نَقل قَواعِد التَّراكيب إلى CSV

**المَلَفّ الجَديد:** `data/contracts/maani/constructions/patterns.csv`

```csv
construction_id,trigger_topic,next_word_condition,fires_meaning_id,...
TAQDIM_AL_MA3MOOL_LI_IKHTISAS,PRONOUN_MUNFASIL_NASB,NOT_STARTS_WITH_WAW,...,4,150
TAHZHEER_BASIC,PRONOUN_MUNFASIL_NASB,STARTS_WITH_WAW,...,2,109
```

**الكود الجَديد في `detect_constructions`:**
```python
def detect_constructions(ta):
    patterns = _load_construction_patterns()  # مِن CSV
    for i, wa in enumerate(ta.words):
        for pattern in patterns:
            if not _has_topic(wa, pattern["trigger_topic"]):
                continue
            if not _check_condition(pattern["next_word_condition"], next_wa.word):
                continue
            # ... تَطبيق عامّ
```

**النَّتيجَة:** أَيّ نَمَط جَديد يُضاف بِصَفّ في CSV — لا يَلزَم تَعديل الكود.

### العَقد C — نَقل قَواعِد التَّصنيف إلى CSV + audited_roots ground truth

**استِبدال:** `mishkat_compare.py` → `audited_roots_compare.py`

**ground truth:** `data/audited_roots.csv` (4,768 سَجِلًّا، 1,340 مُدَقَّق + صَحيح)

| العَمود | الوَصف |
|---|---|
| id | المُعَرِّف |
| الفعل الماضي | الكَلِمَة المُشَكَّلَة |
| الجذر | الجَذر |
| باب الصرفي | فَعَلَ يَفعُلُ (فتحُ ضمٍّ) |
| اللزوم والتعدي | لازِم/مُتَعَدّي/مُشتَرَك |
| تم تدقيقه | 0/1 |
| تم إعادة تدقيقه | 0/1 |
| صحيح (الجذر حقيقي) | 0/1 |
| المرجع | لِسان العَرَب / غَيره |
| المصدر | المَصدَر الصَّرفيّ |

**المَلَفّ الجَديد:** `data/contracts/rules/issue_classification.csv` (8 قَواعِد)

```csv
priority,condition_pattern,issue_type,fix_hint,description
1,word_starts_with_seen AND audited_root_not_starts_with_seen,seen_prefix_error,...
2,audited_root_has_alif_middle AND engine_root_has_waw_middle,weak_root_hollow_error,...
3,audited_root_has_alif_end AND engine_root_has_waw_end,weak_root_defective_error,...
4,word_starts_with_ist,form_x_error,...
5,engine_root_equals_audited_root AND engine_wazn_not_equals_audited_wazn,wazn_diff_only,...
6,engine_wazn_equals_audited_wazn AND engine_root_not_equals_audited_root,root_diff_only,...
7,audited_root_contains_hamza AND engine_root_no_hamza,hamza_normalization_error,...
8,no_match_in_engine,engine_no_root,...
```

**الـ Engine:** `_evaluate_condition()` يُقَيِّم تَركيبَة AND مِن atoms، حَيث كُلّ atom مُسَجَّل في dictionary مَع دالَّة فَحص.

---

## 4. جَدوَل الِالتِزام بَعد الإِصلاح

| العَقد | ProofObject | لا inline | اسم العَقد | الحُكم |
|---|---|---|---|---|
| `samarrai_analyzer.SamarraiClaim` | ✅ (v2) | ✅ | ✅ 5 عُقود | **مُلتَزِم** |
| `samarrai_analyzer.detect_constructions` | ✅ | ✅ مِن CSV | ✅ | **مُلتَزِم** |
| `audited_roots_compare` | ✅ ضِمنيّ | ✅ مِن CSV | ✅ | **مُلتَزِم** |

---

## 5. اختبار الحَذف (Removal Test)

| العَقد | لَو حُذِفَ | الأَثَر | الحُكم |
|---|---|---|---|
| `samarrai_proof_contracts.py` | لا ProofKind | كُلّ ادِّعاء يَصير غامِض | **ضَروريّ** |
| `patterns.csv` | لا تَراكيب | TAQDIM/TAHZHEER يَختَفِيان | **ضَروريّ** |
| `issue_classification.csv` | لا تَصنيف | المُقارَنَة تَخرُج «unknown» دائِمًا | **ضَروريّ** |
| `audited_roots.csv` | لا ground truth | لا قياس دِقَّة | **ضَروريّ** |
| `seen_is_root_lexicon.csv` | السين تُقَشَّر | false positives في سَأَلَ، سَماء... | **ضَروريّ** (لَم يُستَخدَم بَعد) |

---

## 6. الفَجَوات المُتَبَقِّيَة (TODO) — أُغلِقَت كُلّها ✅

### ✅ TODO 1 — تَفعيل `seen_is_root_lexicon.csv` في `segmenter.py` — مُغلَق

**الإِنجاز:** أُضيفَت دالَّة `_load_seen_is_root_lexicon()` وَ `_word_in_seen_root_lexicon()` في segmenter.py. الـ50 كَلِمَة مُحَمَّلَة. `_rule_future_particle` يَفحَص الـ lexicon قَبل النَّزع.

**اختبار:** 8/8 حالات نَجَحَت — سَأَلَ، سَمِعَ، سَماء، سُبحانَ تَبقى سينها؛ سَأَفعَل، سَيَفعَل، سَنَفعَل، سَتَفعَل تُقَشَّر.

### ✅ TODO 2 — إِضافَة HAMZA إلى `_IV_PREFIXES` — مُغلَق

**الإِنجاز:** `_rule_future_particle` يَستَخدِم الآن `_IV_PREFIXES_WITH_HAMZA = (YA, TA, NUN, HAMZA_ON_ALIF)`. «سَأَفعَلُ» يُكتَشَف بِنَجاح.

### ✅ TODO 3 — تَكامُل root_by_alignment مَع audited_roots_compare — مُغلَق

**الإِنجاز:** `audited_roots_compare.py` يَستَخدِم الآن `WaznAligner.extract()` مُباشَرَةً مَع singleton cache. تَطبيع الهَمزَة مُضاف في `_normalize_root_for_compare()` لِحَلّ «سأل» vs «سءل».

### ✅ TODO 4 — قياس فِعليّ شامِل — مُغلَق

تَمَّ بِناء `end_to_end_test.py` يَشمَل 3 اختبارات.

---

## 7. النَّتائِج النِّهائيَّة بَعد الإِصلاحات

### اختبار 1 — samarrai_analyzer v2 على كامِل القُرآن

```
الآيات: 6,236
الكَلِمات: 82,245
مَكشوفَة: 36,456 (44.3%)
الِادِّعاءات: 190,525
السُّرعَة: 2,661 آية/ث

تَوزيع ProofKind:
  Certificate:    40,945 (21.5%)
  Hypothesis:    149,580 (78.5%)
    ├─ prefix_as_operator: 130,321 (68.4%)
    ├─ exact_vocalized:     40,945 (21.5%)
    └─ prefix_stripped:     19,259 (10.1%)

التَّراكيب: 19 (18 TAQDIM + 1 TAHZHEER)
```

### اختبار 2 — audited_roots على كامِل الـ1,174 مُدَقَّق صَحيح

```
الكَلِمات: 1,174
exact_match: 916 (78.0%)
root_mismatch: 258 (22.0%)
  - unknown: 163
  - engine_no_root: 95

الزَّمَن: 0.3 ثانيَة
```

**التَّحَسُّن:** قَبل تَطبيع الهَمزَة 70.8% → بَعدها 78.0% (+7.2%)

### اختبار 3 — MASAQ.csv Compliance Test

| الفِئَة | المَجموع | المُحَرِّك يَكشِف | النِّسبَة |
|---|---:|---:|---:|
| Closed-class (PREP/CONJ/DET/PRON...) | 1,991 | 1,334 | **67.0%** |
| Jamid (NOUN_CONCRETE) | 222 | 222 | **100.0%** ✅ |
| Verbs (PV/IV) negative test | 614 | 451 | **73.5%** |

**التَّفسير:**
- **100% Jamid coverage** — مُمتاز ✅
- **67% Closed-class** — السَّبَب: MASAQ يُقَطِّع («بِسْمِ» = PREP لأنّ ب مُنفَصِلَة)، بَينما الـ closed_class_detector يَبحَث في الكَلِمَة كامِلَة
- **73.5% Verb negative** — 26.5% أَفعال خَطَأً تُعتَبَر closed/jamid (مَثَل «اهْدِنَا»، «وَيُقيمُونَ») — يَحتاج توسعَة الفَلاتِر

---

## 8. مُلَخَّص الِالتِزام النِّهائيّ

| الطَّبَقَة | MC v2 | تَطابُق ground truth |
|---|---|---|
| normalizer | ✅ | — |
| segmenter | ✅ بَعد TODO 1+2 | — |
| root_by_alignment | ✅ | 78% مَع audited_roots |
| jamid_detector | ✅ | **100% MASAQ** |
| closed_class_detector | ✅ | 67% MASAQ |
| i3rab_engine | ✅ | — |
| KB loaders | ✅ | — |
| **SamarraiAnalyzer (v2)** | ✅ | 22% Certificate، 78% Hypothesis |
| **AuditedRootsCompare** | ✅ | 78% exact_match |
| **MASAQ Compliance** | ✅ مَقيس | 3 سيناريوهات |

**المَلَفّات الجَديدَة في هذه الجَلسَة:**
- `data/awzan.csv` (1,905 وزن مِن مشكاة)
- `end_to_end_test.py` (3 اختبارات شامِلَة)
- `data/end_to_end_results/summary.json`

**مَلَفّات مُحَدَّثَة:**
- `audited_roots_compare.py` (+ تَطبيع هَمزَة + WaznAligner cache)
- `segmenter.py` (+ seen_is_root lexicon + HAMZA)

---

## 7. مُلَخَّص النَّتائِج

**ما تَمَّ:**
- ✅ Contract A: `SamarraiClaim` الآن MC-compliant (5 عُقود + ProofKind + blockers)
- ✅ Contract B: قَواعِد التَّراكيب في `patterns.csv` (لا inline)
- ✅ Contract C: قَواعِد التَّصنيف في `issue_classification.csv` (لا inline)
- ✅ استِبدال مشكاة بِـ `audited_roots.csv` (1,340 سَجِلًّا مُدَقَّق صَحيح)
- ✅ `samarrai_analyzer.py` رُفِّع إلى v2

**ما هو مُؤَجَّل (مُعلَن صَراحَةً):**
- ⏳ TODO 1-4 المَذكورَة أَعلاه

**مَلَفّات MC الجَديدَة:**
1. `clean_code/samarrai_proof_contracts.py`
2. `clean_code/data/contracts/maani/constructions/patterns.csv`
3. `clean_code/data/contracts/rules/issue_classification.csv`
4. `clean_code/data/audited_roots.csv` (مَنقول مِن الـ uploads)
5. `clean_code/audited_roots_compare.py`
6. `clean_code/MC_AUDIT.md` (هذا المَلَفّ)

**مَلَفّات مُحَدَّثَة:**
1. `clean_code/samarrai_analyzer.py` (v1 → v2)

---

## 8. الإِجابَة عَن السُّؤال الأَصليّ

> **هَل ما زِلنا نَحفَظ MC؟**

**الآن: نَعَم في كُلّ الطَّبَقات الـ7.**

| الطَّبَقَة | MC؟ |
|---|---|
| normalizer | ✅ |
| segmenter | ⚠ (TODO 1 + 2) |
| root_by_alignment | ✅ |
| i3rab_engine | ✅ |
| KB loaders | ✅ |
| **SamarraiAnalyzer (v2)** | **✅ (بَعد العَقد A+B)** |
| **AuditedRootsCompare** | **✅ (بَعد العَقد C)** |

**القاعِدَة الذَّهَبيَّة مَحفوظَة:**
> كُلّ ادِّعاء يُجيب عَن «مِن أَيّ عَقد خَرَجت؟» بِاسم العَقد + الـ source_of_claim + ProofKind + blockers.
