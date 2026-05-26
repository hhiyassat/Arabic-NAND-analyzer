"""page_splitter.py — تَقسيم ملفّ OCR إلى صَفحات.

يَبحَث عَن فَواصِل: /////////////// page N ///////////////
يَستَخرِج part مِن اسم الملفّ (1.txt → part=1).
يَكتُب JSONL.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import sys
_HERE = Path(__file__).resolve().parent
_KB = _HERE.parent
sys.path.insert(0, str(_KB))
from grammar_kb.models import Page


# نَمَط فاصِل الصَّفحَة — يَسمَح بِأَيّ عَدَد مِن الـ /
PAGE_DELIM_RE = re.compile(r'/+\s*page\s+(\d+)\s*/+', re.IGNORECASE)


def split_file(path: str | Path) -> list[Page]:
    """يَقسِم ملفًّا واحِدًا إلى قائِمَة Pages."""
    path = Path(path)
    part = _infer_part(path.name)
    text = path.read_text(encoding="utf-8", errors="replace")

    pages: list[Page] = []
    matches = list(PAGE_DELIM_RE.finditer(text))
    if not matches:
        # ملفّ بِلا فَواصِل — صَفحَة واحِدَة
        pages.append(Page(
            doc_id=f"maani_alnahw_part_{part}",
            part=part,
            page=1,
            raw_text=text.strip(),
            source_file=path.name,
        ))
        return pages

    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        pages.append(Page(
            doc_id=f"maani_alnahw_part_{part}",
            part=part,
            page=page_num,
            raw_text=raw,
            source_file=path.name,
        ))
    return pages


def _infer_part(filename: str) -> int:
    """1.txt → 1، 2.txt → 2."""
    m = re.match(r'(\d+)\.txt$', filename)
    if m:
        return int(m.group(1))
    return 0


def split_directory(input_dir: str | Path) -> list[Page]:
    """يَقسِم كُلّ *.txt في مُجلَّد."""
    input_dir = Path(input_dir)
    all_pages: list[Page] = []
    for path in sorted(input_dir.glob("*.txt")):
        all_pages.extend(split_file(path))
    return all_pages


def write_jsonl(pages: Iterable[Page], output_path: str | Path) -> int:
    """يَكتُب الصَّفحات لِـ JSONL — يُرجِع العَدَد."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[dict]:
    """قِراءَة JSONL إلى قائِمَة dicts."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
