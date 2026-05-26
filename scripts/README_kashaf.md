# تَنزيل كُتُب الشاملَة — generic

سكربتان عامَّان لِتَنزيل **أَيّ كِتاب** مِن المَكتَبَة الشاملَة (`shamela.ws`) وَ تَنظيفه.

> ⚠️ السكربتات الـ Kashaf-specific القَديمَة (`download_kashaf_shamela.py` و `prepare_kashaf_text.py`)
> صارَت مَنسوخَة. يُمكِنُك حَذفها — استَخدِم النُّسخَة العامَّة أَدناه.

## التَّبَعيَّات

```bash
pip install requests beautifulsoup4
```

## الخَطوَة 1: التَّنزيل

```bash
# بِرَقم الكِتاب
python3 scripts/download_shamela_book.py --book-id 23627

# بِالرابِط الكامِل
python3 scripts/download_shamela_book.py --url https://shamela.ws/book/23627

# مَع slug مُخَصَّص
python3 scripts/download_shamela_book.py --book-id 23627 --slug kashaf

# مَع تَخصيص مُجَلَّد المُخرَج
python3 scripts/download_shamela_book.py --book-id 23627 --out-dir data/raw/zamakhshari/

# مَع زِيادَة الفاصِل لِلِاحتِرام
python3 scripts/download_shamela_book.py --book-id 23627 --delay 3.0
```

### الخِيارات

| الخِيار | الوَصف |
|---|---|
| `--book-id N` أَو `--url ...` | إِلزاميّ — أَحَدُهما |
| `--slug NAME` | اسم المُجَلَّد (يُكشَف تِلقائيًّا مِن اسم الكِتاب) |
| `--out-dir PATH` | مُجَلَّد المُخرَجات (افتراضيّ `data/raw/{slug}/`) |
| `--start N` | رَقم الصَّفحَة الأَوَّل (افتراضيّ 1) |
| `--end N` | رَقم الصَّفحَة الأَخير (يُكشَف تِلقائيًّا) |
| `--delay N` | فاصِل بَين الطَّلَبات بِالثَّواني (افتراضيّ 1.5) |
| `--no-resume` | إعادَة كامِلَة بَدَل الاستِئناف |
| `--max-empty-streak N` | إِيقاف بَعد N صَفحَة فارِغَة (افتراضيّ 10) |

### الخَصائص

- **generic** — أَيّ كِتاب في الشاملَة (لا hard-coding)
- **اكتِشاف تِلقائيّ** لاسم الكِتاب + المُؤَلِّف مِن صَفحَة الفِهرِس
- **يَحتَفِظ بِالتَّشكيل** كامِلًا (الـ raw_text لا يُعَدَّل)
- **استِئناف** — يَقرَأ المَلَفّ المَوجود وَ يَتَخَطّى المُنَزَّل
- **retry** 3 مَرّات مَع backoff لِكُلّ صَفحَة
- **user-agent مُحتَرَم** — يُعَرِّف نَفسه كَبَحث عَرَبيّ
- **اكتِشاف نِهايَة الكِتاب** بِـ max_empty_streak

### المُخرَجات

في `data/raw/{slug}/`:
- `{slug}_raw_pages.jsonl` — سَطر لِكُلّ صَفحَة
- `{slug}_index.html` — نُسخَة مِن صَفحَة الفِهرِس
- `book_meta.json` — اسم/مُؤَلِّف/book_id/slug
- `download_report.md` — تَقرير شامِل

صِيغَة سَطر JSONL:
```json
{
  "book": "الكشاف",
  "author": "الزمخشري",
  "source": "shamela",
  "book_id": "23627",
  "url": "https://shamela.ws/book/23627/123",
  "page_no": 123,
  "section_title": "سورة البقرة",
  "raw_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ...",
  "has_diacritics": true,
  "downloaded_at": "2026-05-23T03:00:00+00:00"
}
```

## الخَطوَة 2: التَّنظيف وَ الفَهرَسَة

```bash
# تَنظيف بِناءً على slug
python3 scripts/prepare_shamela_book.py --slug kashaf

# تَنظيف مَع نُسخَة بِلا تَشكيل (cleaned_text_plain)
python3 scripts/prepare_shamela_book.py --slug kashaf --strip-diacritics

# لِكُتُب غَير التَّفسير (لا فَهرَسَة آيات)
python3 scripts/prepare_shamela_book.py --slug ibn_aqil --no-quran-index

# تَخصيص المَسارات
python3 scripts/prepare_shamela_book.py --input data/raw/X/X_raw_pages.jsonl
```

### الخَصائص

- **يَحتَفِظ بِالتَّشكيل** في `cleaned_text`
- **اختياريًّا** يُضيف `cleaned_text_plain` (مَجرَّد) بِـ `--strip-diacritics`
- **يَكشِف السورَة الحاليَّة** («سورة كَذا») في كُتُب التَّفسير
- **يَستَخرِج الاقتِباسات القُرآنيَّة** بَين ﴿…﴾ أَو بَعد «قَوله تَعالى»
- **دَعم النِّطاقات** [البقرة: 1-2]
- **dedup حَسَب نَصّ الآيَة** (مُجَرَّدًا مِن التَّشكيل)
- **يَدعَم 114 سورَة** بِأَسمائها + variants

### المُخرَجات

في `data/processed/{slug}/`:
- `{slug}_clean_sections.jsonl` — كُلّ صَفحَة مَع `cleaned_text` + سورَة مَكشوفَة
- `{slug}_ayah_index.jsonl` — فَهرَس آيات (لِكُتُب التَّفسير)

صِيغَة فَهرَس الآيات:
```json
{
  "page_no": 5,
  "position": 234,
  "quote_type": "ornamental_brackets",
  "ayah_text": "هُدًى لِلْمُتَّقِينَ",
  "ayah_text_plain": "هدى للمتقين",
  "surah_num": 2,
  "surah_name": "البقرة",
  "ayah_no": 2,
  "ayah_range_end": null,
  "context_before": "..."
}
```

## أَمثلَة لِكُتُب مُختَلِفَة

```bash
# الكشّاف لِلزَّمَخشَريّ (تَفسير)
python3 scripts/download_shamela_book.py --book-id 23627 --slug kashaf
python3 scripts/prepare_shamela_book.py --slug kashaf

# تَفسير ابن كَثير (مَثَلًا book/95)
python3 scripts/download_shamela_book.py --book-id 95 --slug ibn_kathir
python3 scripts/prepare_shamela_book.py --slug ibn_kathir

# شَرح ابن عقيل (نَحو، لا فَهرَسَة آيات)
python3 scripts/download_shamela_book.py --book-id 12345 --slug ibn_aqil
python3 scripts/prepare_shamela_book.py --slug ibn_aqil --no-quran-index
```

## التَّكامُل مَع المَشروع

بَعد التَّنزيل وَ التَّنظيف، يُمكِن:
- استِخدام `{slug}_ayah_index.jsonl` كَ **شَواهِد قُرآنيَّة** لِكَلِمات/تَراكيب
- **رَبط analyze_verse** بِتَفسير ما عَبر (سورَة، آيَة)
- **توسيع `maani_kb_loader`** لِيَدعَم تَفاسير مُتَعَدِّدَة
