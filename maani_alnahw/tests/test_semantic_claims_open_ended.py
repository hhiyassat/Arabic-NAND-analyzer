"""اختبارات النَّظام الجَديد open-ended.

نَختَبِر:
  1. الـ pipeline لا يَعتَمِد عَلى REQUIRED_CONSTRUCTIONS
  2. claims تَحتَوي part + page
  3. cards لَها source_claims
  4. constructions = subset مِن meaning_cards
  5. كَثافَة claims لِصَفحَة ظَنّ
  6. صَفَحات أَرَأَيتَكُم تُنتِج عِدَّة cards
  7. حُروف الجَرّ لا تُختَزَل في قاعِدَة واحِدَة
  8. كُلّ صَفحَة لَها coverage record
  9. صَفَحات OCR ضَعيف تَدخُل manual_review_queue
  10. لا «no fixed construction limit»
"""

import json
from pathlib import Path

from maani_alnahw import (
    semantic_claim_extractor,
    meaning_card_builder,
    coverage_analyzer,
    manual_review,
    construction_mapper,
)


# ─── Helper fixtures ─────────────────────────────────────────────────

def _page(part, page, text):
    return {
        "doc_id": f"maani_alnahw_part_{part}",
        "part": part,
        "page": page,
        "raw_text": text,
        "cleaned_text": text,
        "source_file": f"{part}.txt",
    }


# 1
def test_no_fixed_construction_limit():
    """تَأَكُّد أَنّ الكود لا يَعتَمِد عَلى REQUIRED_CONSTRUCTIONS."""
    import maani_alnahw.construction_mapper as cm
    assert not hasattr(cm, "REQUIRED_CONSTRUCTIONS"), \
        "REQUIRED_CONSTRUCTIONS يَجِب أَن تُحذَف"
    # يَجوز وُجود SEED_CONSTRUCTION_EXAMPLES
    assert hasattr(cm, "SEED_CONSTRUCTION_EXAMPLES")


# 2
def test_claims_have_source_page():
    pages = [_page(2, 5, "تدخل ظن وأخواتها على المبتدأ والخبر فتنصبهما مفعولين.")]
    topics = []
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, topics)
    assert all(c.part == 2 for c in claims)
    assert all(c.page == 5 for c in claims)
    assert all(c.claim_id for c in claims)


# 3
def test_meaning_cards_have_source_claims():
    pages = [_page(2, 5, "تدخل ظن وأخواتها على المبتدأ والخبر فتنصبهما مفعولين. "
                          "الفرق بين علم وعرف ظاهر. والصواب أن العلم يتعلق بالصفات.")]
    topics = []
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, topics)
    cards = meaning_card_builder.build_meaning_cards([c.to_dict() for c in claims])
    assert len(cards) > 0
    for card in cards:
        assert card.source_claims, f"Card {card.meaning_id} لَيس لَها source_claims"


# 4
def test_constructions_are_subset_of_meaning_cards():
    pages = [_page(2, 5,
        "تدخل ظن وأخواتها على المبتدأ والخبر فتنصبهما مفعولين. "
        "حسب وخال وعلم ورأى من أفعال القلوب. "
        "معنى الباء الإلصاق. "
    )]
    topics = []
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, topics)
    cards = meaning_card_builder.build_meaning_cards([c.to_dict() for c in claims])
    constructions = construction_mapper.build_constructions_from_meaning_cards(
        [c.to_dict() for c in cards]
    )
    card_ids = {c.meaning_id for c in cards}
    for cons in constructions:
        assert cons.get("source_meaning_card") in card_ids, \
            f"construction بِلا source_meaning_card مُطابِق: {cons.get('construction_id')}"


# 5
def test_zann_page_claim_density():
    """صَفحَة ظَنّ يَجِب أَن تُنتِج عِدَّة claims لا واحِدًا."""
    zann_text = (
        "ظن وأخواتها\n"
        "تدخل ظن وأخواتها على المبتدأ والخبر فتنصبهما مفعولين كما هو رأي الجمهور.\n"
        "تقول: ظننت عليًّا أخاك.\n"
        "إذا ذكرت أحد المفعولين دون الآخر نقص المعنى.\n"
        "والصواب أن المفعول الثاني خبر منسوب إلى المفعول الأول.\n"
        "وتنقسم هذه الأفعال إلى أفعال القلوب وأفعال التحويل.\n"
    )
    pages = [_page(2, 5, zann_text)]
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, [])
    assert len(claims) >= 3, f"يَجِب أَن يَكون عَدَد claims ≥ 3، حُصِل عَلى {len(claims)}"


# 6
def test_araytakum_multiple_meanings():
    text = (
        "أرأيت وأرأيتك\n"
        "قد تكون أرأيت للرؤية، وقد تكون بمعنى أخبرني.\n"
        "ومعنى أرأيتكم في الاستخبار: أخبروني.\n"
        "الكاف هنا علامة خطاب لا محل لها من الإعراب.\n"
        "وتزاد الكاف لتوكيد الخطاب والتنبيه.\n"
        "والذي أراه أن أرأيتك بمعنى أخبرني تختلف عن أرأيتك بمعنى رؤية النفس.\n"
        "إذا كانت للرؤية فالكاف مفعول.\n"
        "بخلاف ما إذا كانت للاستخبار.\n"
    )
    pages = [_page(2, 14, text)]
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, [])
    cards = meaning_card_builder.build_meaning_cards([c.to_dict() for c in claims])
    assert len(cards) >= 2, f"أَرَأَيتَكُم تَستَحِقّ ≥ 2 cards، حُصِل عَلى {len(cards)}"


# 7
def test_prepositions_generate_many_meanings():
    text = (
        "حروف الجر\n"
        "الأصل في حروف الجر ألا ينوب بعضها عن بعض.\n"
        "معنى الباء الإلصاق.\n"
        "معنى اللام التعليل والملك.\n"
        "معنى من ابتداء الغاية.\n"
        "معنى إلى انتهاء الغاية.\n"
        "ما يوهم النيابة يؤول بالتضمين.\n"
        "والذي أراه أن إبقاء الحرف على معناه أولى.\n"
    )
    pages = [_page(3, 11, text)]
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, [])
    cards = meaning_card_builder.build_meaning_cards([c.to_dict() for c in claims])
    assert len(cards) >= 2, f"حُروف الجَرّ تَستَحِقّ ≥ 2 cards، حُصِل عَلى {len(cards)}"


# 8
def test_page_coverage_for_all_pages():
    pages = [
        _page(2, 5, "نص قصير عن ظن"),
        _page(2, 6, "نص آخر طويل عن أفعال القلوب لا يحتوي أي نمط معروف"),
        _page(2, 7, ""),  # صَفحَة فارِغَة
    ]
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, [])
    cards = meaning_card_builder.build_meaning_cards([c.to_dict() for c in claims])
    coverage = coverage_analyzer.build_page_coverage(
        pages, [c.to_dict() for c in claims], [c.to_dict() for c in cards], [], []
    )
    assert len(coverage) == len(pages)
    keys = {(c.part, c.page) for c in coverage}
    expected = {(p["part"], p["page"]) for p in pages}
    assert keys == expected


# 9
def test_manual_review_for_low_confidence():
    """صَفحَة طَويلَة بِلا claims يَجِب أَن تَدخُل manual_review."""
    long_no_claim = _page(2, 99, "نص " * 200)  # > 800 حَرف
    coverage = coverage_analyzer.build_page_coverage(
        [long_no_claim], [], [], [], []
    )
    review = manual_review.build_review_queue(
        [long_no_claim], [], [], [c.to_dict() for c in coverage], []
    )
    assert any(it.part == 2 and it.page == 99 for it in review), \
        "صَفحَة طَويلَة بِلا claims يَجِب أَن تَدخُل manual_review"


# 10
def test_no_required_construction_count_gate():
    """تَأَكُّد أَنّ build_constructions_from_meaning_cards لا يَستَهدِف عَدَدًا ثابِتًا."""
    # cards فارِغَة → 0 constructions (لا خَطَأ)
    constructions = construction_mapper.build_constructions_from_meaning_cards([])
    assert constructions == []
    # cards كَثيرَة → constructions كَثيرَة (بِلا حَدّ أَعلى)
    fake_card = {
        "meaning_id": "M_TEST_1",
        "title": "test",
        "meaning_type": "particle_meaning",
        "engine_applicability": "direct_rule",
        "triggers": {"particles": ["الباء"]},
        "source_refs": [{"part": 3, "page_start": 11}],
        "confidence": 0.9,
    }
    constructions = construction_mapper.build_constructions_from_meaning_cards([fake_card] * 50)
    assert len(constructions) == 50, "لا يَجِب وُجود حَدّ أَعلى عَلى عَدَد constructions"


# اختِبار إِضافيّ: claims types diverse
def test_diverse_claim_types_extracted():
    text = (
        "الفرق بين علم وعرف. "
        "معنى الباء الإلصاق. "
        "تنصب الاسم بعدها. "
        "غالبًا تأتي للظرفية. "
        "والصواب أن تكون كذلك. "
        "قال سيبويه إن هذا جائز. "
        "بخلاف ما لو دخل عليها حرف. "
    )
    pages = [_page(1, 10, text)]
    claims = semantic_claim_extractor.extract_claims_from_pages(pages, [])
    types = {c.claim_type for c in claims}
    # يَنبَغي أَن نَرى أَنواعًا مُتَنَوِّعَة (لا نَوع واحِد)
    assert len(types) >= 3, f"يَجِب رُؤيَة ≥ 3 أَنواع claims، حُصِل عَلى {types}"
