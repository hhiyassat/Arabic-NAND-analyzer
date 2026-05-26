# اختبارات معمار المعنى العربي — أَحدَث الأَوامِر

> مَلَفّ يُحَدَّث مَع كُلّ مَرحَلَة جَديدَة. آخِر تَحديث: 2026-05-23

---

## 🆕 المَرحَلَة الحاليَّة: اختبار 102 جُملَة عَوامِل + مَسح القُرآن

### 0a. اختبار 102 جُملَة عَوامِل مُشَكَّلَة (sample_operators_test.txt)

```bash
python3 test_operators_samples.py                    # كُلّ الـ102 + مُلَخَّص
python3 test_operators_samples.py --line 6           # جُملَة واحِدَة («وَاللَّهِ لَأَشْرَبَنَّ»)
python3 test_operators_samples.py --verbose          # تَفاصيل كامِلَة لِكُلّ جُملَة
python3 test_operators_samples.py --csv              # CSV فَقَط بِلا طِباعَة
```

**ما يَفعَل:** يَقرَأ 102 جُملَة عَوامِل مُختَبَرَة (سامرّائيّ + ابن هشام) مِن `sample_operators_test.txt`
وَ يَفحَص كُلّ جُملَة عَلى حِدَة بِالـ KB الجَديدَة.

**المُتَوَقَّع:**
- 332 كَلِمَة، 97 مَكشوفَة (29.2%)
- أَبواب أَكثَر ظُهورًا: PREP_BA (110)، PREP_LAM (96)، PREP_KAF (39)
- مَخرَجات: `data/samarrai_sweep/operators_samples_results.csv`

**أَمثِلَة:**
- جُملَة 1: «مَرَرْتُ بِزَيْدٍ» → الباء (10 مَعاني)
- جُملَة 6: «وَاللَّهِ لَأَشْرَبَنَّ» → 100% تَغطيَة، 16 ادِّعاء (واو القَسَم + لام الجَواب)
- جُملَة 40: «لَمْ يَكْتُبْ زَيْدٌ» → JAZM_LAM
- جُملَة 96: «حَسِبْتُ زَيْدًا حَاضِرًا» → ZANN_FAMILY (أَفعال القُلوب)

### 0b. مَسح كامِل القُرآن (6,236 آية في 2.5 ثانيَة)

```bash
python3 samarrai_quran_sweep.py                   # كامِل القُرآن
python3 samarrai_quran_sweep.py --surah 1         # سُورَة واحِدَة فَقَط
python3 samarrai_quran_sweep.py --max 100         # أَوَّل 100 آية (لِلِاختبار)
```

**ما يَفعَل:** يَفحَص كُلّ آية بِالـ KB الجَديدَة (243 قاعِدَة) وَ يُخرِج:
- `data/samarrai_sweep/per_verse.csv` — لِكُلّ آية (تَغطيَة، ادِّعاءات، تَراكيب)
- `data/samarrai_sweep/per_word.csv` — لِكُلّ كَلِمَة مَكشوفَة (volume، topic_id، source_page)
- `data/samarrai_sweep/constructions.csv` — كُلّ التَّراكيب المَكشوفَة (TAQDIM، TAHZHEER)
- `data/samarrai_sweep/top_operators.csv` — أَكثَر العَوامِل ظُهورًا
- `data/samarrai_sweep/top_topics.csv` — أَكثَر الأَبواب
- `data/samarrai_sweep/summary.txt` — تَقرير نَصّيّ

**المُتَوَقَّع (أَحدَث مَسح):**
- 82,245 كَلِمَة | 36,456 مَكشوفَة (**44.3% تَغطيَة**)
- 190,525 ادِّعاء دَلاليّ
- 19 تَركيب (18 TAQDIM + 1 TAHZHEER)
- أَكثَر العَوامِل: بِ (40,480) → لِ → وَ → مِن → كَ
- السُّرعَة: ~2,500 آية/ث

---

## SamarraiAnalyzer (المُجَلَّدات 1-4 + كَشف التَّراكيب)

### 1. تَحليل آية مِن القُرآن

```bash
python3 samarrai_analyzer.py --verse 1:5
```

**ما يَفعَل:** يُحَلِّل آية «إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ» عَبر المُجَلَّدات الأَربَعَة لِلسامَرّائيّ.
**المُتَوَقَّع:** يَكشِف ضَمير المُنفَصِل المَنصوب + تَركيب TAQDIM_AL_MA3MOOL_LI_IKHTISAS مَرَّتَين.

```bash
python3 samarrai_analyzer.py --verse 1:1   # بِسمِ اللَّهِ — 10 مَعاني لِلباء
python3 samarrai_analyzer.py --verse 1:2   # الحَمدُ لِلَّهِ — 13 مَعنى لِلام
python3 samarrai_analyzer.py --verse 112:3 # لَم يَلِدْ وَلَم يُولَدْ — الجَوازِم
```

### 2. تَحليل نَصّ مُباشَر

```bash
python3 samarrai_analyzer.py "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ"
python3 samarrai_analyzer.py "إِيَّاكُمْ وَالظَّنَّ"
```

**ما يَفعَل:** يُحَلِّل أَيّ نَصّ عَرَبيّ مُشَكَّل.
**المُتَوَقَّع:** يَكشِف العَوامِل (إِنَّ، إِيَّا...) + التَّراكيب (TAHZHEER).

### 3. كَشف التَّراكيب النَّحويَّة

```bash
python3 samarrai_analyzer.py "إِيَّاكَ نَعْبُدُ"        # TAQDIM
python3 samarrai_analyzer.py "إِيَّاكُمْ وَالكَذِبَ"     # TAHZHEER
```

**ما يَفعَل:** يَكشِف القَواعِد التَّركيبيَّة (نَمَط) لا الكَلِميَّة (lookup).
**المُتَوَقَّع:**
- إِيَّا + فِعل → `TAQDIM_AL_MA3MOOL_LI_IKHTISAS` (ج4/ص150)
- إِيَّا + واو+اسم → `TAHZHEER_BASIC` (ج2/ص109)

### 4. عَرض تَفصيليّ مَع المَثَل القُرآنيّ

```bash
python3 samarrai_analyzer.py --verse 1:5 -v
python3 samarrai_analyzer.py "بِسمِ اللَّهِ" -v
```

**ما يَفعَل:** يُضيف topic_id + syntactic_effect + confidence + مَثَل قُرآنيّ + source_page.

### 5. إِحصاءات الـ KB

```bash
python3 samarrai_analyzer.py --stats
```

**ما يَفعَل:** يَعرِض عَدَد السِّجِلّات وَ الأَبواب لِكُلّ مُجَلَّد.
**المُتَوَقَّع:** 243 سِجِلًّا، 78 بابًا (1: 70+12 إِيَّا، 2: 42، 3: 62، 4: 57).

### 6. تَحليل مَلَفّ نَصّيّ

```bash
python3 samarrai_analyzer.py --file my_text.txt
python3 samarrai_analyzer.py --file my_text.txt -v
```

---

## مُحَمِّلات المُجَلَّدات (volume loaders)

كُلّ مُحَمِّل يُمكِن تَشغيله مُستَقِلًّا لِفَحص مُحتَوى مُجَلَّد:

```bash
python3 samarrai_loaders/volume1_loader.py   # المَعارِف + الإِسناد (70 سِجِلًّا + 12 إِيَّا)
python3 samarrai_loaders/volume2_loader.py   # الأَفعال + المَفاعيل (42)
python3 samarrai_loaders/volume3_loader.py   # حُروف الجَرّ + التَّضمين (62، 17 حَرف)
python3 samarrai_loaders/volume4_loader.py   # الجَزم + الشَّرط + التَّوكيد + القَسَم (57)
```

**ما يَفعَل:** يَعرِض إِحصاءات المُجَلَّد + اختبار lookup عَلى عَيِّنَة عَوامِل.

---

## أَدَوات سابِقَة (لا تَزال تَعمَل)

### analyze_verse.py — التَّحليل الشَّامِل بِكُلّ الطَّبَقات

```bash
python3 analyze_verse.py 1:5
python3 analyze_verse.py 1:5 --full      # كُلّ الطَّبَقات (M1, Phase C, إعراب، Maani...)
python3 analyze_verse.py 1:5 --maani     # Maani-KB فَقَط
```

### analyze_maani.py — مَعاني النَّحو فَقَط

```bash
python3 analyze_maani.py 1:5
python3 analyze_maani.py 2:214
```

### analyze_text.py — نَصّ عامّ (لَيسَ قُرآنًا)

```bash
python3 analyze_text.py "نَصّ عَرَبيّ مُشَكَّل"
python3 analyze_text.py --file essay.txt
```

---

## اختبارات سَريعَة لِلتَّحَقُّق

### يَجِب أَن تَنجَح كُلّها (smoke tests):

```bash
# 1. الـ KB يُحَمَّل بِنَجاح
python3 samarrai_analyzer.py --stats | grep "المَجموع"
# المُتَوَقَّع: 243 سِجِلًّا

# 2. التَّقديم لِلِاختِصاص يَنطَلِق في الفاتحَة
python3 samarrai_analyzer.py --verse 1:5 | grep -c "TAQDIM_AL_MA3MOOL"
# المُتَوَقَّع: 2

# 3. التَّحذير يَنطَلِق
python3 samarrai_analyzer.py "إِيَّاكُمْ وَالظَّنَّ" | grep -c "TAHZHEER"
# المُتَوَقَّع: ≥1

# 4. حُروف الجَرّ مُغَطّاة
python3 samarrai_analyzer.py "بِسمِ اللَّهِ" | grep -c "ج3"
# المُتَوَقَّع: ≥10 (مَعاني الباء)

# 5. NFC يَعمَل (إِيَّاكَ مِن القُرآن لا يَتَطابَق مَع إِيَّاكِ)
python3 samarrai_analyzer.py --verse 1:5 | grep "إِيَّاكَ" | grep -c "مُؤَنَّث"
# المُتَوَقَّع: 0
```

---

## مَواضِع المَلَفّات

| المَلَفّ | المَكان |
|---|---|
| المُحَلِّل المُوَحَّد | `samarrai_analyzer.py` |
| المُحَمِّلات | `samarrai_loaders/volume{1,2,3,4}_loader.py` |
| الـ CSVs | `data/contracts/maani/volume{1,2,3,4}/*.csv` |
| الـ schema | `data/contracts/maani/schema.md` |
| القُرآن المُشَكَّل | `../data/quran-uthmani-with-pause-mark.txt` |
| هذا المَلَفّ | `TESTS.md` |

---

## سَجِلّ المَراحِل (للرُّجوع)

- **Phase A** (2026-05): مُجَلَّد 1 — المَعارِف + الإِسناد (70 سِجِلًّا)
- **Phase B** (2026-05): مُجَلَّد 2 — الأَفعال + المَفاعيل (42)
- **Phase C** (2026-05): مُجَلَّد 3 — حُروف الجَرّ + التَّضمين (62، 17 حَرف)
- **Phase D** (2026-05): مُجَلَّد 4 — الجَزم + الشَّرط + التَّوكيد + القَسَم + التَّقديم (57)
- **SamarraiAnalyzer v1** (2026-05): المُحَلِّل المُوَحَّد فَوق الـ4 + كَشف التَّراكيب (TAQDIM + TAHZHEER)

---

## ✏️ إِضافَة مَرحَلَة جَديدَة

عِندَما نُكمِل مَرحَلَة جَديدَة، أَضِف في الأَعلى تَحت «🆕 المَرحَلَة الحاليَّة»:
- الأَمر المُختَصَر
- ما يَفعَل
- ما هو المُتَوَقَّع
- مَثَل ناجِح
