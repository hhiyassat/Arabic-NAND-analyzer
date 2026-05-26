"""resolution_rules.py — قَواعِد سِياقيَّة لِـ 7 ambiguous surfaces.

كُلّ rule يَأخُذ context_features ويُرجِع Resolution.

Certificate policy (مِن العَقد):
  • strong context evidence
  • no conflicting candidate remains
  • no blockers
  • reason is explicit
وَإِلّا → Hypothesis.
"""
from __future__ import annotations

import re
from typing import Optional

from .schema import Resolution

# Normalize for matching
_DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭ]")
_ALEF_VARIANTS = re.compile(r"[ٱآأإ]")


def _strip(s: str) -> str:
    s = _DIACRITICS.sub("", s or "")
    s = _ALEF_VARIANTS.sub("ا", s)
    return s


# ─────────────────────────────────────────────────────────────
# مَن  vs  مِن (الفَرق بِالشَّكل: مَن = اسم، مِن = حَرف جَرّ)
# ─────────────────────────────────────────────────────────────
def resolve_man(surface: str, ctx: dict) -> Resolution:
    """مَن: relative / conditional / interrogative / unresolved."""
    bare = _strip(surface)
    norm = bare

    # مِنْ (kasra) → preposition. مَن (fatha) → relative/conditional/interrogative
    if "مِنْ" in surface or "مِّن" in surface or surface == "مِن":
        return Resolution(
            surface=surface, normalized=norm,
            selected_class="HARF",
            selected_function="prepositional_phrase_component",
            candidates=["HARF"],
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="HARF",
            reason="مِن (kasra) = حَرف جَرّ — لا غموض",
        )

    # مَن: تَحقَّق مِن سِياق
    candidates = ["ISM_MAWSOOL", "ISM_MABNI", "HARF"]
    reasons = []

    # سِياق استِفهام
    if ctx.get("preceded_by_question_verb") or ctx.get("preceded_by_interrogative_particle"):
        reasons.append("preceded_by_question_context")
        return Resolution(
            surface=surface, normalized=norm,
            selected_class="ISM_MABNI",
            selected_function="interrogative_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MABNI",
            reason="; ".join(reasons),
        )

    # سِياق شَرط (مُضارِع مَجزوم + جَواب)
    if ctx.get("next_is_jussive_verb") and ctx.get("has_jawab_al_shart_pattern"):
        return Resolution(
            surface=surface, normalized=norm,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MABNI",
            reason="jussive_verb + jawab_al_shart",
        )

    # شَرط بِدون جواب صَريح → Hypothesis
    if ctx.get("next_is_jussive_verb"):
        return Resolution(
            surface=surface, normalized=norm,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MABNI",
            needs_context=True,
            reason="jussive only, no clear jawab",
        )

    # اسم مَوصول: مَن + clause (فِعل لَيس مَجزومًا)
    if ctx.get("next_is_present_verb") or ctx.get("next_is_past_verb"):
        return Resolution(
            surface=surface, normalized=norm,
            selected_class="ISM_MAWSOOL",
            selected_function="relative_pronoun",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MAWSOOL",
            needs_context=True,
            reason="followed by verb, default relative",
        )

    # السِياق غَير كافٍ
    return Resolution(
        surface=surface, normalized=norm,
        selected_class="ISM_MABNI",
        selected_function="unresolved_ambiguous",
        candidates=candidates,
        context_features=ctx,
        certainty="Hypothesis",
        masaq_compatible_class="ISM_MABNI",
        needs_context=True,
        blockers=["insufficient_context"],
        reason="no context signals",
    )


# ─────────────────────────────────────────────────────────────
# ما
# ─────────────────────────────────────────────────────────────
def resolve_ma(surface: str, ctx: dict) -> Resolution:
    """ما: relative / negative / conditional / interrogative / extra / unresolved."""
    bare = _strip(surface)
    candidates = ["HARF", "ISM_MAWSOOL", "ISM_MABNI"]

    # سِياق استِفهام
    if ctx.get("preceded_by_question_verb") or ctx.get("preceded_by_interrogative_particle"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="interrogative_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MABNI",
            reason="preceded_by_question_context",
        )

    # سِياق شَرط (jussive + jawab)
    if ctx.get("next_is_jussive_verb") and ctx.get("has_jawab_al_shart_pattern"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MABNI",
            reason="jussive_verb + jawab_al_shart",
        )

    if ctx.get("next_is_jussive_verb"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MABNI",
            needs_context=True,
            reason="jussive only",
        )

    # ما النافِيَة: ما + فِعل ماضٍ (وَلَيس في سِياق مَوصول)
    if ctx.get("next_is_past_verb") and not ctx.get("preceded_by_preposition"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="HARF",
            selected_function="negative_particle",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="HARF",
            needs_context=True,
            reason="followed_by_past_verb (negation pattern)",
        )

    # ما المَوصولَة: ما + فِعل مُضارِع (لَيس مَجزومًا) في سِياق clause
    if ctx.get("next_is_present_verb") and not ctx.get("next_is_jussive_verb"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MAWSOOL",
            selected_function="relative_pronoun",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MAWSOOL",
            needs_context=True,
            reason="followed_by_present_verb, default relative",
        )

    # ما الزائِدَة: بَعد حَرف جَرّ مُحَدَّد (إِنَّما) — نَتَرُكها Hypothesis
    if ctx.get("preceded_by_preposition") and not ctx.get("next_is_present_verb"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="HARF",
            selected_function="extra_particle",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="HARF",
            needs_context=True,
            reason="after_preposition, possibly extra particle",
        )

    return Resolution(
        surface=surface, normalized=bare,
        selected_class="ISM_MABNI",
        selected_function="unresolved_ambiguous",
        candidates=candidates,
        context_features=ctx,
        certainty="Hypothesis",
        masaq_compatible_class="ISM_MABNI",
        needs_context=True,
        blockers=["insufficient_context"],
        reason="no context signals",
    )


# ─────────────────────────────────────────────────────────────
# أَيّ
# ─────────────────────────────────────────────────────────────
def resolve_ayy(surface: str, ctx: dict) -> Resolution:
    bare = _strip(surface)
    candidates = ["ISM_MABNI", "ISM_MUARAB", "ISM_MAWSOOL"]

    if ctx.get("preceded_by_question_verb") or ctx.get("preceded_by_interrogative_particle"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MUARAB",
            selected_function="interrogative_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MUARAB",
            reason="question_context",
        )

    if ctx.get("next_is_jussive_verb") and ctx.get("has_jawab_al_shart_pattern"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MUARAB",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class="ISM_MUARAB",
            reason="jussive + jawab",
        )

    # idafa: أَيّ + اسم مَجرور
    if ctx.get("next_is_genitive_nominal") or ctx.get("next_starts_with_alef_lam"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MUARAB",
            selected_function="interrogative_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MUARAB",
            needs_context=True,
            reason="idafa pattern, often interrogative",
        )

    return Resolution(
        surface=surface, normalized=bare,
        selected_class="ISM_MUARAB",
        selected_function="unresolved_ambiguous",
        candidates=candidates,
        context_features=ctx,
        certainty="Hypothesis",
        masaq_compatible_class="ISM_MUARAB",
        needs_context=True,
        blockers=["insufficient_context"],
        reason="no clear signal",
    )


# ─────────────────────────────────────────────────────────────
# مَتى / أَين / أَنّى / حَيث (ظُروف)
# ─────────────────────────────────────────────────────────────
def _resolve_locative_or_temporal(
    surface: str, ctx: dict, *,
    kind: str,  # "temporal" or "locative" or "manner"
    masaq_class: str,  # what MASAQ tags it
) -> Resolution:
    bare = _strip(surface)
    func_map = {"temporal": "temporal_adverb", "locative": "locative_adverb",
                "manner": "locative_adverb"}  # manner ≈ locative in this schema
    base_function = func_map[kind]
    candidates = ["ISM_MABNI", masaq_class]

    if ctx.get("preceded_by_question_verb") or ctx.get("preceded_by_interrogative_particle"):
        # interrogative + adverbial — كَلاهُما
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="interrogative_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class=masaq_class,
            reason=f"question_context; functions as {base_function}+interrogative",
        )

    if ctx.get("next_is_jussive_verb") and ctx.get("has_jawab_al_shart_pattern"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Certificate",
            masaq_compatible_class=masaq_class,
            reason=f"jussive + jawab; functions as {base_function}+conditional",
        )

    if ctx.get("next_is_jussive_verb"):
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class=masaq_class,
            needs_context=True,
            reason="jussive only",
        )

    # default: adverbial
    return Resolution(
        surface=surface, normalized=bare,
        selected_class="ISM_MABNI",
        selected_function=base_function,
        candidates=candidates,
        context_features=ctx,
        certainty="Hypothesis",
        masaq_compatible_class=masaq_class,
        needs_context=True,
        reason=f"default {base_function}",
    )


def resolve_mata(surface: str, ctx: dict) -> Resolution:
    return _resolve_locative_or_temporal(surface, ctx, kind="temporal", masaq_class="HARF")


def resolve_ayna(surface: str, ctx: dict) -> Resolution:
    return _resolve_locative_or_temporal(surface, ctx, kind="locative", masaq_class="HARF")


def resolve_anna(surface: str, ctx: dict) -> Resolution:
    return _resolve_locative_or_temporal(surface, ctx, kind="manner", masaq_class="HARF")


def resolve_haythu(surface: str, ctx: dict) -> Resolution:
    """حَيث: غالِبًا ظَرف مَكان (locative_adverb)."""
    bare = _strip(surface)
    candidates = ["ISM_MABNI"]

    if ctx.get("next_is_jussive_verb"):
        # حَيث + مُضارِع مَجزوم → شَرط (حَيثُما)
        return Resolution(
            surface=surface, normalized=bare,
            selected_class="ISM_MABNI",
            selected_function="conditional_tool",
            candidates=candidates,
            context_features=ctx,
            certainty="Hypothesis",
            masaq_compatible_class="ISM_MABNI",
            needs_context=True,
            reason="jussive after حَيث (conditional usage)",
        )

    # default: ظَرف مَكان
    return Resolution(
        surface=surface, normalized=bare,
        selected_class="ISM_MABNI",
        selected_function="locative_adverb",
        candidates=candidates,
        context_features=ctx,
        certainty="Hypothesis",
        masaq_compatible_class="ISM_MABNI",
        needs_context=True,
        reason="default locative",
    )


# ─────────────────────────────────────────────────────────────
# Compounds: بِمَا
# ─────────────────────────────────────────────────────────────
def resolve_bima(surface: str, ctx: dict) -> Resolution:
    """بِما = بِ + ما. حَلّ ما داخِليًّا."""
    # نَستَدعي resolve_ma عَلى الجُزء الثَّاني
    inner = resolve_ma("ما", ctx)
    return Resolution(
        surface=surface,
        normalized="بما",
        selected_class="HARF",
        selected_function="prepositional_phrase_component",
        candidates=["HARF"],
        context_features={**ctx, "compound_split": "بِ + ما",
                          "embedded_ma_function": inner.selected_function,
                          "embedded_ma_certainty": inner.certainty},
        certainty="Certificate",
        masaq_compatible_class="HARF",
        reason=f"compound: prep + ma ({inner.selected_function})",
    )


# ─────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────
_RULES = {
    "مَن": resolve_man, "من": resolve_man,
    "ما": resolve_ma, "مَا": resolve_ma,
    "أَيّ": resolve_ayy, "أَيُّ": resolve_ayy, "أَيَّ": resolve_ayy,
    "أي": resolve_ayy, "أيّ": resolve_ayy,
    "مَتَى": resolve_mata, "متى": resolve_mata, "مَتى": resolve_mata,
    "أَيْنَ": resolve_ayna, "أَين": resolve_ayna, "أين": resolve_ayna,
    "أَنَّى": resolve_anna, "أنى": resolve_anna, "أَنّى": resolve_anna,
    "حَيْثُ": resolve_haythu, "حَيث": resolve_haythu, "حيث": resolve_haythu,
    "بِمَا": resolve_bima, "بما": resolve_bima, "بِما": resolve_bima,
}


def get_rule(surface: str):
    """يُرجِع rule function لِـ surface (None إذا غَير مَدعوم)."""
    if surface in _RULES:
        return _RULES[surface]
    # tolerance: حاوِل normalize خَفيف
    bare = _strip(surface)
    return _RULES.get(bare)


__all__ = ["get_rule", "resolve_man", "resolve_ma", "resolve_ayy",
           "resolve_mata", "resolve_ayna", "resolve_anna", "resolve_haythu",
           "resolve_bima"]
