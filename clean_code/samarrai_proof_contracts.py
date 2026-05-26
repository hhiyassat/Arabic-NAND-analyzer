"""samarrai_proof_contracts.py — أَسماء العُقود لِـ SamarraiAnalyzer.

كُلّ ادِّعاء في SamarraiClaim يُسَنَد إلى عَقد مَعروف بِالاسم لِيُجيب عَن:
«مِن أَيّ عَقد خَرَجت؟»

CONSTITUTIONAL (MC):
  • Certificate — exact vocalized match مَع المُجَلَّد المَصدر
  • Hypothesis — prefix-stripped أَو plain fallback
  • Zero — لا تَطابُق (لا يُنتَج SamarraiClaim أَصلًا)
"""

from typing import Literal

ProofKind = Literal["Certificate", "Hypothesis", "Zero"]

# ─── العُقود ───────────────────────────────────────────────────────

CONTRACT_EXACT_VOCALIZED = "ExactVocalizedSamarraiContract:v1"
# مُطابَقَة تامَّة مَع vocalized_form في CSV — Certificate

CONTRACT_PREFIX_STRIPPED = "PrefixStrippedSamarraiContract:v1"
# نَزَعنا بادِئَة (و، ف، ب، ل، س، ك، ال) ثُمّ مُطابَقَة exact — Hypothesis
# blocker: «الكَلِمَة الكامِلَة بِالبادِئَة لا تُطابِق KB»

CONTRACT_PREFIX_AS_OPERATOR = "PrefixAsOperatorSamarraiContract:v1"
# الحَرف البادِئ نَفسه مُطابِق لِعامِل (بِ، لِ، كَ، وَ، فَ، سَ) — Hypothesis
# blocker: «نَستَخرِج العامِل البادِئ مُنفَرِدًا، لا الكَلِمَة كامِلَة»

CONTRACT_PLAIN_FALLBACK = "PlainFallbackSamarraiContract:v1"
# مُطابَقَة plain (بَعد نَزع التَّشكيل) — Hypothesis قَويّ blocker
# blocker: «التَّشكيل في المُدخَل لا يُطابِق التَّشكيل المَخزون — قَد تَكون كَلِمَة مُختَلِفَة»

CONTRACT_PATTERN_CONSTRUCTION = "PatternConstructionContract:v1"
# تَركيب مَكشوف بِنَمَط (TAQDIM، TAHZHEER) — Hypothesis لأنّه يَعتَمِد على Heuristic

CONTRACT_NO_MATCH = "NoMatchContract:v1"
# لا شَيء — Zero (لا يُنتَج عادَةً، فَقَط لِلتَّوثيق)


# ─── دَوال مُساعِدَة ────────────────────────────────────────────────

def kind_for_match_type(match_type: str) -> tuple[ProofKind, str]:
    """يُعيد (ProofKind, contract_name) بِحَسَب نَوع المُطابَقَة."""
    if match_type == "exact_vocalized":
        return "Certificate", CONTRACT_EXACT_VOCALIZED
    elif match_type == "prefix_stripped":
        return "Hypothesis", CONTRACT_PREFIX_STRIPPED
    elif match_type == "prefix_as_operator":
        return "Hypothesis", CONTRACT_PREFIX_AS_OPERATOR
    elif match_type == "plain_fallback":
        return "Hypothesis", CONTRACT_PLAIN_FALLBACK
    elif match_type == "pattern_construction":
        return "Hypothesis", CONTRACT_PATTERN_CONSTRUCTION
    else:
        return "Zero", CONTRACT_NO_MATCH


def blockers_for_match_type(match_type: str) -> list[str]:
    """يُرجِع البَقايا المانِعَة لِكُلّ نَوع مُطابَقَة."""
    if match_type == "exact_vocalized":
        return []   # لا بَقايا — Certificate
    elif match_type == "prefix_stripped":
        return ["نَزعنا بادِئَة (و/ف/ب/ل/س/ك/ال) — لَو الكَلِمَة الأَصليَّة في KB كانَت تَفضِل"]
    elif match_type == "prefix_as_operator":
        return ["الكَلِمَة الكامِلَة لَم تَتَطابَق — نَستَخرِج الحَرف البادِئ كَعامِل"]
    elif match_type == "plain_fallback":
        return [
            "التَّشكيل في المُدخَل لا يُطابِق التَّشكيل المَخزون",
            "قَد تَكون الكَلِمَتان مُختَلِفَتَين تَمامًا (مِثل رَبِّ vs رُبَّ)",
        ]
    elif match_type == "pattern_construction":
        return ["النَّمَط heuristic — قَد يُخطِئ في حالات نادِرَة"]
    else:
        return ["لا تَطابُق"]


def confidence_for_match_type(match_type: str) -> float:
    """نِسبَة الثِّقَة الافتِراضيَّة بِحَسَب نَوع المُطابَقَة."""
    return {
        "exact_vocalized": 0.95,
        "prefix_stripped": 0.85,
        "prefix_as_operator": 0.80,
        "plain_fallback": 0.50,
        "pattern_construction": 0.85,
    }.get(match_type, 0.0)
