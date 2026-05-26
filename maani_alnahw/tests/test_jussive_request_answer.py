"""اختبارات جَزم المُضارع وَ جَواب الطَّلَب."""

from maani_alnahw import rule_extractor


def test_lam_lamma_distinction():
    topic = {"topic_id": "LAMMA__P4", "title": "لما",
             "part": 4, "start_page": 100, "end_page": 110}
    pages = [{"part": 4, "page": 100,
              "cleaned_text": "لما يحضر خالد — استمرار النفي إلى زمن التكلم",
              "raw_text": "..."}]
    rule = rule_extractor.extract_lam_lamma_rule(topic, pages)
    assert rule is not None
    assert rule.syntactic_effect["lamma"]["expectation"] == "تَوَقُّع الحُصول غالِبًا"
    assert rule.syntactic_effect["lamma"]["duration"].startswith("مُستَمِرّ")


def test_jawab_talab_valid_estimate():
    topic = {"topic_id": "JAWAB_AL_TALAB__P4", "title": "جواب الطلب",
             "part": 4, "start_page": 120, "end_page": 130}
    pages = [{"part": 4, "page": 120,
              "cleaned_text": "جواب الطلب أسلوب شرطي دلاليا زرني أكرمك",
              "raw_text": "..."}]
    rule = rule_extractor.extract_jawab_talab_rule(topic, pages)
    assert rule is not None
    # «زُرني أُكرِمك» يَجِب أَن يَكون مَقبولًا
    valid_ex = next((e for e in rule.examples if "زرني" in e["text"]), None)
    assert valid_ex is not None
    assert valid_ex["valid"] is True
    # «لا تَدنُ مِن الأَسَد يَأكُلك» يَجِب أَن يَكون مَرفوضًا
    invalid_ex = next((e for e in rule.examples if "يأكلك" in e["text"]), None)
    assert invalid_ex is not None
    assert invalid_ex["valid"] is False


def test_jussive_not_allowed_after_wrong_negative():
    """فَحص قاعِدَة: لا يَجوز الجَزم إِذا كانَ التَّقدير الشَّرطيّ غَير صَحيح."""
    topic = {"topic_id": "JAWAB_AL_TALAB__P4", "title": "جواب الطلب",
             "part": 4, "start_page": 120, "end_page": 130}
    pages = [{"part": 4, "page": 120,
              "cleaned_text": "جواب الطلب — لا تدن من الأسد يأكلك خطأ",
              "raw_text": "..."}]
    rule = rule_extractor.extract_jawab_talab_rule(topic, pages)
    assert rule is not None
    # exceptions تَحوي تَحذيرًا حَول النَّهي
    assert any("النَّهي" in w for w in rule.exceptions_or_warnings)
