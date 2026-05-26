"""اختبار قَواعِد العَدَد وَ المَعدود."""

from maani_alnahw import rule_extractor, construction_mapper


def test_number_rule_extracted():
    topic = {"topic_id": "NUMBER_COUNTED__P4", "title": "العدد والمعدود",
             "part": 4, "start_page": 1, "end_page": 30}
    pages = [{"part": 4, "page": 1,
              "cleaned_text": "العدد والمعدود: قواعد العدد مع تمييز مفرد",
              "raw_text": "..."}]
    rule = rule_extractor.extract_number_rule(topic, pages)
    assert rule is not None
    # تَأَكُّد مِن جَميع التَّصنيفات
    classes = rule.syntactic_effect["rules_by_class"]
    assert "unit_1_2" in classes
    assert classes["unit_1_2"]["agreement"] == "agree"
    assert "unit_3_10" in classes
    assert classes["unit_3_10"]["agreement"] == "oppose"
    assert "teens_11_12" in classes
    assert "teens_13_19" in classes
    assert "tens" in classes
    assert "hundred_thousand" in classes


def test_number_construction_built():
    rule = {
        "rule_id": "NUMBER_COUNTED__P4_001",
        "syntactic_effect": {
            "rules_by_class": {"unit_3_10": {"agreement": "oppose"}}
        },
        "source": {"part": 4, "page_start": 1},
        "confidence": 0.95,
    }
    constructions = construction_mapper.build_constructions([rule])
    assert len(constructions) == 1
    c = constructions[0]
    assert c["construction_id"] == "NUMBER_COUNTED"
    assert c["semantic_output"]["produces_plural_entity"] is True
