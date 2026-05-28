"""Layer 3 — Role classifier.

Given a sentence with Layer-1 (WordClass) and Layer-2 (Case+Mark) filled in,
assign each token a syntactic role (مبتدأ / فاعل / مفعول به / خبر / نعت /
بدل / معطوف / مضاف إليه / اسم مجرور / اسم إنّ / خبر إنّ / حرف ...).

The Quran's i3rab has 3,855 distinct role phrases. We map our predictions
to a coarse set of ~25 PRIMARY roles. Phase 3 v1 covers:

  - حرف جر         → "حرف جر"
  - حرف عطف        → "حرف عطف"
  - حرف نصب        → "حرف نصب"
  - حرف جزم        → "حرف جزم"
  - حرف نفي        → "حرف نفي"
  - ضمير           → "ضمير منفصل/متّصل"
  - اسم مجرور      → اسم بعد حرف جر
  - مفعول به       → اسم منصوب بعد فعل متعدّ
  - فاعل           → اسم مرفوع بعد فعل
  - مبتدأ          → اسم مرفوع أوّل جملة اسمية (لا فعل قبله)
  - خبر            → اسم مرفوع بعد مبتدأ
  - اسم إنّ        → اسم منصوب بعد إنّ/أنّ/كأنّ/لكنّ/لعلّ/ليت
  - خبر إنّ        → اسم مرفوع بعد اسم إنّ
  - نعت            → اسم يطابق ما قبله في الإعراب والتعريف
  - معطوف          → اسم بعد حرف عطف (و/ف/ثمّ/أو) ويتبعه في الإعراب
  - مضاف إليه      → اسم مجرور غير مسبوق بحرف جر
  - فعل ماضٍ/مضارع/أمر — بالنسبة للأفعال

Rules are positional + case-aware. Sentence-level structure (clauses,
nested جمل) is NOT yet handled — that comes with M1.A.
"""

from __future__ import annotations

# Closed-class form sets — loaded from canonical contract files.
# Per 14_Minimal_Complete_Theory.md, no hidden contracts in code.
import sys as _sys
from pathlib import Path as _Path
_CC = _Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_CC))
try:
    from contracts_loader import load_harf_inna, load_kana_family
    _HAROF_INNA = load_harf_inna()
    _KANA_FAMILY = load_kana_family()
except ImportError:
    _HAROF_INNA = set()
    _KANA_FAMILY = set()


def _strip_diac(s: str) -> str:
    from wazn_data import DIACRITICS  # type: ignore
    return "".join(c for c in (s or "") if c not in DIACRITICS)


# PATCH 3 FIXUP (2026-05-26) — FunctionalNounIdafaContract (L3 side).
# Functional locative/temporal nouns (بَيْنَ، عِندَ، تَحْتَ، فَوْقَ، قَبْلَ،
# بَعْدَ، ...) are ظُروف — they take case mechanically but their syntactic
# role is ظَرف (adverbial), NOT the generic case-based fallback "اسم مجزوم"
# / "اسم منصوب". They almost always head an إِضافَة (بَيْنَكُمْ = بَيْنَ
# مُضاف + كُمْ مُضاف إِليه). Override the role at L3 to ظَرف مكان (kept as
# a Certificate) so downstream readers see a linguistically valid role
# instead of a case-only fallback.
def _load_functional_locative_stems() -> set:
    """Plain-text stems of LOCATIVE functional nouns only.
    Source: data/contracts/lists/functional_nouns_lexicon.csv,
    filtered to rows with category="locative".

    PATCH 4.5 (2026-05-26): the lexicon also contains non-locative
    categories (quantifier, exception, interrog, similitive, time-adv).
    The L3 ظَرف-مَكان override must NOT fire for those — e.g. كُلَّ
    (category=quantifier) was incorrectly getting role=ظرف مكان when
    appearing in بِكُلِّ. Restrict to category=locative; other categories
    fall back to the normal RoleRulesContract path.
    """
    here = _Path(__file__).resolve().parent.parent
    path = here / "data" / "contracts" / "lists" / "functional_nouns_lexicon.csv"
    s: set = set()
    if not path.is_file():
        return s
    import csv as _csv
    with path.open(encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            category = (row.get("category") or "").strip().lower()
            if category != "locative":
                continue
            surf = (row.get("surface") or "").strip()
            if surf:
                s.add(_strip_diac(surf))
    return s


_FUNCTIONAL_LOCATIVE_STEMS = _load_functional_locative_stems()


def _is_functional_locative_noun(t) -> bool:
    """True if the token's stem (diacritic-stripped) is a LOCATIVE
    functional noun like بَيْنَ، عِندَ، تَحْتَ، فَوْقَ. Stems are matched
    after stripping diacritics so the shadda-elision form بَّيْنَ matches
    بَيْنَ. Non-locative entries (quantifier, exception, etc.) are
    excluded by category — see PATCH 4.5."""
    stem = getattr(t, "stem", "") or t.token or ""
    return _strip_diac(stem) in _FUNCTIONAL_LOCATIVE_STEMS


class RoleClassifier:
    """Assign role per token via RoleRulesContract (data-driven)."""

    def __init__(self) -> None:
        try:
            import sys as _sys
            from pathlib import Path as _Path
            _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
            from role_rules_contract import RoleRulesContract
            self._role_rules = RoleRulesContract()
        except ImportError:
            self._role_rules = None

    def _set_role(self, t, *, phrase, source, kind, contract,
                  blockers=None, alternatives=None):
        t.role_phrase = phrase
        t.role_source = source
        t.role_kind = kind
        t.role_contract = contract
        if blockers:
            t.role_blockers = list(blockers)
        if alternatives:
            t.role_alternatives = list(alternatives)

    def classify_sentence(self, sent) -> None:
        tokens = sent.tokens
        n = len(tokens)
        # First pass: assign roles for HARF and ISM_MABNI tokens
        for i, t in enumerate(tokens):
            if t.word_class == "HARF":
                self._assign_harf_role(t)
            elif t.word_class == "ISM_MABNI":
                self._set_role(
                    t, phrase="اسم مبني",
                    source="ism_mabni_default",
                    kind="Certificate",
                    contract="ism_mabni_by_class",
                )
            elif t.word_class == "JALALAH":
                # Will be refined in second pass via case
                pass
            elif t.word_class == "FIIL":
                if t.verb_aspect == "PV":
                    self._set_role(
                        t, phrase="فعل ماضٍ", source="fiil_aspect:PV",
                        kind="Certificate", contract="verb_aspect_PV",
                    )
                elif t.verb_aspect == "IV":
                    self._set_role(
                        t, phrase="فعل مضارع", source="fiil_aspect:IV",
                        kind="Certificate", contract="verb_aspect_IV",
                    )
                elif t.verb_aspect == "CV":
                    self._set_role(
                        t, phrase="فعل أمر", source="fiil_aspect:CV",
                        kind="Certificate", contract="verb_aspect_CV",
                    )
                else:
                    self._set_role(
                        t, phrase="فعل", source="fiil_default",
                        kind="Hypothesis", contract="fiil_aspect_unknown",
                        blockers=["verb_aspect_not_determined"],
                    )

        # Second pass: positional rules for ISM_MUARAB / JAMID / AALAM / JALALAH
        # Track context as we walk left-to-right
        ctx = {
            "saw_inna": False,        # هل رأينا حرف نصب من إنّ وأخواتها
            "inna_subj_set": False,   # هل أعطينا اسم إنّ بالفعل
            "saw_kana": False,
            "kana_subj_set": False,
            "last_verb_idx": -1,
            "last_verb_obj_set": False,
            "in_genitive_chain": False,  # تتابع مضاف+مضاف إليه
            "saw_mubtada": False,
            "saw_khabar": False,
        }

        for i, t in enumerate(tokens):
            if t.word_class in {"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"}:
                self._assign_ism_role(t, i, tokens, ctx)
            # Update context after assigning this token
            self._update_ctx(t, i, ctx)

    def _assign_harf_role(self, t) -> None:
        kind = t.closed_class_kind or ""
        mapping = {
            "HARF_JARR": "حرف جر",
            "HARF_ATF": "حرف عطف",
            "HARF_NASB": "حرف نصب",
            "HARF_JAZM": "حرف جزم",
            "HARF_NAFI": "حرف نفي",
            "HARF_NAFY": "حرف نفي",
            "HARF_NIDA": "حرف نداء",
            "HARF_TAWKEED": "حرف توكيد",
            "HARF_ISTIFHAM": "حرف استفهام",
            "HARF_ISTINAAD": "حرف استئناف",
        }
        phrase = mapping.get(kind, "حرف")
        if kind in mapping:
            self._set_role(
                t, phrase=phrase, source=f"harf_kind:{kind}",
                kind="Certificate", contract=f"harf_kind:{kind}",
            )
        else:
            # generic HARF — we know it's a particle but not which type
            self._set_role(
                t, phrase="حرف", source="harf_kind:generic",
                kind="Hypothesis", contract="harf_kind_generic",
                blockers=["no_specific_harf_subtype"],
            )

    def _assign_ism_role(self, t, i: int, tokens, ctx) -> None:
        """Assign role for ISM via RoleRulesContract (data-driven)."""
        prev = tokens[i - 1] if i > 0 else None

        # PATCH 11 (2026-05-28) — Temporal/conditional particle role.
        # Tokens like إِذَا / إِذ / لَمَّا are ظَرف زَمان / أَداة شَرط,
        # never مفعول به. L3's case-based RoleRulesContract picks
        # `مفعول به منصوب` for them because case_id=2 (accusative
        # form) and there's a verb in scope. Force the correct role
        # before the case-rules fire.
        _surf = (getattr(t, "token", "") or "").strip()
        _surf_plain = "".join(c for c in _surf if c not in "ًٌٍَُِّْـٰٓ")
        _surf_plain = (_surf_plain
                        .replace("ٱ", "ا").replace("أ", "ا")
                        .replace("إ", "ا").replace("آ", "ا"))
        if _surf_plain in ("اذا", "اذ", "لما"):
            self._set_role(
                t,
                phrase="ظرف شرط",
                source="patch11_temporal_conditional_particle",
                kind="Certificate",
                contract="TemporalConditionalParticleContract:patch11",
            )
            return

        # PATCH 3 FIXUP (2026-05-26) — FunctionalNounIdafaContract.
        # Fires BEFORE the case-based RoleRulesContract because functional
        # locative nouns (بَيْنَ، عِندَ، تَحْتَ، ...) must NOT receive the
        # generic case-only fallback "اسم مجزوم" / "اسم منصوب". They are
        # ظُروف whose role is ظَرف مَكان مُضاف (adverbial, head of إِضافَة).
        if _is_functional_locative_noun(t):
            self._set_role(
                t,
                phrase="ظرف مكان",
                source="functional_noun_locative",
                kind="Certificate",
                contract="FunctionalNounIdafaContract:locative",
            )
            return

        # New path: delegate to RoleRulesContract if available
        if self._role_rules is not None:
            result = self._role_rules.apply(t, prev, ctx, tokens, i)
            if result is not None:
                self._set_role(
                    t,
                    phrase=result["role_phrase"],
                    source=result["contract"],
                    kind=result["role_kind"],
                    contract=result["contract"],
                )
                self._role_rules.apply_side_effects(result["rule_name"], ctx)
                return
            # Fallthrough to legacy if no rule matched

        # === LEGACY PATH (kept for safety) ===
        # Rule 1: اسم مجرور بعد حرف جر
        if prev and prev.word_class == "HARF" and prev.closed_class_kind == "HARF_JARR":
            self._set_role(
                t, phrase="اسم مجرور",
                source=f"after_HARF_JARR({prev.token})",
                kind="Certificate",
                contract=f"after_HARF_JARR:{prev.token}",
            )
            return

        # === Rule 2: اسم إنّ — منصوب بعد إنّ وأخواتها ===
        if (
            prev and prev.word_class == "HARF"
            and _strip_diac(prev.token) in _HAROF_INNA
            and t.case_id == 2
        ):
            self._set_role(
                t, phrase=f"اسم ({prev.token}) منصوب",
                source=f"ism_inna_after({prev.token})",
                kind="Certificate",
                contract=f"ism_inna_after:{prev.token}",
            )
            ctx["inna_subj_set"] = True
            return

        # === Rule 3: خبر إنّ — مرفوع بعد اسم إنّ ===
        if ctx.get("saw_inna") and ctx.get("inna_subj_set") and t.case_id == 1:
            self._set_role(
                t, phrase="خبر (إنّ) مرفوع",
                source="khabar_inna",
                kind="Hypothesis",
                contract="khabar_inna_positional",
                alternatives=[
                    {"role": "نعت", "reason": "if_agrees_with_ism_inna"},
                ],
            )
            ctx["inna_subj_set"] = False  # consumed
            return

        # === Rule 4: مفعول به — منصوب بعد فعل ===
        if (
            ctx.get("last_verb_idx") >= 0
            and not ctx.get("last_verb_obj_set")
            and t.case_id == 2
            and not any(
                tk.word_class == "HARF"
                and tk.closed_class_kind == "HARF_JARR"
                for tk in tokens[ctx["last_verb_idx"] + 1 : i]
            )
        ):
            self._set_role(
                t, phrase="مفعول به منصوب",
                source="mafool_bih_after_verb",
                kind="Hypothesis",
                contract="mafool_bih_positional",
                alternatives=[
                    {"role": "حال", "reason": "if_indefinite_after_complete_verb"},
                    {"role": "تمييز", "reason": "if_specifies_ambiguous_noun"},
                ],
            )
            ctx["last_verb_obj_set"] = True
            return

        # === Rule 5: فاعل — مرفوع بعد فعل ===
        if (
            ctx.get("last_verb_idx") >= 0
            and t.case_id == 1
            and not any(
                tk.case_id == 1
                for tk in tokens[ctx["last_verb_idx"] + 1 : i]
                if tk.word_class in {"ISM_MUARAB", "JAMID", "AALAM"}
            )
        ):
            self._set_role(
                t, phrase="فاعل مرفوع",
                source="faail_after_verb",
                kind="Hypothesis",
                contract="faail_positional",
                alternatives=[
                    {"role": "نائب فاعل", "reason": "if_verb_is_passive"},
                ],
            )
            return

        # === Rule 6: مبتدأ — مرفوع، لا فعل قبله ===
        if t.case_id == 1 and ctx.get("last_verb_idx") < 0 and not ctx.get("saw_mubtada"):
            self._set_role(
                t, phrase="مبتدأ مرفوع",
                source="mubtada_first_marfu",
                kind="Hypothesis",
                contract="mubtada_first_marfu_no_verb",
                alternatives=[
                    {"role": "خبر مقدّم", "reason": "if_inverted_nominal_sentence"},
                ],
            )
            ctx["saw_mubtada"] = True
            return

        # === Rule 7: خبر — مرفوع بعد مبتدأ ===
        if t.case_id == 1 and ctx.get("saw_mubtada") and not ctx.get("saw_khabar"):
            self._set_role(
                t, phrase="خبر مرفوع",
                source="khabar_after_mubtada",
                kind="Hypothesis",
                contract="khabar_after_mubtada",
                alternatives=[
                    {"role": "بدل", "reason": "if_substitutes_mubtada"},
                    {"role": "نعت", "reason": "if_agrees_in_def_with_mubtada"},
                ],
            )
            ctx["saw_khabar"] = True
            return

        # === Rule 8: نعت — يطابق ما قبله في الإعراب والتعريف ===
        if (
            prev
            and prev.word_class in {"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"}
            and prev.case_id == t.case_id
            and prev.case_id is not None
        ):
            prev_plain = _strip_diac(prev.token)
            this_plain = _strip_diac(t.token)
            both_def = prev_plain.startswith("ال") and this_plain.startswith("ال")
            both_indef = not prev_plain.startswith("ال") and not this_plain.startswith("ال")
            if both_def or both_indef:
                case_name = ["", "مرفوع", "منصوب", "مجرور", "مجزوم", "مبني"][t.case_id]
                self._set_role(
                    t, phrase=f"نعت {case_name}",
                    source="naat_agrees_prev",
                    kind="Hypothesis",
                    contract="naat_case_def_agreement",
                    alternatives=[
                        {"role": "بدل", "reason": "if_independent_referent"},
                        {"role": "عطف بيان", "reason": "if_clarifying"},
                    ],
                )
                return

        # === Rule 9: مضاف إليه — مجرور غير مسبوق بحرف جر ===
        if (
            t.case_id == 3
            and prev
            and prev.word_class in {"ISM_MUARAB", "JAMID", "AALAM", "JALALAH"}
        ):
            self._set_role(
                t, phrase="مضاف إليه مجرور",
                source="mudaf_ilayh",
                kind="Hypothesis",
                contract="mudaf_ilayh_positional",
                alternatives=[
                    {"role": "نعت مجرور", "reason": "if_agrees_with_prev"},
                ],
            )
            return

        # === Rule 10: معطوف — بعد حرف عطف ===
        if (
            prev
            and prev.word_class == "HARF"
            and prev.closed_class_kind == "HARF_ATF"
            and t.case_id is not None
        ):
            case_name = ["", "مرفوع", "منصوب", "مجرور", "مجزوم", "مبني"][t.case_id]
            self._set_role(
                t, phrase=f"معطوف {case_name}",
                source=f"maotoof_after_ATF({prev.token})",
                kind="Certificate",
                contract=f"maotoof_after_ATF:{prev.token}",
            )
            return

        # === Fallback: case-based generic label — Hypothesis with blocker ===
        if t.case_id == 1:
            phrase = "اسم مرفوع"
        elif t.case_id == 2:
            phrase = "اسم منصوب"
        elif t.case_id == 3:
            phrase = "اسم مجرور"
        elif t.case_id == 4:
            phrase = "اسم مجزوم"
        elif t.case_id == 5:
            phrase = "اسم مبني"
        else:
            phrase = "اسم"
        self._set_role(
            t, phrase=phrase, source="fallback_case_only",
            kind="Hypothesis",
            contract="fallback_case_only",
            blockers=["no_positional_or_contextual_rule_fired"],
        )

    def _update_ctx(self, t, i: int, ctx: dict) -> None:
        if t.word_class == "FIIL":
            ctx["last_verb_idx"] = i
            ctx["last_verb_obj_set"] = False
        if t.word_class == "HARF":
            plain = _strip_diac(t.token)
            if plain in _HAROF_INNA:
                ctx["saw_inna"] = True
                ctx["inna_subj_set"] = False
            if plain in _KANA_FAMILY:
                ctx["saw_kana"] = True
                ctx["kana_subj_set"] = False


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    from .engine import I3rabEngine

    eng = I3rabEngine()
    sentences = [
        "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
        "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",
        "ذَلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ",
        "إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ",
        "لَنْ يَكْتُبَ الْمُسْلِمُونَ كِتَابًا",
    ]
    for text in sentences:
        print(f"\n=== {text} ===")
        s = eng.analyze_sentence(text)
        for t in s.tokens:
            print(f"  {t.token:<22} {t.word_class:<11} {t.role_phrase:<26} (src={t.role_source})")
