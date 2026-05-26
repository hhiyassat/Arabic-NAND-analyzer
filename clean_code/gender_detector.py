"""gender_detector.py — كَشف الجِنس بِتَرتيب أَدِلَّة (Feature Resolution).

طَبَقَة فَوق الـ Morphology وتَحت الـ Syntax. تُمَيِّز 5 أَنواع جِنس:
  • LEXICAL — جِنس اللَّفظ (morphological)
  • SEMANTIC — جِنس المَرجِع (الذَّكَر/الأُنثى الحَقيقيّ)
  • AGREEMENT — جِنس المُطابَقَة (مِن السِّياق)
  • ADDRESSEE — جِنس المُخاطَب (مِن ضَمائر الخِطاب)
  • COUNTED — جِنس المَعدود (في باب العَدَد)

تَرتيب الأَدِلَّة (الأَقوى أَوَّلًا):
  1. ضَمير صَريح (هي، ها)
  2. تَصريف فِعل (كَتَبَت)
  3. اسم إِشارَة/مَوصول (الَّتي، هذه)
  4. مُطابَقَة نَحويَّة (شَمسٌ مُشرِقَة)
  5. مُعجَم (أَرض، شَمس)
  6. عَلامَة صَرفيَّة (ـة، ـات، فَعلاء)
  7. وَزن (فَاعِلَة)
  8. افتراض (M.default، ثِقَة مُنخَفِضَة)

كُلّ نَتيجَة تَحمِل:
  • gender + confidence + evidence list + warning عِندَ التَّعارُض
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "GenderDetector:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return s


@dataclass
class GenderResult:
    """نَتيجَة كَشف الجِنس لِكَلِمَة."""
    token: str = ""
    canonical: str = ""
    gender: str = ""              # M / F / X / M_grammatical / M_or_mixed
    confidence: float = 0.0       # 0.0 - 1.0
    evidence: list = field(default_factory=list)  # list[str]
    source: str = ""              # lexicon / morphology / pronoun / verb / agreement / demonstrative
    warnings: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "canonical": self.canonical,
            "gender": self.gender,
            "confidence": round(self.confidence, 2),
            "evidence": list(self.evidence),
            "source": self.source,
            "warnings": list(self.warnings),
            "alternatives": list(self.alternatives),
            "contract": self.contract,
        }


@dataclass
class DemonstrativeDecomposition:
    """تَفكيك اسم الإِشارَة المُلتَصِق بِضَمير المُخاطَب (ذلكم، تلكم، ...)."""
    surface: str = ""
    referent_form: str = ""
    referent_gender: str = ""
    referent_number: str = ""
    addressee_suffix: str = ""
    addressee_person: str = ""
    addressee_gender: str = ""
    addressee_number: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "surface": self.surface,
            "referent_part": {
                "form": self.referent_form,
                "gender": self.referent_gender,
                "number": self.referent_number,
                "refers_to": "context_or_previous_clause",
            },
            "addressee_part": {
                "form": self.addressee_suffix,
                "person": self.addressee_person,
                "gender": self.addressee_gender,
                "number": self.addressee_number,
            } if self.addressee_suffix else None,
            "warning": self.note or "",
        }


class GenderDetector:

    def __init__(self):
        # المُعجَم: form → (gender, kind)
        self._inherent: dict[str, dict] = {}
        for r in _load_rows("inherent_gender_lexicon.csv", subdir="lists"):
            canon = _normalize(r.get("form", ""))
            if canon:
                self._inherent[canon] = r

        # أَنماط مَورفولوجيَّة
        self._morph_patterns = _load_rows("gender_morphology_patterns.csv")

        # تَفكيك أَسماء الإِشارَة المُرَكَّبَة
        self._demonstratives: dict[str, dict] = {}
        for r in _load_rows("demonstrative_decomposition.csv", subdir="lists"):
            canon = _normalize(r.get("form", ""))
            if canon:
                self._demonstratives[canon] = r

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def detect(self, token: str, *, wazn: str = "", word_class: str = "",
               context_agreement: Optional[str] = None) -> GenderResult:
        """يَكشِف جِنس الـ token بِتَرتيب الأَدِلَّة.

        context_agreement: لَو وُجِدَ، يَستَخدِم المُطابَقَة كَ دَليل أَقوى.
        """
        plain = _normalize(token)
        result = GenderResult(token=token, canonical=plain)

        # 1. اسم إِشارَة مُرَكَّب (ذلكم، تلكم، ...) — أَعلى أَولَوِيَّة لِأَنّه يَتَطَلَّب تَفكيك
        decomp = self._demonstratives.get(plain)
        if decomp:
            result.source = "demonstrative_decomposition"
            result.gender = decomp.get("referent_gender", "")
            result.confidence = 0.95
            result.evidence.append(
                f"demonstrative_referent={decomp.get('referent_form', '')}"
                f"({decomp.get('referent_gender', '')}.{decomp.get('referent_number', '')})"
            )
            if decomp.get("addressee_suffix"):
                result.evidence.append(
                    f"addressee_suffix={decomp.get('addressee_suffix', '')}"
                    f"({decomp.get('addressee_gender', '')}.{decomp.get('addressee_number', '')})"
                )
                result.warnings.append(
                    f"المُشار إِليه {decomp.get('referent_gender', '')}.{decomp.get('referent_number', '')}، "
                    f"المُخاطَب {decomp.get('addressee_gender', '')}.{decomp.get('addressee_number', '')} — لا يُختَلَط بَينهما"
                )
            return result

        # 2. مُطابَقَة نَحويَّة (لَو مُرِّرَت)
        if context_agreement:
            result.source = "agreement"
            result.gender = context_agreement
            result.confidence = 0.95
            result.evidence.append(f"agreement_context:{context_agreement}")
            return result

        # 3. المُعجَم (سَماعيّ + استثناءات)
        # نُجَرِّب الـ token كَما هو
        for try_key in (plain, plain.replace("ال", "", 1) if plain.startswith("ال") else plain):
            if try_key in self._inherent:
                row = self._inherent[try_key]
                result.source = "lexicon"
                result.gender = row.get("gender", "")
                result.confidence = 0.9
                result.evidence.append(
                    f"inherent_lexicon:{try_key} ({row.get('kind', '')})"
                )
                return result

        # 4. عَلامات صَرفيَّة + أَوزان
        # نَفحَص ـة (إِن لَم تَكُن في استثناءات)
        for rule in self._morph_patterns:
            pattern = rule.get("pattern", "")
            gender = rule.get("gender", "")
            conf = float(rule.get("confidence", "0.5") or "0.5")
            name = rule.get("name", "")

            matched = False
            if pattern.startswith("ends_with:"):
                suffix = pattern[len("ends_with:"):]
                if plain.endswith(suffix):
                    matched = True
            elif pattern.startswith("wazn_match:"):
                target = pattern[len("wazn_match:"):]
                target_plain = _normalize(target)
                if wazn and _normalize(wazn) == target_plain:
                    matched = True

            if matched:
                result.source = "morphology"
                result.gender = gender
                result.confidence = conf
                result.evidence.append(f"pattern:{name} → {pattern}")
                # لا نَرجِع فَورًا — قَد يَكون هُناك pattern أَدَقّ أَو استثناء
                # نُكمِل لِتَجميع البَدائل
                break  # أَوَّل تَطابُق (الأَوزان مُرَتَّبَة بِالأَولَوِيَّة)

        # 5. تَحَقُّق مِن استثناءات «ة + اسم عَلَم رَجُل» (حَمزَة، طَلحَة)
        if result.gender == "F" and result.source == "morphology" and plain in self._inherent:
            # تَمَّ التَّحَقُّق في المُعجَم — هذا fallback إِن لَم يُكتَشَف
            pass

        # 6. افتراض: M.default بِثِقَة مُنخَفِضَة
        if not result.gender:
            result.source = "default"
            result.gender = "M"
            result.confidence = 0.3
            result.evidence.append("default_masculine_fallback")
            result.warnings.append("لا دَليل قَطعيّ — افتراض M بِثِقَة مُنخَفِضَة")

        return result

    def decompose_demonstrative(self, token: str) -> Optional[DemonstrativeDecomposition]:
        plain = _normalize(token)
        row = self._demonstratives.get(plain)
        if not row:
            return None
        return DemonstrativeDecomposition(
            surface=token,
            referent_form=row.get("referent_form", ""),
            referent_gender=row.get("referent_gender", ""),
            referent_number=row.get("referent_number", ""),
            addressee_suffix=row.get("addressee_suffix", ""),
            addressee_person=row.get("addressee_person", ""),
            addressee_gender=row.get("addressee_gender", ""),
            addressee_number=row.get("addressee_number", ""),
            note=row.get("note", ""),
        )


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    d = GenderDetector()
    tests = [
        ("أَرضٌ", "", "", "F"),          # سَماعيّ
        ("شَمسٌ", "", "", "F"),          # سَماعيّ
        ("نارٌ", "", "", "F"),
        ("قَمَرٌ", "", "", "M"),
        ("كاتِبَةٌ", "", "", "F"),       # ـة
        ("حَمزَةٌ", "", "", "M"),        # استثناء
        ("طَلحَةُ", "", "", "M"),
        ("مُصطَفى", "", "", "M"),        # استثناء أَلِف مَقصورَة
        ("كُبرى", "", "", "F"),          # أَلِف مَقصورَة F
        ("صَحراء", "", "", "F"),         # أَلِف مَمدودَة
        ("ماء", "", "", "M"),            # استثناء
        ("ذلكم", "", "", "M"),           # المُشار إِليه M (والمُخاطَب M.PL)
        ("تلكم", "", "", "F"),
        ("ذلك", "", "", "M"),
        ("تلك", "", "", "F"),
        ("الَّتي", "", "", "F"),         # يَحتاج إِضافَتها لِلمُعجَم — حاليًّا default
        ("كاتِب", "كاتِب", "", "M"),
        ("كاتِبَة", "كاتِبَة", "", "F"),
    ]
    ok = 0
    print(f"contract: {CONTRACT_NAME}")
    print(f"inherent loaded: {len(d._inherent)}")
    print(f"demonstratives loaded: {len(d._demonstratives)}")
    print(f"morph patterns: {len(d._morph_patterns)}")
    print()
    for word, wazn, wc, expected in tests:
        r = d.detect(word, wazn=wazn, word_class=wc)
        mark = "✓" if r.gender == expected else "✗"
        if r.gender == expected:
            ok += 1
        print(f"  {mark} {word:<14}  → {r.gender}  ({r.source}, conf={r.confidence})  "
              f"expected={expected}")
    print(f"\n{ok}/{len(tests)} ✓")
