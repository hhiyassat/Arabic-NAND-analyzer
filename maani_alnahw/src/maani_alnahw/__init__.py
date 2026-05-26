"""maani_alnahw — استخراج قاعِدَة مَعرِفَة نَحويَّة دَلاليَّة مِن «مَعاني النَّحو».

المُكَوِّنات:
  • page_splitter — تَقسيم الصَّفحات مِن ملفّات OCR
  • ocr_normalizer — تَصحيح أَخطاء OCR (static + heuristic)
  • topic_detector — كَشف الأَبواب
  • rule_extractor — استخراج بطاقات القَواعِد
  • example_extractor — استخراج الأَمثلة والآيات
  • opinion_extractor — استخراج الخِلاف وَ التَّرجيح
  • construction_mapper — تَحويل القَواعِد إلى صيغَة قابِلَة لِلتَّحليل
  • validators — التَّحَقُّق
  • exporter — التَّصدير وَ التَّقارير
  • cli — واجِهَة سَطر الأَوامِر
"""

__version__ = "0.1.0"
