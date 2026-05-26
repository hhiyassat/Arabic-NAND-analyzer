"""rule_extractor.py — استخراج بطاقات القَواعِد مِن الأَبواب المَكشوفَة.

نَهج:
  • لِكُلّ topic، نَقرَأ صَفَحاتِه (start_page → end_page)
  • نُطَبِّق extractor مُتَخَصِّص لِكُلّ نَوع تَركيب (إِن كانَ مَوجودًا)
  • وَ extractor عامّ يُنتِج RuleCard أَوَّليَّة بِناءً على المَلامِح المُكتَشَفَة

الـ extractors المُتَخَصِّصَة (rule-based):
  • zann_extractor — ظَنّ وَ أَخواتها
  • ilm_arafa_extractor — الفَرق بَين عَلِم وَ عَرَف
  • araayta_extractor — أَرَأَيت / أَرَأَيتَكَ
  • number_extractor — العَدَد وَ المَعدود
  • prep_extractor — حُروف الجَرّ
  • tadmeen_extractor — التَّضمين
  • lam_lamma_extractor — لَم وَ لَمّا
  • jussive_extractor — جَزم المُضارِع / جَواب الطَّلَب

كُلّ extractor يُنتِج RuleCard مَع confidence، وَ يَترُك الفَجَوات لِلمُراجَعَة اليَدَويَّة.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import RuleCard


# ─── أَدوات مُساعِدَة ───────────────────────────────────────────────────

def _pages_for_topic(pages: list[dict], topic: dict) -> list[dict]:
    part = topic["part"]
    start = topic["start_page"]
    end = topic.get("end_page") or 99999
    return [p for p in pages if p["part"] == part and start <= p["page"] <= end]


def _concat_text(pages: list[dict]) -> str:
    return "\n".join(p.get("cleaned_text") or p.get("raw_text", "") for p in pages)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _source_for_topic(topic: dict) -> dict:
    return {
        "book": "معاني النحو",
        "author": "فاضل صالح السامرائي",
        "part": topic["part"],
        "page_start": topic["start_page"],
        "page_end": topic.get("end_page"),
    }


# ─── ZANN extractor ─────────────────────────────────────────────────────

def extract_zann_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    """ظَنّ وَ أَخواتها — قاعِدَة عَمَلهَا."""
    text = _concat_text(pages)
    # دَلائل التَّأكيد
    indicators = ["المبتدأ", "الخبر", "مفعولين", "ينصب", "تنصب"]
    has = sum(1 for i in indicators if i in text)
    if has < 2:
        return None
    return RuleCard(
        rule_id=f"ZANN_WA_AKHAWATUHA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="عَمَل ظَنّ وَ أَخواتها",
        source=_source_for_topic(topic),
        trigger={
            "type": "verb_class",
            "lemmas": ["ظن", "حسب", "خال", "زعم", "علم", "رأى", "وجد", "ألفى"],
            "construction": "verb + subject + object_1 + object_2",
        },
        syntactic_effect={
            "input_structure": "مبتدأ + خبر",
            "output_structure": "مفعول أول + مفعول ثان",
            "case_effect": {
                "object_1": "منصوب",
                "object_2": "منصوب",
            },
        },
        semantic_effect={
            "description": "نِسبَة حُكم أَو صِفَة إلى المَفعول الأَوَّل يَقينًا أَو شَكًّا أَو رُجحانًا بِحَسَب الفِعل وَ السِّياق",
            "deep_relation": "predication",
            "modality": ["يقين", "رجحان", "شك_محتمل_حسب_الفعل"],
        },
        conditions=[
            "أَن يَكون الفِعل مِن أَفعال القُلوب أَو التَّحويل النَّاصِبَة لِمَفعولَين",
            "أَن يَكون المَفعولان في الأَصل مُبتَدَأ وَ خَبَرًا",
        ],
        exceptions_or_warnings=[
            "لا يَجوز دائِمًا الِاكتِفاء بِأَحَد المَفعولَين إِن نَقَص المَعنى",
            "لا تَعامُل المَفعول الثَّاني كَحال إِلّا بِدَليل قَويّ",
            "modality لَيسَت نِهائيَّة — السِّياق هو الفَيصَل",
        ],
        examples=[
            {"text": "ظننت عليًّا أخاك", "object_1": "عليًّا", "object_2": "أخاك",
             "deep_predication": "علي أخوك"},
            {"text": "حسبت عبد الله زيدًا بكرًا", "object_1": "زيدًا", "object_2": "بكرًا",
             "deep_predication": "زيد بكر"},
        ],
        author_position="رأي الجمهور — مَع تَحَفُّظ المُؤَلِّف على إِطلاق modality",
        confidence=0.93,
    )


# ─── ILM vs ARAFA extractor ─────────────────────────────────────────────

def extract_ilm_arafa_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if not _contains_any(text, ["علم", "عرف"]):
        return None
    return RuleCard(
        rule_id=f"ILM_VS_ARAFA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="الفَرق بَين عَلِم وَ عَرَف",
        source=_source_for_topic(topic),
        trigger={
            "type": "verb_disambiguation",
            "lemmas": ["علم", "عرف"],
        },
        syntactic_effect={
            "ilm_two_objects": "عَلِم بِمَعنى إِدراك مَضمون الجُملَة → تَنصِب مَفعولَين",
            "ilm_one_object": "عَلِم بِمَعنى عَرَف → تَنصِب مَفعولًا واحِدًا",
            "arafa_one_object": "عَرَف → تَنصِب مَفعولًا واحِدًا غالِبًا (الذَّات)",
        },
        semantic_effect={
            "description": "العِلم يَتَعَلَّق بِالصِّفات وَ بِالكُلِّيَّات؛ المَعرِفَة بِالذَّوات وَ الجُزئيَّات",
            "examples_meaning": {
                "علمت خالدًا طالبًا": "عَلِمتُ اتِّصاف خالد بِالطّالِبيَّة",
                "عرفت خالدًا طالبًا": "عَرَفت خالدًا حال كَونِه طالِبًا (الذَّات في تِلكَ الحال)",
            },
        },
        conditions=[
            "إِن جاءَ بَعد عَلِم مَنصوبان: الأَوَّل المَحكوم عَلَيه، الثَّاني الحُكم",
            "إِن جاءَ بَعد عَرَف مَنصوب ثانٍ، افحَص هَل هو حال لا مَفعول ثانٍ",
        ],
        exceptions_or_warnings=[
            "بَعض النَّحاة (الرَّضيّ) يَرى لا فَرق مَعنويًّا بَين عَلِمت وَ عَرَفت",
            "المُؤَلِّف وَ أَكثَر النَّحاة يُرَجِّحون التَّفريق: العِلم لِلصِّفات، المَعرِفَة لِلذَّوات",
        ],
        examples=[
            {"text": "علمت خالدًا طالبًا", "interpretation": "اتصاف"},
            {"text": "عرفت خالدًا طالبًا", "interpretation": "ذات_في_حال"},
            {"text": "لا تعلمهم نحن نعلمهم",
             "source": {"surah": "التوبة", "ayah": 101},
             "interpretation": "علمت_أمرهم_لا_ذواتهم"},
        ],
        author_position="السامرّائيّ يُرَجِّح التَّفريق — تَحَفُّظ على رأي الرَّضيّ",
        confidence=0.9,
    )


# ─── ARAYTA / ARAYTAKA extractor ───────────────────────────────────────

def extract_arayta_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "أرأيت" not in text and "ارأيت" not in text:
        return None
    return RuleCard(
        rule_id=f"ARAYTA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="أَرَأَيت وَ أَرَأَيتَكَ",
        source=_source_for_topic(topic),
        trigger={
            "type": "construction_disambiguation",
            "lemmas": ["أرأيت", "أرأيتك", "أرأيتكم", "أرأيتكن"],
        },
        syntactic_effect={
            "if_meaning_seeing": "تَعامِل كَفِعل رُؤيَة عاديّ",
            "if_meaning_inform": {
                "construction_id": "ARAYTAKUM_ISTIKHBAR",
                "taa_status": "تاء الفاعِل ثابِتَة (مَفتوحَة) لا تَتَغَيَّر",
                "kaaf_status": "عَلامَة خِطاب لا مَحَلّ لَها مِن الإِعراب",
                "kaaf_morphology": "تَتَصَرَّف حَسَب المُخاطَب (كَ/كِ/كُما/كُم/كُنّ)",
                "warning": "لا تَجعَل الكاف مَفعولًا بِها بِالضَّرورَة",
            },
        },
        semantic_effect={
            "description": "أَرَأَيت قَد تَكون بِمَعنى الرُّؤيَة، أَو بِمَعنى الإِخبار (= أَخبِرني)",
            "context_clue": "إِذا كانَ السِّياق استِخبار عَن حالٍ عَجيب → بِمَعنى أَخبِرني",
        },
        conditions=[
            "افحَص السِّياق قَبل التَّحديد",
            "إِن جاءَ بَعدها (أَ) أَو كَلِمَة استِفهام → غالِبًا استِخبار",
        ],
        exceptions_or_warnings=[
            "بَعض النَّحاة يَجعَل الكاف مَفعولًا في «أَرَأَيتَ نَفسَك» — لَكِنّ هذا غَير ما يَنطَبِق على «أَرَأَيتَكَ» الِاستِخباريَّة",
        ],
        examples=[
            {"text": "أرأيت محمدًا",
             "type": "seeing",
             "analysis": {"verb": "أرأيت", "object": "محمدًا"}},
            {"text": "أرأيتكم إن أتاكم عذاب الله",
             "type": "istikhbar",
             "analysis": {
                 "construction_id": "ARAYTAKUM_ISTIKHBAR",
                 "meaning": "أَخبِروني",
                 "taa": {"status": "fixed", "form": "ت"},
                 "address_suffix": {"form": "كم", "person": 2, "number": "plural",
                                    "gender": "masculine_grammatical", "role": "address_marker"},
                 "warning": "الكاف هُنا لَيسَت مَفعولًا"
             }},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد التَّفريق وَ يُحَذِّر مِن جَعل الكاف مَفعولًا قَطعيًّا",
        confidence=0.88,
    )


# ─── NUMBER COUNTED extractor ─────────────────────────────────────────

def extract_number_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if not _contains_any(text, ["العدد", "تمييز", "مفرد", "جمع"]):
        return None
    return RuleCard(
        rule_id=f"NUMBER_COUNTED__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="قَواعِد العَدَد وَ المَعدود",
        source=_source_for_topic(topic),
        trigger={
            "type": "quantity_phrase",
            "construction": "عَدَد + مَعدود",
        },
        syntactic_effect={
            "rules_by_class": {
                "unit_1_2": {"agreement": "agree", "counted_form": "SG_or_DU",
                             "counted_case": "nominative_after_noun"},
                "unit_3_10": {"agreement": "oppose", "counted_form": "PL",
                              "counted_case": "genitive_idafa"},
                "teens_11_12": {"agreement": "agree", "counted_form": "SG",
                                "counted_case": "accusative_tamyiz"},
                "teens_13_19": {"agreement": "mixed", "counted_form": "SG",
                                "counted_case": "accusative_tamyiz",
                                "note": "الآحاد تُخالِف، عَشر تُوافِق"},
                "tens": {"agreement": "invariable", "counted_form": "SG",
                         "counted_case": "accusative_tamyiz"},
                "compound_21_22": {"agreement": "unit_agrees", "counted_form": "SG",
                                   "counted_case": "accusative_tamyiz"},
                "compound_23_99": {"agreement": "unit_opposes", "counted_form": "SG",
                                   "counted_case": "accusative_tamyiz"},
                "hundred_thousand": {"agreement": "no_gender_relation",
                                     "counted_form": "SG",
                                     "counted_case": "genitive_idafa"},
            },
        },
        semantic_effect={
            "description": "العَدَد لَيس مُجَرَّد كَمِّيَّة — يُلازِم التَّذكير وَ التَّأنيث وَ يُؤَثِّر على الإِحالَة اللاحِقَة",
            "anaphora_rule": "العَدَد + المَعدود يُنتِج كِيانًا دَلاليًّا واحِدًا plural، حَتّى لَو كانَ السَّطح SG",
        },
        conditions=[
            "جِنس العَدَد يَتَحَدَّد مِن جِنس مُفرَد المَعدود لا مِن جَمعه",
            "تَفريق بَين العَدَد النَّحويّ (SG/DU/PL) وَ العَدَد الحِسابيّ (1، 2، ...)",
        ],
        exceptions_or_warnings=[
            "بِضع وَ بِضعَة لِلعَدَد المُبهَم (3-9)",
            "مِئَة وَ أَلف لا تَخضَع لِقاعِدَة الجِنس",
        ],
        examples=[
            {"text": "خمسة رجال", "value": 5, "rule": "unit_3_10_oppose"},
            {"text": "خمس نساء", "value": 5, "rule": "unit_3_10_oppose"},
            {"text": "أحد عشر رجلًا", "value": 11, "rule": "teens_11_12_agree"},
            {"text": "ثلاث عشرة امرأة", "value": 13, "rule": "teens_13_19_mixed"},
            {"text": "عشرون رجلًا", "value": 20, "rule": "tens_invariable"},
            {"text": "خمسة وعشرون دينارًا", "value": 25, "rule": "compound_23_99"},
            {"text": "مئة سنة", "value": 100, "rule": "hundred_thousand"},
        ],
        author_position="السَّامَرَّائيّ — مُطابِق لِلجُمهور مَع تَأكيد البُعد الدَّلاليّ (semantic_number)",
        confidence=0.95,
    )


# ─── PREPOSITION extractor ────────────────────────────────────────────

def extract_preposition_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if not _contains_any(text, ["حروف الجر", "إلى", "الباء", "اللام", "من", "في", "على", "عن"]):
        return None
    return RuleCard(
        rule_id=f"PREPOSITION_SUBSTITUTION__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="نِيابَة حُروف الجَرّ بَعضِها عَن بَعض",
        source=_source_for_topic(topic),
        trigger={
            "type": "preposition_unexpected_meaning",
            "particles": ["إلى", "الباء", "اللام", "من", "عن", "على", "في"],
        },
        syntactic_effect={
            "rejected_default": "لا يَنوب بَعضُها عَن بَعض آليًّا",
            "investigation_order": [
                "هَل هذا تَضمين؟",
                "هَل المَجاز قائِم؟",
                "هَل المَعنيان مُتَقارِبان؟",
                "هَل السِّياق قُرآنيّ/فَصيح؟",
                "هَل المُؤَلِّف يُرَجِّح إِبقاءَ الحَرف على أَصلِه؟",
            ],
        },
        semantic_effect={
            "principle": "كُلّ حَرف لَه مَعنًى أَصليّ — لا تُعَوِّض حَرفًا بِحَرف بِلا قَرينَة",
            "alternatives": "التَّضمين / المَجاز / تَقارُب المَعنى",
        },
        conditions=[
            "إِذا بَدا حَرف بِمَعنى آخَر، افحَص التَّضمين أَوَّلًا",
            "اعتَمِد على المَعنى الأَصليّ ما لَم يَستَوجِب السِّياق غَيره",
        ],
        exceptions_or_warnings=[
            "البَصريّون يَرفُضون النِّيابَة عُمومًا، الكوفيّون أَوسَع",
            "السامرّائيّ مَع البَصريّين في الأَصل + قَبول التَّضمين",
        ],
        examples=[
            {"text": "سَأَلَ سائِلٌ بِعَذابٍ",
             "wrong_analysis": "الباء بِمَعنى عَن",
             "correct_analysis": "سَأَل ضُمِّن مَعنى دَعا → الباء على أَصلها",
             "source": {"surah": "المعارج", "ayah": 1}},
        ],
        author_position="السَّامَرَّائيّ يَرفُض الإِطلاق وَ يَرى تَضمين الفِعل أَولى",
        confidence=0.9,
    )


# ─── TADMEEN extractor ────────────────────────────────────────────────

def extract_tadmeen_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "تضمين" not in text and "ضُمّ" not in text:
        return None
    return RuleCard(
        rule_id=f"TADMEEN__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="التَّضمين النَّحويّ-الدَّلاليّ",
        source=_source_for_topic(topic),
        trigger={
            "type": "verb_unexpected_preposition",
            "marker": "حَرف جَرّ غَير مُتَوَقَّع مَع الفِعل",
        },
        syntactic_effect={
            "definition": "إِشراب لَفظ مَعنى لَفظ آخَر، فَيَأخُذ شَيئًا مِن تَعديتِه أَو مُتَعَلِّقاتِه",
            "result": "الفِعل يَجمَع مَعنَيَين، وَ يَتَعَدَّى بِحَرف غَيره",
        },
        semantic_effect={
            "description": "زِيادَة في المَعنى لا مُجَرَّد استِبدال",
            "tracking_required": ["original_meaning", "included_meaning", "evidence", "semantic_gain"],
        },
        conditions=[
            "وُجود مُناسَبَة بَين الفِعلَين",
            "وُجود قَرينَة تَدُلّ على الفِعل المُضَمَّن",
            "أَمن اللَّبس",
            "مُلائَمَة الذَّوق العَرَبيّ",
            "وُجود غَرَض بَلاغيّ",
        ],
        exceptions_or_warnings=[
            "إِفراط بَعض النَّحاة في التَّضمين — السَّامَرَّائيّ يَطلُب قَرائن قَويَّة",
            "لا يَكفي مُجَرَّد اختِلاف الحَرف لِلتَّضمين",
        ],
        examples=[
            {"text": "ولا تعدُ عيناك عنهم",
             "surface_verb": "تَعدُ",
             "original_meaning": "تَجاوُز",
             "included_meaning": "تَنبو / تَعلو / تَنصَرِف",
             "evidence": "التَّعدية بِـ عَن",
             "semantic_gain": "الجَمع بَين مَعنى المُجاوَزَة وَ النُّبُوّ"},
        ],
        author_position="السَّامَرَّائيّ يُرَحِّب بِالتَّضمين كَأَداة تَفسيريَّة مَع شُروط صارِمَة",
        confidence=0.92,
    )


# ─── LAM / LAMMA extractor ────────────────────────────────────────────

def extract_lam_lamma_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "لما" not in text and "لمّا" not in text:
        return None
    return RuleCard(
        rule_id=f"LAM_LAMMA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="الفَرق بَين لَم وَ لَمّا",
        source=_source_for_topic(topic),
        trigger={
            "type": "negation_particles",
            "particles": ["لم", "لمّا"],
            "follows": "مُضارِع مَجزوم",
        },
        syntactic_effect={
            "lam": {
                "effect": "نَفي المُضارع وَ قَلب زَمَنه إلى الماضي",
                "duration": "مُنقَطِع أَو مُتَّصِل بِالحال",
            },
            "lamma": {
                "effect": "نَفي المُضارع وَ قَلب زَمَنه إلى الماضي",
                "duration": "مُستَمِرّ النَّفي إلى زَمَن التَّكَلُّم",
                "expectation": "تَوَقُّع الحُصول غالِبًا",
                "constraints": [
                    "لا تَقتَرِن بِأَداة الشَّرط",
                    "يَجوز حَذف فِعلها إِذا دَلَّ عَلَيه دَليل",
                ],
            },
        },
        semantic_effect={
            "lam_vs_lamma": "الفَرق دَلاليّ — لَيس مُجَرَّد بَديل لَفظيّ",
            "lam_example": "لَم يَحضُر خالد — قَد يَحضُر بَعد ذلِك",
            "lamma_example": "لَمّا يَحضُر خالد — لَم يَحضُر إلى الآن، حُضوره مُتَوَقَّع",
        },
        conditions=[
            "كِلتاهما تَجزِم المُضارع",
            "كِلتاهما تَنقُل زَمَن الفِعل إلى الماضي",
        ],
        exceptions_or_warnings=[
            "لا تَخلِط بَين لَمّا الجازِمَة وَ لَمّا الحينيَّة (ظَرف زَمان)",
        ],
        examples=[
            {"text": "لم يحضر خالد", "particle": "لم",
             "duration": "مُمكِن التَّوَقُّف"},
            {"text": "لما يحضر خالد", "particle": "لمّا",
             "duration": "مُستَمِرّ_حَتّى_الآن",
             "expectation": "حُضوره مُتَوَقَّع"},
            {"text": "ولما يدخل الإيمان في قلوبكم",
             "source": {"surah": "الحجرات", "ayah": 14},
             "interpretation": "نَفي مُستَمِرّ مَع تَوَقُّع الدُّخول"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد البُعد الدَّلاليّ (التَّوَقُّع وَ الاستمرار)",
        confidence=0.94,
    )


# ─── JUSSIVE / JAWAB AL-TALAB extractor ───────────────────────────────

def extract_jawab_talab_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "جواب الطلب" not in text and "جواب طلب" not in text:
        return None
    return RuleCard(
        rule_id=f"JAWAB_AL_TALAB__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="جَواب الطَّلَب",
        source=_source_for_topic(topic),
        trigger={
            "type": "conditional_implicature",
            "first_clause_markers": ["أمر", "نهي", "استفهام", "تمنّ", "عرض", "تحضيض"],
            "second_clause_marker": "مُضارع مَجزوم",
        },
        syntactic_effect={
            "rule": "إِذا جاءَ مُضارع مَجزوم بَعد طَلَب، فَهو مُتَرَتِّب على الطَّلَب كَتَرَتُّب الجَزاء على الشَّرط",
            "test": "صِحَّة تَقدير «إِن + الطَّلَب → الفِعل الثَّاني»",
        },
        semantic_effect={
            "description": "أُسلوب شَرطيّ دَلاليًّا — لَيس مُجَرَّد جَزم آليّ",
            "components": [
                "الطَّلَب مَطلوب",
                "الفِعل الثَّاني مُتَرَتِّب على تَحَقُّق الطَّلَب",
            ],
        },
        conditions=[
            "أَن يَصِحّ تَقدير الشَّرط",
            "أَن لا يَكون الفِعل الثَّاني حاصِلًا مُسبَقًا",
        ],
        exceptions_or_warnings=[
            "بَعد النَّهي، لا يَجوز الجَزم إِلّا إِذا صَحّ تَقدير الشَّرط",
            "«لا تَدنُ مِن الأَسَد يَأكُلك» — لا يَجوز الجَزم؛ لأَنّ «إِن لا تَدنُ يَأكُلك» غَير صَحيح",
            "«لا تَدنُ مِن الأَسَد تَسلَم» — يَجوز؛ لأَنّ «إِن لا تَدنُ تَسلَم» صَحيح",
            "فَرِّق بَين فاء السَّبَبيَّة وَ حَذف الفاء + الجَزم",
        ],
        examples=[
            {"text": "زرني أكرمك",
             "first_clause": "زُرني (أَمر)",
             "second_clause": "أُكرِمك (مُضارع مَجزوم)",
             "conditional_estimate": "إِن تَزُرني أُكرِمك",
             "valid": True},
            {"text": "لا تدن من الأسد تسلم",
             "first_clause": "لا تَدنُ (نَهي)",
             "second_clause": "تَسلَم (مَجزوم)",
             "conditional_estimate": "إِن لا تَدنُ تَسلَم",
             "valid": True},
            {"text": "لا تدن من الأسد يأكلك",
             "first_clause": "لا تَدنُ (نَهي)",
             "second_clause": "يَأكُلك",
             "conditional_estimate": "إِن لا تَدنُ يَأكُلك",
             "valid": False,
             "fix": "لا تَدنُ مِن الأَسَد فَيَأكُلَك — فاء السَّبَبيَّة، لا جَزم"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد البُعد الشَّرطيّ الدَّلاليّ — لا جَزم آليّ",
        confidence=0.93,
    )


# ─── IDMAR AL LAM extractor ───────────────────────────────────────────

def extract_idmar_lam_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "اللام" not in text and "إضمار" not in text:
        return None
    return RuleCard(
        rule_id=f"IDMAR_AL_LAM__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="إِضمار اللَّام",
        source=_source_for_topic(topic),
        trigger={
            "type": "implicit_command_lam",
            "context": "فِعل طَلَب يَتلوه فِعل مُضارع بِلا لام ظاهِرَة",
        },
        syntactic_effect={
            "two_readings": [
                {"name": "إضمار_لام_أَمر",
                 "estimate": "قُل لَهُم لِيَقولوا (لِيَقولوا = لام أَمر مُضمَرَة)",
                 "meaning": "الفِعل الثَّاني مَطلوب بِذاتِه"},
                {"name": "جَواب_طَلَب",
                 "estimate": "إِن تَقُل لَهُم يَقولوا",
                 "meaning": "الفِعل الثَّاني جَزاء، مُتَرَتِّب"},
            ],
        },
        semantic_effect={
            "description": "السِّياق يُحَدِّد القِراءَة — لا تَفتَرِض جَواب الطَّلَب دائِمًا",
        },
        conditions=[
            "افحَص هَل الفِعل الثَّاني مَطلوب بِذاتِه أَم جَزاء",
            "إِن احتَمَل القِراءَتَين، أَخرِج كِلتَيهما مَع درَجات ثِقَة",
        ],
        exceptions_or_warnings=[
            "بَعض النَّحاة يَفتَرِض جَواب الطَّلَب آليًّا — السَّامَرَّائيّ يَرفُض ذلِك",
        ],
        examples=[
            {"text": "قل لعبادي يقولوا",
             "source": {"surah": "الإسراء", "ayah": 53},
             "reading_1": {"interpretation": "قُل لَهُم لِيَقولوا (لام أَمر)",
                           "confidence": 0.55},
             "reading_2": {"interpretation": "إِن تَقُل لَهُم يَقولوا (جَواب طَلَب)",
                           "confidence": 0.45}},
        ],
        author_position="السَّامَرَّائيّ يَطلُب الفَحص — لا يَفصِل قَطعًا",
        confidence=0.85,
    )


# ─── RAA (رأى) — ثَلاثَة مَعانٍ ─────────────────────────────────────────

def extract_raa_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "رأى" not in text and "رأي" not in text:
        return None
    return RuleCard(
        rule_id=f"RAA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="رَأى — البَصَريَّة وَ القَلبيَّة وَ الحُلميَّة",
        source=_source_for_topic(topic),
        trigger={
            "type": "verb_polysemy",
            "lemma": "رأى",
            "branches": [
                {"name": "basira", "valency": 1, "meaning": "إِدراك بِالعَين"},
                {"name": "qalbiya", "valency": 2, "meaning": "اعتِقاد قَلبيّ"},
                {"name": "hulmiyya", "valency": 2, "meaning": "رُؤيا مَنام", "scope": "قَد يَتَعَدَّى لِمَفعولَين في الرُّؤيا"},
            ],
        },
        syntactic_effect={
            "basira": {"case_pattern": "accusative", "example": "رَأَيتُ سَعيدًا"},
            "qalbiya": {"case_pattern": "accusative + accusative",
                        "example": "رَأَيتُ الحَقَّ مُنتَصِرًا"},
            "hulmiyya": {"case_pattern": "accusative + accusative (في الرُّؤيا)",
                         "example": "إِنِّي أَرَنِي أَعصِرُ خَمرًا"},
        },
        semantic_effect={
            "branches_modality": {
                "basira": "sensory_perception",
                "qalbiya": "belief_or_certainty",
                "hulmiyya": "dream_vision",
            },
            "disambiguation_clue": "السِّياق يُحَدِّد — وُجود مَفعولَين قَلبيَّين يَدُلّ على القَلبيَّة",
        },
        conditions=[
            "البَصَريَّة: مَفعول واحِد، إِدراك حِسِّيّ",
            "القَلبيَّة: مَفعولان، إِدراك ذِهنيّ",
            "الحُلميَّة: مَفعولان في سِياق الرُّؤيا",
        ],
        exceptions_or_warnings=[
            "لا تُعتَبَر القَلبيَّة افتراضيَّة — افحَص السِّياق",
            "رُؤيا الأَنبياء قَد تَكون حُلميَّة عَلى صورَة قَلبيَّة",
        ],
        examples=[
            {"text": "رأيت سعيدًا", "branch": "basira", "valency": 1},
            {"text": "رأيت الحق منتصرًا", "branch": "qalbiya", "valency": 2},
            {"text": "إني أرني أعصر خمرًا",
             "source": {"surah": "يوسف", "ayah": 36},
             "branch": "hulmiyya", "valency": 2,
             "interpretation": "رُؤيا يُوسُف"},
        ],
        author_position="السَّامَرَّائيّ يُفَرِّق بِالسِّياق",
        confidence=0.9,
    )


# ─── ZANNA (ظن) — تَركيز عَلى الفِعل ─────────────────────────────────────

def extract_zanna_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "ظن" not in text:
        return None
    return RuleCard(
        rule_id=f"ZANNA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="ظَنّ — رُجحان مَع احتِمال شَكّ",
        source=_source_for_topic(topic),
        trigger={
            "type": "specific_verb",
            "lemma": "ظن",
            "construction_parent": "ZANN_WA_AKHAWATUHA",
        },
        syntactic_effect={
            "valency": 2,
            "case_pattern": "accusative + accusative",
            "example": "ظَنَنتُ زَيدًا أَخاك",
        },
        semantic_effect={
            "primary": "رُجحان (probable_belief)",
            "may_extend_to": "يَقين قَويّ بَحَسَب السِّياق",
            "negative_use": "قَد تَدُلّ على شَكّ خالِص في سِياق النَّفي",
        },
        conditions=[
            "أَن تَنصِب مَفعولَين أَصلُهما مُبتَدَأ وَ خَبَر",
            "السِّياق يُرَجِّح بَين الشَّكّ وَ اليَقين",
        ],
        exceptions_or_warnings=[
            "في القُرآن: «وَ ظَنَنتُم ظَنَّ السَّوء» — ظَنّ هُنا تَدُلّ على اعتِقاد سَيِّئ يَقينيّ",
            "لا تَجعَل ظَنّ + أَنّ = يَقينًا قاعِدَة مُطلَقَة",
        ],
        examples=[
            {"text": "ظننت زيدًا أخاك", "modality": "probable_belief"},
            {"text": "إن نظن إلا ظنًّا",
             "source": {"surah": "الجاثية", "ayah": 32},
             "modality": "uncertain_belief"},
        ],
        author_position="السَّامَرَّائيّ — modality سياقيَّة لَيسَت لَفظيَّة",
        confidence=0.92,
    )


# ─── WAJADA (وجد) ─────────────────────────────────────────────────────

def extract_wajada_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "وجد" not in text:
        return None
    return RuleCard(
        rule_id=f"WAJADA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="وَجَد — اليَقين بَعدَ بَحث",
        source=_source_for_topic(topic),
        trigger={"type": "specific_verb", "lemma": "وجد",
                 "construction_parent": "ZANN_WA_AKHAWATUHA"},
        syntactic_effect={
            "valency_2": "مَفعولان: «وَجَدتُ زَيدًا قائِمًا» — أَفعال اليَقين",
            "valency_1": "مَفعول واحِد بِمَعنى المُصادَفَة: «وَجَدتُ كِتابًا»",
        },
        semantic_effect={
            "primary": "اليَقين بَعدَ بَحث (finding_or_certain_judgment)",
            "secondary_meanings": ["وَجَد بِمَعنى عَلِم", "وَجَد بِمَعنى صادَف", "وَجَد بِمَعنى أَحَسّ"],
        },
        conditions=[
            "السِّياق يُحَدِّد valency",
            "أَكثَر استِخدامها قُرآنيًّا في معنى اليَقين",
        ],
        exceptions_or_warnings=[
            "لا تَخلِط بَين وَجَد المُتَعَدِّيَة لِمَفعولَين وَ وَجَد بِمَعنى صادَف",
        ],
        examples=[
            {"text": "وجدت زيدًا قائمًا", "valency": 2, "meaning": "certain_judgment"},
            {"text": "وجدنا آباءنا على أمة",
             "source": {"surah": "الزخرف", "ayah": 22},
             "valency": 2, "meaning": "found_state"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد الجِهَة اليَقينيَّة في القُرآن",
        confidence=0.9,
    )


# ─── DARA (درى) ────────────────────────────────────────────────────────

def extract_dara_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "درى" not in text and "دري" not in text:
        return None
    return RuleCard(
        rule_id=f"DARA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="دَرَى — العِلم بَعد جَهل",
        source=_source_for_topic(topic),
        trigger={"type": "specific_verb", "lemma": "درى",
                 "construction_parent": "ZANN_WA_AKHAWATUHA"},
        syntactic_effect={
            "base_form": "تَتَعَدَّى بِالباء — «دَرَيتُ بِخالد»",
            "with_hamza": "أَدرى — تَتَعَدَّى بِنَفسها — «وَ ما أَدراكَ»",
            "two_objects_rare": "تَتَعَدَّى لِمَفعولَين نادِرًا",
        },
        semantic_effect={
            "description": "الدِّرايَة عِلم بَعدَ جَهل، بِضَرب مِن الحِيلَة أَو التَّوَسُّل",
            "vs_ilm": "العِلم أَعَمّ — يَشمَل ما لَم يُسبَق بِجَهل، الدِّرايَة لا تُستَعمَل في حَقّ اللَّه",
        },
        conditions=[
            "الدِّرايَة بَعد بَحث أَو سُؤال",
            "لا تُستَعمَل لِما هُو مَعلوم بِالضَّرورَة",
        ],
        exceptions_or_warnings=[
            "لا تُقَل «دَرَى اللَّه» — تَخصيص أُسلوبيّ",
            "بَعض النَّحاة يَجعَلها مُرادِفَة لِعَلِم — السَّامَرَّائيّ يُفَرِّق",
        ],
        examples=[
            {"text": "وما أدري ما يفعل بي ولا بكم",
             "source": {"surah": "الأحقاف", "ayah": 9},
             "valency": 1, "meaning": "knowledge_after_question"},
            {"text": "وما أدراك ما الحاقة",
             "source": {"surah": "الحاقة", "ayah": 2},
             "valency": 2, "form": "أَدرى"},
        ],
        author_position="السَّامَرَّائيّ يَرى الدِّرايَة بَعد جَهل بِضَرب مِن الحِيلَة",
        confidence=0.88,
    )


# ─── JUSSIVE — جَزم المُضارِع المُستَقِلّ ───────────────────────────────

def extract_jussive_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "جزم" not in text and "مجزوم" not in text:
        return None
    return RuleCard(
        rule_id=f"JUSSIVE__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="جَزم المُضارِع — أَدواتُه وَ مَعانيه",
        source=_source_for_topic(topic),
        trigger={
            "type": "syntactic_phenomenon",
            "phenomenon": "تَغَيُّر آخِر المُضارِع إلى السُّكون أَو حَذف النُّون",
            "particles": ["لم", "لمّا", "لام الأمر", "لا الناهية",
                          "إن", "من", "ما", "متى", "أينما"],
        },
        syntactic_effect={
            "categories": {
                "jazm_by_one_particle": ["لم", "لمّا", "لام الأمر", "لا الناهية"],
                "jazm_by_two_particles": ["أدوات الشرط: إن، من، ما، متى، أين..."],
                "jazm_by_jawab": "جَواب الطَّلَب — مَجزوم بِشَرط مُقَدَّر",
            },
        },
        semantic_effect={
            "lam_lamma": "نَفي وَ قَلب لِلماضي",
            "lam_al_amr": "أَمر بِفِعل غائِب",
            "la_nahiya": "نَهي عَن فِعل",
            "shart": "تَعليق الجَواب عَلى الشَّرط",
            "jawab_talab": "تَرَتُّب جَزائيّ على طَلَب",
        },
        conditions=[
            "الجَزم لا يَكون إِلّا في المُضارع",
            "السُّكون أَو حَذف النُّون عَلامَتا الجَزم",
        ],
        exceptions_or_warnings=[
            "بَعض الأَفعال جامِدَة لا تَتَأَثَّر",
            "جَواب الطَّلَب لَيس آليًّا — يَحتاج اختِبار التَّقدير الشَّرطيّ",
        ],
        examples=[
            {"text": "لم يقم زيد", "particle": "لم", "category": "single_particle"},
            {"text": "ليقم زيد", "particle": "لام الأمر", "category": "single_particle"},
            {"text": "إن تجتهد تنجح", "particle": "إن", "category": "two_particles_shart"},
            {"text": "زرني أكرمك", "category": "jawab_talab"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد البُعد الدَّلاليّ لِكُلّ نَوع جَزم",
        confidence=0.93,
    )


# ─── LAM_AL_AMR — لام الأَمر ────────────────────────────────────────────

def extract_lam_al_amr_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "لام الأمر" not in text and "لام الامر" not in text:
        return None
    return RuleCard(
        rule_id=f"LAM_AL_AMR__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="لام الأَمر — أَمر الغائِب وَ المُتَكَلِّم",
        source=_source_for_topic(topic),
        trigger={"type": "jussive_particle", "particle": "لِـ"},
        syntactic_effect={
            "effect": "جَزم المُضارع",
            "addressee_type": "الغائِب أَو المُتَكَلِّم (لا المُخاطَب — لِأَنّ المُخاطَب لَه فِعل أَمر مُباشِر)",
            "mark": "السُّكون أَو حَذف النُّون",
        },
        semantic_effect={
            "description": "أَمر صَريح بِفِعل لِلغائِب أَو المُتَكَلِّم",
            "modality": "directive",
            "vs_imperative": "فِعل الأَمر لِلمُخاطَب، لام الأَمر لِغَيره",
        },
        conditions=[
            "تَدخُل على المُضارع",
            "تَكون مَكسورَة في الأَصل، تُسَكَّن مَع و/ف",
        ],
        exceptions_or_warnings=[
            "تُكسَر اللَّام إِن لَم تَتَّصِل بِـ و/ف، نَحو: لِيَقُم زَيد",
            "تُسَكَّن مَع و/ف: «وَلْيَكُن مِنكُم أُمَّةٌ»",
        ],
        examples=[
            {"text": "ليقم زيد", "addressee": "ghaa'ib"},
            {"text": "ولْيَكُن منكم أمة",
             "source": {"surah": "آل عمران", "ayah": 104},
             "addressee": "audience_indirect"},
            {"text": "لِنُنفِق مِمّا رَزَقَنا اللَّه",
             "addressee": "mutakallim_pl"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد الفَرق بَين أَمر الغائِب وَ المُخاطَب",
        confidence=0.92,
    )


# ─── LA_NAHIYA — لا النَّاهيَة ──────────────────────────────────────────

def extract_la_nahiya_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "لا الناهية" not in text and "ناهية" not in text:
        return None
    return RuleCard(
        rule_id=f"LA_NAHIYA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="لا النَّاهيَة — النَّهي الصَّريح",
        source=_source_for_topic(topic),
        trigger={"type": "jussive_particle", "particle": "لا (ناهية)"},
        syntactic_effect={
            "effect": "جَزم المُضارع",
            "addressee_type": "المُخاطَب غالِبًا، وَ قَد تَدخُل على الغائِب",
            "vs_la_nafiya": "لا النَّافِيَة لا تَجزِم — تَكون عاطِفَة أَو نافِيَة لِلجِنس",
        },
        semantic_effect={
            "description": "نَهي عَن فِعل",
            "modality": "prohibition",
            "negation_scope": "الفِعل المُضارع المَجزوم بَعدَها",
        },
        conditions=[
            "تَدخُل على المُضارع",
            "تَجزِم بِالسُّكون أَو حَذف النُّون",
        ],
        exceptions_or_warnings=[
            "تَفريق بَين لا النَّاهيَة وَ لا النَّافيَة بِالسِّياق وَ بِعَلامَة الجَزم",
            "لا النَّافيَة لِلجِنس تَنصِب الاسم وَ تَرفَع الخَبَر — مُختَلِفَة كُلِّيًّا",
        ],
        examples=[
            {"text": "لا تقربوا الصلاة وأنتم سكارى",
             "source": {"surah": "النساء", "ayah": 43},
             "modality": "prohibition"},
            {"text": "لا تجعل مع الله إلهًا آخر",
             "source": {"surah": "الإسراء", "ayah": 22},
             "modality": "prohibition"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد التَّفريق بَين النَّاهيَة وَ النَّافيَة",
        confidence=0.94,
    )


# ─── AFAL_AL_TAHWIL — أَفعال التَّحويل ─────────────────────────────────

def extract_tahwil_rule(topic: dict, pages: list[dict]) -> Optional[RuleCard]:
    text = _concat_text(pages)
    if "تحويل" not in text and "تصيير" not in text and "اتخذ" not in text:
        return None
    return RuleCard(
        rule_id=f"AFAL_AL_TAHWIL__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="أَفعال التَّحويل — التَّصيير",
        source=_source_for_topic(topic),
        trigger={
            "type": "verb_class",
            "lemmas": ["جعل", "اتخذ", "ترك", "صير", "رد", "تخذ", "وهب"],
            "construction_parent": "ZANN_WA_AKHAWATUHA",
        },
        syntactic_effect={
            "valency": 2,
            "case_pattern": "accusative + accusative",
            "first_object": "المَفعول الأَوَّل: الَّذي يُحَوَّل",
            "second_object": "المَفعول الثَّاني: الحالَة الجَديدَة",
        },
        semantic_effect={
            "relation": "transformation",
            "deep_structure": "object_1 صارَ object_2 بِفِعل الفاعِل",
            "modality": "causative_transformation",
        },
        conditions=[
            "أَن يَكون الفِعل دالًّا على نَقل المَفعول الأَوَّل لِحالَة جَديدَة",
            "أَن يَكون المَفعول الثَّاني هُو الحالَة لا الذَّات",
        ],
        exceptions_or_warnings=[
            "جَعَل تَأتي بِمَعنى التَّحويل وَ بِمَعنى الخَلق وَ بِمَعنى الاعتِقاد — السِّياق يُحَدِّد",
            "اتَّخَذ بِمَعنى التَّحويل تَكون لِمَفعولَين، وَ بِمَعنى الأَخذ لِمَفعول واحِد",
        ],
        examples=[
            {"text": "جعلت الطين خزفًا", "first": "الطين", "second": "خزفًا"},
            {"text": "واتخذ الله إبراهيم خليلًا",
             "source": {"surah": "النساء", "ayah": 125},
             "first": "إبراهيم", "second": "خليلًا"},
            {"text": "وجعلنا منهم أئمة يهدون",
             "source": {"surah": "السجدة", "ayah": 24},
             "first": "منهم", "second": "أئمة"},
        ],
        author_position="السَّامَرَّائيّ يُفَرِّق المَعاني المُتَعَدِّدَة لِـ جَعَل",
        confidence=0.93,
    )


# ─── حُروف الجَرّ الفَرديَّة ──────────────────────────────────────────

def _build_preposition_individual(topic: dict, pages: list[dict],
                                   particle: str, particle_id: str,
                                   primary_meaning: str,
                                   secondary_meanings: list[str],
                                   examples: list[dict],
                                   tadmeen_notes: str = "") -> Optional[RuleCard]:
    text = _concat_text(pages)
    if particle not in text:
        return None
    return RuleCard(
        rule_id=f"{particle_id}__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title=f"حَرف الجَرّ «{particle}» — مَعانيه",
        source=_source_for_topic(topic),
        trigger={"type": "preposition", "particle": particle},
        syntactic_effect={
            "effect": "جَرّ الاسم بَعده",
            "construction_parent": "PREPOSITION_SUBSTITUTION",
        },
        semantic_effect={
            "primary_meaning": primary_meaning,
            "secondary_meanings": secondary_meanings,
            "substitution_policy": "لا يَنوب عَنه حَرف آخَر إِلّا بِقَرينَة وَ تَضمين",
            "tadmeen_notes": tadmeen_notes,
        },
        conditions=[
            "افحَص المَعنى الأَصليّ أَوَّلًا",
            "إِذا بَدا بِمَعنى آخَر، تَفَحَّص تَضمين الفِعل",
        ],
        exceptions_or_warnings=[
            f"بَعض النَّحاة يَجعَلون «{particle}» تَنوب عَن حَرف آخَر — السَّامَرَّائيّ يُفَضِّل التَّضمين",
        ],
        examples=examples,
        author_position="السَّامَرَّائيّ — أَصل المَعنى مَع جَواز التَّضمين بِشُروط",
        confidence=0.9,
    )


def extract_ba_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "الباء", "BA",
        primary_meaning="الإِلصاق (الحَقيقيّ وَ المَجازيّ)",
        secondary_meanings=["السَّبَبيَّة", "الاستِعانَة", "المُصاحَبَة", "الظَّرفيَّة",
                            "البَدَل", "المُقابَلَة", "القَسَم"],
        examples=[
            {"text": "أمسكت بيدك", "meaning": "الإلصاق"},
            {"text": "كتبت بالقلم", "meaning": "الاستعانة"},
            {"text": "سأل سائل بعذاب",
             "source": {"surah": "المعارج", "ayah": 1},
             "meaning": "تضمين سأل=دعا → الباء على أصلها"},
            {"text": "بسم الله", "meaning": "الاستعانة/المصاحبة"},
        ],
        tadmeen_notes="إِذا تَعَدَّى فِعل بِالباء بِمَعنى غَريب — افحَص التَّضمين",
    )


def extract_lam_prep_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "اللام", "LAM_PREP",
        primary_meaning="المِلك وَ الاختِصاص",
        secondary_meanings=["التَّعليل", "الانتِهاء", "الصَّيرورَة (لام العاقِبَة)",
                            "التَّوكيد", "التَّبليغ"],
        examples=[
            {"text": "المال لزيد", "meaning": "الملك"},
            {"text": "جئت لأستفيد", "meaning": "التعليل"},
            {"text": "فالتقطه آل فرعون ليكون لهم عدوًّا",
             "source": {"surah": "القصص", "ayah": 8},
             "meaning": "لام العاقبة — لَيس عِلَّة، بَل صَيرورَة"},
        ],
        tadmeen_notes="لام العاقِبَة تُلتَبَس بِلام التَّعليل — السِّياق يُحَدِّد",
    )


def extract_min_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "من", "MIN",
        primary_meaning="ابتِداء الغايَة (المَكانيَّة وَ الزَّمانيَّة وَ غَيرها)",
        secondary_meanings=["التَّبعيض", "البَيان", "البَدَل", "السَّبَبيَّة", "الزَّائدَة"],
        examples=[
            {"text": "خرجت من البيت", "meaning": "ابتداء_مكاني"},
            {"text": "أخذت من الطعام", "meaning": "التبعيض"},
            {"text": "أساور من ذهب",
             "source": {"surah": "الحج", "ayah": 23},
             "meaning": "بيان_جنس"},
            {"text": "ما جاءنا من بشير",
             "source": {"surah": "المائدة", "ayah": 19},
             "meaning": "زائدة_لِلتَّوكيد"},
        ],
    )


def extract_ila_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "إلى", "ILA",
        primary_meaning="انتِهاء الغايَة (المَكانيَّة وَ الزَّمانيَّة)",
        secondary_meanings=["المُصاحَبَة", "التَّبيين", "بِمَعنى عِندَ"],
        examples=[
            {"text": "سرت إلى المسجد", "meaning": "انتهاء_مكاني"},
            {"text": "ثم أتموا الصيام إلى الليل",
             "source": {"surah": "البقرة", "ayah": 187},
             "meaning": "انتهاء_زماني"},
        ],
    )


def extract_an_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "عن", "AN_PREP",
        primary_meaning="المُجاوَزَة وَ البُعد",
        secondary_meanings=["البَدَل", "السَّبَبيَّة", "التَّعليل", "الاستِعانَة"],
        examples=[
            {"text": "رميت السهم عن القوس", "meaning": "المجاوزة"},
            {"text": "وما يَنطِق عن الهوى",
             "source": {"surah": "النجم", "ayah": 3},
             "meaning": "المجاوزة_المعنوية"},
        ],
    )


def extract_ala_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "على", "ALA_PREP",
        primary_meaning="الاستِعلاء (الحَقيقيّ وَ المَجازيّ)",
        secondary_meanings=["المُصاحَبَة", "التَّعليل", "المَوافَقَة", "بِمَعنى مِن"],
        examples=[
            {"text": "الكتاب على الطاولة", "meaning": "استعلاء_حقيقي"},
            {"text": "ولتكبروا الله على ما هداكم",
             "source": {"surah": "البقرة", "ayah": 185},
             "meaning": "تعليل"},
        ],
    )


def extract_fi_rule(topic, pages):
    return _build_preposition_individual(
        topic, pages, "في", "FI",
        primary_meaning="الظَّرفيَّة (المَكانيَّة وَ الزَّمانيَّة)",
        secondary_meanings=["السَّبَبيَّة", "المُصاحَبَة", "بِمَعنى عَلى", "المُقايَسَة"],
        examples=[
            {"text": "زيد في الدار", "meaning": "ظرفية_مكانية"},
            {"text": "في يوم نحس مستمر",
             "source": {"surah": "القمر", "ayah": 19},
             "meaning": "ظرفية_زمانية"},
            {"text": "لمسكم فيما أفضتم فيه عذاب عظيم",
             "source": {"surah": "النور", "ayah": 14},
             "meaning": "سببية"},
        ],
    )


# ─── الأَبواب التَّمهيديَّة (intro) ─────────────────────────────────────

def extract_jumla_arabiyya_rule(topic, pages):
    if "جملة" not in _concat_text(pages):
        return None
    return RuleCard(
        rule_id=f"JUMLA_ARABIYYA__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="الجُملَة العَرَبيَّة — مَفهومُها وَ أَنواعُها",
        source=_source_for_topic(topic),
        trigger={"type": "introduction"},
        syntactic_effect={
            "definition": "كَلام مُفيد ذو فائِدَة تامَّة",
            "types": {
                "ismiyya": "اسميَّة — مُبتَدَأ + خَبَر",
                "fi3liyya": "فِعليَّة — فِعل + فاعِل",
            },
        },
        semantic_effect={
            "ismiyya_focus": "الثُّبوت وَ الاستِقرار",
            "fi3liyya_focus": "الحَدَث وَ التَّجَدُّد",
        },
        conditions=["إِفادَة المَعنى تَمامًا", "وُجود الإِسناد"],
        exceptions_or_warnings=[
            "بَعض الجُمَل تُعَدّ كَلامًا بِلا فِعل ظاهِر — تَقدير ضِمنيّ",
        ],
        examples=[
            {"text": "زَيد قائِم", "type": "ismiyya"},
            {"text": "قام زَيد", "type": "fi3liyya"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد البُعد الدَّلاليّ لِأَنواع الجُملَة",
        confidence=0.88,
    )


def extract_zahirat_irab_rule(topic, pages):
    if "إعراب" not in _concat_text(pages) and "اعراب" not in _concat_text(pages):
        return None
    return RuleCard(
        rule_id=f"ZAHIRAT_AL_IRAB__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="ظاهِرَة الإِعراب",
        source=_source_for_topic(topic),
        trigger={"type": "introduction"},
        syntactic_effect={
            "definition": "تَغَيُّر آخِر الكَلِمَة بِحَسَب مَوقِعِها مِن الجُملَة",
            "cases": ["رفع", "نصب", "جر", "جزم"],
        },
        semantic_effect={
            "function": "بَيان وَظيفَة الكَلِمَة في الجُملَة",
            "principle": "الإِعراب فَرع المَعنى لا أَصلُه",
        },
        conditions=["وُجود عامِل لَفظيّ أَو مَعنويّ"],
        exceptions_or_warnings=[
            "المَبني لَفظًا قَد يَكون مُعرَبًا مَحَلًّا",
        ],
        examples=[
            {"text": "جاء زيدٌ — زيدًا — زيدٍ", "meaning": "تغير_بحسب_الموقع"},
        ],
        author_position="السَّامَرَّائيّ يُؤَكِّد أَنّ الإِعراب خادِم لِلمَعنى",
        confidence=0.85,
    )


def extract_maani_irab_rule(topic, pages):
    if "معاني" not in _concat_text(pages):
        return None
    return RuleCard(
        rule_id=f"MAANI_AL_IRAB__P{topic['part']}_001",
        topic_id=topic["topic_id"],
        title="مَعاني الإِعراب",
        source=_source_for_topic(topic),
        trigger={"type": "introduction"},
        syntactic_effect={
            "rafع_meaning": "الإِسناد الإِيجابيّ، الأَصالَة، الرَّفع لِلعُمدَة",
            "nasب_meaning": "الفَضلَة، التَّقييد، المَفعوليَّة، الظَّرفيَّة",
            "jarr_meaning": "الإِضافَة، الجَرّ بِحَرف، التَّبَعيَّة",
            "jazm_meaning": "النَّفي، الأَمر، النَّهي، الشَّرط، الجَزاء",
        },
        semantic_effect={
            "principle": "كُلّ حالَة إِعراب تَحمِل وَظيفَة دَلاليَّة مُحَدَّدَة",
            "depth": "الإِعراب لَيس مُجَرَّد عَلامَة — هو دَلالَة",
        },
        conditions=["فَحص المَعنى قَبل الحُكم بِالإِعراب"],
        exceptions_or_warnings=[
            "بَعض النَّحاة جَعَلوا الإِعراب عَلامَة فَقَط — السَّامَرَّائيّ يَرفُض ذلِك",
        ],
        examples=[
            {"text": "زيد قائم", "case": "rafع_عمدة"},
            {"text": "رأيت زيدًا", "case": "nasب_فضلة"},
        ],
        author_position="السَّامَرَّائيّ يَرى الإِعراب نِظامًا دَلاليًّا كامِلًا",
        confidence=0.9,
    )


# ─── المُجَمِّع ─────────────────────────────────────────────────────────

EXTRACTORS_BY_TOPIC_ID = {
    # ─ ZANN family (تَجميع جامِع + تَخصيصات) ─
    "ZANN_WA_AKHAWATUHA": extract_zann_rule,
    "AFAL_AL_QULOOB": extract_zann_rule,
    "AFAL_AL_YAQIN": extract_zann_rule,
    "AFAL_AL_RUJHAN": extract_zann_rule,
    "AFAL_AL_TAHWIL": extract_tahwil_rule,
    # ─ أَفعال مُحَدَّدَة ─
    "ZANNA": extract_zanna_rule,
    "ILM": extract_ilm_arafa_rule,
    "ILM_WA_ARAFA": extract_ilm_arafa_rule,
    "RAA": extract_raa_rule,
    "WAJADA": extract_wajada_rule,
    "DARA": extract_dara_rule,
    # ─ أَرَأَيت ─
    "ARAYTA": extract_arayta_rule,
    "ARAYTAKA": extract_arayta_rule,
    # ─ العَدَد ─
    "NUMBER_COUNTED": extract_number_rule,
    # ─ حُروف الجَرّ ─
    "PREPOSITIONS": extract_preposition_rule,
    "PREPOSITION_SUBSTITUTION": extract_preposition_rule,
    "TADMEEN": extract_tadmeen_rule,
    "BA": extract_ba_rule,
    "LAM": extract_lam_prep_rule,  # في الجُزء 1، اللام كَحَرف جَرّ
    "MIN": extract_min_rule,
    "ILA": extract_ila_rule,
    "AN_PREP": extract_an_rule,
    "ALA_PREP": extract_ala_rule,
    "FI": extract_fi_rule,
    # ─ نَفي وَ جَزم ─
    "LAMMA": extract_lam_lamma_rule,
    "JUSSIVE": extract_jussive_rule,
    "JAWAB_AL_TALAB": extract_jawab_talab_rule,
    "LA_NAHIYA": extract_la_nahiya_rule,
    "LAM_AL_AMR": extract_lam_al_amr_rule,
    "IDMAR_AL_LAM": extract_idmar_lam_rule,
    # ─ تَمهيد ─
    "JUMLA_ARABIYYA": extract_jumla_arabiyya_rule,
    "ZAHIRAT_AL_IRAB": extract_zahirat_irab_rule,
    "MAANI_AL_IRAB": extract_maani_irab_rule,
}


def extract_all_rules(pages: list[dict], topics: list[dict]) -> list[RuleCard]:
    """يَستَخرِج كُلّ القَواعِد المُمكِنَة مِن الأَبواب."""
    rules: list[RuleCard] = []
    seen: set[str] = set()
    for topic in topics:
        # نَستَخرِج base_id (بِدون __P{part}_001)
        base = topic["topic_id"].split("__")[0]
        extractor = EXTRACTORS_BY_TOPIC_ID.get(base)
        if not extractor:
            continue
        topic_pages = _pages_for_topic(pages, topic)
        if not topic_pages:
            continue
        rule = extractor(topic, topic_pages)
        if rule and rule.rule_id not in seen:
            rules.append(rule)
            seen.add(rule.rule_id)
    return rules


def write_rule_cards_jsonl(rules: list[RuleCard], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for r in rules:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
