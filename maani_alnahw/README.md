# معاني النحو — Semantic Grammar Authority

طَبَقَة مَرجِعيَّة تُستَخرَج مِن كِتاب «مَعاني النَّحو» لِلدُّكتور فاضِل صالِح السَّامَرَّائيّ،
تُحَوِّل النَّصّ OCR إلى قاعِدَة مَعرِفَة نَحويَّة دَلاليَّة قابِلَة لِلبَحث والاستخدام في
مُحَرِّك تَحليل العَرَبيَّة/القُرآن.

## الهَيكَل

```
data/
  raw/maani_alnahw/{1,2,3,4}.txt    — مَصدَر OCR
  processed/maani_alnahw/            — مُخرَجات
    pages.jsonl
    cleaned_pages.jsonl
    topics.jsonl
    rule_cards.jsonl
    examples.jsonl
    opinions.jsonl
    ocr_corrections.jsonl
    construction_rules.jsonl
    extraction_report.md
lexicons/                            — مَعاجِم static
  ocr_corrections_static.json
  grammar_terms.json
  scholars.json
  quran_surah_names.json
  construction_triggers.json
src/maani_alnahw/                    — الكود
  models.py
  page_splitter.py
  ocr_normalizer.py
  topic_detector.py
  rule_extractor.py
  example_extractor.py
  opinion_extractor.py
  construction_mapper.py
  validators.py
  exporter.py
  cli.py
src/grammar_kb/                      — KB models لِلاسِتعلام
  models.py
  schema.py
  query.py
tests/                               — pytest
```

## CLI

```
python -m src.maani_alnahw.cli split-pages \
    --input data/raw/maani_alnahw \
    --output data/processed/maani_alnahw/pages.jsonl

python -m src.maani_alnahw.cli normalize \
    --input data/processed/maani_alnahw/pages.jsonl \
    --output data/processed/maani_alnahw/cleaned_pages.jsonl

python -m src.maani_alnahw.cli detect-topics \
    --input data/processed/maani_alnahw/cleaned_pages.jsonl \
    --output data/processed/maani_alnahw/topics.jsonl

python -m src.maani_alnahw.cli extract-rules \
    --pages data/processed/maani_alnahw/cleaned_pages.jsonl \
    --topics data/processed/maani_alnahw/topics.jsonl \
    --output data/processed/maani_alnahw/rule_cards.jsonl

python -m src.maani_alnahw.cli extract-examples \
    --pages data/processed/maani_alnahw/cleaned_pages.jsonl \
    --rules data/processed/maani_alnahw/rule_cards.jsonl \
    --output data/processed/maani_alnahw/examples.jsonl

python -m src.maani_alnahw.cli build-constructions \
    --rules data/processed/maani_alnahw/rule_cards.jsonl \
    --output data/processed/maani_alnahw/construction_rules.jsonl

python -m src.maani_alnahw.cli report \
    --processed data/processed/maani_alnahw \
    --output data/processed/maani_alnahw/extraction_report.md
```

أَو الكُلّ في خَطوَة واحِدَة:
```
python -m src.maani_alnahw.cli all
```

## مَبادِئ مُهِمَّة

1. لا تَستخرِج قاعِدَة قَبل OCR normalization.
2. لا تَثِق بِتَصحيح آليّ ثِقَتُه < 0.85 — سَجِّلها كـ `suggest_only`.
3. خَزِّن الصَّفحَة + الجُزء دائمًا.
4. كُلّ قاعِدَة لها `confidence` و `author_position`.
5. لا تَجعَل «حُروف الجَرّ يَنوب بَعضُها عَن بَعض» قاعِدَة مُطلَقَة — افحَص التَّضمين.
6. لا تَجعَل «ظَنّ + أَنّ = يَقين» قاعِدَة مُطلَقَة — اجعَلها قَرينَة.
7. لا تَجعَل «أَرَأَيتَكُم» دائِمًا فِعل رُؤيَة — افحَص استخبار.
