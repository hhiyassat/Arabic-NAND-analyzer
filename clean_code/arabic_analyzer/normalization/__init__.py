"""arabic_analyzer.normalization — تَطبيع النَّصّ (wrapper، لا منطق جَديد)."""
from .normalize import (
    strip_diacritics, strip_all_marks,
    normalize_light, normalize_strong,
)

__all__ = ["strip_diacritics", "strip_all_marks",
           "normalize_light", "normalize_strong"]
