"""اختبار حُروف الجَرّ — لا نِيابَة آليَّة."""

from maani_alnahw import rule_extractor, construction_mapper


def test_preposition_does_not_simple_substitute():
    topic = {"topic_id": "PREPOSITION_SUBSTITUTION__P3", "title": "نيابة حروف الجر",
             "part": 3, "start_page": 1, "end_page": 50}
    pages = [{"part": 3, "page": 1,
              "cleaned_text": "حروف الجر إلى الباء اللام من تضمين تعدية",
              "raw_text": "..."}]
    rule = rule_extractor.extract_preposition_rule(topic, pages)
    assert rule is not None
    assert rule.syntactic_effect["rejected_default"] == "لا يَنوب بَعضُها عَن بَعض آليًّا"
    # investigation_order has tadmeen first
    assert "هَل هذا تَضمين؟" in rule.syntactic_effect["investigation_order"]


def test_tadmeen_rule_has_conditions():
    topic = {"topic_id": "TADMEEN__P3", "title": "التضمين",
             "part": 3, "start_page": 51, "end_page": 60}
    pages = [{"part": 3, "page": 51,
              "cleaned_text": "التضمين: إشراب لفظ معنى لفظ آخر، فيأخذ تعديته",
              "raw_text": "..."}]
    rule = rule_extractor.extract_tadmeen_rule(topic, pages)
    assert rule is not None
    # شُروط التَّضمين كامِلَة
    conds = rule.conditions
    assert any("مُناسَبَة" in c for c in conds)
    assert any("قَرينَة" in c for c in conds)
    assert any("اللَّبس" in c for c in conds)


def test_construction_preposition_warning():
    rule = {
        "rule_id": "PREPOSITION_SUBSTITUTION__P3_001",
        "source": {"part": 3, "page_start": 1},
        "confidence": 0.9,
    }
    constructions = construction_mapper.build_constructions([rule])
    assert len(constructions) == 1
    c = constructions[0]
    assert c["policy"] == "do_not_substitute_automatically"
    assert "check_tadmeen" in c["investigation_order"]
