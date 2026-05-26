# Archive — ملفات قديمة مُحفوظة للمرجعية

هذا المجلّد يحوي الملفات التي لم تَعُد جزءًا من البنية الفاعلة في المشروع
لكنّها مرجع تاريخي لمسار التطوّر.

## البنية

- **legacy_code/** (232K) — وحدات Python مُجمَّدة استُبدِلت رسميًّا:
  - wazn_matcher.py / _legacy.py — استبدلتها root_by_alignment
  - wazn_matcher_v3.py / _legacy.py — مُجمَّد رسميًّا
  - root_extractor.py / root_verifier.py — استبدلهما root_by_alignment
  - FREEZE_v2.4.md — وثيقة تجميد v2.4
  - golden_name_base.csv / huruf_muqattaa.csv — بيانات معجمية غير مستخدمة

- **legacy_data/** (52M) — نسخ احتياطية وبيانات اختبار قديمة:
  - MEEMAR_v1_pre_extractor.csv — نسخة pre-v3 من MEEMAR
  - MASAQ.csv.bak — backup قبل إصلاحات MASAQ
  - MEEMAR_test*.csv — عيّنات اختبار قديمة
  - MEEMAR_roots_needing_audit.csv — تقرير audit قديم

- **legacy_scripts/** (212K) — 15 سكربت تشغيل-مرّة-واحدة:
  - استخراج/إصلاح MASAQ
  - eval لـ analyzer_v2 و segmenter القديم
  - بناء MEEMAR قبل v3
  - مقارنات سابقة

- **legacy_src/** (748K) — حقبة قبل clean_code:
  - architecture_test/ — أوّل نسخة من المعمار (sample_01.py + adapters)
  - clean_code/ القديم — نسخة مُهجَرة
  - run_architecture_test_sample_01.py

- **legacy_output/** (80K) — مخرجات اختبارات 17 مايو (test_yawm_shahr.txt …)

- **legacy_reports/** (116K) — 14 تقرير + اختبار معطّل:
  - بناء MEEMAR (Tier 1, Tier 2)
  - مقارنات MEEMAR vs i3rab
  - تقارير Segmenter و Mishkat audit
  - WAZN_MATCHER_V3 final report
  - HANDOFF_ADDENDUM_2026-05-18
  - test_analyze_clean_code_text.py (يختبر سكربتًا في legacy_scripts)

## ملاحظة

كل ما هنا تمّ تجميده ولا يجب تعديله. للأسئلة عن المسار التاريخي:
ابدأ من هذا الـ README ثم اقرأ التقرير المعنيّ في legacy_reports/.

لاستعادة أيّ ملف:
```bash
mv archive/<category>/<file> <destination>
```
