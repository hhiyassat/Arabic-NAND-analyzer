"""samarrai_loaders — مُحَمِّلات مَعاني النَّحو لِلسامرَّائيّ.

كُلّ مُجَلَّد لَه loader مُستَقِلّ يَقرَأ CSVs دَستوريَّة (لا inline data).
الـ schema المُوَحَّد في `data/contracts/maani/schema.md`.

المُجَلَّدات الأَربَعَة:
  • volume1_loader — المَعارِف + الإِسناد (الضَّمائر + الإِشارَة + الـ + المَوصول + المُبتَدَأ/الخَبَر)
  • volume2_loader — الأَفعال + المَفاعيل (ظَنَّ + الفاعِل + المَفعول + المُطلَق + الظَّرف)
  • volume3_loader — حُروف الجَرّ + التَّضمين (17 حَرف جَرّ + قاعِدَة التَّضمين)
  • volume4_loader — الجَزم + الشَّرط + التَّوكيد + القَسَم + التَّقديم
"""

from . import volume1_loader, volume2_loader, volume3_loader, volume4_loader

__all__ = ["volume1_loader", "volume2_loader", "volume3_loader", "volume4_loader"]
