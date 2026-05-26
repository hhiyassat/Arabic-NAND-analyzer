"""example_extractor.py — استخراج الأَمثلة وَ الآيات وَ الشَّواهِد.

نَهج:
  • الأَمثلة المَبنيَّة (constructed) — يَكتُبها المُؤَلِّف بَين قَوسَين أَو يَبدَأ بِـ «قُلت/تَقول/نَحو»
  • الآيات القُرآنيَّة — مَحصورَة بَين ( ... ) أَو بَين أَقواس مَع رَفقات [اسم_السورة: رَقم]
  • أَبيات الشِّعر — أَسطُر مُتَوازِنَة عَروضيًّا (تَقريب) — نَتَجاوَزها هُنا

نَستَخرِج الأَمثلة المُرتَبِطَة بِكُلّ rule في صَفَحاتِه.
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
from grammar_kb.models import Example


_LEX_DIR = _HERE.parent.parent / "lexicons"


def _load_surahs() -> dict[str, dict]:
    with open(_LEX_DIR / "quran_surah_names.json", encoding="utf-8") as f:
        data = json.load(f)
    # name → {num, name}
    out = {}
    for s in data.get("surahs", []):
        for v in s.get("variants", []):
            out[v] = s
        out[s["name"]] = s
    return out


SURAHS = None


def _get_surahs() -> dict:
    global SURAHS
    if SURAHS is None:
        SURAHS = _load_surahs()
    return SURAHS


# نَمَط آيَة: نَصّ بَين ( ... ) يَتلوه [اسم_السورة: رَقم]
QURAN_BRACKET_RE = re.compile(r'[\(﴿]([^\)﴾]{5,400})[\)﴾]\s*\[([^\]]+?)\]')


def _parse_surah_ref(ref: str) -> Optional[tuple[str, Optional[int], Optional[int]]]:
    """يُحَلِّل [يوسف: 36] → (يوسف, 36, 36)."""
    # نُنَظِّف
    ref = ref.replace("،", " ").replace("-", " ").strip()
    # نَفصِل بِـ :
    parts = ref.split(":")
    if len(parts) < 2:
        return None
    surah_name = parts[0].strip()
    surahs = _get_surahs()
    surah_info = surahs.get(surah_name)
    if not surah_info:
        # نُجَرِّب بِلا «ال»
        if surah_name.startswith("ال"):
            surah_info = surahs.get(surah_name[2:])
    if not surah_info:
        return None
    # رَقم الآيَة
    num_str = parts[1].strip()
    # نَزع الأَرقام العَرَبيَّة
    ar_to_en = {ord(c): chr(ord('0') + i) for i, c in enumerate('٠١٢٣٤٥٦٧٨٩')}
    num_str = num_str.translate(ar_to_en)
    m = re.search(r'(\d+)', num_str)
    if not m:
        return None
    ayah = int(m.group(1))
    return (surah_info["name"], surah_info["num"], ayah)


def _extract_quranic_examples_from_text(text: str, part: int, page: int,
                                         rule_id: str) -> list[Example]:
    examples = []
    for m in QURAN_BRACKET_RE.finditer(text):
        verse_text = m.group(1).strip()
        ref = m.group(2)
        parsed = _parse_surah_ref(ref)
        ex_id = f"EX_Q_{part}_{page}_{m.start()}"
        ex = Example(
            example_id=ex_id,
            rule_id=rule_id,
            text=verse_text,
            type="quranic_example",
            source={"part": part, "page": page, "ref_raw": ref},
            needs_quran_verification=True,  # OCR قَد يَكون مَشوَّهًا
        )
        if parsed:
            ex.surah = parsed[0]
            ex.surah_num = parsed[1]
            ex.ayah = parsed[2]
        examples.append(ex)
    return examples


# نَمَط مِثال مَبنيّ: «قُلت/تَقول/نَحو/مِثل + نَصّ بَين قَوسَين»
CONSTRUCTED_RE = re.compile(r'(?:نحو|مثل|قولك|تقول|قلت|كقولك)\s*[:\.]?\s*[\(﴿]([^\)﴾]{3,150})[\)﴾]')


def _extract_constructed_examples(text: str, part: int, page: int,
                                   rule_id: str) -> list[Example]:
    examples = []
    for m in CONSTRUCTED_RE.finditer(text):
        ex = Example(
            example_id=f"EX_C_{part}_{page}_{m.start()}",
            rule_id=rule_id,
            text=m.group(1).strip(),
            type="constructed_example",
            source={"part": part, "page": page},
        )
        examples.append(ex)
    return examples


def extract_examples(pages: list[dict], rules: list[dict]) -> list[Example]:
    """لِكُلّ rule، نَجمَع أَمثلَتَه مِن صَفَحاتِه."""
    examples: list[Example] = []
    by_part_page: dict[tuple[int, int], dict] = {(p["part"], p["page"]): p for p in pages}

    for rule in rules:
        source = rule.get("source", {})
        part = source.get("part")
        start = source.get("page_start")
        end = source.get("page_end") or start
        if not part or not start:
            continue
        rule_id = rule["rule_id"]
        for pg in range(start, end + 1):
            page = by_part_page.get((part, pg))
            if not page:
                continue
            text = page.get("cleaned_text") or page.get("raw_text", "")
            examples.extend(_extract_quranic_examples_from_text(text, part, pg, rule_id))
            examples.extend(_extract_constructed_examples(text, part, pg, rule_id))

        # أَيضًا الأَمثلة المُدمَجَة في rule نَفسها (مِن extractor)
        for i, ex in enumerate(rule.get("examples", [])):
            if isinstance(ex, dict) and ex.get("text"):
                examples.append(Example(
                    example_id=f"EX_R_{rule_id}_{i}",
                    rule_id=rule_id,
                    text=ex["text"],
                    type=ex.get("type", "constructed_example"),
                    source=ex.get("source", {"part": part, "page": start}),
                    expected_analysis={k: v for k, v in ex.items()
                                       if k not in ("text", "type", "source")},
                    surah=(ex.get("source") or {}).get("surah"),
                    ayah=(ex.get("source") or {}).get("ayah"),
                ))

    return examples


def write_examples_jsonl(examples: list[Example], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
