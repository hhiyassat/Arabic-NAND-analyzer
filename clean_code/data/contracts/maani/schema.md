# مَخَطَّط contracts/maani/

كُلّ ملفّ CSV تَحت `volumeN/` يَلتَزِم بِالأَعمِدَة التَّاليَة:

## الأَعمِدَة المُوَحَّدَة

| العَمود | النَّوع | الوَصف |
|---|---|---|
| `priority` | int | تَرتيب التَّطبيق (الأَقَلّ أَوَّلًا) |
| `topic_id` | str | مُعَرِّف الباب (PRONOUN، DEMO، AL_DEFINITE، …) |
| `operator` | str | الكَلِمَة المُفتاحيَّة (مُشَكَّلَة) |
| `vocalized_form` | str | الشَّكل المُشَكَّل المُعتَمَد |
| `meaning_id` | str | مُعَرِّف فَريد لِلمَعنى داخِل الباب |
| `meaning_ar` | str | المَعنى بِالعَرَبيَّة |
| `syntactic_effect` | str | الأَثَر النَّحويّ (يَنصِب، يَجزِم، يَرفَع، …) |
| `semantic_field` | str | الحَقل الدَّلاليّ (تَوكيد، نَفي، شَرط، …) |
| `conditions` | str | شُروط التَّطبيق (مَفصولَة بِـ \|) |
| `exceptions` | str | استِثناءات (مَفصولَة بِـ \|) |
| `warnings` | str | تَحذيرات (مَفصولَة بِـ \|) |
| `example_constructed` | str | مِثال مُؤَلَّف (مُشَكَّل) |
| `example_quran` | str | مِثال قُرآنيّ (مُشَكَّل) |
| `surah_ayah` | str | المَرجِع القُرآنيّ (مَثَل: البقرة:2) |
| `author_position` | str | رأي السامرَّائيّ (preferred / reported / rejected) |
| `disagreement` | str | الخِلاف مَع غَيره |
| `source_part` | int | جُزء مَعاني النَّحو (1-4) |
| `source_page` | int | الصَّفحَة |
| `confidence` | float | 0.0-1.0 |

## الـ topic_ids المُعتَمَدَة (مج 1)

| topic_id | الباب |
|---|---|
| `PRONOUN` | الضَّمير |
| `PRONOUN_SHAAN` | ضَمير الشَّأن |
| `NAKIRA_MARIFA` | النَّكِرَة وَ المَعرِفَة |
| `PROPER_NOUN` | العَلَم |
| `DEMONSTRATIVE` | اسم الإِشارَة |
| `AL_DEFINITE` | المُعَرَّف بِأَل |
| `RELATIVE` | الاسم المَوصول |
| `MUBTADA_KHABAR` | المُبتَدَأ وَ الخَبَر |
| `IRAB_PHENOMENON` | ظاهِرَة الإِعراب |
| `IRAB_MEANINGS` | مَعاني الإِعراب |

## المَبدَأ الدَّستوريّ

- **لا inline data في الكود** — كُلّ سَطر هُنا
- **التَّشكيل مَطلوب** — `vocalized_form` يَجِب أَن يَكون مُشَكَّلًا
- **source_of_claim** — كُلّ سَطر يُشير لِجُزء + صَفحَة
- **confidence** — لا قَواعِد قَطعيَّة بِدون مَصدَر مَوثوق
