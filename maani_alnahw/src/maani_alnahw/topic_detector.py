"""topic_detector.py — كَشف الأَبواب وَ الفُصول.

نَهج:
  • نَبحَث في cleaned_text كُلّ صَفحَة عَن نَمَط عُنوان قَصير (≤ 60 حَرف،
    أَوَّل سَطرَين، بِلا نُقطَة)
  • نُطابِق على معجم grammar_terms.json variants
  • نُسَجِّل الصَّفحَة الَّتي بَدَأ فيها العُنوان، وَ نَستَمِرّ حَتّى أَوَّل عُنوان آخَر
  • نُحَدِّد parent بِناءً على hierarchy في المُعجَم
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
from grammar_kb.models import Topic


_LEX_DIR = _HERE.parent.parent / "lexicons"


def _load_grammar_terms() -> dict:
    with open(_LEX_DIR / "grammar_terms.json", encoding="utf-8") as f:
        return json.load(f)


def _strip_diac(s: str) -> str:
    diacritics = "ًٌٍَُِّْـٰٓ"
    return "".join(c for c in s if c not in diacritics)


class TopicDetector:

    def __init__(self):
        self._terms = _load_grammar_terms()
        # نَبني فهرس variant → (id, title, parent)
        self._index: dict[str, dict] = {}
        for c in self._terms.get("constructions", []):
            for v in c.get("variants", []):
                key = _strip_diac(v).strip()
                self._index[key] = {
                    "id": c["id"],
                    "title": c["title"],
                    "parent": c.get("parent"),
                }

    def _scan_page(self, cleaned_text: str) -> list[dict]:
        """يَبحَث عَن عَناوين مُحتَمَلَة في الصَّفحَة."""
        found = []
        lines = cleaned_text.split("\n")
        for i, line in enumerate(lines):
            line_norm = _strip_diac(line.strip())
            if not line_norm or len(line_norm) > 60:
                continue
            if line_norm.endswith((".", "،", "؛", ":")):
                continue
            # مُطابَقَة مُباشِرَة
            if line_norm in self._index:
                info = self._index[line_norm]
                found.append({
                    **info,
                    "raw_heading": line.strip(),
                    "normalized_heading": info["title"],
                    "line_index": i,
                    "confidence": 0.92,
                })
                continue
            # مُطابَقَة جُزئيَّة (السَّطر يَحوي عُنوانًا)
            for variant, info in self._index.items():
                if variant == line_norm:
                    continue
                if len(variant) < 4:
                    continue
                # نَبحَث عَن العُنوان كَكَلِمَة مُستَقِلَّة
                if re.search(rf"(^|\s){re.escape(variant)}(\s|$)", line_norm):
                    # فَقَط لَو السَّطر قَصير (شَبيه بِعُنوان)
                    if len(line_norm) <= 30:
                        found.append({
                            **info,
                            "raw_heading": line.strip(),
                            "normalized_heading": info["title"],
                            "line_index": i,
                            "confidence": 0.78,
                        })
                        break
        return found

    def detect(self, pages: list[dict]) -> list[Topic]:
        """يَستَخرِج الأَبواب مِن قائِمَة صَفَحات (لها cleaned_text)."""
        topics: list[Topic] = []
        seen_ids_in_part: dict[int, dict[str, int]] = {}  # part → {topic_id: start_page}

        for page in pages:
            part = page["part"]
            page_num = page["page"]
            cleaned = page.get("cleaned_text", page.get("raw_text", ""))
            seen_ids_in_part.setdefault(part, {})

            found = self._scan_page(cleaned)
            for hit in found:
                tid = hit["id"]
                if tid in seen_ids_in_part[part]:
                    continue  # نَأخُذ أَوَّل ظُهور فَقَط لِكُلّ topic في كُلّ جُزء
                seen_ids_in_part[part][tid] = page_num
                topics.append(Topic(
                    topic_id=f"{tid}__P{part}",
                    title=hit["title"],
                    part=part,
                    start_page=page_num,
                    parent_topic_id=hit["parent"],
                    raw_heading=hit["raw_heading"],
                    normalized_heading=hit["normalized_heading"],
                    confidence=hit["confidence"],
                ))

        # نُحَدِّد end_page لِكُلّ topic = (start_page التّالي - 1) ضِمن الجُزء
        topics_by_part: dict[int, list[Topic]] = {}
        for t in topics:
            topics_by_part.setdefault(t.part, []).append(t)
        for part, ts in topics_by_part.items():
            ts.sort(key=lambda t: t.start_page)
            for i in range(len(ts) - 1):
                ts[i].end_page = ts[i + 1].start_page - 1

        return topics


def write_topics_jsonl(topics: list[Topic], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for t in topics:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
