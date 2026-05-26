"""number_detector.py — كَشف العَدَد (SG/DU/PL) مَع تَمييز جَمع المُذَكَّر السالِم
مِن المُثَنّى، وَ-جَمع التَّكسير.

تَرتيب الأَدِلَّة:
  1. مُعجَم (rural/قَلوب → PL مَحفوظ)
  2. عَلامات سالِمَة: ـون (PL.رَفع)، ـين (PL.نَصب/جَرّ OR DU.نَصب/جَرّ — يَحتاج case)
  3. عَلامات مُؤَنَّث سالِم: ـات → PL.F
  4. عَلامَة مُثَنّى: ـان (DU.رَفع)، ـين (DU.نَصب/جَرّ)
  5. أَوزان جَمع التَّكسير (broken_plural_patterns.csv)
  6. افتراض: SG
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "NumberDetector:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return s


@dataclass
class NumberResult:
    token: str = ""
    canonical: str = ""
    number: str = ""              # SG / DU / PL
    confidence: float = 0.0
    evidence: list = field(default_factory=list)
    source: str = ""              # lexicon / suffix / wazn / default
    warnings: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "canonical": self.canonical,
            "number": self.number,
            "confidence": round(self.confidence, 2),
            "evidence": list(self.evidence),
            "source": self.source,
            "warnings": list(self.warnings),
            "alternatives": list(self.alternatives),
            "contract": self.contract,
        }


class NumberDetector:

    def __init__(self):
        # المُعجَم لِجَمع التَّكسير
        self._lex: dict[str, dict] = {}
        for r in _load_rows("inherent_gender_lexicon.csv", subdir="lists"):
            canon = _normalize(r.get("form", ""))
            kind = r.get("kind", "")
            if canon and "plural" in kind:
                self._lex[canon] = r
        self._broken_patterns = _load_rows("broken_plural_patterns.csv")

    def detect(self, token: str, *, wazn: str = "", case: str = "") -> NumberResult:
        """case: 'nominative' / 'accusative' / 'genitive' / '' — يُساعِد تَمييز
        ـين (مُثَنّى نَصب/جَرّ vs جَمع مُذَكَّر سالِم نَصب/جَرّ)."""
        plain = _normalize(token)
        result = NumberResult(token=token, canonical=plain)

        # 1. مُعجَم جَمع تَكسير
        if plain in self._lex:
            result.source = "lexicon"
            result.number = "PL"
            result.confidence = 0.95
            result.evidence.append(f"broken_plural_lexicon:{plain}")
            return result

        # 2. ـات → جَمع مُؤَنَّث سالِم
        if plain.endswith("ات") and len(plain) > 3:
            result.source = "suffix"
            result.number = "PL"
            result.confidence = 0.9
            result.evidence.append("sound_feminine_plural:ـات")
            return result

        # 3. ـون → جَمع مُذَكَّر سالِم في الرَّفع
        if plain.endswith("ون") and len(plain) > 3:
            result.source = "suffix"
            result.number = "PL"
            result.confidence = 0.9
            result.evidence.append("sound_masculine_plural_nominative:ـون")
            return result

        # 4. ـان (DU في الرَّفع)
        if plain.endswith("ان") and len(plain) > 3:
            if case == "nominative":
                result.source = "suffix"
                result.number = "DU"
                result.confidence = 0.9
                result.evidence.append("dual_nominative:ـان")
            else:
                result.source = "suffix"
                result.number = "DU"
                result.confidence = 0.6
                result.evidence.append("dual_nominative_or_other:ـان")
                result.warnings.append("بِلا case، نَفترض DU")
            return result

        # 5. ـين (DU.نَصب/جَرّ أَو PL.مُذَكَّر سالِم.نَصب/جَرّ)
        if plain.endswith("ين") and len(plain) > 3:
            if case in ("accusative", "genitive"):
                result.source = "suffix"
                result.number = "DU_or_PL"  # غامِض
                result.confidence = 0.5
                result.evidence.append(f"ambiguous_dual_or_plural_oblique:ـين (case={case})")
                result.alternatives.append({"number": "DU", "reason": "مُثَنّى نَصب/جَرّ"})
                result.alternatives.append({"number": "PL", "reason": "جَمع مُذَكَّر سالِم نَصب/جَرّ"})
                result.warnings.append("ـين تَحتَمِل المُثَنّى وجَمع المُذَكَّر السالِم")
            else:
                result.source = "suffix"
                result.number = "DU_or_PL"
                result.confidence = 0.4
                result.evidence.append("ambiguous_dual_or_plural:ـين")
            return result

        # 6. أَوزان جَمع التَّكسير
        if wazn:
            wazn_plain = _normalize(wazn)
            for rule in self._broken_patterns:
                pattern = _normalize(rule.get("wazn_pattern", ""))
                if pattern and wazn_plain == pattern:
                    result.source = "wazn"
                    result.number = "PL"
                    result.confidence = 0.85
                    result.evidence.append(
                        f"broken_plural_wazn:{rule.get('name','')}:{pattern}"
                    )
                    return result

        # 7. افتراض: SG
        result.source = "default"
        result.number = "SG"
        result.confidence = 0.5
        result.evidence.append("default_singular")
        return result


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    d = NumberDetector()
    tests = [
        ("كِتاب", "", "", "SG"),
        ("كُتُب", "فُعُل", "", "SG"),  # لَيس في pattern
        ("رِجال", "", "", "PL"),       # مُعجَم
        ("مُؤمِنون", "", "", "PL"),    # ـون
        ("مُؤمِنين", "", "accusative", "DU_or_PL"),  # غامِض
        ("ٱلَّذِينَ", "", "", "DU_or_PL"),  # ـين
        ("رَجُلان", "", "nominative", "DU"),
        ("امرَأَتان", "", "nominative", "DU"),
        ("آيات", "", "", "PL"),
        ("قُلوب", "فُعول", "", "PL"),   # وَزن
        ("قُلوب", "", "", "PL"),         # مُعجَم
    ]
    print(f"contract: {CONTRACT_NAME}")
    print(f"lexicon: {len(d._lex)}, patterns: {len(d._broken_patterns)}")
    print()
    ok = 0
    for word, wazn, case, expected in tests:
        r = d.detect(word, wazn=wazn, case=case)
        mark = "✓" if r.number == expected else "✗"
        if r.number == expected:
            ok += 1
        print(f"  {mark} {word:<12}  → {r.number}  ({r.source}, conf={r.confidence}, case={case})  exp={expected}")
    print(f"\n{ok}/{len(tests)} ✓")
