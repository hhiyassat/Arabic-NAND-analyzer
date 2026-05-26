"""coverage_analyzer.py — قِياس تَغطيَة الكِتاب.

مَقاييس النَّجاح الجَديدَة (لا «عَدَد constructions»):
  • page_coverage: كَم صَفحَة عُولِجَت
  • semantic_coverage: كَم صَفحَة أَخرَجَت claims
  • topic_coverage: هَل كُلّ topic إِمّا له cards أَو في manual_review
  • claim_density: مُتَوَسِّط claims/صَفحَة
  • engine_coverage: كَم meaning_card تَحَوَّل إلى construction
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import PageCoverage


def _has_ocr_warnings(page: dict, corrections_by_page: dict) -> bool:
    key = (page["part"], page["page"])
    return key in corrections_by_page and len(corrections_by_page[key]) > 3


def build_page_coverage(
    pages: list[dict],
    claims: list[dict],
    cards: list[dict],
    corrections: list[dict],
    topics: list[dict],
) -> list[PageCoverage]:
    """يُنشئ سِجِلّ تَغطيَة لِكُلّ صَفحَة."""
    claims_by_page = defaultdict(list)
    for c in claims:
        claims_by_page[(c["part"], c["page"])].append(c)

    cards_by_page = defaultdict(list)
    for card in cards:
        ref = (card.get("source_refs") or [{}])[0]
        if ref.get("part") and ref.get("page_start"):
            cards_by_page[(ref["part"], ref["page_start"])].append(card)

    corrections_by_page = defaultdict(list)
    for c in corrections:
        corrections_by_page[(c.get("part"), c.get("page"))].append(c)

    topic_by_page = {}
    for t in topics:
        part = t["part"]
        start = t["start_page"]
        end = t.get("end_page") or start
        for pg in range(start, end + 1):
            if (part, pg) not in topic_by_page:
                topic_by_page[(part, pg)] = t.get("title", "")

    coverage = []
    for page in pages:
        key = (page["part"], page["page"])
        text = page.get("cleaned_text") or page.get("raw_text", "")
        char_count = len(text)
        paragraph_count = len([p for p in text.split("\n\n") if p.strip()]) or 1
        page_claims = claims_by_page.get(key, [])
        page_cards = cards_by_page.get(key, [])
        avg_conf = (sum(c.get("confidence", 0) for c in page_claims) / len(page_claims)
                    if page_claims else 0)

        # تَحديد الـ status
        if char_count < 30:
            status = "no_semantic_content"
            notes = "صَفحَة قَصيرَة جِدًّا (غالِبًا غِلاف/فِهرِس)"
        elif not page_claims:
            if char_count > 500:
                status = "needs_manual_review"
                notes = "صَفحَة طَويلَة بِلا claims — تَحتاج مُراجَعَة"
            else:
                status = "no_semantic_content"
                notes = "لا أَنماط مُكتَشَفَة"
        elif avg_conf < 0.55:
            status = "low_confidence"
            notes = f"مُتَوَسِّط ثِقَة claims مُنخَفِض ({avg_conf:.2f})"
        else:
            status = "extracted"
            notes = ""

        coverage.append(PageCoverage(
            part=page["part"],
            page=page["page"],
            topic_title=topic_by_page.get(key),
            char_count=char_count,
            paragraph_count=paragraph_count,
            claims_count=len(page_claims),
            meaning_cards_count=len(page_cards),
            has_ocr_warnings=_has_ocr_warnings(page, corrections_by_page),
            extraction_status=status,
            notes=notes,
        ))
    return coverage


def write_coverage_jsonl(coverage: list[PageCoverage], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for c in coverage:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def summarize_coverage(coverage: list[dict]) -> dict:
    """مُلَخَّص رَقميّ لِلتَّقرير."""
    total = len(coverage)
    by_status = defaultdict(int)
    pages_with_claims = 0
    total_claims = 0
    pages_with_ocr_warnings = 0
    for c in coverage:
        by_status[c.get("extraction_status", "unknown")] += 1
        if c.get("claims_count", 0) > 0:
            pages_with_claims += 1
        total_claims += c.get("claims_count", 0)
        if c.get("has_ocr_warnings"):
            pages_with_ocr_warnings += 1
    return {
        "total_pages": total,
        "pages_with_claims": pages_with_claims,
        "pages_without_claims": total - pages_with_claims,
        "total_claims": total_claims,
        "avg_claims_per_page": round(total_claims / total, 2) if total else 0,
        "pages_with_ocr_warnings": pages_with_ocr_warnings,
        "by_status": dict(by_status),
    }
