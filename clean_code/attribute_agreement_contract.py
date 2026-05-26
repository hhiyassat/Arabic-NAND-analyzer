"""attribute_agreement_contract.py — عَقد النَّعت.

تَوصيَة المُستَخدِم:
  attribute_of(X, Y) لا يُصدَر إِلّا بِمُطابَقَة في:
    1. الجِنس  (gender)
    2. العَدَد  (number)
    3. التَّعريف (definiteness — ال أَو تَنوين)
    4. الإِعراب (case marker — مَرفوع/مَنصوب/مَجرور)

  وَ يَجِب أَن يَكون X بَعد Y مُباشَرَة (نافِذَة قَصيرَة).

مَثَل: وَٱمْرَأَتَانِ نَعت لِـ فَرَجُلٌ خَطَأ (الجِنس وَالعَدَد لا يُطابِقان).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

VerdictKind = Literal["Certificate", "Hypothesis", "Zero"]

_DIACRITICS = set("ًٌٍَُِّْٰـ")


def _strip_diac(s: str) -> str:
    return "".join(c for c in (s or "") if c not in _DIACRITICS)


# ─────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────

_AUDIT = {
    "candidates_seen": 0,
    "certificate": 0,
    "hypothesis": 0,
    "zero": 0,
    "zero_reasons": {},
}


def reset_audit() -> None:
    _AUDIT["candidates_seen"] = 0
    _AUDIT["certificate"] = 0
    _AUDIT["hypothesis"] = 0
    _AUDIT["zero"] = 0
    _AUDIT["zero_reasons"] = {}


def get_audit() -> dict:
    return dict(_AUDIT)


# ─────────────────────────────────────────────────────────────────
# Features extraction
# ─────────────────────────────────────────────────────────────────

def _get_definiteness(surface: str) -> str:
    """ال → DEF, تَنوين → INDEF, غَير ذَلِك → UNKNOWN."""
    plain = _strip_diac(surface).replace("ٱ", "ا")
    if any(c in surface for c in ("ٌ", "ٍ", "ً")):
        return "INDEF"
    if plain.startswith("ال"):
        return "DEF"
    return "UNKNOWN"


def _get_number(surface: str) -> str:
    """SG / DU / PL."""
    plain = _strip_diac(surface).replace("ٱ", "ا")
    if plain.endswith(("ان", "ين")) and len(plain) >= 4:
        # exclude IV verbs
        if plain[0] in {"ي", "ت", "ن", "أ"}:
            return "DU_IV"
        return "DU"
    if plain.endswith(("ون", "ونَ")):
        return "PL"
    if plain.endswith("ات"):
        return "PL"
    return "SG"


def _get_gender(surface: str) -> str:
    plain = _strip_diac(surface).replace("ٱ", "ا")
    if plain.endswith("ة"):
        return "F"
    if plain.endswith("اء") or plain.endswith("ى"):
        return "F_PROB"
    return "M_OR_UNKNOWN"


def _get_case(surface: str) -> str:
    """RAFA / NASB / JARR."""
    if any(c in surface for c in ("ٌ", "ُ")):
        return "RAFA"
    if any(c in surface for c in ("ً", "َ")) and surface[-1:] in ("ً", "َ"):
        return "NASB"
    if any(c in surface for c in ("ٍ", "ِ")):
        return "JARR"
    return "UNK"


# ─────────────────────────────────────────────────────────────────
# Main evaluator
# ─────────────────────────────────────────────────────────────────

@dataclass
class AttrVerdict:
    kind: VerdictKind
    contract: str = "AttributeAgreementContract:v1"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _record(verdict: AttrVerdict) -> None:
    _AUDIT["candidates_seen"] += 1
    if verdict.kind == "Certificate":
        _AUDIT["certificate"] += 1
    elif verdict.kind == "Hypothesis":
        _AUDIT["hypothesis"] += 1
    else:
        _AUDIT["zero"] += 1
        for b in verdict.blockers:
            key = b.split(" — ")[0][:60]
            _AUDIT["zero_reasons"][key] = _AUDIT["zero_reasons"].get(key, 0) + 1


def evaluate_attribute(*, x_token, y_token,
                       x_idx: int, y_idx: int,
                       all_tokens: list = None,
                       max_window: int = 2) -> AttrVerdict:
    """العَقد الرَّئيس: هَل X نَعت لِـ Y؟"""
    evidence = []
    blockers = []

    x_surface = getattr(x_token, "token", "") or ""
    y_surface = getattr(y_token, "token", "") or ""

    # Gate 1: distance
    if abs(x_idx - y_idx) > max_window:
        v = AttrVerdict(kind="Zero",
            blockers=[f"distance {abs(x_idx-y_idx)} > window {max_window}"])
        _record(v); return v

    # Gate 2: order — نَعت بَعد المَنعوت
    if x_idx <= y_idx:
        v = AttrVerdict(kind="Zero",
            blockers=[f"X[{x_idx}] not after Y[{y_idx}]"])
        _record(v); return v

    # Gate 3: definiteness agreement
    x_def = _get_definiteness(x_surface)
    y_def = _get_definiteness(y_surface)
    if x_def != "UNKNOWN" and y_def != "UNKNOWN" and x_def != y_def:
        v = AttrVerdict(kind="Zero",
            blockers=[f"definiteness mismatch: X={x_def} Y={y_def}"])
        _record(v); return v
    if x_def == y_def and x_def != "UNKNOWN":
        evidence.append(f"definiteness match: {x_def}")

    # Gate 4: number agreement
    x_n = _get_number(x_surface)
    y_n = _get_number(y_surface)
    # نَستَثني DU_IV (مُضارِع مُثَنَّى — لَيس نَعت)
    if x_n == "DU_IV":
        v = AttrVerdict(kind="Zero",
            blockers=["X is IV verb, not attribute"])
        _record(v); return v
    if x_n != y_n:
        # DU mismatch مَع SG لا يَكون نَعت قَطعًا
        if x_n == "DU" and y_n == "SG":
            v = AttrVerdict(kind="Zero",
                blockers=[f"DU/SG number mismatch — not an attribute"])
            _record(v); return v
        # تَأَخَّر: PL يُمكِن أَن يَكون نَعت لِـ SG في بَعض الحالات (جَمع تَكسير)
        if not (x_n == "PL" and y_n == "SG"):
            blockers.append(f"number mismatch: X={x_n} Y={y_n}")

    # Gate 5: gender agreement (loose)
    x_g = _get_gender(x_surface)
    y_g = _get_gender(y_surface)
    if x_g == "F" and y_g == "M_OR_UNKNOWN" and y_n == "SG":
        blockers.append(f"gender mismatch: X=F Y=M (SG)")

    # Verdict
    if not blockers:
        v = AttrVerdict(kind="Certificate", evidence=evidence)
    else:
        v = AttrVerdict(
            kind="Hypothesis" if len(blockers) == 1 else "Zero",
            evidence=evidence, blockers=blockers,
        )
    _record(v); return v


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    class _T:
        def __init__(self, token):
            self.token = token

    # وَٱمْرَأَتَانِ (DU F) نَعت لِـ فَرَجُلٌ (SG M) → mismatch
    y = _T("فَرَجُلٌ")
    x = _T("وَٱمْرَأَتَانِ")
    r = evaluate_attribute(x_token=x, y_token=y, x_idx=2, y_idx=1)
    print(f"وَٱمْرَأَتَانِ → فَرَجُلٌ: {r.kind} {r.blockers}")

    # كِتَابٌ كَريمٌ — match
    y2 = _T("كِتَابٌ")
    x2 = _T("كَريمٌ")
    r2 = evaluate_attribute(x_token=x2, y_token=y2, x_idx=1, y_idx=0)
    print(f"كِتَابٌ كَريمٌ: {r2.kind} {r2.evidence}")

    # الْحَقِّ الْكَريمِ — match
    y3 = _T("الْحَقِّ")
    x3 = _T("الْكَريمِ")
    r3 = evaluate_attribute(x_token=x3, y_token=y3, x_idx=1, y_idx=0)
    print(f"الْحَقِّ الْكَريمِ: {r3.kind} {r3.evidence}")
