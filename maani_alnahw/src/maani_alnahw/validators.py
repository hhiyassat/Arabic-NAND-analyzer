"""validators.py — تَحَقُّق مِن سَلامَة المُخرَجات."""

from __future__ import annotations

from typing import Iterable


def validate_pages(pages: list[dict]) -> tuple[bool, list[str]]:
    errors = []
    for i, p in enumerate(pages):
        for req in ("doc_id", "part", "page", "raw_text", "source_file"):
            if req not in p:
                errors.append(f"page[{i}] missing {req}")
    return (len(errors) == 0, errors)


def validate_rules(rules: list[dict]) -> tuple[bool, list[str]]:
    errors = []
    seen_ids = set()
    for r in rules:
        rid = r.get("rule_id")
        if not rid:
            errors.append("rule has no rule_id")
            continue
        if rid in seen_ids:
            errors.append(f"duplicate rule_id: {rid}")
        seen_ids.add(rid)
        if not r.get("trigger"):
            errors.append(f"rule {rid} has no trigger")
        if not (0 <= r.get("confidence", 0) <= 1):
            errors.append(f"rule {rid} has invalid confidence")
    return (len(errors) == 0, errors)


def validate_topics(topics: list[dict]) -> tuple[bool, list[str]]:
    errors = []
    for t in topics:
        for req in ("topic_id", "title", "part", "start_page"):
            if req not in t:
                errors.append(f"topic missing {req}")
    return (len(errors) == 0, errors)


def low_confidence_records(records: list[dict], threshold: float = 0.75) -> list[dict]:
    return [r for r in records if r.get("confidence", 0) < threshold]
