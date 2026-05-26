"""patient_agreement_contract.py — عَقد إِصدار `patient_of`.

نَفس مَنطِق AgentAgreementContract لَكِن لِلمَفعول بِه:

  patient_of(X, V) may be emitted only if:
    1. V is certified FIIL
    2. X is eligible as object/complement (noun-class, not HARF/PUNCT)
    3. X is not within a prepositional phrase (PREP + JAR → object of PREP, not of V)
    4. X has accusative case evidence (مَنصوب) OR position evidence

Returns: Certificate / Hypothesis / Zero مَع evidence + blockers.

Mirrors AgentAgreementContract policy: counter audit, mark_suppressed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

VerdictKind = Literal["Certificate", "Hypothesis", "Zero"]

# ─────────────────────────────────────────────────────────────────
# Eligibility lists (mirror Agent contract)
# ─────────────────────────────────────────────────────────────────

INELIGIBLE_WORD_CLASSES = {"HARF"}

INELIGIBLE_CLOSED_KINDS = {
    "HARF_JARR", "HARF_NASB", "HARF_JAZM", "HARF_ATF",
    "HARF_NIDA", "HARF_NAFY", "HARF_ESTEFHAM", "HARF_SHART",
    "PUNCT", "PARTICLE",
}

ELIGIBLE_WORD_CLASSES = {
    "ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM", "JALALAH",
    "ISM_MABNI", "ISM_ISHARA", "ISM_MAWSOOL",
}


# ─────────────────────────────────────────────────────────────────
# Audit (separate counter from Agent)
# ─────────────────────────────────────────────────────────────────

_AUDIT = {
    "candidates_seen": 0,
    "passed": 0,
    "certificate": 0,
    "hypothesis": 0,
    "zero": 0,
    "suppressed": 0,
    "blockers_count": 0,
    "zero_reasons": {},
}


def reset_audit() -> None:
    _AUDIT["candidates_seen"] = 0
    _AUDIT["passed"] = 0
    _AUDIT["certificate"] = 0
    _AUDIT["hypothesis"] = 0
    _AUDIT["zero"] = 0
    _AUDIT["suppressed"] = 0
    _AUDIT["blockers_count"] = 0
    _AUDIT["zero_reasons"] = {}


def get_audit() -> dict:
    return dict(_AUDIT)


def mark_suppressed() -> None:
    _AUDIT["suppressed"] += 1


@dataclass
class GateResult:
    passed: bool
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass
class PatientVerdict:
    kind: VerdictKind
    contract: str = "PatientAgreementContract:v1"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    residuals: list[str] = field(default_factory=list)


def _record(verdict: PatientVerdict) -> None:
    _AUDIT["candidates_seen"] += 1
    if verdict.kind == "Certificate":
        _AUDIT["certificate"] += 1
        _AUDIT["passed"] += 1
    elif verdict.kind == "Hypothesis":
        _AUDIT["hypothesis"] += 1
        _AUDIT["passed"] += 1
    else:
        _AUDIT["zero"] += 1
        for b in verdict.blockers:
            key = b.split(" — ")[0][:50]
            _AUDIT["zero_reasons"][key] = _AUDIT["zero_reasons"].get(key, 0) + 1
    _AUDIT["blockers_count"] += len(verdict.blockers)


# ─────────────────────────────────────────────────────────────────
# Gates
# ─────────────────────────────────────────────────────────────────

def _patient_eligibility_gate(x_token) -> GateResult:
    """X يَجِب أَن يَكون اسمًا — لا حَرف جَرّ ولا أداة."""
    surface = getattr(x_token, "token", "") or ""
    wc = getattr(x_token, "word_class", "")
    closed_kind = getattr(x_token, "closed_class_kind", "") or ""

    if not surface or surface == "—":
        return GateResult(False, blockers=["empty_token"])

    if wc in INELIGIBLE_WORD_CLASSES:
        if closed_kind in INELIGIBLE_CLOSED_KINDS:
            return GateResult(False,
                blockers=[f"X is HARF/{closed_kind} — not eligible as patient"])
        return GateResult(False,
            blockers=["X.word_class=HARF — not eligible as patient"])

    if wc == "UNKNOWN":
        return GateResult(False,
            blockers=["X.word_class=UNKNOWN — cannot certify as patient"])

    if wc not in ELIGIBLE_WORD_CLASSES:
        return GateResult(False,
            blockers=[f"X.word_class={wc} — not in eligible patient set"])

    return GateResult(True, evidence=[f"X.word_class={wc} — eligible"])


def _certified_verb_gate(v_token) -> GateResult:
    wc = getattr(v_token, "word_class", "")
    if wc != "FIIL":
        return GateResult(False,
            blockers=[f"target.word_class={wc} — must be FIIL"])
    kind = getattr(v_token, "wordclass_kind", "") or ""
    if kind == "Certificate":
        return GateResult(True, evidence=["target FIIL Certificate"])
    return GateResult(True,
        evidence=["target FIIL classified"],
        blockers=["target FIIL is Hypothesis"])


def _case_check(x_token) -> GateResult:
    """يَفحَص هَل X مَنصوب (المَفعول بِه مَنصوب).

    قَرائِن:
      • تَنوين فَتح (ـً)
      • فَتحَة مُفرَدَة عَلى آخِر حَرف (ـَ) — أَضعَف
      • role_phrase يَحوي «مَنصوب» — أَقوى دَليل
    """
    surface = getattr(x_token, "token", "") or ""
    role = getattr(x_token, "role_phrase", "") or ""

    if "منصوب" in role or "مَنصوب" in role:
        return GateResult(True, evidence=[f"role_phrase indicates منصوب: {role}"])

    # تَنوين الفَتح
    if "ً" in surface:
        return GateResult(True, evidence=["tanwin fath (ـً)"])
    # تاء فَتح في النِّهايَة (لِلمُؤَنَّث المَنصوب)
    if surface.endswith("ةً") or surface.endswith("اً"):
        return GateResult(True, evidence=["nasb-ending"])

    # لا قَرينَة صَريحَة — نُمَرِّر مَع blocker
    return GateResult(True,
        evidence=["no explicit case marker"],
        blockers=["case is implicit — needs position evidence"])


def _not_inside_prep_phrase(x_token, prev_token) -> GateResult:
    """X يَجِب أَلّا يَكون مَجرورًا بِحَرف جَرّ سابِق.

    قَرينَة: لَو السَّابِق HARF_JARR → X هو مَجرور لا مَفعول.
    """
    if prev_token is None:
        return GateResult(True)
    prev_wc = getattr(prev_token, "word_class", "")
    prev_kind = getattr(prev_token, "closed_class_kind", "") or ""
    if prev_wc == "HARF" and prev_kind == "HARF_JARR":
        return GateResult(False,
            blockers=[f"X follows HARF_JARR ({prev_token.token}) — is مَجرور, not مَفعول"])
    return GateResult(True)


# ─────────────────────────────────────────────────────────────────
# Main evaluator
# ─────────────────────────────────────────────────────────────────

def evaluate_patient(x_token, v_token, *, prev_token=None,
                     position_evidence: str = "") -> PatientVerdict:
    """العَقد الرَّئيس لِـ patient_of."""
    all_evidence, all_blockers = [], []

    # Gate 1: Eligibility
    eg = _patient_eligibility_gate(x_token)
    if not eg.passed:
        v = PatientVerdict(kind="Zero",
            evidence=eg.evidence, blockers=eg.blockers)
        _record(v); return v
    all_evidence.extend(eg.evidence)

    # Gate 2: Certified verb
    vg = _certified_verb_gate(v_token)
    if not vg.passed:
        v = PatientVerdict(kind="Zero",
            evidence=all_evidence + vg.evidence,
            blockers=all_blockers + vg.blockers)
        _record(v); return v
    all_evidence.extend(vg.evidence)
    all_blockers.extend(vg.blockers)

    # Gate 3: not inside prep phrase
    pg = _not_inside_prep_phrase(x_token, prev_token)
    if not pg.passed:
        v = PatientVerdict(kind="Zero",
            evidence=all_evidence + pg.evidence,
            blockers=all_blockers + pg.blockers)
        _record(v); return v

    # Gate 4: case check
    cg = _case_check(x_token)
    all_evidence.extend(cg.evidence)
    all_blockers.extend(cg.blockers)

    if position_evidence:
        all_evidence.append(f"position: {position_evidence}")

    if not all_blockers:
        v = PatientVerdict(kind="Certificate", evidence=all_evidence)
    else:
        v = PatientVerdict(
            kind="Hypothesis",
            evidence=all_evidence,
            blockers=all_blockers,
            residuals=["full case verification deferred"],
        )
    _record(v); return v


if __name__ == "__main__":
    print(f"contract: PatientAgreementContract:v1")
    print()

    class FakeToken:
        def __init__(self, token, word_class, closed_kind="",
                     wordclass_kind="", role_phrase=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_kind
            self.wordclass_kind = wordclass_kind
            self.role_phrase = role_phrase

    v = FakeToken("كَتَبَ", "FIIL", wordclass_kind="Certificate")
    cases = [
        ("كِتَابًا (tanwin fath)", FakeToken("كِتَابًا", "ISM_MUARAB",
                                            wordclass_kind="Certificate",
                                            role_phrase="مفعول به منصوب"),
         None),
        ("بِالقَلَمِ (after HARF_JARR)", FakeToken("القَلَمِ", "ISM_MUARAB"),
         FakeToken("بِـ", "HARF", "HARF_JARR")),
        ("ۚ pause", FakeToken("ۚ", "HARF", "PUNCT"), None),
        ("بِسم (HARF)", FakeToken("بِسم", "HARF", "HARF_JARR"), None),
    ]
    for label, x, prev in cases:
        v_ = evaluate_patient(x, v_token=v, prev_token=prev)
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[v_.kind]
        print(f"  {label:32s} → {sym} {v_.kind}")
        for b in v_.blockers[:2]:
            print(f"      blocker: {b}")
    print()
    print(f"audit: {get_audit()}")
