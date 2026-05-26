"""ocr_normalizer.py — تَصحيح أَخطاء OCR.

طَبَقَتان:
  1. تَصحيحات ثابِتَة (static) — مِن lexicons/ocr_corrections_static.json
     • عَناوين الكِتاب
     • عَناوين الأَبواب
     • أَسماء العُلَماء
     • مُصطَلَحات نَحويَّة
  2. تَصحيحات heuristic — عَن طَريق قَوائم variants مَع confidence مُنخَفِض

لا تَتَلَف raw_text أَبَدًا — أَضِف cleaned_text فَقَط.
كُلّ تَصحيح يُسَجَّل في ocr_corrections.jsonl.
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
from grammar_kb.models import OCRCorrection


_LEX_DIR = _HERE.parent.parent / "lexicons"


def _load_lexicon(name: str) -> dict:
    path = _LEX_DIR / name
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── أَدوات تَطبيع نَصّيَّة عامَّة ──────────────────────────────────────────

DIACRITICS = "ًٌٍَُِّْـٰٓ"


def _strip_diacritics(s: str) -> str:
    return "".join(c for c in s if c not in DIACRITICS)


def _normalize_alif_ya(s: str) -> str:
    """تَطبيع خَفيف لِلمُقارَنَة — لا يُغَيِّر النَّصّ النِّهائيّ."""
    s = s.replace("ٱ", "ا")
    s = s.replace("ى", "ي")
    return s


def _is_likely_chapter_heading(line: str) -> bool:
    """سَطر قَصير، مُنعَزِل، بِلا فِعل = عُنوان مُحتَمَل."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    # لا يَنتَهي بِنُقطَة أَو فاصِلَة (عَناوين)
    if line.endswith((".", "،", "؛")):
        return False
    return True


# ─── المُطَبِّع الرَّئيس ──────────────────────────────────────────────────

class OCRNormalizer:

    def __init__(self):
        self._static = _load_lexicon("ocr_corrections_static.json")
        # نَبني خَريطَة مُسَطَّحَة بِكُلّ التَّصحيحات
        self._all_static: dict[str, dict] = {}
        for category in ("book_titles", "chapter_titles", "scholar_names", "grammar_terms"):
            cat_data = self._static.get(category, {})
            for raw, info in cat_data.items():
                if raw == "_description":
                    continue
                self._all_static[raw] = {
                    **info,
                    "category": category,
                }

        # نَرتِّب بِالأَطوَل أَوَّلًا لِيُفَضَّل المُطابَقَة الأَطوَل
        self._raw_keys = sorted(self._all_static.keys(), key=lambda s: -len(s))

    def normalize_page(self, raw_text: str, part: int, page: int) -> tuple[str, list[OCRCorrection]]:
        """يُرجِع (cleaned_text, list[OCRCorrection])."""
        corrections: list[OCRCorrection] = []
        cleaned = raw_text

        # 1. تَطبيق التَّصحيحات الثَّابِتَة
        for raw_form in self._raw_keys:
            if raw_form in cleaned:
                info = self._all_static[raw_form]
                normalized = info["normalized"]
                conf = info.get("confidence", 0.8)
                reason = info.get("reason", "")
                category = info.get("category", "")
                action = "applied" if conf >= 0.85 else "suggest_only"
                if action == "applied":
                    cleaned = cleaned.replace(raw_form, normalized)
                corrections.append(OCRCorrection(
                    part=part, page=page,
                    raw=raw_form, normalized=normalized,
                    reason=[reason, f"category={category}"],
                    confidence=conf, action=action,
                ))

        # 2. تَطبيع خَفيف عامّ
        # ى → ي في نِهايات الكَلِمات الشَّائعَة (مَع حَذَر)
        # هذِه طَبَقَة heuristic — لا تَتدخَّل في كَلِمات قرآنيَّة (تَكشَف بِالـ ٱ)
        # لِذلِك نَترُك raw_text كَما هو، وَ نَطبَع نُسخَة منفصلَة لِلبَحث.

        return cleaned, corrections


def normalize_pages(pages: Iterable[dict]) -> tuple[list[dict], list[OCRCorrection]]:
    """يَأخُذ قائِمَة pages dicts، يُرجِع (cleaned_pages, all_corrections)."""
    normalizer = OCRNormalizer()
    cleaned_pages = []
    all_corrections = []
    for p in pages:
        cleaned_text, corrections = normalizer.normalize_page(
            p["raw_text"], p["part"], p["page"]
        )
        new_p = dict(p)
        new_p["cleaned_text"] = cleaned_text
        cleaned_pages.append(new_p)
        all_corrections.extend(corrections)
    return cleaned_pages, all_corrections


def write_corrections_jsonl(corrections: list[OCRCorrection], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for c in corrections:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def write_pages_jsonl(pages: list[dict], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            count += 1
    return count
