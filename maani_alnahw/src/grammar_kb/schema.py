"""grammar_kb/schema.py — مَخَطَّطات JSON لِكُلّ نَوع.

أَعمِدَة required + types — لِلتَّحَقُّق وَ التَّوثيق.
"""

SCHEMA_PAGE = {
    "required": ["doc_id", "part", "page", "raw_text", "source_file"],
    "optional": ["cleaned_text"],
}

SCHEMA_OCR_CORRECTION = {
    "required": ["part", "page", "raw", "normalized", "confidence"],
    "optional": ["reason", "action"],
}

SCHEMA_TOPIC = {
    "required": ["topic_id", "title", "part", "start_page", "confidence"],
    "optional": ["end_page", "parent_topic_id", "raw_heading", "normalized_heading"],
}

SCHEMA_RULE_CARD = {
    "required": ["rule_id", "topic_id", "title", "source", "trigger", "confidence"],
    "optional": ["syntactic_effect", "semantic_effect", "conditions",
                 "exceptions_or_warnings", "examples", "author_position"],
}

SCHEMA_EXAMPLE = {
    "required": ["example_id", "rule_id", "text"],
    "optional": ["type", "source", "expected_analysis", "surah", "surah_num", "ayah",
                 "needs_quran_verification"],
}

SCHEMA_OPINION = {
    "required": ["opinion_id", "topic_id", "issue", "opinions"],
    "optional": ["source"],
}


def validate_record(record: dict, schema: dict) -> tuple[bool, list]:
    """يَتَحَقَّق أَنّ الـ record يَحوي جَميع الحُقول المَطلوبَة."""
    errors = []
    for req in schema.get("required", []):
        if req not in record:
            errors.append(f"missing required field: {req}")
    return (len(errors) == 0, errors)
