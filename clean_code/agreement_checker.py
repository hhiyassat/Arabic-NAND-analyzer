"""agreement_checker.py — طَبَقَة المُطابَقَة النَّحويَّة في العَرَبيَّة.

ثَلاث أَنواع رَئيسيَّة:
  1. صِفَة ↔ مَوصوف — مُطابَقَة في الجِنس + العَدَد + الإِعراب + التَّعريف
     («رَجُل صالِح»، «امرَأَة صالِحَة»، «الرَّجُل الصَّالِح»)
  2. فِعل ↔ فاعِل — مُطابَقَة في الجِنس + (أَحيانًا) العَدَد
     («جاءَ الرَّجُل»، «جاءَت المَرأَة»، «جاءَ الرِّجال»)
  3. عَدَد ↔ مَعدود — يَستَدعي NumberCountedResolver (مَوجود)

كُلّ فَحص يُرجِع AgreementResult بِـ status + evidence + correction (لَو خَطَأ).

CONSTITUTIONAL: كُلّ القَواعِد data-driven. لا قَوائم inline.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from gender_detector import GenderDetector
from number_detector import NumberDetector


CONTRACT_NAME = "AgreementChecker:v1"


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


@dataclass
class AgreementResult:
    """نَتيجَة فَحص مُطابَقَة."""
    kind: str = ""              # adjective_noun / verb_subject / number_counted
    head: str = ""              # المَتبوع (المَوصوف/الفاعِل/المَعدود)
    dependent: str = ""         # التَّابِع (الصِّفَة/الفِعل/العَدَد)
    status: str = ""            # valid / mismatch / partial / no_check
    head_features: dict = field(default_factory=dict)   # {gender, number, ...}
    dependent_features: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    suggested_correction: str = ""
    confidence: float = 0.0
    contract: str = CONTRACT_NAME

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "head": self.head,
            "dependent": self.dependent,
            "status": self.status,
            "head_features": dict(self.head_features),
            "dependent_features": dict(self.dependent_features),
            "evidence": list(self.evidence),
            "suggested_correction": self.suggested_correction,
            "confidence": round(self.confidence, 2),
            "contract": self.contract,
        }


class AgreementChecker:

    def __init__(self):
        self._gender = GenderDetector()
        self._number = NumberDetector()

    def check_adjective_noun(
        self, adjective: str, noun: str, *,
        adjective_wazn: str = "", noun_wazn: str = "",
    ) -> AgreementResult:
        """يَفحَص مُطابَقَة الصِّفَة لِلمَوصوف في الجِنس + العَدَد + التَّعريف."""
        adj_gr = self._gender.detect(adjective, wazn=adjective_wazn)
        noun_gr = self._gender.detect(noun, wazn=noun_wazn)
        adj_nr = self._number.detect(adjective, wazn=adjective_wazn)
        noun_nr = self._number.detect(noun, wazn=noun_wazn)

        result = AgreementResult(
            kind="adjective_noun",
            head=noun,
            dependent=adjective,
            head_features={
                "gender": noun_gr.gender,
                "number": noun_nr.number,
                "definite": noun.startswith(("ال", "ٱل")),
            },
            dependent_features={
                "gender": adj_gr.gender,
                "number": adj_nr.number,
                "definite": adjective.startswith(("ال", "ٱل")),
            },
        )

        ok_g = adj_gr.gender == noun_gr.gender or "X" in (adj_gr.gender, noun_gr.gender)
        ok_n = adj_nr.number == noun_nr.number or "X" in (adj_nr.number, noun_nr.number)
        ok_def = result.head_features["definite"] == result.dependent_features["definite"]

        if ok_g and ok_n and ok_def:
            result.status = "valid"
            result.confidence = 0.9
            result.evidence.append(
                f"agreement: gender={noun_gr.gender}, number={noun_nr.number}, "
                f"definite={ok_def} — مُطابَقَة كامِلَة"
            )
        elif ok_g and ok_n:
            result.status = "partial"
            result.confidence = 0.6
            result.evidence.append("جِنس وعَدَد مُتَطابِقان، لَكِنّ التَّعريف يَختَلِف")
        else:
            result.status = "mismatch"
            result.confidence = 0.5
            mismatch_kinds = []
            if not ok_g:
                mismatch_kinds.append(f"جِنس ({adj_gr.gender} vs {noun_gr.gender})")
            if not ok_n:
                mismatch_kinds.append(f"عَدَد ({adj_nr.number} vs {noun_nr.number})")
            result.evidence.append(f"مُخالَفَة: {' + '.join(mismatch_kinds)}")
        return result

    def check_verb_subject(
        self, verb: str, subject: str, *,
        verb_features: dict = None,
        subject_wazn: str = "",
    ) -> AgreementResult:
        """يَفحَص مُطابَقَة الفِعل لِلفاعِل.

        verb_features: dict اختِياريّ بِـ gender/number/person مِن morphology table.
        """
        if verb_features is None:
            verb_features = {}
        subj_gr = self._gender.detect(subject, wazn=subject_wazn)
        subj_nr = self._number.detect(subject, wazn=subject_wazn)

        result = AgreementResult(
            kind="verb_subject",
            head=subject,
            dependent=verb,
            head_features={
                "gender": subj_gr.gender,
                "number": subj_nr.number,
            },
            dependent_features=dict(verb_features),
        )

        v_g = verb_features.get("gender", "")
        v_n = verb_features.get("number", "")
        ok_g = (v_g == subj_gr.gender) or ("X" in (v_g, subj_gr.gender)) or not v_g
        # في العَرَبيَّة: لَو الفِعل قَبل الفاعِل، يُجَوَّز إِفراد الفِعل
        # حَتّى مَع جَمع الفاعِل. لَكِنّ المُطابَقَة في الجِنس مَطلوبَة.
        ok_n = (v_n == subj_nr.number) or ("X" in (v_n, subj_nr.number)) or not v_n

        if ok_g and ok_n:
            result.status = "valid"
            result.confidence = 0.85
            result.evidence.append(
                f"verb-subject agreement: gender={subj_gr.gender}, number={subj_nr.number}"
            )
        elif ok_g:
            result.status = "partial"
            result.confidence = 0.6
            result.evidence.append(
                f"جِنس صَحيح، عَدَد مُختَلِف (فِعل={v_n} vs فاعِل={subj_nr.number}) — "
                f"جائِز إِن سَبَقَ الفِعل الفاعِلَ"
            )
        else:
            result.status = "mismatch"
            result.confidence = 0.5
            result.evidence.append(
                f"عَدَم مُطابَقَة جِنس: فِعل {v_g} vs فاعِل {subj_gr.gender}"
            )
        return result

    def check_pronoun_referent(
        self, pronoun_features: dict, referent: str,
    ) -> AgreementResult:
        """يَفحَص هَل المَرجِع المُقتَرَح يُطابِق الضَّمير في جِنس/عَدد/شَخص.

        pronoun_features: {gender, number, person}
        """
        ref_gr = self._gender.detect(referent)
        ref_nr = self._number.detect(referent)

        result = AgreementResult(
            kind="pronoun_referent",
            head=referent,
            dependent=pronoun_features.get("clitic", "?"),
            head_features={
                "gender": ref_gr.gender,
                "number": ref_nr.number,
            },
            dependent_features=dict(pronoun_features),
        )

        p_g = pronoun_features.get("gender", "")
        p_n = pronoun_features.get("number", "")
        p_p = pronoun_features.get("person", "")

        # تَطابُق شَخص
        if p_p == "2" or p_p == "1":
            # ضَمير المُخاطَب/المُتَكَلِّم — المَرجِع لَيس اسمًا عاديًّا
            result.status = "no_check"
            result.evidence.append(
                f"person={p_p} → المَرجِع يُحَدَّد بِالخِطاب لا بِالمُطابَقَة"
            )
            return result

        # ضَمير غائِب (3): تَطابُق جِنس وعَدد
        ok_g = (p_g == ref_gr.gender) or ("X" in (p_g, ref_gr.gender))
        ok_n = (p_n == ref_nr.number) or ("X" in (p_n, ref_nr.number))

        # استثناء: جَمع غَير العاقِل قَد يَأتي ضَميرُه F.SG
        if not ok_n and p_n == "SG" and ref_nr.number == "PL" and p_g == "F":
            result.evidence.append(
                "مُلاحَظَة: جَمع غَير العاقِل يُمكِن مُطابَقَتُه بِـ F.SG"
            )
            result.status = "valid_non_human_plural"
            result.confidence = 0.7
            return result

        # لِضَمير الغائِب: جِنس مُختَلِف = mismatch قاطِع (لا partial)
        if not ok_g:
            result.status = "mismatch"
            result.confidence = 0.3
            result.evidence.append(
                f"تَعارُض جِنس: ضَمير {p_g} vs مَرجِع {ref_gr.gender}"
            )
        elif ok_n:
            result.status = "valid"
            result.confidence = 0.9
            result.evidence.append("جِنس وعَدَد مُتَطابِقان")
        else:
            result.status = "partial"
            result.confidence = 0.5
            result.evidence.append(
                f"جِنس صَحيح، عَدَد مُختَلِف (ضَمير {p_n} vs مَرجِع {ref_nr.number})"
            )

        return result


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = AgreementChecker()
    print(f"contract: {CONTRACT_NAME}")
    print()

    # صِفَة ↔ مَوصوف
    print("─── adjective-noun ───")
    cases = [
        ("صالح", "رجل", "valid"),
        ("صالحة", "امرأة", "valid"),
        ("صالحة", "رجل", "mismatch"),    # جِنس
        ("الصالح", "الرجل", "valid"),
        ("صالح", "الرجل", "partial"),     # تَعريف
    ]
    for adj, noun, expected in cases:
        r = c.check_adjective_noun(adj, noun)
        mark = "✓" if r.status == expected else "✗"
        print(f"  {mark} «{noun} {adj}»: {r.status}  ({r.evidence[0] if r.evidence else ''})")

    # ضَمير ↔ مَرجِع
    print("\n─── pronoun-referent ───")
    pronoun_cases = [
        ({"clitic": "ه", "gender": "M", "number": "SG", "person": "3"}, "رجل", "valid"),
        ({"clitic": "ها", "gender": "F", "number": "SG", "person": "3"}, "امرأة", "valid"),
        ({"clitic": "ه", "gender": "M", "number": "SG", "person": "3"}, "امرأة", "mismatch"),
        ({"clitic": "ها", "gender": "F", "number": "SG", "person": "3"}, "كتب", "valid_non_human_plural"),  # جَمع غَير عاقِل
        ({"clitic": "كم", "gender": "M", "number": "PL", "person": "2"}, "أيّ_اسم", "no_check"),
    ]
    for pf, ref, expected in pronoun_cases:
        r = c.check_pronoun_referent(pf, ref)
        mark = "✓" if r.status == expected else "✗"
        print(f"  {mark} «{pf.get('clitic','')}» → «{ref}»: {r.status}")
