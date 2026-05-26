"""opinion_extractor.py — استخراج الخِلاف وَ التَّرجيح.

يَلتَقِط عِبارات الخِلاف:
  • قيل / ذهب / قال / قالوا
  • والصواب / والحق / والذي أراه / والأولى / والأظهر
  • وهذا مردود / وفيه نظر
  • الجمهور / البصريون / الكوفيون
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import Opinion


PREFERRED_MARKERS = [
    "والصواب", "والحق", "والذي أراه", "الذي أراه", "والأولى", "والأظهر",
    "والراجح", "والمختار", "والصحيح",
]

REPORTED_MARKERS = [
    "قيل", "وقيل", "ذهب", "ذهبوا", "قال", "قالوا", "ويرى", "يرى",
]

REJECTED_MARKERS = [
    "وهذا مردود", "وفيه نظر", "ولا يصح", "لا يصح", "وليس بشيء",
]

SCHOOLS = ["الجمهور", "البصريون", "الكوفيون", "البصرية", "الكوفية"]


def _split_sentences(text: str) -> list[str]:
    # تَقسيم خَفيف بِناءً على نُقطَة/فاصِلَة/استِفهام
    return re.split(r'[\.؟\n]+', text)


def _classify_sentence(s: str) -> Optional[str]:
    s_clean = s.strip()
    if not s_clean:
        return None
    for m in PREFERRED_MARKERS:
        if m in s_clean:
            return "preferred"
    for m in REJECTED_MARKERS:
        if m in s_clean:
            return "rejected"
    for m in REPORTED_MARKERS:
        if s_clean.startswith(m) or f" {m} " in s_clean[:30]:
            return "reported"
    return None


def _detect_holder(s: str) -> str:
    for sch in SCHOOLS:
        if sch in s:
            return sch
    # أَعلام مَعروفون
    for scholar in ["سيبويه", "الرضي", "ابن الناظم", "ابن عقيل", "الأشموني",
                    "الخضري", "الصبان", "الفراء", "الزمخشري", "ابن جني",
                    "ابن يعيش", "ابن هشام", "أبو حيان"]:
        if scholar in s:
            return scholar
    if "السامرائي" in s or "أرى" in s or "الذي أرى" in s:
        return "المؤلف"
    return ""


def extract_opinions_for_topic(topic: dict, pages: list[dict]) -> Optional[Opinion]:
    text = "\n".join(p.get("cleaned_text") or p.get("raw_text", "") for p in pages)
    sentences = _split_sentences(text)
    found_opinions = []
    for s in sentences:
        cls = _classify_sentence(s)
        if not cls:
            continue
        holder = _detect_holder(s) or "غير محدد"
        claim = s.strip()[:280]
        found_opinions.append({
            "holder": holder,
            "claim": claim,
            "status": cls,
        })

    if not found_opinions:
        return None

    return Opinion(
        opinion_id=f"OP_{topic['topic_id']}",
        topic_id=topic["topic_id"],
        issue=topic["title"],
        opinions=found_opinions[:20],  # حَدّ أَقصى لِتَجَنُّب الضَّجيج
        source={
            "part": topic["part"],
            "page_start": topic["start_page"],
            "page_end": topic.get("end_page"),
        },
    )


def extract_all_opinions(pages: list[dict], topics: list[dict]) -> list[Opinion]:
    opinions = []
    by_part_page: dict[tuple[int, int], dict] = {(p["part"], p["page"]): p for p in pages}
    for topic in topics:
        part = topic["part"]
        start = topic["start_page"]
        end = topic.get("end_page") or start
        topic_pages = [by_part_page[(part, pg)] for pg in range(start, end + 1)
                       if (part, pg) in by_part_page]
        if not topic_pages:
            continue
        op = extract_opinions_for_topic(topic, topic_pages)
        if op:
            opinions.append(op)
    return opinions


def write_opinions_jsonl(opinions: list[Opinion], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for o in opinions:
            f.write(json.dumps(o.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
