"""harf_jarr_agreement_contract.py — عَقد جار وَمَجرور.

تَوصيَة المُستَخدِم 2026-05-25:

  "harf_jarr_of(X, H) لا تُصدَر إِلّا إِذا:
     1. H حَرف جَرّ فِعليّ
     2. X اسم/ضَمير مَجرور صالِح
     3. X بَعد H مُباشَرَة أَو في نافِذَة قَصيرَة
     4. لا فاصِل/فِعل/حَرف جَرّ آخَر بَين H وَ X
     5. لا يَجوز إِعادَة استِخدام حَرف جَرّ قَديم

   أَهَمّ قاعِدَة: حَرف الجَرّ يُستَهلَك بَعد أَوَّل مُتَعَلِّق صالِح."

API:
  evaluate_harf_jarr(*, h_token, x_token, all_tokens, h_idx, x_idx,
                     consumed_jarrs: set, max_window: int=3)
    → HarfJarrVerdict(kind, blockers)

الـconsumed_jarrs يَنبَغي أَن يَتَتَبَّعه المُتَّصِل (relation_extractor):
  بَعد كُلّ إِصدار ناجِح، أَضِف h_idx إِلى المَجموعَة.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

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
# Gates
# ─────────────────────────────────────────────────────────────────

def _is_harf_jarr(h_tok) -> bool:
    if not h_tok:
        return False
    wc = getattr(h_tok, "word_class", "")
    if wc != "HARF":
        return False
    kind = getattr(h_tok, "closed_class_kind", "") or ""
    return kind == "HARF_JARR"


def _is_genitive_eligible(x_tok) -> bool:
    """X اسم/ضَمير مَجرور صالِح."""
    if not x_tok:
        return False
    wc = getattr(x_tok, "word_class", "")
    eligible = {
        "ISM_MUARAB", "JAMID", "AALAM", "SINGULAR_TERM",
        "ISM_MABNI", "ISM_MAWSOOL", "ISM_ISHARA",
    }
    return wc in eligible


def _distance_check(h_idx: int, x_idx: int, max_window: int) -> str:
    """X يَجِب أَن يَكون بَعد H مُباشَرَة أَو في نافِذَة قَصيرَة."""
    if x_idx <= h_idx:
        return f"X[{x_idx}] is before H[{h_idx}] — order invalid"
    d = x_idx - h_idx
    if d > max_window:
        return f"distance H→X = {d} > window ({max_window})"
    return ""


def _intervening_blocker(all_tokens: list, h_idx: int, x_idx: int) -> str:
    """فاصِل بَين H وَ X يَمنَع الِارتِباط.

    قَواطِع:
      • فِعل آخَر
      • حَرف جَرّ آخَر
      • مَفعول/مَنصوب
    """
    if x_idx - h_idx <= 1:
        return ""
    for j in range(h_idx + 1, x_idx):
        t = all_tokens[j]
        wc = getattr(t, "word_class", "")
        closed = getattr(t, "closed_class_kind", "") or ""
        if wc == "FIIL":
            return f"intervening FIIL ({t.token}) at [{j}]"
        if wc == "HARF" and closed == "HARF_JARR":
            return f"intervening HARF_JARR ({t.token}) at [{j}]"
        role = (getattr(t, "role_phrase", "") or "")
        if "مفعول" in role or "منصوب" in role:
            return f"intervening مَفعول/مَنصوب ({t.token}) at [{j}]"
    return ""


def _consumed_check(h_idx: int, consumed_jarrs: set) -> str:
    """حَرف الجَرّ مُستَهلَك بَعد أَوَّل مُتَعَلِّق صالِح."""
    if h_idx in consumed_jarrs:
        return f"HARF_JARR at [{h_idx}] already consumed by earlier object"
    return ""


# ─────────────────────────────────────────────────────────────────
# Main evaluator
# ─────────────────────────────────────────────────────────────────

@dataclass
class HarfJarrVerdict:
    kind: VerdictKind
    contract: str = "HarfJarrAgreementContract:v1"
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _record(verdict: HarfJarrVerdict) -> None:
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


def evaluate_harf_jarr(*, h_token, x_token,
                       all_tokens: list,
                       h_idx: int, x_idx: int,
                       consumed_jarrs: Optional[set] = None,
                       max_window: int = 3) -> HarfJarrVerdict:
    """العَقد الرَّئيس."""
    if consumed_jarrs is None:
        consumed_jarrs = set()
    evidence = []
    blockers = []

    # Gate 1: H is real HARF_JARR
    if not _is_harf_jarr(h_token):
        v = HarfJarrVerdict(kind="Zero",
            blockers=["H is not HARF_JARR"])
        _record(v); return v

    # Gate 2: X is eligible
    if not _is_genitive_eligible(x_token):
        v = HarfJarrVerdict(kind="Zero",
            blockers=[f"X.word_class={getattr(x_token,'word_class','?')} — not eligible"])
        _record(v); return v

    # Gate 3: consumed
    consumed = _consumed_check(h_idx, consumed_jarrs)
    if consumed:
        v = HarfJarrVerdict(kind="Zero", blockers=[consumed])
        _record(v); return v

    # Gate 4: distance
    far = _distance_check(h_idx, x_idx, max_window)
    if far:
        v = HarfJarrVerdict(kind="Zero", blockers=[far])
        _record(v); return v

    # Gate 5: intervening blocker
    interv = _intervening_blocker(all_tokens, h_idx, x_idx)
    if interv:
        v = HarfJarrVerdict(kind="Zero", blockers=[interv])
        _record(v); return v

    # Gate 6: ال_تَّأكيد بِالكَسرَة
    x_surface = getattr(x_token, "token", "") or ""
    if "ِ" in x_surface or "ٍ" in x_surface or x_surface.endswith(("ي", "ى")):
        evidence.append(f"X has genitive marker (ـِ/ـٍ/ـي)")

    if evidence and not blockers:
        v = HarfJarrVerdict(kind="Certificate", evidence=evidence)
    else:
        v = HarfJarrVerdict(
            kind="Hypothesis",
            evidence=evidence,
            blockers=blockers or ["no explicit genitive marker — using position"],
        )
    _record(v); return v


# ─────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    class _T:
        def __init__(self, token, word_class="ISM_MUARAB",
                     closed_class_kind="", role_phrase=""):
            self.token = token
            self.word_class = word_class
            self.closed_class_kind = closed_class_kind
            self.role_phrase = role_phrase

    # إلى أَجَلٍ
    h = _T("إِلَىٰٓ", "HARF", "HARF_JARR")
    x = _T("أَجَلٍ", "ISM_MUARAB", role_phrase="اسم مجرور")
    tokens = [h, x]
    r = evaluate_harf_jarr(
        h_token=h, x_token=x,
        all_tokens=tokens, h_idx=0, x_idx=1,
    )
    print(f"إلى أَجَلٍ → {r.kind} {r.evidence}")

    # إلى أَجَلٍ + فعل ثُمّ ٱلَّذِى → must reject (far + intervening verb)
    h2 = _T("إِلَىٰٓ", "HARF", "HARF_JARR")
    x2 = _T("ٱلَّذِى", "ISM_MAWSOOL", role_phrase="اسم مجرور")
    verb = _T("يَكْتُبُ", "FIIL")
    tokens2 = [h2, _T("أَجَلٍ"), verb, _T("بَيْنَكُمْ"), x2]
    r2 = evaluate_harf_jarr(
        h_token=h2, x_token=x2,
        all_tokens=tokens2, h_idx=0, x_idx=4,
    )
    print(f"إلى ... ٱلَّذِى (far) → {r2.kind} {r2.blockers}")

    # consumed check
    r3 = evaluate_harf_jarr(
        h_token=h, x_token=x,
        all_tokens=tokens, h_idx=0, x_idx=1,
        consumed_jarrs={0},
    )
    print(f"إلى consumed → {r3.kind} {r3.blockers}")
    print()
    print(f"audit: {get_audit()}")
