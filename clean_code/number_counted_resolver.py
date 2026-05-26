"""number_counted_resolver.py — طَبَقَة العَدَد والمَعدود.

يَستَخرِج عَلاقَة Number-Counted مِن النَّصّ، يَستَنتِج جِنس المَعدود مِن
مُفرَدِه (لا مِن الجَمع)، يَتَحَقَّق مِن المُطابَقَة، ويُفَرِّق:
  • العَدَد النَّحويّ (SG/DU/PL)
  • العَدَد الحِسابيّ (1، 2، ...)
  • جِنس المَعدود (مِن المُفرَد)
  • Surface vs Semantic number («عِشرون رَجُلًا» — رَجُلًا SG لَفظًا، الكِيان PL=20 دَلاليًّا)

كُلّ العَلاقات data-driven مِن:
  • cardinal_numbers.csv — كَلِمات العَدَد + قيمَتها + class + gender_form
  • number_counted_agreement.csv — قَواعِد المُطابَقَة لِكُلّ class
  • inherent_gender_lexicon.csv — مَع broken_plural_lexicon لِاستِخراج المُفرَد
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows
from gender_detector import GenderDetector
from number_detector import NumberDetector


CONTRACT_NAME = "NumberCountedResolver:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


def _normalize(s: str) -> str:
    s = _strip_diac(s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي")
    return s


@dataclass
class CountedEntity:
    surface: str = ""
    singular: str = ""          # المُفرَد المُستَنتَج (kitab مِن kutub)
    singular_gender: str = ""   # M / F (مِن المُفرَد)
    surface_number: str = ""    # SG / DU / PL — الشَّكل النَّحويّ
    case_role: str = ""         # tamyiz / mudaf_ilayh / nominative_apposition
    source_of_singular: str = ""


@dataclass
class NumberStructure:
    surface: str = ""
    value: int = 0
    number_class: str = ""      # unit_1_2 / unit_3_10 / teens_11_12 / teens_13_19 / tens / compound_21_22 / compound_23_99 / hundred / thousand
    gender_form: str = ""       # M_with_ta / F_without_ta / invariable / M / F


@dataclass
class NumberCountedPhrase:
    span: str = ""
    numeric_value: int = 0
    structure: list = field(default_factory=list)   # list[NumberStructure]
    counted: Optional[CountedEntity] = None
    semantic_quantity: int = 0
    semantic_number: str = ""    # SG / PL / DU
    agreement_status: str = ""   # valid / mismatch / no_check / hierarchical
    agreement_evidence: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    contract: str = CONTRACT_NAME
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "span": self.span,
            "type": "NUMBER_COUNTED_PHRASE",
            "numeric_value": self.numeric_value,
            "structure": [
                {
                    "surface": s.surface,
                    "value": s.value,
                    "number_class": s.number_class,
                    "gender_form": s.gender_form,
                }
                for s in self.structure
            ],
            "counted": (
                {
                    "surface": self.counted.surface,
                    "singular": self.counted.singular,
                    "singular_gender": self.counted.singular_gender,
                    "surface_number": self.counted.surface_number,
                    "case_role": self.counted.case_role,
                    "source": self.counted.source_of_singular,
                }
                if self.counted else None
            ),
            "semantic_entity": {
                "quantity": self.semantic_quantity,
                "semantic_number": self.semantic_number,
            },
            "agreement_check": {
                "status": self.agreement_status,
                "evidence": list(self.agreement_evidence),
            },
            "warnings": list(self.warnings),
            "confidence": round(self.confidence, 2),
            "contract": self.contract,
        }


# مُعجَم استِنتاج المُفرَد مِن الجَمع — مَحمول مِن broken_plural_lexicon.csv
# (CONSTITUTIONAL: لا قَوائم inline)
def _load_broken_plural_lexicon() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for r in _load_rows("broken_plural_lexicon.csv", subdir="lists"):
        pl = _normalize(r.get("plural", ""))
        sg = (r.get("singular") or "").strip()
        gd = (r.get("gender") or "").strip().upper()
        if pl and sg and gd in ("M", "F"):
            out[pl] = (sg, gd)
    return out


BROKEN_PLURAL_TO_SINGULAR = _load_broken_plural_lexicon()


class NumberCountedResolver:

    def __init__(self):
        # كَلِمات العَدَد
        self._numbers: dict[str, dict] = {}
        for r in _load_rows("cardinal_numbers.csv", subdir="lists"):
            plain = _normalize(r.get("form", ""))
            if plain:
                self._numbers[plain] = r
        # قَواعِد المُطابَقَة
        self._agreement_rules: dict[str, dict] = {}
        for r in _load_rows("number_counted_agreement.csv"):
            cls = (r.get("number_class") or "").strip()
            if cls:
                self._agreement_rules[cls] = r
        self._gender_det = GenderDetector()
        self._number_det = NumberDetector()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def _lookup_number(self, token: str) -> Optional[dict]:
        plain = _normalize(token)
        if plain in self._numbers:
            return self._numbers[plain]
        # نُجَرِّب نَزع و/ف/ل
        for prefix in ("و", "ف", "ل"):
            if plain.startswith(prefix):
                rest = plain[len(prefix):]
                if rest in self._numbers:
                    return self._numbers[rest]
        return None

    def _infer_singular(self, surface: str) -> tuple[str, str, str]:
        """يَستَنتِج المُفرَد + جِنسه + مَصدَر الِاستنتاج."""
        plain = _normalize(surface)
        # 1. لَو مَوجود في الـ broken plural lexicon
        if plain in BROKEN_PLURAL_TO_SINGULAR:
            sg, gender = BROKEN_PLURAL_TO_SINGULAR[plain]
            return sg, gender, "broken_plural_lexicon"
        # 2. لَو مُؤَنَّث سالِم ـات: نُحاوِل نَزع ـات + إِضافَة ـة
        if plain.endswith("ات") and len(plain) > 3:
            sg = plain[:-2] + "ة"
            return sg, "F", "sound_feminine_plural_pattern"
        # 3. لَو مُذَكَّر سالِم ـون/ـين
        if plain.endswith("ون") or plain.endswith("ين"):
            sg = plain[:-2]
            return sg, "M", "sound_masculine_plural_pattern"
        # 4. لَو السَّطح بِالفِعل مُفرَد، نَتَفَحَّص جِنسه
        gr = self._gender_det.detect(surface)
        return plain, gr.gender or "M", "surface_singular"

    def _classify_agreement(self, number_value: int) -> str:
        """يُصَنِّف قيمَة العَدَد لِمَعرِفَة قاعِدَة المُطابَقَة."""
        if number_value in (1, 2):
            return "unit_1_2"
        if 3 <= number_value <= 10:
            return "unit_3_10"
        if number_value in (11, 12):
            return "teens_11_12"
        if 13 <= number_value <= 19:
            return "teens_13_19"
        if number_value in (20, 30, 40, 50, 60, 70, 80, 90):
            return "tens"
        if number_value == 100 or number_value == 200:
            return "hundred"
        if number_value == 1000 or number_value == 2000:
            return "thousand"
        if 21 <= number_value <= 22:
            return "compound_21_22"
        if 23 <= number_value <= 99:
            return "compound_23_99"
        if number_value >= 100:
            return "hundred_or_compound"
        return "unknown"

    def detect_in_tokens(self, tokens: list[str]) -> list[NumberCountedPhrase]:
        """يَبحَث عَن تَراكيب عَدَد+مَعدود في قائِمَة tokens."""
        results: list[NumberCountedPhrase] = []
        i = 0
        while i < len(tokens):
            num_row = self._lookup_number(tokens[i])
            if not num_row:
                i += 1
                continue

            # وَجَدنا عَدَدًا. هَل قَبلَه «و» تَدُلّ على مُرَكَّب؟
            structure_tokens: list[int] = [i]
            structure_rows: list[dict] = [num_row]
            j = i + 1
            # نَتَجاوَز كَلِمَة عَدَد إِضافيَّة (لِمُرَكَّبات «أَحَد عَشَر»، «خَمسة عَشَر»، «وعِشرون»)
            while j < len(tokens):
                # تَحَقُّق مِن مُرَكَّب: العَدَد الحالي يَتبَع بِعَدَد آخَر (مَثل عَشَر/عَشرون)
                nxt = self._lookup_number(tokens[j])
                if not nxt:
                    # تَحَقُّق مِن «و» الرَّابِطَة بَين الآحاد والعُقود (واحد + وَ + عِشرون)
                    if _normalize(tokens[j]).startswith("و"):
                        rest = _normalize(tokens[j])[1:]
                        if rest in self._numbers:
                            structure_tokens.append(j)
                            structure_rows.append(self._numbers[rest])
                            j += 1
                            continue
                    break
                structure_tokens.append(j)
                structure_rows.append(nxt)
                j += 1
                if len(structure_tokens) >= 4:
                    break  # أَقصى عَدَد مُرَكَّب

            # احسِب القيمَة الإِجماليَّة
            total_value = 0
            for r in structure_rows:
                try:
                    v = int(r.get("value", "0"))
                    total_value += v
                except Exception:
                    pass

            # المَعدود = الـ token التالي بَعد كُلّ كَلِمات العَدَد
            counted_idx = j
            counted: Optional[CountedEntity] = None
            if counted_idx < len(tokens):
                ct = tokens[counted_idx]
                sg, gender, src = self._infer_singular(ct)
                # عَدَد سَطحيّ
                nd = self._number_det.detect(ct)
                counted = CountedEntity(
                    surface=ct,
                    singular=sg,
                    singular_gender=gender,
                    surface_number=nd.number,
                    case_role="auto",
                    source_of_singular=src,
                )

            # صَنِّف العَدَد
            agreement_class = self._classify_agreement(total_value)
            rule = self._agreement_rules.get(agreement_class, {})

            # تَحَقُّق المُطابَقَة
            status = "no_check"
            evidence = []
            if counted and counted.singular_gender and structure_rows:
                # نُقارِن صيغَة العَدَد بِجِنس المُفرَد
                first_num = structure_rows[0]
                gf = first_num.get("gender_form", "")
                csg = counted.singular_gender
                if agreement_class == "unit_3_10":
                    # المُخالَفَة: M_with_ta لِمَعدود M، F_without_ta لِمَعدود F
                    if (gf == "M_with_ta" and csg == "M") or (gf == "F_without_ta" and csg == "F"):
                        status = "valid"
                        evidence.append(
                            f"3-10 rule: عَدَد {first_num.get('form','')} ({gf}) "
                            f"يُخالِف مَعدود {counted.singular} ({csg}) ✓"
                        )
                    else:
                        status = "mismatch"
                        evidence.append(
                            f"3-10 rule violated: عَدَد {first_num.get('form','')} ({gf}) "
                            f"لا يُخالِف مَعدود {counted.singular} ({csg}) ✗"
                        )
                elif agreement_class in ("teens_11_12", "compound_21_22"):
                    # المُوافَقَة
                    if (gf == "M" and csg == "M") or (gf == "F" and csg == "F"):
                        status = "valid"
                        evidence.append(f"agreement: {gf} matches counted {csg} ✓")
                    else:
                        status = "mismatch"
                        evidence.append(f"agreement violated: {gf} vs {csg} ✗")
                elif agreement_class == "tens":
                    status = "valid"
                    evidence.append(f"tens are invariable; no gender check")
                elif agreement_class in ("hundred", "thousand"):
                    status = "no_gender_relation"
                    evidence.append(f"100/1000 no direct gender relation")

            # semantic
            semantic_number = "PL" if total_value >= 3 else ("DU" if total_value == 2 else "SG")

            phrase = NumberCountedPhrase(
                span=" ".join(tokens[i:counted_idx + 1] if counted else tokens[i:j]),
                numeric_value=total_value,
                structure=[
                    NumberStructure(
                        surface=r.get("form", ""),
                        value=int(r.get("value", "0") or "0") if r.get("value", "").isdigit() else 0,
                        number_class=r.get("class", ""),
                        gender_form=r.get("gender_form", ""),
                    )
                    for r in structure_rows
                ],
                counted=counted,
                semantic_quantity=total_value,
                semantic_number=semantic_number,
                agreement_status=status,
                agreement_evidence=evidence,
                confidence=0.85 if status == "valid" else 0.6,
            )
            results.append(phrase)
            i = counted_idx + 1 if counted else j

        return results


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    r = NumberCountedResolver()
    print(f"contract: {CONTRACT_NAME}")
    print(f"loaded {len(r._numbers)} number words")
    print(f"loaded {len(r._agreement_rules)} agreement rules")
    print()
    tests = [
        ("ثلاثة رجال", 3, "valid"),
        ("ثلاث نساء", 3, "valid"),
        ("ثلاثة نساء", 3, "mismatch"),     # خَطَأ مُتَعَمَّد
        ("ثلاث رجال", 3, "mismatch"),       # خَطَأ مُتَعَمَّد
        ("خمسة كتب", 5, "valid"),
        ("خمس آيات", 5, "valid"),
        ("عشرة أيام", 10, "valid"),
        ("عشرون رجلًا", 20, "valid"),
        ("مئة سنة", 100, "no_gender_relation"),
    ]
    for text, expected_value, expected_status in tests:
        toks = text.split()
        out = r.detect_in_tokens(toks)
        if not out:
            print(f"  ✗ {text}: لا تَركيب عَدَد")
            continue
        p = out[0]
        ok_v = p.numeric_value == expected_value
        ok_s = p.agreement_status == expected_status
        mark = "✓" if ok_v and ok_s else "✗"
        cg = p.counted.singular_gender if p.counted else "—"
        cs = p.counted.singular if p.counted else "—"
        print(f"  {mark} {text:<22}  value={p.numeric_value}  status={p.agreement_status}  "
              f"counted_sg={cs}({cg})")
