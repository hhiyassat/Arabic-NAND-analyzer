"""agent_agreement_contract.py — عَقد إِصدار `agent_of`.

Per user spec (2026-05-24):

  No `agent_of` relation may be emitted unless the target is a certified
  verb and the subject agreement contract has passed.

Returns one of:
  • Certificate — كُلّ الشُّروط مُحَقَّقَة
  • Hypothesis — مُمكِن لَكِنّ قَرينَة ناقِصَة
  • Zero — مَمنوع قَطعًا

Architecture:
  AgentAgreementContract(X, V, context)
    → AgentEligibilityGate(X)         # نَفي قَطعيّ لِلمُستَحيلات
    → CertifiedVerbGate(V)            # V يَجِب أَن يَكون FIIL مُحَقَّق
    → AgreementCheck(X, V)            # تَطابُق الشَّخص/العَدَد/الجِنس
    → PositionCheck(X, V)             # قَرينَة مَوقعيَّة
    → Verdict

كُلّ عَقد فَرعيّ يَرُدّ (passed: bool, evidence: list, blockers: list).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

VerdictKind = Literal["Certificate", "Hypothesis", "Zero"]


# ─────────────────────────────────────────────────────────────────
# Audit metrics — per-session counters
# Per user (2026-05-24): track suppressed vs zero distinctly.
#   suppressed = Zero verdict + caller dropped relation (not emitted)
#   zero       = Zero verdict + caller emitted as Zero (visible)
#   hypothesis = Hypothesis verdict + caller emitted
#   certificate= Certificate verdict + caller emitted
# ─────────────────────────────────────────────────────────────────
_AUDIT = {
    "candidates_seen": 0,
    "passed": 0,        # gates allowed verdict (Cert + Hyp)
    "certificate": 0,
    "hypothesis": 0,
    "zero": 0,          # Zero verdicts (whether emitted or dropped)
    "suppressed": 0,    # subset of zero: caller dropped the relation
    "blockers_count": 0,
    "zero_reasons": {},  # top blocker → count
}


def reset_audit() -> None:
    """يَستَعيد العَدّادات إِلى الصِّفر — يَجِب نِداؤها قَبل كُلّ تَحليل."""
    _AUDIT["candidates_seen"] = 0
    _AUDIT["passed"] = 0
    _AUDIT["certificate"] = 0
    _AUDIT["hypothesis"] = 0
    _AUDIT["zero"] = 0
    _AUDIT["suppressed"] = 0
    _AUDIT["blockers_count"] = 0
    _AUDIT["zero_reasons"] = {}


def get_audit() -> dict:
    """يَرُدّ نُسخَة لِلعَدّادات."""
    return dict(_AUDIT)


def mark_suppressed() -> None:
    """يُنادى مِن المُستَدعي عِندَ إِسقاط العَلاقَة بَعد Zero."""
    _AUDIT["suppressed"] += 1


def _record_verdict(verdict: "AgentVerdict") -> None:
    """يُسَجِّل النَّتيجَة في العَدّادات."""
    _AUDIT["candidates_seen"] += 1
    if verdict.kind == "Certificate":
        _AUDIT["certificate"] += 1
        _AUDIT["passed"] += 1
    elif verdict.kind == "Hypothesis":
        _AUDIT["hypothesis"] += 1
        _AUDIT["passed"] += 1
    else:  # Zero
        _AUDIT["zero"] += 1
        # تَتَبُّع أَكثَر الأَسباب
        for b in verdict.blockers:
            key = b.split(" — ")[0][:50]
            _AUDIT["zero_reasons"][key] = _AUDIT["zero_reasons"].get(key, 0) + 1
    _AUDIT["blockers_count"] += len(verdict.blockers)

# ─────────────────────────────────────────────────────────────────
# قَوائِم الأَهليَّة (eligibility)
# ─────────────────────────────────────────────────────────────────

# أَنواع الكَلِمات الَّتي لا يُمكِن أَن تَكون فاعِلًا أَبَدًا
INELIGIBLE_WORD_CLASSES = {
    "HARF",       # حَرف عامّ — لَيس اسمًا
}

# تَفصيلًا: subclasses في HARF أَو غَيره الَّتي لا تَصلُح كَ فاعِل
INELIGIBLE_CLOSED_KINDS = {
    "HARF_JARR",
    "HARF_NASB",
    "HARF_JAZM",
    "HARF_ATF",
    "HARF_NIDA",
    "HARF_NAFY",
    "HARF_ESTEFHAM",
    "HARF_SHART",
    "PUNCT",
    "DET",
    "PARTICLE",
}

# أَنواع كَلِمات صالِحَة كَ فاعِل (open-class أَو ضَمائر)
ELIGIBLE_WORD_CLASSES = {
    "ISM_MUARAB",
    "JAMID",
    "AALAM",
    "SINGULAR_TERM",
    "JALALAH",
    "ISM_MABNI",       # ضَمائر، أَسماء إِشارَة... بِشُروط
    "ISM_ISHARA",
    # ISM_MAWSOOL يَحتاج عَقدًا خاصًّا (RelativeClauseContract)
    # ISM_DAMIR ضَمير مُنفَصِل — eligible
}

# ضَمائر مُستَتِرَة virtual nodes (implicit_t*)
IMPLICIT_NODE_PREFIX = "implicit_"


@dataclass
class GateResult:
    """نَتيجَة عَقد فَرعيّ."""
    passed: bool
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass
class AgentVerdict:
    """الحُكم النِّهائيّ لِعَقد إِصدار agent_of."""
    kind: VerdictKind
    contract: str = "AgentAgreementContract:v1"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    residuals: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}[self.kind]
        e = f" | evidence={len(self.evidence)}" if self.evidence else ""
        b = f" | blockers={len(self.blockers)}" if self.blockers else ""
        return f"{sym} {self.kind}{e}{b}"


# ─────────────────────────────────────────────────────────────────
# العَقد الفَرعيّ 1: AgentEligibilityGate
# ─────────────────────────────────────────────────────────────────

def _agent_eligibility_gate(x_token) -> GateResult:
    """يَنفي المُستَحيلات قَطعًا.

    Returns passed=False مَع blocker إِذا كانَ X لا يَصلُح أَن يَكون
    فاعِلًا تَحت أَيّ ظَرف (حَرف جَرّ، حَرف عَطف، عَلامَة وَقف...).
    """
    surface = getattr(x_token, "token", "") or ""
    wc = getattr(x_token, "word_class", "")
    closed_kind = getattr(x_token, "closed_class_kind", "") or ""

    # 1. كَلِمَة فارِغَة أَو الـ "—"
    if not surface or surface == "—":
        return GateResult(False, blockers=["empty_token"])

    # 2. HARF عام (لا اسم)
    if wc in INELIGIBLE_WORD_CLASSES:
        # نَتَفَحَّص هَل يَدخُل ضَمن النَّوع الفَرعيّ المَمنوع
        if closed_kind in INELIGIBLE_CLOSED_KINDS:
            return GateResult(False,
                blockers=[f"X is HARF/{closed_kind} — not eligible as agent"])
        # حَتَّى لَو لَم يَكُن لَه subclass، HARF عامّ لا يَصلُح فاعِلًا
        return GateResult(False,
            blockers=[f"X.word_class=HARF — not eligible as agent"])

    # 3. UNKNOWN
    if wc == "UNKNOWN":
        return GateResult(False,
            blockers=[f"X.word_class=UNKNOWN — cannot certify as agent"])

    # 4. ISM_MAWSOOL وَحدَه يَحتاج عَقد صِلَة (مَرَّر كَ Hypothesis-only)
    if wc == "ISM_MAWSOOL":
        return GateResult(True,
            evidence=[f"X is relative pronoun"],
            blockers=["needs_relative_clause_contract — degrade to Hypothesis"])

    # 5. eligible
    if wc in ELIGIBLE_WORD_CLASSES:
        return GateResult(True,
            evidence=[f"X.word_class={wc} — eligible class"])

    # 6. غَير ذلِك — مَرفوض احتِياطًا
    return GateResult(False,
        blockers=[f"X.word_class={wc} — not in eligible set"])


# ─────────────────────────────────────────────────────────────────
# العَقد الفَرعيّ 2: CertifiedVerbGate
# ─────────────────────────────────────────────────────────────────

def _certified_verb_gate(v_token) -> GateResult:
    """V يَجِب أَن يَكون FIIL — وَ مُفَضَّل بِشَهادَة."""
    wc = getattr(v_token, "word_class", "")
    if wc != "FIIL":
        return GateResult(False,
            blockers=[f"target.word_class={wc} — must be FIIL"])
    # هَل التَّصنيف بِشَهادَة؟
    kind = getattr(v_token, "wordclass_kind", "") or ""
    if kind == "Certificate":
        return GateResult(True,
            evidence=["target FIIL classified as Certificate"])
    return GateResult(True,
        evidence=["target FIIL classified"],
        blockers=[f"target FIIL is Hypothesis, not Certificate"])


# ─────────────────────────────────────────────────────────────────
# العَقد الفَرعيّ 3: AgreementCheck
# ─────────────────────────────────────────────────────────────────

# لاحِقَة الفِعل → person/number/gender يُستَنبَط
def _verb_morphology_features(v_token) -> dict:
    """يَستَخرِج (person, number, gender) مِن صيغَة الفِعل."""
    surface = getattr(v_token, "token", "") or ""
    plain = "".join(c for c in surface if c not in "ًٌٍَُِّْـٰٓ")

    # نَزع الـ clitics البادِئَة
    for clitic in ("و", "ف", "أو", "أف"):
        if plain.startswith(clitic) and len(plain) > len(clitic):
            plain = plain[len(clitic):]
            break

    # شَهادات اللاحِقَة (الأَقوى)
    if plain.endswith("تموا") or plain.endswith("تم"):
        return {"person": "2", "number": "plural", "gender": "masculine",
                "evidence": "suffix تُم/تُموا"}
    if plain.endswith("تما"):
        return {"person": "2", "number": "dual", "gender": "common",
                "evidence": "suffix تُما"}
    if plain.endswith("تن"):
        return {"person": "2", "number": "plural", "gender": "feminine",
                "evidence": "suffix تُنَّ"}
    if plain.endswith("نا"):
        # ambiguous: مُتَكَلِّم جَمع past — أَو مُتَّصِل مَفعول
        return {"person": "1", "number": "plural", "gender": "common",
                "evidence": "suffix نا (PV)", "ambiguous": True}
    if plain.endswith("وا"):
        # مُضارِع/ماضي جَمع
        return {"person": "3", "number": "plural", "gender": "masculine",
                "evidence": "suffix وا (plural masc)"}
    if plain.endswith("ون"):
        # مُضارِع 3-جَمع-مذكَّر (يَفعَلونَ) أَو 2-جَمع-مذكَّر (تَفعَلونَ)
        # يَعتَمِد عَلى البادِئَة
        if plain.startswith("ي"):
            return {"person": "3", "number": "plural", "gender": "masculine",
                    "evidence": "يَ+ون (3pl masc)"}
        if plain.startswith("ت"):
            return {"person": "2", "number": "plural", "gender": "masculine",
                    "evidence": "تَ+ون (2pl masc)"}
    if plain.endswith("ين"):
        # تَفعَلِين — 2-singular-feminine
        if plain.startswith("ت"):
            return {"person": "2", "number": "singular", "gender": "feminine",
                    "evidence": "تَ+ين (2sg fem)"}
    if plain.endswith("ان"):
        # يَفعَلانِ / تَفعَلانِ
        if plain.startswith("ي"):
            return {"person": "3", "number": "dual", "gender": "masculine",
                    "evidence": "يَ+ان (3dual)"}
        if plain.startswith("ت"):
            return {"person": "2", "number": "dual", "gender": "common",
                    "evidence": "تَ+ان (2dual)"}
    if plain.endswith("ن"):
        # تَفعَلنَ — جَمع نِسوَة
        if plain.startswith("ت"):
            return {"person": "3", "number": "plural", "gender": "feminine",
                    "evidence": "تَ+نَ (3pl fem)", "ambiguous": True}

    # بِدون لاحِقَة: نَعتَمِد عَلى البادِئَة وَحدَها
    if plain.startswith("ن"):
        return {"person": "1", "number": "plural", "gender": "common",
                "evidence": "prefix ن (1pl)"}
    if plain.startswith("أ"):
        return {"person": "1", "number": "singular", "gender": "common",
                "evidence": "prefix أ (1sg)"}
    if plain.startswith("ي"):
        return {"person": "3", "number": "singular", "gender": "masculine",
                "evidence": "prefix ي (3sg masc)"}
    if plain.startswith("ت"):
        # تَ بِلا لاحِقَة = مُبهَم (2sg masc OR 3sg fem)
        return {"person": "AMBIGUOUS_2or3", "number": "singular",
                "gender": "AMBIGUOUS_masc_or_fem",
                "evidence": "prefix تَ (AMBIGUOUS: 2sg-masc or 3sg-fem)",
                "ambiguous": True}

    # ماضي: لا بادِئَة، يُعتَبَر 3sg-masc افتراضيًّا
    return {"person": "3", "number": "singular", "gender": "masculine",
            "evidence": "PV default (no prefix, no suffix)"}


def _noun_features_heuristic(x_token) -> dict:
    """يَستَنبِط (number, gender) مِن السَّطح لِلاسم.

    Best-effort: يَنتَهي بِـ ة/ـات → مُؤَنَّث؛ يَنتَهي بِـ ـون/ـين → جَمع مُذَكَّر.
    """
    surface = getattr(x_token, "token", "") or ""
    plain = "".join(c for c in surface if c not in "ًٌٍَُِّْـٰٓ")

    feats = {"number": "singular", "gender": "masculine"}
    if plain.endswith("ون") or plain.endswith("ين"):
        feats["number"] = "plural"
        feats["gender"] = "masculine"
    elif plain.endswith("ات") or plain.endswith("اتٌ") or plain.endswith("اتٍ"):
        feats["number"] = "plural"
        feats["gender"] = "feminine"
    elif plain.endswith("ة") or plain.endswith("ه"):
        feats["gender"] = "feminine"
    elif plain.endswith("ا") or plain.endswith("ى"):
        # alif/alif maqsura — قَد يَكون مُؤَنَّث
        pass
    elif plain.endswith("ان") or plain.endswith("ين"):
        feats["number"] = "dual"
    return feats


def _agreement_check(x_token, v_token) -> GateResult:
    """يَفحَص تَطابُق person/number/gender بَين X وَ V.

    قَواعِد مُتَساهِلَة: نَطلُب فَقَط أَن لا يَكون هُناك تَناقُض صَريح.
    """
    v_feats = _verb_morphology_features(v_token)
    n_feats = _noun_features_heuristic(x_token)

    evidence, blockers = [], []
    evidence.append(f"verb_morph: {v_feats.get('evidence', '?')}")

    # X.person يَجِب أَن يَكون 3 (لِأَنّ الِاسم الظَّاهِر دائِمًا غائِب)
    v_person = v_feats.get("person", "")
    if v_person == "1":
        return GateResult(False,
            blockers=[f"verb is 1st-person — explicit noun cannot be 1st"])
    if v_person == "2":
        return GateResult(False,
            blockers=[f"verb is 2nd-person — explicit noun cannot be 2nd"])
    if v_person == "AMBIGUOUS_2or3":
        return GateResult(True,
            evidence=evidence + [f"verb person ambiguous"],
            blockers=["verb prefix تَ ambiguous (2sg or 3fem)"])

    # نَفحَص العَدَد (تَطابُق ضَعيف — جَمع تَكسير يَكسِر القاعِدَة كَثيرًا)
    v_num = v_feats.get("number", "")
    n_num = n_feats.get("number", "singular")
    if v_num and n_num and v_num != n_num:
        # تَناقُض ظاهِرّ، لَكِن قَد يَكون جَمع تَكسير → نَجعَلها blocker لا منع
        blockers.append(f"number mismatch: verb={v_num}, noun={n_num}")

    # الجِنس (مُتَساهِل)
    v_gen = v_feats.get("gender", "")
    n_gen = n_feats.get("gender", "")
    if v_gen and n_gen and v_gen != n_gen and v_gen != "common" and n_gen != "common":
        blockers.append(f"gender mismatch: verb={v_gen}, noun={n_gen}")

    return GateResult(True, evidence=evidence, blockers=blockers)


# ─────────────────────────────────────────────────────────────────
# العَقد الرَّئيس
# ─────────────────────────────────────────────────────────────────

def evaluate_agent(x_token, v_token, *, position_evidence: str = "") -> AgentVerdict:
    """العَقد الرَّئيس: يَفحَص هَل X يَصلُح فاعِلًا لِـ V.

    Returns AgentVerdict مَع kind + evidence + blockers + residuals.
    """
    all_evidence: list[str] = []
    all_blockers: list[str] = []
    all_residuals: list[str] = []

    # 1. AgentEligibilityGate
    eg = _agent_eligibility_gate(x_token)
    if not eg.passed:
        verdict = AgentVerdict(
            kind="Zero",
            evidence=eg.evidence,
            blockers=eg.blockers,
        )
        _record_verdict(verdict)
        return verdict
    all_evidence.extend(eg.evidence)
    all_blockers.extend(eg.blockers)

    # 2. CertifiedVerbGate
    vg = _certified_verb_gate(v_token)
    if not vg.passed:
        verdict = AgentVerdict(
            kind="Zero",
            evidence=all_evidence + vg.evidence,
            blockers=all_blockers + vg.blockers,
        )
        _record_verdict(verdict)
        return verdict
    all_evidence.extend(vg.evidence)
    all_blockers.extend(vg.blockers)

    # 3. AgreementCheck
    ag = _agreement_check(x_token, v_token)
    if not ag.passed:
        verdict = AgentVerdict(
            kind="Zero",
            evidence=all_evidence + ag.evidence,
            blockers=all_blockers + ag.blockers,
        )
        _record_verdict(verdict)
        return verdict
    all_evidence.extend(ag.evidence)
    all_blockers.extend(ag.blockers)

    # 4. Position evidence
    if position_evidence:
        all_evidence.append(f"position: {position_evidence}")

    # 5. الحُكم
    if not all_blockers:
        verdict = AgentVerdict(kind="Certificate", evidence=all_evidence)
    else:
        verdict = AgentVerdict(
            kind="Hypothesis",
            evidence=all_evidence,
            blockers=all_blockers,
            residuals=["full agreement verification deferred"],
        )
    _record_verdict(verdict)
    return verdict


# ─────────────────────────────────────────────────────────────────
# Implicit agent contract (special case)
# ─────────────────────────────────────────────────────────────────

def evaluate_implicit_agent(pronoun: str, v_token, csv_row: dict) -> AgentVerdict:
    """عَقد الضَّمير المُستَتِر — أَخَفّ مِن العام لِأَنّ Source غَير ظاهِر.

    Args:
      pronoun: السَّطح المُنشَأ (نَحنُ/هو/أَنتُم...)
      v_token: الفِعل المُستَهدَف
      csv_row: السَّجَلّ مِن implicit_agents.csv (يَحوي person/number/gender)
    """
    # 1. V يَجِب أَن يَكون FIIL
    vg = _certified_verb_gate(v_token)
    if not vg.passed:
        verdict = AgentVerdict(
            kind="Zero",
            evidence=vg.evidence,
            blockers=vg.blockers + ["implicit agent on non-verb"],
        )
        _record_verdict(verdict)
        return verdict

    v_feats = _verb_morphology_features(v_token)
    csv_person = csv_row.get("person", "")
    csv_number = csv_row.get("number", "")

    evidence = [
        f"verb_morph: {v_feats.get('evidence', '?')}",
        f"implicit from CSV: person={csv_person}/number={csv_number}",
    ]

    v_person = v_feats.get("person", "")
    if v_person != csv_person and v_person != "AMBIGUOUS_2or3":
        verdict = AgentVerdict(
            kind="Zero",
            evidence=evidence,
            blockers=[f"person mismatch: verb={v_person}, csv={csv_person}"],
        )
        _record_verdict(verdict)
        return verdict

    verdict = AgentVerdict(
        kind="Hypothesis",
        evidence=evidence,
        blockers=[],
        residuals=["implicit pronoun: cannot promote to Certificate"],
    )
    _record_verdict(verdict)
    return verdict


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"contract: AgentAgreementContract:v1")
    print()

    # تَجريب يَدَويّ
    class FakeToken:
        def __init__(self, token, word_class, closed_kind="", wordclass_kind=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_kind
            self.wordclass_kind = wordclass_kind

    v = FakeToken("يَكْتُبُ", "FIIL", wordclass_kind="Certificate")
    cases = [
        ("الْوَلَدُ noun", FakeToken("الْوَلَدُ", "ISM_MUARAB", wordclass_kind="Certificate")),
        ("بِدَيْنٍ prep+noun", FakeToken("بِدَيْنٍ", "HARF", "HARF_JARR")),
        ("جُنَاحٌ noun (false ground)", FakeToken("جُنَاحٌ", "ISM_MUARAB", wordclass_kind="Certificate")),
        ("ٱلَّذِينَ relative", FakeToken("ٱلَّذِينَ", "ISM_MAWSOOL", wordclass_kind="Certificate")),
        ("ۚ pause", FakeToken("ۚ", "HARF", "PUNCT")),
        ("UNKNOWN word", FakeToken("xyz", "UNKNOWN")),
    ]
    for label, x in cases:
        v = AgentVerdict
        result = evaluate_agent(x, v_token=FakeToken("يَكْتُبُ", "FIIL", wordclass_kind="Certificate"))
        print(f"  {label:30s} → {result}")
        for b in result.blockers[:2]:
            print(f"      blocker: {b}")
        for e in result.evidence[:2]:
            print(f"      evidence: {e}")
        print()
