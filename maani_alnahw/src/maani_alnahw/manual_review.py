"""manual_review.py — طابور المُراجَعَة اليَدَويَّة.

يَلتَقِط الصَّفَحات الَّتي تَحتاج إِنسانًا:
  • OCR مُشَوَّش جِدًّا
  • صَفحَة طَويلَة بِلا claims
  • topic بِلا cards
  • آيات غَير مُؤَكَّدَة
  • claims مُنخَفِضَة الثِّقَة
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import ManualReviewItem


def build_review_queue(
    pages: list[dict],
    claims: list[dict],
    cards: list[dict],
    coverage: list[dict],
    topics: list[dict],
) -> list[ManualReviewItem]:
    items: list[ManualReviewItem] = []

    # 1. صَفَحات حالَتها needs_manual_review أَو low_confidence
    for cov in coverage:
        if cov.get("extraction_status") not in ("needs_manual_review", "low_confidence"):
            continue
        # نَجِد raw excerpt
        page = next((p for p in pages
                     if p["part"] == cov["part"] and p["page"] == cov["page"]), None)
        sample = ""
        if page:
            text = page.get("cleaned_text") or page.get("raw_text", "")
            sample = text[:250]
        items.append(ManualReviewItem(
            part=cov["part"],
            page=cov["page"],
            reason=cov.get("notes") or cov.get("extraction_status"),
            suggested_action="manual review",
            raw_excerpt_sample=sample,
            confidence=0.4 if cov["extraction_status"] == "needs_manual_review" else 0.5,
            related_topic=cov.get("topic_title"),
        ))

    # 2. topics بِلا أَيّ meaning cards
    cards_by_topic = defaultdict(int)
    for c in cards:
        path = c.get("topic_path") or []
        if path:
            cards_by_topic[path[0]] += 1
    for t in topics:
        if cards_by_topic.get(t.get("title"), 0) == 0:
            items.append(ManualReviewItem(
                part=t["part"],
                page=t["start_page"],
                reason=f"topic «{t.get('title')}» مَكشوف لَكِن بِلا meaning cards",
                suggested_action="مُراجَعَة دَلاليَّة لِلباب",
                confidence=0.5,
                related_topic=t.get("title"),
            ))

    # 3. claims مُنخَفِضَة الثِّقَة (نَأخُذ سامبل مُمَيَّز)
    low_conf_pages = set()
    for c in claims:
        if c.get("confidence", 1.0) < 0.5:
            low_conf_pages.add((c.get("part"), c.get("page")))
    for (part, page) in low_conf_pages:
        if any(it.part == part and it.page == page for it in items):
            continue
        items.append(ManualReviewItem(
            part=part, page=page,
            reason="claims مُتَعَدِّدَة بِثِقَة مُنخَفِضَة في هذِه الصَّفحَة",
            suggested_action="مُراجَعَة claims + إِعادَة استخراج",
            confidence=0.45,
        ))

    return items


def write_review_jsonl(items: list[ManualReviewItem], output_path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
