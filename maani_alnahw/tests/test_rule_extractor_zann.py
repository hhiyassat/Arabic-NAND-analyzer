"""اختبار rule_extractor — ظَنّ وَ أَخواتها."""

from maani_alnahw import rule_extractor


def test_zann_rule_extracted():
    topic = {
        "topic_id": "ZANN_WA_AKHAWATUHA__P2",
        "title": "ظن وأخواتها",
        "part": 2, "start_page": 5, "end_page": 6,
    }
    pages = [{
        "part": 2, "page": 5,
        "cleaned_text": "تدخل ظن وأخواتها على المبتدأ والخبر فتنصبهما مفعولين",
        "raw_text": "...",
    }]
    rule = rule_extractor.extract_zann_rule(topic, pages)
    assert rule is not None
    assert rule.title == "عَمَل ظَنّ وَ أَخواتها"
    # input_structure
    assert rule.syntactic_effect["input_structure"] == "مبتدأ + خبر"
    # output_structure
    assert rule.syntactic_effect["output_structure"] == "مفعول أول + مفعول ثان"
    # case_effect
    assert rule.syntactic_effect["case_effect"]["object_1"] == "منصوب"
    assert rule.syntactic_effect["case_effect"]["object_2"] == "منصوب"
    # lemmas
    assert "ظن" in rule.trigger["lemmas"]
    assert "حسب" in rule.trigger["lemmas"]
    # confidence
    assert rule.confidence >= 0.9


def test_zann_returns_none_if_insufficient_indicators():
    topic = {"topic_id": "X", "title": "X", "part": 1, "start_page": 1, "end_page": 1}
    pages = [{"part": 1, "page": 1, "cleaned_text": "نص لا يَحوي دلائل", "raw_text": "..."}]
    rule = rule_extractor.extract_zann_rule(topic, pages)
    assert rule is None


def test_ilm_arafa_rule_extracted():
    topic = {"topic_id": "ILM_WA_ARAFA__P2", "title": "علم وعرف",
             "part": 2, "start_page": 8, "end_page": 9}
    pages = [{"part": 2, "page": 8,
              "cleaned_text": "الفَرق بَين علم وعرف: العلم يتعلق بالصفات والمعرفة بالذوات",
              "raw_text": "..."}]
    rule = rule_extractor.extract_ilm_arafa_rule(topic, pages)
    assert rule is not None
    assert "العِلم" in rule.semantic_effect["description"] or "العلم" in rule.semantic_effect["description"]
