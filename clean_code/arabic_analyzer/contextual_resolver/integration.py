"""integration.py — Phase 4 hook خَلف feature flag.

Flag default: OFF.
عِندَما يَكون OFF: لا تَغيير في أَيّ output (byte-identical to baseline).

تَفعيل:
  - env var: ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER=1
  - or:     ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER=true/yes/on

شَرط التَّطبيق (كُلّ التَّالي يَجِب أَن يَتَحَقَّق لِلـ Hypothesis path):
  1. surface في HANDLED_SURFACES_NORMALIZED (بَعد _strip)
  2. proof_kind == "Hypothesis"
  3. needs_context OR ≥2 candidates

قَواعِد التَّطبيق (Hypothesis path):
  • resolver→Certificate: تَرقيَة + source=ContextualAmbiguityResolver
                           + حِفظ original candidates
  • resolver→Hypothesis : إِضافَة metadata فَقَط، لا تَرقيَة
  • resolver→unresolved : لا تَغيير
  • خارِج النِّطاق         : لا تَغيير

Certificate Re-evaluation path (added 2026-05-26 per
PHASE4_CERTIFICATE_REEVALUATION_RULE_LOCK.md — قاعِدَة A1):
  شَرط التَّطبيق:
    1. surface في HANDLED_SURFACES_NORMALIZED (بَعد _strip)
    2. proof_kind == "Certificate"
    3. source يَبدَأ بِواحِد مِن:
       - "closed_function_word"
       - "non_verb_override_gate"
  السُّلوك: metadata-only — يُلصِق phase4_* بِدون أَيّ تَعديل لِـ
    word_class / proof_kind / source / proof_contract /
    closed_class_kind / proof_alternatives.
"""
from __future__ import annotations

import os
from typing import Optional

from .resolution_rules import _strip
from .resolver import ContextualAmbiguityResolver, HANDLED_SURFACES_NORMALIZED

# ─────────────────────────────────────────────────────────────
# Feature flag
# ─────────────────────────────────────────────────────────────
_FLAG_ENV = "ARABIC_ANALYZER_ENABLE_CONTEXTUAL_RESOLVER"
_TRUE_VALUES = {"1", "true", "yes", "on", "True", "TRUE", "YES", "ON"}


def is_enabled() -> bool:
    """True إذا flag مُفَعَّل في environment."""
    val = os.environ.get(_FLAG_ENV, "").strip()
    return val in _TRUE_VALUES


# ─────────────────────────────────────────────────────────────
# Resolver singleton
# ─────────────────────────────────────────────────────────────
_resolver_singleton: Optional[ContextualAmbiguityResolver] = None


def _get_resolver() -> ContextualAmbiguityResolver:
    global _resolver_singleton
    if _resolver_singleton is None:
        _resolver_singleton = ContextualAmbiguityResolver()
    return _resolver_singleton


def reset_integration_stats() -> None:
    """يُصَفِّر إحصاءات الـresolver المُشتَرَك."""
    _get_resolver().reset_stats()


def get_integration_stats() -> dict:
    return _get_resolver().get_stats()


# ─────────────────────────────────────────────────────────────
# Eligibility checks
# ─────────────────────────────────────────────────────────────

# Source-prefix gates allowed in Certificate re-evaluation. See
# PHASE4_CERTIFICATE_REEVALUATION_RULE_LOCK.md §٣.٢ — frozen.
_REEVAL_SOURCE_PREFIXES = (
    "closed_function_word",
    "non_verb_override_gate",
)


def _is_eligible(result: dict, surface: str) -> bool:
    """يَفحَص هل decision مُؤَهَّل لِـ Phase 4 Hypothesis enrichment (الـ path القائِم)."""
    # 1. surface في النِّطاق؟
    normalized = _strip(surface)
    if normalized not in HANDLED_SURFACES_NORMALIZED:
        return False
    # 2. proof_kind == Hypothesis؟
    if result.get("proof_kind") != "Hypothesis":
        return False
    # 3. needs_context OR multiple candidates؟
    needs_ctx = result.get("registry_requires_context", False)
    cands = result.get("registry_candidates") or result.get("proof_alternatives") or []
    has_multi = isinstance(cands, list) and len(cands) >= 2
    return needs_ctx or has_multi


def _is_eligible_for_reevaluation(result: dict, surface: str) -> bool:
    """Phase 4 Certificate Re-evaluation eligibility (metadata-only path).

    Per PHASE4_CERTIFICATE_REEVALUATION_RULE_LOCK.md §٢:
      - surface في HANDLED_SURFACES_NORMALIZED
      - proof_kind == "Certificate"
      - source يَبدَأ بِواحِد مِن _REEVAL_SOURCE_PREFIXES

    لا يَتَفاعَل مَع الـ standard _is_eligible — الِاثنان mutually exclusive عَلى proof_kind.
    """
    # 1. surface في النِّطاق؟
    normalized = _strip(surface)
    if normalized not in HANDLED_SURFACES_NORMALIZED:
        return False
    # 2. proof_kind == Certificate؟
    if result.get("proof_kind") != "Certificate":
        return False
    # 3. source مِن أَحَد الـ gates المَحفوظَة؟
    src = result.get("source") or ""
    return any(src.startswith(p) for p in _REEVAL_SOURCE_PREFIXES)


# ─────────────────────────────────────────────────────────────
# Apply
# ─────────────────────────────────────────────────────────────
def maybe_apply_resolver(
    result: dict,
    surface: str,
    *,
    prev_tokens: Optional[list[str]] = None,
    next_tokens: Optional[list[str]] = None,
) -> dict:
    """تَطبيق Phase 4 resolver إذا flag ON ومُؤَهَّل.

    Returns: dict مُحَدَّث (نَفس الـmutated أَو نَفسه إذا flag OFF).
    """
    # Flag OFF → byte-identical
    if not is_enabled():
        return result

    # ─── Path 1: Hypothesis enrichment (القائِم) ───────────────
    if _is_eligible(result, surface):
        R = _get_resolver()
        if not R.can_resolve(surface):
            return result

        # حِفظ candidates الأَصليَّة
        original_candidates = list(
            result.get("registry_candidates")
            or result.get("proof_alternatives")
            or []
        )

        res = R.resolve(
            surface,
            prev_tokens=list(prev_tokens or []),
            next_tokens=list(next_tokens or []),
        )

        # rule 1: Certificate → تَرقيَة
        if res.certainty == "Certificate":
            result["word_class"] = res.selected_class
            result["source"] = "ContextualAmbiguityResolver"
            result["proof_kind"] = "Certificate"
            result["proof_contract"] = "Phase4:ContextualAmbiguityResolver"
            # احذِف blockers (نَحن واثِقون الآن)
            result["proof_blockers"] = []
            # alternatives = original candidates ما عَدا المُختار
            result["proof_alternatives"] = [
                c for c in original_candidates if c != res.selected_class
            ]
            result["phase4_selected_function"] = res.selected_function
            result["phase4_reason"] = res.reason
            result["phase4_context_features"] = res.context_features
            result["phase4_masaq_compatible_class"] = res.masaq_compatible_class
            result["phase4_original_candidates"] = original_candidates
            return result

        # rule 2: Hypothesis (function clear) → metadata فَقَط
        if res.certainty == "Hypothesis" and res.selected_function != "unresolved_ambiguous":
            result["phase4_selected_function"] = res.selected_function
            result["phase4_reason"] = res.reason
            result["phase4_context_features"] = res.context_features
            result["phase4_masaq_compatible_class"] = res.masaq_compatible_class
            result["phase4_original_candidates"] = original_candidates
            # لا نُرَقّي. لا نُغَيِّر word_class.
            return result

        # rule 3: unresolved_ambiguous → لا تَغيير
        return result

    # ─── Path 2: Certificate Re-evaluation (metadata-only) ─────
    # Added 2026-05-26 per PHASE4_CERTIFICATE_REEVALUATION_RULE_LOCK.md §٢.
    # Mutually exclusive مَع Path 1 (Path 1 يَتَطَلَّب Hypothesis، Path 2 يَتَطَلَّب
    # Certificate). Path 2 لا يَمَسّ أَيّ حَقل غَير مَسبوق بِـ phase4_.
    if _is_eligible_for_reevaluation(result, surface):
        R = _get_resolver()
        if not R.can_resolve(surface):
            return result

        # Snapshot — يَجِب أَن نُمَيِّز originals قَبل أَيّ تَعديل (مَع أَنَّ هَذا الفَرع
        # لا يُعَدِّل أَصلًا، لِكَن الـ snapshot حَقّ تَتَبُّع).
        original_word_class = result.get("word_class")
        original_source = result.get("source")
        original_proof_kind = result.get("proof_kind")
        original_candidates = list(
            result.get("registry_candidates")
            or result.get("proof_alternatives")
            or []
        )

        res = R.resolve(
            surface,
            prev_tokens=list(prev_tokens or []),
            next_tokens=list(next_tokens or []),
        )

        # تَطبيق phase4_certainty derivation (per RULE_LOCK §٢.٢):
        if res.selected_function == "unresolved_ambiguous":
            phase4_certainty = "Hypothesis"
        else:
            phase4_certainty = res.certainty  # "Certificate" أَو "Hypothesis"

        # إِلصاق metadata فَقَط (كُلّ المَفاتيح مَسبوقَة بِـ phase4_):
        result["phase4_review_mode"] = "certificate_re_evaluation"
        result["phase4_original_word_class"] = original_word_class
        result["phase4_original_source"] = original_source
        result["phase4_original_proof_kind"] = original_proof_kind
        result["phase4_original_candidates"] = original_candidates
        result["phase4_source"] = "ContextualAmbiguityResolver"
        result["phase4_selected_function"] = res.selected_function
        result["phase4_reason"] = res.reason
        result["phase4_context_features"] = res.context_features
        result["phase4_masaq_compatible_class"] = res.masaq_compatible_class
        result["phase4_certainty"] = phase4_certainty
        return result

    # ─── Else: خارِج النِّطاق → لا تَغيير ──────────────────────
    return result


__all__ = [
    "is_enabled",
    "maybe_apply_resolver",
    "reset_integration_stats",
    "get_integration_stats",
    "_is_eligible",
    "_is_eligible_for_reevaluation",
]
