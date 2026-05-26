"""living_root_contract.py — قاعدة الجذر الفعلي.

Per 14_Minimal_Complete_Theory: every linguistic rule must be a named
contract with an explicit source. This contract replaces the inline
verbal_roots check that used to live in root_pipeline.

القاعدة:
  جذر له فعل (PV/IV/CV) في MASAQ → الجذر إنتاجيّ
  جذر بلا فعل في MASAQ          → جذر اسمي (جامد حقيقي)

تَستخدمه root_pipeline لِتَمييز:
  - كتاب (جذر كتب له فعل) → مشتق محسوس
  - الأرض (جذر أرض بلا فعل) → جامد حقيقي
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from wazn_data import load_verbal_roots_from_masaq, DIACRITICS


CONTRACT_NAME = "LivingRootContract:v1"
DATA_SOURCE = "MASAQ.csv:Morph_Tag in {PV,IV,CV,PV_PASS,IV_PASS,CV_PASS}"


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in DIACRITICS)


class LivingRootContract:
    """Determines whether a root has a living verb in MASAQ."""

    def __init__(self) -> None:
        self._roots = load_verbal_roots_from_masaq()

    def is_living(self, root: str) -> bool:
        """True if the root has any verbal form (PV/IV/CV) in MASAQ."""
        return _strip_diac(root) in self._roots

    def source(self) -> str:
        return CONTRACT_NAME

    def data_source(self) -> str:
        return DATA_SOURCE

    def size(self) -> int:
        return len(self._roots)


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = LivingRootContract()
    print(f"contract: {c.source()}")
    print(f"source:   {c.data_source()}")
    print(f"loaded:   {c.size()} verbal roots")
    print()
    tests = {
        "كتب": "كتاب — مشتق متوقَّع",
        "درس": "مدرسة — مشتق متوقَّع",
        "سما": "السماء — له فعل سَمَا في القرآن",
        "أرض": "الأرض — لا فعل",
        "حجر": "الحجر — لا فعل",
        "نزل": "نَزَل — له فعل",
    }
    for root, desc in tests.items():
        living = c.is_living(root)
        mark = "✓ حيّ" if living else "✗ ميّت"
        print(f"  {root:<8} {mark:<10} ({desc})")
