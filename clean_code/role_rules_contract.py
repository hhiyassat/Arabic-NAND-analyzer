"""role_rules_contract.py — قواعد تحديد الدور الإعرابي.

Per 14_Minimal_Complete_Theory: every rule must be named, with a data
table holding its metadata. The condition logic stays as Python (each
rule is a small predicate function), but the rule REGISTRY — its
priority, name, role phrase, contract identity — is loaded from CSV.

Replaces the inline if/elif chain in layer3._assign_ism_role.

Schema (contracts/rules/role_rules.csv):
  priority           — execution order (1 = first)
  name               — short rule identifier
  condition          — DSL predicate name (must have matching function)
  role_phrase        — Arabic display, may contain {prev}, {case_name}
  role_kind          — Certificate | Hypothesis
  case_id_required   — int or empty (don't filter on case if empty)
  note               — Arabic description

Each `condition` string maps to a function in CONDITIONS dict below.
The function takes (t, prev, ctx, tokens, i) and returns a bool.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from contracts_loader import _load_rows


CONTRACT_NAME = "RoleRulesContract:v1"

_CASE_AR = {1: "مرفوع", 2: "منصوب", 3: "مجرور", 4: "مجزوم", 5: "مبني"}  # canonical


# ============================================================================
# Condition predicates — each named function corresponds to a CSV row
# ============================================================================

def _prev_is_HARF_JARR(t, prev, ctx, tokens, i) -> bool:
    return (prev is not None
            and prev.word_class == "HARF"
            and prev.closed_class_kind == "HARF_JARR")


def _prev_in_HAROF_INNA_and_case_mansoob(t, prev, ctx, tokens, i) -> bool:
    from i3rab_engine.layer3 import _HAROF_INNA, _strip_diac  # type: ignore
    return (prev is not None
            and prev.word_class == "HARF"
            and _strip_diac(prev.token) in _HAROF_INNA
            and t.case_id == 2)


def _saw_inna_subj_set_and_marfoo(t, prev, ctx, tokens, i) -> bool:
    return (ctx.get("saw_inna")
            and ctx.get("inna_subj_set")
            and t.case_id == 1)


def _after_verb_mansoob_no_jarr(t, prev, ctx, tokens, i) -> bool:
    if ctx.get("last_verb_idx", -1) < 0:
        return False
    if ctx.get("last_verb_obj_set"):
        return False
    if t.case_id != 2:
        return False
    # no intervening HARF_JARR between verb and this noun
    for tk in tokens[ctx["last_verb_idx"] + 1 : i]:
        if tk.word_class == "HARF" and tk.closed_class_kind == "HARF_JARR":
            return False
    return True


def _after_verb_marfoo_no_prior_marfoo(t, prev, ctx, tokens, i) -> bool:
    if ctx.get("last_verb_idx", -1) < 0:
        return False
    if t.case_id != 1:
        return False
    for tk in tokens[ctx["last_verb_idx"] + 1 : i]:
        if (tk.word_class in {"ISM_MUARAB", "JAMID", "AALAM"}
                and tk.case_id == 1):
            return False
    return True


def _first_marfoo_no_verb_before(t, prev, ctx, tokens, i) -> bool:
    return (t.case_id == 1
            and ctx.get("last_verb_idx", -1) < 0
            and not ctx.get("saw_mubtada"))


def _marfoo_after_mubtada(t, prev, ctx, tokens, i) -> bool:
    return (t.case_id == 1
            and ctx.get("saw_mubtada")
            and not ctx.get("saw_khabar"))


def _case_def_agreement_with_prev(t, prev, ctx, tokens, i) -> bool:
    from i3rab_engine.layer3 import _strip_diac  # type: ignore
    if not (prev
            and prev.word_class in {"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"}
            and prev.case_id == t.case_id
            and prev.case_id is not None):
        return False
    # Normalize ٱ (U+0671 wasla alif) → ا so Quranic forms like
    # ٱللَّهِ are correctly recognized as definite (start with ال).
    # Without this, naat fires for بِسْمِ ٱللَّهِ via both_indef,
    # masking the correct mudaf-ilayh classification.
    pp = _strip_diac(prev.token).replace("ٱ", "ا")
    tp = _strip_diac(t.token).replace("ٱ", "ا")
    both_def = pp.startswith("ال") and tp.startswith("ال")
    both_indef = (not pp.startswith("ال")) and (not tp.startswith("ال"))
    if not (both_def or both_indef):
        return False
    # Chain guard: in indef+indef pairs (both مجرور with no ال), if the
    # next token is also مجرور, the construct is much more likely an
    # إضافة chain (e.g. مَٰلِكِ يَوْمِ ٱلدِّينِ) than a nominal-naat. Suppress
    # naat so rule 9 (mudaf_ilayh) handles t correctly.
    if both_indef and t.case_id == 3 and tokens and i + 1 < len(tokens):
        nxt = tokens[i + 1]
        if getattr(nxt, "case_id", None) == 3:
            return False
    # MASAQ F3 (2026-05-29) — gen_cons_marked_as_naat suppressors.
    # Two narrow predicate guards that close 2-token إضافة pairs the
    # original chain guard didn't catch.
    #
    # Guard A — functional-locative prev heads إضافة.
    # Locative ظَروف (بَيْنَ، بَعْدَ، عِنْدَ، تَحْتَ، فَوْقَ، قَبْلَ، ...) never
    # carry نعت adjectives in the same case slot; they head إضافة. The
    # detector is reused from layer3.py's PATCH 4.5 functional-locative
    # lexicon (data-driven; no hardcoded list here).
    try:
        from i3rab_engine.layer3 import _is_functional_locative_noun
        if _is_functional_locative_noun(prev):
            return False
    except ImportError:
        pass
    # Guard B — pronoun-suffix on current signals إضافة, not نعت.
    # A noun with an attached possessive pronoun (هـ، ها، كَ، كم، نا،
    # ي، ...) is classically definite-by-possession and is itself مضاف
    # to the pronoun. Its outer relation to prev is مضاف-إليه, not نعت.
    # The both_indef branch above looks at surface ال only, so it
    # misses possessive definiteness; this guard closes that gap.
    _PRON_SUFFIXES_PLAIN = {
        "ه", "ها", "هم", "هما", "هن",
        "ك", "كم", "كما", "كن",
        "نا", "ي",
    }
    for sfx in (getattr(t, "suffixes", None) or []):
        sfx_str = sfx if isinstance(sfx, str) else (sfx[0] if sfx else "")
        if _strip_diac(sfx_str) in _PRON_SUFFIXES_PLAIN:
            return False
    return True


def _majroor_after_noun(t, prev, ctx, tokens, i) -> bool:
    return (t.case_id == 3
            and prev
            and prev.word_class in {"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"})


def _after_HARF_ATF(t, prev, ctx, tokens, i) -> bool:
    return (prev
            and prev.word_class == "HARF"
            and prev.closed_class_kind == "HARF_ATF"
            and t.case_id is not None)


def _case_only(t, prev, ctx, tokens, i) -> bool:
    return t.case_id is not None


CONDITIONS: dict[str, Callable] = {
    "prev_is_HARF_JARR": _prev_is_HARF_JARR,
    "prev_in_HAROF_INNA_and_case_mansoob": _prev_in_HAROF_INNA_and_case_mansoob,
    "saw_inna_subj_set_and_marfoo": _saw_inna_subj_set_and_marfoo,
    "after_verb_mansoob_no_jarr": _after_verb_mansoob_no_jarr,
    "after_verb_marfoo_no_prior_marfoo": _after_verb_marfoo_no_prior_marfoo,
    "first_marfoo_no_verb_before": _first_marfoo_no_verb_before,
    "marfoo_after_mubtada": _marfoo_after_mubtada,
    "case_def_agreement_with_prev": _case_def_agreement_with_prev,
    "majroor_after_noun": _majroor_after_noun,
    "after_HARF_ATF": _after_HARF_ATF,
    "case_only": _case_only,
}


# Side-effects per rule (which ctx flags to update on match)
RULE_SIDE_EFFECTS = {
    "ism_inna":        lambda ctx: ctx.update(inna_subj_set=True),
    "khabar_inna":     lambda ctx: ctx.update(inna_subj_set=False),
    "mafool_bih":      lambda ctx: ctx.update(last_verb_obj_set=True),
    "mubtada":         lambda ctx: ctx.update(saw_mubtada=True),
    "khabar":          lambda ctx: ctx.update(saw_khabar=True),
}


class RoleRulesContract:
    """Apply the 10 role rules in declared priority order."""

    def __init__(self) -> None:
        rules = _load_rows("role_rules.csv")
        # Sort by priority
        rules.sort(key=lambda r: int(r.get("priority", "99")))
        self._rules = rules

    def apply(self, t, prev, ctx, tokens, i) -> Optional[dict]:
        """Return {role_phrase, role_kind, contract, rule_name} or None."""
        for rule in self._rules:
            cond_name = rule.get("condition", "")
            fn = CONDITIONS.get(cond_name)
            if fn is None:
                continue
            try:
                if fn(t, prev, ctx, tokens, i):
                    return self._build_result(rule, t, prev)
            except Exception:
                continue
        return None

    def _build_result(self, rule: dict, t, prev) -> dict:
        phrase_template = rule.get("role_phrase", "")
        case_name = _CASE_AR.get(t.case_id, "")
        prev_token = prev.token if prev else ""
        phrase = phrase_template.format(
            prev=prev_token,
            case_name=case_name,
        )
        contract = f"{rule['name']}:{prev_token}" if "{prev}" in phrase_template else rule["name"]
        return {
            "role_phrase": phrase,
            "role_kind": rule.get("role_kind", "Hypothesis"),
            "contract": contract,
            "rule_name": rule["name"],
            "rule_priority": rule.get("priority", ""),
        }

    def apply_side_effects(self, rule_name: str, ctx: dict) -> None:
        fn = RULE_SIDE_EFFECTS.get(rule_name)
        if fn:
            fn(ctx)

    def source(self) -> str:
        return CONTRACT_NAME


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    c = RoleRulesContract()
    print(f"contract: {c.source()}")
    print(f"rules loaded: {len(c._rules)}")
    for r in c._rules:
        print(f"  [{r['priority']:>2}] {r['name']:<20} → {r['role_phrase']}")
