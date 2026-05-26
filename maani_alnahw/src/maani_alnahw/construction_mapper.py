"""construction_mapper.py — تَحويل rule_cards إلى construction_rules قابِلَة لِلمُحَرِّك.

كُلّ rule_card تَستَحِقّ مَدخَلًا machine-readable يُمكِن لِمُحَرِّك التَّحليل
العَرَبيّ (analyze_verse / I3rabEngine) أَن يَستَخدِمَه لِـ:
  • التَّعَرُّف على التَّركيب بِناءً على lemma + pattern
  • تَطبيق التَّحويل العَميق (deep predication)
  • وَسم العَلاقات الدَّلاليَّة
  • تَوليد modality
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


# ─── خَريطَة construction templates ─────────────────────────────────────

def _build_zann_construction(rule: dict) -> dict:
    return {
        "construction_id": "ZANN_WA_AKHAWATUHA",
        "title": "ظن وأخواتها",
        "triggers": {
            "lemma": rule.get("trigger", {}).get("lemmas", []),
            "pos": "VERB",
            "shape": "verb + nominative + accusative + accusative",
        },
        "pattern": [
            {"slot": "verb", "role": "operator"},
            {"slot": "subject", "role": "experiencer", "case": "nominative"},
            {"slot": "object_1", "role": "predication_subject", "case": "accusative"},
            {"slot": "object_2", "role": "predication_predicate", "case": "accusative"},
        ],
        "deep_transform": {
            "from": "مبتدأ + خبر",
            "to": "مفعول أول + مفعول ثان",
            "deep_predication": "object_1 + object_2",
        },
        "semantic_output": {
            "relation": "judgment_about_object_1",
            "modality_by_lemma": {
                "ظن": "probable_belief",
                "حسب": "probable_belief",
                "خال": "probable_belief",
                "زعم": "claim_or_assumption",
                "علم": "knowledge",
                "رأى": "belief_or_vision_depending_context",
                "وجد": "finding_or_certain_judgment",
                "ألفى": "finding_or_certain_judgment",
            },
        },
        "warnings": [
            "modality لَيسَت قَطعيَّة — السِّياق يُغَيِّر",
            "لا تَجعَل object_2 حالًا إِلّا بِدَليل",
        ],
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_ilm_arafa_construction(rule: dict) -> dict:
    return {
        "construction_id": "ILM_VS_ARAFA",
        "title": "الفرق بين علم وعرف",
        "triggers": {
            "lemma": ["علم", "عرف"],
            "pos": "VERB",
            "branches": [
                {"name": "ilm_two_objects",
                 "lemma": "علم",
                 "valency": 2,
                 "meaning": "إِدراك_مَضمون_الجُملَة",
                 "case_pattern": "accusative + accusative"},
                {"name": "ilm_one_object",
                 "lemma": "علم",
                 "valency": 1,
                 "meaning": "عَرف",
                 "case_pattern": "accusative"},
                {"name": "arafa_one_object",
                 "lemma": "عرف",
                 "valency": 1,
                 "meaning": "إِدراك_الذَّات",
                 "case_pattern": "accusative",
                 "second_accusative_check": "هل هو حال لا مفعول"},
            ],
        },
        "semantic_output": {
            "ilm_concerns": "الصفات والكليات",
            "arafa_concerns": "الذوات والجزئيات",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_arayta_construction(rule: dict) -> dict:
    return {
        "construction_id": "ARAYTAKUM_ISTIKHBAR",
        "title": "أرأيت/أرأيتك الاستخبارية",
        "triggers": {
            "lemma": ["أرأيت", "أرأيتك", "أرأيتكم", "أرأيتكن"],
            "pos": "VERB",
            "context_signal": "اِستِفهام عَن حالٍ عَجيب",
        },
        "morphology": {
            "taa": {"status": "fixed", "form": "ت"},
            "kaaf_or_kaaf_plus": {
                "role": "address_marker",
                "warning": "ليست مفعولًا بالضرورة",
                "agrees_with_addressee": True,
                "forms": {
                    "كَ": {"person": 2, "number": "singular", "gender": "M"},
                    "كِ": {"person": 2, "number": "singular", "gender": "F"},
                    "كما": {"person": 2, "number": "dual", "gender": "X"},
                    "كم": {"person": 2, "number": "plural", "gender": "M_grammatical"},
                    "كن": {"person": 2, "number": "plural", "gender": "F"},
                },
            },
        },
        "semantic_output": {
            "meaning": "أَخبِرني / أَخبروني",
            "speech_act": "request_information",
        },
        "warnings": [
            "افحَص هَل هي بِمَعنى رُؤيَة قَبل تَطبيق هذا التَّركيب",
        ],
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.88),
    }


def _build_number_counted_construction(rule: dict) -> dict:
    return {
        "construction_id": "NUMBER_COUNTED",
        "title": "العدد والمعدود",
        "triggers": {
            "shape": "number + counted_noun",
        },
        "rules_by_class": (rule.get("syntactic_effect") or {}).get("rules_by_class", {}),
        "semantic_output": {
            "produces_plural_entity": True,
            "entity_gender_from_singular_of_counted": True,
            "surface_vs_semantic_number": "سَطح قَد يَكون SG، الكِيان دَلاليًّا PL",
            "anaphora_target": "العَدَد + المَعدود = كِيان واحِد لِلإِحالَة اللاحِقَة",
        },
        "integration": {
            "engine_module": "number_counted_resolver.py",
            "rules_csv": "data/contracts/rules/number_counted_agreement.csv",
            "numbers_csv": "data/contracts/lists/cardinal_numbers.csv",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.95),
    }


def _build_preposition_construction(rule: dict) -> dict:
    return {
        "construction_id": "PREPOSITION_SUBSTITUTION",
        "title": "نيابة حروف الجر",
        "triggers": {
            "marker": "حَرف جَرّ غَير مُتَوَقَّع مَع فِعل",
        },
        "policy": "do_not_substitute_automatically",
        "investigation_order": [
            "check_tadmeen",
            "check_metaphor",
            "check_meaning_proximity",
            "check_quranic_context",
        ],
        "semantic_output": {
            "principle": "كل حرف له معنى أصلي — لا يستبدل بلا قرينة",
            "alternative": "التضمين أولى من النيابة",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_tadmeen_construction(rule: dict) -> dict:
    return {
        "construction_id": "TADMEEN",
        "title": "التضمين النحوي-الدلالي",
        "triggers": {
            "marker": "verb_meets_unexpected_preposition",
        },
        "output_fields": [
            "surface_verb", "original_meaning", "included_meaning",
            "evidence", "semantic_gain",
        ],
        "conditions": rule.get("conditions", []),
        "semantic_output": {
            "result": "verb_carries_two_meanings",
            "syntax_inherits_from_included_meaning": True,
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.92),
    }


def _build_lam_lamma_construction(rule: dict) -> dict:
    return {
        "construction_id": "LAM_VS_LAMMA",
        "title": "الفرق بين لم ولما",
        "triggers": {
            "particles": ["لم", "لمّا"],
            "follows": "مُضارع مَجزوم",
        },
        "branches": {
            "لم": {
                "effect": "نَفي + قَلب لِلماضي",
                "duration": "مُنقَطِع_أو_مُتَّصِل",
                "expectation": False,
            },
            "لمّا": {
                "effect": "نَفي + قَلب لِلماضي",
                "duration": "مُستَمِرّ_حَتّى_زَمَن_التَّكَلُّم",
                "expectation": True,
                "constraints": ["لا_تَقتَرِن_بِأَداة_شَرط", "يَجوز_حَذف_فِعلها"],
            },
        },
        "semantic_output": {
            "modality_difference": "لَمّا تَحمِل تَوَقُّع الحُصول، لَم لا",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.94),
    }


def _build_jawab_talab_construction(rule: dict) -> dict:
    return {
        "construction_id": "JAWAB_AL_TALAB",
        "title": "جواب الطلب",
        "triggers": {
            "first_clause_markers": ["أمر", "نهي", "استفهام", "تمنّ", "عرض", "تحضيض"],
            "second_clause_marker": "مُضارع مَجزوم",
        },
        "validation_test": {
            "name": "conditional_estimate",
            "estimate": "إن + الطلب → الفعل الثاني",
            "must_be_semantically_valid": True,
        },
        "semantic_output": {
            "relation": "conditional_implicature",
            "deep_structure": "if_first_clause_then_second_clause",
        },
        "warnings": [
            "بَعد النَّهي، الجَزم مَشروط بِصِحَّة التَّقدير الشَّرطيّ",
            "فَرِّق بَين فاء السَّبَبيَّة وَ حَذف الفاء + الجَزم",
        ],
        "examples": rule.get("examples", []),
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.93),
    }


def _build_idmar_lam_construction(rule: dict) -> dict:
    return {
        "construction_id": "IDMAR_AL_LAM",
        "title": "إضمار اللام",
        "triggers": {
            "shape": "verb_request + verb_mudaari_no_lam",
        },
        "two_readings": [
            {"id": "implicit_lam_amr",
             "estimate": "قُل لَهُم لِيَقولوا",
             "interpretation": "الفِعل الثَّاني مَطلوب بِذاتِه"},
            {"id": "jawab_talab",
             "estimate": "إِن تَقُل لَهُم يَقولوا",
             "interpretation": "الفِعل الثَّاني جَزاء"},
        ],
        "policy": "emit_both_with_confidence_if_ambiguous",
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.85),
    }


# ─── builders إِضافيَّة ─────────────────────────────────────────────────

def _build_raa_construction(rule: dict) -> dict:
    return {
        "construction_id": "RAA_POLYSEMY",
        "title": "رأى — البصرية والقلبية والحلمية",
        "triggers": {"lemma": ["رأى"], "pos": "VERB"},
        "branches": {
            "basira": {"valency": 1, "modality": "sensory_perception",
                       "case_pattern": "accusative"},
            "qalbiya": {"valency": 2, "modality": "belief_or_certainty",
                        "case_pattern": "accusative + accusative"},
            "hulmiyya": {"valency": 2, "modality": "dream_vision",
                         "case_pattern": "accusative + accusative",
                         "context": "رُؤيا"},
        },
        "disambiguation": {
            "by_object_count": "مَفعول واحِد → بَصَريَّة، اثنان → قَلبيَّة/حُلميَّة",
            "by_context": "وُجود «رُؤيا/منام» → حُلميَّة",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_zanna_construction(rule: dict) -> dict:
    return {
        "construction_id": "ZANNA_VERB",
        "title": "ظن — رجحان مع احتمال شك",
        "triggers": {"lemma": ["ظن"], "pos": "VERB",
                     "construction_parent": "ZANN_WA_AKHAWATUHA"},
        "semantic_output": {
            "primary_modality": "probable_belief",
            "may_extend_to": ["certain_belief", "uncertain_belief"],
            "context_dependent": True,
        },
        "warnings": [
            "لا تَفتَرِض اليَقين مَع «أَنّ» — السِّياق يُحَدِّد",
        ],
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.92),
    }


def _build_wajada_construction(rule: dict) -> dict:
    return {
        "construction_id": "WAJADA_VERB",
        "title": "وجد — اليقين بعد بحث",
        "triggers": {"lemma": ["وجد"], "pos": "VERB",
                     "construction_parent": "ZANN_WA_AKHAWATUHA"},
        "branches": {
            "yaqin_two_objects": {"valency": 2, "modality": "certain_judgment"},
            "encounter_one_object": {"valency": 1, "modality": "encounter"},
        },
        "disambiguation": "السِّياق يُحَدِّد valency",
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_dara_construction(rule: dict) -> dict:
    return {
        "construction_id": "DARA_VERB",
        "title": "درى — علم بعد جهل",
        "triggers": {"lemma": ["درى", "أدرى"], "pos": "VERB"},
        "semantic_output": {
            "modality": "knowledge_after_question",
            "implies_prior_ignorance": True,
            "not_used_for_divine_knowledge": True,
        },
        "morphology_branches": {
            "darā": {"transitivity": "بِالباء"},
            "adrā": {"transitivity": "بِنَفسه أَو لِمَفعولَين"},
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.88),
    }


def _build_jussive_construction(rule: dict) -> dict:
    return {
        "construction_id": "JUSSIVE_GENERAL",
        "title": "جزم المضارع — عام",
        "triggers": {
            "phenomenon": "jussive_mark",
            "particles_single": ["لم", "لمّا", "لام_الأمر", "لا_الناهية"],
            "particles_shart": ["إن", "من", "ما", "متى", "أينما", "حيثما"],
        },
        "categories": {
            "single_particle": "جَزم بِأَداة واحِدَة",
            "shart_two_actions": "جَزم بِأَداة شَرط — تَجزِم فِعلَين",
            "jawab_talab": "جَزم على تَقدير شَرطيّ",
        },
        "semantic_output": {
            "function": "تَغيير زَمَنيّ أَو طَلَبيّ أَو شَرطيّ",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.93),
    }


def _build_lam_al_amr_construction(rule: dict) -> dict:
    return {
        "construction_id": "LAM_AL_AMR",
        "title": "لام الأمر",
        "triggers": {"particle": "لِـ", "follows": "مضارع_مجزوم"},
        "semantic_output": {
            "modality": "directive",
            "addressee": ["ghaa'ib", "mutakallim"],
            "not_for": "المُخاطَب (يَستَخدِم فِعل الأَمر)",
        },
        "morphology": {
            "default_form": "لِـ (مكسورة)",
            "after_waw_or_fa": "لْـ (ساكنة) — وَلْيَكُن/فَلْيَفعَل",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.92),
    }


def _build_la_nahiya_construction(rule: dict) -> dict:
    return {
        "construction_id": "LA_NAHIYA",
        "title": "لا الناهية",
        "triggers": {"particle": "لا", "follows": "مضارع_مجزوم"},
        "semantic_output": {
            "modality": "prohibition",
            "negation_scope": "الفِعل المُضارع المَجزوم",
        },
        "disambiguation_from_la_nafiya": {
            "rule": "لا النَّافيَة لا تَجزِم — اعتَمِد عَلامَة الجَزم",
            "la_li_jins": "تَنصِب الاسم — مُختَلِفَة كُلِّيًّا",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.94),
    }


def _build_tahwil_construction(rule: dict) -> dict:
    return {
        "construction_id": "AFAL_AL_TAHWIL",
        "title": "أفعال التحويل",
        "triggers": {
            "lemma": ["جعل", "اتخذ", "ترك", "صير", "رد", "تخذ", "وهب"],
            "pos": "VERB",
            "construction_parent": "ZANN_WA_AKHAWATUHA",
        },
        "pattern": [
            {"slot": "verb", "role": "operator"},
            {"slot": "subject", "role": "causer", "case": "nominative"},
            {"slot": "object_1", "role": "transformed_entity", "case": "accusative"},
            {"slot": "object_2", "role": "new_state", "case": "accusative"},
        ],
        "semantic_output": {
            "relation": "transformation",
            "modality": "causative_transformation",
        },
        "warnings": [
            "جَعَل وَ اتَّخَذ لَهُما مَعانٍ أُخرى — افحَص valency أَوَّلًا",
        ],
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.93),
    }


def _build_preposition_specific(rule: dict, cid: str, particle: str) -> dict:
    sem = rule.get("semantic_effect", {})
    return {
        "construction_id": cid,
        "title": f"حرف الجر «{particle}»",
        "triggers": {"particle": particle, "pos": "PREP"},
        "semantic_output": {
            "primary_meaning": sem.get("primary_meaning", ""),
            "secondary_meanings": sem.get("secondary_meanings", []),
            "substitution_policy": sem.get("substitution_policy", ""),
            "tadmeen_notes": sem.get("tadmeen_notes", ""),
        },
        "parent": "PREPOSITION_SUBSTITUTION",
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


def _build_ba(rule):
    return _build_preposition_specific(rule, "PREP_BA", "الباء")


def _build_lam_prep(rule):
    return _build_preposition_specific(rule, "PREP_LAM", "اللام")


def _build_min(rule):
    return _build_preposition_specific(rule, "PREP_MIN", "من")


def _build_ila(rule):
    return _build_preposition_specific(rule, "PREP_ILA", "إلى")


def _build_an(rule):
    return _build_preposition_specific(rule, "PREP_AN", "عن")


def _build_ala(rule):
    return _build_preposition_specific(rule, "PREP_ALA", "على")


def _build_fi(rule):
    return _build_preposition_specific(rule, "PREP_FI", "في")


def _build_jumla_arabiyya(rule):
    return {
        "construction_id": "JUMLA_ARABIYYA",
        "title": "الجملة العربية",
        "type": "foundational_concept",
        "categories": {
            "ismiyya": {"focus": "ثبوت_واستقرار", "structure": "مبتدأ + خبر"},
            "fi3liyya": {"focus": "حدث_وتجدد", "structure": "فعل + فاعل"},
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.88),
    }


def _build_zahirat_irab(rule):
    return {
        "construction_id": "ZAHIRAT_AL_IRAB",
        "title": "ظاهرة الإعراب",
        "type": "foundational_concept",
        "cases": ["رفع", "نصب", "جر", "جزم"],
        "principle": "الإِعراب فَرع المَعنى لا أَصلُه",
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.85),
    }


def _build_maani_irab(rule):
    return {
        "construction_id": "MAANI_AL_IRAB",
        "title": "معاني الإعراب",
        "type": "foundational_concept",
        "case_meanings": {
            "رفع": "الإسناد، العمدة، الأصالة",
            "نصب": "الفضلة، التقييد، المفعولية، الظرفية",
            "جر": "الإضافة، الجر بحرف، التبعية",
            "جزم": "النفي، الأمر، النهي، الشرط، الجزاء",
        },
        "source_refs": [rule.get("source", {})],
        "confidence": rule.get("confidence", 0.9),
    }


# ─── الـ dispatcher ────────────────────────────────────────────────────

BUILDERS = {
    "ZANN_WA_AKHAWATUHA": _build_zann_construction,
    "AFAL_AL_QULOOB": _build_zann_construction,
    "AFAL_AL_YAQIN": _build_zann_construction,
    "AFAL_AL_RUJHAN": _build_zann_construction,
    "ILM_VS_ARAFA": _build_ilm_arafa_construction,
    "ILM_WA_ARAFA": _build_ilm_arafa_construction,
    "ARAYTA": _build_arayta_construction,
    "ARAYTAKA": _build_arayta_construction,
    "ARAYTAKUM_ISTIKHBAR": _build_arayta_construction,
    "NUMBER_COUNTED": _build_number_counted_construction,
    "PREPOSITION_SUBSTITUTION": _build_preposition_construction,
    "PREPOSITIONS": _build_preposition_construction,
    "TADMEEN": _build_tadmeen_construction,
    "LAM_LAMMA": _build_lam_lamma_construction,
    "LAM": _build_lam_lamma_construction,
    "LAMMA": _build_lam_lamma_construction,
    "JAWAB_AL_TALAB": _build_jawab_talab_construction,
    "JUSSIVE": _build_jawab_talab_construction,
    "LA_NAHIYA": _build_jawab_talab_construction,
    "LAM_AL_AMR": _build_jawab_talab_construction,
    "IDMAR_AL_LAM": _build_idmar_lam_construction,
}


def _rule_to_construction_key(rule: dict) -> Optional[str]:
    """يَستَنتِج المَفتاح مِن rule_id (مَثلًا ZANN_WA_AKHAWATUHA__P2_001 → ZANN_WA_AKHAWATUHA)."""
    rid = rule.get("rule_id", "")
    if not rid:
        return None
    # نَأخُذ كُلّ شَيء قَبل __P
    return rid.split("__")[0]


def build_constructions(rules: list[dict]) -> list[dict]:
    """يَحوِّل كُلّ rule_card إلى construction_rule (نَهج قَديم — يُحتَفَظ بِه)."""
    out = []
    seen: set[str] = set()
    for rule in rules:
        key = _rule_to_construction_key(rule)
        if not key:
            continue
        builder = BUILDERS.get(key)
        if not builder:
            continue
        construction = builder(rule)
        cid = construction["construction_id"]
        if cid in seen:
            for existing in out:
                if existing["construction_id"] == cid:
                    existing["source_refs"].extend(construction.get("source_refs", []))
                    break
            continue
        seen.add(cid)
        out.append(construction)
    return out


# ─── النَّهج الجَديد: تَحويل MeaningCards → constructions ─────────────
# لا «عَدَد مَطلوب» — كُلّ بِطاقَة قابِلَة لِلتَّشغيل تُصبِح construction.

# هذِه فَقَط seed examples — لَيسَت gate نِهائيَّة
SEED_CONSTRUCTION_EXAMPLES = [
    "ZANN_WA_AKHAWATUHA", "ILM_VS_ARAFA", "ARAYTAKUM_ISTIKHBAR",
    "NUMBER_COUNTED", "PREPOSITION_SUBSTITUTION", "TADMEEN",
    "LAM_VS_LAMMA", "JAWAB_AL_TALAB",
]


def _card_to_construction(card: dict) -> Optional[dict]:
    """يُحَوِّل MeaningCard قابِلَة لِلتَّشغيل (direct/heuristic) إلى construction_rule."""
    appl = card.get("engine_applicability", "")
    if appl not in ("direct_rule", "heuristic_rule"):
        return None
    triggers = card.get("triggers") or {}
    if not triggers:
        return None  # لا مَفعَل وَاضِح
    cid_base = card.get("meaning_id", "")
    construction = {
        "construction_id": cid_base,
        "title": card.get("title", ""),
        "meaning_type": card.get("meaning_type"),
        "triggers": triggers,
        "description": card.get("description", ""),
        "syntactic_effect": card.get("syntactic_effect") or {},
        "semantic_effect": card.get("semantic_effect") or {},
        "conditions": card.get("conditions") or [],
        "warnings": card.get("warnings") or [],
        "examples": card.get("examples") or [],
        "source_meaning_card": card.get("meaning_id"),
        "source_refs": card.get("source_refs") or [],
        "engine_applicability": appl,
        "confidence": card.get("confidence", 0.0),
    }
    return construction


def build_constructions_from_meaning_cards(cards: list[dict]) -> list[dict]:
    """يُنتِج constructions كَ subset مِن meaning_cards.

    لا حَدّ أَعلى — كُلّ بِطاقَة direct_rule أَو heuristic_rule
    لَها triggers تَدخُل.
    """
    out = []
    for card in cards:
        c = _card_to_construction(card)
        if c is not None:
            out.append(c)
    return out


def write_constructions_jsonl(constructions: list[dict], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for c in constructions:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            count += 1
    return count
