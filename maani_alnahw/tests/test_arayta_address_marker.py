"""اختبار أَرَأَيتَكَ كَعَلامَة خِطاب لا كَمَفعول."""

from maani_alnahw import rule_extractor, construction_mapper


def test_araytakum_construction_kaaf_is_address_marker():
    topic = {"topic_id": "ARAYTAKA__P2", "title": "أرأيتك",
             "part": 2, "start_page": 50, "end_page": 55}
    pages = [{"part": 2, "page": 50,
              "cleaned_text": "أرأيت أرأيتك أرأيتكم — الاستخبار",
              "raw_text": "..."}]
    rule = rule_extractor.extract_arayta_rule(topic, pages)
    assert rule is not None
    # construction
    rule_dict = rule.to_dict()
    constructions = construction_mapper.build_constructions([rule_dict])
    assert len(constructions) == 1
    c = constructions[0]
    assert c["construction_id"] == "ARAYTAKUM_ISTIKHBAR"
    assert c["morphology"]["taa"]["status"] == "fixed"
    kaaf = c["morphology"]["kaaf_or_kaaf_plus"]
    assert kaaf["role"] == "address_marker"
    assert "ليست مفعولًا" in kaaf["warning"]
    # كم → plural
    assert c["morphology"]["kaaf_or_kaaf_plus"]["forms"]["كم"]["number"] == "plural"
